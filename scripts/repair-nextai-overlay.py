#!/usr/bin/env python3
"""Recover one missing Base64 character in the committed NextAI overlay.

The repair is fail-closed: strict base64 decoding and gzip CRC/size validation
must produce exactly one patch containing the expected NextAI files.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
from pathlib import Path
import string
import sys
import zlib

ALPHABET = string.ascii_letters + string.digits + "+/"


def decode_patch(encoded: str) -> bytes | None:
    try:
        compressed = base64.b64decode(encoded, validate=True)
        patch = gzip.decompress(compressed)
    except (ValueError, OSError, EOFError, zlib.error):
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
    chunks = [p.read_text(encoding="ascii").strip() for p in parts]
    patch = decode_patch("".join(chunks))

    if patch is None:
        # The joined source is one data character short. Try the two chunks
        # whose stored lengths differ from the 6,000-character split, then the
        # final chunk. Never accept an ambiguous or CRC-invalid reconstruction.
        matches: list[tuple[int, int, str, bytes]] = []
        for chunk_index in (1, 5, 6):
            chunk = chunks[chunk_index]
            padding = len(chunk) - len(chunk.rstrip("="))
            if padding and chunk_index != 6:
                continue
            for position in range(len(chunk) - padding + 1):
                for char in ALPHABET:
                    repaired = chunk[:position] + char + chunk[position:]
                    candidate_chunks = list(chunks)
                    candidate_chunks[chunk_index] = repaired
                    candidate = decode_patch("".join(candidate_chunks))
                    if candidate is not None:
                        matches.append((chunk_index, position, repaired, candidate))
                        if len(matches) > 1:
                            raise SystemExit("Overlay recovery is ambiguous; refusing to apply it")
        if len(matches) != 1:
            raise SystemExit(
                "Could not uniquely recover the NextAI overlay from parts 02, 06 or 07; "
                "refusing to apply unverified data"
            )
        chunk_index, position, repaired_chunk, patch = matches[0]
        print(
            f"OVERLAY_RECOVERY_PASS: inserted one Base64 character into "
            f"part-{chunk_index + 1:02d} at offset {position}"
        )
        print(f"REPAIRED_PART_{chunk_index + 1:02d}_BASE64=" + repaired_chunk)
        if args.repair_in_place:
            parts[chunk_index].write_text(repaired_chunk + "\n", encoding="ascii")
    else:
        print("OVERLAY_INTEGRITY_PASS: stored Base64 and gzip are valid")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patch)
    digest = hashlib.sha256(patch).hexdigest()
    print(f"OVERLAY_DECODE_PASS: {len(patch)} patch bytes; sha256={digest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"OVERLAY_RECOVERY_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
