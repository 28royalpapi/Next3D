#!/usr/bin/env python3
"""Make BIMCraft's existing Assistant the permanent Next AI workspace.

This deliberately edits only native UI labels and the saved dock layout. It
does not replace BIMCraft's command engine, data model, Assistant implementation
or project format.
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
    settings = root / "crates/ui-egui/src/settings.rs"

    replace_once(
        dock,
        '            Palette::Assistant => msg!("Assistant"),',
        '            Palette::Assistant => msg!("Next AI"),',
        "Next AI palette label",
    )
    replace_once(
        dock,
        '        Palette::ALL.into_iter().find(|p| p.name() == name)',
        '            if name == "Assistant" { return Some(Palette::Assistant); }\n'
        '            Palette::ALL.into_iter().find(|p| p.name() == name)',
        "Legacy palette-name compatibility",
    )
    replace_once(
        dock,
        '            right: vec![Stack::of(Palette::Properties), Stack::of(Palette::Browser)],',
        '            right: vec![\n'
        '                Stack::of(Palette::Properties),\n'
        '                Stack { tabs: vec![Palette::Browser, Palette::Assistant], active: 1 },\n'
        '            ],',
        "Default Next AI workspace layout",
    )

    old_restore = '''        for p in Palette::ALL {
            // The Assistant opens when the user asks: a file from before it was added leaves it closed.
            if !d.shown(p) && !closed.contains(&p) && p != Palette::Assistant {
                // First on the left: the Tools palette, which a file from before it holds nothing of, stands where it would have.
                d.put(p, Target::Side(Side::Left));
                d.left.rotate_right(1);
            }
        }'''
    new_restore = '''        for p in Palette::ALL {
            if !d.shown(p) && !closed.contains(&p) {
                if p == Palette::Assistant {
                    if let Some(stack) = d.stack_of_mut(Palette::Browser) {
                        stack.tabs.push(Palette::Assistant);
                        stack.active = stack.tabs.len() - 1;
                    } else {
                        d.put(Palette::Assistant, Target::Side(Side::Right));
                    }
                } else {
                    // First on the left: the Tools palette, which a file from before it holds nothing of, stands where it would have.
                    d.put(p, Target::Side(Side::Left));
                    d.left.rotate_right(1);
                }
            }
        }'''
    replace_once(dock, old_restore, new_restore, "Legacy layout migration")

    replace_once(
        settings,
        '            Page::Assistant => msg!("Assistant"),',
        '            Page::Assistant => msg!("Next AI settings"),',
        "Next AI settings label",
    )

    for path in (dock, settings):
        text = path.read_text(encoding="utf-8")
        if "Palette::Assistant => msg!(\"Next AI\")" in text:
            continue
    print("NEXT BIM WORKSPACE PASS: native Assistant is the visible Next AI tab; legacy layouts remain readable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
