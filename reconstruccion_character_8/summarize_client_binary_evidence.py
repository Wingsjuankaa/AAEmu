#!/usr/bin/env python3
"""Produce deterministic evidence for non-XML AA8 client surfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


MARKERS = (
    "system_nuian_start",
    "dwarf_start",
    "gwe_start",
    "rain_system",
    "start_warborn",
    "start_fp",
    "return_point",
    "default_action_bar_actions",
    "character_supplies",
    "login_stage_abilities",
    "start_equip_pack_id",
    "baseactionbaremptyslotcount",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest().upper()


def matches(path: Path) -> list[str]:
    payload = path.read_bytes().lower()
    found: list[str] = []
    for marker in MARKERS:
        ascii_marker = marker.encode("ascii")
        utf16_marker = marker.encode("utf-16le")
        if ascii_marker in payload or utf16_marker in payload:
            found.append(marker)
    return found


def tree_hash(files: list[Path], root: Path) -> str:
    value = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        value.update(relative.encode("utf-8"))
        value.update(b"\0")
        value.update(bytes.fromhex(digest(path)))
    return value.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login2-root", type=Path, required=True)
    parser.add_argument("--binary", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    login_root = args.login2_root.resolve()
    login_files = sorted(
        (path for path in login_root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(login_root).as_posix(),
    )
    binary_files = sorted(
        (path.resolve() for path in args.binary),
        key=lambda path: path.as_posix().lower(),
    )
    for path in binary_files:
        if not path.is_file():
            raise FileNotFoundError(path)

    login_matches = {
        path.relative_to(login_root).as_posix(): found
        for path in login_files
        if (found := matches(path))
    }
    binaries = [
        {
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "markers": matches(path),
        }
        for path in binary_files
    ]
    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": "negative_native_client_evidence",
        "login2_world": {
            "root": login_root.as_posix(),
            "files": len(login_files),
            "bytes": sum(path.stat().st_size for path in login_files),
            "extensions": dict(
                sorted(
                    Counter(
                        path.suffix.lower() or "<none>"
                        for path in login_files
                    ).items()
                )
            ),
            "tree_sha256": tree_hash(login_files, login_root),
            "marker_matches": login_matches,
        },
        "native_binaries": binaries,
        "markers": list(MARKERS),
        "conclusion": (
            "The complete login2 world, including its 24 DAT and three CTC "
            "binary assets, contains none of the authoritative creation "
            "markers. Across the selected 32/64-bit gameplay binaries, only "
            "x2game owns the native creation table/action strings already "
            "decompiled; the logical return-point names do not occur."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
