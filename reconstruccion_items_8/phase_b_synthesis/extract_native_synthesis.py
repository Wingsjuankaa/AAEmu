#!/usr/bin/env python3
"""Build the native AA8 synthesis/awakening catalogue candidate.

The rows below are decoded from Kakao 8.0 game11 cached SQLite results using
layouts confirmed in x2game.dll.  This script intentionally builds catalogue
data only; it does not enable any item mutation path.
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
    "item_rnd_attr_unit_modifier_group_sets": {
        "columns": (
            "id inherit_priority_id item_rnd_attr_category_id name pick_num weight"
        ).split(),
        "layout": "68 68 68 78 68 68".split(),
        "start": 0x5891573,
        "expected": 459,
        "first_string_reference": 247064,
        "loader": "x2game.dll FUN_39945d20",
    },
    "item_rnd_attr_unit_modifier_groups": {
        "columns": (
            "id fixed_attr item_rnd_attr_unit_modifier_group_set_id "
            "unit_attribute_id unit_modifier_type_id weight"
        ).split(),
        "layout": "68 38 68 68 68 68".split(),
        "start": 0x587D7F9,
        "expected": 3694,
        "loader": "x2game.dll FUN_39945930",
    },
    "item_rnd_attr_unit_modifiers": {
        "columns": "id grade_id group_id max min".split(),
        "layout": "68 68 68 68 68".split(),
        "start": 0x57874A5,
        "expected": 48022,
        "loader": "x2game.dll FUN_39945680",
    },
    "item_rnd_attr_category_properties": {
        "columns": (
            "id bonus_exp_chance bonus_exp_max bonus_exp_min gain_exp gold_mul "
            "grade_id grade_exp item_rnd_attr_category_id max_element_level "
            "max_unit_modifier_num"
        ).split(),
        "layout": ("68 " * 11).split(),
        "start": 0x5897B22,
        "expected": 10088,
        "loader": "x2game.dll FUN_39946120",
    },
    "item_rnd_attr_category_elements": {
        "columns": (
            "id consume_lp item_rnd_attr_category_id level req_exp tax"
        ).split(),
        "layout": ("68 " * 6).split(),
        "start": 0x5906870,
        "expected": 298,
        "loader": "x2game.dll FUN_39946430",
    },
    "item_rnd_attr_categories": {
        "columns": (
            "id currency_id desc item_rnd_attr_category_group_id "
            "material_grade_limit max_evolving_grade message_grade "
            "re_roll_item_set_id"
        ).split(),
        "layout": "68 68 78 68 68 68 68 68".split(),
        "start": 0x5908590,
        "expected": 776,
        # 645 localized duplicate rows agree on this base.
        "first_string_reference": 247474,
        "loader": "x2game.dll FUN_39946710",
    },
    "item_rnd_attr_category_groups": {
        "columns": "id name".split(),
        "layout": "68 78".split(),
        "start": 0x59100F8,
        "expected": 38,
        "loader": "x2game.dll FUN_39947430",
    },
    "item_rnd_attr_category_relations": {
        "columns": "id item_rnd_attr_category_group_id material_id".split(),
        "layout": "68 68 68".split(),
        "start": 0x647CF58,
        "expected": 142,
        "loader": "x2game.dll FUN_39945440",
    },
    "item_evolving_materials": {
        "columns": "item_id item_rnd_attr_category_id show_exp".split(),
        "layout": "68 68 38".split(),
        "start": 0x567C309,
        "expected": 74,
        "loader": "x2game.dll FUN_39a216a0",
    },
    "item_change_mapping_groups": {
        "columns": (
            "id disable evolving_exp_inherit fail_bonus name selectable success"
        ).split(),
        "layout": "68 68 38 68 78 38 68".split(),
        "start": 0x83D7E87,
        "expected": 285,
        "loader": "x2game.dll FUN_39a17540",
    },
    "item_change_mappings": {
        "columns": (
            "id mapping_group_id source_grade_id source_item_id "
            "target_grade_id target_item_id"
        ).split(),
        "layout": ("68 " * 6).split(),
        "start": 0x83A438D,
        "expected": 8468,
        "loader": "x2game.dll FUN_39a08c90",
    },
}


DDL = {
    "item_rnd_attr_unit_modifier_group_sets": """
        CREATE TABLE item_rnd_attr_unit_modifier_group_sets (
            id INTEGER PRIMARY KEY, inherit_priority_id INTEGER NOT NULL,
            item_rnd_attr_category_id INTEGER NOT NULL, name TEXT NOT NULL,
            pick_num INTEGER NOT NULL, weight INTEGER NOT NULL
        )""",
    "item_rnd_attr_unit_modifier_groups": """
        CREATE TABLE item_rnd_attr_unit_modifier_groups (
            id INTEGER PRIMARY KEY, fixed_attr INTEGER NOT NULL,
            item_rnd_attr_unit_modifier_group_set_id INTEGER NOT NULL,
            unit_attribute_id INTEGER NOT NULL,
            unit_modifier_type_id INTEGER NOT NULL, weight INTEGER NOT NULL
        )""",
    "item_rnd_attr_unit_modifiers": """
        CREATE TABLE item_rnd_attr_unit_modifiers (
            id INTEGER PRIMARY KEY, grade_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL, max INTEGER NOT NULL, min INTEGER NOT NULL
        )""",
    "item_rnd_attr_category_properties": """
        CREATE TABLE item_rnd_attr_category_properties (
            id INTEGER PRIMARY KEY, bonus_exp_chance INTEGER NOT NULL,
            bonus_exp_max INTEGER NOT NULL, bonus_exp_min INTEGER NOT NULL,
            gain_exp INTEGER NOT NULL, gold_mul INTEGER NOT NULL,
            grade_id INTEGER NOT NULL, grade_exp INTEGER NOT NULL,
            item_rnd_attr_category_id INTEGER NOT NULL,
            max_element_level INTEGER NOT NULL,
            max_unit_modifier_num INTEGER NOT NULL
        )""",
    "item_rnd_attr_category_elements": """
        CREATE TABLE item_rnd_attr_category_elements (
            id INTEGER PRIMARY KEY, consume_lp INTEGER NOT NULL,
            item_rnd_attr_category_id INTEGER NOT NULL, level INTEGER NOT NULL,
            req_exp INTEGER NOT NULL, tax INTEGER NOT NULL
        )""",
    "item_rnd_attr_categories": """
        CREATE TABLE item_rnd_attr_categories (
            id INTEGER PRIMARY KEY, currency_id INTEGER NOT NULL,
            desc TEXT NOT NULL, item_rnd_attr_category_group_id INTEGER NOT NULL,
            material_grade_limit INTEGER NOT NULL,
            max_evolving_grade INTEGER NOT NULL, message_grade INTEGER NOT NULL,
            re_roll_item_set_id INTEGER NOT NULL
        )""",
    "item_rnd_attr_category_groups": """
        CREATE TABLE item_rnd_attr_category_groups (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL
        )""",
    "item_rnd_attr_category_relations": """
        CREATE TABLE item_rnd_attr_category_relations (
            id INTEGER PRIMARY KEY,
            item_rnd_attr_category_group_id INTEGER NOT NULL,
            material_id INTEGER NOT NULL
        )""",
    "item_evolving_materials": """
        CREATE TABLE item_evolving_materials (
            item_id INTEGER PRIMARY KEY,
            item_rnd_attr_category_id INTEGER NOT NULL,
            show_exp INTEGER NOT NULL
        )""",
    "item_change_mapping_groups": """
        CREATE TABLE item_change_mapping_groups (
            id INTEGER PRIMARY KEY, disable INTEGER NOT NULL,
            evolving_exp_inherit INTEGER NOT NULL, fail_bonus INTEGER NOT NULL,
            name TEXT NOT NULL, selectable INTEGER NOT NULL,
            success INTEGER NOT NULL
        )""",
    "item_change_mappings": """
        CREATE TABLE item_change_mappings (
            id INTEGER PRIMARY KEY, mapping_group_id INTEGER NOT NULL,
            source_grade_id INTEGER NOT NULL, source_item_id INTEGER NOT NULL,
            target_grade_id INTEGER NOT NULL, target_item_id INTEGER NOT NULL
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
    extracted: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, Any] = {}
    for name, spec in TABLES.items():
        raw, end = parser.read_cached_result(
            reader, spec["start"], spec["layout"]
        )
        if len(raw) != spec["expected"]:
            raise RuntimeError(
                f"{name}: expected {spec['expected']} rows, got {len(raw)}"
            )
        extracted[name] = [
            dict(zip(spec["columns"], row, strict=True)) for row in raw
        ]
        ranges[name] = {
            "start": spec["start"],
            "end": end,
            "rows": len(raw),
            "loader": spec["loader"],
        }
    return extracted, ranges


