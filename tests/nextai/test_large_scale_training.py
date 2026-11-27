from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from training.nextai.audit_nextai_corpus import audit_corpus, render_record_text
from training.nextai.buildeng_dataset import make_buildeng_record, SOURCE_LICENSE


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


    def test_buildeng_record_preserves_provenance_and_l0_evidence(self):
        row = {
            "category": "structural/beams",
            "tags": ["reaction", "deterministic"],
            "messages": [
                {"role": "system", "content": "You are a careful engineering assistant."},
                {"role": "user", "content": "A simply supported beam spans 4 m and carries 8 kN/m."},
                {"role": "assistant", "content": "For a simply supported beam with a full-span UDL, each support reaction is wL/2 = 16 kN. The maximum sagging moment is wL^2/8 = 16 kN m. This is a basic statics result, not a member design."},
            ],
        }
        record = make_buildeng_record(row, 17)
        self.assertEqual(record["license"], "Apache-2.0")
        self.assertEqual(record["license"], SOURCE_LICENSE)
        self.assertEqual(record["evidence_level"], "L0")
        self.assertFalse(record["native_execution_verified"])
        self.assertEqual(record["source_category"], "structural/beams")
        self.assertEqual(record["source_split"], "train")
        self.assertIn(record["split"], {"train", "validation", "test"})

    def test_buildeng_identical_user_brief_cannot_leak_across_splits(self):
        first = {
            "category": "structural/beams",
            "tags": ["reaction"],
            "messages": [
                {"role": "system", "content": "Careful engineer."},
                {"role": "user", "content": "Calculate support reactions for a 4 m beam."},
                {"role": "assistant", "content": "The data is incomplete; provide the support arrangement and loading before calculating."},
            ],
        }
        second = {
            "category": "structural/beams",
            "tags": ["adversarial"],
            "messages": [
                {"role": "system", "content": "Different system prompt."},
                {"role": "user", "content": "  Calculate support reactions for a 4 m beam.  "},
                {"role": "assistant", "content": "The support type and loading must be known. A 4 m span alone is not enough to calculate reactions."},
            ],
        }
        a = make_buildeng_record(first, 1)
        b = make_buildeng_record(second, 2)
        self.assertEqual(a["source_group_sha256"], b["source_group_sha256"])
        self.assertEqual(a["split"], b["split"])

    def test_buildeng_rejects_incomplete_or_non_text_conversation(self):
        row = {
            "category": "structural/beams",
            "messages": [
                {"role": "system", "content": "System"},
                {"role": "user", "content": "Please calculate."},
                {"role": "assistant", "content": " "},
            ],
        }
        with self.assertRaises(ValueError):
            make_buildeng_record(row, 1)


if __name__ == "__main__":
    unittest.main()
