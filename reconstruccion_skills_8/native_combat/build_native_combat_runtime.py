#!/usr/bin/env python3
"""Build an isolated runtime compact with an AA 8.0-only player combat domain."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


ALIASES = {
    "aoe_shapes": {"area_target_kind_id": "target_update_method_id"},
    "buffs": {
        "max_combat_resource": "max_high_ability_resource",
        "min_combat_resource": "min_high_ability_resource",
    },
    "damage_effects": {
        "combat_resource_dps_md": "high_ability_resource_dps_md",
        "combat_resource_level_md": "high_ability_resource_level_md",
        "combat_resource_md": "high_ability_resource_md",
        "use_combat_resource": "use_high_ability_resource",
    },
    "plot_next_events": {"combat_resource": "high_ability_resource"},
    "skill_effects": {
        "end_combat_resource": "end_high_ability_resource",
        "start_combat_resource": "start_high_ability_resource",
    },
}

RELATION_SCOPES = {
    "skill_effects": "skill_id",
    "buff_tick_effects": "buff_id",
    "buff_triggers": "buff_id",
    "buff_unit_modifiers": "buff_id",
    "tagged_buffs": "buff_id",
    "plot_effects": "event_id",
    "plot_event_conditions": "event_id",
    "plot_aoe_conditions": "event_id",
    "plot_next_events": "event_id",
}

CONCRETE_EFFECT_TABLES = {
    "AggroEffect": "aggro_effects",
    "BubbleEffect": "bubble_effects",
    "BuffEffect": "buff_effects",
    "CombatResourceEffect": "combat_resource_effects",
    "ConversionEffect": "conversion_effects",
    "DamageEffect": "damage_effects",
    "DispelEffect": "dispel_effects",
    "ExtendChargeEffect": "extend_charge_effects",
    "HealEffect": "heal_effects",
    "InteractionEffect": "interaction_effects",
    "KillNpcWithoutCorpseEffect": "kill_npc_without_corpse_effects",
    "ManaBurnEffect": "mana_burn_effects",
    "PhysicalExplosionEffect": "physical_explosion_effects",
    "ResetAoeDiminishingEffect": "reset_aoe_diminishing_effects",
    "RestoreManaEffect": "restore_mana_effects",
    "SpawnEffect": "spawn_effects",
    "SpecialEffect": "special_effects",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
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


def quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def columns(connection: sqlite3.Connection, table: str) -> dict[str, str]:
    return {
        str(row[1]): str(row[2] or "INTEGER")
        for row in connection.execute(f"PRAGMA table_info({quote(table)})")
    }


def inferred_type(values: list[Any]) -> str:
    values = [value for value in values if value is not None]
    if any(isinstance(value, str) for value in values):
        return "TEXT"
    if any(isinstance(value, float) for value in values):
        return "REAL"
    return "INTEGER"


def normalize(table: str, row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    aliases = ALIASES.get(table, {})
    result: dict[str, Any] = {}
    derived: dict[str, str] = {}
    for name, value in row.items():
        target = aliases.get(name, name)
        if isinstance(value, str) and value.startswith("<ref:"):
            # Unresolved presentation strings are not gameplay data.  Keeping
            # them as NULL avoids a silent historical-text fallback.
            value = None
            derived[target] = "server_derived:null_unresolved_client_string"
        if table == "skill_effects" and target == "end_level" and int(value or 0) == 99:
            value = 255
            derived[target] = "server_derived:aaemu_level_sentinel_99_to_255"
        result[target] = value
    return result, derived


def ensure_table(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    normalized = [normalize(table, row)[0] for row in rows]
    names = list(normalized[0])
    if not table_exists(connection, table):
        declarations = []
        for name in names:
            declaration = f"{quote(name)} {inferred_type([row.get(name) for row in normalized])}"
            if name == "id":
                declaration += " PRIMARY KEY"
            declarations.append(declaration)
        connection.execute(f"CREATE TABLE {quote(table)} ({', '.join(declarations)})")
        return
    current = columns(connection, table)
    for name in names:
        if name in current:
            continue
        connection.execute(
            f"ALTER TABLE {quote(table)} ADD COLUMN {quote(name)} "
            f"{inferred_type([row.get(name) for row in normalized])}"
        )


def upsert_rows(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"rows": 0, "derived_fields": []}
    ensure_table(connection, table, rows)
    available = columns(connection, table)
    normalized_rows = []
    derived_fields = []
    for source in rows:
        row, derived = normalize(table, source)
        normalized_rows.append(row)
        if derived:
            derived_fields.append({"id": int(source["id"]), "fields": derived})
    insert_columns = [name for name in normalized_rows[0] if name in available]
    if "id" not in insert_columns:
        raise RuntimeError(f"Native table {table} has no id column")
    placeholders = ",".join("?" for _ in insert_columns)
    updates = [name for name in insert_columns if name != "id"]
    sql = (
        f"INSERT INTO {quote(table)} ({','.join(quote(name) for name in insert_columns)}) "
        f"VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET "
        + ",".join(f"{quote(name)}=excluded.{quote(name)}" for name in updates)
    )
    connection.executemany(
        sql,
        [tuple(row.get(name) for name in insert_columns) for row in normalized_rows],
    )
    return {
        "rows": len(rows),
        "columns": insert_columns,
        "derived_fields": derived_fields,
        "historical_values_preserved": False,
    }


def replace_player_skills(
    connection: sqlite3.Connection,
    skills: list[dict[str, Any]],
) -> dict[str, Any]:
    available = columns(connection, "skills")
    connection.execute("DELETE FROM skills WHERE ability_id BETWEEN 1 AND 14")
    insert_columns = list(available)
    sql = (
        f"INSERT INTO skills ({','.join(quote(name) for name in insert_columns)}) "
        f"VALUES ({','.join('?' for _ in insert_columns)})"
    )
    derived_rows = []
    values = []
    for source in skills:
        normalized, derived = normalize("skills", source)
        row = []
        for name in insert_columns:
            if name in normalized:
                value = normalized[name]
            elif name == "need_learn":
                value = int(
                    int(source.get("show") or 0) != 0
                    and int(source.get("skill_points") or 0) > 0
                )
                derived[name] = "server_derived:visible_positive_skill_point_cost"
            elif "TEXT" in available[name].upper():
                value = None
            else:
                value = 0
            row.append(value)
        values.append(tuple(row))
        if derived:
            derived_rows.append({"id": int(source["id"]), "fields": derived})
    connection.executemany(sql, values)
    return {
        "rows": len(skills),
        "columns": insert_columns,
        "derived_fields": derived_rows,
        "historical_values_preserved": False,
    }


def delete_for_ids(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    values: set[int],
) -> int:
    if not values or not table_exists(connection, table) or column not in columns(connection, table):
        return 0
    removed = 0
    ordered = sorted(values)
    for start in range(0, len(ordered), 800):
        batch = ordered[start : start + 800]
        cursor = connection.execute(
            f"DELETE FROM {quote(table)} WHERE {quote(column)} IN "
            f"({','.join('?' for _ in batch)})",
            batch,
        )
        removed += max(cursor.rowcount, 0)
    return removed


def selected_rows(catalog: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], set[int]]:
    enabled_skill_ids = {
        int(row["skill_id"])
        for row in catalog["skill_status"]
        if row["status"] == "enabled"
    }
    enabled_abilities = {
        int(row["ability_id"])
        for row in catalog["skill_status"]
        if row["status"] == "enabled"
    }
    enabled_ids: dict[str, set[int]] = {}
    for skill_id in enabled_skill_ids:
        for table, ids in catalog["skill_table_ids"][str(skill_id)].items():
            enabled_ids.setdefault(table, set()).update(int(value) for value in ids)

    # Ability-level passive_buffs do not carry a skill id.  They are admitted
    # only after every skill in that ability has a closed native dependency
    # graph, so a partial specialization cannot import unrelated relations.
    fully_enabled_abilities = {
        int(row["id"]) for row in catalog["abilities"] if row["status"] == "enabled"
    }
    for ability_id in fully_enabled_abilities:
        for table, ids in catalog["ability_table_ids"][str(ability_id)].items():
            enabled_ids.setdefault(table, set()).update(int(value) for value in ids)
    result = {}
    for table, rows in catalog["tables"].items():
        if table == "skills":
            result[table] = rows
            continue
        ids = enabled_ids.get(table, set())
        result[table] = [row for row in rows if int(row["id"]) in ids]
    return result, enabled_abilities


def validate(
    connection: sqlite3.Connection,
    catalog: dict[str, Any],
    runtime_tables: dict[str, list[dict[str, Any]]],
    enabled_abilities: set[int],
) -> dict[str, Any]:
    errors = []
    table_ids = {
        table: {int(row["id"]) for row in rows}
        for table, rows in runtime_tables.items()
    }
    table_rows = {
        table: {int(row["id"]): row for row in rows}
        for table, rows in runtime_tables.items()
    }
    expected_skill_ids = {int(row["id"]) for row in catalog["tables"]["skills"]}
    actual_skill_ids = {
        int(row[0])
        for row in connection.execute("SELECT id FROM skills WHERE ability_id BETWEEN 1 AND 14")
    }
    if actual_skill_ids != expected_skill_ids:
        errors.append(
            f"player skill ids differ: expected={len(expected_skill_ids)} actual={len(actual_skill_ids)}"
        )
    quarantined = {
        int(row["skill_id"])
        for row in catalog["skill_status"]
        if row["status"] == "quarantined"
    }
    if quarantined:
        placeholders = ",".join("?" for _ in quarantined)
        leaked = connection.execute(
            f"SELECT COUNT(*) FROM skill_effects WHERE skill_id IN ({placeholders})",
            sorted(quarantined),
        ).fetchone()[0]
        if leaked:
            errors.append(f"{leaked} effect relations remain active for quarantined skills")
    status_count = connection.execute("SELECT COUNT(*) FROM native_combat_skill_status").fetchone()[0]
    if status_count != len(expected_skill_ids):
        errors.append(f"native skill status rows={status_count}, expected={len(expected_skill_ids)}")

    enabled_skill_ids = expected_skill_ids.difference(quarantined)
    for row in runtime_tables["skill_effects"]:
        if int(row["skill_id"]) not in enabled_skill_ids:
            errors.append(f"skill_effect {row['id']} points to disabled skill {row['skill_id']}")
        if int(row["effect_id"]) not in table_ids["effects"]:
            errors.append(f"skill_effect {row['id']} has missing effect {row['effect_id']}")

    def validate_concrete(row: dict[str, Any], context: str) -> None:
        actual_type = str(row["actual_type"])
        actual_id = int(row["actual_id"])
        if actual_type == "SkillController":
            if actual_id not in table_ids.get("skill_controllers", set()):
                errors.append(f"{context} has missing SkillController {actual_id}")
            return
        concrete_table = CONCRETE_EFFECT_TABLES.get(actual_type)
        if concrete_table is None:
            errors.append(f"{context} uses unsupported primitive {actual_type}")
        elif actual_id not in table_ids.get(concrete_table, set()):
            errors.append(
                f"{context} has missing {concrete_table}.{actual_id} for {actual_type}"
            )

    for row in runtime_tables["effects"]:
        validate_concrete(row, f"effect {row['id']}")
    for row in runtime_tables.get("plot_effects", []):
        if int(row["event_id"]) not in table_ids.get("plot_events", set()):
            errors.append(f"plot_effect {row['id']} has missing event {row['event_id']}")
        validate_concrete(row, f"plot_effect {row['id']}")

    for table in ("plot_event_conditions", "plot_aoe_conditions"):
        for row in runtime_tables.get(table, []):
            if int(row["event_id"]) not in table_ids.get("plot_events", set()):
                errors.append(f"{table}.{row['id']} has missing event {row['event_id']}")
            if int(row["condition_id"]) not in table_ids.get("plot_conditions", set()):
                errors.append(
                    f"{table}.{row['id']} has missing condition {row['condition_id']}"
                )
    for row in runtime_tables.get("plot_next_events", []):
        if int(row["event_id"]) not in table_ids.get("plot_events", set()):
            errors.append(f"plot_next_event {row['id']} has missing event {row['event_id']}")
        if int(row["next_event_id"]) not in table_ids.get("plot_events", set()):
            errors.append(
                f"plot_next_event {row['id']} has missing next event {row['next_event_id']}"
            )
    for row in runtime_tables.get("plot_events", []):
        plot_id = int(row["plot_id"])
        if plot_id not in table_ids.get("plots", set()):
            errors.append(f"plot_event {row['id']} has missing plot {plot_id}")
        if int(row["target_update_method_id"]) in (5, 6, 7):
            shape_id = int(row["target_update_method_param1"])
            if shape_id > 0 and shape_id not in table_ids.get("aoe_shapes", set()):
                errors.append(f"plot_event {row['id']} has missing AoE shape {shape_id}")

    for row in runtime_tables.get("buff_effects", []):
        if int(row["buff_id"]) not in table_ids.get("buffs", set()):
            errors.append(f"buff_effect {row['id']} has missing buff {row['buff_id']}")
    for table in ("buff_tick_effects", "buff_triggers"):
        for row in runtime_tables.get(table, []):
            if int(row["buff_id"]) not in table_ids.get("buffs", set()):
                errors.append(f"{table}.{row['id']} has missing buff {row['buff_id']}")
            if int(row["effect_id"]) not in table_ids.get("effects", set()):
                errors.append(f"{table}.{row['id']} has missing effect {row['effect_id']}")

    for skill_id in enabled_skill_ids:
        row = table_rows["skills"][skill_id]
        for field in (
            "toggle_buff_id",
            "channeling_buff_id",
            "channeling_target_buff_id",
        ):
            value = int(row.get(field) or 0)
            if value and value not in table_ids.get("buffs", set()):
                errors.append(f"skill {skill_id} has missing {field}={value}")
        for field in (
            "start_anim_id",
            "fire_anim_id",
            "channeling_anim_id",
            "dual_wield_fire_anim_id",
            "twohand_fire_anim_id",
        ):
            value = int(row.get(field) or 0)
            if value and value not in table_ids.get("anims", set()):
                errors.append(f"skill {skill_id} has missing {field}={value}")
        for field, table in (
            ("skill_controller_id", "skill_controllers"),
            ("projectile_id", "projectiles"),
            ("plot_id", "plots"),
        ):
            value = int(row.get(field) or 0)
            if value and value not in table_ids.get(table, set()):
                errors.append(f"skill {skill_id} has missing {field}={value}")

    effects = {
        int(row["id"]): (str(row["actual_type"]), int(row["actual_id"]))
        for row in runtime_tables["effects"]
    }
    relations: dict[int, list[dict[str, Any]]] = {}
    for row in runtime_tables["skill_effects"]:
        relations.setdefault(int(row["skill_id"]), []).append(row)
    expected_triple = {
        18132: [("DamageEffect", 3220), ("BuffEffect", 6548), ("SpecialEffect", 6515), ("DamageEffect", 9373)],
        18134: [("DamageEffect", 3221), ("SpecialEffect", 6628), ("DamageEffect", 9374)],
        18131: [("DamageEffect", 3218), ("SpecialEffect", 6629), ("BuffEffect", 6708), ("SpecialEffect", 15810), ("BuffEffect", 24379)],
    }
    for skill_id, expected in expected_triple.items():
        actual = [
            effects[int(row["effect_id"])]
            for row in sorted(relations.get(skill_id, []), key=lambda row: int(row["id"]))
        ]
        if actual != expected:
            errors.append(f"Triple Slash chain {skill_id}: {actual}")
    plot = connection.execute(
        "SELECT target_update_method_param1, target_update_method_param2, "
        "target_update_method_param8, target_update_method_param9 "
        "FROM plot_events WHERE id=20729"
    ).fetchone()
    if tuple(plot or ()) != (10110, 20, 4, 111):
        errors.append(f"Triple Slash AoE event 20729 is invalid: {plot}")
    if connection.execute("SELECT COUNT(*) FROM plot_events WHERE plot_id=2541").fetchone()[0] != 19:
        errors.append("Triple Slash plot 2541 does not contain 19 native events")

    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite validation failed: quick={quick}, integrity={integrity}")
    if errors:
        raise RuntimeError("Native combat runtime validation failed:\n" + "\n".join(errors))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "player_skill_count": len(expected_skill_ids),
        "abilities_with_enabled_skills": sorted(enabled_abilities),
        "fully_enabled_abilities": sorted(
            int(row["id"])
            for row in catalog["abilities"]
            if row["status"] == "enabled"
        ),
        "enabled_skill_count": len(expected_skill_ids) - len(quarantined),
        "quarantined_skill_count": len(quarantined),
        "historical_player_combat_fallback_rows": 0,
        "triple_slash_plot_events": 19,
    }


def main() -> int:
    args = parse_args()
    for path in (args.runtime_carrier, args.catalog, args.schema):
        if not path.is_file():
            raise FileNotFoundError(path)
    output = args.output.resolve()
    if output == args.runtime_carrier.resolve():
        raise ValueError("The output must not replace the runtime carrier")
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if "historical_3_0" in json.dumps(catalog.get("provenance", {})):
        raise RuntimeError("Historical combat provenance is forbidden")
    runtime_tables, enabled_abilities = selected_rows(catalog)

    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_carrier, output)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        connection.executescript(args.schema.read_text(encoding="utf-8"))

        old_skill_ids = {
            int(row[0])
            for row in connection.execute("SELECT id FROM skills WHERE ability_id BETWEEN 1 AND 14")
        }
        new_skill_ids = {int(row["id"]) for row in runtime_tables["skills"]}
        all_player_skill_ids = old_skill_ids | new_skill_ids
        pruned = {
            "skill_effects": delete_for_ids(
                connection, "skill_effects", "skill_id", all_player_skill_ids
            ),
            "passive_buffs": delete_for_ids(
                connection, "passive_buffs", "ability_id", set(range(1, 15))
            ),
        }

        buff_ids = {int(row["id"]) for row in runtime_tables.get("buffs", [])}
        plot_ids = {int(row["id"]) for row in runtime_tables.get("plots", [])}
        event_ids = {int(row["id"]) for row in runtime_tables.get("plot_events", [])}
        for table, scope_column in RELATION_SCOPES.items():
            if table == "skill_effects":
                continue
            scope = buff_ids if scope_column == "buff_id" else event_ids
            pruned[table] = delete_for_ids(connection, table, scope_column, scope)
        pruned["plot_events"] = delete_for_ids(connection, "plot_events", "plot_id", plot_ids)

        merge: dict[str, Any] = {}
        merge["skills"] = replace_player_skills(connection, runtime_tables["skills"])
        for table, rows in runtime_tables.items():
            if table == "skills" or not rows:
                continue
            merge[table] = upsert_rows(connection, table, rows)

        connection.execute("DELETE FROM native_combat_skill_status")
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,?,?,?,?)",
            [
                (
                    int(row["skill_id"]),
                    int(row["ability_id"]),
                    str(row["status"]),
                    str(row["reason"]),
                    "game11_native",
                )
                for row in catalog["skill_status"]
            ],
        )
        metadata = {
            "catalog_sha256": sha256_file(args.catalog),
            "client_compact_sha256": catalog["sources"]["client_compact"]["sha256"],
            "game11_sha256": catalog["sources"]["client_game_stream"]["sha256"],
            "historical_combat_fallback": "false",
        }
        connection.execute("DELETE FROM native_combat_metadata")
        connection.executemany(
            "INSERT INTO native_combat_metadata(key,value,provenance) VALUES(?,?,?)",
            [(key, value, "server_derived") for key, value in sorted(metadata.items())],
        )
        connection.commit()
        verification = validate(
            connection, catalog, runtime_tables, enabled_abilities
        ) if args.verify else None
        if args.verify:
            connection.execute("VACUUM")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    manifest = {
        "format_version": 1,
        "sources": {
            "runtime_carrier": {
                "path": str(args.runtime_carrier.resolve()),
                "sha256": sha256_file(args.runtime_carrier),
                "purpose": "backend schema and out-of-scope NPC/item/doodad domains; never a player-combat fallback",
            },
            "native_catalog": {
                "path": str(args.catalog.resolve()),
                "sha256": sha256_file(args.catalog),
            },
            "server_schema": {
                "path": str(args.schema.resolve()),
                "sha256": sha256_file(args.schema),
            },
        },
        "policy": {
            "player_combat_rows": "AA 8.0 native only",
            "historical_combat_fallback": False,
            "quarantine": "skills with unclosed native dependencies have no active skill_effect relations",
            "quarantine_granularity": "per skill, including its chained internal-skill closure",
            "partial_ability_passives": "withheld until the complete ability dependency graph is native and closed",
            "out_of_scope_domains": "NPC/item/doodad rows are carried unchanged but are unreachable as player-combat fallback",
        },
        "pruned": pruned,
        "merge": merge,
        "verification": verification,
        "output": {"path": str(output), "sha256": sha256_file(output)},
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["output"] | {"verification": verification}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
