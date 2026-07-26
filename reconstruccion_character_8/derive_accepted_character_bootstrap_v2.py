#!/usr/bin/env python3
"""Close the AA8 character bootstrap with explicitly accepted derived policy.

Native cached-query rows remain distinguishable from the small set of
server-owned values accepted by the operator. This tool refuses unexpected v1
blockers, policy drift, missing references, or a non-deterministic matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"
EQUIPMENT_EXTRACTOR_PATH = (
    ROOT / "reconstruccion_items_8" / "extract_native_equipment.py"
)
EXPECTED_V1_BLOCKERS = {
    "spawn_transform_unproven",
    "action_bar_bootstrap_unproven",
    "supply_inventory_slots_unproven",
    "initial_inventory_capacity_unproven",
}
ACTION_SLOT_COUNT = 217
SPELL_ACTION_TYPE = 2
BAG_EXPAND_COLUMNS = (
    "id currency_id is_bank item_count item_id price step".split()
)
BAG_EXPAND_LAYOUT = "68 68 38 68 68 68 68".split()
DERIVED_SCHEMAS = {
    "native_character_creation_spawns": {
        "columns": [
            "character_id",
            "world_id",
            "zone_id",
            "x",
            "y",
            "z",
            "roll",
            "pitch",
            "yaw",
            "return_point_id",
        ],
        "layout": ["68", "68", "68", "60", "60", "60", "60", "60", "60", "68"],
    },
    "native_character_creation_inventory": {
        "columns": ["character_id", "inventory_slots", "bank_slots"],
        "layout": ["68", "68", "68"],
    },
    "native_character_creation_supply_slots": {
        "columns": ["supply_id", "slot_index"],
        "layout": ["68", "68"],
    },
    "native_character_creation_action_slots": {
        "columns": [
            "character_id",
            "ability_id",
            "slot_index",
            "action_type",
            "action_id",
        ],
        "layout": ["68", "68", "68", "68", "70"],
    },
}


def load_parser():
    spec = importlib.util.spec_from_file_location("aa8_cached_result", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_equipment_extractor():
    spec = importlib.util.spec_from_file_location(
        "aa8_native_equipment", EQUIPMENT_EXTRACTOR_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-data", required=True, type=Path)
    parser.add_argument("--v1-manifest", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--base-runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def runtime_ids(path: Path, table: str) -> set[int]:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return {int(row[0]) for row in connection.execute(f'SELECT id FROM "{table}"')}
    finally:
        connection.close()


def extract_bag_expands(game11: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parser = load_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    rows, source_range = parser.locate_cached_result(
        reader,
        BAG_EXPAND_COLUMNS,
        BAG_EXPAND_LAYOUT,
        1,
        {
            "currency_id": 0,
            "is_bank": 1,
            "item_count": 0,
            "item_id": 0,
            "price": 5000,
            "step": 0,
        },
    )
    if len(rows) != 20:
        raise RuntimeError(f"bag_expands expected 20 AA8 rows, found {len(rows)}")
    source_range.update(
        {
            "columns": BAG_EXPAND_COLUMNS,
            "layout": BAG_EXPAND_LAYOUT,
            "loader": (
                "x2game.dll FUN_39a077c0; embedded SELECT at 0x39df35a0 "
                "(64-bit) / file offset 0x1118738 (32-bit)"
            ),
        }
    )
    return rows, source_range


def extract_starter_item_concrete_rows(
    game11: Path,
    item_rows: list[dict[str, Any]],
    base_runtime: Path,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    equipment = load_equipment_extractor()
    parser = load_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    referenced_ids = {int(row["id"]) for row in item_rows}
    selected: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, dict[str, Any]] = {}
    for table in ("item_weapons", "item_armors"):
        table_spec = equipment.TABLES[table]
        rows, source_range = parser.locate_cached_result(
            reader,
            table_spec["columns"],
            table_spec["layout"],
            table_spec["anchor_id"],
            table_spec["anchor"],
        )
        selected[table] = [
            row for row in rows if int(row["item_id"]) in referenced_ids
        ]
        source_range.update(
            {
                "columns": table_spec["columns"],
                "layout": table_spec["layout"],
                "loader": f"x2game.dll confirmed {table} cached-result loader",
                "selected_rows": len(selected[table]),
            }
        )
        ranges[table] = source_range

    weapon_ids = {int(row["item_id"]) for row in selected["item_weapons"]}
    armor_ids = {int(row["item_id"]) for row in selected["item_armors"]}
    if len(weapon_ids) != 9 or len(armor_ids) != 3:
        raise RuntimeError(
            "starter concrete closure differs: "
            f"weapons={sorted(weapon_ids)}, armors={sorted(armor_ids)}"
        )
    overlap = weapon_ids.intersection(armor_ids)
    if overlap:
        raise RuntimeError(f"starter concrete item types overlap: {sorted(overlap)}")

    connection = sqlite3.connect(
        f"file:{base_runtime.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        holdable_ids = {
            int(row[0]) for row in connection.execute("SELECT id FROM holdables")
        }
        wearable_keys = {
            (int(row[0]), int(row[1]))
            for row in connection.execute(
                "SELECT armor_type_id,slot_type_id FROM wearables"
            )
        }
        wearable_kind_ids = {
            int(row[0])
            for row in connection.execute("SELECT armor_type_id FROM wearable_kinds")
        }
        wearable_slot_ids = {
            int(row[0])
            for row in connection.execute("SELECT slot_type_id FROM wearable_slots")
        }
        equip_set_ids = {
            int(row[0])
            for row in connection.execute("SELECT id FROM equip_item_sets")
        }
    finally:
        connection.close()
    missing_holdables = sorted(
        {
            int(row["holdable_id"])
            for row in selected["item_weapons"]
            if int(row["holdable_id"]) not in holdable_ids
        }
    )
    invalid_armor = sorted(
        int(row["item_id"])
        for row in selected["item_armors"]
        if (
            int(row["type_id"]),
            int(row["slot_type_id"]),
        )
        not in wearable_keys
        or int(row["type_id"]) not in wearable_kind_ids
        or int(row["slot_type_id"]) not in wearable_slot_ids
        or (
            int(row["eiset_id"]) != 0
            and int(row["eiset_id"]) not in equip_set_ids
        )
    )
    if missing_holdables or invalid_armor:
        raise RuntimeError(
            "starter concrete dependencies are incomplete: "
            f"holdables={missing_holdables}, armor_items={invalid_armor}"
        )

    coverage_rows: list[dict[str, Any]] = []
    allowed_generic_impl_ids = {0, 14}
    for item in sorted(item_rows, key=lambda row: int(row["id"])):
        item_id = int(item["id"])
        impl_id = int(item["impl_id"])
        if item_id in weapon_ids:
            concrete_type = "weapon"
            provenance = "game11_native_items+game11_native_item_weapons"
        elif item_id in armor_ids:
            concrete_type = "armor"
            provenance = "game11_native_items+game11_native_item_armors"
        elif impl_id in allowed_generic_impl_ids:
            concrete_type = "generic"
            provenance = (
                "game11_native_items+server_generic_item"
                if impl_id == 0
                else "game11_native_teleport_book+server_generic_item"
            )
        else:
            raise RuntimeError(
                f"starter item {item_id} has unresolved concrete impl {impl_id}"
            )
        coverage_rows.append(
            {
                "item_id": item_id,
                "concrete_type": concrete_type,
                "coverage": "complete",
                "missing_dependencies": "",
                "provenance": provenance,
            }
        )
    return selected, ranges, coverage_rows


def validate_bag_expands(
    rows: list[dict[str, Any]], available_item_ids: set[int]
) -> None:
    by_key = {(int(row["is_bank"]), int(row["step"])): row for row in rows}
    if len(by_key) != 20 or set(by_key) != {
        (is_bank, step) for is_bank in (0, 1) for step in range(10)
    }:
        raise RuntimeError("bag_expands does not cover bank and backpack steps 0..9")
    expected_prices = [5000, 10000, 30000, 100000, 250000]
    expected_counts = [1, 3, 6, 10, 10]
    for is_bank in (0, 1):
        for step in range(10):
            row = by_key[(is_bank, step)]
            if int(row["currency_id"]) != 0:
                raise RuntimeError("bag_expands contains an unsupported currency")
            if step < 5:
                expected = (expected_prices[step], 0, 0)
            else:
                expected = (0, 49000, expected_counts[step - 5])
            actual = (
                int(row["price"]),
                int(row["item_id"]),
                int(row["item_count"]),
            )
            if actual != expected:
                raise RuntimeError(
                    f"bag_expands {is_bank}/{step}: expected {expected}, found {actual}"
                )
            if actual[1] and actual[1] not in available_item_ids:
                raise RuntimeError(
                    f"bag_expands references missing runtime item {actual[1]}"
                )


def derive_spawns(
    characters: list[dict[str, Any]],
    start_points: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    point_by_character = {
        int(row["character_id"]): row for row in start_points
    }
    configured_races = {int(value) for value in policy["spawn_by_race"]}
    playable_races = {int(row["char_race_id"]) for row in characters}
    if configured_races != playable_races:
        raise RuntimeError(
            f"spawn policy races differ: expected {sorted(playable_races)}, "
            f"found {sorted(configured_races)}"
        )
    rows: list[dict[str, Any]] = []
    for character in sorted(characters, key=lambda row: int(row["id"])):
        character_id = int(character["id"])
        race = int(character["char_race_id"])
        configured = policy["spawn_by_race"][str(race)]
        native_point = point_by_character[character_id]
        if int(configured["zone_id"]) != int(character["starting_zone_id"]):
            raise RuntimeError(f"spawn zone differs for character {character_id}")
        if int(configured["return_point_id"]) != int(native_point["return_point_id"]):
            raise RuntimeError(
                f"spawn return point differs for character {character_id}"
            )
        rotation = configured["rotation_degrees"]
        rows.append(
            {
                "character_id": character_id,
                "world_id": int(configured["world_id"]),
                "zone_id": int(configured["zone_id"]),
                "x": float(configured["x"]),
                "y": float(configured["y"]),
                "z": float(configured["z"]),
                "roll": math.radians(float(rotation["roll"])),
                "pitch": math.radians(float(rotation["pitch"])),
                "yaw": math.radians(float(rotation["yaw"])),
                "return_point_id": int(configured["return_point_id"]),
            }
        )
    if len(rows) != 12:
        raise RuntimeError(f"spawn matrix expected 12 rows, found {len(rows)}")
    return rows


def derive_inventory(
    characters: list[dict[str, Any]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    capacity = policy["decisions"]["initial_capacity"]
    inventory_slots = int(capacity["inventory_slots"])
    bank_slots = int(capacity["bank_slots"])
    if inventory_slots != 50 or bank_slots != 50:
        raise RuntimeError("accepted v2 initial capacity must remain 50/50")
    return [
        {
            "character_id": int(character["id"]),
            "inventory_slots": inventory_slots,
            "bank_slots": bank_slots,
        }
        for character in sorted(characters, key=lambda row: int(row["id"]))
    ]


def derive_supply_slots(
    supplies: list[dict[str, Any]], policy: dict[str, Any]
) -> list[dict[str, Any]]:
    first_slot = int(policy["decisions"]["supply_slots"]["first_slot"])
    rows = [
        {"supply_id": int(supply["id"]), "slot_index": first_slot + index}
        for index, supply in enumerate(
            sorted(supplies, key=lambda row: int(row["id"]))
        )
    ]
    if len(rows) != 4 or len({row["slot_index"] for row in rows}) != 4:
        raise RuntimeError("accepted supply allocation must contain four unique slots")
    return rows


def derive_actions(
    characters: list[dict[str, Any]],
    abilities: list[dict[str, Any]],
    start_skills: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    selected_slot = int(
        policy["decisions"]["action_bar"]["selected_skill_slot"]
    )
    if selected_slot != 1:
        raise RuntimeError("AA8 client auto-registration evidence requires base slot 1")
    rows: list[dict[str, Any]] = []
    for character in sorted(characters, key=lambda row: int(row["id"])):
        for ability in sorted(abilities, key=lambda row: int(row["ability_id"])):
            ability_id = int(ability["ability_id"])
            skill_id = int(start_skills[str(ability_id)])
            for slot in range(ACTION_SLOT_COUNT):
                selected = slot == selected_slot
                rows.append(
                    {
                        "character_id": int(character["id"]),
                        "ability_id": ability_id,
                        "slot_index": slot,
                        "action_type": SPELL_ACTION_TYPE if selected else 0,
                        "action_id": skill_id if selected else 0,
                    }
                )
    expected = len(characters) * len(abilities) * ACTION_SLOT_COUNT
    if expected != 20832 or len(rows) != expected:
        raise RuntimeError(
            f"accepted action matrix expected 20832 rows, found {len(rows)}"
        )
    return rows


def main() -> int:
    options = parse_args()
    v1_data = read_json(options.v1_data)
    v1_manifest = read_json(options.v1_manifest)
    policy = read_json(options.policy)
    blocker_codes = {entry["code"] for entry in v1_manifest.get("blockers", [])}
    if blocker_codes != EXPECTED_V1_BLOCKERS:
        raise RuntimeError(
            f"unexpected strict-v1 blockers: {sorted(blocker_codes)}"
        )
    if v1_manifest.get("deployable", True):
        raise RuntimeError("strict v1 unexpectedly reports deployable")
    if int(policy.get("schema_version", 0)) != 1:
        raise RuntimeError("unsupported accepted policy schema")

    tables = deepcopy(v1_data["tables"])
    characters = tables["characters"]
    abilities = tables["login_stage_abilities"]
    if len(characters) != 12 or len(abilities) != 8:
        raise RuntimeError("strict v1 playable matrix changed")

    bag_expands, bag_expand_range = extract_bag_expands(options.game11)
    validate_bag_expands(bag_expands, runtime_ids(options.base_runtime, "items"))
    tables["bag_expands"] = bag_expands
    (
        starter_concrete,
        starter_concrete_ranges,
        starter_coverage,
    ) = extract_starter_item_concrete_rows(
        options.game11,
        tables["items"],
        options.base_runtime,
    )
    tables.update(starter_concrete)
    tables["aaemu_item_definition_coverage"] = starter_coverage
    tables["native_character_creation_spawns"] = derive_spawns(
        characters, v1_manifest["start_return_points"], policy
    )
    tables["native_character_creation_inventory"] = derive_inventory(
        characters, policy
    )
    tables["native_character_creation_supply_slots"] = derive_supply_slots(
        tables["character_supplies"], policy
    )
    tables["native_character_creation_action_slots"] = derive_actions(
        characters,
        abilities,
        v1_manifest["start_skill_ids"],
        policy,
    )

    output_data = {
        "format_version": 2,
        "sources": {
            **v1_data["sources"],
            "accepted_policy": {
                "path": str(options.policy.resolve()),
                "sha256": sha256(options.policy),
            },
            "strict_v1_data": {
                "path": str(options.v1_data.resolve()),
                "sha256": sha256(options.v1_data),
            },
            "strict_v1_manifest": {
                "path": str(options.v1_manifest.resolve()),
                "sha256": sha256(options.v1_manifest),
            },
        },
        "tables": tables,
    }

    output_dir = options.output
    output_dir.mkdir(parents=True, exist_ok=True)
    data_path = output_dir / "native-character-creation-v2-data.json"
    write_json(data_path, output_data)

    classifications = deepcopy(v1_manifest["table_classifications"])
    classifications.update(
        {
            "aaemu_item_definition_coverage": "server_derived_reference_closure",
            "bag_expands": "native_authoritative_replacement",
            "item_armors": "native_reference_closure",
            "item_weapons": "native_reference_closure",
            "native_character_creation_spawns": "server_derived_accepted",
            "native_character_creation_inventory": "server_derived_accepted",
            "native_character_creation_supply_slots": "server_derived_accepted",
            "native_character_creation_action_slots": "server_derived_accepted",
        }
    )
    schemas = deepcopy(v1_manifest["table_schemas"])
    equipment = load_equipment_extractor()
    schemas["aaemu_item_definition_coverage"] = {
        "columns": [
            "item_id",
            "concrete_type",
            "coverage",
            "missing_dependencies",
            "provenance",
        ],
        "key_column": "item_id",
        "layout": ["68", "78", "78", "78", "78"],
    }
    schemas["bag_expands"] = {
        "columns": BAG_EXPAND_COLUMNS,
        "layout": BAG_EXPAND_LAYOUT,
    }
    for table in ("item_weapons", "item_armors"):
        schemas[table] = {
            "columns": equipment.TABLES[table]["columns"],
            "key_column": "id",
            "layout": equipment.TABLES[table]["layout"],
        }
    schemas.update(DERIVED_SCHEMAS)
    source_ranges = deepcopy(v1_manifest["source_ranges"])
    source_ranges["bag_expands"] = bag_expand_range
    source_ranges.update(starter_concrete_ranges)

    manifest = {
        "authority": (
            "Kakao 8.0.3.12 r558734 native catalogue plus explicitly accepted "
            "server-derived bootstrap policy"
        ),
        "blockers": [],
        "deployable": True,
        "format_version": 2,
        "matrix": {
            "ability_ids": sorted(
                int(row["ability_id"]) for row in abilities
            ),
            "action_rows": len(
                tables["native_character_creation_action_slots"]
            ),
            "character_templates": len(characters),
            "combinations": len(characters) * len(abilities),
            "slots_per_combination": ACTION_SLOT_COUNT,
        },
        "native_corrections": {
            "bag_expands": {
                "base_runtime_replaced": True,
                "high_step_item_counts": [1, 3, 6, 10, 10],
                "high_step_item_id": 49000,
                "source_result": bag_expand_range,
            }
        },
        "starter_item_concrete_closure": {
            "armor_rows": len(tables["item_armors"]),
            "coverage_rows": len(tables["aaemu_item_definition_coverage"]),
            "generic_item_ids": sorted(
                int(row["item_id"])
                for row in tables["aaemu_item_definition_coverage"]
                if row["concrete_type"] == "generic"
            ),
            "weapon_rows": len(tables["item_weapons"]),
        },
        "native_data_anomalies": {
            "default_skill_missing_skill_ids": [44214],
            "handling": (
                "The complete native default_skills result references skill "
                "44214, which is absent from the complete native skills result. "
                "No character_default_skills row references that default-skill "
                "row; the server loader logs and skips it."
            ),
        },
        "phase": "native_character_creation_v2_accepted_bootstrap",
        "policy": policy,
        "protocol": deepcopy(v1_manifest["protocol"]),
        "source_ranges": source_ranges,
        "sources": {
            **v1_manifest["sources"],
            "accepted_policy": {
                "path": str(options.policy.resolve()),
                "sha256": sha256(options.policy),
            },
            "strict_v1_data": {
                "path": str(options.v1_data.resolve()),
                "sha256": sha256(options.v1_data),
            },
            "strict_v1_manifest": {
                "path": str(options.v1_manifest.resolve()),
                "sha256": sha256(options.v1_manifest),
            },
        },
        "strict_v1_blockers_closed_by_policy": sorted(EXPECTED_V1_BLOCKERS),
        "table_classifications": classifications,
        "table_counts": {
            table: len(rows) for table, rows in sorted(tables.items())
        },
        "table_schemas": schemas,
    }
    manifest["generated_data"] = {
        "path": str(data_path.resolve()),
        "sha256": sha256(data_path),
    }
    manifest_path = output_dir / "native-character-creation-v2-manifest.json"
    write_json(manifest_path, manifest)

    print(
        json.dumps(
            {
                "data": str(data_path.resolve()),
                "data_sha256": sha256(data_path),
                "deployable": True,
                "manifest": str(manifest_path.resolve()),
                "manifest_sha256": sha256(manifest_path),
                "tables": manifest["table_counts"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
