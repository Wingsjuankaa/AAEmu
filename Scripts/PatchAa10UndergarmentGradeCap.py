#!/usr/bin/env python3
"""Raise the AA10 r575 synthesis-undergarment cap from Celestial to Eternal.

Category 23 already ships the complete Divine-through-Eternal EXP and random
attribute ladder, but ``max_evolving_grade`` is stale at grade 7.  Both the
client and AAEmu read that byte directly, so every effective compact.sqlite3
copy must receive the same transactional update.  Backups are intentionally
the caller's responsibility.

The retail client prefers ``game/db/compact.sqlite3`` inside ``game_pak`` over
the loose database.  After patching the loose client copy, reinsert it with the
verified, same-size ``Tools/PakEntryReplace`` utility.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path


CATEGORY_ID = 23
STALE_CAP = 7
ETERNAL_CAP = 12
EXPECTED_LADDER: dict[int, tuple[int, int, int]] = {
    7: (2100, 3420, 4),
    8: (2400, 4680, 4),
    9: (3200, 6120, 4),
    10: (6600, 8000, 5),
    11: (10000, 12000, 5),
    12: (15000, 18000, 5),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def patch_database(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)

    before_size = path.stat().st_size
    before_hash = sha256(path)
    connection = sqlite3.connect(path)
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError(f"{path}: quick_check failed before patch")

        connection.execute("BEGIN IMMEDIATE")
        category = connection.execute(
            "SELECT name, max_evolving_grade, item_rnd_attr_category_group_id "
            "FROM item_rnd_attr_categories WHERE id = ?",
            (CATEGORY_ID,),
        ).fetchone()
        if category is None:
            raise RuntimeError(f"{path}: category {CATEGORY_ID} is missing")
        name, cap, group_id = category
        if name != "live.16.10.cash_underwear.total_attr" or group_id != 3:
            raise RuntimeError(f"{path}: unexpected category {CATEGORY_ID}: {category}")
        if cap not in (STALE_CAP, ETERNAL_CAP):
            raise RuntimeError(f"{path}: unexpected existing cap {cap}")

        ladder = {
            grade: (grade_exp, gain_exp, modifier_count)
            for grade, grade_exp, gain_exp, modifier_count in connection.execute(
                "SELECT grade_id, grade_exp, gain_exp, max_unit_modifier_num "
                "FROM item_rnd_attr_category_properties "
                "WHERE item_rnd_attr_category_id = ? AND grade_id BETWEEN 7 AND 12 "
                "ORDER BY grade_id",
                (CATEGORY_ID,),
            )
        }
        if ladder != EXPECTED_LADDER:
            raise RuntimeError(f"{path}: unexpected Celestial-Eternal ladder {ladder}")

        undergarment_count = connection.execute(
            "SELECT COUNT(*) FROM item_armors "
            "WHERE slot_type_id = 13 AND item_rnd_attr_category_id = ?",
            (CATEGORY_ID,),
        ).fetchone()[0]
        if undergarment_count < 1:
            raise RuntimeError(f"{path}: category {CATEGORY_ID} has no undergarment templates")

        connection.execute(
            "UPDATE item_rnd_attr_categories SET max_evolving_grade = ? WHERE id = ?",
            (ETERNAL_CAP, CATEGORY_ID),
        )
        actual_cap = connection.execute(
            "SELECT max_evolving_grade FROM item_rnd_attr_categories WHERE id = ?",
            (CATEGORY_ID,),
        ).fetchone()[0]
        if actual_cap != ETERNAL_CAP:
            raise RuntimeError(f"{path}: post-patch cap is {actual_cap}")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError(f"{path}: quick_check failed after patch")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    after_size = path.stat().st_size
    if after_size != before_size:
        raise RuntimeError(f"{path}: size changed from {before_size} to {after_size}")

    print(path)
    print(f"  templates: {undergarment_count}")
    print(f"  cap:       {cap} -> {ETERNAL_CAP}")
    print(f"  before:    {before_hash}")
    print(f"  after:     {sha256(path)}")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {Path(sys.argv[0]).name} COMPACT_SQLITE3 [...]", file=sys.stderr)
        return 2
    for argument in sys.argv[1:]:
        patch_database(Path(argument).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
