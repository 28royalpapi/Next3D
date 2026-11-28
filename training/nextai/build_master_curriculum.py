#!/usr/bin/env python3
"""Materialize and audit the authored NextAI master curriculum v3."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from nextai_master_curriculum import (
    VERSION,
    SPECS,
    EXAMPLES_PER_SUBJECT,
    make_master_project_curriculum,
    summarize_master_curriculum_splits,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_curriculum(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Mirror prepare_public_corpora.split_synthetic_curriculum exactly."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows, 1):
        group_id = str(row.get("split_group") or row.get("record_id") or f"lesson-{index}")
        grouped.setdefault(group_id, []).append(row)
    result = {"train": [], "validation": [], "test": []}
    for group_index, group in enumerate(grouped.values(), 1):
        explicit = {str(row.get("curriculum_split")) for row in group if row.get("curriculum_split")}
        if explicit:
            if len(explicit) != 1 or next(iter(explicit)) not in result:
                raise ValueError(f"Invalid or conflicting explicit curriculum split for {group[0].get('record_id')}")
            split = next(iter(explicit))
        else:
            bucket = group_index % 10
            split = "test" if bucket == 0 else "validation" if bucket == 1 else "train"
        result[split].extend(group)
    return result


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = make_master_project_curriculum()
    splits = split_curriculum(rows)
    coverage = summarize_master_curriculum_splits(splits)

    if len(rows) != len(SPECS) * EXAMPLES_PER_SUBJECT:
        raise ValueError("Materialized row count does not match curriculum subjects × examples per subject")
    if coverage["by_split"] != {"train": 784, "validation": 98, "test": 98}:
        raise ValueError(f"Unexpected split counts: {coverage['by_split']}")

    all_ids: set[str] = set()
    for split_name in ("train", "validation", "test"):
        split_rows = splits[split_name]
        for row in split_rows:
            rid = row["record_id"]
            if rid in all_ids:
                raise ValueError(f"Record ID appears in more than one split: {rid}")
            all_ids.add(rid)
        write_jsonl(output_dir / f"{split_name}.jsonl", split_rows)

    per_subject = Counter(row["curriculum_subject_id"] for row in rows)
    if len(per_subject) != 98 or any(count != 10 for count in per_subject.values()):
        raise ValueError("Each subject must have exactly ten authored examples")
    split_hashes = {
        f"{split}.jsonl": {
            "records": len(splits[split]),
            "sha256": sha256_file(output_dir / f"{split}.jsonl"),
            "bytes": (output_dir / f"{split}.jsonl").stat().st_size,
        }
        for split in ("train", "validation", "test")
    }
    manifest = {
        "schema_version": "nextai-master-curriculum-manifest.v3",
        "curriculum_version": VERSION,
        "student": "Qwen/Qwen3.5-0.8B",
        "source": "Next3D project-authored curriculum",
        "license": "project-authored",
        "evidence_level": "L0_authored_learning_example",
        "native_execution_claimed": False,
        "subject_count": len(SPECS),
        "examples_per_subject": EXAMPLES_PER_SUBJECT,
        "total_examples": len(rows),
        "by_collection": coverage["by_collection"],
        "by_application": coverage["by_application"],
        "by_domain": coverage["by_domain"],
        "by_stage": coverage["by_stage"],
        "by_training_stage": coverage["by_training_stage"],
        "by_variant": coverage["by_variant"],
        "by_split": coverage["by_split"],
        "by_split_and_variant": coverage["by_split_and_variant"],
        "by_split_and_collection": coverage["by_split_and_collection"],
        "all_subjects_have_ten_examples": True,
        "all_record_ids_unique": len(all_ids) == len(rows),
        "all_normalized_prompts_unique": len({ " ".join(r["prompt"].lower().split()) for r in rows }) == len(rows),
        "native_execution_traces_included": 0,
        "practical_exam_pack_included": False,
        "files": split_hashes,
        "reference_to_previous_verified_analytic_corpus": {
            "artifact": "nextai-250k-analytic-curriculum",
            "known_records": 250000,
            "by_split": {"train": 225091, "validation": 12491, "test": 12418},
            "qwen_train_text_tokens": 129430330,
            "note": "Previously materialized and tokenizer-audited source snapshot. It is counted separately, not merged into these JSONL files."
        },
        "combined_reference_inventory": {
            "analytic_plus_master_curriculum_total": 250980,
            "train_eligible_records": 225875,
            "validation_records": 12589,
            "held_out_test_records": 12516,
            "scope": "250000 previously audited analytic rows plus 980 newly materialized master curriculum rows only; excludes other public-source datasets, local skill packs, capability metadata lessons and real native traces."
        },
        "training_policy": {
            "test_split_used_for_gradient_updates": False,
            "validation_split_used_for_gradient_updates": False,
            "clarification_variants_have_empty_native_write_plan": True,
            "examples_are_not_execution_evidence": True,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Read back the files and manifest so malformed serialization cannot be uploaded.
    readback = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    for split_name in ("train", "validation", "test"):
        path = output_dir / f"{split_name}.jsonl"
        parsed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(parsed) != readback["by_split"][split_name]:
            raise ValueError(f"{split_name} JSONL read-back count mismatch")
    return readback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
