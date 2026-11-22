# Next AI — Application Capability Inventory

**Pinned source baseline:** FreeCAD `00cb280454069966a2fb0a8e7dc184c46e7b38b3`; BIMCraft `a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b`.  
**Purpose:** establish what the native engines actually contain before designing their AI knowledge packs or collecting training examples.

## How to read this inventory

- **In source** means the capability/workbench/command exists in the pinned source tree. It does not by itself prove a successful runtime test on all three operating systems.
- **Documented working** means the pinned application's own README or area documentation describes a working native workflow. It still needs explicit AI acceptance tests.
- **Partial / verify** means the basic data or drawing operation exists, but richer behaviour such as connectivity, engineering analysis, interoperability fidelity or all edge cases must not be assumed.
- **External** means a separate workbench, add-on, solver, service or library is needed. It is not included merely because the upstream ecosystem has a project for it.

The matrix is not a claim that either program is equivalent to every feature of AutoCAD, Revit, Tekla, ETAP, EPLAN or another specialist product. Next AI must answer from the installed native capability map and identify unsupported work instead of pretending it exists.

---

# 1. NextCAD — FreeCAD

## 1.1 Native workbench/module map

The pinned FreeCAD source contains these modules under `src/Mod`:

| Workbench / module | What Next AI must understand |
| --- | --- |
| **Part** | OpenCASCADE boundary-representation solids, primitives, transforms, booleans, fillets, chamfers, shells, sections and topology |
| **PartDesign** | Bodies, sketches, feature history, pads, pockets, revolves, lofts, sweeps, holes, patterns and additive/subtractive features |
| **Sketcher** | Lines, arcs, circles and other supported geometry; dimensional/geometric constraints; solver state; degrees of freedom; external geometry; fully constrained profiles |
| **Assembly** | Components, links, placements, joints/mates, subassemblies and assembly-specific constraints in the pinned implementation |
| **Draft** | 2D drafting geometry, snaps, dimensions, annotations, arrays, clones and work-plane-based tools |
| **TechDraw** | Drawing pages, orthographic projections, sections, detail views, dimensions, hatching, annotations and export |
| **BIM** | Building elements, architectural objects, levels/buildings, IFC/BIM workflows and related object properties |
| **Fem** | Analysis objects, materials, constraints, loads, meshing, solver setup and result inspection; actual solver availability is a separate dependency check |
| **CAM** | Jobs, stock, tools, operations, toolpaths and post-processing workflows |
| **Mesh / MeshPart** | Mesh import, creation, measurement, repair/analysis and mesh-to-shape workflows |
| **Points** | Point-cloud data, import and point inspection |
| **ReverseEngineering** | Scan/point-cloud-to-geometry and reconstruction workflows |
| **Surface** | Surface construction and editing, including NURBS-related workflows |
| **Robot** | Robot models, trajectories and simulation/robotics workflows |
| **Spreadsheet** | Cells, formulas, aliases and parametric values that can drive model properties |
| **Import** | File import/export integrations supplied by the core and installed modules |
| **OpenSCAD** | OpenSCAD-based/CSG interoperability and object workflows |
| **Material / Measure / Inspection** | Material assignment, measurement and model/shape inspection |
| **Plot / Show / JtReader** | Plotting, visualization and JT interoperability |
| **Start / Help / Test / TemplatePyMod / Web** | Startup, help, testing, template and supporting modules; not all are modelling disciplines |

**Important:** module presence is not the same as a ready-to-use installation of every external solver, format adapter or add-on. NextCAD's runtime must enumerate which workbenches load successfully, which external programs/solvers are available, and which are missing. External workbenches such as gears, fasteners and specialist electrical tools must be separately licensed, pinned and tested before their capabilities are advertised.

## 1.2 Engineering capability families

