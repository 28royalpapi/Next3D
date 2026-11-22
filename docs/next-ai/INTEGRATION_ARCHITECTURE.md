# Next AI — Integration architecture and implementation decisions

## 1. Product boundary

Next AI is a user-facing assistant that works inside two independent applications. It is not a replacement modelling engine and does not create a third common project format.

- NextCAD keeps FreeCAD's document model, Python API, workbenches, feature history and FCStd project format.
- Next BIM keeps BIMCraft's project model, Rust command engine, native BIMC format and IFC workflows.
- A shared agent protocol coordinates planning, local inference, retrieval, permissions, progress and evaluation. Each product has a separate native adapter and capability registry.

## 2. Architecture

```text
                         User request / reference drawing
                                       |
                                       v
                              Next AI workspace
                                       |
                                       v
                       Shared orchestration protocol
                    clarify -> inspect -> plan -> approve
                          -> execute -> verify -> report
                                       |
                  +--------------------+---------------------+
                  |                                          |
                  v                                          v
          NextCAD native adapter                      Next BIM native adapter
          FreeCAD document APIs                       BIMCraft Session/bridge
          typed workbench tools                       typed command registry
          FCStd feature history                        BIMC model / IFC
                  |                                          |
                  +--------------------+---------------------+
                                       |
                                       v
                         Native engine validation
                 recompute / model check / solver / quantities
                                       |
                                       v
                         Save, reopen and report evidence

            Shared local services (user-controlled, on device)
             local language model + optional local vision model
             versioned knowledge retrieval and tool-schema index
             dataset/evaluation harness and local model registry
```

The diagram is a target architecture, not a claim that these components are already implemented.

## 3. Next BIM integration — extend the existing Assistant

The pinned BIMCraft application already contains the in-app Assistant, chat palette, conversation state, tool-call loop and command bridge. Do not build a second assistant panel inside Next BIM.

### Existing foundation

- Provider enum and completion path are in `upstream/BIMCraft/crates/assistant/src/lib.rs`.
- Network boundary and request allow-list are in `upstream/BIMCraft/crates/assistant/src/net.rs`.
- Native assistant tools are in `upstream/BIMCraft/crates/assistant/src/tools.rs`.
- The chat/settings UI is in `upstream/BIMCraft/crates/ui-egui/src/assistant.rs`.
- Design and disclosure behaviour are documented in `upstream/BIMCraft/docs/areas/assistant.md`.

The assistant's native `execute` tool calls a registered BIMCraft command with typed JSON parameters. One turn is run through the shared command bridge and merged into one undo step. This is a sound foundation.

### Local provider — initial source patch prepared

The first Next3D implementation patch is in `patches/nextbim-local-provider.patch.gz.b64`. It adds a keyless OpenAI-compatible Ollama Chat Completions client at the fixed loopback endpoint `http://127.0.0.1:11434/v1/chat/completions`, keeps the remote HTTPS allow-list separate, and blocks local mode in Co-Work sessions. Tests cover request shape, tool-call parsing, local privacy/UI behaviour and a native tool-call-to-undo round trip. These checks are source-level test additions until the CI Rust tests and an actual Ollama runtime test pass.

### Remaining local provider checks

Keep a separate provider choice named **Local model** with:
- a loopback endpoint and model name;
- no required API key;
- an explicit connection test and model/tool-call capability test;
- visible model/runtime status (not installed, stopped, ready, error);
- no remote fallback;
- a clear status saying project context stays on this device.

Do not globally relax the existing remote provider protections. The current BIMCraft network path is HTTPS-only and accepts only its named provider hosts. The local-provider path should be a separate, narrow route that accepts HTTP only for loopback addresses such as 127.0.0.1 or ::1. If a user deliberately selects a non-loopback local-network endpoint in a later version, require a separate security warning and confirmation.

### Required privacy and execution behaviour

- For local mode, the first-send notice must say the prompt, reference files and selected project context go to the local model process on this computer only.
- For remote providers, retain an explicit notice and agreement that the selected provider receives the prompt and project context.
- Never silently switch between local and remote providers after an error.
- Continue to use registered BIMCraft commands and its native model checks; do not add shell or arbitrary Rust/Python execution to the model tool list.
- Keep an undo step for each assistant turn; cancellation and failed commands must not leave partial geometry behind.
- Read-only inspection should remain available separately from write tools.
- High-impact or engineering-sensitive changes must be shown in a plan and approved before execution.

## 4. NextCAD integration — use typed tool-registry patterns, not arbitrary code

The FreeCAD-AI-Assistant reference offers a useful design:
- one registry shared by the chat UI, CLI/console and MCP;
- JSON Schema tool descriptions;
- profiles to limit tool context by discipline;
- GUI-thread dispatch and document transactions;
- an OpenAI-compatible provider that can connect to Ollama without a key.

