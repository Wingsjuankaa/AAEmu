#!/usr/bin/env python3
"""Build the AA10 r575 housing-area polygon catalogue used by Housing H1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


PROJECT = Path(r"E:\AAEmu\rama_10")
REPO = PROJECT / "server" / "AAEmu"
FULL_DB = PROJECT / "data" / "sqlite" / "authoritative" / "game_decrypted.sqlite3"
COMPACT_DB = PROJECT / "client" / "ArcheAge-Returns-10.0.2.13-r575" / "game" / "db" / "compact.sqlite3"
RUNTIME_DB = REPO / ".server_files" / "AAEmu.Game" / "Data" / "compact.sqlite3"
X2GAME = PROJECT / "client" / "ArcheAge-Returns-10.0.2.13-r575" / "Bin64" / "x2game.dll"
PAK_INDEX = PROJECT / "forensics" / "output" / "aa10-client-forensics" / "returns-r575-pak-index.csv"
FRONTIER = PROJECT / "forensics" / "output" / "aa10-client-forensics" / "housing-h1-frontier"
EXTRACTED = FRONTIER / "extracted" / "game"
ENTRY_LIST = FRONTIER / "housing-area-entries.txt"
OUTPUT = REPO / "AAEmu.Game" / "Data" / "housing_area_shapes_aa10_h1.json"
MANIFEST = REPO / "reconstruccion_cliente_10" / "housing_h1" / "generated" / "aa10-housing-h1-manifest.json"
CELL_SIZE = 1024.0
ENTRY_PATTERN = re.compile(
    r"^game/worlds/main_world/(?:world\.xml|level_design/zone/[^/]+/client/housing_area\.xml)$",
    re.IGNORECASE,
)


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest().upper()


def load_index() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with PAK_INDEX.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter=";"):
            name = row["name"].replace("\\", "/")
            if ENTRY_PATTERN.match(name):
                rows[name.lower()] = row | {"name": name}
    return rows


def write_entry_list() -> None:
    rows = load_index()
    names = sorted(row["name"] for row in rows.values())
    world_count = sum(name.lower().endswith("/world.xml") for name in names)
    shape_file_count = sum(name.lower().endswith("/housing_area.xml") for name in names)
    if world_count != 1 or shape_file_count == 0:
        raise ValueError(
            f"Unexpected AA10 housing source set: world={world_count}, shapes={shape_file_count}"
        )
    FRONTIER.mkdir(parents=True, exist_ok=True)
    ENTRY_LIST.write_text("\n".join(names) + "\n", encoding="utf-8")
    print(f"entry_list={ENTRY_LIST}")
    print(f"entries={len(names)}")


def vector(value: str, default: tuple[float, ...]) -> tuple[float, ...]:
    if not value:
        return default
    result = tuple(float(item) for item in value.split(","))
    if len(result) != len(default) or not all(math.isfinite(item) for item in result):
        raise ValueError(f"Malformed vector: {value}")
    return result


def rotate(
    point: tuple[float, float, float],
    quaternion: tuple[float, float, float, float],
) -> tuple[float, float, float]:
    px, py, pz = point
    w, x, y, z = quaternion
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm <= 0.0 or not math.isfinite(norm):
        raise ValueError("Invalid entity quaternion")
    w, x, y, z = w / norm, x / norm, y / norm, z / norm
    return (
        (1 - 2 * (y * y + z * z)) * px
        + 2 * (x * y - z * w) * py
        + 2 * (x * z + y * w) * pz,
        2 * (x * y + z * w) * px
        + (1 - 2 * (x * x + z * z)) * py
        + 2 * (y * z - x * w) * pz,
        2 * (x * z - y * w) * px
        + 2 * (y * z + x * w) * py
        + (1 - 2 * (x * x + y * y)) * pz,
    )


def read_native_catalog(db_path: Path) -> tuple[dict[int, dict[str, object]], dict[str, int]]:
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        active_areas = {
            int(row[0]): {"name": row[1], "group_id": int(row[2])}
            for row in connection.execute(
                "SELECT id,name,housing_group_id FROM housing_areas WHERE activated='t'"
            )
        }
        metrics = {
            "housings": connection.execute("SELECT count(*) FROM housings").fetchone()[0],
            "housings_with_size": connection.execute(
                "SELECT count(*) FROM housings WHERE coalesce(housing_size_id,0)>0"
            ).fetchone()[0],
            "housing_sizes": connection.execute("SELECT count(*) FROM housing_sizes").fetchone()[0],
            "item_housings": connection.execute("SELECT count(*) FROM item_housings").fetchone()[0],
            "active_housing_areas": len(active_areas),
            "group_categories": connection.execute(
                "SELECT count(*) FROM housing_group_categories"
            ).fetchone()[0],
        }
    finally:
        connection.close()
    return active_areas, metrics


def verified_source(path: Path, index: dict[str, dict[str, str]]) -> dict[str, object]:
    relative = path.relative_to(EXTRACTED).as_posix()
    key = f"game/{relative}".lower()
    if key not in index:
        raise ValueError(f"Missing game_pak index entry: {key}")
    expected = index[key]["md5"].upper()
    actual = digest(path, "md5")
    if actual != expected:
        raise ValueError(f"MD5 mismatch for {key}: {actual} != {expected}")
    return {
        "path": index[key]["name"],
        "bytes": path.stat().st_size,
        "md5": actual,
    }


def build() -> None:
    index = load_index()
    active_areas, full_metrics = read_native_catalog(FULL_DB)
    compact_areas, compact_metrics = read_native_catalog(COMPACT_DB)
    if active_areas != compact_areas or full_metrics != compact_metrics:
        raise ValueError("AA10 full and retail compact housing closure differs")
    if full_metrics["housings"] != full_metrics["housings_with_size"]:
        raise ValueError("Not every AA10 housing template has a native size")

    world_path = EXTRACTED / "worlds" / "main_world" / "world.xml"
    world_source = verified_source(world_path, index)
    world_root = ET.parse(world_path).getroot()
    zone_list = world_root.find("ZoneList")
    if zone_list is None:
        raise ValueError("main_world/world.xml has no ZoneList")
    zones = {int(zone.attrib["id"]): zone for zone in zone_list}

    source_files = sorted(
        (EXTRACTED / "worlds" / "main_world" / "level_design" / "zone").glob(
            "*/client/housing_area.xml"
        ),
        key=lambda path: int(path.parts[-3]),
    )
    expected_files = sum(row["name"].lower().endswith("/housing_area.xml") for row in index.values())
    if len(source_files) != expected_files:
        raise ValueError(f"Extracted {len(source_files)} housing files, expected {expected_files}")

    verified_files: list[dict[str, object]] = []
    shapes: list[dict[str, object]] = []
    client_area_ids: list[int] = []
    source_point_count = 0
    rotated_shapes = 0
    zone_name_mismatches: list[dict[str, object]] = []

    for source_path in source_files:
        verified_files.append(verified_source(source_path, index))
        zone_id = int(source_path.parts[-3])
        zone = zones.get(zone_id)
        if zone is None:
            raise ValueError(f"Housing source references absent zone {zone_id}")
        zone_name = zone.attrib["name"]
        origin_x = int(zone.attrib["originX"])
        origin_y = int(zone.attrib["originY"])

        root = ET.parse(source_path).getroot()
        for entity in root.findall("Entity"):
            area = entity.find("Area")
            points_node = area.find("Points") if area is not None else None
            if area is None or points_node is None:
                continue
            area_id = int(area.attrib.get("value1", "0"))
            client_area_ids.append(area_id)
            points = points_node.findall("Point")
            source_point_count += len(points)
            if area_id == 0 or area_id not in active_areas:
                continue
            if len(points) < 3:
                raise ValueError(f"Area {area_id} has fewer than three points")

            entity_position = vector(entity.attrib.get("Pos", ""), (0.0, 0.0, 0.0))
            entity_scale = vector(entity.attrib.get("Scale", ""), (1.0, 1.0, 1.0))
            entity_rotation = vector(entity.attrib.get("Rotate", ""), (1.0, 0.0, 0.0, 0.0))
            if "Rotate" in entity.attrib:
                rotated_shapes += 1
            cell_x = int(entity.attrib.get("cellX", "0"))
            cell_y = int(entity.attrib.get("cellY", "0"))
            base_x = (origin_x + cell_x) * CELL_SIZE + entity_position[0]
            base_y = (origin_y + cell_y) * CELL_SIZE + entity_position[1]

            transformed: list[dict[str, float]] = []
            for point in points:
                local = vector(point.attrib.get("Pos", ""), (0.0, 0.0, 0.0))
                scaled = tuple(local[index] * entity_scale[index] for index in range(3))
                rotated = rotate(scaled, entity_rotation)
                x = base_x + rotated[0]
                y = base_y + rotated[1]
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ValueError(f"Area {area_id} produced a non-finite point")
                transformed.append({"X": round(x, 6), "Y": round(y, 6)})

            xs = [point["X"] for point in transformed]
            ys = [point["Y"] for point in transformed]
            shapes.append(
                {
                    "AreaId": area_id,
                    "ZoneId": zone_id,
                    "World": "main_world",
                    "EntityGuid": entity.attrib.get("EntityGuid", ""),
                    "MinX": min(xs),
                    "MinY": min(ys),
                    "MaxX": max(xs),
                    "MaxY": max(ys),
                    "Points": transformed,
                }
            )
            if active_areas[area_id]["name"] != zone_name:
                zone_name_mismatches.append(
                    {
                        "area_id": area_id,
                        "runtime_name": active_areas[area_id]["name"],
                        "shape_zone_id": zone_id,
                        "shape_zone_name": zone_name,
                    }
                )

    shapes.sort(key=lambda shape: (shape["AreaId"], shape["ZoneId"], shape["EntityGuid"]))
    covered = {int(shape["AreaId"]) for shape in shapes}
    client_unique = {area_id for area_id in client_area_ids if area_id != 0}
    missing = sorted(set(active_areas) - covered)
    diagnostic_only = sorted(client_unique - set(active_areas))
    duplicates = {
        str(area_id): count
        for area_id, count in sorted(Counter(int(shape["AreaId"]) for shape in shapes).items())
        if count > 1
    }

    payload = {
        "SchemaVersion": 1,
        "Source": "ArcheAge Returns 10.0.2.13 r575 game_pak",
        "Shapes": shapes,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metrics = full_metrics | {
        "client_shape_files": len(source_files),
        "client_shapes_total": len(client_area_ids),
        "client_unique_nonzero_area_ids": len(client_unique),
        "source_points_total": source_point_count,
        "promoted_shapes": len(shapes),
        "promoted_unique_areas": len(covered),
        "promoted_points": sum(len(shape["Points"]) for shape in shapes),
        "rotated_promoted_shapes": rotated_shapes,
        "runtime_areas_without_shape": len(missing),
        "client_area_ids_without_runtime_mapping": len(diagnostic_only),
        "runtime_name_vs_shape_zone_mismatches": len(zone_name_mismatches),
    }
    manifest = {
        "schema_version": 1,
        "wave": "AA10 native Housing H1",
        "classification": ["client-native", "server-required", "diagnostic-only"],
        "inputs": {
            "full": {"path": str(FULL_DB), "sha256": digest(FULL_DB)},
            "compact": {"path": str(COMPACT_DB), "sha256": digest(COMPACT_DB)},
            "runtime": {"path": str(RUNTIME_DB), "sha256": digest(RUNTIME_DB)},
            "x2game": {"path": str(X2GAME), "sha256": digest(X2GAME)},
            "game_pak_index": {"path": str(PAK_INDEX), "sha256": digest(PAK_INDEX)},
            "world_xml": world_source,
            "housing_area_xml": verified_files,
        },
        "metrics": metrics,
        "evidence": {
            "duplicate_promoted_area_shapes": duplicates,
            "runtime_areas_without_shape": missing,
            "client_area_ids_without_runtime_mapping": diagnostic_only,
            "runtime_name_vs_shape_zone_mismatches": zone_name_mismatches,
        },
        "constraints": {
            "aa8_values_copied": 0,
            "full_circular_footprint_gate": True,
            "manual_acceptance_pending": True,
        },
        "output": {"path": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "sha256": digest(OUTPUT)},
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"output_sha256={manifest['output']['sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-entry-list", action="store_true")
    args = parser.parse_args()
    if args.write_entry_list:
        write_entry_list()
    else:
        build()


if __name__ == "__main__":
    main()
