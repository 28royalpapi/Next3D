import importlib.util
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training/nextai"
sys.path.insert(0, str(TRAINING))

from scaled_practical_curriculum import (  # noqa: E402
    COLLECTIONS,
    PROFILES,
    SPECS,
    TARGET_PER_COLLECTION,
    VERSION,
    make_scaled_curriculum_expansion,
    summarize_scaled_curriculum,
)
from nextai_master_curriculum import make_master_project_curriculum  # noqa: E402


class ScaledPracticalCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = make_master_project_curriculum()
        cls.expansion = make_scaled_curriculum_expansion()
        cls.summary = summarize_scaled_curriculum(cls.expansion, cls.baseline)
        cls.all_rows = cls.baseline + cls.expansion

    def test_every_practical_collection_reaches_twenty_thousand(self):
        self.assertEqual(self.summary["total_examples_including_v2_baseline"], 100_000)
        self.assertEqual(self.summary["new_expansion_examples"], 99_380)
        self.assertEqual(
            self.summary["by_collection"],
            {collection: TARGET_PER_COLLECTION for collection in COLLECTIONS},
        )

    def test_exact_eighty_ten_ten_split_and_no_group_leakage(self):
        self.assertEqual(
            self.summary["by_split"],
            {"train": 80_000, "validation": 10_000, "test": 10_000},
        )
        groups = {}
        for row in self.all_rows:
            group = row["split_group"]
            split = row["curriculum_split"]
            self.assertNotIn(group, groups, f"scenario group repeated: {group}")
            groups[group] = split
        self.assertEqual(len(groups), 100_000)

    def test_every_original_subject_reaches_its_allocated_count(self):
        per_subject = Counter(row["curriculum_subject_id"] for row in self.all_rows)
        self.assertEqual(len(per_subject), 62)
        self.assertEqual(sum(per_subject.values()), 100_000)
        for collection in COLLECTIONS:
            specs = sorted(
                [spec for spec in SPECS if
                 __import__("nextai_master_curriculum").COLLECTION_BY_APPLICATION[spec["application"]] == collection],
                key=lambda spec: spec["id"],
            )
            quotient, remainder = divmod(TARGET_PER_COLLECTION, len(specs))
            for index, spec in enumerate(specs):
                self.assertEqual(
                    per_subject[spec["id"]],
                    quotient + (1 if index < remainder else 0),
                    spec["id"],
                )

    def test_all_seven_scenario_axes_are_materially_varied(self):
        for collection in COLLECTIONS:
            rows = [row for row in self.expansion if row["curriculum_collection"] == collection]
            self.assertEqual(len(rows), TARGET_PER_COLLECTION - len([
                row for row in self.baseline if row["curriculum_collection"] == collection
            ]))
            keys = [
                "project_context", "primary_objective", "operation", "starting_state",
                "constraint", "input_quality", "deliverable", "affected_input",
            ]
            for key in keys:
                values = {row["scenario_axes"][key] for row in rows}
                self.assertGreaterEqual(len(values), 4, f"{collection} axis {key} is too narrow")

    def test_coverage_summary_reads_scenario_axes_from_serialized_completion(self):
        from scaled_practical_curriculum import summarize_scaled_curriculum
        rows = make_scaled_practical_curriculum()
        serialized_rows = []
        for row in rows:
            copied = dict(row)
            copied.pop("scenario_axes", None)
            # The corpus writer serializes the target; this mirrors that boundary.
            copied["completion"] = json.dumps(json.loads(row["completion"]), ensure_ascii=False)
            serialized_rows.append(copied)
        summary = summarize_scaled_curriculum(serialized_rows)
        self.assertEqual(summary["total_examples_including_v2_baseline"], 100_000)
        for collection, axes in summary["scenario_axis_coverage"].items():
            self.assertEqual(len(axes), 8)
            self.assertTrue(all(not axis["missing_options"] for axis in axes.values()))

    def test_every_profile_option_is_represented_in_each_collection(self):
        coverage = self.summary["scenario_axis_coverage"]
        self.assertEqual(set(coverage), set(COLLECTIONS))
        for collection in COLLECTIONS:
            self.assertEqual(
                set(coverage[collection]),
                {
                    "project_context", "primary_objective", "operation",
                    "starting_state", "constraint", "input_quality",
                    "deliverable", "affected_input",
                },
            )
            for axis, report in coverage[collection].items():
                self.assertEqual(
                    report["unique_options"],
                    report["required_options"],
                    f"{collection} axis {axis} omits profile options",
                )
                self.assertEqual(report["missing_options"], [])
                self.assertGreater(report["min_examples_per_option"], 0)
                self.assertEqual(report["total_examples"], len([
                    row for row in self.expansion
                    if row["curriculum_collection"] == collection
                ]))

    def test_missing_conflicting_and_unverified_inputs_block_native_writes(self):
        blocked = 0
        for row in self.expansion:
            target = json.loads(row["completion"])
            self.assertEqual(target["curriculum_version"], VERSION)
            self.assertEqual(target["evidence_level"], "L0_authored_learning_example")
            self.assertEqual(target["execution_status"], "not_executed_by_this_example")
            if target["execution_blocked_until_clarification"]:
                blocked += 1
                self.assertEqual(target["native_write_plan"], [])
                self.assertIn(target["scenario_axes"]["input_quality"], {"MISSING", "CONFLICT", "UNVERIFIED"})
                self.assertEqual(len(target["unresolved_inputs"]), 1)
                self.assertEqual(
                    target["unresolved_inputs"][0]["input"],
                    target["scenario_axes"]["affected_input"],
                )
                self.assertNotIn(
                    target["scenario_axes"]["affected_input"],
                    target["confirmed_inputs"],
                )
            else:
                self.assertIsInstance(target["native_write_plan"], str)
                self.assertNotEqual(target["native_write_plan"], "")
        self.assertGreater(blocked, 0)
        blocked_ratio = blocked / len(self.expansion)
        self.assertGreaterEqual(blocked_ratio, 0.29)
        self.assertLessEqual(blocked_ratio, 0.31)
        confirmed = sum(
            json.loads(row["completion"])["scenario_axes"]["input_quality"] == "CONFIRMED"
            for row in self.expansion
        )
        confirmed_ratio = confirmed / len(self.expansion)
        self.assertGreaterEqual(confirmed_ratio, 0.69)
        self.assertLessEqual(confirmed_ratio, 0.71)
        self.assertEqual(self.summary["by_input_quality_in_expansion"]["CONFIRMED"], confirmed)
        self.assertEqual(self.summary["blocked_until_clarification_examples_in_expansion"], blocked)

    def test_prompt_and_record_identity_are_unique(self):
        self.assertEqual(len({row["record_id"] for row in self.all_rows}), 100_000)
        normalized = {" ".join(row["prompt"].lower().split()) for row in self.all_rows}
        self.assertEqual(len(normalized), 100_000)

    def test_evidence_labels_never_claim_native_execution(self):
        self.assertEqual(
            {row["evidence_level"] for row in self.all_rows},
            {"L0_authored_learning_example"},
        )
        for row in self.expansion:
            target = json.loads(row["completion"])
            self.assertFalse(target.get("native_execution_verified", False))
            self.assertFalse(target.get("professional_engineering_approval", False))
            self.assertIn("not evidence of native application execution", " ".join(target["limitations_and_non_claims"]))

    def test_materializer_writes_exact_files_and_manifest(self):
        builder_path = TRAINING / "build_scaled_practical_curriculum.py"
        spec = importlib.util.spec_from_file_location("build_scaled_practical_curriculum", builder_path)
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            manifest = builder.build(Path(temp))
            self.assertEqual(manifest["total_examples_including_v2_baseline"], 100_000)
            self.assertEqual(manifest["by_split"], {
                "train": 80_000, "validation": 10_000, "test": 10_000,
            })
            for split, expected in (("train", 80_000), ("validation", 10_000), ("test", 10_000)):
                path = Path(temp) / f"{split}.jsonl"
                with path.open("r", encoding="utf-8") as handle:
                    self.assertEqual(sum(1 for line in handle if line.strip()), expected)
            stored = json.loads((Path(temp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["files"], manifest["files"])
            self.assertFalse(stored["native_execution_claimed"])


if __name__ == "__main__":
    unittest.main()
