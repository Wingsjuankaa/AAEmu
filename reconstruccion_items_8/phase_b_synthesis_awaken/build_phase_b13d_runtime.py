#!/usr/bin/env python3
"""Build the native AA8 Hiram infusion-wrapper runtime.

B13d restores the stackable wrapper -> graded evolving-material flow for the
three directly confirmed Hiram infusion tiers. Gameplay rows come from the
decrypted AA8 compact and game11. The loot-pack to distribution relation is a
documented server derivation: each wrapper's native visible grade band maps to
one unique native game11 distribution (60/30/10).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "reconstruccion_skills_8"
GRADE_DISTRIBUTION_START = 0x46AFDF7
GRADE_DISTRIBUTION_COUNT = 50
GRADE_COLUMNS = ["id", *[f"weight_{grade}" for grade in range(13)]]
GRADE_LAYOUT = ["68"] * len(GRADE_COLUMNS)

WRAPPERS = {
    45731: {
        "name": "Unidentified Hiram Infusion",
        "skill_id": 39052,
        "loot_pack_id": 12470,
        "distribution_id": 17,
        "grades": [2, 3, 4],
    },
    46023: {
        "name": "Mysterious Hiram Infusion",
        "skill_id": 39346,
        "loot_pack_id": 12532,
        "distribution_id": 23,
        "grades": [3, 4, 5],
    },
    47052: {
        "name": "Radiant Hiram Infusion",
        "skill_id": 40772,
        "loot_pack_id": 12759,
        "distribution_id": 47,
        "grades": [5, 6, 7],
    },
}
RESULT_ITEM_ID = 48825
ACTUAL_TYPES = {
    "<ref:75245>": "GainLootPackItemEffect",
    "<ref:75221>": "BuffEffect",
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


def extract_native_grade_distributions(game11: Path) -> list[dict[str, int]]:
    sys.path.insert(0, str(SKILLS_ROOT))
    from extract_battlerage_manifest import CachedResultReader, read_cached_result

    reader = CachedResultReader(game11.read_bytes())
    rows, end = read_cached_result(
        reader,
        GRADE_DISTRIBUTION_START,
        GRADE_LAYOUT,
    )
    if len(rows) != GRADE_DISTRIBUTION_COUNT or end != 0x46B0919:
        raise RuntimeError(
            f"Unexpected AA8 item_grade_distributions result: "
            f"rows={len(rows)} end=0x{end:X}"
        )
    result = [dict(zip(GRADE_COLUMNS, row)) for row in rows]
    if [row["id"] for row in result] != list(range(1, 51)):
        raise RuntimeError("AA8 item-grade distribution IDs are not 1..50")
    for row in result:
        total = sum(int(row[f"weight_{grade}"]) for grade in range(13))
        if total != 100:
            raise RuntimeError(
                f"AA8 item-grade distribution {row['id']} totals {total}, not 100"
            )
    return result


def query_rows(
    connection: sqlite3.Connection,
    table: str,
    ids: set[int],
) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in ids)
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {table} WHERE id IN ({placeholders})",
            sorted(ids),
        )
    ]


def extract_wrapper_closure(
    game11: Path,
    client_compact: Path,
) -> dict[str, list[dict[str, Any]]]:
    sys.path.insert(0, str(SKILLS_ROOT))
    from extract_battlerage_manifest import extract_client_relationships

    relationships = extract_client_relationships(game11)
    skill_ids = {int(wrapper["skill_id"]) for wrapper in WRAPPERS.values()}
    skill_effects = [
        {
            **dict(row),
            "end_level": 255
            if int(row.get("end_level") or 0) == 99
            else int(row.get("end_level") or 0),
        }
        for row in relationships["skill_effects"]
        if int(row["skill_id"]) in skill_ids
    ]
    effect_ids = {int(row["effect_id"]) for row in skill_effects}

    with sqlite3.connect(
        f"file:{client_compact.resolve().as_posix()}?mode=ro",
        uri=True,
    ) as connection:
        connection.row_factory = sqlite3.Row
        skills = query_rows(connection, "skills", skill_ids)
        effects = query_rows(connection, "effects", effect_ids)
        actual_ids = {int(row["actual_id"]) for row in effects}
        gain_loot_effects = query_rows(
            connection,
            "gain_loot_pack_item_effects",
            actual_ids,
        )

    for effect in effects:
        native_type = str(effect["actual_type"])
        if native_type not in ACTUAL_TYPES:
            raise RuntimeError(
                f"Unconfirmed AA8 effect type {native_type} for {effect['id']}"
            )
        effect["actual_type"] = ACTUAL_TYPES[native_type]

    buff_ids = {
        int(effect["actual_id"])
        for effect in effects
        if effect["actual_type"] == "BuffEffect"
    }
    buff_effects = [
        dict(row)
        for row in relationships["concrete_effects"]["buff_effects"]
        if int(row["id"]) in buff_ids
    ]
    expected_actual_ids = {
        int(effect["actual_id"])
        for effect in effects
        if effect["actual_type"] == "GainLootPackItemEffect"
    }
    if {int(row["id"]) for row in gain_loot_effects} != expected_actual_ids:
        raise RuntimeError("AA8 wrapper GainLootPackItemEffect closure is incomplete")
    if {int(row["id"]) for row in buff_effects} != buff_ids:
        raise RuntimeError("AA8 wrapper BuffEffect closure is incomplete")
    if len(skills) != len(skill_ids) or len(skill_effects) != len(skill_ids) * 2:
        raise RuntimeError("AA8 wrapper skill closure is incomplete")

    return {
        "skills": skills,
        "skill_effects": skill_effects,
        "effects": effects,
        "gain_loot_pack_item_effects": gain_loot_effects,
        "buff_effects": buff_effects,
    }


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    available = {
        row[1] for row in connection.execute(f"PRAGMA table_info({table})")
    }
    columns = [column for column in rows[0] if column in available]
    placeholders = ",".join(f":{column}" for column in columns)
    connection.executemany(
        f"""
        INSERT OR REPLACE INTO {table} ({','.join(columns)})
        VALUES ({placeholders})
        """,
        sorted(rows, key=lambda row: int(row["id"])),
    )


def replace_grade_distributions(
    connection: sqlite3.Connection,
    rows: list[dict[str, int]],
) -> None:
    connection.execute("DROP TABLE IF EXISTS item_grade_distributions")
    connection.execute(
        """
        CREATE TABLE item_grade_distributions (
            id INTEGER PRIMARY KEY,
            weight_0 INTEGER NOT NULL,
            weight_1 INTEGER NOT NULL,
            weight_2 INTEGER NOT NULL,
            weight_3 INTEGER NOT NULL,
            weight_4 INTEGER NOT NULL,
            weight_5 INTEGER NOT NULL,
            weight_6 INTEGER NOT NULL,
            weight_7 INTEGER NOT NULL,
            weight_8 INTEGER NOT NULL,
            weight_9 INTEGER NOT NULL,
            weight_10 INTEGER NOT NULL,
            weight_11 INTEGER NOT NULL,
            weight_12 INTEGER NOT NULL
        )
        """
    )
    insert_rows(connection, "item_grade_distributions", rows)


def insert_wrapper_loot(connection: sqlite3.Connection) -> None:
    for item_id, wrapper in sorted(WRAPPERS.items()):
        pack_id = int(wrapper["loot_pack_id"])
        distribution_id = int(wrapper["distribution_id"])
        row_id = 88_000_000 + pack_id
        connection.execute("DELETE FROM loots WHERE loot_pack_id=?", (pack_id,))
        connection.execute("DELETE FROM loot_groups WHERE pack_id=?", (pack_id,))
        connection.execute(
            """
            INSERT INTO loots (
                id, "group", item_id, drop_rate, min_amount, max_amount,
                loot_pack_id, grade_id, always_drop
            ) VALUES (?,1,?,10000000,1,1,?,0,'t')
            """,
            (row_id, RESULT_ITEM_ID, pack_id),
        )
        connection.execute(
            """
            INSERT INTO loot_groups (
                id, pack_id, group_no, drop_rate, item_grade_distribution_id
            ) VALUES (?,?,1,10000000,?)
            """,
            (row_id, pack_id, distribution_id),
        )
        connection.execute(
            """
            UPDATE aaemu_item_definition_coverage
            SET concrete_type='infusion_wrapper',
                coverage='complete',
                missing_dependencies='',
                provenance=?
            WHERE item_id=?
            """,
            (
                "client_compact_8+game11_native+x2game_confirmed+"
                "server_derived_pack_distribution_link",
                item_id,
            ),
        )


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check":
            connection.execute("PRAGMA integrity_check").fetchone()[0],
        "grade_distribution_count": connection.execute(
            "SELECT COUNT(*) FROM item_grade_distributions"
        ).fetchone()[0],
        "grade_distribution_weight12_column": connection.execute(
            """
            SELECT COUNT(*) FROM pragma_table_info('item_grade_distributions')
            WHERE name='weight_12'
            """
        ).fetchone()[0],
        "result_item_complete": connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_item_definition_coverage
            WHERE item_id=? AND concrete_type='evolving_material'
              AND coverage='complete' AND missing_dependencies=''
            """,
            (RESULT_ITEM_ID,),
        ).fetchone()[0],
    }
    for item_id, wrapper in sorted(WRAPPERS.items()):
        skill_id = int(wrapper["skill_id"])
        pack_id = int(wrapper["loot_pack_id"])
        distribution_id = int(wrapper["distribution_id"])
        grades = list(wrapper["grades"])
        checks[f"wrapper_{item_id}_closure"] = connection.execute(
            """
            SELECT COUNT(*)
            FROM items i
            JOIN aaemu_item_definition_coverage c ON c.item_id=i.id
            WHERE i.id=? AND i.use_skill_id=? AND c.coverage='complete'
              AND c.concrete_type='infusion_wrapper'
            """,
            (item_id, skill_id),
        ).fetchone()[0]
        checks[f"skill_{skill_id}_relations"] = connection.execute(
            "SELECT COUNT(*) FROM skill_effects WHERE skill_id=?",
            (skill_id,),
        ).fetchone()[0]
        checks[f"pack_{pack_id}_closure"] = connection.execute(
            """
            SELECT COUNT(*)
            FROM loot_groups g
            JOIN loots l ON l.loot_pack_id=g.pack_id
                         AND l."group"=g.group_no
            WHERE g.pack_id=? AND g.item_grade_distribution_id=?
              AND l.item_id=? AND l.min_amount=1 AND l.max_amount=1
            """,
            (pack_id, distribution_id, RESULT_ITEM_ID),
        ).fetchone()[0]
        weights = connection.execute(
            """
            SELECT weight_0,weight_1,weight_2,weight_3,weight_4,weight_5,
                   weight_6,weight_7,weight_8,weight_9,weight_10,weight_11,
                   weight_12
            FROM item_grade_distributions WHERE id=?
            """,
            (distribution_id,),
        ).fetchone()
        checks[f"distribution_{distribution_id}_bands"] = [
            grade for grade, weight in enumerate(weights) if int(weight) > 0
        ]
        if checks[f"distribution_{distribution_id}_bands"] != grades:
            raise RuntimeError(
                f"AA8 distribution {distribution_id} grade band mismatch"
            )
        if [int(weights[grade]) for grade in grades] != [60, 30, 10]:
            raise RuntimeError(
                f"AA8 distribution {distribution_id} weight mismatch"
            )
    return checks


