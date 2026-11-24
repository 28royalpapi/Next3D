# NextAI local model selection

## Selected footprint candidate

NextAI uses one shared local model for NextCAD and Next BIM:

- Base model: `Qwen/Qwen3.5-0.8B` (873.4 million parameters, Apache-2.0)
- GGUF repository: `axteam/Qwen3.5-0.8B-GGUF`
- File: `Qwen3.5-0.8B-Q4_K_M.gguf`
- Observed Hub file size: 541,903,360 bytes
- Ollama model identifier: `hf.co/axteam/Qwen3.5-0.8B-GGUF:Q4_K_M`
- Shared local OpenAI-compatible endpoint: `http://127.0.0.1:11434/v1/chat/completions`

MiniCPM5-1B Q4_K_M is retained as a comparison candidate at 688,065,920 bytes. It is not the selected package model because the Qwen file leaves roughly 146 MB more room for the complete native applications and the shared runtime.

## Important limitations

The selected GGUF is a third-party quantized conversion of the Qwen base model. Its README says the GGUF is text-only and contains no vision projector. Do not claim direct image understanding from this model. NextAI can still inspect supported native documents through each application's own parsers and expose the resulting object, geometry, BIM, and command data to the model.

The GGUF publisher reports that Ollama use was not tested by the publisher. Therefore the Ollama pull, server start, chat response, and structured-plan call must be runtime-tested before release. The base model card positions the 0.8B model for prototyping, task-specific fine-tuning and research/development. It is not, by itself, evidence of professional engineering-grade reasoning. The release gate is the Next3D CAD/BIM evaluation suite, not the parameter count or a generic benchmark.

## Packaging rule

The model file is shared once; it must never be duplicated inside the NextCAD and Next BIM installers. The model, one inference runtime, retrieval index, native application binaries and shared adapters all count toward the same 1.2 GB package/installed-size limit. Report compressed download size and installed size separately for Windows, macOS and Linux. Do not mark the limit as met until each release artifact has a measured size report.

No native FreeCAD or BIMCraft capability may be removed to meet the package limit. If a platform cannot meet the limit while retaining the full applications, report that failure rather than silently omitting workbenches, modules or formats.