def validate_graph(connection: sqlite3.Connection) -> dict[str, int | str]:
    checks: dict[str, int | str] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0],
    }
    queries = {
        "missing_modifier_group_sets": """
            SELECT COUNT(*) FROM item_rnd_attr_unit_modifier_groups g
            LEFT JOIN item_rnd_attr_unit_modifier_group_sets s
              ON s.id=g.item_rnd_attr_unit_modifier_group_set_id
            WHERE s.id IS NULL""",
        "missing_modifier_groups": """
            SELECT COUNT(*) FROM item_rnd_attr_unit_modifiers m
            LEFT JOIN item_rnd_attr_unit_modifier_groups g ON g.id=m.group_id
            WHERE g.id IS NULL""",
        "missing_property_categories": """
            SELECT COUNT(*) FROM item_rnd_attr_category_properties p
            LEFT JOIN item_rnd_attr_categories c
              ON c.id=p.item_rnd_attr_category_id
            WHERE c.id IS NULL""",
        "missing_element_categories": """
            SELECT COUNT(*) FROM item_rnd_attr_category_elements e
            LEFT JOIN item_rnd_attr_categories c
              ON c.id=e.item_rnd_attr_category_id
            WHERE c.id IS NULL""",
        "missing_mapping_groups": """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN item_change_mapping_groups g ON g.id=m.mapping_group_id
            WHERE g.id IS NULL""",
        "missing_mapping_source_items": """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN items i ON i.id=m.source_item_id WHERE i.id IS NULL""",
        "missing_mapping_target_items": """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN items i ON i.id=m.target_item_id WHERE i.id IS NULL""",
        "missing_evolving_items": """
            SELECT COUNT(*) FROM item_evolving_materials e
            LEFT JOIN items i ON i.id=e.item_id WHERE i.id IS NULL""",
        "missing_relation_materials": """
            SELECT COUNT(*) FROM item_rnd_attr_category_relations r
            LEFT JOIN items i ON i.id=r.material_id WHERE i.id IS NULL""",
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
        for name in TABLES:
            connection.execute(f"DROP TABLE IF EXISTS {name}")
            connection.execute(DDL[name])
            columns = TABLES[name]["columns"]
            placeholders = ",".join(f":{column}" for column in columns)
            connection.executemany(
                f"INSERT INTO {name} ({','.join(columns)}) VALUES ({placeholders})",
                sorted(tables[name], key=lambda row: tuple(row.values())),
            )
        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES ('phase','B3-native-synthesis-awakening'),
                   ('synthesis_mutation','blocked-until-protocol-confirmed'),
                   ('awakening_mutation','blocked-until-protocol-confirmed')
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
        return validate_graph(connection)
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
    with tempfile.TemporaryDirectory(prefix="aa8-synthesis-") as temp:
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

    missing_catalogue_items = sum(
        int(checks[key])
        for key in (
            "missing_mapping_source_items",
            "missing_mapping_target_items",
            "missing_evolving_items",
            "missing_relation_materials",
        )
    )
    manifest = {
        "format_version": 1,
        "phase": "B3-native-synthesis-awakening",
        "authority": ["game11_native", "x2game_confirmed"],
        "sources": hashes,
        "output": {
            "path": str(options.output),
            "sha256": sha256(options.output),
            **checks,
        },
        "tables": ranges,
        "coverage": {
            "graph_internal_orphans": sum(
                int(checks[key])
                for key in (
                    "missing_modifier_group_sets",
                    "missing_modifier_groups",
                    "missing_property_categories",
                    "missing_element_categories",
                    "missing_mapping_groups",
                )
            ),
            "relations_to_items_absent_from_phase_a_catalogue": (
                missing_catalogue_items
            ),
        },
        "deployment": {
            "deployable": False,
            "blocking": [
                "AA8 synthesis request/result protocol is not confirmed byte-for-byte",
                "AA8 awakening reagent, currency, failure and bonus paths are not confirmed",
                "catalogue relations reference items absent from the current Phase A item subset",
            ],
        },
    }
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["output"], indent=2))
    print(
        "rows: "
        + ", ".join(f"{name}={len(rows)}" for name, rows in tables.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
