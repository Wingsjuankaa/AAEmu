#!/usr/bin/env python3
"""Extract every AA8 game_pak surface that can carry structured semantics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


# Rendering containers are included deliberately: some CryEngine formats are
# XML/text despite their extension. Media, mesh, animation and navigation data
# remain inventoried by the complete pak index but cannot define a server-side
# character bootstrap on their own.
STRUCTURED_EXTENSIONS = {
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

# World DAT/CTC are opaque level containers. They are included because they can
# hold transforms or entity data. BAI is a navigation mesh and is classified
# separately rather than treated as character-creation authority.
WORLD_OPAQUE_EXTENSIONS = {".ctc", ".dat"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--pak", required=True, type=Path)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--max-command-chars", type=int, default=28_000)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_entries(index: Path) -> tuple[list[dict[str, Any]], Counter[str]]:
    selected: list[dict[str, Any]] = []
    excluded_classes: Counter[str] = Counter()
    with index.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        for row in reader:
            name = row["name"].replace("\\", "/")
            extension = Path(name).suffix.lower()
            is_world_opaque = (
                name.lower().startswith("game/worlds/")
                and extension in WORLD_OPAQUE_EXTENSIONS
            )
            if extension in STRUCTURED_EXTENSIONS or is_world_opaque:
                selected.append(
                    {
                        "md5": row["md5"].upper(),
                        "name": name,
                        "size": int(row["size"]),
                        "surface": (
                            "world_opaque_container"
                            if is_world_opaque
                            else "structured_or_text_container"
                        ),
                    }
                )
            else:
                if extension == ".bai":
                    excluded_classes["navigation_mesh_bai"] += 1
                elif extension in {".dds", ".bmp", ".jpg", ".png", ".tga"}:
                    excluded_classes["raster_media"] += 1
                elif extension in {".caf", ".anm", ".fsq", ".lmg"}:
                    excluded_classes["animation"] += 1
                elif extension in {".cgf", ".chr"}:
                    excluded_classes["mesh_or_character_geometry"] += 1
                elif extension in {".fsb", ".wav", ".mp3"}:
                    excluded_classes["audio"] += 1
                elif extension == ".alb":
                    excluded_classes["lua_already_decompiled"] += 1
                else:
                    excluded_classes["other_binary_or_unclassified"] += 1
    selected.sort(key=lambda entry: entry["name"].lower())
    return selected, excluded_classes


def command_chunks(
    cli: Path,
    pak: Path,
    output: Path,
    entries: list[dict[str, Any]],
    max_chars: int,
) -> list[list[str]]:
    base = [str(cli), str(pak)]
    chunks: list[list[str]] = []
    current = list(base)
    current_chars = sum(len(value) + 3 for value in current) + 3
    for entry in entries:
        source = entry["name"]
        target = output / Path(source)
        arguments = ["-l", source, str(target)]
        extra_chars = sum(len(value) + 3 for value in arguments)
        if len(current) > len(base) and current_chars + extra_chars > max_chars:
            current.append("+x")
            chunks.append(current)
            current = list(base)
            current_chars = sum(len(value) + 3 for value in current) + 3
        current.extend(arguments)
        current_chars += extra_chars
    if len(current) > len(base):
        current.append("+x")
        chunks.append(current)
    return chunks


def main() -> int:
    options = parse_args()
    for path in (options.index, options.pak, options.cli):
        if not path.is_file():
            raise FileNotFoundError(path)
    options.output.mkdir(parents=True, exist_ok=True)

    entries, excluded_classes = read_entries(options.index)
    chunks = command_chunks(
        options.cli,
        options.pak,
        options.output,
        entries,
        options.max_command_chars,
    )
    failures: list[dict[str, Any]] = []
    for index, command in enumerate(chunks, start=1):
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if process.returncode != 0 or "[ERROR]" in process.stdout:
            failures.append(
                {
                    "chunk": index,
                    "output": process.stdout[-4000:],
                    "returncode": process.returncode,
                }
            )
        if index % 25 == 0 or index == len(chunks):
            print(f"chunks={index}/{len(chunks)} failures={len(failures)}", flush=True)

    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    extracted_bytes = 0
    extracted_by_surface: Counter[str] = Counter()
    for entry in entries:
        target = options.output / Path(entry["name"])
        if not target.is_file():
            missing.append(entry["name"])
            continue
        actual_size = target.stat().st_size
        extracted_bytes += actual_size
        extracted_by_surface[entry["surface"]] += 1
        if actual_size != entry["size"]:
            size_mismatches.append(
                {
                    "actual": actual_size,
                    "expected": entry["size"],
                    "name": entry["name"],
                }
            )

    selected_extensions = Counter(
        Path(entry["name"]).suffix.lower() or "<none>" for entry in entries
    )
    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": {
            "excluded_classes": dict(sorted(excluded_classes.items())),
            "note": (
                "Every pak entry remains anchored by the complete index. This "
                "extraction covers every structured/text container plus all "
                "world DAT/CTC containers. Excluded media, geometry, animation, "
                "audio and navigation meshes cannot independently authorize a "
                "server-side character bootstrap relation."
            ),
        },
        "extraction": {
            "chunks": len(chunks),
            "extracted_bytes": extracted_bytes,
            "extracted_by_surface": dict(sorted(extracted_by_surface.items())),
            "failures": failures,
            "missing": missing,
            "selected_entries": len(entries),
            "selected_extensions": dict(sorted(selected_extensions.items())),
            "size_mismatches": size_mismatches,
        },
        "schema_version": 1,
        "sources": {
            "index": options.index.resolve().as_posix(),
            "index_sha256": sha256(options.index),
            "output": options.output.resolve().as_posix(),
            "pak": options.pak.resolve().as_posix(),
            "pak_bytes": options.pak.stat().st_size,
        },
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if not failures and not missing and not size_mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())
