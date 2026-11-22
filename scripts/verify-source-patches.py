#!/usr/bin/env python3
"""Static source assertions; native compilation and model round trips are separate checks."""
from pathlib import Path
import sys


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify-source-patches.py <FreeCAD root> <BIMCraft root>")
    freecad, bimcraft = Path(sys.argv[1]), Path(sys.argv[2])
    main_window = (freecad / "src/Gui/MainWindow.cpp").read_text(encoding="utf-8")
    main_gui = (freecad / "src/Main/MainGui.cpp").read_text(encoding="utf-8")
    bim_main = (bimcraft / "apps/bimcraft/src/main.rs").read_text(encoding="utf-8")
    bim_ui = (bimcraft / "crates/ui-egui/src/lib.rs").read_text(encoding="utf-8")
    bim_style = (bimcraft / "crates/ui-egui/src/style.rs").read_text(encoding="utf-8")
    assistant = (bimcraft / "crates/assistant/src/lib.rs").read_text(encoding="utf-8")
    local_provider = (bimcraft / "crates/assistant/src/local.rs").read_text(encoding="utf-8")
    net = (bimcraft / "crates/assistant/src/net.rs").read_text(encoding="utf-8")
    assistant_ui = (bimcraft / "crates/ui-egui/src/assistant.rs").read_text(encoding="utf-8")

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

    need('"com.next3d.nextbim"' in bim_main,
         "Next BIM desktop identity is missing")
    need('.with_title("Next BIM")' in bim_main,
         "Next BIM viewport/window title is missing")
    need('run_native("Next BIM"' in bim_main,
         "Next BIM native window fallback title is missing")
    need('format!("{family} · Next BIM")' in bim_ui,
         "Next BIM document window title is missing")
    need('Panel::right("next-ai-workspace")' in bim_ui,
         "Next BIM permanent Next AI panel is missing")
    need('Profile::BimCraft => "Next BIM"' in bim_style,
         "Next BIM visible profile label is missing")

    need("pub mod local;" in assistant and "Provider::Local" in assistant,
         "Next BIM local model provider is missing")
    need('http://127.0.0.1:11434/v1/chat/completions' in local_provider,
         "Next BIM local provider endpoint is missing")
    need("allowed_local" in net and 'host == "127.0.0.1"' in net,
         "Next BIM loopback-only network restriction is missing")
    need("Local model mode is available only in this window" in (bimcraft / "crates/assistant/src/chat.rs").read_text(encoding="utf-8"),
         "Next BIM must reject local inference in Co-Work sessions")
    need("No remote AI provider is contacted" in assistant_ui,
         "Next BIM local-provider privacy notice is missing")

    print("SOURCE CHECK PASS: upstream revisions, product identities, Next AI spaces and Next BIM local-provider guardrails are present.")
    print("This check does not prove compilation, runtime Ollama connectivity, modelling or save/reopen acceptance.")


if __name__ == "__main__":
    main()
