#!/usr/bin/env python3
"""Patch the stale AA10 r575 Hiram synthesis grade caps in compact.sqlite3.

The shipped projection leaves every Hiram category at Celestial (grade 7), while
the next awakening routes require Divine/Epic/Mythic/Eternal as appropriate.
This tool validates every expected row and updates the database transactionally.
Backups are intentionally the caller's responsibility.

For the retail client, patching ``game/db/compact.sqlite3`` alone is insufficient:
``game_pak`` has priority. Reinsert the same-size patched SQLite as
``game/db/compact.sqlite3`` with the verified ``Tools/PakEntryReplace`` utility.
"""

from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path


CAPS: dict[int, tuple[int, ...]] = {
    8: tuple(range(508, 520)),
    9: tuple(range(524, 536)),
    11: tuple(range(606, 618)),
    12: tuple(range(699, 711)) + tuple(range(826, 838)),
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

    before_hash = sha256(path)
    connection = sqlite3.connect(path)
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError(f"{path}: quick_check failed before patch")

        connection.execute("BEGIN IMMEDIATE")
        for desired_grade, category_ids in CAPS.items():
            placeholders = ",".join("?" for _ in category_ids)
            rows = connection.execute(
                f"SELECT id, max_evolving_grade FROM item_rnd_attr_categories "
                f"WHERE id IN ({placeholders}) ORDER BY id",
                category_ids,
            ).fetchall()
            if len(rows) != len(category_ids):
                raise RuntimeError(
                    f"{path}: expected {len(category_ids)} categories for grade "
                    f"{desired_grade}, found {len(rows)}"
                )
            unexpected = [(row_id, cap) for row_id, cap in rows if cap not in (7, desired_grade)]
            if unexpected:
                raise RuntimeError(f"{path}: unexpected existing caps {unexpected}")

            connection.execute(
                f"UPDATE item_rnd_attr_categories SET max_evolving_grade = ? "
                f"WHERE id IN ({placeholders})",
                (desired_grade, *category_ids),
            )

        for desired_grade, category_ids in CAPS.items():
            placeholders = ",".join("?" for _ in category_ids)
            rows = connection.execute(
                f"SELECT id, max_evolving_grade FROM item_rnd_attr_categories "
                f"WHERE id IN ({placeholders}) ORDER BY id",
                category_ids,
            ).fetchall()
            if any(cap != desired_grade for _, cap in rows):
                raise RuntimeError(f"{path}: post-patch verification failed for grade {desired_grade}")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError(f"{path}: quick_check failed after patch")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(f"{path}")
    print(f"  before: {before_hash}")
    print(f"  after:  {sha256(path)}")


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {Path(sys.argv[0]).name} COMPACT_SQLITE3 [...]", file=sys.stderr)
        return 2
    for argument in sys.argv[1:]:
        patch_database(Path(argument).resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
