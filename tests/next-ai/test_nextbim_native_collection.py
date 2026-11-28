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
            "tool": "create_part_box",
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


class NativeTrainingRecordSchemaTests(unittest.TestCase):
    def test_synthetic_native_fixture_matches_the_checked_in_json_schema(self):
        module.validate_training_record(make_record())

    def test_schema_rejects_unrecognised_fields_and_malformed_artifact_hashes(self):
        invalid = make_record()
        invalid["unapproved_runtime_flag"] = True
        with self.assertRaises(module.SchemaValidationError):
            module.validate_training_record(invalid)

        invalid = make_record()
        invalid["native_states"]["after"]["sha256"] = "not-a-sha256"
        with self.assertRaises(module.SchemaValidationError):
            module.validate_training_record(invalid)

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
            self.assertEqual(target["plan"][0]["tool"], "create_part_box")
            self.assertEqual(target["plan"][0]["args"]["length"], 100)
            schema_names = [item["function"]["name"] for item in example["tools"]]
            self.assertIn("create_part_box", schema_names)
            box_schema = next(item["function"] for item in example["tools"]
                              if item["function"]["name"] == "create_part_box")
            self.assertEqual(box_schema["parameters"]["properties"]["length"]["type"], "number")
            self.assertEqual(target["tool_schema_version"], "1.0")
            self.assertEqual(example["split"], "train")
            self.assertEqual(example["source"]["license"], "Apache-2.0")
            self.assertTrue(example["source"]["terms_reviewed"])
            self.assertEqual(example["privacy"]["redaction_status"], "not_needed")
            self.assertEqual(len(example["source"]["source_group_sha256"]), 64)
            evidence = example["native_trace_evidence"]
            self.assertTrue(evidence["round_trip_passed"])
            self.assertTrue(evidence["recompute_passed"])
            self.assertEqual(evidence["validation_overall"], "passed")
            self.assertEqual(evidence["operation_count"], 1)
            self.assertEqual(evidence["applied_operation_count"], 1)
            self.assertEqual(len(evidence["after_state_sha256"]), 64)
            self.assertEqual(len(evidence["operation_trace_sha256"]), 64)

    def test_nextcad_training_input_contains_initial_state_not_post_operation_state(self):
        item = make_record("state-leak-test", "train", "initial-project")
        item["native_states"]["before"] = {
            "format": "FCStd",
            "uri": "before.FCStd",
            "sha256": "c" * 64,
            "state_summary": {"stage": "before", "object_count": 2},
        }
        item["native_states"]["after"]["state_summary"] = {
            "stage": "after",
            "object_count": 99,
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(item) + "\n", encoding="utf-8")
            module.prepare(source, root / "out")
            example = json.loads((root / "out/train.jsonl").read_text(encoding="utf-8"))
            user_context = json.loads(example["messages"][1]["content"])
            self.assertEqual(user_context["native_context"]["document_state_at_request"]["stage"], "before")
            self.assertNotIn("after", user_context["native_context"])
            self.assertEqual(user_context["specification"], item["specification"])
            self.assertFalse(any("Recorded native operation" in value
                                 for value in user_context["specification"]["constraints"]))
            target = json.loads(example["messages"][2]["content"])
            self.assertEqual(target["plan"][0]["args"]["length"], 100)

    def test_nextbim_native_trace_keeps_its_application_specific_steps_contract(self):
        item = make_record("bim-record", "train", "bim-project")
        item["application"] = "nextbim"
        item["operations"][0]["tool"] = "wall"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "records.jsonl"
            source.write_text(json.dumps(item) + "\n", encoding="utf-8")
            summary = module.prepare(source, root / "out")
            self.assertEqual(summary["train"], 1, summary)
            example = json.loads((root / "out/train.jsonl").read_text(encoding="utf-8"))
            target = json.loads(example["messages"][2]["content"])
            self.assertIn("steps", target)
            self.assertNotIn("plan", target)
            self.assertEqual(target["steps"][0]["tool"], "wall")
            self.assertNotIn("tools", example)

    def test_nextbim_native_record_builder_produces_schema_valid_wall_record(self):
        from scripts.run_nextbim_ai_acceptance import build_native_record
        before = {"format": "BIMC", "uri": "before.bimc", "sha256": "a" * 64, "state_summary": {"counts": {"wall": 4}}}
        after = {"format": "BIMC", "uri": "after.bimc", "sha256": "b" * 64, "state_summary": {"counts": {"wall": 5}}}
        record = build_native_record(
            record_id="nextbim-train-wall-1", split="train", scenario_id="train-compact",
            prompt="Add a BIM wall from (1,2) to (3,2) mm.",
            command_id="wall", command_args={"points": [[1.0, 2.0], [3.0, 2.0]]},
            category="wall", before_state=before, after_state=after, before_count=4, after_count=5,
            cli_stdout='{"created":123}', application_version="bimcraft-cli 0.1",
        )
        module.validate_training_record(record)
        self.assertEqual(record["application"], "nextbim")
        self.assertEqual(record["operations"][0]["tool"], "wall")
        self.assertEqual(record["operations"][0]["result"]["element_category"], "wall")
        self.assertEqual(record["split"], "train")
        self.assertEqual(record["validation"]["checks"][0]["actual"], 5)

    def test_nextbim_native_record_builder_produces_schema_valid_floor_record(self):
        from scripts.run_nextbim_ai_acceptance import build_native_record
        before = {"format": "BIMC", "uri": "before.bimc", "sha256": "a" * 64, "state_summary": {"counts": {"floor": 1}}}
        after = {"format": "BIMC", "uri": "after.bimc", "sha256": "b" * 64, "state_summary": {"counts": {"floor": 2}}}
        boundary = [[15000.0, 12000.0], [18000.0, 12000.0], [18000.0, 15000.0], [15000.0, 15000.0]]
        record = build_native_record(
            record_id="nextbim-train-floor-1", split="train", scenario_id="train-compact",
            prompt="Create a floor inside the specified boundary.",
            command_id="floor", command_args={"boundary": boundary},
            category="floor", before_state=before, after_state=after, before_count=1, after_count=2,
            cli_stdout='{"id":124,"area_m2":9}', application_version="bimcraft-cli 0.1",
        )
        module.validate_training_record(record)
        self.assertEqual(record["operations"][0]["tool"], "floor")
        self.assertEqual(record["operations"][0]["arguments"]["boundary"], boundary)
        self.assertEqual(record["operations"][0]["result"]["element_category"], "floor")
        self.assertEqual(record["validation"]["checks"][0]["check_id"], "floor_count_increment")

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
