#!/usr/bin/env python3
"""Extract the AA8 enabled skill_modifiers result cached in game11."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT))

from extract_battlerage_manifest import CachedResultReader, read_cached_result  # noqa: E402


COLUMNS = (
    "owner_type owner_id dynamic_value skill_attribute_id skill_id synergy tag_id "
    "target_buff_id target_tag_id unit_modifier_type_id value"
).split()
LAYOUT = "78 68 68 68 68 38 68 68 68 68 68".split()
EXPECTED_ROWS = 1571
STRING_REFERENCES = {
    "<ref:69859>": "Buff",
    "<ref:69860>": "Item",
    "<ref:69868>": "CombatResource",
}
WEAPON_MASTERY_ROW = {
    "owner_type": "Buff",
    "owner_id": 831,
    "dynamic_value": 0,
    "skill_attribute_id": 10,
    "skill_id": 0,
    "synergy": 0,
    "tag_id": 415,
    "target_buff_id": 0,
    "target_tag_id": 0,
    "unit_modifier_type_id": 1,
    "value": 10,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def locate_start(data: bytes) -> int:
    first_row = (
        b"\x64\x01"
        + struct.pack("<I", 69859)
        + struct.pack("<iiii", 157, 0, 0, 0)
        + b"\x00"
        + struct.pack("<iiiii", 4, 0, 0, 0, 1000)
    )
    matches: list[int] = []
    cursor = 0
    while True:
        cursor = data.find(first_row, cursor)
        if cursor < 0:
            break
        matches.append(cursor)
        cursor += 1
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one native skill_modifiers result, found {len(matches)}"
        )
    return matches[0]


def extract(path: Path) -> tuple[list[dict[str, Any]], int, int]:
    data = path.read_bytes()
    start = locate_start(data)
    reader = CachedResultReader(data)
    raw_rows, end = read_cached_result(reader, start, LAYOUT)
    rows = []
    for values in raw_rows:
        row = dict(zip(COLUMNS, values))
        row["owner_type"] = STRING_REFERENCES.get(
            str(row["owner_type"]), row["owner_type"]
        )
        rows.append(row)
    return rows, start, end


def validate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    if len(rows) != EXPECTED_ROWS:
        errors.append(f"rows={len(rows)}, expected={EXPECTED_ROWS}")
    mastery = [row for row in rows if row == WEAPON_MASTERY_ROW]
    if len(mastery) != 1:
        errors.append(f"Weapon Mastery native row count={len(mastery)}")
    unknown_owners = sorted(
        {str(row["owner_type"]) for row in rows}
        - {"Buff", "Item", "CombatResource"}
    )
    if unknown_owners:
        errors.append(f"unknown owner types: {unknown_owners}")
    if errors:
        raise RuntimeError("AA8 skill_modifiers validation failed:\n" + "\n".join(errors))

    contextual = [
        row
        for row in rows
        if int(row["dynamic_value"]) != 0
        or int(row["target_buff_id"]) != 0
        or int(row["target_tag_id"]) != 0
    ]
    safe_buff_rows = [
        row
        for row in rows
        if row["owner_type"] == "Buff" and row not in contextual
    ]
    return {
        "row_count": len(rows),
        "owner_type_counts": dict(
            sorted(Counter(str(row["owner_type"]) for row in rows).items())
        ),
        "contextual_row_count": len(contextual),
        "safe_buff_row_count": len(safe_buff_rows),
        "weapon_mastery": WEAPON_MASTERY_ROW,
    }


def main() -> int:
    args = parse_args()
    rows, start, end = extract(args.game11)
    verification = validate(rows) if args.verify else None
    catalog = {
        "format_version": 1,
        "scope": "AA8 enabled skill_modifiers cached result",
        "authority": {
            "source": "game11_native",
            "layout": "x2game_confirmed",
            "x2game_function": "FUN_39979330",
            "historical_reference_used": False,
        },
        "source": {
            "path": str(args.game11.resolve()),
            "sha256": sha256_file(args.game11),
            "result_range": {"start": start, "end": end, "rows": len(rows)},
        },
        "columns": COLUMNS,
        "layout": LAYOUT,
        "verification": verification,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(catalog), encoding="utf-8")
    print(
        canonical_json(
            {
                "output": str(args.output.resolve()),
                "sha256": sha256_file(args.output),
                "verification": verification,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
