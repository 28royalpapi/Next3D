# Next AI Engineering Knowledge Packs

These compact documents provide task guidance for the local NextAI operator. They are indexed locally by the NextCAD adapter and do not replace the native FreeCAD documentation, native BIMCraft commands, engineering calculation software or applicable standards.

The pack is deliberately small and text-only. It adds no second model and no geometry engine. For each task, NextAI must retrieve only the relevant sections and inspect the running application's real capabilities.

## Included domains

- `cad/parametric-cad.md`: editable CAD construction, sketches, feature trees, topology-aware editing and drawings.
- `aec/bim-construction.md`: architecture, BIM, structure, MEP, documentation and IFC workflow.
- `engineering/design-validation.md`: engineering inputs, units, calculation discipline, assumptions and verification boundaries.
- `drawing-intake.md`: image/drawing interpretation, scale, annotation and uncertainty rules.
- `design/design-intake.md`: guided requirements interviews for residential/commercial plans, vehicles and consumer products, mechanical parts, assemblies, sheet-metal enclosures, manufacturing drawings, CAM setup, BIM projects, renovations and civil infrastructure.
- `design/design-execution.md`: staged native model creation, editable feature history, room zoning, watchtower component schedules, vehicle packaging, geometry-aware primitive selection, mechanical parts, in-place editing, BIM element workflows and honest validation reports.
- `bim/native-command-playbook.md`: BIMCraft command discovery, staged building creation, room validation, watchtower/guard-tower workflows, in-place element editing and BIM reporting.

## Native CAD operation coverage

The typed NextAI registry now includes native operations for two-object booleans, relative/absolute transform, independent object duplication, fillet and chamfer, PartDesign linear/polar patterns, and native model-derived Spreadsheet schedules. PartDesign Body fillets/chamfers and patterns remain native features in the Body history. For generic Part shapes, fillet/chamfer returns a separate derived shape and reports that it is not a parametric Body feature.

Generic GUI command execution is restricted to a reviewed view-only allowlist. The complete live GUI command registry is for discovery and curriculum coverage, not blanket permission to run any command. New modelling capabilities must be added as typed, validated operations with explicit side effects and verification.

## Progressive engineering skills

The `skills/` directory uses local Markdown `SKILL.md` files. Every skill has a short name/description/tags/aliases entry in the catalogue. At request time, the local registry ranks the skills and loads only the best-matching full instructions (up to three). This is progressive disclosure for a small local Qwen student: it receives the domain knowledge needed for the current design, not every engineering procedure in every turn.

A skill teaches the student what the object/system is, what questions to ask, what components and deliverables matter, and how to stage the work. It does not execute Python or authorize an operation. The exact NextCAD tool schemas, live workbench/API inventory and native validators remain authoritative.

Initial skills cover:
- general engineering-operator method;
- residential floor-plan intake, room programme, wall/opening stages and room/wall schedules;
- elevated water-storage towers;
- mechanical gears/transmissions;
- vehicle packaging;
- electrical control panels;
- civil roads and drainage.

These are authored knowledge lessons (L0). They are not native execution examples, proven engineering designs, or evidence of a trained model. Missing native functions must remain visible as capability gaps. For example, a gear skill cannot make an involute gear generator available if the running FreeCAD installation exposes no reviewed native operation for it.

## Authority order

1. The open native project and its live application version.
2. The exact native tool schema and command implementation.
3. The native application's own documentation and test results.
4. These NextAI workflow notes.
5. Retrieved third-party examples, subject to their recorded licence and validation.

An unavailable capability must be reported as unavailable. A knowledge-pack paragraph never authorizes a command or proves that a design is safe.
