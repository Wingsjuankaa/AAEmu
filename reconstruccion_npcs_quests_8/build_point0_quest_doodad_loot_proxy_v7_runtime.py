#!/usr/bin/env python3
"""Build the bounded doodad-loot tombstone proxy for quest 2264.

AA8 keeps the native quest objective that requires item 24967, but the item
is absent from the complete positive AA8 item catalogue.  The live client
also proves the Empty Ring Box interaction reaches the existing
DoodadFuncLootItem path.  This builder replaces the inherited, unauthorised
item descriptor with a minimal server-derived quest token.  It enables only
doodad loot, inventory, QuestActObjItemGather, persistence, and cleanup.
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
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-use-proxy-v6.sqlite3"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-doodad-loot-proxy-v7.sqlite3"
DEFAULT_MANIFEST = DOMAIN / "generated" / "point0-quest-doodad-loot-proxy-v7-runtime-manifest.json"

EXPECTED_BASE_SHA256 = "6C8797A8F133DEDC4E1247B737160E5EB4818BF19A841A351238EAEAC0091C15"
QUEST_DOSSIER_SHA256 = "B064F805C4E7219936CFBC83181CACBE564B7A8B7D175B40EF9B8DA27F64E876"
ITEM_DOSSIER_SHA256 = "B7A3E66CB4C662920A53F1ED494FFBE6B55F8EC50B716F81B5C806C4FBD6B1F9"
REWARD_ITEM_DOSSIER_SHA256 = "DB1CC839779E216B1F1C82E1A07116F9D523C869F0AFB74CA8949EA6773698AE"
REWARD_SKILL_DOSSIER_SHA256 = "9B642F94C1CCFA7ED46DC52CC06FD2D021A62EC1F003D6725C948E6A7D997438"
CROSSWALK_SHA256 = "38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709"

QUEST_ID = 2264
ITEM_ID = 24967
OBJECTIVE_DETAIL_ID = 1800
NATIVE_DOODAD_ID = 14310
INTERACTION_SKILL_ID = 17310
RUNTIME_LOOT_DETAIL_ID = 2482
PROVENANCE = "server_derived_accepted:quest2264_native_tombstone_doodad_loot_proxy:v1"
REWARD_ITEM_ID = 34004
REWARD_SKILL_ID = 35239
REWARD_PROVENANCE = "client_compact_8+AA8_native_skill35239_full_closure+quest2264_runtime_audit:v1"

# This is deliberately not a recovered native item row.  Every capability
# outside the proven quest-objective lifecycle is disabled.
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
    "category_id": 64,
    "char_gender_id": 0,
    "contribution_point_price": 0,
    "craft_id": 0,
    "description": "Quest objective token for Sloane's Secret.",
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
    "name": "Sloane's Will",
    "notify_ui": 0,
    "one_time_sale": 0,
    "over_icon_id": 0,
    "pickup_limit": 1,
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


def one(connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise RuntimeError(f"required row missing: {sql} {parameters}")
    return tuple(row)


def direct_doodad_loot_gaps(connection: sqlite3.Connection) -> dict[str, int]:
    query = """
        WITH objectives AS (
            SELECT DISTINCT qc.quest_context_id AS quest_id, g.item_id
            FROM quest_components qc
            JOIN quest_acts a
              ON a.quest_component_id=qc.id
             AND a.act_detail_type='QuestActObjItemGather'
            JOIN quest_act_obj_item_gathers g ON g.id=a.act_detail_id
        ), doodad_loot AS (
            SELECT DISTINCT item_id FROM doodad_func_loot_items
        ), gaps AS (
            SELECT o.quest_id,o.item_id
            FROM objectives o
            JOIN doodad_loot d ON d.item_id=o.item_id
            LEFT JOIN items i ON i.id=o.item_id
            LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=o.item_id
            WHERE i.id IS NULL OR COALESCE(c.coverage,'')!='complete'
        )
        SELECT COUNT(*),COUNT(DISTINCT quest_id),COUNT(DISTINCT item_id) FROM gaps
    """
    relations, quests, items = one(connection, query)
    return {"relations": relations, "quests": quests, "items": items}


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks: dict[str, Any] = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "quest": one(
            connection,
            "SELECT category_id,chapter_idx,quest_idx,race,level,zone_id "
            "FROM quest_contexts WHERE id=?",
            (QUEST_ID,),
        ),
        "components": connection.execute(
            "SELECT id,component_kind_id FROM quest_components "
            "WHERE quest_context_id=? ORDER BY id",
            (QUEST_ID,),
        ).fetchall(),
        "objective": one(
            connection,
            "SELECT id,item_id,count,cleanup,destroy_when_drop,drop_when_destroy,"
            "highlight_doodad_id,item_grade_id,use_grade,quest_act_obj_alias_id,use_alias "
            "FROM quest_act_obj_item_gathers WHERE id=?",
            (OBJECTIVE_DETAIL_ID,),
        ),
        "objective_link": one(
            connection,
            "SELECT a.id,a.quest_component_id,qc.quest_context_id "
            "FROM quest_acts a JOIN quest_components qc ON qc.id=a.quest_component_id "
            "WHERE a.act_detail_type='QuestActObjItemGather' AND a.act_detail_id=?",
            (OBJECTIVE_DETAIL_ID,),
        ),
        "reward": one(
            connection,
            "SELECT e.exp,i.item_id,i.count FROM quest_act_supply_exps e, quest_act_supply_items i "
            "WHERE e.id=3936 AND i.id=8884",
        ),
        "reward_coverage": one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies "
            "FROM aaemu_item_definition_coverage WHERE item_id=34004",
        ),
        "reward_item": one(
            connection,
            "SELECT id,impl_id,category_id,max_stack_size,use_skill_id,buff_id,craft_id "
            "FROM items WHERE id=?",
            (REWARD_ITEM_ID,),
        ),
        "reward_skill_effects": connection.execute(
            "SELECT se.id,se.effect_id,e.actual_type,e.actual_id "
            "FROM skill_effects se JOIN effects e ON e.id=se.effect_id "
            "WHERE se.skill_id=? ORDER BY se.id",
            (REWARD_SKILL_ID,),
        ).fetchall(),
        "reward_buff_effects": connection.execute(
            "SELECT id,buff_id,chance,stack FROM buff_effects "
            "WHERE id IN (21541,21580,21581,21582,21583,21584,21585,21586,21587,21588) "
            "ORDER BY id"
        ).fetchall(),
        "reward_buffs": one(
            connection,
            "SELECT COUNT(*),MIN(duration),MAX(duration) FROM buffs "
            "WHERE id IN (20629,20630,20631,20632,20633,20634,20635,20636,20637,20638)",
        ),
        "interaction_skill": one(
            connection,
            "SELECT id,casting_time,min_range,max_range,target_type_id,target_selection_id,"
            "start_anim_id,fire_anim_id FROM skills WHERE id=?",
            (INTERACTION_SKILL_ID,),
        ),
        "doodad_loot": one(
            connection,
            "SELECT id,item_id,count_min,count_max,percent,remain_time,group_id "
            "FROM doodad_func_loot_items WHERE id=?",
            (RUNTIME_LOOT_DETAIL_ID,),
        ),
        "doodad_func": one(
            connection,
            "SELECT id,actual_func_type,actual_func_id,doodad_func_group_id,next_phase "
            "FROM doodad_funcs WHERE actual_func_type='DoodadFuncLootItem' AND actual_func_id=?",
            (RUNTIME_LOOT_DETAIL_ID,),
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
        "proxy": one(
            connection,
            "SELECT quest_id,objective_detail_id,native_doodad_id,interaction_skill_id,"
            "runtime_loot_detail_id,authority,state "
            "FROM aaemu_quest_doodad_loot_tombstone_proxies WHERE item_id=?",
            (ITEM_ID,),
        ),
        "open_paper_rows": one(
            connection, "SELECT COUNT(*) FROM item_open_papers WHERE item_id=?", (ITEM_ID,)
        )[0],
        "prior_loot_proxy": one(
            connection,
            "SELECT coverage,provenance FROM aaemu_item_definition_coverage WHERE item_id=24126",
        ),
        "prior_use_proxy": one(
            connection,
            "SELECT coverage,provenance FROM aaemu_item_definition_coverage WHERE item_id=16293",
        ),
        "gaps_after": direct_doodad_loot_gaps(connection),
    }
    expected: dict[str, Any] = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "quest": (3, 2, 9, 1, 8, 9),
        "components": [(9981, 2), (9983, 4), (9985, 6), (9986, 8)],
        "objective": (1800, ITEM_ID, 1, 1, 1, 1, NATIVE_DOODAD_ID, 1, 0, 1522, 1),
        "objective_link": (23227, 9983, QUEST_ID),
        "reward": (5400, 34004, 5),
        "reward_coverage": ("generic", "complete", ""),
        "reward_item": (REWARD_ITEM_ID, 0, 13, 1000, REWARD_SKILL_ID, 0, 0),
        "reward_skill_effects": [
            (47925, 60645, "BuffEffect", 21541),
            (47975, 60743, "BuffEffect", 21580),
            (47976, 60744, "BuffEffect", 21581),
            (47977, 60745, "BuffEffect", 21582),
            (47978, 60746, "BuffEffect", 21583),
            (47979, 60747, "BuffEffect", 21584),
            (47980, 60748, "BuffEffect", 21585),
            (47981, 60749, "BuffEffect", 21586),
            (47982, 60750, "BuffEffect", 21587),
            (47983, 60751, "BuffEffect", 21588),
        ],
        "reward_buff_effects": [
            (21541, 20629, 100, 1),
            (21580, 20630, 100, 1),
            (21581, 20631, 100, 1),
            (21582, 20632, 100, 1),
            (21583, 20633, 100, 1),
            (21584, 20634, 100, 1),
            (21585, 20635, 100, 1),
            (21586, 20636, 100, 1),
            (21587, 20637, 100, 1),
            (21588, 20638, 100, 1),
        ],
        "reward_buffs": (10, 5000, 5000),
        "interaction_skill": (INTERACTION_SKILL_ID, 1000, 0.0, 4.0, 8, 2, 59, 48),
        "doodad_loot": (RUNTIME_LOOT_DETAIL_ID, ITEM_ID, 1, 1, 10000, 100000, 0),
        "doodad_func": (9948, "DoodadFuncLootItem", RUNTIME_LOOT_DETAIL_ID, 11012, 13898),
        "proxy_item": (ITEM_ID, 64, 0, 1, 2, 1, 0, 0, QUEST_ID, 0, 0, 0, -1, 1),
        "coverage": ("generic", "complete", "", PROVENANCE),
        "proxy": (
            QUEST_ID,
            OBJECTIVE_DETAIL_ID,
            NATIVE_DOODAD_ID,
            INTERACTION_SKILL_ID,
            RUNTIME_LOOT_DETAIL_ID,
            "server_derived",
            "active_bounded",
        ),
        "open_paper_rows": 0,
        "prior_loot_proxy": ("complete", "server_derived_accepted:quest2263_native_tombstone_proxy:v1"),
        "prior_use_proxy": ("complete", "server_derived_accepted:quest2261_native_tombstone_use_proxy:v1"),
        "gaps_after": {"relations": 745, "quests": 653, "items": 552},
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
        before = direct_doodad_loot_gaps(connection)
        if before != {"relations": 746, "quests": 654, "items": 553}:
            raise RuntimeError(f"direct doodad-loot gap census changed: {before}")
        legacy_item = one(
            connection,
            "SELECT category_id,impl_id,loot_quest_id,use_skill_id,max_stack_size "
            "FROM items WHERE id=?",
            (ITEM_ID,),
        )
        if legacy_item != (64, 23, QUEST_ID, 0, 100):
            raise RuntimeError(f"unexpected inherited item 24967 descriptor: {legacy_item}")
        reward_coverage_before = one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies,provenance "
            "FROM aaemu_item_definition_coverage WHERE item_id=?",
            (REWARD_ITEM_ID,),
        )
        if reward_coverage_before != (
            "generic",
            "phase_a_candidate",
            "phase_a_runtime_validation",
            "client_compact_8",
        ):
            raise RuntimeError(f"unexpected reward item 34004 coverage: {reward_coverage_before}")

        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        columns = [row[1] for row in connection.execute("PRAGMA table_info(items)")]
        if set(columns) != set(PROXY_ITEM):
            raise RuntimeError(
                "items schema differs from the bounded proxy contract: "
                f"missing={sorted(set(columns)-set(PROXY_ITEM))}, "
                f"extra={sorted(set(PROXY_ITEM)-set(columns))}"
            )
        connection.execute("DELETE FROM items WHERE id=?", (ITEM_ID,))
        connection.execute(
            f"INSERT INTO items ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            tuple(PROXY_ITEM[column] for column in columns),
        )
        # The inherited OpenPaper relation came from non-AA8 runtime data.
        # The native positive item row is absent, so reading is intentionally
        # excluded from this bounded quest repair.
        connection.execute("DELETE FROM item_open_papers WHERE item_id=?", (ITEM_ID,))
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) VALUES (?,?,?,?,?)",
            (ITEM_ID, "generic", "complete", "", PROVENANCE),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) VALUES (?,?,?,?,?)",
            (REWARD_ITEM_ID, "generic", "complete", "", REWARD_PROVENANCE),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_quest_doodad_loot_tombstone_proxies (
                item_id INTEGER PRIMARY KEY,
                quest_id INTEGER NOT NULL,
                objective_detail_id INTEGER NOT NULL,
                native_doodad_id INTEGER NOT NULL,
                interaction_skill_id INTEGER NOT NULL,
                runtime_loot_detail_id INTEGER NOT NULL,
                authority TEXT NOT NULL,
                state TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            )
            """
        )
        evidence = {
            "client_build": "ArcheAge Kakao 8.0.3.12 r558734",
            "native_relations": [
                "quest_contexts[2264]",
                "QuestActObjItemGather[1800]->item[24967]x1 cleanup=1",
                "QuestActObjItemGather[1800]->highlight_doodad[14310] alias=1522",
                "skill[17310] Empty Ring Box interaction, 1s cast, 0-4m",
            ],
            "server_observed": [
                "doodad interaction skill 17310 reached DoodadFuncLootItem[2482]",
                "DoodadFuncLootItem[2482]->item[24967]x1 at 100%",
                "ItemManager rejected item 24967 only because coverage was Unknown",
            ],
            "negative_evidence": "item:24967 absent from complete AA8 items catalogue; lifecycle=tombstone",
            "removed_unproven_runtime_capability": "item_open_papers[24967]",
            "wiki_corroboration": [
                "https://wiki.archerage.to/na-en/db/quests/2264",
                "https://wiki.archerage.to/na-en/db/items/24967",
            ],
            "not_enabled": ["item use", "open paper", "skill", "buff", "craft", "trade", "auction"],
        }
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_quest_doodad_loot_tombstone_proxies "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                ITEM_ID,
                QUEST_ID,
                OBJECTIVE_DETAIL_ID,
                NATIVE_DOODAD_ID,
                INTERACTION_SKILL_ID,
                RUNTIME_LOOT_DETAIL_ID,
                "server_derived",
                "active_bounded",
                json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            ),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "point0-quest-doodad-loot-tombstone-proxy-v7",
                "AA8 native quest objective + observed doodad loot + bounded server-derived item proxy",
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
        "phase": "point0-quest-doodad-loot-tombstone-proxy-v7",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "classification": {
            "quest_objective": "client_native",
            "item_row": "server_derived_accepted",
            "doodad_loot_binding": "server_observed_compatible",
        },
        "sources": {
            "base_runtime": {"path": str(options.base_runtime), "sha256": base_hash},
            "quest_dossier": {"id": QUEST_ID, "sha256": QUEST_DOSSIER_SHA256},
            "item_dossier": {
                "id": ITEM_ID,
                "sha256": ITEM_DOSSIER_SHA256,
                "native_lifecycle": "tombstone",
            },
            "reward_item_dossier": {
                "id": REWARD_ITEM_ID,
                "sha256": REWARD_ITEM_DOSSIER_SHA256,
                "native_lifecycle": "present",
            },
            "reward_skill_dossier": {
                "id": REWARD_SKILL_ID,
                "sha256": REWARD_SKILL_DOSSIER_SHA256,
                "forensic_readiness": "profile_complete",
            },
            "quest_item_crosswalk": {"sha256": CROSSWALK_SHA256},
            "wiki": {
                "authority": "corroboration_only",
                "quest": "https://wiki.archerage.to/na-en/db/quests/2264",
                "item": "https://wiki.archerage.to/na-en/db/items/24967",
            },
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "item_ids": [ITEM_ID, REWARD_ITEM_ID],
            "doodad_ids": [NATIVE_DOODAD_ID],
            "skill_ids": [INTERACTION_SKILL_ID, REWARD_SKILL_ID],
            "server_derived_item_rows": 1,
            "historical_3_0_rows": 0,
            "native_item_rows_claimed": 0,
            "native_reward_item_promotions": 1,
        },
        "safety": {
            "max_stack_size": 1,
            "bind_on_pickup": True,
            "sellable": False,
            "pickup_limit": 1,
            "cleanup_on_quest_completion": True,
            "enabled_capabilities": [
                "doodad_loot",
                "inventory",
                "quest_item_gather",
                "persistence",
                "cleanup",
            ],
            "disabled_capabilities": [
                "item_use",
                "open_paper",
                "skill",
                "buff",
                "craft",
                "trade",
                "auction",
            ],
        },
        "direct_doodad_loot_gap_census": {"before": before, "after": checks["gaps_after"]},
        "reward_item_audit": {
            "before": {
                "coverage": reward_coverage_before[1],
                "missing_dependencies": reward_coverage_before[2],
                "provenance": reward_coverage_before[3],
            },
            "after": {
                "coverage": "complete",
                "missing_dependencies": "",
                "provenance": REWARD_PROVENANCE,
            },
            "skill_effects": 10,
            "buff_effects": 10,
            "buffs": 10,
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
