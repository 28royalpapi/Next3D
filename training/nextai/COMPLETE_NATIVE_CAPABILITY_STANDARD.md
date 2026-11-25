# NextAI Complete Native Capability Standard

Status: implementation standard for capability discovery and student coverage. It is not a completed training run or a model mastery certificate.

## Objective

NextAI is being trained to become an engineering operator for the complete native NextCAD and Next BIM applications. The target is not a small collection of demonstrations. The student must learn the installed software's full discoverable operation surface, the native object and data models behind those operations, how commands combine into real work, and how to verify or recover from changes.

"Everything the software can do" must be grounded in the exact pinned build and the extensions actually installed. A future build may add capabilities; a workbench may be present in source but fail to load; an external solver may be absent; a visible command may not have a safe typed AI adapter. The standard records these separately instead of guessing.

## 1. The complete capability inventory

A complete inventory has separate layers. No one layer is a substitute for another.

### NextCAD

1. **Source modules and workbenches.** Start from the pinned source index. Record every module, workbench, source path, source revision and external dependency.
2. **Live GUI command registry.** Run the discovery macro inside the actual NextCAD GUI. It uses the native global command registry and records every registered GUI command and its metadata. It also records workbench menu labels and the toolbar commands that the pinned Python workbench wrapper exposes. The wrapper does not expose a menu-label-to-command-ID mapping, so the census must not pretend that it knows every command's menu membership.
3. **Public Python API.** Record public names from the modules loaded after workbench activation, with class/callable/value type and available documentation. This is a separate layer from GUI commands: a callable API method may have no toolbar button. This runtime snapshot is not a complete index of every compiled C++ symbol or every optional module that could not be imported; follow it with a version-pinned API-reference/source index.
4. **Native object model.** Inventory object types, property schemas, units, links, placements, constraints, feature history, dependencies, supported file formats and import/export behaviour.
5. **Optional integrations.** Inventory add-ons, solvers, post-processors, libraries and external programmes separately, with their versions, availability, licences and tests.
6. **AI operation surface.** Compare all discovered capabilities with the reviewed typed NextAI tool registry. A capability that has no safe adapter is a visible coverage gap, not an implied AI ability.

The live census must be taken after the pinned application starts and its workbenches are registered. Source-folder presence alone is not proof of runtime availability.

### Next BIM

1. **Native command registry.** Ingest every command registration from the pinned BIMCraft `ALL` registry, retaining exact command ID, label, aliases, argument description, undo behaviour, menu and file effects.
2. **Runtime command discovery.** Preserve the in-app `list_commands` pathway as the live discovery source. The student must read the exact current command description before constructing an `execute` call.
3. **Native model schema.** Inventory element types, families, type and instance parameters, host/level relationships, geometry, classifications, quantities, materials and IFC mapping.
4. **Project operations.** Include view, schedule, sheet, coordinate, phasing, library, plugin, open/save/export and recovery operations with their user-permission boundaries.
5. **AI operation surface.** Map every native registration to the assistant's read/write tools and the current file-access policy. The native assistant blocks file-reading/writing commands and its image-rendering command; other commands remain subject to the bridge's access rules. A native command can exist while intentionally being disallowed to the assistant.

The pinned baseline contains 214 command registrations. That number is a source inventory count, not 214 proven operator skills.

## 2. Every command becomes a learning obligation

For every native command (and, separately, every callable API operation), the student must cover ten dimensions:

1. Recognition: what it does, when to choose it and when not to choose it.
2. Inputs and units: argument meanings, required/optional fields, defaults, valid ranges, enums and unit conventions.
3. Preconditions: required document state, target objects, references, selections, levels, workplanes and dependencies.
4. Planning: operation order, upstream/downstream dependencies, transactions and impacts on existing objects.
5. Execution: the exact native command or reviewed typed tool and schema-valid arguments.
6. Verification: expected object types, geometry, properties, relationships, dimensions, warnings and state changes.
7. Revision: in-place editing, identity preservation, dependent-object handling and change comparison.
8. Failure recovery: invalid arguments, failed recompute, broken references, constraints, undo/rollback and repair.
9. Composition: use in compound workflows and complete projects, including combinations not explicitly shown in one lesson.
10. Limitations: unsupported functions, unavailable dependencies, incomplete exchange and engineering claims the application cannot prove.

The new census generator creates these as **skill obligations**, not as fake supervised examples. Each obligation carries the native command/API metadata, including the real parameter description and current assistant-policy status. For Next BIM, a parameter contract is a human-readable command-registration description, not a formal JSON Schema; live command discovery and the native engine remain authoritative for argument acceptance. A command is not mastered because a row was generated for it.

## 3. The scenario grammar

Each capability is taught through several levels:

- **Atomic operation:** one command or API action in a controlled document.
- **Contextual operation:** the same action applied to different valid object types, references, orientations, levels, units or model states.
- **Compound workflow:** several native actions in their correct dependency order.
- **Complete project:** a building, assembly, product, drawing set, MEP layout, structural concept, site or infrastructure model.
- **Revision workflow:** modify an existing model without losing object identity, hosted elements, constraints or downstream references.
- **Failure and recovery:** deliberately exercise invalid inputs, unsupported cases, failed constraints, recompute failure, rollback, undo, reopen and repair.
- **Unseen combination:** combine known capabilities in an unfamiliar task and use live discovery when the student encounters an unknown command.

A scenario counts as a distinct case only when it changes a meaningful decision: operation, dependency, constraint, model state, parameter regime, project phase, validation target, deliverable or recovery path. Rephrasing the same prompt does not add coverage.

## 4. Domain and object families

The capability map must span, wherever the pinned application really supports them:

