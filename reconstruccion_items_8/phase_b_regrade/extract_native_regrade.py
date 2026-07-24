#!/usr/bin/env python3
"""Build the native AA8 regrade catalogue candidate.

All cached-result layouts and ranges in this file were confirmed against the
loaders and embedded SQL in Kakao 8.0 x2game.dll. The resulting catalogue is
read-only: it deliberately does not enable the economic mutation.
"""

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
    "item_enchant_ratio_groups": {
        "columns": "id item_impl_id item_enchant_ratio_kind_id".split(),
        "layout": ("68 " * 3).split(),
        "start": 0x8D5C1DA,
        "expected": 6,
        "loader": "x2game.dll item_enchant_ratio_groups loader",
    },
    "item_enchant_ratios": {
        "columns": (
            "item_enchant_ratio_group_id grade success great break downgrade "
            "cost downgrade_min downgrade_max currency_id disable"
        ).split(),
        "layout": ("68 " * 11).split(),
        "start": 0x8D5C229,
        "expected": 78,
        "loader": "x2game.dll item_enchant_ratios loader",
    },
    "item_enchant_ratio_items": {
        "columns": "item_enchant_ratio_group_id item_id".split(),
        "layout": ("68 " * 2).split(),
        "start": 0x8D5CFE0,
        "expected": 2114,
        "loader": "x2game.dll item_enchant_ratio_items loader",
    },
    "item_grade_enchanting_supports": {
        "columns": (
            "item_id add_break_mul add_break_ratio add_disable_mul "
            "add_disable_ratio add_downgrade_mul add_downgrade_ratio "
            "add_great_success_grade add_great_success_mul "
            "add_great_success_ratio add_success_mul add_success_ratio icons "
            "impl_flags req_scale_max_id req_scale_min_id require_grade_max "
            "require_grade_min"
        ).split(),
        "layout": ("68 " * 18).split(),
        "start": 0x57778A8,
        "expected": 99,
        "loader": "x2game.dll FUN_39a40950",
    },
}

DDL = {
    "item_enchant_ratio_groups": """
        CREATE TABLE item_enchant_ratio_groups (
            id INTEGER PRIMARY KEY, item_impl_id INTEGER NOT NULL,
            item_enchant_ratio_kind_id INTEGER NOT NULL
        )""",
    "item_enchant_ratios": """
        CREATE TABLE item_enchant_ratios (
            item_enchant_ratio_group_id INTEGER NOT NULL,
            grade INTEGER NOT NULL, success INTEGER NOT NULL,
            great INTEGER NOT NULL, break INTEGER NOT NULL,
            downgrade INTEGER NOT NULL, cost INTEGER NOT NULL,
            downgrade_min INTEGER NOT NULL, downgrade_max INTEGER NOT NULL,
            currency_id INTEGER NOT NULL, disable INTEGER NOT NULL,
            PRIMARY KEY (item_enchant_ratio_group_id, grade)
        )""",
    "item_enchant_ratio_items": """
        CREATE TABLE item_enchant_ratio_items (
            item_enchant_ratio_group_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            PRIMARY KEY (item_enchant_ratio_group_id, item_id)
        )""",
    "item_grade_enchanting_supports": """
        CREATE TABLE item_grade_enchanting_supports (
            item_id INTEGER PRIMARY KEY,
            add_break_mul INTEGER NOT NULL, add_break_ratio INTEGER NOT NULL,
            add_disable_mul INTEGER NOT NULL, add_disable_ratio INTEGER NOT NULL,
            add_downgrade_mul INTEGER NOT NULL,
            add_downgrade_ratio INTEGER NOT NULL,
            add_great_success_grade INTEGER NOT NULL,
            add_great_success_mul INTEGER NOT NULL,
            add_great_success_ratio INTEGER NOT NULL,
            add_success_mul INTEGER NOT NULL, add_success_ratio INTEGER NOT NULL,
            icons INTEGER NOT NULL, impl_flags INTEGER NOT NULL,
            req_scale_max_id INTEGER NOT NULL, req_scale_min_id INTEGER NOT NULL,
            require_grade_max INTEGER NOT NULL,
            require_grade_min INTEGER NOT NULL
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
    queries = {
        "missing_ratio_groups": """
            SELECT COUNT(*) FROM item_enchant_ratios r
            LEFT JOIN item_enchant_ratio_groups g
              ON g.id=r.item_enchant_ratio_group_id
            WHERE g.id IS NULL""",
        "missing_ratio_item_groups": """
            SELECT COUNT(*) FROM item_enchant_ratio_items i
            LEFT JOIN item_enchant_ratio_groups g
              ON g.id=i.item_enchant_ratio_group_id
            WHERE g.id IS NULL""",
        "ratio_items_absent_from_phase_a": """
            SELECT COUNT(*) FROM item_enchant_ratio_items r
            LEFT JOIN items i ON i.id=r.item_id WHERE i.id IS NULL""",
        "supports_absent_from_phase_a": """
            SELECT COUNT(*) FROM item_grade_enchanting_supports s
            LEFT JOIN items i ON i.id=s.item_id WHERE i.id IS NULL""",
    }
    for key, query in queries.items():
        checks[key] = int(connection.execute(query).fetchone()[0])
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
            VALUES ('phase','B4-native-regrade'),
                   ('regrade_mutation','blocked-until-protocol-confirmed'),
                   ('break_rewards','blocked-layout-pending')
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
    with tempfile.TemporaryDirectory(prefix="aa8-regrade-") as temp:
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
        "phase": "B4-native-regrade",
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
                "AA8 regrade request/result transaction is not confirmed end-to-end",
                "AA8 failure break-reward category layout is still pending",
                "no economic mutation may use historical GradeTemplate ratios",
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
