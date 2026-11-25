# NextAI local model selection

## First baseline

Use one shared model for NextCAD and Next BIM:

- Base: Qwen3.5-0.8B (873.4 million parameters).
- Quantisation: TurinTech Artemis Q4_K_M GGUF.
- Model file: 532,402,496 bytes (about 532.4 MB).
- Vision projector: mmproj-F16.gguf, 204,986,976 bytes (about 205.0 MB).
- Combined model plus projector: about 737.4 MB decimal, before the inference runtime and applications.
- Local Ollama model: hf.co/turintech/Qwen3.5-0.8B-Artemis-GGUF:Q4_K_M.
- Shared local endpoint: http://127.0.0.1:11434/v1/chat/completions.
- Model-repository licence: Apache-2.0.

The Q4 variant is selected for the first Next3D baseline because its publisher reports 173/258 correct on BFCL live_simple, compared with 163/258 for its Q5_K_M variant. It is also about 37 MB smaller. The publisher's measurements are external, vendor-reported results on general tool calls, not independent CAD/BIM tests. Q4 has not yet passed NextAI's native engineering benchmark.

## Why this is a starting model, not the finished intelligence

A 0.8B model is small. Fine-tuning can make it better at application routing, CAD/BIM language, unit-aware specifications, structured native tool calls, clarification and common engineering workflows. It cannot make the model equivalent to a much larger general reasoning model or supply missing application functionality.

NextAI must combine:
1. one shared local multimodal model;
2. separate NextCAD and Next BIM native tool adapters;
3. local, versioned CAD/BIM/engineering knowledge retrieval;
4. deterministic application validators and save/reopen tests;
5. a verified training corpus of successful native operations.

For visual input, the model reads supported drawings/images; it does not generate raster images. It should create native editable geometry and drawings through FreeCAD/BIMCraft commands. The image projector is required for vision, and real drawing prompts still need runtime validation.

## Training decision

Start from the instruction-tuned `Qwen/Qwen3.5-0.8B` checkpoint for supervised fine-tuning, not the pretraining-only Base checkpoint. Use the separate GPU training environment in `training/nextai`: BF16 when supported, FP16 otherwise, with rank-16 LoRA adapted on both the vision and language pathways as configured in `train_nextai.py`. This is a multimodal training recipe, not a claim that every vision capability is already learned.

Include image examples only when the associated labels have reliable ground truth (for example, known vector geometry, dimensions, scale, units, feature identity or verified model state). Never infer exact dimensions from an unscaled screenshot. When image-grounded labels are unavailable, keep those examples text-only; do not count text-only SFT as evidence of improved drawing comprehension. Preserve the unmodified base checkpoint, save the adapter and training configuration, and benchmark the trained candidate against the untouched checkpoint on the same held-out test split.

Train on verified native project traces, not manuals alone:
- a human request and confirmed unit-aware specification;
- the native before/after file state;
- exact typed commands and arguments;
- successful geometry/model checks;
- recompute, transaction and save/close/reopen evidence;
- licence, consent, source lineage and privacy metadata.

Zero-to-CAD sequences are CadQuery, not FreeCAD commands. They can seed examples only after translation and successful execution in the pinned FreeCAD engine. BIM training must use BIMCraft-native actions and IFC/model verification. Public manuals and standards should normally be retrieved with source/version/citation metadata; copyrighted standards must not be copied wholesale into weights without a clear licence.

## Size gate

The entire Next3D product target remains at most 1.2 GB, including both full native applications, shared AI runtime, one shared model, projector, adapters and knowledge packs. The model and projector alone currently account for about 737.4 MB. That leaves roughly 462.6 MB for everything else if the 1.2 GB figure is decimal. This is a hard packaging challenge, not an assertion that the current build fits.

Measure compressed download and installed size separately for Windows, macOS and Linux. Do not strip FreeCAD workbenches, BIMCraft commands, native formats or engineering capabilities to reach the limit. If a full platform package cannot meet the cap, report the measured shortfall instead of hiding it.
