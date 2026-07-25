#!/usr/bin/env python3
"""Seal the AA8 Hiram/Erenor evolution runtime.

B13c starts from the validated B13b runtime and imports only the three
directly observed AA8 skill closures that were still incomplete:

* random evolving-attribute reroll (SpecialEffect 136);
* selective evolving-attribute reroll (SpecialEffect 187);
* Hiram decrystallization (SpecialEffect 156).

No row from the historical compact is consulted.
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
EXPECTED_SKILLS = {
    32060: 136,
    39040: 156,
    46234: 187,
}
EXPECTED_ITEMS = {
    46682: 32060,
    45732: 39040,
    50552: 46234,
    50635: 46234,
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


def extract_closure(
    game11: Path,
    client_compact: Path,
) -> dict[str, list[dict[str, Any]]]:
    sys.path.insert(0, str(SKILLS_ROOT))
    from extract_battlerage_manifest import extract_client_relationships

    relationships = extract_client_relationships(game11)
    skill_effects = [
        {
            **dict(row),
            "end_level": 255
            if int(row.get("end_level") or 0) == 99
            else int(row.get("end_level") or 0),
        }
        for row in relationships["skill_effects"]
        if int(row["skill_id"]) in EXPECTED_SKILLS
    ]
    effect_ids = {int(row["effect_id"]) for row in skill_effects}

    with sqlite3.connect(client_compact) as connection:
        connection.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in effect_ids)
        effects = [
            dict(row)
            for row in connection.execute(
                f"SELECT * FROM effects WHERE id IN ({placeholders})",
                sorted(effect_ids),
            )
        ]
        skill_placeholders = ",".join("?" for _ in EXPECTED_SKILLS)
        skills = [
            dict(row)
            for row in connection.execute(
                f"SELECT * FROM skills WHERE id IN ({skill_placeholders})",
                sorted(EXPECTED_SKILLS),
            )
        ]

    if {int(row["id"]) for row in effects} != effect_ids:
        raise RuntimeError("AA8 client compact is missing a B13c effect row")
    if {int(row["id"]) for row in skills} != set(EXPECTED_SKILLS):
        raise RuntimeError("AA8 client compact is missing a B13c skill row")

    actual_ids = {int(row["actual_id"]) for row in effects}
    special_effects = [
        dict(row)
        for row in relationships["concrete_effects"]["special_effects"]
        if int(row["id"]) in actual_ids
    ]
    special_by_id = {
        int(row["id"]): int(row["special_effect_type_id"])
        for row in special_effects
    }
    effect_by_id = {int(row["id"]): row for row in effects}
    for relation in skill_effects:
        skill_id = int(relation["skill_id"])
        effect = effect_by_id[int(relation["effect_id"])]
        actual_id = int(effect["actual_id"])
        actual_type = special_by_id.get(actual_id)
        if actual_type != EXPECTED_SKILLS[skill_id]:
            raise RuntimeError(
                f"AA8 skill {skill_id} expected SpecialEffect "
                f"{EXPECTED_SKILLS[skill_id]}, got {actual_type}"
            )
        effect["actual_type"] = "SpecialEffect"

    return {
        "skills": skills,
        "skill_effects": skill_effects,
        "effects": effects,
        "special_effects": special_effects,
    }


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
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


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check":
            connection.execute("PRAGMA integrity_check").fetchone()[0],
    }
    for skill_id, special_type in EXPECTED_SKILLS.items():
        checks[f"skill_{skill_id}_closure"] = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM skill_effects se
                JOIN skills s ON s.id=se.skill_id
                JOIN effects e ON e.id=se.effect_id
                JOIN special_effects sp ON sp.id=e.actual_id
                WHERE se.skill_id=? AND e.actual_type='SpecialEffect'
                  AND sp.special_effect_type_id=?
                """,
                (skill_id, special_type),
            ).fetchone()[0]
        )
    for item_id, skill_id in EXPECTED_ITEMS.items():
        checks[f"item_{item_id}_skill"] = int(
            connection.execute(
                "SELECT COUNT(*) FROM items WHERE id=? AND use_skill_id=?",
                (item_id, skill_id),
            ).fetchone()[0]
        )
    checks["reroll_item_set_230"] = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM item_set_items
            WHERE item_set_id=230 AND item_id IN (46682,50552,50635)
            """
        ).fetchone()[0]
    )
    checks["historical_category_material_table"] = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='item_rnd_attr_category_materials'
            """
        ).fetchone()[0]
    )
    return checks


def build(
    base: Path,
    output: Path,
    closure: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        for table in ("skills", "effects", "special_effects", "skill_effects"):
            insert_rows(connection, table, closure[table])
        metadata = {
            "phase": "B13c-native-hiram-erenor-evolution",
            "authority": "AA8 client compact/game11/x2game; no 3.0 rows",
            "implementation.reroll.random":
                "skill 32060/effect 52963/special 21462/type 136",
            "implementation.reroll.selectable":
                "skill 46234/effect 88704/special 56777/type 187",
            "implementation.decrystallization":
                "item 45732/skill 39040/effect 70715/special 35710/type 156",
            "item_task.decrystallization":
                "170 restore-disable-enchant",
            "families.enabled": "hiram_weapons,erenor_weapons",
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
    closure = extract_closure(args.game11, args.client_compact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aa8-b13c-") as directory:
        first = Path(directory) / "first.sqlite3"
        second = Path(directory) / "second.sqlite3"
        checks = build(args.base_runtime, first, closure)
        second_checks = build(args.base_runtime, second, closure)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic B13c build: {first_hash} != {second_hash}"
            )
        if checks != second_checks:
            raise RuntimeError("B13c validation differs between builds")
        if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
            raise RuntimeError(f"B13c SQLite validation failed: {checks}")
        expected_counts = {
            "skill_32060_closure": 1,
            "skill_39040_closure": 1,
            "skill_46234_closure": 1,
            "item_46682_skill": 1,
            "item_45732_skill": 1,
            "item_50552_skill": 1,
            "item_50635_skill": 1,
            "reroll_item_set_230": 3,
            "historical_category_material_table": 0,
        }
        for key, expected in expected_counts.items():
            if checks[key] != expected:
                raise RuntimeError(
                    f"B13c validation {key}={checks[key]}, expected {expected}"
                )
        shutil.copyfile(first, args.output)

    manifest = {
        "phase": "B13c-native-hiram-erenor-evolution",
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
        "closure_counts": {
            table: len(rows) for table, rows in sorted(closure.items())
        },
        "validation": checks,
        "provenance": {
            "skills": "client_compact_8",
            "effects": "client_compact_8+x2game_confirmed_actual_type",
            "skill_effects": "game11_native",
            "special_effects": "game11_native",
            "runtime_logic": "x2game_confirmed+server_derived",
        },
        "blocked_without_inference": [
            "free reroll charges stored in EquipItem.EvolveChance",
            "SC offset 0x113 until its wire serializer is identified",
        ],
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