It is not safe to install unchanged. The reference includes `execute_code` and `execute_code_async`, which call Python `exec` with FreeCAD, GUI, Part and Sketcher in the live application process. Its normal permission profile does not pre-approve arbitrary code, but the code-execution capability exists and a dangerous skip-permissions option exists too.

### Required NextCAD adapter

Build or adapt a typed registry for:
- document and object inspection;
- Sketcher geometry and constraints;
- Part / PartDesign feature operations;
- assembly operations;
- Draft and TechDraw views/dimensions/sheets;
- BIM objects and IFC;
- FEM and CAM only when required dependencies are present;
- file import/export and model validation.

At runtime, enumerate loaded workbenches, commands, formats and optional dependencies. A capability should not be advertised merely because its directory exists in source.

**Default release mode must not expose unrestricted Python or shell execution as an AI tool.** If advanced scripting is introduced later, isolate it from the main application process, use a restricted temporary environment, require explicit user approval and validate every file/model mutation before importing it back. A plain Python `exec` in the live CAD process is not a sandbox.

## 5. Shared tool and action contract

The shared action-plan schema is committed at:

- [Next AI action-plan schema v1](../../schemas/next-ai-action-plan.v1.schema.json)

Before a multi-step mutation, the model produces:
- the application and exact app version;
- the target document identity and state hash;
- assumptions and unresolved questions;
- ordered native tool names and schema versions;
- typed arguments;
- each step's risk, preconditions, expected postconditions and undo behaviour;
- the validation checks that must pass.

Execution is blocked until critical questions are answered and any required approval is given. Tool arguments must validate against the selected application's actual versioned tool schema. The plan is not itself a command and cannot bypass native permissions.

### Risk tiers

| Tier | Examples | Rule |
| --- | --- | --- |
| Read-only | inspect model, list objects, read properties, measure existing geometry | Can run without mutation approval |
| Reversible change | create/edit sketch, add dimension, move an object, change a family/type | Show plan for multi-step edits; use native undo transaction |
| Project change | delete many objects, replace model, bulk convert, overwrite/save-as | Explicit confirmation before execution; never overwrite by default |
| External effect | export to external folder, send to remote provider, invoke external solver/postprocessor | Show destination/provider/tool and get explicit approval |
| Engineering analysis | FEM, structural reinforcement, circuit sizing, compliance-related checks | Require all necessary assumptions/inputs; label the result as analysis, not professional certification |

## 6. Local model strategy

The first implementation should be **local inference + typed tools + retrieval**, not training a foundation model from scratch.

1. Support an OpenAI-compatible local endpoint first so existing local runtimes can be tested without cloud API keys.
2. Benchmark local language models on the actual CAD/BIM tool-call tasks and tool schema sizes.
3. Add a local vision model or multimodal model only after drawing/reference-image tasks have a test set and the hardware cost is understood.
4. Package a tested inference runtime and quantised weights as an optional offline model pack. Do not bundle a multi-gigabyte model into every base application installer.
5. Publish separate CPU/GPU requirements and tested model profiles. A model that runs on a workstation may not be usable on an entry-level laptop.

Remote providers can remain optional, but offline operation must not depend on them, and local mode must not fall back to the network.

## 7. Knowledge and retrieval

Knowledge should be versioned by application and runtime capability:
- native manual and workbench documentation;
- API reference and command descriptions;
- tool argument schemas and examples;
- supported file formats and interchange caveats;
- project-specific parameters, units and object relationships;
- verified synthetic examples and benchmark tasks;
- standards or code references only when there is a clearly recorded source and jurisdiction.

A task should retrieve only the relevant knowledge profile. A plumbing task should not receive the entire FEM manual and all CAM tools. The model must be told whether a capability is native, optional, experimental, unsupported or unavailable on this installation.

## 8. Implementation order

1. Complete and pass the NextCAD / Next BIM native build, test, launch and save/reopen gates.
2. In a separate audit branch, run the FreeCAD-AI-Assistant tests against the pinned NextCAD build and document every tool, permission path and dependency.
3. Add a read-only-only NextCAD prototype first: document inspection, object listing, constraints, measurements and capability discovery.
4. Add the local provider and typed write tools after read-only tests pass.
5. Extend BIMCraft's existing Assistant with a loopback-only local provider, clear local/remote consent and read-only mode.
6. Introduce the shared plan and training-record schemas into both adapters.
7. Build the held-out benchmark and synthetic native examples.
8. Only then compare local base models and decide whether a fine-tune is justified.

## 9. Release gates

Next AI is not ready for users until:
- it cannot execute arbitrary model-generated Python or shell commands in standard mode;
- every write uses the native engine and is undoable or explicitly classified as non-undoable;
- tool arguments and app versions are validated;
- local mode demonstrably makes no remote requests;
- a failed tool call leaves the project unchanged or restores it;
- generated models pass the actual native geometry/model checks;
- save/close/reopen preserves the model;
- offline performance is measured on supported hardware;
- the held-out benchmark proves the model improves over a plain base model with no unverified training leakage.
