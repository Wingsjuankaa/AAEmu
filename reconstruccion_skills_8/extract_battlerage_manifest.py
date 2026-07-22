#!/usr/bin/env python3
"""Build a reproducible Battlerage catalogue for the ArcheAge 8.0 port.

The Kakao 8.0 research SQLite is a client-side query view, not a complete
server compact.  This tool therefore keeps client 8.0, runtime and historical
server-reference data separate and records the source of every relationship.
All SQLite inputs are opened read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import struct
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


FORMAT_VERSION = 1
ABILITY_ID = 1
ABILITY_NAME = "Battlerage"
SIMPLE_VALIDATION_SKILL_ID = 32040
COMPLEX_VALIDATION_SKILL_ID = 23587

SKILL_EFFECT_COLUMNS = (
    "id always_hit application_method_id back chance check_no_source_tag_src "
    "check_no_target_tag_src check_source_tag_src check_target_tag_src "
    "consume_item_count consume_item_id consume_source_item effect_id "
    "end_casting_use_chance end_combat_resource end_level excute_effect_on_fire "
    "friendly front interaction_success_hit item_set_id non_friendly skill_id "
    "source_buff_stack_count_max source_buff_stack_count_min source_buff_tag_id "
    "source_except_buff_stack_count_max source_except_buff_stack_count_min "
    "source_nobuff_tag_id start_casting_use_chance start_combat_resource "
    "start_level synergy_text target_buff_stack_count_max target_buff_stack_count_min "
    "target_buff_tag_id target_combat_resource_id target_except_buff_stack_count_max "
    "target_except_buff_stack_count_min target_nobuff_tag_id target_npc_tag_id weight"
).split()

SKILL_EFFECT_LAYOUT = (
    "68 38 68 38 68 38 38 38 38 68 68 38 68 68 68 68 38 38 38 38 68 "
    "38 68 68 68 68 68 68 68 68 68 68 38 68 68 68 68 68 68 68 68 68"
).split()

PASSIVE_BUFF_COLUMNS = "id ability_id active buff_id level req_points skill_points".split()
PASSIVE_BUFF_LAYOUT = "68 68 38 68 68 68 68".split()

BUFF_COLUMNS = (
    "id active_weapon_id add_duration_buff_mul add_duration_buff_id ag_stance "
    "alive_not_applicable anim_action_id anim_end_id anim_start_id anti_stealth "
    "aura_child_only aura_creator_only aura_max_count aura_radius aura_relation_id "
    "aura_slave_buff_id balance_level blank_minded boss_telescope_range cannot_jump "
    "combat_resource_id combat_text_end combat_text_start conditional_tick "
    "cooldown_skill_id cooldown_skill_tag_id cooldown_skill_time crime crippled "
    "crowd_buff_id crowd_check_buff_tag_id crowd_check_buff_id crowd_check_owner "
    "crowd_friendly crowd_hostile crowd_number crowd_radius "
    "custom_dual_material_fade_time custom_dual_material_id damage_absorption_per_hit "
    "damage_absorption_type_id dead_applicable desc detect_stealth "
    "disarmament_main_hand disarmament_musical disarmament_off_hand "
    "disarmament_ranged do_not_remove_by_other_skill_controller drowning_immortality "
    "duration evade_telescope exempt faction_id fall_damage_immortality "
    "fall_damage_immune fastened find_school_of_fish_range fix_ability_level_to_one "
    "framehold freeze_ship fx_group_id gliding gliding_fall_speed_fast "
    "gliding_fall_speed_normal gliding_fall_speed_slow gliding_land_height "
    "gliding_lift_count gliding_lift_duration gliding_lift_height gliding_lift_speed "
    "gliding_lift_valid_time gliding_move_speed_fast gliding_move_speed_normal "
    "gliding_move_speed_slow gliding_rotate_speed gliding_sliding_time "
    "gliding_smooth_time gliding_startup_speed gliding_startup_time group_id "
    "group_rank head_scale icon_id idle_anim immune_damage immune_except_creator "
    "immune_except_creator_relation_id immune_except_creator_relation_check "
    "immune_except_skill_tag_id immune_health impossible_change_targeting "
    "impossible_rotate impossible_targeting init_max_charge init_min_charge kind_id "
    "knock_down knockback_immune level_duration link_buff_id mainhand_tool_id "
    "mana_burn_immune mana_shield_ratio max_charge max_combat_resource max_life_time "
    "max_stack melee_immortality melee_immune min_combat_resource name no_collide "
    "no_collide_rigid no_exp_penalty non_pushable not_to_mate_rider "
    "not_to_slave_rider off_passive off_passive_exection_tag_id offhand_tool_id "
    "one_time one_time_immortality only_my_pet only_pet_owner owner_only pacifist "
    "per_unit_creation percussion_instrument_start_anim_id "
    "percussion_instrument_tick_anim_id psychokinesis psychokinesis_speed ragdoll "
    "ranged_immortality ranged_immune real_time reflection_chance reflection_heal "
    "reflection_ignore_attacker reflection_ignore_defender reflection_melee "
    "reflection_ranged reflection_ratio reflection_siege reflection_spell "
    "reflection_target_ratio remove_by_summoned remove_on_attack_buff_trigger "
    "remove_on_attack_etc remove_on_attack_etc_dot remove_on_attack_spell_dot "
    "remove_on_attacked_buff_trigger remove_on_attacked_etc remove_on_attacked_etc_dot "
    "remove_on_attacked_spell_dot remove_on_autoattack remove_on_change_equipments "
    "remove_on_damage_buff_trigger remove_on_damage_etc remove_on_damage_etc_dot "
    "remove_on_damage_spell_dot remove_on_damaged_buff_trigger remove_on_damaged_etc "
    "remove_on_damaged_etc_dot remove_on_damaged_spell_dot remove_on_death "
    "remove_on_exempt remove_on_interaction remove_on_land remove_on_mount "
    "remove_on_move remove_on_source_dead remove_on_start_skill remove_on_unbond "
    "remove_on_unmount remove_on_unmount_attach_point_id remove_on_use_skill "
    "require_buff_id restrict_actionbar resurrection_health resurrection_mana "
    "resurrection_percent root save_pos save_rule_id scale scaleDuration set_head_scale "
    "siege_immortality siege_immune silence skill_controller_id slave_applicable sleep "
    "spell_immortality spell_immune sprint_motion stack_rule_id stealth "
    "stop_online_lp_regen string_instrument_start_anim_id string_instrument_tick_anim_id "
    "stun system targeting_relation_id targeting_use_origin_source taunt "
    "taunt_with_top_aggro telescope_range tick tick_active_weapon_id tick_anim_id "
    "tick_area_angle tick_area_exclude_source tick_area_front_angle "
    "tick_area_max_count tick_area_radius tick_area_relation_id "
    "tick_area_use_origin_source tick_level_mana_cost tick_mainhand_tool_id "
    "tick_mana_cost tick_offhand_tool_id transfer_telescope_range transform_buff_id "
    "transparent tube_instrument_start_anim_id tube_instrument_tick_anim_id "
    "use_source_faction walk_only"
).split()

BUFF_LAYOUT = (
    "68 68 68 68 78 38 68 68 68 38 38 38 68 68 68 68 68 38 60 38 68 38 "
    "38 38 68 68 68 38 38 68 68 68 38 38 38 68 60 60 68 68 68 38 78 38 "
    "38 38 38 38 38 38 68 38 38 68 38 38 38 60 38 38 38 68 38 60 60 60 "
    "60 68 60 60 60 60 60 60 60 68 60 60 60 60 68 68 60 68 78 68 38 68 "
    "38 68 60 38 38 38 68 68 68 38 38 68 68 68 38 68 68 68 68 68 38 38 "
    "68 78 38 38 38 38 38 38 38 68 68 38 38 38 38 38 38 38 68 68 38 60 "
    "38 38 38 38 68 38 38 38 38 38 68 38 38 68 38 38 38 38 38 38 38 38 "
    "38 38 70 38 38 38 38 38 38 38 38 38 38 38 38 38 38 38 38 38 38 "
    "68 38 68 38 68 68 38 38 38 68 60 60 38 38 38 38 68 38 38 38 38 38 "
    "68 38 38 68 68 38 38 68 38 38 38 60 68 68 68 68 38 68 68 60 68 38 "
    "60 68 68 68 60 68 38 68 68 38 38"
).split()

BUFF_RESULT_SPEC = {
    "columns": BUFF_COLUMNS,
    "layout": BUFF_LAYOUT,
    "start": 0x2A1FE8F,
    "expected_rows": 27303,
    "anchor_id": 828,
    "anchor_values": {
        "duration": 7000,
        "group_id": 63,
        "icon_id": 6908,
        "max_stack": 1,
    },
    "layout_source": (
        "x2game.dll FUN_39a2ae70 embedded SELECT and column accessor calls 0..229"
    ),
}

CLIENT_BUFF_RELATION_RESULT_SPECS = {
    "buff_tick_effects": {
        "columns": (
            "id buff_id check_no_target_tag_src check_target_tag_src effect_id "
            "or_unit_reqs target_buff_tag_id target_nobuff_tag_id"
        ).split(),
        "layout": "68 68 38 38 68 38 68 68".split(),
        "anchor_id": 6,
        "anchor_values": {"buff_id": 31, "effect_id": 285},
        "layout_source": "x2game.dll FUN_39a2a190 column accessor calls 0..7",
    },
    "buff_triggers": {
        "columns": (
            "id buff_id check_no_tag_src_in_owner check_no_tag_src_in_source "
            "check_no_tag_src_in_target check_tag_src_in_owner check_tag_src_in_source "
            "check_tag_src_in_target delay_time effect_id event_id or_unit_reqs "
            "owner_buff_tag_id owner_no_buff_tag_id source_agent_id source_buff_tag_id "
            "source_no_buff_tag_id target_agent_id target_buff_tag_id "
            "target_no_buff_tag_id use_collision_impact use_damage_amount use_stack_count"
        ).split(),
        "layout": (
            "68 68 38 38 38 38 38 38 68 68 68 38 68 68 68 68 68 68 68 68 "
            "38 38 38"
        ).split(),
        "anchor_id": 22,
        "anchor_values": {"buff_id": 114, "effect_id": 630, "event_id": 6},
        "layout_source": "x2game.dll FUN_39a29860 column accessor calls 0..22",
    },
    "buff_unit_modifiers": {
        "columns": "id owner_type owner_id buff_id tag_id".split(),
        "layout": "68 78 68 68 68".split(),
        "anchor_id": 9,
        "anchor_values": {"owner_id": 357, "buff_id": 0, "tag_id": 55},
        "layout_source": "x2game.dll FUN_39978e50 column accessor calls 0..4",
    },
    "tagged_buffs": {
        "columns": "id buff_id tag_id".split(),
        "layout": "68 68 68".split(),
        "anchor_id": 356,
        "anchor_values": {"buff_id": 828, "tag_id": 216},
        "layout_source": "x2game.dll FUN_39a29620 column accessor calls 0..2",
    },
}

CLIENT_CONCRETE_RESULT_SPECS = {
    "buff_effects": {
        "columns": "id ab_level buff_id chance stack".split(),
        "layout": "68 68 68 68 68".split(),
        "anchor_id": 11084,
        "anchor_values": {"buff_id": 828, "chance": 100, "stack": 1},
    },
    "conversion_effects": {
        "columns": "id category_id source_category_id source_value target_category_id target_value".split(),
        "layout": "68 68 68 68 68 68".split(),
        "anchor_id": 11,
        "anchor_values": {
            "category_id": 2,
            "source_category_id": 2,
            "source_value": 20,
            "target_category_id": 4,
            "target_value": 50,
        },
    },
    "damage_effects": {
        "columns": (
            "id actability_add actability_group_id actability_mul actability_step "
            "adjust_damage_by_height adjust_damage_by_range aggro_multiplier "
            "cancel_protection charged_buff_id charged_level_mul charged_mul "
            "combat_resource_dps_md combat_resource_level_md combat_resource_md "
            "crime critical_bonus damage_type_id dps_inc_multiplier dps_multiplier "
            "engage_combat fire_proc fixed_max fixed_min fixed_type health_steal_ratio "
            "hit_anim_timing_id level_md level_va_end level_va_start mana_damage "
            "mana_steal_ratio multiplier optimum_range percent_max percent_min "
            "range_damage_multipier synergy target_buff_bonus target_buff_bonus_mul "
            "target_buff_tag_id target_charged_buff_id target_charged_mul "
            "target_health_add target_health_max target_health_min target_health_mul "
            "use_charged_buff use_combat_resource use_current_health use_element_effect "
            "use_fixed_damage use_level_damage use_mainhand_weapon use_offhand_weapon "
            "use_percent_damage use_ranged_weapon use_source_health "
            "use_target_charged_buff weapon_slot_id"
        ).split(),
        "layout": (
            "68 60 68 60 68 38 38 60 38 68 60 60 60 60 60 38 68 68 60 60 "
            "38 38 68 68 38 68 68 60 68 68 38 68 60 60 68 68 60 38 68 60 "
            "68 68 60 68 68 68 60 38 38 38 38 38 38 38 38 38 38 38 38 68"
        ).split(),
        "anchor_id": 5347,
        "anchor_values": {
            "adjust_damage_by_height": 1,
            "damage_type_id": 1,
            "hit_anim_timing_id": 1,
            "level_md": 2.0,
            "weapon_slot_id": 15,
        },
        "layout_source": "x2game.dll FUN_3996b1d0 column accessor calls",
    },
    "physical_explosion_effects": {
        "columns": "id hole_size pressure radius".split(),
        "layout": "68 60 60 60".split(),
        "anchor_id": 113,
        "anchor_values": {"hole_size": 1.0, "pressure": 100.0, "radius": 5.0},
    },
    "special_effects": {
        "columns": "id special_effect_type_id value1 value2 value3 value4 value5 value6 value7".split(),
        "layout": "68 68 68 68 68 68 68 68 68".split(),
        "anchor_id": 23306,
        "anchor_values": {
            "special_effect_type_id": 48,
            "value1": 32049,
            "value2": 1500,
        },
    },
}

SKILL_FIELDS = {
    "progression": (
        "ability_id",
        "ability_level",
        "level_step",
        "req_points",
        "skill_points",
        "show",
        "auto_learn",
        "need_learn",
        "precedence_skill_id",
    ),
    "resources": (
        "mana_cost",
        "mana_level_md",
        "cost",
        "consume_lp",
        "combat_resource_id",
        "min_combat_resource",
        "max_combat_resource",
        "high_ability_id",
        "min_high_ability_resource",
        "max_high_ability_resource",
    ),
    "timing": (
        "default_gcd",
        "custom_gcd",
        "cooldown_time",
        "cooldown_tag_id",
        "second_cooldown_tag_id",
        "third_cooldown_tag_id",
        "casting_time",
        "casting_inc",
        "channeling_time",
        "channeling_tick",
        "repeat_count",
        "repeat_tick",
        "effect_delay",
        "effect_repeat_count",
        "effect_repeat_tick",
    ),
    "targeting": (
        "target_type_id",
        "target_selection_id",
        "target_relation_id",
        "target_unit_param",
        "min_range",
        "max_range",
        "target_angle",
        "target_area_count",
        "target_area_radius",
        "target_area_angle",
        "front_angle",
        "valid_height",
        "target_valid_height",
        "check_obstacle",
        "check_terrain",
    ),
    "presentation": (
        "start_anim_id",
        "fire_anim_id",
        "channeling_anim_id",
        "fx_group_id",
        "projectile_id",
        "skill_controller_id",
        "skill_controller_at_end",
        "end_skill_controller",
        "icon_id",
    ),
    "buff_links": (
        "toggle_buff_id",
        "channeling_buff_id",
        "channeling_target_buff_id",
        "cancel_ongoing_buff_exception_tag_id",
        "cooldown_tag_id",
    ),
}

RELATED_SKILL_TABLES = (
    "skill_reagents",
    "skill_products",
    "skill_synergy_icons",
    "tagged_skills",
    "skill_modifiers",
)

RELATED_BUFF_TABLES = (
    "buff_tick_effects",
    "buff_triggers",
    "buff_unit_modifiers",
    "tagged_buffs",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--runtime-compact", required=True, type=Path)
    parser.add_argument("--server-reference", required=True, type=Path)
    parser.add_argument(
        "--client-game-stream",
        required=True,
        type=Path,
        help="Decrypted Kakao 8.0 game11 cached-query stream",
    )
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ability-id", default=ABILITY_ID, type=int)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def open_read_only(path: Path) -> sqlite3.Connection:
    resolved = path.resolve()
    connection = sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


class CachedResultReader:
    """Reader for the SQLite cached-result encoding used by Kakao game11."""

    def __init__(self, data: bytes):
        self.data = data

    def string(self, offset: int) -> tuple[str | None, int]:
        tag = self.data[offset]
        offset += 1
        if tag == 2:
            return None, offset
        if tag == 0:
            end = self.data.index(0, offset)
            return self.data[offset:end].decode("utf-8", "replace"), end + 1
        reference = struct.unpack_from("<I", self.data, offset)[0]
        offset += 4
        if reference == 0xFFFFFFFF:
            end = self.data.index(0, offset)
            return self.data[offset:end].decode("utf-8", "replace"), end + 1
        return f"<ref:{reference}>", offset

    def row(self, offset: int, layout: list[str]) -> tuple[list[Any], int]:
        if self.data[offset] != 100:
            raise ValueError(f"Expected SQLITE_ROW at 0x{offset:x}")
        offset += 1
        values: list[Any] = []
        for field_type in layout:
            if field_type == "38":
                values.append(self.data[offset])
                offset += 1
            elif field_type == "68":
                values.append(struct.unpack_from("<i", self.data, offset)[0])
                offset += 4
            elif field_type in ("40", "70"):
                values.append(struct.unpack_from("<q", self.data, offset)[0])
                offset += 8
            elif field_type == "60":
                values.append(struct.unpack_from("<d", self.data, offset)[0])
                offset += 8
            elif field_type == "78":
                value, offset = self.string(offset)
                values.append(value)
            else:
                raise ValueError(f"Unsupported cached-result field type {field_type}")
        return values, offset


def find_result_start(reader: CachedResultReader, seed: int, layout: list[str]) -> int:
    current = seed
    while True:
        candidate = current
        lower = max(0, current - 8192)
        found = None
        while True:
            candidate = reader.data.rfind(b"\x64", lower, candidate)
            if candidate < 0:
                break
            try:
                _, end = reader.row(candidate, layout)
                if end == current:
                    found = candidate
                    break
            except (IndexError, ValueError, struct.error):
                pass
        if found is None:
            return current
        current = found


def read_cached_result(
    reader: CachedResultReader, start: int, layout: list[str]
) -> tuple[list[list[Any]], int]:
    rows: list[list[Any]] = []
    cursor = start
    while reader.data[cursor] == 100:
        row, cursor = reader.row(cursor, layout)
        rows.append(row)
    if reader.data[cursor] != 101:
        raise ValueError(f"Cached result does not end in SQLITE_DONE at 0x{cursor:x}")
    return rows, cursor


def locate_cached_result(
    reader: CachedResultReader,
    columns: list[str],
    layout: list[str],
    anchor_id: int,
    anchor_values: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if len(columns) != len(layout):
        raise ValueError("Cached-result columns and layout do not match")
    pattern = b"\x64" + struct.pack("<i", anchor_id)
    matches: list[int] = []
    cursor = 0
    while True:
        cursor = reader.data.find(pattern, cursor)
        if cursor < 0:
            break
        try:
            values, end = reader.row(cursor, layout)
            row = dict(zip(columns, values))
            if (
                end < len(reader.data)
                and reader.data[end] in (100, 101)
                and all(row.get(key) == value for key, value in anchor_values.items())
            ):
                matches.append(cursor)
        except (IndexError, ValueError, struct.error):
            pass
        cursor += 1
    if len(matches) != 1:
        raise ValueError(
            f"Expected one cached-result anchor for id {anchor_id}, found {len(matches)}"
        )
    start = find_result_start(reader, matches[0], layout)
    rows, end = read_cached_result(reader, start, layout)
    return [dict(zip(columns, row)) for row in rows], {
        "start": start,
        "end": end,
        "rows": len(rows),
        "anchor": matches[0],
    }


def extract_client_relationships(path: Path) -> dict[str, Any]:
    reader = CachedResultReader(path.read_bytes())
    skill_effects, skill_effect_range = locate_cached_result(
        reader,
        SKILL_EFFECT_COLUMNS,
        SKILL_EFFECT_LAYOUT,
        25615,
        {"skill_id": 23136, "effect_id": 32720},
    )
    passive_buffs, passive_range = locate_cached_result(
        reader,
        PASSIVE_BUFF_COLUMNS,
        PASSIVE_BUFF_LAYOUT,
        244,
        {
            "ability_id": 1,
            "active": 0,
            "buff_id": 7544,
            "level": 1,
            "req_points": 8,
            "skill_points": 0,
        },
    )
    raw_buffs, buffs_end = read_cached_result(
        reader,
        BUFF_RESULT_SPEC["start"],
        BUFF_RESULT_SPEC["layout"],
    )
    buffs = [
        dict(zip(BUFF_RESULT_SPEC["columns"], row))
        for row in raw_buffs
    ]
    if len(buffs) != BUFF_RESULT_SPEC["expected_rows"]:
        raise RuntimeError(
            f"buffs cached range has {len(buffs)} rows; "
            f"expected {BUFF_RESULT_SPEC['expected_rows']}"
        )
    anchors = [
        row for row in buffs
        if int(row["id"]) == BUFF_RESULT_SPEC["anchor_id"]
        and all(
            row.get(key) == value
            for key, value in BUFF_RESULT_SPEC["anchor_values"].items()
        )
    ]
    if len(anchors) != 1:
        raise RuntimeError("buffs cached range failed its confirmed anchor")
    buffs_range = {
        "start": BUFF_RESULT_SPEC["start"],
        "end": buffs_end,
        "rows": len(buffs),
        "anchor": BUFF_RESULT_SPEC["start"],
    }
    buffs_range["layout_source"] = BUFF_RESULT_SPEC["layout_source"]
    buff_relations: dict[str, list[dict[str, Any]]] = {}
    buff_relation_ranges: dict[str, dict[str, Any]] = {}
    for table, spec in CLIENT_BUFF_RELATION_RESULT_SPECS.items():
        rows, result_range = locate_cached_result(
            reader,
            spec["columns"],
            spec["layout"],
            spec["anchor_id"],
            spec["anchor_values"],
        )
        result_range["layout_source"] = spec["layout_source"]
        buff_relations[table] = rows
        buff_relation_ranges[table] = result_range
    concrete_effects: dict[str, list[dict[str, Any]]] = {}
    concrete_ranges: dict[str, dict[str, Any]] = {}
    for table, spec in CLIENT_CONCRETE_RESULT_SPECS.items():
        rows, result_range = locate_cached_result(
            reader,
            spec["columns"],
            spec["layout"],
            spec["anchor_id"],
            spec["anchor_values"],
        )
        result_range["layout_source"] = spec.get(
            "layout_source", "embedded SQL plus clean cached-result boundary validation"
        )
        concrete_effects[table] = rows
        concrete_ranges[table] = result_range
    return {
        "source": {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        },
        "result_ranges": {
            "skill_effects": skill_effect_range,
            "passive_buffs": passive_range,
            "buffs": buffs_range,
            **buff_relation_ranges,
            **concrete_ranges,
        },
        "skill_effects": skill_effects,
        "passive_buffs": passive_buffs,
        "buffs": buffs,
        "buffs_by_id": {int(row["id"]): row for row in buffs},
        "buff_relations": buff_relations,
        "concrete_effects": concrete_effects,
    }


def quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )
    }


def table_columns(connection: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return list(connection.execute(f"PRAGMA table_info({quoted(table)})"))


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def canonical_value(value: Any) -> bytes:
    if value is None:
        return b"N"
    if isinstance(value, bytes):
        return b"B" + len(value).to_bytes(8, "little") + value
    if isinstance(value, str):
        encoded = value.encode("utf-8", "surrogatepass")
        return b"S" + len(encoded).to_bytes(8, "little") + encoded
    if isinstance(value, int):
        return b"I" + str(value).encode("ascii") + b";"
    if isinstance(value, float):
        return b"F" + value.hex().encode("ascii") + b";"
    encoded = repr(value).encode("utf-8", "backslashreplace")
    return b"R" + len(encoded).to_bytes(8, "little") + encoded


def table_fingerprint(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    master = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    schema_sql = master[0] if master and master[0] else ""
    columns = table_columns(connection, table)
    schema = [
        {
            "name": row[1],
            "type": row[2],
            "not_null": bool(row[3]),
            "default": row[4],
            "primary_key_order": row[5],
        }
        for row in columns
    ]
    digest = hashlib.sha256()
    digest.update(json.dumps(schema, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    row_count = 0
    query = f"SELECT * FROM {quoted(table)}"
    try:
        cursor = connection.execute(query + " ORDER BY rowid")
    except sqlite3.OperationalError:
        primary_keys = [row[1] for row in columns if row[5]]
        if primary_keys:
            order = ", ".join(quoted(name) for name in primary_keys)
            cursor = connection.execute(query + f" ORDER BY {order}")
        else:
            cursor = connection.execute(query)
    for row in cursor:
        row_count += 1
        digest.update(b"[")
        for value in row:
            digest.update(canonical_value(value))
        digest.update(b"]")
    return {
        "rows": row_count,
        "columns": len(columns),
        "schema_hash": hashlib.sha256(schema_sql.encode("utf-8")).hexdigest().upper(),
        "content_hash": digest.hexdigest().upper(),
        "schema": schema,
    }


def source_metadata(path: Path, connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "sha256": sha256_file(path),
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "table_count": len(table_names(connection)),
    }


def same_table(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    return bool(
        left
        and right
        and left["schema_hash"] == right["schema_hash"]
        and left["content_hash"] == right["content_hash"]
    )


def classify_runtime_table(
    client: dict[str, Any] | None,
    runtime: dict[str, Any] | None,
    server: dict[str, Any] | None,
) -> str:
    if runtime is None:
        return "not_in_runtime"
    if same_table(runtime, client):
        return "client_8_exact"
    if same_table(runtime, server):
        return "server_reference_exact"
    if client and server:
        return "hybrid_or_modified"
    if server:
        return "modified_server_reference"
    if client:
        return "modified_client_8"
    return "runtime_only"


def build_provenance(
    client_path: Path,
    runtime_path: Path,
    server_path: Path,
    client: sqlite3.Connection,
    runtime: sqlite3.Connection,
    server: sqlite3.Connection,
) -> dict[str, Any]:
    connections = {"client_8": client, "runtime": runtime, "server_reference": server}
    paths = {"client_8": client_path, "runtime": runtime_path, "server_reference": server_path}
    names = {key: table_names(value) for key, value in connections.items()}
    fingerprints: dict[str, dict[str, Any]] = {key: {} for key in connections}
    for source, connection in connections.items():
        for table in sorted(names[source]):
            fingerprints[source][table] = table_fingerprint(connection, table)

    tables: dict[str, Any] = {}
    for table in sorted(set().union(*names.values())):
        entries = {
            source: fingerprints[source].get(table)
            for source in ("client_8", "runtime", "server_reference")
        }
        tables[table] = {
            "runtime_provenance": classify_runtime_table(
                entries["client_8"], entries["runtime"], entries["server_reference"]
            ),
            "sources": entries,
        }

    counts = defaultdict(int)
    for entry in tables.values():
        counts[entry["runtime_provenance"]] += 1
    return {
        "format_version": FORMAT_VERSION,
        "sources": {
            key: source_metadata(paths[key], connections[key]) for key in connections
        },
        "summary": dict(sorted(counts.items())),
        "tables": tables,
    }


def select_existing_fields(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result: dict[str, Any] = {
        "id": row.get("id"),
        "stored_name": row.get("name"),
        "stored_description": row.get("desc"),
    }
    for section, fields in SKILL_FIELDS.items():
        values = {field: row[field] for field in fields if field in row}
        if values:
            result[section] = values
    return result


def localized_skill_texts(
    client: sqlite3.Connection, client_tables: set[str], skill_id: int
) -> dict[str, str]:
    return localized_table_texts(client, client_tables, "skills", skill_id)


def localized_table_texts(
    client: sqlite3.Connection,
    client_tables: set[str],
    table: str,
    row_id: int,
) -> dict[str, str]:
    if "localized_texts" not in client_tables:
        return {}
    return {
        row[0]: row[1]
        for row in client.execute(
            "SELECT tbl_column_name, text FROM localized_texts "
            "WHERE tbl_name = ? AND idx = ? AND locale = 'en_us' "
            "ORDER BY tbl_column_name",
            (table, row_id),
        )
    }


def snake_plural(actual_type: str) -> str:
    special = {"Buff": "buffs", "SkillController": "skill_controllers"}
    if actual_type in special:
        return special[actual_type]
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", actual_type).lower()
    if snake.endswith("effect"):
        return snake + "s"
    return snake + "s"


def first_row_by_id(
    connection: sqlite3.Connection,
    tables: set[str],
    table: str,
    row_id: int,
) -> dict[str, Any] | None:
    if table not in tables:
        return None
    columns = {row[1] for row in table_columns(connection, table)}
    if "id" not in columns:
        return None
    return row_to_dict(
        connection.execute(
            f"SELECT * FROM {quoted(table)} WHERE id = ?", (row_id,)
        ).fetchone()
    )


def rows_by_column(
    connection: sqlite3.Connection,
    tables: set[str],
    table: str,
    column: str,
    value: int,
) -> list[dict[str, Any]]:
    if table not in tables:
        return []
    columns = {row[1] for row in table_columns(connection, table)}
    if column not in columns:
        return []
    order = "id" if "id" in columns else column
    return rows_to_dicts(
        connection.execute(
            f"SELECT * FROM {quoted(table)} WHERE {quoted(column)} = ? "
            f"ORDER BY {quoted(order)}",
            (value,),
        )
    )


def native_buff_relation_rows(
    client_relationships: dict[str, Any], table: str, buff_id: int
) -> list[dict[str, Any]]:
    rows = client_relationships["buff_relations"].get(table, [])
    if table != "buff_unit_modifiers":
        return [row for row in rows if int(row["buff_id"]) == buff_id]

    owner_type_map = client_relationships.get(
        "buff_unit_modifier_owner_type_map", {}
    )
    related: list[dict[str, Any]] = []
    for row in rows:
        owner_type = row.get("owner_type")
        resolved_owner_type = owner_type_map.get(str(owner_type), owner_type)
        roles = []
        if resolved_owner_type == "Buff" and int(row["owner_id"]) == buff_id:
            roles.append("owner")
        if int(row["buff_id"]) == buff_id:
            roles.append("referenced_buff")
        if roles:
            related.append(
                {
                    **row,
                    "resolved_owner_type": resolved_owner_type,
                    "relation_roles": roles,
                }
            )
    return related


def runtime_buff_relation_rows(
    runtime: sqlite3.Connection,
    runtime_tables: set[str],
    table: str,
    buff_id: int,
) -> list[dict[str, Any]]:
    if table != "buff_unit_modifiers":
        return rows_by_column(runtime, runtime_tables, table, "buff_id", buff_id)
    if table not in runtime_tables:
        return []
    return rows_to_dicts(
        runtime.execute(
            "SELECT * FROM buff_unit_modifiers "
            "WHERE buff_id = ? OR (owner_type = 'Buff' AND owner_id = ?) "
            "ORDER BY id",
            (buff_id, buff_id),
        )
    )


def buff_snapshot(
    client: sqlite3.Connection,
    runtime: sqlite3.Connection,
    server: sqlite3.Connection,
    client_tables: set[str],
    runtime_tables: set[str],
    server_tables: set[str],
    client_relationships: dict[str, Any],
    buff_id: int,
) -> dict[str, Any]:
    client_buff = client_relationships["buffs_by_id"].get(buff_id)
    return {
        "buff_id": buff_id,
        "localized_text": localized_table_texts(
            client, client_tables, "buffs", buff_id
        ),
        "template": {
            "client_8": client_buff,
            "runtime": first_row_by_id(runtime, runtime_tables, "buffs", buff_id),
            "server_reference": first_row_by_id(
                server, server_tables, "buffs", buff_id
            ),
        },
        "relations": {
            "client_8": {
                table: native_buff_relation_rows(
                    client_relationships, table, buff_id
                )
                for table in RELATED_BUFF_TABLES
            },
            "runtime_reference": {
                table: runtime_buff_relation_rows(
                    runtime, runtime_tables, table, buff_id
                )
                for table in RELATED_BUFF_TABLES
            },
        },
        "relations_source": {
            "client_8": "client_8_game11",
            "runtime_reference": "runtime_historical_reference",
        },
    }


def resolve_effect_type(
    client_effect: dict[str, Any] | None,
    server_effect: dict[str, Any] | None,
    reference_map: dict[str, str],
) -> tuple[str | None, str]:
    if client_effect:
        client_type = client_effect.get("actual_type")
        if client_type and not str(client_type).startswith("<ref:"):
            return str(client_type), "client_8_direct"
        if client_type and str(client_type) in reference_map:
            return (
                reference_map[str(client_type)],
                "client_8_reference_map_from_stable_effect_pairs",
            )
        if (
            server_effect
            and client_effect.get("actual_id") == server_effect.get("actual_id")
            and server_effect.get("actual_type")
        ):
            return str(server_effect["actual_type"]), "cross_version_id_and_actual_id_match"
        return None, "client_8_string_reference_unresolved"
    if server_effect and server_effect.get("actual_type"):
        return str(server_effect["actual_type"]), "server_reference_only"
    return None, "unresolved"


def effect_chain(
    relation: dict[str, Any],
    relation_source: str,
    client: sqlite3.Connection,
    runtime: sqlite3.Connection,
    server: sqlite3.Connection,
    client_tables: set[str],
    runtime_tables: set[str],
    server_tables: set[str],
    effect_reference_map: dict[str, str],
    client_relationships: dict[str, Any],
) -> dict[str, Any]:
    effect_id = int(relation["effect_id"])
    client_effect = first_row_by_id(client, client_tables, "effects", effect_id)
    runtime_effect = first_row_by_id(runtime, runtime_tables, "effects", effect_id)
    server_effect = first_row_by_id(server, server_tables, "effects", effect_id)
    actual_type, resolution = resolve_effect_type(
        client_effect, server_effect, effect_reference_map
    )
    actual_id = None
    if client_effect and client_effect.get("actual_id") is not None:
        actual_id = int(client_effect["actual_id"])
    elif runtime_effect and runtime_effect.get("actual_id") is not None:
        actual_id = int(runtime_effect["actual_id"])
    elif server_effect and server_effect.get("actual_id") is not None:
        actual_id = int(server_effect["actual_id"])

    concrete_table = snake_plural(actual_type) if actual_type else None
    client_concrete = None
    if concrete_table and actual_id is not None:
        client_concrete = next(
            (
                row
                for row in client_relationships["concrete_effects"].get(
                    concrete_table, []
                )
                if int(row["id"]) == actual_id
            ),
            None,
        )
    runtime_concrete = (
        first_row_by_id(runtime, runtime_tables, concrete_table, actual_id)
        if concrete_table and actual_id is not None
        else None
    )
    server_concrete = (
        first_row_by_id(server, server_tables, concrete_table, actual_id)
        if concrete_table and actual_id is not None
        else None
    )
    result: dict[str, Any] = {
        "skill_effect": relation,
        "skill_effect_source": relation_source,
        "effect": {
            "client_8": client_effect,
            "runtime": runtime_effect,
            "server_reference": server_effect,
            "resolved_actual_type": actual_type,
            "type_resolution": resolution,
        },
        "concrete_effect": {
            "table": concrete_table,
            "actual_id": actual_id,
            "client_8": client_concrete,
            "runtime": runtime_concrete,
            "server_reference": server_concrete,
        },
    }
    if actual_type == "BuffEffect" and (client_concrete or runtime_concrete):
        buff_id = (client_concrete or runtime_concrete).get("buff_id")
        if buff_id:
            result["related_buff"] = buff_snapshot(
                client,
                runtime,
                server,
                client_tables,
                runtime_tables,
                server_tables,
                client_relationships,
                int(buff_id),
            )
    return result


def skill_relations(
    skill_id: int,
    client_skill_present: bool,
    client_relationships: dict[str, Any],
    client: sqlite3.Connection,
    runtime: sqlite3.Connection,
    server: sqlite3.Connection,
    client_tables: set[str],
    runtime_tables: set[str],
    server_tables: set[str],
    effect_reference_map: dict[str, str],
) -> dict[str, Any]:
    if client_skill_present:
        relations = sorted(
            (
                row
                for row in client_relationships["skill_effects"]
                if int(row["skill_id"]) == skill_id
            ),
            key=lambda row: int(row["id"]),
        )
        relation_source = "client_8_game11"
    else:
        relations = rows_by_column(
            runtime, runtime_tables, "skill_effects", "skill_id", skill_id
        )
        relation_source = "runtime_server_reference"
    related = {
        table: rows_by_column(runtime, runtime_tables, table, "skill_id", skill_id)
        for table in RELATED_SKILL_TABLES
    }
    req_links = rows_by_column(
        runtime, runtime_tables, "skill_req_skills", "skill_id", skill_id
    )
    related["skill_req_skills"] = req_links
    related["skill_reqs"] = [
        first_row_by_id(
            runtime, runtime_tables, "skill_reqs", int(link["skill_req_id"])
        )
        for link in req_links
    ]
    return {
        "effects": [
            effect_chain(
                relation,
                relation_source,
                client,
                runtime,
                server,
                client_tables,
                runtime_tables,
                server_tables,
                effect_reference_map,
                client_relationships,
            )
            for relation in relations
        ],
        "other_relations": related,
    }


def common_field_differences(
    client_row: dict[str, Any] | None, server_row: dict[str, Any] | None
) -> dict[str, dict[str, Any]]:
    if not client_row or not server_row:
        return {}
    ignored = {"name", "desc"}
    return {
        key: {"client_8": client_row[key], "server_reference": server_row[key]}
        for key in sorted(set(client_row).intersection(server_row) - ignored)
        if client_row[key] != server_row[key]
    }


def build_effect_type_reference_map(
    client: sqlite3.Connection, server: sqlite3.Connection
) -> tuple[dict[str, str], dict[str, Any]]:
    candidates: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    server_effects = {
        (int(row[0]), int(row[2])): str(row[1])
        for row in server.execute("SELECT id, actual_type, actual_id FROM effects")
        if row[1] is not None
    }
    for effect_id, client_type, actual_id in client.execute(
        "SELECT id, actual_type, actual_id FROM effects WHERE actual_type LIKE '<ref:%'"
    ):
        server_type = server_effects.get((int(effect_id), int(actual_id)))
        if server_type:
            candidates[str(client_type)][server_type] += 1

    resolved: dict[str, str] = {}
    evidence: dict[str, Any] = {}
    for reference, values in sorted(candidates.items()):
        ordered = dict(sorted(values.items()))
        if len(ordered) == 1:
            resolved[reference] = next(iter(ordered))
            state = "resolved_unique"
        else:
            state = "conflict"
        evidence[reference] = {"candidates": ordered, "state": state}
    return resolved, evidence


def build_buff_unit_modifier_owner_type_map(
    client_relationships: dict[str, Any], server: sqlite3.Connection
) -> tuple[dict[str, str], dict[str, Any]]:
    server_rows = {
        int(row["id"]): dict(row)
        for row in server.execute("SELECT * FROM buff_unit_modifiers")
    }
    candidates: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for client_row in client_relationships["buff_relations"].get(
        "buff_unit_modifiers", []
    ):
        reference = client_row.get("owner_type")
        if not reference or not str(reference).startswith("<ref:"):
            continue
        server_row = server_rows.get(int(client_row["id"]))
        if not server_row:
            continue
        if all(
            client_row.get(field) == server_row.get(field)
            for field in ("owner_id", "buff_id", "tag_id")
        ):
            candidates[str(reference)][str(server_row["owner_type"])] += 1

    resolved: dict[str, str] = {}
    evidence: dict[str, Any] = {}
    for reference, values in sorted(candidates.items()):
        ordered = dict(sorted(values.items()))
        if len(ordered) == 1:
            resolved[reference] = next(iter(ordered))
            state = "resolved_unique"
        else:
            state = "conflict"
        evidence[reference] = {"candidates": ordered, "state": state}
    return resolved, evidence


def backend_inventory(source_root: Path) -> dict[str, Any]:
    effects_root = source_root / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects"
    skill_manager = source_root / "AAEmu.Game" / "Core" / "Managers" / "SkillManager.cs"
    class_pattern = re.compile(r"\bclass\s+(\w+)\s*:\s*(?:[\w.]+\.)?EffectTemplate\b")
    classes: dict[str, str] = {}
    for path in sorted(effects_root.rglob("*.cs")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for match in class_pattern.finditer(text):
            classes[match.group(1)] = str(path.relative_to(source_root)).replace("\\", "/")
    controller = source_root / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Templates" / "SkillControllerTemplate.cs"
    if controller.exists():
        classes["SkillController"] = str(controller.relative_to(source_root)).replace("\\", "/")
    classes["Buff"] = "AAEmu.Game/Models/Game/Skills/Templates/BuffTemplate.cs"

    manager_text = skill_manager.read_text(encoding="utf-8-sig", errors="replace")
    loader_types = sorted(set(re.findall(r'_effects\.Add\("([^"]+)"', manager_text)))
    return {
        "effect_template_classes": dict(sorted(classes.items())),
        "skill_manager_registered_types": loader_types,
        "skill_manager_path": str(skill_manager.relative_to(source_root)).replace("\\", "/"),
    }


def skill_status(
    in_client: bool,
    in_server: bool,
    effect_count: int,
    effect_types: list[str | None],
) -> str:
    if in_client and not in_server:
        return "unknown_missing_server_relationships"
    if in_server and not in_client:
        return "server_reference_only"
    if not effect_count:
        return "unknown_no_effect_relationships"
    if any(value is None for value in effect_types):
        return "adaptation_needed_unresolved_effect_type"
    return "adaptation_needed_historical_concrete_effects"


def build_skill_manifest(
    ability_id: int,
    client: sqlite3.Connection,
    runtime: sqlite3.Connection,
    server: sqlite3.Connection,
    provenance: dict[str, Any],
    backend: dict[str, Any],
    client_relationships: dict[str, Any],
) -> dict[str, Any]:
    client_tables = table_names(client)
    runtime_tables = table_names(runtime)
    server_tables = table_names(server)
    effect_reference_map, effect_reference_evidence = build_effect_type_reference_map(
        client, server
    )
    (
        buff_unit_modifier_owner_type_map,
        buff_unit_modifier_owner_type_evidence,
    ) = build_buff_unit_modifier_owner_type_map(client_relationships, server)
    client_relationships["buff_unit_modifier_owner_type_map"] = (
        buff_unit_modifier_owner_type_map
    )
    client_rows = {
        int(row["id"]): dict(row)
        for row in client.execute(
            "SELECT * FROM skills WHERE ability_id = ? ORDER BY ability_level, id",
            (ability_id,),
        )
    }
    server_rows = {
        int(row["id"]): dict(row)
        for row in server.execute(
            "SELECT * FROM skills WHERE ability_id = ? ORDER BY ability_level, id",
            (ability_id,),
        )
    }

    skills = []
    for skill_id in sorted(
        set(client_rows).union(server_rows),
        key=lambda value: (
            (client_rows.get(value) or server_rows[value]).get("ability_level", 0),
            value,
        ),
    ):
        client_row = client_rows.get(skill_id)
        server_row = server_rows.get(skill_id)
        relations = skill_relations(
            skill_id,
            client_row is not None,
            client_relationships,
            client,
            runtime,
            server,
            client_tables,
            runtime_tables,
            server_tables,
            effect_reference_map,
        )
        effect_types = [
            chain["effect"]["resolved_actual_type"] for chain in relations["effects"]
        ]
        controller_id = (client_row or server_row or {}).get("skill_controller_id", 0)
        skills.append(
            {
                "id": skill_id,
                "source_presence": {
                    "client_8": client_row is not None,
                    "runtime": first_row_by_id(runtime, runtime_tables, "skills", skill_id)
                    is not None,
                    "server_reference": server_row is not None,
                },
                "localized_text": localized_skill_texts(client, client_tables, skill_id),
                "client_8": select_existing_fields(client_row),
                "server_reference": select_existing_fields(server_row),
                "common_field_differences": common_field_differences(client_row, server_row),
                "controller": (
                    first_row_by_id(
                        runtime,
                        runtime_tables,
                        "skill_controllers",
                        int(controller_id),
                    )
                    if controller_id
                    else None
                ),
                "relations": relations,
                "status": skill_status(
                    client_row is not None,
                    server_row is not None,
                    len(relations["effects"]),
                    effect_types,
                ),
            }
        )

    passive_rows = sorted(
        (
            row
            for row in client_relationships["passive_buffs"]
            if int(row["ability_id"]) == ability_id
        ),
        key=lambda row: int(row["id"]),
    )
    passives = []
    for passive in passive_rows:
        buff_id = int(passive["buff_id"])
        related_buff = buff_snapshot(
            client,
            runtime,
            server,
            client_tables,
            runtime_tables,
            server_tables,
            client_relationships,
            buff_id,
        )
        native_buff_present = related_buff["template"]["client_8"] is not None
        passives.append(
            {
                "passive_buff": passive,
                "source": "client_8_game11",
                "client_8_confirmation": "direct_cached_query_result",
                "related_buff": related_buff,
                "related_buff_source": (
                    "client_8_game11"
                    if native_buff_present
                    else provenance["tables"]["buffs"]["runtime_provenance"]
                ),
                "status": (
                    "native_buff_template_recovered"
                    if native_buff_present
                    else "missing_native_buff_template"
                ),
            }
        )

    client_ids = set(client_rows)
    server_ids = set(server_rows)
    by_id = {entry["id"]: entry for entry in skills}
    manual_validation = {
        "simple": validation_snapshot(by_id, SIMPLE_VALIDATION_SKILL_ID),
        "complex": validation_snapshot(by_id, COMPLEX_VALIDATION_SKILL_ID),
    }
    return {
        "format_version": FORMAT_VERSION,
        "ability": {"id": ability_id, "name": ABILITY_NAME},
        "source_hashes": {
            **{key: value["sha256"] for key, value in provenance["sources"].items()},
            "client_8_game11": client_relationships["source"]["sha256"],
        },
        "client_8_cached_results": {
            "source": client_relationships["source"],
            "result_ranges": client_relationships["result_ranges"],
        },
        "effect_type_reference_map": {
            "resolved": effect_reference_map,
            "evidence": effect_reference_evidence,
            "method": "Client reference is accepted only when every shared effect.id with the same actual_id maps to one historical actual_type.",
        },
        "buff_unit_modifier_owner_type_reference_map": {
            "resolved": buff_unit_modifier_owner_type_map,
            "evidence": buff_unit_modifier_owner_type_evidence,
            "method": "Client reference is accepted only when every shared row id with identical owner_id, buff_id and tag_id maps to one historical owner_type.",
        },
        "limitations": [
            "Native skill_effects and passive_buffs are recovered directly from the client 8.0 game11 cached-query stream.",
            "Native buff_effects, conversion_effects, damage_effects, physical_explosion_effects and special_effects are recovered from game11.",
            "Native buffs are recovered from game11 with the 230-column layout confirmed in x2game.dll FUN_39a2ae70.",
            "Native buff_tick_effects, buff_triggers, buff_unit_modifiers and tagged_buffs are recovered from game11; historical rows are retained only as an explicit comparison source.",
            "Client actual_type values encoded as <ref:N> are resolved only when effect id and actual id match the server reference.",
        ],
        "summary": {
            "client_8_skill_rows": len(client_ids),
            "runtime_reference_skill_rows": len(server_ids),
            "shared_skill_ids": sorted(client_ids & server_ids),
            "client_8_only_skill_ids": sorted(client_ids - server_ids),
            "server_reference_only_skill_ids": sorted(server_ids - client_ids),
            "client_8_displayed_skill_ids": sorted(
                skill_id for skill_id, row in client_rows.items() if row.get("show")
            ),
            "client_8_skills_with_native_effect_relations": sorted(
                entry["id"]
                for entry in skills
                if entry["source_presence"]["client_8"] and entry["relations"]["effects"]
            ),
            "client_8_native_skill_effect_rows": len(client_relationships["skill_effects"]),
            "client_8_native_passive_rows": len(client_relationships["passive_buffs"]),
            "client_8_native_buff_rows": len(client_relationships["buffs"]),
            "client_8_native_buff_relation_rows": {
                table: len(rows)
                for table, rows in sorted(
                    client_relationships["buff_relations"].items()
                )
            },
            "client_8_native_concrete_rows": {
                table: len(rows)
                for table, rows in sorted(
                    client_relationships["concrete_effects"].items()
                )
            },
            "battlerage_native_passive_rows": len(passives),
        },
        "backend_inventory": backend,
        "skills": skills,
        "passives": passives,
        "manual_validation": manual_validation,
        "first_vertical_selection": {
            "skill_id": COMPLEX_VALIDATION_SKILL_ID,
            "name": "Behind Enemy Lines",
            "reason": (
                "It is the only displayed Battlerage row in the extracted 8.0 skill set "
                "whose id is also present in the historical runtime, making it the first "
                "user-visible candidate with a traceable relationship baseline."
            ),
            "readiness": (
                "ready_for_phase_2_specialization_core"
                if not manual_validation["complex"]["missing_client_8_buff_ids"]
                else "blocked_until_8_0_buff_templates_are_recovered"
            ),
            "preliminary_probe": {
                "skill_id": SIMPLE_VALIDATION_SKILL_ID,
                "name": "Whirlwind Slash",
                "purpose": "Smallest shared-id chain for validating the extractor and future effect-table recovery.",
            },
        },
    }


def validation_snapshot(by_id: dict[int, dict[str, Any]], skill_id: int) -> dict[str, Any]:
    entry = by_id.get(skill_id)
    if not entry:
        return {"skill_id": skill_id, "present": False}
    effects = entry["relations"]["effects"]
    referenced_buff_ids = sorted(
        {
            int(item["related_buff"]["buff_id"])
            for item in effects
            if item.get("related_buff")
        }
    )
    native_buff_ids = sorted(
        {
            int(item["related_buff"]["buff_id"])
            for item in effects
            if item.get("related_buff")
            and item["related_buff"]["template"]["client_8"] is not None
        }
    )
    return {
        "skill_id": skill_id,
        "present": True,
        "client_8_present": entry["source_presence"]["client_8"],
        "server_reference_present": entry["source_presence"]["server_reference"],
        "runtime_effect_count": len(effects),
        "runtime_effect_ids": [item["skill_effect"]["effect_id"] for item in effects],
        "resolved_effect_types": [
            item["effect"]["resolved_actual_type"] for item in effects
        ],
        "effect_type_resolutions": [item["effect"]["type_resolution"] for item in effects],
        "referenced_buff_ids": referenced_buff_ids,
        "client_8_native_buff_ids": native_buff_ids,
        "missing_client_8_buff_ids": sorted(
            set(referenced_buff_ids) - set(native_buff_ids)
        ),
    }


def build_effect_coverage(
    manifest: dict[str, Any], backend: dict[str, Any]
) -> dict[str, Any]:
    classes = backend["effect_template_classes"]
    registered = set(backend["skill_manager_registered_types"])
    aggregate: dict[str, dict[str, Any]] = {}
    unresolved = []
    for skill in manifest["skills"]:
        for chain in skill["relations"]["effects"]:
            actual_type = chain["effect"]["resolved_actual_type"]
            if not actual_type:
                unresolved.append(
                    {
                        "skill_id": skill["id"],
                        "effect_id": chain["skill_effect"]["effect_id"],
                        "resolution": chain["effect"]["type_resolution"],
                    }
                )
                continue
            entry = aggregate.setdefault(
                actual_type,
                {
                    "actual_type": actual_type,
                    "concrete_table": chain["concrete_effect"]["table"],
                    "skill_ids": set(),
                    "effect_ids": set(),
                    "type_resolutions": defaultdict(int),
                    "relation_sources": defaultdict(int),
                    "client_8_concrete_rows_found": 0,
                    "client_8_native_concrete_rows_found": 0,
                    "client_8_native_buff_templates_found": 0,
                    "runtime_concrete_rows_found": 0,
                    "relation_count": 0,
                },
            )
            entry["skill_ids"].add(skill["id"])
            entry["effect_ids"].add(chain["skill_effect"]["effect_id"])
            entry["type_resolutions"][chain["effect"]["type_resolution"]] += 1
            entry["relation_sources"][chain["skill_effect_source"]] += 1
            entry["relation_count"] += 1
            if chain["concrete_effect"]["client_8"] is not None:
                entry["client_8_concrete_rows_found"] += 1
                if chain["skill_effect_source"] == "client_8_game11":
                    entry["client_8_native_concrete_rows_found"] += 1
            if chain["concrete_effect"]["runtime"] is not None:
                entry["runtime_concrete_rows_found"] += 1
            if (
                chain["skill_effect_source"] == "client_8_game11"
                and chain.get("related_buff")
                and chain["related_buff"]["template"]["client_8"] is not None
            ):
                entry["client_8_native_buff_templates_found"] += 1

    coverage = []
    for actual_type, entry in sorted(aggregate.items()):
        class_present = actual_type in classes
        loader_registered = actual_type in registered
        state = (
            "backend_present_missing_native_buff_templates"
            if actual_type == "BuffEffect"
            and class_present
            and loader_registered
            and entry["relation_sources"].get("client_8_game11", 0)
            > entry["client_8_native_buff_templates_found"]
            else "backend_present_native_source_confirmed"
            if actual_type == "BuffEffect"
            and class_present
            and loader_registered
            and entry["relation_sources"].get("client_8_game11", 0)
            == entry["client_8_native_buff_templates_found"]
            else "backend_present_missing_concrete_8_data"
            if class_present
            and loader_registered
            and entry["relation_sources"].get("client_8_game11", 0)
            > entry["client_8_native_concrete_rows_found"]
            else "backend_present_source_unconfirmed"
            if class_present and loader_registered
            else "backend_class_not_registered"
            if class_present
            else "not_implemented"
        )
        coverage.append(
            {
                **entry,
                "skill_ids": sorted(entry["skill_ids"]),
                "effect_ids": sorted(entry["effect_ids"]),
                "type_resolutions": dict(sorted(entry["type_resolutions"].items())),
                "relation_sources": dict(sorted(entry["relation_sources"].items())),
                "backend_class_present": class_present,
                "backend_class_path": classes.get(actual_type),
                "skill_manager_loader_registered": loader_registered,
                "state": state,
            }
        )
    return {
        "format_version": FORMAT_VERSION,
        "ability": manifest["ability"],
        "summary": {
            "resolved_effect_types": len(coverage),
            "unresolved_effect_relations": len(unresolved),
            "backend_present_types": sum(
                1
                for entry in coverage
                if entry["state"].startswith("backend_present_")
            ),
            "not_implemented_types": sum(
                1 for entry in coverage if entry["state"] == "not_implemented"
            ),
        },
        "coverage": coverage,
        "unresolved": unresolved,
    }


def json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def skill_display_name(skill: dict[str, Any]) -> str:
    localized = skill.get("localized_text", {})
    if localized.get("name"):
        return localized["name"]
    client = skill.get("client_8") or {}
    server = skill.get("server_reference") or {}
    return client.get("stored_name") or server.get("stored_name") or "(unnamed)"


def manifest_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# Battlerage skill manifest — ArcheAge 8.0",
        "",
        "Generated by `extract_battlerage_manifest.py`. The input databases were opened read-only.",
        "",
        "## Source boundary",
        "",
        "The client 8.0 research view supplies `skills`, `effects` and English localization. Native skill relationships, concrete effects, passives, the complete 230-column `buffs` result and its four relation tables are reconstructed from the `game11` cached-query stream.",
        "",
        "## Summary",
        "",
        f"- Client 8.0 skill rows with `ability_id = 1`: {summary['client_8_skill_rows']}.",
        f"- Historical runtime rows with `ability_id = 1`: {summary['runtime_reference_skill_rows']}.",
        f"- Shared IDs: {', '.join(map(str, summary['shared_skill_ids'])) or 'none'}.",
        f"- Client 8.0 rows with a native effect relation: {', '.join(map(str, summary['client_8_skills_with_native_effect_relations'])) or 'none'}.",
        f"- Native Battlerage passives recovered from `game11`: {summary['battlerage_native_passive_rows']}.",
        f"- Native buff templates recovered from `game11`: {summary['client_8_native_buff_rows']}.",
        "- Native buff relation rows: "
        + ", ".join(
            f"{table}={rows}"
            for table, rows in summary["client_8_native_buff_relation_rows"].items()
        )
        + ".",
        "",
        "## Skills",
        "",
        "| ID | Name | Client 8.0 | Runtime reference | Effects | Status |",
        "|---:|---|:---:|:---:|---:|---|",
    ]
    for skill in manifest["skills"]:
        presence = skill["source_presence"]
        lines.append(
            f"| {skill['id']} | {skill_display_name(skill).replace('|', '\\|')} | "
            f"{'yes' if presence['client_8'] else 'no'} | "
            f"{'yes' if presence['server_reference'] else 'no'} | "
            f"{len(skill['relations']['effects'])} | {skill['status']} |"
        )
    lines.extend(
        [
            "",
            "## Manual validation anchors",
            "",
            f"- Simple shared chain: `{SIMPLE_VALIDATION_SKILL_ID}` (Whirlwind Slash).",
            f"- Complex shared chain: `{COMPLEX_VALIDATION_SKILL_ID}` (Behind Enemy Lines).",
            "",
            "## First vertical selection",
            "",
            f"Selected `{manifest['first_vertical_selection']['skill_id']}` — {manifest['first_vertical_selection']['name']} — as the first user-visible target. Its native 8.0 relationships, concrete effects and buff templates are now recovered. The next planned stage is the specialization core before enabling individual effects.",
            "",
            "See `battlerage-skill-manifest.json` for complete fields, relationships, concrete effects, buffs, tags, requirements and provenance.",
            "",
        ]
    )
    return "\n".join(lines)


def coverage_markdown(coverage: dict[str, Any]) -> str:
    lines = [
        "# Battlerage effect coverage — ArcheAge 8.0",
        "",
        "This matrix describes the effect types reachable through the relationships currently loaded by the runtime. It does not claim those historical relationships are the native 8.0 definitions.",
        "",
        "| Effect type | Relations | Skills | Native concrete | Backend | Relation sources |",
        "|---|---:|---:|---:|---|---|",
    ]
    for entry in coverage["coverage"]:
        lines.append(
            f"| {entry['actual_type']} | {entry['relation_count']} | "
            f"{len(entry['skill_ids'])} | {entry['client_8_native_concrete_rows_found']} | "
            f"{entry['state']} | {', '.join(entry['relation_sources'])} |"
        )
    lines.extend(
        [
            "",
            f"Unresolved effect relationships: {coverage['summary']['unresolved_effect_relations']}.",
            "",
            "`backend_present_missing_concrete_8_data` means the native relationship is recovered and AAEmu has a class/loader, but one or more referenced concrete rows are absent from the runtime compact.",
            "`backend_present_missing_native_buff_templates` means native BuffEffect rows are recovered, but the client stream has not yet yielded the referenced `buffs` rows.",
            "`backend_present_native_source_confirmed` means both the native BuffEffect row and its referenced 8.0 buff template were recovered.",
            "",
        ]
    )
    return "\n".join(lines)


def verify_outputs(output: Path, manifest: dict[str, Any]) -> None:
    expected = {
        "compact-table-provenance.json",
        "battlerage-skill-manifest.json",
        "battlerage-skill-manifest.md",
        "effect-coverage.json",
        "effect-coverage.md",
    }
    missing = sorted(name for name in expected if not (output / name).is_file())
    if missing:
        raise RuntimeError(f"Missing generated outputs: {', '.join(missing)}")
    if manifest["manual_validation"]["simple"]["runtime_effect_count"] != 1:
        raise RuntimeError("Simple validation skill 32040 no longer has exactly one runtime effect")
    if manifest["manual_validation"]["complex"]["runtime_effect_count"] != 8:
        raise RuntimeError("Complex validation skill 23587 no longer has exactly eight runtime effects")
    expected_buffs = {828, 7543, 26932, 27631, 27632}
    recovered_buffs = set(
        manifest["manual_validation"]["complex"]["client_8_native_buff_ids"]
    )
    if recovered_buffs != expected_buffs:
        raise RuntimeError(
            "Complex validation skill 23587 native buffs differ: "
            f"expected {sorted(expected_buffs)}, found {sorted(recovered_buffs)}"
        )
    expected_cached_rows = {
        "buffs": 27031,
        "buff_tick_effects": 2962,
        "buff_triggers": 10084,
        "buff_unit_modifiers": 159,
        "tagged_buffs": 49526,
    }
    cached_ranges = manifest["client_8_cached_results"]["result_ranges"]
    actual_cached_rows = {
        table: cached_ranges[table]["rows"] for table in expected_cached_rows
    }
    if actual_cached_rows != expected_cached_rows:
        raise RuntimeError(
            "Native buff cached-result row counts differ: "
            f"expected {expected_cached_rows}, found {actual_cached_rows}"
        )
    for name in ("compact-table-provenance.json", "battlerage-skill-manifest.json", "effect-coverage.json"):
        json.loads((output / name).read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    for path in (
        args.client_compact,
        args.runtime_compact,
        args.server_reference,
        args.client_game_stream,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    if not args.source_root.is_dir():
        raise NotADirectoryError(args.source_root)

    client = open_read_only(args.client_compact)
    runtime = open_read_only(args.runtime_compact)
    server = open_read_only(args.server_reference)
    try:
        provenance = build_provenance(
            args.client_compact,
            args.runtime_compact,
            args.server_reference,
            client,
            runtime,
            server,
        )
        backend = backend_inventory(args.source_root)
        client_relationships = extract_client_relationships(args.client_game_stream)
        manifest = build_skill_manifest(
            args.ability_id,
            client,
            runtime,
            server,
            provenance,
            backend,
            client_relationships,
        )
        coverage = build_effect_coverage(manifest, backend)
    finally:
        client.close()
        runtime.close()
        server.close()

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "compact-table-provenance.json").write_text(
        json_text(provenance), encoding="utf-8"
    )
    (args.output / "battlerage-skill-manifest.json").write_text(
        json_text(manifest), encoding="utf-8"
    )
    (args.output / "battlerage-skill-manifest.md").write_text(
        manifest_markdown(manifest), encoding="utf-8"
    )
    (args.output / "effect-coverage.json").write_text(
        json_text(coverage), encoding="utf-8"
    )
    (args.output / "effect-coverage.md").write_text(
        coverage_markdown(coverage), encoding="utf-8"
    )
    if args.verify:
        verify_outputs(args.output, manifest)

    result = {
        "output": str(args.output.resolve()),
        "ability_id": args.ability_id,
        "client_8_skill_rows": manifest["summary"]["client_8_skill_rows"],
        "shared_skill_ids": manifest["summary"]["shared_skill_ids"],
        "effect_types": coverage["summary"]["resolved_effect_types"],
        "verified": bool(args.verify),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
