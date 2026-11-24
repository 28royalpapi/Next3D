# Next AI — Engineering Specialisation, Vision and Model Training

## 1. Product target

NextAI is not meant to be a general chatbot with a CAD logo. It must become a local engineering operator that can understand a task, inspect the active native application, interpret supplied drawings, retrieve relevant domain knowledge, prepare a safe plan, execute real native commands and verify the resulting project.

The supported domain is intentionally broad:

- CAD: 2D drafting, constrained sketches, parametric parts, assemblies, surfaces, technical drawings, import/export and reverse engineering.
- Architecture/BIM: levels, grids, walls, openings, rooms, floors, roofs, stairs, schedules, views, sheets and IFC.
- Civil and structural engineering: structural framing, concrete/steel components, foundations, reinforcement, load cases and analysis setup where supported.
- MEP and infrastructure: plumbing, drainage, water systems, electrical, fire/protection, data/communications, site and utility modelling where supported.
- Engineering practice: units, tolerances, materials, loads, boundary conditions, calculations, design checks, constructability and documentation.
- Construction: coordinated model deliverables, quantities, revisions, sequencing context and issue reporting.

The product must distinguish modelling support from engineering calculation, design approval and professional certification.

## 2. Selected compact multimodal model candidate

The initial candidate is **Qwen3.5-0.8B Artemis Q5_K_M**:

- Base model: Qwen/Qwen3.5-0.8B (approximately 873 million parameters).
- Quantised weights: turintech/Qwen3.5-0.8B-Artemis-GGUF, Q5_K_M.
- Model download size reported by the publisher: approximately 569 MB.
- Vision projector: mmproj-F16.gguf, approximately 205 MB.
- Runtime model ID: hf.co/turintech/Qwen3.5-0.8B-Artemis-GGUF:Q5_K_M.
- Runtime: local Ollama-compatible endpoint on 127.0.0.1:11434.
- License reported by the model repository: Apache-2.0.

This is a **candidate selected for testing**, not an independently verified NextAI model. The publisher's evaluation reports tool-call results on BFCL tasks but also a weakness on MMLU-Pro. Those are vendor-reported results and must be independently checked on NextCAD and Next BIM tasks.

The previously recorded axteam Q4 file is text-only: its own model card explicitly states that the vision encoder is not included. It is therefore not sufficient for the drawing-understanding requirement. The selected candidate includes a separate vision projector. Its publisher's Ollama instructions require Ollama 0.40.11 or newer and pulling the Hugging Face model identifier above so that the projector is included. Both assets must be installed and verified before NextAI advertises image input.

The two candidate assets total roughly 774 MB of model downloads before the applications, shared runtime, retrieval index and other release files. The 1.2 GB whole-product ceiling remains a hard release gate. Actual installed/download sizes must be measured per operating system; the approximate model-card figures are not a packaging proof.

## 3. Why a small model can be useful — and where it cannot be trusted

Fine-tuning can improve:
- recognition of NextCAD versus Next BIM tasks;
- selection of the correct application-specific tool profile;
- structured parameter extraction and unit handling;
- reliable JSON action-plan generation;
- clarification behaviour when dimensions or engineering inputs are missing;
- common CAD/BIM command sequences;
- recovery from known native tool errors;
- interpretation of common drawing symbols and layouts.

Fine-tuning does not magically add reliable structural/geotechnical expertise, create missing software features, or make an 0.8B model equivalent to a much larger reasoning model. The application tools, knowledge retrieval and deterministic validators must carry much of the exactness. If the 0.8B candidate cannot meet the held-out benchmark, do not hide the failure behind a clever prompt.

## 4. The four-part intelligence system

### A. One shared model

Use one locally hosted Qwen3.5-0.8B candidate for both products. The active application, version and adapter identity are supplied in every task. Do not install separate duplicate model weights for NextCAD and Next BIM.

### B. Separate native adapters

NextCAD must use FreeCAD's native document API, workbenches, tool schemas, feature history and undo transactions.

Next BIM must use BIMCraft's native command registry, session/model state, native project format and native undo/validation path.

A shared chat UI and shared planner do not mean a shared geometry engine. Never send a NextCAD tool call to Next BIM or vice versa.

### C. Versioned local knowledge packs

