from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable


TOKENS = (
    "quest_component_texts",
    "quest_component_text_kind_id",
    "start - texts - body",
    "progress - texts - body",
    "ready - texts - body",
    "reward - texts - body",
    "doodad_phase_msg",
    "quest_context_objective_event",
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    ) + "\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _manifest_digest(rows: list[dict[str, object]]) -> str:
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _encodings(token: str) -> tuple[bytes, bytes]:
    lowered = token.lower()
    return lowered.encode("utf-8"), lowered.encode("utf-16-le")


def _scan_root(root: Path, *, suffixes: set[str]) -> dict[str, object]:
    inventory: list[dict[str, object]] = []
    matches: list[dict[str, object]] = []
    total_bytes = 0
    for path in sorted(
        (
            candidate
            for candidate in root.rglob("*")
            if candidate.is_file()
            and candidate.suffix.lower() in suffixes
        ),
        key=lambda value: value.relative_to(root).as_posix().lower(),
    ):
        payload = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        digest = _sha256_bytes(payload)
        total_bytes += len(payload)
        inventory.append(
            {"path": relative, "bytes": len(payload), "sha256": digest}
        )
        lowered = payload.lower()
        hits = []
        for token in TOKENS:
            utf8, utf16 = _encodings(token)
            representations = []
            if utf8 in lowered:
                representations.append("utf8_or_ascii")
            if utf16 in lowered:
                representations.append("utf16le")
            if representations:
                hits.append(
                    {"token": token, "representations": representations}
                )
        if hits:
            matches.append(
                {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": digest,
                    "hits": hits,
                }
            )
    return {
        "root": root.resolve().as_posix(),
        "suffixes": sorted(suffixes),
        "files_scanned": len(inventory),
        "bytes_scanned": total_bytes,
        "inventory_sha256": _manifest_digest(inventory),
        "matches": matches,
    }


def build_snapshot(
    *,
    client_root: Path,
    lua64_root: Path,
    lua32_root: Path,
    xml_root: Path,
) -> dict[str, object]:
    roots: list[tuple[Path, set[str], str]] = [
        (client_root / "bin32", {".dll", ".exe"}, "client_binary"),
        (client_root / "bin64", {".dll", ".exe"}, "client_binary"),
        (lua64_root, {".lua"}, "gamepak_lua64"),
        (lua32_root, {".lua"}, "gamepak_lua32"),
        (xml_root, {".xml"}, "gamepak_xml"),
    ]
    scans = []
    for root, suffixes, kind in roots:
        if not root.is_dir():
            raise FileNotFoundError(root)
        scan = _scan_root(root, suffixes=suffixes)
        scan["kind"] = kind
        scans.append(scan)
    return {
        "format": "AA8_COMPONENT_TEXT_SURFACE_SNAPSHOT_V1",
        "tokens": list(TOKENS),
        "scans": scans,
        "totals": {
            "files_scanned": sum(int(scan["files_scanned"]) for scan in scans),
            "bytes_scanned": sum(int(scan["bytes_scanned"]) for scan in scans),
            "matching_files": sum(len(scan["matches"]) for scan in scans),
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--lua64-root", type=Path, required=True)
    parser.add_argument("--lua32-root", type=Path, required=True)
    parser.add_argument("--xml-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    options = _parser().parse_args(argv)
    snapshot = build_snapshot(
        client_root=options.client_root,
        lua64_root=options.lua64_root,
        lua32_root=options.lua32_root,
        xml_root=options.xml_root,
    )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(_canonical_json(snapshot), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
