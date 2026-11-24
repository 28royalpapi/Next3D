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
        if any((points[i] - points[i - 1]).Length <= 1e-7 for i in range(1, len(points))):
            raise ValueError("A wall path cannot contain consecutive duplicate points.")
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

    if tool == "create_draft_wire":
        import Draft
        raw_points = args.get("points")
        if not isinstance(raw_points, list) or not 2 <= len(raw_points) <= 200:
            raise ValueError("A Draft polyline needs between 2 and 200 points.")
        points = [App.Vector(*_point(p, "wire point")) for p in raw_points]
        if any((points[i] - points[i - 1]).Length <= 1e-7 for i in range(1, len(points))):
            raise ValueError("A Draft polyline cannot contain consecutive duplicate points.")
        closed = args.get("closed", False)
        if not isinstance(closed, bool):
            raise ValueError("closed must be true or false.")
        if closed and len(points) < 3:
            raise ValueError("A closed outline needs at least three points.")
        obj = Draft.make_wire(points, closed=closed, face=False)
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Draft polyline.")
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_draft_dimension":
        import Draft
        start = App.Vector(*_point(args.get("start"), "start"))
        end = App.Vector(*_point(args.get("end"), "end"))
        position = App.Vector(*_point(args.get("dimension_line_point"), "dimension_line_point"))
        if (end - start).Length <= 1e-7:
            raise ValueError("A dimension needs two different measurement points.")
        obj = Draft.make_dimension(start, end, position)
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Draft dimension.")
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
        native_commands = Gui.listCommands()
        if isinstance(native_commands, dict):
            commands = {str(key) for key in native_commands.keys()}
        else:
            commands = {str(item) for item in native_commands}
        if not isinstance(command_id, str) or command_id not in commands:
            raise ValueError("That native command is not registered in this NextCAD installation.")
        blocked = ("Macro", "Python", "Quit", "Exit", "Open", "CloseAll", "SaveAs")
        if any(part in command_id for part in blocked):
            raise ValueError("This native command is outside NextAI's approved command set.")
        Gui.runCommand(command_id, 0)
        return {"native_command_started": command_id}

    if tool in {
        "create_partdesign_body",
        "create_partdesign_sketch",
        "add_sketch_line",
        "add_sketch_circle",
        "add_sketch_polygon",
        "create_partdesign_pad",
        "create_partdesign_pocket",
        "inspect_sketch",
        "inspect_partdesign_body",
    }:
        return _partdesign_step(doc, tool, args)

    raise ValueError(f"Unknown or unavailable native tool: {tool}")


def _partdesign_object(doc, name, expected_type=None):
    obj = doc.getObject(str(name))
    if obj is None:
        matches = doc.getObjectsByLabel(str(name))
        if len(matches) > 1:
            raise ValueError(
                f"'{name}' matches multiple labels. Use the native object Name instead."
            )
        obj = matches[0] if matches else None
    if obj is None:
        raise ValueError(f"Native object '{name}' was not found in document '{doc.Name}'.")
    if expected_type and obj.TypeId != expected_type:
        raise ValueError(
            f"'{name}' is {obj.TypeId}; expected {expected_type}."
        )
    return obj


def _partdesign_body_state(body):
    group = list(getattr(body, "Group", []) or [])
    tip = getattr(body, "Tip", None)
    try:
        shape = body.Shape
        valid = bool(not shape.isNull() and shape.isValid()) if group else True
        volume = float(shape.Volume) if not shape.isNull() else 0.0
        solids = len(shape.Solids) if not shape.isNull() else 0
    except Exception as exc:
        return {
            "valid": False,
            "volume_mm3": None,
            "solids": 0,
            "tip": getattr(tip, "Name", None),
            "error": str(exc)[:240],
        }
    return {
        "valid": valid,
        "volume_mm3": round(volume, 6),
        "solids": solids,
        "tip": getattr(tip, "Name", None),
        "feature_count": len(group),
    }


