#!/usr/bin/env python3
"""Build a pinned NextCAD/Next BIM capability census and student skill map."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
DIMENSIONS = {
    "recognition": "Recognise the capability and know when it is appropriate.",
    "inputs_and_units": "Understand its parameters, units, defaults, constraints and effects.",
    "preconditions": "Inspect the document, objects, references and required preconditions.",
    "planning": "Place it in a correct ordered workflow and preserve dependencies.",
    "execution": "Select the exact native capability and supply valid arguments.",
    "verification": "Inspect native postconditions and prove the intended change.",
    "revision": "Revise existing objects in place while preserving identity and dependencies.",
    "failure_recovery": "Handle invalid inputs, failed recompute, rollback, undo and repair.",
    "composition": "Compose this capability with other operations for new projects and unusual requests.",
    "limitations": "Identify unsupported behaviour and avoid claims beyond the evidence."
}


class CensusError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CensusError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CensusError(f"{path} root must be a JSON object")
    return value


def unique_rows(value: Any, key: str, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise CensusError(f"{label} must be an array")
    seen: set[str] = set()
    rows = []
    for index, row in enumerate(value):
        if not isinstance(row, dict) or not isinstance(row.get(key), str) or not row[key].strip():
            raise CensusError(f"{label}[{index}] requires a non-empty {key}")
        identity = row[key].strip()
        if identity in seen:
            raise CensusError(f"Duplicate {key} in {label}: {identity}")
        seen.add(identity)
        rows.append(row)
    return rows


def load_bim_catalog(path: Path, expected_commit: str | None = None):
    data = read_json(path)
    if data.get("application") != "nextbim" or data.get("schema_version") != VERSION:
        raise CensusError("BIM catalogue must be nextbim schema 1.0.0")
    commit = data.get("upstream_commit")
    if not commit or (expected_commit and commit != expected_commit):
        raise CensusError(f"BIM source commit mismatch: {commit!r}")
    rows = unique_rows(data.get("commands"), "id", "BIM commands")
    if len(rows) != data.get("command_count"):
        raise CensusError(f"BIM command_count says {data.get('command_count')}, found {len(rows)}")
    capabilities = []
    for row in rows:
        if not row.get("label") or not row.get("registration_kind"):
            raise CensusError(f"BIM command {row['id']} lacks label or registration kind")
        capabilities.append({
            "application": "nextbim",
            "capability_id": "nextbim.command." + row["id"],
            "native_id": row["id"],
            "name": row["label"],
            "capability_type": "native_command",
            "source_evidence": "pinned_native_command_registration",
            "source_commit": commit,
            "source_path": data.get("source_path"),
            "registration_kind": row["registration_kind"],
            "aliases": row.get("aliases") or [],
            "parameter_contract": row.get("parameters") or "",
            "undoable": row.get("undoable"),
            "file_effect": row.get("file_effect") or "none",
            "menu": row.get("menu"),
            "runtime_status": "registered_in_pinned_source",
            "assistant_surface": "list_commands_and_execute"
        })
    return data, capabilities


def load_nextcad_source_index(path: Path, expected_commit: str | None = None):
    data = read_json(path)
    if data.get("application") != "nextcad" or data.get("schema_version") != VERSION:
        raise CensusError("NextCAD source index must be nextcad schema 1.0.0")
    commit = data.get("upstream_commit")
    if not commit or (expected_commit and commit != expected_commit):
        raise CensusError(f"NextCAD source commit mismatch: {commit!r}")
    rows = unique_rows(data.get("modules"), "module", "NextCAD modules")
    if len(rows) != data.get("module_count"):
        raise CensusError(f"NextCAD module_count says {data.get('module_count')}, found {len(rows)}")
    capabilities = []
    for row in rows:
        capabilities.append({
            "application": "nextcad",
            "capability_id": "nextcad.workbench." + row["module"],
            "native_id": row["module"],
            "name": row["module"],
            "capability_type": "workbench_or_module",
            "source_evidence": "pinned_source_tree_index",
            "source_commit": commit,
            "source_path": row.get("source_path"),
            "source_present": row.get("source_present"),
            "runtime_status": row.get("runtime_status", "not_yet_verified"),
            "ai_discovery_rule": row.get("ai_discovery_rule"),
            "mastery_status": "not_assessed"
        })

    api_modules = unique_rows(runtime.get("python_api_modules") or [], "name", "NextCAD Python API modules")
    api_capabilities = []
    for api_module in api_modules:
        members = unique_rows(api_module.get("public_members") or [], "name",
                              "NextCAD API members in " + api_module["name"])
        for member in members:
            if member.get("kind") not in ("callable", "class"):
                continue
            api_capabilities.append({
                "application": "nextcad",
                "capability_id": "nextcad.api." + api_module["name"] + "." + member["name"],
                "native_id": api_module["name"] + "." + member["name"],
                "name": member["name"],
                "capability_type": "native_api_member",
                "source_evidence": "live_imported_python_api",
                "source_commit": expected_commit,
                "application_version": data.get("application_version"),
                "runtime_status": "public_api_member_discovered",
                "module": api_module["name"],
                "module_file": api_module.get("module_file"),
                "member_kind": member.get("kind"),
                "documentation": member.get("documentation"),
                "agent_tool_status": "requires_reviewed_typed_adapter",
                "mastery_status": "not_assessed"
            })
    return data, capabilities, api_capabilities


def load_nextcad_runtime(path: Path, expected_commit: str):
    data = read_json(path)
    if data.get("schema_version") != VERSION or data.get("application") != "nextcad":
        raise CensusError("NextCAD runtime report must be schema 1.0.0 / nextcad")
    if data.get("upstream_commit") != expected_commit:
        raise CensusError("NextCAD runtime report does not match the pinned source commit")
    runtime = data.get("runtime_inventory")
    if not isinstance(runtime, dict) or runtime.get("global_command_registry_enumerated") is not True:
        raise CensusError("NextCAD runtime report does not prove global command enumeration")
    workbenches = unique_rows(runtime.get("workbenches"), "id", "NextCAD runtime workbenches")
    commands = unique_rows(runtime.get("commands"), "id", "NextCAD runtime commands")
    wb_ids = {row["id"] for row in workbenches}
    command_ids = {row["id"] for row in commands}
    for wb in workbenches:
        references = wb.get("command_ids") or []
        if not isinstance(references, list) or set(references) - command_ids:
            raise CensusError(f"Workbench {wb['id']} refers to unknown command IDs")
    capabilities = []
    for row in commands:
        workbench_ids = [item for item in row.get("workbenches") or [] if item in wb_ids]
        capabilities.append({
            "application": "nextcad",
            "capability_id": "nextcad.command." + row["id"],
            "native_id": row["id"],
            "name": row.get("menu_text") or row["id"],
            "capability_type": "native_gui_command",
            "source_evidence": "live_nextcad_command_registry",
            "source_commit": expected_commit,
            "application_version": data.get("application_version"),
            "runtime_status": "discovered_in_running_application",
            "workbenches": workbench_ids,
            "menu_text": row.get("menu_text"),
            "tooltip": row.get("tooltip"),
            "status_tip": row.get("status_tip"),
            "whats_this": row.get("whats_this"),
            "accelerator": row.get("accelerator"),
            "icon": row.get("icon"),
            "command_class": row.get("command_class"),
            "is_checkable": row.get("is_checkable"),
            "is_active_at_census": row.get("is_active_at_census"),
            "ui_contexts": row.get("ui_contexts") or [],
            "agent_tool_status": "requires_reviewed_typed_adapter",
            "mastery_status": "not_assessed"
        })
    return data, capabilities


def build_census(bim_path: Path, cad_index_path: Path,
                 cad_runtime_path: Path | None = None,
                 expected_cad_commit: str | None = None,
                 expected_bim_commit: str | None = None):
    bim_data, bim_caps = load_bim_catalog(bim_path, expected_bim_commit)
    cad_data, cad_modules = load_nextcad_source_index(cad_index_path, expected_cad_commit)
    cad_commands = []
    cad_api_members = []
    runtime_data = None
    if cad_runtime_path:
        runtime_data, cad_commands, cad_api_members = load_nextcad_runtime(cad_runtime_path, cad_data["upstream_commit"])

    capabilities = cad_modules + cad_commands + cad_api_members + bim_caps
    obligations = []
    for capability in capabilities:
        if capability["capability_type"] not in ("native_command", "native_gui_command", "native_api_member"):
            continue
        for dimension, objective in DIMENSIONS.items():
            item = {
                "schema": "nextai.skill_obligation.v1",
                "record_type": "skill_obligation_not_training_example",
                "application": capability["application"],
                "capability_id": capability["capability_id"],
                "native_id": capability["native_id"],
                "capability_name": capability["name"],
                "capability_type": capability["capability_type"],
                "skill_dimension": dimension,
                "learning_objective": objective,
                "source_evidence": capability["source_evidence"],
                "source_commit": capability["source_commit"],
                "evidence_required_for_mastery": "L3_native_execution_passed",
                "mastery_status": "not_assessed"
            }
            if capability["application"] == "nextbim":
                item.update({
                    "registration_kind": capability.get("registration_kind"),
                    "undoable": capability.get("undoable"),
                    "file_effect": capability.get("file_effect")
                })
                if capability.get("file_effect") != "none":
                    item["special_rule"] = (
                        "Teach command discovery and user-led file exchange. Preserve the native "
                        "assistant file-access policy; do not train the model to bypass it."
                    )
            else:
                item["workbenches"] = capability.get("workbenches") or []
                item["special_rule"] = (
                    "A discovered GUI command is not automatically a safe, typed AI tool. "
                    "Enable execution only through a reviewed native adapter."
                )
            obligations.append(item)

    registration_kinds = {}
    file_effects = {}
    for row in bim_caps:
        kind = str(row.get("registration_kind") or "unknown")
        effect = str(row.get("file_effect") or "none")
        registration_kinds[kind] = registration_kinds.get(kind, 0) + 1
        file_effects[effect] = file_effects.get(effect, 0) + 1

    census = {
        "schema": "nextai.capability_census.v1",
        "schema_version": VERSION,
        "purpose": "Version-pinned native capability inventory; not a model mastery report.",
        "sources": {
            "nextcad": {
                "upstream_commit": cad_data["upstream_commit"],
                "source_module_count": len(cad_modules),
                "runtime_capture": "captured" if runtime_data else "not_captured",
                "application_version": runtime_data.get("application_version") if runtime_data else None
            },
            "nextbim": {
                "upstream_commit": bim_data["upstream_commit"],
                "registered_command_count": len(bim_caps),
                "registration_kind_counts": dict(sorted(registration_kinds.items())),
                "file_effect_counts": dict(sorted(file_effects.items()))
            }
        },
        "capabilities": capabilities,
        "skill_dimensions": list(DIMENSIONS),
        "counts": {
            "nextcad_source_modules": len(cad_modules),
            "nextcad_runtime_commands": len(cad_commands),
            "nextcad_runtime_api_modules": len((runtime_data or {}).get("runtime_inventory", {}).get("python_api_modules", [])),
            "nextcad_runtime_api_members": len(cad_api_members),
            "nextbim_registered_commands": len(bim_caps),
            "total_discovered_capabilities": len(capabilities),
            "skill_obligations": len(obligations),
            "nextcad_runtime_census_complete": runtime_data is not None
        },
        "evidence_rules": {
            "skill_obligations_are_sft_examples": False,
            "source_presence_is_runtime_availability": False,
            "discovery_is_execution_success": False,
            "mastery_requires_native_execution_and_validation": True
        }
    }
    return census, obligations


def write_outputs(census: dict[str, Any], obligations: list[dict[str, Any]], output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "capability-census.json").write_text(
        json.dumps(census, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (output_dir / "skill-obligations.jsonl").open("w", encoding="utf-8") as handle:
        for row in obligations:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    counts = census["counts"]
    report = [
        "# NextAI native capability census", "",
        "> Inventory and learning requirements only. This is not evidence of student mastery.", "",
        "## Source snapshots", "",
        f"- NextCAD commit: `{census['sources']['nextcad']['upstream_commit']}`",
        f"- Next BIM commit: `{census['sources']['nextbim']['upstream_commit']}`",
        f"- NextCAD runtime capture: **{census['sources']['nextcad']['runtime_capture']}**", "",
        "## Counts", "",
        f"- NextCAD source modules: **{counts['nextcad_source_modules']}**",
        f"- NextCAD live GUI commands: **{counts['nextcad_runtime_commands']}**",
        f"- NextCAD public Python API modules: **{counts['nextcad_runtime_api_modules']}**",
        f"- NextCAD public Python API members: **{counts['nextcad_runtime_api_members']}**",
        f"- Next BIM registered commands: **{counts['nextbim_registered_commands']}**",
        f"- Total capabilities inventoried: **{counts['total_discovered_capabilities']}**",
        f"- Per-command learning obligations: **{counts['skill_obligations']}**", "",
        "## Evidence boundaries", "",
        "- A source module may not load in the running application.",
        "- A discovered GUI command is not automatically an approved AI tool.",
        "- A skill obligation is not an authored lesson, training example, executed task or mastery result.",
        "- Mastery requires native execution, verification and save/reopen evidence.", ""
    ]
    (output_dir / "capability-census-report.md").write_text("\n".join(report), encoding="utf-8")
    summary = {**counts, "obligations_are_training_examples": False, "mastery_claimed": False}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bim-catalog", required=True, type=Path)
    parser.add_argument("--nextcad-source-index", required=True, type=Path)
    parser.add_argument("--nextcad-runtime-report", type=Path)
    parser.add_argument("--expected-nextcad-commit")
    parser.add_argument("--expected-nextbim-commit")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--require-nextcad-runtime", action="store_true")
    args = parser.parse_args()
    if args.require_nextcad_runtime and not args.nextcad_runtime_report:
        parser.error("--require-nextcad-runtime requires --nextcad-runtime-report")
    census, obligations = build_census(
        args.bim_catalog, args.nextcad_source_index, args.nextcad_runtime_report,
        args.expected_nextcad_commit, args.expected_nextbim_commit
    )
    print(json.dumps(write_outputs(census, obligations, args.output_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
