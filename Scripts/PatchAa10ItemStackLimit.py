#!/usr/bin/env python3
"""Raise audited AA10 r575 item stack caps of 1,000 or 9,999 to 99,999.

The item template itself is the shared contract: the retail client reads
``items.max_stack_size`` from its embedded compact SQLite and AAEmu loads the
same column from its runtime database.  This builder accepts only the two
audited r575 row identities (client projection and authoritative server
projection), recognizes the previous 1,000-only patch, rejects any other
mixed/partial state, and changes no other stack caps.

Backups and game_pak replacement are deliberately handled by the PowerShell
applicator.  The default mode is a read-only dry run.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path


RETAIL_STACK_LIMITS = (1_000, 9_999)
PATCHED_STACK_LIMIT = 99_999


@dataclass(frozen=True)
class StackProfile:
    name: str
    retail_1000_count: int
    retail_1000_ids_sha256: str
    retail_9999_count: int
    retail_9999_ids_sha256: str
    combined_count: int
    combined_ids_sha256: str


PROFILES: tuple[StackProfile, ...] = (
    StackProfile(
        name="aa10-r575-client-compact",
        retail_1000_count=2_476,
        retail_1000_ids_sha256="90B420D1441D5CD34FB9FCB3C781019533FEF6B16FBD4D4D5701A1B547197B89",
        retail_9999_count=55,
        retail_9999_ids_sha256="41A871FCBDA7D7053D50E777478C5F1C874574DAE8DDA906305597F4E83C9D64",
        combined_count=2_531,
        combined_ids_sha256="14C1BA767C5E3A077FCCDB177C146423DFFB493502B8B7B0CC63E7B68D6223BE",
    ),
    StackProfile(
        name="aa10-r575-authoritative-runtime",
        retail_1000_count=2_712,
        retail_1000_ids_sha256="282D2E45912E452C7BFA551A79C3A8C8999C0BFA375572F7DD3A442CC68E912D",
        retail_9999_count=59,
        retail_9999_ids_sha256="B66C7F88F4C89BAC7A26AC3222B793ACFB1B657C5C17E1E2200F75F6F6D2083A",
        combined_count=2_771,
        combined_ids_sha256="8146AEA01F997FBF357EB3299F8D7F693ECDFAD348B9A37F3A255ADA61D28C8D",
    ),
)


@dataclass(frozen=True)
class PatchResult:
    profile: str
    target_rows: int
    changed_rows: int
    applied: bool
    before_hash: str
    after_hash: str
    size_preserved: bool


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def ids_sha256(ids: list[int]) -> str:
    payload = ",".join(str(item_id) for item_id in ids).encode("ascii")
    return hashlib.sha256(payload).hexdigest().upper()


def quick_check(connection: sqlite3.Connection, path: Path, phase: str) -> None:
    result = connection.execute("PRAGMA quick_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError(f"{path}: quick_check failed {phase}: {result}")


def validate_schema(connection: sqlite3.Connection, path: Path) -> None:
    columns = connection.execute("PRAGMA table_info(items)").fetchall()
    by_name = {str(column[1]): column for column in columns}
    if "id" not in by_name or "max_stack_size" not in by_name:
        raise RuntimeError(f"{path}: AA10 items schema is missing required columns")
    if int(by_name["id"][5]) != 1:
        raise RuntimeError(f"{path}: items.id is not the primary key")
    if int(by_name["max_stack_size"][3]) != 1:
        raise RuntimeError(f"{path}: items.max_stack_size is unexpectedly nullable")


def _signature(ids: list[int]) -> tuple[int, str]:
    return len(ids), ids_sha256(ids)


def resolve_profile(connection: sqlite3.Connection, path: Path) -> tuple[StackProfile, list[int], int]:
    rows = connection.execute(
        "SELECT id, max_stack_size FROM items "
        "WHERE max_stack_size IN (?, ?, ?) ORDER BY id",
        (*RETAIL_STACK_LIMITS, PATCHED_STACK_LIMIT),
    ).fetchall()
    ids = [int(row[0]) for row in rows]
    signature = _signature(ids)
    profile = next(
        (
            candidate
            for candidate in PROFILES
            if (candidate.combined_count, candidate.combined_ids_sha256) == signature
        ),
        None,
    )
    if profile is None:
        raise RuntimeError(
            f"{path}: unknown AA10 stack row identity "
            f"(count={signature[0]}, ids_sha256={signature[1]})"
        )

    by_limit = {
        limit: [int(item_id) for item_id, value in rows if int(value) == limit]
        for limit in (*RETAIL_STACK_LIMITS, PATCHED_STACK_LIMIT)
    }
    sig_1000 = _signature(by_limit[1_000])
    sig_9999 = _signature(by_limit[9_999])
    sig_patched = _signature(by_limit[PATCHED_STACK_LIMIT])
    empty = _signature([])
    original_1000 = (profile.retail_1000_count, profile.retail_1000_ids_sha256)
    original_9999 = (profile.retail_9999_count, profile.retail_9999_ids_sha256)
    combined = (profile.combined_count, profile.combined_ids_sha256)

    is_retail = sig_1000 == original_1000 and sig_9999 == original_9999 and sig_patched == empty
    is_previous_v1 = sig_1000 == empty and sig_9999 == original_9999 and sig_patched == original_1000
    is_fully_patched = sig_1000 == empty and sig_9999 == empty and sig_patched == combined
    if not (is_retail or is_previous_v1 or is_fully_patched):
        raise RuntimeError(
            f"{path}: partial stack patch detected "
            f"(1000={sig_1000[0]}, 9999={sig_9999[0]}, 99999={sig_patched[0]})"
        )

    changed_rows = sig_1000[0] + sig_9999[0]
    return profile, ids, changed_rows


def patch_database(path: Path, apply_changes: bool) -> PatchResult:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)

    before_hash = sha256(path)
    before_size = path.stat().st_size
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        quick_check(connection, path, "before stack patch")
        validate_schema(connection, path)
        connection.execute("BEGIN IMMEDIATE")

        profile, target_ids, changed_rows = resolve_profile(connection, path)
        before_rows = connection.execute(
            "SELECT id, max_stack_size FROM items ORDER BY id"
        ).fetchall()

        if apply_changes and changed_rows:
            cursor = connection.execute(
                "UPDATE items SET max_stack_size = ? WHERE max_stack_size = ?",
                (PATCHED_STACK_LIMIT, RETAIL_STACK_LIMITS[0]),
            )
            cursor_9999 = connection.execute(
                "UPDATE items SET max_stack_size = ? WHERE max_stack_size = ?",
                (PATCHED_STACK_LIMIT, RETAIL_STACK_LIMITS[1]),
            )
            updated_rows = cursor.rowcount + cursor_9999.rowcount
            if updated_rows != changed_rows:
                raise RuntimeError(
                    f"{path}: expected {changed_rows} updates, got {updated_rows}"
                )

        after_rows = connection.execute(
            "SELECT id, max_stack_size FROM items ORDER BY id"
        ).fetchall()
        if apply_changes:
            target_id_set = set(target_ids)
            expected_rows = [
                (
                    int(item_id),
                    PATCHED_STACK_LIMIT if int(item_id) in target_id_set else int(limit),
                )
                for item_id, limit in before_rows
            ]
            normalized_after = [(int(item_id), int(limit)) for item_id, limit in after_rows]
            if normalized_after != expected_rows:
                raise RuntimeError(f"{path}: a non-target stack limit changed")

            post_profile, _, post_retail_rows = resolve_profile(connection, path)
            if post_profile != profile or post_retail_rows != 0:
                raise RuntimeError(f"{path}: post-patch stack state is invalid")

        quick_check(connection, path, "after stack patch")
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
        raise RuntimeError(
            f"{path}: SQLite size changed from {before_size} to {after_size}; "
            "refusing a non-size-preserving PAK candidate"
        )

    after_hash = sha256(path)
    return PatchResult(
        profile=profile.name,
        target_rows=profile.combined_count,
        changed_rows=changed_rows,
        applied=apply_changes,
        before_hash=before_hash,
        after_hash=after_hash,
        size_preserved=after_size == before_size,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Raise audited AA10 r575 item stack caps from 1,000/9,999 to 99,999."
    )
    parser.add_argument("database", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="commit the validated update (default is a read-only dry run)",
    )
    args = parser.parse_args()

    result = patch_database(args.database, args.apply)
    print(f"Database:          {args.database.resolve()}")
    print(f"Profile:           {result.profile}")
    print(f"Target rows:       {result.target_rows}")
    print(f"Rows to change:    {result.changed_rows}")
    print(f"Target limit:      {PATCHED_STACK_LIMIT}")
    print(f"Action:            {'applied' if result.applied else 'dry run'}")
    print(f"Size preserved:    {'yes' if result.size_preserved else 'no'}")
    print(f"Before SHA-256:    {result.before_hash}")
    print(f"After SHA-256:     {result.after_hash}")
    if not result.applied:
        print("DRY RUN: no database changes were committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
