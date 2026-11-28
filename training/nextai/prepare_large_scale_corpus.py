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

NATIVE_COLLECTION_MANIFEST_SPECS = {
    "nextcad": ("nextcad.native-trace-corpus.v1", "00cb280454069966a2fb0a8e7dc184c46e7b38b3"),
    "nextbim": ("nextbim.native-trace-corpus.v1", "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_native_collection_manifest(manifest_path: Path, application: str) -> dict[str, Any]:
    """Verify a collector manifest and every artifact before using its SFT split files."""
    if application not in NATIVE_COLLECTION_MANIFEST_SPECS:
        raise ValueError(f"Unsupported native collection application: {application}")
    path = Path(manifest_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Native {application} collection manifest not found: {path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid native {application} collection manifest JSON: {exc}") from exc
    expected_schema, expected_revision = NATIVE_COLLECTION_MANIFEST_SPECS[application]
    if manifest.get("schema_version") != expected_schema or manifest.get("application") != application:
        raise ValueError(f"Native {application} collection manifest has the wrong schema or application")
    if manifest.get("source_revision") != expected_revision:
        raise ValueError(f"Native {application} collection manifest does not match the pinned source revision")
    expected_evidence_level = (
        "L3 native execution + L4 save/reopen"
        if application == "nextcad"
        else "L3 native CLI execution + L4 project save/reopen"
    )
    if manifest.get("evidence_level") != expected_evidence_level:
        raise ValueError(f"Native {application} collection manifest has an unexpected evidence level")
    if manifest.get("synthetic_acceptance_fixtures") is not True:
        raise ValueError("Native acceptance collector manifest must identify its examples as controlled synthetic fixtures")
    lineage_flag = (
        manifest.get("train_validation_test_source_lineages_are_disjoint")
        if application == "nextcad"
        else manifest.get("source_lineages_disjoint")
    )
    if lineage_flag is not True:
        raise ValueError("Native collection manifest does not certify split-disjoint project lineages")
    if manifest.get("independent_engineering_validation") != "not_claimed":
        raise ValueError("Native collection manifest must state that independent engineering validation is not claimed")
    sft_summary = manifest.get("sft_summary") or {}
    if sft_summary.get("quarantine", 0) != 0 or sft_summary.get("source_groups_with_split_leakage", 0) != 0:
        raise ValueError("Native collection manifest reports quarantined records or split leakage")

    root = path.parent.resolve()
    inventory = manifest.get("artifact_inventory") or {}
    required_inventory = {"raw_trace", "raw_splits", "sft_splits", "sft_quarantine", "sft_summary"}
    if not required_inventory.issubset(inventory):
        raise ValueError("Native collection manifest has an incomplete artifact inventory")

    def check_artifact(item: dict[str, Any], label: str) -> Path:
        if not isinstance(item, dict):
            raise ValueError(f"Native collection manifest artifact {label} is malformed")
        relative = Path(str(item.get("path") or ""))
        if not str(relative) or relative.is_absolute():
            raise ValueError(f"Native collection manifest artifact {label} must use a relative path")
        artifact = (root / relative).resolve()
        if not artifact.is_relative_to(root):
            raise ValueError(f"Native collection manifest artifact {label} escapes its collection directory")
        if not artifact.is_file():
            raise FileNotFoundError(f"Native collection manifest artifact is missing: {artifact}")
        if artifact.stat().st_size != item.get("bytes"):
            raise ValueError(f"Native collection manifest byte size mismatch for {label}")
        if sha256_file(artifact) != item.get("sha256"):
            raise ValueError(f"Native collection manifest SHA-256 mismatch for {label}")
        if "records" in item:
            with artifact.open("r", encoding="utf-8") as handle:
                actual_records = sum(1 for line in handle if line.strip())
            if actual_records != item["records"]:
                raise ValueError(f"Native collection manifest record count mismatch for {label}")
        return artifact

    raw_trace_path = check_artifact(inventory["raw_trace"], "raw_trace")
    for group_name in ("raw_splits", "sft_splits"):
        group = inventory[group_name]
        if not isinstance(group, dict) or set(group) != {"train", "validation", "test"}:
            raise ValueError(f"Native collection manifest {group_name} must contain train/validation/test")
        for split, item in group.items():
            check_artifact(item, f"{group_name}.{split}")
    check_artifact(inventory["sft_quarantine"], "sft_quarantine")
    summary_path = check_artifact(inventory["sft_summary"], "sft_summary")
    try:
        actual_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Native SFT summary artifact is not valid JSON") from exc
    if actual_summary != sft_summary:
        raise ValueError("Native collection manifest SFT summary does not match the hashed summary artifact")

    declared_counts = manifest.get("split_record_counts") or {}
    if set(declared_counts) != {"train", "validation", "test"}:
        raise ValueError("Native collection manifest must declare all three split counts")

    def read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in native artifact {label}:{line_number}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Native artifact {label}:{line_number} is not a JSON object")
                rows.append(row)
        return rows

    raw_rows = read_jsonl(raw_trace_path, "raw_trace")
    raw_ids_by_split: dict[str, set[str]] = {split: set() for split in ("train", "validation", "test")}
    lineages_by_split: dict[str, set[str]] = {split: set() for split in ("train", "validation", "test")}
    all_raw_ids: set[str] = set()
    for index, row in enumerate(raw_rows, 1):
        split = row.get("split")
        if row.get("application") != application or split not in raw_ids_by_split:
            raise ValueError(f"Native raw trace row {index} has the wrong application or split")
        record_id = str(row.get("record_id") or "").strip()
        if not record_id or record_id in all_raw_ids:
            raise ValueError(f"Native {application} raw trace has a missing or duplicate record ID")
        all_raw_ids.add(record_id)
        raw_ids_by_split[split].add(record_id)
        source_id = str((row.get("source") or {}).get("source_id") or "").strip()
        if not source_id:
            raise ValueError(f"Native {application} raw trace row {index} has no source lineage")
        lineages_by_split[split].add(source_id)

    split_reports = manifest.get("splits") or {}
    if not isinstance(split_reports, dict) or set(split_reports) != {"train", "validation", "test"}:
        raise ValueError("Native collection manifest must include train/validation/test lineage reports")
    all_lineages: set[str] = set()
    for split in ("train", "validation", "test"):
        expected_count = declared_counts.get(split)
        raw_item = inventory["raw_splits"][split]
        sft_item = inventory["sft_splits"][split]
        if not isinstance(expected_count, int) or expected_count < 1:
            raise ValueError(f"Native {application} {split} split count must be a positive integer")
        if raw_item.get("records") != expected_count or len(raw_ids_by_split[split]) != expected_count:
            raise ValueError(f"Native {application} {split} raw trace count does not match its collection manifest")
        raw_split_rows = read_jsonl((root / str(raw_item["path"])).resolve(), f"raw_splits.{split}")
        if any(row.get("application") != application or row.get("split") != split for row in raw_split_rows):
            raise ValueError(f"Native {application} raw split artifact {split} contains a wrong app or split row")
        if {str(row.get("record_id") or "") for row in raw_split_rows} != raw_ids_by_split[split]:
            raise ValueError(f"Native {application} raw split artifact {split} does not match raw_trace")
        lineage_report = split_reports[split]
        if not isinstance(lineage_report, dict):
            raise ValueError(f"Native {application} {split} lineage report is malformed")
        expected_scenarios = {
            "train": ("train-compact", 0.8),
            "validation": ("validation-standard", 1.0),
            "test": ("test-expanded", 1.25),
        }
        expected_scenario, expected_scale = expected_scenarios[split]
        if lineage_report.get("scenario_id") != expected_scenario:
            raise ValueError(f"Native {application} {split} lineage report has the wrong scenario ID")
        try:
            actual_scale = float(lineage_report.get("scenario_scale"))
        except (TypeError, ValueError):
            raise ValueError(f"Native {application} {split} lineage report has no valid scenario scale")
        if abs(actual_scale - expected_scale) > 1e-9:
            raise ValueError(f"Native {application} {split} lineage report has the wrong scenario scale")
        if lineage_report.get("records") != expected_count:
            raise ValueError(f"Native {application} {split} lineage report record count is inconsistent")
        if set(lineage_report.get("record_ids") or []) != raw_ids_by_split[split]:
            raise ValueError(f"Native {application} {split} lineage report record IDs do not match raw_trace")
        if lineages_by_split[split] != {lineage_report.get("source_id")}:
            raise ValueError(f"Native {application} {split} lineage report does not match raw project provenance")
        if int(sft_item.get("records", 0)) != expected_count:
            raise ValueError(f"Native {application} {split} SFT count does not match its collection manifest")
        if not lineages_by_split[split].isdisjoint(all_lineages):
            raise ValueError(f"Native {application} project lineage crosses train/validation/test boundaries")
        all_lineages.update(lineages_by_split[split])

    sft_files: dict[str, str] = {}
    all_sft_ids: set[str] = set()
    for split in ("train", "validation", "test"):
        item = inventory["sft_splits"][split]
        artifact = (root / str(item["path"])).resolve()
        sft_ids: set[str] = set()
        for line_number, row in enumerate(read_jsonl(artifact, f"sft_splits.{split}"), 1):
            if row.get("application") != application or row.get("split") != split:
                raise ValueError(f"Native SFT artifact {artifact}:{line_number} has the wrong application or split")
            record_id = str(row.get("record_id") or "").strip()
            if not record_id or record_id in all_sft_ids:
                raise ValueError(f"Native {application} collection has a missing or duplicate SFT record ID")
            sft_ids.add(record_id)
            all_sft_ids.add(record_id)
        if sft_ids != raw_ids_by_split[split]:
            raise ValueError(f"Native {application} {split} SFT IDs do not exactly match accepted raw trace IDs")
        sft_files[split] = str(artifact)

    if all_sft_ids != all_raw_ids:
        raise ValueError(f"Native {application} SFT conversion changed the accepted raw trace record set")

    return {
        "application": application,
        "manifest_path": str(path),
        "manifest_sha256": sha256_file(path),
        "source_revision": expected_revision,
        "split_record_counts": {split: int(declared_counts[split]) for split in ("train", "validation", "test")},
        "verified_sft_files": sft_files,
        "artifact_inventory_verified": True,
    }


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


def analytic_generation_target(cases_per_family: int, source_counts: dict[str, Any]) -> dict[str, int]:
    """Use the generator's actual emitted family count instead of a stale hardcoded count."""
    if cases_per_family < 0:
        raise ValueError("cases_per_family must be non-negative")
    family_count = int(source_counts.get("analytic_engineering_families", 0))
    if family_count < 1 and cases_per_family > 0:
        raise ValueError("The corpus manifest does not report any analytic engineering families.")
    return {
        "analytic_engineering_family_count": family_count,
        "analytic_engineering_cases_per_family": cases_per_family,
        "analytic_engineering_total_target": cases_per_family * family_count,
    }


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
    parser.add_argument("--nextcad-native-manifest", type=Path, help="Verify and ingest all NextCAD SFT splits from a collector manifest.")
    parser.add_argument("--nextbim-native-train", type=Path)
    parser.add_argument("--nextbim-native-validation", type=Path)
    parser.add_argument("--nextbim-native-test", type=Path)
    parser.add_argument("--nextbim-native-manifest", type=Path, help="Verify and ingest all Next BIM SFT splits from a collector manifest.")
    parser.add_argument(
        "--require-native-manifests", action="store_true",
        help="Require both pinned native collector manifests and verify every artifact before corpus construction.",
    )
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

    if args.require_native_manifests and not (args.nextcad_native_manifest and args.nextbim_native_manifest):
        raise ValueError("--require-native-manifests requires both --nextcad-native-manifest and --nextbim-native-manifest")
    native_inputs = {
        "nextcad_native_train": args.nextcad_native_train,
        "nextcad_native_validation": args.nextcad_native_validation,
        "nextcad_native_test": args.nextcad_native_test,
        "nextbim_native_train": args.nextbim_native_train,
        "nextbim_native_validation": args.nextbim_native_validation,
        "nextbim_native_test": args.nextbim_native_test,
    }
    native_collection_manifests: dict[str, dict[str, Any]] = {}
    for application, manifest_arg in (("nextcad", args.nextcad_native_manifest), ("nextbim", args.nextbim_native_manifest)):
        if manifest_arg is None:
            continue
        explicit = [f"{application}_native_{split}" for split in ("train", "validation", "test") if native_inputs.get(f"{application}_native_{split}") is not None]
        if explicit:
            raise ValueError(f"Use either --{application}-native-manifest or the three explicit {application} split files, not both")
        verified = verify_native_collection_manifest(manifest_arg, application)
        native_collection_manifests[application] = verified
        for split, sft_path in verified["verified_sft_files"].items():
            native_inputs[f"{application}_native_{split}"] = Path(sft_path)

    native_trace_summary = inspect_native_trace_inputs(
        native_inputs,
        require_all=args.require_native_traces or args.require_native_manifests,
    )

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
    source_counts = manifest.get("source_counts", {})
    analytic_target = analytic_generation_target(args.analytic_cases_per_domain, source_counts)
    plan = {
        "schema_version": 1,
        "profile": "full-public-source",
        "student": "Qwen/Qwen3.5-0.8B",
        "project_token_target": None,
        "token_target_status": "NOT_CONFIGURED_BY_PROJECT_OWNER",
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
            **analytic_target,
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
        "native_collection_manifests": native_collection_manifests,
        "native_collection_manifests_required": args.require_native_manifests,
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
            "No project token target is configured. Actual text-token counts are measured and "
            "reported from corpus_audit.json; they are not a training prerequisite. Image patch "
            "tokens and chat-template overhead are reported separately."
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
    plan_path = out / "large_scale_training_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
