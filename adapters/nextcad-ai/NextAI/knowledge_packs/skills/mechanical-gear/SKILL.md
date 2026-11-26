---
name: mechanical-gear
description: Interview, parameterise, model and document gears and related mechanical transmission parts and assemblies.
tags: [mechanical, gear, spur, involute, tooth, transmission, shaft, keyway, assembly, manufacturing]
aliases: [spur gear, helical gear, gear wheel, pinion, gear train, gearbox, toothed wheel]
---

# Gear and mechanical transmission design

## Identify the task

Ask whether the user needs a single gear, mating gear pair, gear train, pinion/shaft assembly or an educational visual model. Clarify the motion/power purpose and whether the output is concept geometry, a dimensioned editable part or a manufacturing definition.

For a conventional external spur gear, establish:
- module (or diametral pitch) and unit system;
- tooth count;
- pressure angle and profile/standard family;
- face width;
- bore diameter, keyway/spline and hub arrangement;
- root/outer geometry assumptions, backlash and profile shift if relevant;
- mating gear tooth count, centre distance and rotation relationship;
- torque, speed, duty cycle, material, heat treatment, lubrication and manufacturing process when functional design is required.

Do not invent module, tooth count, pressure angle, torque or material. If the user only wants a visual concept, label missing functional values as unresolved.

## Understand the geometry and relationships

For a standard spur gear without profile shift, the reference pitch diameter is related to module and tooth count by d = m z. The base circle depends on pitch radius and pressure angle. The involute flank is not a set of arbitrary straight teeth: it is generated from a defined base circle and must be constructed with correct root/tip transitions. A gear pair requires compatible module/pressure angle and an appropriate centre distance and backlash.

Use these relationships to understand the brief, not as an unsourced complete design method. Record the formula version and the assumptions used for any derived dimensions.

## Native operation discovery and build

1. Inspect the available FreeCAD workbenches, add-ons and typed operations for gear generation or involute curves.
2. If a verified gear generator is installed, discover its exact parameters and validate its generated result.
3. If no safe typed gear-profile operation is available, do not invent a tool or emit free Python. Report that the operator's gear-profile generation capability is not yet exposed and offer an explicitly labelled conceptual envelope only.
4. For related shafts, hubs, spacers and plates, use native parametric PartDesign sketches and features when the dimensions are known.
5. Keep each part separate, identify mating axes/faces and assemble with appropriate native joints only when those operations are available.
6. Inspect profile closure, solid validity, concentricity, bore/keyway geometry, tooth count and mating clearances using the native geometry/measurement tools available.

## Drawings and schedules

Where supported, create a dimensioned part drawing and a parameter table containing module, tooth count, pressure angle, pitch diameter, base circle, outer/root dimensions, face width, bore, keyway, material and tolerance. Include a source/status column to show which values are user supplied, derived under a stated convention, modelled or verified.

## Functional-design boundaries

A visually plausible tooth profile does not prove correct involute geometry, contact ratio, backlash, tooth-root strength, pitting resistance, shaft/key strength, bearing life, lubrication or manufacturability. Functional gear design needs the load/speed/duty/material/quality data and an appropriate standard or validated design method. Do not certify a transmission from the viewport or an unverified spreadsheet.
