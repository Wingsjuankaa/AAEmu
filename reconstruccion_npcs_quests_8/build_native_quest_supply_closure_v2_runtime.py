#!/usr/bin/env python3
"""Build the versioned AA8 initial quest-supply closure runtime.

The repair is transversal by contract rather than heuristic: every promoted
entry must have an explicit quest dossier, an exact native item row and a
dependency-free generic descriptor. Items with a concrete implementation,
buff, craft or use-skill dependency remain fail-closed for later dossiers.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-point0-rifle-stack-v1.sqlite3"
)
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-point0-quest-supply-stack-v2.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-quest-supply-closure-v2-runtime-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "503BF9639F2005130C9E63A66A443AEA09577C082D7CE8EDC8AB11DA9118B77A"
)
EXPECTED_GAME11_SHA256 = (
    "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"
)
AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
PROVENANCE = "game11_native_items:quest_initial_supply_generic_v2"

# Adding a future entry here is intentionally insufficient on its own: the
# structural and dependency checks below must also pass, and its dossier/wiki
# evidence must be added to SOURCES before the build is accepted.
CLOSURES = (
    {
        "quest_id": 2259,
        "item_id": 16259,
        "context": (3, 2, 2, 0, 1, 5, 2, 124),
        "components": ((9955, 2), (9956, 3), (9957, 6), (9958, 4), (10001, 8)),
        "accept": (1855, 3611),
        "report": (2091, 10582),
        "supply": (2233, 16259, 1, 0, 1, 1, 1),
        "gather": (1012, 16259, 1, 1, 1, 0),
        "item_core": (64, 0, 1, 2, 1554, 1, 2259, 1, 0, 1, -1, 0, 204, 341),
    },
    {
        "quest_id": 2260,
        "item_id": 16260,
        "context": (3, 2, 3, 0, 1, 5, 2, 124),
        "components": ((9959, 2), (9960, 3), (9961, 6), (9962, 8), (10002, 4)),
        "accept": (1856, 10582),
        "report": (2092, 10583),
        "supply": (1334, 16260, 1, 0, 1, 1, 1),
        "gather": (938, 16260, 1, 1, 1, 0),
        "item_core": (64, 0, 1, 2, 1554, 1, 2260, 1, 0, 1, -1, 0, 204, 341),
    },
)

SOURCES = {
    2259: {
        "quest_dossier": {
            "path": r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\quest-2259.json",
            "sha256": "8F7F9578060849342CA19D30B179C829ED28D399D02E50C7F197E8FCCE824565",
        },
        "item_dossier": {
            "path": r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\item-16259.json",
            "sha256": "D585FE288552A65A89050A1D6873301D0893A84B8F06A41EC8F26091690C7267",
        },
        "wiki": "https://wiki.archerage.to/na-en/db/quests/2259",
    },
    2260: {
        "quest_dossier": {
            "path": r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\quest-2260.json",
            "sha256": "574CA90A7E98B863C491610D00D965F3D3C0512C1AE38C9AAC086286679B8549",
        },
        "item_dossier": {
            "path": r"E:\AAEmu-Research\output\aa8-client-forensics\dossiers\item-16260.json",
            "sha256": "A248CB8CD805D0D16380A792FFA5EABD1A506BCD81B08438C699A37A16BD5468",
        },
        "wiki": "https://wiki.archerage.to/na-en/db/quests/2260",
    },
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def tuples(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in connection.execute(sql, parameters)]


def extract_native_items(game11: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    character = load_module(
        "native_character_item_extractor_supply_v2",
        ROOT / "reconstruccion_character_8" / "extract_native_character_creation.py",
    )
    parser = character.load_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    item_ids = {int(entry["item_id"]) for entry in CLOSURES}
    rows, source = character.extract_referenced_items(parser, reader, item_ids)
    if {int(row["id"]) for row in rows} != item_ids:
        raise RuntimeError("native initial supply extraction is not one-to-one")

    failures: dict[int, dict[str, Any]] = {}
    by_id = {int(row["id"]): row for row in rows}
    for entry in CLOSURES:
        item_id = int(entry["item_id"])
        row = by_id[item_id]
        dependency_fields = {
            "impl_id": int(row["impl_id"]),
            "use_skill_id": int(row["use_skill_id"]),
            "buff_id": int(row["buff_id"]),
            "craft_id": int(row["craft_id"]),
        }
        if dependency_fields != {
            "impl_id": 0,
            "use_skill_id": 0,
            "buff_id": 0,
            "craft_id": 0,
        }:
            failures[item_id] = dependency_fields
    if failures:
        raise RuntimeError(f"initial supply items are not dependency-free generic rows: {failures}")
    return rows, source


def initial_supply_audit(connection: sqlite3.Connection) -> dict[str, int]:
    sql = """
        SELECT COUNT(*), COUNT(DISTINCT qasi.item_id),
               SUM(CASE WHEN COALESCE(c.coverage,'') != 'complete' THEN 1 ELSE 0 END),
               COUNT(DISTINCT CASE WHEN COALESCE(c.coverage,'') != 'complete'
                                   THEN qasi.item_id END)
        FROM quest_components qc
        JOIN quest_acts qa ON qa.quest_component_id=qc.id
                          AND qa.act_detail_type='QuestActSupplyItem'
        JOIN quest_act_supply_items qasi ON qasi.id=qa.act_detail_id
        LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=qasi.item_id
        WHERE qc.component_kind_id=3
    """
    row = connection.execute(sql).fetchone()
    return {
        "acts": int(row[0]),
        "distinct_items": int(row[1]),
        "incomplete_acts": int(row[2]),
        "incomplete_distinct_items": int(row[3]),
    }


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "closures": {},
        "reward_dependencies_2260": tuples(
            connection,
            "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
            "WHERE item_id IN (23633,48507) ORDER BY item_id",
        ),
        "initial_supply_audit": initial_supply_audit(connection),
        "target_item_row_counts": tuples(
            connection,
            "SELECT id,COUNT(*) FROM items WHERE id IN (16259,16260) "
            "GROUP BY id ORDER BY id",
        ),
    }
    failures: dict[str, Any] = {}
    for entry in CLOSURES:
        quest_id = int(entry["quest_id"])
        item_id = int(entry["item_id"])
        actual = {
            "context": tuple(
                connection.execute(
                    "SELECT category_id,chapter_idx,quest_idx,successive,race,"
                    "level,detail_id,zone_id FROM quest_contexts WHERE id=?",
                    (quest_id,),
                ).fetchone()
            ),
            "components": tuples(
                connection,
                "SELECT id,component_kind_id FROM quest_components "
                "WHERE quest_context_id=? ORDER BY id",
                (quest_id,),
            ),
            "accept": tuple(
                connection.execute(
                    "SELECT id,npc_id FROM quest_act_con_accept_npcs WHERE id=?",
                    (entry["accept"][0],),
                ).fetchone()
            ),
            "report": tuple(
                connection.execute(
                    "SELECT id,npc_id FROM quest_act_con_report_npcs WHERE id=?",
                    (entry["report"][0],),
                ).fetchone()
            ),
            "supply": tuple(
                connection.execute(
                    "SELECT id,item_id,count,grade_id,cleanup,destroy_when_drop,"
                    "drop_when_destroy FROM quest_act_supply_items WHERE id=?",
                    (entry["supply"][0],),
                ).fetchone()
            ),
            "gather": tuple(
                connection.execute(
                    "SELECT id,item_id,count,cleanup,destroy_when_drop,"
                    "drop_when_destroy FROM quest_act_obj_item_gathers WHERE id=?",
                    (entry["gather"][0],),
                ).fetchone()
            ),
            "item_core": tuple(
                connection.execute(
                    "SELECT category_id,impl_id,auto_complete,bind_id,icon_id,"
                    "loot_multi,loot_quest_id,max_stack_size,use_skill_id,"
                    "use_skill_as_reagent,fixed_grade,gradable,pickup_sound_id,"
                    "use_or_equipment_sound_id FROM items WHERE id=?",
                    (item_id,),
                ).fetchone()
            ),
            "coverage": tuple(
                connection.execute(
                    "SELECT concrete_type,coverage,missing_dependencies,provenance "
                    "FROM aaemu_item_definition_coverage WHERE item_id=?",
                    (item_id,),
                ).fetchone()
            ),
        }
        expected = {
            "context": tuple(entry["context"]),
            "components": list(entry["components"]),
            "accept": tuple(entry["accept"]),
            "report": tuple(entry["report"]),
            "supply": tuple(entry["supply"]),
            "gather": tuple(entry["gather"]),
            "item_core": tuple(entry["item_core"]),
            "coverage": ("generic", "complete", "", PROVENANCE),
        }
        difference = {
            key: {"expected": expected[key], "actual": actual[key]}
            for key in expected
            if expected[key] != actual[key]
        }
        if difference:
            failures[str(quest_id)] = difference
        checks["closures"][str(quest_id)] = actual

    if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
        failures["sqlite"] = {
            "quick_check": checks["quick_check"],
            "integrity_check": checks["integrity_check"],
        }
    if checks["reward_dependencies_2260"] != [(23633, "complete"), (48507, "complete")]:
        failures["reward_dependencies_2260"] = checks["reward_dependencies_2260"]
    if checks["initial_supply_audit"]["incomplete_acts"] != 999:
        failures["bounded_transversal_audit"] = checks["initial_supply_audit"]
    if checks["target_item_row_counts"] != [(16259, 1), (16260, 1)]:
        failures["target_item_row_counts"] = checks["target_item_row_counts"]
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def build(options: argparse.Namespace) -> dict[str, Any]:
    base_hash = sha256(options.base_runtime)
    if base_hash != EXPECTED_BASE_SHA256:
        raise RuntimeError(
            f"base runtime differs: expected {EXPECTED_BASE_SHA256}, got {base_hash}"
        )
    game11_hash = sha256(options.game11)
    if game11_hash != EXPECTED_GAME11_SHA256:
        raise RuntimeError(
            f"game11 differs: expected {EXPECTED_GAME11_SHA256}, got {game11_hash}"
        )

    for quest_id, evidence in SOURCES.items():
        for key in ("quest_dossier", "item_dossier"):
            path = Path(evidence[key]["path"])
            actual_hash = sha256(path)
            if actual_hash != evidence[key]["sha256"]:
                raise RuntimeError(
                    f"{key} for quest {quest_id} differs: {actual_hash}"
                )

    items, source = extract_native_items(options.game11)
    green = load_module(
        "green_builder_supply_v2",
        DOMAIN / "build_native_nuian_green_arc_runtime.py",
    )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copyfile(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    try:
        audit_before = initial_supply_audit(connection)
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        sanitized, fallbacks = green.sanitize_unresolved_strings(
            connection, "items", items
        )
        # `items.id` is not constrained as UNIQUE in the inherited runtime.
        # SQLite's INSERT OR REPLACE therefore cannot replace by item id.
        # Delete the exact bounded ids first so repeated layering remains
        # one-row-per-native-item and deterministic.
        item_ids = sorted(int(entry["item_id"]) for entry in CLOSURES)
        placeholders = ",".join("?" for _ in item_ids)
        connection.execute(
            f"DELETE FROM items WHERE id IN ({placeholders})",
            item_ids,
        )
        green.replace_rows(connection, "items", sanitized)
        connection.executemany(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            [
                (int(entry["item_id"]), "generic", "complete", "", PROVENANCE)
                for entry in CLOSURES
            ],
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-supply-closure-v2",
                AUTHORITY,
                game11_hash,
                ",".join(str(entry["quest_id"]) for entry in CLOSURES),
            ),
        )
        checks = validate(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    os.replace(temporary, options.output)
    document = {
        "format_version": 2,
        "phase": "native-quest-supply-closure-v2-runtime",
        "authority": AUTHORITY,
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": base_hash},
            "game11_items": {
                "path": str(options.game11),
                "sha256": game11_hash,
                "source_range": [source["start"], source["end"]],
                "rows": source["rows"],
                "loader": source["loader"],
                "item_ids": sorted(int(entry["item_id"]) for entry in CLOSURES),
            },
            "quests": {
                str(quest_id): {
                    **evidence,
                    "wiki_authority": "corroboration_only",
                }
                for quest_id, evidence in sorted(SOURCES.items())
            },
        },
        "scope": {
            "quest_ids": [int(entry["quest_id"]) for entry in CLOSURES],
            "item_ids": [int(entry["item_id"]) for entry in CLOSURES],
            "policy": (
                "explicit native generic initial SupplyItem closure only; "
                "items with unresolved concrete/use-skill dependencies remain fail-closed"
            ),
            "audit_before": audit_before,
            "audit_after": checks["initial_supply_audit"],
        },
        "unresolved_string_fallbacks": fallbacks,
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
    }
    options.manifest.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()
    print(json.dumps(build(options), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
