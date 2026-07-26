#!/usr/bin/env python3
"""Extract the Kakao 8.0 native character-creation catalogue.

Only cached results whose layouts and consumers are confirmed in x2game.dll
are emitted. Server-owned spawn transforms remain blocked until AA8 authority
is available.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"


def load_parser():
    spec = importlib.util.spec_from_file_location("aa8_cached_result", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--runtime-compact", required=True, type=Path)
    parser.add_argument("--x2game", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


TABLES: dict[str, dict[str, Any]] = {
    "character_supplies": {
        "columns": "id ability_id amount grade_id item_id".split(),
        "layout": ["68"] * 5,
        "anchor_id": 87,
        "anchor": {"ability_id": 0, "amount": 1, "grade_id": 0, "item_id": 4045},
        "expected": 4,
        "loader": "x2game.dll embedded SELECT at 0x39dd5a50",
    },
    "characters": {
        "columns": (
            "id char_gender_id char_race_id default_custom_id "
            "default_fx_voice_sound_pack_id default_resurrection_district_id "
            "default_return_district_id default_system_voice_sound_pack_id "
            "face_item_id faction_id model_id preview_cloth_pack_id starting_zone_id"
        ).split(),
        "layout": ["68"] * 13,
        "anchor_id": 1,
        "anchor": {"char_gender_id": 1, "char_race_id": 1, "starting_zone_id": 179},
        "expected": 12,
        "loader": "x2game.dll embedded SELECT at 0x39dd5b30",
    },
    "character_equip_packs": {
        "columns": "id name newbie_cloth_pack_id newbie_weapon_pack_id".split(),
        "layout": ["68", "78", "68", "68"],
        "anchor_id": 1,
        "anchor": {
            "name": "fight_equip_pack",
            "newbie_cloth_pack_id": 11,
            "newbie_weapon_pack_id": 242,
        },
        "expected": 14,
        "loader": "x2game.dll embedded SELECT at 0x39dd15a0",
    },
    "equip_pack_cloths": {
        "columns": (
            "id back_grade_id back_id backpack_grade_id backpack_id belt_grade_id "
            "belt_id bracelet_grade_id bracelet_id cosplay_grade_id cosplay_id "
            "glove_grade_id glove_id headgear_grade_id headgear_id necklace_grade_id "
            "necklace_id pants_grade_id pants_id shirt_grade_id shirt_id shoes_grade_id "
            "shoes_id stabilizer_grade_id stabilizer_id underpants_grade_id "
            "underpants_id undershirt_grade_id undershirt_id"
        ).split(),
        "layout": ["68"] * 29,
        "anchor_id": 1,
        "anchor": {"glove_id": 14464, "headgear_id": 18489},
        "expected": 2389,
        "loader": "x2game.dll FUN_399481d0",
    },
    "equip_pack_weapons": {
        "columns": (
            "id mainhand_grade_id mainhand_id musical_grade_id musical_id "
            "offhand_grade_id offhand_id ranged_grade_id ranged_id"
        ).split(),
        "layout": ["68"] * 9,
        "anchor_id": 1,
        "anchor": {"mainhand_id": 5311},
        "expected": 664,
        "loader": "x2game.dll embedded SELECT at 0x39dd3f10",
    },
    "character_default_skills": {
        "columns": "character_id default_skill_id".split(),
        "layout": ["68", "68"],
        "anchor_id": 13,
        "anchor": {"default_skill_id": 156},
        "expected": 24,
        "loader": "x2game.dll embedded SELECT at 0x39dbae70",
    },
    "default_skills": {
        "columns": (
            "id add_to_slot skill_active_type_id skill_book_category_id skill_id slot_index"
        ).split(),
        "layout": ["68", "38", "68", "68", "68", "68"],
        "anchor_id": 22,
        "anchor": {"add_to_slot": 1, "skill_id": 10594, "slot_index": 22},
        "expected": 146,
        "loader": "x2game.dll embedded SELECT at 0x39dd6880",
    },
    "login_stage_abilities": {
        "columns": (
            "id ability_id active_weapon_id difficulty_score end_signal "
            "preview_skill_01_id preview_skill_02_id preview_skill_03_id start_anim_id "
            "start_equip_pack_id start_signal stop_anim_id tendency_debuff "
            "tendency_enchant tendency_magical_attack tendency_physical_attack "
            "tendency_protect"
        ).split(),
        "layout": (
            ["68", "68", "68", "60", "78"]
            + (["68"] * 5)
            + ["78"]
            + (["68"] * 6)
        ),
        "anchor_id": 1,
        "anchor": {
            "ability_id": 1,
            "difficulty_score": 3.0,
            "start_equip_pack_id": 1,
            "start_signal": "loginstage_class_melee",
        },
        "expected": 8,
        "loader": "x2game.dll FUN_39a41760",
    },
    "district_return_points": {
        "columns": "id district_id faction_id return_point_id".split(),
        "layout": ["68"] * 4,
        "anchor_id": 1,
        "anchor": {"district_id": 1, "faction_id": 101, "return_point_id": 15},
        "expected": 4014,
        "loader": "x2game.dll FUN_39956b30",
    },
    "return_points": {
        "columns": "id editor_name name use_additional".split(),
        "layout": ["68", "78", "78", "38"],
        "anchor_id": 1,
        "anchor": {"editor_name": "Gweonid_HarpaCamp", "use_additional": 1},
        "expected": 1024,
        "loader": (
            "x2game.dll embedded SELECT "
            "id, editor_name, name, use_additional FROM return_points"
        ),
    },
}


STARTER_PACK_IDS = {1, 6, 7, 10, 11, 12, 13, 14}

ITEM_COLUMNS = (
    "id actability_group_id actability_requirement auction_a_category_id "
    "auction_b_category_id auction_c_category_id auction_charge "
    "auction_charge_default auction_only auto_complete auto_loot "
    "auto_register_to_actionbar bind_id buff_id cash_item category_id "
    "char_gender_id contribution_point_price craft_id description "
    "disenchantable exp_abs_lifetime exp_date exp_day_of_week_id "
    "exp_day_of_week_min exp_online_lifetime expedition_level fixed_grade "
    "gradable honor_price icon_id impl_id ingameshop_main_category "
    "ingameshop_sub_category level level_limit level_requirement "
    "limited_sale_count living_point_price loot_multi loot_quest_id "
    "male_icon_id max_enchant_scale_id max_enchantable_grade max_stack_size "
    "name notify_ui one_time_sale over_icon_id pickup_limit pickup_sound_id "
    "price proc_lifetime proc_recharge_restrict_item_id refund sellable "
    "side_effect specialty_zone_id uid use_or_equipment_sound_id "
    "use_skill_as_reagent use_skill_lifetime "
    "use_skill_recharge_restrict_item_id use_skill_id"
).split()

ITEM_LAYOUT = (
    "68 68 68 68 68 68 68 38 38 38 38 38 68 68 38 68 "
    "68 68 68 78 38 68 40 68 68 68 68 68 38 68 68 68 "
    "68 68 68 68 68 68 68 38 68 68 68 68 68 78 38 38 "
    "68 68 68 68 68 68 68 38 38 68 70 68 38 68 68 68"
).split()

SUPPLY_ITEM_IDS = {417, 4045, 18791, 18792}
ITEM_RESULT_ROW_COUNT = 37223
DEFAULT_ACTION_COLUMNS = ["id", "item_id", "slot_index"]
NPC_NICKNAME_COLUMNS = ["id", "map_icon_id", "name"]
NPC_NICKNAME_LAYOUT = ["68", "68", "78"]
NPC_NICKNAME_ROW_COUNT = 169
START_RETURN_POINT_BY_RACE = {
    1: 243,
    3: 239,
    4: 245,
    5: 240,
    6: 241,
    8: 717,
}


def extract_table(parser, reader, name: str, spec: dict[str, Any]):
    rows, source_range = parser.locate_cached_result(
        reader,
        spec["columns"],
        spec["layout"],
        spec["anchor_id"],
        spec["anchor"],
    )
    if len(rows) != spec["expected"]:
        raise RuntimeError(
            f"{name}: expected {spec['expected']} rows, found {len(rows)}"
        )
    source_range["loader"] = spec["loader"]
    source_range["layout"] = spec["layout"]
    source_range["columns"] = spec["columns"]
    return rows, source_range


def item_ids_from_packs(tables: dict[str, list[dict[str, Any]]]) -> list[int]:
    login_pack_ids = {
        int(row["start_equip_pack_id"]) for row in tables["login_stage_abilities"]
    }
    if login_pack_ids != STARTER_PACK_IDS:
        raise RuntimeError(
            f"login-stage pack ids differ: {sorted(login_pack_ids)}"
        )
    packs = {
        int(row["id"]): row for row in tables["character_equip_packs"]
    }
    cloth_ids = {
        int(packs[pack_id]["newbie_cloth_pack_id"]) for pack_id in login_pack_ids
    }
    weapon_ids = {
        int(packs[pack_id]["newbie_weapon_pack_id"]) for pack_id in login_pack_ids
    }
    cloth = {
        int(row["id"]): row for row in tables["equip_pack_cloths"]
    }
    weapons = {
        int(row["id"]): row for row in tables["equip_pack_weapons"]
    }
    item_ids: set[int] = set()
    for pack_id in cloth_ids:
        row = cloth[pack_id]
        item_ids.update(
            int(value)
            for key, value in row.items()
            if key.endswith("_id") and not key.endswith("grade_id") and key != "id"
            and int(value) > 0
        )
    for pack_id in weapon_ids:
        row = weapons[pack_id]
        item_ids.update(
            int(value)
            for key, value in row.items()
            if key.endswith("_id") and not key.endswith("grade_id") and key != "id"
            and int(value) > 0
        )
    return sorted(item_ids)


def extract_referenced_items(
    parser,
    reader,
    referenced_item_ids: set[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, source_range = parser.locate_cached_result(
        reader,
        ITEM_COLUMNS,
        ITEM_LAYOUT,
        417,
        {
            "name": "귀속된 저승의 돌",
            "category_id": 14,
            "max_stack_size": 1000,
        },
    )
    if len(rows) != ITEM_RESULT_ROW_COUNT:
        raise RuntimeError(
            f"items: expected {ITEM_RESULT_ROW_COUNT} rows, found {len(rows)}"
        )

    selected: dict[int, dict[str, Any]] = {}
    duplicate_ids: set[int] = set()
    for row in rows:
        item_id = int(row["id"])
        if item_id not in referenced_item_ids:
            continue
        if item_id in selected:
            duplicate_ids.add(item_id)
        selected[item_id] = row
    if duplicate_ids:
        raise RuntimeError(
            f"items: duplicate referenced ids: {sorted(duplicate_ids)}"
        )

    missing = sorted(referenced_item_ids - set(selected))
    if missing:
        raise RuntimeError(f"items: missing referenced AA8 rows: {missing}")

    bool_columns = {
        ITEM_COLUMNS[index]
        for index, field_type in enumerate(ITEM_LAYOUT)
        if field_type == "38"
    }
    invalid_bool_rows = sorted(
        int(row["id"])
        for row in selected.values()
        if any(int(row[column]) not in (0, 1) for column in bool_columns)
    )
    invalid_stack_rows = sorted(
        int(row["id"])
        for row in selected.values()
        if not 1 <= int(row["max_stack_size"]) <= 10_000_000
    )
    if invalid_bool_rows or invalid_stack_rows:
        raise RuntimeError(
            "items: invalid native rows "
            f"bool={invalid_bool_rows}, stack={invalid_stack_rows}"
        )

    source_range.update(
        {
            "loader": "x2game.dll embedded items SELECT",
            "layout": ITEM_LAYOUT,
            "columns": ITEM_COLUMNS,
            "classification": "native_reference_closure",
            "selected_rows": len(selected),
        }
    )
    return [selected[item_id] for item_id in sorted(selected)], source_range


def prove_empty_default_action_bar(
    parser,
    reader,
    default_skills_range: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Prove the action table has no rows using adjacent native load results.

    x2game.dll FUN_399005a0 calls the loaders in this exact order:
    default_skills, default_action_bar_actions, npc_nicknames. Cached non-empty
    results have a five-byte header (SQLITE_ROW + little-endian row count).
    The npc header starts immediately after the default_skills SQLITE_DONE,
    leaving no cached row payload for the intervening action query.
    """
    npc_rows, npc_range = parser.locate_cached_result(
        reader,
        NPC_NICKNAME_COLUMNS,
        NPC_NICKNAME_LAYOUT,
        3,
        {"map_icon_id": 45, "name": "TEST_재료 상인"},
    )
    if len(npc_rows) != NPC_NICKNAME_ROW_COUNT:
        raise RuntimeError(
            "npc_nicknames sentinel: expected "
            f"{NPC_NICKNAME_ROW_COUNT} rows, found {len(npc_rows)}"
        )

    default_done = int(default_skills_range["end"])
    npc_start = int(npc_range["start"])
    expected_npc_start = default_done + 6
    header = reader.data[default_done + 1 : npc_start]
    expected_header = b"\x64" + struct.pack("<i", NPC_NICKNAME_ROW_COUNT)
    if reader.data[default_done] != 101:
        raise RuntimeError("default_skills result lacks SQLITE_DONE boundary")
    if npc_start != expected_npc_start or header != expected_header:
        raise RuntimeError(
            "default action-bar empty-result boundary is not exact: "
            f"default_done={default_done}, npc_start={npc_start}, "
            f"header={header.hex()}"
        )

    action_range = {
        "start": default_done + 1,
        "end": default_done + 1,
        "rows": 0,
        "columns": DEFAULT_ACTION_COLUMNS,
        "layout": ["68", "68", "68"],
        "loader": "x2game.dll FUN_39956660",
        "classification": "native_authoritative_empty",
        "proof": {
            "loader_order": (
                "FUN_39956370 default_skills -> FUN_39956660 "
                "default_action_bar_actions -> FUN_399568a0 npc_nicknames"
            ),
            "previous_result_done": default_done,
            "next_result_header": default_done + 1,
            "next_result_rows": NPC_NICKNAME_ROW_COUNT,
            "next_result_start": npc_start,
            "intervening_payload_bytes": 0,
        },
    }
    npc_range.update(
        {
            "columns": NPC_NICKNAME_COLUMNS,
            "layout": NPC_NICKNAME_LAYOUT,
            "loader": "x2game.dll FUN_399568a0",
            "classification": "boundary_sentinel",
        }
    )
    return [], action_range, npc_range


