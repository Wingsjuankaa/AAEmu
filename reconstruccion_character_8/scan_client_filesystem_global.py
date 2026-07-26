#!/usr/bin/env python3
"""Inventory and focus-scan every unpacked AA8 client file outside game_pak."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PATTERNS = {
    "action_bar": re.compile(
        rb"action[_ ]?bar|actionbar|auto[_ ]?register|"
        rb"default_action_bar_actions|cannot_auto_register_skill",
        re.IGNORECASE,
    ),
    "capacity": re.compile(
        rb"(?:num|initial|default)?[_ ]?(?:bag|bank|inven(?:tory)?)[_ ]?"
        rb"(?:slots?|capacity)|"
        rb"(?:slots?|capacity)[_ ]?(?:bag|bank|inven(?:tory)?)",
        re.IGNORECASE,
    ),
    "character_creation": re.compile(
        rb"character[_ ]?(?:create|creation|supplies)|"
        rb"(?:create|creation)[_ ]?character|login_stage_abilities|"
        rb"start_equip_pack_id",
        re.IGNORECASE,
    ),
    "spawn_transform": re.compile(
        rb"(?:character|player|login|start)[_ ]{0,3}"
        rb"(?:spawn|position|rotation|transform)|"
        rb"(?:spawn|position|rotation|transform)[_ ]{0,3}"
        rb"(?:character|player|login|start)",
        re.IGNORECASE,
    ),
    "starter_items": re.compile(
        rb"character_supplies|starter[_ ]?(?:item|supply)|"
        rb"initial[_ ]?(?:item|equipment|supply)|start[_ ]?equip",
        re.IGNORECASE,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hit-cap-per-file", type=int, default=100)
    return parser.parse_args()


def strings(data: bytes) -> bytes:
    ascii_strings = re.findall(rb"[\x20-\x7e]{4,}", data)
    utf16_strings = [
        value[::2] for value in re.findall(rb"(?:[\x20-\x7e]\x00){4,}", data)
    ]
    return b"\n".join(ascii_strings + utf16_strings)


def main() -> int:
    options = parse_args()
    if not options.root.is_dir():
        raise FileNotFoundError(options.root)

    entries: list[dict[str, Any]] = []
    extension_counts: Counter[str] = Counter()
    hit_counts: Counter[str] = Counter()
    total_bytes = 0
    for path in sorted(options.root.rglob("*")):
        if not path.is_file() or path.name.lower() == "game_pak":
            continue
        relative = path.relative_to(options.root).as_posix()
        data = path.read_bytes()
        total_bytes += len(data)
        extension = path.suffix.lower() or "<none>"
        extension_counts[extension] += 1
        searchable = strings(data)
        file_hits: list[dict[str, Any]] = []
        for category, pattern in PATTERNS.items():
            for match in pattern.finditer(searchable):
                hit_counts[category] += 1
                if len(file_hits) < options.hit_cap_per_file:
                    start = max(0, match.start() - 100)
                    end = min(len(searchable), match.end() + 140)
                    file_hits.append(
                        {
                            "category": category,
                            "match": match.group().decode(
                                "ascii", errors="replace"
                            ),
                            "snippet": searchable[start:end]
                            .decode("utf-8", errors="replace")
                            .replace("\x00", ""),
                        }
                    )
        entries.append(
            {
                "bytes": len(data),
                "extension": extension,
                "focus_hits": file_hits,
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest().upper(),
            }
        )

    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": {
            "focus_hits_are_authority": False,
            "note": (
                "Every unpacked client file outside game_pak is hashed and "
                "focus-scanned. Hits locate consumers or future review surfaces; "
                "they do not provide server-side creation values by themselves."
            ),
        },
        "files": entries,
        "inventory": {
            "bytes": total_bytes,
            "extension_counts": dict(sorted(extension_counts.items())),
            "file_count": len(entries),
            "hit_counts": dict(sorted(hit_counts.items())),
        },
        "schema_version": 1,
        "source": options.root.resolve().as_posix(),
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