| Family | Native object/data the AI must learn | Required checks before it can report success |
| --- | --- | --- |
| Parametric mechanical CAD | Document/object graph, parameters, expressions, feature history and dependencies | Recompute, valid shape, expected dimensions, mass properties, no broken features |
| 2D sketching and constraints | Geometry, constraints, support plane, attachment, solver status, remaining degrees of freedom | Solver has no conflicts/redundancies; required constraints and intended DoF are correct |
| Solid and surface modelling | B-rep topology, faces/edges/vertices, body membership, feature support and references | Valid solids/surfaces, expected topology and dimensions, references survive recompute |
| Assemblies | Components, links, placements, joints, constraints and subassembly hierarchy | Components resolve, constraints are satisfied, placements and clearances are checked |
| Architecture / BIM | Site/building/storey, walls, doors, windows, slabs, spaces, components and IFC properties | Hosts/levels/placements are correct; room/space boundaries and IFC round-trip are checked |
| Technical drawings | Views, scales, projection direction, sections, detail views, dimensions, symbols and sheets | Drawing views match source model; dimensions and page layout are readable; export opens |
| FEM / CAE | Analysis, mesh, material, loads, constraints, solver settings and result fields | Correct solver exists; mesh and boundary conditions are valid; solver converged; units/results are checked |
| CAM / CNC | Stock, work coordinate system, tools, operation parameters, feeds/speeds, toolpath and postprocessor | Toolpath simulation/collision checks, correct stock/material/tool, and postprocessor output review |
| Mesh / additive manufacturing | Triangle mesh, units, normals, watertightness and tessellation | Mesh quality and scale, manifold/watertight requirements where applicable, export opens |
| Point cloud / reverse engineering | Scan points, registration/alignment, coordinate frames and fitted surfaces | Alignment residuals, tolerances and coverage reported; fitted model remains editable |
| Materials / measurement | Material definitions, units, dimensions, area, volume, mass and measurement references | Units and density are explicit; measured values come from the native model |
| Automation / APIs | FreeCAD Python API, macros, workbench commands, property system and object transactions | Command is available in the running version; script is reviewed/permissioned; document mutation is undoable |

## 1.3 What an AI knowledge item must contain

A picture of a finished part is insufficient. The model needs the native feature sequence and design intent too:

- A sketch: geometry, plane/support, named dimensions, constraints, solver result and remaining DoF.
- A pad/pocket/revolve/loft/sweep: source feature, parameters, direction, support and native readback.
- A fillet/chamfer: selected real edges/faces, radius/size, valid result and rollback behaviour.
- An assembly: component identities, placements, joint definitions, solver/constraint status and degrees of freedom.
- A drawing: source views, projection, scale, dimensions, annotations, sheet and exported PDF/DXF/SVG.
- A FEM analysis: material, mesh, supports, loads, solver, convergence evidence and results.
- A CAM operation: stock, tool, coordinate system, feeds/speeds, toolpath and simulation results.

## 1.4 AI-specific risk boundaries

1. Never invent Edge or Face indices. Inspect the real model and expose stable semantic hints; topology indices can change after recompute.
2. Never silently leave a sketch under-constrained when the user asked for a fully constrained design.
3. Never turn a drawing into a plausible solid without preserving dimensions, constraints and source provenance.
4. Never claim an FEM or CAM result without the required solver/tool and verification.
5. Raw Python execution is a high-risk escape hatch. A third-party assistant that executes arbitrary Python inside the live FreeCAD process must not be integrated unchanged. The default Next AI surface must use typed, permissioned operations; any code execution requires explicit approval, clear preview and rollback.
6. Every write must use the active document's native undo transaction and must preserve FCStd compatibility.

---

# 2. Next BIM — BIMCraft

## 2.1 Native engine and command surface

The pinned BIMCraft source has a separate Rust core (`crates/core`), a desktop UI (`crates/ui-egui`) and a CLI/MCP entry point (`apps/bimcraft-cli`). The core command table contains **214 command registrations** at the pinned revision.

The agent interface is intentionally smaller than the full command table. Its high-level MCP surface includes project context, command execution, scripts, command discovery, model inspection, element queries, schedules, rendering, open/save and the interactive desktop bridge. A user request should normally use native typed commands, not invent a second building model format.

Project files and supported output paths are not interchangeable:

- Native editable project: `.bimc` (and compatible `.bimt` template input).
- IFC4 exchange.
- glTF/GLB scene export.
- SVG/PNG drawing output and PDF sheet printing.
- CSV/XLSX schedule output where supported.
- Revit `.rvt` is read by a bounded reader; this is not a public or complete Revit file implementation.

## 2.2 Building and engineering capability families

A machine-readable index of the 214 registered commands, including each parameter description, edit/read classification and aliases, is available at [BIMCraft native command catalog v1](catalogs/BIMCRAFT_NATIVE_COMMANDS.v1.json).

