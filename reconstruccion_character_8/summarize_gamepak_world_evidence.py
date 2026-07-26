#!/usr/bin/env python3
"""Create a deterministic manifest for the exhaustive AA8 game_pak XML sweep."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


NATIVE_RETURN_NAMES = (
    "system_nuian_start",
    "dwarf_start",
    "Gwe_start",
    "rain_system",
    "start_warborn",
    "start_fp",
)

MISSION_MARKERS = ("Spawn_Nuian", "Spawn_elf", "Spawn_andelph")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def tree_summary(root: Path) -> dict[str, object]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    aggregate = hashlib.sha256()
    total_bytes = 0
    exact_return_hits: dict[str, list[str]] = {
        name: [] for name in NATIVE_RETURN_NAMES
    }
    mission_hits: dict[str, list[str]] = {name: [] for name in MISSION_MARKERS}
    for path in files:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        file_hash = hashlib.sha256(data).hexdigest().upper()
        total_bytes += len(data)
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(len(data)).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(file_hash.encode("ascii"))
        aggregate.update(b"\n")
        text = data.decode("utf-8", errors="ignore")
        for name in NATIVE_RETURN_NAMES:
            if name in text:
                exact_return_hits[name].append(relative)
        for marker in MISSION_MARKERS:
            if marker in text:
                mission_hits[marker].append(relative)
    return {
        "root": str(root.resolve()),
        "files": len(files),
        "bytes": total_bytes,
        "tree_sha256": aggregate.hexdigest().upper(),
        "native_return_name_hits": exact_return_hits,
        "legacy_mission_marker_hits": mission_hits,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--xml-root", required=True, type=Path)
    parser.add_argument("--entity-root", required=True, type=Path)
    parser.add_argument("--mission-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    options = parse_args()
    index_lines = options.index.read_text(
        encoding="utf-8", errors="strict"
    ).splitlines()
    indexed_xml = sum(
        1 for line in index_lines[1:] if line.split(";", 1)[0].lower().endswith(".xml")
    )
    result = {
        "format_version": 1,
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "classification": "exhaustive_negative_spawn_transform_evidence",
        "game_pak_index": {
            "path": str(options.index.resolve()),
            "sha256": sha256(options.index),
            "rows": max(0, len(index_lines) - 1),
            "xml_rows": indexed_xml,
        },
        "all_xml": tree_summary(options.xml_root),
        "world_client_entities": tree_summary(options.entity_root),
        "world_missions": tree_summary(options.mission_root),
        "conclusion": {
            "authoritative_six_race_xyz_quaternion_found": False,
            "reason": (
                "All indexed XML was extracted and searched. None of the six "
                "native return-point editor names occurs. Three legacy mission "
                "spawn markers are incomplete and do not cover the six native "
                "AA8 starts, so they are excluded as server spawn authority."
            ),
        },
    }
    if result["all_xml"]["files"] != indexed_xml:
        raise RuntimeError(
            f"XML extraction is incomplete: index={indexed_xml}, "
            f"files={result['all_xml']['files']}"
        )
    if any(result["all_xml"]["native_return_name_hits"].values()):
        raise RuntimeError("an exact native return-point name unexpectedly matched")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "written": str(options.output.resolve()),
        "xml_files": result["all_xml"]["files"],
        "xml_bytes": result["all_xml"]["bytes"],
        "tree_sha256": result["all_xml"]["tree_sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
