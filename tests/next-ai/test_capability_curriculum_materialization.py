from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training" / "nextai"
sys.path.insert(0, str(TRAINING))

import prepare_public_corpora as public_corpus  # noqa: E402
from build_capability_curriculum import build  # noqa: E402


class CapabilityLearningCurriculumTests(unittest.TestCase):
    def test_source_catalogs_produce_2150_bim_and_192_nextcad_module_lessons(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = build(Path(temp))
            self.assertEqual(manifest["nextcad_source_modules"], 32)
            self.assertEqual(manifest["nextcad_runtime_commands"], 0)
            self.assertEqual(manifest["nextcad_runtime_api_members"], 0)
            self.assertFalse(manifest["nextcad_runtime_census_complete"])
            self.assertEqual(manifest["nextbim_registered_commands"], 215)
            self.assertEqual(manifest["capability_l0_lessons"], 2342)
            self.assertEqual(manifest["capability_lessons_by_type"], {
                "native_command": 2150,
                "workbench_or_module": 192,
            })
            self.assertEqual(manifest["nextcad_workbench_module_lessons"], 192)
            self.assertEqual(manifest["bim_command_obligations_not_training_examples"], 2150)
            self.assertEqual(manifest["nextcad_runtime_obligations_not_training_examples"], 0)
            self.assertEqual(manifest["fine_tuning_readiness"], "NOT_READY_FOR_FULL_OPERATOR_FINETUNING")

    def test_every_discovered_capability_gets_its_expected_learning_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = build(Path(temp))
            rows = []
            for split in ("train", "validation", "test"):
                with (Path(temp) / f"{split}.jsonl").open("r", encoding="utf-8") as handle:
                    rows.extend(json.loads(line) for line in handle if line.strip())
            capability_rows = [
                row for row in rows
                if row.get("record_type") == "authored_metadata_knowledge_not_native_execution"
            ]
            grouped = {}
            for row in capability_rows:
                grouped.setdefault(row["capability_id"], []).append(row)
            self.assertEqual(len(grouped), 247)
            for capability_id, lessons in grouped.items():
                kind = lessons[0]["capability_type"]
                expected = 6 if kind == "workbench_or_module" else 10
                self.assertEqual(len(lessons), expected, capability_id)
                expected_dimensions = (
                    set(public_corpus.NEXTCAD_MODULE_SKILL_DIMENSIONS)
                    if kind == "workbench_or_module"
                    else set(public_corpus.CAPABILITY_SKILL_DIMENSIONS)
                )
                self.assertEqual({row["learning_dimension"] for row in lessons}, expected_dimensions)
                self.assertEqual(
                    {row["split_group"] for row in lessons},
                    {f"capability-knowledge-{lessons[0]['application']}-{capability_id}"},
                )
                self.assertEqual(
                    {row["evidence_level"] for row in lessons},
                    {"L0_metadata_knowledge_authored"},
                )
            module_rows = [row for row in capability_rows if row["capability_type"] == "workbench_or_module"]
            self.assertTrue(module_rows)
            for row in module_rows:
                completion = json.loads(row["completion"])
                self.assertNotEqual(
                    completion["capability"]["runtime_status"],
                    "discovered_in_running_application",
                )
                self.assertIn("source module only", completion["evidence_boundary"])
                self.assertEqual(completion["capability"]["capability_type"], "workbench_or_module")

    def test_capability_and_skill_split_groups_do_not_leak(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = build(Path(temp))
            seen = {}
            for split in ("train", "validation", "test"):
                with (Path(temp) / f"{split}.jsonl").open("r", encoding="utf-8") as handle:
                    for line in handle:
                        row = json.loads(line)
                        self.assertEqual(row["curriculum_split"], split)
                        group = row["split_group"]
                        prior = seen.setdefault(group, split)
                        self.assertEqual(prior, split, f"split-group leakage: {group} appears in {prior} and {split}")
            self.assertGreater(manifest["local_skill_l0_lessons"], 0)
            self.assertEqual(manifest["local_skill_count"], 16)

    def test_ids_and_file_hashes_are_unique_and_readback_counts_match(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = build(Path(temp))
            ids = []
            for split in ("train", "validation", "test"):
                path = Path(temp) / f"{split}.jsonl"
                rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
                ids.extend(row["record_id"] for row in rows)
                self.assertEqual(len(rows), manifest["by_split"][split]["combined"])
                self.assertEqual(
                    manifest["files"][path.name]["sha256"],
                    __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                )
            self.assertEqual(len(ids), len(set(ids)))

    def test_require_runtime_option_fails_closed_without_live_report(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "live NextCAD runtime report"):
                build(Path(temp), require_nextcad_runtime=True)


if __name__ == "__main__":
    unittest.main()
