#!/usr/bin/env python3
"""Hash and marker-scan every decrypted AA8 cached-result stream."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MARKERS = (
    "system_nuian_start",
    "dwarf_start",
    "gwe_start",
    "rain_system",
    "start_warborn",
    "start_fp",
    "default_action_bar_actions",
    "character_supplies",
    "login_stage_abilities",
    "start_equip_pack_id",
    "baseactionbaremptyslotcount",
    "numinvenslots",
    "numbankslots",
    "invenslots",
    "bankslots",
    "auto_register_to_actionbar",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def scan(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    lowered = data.lower()
    digest = hashlib.sha256(data).hexdigest().upper()
    hits: list[dict[str, object]] = []
    for marker in MARKERS:
        for encoding, needle in (
            ("ascii", marker.encode("ascii")),
            ("utf16le", marker.encode("utf-16le")),
        ):
            offset = 0
            while True:
                offset = lowered.find(needle, offset)
                if offset < 0:
                    break
                hits.append(
                    {
                        "encoding": encoding,
                        "marker": marker,
                        "offset": offset,
                    }
                )
                offset += len(needle)
    hits.sort(key=lambda value: (int(value["offset"]), str(value["marker"])))
    return {
        "bytes": len(data),
        "hits": hits,
        "path": path.resolve().as_posix(),
        "sha256": digest,
    }


def main() -> int:
    options = parse_args()
    streams = [
        scan(path)
        for path in sorted(options.root.glob("game*"), key=lambda item: item.name)
        if path.is_file()
    ]
    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": {
            "marker_hits_are_authority": False,
            "note": (
                "Every decrypted cached-result byte is covered. These streams "
                "carry row payloads without table names; a numeric relation is "
                "accepted only when an x2game.dll loader proves its layout and "
                "result boundary."
            ),
        },
        "inventory": {
            "bytes": sum(int(stream["bytes"]) for stream in streams),
            "files": len(streams),
            "marker_hits": sum(len(stream["hits"]) for stream in streams),
        },
        "schema_version": 1,
        "streams": streams,
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
