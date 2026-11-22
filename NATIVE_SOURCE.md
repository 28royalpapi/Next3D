# Native application source layout

Next 3D keeps the original CAD and BIM applications separate. The full upstream trees are attached to this repository as pinned Git submodules so the upstream code, history, licenses and dependency structure are preserved instead of being copied into a disconnected fork.

| Next 3D app | Upstream source | Pinned source revision |
|---|---|---|
| NextCAD | `FreeCAD/FreeCAD` | `00cb280454069966a2fb0a8e7dc184c46e7b38b3` (14 Nov 2026) |
| Next BIM | `IPedrax/BIMCraft` | `a0c57b738e308d433ab4b8c0c93d7fff9e53bc1b` (14 Nov 2026) |

The FreeCAD revision includes the five exact dependency gitlinks for OndselSolver, GSL, AddonManager, Coin and Pivy. A recursive checkout restores those commits; no dependency version is guessed or replaced with the latest branch head.

## Checkout and prepare

```bash
git clone --recurse-submodules --branch nextcad https://github.com/28royalpapi/Next3D.git
cd Next3D
bash scripts/apply-source-patches.sh
```

The preparation script selectively initializes the two production source submodules, checks both pinned revisions, initializes FreeCAD's exact nested dependencies, and applies the product patches. It deliberately does not fetch the separate AI research submodules during native builds. A developer can fetch a specific AI reference with `git submodule update --init -- research/ai-reference/<name>`; the full list and pinned licences are in [THIRD_PARTY_AI_RESEARCH.md](docs/next-ai/THIRD_PARTY_AI_RESEARCH.md).

## Build

NextCAD uses the pinned FreeCAD Pixi/CMake environment:

```bash
cd upstream/FreeCAD
pixi run configure
pixi run build
pixi run test
```

Next BIM uses its pinned Rust workspace:

```bash
cd upstream/BIMCraft
cargo fmt --check
cargo test --workspace
cargo build --release -p bimcraft -p bimcraft-cli
```

The **Native application builds** GitHub Actions workflow runs these checks on Linux, Windows and macOS on both `main` and `nextcad`. It also runs native project round-trip and desktop startup checks. The Linux jobs attempt to launch the real desktop apps and capture screenshots as CI artifacts.

## What the patches change

- NextCAD: product name/vendor and a permanent, non-closable native Qt dock named `Next AI`. The original FreeCAD icon, splash resource, workbenches, document engine and internal Python/API names are retained.
- Next BIM: desktop application identity/title and a permanent right-side egui `Next AI` panel. BIMCraft crate names, document engine and internal compatibility identifiers are retained.
- Neither Next AI panel is connected to an AI service in this phase. The panel is a reserved native workspace only.

The patch changes are intentionally small. No source tree has been rewritten or merged with the other application.
