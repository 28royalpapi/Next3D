#!/usr/bin/env python3
"""Build version-pinned NextCAD/Next BIM capability lessons and local skill sidecars.

The output is deliberately L0 metadata/skill knowledge. It is not a native
execution trace corpus and cannot certify capability mastery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TRAINING = ROOT / "training" / "nextai"
sys.path.insert(0, str(TRAINING))

from capability_census import build_census, write_outputs  # noqa: E402
import prepare_public_corpora as curriculum  # noqa: E402

BIM_CATALOG = ROOT / "docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json"
NEXTCAD_SOURCE_INDEX = ROOT / "docs/next-ai/catalogs/NEXTCAD_WORKBENCH_SOURCE_INDEX.v1.json"
EXPECTED_NEXTCAD_COMMIT = "00cb280454069966a2fb0a8e7dc184c46e7b38b3"
EXPECTED_NEXTBIM_COMMIT = "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"


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


def _assign_stable_skill_ids(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        name = str(row.get("skill_name") or "").strip()
        section = str(row.get("skill_section") or "").strip()
        if not name or not section:
            raise ValueError("A local skill lesson requires its skill name and section.")
        identity = hashlib.sha256(f"{name}\0{section}".encode("utf-8")).hexdigest()[:20]
        row["record_id"] = f"nextai-local-skill-{identity}"
        row["record_type"] = "authored_local_skill_knowledge_not_native_execution"


def _mark_split(rows: list[dict[str, Any]], split: str) -> None:
    for row in rows:
        row["curriculum_split"] = split
        row["data_split"] = split


def build(
    output_dir: Path,
    *,
    nextcad_runtime_report: Path | None = None,
    require_nextcad_runtime: bool = False,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if require_nextcad_runtime and nextcad_runtime_report is None:
        raise ValueError("--require-nextcad-runtime needs a live NextCAD runtime report.")

    census, obligations = build_census(
        BIM_CATALOG,
        NEXTCAD_SOURCE_INDEX,
        nextcad_runtime_report,
        EXPECTED_NEXTCAD_COMMIT,
        EXPECTED_NEXTBIM_COMMIT,
    )
    census_summary = write_outputs(census, obligations, output_dir / "census")
    census_path = output_dir / "census" / "capability-census.json"

    capability_rows = curriculum.make_capability_knowledge_curriculum(census_path)
    skill_rows = curriculum.make_local_skill_curriculum()
    _assign_stable_skill_ids(skill_rows)

    capability_by_id = Counter(row["capability_id"] for row in capability_rows)
    capability_types = Counter(row["capability_type"] for row in capability_rows)
    capability_apps = Counter(row["application"] for row in capability_rows)
    capability_dimensions = Counter(row["learning_dimension"] for row in capability_rows)
    capability_evidence = Counter(row["evidence_level"] for row in capability_rows)

    expected_capability_rows = 0
    expected_by_type: Counter[str] = Counter()
    for capability in census["capabilities"]:
        kind = capability.get("capability_type")
        if kind in {"native_command", "native_gui_command", "native_api_member"}:
            expected_capability_rows += 10
            expected_by_type[kind] += 10
        elif kind == "workbench_or_module" and capability.get("application") == "nextcad":
            expected_capability_rows += len(curriculum.NEXTCAD_MODULE_SKILL_DIMENSIONS)
            expected_by_type[kind] += len(curriculum.NEXTCAD_MODULE_SKILL_DIMENSIONS)
    if len(capability_rows) != expected_capability_rows:
        raise ValueError(
            f"Capability lesson count mismatch: expected {expected_capability_rows}, found {len(capability_rows)}"
        )
    if dict(capability_types) != dict(expected_by_type):
        raise ValueError(f"Capability lesson type counts differ from expected: {capability_types} != {expected_by_type}")
    if len(capability_by_id) != len(census["capabilities"]):
        raise ValueError("At least one discovered capability has no authored metadata lessons.")
    for capability in census["capabilities"]:
        cid = capability["capability_id"]
        expected_per_capability = (
            len(curriculum.NEXTCAD_MODULE_SKILL_DIMENSIONS)
            if capability["capability_type"] == "workbench_or_module"
            else 10
        )
        if capability_by_id[cid] != expected_per_capability:
            raise ValueError(f"{cid} has {capability_by_id[cid]} lessons; expected {expected_per_capability}")

    capability_splits = curriculum.split_synthetic_curriculum(capability_rows)
    skill_splits = curriculum.split_synthetic_curriculum(skill_rows)
    combined = {name: [] for name in ("train", "validation", "test")}
    for split in ("train", "validation", "test"):
        _mark_split(capability_splits[split], split)
        _mark_split(skill_splits[split], split)
        combined[split] = capability_splits[split] + skill_splits[split]
        write_jsonl(output_dir / f"capability_knowledge_{split}.jsonl", capability_splits[split])
        write_jsonl(output_dir / f"local_skills_{split}.jsonl", skill_splits[split])
        write_jsonl(output_dir / f"{split}.jsonl", combined[split])

    # Verify split-group isolation and global record identity before publishing.
    group_to_split: dict[str, str] = {}
    all_ids: set[str] = set()
    for split, rows in combined.items():
        for row in rows:
            record_id = str(row.get("record_id") or "")
            if not record_id or record_id in all_ids:
                raise ValueError(f"Missing or duplicate capability/skill record ID: {record_id!r}")
            all_ids.add(record_id)
            group = str(row.get("split_group") or record_id)
            prior = group_to_split.setdefault(group, split)
            if prior != split:
                raise ValueError(f"Capability/skill group leakage: {group} appears in {prior} and {split}")

    # Obligations remain separate: they are coverage requirements, not training examples.
    obligation_path = output_dir / "skill-obligations.jsonl"
    write_jsonl(obligation_path, obligations)
    files = {}
    for split in ("train", "validation", "test"):
        for prefix, rows in (
            ("", combined[split]),
            ("capability_knowledge_", capability_splits[split]),
            ("local_skills_", skill_splits[split]),
        ):
            filename = f"{prefix}{split}.jsonl"
            file_path = output_dir / filename
            with file_path.open("r", encoding="utf-8") as handle:
                readback_count = sum(1 for line in handle if line.strip())
            if readback_count != len(rows):
                raise ValueError(f"{filename} read-back count mismatch")
            files[filename] = {
                "records": len(rows),
                "bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
    files[obligation_path.name] = {
        "records": len(obligations),
        "bytes": obligation_path.stat().st_size,
        "sha256": sha256_file(obligation_path),
    }

    runtime_complete = bool(census["counts"]["nextcad_runtime_census_complete"])
    nextcad_runtime_commands = int(census["counts"]["nextcad_runtime_commands"])
    nextcad_api_members = int(census["counts"]["nextcad_runtime_api_members"])
    nextcad_source_modules = int(census["counts"]["nextcad_source_modules"])
    nextbim_commands = int(census["counts"]["nextbim_registered_commands"])
    report = {
        "schema_version": "nextai.capability-learning-curriculum.v1",
        "source": "pinned native capability metadata and local project-authored skill files",
        "source_commits": {
            "nextcad": EXPECTED_NEXTCAD_COMMIT,
            "nextbim": EXPECTED_NEXTBIM_COMMIT,
        },
        "nextcad_runtime_census_complete": runtime_complete,
        "nextcad_source_modules": nextcad_source_modules,
        "nextcad_runtime_commands": nextcad_runtime_commands,
        "nextcad_runtime_api_members": nextcad_api_members,
        "nextbim_registered_commands": nextbim_commands,
        "capability_l0_lessons": len(capability_rows),
        "capability_lessons_by_application": dict(sorted(capability_apps.items())),
        "capability_lessons_by_type": dict(sorted(capability_types.items())),
        "capability_lessons_by_dimension": dict(sorted(capability_dimensions.items())),
        "capability_lesson_evidence_levels": dict(sorted(capability_evidence.items())),
        "bim_command_obligations_not_training_examples": len(
            [row for row in obligations if row["application"] == "nextbim"]
        ),
        "nextcad_runtime_obligations_not_training_examples": len(
            [row for row in obligations if row["application"] == "nextcad"]
        ),
        "nextcad_workbench_module_lessons": capability_types.get("workbench_or_module", 0),
        "local_skill_l0_lessons": len(skill_rows),
        "local_skill_count": len({row.get("skill_name") for row in skill_rows}),
        "by_split": {
            split: {
                "capability_knowledge": len(capability_splits[split]),
                "local_skills": len(skill_splits[split]),
                "combined": len(combined[split]),
            }
            for split in ("train", "validation", "test")
        },
        "evidence_boundary": {
            "capability_and_skill_lessons_are_l0": True,
            "skill_obligations_are_training_examples": False,
            "native_execution_records_in_this_artifact": 0,
            "professional_engineering_approvals_claimed": 0,
            "mastery_claimed": False,
        },
        "fine_tuning_readiness": "NOT_READY_FOR_FULL_OPERATOR_FINETUNING",
        "readiness_blockers": [
            *([] if runtime_complete else [
                "NextCAD live GUI command/API runtime census has not been captured; the 32-module source index is not a command inventory."
            ]),
            "Pinned command metadata lessons are L0 knowledge only; exact live schemas and reviewed native AI adapters remain separate requirements.",
            "This artifact contains no native L3 execution, L4 save/reopen or L5 independent validation traces.",
            "The complete merged CAD/BIM/engineering corpus still requires its own build, tokenizer audit and split/leakage review.",
        ],
        "files": files,
        "counts": {
            **census_summary,
            "capability_knowledge_l0": len(capability_rows),
            "local_skill_l0": len(skill_rows),
            "combined_l0": sum(len(rows) for rows in combined.values()),
        },
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Read back the public manifest to ensure it is valid and count-complete.
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if loaded["fine_tuning_readiness"] != "NOT_READY_FOR_FULL_OPERATOR_FINETUNING":
        raise ValueError("Capability corpus must not claim full operator fine-tuning readiness.")
    return loaded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--nextcad-runtime-report", type=Path)
    parser.add_argument("--require-nextcad-runtime", action="store_true")
    args = parser.parse_args()
    manifest = build(
        args.output_dir,
        nextcad_runtime_report=args.nextcad_runtime_report,
        require_nextcad_runtime=args.require_nextcad_runtime,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
