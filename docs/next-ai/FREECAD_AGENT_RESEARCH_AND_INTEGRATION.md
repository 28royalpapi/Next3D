# FreeCAD AI and agent research for the NextAI operator

**Research date:** 2026-11-26  
**Target branch:** `nextai-operator-foundation`  
**Purpose:** identify reusable ideas and code references for making the Qwen3.5-0.8B student a native engineering operator inside NextCAD, without replacing the Next3D architecture or treating image imitation as CAD competence.

## Decision

Do **not** install a second AI workbench wholesale or replace the Next3D student/orchestrator. Use selected projects as implementation references, then implement and test the appropriate patterns in Next3D's own typed native adapter.

The strongest references are:

1. **ghbalf/freecad-ai** — closest overall agent-workbench reference: Plan/Act, structured tool calls, skill packs, tool reranking, document context, repair, and MCP exposure.
2. **blwfish/freecad-mcp** — broader specialised FreeCAD tool/verification catalogue to study for native operation coverage.
3. **nasdomak/freecad-agent** — particularly clear small agent loop: perceive, plan, execute one feature, inspect the actual geometry, and repair/replan.
4. **pitbuild/freecad-mcp-headless** — useful reference for headless model inspection, save/export, measurement and repeatable native validation.
5. **ahelja/FreeCAD-MCP** and **CREATeNG/freecad-mcp-bridge** — useful transport and GUI-thread/permission design references; not training systems.

These are reference implementations, not proof that NextCAD has gained their abilities or that Qwen3.5-0.8B can already use them.

## Repository review

### 1. ghbalf/freecad-ai — closest agent-workbench match

Repository: https://github.com/ghbalf/freecad-ai  
Reviewed source revision: `41f03d7af3f4aec932d70d36fc8f1a99ae2ad25e`  
Published package version at review: `0.35.0-alpha`, dated 2026-11-22.  
Code licence: LGPL-2.1-or-later. Icons: CC0-1.0.

Useful mechanisms:

- Plan mode shows generated code for review and provides a separate check/fix loop.
- Act mode defaults to structured FreeCAD tool calls. Its documented tool surface includes primitives, PartDesign bodies, sketches, pads, pockets, revolves, lofts, sweeps, booleans, fillets, chamfers, shells, patterns, measurement, face/edge inspection, document state, parameter changes, spreadsheets and expressions.
- Reusable skills contain instructions and may have a deterministic Python handler. Skills can load reference files only when needed.
- Tool reranking reduces the number of tool schemas sent to the model for a given request.
- It can expose its FreeCAD tools through an MCP server for an external agent.
- It includes project-level instructions and object/face/edge references, which help an agent identify the actual native geometry being discussed.
- Its documentation includes a skill-optimisation loop that tests a skill, evaluates the result and revises the instructions.

Important limitations and risks:

- The repository explicitly labels itself alpha and warns about crashes from LLM-generated code.
- Its documented tool list is not a complete inventory of every FreeCAD workbench/API, and it does not establish full BIM/TechDraw/CAE/CAM coverage.
- It retains arbitrary Python code-execution paths. The built-in MCP server documentation says it is unauthenticated by default unless a bearer token is configured.
- It is an assistant/workbench, not a comprehensive engineering curriculum or a validated general-purpose CAD operator.
- Its own changelog reports a sizeable system-prompt-plus-tool footprint; this supports using NextAI's dynamic capability retrieval instead of sending every native operation schema to a small model on every turn.

**What Next3D should learn from it:** Plan/Act separation, a reusable typed tool registry, tool reranking, progressively loaded skill references, document-aware context and systematic skill tests. Reimplement these behind Next3D's permissioned action-plan contract. Do not enable unrestricted Python execution in the released student.

### 2. blwfish/freecad-mcp — broad native-tool and verification reference

Repository: https://github.com/blwfish/freecad-mcp  
Reviewed source revision: `07e1ca99966cb21f9308d67d1f7c31edc9576aba`  
Licence: LGPL-2.1.

