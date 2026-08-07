#!/usr/bin/env python3
"""Close quest 2261 and add its bounded AA8 tombstone use-item proxy.

The AA8 graph preserves the complete quest, objective, reward, skill and plot
relations, but item 16293 is a confirmed native tombstone.  The runtime also
lost four native quest-detail rows while composing earlier layers.  This
builder restores those exact client-native rows and adds one explicitly
server-derived item proxy limited to quest supply/use/cleanup.
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
CLIENT_ROOT = Path(r"D:\Proyectos\AAemu\client_kakao")
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-loot-proxy-v5.sqlite3"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-use-proxy-v6.sqlite3"
DEFAULT_MANIFEST = DOMAIN / "generated" / "point0-quest-use-proxy-v6-runtime-manifest.json"

EXPECTED_BASE_SHA256 = "76F1D8A82B1ECEA85FEECAA3A8A114F1BEA9001C6CB8F34D160CE3284FD8EE77"
QUEST_DOSSIER_SHA256 = "C4E6C4ECC66BBEAACC373B0EB8B2A0C097A42C0DA4C409E6C9BA075172335402"
ITEM_DOSSIER_SHA256 = "6D654E8BBDF652B4FC7E3C71E41FB1D9DD721C79203147A910CA0F254F10033F"
SKILL_DOSSIER_SHA256 = "B7CCCD433A254F258B053B61036A66550B680348B86166E8BCD343D2B85E3E16"
GAME11_SHA256 = "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"

QUEST_ID = 2261
ITEM_ID = 16293
SKILL_ID = 13886
PROVENANCE = "server_derived_accepted:quest2261_native_tombstone_use_proxy:v1"

NATIVE_QUEST_ROWS = {
    "objective": (598, "", 1, 0, -1, 0, ITEM_ID, 6578, 1),
    "alias": (6578, "피 묻은 손에게 최면의 지팡이 사용"),
    "reward_exp": (3933, 4500),
    "reward_item": (8881, 1, 5, 1, 1, 0, 18791, 1, 0),
    "reward_acts": (
        (64103, "QuestActSupplyExp", 3933, 9970),
        (65631, "QuestActSupplyItem", 8881, 9970),
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_v5_policy_template() -> dict[str, Any]:
    path = DOMAIN / "build_point0_quest_loot_proxy_v5_runtime.py"
    spec = importlib.util.spec_from_file_location("point0_quest_loot_proxy_v5", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import policy template {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    proxy = dict(module.PROXY_ITEM)
    proxy.update(
        {
            "id": ITEM_ID,
            "category_id": 64,
            "description": "Quest-use token for Truth Extraction.",
            "loot_quest_id": QUEST_ID,
            "max_stack_size": 1,
            "name": "Hypnotic Staff",
            "pickup_limit": 1,
            "use_skill_id": SKILL_ID,
        }
    )
    return proxy


def one(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> tuple[Any, ...]:
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise RuntimeError(f"required row missing: {sql} {parameters}")
    return tuple(row)


def rows(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in connection.execute(sql, parameters)]


def initial_supply_audit(connection: sqlite3.Connection) -> dict[str, int]:
    row = one(
        connection,
        """
        SELECT COUNT(*),COUNT(DISTINCT s.item_id),
               SUM(CASE WHEN COALESCE(c.coverage,'')!='complete' THEN 1 ELSE 0 END),
               COUNT(DISTINCT CASE WHEN COALESCE(c.coverage,'')!='complete' THEN s.item_id END)
        FROM quest_components qc
        JOIN quest_acts a ON a.quest_component_id=qc.id
                         AND a.act_detail_type='QuestActSupplyItem'
        JOIN quest_act_supply_items s ON s.id=a.act_detail_id
        LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=s.item_id
        WHERE qc.component_kind_id=3
        """,
    )
    return {
        "acts": int(row[0]),
        "distinct_items": int(row[1]),
        "incomplete_acts": int(row[2]),
        "incomplete_distinct_items": int(row[3]),
    }


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    event_ids = (3167, 3168, 3169, 3170, 3171, 3172, 3173, 3176)
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "quest": one(
            connection,
            "SELECT category_id,chapter_idx,quest_idx,race,level,zone_id "
            "FROM quest_contexts WHERE id=?",
            (QUEST_ID,),
        ),
        "components": rows(
            connection,
            "SELECT id,component_kind_id FROM quest_components "
            "WHERE quest_context_id=? ORDER BY id",
            (QUEST_ID,),
        ),
        "supply": one(
            connection,
            "SELECT id,item_id,count,grade_id,cleanup,destroy_when_drop,"
            "drop_when_destroy,show_action_bar,try_equip "
            "FROM quest_act_supply_items WHERE id=2273",
        ),
        "objective": one(
            connection,
            "SELECT id,cinema,count,drop_when_destroy,highlight_doodad_phase,"
            "highlight_doodad_id,item_id,quest_act_obj_alias_id,use_alias "
            "FROM quest_act_obj_item_uses WHERE id=598",
        ),
        "alias": one(
            connection,
            "SELECT id,name FROM quest_act_obj_aliases WHERE id=6578",
        ),
        "reward_acts": rows(
            connection,
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE id IN (64103,65631) ORDER BY id",
        ),
        "reward_exp": one(
            connection,
            "SELECT id,exp FROM quest_act_supply_exps WHERE id=3933",
        ),
        "reward_item": one(
            connection,
            "SELECT id,cleanup,count,destroy_when_drop,drop_when_destroy,grade_id,"
            "item_id,show_action_bar,try_equip FROM quest_act_supply_items WHERE id=8881",
        ),
        "reward_item_coverage": one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies "
            "FROM aaemu_item_definition_coverage WHERE item_id=18791",
        ),
        "proxy_item": one(
            connection,
            "SELECT id,category_id,impl_id,level,bind_id,max_stack_size,sellable,"
            "gradable,loot_quest_id,use_skill_id,buff_id,craft_id,fixed_grade,pickup_limit "
            "FROM items WHERE id=?",
            (ITEM_ID,),
        ),
        "coverage": one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies,provenance "
            "FROM aaemu_item_definition_coverage WHERE item_id=?",
            (ITEM_ID,),
        ),
        "proxy_audit": one(
            connection,
            "SELECT quest_id,skill_id,supply_detail_id,objective_detail_id,"
            "authority,state FROM aaemu_quest_use_tombstone_proxies WHERE item_id=?",
            (ITEM_ID,),
        ),
        "skill": one(
            connection,
            "SELECT id,plot_id,target_type_id,target_selection_id,target_unit_param,"
            "min_range,max_range,cooldown_time,ignore_global_cooldown "
            "FROM skills WHERE id=?",
            (SKILL_ID,),
        ),
        "plot": one(connection, "SELECT id,target_type_id FROM plots WHERE id=383"),
        "plot_events": rows(
            connection,
            f"SELECT id FROM plot_events WHERE id IN ({','.join('?' for _ in event_ids)}) "
            "AND plot_id=383 ORDER BY id",
            event_ids,
        ),
        "plot_effects": one(
            connection,
            f"SELECT COUNT(*),COUNT(DISTINCT actual_type) FROM plot_effects "
            f"WHERE event_id IN ({','.join('?' for _ in event_ids)})",
            event_ids,
        ),
        "special_effects": rows(
            connection,
            "SELECT id,special_effect_type_id FROM special_effects "
            "WHERE id IN (6880,6881,6882,6883,6884,6885,6886,6891) ORDER BY id",
        ),
        "buff_effects": rows(
            connection,
            "SELECT id,buff_id,chance,stack FROM buff_effects "
            "WHERE id IN (6728,6731) ORDER BY id",
        ),
        "bubble_effects": rows(
            connection,
            "SELECT id,kind_id FROM bubble_effects "
            "WHERE id IN (1845,1846,1847,1875) ORDER BY id",
        ),
        "initial_supply_audit": initial_supply_audit(connection),
        "item_row_count": one(
            connection, "SELECT COUNT(*) FROM items WHERE id=?", (ITEM_ID,)
        )[0],
        "prior_proxy_preserved": one(
            connection,
            "SELECT coverage,provenance FROM aaemu_item_definition_coverage WHERE item_id=24126",
        ),
    }
    expected: dict[str, Any] = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "quest": (3, 2, 6, 1, 7, 124),
        "components": [(9963, 2), (9965, 3), (9967, 4), (9969, 6), (9970, 8)],
        "supply": (2273, ITEM_ID, 1, 0, 1, 1, 1, 1, 0),
        "objective": NATIVE_QUEST_ROWS["objective"],
        "alias": NATIVE_QUEST_ROWS["alias"],
        "reward_acts": list(NATIVE_QUEST_ROWS["reward_acts"]),
        "reward_exp": NATIVE_QUEST_ROWS["reward_exp"],
        "reward_item": NATIVE_QUEST_ROWS["reward_item"],
        "reward_item_coverage": ("generic", "complete", ""),
        "proxy_item": (ITEM_ID, 64, 0, 1, 2, 1, 0, 0, QUEST_ID, SKILL_ID, 0, 0, -1, 1),
        "coverage": ("generic", "complete", "", PROVENANCE),
        "proxy_audit": (QUEST_ID, SKILL_ID, 2273, 598, "server_derived", "active_bounded"),
        "skill": (SKILL_ID, 383, 4, 2, 119, 0.0, 20.0, 10000, 1),
        "plot": (383, 4),
        "plot_events": [(value,) for value in event_ids],
        "plot_effects": (14, 3),
        "special_effects": [(6880, 36), (6881, 34), (6882, 38), (6883, 40), (6884, 59), (6885, 41), (6886, 61), (6891, 34)],
        "buff_effects": [(6728, 1648, 100, 1), (6731, 3862, 100, 1)],
        "bubble_effects": [(1845, 1), (1846, 1), (1847, 1), (1875, 1)],
        "initial_supply_audit": {"acts": 1003, "distinct_items": 964, "incomplete_acts": 998, "incomplete_distinct_items": 959},
        "item_row_count": 1,
        "prior_proxy_preserved": ("complete", "server_derived_accepted:quest2263_native_tombstone_proxy:v1"),
    }
    failures = {
        key: {"expected": expected[key], "actual": value}
        for key, value in checks.items()
        if value != expected[key]
    }
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def build(options: argparse.Namespace) -> dict[str, Any]:
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
        before = initial_supply_audit(connection)
        if before != {"acts": 1003, "distinct_items": 964, "incomplete_acts": 999, "incomplete_distinct_items": 960}:
            raise RuntimeError(f"initial supply audit changed: {before}")
        if connection.execute("SELECT COUNT(*) FROM items WHERE id=?", (ITEM_ID,)).fetchone()[0] != 0:
            raise RuntimeError("base runtime unexpectedly already contains item 16293")

        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")

        connection.execute(
            "INSERT OR REPLACE INTO quest_act_obj_aliases (id,name) VALUES (?,?)",
            NATIVE_QUEST_ROWS["alias"],
        )
        connection.execute(
            "INSERT OR REPLACE INTO quest_act_obj_item_uses "
            "(id,cinema,count,drop_when_destroy,highlight_doodad_phase,highlight_doodad_id,"
            "item_id,quest_act_obj_alias_id,use_alias) VALUES (?,?,?,?,?,?,?,?,?)",
            NATIVE_QUEST_ROWS["objective"],
        )
        connection.execute(
            "INSERT OR REPLACE INTO quest_act_supply_exps (id,exp) VALUES (?,?)",
            NATIVE_QUEST_ROWS["reward_exp"],
        )
        connection.execute(
            "INSERT OR REPLACE INTO quest_act_supply_items "
            "(id,cleanup,count,destroy_when_drop,drop_when_destroy,grade_id,item_id,show_action_bar,try_equip) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            NATIVE_QUEST_ROWS["reward_item"],
        )
        connection.executemany(
            "INSERT OR REPLACE INTO quest_acts "
            "(id,act_detail_type,act_detail_id,quest_component_id) VALUES (?,?,?,?)",
            NATIVE_QUEST_ROWS["reward_acts"],
        )

        proxy = load_v5_policy_template()
        columns = [row[1] for row in connection.execute("PRAGMA table_info(items)")]
        if set(columns) != set(proxy):
            raise RuntimeError(
                "items schema differs from bounded proxy contract: "
                f"missing={sorted(set(columns)-set(proxy))}, extra={sorted(set(proxy)-set(columns))}"
            )
        connection.execute(
            f"INSERT INTO items ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            tuple(proxy[column] for column in columns),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) VALUES (?,?,?,?,?)",
            (ITEM_ID, "generic", "complete", "", PROVENANCE),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_quest_use_tombstone_proxies (
                item_id INTEGER PRIMARY KEY,
                quest_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                supply_detail_id INTEGER NOT NULL,
                objective_detail_id INTEGER NOT NULL,
                authority TEXT NOT NULL,
                state TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            )
            """
        )
        evidence = {
            "client_build": "ArcheAge Kakao 8.0.3.12 r558734",
            "native_relations": [
                "QuestActSupplyItem[2273]->item[16293]x1 show_action_bar=1 cleanup=1",
                "QuestActObjItemUse[598]->item[16293]x1 alias=6578",
                "skill[13886]->plot[383], hostile target, 0-20m, 10s cooldown",
                "plot[383] complete: 8 events, 7 next events, 14 effects",
            ],
            "native_rows_restored": [
                "quest_act_obj_aliases[6578]",
                "quest_act_obj_item_uses[598] native alias/use_alias fields",
                "quest_act_supply_exps[3933]",
                "quest_act_supply_items[8881]",
                "quest_acts[64103,65631]",
            ],
            "negative_evidence": "item:16293 absent from complete AA8 items catalogue; lifecycle=tombstone",
            "wiki_corroboration": [
                "https://wiki.archerage.to/na-en/db/quests/2261",
                "https://wiki.archerage.to/na-en/db/items/16293",
                "https://wiki.archerage.to/na-en/db/skills/13886",
            ],
            "not_enabled": ["trade", "sell", "auction", "craft", "buff", "equipment"],
        }
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_quest_use_tombstone_proxies VALUES (?,?,?,?,?,?,?,?)",
            (ITEM_ID, QUEST_ID, SKILL_ID, 2273, 598, "server_derived", "active_bounded", json.dumps(evidence, ensure_ascii=False, sort_keys=True)),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "point0-quest-use-tombstone-proxy-v6",
                "AA8 native quest closure + bounded server-derived item proxy",
                QUEST_DOSSIER_SHA256,
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
        "phase": "point0-quest-use-tombstone-proxy-v6",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "classification": {
            "quest_rows": "client_native",
            "item_row": "server_derived_accepted",
        },
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": base_hash},
            "game11": {"sha256": GAME11_SHA256},
            "quest_dossier": {"id": QUEST_ID, "sha256": QUEST_DOSSIER_SHA256},
            "item_dossier": {"id": ITEM_ID, "sha256": ITEM_DOSSIER_SHA256, "native_lifecycle": "tombstone"},
            "skill_dossier": {"id": SKILL_ID, "sha256": SKILL_DOSSIER_SHA256},
            "wiki": {
                "authority": "corroboration_only",
                "quest": "https://wiki.archerage.to/na-en/db/quests/2261",
                "item": "https://wiki.archerage.to/na-en/db/items/16293",
                "skill": "https://wiki.archerage.to/na-en/db/skills/13886",
            },
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "item_ids": [ITEM_ID, 18791],
            "skill_ids": [SKILL_ID],
            "native_quest_rows_restored": 6,
            "server_derived_item_rows": 1,
            "historical_3_0_rows": 0,
            "native_item_rows_claimed": 0,
        },
        "safety": {
            "max_stack_size": 1,
            "bind_on_pickup": True,
            "sellable": False,
            "pickup_limit": 1,
            "cleanup_on_quest_completion": True,
            "enabled_capabilities": ["quest_supply", "inventory", "quest_actionbar", "skill_13886", "quest_item_use", "persistence", "cleanup"],
            "disabled_capabilities": ["trade", "sell", "auction", "craft", "buff", "equipment"],
        },
        "initial_supply_audit": {"before": before, "after": checks["initial_supply_audit"]},
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
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()
    print(json.dumps(build(options), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
