#!/usr/bin/env python3
"""Build the AA8-native quest 2258 runtime (Nuian green arc V5).

The V4 runtime already contains the native quest graph, Malphus, General
Govannon and the reward definitions. Quest 2258 could still be offered even
though its initial SupplyItem dependency was intentionally outside V4. This
builder imports the exact Kakao game11 row for item 16288 and promotes its
generic item definition after validating the complete delivery-only closure.
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
    r"\compact-8.0-runtime-native-nuian-green-arc-v4.sqlite3"
)
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v5.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN
    / "generated"
    / "native-quest-2258-urgent-message-v1-runtime-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "3538C7120360ADA99BF6EC0E0CC051812E962576E0F0264DCE8676558E90AE95"
)
QUEST_ID = 2258
ITEM_ID = 16288
COMPONENT_IDS = {9951, 9952, 9953, 9954, 9999}
ACT_IDS = {14150, 14151, 14195, 14196, 40847}


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
        "native_character_item_extractor",
        ROOT / "reconstruccion_character_8" / "extract_native_character_creation.py",
    )
    parser = character.load_parser()
    reader = parser.CachedResultReader(game11.read_bytes())
    rows, source = character.extract_referenced_items(parser, reader, {ITEM_ID})
    if len(rows) != 1 or int(rows[0]["id"]) != ITEM_ID:
        raise RuntimeError("native item 16288 extraction is not unique")
    item = dict(rows[0])
    expected = {
        "category_id": 64,
        "impl_id": 0,
        "auto_complete": 1,
        "bind_id": 2,
        "icon_id": 6360,
        "loot_multi": 1,
        "loot_quest_id": QUEST_ID,
        "max_stack_size": 10,
        "use_skill_id": 0,
    }
    failures = {
        key: {"expected": value, "actual": item.get(key)}
        for key, value in expected.items()
        if item.get(key) != value
    }
    if failures:
        raise RuntimeError(f"native item 16288 differs: {failures}")
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
            "(9951,9952,9953,9954,9999) ORDER BY id",
        ),
        "accept": tuple(
            connection.execute(
                "SELECT id,npc_id FROM quest_act_con_accept_npcs WHERE id=1854"
            ).fetchone()
        ),
        "report": tuple(
            connection.execute(
                "SELECT id,npc_id FROM quest_act_con_report_npcs WHERE id=2090"
            ).fetchone()
        ),
        "initial_supply": tuple(
            connection.execute(
                "SELECT id,item_id,count,grade_id,cleanup,destroy_when_drop "
                "FROM quest_act_supply_items WHERE id=1339"
            ).fetchone()
        ),
        "objective": tuple(
            connection.execute(
                "SELECT id,item_id,count,cleanup,destroy_when_drop "
                "FROM quest_act_obj_item_gathers WHERE id=935"
            ).fetchone()
        ),
        "item": tuple(
            connection.execute(
                "SELECT id,category_id,impl_id,auto_complete,bind_id,icon_id,"
                "loot_multi,loot_quest_id,max_stack_size,use_skill_id "
                "FROM items WHERE id=?",
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
        "report_npc": tuple(
            connection.execute(
                "SELECT id,model_id,equip_cloths_id,equip_weapons_id,"
                "total_custom_id FROM npcs WHERE id=3611"
            ).fetchone()
        ),
        "reward_coverage": tuples(
            connection,
            "SELECT item_id,coverage FROM aaemu_item_definition_coverage "
            "WHERE item_id IN (18791,23633) ORDER BY item_id",
        ),
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "context": (3, 2, 1, 0, 1, 5, 2, 125),
        "components": [(9951, 2), (9952, 3), (9953, 6), (9954, 8), (9999, 4)],
        "acts": [
            (14150, "QuestActConAcceptNpc", 1854, 9951),
            (14151, "QuestActConReportNpc", 2090, 9953),
            (14195, "QuestActSupplyItem", 1339, 9952),
            (14196, "QuestActObjItemGather", 935, 9999),
            (40847, "QuestActSupplyItem", 4814, 9954),
        ],
        "accept": (1854, 3630),
        "report": (2090, 3611),
        "initial_supply": (1339, ITEM_ID, 1, 0, 1, 1),
        "objective": (935, ITEM_ID, 1, 1, 1),
        "item": (ITEM_ID, 64, 0, 1, 2, 6360, 1, QUEST_ID, 10, 0),
        "coverage": (
            "generic",
            "complete",
            "",
            "game11_native_items:quest2258_delivery_item",
        ),
        "report_npc": (3611, 10, 1064, 144, 422),
        "reward_coverage": [(18791, "complete"), (23633, "complete")],
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
            f"base V4 runtime differs: expected {EXPECTED_BASE_SHA256}, got {base_hash}"
        )

    item, source = extract_native_item(options.game11)
    green = load_module(
        "green_builder", DOMAIN / "build_native_nuian_green_arc_runtime.py"
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
                "game11_native_items:quest2258_delivery_item",
            ),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-2258-urgent-message-v1",
                "ArcheAge Kakao 8.0.3.12 r558734",
                sha256(options.game11),
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
        "phase": "native-quest-2258-urgent-message-v1-runtime",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": base_hash,
            },
            "game11_items": {
                "path": str(options.game11),
                "sha256": sha256(options.game11),
                "source_range": [source["start"], source["end"]],
                "rows": source["rows"],
                "loader": source["loader"],
                "item_id": ITEM_ID,
            },
            "visible_behavior_corroboration": {
                "authority": "corroboration_only",
                "url": "https://wiki.archerage.to/na-en/db/quests/2258",
            },
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "item_ids": [ITEM_ID],
            "accept_npc_ids": [3630],
            "report_npc_ids": [3611],
        },
        "native_chain": {
            "start_component": 9951,
            "supply_component": 9952,
            "supply_item_act": 1339,
            "progress_component": 9999,
            "item_gather_act": 935,
            "ready_component": 9953,
            "reward_component": 9954,
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
