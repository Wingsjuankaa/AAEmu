#!/usr/bin/env python3
"""Build the AA8 selective Lunagem catalogue from game11.

The Kakao 8.0 client stores the selectable result list in the cached native
skill record, not in compact.sqlite.  Result references are item UIDs and are
resolved exclusively through the decrypted AA8 items table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


MARKER = b"\x01\xff\xff\xff\xff"
EFFECT = b'{"effect":"selective_item"'

# AA8 keeps separate selectable lists for each V2 tier and color.  The
# source item use_skill_id alternates across these records and therefore
# cannot bind this family safely.  The binding is derived from the native
# alias, source icon/color and fixed grade (3=base, 4=Splendid).
V2_LUNAGEM_SOURCE_BY_ALIAS = {
    "v2.socket_1tier_red": 43476,
    "v2.socket_1tier_brown": 43477,
    "v2.socket_1tier_blue": 43478,
    "v2.socket_1tier_yellow": 43479,
    "v2.socket_1tier_green": 43480,
    "v2.socket_1tier_pink": 43481,
    "v2.socket_2tier_red": 43483,
    "v2.socket_2tier_brown": 43484,
    "v2.socket_2tier_blue": 43485,
    "v2.socket_2tier_yellow": 43486,
    "v2.socket_2tier_green": 43487,
    "v2.socket_2tier_pink": 43488,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def read_aa8_items(compact: Path) -> tuple[dict[int, dict], dict[int, int]]:
    connection = sqlite3.connect(f"file:{compact.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT id, uid, category_id, use_skill_id, use_skill_as_reagent,
               fixed_grade, max_stack_size
        FROM items
        """
    ).fetchall()
    connection.close()
    by_id = {int(row["id"]): dict(row) for row in rows}
    by_uid = {int(row["uid"]) & 0xFFFFFFFF: int(row["id"]) for row in rows}
    return by_id, by_uid


def extract(game11: Path, compact: Path) -> tuple[list[dict], list[dict]]:
    blob = game11.read_bytes()
    items, uid_to_id = read_aa8_items(compact)
    source_by_skill = {
        int(row["use_skill_id"]): row
        for row in items.values()
        if int(row["category_id"] or 0) == 152
        and int(row["use_skill_id"] or 0) > 0
    }

    closed: list[dict] = []
    blocked: list[dict] = []
    cursor = 0
    while True:
        json_start = blob.find(EFFECT, cursor)
        if json_start < 0:
            break
        cursor = json_start + 1
        json_end = blob.find(b"\0", json_start)
        if json_end < 0:
            continue
        try:
            payload = json.loads(blob[json_start:json_end].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue

        json_marker = json_start - len(MARKER)
        if blob[json_marker:json_start] != MARKER:
            continue
        alias_marker = blob.rfind(MARKER, max(0, json_marker - 512), json_marker)
        if alias_marker < 14:
            continue
        alias_start = alias_marker + len(MARKER)
        alias_end = blob.find(b"\0", alias_start, json_marker)
        if alias_end < 0:
            continue
        skill_offset = alias_start - 14
        skill_id = int.from_bytes(blob[skill_offset:skill_offset + 4], "little")
        alias = blob[alias_start:alias_end].decode("utf-8")
        mapped_source_id = V2_LUNAGEM_SOURCE_BY_ALIAS.get(alias)
        if alias.startswith("v2.socket_"):
            source = items.get(mapped_source_id) if mapped_source_id else None
            source_binding = "server_derived:alias+fixed_grade+icon"
        else:
            source = source_by_skill.get(skill_id)
            source_binding = "client_compact_8:use_skill_id"
        if source is None:
            continue

        options = []
        unresolved = []
        for index, option in enumerate(payload.get("list", []), start=1):
            uid_text = str(option.get("item", "")).strip()
            try:
                uid = int(uid_text, 16) & 0xFFFFFFFF
            except ValueError:
                unresolved.append(uid_text)
                continue
            item_id = uid_to_id.get(uid)
            if item_id is None:
                unresolved.append(uid_text)
                continue
            options.append(
                {
                    "index": index,
                    "result_item_id": item_id,
                    "result_uid": f"{uid:08x}",
                    "count": int(option.get("count", 1)),
                    "grade": (
                        int(option["grade"])
                        if option.get("grade") is not None
                        else None
                    ),
                    "provenance": "game11_native+client_compact_8",
                }
            )

        action = {
            "skill_id": skill_id,
            "source_item_id": int(source["id"]),
            "alias": alias,
            "select_count": int(payload.get("select", 1)),
            "consume_item_count": int(payload.get("consume_item_count", 1)),
            "is_multi": bool(payload.get("is_multi", False)),
            "popup_text": str(payload.get("popup_text", "")),
            "source_offset": skill_offset,
            "source_binding": source_binding,
            "options": options,
            "unresolved_uids": unresolved,
            "provenance": (
                "game11_native+client_compact_8+x2game_confirmed+" +
                source_binding
            ),
        }
        expected = len(payload.get("list", []))
        if unresolved or len(options) != expected or expected == 0:
            blocked.append(action)
        else:
            closed.append(action)

    closed.sort(key=lambda row: row["skill_id"])
    blocked.sort(key=lambda row: row["skill_id"])
    return closed, blocked


DDL = """
CREATE TABLE aaemu_selective_item_actions (
    skill_id INTEGER PRIMARY KEY,
    source_item_id INTEGER NOT NULL UNIQUE,
    alias TEXT NOT NULL,
    select_count INTEGER NOT NULL,
    consume_item_count INTEGER NOT NULL,
    is_multi INTEGER NOT NULL,
    popup_text TEXT NOT NULL,
    provenance TEXT NOT NULL,
    source_offset INTEGER NOT NULL
);
CREATE TABLE aaemu_selective_item_options (
    skill_id INTEGER NOT NULL,
    option_index INTEGER NOT NULL,
    result_item_id INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    result_grade INTEGER,
    result_uid TEXT NOT NULL,
    provenance TEXT NOT NULL,
    PRIMARY KEY (skill_id, option_index)
);
"""


def build(base: Path, destination: Path, actions: list[dict]) -> None:
    shutil.copy2(base, destination)
    connection = sqlite3.connect(destination)
    connection.executescript(
        """
        DROP TABLE IF EXISTS aaemu_selective_item_options;
        DROP TABLE IF EXISTS aaemu_selective_item_actions;
        """
    )
    connection.executescript(DDL)
    for action in actions:
        connection.execute(
            """
            INSERT INTO aaemu_selective_item_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action["skill_id"],
                action["source_item_id"],
                action["alias"],
                action["select_count"],
                action["consume_item_count"],
                int(action["is_multi"]),
                action["popup_text"],
                action["provenance"],
                action["source_offset"],
            ),
        )
        for option in action["options"]:
            connection.execute(
                """
                INSERT INTO aaemu_selective_item_options
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action["skill_id"],
                    option["index"],
                    option["result_item_id"],
                    option["count"],
                    option["grade"],
                    option["result_uid"],
                    option["provenance"],
                ),
            )
    connection.commit()
    connection.execute("VACUUM")
    connection.close()


