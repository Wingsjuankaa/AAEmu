#!/usr/bin/env python3
"""Build the AA8 native character runtime only after every authority gate passes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({quoted(table)})")
    }


def layout_sqlite_type(field_type: str) -> str:
    if field_type in ("38", "68", "40", "70"):
        return "INTEGER"
    if field_type == "60":
        return "REAL"
    if field_type == "78":
        return "TEXT"
    raise RuntimeError(f"unsupported native field layout {field_type!r}")


def main() -> int:
    options = parse_args()
    manifest = json.loads(options.manifest.read_text(encoding="utf-8"))
    data = json.loads(options.data.read_text(encoding="utf-8"))
    blockers = manifest.get("blockers", [])
    if blockers or not manifest.get("deployable", False):
        print(json.dumps({
            "built": False,
            "reason": "native authority gates are not closed",
            "blockers": blockers,
        }, indent=2, ensure_ascii=False))
        return 2

    expected_base = manifest["sources"]["runtime_compact"]["sha256"]
    actual_base = sha256(options.base_runtime)
    if actual_base != expected_base:
        raise RuntimeError(
            f"base runtime hash differs: expected {expected_base}, found {actual_base}"
        )

    options.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(options.base_runtime, options.output)
    connection = sqlite3.connect(options.output)
    try:
        with connection:
            for table, rows in data["tables"].items():
                classification = manifest["table_classifications"].get(table)
                if classification not in (
                    "native_authoritative_replacement",
                    "native_reference_closure",
                    "native_authoritative_empty",
                    "server_derived_accepted",
                    "server_derived_reference_closure",
                ):
                    raise RuntimeError(
                        f"{table}: unsupported classification {classification!r}"
                    )
                if rows:
                    columns = list(rows[0])
                elif classification == "native_authoritative_empty":
                    columns = list(
                        manifest["table_schemas"][table]["columns"]
                    )
                else:
                    raise RuntimeError(f"{table}: empty native table")
                existing = connection.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                if existing:
                    missing_columns = set(columns) - table_columns(connection, table)
                    if missing_columns:
                        if classification in (
                            "native_reference_closure",
                            "server_derived_reference_closure",
                        ):
                            raise RuntimeError(
                                f"{table}: base runtime misses columns "
                                f"{sorted(missing_columns)}"
                            )
                        connection.execute(f"DROP TABLE {quoted(table)}")
                        existing = None
                if existing:
                    if classification in (
                        "native_reference_closure",
                        "server_derived_reference_closure",
                    ):
                        key_column = manifest["table_schemas"].get(
                            table, {}
                        ).get("key_column", "id")
                        if key_column not in columns:
                            raise RuntimeError(
                                f"{table}: reference closure has no "
                                f"{key_column} column"
                            )
                        ids = [int(row[key_column]) for row in rows]
                        placeholders = ", ".join("?" for _ in ids)
                        connection.execute(
                            f"DELETE FROM {quoted(table)} "
                            f"WHERE {quoted(key_column)} IN ({placeholders})",
                            ids,
                        )
                    else:
                        connection.execute(f"DELETE FROM {quoted(table)}")
                if not existing:
                    if classification in (
                        "native_reference_closure",
                        "server_derived_reference_closure",
                    ):
                        raise RuntimeError(
                            f"{table}: cannot apply a closure to a missing table"
                        )
                    if rows:
                        definitions = ", ".join(
                            f"{quoted(column)} REAL"
                            if isinstance(rows[0][column], float)
                            else f"{quoted(column)} TEXT"
                            if isinstance(rows[0][column], str)
                            else f"{quoted(column)} INTEGER"
                            for column in columns
                        )
                    else:
                        layout = manifest["table_schemas"][table]["layout"]
                        definitions = ", ".join(
                            f"{quoted(column)} {layout_sqlite_type(field_type)}"
                            for column, field_type in zip(columns, layout)
                        )
                    connection.execute(
                        f"CREATE TABLE {quoted(table)} ({definitions})"
                    )
                names = ", ".join(quoted(column) for column in columns)
                values = ", ".join("?" for _ in columns)
                if rows:
                    connection.executemany(
                        f"INSERT INTO {quoted(table)} ({names}) VALUES ({values})",
                        ([row[column] for column in columns] for row in rows),
                    )

        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if quick != "ok" or integrity != "ok":
            raise RuntimeError(
                f"SQLite validation failed: quick={quick}, integrity={integrity}"
            )
    finally:
        connection.close()

    print(json.dumps({
        "built": True,
        "output": str(options.output.resolve()),
        "sha256": sha256(options.output),
        "quick_check": quick,
        "integrity_check": integrity,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
