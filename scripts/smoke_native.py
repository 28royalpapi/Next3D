#!/usr/bin/env python3
"""Check that a built native desktop application starts and stays alive briefly."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--seconds", type=int, default=12)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    executable = args.executable.resolve()
    if not executable.is_file():
        raise SystemExit(f"Native application executable not found: {executable}")

    env = os.environ.copy()
    env["NEXT3D_HOME"] = str(Path(__file__).resolve().parents[1])
    env["BIMCRAFT_NO_UPDATE_CHECK"] = "1"
    app_args = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
    command = [str(executable), *app_args]
    log_path = Path.cwd() / f"{executable.stem}-smoke.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + max(5, args.seconds)
            while time.monotonic() < deadline:
                code = process.poll()
                if code is not None:
                    log.flush()
                    details = log_path.read_text(encoding="utf-8", errors="replace")
                    raise RuntimeError(
                        f"{executable.name} exited early with code {code}\n{details}"
                    )
                time.sleep(0.5)
            print(f"NATIVE STARTUP PASS: {executable.name} remained alive for {args.seconds} seconds.")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"NATIVE STARTUP FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
