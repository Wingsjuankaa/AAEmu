#!/usr/bin/env python3
"""Disable only the unconditional Chinese FollowMe tab in AA10 r575 eventcenter.alb.

The Returns ALB is a Lua 5.1 binary chunk.  The validation closure at source lines 77-79 is the
three-instruction function ``return true``.  This patch changes its single LOADBOOL operand from
true to false while preserving every byte other than that operand and the exact entry length.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_SHA256 = "C88D59E1423885C3DE0609A303932C6E3439FCD11A16BDC2090F9E8187035603"
PATCHED_SHA256 = "E9C037CBAAFCF6D1806BAB9071A7D20AE5CDE1F522DEAC2BE9494691998FE6FF"
EXPECTED_SIZE = 18_813
INSTRUCTION_OFFSET = 3_616
LOADBOOL_TRUE = bytes.fromhex("02 00 80 00")
LOADBOOL_FALSE = bytes.fromhex("02 00 00 00")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    data = bytearray(source.read_bytes())
    current_hash = sha256(data)

    if len(data) != EXPECTED_SIZE or current_hash != EXPECTED_SHA256:
        raise SystemExit(
            "refusing unexpected eventcenter.alb: "
            f"bytes={len(data)} sha256={current_hash}"
        )
    if data[INSTRUCTION_OFFSET:INSTRUCTION_OFFSET + 4] != LOADBOOL_TRUE:
        raise SystemExit("FollowMe validation LOADBOOL signature was not found at the proven offset")

    data[INSTRUCTION_OFFSET:INSTRUCTION_OFFSET + 4] = LOADBOOL_FALSE
    patched_hash = sha256(data)
    if len(data) != EXPECTED_SIZE or patched_hash != PATCHED_SHA256:
        raise SystemExit(
            f"post-patch validation failed: bytes={len(data)} sha256={patched_hash}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(
        f"patched: {source}\n"
        f"output:  {output}\n"
        f"bytes:   {len(data)}\n"
        f"sha256:  {current_hash} -> {patched_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