| Family | Native model features documented in the pinned source | AI knowledge and validation |
| --- | --- | --- |
| Project and datums | Project, units, levels, grids, work planes, project/base/survey/shared coordinates and named locations | Correct origin, elevation, true north, coordinate system and units |
| Architecture | Walls (including layered/curved/joined walls), hosted doors/windows, floors, ceilings, roofs, stairs, ramps, railings, shafts, rooms and property boundaries | Wall joins, hosted opening fit, storey constraints, slope, boundaries, room closure and area |
| Families and components | Families, types, instance/type parameters, formulas, forms, voids, symbols, materials and favorites | Correct family/category/type, parameters, host, formula dependencies and geometry |
| Conceptual massing | Masses, lofted/leaning forms, derived floors and walls/floors/roofs by face | Face identity and dependency stability; generated elements must be checked after source mass edits |
| Views and documentation | Plans, reflected ceiling plans, sections, elevations, 3D views, view ranges, crop regions, graphics overrides, filters, phases and design options | Every view has its own scale, range, phase, visibility and annotation context |
| Dimensions and annotations | Linear/angular/radial/3D dimensions, tags, notes, spots, sections/elevations and sheet placement | Dimension references must remain valid and labels must match native element identities |
| Schedules and quantities | Schedules, custom fields, filters, sorting/grouping, formulas, totals and panel schedules | Quantities should be computed from the model; do not infer values from a picture |
| Structural | Beams, structural columns, isolated/strip footings, structural floors, steel section types/catalogue and reinforcing bars | Verify member section, level/offset, material, host, reinforcement coverage and IFC quantities |
| Plumbing | Pipes/runs, fixtures, families, fittings and valves; system names and IFC exchange | A run/fixture existing does not prove a fully connected network, pressure/flow design or code compliance |
| Electrical | Conduits, cable trays, wires, boards, outlets, switches, luminaires, electrical settings, circuits, voltage and panel schedules | Check board supply, phases, poles, ratings, wire type/section and actual circuit/device relationships |
| Lightning protection (SPDA) | Air terminals, down conductors, earth rods, inspection boxes and earthing conductors | Treat as BIM placement/documentation unless an explicit protection-risk/calculation engine is present |
| Data / communications | Data/voice outlets, racks, patch panels, structured cabling and cable trays | Check route/termination data; don't claim end-to-end network connectivity without connectors and validated topology |
| IFC and exchange | IFC import/export, including supported spatial/architectural/structural/MEP categories and custom property sets | Round-trip IFC and report elements skipped, remapped or approximated |
| Plugins and agents | WASM plugin host/SDK, CLI scripts, MCP and existing in-app Assistant | Plugin permissions and command schemas need auditing before the model is given write tools |

## 2.3 Documented boundaries that must remain visible

- A pipe, conduit, cable tray or wire can be a native run with a type, cross-section, level, height/offset and named system. Do not infer that all runs have a complete physical connector graph or that the software performs every hydraulic/electrical/network calculation.
- The in-app assistant executes through the same native command bridge and can group a turn into an undo step. That is a strong foundation. However, its pinned provider implementation is Anthropic/OpenAI/Gemini with user-selected credentials; it is not yet the offline local model requested for Next AI.
- The README's capability table and roadmap have evolved at different rates. For example, the discipline material describes working plumbing/electrical/SPDA/data tools, while the older roadmap still describes more MEP work as future. The source implementation and tests must settle the exact supported boundary for every operation before the AI promises it.
- Revit `.rvt` import is a bounded reader, not full Revit feature parity. BIMCraft's own reader reports what it did not import.
- DWG/DXF export, complete IFC coverage, gbXML, multi-user collaboration and other roadmap items must not be shown as available until their current source, command and tests prove they exist.

## 2.4 What an AI knowledge item must contain

- A floor plan: level, coordinates, units, wall centre-lines/location lines, wall types/layers, joins, doors/windows and host references.
- A room/space: boundary elements, separation lines, height limits, offsets, area method and calculated area/volume.
- A structural element: member type/section, material, level, start/end offsets, justification, host and applicable load-bearing metadata.
- A plumbing run: pipe type/diameter/material, start/end, elevation/offset, fall direction, system, fixture/fitting connections and validation status.
- An electrical circuit: board, distribution system, voltage, phases, poles, breaker, device list, loads, wire type/section and panel schedule.
- A drawing sheet: views placed, scales, paper size, title block, annotations, print settings and exported file.
- An IFC example: exact source project, IFC file, element mapping, properties/quantities and round-trip discrepancies.

