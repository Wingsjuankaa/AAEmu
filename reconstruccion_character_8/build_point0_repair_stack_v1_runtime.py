#!/usr/bin/env python3
"""Build the AA8 point-0 repair runtime from the last accepted stack.

The only data mutation in this layer is the initial action-bar matrix. Native
`default_skills.add_to_slot/slot_index` supplies global basic actions and
`character_default_skills` restricts race-specific actions per character
template. The selected ability skill already accepted at slot 1 is preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest-repair-stack-v1.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-point0-repair-stack-v1.sqlite3"
)
DEFAULT_MANIFEST = DOMAIN / "generated" / "point0-repair-stack-v1-runtime-manifest.json"
EXPECTED_BASE_SHA256 = "7C0100208A4846058F62377203DE48E237D332CFB77E926F90D96B5397C5DB25"
ACTION_SLOT_COUNT = 217
ACTION_TYPE_NONE = 0
ACTION_TYPE_SPELL = 2


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def derive_rows(connection: sqlite3.Connection):
    characters = [row[0] for row in connection.execute("SELECT id FROM characters ORDER BY id")]
    abilities = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT ability_id FROM native_character_creation_action_slots ORDER BY ability_id"
        )
    ]
    selected = {
        (character_id, ability_id): action_id
        for character_id, ability_id, action_id in connection.execute(
            "SELECT character_id,ability_id,action_id "
            "FROM native_character_creation_action_slots "
            "WHERE slot_index=1 AND action_type=?",
            (ACTION_TYPE_SPELL,),
        )
    }
    linked_default_ids = {
        row[0] for row in connection.execute("SELECT DISTINCT default_skill_id FROM character_default_skills")
    }
    addable = {
        row[0]: (row[1], row[2])
        for row in connection.execute(
            "SELECT id,skill_id,slot_index FROM default_skills "
            "WHERE add_to_slot=1 ORDER BY slot_index,id"
        )
    }
    global_actions = [
        (skill_id, slot_index)
        for default_id, (skill_id, slot_index) in addable.items()
        if default_id not in linked_default_ids
    ]
    character_actions = {
        character_id: [
            addable[default_id]
            for (default_id,) in connection.execute(
                "SELECT default_skill_id FROM character_default_skills "
                "WHERE character_id=? ORDER BY default_skill_id",
                (character_id,),
            )
            if default_id in addable
        ]
        for character_id in characters
    }

    rows = []
    expected_non_empty = {}
    for character_id in characters:
        for ability_id in abilities:
            key = (character_id, ability_id)
            if key not in selected:
                raise RuntimeError(f"missing accepted initial skill for character/ability {key}")
            actions = {1: selected[key]}
            for skill_id, slot_index in global_actions + character_actions[character_id]:
                if slot_index in actions and actions[slot_index] != skill_id:
                    raise RuntimeError(
                        f"action collision character={character_id} ability={ability_id} slot={slot_index}"
                    )
                actions[slot_index] = skill_id
            expected_non_empty[key] = tuple(sorted(actions.items()))
            for slot_index in range(ACTION_SLOT_COUNT):
                action_id = actions.get(slot_index, 0)
                rows.append(
                    (
                        ability_id,
                        action_id,
                        ACTION_TYPE_SPELL if action_id else ACTION_TYPE_NONE,
                        character_id,
                        slot_index,
                    )
                )
    return rows, expected_non_empty, global_actions, character_actions, characters, abilities


def validate(connection: sqlite3.Connection, expected_non_empty, characters, abilities):
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "row_count": connection.execute(
            "SELECT COUNT(*) FROM native_character_creation_action_slots"
        ).fetchone()[0],
        "combination_count": connection.execute(
            "SELECT COUNT(*) FROM (SELECT character_id,ability_id "
            "FROM native_character_creation_action_slots GROUP BY character_id,ability_id)"
        ).fetchone()[0],
        "invalid_action_skills": connection.execute(
            "SELECT COUNT(*) FROM native_character_creation_action_slots a "
            "LEFT JOIN skills s ON s.id=a.action_id "
            "WHERE a.action_type=? AND s.id IS NULL",
            (ACTION_TYPE_SPELL,),
        ).fetchone()[0],
    }
    expected_rows = len(characters) * len(abilities) * ACTION_SLOT_COUNT
    if checks != {
        "quick_check": "ok",
        "integrity_check": "ok",
        "row_count": expected_rows,
        "combination_count": len(characters) * len(abilities),
        "invalid_action_skills": 0,
    }:
        raise RuntimeError(f"structural validation failed: {checks}")

    for key, expected in expected_non_empty.items():
        actual = tuple(
            connection.execute(
                "SELECT slot_index,action_id FROM native_character_creation_action_slots "
                "WHERE character_id=? AND ability_id=? AND action_type=? ORDER BY slot_index",
                (*key, ACTION_TYPE_SPELL),
            )
        )
        if actual != expected:
            raise RuntimeError(f"action matrix mismatch for {key}: {actual} != {expected}")
    return checks


def build(options) -> dict:
    base_hash = sha256(options.base_runtime)
    if base_hash != EXPECTED_BASE_SHA256:
        raise RuntimeError(f"unexpected base runtime SHA-256: {base_hash}")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copyfile(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    try:
        rows, expected, global_actions, character_actions, characters, abilities = derive_rows(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM native_character_creation_action_slots")
        connection.executemany(
            "INSERT INTO native_character_creation_action_slots "
            "(ability_id,action_id,action_type,character_id,slot_index) VALUES (?,?,?,?,?)",
            rows,
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS aaemu_point0_repair_stack "
            "(phase TEXT PRIMARY KEY,authority TEXT NOT NULL,base_sha256 TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_point0_repair_stack VALUES (?,?,?)",
            ("point0-repair-stack-v1", "ArcheAge Kakao 8.0.3.12 r558734", base_hash),
        )
        checks = validate(connection, expected, characters, abilities)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    os.replace(temporary, options.output)
    manifest = {
        "format_version": 1,
        "phase": "point0-repair-stack-v1-runtime",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": base_hash},
            "action_authority": ["default_skills", "character_default_skills"],
        },
        "scope": {
            "mutation": ["native_character_creation_action_slots"],
            "characters": characters,
            "abilities": abilities,
            "slots_per_combination": ACTION_SLOT_COUNT,
            "global_actions": [
                {"skill_id": skill_id, "slot_index": slot_index}
                for skill_id, slot_index in global_actions
            ],
            "template_actions": {
                str(character_id): [
                    {"skill_id": skill_id, "slot_index": slot_index}
                    for skill_id, slot_index in actions
                ]
                for character_id, actions in character_actions.items()
            },
        },
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
    }
    options.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()
    print(json.dumps(build(options), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
