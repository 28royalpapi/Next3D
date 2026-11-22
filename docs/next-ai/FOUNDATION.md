# Next AI — First Law, Capability Map and Build Plan

Status: research and architecture phase. No third-party assistant has been installed into either native application yet.

## First law

**Next AI must understand the native application before it is allowed to operate it.**

The native CAD/BIM engine remains the source of truth. AI proposes an understandable, parameterised sequence of native operations; the application executes those operations; the engine validates the resulting model. AI must not claim success when the native model is invalid, incomplete, or not saved.

This law applies to every discipline and every future tool pack.

### Required behaviour for every modelling request

1. Understand the current document and active application, including units, levels/planes, objects, parameters, dependencies and existing feature history.
2. Turn the request into a structured specification: named dimensions, units, constraints, materials, relationships and intended deliverables.
3. Ask about any missing information that materially changes the design. Do not silently invent dimensions, structural loads, electrical ratings, code requirements or site assumptions.
4. Show an ordered plan before a large or consequential change.
5. Execute through typed native commands and normal application transactions. Keep each action inspectable and undoable.
6. Recompute and validate the actual geometry and project data after each important feature.
7. Report warnings and failed checks honestly. Never equate a plausible picture with a valid engineering model.
8. Save and reopen the native project in acceptance tests. Exported images and drawings are deliverables, not substitutes for the editable source model.
9. Keep offline/local inference as the default. No project data may be sent to a remote service without an explicit, informed user choice.

## What each native application gives Next AI

The two engines remain separate. A shared AI orchestrator may serve both, but each application has its own tool adapter, object model, file format, tests and specialist knowledge.

### NextCAD — FreeCAD

FreeCAD is a parametric, unit-aware CAD/CAE platform built on a geometry kernel. The capability inventory must include, at minimum:

| Capability area | What the AI must learn |
| --- | --- |
| Sketcher | Geometry, dimensional and geometric constraints, degrees of freedom, solver state, external references and fully constrained profiles |
| Part / Part Design | Solids, bodies, features, pads, pockets, revolves, lofts, sweeps, holes, patterns, fillets, chamfers and booleans |
| Assemblies | Components, placements, 3D constraints, mates, subassemblies and motion/animation where supported |
| Draft / TechDraw | 2D geometry, annotations, dimensions, projections, sections, hatching, drawing sheets and export |
| BIM / Architecture | Sites, buildings, storeys, walls, doors, windows, slabs, roofs, spaces and IFC exchange |
| FEM / CAE | Analysis setup, materials, constraints, loads, meshes, solvers, result fields and verification |
| CAM / CNC | Jobs, stock, tools, operations, toolpaths, post-processors and manufacturing constraints |
| Mesh / 3D printing | Mesh creation, inspection, repair, tessellation and export |
| Surface / reverse engineering / points | NURBS surfaces, imported scans, point clouds, alignment and reconstruction |
| Robotics / automation | Robot models, trajectories, macros, Python APIs and workbench extensions |
| Spreadsheets / expressions | Named variables, formulas, expressions, quantities, units and dependency links |
| Interoperability | FCStd plus formats such as STEP, IGES, OBJ, STL, DXF, SVG, IFC and other formats supplied by workbenches |

This is a capability map, not a claim that every workbench is installed or every external add-on is part of the base application. The inventory must record whether each operation is native, part of a pinned add-on, or not yet supported.

References:
- https://www.freecad.org/features
- https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Category_Workbenches.md
- https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/TechDraw_Workbench.md

### Next BIM — BIMCraft

BIMCraft is a separate building-information-modelling engine. Its capability map must include:

