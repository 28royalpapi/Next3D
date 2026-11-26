from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "training" / "nextai" / "NextAI_Qwen35_Engineering_Student.ipynb"


class TrainingNotebookContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        cls.code = [
            (cell.get("source", []) if isinstance(cell.get("source", []), str)
             else "".join(cell.get("source", [])))
            for cell in cls.notebook.get("cells", [])
            if cell.get("cell_type") == "code"
        ]

    def test_base_and_tuned_models_use_the_same_held_out_corpus_split(self):
        source = next((item for item in self.code if "training/nextai/evaluate_nextai.py" in item), "")
        self.assertTrue(source, "Notebook must run the multimodal held-out evaluator.")
        self.assertIn("('base', 'Qwen/Qwen3.5-0.8B')", source)
        self.assertIn("('tuned', OUTPUT_DIR + '/merged_16bit')", source)
        self.assertIn("'--test-jsonl', DATA_DIR + '/test.jsonl'", source)
        self.assertIn("'evaluation-{label}.json'", source)

    def test_independent_engineering_benchmark_runs_for_both_models(self):
        source = next((item for item in self.code if "run_engineering_benchmark.py" in item), "")
        self.assertTrue(source, "Notebook must run the train-excluded engineering benchmark.")
        self.assertIn("'engineering-benchmark-{label}.json'", source)
        self.assertIn("'--model', model_path", source)
        self.assertIn("'--output', benchmark_path", source)
        self.assertIn("benchmark['summary']", source)

    def test_both_independent_benchmark_reports_are_persisted_with_the_candidate(self):
        source = next((item for item in self.code if "PERSISTENT_DIR" in item and "candidate_manifest" in item), "")
        self.assertTrue(source, "Notebook must persist a candidate manifest.")
        self.assertIn("'engineering-benchmark-base.json'", source)
        self.assertIn("'engineering-benchmark-tuned.json'", source)


if __name__ == "__main__":
    unittest.main()
