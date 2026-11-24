# NextAI package-size strategy

## Current F16 baseline

The current runtime manifest selects one Qwen3.5-0.8B Q4_K_M student:
- Student weights: 532,402,496 bytes.
- Vision projector: 204,986,976 bytes in F16.
- Combined model assets: 737,389,472 bytes (about 737.4 MB decimal).

This is already a difficult fit under the 1.2 GB whole-product cap. The applications, shared runtime, adapters, local knowledge pack and packaging metadata must also fit. The size is not considered achieved until every release build is measured.

## Q8_0 projector experiment

llama.cpp supports converting multimodal projectors as a separate GGUF file and documents Q8_0 as a suitable high-quality option for multimodal components. The initial experiment is to keep the student weights at Q4_K_M and convert only the matching projector from F16 to Q8_0.

Expected direction, not a measured result: Q8_0 should reduce the projector file to around half of F16. The exact Qwen3.5-0.8B result must be measured from the trained model revision. The estimated combined asset size would then be around 635 MB, but this estimate is not a release-size claim.

Run after training and merging the student checkpoint:

    packaging/nextai/quantize-mmproj-q8.sh /path/to/merged-model /path/to/llama.cpp /path/to/nextai-q8

The script records the actual byte size and SHA-256. Keep the original F16 projector.

## Quality and compatibility gates

Do not use the Q8_0 projector in the released package until all of these pass:

1. The matching Q4 student GGUF and Q8_0 projector load together in the exact local runtime used by Next3D.
2. The actual OpenAI-compatible local endpoint accepts image input without a network fallback.
3. The same held-out drawing/image benchmark runs with F16 and Q8_0 projectors.
4. Compare CAD view recognition, drawing interpretation, feature-family recognition and structured output. Set a non-inferiority threshold before testing.
5. Verify RAM use and response latency on the lowest supported target device.
6. Record exact model/projector hashes, runtime version and results in the release manifest.

If Q8_0 causes a material vision-quality regression, retain F16 and seek savings elsewhere. Do not remove FreeCAD workbenches, BIMCraft commands, native formats, or model features to force a green size number.

## Runtime import

llama.cpp supports a separate projector file alongside a GGUF model and its OpenAI-compatible server supports image inputs. The Ollama import path for a custom multi-file vision model must be tested with the exact version and model repository layout; a successful text-only model import is not proof of multimodal support.

## Measurement report

The release pipeline must report independently:
- main Q4 student GGUF bytes;
- F16 baseline projector bytes;
- Q8_0 candidate projector bytes;
- shared inference runtime bytes;
- NextCAD application bytes;
- Next BIM application bytes;
- adapters and local knowledge bytes;
- compressed download size;
- installed footprint after installation.

The model and projector are shared once across both applications, not duplicated.