---

# 3. What this means for the Next AI model

The same user-facing assistant can appear in both products. The software understanding behind it must remain split:

- **NextCAD knowledge pack:** FreeCAD object model, workbench/API version, FCStd feature trees, Sketcher constraints, PartDesign history, BRep topology, assemblies, drawings, FEM/CAM and installed add-ons.
- **Next BIM knowledge pack:** BIMCraft element schema, 212-command registry, types/families, levels, view/schedule rules, structure/MEP, IFC and BIMC persistence.
- **Shared orchestration:** intent clarification, structured specification, plan, progress/cancellation, tool selection, retrieval, memory and evaluation.
- **No shared geometry engine:** a NextCAD command never mutates a BIMCraft model; a Next BIM command never mutates an FCStd document.

## 3.1 Minimum dataset record

Every training or evaluation example should be a linked package, not an isolated image:

1. Original user prompt and reference drawing/image/PDF.
2. Clarifications, named parameters, units, design assumptions and unresolved questions.
3. Native project before the operation (FCStd or BIMC) plus the relevant object/feature state.
4. Exact native command/tool sequence and argument JSON.
5. Native project after execution and the resulting feature tree/object relationships.
6. Generated plan/elevation/section/isometric views tied to the exact project revision.
7. Automated validation: dimensional accuracy, geometry validity, sketch solver state, model checks, quantities, schedule results, IFC round-trip and save/reopen.
8. Provenance: author/source, document ID, date, licence, permission state, allowed training use and withdrawal identifier.

A picture of a three-bedroom house does not tell the model its exact wall layers, floor elevations, opening hosts, stair riser count, structural sections, circuit ratings or feature dependencies. Those must come from the native project and its validation data.

## 3.2 Dataset construction order

1. Generate small, deterministic examples inside the native applications ourselves.
2. Pair each native project with controlled variations in prompt, view and engineering discipline.
3. Validate every generated result with the native engine.
4. Add public/third-party examples only after source licence, creator permission and dataset terms are checked.
5. Keep held-out benchmark projects completely out of the training set.
6. Scale only after the benchmark shows which tasks fail and why.

Synthetic data must be generated by the real CAD/BIM application and then verified. It must not be accepted just because a vision model says its rendering looks right.

## 3.3 Initial benchmark

Start with a small benchmark of representative tasks, not millions of unchecked samples:

- NextCAD: constrained sketch, parametric bracket, hole pattern, assembly, technical drawing, BIM floor plan, FEM setup and mesh export.
- Next BIM: multi-storey house, rooms/openings, roof/section/sheet, steel frame, plumbing layout, electrical board/circuit, schedule and IFC round-trip.

Measure: correct dimensions and units; editable feature history; valid topology/model; solver/constraint status; save/reopen; repeatability under parameter changes; correct documentation views; and accurate report of unsupported tasks.

Only after a local base model plus tools/retrieval has a measured baseline should Next 3D decide on fine-tuning. Fine-tuning is useful only when it improves held-out performance versus that baseline.

## Source references

- [Pinned FreeCAD workbench modules](https://github.com/FreeCAD/FreeCAD/tree/00cb280454069966a2fb0a8e7dc184c46e7b38b3/src/Mod)
- [FreeCAD source README](https://github.com/FreeCAD/FreeCAD/blob/00cb280454069966a2fb0a8e7dc184c46e7b38b3/README.md)
- [Pinned BIMCraft README](https://github.com/IPedrax/BIMCraft/blob/a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b/README.md)
- [BIMCraft command registry](https://github.com/IPedrax/BIMCraft/blob/a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b/crates/core/src/commands.rs)
- [BIMCraft Assistant design](https://github.com/IPedrax/BIMCraft/blob/a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b/docs/areas/assistant.md)
- [BIMCraft structure and MEP design](https://github.com/IPedrax/BIMCraft/blob/a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b/docs/areas/structure-and-mep.md)
