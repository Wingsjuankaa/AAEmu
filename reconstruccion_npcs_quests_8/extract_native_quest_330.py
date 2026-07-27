#!/usr/bin/env python3
"""Extract a deployable, narrowly scoped AA8-native bundle for quest 330."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_X2GAME = Path(r"E:\AAEmu-Research\input\x2game.dll")
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-character-creation-v2.sqlite3"
)
DEFAULT_SPAWNS = ROOT / "AAEmu.Game" / "Data" / "Worlds" / "main_world" / "npc_spawns.json"
DEFAULT_GHIDRA = Path(r"E:\AAEmu-Research\output\ghidra-static")
DEFAULT_OUTPUT = DOMAIN / "generated"

QUEST_ID = 330
NEXT_QUEST_ID = 2531
QUEST_COMPONENT_IDS = {1520, 1521, 1522}
QUEST_ACT_IDS = {2438, 9874, 64092, 65227, 65228, 65229, 65230, 65619}
REWARD_ITEM_IDS = {23633, 51185, 18791, 47868, 47869}
APPEARANCE_ITEM_IDS = {16066, 25269, 24133, 2722, 18490, 25017, 19838}
APPEARANCE_ARMOR_ITEM_IDS = {16066, 2722, 18490, 25017}
APPEARANCE_BODY_PART_ITEM_IDS = {25269, 24133, 19838}
RUNTIME_COMPLETE_ITEM_IDS = (
    {23633, 48541}
    | APPEARANCE_ITEM_IDS
)


CONCRETE_SPECS: dict[str, dict[str, Any]] = {
    "quest_supplies": {
        "columns": "id copper exp level".split(),
        "layout": "68 68 68 68".split(),
        "start": 0x766324B,
        "done": 0x76635F2,
        "rows": 55,
        "loader": "x2game.dll FUN_399f47d0",
        "sql_address": "0x39DF0200",
        "selected_ids": {1},
    },
    "quest_act_con_accept_npcs": {
        "columns": "id npc_id quest_act_obj_alias_id use_alias".split(),
        "layout": "68 68 68 38".split(),
        "start": 0x6D3DC71,
        "done": 0x6D4B379,
        "rows": 3932,
        "loader": "x2game.dll FUN_399e5480",
        "sql_address": "0x39DEA8F0",
        "selected_ids": {1250, 2097},
    },
    "quest_act_con_report_npcs": {
        "columns": "id npc_id quest_act_obj_alias_id use_alias".split(),
        "layout": "68 68 68 38".split(),
        "start": 0x6D57198,
        "done": 0x6D6731E,
        "rows": 4709,
        "loader": "x2game.dll FUN_399e71e0",
        "sql_address": "0x39DEB4D0",
        "selected_ids": {329},
    },
    "quest_act_supply_items": {
        "columns": (
            "id cleanup count destroy_when_drop drop_when_destroy grade_id "
            "item_id show_action_bar try_equip"
        ).split(),
        "layout": "68 38 68 38 38 68 68 38 38".split(),
        "start": 0x6D6B51B,
        "done": 0x6D89A23,
        "rows": 5644,
        "loader": "x2game.dll FUN_399e7d20",
        "sql_address": "0x39DEB950",
        "selected_ids": {8675, 8676, 8869},
    },
    "quest_act_supply_exps": {
        "columns": "id exp".split(),
        "layout": "68 68".split(),
        "start": 0x6D89D77,
        "done": 0x6D93098,
        "rows": 4185,
        "loader": "x2game.dll FUN_399e8540",
        "sql_address": "0x39DEBC50",
        "selected_ids": {3922},
    },
    "quest_act_supply_selective_items": {
        "columns": "id count grade_id item_id".split(),
        "layout": "68 68 68 68".split(),
        "start": 0x6D9BD7A,
        "done": 0x6D9E222,
        "rows": 552,
        "loader": "x2game.dll FUN_399e8940",
        "sql_address": "0x39DEBDF0",
        "selected_ids": {3646, 3647},
    },
}

UNIT_REQ_SPEC = {
    "columns": (
        "owner_type owner_id display_msg kind_id value1 value2 value3"
    ).split(),
    "layout": "78 68 38 68 68 68 68".split(),
    "start": 0x7CA0C9,
    "done": 0x87EC3C,
    "rows": 27407,
    "first_string_reference": 69872,
    "loader": "x2game.dll FUN_3997a330",
    "sql_address": "0x39DDEC80",
}


GHIDRA_EVIDENCE = {
    "quest_supplies": (
        "quest330-quest-supplies-loader.c",
        "FUN_399f47d0 @ 399f47d0",
    ),
    "quest_act_con_accept_npcs": (
        "quest330-accept-loader.c",
        "FUN_399e5480 @ 399e5480",
    ),
    "quest_act_con_report_npcs": (
        "quest330-quest-act-con-report-npcs-loader.c",
        "FUN_399e71e0 @ 399e71e0",
    ),
    "quest_act_supply_items": (
        "quest330-quest-act-supply-items-loader.c",
        "FUN_399e7d20 @ 399e7d20",
    ),
    "quest_act_supply_exps": (
        "quest330-quest-act-supply-exps-loader.c",
        "FUN_399e8540 @ 399e8540",
    ),
    "quest_act_supply_selective_items": (
        "phaseb11-string-selective-item.c",
        "FUN_399e8940 @ 399e8940",
    ),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_rows_sha256(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest().upper()


def decode_table(
    reader_type,
    data: bytes,
    name: str,
    spec: dict[str, Any],
    selected_ids: set[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns = list(spec["columns"])
    layout = list(spec["layout"])
    if len(columns) != len(layout):
        raise RuntimeError(f"{name}: column/layout length mismatch")
    reader = reader_type(data, spec.get("first_string_reference"))
    cursor = int(spec["start"])
    rows: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    ids: list[int] = []
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, layout)
        row = dict(zip(columns, values))
        row_id = int(row["id"])
        rows.append(row)
        ids.append(row_id)
        if row_id in selected_ids:
            selected.append(row)
    if cursor != int(spec["done"]) or data[cursor] != 101:
        raise RuntimeError(
            f"{name}: SQLITE_DONE mismatch, expected 0x{spec['done']:X}, "
            f"found 0x{cursor:X}"
        )
    if len(rows) != int(spec["rows"]):
        raise RuntimeError(f"{name}: expected {spec['rows']} rows, found {len(rows)}")
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise RuntimeError(f"{name}: native IDs are not sorted and unique")
    found = {int(row["id"]) for row in selected}
    if found != selected_ids:
        raise RuntimeError(f"{name}: missing selected IDs {sorted(selected_ids - found)}")
    return selected, {
        "authority": "Kakao 8.0.3.12 r558734",
        "loader": spec["loader"],
        "sql_address": spec["sql_address"],
        "columns": columns,
        "layout": layout,
        "cached_result": {
            "start": int(spec["start"]),
            "start_hex": f"0x{spec['start']:X}",
            "done": int(spec["done"]),
            "done_hex": f"0x{spec['done']:X}",
            "row_count": len(rows),
            "id_min": min(ids),
            "id_max": max(ids),
            "unique_ids": len(set(ids)),
            "canonical_rows_sha256": canonical_rows_sha256(rows),
        },
        "selected_ids": sorted(selected_ids),
        "selected_rows_sha256": canonical_rows_sha256(selected),
    }


def runtime_rows(
    connection: sqlite3.Connection, table: str, ids: set[int]
) -> list[dict[str, Any]]:
    placeholders = ", ".join("?" for _ in ids)
    return [
        dict(row)
        for row in connection.execute(
            f'SELECT * FROM "{table}" WHERE id IN ({placeholders}) ORDER BY id',
            sorted(ids),
        )
    ]


def select_quest_rows(catalog, game11: bytes):
    selected_ids = {
        "quest_contexts": {QUEST_ID, NEXT_QUEST_ID},
        "quest_components": QUEST_COMPONENT_IDS | {10962, 10963, 10964},
        "quest_acts": QUEST_ACT_IDS | {15458, 15459, 40844, 64093, 65620},
        "npcs": {3597, 11541},
        "models": {10},
        "actor_models": {1},
    }
    rows: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, dict[str, Any]] = {}
    for name, ids in selected_ids.items():
        rows[name], ranges[name] = decode_table(
            catalog.CachedResultReader,
            game11,
            name,
            catalog.TABLE_SPECS[name],
            ids,
        )
    return rows, ranges


def select_equipment_rows(equipment, game11: bytes):
    parser = equipment.load_cache_parser()

    armor_spec = equipment.TABLES["item_armors"]
    armor_rows, armor_range = parser.locate_cached_result(
        parser.CachedResultReader(game11),
        armor_spec["columns"],
        armor_spec["layout"],
        armor_spec["anchor_id"],
        armor_spec["anchor"],
    )
    if len(armor_rows) != int(armor_spec["expected"]):
        raise RuntimeError(
            "item_armors: expected "
            f"{armor_spec['expected']} rows, found {len(armor_rows)}"
        )
    selected_armors = [
        row
        for row in armor_rows
        if int(row["item_id"]) in APPEARANCE_ARMOR_ITEM_IDS
    ]
    found_armors = {int(row["item_id"]) for row in selected_armors}
    if found_armors != APPEARANCE_ARMOR_ITEM_IDS:
        raise RuntimeError(
            "item_armors: missing appearance items "
            f"{sorted(APPEARANCE_ARMOR_ITEM_IDS - found_armors)}"
        )
    armor_range.update(
        {
            "loader": "x2game.dll native item_armors cached SELECT",
            "columns": armor_spec["columns"],
            "layout": armor_spec["layout"],
            "selected_item_ids": sorted(found_armors),
            "selected_rows_sha256": canonical_rows_sha256(selected_armors),
        }
    )

    body_spec = equipment.SPECIAL_RESULTS["item_body_parts"]
    raw_body_parts, body_end = parser.read_cached_result(
        parser.CachedResultReader(game11),
        body_spec["start"],
        body_spec["layout"],
    )
    if len(raw_body_parts) != int(body_spec["expected"]):
        raise RuntimeError(
            "item_body_parts: expected "
            f"{body_spec['expected']} rows, found {len(raw_body_parts)}"
        )
    body_rows = [
        dict(zip(body_spec["columns"], row))
        for row in raw_body_parts
    ]
    selected_body_parts = [
        row
        for row in body_rows
        if int(row["item_id"]) in APPEARANCE_BODY_PART_ITEM_IDS
    ]
    found_body_parts = {int(row["item_id"]) for row in selected_body_parts}
    if found_body_parts != APPEARANCE_BODY_PART_ITEM_IDS:
        raise RuntimeError(
            "item_body_parts: missing appearance items "
            f"{sorted(APPEARANCE_BODY_PART_ITEM_IDS - found_body_parts)}"
        )
    body_range = {
        "start": int(body_spec["start"]),
        "start_hex": f"0x{body_spec['start']:X}",
        "end": body_end,
        "end_hex": f"0x{body_end:X}",
        "rows": len(body_rows),
        "loader": "x2game.dll native item_body_parts cached SELECT",
        "columns": body_spec["columns"],
        "layout": body_spec["layout"],
        "selected_item_ids": sorted(found_body_parts),
        "selected_rows_sha256": canonical_rows_sha256(selected_body_parts),
    }
    return (
        sorted(selected_armors, key=lambda row: int(row["id"])),
        sorted(selected_body_parts, key=lambda row: int(row["item_id"])),
        armor_range,
        body_range,
    )


def select_quest_330_unit_requirements(reader_type, game11: bytes):
    spec = UNIT_REQ_SPEC
    reader = reader_type(game11, spec["first_string_reference"])
    cursor = int(spec["start"])
    rows: list[dict[str, Any]] = []
    while cursor < len(game11) and game11[cursor] == 100:
        values, cursor = reader.row(cursor, spec["layout"])
        rows.append(dict(zip(spec["columns"], values)))
    if cursor != int(spec["done"]) or game11[cursor] != 101:
        raise RuntimeError(
            "unit_reqs: SQLITE_DONE mismatch, "
            f"expected 0x{spec['done']:X}, found 0x{cursor:X}"
        )
    if len(rows) != int(spec["rows"]):
        raise RuntimeError(
            f"unit_reqs: expected {spec['rows']} rows, found {len(rows)}"
        )
    selected = [
        row
        for row in rows
        if row["owner_type"] == "QuestComponent"
        and int(row["owner_id"]) == 1520
    ]
    expected = [{
        "owner_type": "QuestComponent",
        "owner_id": 1520,
        "display_msg": 1,
        "kind_id": 56,
        "value1": 148,
        "value2": 0,
        "value3": 0,
    }]
    if selected != expected:
        raise RuntimeError(f"quest 330 native unit requirements differ: {selected}")
    return selected, {
        "authority": "Kakao 8.0.3.12 r558734",
        "loader": spec["loader"],
        "sql_address": spec["sql_address"],
        "columns": spec["columns"],
        "layout": spec["layout"],
        "cached_result": {
            "start": spec["start"],
            "start_hex": f"0x{spec['start']:X}",
            "done": spec["done"],
            "done_hex": f"0x{spec['done']:X}",
            "row_count": len(rows),
            "selected_rows_sha256": canonical_rows_sha256(selected),
        },
    }


def validate_native_rows(rows: dict[str, list[dict[str, Any]]]) -> None:
    contexts = {int(row["id"]): row for row in rows["quest_contexts"]}
    quest = contexts[QUEST_ID]
    expected_context = {
        "category_id": 3,
        "chapter_idx": 1,
        "degree": 1,
        "detail_id": 2,
        "grade_id": 1,
        "level": 1,
        "min_level": 1,
        "max_level": 0,
        "quest_idx": 1,
        "race": 1,
        "zone_id": 125,
    }
    mismatches = {
        key: (quest[key], value)
        for key, value in expected_context.items()
        if int(quest[key]) != value
    }
    if mismatches:
        raise RuntimeError(f"quest 330 native context mismatch: {mismatches}")
    components = {
        int(row["id"]): row
        for row in rows["quest_components"]
        if int(row["quest_context_id"]) == QUEST_ID
    }
    if set(components) != QUEST_COMPONENT_IDS:
        raise RuntimeError(f"quest 330 component mismatch: {sorted(components)}")
    acts = {
        int(row["id"]): row
        for row in rows["quest_acts"]
        if int(row["quest_component_id"]) in QUEST_COMPONENT_IDS
    }
    if set(acts) != QUEST_ACT_IDS:
        raise RuntimeError(f"quest 330 act mismatch: {sorted(acts)}")
    next_accept = [
        row
        for row in rows["quest_acts"]
        if int(row["quest_component_id"]) == 10962
        and row["act_detail_type"] == "QuestActConAcceptNpc"
        and int(row["act_detail_id"]) == 2097
    ]
    if len(next_accept) != 1:
        raise RuntimeError("quest 2531 native acceptance link is not unique")


def validate_ghidra_evidence(root: Path) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for table, (filename, marker) in GHIDRA_EVIDENCE.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        text = path.read_text(encoding="utf-8")
        if marker not in text or table not in text:
            raise RuntimeError(f"{path}: loader marker is absent")
        evidence[table] = {
            "path": str(path.resolve()),
            "sha256": sha256(path),
            "function": marker.split(" @ ", 1)[0],
            "classification": "x2game_native_loader_accessor_confirmation",
        }
    return evidence


def find_spawn(spawns: list[dict[str, Any]], spawn_id: int, npc_id: int):
    matches = [
        row
        for row in spawns
        if int(row["Id"]) == spawn_id and int(row["UnitId"]) == npc_id
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"spawn {spawn_id}/NPC {npc_id}: expected one row, found {len(matches)}"
        )
    return matches[0]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--x2game", type=Path, default=DEFAULT_X2GAME)
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--spawns", type=Path, default=DEFAULT_SPAWNS)
    parser.add_argument("--ghidra-evidence", type=Path, default=DEFAULT_GHIDRA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    for path in (options.game11, options.x2game, options.base_runtime, options.spawns):
        if not path.is_file():
            raise FileNotFoundError(path)

    catalog = load_module(
        "aa8_npc_quest_catalog", DOMAIN / "extract_native_npc_quest_catalog.py"
    )
    character = load_module(
        "aa8_character_creation",
        ROOT / "reconstruccion_character_8" / "extract_native_character_creation.py",
    )
    equipment = load_module(
        "aa8_native_equipment",
        ROOT / "reconstruccion_items_8" / "extract_native_equipment.py",
    )
    game11 = options.game11.read_bytes()
    selected, source_ranges = select_quest_rows(catalog, game11)
    validate_native_rows(selected)
    selected["unit_reqs"], source_ranges["unit_reqs"] = (
        select_quest_330_unit_requirements(catalog.CachedResultReader, game11)
    )

    for name, spec in CONCRETE_SPECS.items():
        concrete_rows, source_range = decode_table(
            catalog.CachedResultReader,
            game11,
            name,
            spec,
            set(spec["selected_ids"]),
        )
        selected[name] = concrete_rows
        source_ranges[name] = source_range

    item_parser = character.load_parser()
    item_reader = item_parser.CachedResultReader(game11)
    referenced_item_ids = {23633} | APPEARANCE_ITEM_IDS
    item_rows, item_range = character.extract_referenced_items(
        item_parser, item_reader, referenced_item_ids
    )
    selected["items"] = item_rows
    source_ranges["items"] = {
        **item_range,
        "selected_rows_sha256": canonical_rows_sha256(item_rows),
    }
    (
        selected["item_armors"],
        selected["item_body_parts"],
        source_ranges["item_armors"],
        source_ranges["item_body_parts"],
    ) = select_equipment_rows(equipment, game11)

    concrete_by_id = {
        name: {int(row["id"]): row for row in selected[name]}
        for name in CONCRETE_SPECS
    }
    if int(concrete_by_id["quest_act_con_accept_npcs"][1250]["npc_id"]) != 3597:
        raise RuntimeError("quest 330 accept NPC is not native NPC 3597")
    if int(concrete_by_id["quest_act_con_report_npcs"][329]["npc_id"]) != 11541:
        raise RuntimeError("quest 330 report NPC is not native NPC 11541")
    if int(concrete_by_id["quest_act_con_accept_npcs"][2097]["npc_id"]) != 11541:
        raise RuntimeError("quest 2531 is not accepted from native NPC 11541")

    fixed_rewards = concrete_by_id["quest_act_supply_items"]
    selective_rewards = concrete_by_id["quest_act_supply_selective_items"]
    reward_ids = {
        int(row["item_id"]) for row in fixed_rewards.values()
    } | {
        int(row["item_id"]) for row in selective_rewards.values()
    }
    if reward_ids != REWARD_ITEM_IDS:
        raise RuntimeError(f"quest 330 reward closure differs: {sorted(reward_ids)}")
    if int(concrete_by_id["quest_act_supply_exps"][3922]["exp"]) != 210:
        raise RuntimeError("quest 330 native custom EXP is not 210")
    native_level_supply = concrete_by_id["quest_supplies"][1]
    if (
        int(native_level_supply["level"]),
        int(native_level_supply["copper"]),
        int(native_level_supply["exp"]),
    ) != (1, 33, 420):
        raise RuntimeError("native level-1 generic quest supply differs")

    spawns = json.loads(options.spawns.read_text(encoding="utf-8-sig"))
    accept_spawn = find_spawn(spawns, 7682, 3597)
    report_spawn = find_spawn(spawns, 8238, 11541)
    first = accept_spawn["Position"]
    second = report_spawn["Position"]
    distance = math.sqrt(
        sum((float(first[key]) - float(second[key])) ** 2 for key in ("X", "Y", "Z"))
    )

    connection = sqlite3.connect(
        f"file:{options.base_runtime.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        base_snapshot = {
            "quest_contexts": runtime_rows(connection, "quest_contexts", {330, 2531}),
            "quest_components": runtime_rows(
                connection, "quest_components", QUEST_COMPONENT_IDS
            ),
            "quest_acts": runtime_rows(connection, "quest_acts", QUEST_ACT_IDS),
            "quest_act_con_accept_npcs": runtime_rows(
                connection, "quest_act_con_accept_npcs", {1250, 2097}
            ),
            "quest_act_con_report_npcs": runtime_rows(
                connection, "quest_act_con_report_npcs", {329}
            ),
            "quest_act_supply_items": runtime_rows(
                connection, "quest_act_supply_items", {8675, 8676, 8869}
            ),
            "quest_act_supply_exps": runtime_rows(
                connection, "quest_act_supply_exps", {3922}
            ),
            "quest_act_supply_selective_items": runtime_rows(
                connection, "quest_act_supply_selective_items", {3646, 3647}
            ),
            "items": runtime_rows(connection, "items", REWARD_ITEM_IDS),
            "item_armors": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM item_armors WHERE item_id IN (?, ?, ?, ?) "
                    "ORDER BY id",
                    sorted(APPEARANCE_ARMOR_ITEM_IDS),
                )
            ],
            "item_body_parts": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM item_body_parts WHERE item_id IN (?, ?, ?) "
                    "ORDER BY item_id",
                    sorted(APPEARANCE_BODY_PART_ITEM_IDS),
                )
            ],
            "quest_supplies": runtime_rows(connection, "quest_supplies", {1}),
            "npcs": runtime_rows(connection, "npcs", {3597, 11541}),
            "models": runtime_rows(connection, "models", {10}),
            "actor_models": runtime_rows(connection, "actor_models", {1}),
        }
    finally:
        connection.close()

    native_npcs = {int(row["id"]): row for row in selected["npcs"]}
    base_npcs = {int(row["id"]): row for row in base_snapshot["npcs"]}
    for npc_id in (3597, 11541):
        for column in (
            "model_id",
            "faction_id",
            "char_race_id",
            "level",
            "equip_cloths_id",
            "equip_weapons_id",
            "total_custom_id",
            "npc_grade_id",
            "npc_kind_id",
            "scale",
        ):
            if base_npcs[npc_id][column] != native_npcs[npc_id][column]:
                raise RuntimeError(f"NPC {npc_id}: runtime differs in {column}")
    if base_snapshot["quest_supplies"] != [native_level_supply]:
        raise RuntimeError(
            "runtime level-1 quest supply differs from the native AA8 row"
        )

    mutation_tables = {
        "quest_contexts": [
            row for row in selected["quest_contexts"] if int(row["id"]) == QUEST_ID
        ],
        "quest_components": [
            row
            for row in selected["quest_components"]
            if int(row["quest_context_id"]) == QUEST_ID
        ],
        "quest_acts": [
            row
            for row in selected["quest_acts"]
            if int(row["quest_component_id"]) in QUEST_COMPONENT_IDS
        ],
        "quest_act_con_accept_npcs": [
            concrete_by_id["quest_act_con_accept_npcs"][1250]
        ],
        "quest_act_con_report_npcs": [
            concrete_by_id["quest_act_con_report_npcs"][329]
        ],
        "quest_act_supply_items": list(fixed_rewards.values()),
        "quest_act_supply_exps": [
            concrete_by_id["quest_act_supply_exps"][3922]
        ],
        "quest_act_supply_selective_items": list(selective_rewards.values()),
        "unit_reqs": selected["unit_reqs"],
        "items": item_rows,
        "item_armors": selected["item_armors"],
        "item_body_parts": selected["item_body_parts"],
        "aaemu_item_definition_coverage": [
            {
                "item_id": item_id,
                "concrete_type": (
                    "armor"
                    if item_id in APPEARANCE_ARMOR_ITEM_IDS
                    else "body_part"
                    if item_id in APPEARANCE_BODY_PART_ITEM_IDS or item_id == 48541
                    else "generic"
                ),
                "coverage": "complete",
                "missing_dependencies": "",
                "provenance": (
                    "AA8 quest330 NPC appearance closure: "
                    "client compact + game11 native"
                ),
            }
            for item_id in sorted(RUNTIME_COMPLETE_ITEM_IDS)
        ],
    }
    for table, rows in mutation_tables.items():
        if table == "unit_reqs":
            rows.sort(
                key=lambda row: (
                    str(row["owner_type"]),
                    int(row["owner_id"]),
                    int(row["kind_id"]),
                )
            )
            continue
        key = "item_id" if table in (
            "aaemu_item_definition_coverage",
            "item_body_parts",
        ) else "id"
        rows.sort(key=lambda row: int(row[key]))

    sources = {
        "game11": {
            "path": str(options.game11.resolve()),
            "sha256": sha256(options.game11),
        },
        "x2game": {
            "path": str(options.x2game.resolve()),
            "sha256": sha256(options.x2game),
        },
        "base_runtime": {
            "path": str(options.base_runtime.resolve()),
            "sha256": sha256(options.base_runtime),
        },
        "server_spawn_reference": {
            "path": str(options.spawns.resolve()),
            "sha256": sha256(options.spawns),
            "classification": "server_derived_accepted_for_pilot",
        },
    }
    data = {
        "format_version": 3,
        "authority": "Kakao 8.0.3.12 r558734",
        "sources": sources,
        "tables": mutation_tables,
    }
    manifest = {
        "phase": "native-quest-330-v3",
        "authority": "Kakao 8.0.3.12 r558734",
        "deployable": True,
        "scope": {
            "quest_id": QUEST_ID,
            "next_quest_id": NEXT_QUEST_ID,
            "accept_npc_id": 3597,
            "report_npc_id": 11541,
            "component_ids": sorted(QUEST_COMPONENT_IDS),
            "act_ids": sorted(QUEST_ACT_IDS),
            "reward_item_ids": sorted(REWARD_ITEM_IDS),
            "appearance_item_ids": sorted(APPEARANCE_ITEM_IDS),
            "custom_exp": 210,
            "generic_copper": 33,
            "generic_exp_suppressed_by_custom_exp": 420,
        },
        "sources": sources,
        "ghidra_loader_evidence": validate_ghidra_evidence(options.ghidra_evidence),
        "source_ranges": source_ranges,
        "table_classifications": {
            table: (
                "server_derived_runtime_gate_from_native_closure"
                if table == "aaemu_item_definition_coverage"
                else "native_reference_closure"
                if table == "items"
                else "native_authoritative_targeted_upsert"
            )
            for table in mutation_tables
        },
        "table_counts": {
            table: len(rows) for table, rows in mutation_tables.items()
        },
        "runtime_before": base_snapshot,
        "verified_existing_closure": {
            "npcs": [3597, 11541],
            "model_id": 10,
            "actor_model_id": 1,
            "next_quest_accept": {
                "quest_id": 2531,
                "component_id": 10962,
                "act_detail_id": 2097,
                "npc_id": 11541,
                "classification": "native_client_chain_acceptance_closure",
            },
            "level_1_quest_supply": {
                "id": 1,
                "level": 1,
                "copper": 33,
                "exp": 420,
                "classification": "native_existing_runtime_closure",
                "behavior": (
                    "The custom 210 EXP act suppresses generic EXP; no custom "
                    "copper act exists, so the native generic 33 copper applies."
                ),
            },
        },
        "placement_policy": {
            "classification": "server_derived_accepted_for_pilot",
            "native_claim": False,
            "reason": (
                "The two server placements already produce the visible AA8 NPCs. "
                "The operator explicitly authorized this quest-330 pilot while "
                "native placement reconstruction remains incomplete."
            ),
            "accept_spawn": accept_spawn,
            "report_spawn": report_spawn,
            "distance_meters": distance,
        },
        "quest_flow": [
            "NPC 3597 accepts quest 330 through detail 1250.",
            "Quest 330 has no intermediate objective component.",
            "NPC 11541 reports quest 330 through detail 329.",
            "Reward grants 210 custom EXP.",
            "The native level-1 generic supply grants 33 copper; its 420 EXP is "
            "suppressed by the explicit 210 EXP act.",
            "Fixed rewards: item 23633 x1, item 51185 x1, item 18791 x5.",
            "Selection rewards: item 47868 x2 or item 47869 x1.",
            "NPC 11541 accepts the next native quest 2531 through detail 2097.",
        ],
        "server_fix_required": {
            "files": [
                "AAEmu.Game/Models/Game/Quests/Quest.cs",
                "AAEmu.Game/Core/Packets/C2G/CSSelectCharacterPacket.cs",
                "AAEmu.Game/Core/Managers/UnitManagers/NpcManager.cs",
            ],
            "required_behavior": [
                "Return a matching custom reward immediately.",
                "Synchronize active and completed quest state during character selection.",
                "Serialize AA8 NPC race/gender and all six fixed face decals.",
            ],
        },
        "blockers": [],
    }

    write_json(options.output / "native-quest-330-v3-data.json", data)
    write_json(options.output / "native-quest-330-v3-manifest.json", manifest)
    print(
        json.dumps(
            {
                "deployable": True,
                "quest_id": QUEST_ID,
                "output": str(options.output.resolve()),
                "tables": manifest["table_counts"],
                "distance_meters": round(distance, 3),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
