#!/usr/bin/env python3
"""Produce a deterministic, read-only logical comparison of SQLite compacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path


LABEL_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_database(value: str) -> tuple[str, Path]:
    label, separator, raw_path = value.partition("=")
    if not separator or not LABEL_RE.match(label):
        raise argparse.ArgumentTypeError("Expected LABEL=PATH with a simple label")
    return label, Path(raw_path).resolve(strict=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database", action="append", type=parse_database, required=True,
        help="LABEL=PATH; the first database is the comparison baseline",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def database_metadata(path: Path) -> dict[str, object]:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "page_size": connection.execute("PRAGMA page_size").fetchone()[0],
            "page_count": connection.execute("PRAGMA page_count").fetchone()[0],
            "schema_version": connection.execute("PRAGMA schema_version").fetchone()[0],
            "table_count": connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0],
        }
    finally:
        connection.close()


def table_schema(connection: sqlite3.Connection, alias: str) -> dict[str, str]:
    return {
        row[0]: row[1] or ""
        for row in connection.execute(
            f"SELECT name, sql FROM {quote_identifier(alias)}.sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    }


def columns(connection: sqlite3.Connection, alias: str, table: str) -> list[tuple[str, int]]:
    return [
        (row[1], row[5])
        for row in connection.execute(
            f"PRAGMA {quote_identifier(alias)}.table_info({quote_identifier(table)})"
        )
    ]


def compare_pair(
    connection: sqlite3.Connection,
    baseline_alias: str,
    candidate_alias: str,
    baseline_label: str,
    candidate_label: str,
) -> dict[str, object]:
    baseline_schema = table_schema(connection, baseline_alias)
    candidate_schema = table_schema(connection, candidate_alias)
    baseline_tables = set(baseline_schema)
    candidate_tables = set(candidate_schema)
    common_tables = sorted(baseline_tables & candidate_tables)
    schema_changed = [
        table for table in common_tables
        if baseline_schema[table] != candidate_schema[table]
    ]

    row_count_differences: dict[str, dict[str, int]] = {}
    logical_differences: dict[str, dict[str, object]] = {}
    for table in common_tables:
        quoted_table = quote_identifier(table)
        baseline_count = connection.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(baseline_alias)}.{quoted_table}"
        ).fetchone()[0]
        candidate_count = connection.execute(
            f"SELECT COUNT(*) FROM {quote_identifier(candidate_alias)}.{quoted_table}"
        ).fetchone()[0]
        if baseline_count != candidate_count:
            row_count_differences[table] = {
                baseline_label: baseline_count,
                candidate_label: candidate_count,
            }
        if table in schema_changed:
            continue

        baseline_minus_candidate = connection.execute(
            "SELECT COUNT(*) FROM ("
            f"SELECT * FROM {quote_identifier(baseline_alias)}.{quoted_table} EXCEPT "
            f"SELECT * FROM {quote_identifier(candidate_alias)}.{quoted_table})"
        ).fetchone()[0]
        candidate_minus_baseline = connection.execute(
            "SELECT COUNT(*) FROM ("
            f"SELECT * FROM {quote_identifier(candidate_alias)}.{quoted_table} EXCEPT "
            f"SELECT * FROM {quote_identifier(baseline_alias)}.{quoted_table})"
        ).fetchone()[0]
        if baseline_minus_candidate == 0 and candidate_minus_baseline == 0:
            continue

        detail: dict[str, object] = {
            f"{baseline_label}_minus_{candidate_label}": baseline_minus_candidate,
            f"{candidate_label}_minus_{baseline_label}": candidate_minus_baseline,
        }
        table_columns = columns(connection, baseline_alias, table)
        primary_keys = [name for name, pk in table_columns if pk]
        if len(primary_keys) == 1 and baseline_count == candidate_count:
            pk = quote_identifier(primary_keys[0])
            changed_columns: dict[str, int] = {}
            for column_name, _ in table_columns:
                if column_name == primary_keys[0]:
                    continue
                column = quote_identifier(column_name)
                count = connection.execute(
                    f"SELECT COUNT(*) FROM {quote_identifier(baseline_alias)}.{quoted_table} b "
                    f"JOIN {quote_identifier(candidate_alias)}.{quoted_table} c ON b.{pk}=c.{pk} "
                    f"WHERE b.{column} IS NOT c.{column}"
                ).fetchone()[0]
                if count:
                    changed_columns[column_name] = count
            detail["changed_columns_by_primary_key"] = changed_columns
        logical_differences[table] = detail

    return {
        "baseline": baseline_label,
        "candidate": candidate_label,
        "baseline_only_tables": sorted(baseline_tables - candidate_tables),
        "candidate_only_tables": sorted(candidate_tables - baseline_tables),
        "schema_changed_tables": schema_changed,
        "row_count_differences": row_count_differences,
        "logical_differences": logical_differences,
    }


def main() -> int:
    args = parse_args()
    if len(args.database) < 2:
        raise SystemExit("At least two --database values are required")
    labels = [label for label, _ in args.database]
    if len(labels) != len(set(labels)):
        raise SystemExit("Database labels must be unique")

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "method": (
            "Read-only SQLite integrity, schema, row-count and bidirectional EXCEPT comparison. "
            "Column deltas are counted by single-column primary key when schemas and row counts match."
        ),
        "databases": {
            label: database_metadata(path) for label, path in args.database
        },
        "comparisons": [],
    }

    connection = sqlite3.connect(":memory:", uri=True)
    connection.execute("PRAGMA temp_store=FILE")
    try:
        for index, (_, path) in enumerate(args.database):
            uri = f"{path.as_uri()}?mode=ro"
            connection.execute(f"ATTACH DATABASE ? AS db{index}", (uri,))
        baseline_label = args.database[0][0]
        for index, (candidate_label, _) in enumerate(args.database[1:], start=1):
            report["comparisons"].append(
                compare_pair(connection, "db0", f"db{index}", baseline_label, candidate_label)
            )
    finally:
        connection.close()

    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(output)
    for comparison in report["comparisons"]:
        print(json.dumps({
            "candidate": comparison["candidate"],
            "logical_differences": list(comparison["logical_differences"]),
            "schema_changed_tables": comparison["schema_changed_tables"],
            "row_count_difference_tables": list(comparison["row_count_differences"]),
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
