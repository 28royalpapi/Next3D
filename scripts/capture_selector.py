#!/usr/bin/env python3
"""Run the real Next 3D selector, record its window, and invoke both card callbacks."""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from unittest.mock import patch
from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "Next3DLauncher"))
import main as launcher

def main() -> int:
    out = ROOT / "artifacts"
    out.mkdir(parents=True, exist_ok=True)
    os.environ.pop("NEXTCAD_EXECUTABLE", None)
    os.environ.pop("NEXTBIM_EXECUTABLE", None)
    root = launcher.tk.Tk()
    app = launcher.Next3DLauncher(root)
    root.update_idletasks()
    root.update()
    time.sleep(1)
    root.update()
    x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
    screenshot = out / "next3d-selector.png"
    ImageGrab.grab(bbox=(x, y, x+w, y+h)).save(screenshot)
    results = {
        "platform": sys.platform,
        "window_size": [w, h],
        "selector_screenshot": str(screenshot),
        "runtimes": {k: str(launcher.find_runtime(k)) if launcher.find_runtime(k) else None
                     for k in ("nextcad", "nextbim")},
        "button_tests": {},
        "warnings": [],
    }
    with patch.object(launcher.messagebox, "showwarning",
                      side_effect=lambda title, message, **kwargs: results["warnings"].append(title)):
        for key in ("nextcad", "nextbim"):
            app.buttons[key].invoke()
            results["button_tests"][key] = "callback invoked"
    results["warning_count"] = len(results["warnings"])
    (out / "visual-smoke-result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    root.destroy()
    print(json.dumps(results, indent=2))
    return 0 if results["button_tests"] == {"nextcad": "callback invoked", "nextbim": "callback invoked"} else 1

if __name__ == "__main__":
    raise SystemExit(main())
