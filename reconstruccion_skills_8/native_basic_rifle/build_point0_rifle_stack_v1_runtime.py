#!/usr/bin/env python3
"""Layer the closed AA8 Shoot Rifle plot over the accepted point-0 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAIN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "reconstruccion_skills_8" / "native_combat"))
from build_native_combat_runtime import (  # noqa: E402
    CONCRETE_EFFECT_TABLES,
    delete_for_ids,
    table_exists,
    upsert_rows,
)

DEFAULT_BASE = Path(r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-point0-repair-stack-v1.sqlite3")
DEFAULT_OUTPUT = Path(r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-point0-rifle-stack-v1.sqlite3")
DEFAULT_CATALOG = DOMAIN / "generated" / "native-basic-rifle-v1.json"
DEFAULT_MANIFEST = DOMAIN / "generated" / "point0-rifle-stack-v1-runtime-manifest.json"
EXPECTED_BASE_SHA256 = "444C9A2586468C049C4B68B480724D0D3222F9A1E8091951F520033AA39935DF"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate(connection: sqlite3.Connection, catalog: dict) -> dict:
    tables = catalog["tables"]
    ids = {table: {int(row["id"]) for row in rows} for table, rows in tables.items()}
    errors: list[str] = []
    skill = connection.execute(
        "SELECT plot_only,plot_id,projectile_id,weapon_slot_for_autoattack_id,max_range,auto_fire,start_autoattack "
        "FROM skills WHERE id=46938"
    ).fetchone()
    if tuple(skill or ()) != (1, 5796, 9, 17, 15.0, 1, 1):
        errors.append(f"skill 46938 runtime fields differ: {skill}")
    if connection.execute("SELECT COUNT(*) FROM plot_events WHERE plot_id=5796").fetchone()[0] != 16:
        errors.append("plot 5796 does not contain 16 native events")
    closure_events = ids["plot_events"]
    placeholders = ",".join("?" for _ in closure_events)
    if connection.execute(
        f"SELECT COUNT(*) FROM plot_effects WHERE event_id IN ({placeholders})", sorted(closure_events)
    ).fetchone()[0] != 17:
        errors.append("plot 5796 does not contain 17 native plot effects")

    for row in tables["plot_effects"]:
        concrete = CONCRETE_EFFECT_TABLES.get(str(row["actual_type"]))
        if concrete is None or int(row["actual_id"]) not in ids.get(concrete, set()):
            errors.append(f"unclosed plot effect {row['id']}: {row['actual_type']}.{row['actual_id']}")
    for row in tables["plot_events"]:
        if int(row["plot_id"]) != 5796:
            errors.append(f"event {row['id']} points outside plot 5796")
        if int(row["target_update_method_id"]) in (5, 6, 7):
            shape = int(row["target_update_method_param1"])
            if shape and shape not in ids["aoe_shapes"]:
                errors.append(f"event {row['id']} misses AoE shape {shape}")
    for table in ("plot_event_conditions", "plot_aoe_conditions"):
        for row in tables[table]:
            if int(row["event_id"]) not in closure_events or int(row["condition_id"]) not in ids["plot_conditions"]:
                errors.append(f"unclosed {table}.{row['id']}")
    for row in tables["plot_next_events"]:
        if int(row["event_id"]) not in closure_events or int(row["next_event_id"]) not in closure_events:
            errors.append(f"unclosed plot_next_events.{row['id']}")

    damage = connection.execute(
        "SELECT id,dps_multiplier,dps_inc_multiplier,use_ranged_weapon,weapon_slot_id,damage_type_id "
        "FROM damage_effects WHERE id IN (14635,14638,14639) ORDER BY id"
    ).fetchall()
    if len(damage) != 3 or any(tuple(row[1:]) != (0.6, 0.6, 1, 17, 4) for row in damage):
        errors.append(f"native Shoot Rifle damage differs: {damage}")
    if connection.execute("SELECT COUNT(*) FROM anims WHERE id=1074").fetchone()[0] != 1:
        errors.append("native rifle animation 1074 is missing")
    if connection.execute("SELECT COUNT(*) FROM projectiles WHERE id=1347").fetchone()[0] != 1:
        errors.append("native rifle projectile 1347 is missing")
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite checks failed: quick={quick}, integrity={integrity}")
    if errors:
        raise RuntimeError("Shoot Rifle runtime validation failed:\n" + "\n".join(errors))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "skill_id": 46938,
        "plot_id": 5796,
        "plot_events": 16,
        "plot_effects": 17,
        "damage_effects": [14635, 14638, 14639],
        "animation_id": 1074,
        "projectile_id": 1347,
        "historical_3_0_rows": 0,
    }


def build(options: argparse.Namespace) -> dict:
    base_hash = sha256(options.base_runtime)
    if base_hash != EXPECTED_BASE_SHA256:
        raise RuntimeError(f"unexpected base runtime SHA-256: {base_hash}")
    catalog = json.loads(options.catalog.read_text(encoding="utf-8"))
    if catalog.get("historical_3_0_used") is not False:
        raise RuntimeError("catalog does not explicitly forbid historical 3.0 data")
    tables = catalog["tables"]
    catalog_hash = sha256(options.catalog)

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copyfile(options.base_runtime, temporary)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("BEGIN IMMEDIATE")
        plot_ids = {5796}
        new_event_ids = {int(row["id"]) for row in tables["plot_events"]}
        old_event_ids = {
            int(row[0])
            for row in connection.execute("SELECT id FROM plot_events WHERE plot_id=5796")
        }
        event_ids = old_event_ids | new_event_ids
        pruned = {}
        for table in ("plot_effects", "plot_event_conditions", "plot_aoe_conditions", "plot_next_events"):
            pruned[f"{table}.event_id"] = delete_for_ids(connection, table, "event_id", event_ids)
        pruned["plot_next_events.next_event_id"] = delete_for_ids(
            connection, "plot_next_events", "next_event_id", event_ids
        )
        pruned["plot_events.plot_id"] = delete_for_ids(connection, "plot_events", "plot_id", plot_ids)

        merged = {}
        for table, rows in tables.items():
            merged[table] = upsert_rows(connection, table, rows)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS aaemu_point0_rifle_stack ("
            "phase TEXT PRIMARY KEY, authority TEXT NOT NULL, base_sha256 TEXT NOT NULL, catalog_sha256 TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_point0_rifle_stack VALUES (?,?,?,?)",
            ("point0-rifle-stack-v1", catalog["authority"], base_hash, catalog_hash),
        )
        checks = validate(connection, catalog)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()
    os.replace(temporary, options.output)
    manifest = {
        "format_version": 1,
        "phase": "point0-rifle-stack-v1-runtime",
        "authority": catalog["authority"],
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": base_hash},
            "native_catalog": {"path": str(options.catalog), "sha256": catalog_hash},
        },
        "scope": {
            "skill_id": 46938,
            "plot_id": 5796,
            "tables": catalog["table_counts"],
            "policy": "targeted native closure only; all other runtime domains preserved",
        },
        "pruned": pruned,
        "merged": merged,
        "validation": checks,
        "output": {"path": str(options.output), "bytes": options.output.stat().st_size, "sha256": sha256(options.output)},
    }
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()
    print(json.dumps(build(options), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
