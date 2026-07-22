#!/usr/bin/env python3
"""Build the reproducible ArcheAge 8.0 specialization runtime compact.

The input runtime compact and the decrypted client sources are never modified.
The output keeps the server-only schema required by the historical backend,
but replaces progression data with rows recovered from the Kakao 8.0 client.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from extract_battlerage_manifest import (
    CachedResultReader,
    PASSIVE_BUFF_COLUMNS,
    PASSIVE_BUFF_LAYOUT,
    locate_cached_result,
)


LEVEL_COLUMNS = [
    "id",
    "expedition_exp",
    "skill_points",
    "total_butler_exp",
    "total_exp",
    "total_mate_exp",
]
LEVEL_LAYOUT = ["68"] * len(LEVEL_COLUMNS)

SKILL_COLUMNS = """id ability_id ability_level account_cooldown actability_group_id active_weapon_id aggro auto_fire auto_learn auto_reuse auto_reuse_delay calc_user_level camera_acceleration camera_duration camera_hold_z camera_max_distance camera_slow_down_distance camera_speed can_active_weapon_without_anim cancel_ongoing_buff_exception_tag_id cancel_ongoing_buffs casting_cancelable casting_delayable casting_inc casting_time casting_useable category_id channeling_anim_id channeling_buff_id channeling_cancelable channeling_doodad_id channeling_mana channeling_target_buff_id channeling_tick channeling_time char_race_id charge_cooldown_time charge_count check_obstacle check_terrain combat_dice_id combat_resource_id consume_lp controller_camera controller_camera_speed cooldown_tag_id cooldown_time cost crime_point custom_gcd damage_type_id default_gcd desc doodad_bundle_id doodad_hit_family dual_wield_fire_anim_id effect_delay effect_repeat_count effect_repeat_tick effect_speed end_skill_controller fire_anim_id first_reagent_only front_angle fx_group_id gain_life_point icon_id ignore_global_cooldown is_dropable_backpack keep_mana_regen keep_stealth level_rule_no_consideration level_step link_equip_slot_id mainhand_tool_id mana_cost mana_level_md match_animation match_animation_count max_combat_resource max_range min_combat_resource min_range name offhand_tool_id or_unit_reqs percussion_instrument_fire_anim_id percussion_instrument_start_anim_id pitch_angle plot_only plot_id precedence_skill_id projectile_id random_unit_targeting reagent_corpse_status_id repeat_count repeat_tick req_points second_cooldown_tag_id sensitive_operation shot_gun_fire_anim_id shot_gun_start_anim_id show show_target_casting_time skill_controller_id skill_controller_at_end skill_points skip_quest_apply_use_item skip_validate_source start_anim_id start_autoattack stop_autoattack stop_casting_by_turn stop_casting_on_big_hit stop_channeling_on_big_hit stop_channeling_on_start_skill string_instrument_fire_anim_id string_instrument_start_anim_id switch_to_skill_cooldown synergy_icon1_buffkind synergy_icon1_id synergy_icon2_buffkind synergy_icon2_id target_alive target_angle target_area_angle target_area_count target_area_radius target_dead target_decal_radius target_fishing target_my_npc target_offset_angle target_offset_distance target_only_water target_preoccupied target_relation_id target_selection_id target_type_id target_unit_param target_valid_height target_water targetable_stealth third_cooldown_tag_id timing_id toggle_buff_id tube_instrument_fire_anim_id tube_instrument_start_anim_id twohand_fire_anim_id unmount use_anim_time use_condition_bits use_input_direction use_skill_camera use_weapon_cooldown_time valid_height valid_height_edge_to_edge weapon_gcd_id weapon_slot_for_angle_id weapon_slot_for_autoattack_id weapon_slot_for_range_id""".split()
SKILL_LAYOUT = """68 68 68 38 68 68 68 38 38 38 68 38 60 60 38 60 60 60 38 68 38 38 38 68 68 38 68 68 68 38 68 68 68 68 68 68 68 68 38 38 68 68 68 38 68 68 68 68 68 68 68 38 78 68 68 68 68 68 68 60 38 68 38 68 68 68 68 38 38 38 38 38 68 68 68 68 60 38 38 68 68 68 68 78 68 38 68 68 60 38 68 68 68 38 68 68 68 68 68 38 68 68 38 38 68 38 68 38 38 68 38 38 38 38 38 38 68 68 38 38 68 38 68 38 68 68 68 68 38 68 38 38 60 60 38 38 68 68 68 68 60 38 38 68 68 68 68 68 68 38 38 70 38 38 38 60 38 68 68 68 68""".split()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-compact", required=True, type=Path)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--client-game-stream", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def get_columns(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    return [
        {"name": row[1], "type": row[2] or "INTEGER", "pk": row[5]}
        for row in connection.execute(f"PRAGMA table_info({quote_identifier(table)})")
    ]


def extract_game_stream_rows(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    reader = CachedResultReader(path.read_bytes())
    raw_skills, skill_range = locate_cached_result(
        reader,
        SKILL_COLUMNS,
        SKILL_LAYOUT,
        10377,
        {
            "ability_id": 1,
            "ability_level": 10,
            "level_step": 31,
            "req_points": 0,
            "skill_points": 1,
            "show": 1,
            "auto_learn": 1,
        },
    )
    boolean_columns = [
        name for name, field_type in zip(SKILL_COLUMNS, SKILL_LAYOUT) if field_type == "38"
    ]

    def is_valid_skill(row: dict[str, Any]) -> bool:
        return row["id"] > 0 and all(row[name] in (0, 1) for name in boolean_columns)

    first_valid = next(
        (index for index, row in enumerate(raw_skills) if is_valid_skill(row)), None
    )
    if first_valid is None or any(not is_valid_skill(row) for row in raw_skills[first_valid:]):
        raise RuntimeError("The recovered skills cache contains invalid rows inside the result")
    skills = raw_skills[first_valid:]
    if len({row["id"] for row in skills}) != len(skills):
        raise RuntimeError("The recovered skills cache contains duplicate skill ids")

    skill_start = skill_range["start"]
    for _ in range(first_valid):
        _, skill_start = reader.row(skill_start, SKILL_LAYOUT)
    skill_range.update(
        {
            "raw_start": skill_range["start"],
            "raw_rows": skill_range["rows"],
            "start": skill_start,
            "rows": len(skills),
            "discarded_leading_rows": first_valid,
        }
    )
    levels, level_range = locate_cached_result(
        reader,
        LEVEL_COLUMNS,
        LEVEL_LAYOUT,
        2,
        {
            "expedition_exp": 0,
            "skill_points": 1,
            "total_butler_exp": 50,
            "total_exp": 400,
            "total_mate_exp": 50,
        },
    )
    passives, passive_range = locate_cached_result(
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
    return skills, levels, passives, {
        "skills": skill_range,
        "levels": level_range,
        "passive_buffs": passive_range,
    }


def add_client_skill_columns(
    output: sqlite3.Connection, client: sqlite3.Connection
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output_columns = get_columns(output, "skills")
    client_columns = get_columns(client, "skills")
    existing = {column["name"] for column in output_columns}
    for column in client_columns:
        if column["name"] in existing:
            continue
        output.execute(
            f"ALTER TABLE skills ADD COLUMN {quote_identifier(column['name'])} {column['type']}"
        )
    return get_columns(output, "skills"), client_columns


def replace_skills(
    output: sqlite3.Connection,
    client: sqlite3.Connection,
    native_skills: list[dict[str, Any]],
) -> dict[str, int]:
    output_columns, _ = add_client_skill_columns(output, client)
    output_names = [column["name"] for column in output_columns]
    output_indexes = {name: index for index, name in enumerate(output_names)}
    runtime_rows = {
        row[output_indexes["id"]]: row
        for row in output.execute(
            "SELECT " + ", ".join(quote_identifier(name) for name in output_names) + " FROM skills"
        )
    }
    output.execute("DELETE FROM skills")

    placeholders = ", ".join("?" for _ in output_names)
    insert_sql = (
        "INSERT INTO skills ("
        + ", ".join(quote_identifier(name) for name in output_names)
        + ") VALUES ("
        + placeholders
        + ")"
    )

    native_ids: set[int] = set()
    derived_need_learn_rows = 0
    for source_row in native_skills:
        source_id = source_row["id"]
        native_ids.add(source_id)
        runtime_row = runtime_rows.get(source_id)
        values = []
        for index, column in enumerate(output_columns):
            name = column["name"]
            # Cached text may be encoded as a game11 string-table reference.
            # Preserve the historical label/description because these values
            # are not gameplay-authoritative and the runtime row always exists.
            if "TEXT" in column["type"].upper() and runtime_row is not None:
                values.append(runtime_row[index])
            elif name in source_row:
                values.append(source_row[name])
            elif runtime_row is not None:
                # Preserve server-only fields such as need_learn.
                values.append(runtime_row[index])
            elif name == "need_learn":
                # Kakao game11 no longer exposes this historical backend
                # column. A new visible skill with a point cost is learnable;
                # hidden variants and zero-cost helpers are not.
                need_learn = int(
                    source_row.get("ability_id", 0) != 0
                    and source_row.get("show") == 1
                    and source_row.get("skill_points", 0) > 0
                )
                values.append(need_learn)
                derived_need_learn_rows += need_learn
            elif "TEXT" in column["type"].upper():
                values.append(None)
            else:
                values.append(0)
        output.execute(insert_sql, values)

    for source_id, runtime_row in runtime_rows.items():
        if source_id not in native_ids:
            output.execute(insert_sql, runtime_row)

    return {
        "native_client_rows": len(native_ids),
        "historical_base_rows": len(runtime_rows),
        "shared_rows": len(native_ids.intersection(runtime_rows)),
        "historical_compatibility_rows": len(set(runtime_rows).difference(native_ids)),
        "derived_need_learn_rows": derived_need_learn_rows,
        "merged_rows": len(native_ids.union(runtime_rows)),
    }


def replace_levels(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    connection.execute("DELETE FROM levels")
    connection.executemany(
        """
        INSERT INTO levels(
            id, expedition_exp, req_item_count, req_item_id,
            skill_points, total_exp, total_mate_exp
        ) VALUES (?, ?, 0, 0, ?, ?, ?)
        """,
        [
            (
                row["id"],
                row["expedition_exp"],
                row["skill_points"],
                row["total_exp"],
                row["total_mate_exp"],
            )
            for row in rows
        ],
    )


def replace_passives(connection: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    columns = {column["name"] for column in get_columns(connection, "passive_buffs")}
    connection.execute("DELETE FROM passive_buffs")
    insert_columns = [name for name in PASSIVE_BUFF_COLUMNS if name in columns]
    if "high_ability_id" in columns:
        insert_columns.append("high_ability_id")
    sql = (
        "INSERT INTO passive_buffs ("
        + ", ".join(quote_identifier(name) for name in insert_columns)
        + ") VALUES ("
        + ", ".join("?" for _ in insert_columns)
        + ")"
    )
    connection.executemany(
        sql,
        [tuple(row.get(name, 0) for name in insert_columns) for row in rows],
    )


def verify_output(connection: sqlite3.Connection) -> dict[str, Any]:
    result = {
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "counts": {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("skills", "passive_buffs", "levels")
        },
        "anchors": {
            "level_55": connection.execute(
                "SELECT skill_points, total_exp FROM levels WHERE id = 55"
            ).fetchone(),
            "skill_23587": connection.execute(
                "SELECT ability_id, ability_level, skill_points, req_points FROM skills WHERE id = 23587"
            ).fetchone(),
            "skill_10377": connection.execute(
                "SELECT ability_id, ability_level, level_step, skill_points, req_points FROM skills WHERE id = 10377"
            ).fetchone(),
            "modern_starter_skills": connection.execute(
                "SELECT id, ability_id, auto_learn, need_learn, show FROM skills WHERE id IN (39007, 40331, 44196, 47961) ORDER BY ability_id"
            ).fetchall(),
            "swiftblade_hidden_variant": connection.execute(
                "SELECT id, auto_learn, need_learn, show FROM skills WHERE id = 40377"
            ).fetchone(),
            "passive_244": connection.execute(
                "SELECT ability_id, buff_id, req_points, skill_points FROM passive_buffs WHERE id = 244"
            ).fetchone(),
        },
    }
    if result["integrity_check"] != "ok" or result["quick_check"] != "ok":
        raise RuntimeError(f"Generated compact failed SQLite validation: {result}")
    if result["counts"] != {"skills": 35501, "passive_buffs": 278, "levels": 101}:
        raise RuntimeError(f"Generated compact has unexpected row counts: {result['counts']}")
    if tuple(result["anchors"]["skill_10377"]) != (1, 10, 31, 1, 0):
        raise RuntimeError(
            f"Generated compact has the wrong native Battle Focus row: {result['anchors']['skill_10377']}"
        )
    expected_starters = [
        (39007, 11, 1, 1, 1),
        (40331, 12, 1, 1, 1),
        (44196, 13, 1, 1, 1),
        (47961, 14, 1, 1, 1),
    ]
    if [tuple(row) for row in result["anchors"]["modern_starter_skills"]] != expected_starters:
        raise RuntimeError(
            "Generated compact does not identify the modern starter skills: "
            f"{result['anchors']['modern_starter_skills']}"
        )
    if tuple(result["anchors"]["swiftblade_hidden_variant"]) != (40377, 0, 0, 0):
        raise RuntimeError(
            "Generated compact incorrectly marks a hidden Swiftblade variant as learnable: "
            f"{result['anchors']['swiftblade_hidden_variant']}"
        )
    return result


def main() -> int:
    args = parse_args()
    inputs = [args.runtime_compact.resolve(), args.client_compact.resolve(), args.client_game_stream.resolve()]
    output = args.output.resolve()
    if output in inputs:
        raise ValueError("Output must not replace any source file")
    for source in inputs:
        if not source.is_file():
            raise FileNotFoundError(source)

    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.resolve().parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_compact, output)
    skills, levels, passives, cached_ranges = extract_game_stream_rows(args.client_game_stream)

    output_connection = sqlite3.connect(output)
    client_connection = sqlite3.connect(
        f"file:{args.client_compact.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        output_connection.execute("PRAGMA journal_mode = DELETE")
        output_connection.execute("BEGIN IMMEDIATE")
        skill_merge = replace_skills(output_connection, client_connection, skills)
        if skill_merge["derived_need_learn_rows"] != 50:
            raise RuntimeError(
                "Unexpected number of derived native combat skills: "
                f"{skill_merge['derived_need_learn_rows']}"
            )
        replace_levels(output_connection, levels)
        replace_passives(output_connection, passives)
        output_connection.commit()
        verification = verify_output(output_connection) if args.verify else None
    except Exception:
        output_connection.rollback()
        raise
    finally:
        client_connection.close()
        output_connection.close()

    manifest = {
        "format_version": 1,
        "sources": {
            "runtime_compact": {
                "path": str(args.runtime_compact.resolve()),
                "sha256": sha256_file(args.runtime_compact),
            },
            "client_compact": {
                "path": str(args.client_compact.resolve()),
                "sha256": sha256_file(args.client_compact),
            },
            "client_game_stream": {
                "path": str(args.client_game_stream.resolve()),
                "sha256": sha256_file(args.client_game_stream),
                "cached_ranges": cached_ranges,
            },
        },
        "output": {
            "path": str(output),
            "sha256": sha256_file(output),
            "skills": skill_merge,
        },
        "compatibility_policy": {
            "client_shared_gameplay_columns": "recovered from the full Kakao 8.0 game11 cached skills result",
            "cached_text_columns": "historical labels retained because game11 may store them as unresolved string-table references",
            "server_only_skill_columns": "preserved from matching historical base rows",
            "need_learn_for_native_only_rows": "derived as true only for visible skills with a positive skill-point cost",
            "historical_base_rows": "only the 2035 valid ids absent from the native Kakao 8.0 result are retained for backend compatibility",
            "original_sources_modified": False,
        },
        "verification": verification,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest["output"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
