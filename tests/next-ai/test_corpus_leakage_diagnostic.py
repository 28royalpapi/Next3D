from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training/nextai"))
from diagnose_corpus_leakage import diagnose


class CorpusLeakageDiagnosticTests(unittest.TestCase):
    def test_reports_cross_split_text_and_source_identity_without_mutating_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rows = {
                "train": [{
                    "record_id": "r1", "domain": "cad", "source": "source-a",
                    "split_group": "group-shared", "messages": [
                        {"role": "user", "content": "Create a 2 m beam."},
                        {"role": "assistant", "content": "Plan A."},
                    ], "images": [],
                }],
                "validation": [{
                    "record_id": "r2", "domain": "cad", "source": "source-b",
                    "split_group": "group-shared", "messages": [
                        {"role": "user", "content": "Create a 2 m beam."},
                        {"role": "assistant", "content": "Plan A."},
                    ], "images": [],
                }],
                "test": [{
                    "record_id": "r3", "domain": "bim", "source": "source-c",
                    "split_group": "test-only", "messages": [
                        {"role": "user", "content": "Create a 3 m beam."},
                        {"role": "assistant", "content": "Plan B."},
                    ], "images": [],
                }],
            }
            original = {}
            for split, values in rows.items():
                path = root / f"{split}.jsonl"
                original[split] = json.dumps(values[0], sort_keys=True)
                path.write_text(original[split] + "\n", encoding="utf-8")
            report = diagnose(root)
            self.assertEqual(report["summary"]["cross_split_exact_text_groups"], 1)
            self.assertEqual(report["summary"]["cross_split_identity_groups"], 1)
            for split in rows:
                self.assertEqual((root / f"{split}.jsonl").read_text().strip(), original[split])


if __name__ == "__main__":
    unittest.main()
