#!/usr/bin/env python3
"""Extract the closed AA8-native execution graph for basic Shoot Rifle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "reconstruccion_skills_8"
NATIVE_COMBAT = SKILLS / "native_combat"
SWIFTBLADE = SKILLS / "swiftblade"
sys.path[:0] = [str(NATIVE_COMBAT), str(SWIFTBLADE), str(SKILLS)]

from extract_native_combat_catalog import (  # noqa: E402
    create_native_skill_source,
    native_effect_type_map,
    native_plot_type_map,
)
from build_phase2_compact import extract_game_stream_rows  # noqa: E402
from extract_battlerage_manifest import extract_client_relationships  # noqa: E402
from extract_swiftblade_phase3 import (  # noqa: E402
    build_closure,
    canonical_json,
    extract_native_tables,
    open_read_only,
    sha256_file,
)

SKILL_ID = 46938
PLOT_ID = 5796
EXPECTED_CLIENT_SHA256 = "4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57"
EXPECTED_GAME11_SHA256 = "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"
EXPECTED_COUNTS = {
    "anims": 2,
    "aoe_shapes": 5,
    "bubble_effects": 1,
    "damage_effects": 3,
    "passive_buffs": 0,
    "plot_aoe_conditions": 2,
    "plot_conditions": 9,
    "plot_effects": 17,
    "plot_event_conditions": 7,
    "plot_events": 16,
    "plot_next_events": 15,
    "plots": 1,
    "projectiles": 2,
    "skills": 1,
    "special_effects": 13,
}


def validate(tables: dict, diagnostics: dict) -> None:
    counts = {table: len(rows) for table, rows in sorted(tables.items())}
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"unexpected Shoot Rifle closure counts: {counts}")
    blocking = {
        key: diagnostics[key]
        for key in (
            "unresolved_effect_dependencies",
            "unresolved_plot_types",
            "animation_ids_missing",
            "controller_ids_missing",
            "projectile_ids_missing",
            "aoe_shape_ids_missing",
        )
        if diagnostics[key]
    }
    if blocking:
        raise RuntimeError(f"unclosed Shoot Rifle dependencies: {blocking}")
    if diagnostics["reached_plot_ids"] != [PLOT_ID]:
        raise RuntimeError(f"unexpected reached plots: {diagnostics['reached_plot_ids']}")

    skill = tables["skills"][0]
    expected_skill = {
        "id": SKILL_ID,
        "ability_id": 0,
        "plot_id": PLOT_ID,
        "plot_only": 1,
        "projectile_id": 9,
        "weapon_slot_for_autoattack_id": 17,
        "max_range": 15,
        "auto_fire": 1,
        "start_autoattack": 1,
    }
    actual_skill = {key: skill.get(key) for key in expected_skill}
    if actual_skill != expected_skill:
        raise RuntimeError(f"unexpected native skill row: {actual_skill}")

    damage_ids = {14635, 14638, 14639}
    damages = {int(row["id"]): row for row in tables["damage_effects"]}
    if set(damages) != damage_ids:
        raise RuntimeError(f"unexpected Shoot Rifle damage ids: {sorted(damages)}")
    for row in damages.values():
        if not (
            float(row["dps_multiplier"]) == 0.6
            and float(row["dps_inc_multiplier"]) == 0.6
            and int(row["use_ranged_weapon"]) == 1
            and int(row["weapon_slot_id"]) == 17
            and int(row["damage_type_id"]) == 4
        ):
            raise RuntimeError(f"unexpected native ranged damage row: {row}")


def build(options: argparse.Namespace) -> dict:
    client_hash = sha256_file(options.client_compact)
    game11_hash = sha256_file(options.game11)
    if client_hash != EXPECTED_CLIENT_SHA256 or game11_hash != EXPECTED_GAME11_SHA256:
        raise RuntimeError(
            f"unexpected authority hashes: client={client_hash}, game11={game11_hash}"
        )

    game_stream = options.game11.read_bytes()
    skills, _, _, skill_ranges = extract_game_stream_rows(options.game11)
    relationships = extract_client_relationships(options.game11)
    native, native_ranges = extract_native_tables(options.game11)
    client = open_read_only(options.client_compact)
    skill_source = create_native_skill_source(skills)
    try:
        effect_map, effect_evidence = native_effect_type_map(client, game_stream)
        plot_map, plot_evidence = native_plot_type_map(native)
        evidence = {**effect_evidence, **plot_evidence}
        tables, diagnostics = build_closure(
            client,
            None,
            relationships,
            native,
            ability_id=0,
            skill_source=skill_source,
            effect_type_map_override=effect_map,
            plot_type_map_override={**effect_map, **plot_map},
            reference_evidence_override=evidence,
            root_skill_ids={SKILL_ID},
            include_ability_passives=False,
        )
    finally:
        skill_source.close()
        client.close()

    validate(tables, diagnostics)
    dossier_hash = sha256_file(options.dossier)
    catalog = {
        "format_version": 1,
        "scope": "AA8 basic Shoot Rifle skill 46938 and plot 5796",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "authority_order": ["client_compact_8", "game11_native", "stage15_native_dossier"],
        "historical_3_0_used": False,
        "sources": {
            "client_compact": {"path": str(options.client_compact), "sha256": client_hash},
            "game11": {
                "path": str(options.game11),
                "sha256": game11_hash,
                "skill_ranges": skill_ranges,
                "native_ranges": {**relationships["result_ranges"], **native_ranges},
            },
            "relationship_dossier": {"path": str(options.dossier), "sha256": dossier_hash},
        },
        "diagnostics": {
            key: diagnostics[key]
            for key in (
                "unresolved_effect_dependencies",
                "unresolved_plot_types",
                "reached_skill_ids",
                "reached_plot_ids",
                "reached_event_ids",
                "animation_ids_requested",
                "animation_ids_missing",
                "projectile_ids_missing",
                "aoe_shape_ids_requested",
                "aoe_shape_ids_missing",
            )
        },
        "table_counts": {table: len(rows) for table, rows in sorted(tables.items())},
        "tables": tables,
        "provenance": {
            table: {"source": "client_compact_8" if table == "skills" else "game11_native"}
            for table in sorted(tables)
        },
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(canonical_json(catalog), encoding="utf-8")
    round_trip = json.loads(options.output.read_text(encoding="utf-8"))
    if canonical_json(round_trip) != canonical_json(catalog):
        raise RuntimeError("catalog is not deterministic")
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client-compact", type=Path,
        default=Path(r"D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite"),
    )
    parser.add_argument(
        "--game11", type=Path,
        default=Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11"),
    )
    parser.add_argument(
        "--dossier", type=Path,
        default=Path(r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\skill-46938.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parent / "generated" / "native-basic-rifle-v1.json",
    )
    options = parser.parse_args()
    for path in (options.client_compact, options.game11, options.dossier):
        if not path.is_file():
            raise FileNotFoundError(path)
    result = build(options)
    print(canonical_json({"output": str(options.output), "counts": result["table_counts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
