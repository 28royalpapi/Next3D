#!/usr/bin/env python3
"""Verify NextAI capability indexes against the pinned native source checkouts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

CONSTRUCTORS = {"edit", "other", "edit_files", "other_files"}


class VerificationError(RuntimeError):
    pass


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def skip_trivia(source: str, pos: int) -> int:
    """Skip whitespace and Rust line/block comments, including nested blocks."""
    while pos < len(source):
        if source[pos].isspace():
            pos += 1
            continue
        if source.startswith("//", pos):
            end = source.find("\n", pos + 2)
            return len(source) if end < 0 else skip_trivia(source, end + 1)
        if source.startswith("/*", pos):
            depth = 1
            pos += 2
            while pos < len(source) and depth:
                if source.startswith("/*", pos):
                    depth += 1
                    pos += 2
                elif source.startswith("*/", pos):
                    depth -= 1
                    pos += 2
                else:
                    pos += 1
            if depth:
                raise VerificationError("Unterminated Rust block comment in command registry")
            continue
        break
    return pos


def skip_string_or_char(source: str, pos: int) -> int:
    """Skip ordinary, byte, raw and byte-raw Rust literals."""
    start = pos
    if source.startswith("br", pos):
        pos += 2
        hashes = 0
        while pos < len(source) and source[pos] == "#":
            hashes += 1
            pos += 1
        if pos < len(source) and source[pos] == '"':
            terminator = '"' + ("#" * hashes)
            end = source.find(terminator, pos + 1)
            if end < 0:
                raise VerificationError("Unterminated Rust raw byte string")
            return end + len(terminator)
        return start

    if source.startswith("r", pos):
        pos += 1
        hashes = 0
        while pos < len(source) and source[pos] == "#":
            hashes += 1
            pos += 1
        if pos < len(source) and source[pos] == '"':
            terminator = '"' + ("#" * hashes)
            end = source.find(terminator, pos + 1)
            if end < 0:
                raise VerificationError("Unterminated Rust raw string")
            return end + len(terminator)
        return start

    if source.startswith('b"', pos) or source.startswith("b'", pos):
        pos += 1

    quote = source[pos] if pos < len(source) else ""
    if quote not in ('"', "'"):
        return start
    pos += 1
    while pos < len(source):
        if source[pos] == "\\":
            pos += 2
        elif source[pos] == quote:
            return pos + 1
        else:
            pos += 1
    raise VerificationError("Unterminated Rust string/character literal")


def read_simple_string(source: str, pos: int) -> tuple[str, int]:
    if pos >= len(source) or source[pos] != '"':
        raise VerificationError("Expected a string literal as the command constructor's first argument")
    end = pos + 1
    value = []
    while end < len(source):
        char = source[end]
        if char == "\\":
            if end + 1 >= len(source):
                break
            value.extend((char, source[end + 1]))
            end += 2
        elif char == '"':
            return "".join(value), end + 1
        else:
            value.append(char)
            end += 1
    raise VerificationError("Unterminated command identifier string literal")


def extract_command_registrations(source: str) -> list[dict[str, str]]:
    marker = "pub static ALL: &[Command] = &["
    start = source.find(marker)
    if start < 0:
        raise VerificationError("Could not find the ALL command registry array in BIMCraft source")
    pos = start + len(marker)
    bracket_depth = 1
    registrations: list[dict[str, str]] = []

    while pos < len(source) and bracket_depth:
        pos = skip_trivia(source, pos)
        if pos >= len(source):
            break
        skipped = skip_string_or_char(source, pos)
        if skipped != pos:
            pos = skipped
            continue
        char = source[pos]
        if char == "[":
            bracket_depth += 1
            pos += 1
            continue
        if char == "]":
            bracket_depth -= 1
            pos += 1
            continue
        if char.isalpha() or char == "_":
            end = pos + 1
            while end < len(source) and (source[end].isalnum() or source[end] == "_"):
                end += 1
            name = source[pos:end]
            if name in CONSTRUCTORS:
                call_pos = skip_trivia(source, end)
                if call_pos < len(source) and source[call_pos] == "(":
                    first_arg = skip_trivia(source, call_pos + 1)
                    if first_arg >= len(source) or source[first_arg] != '"':
                        raise VerificationError(f"{name}(...) does not start with a command ID string")
                    command_id, _ = read_simple_string(source, first_arg)
                    registrations.append({"id": command_id, "registration_kind": name})
            pos = end
            continue
        pos += 1

    if bracket_depth:
        raise VerificationError("Unterminated BIMCraft ALL command registry array")
    if not registrations:
        raise VerificationError("No BIMCraft command registrations were found")
    ids = [row["id"] for row in registrations]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise VerificationError("Duplicate native command IDs in BIMCraft source: " + ", ".join(duplicates))
    return registrations


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VerificationError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{path} root must be a JSON object")
    return value


def verify(args: argparse.Namespace) -> dict[str, Any]:
    cad_root = args.nextcad_source_root.resolve()
    bim_root = args.nextbim_source_root.resolve()
    cad_index = read_json(args.nextcad_source_index)
    bim_catalog = read_json(args.nextbim_catalog)

    actual_cad_commit = git_commit(cad_root)
    actual_bim_commit = git_commit(bim_root)
    expected_cad_commit = cad_index.get("upstream_commit")
    expected_bim_commit = bim_catalog.get("upstream_commit")
    if actual_cad_commit != expected_cad_commit:
        raise VerificationError(
            f"NextCAD source commit mismatch: source={actual_cad_commit}, index={expected_cad_commit}"
        )
    if actual_bim_commit != expected_bim_commit:
        raise VerificationError(
            f"Next BIM source commit mismatch: source={actual_bim_commit}, catalogue={expected_bim_commit}"
        )

    actual_modules = sorted(
        item.name for item in cad_root.iterdir() if item.is_dir() and not item.name.startswith(".")
    )
    indexed_modules = sorted(
        row["module"] for row in cad_index.get("modules", [])
        if isinstance(row, dict) and isinstance(row.get("module"), str)
    )
    if actual_modules != indexed_modules:
        missing = sorted(set(actual_modules) - set(indexed_modules))
        stale = sorted(set(indexed_modules) - set(actual_modules))
        raise VerificationError(
            f"NextCAD module index is out of sync. Unindexed source modules={missing}; "
            f"missing source directories={stale}"
        )

    source_registrations = extract_command_registrations(
        (bim_root / "crates/core/src/commands.rs").read_text(encoding="utf-8")
    )
    catalog_rows = bim_catalog.get("commands")
    if not isinstance(catalog_rows, list):
        raise VerificationError("BIMCraft catalogue has no commands array")
    catalog_by_id = {row.get("id"): row for row in catalog_rows if isinstance(row, dict)}
    source_by_id = {row["id"]: row for row in source_registrations}
    if set(source_by_id) != set(catalog_by_id):
        missing = sorted(set(source_by_id) - set(catalog_by_id))
        stale = sorted(set(catalog_by_id) - set(source_by_id))
        raise VerificationError(
            f"Next BIM command catalogue is out of sync. Unindexed registrations={missing}; "
            f"stale catalogue IDs={stale}"
        )
    wrong_kinds = sorted(
        command_id for command_id, source_row in source_by_id.items()
        if catalog_by_id[command_id].get("registration_kind") != source_row["registration_kind"]
    )
    if wrong_kinds:
        raise VerificationError("Next BIM registration kind mismatch for: " + ", ".join(wrong_kinds))
    if len(source_registrations) != bim_catalog.get("command_count"):
        raise VerificationError(
            f"Next BIM command_count mismatch: source={len(source_registrations)}, "
            f"catalogue={bim_catalog.get('command_count')}"
        )

    return {
        "status": "PASS",
        "nextcad_commit": actual_cad_commit,
        "nextcad_source_modules": len(actual_modules),
        "nextbim_commit": actual_bim_commit,
        "nextbim_native_registrations": len(source_registrations),
        "nextbim_registration_kind_counts": {
            kind: sum(1 for item in source_registrations if item["registration_kind"] == kind)
            for kind in sorted({item["registration_kind"] for item in source_registrations})
        },
        "catalogue_matches_pinned_native_sources": True
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nextcad-source-root", required=True, type=Path)
    parser.add_argument("--nextbim-source-root", required=True, type=Path)
    parser.add_argument("--nextcad-source-index", required=True, type=Path)
    parser.add_argument("--nextbim-catalog", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args), indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NATIVE CAPABILITY INDEX VERIFICATION FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
