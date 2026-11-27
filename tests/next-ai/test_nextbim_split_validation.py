import unittest
from scripts.collect_nextbim_native_splits import validate_split_trace_rows, validate_source_lineage_separation


class NextBIMNativeSplitValidationTests(unittest.TestCase):
    def rows(self, split, scenario):
        return [{
            "schema_version": "1.0.0", "record_id": f"{scenario}-{stage}", "application": "nextbim",
            "split": split, "source": {"source_id": f"native-bim:{scenario}:{split}:a0c57b738e308d433ab4b8c0c93d7fff9e53bc1"},
            "native_states": {"after": {"sha256": "a" * 64}},
            "validation": {"overall": "passed", "round_trip_passed": True, "recompute_passed": True},
            "operations": [{"tool": "wall", "status": "applied"}],
        } for stage in ("a", "b")]

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
        rows = self.rows("test", "expanded")
        rows[0]["validation"]["round_trip_passed"] = False
        with self.assertRaisesRegex(ValueError, "lacks save/reopen or recompute evidence"):
            validate_split_trace_rows("test", rows)

    def test_source_lineage_must_identify_the_expected_split_scenario(self):
        rows = self.rows("train", "compact")
        rows[0]["source"]["source_id"] = "native-bim:wrong-scenario:train:pinned"
        rows[1]["source"]["source_id"] = "native-bim:wrong-scenario:train:pinned"
        with self.assertRaisesRegex(ValueError, "does not match its scenario"):
            validate_split_trace_rows("train", rows)

    def test_collector_rejects_commands_outside_wall_acceptance_scope(self):
        rows = self.rows("test", "expanded")
        rows[0]["operations"][0]["tool"] = "beam"
        with self.assertRaisesRegex(ValueError, "only native wall commands"):
            validate_split_trace_rows("test", rows)

    def test_wrong_application_or_split_is_rejected(self):
        rows = self.rows("validation", "standard")
        rows[0]["application"] = "nextcad"
        with self.assertRaisesRegex(ValueError, "wrong application or schema"):
            validate_split_trace_rows("validation", rows)


if __name__ == "__main__":
    unittest.main()
