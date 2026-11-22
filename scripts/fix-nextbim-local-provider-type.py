#!/usr/bin/env python3
"""Make both BIMCraft attachment-disclosure branches return the same owned String."""
from pathlib import Path
import sys

OLD = 't("Attached files go only to the local Ollama service on this computer.")'
NEW = OLD + ".to_owned()"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fix-nextbim-local-provider-type.py <BIMCraft source root>")
    path = Path(sys.argv[1]) / "crates/ui-egui/src/assistant.rs"
    if not path.is_file():
        raise SystemExit(f"Next BIM assistant UI source not found: {path}")

    source = path.read_text(encoding="utf-8")
    old_count = source.count(OLD)
    new_count = source.count(NEW)
    if new_count == 1 and old_count == 1:
        # NEW contains OLD as a prefix, so this is the expected idempotent state.
        print("Next BIM local-provider disclosure type check already applied.")
        return 0
    if old_count != 1:
        raise SystemExit(
            "Expected exactly one local Ollama disclosure in assistant.rs; "
            f"found {old_count}. Refusing to modify an unexpected source revision."
        )

    source = source.replace(OLD, NEW, 1)
    path.write_text(source, encoding="utf-8")
    if source.count(NEW) != 1:
        raise SystemExit("Failed to apply the Next BIM local-provider String type correction.")
    print("Applied Next BIM local-provider disclosure String type correction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
