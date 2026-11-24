#!/usr/bin/env python3
"""Install the NextCAD AI adapter without altering FreeCAD's existing modules."""
from __future__ import annotations

from pathlib import Path
import shutil
import sys


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: install-nextcad-ai.py <FreeCAD source root>")
    repo = Path(__file__).resolve().parents[1]
    source = repo / "adapters/nextcad-ai/NextAI"
    destination = Path(sys.argv[1]).resolve() / "src/Mod/NextAI"
    required = (
        source / "__init__.py",
        source / "Init.py",
        source / "InitGui.py",
        source / "next_ai/__init__.py",
        source / "next_ai/ui.py",
        source / "next_ai/provider.py",
        source / "next_ai/freecad_tools.py",
        source / "next_ai/tool_registry.py",
        source / "next_ai/knowledge.py",
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("NextCAD AI adapter is incomplete: " + ", ".join(missing))
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    print(f"NEXTCAD AI INSTALL PASS: installed native workbench module at {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
