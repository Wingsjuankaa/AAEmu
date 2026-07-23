#!/usr/bin/env python3
"""Create an AA8 runtime compact with native unit modifiers and formulas."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


EXPECTED_ROWS = 49095
BATTLE_FOCUS = {
    404: {(81, 280), (17, 150)},
    7651: {(81, 300), (17, 200)},
    13612: {(81, 320), (17, 250)},
    13613: {(81, 340), (17, 300)},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--formula-catalog", required=True, type=Path)
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


def table_count(connection: sqlite3.Connection, table: str) -> int:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]) if exists else 0


def validate(
    connection: sqlite3.Connection,
    catalog: dict[str, Any],
    formula_catalog: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    count = table_count(connection, "unit_modifiers")
    if count != EXPECTED_ROWS:
        errors.append(f"unit_modifiers rows={count}, expected={EXPECTED_ROWS}")
    dynamic_count = int(
        connection.execute(
            "SELECT COUNT(*) FROM unit_modifiers WHERE dynamic_value <> 0"
        ).fetchone()[0]
    )
    if dynamic_count != 149:
        errors.append(f"dynamic rows={dynamic_count}, expected=149")
    for buff_id, expected in BATTLE_FOCUS.items():
        actual = {
            (int(row[0]), int(row[1]))
            for row in connection.execute(
                "SELECT unit_attribute_id, value FROM unit_modifiers "
                "WHERE owner_type='Buff' AND owner_id=? AND dynamic_value=0",
                (buff_id,),
            )
        }
        if actual != expected:
            errors.append(f"Battle Focus buff {buff_id}: {sorted(actual)}")
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite quick={quick}, integrity={integrity}")
    if catalog["authority"]["historical_reference_used"]:
        errors.append("catalog declares historical gameplay provenance")
    if formula_catalog["authority"]["historical_reference_used"]:
        errors.append("formula catalog declares historical gameplay provenance")
    formula_count = table_count(connection, "unit_formulas")
    variable_count = table_count(connection, "unit_formula_variables")
    if formula_count != 480:
        errors.append(f"unit_formulas rows={formula_count}, expected=480")
    if variable_count != 3600:
        errors.append(f"unit_formula_variables rows={variable_count}, expected=3600")
    parry_formula = connection.execute(
        "SELECT formula FROM unit_formulas WHERE owner_type_id=0 AND kind_id=5"
    ).fetchone()
    if parry_formula is None or str(parry_formula[0]) != (
        " if_negative(heir_level-1,(str*15)*100,100000*str^0.26)"
    ):
        errors.append(f"native character parry formula mismatch: {parry_formula}")
    if errors:
        raise RuntimeError("AA8 combat-stat runtime validation failed:\n" + "\n".join(errors))
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "unit_modifier_count": count,
        "dynamic_modifier_count": dynamic_count,
        "unit_formula_count": formula_count,
        "unit_formula_variable_count": variable_count,
        "maximum_attribute_id": int(
            connection.execute("SELECT MAX(unit_attribute_id) FROM unit_modifiers").fetchone()[0]
        ),
        "historical_unit_modifier_rows": 0,
    }


def main() -> int:
    args = parse_args()
    for path in (args.runtime_carrier, args.catalog, args.formula_catalog):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output.resolve() == args.runtime_carrier.resolve():
        raise ValueError("Output must not replace the runtime carrier")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    formula_catalog = json.loads(args.formula_catalog.read_text(encoding="utf-8"))
    rows = catalog["rows"]
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"Catalog contains {len(rows)} unit modifiers")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.runtime_carrier, args.output)
    connection = sqlite3.connect(args.output)
    try:
        carrier_formula_counts = {
            table: table_count(connection, table)
            for table in ("unit_formulas", "unit_formula_variables", "formulas", "wearable_formulas")
        }
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE IF EXISTS unit_modifiers")
        connection.execute(
            "CREATE TABLE unit_modifiers ("
            "owner_type TEXT NOT NULL, "
            "owner_id INTEGER NOT NULL, "
            "dynamic_value INTEGER NOT NULL, "
            "linear_level_bonus INTEGER NOT NULL, "
            "unit_attribute_id INTEGER NOT NULL, "
            "unit_modifier_type_id INTEGER NOT NULL, "
            "value INTEGER NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO unit_modifiers("
            "owner_type,owner_id,dynamic_value,linear_level_bonus,"
            "unit_attribute_id,unit_modifier_type_id,value"
            ") VALUES(?,?,?,?,?,?,?)",
            [
                (
                    str(row["owner_type"]),
                    int(row["owner_id"]),
                    int(row["dynamic_value"]),
                    int(row["linear_level_bonus"]),
                    int(row["unit_attribute_id"]),
                    int(row["unit_modifier_type_id"]),
                    int(row["value"]),
                )
                for row in rows
            ],
        )
        connection.execute(
            "CREATE INDEX idx_unit_modifiers_owner "
            "ON unit_modifiers(owner_type, owner_id)"
        )
        connection.execute("DELETE FROM unit_formula_variables")
        connection.execute("DELETE FROM unit_formulas")
        connection.executemany(
            "INSERT INTO unit_formulas(id,formula,kind_id,owner_type_id) "
            "VALUES(?,?,?,?)",
            [
                (
                    int(row["id"]),
                    str(row["formula"]),
                    int(row["kind_id"]),
                    int(row["owner_type_id"]),
                )
                for row in formula_catalog["formulas"]
            ],
        )
        connection.executemany(
            "INSERT INTO unit_formula_variables("
            "id,key,unit_formula_id,value,variable_kind_id"
            ") VALUES(?,?,?,?,?)",
            [
                (
                    int(row["id"]),
                    int(row["key"]),
                    int(row["unit_formula_id"]),
                    float(row["value"]),
                    int(row["variable_kind_id"]),
                )
                for row in formula_catalog["variables"]
            ],
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS native_combat_stats_metadata ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL, provenance TEXT NOT NULL)"
        )
        connection.execute("DELETE FROM native_combat_stats_metadata")
        metadata = {
            "unit_modifiers_catalog_sha256": sha256_file(args.catalog),
            "unit_modifiers_game11_sha256": catalog["source"]["sha256"],
            "unit_modifiers_provenance": "game11_native",
            "unit_modifiers_x2game_loader": "FUN_3997ab60",
            "unit_formulas_catalog_sha256": sha256_file(args.formula_catalog),
            "unit_formulas_game11_sha256": formula_catalog["source"]["sha256"],
            "unit_formulas_provenance": "game11_native",
            "unit_formulas_x2game_loader": "FUN_39a73350",
            "unit_formula_variables_x2game_loader": "FUN_39a730a0",
            "dynamic_value_policy": "preserved_not_evaluated_as_fixed_bonus",
        }
        connection.executemany(
            "INSERT INTO native_combat_stats_metadata(key,value,provenance) VALUES(?,?,?)",
            [
                (
                    key,
                    value,
                    "game11_native" if key.startswith("unit_modifiers_") else "server_derived",
                )
                for key, value in sorted(metadata.items())
            ],
        )
        connection.commit()
        verification = (
            validate(connection, catalog, formula_catalog) if args.verify else None
        )
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
                "purpose": "stable AA8 native-combat v2 runtime and out-of-scope server schema",
            },
            "native_unit_modifiers": {
                "path": str(args.catalog.resolve()),
                "sha256": sha256_file(args.catalog),
                "provenance": "game11_native",
            },
            "native_unit_formulas": {
                "path": str(args.formula_catalog.resolve()),
                "sha256": sha256_file(args.formula_catalog),
                "provenance": "game11_native",
            },
        },
        "policy": {
            "unit_modifiers": "AA8 game11 native only",
            "historical_unit_modifier_fallback": False,
            "dynamic_value": "preserved; never interpreted as a fixed bonus",
            "base_formulas": "AA8 game11 native only",
            "historical_unit_formula_fallback": False,
        },
        "carrier_formula_counts": carrier_formula_counts,
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
