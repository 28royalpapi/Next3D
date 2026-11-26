---
name: techdraw-engineering-documentation
description: Produce engineering drawings with views, projections, sections, dimensions, annotations, title blocks, sheets and model-derived schedules.
tags: [freecad, nextcad, techdraw, engineering-drawing, drafting, dimensions, section, elevation, sheet, schedule]
aliases: [TechDraw workbench, manufacturing drawing, fabrication drawing, engineering drawing, technical sheet]
---

# TechDraw and engineering documentation

## Drawing intent and requirements

Clarify the drawing purpose: manufacture, assembly, construction, coordination, inspection, tender or presentation. Establish projection convention, units, paper size/orientation, scale, datum scheme, required views, section locations, detail views, dimensioning basis, tolerances, material/finish notes and governing standard/edition. Missing values remain TBD.

## Native drawing workflow

1. Inspect the source document and select the exact editable model objects.
2. Confirm the model units, coordinate system and stable reference datums.
3. Create orthographic views that expose the geometry needed for the drawing purpose.
4. Add isometric views only as supplementary orientation aids; they do not replace dimensioned orthographic views.
5. Create section and detail views where hidden geometry or interfaces require explanation.
6. Add dimensions from actual native geometry/datum references, not guessed screen coordinates.
7. Add centre lines, hatching, annotations, labels, notes and title-block information as supported.
8. Check view scale, projection alignment, clipping, overlaps, text legibility and dimension completeness.
9. Generate schedules/parts lists from the actual model when possible, with object IDs and units.
10. Save/reopen and export to the requested format; compare the exported drawing with the native sheet.

## Native operation discovery

Use the pinned TechDraw documentation, active workbench and exact API signatures. A generic screenshot or Draft label is not a TechDraw sheet. If the current typed adapter lacks view, section, dimension or sheet creation tools, report the missing adapter capabilities. Do not invent those tool calls.

## What a drawing proves

A drawing documents the model and its stated design basis; it does not certify the model. A visual drawing is not a manufacturing definition without the necessary tolerances, material, finish, datum, process and inspection requirements. Never invent unspecified tolerances or standards clauses.
