#!/usr/bin/env python3
"""Build the AA8 native temper/enchant-scale runtime candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"

RATIO_COLUMNS = (
    "id break_ratio cost currency_id disable_ratio down_max down_ratio "
    "grate_success_ratio name scale success_ratio"
).split()
RATIO_LAYOUT = ("68 " * 8 + "78 " + "68 " * 2).split()
RATIO_START = 0x84270F6
RATIO_COUNT = 31

FORBID_COLUMNS = "id item_id name".split()
FORBID_LAYOUT = "68 68 78".split()
FORBID_START = 0x568A829
FORBID_COUNT = 37


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
    ratios, ratio_end = parser.read_cached_result(
        reader, RATIO_START, RATIO_LAYOUT
    )
    forbids, forbid_end = parser.read_cached_result(
        reader, FORBID_START, FORBID_LAYOUT
    )
    if len(ratios) != RATIO_COUNT:
        raise RuntimeError(f"Expected {RATIO_COUNT} ratios, got {len(ratios)}")
    if len(forbids) != FORBID_COUNT:
        raise RuntimeError(f"Expected {FORBID_COUNT} forbids, got {len(forbids)}")
    return (
        [dict(zip(RATIO_COLUMNS, row)) for row in ratios],
        [dict(zip(FORBID_COLUMNS, row)) for row in forbids],
        {
            "enchant_scale_ratios": {
                "start": RATIO_START,
                "end": ratio_end,
                "rows": len(ratios),
                "loader": "x2game.dll FUN_39a0fe30",
            },
            "item_cap_scale_forbids": {
                "start": FORBID_START,
                "end": forbid_end,
                "rows": len(forbids),
                "loader": "x2game.dll FUN_39a0fba0",
            },
        },
    )


def build(base: Path, output: Path, ratios, forbids, hashes):
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE IF EXISTS enchant_scale_ratios")
        connection.execute(
            """
            CREATE TABLE enchant_scale_ratios (
                id INTEGER PRIMARY KEY,
                break_ratio INTEGER NOT NULL,
                cost INTEGER NOT NULL,
                currency_id INTEGER NOT NULL,
                disable_ratio INTEGER NOT NULL,
                down_max INTEGER NOT NULL,
                down_ratio INTEGER NOT NULL,
                grate_success_ratio INTEGER NOT NULL,
                name TEXT NOT NULL,
                scale INTEGER NOT NULL,
                success_ratio INTEGER NOT NULL
            )
            """
        )
        connection.execute("DROP TABLE IF EXISTS item_cap_scale_forbids")
        connection.execute(
            """
            CREATE TABLE item_cap_scale_forbids (
                id INTEGER PRIMARY KEY,
                item_id INTEGER NOT NULL,
                name TEXT NOT NULL
            )
            """
        )
        connection.executemany(
            """
            INSERT INTO enchant_scale_ratios
            (id,break_ratio,cost,currency_id,disable_ratio,down_max,down_ratio,
             grate_success_ratio,name,scale,success_ratio)
            VALUES (:id,:break_ratio,:cost,:currency_id,:disable_ratio,:down_max,
                    :down_ratio,:grate_success_ratio,:name,:scale,:success_ratio)
            """,
            sorted(ratios, key=lambda row: row["id"]),
        )
        connection.executemany(
            """
            INSERT INTO item_cap_scale_forbids (id,item_id,name)
            VALUES (:id,:item_id,:name)
            """,
            sorted(forbids, key=lambda row: row["id"]),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES ('phase','B2-native-temper'),
                   ('temper_state_field','ScaledA'),
                   ('temper_scale_formula','1 + enchant_scale_ratios.scale / 1000')
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
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        missing_caps = connection.execute(
            """
            SELECT COUNT(*) FROM items
            WHERE max_enchant_scale_id > 0
              AND max_enchant_scale_id NOT IN (SELECT id FROM enchant_scale_ratios)
            """
        ).fetchone()[0]
        return {
            "quick_check": quick,
            "integrity_check": integrity,
            "missing_item_caps": missing_caps,
        }
    finally:
        connection.close()


def main() -> int:
    options = arguments()
    ratios, forbids, ranges = extract(options.game11)
    hashes = {
        "game11": sha256(options.game11),
        "base_runtime": sha256(options.base_runtime),
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-temper-") as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        checks = build(options.base_runtime, first, ratios, forbids, hashes)
        build(options.base_runtime, second, ratios, forbids, hashes)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(f"Non-deterministic build: {first_hash} != {second_hash}")
        shutil.copyfile(first, options.output)

    manifest = {
        "format_version": 1,
        "phase": "B2-native-temper",
        "authority": ["game11_native", "x2game_confirmed"],
        "sources": hashes,
        "output": {
            "path": str(options.output),
            "sha256": sha256(options.output),
            **checks,
        },
        "tables": ranges,
        "state": {
            "wire_field": "ScaledA",
            "legacy_fields_prohibited": ["TemperPhysical", "TemperMagical"],
            "multiplier": "1 + scale / 1000",
            "max_level_source": "items.max_enchant_scale_id",
        },
        "deployment": {
            "deployable": False,
            "blocking": [
                "AA8 reagent and currency consumption path is not confirmed",
                "AA8 success/great-success/down outcome packet is not confirmed",
            ],
        },
    }
    options.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["output"], indent=2))
    print(f"rows: enchant_scale_ratios={len(ratios)}, item_cap_scale_forbids={len(forbids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
