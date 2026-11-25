# BIMCraft native command playbook for NextAI

## Authority and safe command selection

This guide describes command families present in the pinned BIMCraft source used by this Next3D branch. The live BIMCraft command catalogue is always authoritative. Before using any command, call `list_commands` with a focused filter and read the returned identifier, label and parameter description. Do not guess a command name, type name, parameter or category from this guide.

The BIMCraft assistant's native tools are:

- `list_commands`: discover exact command identifiers and parameters.
- `inspect_model`: inspect levels, element counts, types, warnings and undo history.
- `query_elements`: retrieve exact element IDs, fields and derived values.
- `execute`: run one native BIMCraft command with JSON parameters.
- `todo_write`: show a staged checklist for multi-step work.

The project remains the user's project. Use the native commands, not external file-writing or arbitrary code. If a command fails, BIMCraft reports the failed command and leaves that operation unapplied; inspect the model before deciding what to do next.

## Building model sequence

For a new building, first establish the brief and inspect the project. Then discover and execute the supported commands in a deliberate sequence:

1. **Project setup:** `level` for confirmed storey elevations and extents; `grid` for confirmed structural axes. Do not invent survey coordinates or a vertical datum.
2. **Primary architecture:** `wall` for wall runs, `door` and `window` for confirmed openings and families/types, `floor` for confirmed slab boundaries and openings, and `room` for spaces enclosed by actual walls and room-separation lines.
3. **Structure:** discover `structural_column`, `beam`, `footing` and `strip_footing` commands and the available types. Use only dimensions, levels, type properties and material choices that have been supplied or explicitly approved as concept placeholders.
4. **Access and envelope:** discover `stair`, `ramp`, `roof` and railing commands. Check stair run, landing, headroom, access and guard requirements from the project brief; do not invent code compliance.
5. **Services:** discover `pipe`, `duct`, electrical panel/circuit and other discipline commands. Confirm system, level, routes, sizes and connectivity inputs before execution.
6. **Documentation:** use `dimension`, `tag`, views, sheets and schedules only where the live catalogue exposes them.
7. **Inspection:** call `inspect_model` and `query_elements` after each major stage. Verify counts, levels, room areas, wall lengths, opening locations, element marks and required properties. Continue only after the current stage has been inspected.

For a request with three or more stages, keep a visible checklist with one item `in_progress` at a time. Update it after each stage. Do not issue one enormous unreviewed command sequence.

## Residential floor plans

After intake confirms the building form, room programme, plot envelope and access, discover `wall`, `door`, `window`, `floor`, `room`, `dimension` and `tag` schemas.

- Create the ground level and any required upper levels.
- Draw a connected wall network with the approved room boundaries.
- Place doors on their intended host walls; do not use a door command where there is no wall at the specified point.
- Place windows on confirmed walls with a sill below the wall top and the correct family/type.
- Create the floor slab from a simple valid boundary and only approved openings.
- Place each room at an interior point that is genuinely bounded. If a room is unbounded, inspect the warning and fix its boundaries rather than treating it as complete.
- Query the resulting rooms and compare actual area, names, number and level with the approved room programme.
- Add dimensions and tags only after the model geometry is inspected.

Do not silently add or remove a bedroom, bathroom, store or other requested room. If the wall network does not bound a room, report the issue and repair the native geometry before claiming the room exists.

## Guard/watchtower design

A phrase such as "wash tower" may mean a watchtower or security guard tower. Confirm that interpretation before modelling. Ask about the structural system (steel, reinforced concrete, timber or other), occupancy, cabin and platform dimensions, platform elevation, overall height, access (stair or ladder), roof, doors/windows, guardrails, site, wind exposure and geotechnical information.

For a visual BIM concept, discover and use the live commands for:

- `level` and `grid` to establish the reference levels and support grid.
- `structural_column` and `beam` for individually marked support members, using available types and approved dimensions.
- `footing` or `strip_footing` only when a concept foundation is requested and its footprint is known.
- `floor` for the platform/deck, `wall` for the cabin, and `door`/`window` for confirmed openings.
- `stair` or a discovered ladder/access component; `roof` for the roof; and railing commands for edge protection.
- `dimension` and `tag` for drawing annotations and member marks.

After each stage, inspect the model and query the exact elements. Produce a member schedule from actual BIM element IDs/marks and actual type properties. If the model only supports a visual envelope, label it as a concept placeholder. Never turn a placeholder dimension into a selected steel section, reinforced-concrete reinforcement design or proof of capacity.

## Editing an existing BIM model

When the user asks to change a beam, wall, door, room or other existing object:

1. Call `query_elements` with a focused category/field filter.
2. Identify the exact six-digit element ID and verify its current fields.
3. Discover `modify` with `list_commands` to confirm its allowed parameters.
4. Use `execute` with `modify` on that same element ID. Do not delete/recreate it to simulate editing.
5. Query the same ID again and compare before/after values, relationships, mark and level.
6. If multiple elements match or the requested property is not editable, ask the user to identify the target or explain the native limitation.

Preserve element identity, GUID, host/containment relationships, schedules and model history wherever the native operation allows it.

## Discipline-specific decision making

- Architecture: room boundaries, openings, circulation, access, areas and levels.
- Structure: grids, columns, beams, foundations, load-path intent, type properties and connectivity.
- Mechanical: ducts, equipment, clearances, routes and systems.
- Plumbing: pipes, fixtures, gradients, sizes, system connectivity and verified outfalls.
- Electrical: panels, circuits, devices, poles, phases, loads and panel schedules.
- Documentation: views, dimensions, tags, sheets and schedules linked to the real model elements.
- Construction/asset handover: phasing, marks, quantities, classification, required properties and exchange checks.

For each discipline, ask for the inputs that control the design. A command's ability to draw an element does not prove that its engineering design, connectivity, classification or compliance is correct.

## Honest completion report

Report native elements created/edited with IDs, marks, levels and verified properties. State which queries and validation checks were actually run. Separate confirmed model content, concept placeholders, missing information, failed commands, unresolved coordination issues and engineering/regulatory checks not performed.
