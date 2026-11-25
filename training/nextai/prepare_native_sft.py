#!/usr/bin/env python3
"""Prepare validated NextAI native traces as compact SFT JSONL."""

from __future__ import annotations

import argparse
import json
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = """You are NextAI, an engineering-focused CAD/BIM operator.
Understand the user's design intent and return a compact JSON tool plan for the
specified native application. Use only the exact application-specific tool names
and typed arguments demonstrated in the training example. Preserve units and
explicit dimensions. Never invent missing dimensions, constraints, loads, code
requirements or project facts. If a critical value is missing, put a concise
question in open_questions and do not fabricate a tool call. Do not output
Python, shell commands, hidden reasoning or claims that an operation has already
been executed. The native application performs and validates all operations.

Return one JSON object with: application, request_summary, assumptions,
open_questions, steps, and validation_targets. Each step contains sequence,
tool, tool_schema_version and arguments. Output JSON only."""


def _valid_record(record: dict[str, Any]) -> tuple[bool, str]:
    required = {
        "schema_version", "record_id", "application", "application_version",
        "task", "specification", "native_states", "operations", "validation",
        "source", "privacy", "split",
    }
    missing = sorted(required - record.keys())
    if missing:
        return False, f"missing required fields: {', '.join(missing)}"
    if record["schema_version"] != "1.0.0":
        return False, "unsupported training-record schema version"
    if record["application"] not in {"nextcad", "nextbim"}:
        return False, "unknown application"
    if record["split"] not in {"train", "validation", "test", "quarantine"}:
        return False, "unknown data split"
    source = record["source"]
    privacy = record["privacy"]
    validation = record["validation"]
    if not source.get("terms_reviewed", False):
        return False, "source terms have not been reviewed"
    if source.get("permission_status") not in {"granted", "not_required"}:
        return False, "source permission is not cleared"
    if not source.get("license"):
        return False, "source licence is missing"
    if source.get("source_type") == "user_owned" and not privacy.get("user_consent", False):
        return False, "user-owned project lacks explicit training consent"
    if privacy.get("contains_personal_data", True) and privacy.get("redaction_status") not in {"complete"}:
        return False, "personal data has not been fully redacted"
    if validation.get("overall") not in {"passed", "passed_with_warnings"}:
        return False, "native validation did not pass"
    if validation.get("round_trip_passed") is not True:
        return False, "native save/reopen round-trip did not pass"
    if validation.get("recompute_passed") is not True:
        return False, "native recompute did not pass"
    if any(check.get("status") == "fail" for check in validation.get("checks", [])):
        return False, "one or more native validation checks failed"
    states = record["native_states"]
    after = states.get("after") if isinstance(states, dict) else None
    if not isinstance(after, dict) or not after.get("sha256"):
        return False, "verified native after-state is missing"
    operations = record["operations"]
    if not isinstance(operations, list) or not operations:
        return False, "native operation trace is empty"
    for index, operation in enumerate(operations):
        if operation.get("status") not in {"applied", "read_only"}:
            return False, f"operation {index} is not a successful native action"
        if not operation.get("tool") or not operation.get("tool_schema_version"):
            return False, f"operation {index} lacks a versioned native tool identity"
        if not isinstance(operation.get("arguments"), dict):
            return False, f"operation {index} arguments are not an object"
    if not record["task"].get("prompt"):
        return False, "task prompt is empty"
    return True, ""


def _source_group(record: dict[str, Any]) -> str:
    return f'{record["application"]}:{record["source"].get("source_id", "")}'


