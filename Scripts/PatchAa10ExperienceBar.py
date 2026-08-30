#!/usr/bin/env python3
"""Rebuild the AA10 r575 EXP-bar ALB from its matching retail Lua source.

The shipped binary chunk hard-disables two ancestral branches which remain correctly
guarded in the source entry. Compile that exact source, restore ArcheAge's Lua header,
and pad it to the original fixed PAK-entry length.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile


EXPECTED_SIZE = 16_807
ORIGINAL_SHA256 = "3831551627119BA57E5B7D360D834EAD2F835D19665DF207CFA89B880B15E6D1"
PATCHED_SHA256 = "2E53830616C656D666C29C2EA39A56AD4C21BCE1A9ED024A935572AA7CEE41F5"
SOURCE_SHA256 = "A80E862583E2DF20AADA0F81386B24379154D04CE335216CB8BC1D85D5786ECC"
LUA_51_HEADER = bytes.fromhex("1B 4C 75 61 51 00 01 04 08 04 08 00")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--alb", required=True, type=Path)
    parser.add_argument("--luac", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def build(source: Path, alb: Path, luac: Path, output: Path) -> str:
    source = source.resolve(strict=True)
    alb = alb.resolve(strict=True)
    luac = luac.resolve(strict=True)
    output = output.resolve()
    source_data = source.read_bytes()
    alb_data = alb.read_bytes()
    source_hash = sha256(source_data)
    current_hash = sha256(alb_data)

    if source_hash != SOURCE_SHA256:
        raise SystemExit(f"refusing unexpected exp_bar_set.lua SHA-256: {source_hash}")
    if len(alb_data) != EXPECTED_SIZE:
        raise SystemExit(f"refusing unexpected exp_bar_set.alb size: {len(alb_data)}")
    if current_hash == PATCHED_SHA256:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(alb_data)
        print(f"already patched: {alb}\noutput: {output}\nsha256: {current_hash}")
        return current_hash
    if current_hash != ORIGINAL_SHA256:
        raise SystemExit(f"refusing unexpected exp_bar_set.alb SHA-256: {current_hash}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa10-exp-bar-") as temp_name:
        compiled = Path(temp_name) / "exp_bar_set.alb"
        subprocess.run([str(luac), "-s", "-o", str(compiled), str(source)], check=True)
        data = bytearray(compiled.read_bytes())

    if data[:12] != LUA_51_HEADER:
        raise SystemExit(f"unexpected Lua 5.1 header: {data[:12].hex().upper()}")
    data[11] = 8  # ArcheAge stores sizeof(lua_Number), not the stock integral flag.
    if len(data) > EXPECTED_SIZE:
        raise SystemExit(f"compiled ALB exceeds the fixed entry: {len(data)} > {EXPECTED_SIZE}")
    data.extend(bytes(EXPECTED_SIZE - len(data)))

    patched_hash = sha256(data)
    if len(data) != EXPECTED_SIZE or patched_hash != PATCHED_SHA256:
        raise SystemExit(
            f"post-patch validation failed: bytes={len(data)} sha256={patched_hash}"
        )

    output.write_bytes(data)
    print(
        f"source:   {source}\n"
        f"original: {alb}\n"
        f"output:  {output}\n"
        f"bytes:   {len(data)}\n"
        f"sha256:  {current_hash} -> {patched_hash}"
    )
    return patched_hash


def main() -> int:
    args = parse_args()
    build(args.source, args.alb, args.luac, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
