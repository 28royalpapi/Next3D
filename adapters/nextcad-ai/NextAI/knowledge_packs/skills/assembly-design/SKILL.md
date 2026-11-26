---
name: assembly-design
description: Plan and build multi-component assemblies using native components, links, placements, joints, constraints and solver verification.
tags: [freecad, nextcad, assembly, joints, mates, components, links, mechanism, kinematics, clearance]
aliases: [Assembly workbench, mechanical assembly, jointed assembly, gear train assembly, component assembly]
---

# Assembly design and kinematic relationships

## Understand the assembly request

Clarify the component list, available native part documents, reference/ground component, mating datums, contact/interface faces, joint type, intended movement, travel/rotation limits, fasteners and whether subassemblies are needed.

Distinguish a physical connection from a kinematic relationship. Two components that touch or overlap visually are not necessarily joined correctly.

## Native assembly concepts

- Component instances and links can reuse a source part without making an unrelated copy.
- Grounding fixes a reference component to the assembly coordinate system.
- Joints define relationships such as fixed, revolute, slider/cylindrical, ball, distance, parallel/perpendicular, rack/pinion, screw or belt where the pinned workbench supports them.
- Mating coordinate systems and connector offsets define the relative placement.
- A solver checks whether the constraint set is solvable, redundant, conflicting or over-constrained.
- Degrees of freedom and motion limits describe permitted movement.

## Workflow

1. Inspect the source parts, units, coordinate frames, reference geometry and file paths.
2. Establish a stable assembly origin and ground the intended reference component.
3. Insert components as native links/instances where reuse is required.
4. Create joints from explicit, inspected mating datums; do not guess FaceN/EdgeN references after geometry changes.
5. Add constraints one logical relationship at a time and solve after each batch.
6. Inspect solver status, component placements, remaining degrees of freedom and motion range.
7. Check interference, clearance, alignment and reachability for the requested operating positions.
8. Create exploded/assembly views, parts lists and drawings where the installed tooling supports them.
9. Save and reopen all dependent documents; verify that source links resolve.

## Safety and completeness

A solved assembly does not prove strength, fatigue life, lubrication, fastener adequacy or manufacturability. A list of component links is not proof of correct mating. Report unsupported joint types and unresolved solver errors honestly.
