#!/usr/bin/env python3
"""Extract the AA8 socket/lunagem catalogue and build a candidate runtime.

Only client-confirmed rows are written.  The Kakao 8.0 game11 cache contains
the short item_socket_chances query (id, fail_break, cost_ratio), not the
server-side socket0..socket9 probabilities.  Those columns are therefore
created as NULL and their dependent socket definitions remain blocked.
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


def load_cache_parser():
    spec = importlib.util.spec_from_file_location("aa8_cached_result", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


TABLES: dict[str, dict[str, Any]] = {
    "item_enchanting_gems": {
        "columns": (
            "id item_id buff_modifier_tooltip eiset_id equip_item_tag_id "
            "equip_item_id equip_level equip_slot_group_id gem_visual_effect_id "
            "ignore_equip_item_tag item_grade_id skill_modifier_tooltip"
        ).split(),
        "layout": "68 68 78 68 68 68 68 68 68 38 68 78".split(),
        "anchor_id": 252,
        "anchor": {"item_id": 29643},
        "expected": 484,
        "layout_source": "x2game.dll FUN_39a3e7d0",
    },
    "item_sockets": {
        "columns": (
            "id item_id buff_modifier_tooltip eiset_id equip_item_tag_id "
            "equip_item_id equip_slot_group_id extractable ignore_equip_item_tag "
            "item_socket_chance_id skill_modifier_tooltip"
        ).split(),
        "layout": "68 68 78 68 68 68 68 38 38 68 78".split(),
        "anchor_id": 2,
        "anchor": {"item_id": 29882},
        "expected": 783,
        "layout_source": "x2game.dll FUN_39a3ebb0",
    },
    "item_socket_level_limits": {
        "columns": "item_id level".split(),
        "layout": "68 68".split(),
        "anchor_id": 30907,
        "anchor": {"level": 0},
        "expected": 762,
        "layout_source": "x2game.dll FUN_39898d30",
    },
    "item_socket_num_limits": {
        "columns": "slot_id grade_id num_socket".split(),
        "layout": "68 68 68".split(),
        "start": 0x8CE27A4,
        "expected": 403,
        "layout_source": "x2game.dll FUN_398e0250",
    },
    "gem_visual_effects": {
        "columns": "id filename".split(),
        "layout": "68 78".split(),
        "anchor_id": 1,
        "anchor": {
            "filename": "abillity_skill_table_m.magic.lightning_magic_hit"
        },
        "expected": 26,
        "layout_source": "x2game.dll FUN_39966520",
    },
    "item_socket_chances_short": {
        "columns": "id fail_break cost_ratio".split(),
        "layout": "68 38 68".split(),
        "start": 0x8CDCEB5,
        "expected": 8,
        "layout_source": "x2game.dll FUN_398d9da0 short-query branch",
    },
    "item_socket_changes": {
        "columns": "id enchant_item_id source_item_id target_item_id".split(),
        "layout": "68 68 68 68".split(),
        "start": 0x649B396,
        "expected": 27,
        "layout_source": "x2game.dll FUN_39a08fa0",
    },
}


DDL = {
    "item_enchanting_gems": """
        CREATE TABLE item_enchanting_gems (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            buff_modifier_tooltip TEXT NOT NULL,
            eiset_id INTEGER NOT NULL,
            equip_item_tag_id INTEGER NOT NULL,
            equip_item_id INTEGER NOT NULL,
            equip_level INTEGER NOT NULL,
            equip_slot_group_id INTEGER NOT NULL,
            gem_visual_effect_id INTEGER NOT NULL,
            ignore_equip_item_tag INTEGER NOT NULL,
            item_grade_id INTEGER NOT NULL,
            skill_modifier_tooltip TEXT NOT NULL
        )
    """,
    "item_sockets": """
        CREATE TABLE item_sockets (
            id INTEGER PRIMARY KEY,
            item_id INTEGER NOT NULL,
            buff_modifier_tooltip TEXT NOT NULL,
            eiset_id INTEGER NOT NULL,
            equip_item_tag_id INTEGER NOT NULL,
            equip_item_id INTEGER NOT NULL,
            equip_slot_group_id INTEGER NOT NULL,
            extractable INTEGER NOT NULL,
            ignore_equip_item_tag INTEGER NOT NULL,
            item_socket_chance_id INTEGER NOT NULL,
            skill_modifier_tooltip TEXT NOT NULL
        )
    """,
    "item_socket_level_limits": """
        CREATE TABLE item_socket_level_limits (
            item_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL
        )
    """,
    "item_socket_num_limits": """
        CREATE TABLE item_socket_num_limits (
            slot_id INTEGER NOT NULL,
            grade_id INTEGER NOT NULL,
            num_socket INTEGER NOT NULL,
            PRIMARY KEY (slot_id, grade_id)
        )
    """,
    "gem_visual_effects": """
        CREATE TABLE gem_visual_effects (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL
        )
    """,
    "item_socket_chances": """
        CREATE TABLE item_socket_chances (
            id INTEGER PRIMARY KEY,
            fail_break INTEGER NOT NULL,
            cost_ratio INTEGER NOT NULL,
            socket0 INTEGER,
            socket1 INTEGER,
            socket2 INTEGER,
            socket3 INTEGER,
            socket4 INTEGER,
            socket5 INTEGER,
            socket6 INTEGER,
            socket7 INTEGER,
            socket8 INTEGER,
            socket9 INTEGER
        )
    """,
    "item_socket_changes": """
        CREATE TABLE item_socket_changes (
            id INTEGER PRIMARY KEY,
            enchant_item_id INTEGER NOT NULL,
            source_item_id INTEGER NOT NULL,
            target_item_id INTEGER NOT NULL
        )
    """,
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
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


def extract_rows(game11: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    parser = load_cache_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    extracted: dict[str, list[dict[str, Any]]] = {}
    ranges: dict[str, Any] = {}

    for name, spec in TABLES.items():
        if "start" in spec:
            raw, end = parser.read_cached_result(reader, spec["start"], spec["layout"])
            rows = [dict(zip(spec["columns"], values)) for values in raw]
            source_range = {
                "start": spec["start"],
                "end": end,
                "rows": len(rows),
            }
        else:
            rows, source_range = parser.locate_cached_result(
                reader,
                spec["columns"],
                spec["layout"],
                spec["anchor_id"],
                spec["anchor"],
            )
        if len(rows) != spec["expected"]:
            raise RuntimeError(
                f"{name}: expected {spec['expected']} rows, got {len(rows)}"
            )
        extracted[name] = rows
        ranges[name] = source_range

    return extracted, ranges


def client_item_ids(path: Path) -> set[int]:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        connection.execute("PRAGMA query_only = ON")
        return {int(row[0]) for row in connection.execute("SELECT id FROM items")}
    finally:
        connection.close()


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    placeholders = ",".join("?" for _ in columns)
    names = ",".join(columns)
    values = [tuple(row[column] for column in columns) for row in rows]
    connection.executemany(
        f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
        values,
    )


def build_runtime(
    base_runtime: Path,
    destination: Path,
    extracted: dict[str, list[dict[str, Any]]],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    shutil.copyfile(base_runtime, destination)
    connection = sqlite3.connect(destination)
    try:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("BEGIN IMMEDIATE")
        for table in (
            "item_enchanting_gems",
            "item_sockets",
            "item_socket_level_limits",
            "item_socket_num_limits",
            "gem_visual_effects",
            "item_socket_chances",
            "item_socket_changes",
        ):
            connection.execute(f"DROP TABLE IF EXISTS {table}")
            connection.execute(DDL[table])

        for table in (
            "item_enchanting_gems",
            "item_sockets",
            "item_socket_level_limits",
            "item_socket_num_limits",
            "gem_visual_effects",
            "item_socket_changes",
        ):
            insert_rows(
                connection,
                table,
                TABLES[table]["columns"],
                sorted(
                    extracted[table],
                    key=lambda row: tuple(row[column] for column in TABLES[table]["columns"]),
                ),
            )

        chance_columns = TABLES["item_socket_chances_short"]["columns"]
        chance_rows = []
        for row in extracted["item_socket_chances_short"]:
            chance_rows.append(
                {
                    **row,
                    **{f"socket{index}": None for index in range(10)},
                }
            )
        insert_rows(
            connection,
            "item_socket_chances",
            chance_columns + [f"socket{index}" for index in range(10)],
            chance_rows,
        )

        coverage_rows = [
            (
                int(row["item_id"]),
                "enchanting_gem",
                "complete",
                "",
                "client_compact_8+game11_native+x2game_confirmed",
            )
            for row in extracted["item_enchanting_gems"]
        ]
        coverage_rows.extend(
            (
                int(row["item_id"]),
                "socket",
                "complete",
                "",
                "client_compact_8+game11_native+x2game_confirmed",
            )
            for row in extracted["item_sockets"]
        )
        connection.executemany(
            """
            INSERT INTO aaemu_item_definition_coverage
                (item_id, concrete_type, coverage, missing_dependencies, provenance)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                concrete_type = excluded.concrete_type,
                coverage = excluded.coverage,
                missing_dependencies = excluded.missing_dependencies,
                provenance = excluded.provenance
            """,
            sorted(coverage_rows),
        )

        connection.execute("DROP TABLE IF EXISTS aaemu_item_phase_b_metadata")
        connection.execute(
            """
            CREATE TABLE aaemu_item_phase_b_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        metadata = {
            "phase": "B1-sockets-lunagems",
            "authority": "AA8-only",
            "socket_probability_status": "blocked:not_present_in_game11_short_query",
            "packet": (
                "SCSocketingResultPacket 0x279:"
                "byte result,uint64 itemId,uint32 itemTemplateId,"
                "byte operation,bool success"
            ),
            "magical_packet": (
                "SCEnchantMagicalResultPacket 0x2ed:"
                "bool result,uint64 itemId,uint32 itemTemplateId"
            ),
            **{f"sha256_{key}": value for key, value in source_hashes.items()},
        }
        connection.executemany(
            "INSERT INTO aaemu_item_phase_b_metadata (key,value) VALUES (?,?)",
            sorted(metadata.items()),
        )
        connection.commit()
        connection.execute("VACUUM")
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        return {"quick_check": quick, "integrity_check": integrity}
    finally:
        connection.close()


