#!/usr/bin/env python3
"""Clone or move one complete AA10 Account Attendance month in a runtime compact.sqlite3.

This intentionally refuses to overwrite an existing target month. Retail/forensic baselines must
never be passed here; use it only on explicitly named operational client/server compact databases.
The ``--move-source`` mode is intended for a same-size replacement of the compact embedded in
``game_pak``: it changes only the source rows' year/month keys and verifies that neither the SQLite
page count nor the file length changed.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sqlite3
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--source-year", type=int, required=True)
    parser.add_argument("--source-month", type=int, choices=range(1, 13), required=True)
    parser.add_argument("--target-year", type=int, required=True)
    parser.add_argument("--target-month", type=int, choices=range(1, 13), required=True)
    parser.add_argument(
        "--move-source",
        action="store_true",
        help="move the source rows instead of inserting copies; guarantees a size-preserving file",
    )
    parser.add_argument(
        "--normal-days",
        type=int,
        choices=(28, 31),
        default=28,
        help="number of visible daily rewards; AA10 r575 renders a native 4x7 grid",
    )
    parser.add_argument(
        "--trim-existing-target",
        action="store_true",
        help="trim an existing 31+4 target to the requested native layout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database = args.database.resolve(strict=True)
    if database.name.lower() != "compact.sqlite3":
        raise SystemExit(f"refusing non-compact target: {database}")
    if (args.source_year, args.source_month) == (args.target_year, args.target_month):
        raise SystemExit("source and target campaign must differ")

    backup_label = "pre-attendance-native28" if args.trim_existing_target else "pre-attendance"
    backup = database.with_name(
        f"{database.name}.{backup_label}-{args.target_year:04d}{args.target_month:02d}.bak"
    )
    before_hash = sha256(database)
    before_size = database.stat().st_size
    connection = sqlite3.connect(database)
    try:
        before_page_count = connection.execute("PRAGMA page_count").fetchone()[0]
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(account_attendance_rewards)")
        ]
        expected = [
            "id", "name", "comment", "year", "month", "day_count", "item_id",
            "item_grade_id", "item_count", "additional_reward",
        ]
        if columns != expected:
            raise RuntimeError(f"unexpected account_attendance_rewards schema: {columns}")

        source_rows_with_ids = connection.execute(
            """
            SELECT id, name, comment, day_count, item_id, item_grade_id, item_count,
                   additional_reward
            FROM account_attendance_rewards
            WHERE year = ? AND month = ?
            ORDER BY day_count, id
            """,
            (args.source_year, args.source_month),
        ).fetchall()
        if len(source_rows_with_ids) != 35:
            raise RuntimeError(
                f"source campaign must contain 35 rows, found {len(source_rows_with_ids)}"
            )
        normal_days = [
            row[3]
            for row in source_rows_with_ids
            if str(row[7]).lower() not in {"t", "1", "true"}
        ]
        additional_days = [
            row[3]
            for row in source_rows_with_ids
            if str(row[7]).lower() in {"t", "1", "true"}
        ]
        if normal_days != list(range(1, 32)) or additional_days != [7, 14, 21, 28]:
            raise RuntimeError(
                f"source campaign is not the expected 31+4 layout: normal={normal_days}, "
                f"additional={additional_days}"
            )
        selected_rows = [
            row
            for row in source_rows_with_ids
            if str(row[7]).lower() in {"t", "1", "true"} or row[3] <= args.normal_days
        ]
        expected_target_count = args.normal_days + 4

        target_count = connection.execute(
            "SELECT COUNT(*) FROM account_attendance_rewards WHERE year = ? AND month = ?",
            (args.target_year, args.target_month),
        ).fetchone()[0]
        if target_count:
            if target_count == expected_target_count:
                print(
                    f"already present: {database} target={args.target_year:04d}-{args.target_month:02d} "
                    f"rows={target_count} sha256={before_hash}"
                )
                return 0
            if not (
                args.trim_existing_target
                and target_count == 35
                and expected_target_count == 32
            ):
                raise RuntimeError(
                    f"target campaign exists but is incomplete/unexpected: rows={target_count}"
                )

        if backup.exists():
            if sha256(backup) != before_hash:
                raise RuntimeError(f"existing backup does not match current database: {backup}")
        else:
            shutil.copy2(database, backup)

        if target_count:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM account_attendance_rewards
                    WHERE year = ? AND month = ? AND day_count > ?
                      AND lower(CAST(additional_reward AS TEXT)) NOT IN ('t', '1', 'true')
                    """,
                    (args.target_year, args.target_month, args.normal_days),
                )
            if cursor.rowcount != target_count - expected_target_count:
                raise RuntimeError(
                    f"expected to trim {target_count - expected_target_count} rows, "
                    f"trimmed {cursor.rowcount}"
                )
        elif args.move_source:
            selected_ids = [row[0] for row in selected_rows]
            placeholders = ",".join("?" for _ in selected_ids)
            with connection:
                cursor = connection.execute(
                    f"""
                    UPDATE account_attendance_rewards
                    SET year = ?, month = ?
                    WHERE id IN ({placeholders})
                    """,
                    (
                        args.target_year,
                        args.target_month,
                        *selected_ids,
                    ),
                )
            if cursor.rowcount != expected_target_count:
                raise RuntimeError(
                    f"expected to move {expected_target_count} rows, moved {cursor.rowcount}"
                )
        else:
            next_id = connection.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM account_attendance_rewards"
            ).fetchone()[0]
            with connection:
                connection.executemany(
                    """
                    INSERT INTO account_attendance_rewards
                        (id, name, comment, year, month, day_count, item_id,
                         item_grade_id, item_count, additional_reward)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            next_id + index,
                            name,
                            comment,
                            args.target_year,
                            args.target_month,
                            day_count,
                            item_id,
                            grade,
                            count,
                            additional,
                        )
                        for index, (_, name, comment, day_count, item_id, grade, count, additional)
                        in enumerate(selected_rows)
                    ],
                )

        check = connection.execute("PRAGMA quick_check").fetchone()[0]
        inserted = connection.execute(
            "SELECT COUNT(*) FROM account_attendance_rewards WHERE year = ? AND month = ?",
            (args.target_year, args.target_month),
        ).fetchone()[0]
        if check != "ok" or inserted != expected_target_count:
            raise RuntimeError(f"post-write validation failed: quick_check={check}, rows={inserted}")
        if args.move_source or args.trim_existing_target:
            source_remaining = connection.execute(
                "SELECT COUNT(*) FROM account_attendance_rewards WHERE year = ? AND month = ?",
                (args.source_year, args.source_month),
            ).fetchone()[0]
            after_page_count = connection.execute("PRAGMA page_count").fetchone()[0]
            after_size = database.stat().st_size
            expected_source_remaining = 35 - expected_target_count if args.move_source else 35
            if source_remaining != expected_source_remaining:
                raise RuntimeError(
                    f"source campaign has {source_remaining} rows; "
                    f"expected {expected_source_remaining}"
                )
            if after_page_count != before_page_count or after_size != before_size:
                raise RuntimeError(
                    "move was not size preserving: "
                    f"pages={before_page_count}->{after_page_count}, bytes={before_size}->{after_size}"
                )
    finally:
        connection.close()

    print(
        f"patched: {database}\n"
        f"backup:  {backup}\n"
        f"mode:    "
        f"{'trim existing target' if args.trim_existing_target else 'move (size preserving)' if args.move_source else 'clone'}\n"
        f"source:  {args.source_year:04d}-{args.source_month:02d} (35 rows)\n"
        f"target:  {args.target_year:04d}-{args.target_month:02d} "
        f"({expected_target_count} rows: {args.normal_days}+4)\n"
        f"sha256 before={before_hash}\n"
        f"sha256 after ={sha256(database)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