Its published guide describes 41 MCP tools arranged as 16 multi-operation dispatchers plus 25 single-purpose tools. The documented native areas include:

- Sketcher geometry and constraints;
- Part and PartDesign features;
- Assembly components, joints and solving;
- Draft arrays and annotation-related operations;
- Spreadsheet and VarSet parametric data;
- CAM jobs, operations and tools;
- mesh conversion and validation;
- measurements, spatial queries, interference/clearance checks;
- geometric verification, fixture comparison and model lint;
- API introspection, operation logs, tracebacks, async jobs and cancellation.

The guide reports manual client tests using Qwen2.5-Coder-14B, Qwen3-32B and Gemma 4 E4B. That is evidence of protocol/tool round-tripping with those larger models, not evidence for Qwen3.5-0.8B or for every operation in every platform/build.

**What Next3D should learn from it:** the distinction between modelling tools and verification tools; operation families; API introspection; geometry checks; model lint; regression checks; async/cancel controls; and structured error reporting. Use this as a coverage checklist, then verify each operation against the exact NextCAD build and expose it through reviewed typed adapters. It is not a drop-in complete NextCAD API.

### 3. nasdomak/freecad-agent — clear staged execution example

Repository: https://github.com/nasdomak/freecad-agent  
Licence: LGPL-2.1-or-later.  
Status declared by its author: MVP / early non-commercial hobby-research project.

It describes an agent loop that perceives the current document, plans a sequence, executes structured commands in undoable transactions, reads the real geometry between features, and rolls back/replans after a failed feature. It asks deterministic clarification questions when crucial values are missing.

Its current structured vocabulary is 20 Part-workbench commands. Its own documentation says small local models drift beyond roughly 6–8 features per request and that its Qwen3:4B tests are limited. The project is therefore a useful design example, not a comprehensive base for our student.

**What Next3D should learn from it:** execute incrementally, re-inspect the native model after every meaningful operation, and repair from observed state rather than assuming the previous command succeeded.

### 4. pitbuild/freecad-mcp-headless — repeatable validation reference

Repository: https://github.com/pitbuild/freecad-mcp-headless  
Licence: MIT.  
Documented test environment: FreeCAD 1.1.4 on Linux.

It drives `freecadcmd` in a persistent worker and provides document inspection, feature-tree inspection, measurements, parameter changes, recompute, save/export and headless rendering. It documents path allow-lists, file-extension restrictions, file-size limits, timeouts, worker restart and read-only/no-execute modes.

**What Next3D should learn from it:** a separate headless verification path for regression testing, model measurement and save/reopen checks. This can complement live GUI execution; it is not a replacement for the visible operator experience. Arbitrary Python execution remains an optional unsandboxed capability in that project and must stay disabled in any untrusted test path.

### 5. GUI-thread and bridge references

- https://github.com/ahelja/FreeCAD-MCP — its documented architecture places GUI actions on FreeCAD's Qt main thread through a queued dispatcher. This is a useful correctness pattern: FreeCAD document mutations must not be made from an arbitrary worker thread.
- https://github.com/CREATeNG/freecad-mcp-bridge — MIT-licensed local MCP bridge with an explicit permission mode and bearer-token configuration. Its main execute tool runs Python in the FreeCAD process, so it is a transport/security reference, not a safe default tool policy for NextAI.

## What this means for the NextCAD student

The student must learn **the native operation grammar**, not memorise finished pictures or a catalogue of fixed projects.

For any user request, it should be able to:

