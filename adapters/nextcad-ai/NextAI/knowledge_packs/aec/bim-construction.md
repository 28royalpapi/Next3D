# Architecture, BIM and Construction — NextAI Skill

## Goal

Translate building and infrastructure requests into a coordinated, data-rich native project. Use the application's real BIM element model, not a picture of a building as a substitute for BIM.

## Project setup

Before authoring, identify project units, origin, survey/base coordinates, true north, levels, grids, work planes, phases, design options and coordinate system. Confirm the intended building/site context and the deliverables (native model, drawings, schedules, IFC or quantity information).

## Architecture

A building model may include:
- levels, grids, site/topography and reference geometry;
- walls, layers, joins, floors, roofs, ceilings and foundations;
- doors and windows hosted in compatible walls;
- stairs, ramps, railings, shafts, rooms/spaces and boundaries;
- component types, families, materials, instance/type parameters and formulas;
- plans, reflected ceiling plans, sections, elevations, 3D views and sheets;
- dimensions, tags, notes, title blocks, schedules and quantities.

The agent must confirm the actual element category, host, type, level, offsets, orientation and parameter constraints before creating or editing an element.

## Structural BIM

Model beams, columns, braces, slabs, foundations and reinforcement only when the native application supports the relevant element and relationships. Capture section/type, material, level, offsets, justification, connection/host data and reinforcement cover/spacing where applicable.

A structural BIM model is not a structural calculation. Do not claim member capacity, stability, deflection, foundation adequacy or code compliance unless a validated analysis/calculation workflow has the required loads, combinations, restraints, materials, soil data and governing standard.

## MEP and building services

Where supported, model plumbing pipes/runs, fittings, valves, fixtures, electrical circuits, panels, boards, outlets, conduits, cable trays, luminaires, data/communications and protection/earthing components.

A visible pipe or cable run does not prove a connected, sized or commissioned system. Check the native connector graph, endpoints, elevations, slopes, systems, device/board associations, ratings and schedules. Report missing connectors and unavailable calculations explicitly.

## Construction coordination

Use the native model to support:
- spatial coordination and clash/clearance review;
- sequencing and temporary works context where represented;
- quantities and schedules calculated from native elements;
- drawing sheets and revision information;
- IFC and other supported exchange deliverables;
- issue lists linking each finding to the affected native element.

Do not invent local labour rates, material prices, productivity, programme duration or code requirements. Those require a location, date, source and project-specific assumptions.

## IFC and exchange

Check the actual import/export implementation and schema version. Preserve GlobalIds, spatial hierarchy, types, properties, quantities and units when supported. After export, re-import into a fresh project and report missing, remapped, simplified or approximated elements. Never describe an exchange format as full fidelity without round-trip evidence.

## App-specific execution

NextCAD uses FreeCAD's own native document model and tool registry. Next BIM uses BIMCraft's native command ids and project engine. Do not send a NextCAD command to BIMCraft or translate a BIMCraft command by guessing parameter names. Select the adapter from the actual active application.
