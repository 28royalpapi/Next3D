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


def _bytes_image(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return base64.b64decode(value, validate=True)
    raise ValueError("dataset image is not bytes")


def make_cad_records(row: dict[str, Any], asset_root: Path, split: str, index: int) -> list[dict[str, Any]]:
    from PIL import Image
    import io

    plan = cad_plan(row.get("cadquery_ops_json"), row.get("num_faces"))
    uuid = re.sub(r"[^A-Za-z0-9_-]", "_", str(row.get("uuid") or index))[:72]
    folder = asset_root / "cad" / split / uuid
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    # The Autodesk teacher was trained on eight views. Preserve all views.
    for view_index in range(8):
        payload = _bytes_image(row.get(f"image_{view_index}"))
        with Image.open(io.BytesIO(payload)) as image:
            image.convert("RGB").save(folder / f"view_{view_index}.jpg", "JPEG", quality=92)
        paths.append(str(folder / f"view_{view_index}.jpg"))

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
    if metadata.get("validated") is not True or score < 4.5:
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


def sample_balanced(groups: dict[str, list[dict[str, Any]]], limit: int, seed: int) -> list[dict[str, Any]]:
    weights = {
        "cad_visual": 0.20,
        "cad_feature_trace": 0.20,
        "bim_ifc_knowledge": 0.25,
        "bim_ifc_qa": 0.10,
        "nextcad_native": 0.125,
        "nextbim_native": 0.125,
    }
    available = {key: rows for key, rows in groups.items() if rows}
    if not available or limit <= 0:
        return []
    total = sum(weights.get(key, 1.0) for key in available)
    rng = random.Random(seed)
    selected = []
    for key, rows in available.items():
        count = min(len(rows), max(1, round(limit * weights.get(key, 1.0) / total)))
        selected.extend(rng.sample(rows, count))
    if len(selected) > limit:
        selected = rng.sample(selected, limit)
    elif len(selected) < limit:
        remaining = [row for rows in available.values() for row in rows if row not in selected]
        rng.shuffle(remaining)
        selected.extend(remaining[:limit - len(selected)])
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
        "cad_visual": [], "cad_feature_trace": [], "bim_ifc_knowledge": [],
        "bim_ifc_qa": [], "nextcad_native": [], "nextbim_native": [],
    }
    validation, tests, quarantine = [], [], []
    counts = Counter()

    cad_limits = [
        ("train", args.max_cad_train, "train"),
        ("val", args.max_cad_validation, "validation"),
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
