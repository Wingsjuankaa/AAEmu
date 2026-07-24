#!/usr/bin/env python3
"""Build the native AA8 item-conversion/smelting catalogue candidate.

The conversion graph is complete. Smelting probability vectors remain an
explicit blocker, so neither operation is enabled by this catalogue.
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
    "item_smelting_items": {
        "columns": "id display_prob item_grade_id item_smelting_id item_id".split(),
        "layout": ("68 " * 5).split(),
        "start": 0x80B44DD,
        "expected": 96,
        "loader": "x2game.dll FUN_39a82a80",
    },
    "item_smeltings": {
        "columns": (
            "id actability_limit amount gold item_set_id item_smelting_prob_id "
            "item_id skill_id"
        ).split(),
        "layout": ("68 " * 8).split(),
        "start": 0x80B4CC3,
        "expected": 32,
        "loader": "x2game.dll FUN_39a82d30",
    },
    "item_conv_reagents": {
        "columns": "id grade_id item_conv_rpack_id item_id max_grade_id".split(),
        "layout": ("68 " * 5).split(),
        "start": 0x80BA2C4,
        "expected": 34822,
        "loader": "x2game.dll FUN_39a84470",
    },
    "item_conv_reagent_filters": {
        "columns": (
            "id item_conv_epack_id item_conv_rpack_id item_grade_id "
            "item_impl_id max_item_grade_id max_level min_level"
        ).split(),
        "layout": ("68 " * 8).split(),
        "start": 0x816CB48,
        "expected": 124,
        "loader": "x2game.dll FUN_39a84720",
    },
    "item_conv_rpack_members": {
        "columns": "id item_conv_rpack_id item_conv_id".split(),
        "layout": ("68 " * 3).split(),
        "start": 0x816DB4A,
        "expected": 5961,
        "loader": "x2game.dll FUN_39a84a10",
    },
    "item_conv_rpacks": {
        "columns": ["id"],
        "layout": ["68"],
        "start": 0x8180A05,
        "expected": 5774,
        "loader": "x2game.dll FUN_39a84c50",
    },
    "item_conv_exception_filters": {
        "columns": "id item_category_id item_conv_epack_id".split(),
        "layout": ("68 " * 3).split(),
        "start": 0x8187AD1,
        "expected": 1,
        "loader": "x2game.dll FUN_39a850a0",
    },
    "item_conv_epacks": {
        "columns": ["id"],
        "layout": ["68"],
        "start": 0x8187AE4,
        "expected": 1,
        "loader": "x2game.dll FUN_39a852e0",
    },
    "item_conv_products": {
        "columns": (
            "id item_conv_ppack_id item_grade_id item_id max min weight"
        ).split(),
        "layout": ("68 " * 7).split(),
        "start": 0x8187AEF,
        "expected": 5626,
        "loader": "x2game.dll FUN_39a85620",
    },
    "item_conv_ppack_members": {
        "columns": "id item_conv_ppack_id item_conv_id".split(),
        "layout": ("68 " * 3).split(),
        "start": 0x81AF847,
        "expected": 5842,
        "loader": "x2game.dll FUN_39a85930",
    },
    "item_conv_ppacks": {
        "columns": "id chance_rate".split(),
        "layout": ("68 " * 2).split(),
        "start": 0x81C20F7,
        "expected": 5630,
        "loader": "x2game.dll FUN_39a85b70",
    },
    "item_convs": {
        "columns": "id item_conv_set_id".split(),
        "layout": ("68 " * 2).split(),
        "start": 0x81CE6EB,
        "expected": 6384,
        "loader": "x2game.dll FUN_39a85ec0",
    },
    "item_conv_sets": {
        "columns": "id dialog_content dialog_title".split(),
        "layout": "68 78 78".split(),
        "start": 0x81DC761,
        "expected": 12,
        "loader": "x2game.dll FUN_39a02950",
    },
}

DDL = {
    "item_smelting_items": """
        CREATE TABLE item_smelting_items (
            id INTEGER PRIMARY KEY, display_prob INTEGER NOT NULL,
            item_grade_id INTEGER NOT NULL, item_smelting_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL
        )""",
    "item_smeltings": """
        CREATE TABLE item_smeltings (
            id INTEGER PRIMARY KEY, actability_limit INTEGER NOT NULL,
            amount INTEGER NOT NULL, gold INTEGER NOT NULL,
            item_set_id INTEGER NOT NULL, item_smelting_prob_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL, skill_id INTEGER NOT NULL
        )""",
    "item_conv_reagents": """
        CREATE TABLE item_conv_reagents (
            id INTEGER PRIMARY KEY, grade_id INTEGER NOT NULL,
            item_conv_rpack_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
            max_grade_id INTEGER NOT NULL
        )""",
    "item_conv_reagent_filters": """
        CREATE TABLE item_conv_reagent_filters (
            id INTEGER PRIMARY KEY, item_conv_epack_id INTEGER NOT NULL,
            item_conv_rpack_id INTEGER NOT NULL, item_grade_id INTEGER NOT NULL,
            item_impl_id INTEGER NOT NULL, max_item_grade_id INTEGER NOT NULL,
            max_level INTEGER NOT NULL, min_level INTEGER NOT NULL
        )""",
    "item_conv_rpack_members": """
        CREATE TABLE item_conv_rpack_members (
            id INTEGER PRIMARY KEY, item_conv_rpack_id INTEGER NOT NULL,
            item_conv_id INTEGER NOT NULL
        )""",
    "item_conv_rpacks": """
        CREATE TABLE item_conv_rpacks (id INTEGER PRIMARY KEY)""",
    "item_conv_exception_filters": """
        CREATE TABLE item_conv_exception_filters (
            id INTEGER PRIMARY KEY, item_category_id INTEGER NOT NULL,
            item_conv_epack_id INTEGER NOT NULL
        )""",
    "item_conv_epacks": """
        CREATE TABLE item_conv_epacks (id INTEGER PRIMARY KEY)""",
    "item_conv_products": """
        CREATE TABLE item_conv_products (
            id INTEGER PRIMARY KEY, item_conv_ppack_id INTEGER NOT NULL,
            item_grade_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
            max INTEGER NOT NULL, min INTEGER NOT NULL, weight INTEGER NOT NULL
        )""",
    "item_conv_ppack_members": """
        CREATE TABLE item_conv_ppack_members (
            id INTEGER PRIMARY KEY, item_conv_ppack_id INTEGER NOT NULL,
            item_conv_id INTEGER NOT NULL
        )""",
    "item_conv_ppacks": """
        CREATE TABLE item_conv_ppacks (
            id INTEGER PRIMARY KEY, chance_rate INTEGER NOT NULL
        )""",
    "item_convs": """
        CREATE TABLE item_convs (
            id INTEGER PRIMARY KEY, item_conv_set_id INTEGER NOT NULL
        )""",
    "item_conv_sets": """
        CREATE TABLE item_conv_sets (
            id INTEGER PRIMARY KEY, dialog_content TEXT NOT NULL,
            dialog_title TEXT NOT NULL
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
        "missing_reagent_rpacks": """
            SELECT COUNT(*) FROM item_conv_reagents r LEFT JOIN item_conv_rpacks p
              ON p.id=r.item_conv_rpack_id WHERE p.id IS NULL""",
        "missing_filter_rpacks": """
            SELECT COUNT(*) FROM item_conv_reagent_filters f
            LEFT JOIN item_conv_rpacks p ON p.id=f.item_conv_rpack_id
            WHERE f.item_conv_rpack_id>0 AND p.id IS NULL""",
        "missing_filter_epacks": """
            SELECT COUNT(*) FROM item_conv_reagent_filters f
            LEFT JOIN item_conv_epacks p ON p.id=f.item_conv_epack_id
            WHERE f.item_conv_epack_id>0 AND p.id IS NULL""",
        "missing_rpack_member_convs": """
            SELECT COUNT(*) FROM item_conv_rpack_members m
            LEFT JOIN item_convs c ON c.id=m.item_conv_id WHERE c.id IS NULL""",
        "missing_rpack_members": """
            SELECT COUNT(*) FROM item_conv_rpack_members m
            LEFT JOIN item_conv_rpacks p ON p.id=m.item_conv_rpack_id
            WHERE p.id IS NULL""",
        "missing_product_ppacks": """
            SELECT COUNT(*) FROM item_conv_products p
            LEFT JOIN item_conv_ppacks g ON g.id=p.item_conv_ppack_id
            WHERE g.id IS NULL""",
        "missing_ppack_member_convs": """
            SELECT COUNT(*) FROM item_conv_ppack_members m
            LEFT JOIN item_convs c ON c.id=m.item_conv_id WHERE c.id IS NULL""",
        "missing_ppack_members": """
            SELECT COUNT(*) FROM item_conv_ppack_members m
            LEFT JOIN item_conv_ppacks p ON p.id=m.item_conv_ppack_id
            WHERE p.id IS NULL""",
        "missing_conv_sets": """
            SELECT COUNT(*) FROM item_convs c LEFT JOIN item_conv_sets s
              ON s.id=c.item_conv_set_id
            WHERE c.item_conv_set_id>0 AND s.id IS NULL""",
        "reagent_items_absent_from_phase_a": """
            SELECT COUNT(*) FROM item_conv_reagents r LEFT JOIN items i
              ON i.id=r.item_id WHERE i.id IS NULL""",
        "product_items_absent_from_phase_a": """
            SELECT COUNT(*) FROM item_conv_products p LEFT JOIN items i
              ON i.id=p.item_id WHERE i.id IS NULL""",
        "smelting_items_absent_from_phase_a": """
            SELECT COUNT(*) FROM item_smelting_items s LEFT JOIN items i
              ON i.id=s.item_id WHERE i.id IS NULL""",
    }
    for key, query in queries.items():
        checks[key] = int(connection.execute(query).fetchone()[0])
    checks["unresolved_localized_strings"] = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM item_conv_sets
            WHERE dialog_content LIKE '<ref:%' OR dialog_title LIKE '<ref:%'
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
                    key=lambda row: tuple(str(row[column]) for column in columns),
                ),
            )
        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES ('phase','B6-native-salvaging'),
                   ('item_conversion_mutation','blocked-until-protocol-confirmed'),
                   ('smelting_mutation','blocked-probability-layout-pending')
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
    with tempfile.TemporaryDirectory(prefix="aa8-salvaging-") as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        checks = build(options.base_runtime, first, tables, hashes)
        build(options.base_runtime, second, tables, hashes)
        if sha256(first) != sha256(second):
            raise RuntimeError("Non-deterministic salvaging catalogue build")
        shutil.copyfile(first, options.output)

    manifest = {
        "format_version": 1,
        "phase": "B6-native-salvaging",
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
                "item_smelting_probs cached layout is not confirmed",
                "AA8 conversion/smelting request and result packets are not confirmed",
                "some localized cached string references still require resolution",
                "catalogue relations reference items absent from the Phase A subset",
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
