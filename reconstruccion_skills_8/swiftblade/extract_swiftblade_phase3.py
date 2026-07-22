#!/usr/bin/env python3
"""Extract the native Kakao 8.0 Swiftblade dependency closure.

All inputs are read-only.  The script deliberately keeps unresolved game11
string references unresolved: a historical compact may identify a reference
only when the row id and numeric target agree exactly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from extract_battlerage_manifest import (  # noqa: E402
    CachedResultReader,
    build_effect_type_reference_map,
    extract_client_relationships,
    locate_cached_result,
    read_cached_result,
)


ABILITY_ID = 12
ABILITY_NAME = "Swiftblade"

NATIVE_RESULT_SPECS: dict[str, dict[str, Any]] = {
    "aoe_shapes": {
        "columns": (
            "id adjust_angle area_target_kind_id calc_distance kind_id "
            "value1 value2 value3"
        ).split(),
        "layout": "68 38 68 38 68 60 60 60".split(),
        "anchor_id": 15485,
        "anchor_values": {"kind_id": 1, "value1": 5.5},
        "layout_source": "x2game.dll FUN_399652b0",
        "start": 0x1D06,
        "expected_rows": 18234,
    },
    "aggro_effects": {
        "columns": (
            "id charged_buff_id charged_mul combat_resource_level_md "
            "combat_resource_md fixed_max fixed_min level_md level_va_end "
            "level_va_start use_charged_buff use_combat_resource "
            "use_fixed_aggro use_level_aggro"
        ).split(),
        "layout": "68 68 60 60 60 68 68 60 68 68 38 38 38 38".split(),
        "anchor_id": 667,
        "anchor_values": {},
        "layout_source": "x2game.dll FUN_3996d460",
        "start": 0xB60FEF,
        "expected_rows": 445,
    },
    "bubble_effects": {
        "columns": "id kind_id speech".split(),
        "layout": "68 68 78".split(),
        "anchor_id": 1,
        "anchor_values": {"kind_id": 1},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_399710a0",
        "start": 0xDEBADB,
        "expected_rows": 5811,
    },
    "combat_resource_effects": {
        "columns": "id chance combat_resource_id max_combat_resource min_combat_resource reset_remain_time".split(),
        "layout": "68 68 68 68 68 38".split(),
        "anchor_id": 469,
        "anchor_values": {},
        "layout_source": "x2game.dll FUN_39974c30",
        "start": 0xE54A6F,
        "expected_rows": 474,
    },
    "extend_charge_effects": {
        "columns": (
            "id charge_buff_id damage_type_id dps_inc_multiplier dps_multiplier "
            "fixed_max fixed_min level_md level_va_end level_va_start percent_max "
            "percent_min use_current_health use_dps_charge use_fixed_charge "
            "use_level_charge use_mainhand_weapon use_offhand_weapon "
            "use_percent_charge use_ranged_weapon"
        ).split(),
        "layout": (
            "68 68 68 60 60 68 68 60 68 68 68 68 38 38 38 38 38 38 38 38"
        ).split(),
        "anchor_id": 1,
        "anchor_values": {"charge_buff_id": 95, "damage_type_id": 2},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_39974f20",
        "start": 0xE57331,
        "expected_rows": 23,
    },
    "heal_effects": {
        "columns": (
            "id actability_add actability_group_id actability_mul actability_step "
            "cancel_protection charged_buff_id charged_mul combat_resource_level_md "
            "combat_resource_md crime dps_multiplier fixed_max fixed_min fixed_type "
            "ignore_heal_aggro level_md level_va_end level_va_start percent "
            "self_target_multiplier slave_applicable use_charged_buff "
            "use_combat_resource use_element_effect use_fixed_heal use_level_heal "
            "weapon_slot_id"
        ).split(),
        "layout": (
            "68 60 68 60 68 38 68 60 60 60 38 60 68 68 38 38 60 68 68 38 "
            "60 38 38 38 38 38 38 68"
        ).split(),
        "anchor_id": 1,
        "anchor_values": {"fixed_max": 1000, "fixed_min": 1000},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_3996c3c0",
        "start": 0xB45F23,
        "expected_rows": 916,
    },
    "interaction_effects": {
        "columns": "id doodad_id source_direction wi_id".split(),
        "layout": "68 68 38 68".split(),
        "anchor_id": 7792,
        "anchor_values": {},
        "layout_source": "x2game.dll FUN_3996ff60",
        "start": 0xDA1CC5,
        "expected_rows": 6898,
    },
    "kill_npc_without_corpse_effects": {
        "columns": "id give_exp npc_id radius vanish".split(),
        "layout": "68 38 68 60 38".split(),
        "anchor_id": 14,
        "anchor_values": {"npc_id": 3812, "radius": 25.0},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_399708e0",
        "start": 0xDD0ECA,
        "expected_rows": 1613,
    },
    "mana_burn_effects": {
        "columns": (
            "id base_max base_min damage_ratio damage_type_id dps_inc_multiplier "
            "dps_multiplier level_md level_va_end level_va_start mana_drain_ratio "
            "percent_max percent_min use_current_health use_fixed_charge "
            "use_level_charge use_mainhand_weapon use_offhand_weapon "
            "use_percent_charge use_ranged_weapon"
        ).split(),
        "layout": (
            "68 68 68 68 68 60 60 60 68 68 60 68 68 38 38 38 38 38 38 38"
        ).split(),
        "anchor_id": 1,
        "anchor_values": {"damage_type_id": 2, "dps_multiplier": 1.0},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_3996f3e0",
        "start": 0xD9F951,
        "expected_rows": 89,
    },
    "plots": {
        "columns": "id name target_type_id".split(),
        "layout": "68 78 68".split(),
        "anchor_id": 2,
        "anchor_values": {"target_type_id": 1},
        "layout_source": "x2game.dll FUN_39a761f0",
        "start": 0x7F840A0,
        "expected_rows": 5853,
    },
    "plot_events": {
        "columns": (
            "id aoe_diminishing name only_die_unit only_my_pet only_my_slave "
            "only_pet_owner plot_id position source_update_method_id "
            "target_update_method_id target_update_method_param1 "
            "target_update_method_param10 target_update_method_param11 "
            "target_update_method_param2 target_update_method_param3 "
            "target_update_method_param4 target_update_method_param5 "
            "target_update_method_param6 target_update_method_param7 "
            "target_update_method_param8 target_update_method_param9 tickets"
        ).split(),
        "layout": "68 38 78 38 38 38 38 68 68 68 68 68 68 68 68 68 68 68 68 68 68 68 68".split(),
        "anchor_id": 2522,
        "anchor_values": {"plot_id": 329, "position": 1},
        "layout_source": "x2game.dll FUN_39a75720",
        "start": 0x7BBFA8A,
        "expected_rows": 45959,
    },
    "plot_conditions": {
        "columns": "id kind_id not_condition or_unit_reqs param1 param2 param3 param4 pure".split(),
        "layout": "68 68 38 38 68 68 68 68 38".split(),
        "anchor_id": 5,
        "anchor_values": {"kind_id": 2},
        "layout_source": "x2game.dll FUN_39a73990",
        "start": 0x7736452,
        "expected_rows": 17402,
    },
    "plot_aoe_conditions": {
        "columns": "id condition_id event_id position".split(),
        "layout": "68 68 68 68".split(),
        "anchor_id": 147,
        "anchor_values": {"condition_id": 5},
        "layout_source": "x2game.dll FUN_39a740d0",
        "start": 0x77AD3B0,
        "expected_rows": 3067,
    },
    "plot_event_conditions": {
        "columns": "id condition_id event_id notify_failure position source_id target_id".split(),
        "layout": "68 68 68 38 68 68 68".split(),
        "anchor_id": 145,
        "anchor_values": {"condition_id": 5},
        "layout_source": "x2game.dll FUN_39a74390",
        "start": 0x77B9F61,
        "expected_rows": 14335,
    },
    "plot_effects": {
        "columns": "id actual_type actual_id event_id position source_id target_id".split(),
        "layout": "68 78 68 68 68 68 68".split(),
        "anchor_id": 2,
        "anchor_values": {"actual_id": 1},
        "layout_source": "x2game.dll FUN_39a74690",
        "start": 0x7814F4D,
        "expected_rows": 58377,
    },
    "plot_next_events": {
        "columns": (
            "id add_anim_cs_time cancel_on_big_hit casting casting_cancelable "
            "casting_delayable casting_inc casting_useable channeling "
            "combat_resource delay event_id fail next_event_id per_target position "
            "speed use_exe_time weight"
        ).split(),
        "layout": "68 38 38 38 38 38 68 38 38 38 68 68 38 68 38 68 68 38 68".split(),
        "anchor_id": 286,
        "anchor_values": {"event_id": 2522},
        "layout_source": "x2game.dll FUN_39a75290",
        "start": 0x79C08B4,
        "expected_rows": 47580,
    },
    "dispel_effects": {
        "columns": "id buff_tag_id cure_count dispel_count stack".split(),
        "layout": "68 68 68 68 68".split(),
        "anchor_id": 3,
        "anchor_values": {"cure_count": 1, "dispel_count": 0},
        "layout_source": "x2game.dll FUN_39970ba0",
        "start": 0xDD8687,
        "expected_rows": 3755,
    },
    "reset_aoe_diminishing_effects": {
        "columns": ["id"],
        "layout": ["68"],
        "anchor_id": 2,
        "anchor_values": {},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_39973660",
        "start": 0xE52AB1,
        "expected_rows": 191,
    },
    "restore_mana_effects": {
        "columns": (
            "id fixed_max fixed_min level_md level_va_end level_va_start percent "
            "use_fixed_value use_level_value"
        ).split(),
        "layout": "68 68 68 60 68 68 38 38 38".split(),
        "anchor_id": 1,
        "anchor_values": {"fixed_max": 2000, "fixed_min": 2000},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_3996d140",
        "start": 0xB5EFE9,
        "expected_rows": 256,
    },
    "spawn_effects": {
        "columns": (
            "id despawn_on_creator_death enable_ray_cast life_time mate_state_id "
            "ori_angle ori_dir_id owner_type_id pos_angle_max pos_angle_min pos_dir_id "
            "pos_distance_max pos_distance_min ray_off_set sub_type "
            "use_summoner_aggro_target use_summoner_faction"
        ).split(),
        "layout": "68 38 38 60 68 60 68 68 60 60 68 60 60 60 68 38 38".split(),
        "anchor_id": 1,
        "anchor_values": {"mate_state_id": 3, "owner_type_id": 2},
        "strict_anchor": True,
        "layout_source": "x2game.dll FUN_3996e5a0",
        "start": 0xD5AC76,
        "expected_rows": 2447,
    },
    "anims": {
        "columns": "id category_id hang_ub loop move_ub name relaxed_ub ride_ub swim_move_ub swim_ub".split(),
        "layout": "68 68 78 38 78 78 78 78 78 78".split(),
        "anchor_id": 1,
        "anchor_values": {"category_id": 1},
        "layout_source": "x2game.dll FUN_39967430",
        "start": 0x3A6ED3,
        "expected_rows": 1071,
        # The first rows prove this base without historical data: the third
        # interned value in row 1 is immediately referenced as 18724, and the
        # first interned value in row 2 is immediately referenced as 18725.
        "string_cache_base": 18722,
    },
    "skill_controllers": {
        "columns": (
            "id active_weapon_id end_anim_id end_skill_id kind_id start_anim_id "
            "str_value1 transition_anim_1_id transition_anim_2_id value1 value10 "
            "value11 value12 value13 value14 value15 value2 value3 value4 value5 "
            "value6 value7 value8 value9"
        ).split(),
        "layout": ("68 68 68 68 68 68 78 " + "68 " * 17).split(),
        "anchor_id": 55,
        "anchor_values": {"kind_id": 1},
        "layout_source": "x2game.dll FUN_399624e0",
        "start": 0x884701,
        "expected_rows": 3083,
    },
    "projectiles": {
        "columns": "id dest_bone_id fx_group_id ignore_z_rotation is_permanent proj_physic_id src_bone_id".split(),
        "layout": "68 68 68 38 38 68 68".split(),
        "anchor_id": 1,
        "anchor_values": {"proj_physic_id": 1},
        "layout_source": "x2game.dll FUN_39955c80",
        "start": 0x630BDAD,
        "expected_rows": 1493,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--runtime-compact", required=True, type=Path)
    parser.add_argument("--server-reference", required=True, type=Path)
    parser.add_argument("--client-game-stream", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def extract_native_tables(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    reader = CachedResultReader(path.read_bytes())
    tables: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, Any] = {}
    for table, spec in NATIVE_RESULT_SPECS.items():
        string_cache_base = spec.get("string_cache_base")
        if string_cache_base is not None:
            reader.begin_string_cache_capture(int(string_cache_base))
        raw_rows, end = read_cached_result(reader, spec["start"], spec["layout"])
        captured_strings = (
            reader.end_string_cache_capture()
            if string_cache_base is not None
            else {}
        )
        rows = [dict(zip(spec["columns"], row)) for row in raw_rows]
        if len(rows) != spec["expected_rows"]:
            raise RuntimeError(
                f"{table} cached range has {len(rows)} rows; expected {spec['expected_rows']}"
            )
        if not any(
            int(row["id"]) == spec["anchor_id"]
            and (
                not spec.get("strict_anchor", False)
                or all(
                    row.get(key) == value
                    for key, value in spec["anchor_values"].items()
                )
            )
            for row in rows
        ):
            raise RuntimeError(f"{table} cached range failed its confirmed anchor")
        result_range = {
            "start": spec["start"],
            "end": end,
            "rows": len(rows),
            "anchor_id": spec["anchor_id"],
        }
        result_range["layout_source"] = spec["layout_source"]
        if captured_strings:
            result_range["string_cache"] = {
                "first_reference": min(captured_strings),
                "last_reference": max(captured_strings),
                "entries": len(captured_strings),
                "source": "game11_native_self_references",
            }
        if table == "anims":
            unresolved_strings = [
                (int(row["id"]), field)
                for row in rows
                for field in (
                    "hang_ub",
                    "move_ub",
                    "name",
                    "relaxed_ub",
                    "ride_ub",
                    "swim_move_ub",
                    "swim_ub",
                )
                if row.get(field) is None
                or str(row[field]).startswith("<ref:")
            ]
            if unresolved_strings:
                raise RuntimeError(
                    "Native animations have unresolved strings: "
                    f"{unresolved_strings}"
                )
        tables[table] = rows
        ranges[table] = result_range
    return tables, ranges


def resolve_reference_map(
    client_rows: list[dict[str, Any]],
    server: sqlite3.Connection,
    table: str,
    value_column: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    server_rows = {
        int(row["id"]): dict(row)
        for row in server.execute(f'SELECT * FROM "{table}"')
    }
    candidates: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in client_rows:
        reference = row.get(value_column)
        if not isinstance(reference, str) or not reference.startswith("<ref:"):
            continue
        historical = server_rows.get(int(row["id"]))
        if historical and int(historical.get("actual_id", -1)) == int(row["actual_id"]):
            value = historical.get(value_column)
            if value:
                candidates[reference][str(value)] += 1
    resolved: dict[str, str] = {}
    evidence: dict[str, Any] = {}
    for reference, values in sorted(candidates.items()):
        ordered = dict(sorted(values.items()))
        state = "conflict"
        if len(ordered) == 1:
            resolved[reference] = next(iter(ordered))
            state = "resolved_unique"
        evidence[reference] = {"candidates": ordered, "state": state}
    return resolved, evidence


def indexed(rows: list[dict[str, Any]], column: str = "id") -> dict[int, dict[str, Any]]:
    return {int(row[column]): row for row in rows}


def grouped(rows: list[dict[str, Any]], column: str) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        result[int(row[column])].append(row)
    return result


def build_closure(
    client: sqlite3.Connection,
    server: sqlite3.Connection | None,
    relationships: dict[str, Any],
    native: dict[str, list[dict[str, Any]]],
    *,
    ability_id: int = ABILITY_ID,
    skill_source: sqlite3.Connection | None = None,
    effect_type_map_override: dict[str, str] | None = None,
    plot_type_map_override: dict[str, str] | None = None,
    reference_evidence_override: dict[str, Any] | None = None,
    root_skill_ids: set[int] | None = None,
    include_ability_passives: bool = True,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    skill_source = skill_source or client
    ability_skills = [
        dict(row)
        for row in skill_source.execute(
            "SELECT * FROM skills WHERE ability_id = ? ORDER BY ability_level, id",
            (ability_id,),
        )
    ]
    ability_skill_ids = {int(row["id"]) for row in ability_skills}
    requested_skill_ids = ability_skill_ids if root_skill_ids is None else set(root_skill_ids)
    unknown_roots = requested_skill_ids.difference(ability_skill_ids)
    if unknown_roots:
        raise ValueError(
            f"Skills {sorted(unknown_roots)} do not belong to ability {ability_id}"
        )
    skills = [row for row in ability_skills if int(row["id"]) in requested_skill_ids]
    skill_ids = {int(row["id"]) for row in skills}
    if effect_type_map_override is not None:
        effect_type_map = dict(effect_type_map_override)
        effect_type_evidence = dict(reference_evidence_override or {})
    else:
        if server is None:
            raise ValueError("A server reference or a native effect type map is required")
        effect_type_map, effect_type_evidence = build_effect_type_reference_map(client, server)
        # game11 carries the first occurrence as an inline string and subsequent
        # values as an interned reference. Both are present in the native effects
        # result, which identifies this post-3.0 type without historical inference.
        effect_type_map["<ref:75256>"] = "CombatResourceEffect"
        effect_type_evidence["<ref:75256>"] = {
            "candidates": {"CombatResourceEffect": 139},
            "state": "resolved_from_client_inline_string_and_interned_reference",
        }
    if plot_type_map_override is not None:
        plot_type_map = dict(plot_type_map_override)
        plot_type_evidence = dict(reference_evidence_override or {})
    else:
        if server is None:
            raise ValueError("A server reference or a native plot type map is required")
        plot_type_map, plot_type_evidence = resolve_reference_map(
            native["plot_effects"], server, "plot_effects", "actual_type"
        )

    all_effects = {int(row["id"]): dict(row) for row in client.execute("SELECT * FROM effects")}
    concrete = {
        **relationships["concrete_effects"],
        **{
            table: native[table]
            for table in (
                "aggro_effects",
                "bubble_effects",
                "combat_resource_effects",
                "dispel_effects",
                "extend_charge_effects",
                "heal_effects",
                "interaction_effects",
                "kill_npc_without_corpse_effects",
                "mana_burn_effects",
                "reset_aoe_diminishing_effects",
                "restore_mana_effects",
                "spawn_effects",
            )
        },
    }
    concrete_by_id = {table: indexed(rows) for table, rows in concrete.items()}
    skill_effects_by_skill = grouped(relationships["skill_effects"], "skill_id")

    selected: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in skills:
        selected["skills"][int(row["id"])] = row
    for row in relationships["passive_buffs"]:
        if include_ability_passives and int(row["ability_id"]) == ability_id:
            selected["passive_buffs"][int(row["id"])] = row

    effect_queue: deque[int] = deque()
    buff_queue: deque[int] = deque()
    controller_ids: set[int] = set()
    projectile_ids: set[int] = set()
    anim_ids: set[int] = set()
    plot_ids: set[int] = set()

    for row in skills:
        for relation in skill_effects_by_skill.get(int(row["id"]), []):
            selected["skill_effects"][int(relation["id"])] = relation
            effect_queue.append(int(relation["effect_id"]))
        for field in ("toggle_buff_id", "channeling_buff_id", "channeling_target_buff_id"):
            if int(row.get(field) or 0):
                buff_queue.append(int(row[field]))
        for field in ("start_anim_id", "fire_anim_id", "channeling_anim_id", "dual_wield_fire_anim_id", "twohand_fire_anim_id"):
            if int(row.get(field) or 0):
                anim_ids.add(int(row[field]))
        if int(row.get("skill_controller_id") or 0):
            controller_ids.add(int(row["skill_controller_id"]))
        if int(row.get("projectile_id") or 0):
            projectile_ids.add(int(row["projectile_id"]))
        if int(row.get("plot_id") or 0):
            plot_ids.add(int(row["plot_id"]))
    for row in selected["passive_buffs"].values():
        buff_queue.append(int(row["buff_id"]))

    reached_effects: set[int] = set()
    unresolved_effect_types: list[dict[str, Any]] = []
    chained_skill_ids: set[int] = set()

    def select_concrete(actual_type: str, actual_id: int) -> None:
        table = {
            "AggroEffect": "aggro_effects",
            "BubbleEffect": "bubble_effects",
            "BuffEffect": "buff_effects",
            "CombatResourceEffect": "combat_resource_effects",
            "DamageEffect": "damage_effects",
            "DispelEffect": "dispel_effects",
            "ExtendChargeEffect": "extend_charge_effects",
            "HealEffect": "heal_effects",
            "InteractionEffect": "interaction_effects",
            "KillNpcWithoutCorpseEffect": "kill_npc_without_corpse_effects",
            "ManaBurnEffect": "mana_burn_effects",
            "ResetAoeDiminishingEffect": "reset_aoe_diminishing_effects",
            "RestoreManaEffect": "restore_mana_effects",
            "SpawnEffect": "spawn_effects",
            "SpecialEffect": "special_effects",
            "ConversionEffect": "conversion_effects",
            "PhysicalExplosionEffect": "physical_explosion_effects",
        }.get(actual_type)
        if actual_type == "SkillController":
            controller_ids.add(actual_id)
            return
        if table is None:
            unresolved_effect_types.append({"actual_type": actual_type, "actual_id": actual_id})
            return
        row = concrete_by_id.get(table, {}).get(actual_id)
        if row is None:
            unresolved_effect_types.append({"actual_type": actual_type, "actual_id": actual_id, "table": table})
            return
        selected[table][actual_id] = row
        if actual_type == "BuffEffect":
            buff_queue.append(int(row["buff_id"]))
        elif actual_type == "SpecialEffect" and int(row["special_effect_type_id"]) == 48:
            chained_skill = int(row["value1"])
            if chained_skill in ability_skill_ids:
                chained_skill_ids.add(chained_skill)
            elif chained_skill > 0:
                unresolved_effect_types.append(
                    {
                        "actual_type": "SpecialEffect:ChainedSkill",
                        "actual_id": actual_id,
                        "skill_id": chained_skill,
                        "reason": "chained_skill_outside_ability",
                    }
                )
            if chained_skill in skill_ids:
                for relation in skill_effects_by_skill.get(chained_skill, []):
                    selected["skill_effects"][int(relation["id"])] = relation
                    effect_queue.append(int(relation["effect_id"]))

    while effect_queue:
        effect_id = effect_queue.popleft()
        if effect_id in reached_effects:
            continue
        reached_effects.add(effect_id)
        effect = all_effects.get(effect_id)
        if effect is None:
            unresolved_effect_types.append({"effect_id": effect_id, "reason": "missing_effect_row"})
            continue
        actual_type = str(effect["actual_type"])
        actual_type = effect_type_map.get(actual_type, actual_type)
        effect = {**effect, "actual_type": actual_type}
        selected["effects"][effect_id] = effect
        select_concrete(actual_type, int(effect["actual_id"]))

    events_by_plot = grouped(native["plot_events"], "plot_id")
    next_by_event = grouped(native["plot_next_events"], "event_id")
    effects_by_event = grouped(native["plot_effects"], "event_id")
    event_conditions_by_event = grouped(native["plot_event_conditions"], "event_id")
    aoe_conditions_by_event = grouped(native["plot_aoe_conditions"], "event_id")
    condition_by_id = indexed(native["plot_conditions"])
    plot_by_id = indexed(native["plots"])
    event_by_id = indexed(native["plot_events"])
    event_queue: deque[int] = deque()
    for plot_id in sorted(plot_ids):
        if plot_id in plot_by_id:
            selected["plots"][plot_id] = plot_by_id[plot_id]
        for event in events_by_plot.get(plot_id, []):
            event_queue.append(int(event["id"]))
    reached_events: set[int] = set()
    unresolved_plot_types: list[dict[str, Any]] = []
    aoe_shape_ids: set[int] = set()
    aoe_shape_by_id = indexed(native["aoe_shapes"])
    while event_queue:
        event_id = event_queue.popleft()
        if event_id in reached_events:
            continue
        reached_events.add(event_id)
        event = event_by_id.get(event_id)
        if event is None:
            unresolved_plot_types.append({"event_id": event_id, "reason": "missing_event"})
            continue
        selected["plot_events"][event_id] = event
        if int(event["target_update_method_id"]) in (5, 6, 7):
            aoe_shape_id = int(event["target_update_method_param1"])
            if aoe_shape_id > 0:
                aoe_shape_ids.add(aoe_shape_id)
                shape = aoe_shape_by_id.get(aoe_shape_id)
                if shape:
                    selected["aoe_shapes"][aoe_shape_id] = shape
        for relation in next_by_event.get(event_id, []):
            selected["plot_next_events"][int(relation["id"])] = relation
            event_queue.append(int(relation["next_event_id"]))
        for relation in event_conditions_by_event.get(event_id, []):
            selected["plot_event_conditions"][int(relation["id"])] = relation
            condition = condition_by_id.get(int(relation["condition_id"]))
            if condition:
                selected["plot_conditions"][int(condition["id"])] = condition
        for relation in aoe_conditions_by_event.get(event_id, []):
            selected["plot_aoe_conditions"][int(relation["id"])] = relation
            condition = condition_by_id.get(int(relation["condition_id"]))
            if condition:
                selected["plot_conditions"][int(condition["id"])] = condition
        for relation in effects_by_event.get(event_id, []):
            relation = dict(relation)
            actual_type = str(relation["actual_type"])
            actual_type = plot_type_map.get(actual_type, actual_type)
            relation["actual_type"] = actual_type
            selected["plot_effects"][int(relation["id"])] = relation
            if actual_type.startswith("<ref:"):
                unresolved_plot_types.append(relation)
            else:
                select_concrete(actual_type, int(relation["actual_id"]))

    # Plot effects can add buffs. Buff relations can then add more generic effects.
    buffs_by_id = relationships["buffs_by_id"]
    relation_groups = {
        table: grouped(rows, "buff_id")
        for table, rows in relationships["buff_relations"].items()
    }
    reached_buffs: set[int] = set()
    buff_link_fields = (
        "aura_slave_buff_id", "crowd_buff_id", "link_buff_id", "require_buff_id",
        "transform_buff_id",
    )
    # A trigger effect may add another buff and that buff may add another
    # trigger.  Drain both queues to a fixed point; a single buff/effect pass
    # silently truncated valid AA8 dependency graphs.
    while buff_queue or effect_queue:
        while buff_queue:
            buff_id = buff_queue.popleft()
            if buff_id <= 0 or buff_id in reached_buffs:
                continue
            reached_buffs.add(buff_id)
            buff = buffs_by_id.get(buff_id)
            if buff is None:
                unresolved_effect_types.append(
                    {"buff_id": buff_id, "reason": "missing_native_buff"}
                )
                continue
            selected["buffs"][buff_id] = buff
            for field in buff_link_fields:
                if int(buff.get(field) or 0):
                    buff_queue.append(int(buff[field]))
            for field in (
                "anim_action_id",
                "anim_start_id",
                "anim_end_id",
                "tick_anim_id",
            ):
                if int(buff.get(field) or 0):
                    anim_ids.add(int(buff[field]))
            if int(buff.get("skill_controller_id") or 0):
                controller_ids.add(int(buff["skill_controller_id"]))
            for table, groups in relation_groups.items():
                for relation in groups.get(buff_id, []):
                    selected[table][int(relation["id"])] = relation
                    if table in ("buff_tick_effects", "buff_triggers"):
                        effect_queue.append(int(relation["effect_id"]))

        while effect_queue:
            effect_id = effect_queue.popleft()
            if effect_id in reached_effects:
                continue
            reached_effects.add(effect_id)
            effect = all_effects.get(effect_id)
            if effect is None:
                unresolved_effect_types.append(
                    {"effect_id": effect_id, "reason": "missing_effect_row"}
                )
                continue
            actual_type = effect_type_map.get(
                str(effect["actual_type"]), str(effect["actual_type"])
            )
            effect = {**effect, "actual_type": actual_type}
            selected["effects"][effect_id] = effect
            select_concrete(actual_type, int(effect["actual_id"]))

    controller_by_id = indexed(native["skill_controllers"])
    for controller_id in sorted(controller_ids):
        row = controller_by_id.get(controller_id)
        if row:
            selected["skill_controllers"][controller_id] = row
            for field in ("start_anim_id", "end_anim_id", "transition_anim_1_id", "transition_anim_2_id"):
                if int(row.get(field) or 0):
                    anim_ids.add(int(row[field]))
    projectile_by_id = indexed(native["projectiles"])
    for projectile_id in sorted(projectile_ids):
        if projectile_id in projectile_by_id:
            selected["projectiles"][projectile_id] = projectile_by_id[projectile_id]
    anim_by_id = indexed(native["anims"])
    for anim_id in sorted(anim_ids):
        if anim_id in anim_by_id:
            selected["anims"][anim_id] = anim_by_id[anim_id]

    tables = {
        table: [rows[key] for key in sorted(rows)]
        for table, rows in sorted(selected.items())
    }
    diagnostics = {
        "effect_type_reference_map": effect_type_map,
        "effect_type_reference_evidence": effect_type_evidence,
        "plot_type_reference_map": plot_type_map,
        "plot_type_reference_evidence": plot_type_evidence,
        "unresolved_effect_dependencies": unresolved_effect_types,
        "unresolved_plot_types": unresolved_plot_types,
        "reached_skill_ids": sorted(skill_ids),
        "chained_skill_ids_requested": sorted(chained_skill_ids),
        "reached_plot_ids": sorted(plot_ids),
        "reached_event_ids": sorted(reached_events),
        "reached_buff_ids": sorted(reached_buffs),
        "animation_ids_requested": sorted(anim_ids),
        "animation_ids_missing": sorted(anim_ids.difference(anim_by_id)),
        "controller_ids_missing": sorted(controller_ids.difference(controller_by_id)),
        "projectile_ids_missing": sorted(projectile_ids.difference(projectile_by_id)),
        "aoe_shape_ids_requested": sorted(aoe_shape_ids),
        "aoe_shape_ids_missing": sorted(aoe_shape_ids.difference(aoe_shape_by_id)),
    }
    return tables, diagnostics


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    args = parse_args()
    for path in (args.client_compact, args.runtime_compact, args.server_reference, args.client_game_stream):
        if not path.is_file():
            raise FileNotFoundError(path)
    relationships = extract_client_relationships(args.client_game_stream)
    native, native_ranges = extract_native_tables(args.client_game_stream)
    client = open_read_only(args.client_compact)
    server = open_read_only(args.server_reference)
    runtime = open_read_only(args.runtime_compact)
    try:
        tables, diagnostics = build_closure(client, server, relationships, native)
        runtime_tables = {row[0] for row in runtime.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        runtime_counts = {
            table: runtime.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in sorted(tables)
            if table in runtime_tables
        }
    finally:
        runtime.close()
        server.close()
        client.close()
    manifest = {
        "format_version": 1,
        "ability": {"id": ABILITY_ID, "name": ABILITY_NAME},
        "sources": {
            "client_compact": {"path": str(args.client_compact.resolve()), "sha256": sha256_file(args.client_compact)},
            "runtime_compact": {"path": str(args.runtime_compact.resolve()), "sha256": sha256_file(args.runtime_compact)},
            "server_reference": {"path": str(args.server_reference.resolve()), "sha256": sha256_file(args.server_reference)},
            "client_game_stream": {"path": str(args.client_game_stream.resolve()), "sha256": sha256_file(args.client_game_stream)},
        },
        "authority_order": ["client_compact_8", "game11", "x2game_dll", "observed_protocol", "historical_reference"],
        "native_cached_ranges": {**relationships["result_ranges"], **native_ranges},
        "table_counts": {table: len(rows) for table, rows in sorted(tables.items())},
        "runtime_baseline_counts": runtime_counts,
        "diagnostics": diagnostics,
        "tables": tables,
    }
    if args.verify:
        if len(tables.get("skills", [])) != 46:
            raise RuntimeError("Expected 46 Swiftblade skill rows")
        visible = [row for row in tables["skills"] if int(row.get("show") or 0)]
        if len(visible) != 12:
            raise RuntimeError(f"Expected 12 visible Swiftblade skills, found {len(visible)}")
        passives = tables.get("passive_buffs", [])
        if len(passives) != 6:
            raise RuntimeError(f"Expected 6 Swiftblade passives, found {len(passives)}")
        golden = {
            40331: [("DamageEffect", 12250), ("SpecialEffect", 42648)],
            40337: [("DamageEffect", 12257)],
        }
        effects = indexed(tables.get("effects", []))
        relation_groups = grouped(tables.get("skill_effects", []), "skill_id")
        for skill_id, expected in golden.items():
            actual = []
            for relation in relation_groups.get(skill_id, []):
                effect = effects[int(relation["effect_id"])]
                actual.append((effect["actual_type"], int(effect["actual_id"])))
            if actual != expected:
                raise RuntimeError(f"Golden chain mismatch for {skill_id}: {actual}")
        if len(relation_groups.get(40339, [])) != 9:
            raise RuntimeError("Expected nine native relations for Sinister Strike 40339")
        if diagnostics["aoe_shape_ids_missing"]:
            raise RuntimeError(
                f"Missing native AoE shapes: {diagnostics['aoe_shape_ids_missing']}"
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(manifest), encoding="utf-8")
    verify_copy = json.loads(args.output.read_text(encoding="utf-8"))
    if canonical_json(verify_copy) != canonical_json(manifest):
        raise RuntimeError("Manifest round-trip is not deterministic")
    print(canonical_json({
        "output": str(args.output.resolve()),
        "sha256": sha256_file(args.output),
        "table_counts": manifest["table_counts"],
        "unresolved_effect_dependencies": len(diagnostics["unresolved_effect_dependencies"]),
        "unresolved_plot_types": len(diagnostics["unresolved_plot_types"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
