#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FREECAD="$ROOT/upstream/FreeCAD"
BIMCRAFT="$ROOT/upstream/BIMCraft"
EXPECTED_FREECAD="00cb280454069966a2fb0a8e7dc184c46e7b38b3"
EXPECTED_BIMCRAFT="a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b"

MODE="both"
if [[ "${1:-}" == "--only" ]]; then
  [[ $# -eq 2 ]] || { echo "Usage: $0 [--only nextcad|nextbim]" >&2; exit 2; }
  MODE="$2"
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--only nextcad|nextbim]" >&2
  exit 2
fi
case "$MODE" in
  both|nextcad|nextbim) ;;
  *) echo "Unknown source preparation mode: $MODE" >&2; exit 2 ;;
esac

require_submodule() {
  local dir="$1"
  local label="$2"
  if [[ ! -d "$dir/.git" && ! -f "$dir/.git" ]]; then
    echo "Missing upstream submodule: $dir ($label)" >&2
    exit 2
  fi
}

if [[ "$MODE" == "both" || "$MODE" == "nextcad" ]]; then
  echo "Preparing pinned NextCAD source only (plus its required nested dependencies)."
  git -C "$ROOT" submodule update --init upstream/FreeCAD
  require_submodule "$FREECAD" "FreeCAD"
  actual_freecad="$(git -C "$FREECAD" rev-parse HEAD)"
  [[ "$actual_freecad" == "$EXPECTED_FREECAD" ]] || {
    echo "Unexpected FreeCAD source revision: $actual_freecad" >&2
    exit 3
  }

  # FreeCAD needs its exact nested dependency gitlinks for a native build.
  git -C "$FREECAD" submodule update --init --recursive

  if ! grep -q 'NextAIWorkspace' "$FREECAD/src/Gui/MainWindow.cpp"; then
    git -C "$FREECAD" apply "$ROOT/patches/nextcad.patch"
  fi
  python3 "$ROOT/scripts/apply-nextcad-branding.py" "$FREECAD"
  # Install NextAI into FreeCAD's native module tree; keep all original workbenches.
  python3 "$ROOT/scripts/install-nextcad-ai.py" "$FREECAD"
fi

if [[ "$MODE" == "both" || "$MODE" == "nextbim" ]]; then
  echo "Preparing pinned Next BIM source only."
  git -C "$ROOT" submodule update --init upstream/BIMCraft
  require_submodule "$BIMCRAFT" "BIMCraft"
  actual_bimcraft="$(git -C "$BIMCRAFT" rev-parse HEAD)"
  [[ "$actual_bimcraft" == "$EXPECTED_BIMCRAFT" ]] || {
    echo "Unexpected BIMCraft source revision: $actual_bimcraft" >&2
    exit 3
  }

  # Preserve BIMCraft's complete native app and brand the executable as Next BIM.
  if ! grep -q 'com.next3d.nextbim' "$BIMCRAFT/apps/bimcraft/src/main.rs"; then
    git -C "$BIMCRAFT" apply --check "$ROOT/patches/nextbim.patch"
    git -C "$BIMCRAFT" apply "$ROOT/patches/nextbim.patch"
  fi
  if grep -q 'with_title("BIMCraft")' "$BIMCRAFT/apps/bimcraft/src/main.rs"; then
    git -C "$BIMCRAFT" apply "$ROOT/patches/nextbim-branding.patch"
  fi

  # Keep the native Assistant on demand; brand it as Next AI without forcing it open.
  python3 "$ROOT/scripts/apply-nextbim-assistant-workspace.py" "$BIMCRAFT"

  # Extend the existing native Assistant with local-only inference; no remote fallback.
  if ! grep -q 'pub mod local;' "$BIMCRAFT/crates/assistant/src/lib.rs"; then
    gzip -dc "$ROOT/patches/nextbim-local-provider.patch.gz" | git -C "$BIMCRAFT" apply -
  fi
  python3 "$ROOT/scripts/fix-nextbim-local-provider-type.py" "$BIMCRAFT"

  # Bundle the same versioned engineering guidance into the native BIMCraft Assistant.
  python3 "$ROOT/scripts/install-nextbim-ai-knowledge.py" "$BIMCRAFT"
fi

if [[ "$MODE" == "both" ]]; then
  # The shared source-preparation gate validates both applications and all contracts.
  python3 -m unittest discover -s "$ROOT/tests/next-ai" -p 'test_*.py' -v
  if [[ -f "$ROOT/packaging/nextai/quantize-mmproj-q8.sh" ]]; then
    bash -n "$ROOT/packaging/nextai/quantize-mmproj-q8.sh"
  fi
  python3 "$ROOT/scripts/verify-source-patches.py" "$FREECAD" "$BIMCRAFT"
else
  echo "FOCUSED SOURCE PREPARATION PASS: $MODE"
fi
