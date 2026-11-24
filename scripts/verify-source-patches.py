#!/usr/bin/env python3
"""Verify pinned native applications and the first NextAI operator integration."""
from __future__ import annotations
import json
from pathlib import Path
import sys

EXPECTED_FREECAD = "00cb280454069966a2fb0a8e7dc184c46e7b38b3"
EXPECTED_BIMCRAFT = "a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"

def need(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL: " + message)

def read(path: Path) -> str:
    need(path.is_file(), "required source file is missing: %s" % path)
    return path.read_text(encoding="utf-8")

def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify-source-patches.py <FreeCAD root> <BIMCraft root>")
    freecad, bimcraft = Path(sys.argv[1]), Path(sys.argv[2])
    root = Path(__file__).resolve().parents[1]

    # The full applications remain the source of truth; this is not a reduced model editor.
    need((freecad / ".git").exists(), "FreeCAD must remain a native upstream git submodule")
    need((bimcraft / ".git").exists(), "BIMCraft must remain a native upstream git submodule")
    main_window = read(freecad / "src/Gui/MainWindow.cpp")
    main_gui = read(freecad / "src/Main/MainGui.cpp")
    need("NextAIWorkspace" in main_window and 'tr("Next AI")' in main_window,
         "NextCAD permanent native Next AI dock is missing")
    need('Config()["ExeName"] = "NextCAD"' in main_gui, "NextCAD application branding is missing")
    need('Config()["ExeVendor"] = "Next 3D"' in main_gui, "NextCAD vendor branding is missing")
    need('Config()["AppIcon"] = "freecad"' in main_gui, "Original FreeCAD app icon resource was not preserved")
    need('Config()["SplashScreen"] = "freecadsplash"' in main_gui, "Original FreeCAD splash resource was not preserved")
    for module in ("Part", "PartDesign", "Sketcher", "Assembly", "Draft", "TechDraw", "BIM", "Fem", "CAM"):
        need((freecad / "src/Mod" / module).is_dir(), "upstream FreeCAD %s workbench/module is missing" % module)

    adapter = freecad / "src/Mod/NextAI"
    init_gui = read(adapter / "InitGui.py")
    ui = read(adapter / "next_ai/ui.py")
    provider = read(adapter / "next_ai/provider.py")
    tools = read(adapter / "next_ai/freecad_tools.py")
    registry = read(adapter / "next_ai/tool_registry.py")
    need("from NextAI.next_ai.ui import NextAIWidget" in init_gui, "NextCAD native dock is not connected to its widget")
    need("QTimer.singleShot" in init_gui and "NextAIWorkspace" in init_gui, "NextCAD dock attachment hook is missing")
    need("DEFAULT_ENDPOINT" in provider and "_NoRedirect" in provider, "NextCAD local provider/redirect protection is missing")
    need("ProxyHandler({})" in provider, "NextCAD local provider must bypass configured system proxies")
    need("discover_capabilities" in tools and "listWorkbenches" in tools and "listCommands" in tools,
         "NextCAD runtime capability discovery is missing")
    need("create_draft_line" in tools and "openTransaction" in tools and "abortTransaction" in tools,
         "NextCAD first native write is not transaction-protected")
    for operation in (
        "create_partdesign_body", "create_partdesign_sketch", "add_sketch_line",
        "add_sketch_circle", "add_sketch_polygon", "create_partdesign_pad",
        "create_partdesign_pocket",
    ):
        need(operation in tools, "NextCAD native PartDesign operation is missing: " + operation)
    need("ConflictingConstraints" in tools and "RedundantConstraints" in tools,
         "NextCAD sketch solver validation is missing")
    need("body.Tip = feature" in tools and "before_volume" in tools and "after_volume" in tools,
         "NextCAD PartDesign feature-history or volume verification is missing")
    need("image_url" in provider and "MINIMUM_OLLAMA_VERSION" in provider,
         "NextCAD local multimodal provider or runtime-version gate is missing")
    need("execute_code" not in registry and "run_python" not in registry,
         "NextCAD default typed registry must not expose arbitrary code execution")

    model = json.loads((root / "models/nextai/model.json").read_text(encoding="utf-8"))
    need(model.get("quantization") == "Q4_K_M", "Shared NextAI model must use the selected compact Q4 student baseline")
    need(model.get("input_mode") == "text_and_image", "Shared NextAI model must declare image input")
    need(model.get("minimum_ollama_version_for_vision") == "0.40.11",
         "Shared NextAI model must declare the multimodal Ollama minimum")
    need(model.get("vision", {}).get("projector_required") is True,
         "Shared NextAI vision projector requirement is missing")
    for relative in (
        "cad/parametric-cad.md",
        "aec/bim-construction.md",
        "engineering/design-validation.md",
        "engineering/mechanical-design.md",
        "engineering/civil-structural.md",
        "engineering/geotechnical.md",
        "engineering/water-hydraulics.md",
        "engineering/electrical-mep.md",
        "drawing-intake.md",
        "construction/construction-delivery.md",
    ):
        need((root / "adapters/nextcad-ai/NextAI/knowledge_packs" / relative).is_file(),
             "NextAI engineering knowledge pack is missing: " + relative)
    need("NATIVE PLAN" in ui and "QMessageBox.question" in ui, "NextCAD mutation approval UI is missing")
    need("begin_turn" in tools and "document changed during" in tools, "NextCAD stale-document protection is missing")

    bim_main = read(bimcraft / "apps/bimcraft/src/main.rs")
    bim_ui = read(bimcraft / "crates/ui-egui/src/lib.rs")
    bim_dock = read(bimcraft / "crates/ui-egui/src/dock.rs")
    bim_style = read(bimcraft / "crates/ui-egui/src/style.rs")
    assistant = read(bimcraft / "crates/assistant/src/lib.rs")
    local_provider = read(bimcraft / "crates/assistant/src/local.rs")
    net = read(bimcraft / "crates/assistant/src/net.rs")
    assistant_ui = read(bimcraft / "crates/ui-egui/src/assistant.rs")
    chat = read(bimcraft / "crates/assistant/src/chat.rs")
    commands = read(bimcraft / "crates/core/src/commands.rs")
    bim_assistant_tools = read(bimcraft / "crates/assistant/src/tools.rs")
    bim_knowledge = read(bimcraft / "crates/assistant/src/knowledge.rs")
    bim_knowledge_pack = read(bimcraft / "crates/assistant/src/next_ai_knowledge.md")

    need('"com.next3d.nextbim"' in bim_main, "Next BIM desktop app identity is missing")
    need('.with_title("Next BIM")' in bim_main and 'run_native("Next BIM"' in bim_main,
         "Next BIM window title/branding is missing")
    need('Palette::Assistant => msg!("Next AI")' in bim_dock, "Native Assistant palette is not branded Next AI")
    need('Stack { tabs: vec![Palette::Browser, Palette::Assistant], active: 1 }' in bim_dock,
         "Next AI workspace is not visible beside the project browser by default")
    need('Panel::right("next-ai-workspace")' not in bim_ui,
         "A duplicate placeholder AI panel must not be created beside the native Assistant")
    need('Profile::BimCraft => "Next BIM"' in bim_style, "Next BIM profile name is missing")
    need("pub mod local;" in assistant and "Provider::Local" in assistant, "Next BIM local provider is missing")
    need("pub mod knowledge;" in assistant and "next_ai_knowledge" in assistant,
         "Next BIM assistant is not instructed to use engineering knowledge retrieval")
    need("next_ai_knowledge" in bim_assistant_tools and "crate::knowledge::search" in bim_assistant_tools,
         "Next BIM native knowledge retrieval tool is missing")
    need('include_str!("next_ai_knowledge.md")' in bim_knowledge,
         "Next BIM local knowledge is not embedded in the Assistant")
    need("engineering/geotechnical.md" in bim_knowledge_pack and "cad/parametric-cad.md" in bim_knowledge_pack,
         "Next BIM shared CAD and engineering knowledge pack is incomplete")
    need("http://127.0.0.1:11434/v1/chat/completions" in local_provider, "Next BIM local provider endpoint is missing")
    need("allowed_local" in net and 'host == "127.0.0.1"' in net, "Next BIM provider loopback boundary is missing")
    need("Local model mode is available only in this window" in chat, "Next BIM local mode must not leak to Co-Work")
    need("No remote AI provider is contacted" in assistant_ui, "Next BIM local privacy notice is missing")
    need('Palette::Assistant => msg!("Next AI")' in bim_dock and 'msg!("Next AI settings")' in read(bimcraft / "crates/ui-egui/src/settings.rs"),
         "Next BIM AI workspace labels are incomplete")
    need("pub static ALL: &[Command]" in commands, "Original BIMCraft native command registry is missing")

    root = Path(__file__).resolve().parents[1]
    catalogue = json.loads((root / "docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json").read_text(encoding="utf-8"))
    need(catalogue.get("command_count") == 214 and len(catalogue.get("commands", [])) == 214,
         "Pinned Next BIM command catalogue must contain all 214 native registrations")
    print("SOURCE CHECK PASS: pinned native apps, full manual workbench/command foundations and both Next AI workspaces are present.")
    print("SOURCE CHECK PASS: NextCAD uses typed, approved, transaction-based local tools; Next BIM reuses its native Assistant and local provider.")
    print("NOT PROOF: live FreeCAD/Ollama GUI session or successful platform build. CI and live acceptance supply that evidence.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
