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


def _summary_point(point):
    return [
        round(float(point.x), 4),
        round(float(point.y), 4),
        round(float(point.z), 4),
    ]


def _object_summary(obj):
    result = {
        "name": str(obj.Name),
        "label": str(obj.Label),
        "type": str(obj.TypeId),
    }

    # Include useful native parameters without serialising arbitrary Python objects.
    parameters = {}
    for prop in (
        "Length", "Width", "Height", "Radius", "Angle", "Reversed",
        "Type", "SideType", "Refine", "Placement", "Thickness", "Diameter",
    ):
        if not hasattr(obj, prop):
            continue
        try:
            value = getattr(obj, prop)
            if prop == "Placement":
                parameters[prop] = {
                    "base": _summary_point(value.Base),
                    "rotation_axis": _summary_point(value.Rotation.Axis),
                    "rotation_degrees": round(float(value.Rotation.Angle) * 180.0 / math.pi, 4),
                }
            elif isinstance(value, (str, bool, int, float)):
                parameters[prop] = round(float(value), 6) if isinstance(value, float) else value
        except Exception:
            continue
    if parameters:
        result["parameters"] = parameters

    if obj.TypeId == "PartDesign::Body":
        tip = getattr(obj, "Tip", None)
        result["body_tip"] = getattr(tip, "Name", None)
        result["feature_names"] = [
            str(item.Name) for item in list(getattr(obj, "Group", []) or [])[:80]
        ]

    if obj.TypeId == "Sketcher::SketchObject":
        try:
            constraints = []
            for item in list(getattr(obj, "Constraints", []))[:60]:
                entry = {
                    "type": str(getattr(item, "Type", "")),
                    "name": str(getattr(item, "Name", "") or ""),
                }
                value = getattr(item, "Value", None)
                if isinstance(value, (int, float)):
                    entry["value"] = round(float(value), 6)
                constraints.append(entry)
            geometry = []
            for index, item in enumerate(list(getattr(obj, "Geometry", []))[:60]):
                entry = {
                    "index": index,
                    "type": type(item).__name__,
                    "construction": bool(getattr(item, "Construction", False)),
                }
                if hasattr(item, "StartPoint") and hasattr(item, "EndPoint"):
                    entry["start"] = _summary_point(item.StartPoint)
                    entry["end"] = _summary_point(item.EndPoint)
                if hasattr(item, "Center") and hasattr(item, "Radius"):
                    entry["center"] = _summary_point(item.Center)
                    entry["radius_mm"] = round(float(item.Radius), 4)
                geometry.append(entry)
            try:
                dof = int(obj.DoF)
            except Exception:
                dof = None
            result["sketch"] = {
                "geometry_count": len(getattr(obj, "Geometry", [])),
                "constraint_count": int(getattr(obj, "ConstraintCount", 0)),
                "degrees_of_freedom": dof,
                "fully_constrained": dof == 0,
                "geometry_truncated": len(getattr(obj, "Geometry", [])) > len(geometry),
                "geometry": geometry,
                "constraints": constraints,
            }
        except Exception as exc:
            result["sketch_summary_error"] = str(exc)[:160]

    try:
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull():
            box = shape.BoundBox
            result["shape"] = {
                "valid": bool(shape.isValid()),
                "volume_mm3": round(float(shape.Volume), 6),
                "area_mm2": round(float(shape.Area), 6),
                "solids": len(shape.Solids),
                "faces": len(shape.Faces),
                "edges": len(shape.Edges),
                "vertices": len(shape.Vertexes),
                "bounding_box_mm": {
                    "min_x": round(float(box.XMin), 4),
                    "min_y": round(float(box.YMin), 4),
                    "min_z": round(float(box.ZMin), 4),
                    "max_x": round(float(box.XMax), 4),
                    "max_y": round(float(box.YMax), 4),
                    "max_z": round(float(box.ZMax), 4),
                    "length_x": round(float(box.XLength), 4),
                    "length_y": round(float(box.YLength), 4),
                    "length_z": round(float(box.ZLength), 4),
                },
            }
    except Exception as exc:
        result["shape_summary_error"] = str(exc)[:160]
    return result


def _doc_summary(doc):
    all_objects = list(doc.Objects)
    objects = [_object_summary(obj) for obj in all_objects[:60]]
    return {
        "name": str(doc.Name),
        "label": str(doc.Label),
        "file": str(getattr(doc, "FileName", "")),
        "object_count": len(all_objects),
        "objects": objects,
        "objects_truncated": len(all_objects) > len(objects),
    }


