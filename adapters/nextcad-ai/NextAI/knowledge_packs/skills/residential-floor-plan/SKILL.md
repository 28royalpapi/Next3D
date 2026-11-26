---
name: residential-floor-plan
description: Interview and model residential floor plans, room programmes, circulation, wall layouts, openings, dimensions and room schedules.
tags: [architecture, residential, house, bedroom, floorplan, bungalow, duplex, room-schedule, walls, doors, windows]
aliases: [three bedroom, 3 bedroom, four bedroom, house plan, bungalow, duplex, maisonette, residential floor plan]
---

# Residential floor-plan design

## Understand the brief before drawing

A bedroom count is not a complete floor-plan specification. Ask the user the high-value questions that determine the room programme:

- Is it a bungalow or a storey house? How many floors?
- How many bedrooms are master bedrooms?
- How many toilets/bathrooms in total? Which are ensuite, shared, or guest WC?
- One sitting/living room, or a formal sitting room plus a separate family lounge?
- Which additional spaces are needed: dining, kitchen, pantry, store, laundry, study, guest room, prayer room, maid's room, carport?
- What are the plot width and depth, road/access side, north/orientation if known, and desired setbacks?
- Is the deliverable an unscaled adjacency concept, dimensioned schematic, site-fitted layout or coordinated 3D BIM model?

Do not assume one bathroom per bedroom. Do not decide the master-bedroom count or lounge count on the user's behalf. Carry confirmed answers forward and do not repeat questions.

If plot dimensions are missing, offer an unscaled relationship concept only. Room sizes, wall thicknesses, setbacks and circulation widths must be confirmed or explicitly proposed for review; do not silently present defaults as regulations.

## Convert the brief into a room programme

Record each room as a distinct item with:
- room mark and name;
- floor/level;
- required count;
- intended use and privacy/access relationships;
- user-confirmed dimensions or proposed dimensions clearly marked;
- adjacency constraints and openings needed.

Check the room-count arithmetic. For example, a three-bedroom brief must still distinguish the number of master rooms, ensuite bathrooms, shared bathrooms and guest WC. Do not infer those counts from the phrase "three-bedroom".

## Plan layout before wall construction

1. Establish drawing units, origin, orientation, plot/site envelope and building footprint.
2. Group spaces into public, private and service zones.
3. Arrange the entry, living spaces, bedrooms, wet areas, kitchen and circulation according to the confirmed relationships.
4. Check that the plan fits the envelope and has a coherent circulation route. Identify privacy conflicts, dead ends and overlapping spaces.
5. Obtain approval of the room adjacency/layout plan before committing to detailed geometry.

## NextCAD native build strategy

Use the live tool catalogue first. Current typed tools may support:
- Draft outlines/closed wires for the footprint and room-zone concept;
- Draft text for room names and marks;
- Draft dimensions for measured layout dimensions;
- Arch walls for wall paths, height and thickness;
- Arch structural elements for supported structural placeholders.

A 2D wire labelled "Bedroom 1" is a zoning outline, not a native room/space object. A wall solid does not by itself create a hosted door or window. Use those element types only when the installed native tools actually expose them. If a needed operation has no safe typed tool, report the coverage gap rather than fabricate a tool call.

Build exterior envelope, internal partitions, openings, stairs and upper floors in separate visible stages. Reinspect dimensions and room boundaries after each stage. Keep walls, floors, doors/windows and rooms separate when the native model supports those relationships.

## Schedules and drawings

Create an appropriate room schedule and a wall/opening schedule when supported. Room schedule fields: mark, room name, level, modelled width, modelled length, calculated area, use/occupancy note, value status (confirmed/proposed/measured) and object ID. Wall schedule fields: wall mark, level, type, modelled height, modelled thickness, measured path length, material (only if actually assigned) and object ID.

Create overall dimensions, important room dimensions, labels, sections/elevations and drawing sheets where native tooling supports them. Report which values were measured from the actual model and which remain proposed.

## Checks and boundaries

- Verify room counts against the agreed brief.
- Verify room zones fit within the building envelope and do not unintentionally overlap.
- Check circulation/access relationships, openings, level associations and wall/room boundaries where the native model exposes them.
- Save and reopen; confirm the model and schedule remain linked to the correct elements.
- Do not claim planning approval, accessibility compliance, fire compliance, structural adequacy or buildability without the relevant site data, jurisdiction, standards and independent checks.
