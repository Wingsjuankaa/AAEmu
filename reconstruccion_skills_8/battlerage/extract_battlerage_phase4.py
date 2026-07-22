#!/usr/bin/env python3
"""Build the native Kakao 8.0 Battlerage dependency closure.

The decrypted client view is authoritative for effects and presentation. The
complete native skill rows and relationships recovered from game11 are used
where the decrypted SQLite view is incomplete. All inputs are read-only.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
SWIFTBLADE_ROOT = SCRIPT_ROOT / "swiftblade"
sys.path.insert(0, str(SCRIPT_ROOT))
sys.path.insert(0, str(SWIFTBLADE_ROOT))

from extract_battlerage_manifest import extract_client_relationships  # noqa: E402
from extract_swiftblade_phase3 import (  # noqa: E402
    build_closure,
    canonical_json,
    extract_native_tables,
    open_read_only,
    sha256_file,
)


ABILITY_ID = 1
ABILITY_NAME = "Battlerage"
EXPECTED_SKILL_ROWS = 42
EXPECTED_VISIBLE_LEARNABLE = 12
EXPECTED_PASSIVES = 6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--runtime-compact", required=True, type=Path)
    parser.add_argument("--server-reference", required=True, type=Path)
    parser.add_argument("--client-game-stream", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def indexed(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["id"]): row for row in rows}


def grouped(rows: list[dict[str, Any]], column: str) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(int(row[column]), []).append(row)
    return result


def verify_closure(tables: dict[str, list[dict[str, Any]]], diagnostics: dict[str, Any]) -> None:
    skills = tables.get("skills", [])
    if len(skills) != EXPECTED_SKILL_ROWS:
        raise RuntimeError(f"Expected {EXPECTED_SKILL_ROWS} Battlerage skill rows, found {len(skills)}")
    visible_learnable = [
        row for row in skills
        if int(row.get("show") or 0) and int(row.get("skill_points") or 0) > 0
    ]
    if len(visible_learnable) != EXPECTED_VISIBLE_LEARNABLE:
        raise RuntimeError(
            f"Expected {EXPECTED_VISIBLE_LEARNABLE} visible learnable Battlerage skills, "
            f"found {len(visible_learnable)}"
        )
    if len(tables.get("passive_buffs", [])) != EXPECTED_PASSIVES:
        raise RuntimeError(f"Expected {EXPECTED_PASSIVES} Battlerage passives")

    effects = indexed(tables.get("effects", []))
    relations = grouped(tables.get("skill_effects", []), "skill_id")
    golden_counts = {
        18132: 4,
        18134: 3,
        18131: 5,
        36401: 4,
        36402: 3,
        36403: 3,
        36404: 3,
        36405: 3,
        36406: 2,
    }
    for skill_id, expected_count in golden_counts.items():
        rows = relations.get(skill_id, [])
        if len(rows) != expected_count:
            raise RuntimeError(
                f"Triple Slash relation mismatch for {skill_id}: "
                f"expected {expected_count}, found {len(rows)}"
            )
        for row in rows:
            if int(row["effect_id"]) not in effects:
                raise RuntimeError(f"Missing effect {row['effect_id']} for skill {skill_id}")

    if diagnostics["animation_ids_missing"]:
        raise RuntimeError(f"Missing animations: {diagnostics['animation_ids_missing']}")
    # Controller 604 belongs exclusively to hidden skill 11854, explicitly
    # named obsolete in the native skill catalogue. It is retained in the
    # manifest for provenance but is outside the playable Battlerage closure.
    unexpected_missing_controllers = sorted(
        set(diagnostics["controller_ids_missing"]).difference({604})
    )
    if unexpected_missing_controllers:
        raise RuntimeError(f"Missing controllers: {unexpected_missing_controllers}")
    if diagnostics["projectile_ids_missing"]:
        raise RuntimeError(f"Missing projectiles: {diagnostics['projectile_ids_missing']}")
    if diagnostics["aoe_shape_ids_missing"]:
        raise RuntimeError(f"Missing AoE shapes: {diagnostics['aoe_shape_ids_missing']}")


def main() -> int:
    args = parse_args()
    for path in (
        args.client_compact,
        args.runtime_compact,
        args.server_reference,
        args.client_game_stream,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    relationships = extract_client_relationships(args.client_game_stream)
    native, native_ranges = extract_native_tables(args.client_game_stream)
    client = open_read_only(args.client_compact)
    runtime = open_read_only(args.runtime_compact)
    server = open_read_only(args.server_reference)
    try:
        tables, diagnostics = build_closure(
            client,
            server,
            relationships,
            native,
            ability_id=ABILITY_ID,
            skill_source=runtime,
        )
        runtime_tables = {
            row[0]
            for row in runtime.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        runtime_counts = {
            table: runtime.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in sorted(tables)
            if table in runtime_tables
        }
    finally:
        server.close()
        runtime.close()
        client.close()

    if args.verify:
        verify_closure(tables, diagnostics)

    manifest = {
        "format_version": 1,
        "ability": {"id": ABILITY_ID, "name": ABILITY_NAME},
        "sources": {
            "client_compact": {
                "path": str(args.client_compact.resolve()),
                "sha256": sha256_file(args.client_compact),
            },
            "runtime_compact": {
                "path": str(args.runtime_compact.resolve()),
                "sha256": sha256_file(args.runtime_compact),
            },
            "server_reference": {
                "path": str(args.server_reference.resolve()),
                "sha256": sha256_file(args.server_reference),
            },
            "client_game_stream": {
                "path": str(args.client_game_stream.resolve()),
                "sha256": sha256_file(args.client_game_stream),
            },
        },
        "authority_order": [
            "client_compact_8",
            "game11",
            "x2game_dll",
            "observed_protocol",
            "historical_reference",
        ],
        "native_cached_ranges": {**relationships["result_ranges"], **native_ranges},
        "table_counts": {table: len(rows) for table, rows in sorted(tables.items())},
        "runtime_baseline_counts": runtime_counts,
        "diagnostics": diagnostics,
        "tables": tables,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(manifest), encoding="utf-8")
    round_trip = json.loads(args.output.read_text(encoding="utf-8"))
    if canonical_json(round_trip) != canonical_json(manifest):
        raise RuntimeError("Manifest round-trip is not deterministic")
    print(canonical_json({
        "output": str(args.output.resolve()),
        "sha256": sha256_file(args.output),
        "table_counts": manifest["table_counts"],
        "unresolved_effect_dependencies": len(diagnostics["unresolved_effect_dependencies"]),
        "unresolved_plot_types": len(diagnostics["unresolved_plot_types"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
