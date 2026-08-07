#!/usr/bin/env python3
"""Build the first transversal AA8 quest-repair runtime.

This layer preserves the broad, stable NPC visual runtime and imports only the
exact Kakao item row required to close quest 2259. Server-side transversal
guards and packet fixes are versioned in source; no historical 3.0 quest rows
or restrictive quest catalogue are introduced here.
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
    r"\compact-8.0-runtime-native-npc-visual-v1.sqlite3"
)
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest-repair-stack-v1.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN
    / "generated"
    / "native-quest-repair-stack-v1-runtime-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7"
)
EXPECTED_GAME11_SHA256 = (
    "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"
)
QUEST_ID = 2259
ITEM_ID = 16259


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


def extract_native_item(game11: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    character = load_module(
        "native_character_item_extractor_stack_v1",
        ROOT / "reconstruccion_character_8" / "extract_native_character_creation.py",
    )
    parser = character.load_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    rows, source = character.extract_referenced_items(parser, reader, {ITEM_ID})
    if len(rows) != 1 or int(rows[0]["id"]) != ITEM_ID:
        raise RuntimeError("native item 16259 extraction is not unique")

    item = dict(rows[0])
    expected = {
        "category_id": 64,
        "impl_id": 0,
        "auto_complete": 1,
        "bind_id": 2,
        "icon_id": 1554,
        "loot_multi": 1,
        "loot_quest_id": QUEST_ID,
        "max_stack_size": 1,
        "use_skill_id": 0,
        "use_skill_as_reagent": 1,
        "fixed_grade": -1,
        "gradable": 0,
        "pickup_sound_id": 204,
        "use_or_equipment_sound_id": 341,
    }
    failures = {
        key: {"expected": value, "actual": item.get(key)}
        for key, value in expected.items()
        if item.get(key) != value
    }
    if failures:
        raise RuntimeError(f"native item 16259 differs: {failures}")
    return item, source


def tuples(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in connection.execute(sql, parameters)]


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0],
        "context": tuple(
            connection.execute(
                "SELECT category_id,chapter_idx,quest_idx,successive,race,"
                "level,detail_id,zone_id FROM quest_contexts WHERE id=?",
                (QUEST_ID,),
            ).fetchone()
        ),
        "components": tuples(
            connection,
            "SELECT id,component_kind_id FROM quest_components "
            "WHERE quest_context_id=? ORDER BY id",
            (QUEST_ID,),
        ),
        "acts": tuples(
            connection,
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE quest_component_id IN "
            "(9955,9956,9957,9958,10001) ORDER BY id",
        ),
        "accept": tuple(
            connection.execute(
                "SELECT id,npc_id FROM quest_act_con_accept_npcs WHERE id=1855"
            ).fetchone()
        ),
        "report": tuple(
            connection.execute(
                "SELECT id,npc_id FROM quest_act_con_report_npcs WHERE id=2091"
            ).fetchone()
        ),
        "initial_supply": tuple(
            connection.execute(
                "SELECT id,item_id,count,grade_id,cleanup,destroy_when_drop,"
                "drop_when_destroy FROM quest_act_supply_items WHERE id=2233"
            ).fetchone()
        ),
        "objective": tuple(
            connection.execute(
                "SELECT id,item_id,count,cleanup,destroy_when_drop,"
                "drop_when_destroy FROM quest_act_obj_item_gathers WHERE id=1012"
            ).fetchone()
        ),
        "item": tuple(
            connection.execute(
                "SELECT id,category_id,impl_id,auto_complete,bind_id,icon_id,"
                "loot_multi,loot_quest_id,max_stack_size,use_skill_id,"
                "use_skill_as_reagent,fixed_grade,gradable,pickup_sound_id,"
                "use_or_equipment_sound_id FROM items WHERE id=?",
                (ITEM_ID,),
            ).fetchone()
        ),
        "coverage": tuple(
            connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=?",
                (ITEM_ID,),
            ).fetchone()
        ),
        "npcs": tuples(
            connection,
            "SELECT id,model_id,equip_cloths_id,equip_weapons_id,"
            "total_custom_id FROM npcs WHERE id IN (3611,10582) ORDER BY id",
        ),
        "reward_coverage": tuple(
            connection.execute(
                "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
                "WHERE item_id=18792"
            ).fetchone()
        ),
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "context": (3, 2, 2, 0, 1, 5, 2, 124),
        "components": [
            (9955, 2),
            (9956, 3),
            (9957, 6),
            (9958, 4),
            (10001, 8),
        ],
        "acts": [
            (14152, "QuestActConAcceptNpc", 1855, 9955),
            (14154, "QuestActConReportNpc", 2091, 9957),
            (15203, "QuestActObjItemGather", 1012, 9958),
            (22574, "QuestActSupplyItem", 2233, 9956),
        ],
        "accept": (1855, 3611),
        "report": (2091, 10582),
        "initial_supply": (2233, ITEM_ID, 1, 0, 1, 1, 1),
        "objective": (1012, ITEM_ID, 1, 1, 1, 0),
        "item": (
            ITEM_ID,
            64,
            0,
            1,
            2,
            1554,
            1,
            QUEST_ID,
            1,
            0,
            1,
            -1,
            0,
            204,
            341,
        ),
        "coverage": (
            "generic",
            "complete",
            "",
            "game11_native_items:quest2259_delivery_item",
        ),
        "npcs": [
            (3611, 10, 1064, 144, 422),
            (10582, 10, 1199, 136, 0),
        ],
        "reward_coverage": (18792, "complete"),
    }
    failures = {
        key: {"expected": value, "actual": checks[key]}
        for key, value in expected.items()
        if checks[key] != value
    }
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

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

    item, source = extract_native_item(options.game11)
    green = load_module(
        "green_builder_stack_v1",
        DOMAIN / "build_native_nuian_green_arc_runtime.py",
    )

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)
    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        sanitized, fallbacks = green.sanitize_unresolved_strings(
            connection, "items", [item]
        )
        green.replace_rows(connection, "items", sanitized)
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            (
                ITEM_ID,
                "generic",
                "complete",
                "",
                "game11_native_items:quest2259_delivery_item",
            ),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-repair-stack-v1",
                "ArcheAge Kakao 8.0.3.12 r558734",
                game11_hash,
                str(QUEST_ID),
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
        "format_version": 1,
        "phase": "native-quest-repair-stack-v1-runtime",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": base_hash,
            },
            "game11_items": {
                "path": str(options.game11),
                "sha256": game11_hash,
                "source_range": [source["start"], source["end"]],
                "rows": source["rows"],
                "loader": source["loader"],
                "item_id": ITEM_ID,
            },
            "quest_dossier": {
                "path": (
                    "E:\\AAEmu-Research\\output\\aa8-client-forensics"
                    "\\dossiers\\quest-2259.json"
                ),
                "sha256": (
                    "8F7F9578060849342CA19D30B179C829ED28D399D02E50C7F197E8FCCE824565"
                ),
            },
            "item_dossier": {
                "path": (
                    "E:\\AAEmu-Research\\output\\aa8-client-forensics"
                    "\\dossiers\\item-16259.json"
                ),
                "sha256": (
                    "D585FE288552A65A89050A1D6873301D0893A84B8F06A41EC8F26091690C7267"
                ),
            },
            "visible_behavior_corroboration": {
                "authority": "corroboration_only",
                "url": "https://wiki.archerage.to/na-en/db/quests/2259",
            },
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "item_ids": [ITEM_ID],
            "accept_npc_ids": [3611],
            "report_npc_ids": [10582],
            "server_families": [
                "selective_item_inventory_delta",
                "quest_loot_idempotence",
                "skill_cast_reentry",
                "skill_object_type_28",
            ],
        },
        "native_chain": {
            "start_component": 9955,
            "supply_component": 9956,
            "supply_item_act": 2233,
            "progress_component": 9958,
            "item_gather_act": 1012,
            "ready_component": 9957,
            "reward_component": 10001,
        },
        "item_definition": {
            "concrete_type": "generic",
            "coverage": "complete",
            "use_skill_id": 0,
            "missing_dependencies": [],
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
    print(json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
