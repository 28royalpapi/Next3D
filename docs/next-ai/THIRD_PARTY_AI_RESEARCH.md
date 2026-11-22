# Next AI — pinned third-party research repositories

These repositories are pinned as separate Git submodules under `research/ai-reference/`. They are **research references**, not installed plugins and not merged into NextCAD, Next BIM or their native engines. Each keeps its own Git history, notices and licence. Before any code is copied or integrated, audit the exact pinned revision, dependencies, security boundaries, supported FreeCAD/BIMCraft version and distribution obligations.

## Pinned references

| Reference path | Repository and pinned commit | Licence at the pinned source | What is worth studying | Decision / risk |
| --- | --- | --- | --- | --- |
| `research/ai-reference/freecad-agent` | [nasdomak/freecad-agent](https://github.com/nasdomak/freecad-agent) `8bde71dc972eb521ff8561082fd68bbe7062a330` | LGPL-2.1-or-later (`LICENSE`) | Local Ollama loop; perceive → plan → act → repair; structured Part commands; clarification; undoable feature transactions; regression tests | Focused MVP (20 structured Part commands in its README), Windows-tested; documented limitations with local small models and unsupported broad workbench coverage. Reuse the loop/testing ideas, not as our full capability layer |
| `research/ai-reference/freecad-ai-assistant` | [iplayfast/FreeCAD-AI-Assistant](https://github.com/iplayfast/FreeCAD-AI-Assistant) `8597761518da0334bc79f8db0ab68fd20a370eab` | LGPL-2.1-or-later | Unified typed tool registry shared by GUI, console and MCP; tool profiles; PartDesign, BIM and FEM tool groups; local OpenAI-compatible provider (including Ollama); runtime discovery and documentation lookup | Strongest initial FreeCAD tool-registry candidate. It also includes arbitrary Python execution in the live FreeCAD process and a local RPC bridge: **do not integrate unchanged**. Audit and disable/restrict raw code execution, network exposure and permissions first |
| `research/ai-reference/freecad-mcp` | [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) `246f608d5de49089aadc41d2d91cfce2ad8a44cd` | MIT | Typed MCP operations, model inspection, strict schemas, Sketcher constraints, solver diagnostics and rollback/verification patterns | Experimental and bounded. Useful for reliable Sketcher automation; not a complete all-workbench assistant |
| `research/ai-reference/chat-cad` | [Vittuu/freecad-chatcad](https://github.com/Vittuu/freecad-chatcad) `49d3cce25f878e08cf3f970e1ab1bca5d4604346` | LGPL-2.1 | Selection-aware chat, viewport images and sketches as input, local provider integration, parameter sheets, undo and rollback | Alpha and Windows-tested by its author. Its README reports that local models in its own tests struggled with multi-feature real parts. Study interaction and visual-input ideas, not as evidence that local models already meet our target |
| `research/ai-reference/kerf` | [wearethefoos/kerf](https://github.com/wearethefoos/kerf) `7ff449c9cf6ecf409d4faba209119646440b92f2` | Apache-2.0 | Clarify → plan → generate → execute → verify → repair loop; parameter/spec and training-example schemas; geometry sidecar; evaluation prompts; dataset provenance/permission fields | Targets Build123d, not FreeCAD or BIMCraft. Reuse the methodology and schema concepts only; its geometry engine must not be brought into either product |

## Verified source-code audit findings

### FreeCAD-AI-Assistant

The pinned project has one typed registry consumed by its agent loop and its RPC/MCP surface. Its provider adapter explicitly supports an OpenAI-compatible endpoint such as Ollama at `http://localhost:11434/v1`, including a keyless local request.

The audit also found:
- The registry contains document, object, PartDesign, BIM, inspection and FEM-related operations.
- The agent chooses a smaller tool profile for a task to avoid flooding a small local model with every schema.
- `execute_code` and `execute_code_async` call Python `exec` in a namespace containing FreeCAD, its GUI, Part and Sketcher. This is real in-process code execution, not a sandbox.
- `execute_code` is included in the assistant's always-selected tool names. The default `freecad` CLI permission profile does **not** pre-approve it, but the implementation has an explicit skip-permissions option. We must inspect every path through the UI and external RPC before reusing the loop.
- Its XML-RPC service defaults to `127.0.0.1:9875` and requires a token in the request path. Do not broaden that listener to the LAN or Internet.

**NextCAD integration rule:** use the schema/registry, GUI-thread dispatch, transaction handling and local OpenAI-compatible provider as design references. Next AI's standard mode must expose typed tools only. Arbitrary Python is not in the normal tool profile, must require a separately enabled advanced mode and explicit per-run permission, and must never be enabled merely because the model requests it.

Pinned audit paths:
- `research/ai-reference/freecad-ai-assistant/freecad/AIAssistant/rpc_server/tools.py`
- `research/ai-reference/freecad-ai-assistant/freecad/AIAssistant/rpc_server/agent.py`
- `research/ai-reference/freecad-ai-assistant/freecad/AIAssistant/rpc_server/tool_handlers.py`
- `research/ai-reference/freecad-ai-assistant/freecad/AIAssistant/rpc_server/settings.py`
- `research/ai-reference/freecad-ai-assistant/freecad/AIAssistant/rpc_server/rpc_server.py`
- `research/ai-reference/freecad-ai-assistant/freecad/AIAssistant/rpc_server/providers/openai_compat.py`

### BIMCraft's existing Assistant

The pinned source already implements the correct high-level shape for Next BIM:
- The assistant has a chat UI, model/provider settings and saved conversation handling.
- Its built-in tools use `execute`, `list_commands`, `inspect_model`, `query_elements` and `todo_write`. The `execute` tool invokes an existing BIMCraft command by its registered id and JSON parameters; it is not an arbitrary shell or Python code tool.
- Operations run through the same command bridge as other agents and the native engine. One assistant turn is grouped into one undo action.
- The core command engine runs model validation after commands. Native model checks must still be supplemented by discipline-specific checks; a structurally valid model is not automatically a code-compliant design.
- The provider enum is currently Anthropic, OpenAI and Gemini. The network client is intentionally HTTPS-only and allows only those named provider hosts.

**Next BIM integration rule:** extend the existing Assistant and tool loop. Add a separate local-provider path that accepts a loopback endpoint (for example an Ollama-compatible local server) without weakening the HTTPS/host checks for remote providers. The settings and first-send consent text must clearly distinguish local-only processing from remote transmission. The provider key must not be required for a local model.

Pinned audit paths:
- `upstream/BIMCraft/crates/assistant/src/lib.rs`
- `upstream/BIMCraft/crates/assistant/src/net.rs`
- `upstream/BIMCraft/crates/assistant/src/tools.rs`
- `upstream/BIMCraft/crates/ui-egui/src/assistant.rs`
- `upstream/BIMCraft/docs/areas/assistant.md`

## Integration rules

1. Keep these repositories in their own submodule directories. Do not copy source files into `upstream/FreeCAD` or `upstream/BIMCraft` without an explicit, reviewed integration patch.
2. Keep source notices and licence files intact when code is later reused. A reference submodule is not a licence to relicense its code.
3. Do not add the separate AGPL-3.0 FreeCADTool/AgentBridge stack to the product code without a deliberate copyleft and dependency decision. It was reviewed as a possible reference but is not included as a pinned submodule.
4. Third-party code is untrusted input. Treat all prompts, attachments, model output and tool arguments as data. The default AI tool layer must be typed and allow-listed, with explicit confirmation for consequential changes.
5. The native build workflow checks out only `upstream/FreeCAD`, `upstream/BIMCraft` and FreeCAD's own exact nested dependencies. It does not download these five research submodules on every build. Developers can fetch the references explicitly with:

```bash
git submodule update --init -- research/ai-reference/freecad-agent
git submodule update --init -- research/ai-reference/freecad-ai-assistant
git submodule update --init -- research/ai-reference/freecad-mcp
git submodule update --init -- research/ai-reference/chat-cad
git submodule update --init -- research/ai-reference/kerf
```

## Initial audit order

1. **FreeCAD-AI-Assistant:** map every tool and schema, identify all code-execution paths, verify the RPC binding/authentication, understand GUI-thread dispatch and transaction boundaries, then run its tests against our exact pinned FreeCAD build.
2. **FreeCAD Agent:** compare its plan/repair loop, perception payload, clarification flow, model limits and undo transaction tests with our own benchmark.
3. **FreeCAD MCP:** compare typed Sketcher operations and solver verification with FreeCAD's native constraint APIs.
4. **Chat CAD:** inspect how selected faces/edges, viewport drawings and reference images are encoded without losing geometric context.
5. **KERF:** adapt its parameter, provenance, training-example and held-out evaluation patterns to two separate native-engine schemas. Do not adopt Build123d as a second geometry engine.

No repository is considered production-ready for Next AI merely because it contains an agent panel or can create a demonstration box.
