#!/usr/bin/env python3
"""Prepare bounded, provenance-aware CAD/BIM lessons for the NextAI student.

Raw corpora and extracted image assets are training-only. They are never copied
into the Next3D desktop installer.
"""
from __future__ import annotations

import argparse
import base64
import itertools
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any

CAD_DATASET = "ADSKAILab/Zero-To-CAD-100k"
BIM_DATASET = "Dietmar2020/ifc-bim-alpaca-124k"
BIM_QA_DATASET = "Dietmar2020/ifc-bim-qa-dataset"

CAD_SYSTEM = (
    "You are NextAI, a CAD geometry and parametric-design specialist. "
    "Identify geometric feature families and construction order from the "
    "supplied evidence. Do not invent dimensions or constraints. Distinguish "
    "visible geometry from editable feature history. Return the requested JSON."
)
BIM_SYSTEM = (
    "You are NextAI, a Building Information Modeling and IFC specialist. "
    "Use correct BIM terminology, units, entity relationships and schema "
    "context. Distinguish a conceptual answer from an IFC model validated by "
    "software. Never claim statutory compliance without a real check."
)

FEATURES = {
    "box": "primitive_box",
    "sphere": "primitive_sphere",
    "cylinder": "primitive_cylinder",
    "cone": "primitive_cone",
    "shell": "shell",
    "extrude": "extrusion",
    "revolve": "revolution",
    "sweep": "sweep",
    "loft": "loft",
    "union": "boolean_union",
    "cut": "boolean_difference",
    "intersect": "boolean_intersection",
    "hole": "hole",
    "pushPoints": "pattern_points",
    "chamfer": "chamfer",
    "fillet": "fillet",
    "mirror": "mirror",
    "rotate": "rotation",
    "translate": "translation",
    "rect": "profile_rectangle",
    "circle": "profile_circle",
    "Workplane": "work_plane",
    "faces": "face_selection",
    "edges": "edge_selection",
}


def parse_operations(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="strict")
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, list):
        raise ValueError("CAD operation trace is not a JSON list")
    operations = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("op_name") or "").strip()
        if not name:
            continue
        args = item.get("args") or []
        keywords = item.get("keywords") or []
        params = {}
        if isinstance(keywords, list):
            for pair in keywords:
                if isinstance(pair, dict) and pair.get("arg") is not None:
                    params[str(pair["arg"])] = pair.get("value")
        operations.append({
            "sequence": index + 1,
            "feature": FEATURES.get(name, re.sub(r"[^A-Za-z0-9]+", "_", name).lower()),
            "reference_operation": name,
            "arguments": args if isinstance(args, list) else [],
            "parameters": params,
            "source_line": item.get("lineno"),
        })
    if not operations:
        raise ValueError("CAD operation trace has no usable operations")
    return operations


def cad_plan(raw_ops: Any, num_faces: Any = None) -> dict[str, Any]:
    ops = parse_operations(raw_ops)
    metadata = {}
    try:
        if num_faces is not None:
            metadata["reference_face_count"] = int(num_faces)
    except (TypeError, ValueError):
        pass
    return {
        "schema": "nextai.cad_feature_plan.v1",
        "domain": "parametric_cad",
        "reference_units": "dataset_default_units; preserve source values",
        "ordered_features": ops,
        "geometry_metadata": metadata,
        "native_execution_rule": (
            "CadQuery operations are teaching references, not native FreeCAD "
            "commands. Translate through the neutral feature plan and the "
            "NextCAD adapter; never execute this source program in the app."
        ),
        "validation_targets": [
            "recompute feature history",
            "check solid and surface topology",
            "confirm units and supplied dimensions",
            "save and reopen the native document",
        ],
    }


def _save_image(value: Any, destination: Path) -> None:
    """Save a Hugging Face Image feature without assuming it is raw bytes.

    datasets.Image normally decodes rows to PIL images. Depending on the
    dataset/viewer version it may instead yield a {bytes, path} mapping.
    Support both forms and raw encoded payloads.
    """
    import io
    from PIL import Image

    source = value
    if isinstance(value, dict):
        if value.get("bytes") is not None:
            source = value["bytes"]
        elif value.get("path"):
            source = Path(value["path"])
        else:
            raise ValueError("dataset image mapping has neither bytes nor path")
    if isinstance(source, Image.Image):
        image = source
        image.load()
        image.convert("RGB").save(destination, "JPEG", quality=92)
        return
    if isinstance(source, (bytes, bytearray)):
        payload = bytes(source)
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
        with Image.open(io.BytesIO(payload)) as image:
            image.convert("RGB").save(destination, "JPEG", quality=92)
        return
    if isinstance(source, Path):
        if not source.is_file():
            raise ValueError(f"dataset image path does not exist: {source}")
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image.convert("RGB").save(destination, "JPEG", quality=92)
        return
    if isinstance(source, str):
        candidate = Path(source)
        if candidate.is_file():
            _save_image(candidate, destination)
            return
        try:
            payload = base64.b64decode(source, validate=True)
        except Exception as exc:
            raise ValueError("dataset image string is neither a path nor valid base64") from exc
        _save_image(payload, destination)
        return
    raise ValueError(f"unsupported dataset image value: {type(value).__name__}")


