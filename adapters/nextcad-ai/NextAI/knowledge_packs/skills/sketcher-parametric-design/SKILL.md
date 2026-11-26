---
name: sketcher-parametric-design
description: Design stable editable 2D Sketcher geometry using geometric and dimensional constraints, solver diagnostics, attachments and reference geometry.
tags: [freecad, nextcad, sketcher, sketch, constraints, degrees-of-freedom, parametric, profile, geometry]
aliases: [Sketcher, 2d sketch, constrained sketch, fully constrained sketch, sketch solver]
---

# Sketcher: parametric sketch design

## Why Sketcher matters

A Sketcher sketch is not simply a drawn outline. It is a set of geometric elements connected by geometric and dimensional constraints. The constraints express design intent and control how the sketch responds when dimensions change. Its geometry, attachment/support and solver state are part of the editable model.

## Understand before drawing

Ask for the intended profile, reference plane/face, units, origin/datums, key dimensions, symmetry/equality relationships, required degrees of freedom and whether any geometry should be construction/reference geometry. Clarify whether the sketch will drive a PartDesign feature, an assembly reference or a drawing.

## Construction workflow

1. Inspect the active document, target Body, support face/origin plane and existing feature tree.
2. Select the correct plane and attachment mode; do not assume a sketch belongs to the intended Body.
3. Add geometry in a deliberate order, preserving closed profiles and separate construction geometry.
4. Apply geometric constraints: coincidence, horizontal/vertical, parallel/perpendicular, tangent, equal, concentric, symmetry and other supported types as the design intent requires.
5. Apply driving dimensions only from user/source/approved derived inputs. Do not lock every point merely to make the solver say "fully constrained" if the sketch's design intent should retain motion.
6. Recompute; inspect solver messages, geometry/constraint counts and remaining degrees of freedom.
7. Diagnose over-constraints, redundant constraints, open wires, self-intersection and conflicting geometry. Do not delete constraints blindly.
8. Test important parameter changes when parametric robustness matters and inspect whether the intended relationships are preserved.

## Native tool policy

Use live Sketcher tools/API signatures from the running NextCAD version. The current typed adapter exposes a limited set of lines, circles and polygons plus body-attached sketches; that is not the full Sketcher workbench. Do not invent arcs, slots, B-splines, external geometry or constraint tools unless the live typed registry actually supports them. Mark absent capabilities as adapter gaps.

## Deliverables

For a sketch-driven part, report sketch name, support plane/face, geometry count, constraint count, degrees of freedom, fully-constrained status, driving dimensions and dependent features. Keep the sketch and feature history editable. A fully constrained sketch is not proof that the profile is geometrically or functionally correct.
