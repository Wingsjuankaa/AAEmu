#!/usr/bin/env python3
"""Build the bounded quest-loot tombstone proxy for quest 2263.

AA8 still exposes the quest/objective/loot relations for item 24126, but the
complete client item catalogue classifies that item as a tombstone.  This
builder therefore does not claim to recover a native item row.  It installs a
minimal, dependency-free server proxy whose only gameplay contract is to let
the exact quest loot enter inventory, advance QuestActObjItemGather, persist,
and be removed by the native cleanup flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
CLIENT_ROOT = Path(r"D:\Proyectos\AAemu\client_kakao")
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-point0-moonrise-armor-persistence-v4.sqlite3"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-loot-proxy-v5.sqlite3"
DEFAULT_MANIFEST = DOMAIN / "generated" / "point0-quest-loot-proxy-v5-runtime-manifest.json"

EXPECTED_BASE_SHA256 = "84A2E6AF2B890A3FE066129F80F041DDE2FF6B071B151AD0D05E2FB509073E0F"
QUEST_DOSSIER_SHA256 = "9D918B408DDDCE7A427E5E64301EC6B39562A88D1328621B0865889CEC0BA519"
ITEM_DOSSIER_SHA256 = "EAA6EEAE0A6B4583E8C66D764F96CA9680DCF1403ACE98110C8F99FC3DBAF9C2"
GAME11_SHA256 = "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"

QUEST_ID = 2263
ITEM_ID = 24126
OBJECTIVE_DETAIL_ID = 2046
PROVENANCE = "server_derived_accepted:quest2263_native_tombstone_proxy:v1"

# Every behavior-bearing value is bounded by the surviving AA8 graph or by a
# conservative server safety rule.  No historical item row is copied.
PROXY_ITEM: dict[str, Any] = {
    "id": ITEM_ID,
    "actability_group_id": 0,
    "actability_requirement": 0,
    "auction_a_category_id": 0,
    "auction_b_category_id": 0,
    "auction_c_category_id": 0,
    "auction_charge": 0,
    "auction_charge_default": 0,
    "auction_only": 0,
    "auto_complete": 0,
    "auto_loot": 0,
    "auto_register_to_actionbar": 0,
    "bind_id": 2,
    "buff_id": 0,
    "cash_item": 0,
    "category_id": 18,
    "char_gender_id": 0,
    "contribution_point_price": 0,
    "craft_id": 0,
    "description": "Quest loot token for A Deadly Plot.",
    "disenchantable": 0,
    "exp_abs_lifetime": 0,
    "exp_date": 0,
    "exp_day_of_week_id": 0,
    "exp_day_of_week_min": 0,
    "exp_online_lifetime": 0,
    "expedition_level": 0,
    "fixed_grade": -1,
    "gradable": 0,
    "honor_price": 0,
    "icon_id": 0,
    "impl_id": 0,
    "ingameshop_main_category": 0,
    "ingameshop_sub_category": 0,
    "level": 1,
    "level_limit": 0,
    "level_requirement": 0,
    "limited_sale_count": 0,
    "living_point_price": 0,
    "loot_multi": 0,
    "loot_quest_id": QUEST_ID,
    "male_icon_id": 0,
    "max_enchant_scale_id": 0,
    "max_enchantable_grade": -1,
    "max_stack_size": 1,
    "name": "Bloodhands' Instructions",
    "notify_ui": 0,
    "one_time_sale": 0,
    "over_icon_id": 0,
    "pickup_limit": 0,
    "pickup_sound_id": 0,
    "price": 0,
    "proc_lifetime": 0,
    "proc_recharge_restrict_item_id": 0,
    "refund": 0,
    "sellable": 0,
    "side_effect": 0,
    "specialty_zone_id": 0,
    "uid": 0,
    "use_or_equipment_sound_id": 0,
    "use_skill_as_reagent": 0,
    "use_skill_lifetime": 0,
    "use_skill_recharge_restrict_item_id": 0,
    "use_skill_id": 0,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _one(connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise RuntimeError(f"required row missing: {sql} {parameters}")
    return tuple(row)


def census_gaps(connection: sqlite3.Connection) -> dict[str, int]:
    query = """
        WITH objectives AS (
            SELECT DISTINCT qc.quest_context_id AS quest_id, g.item_id
            FROM quest_components qc
            JOIN quest_acts a
              ON a.quest_component_id=qc.id
             AND a.act_detail_type='QuestActObjItemGather'
            JOIN quest_act_obj_item_gathers g ON g.id=a.act_detail_id
        ), dropped AS (
            SELECT DISTINCT item_id FROM loots
        ), gaps AS (
            SELECT o.quest_id,o.item_id
            FROM objectives o
            JOIN dropped d ON d.item_id=o.item_id
            LEFT JOIN items i ON i.id=o.item_id
            LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=o.item_id
            WHERE i.id IS NULL OR COALESCE(c.coverage,'')!='complete'
        )
        SELECT COUNT(*),COUNT(DISTINCT quest_id),COUNT(DISTINCT item_id) FROM gaps
    """
    rows, quests, items = _one(connection, query)
    return {"relations": rows, "quests": quests, "items": items}


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "quest": _one(
            connection,
            "SELECT category_id,chapter_idx,quest_idx,race,level,zone_id "
            "FROM quest_contexts WHERE id=?",
            (QUEST_ID,),
        ),
        "objective": _one(
            connection,
            "SELECT id,item_id,count,cleanup,destroy_when_drop,drop_when_destroy "
            "FROM quest_act_obj_item_gathers WHERE id=?",
            (OBJECTIVE_DETAIL_ID,),
        ),
        "objective_link": _one(
            connection,
            "SELECT a.id,a.quest_component_id,qc.quest_context_id "
            "FROM quest_acts a JOIN quest_components qc ON qc.id=a.quest_component_id "
            "WHERE a.act_detail_type='QuestActObjItemGather' AND a.act_detail_id=?",
            (OBJECTIVE_DETAIL_ID,),
        ),
        "loot": _one(
            connection,
            "SELECT COUNT(*),COUNT(DISTINCT loot_pack_id),MIN(drop_rate),MAX(drop_rate),"
            "MIN(min_amount),MAX(max_amount) FROM loots WHERE item_id=?",
            (ITEM_ID,),
        ),
        "item": _one(
            connection,
            "SELECT id,category_id,impl_id,level,bind_id,max_stack_size,sellable,"
            "gradable,loot_quest_id,use_skill_id,buff_id,craft_id,fixed_grade "
            "FROM items WHERE id=?",
            (ITEM_ID,),
        ),
        "coverage": _one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies,provenance "
            "FROM aaemu_item_definition_coverage WHERE item_id=?",
            (ITEM_ID,),
        ),
        "proxy": _one(
            connection,
            "SELECT quest_id,objective_detail_id,objective_count,authority,state "
            "FROM aaemu_quest_loot_tombstone_proxies WHERE item_id=?",
            (ITEM_ID,),
        ),
        "gaps_after": census_gaps(connection),
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "quest": (3, 2, 5, 1, 7, 124),
        "objective": (2046, ITEM_ID, 1, 1, 0, 0),
        "objective_link": (24956, 9978, QUEST_ID),
        "loot": (8, 8, 10000000.0, 10000000.0, 1, 1),
        "item": (ITEM_ID, 18, 0, 1, 2, 1, 0, 0, QUEST_ID, 0, 0, 0, -1),
        "coverage": ("generic", "complete", "", PROVENANCE),
        "proxy": (QUEST_ID, OBJECTIVE_DETAIL_ID, 1, "server_derived", "active_bounded"),
        "gaps_after": {"relations": 742, "quests": 589, "items": 531},
    }
    failures = {
        key: {"expected": expected[key], "actual": value}
        for key, value in checks.items()
        if value != expected[key]
    }
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

    base_hash = sha256(options.base_runtime)
    if base_hash != EXPECTED_BASE_SHA256:
        raise RuntimeError(f"base runtime differs: expected {EXPECTED_BASE_SHA256}, got {base_hash}")

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        before = census_gaps(connection)
        if before != {"relations": 743, "quests": 590, "items": 532}:
            raise RuntimeError(f"quest-loot gap census changed: {before}")
        if connection.execute("SELECT COUNT(*) FROM items WHERE id=?", (ITEM_ID,)).fetchone()[0] != 0:
            raise RuntimeError("base runtime unexpectedly already contains item 24126")

        connection.execute("BEGIN IMMEDIATE")
        columns = [row[1] for row in connection.execute("PRAGMA table_info(items)")]
        if set(columns) != set(PROXY_ITEM):
            raise RuntimeError(
                "items schema differs from the bounded proxy contract: "
                f"missing={sorted(set(columns)-set(PROXY_ITEM))}, extra={sorted(set(PROXY_ITEM)-set(columns))}"
            )
        connection.execute(
            f"INSERT INTO items ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            tuple(PROXY_ITEM[column] for column in columns),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) VALUES (?,?,?,?,?)",
            (ITEM_ID, "generic", "complete", "", PROVENANCE),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_quest_loot_tombstone_proxies (
                item_id INTEGER PRIMARY KEY,
                quest_id INTEGER NOT NULL,
                objective_detail_id INTEGER NOT NULL,
                objective_count INTEGER NOT NULL,
                authority TEXT NOT NULL,
                state TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            )
            """
        )
        evidence = {
            "client_build": "ArcheAge Kakao 8.0.3.12 r558734",
            "native_relations": [
                "quest_contexts[2263]",
                "QuestActObjItemGather[2046]->item[24126]x1 cleanup=1",
                "loots[item_id=24126] eight packs at 100%",
            ],
            "negative_evidence": "item:24126 absent from complete AA8 items catalogue; lifecycle=tombstone",
            "observed": "AA8 client displayed item 24126 in Bloodhand Duelist loot; server rejected inventory transfer",
            "wiki_corroboration": [
                "https://wiki.archerage.to/na-en/db/quests/2263",
                "https://wiki.archerage.to/na-en/db/items/24126",
            ],
            "not_enabled": ["item use", "open paper", "skill", "buff", "craft", "trade", "auction"],
        }
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_quest_loot_tombstone_proxies VALUES (?,?,?,?,?,?,?)",
            (ITEM_ID, QUEST_ID, OBJECTIVE_DETAIL_ID, 1, "server_derived", "active_bounded", json.dumps(evidence, sort_keys=True)),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "point0-quest-loot-tombstone-proxy-v5",
                "AA8 native relations + bounded server-derived proxy",
                ITEM_DOSSIER_SHA256,
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
        "phase": "point0-quest-loot-tombstone-proxy-v5",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "classification": "server_derived_accepted",
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": base_hash},
            "game11": {"sha256": GAME11_SHA256},
            "quest_dossier": {"id": QUEST_ID, "sha256": QUEST_DOSSIER_SHA256},
            "item_dossier": {
                "id": ITEM_ID,
                "sha256": ITEM_DOSSIER_SHA256,
                "native_lifecycle": "tombstone",
            },
            "wiki": {
                "authority": "corroboration_only",
                "quest": "https://wiki.archerage.to/na-en/db/quests/2263",
                "item": "https://wiki.archerage.to/na-en/db/items/24126",
            },
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "item_ids": [ITEM_ID],
            "server_derived_rows": 1,
            "historical_3_0_rows": 0,
            "native_item_rows_claimed": 0,
        },
        "safety": {
            "max_stack_size": 1,
            "bind_on_pickup": True,
            "sellable": False,
            "dependency_free_generic": True,
            "cleanup_on_quest_completion": True,
            "enabled_capabilities": ["loot", "inventory", "quest_item_gather", "persistence", "cleanup"],
            "disabled_capabilities": ["use", "open_paper", "skill", "buff", "craft", "trade", "auction"],
        },
        "gap_census": {
            "before": {"relations": 743, "quests": 590, "items": 532},
            "after": checks["gaps_after"],
        },
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
    }
    options.manifest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