def _partdesign_sketch_state(sketch):
    try:
        dof = int(sketch.DoF)
    except Exception:
        dof = None
    try:
        conflicts = list(sketch.ConflictingConstraints)
    except Exception:
        conflicts = []
    try:
        redundant = list(sketch.RedundantConstraints)
    except Exception:
        redundant = []
    return {
        "name": sketch.Name,
        "geometry_count": len(sketch.Geometry),
        "constraint_count": int(sketch.ConstraintCount),
        "degrees_of_freedom": dof,
        "fully_constrained": dof == 0 and not conflicts and not redundant,
        "conflicting_constraints": conflicts,
        "redundant_constraints": redundant,
        "geometry": [
            {
                "index": i,
                "type": type(geometry).__name__,
                "construction": bool(getattr(geometry, "Construction", False)),
            }
            for i, geometry in enumerate(sketch.Geometry)
        ],
    }


def _pin_sketch_point(sketch, geometry_index, point_index, x, y):
    import Sketcher

    if abs(x) < 1e-9 and abs(y) < 1e-9:
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", geometry_index, point_index, -1, 1)
        )
        return

    if abs(x) < 1e-9:
        sketch.addConstraint(
            Sketcher.Constraint("PointOnObject", geometry_index, point_index, -2)
        )
    else:
        sketch.addConstraint(
            Sketcher.Constraint("DistanceX", -1, 1, geometry_index, point_index, x)
        )

    if abs(y) < 1e-9:
        sketch.addConstraint(
            Sketcher.Constraint("PointOnObject", geometry_index, point_index, -1)
        )
    else:
        sketch.addConstraint(
            Sketcher.Constraint("DistanceY", -1, 1, geometry_index, point_index, y)
        )


def _verify_sketch_solved(sketch, require_fully_constrained=True):
    try:
        sketch.solve()
    except Exception:
        pass
    state = _partdesign_sketch_state(sketch)
    if state["conflicting_constraints"]:
        raise RuntimeError(
            f"Sketch '{sketch.Name}' has conflicting constraints: "
            f"{state['conflicting_constraints']}."
        )
    if state["redundant_constraints"]:
        raise RuntimeError(
            f"Sketch '{sketch.Name}' has redundant constraints: "
            f"{state['redundant_constraints']}."
        )
    if require_fully_constrained and state["degrees_of_freedom"] != 0:
        raise RuntimeError(
            f"Sketch '{sketch.Name}' is not fully constrained "
            f"({state['degrees_of_freedom']} degrees of freedom remain)."
        )
    return state


