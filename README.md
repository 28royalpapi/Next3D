# Next 3D

Next 3D is a desktop selector for two independent native engineering applications:

- **NextCAD** - the original FreeCAD application with a NextCAD product name and a permanent `Next AI` workspace.
- **Next BIM** - the original BIMCraft application with a Next BIM product name and a permanent `Next AI` workspace.

Each app keeps its own native modelling engine, project/document format, APIs, workbenches, undo history and workflows. They are not merged. Civil 3D is not part of this project.

## Native source in this repository

The original source is connected as pinned Git submodules:

- `upstream/FreeCAD` -> `FreeCAD/FreeCAD` at `00cb280454069966a2fb0a8e7dc184c46e7b38b3`.
- `upstream/BIMCraft` -> `IPedrax/BIMCraft` at `a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b`.

FreeCAD's nested dependencies are pinned by FreeCAD itself and are fetched recursively. To work on the selected Next AI branch:

```bash
git clone --recurse-submodules --branch nextcad https://github.com/28royalpapi/Next3D.git
cd Next3D
bash scripts/apply-source-patches.sh
```

See [NATIVE_SOURCE.md](NATIVE_SOURCE.md) for source revisions, patch scope and build commands. Five separate AI research repositories are pinned under `research/ai-reference/`; their original licences and code remain independent. The native build workflow fetches only `upstream/FreeCAD`, `upstream/BIMCraft` and FreeCAD's own nested dependencies.

## Next AI

The first law is: **understand the native application before allowing AI to operate it.** The AI must use each application's real commands and model, ask when important design information is missing, validate native results and preserve undo/editability.

- [Next AI foundation and first law](docs/next-ai/FOUNDATION.md)
- [Application capability inventory](docs/next-ai/CAPABILITY_MATRIX.md)

Next AI is in the research and architecture phase. The reserved workspace is present in both applications, but the local model, provider, knowledge retrieval, native tool adapters and training/evaluation pipeline are not yet implemented. The capability inventory distinguishes source presence from verified runtime support and records known gaps.

## Selector

- `apps/Next3DLauncher/main.py` - cross-platform Python/Tkinter selector.
- `tests/test_launcher.py` - launcher tests.
- `scripts/capture_selector.py` - selector screenshot and card-callback smoke helper.
- `.github/workflows/launcher-visual-smoke.yml` - selector checks on Ubuntu, Windows and macOS.

## Build verification

`.github/workflows/native-application-build.yml` builds NextCAD and Next BIM from the pinned sources on Linux, Windows and macOS. It also runs upstream tests and attempts genuine Linux GUI launches with screenshots as artifacts.

A source checkout or a passing selector test does not prove a native application is accepted. Native build, launch, model edit and save/reopen evidence is tracked in [BUILD_STATUS.md](BUILD_STATUS.md). The base applications must pass those checks before they are called complete; the native workflow runs on both `main` and `nextcad`.