Retrieve only the material needed for the current task:
- CAD workbench/API documentation;
- BIMCraft command descriptions and model semantics;
- engineering and construction workflow guidance;
- drawing interpretation guidance;
- versioned project examples;
- explicitly licensed standards references and calculation methods.

Keep laws, codes and standards as versioned references with jurisdiction, edition and citations. Do not bake unlicensed standards into model weights or represent a generic explanation as a code check.

### D. Deterministic native tools and validators

The model proposes typed operations. Native tools perform them. Validators then check actual geometry, units, constraints, relationships, calculations, schedules, IFC and persistence. A render is not proof of correctness.

## 5. Fine-tuning plan

Qwen3.5 is supported by current Unsloth fine-tuning guidance for text and vision LoRA. That guidance reports roughly 3 GB VRAM for 0.8B BF16 LoRA and recommends avoiding QLoRA for this model family. Training therefore belongs in a separate controlled training environment; the installed Next3D product must not include the training toolchain.

The proposed sequence is:

1. **Baseline:** test the unmodified Artemis candidate with the existing adapters, knowledge retrieval and a held-out task set.
2. **Collect verified records:** generate examples inside the actual pinned NextCAD and Next BIM applications. Each record must bind the request, optional drawing image, exact native before/after projects, tool arguments, validation results and provenance.
3. **Supervised fine-tune:** use BF16 LoRA on approved examples for task routing, specification extraction, native tool selection, JSON plans, clarification and reporting. Include both positive and negative examples.
4. **Vision tuning:** only after drawing tasks have reviewed ground truth, include paired drawing/image and structured specification examples. Do not train from unscaled pictures with guessed dimensions.
5. **Merge and quantise:** merge the approved LoRA into one model, export a supported GGUF build, and verify the vision projector matches the same model revision. Avoid retaining duplicate base and merged model files in the release.
6. **Held-out comparison:** rerun the exact same benchmark on the base and tuned model. Promote the tuned weights only if CAD/BIM task scores improve without increasing unsafe actions, hallucinated commands or invalid geometry.
7. **Release:** pin the model repository revision, file SHA-256 hashes, tokenizer/chat template, projector hash, runtime version and tested context settings.

A tuned model must be treated as a new artefact with its own measured results. Do not claim improvement simply because fine-tuning completed.

## 6. Training record design

The existing `next-ai-training-record.v1.schema.json` is the minimum record contract. A useful training item should include:

- application and exact upstream revision;
- user request, language, task type and discipline;
- original drawing images/PDF pages and source provenance;
- a structured, unit-aware specification and confirmed assumptions;
- native before-state and after-state (FCStd or BIMC);
- exact typed native command sequence and argument JSON;
- native return values, warnings and undo transaction details;
- validation: recompute, geometry validity, dimensions, constraints, quantities, solver/analysis status and save/reopen;
- generated plans, sections, elevations, technical drawings, schedules and exchange files;
- source licence, permission status, consent, redaction and withdrawal key;
- train/validation/test/quarantine assignment.

One source project and all of its variants must remain in one data split. Never put benchmark/test projects into training or retrieval corpora.

## 7. External research and reuse decisions

### Parametric CAD Bench V3

The public V3 benchmark describes 100 complex FreeCAD tasks: 30 text-to-CAD creation, 30 create-and-edit, and 40 engineering-drawing-to-CAD tasks. Its separate native verifier measures geometry and specification consistency, not just whether a script ran. This is a strong evaluation pattern for NextCAD. Use the public benchmark under its own access and licence conditions; do not copy tasks into training data.

### LLM4CAD-DSL

The public repository describes 107,994 paired CAD construction scripts, STL geometry and multi-view images, with feature operations including revolve, pocket, groove, fillet and chamfer. Its symbolic references are a useful design idea because stable semantic entities are less brittle than guessed face/edge coordinates.

The repository does not clearly expose a training/redistribution licence in the reviewed README and says the data is reconstructed from WHUCAD. Therefore it is a **research reference only** until the upstream dataset licence and permissions are explicitly checked. Do not place it in NextAI training yet. Do not adopt its parser as a second native geometry engine.

### CAD-Coder

