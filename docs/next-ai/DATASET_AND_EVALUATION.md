# Next AI — Dataset, training and evaluation plan

## 1. Two different meanings of “parameters”

There are two distinct things:

- **Engineering parameters** are the real design values: a wall thickness, beam span, pipe diameter, voltage, load, hole spacing, floor elevation or sketch constraint.
- **LLM parameters** are the learned weights inside the language/vision model.

The engineering values must be named, unit-aware and tied to native object properties. The model weights are learned from examples and are chosen/tuned separately. A larger set of pictures is not automatically a better engineering dataset.

## 2. The key rule: never keep an unpaired picture

A finished image can show the appearance of a building or component, but it does not necessarily contain:
- exact dimensions, datum and units;
- the sketch geometry and its constraints;
- the editable feature tree and construction sequence;
- the relation between hosts, openings, levels and components;
- material, structural or MEP properties;
- the native model checks, solver state or quantity calculations.

Therefore, **an image-only example is not a complete Next AI training record**. The image must be connected to the exact native project revision that generated it, together with the relevant specification, native commands and validation.

The initial record schema is committed here:

- [Next AI training record schema v1](../../schemas/next-ai-training-record.v1.schema.json)

The schema includes the application (nextcad or nextbim), request, discipline, named parameters, native project states, operations, validation checks, generated views, source licence/permission, privacy, and dataset split. It deliberately does not store hidden model chain-of-thought.

## 3. What one accepted training example contains

A single example should be a reproducible package with:

1. **Request:** the human prompt, language, task and discipline.
2. **Reference material:** drawing images/PDF/vector views and source provenance.
3. **Specification:** named parameters, units, tolerances, constraints, confirmed assumptions and any unresolved question.
4. **Before state:** the native FCStd or BIMC project and an application-readable state summary.
5. **Operation trace:** exact tool/command names, schema versions, arguments, results and undo transaction identity.
6. **After state:** the native saved project, feature history/object graph and source hash.
7. **Validation:** engine checks, geometric measurements, constraint solver state, model checks, quantity comparisons and round-trip results.
8. **Views:** the plan, elevations, sections, isometric/rendered view and exported documents generated from that exact after-state.
9. **Provenance and privacy:** where the example came from, licence, permission state, user consent, redaction and a withdrawal key.
10. **Split:** train, validation, test or quarantine.

The native project is the ground truth. The generated drawing/image is a view of that ground truth, not its replacement.

## 4. Where the data should come from

### A. Native synthetic data — first priority

Create controlled examples directly inside NextCAD and Next BIM:
- start from known templates and empty projects;
- use named, parameterised specifications;
- execute deterministic native commands;
- save the native project;
- perturb important parameters and recompute;
- generate plan/section/elevation/isometric outputs;
- admit the example only when its native checks pass.

This provides examples whose geometry, feature history and validation are known. Synthetic data can produce many controlled variants without scraping or copying another creator's design.

### B. User-owned projects

A user may explicitly contribute their own native project, drawings and approved model history. Keep project identity and personal information out of the learning package unless the user explicitly asks otherwise. A private project does not become public training data by being opened in Next 3D.

### C. Third-party public or contributed data

Before accepting any public CAD/BIM model, drawing, image or tutorial, record and review its licence and terms. Publicly viewable does not automatically mean permission to redistribute or train on it. Respect creator permission, attribution, withdrawal requests and dataset-specific usage conditions. Examples with denied or unresolved permission go to quarantine, not training.

### D. Tutorials and demonstrations

Tutorials may help explain design intent, but a video transcript alone is not ground truth. Align the narration with the actual feature/command sequence and its resulting model, and only use the material under an appropriate licence or permission.

## 5. Separate knowledge from fine-tuning

Next AI needs several layers; one fine-tuned model cannot safely memorise every manual, workbench and tool version.

| Layer | Purpose |
| --- | --- |
| Local language/vision model | Understand requests, interpret supported visual references, clarify and plan |
| Versioned knowledge retrieval | Find the correct manual/API/workbench rules, command schemas, project conventions and examples for the running app version |
| Native tool adapter | Expose typed operations, inspect current model state and return structured native results |
| Engineering validator | Check actual geometry, constraints, units, model relationships, schedules, IFC and file persistence |
| Evaluation suite | Measure accuracy and repeatability on fixed tasks that are never included in training |

The knowledge pack must be selected by application and version. NextCAD and Next BIM require separate native adapters and separate engineering data schemas even when the chat and orchestration code are shared.

