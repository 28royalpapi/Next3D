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
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Keep sibling training helpers importable both when this file is run directly
# and when legacy acceptance tests load it through importlib.util.spec_from_file_location.
sys.path.insert(0, str(Path(__file__).resolve().parent))

CAD_DATASET = "ADSKAILab/Zero-To-CAD-100k"
BIM_DATASET = "Dietmar2020/ifc-bim-alpaca-124k"
BIM_QA_DATASET = "Dietmar2020/ifc-bim-qa-dataset"
BUILDENG_DATASET = "Irfanuruchi/buildeng"

from buildeng_dataset import make_buildeng_record
from generate_verified_engineering_cases import FAMILY_BUILDERS, generate_cases
from nextai_master_curriculum import make_master_project_curriculum, summarize_master_curriculum_splits, separate_master_curriculum_splits
from scaled_practical_curriculum import make_scaled_curriculum_expansion, separate_scaled_curriculum_splits, summarize_scaled_curriculum

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
ENGINEERING_SYSTEM = (
    "You are NextAI, a civil, structural, hydraulic and construction engineering "
    "specialist. Show unit-consistent calculations and make the given inputs "
    "and assumptions explicit. Distinguish a bounded educational calculation "
    "from a complete design or safety approval. Never invent missing data, "
    "load values, soil parameters, code clauses or compliance status."
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
        paths.append(destination.relative_to(asset_root.parent).as_posix())

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
    # Shuffle shards deterministically. CAD rows carry multiple binary images,
    # so keep the Arrow shuffle buffer tiny: even 64 examples can exceed Arrow's
    # 2 GiB binary-offset limit when image payloads are concatenated.
    split_seed = seed + {"train": 0, "validation": 1, "test": 2}.get(split, 3)
    buffer_size = 4 if repo == CAD_DATASET else 64
    dataset = dataset.shuffle(seed=split_seed, buffer_size=buffer_size)
    return itertools.islice(iter(dataset), max(0, limit))


def read_native(
    path: str | None,
    domain: str,
    application: str,
    expected_split: str,
) -> list[dict[str, Any]]:
    if not path:
        return []
    result = []
    seen_ids = set()
    with Path(path).open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            record_id = str(row.get("record_id") or f"{domain}-{index}")
            if record_id in seen_ids:
                raise ValueError(f"Duplicate native trace record ID in {path}:{index}")
            seen_ids.add(record_id)
            if row.get("application") != application:
                raise ValueError(
                    f"Native trace {record_id} belongs to {row.get('application')!r}, expected {application!r}"
                )
            if row.get("split") != expected_split:
                raise ValueError(
                    f"Native trace {record_id} has split {row.get('split')!r}, expected {expected_split!r}; "
                    "use separate prepare_native_sft train/validation/test files"
                )
            messages = row.get("messages")
            if not isinstance(messages, list) or len(messages) < 3:
                raise ValueError(f"Native trace {record_id} has no complete system/user/assistant conversation")
            roles = [message.get("role") for message in messages if isinstance(message, dict)]
            if not {"system", "user", "assistant"}.issubset(set(roles)):
                raise ValueError(f"Native trace {record_id} is missing required conversation roles")
            source = row.get("source") or {}
            if not source.get("license") or source.get("terms_reviewed") is not True:
                raise ValueError(f"Native trace {record_id} has no reviewed source licence")
            privacy = row.get("privacy") or {}
            if privacy.get("contains_personal_data", True) and privacy.get("redaction_status") != "complete":
                raise ValueError(f"Native trace {record_id} has unredacted personal data")
            evidence = row.get("native_trace_evidence") or {}
            if evidence.get("validation_overall") not in {"passed", "passed_with_warnings"}:
                raise ValueError(f"Native trace {record_id} has no passing native-validation evidence")
            if evidence.get("round_trip_passed") is not True or evidence.get("recompute_passed") is not True:
                raise ValueError(f"Native trace {record_id} has no passing save/reopen and recompute evidence")
            if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("after_state_sha256") or "")):
                raise ValueError(f"Native trace {record_id} has no verified native after-state hash")
            try:
                operation_count = int(evidence.get("operation_count", 0))
                applied_count = int(evidence.get("applied_operation_count", 0))
                read_only_count = int(evidence.get("read_only_operation_count", 0))
            except (TypeError, ValueError):
                raise ValueError(f"Native trace {record_id} has invalid operation evidence counts")
            if operation_count < 1 or applied_count + read_only_count != operation_count:
                raise ValueError(f"Native trace {record_id} has incomplete operation evidence")
            if not re.fullmatch(r"[0-9a-f]{64}", str(evidence.get("operation_trace_sha256") or "")):
                raise ValueError(f"Native trace {record_id} has no operation-trace fingerprint")
            result.append({
                "record_id": record_id,
                "domain": domain,
                "messages": messages,
                "images": [],
                "source": source.get("source_type") or "Next3D native training trace",
                "license": source["license"],
                "attribution": source.get("attribution"),
                "source_group_sha256": source.get("source_group_sha256"),
                "application_version": row.get("application_version"),
                "adapter_schema_version": row.get("adapter_schema_version"),
                "privacy": privacy,
                "native_trace_evidence": evidence,
                "source_split": expected_split,
            })
    return result


