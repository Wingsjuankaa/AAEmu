#!/usr/bin/env python3
"""Extract uncommon AA8 text/structured formats omitted by the bulk class pass."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


SUPPLEMENTAL_EXTENSIONS = {
    ".ccc",
    ".cnd",
    ".cry",
    ".dbh",
    ".filters",
    ".joy",
    ".lua",
    ".manifest",
    ".mhtml",
    ".node",
    ".py",
    ".removed",
    ".vcxproj",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--pak", required=True, type=Path)
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> int:
    options = parse_args()
    entries: list[dict[str, Any]] = []
    with options.index.open("r", encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter=";"):
            name = row["name"].replace("\\", "/")
            if Path(name).suffix.lower() in SUPPLEMENTAL_EXTENSIONS:
                entries.append(
                    {
                        "md5": row["md5"].upper(),
                        "name": name,
                        "size": int(row["size"]),
                    }
                )
    entries.sort(key=lambda value: value["name"].lower())

    options.output.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, Any]] = []
    for entry in entries:
        target = options.output / Path(entry["name"])
        target.parent.mkdir(parents=True, exist_ok=True)
        process = subprocess.run(
            [
                str(options.cli),
                str(options.pak),
                "-l",
                entry["name"],
                str(target),
                "+x",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if process.returncode != 0 or "[ERROR]" in process.stdout:
            failures.append(
                {
                    "name": entry["name"],
                    "output": process.stdout[-2000:],
                    "returncode": process.returncode,
                }
            )

    missing: list[str] = []
    mismatches: list[dict[str, Any]] = []
    extracted_bytes = 0
    for entry in entries:
        target = options.output / Path(entry["name"])
        if not target.is_file():
            missing.append(entry["name"])
            continue
        data = target.read_bytes()
        extracted_bytes += len(data)
        actual_md5 = hashlib.md5(data).hexdigest().upper()
        if len(data) != entry["size"] or actual_md5 != entry["md5"]:
            mismatches.append(
                {
                    "actual_md5": actual_md5,
                    "actual_size": len(data),
                    "expected_md5": entry["md5"],
                    "expected_size": entry["size"],
                    "name": entry["name"],
                }
            )

    payload = {
        "authority": "Kakao 8.0.3.12 r558734",
        "classification": {
            "note": (
                "Supplement to the bulk structured/world extraction. It covers "
                "every uncommon text, project, animation-header and structured "
                "format that remained semantically reviewable. compact.sqlite is "
                "covered through the separately decrypted compact authority."
            )
        },
        "extraction": {
            "entries": len(entries),
            "extension_counts": dict(
                sorted(
                    Counter(
                        Path(entry["name"]).suffix.lower() for entry in entries
                    ).items()
                )
            ),
            "extracted_bytes": extracted_bytes,
            "failures": failures,
            "missing": missing,
            "mismatches": mismatches,
        },
        "schema_version": 1,
        "sources": {
            "index": options.index.resolve().as_posix(),
            "index_sha256": sha256(options.index),
            "pak": options.pak.resolve().as_posix(),
        },
    }
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    clean = not failures and not missing and not mismatches
    return 0 if clean else 2


if __name__ == "__main__":
    raise SystemExit(main())
