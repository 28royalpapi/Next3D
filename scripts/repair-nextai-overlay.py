#!/usr/bin/env python3
"""Recover one missing Base64 data character in the committed NextAI overlay.

The complete stream is searched, not guessed from chunk lengths. A candidate is
accepted only when strict Base64 decoding, gzip CRC/size validation, and the
expected patch markers all pass. The search aborts on ambiguity.
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
        if compressed[:3] != b"\x1f\x8b\x08":
            return None
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
    encoded = "".join(chunks)
    patch = decode_patch(encoded)
    repaired = None

    if patch is None:
        # Padding belongs at the end and is already present. Search every data
        # insertion point across the joined stream; this also covers a missing
        # character at any chunk boundary.
        if not encoded.endswith("=="):
            raise SystemExit("Invalid overlay padding; refusing to rewrite it")
        data_end = len(encoded) - 2
        matches: list[tuple[int, str, bytes]] = []
        attempts = 0
        for position in range(data_end + 1):
            for char in ALPHABET:
                attempts += 1
                candidate = encoded[:position] + char + encoded[position:]
                decoded = decode_patch(candidate)
                if decoded is not None:
                    matches.append((position, char, decoded))
                    if len(matches) > 1:
                        raise SystemExit("Overlay recovery is ambiguous; refusing to apply it")
            if position and position % 5000 == 0:
                print(f"Overlay search progress: {position}/{data_end} positions", flush=True)
        if len(matches) != 1:
            raise SystemExit(
                f"Could not uniquely recover the NextAI overlay; "
                f"checked {attempts} insertion candidates"
            )
        position, char, patch = matches[0]
        repaired = encoded[:position] + char + encoded[position:]
        print(
            f"OVERLAY_RECOVERY_PASS: inserted one Base64 character at "
            f"joined-stream offset {position} (character {char})"
        )
        print(f"RECOVERED_STREAM_SHA256={hashlib.sha256(repaired.encode('ascii')).hexdigest()}")
        if args.repair_in_place:
            cursor = 0
            target_index = None
            target_offset = None
            for index, chunk in enumerate(chunks):
                if cursor <= position <= cursor + len(chunk):
                    target_index = index
                    target_offset = position - cursor
                    break
                cursor += len(chunk)
            if target_index is None:
                raise SystemExit("Recovered offset could not be mapped to a source chunk")
            fixed_chunk = chunks[target_index][:target_offset] + char + chunks[target_index][target_offset:]
            parts[target_index].write_text(fixed_chunk + "\n", encoding="ascii")
            print(f"REPAIRED_PART_{target_index + 1:02d}_BASE64=" + fixed_chunk)
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
