# NextAI comprehensive capability curriculum programme

Status: programme specification; not evidence of a completed training run.

## Purpose

NextAI is intended to become a design-and-build operator for the complete native NextCAD and Next BIM applications. It must understand what the installed applications can do, choose the correct native operations, plan multi-stage work, create editable models, inspect the result, preserve object identity during revisions, and report what has and has not been verified.

This programme is deliberately larger than a collection of demonstration projects. It covers capability knowledge, individual operations, compound workflows, complete projects, natural-language design interviews, revisions, recovery, file exchange, and out-of-distribution combinations.

The scope is the full capability surface that can actually be discovered in the pinned application versions, plus the engineering and design knowledge needed to use those capabilities responsibly. It is not possible to enumerate every conceivable shape, dimension, product, building or future workflow: those combinations are effectively unbounded. The goal is therefore to teach the reusable operation grammar and decision-making needed to generalise to new requests, while maintaining a live catalogue of the actual commands installed.

## Baseline from the current branch

The current repository baseline contains:

- Next BIM's pinned native command catalogue: 215 command registrations from BIMCraft commit a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b. Of these, 159 are edit registrations, 34 are other/query-style registrations, 11 are other/file-oriented actions and 11 are edit/file registrations. These are command registrations, not 214 proven AI skills.
- NextCAD retains the upstream FreeCAD workbench foundations for Part, PartDesign, Sketcher, Assembly, Draft, TechDraw, BIM, FEM and CAM. The current NextAI adapter exposes capability discovery and a restricted typed tool set, but it does not yet give the model typed first-class coverage of every operation in every workbench.
- Current guided design intake: 114 scenarios and 342 dialogue-turn examples.
- Current NextCAD execution curriculum: 12 native tool-plan examples.
- Current Next BIM execution curriculum: 8 command-discovery workflow examples.
- The model manifest selects a Qwen3.5-0.8B Q4_K_M multimodal baseline. It is not a fine-tuned NextAI checkpoint.

The baseline counts above are the current authored curriculum and catalogue counts. They must never be presented as the number of skills the student has mastered.

## What counts as a scenario

A scenario is not just a sentence with a different product name or a different dimension. A qualifying scenario must change a meaningful decision, native operation, dependency, constraint, project stage, model state, validation target or recovery path.

Every scenario should carry, where applicable:

1. Application and version, with the exact capability catalogue version.
2. Domain, discipline, object family and project scale.
3. User request and design intent.
4. Known inputs, units, coordinate system and source of each value.
5. Missing information and the questions NextAI must ask.
6. Existing native model state, if the task is a revision.
7. Expected operation sequence or workflow graph.
8. Expected native object types, relationships and editable feature history.
9. Validation checks and expected evidence.
10. Prohibited assumptions, safety boundaries and unresolved items.
11. Data provenance, licence, privacy clearance and split lineage.
12. Outcome: authored lesson, schema-checked plan, native execution, or independently validated result.

A paraphrase-only duplicate does not earn a new coverage count. Variants are retained only when they exercise a distinct skill or decision.

## Curriculum layers

### Layer 1 — Full native capability census

Build a machine-readable inventory from the actual pinned applications, not from memory or a short list of popular tools.

For NextCAD, discover every installed workbench and command ID at runtime, retain its native module/workbench identity, and map command families, object types, supported properties, creation/edit/query behaviour, and input schemas. Include Part, PartDesign, Sketcher, Assembly, Draft, TechDraw, BIM, FEM and CAM, plus all additional workbenches present in the build. Record commands that are visible to a human but not yet callable through NextAI as capability gaps rather than pretending the assistant can already use them.

For Next BIM, ingest all 215 catalogue registrations and their exact descriptions, parameter schemas, undo behaviour and file effects. Rebuild this inventory whenever the pinned BIMCraft source changes. Do not infer that a command works merely because it appears in the catalogue; command-level tests must confirm its arguments and state effects.

The census must distinguish: discoverable, documented, callable by the assistant, schema-tested, native-executed, and end-to-end validated.

### Layer 2 — Atomic skills

Teach each native capability in isolation before asking the student to combine it. Examples include creating, inspecting, selecting, moving, aligning, mirroring, patterning, constraining, modifying, grouping, annotating, measuring, scheduling, querying, importing, exporting, undoing, recovering and validating.