def resolve_start_return_points(
    tables: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    districts: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in tables["district_return_points"]:
        key = (int(row["district_id"]), int(row["faction_id"]))
        districts.setdefault(key, []).append(row)

    return_points = {
        int(row["id"]): row for row in tables["return_points"]
    }
    resolved: list[dict[str, Any]] = []
    for character in tables["characters"]:
        race = int(character["char_race_id"])
        key = (
            int(character["default_return_district_id"]),
            int(character["faction_id"]),
        )
        matches = districts.get(key, [])
        if not matches:
            raise RuntimeError(
                f"character {character['id']}: no native start district for {key}"
            )
        if len(matches) != 1:
            raise RuntimeError(
                f"character {character['id']}: native start district {key} "
                f"has {len(matches)} candidate rows"
            )
        district = matches[0]
        return_point_id = int(district["return_point_id"])
        expected = START_RETURN_POINT_BY_RACE.get(race)
        if return_point_id != expected:
            raise RuntimeError(
                f"race {race}: expected return point {expected}, "
                f"found {return_point_id}"
            )
        return_point = return_points.get(return_point_id)
        if return_point is None:
            raise RuntimeError(
                f"race {race}: missing return point row {return_point_id}"
            )
        if int(return_point["use_additional"]) != 1:
            raise RuntimeError(
                f"race {race}: start return point {return_point_id} "
                "is not marked use_additional"
            )
        resolved.append(
            {
                "character_id": int(character["id"]),
                "race_id": race,
                "gender_id": int(character["char_gender_id"]),
                "starting_zone_id": int(character["starting_zone_id"]),
                "district_id": key[0],
                "faction_id": key[1],
                "district_return_point_row_id": int(district["id"]),
                "return_point_id": return_point_id,
                "return_point_editor_name": return_point["editor_name"],
                "return_point_use_additional": int(
                    return_point["use_additional"]
                ),
            }
        )
    return resolved


def sqlite_ids(path: Path, table: str) -> set[int]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return {int(row[0]) for row in connection.execute(f'SELECT id FROM "{table}"')}
    finally:
        connection.close()


def extract_start_skills_from_runtime(
    path: Path,
    ability_ids: list[int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Close the selected ability -> learned skill references from native B14.

    B14 is itself a validated AA8-derived runtime and remains the build base.
    Keeping the complete rows here makes the creation domain independently
    auditable without replacing the unrelated skill catalogue.
    """
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        columns = [
            str(row[1])
            for row in connection.execute('PRAGMA table_info("skills")')
        ]
        placeholders = ", ".join("?" for _ in ability_ids)
        rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM skills "
                f"WHERE ability_id IN ({placeholders}) "
                "AND ability_level <= 1 AND auto_learn = 1 "
                "AND need_learn = 1 AND show = 1 "
                "ORDER BY ability_id, id",
                ability_ids,
            )
        ]
    finally:
        connection.close()

    by_ability: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_ability.setdefault(int(row["ability_id"]), []).append(row)
    invalid = {
        ability_id: [int(row["id"]) for row in by_ability.get(ability_id, [])]
        for ability_id in ability_ids
        if len(by_ability.get(ability_id, [])) != 1
    }
    if invalid:
        raise RuntimeError(
            f"native start skill closure is not one-to-one: {invalid}"
        )

    return rows, {
        "source": "validated native runtime B14",
        "source_sha256": sha256(path),
        "table": "skills",
        "columns": columns,
        "classification": "native_reference_closure",
        "criteria": {
            "ability_ids": ability_ids,
            "ability_level_max": 1,
            "auto_learn": 1,
            "need_learn": 1,
            "show": 1,
        },
        "selected_rows": len(rows),
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    options = parse_args()
    for path in (
        options.game11,
        options.client_compact,
        options.runtime_compact,
        options.x2game,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    parser = load_parser()
    reader = parser.CachedResultReader(options.game11.read_bytes())
    tables: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, dict[str, Any]] = {}
    for name, spec in TABLES.items():
        tables[name], ranges[name] = extract_table(parser, reader, name, spec)

    ability_ids = sorted(
        int(row["ability_id"]) for row in tables["login_stage_abilities"]
    )
    if ability_ids != [1, 6, 7, 10, 11, 12, 13, 14]:
        raise RuntimeError(f"unexpected login abilities: {ability_ids}")

    character_ids = {int(row["id"]) for row in tables["characters"]}
    if len(character_ids) != 12:
        raise RuntimeError("the native playable race/gender matrix is incomplete")
    default_skill_ids = {int(row["id"]) for row in tables["default_skills"]}
    missing_default_skills = sorted(
        {
            int(row["default_skill_id"])
            for row in tables["character_default_skills"]
        }
        - default_skill_ids
    )
    if missing_default_skills:
        raise RuntimeError(
            f"missing referenced default skills: {missing_default_skills}"
        )

    starter_item_ids = item_ids_from_packs(tables)
    supply_item_ids = {
        int(row["item_id"]) for row in tables["character_supplies"]
    }
    if supply_item_ids != SUPPLY_ITEM_IDS:
        raise RuntimeError(
            f"native supply item ids differ: {sorted(supply_item_ids)}"
        )
    referenced_item_ids = set(starter_item_ids) | supply_item_ids
    tables["items"], ranges["items"] = extract_referenced_items(
        parser,
        reader,
        referenced_item_ids,
    )
    (
        tables["default_action_bar_actions"],
        ranges["default_action_bar_actions"],
        ranges["npc_nicknames_sentinel"],
    ) = prove_empty_default_action_bar(
        parser,
        reader,
        ranges["default_skills"],
    )
    client_item_ids = sqlite_ids(options.client_compact, "items")
    runtime_item_ids = sqlite_ids(options.runtime_compact, "items")
    missing_client_items = sorted(referenced_item_ids - client_item_ids)
    missing_runtime_items = sorted(referenced_item_ids - runtime_item_ids)
    start_return_points = resolve_start_return_points(tables)
    tables["skills"], ranges["skills"] = extract_start_skills_from_runtime(
        options.runtime_compact,
        ability_ids,
    )
    start_skill_ids = {
        int(row["ability_id"]): int(row["id"]) for row in tables["skills"]
    }

    blockers = [
        {
            "code": "spawn_transform_unproven",
            "detail": (
                "AA8 characters, district_return_points and return_points prove "
                "the zone and logical start return point for every playable "
                "race, but expose no authoritative server XYZ/quaternion. The "
                "AA8 character-list serializer consumes position, three angles "
                "and zone as server-provided character fields; no client-side "
                "initializer for those values was found. Historical "
                "CharTemplates.json is excluded."
            ),
        },
        {
            "code": "action_bar_bootstrap_unproven",
            "detail": (
                "The native default_action_bar_actions result is exactly empty "
                "and character_default_skills proves only per-character defaults. "
                "The client auto-registers a combat skill in the first empty base "
                "slot only while handling an explicit SCSkillLearned packet and "
                "only below level 21. Character creation does not prove that this "
                "packet was emitted by an authentic AA8 server, so neither the "
                "selected skill's initial slot nor a complete snapshot has been "
                "observed. BaseActionBarEmptySlotCount dispatches telemetry rather "
                "than populating an action."
            ),
        },
        {
            "code": "supply_inventory_slots_unproven",
            "detail": (
                "character_supplies proves item, amount and grade but its AA8 "
                "layout has no bag slot. The client consumes item slots from "
                "server inventory packets and the four starter supply item "
                "templates have auto_register_to_actionbar disabled. Historical "
                "first-free placement and historical action slots 10-12 are "
                "excluded."
            ),
        },
        {
            "code": "initial_inventory_capacity_unproven",
            "detail": (
                "The AA8 character row does not contain initial bag/bank capacity. "
                "The character-list and full-character serializers consume "
                "invenSlots/numInvenSlots and bankSlots/numBankSlots as "
                "server-provided values, but no client-side initial values were "
                "found. CharTemplates.json capacity is historical and cannot "
                "authorize a native bootstrap."
            ),
        },
    ]
    sources = {
        "game11": {"path": str(options.game11), "sha256": sha256(options.game11)},
        "client_compact": {
            "path": str(options.client_compact),
            "sha256": sha256(options.client_compact),
        },
        "runtime_compact": {
            "path": str(options.runtime_compact),
            "sha256": sha256(options.runtime_compact),
        },
        "x2game": {"path": str(options.x2game), "sha256": sha256(options.x2game)},
    }
    bundle = {
        "format_version": 1,
        "sources": sources,
        "tables": tables,
    }
    manifest = {
        "phase": "native-character-creation-v1",
        "authority": "Kakao 8.0.3.12 r558734",
        "deployable": not blockers,
        "sources": sources,
        "source_ranges": ranges,
        "table_counts": {name: len(rows) for name, rows in tables.items()},
        "table_classifications": {
            name: (
                "native_reference_closure"
                if name in ("items", "skills")
                else "native_authoritative_empty"
                if name == "default_action_bar_actions"
                else "native_authoritative_replacement"
            )
            for name in tables
        },
        "table_schemas": {
            "default_action_bar_actions": {
                "columns": DEFAULT_ACTION_COLUMNS,
                "layout": ["68", "68", "68"],
            }
        },
        "matrix": {
            "character_templates": len(character_ids),
            "ability_ids": ability_ids,
            "combinations": len(character_ids) * len(ability_ids),
        },
        "start_return_points": start_return_points,
        "starter_item_ids": starter_item_ids,
        "supply_item_ids": sorted(supply_item_ids),
        "referenced_item_ids": sorted(referenced_item_ids),
        "start_skill_ids": start_skill_ids,
        "start_skill_reference_closure": {
            "classification": "native_reference_closure",
            "rows": len(tables["skills"]),
            "historical_rows": 0,
            "criteria": ranges["skills"]["criteria"],
        },
        "starter_item_ids_missing_client_base": missing_client_items,
        "starter_item_ids_missing_runtime_base": missing_runtime_items,
        "item_reference_closure": {
            "classification": "native_reference_closure",
            "rows": len(tables["items"]),
            "source_result_rows": ITEM_RESULT_ROW_COUNT,
            "historical_rows": 0,
        },
        "default_action_bar_actions": {
            "provenance": "game11_adjacent_native_result_boundary",
            "loader": "x2game.dll FUN_39956660",
            "rows": 0,
            "historical_rows": 0,
            "proof": ranges["default_action_bar_actions"]["proof"],
        },
        "protocol": {
            "create_character_request": (
                "x2game.dll FUN_3997d1b0 + FUN_399a70b0: string name, byte race, "
                "byte gender, seven uint32 body items, 0x128-byte custom model, "
                "three ability bytes, byte level=1, int32 introZoneId=-1"
            ),
            "create_character_response": (
                "opcode 0x2DD -> x2game.dll FUN_3997b180 -> FUN_399228b0; "
                "the response is exactly the AA8 character-list serializer"
            ),
            "action_slots_snapshot": (
                "SCActionSlots serializes exactly 217 entries; type byte followed "
                "by uint32 for 1/2/5/6, uint64 for 4, no payload for 0"
            ),
            "skill_auto_registration": (
                "x2game.dll FUN_392fa740 handles explicit SCSkillLearned, calls "
                "FUN_395fb5a0, then FUN_39690860; below level 21 the latter uses "
                "FUN_39690340 to select an existing matching spell or the first "
                "empty base slot and dispatches ACTION_BAR_AUTO_REGISTERED"
            ),
            "server_owned_character_state": (
                "x2game.dll FUN_3991e9f0 serializes position, angles, zone, "
                "invenSlots and bankSlots from the server character state; "
                "FUN_39926040/FUN_3997dfa0 consume the full-state inventory and "
                "bank slot counts"
            ),
            "update_action_slot": (
                "x2game.dll FUN_399a7970 + FUN_3999be30: byte slot, byte type; "
                "uint32 for types 1/2/5/6, uint64 for type 4"
            ),
            "observed_opcode_0x0ae": (
                "inventory sort; x2game.dll FUN_397d3980, not action-bar traffic"
            ),
        },
        "blockers": blockers,
    }

    options.output.mkdir(parents=True, exist_ok=True)
    write_json(options.output / "native-character-creation-v1-data.json", bundle)
    write_json(options.output / "native-character-creation-v1-manifest.json", manifest)
    print(json.dumps({
        "output": str(options.output.resolve()),
        "deployable": manifest["deployable"],
        "table_counts": manifest["table_counts"],
        "blockers": [blocker["code"] for blocker in blockers],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
