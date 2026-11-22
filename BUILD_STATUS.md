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

Both applications contain a permanent reserved Next AI workspace. There is no AI runtime, model connection or CAD/BIM tool-calling implementation in this phase. Next AI implementation should begin after the native app build and edit-save-reopen acceptance checks pass.
