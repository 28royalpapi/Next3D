from __future__ import annotations

import unittest

from scripts.collect_nextcad_native_splits import (
    SCENARIOS,
    validate_source_lineage_separation,
    validate_split_trace_rows,
)


def rows_for(split: str):
    scenario = SCENARIOS[split][0]
    source_id = f"native-nextcad:{scenario}:{split}:project-lineage"
    return [
        {
            "schema_version": "1.0.0",
            "record_id": f"{scenario}-{stage}",
            "application": "nextcad",
            "split": split,
            "source": {"source_id": source_id},
            "task": {"prompt": f"Create the approved test object, stage {stage}"},
            "validation": {
                "overall": "passed",
                "round_trip_passed": True,
                "recompute_passed": True,
            },
            "native_states": {"after": {"sha256": "a" * 64}},
            "operations": [
                {"tool": "create_part_box", "status": "applied", "arguments": {"length": 100}}
            ],
        }
        for stage in ("a", "b")
    ]


class NextCADNativeSplitValidationTests(unittest.TestCase):
    def test_all_three_splits_validate_with_distinct_scenario_lineages(self):
        reports = {
            split: validate_split_trace_rows(split, rows_for(split))
            for split in ("train", "validation", "test")
        }
        validate_source_lineage_separation(reports)
        self.assertEqual(
            [reports[split]["records"] for split in ("train", "validation", "test")],
            [2, 2, 2],
        )
        self.assertEqual(
            {reports[split]["scenario_id"] for split in reports},
            {SCENARIOS[split][0] for split in reports},
        )

    def test_scenario_identity_must_be_present_in_source_lineage(self):
        rows = rows_for("train")
        for row in rows:
            row["source"]["source_id"] = "native-nextcad:wrong-scenario:train:project"
        with self.assertRaisesRegex(ValueError, "source lineage does not match its scenario"):
            validate_split_trace_rows("train", rows)

    def test_native_after_state_requires_a_sha256_digest(self):
        rows = rows_for("test")
        rows[0]["native_states"]["after"]["sha256"] = "not-a-hash"
        with self.assertRaisesRegex(ValueError, "valid saved native after-state SHA-256"):
            validate_split_trace_rows("test", rows)

    def test_stage_prompts_must_be_distinct(self):
        rows = rows_for("validation")
        rows[1]["task"]["prompt"] = rows[0]["task"]["prompt"]
        with self.assertRaisesRegex(ValueError, "stage prompts must be present and distinct"):
            validate_split_trace_rows("validation", rows)

    def test_project_lineage_cannot_cross_split_boundaries(self):
        reports = {
            "train": {"source_id": "same-project-lineage"},
            "validation": {"source_id": "same-project-lineage"},
            "test": {"source_id": "heldout-project-lineage"},
        }
        with self.assertRaisesRegex(ValueError, "assigned to more than one split"):
            validate_source_lineage_separation(reports)


if __name__ == "__main__":
    unittest.main()