def validate(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    actions = connection.execute(
        "SELECT COUNT(*) FROM aaemu_selective_item_actions"
    ).fetchone()[0]
    options = connection.execute(
        "SELECT COUNT(*) FROM aaemu_selective_item_options"
    ).fetchone()[0]
    orphans = connection.execute(
        """
        SELECT COUNT(*) FROM aaemu_selective_item_options o
        LEFT JOIN aaemu_selective_item_actions a ON a.skill_id=o.skill_id
        LEFT JOIN items i ON i.id=o.result_item_id
        WHERE a.skill_id IS NULL OR i.id IS NULL
        """
    ).fetchone()[0]
    connection.close()
    if quick != "ok" or integrity != "ok" or orphans:
        raise RuntimeError(
            f"Invalid runtime: quick={quick}, integrity={integrity}, orphans={orphans}"
        )
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "actions": actions,
        "options": options,
        "orphans": orphans,
    }


def main() -> None:
    options = args()
    actions, blocked = extract(options.game11, options.client_compact)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        build(options.base_runtime, first, actions)
        build(options.base_runtime, second, actions)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic builds: {first_hash} != {second_hash}"
            )
        shutil.copy2(first, options.output)

    report = {
        "runtime": str(options.output),
        "sha256": sha256(options.output),
        "sources": {
            "game11": {"path": str(options.game11), "sha256": sha256(options.game11)},
            "client_compact": {
                "path": str(options.client_compact),
                "sha256": sha256(options.client_compact),
            },
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": sha256(options.base_runtime),
            },
        },
        "validation": validate(options.output),
        "actions": actions,
        "blocked_actions": blocked,
        "wire": {
            "packet": "CSBagHandleSelectiveItemsPacket",
            "opcode": "0x1C4",
            "layout": "byte slotType, byte slot, uint32 tryCount, uint32 count, uint32[count] optionIndices",
            "item_task_reason": 150,
            "evidence": "x2game.dll+selective_item.alb",
        },
    }
    options.manifest.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["validation"], sort_keys=True))
    print(report["sha256"])


if __name__ == "__main__":
    main()
