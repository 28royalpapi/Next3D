# NextAI large-scale engineering student programme

Status: implementation programme and corpus builder. This document does not claim that a 400-million-token corpus has already been downloaded or trained.

## Why the previous recipe was too small

The earlier notebook defaults selected 2,500 of the 81,000 available Zero-to-CAD training rows, 30,000 of the 112,476 IFC/BIM Alpaca training rows, and 5,000 IFC/BIM QA rows. It then capped the mixed/public sample at 24,000 records. Most of the licensed upstream material was therefore excluded before training.

The new full-source builder includes all available licensed rows from the published CAD and BIM splits plus the 145,117-record BuildEng source. It adds a 170,000-case original analytic curriculum (10,000 cases in each of 22 engineering families), raises the mixed sampler to 700,000 records, and creates deterministic internal validation/test partitions for BuildEng, which publishes only one train split. It keeps the other source splits separate and untouched, while also retaining every first-party skill and native-capability knowledge lesson.

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
| Irfanuruchi/buildeng | 145,117 train rows; Apache-2.0 | Civil/structural/building reasoning, beam calculations, inspection-first decisions, missing-input discipline, repair, foundations, settlement, MEP safety | One published train split only; create deterministic internal partitions by normalized category + user brief; publisher-described validated is not Next3D native verification |
| Next3D authored curriculum | Project-authored | Design intake, operator method, engineering examples and native plans | Authored lessons remain L0 unless native execution evidence exists |
| Pinned capability census | Upstream source licences | Ten knowledge dimensions per discovered native capability | L0 metadata lessons, not command-execution proof |
| Swiss Dwellings (optional) | CC-BY-4.0 | Measured residential floor-plan geometry and room relationships | Keep building-level split and source attribution |
| GNI BIM IFC models (optional) | CC-BY-4.0 as declared by preparation manifest | IFC model hierarchy and object/property relationships | Coursework examples; never use as engineering truth |

## Original formula-checked engineering curriculum

The generator `generate_verified_engineering_cases.py` currently implements 22 formula families: simply supported beams under UDL and central point loads, cantilevers, axial bars, shaft torsion, pipe continuity, Darcy-Weisbach losses, Manning open-channel flow, effective stress, one-dimensional consolidation, concrete slab quantities, reinforcement mass, gear ratios, three-phase power, differential levelling, rectangular section properties and average-end-area earthworks.

The full-scale builder creates 10,000 distinct parameterised cases per family (170,000 total target records). Each answer includes its governing equations, exact inputs, calculated outputs, units, assumptions and limitations. The generator is checked against independent reference calculations in unit tests. These are L0 educational examples from closed-form solvers; they are not FEM results, code checks, native CAD/BIM executions or engineering approvals. The corpus audit measures their actual Qwen token contribution after generation.

## External examination candidates

**Google Physical-Engineering's Last Exam** is a gated Hugging Face benchmark with long-horizon engineering workspaces across electrical, civil, structural and mechanical engineering. It carries a CC-BY-4.0 tag. It is an evaluation candidate, not training material: keep its task workspaces and expected deliverables out of training, retrieval and prompt examples. The current Justin75685 Hub connection cannot inspect the gated files; use it only after the dataset access terms are accepted and the evaluation protocol is reviewed.

Two other potentially useful datasets remain quarantined rather than being silently admitted. MechQA contains 202,068 material-property QA pairs derived from 125,967 research papers, and its paper is CC-BY-4.0, but the dataset repository does not declare a dataset licence and the underlying article-context rights need a record-level review. OpenPyStruct describes a two-million-case structural-response dataset, but the Zenodo dataset record does not state a dataset licence; its MIT software licence does not, by itself, establish the data licence. Neither is included in this corpus builder until those rights are resolved.

## Why 400M tokens is not automatically the right first fine-tuning run

The published N-ATLaS model is based on Llama-3 8B. NextAI's packaged student is Qwen3.5-0.8B because the project requires a compact local model. These are very different capacity budgets.

For the 0.8B student, training must use staged, domain-balanced batches and replay of earlier capabilities. Repeated exposure to the same examples is not a substitute for new verified knowledge. The 400M goal is a measured scale target; it must not override validation quality or the package-size constraint.

The application must also keep versioned retrieval, typed native execution and engineering validators. A compact student cannot safely store every version of every CAD/BIM manual or guarantee professional design approval from model weights alone.

## Progressive five-stage course

Each SFT epoch is now ordered as an actual progressive course rather than shuffled as one flat mixture:

1. **Foundations:** mathematical relationships, units, measurements, statics and basic engineering calculations.
2. **CAD/BIM fluency:** parametric CAD concepts, geometry/feature traces, IFC semantics and BIM model structure.
3. **Engineering disciplines:** civil/structural/geotechnical/hydraulic/mechanical/electrical reasoning, including the BuildEng source.
4. **Operator methods:** capability discovery, design interviews, command/schema selection, planning, revision and recovery.
5. **Integrated projects:** native execution traces and complete multi-discipline workflows where the relevant evidence exists.

Within every later stage, the trainer inserts a deterministic 10% rehearsal sample from all earlier stages after each 32 new examples. This is spaced replay: new material is introduced progressively, while the student repeatedly revisits earlier material. The trainer uses a sequential sampler so the order is preserved. The exact stage counts, replay counts, seed and SHA-256 of the ordered index are written to `curriculum_schedule.json` and `training_config.json`; resuming a run must use the same corpus and seed.

These stages are a training schedule, not proof that the model has mastered a discipline. Promotion still depends on untouched tests, unseen engineering cases and native application acceptance.

## Large-corpus memory and examination controls

The trainer uses an indexed JSONL dataset: it first builds a compact byte-offset index, then reads/decodes one record when a batch requests it. It validates each split without retaining the full record set in memory. The validation split is used for in-training evaluation. The held-out test split is not evaluated during fine-tuning; after the candidate checkpoint is frozen, both the untouched base model and candidate are evaluated on the same test split and compared by domain. This prevents repeated peeking at the final examination while training decisions are still being made.

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

## Native collector manifest handoff

The native execution path is deliberately separate from public/synthetic corpus generation. Build and launch the pinned native apps first; then collect each application's controlled train/validation/test acceptance runs:

```bash
python scripts/collect_nextcad_native_splits.py --executable /path/to/NextCAD --output-dir artifacts/native/nextcad
python scripts/collect_nextbim_native_splits.py --cli /path/to/bimcraft-cli --output-dir artifacts/native/nextbim
```

After both collectors finish, the full-scale builder consumes the manifests, re-verifies their artifact inventories and split contents, and refuses to proceed unless both apps have all six non-empty split files:

```bash
python training/nextai/prepare_large_scale_corpus.py \
  --output-dir artifacts/nextai-full-corpus \
  --nextcad-native-manifest artifacts/native/nextcad/manifest.json \
  --nextbim-native-manifest artifacts/native/nextbim/manifest.json \
  --require-native-manifests \
  --nextcad-runtime-report artifacts/nextcad-runtime/nextcad-runtime.json \
  --require-nextcad-runtime
```

The runtime report is produced by running training/nextai/discover_nextcad_runtime.FCMacro inside the pinned NextCAD GUI. The build also performs the tokenizer audit unless explicitly disabled. A successful manifest check means the collected files and provenance declarations are internally consistent; it does not mean NextAI has been trained or has passed independent engineering validation.
