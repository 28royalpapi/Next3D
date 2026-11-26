---
name: water-storage-tower
description: Clarify, plan, model and document elevated water storage tanks, support towers, platforms, access and associated components.
tags: [water, storage, tower, tank, wash-tower, hydraulic, civil, structural, steel, reinforced-concrete, platform, ladder]
aliases: [water tower, watertower, wash tower, elevated tank, elevated water tank, storage tank tower]
---

# Elevated water-storage tower

First confirm that the user means a water-storage tower. Do not interpret "wash tower" as a known structure without confirmation when the meaning is uncertain.

## Design intake

Ask for the information that affects the configuration:

- Required storage capacity and whether it is usable or gross capacity.
- Tank form: cylindrical, rectangular, spherical, or another form.
- Tank diameter/plan dimensions, height/depth and operating water levels if known.
- Tank base elevation and total tower height.
- Support system: steel frame, reinforced-concrete frame, shaft/shaft-and-brace, or another arrangement.
- Support footprint, number and layout of legs/columns, bracing arrangement and platform dimensions.
- Access: ladder or stair, cage/landing requirements, guardrails and maintenance access.
- Pipe inlet/outlet, overflow, drain, vent and access hatch locations if they are part of scope.
- Site survey, terrain, wind exposure, geotechnical information and project location.
- Is the request a visual concept, dimensioned coordination model or engineered construction design?

Ask whether the user has a preferred section/material. Do not guess steel grades, concrete grades, plate thicknesses, wall thicknesses, foundation dimensions, wind loads, water loads or safety factors.

## Component model

Keep the model decomposed and labelled:
- tank shell/body and roof/base;
- columns or supporting shaft;
- beams/ring beams and bracing members;
- deck/platform and maintenance landings;
- access ladder/stair, handrails and guardrails;
- pipe nozzles and other interfaces;
- foundation placeholders only when the scope and inputs are clear.

A cylindrical tank can be represented with native cylindrical geometry for a concept envelope. Columns and beams may use supported Arch structural objects or editable Part/PartDesign members. Do not mistake a solid cylinder for a fabricated shell: wall thickness, roof details, stiffeners and connection details need explicit geometry and proper tools.

## Build sequence

1. Establish axes, levels, origin, footprint and tank/support envelope.
2. Model the support system as separate named members.
3. Inspect column positions, bracing layout and member elevations.
4. Model the platform/ring beams and access arrangement.
5. Model the tank body and roof/base geometry.
6. Add openings/nozzles and service interfaces when locations and dimensions are supplied.
7. Add dimensions, component marks and a member schedule.
8. Recompute, inspect geometry and save/reopen before reporting.

For a large tower, split the work into approved stages. Let the user see the native model develop; do not create an image or imported mesh and call it a model.

## Schedule outputs

When supported, create a model-derived table:
- mark and native object ID;
- member/component type;
- section or geometric envelope;
- width/depth/diameter and thickness where actually modelled;
- length/elevation and placement;
- material property only if assigned in the native model;
- volume/mass only when material/density is known and calculation is valid;
- status: concept placeholder, user-confirmed, modelled, measured or independently checked.

Use actual native properties and geometry measurements. A guessed member section must not appear as selected structural design.

## Engineering validation boundaries

A 3D tower concept is not a structural design. Capacity, hydrostatic pressure, shell buckling, wind loading, seismic loading, frame stability, connection design, fatigue, corrosion, foundation bearing/settlement and geotechnical adequacy require appropriate design inputs and validated calculation/analysis methods. A visible FEM result is not proof unless loads, constraints, materials, mesh quality, solver and result interpretation are checked. Do not claim construction readiness or safety without qualified independent review.