1. **Understand intent and engineering context.** Identify the object/system, discipline, purpose, units, required dimensions, interfaces, constraints, outputs and unknowns. Ask only for missing information that changes the design.
2. **Inspect the actual document.** Read object types, stable object identities, feature history, selected faces/edges, parameters, constraints, dependencies, units, current workbench, installed capabilities and relevant project instructions.
3. **Discover the correct native operations.** Retrieve only the relevant workbench/API descriptions and typed schemas for the next stage. If an operation is unfamiliar, inspect the pinned native API/docs and its live signature before planning.
4. **Write a staged plan.** Show the user the intended sequence, assumptions, dependencies, expected native objects and verification checks before a consequential multi-step change.
5. **Execute visibly in small batches.** Create the first actual native feature, let the viewport/tree update, inspect the result, then plan or execute the next dependent feature. A water tower, building or vehicle should emerge as a sequence of editable native objects—not as one imported image or anonymous mesh.
6. **Use feedback to adapt.** Compare intended and actual state after every operation. On failure, preserve the error, undo/rollback the affected step, inspect the new state, and choose a corrected native operation.
7. **Produce project deliverables.** Where appropriate, create editable dimensions, annotations, drawings, component schedules and a native Spreadsheet/other supported table. These must be generated from actual object properties and measurements, with units and provenance—not invented by the language model.
8. **Save and prove.** Recompute, check geometry and relationships, save, reopen, and run the relevant exchange or discipline-specific validation before reporting completion.

### Examples of expected operator behaviour

**Architectural floor plan:** inspect the site and brief; establish levels/grids; create floor plates and external walls; add partitions; place openings and doors/windows; add rooms/spaces and circulation; inspect areas and boundaries; then create a wall/room/opening schedule and dimensioned views where the native toolset supports them.

**Water tower:** clarify capacity, tank geometry/elevation, support arrangement, material assumptions and site/load information; create the tank and support system as separate native components; add bracing, access and safety components; inspect connections and dimensions; then produce a member/component schedule with IDs, section/diameter, lengths, elevations and source properties. A visual concept is not a structural design: loads, wind, foundation and code checks require explicit inputs and validated analysis.

**Mechanical gear:** use actual gear parameters such as module, tooth count, pressure angle, pitch diameter, face width, bore and keyway requirements; construct a parametric gear/feature history; inspect the resulting geometry and dimensions; then create a parameter/dimension table and drawing. A visually plausible tooth shape is not proof of correct tooth geometry, strength or manufacturability.

### Table and drawing behaviour is part of the task

The student should learn that engineering work often ends with more than 3D geometry. Depending on the project and native tool availability, deliverables may include:

- wall, room, opening, door/window and finish schedules;
- structural member and connection schedules;
- tank/component schedules;
- mechanical part parameter and feature tables;
- dimensions, sections, elevations, detail views and drawing sheets;
- quantities, units, materials and explicit validation status.

A table row must distinguish at least: **required value**, **modelled value**, **measured/calculated value**, **unit**, and **evidence/source**. Do not silently treat a user-requested dimension as a measured model dimension. Do not claim a code check or engineering adequacy merely because a table or drawing exists.

## Required Next3D implementation direction

Next3D already has its own two-engine boundary, typed NextCAD tools, native capability census, retrieval and shared action-plan contract. Continue that architecture. Extend it using these priorities:

### A. Dynamic capability discovery and tool routing
- Build the full live inventory from installed NextCAD workbenches, command registry, public Python API modules, object types, formats and optional dependencies.
- Represent every discoverable operation as a capability record with native ID, source/version, input contract, preconditions, side effects, dependencies, verification and limitations.
- Use hierarchy and task-specific retrieval: discipline → workbench → operation family → exact tool schema. Do not flood Qwen with the entire catalogue.
- Keep discovered-but-not-adapted commands visible as gaps. Never advertise them as executable merely because FreeCAD exposes a UI command.

### B. Native typed operation library
- Prioritise broad coverage of Sketcher, Part, PartDesign, Draft, Assembly, TechDraw, BIM, Spreadsheet, Mesh, Points, Surface, ReverseEngineering, FEM, CAM, Import/Export and all other modules present in the exact pinned NextCAD build.
- Keep high-risk file, solver, external-program and project-wide operations behind explicit permission and dependency checks.
- Prefer deterministic handlers with validated arguments over model-generated Python. An isolated, reviewed scripting escape hatch is a separate future decision, not the default route.

