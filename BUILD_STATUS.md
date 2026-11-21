# Build and visual verification status

## GitHub Actions selector run

Workflow run: [44911879342](https://github.com/28royalpapi/Next3D/actions/runs/44911879342) - completed successfully.

| Runner | Selector | Button callbacks | Screenshot artifact |
|---|---|---|---|
| Ubuntu 24.04 | PASS | PASS | Uploaded |
| Windows 2025 | PASS | PASS | Uploaded |
| macOS 15 Intel | PASS | PASS | Uploaded |

The Windows layout was adjusted to fit its smaller runner display. The macOS card buttons were changed to platform-neutral clickable labels so the dark button text remains readable. The corrected screenshots are from the second successful run, after these fixes.

Each runner reported that both native runtimes were not installed. The button callbacks ran and returned the expected missing-runtime warnings; no substitute CAD/BIM applications were launched.

## Native application acceptance - not yet verified

- No NextCAD/FreeCAD native executable has been built or launched.
- No Next BIM/BIMCraft native executable has been built or launched.
- No native CAD or BIM model has been edited, saved and reopened.
- The FreeCAD and BIMCraft screenshots in the supplied source archives are genuine upstream documentation references, not screenshots of the newly branded applications running in these CI jobs.

The supplied FreeCAD ZIP omits the contents of five declared Git submodules. The Linux working environment used for local source checks has no Rust/Cargo, Pixi or FreeCAD executable.

**Scope of this workflow:** the selector only. It is not a FreeCAD or BIMCraft build workflow and does not prove native application editing.
