#!/usr/bin/env python3
"""Enable the exact AA10 r575 merchant goods restored by the server policy.

The Returns client builds merchant pages from ``merchant_goods.enable`` in its
embedded ``game/db/compact.sqlite3``.  The server-side allowlist remains the
authority for purchase validation; this patch exposes only the same nine rows
in the client catalog.  Backups and reinsertion into ``game_pak`` are the
caller's responsibility.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path


EXPECTED_GOODS: tuple[tuple[int, int, int, int, int, int, int, int], ...] = (
    # id, merchant_pack_id, item_id, grade_id, view_order, cost,
    # purchase_type_id, purchase_limit
    (8237, 119, 47868, 0, 103, 0, 1, 0),
    (8238, 119, 47869, 0, 102, 0, 1, 0),
    (8239, 120, 47868, 0, 103, 0, 1, 0),
    (8240, 120, 47869, 0, 102, 0, 1, 0),
    (8341, 119, 51185, 0, 101, 0, 1, 0),
    (8342, 120, 51185, 0, 101, 0, 1, 0),
    (8430, 119, 53424, 0, 101, 0, 1, 0),
    (8431, 120, 53424, 0, 101, 0, 1, 0),
    (8511, 145, 54335, 3, 100, 0, 1, 0),
)

TARGET_IDS = tuple(row[0] for row in EXPECTED_GOODS)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def quick_check(connection: sqlite3.Connection, path: Path, phase: str) -> None:
    result = connection.execute("PRAGMA quick_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError(f"{path}: quick_check failed {phase}: {result}")


def read_targets(connection: sqlite3.Connection) -> list[tuple]:
    placeholders = ",".join("?" for _ in TARGET_IDS)
    return connection.execute(
        "SELECT id, merchant_pack_id, item_id, grade_id, enable, view_order, "
        "cost, purchase_type_id, purchase_limit FROM merchant_goods "
        f"WHERE id IN ({placeholders}) ORDER BY id",
        TARGET_IDS,
    ).fetchall()


def validate_targets(path: Path, rows: list[tuple]) -> None:
    identity = tuple(
        (row[0], row[1], row[2], row[3], row[5], row[6], row[7], row[8])
        for row in rows
    )
    if identity != EXPECTED_GOODS:
        raise RuntimeError(f"{path}: unexpected AA10 merchant-good set: {identity}")

    invalid_states = [(row[0], row[4]) for row in rows if row[4] not in ("f", "t")]
    if invalid_states:
        raise RuntimeError(f"{path}: unexpected enable states: {invalid_states}")


def patch_database(path: Path, apply_changes: bool) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)

    before_size = path.stat().st_size
    before_hash = sha256(path)
    connection = sqlite3.connect(path)
    try:
        quick_check(connection, path, "before patch")
        connection.execute("BEGIN IMMEDIATE")
        rows = read_targets(connection)
        validate_targets(path, rows)
        disabled_ids = [row[0] for row in rows if row[4] == "f"]
        unrelated_before = connection.execute(
            "SELECT * FROM merchant_goods WHERE id NOT IN "
            f"({','.join('?' for _ in TARGET_IDS)}) ORDER BY id",
            TARGET_IDS,
        ).fetchall()

        if apply_changes and disabled_ids:
            placeholders = ",".join("?" for _ in disabled_ids)
            cursor = connection.execute(
                f"UPDATE merchant_goods SET enable = 't' "
                f"WHERE id IN ({placeholders}) AND enable = 'f'",
                disabled_ids,
            )
            if cursor.rowcount != len(disabled_ids):
                raise RuntimeError(
                    f"{path}: expected {len(disabled_ids)} updates, got {cursor.rowcount}"
                )

        after_rows = read_targets(connection)
        validate_targets(path, after_rows)
        if apply_changes and any(row[4] != "t" for row in after_rows):
            raise RuntimeError(f"{path}: not every approved merchant good is enabled")

        unrelated_after = connection.execute(
            "SELECT * FROM merchant_goods WHERE id NOT IN "
            f"({','.join('?' for _ in TARGET_IDS)}) ORDER BY id",
            TARGET_IDS,
        ).fetchall()
        if unrelated_after != unrelated_before:
            raise RuntimeError(f"{path}: an unrelated merchant_good changed")

        quick_check(connection, path, "after patch")
        if apply_changes:
            connection.commit()
        else:
            connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    after_size = path.stat().st_size
    if after_size != before_size:
        raise RuntimeError(f"{path}: size changed from {before_size} to {after_size}")

    print(path)
    print(f"  approved goods:   {len(EXPECTED_GOODS)}")
    print(f"  disabled before:  {len(disabled_ids)}")
    print(f"  action:           {'applied' if apply_changes else 'dry run'}")
    print(f"  before SHA-256:   {before_hash}")
    print(f"  after SHA-256:    {sha256(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enable the exact AA10 r575 merchant catalog allowlist safely."
    )
    parser.add_argument("databases", nargs="+", type=Path)
    parser.add_argument(
        "--apply", action="store_true", help="commit the validated f -> t updates"
    )
    args = parser.parse_args()

    for database in args.databases:
        patch_database(database.resolve(), args.apply)
    if not args.apply:
        print("DRY RUN: no database changes were committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
