# NextAI compact-student training pipeline

The only runtime student is Qwen3.5-0.8B. The larger CAD and BIM teacher models are research/training aids only. Teacher weights, raw datasets, training images, checkpoints and training libraries are never shipped in the Next3D installer.

## Data sources and admission

- Autodesk Zero-to-CAD-100k (Apache-2.0): use bounded streaming samples from its train, validation and test splits. It includes eight rendered views and a structured construction-operation trace.
- IFC BIM Alpaca 124K (MIT): admit only high-quality rows with the published `source` label containing `validated` (for example `validated-synthetic`) or an explicit `metadata.validated=true` flag, and a score of at least 4.5. This remains a dataset provenance claim, not actual IFC/BIMCraft validation.
- IFC BIM QA (CC-BY-4.0): preserve Dietmar2020 attribution and keep its test split held out.
- Native NextCAD and Next BIM training records: admit only when they pass the native training-record schema, permissions/consent, application recompute, geometry/model validation and save/reopen round trip.
- Cairn IFC BIM deduplicated data is excluded from positive training until its generated IFC has been independently validated; its own dataset card says its IFC output is unvalidated.
- CAD-Recode v1.5 (CC-BY-NC-4.0) is excluded from commercial model training unless separate commercial permission is obtained.

## Prepare

Install the training-only data libraries:

    pip install datasets pillow shapely ifcopenshell

Prepare a bounded mixed corpus outside the app:

    python training/nextai/prepare_public_corpora.py --output-dir /workspace/nextai-corpus --max-cad-train 2500 --max-bim-train 30000 --max-mixed-train 24000 --swiss-dwellings-dir /workspace/swiss-dwellings-corpus --ifc-model-corpus-dir /workspace/gni-ifc-corpus

### Optional real architectural and IFC model lessons

