#!/usr/bin/env python3
"""Apply NextCAD's product-facing application name without changing FreeCAD APIs."""
from pathlib import Path
import sys


def replace_once(path: Path, old: bytes, new: bytes) -> None:
    data = path.read_bytes()
    old_count = data.count(old)
    new_count = data.count(new)
    if old_count == 1:
        path.write_bytes(data.replace(old, new, 1))
    elif old_count == 0 and new_count == 1:
        return  # Idempotent when the source patch has already been applied.
    else:
        raise SystemExit(
            f"Unexpected branding state in {path}: old={old_count}, new={new_count}, token={old!r}"
        )


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply-nextcad-branding.py <FreeCAD source root>")
    source = Path(sys.argv[1])
    main_gui = source / "src/Main/MainGui.cpp"
    replace_once(
        main_gui,
        b'App::Application::Config()["ExeName"] = "FreeCAD";',
        b'App::Application::Config()["ExeName"] = "NextCAD";',
    )
    replace_once(
        main_gui,
        b'App::Application::Config()["ExeVendor"] = "FreeCAD";',
        b'App::Application::Config()["ExeVendor"] = "Next 3D";',
    )


if __name__ == "__main__":
    main()
