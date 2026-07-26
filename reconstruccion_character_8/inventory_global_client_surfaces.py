#!/usr/bin/env python3
"""Inventory every AA8 client surface without assigning gameplay meaning."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FOCUS_MARKERS = (
    "character",
    "create",
    "login_stage",
    "starting_zone",
    "start_zone",
    "spawn",
    "respawn",
    "return_point",
    "intro",
    "action_bar",
    "actionbar",
    "shortcut",
    "hotkey",
    "auto_register",
    "inventory",
    "bag_slot",
    "bank_slot",
    "capacity",
    "character_supplies",
    "start_equip",
)

EXACT_NATIVE_MARKERS = (
    "system_nuian_start",
    "dwarf_start",
    "gwe_start",
    "rain_system",
    "start_warborn",
    "start_fp",
    "default_action_bar_actions",
    "character_supplies",
    "login_stage_abilities",
    "start_equip_pack_id",
    "baseactionbaremptyslotcount",
)

TEXT_EXTENSIONS = {
    ".xml",
    ".txt",
    ".cfg",
    ".ini",
    ".json",
    ".csv",
    ".lua",
    ".g",
    ".cdf",
    ".chrparams",
    ".cal",
    ".mtl",
    ".ent",
    ".animevents",
    ".adb",
    ".ik",
    ".lst",
    ".xsd",
    ".html",
    ".htm",
    ".js",
    ".css",
}

WORLD_BINARY_EXTENSIONS = {
    ".dat",
    ".ctc",
    ".bin",
    ".pak",
    ".raw",
    ".hmap",
}

ASCII_RUN = re.compile(rb"[\x20-\x7e]{4,}")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest().upper()


def normalized_extension(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return suffix or "<none>"


def inventory_gamepak_index(path: Path) -> dict[str, Any]:
    extensions: Counter[str] = Counter()
    roots: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    keyword_counts: Counter[str] = Counter()
    keyword_paths: dict[str, list[str]] = defaultdict(list)
    total_files = 0
    total_bytes = 0

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        for row in reader:
            name = row["name"].replace("\\", "/")
            lowered = name.lower()
            size = int(row["size"])
            extension = normalized_extension(name)
            total_files += 1
            total_bytes += size
            extensions[extension] += 1
            parts = lowered.split("/")
            roots["/".join(parts[: min(3, len(parts))])] += 1
            if extension in TEXT_EXTENSIONS:
                classes["text_or_text_container"] += 1
            elif extension in WORLD_BINARY_EXTENSIONS:
                classes["world_or_opaque_binary"] += 1
            else:
                classes["asset_or_other_binary"] += 1
            for marker in FOCUS_MARKERS:
                if marker in lowered:
                    keyword_counts[marker] += 1
                    if len(keyword_paths[marker]) < 2000:
                        keyword_paths[marker].append(name)

    return {
        "path": path.resolve().as_posix(),
        "sha256": sha256(path),
        "files": total_files,
        "uncompressed_bytes": total_bytes,
        "extensions": dict(sorted(extensions.items())),
        "top_level_groups": dict(
            sorted(roots.items(), key=lambda item: (-item[1], item[0]))[:500]
        ),
        "surface_classes": dict(sorted(classes.items())),
        "focus_path_counts": dict(sorted(keyword_counts.items())),
        "focus_paths_capped_at_2000_each": {
            marker: sorted(paths)
            for marker, paths in sorted(keyword_paths.items())
        },
    }


def quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def inventory_compact(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro",
        uri=True,
    )
    try:
        tables: list[dict[str, Any]] = []
        exact_matches: dict[str, list[dict[str, Any]]] = defaultdict(list)
        names = [
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' ORDER BY name"
            )
        ]
        for table in names:
            info = list(connection.execute(f"PRAGMA table_info({quoted(table)})"))
            columns = [
                {
                    "name": str(row[1]),
                    "type": str(row[2]),
                    "not_null": bool(row[3]),
                    "primary_key": int(row[5]),
                }
                for row in info
            ]
            tables.append(
                {
                    "name": table,
                    "rows": int(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {quoted(table)}"
                        ).fetchone()[0]
                    ),
                    "columns": columns,
                    "create_sql": connection.execute(
                        "SELECT sql FROM sqlite_master "
                        "WHERE type='table' AND name=?",
                        (table,),
                    ).fetchone()[0],
                }
            )
            text_columns = [
                column["name"]
                for column in columns
                if any(
                    token in column["type"].upper()
                    for token in ("CHAR", "CLOB", "TEXT")
                )
            ]
            for column in text_columns:
                for marker in EXACT_NATIVE_MARKERS:
                    count = int(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {quoted(table)} "
                            f"WHERE instr(lower({quoted(column)}), ?) > 0",
                            (marker,),
                        ).fetchone()[0]
                    )
                    if count:
                        exact_matches[marker].append(
                            {
                                "table": table,
                                "column": column,
                                "rows": count,
                            }
                        )
        return {
            "path": path.resolve().as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "tables": tables,
            "exact_native_marker_matches": dict(sorted(exact_matches.items())),
        }
    finally:
        connection.close()


def strings_with_offsets(path: Path) -> list[tuple[int, str]]:
    payload = path.read_bytes()
    return [
        (match.start(), match.group().decode("ascii", errors="replace"))
        for match in ASCII_RUN.finditer(payload)
    ]


def inventory_binary(path: Path) -> dict[str, Any]:
    semantic: list[dict[str, Any]] = []
    sql: list[dict[str, Any]] = []
    seen_semantic: set[tuple[int, str]] = set()
    seen_sql: set[tuple[int, str]] = set()
    for offset, value in strings_with_offsets(path):
        lowered = value.lower()
        if any(marker in lowered for marker in EXACT_NATIVE_MARKERS):
            key = (offset, value)
            if key not in seen_semantic:
                semantic.append({"offset": offset, "value": value})
                seen_semantic.add(key)
        if (
            "select " in lowered
            or " from " in lowered
            or " join " in lowered
        ) and any(marker in lowered for marker in FOCUS_MARKERS):
            key = (offset, value)
            if key not in seen_sql:
                sql.append({"offset": offset, "value": value})
                seen_sql.add(key)
    return {
        "path": path.resolve().as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "semantic_strings": semantic,
        "focus_sql_strings": sql,
    }


def inventory_cache_streams(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.resolve().as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(root.glob("game*"), key=lambda item: item.name)
        if path.is_file()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", type=Path, required=True)
    parser.add_argument("--game11-root", type=Path, required=True)
    parser.add_argument("--gamepak-index", type=Path, required=True)
    parser.add_argument("--gamepak", type=Path, required=True)
    parser.add_argument("--gamepak-sha256")
    parser.add_argument("--binary", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": "native_client_global_surface_inventory",
        "compact": inventory_compact(args.compact),
        "cached_result_streams": inventory_cache_streams(args.game11_root),
        "gamepak": {
            "path": args.gamepak.resolve().as_posix(),
            "bytes": args.gamepak.stat().st_size,
            "sha256": args.gamepak_sha256,
            "content_identity": (
                "The complete index records per-entry MD5, size and offset. "
                "The monolithic SHA-256 is optional because re-reading the "
                "51.5 GB container is not required for deterministic index "
                "analysis."
            ),
            "index": inventory_gamepak_index(args.gamepak_index),
        },
        "binaries": [
            inventory_binary(path)
            for path in sorted(
                (path.resolve() for path in args.binary),
                key=lambda item: item.as_posix().lower(),
            )
        ],
        "focus": {
            "current_session": [
                "spawn transform",
                "initial action bar",
                "starter supply bag slots",
                "initial inventory and bank capacity",
            ],
            "policy": (
                "Inventory only. A filename, string or numeric co-occurrence "
                "does not authorize a gameplay relation."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
