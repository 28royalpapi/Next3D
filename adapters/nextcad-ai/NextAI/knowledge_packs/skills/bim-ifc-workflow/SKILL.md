---
name: bim-ifc-workflow
description: Plan native BIM models, spatial hierarchies, building elements, properties, quantities, coordination, documentation and IFC exchange.
tags: [freecad, nextcad, bim, arch, ifc, building, spatial-hierarchy, levels, walls, windows, doors, properties, quantities, coordination]
aliases: [FreeCAD BIM, Arch workbench, IFC model, building information model, building model]
---

# BIM and IFC workflows in NextCAD

## Understand the BIM information brief

Clarify project purpose, site/survey, coordinate reference and vertical datum, building levels/storeys, disciplines, element breakdown, information requirements, classifications, property sets, quantities, phases, coordination process and exchange deliverables.

A 3D architectural model and an information-rich BIM model are not necessarily the same thing. A wall-shaped solid is not proof of a correct native wall type, layer build-up, hosted openings or IFC relationship.

## Native model structure

Understand the actual installed Arch/BIM object types, building/site/level containers, wall/floor/roof/window/door/stair/structure/space types, host/level relationships, materials, properties, classifications, quantities, references and IFC mapping. Use the exact native object schema and live API documentation.

## Workflow

1. Establish coordinate system, survey datum, site boundary and levels.
2. Create project/building/storey hierarchy where supported.
3. Create grids, floor plates and spatial boundaries.
4. Create wall/floor/roof and structural elements with known type, thickness and elevation.
5. Place openings and hosted components only when their host relationships and dimensions are supported by native tools.
6. Create rooms/spaces, verify boundaries and assign properties/classifications.
7. Coordinate structural and MEP elements using explicit model relationships where available.
8. Produce schedules, views, sheets and quantity reports from native element properties.
9. Export IFC with the required schema/version and mappings.
10. Validate the exchange file using the relevant IFC validator and compare element counts, relationships, property sets and quantities.

## Limits

A 3D solids package is not automatically a BIM deliverable. A successful IFC export is not proof of complete information or coordination. Do not claim IFC validity, required property completeness, code compliance or clash-free status without corresponding checks.

The NextAI student uses this skill for FreeCAD/NextCAD's BIM/Arch ecosystem only. Next BIM remains a separate BIMCraft engine and command set; do not mix its commands or project format into this native FreeCAD workflow.
