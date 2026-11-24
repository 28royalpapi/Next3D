# NextAI model specialisation pipeline

This folder contains training-only tooling. Nothing here is shipped in the Next3D desktop installer.

## Training strategy

- Runtime baseline: one shared Qwen3.5-0.8B Artemis Q4_K_M model for both applications.
- Fine-tuning source checkpoint: use the compatible Hugging Face Transformers checkpoint, not the quantised GGUF file.
- Training method: supervised fine-tuning with BF16 LoRA in a separate GPU environment; merge the approved adapter and export/quantise once.
- Teacher references: Autodesk Zero-To-CAD-Qwen3-VL-2B for CAD construction-sequence research and the Qwen3-4B IFC/BIM adapter for BIM/IFC research. Teachers are not runtime dependencies and are not bundled.
- CAD source data: stratified sample of Zero-To-CAD-1M; convert CadQuery examples through a neutral intent representation, then generate and validate equivalent FreeCAD-native traces.
- BIM source data: audit IFC BIM Alpaca 124K and the deduplicated IFC/BIM subset; verify every admitted record against the correct IFC schema and BIMCraft-native model/command checks.
- Exclude CAD-Recode v1.5 from commercial training unless separate commercial permission is obtained because its Hub licence is CC-BY-NC-4.0.

## Native-trace admission gate

A positive training example must already have:
1. a provenance-aware training record conforming to the NextAI training-record schema;
2. reviewed source terms and cleared permission;
3. explicit consent for user-owned projects;
4. no unredacted personal data;
5. successful native validation, recompute and save/reopen;
6. versioned native tool names and typed arguments.

Run the standard-library-only converter:

    python training/nextai/prepare_native_sft.py --input /path/to/approved-native-records.jsonl --output-dir /path/to/nextai-sft

The output contains separate train.jsonl, validation.jsonl, test.jsonl, quarantine.jsonl and summary.json. The test split is never merged into training. Records sharing one source lineage across different splits are quarantined to prevent leakage.

## Training/evaluation rule

Mix CAD and BIM records in the same training run so the shared model retains both domains. Track per-domain and per-application scores separately. Keep held-out native tasks and project lineages out of both training and retrieval. Do not promote a fine-tuned model unless it improves native CAD/BIM completion and does not increase invalid geometry, incorrect units, unsupported commands or unsafe actions.

Fine-tuning teaches NextAI's response and tool-selection patterns. Versioned retrieval remains responsible for changing manuals, API references, laws and standards; native applications remain responsible for geometry and model validation.
