#!/usr/bin/env python3
"""Decompile extracted AA8 Lua 5.1 ALB files with reproducible provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--java", required=True, type=Path)
    parser.add_argument("--unluac", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def normalize_alb(data: bytes, source: Path) -> bytes:
    if len(data) < 12 or data[:5] != b"\x1bLuaQ":
        raise RuntimeError(f"{source}: not an AA8 Lua 5.1 ALB")
    normalized = bytearray(data)
    # AA8 stores sizeof(lua_Number)=8 at byte 11. unluac expects the
    # standard Lua 5.1 integrality test byte (0) at that position.
    if normalized[11] not in (0, 8):
        raise RuntimeError(
            f"{source}: unexpected Lua number integrality byte {normalized[11]}"
        )
    normalized[11] = 0
    return bytes(normalized)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    options = parse_args()
    for path in (options.input, options.java, options.unluac):
        if not path.exists():
            raise FileNotFoundError(path)

    sources = sorted(options.input.rglob("*.alb"))
    if not sources:
        raise RuntimeError(f"no ALB files below {options.input}")

    results: list[dict[str, Any]] = []
    failures = 0
    for source in sources:
        relative = source.relative_to(options.input)
        luac = options.output / relative.with_suffix(".luac")
        lua = options.output / relative.with_suffix(".lua")
        luac.parent.mkdir(parents=True, exist_ok=True)
        source_data = source.read_bytes()
        entry: dict[str, Any] = {
            "path": relative.as_posix(),
            "source_sha256": sha256_bytes(source_data),
            "source_size": len(source_data),
        }
        try:
            normalized = normalize_alb(source_data, source)
            luac.write_bytes(normalized)
            process = subprocess.run(
                [
                    str(options.java),
                    "-jar",
                    str(options.unluac),
                    str(luac),
                ],
                check=False,
                capture_output=True,
            )
            if process.returncode != 0:
                failures += 1
                entry["error"] = process.stderr.decode(
                    "utf-8", errors="replace"
                ).strip()
            else:
                lua.write_bytes(process.stdout)
                entry.update(
                    {
                        "luac_sha256": sha256(luac),
                        "lua_sha256": sha256(lua),
                        "lua_size": lua.stat().st_size,
                    }
                )
        except Exception as exception:
            failures += 1
            entry["error"] = str(exception)
        results.append(entry)

    write_json(
        options.manifest,
        {
            "format": "aa8-character-gamepak-decompilation-v1",
            "input": str(options.input.resolve()),
            "java": str(options.java.resolve()),
            "unluac": {
                "path": str(options.unluac.resolve()),
                "sha256": sha256(options.unluac),
            },
            "source_count": len(sources),
            "decompiled_count": len(sources) - failures,
            "failure_count": failures,
            "files": results,
        },
    )
    print(
        json.dumps(
            {
                "sources": len(sources),
                "decompiled": len(sources) - failures,
                "failures": failures,
                "manifest": str(options.manifest.resolve()),
            },
            indent=2,
        )
    )
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
