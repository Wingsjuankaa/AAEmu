#!/usr/bin/env python3
"""Verify the complete accepted AA8 character-creation runtime."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any


REPLACEMENT_CLASSIFICATIONS = {
    "native_authoritative_replacement",
    "native_authoritative_empty",
    "server_derived_accepted",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def fail(message: str) -> None:
    raise RuntimeError(message)


def fetch_rows(
    connection: sqlite3.Connection, table: str, columns: list[str]
) -> list[dict[str, Any]]:
    names = ", ".join(f'"{column}"' for column in columns)
    order = ", ".join(f'"{column}"' for column in columns)
    return [
        dict(row)
        for row in connection.execute(
            f'SELECT {names} FROM "{table}" ORDER BY {order}'
        )
    ]


def canonical(rows: list[dict[str, Any]], columns: list[str]) -> list[tuple[Any, ...]]:
    return sorted(tuple(row[column] for column in columns) for row in rows)


def assert_exact_tables(
    connection: sqlite3.Connection,
    data: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    for table, expected_rows in data["tables"].items():
        classification = manifest["table_classifications"][table]
        if expected_rows:
            columns = list(expected_rows[0])
        else:
            columns = list(manifest["table_schemas"][table]["columns"])
        if classification in REPLACEMENT_CLASSIFICATIONS:
            actual_rows = fetch_rows(connection, table, columns)
            if canonical(actual_rows, columns) != canonical(expected_rows, columns):
                fail(f"{table}: runtime rows differ from the generated catalogue")
        elif classification in (
            "native_reference_closure",
            "server_derived_reference_closure",
        ):
            key_column = manifest["table_schemas"].get(table, {}).get(
                "key_column", "id"
            )
            for expected in expected_rows:
                identifier = int(expected[key_column])
                actual = connection.execute(
                    f'SELECT * FROM "{table}" WHERE "{key_column}"=?',
                    (identifier,),
                ).fetchall()
                if len(actual) != 1:
                    fail(
                        f"{table}: closure {key_column} {identifier} "
                        "is missing or duplicated"
                    )
                actual_row = dict(actual[0])
                for column, value in expected.items():
                    if actual_row[column] != value:
                        fail(
                            f"{table}: closure {key_column} {identifier} "
                            f"column {column} differs"
                        )
        else:
            fail(f"{table}: unsupported classification {classification}")


def scalar(connection: sqlite3.Connection, sql: str) -> int:
    return int(connection.execute(sql).fetchone()[0])


def assert_relations(connection: sqlite3.Connection) -> None:
    checks = {
        "character_spawn": """
            SELECT COUNT(*) FROM characters c
            LEFT JOIN native_character_creation_spawns s ON s.character_id=c.id
            WHERE s.character_id IS NULL OR s.zone_id<>c.starting_zone_id
        """,
        "character_inventory": """
            SELECT COUNT(*) FROM characters c
            LEFT JOIN native_character_creation_inventory i ON i.character_id=c.id
            WHERE i.character_id IS NULL OR i.inventory_slots<>50 OR i.bank_slots<>50
        """,
        "login_equip_pack": """
            SELECT COUNT(*) FROM login_stage_abilities a
            LEFT JOIN character_equip_packs p ON p.id=a.start_equip_pack_id
            WHERE p.id IS NULL
        """,
        "equip_cloth_pack": """
            SELECT COUNT(*) FROM character_equip_packs p
            LEFT JOIN equip_pack_cloths c ON c.id=p.newbie_cloth_pack_id
            WHERE p.newbie_cloth_pack_id<>0 AND c.id IS NULL
        """,
        "equip_weapon_pack": """
            SELECT COUNT(*) FROM character_equip_packs p
            LEFT JOIN equip_pack_weapons w ON w.id=p.newbie_weapon_pack_id
            WHERE p.newbie_weapon_pack_id<>0 AND w.id IS NULL
        """,
        "supply_item": """
            SELECT COUNT(*) FROM character_supplies s
            LEFT JOIN items i ON i.id=s.item_id WHERE i.id IS NULL
        """,
        "supply_slot": """
            SELECT COUNT(*) FROM character_supplies s
            LEFT JOIN native_character_creation_supply_slots d ON d.supply_id=s.id
            WHERE d.supply_id IS NULL OR d.slot_index<0 OR d.slot_index>=50
        """,
        "action_skill": """
            SELECT COUNT(*) FROM native_character_creation_action_slots a
            LEFT JOIN skills s ON s.id=a.action_id
            WHERE a.action_type=2 AND s.id IS NULL
        """,
        "action_non_spell_payload": """
            SELECT COUNT(*) FROM native_character_creation_action_slots
            WHERE (action_type=0 AND action_id<>0)
               OR (action_type NOT IN (0,2))
        """,
        "bag_expand_item": """
            SELECT COUNT(*) FROM bag_expands b
            LEFT JOIN items i ON i.id=b.item_id
            WHERE b.item_id<>0 AND i.id IS NULL
        """,
        "default_skill_character": """
            SELECT COUNT(*) FROM character_default_skills d
            LEFT JOIN characters c ON c.id=d.character_id WHERE c.id IS NULL
        """,
        "default_skill_relation": """
            SELECT COUNT(*) FROM character_default_skills d
            LEFT JOIN default_skills s ON s.id=d.default_skill_id WHERE s.id IS NULL
        """,
        "creation_default_skill_template": """
            SELECT COUNT(*) FROM character_default_skills d
            JOIN default_skills ds ON ds.id=d.default_skill_id
            LEFT JOIN skills s ON s.id=ds.skill_id
            WHERE s.id IS NULL
        """,
    }
    for name, sql in checks.items():
        missing = scalar(connection, sql)
        if missing:
            fail(f"{name}: found {missing} invalid or orphan rows")


def assert_matrix(connection: sqlite3.Connection) -> None:
    if scalar(connection, "SELECT COUNT(*) FROM characters") != 12:
        fail("playable character template count differs from 12")
    if scalar(connection, "SELECT COUNT(*) FROM login_stage_abilities") != 8:
        fail("selectable ability count differs from 8")
    if scalar(
        connection,
        "SELECT COUNT(*) FROM native_character_creation_action_slots",
    ) != 20832:
        fail("action matrix row count differs from 20832")
    combinations = connection.execute(
        """
        SELECT character_id,ability_id,COUNT(*) rows,
               SUM(CASE WHEN slot_index=1 AND action_type=2 AND action_id<>0
                        THEN 1 ELSE 0 END) selected,
               SUM(CASE WHEN slot_index<>1 AND (action_type<>0 OR action_id<>0)
                        THEN 1 ELSE 0 END) unexpected
        FROM native_character_creation_action_slots
        GROUP BY character_id,ability_id
        ORDER BY character_id,ability_id
        """
    ).fetchall()
    if len(combinations) != 96:
        fail(f"action matrix expected 96 combinations, found {len(combinations)}")
    for row in combinations:
        if int(row["rows"]) != 217 or int(row["selected"]) != 1 or int(
            row["unexpected"]
        ):
            fail(
                "invalid action snapshot for "
                f"{row['character_id']}/{row['ability_id']}"
            )
    ranges = connection.execute(
        """
        SELECT character_id,ability_id,MIN(slot_index) minimum,
               MAX(slot_index) maximum,COUNT(DISTINCT slot_index) distinct_slots
        FROM native_character_creation_action_slots
        GROUP BY character_id,ability_id
        """
    ).fetchall()
    if any(
        int(row["minimum"]) != 0
        or int(row["maximum"]) != 216
        or int(row["distinct_slots"]) != 217
        for row in ranges
    ):
        fail("action matrix contains a gap or duplicate slot")


def assert_spawns(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT character_id,world_id,zone_id,x,y,z,roll,pitch,yaw
        FROM native_character_creation_spawns ORDER BY character_id
        """
    ).fetchall()
    if len(rows) != 12:
        fail("spawn matrix differs from 12 rows")
    for row in rows:
        if int(row["world_id"]) != 1:
            fail(f"spawn {row['character_id']} has an unexpected world")
        if not all(
            math.isfinite(float(row[column]))
            for column in ("x", "y", "z", "roll", "pitch", "yaw")
        ):
            fail(f"spawn {row['character_id']} contains a non-finite transform")
        if abs(float(row["yaw"])) > math.pi:
            fail(f"spawn {row['character_id']} yaw was not converted to radians")


