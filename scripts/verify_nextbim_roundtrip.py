#!/usr/bin/env python3
"""Create, save, reopen, edit, save and reopen a real Next BIM project via the native BIMCraft engine."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def command(binary: Path, *args: str) -> str:
    result = subprocess.run(
        [str(binary), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {binary} {' '.join(args)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def project_info(binary: Path, project: Path) -> dict:
    output = command(binary, "info", str(project))
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bimcraft-cli info did not return JSON: {output}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("counts"), dict):
        raise RuntimeError(f"Project information is missing element counts: {data}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    args = parser.parse_args()
    cli = args.cli.resolve()
    if not cli.is_file():
        raise SystemExit(f"Next BIM project CLI executable not found: {cli}")

    with tempfile.TemporaryDirectory(prefix="nextbim-roundtrip-") as temp:
        project = Path(temp) / "nextbim-roundtrip.bimc"
        first_wall = 'wall {"points":[[15000,10000],[18000,10000]]}'
        command(cli, "run", "--sample", "--cmd", first_wall, "--save", str(project))
        if not project.is_file() or project.stat().st_size == 0:
            raise RuntimeError("Next BIM did not write the first project file")

        first = project_info(cli, project)
        first_walls = int(first["counts"].get("wall", 0))
        if first_walls < 5:
            raise RuntimeError(f"Expected the sample plus the first new wall; found {first_walls}")

        second_wall = 'wall {"points":[[15000,13000],[18000,13000]]}'
        command(cli, "run", str(project), "--cmd", second_wall, "--save", str(project))
        second = project_info(cli, project)
        second_walls = int(second["counts"].get("wall", 0))
        if second_walls != first_walls + 1:
            raise RuntimeError(
                f"Save/reopen did not preserve the first model and next edit: "
                f"before={first_walls}, after={second_walls}"
            )

        print(
            "NEXT BIM PROJECT ROUND-TRIP PASS: sample created, saved, reopened, edited, "
            f"saved again and reopened; wall count {first_walls} -> {second_walls}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
