#!/usr/bin/env python3
"""Create, save, reopen, edit, save and reopen a real NextCAD FreeCAD document."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def macro_text() -> str:
    return r'''import os
import FreeCAD as App
import Part

project_path = os.environ["NEXTCAD_ROUNDTRIP_FILE"]
marker_path = os.environ["NEXTCAD_ROUNDTRIP_MARKER"]

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

doc = App.newDocument("NextCAD_RoundTrip")
box = doc.addObject("Part::Box", "AcceptanceBox")
box.Length = 10.0
box.Width = 20.0
box.Height = 30.0
doc.recompute()
require(abs(box.Shape.Volume - 6000.0) < 1e-6, "initial box volume is wrong")
doc.saveAs(project_path)
App.closeDocument(doc.Name)

doc = App.openDocument(project_path)
box = doc.getObject("AcceptanceBox")
require(box is not None, "saved box is missing after first reopen")
require(abs(box.Shape.Volume - 6000.0) < 1e-6, "first reopened volume is wrong")
box.Length = 20.0
doc.recompute()
require(abs(box.Shape.Volume - 12000.0) < 1e-6, "edited box volume is wrong")
doc.save()
App.closeDocument(doc.Name)

doc = App.openDocument(project_path)
box = doc.getObject("AcceptanceBox")
require(box is not None, "edited box is missing after second reopen")
require(abs(box.Length.Value - 20.0) < 1e-6, "edited Length was not persisted")
require(abs(box.Shape.Volume - 12000.0) < 1e-6, "edited shape was not persisted")
with open(marker_path, "w", encoding="utf-8") as marker:
    marker.write("PASS: native FCStd create-save-reopen-edit-save-reopen; volume=12000\n")
App.closeDocument(doc.Name)
'''


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "upstream" / "FreeCAD"
    executable_name = "FreeCADCmd.exe" if os.name == "nt" else "FreeCADCmd"
    executable = root / "build" / "relWithDebInfo" / "bin" / executable_name
    if not executable.is_file():
        raise SystemExit(f"FreeCADCmd executable not found: {executable}")

    with tempfile.TemporaryDirectory(prefix="nextcad-roundtrip-") as temp:
        folder = Path(temp)
        project = folder / "nextcad-roundtrip.FCStd"
        marker = folder / "passed.txt"
        macro = folder / "verify_nextcad_roundtrip.FCMacro"
        macro.write_text(macro_text(), encoding="utf-8")
        env = os.environ.copy()
        env["NEXTCAD_ROUNDTRIP_FILE"] = str(project)
        env["NEXTCAD_ROUNDTRIP_MARKER"] = str(marker)
        result = subprocess.run(
            [str(executable), str(macro)],
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode != 0 or not marker.is_file():
            raise RuntimeError(
                f"FreeCADCmd round-trip failed ({result.returncode})\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        print(marker.read_text(encoding="utf-8").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
