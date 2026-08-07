#!/usr/bin/env python3
"""Build the corroborated Deven weapon merchant reconstruction runtime.

The client merchant packs 119 and 120 contain the same 37 entries exposed by
Deven.  The observed AAEmu runtime pack is 914119 and the matching-version wiki
lists the captured item IDs under NPC 5342.  Ten captured definitions are
positive in the AA8 compact.  For the other 24, this user-authorized builder
imports only the legacy base item/weapon rows whose identities, categories,
visible prices and use behavior are corroborated by the AA8 client, the native
pack and the wiki.  It does not import unrelated historical gameplay rows.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE = ROOT / "reconstruccion_items_8" / "phase_b_explorer_hiram"
B14_BUILDER = PHASE / "build_phase_b14_runtime.py"

CAPTURE_SCHEMA = "AA8_MERCHANT_PURCHASE_RECONSTRUCTION_CAPTURE_V1"
NPC_TEMPLATE_ID = 5342
RUNTIME_PACK_ID = 914119
NATIVE_PACK_IDS = (119, 120)
NATIVE_PACK_OFFSET = 0x8CA020F
ALREADY_COMPLETE = {47868, 47869, 51185}
EXPECTED_NATIVE_COUNT = 37
EXPECTED_CAPTURE_COUNT = 34
EXPECTED_POSITIVE_CAPTURE_COUNT = 10
EXPECTED_TOMBSTONE_COUNT = 24
CLOAKED_LEGACY_IDS = {
    23862, 23866, 23870, 23874, 23878, 23882, 23886, 23890, 23894,
}
HONOR_LEGACY_IDS = {
    18391, 18393, 18395, 18397, 18399, 18401, 18403, 18405,
    18407, 18409, 18411, 18413, 18415, 18417, 18419,
}
WIKI_NPC_URL = "https://wiki.archerage.to/na-en/db/npcs/5342"
OBSERVED_SCREENSHOT_SHA256 = (
    "7EC0693B049D81EE6CF240B227F1DA35B84B63F01A7357FB5FA553484E2B26F3"
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--legacy-compact", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--dossiers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_b14():
    spec = importlib.util.spec_from_file_location("aa8_b14c_base", B14_BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["aa8_b14c_base"] = module
    spec.loader.exec_module(module)
    return module


def load_capture(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != EXPECTED_CAPTURE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CAPTURE_COUNT} captured relations, found {len(rows)}"
        )
    keys = [str(row["DeduplicationKey"]) for row in rows]
    if len(set(keys)) != len(keys):
        raise RuntimeError("Capture contains duplicate reconstruction keys")
    for row in rows:
        if row.get("Schema") != CAPTURE_SCHEMA:
            raise RuntimeError("Unexpected capture schema")
        merchant = row.get("Merchant") or {}
        if int(merchant.get("NpcTemplateId", 0)) != NPC_TEMPLATE_ID:
            raise RuntimeError("Capture contains a different NPC template")
        if int(merchant.get("MerchantPackId", 0)) != RUNTIME_PACK_ID:
            raise RuntimeError("Capture contains a different runtime merchant pack")
    return rows


def decode_native_pack(game11: Path) -> tuple[list[dict[str, Any]], int]:
    b14 = load_b14()
    reader = b14.cached_reader(game11)
    columns = (
        "pack_id kind_id item_id grade_id cost item_point_id "
        "item_point_icon item_point_icon_key"
    ).split()
    layout = "68 68 68 68 68 68 78 78".split()
    rows, end, _ = b14.cached_rows(
        reader,
        NATIVE_PACK_OFFSET,
        columns,
        layout,
    )
    packs = {
        pack_id: [row for row in rows if int(row["pack_id"]) == pack_id]
        for pack_id in NATIVE_PACK_IDS
    }
    signatures = {
        pack_id: [
            (
                int(row["item_id"]),
                int(row["grade_id"]),
                int(row["kind_id"]),
                int(row["cost"]),
                int(row["item_point_id"]),
            )
            for row in values
        ]
        for pack_id, values in packs.items()
    }
    if any(len(values) != EXPECTED_NATIVE_COUNT for values in packs.values()):
        raise RuntimeError("Native weapon merchant pack does not contain 37 rows")
    if signatures[NATIVE_PACK_IDS[0]] != signatures[NATIVE_PACK_IDS[1]]:
        raise RuntimeError("Native merchant packs 119 and 120 no longer agree")
    if any(int(row["kind_id"]) != 0 for row in packs[NATIVE_PACK_IDS[0]]):
        raise RuntimeError("Native weapon merchant pack changed currency kind")
    return packs[NATIVE_PACK_IDS[0]], end


def classify_items(
    client_compact: Path,
    captured_ids: set[int],
    dossiers: Path,
) -> tuple[set[int], set[int], dict[int, dict[str, Any]], dict[int, str]]:
    with sqlite3.connect(client_compact) as connection:
        connection.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in captured_ids)
        positive_rows = {
            int(row["id"]): dict(row)
            for row in connection.execute(
                f"SELECT * FROM items WHERE id IN ({placeholders})",
                sorted(captured_ids),
            )
        }
    positive = set(positive_rows)
    tombstones = captured_ids - positive
    if len(positive) != EXPECTED_POSITIVE_CAPTURE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_POSITIVE_CAPTURE_COUNT} positive AA8 items, found {len(positive)}"
        )
    if len(tombstones) != EXPECTED_TOMBSTONE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_TOMBSTONE_COUNT} tombstones, found {len(tombstones)}"
        )

    dossier_hashes: dict[int, str] = {}
    for item_id in sorted(captured_ids):
        path = dossiers / f"item-{item_id}.json"
        dossier = json.loads(path.read_text(encoding="utf-8"))
        root = next(
            node
            for node in dossier["graph"]["nodes"]
            if node["entity_key"] == f"item:{item_id}"
        )
        expected_lifecycle = "present" if item_id in positive else "tombstone"
        if root.get("lifecycle") != expected_lifecycle:
            raise RuntimeError(
                f"Item {item_id} dossier lifecycle is {root.get('lifecycle')}, "
                f"expected {expected_lifecycle}"
            )
        dossier_hashes[item_id] = sha256(path)
    return positive, tombstones, positive_rows, dossier_hashes


def ensure_merchant_columns(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(merchant_goods)")}
    if "currency_id" not in columns:
        connection.execute(
            "ALTER TABLE merchant_goods ADD COLUMN currency_id INTEGER NOT NULL DEFAULT 0"
        )
    if "price" not in columns:
        connection.execute(
            "ALTER TABLE merchant_goods ADD COLUMN price INTEGER NOT NULL DEFAULT -1"
        )
    if "sort_order" not in columns:
        connection.execute(
            "ALTER TABLE merchant_goods ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
        )


def read_rows(
    connection: sqlite3.Connection,
    table: str,
    key: str,
    identifiers: set[int],
) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in identifiers)
    connection.row_factory = sqlite3.Row
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {table} WHERE {key} IN ({placeholders}) ORDER BY {key}",
            sorted(identifiers),
        )
    ]


def insert_compatible_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    available = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    for row in rows:
        compatible = {key: value for key, value in row.items() if key in available}
        columns = list(compatible)
        connection.execute(
            f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})",
            [compatible[column] for column in columns],
        )


def load_legacy_definitions(
    legacy_compact: Path,
    tombstones: set[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int], set[int]]:
    if tombstones != CLOAKED_LEGACY_IDS | HONOR_LEGACY_IDS:
        raise RuntimeError("Captured legacy partition changed unexpectedly")
    with sqlite3.connect(legacy_compact) as connection:
        items = read_rows(connection, "items", "id", tombstones)
        weapons = read_rows(connection, "item_weapons", "item_id", tombstones)
        if {int(row["id"]) for row in items} != tombstones:
            raise RuntimeError("Legacy compact lacks one or more captured item rows")
        if {int(row["item_id"]) for row in weapons} != HONOR_LEGACY_IDS:
            raise RuntimeError("Legacy compact lacks one or more Honor weapon rows")

        # The old compact prices the cloaked wrappers at one copper.  The AA8
        # client screenshot and matching wiki show 50 gold, and every positive
        # AA8 cloaked wrapper uses 500000 copper.  Keep all other legacy fields
        # but replace this demonstrably stale value.
        for row in items:
            item_id = int(row["id"])
            if item_id in CLOAKED_LEGACY_IDS:
                row["price"] = 500_000
            elif item_id in HONOR_LEGACY_IDS:
                if int(row["price"]) not in {1_000_000, 1_400_000}:
                    raise RuntimeError(f"Unexpected Honor price for item {item_id}")
                if int(row["honor_price"]) not in {2_000, 3_000}:
                    raise RuntimeError(f"Unexpected Honor point price for item {item_id}")

        use_skills = {
            int(row["use_skill_id"])
            for row in items
            if int(row.get("use_skill_id") or 0) > 0
        }
        skill_placeholders = ",".join("?" for _ in use_skills)
        skill_effects = list(
            connection.execute(
                f"SELECT skill_id,effect_id FROM skill_effects "
                f"WHERE skill_id IN ({skill_placeholders})",
                sorted(use_skills),
            )
        )
        effect_ids = {int(row[1]) for row in skill_effects}
        if len(use_skills) != 24 or len(skill_effects) != 41 or len(effect_ids) != 41:
            raise RuntimeError("Legacy use-skill closure changed unexpectedly")
    return items, weapons, use_skills, effect_ids


def build(options: argparse.Namespace) -> dict[str, Any]:
    capture_rows = load_capture(options.capture)
    native_rows, native_end = decode_native_pack(options.game11)
    native_ids = {int(row["item_id"]) for row in native_rows}
    captured_ids = {int(row["Item"]["ItemId"]) for row in capture_rows}
    if native_ids - ALREADY_COMPLETE != captured_ids:
        missing = sorted((native_ids - ALREADY_COMPLETE) - captured_ids)
        extra = sorted(captured_ids - native_ids)
        raise RuntimeError(
            f"Capture/native closure mismatch; missing={missing}, extra={extra}"
        )

    positive, tombstones, positive_rows, dossier_hashes = classify_items(
        options.client_compact,
        captured_ids,
        options.dossiers,
    )
    legacy_items, legacy_weapons, legacy_skills, legacy_effects = (
        load_legacy_definitions(options.legacy_compact, tombstones)
    )

    options.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(options.base_runtime, options.output)
    with sqlite3.connect(options.output) as connection:
        ensure_merchant_columns(connection)
        insert_compatible_rows(connection, "items", legacy_items)
        insert_compatible_rows(connection, "item_weapons", legacy_weapons)
        supported = set(native_ids)
        placeholders = ",".join("?" for _ in supported)
        runtime_items = {
            int(row[0])
            for row in connection.execute(
                f"SELECT id FROM items WHERE id IN ({placeholders})",
                sorted(supported),
            )
        }
        if runtime_items != supported:
            raise RuntimeError(
                f"Base runtime lacks supported item templates: {sorted(supported - runtime_items)}"
            )
        use_skills = {
            int(row[0]): int(row[1] or 0)
            for row in connection.execute(
                f"SELECT id,use_skill_id FROM items WHERE id IN ({placeholders})",
                sorted(supported),
            )
        }
        required_skills = {
            skill_id for skill_id in use_skills.values() if skill_id > 0
        }
        if required_skills:
            skill_placeholders = ",".join("?" for _ in required_skills)
            loaded_skills = {
                int(row[0])
                for row in connection.execute(
                    f"SELECT id FROM skills WHERE id IN ({skill_placeholders})",
                    sorted(required_skills),
                )
            }
            if loaded_skills != required_skills:
                raise RuntimeError(
                    f"Base runtime lacks use skills: {sorted(required_skills - loaded_skills)}"
                )
        if not legacy_skills <= loaded_skills:
            raise RuntimeError("Runtime lacks a user-authorized legacy use skill")
        effect_placeholders = ",".join("?" for _ in legacy_effects)
        loaded_effects = {
            int(row[0])
            for row in connection.execute(
                f"SELECT id FROM effects WHERE id IN ({effect_placeholders})",
                sorted(legacy_effects),
            )
        }
        if loaded_effects != legacy_effects:
            raise RuntimeError("Runtime lacks a legacy use-skill effect")
        expected_weapon_ids = HONOR_LEGACY_IDS | {50802}
        weapon_placeholders = ",".join("?" for _ in expected_weapon_ids)
        loaded_weapon_ids = {
            int(row[0])
            for row in connection.execute(
                f"SELECT item_id FROM item_weapons WHERE item_id IN ({weapon_placeholders})",
                sorted(expected_weapon_ids),
            )
        }
        if loaded_weapon_ids != expected_weapon_ids:
            raise RuntimeError("Runtime weapon descriptors are incomplete")

        existing_supported = ALREADY_COMPLETE | positive
        existing_placeholders = ",".join("?" for _ in existing_supported)
        coverage = {
            int(row[0]): (str(row[1]), str(row[2]), str(row[3]))
            for row in connection.execute(
                f"""
                SELECT item_id,concrete_type,coverage,missing_dependencies
                FROM aaemu_item_definition_coverage
                WHERE item_id IN ({existing_placeholders})
                """,
                sorted(existing_supported),
            )
        }
        if set(coverage) != existing_supported:
            raise RuntimeError("Existing item coverage rows are incomplete")
        for item_id in ALREADY_COMPLETE:
            if coverage[item_id][1] != "complete" or coverage[item_id][2] != "":
                raise RuntimeError(f"Existing box {item_id} is no longer complete")
        for item_id in positive:
            if coverage[item_id][1] not in {"phase_a_candidate", "complete"}:
                raise RuntimeError(f"Positive AA8 item {item_id} has unsafe coverage")

        for item_id in sorted(tombstones):
            concrete_type = "weapon" if item_id in HONOR_LEGACY_IDS else "generic"
            connection.execute(
                """
                INSERT OR REPLACE INTO aaemu_item_definition_coverage (
                    item_id,concrete_type,coverage,missing_dependencies,provenance
                ) VALUES (?,?,'complete','',?)
                """,
                (
                    item_id,
                    concrete_type,
                    "legacy_3_0_user_authorized+AA8_native_pack+"
                    "AA8_observed_shop+wiki_corroborated",
                ),
            )

        connection.execute(
            "DELETE FROM merchant_goods WHERE merchant_pack_id=?",
            (RUNTIME_PACK_ID,),
        )
        for order, row in enumerate(native_rows):
            item_id = int(row["item_id"])
            price = int(
                connection.execute(
                    "SELECT price FROM items WHERE id=?", (item_id,)
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO merchant_goods (
                    id,merchant_pack_id,item_id,grade_id,currency_id,price,sort_order
                ) VALUES (?,?,?,?,0,?,?)
                """,
                (
                    91_500_000 + RUNTIME_PACK_ID * 100 + order,
                    RUNTIME_PACK_ID,
                    item_id,
                    int(row["grade_id"]),
                    price,
                    order,
                ),
            )

        for item_id in sorted(positive):
            connection.execute(
                """
                UPDATE aaemu_item_definition_coverage
                SET coverage='complete', missing_dependencies='',
                    provenance=provenance || '+B14C_native_merchant_purchase'
                WHERE item_id=?
                """,
                (item_id,),
            )
        connection.commit()

        goods = [
            tuple(row)
            for row in connection.execute(
                """
                SELECT item_id,grade_id,currency_id,price,sort_order
                FROM merchant_goods WHERE merchant_pack_id=?
                ORDER BY sort_order
                """,
                (RUNTIME_PACK_ID,),
            )
        ]
        if len(goods) != EXPECTED_NATIVE_COUNT:
            raise RuntimeError("Runtime merchant stock does not contain 37 rows")
        if {row[0] for row in goods} != native_ids:
            raise RuntimeError("Runtime merchant stock IDs differ from native pack")
        if any(row[3] < 0 for row in goods):
            raise RuntimeError("A stock relation lacks a materialized price")
        expected_cloaked_prices = {
            int(row[0]): int(row[1])
            for row in connection.execute(
                f"SELECT id,price FROM items WHERE id IN "
                f"({','.join('?' for _ in CLOAKED_LEGACY_IDS)})",
                sorted(CLOAKED_LEGACY_IDS),
            )
        }
        if set(expected_cloaked_prices.values()) != {500_000}:
            raise RuntimeError("AA8 cloaked shop prices are not 50 gold")
        promoted = {
            int(row[0])
            for row in connection.execute(
                """
                SELECT item_id FROM aaemu_item_definition_coverage
                WHERE coverage='complete' AND missing_dependencies=''
                  AND item_id IN ({})
                """.format(",".join("?" for _ in captured_ids)),
                sorted(captured_ids),
            )
        }
        if promoted != captured_ids:
            raise RuntimeError("Not all captured items were materialized")
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]

    manifest = {
        "phase": "B14c-corroborated-deven-merchant-reconstruction",
        "authority_order": [
            "compact-client-8.0-decrypted.sqlite",
            "game11_native",
            "observed_local_protocol",
            "matching_version_wiki",
            "legacy_3_0_user_authorized_minimal_rows",
        ],
        "historical_3_0_gameplay_rows": 39,
        "sources": {
            "game11": {"path": str(options.game11), "sha256": sha256(options.game11)},
            "client_compact": {
                "path": str(options.client_compact),
                "sha256": sha256(options.client_compact),
            },
            "legacy_compact": {
                "path": str(options.legacy_compact),
                "sha256": sha256(options.legacy_compact),
                "imported_items": 24,
                "imported_item_weapons": 15,
                "imported_total_rows": 39,
            },
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": sha256(options.base_runtime),
            },
            "capture": {
                "path": str(options.capture),
                "sha256": sha256(options.capture),
                "relations": len(capture_rows),
                "distinct_keys": len({row["DeduplicationKey"] for row in capture_rows}),
            },
            "dossier_sha256": {
                str(item_id): value for item_id, value in sorted(dossier_hashes.items())
            },
        },
        "native_merchant": {
            "npc_template_id": NPC_TEMPLATE_ID,
            "runtime_pack_id": RUNTIME_PACK_ID,
            "native_pack_ids": list(NATIVE_PACK_IDS),
            "cached_result_start": NATIVE_PACK_OFFSET,
            "cached_result_end": native_end,
            "rows": EXPECTED_NATIVE_COUNT,
            "item_ids_in_order": [int(row["item_id"]) for row in native_rows],
            "grade_ids_in_order": [int(row["grade_id"]) for row in native_rows],
        },
        "classification": {
            "already_complete_item_ids": sorted(ALREADY_COMPLETE),
            "promoted_positive_item_ids": sorted(positive),
            "materialized_legacy_item_ids": sorted(tombstones),
            "creatable_relations": len(native_ids),
            "blocked_relations": 0,
            "legacy_policy": "explicitly_user_authorized_minimal_closure",
            "cloaked_price_policy": "500000_from_AA8_observed_shop_and_wiki",
            "honor_price_policy": "legacy_values_corroborated_by_AA8_shop_and_wiki",
            "wiki_npc_url": WIKI_NPC_URL,
            "observed_shop_screenshot_sha256": OBSERVED_SCREENSHOT_SHA256,
        },
        "validation": {
            "quick_check": quick_check,
            "integrity_check": integrity_check,
            "merchant_goods": len(goods),
            "promoted_positive": len(positive),
            "materialized_legacy": len(tombstones),
            "blocked_tombstones": 0,
        },
        "output": {"path": str(options.output), "sha256": sha256(options.output)},
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    options = arguments()
    manifest = build(options)
    print(json.dumps(manifest["validation"], sort_keys=True))
    print(manifest["output"]["sha256"])


if __name__ == "__main__":
    main()