def _partdesign_step(doc, tool, args):
    App, _Gui = _apps()
    if tool == "create_partdesign_body":
        name = str(args.get("name", "NextAIBody")).strip()
        if not name or len(name) > 80:
            raise ValueError("Body name must contain 1 to 80 characters.")
        existing = doc.getObject(name)
        if existing is not None:
            if existing.TypeId != "PartDesign::Body":
                raise ValueError(
                    f"'{name}' already exists and is not a PartDesign body."
                )
            return {"body": existing.Name, "created": False, **_partdesign_body_state(existing)}
        body = doc.addObject("PartDesign::Body", name)
        doc.recompute()
        if body is None or body.TypeId != "PartDesign::Body":
            raise RuntimeError("FreeCAD failed to create the PartDesign body.")
        return {"body": body.Name, "created": True, **_partdesign_body_state(body)}

    if tool == "create_partdesign_sketch":
        body = _partdesign_object(doc, args.get("body_name"), "PartDesign::Body")
        name = str(args.get("name", "Profile")).strip()
        plane_name = str(args.get("plane", "XY_Plane"))
        offset = _number(args.get("offset", 0.0), "offset", -1_000_000.0, 1_000_000.0)
        if not name or len(name) > 80:
            raise ValueError("Sketch name must contain 1 to 80 characters.")
        if plane_name not in {"XY_Plane", "XZ_Plane", "YZ_Plane"}:
            raise ValueError("Sketch plane must be XY_Plane, XZ_Plane or YZ_Plane.")
        doc.recompute()
        origin = getattr(body, "Origin", None)
        if origin is None:
            raise RuntimeError("The PartDesign body has no native Origin object.")
        plane = next(
            (
                feature for feature in getattr(origin, "OriginFeatures", [])
                if getattr(feature, "Role", None) == plane_name
            ),
            None,
        )
        if plane is None:
            raise RuntimeError(
                f"Could not find {plane_name} on body '{body.Name}'."
            )
        sketch = doc.addObject("Sketcher::SketchObject", name)
        body.addObject(sketch)
        attached = False
        for attribute in ("AttachmentSupport", "Support"):
            if hasattr(sketch, attribute):
                try:
                    setattr(sketch, attribute, [(plane, "")])
                    sketch.MapMode = "FlatFace"
                    attached = True
                    break
                except (AttributeError, TypeError, RuntimeError):
                    continue
        if not attached:
            doc.removeObject(sketch.Name)
            raise RuntimeError(
                "This FreeCAD version could not attach the sketch to the body's origin plane."
            )
        if abs(offset) > 1e-9:
            sketch.AttachmentOffset = App.Placement(
                App.Vector(0, 0, offset), App.Rotation()
            )
        doc.recompute()
        return {
            "sketch": sketch.Name,
            "body": body.Name,
            "plane": plane_name,
            "offset_mm": offset,
            "state": _partdesign_sketch_state(sketch),
        }

    if tool in {"add_sketch_line", "add_sketch_circle", "add_sketch_polygon"}:
        sketch = _partdesign_object(
            doc, args.get("sketch_name"), "Sketcher::SketchObject"
        )
        if tool == "add_sketch_line":
            import Part
            start = _point(args.get("start"), "start")
            end = _point(args.get("end"), "end")
            if math.dist(start[:2], end[:2]) <= 1e-7:
                raise ValueError("Sketch line endpoints must be different.")
            geometry_index = sketch.addGeometry(
                Part.LineSegment(
                    App.Vector(start[0], start[1], 0),
                    App.Vector(end[0], end[1], 0),
                ),
                bool(args.get("construction", False)),
            )
            _pin_sketch_point(sketch, geometry_index, 1, start[0], start[1])
            _pin_sketch_point(sketch, geometry_index, 2, end[0], end[1])
            label = str(args.get("label", "")).strip()
            if label:
                for index in range(int(sketch.ConstraintCount)):
                    try:
                        sketch.renameConstraint(index, f"{label}_{index}")
                    except Exception:
                        pass
            doc.recompute()
            return {
                "sketch": sketch.Name,
                "geometry_index": geometry_index,
                "label": label,
                "state": _verify_sketch_solved(sketch),
            }

        if tool == "add_sketch_circle":
            import Part
            import Sketcher
            radius = _number(args.get("radius"), "radius", 0.001, 1_000_000.0)
            center = _point(args.get("center", [0, 0]), "center")
            geometry_index = sketch.addGeometry(
                Part.Circle(
                    App.Vector(center[0], center[1], 0),
                    App.Vector(0, 0, 1),
                    radius,
                ),
                bool(args.get("construction", False)),
            )
            _pin_sketch_point(sketch, geometry_index, 3, center[0], center[1])
            constraint_index = sketch.addConstraint(
                Sketcher.Constraint("Diameter", geometry_index, radius * 2.0)
            )
            label = str(args.get("label", "")).strip()
            if label and hasattr(sketch, "renameConstraint"):
                try:
                    sketch.renameConstraint(constraint_index, label[:80])
                except Exception:
                    pass
            doc.recompute()
            return {
                "sketch": sketch.Name,
                "geometry_index": geometry_index,
                "radius_mm": radius,
                "diameter_mm": radius * 2.0,
                "label": label,
                "state": _verify_sketch_solved(sketch),
            }

        import Part
        points = args.get("points")
        if not isinstance(points, list) or not 3 <= len(points) <= 80:
            raise ValueError("A sketch polygon needs between 3 and 80 points.")
        points2d = []
        for index, value in enumerate(points):
            point = _point(value, f"points[{index}]")
            points2d.append(point[:2])
        if len({(round(p[0], 7), round(p[1], 7)) for p in points2d}) < 3:
            raise ValueError("A sketch polygon needs at least three distinct vertices.")
        if any(
            math.dist(points2d[i], points2d[(i + 1) % len(points2d)]) <= 1e-7
            for i in range(len(points2d))
        ):
            raise ValueError("Polygon vertices must not be duplicated or consecutive repeats.")
        indices = []
        for i, start in enumerate(points2d):
            end = points2d[(i + 1) % len(points2d)]
            geometry_index = sketch.addGeometry(
                Part.LineSegment(
                    App.Vector(start[0], start[1], 0),
                    App.Vector(end[0], end[1], 0),
                ),
                False,
            )
            indices.append(geometry_index)
        # Join each segment end to the following segment start, then pin each
        # vertex once. This produces a closed, fully constrained native profile
        # without duplicating coordinate constraints on shared endpoints.
        import Sketcher
        for i, geometry_index in enumerate(indices):
            following = indices[(i + 1) % len(indices)]
            sketch.addConstraint(
                Sketcher.Constraint("Coincident", geometry_index, 2, following, 1)
            )
        for i, geometry_index in enumerate(indices):
            _pin_sketch_point(sketch, geometry_index, 1, points2d[i][0], points2d[i][1])
        doc.recompute()
        return {
            "sketch": sketch.Name,
            "geometry_indices": indices,
            "closed": True,
            "state": _verify_sketch_solved(sketch),
        }

    if tool in {"create_partdesign_pad", "create_partdesign_pocket"}:
        body = _partdesign_object(doc, args.get("body_name"), "PartDesign::Body")
        sketch = _partdesign_object(
            doc, args.get("sketch_name"), "Sketcher::SketchObject"
        )
        if sketch not in list(getattr(body, "Group", [])):
            raise ValueError(
                f"Sketch '{sketch.Name}' does not belong to body '{body.Name}'."
            )
        _verify_sketch_solved(sketch, require_fully_constrained=True)
        length = _number(args.get("length"), "length", 0.001, 1_000_000.0)
        before_state = _partdesign_body_state(body)
        before_volume = before_state["volume_mm3"] or 0.0
        feature_kind = "PartDesign::Pad" if tool == "create_partdesign_pad" else "PartDesign::Pocket"
        feature_name = str(args.get("name", "NextAIFeature")).strip() or "NextAIFeature"
        feature = doc.addObject(
            feature_kind,
            "NextAI" + ("Pad" if tool == "create_partdesign_pad" else "Pocket"),
        )
        body.addObject(feature)
        feature.Profile = sketch
        feature.Length = length
        if tool == "create_partdesign_pad":
            if args.get("symmetric", False):
                if hasattr(feature, "SideType"):
                    feature.SideType = "Symmetric"
                else:
                    doc.removeObject(feature.Name)
                    raise RuntimeError(
                        "Symmetric pad is not supported by this FreeCAD version; no feature was kept."
                    )
        else:
            feature.Reversed = bool(args.get("reversed", True))
            if args.get("through_all", False):
                feature.Type = "ThroughAll"
        if hasattr(feature, "Refine"):
            feature.Refine = False
        if feature_name:
            feature.Label = feature_name[:120]
        sketch.Visibility = False
        doc.recompute()
        shape = getattr(feature, "Shape", None)
        if shape is None or shape.isNull() or not shape.isValid():
            raise RuntimeError(
                f"{tool} produced an invalid or empty feature shape; the transaction will roll back."
            )
        body.Tip = feature
        doc.recompute()
        after_state = _partdesign_body_state(body)
        after_volume = after_state["volume_mm3"] or 0.0
        if not after_state["valid"] or after_state["solids"] != 1:
            raise RuntimeError(
                f"The body after {tool} is not one valid solid: {after_state}."
            )
        if tool == "create_partdesign_pad" and after_volume <= before_volume + 1e-7:
            raise RuntimeError(
                f"Pad did not increase body volume ({before_volume} -> {after_volume} mm^3)."
            )
        if tool == "create_partdesign_pocket" and after_volume >= before_volume - 1e-7:
            raise RuntimeError(
                f"Pocket did not remove material ({before_volume} -> {after_volume} mm^3)."
            )
        return {
            "feature": feature.Name,
            "label": feature.Label,
            "type": feature.TypeId,
            "length_mm": length,
            "before_volume_mm3": before_volume,
            "after_volume_mm3": after_volume,
            "state": after_state,
        }

    if tool == "inspect_sketch":
        sketch = _partdesign_object(
            doc, args.get("sketch_name"), "Sketcher::SketchObject"
        )
        return _partdesign_sketch_state(sketch)

    if tool == "inspect_partdesign_body":
        body = _partdesign_object(doc, args.get("body_name"), "PartDesign::Body")
        return {
            "body": body.Name,
            "label": body.Label,
            **_partdesign_body_state(body),
            "features": [
                {"name": obj.Name, "label": obj.Label, "type": obj.TypeId}
                for obj in list(getattr(body, "Group", []) or [])[:200]
            ],
        }

    raise ValueError(f"Unknown PartDesign NextAI tool: {tool}")


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
