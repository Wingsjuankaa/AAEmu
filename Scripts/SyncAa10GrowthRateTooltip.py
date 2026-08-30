#!/usr/bin/env python3
"""Keep AA10 r575 client growth tooltips aligned with server GrowthRate.

The client calculates a doodad's tooltip by combining the server-provided
remaining time for the current phase with future ``doodad_func_growths.delay``
values from its local ``compact.sqlite3``.  AAEmu scales the server phases but
the retail client data is unscaled, so this tool regenerates only that delay
column from an immutable retail database and the effective World.json value.

The synchronization is intentionally derived from the retail baseline on every
run.  It never divides the already-patched client values, which makes changing
GrowthRate and repeated launches deterministic and idempotent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path


TABLE = "doodad_func_growths"
MIN_RATE = 1.0
MAX_RATE = 1000.0


@dataclass(frozen=True)
class SyncResult:
    rate: float
    row_count: int
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


def quick_check(connection: sqlite3.Connection, path: Path, phase: str) -> None:
    result = connection.execute("PRAGMA quick_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError(f"{path}: quick_check failed {phase}: {result}")


def read_growth_rate(world_config: Path) -> float:
    if not world_config.is_file():
        raise FileNotFoundError(world_config)

    document = json.loads(world_config.read_text(encoding="utf-8-sig"))
    try:
        rate = float(document["World"]["GrowthRate"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(
            f"{world_config}: World.GrowthRate is missing or invalid"
        ) from error

    if not math.isfinite(rate) or not MIN_RATE <= rate <= MAX_RATE:
        raise RuntimeError(
            f"{world_config}: GrowthRate {rate!r} must be between "
            f"{MIN_RATE:g} and {MAX_RATE:g}"
        )
    return rate


def scaled_delay(retail_delay: int, rate: float) -> int:
    if retail_delay < 0:
        raise RuntimeError(f"negative retail growth delay: {retail_delay}")
    # The compact schema stores integer milliseconds.  Truncation mirrors the
    # millisecond representation used by the client and differs from AAEmu's
    # double-precision scheduled time by less than one millisecond.
    return math.floor(retail_delay / rate)


def read_baseline_rows(database: Path, rate: float) -> list[tuple[int, int]]:
    if not database.is_file():
        raise FileNotFoundError(database)

    uri = database.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        quick_check(connection, database, "while reading retail baseline")
        rows = connection.execute(
            f"SELECT id, delay FROM {TABLE} ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        raise RuntimeError(f"{database}: {TABLE} is empty")
    if any(row_id is None or delay is None for row_id, delay in rows):
        raise RuntimeError(f"{database}: {TABLE} contains null ids or delays")

    return [(int(row_id), scaled_delay(int(delay), rate)) for row_id, delay in rows]


def preserve_sqlite_size(database: Path, expected_size: int, schema_version: int) -> None:
    connection = sqlite3.connect(database, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        if expected_size % page_size != 0:
            raise RuntimeError(
                f"{database}: original size {expected_size} is not page-aligned to {page_size}"
            )
        expected_pages = expected_size // page_size
        current_pages = int(connection.execute("PRAGMA page_count").fetchone()[0])
        if current_pages > expected_pages:
            raise RuntimeError(
                f"{database}: vacuumed database has too many pages "
                f"({current_pages} > {expected_pages})"
            )

        connection.execute(f"PRAGMA schema_version = {schema_version}")
    finally:
        connection.close()

    if current_pages < expected_pages:
        extra_pages = expected_pages - current_pages
        leaf_capacity = (page_size // 4) - 2
        page_numbers = list(range(current_pages + 1, expected_pages + 1))
        groups: list[tuple[int, list[int]]] = []
        while page_numbers:
            trunk = page_numbers.pop(0)
            leaves = page_numbers[:leaf_capacity]
            del page_numbers[:leaf_capacity]
            groups.append((trunk, leaves))

        with database.open("r+b") as output:
            header = bytearray(output.read(100))
            if header[:16] != b"SQLite format 3\x00":
                raise RuntimeError(f"{database}: invalid SQLite header")
            if struct.unpack(">I", header[32:36])[0] != 0:
                raise RuntimeError(f"{database}: VACUUM left an unexpected freelist")

            output.truncate(expected_size)
            for index, (trunk, leaves) in enumerate(groups):
                next_trunk = groups[index + 1][0] if index + 1 < len(groups) else 0
                page = bytearray(page_size)
                struct.pack_into(">II", page, 0, next_trunk, len(leaves))
                for leaf_index, leaf_page in enumerate(leaves):
                    struct.pack_into(">I", page, 8 + leaf_index * 4, leaf_page)
                output.seek((trunk - 1) * page_size)
                output.write(page)

            change_counter = (struct.unpack(">I", header[24:28])[0] + 1) & 0xFFFFFFFF
            struct.pack_into(">I", header, 24, change_counter)
            struct.pack_into(">I", header, 28, expected_pages)
            struct.pack_into(">I", header, 32, groups[0][0])
            struct.pack_into(">I", header, 36, extra_pages)
            struct.pack_into(">I", header, 92, change_counter)
            output.seek(0)
            output.write(header)

    verification = sqlite3.connect(database, timeout=30)
    try:
        page_count = int(verification.execute("PRAGMA page_count").fetchone()[0])
        if page_count != expected_pages:
            raise RuntimeError(
                f"{database}: page count {page_count} does not match {expected_pages}"
            )
        quick_check(verification, database, "after allocating valid freelist pages")
    finally:
        verification.close()

    if database.stat().st_size != expected_size:
        raise RuntimeError(
            f"{database}: physical size {database.stat().st_size} does not match "
            f"SQLite page size {expected_size}"
        )


def sync_database(
    world_config: Path,
    retail_database: Path,
    client_database: Path,
    apply_changes: bool,
    preserve_size: bool = False,
) -> SyncResult:
    world_config = world_config.resolve()
    retail_database = retail_database.resolve()
    client_database = client_database.resolve()

    if retail_database == client_database:
        raise RuntimeError("retail baseline and client target must be different files")
    if not client_database.is_file():
        raise FileNotFoundError(client_database)

    rate = read_growth_rate(world_config)
    expected_rows = read_baseline_rows(retail_database, rate)
    expected_by_id = dict(expected_rows)
    before_hash = sha256(client_database)
    before_size = client_database.stat().st_size

    connection = sqlite3.connect(client_database, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout = 30000")
        quick_check(connection, client_database, "before synchronization")
        schema_version = int(connection.execute("PRAGMA schema_version").fetchone()[0])
        connection.execute("BEGIN IMMEDIATE")

        actual_rows = connection.execute(
            f"SELECT id, delay FROM {TABLE} ORDER BY id"
        ).fetchall()
        actual_ids = [int(row_id) for row_id, _ in actual_rows]
        expected_ids = [row_id for row_id, _ in expected_rows]
        if actual_ids != expected_ids:
            raise RuntimeError(
                f"{client_database}: {TABLE} row identity differs from retail baseline"
            )

        updates = [
            (expected_by_id[int(row_id)], int(row_id))
            for row_id, current_delay in actual_rows
            if int(current_delay) != expected_by_id[int(row_id)]
        ]
        if apply_changes and updates:
            connection.executemany(
                f"UPDATE {TABLE} SET delay = ? WHERE id = ?",
                updates,
            )

        verification_rows = connection.execute(
            f"SELECT id, delay FROM {TABLE} ORDER BY id"
        ).fetchall()
        if apply_changes:
            normalized = [(int(row_id), int(delay)) for row_id, delay in verification_rows]
            if normalized != expected_rows:
                raise RuntimeError(
                    f"{client_database}: post-update growth delays do not match rate {rate:g}"
                )

        quick_check(connection, client_database, "after synchronization")
        if apply_changes:
            connection.commit()
        else:
            connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    if apply_changes and preserve_size and updates:
        vacuum = sqlite3.connect(client_database, timeout=30)
        try:
            vacuum.execute("PRAGMA busy_timeout = 30000")
            vacuum.execute("VACUUM")
        finally:
            vacuum.close()

        preserve_sqlite_size(client_database, before_size, schema_version)

        verification = sqlite3.connect(
            client_database.resolve().as_uri() + "?mode=ro", uri=True
        )
        try:
            quick_check(verification, client_database, "after size preservation")
            final_rows = verification.execute(
                f"SELECT id, delay FROM {TABLE} ORDER BY id"
            ).fetchall()
            normalized = [(int(row_id), int(delay)) for row_id, delay in final_rows]
            if normalized != expected_rows:
                raise RuntimeError(
                    f"{client_database}: size-preserved growth delays do not match rate {rate:g}"
                )
        finally:
            verification.close()

        if client_database.stat().st_size != before_size:
            raise RuntimeError(
                f"{client_database}: failed to preserve exact size {before_size}"
            )

    after_hash = sha256(client_database)
    return SyncResult(
        rate=rate,
        row_count=len(expected_rows),
        changed_rows=len(updates),
        applied=apply_changes,
        before_hash=before_hash,
        after_hash=after_hash,
        size_preserved=preserve_size,
    )


def default_paths() -> tuple[Path, Path, Path]:
    repository_root = Path(__file__).resolve().parent.parent
    project_root = repository_root.parent.parent
    runtime_config = (
        repository_root
        / ".server_files"
        / "AAEmu.Game"
        / "Configurations"
        / "World.json"
    )
    versioned_config = repository_root / "AAEmu.Game" / "Configurations" / "World.json"
    world_config = runtime_config if runtime_config.is_file() else versioned_config
    retail_database = project_root / "data" / "sqlite" / "retail" / "compact.sqlite3"
    client_database = (
        project_root
        / "client"
        / "ArcheAge-Returns-10.0.2.13-r575"
        / "game"
        / "db"
        / "compact.sqlite3"
    )
    return world_config, retail_database, client_database


def main() -> int:
    default_config, default_baseline, default_client = default_paths()
    parser = argparse.ArgumentParser(
        description="Synchronize AA10 client growth tooltip delays with World.GrowthRate."
    )
    parser.add_argument("--world-config", type=Path, default=default_config)
    parser.add_argument("--retail-database", type=Path, default=default_baseline)
    parser.add_argument("--client-database", type=Path, default=default_client)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="commit the validated delay updates (default is a read-only dry run)",
    )
    parser.add_argument(
        "--preserve-size",
        action="store_true",
        help="vacuum and pad the result back to its original size for PAK replacement",
    )
    args = parser.parse_args()

    result = sync_database(
        args.world_config,
        args.retail_database,
        args.client_database,
        args.apply,
        args.preserve_size,
    )
    print(f"World config:      {args.world_config.resolve()}")
    print(f"Retail baseline:   {args.retail_database.resolve()}")
    print(f"Client database:   {args.client_database.resolve()}")
    print(f"GrowthRate:        {result.rate:g}")
    print(f"Growth rows:       {result.row_count}")
    print(f"Rows to change:    {result.changed_rows}")
    print(f"Action:            {'applied' if result.applied else 'dry run'}")
    print(f"Size preserved:    {'yes' if result.size_preserved else 'not requested'}")
    print(f"Before SHA-256:    {result.before_hash}")
    print(f"After SHA-256:     {result.after_hash}")
    if not result.applied:
        print("DRY RUN: no database changes were committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
