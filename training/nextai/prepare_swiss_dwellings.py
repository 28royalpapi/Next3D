#!/usr/bin/env python3
"""Build image-to-vector floor-plan lessons from Swiss Dwellings v3.0.0.

The 931.9 MB source archive is read directly as a ZIP member; it is not extracted
in full and is never copied into the Next3D installer. Records preserve the
source's metric local coordinate system and are grouped/split by building so
that floors from one building cannot leak across train/validation/test.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SOURCE_NAME = "Swiss Dwellings v3.0.0"
SOURCE_DOI = "10.5281/zenodo.7788422"
SOURCE_LICENSE = "CC-BY-4.0"
ATTRIBUTION = (
    "Standfest et al., Swiss Dwellings v3.0.0, Archilyse AG, "
    "Zenodo DOI 10.5281/zenodo.7788422"
)
SYSTEM = (
    "You are NextAI, an architectural CAD and BIM specialist. Interpret the "
    "supplied floor-plan image using the provided task and return structured "
    "room and building information. Preserve the source coordinate frame and "
    "metres. Distinguish rooms, separators, openings and fixtures. Do not infer "
    "door connectivity from proximity alone, invent dimensions, or claim code "
    "compliance. The vector geometry supplied in a training target is ground "
    "truth for this example."
)

REQUIRED_COLUMNS = {
    "site_id", "building_id", "floor_id", "plan_id",
    "entity_type", "entity_subtype", "geometry",
}


def floor_key(row: dict[str, str]) -> tuple[str, str, str, str] | None:
    site = (row.get("site_id") or "").strip()
    building = (row.get("building_id") or "").strip()
    floor = (row.get("floor_id") or "").strip()
    plan = (row.get("plan_id") or "").strip()
    if not site or not building or not floor:
        return None
    return site, building, floor, plan


def building_split(site_id: str, building_id: str) -> str:
    key = f"{site_id}:{building_id}".encode("utf-8")
    bucket = int(hashlib.sha256(key).hexdigest()[:8], 16) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "test"


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_ref(prefix: str, key: tuple[str, ...], value: str | None) -> str | None:
    if not value:
        return None
    raw = ":".join((*key, value))
    return f"{prefix}_{_stable_hash(raw)[:12]}"


def _json_coordinates(value: Any, digits: int = 4) -> Any:
    if isinstance(value, (tuple, list)):
        return [_json_coordinates(item, digits) for item in value]
    if isinstance(value, (int, float)):
        return round(float(value), digits)
    return value


def _geometry_to_record(row: dict[str, str], geometry: Any, key: tuple[str, ...]) -> dict[str, Any]:
    from shapely.geometry import mapping

    entity_type = (row.get("entity_type") or "").strip().lower()
    subtype = (row.get("entity_subtype") or "").strip().upper()
    return {
        "entity_type": entity_type,
        "entity_subtype": subtype,
        "unit_usage": (row.get("unit_usage") or "").strip().upper() or None,
        "apartment_ref": _safe_ref("apt", key, row.get("apartment_id")),
        "unit_ref": _safe_ref("unit", key, row.get("unit_id")),
        "area_ref": _safe_ref("area", key, row.get("area_id")),
        "geometry_type": geometry.geom_type,
        "coordinates_m": _json_coordinates(mapping(geometry).get("coordinates")),
        "area_m2": round(float(geometry.area), 4) if entity_type == "area" else None,
        "length_m": round(float(geometry.length), 4),
        "elevation_m": _float_or_none(row.get("elevation")),
        "height_m": _float_or_none(row.get("height")),
    }


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _geometry_parts(geometry: Any):
    kind = geometry.geom_type
    if kind == "Polygon":
        yield "polygon", list(geometry.exterior.coords)
        for interior in geometry.interiors:
            yield "line", list(interior.coords)
    elif kind in {"MultiPolygon", "GeometryCollection"}:
        for child in geometry.geoms:
            yield from _geometry_parts(child)
    elif kind in {"LineString", "LinearRing"}:
        yield "line", list(geometry.coords)
    elif kind == "MultiLineString":
        for child in geometry.geoms:
            yield from _geometry_parts(child)
    elif kind == "Point":
        yield "point", [(geometry.x, geometry.y)]
    elif kind == "MultiPoint":
        for child in geometry.geoms:
            yield from _geometry_parts(child)


def render_floor(entities: list[dict[str, Any]], image_path: Path, size: int = 512) -> None:
    from PIL import Image, ImageDraw
    from shapely import wkt

    geometries = [wkt.loads(item["geometry"]) for item in entities]
    bounds = [geometry.bounds for geometry in geometries if not geometry.is_empty]
    if not bounds:
        raise ValueError("floor has no drawable geometry")
    min_x = min(item[0] for item in bounds)
    min_y = min(item[1] for item in bounds)
    max_x = max(item[2] for item in bounds)
    max_y = max(item[3] for item in bounds)
    span_x = max(max_x - min_x, 0.01)
    span_y = max(max_y - min_y, 0.01)
    margin = 22
    scale = min((size - 2 * margin) / span_x, (size - 2 * margin) / span_y)

    def point_to_pixel(point):
        x, y = point[:2]
        px = margin + (x - min_x) * scale
        py = size - margin - (y - min_y) * scale
        return int(round(px)), int(round(py))

    image = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(image)
    palette = {
        "area": ((240, 244, 248), (55, 75, 95)),
        "separator": (None, (25, 35, 45)),
        "opening": (None, (190, 65, 45)),
        "feature": (None, (35, 120, 95)),
        "outline": (None, (100, 90, 160)),
    }

    # Areas are rendered first so walls, openings and fixtures remain visible.
    ordered = sorted(
        zip(entities, geometries),
        key=lambda pair: {"area": 0, "outline": 1, "separator": 2, "opening": 3, "feature": 4}.get(
            (pair[0].get("entity_type") or "").lower(), 5
        ),
    )
    for row, geometry in ordered:
        entity_type = (row.get("entity_type") or "").lower()
        fill, outline = palette.get(entity_type, (None, (40, 40, 40)))
        for part_kind, coordinates in _geometry_parts(geometry):
            pts = [point_to_pixel(point) for point in coordinates]
            if part_kind == "polygon" and len(pts) >= 3:
                draw.polygon(pts, fill=fill, outline=outline, width=2)
            elif part_kind == "line" and len(pts) >= 2:
                width = 4 if entity_type == "separator" else 2
                draw.line(pts, fill=outline, width=width)
            elif part_kind == "point" and pts:
                x, y = pts[0]
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=outline)

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(image_path, format="PNG", optimize=True)


def _open_geometry_csv(archive: zipfile.ZipFile, member: str):
    return io.TextIOWrapper(archive.open(member, "r"), encoding="utf-8-sig", newline="")


def find_geometry_member(archive: zipfile.ZipFile, requested: str | None = None) -> str:
    if requested:
        if requested not in archive.namelist():
            raise FileNotFoundError(f"ZIP member not found: {requested}")
        return requested
    matches = [name for name in archive.namelist() if name.lower().endswith("geometries.csv")]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one geometries.csv in the ZIP; specify --geometry-member. "
            f"Found {len(matches)} candidates."
        )
    return matches[0]


def discover_selected_floors(
    archive: zipfile.ZipFile,
    member: str,
    caps: dict[str, int],
    seed: int,
) -> tuple[dict[str, set[tuple[str, str, str, str]]], dict[str, int]]:
    pools: dict[str, set[tuple[str, str, str, str]]] = {
        "train": set(), "validation": set(), "test": set()
    }
    row_count = 0
    with _open_geometry_csv(archive, member) as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"geometries.csv missing columns: {sorted(missing)}")
        for row in reader:
            row_count += 1
            key = floor_key(row)
            if key is None:
                continue
            pools[building_split(key[0], key[1])].add(key)

    selected = {}
    for split, keys in pools.items():
        ordered = sorted(
            keys,
            key=lambda key: _stable_hash(f"{seed}:{':'.join(key)}"),
        )
        selected[split] = set(ordered[: max(0, caps[split])])
    return selected, {"csv_rows_scanned": row_count, **{f"{key}_floor_keys": len(value) for key, value in pools.items()}}


def _room_adjacency(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links = []
    for i in range(len(rooms)):
        for j in range(i + 1, len(rooms)):
            shared = rooms[i]["_geometry"].boundary.intersection(rooms[j]["_geometry"].boundary)
            shared_length = float(shared.length)
            if shared_length > 0.01:
                links.append({
                    "room_a": rooms[i]["area_ref"],
                    "room_b": rooms[j]["area_ref"],
                    "relation": "shared_boundary",
                    "shared_boundary_m": round(shared_length, 4),
                })
    for room in rooms:
        room.pop("_geometry", None)
    return links


def prepare(
    zip_path: Path,
    output_dir: Path,
    max_train: int = 600,
    max_validation: int = 60,
    max_test: int = 60,
    image_size: int = 512,
    seed: int = 3407,
    geometry_member: str | None = None,
) -> dict[str, Any]:
    from shapely import wkt

    caps = {"train": max_train, "validation": max_validation, "test": max_test}
    output_dir.mkdir(parents=True, exist_ok=True)
    asset_root = output_dir / "assets"
    records: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    quarantined = []
    source_counts = Counter()

    with zipfile.ZipFile(zip_path) as archive:
        member = find_geometry_member(archive, geometry_member)
        selected, discovery_stats = discover_selected_floors(archive, member, caps, seed)
        selected_lookup = {
            key: split for split, keys in selected.items() for key in keys
        }
        grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)

        with _open_geometry_csv(archive, member) as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                key = floor_key(row)
                if key in selected_lookup:
                    grouped[key].append(row)
                    source_counts[(row.get("entity_type") or "unknown").lower()] += 1

        for key in sorted(grouped):
            split = selected_lookup[key]
            raw_rows = grouped[key]
            parsed = []
            area_geometries = []
            valid_geometries = []
            for row_index, row in enumerate(raw_rows):
                raw_wkt = (row.get("geometry") or "").strip()
                if not raw_wkt:
                    quarantined.append({"floor_hash": _stable_hash(":".join(key))[:12], "row": row_index, "reason": "empty geometry"})
                    continue
                try:
                    geometry = wkt.loads(raw_wkt)
                    if geometry.is_empty or not geometry.is_valid:
                        raise ValueError("empty or invalid WKT geometry")
                    entity = _geometry_to_record(row, geometry, key)
                    parsed.append((row, geometry, entity))
                    valid_geometries.append(geometry)
                    if entity["entity_type"] == "area":
                        area_geometries.append((row, geometry, entity))
                except Exception as exc:
                    quarantined.append({
                        "floor_hash": _stable_hash(":".join(key))[:12],
                        "row": row_index,
                        "reason": str(exc)[:200],
                    })

            if not area_geometries:
                quarantined.append({"floor_hash": _stable_hash(":".join(key))[:12], "reason": "no valid room-area polygons"})
                continue

            record_id = f"swiss-floor-{_stable_hash(':'.join(key))[:16]}"
            image_path = asset_root / split / f"{record_id}.png"
            try:
                render_floor([row for row, _geometry, _entity in parsed], image_path, image_size)
            except Exception as exc:
                quarantined.append({"record_id": record_id, "reason": f"render failed: {str(exc)[:180]}"})
                continue

            rooms = []
            for row, geometry, entity in area_geometries:
                if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                    continue
                room = dict(entity)
                room["room_label"] = entity["entity_subtype"]
                room["geometry"] = {
                    "type": entity["geometry_type"],
                    "coordinates_m": entity["coordinates_m"],
                }
                room["calculated_area_m2"] = round(float(geometry.area), 4)
                room["calculated_perimeter_m"] = round(float(geometry.length), 4)
                room["_geometry"] = geometry
                rooms.append(room)

            adjacency = _room_adjacency(rooms)
            counts = Counter(
                f"{entity['entity_type']}:{entity['entity_subtype']}"
                for _row, _geometry, entity in parsed
            )
            target = {
                "schema": "nextai.swiss_dwellings_floorplan.v1",
                "units": "metres",
                "coordinate_frame": {
                    "type": "local_site_coordinates",
                    "x_axis": "east",
                    "y_axis": "north",
                    "warning": "Coordinates are local to the source site; they are not national-grid or geodetic coordinates.",
                },
                "floor": {
                    "site_ref": _safe_ref("site", key, key[0]),
                    "building_ref": _safe_ref("building", key, key[1]),
                    "floor_ref": f"floor_{_stable_hash(':'.join(key))[:12]}",
                    "plan_ref": _safe_ref("plan", key, key[3]),
                    "room_count": len(rooms),
                },
                "rooms": [
                    {k: v for k, v in room.items() if k != "_geometry"}
                    for room in rooms
                ],
                "room_shared_boundary_graph": adjacency,
                "element_counts_by_category": dict(sorted(counts.items())),
                "source_geometry_rows": len(parsed),
                "relationship_rule": (
                    "Only explicit area/unit IDs and computed shared room boundaries are included. "
                    "A shared boundary is not proof of a door or passable connection."
                ),
                "validation_targets": [
                    "all room polygons are valid",
                    "room area and perimeter are consistent with the source metric geometry",
                    "shared-boundary graph is derived from polygon intersections",
                    "source coordinates remain in metres and local-site orientation",
                ],
            }
            prompt = (
                "Interpret this real vector-derived building floor-plan image. "
                "Return the room labels, their exact metric boundary geometry, "
                "measured area and perimeter, and the shared-boundary graph in the "
                "specified schema. Do not infer door connectivity from shared walls. "
                "Keep the local site coordinate frame in metres."
            )
            records[split].append({
                "record_id": record_id,
                "domain": "swiss_dwellings_floorplan",
                "system": SYSTEM,
                "prompt": prompt,
                "completion": json.dumps(target, ensure_ascii=False, separators=(",", ":")),
                "images": [str(image_path)],
                "source": SOURCE_NAME,
                "source_doi": SOURCE_DOI,
                "license": SOURCE_LICENSE,
                "attribution": ATTRIBUTION,
                "source_split": split,
                "building_split_key": _stable_hash(f"{key[0]}:{key[1]}"),
            })

    for split, rows in records.items():
        path = output_dir / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for record in rows:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    with (output_dir / "quarantine.jsonl").open("w", encoding="utf-8") as handle:
        for item in quarantined:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    manifest = {
        "schema_version": 1,
        "source": SOURCE_NAME,
        "doi": SOURCE_DOI,
        "license": SOURCE_LICENSE,
        "attribution": ATTRIBUTION,
        "source_archive_size_label": "931.9 MB as displayed by Zenodo; the actual downloaded file size is recorded separately if available",
        "training_source_only_not_runtime_dependency": True,
        "split_by_building_to_prevent_floor_leakage": True,
        "discovery": discovery_stats,
        "selected_floor_keys": {split: len(keys) for split, keys in selected.items()},
        "records": {split: len(rows) for split, rows in records.items()},
        "quarantined_items": len(quarantined),
        "entity_type_rows_in_selected_floors": dict(source_counts),
        "coordinate_units": "metres",
        "source_ids_pseudonymized_in_targets": True,
        "notes": [
            "The source contains real, manually quality-reviewed building plan geometry, but is not a certified engineering design dataset.",
            "Images are rendered from source vectors; exact room labels and coordinates are supervised from vector geometry, not estimated from pixels.",
            "Dataset simulation/environmental columns and location metadata are intentionally not included in these training records.",
            "Rooms sharing a boundary are not assumed to have a door or navigable connection.",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--geometry-member")
    parser.add_argument("--max-train", type=int, default=600)
    parser.add_argument("--max-validation", type=int, default=60)
    parser.add_argument("--max-test", type=int, default=60)
    parser.add_argument("--image-size", type=int, default=512)
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()
    if min(args.max_train, args.max_validation, args.max_test) < 0:
        parser.error("sample caps cannot be negative")
    if not 256 <= args.image_size <= 1024:
        parser.error("image size must be between 256 and 1024")
    result = prepare(
        args.zip, args.output_dir, args.max_train, args.max_validation,
        args.max_test, args.image_size, args.seed, args.geometry_member
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