## 6. Training stages

### Stage 0 — baseline, no fine-tuning
Use a capable local model with retrieved versioned documentation and typed native tools. Measure its performance before training anything. This establishes whether problems come from the model, the tool interface, missing context or missing application capability.

### Stage 1 — curated examples
Build a high-quality set of successful and failed tasks. Include simple tasks and multi-step tasks. Keep failures with explicit reasons for internal evaluation and debugging; do not label invalid geometry as a successful target.

### Stage 2 — retrieval and tool selection
Teach the runtime to select the relevant tool profile and knowledge documents for a task. Do not send every CAD/BIM command schema and every manual page to a small model on every turn.

### Stage 3 — small supervised fine-tune
Only after the baseline is measured, consider LoRA/QLoRA fine-tuning on validated command traces, parameter specifications, tool-selection examples and drawing-to-structured-spec pairs. Keep app-specific training/validation/test partitions separate.

### Stage 4 — preference and repair training
Use reviewed examples to teach when to ask a question, when to refuse, when to choose a safer native operation and how to recover from a verified tool failure. A successful example must still be checked by the native engine.

### Stage 5 — offline packaging
Package a local inference runtime and quantised model weights as an optional offline model pack for Windows, Linux and macOS. Do not assume every computer can run the same model at the same speed. Publish tested CPU/GPU memory requirements and per-platform results. The CAD/BIM application should remain usable when the model pack is not installed.

## 7. Initial benchmark before large-scale data collection

Start with a compact, held-out benchmark, then expand based on failure analysis. The benchmark should include at least:

### NextCAD tasks
- create and constrain a dimensioned sketch;
- build a parametric PartDesign solid with a hole and fillet;
- edit a named dimension and prove the dependent feature history recomputes;
- build and constrain a small assembly;
- produce a dimensioned TechDraw page;
- create a simple BIM object/IFC export;
- set up a basic FEM analysis only when the pinned solver dependencies are actually available;
- create a CAM job/toolpath only when the required tools and postprocessor are installed.

### Next BIM tasks
- create a multi-room floor plan with correct levels, hosted doors and windows;
- add a floor, roof, section and sheet with dimensions;
- create a structural frame and reinforcement example;
- create a plumbing layout with slopes and fixture families;
- create an electrical board, circuits and panel schedule;
- create a data/SPDA example within the implemented command boundary;
- export IFC and import it again, recording differences;
- edit a parameter, save, close, reopen and verify the result.

### Scoring

For each task, score:
- whether the AI asked for missing critical information;
- semantic correctness of the structured specification;
- correct native tool selection and arguments;
- dimensional/unit accuracy;
- geometry validity and, for sketches, correct constraint/solver state;
- preserved editability and meaningful native feature history;
- recompute, undo/redo and save/reopen stability;
- correct views, drawings, schedules and IFC mapping;
- honestly reported warnings and unsupported operations.

A visually plausible render does not pass a task if the native model is invalid or not editable. A result that fails a native check must never be recorded as a successful training target.

## 8. Dataset quality controls

- Deduplicate by native project lineage and model-state hashes, not only by image similarity.
- Keep all variants of one source project in the same data split to prevent leakage.
- Keep benchmark/test models out of all training and retrieval corpora.
- Store source licence, permission status and attribution with every record.
- Quarantine records with missing native files, missing provenance, unresolved permissions or failed validation.
- Store large native projects and images in a controlled dataset store; the public Git repository contains schemas, scripts, documentation and small synthetic fixtures—not users' private engineering projects.
- Version every schema, tool definition, application revision and validator. A changed command contract can change what the model has learned.

## 9. Go / no-go gates

| Gate | Required evidence |
| --- | --- |
| Native capability | Capability exists in the pinned app and its native test passes |
| Data record | Native source file, request, operation trace, validation and provenance are all present |
| Geometry / project | The real model passes its application checks and save/reopen test |
| Licence / permission | The source is explicitly allowed for the intended dataset use |
| Baseline | A fixed local model + retrieval + tools has been measured on the held-out benchmark |
| Fine-tuning | The tuned model improves held-out results over the same untuned baseline without increasing unsafe/invalid operations |
| Offline delivery | Each supported OS has a tested local runtime/model package with published hardware requirements |

**The first deliverable is a reliable local assistant with native tools and a measured benchmark. The large training corpus and fine-tuning follow the evidence; they do not come first.**
