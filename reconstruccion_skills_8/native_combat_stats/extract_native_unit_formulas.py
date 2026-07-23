#!/usr/bin/env python3
"""Extract AA8 unit formulas and variables from the native game11 cache.

The SQL column order and value layouts are confirmed by x2game.dll:

* FUN_39a73350: unit_formulas
* FUN_39a730a0: unit_formula_variables

No historical compact is accepted as input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))

from extract_battlerage_manifest import CachedResultReader, read_cached_result  # noqa: E402


FORMULA_COLUMNS = ["id", "formula", "kind_id", "owner_type_id"]
FORMULA_LAYOUT = ["68", "78", "68", "68"]
FORMULA_FIRST_STRING_REFERENCE = 361128
FORMULA_EXPECTED_ROWS = 480
FORMULA_ANCHOR = {
    "id": 1,
    "formula": "if_negative(heir_level-1,(str*10)*100,200000*str^0.26)",
    "kind_id": 1,
    "owner_type_id": 0,
}

VARIABLE_COLUMNS = ["id", "key", "unit_formula_id", "value", "variable_kind_id"]
VARIABLE_LAYOUT = ["68", "68", "68", "60", "68"]
VARIABLE_EXPECTED_ROWS = 3600
VARIABLE_FIRST_ROW = {
    "id": 1,
    "key": 0,
    "unit_formula_id": 1,
    "value": 0.0,
    "variable_kind_id": 1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def locate_unique_row(
    reader: CachedResultReader,
    layout: list[str],
    first_id: int,
    predicate: Any,
) -> int:
    pattern = b"\x64" + struct.pack("<i", first_id)
    matches: list[int] = []
    cursor = 0
    while True:
        cursor = reader.data.find(pattern, cursor)
        if cursor < 0:
            break
        try:
            row, end = reader.row(cursor, layout)
            if end < len(reader.data) and reader.data[end] in (100, 101) and predicate(row):
                matches.append(cursor)
        except (IndexError, ValueError, struct.error):
            pass
        cursor += 1
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one cached result anchor for id {first_id}, found {len(matches)}"
        )
    return matches[0]


def extract(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    data = path.read_bytes()

    formula_probe = CachedResultReader(data)
    formula_start = locate_unique_row(
        formula_probe,
        FORMULA_LAYOUT,
        1,
        lambda row: (
            row[0] == FORMULA_ANCHOR["id"]
            and row[1] == FORMULA_ANCHOR["formula"]
            and row[2] == FORMULA_ANCHOR["kind_id"]
            and row[3] == FORMULA_ANCHOR["owner_type_id"]
        ),
    )
    formula_reader = CachedResultReader(data)
    formula_reader.begin_string_cache_capture(FORMULA_FIRST_STRING_REFERENCE)
    formula_values, formula_end = read_cached_result(
        formula_reader, formula_start, FORMULA_LAYOUT
    )
    formula_reader.end_string_cache_capture()
    formulas = [dict(zip(FORMULA_COLUMNS, row)) for row in formula_values]

    variable_reader = CachedResultReader(data)
    variable_start = locate_unique_row(
        variable_reader,
        VARIABLE_LAYOUT,
        1,
        lambda row: dict(zip(VARIABLE_COLUMNS, row)) == VARIABLE_FIRST_ROW,
    )
    variable_values, variable_end = read_cached_result(
        variable_reader, variable_start, VARIABLE_LAYOUT
    )
    variables = [dict(zip(VARIABLE_COLUMNS, row)) for row in variable_values]

    return formulas, variables, {
        "formula_start": formula_start,
        "formula_end": formula_end,
        "variable_start": variable_start,
        "variable_end": variable_end,
    }


def validate(
    formulas: list[dict[str, Any]],
    variables: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if len(formulas) != FORMULA_EXPECTED_ROWS:
        errors.append(f"formulas={len(formulas)}, expected={FORMULA_EXPECTED_ROWS}")
    if len(variables) != VARIABLE_EXPECTED_ROWS:
        errors.append(f"variables={len(variables)}, expected={VARIABLE_EXPECTED_ROWS}")
    if formulas[0] != FORMULA_ANCHOR:
        errors.append(f"formula anchor mismatch: {formulas[0]}")
    if variables[0] != VARIABLE_FIRST_ROW:
        errors.append(f"variable anchor mismatch: {variables[0]}")

    unresolved = [
        row["id"]
        for row in formulas
        if isinstance(row["formula"], str) and row["formula"].startswith("<ref:")
    ]
    if unresolved:
        errors.append(f"unresolved formula references: {unresolved[:20]}")

    formula_ids = {int(row["id"]) for row in formulas}
    orphan_variables = [
        int(row["id"])
        for row in variables
        if int(row["unit_formula_id"]) not in formula_ids
    ]
    if orphan_variables:
        errors.append(f"orphan formula variables: {orphan_variables[:20]}")

    character_formulas = {
        int(row["kind_id"]): str(row["formula"])
        for row in formulas
        if int(row["owner_type_id"]) == 0
    }
    expected_character_values = {
        5: " if_negative(heir_level-1,(str*15)*100,100000*str^0.26)",
        20: "((level ^ 1.3 + level * 3 + 17) * 100 ) * 100",
        45: "if_negative(heir_level-1,(sta*6)*100,166000*sta^0.26)",
        46: "if_negative(heir_level-1,(dex*4)*100,50000*dex^0.26)",
    }
    for kind_id, expected in expected_character_values.items():
        if character_formulas.get(kind_id) != expected:
            errors.append(
                f"character formula kind {kind_id}: {character_formulas.get(kind_id)!r}"
            )

    if errors:
        raise RuntimeError("AA8 unit formula validation failed:\n" + "\n".join(errors))

    return {
        "formula_count": len(formulas),
        "variable_count": len(variables),
        "owner_counts": dict(
            sorted(Counter(int(row["owner_type_id"]) for row in formulas).items())
        ),
        "character_kind_count": len(character_formulas),
        "maximum_kind_id": max(int(row["kind_id"]) for row in formulas),
        "maximum_variable_kind_id": max(
            int(row["variable_kind_id"]) for row in variables
        ),
        "unresolved_formula_references": 0,
        "orphan_formula_variables": 0,
    }


def main() -> int:
    args = parse_args()
    if not args.game11.is_file():
        raise FileNotFoundError(args.game11)

    formulas, variables, ranges = extract(args.game11)
    verification = validate(formulas, variables) if args.verify else None
    catalog = {
        "format_version": 1,
        "scope": "AA8 native unit formulas and unit formula variables",
        "authority": {
            "source": "game11_native",
            "layout": "x2game_confirmed",
            "x2game_functions": {
                "unit_formulas": "FUN_39a73350",
                "unit_formula_variables": "FUN_39a730a0",
            },
            "sql": {
                "unit_formulas": (
                    "SELECT id, formula, kind_id, owner_type_id FROM unit_formulas"
                ),
                "unit_formula_variables": (
                    "SELECT id, key, unit_formula_id, value, variable_kind_id "
                    "FROM unit_formula_variables"
                ),
            },
            "historical_reference_used": False,
        },
        "source": {
            "path": str(args.game11.resolve()),
            "sha256": sha256_file(args.game11),
            "result_ranges": ranges,
            "formula_first_string_reference": FORMULA_FIRST_STRING_REFERENCE,
        },
        "formula_columns": FORMULA_COLUMNS,
        "formula_layout": FORMULA_LAYOUT,
        "variable_columns": VARIABLE_COLUMNS,
        "variable_layout": VARIABLE_LAYOUT,
        "verification": verification,
        "formulas": formulas,
        "variables": variables,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(catalog), encoding="utf-8")
    round_trip = json.loads(args.output.read_text(encoding="utf-8"))
    if canonical_json(round_trip) != canonical_json(catalog):
        raise RuntimeError("Catalog output is not deterministic")
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
