#!/usr/bin/env python3
"""Static source assertions; these are not a substitute for a native build."""
from pathlib import Path
import sys


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify-source-patches.py <FreeCAD root> <BIMCraft root>")
    freecad = Path(sys.argv[1])
    bimcraft = Path(sys.argv[2])

    main_window = (freecad / "src/Gui/MainWindow.cpp").read_text(encoding="utf-8")
    main_gui = (freecad / "src/Main/MainGui.cpp").read_text(encoding="utf-8")
    bim_main = (bimcraft / "apps/bimcraft/src/main.rs").read_text(encoding="utf-8")
    bim_ui = (bimcraft / "crates/ui-egui/src/lib.rs").read_text(encoding="utf-8")

    need("NextAIWorkspace" in main_window and 'tr("Next AI")' in main_window,
         "NextCAD permanent Next AI dock is missing")
    need('Config()["ExeName"] = "NextCAD"' in main_gui,
         "NextCAD application name is missing")
    need('Config()["ExeVendor"] = "Next 3D"' in main_gui,
         "NextCAD vendor branding is missing")
    need('Config()["AppIcon"] = "freecad"' in main_gui,
         "Original FreeCAD icon resource was not preserved")
    need('Config()["SplashScreen"] = "freecadsplash"' in main_gui,
         "Original FreeCAD splash resource was not preserved")

    need('"com.next3d.nextbim"' in bim_main and '"Next BIM"' in bim_main,
         "Next BIM product identity is missing")
    need('Panel::right("next-ai-workspace")' in bim_ui,
         "Next BIM permanent Next AI panel is missing")

    print("SOURCE CHECK PASS: both upstream trees, product identities and reserved Next AI spaces are present.")
    print("This check does not prove compilation, launch, modelling, save/reopen or tool-level acceptance.")


if __name__ == "__main__":
    main()