| Capability area | What the AI must learn |
| --- | --- |
| Project and spatial structure | Projects, sites/buildings, levels, grids, coordinates, project units and parameters |
| Architecture | Walls, doors, windows, floors, ceilings, roofs, rooms/spaces, stairs, ramps, railings, shafts and dormers |
| Families and types | Family geometry, type parameters, instance parameters, materials and reusable building components |
| Structural | Beams, structural columns, footings, strip footings and structural floors |
| Plumbing / mechanical services | Fixtures, pipes, runs, slopes, sizes, materials and supported system relationships |
| Electrical / data / lightning protection | Devices, panels/racks, cable trays, conduits, wires, air terminals, down conductors and earthing elements |
| Views and documentation | Plans, sections, elevations, 3D views, view ranges, visibility/graphics, annotations, dimensions, tags and sheets |
| Quantification | Schedules, fields, filters, grouping, calculated values, quantities and totals |
| Interoperability | Native BIMCraft project files and IFC import/export, with round-trip checks |

Important boundaries must be recorded, not hidden. For example, a pipe or cable run existing in the model does not automatically prove that a fully connected, rules-checked MEP network or electrical circuit engine exists. Each category needs a tested support status.

BIMCraft already has an in-app Assistant and an MCP/CLI command interface in the pinned source. The existing Assistant supports remote model providers (Anthropic, OpenAI and Gemini) and performs project mutations through the same native command engine. The Next AI work should extend this foundation with a local/offline provider and improve its engineering knowledge and validation, rather than duplicate the assistant UI or bypass the BIMCraft command layer.

References:
- https://github.com/IPedrax/BIMCraft
- https://github.com/IPedrax/BIMCraft/blob/main/docs/areas/assistant.md
- https://github.com/IPedrax/BIMCraft/blob/main/docs/areas/structure-and-mep.md
- https://github.com/IPedrax/BIMCraft/blob/main/docs/disciplines.md

## Existing AI projects to study before integrating anything

