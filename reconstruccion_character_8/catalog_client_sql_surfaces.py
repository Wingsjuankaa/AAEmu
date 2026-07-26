#!/usr/bin/env python3
"""Catalogue every embedded SQL statement in the AA8 x2game binaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ASCII = re.compile(rb"[\x20-\x7e]{8,}")
SQL_PREFIX = re.compile(
    r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|REPLACE|PRAGMA)\b",
    re.IGNORECASE,
)
TABLE_REFERENCE = re.compile(
    r"\b(?:FROM|JOIN|UPDATE|INTO|TABLE(?:\s+IF\s+NOT\s+EXISTS)?)\s+"
    r"[`\"']?([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
FOCUS_TABLES = {
    "character_default_skills",
    "character_equip_packs",
    "character_supplies",
    "characters",
    "default_action_bar_actions",
    "default_inventory_tab_groups",
    "default_inventory_tabs",
    "default_skills",
    "district_return_points",
    "equip_pack_cloths",
    "equip_pack_weapons",
    "item_bags",
    "login_stage_abilities",
    "return_points",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def statements(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    result: list[dict[str, Any]] = []
    for match in ASCII.finditer(data):
        value = match.group().decode("ascii")
        if not SQL_PREFIX.search(value):
            continue
        tables = sorted({name.lower() for name in TABLE_REFERENCE.findall(value)})
        result.append(
            {
                "focus": sorted(set(tables) & FOCUS_TABLES),
                "offset": match.start(),
                "sha256": hashlib.sha256(match.group()).hexdigest().upper(),
                "tables": tables,
                "value": value,
            }
        )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    binaries: list[dict[str, Any]] = []
    statement_sets: list[set[str]] = []
    global_tables: Counter[str] = Counter()
    for path in sorted(options.binary, key=lambda item: item.as_posix().lower()):
        if not path.is_file():
            raise FileNotFoundError(path)
        found = statements(path)
        statement_set = {entry["value"] for entry in found}
        statement_sets.append(statement_set)
        tables = Counter(
            table for entry in found for table in set(entry["tables"])
        )
        global_tables.update(tables)
        binaries.append(
            {
                "bytes": path.stat().st_size,
                "path": path.resolve().as_posix(),
                "sha256": sha256(path),
                "statement_count": len(found),
                "statements": found,
                "table_reference_counts": dict(sorted(tables.items())),
            }
        )

    common = set.intersection(*statement_sets) if statement_sets else set()
    union = set.union(*statement_sets) if statement_sets else set()
    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "binaries": binaries,
        "classification": {
            "note": (
                "This is a complete embedded ASCII SQL inventory. A query proves "
                "a client loader layout, not a server-side creation relation."
            ),
            "sql_is_direct_gameplay_authority": False,
        },
        "comparison": {
            "common_statements": len(common),
            "statement_union": len(union),
            "statements_not_common": sorted(union - common),
        },
        "schema_version": 1,
        "table_reference_counts_all_binaries": dict(sorted(global_tables.items())),
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
