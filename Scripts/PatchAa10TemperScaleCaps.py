#!/usr/bin/env python3
"""Restore the AA10 r575 equipment Temper cap from +12 to +30.

The disabled r575 Temper feature ships all 32 scale descriptors (none and
+1..+30) and its four catalyst effects declare scale 30, but every temperable
item template was bulk-capped at descriptor 12.  Both the client and AAEmu
read ``items.max_enchant_scale_id`` directly, so every effective
``compact.sqlite3`` copy must receive the same transactional update.

Backups are intentionally the caller's responsibility.  The retail client
prefers ``game/db/compact.sqlite3`` inside ``game_pak`` over the loose copy;
after patching the loose client database, reinsert it with the verified
same-size ``Tools/PakEntryReplace`` utility.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path


STALE_CAP = 12
RETAIL_CAP = 30
# The compact retail projection omits 73 server-only/test templates retained by
# the decrypted World catalogue. Both exact projections are accepted; anything
# else fails closed.
EXPECTED_COVERAGE = {
    (6461, 2355, 4106, 0),
    (6534, 2384, 4142, 8),
}
EXPECTED_RATIO_COUNT = 32
EXPECTED_CATALYST_EFFECTS = {
    37723: (1, 0, 0, 30),
    37724: (2, 0, 0, 30),
    39267: (1, 1, 0, 30),
    39268: (2, 1, 0, 30),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _validate_catalogue(connection: sqlite3.Connection, path: Path) -> tuple[int, int, int]:
    ratios = connection.execute(
        "SELECT id, name, scale FROM enchant_scale_ratios ORDER BY id"
    ).fetchall()
    if len(ratios) != EXPECTED_RATIO_COUNT:
        raise RuntimeError(f"{path}: expected 32 enchant-scale ratios, got {len(ratios)}")
    if ratios[0] != (0, "none", 0) or ratios[30] != (30, "+30", 250):
        raise RuntimeError(f"{path}: unexpected none/+30 scale descriptors")

    catalyst_effects = {
        skill_id: (value1, value2, value3, value4)
        for skill_id, value1, value2, value3, value4 in connection.execute(
            "SELECT se.skill_id, sp.value1, sp.value2, sp.value3, sp.value4 "
            "FROM skill_effects se "
            "JOIN effects e ON e.id = se.effect_id "
            "JOIN special_effects sp ON sp.id = e.actual_id "
            "WHERE se.skill_id IN (37723, 37724, 39267, 39268) "
            "AND e.actual_type = 'SpecialEffect' AND sp.special_effect_type_id = 126"
        )
    }
    if catalyst_effects != EXPECTED_CATALYST_EFFECTS:
        raise RuntimeError(f"{path}: unexpected Temper catalyst effects {catalyst_effects}")

    template_count = connection.execute(
        "SELECT COUNT(*) FROM items WHERE max_enchant_scale_id IN (?, ?)",
        (STALE_CAP, RETAIL_CAP),
    ).fetchone()[0]
    weapon_count = connection.execute(
        "SELECT COUNT(*) FROM items i JOIN item_weapons w ON w.item_id = i.id "
        "WHERE i.max_enchant_scale_id IN (?, ?)",
        (STALE_CAP, RETAIL_CAP),
    ).fetchone()[0]
    armor_count = connection.execute(
        "SELECT COUNT(*) FROM items i JOIN item_armors a ON a.item_id = i.id "
        "WHERE i.max_enchant_scale_id IN (?, ?)",
        (STALE_CAP, RETAIL_CAP),
    ).fetchone()[0]
    orphan_count = template_count - weapon_count - armor_count
    actual = (template_count, weapon_count, armor_count, orphan_count)
    if actual not in EXPECTED_COVERAGE:
        raise RuntimeError(
            f"{path}: unexpected Temper template coverage {actual}, "
            f"expected one of {sorted(EXPECTED_COVERAGE)}"
        )
    return template_count, weapon_count, armor_count


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
        template_count, weapon_count, armor_count = _validate_catalogue(connection, path)
        caps_before = dict(
            connection.execute(
                "SELECT max_enchant_scale_id, COUNT(*) FROM items "
                "WHERE max_enchant_scale_id IN (?, ?) GROUP BY max_enchant_scale_id",
                (STALE_CAP, RETAIL_CAP),
            )
        )
        unexpected_caps = connection.execute(
            "SELECT max_enchant_scale_id, COUNT(*) FROM items "
            "WHERE max_enchant_scale_id > 0 AND max_enchant_scale_id NOT IN (?, ?) "
            "GROUP BY max_enchant_scale_id",
            (STALE_CAP, RETAIL_CAP),
        ).fetchall()
        if unexpected_caps:
            raise RuntimeError(f"{path}: unexpected positive Temper caps {unexpected_caps}")
        if caps_before not in (
            {STALE_CAP: template_count},
            {RETAIL_CAP: template_count},
        ):
            raise RuntimeError(f"{path}: mixed or incomplete Temper caps {caps_before}")

        connection.execute(
            "UPDATE items SET max_enchant_scale_id = ? WHERE max_enchant_scale_id = ?",
            (RETAIL_CAP, STALE_CAP),
        )
        caps_after = dict(
            connection.execute(
                "SELECT max_enchant_scale_id, COUNT(*) FROM items "
                "WHERE max_enchant_scale_id > 0 GROUP BY max_enchant_scale_id"
            )
        )
        if caps_after != {RETAIL_CAP: template_count}:
            raise RuntimeError(f"{path}: post-patch Temper caps are {caps_after}")
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
    print(f"  templates: {template_count} ({weapon_count} weapons, {armor_count} armors)")
    print(f"  cap:       {next(iter(caps_before))} -> {RETAIL_CAP}")
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
