#!/usr/bin/env python3
"""Collect split-disjoint native Next BIM/BIMCraft CLI traces and prepare SFT sidecars."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_nextbim_ai_acceptance.py"
SCENARIOS = {"train": ("train-compact", 0.8), "validation": ("validation-standard", 1.0), "test": ("test-expanded", 1.25)}


def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
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
        raise ValueError(f"Unknown Next BIM split: {split}")
    if len(rows) != 2:
        raise ValueError(f"Next BIM {split} must contain exactly two native operation records")
    ids: set[str] = set()
    lineages: set[str] = set()
    operation_count = 0
    prompts: set[str] = set()
    for row in rows:
        record_id = str(row.get("record_id") or "")
        if not record_id or record_id in ids:
            raise ValueError(f"Next BIM {split} records contain a missing or duplicate record ID")
        ids.add(record_id)
        if row.get("schema_version") != "1.0.0" or row.get("application") != "nextbim":
            raise ValueError(f"Next BIM {split} record has the wrong application or schema")
        if row.get("split") != split:
            raise ValueError(f"Next BIM {split} file contains a record labelled {row.get('split')!r}")
        source_id = str((row.get("source") or {}).get("source_id") or "")
        if not source_id:
            raise ValueError(f"Next BIM {split} record has no source lineage")
        expected_scenario = SCENARIOS[split][0]
        if expected_scenario not in source_id or split not in source_id:
            raise ValueError(f"Next BIM {split} record has a source lineage that does not match its scenario")
        lineages.add(source_id)
        prompt = str((row.get("task") or {}).get("prompt") or "").strip()
        if not prompt:
            raise ValueError(f"Next BIM {split} record has no task prompt")
        prompts.add(prompt)
        validation = row.get("validation") or {}
        if validation.get("overall") not in {"passed", "passed_with_warnings"}:
            raise ValueError(f"Next BIM {split} record has no passing validation result")
        if validation.get("round_trip_passed") is not True or validation.get("recompute_passed") is not True:
            raise ValueError(f"Next BIM {split} record lacks save/reopen or recompute evidence")
        native_states = row.get("native_states") or {}
        before = native_states.get("before") or {}
        after = native_states.get("after") or {}
        before_hash = str(before.get("sha256") or "")
        after_hash = str(after.get("sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", before_hash):
            raise ValueError(f"Next BIM {split} record has no valid before-project SHA-256")
        if not re.fullmatch(r"[0-9a-f]{64}", after_hash) or after_hash == before_hash:
            raise ValueError(f"Next BIM {split} record has no distinct valid saved after-project SHA-256")
        operations = row.get("operations")
        if not isinstance(operations, list) or len(operations) != 1:
            raise ValueError(f"Next BIM {split} acceptance record must contain exactly one native wall command")
        operation = operations[0]
        if operation.get("status") != "applied":
            raise ValueError(f"Next BIM {split} record contains a failed command")
        if operation.get("tool") != "wall":
            raise ValueError(f"Next BIM {split} acceptance trace may contain only native wall commands")
        if operation.get("before_state_hash") != before_hash or operation.get("after_state_hash") != after_hash:
            raise ValueError(f"Next BIM {split} operation hashes do not match the native before/after states")
        result = operation.get("result") or {}
        try:
            count_before = int(result.get("wall_count_before"))
            count_after = int(result.get("wall_count_after_reopen"))
            count_delta = int(result.get("count_delta"))
        except (TypeError, ValueError):
            raise ValueError(f"Next BIM {split} wall command has incomplete reopened-count evidence")
        if count_after != count_before + 1 or count_delta != 1:
            raise ValueError(f"Next BIM {split} wall command does not prove exactly one persisted wall")
        checks = validation.get("checks") or []
        increment = next((item for item in checks if item.get("check_id") == "wall_count_increment"), None)
        if not increment or increment.get("status") != "pass":
            raise ValueError(f"Next BIM {split} record lacks a passing wall-count validation check")
        if increment.get("expected") != count_before + 1 or increment.get("actual") != count_after:
            raise ValueError(f"Next BIM {split} validation count does not match the recorded CLI result")
        operation_count += 1
    if len(lineages) != 1:
        raise ValueError(f"Next BIM {split} stage records must share one source lineage")
    if len(prompts) != 2:
        raise ValueError(f"Next BIM {split} stage prompts must be present and distinct")
    return {"records": len(rows), "source_id": next(iter(lineages)), "record_ids": sorted(ids),
            "operation_count": operation_count, "scenario_id": SCENARIOS[split][0], "scenario_scale": SCENARIOS[split][1]}


def validate_source_lineage_separation(reports: dict[str, dict[str, Any]]) -> None:
    seen: set[str] = set()
    for split in ("train", "validation", "test"):
        source_id = str((reports.get(split) or {}).get("source_id") or "")
        if not source_id:
            raise ValueError(f"Missing Next BIM {split} source lineage")
        if source_id in seen:
            raise ValueError("A native BIM project lineage was assigned to more than one split")
        seen.add(source_id)


def collect_trace_files(trace_files: dict[str, Path], output_dir: Path) -> dict[str, Any]:
    if set(trace_files) != set(SCENARIOS):
        raise ValueError("Exactly Next BIM train, validation and test files are required")
    rows_all, reports, ids = [], {}, set()
    for split in ("train","validation","test"):
        path=Path(trace_files[split]).resolve()
        if not path.is_file(): raise FileNotFoundError(f"Missing Next BIM {split} trace: {path}")
        rows=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        report = validate_split_trace_rows(split, rows)
        if ids.intersection(report["record_ids"]):
            raise ValueError("Duplicate Next BIM record ID across data splits")
        ids.update(report["record_ids"])
        reports[split] = {**report, "sha256": sha256_file(path)}
        rows_all.extend(rows)
    validate_source_lineage_separation(reports)
    output_dir.mkdir(parents=True,exist_ok=True)
    raw=output_dir/"native-records.jsonl"
    raw.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows_all),encoding="utf-8")
    for split in ("train","validation","test"):
        (output_dir/f"nextbim-native-{split}.jsonl").write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows_all if row["split"]==split),encoding="utf-8")
    sys.path.insert(0,str(ROOT))
    from training.nextai.prepare_native_sft import prepare
    summary=prepare(raw,output_dir/"sft")
    expected={"train":2,"validation":2,"test":2}
    actual={split:summary.get(split,0) for split in expected}
    if actual!=expected: raise RuntimeError(f"Next BIM SFT did not preserve six records: {actual}")
    if summary.get("quarantine", 0) != 0 or summary.get("source_groups_with_split_leakage", 0) != 0:
        raise RuntimeError(f"Next BIM SFT conversion quarantined records or detected split leakage: {summary}")
    artifact_inventory = {
        "raw_trace": describe_artifact(raw, output_dir, records=len(rows_all)),
        "raw_splits": {
            split: describe_artifact(output_dir / f"nextbim-native-{split}.jsonl", output_dir, records=actual[split])
            for split in ("train", "validation", "test")
        },
        "sft_splits": {
            split: describe_artifact(output_dir / "sft" / f"{split}.jsonl", output_dir, records=actual[split])
            for split in ("train", "validation", "test")
        },
        "sft_quarantine": describe_artifact(
            output_dir / "sft" / "quarantine.jsonl", output_dir,
            records=summary.get("quarantine", 0),
        ),
        "sft_summary": describe_artifact(output_dir / "sft" / "summary.json", output_dir),
    }
    manifest={"schema_version":"nextbim.native-trace-corpus.v1","application":"nextbim","source_revision":"a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b","evidence_level":"L3 native CLI execution + L4 project save/reopen","independent_engineering_validation":"not_claimed","synthetic_acceptance_fixtures":True,"split_record_counts":actual,"splits":reports,"raw_trace_file":raw.name,"raw_trace_sha256":sha256_file(raw),"sft_output_dir":"sft","sft_summary":summary,"artifact_inventory":artifact_inventory,"source_lineages_disjoint":True,"note":"Native BIMCraft wall-command acceptance examples. They test command execution and project persistence; independent geometric and engineering validation is not claimed."}
    (output_dir/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return manifest


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    cli=args.cli.resolve()
    if not cli.is_file(): raise SystemExit(f"Next BIM CLI executable not found: {cli}")
    out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
    files={}
    for split,(scenario,scale) in SCENARIOS.items():
        run_dir=out/"runs"/split; run_dir.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,str(RUNNER),"--cli",str(cli),"--output-dir",str(run_dir),"--split",split,"--scenario-id",scenario,"--scenario-scale",str(scale)]
        print("+"," ".join(cmd),flush=True); subprocess.run(cmd,cwd=Path.cwd(),check=True)
        files[split]=run_dir/"nextbim-ai-native-acceptance-trace.jsonl"
    print(json.dumps(collect_trace_files(files,out),indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