def _example(record: dict[str, Any]) -> dict[str, Any]:
    task = record["task"]
    spec = record["specification"]
    states = record["native_states"]
    before = states.get("before") or {}
    after = states["after"]
    context = {
        "application": record["application"],
        "application_version": record["application_version"],
        "adapter_schema_version": record.get("adapter_schema_version", "unknown"),
        "task": {
            "prompt": task["prompt"],
            "task_type": task["task_type"],
            "discipline": task["discipline"],
            "language": task["language"],
        },
        "specification": spec,
        "native_context": {
            "format": after.get("format"),
            "before_state_summary": before.get("state_summary"),
            "current_state_summary": after.get("state_summary"),
        },
    }
    steps = [
        {
            "sequence": op["sequence"],
            "tool": op["tool"],
            "tool_schema_version": op["tool_schema_version"],
            "arguments": op["arguments"],
        }
        for op in record["operations"]
    ]
    targets = [
        check["check_id"]
        for check in record["validation"].get("checks", [])
        if check.get("status") in {"pass", "warning"}
    ]
    target = {
        "application": record["application"],
        "request_summary": task["prompt"],
        "assumptions": spec.get("assumptions", []),
        "open_questions": spec.get("unresolved_questions", []),
        "steps": steps,
        "validation_targets": targets,
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False, sort_keys=True)},
        {"role": "assistant", "content": json.dumps(target, ensure_ascii=False, sort_keys=True)},
    ]
    source = record["source"]
    privacy = record["privacy"]
    source_group_sha256 = hashlib.sha256(_source_group(record).encode("utf-8")).hexdigest()
    source_metadata = {
        "source_type": source.get("source_type"),
        "license": source.get("license"),
        "attribution": source.get("attribution"),
        "permission_status": source.get("permission_status"),
        "terms_reviewed": source.get("terms_reviewed") is True,
        "source_group_sha256": source_group_sha256,
    }
    privacy_metadata = {
        "contains_personal_data": privacy.get("contains_personal_data"),
        "redaction_status": privacy.get("redaction_status"),
        "user_consent": privacy.get("user_consent") is True,
    }
    return {
        "messages": messages,
        "record_id": record["record_id"],
        "application": record["application"],
        "application_version": record["application_version"],
        "adapter_schema_version": record.get("adapter_schema_version", "unknown"),
        "split": record["split"],
        "source": source_metadata,
        "privacy": privacy_metadata,
    }


def prepare(input_path: Path, output_dir: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("record must be a JSON object")
                record_id = str(record.get("record_id", f"line-{line_number}"))
                if record_id in seen_ids:
                    rejected.append({"record_id": record_id, "reason": "duplicate record_id"})
                    continue
                seen_ids.add(record_id)
                ok, reason = _valid_record(record)
                if not ok:
                    rejected.append({"record_id": record_id, "reason": reason})
                    continue
                records.append(record)
            except Exception as exc:
                rejected.append({"record_id": f"line-{line_number}", "reason": str(exc)})

    group_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record["split"] != "quarantine":
            group_splits[_source_group(record)].add(record["split"])
    conflicted_groups = {group for group, splits in group_splits.items() if len(splits) > 1}

    output_dir.mkdir(parents=True, exist_ok=True)
    buckets: dict[str, list[dict[str, Any]]] = {
        "train": [], "validation": [], "test": []
    }
    for record in records:
        group = _source_group(record)
        if record["split"] == "quarantine":
            rejected.append({"record_id": record["record_id"], "reason": "record pre-marked quarantine"})
            continue
        if group in conflicted_groups:
            rejected.append({
                "record_id": record["record_id"],
                "reason": "same source lineage appears in multiple splits",
            })
            continue
        buckets[record["split"]].append(_example(record))

    for split, examples in buckets.items():
        with (output_dir / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for example in examples:
                handle.write(json.dumps(example, ensure_ascii=False) + "\n")
    with (output_dir / "quarantine.jsonl").open("w", encoding="utf-8") as handle:
        for item in rejected:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    summary = {
        "input": str(input_path),
        "train": len(buckets["train"]),
        "validation": len(buckets["validation"]),
        "test": len(buckets["test"]),
        "quarantine": len(rejected),
        "source_groups_with_split_leakage": len(conflicted_groups),
        "test_split_is_not_added_to_training": True,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Native training records JSONL")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.input, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