### NextCAD
- 2D drafting, annotation, dimensions, layers, blocks, snaps and coordinate transforms.
- Sketch geometry, geometric constraints, dimensional constraints, solver state and degrees of freedom.
- Parametric parts, Part/PartDesign features, feature trees, solids, surfaces, booleans, dress-ups, patterns, topology and tolerances.
- Assemblies, links, placements, joints, subassemblies, clearances and interference.
- Architecture/BIM, spaces, walls, openings, roofs, slabs, levels, IFC and building documentation.
- TechDraw, projections, sections, details, dimensions, title blocks, sheets and exports.
- Meshes, point clouds, reverse engineering, surface reconstruction and additive manufacturing preparation.
- FEM/CAE: materials, meshes, supports, loads, solver selection, result fields and convergence evidence when the required solver is installed.
- CAM/CNC: stock, work coordinate systems, tools, operations, toolpaths, simulation and post-processors when dependencies are installed.
- Spreadsheets, formulas, expressions, material assignment, measurement, automation and interoperability.

### Next BIM
- Projects, sites, coordinates, levels, grids and workplanes.
- Architecture: walls, wall types/layers, hosted doors/windows, floors, roofs, rooms, stairs, ramps, railings, shafts and adaptive components.
- Families, types, parameters, materials, forms, voids, symbols and reusable components.
- Conceptual massing, derived elements and dependent geometry.
- Structure: columns, beams, floors, foundations, steel sections, reinforcement and member relationships.
- Plumbing, mechanical services, electrical distribution, lighting, communications, cable trays, conduits, wires, panels and supported system data.
- Views, visibility, phases, filters, dimensions, tags, annotations, sections, elevations, sheets and print output.
- Schedules, quantities, filters, formulas, totals and panel schedules.
- IFC import/export, properties, quantities, model checks, revisions, recovery, plugins and agent operations.

The list is a taxonomy for checking coverage. The actual native registries and test results decide what is implemented in a specific build.

## 5. Complete project training

Command knowledge must be composed into complete project families, including:

- Houses of different sizes and forms, apartments, offices, schools, hospitals, hotels, warehouses, factories, towers and mixed-use buildings.
- Multi-storey and high-rise buildings with typical, mirrored, alternating and unique floor plates, podiums, transfer floors, plant rooms, basements, roof levels, stairs, lifts and vertical service risers.
- Structural framing concepts, foundations, reinforced-concrete and steel elements, reinforcement placement and analysis preparation.
- MEP layouts and coordination, with real native connector/network evidence wherever the software supports it.
- Roads, drainage, site grading, retaining works, bridges, culverts and infrastructure models where supported by the native engine.
- Mechanical parts, shafts, housings, gears, pumps, valves, tanks, brackets, sheet metal and assemblies.
- Consumer products such as bottles, caps, appliances, furniture, electronics housings and packaging.
- Vehicles and equipment packaging concepts, assemblies, layouts and documentation.
- Manufacturing drawings, CAM preparation, quantities, schedules, revisions and handover packages.

Large scenarios must be staged: inspect, confirm missing requirements, plan, execute coherent batches, inspect after each batch, save/reopen and verify the deliverables. The model must distinguish visual placeholders from engineered geometry and must never infer loads, ratings, tolerances, material properties or code compliance that were not supplied and checked.

## 6. Scenario milestones and measurement

The curriculum milestones remain:

- **Milestone A:** at least 10,000 meaningful scenarios for NextCAD and 10,000 for Next BIM.
- **Milestone B:** at least 100,000 meaningful scenarios for each application.
- **Continuous:** add cases for every newly discovered native capability, new dependency, changed command schema and observed failure mode.

Coverage must be reported separately by application, workbench/command, domain, skill dimension, scenario family and evidence level. It must not be inflated by paraphrase duplicates or by treating one command's ten learning obligations as ten trained examples.

At each milestone, publish separate counts for: capabilities discovered, obligations mapped, lessons authored, schema-checked plans, native-executed traces, save/reopen passes, independent validation passes and held-out tests.

## 7. Evidence and promotion

Use the existing evidence ladder:

- L0: knowledge authored.
- L1: command and argument schema checked.
- L2: complete plan and dependencies checked.
- L3: native application execution passed.
- L4: save/close/reopen round-trip passed.
- L5: independent domain validation passed.

A positive native-operation training example should include the user request, confirmed specification and units, native before/after states, exact operations and arguments, validation results, save/reopen proof, provenance, licence, privacy clearance and split lineage. Failed attempts are valuable recovery lessons, but they must be labelled as failures and must not be mixed into positive execution targets.

The base student and candidate must be evaluated on the same held-out project families. Measure command selection, argument validity, sequence order, unit handling, dependency preservation, revision correctness, recovery, model geometry, BIM/IFC relationships and honest limitation reporting separately.

## 8. Implementation in this branch

- `discover_nextcad_runtime.FCMacro`: read-only capture of the live FreeCAD command registry and workbench membership. It does not invoke modelling commands or save the user's project.
- `capability_census.py`: merges the NextCAD source index, live NextCAD report and pinned BIMCraft catalogue; outputs a full census, summary and per-command skill-obligations file.
- `test_capability_census.py`: checks the 214-command BIM baseline, all ten learning dimensions, source pinning, runtime report validation and policy boundaries.

The remaining integration task is to run the runtime capture against each native build and archive the resulting census. Then the typed AI adapters and per-command scenario builders can be expanded against the real inventory instead of guesses.

This standard defines the work. It does not claim the 10,000/100,000 scenarios have already been authored, that the student has been fine-tuned, or that every discovered command has passed native execution.
