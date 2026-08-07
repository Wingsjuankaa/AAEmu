#!/usr/bin/env python3
"""Build the AA 8.0 native combat catalogue for the fourteen player abilities.

The historical compact is intentionally not an input.  Skill rows, cached
relationships and concrete descriptors come from the decrypted Kakao compact
and game11.  Interned type names are reconstructed from the native string-cache
sequence and verified anchors, never by matching a 3.0 row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
SWIFTBLADE_ROOT = SCRIPT_ROOT / "swiftblade"
sys.path.insert(0, str(SCRIPT_ROOT))
sys.path.insert(0, str(SWIFTBLADE_ROOT))

from build_phase2_compact import extract_game_stream_rows  # noqa: E402
from extract_battlerage_manifest import extract_client_relationships  # noqa: E402
from extract_swiftblade_phase3 import (  # noqa: E402
    build_closure,
    canonical_json,
    extract_native_tables,
    open_read_only,
    sha256_file,
)


ABILITIES = {
    1: "Battlerage",
    2: "Witchcraft",
    3: "Defense",
    4: "Auramancy",
    5: "Occultism",
    6: "Archery",
    7: "Sorcery",
    8: "Shadowplay",
    9: "Songcraft",
    10: "Vitalism",
    11: "Malediction",
    12: "Swiftblade",
    13: "Gunslinger",
    14: "Spelldance",
}

PROVENANCE = {
    "skills": "game11_native",
    "passive_buffs": "game11_native",
    "effects": "client_compact_8",
    "skill_effects": "game11_native",
    "buffs": "game11_native",
    "bubble_effects": "game11_native",
    "buff_effects": "game11_native",
    "buff_tick_effects": "game11_native",
    "buff_triggers": "game11_native",
    "buff_unit_modifiers": "game11_native",
    "tagged_buffs": "game11_native",
    "conversion_effects": "game11_native",
    "damage_effects": "game11_native",
    "physical_explosion_effects": "game11_native",
    "special_effects": "game11_native",
    "aggro_effects": "game11_native",
    "combat_resource_effects": "game11_native",
    "dispel_effects": "game11_native",
    "extend_charge_effects": "game11_native",
    "heal_effects": "game11_native",
    "interaction_effects": "game11_native",
    "kill_npc_without_corpse_effects": "game11_native",
    "mana_burn_effects": "game11_native",
    "reset_aoe_diminishing_effects": "game11_native",
    "restore_mana_effects": "game11_native",
    "spawn_effects": "game11_native",
    "plots": "game11_native",
    "plot_events": "game11_native",
    "plot_conditions": "game11_native",
    "plot_aoe_conditions": "game11_native",
    "plot_event_conditions": "game11_native",
    "plot_effects": "game11_native",
    "plot_next_events": "game11_native",
    "aoe_shapes": "game11_native",
    "anims": "game11_native",
    "skill_controllers": "game11_native",
    "projectiles": "game11_native",
}

SEMANTICS_PENDING = {
    "HealEffect": "AA8 fields and formula semantics are not fully implemented",
    "KillNpcWithoutCorpseEffect": "native give_exp behavior is not implemented",
    "ManaBurnEffect": "AA8 damage, ratio and weapon fields are not fully implemented",
    "SpawnEffect": "AA8 ray-cast, ray offset and owner variants remain unimplemented",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--client-game-stream", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--coverage", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def create_native_skill_source(skills: list[dict[str, Any]]) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    columns = list(skills[0])
    declarations = []
    for name in columns:
        values = [row.get(name) for row in skills[:1000] if row.get(name) is not None]
        column_type = "TEXT" if any(isinstance(value, str) for value in values) else "REAL" if any(isinstance(value, float) for value in values) else "INTEGER"
        declarations.append(f'"{name}" {column_type}')
    connection.execute(f"CREATE TABLE skills ({', '.join(declarations)})")
    connection.executemany(
        f"INSERT INTO skills VALUES ({','.join('?' for _ in columns)})",
        [tuple(row.get(name) for name in columns) for row in skills],
    )
    connection.row_factory = sqlite3.Row
    return connection


def native_effect_type_map(client: sqlite3.Connection, game_stream: bytes) -> tuple[dict[str, str], dict[str, Any]]:
    """Resolve the compact string cache without consulting historical data.

    The effects result introduces forty inline names in order.  game11 assigns
    the same consecutive cache ids to those values.  CombatResourceEffect is a
    confirmed native anchor: it is the 38th inline name and is subsequently
    referenced as 75256.  DamageEffect and HealEffect were interned by earlier
    native results and are confirmed by their unique inline strings plus their
    cached ids in the effects stream.
    """

    direct_types: list[str] = []
    for (actual_type,) in client.execute("SELECT actual_type FROM effects ORDER BY id"):
        value = str(actual_type)
        if value.startswith("<ref:") or value in direct_types:
            continue
        direct_types.append(value)
    if "CombatResourceEffect" not in direct_types:
        raise RuntimeError("The native CombatResourceEffect string anchor is missing")
    anchor_ref = 75256
    base_ref = anchor_ref - direct_types.index("CombatResourceEffect")
    if base_ref != 75219:
        raise RuntimeError(f"Unexpected native effect string-cache base {base_ref}")

    resolved = {
        f"<ref:{base_ref + index}>": value
        for index, value in enumerate(direct_types)
    }
    resolved.update({"<ref:69865>": "DamageEffect", "<ref:69867>": "HealEffect"})

    referenced_values = {
        str(row[0])
        for row in client.execute("SELECT DISTINCT actual_type FROM effects")
        if str(row[0]).startswith("<ref:")
    }
    evidence: dict[str, Any] = {}
    for reference, value in sorted(resolved.items()):
        inline_count = game_stream.count(value.encode("utf-8") + b"\x00")
        ref_id = int(reference[5:-1])
        reference_count = game_stream.count(ref_id.to_bytes(4, "little"))
        if inline_count < 1 or (reference in referenced_values and reference_count < 1):
            raise RuntimeError(
                f"Native string-cache evidence is missing for {reference}={value}"
            )
        evidence[reference] = {
            "value": value,
            "inline_occurrences": inline_count,
            "reference_occurrences": reference_count,
            "source": "game11_string_cache",
        }
    return resolved, evidence


def native_plot_type_map(native: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, str], dict[str, Any]]:
    direct: list[str] = []
    references: set[int] = set()
    for row in native["plot_effects"]:
        value = str(row["actual_type"])
        if value.startswith("<ref:"):
            ref_id = int(value[5:-1])
            if ref_id >= 100000:
                references.add(ref_id)
        elif value not in direct:
            direct.append(value)
    modern = sorted(references)
    if modern != list(range(361228, 361228 + len(direct))):
        raise RuntimeError(
            f"Unexpected plot string-cache sequence: refs={modern}, direct={direct}"
        )
    resolved = {f"<ref:{ref}>": value for ref, value in zip(modern, direct)}
    evidence = {
        reference: {
            "value": value,
            "source": "game11_plot_effects_inline_sequence",
        }
        for reference, value in resolved.items()
    }
    return resolved, evidence


def merge_tables(
    destination: dict[str, dict[int, dict[str, Any]]],
    source: dict[str, list[dict[str, Any]]],
) -> None:
    for table, rows in source.items():
        for row in rows:
            row_id = int(row["id"])
            previous = destination[table].get(row_id)
            if previous is not None and previous != row:
                raise RuntimeError(f"Conflicting native row {table}.{row_id}")
            destination[table][row_id] = row


def diagnostic_summary(
    diagnostics: dict[str, Any],
    tables: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    effect_reasons = Counter(
        str(row.get("actual_type") or row.get("reason") or "unknown")
        for row in diagnostics["unresolved_effect_dependencies"]
    )
    reached_primitives = {
        str(row["actual_type"])
        for table in (
            (tables or {}).get("effects", []),
            (tables or {}).get("plot_effects", []),
        )
        for row in table
    }
    return {
        "unresolved_effect_dependencies": dict(sorted(effect_reasons.items())),
        "unresolved_plot_types": diagnostics["unresolved_plot_types"],
        "missing_animations": diagnostics["animation_ids_missing"],
        "missing_controllers": diagnostics["controller_ids_missing"],
        "missing_projectiles": diagnostics["projectile_ids_missing"],
        "missing_aoe_shapes": diagnostics["aoe_shape_ids_missing"],
        "backend_semantics_pending": {
            primitive: SEMANTICS_PENDING[primitive]
            for primitive in sorted(reached_primitives.intersection(SEMANTICS_PENDING))
        },
    }


def has_blocking_diagnostics(summary: dict[str, Any]) -> bool:
    return any(
        summary[key]
        for key in (
            "unresolved_effect_dependencies",
            "unresolved_plot_types",
            "missing_animations",
            "missing_controllers",
            "missing_projectiles",
            "missing_aoe_shapes",
            "backend_semantics_pending",
        )
    )


def backend_coverage(source_root: Path, tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    effect_types = sorted(
        {
            str(row["actual_type"])
            for row in tables.get("effects", []) + tables.get("plot_effects", [])
        }
    )
    manager = (source_root / "AAEmu.Game/Core/Managers/SkillManager.cs").read_text(encoding="utf-8")
    effects_root = source_root / "AAEmu.Game/Models/Game/Skills/Effects"
    primitives = []
    for actual_type in effect_types:
        registered = f'_effects.Add("{actual_type}"' in manager
        class_present = (effects_root / f"{actual_type}.cs").is_file()
        if actual_type == "SkillController":
            class_present = (source_root / "AAEmu.Game/Models/Game/Skills/Templates/SkillControllerTemplate.cs").is_file()
        if not registered or not class_present:
            state = "native_not_implemented"
        elif actual_type in SEMANTICS_PENDING:
            state = "native_semantics_pending"
        else:
            state = "native_implemented"
        primitives.append(
            {
                "primitive": actual_type,
                "state": state,
                "registered": registered,
                "model_present": class_present,
            }
        )
    return {
        "effect_primitives": primitives,
        "counts": dict(Counter(row["state"] for row in primitives)),
        "plot_target_methods": [1, 2, 3, 4, 5, 6, 7],
        "provenance_states": [
            "client_compact_8",
            "game11_native",
            "x2game_confirmed",
            "server_derived",
            "server_only",
        ],
    }


def provenance_manifest(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for table, rows in sorted(tables.items()):
        source = PROVENANCE.get(table, "game11_native")
        result[table] = {
            "source": source,
            "rows": {
                str(row["id"]): {
                    "row": source,
                    "fields": {name: source for name in sorted(row)},
                }
                for row in rows
            },
        }
    return result


def main() -> int:
    args = parse_args()
    for path in (args.client_compact, args.client_game_stream):
        if not path.is_file():
            raise FileNotFoundError(path)
    if not args.source_root.is_dir():
        raise FileNotFoundError(args.source_root)

    game_stream = args.client_game_stream.read_bytes()
    skills, levels, passives, skill_ranges = extract_game_stream_rows(args.client_game_stream)
    native_skills = [row for row in skills if int(row["ability_id"]) in ABILITIES]
    relationships = extract_client_relationships(args.client_game_stream)
    native, native_ranges = extract_native_tables(args.client_game_stream)
    client = open_read_only(args.client_compact)
    skill_source = create_native_skill_source(skills)
    try:
        effect_map, effect_evidence = native_effect_type_map(client, game_stream)
        plot_map, plot_evidence = native_plot_type_map(native)
        combined_evidence = {**effect_evidence, **plot_evidence}
        aggregate: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
        ability_manifests = []
        ability_table_ids: dict[str, dict[str, list[int]]] = {}
        skill_table_ids: dict[str, dict[str, list[int]]] = {}
        status_rows = []
        for ability_id, ability_name in ABILITIES.items():
            tables, diagnostics = build_closure(
                client,
                None,
                relationships,
                native,
                ability_id=ability_id,
                skill_source=skill_source,
                effect_type_map_override=effect_map,
                plot_type_map_override={**effect_map, **plot_map},
                reference_evidence_override=combined_evidence,
            )
            merge_tables(aggregate, tables)
            summary = diagnostic_summary(diagnostics, tables)
            ability_skill_ids = {int(row["id"]) for row in tables.get("skills", [])}
            ability_status_rows = []
            for row in tables.get("skills", []):
                root_skill_id = int(row["id"])
                closure_skill_ids = {root_skill_id}
                while True:
                    skill_tables, skill_diagnostics = build_closure(
                        client,
                        None,
                        relationships,
                        native,
                        ability_id=ability_id,
                        skill_source=skill_source,
                        effect_type_map_override=effect_map,
                        plot_type_map_override={**effect_map, **plot_map},
                        reference_evidence_override=combined_evidence,
                        root_skill_ids=closure_skill_ids,
                        include_ability_passives=False,
                    )
                    requested = {
                        int(value)
                        for value in skill_diagnostics.get(
                            "chained_skill_ids_requested", []
                        )
                        if int(value) in ability_skill_ids
                    }
                    expanded = closure_skill_ids | requested
                    if expanded == closure_skill_ids:
                        break
                    closure_skill_ids = expanded

                skill_summary = diagnostic_summary(skill_diagnostics, skill_tables)
                quarantined = has_blocking_diagnostics(skill_summary)
                reasons = canonical_json(skill_summary).strip() if quarantined else ""
                status = "quarantined" if quarantined else "enabled"
                status_row = {
                    "skill_id": root_skill_id,
                    "ability_id": ability_id,
                    "status": status,
                    "reason": reasons,
                    "closure_skill_ids": sorted(closure_skill_ids),
                }
                ability_status_rows.append(status_row)
                status_rows.append(
                    status_row
                )
                skill_table_ids[str(root_skill_id)] = {
                    table: sorted(int(value["id"]) for value in values)
                    for table, values in sorted(skill_tables.items())
                }

            enabled_skill_count = sum(
                row["status"] == "enabled" for row in ability_status_rows
            )
            if enabled_skill_count == len(ability_status_rows):
                ability_status = "enabled"
            elif enabled_skill_count:
                ability_status = "partial"
            else:
                ability_status = "quarantined"
            ability_manifests.append(
                {
                    "id": ability_id,
                    "name": ability_name,
                    "status": ability_status,
                    "skill_count": len(tables.get("skills", [])),
                    "enabled_skill_count": enabled_skill_count,
                    "quarantined_skill_count": len(ability_status_rows) - enabled_skill_count,
                    "visible_count": sum(int(row.get("show") or 0) != 0 for row in tables.get("skills", [])),
                    "table_counts": {table: len(rows) for table, rows in sorted(tables.items())},
                    "diagnostics": summary,
                }
            )
            ability_table_ids[str(ability_id)] = {
                table: sorted(int(row["id"]) for row in rows)
                for table, rows in sorted(tables.items())
            }
    finally:
        skill_source.close()
        client.close()

    tables = {
        table: [rows[row_id] for row_id in sorted(rows)]
        for table, rows in sorted(aggregate.items())
    }
    coverage = backend_coverage(args.source_root, tables)
    catalog = {
        "format_version": 1,
        "scope": "AA 8.0 player combat abilities 1-14",
        "authority_order": [
            "client_compact_8",
            "game11_native",
            "x2game_confirmed",
            "observed_protocol",
        ],
        "sources": {
            "client_compact": {
                "path": str(args.client_compact.resolve()),
                "sha256": sha256_file(args.client_compact),
            },
            "client_game_stream": {
                "path": str(args.client_game_stream.resolve()),
                "sha256": sha256_file(args.client_game_stream),
                "skill_ranges": skill_ranges,
                "native_ranges": {**relationships["result_ranges"], **native_ranges},
            },
        },
        "reference_resolution": {
            "effect_types": effect_map,
            "plot_types": plot_map,
            "evidence": combined_evidence,
            "historical_reference_used": False,
        },
        "abilities": ability_manifests,
        "ability_table_ids": ability_table_ids,
        "skill_table_ids": skill_table_ids,
        "skill_status": sorted(status_rows, key=lambda row: row["skill_id"]),
        "table_counts": {table: len(rows) for table, rows in tables.items()},
        "tables": tables,
        "provenance": provenance_manifest(tables),
        "coverage": coverage,
    }

    if args.verify:
        if len(native_skills) != 462:
            raise RuntimeError(f"Expected 462 native player-combat skill rows, found {len(native_skills)}")
        if len(tables.get("skills", [])) != 462:
            raise RuntimeError(f"Catalogue closure contains {len(tables.get('skills', []))} skills")
        if any(
            value == "historical_3_0"
            for table in catalog["provenance"].values()
            for value in [table["source"]]
        ):
            raise RuntimeError("Historical provenance entered the native combat catalogue")
        ability_status = {row["id"]: row["status"] for row in ability_manifests}
        if ability_status[1] != "enabled" or ability_status[12] != "enabled":
            raise RuntimeError(f"Pilot abilities are not closed: {ability_status}")
        relations = defaultdict(list)
        effects = {int(row["id"]): row for row in tables["effects"]}
        for relation in tables["skill_effects"]:
            relations[int(relation["skill_id"])].append(relation)
        expected = {
            18132: [("DamageEffect", 3220), ("BuffEffect", 6548), ("SpecialEffect", 6515), ("DamageEffect", 9373)],
            18134: [("DamageEffect", 3221), ("SpecialEffect", 6628), ("DamageEffect", 9374)],
            18131: [("DamageEffect", 3218), ("SpecialEffect", 6629), ("BuffEffect", 6708), ("SpecialEffect", 15810), ("BuffEffect", 24379)],
        }
        for skill_id, chain in expected.items():
            actual = [
                (str(effects[int(row["effect_id"])]["actual_type"]), int(effects[int(row["effect_id"])]["actual_id"]))
                for row in sorted(relations[skill_id], key=lambda row: int(row["id"]))
            ]
            if actual != chain:
                raise RuntimeError(f"Triple Slash chain mismatch for {skill_id}: {actual}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.coverage.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(catalog), encoding="utf-8")
    args.coverage.write_text(canonical_json(coverage), encoding="utf-8")
    round_trip = json.loads(args.output.read_text(encoding="utf-8"))
    if canonical_json(round_trip) != canonical_json(catalog):
        raise RuntimeError("Catalogue output is not deterministic")
    print(
        canonical_json(
            {
                "output": str(args.output.resolve()),
                "sha256": sha256_file(args.output),
                "skill_count": len(tables.get("skills", [])),
                "enabled_abilities": [row["name"] for row in ability_manifests if row["status"] == "enabled"],
                "partial_abilities": [row["name"] for row in ability_manifests if row["status"] == "partial"],
                "quarantined_abilities": [row["name"] for row in ability_manifests if row["status"] == "quarantined"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