def make_advanced_engineering_curriculum() -> list[dict[str, Any]]:
    """Generate original, unit-aware CAD/BIM/engineering lessons with varied inputs.

    These lessons teach concepts and neutral plans. They are not represented as
    native FreeCAD/BIMCraft command traces, calculations or code-compliance proof.
    """
    lessons: list[dict[str, Any]] = []

    for index in range(12):
        width = 100 + (index % 6) * 20
        height = 70 + (index % 5) * 10
        thickness = 8 + (index % 4) * 2
        hole_diameter = 6 + (index % 3) * 2
        edge_offset = 18 + (index % 4) * 3
        radius = 2 + (index % 3)
        filling = "IfcWindow" if index % 2 == 0 else "IfcDoor"
        storeys = 2 + index % 4
        span_x = 5000 + (index % 4) * 500
        span_y = 4000 + (index % 3) * 500
        floor_height = 3000 + (index % 3) * 250
        soil_depth = 5 + (index % 5) * 2
        pipe_flow = 2.0 + (index % 5) * 0.5

        lessons.append({
            "domain": "cad_2d_entity_semantics",
            "system": CAD_SYSTEM,
            "prompt": (
                f"Prepare a precise 2D CAD plate profile {width} mm by {height} mm "
                f"with two {hole_diameter} mm holes, each centre {edge_offset} mm "
                "from its nearest vertical edge. Specify entities, coordinate "
                "conventions, layers, dimensions and checks. Do not infer any "
                "undimensioned geometry."
            ),
            "completion": {
                "schema": "nextai.cad_2d_profile.v1",
                "units": "mm",
                "origin": [0, 0],
                "outline": {
                    "entity": "closed_polyline",
                    "vertices": [[0, 0], [width, 0], [width, height], [0, height]],
                    "closed": True,
                    "layer": "P-PROFILE",
                },
                "holes": [
                    {"entity": "circle", "centre": [edge_offset, height / 2], "diameter": hole_diameter, "layer": "P-HOLES"},
                    {"entity": "circle", "centre": [width - edge_offset, height / 2], "diameter": hole_diameter, "layer": "P-HOLES"},
                ],
                "dimensions": [
                    {"name": "overall_width", "value": width, "unit": "mm"},
                    {"name": "overall_height", "value": height, "unit": "mm"},
                    {"name": "hole_diameter", "value": hole_diameter, "unit": "mm"},
                    {"name": "hole_edge_offset", "value": edge_offset, "unit": "mm"},
                ],
                "layers": {"P-PROFILE": "visible plate boundary", "P-HOLES": "hole geometry", "P-DIMS": "dimensions and extension lines"},
                "validation": ["polyline closed", "two holes present", "hole centres symmetric about vertical centreline", "all dimensions preserve mm units"],
            },
        })

        lessons.append({
            "domain": "cad_coordinate_transforms",
            "system": CAD_SYSTEM,
            "prompt": (
                "Explain the difference between global and local coordinate systems "
                "in a parametric CAD model. Show how a component located at a known "
                "origin and rotated about its local Z axis is transformed, and explain "
                "why the assembly parent coordinate frame must be preserved."
            ),
            "completion": {
                "schema": "nextai.cad_coordinate_frame_lesson.v1",
                "concepts": {
                    "global_frame": "the shared project or assembly reference frame",
                    "local_frame": "a component's own origin and orthogonal axes",
                    "placement": "a rigid transform mapping local coordinates into the parent frame",
                    "rotation": "changes orientation about a specified axis and angle",
                    "translation": "changes the origin position without changing shape",
                },
                "safe_sequence": ["identify parent frame", "identify component local frame", "state units and rotation axis", "apply transform in the intended order", "inspect the transformed datum and geometry"],
                "checks": ["axes remain orthogonal", "transform order is explicit", "units are consistent", "source component geometry is not destructively modified"],
            },
        })

        lessons.append({
            "domain": "cad_parametric_features",
            "system": CAD_SYSTEM,
            "prompt": (
                f"Plan a parametric plate {width} mm by {height} mm by {thickness} mm "
                f"with two {hole_diameter} mm through-holes and a {radius} mm edge "
                "fillet. Return an editable feature sequence, dependencies and checks."
            ),
            "completion": {
                "schema": "nextai.cad_parametric_feature_tree.v1",
                "units": "mm",
                "features": [
                    {"order": 1, "feature": "constrained_sketch", "profile": "rectangle", "width": width, "height": height},
                    {"order": 2, "feature": "pad", "length": thickness, "depends_on": [1]},
                    {"order": 3, "feature": "hole", "diameter": hole_diameter, "termination": "through_all", "quantity": 2, "depends_on": [1, 2]},
                    {"order": 4, "feature": "fillet", "radius": radius, "target": "user-confirmed outer edges", "depends_on": [2, 3]},
                ],
                "design_intent": ["named driving dimensions", "fully constrained profile", "stable feature references", "editable history"],
                "validation": ["sketch solver reports intended constraint state", "one valid solid", "two through-holes", "fillet succeeds", "recompute and save/reopen"],
            },
        })

        lessons.append({
            "domain": "cad_assembly_design",
            "system": CAD_SYSTEM,
            "prompt": (
                "Plan an editable two-component mechanical assembly consisting of a "
                "base plate and a vertical support. Explain datum selection, component "
                "placement, assembly constraints and interference checks without "
                "assuming the CAD application's exact command names."
            ),
            "completion": {
                "schema": "nextai.cad_assembly_plan.v1",
                "components": [
                    {"id": "base", "role": "fixed reference component", "datum": "bottom mounting plane and central axes"},
                    {"id": "support", "role": "positioned component", "datum": "mounting face and centre plane"},
                ],
                "placement_strategy": ["ground the base in the assembly frame", "align support mounting face with base datum", "align required centre axes", "apply only the constraints needed to remove intended degrees of freedom"],
                "constraints": ["coincident mounting planes", "concentric axes where circular interfaces exist", "orientation constraint to prevent unintended rotation"],
                "checks": ["no over-constrained component", "remaining degrees of freedom are intentional", "clearance and interference tests pass", "component files and references resolve"],
            },
        })

        lessons.append({
            "domain": "cad_technical_documentation",
            "system": CAD_SYSTEM,
            "prompt": (
                "Prepare a manufacturing drawing plan for the plate described in "
                f"this task: {width} mm by {height} mm, thickness {thickness} mm, "
                f"two holes diameter {hole_diameter} mm. Include views, dimensions, "
                "tolerances, units, projection convention and revision controls. "
                "Do not invent tolerances or material."
            ),
            "completion": {
                "schema": "nextai.cad_drawing_release_plan.v1",
                "views": ["front", "top", "side", "isometric reference", "section only if needed to clarify internal features"],
                "dimensions": ["overall width", "overall height", "thickness", "hole diameter", "hole centre offsets"],
                "metadata": ["part identifier", "units mm", "scale", "projection convention confirmed by user", "revision", "material only when specified"],
                "tolerances": "use explicitly supplied tolerances or the project-approved tolerance standard; do not invent values",
                "checks": ["orthographic views agree", "dimensions are not duplicated or contradictory", "all manufacturing-critical geometry is defined", "revision status is visible"],
            },
        })

        lessons.append({
            "domain": "cad_interoperability",
            "system": CAD_SYSTEM,
            "prompt": (
                "Explain how to choose between STEP, IGES, STL, OBJ, 3MF, DXF and "
                "SVG when exchanging a CAD design. Distinguish editable boundary "
                "representation, tessellated mesh, 2D vector drawing and parametric history."
            ),
            "completion": {
                "schema": "nextai.cad_exchange_format_guide.v1",
                "formats": {
                    "STEP": "preferred neutral solid/surface product geometry exchange when supported",
                    "IGES": "legacy curve and surface exchange; validate translation quality",
                    "STL": "triangulated surface mesh for additive manufacturing and visualisation; no parametric feature history",
                    "OBJ": "mesh and optional material exchange; not a native parametric CAD history",
                    "3MF": "additive-manufacturing container with richer manufacturing metadata than basic STL",
                    "DXF": "2D drawing geometry and supported annotations",
                    "SVG": "2D vector graphics, not a general 3D solid exchange format",
                },
                "before_export": ["confirm units", "choose selected bodies or drawing", "check coordinate origin and orientation", "set mesh tolerance only for tessellated formats"],
                "after_import": ["check units and bounding dimensions", "validate solids or mesh integrity", "inspect faces, edges and surfaces", "compare with source view", "record what information did not transfer"],
            },
        })

        lessons.append({
            "domain": "bim_spatial_hierarchy",
            "system": BIM_SYSTEM,
            "prompt": (
                f"Model the information hierarchy for a {storeys}-storey building. "
                "Separate project, site, building, storeys, spaces, element types "
                "and placed instances. Explain containment and aggregation."
            ),
            "completion": {
                "schema": "nextai.bim_spatial_hierarchy.v1",
                "hierarchy": ["project", "site", "building", "building storey", "space"],
                "storeys": [{"name": f"Level {n + 1}", "elevation_mm": n * floor_height} for n in range(storeys)],
                "rules": ["spatial containers are distinct from physical elements", "elements have persistent identities", "type definitions are not placed instances", "spatial containment and element aggregation are separate relationships"],
                "validation": ["each element assigned to intended spatial context", "storey elevations and units consistent", "no duplicate global identifiers", "spaces and boundaries are valid"],
            },
        })

        lessons.append({
            "domain": "bim_type_instance_data",
            "system": BIM_SYSTEM,
            "prompt": (
                "Explain BIM type-versus-instance data using a door family. Identify "
                "which properties are reusable type properties and which belong "
                "to one placed door instance. Include identity, host and level."
            ),
            "completion": {
                "schema": "nextai.bim_type_instance_lesson.v1",
                "type_properties": ["nominal width and height", "frame construction", "manufacturer model", "fire/acoustic rating when certified"],
                "instance_properties": ["unique element identifier", "actual location and orientation", "host wall/opening", "storey", "mark", "phase and status"],
                "relationship": "Each placed instance references one reusable type definition while retaining its own identity and placement.",
                "validation": ["unique instance identifiers", "required type properties populated", "host relationship valid", "instance dimensions do not contradict type constraints"],
            },
        })

        lessons.append({
            "domain": "bim_material_properties",
            "system": BIM_SYSTEM,
            "prompt": (
                "Describe a layered wall BIM specification and its information "
                "requirements. Distinguish material identity, layer order, thickness, "
                "function and property sets. Do not invent performance ratings."
            ),
            "completion": {
                "schema": "nextai.bim_material_layer_set.v1",
                "layers": [
                    {"order": 1, "function": "external finish", "material": "user-specified", "thickness_mm": None},
                    {"order": 2, "function": "structural or backing layer", "material": "user-specified", "thickness_mm": None},
                    {"order": 3, "function": "insulation or cavity layer where specified", "material": "user-specified", "thickness_mm": None},
                    {"order": 4, "function": "internal finish", "material": "user-specified", "thickness_mm": None},
                ],
                "required_data": ["material name and classification", "layer function", "thickness and unit", "thermal/acoustic/fire properties only from verified source data"],
                "checks": ["layer order matches assembly direction", "thicknesses are positive when supplied", "total wall thickness reconciles", "property source and classification are recorded"],
            },
        })

        lessons.append({
            "domain": "bim_ifc_exchange_requirements",
            "system": BIM_SYSTEM,
            "prompt": (
                "Prepare an openBIM exchange acceptance plan for an IFC model. "
                "Explain the roles of IFC schema validation, IDS information "
                "requirements, BCF issue exchange and bSDD classification. Do not "
                "claim the file passes until validation is run."
            ),
            "completion": {
                "schema": "nextai.openbim_exchange_plan.v1",
                "ifc": "exchange data schema for building objects, geometry, properties and relationships",
                "ids": "machine-readable information delivery requirements for checking required entities and properties",
                "bcf": "issue and viewpoint exchange for coordination findings",
                "bsdd": "dictionary for consistent classifications, properties and definitions",
                "validation_stages": ["check IFC syntax/schema", "check entity and relationship validity", "run IDS requirements", "inspect geometry and placements", "review BCF issues", "record software and schema version"],
                "rule": "A valid IFC syntax check does not prove design adequacy or compliance with every project requirement.",
            },
        })

        lessons.append({
            "domain": "bim_georeferencing",
            "system": BIM_SYSTEM,
            "prompt": (
                "Explain how a BIM project coordinate system relates to local model "
                "coordinates, survey coordinates, true north and a projected national "
                "grid. List the information required before applying a coordinate transform."
            ),
            "completion": {
                "schema": "nextai.bim_georeferencing_lesson.v1",
                "frames": ["local element coordinates", "project/site coordinates", "survey control coordinates", "projected or geospatial reference system"],
                "required_inputs": ["CRS identifier or EPSG code", "survey control points", "horizontal and vertical datum", "units", "rotation to true/grid north", "known translation and elevation offsets"],
                "workflow": ["record the agreed CRS", "check survey control", "define model origin and orientation", "apply one documented transform", "test known control points", "export and re-import to verify"],
                "validation": ["control-point residuals within project tolerance", "units and vertical datum correct", "no duplicate or conflicting transforms"],
            },
        })

        lessons.append({
            "domain": "bim_phasing_revisions",
            "system": BIM_SYSTEM,
            "prompt": (
                "Explain how BIM construction phases, design options, revisions and "
                "demolition/new work status should be represented without losing "
                "the history of the original building elements."
            ),
            "completion": {
                "schema": "nextai.bim_phase_revision_lesson.v1",
                "concepts": {
                    "phase": "project stage or construction/demolition state assigned to model elements",
                    "design_option": "alternative proposal kept separate for comparison and approval",
                    "revision": "controlled change to a model or drawing deliverable",
                    "issue_status": "coordination or approval state, not the same as construction phase",
                },
                "workflow": ["record existing conditions", "assign demolition and new-work phases explicitly", "keep alternatives identifiable", "track model revisions and approvals", "publish a coordinated issue-specific deliverable"],
                "checks": ["existing elements retained in history", "phase filters produce expected views", "revisions trace to approved changes"],
            },
        })

        lessons.append({
            "domain": "engineering_structural_workflow",
            "system": BIM_SYSTEM,
            "prompt": (
                "Explain the structural load path for a framed building from floor "
                "slabs through beams and columns to foundations and supporting ground. "
                "List the inputs needed before any member sizing or code check."
            ),
            "completion": {
                "schema": "nextai.structural_load_path_lesson.v1",
                "load_path": ["floor and roof actions", "slabs or deck", "beams and girders", "columns or walls", "foundations", "bearing soil or rock"],
                "checks": ["continuous load transfer", "stability in both principal directions", "lateral load-resisting system identified", "connection and support assumptions documented"],
                "required_inputs": ["geometry and spans", "material properties", "permanent and variable actions", "wind and seismic criteria where applicable", "support and soil conditions", "design jurisdiction and code edition"],
                "rule": "Do not size members or state compliance without a complete analysis model, verified loads and the applicable code edition.",
            },
        })

        lessons.append({
            "domain": "engineering_reinforced_concrete_workflow",
            "system": BIM_SYSTEM,
            "prompt": (
                "Prepare a code-aware reinforced concrete design workflow for a "
                "structural member. Identify required inputs, analysis, design checks, "
                "detailing and review stages. Do not invent dimensions, loads or code clauses."
            ),
            "completion": {
                "schema": "nextai.reinforced_concrete_workflow.v1",
                "stages": ["confirm design basis and code edition", "collect geometry and material strengths", "establish load cases and combinations from the adopted code", "analyse the structural model", "check strength and serviceability", "design reinforcement and anchorage", "detail cover, spacing, laps and curtailment", "independent design review and issue"],
                "required_inputs": ["member type and support conditions", "section dimensions", "concrete and reinforcement grades", "actions and combinations", "exposure and fire requirements", "detailing and constructability constraints"],
                "not_assumed": ["BS 8110 edition", "Eurocode edition and national annex", "load values", "material grades", "bar sizes"],
                "validation": ["calculations trace to cited code clauses", "units reconcile", "detailing checks are complete", "qualified engineer reviews the design"],
            },
        })

        lessons.append({
            "domain": "engineering_geotechnical_workflow",
            "system": BIM_SYSTEM,
            "prompt": (
                f"Plan the geotechnical investigation for a proposed building with "
                f"foundation influence depth extending to about {soil_depth} m. "
                "Explain how boreholes, sampling, groundwater observations and "
                "laboratory tests support foundation selection. Do not assume soil capacity."
            ),
            "completion": {
                "schema": "nextai.geotechnical_investigation_plan.v1",
                "investigation": ["review site history and geology", "prepare investigation layout based on structure and variability", "advance boreholes or trial pits to justified depths", "record strata and groundwater observations", "obtain representative samples", "perform suitable in-situ and laboratory tests", "prepare a factual and interpretative geotechnical report"],
                "parameters_from_report": ["stratigraphy", "groundwater level and variation", "strength parameters", "compressibility and settlement parameters", "unit weight", "permeability", "aggressivity and chemical conditions"],
                "foundation_checks": ["bearing resistance", "total and differential settlement", "sliding and overturning where relevant", "groundwater and construction effects", "nearby structures and services"],
                "rule": "Do not invent allowable bearing pressure or recommend a foundation type without site-specific investigation and structural loads.",
            },
        })

        lessons.append({
            "domain": "engineering_water_and_drainage",
            "system": BIM_SYSTEM,
            "prompt": (
                f"Plan a drainage and water-services information model with a design "
                f"flow supplied as {pipe_flow:.1f} L/s. Identify catchments, pipe runs, "
                "levels, gradients, structures and outfall relationships. Do not guess "
                "pipe diameter or a statutory minimum gradient."
            ),
            "completion": {
                "schema": "nextai.water_drainage_information_plan.v1",
                "design_flow": {"value": pipe_flow, "unit": "L/s", "origin": "user supplied in task"},
                "objects": ["catchment", "pipe segment", "manhole or access chamber", "inlet or fixture", "outfall or connection"],
                "required_properties": ["invert levels", "cover levels", "pipe material", "diameter", "design flow", "slope", "system type"],
                "checks": ["flow direction consistent with inverts", "network connectivity checked", "cover and clearance checked", "hydraulic capacity analysed using adopted method", "outfall approval recorded"],
                "missing_inputs": ["rainfall or fixture criteria", "catchment area", "roughness", "permitted discharge", "applicable jurisdiction and standard"],
            },
        })

        lessons.append({
            "domain": "engineering_survey_and_setting_out",
            "system": BIM_SYSTEM,
            "prompt": (
                "Explain the survey and setting-out information needed to transfer "
                "a BIM/CAD building grid to a construction site. Include control points, "
                "benchmarks, grid intersections, levels, tolerances and independent checks."
            ),
            "completion": {
                "schema": "nextai.survey_setting_out_plan.v1",
                "control": ["verified horizontal control points", "verified vertical benchmark", "coordinate reference system", "project grid and orientation"],
                "setting_out": ["derive grid intersection coordinates", "set out offsets and building corners", "transfer level datums", "record instrument and method", "check independent backsight or closure"],
                "checks": ["coordinate units explicit", "closure within project survey tolerance", "benchmark height source documented", "as-set-out values independently checked"],
                "rule": "Do not treat arbitrary model origin coordinates as surveyed site coordinates.",
            },
        })

        lessons.append({
            "domain": "construction_project_controls",
            "system": BIM_SYSTEM,
            "prompt": (
                "Convert a building construction scope into a work breakdown structure "
                "and a logic-linked programme. Explain dependencies, milestones, "
                "critical path and progress evidence without inventing durations."
            ),
            "completion": {
                "schema": "nextai.construction_controls_plan.v1",
                "wbs": ["mobilisation and site establishment", "substructure", "superstructure", "envelope", "building services", "internal finishes", "testing and commissioning", "handover"],
                "schedule_fields": ["activity id", "description", "duration", "predecessors", "successors", "calendar", "baseline dates", "actual dates", "responsible party"],
                "rules": ["logic links must be explicit", "critical path is calculated from activity network", "baseline and actual progress are separate", "percent complete requires measurable evidence"],
                "not_assumed": ["activity durations", "crew productivity", "procurement lead times", "weather allowances"],
            },
        })

        lessons.append({
            "domain": "construction_cost_and_quantities",
            "system": BIM_SYSTEM,
            "prompt": (
                "Explain how a BIM quantity take-off becomes a bill of quantities and "
                "cost estimate. Distinguish model quantities, measurement rules, "
                "rates, allowances and tender adjustments."
            ),
            "completion": {
                "schema": "nextai.bim_cost_estimation_workflow.v1",
                "sequence": ["define measurement rules and work sections", "filter model elements by classification and phase", "extract dimensions and quantities from validated native objects", "apply agreed deductions and waste rules", "map items to bill descriptions", "apply sourced rates and currency/date basis", "record preliminaries, risks and allowances separately", "review and reconcile"],
                "quantity_sources": ["element count", "length", "area", "volume", "weight only where source data supports it"],
                "required_metadata": ["measurement method", "unit", "currency", "rate source", "price date", "location", "tax and escalation basis"],
                "rule": "A model quantity is not a complete cost estimate; never invent rates or market prices.",
            },
        })

        lessons.append({
            "domain": "construction_quality_and_safety",
            "system": BIM_SYSTEM,
            "prompt": (
                "Prepare a combined construction quality-control and site safety "
                "inspection plan for a concrete placement activity. Include hold points, "
                "inspection evidence, hazards, controls and approval responsibilities."
            ),
            "completion": {
                "schema": "nextai.construction_quality_safety_plan.v1",
                "quality": ["approved drawings and method statement", "formwork and reinforcement inspection", "cover and embedded items inspection", "concrete delivery and mix record", "placement and compaction observation", "curing and test records", "nonconformance and corrective action"],
                "safety": ["lifting and handling hazards", "work at height and edge protection", "plant and vehicle interface", "temporary works stability", "electrical and access hazards", "PPE and emergency arrangements"],
                "hold_points": ["pre-pour inspection", "concrete acceptance", "post-placement review"],
                "evidence": ["inspection request", "signed checklist", "test results", "photographs tied to location/date", "approved corrective-action closure"],
                "rule": "Use the project's approved method statement, risk assessment and applicable law; this generic checklist does not replace site-specific safety planning.",
            },
        })

    # A separate standards lesson teaches the student how to handle laws and codes
    # without memorising stale or copyrighted clauses as if they were universal.
    lessons.append({
        "domain": "engineering_standards_and_regulations",
        "system": BIM_SYSTEM,
        "prompt": (
            "A user asks whether a CAD/BIM design complies with a building or "
            "engineering code but does not state the project country, code edition "
            "or design basis. Explain how NextAI should proceed."
        ),
        "completion": {
            "schema": "nextai.standards_compliance_protocol.v1",
            "required_context": ["jurisdiction", "authority having jurisdiction", "standard or regulation title", "edition and amendments", "project type and scope", "design basis and verified inputs"],
            "workflow": ["ask for missing jurisdiction and edition", "retrieve the authorised standard or official regulatory source", "record exact clause and source citation", "check the actual native model or engineering calculation", "report each pass, fail, warning and unverified item", "request qualified professional review where legally required"],
            "rules": ["never assume BS 8110, Eurocodes or another code applies without confirmation", "never invent clause numbers or limits", "do not redistribute copyrighted standards without permission", "distinguish software validation from legal compliance and professional certification"],
        },
    })

    # Additional engineering lessons close gaps between model creation,
    # engineering validation and downstream project delivery.
    for index in range(12):
        width = 100 + (index % 6) * 20
        height = 70 + (index % 5) * 10
        thickness = 8 + (index % 4) * 2
        diameter = 6 + (index % 3) * 2
        depth = 5 + (index % 5) * 2
        storeys = 2 + index % 4

        lessons.extend([
            {
                "domain": "cad_geometry_topology",
                "system": CAD_SYSTEM,
                "prompt": "Explain how vertices, edges, wires, faces, shells, solids and meshes relate in a boundary-representation CAD model. Give the validity checks required before editing, manufacturing or exporting.",
                "completion": {
                    "schema": "nextai.cad_topology_validation.v1",
                    "entities": {
                        "vertex": "topological point",
                        "edge": "bounded curve between vertices",
                        "wire": "ordered connected boundary edges",
                        "face": "surface bounded by wires",
                        "shell": "connected collection of faces",
                        "solid": "closed shell enclosing a volume",
                        "mesh": "polygon facets approximating a surface, without parametric feature history",
                    },
                    "checks": ["wire closure where required", "valid face boundaries", "closed shell for volume solids", "kernel solid validity and non-zero volume", "mesh watertightness and consistent normals", "units and geometric tolerance recorded"],
                    "rule": "A visually closed mesh is not proof of a valid parametric solid.",
                },
            },
            {
                "domain": "cad_sketch_constraint_diagnosis",
                "system": CAD_SYSTEM,
                "prompt": f"Diagnose a fully constrained sketch for a {width} mm by {height} mm plate with two {diameter} mm holes. Explain degrees of freedom, geometric constraints and driving dimensions.",
                "completion": {
                    "schema": "nextai.sketch_constraint_diagnosis.v1",
                    "units": "mm",
                    "geometry": ["four connected lines", "two circles"],
                    "constraints": ["coincident endpoints", "horizontal and vertical edges", "equal opposite sides", "aligned hole centres", "symmetric hole centres"],
                    "dimensions": [{"name": "width", "value": width}, {"name": "height", "value": height}, {"name": "hole_diameter", "value": diameter}],
                    "diagnosis": ["inspect remaining degrees of freedom", "identify unconstrained translation/rotation", "add only independent constraints", "recompute and inspect conflicts", "change one driving dimension and verify intended movement"],
                    "acceptance": ["zero intended degrees of freedom", "no redundant or conflicting constraints", "dimensions trace to the specification"],
                },
            },
            {
                "domain": "cad_boolean_feature_planning",
                "system": CAD_SYSTEM,
                "prompt": f"Plan a parametric boolean difference for a {width} mm by {height} mm by {thickness} mm plate with a central {diameter} mm through-hole. Return the base solid, cutter and feature order.",
                "completion": {
                    "schema": "nextai.cad_boolean_feature_plan.v1",
                    "units": "mm",
                    "features": [
                        {"order": 1, "id": "base", "operation": "box", "length": width, "width": height, "height": thickness},
                        {"order": 2, "id": "cutter", "operation": "cylinder", "radius": diameter / 2, "height": thickness, "origin": [width / 2, height / 2, 0]},
                        {"order": 3, "id": "result", "operation": "boolean_difference", "base": "base", "tool": "cutter"},
                    ],
                    "validation": ["one valid solid", "one through-hole", "volume reduction matches the removed cylinder within tolerance", "recompute and save/reopen"],
                },
            },
            {
                "domain": "cad_surface_modelling",
                "system": CAD_SYSTEM,
                "prompt": "Choose between extrusion, revolution, sweep and loft for a parametric surface or solid. Describe the profiles, guide curves, axes, section order and continuity checks needed.",
                "completion": {
                    "schema": "nextai.cad_surface_modelling_guide.v1",
                    "operations": {"extrusion": "translate a profile along a vector", "revolution": "rotate a profile about an axis", "sweep": "move a profile along a guide path", "loft": "interpolate between ordered sections"},
                    "inputs": ["profile geometry and closure", "axis or path", "section order", "orientation/twist rule", "continuity requirement", "units and tolerance"],
                    "checks": ["profiles valid and consistently oriented", "guide path continuous", "section correspondence checked", "self-intersections checked", "result shell/solid validity matches intent"],
                },
            },
            {
                "domain": "cad_mesh_quality",
                "system": CAD_SYSTEM,
                "prompt": "Prepare a mesh export quality checklist for a parametric part. Explain scale, chordal deviation, angular deflection, watertightness, normals and format selection.",
                "completion": {
                    "schema": "nextai.cad_mesh_quality_plan.v1",
                    "checks": ["correct body and revision", "units and scale", "mesh closure/manifold edges", "consistent normals", "self-intersection", "chordal deviation", "angular deflection", "minimum feature size", "orientation and origin"],
                    "formats": {"STL": "triangular surface; no parametric history", "3MF": "additive manufacturing container with richer metadata"},
                    "acceptance": ["mesh integrity passes", "tessellation error fits manufacturing tolerance", "dimensions agree with source B-rep", "export can be re-imported and inspected"],
                },
            },
            {
                "domain": "cad_fem_preprocessing",
                "system": CAD_SYSTEM,
                "prompt": "Prepare a finite-element analysis of a structural bracket. Identify idealisation, material, contacts, mesh, loads, supports, convergence and independent checks. Do not invent loads or claim a solved result.",
                "completion": {
                    "schema": "nextai.fem_preprocessing_plan.v1",
                    "stages": ["simplify only non-critical detail", "assign verified material", "define contacts", "select element formulation and mesh controls", "apply supports matching physical conditions", "apply documented load cases", "solve and review residuals", "refine mesh and check convergence", "compare with hand checks and engineering judgement"],
                    "required_inputs": ["material modulus and Poisson ratio", "strength properties where needed", "load magnitudes/directions", "support stiffness", "contact assumptions", "solver and acceptance criteria"],
                    "rule": "A stress plot is not a valid result without correct boundary conditions, equilibrium, convergence and review.",
                },
            },
            {
                "domain": "cad_cam_preprocessing",
                "system": CAD_SYSTEM,
                "prompt": "Prepare a CAM job for a plate with drilled holes. List the stock, work coordinate system, machine, tools, operations, cutting data, simulation and postprocessor information needed before generating G-code.",
                "completion": {
                    "schema": "nextai.cam_job_plan.v1",
                    "stages": ["confirm model revision", "define stock and material", "set machine and work coordinate system", "select verified tools and holders", "choose facing/profile/drilling operations", "set feeds/speeds/depths from approved data", "simulate and check collisions", "review remaining stock", "postprocess for the exact controller", "verify approved setup"],
                    "required_inputs": ["machine kinematics", "controller", "tool geometry", "material cutting data", "workholding", "tolerances"],
                    "not_assumed": ["spindle speed", "feed rate", "tool diameter", "stepover", "cut depth", "machine-specific G-code"],
                },
            },
            {
                "domain": "bim_room_boundaries",
                "system": BIM_SYSTEM,
                "prompt": "Explain how BIM rooms/spaces are bounded by walls, doors, floors and separation lines. Distinguish room objects, boundaries, gross/net area and room enclosure validity.",
                "completion": {
                    "schema": "nextai.bim_room_boundary_lesson.v1",
                    "concepts": {"space": "semantic spatial object with identity and level", "boundary": "enclosure derived from room-bounding objects", "gross_area": "area by the adopted gross boundary convention", "net_area": "area by the adopted clear boundary convention", "volume": "enclosed volume subject to height/boundary rules"},
                    "checks": ["boundary is closed", "correct storey assignment", "boundary elements resolve", "area method is documented", "unbounded/overlapping rooms are reported"],
                    "rule": "A shared wall does not prove a door or navigable connection.",
                },
            },
            {
                "domain": "bim_asset_handover",
                "system": BIM_SYSTEM,
                "prompt": "Prepare BIM asset information requirements for facilities-management handover. Include type and instance data, location, classification, manufacturer, warranty and maintenance document fields.",
                "completion": {
                    "schema": "nextai.bim_asset_handover.v1",
                    "fields": ["asset_id", "ifc_class", "asset_type", "classification", "storey", "space", "system", "manufacturer", "model_reference", "serial_number", "installation_date", "warranty_expiry", "maintenance_interval", "document_reference"],
                    "rules": ["separate type and instance data", "preserve approved identifiers", "link documents to the correct asset", "record missing values rather than guessing", "validate against the agreed handover requirements"],
                    "checks": ["unique asset IDs", "resolvable location and system", "required properties complete", "document links resolve", "open issues disclosed"],
                },
            },
            {
                "domain": "bim_revision_change_impact",
                "system": BIM_SYSTEM,
                "prompt": "A host wall is moved in a BIM project. Explain how to identify dependent doors/windows, rooms, finishes, dimensions, schedules, sections and quantities before applying the edit.",
                "completion": {
                    "schema": "nextai.bim_change_impact_plan.v1",
                    "workflow": ["capture before-state and element identity", "inspect direct and indirect dependencies", "list hosted elements", "identify room boundary and finish impacts", "identify affected views, dimensions and schedules", "identify quantity and IFC relationship changes", "request approval if design intent is ambiguous", "apply as one native transaction", "recompute and revalidate affected objects", "compare and save a revision record"],
                    "rule": "Never move a host object without checking hosted elements and seeking approval when the change is ambiguous.",
                },
            },
            {
                "domain": "construction_4d_sequence",
                "system": BIM_SYSTEM,
                "prompt": f"Plan a 4D BIM workflow for a {storeys}-storey building. Distinguish WBS activity dates, model phases, baseline, actual progress and field-verified completion.",
                "completion": {
                    "schema": "nextai.construction_4d_plan.v1",
                    "sequence": ["create WBS activities", "link activities to model elements and work zones", "define dependencies and calendars", "assign baseline durations and dates", "simulate planned sequence", "record actual dates and measurable evidence separately", "track deviations and approved recovery actions", "retain baseline/revision history"],
                    "checks": ["no broken activity dependencies", "linked elements exist", "baseline remains controlled", "actual progress has traceable field evidence"],
                    "rule": "A model phase or element's existence is not evidence that site work has been completed.",
                },
            },
            {
                "domain": "civil_site_coordination",
                "system": BIM_SYSTEM,
                "prompt": f"Prepare a civil site BIM model for a {depth} m deep proposed foundation influence zone. Include survey controls, boundary, terrain, building pad, access, drainage and buried utilities. State the inputs needed before grading design.",
                "completion": {
                    "schema": "nextai.civil_site_model_plan.v1",
                    "layers": ["survey control and benchmarks", "legal/site boundary", "existing terrain", "proposed finished levels", "building footprint and formation", "roads and pedestrian access", "hardscape", "surface drainage and outfall", "buried utilities and easements"],
                    "required_inputs": ["topographic survey", "boundary/title information", "geotechnical report", "rainfall/catchment data", "utility records", "road authority requirements", "local planning/environmental rules"],
                    "checks": ["coordinate system and datum agree", "cut/fill uses verified surfaces", "runoff reaches approved outfall", "access gradients and clearances checked", "services coordinated with foundations"],
                    "rule": "Never fabricate survey levels, legal boundaries, drainage capacity or approval status.",
                },
            },
        ])


    # Worked, unit-aware calculation lessons. Values are explicitly supplied
    # in each prompt; the targets show auditable equilibrium, stiffness,
    # continuity and quantity steps rather than unsupported design decisions.
    for index in range(12):
        span_m = 6.0 + 0.5 * (index % 3)
        udl_kn_m = 3.0 + 0.5 * (index % 4)
        point_load_kn = 9.0 + (index % 5)
        point_distance_m = span_m / 3.0
        udl_resultant_kn = udl_kn_m * span_m
        right_reaction_kn = (
            udl_resultant_kn * (span_m / 2.0)
            + point_load_kn * point_distance_m
        ) / span_m
        left_reaction_kn = udl_resultant_kn + point_load_kn - right_reaction_kn

        lessons.append({
            "domain": "engineering_beam_reactions_calculation",
            "system": ENGINEERING_SYSTEM,
            "prompt": (
                f"A simply supported beam has span {span_m:g} m, a full-span "
                f"uniformly distributed load of {udl_kn_m:g} kN/m, and a "
                f"{point_load_kn:g} kN point load located {point_distance_m:g} m "
                "from the left support. Calculate the two vertical reactions "
                "using static equilibrium. Treat this as an idealised textbook "
                "exercise, not a complete member design."
            ),
            "completion": {
                "schema": "nextai.beam_reactions_worked.v1",
                "units": {"length": "m", "distributed_load": "kN/m", "force": "kN", "moment": "kN.m"},
                "model": "pin and roller supports; full-span UDL; one vertical point load; self-weight excluded because it is not specified",
                "given": {
                    "span_m": span_m,
                    "udl_kn_per_m": udl_kn_m,
                    "point_load_kn": point_load_kn,
                    "point_load_distance_from_left_m": round(point_distance_m, 6),
                },
                "working": [
                    f"UDL resultant = wL = {udl_kn_m:g} × {span_m:g} = {udl_resultant_kn:g} kN, acting at L/2",
                    f"Take moments about the left support: R_B L = (wL)(L/2) + P a = {udl_resultant_kn:g} × {span_m/2:g} + {point_load_kn:g} × {point_distance_m:g}",
                    "Solve the moment equation for the right reaction, then use vertical force equilibrium for the left reaction",
                ],
                "answer": {
                    "left_reaction_kn": round(left_reaction_kn, 6),
                    "right_reaction_kn": round(right_reaction_kn, 6),
                    "vertical_force_check_kn": round(left_reaction_kn + right_reaction_kn - udl_resultant_kn - point_load_kn, 9),
                    "left_support_moment_check_kn_m": round(
                        right_reaction_kn * span_m
                        - udl_resultant_kn * span_m / 2.0
                        - point_load_kn * point_distance_m, 9
                    ),
                },
                "limits": [
                    "This checks global reactions only; it does not calculate shear-force or bending-moment envelopes, deflection, stability or member capacity.",
                    "A real design requires the applicable load combinations, self-weight, support conditions, material data and governing jurisdictional standard.",
                ],
            },
        })

        youngs_modulus_pa = 200e9
        area_mm2 = 300.0 + 50.0 * (index % 5)
        bar_length_m = 2.0 + 0.25 * (index % 3)
        axial_force_kn = 15.0 + 5.0 * (index % 4)
        area_m2 = area_mm2 * 1e-6
        axial_stiffness_n_per_m = youngs_modulus_pa * area_m2 / bar_length_m
        displacement_mm = (axial_force_kn * 1000.0 / axial_stiffness_n_per_m) * 1000.0

        lessons.append({
            "domain": "engineering_fem_axial_bar_calculation",
            "system": ENGINEERING_SYSTEM,
            "prompt": (
                f"For a one-element, two-node linear axial bar with E = 200 GPa, "
                f"area = {area_mm2:g} mm², length = {bar_length_m:g} m, node 1 fixed "
                f"and a tensile {axial_force_kn:g} kN force at node 2, form the "
                "element stiffness matrix and calculate the free-end displacement. "
                "Show unit conversions. This is a linear-elastic teaching example."
            ),
            "completion": {
                "schema": "nextai.fem_axial_bar_worked.v1",
                "units": {"E": "Pa", "area": "m2 after conversion", "length": "m", "stiffness": "N/m", "force": "N", "displacement": "mm"},
                "given": {"youngs_modulus_pa": youngs_modulus_pa, "area_mm2": area_mm2, "area_m2": area_m2, "length_m": bar_length_m, "tensile_force_kn": axial_force_kn},
                "working": [
                    "Convert area from mm² to m² by multiplying by 10⁻⁶",
                    "For a 2-node axial bar, k = EA/L",
                    "The local element matrix is k multiplied by [[1, -1], [-1, 1]]",
                    "With node 1 fixed, the free-end displacement is F/k",
                ],
                "element_stiffness_n_per_m": round(axial_stiffness_n_per_m, 3),
                "element_matrix_n_per_m": [
                    [round(axial_stiffness_n_per_m, 3), round(-axial_stiffness_n_per_m, 3)],
                    [round(-axial_stiffness_n_per_m, 3), round(axial_stiffness_n_per_m, 3)],
                ],
                "answer": {
                    "node_1_displacement_mm": 0.0,
                    "node_2_displacement_mm": round(displacement_mm, 6),
                    "support_reaction_kn": round(-axial_force_kn, 6),
                },
                "limits": [
                    "Assumes a prismatic bar, small displacement, linear elasticity, perfect axial alignment and no thermal strain.",
                    "This single-element result is not a complete structural analysis or member-capacity check.",
                ],
            },
        })

        flow_m3_s = 0.01 + 0.002 * index
        pipe_diameter_m = 0.10 + 0.01 * (index % 4)
        pipe_area_m2 = math.pi * pipe_diameter_m**2 / 4.0
        mean_velocity_m_s = flow_m3_s / pipe_area_m2

        lessons.append({
            "domain": "engineering_pipe_continuity_calculation",
            "system": ENGINEERING_SYSTEM,
            "prompt": (
                f"A full circular pipe carries a steady discharge of {flow_m3_s:g} m³/s "
                f"and has internal diameter {pipe_diameter_m:g} m. Calculate its "
                "cross-sectional area and mean flow velocity using continuity. "
                "Assume incompressible steady flow and do not calculate head loss."
            ),
            "completion": {
                "schema": "nextai.pipe_continuity_worked.v1",
                "units": {"discharge": "m3/s", "diameter": "m", "area": "m2", "velocity": "m/s"},
                "given": {"discharge_m3_s": flow_m3_s, "internal_diameter_m": pipe_diameter_m},
                "working": [
                    "For a circular pipe, A = πD²/4",
                    "Apply continuity for steady incompressible flow: Q = Av",
                    "Rearrange to v = Q/A and retain SI units",
                ],
                "answer": {
                    "area_m2": round(pipe_area_m2, 8),
                    "mean_velocity_m_s": round(mean_velocity_m_s, 6),
                    "continuity_check_m3_s": round(pipe_area_m2 * mean_velocity_m_s, 9),
                },
                "limits": [
                    "Mean velocity alone does not determine pressure, energy grade line, friction loss or pump duty.",
                    "A real hydraulic assessment also needs pipe roughness, length, fittings, fluid properties and boundary conditions.",
                ],
            },
        })

        slab_length_m = 5.0 + 0.5 * (index % 3)
        slab_width_m = 4.0 + 0.25 * (index % 4)
        slab_thickness_m = 0.15 + 0.025 * (index % 2)
        concrete_volume_m3 = slab_length_m * slab_width_m * slab_thickness_m

        lessons.append({
            "domain": "construction_concrete_quantity_calculation",
            "system": ENGINEERING_SYSTEM,
            "prompt": (
                f"Calculate the net geometric concrete volume for a rectangular "
                f"slab {slab_length_m:g} m long, {slab_width_m:g} m wide and "
                f"{slab_thickness_m:g} m thick. Assume no openings and no allowance "
                "for waste. Show the unit-consistent calculation."
            ),
            "completion": {
                "schema": "nextai.concrete_quantity_worked.v1",
                "units": {"dimensions": "m", "volume": "m3"},
                "given": {"length_m": slab_length_m, "width_m": slab_width_m, "thickness_m": slab_thickness_m},
                "working": [
                    "For a rectangular slab, volume = length × width × thickness",
                    f"Substitute the supplied dimensions: {slab_length_m:g} × {slab_width_m:g} × {slab_thickness_m:g}",
                    "The resulting unit is m³",
                ],
                "answer": {
                    "net_concrete_volume_m3": round(concrete_volume_m3, 6),
                    "plan_area_m2": round(slab_length_m * slab_width_m, 6),
                },
                "exclusions": [
                    "No waste or overbreak allowance",
                    "No deduction for openings because the prompt specifies none",
                    "No reinforcement, formwork or cost quantity is inferred from concrete volume",
                ],
            },
        })

    return lessons


