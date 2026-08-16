#!/usr/bin/env python3
"""Validate or restore the eight native r575 Lunagem chance profiles.

The retail compact projection can contain the correct catalogue and metadata while leaving every
socket probability at zero. Values below come from the complete 10.0.2.13 r575
game_decrypted.sqlite3. The command fails closed if it encounters any third state.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from pathlib import Path


NATIVE_PROFILES = {
    1: ((0, 10000, 5000, 5000, 5000, 5000, 5000, 5000, 5000, 5000), "t", 1),
    2: ((0, 10000, 7500, 6500, 5500, 5000, 5000, 5000, 5000, 5000), "t", 1),
    3: ((0, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000), "t", 2),
    4: ((0, 10000, 6000, 5000, 3360, 1680, 840, 420, 380, 340), "f", 3),
    5: ((0, 10000, 9500, 8500, 7500, 6500, 5500, 5000, 5000, 5000), "t", 1),
    6: ((0, 10000, 8500, 7500, 6500, 5500, 5000, 5000, 5000, 5000), "t", 1),
    7: ((0, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000), "f", 100),
    8: ((0, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000), "f", 106),
}

SOCKET_COLUMNS = tuple(f"socket{index}" for index in range(10))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path, help="Path to the AA10 compact.sqlite3")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Restore profiles whose ten probability columns are all zero",
    )
    args = parser.parse_args()

    database = args.database.resolve(strict=True)
    before_hash = sha256(database)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    changed: list[int] = []

    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite quick_check failed before validation")

        columns = {row[1] for row in connection.execute("PRAGMA table_info(item_socket_chances)")}
        required = {"id", "fail_break", "cost_ratio", *SOCKET_COLUMNS}
        if not required.issubset(columns):
            raise RuntimeError(f"item_socket_chances is missing columns: {sorted(required - columns)}")

        select_columns = ", ".join(("id", *SOCKET_COLUMNS, "fail_break", "cost_ratio"))
        rows = {
            int(row["id"]): row
            for row in connection.execute(
                f"SELECT {select_columns} FROM item_socket_chances ORDER BY id"
            )
        }
        if set(rows) != set(NATIVE_PROFILES):
            raise RuntimeError(
                f"Expected profiles {sorted(NATIVE_PROFILES)}, found {sorted(rows)}"
            )

        connection.execute("BEGIN IMMEDIATE")
        for profile_id, (expected_chances, expected_fail_break, expected_cost_ratio) in NATIVE_PROFILES.items():
            row = rows[profile_id]
            fail_break = str(row["fail_break"]).lower()
            cost_ratio = int(row["cost_ratio"])
            if fail_break != expected_fail_break or cost_ratio != expected_cost_ratio:
                raise RuntimeError(
                    f"Profile {profile_id} metadata differs: "
                    f"fail_break={fail_break}, cost_ratio={cost_ratio}"
                )

            current = tuple(int(row[column]) for column in SOCKET_COLUMNS)
            if current == expected_chances:
                continue
            if current != (0,) * len(SOCKET_COLUMNS):
                raise RuntimeError(
                    f"Profile {profile_id} has unexpected partial probabilities: {current}"
                )
            if not args.apply:
                raise RuntimeError(
                    f"Profile {profile_id} is zeroed; rerun with --apply to restore it"
                )

            assignments = ", ".join(f"{column} = ?" for column in SOCKET_COLUMNS)
            connection.execute(
                f"UPDATE item_socket_chances SET {assignments} WHERE id = ?",
                (*expected_chances, profile_id),
            )
            changed.append(profile_id)

        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite quick_check failed after validation")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    after_hash = sha256(database)
    action = "restored" if changed else "validated"
    print(f"{action}: {database}")
    print(f"profiles changed: {changed}")
    print(f"sha256 before: {before_hash}")
    print(f"sha256 after:  {after_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
