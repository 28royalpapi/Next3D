# Build and verification status

## Selector

The selector-only GitHub Actions run `44911879342` passed on Ubuntu 24.04, Windows 2025 and macOS 15 Intel. This validates the selector UI and its app-card callbacks only.

## Source provenance and patch preparation

- NextCAD source is pinned to the exact FreeCAD commit represented by the supplied archive. Its five nested git submodules are pinned by that upstream commit and are initialized recursively.
- Next BIM source is pinned to the exact BIMCraft commit represented by the supplied archive.
- The NextCAD and Next BIM patch sets were applied to clean extractions of the supplied original archives and compared with the prepared working trees. Only the intended four source files differ.
- Static source assertions verify both Next AI workspace markers and the NextCAD/Next BIM product identities. These checks are not compilation tests.

## Native app acceptance - pending

The native application workflow builds and tests both applications on Linux, Windows and macOS. Until its jobs finish successfully, the following are **not** claimed:

- successful native compilation on all three operating systems;
- a real NextCAD or Next BIM application launch;
- successful creation/editing/saving/reopening of a CAD or BIM model;
- complete tool-level acceptance of every original workbench and command.

The local execution environment has no Rust/Cargo compiler, Pixi environment or FreeCAD executable, so these native checks cannot be completed locally here.

## Screenshots

The source archives contain genuine upstream documentation images, not screenshots of the modified NextCAD or Next BIM applications. No image is labelled as a Next 3D application screenshot until it is captured from the newly built executable. The Linux native build workflow attempts to upload real GUI screenshots as artifacts after launching each application.

## Current AI curriculum preparation

- The checked-in Next BIM native command catalogue contains **215 registrations** at the pinned BIMCraft revision. Registrations are inventory entries, not proof that all 215 commands are exposed to or mastered by Next AI.
- The CPU-only curriculum workflow completed successfully in Actions run `45831337789`. Its audit reports 25,780 train, 2,730 validation and 1,415 held-out test records across 83 labelled domains, with split-integrity checks passing and the held-out test excluded from gradient updates. The artifact contains the manifest and audit profile, not the full raw training corpus.
- Native NextCAD training examples now include the same reviewed, task-selected typed tool schemas supplied at runtime. Held-out evaluation now supplies those schemas too. These changes are awaiting the native source-preparation CI run.
- No fine-tuned model has been produced or evaluated yet. No Hugging Face paid GPU job has been started. The free-account ZeroGPU allowance is 5 GPU minutes/day; the 25,780-record multimodal fine-tune is not being represented as achievable within that quota. NextCAD live runtime capture is still missing (0 runtime commands and 0 Python API members in the current census), and the 28-case engineering benchmark has not yet been run against a trained student. Native unseen-task execution remains pending.

## Next AI

- NextCAD has a native Next AI workbench adapter with a local-only OpenAI-compatible provider, live workbench/document discovery, a typed starter tool registry, native plan approval, and one-transaction execution. The starter write tools remain limited; full Sketcher, PartDesign, Assembly, TechDraw, advanced BIM, FEM and CAM coverage is not yet complete.
- NextCAD's workspace now accepts local drawing images (up to four per turn), sends them as multimodal data only to the loopback model endpoint, and retains only text in the conversation history. This is source implementation; real inference and image-reading quality are pending.
- NextCAD now retrieves its bundled CAD, BIM/construction, engineering-validation and drawing-intake skill packs together with native FreeCAD manual excerpts.
- The provider now checks the local Ollama version and selected model installation before users rely on image input. The selected model identifier is the Hugging Face Ollama route `hf.co/turintech/Qwen3.5-0.8B-Artemis-GGUF:Q5_K_M`, which requires Ollama 0.40.11 or newer for the publisher's multimodal setup.
- Selected model candidate: Qwen3.5-0.8B Artemis Q5_K_M, approximately 569 MB plus its approximately 205 MB vision projector. These are approximate download sizes; the full package-size acceptance remains pending. The earlier axteam 541,903,360-byte quantisation has been superseded because its model card says it lacks the vision encoder.
- A specialist engineering training and evaluation plan is documented in `docs/next-ai/ENGINEERING_SPECIALIZATION.md`. No fine-tune has been completed yet.
- Next BIM reuses BIMCraft's native Assistant as the default Next AI workspace. The local-provider source patch and 215-command catalogue exist, but the exact Artemis model configuration, multimodal image path, full command-level acceptance and runtime behaviour remain to be completed and tested.
- Neither the selected model nor the CAD/BIM adapters have passed an end-to-end local model test or the native desktop build/launch/save-reopen gates. The 1.2 GB cross-platform package target is not yet proven.



## 2026-11-26 verified pipeline update

- Curriculum audit: Actions run [45831337789](https://github.com/28royalpapi/Next3D/actions/runs/45831337789) passed. Main corpus: 25,780 train / 2,730 validation / 1,415 test; 83 labelled domains; zero cross-split identity conflicts; test excluded from training.
- The census includes 32 NextCAD source modules and 215 Next BIM command registrations. It does **not** contain live NextCAD runtime commands/API members; source presence must not be presented as a complete runtime inventory.
- Native CI: [run 45838757169](https://github.com/28royalpapi/Next3D/actions/runs/45838757169) passed source preparation and is running the six-OS/app matrix. Final compile, launch, real operation, save/reopen and unit-test results remain pending.
- No model has been fine-tuned. No paid HF Job or upgraded Space hardware may be used. The current HF identity has no Hub write-repo scope; checkpoint upload/Space creation requires an authorised write connection.
