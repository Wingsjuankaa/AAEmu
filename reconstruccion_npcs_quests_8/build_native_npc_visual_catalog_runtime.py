#!/usr/bin/env python3
"""Build the bounded native AA8 NPC presentation closure.

The builder projects only native presentation fields onto existing NPC rows,
adds native rows required by the currently configured world spawns, imports
the exact model/custom/equipment descriptor closure, and creates a
presentation-only item allow-list.  It never promotes player item-definition
coverage and never imports historical 3.0 rows as AA8 authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable


AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
PHASE = "native-npc-visual-catalog-v1"
DOMAIN = Path(__file__).resolve().parent
REPO = DOMAIN.parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3"
)
DEFAULT_GRAPH = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics"
    r"\aa8-client-knowledge.sqlite"
)
DEFAULT_ITEM_FORENSICS = Path(
    r"E:\AAEmu-Research\output\aa8-item-forensics"
    r"\aa8-item-forensics.sqlite"
)
DEFAULT_WORLDS = REPO / "AAEmu.Game" / "Data" / "Worlds"
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-npc-visual-v1.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-npc-visual-v1-runtime-manifest.json"
)

EXPECTED_BASE_SHA256 = (
    "11E4D8FD9D28DBA23E25934A5A27CCAD7E4CE4C7B15DF3EEE09C0797622D953B"
)
EXPECTED_GRAPH_SHA256 = (
    "807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC"
)
EXPECTED_ITEM_FORENSICS_SHA256 = (
    "36C2A49F90E1B4CE0C1BD3B83A0D6A0261E6222F8A093BEE5087F55DBA3293B8"
)

NPC_PRESENTATION_FIELDS = (
    "model_id",
    "equip_cloths_id",
    "equip_weapons_id",
    "total_custom_id",
    "char_race_id",
    "scale",
    "opacity",
)
CLOTH_ITEM_FIELDS = (
    "headgear_id",
    "necklace_id",
    "shirt_id",
    "belt_id",
    "pants_id",
    "glove_id",
    "shoes_id",
    "bracelet_id",
    "back_id",
    "cosplay_id",
    "undershirt_id",
    "underpants_id",
    "stabilizer_id",
)
WEAPON_ITEM_FIELDS = (
    "mainhand_id",
    "offhand_id",
    "ranged_id",
    "musical_id",
)
BODY_ASSET_FIELDS = (
    "asset_id",
    "asset_1_id",
    "asset_2_id",
    "asset_3_id",
    "asset_4_id",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_digest(connection: sqlite3.Connection, sql: str) -> str:
    rows = connection.execute(sql).fetchall()
    payload = json.dumps(
        [list(row) for row in rows],
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def native_rows(
    connection: sqlite3.Connection, table: str
) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for native_id, row_json in connection.execute(
        "SELECT native_id,row_json FROM native_rows "
        "WHERE source_table=? AND state='confirmed' ORDER BY native_id",
        (table,),
    ):
        rows[int(native_id)] = json.loads(row_json)
    if not rows:
        raise RuntimeError(f"confirmed native table is empty: {table}")
    return rows


def cached_rows(
    connection: sqlite3.Connection, table: str
) -> list[dict[str, Any]]:
    spec = connection.execute(
        "SELECT q.query_spec_id,r.status,r.row_count "
        "FROM query_specs q JOIN cached_results r USING(query_spec_id) "
        "WHERE q.table_name=? ORDER BY q.query_spec_id",
        (table,),
    ).fetchall()
    if len(spec) != 1 or spec[0][1] not in {
        "confirmed",
        "confirmed_consumer_resolved",
        "confirmed_global_cache_resolved",
    }:
        raise RuntimeError(f"native cached result is not uniquely confirmed: {table} {spec}")
    rows = [
        json.loads(row[0])
        for row in connection.execute(
            "SELECT row_json FROM cached_result_rows "
            "WHERE query_spec_id=? ORDER BY row_index",
            (spec[0][0],),
        )
    ]
    if len(rows) != int(spec[0][2]):
        raise RuntimeError(
            f"native cached row count differs for {table}: "
            f"{len(rows)} != {spec[0][2]}"
        )
    return rows


def configured_spawn_ids(worlds: Path) -> tuple[set[int], int, int]:
    ids: set[int] = set()
    row_count = 0
    files = sorted(worlds.rglob("npc_spawns.json"))
    for path in files:
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
        for row in rows:
            ids.add(int(row["UnitId"]))
            row_count += int(row.get("Count", 1))
    if not files or not ids:
        raise RuntimeError(f"no configured NPC spawns found under {worlds}")
    return ids, len(files), row_count


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    columns = [str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")]
    if not columns:
        raise RuntimeError(f"runtime table is missing: {table}")
    return columns


def normalize_value(table: str, column: str, value: Any) -> Any:
    if table == "total_character_customs" and column == "modifier":
        if isinstance(value, dict):
            return value.get("value")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return value


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: Iterable[dict[str, Any]],
    key: str,
) -> tuple[int, int]:
    columns = table_columns(connection, table)
    inserted = 0
    updated = 0
    for row in sorted(rows, key=lambda value: int(value[key])):
        shared = [column for column in columns if column in row]
        if key not in shared:
            raise RuntimeError(f"{table} row has no key {key}: {row}")
        values = [
            normalize_value(table, column, row[column]) for column in shared
        ]
        exists = connection.execute(
            f"SELECT 1 FROM {table} WHERE {key}=?", (row[key],)
        ).fetchone()
        if exists:
            update_columns = [column for column in shared if column != key]
            connection.execute(
                f"UPDATE {table} SET "
                + ",".join(f"{column}=?" for column in update_columns)
                + f" WHERE {key}=?",
                [
                    normalize_value(table, column, row[column])
                    for column in update_columns
                ]
                + [row[key]],
            )
            updated += 1
        else:
            connection.execute(
                f"INSERT INTO {table} ("
                + ",".join(shared)
                + ") VALUES ("
                + ",".join("?" for _ in shared)
                + ")",
                values,
            )
            inserted += 1
    return inserted, updated


def build_closure(
    runtime: sqlite3.Connection,
    graph: sqlite3.Connection,
    item_forensics: sqlite3.Connection,
    worlds: Path,
) -> dict[str, Any]:
    npcs = native_rows(graph, "npcs")
    models = native_rows(graph, "models")
    actor_models = native_rows(graph, "actor_models")
    customs = native_rows(graph, "total_character_customs")
    characters = native_rows(graph, "characters")
    cloth_packs = native_rows(graph, "equip_pack_cloths")
    weapon_packs = native_rows(graph, "equip_pack_weapons")

    runtime_npc_ids = {
        int(row[0]) for row in runtime.execute("SELECT id FROM npcs")
    }
    spawn_ids, spawn_file_count, configured_spawn_rows = configured_spawn_ids(
        worlds
    )
    native_ids = set(npcs)
    existing_native_ids = runtime_npc_ids & native_ids
    deferred_spawned_native_ids = (spawn_ids - runtime_npc_ids) & native_ids
    # Do not make previously absent actors reachable from historical world
    # files until their AI params and interaction-set closures are decoded.
    target_npc_ids = existing_native_ids
    unresolved_non_native_spawns = sorted(
        (spawn_ids - runtime_npc_ids) - native_ids
    )

    model_ids = {int(npcs[npc_id]["model_id"]) for npc_id in target_npc_ids}
    missing_models = sorted(model_ids - set(models))
    if missing_models:
        raise RuntimeError(f"target NPC model rows are missing: {missing_models}")
    actor_model_ids = {
        int(models[model_id]["sub_id"])
        for model_id in model_ids
        if models[model_id]["sub_type"] == "ActorModel"
    }
    missing_actor_models = sorted(actor_model_ids - set(actor_models))
    if missing_actor_models:
        raise RuntimeError(
            f"target actor-model rows are missing: {missing_actor_models}"
        )

    custom_ids = {
        int(npcs[npc_id]["total_custom_id"])
        for npc_id in target_npc_ids
        if int(npcs[npc_id]["total_custom_id"])
    }
    missing_customs = sorted(custom_ids - set(customs))
    if missing_customs:
        raise RuntimeError(f"target total customs are missing: {missing_customs}")

    cloth_pack_ids = {
        int(npcs[npc_id]["equip_cloths_id"])
        for npc_id in target_npc_ids
        if int(npcs[npc_id]["equip_cloths_id"])
    }
    weapon_pack_ids = {
        int(npcs[npc_id]["equip_weapons_id"])
        for npc_id in target_npc_ids
        if int(npcs[npc_id]["equip_weapons_id"])
    }
    if cloth_pack_ids - set(cloth_packs):
        raise RuntimeError(
            f"target cloth packs are missing: {sorted(cloth_pack_ids - set(cloth_packs))}"
        )
    if weapon_pack_ids - set(weapon_packs):
        raise RuntimeError(
            f"target weapon packs are missing: {sorted(weapon_pack_ids - set(weapon_packs))}"
        )

    armor_item_ids: set[int] = set()
    weapon_item_ids: set[int] = set()
    slot_references: dict[str, set[int]] = {}
    for pack_id in sorted(cloth_pack_ids):
        pack = cloth_packs[pack_id]
        for field in CLOTH_ITEM_FIELDS:
            item_id = int(pack[field])
            if item_id:
                armor_item_ids.add(item_id)
                slot_references.setdefault(field, set()).add(item_id)
    for pack_id in sorted(weapon_pack_ids):
        pack = weapon_packs[pack_id]
        for field in WEAPON_ITEM_FIELDS:
            item_id = int(pack[field])
            if item_id:
                weapon_item_ids.add(item_id)
                slot_references.setdefault(field, set()).add(item_id)

    all_armors = {
        int(row["item_id"]): row
        for row in cached_rows(item_forensics, "item_armors")
    }
    all_weapons = {
        int(row["item_id"]): row
        for row in cached_rows(item_forensics, "item_weapons")
    }
    all_body_parts = {
        int(row["item_id"]): row
        for row in cached_rows(item_forensics, "item_body_parts")
        if int(row["item_id"])
    }
    if armor_item_ids - set(all_armors):
        raise RuntimeError(
            f"native NPC armor descriptors are missing: "
            f"{sorted(armor_item_ids - set(all_armors))}"
        )
    if weapon_item_ids - set(all_weapons):
        raise RuntimeError(
            f"native NPC weapon descriptors are missing: "
            f"{sorted(weapon_item_ids - set(all_weapons))}"
        )

    explicit_body_ids = {
        int(row[field])
        for row in customs.values()
        for field in ("hair_id", "horn_id")
        if int(row[field])
    }
    explicit_body_ids.update(
        int(row["face_item_id"])
        for row in characters.values()
        if int(row["face_item_id"])
    )
    if explicit_body_ids - set(all_body_parts):
        raise RuntimeError(
            f"native NPC body-part descriptors are missing: "
            f"{sorted(explicit_body_ids - set(all_body_parts))}"
        )

    armor_rows = [all_armors[item_id] for item_id in sorted(armor_item_ids)]
    weapon_rows = [all_weapons[item_id] for item_id in sorted(weapon_item_ids)]
    body_rows = list(all_body_parts.values())

    armor_asset_family_ids = {
        int(row[field])
        for row in armor_rows
        for field in ("asset_id", "asset2_id")
        if int(row[field])
    }
    all_armor_assets = cached_rows(item_forensics, "item_armor_assets")
    armor_asset_rows = [
        row
        for row in all_armor_assets
        if int(row["armor_asset_id"]) in armor_asset_family_ids
    ]
    item_asset_ids = {
        int(row["asset_id"]) for row in armor_asset_rows if int(row["asset_id"])
    }
    item_asset_ids.update(
        int(row["asset_id"]) for row in weapon_rows if int(row["asset_id"])
    )
    item_asset_ids.update(
        int(row[field])
        for row in body_rows
        for field in BODY_ASSET_FIELDS
        if int(row[field])
    )
    all_item_assets = {
        int(row["id"]): row
        for row in cached_rows(item_forensics, "item_assets")
    }
    item_asset_rows = [
        all_item_assets[item_id]
        for item_id in sorted(item_asset_ids & set(all_item_assets))
    ]

    armor_mapping_ids = {
        int(row["armor_asset_id"]) for row in armor_asset_rows
    }
    whitelist: list[dict[str, Any]] = []
    for item_id in sorted(armor_item_ids):
        row = all_armors[item_id]
        mapped = any(
            int(row[field]) in armor_mapping_ids
            for field in ("asset_id", "asset2_id")
            if int(row[field])
        )
        whitelist.append(
            {
                "item_id": item_id,
                "visual_kind": "armor",
                "descriptor_id": int(row["id"]),
                "asset_state": "resolved" if mapped else "native_pathless",
                "source_table": "item_armors",
            }
        )
    for item_id in sorted(weapon_item_ids):
        row = all_weapons[item_id]
        asset_id = int(row["asset_id"])
        resolved = asset_id in all_item_assets and bool(
            all_item_assets[asset_id].get("path")
        )
        whitelist.append(
            {
                "item_id": item_id,
                "visual_kind": "weapon",
                "descriptor_id": int(row["id"]),
                "asset_state": "resolved" if resolved else "native_pathless",
                "source_table": "item_weapons",
            }
        )
    for item_id in sorted(all_body_parts):
        row = all_body_parts[item_id]
        resolved = any(
            int(row[field]) in all_item_assets
            and bool(all_item_assets[int(row[field])].get("path"))
            for field in BODY_ASSET_FIELDS
            if int(row[field])
        )
        whitelist.append(
            {
                "item_id": item_id,
                "visual_kind": "body_part",
                "descriptor_id": item_id,
                "asset_state": "resolved" if resolved else "native_pathless",
                "source_table": "item_body_parts",
            }
        )
    whitelist_by_id = {int(row["item_id"]): row for row in whitelist}
    if len(whitelist_by_id) != len(whitelist):
        raise RuntimeError("NPC visual item kinds overlap unexpectedly")
    if 0 in whitelist_by_id:
        raise RuntimeError("NPC visual catalogue contains sentinel item id 0")

    return {
        "npcs": npcs,
        "models": [models[value] for value in sorted(model_ids)],
        "actor_models": [
            actor_models[value] for value in sorted(actor_model_ids)
        ],
        "customs": list(customs.values()),
        "cloth_packs": [
            cloth_packs[value] for value in sorted(cloth_pack_ids)
        ],
        "weapon_packs": [
            weapon_packs[value] for value in sorted(weapon_pack_ids)
        ],
        "armor_rows": armor_rows,
        "weapon_rows": weapon_rows,
        "body_rows": body_rows,
        "armor_asset_rows": armor_asset_rows,
        "item_asset_rows": item_asset_rows,
        "whitelist": list(whitelist_by_id.values()),
        "target_npc_ids": target_npc_ids,
        "existing_native_ids": existing_native_ids,
        "deferred_spawned_native_ids": deferred_spawned_native_ids,
        "runtime_npc_ids": runtime_npc_ids,
        "spawn_ids": spawn_ids,
        "negative_evidence": {
            "configured_spawn_templates_absent_from_runtime_and_native_catalog": (
                unresolved_non_native_spawns
            ),
            "configured_spawn_templates_native_but_runtime_deferred": sorted(
                deferred_spawned_native_ids
            ),
            "statement": (
                "Legacy ids without a positive Kakao row were not synthesized. "
                "Positive native ids absent from runtime were also kept "
                "disabled because their AI-param and interaction-set runtime "
                "closures are not yet decoded."
            ),
        },
        "summary": {
            "spawn_files": spawn_file_count,
            "configured_spawn_rows": configured_spawn_rows,
            "configured_spawn_templates": len(spawn_ids),
            "target_npcs": len(target_npc_ids),
            "existing_native_npcs": len(existing_native_ids),
            "deferred_spawned_native_npcs": len(deferred_spawned_native_ids),
            "target_models": len(model_ids),
            "target_actor_models": len(actor_model_ids),
            "total_character_customs": len(customs),
            "cloth_packs": len(cloth_pack_ids),
            "weapon_packs": len(weapon_pack_ids),
            "armor_items": len(armor_item_ids),
            "weapon_items": len(weapon_item_ids),
            "body_parts": len(all_body_parts),
            "visual_items": len(whitelist_by_id),
            "armor_asset_rows": len(armor_asset_rows),
            "item_asset_rows": len(item_asset_rows),
            "slot_distinct_item_counts": {
                key: len(value) for key, value in sorted(slot_references.items())
            },
        },
    }


def mutate_runtime(
    connection: sqlite3.Connection, closure: dict[str, Any], source_hashes: dict[str, str]
) -> dict[str, Any]:
    items_digest_before = canonical_digest(
        connection, "SELECT * FROM items ORDER BY id"
    )
    coverage_digest_before = canonical_digest(
        connection,
        "SELECT * FROM aaemu_item_definition_coverage ORDER BY item_id",
    )
    npc_columns = table_columns(connection, "npcs")
    gameplay_columns = [
        column
        for column in npc_columns
        if column not in {"id", *NPC_PRESENTATION_FIELDS}
    ]
    gameplay_digest_before = canonical_digest(
        connection,
        "SELECT id,"
        + ",".join(gameplay_columns)
        + " FROM npcs ORDER BY id",
    )

    connection.execute("BEGIN IMMEDIATE")
    native_npcs: dict[int, dict[str, Any]] = closure["npcs"]
    for npc_id in sorted(closure["existing_native_ids"]):
        row = native_npcs[npc_id]
        connection.execute(
            "UPDATE npcs SET "
            + ",".join(f"{field}=?" for field in NPC_PRESENTATION_FIELDS)
            + " WHERE id=?",
            [row[field] for field in NPC_PRESENTATION_FIELDS] + [npc_id],
        )
    mutations = {
        "npcs": {
            "presentation_updated": len(closure["existing_native_ids"]),
            "spawned_native_inserted": 0,
            "spawned_native_deferred": len(
                closure["deferred_spawned_native_ids"]
            ),
        }
    }
    for table, rows, key in (
        ("models", closure["models"], "id"),
        ("actor_models", closure["actor_models"], "id"),
        ("total_character_customs", closure["customs"], "id"),
        ("equip_pack_cloths", closure["cloth_packs"], "id"),
        ("equip_pack_weapons", closure["weapon_packs"], "id"),
        ("item_armors", closure["armor_rows"], "id"),
        ("item_weapons", closure["weapon_rows"], "id"),
        ("item_body_parts", closure["body_rows"], "item_id"),
        ("item_armor_assets", closure["armor_asset_rows"], "id"),
        ("item_assets", closure["item_asset_rows"], "id"),
    ):
        inserted, updated = upsert_rows(connection, table, rows, key)
        mutations[table] = {"inserted": inserted, "updated": updated}

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS aaemu_npc_visual_items (
            item_id INTEGER PRIMARY KEY,
            visual_kind TEXT NOT NULL,
            descriptor_id INTEGER NOT NULL,
            asset_state TEXT NOT NULL,
            source_table TEXT NOT NULL,
            provenance TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS aaemu_native_npc_visual_npcs (
            npc_id INTEGER PRIMARY KEY,
            source_scope TEXT NOT NULL,
            provenance TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS aaemu_native_npc_visual_reconstruction (
            phase TEXT PRIMARY KEY,
            authority TEXT NOT NULL,
            base_runtime_sha256 TEXT NOT NULL,
            graph_sha256 TEXT NOT NULL,
            item_forensics_sha256 TEXT NOT NULL,
            scope_json TEXT NOT NULL
        );
        DELETE FROM aaemu_npc_visual_items;
        DELETE FROM aaemu_native_npc_visual_npcs;
        """
    )
    connection.executemany(
        "INSERT INTO aaemu_npc_visual_items "
        "(item_id,visual_kind,descriptor_id,asset_state,source_table,provenance) "
        "VALUES (?,?,?,?,?,?)",
        [
            (
                row["item_id"],
                row["visual_kind"],
                row["descriptor_id"],
                row["asset_state"],
                row["source_table"],
                "game11_native+x2game_confirmed+npc_equip_pack_relation",
            )
            for row in closure["whitelist"]
        ],
    )
    connection.executemany(
        "INSERT INTO aaemu_native_npc_visual_npcs "
        "(npc_id,source_scope,provenance) VALUES (?,?,?)",
        [
            (
                npc_id,
                (
                    "existing_runtime_native_projection"
                ),
                "game11_native",
            )
            for npc_id in sorted(closure["target_npc_ids"])
        ],
    )
    connection.execute(
        "INSERT OR REPLACE INTO aaemu_native_npc_visual_reconstruction "
        "(phase,authority,base_runtime_sha256,graph_sha256,"
        "item_forensics_sha256,scope_json) VALUES (?,?,?,?,?,?)",
        (
            PHASE,
            AUTHORITY,
            source_hashes["base_runtime"],
            source_hashes["graph"],
            source_hashes["item_forensics"],
            json.dumps(
                closure["summary"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ),
    )
    connection.commit()

    items_digest_after = canonical_digest(
        connection, "SELECT * FROM items ORDER BY id"
    )
    coverage_digest_after = canonical_digest(
        connection,
        "SELECT * FROM aaemu_item_definition_coverage ORDER BY item_id",
    )
    gameplay_digest_after = canonical_digest(
        connection,
        "SELECT id,"
        + ",".join(gameplay_columns)
        + " FROM npcs WHERE id IN (SELECT npc_id FROM "
        "aaemu_native_npc_visual_npcs WHERE "
        "source_scope='existing_runtime_native_projection') ORDER BY id",
    )
    gameplay_digest_before_existing = canonical_digest(
        connection,
        "SELECT id,"
        + ",".join(gameplay_columns)
        + " FROM npcs WHERE id IN (SELECT npc_id FROM "
        "aaemu_native_npc_visual_npcs WHERE "
        "source_scope='existing_runtime_native_projection') ORDER BY id",
    )
    # The full pre-mutation digest includes runtime-only rows and is retained
    # for the manifest.  The scoped equality is also checked explicitly below
    # from the immutable source database by validate_output.
    return {
        "mutations": mutations,
        "items_digest_before": items_digest_before,
        "items_digest_after": items_digest_after,
        "item_definition_coverage_digest_before": coverage_digest_before,
        "item_definition_coverage_digest_after": coverage_digest_after,
        "npc_gameplay_digest_before_all_runtime_rows": gameplay_digest_before,
        "npc_gameplay_digest_after_existing_projection": gameplay_digest_after,
        "npc_gameplay_digest_scoped_recheck": gameplay_digest_before_existing,
    }


def validate_output(
    output: sqlite3.Connection,
    base: sqlite3.Connection,
    closure: dict[str, Any],
    mutation: dict[str, Any],
) -> dict[str, Any]:
    if mutation["items_digest_before"] != mutation["items_digest_after"]:
        raise RuntimeError("the player items catalogue changed")
    if (
        mutation["item_definition_coverage_digest_before"]
        != mutation["item_definition_coverage_digest_after"]
    ):
        raise RuntimeError("player item-definition coverage changed")

    base_columns = table_columns(base, "npcs")
    gameplay_columns = [
        column
        for column in base_columns
        if column not in {"id", *NPC_PRESENTATION_FIELDS}
    ]
    ids = sorted(closure["existing_native_ids"])
    for npc_id in ids:
        base_row = base.execute(
            "SELECT " + ",".join(gameplay_columns) + " FROM npcs WHERE id=?",
            (npc_id,),
        ).fetchone()
        output_row = output.execute(
            "SELECT " + ",".join(gameplay_columns) + " FROM npcs WHERE id=?",
            (npc_id,),
        ).fetchone()
        if base_row != output_row:
            raise RuntimeError(
                f"non-presentation NPC fields changed for existing NPC {npc_id}"
            )

    native_npcs: dict[int, dict[str, Any]] = closure["npcs"]
    for npc_id in sorted(closure["target_npc_ids"]):
        output_row = output.execute(
            "SELECT " + ",".join(NPC_PRESENTATION_FIELDS)
            + " FROM npcs WHERE id=?",
            (npc_id,),
        ).fetchone()
        expected = tuple(
            native_npcs[npc_id][field] for field in NPC_PRESENTATION_FIELDS
        )
        if output_row != expected:
            raise RuntimeError(
                f"native presentation projection differs for NPC {npc_id}: "
                f"{output_row} != {expected}"
            )

    audits = {
        "target_npc_missing_model": """
            SELECT COUNT(*) FROM aaemu_native_npc_visual_npcs v
            JOIN npcs n ON n.id=v.npc_id
            LEFT JOIN models m ON m.id=n.model_id
            WHERE n.model_id<>0 AND m.id IS NULL
        """,
        "target_npc_missing_total_custom": """
            SELECT COUNT(*) FROM aaemu_native_npc_visual_npcs v
            JOIN npcs n ON n.id=v.npc_id
            LEFT JOIN total_character_customs c ON c.id=n.total_custom_id
            WHERE n.total_custom_id<>0 AND c.id IS NULL
        """,
        "target_npc_missing_cloth_pack": """
            SELECT COUNT(*) FROM aaemu_native_npc_visual_npcs v
            JOIN npcs n ON n.id=v.npc_id
            LEFT JOIN equip_pack_cloths p ON p.id=n.equip_cloths_id
            WHERE n.equip_cloths_id<>0 AND p.id IS NULL
        """,
        "target_npc_missing_weapon_pack": """
            SELECT COUNT(*) FROM aaemu_native_npc_visual_npcs v
            JOIN npcs n ON n.id=v.npc_id
            LEFT JOIN equip_pack_weapons p ON p.id=n.equip_weapons_id
            WHERE n.equip_weapons_id<>0 AND p.id IS NULL
        """,
        "target_model_missing_actor_model": """
            SELECT COUNT(*) FROM aaemu_native_npc_visual_npcs v
            JOIN npcs n ON n.id=v.npc_id
            JOIN models m ON m.id=n.model_id
            LEFT JOIN actor_models a ON a.id=m.sub_id
            WHERE m.sub_type='ActorModel' AND a.id IS NULL
        """,
        "visual_item_missing_descriptor": """
            SELECT COUNT(*) FROM aaemu_npc_visual_items v
            LEFT JOIN item_armors a
              ON v.visual_kind='armor' AND a.item_id=v.item_id
            LEFT JOIN item_weapons w
              ON v.visual_kind='weapon' AND w.item_id=v.item_id
            LEFT JOIN item_body_parts b
              ON v.visual_kind='body_part' AND b.item_id=v.item_id
            WHERE a.item_id IS NULL AND w.item_id IS NULL AND b.item_id IS NULL
        """,
    }
    audit_results = {
        name: int(output.execute(sql).fetchone()[0])
        for name, sql in audits.items()
    }
    nonzero = {key: value for key, value in audit_results.items() if value}
    if nonzero:
        raise RuntimeError(f"runtime NPC visual orphan audit failed: {nonzero}")

    quick = output.execute("PRAGMA quick_check").fetchone()[0]
    integrity = output.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(
            f"SQLite validation failed: quick={quick}, integrity={integrity}"
        )
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "orphan_audits": audit_results,
        "items_catalog_unchanged": True,
        "item_definition_coverage_unchanged": True,
        "existing_npc_non_presentation_fields_unchanged": True,
        "native_presentation_projection_exact": True,
        "runtime_counts": {
            table: int(output.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "npcs",
                "models",
                "actor_models",
                "total_character_customs",
                "item_armors",
                "item_weapons",
                "item_body_parts",
                "aaemu_npc_visual_items",
                "aaemu_native_npc_visual_npcs",
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument(
        "--item-forensics", type=Path, default=DEFAULT_ITEM_FORENSICS
    )
    parser.add_argument("--worlds", type=Path, default=DEFAULT_WORLDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

    expected = {
        "base_runtime": (options.base_runtime, EXPECTED_BASE_SHA256),
        "graph": (options.graph, EXPECTED_GRAPH_SHA256),
        "item_forensics": (
            options.item_forensics,
            EXPECTED_ITEM_FORENSICS_SHA256,
        ),
    }
    source_hashes: dict[str, str] = {}
    for name, (path, expected_hash) in expected.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected_hash:
            raise RuntimeError(
                f"{name} differs from the audited input: {actual} != {expected_hash}"
            )
        source_hashes[name] = actual

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    output = sqlite3.connect(temporary)
    base = sqlite3.connect(
        f"file:{options.base_runtime.resolve().as_posix()}?mode=ro", uri=True
    )
    graph = sqlite3.connect(
        f"file:{options.graph.resolve().as_posix()}?mode=ro", uri=True
    )
    item_forensics = sqlite3.connect(
        f"file:{options.item_forensics.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        client_build = graph.execute(
            "SELECT value FROM metadata WHERE key='client_build'"
        ).fetchone()
        if not client_build or client_build[0] != AUTHORITY.replace(
            "ArcheAge ", ""
        ):
            raise RuntimeError(f"unexpected forensic client build: {client_build}")
        closure = build_closure(output, graph, item_forensics, options.worlds)
        mutation = mutate_runtime(output, closure, source_hashes)
        validation = validate_output(output, base, closure, mutation)
    except Exception:
        output.rollback()
        output.close()
        base.close()
        graph.close()
        item_forensics.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        output.close()
        base.close()
        graph.close()
        item_forensics.close()

    os.replace(temporary, options.output)
    document = {
        "format_version": 1,
        "phase": PHASE,
        "authority": AUTHORITY,
        "sources": {
            name: {"path": str(path), "sha256": source_hashes[name]}
            for name, (path, _) in expected.items()
        },
        "dossier": {
            "root": "npc:3597",
            "profile": "generic",
            "json_sha256": (
                "ECCC638F6DC1042F3ACD764729B8B1B4D0B326DB04F5A0DF38DB8AFB4285E319"
            ),
            "forensic_readiness": "profile_complete",
            "reconstruction_readiness": "runtime_audit_required",
        },
        "scope": closure["summary"],
        "negative_evidence": closure["negative_evidence"],
        "mutation": mutation,
        "validation": validation,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {
            "deployed": False,
            "service": "game",
            "reason": "Candidate built and validated; deployment pending.",
        },
    }
    options.manifest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {options.output} ({options.output.stat().st_size} bytes, "
        f"sha256={document['output']['sha256']})"
    )
    print(json.dumps(closure["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
