#!/usr/bin/env python3
"""Replace a full-precision Qwen3.5 vision projector with a verified Q8_0 one."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(gguf_dir: Path) -> list[dict[str, Any]]:
    files = []
    for path in sorted(gguf_dir.rglob("*.gguf")):
        files.append({
            "file": str(path.relative_to(gguf_dir)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
            "kind": "vision_projector" if "mmproj" in path.name.lower() else "language_model",
        })
    if not any(item["kind"] == "language_model" for item in files):
        raise RuntimeError("No main language-model GGUF found; refusing to package projector alone.")
    return files


def install_projector(gguf_dir: Path, q8_projector: Path) -> list[dict[str, Any]]:
    if not q8_projector.is_file() or q8_projector.stat().st_size <= 4:
        raise RuntimeError("Q8_0 projector is missing or empty.")
    with q8_projector.open("rb") as handle:
        if handle.read(4) != b"GGUF":
            raise RuntimeError("Q8_0 projector does not have a GGUF file header.")

    # Do not remove the old projector until the replacement has been verified.
    replacement = gguf_dir / "mmproj-Q8_0.gguf"
    staged = gguf_dir / ".mmproj-Q8_0.gguf.tmp"
    shutil.copy2(q8_projector, staged)
    with staged.open("rb") as handle:
        if handle.read(4) != b"GGUF":
            staged.unlink(missing_ok=True)
            raise RuntimeError("Staged projector failed GGUF header verification.")
    staged.replace(replacement)

    for old in gguf_dir.rglob("*.gguf"):
        if old != replacement and "mmproj" in old.name.lower():
            old.unlink()

    files = inventory(gguf_dir)
    if not any(item["kind"] == "vision_projector" for item in files):
        raise RuntimeError("Projector replacement is absent from the final GGUF inventory.")
    return files


def compact_export(merged_model_dir: Path, llama_cpp_dir: Path, gguf_dir: Path) -> dict[str, Any]:
    merged_model_dir = merged_model_dir.resolve()
    llama_cpp_dir = llama_cpp_dir.resolve()
    gguf_dir = gguf_dir.resolve()
    converter = llama_cpp_dir / "convert_hf_to_gguf.py"
    helper = Path(__file__).resolve().parents[2] / "packaging/nextai/quantize-mmproj-q8.sh"
    if not (merged_model_dir / "config.json").is_file():
        raise FileNotFoundError(f"Merged model config not found: {merged_model_dir / 'config.json'}")
    if not converter.is_file():
        raise FileNotFoundError(f"llama.cpp multimodal converter not found: {converter}")
    if not helper.is_file():
        raise FileNotFoundError(f"Projector quantization helper not found: {helper}")

    # Validate that a main GGUF exists before doing projector conversion.
    inventory(gguf_dir)
    temp_dir = gguf_dir / ".projector-q8-staging"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    subprocess.run(
        ["bash", str(helper), str(merged_model_dir), str(llama_cpp_dir), str(temp_dir)],
        check=True,
    )
    q8 = temp_dir / "mmproj-Q8_0.gguf"
    files = install_projector(gguf_dir, q8)
    shutil.rmtree(temp_dir, ignore_errors=True)

    manifest = {
        "schema_version": 1,
        "student": "Qwen/Qwen3.5-0.8B",
        "language_model_quantization": "Q4_K_M",
        "vision_projector_quantization": "Q8_0",
        "files": files,
        "total_gguf_bytes": sum(item["size_bytes"] for item in files),
        "full_precision_projector_removed_after_verified_replacement": True,
        "teacher_weights_included": False,
        "training_data_included": False,
        "note": "This is the model-artifact size only; it is not the full Next3D installer size.",
    }
    manifest_path = gguf_dir / "compact-export-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result_path = gguf_dir.parent / "training_result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["gguf_files"] = files
        result["gguf_total_bytes"] = manifest["total_gguf_bytes"]
        result["vision_projector_quantization"] = "Q8_0"
        result["compact_export_manifest"] = str(manifest_path)
        result_path.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged-model-dir", required=True, type=Path)
    parser.add_argument("--llama-cpp-dir", required=True, type=Path)
    parser.add_argument("--gguf-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compact_export(args.merged_model_dir, args.llama_cpp_dir, args.gguf_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
