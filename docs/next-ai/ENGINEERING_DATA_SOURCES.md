# NextAI — Engineering Data Sources and Specialisation Curriculum

Status: research-backed ingestion plan. No third-party dataset is approved for production training until its files, licence, provenance, quality and held-out split are checked.

## Decision

Build a specialised engineering model by adapting an open-weight base model, not by pretraining a foundation model from scratch. The training target is a compact model that is unusually good at CAD/BIM understanding, specification extraction, planning, tool selection, clarification and repair. The product must still use versioned retrieval and native application tools for exact facts and operations.

Do not put training corpora, source archives or training dependencies in the Next3D installer. The 1.2 GB limit applies to the released applications, shared runtime, model, projector (if used), adapters and runtime knowledge packs.

## High-value public data candidates

| Domain | Resource | Published content / size | Licence shown on Hub | Decision |
|---|---|---|---|---|
| CAD construction sequences | [Autodesk Zero-to-CAD-1M](https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-1m) | 979,600 train; 10,000 validation; 10,000 test. Train Parquet ~338.8 GB; validation ~3.5 GB; test ~3.4 GB. Records include CadQuery source, parsed operation sequence, face counts, renders, STL and STEP. | Apache-2.0 | Highest-priority CAD data candidate. Do not download all 346 GB. Build a stratified, reproducible sample by operation family, feature depth, parameter count, topology and difficulty. Keep test split held out. |
| CAD code from point clouds | [CAD-Recode v1.5](https://huggingface.co/datasets/filapro/cad-recode-v1.5) | About 1M CadQuery programs; source describes point-cloud-to-code examples. | CC-BY-NC-4.0 | Quarantine for commercial model training unless a separate commercial permission is obtained. Do not assume attribution alone removes the non-commercial restriction. |
| BIM / IFC instruction following | [IFC BIM Alpaca 124K](https://huggingface.co/datasets/Dietmar2020/ifc-bim-alpaca-124k) | 112,476 train and 12,498 validation; ~13.9 MB train and ~1.6 MB validation. Six columns: instruction, input, output, source, metadata, score. Covers IFC 4.3.x-devel entities, properties, relationships and practices. | MIT | First BIM corpus to audit. Inspect source attribution, duplicates, factual validity, IFC version alignment and examples with native IFC validation before admitting records. |
| BIM / IFC knowledge QA | [IFC BIM QA Dataset](https://huggingface.co/datasets/Dietmar2020/ifc-bim-qa-dataset) | 9,800 train and 3,700 test; 13,485 total QA pairs. Includes schema knowledge, constraints, documentation and workflows. | CC-BY-4.0 | Use as a secondary QA/evaluation candidate after source and answer verification. Keep its test split out of training and retrieval. |
| BIM / IFC curated instructions | [IFC BIM High-Quality Alpaca](https://huggingface.co/datasets/Dietmar2020/ifc-bim-high-quality-alpaca) | Curated instruction data; exact usable rows and provenance need inspection. | Apache-2.0 shown on Hub | Candidate for quality comparison, not automatic inclusion. Compare with the 124K set and deduplicate by source/template. |
| BIM / IFC deduplicated instructions | [Cairn IFC-BIM Alpaca Dedup](https://huggingface.co/datasets/cairndev/ifc-bim-alpaca-dedup) | 5.6K train, 301 validation, 348 test. Split by template family to reduce leakage. | Apache-2.0 shown on Hub | Valuable clean baseline/evaluation and training subset. Audit the upstream pin and transformations before adoption. |
| CAD task-specialised teacher | [Zero-To-CAD-Qwen3-VL-2B](https://huggingface.co/ADSKAILab/Zero-To-CAD-Qwen3-VL-2B) | Approximately 2.13B parameters; specialised for text/image-to-CAD with CadQuery and linked to Zero-to-CAD-1M. | Apache-2.0 shown on Hub | Research/teacher candidate only. Too large for the target runtime package and not a NextCAD-native operator. Study outputs and distillation possibilities; do not bundle. |
| BIM task-specialised adapter | [Qwen3-4B IFC/BIM QLoRA](https://huggingface.co/cairndev/qwen3-4b-ifc-bim-qlora) | Adapter trained from Qwen3-4B-Base on a deduplicated IFC/BIM instruction set. | Apache-2.0 shown on Hub | Teacher/reference candidate only. The 4B base is not a viable bundled model under the total product-size ceiling. Audit adapter/base compatibility and training recipe before use. |

### Important observations from dataset previews

- Zero-to-CAD records contain executable CadQuery programs and parsed feature-operation sequences, not merely captions. A sample includes a parameterised revolved component with holes, a polar array, counterbore and chamfer. This is valuable for learning parametric design intent and feature sequencing.
- CadQuery is not FreeCAD's native API. Do not train the model to paste CadQuery scripts into the live FreeCAD process. Convert the task intent/feature sequence into a neutral intermediate specification, then create and validate a corresponding FreeCAD-native trace inside the pinned FreeCAD engine.
- The IFC/BIM Alpaca preview includes material-layer sets and wall-opening-window relationships. These are useful IFC concepts, but every record must be checked against the relevant schema edition and an IFC validator; a dataset's `validated: true` metadata is a claim to verify, not proof.
- The IFC QA preview includes formal IFC entity constraints and resource semantics. This can teach domain vocabulary and schema relationships, but it does not by itself teach BIMCraft's current native command interface.

## Additional 2D and constrained-sketch research

- [SketchGraphs](https://github.com/PrincetonLIPS/SketchGraphs) is a useful research dataset for parametric sketch construction and geometric constraint graphs. Its documentation describes 15 million sketches and processed construction-sequence splits. The raw collection is about 43 GB and the filtered construction-sequence package is a separate large download. The GitHub repository's code is MIT-licensed, but the dataset documentation states that the original sketch creators hold the copyright and points to Onshape Terms of Use. Therefore **SketchGraphs is a research lead, not an approved commercial training input**: keep it quarantined until the underlying data terms and rights for model training and redistribution are independently cleared. <Cite refs={["turn128951search1","turn128951search2","turn128951search5"]}/>
- The official [FreeCAD documentation licence](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/License.md) states that the documentation and website use CC-BY-3.0. This makes the official manuals a practical source for a version-pinned, attributed knowledge/training pipeline, subject to retaining the required attribution and checking each source's own notices. Use the actual FreeCAD API and workbench documentation to develop small lessons on Draft entities, Sketcher constraints, Part/PartDesign, assemblies and TechDraw. Do not bulk copy entire manuals into the shipped installer; retrieve relevant excerpts locally and keep attribution/provenance. <Cite refs={["turn128951search0","turn128951search7","turn128951search8"]}/>

For 2D drafting, the first student corpus therefore combines three different sources: authored neutral drafting exercises with exact dimensions, versioned FreeCAD documentation knowledge, and later native FreeCAD operation traces. SketchGraphs may add real constrained-sketch variety only if its dataset rights are cleared. This avoids mistaking a 3D CAD dataset for a complete 2D drafting curriculum.

## Canonical software documentation and observation references

- **FreeCAD:** use the official [documentation repository](https://github.com/FreeCAD/FreeCAD-documentation), [feature list](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Feature_list.md), and [scripting basics](https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/FreeCAD_Scripting_Basics.md). FreeCAD documents that UI actions can be recorded as macros and that its Python API exposes document objects and geometry. NextAI should convert observed actions into safe semantic event records; it must not blindly replay arbitrary macro text generated by a model.
- **Revit as a BIM capability reference:** use the [official Revit API Developer Guide](https://help.autodesk.com/cloudhelp/2027/ENU/Revit-API/files/Revit_API_Developers_Guide_html.html) to study Revit's model objects, transactions, events, views, schedules, families and API concepts. This is a capability reference for BIM workflows, not code to copy into BIMCraft. BIMCraft's own command registry and data model remain authoritative for actual Next BIM execution.
- **OpenBIM:** use the [buildingSMART Standards Server](https://standards.buildingsmart.org/) for IFC, IDS, BCF, MVD and openCDE specifications, plus the [bSDD service](https://www.buildingsmart.org/users/services/buildingsmart-data-dictionary/). IDS expresses machine-checkable information requirements; bSDD supplies definitions and classifications. These are complementary resources, not interchangeable standards.

For manual-work observation, FreeCAD's macro recording and document/selection observer interfaces can provide the source events. In Next BIM, the UI and agents both act on the same BIMCraft Session and native command engine; observe the resulting model changes and active selection at the desktop frame boundary. In both applications, keep the stream local, opt-in, bounded and pauseable. Record object types, dimensions, constraints, relationships and command summaries; exclude unrelated desktop activity, free-text notes and personal project metadata unless the user explicitly shares them with a prompt.

## Additional floor-plan and IFC model corpora

### Swiss Dwellings v3.0.0 — priority architectural floor-plan corpus

- Official release: [Zenodo DOI 10.5281/zenodo.7788422](https://zenodo.org/records/7788422); [dataset and licensing summary](https://archilyse.standfest.science/swiss-dwellings).
- CC BY 4.0; attribute Standfest et al. / Archilyse AG and retain the DOI. The published archive is 931.9 MB. It contains more than 45,000 apartments and about 370,000 rooms across approximately 3,100 buildings.
- `geometries.csv` contains semantic area, separator, opening and fixture geometry as WKT in metres, with local-site coordinates (+x east, +y north), floor/building/plan/unit identifiers, elevation and height. The source documentation says the digitised geometry passed manual QA, with maximum 5% apartment-area deviation and median deviation 1.2%.
- **Implemented ingestion:** `training/nextai/prepare_swiss_dwellings.py` reads the CSV directly from the ZIP without extracting the whole archive, selects whole floors, renders local images and creates exact room-polygon labels, metric area/perimeter values and shared-boundary graphs. All floors from the same building remain in one split. The optional corpus can be merged with `prepare_public_corpora.py --swiss-dwellings-dir <prepared-folder>`.
- Training use: visual-to-vector room understanding and architectural spatial semantics. The dataset is not a statutory design, not as-built truth for every building element and not a certified engineering design set. Do not infer door connectivity from a shared wall boundary. Location ratings, addresses and simulation columns are excluded from the student corpus.
- The 931.9 MB archive is a development-time training source only. It is never bundled in Next3D.

### GNI-BIM Dataset — diverse authored IFC models

- [GitHub repository](https://github.com/ZijianWang-ZW/GNI-BIM-Dataset), [Zenodo record](https://zenodo.org/records/19722012).
- The authors report 224 anonymised IFC building models, including 208 individual student submissions and 16 models from nine multi-discipline projects. The authors parsed 223 of them and report 290,877 physical element instances across 42 IfcElement subclasses. The dataset contents are CC BY 4.0; accompanying anonymisation code is MIT.
- **Quality limitation:** the authors explicitly provide the student-coursework models "as is" with no guarantee of correctness, completeness or fitness for engineering use, and warn about third-party embedded product families. These files are useful for learning actual IFC structures and schema variety, not positive examples of design correctness. Parse, anonymise and validate each model; keep invalid/incomplete records quarantined.

### Large-Scale IFC-Compliant Building Models — generated IFC coverage

- [Zenodo DOI 10.5281/zenodo.20788324](https://doi.org/10.5281/zenodo.20788324).
- The NLM Dataset Catalog describes 73,303 complete IFC4-compliant residential 3D building models generated through a deterministic IfcOpenShell-based rule pipeline. The catalogue lists CC BY 4.0.
- This is an unusually large source of structured IFC residential model patterns. Because it is algorithmically generated and residential-only, use it to expand IFC schema/relationship coverage, not to imply coverage of all real-world BIM workflows or design quality. Inspect the archive, schema, per-file validity, source code and attribution before choosing a sample.

### Other floor-plan data — rights status

- [Modified Swiss Dwellings (MSD)](https://archilyse.standfest.science/modified-swiss-dwellings) is a CC BY 4.0 benchmark derived from Swiss Dwellings, with room polygons, semantic areas, openings and graph-oriented data. It is a useful later benchmark for building-complex generalisation; avoid training on its evaluation split.
- CubiCasa5K and FloorPlanCAD include valuable annotated floor-plan examples but are published under non-commercial licences in their commonly used releases. They are not admitted to commercial NextAI training unless separate permissions are obtained.
- HouseExpo's code repository is MIT, but its content is derived from SUNCG. The underlying dataset rights must be cleared before commercial training; code licence alone does not license the data.

## Engineering curriculum the model must learn

### CAD foundation (application-independent)
1. Coordinate systems, origins, planes, axes, transformations and units.
2. 2D drafting: lines, arcs, circles, polylines, offsets, trims, extensions, hatches, layers, blocks, annotations and dimension styles.
3. Geometry and topology: vertices, edges, wires, faces, shells, solids, surfaces, meshes and tolerances.
4. Parametric design: sketches, constraints, degrees of freedom, dimensions, expressions, dependencies, feature trees and recomputation.
5. Solid modelling: primitives, extrusions, revolutions, sweeps, lofts, booleans, patterns, fillets and chamfers.
6. Assemblies: components, coordinate placement, mates/constraints, clearances and interference.
7. Drawing production: projections, sections, elevations, detail views, dimensions, scales, title blocks and sheet layouts.
8. Exchange and interoperability: STEP, IGES, DXF, DWG where licensed/supported, STL, OBJ, 3MF, SVG and neutral product structures.
9. Design intent, editability, model repair, versioning and revision comparison.

### BIM foundation (application-independent)
1. BIM versus 2D CAD; information-rich objects versus unstructured geometry.
2. Project/site/building/storey/spatial hierarchy, grids, datums, coordinates, georeferencing and units.
3. Object classes, types, instances, families, parameters, materials and property sets.
4. Host/dependent relationships: wall-opening-window/door, slab-edge, roof, stair and railing.
5. IFC schema concepts: entities, inheritance, attributes, property sets, quantity sets, placements, representations and relationships.
6. Views and documentation: plans, sections, elevations, 3D views, view ranges, annotations, tags, schedules and sheets.
7. Coordination: clashes, clearances, model federation, issue tracking, revisions and change impact.
8. Quantities and schedules: take-off, classification, grouping, filters and calculated fields.
9. Construction sequencing and model-based delivery; distinguish 4D/5D concepts from capabilities actually implemented.
10. MEP and structural semantics, with explicit support status for connectivity, calculations and validation.

### Engineering and construction context
Teach terminology and workflow across architecture, civil, structural, geotechnical, mechanical, electrical, plumbing, fire protection, infrastructure and construction. For the current release, prioritise CAD and BIM workflows; expose other disciplines as knowledge-only unless the native application and validated toolset support the operation.

Standards and law must be jurisdiction- and edition-aware. Maintain a source register with issuing body, jurisdiction, edition/date, scope, amendment status, access/licence and citation. Do not copy copyrighted standards such as British Standards into model weights or distribute their text without permission. Retrieval may point to licensed copies or official public sources. A model explanation is not a statutory compliance check or professional certification.

For BIM/openBIM, use the official [buildingSMART Standards Server](https://standards.buildingsmart.org/) and the published [IFC 4.3.2.0 specification](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/index.html) as canonical schema references. buildingSMART also publishes IDS, BCF, bSDD and openCDE specifications. Its formal IFC specification is published under CC BY-ND 4.0; preserve the exact version and licence conditions, and do not turn the full specification into a modified redistributed knowledge pack or training target without a legal review. Use schema files and validation tools to check generated IFC, not language-model confidence.

## How to specialise the compact model

1. **Baseline first:** pin one candidate checkpoint and runtime; measure it on a held-out CAD/BIM benchmark before training.
2. **Curate, don't dump:** select balanced examples from the public datasets. Remove malformed programs, duplicate templates, invalid geometry, unsupported features, ambiguous units and records without acceptable provenance.
3. **Build a neutral engineering representation:** represent design intent as typed entities, parameters with units, constraints, coordinate frames, relationships, ordered features and expected checks. Keep this separate from either app's API.
4. **Generate native traces:** for each selected CAD task, execute a corresponding operation sequence in FreeCAD and validate the resulting FCStd project. For BIM tasks, create/inspect native BIMCraft project states and IFC exports. Only successful native traces become positive application-specific tool examples.
5. **Train separate skills in one shared model:** task/domain routing, specification extraction, clarification, plan generation, tool selection, typed JSON arguments, progress narration, error interpretation and repair. Keep separate NextCAD and Next BIM adapters/tool schemas.
6. **LoRA fine-tune:** train in a separate GPU environment; never ship training libraries or raw corpora in the desktop installer. Preserve the original checkpoint and compare base versus tuned model on exactly the same held-out tasks.
7. **Vision training only with ground truth:** pair drawings/images with exact dimensions, scale, units, layers, native model and verified geometry. Do not teach the model to infer exact dimensions from unscaled screenshots.
8. **Promote only on evidence:** tuned model must improve native task completion and reduce invalid tool calls without increasing unsafe operations. If it fails, improve data/tool contracts or use a larger optional model profile rather than pretending the small model is expert.

## Live manual-work observation

NextAI should observe the user's actual native editing activity through application events and state snapshots, not by guessing from screenshots alone.

Capture (with visible user control):
- active document and application version;
- selected object(s), workbench/tool and current selection context;
- created/modified/deleted object events;
- changed properties, dimensions, units and constraints;
- feature-tree or BIM object-graph changes;
- recompute/validation results and undo/redo transaction boundaries;
- current view/camera and optional viewport snapshot when visual context is needed.

Convert events into a compact project-state delta and an explanation of what changed. The assistant can then say what it observed, answer questions about the live project and offer next actions. Observation must be local, transparent, pauseable and excluded from model training unless the user separately opts in. Never capture unrelated desktop windows or transmit project state remotely in local mode.

## Initial implementation deliverables

- [ ] Dataset manifest with pinned revisions, licence, source, split, checksum, filters and admission status.
- [ ] Dataset inspection/normalisation scripts outside the shipped application.
- [ ] Neutral CAD/BIM intent schema and versioned application-specific trace schemas.
- [ ] FreeCAD-native task generator and validator; BIMCraft-native task generator and IFC validation path.
- [ ] Held-out benchmark independent of training data.
- [ ] LoRA training configuration and reproducible training run.
- [ ] Runtime event-observation API for NextCAD and Next BIM.
- [ ] Model card documenting hardware, supported languages, limitations, evaluation and provenance.
- [ ] Package-size report proving the full product stays within 1.2 GB, or an explicit measured exception.

## Source references

- https://huggingface.co/datasets/ADSKAILab/Zero-To-CAD-1m
- https://huggingface.co/datasets/filapro/cad-recode-v1.5
- https://huggingface.co/datasets/Dietmar2020/ifc-bim-alpaca-124k
- https://huggingface.co/datasets/Dietmar2020/ifc-bim-qa-dataset
- https://huggingface.co/datasets/Dietmar2020/ifc-bim-high-quality-alpaca
- https://huggingface.co/datasets/cairndev/ifc-bim-alpaca-dedup
- https://huggingface.co/ADSKAILab/Zero-To-CAD-Qwen3-VL-2B
- https://huggingface.co/cairndev/qwen3-4b-ifc-bim-qlora
