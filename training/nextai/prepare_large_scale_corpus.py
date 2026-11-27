#!/usr/bin/env python3
"""Build the full available public CAD/BIM corpus for NextAI, not notebook smoke samples."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_DIR = Path(__file__).resolve().parent

NATIVE_TRACE_INPUTS = (
    ("nextcad_native_train", "--nextcad-native-train", "nextcad", "train"),
    ("nextcad_native_validation", "--nextcad-native-validation", "nextcad", "validation"),
    ("nextcad_native_test", "--nextcad-native-test", "nextcad", "test"),
    ("nextbim_native_train", "--nextbim-native-train", "nextbim", "train"),
    ("nextbim_native_validation", "--nextbim-native-validation", "nextbim", "validation"),
    ("nextbim_native_test", "--nextbim-native-test", "nextbim", "test"),
)


def inspect_native_trace_inputs(
    inputs: dict[str, Path | None],
    *,
    require_all: bool = False,
) -> dict[str, dict[str, Any]]:
    """Verify prepared native SFT files and fingerprint each application/split input."""
    summary: dict[str, dict[str, Any]] = {}
    missing = []
    for key, _flag, application, split in NATIVE_TRACE_INPUTS:
        raw_path = inputs.get(key)
        if raw_path is None:
            summary[key] = {"status": "not_provided", "application": application, "split": split, "records": 0}
            if require_all:
                missing.append(key)
            continue

        path = Path(raw_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Native {application} {split} trace file not found: {path}")
        digest = hashlib.sha256()
        record_count = 0
        record_ids: set[str] = set()
        with path.open("rb") as handle:
            for line_number, raw_line in enumerate(handle, 1):
                digest.update(raw_line)
                if not raw_line.strip():
                    continue
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid native trace JSON at {path}:{line_number}: {exc}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Native trace at {path}:{line_number} is not a JSON object")
                if row.get("application") != application:
                    raise ValueError(
                        f"Native trace at {path}:{line_number} belongs to {row.get('application')!r}, "
                        f"expected {application!r}"
                    )
                if row.get("split") != split:
                    raise ValueError(
                        f"Native trace at {path}:{line_number} has split {row.get('split')!r}, "
                        f"expected {split!r}"
                    )
                if not isinstance(row.get("messages"), list) or len(row["messages"]) < 3:
                    raise ValueError(f"Native trace at {path}:{line_number} has no complete SFT conversation")
                evidence = row.get("native_trace_evidence") or {}
                if evidence.get("validation_overall") not in {"passed", "passed_with_warnings"}:
                    raise ValueError(f"Native trace at {path}:{line_number} has no passing native-validation evidence")
                if evidence.get("round_trip_passed") is not True or evidence.get("recompute_passed") is not True:
                    raise ValueError(f"Native trace at {path}:{line_number} has no save/reopen and recompute evidence")
                if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("after_state_sha256") or "")):
                    raise ValueError(f"Native trace at {path}:{line_number} has no verified after-state hash")
                try:
                    operation_count = int(evidence.get("operation_count", 0))
                    applied_count = int(evidence.get("applied_operation_count", 0))
                    read_only_count = int(evidence.get("read_only_operation_count", 0))
                except (TypeError, ValueError):
                    raise ValueError(f"Native trace at {path}:{line_number} has invalid operation counts")
                if operation_count < 1 or applied_count + read_only_count != operation_count:
                    raise ValueError(f"Native trace at {path}:{line_number} has incomplete operation evidence")
                if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("operation_trace_sha256") or "")):
                    raise ValueError(f"Native trace at {path}:{line_number} has no operation trace fingerprint")
                record_id = str(row.get("record_id") or "").strip()
                if not record_id:
                    raise ValueError(f"Native trace at {path}:{line_number} has no record_id")
                if record_id in record_ids:
                    raise ValueError(f"Duplicate native trace record_id {record_id!r} in {path}")
                record_ids.add(record_id)
                record_count += 1

        if require_all and record_count == 0:
            missing.append(key + " (empty)")
        summary[key] = {
            "status": "present" if record_count else "empty",
            "application": application,
            "split": split,
            "path": str(path),
            "records": record_count,
            "sha256": digest.hexdigest(),
        }

    if missing:
        raise ValueError(
            "--require-native-traces needs non-empty prepared native trace files for all six "
            "NextCAD/Next BIM train, validation and held-out test splits. Missing: "
            + ", ".join(missing)
        )
    return summary


def native_trace_command_args(summary: dict[str, dict[str, Any]]) -> list[str]:
    """Forward only verified native trace files into the public-corpus builder."""
    result: list[str] = []
    for key, flag, _application, _split in NATIVE_TRACE_INPUTS:
        item = summary.get(key) or {}
        if item.get("status") in {"present", "empty"} and item.get("path"):
            result.extend([flag, str(item["path"])])
    return result


def run(command: list[str], *, cwd: Path = REPO_ROOT) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def build_capability_census_command(
    output_dir: Path,
    *,
    runtime_report: Path | None = None,
    require_runtime: bool = False,
) -> list[str]:
    """Build the pinned census command, optionally using a live NextCAD runtime capture."""
    if require_runtime and runtime_report is None:
        raise ValueError("--require-nextcad-runtime requires --nextcad-runtime-report")
    command = [
        sys.executable, str(TRAINING_DIR / "capability_census.py"),
        "--bim-catalog", str(REPO_ROOT / "docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json"),
        "--nextcad-source-index", str(REPO_ROOT / "docs/next-ai/catalogs/NEXTCAD_WORKBENCH_SOURCE_INDEX.v1.json"),
        "--expected-nextcad-commit", "00cb280454069966a2fb0a8e7dc184c46e7b38b3",
        "--expected-nextbim-commit", "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b",
        "--output-dir", str(output_dir),
    ]
    if runtime_report is not None:
        runtime_path = Path(runtime_report).resolve()
        if not runtime_path.is_file():
            raise FileNotFoundError(f"NextCAD runtime census report does not exist: {runtime_path}")
        command += ["--nextcad-runtime-report", str(runtime_path)]
    if require_runtime:
        command.append("--require-nextcad-runtime")
    return command


def capability_census_summary(census_path: Path) -> dict[str, Any]:
    """Expose source/runtime coverage honestly in the large-scale build plan."""
    census = json.loads(census_path.read_text(encoding="utf-8"))
    if census.get("schema") != "nextai.capability_census.v1":
        raise ValueError("Capability census has an unexpected schema.")
    counts = census.get("counts") or {}
    sources = census.get("sources") or {}
    nextcad = sources.get("nextcad") or {}
    runtime_captured = counts.get("nextcad_runtime_census_complete") is True
    return {
        "nextcad_runtime_capture": nextcad.get("runtime_capture", "not_captured"),
        "nextcad_source_modules": counts.get("nextcad_source_modules", 0),
        "nextcad_runtime_commands": counts.get("nextcad_runtime_commands", 0),
        "nextcad_runtime_api_modules": counts.get("nextcad_runtime_api_modules", 0),
        "nextcad_runtime_api_members": counts.get("nextcad_runtime_api_members", 0),
        "nextcad_runtime_census_complete": runtime_captured,
        "nextcad_python_api_enumeration_scope": nextcad.get("python_api_enumeration_scope"),
        "nextbim_registered_commands": counts.get("nextbim_registered_commands", 0),
        "total_discovered_capabilities": counts.get("total_discovered_capabilities", 0),
        "skill_obligations": counts.get("skill_obligations", 0),
        "skill_obligations_are_training_examples": False,
        "native_mastery_claimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--cad-train", type=int, default=85000)
    parser.add_argument("--cad-validation", type=int, default=10000)
    parser.add_argument("--cad-test", type=int, default=10000)
    parser.add_argument("--bim-train", type=int, default=115000)
    parser.add_argument("--bim-validation", type=int, default=13000)
    parser.add_argument("--ifcqa-train", type=int, default=10000)
    parser.add_argument("--ifcqa-test", type=int, default=4000)
    parser.add_argument("--buildeng-records", type=int, default=145117)
    parser.add_argument("--analytic-cases-per-domain", type=int, default=10000)
    parser.add_argument("--mixed-train-cap", type=int, default=700000)
    parser.add_argument("--validation-cap", type=int, default=60000)
    parser.add_argument("--test-cap", type=int, default=50000)
    parser.add_argument("--swiss-dwellings-dir", type=Path)
    parser.add_argument("--ifc-model-corpus-dir", type=Path)
    parser.add_argument("--nextcad-native-train", type=Path)
    parser.add_argument("--nextcad-native-validation", type=Path)
    parser.add_argument("--nextcad-native-test", type=Path)
    parser.add_argument("--nextbim-native-train", type=Path)
    parser.add_argument("--nextbim-native-validation", type=Path)
    parser.add_argument("--nextbim-native-test", type=Path)
    parser.add_argument(
        "--require-native-traces", action="store_true",
        help="Require non-empty validated NextCAD and Next BIM native traces in all train/validation/test splits.",
    )
    parser.add_argument(
        "--nextcad-runtime-report", type=Path,
        help="JSON report emitted by discover_nextcad_runtime.FCMacro inside the pinned NextCAD runtime.",
    )
    parser.add_argument(
        "--require-nextcad-runtime", action="store_true",
        help="Refuse to proceed unless the live NextCAD command registry/API census is captured.",
    )
    parser.add_argument("--skip-capability-census", action="store_true")
    parser.add_argument("--skip-token-audit", action="store_true")
    parser.add_argument("--tokenizer", default="Qwen/Qwen3.5-0.8B")
    args = parser.parse_args()

    limits = (
        args.cad_train, args.cad_validation, args.cad_test,
        args.bim_train, args.bim_validation, args.ifcqa_train, args.ifcqa_test,
        args.buildeng_records, args.analytic_cases_per_domain,
        args.mixed_train_cap, args.validation_cap, args.test_cap,
    )
    if any(value < 0 for value in limits):
        parser.error("All source and split limits must be non-negative.")
    if args.mixed_train_cap == 0 or args.validation_cap == 0 or args.test_cap == 0:
        parser.error("Mixed train, validation and test caps must be positive.")
    if args.require_nextcad_runtime and not args.nextcad_runtime_report and not args.skip_capability_census:
        parser.error("--require-nextcad-runtime requires --nextcad-runtime-report")
    if args.skip_capability_census and args.nextcad_runtime_report:
        parser.error("--nextcad-runtime-report cannot be used with --skip-capability-census")

    native_trace_summary = inspect_native_trace_inputs({
        "nextcad_native_train": args.nextcad_native_train,
        "nextcad_native_validation": args.nextcad_native_validation,
        "nextcad_native_test": args.nextcad_native_test,
        "nextbim_native_train": args.nextbim_native_train,
        "nextbim_native_validation": args.nextbim_native_validation,
        "nextbim_native_test": args.nextbim_native_test,
    }, require_all=args.require_native_traces)

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    census_path = out / "capability-census.json"

    if not args.skip_capability_census:
        census_command = build_capability_census_command(
            out / "capability-census",
            runtime_report=args.nextcad_runtime_report,
            require_runtime=args.require_nextcad_runtime,
        )
        run(census_command)
        census_path = out / "capability-census" / "capability-census.json"
    else:
        candidates = [
            out / "capability-census" / "capability-census.json",
            out / "capability-census.json",
        ]
        census_path = next((path for path in candidates if path.is_file()), None)
        if census_path is None:
            raise FileNotFoundError("--skip-capability-census requires an existing capability-census.json")

    census_summary = capability_census_summary(census_path)
    if args.require_nextcad_runtime and not census_summary["nextcad_runtime_census_complete"]:
        raise RuntimeError(
            "A live NextCAD runtime report is required, but the selected capability census "
            "does not contain one. Run discover_nextcad_runtime.FCMacro inside the pinned "
            "NextCAD GUI and pass its nextcad-runtime.json report."
        )

    command = [
        sys.executable, str(TRAINING_DIR / "prepare_public_corpora.py"),
        "--output-dir", str(out / "corpus"),
        "--max-cad-train", str(args.cad_train),
        "--max-cad-validation", str(args.cad_validation),
        "--max-cad-test", str(args.cad_test),
        "--max-bim-train", str(args.bim_train),
        "--max-bim-validation", str(args.bim_validation),
        "--max-ifcqa-train", str(args.ifcqa_train),
        "--max-ifcqa-test", str(args.ifcqa_test),
        "--max-buildeng-records", str(args.buildeng_records),
        "--analytic-cases-per-domain", str(args.analytic_cases_per_domain),
        "--max-mixed-train", str(args.mixed_train_cap),
        "--max-validation", str(args.validation_cap),
        "--max-test", str(args.test_cap),
        "--capability-census", str(census_path),
        "--seed", str(args.seed),
    ]
    if args.swiss_dwellings_dir:
        command += ["--swiss-dwellings-dir", str(args.swiss_dwellings_dir.resolve())]
    if args.ifc_model_corpus_dir:
        command += ["--ifc-model-corpus-dir", str(args.ifc_model_corpus_dir.resolve())]
    command += native_trace_command_args(native_trace_summary)
    run(command)

    manifest_path = out / "corpus" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan = {
        "schema_version": 1,
        "profile": "full-public-source",
        "student": "Qwen/Qwen3.5-0.8B",
        "target_train_text_tokens": 400_000_000,
        "token_target_is_a_goal_not_a_claim": True,
        "source_limits": {
            "cad_train_source_rows": args.cad_train,
            "cad_validation_source_rows": args.cad_validation,
            "cad_test_source_rows": args.cad_test,
            "bim_train_source_rows": args.bim_train,
            "bim_validation_source_rows": args.bim_validation,
            "ifcqa_train_source_rows": args.ifcqa_train,
            "ifcqa_test_source_rows": args.ifcqa_test,
            "buildeng_source_rows": args.buildeng_records,
            "analytic_cases_per_domain": args.analytic_cases_per_domain,
            "analytic_engineering_total_target": args.analytic_cases_per_domain * 17,
            "mixed_train_cap": args.mixed_train_cap,
            "validation_cap": args.validation_cap,
            "test_cap": args.test_cap,
        },
        "source_counts": manifest.get("source_counts", {}),
        "records": {
            "train": manifest.get("train_records", 0),
            "validation": manifest.get("validation_records", 0),
            "test": manifest.get("test_records", 0),
            "quarantined": manifest.get("quarantined_rows", 0),
        },
        "training_domain_counts": manifest.get("training_domain_counts", {}),
        "capability_census_summary": census_summary,
        "native_execution_evidence_inputs": native_trace_summary,
        "native_execution_evidence_record_counts": {
            key: item.get("records", 0) for key, item in native_trace_summary.items()
        },
        "requires_native_traces_for_full_execution_training": True,
        "requires_live_nextcad_runtime_for_full_native_coverage": True,
        "analytic_engineering_split_counts": {
            "train": manifest.get("source_counts", {}).get("analytic_engineering_train", 0),
            "validation": manifest.get("source_counts", {}).get("analytic_engineering_validation", 0),
            "test": manifest.get("source_counts", {}).get("analytic_engineering_test", 0),
            "families": manifest.get("source_counts", {}).get("analytic_engineering_families", 0),
        },
        "capability_census": str(census_path),
        "corpus_dir": str(out / "corpus"),
        "requires_token_audit_before_gpu": True,
        "requires_native_trace_validation_before_claiming_native_mastery": True,
        "note": (
            "400M is a target, not an achieved number. Actual text tokens must be read "
            "from corpus_audit.json; image patch tokens and chat-template overhead are separate."
        ),
    }
    if not args.skip_token_audit:
        audit_command = [
            sys.executable, str(TRAINING_DIR / "audit_nextai_corpus.py"),
            "--data-dir", str(out / "corpus"),
            "--tokenizer", args.tokenizer,
            "--output", str(out / "corpus" / "corpus_audit.json"),
        ]
        run(audit_command)
        audit = json.loads((out / "corpus" / "corpus_audit.json").read_text(encoding="utf-8"))
        plan["token_audit"] = {
            "status": audit.get("status"),
            "train_text_tokens": audit.get("train_text_tokens"),
            "validation_text_tokens": audit.get("validation_text_tokens"),
            "held_out_test_text_tokens": audit.get("held_out_test_text_tokens"),
            "image_files_total": audit.get("image_files_total"),
            "image_bytes_total": audit.get("image_bytes_total"),
        }
        plan["target_met"] = int(audit.get("train_text_tokens", 0)) >= int(plan["target_train_text_tokens"])
    plan_path = out / "large_scale_training_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
