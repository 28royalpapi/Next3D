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
- [BIMCraft's 215-command native catalogue](docs/next-ai/catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json)
- [NextCAD source workbench index](docs/next-ai/catalogs/NEXTCAD_WORKBENCH_SOURCE_INDEX.v1.json)
- [Pinned third-party AI research projects](docs/next-ai/THIRD_PARTY_AI_RESEARCH.md)
- [Dataset, training and evaluation plan](docs/next-ai/DATASET_AND_EVALUATION.md)
- [Integration architecture and implementation order](docs/next-ai/INTEGRATION_ARCHITECTURE.md)
- [Native action-plan schema v1](schemas/next-ai-action-plan.v1.schema.json)

NextAI has moved beyond a workspace-only concept. The repository now contains a NextCAD adapter with a local-only provider path, live workbench/document discovery, a starter typed tool registry, plan approval and transactional execution; a Next BIM local-provider patch built around a fixed loopback Ollama endpoint; a 215-registration BIMCraft command catalogue; engineering knowledge/skill curriculum; and data-preparation, native-trace validation, training and evaluation pipelines.

These are source-level implementation milestones, not proof of a finished operator. The starter tool surface is still limited and does not expose every native CAD/BIM command. Native builds, GUI/CLI acceptance, live NextCAD runtime discovery, full-scale corpus/token audit, end-to-end local inference, fine-tuning, held-out model performance and the final offline package remain separate acceptance gates. See [BUILD_STATUS.md](BUILD_STATUS.md) for verified results and explicit blockers.

## Selector

- `apps/Next3DLauncher/main.py` - cross-platform Python/Tkinter selector.
- `tests/test_launcher.py` - launcher tests.
- `scripts/capture_selector.py` - selector screenshot and card-callback smoke helper.
- `.github/workflows/launcher-visual-smoke.yml` - selector checks on Ubuntu, Windows and macOS.

## Build verification

`.github/workflows/native-application-build.yml` builds NextCAD and Next BIM from the pinned sources. Its Linux-focused evidence path builds both applications and attempts native trace collection plus real GUI launches; a full Linux/Windows/macOS matrix is available as a separate dispatch option.

A source checkout, passing unit tests or a selector screenshot does not prove a native application is accepted. Native build, launch, model edit and save/reopen evidence is tracked in [BUILD_STATUS.md](BUILD_STATUS.md). The applications must pass those checks before they are called complete.