def main() -> int:
    options = arguments()
    extracted, ranges = extract_rows(options.game11)
    known_items = client_item_ids(options.client_compact)
    chance_ids = {int(row["id"]) for row in extracted["item_socket_chances_short"]}
    referenced_chances = {
        int(row["item_socket_chance_id"])
        for row in extracted["item_sockets"]
        if int(row["item_socket_chance_id"]) != 0
    }
    missing_chances = sorted(referenced_chances - chance_ids)

    source_hashes = {
        "game11": sha256(options.game11),
        "client_compact": sha256(options.client_compact),
        "base_runtime": sha256(options.base_runtime),
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aa8-sockets-") as temp_dir:
        first = Path(temp_dir) / "first.sqlite3"
        second = Path(temp_dir) / "second.sqlite3"
        checks = build_runtime(options.base_runtime, first, extracted, source_hashes)
        build_runtime(options.base_runtime, second, extracted, source_hashes)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic runtime: {first_hash} != {second_hash}"
            )
        shutil.copyfile(first, options.output)

    manifest = {
        "format_version": 1,
        "phase": "B1-sockets-lunagems",
        "authority": [
            "client_compact_8",
            "game11_native",
            "x2game_confirmed",
        ],
        "sources": source_hashes,
        "output": {
            "path": str(options.output),
            "sha256": sha256(options.output),
            **checks,
        },
        "tables": {
            name: {
                "rows": len(rows),
                "range": ranges[name],
                "layout_source": TABLES[name]["layout_source"],
            }
            for name, rows in extracted.items()
        },
        "closure": {
            "enchanting_gem_items_missing_from_client_items": sorted(
                int(row["item_id"])
                for row in extracted["item_enchanting_gems"]
                if int(row["item_id"]) not in known_items
            ),
            "socket_items_missing_from_client_items": sorted(
                int(row["item_id"])
                for row in extracted["item_sockets"]
                if int(row["item_id"]) not in known_items
            ),
            "referenced_socket_chance_ids": sorted(referenced_chances),
            "available_short_socket_chance_ids": sorted(chance_ids),
            "missing_socket_chance_ids": missing_chances,
        },
        "protocol": {
            "opcode": "0x279",
            "name": "SCSocketingResultPacket",
            "fields": [
                "byte result",
                "uint64 itemId",
                "uint32 itemTemplateId",
                "byte operation",
                "bool success",
            ],
            "evidence": [
                "x2game.dll FUN_39988cc0",
                "x2game.dll handler FUN_39301ac0",
            ],
            "operation_semantics": "0=remove,1=install",
            "magical_enchant": {
                "opcode": "0x2ED",
                "name": "SCEnchantMagicalResultPacket",
                "fields": [
                    "bool result",
                    "uint64 itemId",
                    "uint32 itemTemplateId",
                ],
                "evidence": [
                    "x2game.dll FUN_39988dc0",
                    "x2game.dll handler FUN_39301ca0",
                ],
            },
        },
        "deployment": {
            "deployable": False,
            "blocking": [
                "socket0..socket9 probabilities are absent from the game11 short query",
                "lunagem success/failure mutation is intentionally gated",
            ],
            "active_slice": "guaranteed enchanting gems",
        },
    }
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["output"], indent=2))
    print(
        "rows:",
        ", ".join(f"{name}={len(rows)}" for name, rows in extracted.items()),
    )
    print("missing_socket_chance_ids:", missing_chances)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
