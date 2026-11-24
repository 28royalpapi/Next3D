# NextAI compact-student training pipeline

The only runtime student is Qwen3.5-0.8B. The larger CAD and BIM teacher models are research/training aids only. Teacher weights, raw datasets, training images, checkpoints and training libraries are never shipped in the Next3D installer.

## Data sources and admission

- Autodesk Zero-to-CAD-100k (Apache-2.0): use bounded streaming samples from its train, validation and test splits. It includes eight rendered views and a structured construction-operation trace.
- IFC BIM Alpaca 124K (MIT): admit only high-quality rows whose source metadata says validated=true and whose score is at least 4.5. This flag is treated as a source claim, not as actual IFC/BIMCraft validation.
- IFC BIM QA (CC-BY-4.0): preserve Dietmar2020 attribution and keep its test split held out.
- Native NextCAD and Next BIM training records: admit only when they pass the native training-record schema, permissions/consent, application recompute, geometry/model validation and save/reopen round trip.
- Cairn IFC BIM deduplicated data is excluded from positive training until its generated IFC has been independently validated; its own dataset card says its IFC output is unvalidated.
- CAD-Recode v1.5 (CC-BY-NC-4.0) is excluded from commercial model training unless separate commercial permission is obtained.

## Prepare

Install the training-only data libraries:

    pip install datasets pillow

Prepare a bounded mixed corpus outside the app:

    python training/nextai/prepare_public_corpora.py --output-dir /workspace/nextai-corpus --max-cad-train 2500 --max-bim-train 30000 --max-mixed-train 24000

The builder also adds a small Next3D-authored synthetic curriculum for 2D drafting, parametric sketches, 3D feature order, technical drawing documentation, BIM spatial concepts, IFC wall-opening-window relationships, BIM documentation and construction information workflows. These are neutral concepts and feature plans, not claims of native execution. Optional validated native trace files can be supplied with --nextcad-native and --nextbim-native. Training and validation are separate from the untouched test split. The manifest records source licences, counts, and domain mix.

## Train

The trainer follows the Unsloth Qwen3.5-0.8B vision recipe with BF16/FP16 LoRA (depending on GPU hardware), vision encoder weights frozen in the first pass, and language/attention/MLP layers trainable. It does not use QLoRA. Begin with a small run to check memory and loss before a longer experiment.

    pip install --upgrade unsloth unsloth_zoo
    pip install --upgrade transformers trl datasets peft accelerate bitsandbytes pillow
    python training/nextai/train_nextai.py --data-dir /workspace/nextai-corpus --output-dir /workspace/nextai-run-001 --max-steps 800

The script saves the LoRA adapter and exports a Q4_K_M GGUF. The teacher weights are not required for this training script and are not bundled. The final merged quantised model is a new candidate; it must be independently benchmarked before replacing the current runtime baseline.

## Promotion gates

- Measure CAD visual feature recognition, feature ordering, dimensional preservation, and unit handling.
- Measure BIM/IFC schema QA, IFC relationships, materials, properties and requirements.
- Measure native command planning separately for NextCAD and Next BIM.
- Actually run the proposed actions in the native applications and verify geometry/model state, recompute, rollback/undo, save/reopen and exchange exports.
- Report each domain separately. Do not let a high CAD average hide a failed BIM capability.
- Measure the final GGUF and projector file sizes, then the full download and installed Next3D package for each OS. Never strip native FreeCAD workbenches or BIMCraft features to reach the 1.2 GB ceiling.

The local execution container currently has no CUDA GPU. No actual model training is claimed by adding these scripts; an authorised GPU environment is required to run the training command.