def make_cad_records(row: dict[str, Any], asset_root: Path, split: str, index: int) -> list[dict[str, Any]]:
    plan = cad_plan(row.get("cadquery_ops_json"), row.get("num_faces"))
    uuid = re.sub(r"[^A-Za-z0-9_-]", "_", str(row.get("uuid") or index))[:72]
    folder = asset_root / "cad" / split / uuid
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    # The dataset's eight-view representation is preserved for visual learning.
    for view_index in range(8):
        destination = folder / f"view_{view_index}.jpg"
        _save_image(row.get(f"image_{view_index}"), destination)
        paths.append(str(destination))

    feature_families = []
    for operation in plan["ordered_features"]:
        feature = operation["feature"]
        if feature not in feature_families:
            feature_families.append(feature)
    visual_target = {
        "schema": "nextai.cad_visual_feature_summary.v1",
        "feature_families": feature_families,
        "likely_construction_order": [x["feature"] for x in plan["ordered_features"]],
        "exact_dimensions": "unknown unless explicitly supplied",
        "rule": "Do not measure exact dimensions from unscaled rendered views.",
    }
    visual_prompt = (
        "Eight views show the same synthetic parametric CAD component. Identify "
        "the feature families and likely construction order. Do not guess exact "
        "dimensions from pixels. Return a JSON feature summary."
    )
    trace_prompt = (
        "Convert this reference construction trace to the neutral NextAI CAD "
        "feature-plan schema. Preserve order and all explicit parameter values. "
        "Do not execute source code or claim these are native FreeCAD commands.\n"
        + json.dumps(plan["ordered_features"], ensure_ascii=False)
    )
    common = {
        "source": CAD_DATASET,
        "license": "Apache-2.0",
        "source_split": split,
    }
    return [
        {
            "record_id": f"cad-visual-{uuid}",
            "domain": "cad_visual",
            "system": CAD_SYSTEM,
            "prompt": visual_prompt,
            "completion": json.dumps(visual_target, ensure_ascii=False),
            "images": paths,
            **common,
        },
        {
            "record_id": f"cad-trace-{uuid}",
            "domain": "cad_feature_trace",
            "system": CAD_SYSTEM,
            "prompt": trace_prompt,
            "completion": json.dumps(plan, ensure_ascii=False),
            "images": [],
            **common,
        },
    ]


def parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def make_bim_record(row: dict[str, Any], record_id: str) -> dict[str, Any] | None:
    try:
        score = float(row.get("score"))
    except (TypeError, ValueError):
        return None
    metadata = parse_metadata(row.get("metadata"))
    source_label = str(row.get("source") or "").strip()
    # The published dataset example uses source="validated-synthetic" and
    # often has no metadata.validated field. Accept that explicit provenance
    # label (or an explicit metadata flag), but do not treat every row as
    # independently verified by NextAI.
    source_claims_validation = "validated" in source_label.lower()
    metadata_claims_validation = metadata.get("validated") is True
    if not (source_claims_validation or metadata_claims_validation) or score < 4.5:
        return None
    instruction = str(row.get("instruction") or "").strip()
    extra = str(row.get("input") or "").strip()
    answer = str(row.get("output") or "").strip()
    if not instruction or not answer:
        return None
    return {
        "record_id": record_id,
        "domain": "bim_ifc_knowledge",
        "system": BIM_SYSTEM,
        "prompt": instruction + ("\n\n" + extra if extra else ""),
        "completion": answer,
        "images": [],
        "source": BIM_DATASET,
        "source_record_label": source_label,
        "license": "MIT",
        "source_validated_claim": True,
        "source_score": score,
        "source_metadata": metadata,
    }


def make_bim_qa_record(row: dict[str, Any], record_id: str, split: str) -> dict[str, Any] | None:
    question = str(row.get("question") or "").strip()
    answer = str(row.get("answer") or "").strip()
    if not question or not answer:
        return None
    return {
        "record_id": record_id,
        "domain": "bim_ifc_qa",
        "system": BIM_SYSTEM,
        "prompt": question,
        "completion": answer,
        "images": [],
        "source": BIM_QA_DATASET,
        "license": "CC-BY-4.0",
        "attribution": "Dietmar2020, IFC BIM Question-Answering Dataset",
        "source_split": split,
    }


def load_stream(repo: str, split: str, limit: int, seed: int):
    from datasets import load_dataset
    dataset = load_dataset(repo, split=split, streaming=True)
    if split == "train":
        dataset = dataset.shuffle(seed=seed, buffer_size=5000)
    return itertools.islice(iter(dataset), max(0, limit))


def read_native(path: str | None, domain: str) -> list[dict[str, Any]]:
    if not path:
        return []
    result = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row.get("messages"), list) and len(row["messages"]) >= 2:
                result.append({
                    "record_id": str(row.get("record_id") or f"{domain}-{index}"),
                    "domain": domain,
                    "messages": row["messages"],
                    "images": [],
                    "source": "Next3D native training trace",
                    "license": "see attached native source record",
                })
    return result


