from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.nextai.audit_nextai_corpus import audit_corpus, render_record_text


class FakeTokenizer:
    name_or_path = "fake-test-tokenizer"

    def encode(self, text, add_special_tokens=False):
        return text.split()


class LargeScaleTrainingTests(unittest.TestCase):
    def test_conversation_text_and_tools_are_counted_separately(self):
        row = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "Create a beam"}]},
                {"role": "assistant", "content": [{"type": "text", "text": "Need span and loads"}]},
            ],
            "tools": [{"type": "function", "function": {"name": "inspect_model"}}],
        }
        text, schemas = render_record_text(row)
        self.assertIn("<user>", text)
        self.assertIn("Create a beam", text)
        self.assertIn("Need span and loads", text)
        self.assertIn("inspect_model", schemas)

    def test_token_audit_counts_splits_and_images(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "small.jpg"
            image.write_bytes(b"fake-image-bytes")
            rows = {
                "train": [
                    {"record_id": "train-1", "domain": "structural", "source": "authored",
                     "license": "project-authored", "prompt": "Calculate beam reaction",
                     "completion": "Reaction is 12 kN", "images": [str(image)]}
                ],
                "validation": [
                    {"record_id": "validation-1", "domain": "bim", "source": "public",
                     "license": "MIT", "prompt": "What is IFC?", "completion": "A data schema."}
                ],
                "test": [
                    {"record_id": "test-1", "domain": "cad", "source": "public",
                     "license": "Apache-2.0", "prompt": "List features", "completion": "Pad then pocket."}
                ],
            }
            for split, records in rows.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in records),
                    encoding="utf-8",
                )
            report = audit_corpus(root, FakeTokenizer())
            self.assertEqual(report["status"], "PASS")
            self.assertGreater(report["train_text_tokens"], 0)
            self.assertEqual(report["image_files_total"], 1)
            self.assertEqual(report["missing_image_files"], [])

    def test_cross_split_source_group_leakage_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = {"source_group_sha256": "same-project-hash"}
            records = {
                "train": [{"record_id": "a", "prompt": "A", "completion": "B", **source}],
                "validation": [{"record_id": "b", "prompt": "C", "completion": "D", **source}],
                "test": [{"record_id": "c", "prompt": "E", "completion": "F"}],
            }
            for split, rows in records.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )
            with self.assertRaisesRegex(ValueError, "Cross-split source identity leakage"):
                audit_corpus(root, FakeTokenizer())

    def test_missing_image_is_reported_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = {
                "train": [{"record_id": "a", "prompt": "A", "completion": "B", "images": [str(root / "missing.jpg")]}],
                "validation": [{"record_id": "b", "prompt": "C", "completion": "D"}],
                "test": [{"record_id": "c", "prompt": "E", "completion": "F"}],
            }
            for split, rows in records.items():
                (root / f"{split}.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows),
                    encoding="utf-8",
                )
            report = audit_corpus(root, FakeTokenizer())
            self.assertEqual(len(report["missing_image_files"]), 1)


if __name__ == "__main__":
    unittest.main()
