#!/usr/bin/env python3
"""Diagnose source-identity and exact model-input leakage across NextAI splits.

This tool is read-only: it never moves, drops or relabels records. It emits
record-level metadata for review before any split repair is accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from audit_nextai_corpus import SPLITS, render_record_text


def _digest(value: str) -> str:
    return hashlib.sha256(" ".join(value.split()).encode("utf-8")).hexdigest()


def _image_fingerprint(row: dict[str, Any]) -> str:
    images = row.get("images") or []
    if not images:
        return ""
    return hashlib.sha256(
        json.dumps(images, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def diagnose(data_dir: Path) -> dict[str, Any]:
    text_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    identity_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    split_counts: dict[str, int] = {}
    for split in SPLITS:
        path = data_dir / f"{split}.jsonl"
        if not path.is_file():
            raise FileNotFoundError(f"Required split missing: {path}")
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{line_number} is not a JSON object")
                count += 1
                text, _schema = render_record_text(row)
                metadata = {
                    "split": split,
                    "line": line_number,
                    "record_id": str(row.get("record_id") or ""),
                    "domain": str(row.get("domain") or "unknown"),
                    "source": str(row.get("source") or "unspecified"),
                    "split_group": str(row.get("split_group") or ""),
                    "source_group_sha256": str(row.get("source_group_sha256") or ""),
                    "image_fingerprint": _image_fingerprint(row),
                }
                text_groups[_digest(text)].append(metadata)
                for key in ("record_id", "split_group", "source_group_sha256"):
                    value = metadata[key]
                    if value:
                        identity_groups[f"{key}:{value}"].append(metadata)
        split_counts[split] = count

    def summarize(groups: dict[str, list[dict[str, Any]]], *, cross_only: bool) -> list[dict[str, Any]]:
        output = []
        for digest, rows in groups.items():
            splits = sorted({row["split"] for row in rows})
            if len(rows) < 2 or (cross_only and len(splits) < 2):
                continue
            output.append({
                "fingerprint": digest,
                "splits": splits,
                "record_count": len(rows),
                "records": rows,
            })
        return sorted(output, key=lambda item: (-len(item["splits"]), -item["record_count"], item["fingerprint"]))

    exact = summarize(text_groups, cross_only=True)
    identities = summarize(identity_groups, cross_only=True)
    within = summarize(text_groups, cross_only=False)
    within = [item for item in within if len(item["splits"]) == 1]
    return {
        "schema_version": "nextai.corpus-leakage-diagnostic.v1",
        "read_only": True,
        "split_counts": split_counts,
        "cross_split_exact_text_groups": exact,
        "cross_split_identity_groups": identities,
        "within_split_duplicate_text_groups": within,
        "summary": {
            "cross_split_exact_text_groups": len(exact),
            "cross_split_identity_groups": len(identities),
            "within_split_duplicate_text_groups": len(within),
            "records_in_cross_split_text_groups": sum(x["record_count"] for x in exact),
            "records_in_cross_split_identity_groups": sum(x["record_count"] for x in identities),
        },
        "note": (
            "This report identifies candidate leakage but does not repair it. "
            "Image fingerprints are recorded because identical text with different images "
            "may represent distinct visual supervision."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = diagnose(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