For geometric modelling, include primitives, profiles, sketches, constraints, pads, pockets, revolves, sweeps, lofts, booleans, fillets, chamfers, shells, patterns, arrays, transformations, surface operations, meshes, topology, tolerances and feature-history dependencies wherever the installed toolset supports them.

For BIM, include levels, grids, walls, floors, roofs, doors, windows, rooms, stairs, ramps, railings, columns, beams, footings, reinforcement, adaptive components, materials, parameters, phases, families, views, sheets, schedules, site coordinates, MEP systems, quantities, imports, exports, links and model checks where the native catalogue supports them.

### Layer 3 — Compound workflows

Teach meaningful sequences that combine capabilities. A student should understand why one action precedes another, what dependencies it creates, how later edits affect earlier objects, and how to verify the result.

Examples include:
- sketch → constrain → pad → pocket → fillet → drawing;
- component → repeated pattern → assembly → interference/fit checks → drawing;
- terrain/site → levels → grids → foundations → frame → floors → envelope → rooms;
- rooms → doors/windows → schedules → sheets → IFC exchange;
- equipment → connectors → ducts/pipes/cable routes → system membership → coordination checks;
- existing model → inspect → identify exact element → edit in place → compare → save/reopen.

### Layer 4 — Complete project scenarios

The curriculum must include whole projects rather than isolated objects. Project families include:

**Architecture and building:** studio, bungalow, duplex, maisonette, six-bedroom house, apartment blocks, offices, schools, clinics, hospitals, hotels, shops, warehouses, factories, parking structures, stadiums, towers, mixed-use buildings, renovations, extensions and phased construction.

**Building height and floor variation:** one-storey, multi-storey and high-rise buildings, including 10-storey and 30-storey examples. Teach repeated typical floors, mirrored floors, alternating layouts, transfer levels, podiums, plant floors, roof levels, basements and genuinely different floor plates. Repetition must use controlled native copies/instances or equivalent relationships where appropriate; unique floors must remain individually editable. The assistant must track level elevations, vertical circulation, shafts, structural continuity, service risers and changes between floors.

**Civil and infrastructure:** roads, junctions, pavements, drainage, water networks, retaining structures, bridges, culverts, earthworks, site grading, utilities and infrastructure coordination, only to the extent supported by the installed native tools and verified engineering inputs.

**Structural:** concrete, steel and timber framing concepts, grids, columns, beams, slabs, foundations, reinforcement, connections, load paths and analysis preparation. Geometry creation is not proof of structural adequacy. Loads, materials, boundary conditions, code basis and analysis results must be supplied and checked.

**Mechanical and product design:** shafts, gears, housings, brackets, fasteners, bearings, pumps, valves, tanks, ducts, sheet-metal enclosures, furniture, appliances, tools, consumer products, electronics housings and mechanical assemblies.

**Consumer products and manufacturing examples:** a plastic bottle with body, shoulder, neck finish, cap interface, wall-thickness intent, draft and mould-parting considerations; a microwave oven with enclosure, cavity, door, hinge system, controls, ventilation and internal component envelopes; product variants, exploded assemblies, drawings, tolerances, materials, manufacturing operations and packaging. The model must state which features are merely visual envelopes and which have been dimensioned or checked. It must not claim food safety, electrical safety, thermal performance, pressure integrity or manufacturability without the corresponding engineering validation.

**Vehicles and equipment:** packaging concepts, chassis, body, wheel envelopes, brackets, mechanisms, equipment skids and assemblies. A visual model must not be represented as roadworthy or production-ready without the required specialist checks.

**BIM delivery:** new-build and renovation models, architecture/structure/MEP coordination, rooms and spaces, element data, quantities, schedules, sheets, phases, georeferencing, IFC exchange, information requirements, issue coordination and handover.

### Layer 5 — Human-style design intake and collaboration

Teach NextAI to conduct a useful design conversation rather than guessing. It must ask for purpose, users, site, plot dimensions, access, room or component requirements, dimensions, interfaces, materials, loads, operating conditions, level of detail, deliverables and applicable standards only where these are relevant.

It must retain confirmed answers, ask only for missing information, separate required inputs from preferences, show assumptions for approval, and distinguish concept design from detailed design. It must ask the user before consequential native modifications and must not claim execution before the application reports success.

