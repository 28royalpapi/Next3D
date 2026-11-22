# Next 3D

Next 3D is a desktop selector for two independent native engineering applications:

- **NextCAD** - the original FreeCAD application with a NextCAD product name and a permanent `Next AI` workspace.
- **Next BIM** - the original BIMCraft application with a Next BIM product name and a permanent `Next AI` workspace.

Each app keeps its own native modelling engine, project/document format, APIs, workbenches, undo history and workflows. They are not merged. Civil 3D is not part of this project.

## Native source in this repository

The original source is connected as pinned Git submodules:

- `upstream/FreeCAD` -> `FreeCAD/FreeCAD` at `00cb280454069966a2fb0a8e7dc184c46e7b38b3`.
- `upstream/BIMCraft` -> `IPedrax/BIMCraft` at `a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b`.

FreeCAD's five nested dependencies are pinned by FreeCAD itself and are fetched recursively. Clone this repository with `--recurse-submodules`, then run `bash scripts/apply-source-patches.sh`. See [NATIVE_SOURCE.md](NATIVE_SOURCE.md) for the source revisions, patch scope and build commands.

## Selector

- `apps/Next3DLauncher/main.py` - cross-platform Python/Tkinter selector.
- `tests/test_launcher.py` - launcher tests.
- `scripts/capture_selector.py` - selector screenshot and card-callback smoke helper.
- `.github/workflows/launcher-visual-smoke.yml` - selector checks on Ubuntu, Windows and macOS.

## Build verification

`.github/workflows/native-application-build.yml` builds NextCAD and Next BIM from the pinned sources on all three desktop operating systems. The workflow also attempts genuine Linux GUI launches and saves screenshots as artifacts.

A source checkout or a passing selector test does not prove a native application is accepted. Native build, launch, model edit and save/reopen evidence is tracked in [BUILD_STATUS.md](BUILD_STATUS.md). Next AI is currently only a reserved UI space; its assistant functionality is the next implementation phase after the two base applications pass acceptance.
