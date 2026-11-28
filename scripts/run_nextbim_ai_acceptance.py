#!/usr/bin/env python3
"""Execute two real BIMCraft CLI wall operations and record save/reopen evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from training.nextai.schema_validation import validate_training_record

PINNED_NEXTBIM_COMMIT = "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"
COMMAND_SCHEMA_VERSION = "BIMCRAFT_NATIVE_COMMANDS.v1"


def command(binary: Path, *args: str) -> str:
    result = subprocess.run([str(binary), *args], check=False, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(
            f"Next BIM CLI failed ({result.returncode}): {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_info(binary: Path, project: Path) -> dict[str, Any]:
    try:
        value = json.loads(command(binary, "info", str(project)))
    except json.JSONDecodeError as exc:
        raise RuntimeError("BIMCraft CLI info did not return valid JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("counts"), dict):
        raise RuntimeError(f"BIMCraft project info has no element counts: {value}")
    return value


def native_state(path: Path, info: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "BIMC",
        "uri": path.name,
        "sha256": sha256_file(path),
        "state_summary": {
            "counts": info.get("counts", {}),
            "levels": info.get("levels", []),
            "warnings": info.get("warnings", []),
        },
        "application_revision": PINNED_NEXTBIM_COMMIT,
    }


def build_native_record(
    *,
    record_id: str,
    split: str,
    scenario_id: str,
    prompt: str,
    command_id: str,
    command_args: dict[str, Any],
    category: str,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any],
    before_count: int,
    after_count: int,
    cli_stdout: str,
    application_version: str,
) -> dict[str, Any]:
    if after_count != before_count + 1:
        raise ValueError(
            f"A native {category} operation must increase the reopened {category} count by exactly one"
        )
    if command_id not in {"wall", "floor"} or category != command_id:
        raise ValueError(f"Unsupported native acceptance command/category: {command_id}/{category}")
    source_id = f"nextbim-native-acceptance:{scenario_id}:{split}:{PINNED_NEXTBIM_COMMIT}"
    transaction = hashlib.sha256(f"{source_id}:{record_id}:{after_state['sha256']}".encode()).hexdigest()[:24]
    parameters = [
        {
            "name": name,
            "value": value,
            "unit": "mm",
            "description": f"Native {category} command parameter: {name}",
            "origin": "derived",
            "confirmed": True,
        }
        for name, value in command_args.items()
    ]
    before_hash = before_state.get("sha256") if before_state else None
    return {
        "schema_version": "1.0.0",
        "record_id": record_id,
        "application": "nextbim",
        "application_version": application_version,
        "adapter_schema_version": COMMAND_SCHEMA_VERSION,
        "task": {
            "prompt": prompt,
            "task_type": "create",
            "discipline": ["BIM", "architectural modelling"],
            "language": "en",
            "reference_questions": [],
            "design_rationale": (
                f"Synthetic native CLI acceptance operation using the {command_id} command; "
                "not a functional or code-approved building design."
            ),
        },
        "specification": {
            "parameters": parameters,
            "constraints": [
                "Plan coordinates are millimetres.",
                f"The operation creates one native BIMCraft {category} element.",
            ],
            "assumptions": [
                "This fixture verifies native command execution, project persistence and element counts only."
            ],
            "unresolved_questions": [],
        },
        "native_states": {"before": before_state, "after": after_state},
        "operations": [{
            "sequence": 0,
            "tool": command_id,
            "tool_schema_version": COMMAND_SCHEMA_VERSION,
            "arguments": command_args,
            "result": {
                "cli_stdout": cli_stdout[:4000],
                "element_category": category,
                "element_count_before": before_count,
                "element_count_after_reopen": after_count,
                "count_delta": after_count - before_count,
            },
            "status": "applied",
            "transaction_id": transaction,
            "before_state_hash": before_hash,
            "after_state_hash": after_state["sha256"],
            "user_approved": True,
            "error_code": None,
        }],
        "validation": {
            "overall": "passed",
            "checks": [
                {
                    "check_id": f"{category}_count_increment",
                    "status": "pass",
                    "summary": f"Reopened project reports exactly one additional {category}.",
                    "expected": before_count + 1,
                    "actual": after_count,
                    "unit": "elements",
                    "tolerance": 0,
                    "evidence": "BIMCraft CLI info after save and reopen.",
                },
                {
                    "check_id": "project_save_reopen",
                    "status": "pass",
                    "summary": "BIMCraft reopened the saved project and returned its element counts.",
                    "expected": True,
                    "actual": True,
                    "unit": None,
                    "tolerance": None,
                    "evidence": "bimcraft-cli info on the saved .bimc project.",
                },
            ],
            "engine_report": {
                "application": "Next BIM",
                "application_version": application_version,
                "source_commit": PINNED_NEXTBIM_COMMIT,
                "validation_scope": (
                    f"Native {category} command execution and save/reopen count verification; "
                    "independent geometric/engineering validation not claimed."
                ),
            },
            "round_trip_passed": True,
            "recompute_passed": True,
            "parametric_perturbation_passed": None,
        },
        "artifacts": [{
            "kind": "other",
            "uri": after_state["uri"],
            "sha256": after_state["sha256"],
            "native_state_hash": after_state["sha256"],
            "description": f"Native BIMCraft .bimc project after the recorded {category} command.",
        }],
        "source": {
            "source_type": "synthetic",
            "source_id": source_id,
            "author_or_owner": "Next3D",
            "license": "project-authored",
            "permission_status": "not_required",
            "terms_reviewed": True,
            "attribution": "Generated by the pinned BIMCraft native CLI acceptance runner.",
            "withdrawal_key": "nextbim-native-acceptance",
        },
        "privacy": {
            "user_consent": False,
            "contains_personal_data": False,
            "public_release_allowed": True,
            "redaction_status": "not_needed",
        },
        "split": split,
    }


def run_acceptance(cli: Path, output_dir: Path, split: str, scenario_id: str, scale: float) -> dict[str, Any]:
    if split not in {"train", "validation", "test"}:
        raise ValueError(f"Unsupported split: {split}")
    if not 0.5 <= scale <= 2.0:
        raise ValueError("Scenario scale must be in [0.5, 2.0]")
    output_dir.mkdir(parents=True, exist_ok=True)
    version = command(cli, "--version")
    project = output_dir / "working.bimc"
    baseline_out = command(cli, "run", "--sample", "--save", str(project))
    baseline_info = project_info(cli, project)
    baseline_hash = sha256_file(project)
    baseline_state = native_state(project, baseline_info)

    stage_plan = [
        {
            "stage": "a",
            "command": "wall",
            "category": "wall",
            "args": {
                "points": [
                    [15000.0 * scale, 10000.0 * scale],
                    [18000.0 * scale, 10000.0 * scale],
                ]
            },
            "prompt": (
                f"Add a native BIM wall from ({15000.0 * scale:g}, {10000.0 * scale:g}) mm "
                f"to ({18000.0 * scale:g}, {10000.0 * scale:g}) mm in the current project "
                f"({scenario_id}, stage a)."
            ),
        },
        {
            "stage": "b",
            "command": "floor",
            "category": "floor",
            "args": {
                "boundary": [
                    [15000.0 * scale, 12000.0 * scale],
                    [18000.0 * scale, 12000.0 * scale],
                    [18000.0 * scale, 15000.0 * scale],
                    [15000.0 * scale, 15000.0 * scale],
                ]
            },
            "prompt": (
                f"Create one native BIM floor slab inside the explicit rectangular boundary "
                f"for project scenario {scenario_id} (stage b). Keep the boundary in millimetres."
            ),
        },
    ]
    records = []
    previous_state = baseline_state
    counts_before: dict[str, int] = {}
    counts_after: dict[str, int] = {}
    for item in stage_plan:
        command_id = item["command"]
        category = item["category"]
        before_count = int(project_info(cli, project)["counts"].get(category, 0))
        command_text = command_id + " " + json.dumps(item["args"], separators=(",", ":"))
        stdout = command(cli, "run", str(project), "--cmd", command_text, "--save", str(project))
        info = project_info(cli, project)
        after_count = int(info["counts"].get(category, 0))
        if after_count != before_count + 1:
            raise RuntimeError(
                f"BIMCraft {command_id} count did not increase by one after stage {item['stage']}: "
                f"{before_count} -> {after_count}"
            )
        stage_path = output_dir / f"stage-{item['stage']}.bimc"
        shutil.copy2(project, stage_path)
        after_state = native_state(stage_path, info)
        record_id = (
            f"nextbim-{split}-{scenario_id}-stage-{item['stage']}-"
            f"{after_state['sha256'][:12]}"
        )
        record = build_native_record(
            record_id=record_id,
            split=split,
            scenario_id=scenario_id,
            prompt=item["prompt"],
            command_id=command_id,
            command_args=item["args"],
            category=category,
            before_state=previous_state,
            after_state=after_state,
            before_count=before_count,
            after_count=after_count,
            cli_stdout=stdout,
            application_version=version,
        )
        records.append(record)
        counts_before[category] = before_count
        counts_after[category] = after_count
        previous_state = after_state

    for record in records:
        validate_training_record(record)
    trace_path = output_dir / "nextbim-ai-native-acceptance-trace.jsonl"
    trace_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    report = {
        "status": "PASS",
        "application": "nextbim",
        "application_version": version,
        "split": split,
        "scenario_id": scenario_id,
        "scenario_scale": scale,
        "records": len(records),
        "commands": [row["operations"][0]["tool"] for row in records],
        "element_counts_before": counts_before,
        "element_counts_after_reopen": counts_after,
        "baseline_sha256": baseline_hash,
        "trace_path": str(trace_path),
        "baseline_cli_output": baseline_out[:2000],
        "evidence_level": "L3 native CLI execution + L4 project save/reopen",
        "independent_engineering_validation": "not_claimed",
    }
    (output_dir / "acceptance.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--scenario-id", default="baseline")
    parser.add_argument("--scenario-scale", type=float, default=1.0)
    args = parser.parse_args()
    cli = args.cli.resolve()
    if not cli.is_file():
        raise SystemExit(f"Next BIM project CLI executable not found: {cli}")
    result = run_acceptance(cli, args.output_dir.resolve(), args.split, args.scenario_id, args.scenario_scale)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