For a six-bedroom house, for example, the student should clarify the number of floors, bedroom and master-bedroom arrangement, ensuite/shared facilities, public/private zones, living/dining spaces, kitchen, service spaces, parking, plot and road side, orientation, room-size expectations and required drawings. It should then build in visible stages: site and grids, floor plates and external walls, internal partitions, openings, stairs and circulation, room/space objects, upper floors, structure, roof, MEP coordination, dimensions, labels, schedules and sheets. Each stage must be inspected before moving on.

### Layer 6 — Revisions, unusual requests and recovery

Train on tasks that begin from an existing model: move a wall without losing its hosted windows, change a component interface, resize one floor while preserving the others, replace one family/type, add a new floor, revise only a selected assembly component, compare design options, recover an autosave, handle failed recomputes, resolve conflicting constraints, find a broken reference, and report unsupported operations.

Include unusual combinations and open-ended prompts: redesign a bottle into a refillable dispenser; convert a standard building floor into a plant level; fit a mechanical assembly into a constrained enclosure; adapt a tower for a different occupancy; remodel an existing building around a new stair core; create a modular product family from one parameterised master. The model should combine known operations compositionally and use live capability discovery when it encounters an unfamiliar command.

## Scenario scale and counting rules

The programme target is staged:

- First milestone: at least 10,000 meaningful scenario cases per application, with explicit coverage across atomic skills, compound workflows, complete projects, revisions and recovery.
- Expansion milestone: 100,000 or more meaningful cases per application, with domain balance and held-out project families.
- Ongoing: new capability and failure cases whenever the native applications, command catalogue, tool adapter or engineering knowledge changes.

The target is not met by generating 100,000 near-identical prompts. The corpus builder must track unique skill signatures, source-group hashes, application/domain coverage, operation sequences, scenario families and validation types. Duplicate and near-duplicate checks must run before training. Counts must be reported separately for authored dialogue, synthetic task plans, schema-checked plans, verified native traces and held-out tests.

The exact NextCAD count cannot be responsibly stated until its complete workbench/command census is exported from the installed build. The existing typed NextAI tool list is not a proxy for the full set of commands available to a human user.

## Evidence ladder

Every lesson and every reported milestone must carry one of these evidence levels:

- **L0 — Knowledge authored:** an explanation, procedure or scenario exists.
- **L1 — Schema checked:** tool names, command IDs and arguments are validated against the pinned catalogue.
- **L2 — Plan checked:** the complete ordered action plan passes structural, dependency and safety checks.
- **L3 — Native execution passed:** the real application executed the operations and its resulting document/model state was inspected.
- **L4 — Round-trip passed:** the native project saved, closed/reopened and retained the expected state.
- **L5 — Independent validation passed:** domain-specific geometry, BIM/IFC, manufacturing or engineering checks passed with recorded evidence.

A scenario at L0 or L1 must never be counted as an executed or mastered task. A warning or partial result must remain visible in the report.

## How the student learns

There are three connected but different systems:

1. **Native capability and knowledge retrieval** supplies the current manuals, command catalogue, schemas, object vocabulary and engineering references. Retrieval can expose new information without changing model weights.
2. **Supervised fine-tuning** teaches the Qwen student how to ask, reason over the supplied state, select operations, compose plans, follow tool schemas and report results. This is where training updates the model's learnable parameters. The planned LoRA process updates adapter parameters; it does not mean every base-model parameter is rewritten.
3. **Native execution and evaluation** tests whether the plan actually works in NextCAD or Next BIM. Only successful, permission-cleared, privacy-reviewed and round-trip-verified native traces may enter the positive native-execution training set.

The number of scenario records is not the number of model parameters. The current model manifest reports approximately 873.4 million base parameters. Ten thousand or one hundred thousand lessons do not automatically make the student competent. Competence must be measured on held-out scenarios and native application outcomes.

The 0.8B student may need retrieval and deterministic native tools to cover a large professional domain; simply making a small model's fine-tuning dataset larger does not guarantee that it can retain every detail. The target is a capable operator that can discover and compose native capabilities, not a model that memorises every possible design.

## Training and promotion gates

Before a new student is promoted:

1. Verify corpus provenance, licence, privacy, data splits and deduplication.
2. Report record counts by application, domain, evidence level and scenario family.
3. Train a candidate from a documented base checkpoint and save the adapter/checkpoint, configuration, random seed, software versions and logs.
4. Compare the untouched base student and candidate on the same held-out test set.
5. Measure clarification quality, command selection, schema validity, sequence ordering, constraint handling, revision correctness, recovery and honest limitation reporting.
6. Execute representative tasks in the actual native applications and inspect the resulting models.
7. Save/reopen projects and compare object identities, properties, geometry and relationships.
8. Run relevant geometry, topology, IFC, schedule, quantity, simulation or engineering checks.
9. Publish per-domain pass rates and failure examples. Do not hide a weak discipline behind a high overall average.
10. Measure the final model, vision projector, runtime, application binaries and installed package separately on each operating system.