### C. Stateful plan–execute–observe–repair loop
Use one consistent loop:

`intent → inspect → retrieve → plan → approve → execute one stage → recompute → inspect → verify → continue or repair → save/reopen → report`

Each operation returns structured evidence: tool/version, arguments, created/changed object identities, before/after state, warnings, validation result and rollback status. The next plan is conditioned on the actual returned state.

### D. Learning records that teach transferable skills
For a validated action trace, retain:
- the user intent and confirmed brief;
- initial model state and relevant capability/schema versions;
- the ordered plan and why each operation was selected;
- exact native tool calls and typed arguments;
- native results and before/after state deltas;
- failure, recovery and undo events where applicable;
- verification checks and saved/reopened result;
- source provenance, licence, privacy clearance and held-out split lineage.

Teach atomic operations, contextual variants, compound workflows, complete projects, revisions, failure recovery and unfamiliar combinations. Do not count screenshots or paraphrased prompts as proof of capability. Use images as supporting observations, never as a substitute for editable feature history and native model state.

### E. Engineering documentation generation
Add explicit task families for turning a finished model into schedules, tables and drawings. Generate values from native properties or verified geometry queries. Store units, source and evidence status. Keep user-specified, modelled and measured values separate. Route structural, hydraulic, mechanical and building-code checks through validated engineering methods and report their assumptions and limits.

### F. Evaluation and promotion
Evaluate command selection, argument validity, operation ordering, unit handling, feature-history quality, constraints, dependency preservation, recovery, geometry, interference, drawing/table accuracy, save/reopen and unfamiliar task composition independently. A candidate improves only when it beats the untouched student on held-out tasks and passes real NextCAD native execution tests.

## Adoption decision

- **Do not vendor a full third-party AI workbench into Next3D yet.** It would duplicate the user interface/orchestration and bring provider, permission and arbitrary-code paths we do not need.
- **Use ghbalf/freecad-ai as the primary design reference** for skills, tool routing, planning modes and MCP/tool registry patterns.
- **Use blwfish/freecad-mcp as the primary operation/verification checklist** for specialised native FreeCAD areas.
- **Use nasdomak/freecad-agent as a clear example** of incremental feature execution and geometry-aware repair.
- **Study pitbuild's headless worker** for CI and native save/reopen/regression tests.
- **Reimplement the selected ideas in Next3D's existing typed, permissioned adapter** and test them against the pinned NextCAD build. Preserve the original projects' attribution and licences if any source code is later copied. No third-party source code is copied into Next3D by this research document.

## Sources

- ghbalf/freecad-ai README: https://github.com/ghbalf/freecad-ai
- ghbalf/freecad-ai changelog: https://github.com/ghbalf/freecad-ai/blob/master/CHANGELOG.md
- ghbalf/freecad-ai code licence: https://github.com/ghbalf/freecad-ai/blob/master/LICENSE-CODE
- nasdomak/freecad-agent README: https://github.com/nasdomak/freecad-agent
- nasdomak/freecad-agent licence: https://github.com/nasdomak/freecad-agent/blob/main/LICENSE
- blwfish/freecad-mcp tool catalogue: https://github.com/blwfish/freecad-mcp/blob/main/TOOLS.md
- blwfish/freecad-mcp install/agent guide: https://github.com/blwfish/freecad-mcp/blob/main/AGENT-INSTALL.md
- pitbuild/freecad-mcp-headless README: https://github.com/pitbuild/freecad-mcp-headless
- ahelja/FreeCAD-MCP README: https://github.com/ahelja/FreeCAD-MCP
- CREATeNG/freecad-mcp-bridge README: https://github.com/CREATeNG/freecad-mcp-bridge
- Existing Next3D architecture: `docs/next-ai/INTEGRATION_ARCHITECTURE.md`
- Existing Next3D capability standard: `training/nextai/COMPLETE_NATIVE_CAPABILITY_STANDARD.md`
