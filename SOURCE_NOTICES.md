# Source notices and provenance

## NextCAD / FreeCAD

The intended NextCAD application is derived from the user-supplied `FreeCAD-main.zip`. The original FreeCAD licence, copyright notices, module names and project identifiers must be retained. The archive omits the contents of five declared Git submodules; recursively initialise those exact upstream submodules before attempting a source build.

## Next BIM / BIMCraft

The intended Next BIM application is derived from the user-supplied `BIMCraft-main.zip`. Preserve its upstream MIT and Apache licence files, NOTICE, internal crate names and source attribution. No native compiled executable is present in the archive.

## Next 3D selector

The selector source under `apps/Next3DLauncher/` is newly authored Python/Tkinter code. It starts each native app as a separate process and does not merge document models or undo histories.

## Screenshot provenance

The source archive contains upstream documentation screenshots. They depict the original applications and are included in visual documentation only. They are not screenshots captured from a NextCAD or Next BIM executable produced by this project.
