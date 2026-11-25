#!/usr/bin/env python3
"""Create privacy-filtered BIM/IFC lessons from local IFC2x3/IFC4 model collections.

The script requires IfcOpenShell only in the external training environment.
It emits schema-aware structured lessons; raw IFC files are never bundled in
Next3D. Dataset quality is not inferred from successful parsing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

GNI_SOURCE = "GNI-BIM Dataset"
GNI_DOI = "10.5281/zenodo.19722012"
GNI_LICENSE = "CC-BY-4.0"
GNI_ATTRIBUTION = (
    "Wang et al., GNI-BIM Dataset, Technical University of Munich, "
    "Georg Nemetschek Institute, Zenodo DOI 10.5281/zenodo.19722012"
)
SYSTEM = (
    "You are NextAI, a Building Information Modeling and IFC specialist. "
    "Interpret the supplied structured IFC extract. Preserve entity classes, "
    "spatial containment, type assignments, units, property values and explicit "
    "relationships. Distinguish data present in the file from information that "
    "is missing. Do not claim that a model is geometrically valid, code-compliant "
    "or engineering-correct merely because it parses."
)

SAFE_ENUM_PROPERTIES = {
    "predefinedtype", "loadbearing", "isexternal", "firerating",
    "fireexit", "combustible", "extendtostructure",
}
RELATION_TYPES = (
    "IfcRelAggregates",
    "IfcRelContainedInSpatialStructure",
    "IfcRelVoidsElement",
    "IfcRelFillsElement",
    "IfcRelConnectsElements",
    "IfcRelDefinesByType",
    "IfcRelAssociatesMaterial",
    "IfcRelDefinesByProperties",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def split_group(group_key: str) -> str:
    bucket = int(hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def split_group_for_file(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    parts = relative.parts
    # Architectural and structural files from one 2026 design team are paired;
    # keep the team project together in one split to prevent leakage.
    if "2026_BIMprojects" in parts:
        idx = parts.index("2026_BIMprojects")
        group = "/".join(parts[: idx + 2]) if len(parts) > idx + 1 else str(relative.parent)
    else:
        # 2025 student submissions are separate models rather than paired files.
        group = str(relative.with_suffix(""))
    return group


def _safe_scalar(name: str, value: Any) -> int | float | bool | str | None:
    key = name.casefold().replace(" ", "").replace("_", "")
    # Deny personal/project identifiers before checking the value type, so
    # even numeric student IDs, phone numbers or addresses cannot slip through.
    denied = (
        "name", "email", "phone", "address", "author", "student",
        "owner", "contact", "person", "projectnumber", "guid", "globalid",
        "userid", "username", "company", "organisation", "organization",
    )
    if any(marker in key for marker in denied):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, str):
        clean = value.strip()
        unsafe_markers = ("@", "/", "\\\\", "email", "phone", "address", "author", "student", "projectnumber")
        lowered = clean.casefold()
        if key in SAFE_ENUM_PROPERTIES and clean and len(clean) <= 64:
            if not any(marker in lowered for marker in unsafe_markers):
                return clean
    return None


def _get_psets(element: Any, util_element: Any) -> dict[str, Any]:
    try:
        return util_element.get_psets(element, should_inherit=True)
    except TypeError:
        try:
            return util_element.get_psets(element)
        except Exception:
            return {}
    except Exception:
        return {}


def _container(element: Any, util_element: Any) -> Any | None:
    try:
        return util_element.get_container(element, should_get_direct=False)
    except TypeError:
        try:
            return util_element.get_container(element)
        except Exception:
            return None
    except Exception:
        return None


def _type_object(element: Any, util_element: Any) -> Any | None:
    try:
        return util_element.get_type(element)
    except Exception:
        return None


def _materials(element: Any, util_element: Any) -> list[str]:
    try:
        mats = util_element.get_materials(element)
        return sorted({material.is_a() for material in mats if material is not None})
    except Exception:
        return []


def _numeric_psets(element: Any, util_element: Any) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for pset_name, properties in _get_psets(element, util_element).items():
        if not isinstance(properties, dict):
            continue
        values = {}
        for property_name, value in properties.items():
            if str(property_name).casefold() == "id":
                continue
            safe = _safe_scalar(str(property_name), value)
            if safe is not None:
                values[str(property_name)[:80]] = safe
        if values:
            output[str(pset_name)[:100]] = values
    return output


def _schema_units(model: Any) -> list[dict[str, str | None]]:
    result = []
    try:
        projects = model.by_type("IfcProject")
        assignment = projects[0].UnitsInContext if projects else None
        for unit in (assignment.Units if assignment else []):
            result.append({
                "unit_type": getattr(unit, "UnitType", None),
                "unit_class": unit.is_a(),
                "name": getattr(unit, "Name", None),
                "prefix": getattr(unit, "Prefix", None),
            })
    except Exception:
        pass
    return result


def extract_model(model: Any, element_chunk_size: int = 64) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    import ifcopenshell.util.element as util_element

    schema = str(getattr(model, "schema", "unknown"))
    spatial_classes = ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]
    spatial_counts = {}
    for ifc_class in spatial_classes:
        try:
            spatial_counts[ifc_class] = len(model.by_type(ifc_class))
        except Exception:
            spatial_counts[ifc_class] = 0

    elements = []
    # Element IDs and all non-element relationship endpoints use generated local
    # surrogate IDs. This preserves IFC graph topology without emitting source
    # GlobalIds, STEP line numbers or file-specific identifiers.
    id_map: dict[int, str] = {}
    entity_type_map: dict[str, str] = {}
    external_endpoints: dict[str, dict[str, str]] = {}
    raw_elements = sorted(model.by_type("IfcElement"), key=lambda item: item.id())
    for index, element in enumerate(raw_elements, 1):
        local_id = f"e{index:06d}"
        id_map[element.id()] = local_id
        entity_type_map[local_id] = element.is_a()

    def endpoint_ref(entity: Any) -> str | None:
        if entity is None or not hasattr(entity, "id"):
            return None
        step_id = entity.id()
        if step_id in id_map:
            return id_map[step_id]
        if step_id not in id_map:
            # IDs are stable only inside this parser run and are never exported.
            local_id = f"x{len(external_endpoints) + 1:07d}"
            id_map[step_id] = local_id
            entity_type_map[local_id] = entity.is_a()
            external_endpoints[local_id] = {
                "local_id": local_id,
                "ifc_class": entity.is_a(),
            }
        return id_map[step_id]

    for index, element in enumerate(raw_elements, 1):
        local_id = id_map[element.id()]
        container = _container(element, util_element)
        type_obj = _type_object(element, util_element)
        try:
            predefined_type = getattr(element, "PredefinedType", None)
        except Exception:
            predefined_type = None
        elements.append({
            "local_id": local_id,
            "ifc_class": element.is_a(),
            "predefined_type": str(predefined_type) if predefined_type else None,
            "type_class": type_obj.is_a() if type_obj else None,
            "container_class": container.is_a() if container else None,
            "container_global_id_hash": (
                hashlib.sha256(str(getattr(container, "GlobalId", "")).encode()).hexdigest()[:12]
                if container and getattr(container, "GlobalId", None) else None
            ),
            "material_classes": _materials(element, util_element),
            "numeric_and_safe_enum_psets": _numeric_psets(element, util_element),
        })

    relationship_rows = []
    relationship_counts = Counter()
    relationship_accessors = {
        "IfcRelAggregates": ("RelatingObject", "RelatedObjects", "aggregates"),
        "IfcRelContainedInSpatialStructure": ("RelatingStructure", "RelatedElements", "spatially_contains"),
        "IfcRelVoidsElement": ("RelatingBuildingElement", "RelatedOpeningElement", "has_opening"),
        "IfcRelFillsElement": ("RelatingOpeningElement", "RelatedBuildingElement", "opening_filled_by"),
        "IfcRelConnectsElements": ("RelatingElement", "RelatedElement", "connects"),
        "IfcRelDefinesByType": ("RelatingType", "RelatedObjects", "has_type"),
        "IfcRelAssociatesMaterial": ("RelatingMaterial", "RelatedObjects", "has_material"),
        "IfcRelDefinesByProperties": ("RelatingPropertyDefinition", "RelatedObjects", "has_property_set"),
    }
    for ifc_class in RELATION_TYPES:
        try:
            relations = model.by_type(ifc_class)
        except Exception:
            relations = []
        for relation in relations:
            relationship_counts[ifc_class] += 1
            left_name, right_name, relation_type = relationship_accessors[ifc_class]
            left = getattr(relation, left_name, None)
            right = getattr(relation, right_name, None)
            left_id = endpoint_ref(left)
            right_values = right if isinstance(right, (list, tuple)) else [right]
            for right_value in right_values:
                right_id = endpoint_ref(right_value)
                if left_id and right_id:
                    relationship_rows.append({
                        "source": left_id,
                        "source_class": entity_type_map[left_id],
                        "target": right_id,
                        "target_class": entity_type_map[right_id],
                        "relation": relation_type,
                        "ifc_relationship": ifc_class,
                    })

    counts = Counter(item["ifc_class"] for item in elements)
    material_count = sum(bool(item["material_classes"]) for item in elements)
    pset_count = sum(bool(item["numeric_and_safe_enum_psets"]) for item in elements)
    summary = {
        "schema": "nextai.ifc_model_summary.v1",
        "ifc_schema": schema,
        "spatial_structure_counts": spatial_counts,
        "element_count": len(elements),
        "element_counts_by_ifc_class": dict(sorted(counts.items())),
        "relationship_counts": dict(sorted(relationship_counts.items())),
        "relationship_edges_extracted": len(relationship_rows),
        "elements_with_material_association": material_count,
        "elements_with_numeric_or_safe_enum_psets": pset_count,
        "project_units": _schema_units(model),
        "limitations": [
            "Parsing does not prove geometric validity, model completeness, design adequacy or statutory compliance.",
            "Only numeric values and a small allow-list of safe IFC enumeration properties are retained; free-text names and personal metadata are omitted.",
            "Relationships preserve connections to external type, material, property-set and spatial endpoints using generated local references; endpoint labels and source identifiers are not emitted.",
            "Element identifiers are remapped to local surrogate IDs; original GlobalIds and file paths are not emitted.",
        ],
    }
    chunks = []
    for start in range(0, len(elements), element_chunk_size):
        subset = elements[start : start + element_chunk_size]
        included = {item["local_id"] for item in subset}
        # Keep any relationship touching this chunk. The other endpoint may be
        # a type object, material, property set, spatial container, or an element
        # stored in another chunk; preserve its class and local surrogate ID.
        edges = [
            edge for edge in relationship_rows
            if edge["source"] in included or edge["target"] in included
        ]
        external = {}
        for edge in edges:
            for endpoint_id in (edge["source"], edge["target"]):
                if endpoint_id not in included:
                    external[endpoint_id] = external_endpoints.get(
                        endpoint_id,
                        {"local_id": endpoint_id, "ifc_class": entity_type_map[endpoint_id]},
                    )
        chunks.append({
            "schema": "nextai.ifc_element_inventory.v1",
            "ifc_schema": schema,
            "element_chunk_start": start,
            "elements": subset,
            "relationships_touching_chunk": edges,
            "external_relationship_endpoints": sorted(external.values(), key=lambda row: row["local_id"]),
            "note": "Relationship edges may refer to external endpoints. IDs are generated local references, not source GlobalIds.",
        })
    return summary, chunks


def build_records(
    path: Path,
    root: Path,
    source_name: str,
    doi: str,
    license_id: str,
    chunk_size: int,
) -> list[dict[str, Any]]:
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    summary, chunks = extract_model(model, chunk_size)
    digest = sha256_file(path)
    rel_path = path.relative_to(root).as_posix()
    source_id = f"{source_name}:{digest[:16]}"
    records = [{
        "record_id": f"ifc-summary-{digest[:16]}",
        "domain": "ifc_model_summary",
        "system": SYSTEM,
        "prompt": (
            "Produce a BIM model inventory from this parsed IFC model. Explain its "
            "schema, spatial structure, element-class coverage, relationships, unit "
            "assignments and information gaps. State what is not validated."
        ),
        "completion": json.dumps(summary, ensure_ascii=False, separators=(",", ":")),
        "images": [],
        "source": source_name,
        "source_doi": doi,
        "license": license_id,
        "attribution": source_name,
        "source_file_sha256": digest,
        "split_group": split_group_for_file(path, root),
    }]
    for index, chunk in enumerate(chunks):
        records.append({
            "record_id": f"ifc-inventory-{digest[:12]}-{index:04d}",
            "domain": "ifc_element_inventory",
            "system": SYSTEM,
            "prompt": (
                f"Interpret this IFC {chunk['ifc_schema']} element inventory chunk. "
                "Identify the element classes, safe property information, material "
                "assignments, type assignments and explicitly shown relationships. "
                "Do not infer missing engineering calculations."
            ),
            "completion": json.dumps(chunk, ensure_ascii=False, separators=(",", ":")),
            "images": [],
            "source": source_name,
            "source_doi": doi,
            "license": license_id,
            "attribution": source_name,
            "source_file_sha256": digest,
            "split_group": split_group_for_file(path, root),
        })
    return records


def prepare(
    root: Path,
    output_dir: Path,
    source_name: str = GNI_SOURCE,
    doi: str = GNI_DOI,
    license_id: str = GNI_LICENSE,
    max_train: int = 160,
    max_validation: int = 24,
    max_test: int = 24,
    max_file_bytes: int = 256 * 1024 * 1024,
    chunk_size: int = 64,
) -> dict[str, Any]:
    root = root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    caps = {"train": max_train, "validation": max_validation, "test": max_test}
    candidates = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".ifc", ".ifczip"}
    )
    grouped: dict[str, list[Path]] = defaultdict(list)
    skipped = []
    for path in candidates:
        if path.stat().st_size > max_file_bytes:
            skipped.append({"file_hash": sha256_file(path)[:16], "reason": "file exceeds configured byte cap"})
            continue
        group = split_group_for_file(path, root)
        grouped[split_group(group)].append(path)

    selected = {}
    for split, paths in grouped.items():
        selected[split] = sorted(paths, key=lambda p: sha256_file(p)[:16])[: caps[split]]

    output = {"train": [], "validation": [], "test": []}
    quarantine = []
    for split, files in selected.items():
        for path in files:
            try:
                output[split].extend(build_records(path, root, source_name, doi, license_id, chunk_size))
            except Exception as exc:
                quarantine.append({
                    "file_hash": sha256_file(path)[:16],
                    "reason": f"{type(exc).__name__}: {str(exc)[:240]}",
                })

    for split, records in output.items():
        with (output_dir / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (output_dir / "quarantine.jsonl").open("w", encoding="utf-8") as handle:
        for row in quarantine + skipped:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": 1,
        "source": source_name,
        "doi": doi,
        "license": license_id,
        "parser": "IfcOpenShell",
        "privacy_policy": "no original GlobalIds, source paths, free-text names, author fields or contact details emitted",
        "group_split_rule": "paired BIM project files remain in one split; other files split by source model",
        "model_files": {split: len(files) for split, files in selected.items()},
        "training_records": {split: len(records) for split, records in output.items()},
        "quarantined_or_skipped_files": len(quarantine) + len(skipped),
        "test_not_used_for_training": True,
        "raw_ifc_files_not_shipped_in_installer": True,
        "warning": "Successful IFC parsing is not proof that a student coursework model is correct or safe for engineering use.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Directory containing .ifc and/or .ifczip files")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-name", default=GNI_SOURCE)
    parser.add_argument("--doi", default=GNI_DOI)
    parser.add_argument("--license", default=GNI_LICENSE)
    parser.add_argument("--max-train", type=int, default=160)
    parser.add_argument("--max-validation", type=int, default=24)
    parser.add_argument("--max-test", type=int, default=24)
    parser.add_argument("--max-file-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--chunk-size", type=int, default=64)
    args = parser.parse_args()
    if min(args.max_train, args.max_validation, args.max_test) < 0:
        parser.error("model limits cannot be negative")
    if not 1 <= args.chunk_size <= 256:
        parser.error("chunk size must be between 1 and 256")
    print(json.dumps(prepare(
        args.root, args.output_dir, args.source_name, args.doi, args.license,
        args.max_train, args.max_validation, args.max_test,
        args.max_file_bytes, args.chunk_size
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
