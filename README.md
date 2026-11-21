# Next 3D

Next 3D is a desktop selector for two separate native engineering applications:
- **NextCAD** - based on the supplied FreeCAD source.
- **Next BIM** - based on the supplied BIMCraft source.

The applications are intended to remain independent: separate model engines, native documents, undo/redo histories and workflows. The earlier combined-engine prototype is not the selected architecture.

## What is currently in this GitHub repository

- `apps/Next3DLauncher/main.py` - cross-platform Python/Tkinter selector.
- `tests/test_launcher.py` - launcher runtime-discovery tests.
- `scripts/capture_selector.py` - launches the selector, saves a window screenshot and invokes both app-card callbacks.
- `.github/workflows/launcher-visual-smoke.yml` - intended selector smoke matrix for Ubuntu, Windows and macOS.

## What is not yet in this GitHub repository

The complete FreeCAD and BIMCraft source trees from the two original archives have **not** been uploaded to this GitHub branch. They are not present merely because the launcher refers to them. Native NextCAD and Next BIM executables are not included either.

The local working package was prepared separately from the supplied archives. FreeCAD's uploaded ZIP lacks the contents of five declared Git submodules, which must be initialized before building.

## Verification boundary

A selector screenshot or selector test does not prove that NextCAD or Next BIM builds, launches, or edits a model. No native CAD/BIM build or edit-save-reopen test is claimed by this repository snapshot. See `BUILD_STATUS.md` for the current evidence boundary.

The dedicated Next AI functionality is deferred; this phase is focused on the non-AI platform.
