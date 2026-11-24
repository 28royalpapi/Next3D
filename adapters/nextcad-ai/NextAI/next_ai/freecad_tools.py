"""Read-only discovery and typed native operations for FreeCAD.

No Python console, exec/eval, shell or arbitrary macro execution is exposed.
"""
from __future__ import annotations

import math
import re


def _apps():
    import FreeCAD as App
    import FreeCADGui as Gui
    return App, Gui


def _number(value, name, minimum=-1_000_000.0, maximum=1_000_000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    value = float(value)
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the allowed range.")
    return value


def _point(value, name="point"):
    if not isinstance(value, (list, tuple)) or len(value) not in (2, 3):
        raise ValueError(f"{name} must contain two or three coordinates.")
    coords = [_number(v, f"{name}[{i}]") for i, v in enumerate(value)]
    if len(coords) == 2:
        coords.append(0.0)
    return coords


def _doc_summary(doc):
    objects = []
    for obj in list(doc.Objects)[:100]:
        objects.append(
            {
                "name": str(obj.Name),
                "label": str(obj.Label),
                "type": str(obj.TypeId),
            }
        )
    return {
        "name": str(doc.Name),
        "label": str(doc.Label),
        "file": str(getattr(doc, "FileName", "")),
        "object_count": len(doc.Objects),
        "objects": objects,
        "objects_truncated": len(doc.Objects) > len(objects),
    }


def inspect_document():
    App, _Gui = _apps()
    doc = App.ActiveDocument
    if doc is None:
        return {"open": False, "message": "No document is open in NextCAD."}
    return {"open": True, **_doc_summary(doc)}


def discover_capabilities(query: str = ""):
    """Discover live FreeCAD workbenches and rank native commands for this task."""
    App, Gui = _apps()
    workbenches = Gui.listWorkbenches()
    commands = Gui.listCommands()
    if isinstance(workbenches, dict):
        workbench_ids = sorted(str(key) for key in workbenches.keys())
    else:
        workbench_ids = sorted(str(item) for item in workbenches)
    command_ids = sorted(set(str(item) for item in commands))
    terms = [part.lower() for part in re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}", str(query))]
    if terms:
        ranked = [
            (sum(term in command.lower() for term in terms), command)
            for command in command_ids
        ]
        relevant = [item for item in ranked if item[0] > 0]
        relevant.sort(key=lambda item: (-item[0], item[1]))
        selected_commands = [item[1] for item in relevant[:180]] or command_ids[:120]
    else:
        selected_commands = command_ids[:120]
    return {
        "application": "NextCAD (FreeCAD native engine)",
        "version": str(getattr(App, "Version", lambda: "unknown")()),
        "workbenches": workbench_ids,
        "command_count": len(command_ids),
        "commands": selected_commands,
        "commands_truncated": len(command_ids) > len(selected_commands),
        "native_formats": [
            "FCStd", "STEP", "IGES", "BREP", "STL", "OBJ", "DXF", "SVG", "IFC"
        ],
    }


def begin_turn():
    """Capture the active document identity before model planning begins."""
    App, _Gui = _apps()
    doc = App.ActiveDocument
    if doc is None:
        raise RuntimeError("Open or create a NextCAD document before asking NextAI to modify it.")
    return {
        "document": doc,
        "name": str(doc.Name),
        "file": str(getattr(doc, "FileName", "")),
    }


def _assert_turn(token):
    App, _Gui = _apps()
    doc = token.get("document") if isinstance(token, dict) else None
    if doc is None or App.ActiveDocument is not doc:
        raise RuntimeError("document changed during turn; no planned operations were applied")
    if str(doc.Name) != token.get("name") or str(getattr(doc, "FileName", "")) != token.get("file"):
        raise RuntimeError("document changed during turn; no planned operations were applied")
    return doc


def _create_step(doc, tool, args):
    App, Gui = _apps()
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object.")

    if tool == "create_draft_line":
        import Draft
        start = App.Vector(*_point(args.get("start"), "start"))
        end = App.Vector(*_point(args.get("end"), "end"))
        if (end - start).Length <= 1e-7:
            raise ValueError("A line needs two different points.")
        obj = Draft.make_line(start, end)
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Draft line.")
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_draft_rectangle":
        import Draft
        length = _number(args.get("length"), "length", 0.001, 1_000_000.0)
        width = _number(args.get("width"), "width", 0.001, 1_000_000.0)
        origin = App.Vector(*_point(args.get("origin", [0, 0, 0]), "origin"))
        placement = App.Placement(origin, App.Rotation())
        obj = Draft.make_rectangle(length, width, placement=placement, face=False)
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Draft rectangle.")
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_arch_wall":
        import Draft
        import Arch
        raw_points = args.get("points")
        if not isinstance(raw_points, list) or not 2 <= len(raw_points) <= 200:
            raise ValueError("A wall path needs between 2 and 200 points.")
        points = [App.Vector(*_point(p, "wall point")) for p in raw_points]
        if all((points[0] - point).Length <= 1e-7 for point in points[1:]):
            raise ValueError("The wall path has no length.")
        height = _number(args.get("height", 3000), "height", 100.0, 100_000.0)
        width = _number(args.get("width", 200), "width", 25.0, 5_000.0)
        baseline = Draft.make_wire(points, closed=False)
        wall = Arch.makeWall(
            baseline,
            height=height,
            width=width,
            name=str(args.get("label", "NextAI Wall"))[:120],
        )
        if wall is None:
            raise RuntimeError("FreeCAD did not create the Arch wall.")
        return {"created": wall.Name, "label": wall.Label, "type": wall.TypeId}

    if tool == "create_part_box":
        x = _number(args.get("length"), "length", 0.001, 1_000_000.0)
        y = _number(args.get("width"), "width", 0.001, 1_000_000.0)
        z = _number(args.get("height"), "height", 0.001, 1_000_000.0)
        obj = doc.addObject("Part::Box", "NextAIBox")
        obj.Length, obj.Width, obj.Height = x, y, z
        obj.Placement = App.Placement(
            App.Vector(*_point(args.get("origin", [0, 0, 0]), "origin")),
            App.Rotation(),
        )
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_draft_circle":
        import Draft
        radius = _number(args.get("radius"), "radius", 0.001, 1_000_000.0)
        center = App.Vector(*_point(args.get("center", [0, 0, 0]), "center"))
        placement = App.Placement(center, App.Rotation())
        obj = Draft.make_circle(radius, placement=placement, face=False)
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Draft circle.")
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_draft_text":
        import Draft
        text_value = args.get("text")
        if not isinstance(text_value, str) or not text_value.strip() or len(text_value) > 2000:
            raise ValueError("Text must contain between 1 and 2,000 characters.")
        position = App.Vector(*_point(args.get("position", [0, 0, 0]), "position"))
        height = _number(args.get("height", 250), "height", 1.0, 10_000.0)
        obj = Draft.make_text(text_value.splitlines(), placement=position, height=height)
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Draft text.")
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_arch_structure":
        import Arch
        length = _number(args.get("length"), "length", 25.0, 20_000.0)
        width = _number(args.get("width"), "width", 25.0, 20_000.0)
        height = _number(args.get("height"), "height", 25.0, 100_000.0)
        obj = Arch.makeStructure(length=length, width=width, height=height,
                                 name=str(args.get("label", "NextAI Structure"))[:120])
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Arch structural element.")
        obj.Placement = App.Placement(
            App.Vector(*_point(args.get("origin", [0, 0, 0]), "origin")),
            App.Rotation(),
        )
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "activate_workbench":
        workbench_id = args.get("workbench_id")
        available = discover_capabilities()["workbenches"]
        if not isinstance(workbench_id, str) or workbench_id not in available:
            raise ValueError("That workbench is not registered in this NextCAD installation.")
        Gui.activateWorkbench(workbench_id)
        return {"activated_workbench": workbench_id}

    if tool == "run_native_command":
        command_id = args.get("command_id")
        commands = set(discover_capabilities()["commands"])
        if not isinstance(command_id, str) or command_id not in commands:
            raise ValueError("That native command is not registered in this NextCAD installation.")
        blocked = ("Macro", "Python", "Quit", "Exit", "Open", "CloseAll", "SaveAs")
        if any(part in command_id for part in blocked):
            raise ValueError("This native command is outside NextAI's approved command set.")
        Gui.runCommand(command_id, 0)
        return {"native_command_started": command_id}

    raise ValueError(f"Unknown or unavailable native tool: {tool}")


def execute_plan(token, plan):
    """Execute an approved plan in one FreeCAD undo transaction."""
    doc = _assert_turn(token)
    if not isinstance(plan, list) or not 1 <= len(plan) <= 20:
        raise ValueError("A native plan must contain between 1 and 20 steps.")
    doc.openTransaction("Next AI: approved design operation")
    results = []
    try:
        for index, step in enumerate(plan, start=1):
            _assert_turn(token)
            if not isinstance(step, dict) or set(step) - {"tool", "args"}:
                raise ValueError(f"Plan step {index} has an invalid shape.")
            tool = step.get("tool")
            if not isinstance(tool, str):
                raise ValueError(f"Plan step {index} has no tool name.")
            results.append({"step": index, **_create_step(doc, tool, step.get("args", {}))})
        doc.recompute()
        doc.commitTransaction()
    except Exception:
        try:
            doc.abortTransaction()
        finally:
            raise
    return {"success": True, "document": _doc_summary(doc), "results": results}
