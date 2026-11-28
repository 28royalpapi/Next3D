import importlib.util
import json
import unittest
import importlib.util
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


class MasterCurriculumTests(unittest.TestCase):

    def test_master_examples_survive_assigned_splits_and_have_auditable_counts(self):
        rows = module.make_master_project_curriculum()
        splits = corpus_module.split_synthetic_curriculum(rows)
        summary = module.summarize_master_curriculum_splits(splits)
        self.assertEqual(summary["total"], 62)
        self.assertEqual(sum(summary["by_split"].values()), 62)
        self.assertEqual(sum(summary["by_domain"].values()), 62)
        self.assertEqual(sum(summary["by_application"].values()), 62)
        self.assertEqual(summary["evidence_level"], "L0_authored_learning_example")
        self.assertFalse(summary["native_execution_claimed"])
        self.assertGreater(summary["by_split"]["train"], 0)
        self.assertGreater(summary["by_split"]["validation"], 0)
        self.assertGreater(summary["by_split"]["test"], 0)

    def test_curriculum_is_broad_and_has_unique_split_lineage(self):
        rows = module.make_master_project_curriculum()
        self.assertGreaterEqual(len(rows), 60)
        self.assertEqual(len({row["record_id"] for row in rows}), len(rows))
        self.assertEqual(len({row["split_group"] for row in rows}), len(rows))
        domains = {row["domain"] for row in rows}
        for required in (
            "cad_parametric_design",
            "bim_residential_architecture",
            "engineering_structural_slabs",
            "engineering_geotechnical_foundations",
            "engineering_stormwater_drainage",
            "integrated_project_ten_storey_office",
            "operator_native_tool_selection",
            "operator_failed_recompute_recovery",
            "operator_ifc_roundtrip_recovery",
        ):
            self.assertIn(required, domains)

    def test_each_record_has_a_structured_l0_target_and_checks(self):
        rows = module.make_master_project_curriculum()
        for row in rows:
            self.assertTrue(row["prompt"].strip(), row["record_id"])
            target = json.loads(row["completion"])
            self.assertEqual(target["scenario_id"], row["record_id"])
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


if __name__ == "__main__":
    unittest.main()
