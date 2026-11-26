#!/usr/bin/env python3
"""Brand BIMCraft's native Assistant as Next AI without changing its default layout.

The native Assistant remains on-demand, preserving BIMCraft's established
workspace and saved-project behaviour. Only user-facing palette naming and
legacy palette-name compatibility are changed.
"""
from __future__ import annotations

from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    source = path.read_text(encoding="utf-8")
    if new in source:
        return
    count = source.count(old)
    if count != 1:
        raise SystemExit(
            f"{description}: expected one source match, found {count}; "
            f"refusing to patch {path}"
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply-nextbim-assistant-workspace.py <BIMCraft source root>")
    root = Path(sys.argv[1]).resolve()
    dock = root / "crates/ui-egui/src/dock.rs"

    replace_once(
        dock,
        '            Palette::Assistant => msg!("Assistant"),',
        '            Palette::Assistant => msg!("Next AI"),',
        "Next AI palette label",
    )
    replace_once(
        dock,
        '        Palette::ALL.into_iter().find(|p| p.name() == name)',
        '        if name == "Assistant" {\n'
        '            return Some(Palette::Assistant);\n'
        '        }\n'
        '        Palette::ALL.into_iter().find(|p| p.name() == name)',
        "Legacy palette-name compatibility",
    )

    print(
        "NEXT BIM WORKSPACE PASS: native Assistant is labelled Next AI, "
        "remains on-demand, and legacy saved palette names remain readable."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