No paid GPU run is implied by this specification. A GPU fine-tuning run must be explicitly authorised, executed and evaluated before a trained student is claimed.

## Reporting format

Every progress report should state:

- exact branch and commit;
- native application versions and catalogue snapshot;
- number of capabilities discovered, documented, callable, schema-tested and native-verified;
- number of unique scenarios authored, generated, schema-checked, executed and round-trip passed, separately for NextCAD and Next BIM;
- training run ID, source checkpoint, actual train/validation/test counts, GPU, duration, losses and saved artifact hashes;
- base-versus-candidate results per domain;
- known unsupported capabilities, failed scenarios and unresolved engineering checks;
- measured package sizes by operating system.

The headline claim must match the strongest evidence actually obtained. “100,000 scenarios prepared” is not the same as “100,000 scenarios executed successfully” or “the student mastered 100,000 skills.”

## Immediate next work

1. Export the full live NextCAD workbench and command inventory from the pinned build.
2. Expand the 215-command Next BIM catalogue into a command-by-command capability test plan, then verify each command's parameters and state effects.
3. Build a shared capability graph linking objects, operations, dependencies, disciplines, project stages and validation checks.
4. Add meaningful scenario families for architecture, high-rise floor variation, civil/structural, MEP, mechanical assemblies, consumer products, manufacturing, existing-model revisions and recovery.
5. Generate the first 10,000-case candidate corpus with provenance and deduplication, then audit its coverage before any GPU training.
6. Collect real native execution traces and held-out tests; promote only after measured improvement.

This programme is the coverage plan. It does not claim that the 10,000-case or 100,000-case targets have already been generated, that the model has been fine-tuned, or that all native operations have been verified.


## Master project/operator curriculum v1 — 28 November 2026

The corpus builder now includes an additional authored collection in
`nextai_master_curriculum.py`. It adds 62 distinct L0 scenario families:

| Collection | New examples | Coverage |
|---|---:|---|
| NextCAD | 12 | Parametric sketches/features, solids/surfaces, sweeps, gears, sheet metal, assemblies, drawings, FEM/CAM preparation, mesh repair and safe revisions |
| Next BIM | 12 | Datums, residential and multi-storey buildings, structural framing, healthcare spaces, MEP, clashes, quantities, IFC, renovation and georeferencing |
| Engineering disciplines | 16 | RC beams/slabs/columns, foundations, settlement, retaining walls, piles, slope stability, roads, drainage, channels, pumping, water networks, survey, earthworks and QA |
| Integrated projects | 10 | Bungalow, apartment, office tower, clinic, road/drainage, bridge/culvert, water tower, pump station, industrial skid and retrofit |
| Operator method/recovery | 12 | Intake, live discovery, tool selection, decomposition, identity-preserving edit, recompute/constraint/schema/IFC recovery, missing inputs and save/reopen verification |

These records enter the normal synthetic curriculum path, each with unique split lineage,
ordered workflow objectives, acceptance checks, failure modes and explicit non-claims.
They are L0 authored examples—not native traces or professional design approvals.

A separate `operator_practical_exam_v1.json` contains 18 evaluation-only tasks across CAD,
BIM, engineering and integrated projects. It is explicitly held out and is not imported by
the training corpus builder. Native practical examinations must still run inside the pinned
applications and produce L3/L4 evidence; engineering cases also require domain-specific L5
review where safety or code adequacy is being assessed.

### What this addition does not complete

- The 62 new scenarios do not satisfy the 10,000-case-per-application expansion milestone.
- The 215 BIMCraft command registrations still need command-by-command runtime/schema/state-effect verification; registration and metadata lessons are not proof that every command is callable or works.
- The full live NextCAD runtime command census still needs to be captured from the pinned GUI.
- The six native train/validation/test trace files still need real collector artifacts and manifest review. Existing acceptance round trips and collector fixtures are not a substitute for a broad native operation corpus.
- The complete mixed corpus must be rebuilt, deduplicated, tokenizer-audited and reviewed by application/domain/evidence level after these changes.
