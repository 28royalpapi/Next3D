import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training" / "nextai"
sys.path.insert(0, str(TRAINING))

from engineering_benchmark_v1 import (
    BENCHMARK_VERSION,
    aggregate_scores,
    benchmark_records,
    score_prediction,
)


class IndependentEngineeringBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = benchmark_records()
        cls.by_id = {case["case_id"]: case for case in cls.cases}

    def _reference_prediction(self, case):
        expected = case["expected"]
        if expected["status"] == "calculated":
            return json.dumps({
                "status": "calculated",
                "method": expected["method"],
                "values": expected["values"],
                "units": expected["units"],
                "working": "Reference-value fixture for scoring logic.",
                "limitations": "Calculation only; not design approval.",
            })
        phrases = [group[0] for group in expected["required_missing_groups"]]
        return json.dumps({
            "status": "insufficient_information",
            "missing_inputs": phrases,
            "limitations": "No unsupported design result is supplied.",
        })

    def test_benchmark_has_unique_train_excluded_cases_across_engineering_domains(self):
        self.assertEqual(BENCHMARK_VERSION, "nextai-engineering-heldout-v1")
        self.assertEqual(len(self.cases), 28)
        self.assertEqual(len(self.by_id), len(self.cases))
        self.assertGreaterEqual(len({case["domain"] for case in self.cases}), 8)
        self.assertTrue(all(case["level"] for case in self.cases))

    def test_reference_answers_pass_the_numeric_and_safety_rubric(self):
        scored = [
            score_prediction(case, self._reference_prediction(case))
            for case in self.cases
        ]
        self.assertTrue(all(row["passed"] for row in scored))
        summary = aggregate_scores(scored)
        self.assertEqual(summary["case_count"], 28)
        self.assertEqual(summary["passed_cases"], 28)
        self.assertEqual(summary["overall_pass_rate"], 1.0)

    def test_numerically_wrong_result_fails_even_when_json_and_method_are_valid(self):
        case = self.by_id["GEO-01"]
        expected = case["expected"]
        prediction = {
            "status": expected["status"],
            "method": expected["method"],
            "values": dict(expected["values"]),
            "units": dict(expected["units"]),
        }
        prediction["values"]["effective_stress_kpa"] = 99.0
        score = score_prediction(case, json.dumps(prediction))
        self.assertEqual(score["json_parse"], 1.0)
        self.assertEqual(score["method_match"], 1.0)
        self.assertLess(score["numeric_accuracy"], 1.0)
        self.assertFalse(score["passed"])

    def test_wrong_or_missing_units_fail(self):
        case = self.by_id["HYD-03"]
        expected = case["expected"]
        prediction = {
            "status": "calculated",
            "method": expected["method"],
            "values": dict(expected["values"]),
            "units": {"input_power_kw": "W"},
        }
        score = score_prediction(case, json.dumps(prediction))
        self.assertEqual(score["numeric_accuracy"], 1.0)
        self.assertEqual(score["unit_accuracy"], 0.0)
        self.assertFalse(score["passed"])

    def test_underdetermined_design_must_ask_for_missing_inputs(self):
        case = self.by_id["SAFE-01"]
        prediction = {
            "status": "insufficient_information",
            "missing_inputs": ["design loads", "support restraint", "concrete grade",
                               "reinforcement grade", "design code edition"],
        }
        score = score_prediction(case, json.dumps(prediction))
        self.assertEqual(score["missing_input_coverage"], 1.0)
        self.assertTrue(score["passed"])

    def test_underdetermined_design_fails_if_model_invents_numeric_sizes(self):
        case = self.by_id["SAFE-01"]
        prediction = {
            "status": "insufficient_information",
            "missing_inputs": ["design loads", "support restraint", "concrete grade",
                               "reinforcement grade", "design code edition"],
            "values": {"beam_depth_mm": 600},
        }
        score = score_prediction(case, json.dumps(prediction))
        self.assertTrue(score["hallucinated_numeric_design_result"])
        self.assertFalse(score["passed"])

    def test_independent_benchmark_is_not_imported_into_training_corpus_builder(self):
        corpus_builder = (TRAINING / "prepare_public_corpora.py").read_text(encoding="utf-8")
        trainer = (TRAINING / "train_nextai.py").read_text(encoding="utf-8")
        self.assertNotIn("engineering_benchmark_v1", corpus_builder)
        self.assertNotIn("engineering_benchmark_v1", trainer)

    def test_inference_runner_compiles_without_starting_model_compute(self):
        source = (TRAINING / "run_engineering_benchmark.py").read_text(encoding="utf-8")
        compile(source, str(TRAINING / "run_engineering_benchmark.py"), "exec")


if __name__ == "__main__":
    unittest.main()