def assert_bag_expands(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT is_bank,step,price,item_id,item_count FROM bag_expands
        ORDER BY is_bank,step
        """
    ).fetchall()
    if len(rows) != 20:
        fail("bag_expands differs from 20 native rows")
    expected_prices = [5000, 10000, 30000, 100000, 250000]
    expected_counts = [1, 3, 6, 10, 10]
    keys = set()
    for row in rows:
        key = (int(row["is_bank"]), int(row["step"]))
        keys.add(key)
        step = key[1]
        expected = (
            (expected_prices[step], 0, 0)
            if step < 5
            else (0, 49000, expected_counts[step - 5])
        )
        actual = (
            int(row["price"]),
            int(row["item_id"]),
            int(row["item_count"]),
        )
        if actual != expected:
            fail(f"bag_expands {key} expected {expected}, found {actual}")
    if keys != {(is_bank, step) for is_bank in (0, 1) for step in range(10)}:
        fail("bag_expands does not cover both containers and steps 0..9")
    if scalar(connection, "SELECT COUNT(*) FROM bag_expands WHERE item_id=8000025"):
        fail("historical expansion item 8000025 remains active")


def assert_native_anomalies(connection: sqlite3.Connection) -> None:
    missing = {
        int(row[0])
        for row in connection.execute(
            """
            SELECT DISTINCT d.skill_id FROM default_skills d
            LEFT JOIN skills s ON s.id=d.skill_id
            WHERE s.id IS NULL
            """
        )
    }
    if missing != {44214}:
        fail(
            "native dangling default-skill set changed: "
            f"expected [44214], found {sorted(missing)}"
        )


def main() -> int:
    options = parse_args()
    data = json.loads(options.data.read_text(encoding="utf-8"))
    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
    if manifest.get("blockers") or not manifest.get("deployable"):
        fail("v2 manifest is not deployable")
    connection = sqlite3.connect(
        f"file:{options.runtime.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if quick != "ok" or integrity != "ok":
            fail(f"SQLite checks failed: quick={quick}, integrity={integrity}")
        assert_exact_tables(connection, data, manifest)
        assert_relations(connection)
        assert_matrix(connection)
        assert_spawns(connection)
        assert_bag_expands(connection)
        assert_native_anomalies(connection)
    finally:
        connection.close()
    print(
        json.dumps(
            {
                "action_rows": 20832,
                "bag_expand_rows": 20,
                "combinations": 96,
                "integrity_check": integrity,
                "orphan_rows": 0,
                "quick_check": quick,
                "runtime": str(options.runtime.resolve()),
                "verified": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
