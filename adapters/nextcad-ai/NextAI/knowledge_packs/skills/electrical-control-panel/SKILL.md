---
name: electrical-control-panel
description: Clarify and model electrical control panels, enclosures, DIN rails, devices, cable routes and schedules with explicit electrical design inputs.
tags: [electrical, panel, switchgear, cabinet, control, wiring, circuit, cable, enclosure, MEP]
aliases: [electrical panel, control cabinet, switchboard, distribution board, MCC, electrical enclosure]
---

# Electrical control panel and cabinet

## Intake before layout

Establish:
- panel purpose and supply system: nominal voltage, phase count, frequency, earthing arrangement and source;
- circuit/load list with equipment names, ratings, starting/inrush characteristics and duty;
- required protection and control functions;
- fault level or source impedance and any verified protective-device selection basis;
- enclosure environment, ingress protection target, location, ventilation, heat dissipation and access;
- approximate enclosure width/height/depth or installation-space limit;
- device list (breaker, contactor, relay, PLC, VFD, PSU, terminal blocks, meters, isolator);
- cable entry, gland plate, trunking, segregation, PE/neutral bars and maintenance clearances;
- governing jurisdiction, standards and project deliverables.

Do not choose breaker ratings, conductor sizes, fault ratings, protection settings, IP rating or thermal design from intuition. Ask for the design basis or mark the values TBD.

## Build the physical model

Decompose the cabinet into:
- enclosure body, door and removable panels;
- mounting backplate and DIN rails;
- device/component placeholders with meaningful tags;
- cable ducts/trunking and cable-entry regions;
- terminal rows, PE/neutral bars and interfaces;
- labels, dimensions and door-mounted devices.

Establish an enclosure coordinate system and device mounting plane. Place large equipment first, then rails and devices, then ducts and cable paths. Use the actual native workbench/tools exposed by this NextCAD installation. A device cuboid is a packaging placeholder unless it has a verified family/part geometry.

## Native capability rules

- Discover the current Part, PartDesign, Draft, BIM and electrical-related tools/add-ons.
- Use parametric PartDesign components where meaningful; use separate objects/labels so the panel schedule can map to the model.
- Do not claim a circuit is electrically connected because two solids touch visually. Require explicit native connectivity/system objects or verified wiring records.
- Do not invent an electrical tool name. If the current typed registry cannot create circuit/schematic connectivity, report that limitation and keep the model at a physical-layout level.

## Schedules and checks

Where the model/toolset supports them, create:
- panel/device schedule: tag, description, quantity, manufacturer/type if confirmed, modelled envelope and location;
- circuit schedule: circuit ID, load, voltage, phase, protection, cable and status (only from approved inputs);
- cable/terminal schedule and drawing views.

Extract locations and dimensions from native objects. Electrical ratings and protection properties must come from confirmed project data, not visual geometry.

## Safety boundary

Panel geometry is not an electrical design. Short-circuit, protection coordination, conductor sizing, earthing, temperature-rise, arc-flash and statutory checks require suitable calculations, validated libraries, source data and qualified review. Never claim energisation or compliance from a 3D layout.
