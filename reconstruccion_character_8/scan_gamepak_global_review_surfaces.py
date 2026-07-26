#!/usr/bin/env python3
"""Scan all extracted AA8 structured and opaque world review surfaces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


PATTERNS = {
    "action_bar": re.compile(
        rb"action[_ ]?bar|actionbar|auto[_ ]?register|default_action_bar_actions|"
        rb"baseactionbaremptyslotcount",
        re.IGNORECASE,
    ),
    "capacity": re.compile(
        rb"(?:bag|bank|inven(?:tory)?)[_ ]?(?:slot|capacity)|"
        rb"(?:num|initial|default)[_ ]?(?:bag|bank|inven(?:tory)?)[_ ]?slots?",
        re.IGNORECASE,
    ),
    "character_creation": re.compile(
        rb"character[_ ]?(?:create|creation|supplies)|"
        rb"(?:create|creation)[_ ]?character|login_stage_abilities|"
        rb"start_equip_pack_id",
        re.IGNORECASE,
    ),
    "initial_items": re.compile(
        rb"character_supplies|starter[_ ]?(?:item|supply)|"
        rb"initial[_ ]?(?:item|equipment|supply)|start[_ ]?equip",
        re.IGNORECASE,
    ),
    "spawn_transform": re.compile(
        rb"(?:character|player|login|start)[_ ]{0,3}"
        rb"(?:spawn|position|rotation|transform)|"
        rb"(?:spawn|position|rotation|transform)[_ ]{0,3}"
        rb"(?:character|player|login|start)",
        re.IGNORECASE,
    ),
    "start_markers": re.compile(
        rb"system_nuian_start|dwarf_start|gwe_start|rain_system|"
        rb"start_warborn|start_fp",
        re.IGNORECASE,
    ),
}
CURRENT_FOCUS = {
    "action_bar",
    "capacity",
    "character_creation",
    "initial_items",
    "spawn_transform",
    "start_markers",
}
TEXT_EXTENSIONS = {
    ".animevents",
    ".bonelodxml",
    ".cal",
    ".cdf",
    ".cfg",
    ".csv",
    ".ent",
    ".g",
    ".html",
    ".ini",
    ".json",
    ".lyr",
    ".mtl",
    ".txt",
    ".xml",
}

DECODED_OUTPUT_MD5_EXCEPTIONS = {
    "easyanticheat/launcher/settings_32.json": {
        "decoded_md5": "CA6E5F2A940AC30AA8DA3D8D7971E37C",
        "index_md5": "7B98D12B6CED6D002DCB6B75E53A6E34",
        "sha256": "9A44A8EF0272A17E6CFCB3A760C8A7AE4902D8108DF69B3F5440C3AEC0828F52",
    },
    "easyanticheat/launcher/settings_64.json": {
        "decoded_md5": "B46E48538C748171A46626079AACE779",
        "index_md5": "31E2380D13BA35FE86E5FFF7CB0E4962",
        "sha256": "A6D2D0F5044B49498E8D8AEF03AFF93EE2927F2500297AB9F4844818B5C8BC2F",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hit-cap", type=int, default=2_000)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_index(path: Path) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter=";"):
            name = row["name"].replace("\\", "/")
            entries[name.lower()] = {
                "md5": row["md5"].upper(),
                "name": name,
                "size": int(row["size"]),
            }
    return entries


def printable_ascii(data: bytes) -> bytes:
    return b"\n".join(re.findall(rb"[\x20-\x7e]{4,}", data))


def printable_utf16le(data: bytes) -> bytes:
    strings = re.findall(rb"(?:[\x20-\x7e]\x00){4,}", data)
    return b"\n".join(value[::2] for value in strings)


def snippets(data: bytes, match: re.Match[bytes]) -> str:
    start = max(0, match.start() - 120)
    end = min(len(data), match.end() + 180)
    return data[start:end].decode("utf-8", errors="replace").replace("\x00", "")


def scan_file(
    path: Path,
    input_root: Path,
    index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    relative = path.relative_to(input_root).as_posix()
    index_entry = index.get(relative.lower())
    if index_entry is None:
        return {"missing_index_entry": relative}

    data = path.read_bytes()
    extension = path.suffix.lower() or "<none>"
    actual_md5 = hashlib.md5(data).hexdigest().upper()
    mismatch = None
    decoded_md5_difference = None
    md5_unavailable = False
    if index_entry["md5"] == "00000000000000000000000000000000":
        md5_unavailable = True
    elif actual_md5 != index_entry["md5"]:
        exception = DECODED_OUTPUT_MD5_EXCEPTIONS.get(relative.lower())
        actual_sha256 = hashlib.sha256(data).hexdigest().upper()
        if (
            exception is not None
            and actual_md5 == exception["decoded_md5"]
            and index_entry["md5"] == exception["index_md5"]
            and actual_sha256 == exception["sha256"]
        ):
            decoded_md5_difference = {
                "decoded_md5": actual_md5,
                "decoded_sha256": actual_sha256,
                "index_md5": index_entry["md5"],
                "path": relative,
                "proof": (
                    "AAPakCLI decoded the same bytes in two independent "
                    "extractions; the pak index digest is stale for this EAC "
                    "launcher JSON."
                ),
            }
        else:
            mismatch = {
                "actual": actual_md5,
                "expected": index_entry["md5"],
                "path": relative,
            }

    magic = None
    if extension in TEXT_EXTENSIONS:
        searchable = data.replace(b"\x00", b"")
    else:
        magic = data[:8].hex().upper() or "<empty>"
        searchable = printable_ascii(data) + b"\n" + printable_utf16le(data)

    file_hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for category, pattern in PATTERNS.items():
        for match in pattern.finditer(searchable):
            file_hits[category].append(
                {
                    "match": match.group().decode("ascii", errors="replace"),
                    "path": relative,
                    "snippet": snippets(searchable, match),
                }
            )
    return {
        "bytes": len(data),
        "extension": extension,
        "hits": file_hits,
        "magic": magic,
        "decoded_md5_difference": decoded_md5_difference,
        "md5_mismatch": mismatch,
        "md5_unavailable": md5_unavailable,
        "path": relative,
    }


def main() -> int:
    options = parse_args()
    if not options.index.is_file():
        raise FileNotFoundError(options.index)
    if not options.input.is_dir():
        raise FileNotFoundError(options.input)

    index = read_index(options.index)
    hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    hit_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    magic_counts: Counter[str] = Counter()
    md5_mismatches: list[dict[str, Any]] = []
    decoded_md5_differences: list[dict[str, Any]] = []
    md5_unavailable: list[str] = []
    missing_index_entries: list[str] = []
    processed_bytes = 0
    processed_files = 0

    paths = sorted(path for path in options.input.rglob("*") if path.is_file())
    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        results = executor.map(
            lambda path: scan_file(path, options.input, index),
            paths,
        )
        for result in results:
            if "missing_index_entry" in result:
                missing_index_entries.append(result["missing_index_entry"])
                continue
            processed_files += 1
            processed_bytes += int(result["bytes"])
            extension_counts[result["extension"]] += 1
            if result["magic"] is not None:
                magic_counts[result["magic"]] += 1
            if result["md5_unavailable"]:
                md5_unavailable.append(result["path"])
            if result["decoded_md5_difference"] is not None:
                decoded_md5_differences.append(
                    result["decoded_md5_difference"]
                )
            if result["md5_mismatch"] is not None:
                md5_mismatches.append(result["md5_mismatch"])
            for category, file_hits in result["hits"].items():
                hit_counts[category] += len(file_hits)
                remaining = options.hit_cap - len(hits[category])
                if remaining > 0:
                    hits[category].extend(file_hits[:remaining])
            if processed_files % 5_000 == 0:
                print(
                    f"files={processed_files}/{len(paths)} "
                    f"bytes={processed_bytes}",
                    flush=True,
                )

    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": {
            "content_hits_are_authority": False,
            "current_focus": sorted(CURRENT_FOCUS),
            "note": (
                "All selected structured/text containers and opaque world DAT/CTC "
                "containers were scanned. Hits locate review surfaces only; they "
                "do not prove a gameplay relation without a native consumer."
            ),
        },
        "integrity": {
            "decoded_output_md5_differences": decoded_md5_differences,
            "md5_mismatches": md5_mismatches,
            "md5_unavailable_in_source_index": md5_unavailable,
            "missing_index_entries": missing_index_entries,
            "note": (
                "A zero MD5 in the native pak index means the source index does "
                "not publish a content digest. Those entries remain covered by "
                "the exact indexed size and are reported separately; zero is "
                "never treated as an expected content hash."
            ),
        },
        "scan": {
            "extension_counts": dict(sorted(extension_counts.items())),
            "hit_counts": dict(sorted(hit_counts.items())),
            "hits_capped_at": options.hit_cap,
            "hits": {key: value for key, value in sorted(hits.items())},
            "opaque_magic_counts": dict(sorted(magic_counts.items())),
            "processed_bytes": processed_bytes,
            "processed_files": processed_files,
        },
        "schema_version": 1,
        "sources": {
            "index": options.index.resolve().as_posix(),
            "index_sha256": sha256(options.index),
            "input": options.input.resolve().as_posix(),
        },
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    clean = not md5_mismatches and not missing_index_entries
    return 0 if clean else 2


if __name__ == "__main__":
    raise SystemExit(main())
