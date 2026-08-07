#!/usr/bin/env python3
"""Decode the exact AA8 unit_reqs cached result from Kakao game11."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reconstruccion_skills_8"))

from extract_battlerage_manifest import CachedResultReader, read_cached_result  # noqa: E402


EXPECTED_SHA256 = "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"
RESULT_START = 0x828B2C
RESULT_END = 0x87EC3C
FIRST_STRING_REFERENCE = 0x110FA
EXPECTED_ROWS = 13_053
COLUMNS = (
    "owner_type",
    "owner_id",
    "display_msg",
    "kind_id",
    "value1",
    "value2",
    "value3",
)
LAYOUT = ["78", "68", "38", "68", "68", "68", "68"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def extract_unit_requirements(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"Unexpected AA8 game11 SHA-256: {digest}")

    reader = CachedResultReader(data)
    reader.begin_string_cache_capture(FIRST_STRING_REFERENCE)
    raw_rows, end = read_cached_result(reader, RESULT_START, LAYOUT)
    string_cache = reader.end_string_cache_capture()
    if end != RESULT_END or len(raw_rows) != EXPECTED_ROWS:
        raise RuntimeError(
            f"AA8 unit_reqs boundary mismatch: rows={len(raw_rows)} end=0x{end:X}"
        )

    rows = [dict(zip(COLUMNS, row)) for row in raw_rows]
    return rows, {
        "authority": "AA8_Kakao_game11_cached_result",
        "source": str(path.resolve()),
        "source_sha256": digest,
        "result_start": RESULT_START,
        "result_end": RESULT_END,
        "layout": LAYOUT,
        "rows": len(rows),
        "string_cache_first_reference": FIRST_STRING_REFERENCE,
        "string_cache": {str(key): value for key, value in sorted(string_cache.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows, provenance = extract_unit_requirements(args.game11)
    payload = {"schema_version": 1, "provenance": provenance, "rows": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(provenance, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
