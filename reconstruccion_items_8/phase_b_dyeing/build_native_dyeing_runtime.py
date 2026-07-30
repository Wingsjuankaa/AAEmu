#!/usr/bin/env python3
"""Build the isolated native AA8 dyeing runtime candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
PARSER_PATH = (
    ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"
)

DYEABLE_START = 93_390_348
DYEABLE_END = 93_392_976
DYEABLE_ROWS = 292
DYEABLE_LAYOUT = ["68", "68"]
DYEABLE_COLUMNS = ["item_id", "color"]

SKILL_IDS = {22_727, 39_137, 43_874}
SKILL_EFFECT_IDS = {24_991, 54_727, 62_895}
EFFECT_IDS = {31_866, 70_986, 83_102}
GAIN_EFFECT_IDS = {3_802, 4_360}
DYEING_BRIDGE_ITEMS = {
    45_632: "dyeing_wrapper",
    48_965: "dyeing_ticket",
}
LOOT_ROWS = [
    {
        "id": 88_012_508,
        "group": 1,
        "item_id": 45_632,
        "drop_rate": 10_000_000,
        "min_amount": 1,
        "max_amount": 1,
        "loot_pack_id": 12_508,
        "grade_id": 0,
        "always_drop": "t",
    },
    {
        "id": 88_013_114,
        "group": 1,
        "item_id": 48_965,
        "drop_rate": 10_000_000,
        "min_amount": 1,
        "max_amount": 1,
        "loot_pack_id": 13_114,
        "grade_id": 0,
        "always_drop": "t",
    },
]

EVIDENCE_FILES = {
    "ghidra_dyeing_structures_x64":
        "ghidra-dyeing-structures-64.txt",
    "ghidra_dyeing_exact_protocol_x86":
        "ghidra-dyeing-exact-protocol-32.txt",
    "ghidra_dyeing_consumers_x86":
        "ghidra-dyeing-consumers-32.txt",
    "ghidra_dyeing_color_consumers_x86":
        "ghidra-dyeing-color-consumers-32.txt",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", required=True, type=Path)
    parser.add_argument("--client-compact", required=True, type=Path)
    parser.add_argument("--base-runtime", required=True, type=Path)
    parser.add_argument("--forensics-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json(document: Any) -> str:
    return json.dumps(
        document,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def load_parser():
    spec = importlib.util.spec_from_file_location(
        "aa8_dyeing_cached_result",
        PARSER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def query_rows(
    connection: sqlite3.Connection,
    table: str,
    ids: Iterable[int],
) -> list[dict[str, Any]]:
    values = sorted(set(int(value) for value in ids))
    placeholders = ",".join("?" for _ in values)
    connection.row_factory = sqlite3.Row
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {table} "
            f"WHERE id IN ({placeholders}) ORDER BY id",
            values,
        )
    ]


def extract(
    game11: Path,
    client_compact: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    parser = load_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    raw_dyeable, dyeable_end = parser.read_cached_result(
        reader,
        DYEABLE_START,
        DYEABLE_LAYOUT,
    )
    dyeable_items = [
        dict(zip(DYEABLE_COLUMNS, row, strict=True))
        for row in raw_dyeable
    ]
    if len(dyeable_items) != DYEABLE_ROWS:
        raise RuntimeError(
            f"dyeable_items: expected {DYEABLE_ROWS}, "
            f"got {len(dyeable_items)}"
        )
    if dyeable_end != DYEABLE_END:
        raise RuntimeError(
            f"dyeable_items: expected end {DYEABLE_END}, got {dyeable_end}"
        )
    item_ids = [int(row["item_id"]) for row in dyeable_items]
    if len(set(item_ids)) != DYEABLE_ROWS:
        raise RuntimeError("dyeable_items contains duplicate item ids")
    alpha_values = sorted(
        {
            (int(row["color"]) & 0xFFFFFFFF) >> 24
            for row in dyeable_items
        }
    )
    if alpha_values != [0xFF]:
        raise RuntimeError(
            f"dyeable_items contains unexpected alpha values {alpha_values}"
        )

    relationships = parser.extract_client_relationships(game11)
    skill_effects = [
        {
            **dict(row),
            "start_high_ability_resource":
                int(row.get("start_combat_resource") or 0),
            "end_high_ability_resource":
                int(row.get("end_combat_resource") or 0),
            "end_level": 255
            if int(row.get("end_level") or 0) == 99
            else int(row.get("end_level") or 0),
        }
        for row in relationships["skill_effects"]
        if int(row["id"]) in SKILL_EFFECT_IDS
    ]
    if {int(row["id"]) for row in skill_effects} != SKILL_EFFECT_IDS:
        raise RuntimeError("The native dyeing skill-effect closure is incomplete")

    with sqlite3.connect(client_compact) as connection:
        skills = query_rows(connection, "skills", SKILL_IDS)
        effects = query_rows(connection, "effects", EFFECT_IDS)
        gain_effects = query_rows(
            connection,
            "gain_loot_pack_item_effects",
            GAIN_EFFECT_IDS,
        )
        placeholders = ",".join("?" for _ in item_ids)
        present_dyeable_item_ids = {
            int(row[0])
            for row in connection.execute(
                f"SELECT id FROM items WHERE id IN ({placeholders})",
                item_ids,
            )
        }
        dyeable_tombstones = sorted(
            set(item_ids) - present_dyeable_item_ids
        )
        connection.row_factory = sqlite3.Row
        dyeing_items = [
            dict(row)
            for row in connection.execute(
                """
                SELECT id,use_skill_id FROM items
                WHERE id>0 AND impl_id=27 ORDER BY id
                """
            )
        ]
        if len(dyeing_items) != 26:
            raise RuntimeError(
                "Dyeing item lifecycle changed: expected 26 positive "
                f"impl_id=27 rows, got {len(dyeing_items)}"
            )
        if {
            int(row["use_skill_id"])
            for row in dyeing_items
        } != {22_727, 39_137}:
            raise RuntimeError(
                "Dyeing items reference an unexpected native skill set"
            )
        if len(dyeable_tombstones) != 25:
            raise RuntimeError(
                "dyeable_items lifecycle changed: expected 25 item "
                f"tombstones, got {len(dyeable_tombstones)}"
            )
    if {int(row["id"]) for row in skills} != SKILL_IDS:
        raise RuntimeError("The native dyeing skill rows are incomplete")
    if {int(row["id"]) for row in effects} != EFFECT_IDS:
        raise RuntimeError("The native dyeing effect rows are incomplete")
    if {int(row["id"]) for row in gain_effects} != GAIN_EFFECT_IDS:
        raise RuntimeError("The native dyeing gain-effect rows are incomplete")

    for row in effects:
        if int(row["id"]) in {70_986, 83_102}:
            row["actual_type"] = "GainLootPackItemEffect"
        elif int(row["id"]) == 31_866:
            row["actual_type"] = "SpecialEffect"

    tables = {
        "dyeable_items": dyeable_items,
        "skill_effects": skill_effects,
        "effects": effects,
        "gain_loot_pack_item_effects": gain_effects,
        "skills": skills,
        "dyeing_items": dyeing_items,
    }
    facts = {
        "dyeable_items": {
            "query": "SELECT item_id, color FROM dyeable_items",
            "start": DYEABLE_START,
            "end": dyeable_end,
            "rows": len(dyeable_items),
            "distinct_colors": len(
                {int(row["color"]) & 0xFFFFFFFF for row in dyeable_items}
            ),
            "alpha_values": alpha_values,
            "physical_item_rows": len(present_dyeable_item_ids),
            "tombstone_count": len(dyeable_tombstones),
            "tombstone_item_ids": dyeable_tombstones,
            "loader_x64": "FUN_399478e0",
            "loader_x86": "FUN_39ade0e0",
        },
        "skill_effect_ids": sorted(SKILL_EFFECT_IDS),
        "effect_ids": sorted(EFFECT_IDS),
        "gain_effect_ids": sorted(GAIN_EFFECT_IDS),
        "loot_rows": LOOT_ROWS,
        "bridge_items": [
            {
                "item_id": item_id,
                "concrete_type": concrete_type,
            }
            for item_id, concrete_type in sorted(
                DYEING_BRIDGE_ITEMS.items()
            )
        ],
        "dyeing_item_ids": [
            int(row["id"])
            for row in dyeing_items
        ],
    }
    return tables, facts


def compatible_insert(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
) -> None:
    available = {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})")
    }
    for row in sorted(rows, key=lambda value: int(value["id"])):
        columns = [
            column
            for column in row
            if column in available and
            column not in {"start_combat_resource", "end_combat_resource"}
        ]
        placeholders = ",".join("?" for _ in columns)
        connection.execute(
            f"INSERT OR REPLACE INTO {table} "
            f"({','.join(columns)}) VALUES ({placeholders})",
            tuple(row[column] for column in columns),
        )


def validate(
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute(
            "PRAGMA quick_check"
        ).fetchone()[0],
        "integrity_check": connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0],
        "dyeable_items": connection.execute(
            "SELECT COUNT(*) FROM dyeable_items"
        ).fetchone()[0],
        "distinct_dyeable_items": connection.execute(
            "SELECT COUNT(DISTINCT item_id) FROM dyeable_items"
        ).fetchone()[0],
        "non_opaque_default_colors": connection.execute(
            """
            SELECT COUNT(*) FROM dyeable_items
            WHERE ((color & 4294967295) >> 24) != 255
            """
        ).fetchone()[0],
        "native_dyeable_tombstones": connection.execute(
            """
            SELECT COUNT(*) FROM dyeable_items d
            LEFT JOIN items i ON i.id=d.item_id
            WHERE i.id IS NULL
            """
        ).fetchone()[0],
        "historical_item_dyeings": connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='item_dyeings'
            """
        ).fetchone()[0],
        "historical_dyeing_colors": connection.execute(
            """
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name='dyeing_colors'
            """
        ).fetchone()[0],
        "native_skill_effects": connection.execute(
            "SELECT COUNT(*) FROM skill_effects "
            "WHERE id IN (24991,54727,62895)"
        ).fetchone()[0],
        "native_effects": connection.execute(
            "SELECT COUNT(*) FROM effects "
            "WHERE id IN (31866,70986,83102)"
        ).fetchone()[0],
        "native_gain_effects": connection.execute(
            "SELECT COUNT(*) FROM gain_loot_pack_item_effects "
            "WHERE id IN (3802,4360)"
        ).fetchone()[0],
        "derived_loot_rows": connection.execute(
            "SELECT COUNT(*) FROM loots "
            "WHERE loot_pack_id IN (12508,13114)"
        ).fetchone()[0],
        "orphan_skill_effects": connection.execute(
            """
            SELECT COUNT(*) FROM skill_effects se
            LEFT JOIN skills s ON s.id=se.skill_id
            LEFT JOIN effects e ON e.id=se.effect_id
            WHERE se.id IN (24991,54727,62895)
              AND (s.id IS NULL OR e.id IS NULL)
            """
        ).fetchone()[0],
        "orphan_gain_effects": connection.execute(
            """
            SELECT COUNT(*) FROM effects e
            LEFT JOIN gain_loot_pack_item_effects g
              ON g.id=e.actual_id
            WHERE e.id IN (70986,83102)
              AND (e.actual_type!='GainLootPackItemEffect' OR g.id IS NULL)
            """
        ).fetchone()[0],
        "orphan_loot_items": connection.execute(
            """
            SELECT COUNT(*) FROM loots l
            LEFT JOIN items i ON i.id=l.item_id
            WHERE l.loot_pack_id IN (12508,13114) AND i.id IS NULL
            """
        ).fetchone()[0],
        "phase_a_dyeing_items": connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_item_definition_coverage
            WHERE concrete_type='dyeing'
              AND coverage='phase_a_candidate'
              AND provenance LIKE '%backend_implemented%'
            """
        ).fetchone()[0],
        "phase_a_dyeing_closure_items": connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_item_definition_coverage
            WHERE provenance LIKE '%b15_dyeing_closure%'
              AND coverage='phase_a_candidate'
            """
        ).fetchone()[0],
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "dyeable_items": 292,
        "distinct_dyeable_items": 292,
        "non_opaque_default_colors": 0,
        "native_dyeable_tombstones": 25,
        "historical_item_dyeings": 0,
        "historical_dyeing_colors": 0,
        "native_skill_effects": 3,
        "native_effects": 3,
        "native_gain_effects": 2,
        "derived_loot_rows": 2,
        "orphan_skill_effects": 0,
        "orphan_gain_effects": 0,
        "orphan_loot_items": 0,
        "phase_a_dyeing_items": 26,
        "phase_a_dyeing_closure_items": 28,
    }
    for key, value in expected.items():
        if checks[key] != value:
            raise RuntimeError(
                f"Validation failed for {key}: "
                f"{checks[key]!r} != {value!r}"
            )
    return checks


