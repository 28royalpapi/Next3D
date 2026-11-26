---
name: engineering-operator-method
description: Universal method for understanding an engineering request, interviewing the user, discovering native operations, planning, building in stages, verifying and documenting unfamiliar designs.
tags: [engineering, operator, planning, native-operations, verification, documentation]
aliases: [engineering operator, unfamiliar design, project workflow, design automation]
---

# Engineering operator method

Use this skill for every substantial CAD/BIM request. It teaches the operator how to work; it does not replace the subject-specific skill or the native command registry.

## Two kinds of understanding are required

1. **What is being designed:** purpose, discipline, components, expected behaviour, constraints, design conventions, important dimensions, interfaces, deliverables and engineering checks.
2. **How the installed application can build it:** native workbenches, object model, typed tools, commands, feature history, parameters, constraints, document relationships, undo, recompute, inspection, save/reopen and exchange.

Neither is sufficient alone. A perfect command sequence can build the wrong thing; good engineering intent without native operating knowledge cannot produce an editable model.

## Before proposing geometry

- Identify the application and exact running version. Read the live project/document state.
- Classify the request: create, edit, inspect, document, export, analysis, coordination or conversion.
- Identify the object/system, user purpose and required deliverable.
- Retrieve the most relevant engineering skill and the current native manuals/tool descriptions.
- Ask only questions that change the next design decision. Preserve answers already given. Separate confirmed values, proposals, native defaults, derived values and unresolved questions.
- Determine whether the requested task is a concept, schematic, dimensioned design, coordinated BIM model, manufacturing definition or engineering analysis.
- Never infer dimensions, units, material grades, loads, soil properties, electrical ratings, tolerances, standards or performance requirements.

## Native capability discovery

- Prefer typed native tools and exact versioned schemas.
- Discover the relevant workbench/API/command before composing an unfamiliar operation.
- Filter the available tool catalogue by task, but never hide the fact that other capabilities exist.
- A command visible in the GUI is not automatically safe to invoke from an AI plan. The command must have a reviewed adapter, validated inputs and an explicit permission policy.
- If a needed native operation is not represented by an approved typed tool, say exactly what is missing. Do not invent tool names or paste Python, macros or shell code.

## Build as an observable operation sequence

1. Inspect the existing model and identify target objects by stable native identity.
2. Write an ordered plan with each stage's purpose, inputs, preconditions, expected native objects and verification checks.
3. Resolve essential unknowns and obtain approval for the plan.
4. Execute a coherent stage, not a giant opaque design dump.
5. Recompute and inspect the real native model after each stage.
6. Compare actual geometry/properties/relationships with intended postconditions.
7. On failure, capture the error, roll back the affected transaction, inspect the new state and choose a revised operation. Never pretend the failed operation succeeded.
8. Keep components separate and meaningfully labelled where future editing, assembly or schedules require it.
9. Preserve feature history, constraints, object identity and hosted relationships during revisions.

## Make the documentation from the model

When relevant, create dimensions, annotations, drawing views, sheets and schedules. Extract every reported quantity from native properties or verified measurements. A schedule should identify its object/element source and unit. Keep user-confirmed, proposed, calculated and measured values distinct.

## Final reporting

Report what was actually created or changed; native object/feature count; dimensions and units; recompute/geometry checks; constraints and relationships checked; schedule/drawing deliverables; save/reopen and exchange results; unresolved assumptions; and engineering checks not performed. A viewport image is supplementary evidence, not proof of correct geometry, editability or engineering adequacy.
