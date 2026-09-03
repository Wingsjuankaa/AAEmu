#!/usr/bin/env python3
"""Build a deterministic AA10 reconstruction backlog from the current checkout.

The report is deliberately evidence-first.  It does not claim that a packet file,
client table or feature bit proves a working mechanic; instead it records the
observable implementation surfaces which must be reviewed together with the
hand-curated domain dossier in Docs/AA10ReconstructionBacklog_es.md.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path


MARKER_RE = re.compile(
    r"\bTODO\b|\bFIXME\b|NotImplementedException|NotSupportedException|"
    r"nothing acts|nothing constructs|not implemented",
    re.IGNORECASE,
)
ENUM_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\s*,")
REGISTER_RE = re.compile(r"typeof\(([A-Za-z_][A-Za-z0-9_]*)\)")

EXCLUDED_PARTS = {".git", "bin", "obj", ".idea", ".vs", "TestResults"}
CODE_SUFFIXES = {".cs", ".csproj", ".json", ".xml", ".sql"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments without damaging quoted JSON strings."""
    out: list[str] = []
    i = 0
    quoted = False
    escaped = False
    while i < len(text):
        char = text[i]
        if quoted:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            i += 1
            continue
        if char == '"':
            quoted = True
            out.append(char)
            i += 1
            continue
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        out.append(char)
        i += 1
    return "".join(out)


def load_flags(path: Path) -> dict[str, bool]:
    payload = json.loads(strip_json_comments(path.read_text(encoding="utf-8-sig")))
    return {str(k): bool(v) for k, v in payload["Features"]["Flags"].items()}


def feature_inventory(root: Path) -> dict[str, object]:
    enum_path = root / "AAEmu.Game/Models/Game/Features/Feature.cs"
    source_path = root / "AAEmu.Game/Configurations/Features.json"
    runtime_path = root / ".server_files/AAEmu.Game/Configurations/Features.json"

    enum_rows: list[tuple[str, int]] = []
    for line in enum_path.read_text(encoding="utf-8-sig").splitlines():
        match = ENUM_RE.match(line)
        if match:
            enum_rows.append((match.group(1), int(match.group(2))))

    source = load_flags(source_path)
    runtime = load_flags(runtime_path)
    bit_names: dict[int, list[str]] = collections.defaultdict(list)
    for name, bit in enum_rows:
        bit_names[bit].append(name)

    rows = []
    for bit in sorted(bit_names):
        names = bit_names[bit]
        source_enabled = any(source.get(name, False) for name in names)
        runtime_enabled = any(runtime.get(name, False) for name in names)
        rows.append(
            {
                "bit": bit,
                "names": names,
                "source_enabled": source_enabled,
                "runtime_enabled": runtime_enabled,
                "source_entries": {name: source[name] for name in names if name in source},
                "runtime_entries": {name: runtime[name] for name in names if name in runtime},
            }
        )

    return {
        "source": {
            "path": source_path.relative_to(root).as_posix(),
            "sha256": sha256(source_path),
        },
        "runtime_mount": {
            "path": runtime_path.relative_to(root).as_posix(),
            "sha256": sha256(runtime_path),
        },
        "unique_bits": len(rows),
        "runtime_enabled_bits": sum(row["runtime_enabled"] for row in rows),
        "runtime_disabled_bits": sum(not row["runtime_enabled"] for row in rows),
        "source_enabled_bits": sum(row["source_enabled"] for row in rows),
        "configuration_drift": [
            row for row in rows if row["source_enabled"] != row["runtime_enabled"]
        ],
        "features": rows,
    }


def source_category(relative: str) -> str:
    normalized = relative.replace("\\", "/")
    prefixes = (
        ("AAEmu.Game/Core/Packets/C2G/", "C2G"),
        ("AAEmu.Game/Core/Packets/G2C/", "G2C"),
        ("AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects/", "SpecialEffect"),
        ("AAEmu.Game/Models/Game/Skills/", "Skill"),
        ("AAEmu.Game/Core/Managers/", "Manager"),
        ("AAEmu.Game/Models/Game/Quests/", "Quest"),
        ("AAEmu.Game/Models/Game/Char/", "Character"),
        ("AAEmu.Game/Models/Game/Units/", "Unit"),
        ("AAEmu.Game/Models/Game/World/", "World"),
        ("AAEmu.Game/Models/Game/", "GameModel"),
        ("AAEmu.Login/", "Login"),
        ("AAEmu.UnitTests/", "Test"),
    )
    for prefix, category in prefixes:
        if normalized.startswith(prefix):
            return category
    return normalized.split("/", 1)[0]


