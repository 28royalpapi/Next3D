# NextAI large-scale engineering student programme

Status: implementation programme and corpus builder. This document does not claim that a 400-million-token corpus has already been downloaded or trained.

## Why the previous recipe was too small

The earlier notebook defaults selected 2,500 of the 81,000 available Zero-to-CAD training rows, 30,000 of the 112,476 IFC/BIM Alpaca training rows, and 5,000 IFC/BIM QA rows. It then capped the mixed/public sample at 24,000 records. Most of the licensed upstream material was therefore excluded before training.

The new full-source builder uses the published splits and raises the mixed sampler to 300,000 records. It keeps a real validation set and untouched held-out test set, while also retaining every first-party skill and native-capability knowledge lesson.

## Target scale

The programme uses 400 million **measured student-token** updates as an ambitious planning benchmark, inspired by N-ATLaS. That is a target, not a number to reach by duplicating short prompts, repeating records or counting image files as tokens.

The actual corpus size is determined by the tokenizer loaded from Qwen/Qwen3.5-0.8B. \`audit_nextai_corpus.py\` reports text-token counts for train, validation and test separately, plus tool schemas, source/domain balance, image files and image bytes. Vision patch tokens and the runtime chat-template overhead are explicitly reported as outside that text-token count.

If the complete licensed source corpus does not reach 400M unique text tokens, the report must show the measured shortfall. Expansion must come from additional licensed engineering material and native-verified traces, not from synthetic paraphrase inflation.

## Five-stage learning programme

### Stage 0 — Baseline and data admission
- Record the untouched Qwen3.5-0.8B baseline on the held-out engineering benchmark before training.
- Verify provenance, licence, source split, record identity, group hashes, image assets, duplicate leakage and token counts.
- Quarantine broken images, empty targets, duplicate leakage, unresolved licences and unsupported native-operation claims.
- Keep the test split out of gradient updates and retrieval during training.

### Stage 1 — Geometric and parametric CAD
- Multi-view geometry understanding and feature-family recognition.
- Construction traces: sketches, constraints, pads, pockets, revolve, sweep, loft, booleans, shells, fillets, chamfers, patterns and transforms.
- Feature order, preconditions, parameters, dimensions and units.
- Parametric dependency diagnosis, topology validity, recompute and editability.
- Native FreeCAD/NextCAD command selection, typed inputs and unsupported-operation reporting.

### Stage 2 — BIM and information modelling
- IFC schema and entity semantics, spatial hierarchy, containment, aggregation, typing and material/property relationships.
- Walls, floors, roofs, doors, windows, rooms, levels, grids, stairs, structure and schedules.
- Hosted openings, room boundaries, quantities, phasing, renovation and multi-storey variation.
- MEP networks, connectors, systems, clashes, IFC export/import and model handover.
- BIMCraft command discovery, parameter selection, stable element identity and in-place modification.

### Stage 3 — Engineering reasoning and discipline practice
- Mathematics, units, dimensions, numerical estimation and error checking.
- Structural analysis concepts, statics, beams, slabs, columns, foundations, concrete, steel and timber.
- Geotechnical interpretation, effective stress, consolidation, bearing, settlement and ground investigation limits.
- Hydrology, open-channel flow, pipe hydraulics, pumps, water supply, drainage and networks.
- Surveying, coordinate transformations, levelling, setting out, earthworks and road geometry.
- Mechanical design, materials, fits, tolerances, gears, assemblies, manufacturing, FEM and CAM preparation.
- Electrical and building-services coordination, while keeping safety-critical design decisions tied to applicable standards and validated inputs.

### Stage 4 — Operator behaviour, tool use and repair
- Multi-turn design intake: identify missing requirements and preserve answers.
- Live native capability discovery and exact command/schema selection.
- Ordered multi-step planning, typed tool calls and visible progress.
- Model-state inspection before and after each operation.
- Revision of existing objects while preserving identity, dependencies, hosts and relationships.
- Failure diagnosis, rollback, recompute recovery and honest reporting.
- Tool-call traces must be kept separate by evidence level. L0 knowledge is never relabelled as L3 native success.

### Stage 5 — Mixed integration and independent examination
- Whole projects combining architectural, structural, MEP, civil, mechanical and documentation work.
- New/unseen combinations of tools, room programmes, products and project constraints.
- Held-out tasks by source group and project family, not random paraphrases of training prompts.
- Base-versus-candidate comparisons, measured by domain and failure class.
- Real NextCAD and Next BIM execution, save/close/reopen, geometry and IFC validation before model promotion.

## Data sources currently admitted by the repository

| Source | Published scale / licence | Curriculum value | Admission boundary |
|---|---|---|---|
| ADSKAILab/Zero-To-CAD-100k | 81.0K train, 9.7K validation, 9.8K test; Apache-2.0 | Multi-view synthetic CAD and feature-operation traces | Translate CadQuery concepts into the neutral plan; do not pretend CadQuery calls are FreeCAD-native commands |
| Dietmar2020/ifc-bim-alpaca-124k | 112.5K train, 12.5K validation; MIT | IFC/BIM instruction and relationship knowledge | Keep the existing source-validated + score >=4.5 filter; source validation is not Next3D validation |
| Dietmar2020/ifc-bim-qa-dataset | 9.8K train, 3.7K test; CC-BY-4.0 | IFC conceptual/schema QA | Preserve attribution; test remains held out |
| Next3D authored curriculum | Project-authored | Design intake, operator method, engineering examples and native plans | Authored lessons remain L0 unless native execution evidence exists |
| Pinned capability census | Upstream source licences | Ten knowledge dimensions per discovered native capability | L0 metadata lessons, not command-execution proof |
| Swiss Dwellings (optional) | CC-BY-4.0 | Measured residential floor-plan geometry and room relationships | Keep building-level split and source attribution |
| GNI BIM IFC models (optional) | CC-BY-4.0 as declared by preparation manifest | IFC model hierarchy and object/property relationships | Coursework examples; never use as engineering truth |

## Why 400M tokens is not automatically the right first fine-tuning run

The published N-ATLaS model is based on Llama-3 8B. NextAI's packaged student is Qwen3.5-0.8B because the project requires a compact local model. These are very different capacity budgets.

For the 0.8B student, training must use staged, domain-balanced batches and replay of earlier capabilities. Repeated exposure to the same examples is not a substitute for new verified knowledge. The 400M goal is a measured scale target; it must not override validation quality or the package-size constraint.

The application must also keep versioned retrieval, typed native execution and engineering validators. A compact student cannot safely store every version of every CAD/BIM manual or guarantee professional design approval from model weights alone.

## Compute and reproducibility

- Corpus build: full published source splits, pinned random seed, source/version and licence manifest.
- Audit: exact Qwen tokenizer text counts, token-length distribution, image inventory, split-leakage checks, per-domain/source counts.
- Fine-tune: BF16 LoRA on both vision and language branches; no QLoRA substitution for this selected Qwen3.5 recipe.
- Save: resumable checkpoints, adapter, tokenizer, training configuration, RNG seed, GPU/driver and package versions, logs and final checksums.
- Evaluation: unchanged held-out set; same decoding parameters for base/candidate; per-domain reports; no test use in gradients.
- Native release gate: actual application operations and save/reopen round-trips in both NextCAD and Next BIM.
- Packaging: verify Q4_K_M model + Q8_0 vision projector and total package against the 1.2 GB ceiling, separately from desktop application binaries.

## Current blockers

1. The Hugging Face corpus and student model repositories are currently empty apart from Hub metadata.
2. The connected Hugging Face account has no visible running Jobs. A GPU run needs a positive compute-credit balance; current published Jobs pricing bills by the minute.
3. Full CAD multimodal training needs a GPU with sufficient VRAM and ephemeral storage; the 8-view images make a small T4 a risky choice for the full run.
4. Native-executed training traces remain limited until the real application acceptance workflows pass and emit records.

Do not mark the project as trained until \`training_result.json\`, adapter/checkpoint artifacts, measured token-audit report, held-out evaluation and native acceptance evidence exist.