The CAD-Coder dataset is described as Apache-2.0 and pairs natural-language descriptions with CadQuery programs and reasoning data. Its CadQuery scripts are not NextCAD native operations. At most, approved records may be used as task-description seeds and translated into NextCAD-native tool traces that are then independently created and verified in FreeCAD. Do not execute third-party generated code inside the live application.

### CADFS-2B

CADFS-2B is a task-specialised Qwen2-VL-2B model for text/image-to-CAD FeatureScript. The model is MIT-licensed according to its public model card, but it is a 2B model and targets Onshape FeatureScript. It is too large for the current whole-product size target and does not directly produce FreeCAD or BIMCraft operations. Study its data-alignment and task-specialisation approach; do not package it as NextAI's runtime.

### BIM research

Recent BIM agent research demonstrates schema-guided and tool-augmented interaction with IFC models, dynamic tool composition, and explicit memory for multi-step BIM queries. Another Revit-oriented BIM coordination study uses separate assistant, checker, sender, executor and terminator roles. These are useful patterns, not proof of universal BIM automation. NextAI should keep these roles as stages in one light orchestration loop, not install several additional large models.

## 8. NextAI benchmark and promotion gate

Create a held-out internal test suite for both products. Include text-only tasks, multi-turn edits and drawing/image tasks.

### NextCAD
- dimensioned constrained sketch;
- PartDesign body with pocket, hole, fillet and parameter edit;
- Draft floor plan with dimensions and annotations;
- parametric wall/opening or building element;
- assembly placement/relationship;
- TechDraw page with dimensions and views;
- supported import/export round-trip;
- FEM/CAM task only when the pinned dependencies and required solvers are present.

### Next BIM
- multi-level architectural plan with hosted doors/windows;
- roof, stair, section, elevation and sheet;
- structural frame and member type changes;
- plumbing layout with levels, slopes and connected fixtures;
- electrical panel/circuit/schedule;
- MEP/data/protection task within implemented native command support;
- quantity schedule and IFC round-trip;
- multi-step edit, undo, save, close and reopen.

### Score every run

Measure:
- correct task/application routing;
- missing-input clarification and assumption discipline;
- drawing facts extracted correctly versus uncertain facts;
- tool selection, argument validity and command success;
- dimension and unit accuracy;
- native model/feature validity and editability;
- constraints, hosts, connections and relationships;
- recompute, undo/redo and save/reopen;
- correct report of limitations and failed checks;
- unsafe or unsupported actions (target: zero).

Promotion requires a measured improvement over the same base model + retrieval + tools baseline. A model that answers more fluently but creates more invalid projects must not be promoted.

## 9. Current implementation boundary

Already present in the repository:
- a separate NextCAD adapter with local-only provider, typed starter tools and native plan approval;
- Next BIM's existing native Assistant integrated as its Next AI workspace, with a local provider patch prepared;
- a 214-command BIMCraft registry catalogue;
- a shared Qwen model manifest;
- compact NextCAD knowledge packs for parametric CAD, BIM/construction, engineering validation and drawing intake;
- a schema for provenance-aware native training records.

Not yet proven:
- successful local multimodal inference with the selected model and projector;
- complete CAD/BIM feature coverage;
- fine-tuning or improved engineering benchmark performance;
- real native application builds and full GUI workflows on every supported OS;
- the 1.2 GB final installed/download size.

No future feature or model result should be marked complete until its native and runtime acceptance checks pass.

## References

- [Qwen3.5-0.8B official model card](https://huggingface.co/Qwen/Qwen3.5-0.8B)
- [TurinTech Qwen3.5-0.8B Artemis GGUF](https://huggingface.co/turintech/Qwen3.5-0.8B-Artemis-GGUF)
- [Qwen3.5 fine-tuning guidance (Unsloth)](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- [Parametric CAD Bench V3](https://dev.cadbench.ai/)
- [LLM4CAD-DSL repository](https://github.com/YuewanSun/LLM4CAD-DSL)
- [CAD-Coder dataset](https://huggingface.co/datasets/gudo7208/CAD-Coder)
- [CADFS-2B model](https://huggingface.co/VladPyatov/CADFS-2B)
- [Schema-guided tool-augmented IFC multi-agent framework (2026)](https://doi.org/10.1016/j.autcon.2026.106888)
- [AI BIM coordinator for non-expert interaction](https://www.sciencedirect.com/science/article/pii/S092658052500603X)
