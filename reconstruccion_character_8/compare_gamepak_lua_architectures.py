#!/usr/bin/env python3
"""Compare the complete AA8 32-bit and 64-bit decompiled Lua trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


FOCUS_PATTERNS = {
    "action_bar": re.compile(
        r"action.?bar|auto.?register|shortcut.?slot|establishslot", re.IGNORECASE
    ),
    "capacity": re.compile(
        r"(?:bag|bank|inventory).{0,24}capacit|"
        r"capacit.{0,24}(?:bag|bank|inventory)",
        re.IGNORECASE,
    ),
    "character_creation": re.compile(
        r"character.?creat|creat.{0,16}character|endcharactercreate",
        re.IGNORECASE,
    ),
    "initial_items": re.compile(
        r"character.?suppl|start.?equip|initial.{0,16}(?:item|equip|supply)",
        re.IGNORECASE,
    ),
    "login_stage": re.compile(r"login.?stage|starting.?zone", re.IGNORECASE),
    "spawn_transform": re.compile(
        r"(?:character|player).{0,24}(?:spawn|start).{0,24}"
        r"(?:position|rotation|transform)|"
        r"(?:position|rotation|transform).{0,24}"
        r"(?:character|player).{0,24}(?:spawn|start)",
        re.IGNORECASE,
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lua32", required=True, type=Path)
    parser.add_argument("--lua64", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def collect(root: Path, excluded_root: Path | None = None) -> dict[str, Path]:
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*.lua"))
        if excluded_root is None
        or not path.resolve().is_relative_to(excluded_root.resolve())
    }


def focus_hits(path: Path, relative: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_number, line in enumerate(text.splitlines(), start=1):
        categories = [
            category
            for category, pattern in FOCUS_PATTERNS.items()
            if pattern.search(line)
        ]
        if categories:
            hits.append(
                {
                    "categories": categories,
                    "line": line_number,
                    "path": relative,
                    "text": line.strip()[:500],
                }
            )
    return hits


def main() -> int:
    options = parse_args()
    for root in (options.lua32, options.lua64):
        if not root.is_dir():
            raise FileNotFoundError(root)

    nested_lua64 = (
        options.lua64
        if options.lua64.resolve().is_relative_to(options.lua32.resolve())
        else None
    )
    files32 = collect(options.lua32, nested_lua64)
    files64 = collect(options.lua64)
    paths32 = set(files32)
    paths64 = set(files64)
    common = sorted(paths32 & paths64)

    differences: list[dict[str, Any]] = []
    combined_hasher = hashlib.sha256()
    hits: list[dict[str, Any]] = []
    for relative in common:
        data32 = files32[relative].read_bytes()
        data64 = files64[relative].read_bytes()
        hash32 = sha256_bytes(data32)
        hash64 = sha256_bytes(data64)
        combined_hasher.update(relative.encode("utf-8"))
        combined_hasher.update(b"\0")
        combined_hasher.update(bytes.fromhex(hash32))
        if hash32 != hash64:
            differences.append(
                {
                    "lua32_sha256": hash32,
                    "lua64_sha256": hash64,
                    "path": relative,
                }
            )
        hits.extend(focus_hits(files32[relative], relative))

    payload = {
        "classification": {
            "architecture_relation": (
                "byte_identical_decompiled_source"
                if not differences and paths32 == paths64
                else "source_difference_requires_review"
            ),
            "focus_hits_are_authority": False,
            "note": (
                "Keyword hits identify review surfaces only. They do not establish "
                "native character-creation values or relations."
            ),
        },
        "comparison": {
            "common_files": len(common),
            "content_differences": differences,
            "lua32_files": len(files32),
            "lua32_only": sorted(paths32 - paths64),
            "lua64_files": len(files64),
            "lua64_only": sorted(paths64 - paths32),
            "source_tree_sha256": combined_hasher.hexdigest().upper(),
        },
        "focus_hits": hits,
        "schema_version": 1,
        "sources": {
            "lua32_root": str(options.lua32.resolve()),
            "lua64_root": str(options.lua64.resolve()),
        },
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    clean = not differences and paths32 == paths64
    return 0 if clean else 2


if __name__ == "__main__":
    raise SystemExit(main())