def build(
    base_runtime: Path,
    output: Path,
    tables: dict[str, list[dict[str, Any]]],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    shutil.copyfile(base_runtime, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")

        connection.execute("DROP TABLE IF EXISTS dyeable_items")
        connection.execute(
            """
            CREATE TABLE dyeable_items (
                item_id INTEGER PRIMARY KEY,
                color INTEGER NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO dyeable_items (item_id,color) "
            "VALUES (:item_id,:color)",
            sorted(
                tables["dyeable_items"],
                key=lambda row: int(row["item_id"]),
            ),
        )
        connection.execute("DROP TABLE IF EXISTS item_dyeings")
        connection.execute("DROP TABLE IF EXISTS dyeing_colors")

        compatible_insert(
            connection,
            "skill_effects",
            tables["skill_effects"],
        )
        compatible_insert(connection, "effects", tables["effects"])
        compatible_insert(
            connection,
            "gain_loot_pack_item_effects",
            tables["gain_loot_pack_item_effects"],
        )
        connection.executemany(
            """
            UPDATE aaemu_item_definition_coverage
            SET concrete_type='dyeing',
                coverage='phase_a_candidate',
                missing_dependencies='manual_client_acceptance',
                provenance='client_compact_8+game11_native+x2game_confirmed+backend_implemented+b15_dyeing_closure'
            WHERE item_id=?
            """,
            (
                (int(row["id"]),)
                for row in tables["dyeing_items"]
            ),
        )
        connection.executemany(
            """
            UPDATE aaemu_item_definition_coverage
            SET concrete_type=?,
                coverage='phase_a_candidate',
                missing_dependencies='manual_client_acceptance',
                provenance='client_compact_8+game11_native+x2game_confirmed+backend_implemented+b15_dyeing_closure'
            WHERE item_id=?
            """,
            (
                (concrete_type, item_id)
                for item_id, concrete_type in sorted(
                    DYEING_BRIDGE_ITEMS.items()
                )
            ),
        )

        for loot_pack_id in (12_508, 13_114):
            connection.execute(
                "DELETE FROM loots WHERE loot_pack_id=?",
                (loot_pack_id,),
            )
            connection.execute(
                "DELETE FROM loot_groups WHERE pack_id=?",
                (loot_pack_id,),
            )
        connection.executemany(
            """
            INSERT INTO loots (
                id,"group",item_id,drop_rate,min_amount,max_amount,
                loot_pack_id,grade_id,always_drop
            ) VALUES (
                :id,:group,:item_id,:drop_rate,:min_amount,:max_amount,
                :loot_pack_id,:grade_id,:always_drop
            )
            """,
            LOOT_ROWS,
        )

        connection.execute(
            """
            INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
            VALUES
              ('phase','B15-native-dyeing'),
              ('dyeing_protocol','x2game_x86_x64_confirmed'),
              ('dyeing_persistence','equipment_detail_0x14_gemids_2'),
              ('dyeing_loot_bindings','server_derived_visible_AA8_outputs'),
              ('dyeing_deployable','false_pending_client_acceptance')
            """
        )
        for key, value in sorted(source_hashes.items()):
            connection.execute(
                """
                INSERT OR REPLACE INTO aaemu_item_phase_b_metadata (key,value)
                VALUES (?,?)
                """,
                (f"sha256_{key}", value),
            )
        connection.commit()
        connection.execute("VACUUM")
        return validate(connection)
    finally:
        connection.close()


def main() -> int:
    options = arguments()
    for path in (
        options.game11,
        options.client_compact,
        options.base_runtime,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)

    evidence_paths = {
        key: options.forensics_dir / filename
        for key, filename in EVIDENCE_FILES.items()
    }
    for path in evidence_paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    tables, facts = extract(options.game11, options.client_compact)
    source_hashes = {
        "game11": sha256(options.game11),
        "client_compact": sha256(options.client_compact),
        "base_runtime": sha256(options.base_runtime),
        **{
            key: sha256(path)
            for key, path in sorted(evidence_paths.items())
        },
    }

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-dyeing-") as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        checks = build(
            options.base_runtime,
            first,
            tables,
            source_hashes,
        )
        second_checks = build(
            options.base_runtime,
            second,
            tables,
            source_hashes,
        )
        if checks != second_checks:
            raise RuntimeError("The two validation reports differ")
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash:
            raise RuntimeError(
                f"Non-deterministic build: {first_hash} != {second_hash}"
            )
        shutil.copyfile(first, options.output)

    manifest = {
        "format_version": 1,
        "phase": "B15-native-dyeing",
        "classification": "native_relation_evidence_superseded_runtime_experiment",
        "authority": [
            "client_compact_8",
            "game11_native",
            "x2game_confirmed",
            "wiki_archerage_visible_corroboration",
            "server_derived",
        ],
        "sources": source_hashes,
        "facts": facts,
        "server_derived": {
            "loot_rows": LOOT_ROWS,
            "corroboration": [
                {
                    "entity": "item",
                    "id": 45632,
                    "url": (
                        "https://wiki.archerage.to/na-en/db/items/45632"
                    ),
                    "visible_fact": "Wrapped Dye Ticket grants item 48965",
                }
            ],
            "reason": (
                "AA8 client effects identify loot packs 12508 and 13114; "
                "the matching-version visible database confirms the single "
                "outputs 45632 and 48965. The client compact has no server "
                "loots table."
            ),
        },
        "output": {
            "path": str(options.output.resolve()),
            "sha256": sha256(options.output),
            **checks,
        },
        "deployment": {
            "active": False,
            "deployable": False,
            "superseded_by": "aa8-client-forensics",
            "blocking": [
                "server implementation is outside the client-forensics scope",
            ],
        },
    }
    options.manifest.write_text(
        canonical_json(manifest),
        encoding="utf-8",
    )
    print(canonical_json(manifest["output"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
