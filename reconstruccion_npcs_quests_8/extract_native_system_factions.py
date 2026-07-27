#!/usr/bin/env python3
"""Extract the AA8 native system_factions cached result from game11."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PARSER_PATH = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"
AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734 game11"

COLUMNS = (
    "id aggro_link desc_when_use_create_expedition guard_help icon_id "
    "integration_faction is_diplomacy_tgt mother_id name owner_id owner_name "
    "owner_type_id political_system_id show_create_expedition"
).split()
LAYOUT = "68 38 78 38 68 38 38 68 78 68 78 68 68 38".split()


def load_parser():
    spec = importlib.util.spec_from_file_location("aa8_cached_result", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--data-output", type=Path)
    return parser.parse_args()


def decode_native_text(value: Any) -> Any:
    """Repair UTF-8 text exposed as Latin-1 by the cached-result reader."""
    if not isinstance(value, str):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def main() -> int:
    options = parse_args()
    parser = load_parser()
    reader = parser.CachedResultReader(options.game11.read_bytes())
    rows, source_range = parser.locate_cached_result(
        reader,
        COLUMNS,
        LAYOUT,
        101,
        {"guard_help": 1, "mother_id": 148},
    )
    rows = [
        {column: decode_native_text(value) for column, value in row.items()}
        for row in rows
    ]
    rows.sort(key=lambda row: int(row["id"]))
    by_id: dict[int, dict[str, Any]] = {int(row["id"]): row for row in rows}
    if len(rows) != 114 or 101 not in by_id or 148 not in by_id:
        raise RuntimeError("Unexpected AA8 system_factions cached result")
    if int(by_id[101]["mother_id"]) != 148 or int(by_id[148]["mother_id"]) != 0:
        raise RuntimeError("Native faction chain 101 -> 148 -> 0 did not validate")

    manifest = {
        "authority": AUTHORITY,
        "source": {
            "path": str(options.game11.resolve()),
            "sha256": sha256_file(options.game11),
            "size": options.game11.stat().st_size,
        },
        "loader": {
            "function": "x2game.dll FUN_399698b0",
            "sql_address": "0x39DD8CA0",
            "columns": COLUMNS,
            "layout": LAYOUT,
        },
        "cached_result": {
            "start": source_range["start"],
            "start_hex": f"0x{source_range['start']:X}",
            "done": source_range["end"],
            "done_hex": f"0x{source_range['end']:X}",
            "rows": len(rows),
            "id_min": min(by_id),
            "id_max": max(by_id),
            "canonical_rows_sha256": hashlib.sha256(
                json.dumps(
                    rows,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest().upper(),
        },
        "quest_330_faction_chain": {
            "character_faction": by_id[101],
            "required_mother_faction": by_id[148],
            "chain": [101, 148, 0],
            "validated": True,
        },
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    data_output = (
        options.data_output
        if options.data_output is not None
        else options.output.with_name("native-system-factions-v1-data.json")
    )
    data = {
        "authority": AUTHORITY,
        "source": manifest["source"],
        "loader": manifest["loader"],
        "cached_result": manifest["cached_result"],
        "table": "system_factions",
        "rows": rows,
    }
    data_output.parent.mkdir(parents=True, exist_ok=True)
    data_output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"system_factions: {len(rows)} rows "
        f"0x{source_range['start']:X}..0x{source_range['end']:X}; "
        "quest330 chain 101 -> 148 -> 0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
