#!/usr/bin/env python3
"""Build the deterministic AA8 Shadowplay V6 runtime from native evidence."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NATIVE_COMBAT = ROOT / "reconstruccion_skills_8" / "native_combat"
SHARED_PRIMITIVES = ROOT / "reconstruccion_skills_8" / "shared_primitives"
sys.path.insert(0, str(NATIVE_COMBAT))
sys.path.insert(0, str(SHARED_PRIMITIVES))

from build_native_combat_runtime import columns, normalize, sha256_file, upsert_rows  # noqa: E402
from extract_native_unit_requirements import (  # noqa: E402
    EXPECTED_SHA256 as EXPECTED_GAME11_SHA256,
    extract_unit_requirements,
)


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
EXPECTED_CARRIER_SHA256 = "BC927E9349D413A807C6FA389A7010D079F2B44FC92DFB1145456DD1C68D6E58"
EXPECTED_KNOWLEDGE_SHA256 = "A3AB85F0F033407845651AD9277EFBBB4E772A1A8FCD20D973C2DCB5A3848559"

VISIBLE_ROOTS = (10082, 10104, 10189, 10481, 10496, 10648, 12029, 12049,
                 12139, 13344, 18125, 23594)
ALL_ROOTS = (10082, 10104, 10189, 10481, 10496, 10648, 11418, 12029, 12049,
             12139, 13344, 18125, 18126, 18127, 19050, 19052, 19054, 23594,
             36588, 36589, 36590, 36591, 36593, 36594, 39297, 39298, 40787,
             40788, 40815, 44288, 44289)
PASSIVES = ((6, 483, 5), (33, 488, 8), (55, 1548, 6), (259, 7570, 4),
            (260, 7572, 3), (302, 863, 7))

TOMBSTONE_ROOT_FIELDS = {
    10082: (
        "ability_id", "ability_level", "active_weapon_id", "auto_learn",
        "camera_acceleration", "camera_duration", "camera_max_distance",
        "camera_slow_down_distance", "camera_speed", "cancel_ongoing_buffs",
        "category_id", "check_obstacle", "combat_dice_id",
        "controller_camera_speed", "cooldown_time", "cost", "damage_type_id",
        "default_gcd", "desc", "effect_repeat_count", "fx_group_id", "icon_id",
        "keep_stealth", "level_step", "link_backpack_type_id",
        "link_equip_slot_id", "mana_level_md", "name", "need_learn",
        "repeat_count", "repeat_tick", "show", "show_target_casting_time",
        "skill_points", "source_alive", "stop_autoattack",
        "synergy_icon1_buffkind", "synergy_icon1_id", "synergy_icon2_buffkind",
        "target_alive", "target_area_angle", "target_area_count",
        "target_selection_id", "target_water", "timing_id",
        "valid_height_edge_to_edge", "weapon_slot_for_angle_id",
        "weapon_slot_for_autoattack_id", "weapon_slot_for_range_id",
    ),
    10104: (
        "ability_id", "ability_level", "aggro", "auto_learn",
        "camera_acceleration", "camera_duration", "camera_max_distance",
        "camera_slow_down_distance", "camera_speed", "cancel_ongoing_buffs",
        "category_id", "check_obstacle", "combat_dice_id",
        "controller_camera_speed", "cooldown_time", "cost", "damage_type_id",
        "default_gcd", "desc", "effect_repeat_count", "effect_speed",
        "fire_anim_id", "fx_group_id", "icon_id", "level_rule_no_consideration",
        "level_step", "link_backpack_type_id", "link_equip_slot_id",
        "mana_level_md", "max_range", "name", "need_learn", "repeat_count",
        "repeat_tick", "show", "show_target_casting_time", "skill_points",
        "source_alive", "stop_autoattack", "synergy_icon1_id",
        "synergy_icon2_buffkind", "target_alive", "target_angle",
        "target_area_angle", "target_area_count", "target_selection_id",
        "target_type_id", "target_water", "timing_id", "use_anim_time",
        "valid_height_edge_to_edge", "weapon_slot_for_angle_id",
        "weapon_slot_for_autoattack_id", "weapon_slot_for_range_id",
    ),
    10189: (
        "ability_id", "ability_level", "active_weapon_id", "auto_learn",
        "camera_acceleration", "camera_duration", "camera_max_distance",
        "camera_slow_down_distance", "camera_speed", "cancel_ongoing_buffs",
        "category_id", "check_obstacle", "combat_dice_id",
        "controller_camera_speed", "cooldown_time", "cost", "custom_gcd",
        "damage_type_id", "desc", "fx_group_id", "icon_id", "level_step",
        "link_backpack_type_id", "link_equip_slot_id", "mana_level_md", "name",
        "need_learn", "repeat_count", "repeat_tick", "show",
        "show_target_casting_time", "skill_points", "source_alive",
        "synergy_icon1_buffkind", "synergy_icon2_buffkind", "target_alive",
        "target_area_angle", "target_area_count", "target_selection_id",
        "target_water", "timing_id", "valid_height_edge_to_edge",
        "weapon_slot_for_angle_id", "weapon_slot_for_autoattack_id",
        "weapon_slot_for_range_id",
    ),
}

SEED_KEYS = {
    "effect_detail:bubble_effects:4766",
    "plot_effect:35005",
    "skill:36594",
    "skill:40815",
    "buff:22271",
    "buff:24095",
    "buff:24236",
    "buff:21999",
    "buff:18135",
    "buff:24237",
    "buff_trigger:9968",
    "buff_trigger:9970",
    "buff_trigger:9973",
    "buff_trigger:11343",
    "buff_trigger:11418",
    "buff_trigger:11420",
}
SEED_KEYS.update(f"skill:{skill_id}" for skill_id in ALL_ROOTS)
SEED_KEYS.update(f"passive_buff:{skill_id}" for skill_id, _, _ in PASSIVES)
SEED_KEYS.update(f"buff:{buff_id}" for _, buff_id, _ in PASSIVES)

EXECUTABLE_TABLES = {
    "skills", "skill_effects", "effects", "aggro_effects", "buff_effects",
    "special_effects", "damage_effects", "dispel_effects", "bubble_effects",
    "combat_resource_effects", "reset_aoe_diminishing_effects", "buffs",
    "buff_tick_effects", "buff_triggers", "buff_unit_modifiers",
    "buff_modifiers", "unit_modifiers", "tagged_buffs", "tagged_skills",
    "passive_buffs", "plots", "plot_events", "plot_next_events",
    "plot_event_conditions", "plot_conditions", "plot_aoe_conditions",
    "plot_effects", "skill_controllers", "anims", "projectiles", "fx_groups",
    "icons", "tags",
}

INCOMING_PREFIXES = {
    "buff": ("buff_trigger:", "buff_tick_effect:", "buff_unit_modifier:",
             "buff_modifier:", "tagged_buff:"),
    "skill": ("skill_effect_application:", "tagged_skill:"),
    "plot": ("plot_event:",),
    "plot_event": ("plot_effect:", "plot_event_condition:",
                   "plot_aoe_condition:", "plot_next_event:"),
}

SERVER_HIT_EFFECTS = (
    (22266, 22271, 18, 1, "server-required",
     "AA8 coating -> native dummy; trigger 9973 consumes tag 3567"),
    (24093, 24095, 18, 1, "server-required",
     "AA8 Flame coating -> persistent native dummy; trigger 11343 applies Poison"),
    (24235, 24236, 18, 1, "server-required",
     "AA8 Wave coating -> native dummy; trigger 11420 consumes tag 3567"),
)

SHADOWPLAY_RANGED_UNIT_REQUIREMENTS = (
    ("Skill", 12139, 1, 29, 0, 0, 0),
    ("Skill", 12139, 1, 29, 2, 0, 0),
)

SHADOWPLAY_PLOT_UNIT_REQUIREMENTS = (
    ("PlotCondition", 9159, 1, 38, 0, 0, 0),
    ("PlotCondition", 9159, 1, 38, 1, 0, 0),
    ("PlotCondition", 9159, 1, 38, 5, 0, 0),
    ("PlotCondition", 21578, 1, 38, 0, 0, 0),
    ("PlotCondition", 21769, 1, 38, 0, 0, 0),
    ("PlotCondition", 21770, 1, 38, 0, 0, 0),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def exact_native_row(connection: sqlite3.Connection, entity_key: str):
    candidates = []
    for row in connection.execute(
        "SELECT source_table,row_json,state,provenance FROM native_rows "
        "WHERE entity_key=?", (entity_key,)
    ):
        try:
            payload = json.loads(row["row_json"])
        except json.JSONDecodeError:
            continue
        if row["source_table"] not in EXECUTABLE_TABLES or "id" not in payload:
            continue
        candidates.append((len(payload), row["source_table"], payload,
                           row["state"], row["provenance"]))
    return max(candidates, default=None, key=lambda item: item[0])


def evidence_closure(connection: sqlite3.Connection) -> tuple[set[str], dict[str, Any]]:
    selected = set(SEED_KEYS)
    changed = True
    while changed:
        changed = False
        for key in tuple(sorted(selected)):
            for relation in connection.execute(
                "SELECT dst_entity_key,state,authority,locator,loader_or_consumer "
                "FROM relations WHERE src_entity_key=? AND required=1", (key,)
            ):
                if relation["dst_entity_key"] not in selected:
                    selected.add(relation["dst_entity_key"])
                    changed = True

            kind = key.split(":", 1)[0]
            prefixes = INCOMING_PREFIXES.get(kind, ())
            if prefixes:
                for relation in connection.execute(
                    "SELECT src_entity_key FROM relations WHERE dst_entity_key=? "
                    "AND required=1", (key,)
                ):
                    source = relation["src_entity_key"]
                    if source.startswith(prefixes) and source not in selected:
                        selected.add(source)
                        changed = True

    provenance = {}
    for key in sorted(selected):
        relations = [dict(row) for row in connection.execute(
            "SELECT relation,dst_entity_key,state,authority,locator,"
            "loader_or_consumer,provenance FROM relations WHERE src_entity_key=? "
            "AND required=1 ORDER BY relation,ordinal", (key,)
        )]
        if relations:
            provenance[key] = relations
    return selected, provenance


def select_rows(connection: sqlite3.Connection, keys: set[str]):
    selected: dict[str, dict[int, tuple[dict[str, Any], str, str]]] = {}
    for key in sorted(keys):
        result = exact_native_row(connection, key)
        if result is None:
            continue
        _, table, payload, state, provenance = result
        selected.setdefault(table, {})[int(payload["id"])] = (payload, key, state)
    return selected


def rebuild_tombstone_roots(connection: sqlite3.Connection):
    schema = columns(connection, "skills")
    rebuilt = []
    field_provenance = []
    for skill_id, field_names in TOMBSTONE_ROOT_FIELDS.items():
        source = connection.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
        if source is None:
            raise RuntimeError(f"Missing live-materialized root {skill_id}")
        source = dict(source)
        row = {}
        for name, sql_type in schema.items():
            row[name] = "" if "TEXT" in sql_type.upper() else 0
        row["id"] = skill_id
        for name in field_names:
            if name not in schema:
                raise RuntimeError(f"skills.{name} is absent for root {skill_id}")
            row[name] = source[name]
            field_provenance.append((
                "skills", skill_id, name, "server-required",
                "live C2S learn identity + AA8 localization/descendant closure; "
                "field retained explicitly from the validated AA8 carrier",
            ))
        rebuilt.append(row)
    connection.executemany(
        "DELETE FROM skills WHERE id=?", [(skill_id,) for skill_id in TOMBSTONE_ROOT_FIELDS]
    )
    upsert_rows(connection, "skills", rebuilt)
    return field_provenance


def rebuild_shadowplay_unit_requirements(
    connection: sqlite3.Connection, game11: Path
) -> tuple[list[tuple[Any, ...]], dict[str, Any]]:
    """Replace inherited legacy requirements with the bounded AA8 closure."""
    rows, evidence = extract_unit_requirements(game11)
    native_skill_rows = sorted(
        (
            row["owner_type"], int(row["owner_id"]), int(row["display_msg"]),
            int(row["kind_id"]), int(row["value1"]), int(row["value2"]),
            int(row["value3"]),
        )
        for row in rows
        if row["owner_type"] == "Skill" and int(row["owner_id"]) in (10481, 12139)
    )
    expected_native = [("Skill", 12139, 1, 29, 2, 0, 0)]
    if native_skill_rows != expected_native:
        raise RuntimeError(
            f"Unexpected AA8 Shadowplay ranged requirements: {native_skill_rows}"
        )

    native_plot_rows = sorted(
        (
            row["owner_type"], int(row["owner_id"]), int(row["display_msg"]),
            int(row["kind_id"]), int(row["value1"]), int(row["value2"]),
            int(row["value3"]),
        )
        for row in rows
        if row["owner_type"] == "PlotCondition"
        and int(row["owner_id"]) in (9159, 21578, 21769, 21770)
    )
    if native_plot_rows != sorted(SHADOWPLAY_PLOT_UNIT_REQUIREMENTS):
        raise RuntimeError(
            f"Unexpected AA8 Shadowplay plot requirements: {native_plot_rows}"
        )

    inherited = [tuple(row) for row in connection.execute(
        "SELECT owner_type,owner_id,display_msg,kind_id,value1,value2,value3 "
        "FROM unit_reqs WHERE owner_type='Skill' AND owner_id IN (10481,12139) "
        "ORDER BY owner_id,kind_id,value1,value2,value3"
    )]
    expected_inherited = [
        ("Skill", 10481, 1, 29, 0, 0, 0),
        ("Skill", 12139, 1, 29, 0, 0, 0),
    ]
    if inherited != expected_inherited:
        raise RuntimeError(f"Unexpected inherited Shadowplay requirements: {inherited}")

    inherited_plot = [tuple(row) for row in connection.execute(
        "SELECT owner_type,owner_id,display_msg,kind_id,value1,value2,value3 "
        "FROM unit_reqs WHERE owner_type='PlotCondition' "
        "AND owner_id IN (9159,21578,21769,21770) "
        "ORDER BY owner_id,kind_id,value1,value2,value3"
    )]
    if inherited_plot:
        raise RuntimeError(
            f"Unexpected inherited Shadowplay plot requirements: {inherited_plot}"
        )

    connection.execute(
        "DELETE FROM unit_reqs WHERE owner_type='Skill' AND owner_id IN (10481,12139)"
    )
    connection.execute(
        "DELETE FROM unit_reqs WHERE owner_type='PlotCondition' "
        "AND owner_id IN (9159,21578,21769,21770)"
    )
    connection.executemany(
        "INSERT INTO unit_reqs(owner_type,owner_id,display_msg,kind_id,value1,value2,value3) "
        "VALUES(?,?,?,?,?,?,?)",
        SHADOWPLAY_RANGED_UNIT_REQUIREMENTS + SHADOWPLAY_PLOT_UNIT_REQUIREMENTS,
    )
    provenance = [
        (
            "Skill", 12139, 29, 0, "legacy_3_0_corroborated",
            "AA8 skill or_unit_reqs=true + exact game11 rifle companion + "
            "r575 exact relation shape; retained bow alternative",
        ),
        (
            "Skill", 12139, 29, 2, "client-native",
            "AA8 game11 cached unit_reqs exact row; owner ref 69872 resolved as Skill",
        ),
    ]
    provenance.extend(
        (
            owner_type, owner_id, kind_id, value1, "client-native",
            "AA8 game11 cached unit_reqs exact row; owner ref resolved as "
            "PlotCondition; kind 38 is URK_TARGET_OWNER_TYPE",
        )
        for owner_type, owner_id, _, kind_id, value1, _, _
        in SHADOWPLAY_PLOT_UNIT_REQUIREMENTS
    )
    return provenance, evidence


def verify(connection: sqlite3.Connection) -> dict[str, Any]:
    errors = []
    roots = [row[0] for row in connection.execute(
        "SELECT id FROM skills WHERE ability_id=8 ORDER BY id")]
    if roots != list(ALL_ROOTS):
        errors.append(f"Shadowplay root mismatch: {roots}")
    visible = [row[0] for row in connection.execute(
        "SELECT id FROM skills WHERE id IN ({}) AND show=1 ORDER BY id".format(
            ",".join(map(str, VISIBLE_ROOTS))))]
    if visible != list(VISIBLE_ROOTS):
        errors.append(f"Visible root mismatch: {visible}")
    passives = [tuple(row) for row in connection.execute(
        "SELECT id,buff_id,req_points,skill_points FROM passive_buffs "
        "WHERE ability_id=8 ORDER BY id")]
    expected_passives = [(skill_id, buff_id, req_points, 0)
                         for skill_id, buff_id, req_points in PASSIVES]
    if passives != expected_passives:
        errors.append(f"Passive mismatch: {passives}")
    quarantined = [tuple(row) for row in connection.execute(
        "SELECT skill_id,reason FROM native_combat_skill_status "
        "WHERE ability_id=8 AND status='quarantined'")]
    if quarantined:
        errors.append(f"Shadowplay quarantine remains: {quarantined}")
    if connection.execute(
        "SELECT COUNT(*) FROM buff_triggers WHERE id=88000001").fetchone()[0]:
        errors.append("Reserved poison trigger 88000001 remains")
    if connection.execute("SELECT COUNT(*) FROM effects WHERE id=720").fetchone()[0]:
        errors.append("Historical poison effect 720 remains")
    if connection.execute("SELECT COUNT(*) FROM buff_effects WHERE id=256").fetchone()[0]:
        errors.append("Historical poison BuffEffect 256 remains")
    poison_requirements = [tuple(row) for row in connection.execute(
        "SELECT kind_id,value1 FROM unit_reqs "
        "WHERE owner_type='Skill' AND owner_id=10481 ORDER BY kind_id,value1"
    )]
    if poison_requirements:
        errors.append(f"Historical Poisoned Weapons requirements remain: {poison_requirements}")
    mark_requirements = [tuple(row) for row in connection.execute(
        "SELECT kind_id,value1 FROM unit_reqs "
        "WHERE owner_type='Skill' AND owner_id=12139 ORDER BY kind_id,value1"
    )]
    if mark_requirements != [(29, 0), (29, 2)]:
        errors.append(f"Stalker's Mark ranged alternatives mismatch: {mark_requirements}")
    mark_or = connection.execute(
        "SELECT or_unit_reqs FROM skills WHERE id=12139"
    ).fetchone()
    if mark_or is None or int(mark_or[0]) != 1:
        errors.append(f"Stalker's Mark OR contract mismatch: {mark_or}")
    plot_requirements = [tuple(row) for row in connection.execute(
        "SELECT owner_type,owner_id,display_msg,kind_id,value1,value2,value3 "
        "FROM unit_reqs WHERE owner_type='PlotCondition' "
        "AND owner_id IN (9159,21578,21769,21770) "
        "ORDER BY owner_id,kind_id,value1,value2,value3"
    )]
    if plot_requirements != sorted(SHADOWPLAY_PLOT_UNIT_REQUIREMENTS):
        errors.append(f"Shadowplay plot unit requirements mismatch: {plot_requirements}")
    relations = [tuple(row) for row in connection.execute(
        "SELECT source_buff_id,impact_buff_id,"
        "allowed_damage_type_mask,require_positive_damage "
        "FROM native_server_hit_effects ORDER BY source_buff_id")]
    if relations != [row[:4] for row in SERVER_HIT_EFFECTS]:
        errors.append(f"Server hit relation mismatch: {relations}")
    bubble = connection.execute(
        "SELECT kind_id,speech FROM bubble_effects WHERE id=4766").fetchone()
    plot_effect = connection.execute(
        "SELECT actual_id,actual_type,event_id,source_id,target_id "
        "FROM plot_effects WHERE id=35005").fetchone()
    if bubble is None or bubble[0] != 3:
        errors.append("BubbleEffect 4766 is absent")
    if plot_effect is None or tuple(plot_effect) != (4766, "BubbleEffect", 25140, 1, 3):
        errors.append(f"Shadowsmite Lightning effect mismatch: {plot_effect}")

    dangling_plot_references = {}
    plot_reference_checks = {
        "plot_events.plot_id": (
            "SELECT COUNT(*) FROM plot_events child LEFT JOIN plots parent "
            "ON parent.id=child.plot_id WHERE parent.id IS NULL"
        ),
        "plot_effects.event_id": (
            "SELECT COUNT(*) FROM plot_effects child LEFT JOIN plot_events parent "
            "ON parent.id=child.event_id WHERE parent.id IS NULL"
        ),
        "plot_next_events.event_id": (
            "SELECT COUNT(*) FROM plot_next_events child LEFT JOIN plot_events parent "
            "ON parent.id=child.event_id WHERE parent.id IS NULL"
        ),
        "plot_next_events.next_event_id": (
            "SELECT COUNT(*) FROM plot_next_events child LEFT JOIN plot_events parent "
            "ON parent.id=child.next_event_id WHERE parent.id IS NULL"
        ),
        "plot_event_conditions.event_id": (
            "SELECT COUNT(*) FROM plot_event_conditions child LEFT JOIN plot_events parent "
            "ON parent.id=child.event_id WHERE parent.id IS NULL"
        ),
        "plot_aoe_conditions.event_id": (
            "SELECT COUNT(*) FROM plot_aoe_conditions child LEFT JOIN plot_events parent "
            "ON parent.id=child.event_id WHERE parent.id IS NULL"
        ),
    }
    for reference, query in plot_reference_checks.items():
        count = connection.execute(query).fetchone()[0]
        if count:
            dangling_plot_references[reference] = count
    if dangling_plot_references:
        errors.append(f"Dangling plot references: {dangling_plot_references}")

    shadowplay_plot_events = connection.execute(
        "SELECT COUNT(*) FROM plot_events WHERE plot_id=3008"
    ).fetchone()[0]
    if shadowplay_plot_events == 0:
        errors.append("Shadowsmite Lightning plot 3008 has no events")
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite checks failed: {quick}/{integrity}")
    if errors:
        raise RuntimeError("\n".join(errors))
    return {
        "roots": len(roots), "visible_roots": len(visible), "passives": len(passives),
        "quarantined": 0, "quick_check": quick, "integrity_check": integrity,
        "server_hit_effects": len(relations), "bubble_effect_4766": True,
        "shadowplay_plot_3008_events": shadowplay_plot_events,
        "dangling_plot_references": 0,
        "poisoned_weapons_unit_requirements": 0,
        "stalkers_mark_ranged_alternatives": 2,
        "shadowplay_plot_unit_requirements": len(plot_requirements),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    if sha256_file(args.runtime_carrier) != EXPECTED_CARRIER_SHA256:
        raise RuntimeError("Unexpected runtime carrier SHA-256")
    if sha256_file(args.knowledge) != EXPECTED_KNOWLEDGE_SHA256:
        raise RuntimeError("Unexpected knowledge SHA-256")
    if sha256_file(args.game11) != EXPECTED_GAME11_SHA256:
        raise RuntimeError("Unexpected AA8 game11 SHA-256")
    observations = json.loads(args.observations.read_text(encoding="utf-8"))
    observed = sorted(int(row["skill_id"]) for row in observations["observations"]
                      if row["kind"] == "learn_request")
    if observed != [10082, 10104, 10189]:
        raise RuntimeError(f"Unexpected live learn evidence: {observed}")

    knowledge = ro(args.knowledge)
    try:
        keys, relation_evidence = evidence_closure(knowledge)
        native_rows = select_rows(knowledge, keys)
    finally:
        knowledge.close()

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    if output == args.runtime_carrier.resolve():
        raise ValueError("Output cannot replace the carrier")
    shutil.copy2(args.runtime_carrier, output)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        field_provenance = rebuild_tombstone_roots(connection)
        unit_req_provenance, unit_req_evidence = rebuild_shadowplay_unit_requirements(
            connection, args.game11
        )
        connection.execute("DELETE FROM buff_triggers WHERE id=88000001")
        connection.execute("DELETE FROM effects WHERE id=720")
        connection.execute("DELETE FROM buff_effects WHERE id=256")
        connection.execute("DROP TABLE IF EXISTS shadowplay_reconstruction_v2_metadata")

        imported = {}
        provenance_rows = []
        for table in sorted(native_rows):
            rows = [native_rows[table][row_id][0] for row_id in sorted(native_rows[table])]
            imported[table] = upsert_rows(connection, table, rows)
            for row_id in sorted(native_rows[table]):
                _, key, state = native_rows[table][row_id]
                provenance_rows.append((
                    table, row_id, "client-native", key,
                    f"knowledge native_rows state={state}",
                ))

        connection.execute(
            "CREATE TABLE native_server_hit_effects("
            "source_buff_id INTEGER PRIMARY KEY,impact_buff_id INTEGER NOT NULL,"
            "allowed_damage_type_mask INTEGER NOT NULL,"
            "require_positive_damage INTEGER NOT NULL,classification TEXT NOT NULL,"
            "provenance TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO native_server_hit_effects VALUES(?,?,?,?,?,?)",
            SERVER_HIT_EFFECTS,
        )
        connection.execute(
            "CREATE TABLE shadowplay_v3_row_provenance("
            "table_name TEXT NOT NULL,row_id INTEGER NOT NULL,classification TEXT NOT NULL,"
            "entity_key TEXT NOT NULL,evidence TEXT NOT NULL,"
            "PRIMARY KEY(table_name,row_id))"
        )
        connection.executemany(
            "INSERT INTO shadowplay_v3_row_provenance VALUES(?,?,?,?,?)",
            provenance_rows,
        )
        connection.execute(
            "CREATE TABLE shadowplay_v3_field_provenance("
            "table_name TEXT NOT NULL,row_id INTEGER NOT NULL,field_name TEXT NOT NULL,"
            "classification TEXT NOT NULL,evidence TEXT NOT NULL,"
            "PRIMARY KEY(table_name,row_id,field_name))"
        )
        connection.executemany(
            "INSERT INTO shadowplay_v3_field_provenance VALUES(?,?,?,?,?)",
            field_provenance,
        )
        connection.execute(
            "CREATE TABLE shadowplay_v6_unit_req_provenance("
            "owner_type TEXT NOT NULL,owner_id INTEGER NOT NULL,"
            "kind_id INTEGER NOT NULL,value1 INTEGER NOT NULL,"
            "classification TEXT NOT NULL,evidence TEXT NOT NULL,"
            "PRIMARY KEY(owner_type,owner_id,kind_id,value1))"
        )
        connection.executemany(
            "INSERT INTO shadowplay_v6_unit_req_provenance VALUES(?,?,?,?,?,?)",
            unit_req_provenance,
        )
        connection.execute(
            "CREATE TABLE shadowplay_reconstruction_v6_metadata("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance TEXT NOT NULL)"
        )
        metadata = {
            "client_build": CLIENT_BUILD,
            "classification_policy": "client-native|server-required only",
            "shadowplay_roots": ",".join(map(str, ALL_ROOTS)),
            "tombstone_roots": "10082,10104,10189",
            "poison_contract": "22266->22271;24093->24095->21999;24235->24236",
            "poison_negative_evidence": "no AA8 relation 24093->40815; live TlId=0 damage disconnect",
            "bubble_contract": "plot_effect:35005->BubbleEffect:4766",
            "negative_evidence": "88000001,effect720,buff_effect256,V2-full-legacy-root",
            "ranged_admission": "10481:no-unit-req;12139:equip-ranged-bow-or-shotgun",
            "plot_unit_requirements": "kind38:URK_TARGET_OWNER_TYPE;9159=0|1|5",
        }
        connection.executemany(
            "INSERT INTO shadowplay_reconstruction_v6_metadata VALUES(?,?,?)",
            [(key, value, "aa8_shadowplay_v6") for key, value in sorted(metadata.items())],
        )
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,8,'enabled',?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=8,status='enabled',reason=excluded.reason,provenance=excluded.provenance",
            [(skill_id, "Shadowplay V3 client-native/server-required closure",
              "aa8_shadowplay_v6") for skill_id in ALL_ROOTS],
        )
        connection.commit()
        verification = verify(connection) if args.verify else None
        connection.execute("VACUUM")
    except Exception:
        connection.rollback()
        connection.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        if output.exists():
            connection.close()

    manifest = {
        "format_version": 6,
        "client_build": CLIENT_BUILD,
        "authority": {
            "aa8_knowledge": "client-native",
            "live_learn_packets": "server-required tombstone identity",
            "modern": "structural comparator only",
            "custom_hypothesis": "forbidden",
        },
        "sources": {
            "carrier": {"path": str(args.runtime_carrier.resolve()),
                        "sha256": EXPECTED_CARRIER_SHA256},
            "knowledge": {"path": str(args.knowledge.resolve()),
                          "sha256": EXPECTED_KNOWLEDGE_SHA256},
            "game11": {"path": str(args.game11.resolve()),
                       "sha256": EXPECTED_GAME11_SHA256},
            "observations": {"path": str(args.observations.resolve()),
                             "sha256": sha256_file(args.observations)},
        },
        "evidence_keys": sorted(keys),
        "relation_evidence": relation_evidence,
        "imported": imported,
        "server_hit_effects": SERVER_HIT_EFFECTS,
        "unit_requirements": {
            "rows": SHADOWPLAY_RANGED_UNIT_REQUIREMENTS + SHADOWPLAY_PLOT_UNIT_REQUIREMENTS,
            "provenance": unit_req_provenance,
            "game11": unit_req_evidence,
            "tombstones": [
                {
                    "owner_id": 10481,
                    "classification": "client-native-negative",
                    "evidence": "zero rows in the complete 13053-row AA8 game11 result; "
                                "skill or_unit_reqs=false; legacy bow row removed",
                }
            ],
        },
        "verification": verification,
        "output": {"path": str(output), "sha256": sha256_file(output)},
    }
    args.manifest.write_text(canonical(manifest), encoding="utf-8")
    print(canonical({
        "output": str(output), "output_sha256": manifest["output"]["sha256"],
        "manifest": str(args.manifest.resolve()), "verification": verification,
    }))
    return manifest


if __name__ == "__main__":
    build(parse_args())