def build(
    base: Path,
    output: Path,
    closure: dict[str, list[dict[str, Any]]],
    distributions: list[dict[str, int]],
) -> dict[str, Any]:
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("BEGIN IMMEDIATE")
        for table in (
            "skills",
            "effects",
            "skill_effects",
            "gain_loot_pack_item_effects",
            "buff_effects",
        ):
            insert_rows(connection, table, closure[table])
        replace_grade_distributions(connection, distributions)
        insert_wrapper_loot(connection)
        metadata = {
            "phase": "B13d-native-hiram-infusion-wrappers",
            "authority": "AA8 client compact/game11/x2game; no 3.0 rows",
            "implementation.infusion_wrappers":
                "45731:39052:12470:17,"
                "46023:39346:12532:23,"
                "47052:40772:12759:47",
            "implementation.infusion_result":
                "item 48825 ItemEvolvingMaterialDesc category 520",
            "implementation.grade_distributions":
                "50 native game11 rows, grades 0..12",
            "implementation.pack_distribution_link":
                "server_derived from exact native wrapper grade bands",
        }
        connection.executemany(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES (?,?)
            """,
            sorted(metadata.items()),
        )
        connection.commit()
        connection.execute("VACUUM")
        connection.commit()
        return validate(connection)
    finally:
        connection.close()


def main() -> None:
    args = arguments()
    closure = extract_wrapper_closure(args.game11, args.client_compact)
    distributions = extract_native_grade_distributions(args.game11)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aa8-b13d-") as directory:
        first = Path(directory) / "first.sqlite3"
        second = Path(directory) / "second.sqlite3"
        checks = build(
            args.base_runtime, first, closure, distributions
        )
        second_checks = build(
            args.base_runtime, second, closure, distributions
        )
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash or checks != second_checks:
            raise RuntimeError("B13d build is not deterministic")
        if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
            raise RuntimeError(f"B13d SQLite validation failed: {checks}")
        if checks["grade_distribution_count"] != 50:
            raise RuntimeError(f"B13d grade distributions incomplete: {checks}")
        for item_id, wrapper in WRAPPERS.items():
            expected = {
                f"wrapper_{item_id}_closure": 1,
                f"skill_{wrapper['skill_id']}_relations": 2,
                f"pack_{wrapper['loot_pack_id']}_closure": 1,
            }
            for key, value in expected.items():
                if checks[key] != value:
                    raise RuntimeError(
                        f"B13d validation {key}={checks[key]}, expected {value}"
                    )
        shutil.copyfile(first, args.output)

    manifest = {
        "phase": "B13d-native-hiram-infusion-wrappers",
        "authority_order": [
            "compact-client-8.0-decrypted.sqlite",
            "game11_native",
            "x2game_confirmed",
            "observed_protocol",
        ],
        "base_runtime": {
            "path": str(args.base_runtime),
            "sha256": sha256(args.base_runtime),
        },
        "output": {
            "path": str(args.output),
            "sha256": sha256(args.output),
        },
        "wrappers": WRAPPERS,
        "result": {
            "item_id": RESULT_ITEM_ID,
            "concrete_type": "ItemEvolvingMaterialDesc",
            "stackable": False,
        },
        "closure_counts": {
            table: len(rows) for table, rows in sorted(closure.items())
        },
        "validation": checks,
        "provenance": {
            "skills": "client_compact_8",
            "effects": "client_compact_8+x2game_confirmed_actual_type",
            "skill_effects": "game11_native",
            "concrete_effects": "client_compact_8+game11_native",
            "grade_distributions": "game11_native+x2game_confirmed_layout",
            "pack_distribution_link":
                "server_derived_unique_native_grade_band_match",
        },
        "historical_3_0_rows": 0,
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
