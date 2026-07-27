#!/usr/bin/env python3
"""Exhaustively test decrypted AA8 client streams for spawner row results.

The x2game loaders prove the schemas, but a schema string is not proof that
client-mode execution serialized the rows.  This audit scans every non-empty
decrypted stream for contiguous results matching the exact native layouts.
Plausibility filters only reject impossible decodes; any surviving chain is a
candidate requiring a separate native anchor before acceptance.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path
from typing import Any

from extract_native_npc_quest_catalog import (
    AUTHORITY,
    CachedResultReader,
    UNLOCATED_NATIVE_TABLES,
    sha256_file,
)


DEFAULT_STREAM_ROOT = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted")
NONEMPTY_STREAMS = ("game0", "game2", "game6", "game7", "game11")


def plausible_spawner(row: dict[str, Any]) -> bool:
    doubles = [
        row[key]
        for key in (
            "destroyTime",
            "endTime",
            "spawn_delay_max",
            "spawn_delay_min",
            "startTime",
            "test_radius_npc",
            "test_radius_pc",
        )
    ]
    return (
        0 < row["id"] < 1_000_000
        and row["activation_state"] in (0, 1)
        and all(math.isfinite(value) and 0 <= value <= 1_000_000_000 for value in doubles)
        and 0 <= row["maxPopulation"] <= 100_000
        and 0 <= row["min_population"] <= 100_000
        and 0 < row["npc_spawner_category_id"] < 100_000
        and row["save_indun"] in (0, 1)
        and 0 <= row["suspend_spawn_count"] <= 100_000
        and isinstance(row["name"], str)
    )


def plausible_member(row: dict[str, Any]) -> bool:
    member_type = row["member_type"]
    return (
        0 < row["id"] < 1_000_000
        and isinstance(member_type, str)
        and (
            member_type in ("Npc", "NpcGroup")
            or (member_type.startswith("<ref:") and member_type.endswith(">"))
        )
        and 0 < row["member_id"] < 1_000_000
        and 0 < row["npc_spawner_id"] < 1_000_000
        and math.isfinite(row["weight"])
        and 0.001 <= row["weight"] <= 1_000
    )


def scan(data: bytes, table: str) -> dict[str, Any]:
    spec = UNLOCATED_NATIVE_TABLES[table]
    predicate = plausible_spawner if table == "npc_spawners" else plausible_member
    valid: dict[int, tuple[int, dict[str, Any]]] = {}
    cursor = 0
    row_markers = 0
    while True:
        cursor = data.find(b"\x64", cursor)
        if cursor < 0:
            break
        row_markers += 1
        try:
            reader = CachedResultReader(data, None)
            values, end = reader.row(cursor, spec["layout"])
            row = dict(zip(spec["columns"], values))
            if (
                end < len(data)
                and data[end] in (100, 101)
                and predicate(row)
            ):
                valid[cursor] = (end, row)
        except (IndexError, ValueError, OverflowError, struct.error):
            pass
        cursor += 1

    linked_ends = {end for end, _ in valid.values()}
    roots = [offset for offset in valid if offset not in linked_ends]
    chains: list[dict[str, Any]] = []
    for root in roots:
        cursor = root
        rows: list[dict[str, Any]] = []
        while cursor in valid:
            cursor, row = valid[cursor]
            rows.append(row)
        if len(rows) >= 2:
            chains.append(
                {
                    "start_hex": f"0x{root:X}",
                    "end_hex": f"0x{cursor:X}",
                    "rows": len(rows),
                    "first_id": rows[0]["id"],
                    "last_id": rows[-1]["id"],
                }
            )
    chains.sort(key=lambda item: (-item["rows"], item["start_hex"]))
    return {
        "row_markers_examined": row_markers,
        "plausible_individual_rows": len(valid),
        "contiguous_candidate_chains": chains,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream-root", type=Path, default=DEFAULT_STREAM_ROOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent
        / "generated"
        / "native-spawner-stream-audit-v1-manifest.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    streams: dict[str, Any] = {}
    for name in NONEMPTY_STREAMS:
        path = args.stream_root / name
        if not path.is_file():
            raise FileNotFoundError(path)
        data = path.read_bytes()
        streams[name] = {
            "path": str(path.resolve()),
            "bytes": len(data),
            "sha256": sha256_file(path),
            "tables": {
                table: scan(data, table)
                for table in ("npc_spawners", "npc_spawner_npcs")
            },
        }
    candidate_chains = sum(
        len(table["contiguous_candidate_chains"])
        for stream in streams.values()
        for table in stream["tables"].values()
    )
    manifest = {
        "format_version": 1,
        "authority": AUTHORITY,
        "classification": "exhaustive decrypted-client-stream absence audit",
        "layouts": UNLOCATED_NATIVE_TABLES,
        "streams": streams,
        "result": {
            "candidate_chains": candidate_chains,
            "rows_recovered": 0,
            "conclusion": (
                "No contiguous cached result matching either exact x2game loader "
                "layout exists in the non-empty decrypted client streams."
                if candidate_chains == 0
                else "Candidate chains require native anchor validation."
            ),
            "scope_limit": (
                "Absence from client-mode streams does not prove absence from the "
                "private AA8 server compact."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output.resolve())
    print(json.dumps(manifest["result"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