| Project | Useful contribution | Current limit or risk | Decision |
| --- | --- | --- | --- |
| [FreeCAD-AI-Assistant](https://github.com/iplayfast/FreeCAD-AI-Assistant) | LGPL-2.1-or-later; one registry for GUI, console and MCP; local OpenAI-compatible providers; PartDesign, BIM and FEM handlers; tool profiles | Includes unrestricted Python execution in the live FreeCAD process. Its own docs warn that the RPC endpoint must remain loopback-only. Tool calls and UI compatibility need testing against our exact FreeCAD build | Highest-priority source to audit; reuse only after security, compatibility and licence review |
| [FreeCAD Agent](https://github.com/nasdomak/freecad-agent) | LGPL-2.1-or-later; local Ollama loop; perception → plan → act → repair; deterministic clarification; undoable transactions; useful tests | MVP focused on 20 structured Part-workbench commands; the README reports Windows testing and limits with small local models | Reuse its agent-loop and verification lessons; not the complete NextCAD capability layer |
| [FreeCAD MCP](https://github.com/neka-nat/freecad-mcp) | Typed tools, explicit schemas, document inspection and auditable native operations | Experimental and bounded; its strongest verified work is constrained Sketcher automation, not all-purpose CAD generation | Study its strict contracts and solver-validation approach |
| [Chat CAD](https://github.com/Vittuu/freecad-chatcad) | Selection-aware and image/sketch input, local provider integration, parametric model workflow | Alpha; the authors report local-model failures on real multi-feature parts in their own tests | Study UI and visual-input ideas; do not treat its local-model results as proven |
| [FreeCADTool](https://github.com/Graphene-Lab/FreeCADTool) | Typed CAD operations and broad PartDesign operations over a local bridge | AGPL-3.0 and a separate AgentBridge host; distribution and dependency implications need review | Do not copy into NextCAD without a deliberate licence/architecture decision |
| [KERF](https://github.com/wearethefoos/kerf) | Apache-2.0; clarify → plan → generate → execute → verify → repair; structured parameter and training-example schemas; geometry sidecar and evaluation plans | Targets Build123d, not the FreeCAD or BIMCraft native engines. The project describes its current state as early foundations, with no fine-tuned model or completed data pipeline | Reuse the general methodology and schema ideas, not its geometry engine |

## The model and the data

We should not train a foundation model from scratch or build a dataset of pictures alone as the first step.

A rendered image can show what a model looks like, but it usually cannot tell us the exact feature history, constraints, units, named parameters, topology, material properties, system relationships or why the design was built that way. The training record must link visual references to the native, editable engineering data and to a verified sequence of operations.

A Next AI training example should contain:

- the user's request and any reference drawing/image;
- the clarified specification, assumptions, named parameters and units;
- the native document state before the change;
- the ordered native tool/command sequence and arguments;
- the native document state after the change;
- the saved native project and, where appropriate, exported IFC/DXF/PDF/STEP or other outputs;
- validation results such as geometry validity, dimensions, volumes, sketch solver state, model checks, IFC round-trip results and warnings;
- source provenance, licence, permission status and any withdrawal identifier.

Images remain important. We should generate or collect plan, elevation, section, isometric, detail and rendered views that are paired with the exact native models that produced them. For 2D drawings, preserve vector dimensions and geometry where available; do not reduce every source to a raster image.

Every dataset item must have traceable rights. Public availability alone is not permission to train on a drawing, model, tutorial or image. Synthetic examples should be generated from our own native engines and validated automatically.

KERF's training-example schema is a useful reference because it stores state, named parameters, feature history, operation, code, validation result and source licence/permission metadata:
- https://github.com/wearethefoos/kerf/blob/main/schemas/training_example.schema.json

## Recommended architecture

1. **Shared agent runtime:** clarification, project understanding, planning, tool selection, progress, cancellation, memory, validation and repair.
2. **NextCAD adapter:** typed FreeCAD operations and read-only inspection tools, with separate profiles for Sketcher/PartDesign, Draft/TechDraw, BIM, FEM, CAM, assembly and other supported workbenches.
3. **Next BIM adapter:** BIMCraft commands/MCP tools for architecture, structure, MEP, views, schedules, families and IFC.
4. **Local model provider:** OpenAI-compatible local endpoint first (Ollama or llama.cpp-compatible server); no cloud key required. Later, package the runtime and quantized model weights as an offline model pack with a separately tested CPU/GPU path.
5. **Knowledge retrieval:** local, versioned manuals, API references, command schemas, examples, standards and validated project patterns. The correct knowledge pack is selected by application, version and discipline.
6. **Visual understanding:** a vision-capable local model or a separate local vision component for drawings, screenshots and user sketches. Its interpretation must resolve into explicit parameters and native operations before execution.
7. **Dataset and evaluation pipeline:** collect, normalize, validate, de-duplicate, license-check and version examples. Fine-tuning is a later measured step, not the starting point.

The same AI runtime must never merge the CAD and BIM engines or make a single generic document model for both products.

## Release gates

| Gate | Pass condition |
| --- | --- |
| A. Capability inventory | Every relevant workbench, command family, file type and known limitation is documented with a tested/pinned version |
| B. Tool contract | Read-only inspection and typed write operations are schema-validated; untrusted Python/shell execution is disabled by default |
| C. Native verification | Create/edit/recompute/undo/save/reopen workflows pass on real application documents |
| D. Local inference | The selected local model completes measured tool-calling tasks with no remote network access |
| E. Engineering evaluation | Results meet dimension, constraint, topology, project-integrity and IFC/drawing checks; failures are recorded, not hidden |
| F. Dataset quality | Every example is executable or otherwise verifiable, deduplicated and provenance/permission tracked |
| G. Fine-tuning | A fine-tuned model beats the same base model plus tools/retrieval on a held-out benchmark |
| H. Offline package | Fresh installs can run the selected model locally on each supported OS, with honest hardware requirements |

## Immediate work order

1. Finish the native NextCAD and Next BIM build/test/launch acceptance already running in CI. Source checkout and patch application have passed; that alone is not full app acceptance.
2. Complete the FreeCAD and BIMCraft capability inventory, including what is native, add-on dependent, partially implemented or missing.
3. Audit the LGPL FreeCAD-AI-Assistant tool registry and the existing BIMCraft Assistant. Identify exactly what can be reused safely and where the local-provider adapters fit.
4. Design and freeze the shared training-example schema plus separate NextCAD and Next BIM operation schemas.
5. Build a small, high-quality benchmark and synthetic sample set before planning large-scale collection or model training.