def make_design_intake_curriculum() -> list[dict[str, Any]]:
    """Teach NextAI to interview users before producing CAD or BIM designs.

    Every design scenario is represented as three supervised turns: initial
    clarification, context-aware follow-up, and a confirmed design brief.
    All three records share one split_group so dialogue stages cannot leak
    across training, validation and held-out test sets.
    """
    lessons: list[dict[str, Any]] = []

    design_system = (
        "You are NextAI, a helpful CAD/BIM design assistant. Before creating "
        "geometry, understand the user's purpose and ask only the questions "
        "needed for the next safe design step. Ask concise, grouped questions "
        "in natural language. Track what the user has already confirmed; never "
        "ask the same question twice. Separate required inputs from optional "
        "preferences. Never invent dimensions, loads, material properties, "
        "site conditions, standards or approvals. When enough information is "
        "available for a concept, summarise the brief and state any proposed "
        "assumptions clearly. Do not claim that geometry has been created until "
        "the native application has actually created and validated it. Return exactly one "
        "JSON object with two fields: message (natural language for the user) and plan "
        "(a list of native tool steps). During clarification, the plan must be empty. "
        "Do not wrap the JSON in Markdown."
    )
    cad_system = design_system + (
        " For CAD, clarify the object's function, envelope, interfaces, "
        "components, intended level of detail and manufacturing/export purpose. "
        "Keep safety-critical or load-bearing design decisions subject to "
        "verified engineering inputs and native checks."
    )
    bim_system = design_system + (
        " For BIM, clarify project scope, building/site context, disciplines, "
        "coordinate reference, information requirements, exchange deliverables "
        "and validation criteria. Distinguish geometry from information data."
    )
    architecture_system = design_system + (
        " For architectural planning, distinguish bedrooms, master bedrooms, "
        "bathrooms and toilet/WC rooms; clarify ensuite versus shared facilities, "
        "living spaces, building form and optional rooms. Ask for plot dimensions "
        "and access orientation before claiming a site-fitted scaled plan."
    )

    def add_three_turn_flow(
        domain: str,
        family: str,
        scenario_index: int,
        initial_prompt: str,
        first_assistant: str,
        first_user_reply: str,
        follow_up_assistant: str,
        second_user_reply: str,
        final_assistant: str,
        system: str,
    ) -> None:
        group_id = f"design-intake-{family}-{scenario_index:02d}"
        first_response = json.dumps({"message": first_assistant, "plan": []}, ensure_ascii=False)
        follow_up_response = json.dumps({"message": follow_up_assistant, "plan": []}, ensure_ascii=False)
        final_response = json.dumps({"message": final_assistant, "plan": []}, ensure_ascii=False)
        lessons.extend([
            {
                "domain": domain,
                "system": system,
                "prompt": initial_prompt,
                "completion": first_response,
                "split_group": group_id,
                "stage": "initial_clarification",
            },
            {
                "domain": domain,
                "system": system,
                "prompt": (
                    "Conversation so far:\n"
                    f"User: {initial_prompt}\n"
                    f"Assistant: {first_response}\n"
                    f"User: {first_user_reply}\n\n"
                    "Respond to the latest user turn. Preserve confirmed details, "
                    "ask only for essential information that is still missing, "
                    "and do not repeat questions already answered. Return the required JSON."
                ),
                "completion": follow_up_response,
                "split_group": group_id,
                "stage": "context_aware_follow_up",
            },
            {
                "domain": domain,
                "system": system,
                "prompt": (
                    "Conversation so far:\n"
                    f"User: {initial_prompt}\n"
                    f"Assistant: {first_response}\n"
                    f"User: {first_user_reply}\n"
                    f"Assistant: {follow_up_response}\n"
                    f"User: {second_user_reply}\n\n"
                    "Now provide the confirmed design brief and next native application step. "
                    "Do not invent missing facts. Return the required JSON."
                ),
                "completion": final_response,
                "split_group": group_id,
                "stage": "confirmed_design_brief",
            },
        ])

    # Residential design: the first reply explicitly asks about every item
    # the user requested NextAI to clarify, rather than assuming defaults.
    home_prompts = [
        "Generate a 3-bedroom floor plan.",
        "Can you draw a house plan with three bedrooms?",
        "I need a floor plan for a three-bedroom home.",
        "Prepare a three-bedroom residential layout for me.",
        "Design a three-bedroom house in CAD.",
        "I want a simple floor plan: three bedrooms.",
        "Create a concept plan for a three-bedroom family house.",
        "Help me lay out a three-bedroom residence.",
        "Draw a three-bedroom home layout with good circulation.",
        "Make a residential plan with three bedrooms and shared spaces.",
        "I need a three-bedroom house plan that I can edit later.",
        "Start a CAD floor plan for a three-bedroom home.",
    ]
    extras = [
        ["store", "dining area"],
        ["store", "laundry"],
        ["pantry", "dining area"],
        ["store", "guest WC"],
        ["laundry", "small study"],
        ["store", "family lounge"],
        ["pantry", "laundry"],
        ["store", "prayer room"],
        ["dining area", "guest WC"],
        ["store", "carport"],
        ["pantry", "study"],
        ["laundry", "family lounge"],
    ]
    forms = ["bungalow", "bungalow", "two-storey house", "bungalow"] * 3
    masters = [1, 1, 2, 1, 1, 2, 1, 1, 1, 2, 1, 1]
    toilets = [2, 3, 3, 2, 3, 4, 2, 3, 2, 4, 3, 2]
    living = [1, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 1]
    for i, initial_prompt in enumerate(home_prompts):
        master_count = masters[i]
        toilet_count = toilets[i]
        ensuite_count = min(master_count, toilet_count - 1)
        shared_count = toilet_count - ensuite_count
        form = forms[i]
        living_count = living[i]
        living_label = "one sitting/living room" if living_count == 1 else "one formal sitting room and one family lounge"
        extra_rooms = extras[i]
        extras_label = ", ".join(extra_rooms)
        first_assistant = (
            "Certainly. Before I draw, let me confirm the layout you want:\n"
            "1. Should it be a bungalow or a storey house?\n"
            "2. How many master bedrooms do you want, and should each have an ensuite?\n"
            "3. How many toilets/bathrooms should there be in total? How many should be ensuite and how many shared or guest facilities?\n"
            "4. Do you want one sitting room, or a separate formal sitting room and family lounge?\n"
            "5. Which extra spaces should I include, such as a store, pantry, dining area, laundry, study, guest room or carport?\n"
            "6. Do you have the plot width and depth, and which side faces the road? You can give these in metres. "
            "I can make an unscaled concept without plot dimensions, but I need them for a scaled site-fitted plan."
        )
        first_user_reply = (
            f"Make it a {form}. I want 3 bedrooms, {master_count} master bedroom"
            f"{'s' if master_count != 1 else ''}, {toilet_count} toilet/bathroom spaces in total "
            f"({ensuite_count} ensuite and {shared_count} shared/guest), {living_label}, "
            f"and include {extras_label}. I have not chosen room dimensions yet."
        )
        follow_up_assistant = (
            "Thank you. I have recorded the building form, three bedrooms, the master-bedroom "
            "count, the total toilet/bathroom count and its ensuite/shared split, the living spaces "
            f"and these additional rooms: {extras_label}. I will not ask you to repeat those details. "
            "To fit the layout to your land, what are the plot width and depth, and which plot side "
            "has the road entrance? Also, should I propose preliminary room sizes for your review?"
        )
        second_user_reply = (
            f"The plot is {18 + (i % 3) * 2} m by {30 + (i % 2) * 5} m. "
            "The road is along the shorter frontage. Please propose room sizes, label them as "
            "preliminary, and keep all dimensions in metres."
        )
        final_assistant = (
            "Design brief confirmed:\n"
            f"- Building form: {form}\n"
            "- Bedrooms: 3\n"
            f"- Master bedrooms: {master_count}\n"
            f"- Toilets/bathrooms: {toilet_count} total ({ensuite_count} ensuite, {shared_count} shared/guest)\n"
            f"- Living spaces: {living_label}\n"
            f"- Additional rooms: {extras_label}\n"
            f"- Plot: {18 + (i % 3) * 2} m by {30 + (i % 2) * 5} m, road on the shorter frontage\n"
            "- Room sizes: propose preliminary dimensions and mark them for user review\n"
            "- Units: metres\n\n"
            "I now have enough information to prepare a dimensioned concept layout. I will show "
            "the room schedule, circulation, proposed wall positions, doors and windows, and "
            "overall dimensions. I will keep setbacks, exact wall build-ups and local planning "
            "requirements as items to confirm; I will not claim permit approval or code compliance."
        )
        add_three_turn_flow(
            "design_intake_architecture", "home", i + 1, initial_prompt,
            first_assistant, first_user_reply, follow_up_assistant,
            second_user_reply, final_assistant, architecture_system,
        )

    # Commercial spaces: teach work-pattern and occupancy questions, not only
    # room counting.
    office_uses = [
        ("small office", 12, 2, "reception, open work area and one meeting room"),
        ("design studio", 18, 1, "shared work tables, material library and review room"),
        ("clinic reception and consultation suite", 6, 3, "waiting area, consultation rooms and accessible WC"),
        ("training centre", 30, 2, "classroom, instructor room and storage"),
        ("co-working office", 24, 2, "hot desks, quiet rooms and meeting rooms"),
        ("retail shop", 5, 1, "sales floor, stock room and staff area"),
        ("small restaurant", 8, 2, "dining area, kitchen, wash-up and dry store"),
        ("community learning hub", 20, 2, "teaching room, reading area and multipurpose room"),
    ]
    for i, (use, people, toilets, extras_text) in enumerate(office_uses):
        prompt = f"Create a CAD floor plan for a {use}."
        first = (
            f"I can plan the {use}. Before drawing, please confirm: "
            f"(1) the expected staff/visitor capacity (I have no confirmed occupancy yet), "
            "(2) the activities and rooms that must be included, "
            "(3) the number and type of toilets, including any accessible provision, "
            "(4) whether this is a new building or a fit-out of an existing shell, "
            "(5) the usable floorplate dimensions and entrance position, and "
            "(6) whether you need a schematic concept or a dimensioned layout. "
            "Are there any access, privacy or equipment requirements I should respect?"
        )
        first_reply = (
            f"It is for about {people} people. Include {extras_text}. "
            f"Allow {toilets} toilet rooms for the concept. It is a fit-out, but I have not sent "
            "the existing floor plan or measured floorplate yet."
        )
        follow = (
            f"Understood: I have recorded the {people}-person planning target, {extras_text}, "
            f"and {toilets} toilet rooms. Since this is a fit-out, please provide the existing "
            "floor plan or the measured internal width and depth, and mark the entrance and any "
            "fixed columns, stairs, shafts or service cores. Without that existing-condition "
            "information I can only prepare a generic adjacency concept, not claim it fits the site."
        )
        second_reply = (
            f"The measured internal floorplate is {12 + i} m by {16 + (i % 3) * 2} m. "
            "The entrance is on the shorter side. I will provide a measured drawing before "
            "asking for a fit-out model; start with a room adjacency proposal."
        )
        final = (
            f"Brief recorded for a {use}: planning capacity {people}; toilet rooms {toilets}; "
            f"required spaces {extras_text}; measured floorplate {12 + i} m by "
            f"{16 + (i % 3) * 2} m; entrance on the shorter side. The next deliverable is a "
            "room adjacency and circulation proposal. Existing columns, stairs, shafts, accessible "
            "routes and applicable occupancy/fire requirements must be checked against the measured "
            "source plan before detailed geometry is approved."
        )
        add_three_turn_flow("design_intake_commercial_architecture", "commercial", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, architecture_system)

    # Vehicle and transport CAD: start with the vehicle's intended use and
    # package, then distinguish a concept model from roadworthy engineering.
    vehicle_specs = [
        ("compact electric SUV", "five", "electric", "front-wheel drive"),
        ("two-seat sports coupe", "two", "petrol", "rear-wheel drive"),
        ("family sedan", "five", "hybrid", "front-wheel drive"),
        ("double-cab pickup", "five", "diesel", "four-wheel drive"),
        ("small city car", "four", "electric", "rear-wheel drive"),
        ("off-road utility vehicle", "five", "petrol", "four-wheel drive"),
        ("electric delivery van", "two front seats", "electric", "front-wheel drive"),
        ("track-day sports car", "two", "petrol", "mid-engine rear-wheel drive"),
        ("minibus", "twelve", "diesel", "rear-wheel drive"),
        ("compact crossover", "five", "hybrid", "all-wheel drive"),
    ]
    for i, (vehicle, occupants, powertrain, drive) in enumerate(vehicle_specs):
        prompt = "Design a car in CAD." if i == 0 else f"Create a CAD concept for a {vehicle}."
        first = (
            "I can help build an editable vehicle concept. First, please confirm: "
            f"(1) the vehicle type and main use, (2) the number of occupants, "
            "(3) the target overall length, width, height and wheelbase—or permission "
            "to use clearly labelled concept placeholders, (4) the powertrain and drive "
            "layout if already chosen, (5) the exterior/interior components you want "
            "modelled, and (6) whether the deliverable is a visual concept, packaging "
            "model, detailed assembly or manufacturing drawings. Do you have wheel and "
            "tyre sizes, ground-clearance targets or battery/engine package dimensions?"
        )
        first_reply = (
            f"Make it a {vehicle} for {occupants} occupants, using a {powertrain} powertrain "
            f"and {drive}. I want an editable exterior and packaging concept, not manufacturing "
            "drawings yet. I do not have every component dimension."
        )
        follow = (
            f"Recorded: {vehicle}, {occupants} occupants, {powertrain} powertrain, {drive}, "
            "and an editable exterior/packaging concept. I still need the target vehicle envelope "
            "(length, width, height and wheelbase), or your approval to create labelled editable "
            "parameters for those values. Please also tell me whether I should keep wheel/tyre, "
            "battery/engine and suspension interfaces as placeholders until verified package data "
            "is supplied."
        )
        second_reply = (
            f"Use a concept envelope of {4.2 + (i % 4) * 0.1:.1f} m length, "
            f"{1.75 + (i % 3) * 0.05:.2f} m width and {1.5 + (i % 3) * 0.05:.2f} m height. "
            f"Use a {2.6 + (i % 4) * 0.05:.2f} m wheelbase. Keep wheel/tyre and powertrain "
            "mounting details as named editable placeholders for now."
        )
        final = (
            f"Vehicle brief: {vehicle}; occupants: {occupants}; powertrain: {powertrain}; "
            f"drive layout: {drive}; concept envelope: {4.2 + (i % 4) * 0.1:.1f} m × "
            f"{1.75 + (i % 3) * 0.05:.2f} m × {1.5 + (i % 3) * 0.05:.2f} m; "
            f"wheelbase: {2.6 + (i % 4) * 0.05:.2f} m. Deliverable: editable exterior and "
            "packaging concept. Wheel/tyre and powertrain mounts remain named, editable placeholders. "
            "NextCAD should organise the body, glazing, doors, wheel envelopes and interior package "
            "as separate parametric components. This concept is not a roadworthy vehicle design: "
            "crashworthiness, restraint systems, braking, steering, chassis strength and statutory "
            "compliance require verified engineering data, qualified review and applicable tests."
        )
        add_three_turn_flow("design_intake_vehicle_cad", "vehicle", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)

    # General mechanical parts: function and interfaces govern the model.
    component_specs = [
        ("mounting bracket", "support a specified component on a frame"),
        ("gearbox housing", "enclose and locate a gear train"),
        ("rotating shaft", "transmit torque between defined interfaces"),
        ("pump impeller", "transfer energy to a specified fluid"),
        ("machine guard", "separate people from moving machine parts"),
        ("lifting eye", "provide a defined lifting attachment point"),
        ("bearing block", "locate a shaft and its bearing"),
        ("pipe flange", "connect two specified pipe components"),
        ("robot arm link", "connect two joints in a defined mechanism"),
        ("heat sink", "transfer heat away from a defined electronic component"),
    ]
    for i, (part, function) in enumerate(component_specs):
        prompt = f"Design a {part} in CAD."
        first = (
            f"I can model the {part}. Before choosing geometry, please clarify: "
            f"(1) what it must do ({function}), (2) which parts it connects to and "
            "the measured mating dimensions, (3) the available envelope and critical "
            "hole/shaft/face locations, (4) expected loads, motion, temperature or fluid "
            "conditions where relevant, (5) preferred material if known, and "
            "(6) manufacturing method and required tolerances. Is this a visual prototype "
            "or a functional/load-bearing component?"
        )
        first_reply = (
            f"It is for {function}. It must fit an existing assembly, but I have not supplied "
            "the mating drawing or exact loads. Make a preliminary parametric concept."
        )
        follow = (
            f"Understood: the {part} must {function}, fit an existing assembly and begin as a "
            "preliminary parametric concept. Please supply the mating interface measurements or "
            "reference drawing, and identify any known loads or operating conditions. Until those "
            "are verified, I can model the envelope and editable interfaces but cannot size it for "
            "strength or certify functional safety."
        )
        second_reply = (
            "I will attach the mating drawing and verified operating data later. For now, create "
            "named parameters for the unknown interfaces and leave strength-critical dimensions "
            "uncommitted. Use millimetres and keep the feature history editable."
        )
        final = (
            f"Part brief: {part}; function: {function}; units: mm; parametric editable concept. "
            "Unknown mating interfaces and operating loads must remain named, uncommitted parameters. "
            "The next native CAD step is to create a reference skeleton, datum planes and named "
            "parameters, then build the base feature only after the reference drawing is attached. "
            "Do not invent interface sizes, material properties, load capacity or tolerances. "
            "A concept model is not proof of structural or functional adequacy."
        )
        add_three_turn_flow("design_intake_mechanical_part", "mechanical-part", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)

    # Assembly design: interfaces, degrees of freedom and motion must be explicit.
    assembly_specs = [
        ("gearbox assembly", "shafts, gears, bearings and housing"),
        ("bicycle crank assembly", "crank arms, spindle, bearings and chainring"),
        ("robot gripper", "base, links, pivots, actuator and fingers"),
        ("desk chair mechanism", "seat, backrest, height adjuster and swivel base"),
        ("conveyor drive assembly", "motor, gearbox, coupling, shaft and rollers"),
        ("door hinge mechanism", "leaves, pin, knuckles and fasteners"),
        ("pump assembly", "casing, impeller, shaft, seals and bearings"),
        ("folding mechanism", "links, pivots, stops, locks and user controls"),
    ]
    for i, (assembly, components) in enumerate(assembly_specs):
        prompt = f"Create a CAD model of a {assembly}."
        first = (
            f"I can organise the {assembly}. Please confirm: (1) the function and operating "
            f"sequence, (2) the required components (a starting list could be {components}), "
            "(3) which components are existing parts versus new designs, (4) which component is the reference component, (5) the mating faces, "
            "axes, fastener patterns and interface dimensions, (6) which joints should be fixed, "
            "revolute, prismatic or otherwise constrained, and (7) the expected motion range and "
            "service access. Do you need an exploded view or manufacturing drawings?"
        )
        first_reply = (
            f"Use {components}. Some parts will be new, but I have not supplied their interface "
            "dimensions or motion limits. I need an editable assembly and an exploded view."
        )
        follow = (
            "I have recorded the component list, editable assembly requirement and exploded-view "
            "deliverable. Please identify the reference component and provide the interface axes/"
            "faces or source part files. Also confirm the intended joint motion and its limits. "
            "I will not lock components together or invent clearances where the interfaces are unknown."
        )
        second_reply = (
            "Use the housing/base as the reference component. I will provide the source part files "
            "for the remaining components. Show unconfirmed joints as unresolved constraints."
        )
        final = (
            f"Assembly brief: {assembly}; planned components: {components}; reference component: "
            "housing/base; outputs: editable assembly and exploded view. Source component files and "
            "measured interfaces remain required before final constraints are assigned. NextCAD should "
            "preserve component instances, apply only confirmed fixed/revolute/prismatic joints, report "
            "remaining degrees of freedom and flag unresolved constraints rather than guessing."
        )
        add_three_turn_flow("design_intake_assembly_cad", "assembly", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)

    # Sheet-metal / enclosure design: manufacturing and internal packaging.
    enclosures = [
        ("electrical control cabinet", "control equipment, terminals and cable entries"),
        ("desktop computer case", "motherboard, power supply, drives and cooling"),
        ("industrial sensor enclosure", "sensor board, connectors and environmental protection"),
        ("battery enclosure", "battery modules, isolation and thermal management"),
        ("wall-mounted distribution box", "protective devices, busbars and cable routing"),
        ("instrument enclosure", "display, circuit board, controls and connectors"),
        ("pump control panel", "controller, switches, indicators and cable glands"),
        ("small network cabinet", "switches, patch panels, power and airflow"),
    ]
    for i, (name, contents) in enumerate(enclosures):
        prompt = f"Design a sheet-metal {name} in CAD."
        first = (
            f"I can prepare the {name}. Please confirm the internal items ({contents}), "
            "overall width/height/depth, preferred sheet material and thickness if known, "
            "mounting method, access-panel/door arrangement, connector and cable openings, "
            "cooling/ventilation needs, and the manufacturing method. Do you have a target "
            "environmental/IP rating or electrical/thermal requirements from the project?"
        )
        first_reply = (
            f"It must contain {contents}. I need a sheet-metal enclosure with a removable access "
            "panel, but the final dimensions and sheet thickness are not fixed yet."
        )
        follow = (
            "Recorded: the internal equipment, sheet-metal construction and removable access panel. "
            "Please provide the component layout or largest component dimensions, plus the intended "
            "mounting points. Should I create an editable enclosure envelope with provisional bend "
            "and thickness parameters, clearly marked for confirmation?"
        )
        second_reply = (
            "Yes. Use a provisional editable envelope and clearly named parameters. Do not claim an "
            "IP rating, electrical clearance or thermal performance until I provide verified data."
        )
        final = (
            f"Enclosure brief: {name}; contents: {contents}; construction: sheet metal; access: "
            "removable panel; envelope, material and thickness: provisional named parameters awaiting "
            "confirmation. NextCAD can create an editable base sheet, flanges, bends and access panel "
            "with a flat-pattern check. Cable openings, clearances, ventilation, grounding and any "
            "IP/electrical/thermal rating remain unverified until approved data and relevant tests exist."
        )
        add_three_turn_flow("design_intake_sheet_metal_cad", "sheet-metal", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)

    # BIM new-build intake: the output is an information model as well as geometry.
    bim_projects = [
        ("three-storey residential apartment building", "residential", "architecture, structure and MEP"),
        ("single-storey school", "education", "architecture, structure, HVAC, electrical and plumbing"),
        ("small hospital", "healthcare", "architecture, structure, HVAC, electrical, plumbing and medical services"),
        ("office building", "commercial", "architecture, structure and building services"),
        ("warehouse", "industrial/storage", "architecture, structure, fire protection and electrical"),
        ("hotel", "hospitality", "architecture, structure, HVAC, plumbing, electrical and interiors"),
        ("shopping centre", "retail", "architecture, structure, HVAC, electrical, plumbing and fire protection"),
        ("residential bungalow", "residential", "architecture, structure, plumbing and electrical"),
        ("university laboratory", "education/research", "architecture, structure, HVAC, electrical and specialist services"),
        ("mixed-use development", "mixed use", "architecture, structure, MEP, site works and vertical circulation"),
    ]
    for i, (project, use, disciplines) in enumerate(bim_projects):
        prompt = f"Create a BIM model for a {project}."
        first = (
            f"I can set up the BIM project for the {project}. Before modelling, please confirm: "
            f"(1) project location and governing jurisdiction, (2) site survey, coordinate reference "
            "and vertical datum, (3) building use and occupancy, number of storeys and approximate "
            "floor area, (4) which disciplines are in scope—such as "
            f"{disciplines}, (5) required model detail and information (geometry and asset data), "
            "(6) deliverables such as schedules, quantities, issue coordination and IFC export, "
            "including the required IFC schema/version, and (7) project units and naming/classification "
            "standards. Are you starting from drawings, a survey, or an existing model?"
        )
        first_reply = (
            f"It is a {use} project. Include {disciplines}. I need a coordinated BIM model and "
            "IFC exchange, but I have not supplied the survey, coordinate system or information "
            "requirements yet."
        )
        follow = (
            "Recorded: project use, requested disciplines, coordinated BIM model and IFC exchange. "
            "For a reliable setup, please provide the site survey or source drawings, project "
            "coordinate reference/vertical datum, target IFC schema, and the required information "
            "level or employer information requirements. I will keep these as unresolved items rather "
            "than invent coordinates, levels, classifications or asset properties."
        )
        second_reply = (
            "I will provide the survey and employer information requirements. Start with the project "
            "structure, storeys, discipline model breakdown and an information-delivery checklist. "
            "Keep the IFC schema configurable until confirmed."
        )
        final = (
            f"BIM brief: project {project}; use {use}; disciplines {disciplines}; required output: "
            "coordinated information model and IFC exchange. Site coordinates, levels, IFC schema "
            "and information requirements remain pending source documents. The next BIMCraft step is "
            "to create the project structure, storeys, discipline containers and an information-delivery "
            "checklist. Do not fabricate survey coordinates or claim IDS/IFC validation before running "
            "the agreed checks on the native model and export."
        )
        add_three_turn_flow("design_intake_bim_new_build", "bim-new", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, bim_system)

    # BIM renovation: teach the model to establish the reliability of existing
    # information before changing the asset.
    renovation_scopes = [
        ("residential extension", "extend living space and add a bedroom"),
        ("office refurbishment", "replan workspaces and upgrade building services"),
        ("school renovation", "refurbish teaching rooms and improve accessibility"),
        ("hospital ward upgrade", "reconfigure clinical spaces and services"),
        ("warehouse conversion", "change the building to a new operational use"),
        ("historic building restoration", "record and conserve significant existing fabric"),
        ("apartment remodelling", "reconfigure selected rooms and wet areas"),
        ("retail fit-out", "adapt an existing shell for a new tenant"),
    ]
    for i, (project, scope) in enumerate(renovation_scopes):
        prompt = f"Update the BIM model for a {project}."
        first = (
            f"I can help with the {project}. First, what is the exact scope ({scope}), and which "
            "elements must remain, be removed or be added? What existing information is available "
            "(verified as-built drawings, survey, point cloud, photographs or IFC model), how current "
            "is it, and who verified it? Please identify the coordinate reference, project phase, "
            "required disciplines, asset information to preserve and the required deliverables."
        )
        first_reply = (
            f"The scope is to {scope}. We have an old PDF plan and photographs, but no verified "
            "as-built model. Some existing dimensions may have changed on site."
        )
        follow = (
            "I have recorded the renovation scope and the source evidence: an old PDF plan and "
            "photographs whose dimensions are not verified. Please arrange a measured survey or "
            "confirm which dimensions have been checked on site, and identify elements that must "
            "not be disturbed. I can prepare an existing-condition information checklist now, but "
            "I must not treat the old drawing as accurate as-built geometry."
        )
        second_reply = (
            "We will commission a measured survey and mark protected elements. For now, prepare an "
            "existing-condition model plan with uncertain dimensions flagged and no destructive edits."
        )
        final = (
            f"Renovation brief: {project}; scope: {scope}; current evidence: old PDF and photographs "
            "only; as-built accuracy: unverified; measured survey: pending; protected elements: to be "
            "identified. Next BIMCraft step: create an existing-condition register with source, date, "
            "confidence and verification status for each element group. Keep uncertain geometry flagged "
            "and do not move/delete existing elements until the survey and scope are approved."
        )
        add_three_turn_flow("design_intake_bim_renovation", "bim-renovation", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, bim_system)

    # Civil infrastructure: request design basis and source survey before
    # creating route geometry or claiming compliance.
    infra_types = [
        ("access road", "road classification, design speed and vehicle type"),
        ("urban drainage network", "catchment, rainfall basis, outfall and allowable discharge"),
        ("pedestrian bridge", "span arrangement, loading basis, clearance and geotechnical data"),
        ("car park", "vehicle mix, capacity, circulation and accessible bays"),
        ("water distribution network", "demand, pressure zones, source, storage and pipe material"),
        ("sewer network", "design flow, ground levels, outfall and maintenance access"),
        ("site grading model", "survey datum, existing/proposed levels, drainage and earthworks limits"),
        ("retaining structure", "retained height, ground profile, soil investigation and water conditions"),
    ]
    for i, (asset, basis) in enumerate(infra_types):
        prompt = f"Design an {asset} in CAD/BIM."
        first = (
            f"I can prepare the {asset} model. Before geometry, please confirm the design basis: "
            f"{basis}; project location and governing authority; source topographic survey and datum; "
            "alignment/site boundary and right-of-way; required capacities or performance criteria; "
            "known geotechnical, utility and environmental constraints; and the required drawing, "
            "quantity and BIM/IFC deliverables. Which inputs are already verified and which are still "
            "estimates?"
        )
        first_reply = (
            f"The project is an {asset}. I have an approximate site sketch, but no verified survey "
            "or complete design basis yet. I need a preliminary model for coordination."
        )
        follow = (
            f"Understood: {asset}, preliminary coordination model, approximate sketch only. Please "
            "provide the verified survey and the project-specific design criteria for {basis}. "
            "Until then, I can prepare a data checklist and an explicitly schematic alignment/site "
            "model, but not dimensioned construction geometry or a compliant engineering design."
        )
        second_reply = (
            "Proceed with a clearly marked schematic coordination model. Keep all unverified levels, "
            "dimensions and capacities as unresolved parameters, and list the documents needed to "
            "advance it to detailed design."
        )
        final = (
            f"Infrastructure brief: {asset}; deliverable: schematic coordination model only; source "
            "survey and design basis: unverified/pending. Keep alignment, levels, capacities and "
            "geotechnical values as unresolved parameters. The next native CAD/BIM step is to create "
            "reference layers, coordinate/datum placeholders and an assumptions register. Do not "
            "produce construction-ready geometry or state regulatory compliance until verified data, "
            "design calculations and jurisdictional reviews are complete."
        )
        add_three_turn_flow("design_intake_civil_infrastructure", "infrastructure", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, ENGINEERING_SYSTEM)

    # Consumer products and industrial design: learn the product's purpose,
    # user, interface, ergonomics and manufacturing route before surfacing.
    products = [
        ("ergonomic task chair", "seated office work", "seat, backrest, armrests, adjustment and base"),
        ("adjustable desk lamp", "task lighting", "base, arm, pivots, light source and controls"),
        ("handheld power drill", "drilling and fastening", "motor, gearbox, chuck, battery and grip"),
        ("insulated water bottle", "carrying hot or cold liquids", "body, lid, seal, mouthpiece and handle"),
        ("storage cabinet", "organising household or office items", "carcase, shelves, doors, hinges and handles"),
        ("manual garden tool", "a defined gardening task", "working head, shaft, grip and attachment"),
        ("portable speaker housing", "portable audio playback", "drivers, enclosure, controls, battery and connectors"),
        ("kitchen appliance", "a specified food-preparation task", "motor or heater, controls, housing, removable parts and guards"),
    ]
    for i, (product, use, components) in enumerate(products):
        prompt = f"Design a {product} in CAD."
        first = (
            f"I can help design the {product}. What task should it perform and who will use it? "
            "Please confirm the working environment, target size/envelope, ergonomic or handling "
            f"needs, and the main components (a starting list could be {components}). "
            "Do any parts need to move, open, rotate, adjust or be removable? Do you have "
            "material and manufacturing preferences, or should I keep them as options? "
            "Finally, do you need a visual concept, editable parametric model, assembly or drawings?"
        )
        first_reply = (
            f"It is for {use}. Include {components}. I want an editable product concept, but "
            "I have not chosen all dimensions, material or manufacturing method."
        )
        follow = (
            f"Recorded: {product} for {use}, with {components}, as an editable concept. "
            "Please provide the target envelope and any critical user-fit or connection dimensions, "
            "or confirm that I may create named editable parameters for them. I will not silently "
            "choose material or manufacturing method; those can remain alternatives until reviewed."
        )
        second_reply = (
            "Use named editable parameters for the unconfirmed dimensions. Show the main parts as "
            "separate editable components and mark material/process choices as options for review."
        )
        final = (
            f"Product brief: {product}; function: {use}; components: {components}; deliverable: "
            "editable parametric concept with separate components. Unconfirmed dimensions remain "
            "named parameters; material and manufacturing method remain alternatives, not decisions. "
            "NextCAD should establish the main envelope and interface skeleton before detailed "
            "features. Ergonomic fit, moving-part clearances and any safety-related performance "
            "must be checked against supplied requirements and appropriate tests."
        )
        add_three_turn_flow("design_intake_consumer_product_cad", "consumer-product", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)

    # Technical drawings: teach the student to ask for drawing conventions,
    # tolerances and controlled requirements rather than inventing them.
    drawing_prompts = [
        "Prepare a manufacturing drawing for my mechanical part.",
        "Create a dimensioned 2D drawing from my CAD model.",
        "Make an assembly drawing with a parts list.",
        "Prepare a sectioned drawing for a machined housing.",
        "Create a fabrication drawing for a welded frame.",
        "Generate sheet-metal flat-pattern and fold drawings.",
        "Prepare an architectural detail drawing from the model.",
        "Create a civil engineering setting-out drawing.",
    ]
    for i, prompt in enumerate(drawing_prompts):
        first = (
            "I can prepare the drawing package. Please confirm the exact part/model revision, "
            "units, sheet size and scale, projection method, required orthographic/section/detail "
            "views, dimensions and datum scheme, material and surface finish, tolerances/GD&T, "
            "revision/title-block information, and the required drawing standard with jurisdiction "
            "and edition. Which values are already defined in the model, and which must remain TBD?"
        )
        first_reply = (
            "Use the current model revision and millimetres. I need the drawing views and dimensions, "
            "but the material, tolerances and drawing standard have not been confirmed."
        )
        follow = (
            "I have the model-revision and millimetre requirements. Please confirm the projection "
            "method and sheet size. For material, tolerances, finish and the governing drawing "
            "standard, should I leave them explicitly marked TBD until approved information is supplied? "
            "I will not invent tolerance values or claim standards compliance."
        )
        second_reply = (
            "Use first-angle projection and A3 sheets. Leave material, tolerances, finish and standard "
            "references as TBD; flag them in the drawing issue checklist."
        )
        final = (
            "Drawing brief: use the current model revision, millimetres, first-angle projection and "
            "A3 sheets. Produce the requested views and dimensions from the verified model. Material, "
            "tolerances, finish and governing standard remain TBD and must be listed as open items. "
            "Do not fabricate GD&T values or mark the drawing approved for manufacture until those "
            "requirements are confirmed and the drawing is checked."
        )
        add_three_turn_flow("design_intake_technical_drawing_cad", "technical-drawing", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)

    # CAM preparation: gather machine, stock and tooling data before toolpath
    # or controller-specific output can be considered.
    cam_prompts = [
        "Prepare CNC machining for this plate.",
        "Generate a milling setup for a mechanical bracket.",
        "Prepare a drilling toolpath for a hole pattern.",
        "Set up a turning operation for a shaft.",
        "Create a CAM plan for a pocketed aluminium component.",
        "Prepare a machining plan for a steel housing.",
        "Set up a 3-axis milling job for a fixture plate.",
        "Prepare a router job for a sheet material part.",
    ]
    for i, prompt in enumerate(cam_prompts):
        first = (
            "Before preparing toolpaths, please confirm the stock material and stock dimensions, "
            "the exact machine and axis configuration, controller/postprocessor, workholding and "
            "work coordinate system, cutting tools and holders, required operations, tolerances and "
            "surface finish. Feeds, speeds, stepovers and cut depths must come from approved data for "
            "the actual machine, tool and material. Do you need a setup sheet, simulation, toolpaths "
            "or controller-specific output?"
        )
        first_reply = (
            "I need a CAM setup plan for this part. The material is known, but I have not supplied "
            "the machine, controller, tool list or workholding details."
        )
        follow = (
            "I have recorded the need for a CAM setup plan and the known material. Please supply the "
            "machine/controller, stock size, fixture/workholding, work coordinate origin and tool/holder "
            "list. Until then I can prepare an operation checklist with unresolved parameters, but "
            "must not invent cutting data, simulate an unverified machine or generate controller G-code."
        )
        second_reply = (
            "Prepare the operation checklist and setup-data template only. Keep machine, fixture, tools, "
            "feeds, speeds, depths and postprocessor unresolved until the machinist supplies them."
        )
        final = (
            "CAM brief: prepare an operation checklist and setup-data template only. Machine, "
            "controller, stock dimensions, workholding, tools, cutting data and postprocessor remain "
            "unresolved. NextCAD may organise the model features and identify candidate operations, "
            "but no executable toolpath or G-code should be produced until the real setup is verified "
            "and the simulation/collision review passes."
        )
        add_three_turn_flow("design_intake_cam_cad", "cam", i + 1,
                            prompt, first, first_reply, follow, second_reply, final, cad_system)


    # Dedicated guard/watchtower interview, including the user's concrete-vs-steel decision.
    for i, material in enumerate([
        "steel frame", "reinforced concrete", "steel frame", "reinforced concrete",
        "timber frame", "steel frame", "reinforced concrete", "steel frame",
    ], 1):
        prompt = [
            "I need a wash tower where security people can stay.",
            "Design a watch tower for security officers.",
            "I need a guard tower overlooking the entrance.",
            "Create an elevated security lookout tower.",
            "Make a watchtower for two security guards.",
            "Design a small tower for site security staff.",
            "I want a guard post above the perimeter wall.",
            "Create an observation tower for security personnel.",
        ][i - 1]
        first = (
            "Do you mean a watchtower/guard tower where security staff can stay and observe the site? "
            "Before I design it, please confirm: (1) the structure you prefer—steel frame, reinforced "
            "concrete, timber or another system; (2) how many people must occupy the cabin; "
            "(3) the observation-platform height above ground; (4) cabin width/depth and any desk, "
            "seating, storage or equipment needs; (5) stair or ladder access; (6) roof, doors, windows, "
            "guardrails, lighting and power; and (7) site survey, ground information and wind exposure. "
            "Do you need a visual concept or an engineered construction design?"
        )
        first_reply = (
            f"Yes, a guard watchtower. Use a {material}, for two security officers. "
            f"Set the platform around {6000 + ((i - 1) % 3) * 1000} mm above ground and cover the cabin. "
            "I want an editable visual concept first, not a certified design."
        )
        follow = (
            f"Recorded: watchtower for two officers; material intent {material}; platform height about "
            f"{6000 + ((i - 1) % 3) * 1000} mm; covered cabin; concept only. Please confirm the cabin "
            "footprint, preferred stair or ladder, and whether I may use clearly labelled placeholder "
            "envelopes for columns and beams. A safe structural design still needs the site survey, wind "
            "exposure, occupancy/equipment loads, geotechnical/foundation information, connections and "
            "the governing design standard."
        )
        second_reply = (
            "Use a 4000 mm by 4000 mm support footprint and a 2600 mm by 2600 mm cabin. "
            f"Keep the {material} concept, use a stair and roof, and show placeholder member envelopes "
            "only for visual coordination. I will provide site, wind and soil information before sizing."
        )
        final = (
            f"Confirmed watchtower brief: {material}; two occupants; platform +"
            f"{6000 + ((i - 1) % 3) * 1000} mm; 4000 × 4000 mm support footprint; 2600 × 2600 mm cabin; "
            "covered cabin; stair access requested; visual concept only. Editable column/beam/cabin/roof "
            "envelopes may be created and labelled as placeholders. The material intent is not yet "
            "assigned as verified native material data, and the placeholder sizes are not engineered "
            "sections. Stair, guardrails, openings, foundations, connections, wind and soil design remain "
            "to be modelled/checked from verified inputs. No load capacity, wind resistance, foundation "
            "adequacy or construction readiness is claimed."
        )
        add_three_turn_flow(
            "design_intake_watchtower_architecture", "watchtower", i,
            prompt, first, first_reply, follow, second_reply, final, architecture_system
        )

    return lessons



