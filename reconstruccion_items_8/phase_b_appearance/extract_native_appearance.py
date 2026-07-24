#!/usr/bin/env python3
"""Build the native AA8 appearance-conversion catalogue candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"

TABLES: dict[str, dict[str, Any]] = {
    "item_look_converts": {
        "columns": "id gold name".split(),
        "layout": "68 68 78".split(),
        "start": 0x649BB68,
        "expected": 35,
        "loader": "x2game.dll FUN_39a08490",
    },
    "item_look_convert_holdables": {
        "columns": "id holdable_id item_look_convert_id".split(),
        "layout": ("68 " * 3).split(),
        "start": 0x83A3A14,
        "expected": 29,
        "loader": "x2game.dll FUN_39a07ad0",
    },
    "item_look_convert_wearables": {
        "columns": (
            "id item_category_id item_look_convert_id wearable_slot_id"
        ).split(),
        "layout": ("68 " * 4).split(),
        "start": 0x83A3B93,
        "expected": 10,
        "loader": "x2game.dll FUN_39a07d10",
    },
    "item_look_convert_required_items": {
        "columns": "id item_count item_look_convert_id item_id".split(),
        "layout": ("68 " * 4).split(),
        "start": 0x83A3C43,
        "expected": 30,
        "loader": "x2game.dll FUN_39a07f90",
    },
    "item_look_revert_required_items": {
        "columns": "id item_count item_look_convert_id item_id".split(),
        "layout": ("68 " * 4).split(),
        "start": 0x83A3E47,
        "expected": 28,
        "loader": "x2game.dll FUN_39a08210",
    },
}

DDL = {
    "item_look_converts": """
        CREATE TABLE item_look_converts (
            id INTEGER PRIMARY KEY, gold INTEGER NOT NULL, name TEXT NOT NULL
        )""",
    "item_look_convert_holdables": """
        CREATE TABLE item_look_convert_holdables (
            id INTEGER PRIMARY KEY, holdable_id INTEGER NOT NULL,
            item_look_convert_id INTEGER NOT NULL
        )""",
    "item_look_convert_wearables": """
        CREATE TABLE item_look_convert_wearables (
            id INTEGER PRIMARY KEY, item_category_id INTEGER NOT NULL,
            item_look_convert_id INTEGER NOT NULL,
            wearable_slot_id INTEGER NOT NULL
        )""",
    "item_look_convert_required_items": """
        CREATE TABLE item_look_convert_required_items (
            id INTEGER PRIMARY KEY, item_count INTEGER NOT NULL,
            item_look_convert_id INTEGER NOT NULL, item_id INTEGER NOT NULL
        )""",
    "item_look_revert_required_items": """
        CREATE TABLE item_look_revert_required_items (
            id INTEGER PRIMARY KEY, item_count INTEGER NOT NULL,
            item_look_convert_id INTEGER NOT NULL, item_id INTEGER NOT NULL
        )""",
}


def parser_module():
    spec = importlib.util.spec_from_file_location("aa8_cached_result", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def extract(game11: Path):
    parser = parser_module()
    reader = parser.CachedResultReader(game11.read_bytes())
    tables: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, Any] = {}
    for name, spec in TABLES.items():
        rows, end = parser.read_cached_result(reader, spec["start"], spec["layout"])
        if len(rows) != spec["expected"]:
            raise RuntimeError(
                f"{name}: expected {spec['expected']} rows, got {len(rows)}"
            )
        tables[name] = [
            dict(zip(spec["columns"], row, strict=True)) for row in rows
        ]
        ranges[name] = {
            "start": spec["start"],
            "end": end,
            "rows": len(rows),
            "loader": spec["loader"],
        }
    return tables, ranges


def validate(connection: sqlite3.Connection) -> dict[str, int | str]:
    checks: dict[str, int | str] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0],
    }
    for table in (
        "item_look_convert_holdables",
        "item_look_convert_wearables",
        "item_look_convert_required_items",
        "item_look_revert_required_items",
    ):
        checks[f"missing_converts_{table}"] = int(
            connection.execute(
                f"""
                SELECT COUNT(*) FROM {table} r
                LEFT JOIN item_look_converts c ON c.id=r.item_look_convert_id
                WHERE c.id IS NULL
                """
            ).fetchone()[0]
        )
    for table in (
        "item_look_convert_required_items",
        "item_look_revert_required_items",
    ):
        checks[f"missing_items_{table}"] = int(
            connection.execute(
                f"""
                SELECT COUNT(*) FROM {table} r
                LEFT JOIN items i ON i.id=r.item_id WHERE i.id IS NULL
                """
            ).fetchone()[0]
        )
    return checks


def build(base: Path, output: Path, tables, hashes):
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        for name, spec in TABLES.items():
            connection.execute(f"DROP TABLE IF EXISTS {name}")
            connection.execute(DDL[name])
            columns = spec["columns"]
            placeholders = ",".join(f":{column}" for column in columns)
            connection.executemany(
                f"INSERT INTO {name} ({','.join(columns)}) VALUES ({placeholders})",
                sorted(
                    tables[name],
                    key=lambda row: tuple(row[column] for column in columns),
                ),
            )
        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES ('phase','B5-native-appearance'),
                   ('appearance_mutation','blocked-until-protocol-confirmed')
            """
        )
        for key, value in sorted(hashes.items()):
            connection.execute(
                """
                INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
                VALUES (?,?)
                """,
                (f"sha256_{key}", value),
            )
        connection.commit()
        connection.execute("VACUUM")
        return validate(connection)
    finally:
        connection.close()


def main() -> int:
    options = arguments()
    tables, ranges = extract(options.game11)
    hashes = {
        "game11": sha256(options.game11),
        "base_runtime": sha256(options.base_runtime),
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-appearance-") as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        checks = build(options.base_runtime, first, tables, hashes)
        build(options.base_runtime, second, tables, hashes)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic build: {first_hash} != {second_hash}"
            )
        shutil.copyfile(first, options.output)

    manifest = {
        "format_version": 1,
        "phase": "B5-native-appearance",
        "authority": ["game11_native", "x2game_confirmed"],
        "sources": hashes,
        "output": {
            "path": str(options.output),
            "sha256": sha256(options.output),
            **checks,
        },
        "tables": ranges,
        "deployment": {
            "deployable": False,
            "blocking": [
                "AA8 appearance request/result packets are not confirmed byte-for-byte",
                "appearance conversion mutation and rollback are not implemented",
            ],
        },
    }
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["output"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
