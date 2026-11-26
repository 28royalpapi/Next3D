#!/usr/bin/env python3
"""Run typed NextAI operations inside the built NextCAD GUI and verify save/reopen."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--executable", help="Built FreeCAD/NextCAD GUI executable")
    mode.add_argument("--command-prefix", help='Launcher prefix, e.g. "pixi run freecad"')
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--output", type=Path, help="Optional JSON report path; defaults to artifacts/nextcad-ai-native-acceptance.json")
    args = parser.parse_args()
    if args.timeout_seconds < 30:
        parser.error("--timeout-seconds must be at least 30")

    repo = Path(__file__).resolve().parents[1]
    schema_tools = repo / "training" / "nextai"
    sys.path.insert(0, str(schema_tools))
    from schema_validation import validate_training_record
    source_root = repo / "upstream" / "FreeCAD"
    module_root = source_root / "src" / "Mod" / "NextAI"
    macro = repo / "training" / "nextai" / "verify_nextcad_ai_native.FCMacro"
    if not macro.is_file():
        raise SystemExit(f"Native acceptance macro not found: {macro}")
    if not module_root.is_dir():
        raise SystemExit(f"Installed NextAI module not found: {module_root}")

    output = (args.output or (repo / "artifacts" / "nextcad-ai-native-acceptance.json")).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    project = output.with_name("nextcad-ai-native-acceptance.FCStd")
    stage_project = output.with_name("nextcad-ai-native-acceptance-stage-a.FCStd")
    trace_path = output.with_name("nextcad-ai-native-acceptance-trace.jsonl")
    for path in (output, project, stage_project, trace_path):
        if path.exists():
            path.unlink()

    if args.executable:
        executable = Path(args.executable)
        if not executable.is_absolute():
            executable = (Path.cwd() / executable).resolve()
        if not executable.is_file():
            raise SystemExit(f"NextCAD executable not found: {executable}")
        command = [str(executable), str(macro)]
    else:
        prefix = shlex.split(args.command_prefix)
        if not prefix:
            parser.error("--command-prefix cannot be empty")
        command = [*prefix, str(macro)]

    env = os.environ.copy()
    env["NEXT3D_HOME"] = str(repo)
    env["NEXT3D_NEXTCAD_SOURCE_COMMIT"] = "00cb280454069966a2fb0a8e7dc184c46e7b38b3"
    env["NEXT3D_NEXTCAD_AI_MODULE_PATH"] = str(module_root)
    env["NEXT3D_NEXTCAD_AI_ACCEPTANCE_MARKER"] = str(output)
    env["NEXT3D_NEXTCAD_AI_ACCEPTANCE_PROJECT"] = str(project)
    env["NEXT3D_NEXTCAD_AI_ACCEPTANCE_STAGE_PROJECT"] = str(stage_project)
    log_path = output.with_suffix(output.suffix + ".launcher.log")
    process = None
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command, cwd=Path.cwd(), env=env,
                stdout=log, stderr=subprocess.STDOUT
            )
            deadline = time.monotonic() + args.timeout_seconds
            result = None
            while time.monotonic() < deadline:
                if output.is_file() and output.stat().st_size:
                    try:
                        candidate = json.loads(output.read_text(encoding="utf-8"))
                    except Exception:
                        candidate = None
                    if isinstance(candidate, dict):
                        result = candidate
                        break
                code = process.poll()
                if code is not None:
                    raise RuntimeError(
                        f"NextCAD exited before writing native acceptance report (code {code}). "
                        f"See {log_path}"
                    )
                time.sleep(0.5)
            if result is None:
                raise TimeoutError(
                    f"Timed out after {args.timeout_seconds}s waiting for native acceptance. "
                    f"See {log_path}"
                )
            if result.get("status") != "PASS":
                raise RuntimeError(
                    "NextAI native operations failed inside the built GUI:\n"
                    + json.dumps(result, indent=2, ensure_ascii=False)
                    + f"\nLauncher log: {log_path}"
                )
            if not project.is_file() or project.stat().st_size == 0:
                raise RuntimeError("Native acceptance did not produce a saved FCStd project.")
            if not stage_project.is_file() or stage_project.stat().st_size == 0:
                raise RuntimeError("Native acceptance did not preserve its staged FCStd round-trip.")
            if not trace_path.is_file() or trace_path.stat().st_size == 0:
                raise RuntimeError("Native acceptance did not produce its versioned native-operation trace.")
            trace_rows = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if len(trace_rows) != 2 or any(row.get("split") != "test" for row in trace_rows):
                raise RuntimeError("Native acceptance trace must contain two held-out test records.")
            if any(len(row.get("operations", [])) > 20 for row in trace_rows):
                raise RuntimeError("A native acceptance plan exceeds the NextAI runtime step limit.")
            for row in trace_rows:
                validate_training_record(row)
            print(
                "NEXTAI NATIVE ACCEPTANCE PASS: "
                f"{len(result.get('checks', {}))} checks, "
                f"{result.get('native_object_count')} reopened objects, "
                f"{sum(len(row.get('operations', [])) for row in trace_rows)} native operation records, "
                f"report={output}, project={project}, trace={trace_path}"
            )
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NEXTAI NATIVE ACCEPTANCE FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
