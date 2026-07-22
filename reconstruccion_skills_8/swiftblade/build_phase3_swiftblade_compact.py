#!/usr/bin/env python3
"""Build a runtime compact from a native specialization closure."""

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

SKIP_TABLES = {"skills"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-compact", required=True, type=Path)
    parser.add_argument("--closure", required=True, type=Path)
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
    non_null = [value for value in values if value is not None]
    if any(isinstance(value, str) for value in non_null):
        return "TEXT"
    if any(isinstance(value, float) for value in non_null):
        return "REAL"
    return "INTEGER"


def ensure_table(connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    alias_sources = set(ALIASES.get(table, {}))
    source_columns = [name for name in rows[0] if name not in alias_sources]
    if not table_exists(connection, table):
        declarations = []
        for name in source_columns:
            values = [row.get(name) for row in rows]
            declaration = f"{quote(name)} {inferred_type(values)}"
            if name == "id":
                declaration += " PRIMARY KEY"
            declarations.append(declaration)
        connection.execute(f"CREATE TABLE {quote(table)} ({', '.join(declarations)})")
        return
    current = columns(connection, table)
    for name in source_columns:
        if name in current:
            continue
        values = [row.get(name) for row in rows]
        connection.execute(
            f"ALTER TABLE {quote(table)} ADD COLUMN {quote(name)} {inferred_type(values)}"
        )


def normalized_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    aliases = ALIASES.get(table, {})
    result = {aliases.get(key, key): value for key, value in row.items()}
    if table == "skill_effects" and int(result.get("end_level") or 0) == 99:
        result["end_level"] = 255
    return result


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    ensure_table(connection, table, rows)
    available = columns(connection, table)
    normalized = [normalized_row(table, row) for row in rows]
    insert_columns = [name for name in normalized[0] if name in available]
    if "id" not in insert_columns:
        raise RuntimeError(f"{table} has no id column in the native closure")
    existing: dict[int, dict[str, Any]] = {}
    ids = [int(row["id"]) for row in normalized]
    for start in range(0, len(ids), 800):
        batch = ids[start : start + 800]
        placeholders = ",".join("?" for _ in batch)
        for old in connection.execute(
            f"SELECT * FROM {quote(table)} WHERE id IN ({placeholders})", batch
        ):
            existing[int(old[0])] = dict(old)
    collision_differences = []
    preserved_unresolved_strings = []
    for row in normalized:
        old = existing.get(int(row["id"]))
        if old is None:
            continue
        for name in insert_columns:
            value = row.get(name)
            if (
                isinstance(value, str)
                and value.startswith("<ref:")
                and isinstance(old.get(name), str)
                and not old[name].startswith("<ref:")
            ):
                preserved_unresolved_strings.append(
                    {"id": int(row["id"]), "column": name, "client_reference": value}
                )
                row[name] = old[name]
        differences = {
            name: {"historical": old.get(name), "client_8": row.get(name)}
            for name in insert_columns
            if old.get(name) != row.get(name)
        }
        if differences:
            collision_differences.append({"id": int(row["id"]), "fields": differences})
    placeholders = ", ".join("?" for _ in insert_columns)
    update_columns = [name for name in insert_columns if name != "id"]
    sql = (
        f"INSERT INTO {quote(table)} ({', '.join(quote(name) for name in insert_columns)}) "
        f"VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET "
        + ", ".join(f"{quote(name)}=excluded.{quote(name)}" for name in update_columns)
    )
    connection.executemany(sql, [tuple(row.get(name) for name in insert_columns) for row in normalized])
    return {
        "rows": len(rows),
        "inserted": len(rows) - len(existing),
        "collisions": len(existing),
        "changed_collisions": len(collision_differences),
        "collision_differences": collision_differences,
        "preserved_unresolved_strings": preserved_unresolved_strings,
        "columns": insert_columns,
    }


def delete_outside_closure(
    connection: sqlite3.Connection,
    table: str,
    scope_column: str,
    scope_ids: set[int],
    closure_ids: set[int],
) -> int:
    if not scope_ids or not table_exists(connection, table):
        return 0
    available = columns(connection, table)
    if scope_column not in available or "id" not in available:
        return 0
    scope_values = sorted(scope_ids)
    parameters: list[int] = list(scope_values)
    sql = (
        f"DELETE FROM {quote(table)} WHERE {quote(scope_column)} IN "
        f"({','.join('?' for _ in scope_values)})"
    )
    if closure_ids:
        retained = sorted(closure_ids)
        sql += f" AND id NOT IN ({','.join('?' for _ in retained)})"
        parameters.extend(retained)
    cursor = connection.execute(sql, parameters)
    return cursor.rowcount


def prune_scoped_relations(
    connection: sqlite3.Connection,
    closure: dict[str, Any],
) -> dict[str, int]:
    tables = closure["tables"]
    skill_ids = {int(row["id"]) for row in tables.get("skills", [])}
    buff_ids = {int(row["id"]) for row in tables.get("buffs", [])}
    plot_ids = {int(row["id"]) for row in tables.get("plots", [])}
    native_event_ids = {int(row["id"]) for row in tables.get("plot_events", [])}
    existing_event_ids: set[int] = set()
    if plot_ids and table_exists(connection, "plot_events"):
        values = sorted(plot_ids)
        existing_event_ids = {
            int(row[0])
            for row in connection.execute(
                f"SELECT id FROM plot_events WHERE plot_id IN "
                f"({','.join('?' for _ in values)})",
                values,
            )
        }
    event_scope = existing_event_ids.union(native_event_ids)

    pruned: dict[str, int] = {}
    relation_scopes = {
        "skill_effects": ("skill_id", skill_ids),
        "buff_tick_effects": ("buff_id", buff_ids),
        "buff_triggers": ("buff_id", buff_ids),
        "buff_unit_modifiers": ("buff_id", buff_ids),
        "tagged_buffs": ("buff_id", buff_ids),
        "plot_effects": ("event_id", event_scope),
        "plot_event_conditions": ("event_id", event_scope),
        "plot_aoe_conditions": ("event_id", event_scope),
        "plot_next_events": ("event_id", event_scope),
    }
    for table, (scope_column, scope_ids) in relation_scopes.items():
        closure_ids = {int(row["id"]) for row in tables.get(table, [])}
        count = delete_outside_closure(
            connection, table, scope_column, scope_ids, closure_ids
        )
        if count:
            pruned[table] = count

    count = delete_outside_closure(
        connection,
        "plot_events",
        "plot_id",
        plot_ids,
        native_event_ids,
    )
    if count:
        pruned["plot_events"] = count

    ability_id = int(closure["ability"]["id"])
    passive_ids = {int(row["id"]) for row in tables.get("passive_buffs", [])}
    count = delete_outside_closure(
        connection,
        "passive_buffs",
        "ability_id",
        {ability_id},
        passive_ids,
    )
    if count:
        pruned["passive_buffs"] = count
    return pruned


def validate(connection: sqlite3.Connection, closure: dict[str, Any]) -> dict[str, Any]:
    tables = closure["tables"]
    errors: list[str] = []
    effect_types = {
        int(row["id"]): (str(row["actual_type"]), int(row["actual_id"]))
        for row in tables["effects"]
    }
    concrete_tables = {
        "AggroEffect": "aggro_effects",
        "BuffEffect": "buff_effects",
        "CombatResourceEffect": "combat_resource_effects",
        "ConversionEffect": "conversion_effects",
        "DamageEffect": "damage_effects",
        "DispelEffect": "dispel_effects",
        "InteractionEffect": "interaction_effects",
        "PhysicalExplosionEffect": "physical_explosion_effects",
        "SpecialEffect": "special_effects",
    }
    for relation in tables["skill_effects"]:
        effect_id = int(relation["effect_id"])
        if effect_id not in effect_types:
            errors.append(f"skill_effect {relation['id']} lacks effect {effect_id}")
    for effect_id, (actual_type, actual_id) in effect_types.items():
        table = concrete_tables.get(actual_type)
        if table and connection.execute(
            f"SELECT 1 FROM {quote(table)} WHERE id=?", (actual_id,)
        ).fetchone() is None:
            errors.append(f"effect {effect_id} lacks {table}.{actual_id}")
    for relation in tables["plot_effects"]:
        actual_type = str(relation["actual_type"])
        actual_id = int(relation["actual_id"])
        table = "skill_controllers" if actual_type == "SkillController" else concrete_tables.get(actual_type)
        if table and connection.execute(
            f"SELECT 1 FROM {quote(table)} WHERE id=?", (actual_id,)
        ).fetchone() is None:
            errors.append(f"plot_effect {relation['id']} lacks {table}.{actual_id}")
    event_ids = {int(row["id"]) for row in tables["plot_events"]}
    for relation in tables["plot_next_events"]:
        if int(relation["event_id"]) not in event_ids or int(relation["next_event_id"]) not in event_ids:
            errors.append(f"orphan plot_next_event {relation['id']}")
    for table in ("plot_effects", "plot_event_conditions", "plot_aoe_conditions"):
        for row in tables.get(table, []):
            if int(row["event_id"]) not in event_ids:
                errors.append(f"orphan {table}.{row['id']}")
    conditions = {int(row["id"]) for row in tables["plot_conditions"]}
    for table in ("plot_event_conditions", "plot_aoe_conditions"):
        for row in tables.get(table, []):
            if int(row["condition_id"]) not in conditions:
                errors.append(f"{table}.{row['id']} lacks condition {row['condition_id']}")
    for event in tables["plot_events"]:
        if int(event["target_update_method_id"]) not in (5, 6, 7):
            continue
        shape_id = int(event["target_update_method_param1"])
        if shape_id > 0 and connection.execute(
            "SELECT 1 FROM aoe_shapes WHERE id=?", (shape_id,)
        ).fetchone() is None:
            errors.append(f"plot_event {event['id']} lacks aoe_shapes.{shape_id}")
    ability_id = int(closure["ability"]["id"])
    if ability_id == 12:
        golden_skill_ids = (40331, 40337, 40339)
    elif ability_id == 1:
        golden_skill_ids = (18132, 18134, 18131, 36401, 36402, 36403, 36404, 36405, 36406)
    else:
        golden_skill_ids = ()
    golden = {}
    for skill_id in golden_skill_ids:
        golden[skill_id] = [
            effect_types[int(row[0])]
            for row in connection.execute(
                "SELECT effect_id FROM skill_effects WHERE skill_id=? ORDER BY id", (skill_id,)
            )
        ]
    expected = {}
    if ability_id == 12:
        expected = {
            40331: [("DamageEffect", 12250), ("SpecialEffect", 42648)],
            40337: [("DamageEffect", 12257)],
        }
    elif ability_id == 1:
        expected = {
            18132: [("DamageEffect", 3220), ("BuffEffect", 6548), ("SpecialEffect", 6515), ("DamageEffect", 9373)],
            18134: [("DamageEffect", 3221), ("SpecialEffect", 6628), ("DamageEffect", 9374)],
            18131: [("DamageEffect", 3218), ("SpecialEffect", 6629), ("BuffEffect", 6708), ("SpecialEffect", 15810), ("BuffEffect", 24379)],
            36401: [("DamageEffect", 9584), ("BuffEffect", 22833), ("SpecialEffect", 28540), ("DamageEffect", 9585)],
            36402: [("DamageEffect", 9586), ("SpecialEffect", 28541), ("DamageEffect", 9587)],
            36403: [("DamageEffect", 9588), ("BuffEffect", 22835), ("DamageEffect", 9908)],
            36404: [("DamageEffect", 9589), ("SpecialEffect", 28544), ("DamageEffect", 9590)],
            36405: [("DamageEffect", 9591), ("SpecialEffect", 28545), ("DamageEffect", 9592)],
            36406: [("DamageEffect", 9593), ("BuffEffect", 22838)],
        }
    for skill_id, chain in expected.items():
        if golden[skill_id] != chain:
            errors.append(f"golden chain mismatch for {skill_id}: {golden[skill_id]}")
    if ability_id == 12 and len(golden[40339]) != 9:
        errors.append(f"Sinister Strike has {len(golden[40339])} relations instead of 9")
    if ability_id == 1:
        for plot_id in (2855, 2856, 2857):
            count = connection.execute(
                "SELECT COUNT(*) FROM plot_events WHERE plot_id=?", (plot_id,)
            ).fetchone()[0]
            if count == 0:
                errors.append(f"Triple Slash plot {plot_id} has no events")
        if closure["diagnostics"]["unresolved_effect_dependencies"]:
            errors.append("Battlerage closure has unresolved effect dependencies")
        if closure["diagnostics"]["unresolved_plot_types"]:
            errors.append("Battlerage closure has unresolved plot types")
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite validation failed: quick={quick}, integrity={integrity}")
    if errors:
        raise RuntimeError("Phase 3 compact validation failed:\n" + "\n".join(errors[:50]))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "golden_chains": {str(key): value for key, value in golden.items()},
        "orphan_events": 0,
        "missing_concrete_dependencies": 0,
        "animation_ids_missing": closure["diagnostics"]["animation_ids_missing"],
        "aoe_shape_ids_missing": closure["diagnostics"]["aoe_shape_ids_missing"],
    }


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    args = parse_args()
    if not args.runtime_compact.is_file() or not args.closure.is_file():
        raise FileNotFoundError("Runtime compact or closure is missing")
    output = args.output.resolve()
    if output == args.runtime_compact.resolve():
        raise ValueError("Output must not replace the Phase 2 compact")
    closure = json.loads(args.closure.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_compact, output)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        pruned = prune_scoped_relations(connection, closure)
        merge = {}
        for table, rows in closure["tables"].items():
            if table in SKIP_TABLES or not rows:
                continue
            merge[table] = upsert_rows(connection, table, rows)
        connection.commit()
        verification = validate(connection, closure) if args.verify else None
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    manifest = {
        "format_version": 1,
        "sources": {
            "phase2_runtime": {"path": str(args.runtime_compact.resolve()), "sha256": sha256_file(args.runtime_compact)},
            "specialization_closure": {"path": str(args.closure.resolve()), "sha256": sha256_file(args.closure)},
        },
        "output": {"path": str(output), "sha256": sha256_file(output)},
        "policy": {
            "scope": f"only ids in the native {closure['ability']['name']} closure",
            "collision_winner": "Kakao 8.0 native row",
            "unresolved_interned_strings": "matching historical text is retained only when game11 exposes <ref:N>; the native reference remains in the closure manifest",
            "phase2_source_modified": False,
            "end_level_normalization": "99 -> 255; original remains in closure manifest",
            "combat_resource_alias": "mapped to historical high_ability_resource columns while preserving other confirmed native columns",
        },
        "pruned_historical_relations": pruned,
        "merge": merge,
        "verification": verification,
    }
    args.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    print(canonical_json({
        "output": str(output),
        "sha256": manifest["output"]["sha256"],
        "manifest": str(args.manifest.resolve()),
        "verification": verification,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
