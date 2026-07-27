#!/usr/bin/env python3
"""Extract the proven AA8 NPC/model/quest catalogue from the game11 cache.

This is a forensic extractor, not a runtime builder.  It reads Kakao
8.0.3.12 evidence and the current runtime compact read-only, verifies the
native cached-result boundaries, and emits a compact manifest with native
closure statistics.  Historical runtime rows are comparison-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import struct
from collections import Counter
from pathlib import Path
from typing import Any


FORMAT_VERSION = 1
AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
DEFAULT_GAME11 = Path(
    r"E:\AAEmu-Research\output\compact-8.0-extracted\game11"
)
DEFAULT_X2GAME = Path(r"E:\AAEmu-Research\input\x2game.dll")
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-character-creation-v2.sqlite3"
)


def words(value: str) -> list[str]:
    return value.split()


TABLE_SPECS: dict[str, dict[str, Any]] = {
    "actor_models": {
        "columns": words(
            "id actor_height add_box animation_graph attack_start_range beanstalk_back "
            "box_x box_y box_z center_x center_y center_z face_target_instantly fly_mode "
            "fx_scale game_backward_diagonal_multiplier game_backward_multiplier "
            "game_bow_look_ik_blend_head game_bow_look_ik_blend_neck "
            "game_bow_look_ik_blend_spine1 game_bow_look_ik_blend_spine2 "
            "game_bow_look_ik_blend_spine3 game_forward_diagonal_multiplier "
            "game_forward_multiplier game_grab_multiplier game_inertia game_inertia_accel "
            "game_jump_height game_lean_angle game_lean_shift game_look_ik_blend_head "
            "game_look_ik_blend_neck game_look_ik_blend_spine1 game_look_ik_blend_spine2 "
            "game_look_ik_blend_spine3 game_max_grab_mass game_max_grab_volume "
            "game_sprint_multiplier game_strafe_multiplier "
            "game_walk_backward_diagonal_multiplier game_walk_backward_multiplier "
            "game_walk_forward_diagonal_multiplier game_walk_multiplier "
            "game_walk_strafe_multiplier ground_targetable hand_rate height hit_power "
            "hrope_down model_file model_view_offset_z movement_id physics_flags "
            "physics_living_air_resistance physics_living_collider_mat "
            "physics_living_gravity physics_living_k_air_control physics_living_mass "
            "physics_living_max_climb_angle physics_living_max_vel_ground "
            "physics_living_min_fall_angle physics_living_min_slide_angle "
            "physics_living_time_impulse_recover physics_mass physics_stiffness_scale "
            "portrait push_ragdoll radius restrict_boarding_mate restrict_boarding_slave "
            "restrict_climb rope_back rope_hanging_hand_offset_x rope_hanging_hand_offset_y "
            "rope_hanging_hand_offset_z rope_walking_hand_offset_x "
            "rope_walking_hand_offset_y rope_walking_hand_offset_z shared_dummy_model "
            "sight_fov sight_range slope_alignment turn_speed underwater_creature "
            "upperbody_graph use_ragdoll use_ragdoll_hit use_ragdoll_knock_down "
            "use_random_idle_control"
        ),
        "layout": words(
            "68 60 38 78 60 60 60 60 60 60 60 60 38 38 60 60 60 60 60 60 "
            "60 60 60 60 60 60 60 60 68 60 60 60 60 60 60 68 60 60 60 60 "
            "60 60 60 60 38 60 60 68 60 78 60 68 68 60 78 60 60 68 60 68 "
            "60 60 60 68 68 78 38 60 38 38 38 60 60 60 60 60 60 60 38 60 "
            "60 38 60 38 78 38 38 38 38"
        ),
        "start": 0x3D6E2DD,
        "done": 0x3E5ECA6,
        "rows": 1598,
        "first_string_reference": 150174,
        "loader": "x2game.dll FUN_39a2fdd0",
        "sql_address": "0x39df6e70",
        "projection": ("id", "model_file"),
    },
    "models": {
        "columns": words(
            "id auto_adjust_bind_offset big camera_distance camera_distance_for_action_mode "
            "camera_distance_for_wide_mode despawn_doodad_on_collision dying_time "
            "high_impact_fx_group_id low_impact_fx_group_id middle_impact_fx_group_id "
            "mount_pose_id name name_tag_offset play_mount_animation player_mount_name_tag_pos "
            "selectable show_name_tag sound_material_id sound_pack_id sub_type sub_id "
            "target_decal_size use_target_decal use_target_highlight use_target_silhouette"
        ),
        "layout": words(
            "68 38 38 60 60 60 38 60 68 68 68 68 78 60 38 38 38 38 68 68 "
            "78 68 60 38 38 38"
        ),
        "start": 0x3F1BECB,
        "done": 0x3F706F3,
        "rows": 2907,
        "first_string_reference": 154480,
        "loader": "x2game.dll FUN_39a33d70",
        "sql_address": "0x39df8010",
        "projection": ("id", "name", "sub_type", "sub_id"),
    },
    "npcs": {
        "columns": words(
            "id ability_changer absolute_return_distance accept_aggro_link "
            "activate_ai_always aggression aggro_link_help_dist aggro_link_sight_check "
            "aggro_link_special_guard aggro_link_special_ignore_npc_attacker "
            "aggro_link_special_rule_id ai_file_id armor_element_level armor_type_id "
            "attack_start_range_scale auctioneer banker base_skill_delay base_skill_strafe "
            "base_skill_id battle_field_recruiter blacksmith char_race_id check_backpack "
            "check_target_under_terrain crowd_effect decaying_sec_after_looted "
            "dont_pushable_like_ghost engage_combat_bgm_id engage_combat_give_quest_id "
            "equip_cloths_id equip_weapons_id exp_adder exp_multiplier expedition faction_id "
            "force_target_me_on_attack friendly_near_quest_id heir_level honor_point level "
            "look_converter mate_equip_slot_pack_id mate_kind_id mate_revive_delay "
            "mate_revive_hp_percent mate_revive_mp_percent merchant merchant_random_pack_id "
            "model_id multi_jump multi_jump_pow_y multi_jump_pow_z name no_apply_total_custom "
            "no_exp no_penalty non_pushable_by_actor npc_ai_client_param_id npc_ai_param_id "
            "npc_grade_id npc_interaction_set_id npc_kind_id npc_nickname_id "
            "npc_posture_set_id npc_strafe_param_id npc_template_id opacity party_flag "
            "pet_item_id priest ragdoll_after_death_anim repairman return_distance "
            "return_when_enter_housing_area run_away_threshold scale show_faction_tag "
            "show_name_tag show_on_boss_telescope sight_fov_scale sight_range_scale "
            "skill_trainer so_state sound_pack_id specialty specialty_coin_id stabler "
            "teleporter total_custom_id track_friendship tradegood_buy trader use_abuser_list "
            "use_ddcms_mount_skill use_hp_bar_split use_model_camera_distance use_range_mod "
            "visible_to_creator_only weapon_element_id weapon_element_level"
        ),
        "layout": words(
            "68 38 60 38 38 38 60 38 38 38 68 68 68 68 60 38 38 60 38 68 "
            "38 38 68 38 38 38 68 38 68 68 68 68 68 60 38 68 38 68 68 68 "
            "68 38 68 68 68 68 68 38 68 68 68 60 60 78 38 38 38 38 68 68 "
            "68 68 68 68 68 68 68 60 38 68 38 38 38 60 38 60 60 38 38 38 "
            "60 60 38 78 68 38 68 38 38 68 38 38 38 38 38 38 38 38 38 68 68"
        ),
        "start": 0x5A02E9D,
        "done": 0x5FD8D95,
        "rows": 18217,
        "first_string_reference": None,
        "loader": "x2game.dll FUN_39959180",
        "sql_address": "0x39dd1f30",
        "projection": ("id", "name", "model_id"),
    },
    "quest_acts": {
        "columns": words("id act_detail_type act_detail_id quest_component_id"),
        "layout": words("68 78 68 68"),
        "start": 0x6DB2158,
        "done": 0x6E6D1D6,
        "rows": 42446,
        "first_string_reference": 320614,
        "loader": "x2game.dll FUN_399f0320",
        "sql_address": "0x39def990",
        "native_filter": "WHERE enable='t'",
        "projection": (
            "id",
            "act_detail_type",
            "act_detail_id",
            "quest_component_id",
        ),
    },
    "quest_components": {
        "columns": words(
            "id ai_command_set_id ai_path_name ai_path_type_id buff_id cinema_id "
            "component_kind_id hide_quest_marker next_component npc_ai_id npc_spawner_id "
            "npc_id or_unit_reqs play_cinema_before_bubble quest_context_id skill_self "
            "skill_id sound_id summary_voice_id"
        ),
        "layout": words(
            "68 68 78 68 68 68 68 38 68 68 68 68 38 38 68 38 68 68 68"
        ),
        "start": 0x745854B,
        "done": 0x7647870,
        "rows": 32191,
        "first_string_reference": None,
        "loader": "x2game.dll FUN_399f3a80",
        "sql_address": "0x39de93a0",
        "projection": (
            "id",
            "next_component",
            "npc_spawner_id",
            "npc_id",
            "quest_context_id",
        ),
    },
    "quest_contexts": {
        "columns": words(
            "id category_id chapter_idx degree detail_id grade_id hide_chapter_index "
            "let_it_done level max_level min_level name only_one_score_title priority "
            "quest_idx race repeatable restart_on_fail score selective successive "
            "use_accept_message use_complete_message use_quest_camera zone_id"
        ),
        "layout": words(
            "68 68 68 68 68 68 38 38 68 68 68 78 38 68 68 68 38 38 68 38 "
            "38 38 38 38 68"
        ),
        "start": 0x76635F8,
        "done": 0x77182D3,
        "rows": 7826,
        "first_string_reference": None,
        "loader": "x2game.dll FUN_399f5cb0",
        "sql_address": "0x39de98b0",
        "projection": ("id", "name", "race", "zone_id"),
    },
}

UNLOCATED_NATIVE_TABLES = {
    "npc_spawners": {
        "columns": words(
            "id activation_state destroyTime endTime maxPopulation min_population name "
            "npc_spawner_category_id save_indun spawn_delay_max spawn_delay_min startTime "
            "suspend_spawn_count test_radius_npc test_radius_pc"
        ),
        "layout": words("68 38 60 60 68 68 78 68 38 60 60 60 68 60 60"),
        "loader": "x2game.dll FUN_3994dd60",
        "sql_address": "0x39dd1470",
    },
    "npc_spawner_npcs": {
        "columns": words("id member_type member_id npc_spawner_id weight"),
        "layout": words("68 78 68 68 60"),
        "loader": "x2game.dll FUN_3994da10",
        "sql_address": "0x39dd5300",
    },
}

STARTING_ZONES = {
    129: "Elf",
    157: "Warborn",
    179: "Nuian",
    184: "Firran",
    187: "Harani",
    328: "Dwarf",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class CachedResultReader:
    """Reader for the SQLite cached-result encoding used by Kakao game11."""

    def __init__(self, data: bytes, first_string_reference: int | None):
        self.data = data
        self.cache: dict[int, str] = {}
        self.next_reference = first_string_reference
        self.tokens: Counter[str] = Counter()
        self.unresolved_references: Counter[int] = Counter()

    def string(self, offset: int) -> tuple[str | None, int]:
        tag = self.data[offset]
        offset += 1
        if tag == 2:
            self.tokens["null"] += 1
            return None, offset
        if tag == 0:
            end = self.data.index(0, offset)
            self.tokens["literal"] += 1
            return self.data[offset:end].decode("utf-8", "replace"), end + 1
        reference = struct.unpack_from("<I", self.data, offset)[0]
        offset += 4
        if reference == 0xFFFFFFFF:
            end = self.data.index(0, offset)
            value = self.data[offset:end].decode("utf-8", "replace")
            self.tokens["insert"] += 1
            if self.next_reference is not None:
                self.cache[self.next_reference] = value
                self.next_reference += 1
            return value, end + 1
        self.tokens["reference"] += 1
        if reference in self.cache:
            self.tokens["resolved_reference"] += 1
            return self.cache[reference], offset
        self.tokens["unresolved_reference"] += 1
        self.unresolved_references[reference] += 1
        return f"<ref:{reference}>", offset

    def row(self, offset: int, layout: list[str]) -> tuple[list[Any], int]:
        if self.data[offset] != 100:
            raise ValueError(f"Expected SQLITE_ROW at 0x{offset:X}")
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
                raise ValueError(f"Unsupported field type {field_type}")
        return values, offset


def extract_table(
    data: bytes,
    name: str,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    columns = spec["columns"]
    layout = spec["layout"]
    if len(columns) != len(layout):
        raise ValueError(f"{name}: {len(columns)} columns != {len(layout)} fields")
    reader = CachedResultReader(data, spec["first_string_reference"])
    cursor = spec["start"]
    digest = hashlib.sha256()
    ids: list[int] = []
    projections: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, layout)
        row = dict(zip(columns, values))
        encoded = json.dumps(
            row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        digest.update(encoded)
        digest.update(b"\n")
        ids.append(int(row["id"]))
        projections.append({key: row[key] for key in spec["projection"]})
        if len(samples) < 2:
            samples.append(row)
    if cursor != spec["done"] or data[cursor] != 101:
        raise ValueError(
            f"{name}: expected SQLITE_DONE at 0x{spec['done']:X}, got 0x{cursor:X}"
        )
    if len(ids) != spec["rows"]:
        raise ValueError(f"{name}: expected {spec['rows']} rows, got {len(ids)}")
    result = {
        "authority": AUTHORITY,
        "loader": spec["loader"],
        "sql_address": spec["sql_address"],
        "native_filter": spec.get("native_filter"),
        "columns": columns,
        "layout": layout,
        "cached_result": {
            "start_hex": f"0x{spec['start']:X}",
            "done_hex": f"0x{spec['done']:X}",
            "row_count": len(ids),
            "id_min": min(ids),
            "id_max": max(ids),
            "unique_ids": len(set(ids)),
            "canonical_rows_sha256": digest.hexdigest().upper(),
        },
        "string_cache": {
            "first_reference": spec["first_string_reference"],
            "tokens": dict(sorted(reader.tokens.items())),
            "captured_strings": len(reader.cache),
            "unresolved_reference_count": sum(reader.unresolved_references.values()),
            "unresolved_reference_ids": sorted(reader.unresolved_references),
        },
        "sample_rows": samples[:2],
    }
    return result, projections


def runtime_table_summary(
    path: Path,
    table: str,
    native_ids: set[int],
    native_columns: list[str],
) -> dict[str, Any]:
    if not path.exists():
        return {"available": False}
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only=ON")
        present = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not present:
            return {"available": True, "table_present": False}
        columns = [
            row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
        ]
        runtime_ids = {
            int(row[0]) for row in connection.execute(f'SELECT id FROM "{table}"')
        }
        return {
            "available": True,
            "table_present": True,
            "row_count": len(runtime_ids),
            "column_count": len(columns),
            "columns": columns,
            "native_columns_absent_from_runtime": sorted(
                set(native_columns) - set(columns)
            ),
            "runtime_columns_absent_from_native": sorted(
                set(columns) - set(native_columns)
            ),
            "native_ids_absent_from_runtime": len(native_ids - runtime_ids),
            "runtime_ids_absent_from_native": len(runtime_ids - native_ids),
        }
    finally:
        connection.close()


def unresolved(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("<ref:")


def extract_quest_act_sql_inventory(path: Path) -> list[dict[str, Any]]:
    """Return native embedded SELECTs without inferring their result layouts."""
    data = path.read_bytes()
    inventory: list[dict[str, Any]] = []
    for match in re.finditer(rb"[ -~]{20,}\x00", data):
        sql = match.group()[:-1].decode("ascii", "strict")
        if " FROM quest_act" not in sql:
            continue
        table_match = re.search(r"\bFROM\s+([a-z0-9_]+)", sql)
        inventory.append(
            {
                "file_offset_hex": f"0x{match.start():X}",
                "table": table_match.group(1) if table_match else None,
                "sql": sql,
            }
        )
    return inventory


def quest_manager_support_audit(
    path: Path, native_sql_inventory: list[dict[str, Any]]
) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    loaded_tables = sorted(
        set(re.findall(r'SELECT \* FROM (quest_act[a-z0-9_]+)', source))
        - {"quest_acts"}
    )
    native_tables = sorted(
        {
            entry["table"]
            for entry in native_sql_inventory
            if entry["table"] and entry["table"] != "quest_acts"
        }
    )
    return {
        "source": str(path),
        "native_concrete_table_count": len(native_tables),
        "quest_manager_loaded_table_count": len(loaded_tables),
        "native_tables_not_loaded": sorted(set(native_tables) - set(loaded_tables)),
        "loaded_tables_not_in_native_inventory": sorted(
            set(loaded_tables) - set(native_tables)
        ),
    }


def build_closure(
    rows: dict[str, list[dict[str, Any]]], backend_root: Path
) -> dict[str, Any]:
    actor_ids = {row["id"] for row in rows["actor_models"]}
    model_ids = {row["id"] for row in rows["models"]}
    npc_ids = {row["id"] for row in rows["npcs"]}
    context_ids = {row["id"] for row in rows["quest_contexts"]}
    component_ids = {row["id"] for row in rows["quest_components"]}

    actor_model_links = [
        row
        for row in rows["models"]
        if row["sub_type"] == "ActorModel" and int(row["sub_id"]) != 0
    ]
    unresolved_model_types = sum(
        1 for row in rows["models"] if unresolved(row["sub_type"])
    )
    npc_model_refs = [int(row["model_id"]) for row in rows["npcs"] if row["model_id"]]
    component_npc_refs = [
        int(row["npc_id"]) for row in rows["quest_components"] if row["npc_id"]
    ]
    component_spawner_refs = [
        int(row["npc_spawner_id"])
        for row in rows["quest_components"]
        if row["npc_spawner_id"]
    ]
    act_types = Counter(
        row["act_detail_type"]
        for row in rows["quest_acts"]
        if not unresolved(row["act_detail_type"])
    )
    unresolved_act_types = sum(
        1 for row in rows["quest_acts"] if unresolved(row["act_detail_type"])
    )
    backend_types = {
        path.stem
        for path in backend_root.rglob("QuestAct*.cs")
        if re.fullmatch(r"QuestAct[A-Za-z0-9_]+", path.stem)
    }
    starting_zone_counts = Counter(
        int(row["zone_id"])
        for row in rows["quest_contexts"]
        if int(row["zone_id"]) in STARTING_ZONES
    )
    return {
        "npc_to_model": {
            "references": len(npc_model_refs),
            "missing_model_ids": sorted(set(npc_model_refs) - model_ids),
            "missing_reference_count": sum(
                1 for model_id in npc_model_refs if model_id not in model_ids
            ),
        },
        "model_to_actor_model": {
            "resolved_actor_model_links": len(actor_model_links),
            "missing_actor_model_ids": sorted(
                {
                    int(row["sub_id"])
                    for row in actor_model_links
                    if int(row["sub_id"]) not in actor_ids
                }
            ),
            "unresolved_model_type_rows": unresolved_model_types,
        },
        "quest_context_to_component": {
            "dangling_component_ids": [
                row["id"]
                for row in rows["quest_components"]
                if row["quest_context_id"] not in context_ids
            ],
            "classification": (
                "native nonzero references outside the extracted quest_contexts result; "
                "must be explained before deployment"
            ),
        },
        "quest_component_to_act": {
            "dangling_act_ids": [
                row["id"]
                for row in rows["quest_acts"]
                if row["quest_component_id"] not in component_ids
            ],
        },
        "quest_component_to_npc": {
            "references": len(component_npc_refs),
            "missing_npc_ids": sorted(set(component_npc_refs) - npc_ids),
            "missing_reference_count": sum(
                1 for npc_id in component_npc_refs if npc_id not in npc_ids
            ),
        },
        "quest_component_to_spawner": {
            "references": len(component_spawner_refs),
            "status": "blocked: native npc_spawners cached result not yet located",
        },
        "quest_act_types": {
            "resolved_type_count": len(act_types),
            "resolved_row_count": sum(act_types.values()),
            "unresolved_row_count": unresolved_act_types,
            "rows_by_type": dict(sorted(act_types.items())),
            "backend_class_count": len(backend_types),
            "native_types_without_backend_class": sorted(set(act_types) - backend_types),
            "backend_classes_without_native_type": sorted(backend_types - set(act_types)),
        },
        "starting_zone_quest_contexts": {
            str(zone_id): {
                "race": race,
                "quest_context_count": starting_zone_counts[zone_id],
            }
            for zone_id, race in STARTING_ZONES.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--x2game", type=Path, default=DEFAULT_X2GAME)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent
        / "generated"
        / "native-npc-quest-catalog-v1-manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.game11, args.x2game):
        if not path.is_file():
            raise FileNotFoundError(path)
    game11 = args.game11.read_bytes()
    table_manifests: dict[str, Any] = {}
    rows: dict[str, list[dict[str, Any]]] = {}
    for name, spec in TABLE_SPECS.items():
        table_manifests[name], rows[name] = extract_table(game11, name, spec)

    repo_root = Path(__file__).resolve().parent.parent
    quest_sql_inventory = extract_quest_act_sql_inventory(args.x2game)
    quest_manager_path = repo_root / "AAEmu.Game" / "Core" / "Managers" / "QuestManager.cs"
    manifest = {
        "format_version": FORMAT_VERSION,
        "authority": AUTHORITY,
        "classification": "native forensic catalogue; not runtime-deployable",
        "deployable": False,
        "sources": {
            "game11": {
                "path": str(args.game11.resolve()),
                "bytes": args.game11.stat().st_size,
                "sha256": sha256_file(args.game11),
            },
            "x2game": {
                "path": str(args.x2game.resolve()),
                "bytes": args.x2game.stat().st_size,
                "sha256": sha256_file(args.x2game),
            },
            "runtime_comparison_only": {
                "path": str(args.runtime.resolve()),
                "exists": args.runtime.exists(),
                "sha256": sha256_file(args.runtime) if args.runtime.exists() else None,
            },
        },
        "tables": table_manifests,
        "unlocated_native_tables": UNLOCATED_NATIVE_TABLES,
        "quest_act_loader_sql_inventory": {
            "source": "embedded ASCII SQL in x2game.dll",
            "layout_status": (
                "SQL/table inventory is native; each concrete table still requires "
                "its loader accessor layout and cached-result boundary"
            ),
            "entries": quest_sql_inventory,
        },
        "server_consumer_audit": {
            "quest_manager": quest_manager_support_audit(
                quest_manager_path, quest_sql_inventory
            ),
        },
        "native_closure": build_closure(rows, repo_root / "AAEmu.Game"),
        "runtime_comparison": {
            name: runtime_table_summary(
                args.runtime,
                name,
                {int(row["id"]) for row in rows[name]},
                TABLE_SPECS[name]["columns"],
            )
            for name in TABLE_SPECS
        },
        "location_evidence": {
            "server_consumer": "SpawnManager loads AAEmu.Game/Data/Worlds/*/npc_spawns.json",
            "current_json_classification": "historical server-reference; forbidden as AA8 authority",
            "game_pak_xml_result": (
                "mission_mission0.xml exposes client area entities and partial legacy "
                "spawn markers, but no complete npc_spawner_id/world/position relation"
            ),
            "status": "blocked pending native placement-source reconstruction",
        },
        "blockers": [
            "Locate and decode the native npc_spawners cached result.",
            "Locate and decode the native npc_spawner_npcs cached result.",
            "Reconstruct authoritative spawner placements (world, coordinates, rotation).",
            "Extract every concrete quest-act detail table referenced by enabled quest_acts.",
            "Resolve remaining cross-result string-cache references without historical data.",
            "Implement AA8 schema/consumer changes before producing a runtime compact.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(
        json.dumps(
            {
                name: value["cached_result"]["row_count"]
                for name, value in table_manifests.items()
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
