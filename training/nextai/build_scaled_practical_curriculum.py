#!/usr/bin/env python3
"""Materialize the complete 100,000-example scaled NextAI practical curriculum."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scaled_practical_curriculum import (
    COLLECTIONS,
    TARGET_PER_COLLECTION,
    VERSION,
    make_scaled_curriculum_expansion,
    summarize_scaled_curriculum,
)
from nextai_master_curriculum import make_master_project_curriculum


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def build(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = make_master_project_curriculum()
    expansion = make_scaled_curriculum_expansion()
    all_rows = baseline + expansion
    summary = summarize_scaled_curriculum(expansion, baseline)
    splits = {name: [] for name in ("train", "validation", "test")}
    for row in all_rows:
        split = row.get("curriculum_split")
        if split not in splits:
            raise ValueError(f"Invalid curriculum split on {row.get('record_id')}: {split!r}")
        splits[split].append(row)

    expected_splits = {"train": 80_000, "validation": 10_000, "test": 10_000}
    if {name: len(rows) for name, rows in splits.items()} != expected_splits:
        raise ValueError("Materialized practical curriculum split counts are not 80k/10k/10k")

    all_ids: set[str] = set()
    split_groups: dict[str, str] = {}
    for split, rows in splits.items():
        for row in rows:
            rid = str(row.get("record_id") or "")
            if not rid or rid in all_ids:
                raise ValueError(f"Missing or duplicate record ID: {rid!r}")
            all_ids.add(rid)
            group = str(row.get("split_group") or rid)
            prior = split_groups.setdefault(group, split)
            if prior != split:
                raise ValueError(f"Scenario group leakage: {group} appears in {prior} and {split}")
        write_jsonl(output_dir / f"{split}.jsonl", rows)

    files = {
        f"{split}.jsonl": {
            "records": len(rows),
            "bytes": (output_dir / f"{split}.jsonl").stat().st_size,
            "sha256": sha256_file(output_dir / f"{split}.jsonl"),
        }
        for split, rows in splits.items()
    }
    manifest = {
        "schema_version": "nextai-scaled-practical-curriculum-manifest.v1",
        "curriculum_version": VERSION,
        "student_target": "Qwen/Qwen3.5-0.8B",
        "source": "Next3D authored and deterministic scenario-matrix curriculum",
        "license": "project-authored",
        "evidence_level": "L0_authored_learning_example",
        "native_execution_claimed": False,
        "target_per_collection": TARGET_PER_COLLECTION,
        "collections": list(COLLECTIONS),
        **summary,
        "files": files,
        "all_record_ids_unique": len(all_ids) == len(all_rows),
        "scenario_group_split_leakage": False,
        "training_policy": {
            "train_records": 80_000,
            "validation_records": 10_000,
            "held_out_test_records": 10_000,
            "validation_or_test_used_for_gradient_updates": False,
            "clarification_blocked_records_have_empty_native_write_plan": True,
            "native_execution_traces_included": 0,
            "professional_engineering_approvals_claimed": 0,
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Read back each JSONL without holding a second full copy in memory.
    for split, expected in expected_splits.items():
        count = 0
        with (output_dir / f"{split}.jsonl").open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                if row.get("curriculum_split") != split:
                    raise ValueError(f"{split}.jsonl row {line_number} has the wrong split label")
                count += 1
        if count != expected:
            raise ValueError(f"{split}.jsonl read-back count mismatch: {count} != {expected}")
    readback = json.loads(manifest_path.read_text(encoding="utf-8"))
    if readback["total_examples_including_v2_baseline"] != 100_000:
        raise ValueError("Manifest read-back total is not 100,000")
    return readback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.output_dir)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
