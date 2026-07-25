#!/usr/bin/env python3
"""Build the directed AA8 Hiram/Erenor evolution catalogue.

The source rows are decoded from Kakao 8.0 game11 by the already validated
phase-B extractor.  B12 is used only as the container for the non-evolution
domains.  Every evolution table is dropped and rebuilt from native AA8 rows.
In particular, the historical ``item_rnd_attr_category_materials`` table is
removed because no AA8 loader or cached result exists for it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_EXTRACTOR = (
    ROOT / "reconstruccion_items_8" / "phase_b_synthesis"
    / "extract_native_synthesis.py"
)

TARGET_GROUPS = {
    1: "hiram_t1_t3",
    29: "hiram_t4_t5",
    21: "erenor_weapons",
}
MATERIAL_GROUPS = {
    2: "hiram_materials",
    30: "hiram_t4_t5_materials",
    24: "erenor_common_materials",
    25: "erenor_weapon_materials",
}


def load_source_module():
    spec = importlib.util.spec_from_file_location("aa8_synthesis_source", SOURCE_EXTRACTOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def extract_awakening_reactives(
    game11: Path,
    client_compact: Path,
    mapping_group_ids: set[int],
) -> dict[str, list[dict[str, Any]]]:
    """Recover the native scroll skill closure consumed by awaken mode 11."""
    skills_root = ROOT / "reconstruccion_skills_8"
    sys.path.insert(0, str(skills_root))
    from extract_battlerage_manifest import extract_client_relationships

    relationships = extract_client_relationships(game11)
    special_rows = {
        int(row["id"]): dict(row)
        for row in relationships["concrete_effects"]["special_effects"]
        if int(row["special_effect_type_id"]) == 165
        and int(row["value1"]) in mapping_group_ids
    }
    with sqlite3.connect(client_compact) as connection:
        connection.row_factory = sqlite3.Row
        effects = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT * FROM effects
                WHERE actual_id IN ({','.join('?' for _ in special_rows)})
                """,
                sorted(special_rows),
            )
        ] if special_rows else []
        effect_ids = {int(row["id"]) for row in effects}
        skill_effects = [
            {
                **dict(row),
                # AA8 uses 99 as its open-ended client level. The backend
                # consumes 255; preserve the original in the manifest.
                "end_level": 255
                if int(row.get("end_level") or 0) == 99
                else int(row.get("end_level") or 0),
            }
            for row in relationships["skill_effects"]
            if int(row["effect_id"]) in effect_ids
        ]
        skill_ids = {int(row["skill_id"]) for row in skill_effects}
        skills = [
            dict(row)
            for row in connection.execute(
                f"""
                SELECT * FROM skills
                WHERE id IN ({','.join('?' for _ in skill_ids)})
                """,
                sorted(skill_ids),
            )
        ] if skill_ids else []
        loaded_skill_ids = {int(row["id"]) for row in skills}
        excluded_skill_effects = [
            row
            for row in skill_effects
            if int(row["skill_id"]) not in loaded_skill_ids
        ]
        skill_effects = [
            row
            for row in skill_effects
            if int(row["skill_id"]) in loaded_skill_ids
        ]

    # The interned client reference used by these effects was already
    # resolved byte-for-byte as SpecialEffect in the native combat phase.
    for row in effects:
        row["actual_type"] = "SpecialEffect"
    return {
        "special_effects": list(special_rows.values()),
        "effects": effects,
        "skill_effects": skill_effects,
        "skills": skills,
        "excluded_skill_effects": excluded_skill_effects,
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rows_from(connection: sqlite3.Connection, query: str, values=()) -> list[dict[str, Any]]:
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(query, values)]


