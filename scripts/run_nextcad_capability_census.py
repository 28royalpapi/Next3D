#!/usr/bin/env python3
"""Launch NextCAD with the read-only runtime census macro and build its skill map."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--executable", help="Built FreeCAD/NextCAD GUI executable")
    mode.add_argument("--command-prefix", help='Launcher prefix, e.g. "pixi run freecad"')
    parser.add_argument("--macro", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--census-output", required=True, type=Path)
    parser.add_argument("--nextcad-commit", required=True)
    parser.add_argument("--nextbim-commit", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    macro = args.macro.resolve()
    output = args.output.resolve()
    census_output = args.census_output.resolve()
    if not macro.is_file():
        raise SystemExit(f"NextCAD census macro not found: {macro}")
    if args.timeout_seconds < 15:
        parser.error("--timeout-seconds must be at least 15")
    output.parent.mkdir(parents=True, exist_ok=True)
    census_output.mkdir(parents=True, exist_ok=True)
    for old in (output, output.with_suffix(output.suffix + ".tmp")):
        if old.exists():
            old.unlink()

    if args.executable:
        executable = Path(args.executable)
        if not executable.is_absolute():
            executable = (Path.cwd() / executable).resolve()
        if not executable.is_file():
            raise SystemExit(f"NextCAD GUI executable not found: {executable}")
        command = [str(executable), str(macro)]
    else:
        prefix = shlex.split(args.command_prefix)
        if not prefix:
            parser.error("--command-prefix cannot be empty")
        command = [*prefix, str(macro)]

    env = os.environ.copy()
    env["NEXT3D_CAPABILITY_REPORT"] = str(output)
    env["NEXT3D_NEXTCAD_SOURCE_COMMIT"] = args.nextcad_commit
    env["NEXT3D_HOME"] = str(repo)
    log_path = output.with_suffix(output.suffix + ".launcher.log")
    process = None
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command, cwd=Path.cwd(), env=env,
                stdout=log, stderr=subprocess.STDOUT
            )
            deadline = time.monotonic() + args.timeout_seconds
            report = None
            while time.monotonic() < deadline:
                if output.is_file() and output.stat().st_size > 0:
                    try:
                        candidate = json.loads(output.read_text(encoding="utf-8"))
                    except Exception:
                        candidate = None
                    if isinstance(candidate, dict):
                        report = candidate
                        break
                code = process.poll()
                if code is not None:
                    raise RuntimeError(
                        f"NextCAD exited before writing its capability report (code {code}). "
                        f"See {log_path}"
                    )
                time.sleep(0.5)
            if report is None:
                raise TimeoutError(
                    f"Timed out after {args.timeout_seconds}s waiting for {output}. "
                    f"See {log_path}"
                )
            runtime = report.get("runtime_inventory", {})
            commands = runtime.get("commands", [])
            workbenches = runtime.get("workbenches", [])
            if report.get("application") != "nextcad":
                raise RuntimeError("Runtime report did not identify application=nextcad")
            if report.get("upstream_commit") != args.nextcad_commit:
                raise RuntimeError("Runtime report source commit did not match the pinned NextCAD revision")
            if not commands or not workbenches or runtime.get("global_command_registry_enumerated") is not True:
                raise RuntimeError("Runtime report is incomplete: no commands/workbenches or no global enumeration proof")
            print(
                f"NEXTCAD RUNTIME CENSUS PASS: {len(commands)} native GUI commands, "
                f"{len(workbenches)} workbenches, application {report.get('application_version')}"
            )
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    builder = repo / "training/nextai/capability_census.py"
    bim_catalog = repo / "docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json"
    cad_index = repo / "docs/next-ai/catalogs/NEXTCAD_WORKBENCH_SOURCE_INDEX.v1.json"
    subprocess.run([
        sys.executable, str(builder),
        "--bim-catalog", str(bim_catalog),
        "--nextcad-source-index", str(cad_index),
        "--nextcad-runtime-report", str(output),
        "--expected-nextcad-commit", args.nextcad_commit,
        "--expected-nextbim-commit", args.nextbim_commit,
        "--output-dir", str(census_output),
        "--require-nextcad-runtime",
    ], check=True)
    print(f"NEXTAI FULL CAPABILITY CENSUS PASS: {census_output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NEXTCAD CAPABILITY CENSUS FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
