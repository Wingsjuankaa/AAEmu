#!/usr/bin/env python3
"""Build the transversal AA8 Nuia racial-story runtime through chapter 6.

The authoritative quest/component/act graph comes from the frozen Kakao
8.0.3.12 forensic SQLite. Missing static item rows are materialized only when
the AA8 graph proves the exact quest relation, the matching-version wiki cache
confirms the item identity, the compatible legacy row is bounded, and every
referenced AA8 skill/effect dependency is already present. Opaque doodad
product edges remain explicitly observation-required.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
CLIENT_ROOT = Path(r"D:\Proyectos\AAemu\client_kakao")
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-initial-supply-crosswalk-v8.sqlite3"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-nuia-story-chapter6-v1.sqlite3"
DEFAULT_MANIFEST = DOMAIN / "generated" / "native-nuia-story-chapter6-v1-runtime-manifest.json"
DEFAULT_GRAPH = Path(r"E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v1.sqlite3")
DEFAULT_KNOWLEDGE = Path(r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite")
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_LEGACY = (
    ROOT / "assets" / "compact-3.0.3.0" / "3030.14082023" /
    "win10-x64" / "AAEmu.Game" / "Data" / "compact.sqlite3"
)

EXPECTED = {
    "base": "DA7F6026EDE6F9AE2E7B684BDF6BB199078ABF001C50CBD921F8DE50AADA295C",
    "graph": "AF5D48C4AF1C9A266B058FF6D1D0A571C4A5E17C412320360C01F34FEA2056F9",
    "knowledge": "63BBA93992D87B7BA9E2946CAC1C2077849CAC9BF4FA4C07D08424E91B8E568B",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
    "legacy": "9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397",
}

DETAIL_TABLES = {
    "QuestActConAcceptDoodad": "quest_act_con_accept_doodads",
    "QuestActConAcceptNpc": "quest_act_con_accept_npcs",
    "QuestActConAcceptSphere": "quest_act_con_accept_spheres",
    "QuestActConAutoComplete": "quest_act_con_auto_completes",
    "QuestActConReportDoodad": "quest_act_con_report_doodads",
    "QuestActConReportNpc": "quest_act_con_report_npcs",
    "QuestActObjCinema": "quest_act_obj_cinemas",
    "QuestActObjInteraction": "quest_act_obj_interactions",
    "QuestActObjItemGather": "quest_act_obj_item_gathers",
    "QuestActObjItemUse": "quest_act_obj_item_uses",
    "QuestActObjMonsterGroupHunt": "quest_act_obj_monster_group_hunts",
    "QuestActObjMonsterHunt": "quest_act_obj_monster_hunts",
    "QuestActObjSphere": "quest_act_obj_spheres",
    "QuestActObjTalk": "quest_act_obj_talks",
    "QuestActSupplyCopper": "quest_act_supply_coppers",
    "QuestActSupplyExp": "quest_act_supply_exps",
    "QuestActSupplyItem": "quest_act_supply_items",
    "QuestActSupplySelectiveItem": "quest_act_supply_selective_items",
}

MISSING_ITEM_IDS = {
    17584, 17585, 23621, 23828, 24087, 24124, 24125, 24159,
    24160, 24161, 24372, 24462, 24569, 24570, 24575, 24576,
    24969, 24970, 24971, 24972, 25076, 25077, 26023,
}
PROMOTED_NATIVE_ITEM_IDS = {
    34001, 34002, 34003, 34005, 34006, 34007,
    34008, 34009, 47861, 47877, 47955,
}
CLIENT_DOODAD_IDS = {14109, 14114, 14118, 14120, 14121, 14122, 14124}
OBSERVATION_REQUIRED = {
    2492: "doodad-to-item production edge for item 24160",
    4404: "doodad-to-item production edge for item 24575",
}

EFFECT_TABLES = {
    "BuffEffect": "buff_effects",
    "DispelEffect": "dispel_effects",
    "NpcSpawnerSpawnEffect": "npc_spawner_spawn_effects",
    "KillNpcWithoutCorpseEffect": "kill_npc_without_corpse_effects",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')]


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    columns = list(rows[0])
    existing = set(table_columns(connection, table))
    if not set(columns).issubset(existing):
        raise RuntimeError(
            f"{table} schema lacks native columns {sorted(set(columns) - existing)}"
        )
    placeholders = ",".join("?" for _ in columns)
    quoted = ",".join(f'"{column}"' for column in columns)
    connection.executemany(
        f'INSERT OR REPLACE INTO "{table}" ({quoted}) VALUES ({placeholders})',
        [[row[column] for column in columns] for row in rows],
    )


def sanitize_strings(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result: list[dict[str, Any]] = []
    fallbacks: list[dict[str, Any]] = []
    connection.row_factory = sqlite3.Row
    for source in rows:
        row = dict(source)
        previous = connection.execute(
            f'SELECT * FROM "{table}" WHERE id=?', (int(row["id"]),)
        ).fetchone()
        previous_values = dict(previous) if previous else {}
        for column, value in list(row.items()):
            if not (isinstance(value, str) and value.startswith("<ref:") and value.endswith(">")):
                continue
            replacement = previous_values.get(column) or ""
            row[column] = replacement
            fallbacks.append(
                {
                    "table": table,
                    "id": int(row["id"]),
                    "column": column,
                    "native_reference": value,
                    "runtime_value": replacement,
                }
            )
        result.append(row)
    return result, fallbacks


def load_story_graph(path: Path) -> dict[str, Any]:
    connection = ro(path)
    try:
        quests = [dict(row) for row in connection.execute(
            "SELECT * FROM story_quests ORDER BY chapter_idx,quest_idx,quest_id"
        )]
        components = []
        for row in connection.execute(
            "SELECT row_json FROM story_quest_components ORDER BY quest_id,ordinal"
        ):
            components.append(json.loads(row[0]))
        acts: list[dict[str, Any]] = []
        details: dict[str, list[dict[str, Any]]] = {
            detail_type: [] for detail_type in DETAIL_TABLES
        }
        for row in connection.execute(
            "SELECT quest_id,component_id,quest_act_id,act_detail_type,"
            "act_detail_id,detail_row_json FROM story_quest_acts "
            "ORDER BY quest_id,component_id,quest_act_id"
        ):
            detail_type = str(row[3])
            if detail_type not in DETAIL_TABLES:
                raise RuntimeError(f"unsupported native quest act type {detail_type}")
            acts.append(
                {
                    "id": int(row[2]),
                    "act_detail_type": detail_type,
                    "act_detail_id": int(row[4]),
                    "quest_component_id": int(row[1]),
                }
            )
            if row[5] is None:
                raise RuntimeError(f"missing detail row for quest act {row[2]}")
            details[detail_type].append(json.loads(row[5]))
        item_ids = {
            int(row[0]) for row in connection.execute(
                "SELECT DISTINCT item_id FROM story_quest_items"
            )
        }
        return {
            "quests": quests,
            "components": components,
            "acts": acts,
            "details": details,
            "item_ids": item_ids,
        }
    finally:
        connection.close()


def load_doodad_decoder():
    path = DOMAIN / "extract_native_nuian_green_arc.py"
    spec = importlib.util.spec_from_file_location("nuia_doodad_decoder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_client_doodads(game11_path: Path) -> dict[str, list[dict[str, Any]]]:
    decoder = load_doodad_decoder()
    catalog = decoder.load_catalog()
    data = game11_path.read_bytes()
    decoded: dict[str, list[dict[str, Any]]] = {}
    for table, spec in decoder.DOODAD_SPECS.items():
        decoded[table], _ = decoder.decode_rows(
            catalog.CachedResultReader, data, table, spec
        )

    almighties = [
        row for row in decoded["doodad_almighties"]
        if int(row["id"]) in CLIENT_DOODAD_IDS
    ]
    if {int(row["id"]) for row in almighties} != CLIENT_DOODAD_IDS:
        raise RuntimeError("AA8 client-doodad template closure changed")
    if any(int(row["client_doodad"]) != 1 for row in almighties):
        raise RuntimeError("selected logical doodad is not client_doodad=1")

    groups = [
        row for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in CLIENT_DOODAD_IDS
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        row for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    if any(row["actual_func_type"] != "DoodadFuncQuest" for row in funcs):
        raise RuntimeError("selected proxy doodad gained a non-quest function")
    quest_func_ids = {int(row["actual_func_id"]) for row in funcs}
    quest_funcs = [
        row for row in decoded["doodad_func_quests"]
        if int(row["id"]) in quest_func_ids
    ]
    if {int(row["id"]) for row in quest_funcs} != quest_func_ids:
        raise RuntimeError("AA8 client-doodad quest function closure changed")

    return {
        "doodad_almighties": almighties,
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_quests": quest_funcs,
    }


def ensure_wiki_identity(
    knowledge: sqlite3.Connection,
    item_id: int,
) -> dict[str, Any]:
    row = knowledge.execute(
        "SELECT url,status_code,state,comparison_state,response_sha256 "
        "FROM wiki_entities WHERE entity_key=?",
        (f"item:{item_id}",),
    ).fetchone()
    if row is None or tuple(row[1:4]) != (200, "confirmed", "match"):
        raise RuntimeError(f"item {item_id} lacks matching-version wiki corroboration")
    return dict(row)


def actual_effect_table(actual_type: str) -> str:
    if actual_type in EFFECT_TABLES:
        return EFFECT_TABLES[actual_type]
    if not actual_type.endswith("Effect"):
        raise RuntimeError(f"unsupported effect type {actual_type}")
    stem = actual_type[:-6]
    chars: list[str] = []
    for index, char in enumerate(stem):
        if index and char.isupper() and stem[index - 1].islower():
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars) + "_effects"


def validate_skill_closure(
    runtime: sqlite3.Connection,
    knowledge: sqlite3.Connection,
    skill_id: int,
) -> dict[str, Any]:
    native = knowledge.execute(
        "SELECT state,lifecycle,provenance FROM entities WHERE entity_key=?",
        (f"skill:{skill_id}",),
    ).fetchone()
    if native is None or native[0] != "confirmed" or native[1] != "present":
        raise RuntimeError(f"skill {skill_id} lacks positive AA8 identity")
    if runtime.execute("SELECT 1 FROM skills WHERE id=?", (skill_id,)).fetchone() is None:
        raise RuntimeError(f"runtime skill {skill_id} is missing")
    effects = runtime.execute(
        "SELECT se.id,se.effect_id,e.actual_type,e.actual_id "
        "FROM skill_effects se JOIN effects e ON e.id=se.effect_id "
        "WHERE se.skill_id=? ORDER BY se.id",
        (skill_id,),
    ).fetchall()
    concrete: list[dict[str, Any]] = []
    for row in effects:
        table = actual_effect_table(str(row[2]))
        if runtime.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone() is None:
            raise RuntimeError(f"skill {skill_id} effect table {table} is missing")
        if runtime.execute(
            f'SELECT 1 FROM "{table}" WHERE id=?', (int(row[3]),)
        ).fetchone() is None:
            raise RuntimeError(
                f"skill {skill_id} concrete effect {table}[{row[3]}] is missing"
            )
        concrete.append({"table": table, "id": int(row[3])})
    return {
        "skill_id": skill_id,
        "native_provenance": str(native[2]),
        "skill_effects": len(effects),
        "concrete_effects": concrete,
    }


def row_for_runtime_schema(
    runtime: sqlite3.Connection,
    table: str,
    source: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    result: dict[str, Any] = {}
    padded: list[str] = []
    for info in runtime.execute(f'PRAGMA table_info("{table}")'):
        name = str(info[1])
        if name in source:
            result[name] = source[name]
            continue
        padded.append(name)
        result[name] = "" if "TEXT" in str(info[2]).upper() else 0
    return result, padded


def materialize_items(
    runtime: sqlite3.Connection,
    legacy_path: Path,
    knowledge_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    legacy = ro(legacy_path)
    knowledge = ro(knowledge_path)
    materialized: list[dict[str, Any]] = []
    skill_audits: dict[int, dict[str, Any]] = {}
    padded_columns: set[str] = set()
    try:
        for item_id in sorted(MISSING_ITEM_IDS):
            wiki = ensure_wiki_identity(knowledge, item_id)
            source_row = legacy.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
            if source_row is None:
                raise RuntimeError(f"legacy item {item_id} is missing")
            source = dict(source_row)
            if int(source["sellable"]) != 0 or int(source["buff_id"]) != 0 or int(source["craft_id"]) != 0:
                raise RuntimeError(f"legacy item {item_id} exceeds bounded quest-item policy")
            skill_id = int(source["use_skill_id"])
            if skill_id:
                skill_audits.setdefault(
                    skill_id,
                    validate_skill_closure(runtime, knowledge, skill_id),
                )
            row, padded = row_for_runtime_schema(runtime, "items", source)
            padded_columns.update(padded)
            upsert_rows(runtime, "items", [row])

            concrete_type = "generic"
            if item_id == 24087:
                armor = legacy.execute(
                    "SELECT * FROM item_armors WHERE item_id=?", (item_id,)
                ).fetchone()
                if armor is None:
                    raise RuntimeError("Noryette cloak armor descriptor is missing")
                armor_row, armor_padded = row_for_runtime_schema(
                    runtime, "item_armors", dict(armor)
                )
                padded_columns.update(f"item_armors.{column}" for column in armor_padded)
                upsert_rows(runtime, "item_armors", [armor_row])
                concrete_type = "armor"

            provenance = (
                "legacy_3_0_corroborated:AA8_nuia_story_relation+"
                f"wiki_item_identity+dependency_audit:item{item_id}:v1"
            )
            runtime.execute(
                "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
                "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
                "VALUES (?,?,?,?,?)",
                (item_id, concrete_type, "complete", "", provenance),
            )
            materialized.append(
                {
                    "item_id": item_id,
                    "concrete_type": concrete_type,
                    "use_skill_id": skill_id,
                    "wiki_url": str(wiki["url"]),
                    "wiki_response_sha256": str(wiki["response_sha256"]),
                    "provenance": provenance,
                }
            )

        for item_id in sorted(PROMOTED_NATIVE_ITEM_IDS):
            row = runtime.execute(
                "SELECT use_skill_id FROM items WHERE id=?", (item_id,)
            ).fetchone()
            if row is None:
                raise RuntimeError(f"native AA8 item {item_id} disappeared")
            skill_id = int(row[0])
            if skill_id:
                skill_audits.setdefault(
                    skill_id,
                    validate_skill_closure(runtime, knowledge, skill_id),
                )
            runtime.execute(
                "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
                "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
                "VALUES (?,?,?,?,?)",
                (
                    item_id,
                    "generic",
                    "complete",
                    "",
                    "client_compact_8+AA8_nuia_story_native_item_closure:v1",
                ),
            )
    finally:
        legacy.close()
        knowledge.close()
    return materialized, list(skill_audits.values()), sorted(padded_columns)


def validate_runtime(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    doodads: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    quest_ids = {int(row["quest_id"]) for row in story["quests"]}
    component_ids = {int(row["id"]) for row in story["components"]}
    act_ids = {int(row["id"]) for row in story["acts"]}
    if (len(quest_ids), len(component_ids), len(act_ids)) != (55, 222, 344):
        raise RuntimeError("Nuia story graph cardinality changed")

    actual_quests = {
        int(row[0]) for row in connection.execute(
            "SELECT id FROM quest_contexts WHERE id IN "
            f"({','.join('?' for _ in quest_ids)})", sorted(quest_ids)
        )
    }
    if actual_quests != quest_ids:
        raise RuntimeError(f"missing quest contexts {sorted(quest_ids - actual_quests)}")

    for expected in story["components"]:
        row = connection.execute(
            "SELECT * FROM quest_components WHERE id=?", (int(expected["id"]),)
        ).fetchone()
        if row is None:
            raise RuntimeError(f"missing quest component {expected['id']}")
        actual = dict(row)
        mismatch = {key: (value, actual.get(key)) for key, value in expected.items() if actual.get(key) != value}
        if mismatch:
            raise RuntimeError(f"component {expected['id']} mismatch {mismatch}")

    actual_act_ids = {
        int(row[0]) for row in connection.execute(
            "SELECT id FROM quest_acts WHERE id IN "
            f"({','.join('?' for _ in act_ids)})", sorted(act_ids)
        )
    }
    if actual_act_ids != act_ids:
        raise RuntimeError(f"missing quest acts {sorted(act_ids - actual_act_ids)}")

    for detail_type, rows in story["details"].items():
        table = DETAIL_TABLES[detail_type]
        for expected in rows:
            row = connection.execute(
                f'SELECT * FROM "{table}" WHERE id=?', (int(expected["id"]),)
            ).fetchone()
            if row is None:
                raise RuntimeError(f"missing {table}[{expected['id']}]")
            actual = dict(row)
            mismatch = {key: (value, actual.get(key)) for key, value in expected.items() if actual.get(key) != value}
            if mismatch:
                raise RuntimeError(f"{table}[{expected['id']}] mismatch {mismatch}")

    item_ids = sorted(story["item_ids"])
    item_rows = connection.execute(
        "SELECT i.id,c.coverage FROM items i "
        "LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=i.id "
        f"WHERE i.id IN ({','.join('?' for _ in item_ids)}) ORDER BY i.id",
        item_ids,
    ).fetchall()
    if len(item_rows) != 61 or any(row[1] != "complete" for row in item_rows):
        raise RuntimeError("not all 61 Nuia story items are materially complete")

    for doodad_id in CLIENT_DOODAD_IDS:
        row = connection.execute(
            "SELECT client_doodad FROM doodad_almighties WHERE id=?", (doodad_id,)
        ).fetchone()
        if row is None or int(row[0]) != 1:
            raise RuntimeError(f"client doodad {doodad_id} is missing")
    proxy_groups = connection.execute(
        "SELECT doodad_almighty_id,model FROM doodad_func_groups WHERE "
        f"doodad_almighty_id IN ({','.join('?' for _ in CLIENT_DOODAD_IDS)}) "
        "AND model LIKE 'npctype://%' ORDER BY doodad_almighty_id",
        sorted(CLIENT_DOODAD_IDS),
    ).fetchall()
    if {int(row[0]) for row in proxy_groups} != CLIENT_DOODAD_IDS:
        raise RuntimeError("not every client doodad has its native NPC proxy model")

    quest_func_ids = {
        int(row["id"]) for row in doodads["doodad_func_quests"]
    }
    runtime_quest_funcs = {
        int(row[0]) for row in connection.execute(
            "SELECT id FROM doodad_func_quests WHERE id IN "
            f"({','.join('?' for _ in quest_func_ids)})", sorted(quest_func_ids)
        )
    }
    if runtime_quest_funcs != quest_func_ids:
        raise RuntimeError("client-doodad quest function import is incomplete")

    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "quest_contexts": len(actual_quests),
        "quest_components": len(component_ids),
        "quest_acts": len(actual_act_ids),
        "act_types": len(story["details"]),
        "story_items_complete": len(item_rows),
        "client_doodads": len(CLIENT_DOODAD_IDS),
        "client_doodad_proxy_groups": len(proxy_groups),
        "client_doodad_quest_funcs": len(runtime_quest_funcs),
        "prior_item_24967_coverage": connection.execute(
            "SELECT coverage FROM aaemu_item_definition_coverage WHERE item_id=24967"
        ).fetchone()[0],
        "prior_item_21604_coverage": connection.execute(
            "SELECT coverage FROM aaemu_item_definition_coverage WHERE item_id=21604"
        ).fetchone()[0],
        "merchant_goods_914119": connection.execute(
            "SELECT COUNT(*) FROM merchant_goods WHERE merchant_pack_id=914119"
        ).fetchone()[0],
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "quest_contexts": 55,
        "quest_components": 222,
        "quest_acts": 344,
        "act_types": 18,
        "story_items_complete": 61,
        "client_doodads": 7,
        "client_doodad_proxy_groups": 7,
        "client_doodad_quest_funcs": len(quest_func_ids),
        "prior_item_24967_coverage": "complete",
        "prior_item_21604_coverage": "complete",
        "merchant_goods_914119": 37,
    }
    failures = {
        key: {"expected": expected[key], "actual": value}
        for key, value in checks.items() if expected[key] != value
    }
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def build(options: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "base": options.base_runtime,
        "graph": options.graph,
        "knowledge": options.knowledge,
        "game11": options.game11,
        "legacy": options.legacy_compact,
    }
    source_hashes = {name: sha256(path) for name, path in sources.items()}
    for name, expected in EXPECTED.items():
        if source_hashes[name] != expected:
            raise RuntimeError(
                f"{name} source differs: expected {expected}, got {source_hashes[name]}"
            )

    story = load_story_graph(options.graph)
    doodads = extract_client_doodads(options.game11)
    quest_ids = {int(row["quest_id"]) for row in story["quests"]}
    if any(int(row["quest_id"]) not in quest_ids for row in doodads["doodad_func_quests"]):
        raise RuntimeError("client-doodad closure reaches a quest outside the 55-quest scope")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    string_fallbacks: list[dict[str, Any]] = []
    try:
        existing_items = {
            int(row[0]) for row in connection.execute(
                "SELECT id FROM items WHERE id IN "
                f"({','.join('?' for _ in MISSING_ITEM_IDS)})",
                sorted(MISSING_ITEM_IDS),
            )
        }
        if existing_items:
            raise RuntimeError(f"bounded missing-item census changed: {sorted(existing_items)}")

        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")

        component_ids = {int(row["id"]) for row in story["components"]}
        connection.execute(
            "DELETE FROM quest_acts WHERE quest_component_id IN "
            f"({','.join('?' for _ in component_ids)})",
            sorted(component_ids),
        )
        upsert_rows(connection, "quest_components", story["components"])
        upsert_rows(connection, "quest_acts", story["acts"])
        for detail_type, rows in story["details"].items():
            upsert_rows(connection, DETAIL_TABLES[detail_type], rows)

        for table, rows in doodads.items():
            clean, fallbacks = sanitize_strings(connection, table, rows)
            string_fallbacks.extend(fallbacks)
            upsert_rows(connection, table, clean)

        materialized, skill_audits, padded_columns = materialize_items(
            connection, options.legacy_compact, options.knowledge
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_nuia_story_chapter6_materializations (
                item_id INTEGER PRIMARY KEY,
                authority TEXT NOT NULL,
                state TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            )
            """
        )
        for row in materialized:
            connection.execute(
                "INSERT OR REPLACE INTO aaemu_nuia_story_chapter6_materializations "
                "VALUES (?,?,?,?)",
                (
                    row["item_id"],
                    "legacy_3_0_corroborated",
                    "active_bounded",
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                ),
            )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-nuia-story-chapter6-v1",
                "AA8 native quest graph + bounded corroborated item closure",
                EXPECTED["graph"],
                ",".join(map(str, sorted(quest_ids))),
            ),
        )
        checks = validate_runtime(connection, story, doodads)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    os.replace(temporary, options.output)
    document = {
        "format_version": 1,
        "phase": "native-nuia-story-chapter6-v1",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            name: {"path": str(path), "sha256": source_hashes[name]}
            for name, path in sources.items()
        },
        "scope": {
            "quest_ids": sorted(quest_ids),
            "chapters": list(range(7)),
            "quest_contexts": 55,
            "quest_components": 222,
            "quest_acts": 344,
            "act_types": 18,
            "story_item_ids": sorted(story["item_ids"]),
            "legacy_materialized_item_ids": sorted(MISSING_ITEM_IDS),
            "native_promoted_item_ids": sorted(PROMOTED_NATIVE_ITEM_IDS),
            "client_doodad_ids": sorted(CLIENT_DOODAD_IDS),
        },
        "classification": {
            "quest_graph": "client_compact_8+game11_native",
            "client_doodads": "game11_native",
            "materialized_items": "legacy_3_0_corroborated",
            "native_item_promotions": "client_compact_8",
        },
        "materialized_items": materialized,
        "skill_dependency_audits": skill_audits,
        "legacy_schema_padding_columns": padded_columns,
        "unresolved_string_fallbacks": string_fallbacks,
        "observation_required": [
            {"quest_id": quest_id, "blocker": blocker}
            for quest_id, blocker in sorted(OBSERVATION_REQUIRED.items())
        ],
        "safety": {
            "opaque_product_edges_not_invented": True,
            "chapter_boundaries_not_invented": True,
            "outside_category_quests_not_merged": True,
            "runtime_is_cumulative_from_point0_v8": True,
        },
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {"deployed": False},
    }
    options.manifest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--legacy-compact", type=Path, default=DEFAULT_LEGACY)
    options = parser.parse_args()
    print(json.dumps(build(options), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
