#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: quantize-mmproj-q8.sh <merged-model-directory> <llama.cpp-directory> <output-directory>" >&2
  exit 2
fi

MODEL_DIR="$(cd "$1" && pwd)"
LLAMA_CPP_DIR="$(cd "$2" && pwd)"
OUTPUT_DIR="$3"
CONVERTER="$LLAMA_CPP_DIR/convert_hf_to_gguf.py"

if [[ ! -f "$CONVERTER" ]]; then
  echo "Missing llama.cpp multimodal converter: $CONVERTER" >&2
  exit 3
fi
if [[ ! -f "$MODEL_DIR/config.json" ]]; then
  echo "Merged model directory must contain config.json: $MODEL_DIR" >&2
  exit 4
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/mmproj-Q8_0.gguf"

python3 "$CONVERTER" \
  --mmproj \
  --outfile "$OUTPUT_FILE" \
  --outtype q8_0 \
  "$MODEL_DIR"

if [[ ! -s "$OUTPUT_FILE" ]]; then
  echo "Q8_0 projector conversion did not produce a non-empty file." >&2
  exit 5
fi

SIZE_BYTES="$(wc -c < "$OUTPUT_FILE" | tr -d ' ')"
SHA256="$(sha256sum "$OUTPUT_FILE" | awk '{print $1}')"
printf 'Q8_0 projector created: %s\n' "$OUTPUT_FILE"
printf 'Size bytes: %s\nSHA256: %s\n' "$SIZE_BYTES" "$SHA256"
printf '%s\n' "$SIZE_BYTES" > "$OUTPUT_DIR/mmproj-Q8_0.size-bytes"
printf '%s\n' "$SHA256" > "$OUTPUT_DIR/mmproj-Q8_0.sha256"