def filter_catalogue(tables: dict[str, list[dict[str, Any]]], base: Path):
    categories = tables["item_rnd_attr_categories"]
    enabled_group_ids = set(TARGET_GROUPS) | set(MATERIAL_GROUPS)
    enabled_category_ids = {
        row["id"]
        for row in categories
        if row["item_rnd_attr_category_group_id"] in enabled_group_ids
    }

    with sqlite3.connect(base) as connection:
        family_items = {
            row["item_id"]
            for row in rows_from(
                connection,
                """
                SELECT w.item_id
                FROM item_weapons w
                WHERE w.item_rnd_attr_category_id IN (
                    SELECT id FROM item_rnd_attr_categories
                    WHERE item_rnd_attr_category_group_id IN (1,21,29)
                )
                """,
            )
        }
        all_item_ids = {
            row["id"] for row in rows_from(connection, "SELECT id FROM items")
        }

    mappings = [
        row
        for row in tables["item_change_mappings"]
        if row["source_item_id"] in family_items
        and row["target_item_id"] in family_items
    ]
    mapping_group_ids = {row["mapping_group_id"] for row in mappings}

    sets = [
        row
        for row in tables["item_rnd_attr_unit_modifier_group_sets"]
        if row["item_rnd_attr_category_id"] in enabled_category_ids
    ]
    # Native inheritance is by group-set id. Pull ancestors without guessing.
    by_set_id = {
        row["id"]: row
        for row in tables["item_rnd_attr_unit_modifier_group_sets"]
    }
    required_set_ids = {row["id"] for row in sets}
    frontier = list(sets)
    while frontier:
        row = frontier.pop()
        parent_id = row["inherit_priority_id"]
        if parent_id and parent_id in by_set_id and parent_id not in required_set_ids:
            required_set_ids.add(parent_id)
            frontier.append(by_set_id[parent_id])
    sets = [row for row in by_set_id.values() if row["id"] in required_set_ids]

    groups = [
        row
        for row in tables["item_rnd_attr_unit_modifier_groups"]
        if row["item_rnd_attr_unit_modifier_group_set_id"] in required_set_ids
    ]
    modifier_group_ids = {row["id"] for row in groups}

    filtered = {
        "item_rnd_attr_categories": [
            row for row in categories if row["id"] in enabled_category_ids
        ],
        "item_rnd_attr_category_groups": [
            row
            for row in tables["item_rnd_attr_category_groups"]
            if row["id"] in enabled_group_ids
        ],
        "item_rnd_attr_category_properties": [
            row
            for row in tables["item_rnd_attr_category_properties"]
            if row["item_rnd_attr_category_id"] in enabled_category_ids
        ],
        "item_rnd_attr_category_elements": [
            row
            for row in tables["item_rnd_attr_category_elements"]
            if row["item_rnd_attr_category_id"] in enabled_category_ids
        ],
        "item_rnd_attr_category_relations": [
            row
            for row in tables["item_rnd_attr_category_relations"]
            if row["item_rnd_attr_category_group_id"] in TARGET_GROUPS
            and row["material_id"] in all_item_ids
        ],
        "item_evolving_materials": [
            row
            for row in tables["item_evolving_materials"]
            if row["item_rnd_attr_category_id"] in enabled_category_ids
            and row["item_id"] in all_item_ids
        ],
        "item_change_mapping_groups": [
            row
            for row in tables["item_change_mapping_groups"]
            if row["id"] in mapping_group_ids
        ],
        "item_change_mappings": mappings,
        "item_rnd_attr_unit_modifier_group_sets": sets,
        "item_rnd_attr_unit_modifier_groups": groups,
        "item_rnd_attr_unit_modifiers": [
            row
            for row in tables["item_rnd_attr_unit_modifiers"]
            if row["group_id"] in modifier_group_ids
        ],
    }
    return filtered, family_items, enabled_category_ids


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "historical_category_material_table": connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='item_rnd_attr_category_materials'
            """
        ).fetchone()[0],
    }
    orphan_queries = {
        "orphan_properties": """
            SELECT COUNT(*) FROM item_rnd_attr_category_properties p
            LEFT JOIN item_rnd_attr_categories c
              ON c.id=p.item_rnd_attr_category_id WHERE c.id IS NULL""",
        "orphan_elements": """
            SELECT COUNT(*) FROM item_rnd_attr_category_elements e
            LEFT JOIN item_rnd_attr_categories c
              ON c.id=e.item_rnd_attr_category_id WHERE c.id IS NULL""",
        "orphan_evolving_material_items": """
            SELECT COUNT(*) FROM item_evolving_materials e
            LEFT JOIN items i ON i.id=e.item_id WHERE i.id IS NULL""",
        "orphan_relation_items": """
            SELECT COUNT(*) FROM item_rnd_attr_category_relations r
            LEFT JOIN items i ON i.id=r.material_id WHERE i.id IS NULL""",
        "orphan_mapping_groups": """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN item_change_mapping_groups g ON g.id=m.mapping_group_id
            WHERE g.id IS NULL""",
        "orphan_mapping_sources": """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN items i ON i.id=m.source_item_id WHERE i.id IS NULL""",
        "orphan_mapping_targets": """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN items i ON i.id=m.target_item_id WHERE i.id IS NULL""",
        "orphan_modifier_sets": """
            SELECT COUNT(*) FROM item_rnd_attr_unit_modifier_groups g
            LEFT JOIN item_rnd_attr_unit_modifier_group_sets s
              ON s.id=g.item_rnd_attr_unit_modifier_group_set_id
            WHERE s.id IS NULL""",
        "orphan_modifier_groups": """
            SELECT COUNT(*) FROM item_rnd_attr_unit_modifiers m
            LEFT JOIN item_rnd_attr_unit_modifier_groups g ON g.id=m.group_id
            WHERE g.id IS NULL""",
        "orphan_awakening_skill_effect_skills": """
            SELECT COUNT(*) FROM skill_effects se
            LEFT JOIN skills s ON s.id=se.skill_id
            JOIN effects e ON e.id=se.effect_id
            JOIN special_effects sp ON sp.id=e.actual_id
            WHERE e.actual_type='SpecialEffect' AND sp.special_effect_type_id=165
              AND s.id IS NULL""",
        "orphan_awakening_skill_effect_effects": """
            SELECT COUNT(*) FROM skill_effects se
            LEFT JOIN effects e ON e.id=se.effect_id
            WHERE se.id IN (
                SELECT se2.id
                FROM skill_effects se2
                JOIN effects e2 ON e2.id=se2.effect_id
                JOIN special_effects sp2 ON sp2.id=e2.actual_id
                WHERE e2.actual_type='SpecialEffect' AND sp2.special_effect_type_id=165
            ) AND e.id IS NULL""",
        "orphan_awakening_special_effects": """
            SELECT COUNT(*) FROM effects e
            LEFT JOIN special_effects sp ON sp.id=e.actual_id
            WHERE e.actual_type='SpecialEffect'
              AND e.id IN (
                SELECT effect_id FROM skill_effects
                WHERE consume_item_id > 0
              )
              AND sp.id IS NULL""",
        "orphan_awakening_reactive_items": """
            SELECT COUNT(*) FROM skill_effects se
            JOIN effects e ON e.id=se.effect_id
            JOIN special_effects sp ON sp.id=e.actual_id
            LEFT JOIN items i ON i.id=se.consume_item_id
            WHERE e.actual_type='SpecialEffect' AND sp.special_effect_type_id=165
              AND se.consume_item_id > 0 AND i.id IS NULL""",
        "orphan_awakening_reactive_mapping_groups": """
            SELECT COUNT(*) FROM skill_effects se
            JOIN effects e ON e.id=se.effect_id
            JOIN special_effects sp ON sp.id=e.actual_id
            LEFT JOIN item_change_mapping_groups mg ON mg.id=sp.value1
            WHERE e.actual_type='SpecialEffect' AND sp.special_effect_type_id=165
              AND mg.id IS NULL""",
    }
    for key, query in orphan_queries.items():
        checks[key] = int(connection.execute(query).fetchone()[0])
    return checks


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    available = {
        row[1] for row in connection.execute(f"PRAGMA table_info({table})")
    }
    columns = [column for column in rows[0] if column in available]
    placeholders = ",".join(f":{column}" for column in columns)
    connection.executemany(
        f"""
        INSERT OR REPLACE INTO {table} ({','.join(columns)})
        VALUES ({placeholders})
        """,
        sorted(rows, key=lambda row: int(row["id"])),
    )


def build(
    source,
    base: Path,
    output: Path,
    tables: dict[str, list[dict[str, Any]]],
    awakening_reactives: dict[str, list[dict[str, Any]]],
):
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE IF EXISTS item_rnd_attr_category_materials")
        for name in source.TABLES:
            connection.execute(f"DROP TABLE IF EXISTS {name}")
            connection.execute(source.DDL[name])
            columns = source.TABLES[name]["columns"]
            placeholders = ",".join(f":{column}" for column in columns)
            connection.executemany(
                f"INSERT INTO {name} ({','.join(columns)}) VALUES ({placeholders})",
                sorted(tables[name], key=lambda row: tuple(row[column] for column in columns)),
            )
        for name in ("skills", "special_effects", "effects", "skill_effects"):
            insert_rows(connection, name, awakening_reactives[name])
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_item_phase_b_metadata (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
            )
            """
        )
        metadata = {
            "phase": "B13a-native-hiram-erenor-evolution-catalogue",
            "authority": "AA8 game11/x2game; no historical 3.0 evolution rows",
            "skill.synthesis": "30666",
            "effect.synthesis": "20058",
            "special_type.synthesis": "123",
            "skill.reroll": "32060",
            "effect.reroll": "21462",
            "special_type.reroll": "136",
            "special_type.awakening": "165",
            "awakening.reactive_closure":
                "skills/effects/special_effects/skill_effects from AA8",
        }
        connection.executemany(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES (?,?)
            """,
            sorted(metadata.items()),
        )
        connection.commit()
        connection.execute("VACUUM")
        connection.commit()
        return validate(connection)
    finally:
        connection.close()


def main() -> None:
    args = arguments()
    source = load_source_module()
    extracted, ranges = source.extract(args.game11)
    tables, family_items, category_ids = filter_catalogue(extracted, args.base_runtime)
    mapping_group_ids = {
        int(row["id"]) for row in tables["item_change_mapping_groups"]
    }
    awakening_reactives = extract_awakening_reactives(
        args.game11,
        args.client_compact,
        mapping_group_ids,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-b13a-") as directory:
        first = Path(directory) / "first.sqlite3"
        second = Path(directory) / "second.sqlite3"
        checks = build(
            source, args.base_runtime, first, tables, awakening_reactives
        )
        second_checks = build(
            source, args.base_runtime, second, tables, awakening_reactives
        )
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic B13a build: {first_hash} != {second_hash}"
            )
        if checks != second_checks:
            raise RuntimeError("B13a validation differs between deterministic builds")
        if any(
            value != 0
            for key, value in checks.items()
            if key not in {"quick_check", "integrity_check"}
        ):
            raise RuntimeError(f"B13a graph validation failed: {checks}")
        if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
            raise RuntimeError(f"B13a SQLite validation failed: {checks}")
        shutil.copyfile(first, args.output)

    manifest = {
        "phase": "B13a-native-hiram-erenor-evolution-catalogue",
        "authority_order": [
            "compact-client-8.0-decrypted.sqlite",
            "game11_native",
            "x2game_confirmed",
            "observed_protocol",
        ],
        "base_runtime": {
            "path": str(args.base_runtime),
            "sha256": sha256(args.base_runtime),
        },
        "output": {"path": str(args.output), "sha256": sha256(args.output)},
        "target_groups": TARGET_GROUPS,
        "material_groups": MATERIAL_GROUPS,
        "family_item_count": len(family_items),
        "category_count": len(category_ids),
        "table_counts": {name: len(rows) for name, rows in sorted(tables.items())},
        "awakening_reactive_counts": {
            name: len(rows)
            for name, rows in sorted(awakening_reactives.items())
        },
        "blocked_awakening_relations": [
            {
                "skill_effect_id": int(row["id"]),
                "skill_id": int(row["skill_id"]),
                "reason": "skill_absent_from_client_compact_8",
            }
            for row in awakening_reactives["excluded_skill_effects"]
        ],
        "source_ranges": ranges,
        "validation": checks,
        "protocol_evidence": {
            "synthesis_skill": 30666,
            "synthesis_effect": 20058,
            "synthesis_special_type": 123,
            "reroll_skill": 32060,
            "reroll_effect": 21462,
            "reroll_special_type": 136,
            "skill_object_type": 6,
            "material_count_field": "SkillItem.Type2",
            "x2game_execute": "FUN_39120cc0",
            "awakening_mode": 11,
            "awakening_special_type": 165,
            "awakening_mapping_group_field": "SpecialEffect.value1",
            "awakening_consume_count_name": "awakenConsumeCount",
        },
        "excluded_as_historical": ["item_rnd_attr_category_materials"],
        "provenance": {
            name: "game11_native" for name in tables
        },
        "awakening_reactive_provenance": {
            "skills": "client_compact_8",
            "effects": "client_compact_8+x2game_confirmed_actual_type",
            "skill_effects": "game11_native",
            "special_effects": "game11_native",
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
