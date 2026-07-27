#!/usr/bin/env python3
"""Apply the validated AA8-native quest 330 bundle to a runtime compact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-character-creation-v2.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest330-v3.sqlite3"
)
DEFAULT_DATA = DOMAIN / "generated" / "native-quest-330-v3-data.json"
DEFAULT_MANIFEST = DOMAIN / "generated" / "native-quest-330-v3-manifest.json"

ALLOWED_CLASSIFICATIONS = {
    "native_authoritative_targeted_upsert",
    "native_reference_closure",
    "server_derived_runtime_gate_from_native_closure",
}

TABLE_KEYS = {
    "aaemu_item_definition_coverage": "item_id",
    "item_body_parts": "item_id",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({quoted(table)})")
    ]


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        raise RuntimeError(f"{table}: targeted upsert cannot be empty")
    columns = list(rows[0])
    if any(list(row) != columns for row in rows):
        raise RuntimeError(f"{table}: inconsistent row columns")
    missing = set(columns) - set(table_columns(connection, table))
    if missing:
        raise RuntimeError(f"{table}: runtime misses columns {sorted(missing)}")
    if table == "unit_reqs":
        owner_pairs = {
            (str(row["owner_type"]), int(row["owner_id"])) for row in rows
        }
        for owner_type, owner_id in owner_pairs:
            connection.execute(
                "DELETE FROM unit_reqs WHERE owner_type=? AND owner_id=?",
                (owner_type, owner_id),
            )
        columns = list(rows[0])
        names = ", ".join(quoted(column) for column in columns)
        values = ", ".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO {quoted(table)} ({names}) VALUES ({values})",
            ([row[column] for column in columns] for row in rows),
        )
        return
    key = TABLE_KEYS.get(table, "id")
    ids = [int(row[key]) for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"{table}: duplicate IDs in bundle")
    placeholders = ", ".join("?" for _ in ids)
    connection.execute(
        f"DELETE FROM {quoted(table)} WHERE {quoted(key)} IN ({placeholders})", ids
    )
    names = ", ".join(quoted(column) for column in columns)
    values = ", ".join("?" for _ in columns)
    connection.executemany(
        f"INSERT INTO {quoted(table)} ({names}) VALUES ({values})",
        ([row[column] for column in columns] for row in rows),
    )


def verify_exact_rows(
    connection: sqlite3.Connection,
    table: str,
    expected: list[dict[str, Any]],
) -> None:
    connection.row_factory = sqlite3.Row
    if table == "unit_reqs":
        expected_pairs = {
            (str(row["owner_type"]), int(row["owner_id"])) for row in expected
        }
        actual: list[dict[str, Any]] = []
        columns = list(expected[0])
        names = ", ".join(quoted(column) for column in columns)
        for owner_type, owner_id in sorted(expected_pairs):
            actual.extend(
                dict(row)
                for row in connection.execute(
                    f"SELECT {names} FROM unit_reqs "
                    "WHERE owner_type=? AND owner_id=? "
                    "ORDER BY kind_id, value1, value2, value3",
                    (owner_type, owner_id),
                )
            )
        if actual != expected:
            raise RuntimeError(
                "unit_reqs: post-build rows differ from native bundle"
            )
        return
    key = TABLE_KEYS.get(table, "id")
    ids = [int(row[key]) for row in expected]
    placeholders = ", ".join("?" for _ in ids)
    columns = list(expected[0])
    names = ", ".join(quoted(column) for column in columns)
    actual = [
        dict(row)
        for row in connection.execute(
            f"SELECT {names} FROM {quoted(table)} "
            f"WHERE {quoted(key)} IN ({placeholders}) ORDER BY {quoted(key)}",
            ids,
        )
    ]
    ordered_expected = sorted(expected, key=lambda row: int(row[key]))
    if actual != ordered_expected:
        raise RuntimeError(f"{table}: post-build rows differ from native bundle")


def one(connection: sqlite3.Connection, sql: str, parameters=()):
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise RuntimeError(f"closure query returned no row: {sql}")
    return row


def verify_runtime(
    connection: sqlite3.Connection,
    tables: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    for table, rows in tables.items():
        verify_exact_rows(connection, table, rows)

    context_count = int(
        one(connection, "SELECT COUNT(*) FROM quest_contexts WHERE id=330")[0]
    )
    component_count = int(
        one(
            connection,
            "SELECT COUNT(*) FROM quest_components WHERE quest_context_id=330",
        )[0]
    )
    act_count = int(
        one(
            connection,
            """
            SELECT COUNT(*)
            FROM quest_acts qa
            JOIN quest_components qc ON qc.id=qa.quest_component_id
            WHERE qc.quest_context_id=330
            """,
        )[0]
    )
    if (context_count, component_count, act_count) != (1, 3, 8):
        raise RuntimeError(
            "quest 330 structural closure differs: "
            f"{context_count}/{component_count}/{act_count}"
        )

    expected_details = {
        "QuestActConAcceptNpc": ("quest_act_con_accept_npcs", 1250),
        "QuestActConReportNpc": ("quest_act_con_report_npcs", 329),
        "QuestActSupplyExp": ("quest_act_supply_exps", 3922),
        "QuestActSupplyItem:8675": ("quest_act_supply_items", 8675),
        "QuestActSupplyItem:8676": ("quest_act_supply_items", 8676),
        "QuestActSupplyItem:8869": ("quest_act_supply_items", 8869),
        "QuestActSupplySelectiveItem:3646": (
            "quest_act_supply_selective_items",
            3646,
        ),
        "QuestActSupplySelectiveItem:3647": (
            "quest_act_supply_selective_items",
            3647,
        ),
    }
    for label, (table, detail_id) in expected_details.items():
        count = int(
            one(
                connection,
                f"SELECT COUNT(*) FROM {quoted(table)} WHERE id=?",
                (detail_id,),
            )[0]
        )
        if count != 1:
            raise RuntimeError(f"{label}: expected one detail row, found {count}")

    reward_item_ids = {23633, 51185, 18791, 47868, 47869}
    placeholders = ", ".join("?" for _ in reward_item_ids)
    present_items = {
        int(row[0])
        for row in connection.execute(
            f"SELECT id FROM items WHERE id IN ({placeholders})",
            sorted(reward_item_ids),
        )
    }
    if present_items != reward_item_ids:
        raise RuntimeError(
            f"quest 330 reward items missing: {sorted(reward_item_ids - present_items)}"
        )

    appearance_item_ids = {
        16066, 25269, 24133, 2722, 18490, 25017, 19838
    }
    placeholders = ", ".join("?" for _ in appearance_item_ids)
    present_appearance_items = {
        int(row[0])
        for row in connection.execute(
            f"SELECT id FROM items WHERE id IN ({placeholders})",
            sorted(appearance_item_ids),
        )
    }
    if present_appearance_items != appearance_item_ids:
        raise RuntimeError(
            "quest 330 NPC appearance items missing: "
            f"{sorted(appearance_item_ids - present_appearance_items)}"
        )
    expected_armor_slots = {
        16066: (1, 31),
        2722: (1, 3),
        18490: (5, 5),
        25017: (1, 7),
    }
    actual_armor_slots = {
        int(row[0]): (int(row[1]), int(row[2]))
        for row in connection.execute(
            """
            SELECT item_id, type_id, slot_type_id
            FROM item_armors
            WHERE item_id IN (?, ?, ?, ?)
            """,
            sorted(expected_armor_slots),
        )
    }
    if actual_armor_slots != expected_armor_slots:
        raise RuntimeError(
            "quest 330 NPC armor descriptors differ: "
            f"{actual_armor_slots}"
        )
    expected_hair = {24133, 25269}
    actual_hair = {
        int(row[0])
        for row in connection.execute(
            """
            SELECT item_id
            FROM item_body_parts
            WHERE item_id IN (?, ?)
              AND model_id=10
              AND slot_type_id=24
            """,
            sorted(expected_hair),
        )
    }
    if actual_hair != expected_hair:
        raise RuntimeError(
            f"quest 330 NPC native hair descriptors differ: {actual_hair}"
        )
    native_start_requirement = [
        tuple(row)
        for row in connection.execute(
            """
            SELECT display_msg, kind_id, value1, value2, value3
            FROM unit_reqs
            WHERE owner_type='QuestComponent' AND owner_id=1520
            """
        )
    ]
    if native_start_requirement != [(1, 56, 148, 0, 0)]:
        raise RuntimeError(
            "quest 330 native start requirement differs: "
            f"{native_start_requirement}"
        )
    complete_gate_ids = appearance_item_ids | {23633, 48541}
    placeholders = ", ".join("?" for _ in complete_gate_ids)
    complete_gate_count = int(
        one(
            connection,
            f"""
            SELECT COUNT(*)
            FROM aaemu_item_definition_coverage
            WHERE item_id IN ({placeholders})
              AND coverage='complete'
              AND missing_dependencies=''
            """,
            sorted(complete_gate_ids),
        )[0]
    )
    if complete_gate_count != len(complete_gate_ids):
        raise RuntimeError(
            "quest 330 reward/NPC appearance runtime gates are incomplete"
        )

    npc_links = {
        "accept": int(
            one(
                connection,
                "SELECT npc_id FROM quest_act_con_accept_npcs WHERE id=1250",
            )[0]
        ),
        "report": int(
            one(
                connection,
                "SELECT npc_id FROM quest_act_con_report_npcs WHERE id=329",
            )[0]
        ),
    }
    if npc_links != {"accept": 3597, "report": 11541}:
        raise RuntimeError(f"quest 330 NPC links differ: {npc_links}")

    next_accept_count = int(
        one(
            connection,
            """
            SELECT COUNT(*)
            FROM quest_contexts q
            JOIN quest_components c ON c.quest_context_id=q.id
            JOIN quest_acts a ON a.quest_component_id=c.id
            JOIN quest_act_con_accept_npcs d ON d.id=a.act_detail_id
            WHERE q.id=2531
              AND c.id=10962
              AND a.act_detail_type='QuestActConAcceptNpc'
              AND a.act_detail_id=2097
              AND d.npc_id=11541
            """,
        )[0]
    )
    if next_accept_count != 1:
        raise RuntimeError("quest 2531 acceptance closure at NPC 11541 is absent")

    level_supply = tuple(
        one(
            connection,
            "SELECT level, copper, exp FROM quest_supplies WHERE id=1",
        )
    )
    if level_supply != (1, 33, 420):
        raise RuntimeError(f"native level-1 quest supply differs: {level_supply}")

    npc_model_count = int(
        one(
            connection,
            """
            SELECT COUNT(*)
            FROM npcs n
            JOIN models m ON m.id=n.model_id
            JOIN actor_models a
              ON m.sub_type='ActorModel' AND a.id=m.sub_id
            WHERE n.id IN (3597, 11541)
              AND m.id=10
              AND a.id=1
            """,
        )[0]
    )
    if npc_model_count != 2:
        raise RuntimeError("quest 330 NPC/model/actor-model closure is incomplete")

    quick = str(one(connection, "PRAGMA quick_check")[0])
    integrity = str(one(connection, "PRAGMA integrity_check")[0])
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(
            f"SQLite validation failed: quick={quick}, integrity={integrity}"
        )
    return {
        "quest_contexts": context_count,
        "quest_components": component_count,
        "quest_acts": act_count,
        "reward_items": len(present_items),
        "appearance_items": len(present_appearance_items),
        "appearance_armors": len(actual_armor_slots),
        "appearance_hair": len(actual_hair),
        "native_start_requirement": [56, 148],
        "complete_runtime_gates": complete_gate_count,
        "accept_npc": npc_links["accept"],
        "report_npc": npc_links["report"],
        "next_quest_accept_closed": True,
        "generic_copper": level_supply[1],
        "generic_exp_suppressed": level_supply[2],
        "npc_model_links": npc_model_count,
        "quick_check": quick,
        "integrity_check": integrity,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    for path in (options.base_runtime, options.data, options.manifest):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
    data = json.loads(options.data.read_text(encoding="utf-8"))
    if not manifest.get("deployable") or manifest.get("blockers"):
        raise RuntimeError("quest 330 authority gates are not closed")
    expected_base = manifest["sources"]["base_runtime"]["sha256"]
    actual_base = sha256(options.base_runtime)
    if actual_base != expected_base:
        raise RuntimeError(
            f"base runtime hash differs: expected {expected_base}, found {actual_base}"
        )
    if data["sources"]["base_runtime"]["sha256"] != expected_base:
        raise RuntimeError("data bundle and manifest disagree about the base runtime")

    tables = data["tables"]
    for table in tables:
        classification = manifest["table_classifications"].get(table)
        if classification not in ALLOWED_CLASSIFICATIONS:
            raise RuntimeError(f"{table}: unsupported classification {classification!r}")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(options.base_runtime, options.output)
    connection = sqlite3.connect(options.output)
    try:
        with connection:
            context_columns = set(table_columns(connection, "quest_contexts"))
            for column in ("hide_chapter_index", "only_one_score_title"):
                if column not in context_columns:
                    connection.execute(
                        f"ALTER TABLE quest_contexts ADD COLUMN {quoted(column)} "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
            for table, rows in tables.items():
                upsert_rows(connection, table, rows)
        verification = verify_runtime(connection, tables)
    finally:
        connection.close()

    result = {
        "built": True,
        "output": str(options.output.resolve()),
        "sha256": sha256(options.output),
        "base_sha256": actual_base,
        "verification": verification,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