def iter_source_files(root: Path):
    for project in sorted(root.glob("AAEmu.*")):
        if not project.is_dir():
            continue
        for path in sorted(project.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
                continue
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            yield path


def marker_inventory(root: Path) -> dict[str, object]:
    rows = []
    for path in iter_source_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if MARKER_RE.search(line):
                rows.append(
                    {
                        "path": relative,
                        "line": line_number,
                        "category": source_category(relative),
                        "text": line.strip(),
                    }
                )

    counts = collections.Counter(row["category"] for row in rows)
    file_count = len({row["path"] for row in rows})
    return {
        "marker_count": len(rows),
        "file_count": file_count,
        "by_category": dict(sorted(counts.items())),
        "markers": rows,
    }


def packet_inventory(root: Path) -> dict[str, object]:
    c2g_dir = root / "AAEmu.Game/Core/Packets/C2G"
    g2c_dir = root / "AAEmu.Game/Core/Packets/G2C"
    network = (root / "AAEmu.Game/Core/Network/Game/GameNetwork.cs").read_text(
        encoding="utf-8-sig"
    )
    registered = set(REGISTER_RE.findall(network))

    c2g = []
    for path in sorted(c2g_dir.glob("*.cs")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        packet_name = path.stem
        if packet_name in {"CSOffsets", "X2EnterWorldPacket"}:
            artifact = True
        else:
            artifact = False
        c2g.append(
            {
                "packet": packet_name,
                "path": path.relative_to(root).as_posix(),
                "registered": packet_name in registered,
                "known_artifact": artifact,
                "explicit_noop": "nothing acts" in text.lower(),
                "has_marker": bool(MARKER_RE.search(text)),
            }
        )

    g2c = []
    for path in sorted(g2c_dir.glob("*.cs")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        g2c.append(
            {
                "packet": path.stem,
                "path": path.relative_to(root).as_posix(),
                "explicit_no_constructor": "nothing constructs" in text.lower(),
                "has_marker": bool(MARKER_RE.search(text)),
            }
        )

    return {
        "C2G": {
            "file_count": len(c2g),
            "registered_count": sum(row["registered"] for row in c2g),
            "unregistered_count": sum(not row["registered"] for row in c2g),
            "explicit_noop_count": sum(row["explicit_noop"] for row in c2g),
            "registered_explicit_noop_count": sum(
                row["registered"] and row["explicit_noop"] for row in c2g
            ),
            "packets": c2g,
        },
        "G2C": {
            "file_count": len(g2c),
            "explicit_no_constructor_count": sum(
                row["explicit_no_constructor"] for row in g2c
            ),
            "packets": g2c,
        },
    }


def special_effect_inventory(root: Path) -> dict[str, object]:
    folder = root / "AAEmu.Game/Models/Game/Skills/Effects/SpecialEffects"
    rows = []
    for path in sorted(folder.glob("*.cs")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        rows.append(
            {
                "effect": path.stem,
                "path": path.relative_to(root).as_posix(),
                "has_marker": bool(MARKER_RE.search(text)),
                "explicit_stub_body": bool(
                    re.search(r"//\s*TODO\s+\.\.\.", text, re.IGNORECASE)
                ),
            }
        )
    return {
        "file_count": len(rows),
        "files_with_markers": sum(row["has_marker"] for row in rows),
        "explicit_stub_bodies": sum(row["explicit_stub_body"] for row in rows),
        "effects": rows,
    }


def build_report(root: Path) -> dict[str, object]:
    return {
        "schema": "aa10-reconstruction-backlog/v1",
        "scope": "AAEmu 10.0.2.13 r575 checkout",
        "root": str(root),
        "limitations": [
            "A marker, packet class, feature bit or client table is evidence, not proof of an end-to-end mechanic.",
            "Dynamic closure and native parity remain governed by the cited checkpoints and validation gates.",
            "The runtime mount is .server_files/AAEmu.Game/Configurations/Features.json.",
        ],
        "features": feature_inventory(root),
        "backend_markers": marker_inventory(root),
        "packets": packet_inventory(root),
        "special_effects": special_effect_inventory(root),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="AAEmu repository root",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="emit only reproducible counts, not every row",
    )
    args = parser.parse_args()
    report = build_report(args.root.resolve())
    if args.summary:
        report["backend_markers"].pop("markers", None)
        report["packets"]["C2G"].pop("packets", None)
        report["packets"]["G2C"].pop("packets", None)
        report["special_effects"].pop("effects", None)
        report["features"].pop("features", None)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
