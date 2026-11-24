#!/usr/bin/env python3
"""Recover the single truncated character in the committed NextAI overlay.

Recovery is deliberately narrow and fail-closed: first try the source as stored;
if invalid, insert one Base64 alphabet character into the final chunk only. A
candidate is accepted only if strict Base64 decoding and gzip CRC/size checks
succeed and the result is a Git patch containing the expected NextAI adapters.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
from pathlib import Path
import string
import sys

ALPHABET = string.ascii_letters + string.digits + "+/"


def decode_patch(encoded: str) -> bytes | None:
    try:
        compressed = base64.b64decode(encoded, validate=True)
        patch = gzip.decompress(compressed)
    except (ValueError, OSError):
        return None
    if not patch.startswith(b"diff --git "):
        return None
    if b"adapters/nextcad-ai/" not in patch:
        return None
    if b"nextbim-native-assistant-workspace.patch" not in patch:
        return None
    return patch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=Path("patches/nextai-operator-overlay"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/nextai-operator-overlay.patch"))
    parser.add_argument("--repair-in-place", action="store_true")
    args = parser.parse_args()

    parts = sorted(args.folder.glob("part-*.b64"))
    if len(parts) != 7:
        raise SystemExit(f"Expected 7 NextAI overlay chunks, found {len(parts)}")

    chunks = [path.read_text(encoding="ascii").strip() for path in parts]
    encoded = "".join(chunks)
    patch = decode_patch(encoded)
    if patch is None:
        # The committed final chunk is 228 characters. The complete stream is
        # exactly one Base64 data character short; never guess which character.
        final = chunks[-1]
        if not final.endswith("="):
            raise SystemExit("Overlay is invalid and the final chunk has no Base64 padding")
        candidates: list[tuple[int, str, bytes]] = []
        insertion_limit = len(final) - len(final.rstrip("="))
        for position in range(len(final) - insertion_limit + 1):
            for char in ALPHABET:
                repaired = final[:position] + char + final[position:]
                candidate = decode_patch("".join(chunks[:-1]) + repaired)
                if candidate is not None:
                    candidates.append((position, repaired, candidate))
                    if len(candidates) > 1:
                        raise SystemExit("Overlay recovery is ambiguous; refusing to apply it")
        if len(candidates) != 1:
            raise SystemExit(
                "Could not uniquely recover the final NextAI overlay chunk; "
                "refusing to apply unverified data"
            )
        position, repaired_final, patch = candidates[0]
        print(f"OVERLAY_RECOVERY_PASS: inserted one Base64 character in part-07 at offset {position}")
        print("REPAIRED_PART_07_BASE64=" + repaired_final)
        if args.repair_in_place:
            parts[-1].write_text(repaired_final + "\n", encoding="ascii")
    else:
        print("OVERLAY_INTEGRITY_PASS: stored Base64 and gzip are valid")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patch)
    print(f"OVERLAY_DECODE_PASS: {len(patch)} patch bytes; sha256={hashlib.sha256(patch).hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"OVERLAY_RECOVERY_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
