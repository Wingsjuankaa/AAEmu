#!/usr/bin/env python3
"""Compare two deterministic TSV exports produced by PakIndexExport."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path, PurePosixPath


RELEVANT_PREFIXES = (
    "game/scriptsbin64/",
    "game/ui/",
    "game/custom/",
    "game/objects/item/",
    "game/worlds/",
    "game/sounds/archeragecustom/",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("left_index", type=Path)
    parser.add_argument("right_index", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--left-label", default="left")
    parser.add_argument("--right-label", default="right")
    return parser.parse_args()


def load(path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        fields = reader.fieldnames or []
        rows = {}
        for row in reader:
            name = row.get("Name") or row.get("name") or row.get("Path") or row.get("path")
            if not name:
                raise RuntimeError(f"No path/name column in {path}; columns={fields}")
            normalized = name.replace("\\", "/").lower()
            rows[normalized] = row
        return fields, rows


def value(row: dict[str, str], *candidates: str) -> str:
    lower = {key.lower(): val for key, val in row.items()}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return ""


def same_payload(left: dict[str, str], right: dict[str, str]) -> bool:
    return (
        value(left, "Size", "UncompressedSize") == value(right, "Size", "UncompressedSize")
        and value(left, "MD5", "Hash") == value(right, "MD5", "Hash")
    )


def prefix(name: str) -> str:
    parts = PurePosixPath(name).parts
    return "/".join(parts[:3]) if len(parts) >= 3 else "/".join(parts)


def write_names(path: Path, names: list[str]) -> None:
    path.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    _, left = load(args.left_index.resolve(strict=True))
    _, right = load(args.right_index.resolve(strict=True))

    left_names = set(left)
    right_names = set(right)
    common = left_names & right_names
    left_only = sorted(left_names - right_names)
    right_only = sorted(right_names - left_names)
    changed = sorted(name for name in common if not same_payload(left[name], right[name]))
    identical = len(common) - len(changed)
    relevant_left_only = [name for name in left_only if name.startswith(RELEVANT_PREFIXES)]
    relevant_changed = [name for name in changed if name.startswith(RELEVANT_PREFIXES)]

    write_names(output / f"{args.left_label}-only.txt", left_only)
    write_names(output / f"{args.right_label}-only.txt", right_only)
    write_names(output / "common-changed.txt", changed)
    write_names(output / f"{args.left_label}-only-relevant.txt", relevant_left_only)
    write_names(output / "common-changed-relevant.txt", relevant_changed)

    extensions = Counter(PurePosixPath(name).suffix.lower() or "<none>" for name in left_only)
    prefixes = Counter(prefix(name) for name in left_only)
    summary = {
        "left": {"label": args.left_label, "path": str(args.left_index.resolve()), "entries": len(left)},
        "right": {"label": args.right_label, "path": str(args.right_index.resolve()), "entries": len(right)},
        "common_entries": len(common),
        "common_identical_size_and_md5": identical,
        "common_changed_size_or_md5": len(changed),
        "left_only_entries": len(left_only),
        "right_only_entries": len(right_only),
        "left_only_relevant_entries": len(relevant_left_only),
        "common_changed_relevant_entries": len(relevant_changed),
        "left_only_extensions": dict(sorted(extensions.items(), key=lambda item: (-item[1], item[0]))),
        "left_only_prefixes": dict(sorted(prefixes.items(), key=lambda item: (-item[1], item[0]))[:50]),
        "classification_note": (
            "Pak membership/hash differences are structural candidates only. "
            "Custom assets and version-sensitive ALB bytecode require semantic validation before reuse."
        ),
    }
    summary_path = output / "pak-index-comparison.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(summary_path)
    print(json.dumps({key: summary[key] for key in (
        "common_entries", "common_identical_size_and_md5", "common_changed_size_or_md5",
        "left_only_entries", "right_only_entries")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
