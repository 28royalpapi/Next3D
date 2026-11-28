import importlib.util
import json
import unittest
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "training/nextai/nextai_master_curriculum.py"
spec = importlib.util.spec_from_file_location("nextai_master_curriculum", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
CORPUS_SCRIPT = ROOT / "training/nextai/prepare_public_corpora.py"
corpus_spec = importlib.util.spec_from_file_location("prepare_public_corpora_master_audit", CORPUS_SCRIPT)
corpus_module = importlib.util.module_from_spec(corpus_spec)
corpus_spec.loader.exec_module(corpus_module)
BUILD_SCRIPT = ROOT / "training/nextai/build_master_curriculum.py"
build_spec = importlib.util.spec_from_file_location("build_master_curriculum", BUILD_SCRIPT)
build_module = importlib.util.module_from_spec(build_spec)
build_spec.loader.exec_module(build_module)


class MasterCurriculumTests(unittest.TestCase):
    def test_materialized_files_and_manifest_report_exact_student_examples(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = build_module.build(Path(temp))
            self.assertEqual(manifest["total_examples"], 940)
            self.assertEqual(manifest["by_split"], {"train": 752, "validation": 94, "test": 94})
            self.assertEqual(manifest["combined_reference_inventory"]["analytic_plus_master_curriculum_total"], 250940)
            self.assertEqual(manifest["combined_reference_inventory"]["train_eligible_records"], 225843)
            self.assertTrue(manifest["all_subjects_have_ten_examples"])
            self.assertTrue(manifest["all_record_ids_unique"])
            self.assertTrue(manifest["all_normalized_prompts_unique"])
            self.assertFalse(manifest["native_execution_claimed"])
            self.assertEqual(manifest["by_collection"]["NextCAD"], 120)
            self.assertEqual(manifest["by_collection"]["Next BIM"], 120)
            self.assertEqual(manifest["by_collection"]["Engineering disciplines"], 160)
            self.assertEqual(manifest["by_collection"]["Complex engineering projects"], 100)
            self.assertEqual(manifest["by_collection"]["Native operator, tool selection and recovery"], 120)
            self.assertEqual(manifest["by_application"], {
                "nextcad": 120, "nextbim": 120, "engineering": 280,
                "integrated": 200, "operator": 220,
            })
            self.assertEqual(manifest["by_split_and_variant"]["validation"], {"DELIVERY": 94})
            self.assertEqual(manifest["by_split_and_variant"]["test"], {"INDEPENDENT_REVIEW": 94})
    def test_each_subject_has_ten_meaningfully_distinct_examples(self):
        rows = module.make_master_project_curriculum()
        self.assertEqual(len(rows), 940)
        self.assertEqual(len({row["record_id"] for row in rows}), 940)
        self.assertEqual(len({row["prompt"] for row in rows}), 940)
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["curriculum_subject_id"]].append(row)
        self.assertEqual(len(grouped), 94)
        self.assertTrue(all(len(items) == 10 for items in grouped.values()))
        expected = {
            "NextCAD": 120,
            "Next BIM": 120,
            "Engineering disciplines": 280,
            "Complex engineering projects": 200,
            "Native operator, tool selection and recovery": 120,
        }
        self.assertEqual(dict(Counter(row["curriculum_collection"] for row in rows)), expected)

    def test_split_counts_are_exact_and_each_subject_spans_all_splits(self):
        rows = module.make_master_project_curriculum()
        splits = corpus_module.split_synthetic_curriculum(rows)
        self.assertEqual(build_module.split_curriculum(rows), splits)
        summary = module.summarize_master_curriculum_splits(splits)
        self.assertEqual(summary["total"], 940)
        self.assertEqual(summary["by_split"], {"train": 752, "validation": 94, "test": 94})
        self.assertEqual(sum(summary["by_domain"].values()), 940)
        self.assertEqual(sum(summary["by_application"].values()), 940)
        expected_collections = {
            "NextCAD": 120,
            "Next BIM": 120,
            "Engineering disciplines": 280,
            "Complex engineering projects": 200,
            "Native operator, tool selection and recovery": 120,
        }
        self.assertEqual(summary["by_collection"], expected_collections)
        by_subject_split = defaultdict(Counter)
        for split, items in splits.items():
            for row in items:
                by_subject_split[row["curriculum_subject_id"]][split] += 1
        for subject_id, counts in by_subject_split.items():
            self.assertEqual(counts, Counter({"train": 8, "validation": 1, "test": 1}), subject_id)
        self.assertEqual(summary["evidence_level"], "L0_authored_learning_example")
        self.assertFalse(summary["native_execution_claimed"])

    def test_nine_variant_types_cover_distinct_learning_conditions(self):
        rows = module.make_master_project_curriculum()
        expected_variants = {
            "BASELINE", "BOUNDARY", "CLARIFY", "REVISION", "RECOVERY",
            "COORDINATION", "ALTERNATIVE", "CHANGE_IMPACT", "DELIVERY",
            "INDEPENDENT_REVIEW",
        }
        by_subject = defaultdict(set)
        for row in rows:
            by_subject[row["curriculum_subject_id"]].add(row["curriculum_variant_id"])
        for subject_id, variants in by_subject.items():
            self.assertEqual(variants, expected_variants, subject_id)

    def test_clarification_examples_never_include_a_native_write_plan(self):
        for row in module.make_master_project_curriculum():
            target = json.loads(row["completion"])
            if row["curriculum_variant_id"] == "CLARIFY":
                self.assertEqual(target["response_mode"], "clarify_before_action")
                self.assertTrue(target["execution_blocked_until_clarification"])
                self.assertEqual(target["native_write_plan"], [])
                self.assertGreaterEqual(len(target["workflow"]), 3)
                self.assertTrue(all(step.get("objective") for step in target["workflow"]))

    def test_each_record_has_structured_l0_target_and_preserves_subject_lineage(self):
        rows = module.make_master_project_curriculum()
        for row in rows:
            self.assertTrue(row["prompt"].strip(), row["record_id"])
            target = json.loads(row["completion"])
            self.assertEqual(target["scenario_id"], row["curriculum_subject_id"])
            self.assertEqual(target["variant_id"], row["curriculum_variant_id"])
            self.assertEqual(target["evidence_level"], "L0_authored_learning_example")
            self.assertEqual(target["execution_status"], "not_executed_by_this_example")
            self.assertGreaterEqual(len(target["workflow"]), 3, row["record_id"])
            self.assertGreaterEqual(len(target["acceptance_checks"]), 3, row["record_id"])
            self.assertTrue(target["limitations_and_non_claims"], row["record_id"])

    def test_no_native_success_or_engineering_approval_is_claimed(self):
        for row in module.make_master_project_curriculum():
            target = json.loads(row["completion"])
            self.assertEqual(target["evidence_level"], "L0_authored_learning_example")
            self.assertNotIn("native_execution_passed", target)
            self.assertEqual(target["execution_status"], "not_executed_by_this_example")
            self.assertTrue(target["limitations_and_non_claims"])
            self.assertTrue(all(isinstance(item, str) and item.strip()
                                for item in target["limitations_and_non_claims"]))


    def test_stage_three_explicitly_covers_electrical_and_mechanical_disciplines(self):
        rows = module.make_master_project_curriculum()
        subjects = {
            row["curriculum_subject_id"]: (row["domain"], row["stage"])
            for row in rows if row["curriculum_variant_id"] == "BASELINE"
        }
        required = {
            "ENG-017": "engineering_electrical_load_and_distribution",
            "ENG-018": "engineering_electrical_lighting_and_emergency",
            "ENG-019": "engineering_electrical_earthing_protection",
            "ENG-020": "engineering_electrical_control_panels",
            "ENG-021": "engineering_instrumentation_and_control",
            "ENG-022": "engineering_power_system_studies",
            "ENG-023": "engineering_renewable_microgrids",
            "ENG-024": "engineering_mechanical_hvac_thermal",
            "ENG-025": "engineering_mechanical_thermodynamics",
            "ENG-026": "engineering_mechanical_machine_elements",
            "ENG-027": "engineering_product_design_and_manufacturing",
            "ENG-028": "engineering_electromechanical_integration",
        }
        for subject_id, domain in required.items():
            self.assertEqual(subjects[subject_id], (domain, "discipline_depth"))

    def test_stage_four_and_five_are_expanded_with_concrete_subjects(self):
        rows = module.make_master_project_curriculum()
        baseline = {
            row["curriculum_subject_id"]: row
            for row in rows if row["curriculum_variant_id"] == "BASELINE"
        }
        operator_ids = [f"OPS-{number:03d}" for number in range(13, 23)]
        project_ids = [f"PRJ-{number:03d}" for number in range(11, 21)]
        for subject_id in operator_ids:
            self.assertIn(subject_id, baseline)
            self.assertEqual(baseline[subject_id]["stage"], "operator_method")
        for subject_id in project_ids:
            self.assertIn(subject_id, baseline)
            self.assertEqual(baseline[subject_id]["stage"], "integrated_projects")
        for subject_id in operator_ids + project_ids:
            target = json.loads(baseline[subject_id]["completion"])
            self.assertGreaterEqual(len(target["workflow"]), 4)
            self.assertGreaterEqual(len(target["acceptance_checks"]), 4)
            self.assertTrue(target["limitations_and_non_claims"])



if __name__ == "__main__":
    unittest.main()
