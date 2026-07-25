#!/usr/bin/env python3
"""Seal the executable Hiram synthesis runtime from the validated B13a graph.

This step deliberately adds no gameplay rows.  It marks the exact B13a
catalogue consumed by the server implementation after checking that the
native graph is intact and contains no historical category-material table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def build(base: Path, output: Path) -> dict:
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES
              ('phase','B13b-native-hiram-synthesis'),
              ('implementation.synthesis','ItemEvolving/ItemTaskType.Evolving'),
              ('state.evolution_experience','equipment detail +0x40'),
              ('state.random_modifiers','equipment detail +0x44..+0x54'),
              ('formula.gold','truncate(gold_multiplier * material_exp * 0.001000000047)'),
              ('awakening.reactive','confirmed-special-effect-165'),
              ('awakening.mutation','blocked-until-native-chance-and-result-protocol-confirmed')
            """
        )
        connection.commit()
        connection.execute("VACUUM")
        checks = {
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "integrity_check": connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0],
            "historical_category_material_table": connection.execute(
                """
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table'
                  AND name='item_rnd_attr_category_materials'
                """
            ).fetchone()[0],
            "hiram_pilot_mapping": connection.execute(
                """
                SELECT COUNT(*) FROM item_change_mappings
                WHERE source_item_id=45635 AND target_item_id=45828
                """
            ).fetchone()[0],
        }
        return checks
    finally:
        connection.close()


def main():
    args = arguments()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-b13b-") as directory:
        first = Path(directory) / "first.sqlite3"
        second = Path(directory) / "second.sqlite3"
        checks = build(args.base_runtime, first)
        second_checks = build(args.base_runtime, second)
        if checks != second_checks or sha256(first) != sha256(second):
            raise RuntimeError("Non-deterministic B13b build")
        if (
            checks["quick_check"] != "ok"
            or checks["integrity_check"] != "ok"
            or checks["historical_category_material_table"] != 0
            or checks["hiram_pilot_mapping"] < 1
        ):
            raise RuntimeError(f"B13b validation failed: {checks}")
        shutil.copyfile(first, args.output)

    manifest = {
        "phase": "B13b-native-hiram-synthesis",
        "base_runtime": {
            "path": str(args.base_runtime),
            "sha256": sha256(args.base_runtime),
        },
        "output": {
            "path": str(args.output),
            "sha256": sha256(args.output),
        },
        "validation": checks,
        "implemented": [
            "native material relation validation",
            "native material gain_exp",
            "native section XP and multi-grade progression",
            "x2game-confirmed gold formula",
            "skill 30666 and special effect 20058/type 123",
            "ItemTask reason 100 evolving",
            "immediate authoritative item detail refresh",
        ],
        "blocked_without_inference": [
            "natural bonus XP roll scale",
            "initial and rerolled random-attribute selection",
            "awakening chance scale and crystallization roll",
            "awakening result/failure serialization",
        ],
        "awakening_reactive_relation":
            "confirmed through item.use_skill_id -> skill_effects -> "
            "SpecialEffect type 165 value1 mapping_group_id",
        "historical_3_0_runtime_dependencies": [],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
