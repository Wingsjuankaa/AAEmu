#!/usr/bin/env python3
"""Build the AA8 native equipment catalogue from confirmed client sources.

The script never mutates its inputs.  It copies the current native-combat
runtime and replaces only the item/equipment domain with rows recovered from
the AA 8.0.3.12 client.  The resulting database remains a candidate until all
blocked configuration/layout dependencies listed in the manifest are closed.
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


ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"


def load_cache_parser():
    spec = importlib.util.spec_from_file_location("aa8_cached_result", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


TABLES: dict[str, dict[str, Any]] = {
    "item_weapons": {
        "columns": "id item_id asset_id base_enchantable base_equipment charge_count charge_lifetime drawn_scale durability_multiplier eiset_id enhanced_item_material_id fixed_attacked_sound_id fixed_visual_effect_id holdable_id item_rnd_attr_category_id mod_set_id or_unit_reqs recharge_buff_id recharge_restrict_item_id recharge_rnd_attr_unit_modifier_restrict_item_id repairable rnd_attr_unit_modifier_lifetime skin_kind_id useAsStat worn_scale".split(),
        "layout": "68 68 68 38 38 68 68 60 68 68 68 68 68 68 68 68 38 68 68 68 38 68 68 38 60".split(),
        "anchor_id": 4,
        "anchor": {"item_id": 7},
        "expected": 6584,
    },
    "item_armors": {
        "columns": "id item_id asset2_id asset_id base_enchantable base_equipment charge_count charge_lifetime durability_multiplier eiset_id enhanced_item_material_id equip_only_has_armor_visual invisible_asset item_rnd_attr_category_id mod_set_id no_visual_error_message or_unit_reqs recharge_buff_id recharge_restrict_item_id recharge_rnd_attr_unit_modifier_restrict_item_id repairable rnd_attr_unit_modifier_lifetime skin_kind_id slot_type_id type_id useAsStat".split(),
        "layout": "68 68 68 68 38 38 68 68 68 68 68 38 38 68 68 78 38 68 68 68 38 68 68 68 68 38".split(),
        "anchor_id": 188,
        "anchor": {"item_id": 1177},
        "expected": 11604,
    },
    "item_accessories": {
        "columns": "id item_id charge_count charge_lifetime durability_multiplier eiset_id item_rnd_attr_category_id mod_set_id or_unit_reqs recharge_buff_id recharge_restrict_item_id recharge_rnd_attr_unit_modifier_restrict_item_id repairable rnd_attr_unit_modifier_lifetime slot_type_id type_id".split(),
        "layout": "68 68 68 68 68 68 68 68 38 68 68 68 38 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"item_id": 2963},
        "expected": 642,
    },
    "equip_item_attr_modifiers": {
        "columns": "id alias dex_weight int_weight spi_weight sta_weight str_weight".split(),
        "layout": "68 78 68 68 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"dex_weight": 3, "str_weight": 5},
        "expected": 120,
    },
    "equip_slot_group_maps": {
        "columns": "id equip_slot_group_id equip_slot_type_id".split(),
        "layout": "68 68 68".split(),
        "anchor_id": 3,
        "anchor": {"equip_slot_group_id": 2, "equip_slot_type_id": 16},
        "expected": 138,
    },
    "holdables": {
        "columns": "id angle anim_l1_ratio anim_l1_id anim_l2_ratio anim_l2_id anim_l3_id anim_r1_ratio anim_r1_id anim_r2_ratio anim_r2_id anim_r3_id damage_scale durability_ratio element_id enchanted_dps1000 formula_armor formula_dps formula_hdps formula_magic_resist formula_mdps gear_score_multiplier item_proc_id max_range min_range name pose_id renew_category sheathe_priority slot_type_id sound_material_id speed stat_multiplier".split(),
        "layout": "68 68 68 68 68 68 68 68 68 68 68 68 68 60 68 68 78 78 78 78 78 68 68 68 68 78 68 68 68 68 68 68 68".split(),
        "anchor_id": 3,
        "anchor": {"angle": 90, "slot_type_id": 16, "element_id": 2},
        "expected": 32,
    },
    "wearable_kinds": {
        "columns": "armor_type_id durability_ratio full_buff_id half_buff_id sound_material_id".split(),
        "layout": "68 60 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"full_buff_id": 716},
        "expected": 5,
    },
    "wearable_slots": {
        "columns": "id coverage gear_score_multiplier slot_type_id".split(),
        "layout": "68 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"coverage": 4, "slot_type_id": 2},
        "expected": 16,
    },
    "item_grades": {
        "columns": "id color_argb durability_value grade_order icon_id name refund_multiplier stat_multiplier upgrade_ratio var_holdable_armor var_holdable_dps var_holdable_heal_dps var_holdable_magic_dps var_holdable_magic_resist var_wearable_armor var_wearable_magic_resistance".split(),
        "layout": "68 78 60 68 68 78 68 68 68 60 60 60 60 60 60 60".split(),
        "anchor_id": 2,
        "anchor": {"grade_order": 2, "stat_multiplier": 108},
        "expected": 13,
    },
    "item_procs": {
        "columns": "id chance_kind_id chance_param chance_rate cooldown_sec description finisher item_level_based_chance_bonus or_unit_reqs skill_id trigger_skill_id trigger_tag_id".split(),
        "layout": "68 68 68 68 68 78 38 68 38 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"chance_kind_id": 9, "chance_rate": 5},
        "expected": 199,
    },
    "equip_item_set_bonuses": {
        "columns": "id buff_id equip_item_set_id num_pieces proc_id".split(),
        "layout": "68 68 68 68 68".split(),
        "anchor_id": 80,
        "anchor": {"buff_id": 3963, "equip_item_set_id": 2},
        "expected": 938,
    },
    "item_proc_bindings": {
        "columns": "id item_id proc_id".split(),
        "layout": "68 68 68".split(),
        "anchor_id": 80,
        "anchor": {"item_id": 1690, "proc_id": 22},
        "expected": 186,
    },
    "item_set_items": {
        "columns": "id count item_set_id item_id".split(),
        "layout": "68 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"count": 5, "item_set_id": 2},
        "expected": 735,
    },
    "item_grade_buffs": {
        "columns": "id buff_id item_grade_id item_id".split(),
        "layout": "68 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"buff_id": 28005, "item_grade_id": 2, "item_id": 27457},
        "expected": 103,
    },
    "armor_grade_buffs": {
        "columns": "id armor_type_id buff_id item_grade_id".split(),
        "layout": "68 68 68 68".split(),
        "anchor_id": 2,
        "anchor": {"armor_type_id": 1, "buff_id": 6419, "item_grade_id": 5},
        "expected": 33,
    },
}


SPECIAL_RESULTS = {
    "wearable_armor": {
        "start": 0xB62,
        "columns": ["armor_bp", "armor_type_id", "slot_type_id"],
        "layout": ["68", "68", "68"],
        "expected": 71,
    },
    "wearable_magic": {
        "start": 0xEFE,
        "columns": ["magic_resistance_bp", "armor_type_id", "slot_type_id"],
        "layout": ["68", "68", "68"],
        "expected": 71,
    },
    "equip_slot_groups": {
        "start": 0x46C2624,
        "columns": ["id", "pet_only"],
        "layout": ["68", "38"],
        "expected": 47,
    },
    "equip_item_sets": {
        # The short result at 0x649BB68 is a different three-column table
        # with a coincidentally compatible layout.  The native
        # `SELECT id, name, wear FROM equip_item_sets` result is the 495-row
        # range below; it contains the modern set ids referenced by active
        # AA8 equipment (for example 519).
        "start": 0x46BD05C,
        "columns": ["id", "name", "wear"],
        "layout": ["68", "78", "38"],
        "expected": 495,
    },
    "item_sets": {
        # Immediately follows the native item_set_items result.  The layout
        # is confirmed by the embedded `SELECT id, kind_id FROM item_sets`.
        "start": 0x80B9A0F,
        "columns": ["id", "kind_id"],
        "layout": ["68", "68"],
        "expected": 247,
    },
    "item_backpacks": {
        "start": 0x56910CF,
        "columns": "id item_id asset2_id asset_id backpack_type_id declare_siege_zone_group_id freshness_group_id glider_anim_action_id glider_fast_anim_action_id glider_sliding_anim_action_id glider_slow_anim_action_id heavy skin_kind_id storage_visual use_as_stat".split(),
        "layout": "68 68 68 68 68 68 68 68 68 68 68 38 68 78 38".split(),
        "expected": 1168,
    },
    "item_body_parts": {
        "start": 0x5766210,
        "columns": "item_id asset_1_id asset_2_id asset_3_id asset_4_id asset_id custom_texture_id custom_texture_1_id custom_texture_2_id custom_texture_3_id custom_texture_4_id face_mask hair_base left_eye_height left_eye_width left_eye_x left_eye_y model_id npc_only odd_eye right_eye_height right_eye_width right_eye_x right_eye_y slot_type_id".split(),
        "layout": (["68"] * 11) + ["78", "78"] + (["68"] * 5) + ["38", "38"] + (["68"] * 5),
        "expected": 718,
    },
    "wearable_formulas": {
        "start": 0x3F71CF7,
        "columns": ["kind_id", "formula"],
        "layout": ["68", "78"],
        "expected": 2,
    },
}

ITEM_CONFIG_COLUMNS = [
    "durability_decrement_chance",
    "durability_repair_cost_factor",
    "durability_const",
    "holdable_durability_const",
    "wearable_durability_const",
    "death_durability_loss_ratio",
    "item_stat_const",
    "holdable_stat_const",
    "wearable_stat_const",
    "stat_value_const",
]
ITEM_CONFIG_LAYOUT = ["60", "60", "60", "60", "60", "68", "68", "68", "68", "68"]


SQL_TYPES = {"38": "INTEGER", "40": "INTEGER", "68": "INTEGER", "70": "INTEGER", "60": "REAL", "78": "TEXT"}

# Confirmed from the holdables cached result in Kakao r558734.  The first
# newly interned value is the holdable name at reference 157353; subsequent
# formula fields reuse those references.  Starting at 157354 shifts every
# value by one and turns valid formulas into unrelated strings.
HOLDABLE_FIRST_STRING_REFERENCE = 157353
HOLDABLE_FORMULA_FIELDS = (
    "formula_armor",
    "formula_dps",
    "formula_hdps",
    "formula_magic_resist",
    "formula_mdps",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--unit-modifiers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def rows_at(parser, reader, spec):
    raw, end = parser.read_cached_result(reader, spec["start"], spec["layout"])
    rows = [dict(zip(spec["columns"], row)) for row in raw]
    if len(rows) != spec["expected"]:
        raise RuntimeError(f"{spec}: expected {spec['expected']} rows, got {len(rows)}")
    return rows, {"start": spec["start"], "end": end, "rows": len(rows)}


def create_table(connection: sqlite3.Connection, name: str, columns: list[str], layout: list[str]) -> None:
    definition = ", ".join(f'"{column}" {SQL_TYPES[field]}' for column, field in zip(columns, layout))
    connection.execute(f'DROP TABLE IF EXISTS "{name}"')
    connection.execute(f'CREATE TABLE "{name}" ({definition})')


def insert_rows(connection: sqlite3.Connection, name: str, columns: list[str], rows: list[dict[str, Any]]) -> None:
    names = ", ".join(f'"{column}"' for column in columns)
    values = ", ".join("?" for _ in columns)
    connection.executemany(
        f'INSERT INTO "{name}" ({names}) VALUES ({values})',
        ([row.get(column) for column in columns] for row in rows),
    )


def filter_runtime_closure(
    native_items: list[dict[str, Any]],
    extracted: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Keep only concrete rows reachable from the AA8 client item catalogue.

    The client database deliberately retains thousands of obsolete concrete
    weapon/armor rows whose base item no longer exists.  They are native
    archaeological data, but they are not part of the enabled AA8 catalogue
    and must not become creatable server definitions.
    """

    active_item_ids = {int(row["id"]) for row in native_items}
    runtime_tables = {name: list(rows) for name, rows in extracted.items()}
    filtered: dict[str, int] = {}

    for table in (
        "item_weapons",
        "item_armors",
        "item_accessories",
        "item_backpacks",
        "item_proc_bindings",
        "item_grade_buffs",
        "item_set_items",
    ):
        original = runtime_tables[table]
        runtime_tables[table] = [
            row for row in original if int(row["item_id"]) in active_item_ids
        ]
        filtered[table] = len(original) - len(runtime_tables[table])

    equip_set_ids = {
        int(row["id"]) for row in runtime_tables["equip_item_sets"]
    }
    original_bonuses = runtime_tables["equip_item_set_bonuses"]
    runtime_tables["equip_item_set_bonuses"] = [
        row for row in original_bonuses
        if int(row["equip_item_set_id"]) in equip_set_ids
    ]
    filtered["equip_item_set_bonuses"] = (
        len(original_bonuses) - len(runtime_tables["equip_item_set_bonuses"])
    )

    item_set_ids = {int(row["id"]) for row in runtime_tables["item_sets"]}
    original_set_items = runtime_tables["item_set_items"]
    runtime_tables["item_set_items"] = [
        row for row in original_set_items
        if int(row["item_set_id"]) in item_set_ids
    ]
    filtered["item_set_items_missing_set"] = (
        len(original_set_items) - len(runtime_tables["item_set_items"])
    )

    slot_group_ids = {
        int(row["id"]) for row in runtime_tables["equip_slot_groups"]
    }
    original_slot_maps = runtime_tables["equip_slot_group_maps"]
    runtime_tables["equip_slot_group_maps"] = [
        row for row in original_slot_maps
        if int(row["equip_slot_group_id"]) in slot_group_ids
    ]
    filtered["equip_slot_group_maps"] = (
        len(original_slot_maps) - len(runtime_tables["equip_slot_group_maps"])
    )

    return runtime_tables, {
        "active_item_ids": len(active_item_ids),
        "excluded_unreachable_native_rows": filtered,
    }


