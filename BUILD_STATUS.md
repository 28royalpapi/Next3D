# Build and visual verification status

## Verified in the current Linux working environment

- The Next 3D selector was launched under Xvfb and its visible window captured.
- The selector displays the NextCAD and Next BIM application choices.
- The NextCAD and Next BIM button callbacks were invoked in the real selector; both produced the expected missing-runtime warning path.
- Three launcher unit tests pass.
- Python syntax checks pass.

## Not verified

- No NextCAD/FreeCAD native executable has been built or launched.
- No Next BIM/BIMCraft native executable has been built or launched.
- No native CAD or BIM model has been edited, saved and reopened.
- Windows and macOS runtime execution is not evidenced by this local run.
- No Windows/macOS/Linux native application acceptance report is available.

The source archives include genuine screenshots of the original FreeCAD and BIMCraft interfaces. Such screenshots are upstream documentation references and must not be described as screenshots of the newly branded applications launched in this run.

The Linux environment used here has no Rust compiler, Cargo, Pixi or FreeCAD executable. The supplied FreeCAD archive omits the contents of five declared Git submodules.

The workflow in this repository is currently intended to exercise and capture the **selector only**. It is not a native CAD/BIM build workflow.