def make_design_execution_curriculum() -> list[dict[str, Any]]:
    """Teach the student to turn approved design briefs into editable native operations."""
    lessons: list[dict[str, Any]] = []

    def add(domain: str, prompt: str, message: str, plan: list[dict[str, Any]]) -> None:
        lessons.append({
            "domain": domain,
            "system": CAD_SYSTEM,
            "prompt": prompt,
            "completion": json.dumps({"message": message, "plan": plan}, ensure_ascii=False),
        })

    floorplan_plan = [
        {"tool": "create_draft_wire", "args": {"points": [[0,0],[16000,0],[16000,12000],[0,12000]], "closed": True, "label": "A-00 — 3 bedroom bungalow outline"}},
        {"tool": "create_draft_wire", "args": {"points": [[0,8000],[5000,8000],[5000,12000],[0,12000]], "closed": True, "label": "A-01 — Master bedroom"}},
        {"tool": "create_draft_wire", "args": {"points": [[0,6000],[2500,6000],[2500,8000],[0,8000]], "closed": True, "label": "A-02 — Master ensuite"}},
        {"tool": "create_draft_wire", "args": {"points": [[0,2000],[5000,2000],[5000,6000],[0,6000]], "closed": True, "label": "A-03 — Bedroom 2"}},
        {"tool": "create_draft_wire", "args": {"points": [[5000,6000],[11000,6000],[11000,12000],[5000,12000]], "closed": True, "label": "A-04 — Sitting and living"}},
        {"tool": "create_draft_wire", "args": {"points": [[5000,4000],[7000,4000],[7000,6000],[5000,6000]], "closed": True, "label": "A-05 — Store"}},
        {"tool": "create_draft_wire", "args": {"points": [[11000,4000],[16000,4000],[16000,8000],[11000,8000]], "closed": True, "label": "A-06 — Kitchen and dining"}},
        {"tool": "create_draft_wire", "args": {"points": [[11000,8000],[16000,8000],[16000,12000],[11000,12000]], "closed": True, "label": "A-07 — Bedroom 3"}},
        {"tool": "create_draft_wire", "args": {"points": [[11000,2000],[13500,2000],[13500,4000],[11000,4000]], "closed": True, "label": "A-08 — Shared bathroom"}},
        {"tool": "create_draft_text", "args": {"text": "MASTER BEDROOM\n5.0 × 4.0 m", "position": [1200,9800], "height": 250, "label": "Room label — master bedroom"}},
        {"tool": "create_draft_text", "args": {"text": "ENSUITE\n2.5 × 2.0 m", "position": [300,6800], "height": 180, "label": "Room label — ensuite"}},
        {"tool": "create_draft_text", "args": {"text": "BEDROOM 2\n5.0 × 4.0 m", "position": [1200,3800], "height": 250, "label": "Room label — bedroom 2"}},
        {"tool": "create_draft_text", "args": {"text": "SITTING / LIVING\n6.0 × 6.0 m", "position": [6500,9000], "height": 250, "label": "Room label — sitting room"}},
        {"tool": "create_draft_text", "args": {"text": "STORE\n2.0 × 2.0 m", "position": [5200,4800], "height": 160, "label": "Room label — store"}},
        {"tool": "create_draft_text", "args": {"text": "KITCHEN / DINING\n5.0 × 4.0 m", "position": [11600,5600], "height": 230, "label": "Room label — kitchen and dining"}},
        {"tool": "create_draft_text", "args": {"text": "BEDROOM 3\n5.0 × 4.0 m", "position": [11600,9800], "height": 250, "label": "Room label — bedroom 3"}},
        {"tool": "create_draft_text", "args": {"text": "SHARED BATH\n2.5 × 2.0 m", "position": [11050,2800], "height": 160, "label": "Room label — shared bathroom"}},
        {"tool": "create_draft_dimension", "args": {"start": [0,0], "end": [16000,0], "dimension_line_point": [8000,-700], "label": "Overall plan width — 16000 mm"}},
        {"tool": "create_draft_dimension", "args": {"start": [0,0], "end": [0,12000], "dimension_line_point": [-700,6000], "label": "Overall plan depth — 12000 mm"}},
    ]
    add(
        "design_execution_residential_floorplan",
        "The user approved a 3-bedroom bungalow concept in NextCAD: one master bedroom with ensuite, two other bedrooms, one shared bathroom (two toilet/bathroom rooms total), one sitting room, one store, and a kitchen/dining area. Use a 16000 × 12000 mm concept envelope and these room zones: master 0,8000–5000,12000; ensuite 0,6000–2500,8000; bedroom 2 0,2000–5000,6000; sitting 5000,6000–11000,12000; store 5000,4000–7000,6000; kitchen/dining 11000,4000–16000,8000; bedroom 3 11000,8000–16000,12000; shared bathroom 11000,2000–13500,4000. Create editable native 2D room zoning.",
        "I will build native editable Draft geometry, not a generated picture. The 16000 × 12000 mm outline contains the agreed room zones and labels, with two overall dimensions. This is a 2D room-zoning concept only: doors, windows, openings, wall thicknesses, setbacks, access, ventilation and local planning checks are not yet modelled or verified.",
        floorplan_plan,
    )

    watchtower_plan = []
    for i, origin in enumerate(([0,0,0],[3700,0,0],[0,3700,0],[3700,3700,0]), 1):
        watchtower_plan.append({"tool": "create_arch_structure", "args": {
            "length": 300, "width": 300, "height": 6000, "origin": origin,
            "label": f"C{i:02d} — column envelope 300×300×6000 — concept placeholder"
        }})
    for i, (length, width, origin) in enumerate((
        (4000,250,[0,0,5600]), (4000,250,[0,3750,5600]),
        (250,4000,[0,0,5600]), (250,4000,[3750,0,5600]),
    ), 1):
        watchtower_plan.append({"tool": "create_part_box", "args": {
            "length": length, "width": width, "height": 400, "origin": origin,
            "label": f"B{i:02d} — perimeter beam envelope — concept only, not engineered"
        }})
    watchtower_plan.append({"tool": "create_part_box", "args": {
        "length": 4000, "width": 4000, "height": 250, "origin": [0,0,6000],
        "label": "D01 — elevated deck 4000×4000×250 — concept placeholder"
    }})
    for label, points in [
        ("W01 — cabin front wall", [[700,700,6250],[3300,700,6250]]),
        ("W02 — cabin right wall", [[3300,700,6250],[3300,3300,6250]]),
        ("W03 — cabin rear wall", [[3300,3300,6250],[700,3300,6250]]),
        ("W04 — cabin left wall", [[700,3300,6250],[700,700,6250]]),
    ]:
        watchtower_plan.append({"tool": "create_arch_wall", "args": {
            "points": points, "height": 2300, "width": 150, "label": label
        }})
    watchtower_plan.append({"tool": "create_part_box", "args": {
        "length": 3000, "width": 3000, "height": 150, "origin": [500,500,8550],
        "label": "R01 — cabin roof envelope 3000×3000×150 — concept placeholder"
    }})
    watchtower_plan.extend([
        {"tool": "create_draft_dimension", "args": {
            "start": [0,-500,0], "end": [4000,-500,0], "dimension_line_point": [2000,-900,0],
            "label": "Support footprint width — 4000 mm"
        }},
        {"tool": "create_draft_dimension", "args": {
            "start": [0,0,0], "end": [0,0,8700], "dimension_line_point": [-900,0,4350],
            "label": "Concept overall height — 8700 mm"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "GUARD WATCHTOWER — STEEL INTENT CONCEPT ONLY\n"
                    "2 occupants | platform +6000 mm | support footprint 4000×4000 mm\n"
                    "Cabin 2600×2600 mm | wall height 2300 mm | roof 3000×3000 mm\n"
                    "C01-C04: 300×300 mm column envelopes; B01-B04: 250×400 mm beam envelopes\n"
                    "Member envelopes are visual placeholders, NOT engineered sizes. No verified "
                    "material assignment has been made. Access stair, door/window openings, guardrails, "
                    "foundations, connections, wind and geotechnical design remain open.",
            "position": [4500,500,8700], "height": 150, "label": "Watchtower notes and member schedule"
        }}
    ])
    add(
        "design_execution_watchtower_concept",
        "The user approved an editable visual concept for a steel-intent watchtower for two guards: 4000×4000 mm support footprint, observation platform at +6000 mm, 2600×2600 mm cabin, 2300 mm cabin wall height and a roof. The user explicitly approved visible placeholder envelopes only: 300×300×6000 mm columns, 250×400 mm perimeter beam envelopes, 4000×4000×250 mm deck and 3000×3000×150 mm roof. Create the native concept and identify what remains unmodelled. Do not present the envelopes as engineered steel sections or assign a material that the tools cannot set.",
        "I will create the editable 3D tower concept with native Arch structure/wall objects and parametric box components. Supports, beams, deck, cabin walls and roof are individually named. I will add overall dimensions and a member schedule. This is visual coordination geometry only: the stair, guardrails, door/window openings, foundations and connections are not modelled, and the listed member envelopes are not structurally designed or material-assigned.",
        watchtower_plan,
    )

    mechanical_plan = [
        {"tool": "create_partdesign_body", "args": {"name": "GearHousingBody"}},
        {"tool": "create_partdesign_sketch", "args": {"body_name": "GearHousingBody", "name": "HousingBaseProfile", "plane": "XY_Plane", "offset": 0}},
        {"tool": "add_sketch_polygon", "args": {"sketch_name": "HousingBaseProfile", "points": [[0,0],[200,0],[200,150],[0,150]]}},
        {"tool": "create_partdesign_pad", "args": {"body_name": "GearHousingBody", "sketch_name": "HousingBaseProfile", "length": 80, "name": "HousingBasePad"}},
        {"tool": "create_partdesign_sketch", "args": {"body_name": "GearHousingBody", "name": "MountingHoleProfile", "plane": "XY_Plane", "offset": 80}},
        {"tool": "add_sketch_circle", "args": {"sketch_name": "MountingHoleProfile", "center": [15,15], "radius": 6, "label": "Mounting hole 1"}},
        {"tool": "add_sketch_circle", "args": {"sketch_name": "MountingHoleProfile", "center": [185,15], "radius": 6, "label": "Mounting hole 2"}},
        {"tool": "add_sketch_circle", "args": {"sketch_name": "MountingHoleProfile", "center": [185,135], "radius": 6, "label": "Mounting hole 3"}},
        {"tool": "add_sketch_circle", "args": {"sketch_name": "MountingHoleProfile", "center": [15,135], "radius": 6, "label": "Mounting hole 4"}},
        {"tool": "create_partdesign_pocket", "args": {"body_name": "GearHousingBody", "sketch_name": "MountingHoleProfile", "length": 80, "through_all": True, "reversed": False, "name": "FourMountingHoles"}},
    ]
    add(
        "design_execution_parametric_mechanical_part",
        "Create an editable parametric mounting base for a gear-housing concept in NextCAD. Approved envelope: 200×150×80 mm; four 12 mm diameter through-holes, centres 15 mm from each adjacent edge. Use a native PartDesign body, constrained profile, Pad and Pocket feature history. Do not choose material, loads or tolerances.",
        "I will create a native PartDesign body with a fully constrained 200×150 mm base sketch, pad it 80 mm, then add four 12 mm through-holes using a second sketch and pocket. The object stays editable in the PartDesign feature tree. Material, tolerances, loads and functional capacity are not specified, so none will be assumed.",
        mechanical_plan,
    )

    edit_plan = [
        {"tool": "edit_native_property", "args": {"object_name": "B01Beam", "property_name": "Width", "value": 300}},
        {"tool": "edit_native_property", "args": {"object_name": "B01Beam", "property_name": "Height", "value": 450}},
        {"tool": "edit_native_property", "args": {"object_name": "B01Beam", "property_name": "Label", "value": "B01 — revised beam envelope 4000×300×450 mm — concept only"}},
    ]
    add(
        "design_execution_edit_existing_model",
        "The open NextCAD document inspection shows an existing Part::Box object whose exact Name is B01Beam, currently Width=250 mm and Height=400 mm. The user explicitly asks to change this existing beam envelope to Width=300 mm and Height=450 mm, then update its label. Do not create another beam.",
        "I will edit the existing B01Beam in place: update its Width and Height, then change its label. I will not create a duplicate. The native document recomputes after each change, and I will report the before-and-after values.",
        edit_plan,
    )



    # Vehicle package concept: teach the student to select native primitives
    # by geometric role and build the model as separately editable components.
    vehicle_plan = [
        {"tool": "create_part_box", "args": {
            "length": 4200, "width": 1800, "height": 250, "origin": [0,0,0],
            "label": "CH01 — chassis envelope 4200×1800×250 mm — concept only"
        }},
        {"tool": "create_part_box", "args": {
            "length": 3200, "width": 1400, "height": 1000, "origin": [500,200,600],
            "label": "BD01 — passenger body envelope 3200×1400×1000 mm — concept only"
        }},
    ]
    for mark, x, y in (
        ("WH01", 700, -220), ("WH02", 3500, -220),
        ("WH03", 700, 1800), ("WH04", 3500, 1800),
    ):
        vehicle_plan.append({"tool": "create_part_cylinder", "args": {
            "radius": 350, "height": 220, "origin": [x,y,350], "axis": [0,1,0],
            "label": f"{mark} — wheel envelope Ø700×220 mm — concept only"
        }})
    vehicle_plan.extend([
        {"tool": "create_draft_dimension", "args": {
            "start": [0,0,0], "end": [4200,0,0], "dimension_line_point": [2100,-700,0],
            "label": "Vehicle package length — 4200 mm"
        }},
        {"tool": "create_draft_dimension", "args": {
            "start": [0,0,0], "end": [0,1800,0], "dimension_line_point": [-700,900,0],
            "label": "Chassis package width — 1800 mm"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "VEHICLE PACKAGE CONCEPT — NOT A ROAD-READY DESIGN\n"
                    "CH01 chassis envelope; BD01 body envelope; WH01-WH04 wheel envelopes.\n"
                    "No suspension, steering, braking, drivetrain, crash structure, materials, "
                    "clearances or regulatory validation are included.",
            "position": [4500,0,0], "height": 160, "label": "Vehicle concept scope and component schedule"
        }}
    ])
    add(
        "design_execution_vehicle_package",
        "The user approved a simple editable vehicle packaging concept with these explicit dimensions: chassis envelope 4200×1800×250 mm; passenger body envelope 3200×1400×1000 mm at [500,200,600] mm; four wheel envelopes diameter 700 mm and width 220 mm, with wheel centres at x=700/3500 mm and z=350 mm on both sides of the chassis. Use separate native Part boxes for chassis/body and native cylinders for wheels. Add dimensions and a component note. Do not claim suspension, steering, brakes, powertrain, crashworthiness or road legality.",
        "I will create separate editable chassis, body and four wheel-envelope components. Cylinders are appropriate for the wheel envelopes, while boxes are only packaging placeholders for the chassis and body. I will add the overall package dimensions and a note identifying the systems that are not modelled. This is not a functional or road-ready vehicle.",
        vehicle_plan,
    )

    # Teach primitive selection from geometry intent rather than using a box
    # for every object. All dimensions below are explicit concept inputs.
    add(
        "design_execution_cylindrical_shaft",
        "Create an editable native shaft concept in NextCAD. Approved dimensions: radius 20 mm, length 240 mm, origin [0,0,0], axis [0,0,1]. Use the correct native primitive and label it SH01. Do not infer material, fit or torque capacity.",
        "A shaft is rotationally symmetric, so I will use a native editable Part cylinder with a 20 mm radius and 240 mm length along the Z axis. Material, fit, torque capacity and tolerances remain unspecified.",
        [{"tool": "create_part_cylinder", "args": {
            "radius": 20, "height": 240, "origin": [0,0,0], "axis": [0,0,1],
            "label": "SH01 — shaft concept Ø40×240 mm"
        }}],
    )
    add(
        "design_execution_spherical_component",
        "Create an editable native spherical knob concept. The user approved a 35 mm radius and centre [0,0,0]. Use the native sphere primitive and label it KN01. Do not infer material or ergonomic suitability.",
        "A spherical knob is best represented by a native editable Part sphere, not a faceted picture or a rectangular block. I will use the approved 35 mm radius and centre. Material and ergonomic suitability remain open.",
        [{"tool": "create_part_sphere", "args": {
            "radius": 35, "center": [0,0,0], "label": "KN01 — spherical knob concept R35 mm"
        }}],
    )
    add(
        "design_execution_tapered_nozzle",
        "Create an editable native tapered nozzle concept in NextCAD. Approved dimensions: base radius 40 mm, tip radius 10 mm, height 120 mm, origin [0,0,0], axis [0,0,1]. Use the correct native primitive and label NZ01. Do not infer flow capacity, pressure rating or material.",
        "A tapered nozzle is represented by a native editable Part cone/frustum with two end radii. I will use the approved 40 mm and 10 mm radii over 120 mm height. This geometry alone does not establish flow capacity, pressure rating or material suitability.",
        [{"tool": "create_part_cone", "args": {
            "radius1": 40, "radius2": 10, "height": 120, "origin": [0,0,0], "axis": [0,0,1],
            "label": "NZ01 — tapered nozzle concept R40/R10×120 mm"
        }}],
    )


    # Three-dimensional architectural shell: these are actual native Arch
    # walls, not merely closed 2D room-zone outlines.
    shell_plan = []
    for mark, points in [
        ("W01 — south external wall", [[0,0],[10000,0]]),
        ("W02 — east external wall", [[10000,0],[10000,8000]]),
        ("W03 — north external wall", [[10000,8000],[0,8000]]),
        ("W04 — west external wall", [[0,8000],[0,0]]),
        ("W05 — main internal partition", [[4000,0],[4000,8000]]),
        ("W06 — secondary internal partition", [[7000,0],[7000,4000]]),
        ("W07 — lower room partition", [[4000,4000],[10000,4000]]),
    ]:
        shell_plan.append({"tool": "create_arch_wall", "args": {
            "points": points, "height": 3000, "width": 200, "label": mark
        }})
    shell_plan.extend([
        {"tool": "create_draft_text", "args": {
            "text": "ROOM A — 4.0 × 8.0 m", "position": [500,4200], "height": 220,
            "label": "Room A annotation"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "ROOM B — 3.0 × 4.0 m", "position": [4300,6000], "height": 180,
            "label": "Room B annotation"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "ROOM C — 3.0 × 4.0 m", "position": [7300,6000], "height": 180,
            "label": "Room C annotation"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "ROOM D — 6.0 × 4.0 m", "position": [4300,1500], "height": 220,
            "label": "Room D annotation"
        }},
        {"tool": "create_draft_dimension", "args": {
            "start": [0,0], "end": [10000,0], "dimension_line_point": [5000,-700],
            "label": "External width — 10000 mm"
        }},
        {"tool": "create_draft_dimension", "args": {
            "start": [0,0], "end": [0,8000], "dimension_line_point": [-700,4000],
            "label": "External depth — 8000 mm"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "3D ARCHITECTURAL WALL SHELL — CONCEPT ONLY\n"
                    "Native Arch wall objects, each separately named and editable.\n"
                    "Wall height 3000 mm and thickness 200 mm are approved concept inputs.\n"
                    "Door/window openings, wall joins, room objects, lintels, services, "
                    "setbacks and local approval checks are not included.",
            "position": [10300,0], "height": 150, "label": "3D shell scope and assumptions"
        }},
    ])
    add(
        "design_execution_3d_architectural_wall_shell",
        "The user approved a simple 3D architectural shell in NextCAD, 10000×8000 mm overall, 3000 mm wall height and 200 mm wall thickness. The room zoning is: Room A on the west side; Rooms B and C in the north-east half; Room D in the south-east half. Build four separate exterior Arch walls and three separate internal Arch partitions using the exact supplied coordinates. Add room labels and two overall dimensions. Do not claim doors, windows, spaces or wall openings have been created.",
        "I will create seven separate native Arch wall objects, each with its own editable label, then add room annotations and overall dimensions. This is a 3D wall-shell concept, not just a picture or a set of 2D room outlines. Doors, windows, openings, wall joins and room/space objects are not yet included or verified.",
        shell_plan,
    )

    # Enclosure modelling: separate body, cover, mounting feet and cable
    # entry envelopes so later changes do not destroy the component identities.
    enclosure_plan = [
        {"tool": "create_part_box", "args": {
            "length": 600, "width": 400, "height": 500, "origin": [0,0,0],
            "label": "ENC01 — cabinet external envelope 600×400×500 mm — concept"
        }},
        {"tool": "create_part_box", "args": {
            "length": 620, "width": 420, "height": 40, "origin": [-10,-10,500],
            "label": "COV01 — removable cover envelope 620×420×40 mm — concept"
        }},
    ]
    for mark, x, y in (
        ("FT01", 30, 30), ("FT02", 530, 30), ("FT03", 30, 330), ("FT04", 530, 330),
    ):
        enclosure_plan.append({"tool": "create_part_box", "args": {
            "length": 40, "width": 40, "height": 60, "origin": [x,y,-60],
            "label": f"{mark} — mounting foot envelope 40×40×60 mm"
        }})
    for mark, x, y in (("CG01", 150, 0), ("CG02", 300, 0), ("CG03", 450, 0)):
        enclosure_plan.append({"tool": "create_part_cylinder", "args": {
            "radius": 15, "height": 30, "origin": [x,y,200], "axis": [0,1,0],
            "label": f"{mark} — cable-entry envelope Ø30 mm"
        }})
    enclosure_plan.append({"tool": "create_draft_text", "args": {
        "text": "ELECTRICAL CABINET CONCEPT — EXTERNAL ENVELOPES ONLY\n"
                "ENC01 cabinet; COV01 cover; FT01-FT04 feet; CG01-CG03 cable-entry envelopes.\n"
                "Internal rails, component clearances, ventilation, earthing, IP rating, "
                "electrical separation and thermal performance are not modelled or verified.",
        "position": [700,0,0], "height": 100, "label": "Cabinet component schedule and exclusions"
    }})
    add(
        "design_execution_electrical_cabinet",
        "Create an editable visual concept for an electrical cabinet in NextCAD. Approved external envelope is 600×400×500 mm. Add a separate 620×420×40 mm cover, four 40×40×60 mm mounting feet, and three Ø30 mm cable-entry envelopes. Keep every component separately named and editable. Do not claim the enclosure is hollow, IP-rated, electrically safe, thermally adequate or ready for fabrication.",
        "I will create separately editable cabinet, cover, mounting-foot and cable-entry envelope objects, then add a component schedule. The current toolset creates external primitive envelopes; it does not hollow the cabinet or verify internal electrical clearances, ventilation, earthing, ingress protection or thermal performance.",
        enclosure_plan,
    )

    # Annular PartDesign sketch and Pad demonstrate a genuinely hollow tube,
    # unlike overlaying two primitive cylinders.
    tube_plan = [
        {"tool": "create_partdesign_body", "args": {"name": "TubeBody"}},
        {"tool": "create_partdesign_sketch", "args": {"body_name": "TubeBody", "name": "TubeSection", "plane": "XY_Plane", "offset": 0}},
        {"tool": "add_sketch_circle", "args": {"sketch_name": "TubeSection", "center": [0,0], "radius": 25, "label": "Tube outside radius"}},
        {"tool": "add_sketch_circle", "args": {"sketch_name": "TubeSection", "center": [0,0], "radius": 20, "label": "Tube inside radius"}},
        {"tool": "create_partdesign_pad", "args": {"body_name": "TubeBody", "sketch_name": "TubeSection", "length": 500, "name": "TubeExtrusion"}},
    ]
    add(
        "design_execution_parametric_hollow_tube",
        "Create an editable hollow tube in NextCAD using native PartDesign. Approved dimensions: outside diameter 50 mm, inside diameter 40 mm, length 500 mm. Use one annular sketch with two concentric circles, then Pad the ring profile. Do not substitute overlapping solid cylinders, and do not infer material, pressure rating or flow capacity.",
        "I will create a PartDesign body, sketch the two concentric circles (radii 25 and 20 mm), and pad the annular profile 500 mm. This creates one editable hollow tube feature rather than two overlapping primitive solids. Material, wall-pressure rating, flow capacity and manufacturing tolerances remain unspecified.",
        tube_plan,
    )

    # Pump package: identify each native component by mark, but leave the
    # internal impeller, seals, shaft clearances and performance unresolved.
    pump_plan = [
        {"tool": "create_part_cylinder", "args": {
            "radius": 100, "height": 180, "origin": [0,0,0], "axis": [0,0,1],
            "label": "PC01 — pump casing external envelope Ø200×180 mm — concept"
        }},
        {"tool": "create_part_cylinder", "args": {
            "radius": 20, "height": 260, "origin": [0,0,-40], "axis": [0,0,1],
            "label": "SH01 — shaft envelope Ø40×260 mm — concept"
        }},
        {"tool": "create_part_cylinder", "args": {
            "radius": 80, "height": 20, "origin": [0,0,60], "axis": [0,0,1],
            "label": "IM01 — impeller disc envelope Ø160×20 mm — concept only"
        }},
        {"tool": "create_part_box", "args": {
            "length": 300, "width": 180, "height": 25, "origin": [-150,-90,-25],
            "label": "PB01 — pump mounting base envelope 300×180×25 mm"
        }},
        {"tool": "create_draft_text", "args": {
            "text": "PUMP PACKAGE CONCEPT\nPC01 casing envelope; SH01 shaft envelope; IM01 impeller disc envelope; PB01 base.\n"
                    "Flow path, internal volute, clearances, seals, bearings, materials, pressure "
                    "rating, duty point and hydraulic performance are not modelled or validated.",
            "position": [350,0,0], "height": 100, "label": "Pump component schedule and scope"
        }},
    ]
    add(
        "design_execution_pump_package",
        "Create an editable pump package concept with approved envelope inputs: casing Ø200×180 mm, shaft Ø40×260 mm, impeller-disc envelope Ø160×20 mm and mounting base 300×180×25 mm. Build each as a separately labelled native object. This is a package arrangement only: do not claim that the internal volute, sealing, bearing arrangement, flow path or hydraulic performance is designed.",
        "I will place separately editable casing, shaft, impeller-envelope and mounting-base components. The plan labels each part so it can be inspected and revised independently. Internal hydraulic geometry and hydraulic performance, seals, bearings, material, pressure rating and pump duty are not established by these envelope shapes.",
        pump_plan,
    )

    return lessons


