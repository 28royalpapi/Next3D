---
name: partdesign-feature-modelling
description: Build editable Part and PartDesign models using feature history, additive and subtractive operations, topology-aware editing and solid validation.
tags: [freecad, nextcad, part, partdesign, solid, feature-tree, pad, pocket, revolve, loft, sweep, boolean, fillet, chamfer]
aliases: [PartDesign, Part workbench, parametric part, mechanical modelling, solid modelling]
---

# Part and PartDesign feature modelling

## Choose the right modelling approach

Use Part primitives and direct shape operations when the user needs a suitable independent shape or assembly envelope. Prefer PartDesign Body feature history when the component should remain an editable parametric solid with sketches and named features. Do not mix a static mesh into a feature-history workflow and imply it has the same editability.

## PartDesign model logic

A Body owns an ordered sequence of features. Additive features add material; subtractive features remove material; dress-up operations alter edges/faces; patterns and mirrors repeat existing features. Every feature depends on upstream geometry and references. A change to an upstream sketch or face may alter or break downstream references.

Understand:
- Body and its current Tip;
- support/attachment of sketches and datum references;
- Profile, Base, Tool and other feature links;
- pad/pocket depth, direction, symmetry, through-all and other supported extents;
- revolve axis/angle; loft/sweep sections and paths;
- boolean operands and result shape;
- fillet/chamfer selected topology;
- mirror/pattern source feature, direction/axis, angle/span and occurrence count;
- recompute states, shape validity, solid count, volume and bounding box.

## Modelling sequence

1. Confirm function, interface geometry, envelope, material/process intent and critical dimensions.
2. Inspect the Body, Tip, sketches, parameters and dependencies.
3. Create or revise an appropriately constrained profile.
4. Apply the smallest meaningful native feature; recompute and inspect before adding the next.
5. Use exact selected faces/edges from a fresh geometry inspection. Topological Edge/Face indices can change after upstream edits; never reuse stale edge indices.
6. Prefer the Body's current Tip when adding a feature. Preserve the order and avoid creating a new branch that silently drops later features.
7. Check expected postconditions: non-null shape, valid shape, expected solid count, volume increase/decrease, bounds, profile status and feature links.
8. Save/reopen and test parameter changes when the design requires stable parametric behaviour.

## When Part is more appropriate

Part operations can create primitives, transforms, booleans, copies and derived BRep geometry. A generic derived Part shape may be geometrically valid but not have the editable PartDesign feature history of a Body. Report that distinction.

## Current adapter coverage boundary

NextAI currently has typed paths for selected primitives, a constrained Sketcher subset, Body/sketch creation, Pad/Pocket, variables/expressions, boolean operations, transforms, duplication, fillet/chamfer, and linear/polar patterns. This does not yet cover every Part/PartDesign command or prove runtime success for all FreeCAD versions. Use live discovery and report uncovered features rather than guessing tool names or argument schemas.
