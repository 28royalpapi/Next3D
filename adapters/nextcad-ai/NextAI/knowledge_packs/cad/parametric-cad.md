# Parametric CAD — NextAI Skill

## Goal

Create and edit native, inspectable CAD projects rather than producing a one-off picture or an opaque mesh when an editable model is requested.

## Task intake

Identify the application (NextCAD/FreeCAD), workbench availability, document units, coordinate system, target object, required deliverables and missing dimensions. Determine whether the request is 2D drafting, solid modelling, surface modelling, assembly, technical documentation, BIM, reverse engineering, FEM or CAM.

Ask for missing critical dimensions, datums, tolerances, material, fit, constraints and intended manufacturing process. Never infer exact geometry from an unscaled screenshot.

## Preferred construction discipline

- Build from a named design specification with explicit units and constraints.
- Prefer a constrained Sketcher profile when the geometry is naturally sketch-based.
- Use native PartDesign bodies and feature history for sequential parametric components.
- Use native Draft entities for 2D lines, polylines, dimensions and annotations.
- Use native Arch/BIM objects for building elements where the workbench is loaded.
- Preserve source objects, dependencies, labels, placement and feature relationships.
- Prefer stable semantic references and native object identities over brittle hard-coded edge/face indices.
- Do not silently replace a feature-based design with a static mesh or compound.
- Make edits in an undoable native transaction; recompute and inspect the result before reporting success.

## Mechanical part workflow

1. Clarify the part purpose, units, overall envelope, interfaces, materials and manufacturing constraints.
2. Create datum planes/axes or select stable references.
3. Create a fully constrained base sketch where practical.
4. Build the primary solid with a native feature.
5. Add subsequent pockets, holes, patterns, fillets, chamfers, ribs or revolutions as native features.
6. Verify dimensions, volume, solid count, validity and dependency state.
7. Change at least one defining parameter and verify that dependent features recompute.
8. Save, close and reopen the native file; confirm the tree and geometry survive.

## Architectural / civil drafting workflow

- Establish site/project coordinates, levels, grids, units and orientation before drawing.
- Separate layers/categories and object types appropriately.
- Use explicit wall centre-lines, widths, heights, alignments and opening positions.
- Use native parametric walls, floors, columns, beams, stairs, roofs and spaces where the installed workbench supports them.
- Keep dimensions, annotations and views linked to the native model where supported.
- Produce plans, elevations, sections, details and sheets from the project, not as disconnected illustrations.

## Advanced CAD feature boundary

The model may propose advanced operations only when the live registry exposes a validated native tool or a user-approved native command path. The existence of a FreeCAD module in the source tree is not proof that its workbench loaded or that its optional dependency is installed. FEM and CAM operations must be gated on the actual solver, mesh, tool library and postprocessor availability.

## Verification report

Report: native object names/types, key dimensions and units, constraint state, recompute status, geometry checks, warnings, save/reopen result and any remaining manual steps. A rendered viewport alone is not a pass.
