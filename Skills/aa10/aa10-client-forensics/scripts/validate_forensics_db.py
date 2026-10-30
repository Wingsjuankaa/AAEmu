#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def scalar(connection: sqlite3.Connection, sql: str) -> object:
    row = connection.execute(sql).fetchone()
    return None if row is None else row[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise FileNotFoundError(database)

    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        tables = {str(row[0]) for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        result = {
            "database": database.as_posix(),
            "quick_check": scalar(connection, "PRAGMA quick_check"),
            "integrity_check": scalar(connection, "PRAGMA integrity_check"),
            "tables": len(tables),
        }
        for table in (
            "artifacts", "source_databases", "source_tables", "query_specs",
            "native_functions", "entities", "relations", "consumers",
            "serializers", "opaque_regions", "coverage", "validation_events",
        ):
            if table in tables:
                result[table] = scalar(connection, f'SELECT COUNT(*) FROM "{table}"')
        if "relations" in tables:
            result["unclassified_relations"] = scalar(
                connection,
                "SELECT COUNT(*) FROM relations WHERE state IS NULL OR state=''",
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if (
            result["quick_check"] == "ok"
            and result["integrity_check"] == "ok"
            and result.get("unclassified_relations", 0) == 0
        ) else 2
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
