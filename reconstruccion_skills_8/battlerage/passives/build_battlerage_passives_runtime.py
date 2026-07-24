#!/usr/bin/env python3
"""Build a separate AA8 runtime containing native Battlerage passive data."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--skill-modifiers", required=True, type=Path)
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


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    rows = connection.execute("SELECT COUNT(*) FROM skill_modifiers").fetchone()[0]
    native_mastery = connection.execute(
        "SELECT owner_type,owner_id,dynamic_value,skill_attribute_id,skill_id,"
        "synergy,tag_id,target_buff_id,target_tag_id,unit_modifier_type_id,value "
        "FROM skill_modifiers WHERE owner_type='Buff' AND owner_id=831"
    ).fetchall()
    stale = connection.execute(
        "SELECT COUNT(*) FROM skill_modifiers WHERE owner_id IN (811,7544)"
    ).fetchone()[0]
    proc = connection.execute(
        "SELECT req_buff_id,trigger_kind_id,skill_tag_id,effect_id,cooldown_ms "
        "FROM passive_procs"
    ).fetchall()
    effect = connection.execute(
        "SELECT actual_type,actual_id FROM effects WHERE id=56457"
    ).fetchall()
    suppression = connection.execute(
        "SELECT req_buff_id,cooldown_ms,provenance FROM combat_buffs "
        "WHERE req_buff_id IN (2610,2621) ORDER BY req_buff_id"
    ).fetchall()
    errors = []
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite checks: quick={quick}, integrity={integrity}")
    if rows != 1571:
        errors.append(f"skill_modifiers rows={rows}, expected=1571")
    if native_mastery != [
        ("Buff", 831, 0, 10, 0, 0, 415, 0, 0, 1, 10)
    ]:
        errors.append(f"Weapon Mastery row mismatch: {native_mastery}")
    if stale != 0:
        errors.append(f"historical Battlerage skill modifiers remain: {stale}")
    if proc != [(811, 1, 415, 56457, 1000)]:
        errors.append(f"Attack Speed Training proc mismatch: {proc}")
    if effect != [("BuffEffect", 19755)]:
        errors.append(f"native Frenzy effect mismatch: {effect}")
    if suppression != [
        (2610, 12000, "server_derived"),
        (2621, 12000, "server_derived"),
    ]:
        errors.append(f"passive suppression mismatch: {suppression}")
    if errors:
        raise RuntimeError("AA8 passive runtime validation failed:\n" + "\n".join(errors))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "skill_modifier_count": rows,
        "historical_battlerage_skill_modifier_count": stale,
        "passive_proc_count": len(proc),
        "passive_suppression_count": len(suppression),
    }


def main() -> int:
    args = parse_args()
    catalog = json.loads(args.skill_modifiers.read_text(encoding="utf-8"))
    rows = catalog["rows"]
    if len(rows) != 1571:
        raise RuntimeError(f"Catalog contains {len(rows)} rows")
    if args.output.resolve() == args.runtime_carrier.resolve():
        raise ValueError("Output must not replace the runtime carrier")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.runtime_carrier, args.output)
    connection = sqlite3.connect(args.output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE IF EXISTS skill_modifiers")
        connection.execute(
            "CREATE TABLE skill_modifiers ("
            "owner_type TEXT NOT NULL, owner_id INTEGER NOT NULL, "
            "dynamic_value INTEGER NOT NULL, skill_attribute_id INTEGER NOT NULL, "
            "skill_id INTEGER NOT NULL, synergy INTEGER NOT NULL, "
            "tag_id INTEGER NOT NULL, target_buff_id INTEGER NOT NULL, "
            "target_tag_id INTEGER NOT NULL, unit_modifier_type_id INTEGER NOT NULL, "
            "value INTEGER NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO skill_modifiers VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            [
                tuple(
                    row[column]
                    for column in (
                        "owner_type",
                        "owner_id",
                        "dynamic_value",
                        "skill_attribute_id",
                        "skill_id",
                        "synergy",
                        "tag_id",
                        "target_buff_id",
                        "target_tag_id",
                        "unit_modifier_type_id",
                        "value",
                    )
                )
                for row in rows
            ],
        )
        connection.execute(
            "CREATE INDEX idx_skill_modifiers_owner "
            "ON skill_modifiers(owner_type, owner_id)"
        )
        combat_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(combat_buffs)")
        }
        if "cooldown_ms" not in combat_columns:
            connection.execute(
                "ALTER TABLE combat_buffs ADD COLUMN cooldown_ms INTEGER NOT NULL DEFAULT 0"
            )
        if "provenance" not in combat_columns:
            connection.execute(
                "ALTER TABLE combat_buffs ADD COLUMN provenance TEXT NOT NULL "
                "DEFAULT 'carrier_unmigrated'"
            )
        connection.execute(
            "UPDATE combat_buffs SET cooldown_ms=12000, provenance='server_derived' "
            "WHERE req_buff_id IN (2610,2621)"
        )
        connection.execute("DROP TABLE IF EXISTS passive_procs")
        connection.execute(
            "CREATE TABLE passive_procs ("
            "id INTEGER PRIMARY KEY, req_buff_id INTEGER NOT NULL, "
            "trigger_kind_id INTEGER NOT NULL, skill_tag_id INTEGER NOT NULL, "
            "effect_id INTEGER NOT NULL, cooldown_ms INTEGER NOT NULL, "
            "provenance TEXT NOT NULL, evidence TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO passive_procs VALUES(1,811,1,415,56457,1000,?,?)",
            (
                "server_derived",
                "AA8 buff 811 description + native tag 415 + native effect 56457",
            ),
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS battlerage_passive_metadata ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL, provenance TEXT NOT NULL)"
        )
        connection.execute("DELETE FROM battlerage_passive_metadata")
        connection.executemany(
            "INSERT INTO battlerage_passive_metadata VALUES(?,?,?)",
            [
                (
                    "skill_modifiers_catalog_sha256",
                    sha256_file(args.skill_modifiers),
                    "game11_native",
                ),
                (
                    "skill_modifiers_x2game_loader",
                    "FUN_39979330",
                    "x2game_confirmed",
                ),
                (
                    "attack_speed_training_proc",
                    "req_buff=811;trigger=damage_skill_hit;tag=415;"
                    "effect=56457;cooldown_ms=1000",
                    "server_derived",
                ),
                (
                    "passive_suppression",
                    "req_buffs=2610,2621;cooldown_ms=12000",
                    "server_derived",
                ),
                (
                    "historical_3_0_fallback",
                    "false",
                    "server_only",
                ),
            ],
        )
        connection.commit()
        verification = validate(connection) if args.verify else None
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
            },
            "skill_modifiers": {
                "path": str(args.skill_modifiers.resolve()),
                "sha256": sha256_file(args.skill_modifiers),
                "provenance": "game11_native",
            },
        },
        "policy": {
            "historical_3_0_fallback": False,
            "unsupported_contextual_modifiers": "loaded but quarantined by backend",
        },
        "verification": verification,
        "output": {
            "path": str(args.output.resolve()),
            "sha256": sha256_file(args.output),
        },
    }
    args.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    print(canonical_json(manifest["output"] | {"verification": verification}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