def validate_runtime_closure(
    connection: sqlite3.Connection,
    item_modifier_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    checks = {
        "weapon_without_item": """
            SELECT COUNT(*) FROM item_weapons
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "armor_without_item": """
            SELECT COUNT(*) FROM item_armors
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "accessory_without_item": """
            SELECT COUNT(*) FROM item_accessories
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "backpack_without_item": """
            SELECT COUNT(*) FROM item_backpacks
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "weapon_without_holdable": """
            SELECT COUNT(*) FROM item_weapons
            WHERE holdable_id NOT IN (SELECT id FROM holdables)
        """,
        "armor_without_wearable_slot": """
            SELECT COUNT(*) FROM item_armors
            WHERE slot_type_id NOT IN (SELECT slot_type_id FROM wearable_slots)
        """,
        "accessory_without_wearable_slot": """
            SELECT COUNT(*) FROM item_accessories
            WHERE slot_type_id NOT IN (SELECT slot_type_id FROM wearable_slots)
        """,
        "equipment_bonus_without_set": """
            SELECT COUNT(*) FROM equip_item_set_bonuses
            WHERE equip_item_set_id NOT IN (SELECT id FROM equip_item_sets)
        """,
        "item_set_entry_without_set": """
            SELECT COUNT(*) FROM item_set_items
            WHERE item_set_id NOT IN (SELECT id FROM item_sets)
        """,
        "item_set_entry_without_item": """
            SELECT COUNT(*) FROM item_set_items
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "proc_binding_without_item": """
            SELECT COUNT(*) FROM item_proc_bindings
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "grade_buff_without_item": """
            SELECT COUNT(*) FROM item_grade_buffs
            WHERE item_id NOT IN (SELECT id FROM items)
        """,
        "slot_map_without_group": """
            SELECT COUNT(*) FROM equip_slot_group_maps
            WHERE equip_slot_group_id NOT IN (SELECT id FROM equip_slot_groups)
        """,
    }
    results = {
        name: int(connection.execute(sql).fetchone()[0])
        for name, sql in checks.items()
    }

    active_items = {
        int(row[0]) for row in connection.execute("SELECT id FROM items")
    }
    active_armors = {
        int(row[0]) for row in connection.execute("SELECT id FROM item_armors")
    }
    results["item_unit_modifier_without_owner"] = sum(
        1 for row in item_modifier_rows
        if (
            row["owner_type"] == "Item"
            and int(row["owner_id"]) not in active_items
        ) or (
            row["owner_type"] == "ItemArmor"
            and int(row["owner_id"]) not in active_armors
        )
    )
    # AA8 loads body-part definitions from their own cached result.  Many
    # valid face/nude/hair definitions intentionally have no row in the
    # general items result, but ItemManager can still construct their
    # BodyPartTemplate directly.  Treat this as an explicit native topology,
    # not as an orphaned gameplay item.
    informational = {
        "body_parts_without_general_item": int(
            connection.execute(
                """
                SELECT COUNT(*) FROM item_body_parts
                WHERE item_id NOT IN (SELECT id FROM items)
                """
            ).fetchone()[0]
        )
    }
    return {
        "checks": results,
        "informational": informational,
        "ok": all(value == 0 for value in results.values()),
    }


def main() -> int:
    options = args()
    parser = load_cache_parser()
    reader = parser.CachedResultReader(options.game11.read_bytes())
    extracted: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, Any] = {}

    for table, spec in TABLES.items():
        rows, source_range = parser.locate_cached_result(
            reader, spec["columns"], spec["layout"], spec["anchor_id"], spec["anchor"]
        )
        if len(rows) != spec["expected"]:
            raise RuntimeError(f"{table}: expected {spec['expected']} rows, got {len(rows)}")
        extracted[table] = rows
        ranges[table] = source_range

    special = {}
    for name, spec in SPECIAL_RESULTS.items():
        special[name], ranges[name] = rows_at(parser, reader, spec)

    # Re-read the two adjacent native results while reproducing x2game's
    # result-string cache.  The first pass above deliberately remains
    # cache-neutral so locating unrelated cached results cannot alter the
    # reference sequence.  wearable_formulas immediately follows holdables
    # and its second row references the formula interned by its first row.
    holdable_spec = TABLES["holdables"]
    reader.begin_string_cache_capture(HOLDABLE_FIRST_STRING_REFERENCE)
    raw_holdables, holdable_end = parser.read_cached_result(
        reader,
        ranges["holdables"]["start"],
        holdable_spec["layout"],
    )
    extracted["holdables"] = [
        dict(zip(holdable_spec["columns"], row)) for row in raw_holdables
    ]
    special["wearable_formulas"], wearable_formula_range = rows_at(
        parser,
        reader,
        SPECIAL_RESULTS["wearable_formulas"],
    )
    string_cache = reader.end_string_cache_capture()
    ranges["holdables"]["end"] = holdable_end
    ranges["wearable_formulas"] = wearable_formula_range

    unresolved_formulas = [
        {
            "table": "holdables",
            "id": row["id"],
            "field": field,
            "value": row[field],
        }
        for row in extracted["holdables"]
        for field in HOLDABLE_FORMULA_FIELDS
        if isinstance(row[field], str) and row[field].startswith("<ref:")
    ]
    unresolved_formulas.extend(
        {
            "table": "wearable_formulas",
            "id": row["kind_id"],
            "field": "formula",
            "value": row["formula"],
        }
        for row in special["wearable_formulas"]
        if isinstance(row["formula"], str) and row["formula"].startswith("<ref:")
    )
    if unresolved_formulas:
        raise RuntimeError(
            "Native equipment formulas still contain unresolved string-cache "
            f"references: {unresolved_formulas}"
        )

    # This single-row result is followed immediately by the next cached
    # result instead of SQLITE_DONE. The layout is confirmed by
    # FUN_39879f80 in x2game.dll. Structural bounds produce exactly one
    # candidate in r558734 game11 and avoid assuming any individual value.
    config_candidates = []
    for offset, marker in enumerate(reader.data):
        if marker != 100:
            continue
        try:
            values, end = reader.row(offset, ITEM_CONFIG_LAYOUT)
        except (IndexError, ValueError):
            continue
        real_values = values[:5]
        integer_values = values[5:]
        if (
            all(0.1 <= value <= 1000 for value in real_values)
            and 0 <= integer_values[0] <= 100
            and all(1 <= value <= 10000 for value in integer_values[1:])
        ):
            config_candidates.append((offset, end, values))
    if len(config_candidates) != 1:
        raise RuntimeError(f"Expected one structurally valid item_configs row, got {len(config_candidates)}")
    config_start, config_end, config_values = config_candidates[0]
    extracted["item_configs"] = [dict(zip(ITEM_CONFIG_COLUMNS, config_values))]
    ranges["item_configs"] = {
        "start": config_start,
        "end": config_end,
        "rows": 1,
        "layout_source": "x2game.dll FUN_39879f80",
    }

    wearable_magic = {
        (row["armor_type_id"], row["slot_type_id"]): row["magic_resistance_bp"]
        for row in special["wearable_magic"]
    }
    extracted["wearables"] = [
        {
            **row,
            "magic_resistance_bp": wearable_magic[(row["armor_type_id"], row["slot_type_id"])],
        }
        for row in special["wearable_armor"]
    ]
    extracted["equip_slot_groups"] = special["equip_slot_groups"]
    extracted["equip_item_sets"] = special["equip_item_sets"]
    extracted["item_sets"] = special["item_sets"]
    extracted["item_backpacks"] = special["item_backpacks"]
    extracted["item_body_parts"] = special["item_body_parts"]
    extracted["wearable_formulas"] = special["wearable_formulas"]

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(options.base_runtime, temporary)

    client = sqlite3.connect(f"file:{options.client_compact.resolve().as_posix()}?mode=ro", uri=True)
    client.row_factory = sqlite3.Row
    runtime = sqlite3.connect(temporary)
    try:
        runtime.execute("PRAGMA foreign_keys = OFF")
        runtime.execute("BEGIN IMMEDIATE")

        # The reconstructed compact contains the item result loaded by AA8.
        # Concrete tables also retain obsolete rows, so only definitions whose
        # base item exists enter the enabled runtime closure. The signed anomaly
        # is deliberately excluded and recorded rather than uint-cast.
        item_sql = client.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='items'"
        ).fetchone()[0]
        native_items = [dict(row) for row in client.execute("SELECT * FROM items WHERE id >= 0")]
        signed_anomalies = [dict(row) for row in client.execute("SELECT * FROM items WHERE id < 0")]
        runtime.execute('DROP TABLE IF EXISTS "items"')
        runtime.execute(item_sql)
        item_columns = [row[1] for row in runtime.execute("PRAGMA table_info(items)")]
        insert_rows(runtime, "items", item_columns, native_items)

        runtime_tables, closure_filter = filter_runtime_closure(native_items, extracted)

        for table, spec in TABLES.items():
            create_table(runtime, table, spec["columns"], spec["layout"])
            insert_rows(runtime, table, spec["columns"], runtime_tables[table])

        create_table(
            runtime,
            "wearables",
            ["armor_bp", "magic_resistance_bp", "armor_type_id", "slot_type_id"],
            ["68", "68", "68", "68"],
        )
        insert_rows(
            runtime,
            "wearables",
            ["armor_bp", "magic_resistance_bp", "armor_type_id", "slot_type_id"],
            runtime_tables["wearables"],
        )
        create_table(runtime, "equip_slot_groups", ["id", "pet_only"], ["68", "38"])
        insert_rows(runtime, "equip_slot_groups", ["id", "pet_only"], runtime_tables["equip_slot_groups"])
        create_table(runtime, "equip_item_sets", ["id", "name", "wear"], ["68", "78", "38"])
        insert_rows(runtime, "equip_item_sets", ["id", "name", "wear"], runtime_tables["equip_item_sets"])
        create_table(runtime, "item_sets", ["id", "kind_id"], ["68", "68"])
        insert_rows(runtime, "item_sets", ["id", "kind_id"], runtime_tables["item_sets"])
        create_table(
            runtime, "item_backpacks",
            SPECIAL_RESULTS["item_backpacks"]["columns"],
            SPECIAL_RESULTS["item_backpacks"]["layout"],
        )
        insert_rows(
            runtime, "item_backpacks",
            SPECIAL_RESULTS["item_backpacks"]["columns"],
            runtime_tables["item_backpacks"],
        )
        create_table(
            runtime, "item_body_parts",
            SPECIAL_RESULTS["item_body_parts"]["columns"],
            SPECIAL_RESULTS["item_body_parts"]["layout"],
        )
        insert_rows(
            runtime, "item_body_parts",
            SPECIAL_RESULTS["item_body_parts"]["columns"],
            runtime_tables["item_body_parts"],
        )
        create_table(runtime, "wearable_formulas", ["kind_id", "formula"], ["68", "78"])
        insert_rows(runtime, "wearable_formulas", ["kind_id", "formula"], runtime_tables["wearable_formulas"])

        modifier_document = json.loads(options.unit_modifiers.read_text(encoding="utf-8"))
        modifier_candidates = [
            row for row in modifier_document["rows"]
            if row["owner_type"] in ("Item", "ItemArmor")
        ]
        active_item_ids = {int(row["id"]) for row in native_items}
        active_armor_definition_ids = {
            int(row["id"]) for row in runtime_tables["item_armors"]
        }
        modifiers = [
            row for row in modifier_candidates
            if (
                row["owner_type"] == "Item"
                and int(row["owner_id"]) in active_item_ids
            ) or (
                row["owner_type"] == "ItemArmor"
                and int(row["owner_id"]) in active_armor_definition_ids
            )
        ]
        runtime.execute(
            "DELETE FROM unit_modifiers WHERE owner_type IN ('Item', 'ItemArmor')"
        )
        modifier_columns = modifier_document["columns"]
        insert_rows(runtime, "unit_modifiers", modifier_columns, modifiers)

        runtime.execute("DROP TABLE IF EXISTS item_configs")
        runtime.execute(
            "CREATE TABLE item_configs (" +
            ", ".join(
                f'"{column}" {"REAL" if index < 5 else "INTEGER"}'
                for index, column in enumerate(ITEM_CONFIG_COLUMNS)
            ) +
            ")"
        )
        insert_rows(runtime, "item_configs", ITEM_CONFIG_COLUMNS, extracted["item_configs"])

        runtime.execute(
            """CREATE TABLE IF NOT EXISTS aaemu_item_definition_coverage (
                   item_id INTEGER PRIMARY KEY,
                   concrete_type TEXT NOT NULL,
                   coverage TEXT NOT NULL,
                   missing_dependencies TEXT NOT NULL,
                   provenance TEXT NOT NULL
               )"""
        )
        runtime.execute("DELETE FROM aaemu_item_definition_coverage")
        concrete: dict[int, str] = {}
        for table, kind in (("item_weapons", "weapon"), ("item_armors", "armor"), ("item_accessories", "accessory")):
            for row in runtime_tables[table]:
                concrete[int(row["item_id"])] = kind
        coverage_rows = []
        for row in runtime_tables["item_backpacks"]:
            concrete[int(row["item_id"])] = "backpack"
        for row in runtime_tables["item_body_parts"]:
            concrete[int(row["item_id"])] = "body_part"
        for item in native_items:
            item_id = int(item["id"])
            kind = concrete.get(item_id, "generic")
            # In AA8, impl_id=0 is the concrete generic Item implementation,
            # not a missing subtype. Coinpurses and unidentified equipment
            # containers intentionally use it and execute through
            # items.use_skill_id.
            native_generic = kind == "generic" and int(item["impl_id"]) == 0
            complete = (
                kind in ("weapon", "armor", "accessory", "backpack", "body_part")
                or native_generic
            )
            coverage_rows.append(
                (
                    item_id,
                    kind,
                    "phase_a_candidate" if complete else "catalog_only",
                    "phase_a_runtime_validation" if complete else "concrete_type_not_recovered",
                    (
                        "client_compact_8"
                        if native_generic
                        else "client_compact_8+game11_native"
                    )
                    if complete
                    else "client_compact_8",
                )
            )
        native_item_ids = {int(item["id"]) for item in native_items}
        for row in runtime_tables["item_body_parts"]:
            item_id = int(row["item_id"])
            if item_id in native_item_ids:
                continue
            coverage_rows.append(
                (
                    item_id,
                    "body_part",
                    "phase_a_candidate",
                    "phase_a_runtime_validation",
                    "game11_native+server_derived",
                )
            )
        runtime.executemany(
            "INSERT INTO aaemu_item_definition_coverage VALUES (?, ?, ?, ?, ?)",
            coverage_rows,
        )
        closure_validation = validate_runtime_closure(runtime, modifiers)
        runtime.commit()
        quick = runtime.execute("PRAGMA quick_check").fetchone()[0]
        integrity = runtime.execute("PRAGMA integrity_check").fetchone()[0]
    except Exception:
        runtime.rollback()
        raise
    finally:
        client.close()
        runtime.close()

    temporary.replace(options.output)
    manifest = {
        "format_version": 1,
        "authority": [
            "compact-client-8.0-decrypted.sqlite",
            "game11_native",
            "x2game_confirmed",
        ],
        "inputs": {
            "client_compact": {"path": str(options.client_compact), "sha256": sha256(options.client_compact)},
            "game11": {"path": str(options.game11), "sha256": sha256(options.game11)},
            "base_runtime": {"path": str(options.base_runtime), "sha256": sha256(options.base_runtime)},
            "unit_modifiers": {"path": str(options.unit_modifiers), "sha256": sha256(options.unit_modifiers)},
        },
        "output": {"path": str(options.output), "sha256": sha256(options.output)},
        "validation": {"quick_check": quick, "integrity_check": integrity},
        "counts": {
            "items": len(native_items),
            **{table: len(rows) for table, rows in runtime_tables.items()},
            "raw_native_rows": {
                table: len(rows) for table, rows in extracted.items()
            },
            "item_unit_modifiers": len(modifiers),
        },
        "closure_filter": closure_filter,
        "closure_validation": closure_validation,
        "source_ranges": ranges,
        "string_cache": {
            "source": "game11_native+x2game_confirmed",
            "first_reference": HOLDABLE_FIRST_STRING_REFERENCE,
            "last_reference": max(string_cache),
            "captured_values": len(string_cache),
            "unresolved_equipment_formulas": len(unresolved_formulas),
        },
        "signed_item_id_anomalies": signed_anomalies,
        "blocked_dependencies": [
            {
                "dependency": "remaining_item_concrete_types",
                "reason": "consumables and additional concrete item families have not yet been recovered",
                "deployment_blocking": True,
            },
            {
                "dependency": "phase_b_item_details",
                "reason": "sockets/temper/synthesis/awakening remain outside Phase A",
                "deployment_blocking": False,
            },
        ],
        "deployable": False,
        "provenance": {
            "items": "client_compact_8",
            "equipment_tables": "game11_native",
            "unit_modifiers": "game11_native",
            "coverage": "server_derived",
        },
    }
    options.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(options.output), "sha256": manifest["output"]["sha256"], "deployable": False}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
