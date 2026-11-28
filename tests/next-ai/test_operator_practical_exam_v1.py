import json
import unittest
from pathlib import Path

EXAM = Path(__file__).resolve().parents[2] / "training/nextai/operator_practical_exam_v1.json"


class OperatorPracticalExamTests(unittest.TestCase):
    def test_exam_is_explicitly_held_out_and_not_training_data(self):
        data = json.loads(EXAM.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "nextai-operator-practical-exam.v1")
        self.assertTrue(data["training_excluded"])
        self.assertEqual(data["split"], "test")
        self.assertGreaterEqual(len(data["cases"]), 18)
        ids = [case["case_id"] for case in data["cases"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_exam_covers_native_apps_engineering_and_integrated_projects(self):
        data = json.loads(EXAM.read_text(encoding="utf-8"))
        applications = {case["application"] for case in data["cases"]}
        self.assertTrue({"nextcad", "nextbim", "engineering", "integrated"}.issubset(applications))
        for case in data["cases"]:
            self.assertTrue(case["acceptance_criteria"])
            self.assertTrue(case["expected_evidence"])
            self.assertTrue(case["prohibited_claims"])


if __name__ == "__main__":
    unittest.main()