def _create_model_schedule(doc, args):
    """Create a native Spreadsheet schedule from actual document objects and geometry."""
    if not isinstance(args, dict):
        raise ValueError("Schedule arguments must be an object.")
    requested = args.get("object_names", [])
    if not isinstance(requested, list) or len(requested) > 200:
        raise ValueError("object_names must be a list of at most 200 native object names.")
    if any(not isinstance(name, str) or not name.strip() for name in requested):
        raise ValueError("Every schedule object name must be a non-empty string.")
    if len(set(requested)) != len(requested):
        raise ValueError("Schedule object_names cannot contain duplicates.")

    schedule_name = str(args.get("name", "NextAIModelSchedule")).strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", schedule_name):
        raise ValueError("Schedule name must be a simple native identifier of 1 to 40 characters.")

    if requested:
        objects = []
        for name in requested:
            obj = doc.getObject(name)
            if obj is None:
                raise ValueError(f"Schedule object '{name}' was not found in the active document.")
            objects.append(obj)
    else:
        objects = [
            obj for obj in list(doc.Objects)
            if str(getattr(obj, "TypeId", "")) != "Spreadsheet::Sheet"
        ][:200]

    if not objects:
        raise ValueError("There are no native model objects to schedule.")
    if len(objects) > 200:
        raise ValueError("A model schedule is limited to 200 objects per operation.")

    headers = [
        "Mark", "Native object ID", "Component / label", "Native type",
        "X span (mm)", "Y span (mm)", "Z span (mm)",
        "Shape area (mm^2)", "Volume (mm^3)", "Solid count",
        "Faces", "Edges", "Geometry valid", "Native dimensions / properties",
    ]
    rows = []
    for index, obj in enumerate(objects, start=1):
        summary = _object_summary(obj)
        shape = summary.get("shape") or {}
        bounds = shape.get("bounding_box_mm") or {}
        native_dimensions = []
        for prop in (
            "Length", "Width", "Height", "Radius", "Radius1", "Radius2",
            "Diameter", "Thickness", "Angle",
        ):
            try:
                if prop in list(getattr(obj, "PropertiesList", [])):
                    native_dimensions.append(f"{prop}={getattr(obj, prop)}")
            except Exception:
                continue
        rows.append([
            f"M{index:03d}",
            summary.get("name", ""),
            summary.get("label", ""),
            summary.get("type", ""),
            bounds.get("length_x", ""),
            bounds.get("length_y", ""),
            bounds.get("length_z", ""),
            shape.get("area_mm2", ""),
            shape.get("volume_mm3", ""),
            shape.get("solids", ""),
            shape.get("faces", ""),
            shape.get("edges", ""),
            shape.get("valid", ""),
            "; ".join(native_dimensions),
        ])

    if doc.getObject(schedule_name) is not None:
        raise ValueError(
            f"Schedule object '{schedule_name}' already exists. Choose another name; existing schedules are not overwritten."
        )
    sheet = doc.addObject("Spreadsheet::Sheet", schedule_name)
    if sheet is None or str(getattr(sheet, "TypeId", "")) != "Spreadsheet::Sheet":
        raise RuntimeError("FreeCAD did not create a native Spreadsheet sheet.")

    def cell_value(value):
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        text_value = str(value)
        # Prevent a model label from being interpreted as a Spreadsheet formula.
        if text_value.startswith(("=", "+", "-", "@")):
            text_value = "'" + text_value
        return text_value

    def cell_name(column, row):
        letters = ""
        value = column + 1
        while value:
            value, remainder = divmod(value - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{row}"

    for column, header in enumerate(headers):
        sheet.set(cell_name(column, 1), header)
    for row_index, row in enumerate(rows, start=2):
        for column, value in enumerate(row):
            sheet.set(cell_name(column, row_index), cell_value(value))

    try:
        sheet.Label = str(args.get("label", "NextAI model-derived component schedule"))[:120]
    except Exception:
        pass
    doc.recompute()
    return {
        "schedule": sheet.Name,
        "label": str(getattr(sheet, "Label", sheet.Name)),
        "type": sheet.TypeId,
        "row_count": len(rows),
        "column_count": len(headers),
        "source_rule": "Native object properties and measured Shape/BoundBox values only; blank values mean the model does not expose that field.",
        "sample_marks": [row[0] for row in rows[:8]],
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


def _native_name(value, fallback):
    raw = str(value or fallback).strip()
    safe = re.sub(r"[^A-Za-z0-9_]", "_", raw)[:40]
    if not safe or not safe[0].isalpha():
        safe = "NextAI_" + safe
    return safe


def _document_object(doc, name):
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise ValueError("A valid native object name is required.")
    obj = doc.getObject(name)
    if obj is None:
        raise ValueError(f"Native object '{name}' was not found in the active document.")
    return obj


def _native_shape(obj):
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        raise ValueError(f"'{obj.Label}' has no non-empty native shape.")
    return shape


def _verify_native_shape(obj, operation):
    shape = _native_shape(obj)
    if not shape.isValid():
        raise RuntimeError(f"{operation} produced invalid geometry; the transaction will roll back.")
    state = list(getattr(obj, "State", []) or [])
    if any(item in ("Invalid", "Error") for item in state):
        raise RuntimeError(f"{operation} left the native object in an invalid state: {state}.")
    return {
        "valid": True,
        "solids": len(shape.Solids),
        "faces": len(shape.Faces),
        "edges": len(shape.Edges),
        "volume_mm3": round(float(shape.Volume), 6),
        "area_mm2": round(float(shape.Area), 6),
    }


def _find_partdesign_body(obj):
    if str(getattr(obj, "TypeId", "")) == "PartDesign::Body":
        return obj
    try:
        parents = list(getattr(obj, "InList", []) or [])
    except Exception:
        parents = []
    return next((parent for parent in parents if str(getattr(parent, "TypeId", "")) == "PartDesign::Body"), None)


def _apply_relative_placement(old, tx, ty, tz, ax, ay, az, angle):
    """Translate in global coordinates and rotate in place about the object's origin."""
    App, _Gui = _apps()
    new_base = old.Base + App.Vector(tx, ty, tz)
    if abs(angle) > 1e-12:
        axis = App.Vector(ax, ay, az)
        if axis.Length <= 1e-9:
            raise ValueError("A non-zero rotation angle requires a non-zero rotation axis.")
        delta_rotation = App.Rotation(axis, angle)
        new_rotation = delta_rotation.multiply(old.Rotation)
    else:
        new_rotation = old.Rotation
    return App.Placement(new_base, new_rotation)


def _edge_references(shape, raw_edges):
    if not isinstance(raw_edges, list) or not raw_edges or len(raw_edges) > 200:
        raise ValueError("edges must contain 'all' or one or more explicit EdgeN references.")
    if any(not isinstance(item, str) for item in raw_edges):
        raise ValueError("Every edge reference must be a string.")
    if len(set(raw_edges)) != len(raw_edges):
        raise ValueError("Edge references cannot contain duplicates.")
    if "all" in raw_edges:
        if len(raw_edges) != 1:
            raise ValueError("Use 'all' by itself; do not mix it with explicit EdgeN references.")
        if not shape.Edges:
            raise ValueError("The selected object has no edges.")
        return [f"Edge{index}" for index in range(1, len(shape.Edges) + 1)]
    resolved = []
    for reference in raw_edges:
        match = re.fullmatch(r"Edge([1-9][0-9]*)", reference)
        if not match:
            raise ValueError(f"Unsupported edge reference '{reference}'. Use 'all' or exact EdgeN names.")
        index = int(match.group(1))
        if index > len(shape.Edges):
            raise ValueError(f"{reference} does not exist; the selected shape has {len(shape.Edges)} edges.")
        resolved.append(reference)
    return resolved


def _create_boolean(doc, args):
    App, _Gui = _apps()
    operation = str(args.get("operation", "")).lower()
    if operation not in {"fuse", "cut", "common"}:
        raise ValueError("Boolean operation must be fuse, cut or common.")
    first = _document_object(doc, args.get("object1"))
    second = _document_object(doc, args.get("object2"))
    if first is second:
        raise ValueError("A boolean operation requires two different native objects.")
    doc.recompute()
    _native_shape(first)
    _native_shape(second)
    label = str(args.get("label", "")).strip()[:120]
    native_name = _native_name(label, operation.capitalize())

    if first.TypeId == "PartDesign::Body" and second.TypeId == "PartDesign::Body":
        feature = first.newObject("PartDesign::Boolean", native_name)
        feature.Type = {"fuse": "Fuse", "cut": "Cut", "common": "Common"}[operation]
        feature.addObjects([second])
        first.Tip = feature
        doc.recompute()
        verification = _verify_native_shape(feature, "PartDesign Boolean")
        verification["body"] = first.Name
        parametric = True
    else:
        part_type = {"fuse": "Part::Fuse", "cut": "Part::Cut", "common": "Part::Common"}[operation]
        feature = doc.addObject(part_type, native_name)
        feature.Base = first
        feature.Tool = second
        if label:
            feature.Label = label
        doc.recompute()
        verification = _verify_native_shape(feature, "Part Boolean")
        parametric = True

    return {
        "created": feature.Name,
        "label": feature.Label,
        "type": feature.TypeId,
        "operation": operation,
        "base_object": first.Name,
        "tool_object": second.Name,
        "parametric_native_feature": parametric,
        "verification": verification,
    }


def _transform_native_object(doc, args):
    App, _Gui = _apps()
    obj = _document_object(doc, args.get("object_name"))
    if not hasattr(obj, "Placement"):
        raise ValueError(f"'{obj.Label}' does not expose a native Placement property.")
    tx = _number(args.get("translate_x", 0.0), "translate_x")
    ty = _number(args.get("translate_y", 0.0), "translate_y")
    tz = _number(args.get("translate_z", 0.0), "translate_z")
    ax = _number(args.get("rotate_axis_x", 0.0), "rotate_axis_x")
    ay = _number(args.get("rotate_axis_y", 0.0), "rotate_axis_y")
    az = _number(args.get("rotate_axis_z", 1.0), "rotate_axis_z")
    angle = _number(args.get("rotate_angle", 0.0), "rotate_angle", -360000.0, 360000.0)
    relative = args.get("relative", True)
    if not isinstance(relative, bool):
        raise ValueError("relative must be true or false.")

    if relative:
        obj.Placement = _apply_relative_placement(obj.Placement, tx, ty, tz, ax, ay, az, angle)
    else:
        axis = App.Vector(ax, ay, az)
        if abs(angle) > 1e-12 and axis.Length <= 1e-9:
            raise ValueError("A non-zero rotation angle requires a non-zero rotation axis.")
        rotation = App.Rotation(axis, angle) if abs(angle) > 1e-12 else App.Rotation()
        obj.Placement = App.Placement(App.Vector(tx, ty, tz), rotation)

    doc.recompute()
    verification = {}
    if getattr(obj, "Shape", None) is not None and not obj.Shape.isNull():
        verification = _verify_native_shape(obj, "Native transform")
    return {
        "edited": obj.Name,
        "label": obj.Label,
        "relative": relative,
        "translation_mm": [tx, ty, tz],
        "rotation_axis": [ax, ay, az],
        "rotation_degrees": angle,
        "verification": verification,
    }


def _duplicate_native_object(doc, args):
    App, _Gui = _apps()
    obj = _document_object(doc, args.get("object_name"))
    copied = doc.copyObject(obj, True)
    clone = copied[-1] if isinstance(copied, (list, tuple)) else copied
    if clone is None:
        raise RuntimeError(f"FreeCAD could not duplicate '{obj.Label}'.")
    requested_label = str(args.get("label", "")).strip()
    clone.Label = requested_label[:120] if requested_label else (str(obj.Label) + " Copy")[:120]
    tx = _number(args.get("translate_x", 0.0), "translate_x")
    ty = _number(args.get("translate_y", 0.0), "translate_y")
    tz = _number(args.get("translate_z", 0.0), "translate_z")
    angle = _number(args.get("rotate_angle", 0.0), "rotate_angle", -360000.0, 360000.0)
    ax = _number(args.get("rotate_axis_x", 0.0), "rotate_axis_x")
    ay = _number(args.get("rotate_axis_y", 0.0), "rotate_axis_y")
    az = _number(args.get("rotate_axis_z", 1.0), "rotate_axis_z")
    if tx or ty or tz or angle:
        if not hasattr(clone, "Placement"):
            raise ValueError(f"Duplicate '{clone.Label}' does not expose Placement for the requested offset.")
        clone.Placement = _apply_relative_placement(clone.Placement, tx, ty, tz, ax, ay, az, angle)
    doc.recompute()
    verification = {}
    if getattr(clone, "Shape", None) is not None and not clone.Shape.isNull():
        verification = _verify_native_shape(clone, "Native duplicate")
    return {
        "created": clone.Name,
        "label": clone.Label,
        "type": clone.TypeId,
        "source_object": obj.Name,
        "source_unchanged": True,
        "verification": verification,
    }


def _create_edge_feature(doc, args, operation):
    App, _Gui = _apps()
    obj = _document_object(doc, args.get("object_name"))
    shape = _native_shape(obj)
    edges = _edge_references(shape, args.get("edges"))
    if operation == "fillet":
        amount = _number(args.get("radius"), "radius", 0.001, 1_000_000.0)
        feature_type = "PartDesign::Fillet"
        property_name = "Radius"
    else:
        amount = _number(args.get("size"), "size", 0.001, 1_000_000.0)
        feature_type = "PartDesign::Chamfer"
        property_name = "Size"

    body = _find_partdesign_body(obj)
    label = str(args.get("label", "")).strip()[:120]
    native_name = _native_name(label, operation.capitalize())
    if body is not None:
        base_feature = body.Tip if obj is body else obj
        if base_feature is None:
            raise ValueError(f"PartDesign body '{body.Label}' has no feature to modify.")
        feature = body.newObject(feature_type, native_name)
        feature.Base = (base_feature, edges)
        setattr(feature, property_name, amount)
        body.Tip = feature
        doc.recompute()
        verification = _verify_native_shape(feature, f"PartDesign {operation}")
        verification["body"] = body.Name
        parametric = True
    else:
        # Generic Part shapes have no PartDesign history. Keep the original
        # object and create a separate result with an explicit source link.
        selected = [shape.Edges[int(reference[4:]) - 1] for reference in edges]
        output_shape = shape.makeFillet(amount, selected) if operation == "fillet" else shape.makeChamfer(amount, selected)
        if output_shape.isNull() or not output_shape.isValid():
            raise RuntimeError(f"Native Part {operation} returned invalid geometry.")
        feature = doc.addObject("Part::Feature", native_name)
        feature.Shape = output_shape
        if hasattr(feature, "addProperty"):
            feature.addProperty("App::PropertyLink", "NextAIBaseObject", "NextAI")
            feature.NextAIBaseObject = obj
            feature.addProperty("App::PropertyString", "NextAIOperation", "NextAI")
            feature.NextAIOperation = operation
            feature.addProperty("App::PropertyString", "NextAISelectedEdges", "NextAI")
            feature.NextAISelectedEdges = ", ".join(edges)
            feature.addProperty("App::PropertyLength", "NextAIAmount", "NextAI")
            feature.NextAIAmount = amount
        if label:
            feature.Label = label
        doc.recompute()
        verification = _verify_native_shape(feature, f"Part {operation}")
        parametric = False

    return {
        "created": feature.Name,
        "label": feature.Label,
        "type": feature.TypeId,
        "operation": operation,
        "amount_mm": amount,
        "edges": edges,
        "parametric_native_feature": parametric,
        "verification": verification,
    }


def _create_partdesign_pattern(doc, args, pattern_kind):
    App, _Gui = _apps()
    feature = _document_object(doc, args.get("feature_name"))
    body = _find_partdesign_body(feature)
    if body is None or feature is body:
        raise ValueError("The source feature must belong to a native PartDesign Body.")
    if feature not in list(getattr(body, "Group", []) or []):
        raise ValueError(f"Feature '{feature.Name}' is not part of body '{body.Name}'.")
    direction = str(args.get("axis", args.get("direction", "Z"))).upper()
    if direction not in {"X", "Y", "Z"}:
        raise ValueError("Only body origin axes X, Y or Z are currently supported.")
    origin = getattr(body, "Origin", None)
    axes = list(getattr(origin, "OriginFeatures", []) or []) if origin else []
    axis_role = direction + "_Axis"
    axis_object = next((item for item in axes if getattr(item, "Role", None) == axis_role), None)
    if axis_object is None:
        raise RuntimeError(f"Could not resolve the native body {direction} axis.")
    try:
        occurrences = int(args.get("occurrences"))
    except (TypeError, ValueError) as exc:
        raise ValueError("occurrences must be an integer of at least 2.") from exc
    if isinstance(args.get("occurrences"), bool) or occurrences < 2 or occurrences > 1000:
        raise ValueError("occurrences must be an integer between 2 and 1000.")
    label = str(args.get("label", "")).strip()[:120]
    native_name = _native_name(label, pattern_kind.capitalize())
    if pattern_kind == "linear":
        length = _number(args.get("length"), "length", 0.001, 1_000_000.0)
        pattern = body.newObject("PartDesign::LinearPattern", native_name)
        pattern.Originals = [feature]
        pattern.Direction = (axis_object, [""])
        pattern.Length = length
    else:
        angle = _number(args.get("angle", 360.0), "angle", 0.001, 360.0)
        pattern = body.newObject("PartDesign::PolarPattern", native_name)
        pattern.Originals = [feature]
        pattern.Axis = (axis_object, [""])
        pattern.Angle = angle
    pattern.Occurrences = occurrences
    body.Tip = pattern
    doc.recompute()
    verification = _verify_native_shape(pattern, f"PartDesign {pattern_kind} pattern")
    return {
        "created": pattern.Name,
        "label": pattern.Label,
        "type": pattern.TypeId,
        "source_feature": feature.Name,
        "axis": direction,
        "occurrences": occurrences,
        "verification": verification,
    }


def _create_step(doc, tool, args):
    App, Gui = _apps()
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object.")

    if tool == "create_model_schedule":
        return _create_model_schedule(doc, args)

    if tool == "boolean_operation":
        return _create_boolean(doc, args)

    if tool == "transform_object":
        return _transform_native_object(doc, args)

    if tool == "duplicate_object":
        return _duplicate_native_object(doc, args)

    if tool == "fillet_edges":
        return _create_edge_feature(doc, args, "fillet")

    if tool == "chamfer_edges":
        return _create_edge_feature(doc, args, "chamfer")

    if tool == "linear_pattern":
        return _create_partdesign_pattern(doc, args, "linear")

    if tool == "polar_pattern":
        return _create_partdesign_pattern(doc, args, "polar")

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
            name="NextAIWall",
        )
        if wall is None:
            raise RuntimeError("FreeCAD did not create the Arch wall.")
        if args.get("label"):
            wall.Label = str(args["label"])[:120]
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

    if tool == "create_part_cylinder":
        radius = _number(args.get("radius"), "radius", 0.001, 1_000_000.0)
        height = _number(args.get("height"), "height", 0.001, 1_000_000.0)
        origin = App.Vector(*_point(args.get("origin", [0, 0, 0]), "origin"))
        axis = App.Vector(*_point(args.get("axis", [0, 0, 1]), "axis"))
        if axis.Length <= 1e-7:
            raise ValueError("A cylinder axis must be a non-zero direction.")
        obj = doc.addObject("Part::Cylinder", "NextAICylinder")
        obj.Radius = radius
        obj.Height = height
        obj.Placement = App.Placement(
            origin,
            App.Rotation(App.Vector(0, 0, 1), axis),
        )
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_part_sphere":
        radius = _number(args.get("radius"), "radius", 0.001, 1_000_000.0)
        center = App.Vector(*_point(args.get("center", [0, 0, 0]), "center"))
        obj = doc.addObject("Part::Sphere", "NextAISphere")
        obj.Radius = radius
        obj.Placement = App.Placement(center, App.Rotation())
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
        return {"created": obj.Name, "label": obj.Label, "type": obj.TypeId}

    if tool == "create_part_cone":
        radius1 = _number(args.get("radius1"), "radius1", 0.0, 1_000_000.0)
        radius2 = _number(args.get("radius2"), "radius2", 0.0, 1_000_000.0)
        height = _number(args.get("height"), "height", 0.001, 1_000_000.0)
        if radius1 <= 0 and radius2 <= 0:
            raise ValueError("A cone needs at least one positive end radius.")
        origin = App.Vector(*_point(args.get("origin", [0, 0, 0]), "origin"))
        axis = App.Vector(*_point(args.get("axis", [0, 0, 1]), "axis"))
        if axis.Length <= 1e-7:
            raise ValueError("A cone axis must be a non-zero direction.")
        obj = doc.addObject("Part::Cone", "NextAICone")
        obj.Radius1 = radius1
        obj.Radius2 = radius2
        obj.Height = height
        obj.Placement = App.Placement(
            origin,
            App.Rotation(App.Vector(0, 0, 1), axis),
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
        obj = Arch.makeStructure(length=length, width=width, height=height, name="NextAIStructure")
        if obj is None:
            raise RuntimeError("FreeCAD did not create the Arch structural element.")
        obj.Placement = App.Placement(
            App.Vector(*_point(args.get("origin", [0, 0, 0]), "origin")),
            App.Rotation(),
        )
        if args.get("label"):
            obj.Label = str(args["label"])[:120]
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
        "create_parametric_variables",
        "bind_parametric_expression",
        "add_sketch_line",
        "add_sketch_circle",
        "add_sketch_polygon",
        "create_partdesign_pad",
        "create_partdesign_pocket",
        "inspect_sketch",
        "inspect_partdesign_body",
        "edit_native_property",
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

    if tool == "create_parametric_variables":
        name = str(args.get("name", "Vars")).strip() or "Vars"
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name):
            raise ValueError("Variable-set name must be a simple identifier.")
        varset = doc.getObject(name)
        if varset is None:
            varset = doc.addObject("App::VarSet", name)
            doc.recompute()
        elif varset.TypeId != "App::VarSet":
            raise ValueError(
                f"'{name}' already exists and is {varset.TypeId}, not an App::VarSet."
            )

        allowed_types = {
            "App::PropertyLength",
            "App::PropertyFloat",
            "App::PropertyInteger",
            "App::PropertyAngle",
            "App::PropertyString",
            "App::PropertyBool",
        }
        paths = {}
        for entry in args.get("variables", []):
            variable_name = str(entry.get("name", "")).strip()
            value = entry.get("value")
            property_type = str(entry.get("type", "App::PropertyLength"))
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", variable_name):
                raise ValueError(f"Invalid parameter name: {variable_name!r}.")
            if property_type not in allowed_types:
                raise ValueError(
                    f"Unsupported parameter type '{property_type}'. "
                    f"Allowed: {sorted(allowed_types)}."
                )
            if property_type in {"App::PropertyLength", "App::PropertyFloat", "App::PropertyAngle"}:
                value = _number(value, variable_name, -1_000_000.0, 1_000_000.0)
            elif property_type == "App::PropertyInteger":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValueError(f"{variable_name} must be an integer.")
            elif property_type == "App::PropertyString":
                if not isinstance(value, str) or len(value) > 200:
                    raise ValueError(f"{variable_name} must be a string of at most 200 characters.")
            elif property_type == "App::PropertyBool":
                if not isinstance(value, bool):
                    raise ValueError(f"{variable_name} must be true or false.")

            if variable_name in varset.PropertiesList:
                if varset.getGroupOfProperty(variable_name) == "Base":
                    raise ValueError(
                        f"'{variable_name}' is a built-in VarSet property, not a parameter."
                    )
                actual_type = varset.getTypeIdOfProperty(variable_name)
                if actual_type != property_type:
                    raise ValueError(
                        f"Parameter '{variable_name}' already exists as {actual_type}; "
                        f"it cannot be silently changed to {property_type}."
                    )
            else:
                varset.addProperty(
                    property_type,
                    variable_name,
                    "Parameters",
                    str(entry.get("description", "NextAI project parameter"))[:240],
                )
            setattr(varset, variable_name, value)
            paths[variable_name] = f"{varset.Name}.{variable_name}"

        doc.recompute()
        values = {
            variable_name: str(getattr(varset, variable_name))
            for variable_name in paths
        }
        return {
            "varset": varset.Name,
            "parameters": values,
            "expression_paths": paths,
        }

    if tool == "bind_parametric_expression":
        target = _partdesign_object(doc, args.get("object_name"))
        property_name = str(args.get("property_name", "")).strip()
        expression = str(args.get("expression", "")).strip()
        if not property_name or len(property_name) > 100:
            raise ValueError("A valid native property or named sketch constraint is required.")
        if not expression or len(expression) > 240:
            raise ValueError("Expression must contain 1 to 240 characters.")
        constraint_names = [
            str(getattr(item, "Name", "") or "")
            for item in list(getattr(target, "Constraints", []))
        ]
        if property_name in constraint_names:
            expression_target = f"Constraints.{property_name}"
        elif property_name in list(getattr(target, "PropertiesList", [])):
            expression_target = property_name
        else:
            named = [item for item in constraint_names if item]
            raise ValueError(
                f"'{property_name}' is not a property or named constraint on '{target.Name}'. "
                f"Named constraints: {named[:30]}."
            )
        was_invalid = "Invalid" in list(getattr(target, "State", []))
        try:
            value = target.evalExpression(expression)
        except Exception as exc:
            raise ValueError(
                f"Expression '{expression}' did not resolve in FreeCAD: {str(exc)[:200]}"
            ) from None
        target.setExpression(expression_target, expression)
        doc.recompute()
        if not was_invalid and "Invalid" in list(getattr(target, "State", [])):
            raise RuntimeError(
                f"Binding {target.Name}.{expression_target} to '{expression}' made the object invalid."
            )
        return {
            "object": target.Name,
            "property": expression_target,
            "expression": expression,
            "evaluated_value": str(value),
            "state": str(list(getattr(target, "State", []))),
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

    if tool == "edit_native_property":
        object_name = str(args.get("object_name", "")).strip()
        property_name = str(args.get("property_name", "")).strip()
        value = args.get("value")
        if not object_name or len(object_name) > 120:
            raise ValueError("A valid native object name is required.")
        obj = doc.getObject(object_name)
        if obj is None:
            raise ValueError(f"Native object '{object_name}' was not found in the active document.")

        if property_name == "Label":
            if not isinstance(value, str) or not value.strip() or len(value) > 120:
                raise ValueError("Label must be a non-empty string of at most 120 characters.")
            before = str(obj.Label)
            obj.Label = value.strip()
            doc.recompute()
            return {
                "edited": obj.Name,
                "property": "Label",
                "before": before,
                "after": str(obj.Label),
                "object": _object_summary(obj),
            }

        editable_by_type = {
            "Part::Box": {"Length", "Width", "Height"},
            "Part::Cylinder": {"Radius", "Height"},
            "Part::Cone": {"Radius1", "Radius2", "Height"},
            "Arch::Wall": {"Height", "Width"},
            "Arch::Structure": {"Length", "Width", "Height"},
            "PartDesign::Pad": {"Length"},
            "PartDesign::Pocket": {"Length"},
        }
        permitted = editable_by_type.get(str(obj.TypeId), set())
        if property_name not in permitted or property_name not in list(obj.PropertiesList):
            raise ValueError(
                f"Property '{property_name}' is not an approved editable dimension for {obj.TypeId}."
            )
        property_type = str(obj.getTypeIdOfProperty(property_name))
        if property_type not in {"App::PropertyLength", "App::PropertyDistance", "App::PropertyFloat"}:
            raise ValueError(
                f"Property '{property_name}' has unsupported type {property_type}; no edit was made."
            )
        get_editor_mode = getattr(obj, "getEditorMode", None)
        if callable(get_editor_mode):
            try:
                if int(get_editor_mode(property_name)) & 1:
                    raise ValueError(f"Property '{property_name}' is read-only.")
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError(
                    f"Could not confirm that '{property_name}' is editable: {str(exc)[:160]}"
                ) from None

        new_value = _number(value, property_name, 0.001, 1_000_000.0)
        current = getattr(obj, property_name)
        before = float(getattr(current, "Value", current))
        setattr(obj, property_name, new_value)
        doc.recompute()
        state = list(getattr(obj, "State", []) or [])
        if "Invalid" in state:
            raise RuntimeError(
                f"Editing {obj.Name}.{property_name} made the native object invalid; the transaction will roll back."
            )
        shape = getattr(obj, "Shape", None)
        if shape is not None and not shape.isNull() and not shape.isValid():
            raise RuntimeError(
                f"Editing {obj.Name}.{property_name} produced invalid geometry; the transaction will roll back."
            )
        current = getattr(obj, property_name)
        after = float(getattr(current, "Value", current))
        return {
            "edited": obj.Name,
            "property": property_name,
            "before": before,
            "after": after,
            "object": _object_summary(obj),
        }

    raise ValueError(f"Unknown PartDesign NextAI tool: {tool}")


def execute_plan(token, plan, progress_callback=None):
    """Execute an approved plan in one undo transaction, refreshing the native viewport per step."""
    doc = _assert_turn(token)
    if not isinstance(plan, list) or not 1 <= len(plan) <= 20:
        raise ValueError("A native plan must contain between 1 and 20 steps.")
    _App, Gui = _apps()
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
            if progress_callback is not None:
                progress_callback(index, len(plan), tool, "starting")
            result = _create_step(doc, tool, step.get("args", {}))
            # Recompute and repaint after every real native operation. This makes
            # approved multi-step plans visibly build in the open CAD viewport.
            doc.recompute()
            try:
                Gui.updateGui()
            except Exception:
                pass
            results.append({"step": index, **result})
            if progress_callback is not None:
                progress_callback(index, len(plan), tool, "completed")
        doc.recompute()
        try:
            Gui.updateGui()
        except Exception:
            pass
        doc.commitTransaction()
    except Exception:
        try:
            doc.abortTransaction()
            try:
                doc.recompute()
                Gui.updateGui()
            except Exception:
                pass
        finally:
            raise
    return {"success": True, "document": _doc_summary(doc), "results": results}
