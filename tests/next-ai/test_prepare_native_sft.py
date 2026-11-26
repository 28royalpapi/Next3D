import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/prepare_native_sft.py"
spec = importlib.util.spec_from_file_location("prepare_native_sft", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_record(record_id="r1", split="train", source_id="project-a"):
    return {
        "schema_version": "1.0.0",
        "record_id": record_id,
        "application": "nextcad",
        "application_version": "1.0",
        "adapter_schema_version": "1.0",
        "task": {
            "prompt": "Create a 100 mm cube.",
            "task_type": "create",
            "discipline": ["mechanical"],
            "language": "en",
        },
        "specification": {
            "parameters": [],
            "constraints": [],
            "assumptions": [],
            "unresolved_questions": [],
        },
        "native_states": {
            "before": None,
            "after": {
                "format": "FCStd",
                "uri": "file://after.FCStd",
                "sha256": "a" * 64,
                "state_summary": {"objects": 1},
            },
        },
        "operations": [{
            "sequence": 0,
            "tool": "create_box",
            "tool_schema_version": "1.0",
            "arguments": {"length": 100, "width": 100, "height": 100},
            "result": {"created": "Box"},
            "status": "applied",
            "transaction_id": "tx-1",
            "before_state_hash": None,
            "after_state_hash": "b" * 64,
        }],
        "validation": {
            "overall": "passed",
            "checks": [{"check_id": "solid_valid", "status": "pass", "summary": "Solid is valid"}],
            "round_trip_passed": True,
            "recompute_passed": True,
        },
        "artifacts": [],
        "source": {
            "source_type": "synthetic",
            "source_id": source_id,
            "license": "Apache-2.0",
            "permission_status": "not_required",
            "terms_reviewed": True,
            "withdrawal_key": "synthetic-1",
        },
        "privacy": {
            "user_consent": False,
            "contains_personal_data": False,
            "public_release_allowed": True,
            "redaction_status": "not_needed",
        },
        "split": split,
    }


class PrepareNativeSftTests(unittest.TestCase):
    def test_valid_native_trace_becomes_tool_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(make_record()) + "\n", encoding="utf-8")
            out = root / "out"
            summary = module.prepare(source, out)
            self.assertEqual(summary["train"], 1)
            example = json.loads((out / "train.jsonl").read_text(encoding="utf-8"))
            target = json.loads(example["messages"][2]["content"])
            self.assertEqual(target["message"], "I have a confirmed specification and will carry out the approved native CAD plan.")
            self.assertEqual(target["plan"][0]["tool"], "create_box")
            self.assertEqual(target["plan"][0]["args"]["length"], 100)
            self.assertEqual(target["tool_schema_version"], "1.0")
            self.assertEqual(example["split"], "train")
            self.assertEqual(example["source"]["license"], "Apache-2.0")
            self.assertTrue(example["source"]["terms_reviewed"])
            self.assertEqual(example["privacy"]["redaction_status"], "not_needed")
            self.assertEqual(len(example["source"]["source_group_sha256"]), 64)

    def test_nextbim_native_trace_keeps_its_application_specific_steps_contract(self):
        item = make_record("bim-record", "train", "bim-project")
        item["application"] = "nextbim"
        item["operations"][0]["tool"] = "wall"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(item) + "\\n", encoding="utf-8")
            module.prepare(source, root / "out")
            example = json.loads((root / "out/train.jsonl").read_text(encoding="utf-8"))
            target = json.loads(example["messages"][2]["content"])
            self.assertIn("steps", target)
            self.assertNotIn("plan", target)
            self.assertEqual(target["steps"][0]["tool"], "wall")

    def test_failed_native_validation_is_quarantined(self):
        item = make_record()
        item["validation"]["overall"] = "failed"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(item) + "\n", encoding="utf-8")
            summary = module.prepare(source, root / "out")
            self.assertEqual(summary["train"], 0)
            self.assertEqual(summary["quarantine"], 1)

    def test_source_lineage_cannot_leak_across_splits(self):
        a = make_record("train-record", "train", "same-project")
        b = make_record("test-record", "test", "same-project")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(a) + "\n" + json.dumps(b) + "\n", encoding="utf-8")
            summary = module.prepare(source, root / "out")
            self.assertEqual(summary["train"], 0)
            self.assertEqual(summary["test"], 0)
            self.assertEqual(summary["quarantine"], 2)

    def test_test_split_remains_separate(self):
        item = make_record("test-record", "test", "heldout-project")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(item) + "\n", encoding="utf-8")
            summary = module.prepare(source, root / "out")
            self.assertEqual(summary["test"], 1)
            self.assertEqual(summary["train"], 0)
            self.assertTrue(summary["test_split_is_not_added_to_training"])


if __name__ == "__main__":
    unittest.main()