Swiss Dwellings v3.0.0 adds real 2D floor-plan images rendered from metric vector geometry. Download the 931.9 MB ZIP from [Zenodo](https://zenodo.org/records/7788422) into the external training workspace, then prepare it:

    python training/nextai/prepare_swiss_dwellings.py --zip /workspace/swiss-dwellings-v3.0.0.zip --output-dir /workspace/swiss-dwellings-corpus --max-train 600 --max-validation 60 --max-test 60

The optional records are split by building, not by individual floor, so floors from one building cannot leak between train and test. Room polygons, labels, calculated area/perimeter and shared-boundary relationships are derived from the original WKT in metres. The model is explicitly told that a shared wall is not proof of a door or passable connection.

For IFC model understanding, the local IFC parser uses IfcOpenShell to extract schema, spatial structure, element classes, material assignments, safe numeric properties and explicit IFC relationships. For the GNI-BIM dataset, download [2025_BIMfundamentals.zip](https://zenodo.org/records/19722012) and [2026_BIMprojects.zip](https://zenodo.org/records/19722012) from Zenodo, extract them into one folder, and run:

    python training/nextai/prepare_ifc_models.py --root /workspace/gni-ifc --output-dir /workspace/gni-ifc-corpus --source-name "GNI-BIM Dataset" --doi 10.5281/zenodo.19722012 --license CC-BY-4.0

Then pass the prepared folders to the main corpus builder using `--swiss-dwellings-dir` and `--ifc-model-corpus-dir`. Both raw corpora and all parsed/rendered assets remain external training data; they are not part of the application package. IFC parsing does not prove student models are correct or engineering-compliant.

The [GNI-BIM dataset](https://github.com/ZijianWang-ZW/GNI-BIM-Dataset) includes 224 IFC models, but its authors explicitly disclaim correctness and completeness. It is used for IFC structure, relationships and property vocabulary, not as engineering truth. A separate 73,303-model IFC4 dataset is also documented in the source register as a later broad-coverage option; its generated residential scope should not be confused with diverse real project design examples.

Validated native project traces from both applications can be added without mixing them into the wrong application or held-out split. First run `prepare_native_sft.py` over approved native records to produce separate `train.jsonl`, `validation.jsonl` and `test.jsonl`. Then pass the six corresponding paths:

    --nextcad-native-train /workspace/nextcad-sft/train.jsonl
    --nextcad-native-validation /workspace/nextcad-sft/validation.jsonl
    --nextcad-native-test /workspace/nextcad-sft/test.jsonl
    --nextbim-native-train /workspace/nextbim-sft/train.jsonl
    --nextbim-native-validation /workspace/nextbim-sft/validation.jsonl
    --nextbim-native-test /workspace/nextbim-sft/test.jsonl

Each record retains the producing application, source licence, privacy status and source-group hash. The corpus builder rejects a native record assigned to the wrong application or split. The older `--nextcad-native` and `--nextbim-native` flags remain train-only compatibility aliases.

The builder streams the CAD dataset's published `train`, `validation` and `test` splits (not a guessed `val` split name), decodes its eight Hugging Face image views, and adds a Next3D-authored curriculum for 2D drafting, constrained sketches, 3D feature order, technical documentation, explicit three-bedroom/two-bathroom floor-plan geometry, structural grids and framing relationships, MEP system connectivity, clash coordination, quantity schedules, IFC relationships and construction handover. These are neutral design-intent lessons, not claims of native execution or engineering/code compliance. Optional validated native trace files can be supplied using the application- and split-specific flags above. Training and validation are separate from the untouched test split. The manifest records source licences, counts, and domain mix.

### Guided design conversations

The authored curriculum now includes three-turn design-intake examples for residential and commercial floor plans, vehicles, consumer products, mechanical parts, assemblies, sheet-metal enclosures, manufacturing drawings, CAM setup, new-build BIM, renovation BIM and civil infrastructure. For a three-bedroom home, the student first asks whether it is a bungalow or storey house, the number of master bedrooms, total toilets and ensuite/shared split, sitting/living-room arrangement, optional rooms such as a store, and plot dimensions/road access. It then carries confirmed answers forward and asks only for missing information. The final turn summarises the room programme and distinguishes a schematic concept from a dimensioned site-fitted plan. Similar intake stages teach vehicle packaging, component interfaces, assembly joints, BIM disciplines, coordinate references, information requirements, IFC deliverables and existing-condition evidence.

Each design scenario produces separate initial-question, context-aware-follow-up and confirmed-brief examples. The three records share one split group, so stages from the same conversation cannot be scattered across training, validation and test. These are authored dialogue lessons, not real CAD/BIM execution traces. The student must still call the appropriate native NextCAD or BIMCraft tools, then verify geometry, constraints, recompute, save/reopen and exchange validation before reporting a model as created.

The design-intake programme now contains 114 scenarios (342 conversation-turn examples): it includes a dedicated watchtower/guard-tower interview that asks whether the structure is steel, reinforced concrete or another system, and clarifies occupancy, platform height, cabin, access, roof, guardrails, wind, site and ground information. A separate design-execution programme adds four native NextCAD tool-plan examples: an editable three-bedroom room-zoning plan with labels/dimensions; a named 3D watchtower concept with separate columns, beams, deck, cabin walls, roof and member schedule; a PartDesign mounting base built from a constrained sketch, Pad and through-hole Pocket; and an in-place edit of an existing beam. These examples use the exact typed NextCAD tool registry and the expected message/plan response shape. The floor plan is explicitly room zoning rather than a full door/window/wall construction model. The tower's member envelopes are explicitly visual placeholders, not engineered sections. The example mechanical part has no assumed material, loads or tolerances.

The shared local knowledge pack, design/design-execution.md, teaches staged creation, viewport feedback, editable feature history, object labels, component schedules, inspection and in-place modification. NextCAD's execution layer now recomputes and refreshes the native viewport after each approved operation while keeping the multi-step edit in one undo/rollback transaction. Its edit_native_property operation changes a restricted set of existing native dimensions or labels and validates the recomputed object. BIMCraft's existing assistant is being taught to perform work in visible batches using inspect_model, list_commands, execute, query_elements, modify and todo_write. This changes its native assistant guidance; it does not mean the Qwen student is already connected as BIMCraft's live provider.

## Train

The trainer follows the official Unsloth Qwen3.5-0.8B vision recipe with BF16 when supported and FP16 otherwise. It applies rank-16 LoRA to both vision and language pathways while preserving the original base checkpoint weights; it does not use QLoRA. The curriculum covers 2D drafting and coordinate systems; sketch constraint diagnosis; parametric feature trees, booleans, surface operations, topology and mesh quality; assemblies, technical drawings, FEM and CAM preparation; BIM spatial/type/property/IFC relationships, room boundaries, georeferencing, phases, asset handover and change impact; plus structural, reinforced-concrete, geotechnical, water, surveying, site coordination, project controls, 4D scheduling, quantities, quality, safety and standards-aware workflows. The authored lessons also include worked, unit-checked examples for simply supported beam reactions, a two-node axial-bar FEM element, pipe continuity and concrete volume; each states its idealisations and what the calculation does not prove. These are original teaching examples and structured plans, not native application traces or certified engineering designs. The default notebook completes one full pass over the sampled training set; use `--max-steps 100` for a short memory/throughput smoke test before the full pass. It selects BF16 where the GPU supports it, otherwise FP16. The Unsloth guide reports about 3 GB VRAM for a basic 0.8B BF16 LoRA recipe; multi-view CAD and 4K context can need more headroom, so the notebook checks actual GPU memory and should be adjusted if it runs out.

    pip install --upgrade unsloth unsloth_zoo
    pip install --upgrade transformers trl datasets peft accelerate bitsandbytes pillow
    python training/nextai/train_nextai.py --data-dir /workspace/nextai-corpus --output-dir /workspace/nextai-run-001 --max-steps -1 --num-train-epochs 1

The script saves the LoRA adapter, a temporary merged 16-bit checkpoint, and exports the main language model as Q4_K_M GGUF. The notebook then converts the separate multimodal vision projector to Q8_0 with the repository's `quantize-mmproj-q8.sh`, verifies its GGUF header and SHA-256, and replaces the full-precision projector only after the Q8 file is valid. The teacher weights are not required for this training script and are not bundled. The final merged quantised model is a new candidate; it must be independently benchmarked before replacing the current runtime baseline.

## Compare the untouched student and tuned candidate

Run the same held-out test file against the untouched student and the trained candidate, writing separate reports. The training script defaults to one complete epoch (`--max-steps -1`) rather than stopping after an arbitrary 800 steps; validation metrics are recorded at the end of the run. A second epoch is considered only after validation shows improvement without overfitting:

    python training/nextai/evaluate_nextai.py --model Qwen/Qwen3.5-0.8B --test-jsonl /workspace/nextai-corpus/test.jsonl --output /workspace/eval-base.json
    python training/nextai/evaluate_nextai.py --model /workspace/nextai-run-001/merged_16bit --test-jsonl /workspace/nextai-corpus/test.jsonl --output /workspace/eval-tuned.json

The evaluator reports JSON parse rate, expected-key recall, scalar matches and lexical overlap separately by task domain. These are diagnostics, not engineering correctness. Compare the base and tuned reports on the identical test split before native engine validation.

## Promotion gates

- Measure CAD visual feature recognition, feature ordering, dimensional preservation, and unit handling.
- Measure BIM/IFC schema QA, IFC relationships, materials, properties and requirements.
- Measure native command planning separately for NextCAD and Next BIM.
- Actually run the proposed actions in the native applications and verify geometry/model state, recompute, rollback/undo, save/reopen and exchange exports.
- Report each domain separately. Do not let a high CAD average hide a failed BIM capability.
- Measure the final GGUF and projector file sizes, then the full download and installed Next3D package for each OS. Never strip native FreeCAD workbenches or BIMCraft features to reach the 1.2 GB ceiling.

The local execution container currently has no CUDA GPU. No actual model training is claimed by adding these scripts; an authorised GPU environment is required to run the training command.


## One-click GPU notebook

Open [NextAI_Qwen35_Engineering_Student.ipynb](./NextAI_Qwen35_Engineering_Student.ipynb) in Google Colab, select a GPU runtime, and run the cells from top to bottom. It downloads only the bounded teaching sample, trains the single 0.8B student, evaluates the untouched test set, and reports the exported GGUF byte size. The notebook does not upload training data or model files into the Next3D application package.

The notebook is a reproducible training entry point, not evidence that a training run has completed. The Qwen3.5 vision projector is a separate runtime artifact: public Q4_K_M examples list a roughly 564 MB language model plus a roughly 198 MB F16 projector, so both must be counted. A public Qwen3.5-0.8B GGUF listing reports about 564 MB for Q4_K_M and 198 MB for the F16 projector ([reference](https://huggingface.co/notschmee/Qwen3.5-0.8B-GGUF)). Our Q8 projector export is intended to reduce this second component, but its actual bytes must be measured after export. Save its output and training report as the experiment artifact. Do not promote a candidate based on training loss alone.