def make_bim_execution_curriculum() -> list[dict[str, Any]]:
    """Teach BIMCraft's live command-discovery and staged model-editing protocol."""
    lessons: list[dict[str, Any]] = []
    operator_system = (
        BIM_SYSTEM + " You are also a BIMCraft native project operator. The only assistant tools are "
        "inspect_model, query_elements, list_commands, execute and todo_write. A command's actual "
        "identifier and parameter schema must be obtained from list_commands at runtime. Never guess "
        "command IDs, fields, enum values or defaults. Call execute only after the exact command and "
        "schema are visible. After each coherent stage, inspect_model or query_elements must confirm "
        "the project state. Edit existing elements by their returned six-digit IDs with modify; do not "
        "delete and recreate to simulate an edit. File open/save/export is performed by the user."
    )

    def add(domain: str, prompt: str, workflow: list[dict[str, Any]], message: str, checks: list[str]) -> None:
        lessons.append({
            "domain": domain,
            "system": operator_system,
            "prompt": prompt,
            "completion": json.dumps({
                "message": message,
                "workflow": workflow,
                "checks": checks,
                "command_execution_rule": (
                    "The workflow lists approved assistant-tool decisions. For every execute step, "
                    "first retrieve the live command catalogue and use only the exact command ID and "
                    "parameter schema returned by list_commands. Do not invent the command or its parameters."
                ),
            }, ensure_ascii=False),
        })

    add(
        "bim_execution_new_build",
        "The user approved a two-storey residential BIM concept. Project survey, coordinate reference and storey heights are supplied in the open brief. Build architecture and prepare the coordinated project without guessing command IDs or schema fields.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "todo_write", "args": {"todos": [
                {"content": "Inspect project levels, units and existing elements", "status": "in_progress"},
                {"content": "Discover native level and grid commands", "status": "pending"},
                {"content": "Create the agreed storey and grid structure", "status": "pending"},
                {"content": "Discover and model walls, floors and openings", "status": "pending"},
                {"content": "Create rooms and verify boundaries", "status": "pending"},
                {"content": "Inspect counts, relationships and warnings", "status": "pending"},
            ]}},
            {"tool": "list_commands", "args": {"filter": "level"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "grid"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "wall"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "floor"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "door"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "window"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "room"}, "stage": "discover"},
            {"tool": "query_elements", "args": {"limit": 200}, "stage": "baseline"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will start by inspecting the live project and its existing levels/elements. Then I will retrieve the exact native command schemas for levels, grids, walls, floors, doors, windows and rooms. I will build in short stages, updating the checklist and inspecting the project between stages. I will not invent BIMCraft command parameters or claim a room is valid until its boundaries are checked.",
        ["Storeys and grids match the supplied survey/project brief", "Wall/floor/opening commands are confirmed from the live catalogue", "Door/window hosting is verified", "Room boundaries and areas are inspected", "Project warnings and element counts are reported"],
    )

    add(
        "bim_execution_watchtower",
        "Create a BIM coordination model for an approved two-occupant guard watchtower concept. The user supplied steel-intent placeholders, support footprint, platform level, cabin dimensions and roof. Do not size the structure or infer code compliance.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "list_commands", "args": {"filter": "level"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "column"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "beam"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "floor"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "wall"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "stair"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "railing"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "schedule"}, "stage": "discover"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will discover the exact BIMCraft commands for levels, columns, beams, floors, walls, stairs, railings and schedules. I will then create the conceptual BIM elements only where their returned schemas support the agreed properties. Member sections remain placeholders, not engineered sizes; the model must record missing material, connection, foundation and site data as open items.",
        ["Column and beam marks remain separately identifiable", "Elements are assigned to the correct level", "Cabin and platform spaces are bounded", "Stair and railing elements are reported as modelled or not modelled", "No structural adequacy is inferred from BIM geometry"],
    )

    add(
        "bim_execution_mep_coordination",
        "Coordinate plumbing, electrical and HVAC for a confirmed small building. The user has supplied equipment locations and service requirements, but pipe/cable/duct sizing and design loads are not yet approved.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "list_commands", "args": {"filter": "pipe"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "plumbing"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "electrical"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "duct"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "connector"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "system"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "schedule"}, "stage": "discover"},
            {"tool": "query_elements", "args": {"limit": 200}, "stage": "baseline"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will inspect the project and discover the live pipe, plumbing, electrical, duct, connector, system and schedule commands. I can coordinate the supplied equipment locations and routes where supported. I will not invent pipe diameters, cable sizes, airflow, circuit loads or pressure ratings. I will check connectors and system membership after each discipline stage.",
        ["Each route is linked to the correct system where native support exists", "Connector endpoints and open ends are checked", "Equipment and terminal relationships are inspected", "Unspecified design sizes/loads remain open", "Schedules and warnings are reviewed"],
    )

    add(
        "bim_execution_edit_existing_element",
        "The user asks to move an existing BIM wall. The current model is open. Find the exact wall and change its approved location without creating a duplicate or losing its identity, host relationships or attached openings.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "query_elements", "args": {"category": "wall", "limit": 200}, "stage": "identify"},
            {"tool": "list_commands", "args": {"filter": "modify"}, "stage": "discover"},
            {"tool": "query_elements", "args": {"category": "door", "limit": 200}, "stage": "dependencies"},
            {"tool": "query_elements", "args": {"category": "window", "limit": 200}, "stage": "dependencies"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will query existing walls and identify the exact six-digit element ID. I will inspect the door/window dependencies and retrieve the live modify command schema. Only then will I call execute with that ID and approved fields. I will query the same ID again and compare its before/after values; I will not delete and recreate the wall.",
        ["The same element ID remains after editing", "Hosted doors/windows remain connected or exceptions are reported", "The modified position matches the approved values", "No duplicate wall was created", "The model is re-inspected after the edit"],
    )

    add(
        "bim_execution_quantity_schedule",
        "Prepare a quantity schedule for a confirmed building model. The user needs element counts and geometry-derived areas/lengths/volumes, not guessed quantities or prices.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "list_commands", "args": {"filter": "schedule"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "quantity"}, "stage": "discover"},
            {"tool": "query_elements", "args": {"category": "wall", "limit": 200}, "stage": "query"},
            {"tool": "query_elements", "args": {"category": "floor", "limit": 200}, "stage": "query"},
            {"tool": "query_elements", "args": {"category": "door", "limit": 200}, "stage": "query"},
            {"tool": "query_elements", "args": {"category": "window", "limit": 200}, "stage": "query"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will discover native schedule/quantity commands and query the relevant element categories. I will use geometry-derived values returned by the model, keep units visible and report missing or unclassified elements. I will not invent material prices, waste percentages or labour costs.",
        ["Element counts reconcile with queried model records", "Area/length/volume units are explicit", "Duplicates and unclassified elements are reported", "No prices or allowances are invented"],
    )

    add(
        "bim_execution_renovation_existing_conditions",
        "Prepare a renovation BIM workflow. The project includes an old PDF plan and photographs, but their dimensions are not verified. A measured survey will be commissioned before any existing wall is moved.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "query_elements", "args": {"limit": 200}, "stage": "baseline"},
            {"tool": "list_commands", "args": {"filter": "phase"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "property"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "issue"}, "stage": "discover"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will record the existing model state and discover the available phase/property/issue commands. Old drawings and photographs will be stored as unverified reference evidence, not treated as exact as-built geometry. I will not move, delete or resize existing elements until the measured survey and protected-element list are approved.",
        ["Existing-condition confidence and source are recorded", "Protected elements are identified", "Unverified dimensions are flagged", "No destructive edit occurs before survey approval", "Open issues remain visible"],
    )

    add(
        "bim_execution_ifc_exchange_readiness",
        "Prepare the BIM model for an agreed IFC exchange. The user has not yet supplied final IFC schema/version or the employer information requirements. Do not export a file or claim conformance from the assistant.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "list_commands", "args": {"filter": "ifc"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "property"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "classification"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "validate"}, "stage": "discover"},
            {"tool": "query_elements", "args": {"limit": 200}, "stage": "audit"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will check available IFC, property, classification and validation commands, then audit model elements and missing information. The IFC schema and information requirements must be confirmed first. This assistant cannot perform file exports; the user controls file export in the native application. I will not claim IFC/IDS conformance without checking the actual exported file.",
        ["IFC schema/version and information requirements are confirmed", "Missing properties and classifications are listed", "Spatial hierarchy, types and relationships are reviewed", "File export remains user-controlled", "Round-trip validation is not claimed until performed"],
    )

    add(
        "bim_execution_structural_coordination",
        "Prepare a coordinated structural BIM frame for a building with an approved grid and levels. The user has not supplied structural analysis results or final member sizes.",
        [
            {"tool": "inspect_model", "args": {}, "stage": "preflight"},
            {"tool": "list_commands", "args": {"filter": "grid"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "column"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "beam"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "brace"}, "stage": "discover"},
            {"tool": "list_commands", "args": {"filter": "slab"}, "stage": "discover"},
            {"tool": "query_elements", "args": {"limit": 200}, "stage": "baseline"},
            {"tool": "inspect_model", "args": {}, "stage": "verify"},
        ],
        "I will inspect the model and discover the live grid, column, beam, brace and slab commands. I will map member placements to the approved grid and levels, use only supplied/proposed placeholder sections where the user has approved them, and keep the analysis status clearly separate from BIM geometry. I will not claim member capacity or structural compliance.",
        ["Grid and element alignments are inspected", "Members have stable marks and level assignment", "Connectivity is checked where supported", "Member sizes are not presented as engineered without calculations", "Analysis and approval status are disclosed"],
    )

    return lessons



def make_engineering_operator_curriculum() -> list[dict[str, Any]]:
    """Authored L0 design-intake lessons for specialist engineering object families.

    These teach the student what information a design requires. They are not
    native execution traces and must never be counted as validated models.
    """
    system = (
        "You are NextAI, a local engineering operator for native CAD/BIM software. "
        "Understand the engineering object before selecting native operations. Ask concise "
        "questions for missing requirements, preserve confirmed answers and return exactly "
        "one JSON object with message and plan. During essential clarification the plan must "
        "be empty. Use only the exact native tool names and schemas supplied in the context. "
        "Never invent geometry, dimensions, ratings, loads, materials, standards or tools. "
        "A concept model is not a verified engineering design."
    )
    lessons: list[dict[str, Any]] = []

    def add_flow(family: str, domain: str, initial: str, first_message: str,
                 first_reply: str, second_message: str, second_reply: str,
                 final_message: str, system_suffix: str = "") -> None:
        group = "engineering-skill-intake-" + family
        prompt_system = system + system_suffix
        turns = [
            (initial, first_message, "initial_clarification"),
            (
                "Conversation so far:\nUser: " + initial
                + "\nAssistant: " + json.dumps({"message": first_message, "plan": []}, ensure_ascii=False)
                + "\nUser: " + first_reply
                + "\n\nRespond only to the latest turn. Preserve confirmed facts and ask only for information still missing.",
                second_message,
                "context_aware_follow_up",
            ),
            (
                "Conversation so far:\nUser: " + initial
                + "\nAssistant: " + json.dumps({"message": first_message, "plan": []}, ensure_ascii=False)
                + "\nUser: " + first_reply
                + "\nAssistant: " + json.dumps({"message": second_message, "plan": []}, ensure_ascii=False)
                + "\nUser: " + second_reply
                + "\n\nSummarise the confirmed design brief and state the next native step. Do not invent missing information.",
                final_message,
                "confirmed_brief_or_capability_boundary",
            ),
        ]
        for prompt, message, stage in turns:
            lessons.append({
                "domain": domain,
                "system": prompt_system,
                "prompt": prompt,
                "completion": json.dumps({"message": message, "plan": []}, ensure_ascii=False),
                "split_group": group,
                "stage": stage,
                "evidence_level": "L0_knowledge_authored",
            })

    add_flow(
        "water-storage-tower",
        "design_intake_water_storage_tower",
        "I want you to design a water tower.",
        "What storage capacity do you need, what tank shape do you prefer, and what should the tank-bottom elevation and overall tower height be? Should the support be steel, reinforced concrete or another system? Please also confirm the support footprint, access (ladder or stair), and whether this is a visual concept or an engineered design.",
        "Use a cylindrical tank with about 50 cubic metres capacity. Steel support, 5 m by 5 m footprint, tank bottom 10 m above ground, 4 m tank height. It is only a visual concept for now, with a ladder.",
        "I have the tank form, capacity target, support material intent, footprint and tank-bottom elevation. Should the four support members be shown only as labelled visual envelopes, or do you have selected structural sections? Also confirm whether the tank's 4 m height is its straight cylindrical shell height, and whether the ladder should reach the tank platform.",
        "Use four round 250 mm diameter member placeholders, cylindrical tank radius 2 m and 4 m shell height. Ladder reaches the platform. Do not select steel sections or claim structural safety.",
        "Confirmed concept brief: nominal 50 m³ cylindrical tank envelope, 2 m radius and 4 m shell height; four separate 250 mm-diameter support placeholders on a 5 m square footprint; tank bottom/platform elevation 10 m; ladder to platform. The supports are visual solid-cylinder placeholders, not selected steel sections. I can create the editable tank and four support envelopes in separate native objects, then add the footprint/elevation dimensions. The ladder, platform connections, bracing, foundation and engineering checks remain separate unresolved work because the current typed tool set does not yet expose a complete water-tower structural system.",
        " For water-storage towers, distinguish tank capacity and geometry from support design. A visual model must not imply shell thickness, wind resistance, member capacity or foundation adequacy.",
    )
    add_flow(
        "mechanical-gear",
        "design_intake_mechanical_gear",
        "Build me a spur gear.",
        "Is this a single gear or a mating gear pair? Please provide module (or diametral pitch), tooth count, pressure angle, face width, bore/keyway, and whether you need a visual concept or a functional manufacturing model. For a functional gear, I also need the transmitted torque, speed, duty cycle, material and manufacturing requirements.",
        "One external spur gear. Module 4, 24 teeth, standard 20 degree pressure angle, 20 mm face width and 20 mm bore. I only need a visual concept.",
        "I have the main gear parameters. Do you want a hub or keyway, and should I leave the hub/keyway absent? I will also check whether this NextCAD installation exposes an approved involute gear-generation operation before claiming I can create the tooth profile.",
        "No hub and no keyway. Just the gear.",
        "Confirmed brief: one external spur gear, module 4, 24 teeth, 20° pressure angle, 20 mm face width, 20 mm bore, no hub or keyway, visual concept only. The reference pitch diameter is 96 mm under the stated standard spur-gear relation. However, I must inspect the live native capability registry for an approved involute gear-profile generator. The current typed NextAI tool list has no dedicated gear-generation operation, so I must not pretend a cylinder or polygon is a real involute gear. Until a reviewed native gear tool is available, I can prepare the parametric specification and report this execution gap.",
        " For gear tasks, a cylinder or arbitrary toothed-looking polygon is not a validated involute profile. Ask for tooth geometry inputs and use only a live, reviewed native gear generator; otherwise disclose the capability gap.",
    )
    add_flow(
        "electrical-control-panel",
        "design_intake_electrical_control_panel",
        "Create an electrical control panel in CAD.",
        "What is the supply voltage, phase/frequency, panel purpose, enclosure size/environment, device list and required circuit count? Is this only a physical packaging layout or must it include a verified schematic and electrical connectivity? For electrical design I will also need load data, fault level, earthing arrangement and the applicable design basis.",
        "It is a 415 V three-phase motor-control cabinet, 800 by 600 by 300 mm, IP54 target, with six outgoing circuits. For now I only need a physical packaging concept.",
        "I can create the outer enclosure envelope, but I need the main device/component list and the approximate mounting/backplate arrangement before laying out internal placeholders. Are the six circuits three motors, two pumps and one lighting circuit, or something else? Please confirm that the devices are visual placeholders only.",
        "Three motors at 15 kW each, two pumps at 7.5 kW each and one lighting circuit at 2 kW. Visual placeholders only; no electrical sizing.",
        "Confirmed physical-layout brief: 415 V three-phase motor-control cabinet, nominal envelope 800 × 600 × 300 mm, IP54 target, six outgoing circuits comprising three 15 kW motor loads, two 7.5 kW pump loads and one 2 kW lighting load. The load list is user supplied; protection, conductors, fault rating, thermal design, earthing and circuit connectivity are not designed. I can create the cabinet envelope as an editable native box. The current typed registry does not expose a complete device-library, electrical schematic or circuit-connectivity toolset, so those items must remain explicit capability gaps.",
        " An electrical cabinet's 3D boxes are packaging placeholders only. Never infer circuit connectivity, breaker ratings, conductor sizing, fault rating, IP performance or thermal adequacy from geometry.",
    )
    add_flow(
        "civil-road-drainage",
        "design_intake_civil_road_drainage",
        "Design a road and stormwater drainage for my site.",
        "Is this a new road, junction, access road or site road? Please provide the survey/topographic source, coordinate reference and vertical datum, road length/alignment/width, terrain and tie-in levels. For drainage, I will need the catchment boundary/area, rainfall basis or design return period, outfall level, flow direction and any known utility conflicts. Is this a concept model or an engineered design?",
        "It is a 250 m site access road, about 7 m wide. I do not have survey or drainage calculations yet. I need a concept only.",
        "I can prepare an explicitly schematic road corridor/layout concept, but without survey coordinates, levels and a drainage basis I cannot place reliable gradients, inverts, culvert sizes or outfall levels. Do you have an agreed drawing origin and orientation, and should the concept avoid assigning any elevations or pipe sizes?",
        "Use a simple local XY origin and no elevations or pipe sizes. Show only the road centreline and 7 m width envelope as a schematic concept.",
        "Confirmed schematic scope: 250 m site access road, 7 m width, local XY origin, no survey-based coordinates, no vertical profile and no drainage pipe sizing. This can be represented as a plan-view outline/centreline with an explicit not-to-scale/schematic label if the typed drafting tools are available. Drainage capacity, gradients, invert levels, cover, culvert sizing and flood performance remain unresolved until survey and hydrology inputs are supplied.",
        " For civil road/drainage work, a plan polyline is not a road corridor and a drawn pipe is not a verified hydraulic network. Require survey, datum, level and hydrology information before engineering claims.",
    )
    return lessons


def make_local_skill_curriculum() -> list[dict[str, Any]]:
    """Convert every first-party local engineering skill into small L0 SFT lessons.

    Each skill section is chunked deterministically, and every chunk keeps its
    own split_group so closely related paragraphs cannot leak between splits.
    This teaches the compact student the same domain procedures available to
    its local retrieval system without claiming a native execution occurred.
    """
    import re
    from pathlib import Path

    skill_root = (
        Path(__file__).resolve().parents[2]
        / "adapters" / "nextcad-ai" / "NextAI" / "knowledge_packs" / "skills"
    )
    if not skill_root.is_dir():
        return []

    system = (
        "You are NextAI, a local CAD/BIM engineering student. This lesson is "
        "authored engineering knowledge, not a native execution trace. Explain "
        "the design intent, required questions, object concepts, workflow, "
        "verification and limitations contained in the supplied skill text. "
        "Distinguish a visual/concept model from an engineered or independently "
        "validated design. Never invent native commands, dimensions, standards "
        "or results that the skill does not provide."
    )

    def split_paragraph(paragraph: str, limit: int = 1500) -> list[str]:
        paragraph = paragraph.strip()
        if len(paragraph) <= limit:
            return [paragraph] if paragraph else []
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        chunks = []
        current = ""
        for sentence in sentences:
            if len(sentence) > limit:
                if current:
                    chunks.append(current)
                    current = ""
                for start in range(0, len(sentence), limit):
                    chunks.append(sentence[start:start + limit])
                continue
            candidate = (current + " " + sentence).strip()
            if current and len(candidate) > limit:
                chunks.append(current)
                current = sentence
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks

    def section_chunks(body: str, limit: int = 1800) -> list[tuple[str, str]]:
        headings = list(re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", body))
        sections = []
        if not headings:
            headings = []
            sections.append(("Overview", body.strip()))
        else:
            prefix = body[:headings[0].start()].strip()
            if prefix:
                sections.append(("Overview", prefix))
            for index, match in enumerate(headings):
                end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
                sections.append((match.group(1).strip(), body[match.end():end].strip()))

        output = []
        for heading, section_body in sections:
            paragraphs = [item.strip() for item in re.split(r"\n\s*\n", section_body) if item.strip()]
            chunk = ""
            chunk_index = 0
            for paragraph in paragraphs:
                for part in split_paragraph(paragraph, limit):
                    candidate = (chunk + "\n\n" + part).strip()
                    if chunk and len(candidate) > limit:
                        chunk_index += 1
                        output.append((f"{heading} / part {chunk_index}", chunk))
                        chunk = part
                    else:
                        chunk = candidate
            if chunk:
                chunk_index += 1
                output.append((f"{heading} / part {chunk_index}", chunk))
        return output

    lessons = []
    for skill_path in sorted(skill_root.glob("*/SKILL.md")):
        if skill_path.is_symlink() or not skill_path.is_file() or skill_path.stat().st_size > 80_000:
            continue
        raw = skill_path.read_text(encoding="utf-8")
        lines = raw.splitlines()
        if not lines or lines[0].strip() != "---":
            continue
        end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
        if end is None:
            continue
        metadata = {}
        for line in lines[1:end]:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip().lower()] = value.strip().strip("\"'")
        name = str(metadata.get("name") or skill_path.parent.name).strip()
        description = str(metadata.get("description") or "").strip()
        if not name or not description:
            continue
        body = "\n".join(lines[end + 1:]).strip()
        if not body:
            continue
        sections = section_chunks(body)
        for index, (heading, chunk) in enumerate(sections, start=1):
            slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")[:36] or "overview"
            lessons.append({
                "domain": "engineering_skill_knowledge",
                "system": system,
                "prompt": (
                    f"Teach me the '{name}' engineering skill. Focus on '{heading}'. "
                    "Explain the relevant concepts, questions, decision rules, native workflow, "
                    "checks and limitations from the authored skill. Keep confirmed facts and "
                    "unresolved requirements separate."
                ),
                "completion": (
                    f"Engineering skill: {name}\n"
                    f"Description: {description}\n"
                    f"Lesson section: {heading}\n\n{chunk}\n\n"
                    "Evidence status: L0 authored knowledge only. No native operation was executed "
                    "and no geometry or engineering design is thereby validated."
                ),
                "split_group": f"nextai-skill-{name}",
                "stage": "local_skill_knowledge",
                "skill_name": name,
                "skill_section": heading,
                "evidence_level": "L0_knowledge_authored",
            })
    return lessons


CAPABILITY_SKILL_DIMENSIONS = {
    "recognition": "Explain what this native capability is called and what the pinned inventory actually says it does.",
    "inputs_and_units": "Identify known input metadata and explicitly distinguish a human-readable description from a formal schema.",
    "preconditions": "Explain what must be inspected in the live document before this capability can safely be planned.",
    "planning": "Explain how to place this capability into an ordered workflow without inventing undocumented dependencies.",
    "execution": "Explain how the local assistant is allowed to discover or invoke this capability under its current permission policy.",
    "verification": "Explain what evidence is still needed to prove that a native operation actually succeeded.",
    "revision": "Explain what must be inspected before revising existing model objects and what revision behaviour remains unknown.",
    "failure_recovery": "Explain how to handle a native failure without inventing rollback or retry guarantees.",
    "composition": "Explain what must be learned before composing this capability into a larger project workflow.",
    "limitations": "State exactly what the pinned metadata does not prove and what must not be claimed.",
}

NEXTCAD_MODULE_SKILL_DIMENSIONS = {
    "module_recognition": "Describe the module/workbench using only its pinned source metadata; do not infer the exact feature set from its name.",
    "source_layout": "Locate the module in the pinned source tree and distinguish source presence from successful installation.",
    "runtime_availability": "Explain how to verify that the workbench/module actually imports and registers in the running NextCAD build.",
    "capability_discovery": "Describe how to enumerate the module's live GUI commands and public API members after activation.",
    "dependency_and_activation": "Identify only documented activation/dependency facts and list what must be checked in the installed runtime.",
    "limitations": "State that a source module is not a discovered command, safe AI tool, executed task or evidence of mastery.",
}


def make_capability_knowledge_curriculum(census_path: Path) -> list[dict[str, Any]]:
    """Turn pinned command/API metadata into attributed L0 lessons, never execution traces."""
    census = json.loads(Path(census_path).read_text(encoding="utf-8"))
    if census.get("schema") != "nextai.capability_census.v1":
        raise ValueError("Capability census has an unexpected schema.")
    if census.get("evidence_rules", {}).get("mastery_requires_native_execution_and_validation") is not True:
        raise ValueError("Capability census does not preserve the native mastery evidence rule.")
    capabilities = census.get("capabilities")
    if not isinstance(capabilities, list):
        raise ValueError("Capability census has no capabilities array.")

    lessons = []
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        capability_type = capability.get("capability_type")
        is_nextcad_module = capability_type == "workbench_or_module" and capability.get("application") == "nextcad"
        if capability_type not in {"native_command", "native_gui_command", "native_api_member"} and not is_nextcad_module:
            continue
        application = capability.get("application")
        if application not in {"nextcad", "nextbim"}:
            continue
        native_id = str(capability.get("native_id") or "").strip()
        capability_id = str(capability.get("capability_id") or "").strip()
        name = str(capability.get("name") or native_id).strip()
        source_commit = str(capability.get("source_commit") or "").strip()
        if not native_id or not capability_id or not source_commit:
            raise ValueError("A native capability lesson requires a native ID, capability ID and source commit.")

        metadata = capability.get("native_metadata") or {}
        parameter_contract = str(
            capability.get("parameter_contract") or metadata.get("parameter_contract") or ""
        ).strip()
        contract_kind = str(
            capability.get("parameter_contract_kind") or metadata.get("parameter_contract_kind") or ""
        ).strip()
        known = {
            "application": application,
            "capability_name": name,
            "native_id": native_id,
            "capability_type": capability_type,
            "source_evidence": capability.get("source_evidence"),
            "source_commit": source_commit,
            "source_path": capability.get("source_path"),
            "source_present": capability.get("source_present"),
            "runtime_status": capability.get("runtime_status"),
            "ai_discovery_rule": capability.get("ai_discovery_rule"),
            "application_version": capability.get("application_version"),
            "menu_or_ui_label": capability.get("menu_text") or capability.get("menu"),
            "tooltip": capability.get("tooltip"),
            "status_tip": capability.get("status_tip"),
            "registration_kind": capability.get("registration_kind") or metadata.get("registration_kind"),
            "parameter_contract": parameter_contract or None,
            "parameter_contract_kind": contract_kind or None,
            "undoable": capability.get("undoable") if "undoable" in capability else metadata.get("undoable"),
            "file_effect": capability.get("file_effect") or metadata.get("file_effect") or "not specified",
            "assistant_execution_status": capability.get("assistant_execution_status")
                or metadata.get("assistant_execution_status")
                or capability.get("agent_tool_status")
                or "requires_reviewed_typed_adapter",
        }
        if is_nextcad_module:
            license_name = "LGPL-2.1"
            attribution = "FreeCAD contributors; pinned FreeCAD source module metadata, adapted for Next3D."
            policy = (
                "This record proves only that a module/workbench path is present in the pinned source index. "
                "Its runtime availability is not yet verified. Before relying on it, activate the module in the "
                "pinned NextCAD GUI, inspect the live workbench registry, enumerate its commands and public API, "
                "and review each operation for a typed AI adapter. Never infer commands from a module name."
            )
            domain = "nextcad_workbench_knowledge"
        elif application == "nextcad":
            license_name = "LGPL-2.1"
            attribution = "FreeCAD contributors; pinned FreeCAD source/runtime metadata, adapted for Next3D."
            policy = (
                "A discovered FreeCAD GUI command or API member is not an approved AI operation. "
                "NextCAD must use a reviewed typed adapter, exact argument schema and native validation. "
                "The generic GUI command fallback is view-only."
            )
            domain = "nextcad_capability_knowledge"
        else:
            license_name = "MIT OR Apache-2.0"
            attribution = "IPedrax and BIMCraft contributors; pinned BIMCraft command-registration metadata, adapted for Next3D."
            policy = (
                "Use the live BIMCraft list_commands result and exact native command description before "
                "constructing an execute request. Respect the native Assistant's file/image restrictions "
                "and the permissioned command bridge."
            )
            domain = "nextbim_capability_knowledge"

        dimensions = (
            NEXTCAD_MODULE_SKILL_DIMENSIONS
            if is_nextcad_module
            else CAPABILITY_SKILL_DIMENSIONS
        )
        capability_subject = "source module/workbench" if is_nextcad_module else "native capability"
        for dimension, objective in dimensions.items():
            prompt = (
                f"Teach the '{dimension}' aspect of {capability_subject} '{native_id}' "
                f"({name}) in {application}. Use only the pinned capability metadata below. "
                "Do not invent parameters, units, prerequisites, commands, geometry or successful results."
            )
            completion = {
                "lesson_type": (
                    "pinned_nextcad_source_module_knowledge"
                    if is_nextcad_module
                    else "pinned_native_capability_metadata_knowledge"
                ),
                "evidence_level": "L0_metadata_knowledge_authored",
                "application": application,
                "capability": known,
                "learning_dimension": dimension,
                "learning_objective": objective,
                "known_from_pinned_metadata": {
                    key: value for key, value in known.items()
                    if value not in (None, "", [], {})
                },
                "parameter_rule": (
                    "This is a source-module inventory entry, not a command contract. It does not expose a "
                    "complete operation list, parameter schema or runtime availability. Discover and verify "
                    "those facts inside the pinned running application."
                    if is_nextcad_module else
                    "The parameter contract is human-readable registration text, not a formal JSON Schema. "
                    "Treat it as a discovery hint and ask the live native command registry for current details."
                    if contract_kind == "human_readable_registration_description_not_json_schema"
                    else (
                        "No formal parameter schema is present in this census record. Do not invent arguments or units; "
                        "use the live native documentation or a reviewed typed adapter."
                    ) if not parameter_contract else
                    "This is descriptive metadata only. It is not a validated JSON Schema or proof that these arguments execute."
                ),
                "execution_permission_rule": policy,
                "evidence_boundary": (
                    (
                        "This lesson describes a source module only. Source presence is not proof that the "
                        "module loads or registers in the running application, and it is not a list of callable "
                        "operations. No native operation was executed by generating this lesson. L3/L4/L5 evidence "
                        "must be collected separately."
                    ) if is_nextcad_module else
                    "This lesson describes a pinned source/runtime capability, not an executed task. "
                    "No native object was created, edited, saved, reopened or independently validated by generating this lesson. "
                    "Mastery requires L3 native execution, L4 save/reopen and L5 independent validation."
                ),
            }
            lessons.append({
                "record_id": f"capability-knowledge-{application}-{capability_id}-{dimension}",
                "domain": domain,
                "system": (
                    "You are NextAI. Teach native software knowledge from version-pinned capability metadata. "
                    "Be precise about known facts and unknowns. A catalogue entry is not execution proof or permission."
                ),
                "prompt": prompt,
                "completion": json.dumps(completion, ensure_ascii=False),
                "images": [],
                "source": "Next3D pinned native capability metadata",
                "license": license_name,
                "attribution": attribution,
                "source_commit": source_commit,
                "application": application,
                "capability_type": capability_type,
                "native_id": native_id,
                "capability_id": capability_id,
                "learning_dimension": dimension,
                "evidence_level": "L0_metadata_knowledge_authored",
                "split_group": "capability-knowledge-" + application + "-" + capability_id,
                "stage": (
                    "nextcad_source_module_knowledge"
                    if is_nextcad_module else "capability_metadata_knowledge"
                ),
                "record_type": "authored_metadata_knowledge_not_native_execution",
            })
    return lessons

def make_synthetic_curriculum() -> list[dict[str, Any]]:
    """Small, original, unit-aware lessons that cover gaps in public corpora."""
    lessons = (make_advanced_engineering_curriculum() + make_design_intake_curriculum() + make_engineering_operator_curriculum() + make_design_execution_curriculum() + make_bim_execution_curriculum()) + [
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
        # Reserve a full 3.5 m depth for the master bedroom and at least
        # 2.0 m for the ensuite/dressing band, so the stated area targets
        # are actually met rather than being labels over undersized rooms.
        upper_bath_y = min(shell_depth - 2000, south_depth + 3500)
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
                    {"name": "Master dressing", "zone": "inside master suite", "minimum_area_m2": 3},
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
                    {"connects": ["Living and dining", "Kitchen"], "point": [mid_x, south_depth // 2]},
                    {"connects": ["Living and dining", "Bedroom 2"], "point": [x1 // 2, south_depth]},
                    {"connects": ["Kitchen", "Hall and circulation"], "point": [(x2 + x3) // 2, south_depth]},
                    {"connects": ["Bedroom 3", "Hall and circulation"], "point": [x2, south_depth + (upper_bath_y - south_depth) // 2]},
                    {"connects": ["Hall and circulation", "Shared bathroom"], "point": [(x2 + x3) // 2, upper_bath_y]},
                    {"connects": ["Hall and circulation", "Master bedroom"], "point": [x3, south_depth + (upper_bath_y - south_depth) // 2]},
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
                    {"from": "living and dining", "to": "kitchen", "type": "door"},
                    {"from": "living and dining", "to": "bedroom 2", "type": "door"},
                    {"from": "kitchen", "to": "hall and circulation", "type": "door"},
                    {"from": "bedroom 3", "to": "hall and circulation", "type": "door"},
                    {"from": "hall and circulation", "to": "shared bathroom", "type": "door"},
                    {"from": "hall and circulation", "to": "master bedroom", "type": "door"},
                    {"from": "master bedroom", "to": "master ensuite", "type": "door"},
                    {"from": "master bedroom", "to": "master dressing", "type": "door"},
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

    lessons.extend(make_master_project_curriculum())
    # Preserve the five practical curricula at >=20,000 examples each.
    # Generated rows remain L0 until real native evidence is collected.
    lessons.extend(make_scaled_curriculum_expansion())

    records = []
    for index, lesson in enumerate(lessons):
        completion = lesson["completion"]
        if not isinstance(completion, str):
            completion = json.dumps(completion, ensure_ascii=False)
        records.append({
            "record_id": f"next3d-synthetic-{index + 1:04d}",
            "domain": lesson["domain"],
            "system": lesson["system"],
            "prompt": lesson["prompt"],
            "completion": completion,
            "images": [],
            "source": (
                "Next3D local engineering skill packs"
                if lesson.get("skill_name") else "Next3D original synthetic curriculum"
            ),
            "license": "project-authored",
            **({
                "curriculum_version": lesson["curriculum_version"],
                "curriculum_item_id": lesson["record_id"],
                "curriculum_subject_id": lesson.get("curriculum_subject_id"),
                "curriculum_collection": lesson.get("curriculum_collection"),
                "curriculum_variant_id": lesson.get("curriculum_variant_id"),
                "curriculum_split": lesson.get("curriculum_split"),
                "curriculum_stage": lesson.get("curriculum_stage"),
                "application": lesson.get("application"),
                "evidence_level": lesson.get("evidence_level"),
                "scenario_hash": lesson.get("scenario_hash"),
                "scenario_axes": lesson.get("scenario_axes"),
            } if lesson.get("curriculum_version") and lesson.get("record_id") else {}),
            **({"split_group": lesson["split_group"], "stage": lesson["stage"]}
               if lesson.get("split_group") else {}),
            **({"skill_name": lesson["skill_name"], "skill_section": lesson["skill_section"],
                "evidence_level": lesson["evidence_level"]} if lesson.get("skill_name") else {}),
        })
    return records


def append_analytic_training_records(
    groups: dict[str, list[dict[str, Any]]],
    records: list[dict[str, Any]],
) -> None:
    """Append analytic records while admitting new solver families into the domain map."""
    for record in records:
        domain = str(record.get("domain") or "").strip()
        if not domain:
            raise ValueError("Analytic engineering record has no domain.")
        groups.setdefault(domain, []).append(record)


def merge_analytic_splits(
    train_rows: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    analytic_splits: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Preserve every generated analytic record outside the capped public sampler."""
    merged = {
        "train": list(train_rows),
        "validation": list(validation_rows),
        "test": list(test_rows),
    }
    for split in ("train", "validation", "test"):
        rows = analytic_splits.get(split)
        if not isinstance(rows, list):
            raise ValueError(f"Analytic curriculum is missing its {split} split.")
        for row in rows:
            if row.get("split") != split:
                raise ValueError(
                    f"Analytic record {row.get('record_id')!r} is assigned to "
                    f"{row.get('split')!r}, not {split!r}."
                )
        merged[split].extend(rows)
    return merged["train"], merged["validation"], merged["test"]


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
        "cad_2d_entity_semantics": 0.04,
        "cad_coordinate_transforms": 0.03,
        "cad_parametric_features": 0.04,
        "cad_assembly_design": 0.03,
        "cad_technical_documentation": 0.03,
        "cad_interoperability": 0.03,
        "bim_spatial_hierarchy": 0.04,
        "bim_type_instance_data": 0.03,
        "bim_material_properties": 0.03,
        "bim_ifc_exchange_requirements": 0.04,
        "bim_georeferencing": 0.03,
        "bim_phasing_revisions": 0.02,
        "engineering_structural_workflow": 0.04,
        "engineering_reinforced_concrete_workflow": 0.04,
        "engineering_geotechnical_workflow": 0.04,
        "engineering_water_and_drainage": 0.03,
        "engineering_survey_and_setting_out": 0.03,
        "engineering_standards_and_regulations": 0.03,
        "construction_project_controls": 0.03,
        "construction_cost_and_quantities": 0.03,
        "construction_quality_and_safety": 0.03,
        "swiss_dwellings_floorplan": 0.09,
        "ifc_model_summary": 0.06,
        "ifc_element_inventory": 0.08,
        "cad_geometry_topology": 0.035,
        "cad_sketch_constraint_diagnosis": 0.04,
        "cad_boolean_feature_planning": 0.03,
        "cad_surface_modelling": 0.03,
        "cad_mesh_quality": 0.025,
        "cad_fem_preprocessing": 0.025,
        "cad_cam_preprocessing": 0.025,
        "bim_room_boundaries": 0.04,
        "bim_asset_handover": 0.035,
        "bim_revision_change_impact": 0.03,
        "construction_4d_sequence": 0.03,
        "civil_site_coordination": 0.03,
        "engineering_beam_reactions_calculation": 0.035,
        "engineering_fem_axial_bar_calculation": 0.035,
        "engineering_pipe_continuity_calculation": 0.03,
        "construction_concrete_quantity_calculation": 0.03,
        "engineering_skill_knowledge": 0.08,
        "engineering_buildeng_reasoning": 0.18,
        "engineering_statics_beam_udl": 0.04,
        "engineering_statics_beam_centre_load": 0.035,
        "engineering_statics_cantilever_tip_load": 0.03,
        "engineering_structural_axial_bar": 0.035,
        "engineering_mechanical_torsion": 0.03,
        "engineering_hydraulics_continuity": 0.03,
        "engineering_hydraulics_darcy_weisbach": 0.03,
        "engineering_hydraulics_manning": 0.025,
        "engineering_geotechnical_effective_stress": 0.035,
        "engineering_geotechnical_consolidation": 0.035,
        "construction_concrete_quantity": 0.03,
        "construction_reinforcement_mass": 0.025,
        "engineering_mechanical_gear_ratio": 0.025,
        "engineering_electrical_three_phase_power": 0.025,
        "engineering_surveying_leveling": 0.03,
        "engineering_structural_section_properties": 0.03,
        "engineering_structural_euler_column_buckling": 0.035,
        "engineering_geotechnical_rankine_active_pressure": 0.035,
        "engineering_hydraulics_hydrostatic_gate": 0.025,
        "engineering_geotechnical_terzaghi_strip_footing": 0.035,
        "engineering_geotechnical_infinite_slope": 0.035,
        "engineering_hydraulics_rational_method_runoff": 0.025,
        "engineering_hydraulics_water_pump_power": 0.025,
        "engineering_geotechnical_elastic_foundation_settlement": 0.035,
        "civil_earthwork_average_end_area": 0.025,
        "nextcad_capability_knowledge": 0.10,
        "nextbim_capability_knowledge": 0.12,
        "design_intake_water_storage_tower": 0.04,
        "design_intake_mechanical_gear": 0.04,
        "design_intake_electrical_control_panel": 0.04,
        "design_intake_civil_road_drainage": 0.04,
        "design_intake_architecture": 0.055,
        "design_intake_commercial_architecture": 0.035,
        "design_intake_vehicle_cad": 0.045,
        "design_intake_mechanical_part": 0.045,
        "design_intake_assembly_cad": 0.04,
        "design_intake_sheet_metal_cad": 0.04,
        "design_intake_bim_new_build": 0.055,
        "design_intake_bim_renovation": 0.045,
        "design_intake_civil_infrastructure": 0.04,
        "design_intake_consumer_product_cad": 0.04,
        "design_intake_technical_drawing_cad": 0.035,
        "design_intake_cam_cad": 0.035,
        "design_intake_watchtower_architecture": 0.045,
        "design_execution_residential_floorplan": 0.05,
        "design_execution_watchtower_concept": 0.05,
        "design_execution_parametric_mechanical_part": 0.05,
        "design_execution_edit_existing_model": 0.045,
        "design_execution_vehicle_package": 0.03,
        "design_execution_cylindrical_shaft": 0.02,
        "design_execution_spherical_component": 0.02,
        "design_execution_tapered_nozzle": 0.02,
        "design_execution_3d_architectural_wall_shell": 0.045,
        "design_execution_electrical_cabinet": 0.03,
        "design_execution_parametric_hollow_tube": 0.03,
        "design_execution_pump_package": 0.03,
        "bim_execution_new_build": 0.045,
        "bim_execution_watchtower": 0.04,
        "bim_execution_mep_coordination": 0.04,
        "bim_execution_edit_existing_element": 0.04,
        "bim_execution_quantity_schedule": 0.03,
        "bim_execution_renovation_existing_conditions": 0.035,
        "bim_execution_ifc_exchange_readiness": 0.035,
        "bim_execution_structural_coordination": 0.04,
        "nextcad_native": 0.05,
        "nextbim_native": 0.05,
    }
    missing_analytic_weights = sorted(set(FAMILY_BUILDERS) - set(weights))
    if missing_analytic_weights:
        raise ValueError(
            "Analytic engineering families lack explicit sampler weights: "
            + ", ".join(missing_analytic_weights)
        )
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


def merge_native_trace_splits(
    base_train: list[dict[str, Any]],
    base_validation: list[dict[str, Any]],
    base_test: list[dict[str, Any]],
    native_splits: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Append all native execution evidence after public-data sampling/capping."""
    return (
        base_train + list(native_splits.get("train", [])),
        base_validation + list(native_splits.get("validation", [])),
        base_test + list(native_splits.get("test", [])),
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def split_synthetic_curriculum(lessons: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Hold out design families and keep every dialogue stage in one split."""
    result = {"train": [], "validation": [], "test": []}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for index, lesson in enumerate(lessons, 1):
        group_id = str(lesson.get("split_group") or lesson.get("record_id") or f"lesson-{index}")
        grouped.setdefault(group_id, []).append(lesson)
    for group_index, group in enumerate(grouped.values(), 1):
        explicit = {str(row.get("curriculum_split")) for row in group if row.get("curriculum_split")}
        if explicit:
            if len(explicit) != 1 or next(iter(explicit)) not in result:
                raise ValueError(f"Invalid or conflicting explicit curriculum split for {group[0].get('record_id')}")
            split = next(iter(explicit))
        else:
            bucket = group_index % 10
            split = "test" if bucket == 0 else "validation" if bucket == 1 else "train"
        result[split].extend(group)
    return result


def read_swiss_dwellings_directory(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load pre-rendered, building-disjoint Swiss Dwellings records by split."""
    result = {"train": [], "validation": [], "test": []}
    for split in result:
        source_path = path / f"{split}.jsonl"
        if not source_path.is_file():
            raise FileNotFoundError(f"Swiss Dwellings {split} file not found: {source_path}")
        with source_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("domain") != "swiss_dwellings_floorplan":
                    raise ValueError(f"Unexpected Swiss Dwellings domain at {source_path}:{line_number}")
                if row.get("source_doi") != "10.5281/zenodo.7788422" or row.get("license") != "CC-BY-4.0":
                    raise ValueError(f"Swiss Dwellings provenance mismatch at {source_path}:{line_number}")
                if row.get("source_split") != split:
                    raise ValueError(f"Swiss Dwellings record has wrong split at {source_path}:{line_number}")
                images = row.get("images") or []
                if len(images) != 1 or not Path(images[0]).is_file():
                    raise FileNotFoundError(f"Swiss Dwellings record image missing at {source_path}:{line_number}")
                result[split].append(row)
    return result


def read_ifc_model_corpus(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Read IFC model summaries and element inventories prepared by IfcOpenShell."""
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"IFC model corpus manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("test_not_used_for_training") is not True:
        raise ValueError("IFC model corpus must declare its test split as held out")
    result = {"train": [], "validation": [], "test": []}
    for split in result:
        source_path = path / f"{split}.jsonl"
        if not source_path.is_file():
            raise FileNotFoundError(f"IFC model corpus {split} file not found: {source_path}")
        with source_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("domain") not in {"ifc_model_summary", "ifc_element_inventory"}:
                    raise ValueError(f"Unexpected IFC model domain at {source_path}:{line_number}")
                if row.get("source") != manifest.get("source"):
                    raise ValueError(f"IFC model source mismatch at {source_path}:{line_number}")
                if row.get("license") != manifest.get("license") or not row.get("source_doi"):
                    raise ValueError(f"IFC model licence or DOI missing at {source_path}:{line_number}")
                if not row.get("source_file_sha256") or not row.get("split_group"):
                    raise ValueError(f"IFC model provenance or split group missing at {source_path}:{line_number}")
                result[split].append(row)
    return result, manifest


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
        "cad_2d_entity_semantics": [], "cad_coordinate_transforms": [],
        "cad_parametric_features": [], "cad_assembly_design": [],
        "cad_technical_documentation": [], "cad_interoperability": [],
        "bim_spatial_hierarchy": [], "bim_type_instance_data": [],
        "bim_material_properties": [], "bim_ifc_exchange_requirements": [],
        "bim_georeferencing": [], "bim_phasing_revisions": [],
        "engineering_structural_workflow": [], "engineering_reinforced_concrete_workflow": [],
        "engineering_geotechnical_workflow": [], "engineering_water_and_drainage": [],
        "engineering_survey_and_setting_out": [], "engineering_standards_and_regulations": [],
        "construction_project_controls": [], "construction_cost_and_quantities": [],
        "construction_quality_and_safety": [], "swiss_dwellings_floorplan": [],
        "ifc_model_summary": [], "ifc_element_inventory": [],
        "cad_geometry_topology": [], "cad_sketch_constraint_diagnosis": [],
        "cad_boolean_feature_planning": [], "cad_surface_modelling": [],
        "cad_mesh_quality": [], "cad_fem_preprocessing": [], "cad_cam_preprocessing": [],
        "bim_room_boundaries": [], "bim_asset_handover": [],
        "bim_revision_change_impact": [], "construction_4d_sequence": [],
        "civil_site_coordination": [], "engineering_skill_knowledge": [],
        "nextcad_capability_knowledge": [], "nextbim_capability_knowledge": [],
        "design_intake_architecture": [], "design_intake_commercial_architecture": [],
        "design_intake_vehicle_cad": [], "design_intake_mechanical_part": [],
        "design_intake_assembly_cad": [], "design_intake_sheet_metal_cad": [],
        "design_intake_bim_new_build": [], "design_intake_bim_renovation": [],
        "design_intake_civil_infrastructure": [],
        "design_intake_consumer_product_cad": [], "design_intake_technical_drawing_cad": [],
        "design_intake_cam_cad": [], "design_intake_watchtower_architecture": [],
        "design_execution_residential_floorplan": [], "design_execution_watchtower_concept": [],
        "design_execution_parametric_mechanical_part": [], "design_execution_edit_existing_model": [],
        "nextcad_native": [], "nextbim_native": [],
        "engineering_buildeng_reasoning": [],
    }
    for domain in (
        "engineering_statics_beam_udl",
        "engineering_statics_beam_centre_load",
        "engineering_statics_cantilever_tip_load",
        "engineering_structural_axial_bar",
        "engineering_mechanical_torsion",
        "engineering_hydraulics_continuity",
        "engineering_hydraulics_darcy_weisbach",
        "engineering_hydraulics_manning",
        "engineering_geotechnical_effective_stress",
        "engineering_geotechnical_consolidation",
        "construction_concrete_quantity",
        "construction_reinforcement_mass",
        "engineering_mechanical_gear_ratio",
        "engineering_electrical_three_phase_power",
        "engineering_surveying_leveling",
        "engineering_structural_section_properties",
        "civil_earthwork_average_end_area",
    ):
        groups.setdefault(domain, [])
    validation, tests, quarantine = [], [], []
    counts = Counter()
    ifc_model_manifest = None

    # Preserve the most independent split when a source UUID is duplicated
    # across the dataset's published splits: test takes precedence, then
    # validation, then train. This prevents a CAD component and its derived
    # visual/feature-trace records from leaking between model-development splits.
    cad_limits = [
        ("test", args.max_cad_test, "test"),
        ("validation", args.max_cad_validation, "validation"),
        ("train", args.max_cad_train, "train"),
    ]
    seen_cad_source_ids: set[str] = set()
    for source_split, maximum, target_split in cad_limits:
        for index, row in enumerate(load_stream(CAD_DATASET, source_split, maximum, args.seed)):
            try:
                source_id = str(row.get("uuid") or "").strip()
                if not source_id:
                    raise ValueError("CAD source row has no stable UUID; refusing to create an untraceable split identity")
                source_key = source_id.casefold()
                if source_key in seen_cad_source_ids:
                    counts["cad_duplicate_source_rows_skipped"] += 1
                    continue
                seen_cad_source_ids.add(source_key)
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

    # BuildEng publishes one upstream train split. Create stable internal
    # train/validation/test partitions by normalized category + user brief.
    # Keep this 145K civil/structural safety-reasoning source separately labelled.
    buildeng_seen: set[str] = set()
    for index, row in enumerate(load_stream(BUILDENG_DATASET, "train", args.max_buildeng_records, args.seed)):
        counts["buildeng_source_rows"] += 1
        try:
            record = make_buildeng_record(row, index)
            if record["record_id"] in buildeng_seen:
                counts["buildeng_duplicate_rows_skipped"] += 1
                continue
            buildeng_seen.add(record["record_id"])
            target_split = record["split"]
            if target_split == "train":
                groups["engineering_buildeng_reasoning"].append(record)
            elif target_split == "validation":
                validation.append(record)
            else:
                tests.append(record)
            counts[f"buildeng_{target_split}_accepted"] += 1
        except Exception as exc:
            counts["buildeng_quarantined"] += 1
            quarantine.append({
                "source": BUILDENG_DATASET,
                "split": "train_with_deterministic_internal_split",
                "row": index,
                "reason": str(exc),
            })

    # Generate deterministic original engineering calculation cases from
    # reviewed closed-form solvers. These are L0 analytic lessons, not native traces.
    analytic_splits, analytic_manifest = generate_cases(
        cases_per_domain=args.analytic_cases_per_domain,
        seed=args.seed,
    )
    # Keep all analytic records separate from the capped public/mixed sampler.
    # Their per-family 10,000-case targets must survive into the final JSONL splits.
    counts["analytic_engineering_train"] = len(analytic_splits["train"])
    counts["analytic_engineering_validation"] = len(analytic_splits["validation"])
    counts["analytic_engineering_test"] = len(analytic_splits["test"])
    counts["analytic_engineering_families"] = len(analytic_manifest.get("families", {}))

    if args.swiss_dwellings_dir:
        swiss_records = read_swiss_dwellings_directory(args.swiss_dwellings_dir)
        groups["swiss_dwellings_floorplan"].extend(swiss_records["train"])
        validation.extend(swiss_records["validation"])
        tests.extend(swiss_records["test"])
        counts["swiss_dwellings_train"] = len(swiss_records["train"])
        counts["swiss_dwellings_validation"] = len(swiss_records["validation"])
        counts["swiss_dwellings_test"] = len(swiss_records["test"])

    if args.ifc_model_corpus_dir:
        ifc_records, ifc_model_manifest = read_ifc_model_corpus(args.ifc_model_corpus_dir)
        for record in ifc_records["train"]:
            groups[record["domain"]].append(record)
        validation.extend(ifc_records["validation"])
        tests.extend(ifc_records["test"])
        counts["ifc_model_train_records"] = len(ifc_records["train"])
        counts["ifc_model_validation_records"] = len(ifc_records["validation"])
        counts["ifc_model_test_records"] = len(ifc_records["test"])

    native_splits: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    native_application_splits: dict[tuple[str, str], list[dict[str, Any]]] = {
        (application, split): []
        for application in ("nextcad", "nextbim")
        for split in ("train", "validation", "test")
    }
    native_specs = (
        ("nextcad_native", "nextcad", "train", args.nextcad_native_train or args.nextcad_native),
        ("nextcad_native", "nextcad", "validation", args.nextcad_native_validation),
        ("nextcad_native", "nextcad", "test", args.nextcad_native_test),
        ("nextbim_native", "nextbim", "train", args.nextbim_native_train or args.nextbim_native),
        ("nextbim_native", "nextbim", "validation", args.nextbim_native_validation),
        ("nextbim_native", "nextbim", "test", args.nextbim_native_test),
    )
    for domain, application, split, native_path in native_specs:
        rows = read_native(native_path, domain, application, split)
        native_splits[split].extend(rows)
        native_application_splits[(application, split)].extend(rows)
        counts[f"{domain}_{split}"] = len(rows)
    synthetic_splits = split_synthetic_curriculum(make_synthetic_curriculum())
    # Keep the master curriculum outside the capped public/mixed sampler. It
    # represents required first-party learning objectives and must never be
    # silently dropped by per-domain quotas.
    master_curriculum_splits, synthetic_splits = separate_master_curriculum_splits(synthetic_splits)
    master_curriculum_coverage = summarize_master_curriculum_splits(master_curriculum_splits)
    scaled_curriculum_splits, synthetic_splits = separate_scaled_curriculum_splits(synthetic_splits)
    scaled_expansion_rows = [
        *scaled_curriculum_splits["train"],
        *scaled_curriculum_splits["validation"],
        *scaled_curriculum_splits["test"],
    ]
    scaled_curriculum_coverage = summarize_scaled_curriculum(
        scaled_expansion_rows,
        [*master_curriculum_splits["train"], *master_curriculum_splits["validation"], *master_curriculum_splits["test"]],
    )
    for split_name, count in scaled_curriculum_coverage["by_split"].items():
        counts[f"practical_curriculum_{split_name}"] = count
    counts["practical_curriculum_total"] = scaled_curriculum_coverage["total_examples_including_v2_baseline"]
    counts["practical_curriculum_expansion_records"] = scaled_curriculum_coverage["new_expansion_examples"]
    for split_name, count in master_curriculum_coverage["by_split"].items():
        counts[f"master_curriculum_{split_name}"] = count
    counts["master_curriculum_total"] = master_curriculum_coverage["total"]
    for lesson in synthetic_splits["train"]:
        groups.setdefault(lesson["domain"], []).append(lesson)
    validation.extend(synthetic_splits["validation"])
    tests.extend(synthetic_splits["test"])
    counts["synthetic_train"] = len(synthetic_splits["train"])
    counts["synthetic_validation"] = len(synthetic_splits["validation"])
    counts["synthetic_test"] = len(synthetic_splits["test"])

    # Keep first-party local skills and the complete native capability census
    # outside the capped public/mixed sampler. Every known capability lesson
    # must survive corpus assembly; otherwise "complete capability learning"
    # would depend on random sampling luck.
    skill_splits = split_synthetic_curriculum(make_local_skill_curriculum())
    capability_splits = {"train": [], "validation": [], "test": []}
    capability_census_path = getattr(args, "capability_census", None)
    if capability_census_path:
        capability_lessons = make_capability_knowledge_curriculum(capability_census_path)
        capability_splits = split_synthetic_curriculum(capability_lessons)
    else:
        capability_lessons = []

    for split_name in ("train", "validation", "test"):
        counts[f"local_skill_{split_name}"] = len(skill_splits[split_name])
        counts[f"capability_knowledge_{split_name}"] = len(capability_splits[split_name])
    counts["local_skill_total"] = sum(len(rows) for rows in skill_splits.values())
    counts["capability_knowledge_total"] = len(capability_lessons)

    base_train = sample_balanced(groups, args.max_mixed_train, args.seed)
    base_validation = validation[:args.max_validation]
    base_tests = tests[:args.max_test]
    train, validation_rows, test_rows = merge_native_trace_splits(
        base_train, base_validation, base_tests, native_splits
    )
    train, validation_rows, test_rows = merge_analytic_splits(
        train, validation_rows, test_rows, analytic_splits
    )
    final_split_rows = {
        "train": train,
        "validation": validation_rows,
        "test": test_rows,
    }
    analytic_final_split_counts = {
        split: dict(Counter(
            row["case_family"] for row in rows
            if row.get("source") == analytic_manifest["source"] and row.get("case_family")
        ))
        for split, rows in final_split_rows.items()
    }
    expected_analytic_split_counts = {
        split: dict(Counter(row["case_family"] for row in rows))
        for split, rows in analytic_splits.items()
    }
    if analytic_final_split_counts != expected_analytic_split_counts:
        raise ValueError("Analytic per-family counts were not fully preserved in final corpus splits.")
    analytic_final_split_totals = {
        split: sum(families.values())
        for split, families in analytic_final_split_counts.items()
    }
    analytic_family_totals: Counter = Counter()
    for families in analytic_final_split_counts.values():
        analytic_family_totals.update(families)
    if dict(analytic_family_totals) != dict(analytic_manifest["families"]):
        raise ValueError("Final analytic family totals do not match the generator manifest.")
    # Keep every authored master curriculum row even when the public/mixed
    # sampler reaches its cap. Train/validation/test remain strictly separate.
    train += master_curriculum_splits["train"]
    validation_rows += master_curriculum_splits["validation"]
    test_rows += master_curriculum_splits["test"]
    # Keep all 99,380 scale-expansion rows outside public/mixed sampler caps.
    train += scaled_curriculum_splits["train"]
    validation_rows += scaled_curriculum_splits["validation"]
    test_rows += scaled_curriculum_splits["test"]
    train += skill_splits["train"] + capability_splits["train"]
    validation_rows += skill_splits["validation"] + capability_splits["validation"]
    test_rows += skill_splits["test"] + capability_splits["test"]
    random.Random(args.seed + 1).shuffle(validation_rows)
    random.Random(args.seed + 2).shuffle(test_rows)
    random.Random(args.seed + 3).shuffle(train)

    write_jsonl(out / "train.jsonl", train)
    write_jsonl(out / "validation.jsonl", validation_rows)
    write_jsonl(out / "test.jsonl", test_rows)
    write_jsonl(out / "skill_train.jsonl", skill_splits["train"])
    write_jsonl(out / "skill_validation.jsonl", skill_splits["validation"])
    write_jsonl(out / "skill_test.jsonl", skill_splits["test"])
    write_jsonl(out / "capability_train.jsonl", capability_splits["train"])
    write_jsonl(out / "capability_validation.jsonl", capability_splits["validation"])
    write_jsonl(out / "capability_test.jsonl", capability_splits["test"])
    write_jsonl(out / "master_curriculum_train.jsonl", master_curriculum_splits["train"])
    write_jsonl(out / "master_curriculum_validation.jsonl", master_curriculum_splits["validation"])
    write_jsonl(out / "master_curriculum_test.jsonl", master_curriculum_splits["test"])
    write_jsonl(out / "scaled_practical_curriculum_train.jsonl", scaled_curriculum_splits["train"])
    write_jsonl(out / "scaled_practical_curriculum_validation.jsonl", scaled_curriculum_splits["validation"])
    write_jsonl(out / "scaled_practical_curriculum_test.jsonl", scaled_curriculum_splits["test"])
    for application in ("nextcad", "nextbim"):
        for split in ("train", "validation", "test"):
            write_jsonl(
                out / f"{application}_native_{split}.jsonl",
                native_application_splits[(application, split)],
            )
    write_jsonl(out / "quarantine.jsonl", quarantine)

    manifest = {
        "schema_version": 1,
        "student": "Qwen/Qwen3.5-0.8B",
        "method": "Full-precision BF16/FP16 LoRA supervised fine-tuning",
        "sources": [
            *([{
                "repo": "Next3D pinned native capability census",
                "license": "per-capability upstream source license",
                "purpose": "L0 metadata-derived lessons for each pinned native command/API and ten learning dimensions; not execution traces",
                "census_path": str(capability_census_path.resolve()),
                "capability_lesson_records": counts.get("capability_knowledge_total", 0),
            }] if capability_census_path else []),
            {"repo": CAD_DATASET, "license": "Apache-2.0", "purpose": "CAD visual feature recognition and construction sequence"},
            {"repo": BIM_DATASET, "license": "MIT", "purpose": "IFC/BIM instruction lessons; source must claim validation and score >=4.5"},
            {"repo": BIM_QA_DATASET, "license": "CC-BY-4.0", "attribution": "Dietmar2020", "purpose": "IFC/BIM conceptual QA"},
            {"repo": BUILDENG_DATASET, "license": "Apache-2.0", "purpose": "145,117 publisher-described civil/structural/building-engineering chat examples covering conservative reasoning, missing-input discipline, calculations, inspection and repair; split deterministically by normalized category and user brief; L0 material, not Next3D native execution"},
            {"repo": analytic_manifest["source"], "license": analytic_manifest["license"], "purpose": "Original formula-checked analytic cases across statics, structural mechanics, hydraulics, geotechnical calculations, quantities, mechanical systems, electrical power and surveying; explicit governing equations, inputs, units and assumptions; L0 analytic examples, not native application execution", "generation_method": analytic_manifest["generation_method"], "seed": args.seed, "cases_per_domain": args.analytic_cases_per_domain, "families": analytic_manifest["families"], "split_counts": analytic_manifest["split_counts"]},
            {"repo": "Swiss Dwellings v3.0.0", "doi": "10.5281/zenodo.7788422", "license": "CC-BY-4.0", "attribution": "Standfest et al., Archilyse AG", "purpose": "Image-grounded architectural floor-plan geometry, room typology and shared-boundary relationships; optional training-only corpus"},
            {"repo": "optional IFC model corpus", "license": "manifest-declared", "purpose": "Parsed IFC2x3/IFC4 model hierarchy, element classes, safe properties, materials and relationships; no original GlobalIds or free-text personal metadata"},
            {"repo": "Next3D original synthetic curriculum", "license": "project-authored", "purpose": "2D drafting, parametric sketches, 3D modeling, documentation, multi-turn CAD/BIM design intake, BIM concepts and construction workflows"},
            {"repo": "Next3D master project/operator curriculum v2", "license": "project-authored", "purpose": "620 L0 baseline examples across NextCAD, Next BIM, engineering disciplines, integrated projects and operator behaviour; retained outside mixed sampling caps."},
            {"repo": "Next3D scaled practical curriculum v1", "license": "project-authored", "purpose": "99,380 additional L0 scenarios, bringing each of five practical collections to exactly 20,000 examples (100,000 total including the v2 baseline). Each scenario varies project context, objective, operation, starting state, constraint, input quality, affected input/reference and deliverable. Retained outside mixed sampling caps; not native execution evidence."},
            {"repo": "Next3D local engineering skill packs", "license": "project-authored", "purpose": "Section-level engineering and native-workbench knowledge lessons from the local NextAI skill library; L0 authored knowledge, not native execution traces"},
        ],
        "source_counts": dict(counts),
        "analytic_records_preserved_outside_mixed_sampler": analytic_final_split_totals,
        "analytic_family_records_preserved_in_final_splits": analytic_final_split_counts,
        "train_records": len(train),
        "validation_records": len(validation_rows),
        "test_records": len(test_rows),
        "quarantined_rows": len(quarantine),
        "training_domain_counts": dict(Counter(row["domain"] for row in train)),
        "authored_master_curriculum_coverage": master_curriculum_coverage,
        "scaled_practical_curriculum_coverage": scaled_curriculum_coverage,
        "curated_example_inventory": {
            "analytic_engineering": {
                "train": counts.get("analytic_engineering_train", 0),
                "validation": counts.get("analytic_engineering_validation", 0),
                "test": counts.get("analytic_engineering_test", 0),
            },
            "master_project_operator_curriculum": {
                "train": master_curriculum_coverage["by_split"]["train"],
                "validation": master_curriculum_coverage["by_split"]["validation"],
                "test": master_curriculum_coverage["by_split"]["test"],
                "total": master_curriculum_coverage["total"],
                "by_collection": master_curriculum_coverage["by_collection"],
                "retained_outside_mixed_sampler_cap": True,
                "included_within_scaled_practical_curriculum": True,
            },
            "scaled_practical_curriculum": {
                "train": scaled_curriculum_coverage["by_split"]["train"],
                "validation": scaled_curriculum_coverage["by_split"]["validation"],
                "test": scaled_curriculum_coverage["by_split"]["test"],
                "total": scaled_curriculum_coverage["total_examples_including_v2_baseline"],
                "by_collection": scaled_curriculum_coverage["by_collection"],
                "retained_outside_mixed_sampler_cap": True,
            },
            "combined_analytic_plus_master_curriculum": {
                "train": counts.get("analytic_engineering_train", 0) + master_curriculum_coverage["by_split"]["train"],
                "validation": counts.get("analytic_engineering_validation", 0) + master_curriculum_coverage["by_split"]["validation"],
                "test": counts.get("analytic_engineering_test", 0) + master_curriculum_coverage["by_split"]["test"],
                "total": (
                    counts.get("analytic_engineering_train", 0)
                    + counts.get("analytic_engineering_validation", 0)
                    + counts.get("analytic_engineering_test", 0)
                    + master_curriculum_coverage["total"]
                ),
                "historical_pre_scale_subtotal": True,
                "scope_note": "Historical pre-scale subtotal only: 250k analytic + 620 master baseline. The 620 are already included in scaled_practical_curriculum; do not add this historical field to the current combined total.",
            },
            "combined_analytic_plus_practical_curriculum": {
                "train": counts.get("analytic_engineering_train", 0) + scaled_curriculum_coverage["by_split"]["train"],
                "validation": counts.get("analytic_engineering_validation", 0) + scaled_curriculum_coverage["by_split"]["validation"],
                "test": counts.get("analytic_engineering_test", 0) + scaled_curriculum_coverage["by_split"]["test"],
                "total": (
                    counts.get("analytic_engineering_train", 0)
                    + counts.get("analytic_engineering_validation", 0)
                    + counts.get("analytic_engineering_test", 0)
                    + scaled_curriculum_coverage["total_examples_including_v2_baseline"]
                ),
                "scope_note": "Current non-overlapping subtotal: the exact 250k analytic corpus plus the 100k practical curriculum; the 100k practical total already contains the original 620 master baseline. Excludes other public sources, local skill packs, capability metadata and native trace artifacts.",
            },
        },
        "native_execution_trace_records": {
            application: {
                split: len(native_application_splits[(application, split)])
                for split in ("train", "validation", "test")
            }
            for application in ("nextcad", "nextbim")
        },
        "native_execution_traces_retained_outside_public_sampling_caps": True,
        "test_not_used_for_training": True,
        "raw_data_and_images_not_shipped_in_installer": True,
        "notes": [
            "CadQuery teaches reference feature semantics only; NextCAD must map to native FreeCAD tools.",
            "Exact dimensions are never inferred from unscaled image views.",
            "IFC text examples are not proof of an IFC file or BIMCraft project passing validation.",
            "The IFC dedup set is excluded from positive lessons until its generated IFC is validated.",
            "Standards remain versioned retrieval references, not copied wholesale into model weights.",
            "Every first-party local skill, pinned capability metadata lesson and validated native execution trace is retained in dedicated sidecar splits and merged into its exact train/validation/test output without the capped public/mixed sampler.",
            "Swiss Dwellings images and vector labels are a training-only optional corpus; the 931.9 MB source archive is not part of the runtime package.",
            "Swiss Dwellings floors from the same building are kept in one data split to prevent train/test leakage.",
            "Optional IFC model records are split by source model or paired project team; free-text names and original GlobalIds are excluded.",
            "Guided design-intake dialogue stages remain grouped together in one split; confirmed answers are carried forward and missing requirements are asked without repetition.",
            "Native design-execution examples use the current NextCAD typed tool schemas and are validated against the registry in tests; watchtower member dimensions are concept placeholders, and the floor-plan example is room zoning only.",
            "BuildEng source validation is a publisher-described dataset claim; its examples remain L0 authored reasoning and are not NextCAD/Next BIM execution or professional design approval.",
            "BuildEng has only one published train split; internal validation/test partitions are generated deterministically from normalized category and user-request fingerprints, not published benchmark splits.",
            "Original analytic engineering cases are generated by closed-form formula functions with governing equations, inputs, units and assumptions. They are educational L0 examples, not code-compliant designs or native CAD/BIM traces.",
            "The practical curriculum subtotal includes the 620 master baseline exactly once; use combined_analytic_plus_practical_curriculum for the current non-overlapping analytic-plus-practical count.",
        ],
    }
    for application in ("nextcad", "nextbim"):
        split_counts = {
            split: len(native_application_splits[(application, split)])
            for split in ("train", "validation", "test")
        }
        if any(split_counts.values()):
            manifest["sources"].append({
                "repo": f"Next3D validated {application} native execution traces",
                "license": "Per-record reviewed source licence recorded in trace metadata",
                "purpose": (
                    "Versioned native application operations accepted only after schema, "
                    "provenance/privacy, recompute and save/reopen validation gates; not a "
                    "professional design approval or guarantee of general native competence"
                ),
                "application": application,
                "split_counts": split_counts,
            })

    if ifc_model_manifest:
        manifest["sources"].append({
            "repo": ifc_model_manifest.get("source"),
            "doi": ifc_model_manifest.get("doi"),
            "license": ifc_model_manifest.get("license"),
            "purpose": "Parsed IFC model hierarchy, object classes, safe properties, materials and explicit relationships",
            "model_files": ifc_model_manifest.get("model_files"),
            "records": ifc_model_manifest.get("training_records"),
        })

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
    parser.add_argument("--max-buildeng-records", type=int, default=145117)
    parser.add_argument("--analytic-cases-per-domain", type=int, default=0,
                        help="Original formula-checked analytic cases per engineering family; 0 disables this source.")
    parser.add_argument("--max-mixed-train", type=int, default=24000)
    parser.add_argument("--max-validation", type=int, default=2500)
    parser.add_argument("--max-test", type=int, default=1200)
    parser.add_argument("--swiss-dwellings-dir", type=Path,
                        help="Optional directory containing Swiss Dwellings train/validation/test JSONL and rendered images.")
    parser.add_argument("--ifc-model-corpus-dir", type=Path,
                        help="Optional directory containing IfcOpenShell-parsed IFC model train/validation/test JSONL and manifest.")
    parser.add_argument("--capability-census", type=Path,
                        help="Optional capability-census.json from the pinned native NextCAD/Next BIM inventories.")
    # Legacy flags are train-only. Pass all three prepared files to keep the
    # native project's source lineage and held-out split separate.
    parser.add_argument("--nextcad-native", help="Legacy alias for --nextcad-native-train only.")
    parser.add_argument("--nextbim-native", help="Legacy alias for --nextbim-native-train only.")
    parser.add_argument("--nextcad-native-train")
    parser.add_argument("--nextcad-native-validation")
    parser.add_argument("--nextcad-native-test")
    parser.add_argument("--nextbim-native-train")
    parser.add_argument("--nextbim-native-validation")
    parser.add_argument("--nextbim-native-test")
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()
    if any(value < 0 for value in (
        args.max_cad_train, args.max_cad_validation, args.max_cad_test,
        args.max_bim_train, args.max_bim_validation, args.max_ifcqa_train,
        args.max_ifcqa_test, args.max_buildeng_records, args.max_mixed_train,
        args.analytic_cases_per_domain,
    )):
        parser.error("sample limits cannot be negative")
    print(json.dumps(prepare(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