def make_synthetic_curriculum() -> list[dict[str, Any]]:
    """Small, original, unit-aware lessons that cover gaps in public corpora."""
    lessons = [
        {
            "domain": "cad_2d_drafting",
            "system": CAD_SYSTEM,
            "prompt": "Create a neutral 2D drafting plan for a rectangular room 6000 mm by 4000 mm. Use the lower-left corner as origin, millimetres, a closed outline, four explicit dimensions, separate wall and dimension layers, and no invented doors or windows.",
            "completion": {
                "schema": "nextai.2d_drawing_plan.v1",
                "units": "mm",
                "origin": [0, 0],
                "entities": [
                    {"type": "line", "layer": "A-WALL", "start": [0, 0], "end": [6000, 0]},
                    {"type": "line", "layer": "A-WALL", "start": [6000, 0], "end": [6000, 4000]},
                    {"type": "line", "layer": "A-WALL", "start": [6000, 4000], "end": [0, 4000]},
                    {"type": "line", "layer": "A-WALL", "start": [0, 4000], "end": [0, 0]},
                ],
                "dimensions": [
                    {"axis": "x", "value": 6000, "unit": "mm"},
                    {"axis": "y", "value": 4000, "unit": "mm"},
                ],
                "layers": ["A-WALL", "A-DIMS"],
                "assumptions": [],
                "validation": ["closed outline", "opposite sides parallel", "dimensions match user specification"],
            },
        },
        {
            "domain": "cad_2d_drafting",
            "system": CAD_SYSTEM,
            "prompt": "Explain how to organise a technical floor-plan drawing with layers, line types, dimensions, annotations and hatches. Return a concise structured drafting standard without assuming a particular CAD application's commands.",
            "completion": {
                "schema": "nextai.drafting_practice.v1",
                "layers": {
                    "A-WALL": "primary wall outlines",
                    "A-DOOR": "door leaves and swing arcs",
                    "A-WIND": "window frames and openings",
                    "A-DIMS": "dimensions and extension lines",
                    "A-TEXT": "room names and notes",
                    "A-HATCH": "material poche and cut fills",
                },
                "rules": [
                    "Use model geometry at full scale and set paper scale in the sheet/view.",
                    "Keep annotation separate from model geometry.",
                    "Use consistent lineweight hierarchy and readable text sizes.",
                    "Dimension from stable datums and avoid duplicate dimensions.",
                    "Use closed boundaries for hatch regions and verify no gaps.",
                    "Preserve units and drawing coordinate origin.",
                ],
            },
        },
        {
            "domain": "cad_parametric_sketch",
            "system": CAD_SYSTEM,
            "prompt": "Plan a fully constrained 2D sketch for a 120 mm by 80 mm rectangular plate with two 8 mm diameter holes on its horizontal centreline, each centre 25 mm from the nearest vertical edge. Describe geometric constraints and driving dimensions; do not generate application commands.",
            "completion": {
                "schema": "nextai.parametric_sketch_plan.v1",
                "units": "mm",
                "entities": ["four connected line segments", "two circles"],
                "geometric_constraints": [
                    "coincident endpoints at all four rectangle corners",
                    "horizontal top and bottom edges",
                    "vertical left and right edges",
                    "equal opposite side lengths",
                    "horizontal alignment of hole centres",
                    "symmetric hole centres about the plate vertical centreline",
                ],
                "driving_dimensions": [
                    {"name": "plate_width", "value": 120, "unit": "mm"},
                    {"name": "plate_height", "value": 80, "unit": "mm"},
                    {"name": "hole_diameter", "value": 8, "unit": "mm"},
                    {"name": "hole_edge_offset", "value": 25, "unit": "mm"},
                ],
                "acceptance": ["zero remaining degrees of freedom", "no conflicting constraints", "all dimensions are user-specified"],
            },
        },
        {
            "domain": "cad_parametric_sketch",
            "system": CAD_SYSTEM,
            "prompt": "Explain the difference between geometric constraints, dimensional constraints and a fully constrained parametric sketch. Give examples and describe how a feature tree depends on the sketch.",
            "completion": {
                "schema": "nextai.parametric_cad_concepts.v1",
                "geometric_constraints": ["coincident", "horizontal", "vertical", "parallel", "perpendicular", "tangent", "equal", "symmetric"],
                "dimensional_constraints": ["length", "radius", "diameter", "distance", "angle"],
                "fully_constrained": "The sketch has no remaining free degrees of freedom under its intended design constraints.",
                "feature_dependency": "A pad or pocket references the sketch; changing driving dimensions recomputes dependent features in history order.",
                "checks": ["avoid redundant constraints", "avoid conflicting constraints", "recompute after edits", "confirm the intended design intent"],
            },
        },
        {
            "domain": "cad_3d_modelling",
            "system": CAD_SYSTEM,
            "prompt": "Plan a parametric 3D plate from an explicitly dimensioned sketch: 120 mm by 80 mm, 10 mm thick, with two 8 mm through-holes and a 2 mm edge chamfer. Return an ordered neutral feature tree and validation requirements.",
            "completion": {
                "schema": "nextai.cad_feature_plan.v1",
                "units": "mm",
                "features": [
                    {"sequence": 1, "type": "constrained_sketch", "profile": "rectangle", "width": 120, "height": 80},
                    {"sequence": 2, "type": "pad", "length": 10, "source": 1},
                    {"sequence": 3, "type": "hole_pattern", "diameter": 8, "count": 2, "through_all": True, "source": 1},
                    {"sequence": 4, "type": "chamfer", "distance": 2, "target": "specified external edges"},
                ],
                "validation": ["valid solid", "hole axes and spacing match the sketch", "chamfer target edges identified", "recompute and save/reopen"],
            },
        },
        {
            "domain": "cad_documentation",
            "system": CAD_SYSTEM,
            "prompt": "Describe the minimum information needed to produce a manufacturing drawing from a parametric part: orthographic views, sections, dimensions, tolerances, material, scale, projection method and revision information.",
            "completion": {
                "schema": "nextai.technical_drawing_checklist.v1",
                "views": ["front", "top", "side", "isometric reference", "section where internal geometry is hidden"],
                "annotations": ["overall and functional dimensions", "tolerances", "surface finish where specified", "material", "part identifier"],
                "sheet": ["units", "scale", "projection convention", "title block", "revision", "date", "author or responsible role"],
                "quality_checks": ["no contradictory dimensions", "no missing critical dimensions", "views agree with the 3D model", "printable text and lineweights"],
            },
        },
        {
            "domain": "bim_concepts",
            "system": BIM_SYSTEM,
            "prompt": "Explain the difference between a BIM spatial hierarchy, a building element, an element type and an instance. Use a small building example and show how storeys, walls, doors and rooms relate.",
            "completion": {
                "schema": "nextai.bim_spatial_model.v1",
                "hierarchy": ["project", "site", "building", "building storey", "space or room"],
                "elements": [
                    {"class": "wall", "role": "physical building element", "level": "Level 1"},
                    {"class": "door", "role": "opening-filling element hosted by a wall opening", "level": "Level 1"},
                    {"class": "room", "role": "spatial object bounded by building elements", "level": "Level 1"},
                ],
                "type_instance": "A type stores reusable characteristics; an instance is a placed occurrence with its own identity and placement.",
                "checks": ["elements assigned to the correct storey", "host/opening relationships preserved", "room boundaries are closed and consistent"],
            },
        },
        {
            "domain": "bim_ifc_relationships",
            "system": BIM_SYSTEM,
            "prompt": "Describe the standard IFC relationship pattern for a wall with an opening filled by a window. State the entities and relationship direction in order.",
            "completion": {
                "schema": "nextai.ifc_relationship_lesson.v1",
                "sequence": [
                    {"entity": "IfcWall", "role": "host building element"},
                    {"entity": "IfcOpeningElement", "role": "opening in the wall"},
                    {"entity": "IfcWindow", "role": "element filling the opening"},
                ],
                "relationships": [
                    {"entity": "IfcRelVoidsElement", "relating": "IfcWall", "related": "IfcOpeningElement"},
                    {"entity": "IfcRelFillsElement", "relating": "IfcOpeningElement", "related": "IfcWindow"},
                ],
                "checks": ["opening is spatially contained by its host", "filling element uses the opening relationship", "geometry and placements are consistent"],
            },
        },
        {
            "domain": "bim_documentation",
            "system": BIM_SYSTEM,
            "prompt": "Plan a BIM documentation set for a two-storey residential building. Include views, sheets, schedules and model coordination information. Do not invent building dimensions.",
            "completion": {
                "schema": "nextai.bim_documentation_plan.v1",
                "views": ["Level 1 floor plan", "Level 2 floor plan", "roof plan", "building elevations", "building sections", "overall 3D view"],
                "schedules": ["doors", "windows", "rooms", "walls and material layers", "floors and roofs"],
                "sheets": ["cover and general notes", "plans", "elevations", "sections", "schedules"],
                "coordination": ["levels and grids consistent", "hosted openings coordinated", "view annotations legible", "model warnings reviewed", "IFC export checked"],
            },
        },
        {
            "domain": "construction_workflows",
            "system": BIM_SYSTEM,
            "prompt": "Describe a model-based construction information sequence from design development through coordination, issue resolution, documentation and handover. Distinguish a planned sequence from verified site progress.",
            "completion": {
                "schema": "nextai.construction_information_workflow.v1",
                "stages": [
                    "agree project coordinates, levels, grids and information requirements",
                    "develop architectural, structural and MEP models",
                    "coordinate model interfaces and identify clashes",
                    "assign issues, owners, due dates and resolution evidence",
                    "revise coordinated models and update drawings and schedules",
                    "prepare approved exchange and handover deliverables",
                ],
                "rule": "A model sequence is not evidence that construction work happened. Site progress requires separately verified project records.",
            },
        },
    ]
    # Expand the authored curriculum with deterministic parameter variations.
    # These are neutral design-intent lessons, not native execution traces.
    for index in range(80):
        width = 4000 + (index % 10) * 400
        height = 3000 + (index % 8) * 300
        lessons.append({
            "domain": "cad_2d_drafting",
            "system": CAD_SYSTEM,
            "prompt": (
                f"Create a neutral 2D room outline, {width} mm wide by {height} mm high. "
                "Use the lower-left corner as the origin, draw a closed four-edge outline, "
                "put geometry on A-WALL and dimensions on A-DIMS, and return exact dimensions."
            ),
            "completion": {
                "schema": "nextai.2d_drawing_plan.v1",
                "units": "mm",
                "origin": [0, 0],
                "outline": [[0, 0], [width, 0], [width, height], [0, height], [0, 0]],
                "layers": {"geometry": "A-WALL", "dimensions": "A-DIMS"},
                "dimensions": [{"axis": "x", "value": width}, {"axis": "y", "value": height}],
                "validation": ["closed polyline", "opposite edges parallel", "dimensions exact"],
            },
        })

        plate_width = 80 + (index % 9) * 10
        plate_height = 50 + (index % 7) * 5
        hole_diameter = 6 + (index % 4) * 2
        edge_offset = 15 + (index % 5) * 2
        lessons.append({
            "domain": "cad_parametric_sketch",
            "system": CAD_SYSTEM,
            "prompt": (
                f"Plan a fully constrained {plate_width} mm by {plate_height} mm plate sketch "
                f"with two {hole_diameter} mm diameter holes on the horizontal centreline, "
                f"each centre {edge_offset} mm from its nearest vertical edge. State the "
                "geometric constraints and driving dimensions; no app-specific code."
            ),
            "completion": {
                "schema": "nextai.parametric_sketch_plan.v1",
                "units": "mm",
                "profile": {"type": "rectangle", "width": plate_width, "height": plate_height},
                "holes": [
                    {"centre": [edge_offset, plate_height / 2], "diameter": hole_diameter},
                    {"centre": [plate_width - edge_offset, plate_height / 2], "diameter": hole_diameter},
                ],
                "constraints": ["coincident corners", "horizontal and vertical edges", "equal opposite sides",
                                "hole centres horizontal", "holes symmetric about plate centreline"],
                "driving_dimensions": {"width": plate_width, "height": plate_height,
                                       "hole_diameter": hole_diameter, "edge_offset": edge_offset},
                "acceptance": ["zero remaining degrees of freedom", "no conflicting constraints"],
            },
        })

        length = 100 + (index % 8) * 10
        breadth = 60 + (index % 6) * 5
        thickness = 8 + (index % 5) * 2
        diameter = 6 + (index % 4) * 2
        chamfer = 1 + (index % 3)
        lessons.append({
            "domain": "cad_3d_modelling",
            "system": CAD_SYSTEM,
            "prompt": (
                f"Plan a parametric plate {length} mm by {breadth} mm by {thickness} mm, "
                f"with two {diameter} mm through-holes and a {chamfer} mm chamfer on the "
                "specified outside top edges. Return the feature order and checks."
            ),
            "completion": {
                "schema": "nextai.cad_feature_plan.v1",
                "units": "mm",
                "features": [
                    {"step": 1, "operation": "constrained_rectangle", "width": length, "height": breadth},
                    {"step": 2, "operation": "pad", "length": thickness},
                    {"step": 3, "operation": "two_through_holes", "diameter": diameter},
                    {"step": 4, "operation": "chamfer", "distance": chamfer,
                     "target": "user-specified outside top edges"},
                ],
                "validation": ["valid solid", "hole count is two", "dimensions preserved", "recompute and reopen"],
            },
        })

        storeys = 2 + (index % 4)
        levels = [{"name": f"Level {n + 1}", "elevation_mm": n * 3000} for n in range(storeys)]
        lessons.append({
            "domain": "bim_concepts",
            "system": BIM_SYSTEM,
            "prompt": f"Describe a BIM spatial hierarchy for a {storeys}-storey building. Explain project, site, building, storeys, spaces and placed element instances.",
            "completion": {
                "schema": "nextai.bim_spatial_model.v1",
                "hierarchy": ["project", "site", "building", "building storey", "space"],
                "levels": levels,
                "principle": "Building elements are assigned to their spatial context; a type is reusable definition data and an instance is a specific placed occurrence.",
                "checks": ["unique element identities", "correct storey assignment", "consistent elevations and units"],
            },
        })

        fill_type = "IfcDoor" if index % 2 == 0 else "IfcWindow"
        fill_relation = "IfcRelFillsElement"
        lessons.append({
            "domain": "bim_ifc_relationships",
            "system": BIM_SYSTEM,
            "prompt": f"Explain the IFC relationship chain for an IfcWall containing an IfcOpeningElement filled by an {fill_type}. State relationship direction.",
            "completion": {
                "schema": "nextai.ifc_relationship_lesson.v1",
                "entities": ["IfcWall", "IfcOpeningElement", fill_type],
                "relationships": [
                    {"entity": "IfcRelVoidsElement", "relating": "IfcWall", "related": "IfcOpeningElement"},
                    {"entity": fill_relation, "relating": "IfcOpeningElement", "related": fill_type},
                ],
                "checks": ["opening linked to host wall", "filling linked to opening", "placements and geometry consistent"],
            },
        })

        sheet_count = 4 + (index % 5)
        lessons.append({
            "domain": "bim_documentation",
            "system": BIM_SYSTEM,
            "prompt": f"Prepare a BIM documentation checklist for a {storeys}-storey building with {sheet_count} drawing sheets. Include views, schedules and coordination checks; do not invent dimensions.",
            "completion": {
                "schema": "nextai.bim_documentation_plan.v1",
                "views": ["floor plans by storey", "roof plan", "elevations", "sections", "overall 3D view"],
                "schedules": ["doors", "windows", "rooms", "walls", "floors and roofs"],
                "sheet_count_target": sheet_count,
                "coordination": ["levels and grids match", "hosted openings coordinated", "annotations legible", "model warnings reviewed", "IFC export checked"],
            },
        })

    for index in range(32):
        drawing_scale = ["1:50", "1:100", "1:20", "1:10"][index % 4]
        lessons.append({
            "domain": "cad_documentation",
            "system": CAD_SYSTEM,
            "prompt": f"Create a technical drawing checklist for a manufactured component at drawing scale {drawing_scale}. Include projection views, dimensions, tolerances only when specified, units, material and revision metadata.",
            "completion": {
                "schema": "nextai.technical_drawing_checklist.v1",
                "scale": drawing_scale,
                "views": ["front", "top", "side", "isometric reference", "section when internal geometry requires it"],
                "annotations": ["specified functional dimensions", "specified tolerances", "material", "part identifier"],
                "sheet_metadata": ["units", "projection method", "title block", "revision", "date"],
                "checks": ["views consistent with the model", "no contradictory dimensions", "critical dimensions present"],
            },
        })

    for index in range(24):
        stages = [
            "confirm project coordinates, levels, grids and information requirements",
            "develop architecture, structure and MEP models",
            "coordinate model interfaces and identify clashes",
            "assign issues with owners and due dates",
            "resolve issues and update coordinated models",
            "publish approved documentation and handover data",
        ]
        shift = index % len(stages)
        ordered = stages[shift:] + stages[:shift]
        lessons.append({
            "domain": "construction_workflows",
            "system": BIM_SYSTEM,
            "prompt": "Describe a model-based coordination and construction information workflow. Distinguish design/model milestones from verified site progress.",
            "completion": {
                "schema": "nextai.construction_information_workflow.v1",
                "stages": ordered,
                "rule": "A model or planned sequence does not prove that site work happened. Site progress requires independent project evidence.",
            },
        })

    # Building-scale BIM curriculum: floor plans, structural systems, MEP,
    # coordination and quantities. These are neutral information models,
    # never claims of structural adequacy or statutory compliance.
    for index in range(24):
        shell_width = 14000 + (index % 4) * 1000
        shell_depth = 10000 + (index % 3) * 1000
        mid_x = shell_width // 2
        south_depth = 4500 + (index % 3) * 250
        north_depth = shell_depth - south_depth
        x1, x2, x3 = shell_width * 2 // 7, shell_width * 4 // 7, shell_width * 5 // 7
        upper_bath_y = shell_depth - north_depth // 3
        ensuite_x = x3 + (shell_width - x3) // 2
        lessons.append({
            "domain": "bim_architectural_floorplan",
            "system": BIM_SYSTEM,
            "prompt": (
                f"Plan a single-storey three-bedroom, two-bathroom home in a "
                f"{shell_width} mm by {shell_depth} mm rectangular shell. One "
                "bathroom must be ensuite to the master bedroom. Return a "
                "dimensioned room-program layout, room adjacency and door/window "
                "relationships. Keep every room inside the shell, avoid overlap, "
                "preserve the stated dimensions and list any design assumptions."
            ),
            "completion": {
                "schema": "nextai.bim_floorplan_program.v1",
                "units": "mm",
                "shell": {"width": shell_width, "depth": shell_depth, "origin": [0, 0]},
                "design_status": "conceptual layout proposal; verify access, local regulations and user preferences before issue",
                "room_program": [
                    {"name": "Living and dining", "zone": "south", "minimum_area_m2": 24},
                    {"name": "Kitchen", "zone": "south-east", "minimum_area_m2": 12},
                    {"name": "Bedroom 2", "zone": "north-west", "minimum_area_m2": 12},
                    {"name": "Bedroom 3", "zone": "north-centre", "minimum_area_m2": 12},
                    {"name": "Master bedroom", "zone": "north-east", "minimum_area_m2": 14},
                    {"name": "Shared bathroom", "zone": "near hall", "minimum_area_m2": 4},
                    {"name": "Master ensuite", "zone": "inside master suite", "minimum_area_m2": 4},
                    {"name": "Hall and circulation", "zone": "central", "minimum_clear_width_mm": 1200},
                ],
                "room_rectangles": [
                    {"name": "Living and dining", "bounds": [0, 0, mid_x, south_depth]},
                    {"name": "Kitchen", "bounds": [mid_x, 0, shell_width, south_depth]},
                    {"name": "Bedroom 2", "bounds": [0, south_depth, x1, shell_depth]},
                    {"name": "Bedroom 3", "bounds": [x1, south_depth, x2, shell_depth]},
                    {"name": "Hall and circulation", "bounds": [x2, south_depth, x3, upper_bath_y]},
                    {"name": "Shared bathroom", "bounds": [x2, upper_bath_y, x3, shell_depth]},
                    {"name": "Master bedroom", "bounds": [x3, south_depth, shell_width, upper_bath_y]},
                    {"name": "Master ensuite", "bounds": [x3, upper_bath_y, ensuite_x, shell_depth]},
                    {"name": "Master dressing", "bounds": [ensuite_x, upper_bath_y, shell_width, shell_depth]},
                ],
                "door_centres": [
                    {"connects": ["entrance", "Living and dining"], "point": [mid_x, 0]},
                    {"connects": ["Living and dining", "Bedroom 2"], "point": [x1 // 2, south_depth]},
                    {"connects": ["Bedroom 3", "Hall and circulation"], "point": [x2, south_depth + (upper_bath_y - south_depth) // 2]},
                    {"connects": ["Kitchen", "Hall and circulation"], "point": [(x2 + x3) // 2, south_depth]},
                    {"connects": ["Hall and circulation", "Shared bathroom"], "point": [(x2 + x3) // 2, upper_bath_y]},
                    {"connects": ["Kitchen", "Master bedroom"], "point": [(x3 + shell_width) // 2, south_depth]},
                    {"connects": ["Master bedroom", "Master ensuite"], "point": [(x3 + ensuite_x) // 2, upper_bath_y]},
                    {"connects": ["Master bedroom", "Master dressing"], "point": [(ensuite_x + shell_width) // 2, upper_bath_y]},
                ],
                "window_zones": ["living south facade", "kitchen east facade", "bedroom 2 west facade", "bedroom 3 north facade", "master east facade", "bathrooms with privacy glazing"],
                "layout_rules": [
                    "all room boundaries remain within the external shell",
                    "room polygons must not overlap",
                    "all habitable rooms require an appropriate external opening",
                    "each bathroom requires access and ventilation provision",
                    "the master ensuite must connect to the master suite",
                    "circulation must connect the entrance to the bedroom and shared spaces",
                ],
                "required_relationships": [
                    {"from": "entrance", "to": "living and dining", "type": "door"},
                    {"from": "living and dining", "to": "hall and circulation", "type": "door"},
                    {"from": "hall and circulation", "to": "bedroom 2", "type": "door"},
                    {"from": "hall and circulation", "to": "bedroom 3", "type": "door"},
                    {"from": "hall and circulation", "to": "shared bathroom", "type": "door"},
                    {"from": "hall and circulation", "to": "master bedroom", "type": "door"},
                    {"from": "master bedroom", "to": "master ensuite", "type": "door"},
                ],
                "unresolved_inputs": ["site orientation", "setbacks", "wall thickness", "door and window sizes", "accessibility requirements", "local planning rules"],
                "validation": ["shell dimensions exact", "no room overlap", "room adjacency graph connected", "door relationships valid", "areas and circulation checked"],
            },
        })

        grid_x = [0, 6000, 12000]
        grid_y = [0, 5000, 10000]
        lessons.append({
            "domain": "bim_structural_model",
            "system": BIM_SYSTEM,
            "prompt": (
                "Create a neutral structural BIM framing plan for a three-by-three "
                "column grid with X gridlines A-C at 6000 mm spacing and Y gridlines "
                "1-3 at 5000 mm spacing. Include columns, beams, floor slabs and "
                "storey relationships. Do not size members or claim structural adequacy."
            ),
            "completion": {
                "schema": "nextai.bim_structural_frame.v1",
                "units": "mm",
                "grid": {"x": [{"name": name, "coordinate": value} for name, value in zip(["A", "B", "C"], grid_x)],
                         "y": [{"name": name, "coordinate": value} for name, value in zip(["1", "2", "3"], grid_y)]},
                "storeys": [{"name": "Ground", "elevation": 0}, {"name": "Level 1", "elevation": 3000}],
                "columns": [{"grid": f"{x}{y}", "from": "Ground", "to": "Level 1"} for x in ["A", "B", "C"] for y in ["1", "2", "3"]],
                "beams": [{"grid_line": line, "direction": direction} for line in ["A", "B", "C", "1", "2", "3"] for direction in ["primary framing"]],
                "slabs": [{"storey": "Level 1", "bounded_by": "beam grid bays"}],
                "checks": ["column locations match grid intersections", "beam endpoints connect to intended supports", "slab boundaries align with framing bays", "levels and units consistent"],
                "not_performed": ["member sizing", "load analysis", "reinforcement design", "code compliance"],
            },
        })

        system_type = ["domestic cold water", "sanitary drainage", "HVAC supply air", "electrical containment"][index % 4]
        lessons.append({
            "domain": "bim_mep_systems",
            "system": BIM_SYSTEM,
            "prompt": (
                f"Plan a BIM information model for a {system_type} system in a "
                "multi-room building. Identify equipment, terminals, distribution "
                "segments, connectors, spaces and the required system relationships. "
                "Do not invent pipe diameters, cable sizes, airflow, gradients or loads."
            ),
            "completion": {
                "schema": "nextai.bim_mep_system_plan.v1",
                "system_type": system_type,
                "objects": ["source equipment or panel", "distribution segments", "connectors", "terminal devices", "served spaces"],
                "relationships": ["segments connect through compatible ports", "terminals belong to the correct system", "equipment and terminals are assigned to relevant spaces"],
                "required_properties": ["system identifier", "service type", "level", "location", "manufacturer data when supplied", "design flow or load only when specified"],
                "missing_design_inputs": ["design criteria", "equipment capacities", "pipe/cable/duct sizes", "routing clearances", "applicable standard"],
                "validation": ["connectivity graph has no unintended open ends", "system classification is consistent", "units and levels are valid"],
            },
        })

        lessons.append({
            "domain": "bim_coordination",
            "system": BIM_SYSTEM,
            "prompt": (
                "Review a coordination issue where an HVAC duct intersects a "
                "structural beam. Explain how to classify the issue, record evidence, "
                "assign responsibility and verify resolution without silently moving "
                "either element."
            ),
            "completion": {
                "schema": "nextai.bim_coordination_issue.v1",
                "issue_type": "potential hard clash",
                "participants": ["HVAC duct", "structural beam"],
                "workflow": ["detect using model geometry", "confirm clash tolerance and clearance rules", "capture viewpoint and element identifiers", "assign responsible discipline", "propose alternatives", "obtain approval", "revise native model", "rerun coordination check", "close with evidence"],
                "issue_fields": ["issue_id", "status", "priority", "responsible_party", "due_date", "element_ids", "viewpoint", "description", "resolution_evidence"],
                "safety_rule": "Do not move structural or MEP elements automatically; preserve design intent and require approval.",
            },
        })

        lessons.append({
            "domain": "bim_quantities",
            "system": BIM_SYSTEM,
            "prompt": (
                "Prepare a BIM quantity schedule for walls, doors, windows, floors "
                "and rooms. Explain which quantities should be read from native model "
                "properties and how missing or unclassified elements should be reported."
            ),
            "completion": {
                "schema": "nextai.bim_quantity_schedule.v1",
                "schedule_fields": ["element_id", "ifc_class", "type_mark", "storey", "material", "count", "length", "area", "volume", "unit", "source_property"],
                "rules": ["read quantities from validated native geometry and properties", "state measurement rules and units", "exclude voids only according to the selected measurement rule", "report missing classifications instead of guessing", "keep type and instance quantities distinct"],
                "validation": ["schedule totals reconcile with selected model elements", "units are consistent", "duplicate element identifiers are rejected", "unclassified elements appear in an exceptions list"],
            },
        })

        lessons.append({
            "domain": "construction_information",
            "system": BIM_SYSTEM,
            "prompt": (
                "Create a construction information handover checklist from a "
                "coordinated BIM model. Include asset data, spaces, systems, "
                "maintainable equipment, document links and issue status."
            ),
            "completion": {
                "schema": "nextai.construction_handover.v1",
                "deliverables": ["approved native model", "validated IFC exchange", "asset register", "space register", "equipment and system schedules", "operation and maintenance document references", "closed/open issue register", "revision and approval history"],
                "checks": ["required asset fields complete", "unique identifiers preserved", "document links resolve", "open issues clearly disclosed", "exchange model validates against agreed requirements"],
                "rule": "A design model is not an as-built record unless field changes and approvals have been verified.",
            },
        })

    records = []
    for index, lesson in enumerate(lessons):
        completion = lesson["completion"]
        if not isinstance(completion, str):
            completion = json.dumps(completion, ensure_ascii=False)
        records.append({
            "record_id": f"next3d-synthetic-{index + 1:03d}",
            "domain": lesson["domain"],
            "system": lesson["system"],
            "prompt": lesson["prompt"],
            "completion": completion,
            "images": [],
            "source": "Next3D original synthetic curriculum",
            "license": "project-authored",
        })
    return records


def sample_balanced(groups: dict[str, list[dict[str, Any]]], limit: int, seed: int) -> list[dict[str, Any]]:
    weights = {
        "cad_visual": 0.12,
        "cad_feature_trace": 0.12,
        "cad_2d_drafting": 0.12,
        "cad_parametric_sketch": 0.12,
        "cad_3d_modelling": 0.10,
        "cad_documentation": 0.07,
        "bim_ifc_knowledge": 0.12,
        "bim_ifc_qa": 0.06,
        "bim_concepts": 0.06,
        "bim_ifc_relationships": 0.05,
        "bim_documentation": 0.03,
        "construction_workflows": 0.03,
        "bim_architectural_floorplan": 0.08,
        "bim_structural_model": 0.08,
        "bim_mep_systems": 0.07,
        "bim_coordination": 0.06,
        "bim_quantities": 0.04,
        "construction_information": 0.04,
        "nextcad_native": 0.05,
        "nextbim_native": 0.05,
    }
    pools = {key: list(rows) for key, rows in groups.items() if rows}
    if not pools or limit <= 0:
        return []
    rng = random.Random(seed)
    selected = []
    while pools and len(selected) < limit:
        remaining = limit - len(selected)
        total_weight = sum(weights.get(key, 1.0) for key in pools)
        exact = {key: remaining * weights.get(key, 1.0) / total_weight for key in pools}
        quotas = {key: int(value) for key, value in exact.items()}
        spare = remaining - sum(quotas.values())
        for key in sorted(pools, key=lambda item: exact[item] - quotas[item], reverse=True):
            if spare <= 0:
                break
            quotas[key] += 1
            spare -= 1
        progress = 0
        for key in list(pools):
            count = min(len(pools[key]), quotas.get(key, 0))
            if count <= 0:
                continue
            indices = set(rng.sample(range(len(pools[key])), count))
            selected.extend(row for index, row in enumerate(pools[key]) if index in indices)
            pools[key] = [row for index, row in enumerate(pools[key]) if index not in indices]
            progress += count
            if not pools[key]:
                del pools[key]
        if progress == 0:
            # Defensive fallback if rounding ever produces no quota.
            key = max(pools, key=lambda item: weights.get(item, 1.0))
            count = min(remaining, len(pools[key]))
            selected.extend(rng.sample(pools[key], count))
            del pools[key]
    rng.shuffle(selected)
    return selected


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    out = Path(args.output_dir).resolve()
    assets = out / "assets"
    groups = {
        "cad_visual": [], "cad_feature_trace": [], "cad_2d_drafting": [],
        "cad_parametric_sketch": [], "cad_3d_modelling": [], "cad_documentation": [],
        "bim_ifc_knowledge": [], "bim_ifc_qa": [], "bim_concepts": [],
        "bim_ifc_relationships": [], "bim_documentation": [],
        "construction_workflows": [], "bim_architectural_floorplan": [],
        "bim_structural_model": [], "bim_mep_systems": [], "bim_coordination": [],
        "bim_quantities": [], "construction_information": [],
        "nextcad_native": [], "nextbim_native": [],
    }
    validation, tests, quarantine = [], [], []
    counts = Counter()

    cad_limits = [
        ("train", args.max_cad_train, "train"),
        ("validation", args.max_cad_validation, "validation"),
        ("test", args.max_cad_test, "test"),
    ]
    for source_split, maximum, target_split in cad_limits:
        for index, row in enumerate(load_stream(CAD_DATASET, source_split, maximum, args.seed)):
            try:
                records = make_cad_records(row, assets, target_split, index)
                if target_split == "train":
                    for record in records:
                        groups[record["domain"]].append(record)
                elif target_split == "validation":
                    validation.extend(records)
                else:
                    tests.extend(records)
                counts[f"cad_{target_split}_rows"] += 1
            except Exception as exc:
                quarantine.append({
                    "source": CAD_DATASET, "split": source_split, "row": index,
                    "reason": str(exc),
                })

    for split, maximum in (("train", args.max_bim_train), ("validation", args.max_bim_validation)):
        for index, row in enumerate(load_stream(BIM_DATASET, split, maximum, args.seed)):
            record = make_bim_record(row, f"bim-{split}-{index}")
            if record is None:
                counts[f"bim_{split}_rejected"] += 1
                continue
            counts[f"bim_{split}_accepted"] += 1
            if split == "train":
                groups["bim_ifc_knowledge"].append(record)
            else:
                validation.append(record)

    for index, row in enumerate(load_stream(BIM_QA_DATASET, "train", args.max_ifcqa_train, args.seed)):
        record = make_bim_qa_record(row, f"ifc-qa-train-{index}", "train")
        if record:
            groups["bim_ifc_qa"].append(record)
    for index, row in enumerate(load_stream(BIM_QA_DATASET, "test", args.max_ifcqa_test, args.seed)):
        record = make_bim_qa_record(row, f"ifc-qa-test-{index}", "test")
        if record:
            tests.append(record)

    groups["nextcad_native"] = read_native(args.nextcad_native, "nextcad_native")
    groups["nextbim_native"] = read_native(args.nextbim_native, "nextbim_native")
    for lesson in make_synthetic_curriculum():
        groups[lesson["domain"]].append(lesson)
    train = sample_balanced(groups, args.max_mixed_train, args.seed)
    random.Random(args.seed + 1).shuffle(validation)
    random.Random(args.seed + 2).shuffle(tests)

    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "validation.jsonl", validation[:args.max_validation])
    write_jsonl(out / "test.jsonl", tests[:args.max_test])
    write_jsonl(out / "quarantine.jsonl", quarantine)

    manifest = {
        "schema_version": 1,
        "student": "Qwen/Qwen3.5-0.8B",
        "method": "BF16 LoRA supervised fine-tuning",
        "sources": [
            {"repo": CAD_DATASET, "license": "Apache-2.0", "purpose": "CAD visual feature recognition and construction sequence"},
            {"repo": BIM_DATASET, "license": "MIT", "purpose": "IFC/BIM instruction lessons; only metadata.validated=true and score >=4.5"},
            {"repo": BIM_QA_DATASET, "license": "CC-BY-4.0", "attribution": "Dietmar2020", "purpose": "IFC/BIM conceptual QA"},
            {"repo": "Next3D original synthetic curriculum", "license": "project-authored", "purpose": "2D drafting, parametric sketches, 3D modeling, documentation, BIM concepts and construction workflows"},
        ],
        "source_counts": dict(counts),
        "train_records": len(train),
        "validation_records": min(len(validation), args.max_validation),
        "test_records": min(len(tests), args.max_test),
        "quarantined_rows": len(quarantine),
        "training_domain_counts": dict(Counter(row["domain"] for row in train)),
        "test_not_used_for_training": True,
        "raw_data_and_images_not_shipped_in_installer": True,
        "notes": [
            "CadQuery teaches reference feature semantics only; NextCAD must map to native FreeCAD tools.",
            "Exact dimensions are never inferred from unscaled image views.",
            "IFC text examples are not proof of an IFC file or BIMCraft project passing validation.",
            "The IFC dedup set is excluded from positive lessons until its generated IFC is validated.",
            "Standards remain versioned retrieval references, not copied wholesale into model weights.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-cad-train", type=int, default=2500)
    parser.add_argument("--max-cad-validation", type=int, default=250)
    parser.add_argument("--max-cad-test", type=int, default=250)
    parser.add_argument("--max-bim-train", type=int, default=30000)
    parser.add_argument("--max-bim-validation", type=int, default=3000)
    parser.add_argument("--max-ifcqa-train", type=int, default=5000)
    parser.add_argument("--max-ifcqa-test", type=int, default=1000)
    parser.add_argument("--max-mixed-train", type=int, default=24000)
    parser.add_argument("--max-validation", type=int, default=2500)
    parser.add_argument("--max-test", type=int, default=1200)
    parser.add_argument("--nextcad-native")
    parser.add_argument("--nextbim-native")
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()
    if any(value < 0 for value in (
        args.max_cad_train, args.max_cad_validation, args.max_cad_test,
        args.max_bim_train, args.max_bim_validation, args.max_ifcqa_train,
        args.max_ifcqa_test, args.max_mixed_train,
    )):
        parser.error("sample limits cannot be negative")
    print(json.dumps(prepare(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
