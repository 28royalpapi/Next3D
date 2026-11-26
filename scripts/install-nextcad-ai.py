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
        source / "next_ai/engineering_skills.py",
        source / "knowledge_packs/skills/engineering-operator-method/SKILL.md",
        source / "knowledge_packs/skills/residential-floor-plan/SKILL.md",
        source / "knowledge_packs/skills/water-storage-tower/SKILL.md",
        source / "knowledge_packs/skills/mechanical-gear/SKILL.md",
        source / "knowledge_packs/skills/vehicle-package-design/SKILL.md",
        source / "knowledge_packs/skills/electrical-control-panel/SKILL.md",
        source / "knowledge_packs/skills/civil-road-drainage/SKILL.md",
        source / "knowledge_packs/skills/sketcher-parametric-design/SKILL.md",
        source / "knowledge_packs/skills/partdesign-feature-modelling/SKILL.md",
        source / "knowledge_packs/skills/assembly-design/SKILL.md",
        source / "knowledge_packs/skills/techdraw-engineering-documentation/SKILL.md",
        source / "knowledge_packs/skills/fem-analysis-preparation/SKILL.md",
        source / "knowledge_packs/skills/cam-toolpath-preparation/SKILL.md",
        source / "knowledge_packs/skills/mesh-reverse-engineering/SKILL.md",
        source / "knowledge_packs/skills/spreadsheet-parametric-data/SKILL.md",
        source / "knowledge_packs/skills/bim-ifc-workflow/SKILL.md",
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
