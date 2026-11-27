#!/usr/bin/env python3
"""Collect split-disjoint native NextCAD acceptance traces and prepare SFT sidecars."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_nextcad_ai_acceptance.py"
SCENARIOS = {"train": ("train-compact", 0.8), "validation": ("validation-standard", 1.0), "test": ("test-expanded", 1.25)}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def describe_artifact(path: Path, output_dir: Path, *, records: int | None = None) -> dict[str, Any]:
    """Return a portable path, byte count and SHA-256 for a collected artifact."""
    resolved = path.resolve()
    root = output_dir.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Expected native trace artifact is missing: {resolved}")
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Native trace artifact escapes the output directory: {resolved}") from exc
    result = {
        "path": relative,
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }
    if records is not None:
        with resolved.open("r", encoding="utf-8") as handle:
            actual_records = sum(1 for line in handle if line.strip())
        if actual_records != records:
            raise ValueError(
                f"Native trace artifact record count mismatch for {relative}: "
                f"expected {records}, found {actual_records}"
            )
        result["records"] = actual_records
    return result


def validate_split_trace_rows(split: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if split not in SCENARIOS:
        raise ValueError(f"Unknown native trace split: {split}")
    if len(rows) != 2:
        raise ValueError(f"NextCAD {split} run must contain exactly two staged operation records")
    record_ids, source_ids, prompts = set(), set(), set()
    operation_count = 0
    for row in rows:
        record_id = str(row.get("record_id") or "")
        if not record_id or record_id in record_ids:
            raise ValueError(f"NextCAD {split} traces contain a missing or duplicate record_id")
        record_ids.add(record_id)
        if row.get("schema_version") != "1.0.0" or row.get("application") != "nextcad":
            raise ValueError(f"NextCAD {split} trace has an unsupported schema or application")
        if row.get("split") != split:
            raise ValueError(f"NextCAD {split} trace contains a record labelled {row.get('split')!r}")
        source_id = str((row.get("source") or {}).get("source_id") or "")
        if not source_id:
            raise ValueError(f"NextCAD {split} trace is missing source lineage")
        expected_scenario = SCENARIOS[split][0]
        if expected_scenario not in source_id or split not in source_id:
            raise ValueError(
                f"NextCAD {split} trace source lineage does not match its scenario"
            )
        source_ids.add(source_id)
        prompts.add(str((row.get("task") or {}).get("prompt") or ""))
        validation = row.get("validation") or {}
        if validation.get("overall") not in {"passed", "passed_with_warnings"}:
            raise ValueError(f"NextCAD {split} trace did not pass native validation")
        if validation.get("round_trip_passed") is not True or validation.get("recompute_passed") is not True:
            raise ValueError(f"NextCAD {split} trace lacks save/reopen or recompute evidence")
        after = (row.get("native_states") or {}).get("after") or {}
        if not re.fullmatch(r"[0-9a-f]{64}", str(after.get("sha256") or "")):
            raise ValueError(f"NextCAD {split} trace lacks a valid saved native after-state SHA-256")
        operations = row.get("operations")
        if not isinstance(operations, list) or not operations or any(op.get("status") != "applied" for op in operations):
            raise ValueError(f"NextCAD {split} trace has missing or failed native operations")
        operation_count += len(operations)
    if len(source_ids) != 1:
        raise ValueError(f"NextCAD {split} stage A/B records must share one source lineage")
    if len(prompts) != 2 or "" in prompts:
        raise ValueError(f"NextCAD {split} stage prompts must be present and distinct")
    return {"records": len(rows), "source_id": next(iter(source_ids)), "record_ids": sorted(record_ids),
            "operation_count": operation_count, "scenario_id": SCENARIOS[split][0], "scenario_scale": SCENARIOS[split][1]}


def validate_source_lineage_separation(split_reports: dict[str, dict[str, Any]]) -> None:
    seen = set()
    for split in ("train", "validation", "test"):
        source_id = str((split_reports.get(split) or {}).get("source_id") or "")
        if not source_id:
            raise ValueError(f"Missing NextCAD {split} source lineage")
        if source_id in seen:
            raise ValueError("A native project lineage was assigned to more than one split")
        seen.add(source_id)


def collect_trace_files(trace_files: dict[str, Path], output_dir: Path) -> dict[str, Any]:
    if set(trace_files) != set(SCENARIOS):
        raise ValueError("Exactly train, validation and test trace files are required")
    all_rows, split_reports, seen_ids = [], {}, set()
    for split in ("train", "validation", "test"):
        path = Path(trace_files[split]).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Missing native NextCAD {split} trace file: {path}")
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        report = validate_split_trace_rows(split, rows)
        if seen_ids.intersection(report["record_ids"]):
            raise ValueError("Duplicate native record IDs occur across data splits")
        seen_ids.update(report["record_ids"])
        report.update({"input_path": str(path), "input_sha256": sha256_file(path)})
        split_reports[split] = report
        all_rows.extend(rows)
    validate_source_lineage_separation(split_reports)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "native-records.jsonl"
    raw_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in all_rows), encoding="utf-8")
    for split in ("train", "validation", "test"):
        (output_dir / f"nextcad-native-{split}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in all_rows if row["split"] == split), encoding="utf-8"
        )
    sys.path.insert(0, str(REPO_ROOT))
    from training.nextai.prepare_native_sft import prepare
    sft_summary = prepare(raw_path, output_dir / "sft")
    expected = {"train": 2, "validation": 2, "test": 2}
    actual = {split: sft_summary.get(split, 0) for split in expected}
    if actual != expected:
        raise RuntimeError(f"Native SFT conversion did not preserve the six traces: {actual}")
    if sft_summary.get("quarantine", 0) != 0 or sft_summary.get("source_groups_with_split_leakage", 0) != 0:
        raise RuntimeError(f"Native SFT conversion quarantined records or detected split leakage: {sft_summary}")
    artifact_inventory = {
        "raw_trace": describe_artifact(raw_path, output_dir, records=len(all_rows)),
        "raw_splits": {
            split: describe_artifact(output_dir / f"nextcad-native-{split}.jsonl", output_dir, records=actual[split])
            for split in ("train", "validation", "test")
        },
        "sft_splits": {
            split: describe_artifact(output_dir / "sft" / f"{split}.jsonl", output_dir, records=actual[split])
            for split in ("train", "validation", "test")
        },
        "sft_quarantine": describe_artifact(
            output_dir / "sft" / "quarantine.jsonl", output_dir,
            records=sft_summary.get("quarantine", 0),
        ),
        "sft_summary": describe_artifact(output_dir / "sft" / "summary.json", output_dir),
    }
    manifest = {
        "schema_version": "nextcad.native-trace-corpus.v1", "application": "nextcad",
        "source_revision": "00cb280454069966a2fb0a8e7dc184c46e7b38b3",
        "evidence_level": "L3 native execution + L4 save/reopen",
        "independent_engineering_validation": "not_claimed", "synthetic_acceptance_fixtures": True,
        "split_record_counts": actual, "splits": split_reports,
        "raw_trace_file": raw_path.name, "raw_trace_sha256": sha256_file(raw_path),
        "sft_output_dir": "sft", "sft_summary": sft_summary,
        "artifact_inventory": artifact_inventory,
        "train_validation_test_source_lineages_are_disjoint": True,
        "note": "Controlled native software-acceptance examples, not broad user projects or independent engineering validation."
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--executable", help="Built FreeCAD/NextCAD GUI executable")
    mode.add_argument("--command-prefix", help='Launcher prefix, e.g. "pixi run freecad"')
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.timeout_seconds < 30:
        parser.error("--timeout-seconds must be at least 30")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_files = {}
    for split, (scenario, scale) in SCENARIOS.items():
        run_dir = output_dir / "runs" / split
        run_dir.mkdir(parents=True, exist_ok=True)
        report_path = run_dir / "acceptance.json"
        cmd = [sys.executable, str(RUNNER), "--timeout-seconds", str(args.timeout_seconds), "--output", str(report_path),
               "--split", split, "--scenario-id", scenario, "--scenario-scale", str(scale)]
        cmd += ["--executable", args.executable] if args.executable else ["--command-prefix", args.command_prefix]
        print("+", " ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=Path.cwd(), check=True)
        trace_files[split] = report_path.with_name("nextcad-ai-native-acceptance-trace.jsonl")
    print(json.dumps(collect_trace_files(trace_files, output_dir), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
