#!/usr/bin/env python3
"""Extract the AA8 unit_modifiers cached result from game11.

The layout and SQL order are confirmed by x2game.dll function FUN_3997ab60.
No historical compact is accepted as an input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from extract_battlerage_manifest import CachedResultReader, read_cached_result  # noqa: E402


COLUMNS = [
    "owner_type",
    "owner_id",
    "dynamic_value",
    "linear_level_bonus",
    "unit_attribute_id",
    "unit_modifier_type_id",
    "value",
]
LAYOUT = ["78", "68", "68", "68", "68", "68", "40"]
FIRST_STRING_REFERENCE = 69859
EXPECTED_ROWS = 49095
EXPECTED_STRING_CACHE = {
    69859: "Buff",
    69860: "Item",
    69861: "ItemArmor",
    69862: "Slave",
    69863: "BuffUnitModifier",
    69864: "Housing",
    69865: "DamageEffect",
    69866: "EquipSlotReinforceSetEffect",
    69867: "HealEffect",
    69868: "CombatResource",
    69869: "Buffs",
    69870: "EquipSlotReinforceBundleEffect",
    69871: "ExpeditionBuffGrade",
}
FIRST_ROW = {
    "owner_type": "Buff",
    "owner_id": 15,
    "dynamic_value": 0,
    "linear_level_bonus": 0,
    "unit_attribute_id": 8,
    "unit_modifier_type_id": 0,
    "value": 400,
}
BATTLE_FOCUS = {
    404: {(81, 280), (17, 150)},
    7651: {(81, 300), (17, 200)},
    13612: {(81, 320), (17, 250)},
    13613: {(81, 340), (17, 300)},
}

VISIBLE_COMBAT_STATS = {
    "melee_accuracy": {
        "base_attribute": 18,
        "multiplier_attribute": 78,
        "server_property": "MeleeAccuracy",
        "consumer": "Skill.RollCombatDice",
    },
    "ranged_accuracy": {
        "base_attribute": 23,
        "multiplier_attribute": 83,
        "server_property": "RangedAccuracy",
        "consumer": "Skill.RollCombatDice",
    },
    "spell_accuracy": {
        "base_attribute": 28,
        "multiplier_attribute": 88,
        "server_property": "SpellAccuracy",
        "consumer": "Skill.RollCombatDice",
    },
    "melee_critical": {
        "base_attribute": 16,
        "multiplier_attribute": 77,
        "server_property": "MeleeCritical",
        "consumer": "DamageEffect",
    },
    "ranged_critical": {
        "base_attribute": 25,
        "multiplier_attribute": 82,
        "server_property": "RangedCritical",
        "consumer": "DamageEffect",
    },
    "spell_critical": {
        "base_attribute": 30,
        "multiplier_attribute": 86,
        "server_property": "SpellCritical",
        "consumer": "DamageEffect",
    },
    "heal_critical": {
        "base_attribute": 174,
        "multiplier_attribute": 185,
        "server_property": "HealCritical",
        "consumer": "HealEffect",
    },
    "melee_critical_damage": {
        "base_attribute": 17,
        "multiplier_attribute": None,
        "server_property": "MeleeCriticalBonus",
        "consumer": "DamageEffect",
    },
    "melee_parry": {
        "base_attribute": 22,
        "multiplier_attribute": 81,
        "server_property": "MeleeParryRate",
        "consumer": "Skill.RollCombatDice",
    },
    "ranged_parry": {
        "base_attribute": 153,
        "multiplier_attribute": 154,
        "server_property": "RangedParryRate",
        "consumer": "Skill.RollCombatDice",
    },
    "block": {
        "base_attribute": 177,
        "multiplier_attribute": 179,
        "server_property": "BlockRate",
        "consumer": "Skill.RollCombatDice",
    },
    "dodge": {
        "base_attribute": 178,
        "multiplier_attribute": 180,
        "server_property": "DodgeRate",
        "consumer": "Skill.RollCombatDice",
    },
}

VISIBLE_STAT_GROUPS = {
    "primary_attributes": {
        "ui_fields": ["strength", "agility", "stamina", "intelligence", "spirit"],
        "attribute_ids": [0, 1, 2, 3, 4],
        "formula_status": "server_reference_pending_x2game_reconstruction",
    },
    "attack_power": {
        "ui_fields": ["melee_attack", "ranged_attack", "magic_attack", "healing_power"],
        "attribute_ids": [96, 33, 98, 34, 87, 35, 173, 175],
        "server_properties": ["Dps", "DpsInc", "RangedDps", "RangedDpsInc", "MDps", "MDpsInc", "HDps", "HDpsInc"],
        "formula_status": "server_reference_pending_x2game_reconstruction",
    },
    "defense": {
        "ui_fields": ["physical_defense", "magic_defense"],
        "attribute_ids": [8, 64],
        "server_properties": ["Armor", "MagicResistance"],
        "formula_status": "server_reference_pending_x2game_reconstruction",
    },
    "speeds": {
        "ui_fields": ["move_speed", "cast_time", "attack_speed"],
        "attribute_ids": [10, 71, 54, 55, 119, 218],
        "server_properties": ["MoveSpeed", "CastTimeMul"],
        "formula_status": "attack_speed_consumer_pending",
    },
    "critical_defense": {
        "ui_fields": ["resilience", "received_critical_rate", "received_critical_damage", "toughness"],
        "attribute_ids": [182, 183],
        "server_properties": ["BattleResist", "Flexibility"],
        "formula_status": "client_ui_semantics_pending_protocol_validation",
    },
    "incoming_damage": {
        "ui_fields": [
            "received_melee_damage",
            "received_ranged_damage",
            "received_magic_damage",
            "received_siege_damage",
            "fixed_melee_reduction",
            "fixed_ranged_reduction",
            "fixed_magic_reduction",
        ],
        "attribute_ids": [58, 142, 143, 144, 145, 146, 147, 148, 149],
        "server_properties": [
            "IncomingDamageMul",
            "IncomingMeleeDamageMul",
            "IncomingRangedDamageMul",
            "IncomingSpellDamageMul",
        ],
        "formula_status": "server_consumers_present",
    },
    "incoming_pve_damage": {
        "ui_fields": [
            "received_pve_damage",
            "fixed_pve_melee_reduction",
            "fixed_pve_ranged_reduction",
            "fixed_pve_magic_reduction",
        ],
        "attribute_ids": [199, 200, 201, 202],
        "formula_status": "native_modifiers_loaded_consumer_pending",
    },
    "penetration": {
        "ui_fields": ["defense_penetration", "magic_penetration"],
        "attribute_ids": [57, 184],
        "server_properties": ["DefensePenetration", "MagicPenetration"],
        "formula_status": "server_consumers_present",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def locate_start(data: bytes) -> int:
    pattern = (
        b"\x64\x01\xff\xff\xff\xffBuff\x00"
        + struct.pack("<iiiii", 15, 0, 0, 8, 0)
        + struct.pack("<q", 400)
    )
    matches = []
    cursor = 0
    while True:
        cursor = data.find(pattern, cursor)
        if cursor < 0:
            break
        matches.append(cursor)
        cursor += 1
    if len(matches) != 1:
        raise RuntimeError(f"Expected one native unit_modifiers result, found {len(matches)}")
    return matches[0]


def extract(path: Path) -> tuple[list[dict[str, Any]], dict[int, str], int, int]:
    data = path.read_bytes()
    start = locate_start(data)
    reader = CachedResultReader(data)
    reader.begin_string_cache_capture(FIRST_STRING_REFERENCE)
    raw_rows, end = read_cached_result(reader, start, LAYOUT)
    string_cache = reader.end_string_cache_capture()
    rows = [dict(zip(COLUMNS, values)) for values in raw_rows]
    return rows, string_cache, start, end


def validate(rows: list[dict[str, Any]], string_cache: dict[int, str]) -> dict[str, Any]:
    errors: list[str] = []
    if len(rows) != EXPECTED_ROWS:
        errors.append(f"rows={len(rows)}, expected={EXPECTED_ROWS}")
    if rows[0] != FIRST_ROW:
        errors.append(f"first row mismatch: {rows[0]}")
    if string_cache != EXPECTED_STRING_CACHE:
        errors.append(f"string cache mismatch: {string_cache}")

    for buff_id, expected in BATTLE_FOCUS.items():
        actual = {
            (int(row["unit_attribute_id"]), int(row["value"]))
            for row in rows
            if row["owner_type"] == "Buff"
            and int(row["owner_id"]) == buff_id
            and int(row["dynamic_value"]) == 0
        }
        if actual != expected:
            errors.append(f"Battle Focus buff {buff_id}: {sorted(actual)}")

    dynamic_rows = [row for row in rows if int(row["dynamic_value"]) != 0]
    dynamic_attributes = Counter(int(row["unit_attribute_id"]) for row in dynamic_rows)
    if dynamic_attributes != Counter({215: 147, 221: 2}):
        errors.append(f"dynamic attributes mismatch: {dict(dynamic_attributes)}")
    if errors:
        raise RuntimeError("AA8 unit_modifiers validation failed:\n" + "\n".join(errors))

    return {
        "row_count": len(rows),
        "owner_type_counts": dict(sorted(Counter(row["owner_type"] for row in rows).items())),
        "dynamic_row_count": len(dynamic_rows),
        "dynamic_attributes": dict(sorted(dynamic_attributes.items())),
        "minimum_value": min(int(row["value"]) for row in rows),
        "maximum_value": max(int(row["value"]) for row in rows),
        "maximum_attribute_id": max(int(row["unit_attribute_id"]) for row in rows),
        "battle_focus": {
            str(buff_id): sorted([list(value) for value in values])
            for buff_id, values in BATTLE_FOCUS.items()
        },
    }


def main() -> int:
    args = parse_args()
    if not args.game11.is_file():
        raise FileNotFoundError(args.game11)

    rows, string_cache, start, end = extract(args.game11)
    verification = validate(rows, string_cache) if args.verify else None
    catalog = {
        "format_version": 1,
        "scope": "AA8 enabled unit_modifiers cached result",
        "authority": {
            "source": "game11_native",
            "layout": "x2game_confirmed",
            "x2game_function": "FUN_3997ab60",
            "sql": (
                "SELECT owner_type, owner_id, dynamic_value, linear_level_bonus, "
                "unit_attribute_id, unit_modifier_type_id, value "
                "FROM unit_modifiers WHERE enable = 't'"
            ),
            "historical_reference_used": False,
        },
        "source": {
            "path": str(args.game11.resolve()),
            "sha256": sha256_file(args.game11),
            "result_range": {"start": start, "end": end, "rows": len(rows)},
            "string_cache": {str(key): value for key, value in sorted(string_cache.items())},
        },
        "columns": COLUMNS,
        "layout": LAYOUT,
        "visible_combat_stats": VISIBLE_COMBAT_STATS,
        "visible_stat_groups": VISIBLE_STAT_GROUPS,
        "formula_provenance": {
            "unit_modifiers": "game11_native",
            "attribute_ids": "x2game_confirmed",
            "base_unit_formulas": "server_reference_pending_x2game_reconstruction",
            "dynamic_value_semantics": (
                "x2game layout confirmed; nonzero rows are restricted to combat-resource "
                "attributes 215 and 221 and are not evaluated as fixed bonuses"
            ),
        },
        "verification": verification,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(catalog), encoding="utf-8")
    round_trip = json.loads(args.output.read_text(encoding="utf-8"))
    if canonical_json(round_trip) != canonical_json(catalog):
        raise RuntimeError("Catalog output is not deterministic")
    print(
        canonical_json(
            {
                "output": str(args.output.resolve()),
                "sha256": sha256_file(args.output),
                "verification": verification,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
