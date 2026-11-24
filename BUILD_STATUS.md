# Build and verification status

## Selector

The selector-only GitHub Actions run `44911879342` passed on Ubuntu 24.04, Windows 2025 and macOS 15 Intel. This validates the selector UI and its app-card callbacks only.

## Source provenance and patch preparation

- NextCAD source is pinned to the exact FreeCAD commit represented by the supplied archive. Its five nested git submodules are pinned by that upstream commit and are initialized recursively.
- Next BIM source is pinned to the exact BIMCraft commit represented by the supplied archive.
- The NextCAD and Next BIM patch sets were applied to clean extractions of the supplied original archives and compared with the prepared working trees. Only the intended four source files differ.
- Static source assertions verify both Next AI workspace markers and the NextCAD/Next BIM product identities. These checks are not compilation tests.

## Native app acceptance - pending

The native application workflow builds and tests both applications on Linux, Windows and macOS. Until its jobs finish successfully, the following are **not** claimed:

- successful native compilation on all three operating systems;
- a real NextCAD or Next BIM application launch;
- successful creation/editing/saving/reopening of a CAD or BIM model;
- complete tool-level acceptance of every original workbench and command.

The local execution environment has no Rust/Cargo compiler, Pixi environment or FreeCAD executable, so these native checks cannot be completed locally here.

## Screenshots

The source archives contain genuine upstream documentation images, not screenshots of the modified NextCAD or Next BIM applications. No image is labelled as a Next 3D application screenshot until it is captured from the newly built executable. The Linux native build workflow attempts to upload real GUI screenshots as artifacts after launching each application.

## Next AI

- NextCAD has a native Next AI workbench adapter in `adapters/nextcad-ai/NextAI`. It includes a local-only Ollama-compatible provider, document/workbench inspection, a typed tool registry, a plan approval dialog and transaction-protected starter operations. The current write-tool coverage is still limited; it does not yet cover the full FreeCAD workspace (Sketcher constraints, broad PartDesign, Assembly, TechDraw, FEM/CAM and complete BIM workflows).
- Next BIM reuses BIMCraft's existing native Assistant, relabelled and placed as the default Next AI workspace. A separate local-only Ollama-compatible provider patch is prepared. The native 214-command catalogue is indexed, but full command coverage and runtime execution have not yet been accepted.
- Both local model and provider configurations are present in source, but no end-to-end model download, inference, multi-step CAD/BIM task, or cross-platform package-size test has passed yet.
- Selected initial model for the 1.2 GB package target: Qwen3.5-0.8B Q4_K_M (541,903,360 bytes). This is a footprint-driven selection for runtime benchmarking, not a claim that the model alone guarantees expert CAD/BIM reasoning.
- The native build, GUI launch and save/reopen acceptance gates remain pending. The source-preparation workflow was updated on 24 November 2026 to remove ambiguity about the obsolete encoded overlay step and to run the current pinned-source preparation script.

