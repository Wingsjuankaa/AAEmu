#!/usr/bin/env python3
"""Build the AA8 actorless Honor-store stock observed through openType 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


CAPTURE_SCHEMA = "AA8_MERCHANT_PURCHASE_RECONSTRUCTION_CAPTURE_V1"
GLOBAL_OPEN_TYPE = 2
HONOR_CURRENCY_ID = 1
MERCHANT_PACK_ID = 920002

# Page/column order observed in the AA8 client. Prices are Honor points.
STOCK = (
    (45732, 3, 10_000, "Decrystallization Scroll"),
    (36602, 7, 50_000, "Bound Superior Yellow Regrade Charm"),
    (36604, 7, 100_000, "Bound Superior Red Regrade Charm"),
    (39585, 0, 2_500, "Bound Worn Costume"),
    (48858, 3, 13_000, "Bound Weapon Tempering Charm"),
    (48859, 3, 3_500, "Bound Armor Tempering Charm"),
    (48860, 6, 26_000, "Bound Resplendent Weapon Tempering Charm"),
    (48861, 6, 7_000, "Bound Resplendent Armor Tempering Charm"),
    (46682, 0, 30_000, "Bound Serendipity Stone"),
    (40491, 2, 2_000, "Honorforged Medal"),
    (42168, 0, 500, "Goblet of Honor"),
    (43476, 3, 7_000, "Fireglow Lunagem"),
    (43477, 3, 7_000, "Copperglow Lunagem"),
    (43478, 3, 7_000, "Waveglow Lunagem"),
    (43479, 3, 7_000, "Galeglow Lunagem"),
    (43480, 3, 7_000, "Earthglow Lunagem"),
    (46151, 3, 1_500, "Luna Charm Rank 1"),
    (38568, 0, 2_400, "Mornstone"),
    (32212, 2, 5_000, "Draught of Forgiveness"),
    (4740, 0, 300, "Pinion Portal: Halcyona"),
    (4741, 0, 300, "Pinion Portal: Hasla"),
    (4742, 0, 400, "Pinion Portal: Diamond Shores"),
    (38670, 0, 20_000, "Epherium Windsong Cloak"),
    (38673, 0, 20_000, "Epherium Twintail Cloak"),
    (38676, 0, 20_000, "Epherium Bastion Cloak"),
    (38679, 0, 20_000, "Epherium Arrowflash Cloak"),
    (38682, 0, 20_000, "Epherium Hatchetblade Cloak"),
    (40202, 0, 1_200, "Mirror of Boundaries"),
    (39576, 0, 3_000, "Blood Archeum Crystal"),
    (39055, 6, 240_000, "Pioneer Earrings"),
    (52170, 3, 3_000, "Onyx Grinding Guardian Scroll"),
)

LEGACY_ITEM_IDS = {4740, 4741, 4742}
SCREENSHOT_SHA256 = (
    "694B41B966601B52FEAE1D560638E056DA9F7471FEB87AE2DA41C0511B04DBF6",
    "8B119BBFC0A2C6DEFBB27BA84F7CADCDE34F0901AAA1991BC8B19754092EA000",
    "785FAB26E5A032623647BDBF2CB7177C477876A53728FF01DEFDA7E3A8DF3EB9",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--legacy-compact", type=Path, required=True)
    parser.add_argument("--crosswalk", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--dossiers", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path, nargs=3, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def compatible_row(row: sqlite3.Row, destination_columns: set[str]) -> dict[str, Any]:
    return {key: row[key] for key in row.keys() if key in destination_columns}


def validate_capture(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != len(STOCK):
        raise RuntimeError(f"Expected 31 captured relations, found {len(rows)}")
    if len({row["DeduplicationKey"] for row in rows}) != len(rows):
        raise RuntimeError("Capture contains duplicated relations")
    captured = set()
    for row in rows:
        merchant = row["Merchant"]
        item = row["Item"]
        if row.get("Schema") != CAPTURE_SCHEMA:
            raise RuntimeError("Unexpected capture schema")
        if any(int(merchant[key]) != 0 for key in (
            "NpcObjId", "NpcTemplateId", "DoodadObjId", "DoodadTemplateId", "UnknownId"
        )):
            raise RuntimeError("Capture is not actorless")
        if int(merchant["OpenType"]) != GLOBAL_OPEN_TYPE or merchant["UseAaPoint"]:
            raise RuntimeError("Capture is not the observed openType 2 context")
        if int(item["CurrencyId"]) != HONOR_CURRENCY_ID:
            raise RuntimeError("Capture contains a non-Honor request")
        captured.add((int(item["ItemId"]), int(item["Grade"])))
    expected = {(item_id, grade) for item_id, grade, _, _ in STOCK}
    if captured != expected:
        raise RuntimeError(f"Capture/visual stock mismatch: {sorted(captured ^ expected)}")
    return rows


def validate_crosswalk(path: Path) -> dict[int, str]:
    ids = [row[0] for row in STOCK]
    with sqlite3.connect(path) as connection:
        placeholders = ",".join("?" for _ in ids)
        rows = connection.execute(
            f"SELECT aa8_id,aa10_id,classification FROM row_comparisons "
            f"WHERE table_name='items' AND (aa8_id IN ({placeholders}) OR "
            f"(aa8_id IS NULL AND aa10_id IN ({placeholders})))",
            ids + ids,
        ).fetchall()
    classifications = {
        int(aa8_id if aa8_id is not None else aa10_id): classification
        for aa8_id, aa10_id, classification in rows
    }
    if set(classifications) != set(ids):
        raise RuntimeError("Crosswalk does not account for every observed item")
    for item_id in ids:
        expected = "aa10_only" if item_id in LEGACY_ITEM_IDS else "stable_id_changed_properties"
        if classifications[item_id] != expected:
            raise RuntimeError(
                f"Unexpected crosswalk classification for {item_id}: "
                f"{classifications[item_id]}"
            )
    return classifications


def validate_dossiers(path: Path) -> dict[int, str]:
    hashes = {}
    for item_id, _, _, _ in STOCK:
        dossier_path = path / f"item-{item_id}.json"
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        root = next(
            node for node in dossier["graph"]["nodes"]
            if node["entity_key"] == f"item:{item_id}"
        )
        expected = "tombstone" if item_id in LEGACY_ITEM_IDS else "present"
        if root.get("lifecycle") != expected:
            raise RuntimeError(f"Unexpected dossier lifecycle for {item_id}")
        hashes[item_id] = sha256(dossier_path)
    return hashes


def insert_legacy_portals(
    output: sqlite3.Connection,
    legacy_path: Path,
) -> None:
    destination_columns = {
        row[1] for row in output.execute("PRAGMA table_info(items)")
    }
    with sqlite3.connect(legacy_path) as legacy:
        legacy.row_factory = sqlite3.Row
        rows = list(legacy.execute(
            "SELECT * FROM items WHERE id IN (4740,4741,4742) ORDER BY id"
        ))
    if {int(row["id"]) for row in rows} != LEGACY_ITEM_IDS:
        raise RuntimeError("Legacy compact lacks the three observed portal items")
    expected_skills = {4740: 30944, 4741: 30945, 4742: 30946}
    prices = {item_id: price for item_id, _, price, _ in STOCK}
    for source in rows:
        item_id = int(source["id"])
        if int(source["use_skill_id"]) != expected_skills[item_id]:
            raise RuntimeError(f"Unexpected legacy use skill for portal {item_id}")
        row = compatible_row(source, destination_columns)
        row["honor_price"] = prices[item_id]
        columns = list(row)
        output.execute(
            f"INSERT INTO items ({','.join(columns)}) VALUES "
            f"({','.join('?' for _ in columns)})",
            [row[column] for column in columns],
        )


def build(options: argparse.Namespace) -> dict[str, Any]:
    capture = validate_capture(options.capture)
    classifications = validate_crosswalk(options.crosswalk)
    dossier_hashes = validate_dossiers(options.dossiers)
    screenshot_hashes = tuple(sha256(path) for path in options.screenshots)
    if screenshot_hashes != SCREENSHOT_SHA256:
        raise RuntimeError("Observed Honor-store screenshots changed")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copyfile(options.base_runtime, temporary)
    ids = [row[0] for row in STOCK]
    with sqlite3.connect(temporary) as connection:
        connection.execute("PRAGMA foreign_keys=OFF")
        present = {
            int(row[0])
            for row in connection.execute(
                f"SELECT id FROM items WHERE id IN ({','.join('?' for _ in ids)})",
                ids,
            )
        }
        if present != set(ids) - LEGACY_ITEM_IDS:
            raise RuntimeError("Base runtime item partition changed")
        insert_legacy_portals(connection, options.legacy_compact)

        # All 31 definitions are now safe to instantiate in inventory. This
        # does not claim that every optional use/evolution capability is closed.
        descriptor = {item_id: "generic" for item_id in ids}
        descriptor.update({item_id: "armor" for item_id in (39585, 38670, 38673, 38676, 38679, 38682)})
        descriptor[39055] = "accessory"
        for item_id in ids:
            provenance = (
                "legacy_3_0_corroborated+aa8_live_honor_store+aa10_crosswalk_identity"
                if item_id in LEGACY_ITEM_IDS else
                "client_compact_8+aa8_live_honor_store+aa10_crosswalk_stable_id"
            )
            connection.execute(
                "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
                "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
                "VALUES (?,?, 'complete','',?)",
                (item_id, descriptor[item_id], provenance),
            )

        connection.execute(
            "CREATE TABLE IF NOT EXISTS aaemu_global_merchant_packs ("
            "open_type INTEGER NOT NULL, currency_id INTEGER NOT NULL, "
            "merchant_pack_id INTEGER NOT NULL, provenance TEXT NOT NULL, "
            "PRIMARY KEY(open_type,currency_id), UNIQUE(merchant_pack_id))"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_global_merchant_packs "
            "(open_type,currency_id,merchant_pack_id,provenance) VALUES (?,?,?,?)",
            (GLOBAL_OPEN_TYPE, HONOR_CURRENCY_ID, MERCHANT_PACK_ID,
             "aa8_live_protocol+three_page_visual_capture"),
        )
        connection.execute(
            "DELETE FROM merchant_goods WHERE merchant_pack_id=?",
            (MERCHANT_PACK_ID,),
        )
        for sort_order, (item_id, grade, price, _) in enumerate(STOCK):
            connection.execute(
                "INSERT INTO merchant_goods "
                "(id,merchant_pack_id,item_id,grade_id,currency_id,price,sort_order) "
                "VALUES (?,?,?,?,?,?,?)",
                (92_000_201 + sort_order, MERCHANT_PACK_ID, item_id, grade,
                 HONOR_CURRENCY_ID, price, sort_order),
            )

        missing_skills = connection.execute(
            "SELECT i.id,i.use_skill_id FROM items i LEFT JOIN skills s "
            "ON s.id=i.use_skill_id WHERE i.id IN (%s) AND i.use_skill_id>0 "
            "AND s.id IS NULL" % ",".join("?" for _ in ids),
            ids,
        ).fetchall()
        if missing_skills:
            raise RuntimeError(f"Missing use-skill closure: {missing_skills}")
        connection.commit()
        connection.execute("VACUUM")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("Output quick_check failed")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Output integrity_check failed")

    connection.close()
    os.replace(temporary, options.output)
    manifest = {
        "phase": "AA8-global-honor-store-open-type-2-v1",
        "authority": {
            "open_type": GLOBAL_OPEN_TYPE,
            "currency_id": HONOR_CURRENCY_ID,
            "merchant_pack_id": MERCHANT_PACK_ID,
            "relations": len(STOCK),
            "legacy_rows": len(LEGACY_ITEM_IDS),
        },
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": sha256(options.base_runtime)},
            "legacy_compact": {"path": str(options.legacy_compact), "sha256": sha256(options.legacy_compact)},
            "crosswalk": {"path": str(options.crosswalk), "sha256": sha256(options.crosswalk)},
            "capture": {"path": str(options.capture), "sha256": sha256(options.capture), "rows": len(capture)},
            "screenshots": [
                {"path": str(path), "sha256": digest}
                for path, digest in zip(options.screenshots, screenshot_hashes)
            ],
            "dossiers": dossier_hashes,
        },
        "crosswalk_classifications": classifications,
        "stock": [
            {"item_id": item_id, "grade": grade, "price": price,
             "currency_id": HONOR_CURRENCY_ID, "sort_order": order, "name": name}
            for order, (item_id, grade, price, name) in enumerate(STOCK)
        ],
        "output": {"path": str(options.output), "sha256": sha256(options.output)},
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


if __name__ == "__main__":
    result = build(arguments())
    print(json.dumps(result["output"], indent=2))
