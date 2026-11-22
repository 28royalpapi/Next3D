#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FREECAD="$ROOT/upstream/FreeCAD"
BIMCRAFT="$ROOT/upstream/BIMCraft"
EXPECTED_FREECAD="00cb280454069966a2fb0a8e7dc184c46e7b38b3"
EXPECTED_BIMCRAFT="a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"

# Initialize only the two production application sources here. The additional
# AI projects are pinned under research/ai-reference and are checked out by
# developers when they are studying/reusing them, not by the native build jobs.
git -C "$ROOT" submodule update --init upstream/FreeCAD upstream/BIMCraft

for dir in "$FREECAD" "$BIMCRAFT"; do
  if [[ ! -d "$dir/.git" && ! -f "$dir/.git" ]]; then
    echo "Missing upstream submodule: $dir" >&2
    exit 2
  fi
done

actual_freecad="$(git -C "$FREECAD" rev-parse HEAD)"
actual_bimcraft="$(git -C "$BIMCRAFT" rev-parse HEAD)"
[[ "$actual_freecad" == "$EXPECTED_FREECAD" ]] || { echo "Unexpected FreeCAD source revision: $actual_freecad" >&2; exit 3; }
[[ "$actual_bimcraft" == "$EXPECTED_BIMCRAFT" ]] || { echo "Unexpected BIMCraft source revision: $actual_bimcraft" >&2; exit 3; }

# Restore FreeCAD's full nested dependency tree at the exact gitlink revisions
# recorded by the pinned FreeCAD commit.
git -C "$FREECAD" submodule update --init --recursive

if ! grep -q 'NextAIWorkspace' "$FREECAD/src/Gui/MainWindow.cpp"; then
  git -C "$FREECAD" apply "$ROOT/patches/nextcad.patch"
fi
python3 "$ROOT/scripts/apply-nextcad-branding.py" "$FREECAD"

if ! grep -q 'next-ai-workspace' "$BIMCRAFT/crates/ui-egui/src/lib.rs"; then
  git -C "$BIMCRAFT" apply "$ROOT/patches/nextbim.patch"
fi
# Ensure the visible app/viewport branding is Next BIM as well as the executable fallback title.
if grep -q 'with_title("BIMCraft")' "$BIMCRAFT/apps/bimcraft/src/main.rs"; then
  git -C "$BIMCRAFT" apply "$ROOT/patches/nextbim-branding.patch"
fi

# Extend BIMCraft's existing Assistant with local Ollama inference. The patch
# is compressed in the repository to keep the source delta easy to fetch.
if ! grep -q 'pub mod local;' "$BIMCRAFT/crates/assistant/src/lib.rs"; then
  python3 -c 'import base64,gzip,pathlib,sys; sys.stdout.buffer.write(gzip.decompress(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes())))' \
    "$ROOT/patches/nextbim-local-provider.patch.gz.b64" | git -C "$BIMCRAFT" apply -
fi

python3 "$ROOT/scripts/verify-source-patches.py" "$FREECAD" "$BIMCRAFT"
