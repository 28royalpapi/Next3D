---
name: cam-toolpath-preparation
description: Prepare CNC jobs and toolpaths with stock, work coordinates, fixtures, tools, cutting data, simulation and postprocessors.
tags: [freecad, nextcad, cam, cnc, toolpath, stock, work-offset, fixtures, tools, feeds, speeds, postprocessor, gcode]
aliases: [Path workbench, CAM job, CNC machining, G-code, machining operations]
---

# CAM / CNC toolpath preparation

## Machine and setup intake

Before producing a toolpath, clarify the machine, controller, axis configuration, units, stock material/size, workholding/fixtures, work coordinate system and zero, cutting tools, holders, spindle/feed limits, coolant, operation sequence, tolerance/finish requirement and exact postprocessor.

A generic model or screenshot is not sufficient to choose cutting conditions. Never invent feed rates, spindle speed, depth of cut, step-over, tool diameter, stock size or a controller-specific postprocessor.

## CAM workflow

1. Inspect the final native part and identify machining datums and machinable geometry.
2. Define stock and its location relative to the part and work coordinate system.
3. Define fixtures and clamps; inspect tool access and collision risks.
4. Select exact tools from a verified tool library and record tool/holder geometry.
5. Choose suitable roughing, pocketing, profiling, drilling, facing and finishing operations.
6. Set cutting data from approved machine/tool/material guidance.
7. Generate toolpaths and inspect operation warnings, tool engagement, remaining stock and holder/fixture collisions.
8. Simulate material removal; compare the result with intended geometry.
9. Confirm safe heights, work offsets, tool changes, units and machine-specific output settings.
10. Post-process only with the exact verified controller postprocessor. Inspect the generated code and have a qualified operator approve before machining.

## Capability and safety

CAM support can vary across FreeCAD releases; inspect the exact Path/CAM API and postprocessors in the running build. Toolpath creation is not proof of collision-free or safe machining. Never send G-code to a machine or claim it is ready without explicit review and simulation.
