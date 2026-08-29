#!/usr/bin/env python3
"""Build the closed AA10 housing-rebuilding catalogue from an authoritative SQLite."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


NATIVE_SKILLS = {28828, 28829}
TERRITORIAL_TARGETS = {641, 644}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_manifest(database: Path) -> dict:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    item_ids = {row[0] for row in connection.execute("SELECT id FROM items")}
    housing_ids = {row[0] for row in connection.execute("SELECT id FROM housings")}

    materials: dict[int, list[dict]] = defaultdict(list)
    for row in connection.execute(
        """SELECT housing_rebuilding_id, item_id, count
           FROM housing_rebuilding_materials ORDER BY id"""
    ):
        materials[row[0]].append({"item_id": row[1], "count": row[2]})

    pack_routes: dict[int, list[dict]] = defaultdict(list)
    definition_packs: dict[int, set[int]] = defaultdict(set)
    for row in connection.execute(
        """SELECT housing_rebuilding_pack_id, housing_rebuilding_id, position
           FROM housing_rebuilding_pack_rebuildings
           ORDER BY housing_rebuilding_pack_id, position, id"""
    ):
        route = {"rebuilding_id": row[1], "position": row[2]}
        pack_routes[row[0]].append(route)
        definition_packs[row[1]].add(row[0])

    source_templates: dict[int, list[int]] = defaultdict(list)
    for row in connection.execute(
        """SELECT id, housing_rebuilding_pack_id FROM housings
           WHERE housing_rebuilding_pack_id IS NOT NULL
             AND housing_rebuilding_pack_id > 0 ORDER BY id"""
    ):
        source_templates[row[1]].append(row[0])

    definitions = []
    reasons = Counter()
    for row in connection.execute(
        """SELECT id, name, skill_id, housing_id, labor_power,
                  actability_group_id, change_point_desc
           FROM housing_rebuildings ORDER BY id"""
    ):
        definition_materials = materials[row["id"]]
        if row["housing_id"] not in housing_ids:
            reason = "missing_target_housing"
        elif row["skill_id"] not in NATIVE_SKILLS:
            reason = "missing_skill_consumer"
        elif not definition_materials:
            reason = (
                "territorial_subsystem_required"
                if row["housing_id"] in TERRITORIAL_TARGETS
                else "missing_materials"
            )
        elif any(
            material["item_id"] not in item_ids or material["count"] <= 0
            for material in definition_materials
        ):
            reason = "missing_item"
        else:
            reason = "executable"
        reasons[reason] += 1

        packs = sorted(definition_packs[row["id"]])
        definitions.append(
            {
                "id": row["id"],
                "name": row["name"],
                "skill_id": row["skill_id"],
                "target_housing_id": row["housing_id"],
                "labor_power": row["labor_power"],
                "actability_group_id": row["actability_group_id"],
                "change_point_desc": row["change_point_desc"],
                "materials": definition_materials,
                "pack_ids": packs,
                "source_housing_ids": sorted(
                    source_id for pack_id in packs for source_id in source_templates[pack_id]
                ),
                "status": reason,
            }
        )

    manifest = {
        "schema": "aa10-housing-rebuilding-manifest-v1",
        "source": {
            "file": database.name,
            "sha256": sha256(database),
            "size": database.stat().st_size,
        },
        "native_contract": {
            "feature": "rebuildHouse (bit 111)",
            "request_opcode": "0x1AB",
            "response_opcode": "0x2BA",
            "skill_object_type": 7,
            "skills": sorted(NATIVE_SKILLS),
            "response_entry": "bt:i32, vt:bool, pd:f64, wp:i32, dtr:i32",
        },
        "summary": {
            "housing_templates": len(housing_ids),
            "templates_with_pack": sum(len(ids) for ids in source_templates.values()),
            "packs_with_routes": len(pack_routes),
            "definitions": len(definitions),
            "materials": sum(len(rows) for rows in materials.values()),
            "pack_routes": sum(len(rows) for rows in pack_routes.values()),
            "classification": dict(sorted(reasons.items())),
        },
        "packs": [
            {
                "id": pack_id,
                "source_housing_ids": source_templates[pack_id],
                "routes": routes,
            }
            for pack_id, routes in sorted(pack_routes.items())
        ],
        "definitions": definitions,
    }
    connection.close()
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not args.database.is_file() or args.database.stat().st_size == 0:
        raise SystemExit(f"invalid authoritative SQLite: {args.database}")
    manifest = build_manifest(args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()
