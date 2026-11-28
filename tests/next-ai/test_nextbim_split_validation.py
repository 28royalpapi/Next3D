import hashlib
import tempfile
import unittest
from pathlib import Path
from scripts.collect_nextbim_native_splits import describe_artifact, validate_split_trace_rows, validate_source_lineage_separation


class NextBIMNativeSplitValidationTests(unittest.TestCase):
    def test_artifact_inventory_records_portable_path_size_and_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "sft" / "train.jsonl"
            path.parent.mkdir()
            payload = b'{"record_id":"r1"}\\n'
            path.write_bytes(payload)
            item = describe_artifact(path, root, records=1)
            self.assertEqual(item["path"], "sft/train.jsonl")
            self.assertEqual(item["bytes"], len(payload))
            self.assertEqual(item["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(item["records"], 1)

    def test_artifact_inventory_rejects_record_count_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "train.jsonl"
            path.write_text('{"record_id":"r1"}\\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "record count mismatch"):
                describe_artifact(path, root, records=2)

    def test_artifact_inventory_rejects_paths_outside_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "output"
            outside = Path(temp) / "outside.jsonl"
            root.mkdir()
            outside.write_text("{}\\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes the output directory"):
                describe_artifact(outside, root)

    def rows(self, split, scenario):
        result = []
        stages = (
            ("a", "wall", "wall", 5, 6),
            ("b", "floor", "floor", 1, 2),
        )
        for stage, command, category, count_before, count_after in stages:
            result.append({
                "schema_version": "1.0.0",
                "record_id": f"{scenario}-{stage}",
                "application": "nextbim",
                "split": split,
                "source": {"source_id": f"native-bim:{scenario}:{split}:a0c57b738e308d433ab4b8c0c93d7fff9e53bc1"},
                "task": {"prompt": f"Add native {command} stage {stage} for {scenario}."},
                "native_states": {
                    "before": {"sha256": "b" * 64},
                    "after": {"sha256": "a" * 64},
                },
                "validation": {
                    "overall": "passed",
                    "round_trip_passed": True,
                    "recompute_passed": True,
                    "checks": [{
                        "check_id": f"{category}_count_increment",
                        "status": "pass",
                        "expected": count_after,
                        "actual": count_after,
                    }],
                },
                "operations": [{
                    "tool": command,
                    "status": "applied",
                    "before_state_hash": "b" * 64,
                    "after_state_hash": "a" * 64,
                    "result": {
                        "element_category": category,
                        "element_count_before": count_before,
                        "element_count_after_reopen": count_after,
                        "count_delta": 1,
                    },
                }],
            })
        return result

    def test_three_splits_validate_with_distinct_project_lineages(self):
        reports = {
            "train": validate_split_trace_rows("train", self.rows("train", "train-compact")),
            "validation": validate_split_trace_rows("validation", self.rows("validation", "validation-standard")),
            "test": validate_split_trace_rows("test", self.rows("test", "test-expanded")),
        }
        validate_source_lineage_separation(reports)
        self.assertEqual([reports[k]["records"] for k in ("train", "validation", "test")], [2, 2, 2])
        self.assertEqual(len({reports[k]["source_id"] for k in reports}), 3)

    def test_same_project_lineage_cannot_be_reused_across_splits(self):
        reports = {"train": {"source_id": "same-project"}, "validation": {"source_id": "same-project"}, "test": {"source_id": "heldout-project"}}
        with self.assertRaisesRegex(ValueError, "assigned to more than one split"):
            validate_source_lineage_separation(reports)

    def test_failed_save_reopen_or_recompute_evidence_is_rejected(self):
        rows = self.rows("test", "test-expanded")
        rows[0]["validation"]["round_trip_passed"] = False
        with self.assertRaisesRegex(ValueError, "lacks save/reopen or recompute evidence"):
            validate_split_trace_rows("test", rows)

    def test_source_lineage_must_identify_the_expected_split_scenario(self):
        rows = self.rows("train", "train-compact")
        rows[0]["source"]["source_id"] = "native-bim:wrong-scenario:train:pinned"
        rows[1]["source"]["source_id"] = "native-bim:wrong-scenario:train:pinned"
        with self.assertRaisesRegex(ValueError, "does not match its scenario"):
            validate_split_trace_rows("train", rows)

    def test_collector_requires_wall_and_floor_in_each_split(self):
        rows = self.rows("test", "test-expanded")
        rows[1]["operations"][0]["tool"] = "wall"
        rows[1]["operations"][0]["result"]["element_category"] = "wall"
        rows[1]["validation"]["checks"][0]["check_id"] = "wall_count_increment"
        with self.assertRaisesRegex(ValueError, "one native wall and one native floor"):
            validate_split_trace_rows("test", rows)

    def test_collector_rejects_commands_outside_accepted_native_scope(self):
        rows = self.rows("test", "test-expanded")
        rows[0]["operations"][0]["tool"] = "beam"
        rows[0]["operations"][0]["result"]["element_category"] = "beam"
        rows[0]["validation"]["checks"][0]["check_id"] = "beam_count_increment"
        with self.assertRaisesRegex(ValueError, "unsupported command"):
            validate_split_trace_rows("test", rows)

    def test_operation_hashes_must_match_native_before_and_after_states(self):
        rows = self.rows("test", "test-expanded")
        rows[0]["operations"][0]["after_state_hash"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "operation hashes do not match"):
            validate_split_trace_rows("test", rows)

    def test_native_element_count_must_increase_exactly_once(self):
        rows = self.rows("test", "test-expanded")
        rows[0]["operations"][0]["result"]["count_delta"] = 2
        with self.assertRaisesRegex(ValueError, "does not prove exactly one persisted element"):
            validate_split_trace_rows("test", rows)

    def test_validation_count_must_match_reopened_cli_result(self):
        rows = self.rows("validation", "validation-standard")
        rows[1]["validation"]["checks"][0]["actual"] = 999
        with self.assertRaisesRegex(ValueError, "validation count does not match"):
            validate_split_trace_rows("validation", rows)

    def test_stage_prompts_must_be_distinct(self):
        rows = self.rows("train", "train-compact")
        rows[1]["task"]["prompt"] = rows[0]["task"]["prompt"]
        with self.assertRaisesRegex(ValueError, "stage prompts must be present and distinct"):
            validate_split_trace_rows("train", rows)

    def test_wrong_application_or_split_is_rejected(self):
        rows = self.rows("validation", "standard")
        rows[0]["application"] = "nextcad"
        with self.assertRaisesRegex(ValueError, "wrong application or schema"):
            validate_split_trace_rows("validation", rows)


if __name__ == "__main__":
    unittest.main()
