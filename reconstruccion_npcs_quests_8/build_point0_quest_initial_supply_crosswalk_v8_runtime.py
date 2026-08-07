#!/usr/bin/env python3
"""Build the bounded crosswalk-backed initial SupplyItem closure for quest 2265.

The AA8 quest graph proves that quest 2265 supplies item 21604, but the
positive AA8 item catalogue retains only a tombstone.  The completed quest ↔
item crosswalk and the matching-version wiki corroborate the exact visible
identity and role.  Every shared field of the inherited dependency-free 3.0
row is exact; the nine AA8-only runtime columns are zero-padded.  This phase
therefore promotes that one existing row as explicitly corroborated legacy
materialization.

The selection predicate is transversal: native fixed initial SupplyItem,
crosswalk role/count match, tombstone closure, existing generic quest-item row,
no skill/buff/craft dependencies, not sellable, and incomplete runtime
coverage.  Against the current runtime it selects exactly quest 2265/item
21604; all other incomplete grants remain fail-closed.
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
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-point0-merchant-deven-v1.sqlite3"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-point0-quest-initial-supply-crosswalk-v8.sqlite3"
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "point0-quest-initial-supply-crosswalk-v8-runtime-manifest.json"
)
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\quest-item-crosswalk-v1.sqlite3"
)
DEFAULT_LEGACY = (
    ROOT
    / "assets"
    / "compact-3.0.3.0"
    / "3030.14082023"
    / "win10-x64"
    / "AAEmu.Game"
    / "Data"
    / "compact.sqlite3"
)

EXPECTED_BASE_SHA256 = "1625ABD2DA6E6350A0F64B6ADAA90FF61CCD93FE32F480DB3DB282640B998E66"
EXPECTED_CROSSWALK_SHA256 = "38E5CE75C90B0E64367A69E182E301B844E0904628CA726442F2D08A8DD34709"
EXPECTED_LEGACY_SHA256 = "9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397"

QUEST_DOSSIER_SHA256 = "A9EAEB052DDB873177E4A92FA42CB5D78B5C8105360AF54013C9FAB8844327E5"
ITEM_DOSSIER_SHA256 = "D36B4E5E61B810DC658CB0C619BC911A303A2A9B134E2F3B3697ED0C08ECB8DA"
REWARD_ITEM_DOSSIER_SHA256 = "FDAE093E16A217794C83A195F5B2DF44BF554DD2035717726948403A94784D76"
REWARD_SKILL_DOSSIER_SHA256 = "F22E688FAFD28818BBAFEA8321C406B97162B0BE3CF10C98BD854E117583F217"

QUEST_ID = 2265
ITEM_ID = 21604
REWARD_ITEM_ID = 34000
REWARD_SKILL_ID = 35238
ITEM_PROVENANCE = "legacy_3_0_corroborated:AA8_quest2265_crosswalk_match:v1"
REWARD_PROVENANCE = (
    "client_compact_8+AA8_native_skill35238_full_closure+quest2265_runtime_audit:v1"
)

SAFE_CANDIDATE_SQL = """
    SELECT DISTINCT
        g.quest_id,g.component_id,g.quest_act_id,g.act_detail_id,g.item_id,
        g.count,g.cleanup,g.destroy_when_drop,g.drop_when_destroy,
        g.show_action_bar,g.try_equip,qc.comparison_key,
        ic.closure_state,i.category_id,i.impl_id,i.level,i.bind_id,
        i.max_stack_size,i.sellable,i.loot_quest_id,i.use_skill_id,
        i.buff_id,i.craft_id
    FROM crosswalk.quest_item_grants g
    JOIN crosswalk.item_closure ic ON ic.item_id=g.item_id
    JOIN crosswalk.quest_item_comparisons qc
      ON qc.grant_key=g.grant_key
     AND qc.overall_state='match'
     AND qc.role_comparison_state='match'
     AND qc.count_comparison_state='match'
    JOIN main.items i ON i.id=g.item_id
    LEFT JOIN main.aaemu_item_definition_coverage cov ON cov.item_id=g.item_id
    WHERE g.grant_phase='initial_supply'
      AND g.selection_mode='fixed'
      AND g.act_detail_type='QuestActSupplyItem'
      AND g.native_state='confirmed'
      AND ic.closure_state='tombstone'
      AND i.category_id=64
      AND i.impl_id=0
      AND i.use_skill_id=0
      AND i.buff_id=0
      AND i.craft_id=0
      AND i.sellable=0
      AND COALESCE(cov.coverage,'Unknown')!='complete'
    ORDER BY g.quest_id,g.item_id
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def one(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> tuple[Any, ...]:
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise RuntimeError(f"required row missing: {sql} {parameters}")
    return tuple(row)


def initial_supply_gaps(connection: sqlite3.Connection) -> dict[str, int]:
    relations, quests, items = one(
        connection,
        """
        SELECT COUNT(*),COUNT(DISTINCT g.quest_id),COUNT(DISTINCT g.item_id)
        FROM crosswalk.quest_item_grants g
        LEFT JOIN main.items i ON i.id=g.item_id
        LEFT JOIN main.aaemu_item_definition_coverage cov ON cov.item_id=g.item_id
        WHERE g.grant_phase='initial_supply'
          AND g.native_state='confirmed'
          AND (i.id IS NULL OR COALESCE(cov.coverage,'')!='complete')
        """,
    )
    return {"relations": relations, "quests": quests, "items": items}


def candidate_rows(connection: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in connection.execute(SAFE_CANDIDATE_SQL).fetchall()]


def reward_closure(connection: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return [
        tuple(row)
        for row in connection.execute(
            """
            SELECT se.id,se.effect_id,e.actual_type,e.actual_id,
                   be.buff_id,be.chance,be.stack,b.duration
            FROM skill_effects se
            JOIN effects e ON e.id=se.effect_id
            JOIN buff_effects be ON be.id=e.actual_id
            JOIN buffs b ON b.id=be.buff_id
            WHERE se.skill_id=?
            ORDER BY se.id
            """,
            (REWARD_SKILL_ID,),
        ).fetchall()
    ]


EXPECTED_CANDIDATE = (
    2265,
    9988,
    14179,
    1336,
    21604,
    1,
    1,
    1,
    1,
    1,
    0,
    "quest_item_comparison:b734129ee9a70e13c907e0814c64fe9d",
    "tombstone",
    64,
    0,
    1,
    2,
    1,
    0,
    2265,
    0,
    0,
    0,
)

EXPECTED_REWARD_CLOSURE = [
    (47924, 60644, "BuffEffect", 21540, 20619, 100, 1, 5000),
    (47966, 60724, "BuffEffect", 21571, 20620, 100, 1, 5000),
    (47967, 60725, "BuffEffect", 21572, 20621, 100, 1, 5000),
    (47968, 60726, "BuffEffect", 21573, 20622, 100, 1, 5000),
    (47969, 60727, "BuffEffect", 21574, 20623, 100, 1, 5000),
    (47970, 60728, "BuffEffect", 21575, 20624, 100, 1, 5000),
    (47971, 60729, "BuffEffect", 21576, 20625, 100, 1, 5000),
    (47972, 60730, "BuffEffect", 21577, 20626, 100, 1, 5000),
    (47973, 60731, "BuffEffect", 21578, 20627, 100, 1, 5000),
    (47974, 60732, "BuffEffect", 21579, 20628, 100, 1, 5000),
]


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
        "initial_supply": one(
            connection,
            "SELECT id,item_id,count,cleanup,destroy_when_drop,drop_when_destroy,"
            "show_action_bar,try_equip FROM quest_act_supply_items WHERE id=1336",
        ),
        "rewards": (
            one(connection, "SELECT exp FROM quest_act_supply_exps WHERE id=3937")[0],
            *one(
                connection,
                "SELECT item_id,count FROM quest_act_supply_items WHERE id=4819",
            ),
            *one(
                connection,
                "SELECT item_id,count FROM quest_act_supply_items WHERE id=8885",
            ),
        ),
        "item": one(
            connection,
            "SELECT id,category_id,impl_id,level,bind_id,max_stack_size,sellable,"
            "gradable,loot_quest_id,use_skill_id,buff_id,craft_id,fixed_grade,pickup_limit "
            "FROM items WHERE id=?",
            (ITEM_ID,),
        ),
        "item_coverage": one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies,provenance "
            "FROM aaemu_item_definition_coverage WHERE item_id=?",
            (ITEM_ID,),
        ),
        "proxy": one(
            connection,
            "SELECT quest_id,component_id,quest_act_id,act_detail_id,item_id,"
            "authority,state FROM aaemu_quest_initial_supply_crosswalk_materializations "
            "WHERE item_id=?",
            (ITEM_ID,),
        ),
        "reward_item": one(
            connection,
            "SELECT id,impl_id,category_id,max_stack_size,use_skill_id,buff_id,craft_id "
            "FROM items WHERE id=?",
            (REWARD_ITEM_ID,),
        ),
        "reward_coverage": one(
            connection,
            "SELECT concrete_type,coverage,missing_dependencies,provenance "
            "FROM aaemu_item_definition_coverage WHERE item_id=?",
            (REWARD_ITEM_ID,),
        ),
        "reward_skill": one(
            connection,
            "SELECT id,casting_time,cooldown_time,min_range,max_range,target_type_id,"
            "target_selection_id,start_anim_id,fire_anim_id FROM skills WHERE id=?",
            (REWARD_SKILL_ID,),
        ),
        "reward_closure": reward_closure(connection),
        "gilda_coverage": one(
            connection,
            "SELECT coverage FROM aaemu_item_definition_coverage WHERE item_id=23633",
        )[0],
        "merchant_goods": one(
            connection,
            "SELECT COUNT(*) FROM merchant_goods WHERE merchant_pack_id=914119",
        )[0],
        "prior_quest_proxy": one(
            connection,
            "SELECT coverage FROM aaemu_item_definition_coverage WHERE item_id=24967",
        )[0],
        "safe_candidates_after": candidate_rows(connection),
        "initial_supply_gaps_after": initial_supply_gaps(connection),
    }
    expected: dict[str, Any] = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "quest": (3, 2, 10, 1, 9, 9),
        "components": [(9987, 2), (9988, 3), (9989, 6), (9991, 8)],
        "initial_supply": (1336, 21604, 1, 1, 1, 1, 1, 0),
        "rewards": (6700, 23633, 1, 34000, 5),
        "item": (21604, 64, 0, 1, 2, 1, 0, 0, 2265, 0, 0, 0, -1, 0),
        "item_coverage": ("generic", "complete", "", ITEM_PROVENANCE),
        "proxy": (
            2265,
            9988,
            14179,
            1336,
            21604,
            "legacy_3_0_corroborated",
            "active_bounded",
        ),
        "reward_item": (34000, 0, 13, 1000, 35238, 0, 0),
        "reward_coverage": ("generic", "complete", "", REWARD_PROVENANCE),
        "reward_skill": (35238, 3000, 10000, 0.0, 0.0, 0, 1, 78, 48),
        "reward_closure": EXPECTED_REWARD_CLOSURE,
        "gilda_coverage": "complete",
        "merchant_goods": 37,
        "prior_quest_proxy": "complete",
        "safe_candidates_after": [],
        "initial_supply_gaps_after": {"relations": 1173, "quests": 1082, "items": 1110},
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
    source_hashes = {
        "base_runtime": sha256(options.base_runtime),
        "crosswalk": sha256(options.crosswalk),
        "legacy_compact": sha256(options.legacy_compact),
    }
    expected_hashes = {
        "base_runtime": EXPECTED_BASE_SHA256,
        "crosswalk": EXPECTED_CROSSWALK_SHA256,
        "legacy_compact": EXPECTED_LEGACY_SHA256,
    }
    if source_hashes != expected_hashes:
        raise RuntimeError(
            f"source identity differs: expected {expected_hashes}, got {source_hashes}"
        )

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    try:
        connection.execute("ATTACH DATABASE ? AS crosswalk", (str(options.crosswalk),))
        connection.execute("ATTACH DATABASE ? AS legacy", (str(options.legacy_compact),))

        gaps_before = initial_supply_gaps(connection)
        if gaps_before != {"relations": 1174, "quests": 1083, "items": 1111}:
            raise RuntimeError(f"initial SupplyItem gap census changed: {gaps_before}")
        candidates_before = candidate_rows(connection)
        if candidates_before != [EXPECTED_CANDIDATE]:
            raise RuntimeError(
                "safe crosswalk candidate set changed: "
                f"expected {[EXPECTED_CANDIDATE]}, got {candidates_before}"
            )

        columns = [row[1] for row in connection.execute("PRAGMA main.table_info(items)")]
        legacy_columns = [
            row[1] for row in connection.execute("PRAGMA legacy.table_info(items)")
        ]
        common_columns = [column for column in columns if column in legacy_columns]
        runtime_item = one(
            connection,
            f"SELECT {','.join(common_columns)} FROM main.items WHERE id=?",
            (ITEM_ID,),
        )
        legacy_item = one(
            connection,
            f"SELECT {','.join(common_columns)} FROM legacy.items WHERE id=?",
            (ITEM_ID,),
        )
        if runtime_item != legacy_item:
            raise RuntimeError("runtime item 21604 differs in a shared legacy field")
        runtime_only_columns = sorted(set(columns) - set(legacy_columns))
        schema_padding_values = one(
            connection,
            f"SELECT {','.join(runtime_only_columns)} FROM main.items WHERE id=?",
            (ITEM_ID,),
        )
        schema_padding = dict(zip(runtime_only_columns, schema_padding_values))
        expected_schema_padding = {
            "auction_only": 0,
            "auto_complete": 0,
            "auto_loot": 0,
            "exp_day_of_week_id": 0,
            "exp_day_of_week_min": 0,
            "max_enchant_scale_id": 0,
            "proc_lifetime": 0,
            "proc_recharge_restrict_item_id": 0,
            "uid": 0,
        }
        if schema_padding != expected_schema_padding:
            raise RuntimeError(
                "AA8 runtime-only schema padding for item 21604 differs: "
                f"{schema_padding}"
            )

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
            raise RuntimeError(
                f"unexpected reward item 34000 coverage: {reward_coverage_before}"
            )
        if reward_closure(connection) != EXPECTED_REWARD_CLOSURE:
            raise RuntimeError("native reward skill 35238 closure differs")

        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            (ITEM_ID, "generic", "complete", "", ITEM_PROVENANCE),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            (REWARD_ITEM_ID, "generic", "complete", "", REWARD_PROVENANCE),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS aaemu_quest_initial_supply_crosswalk_materializations (
                item_id INTEGER PRIMARY KEY,
                quest_id INTEGER NOT NULL,
                component_id INTEGER NOT NULL,
                quest_act_id INTEGER NOT NULL,
                act_detail_id INTEGER NOT NULL,
                comparison_key TEXT NOT NULL,
                authority TEXT NOT NULL,
                state TEXT NOT NULL,
                evidence_json TEXT NOT NULL
            )
            """
        )
        evidence = {
            "client_build": "ArcheAge Kakao 8.0.3.12 r558734",
            "native_grant": {
                "quest_id": 2265,
                "component_id": 9988,
                "quest_act_id": 14179,
                "act_detail_id": 1336,
                "item_id": 21604,
                "count": 1,
                "cleanup": 1,
                "destroy_when_drop": 1,
                "drop_when_destroy": 1,
                "show_action_bar": 1,
            },
            "crosswalk": {
                "comparison_key": EXPECTED_CANDIDATE[11],
                "overall_state": "match",
                "role": "match",
                "count": "match",
            },
            "legacy_row": {
                "source_sha256": source_hashes["legacy_compact"],
                "all_shared_fields_exact": True,
                "field_overrides": 0,
                "aa8_runtime_only_zero_padding": schema_padding,
            },
            "wiki_corroboration": [
                "https://wiki.archerage.to/na-en/db/quests/2265",
                "https://wiki.archerage.to/na-en/db/items/21604",
            ],
            "not_enabled": [
                "item use",
                "skill",
                "buff",
                "craft",
                "equipment",
                "sale",
                "trade",
                "auction",
            ],
        }
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_quest_initial_supply_crosswalk_materializations "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                ITEM_ID,
                QUEST_ID,
                9988,
                14179,
                1336,
                EXPECTED_CANDIDATE[11],
                "legacy_3_0_corroborated",
                "active_bounded",
                json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            ),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "point0-quest-initial-supply-crosswalk-v8",
                "AA8 native SupplyItem + crosswalk match + corroborated minimal legacy row",
                EXPECTED_CROSSWALK_SHA256,
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
        "phase": "point0-quest-initial-supply-crosswalk-v8",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "classification": {
            "quest_grant": "client_native",
            "item_row": "legacy_3_0_corroborated",
            "selection_policy": "crosswalk_transversal_bounded",
            "reward_item": "client_native_full_closure",
        },
        "sources": {
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": source_hashes["base_runtime"],
            },
            "crosswalk": {
                "path": str(options.crosswalk),
                "sha256": source_hashes["crosswalk"],
            },
            "legacy_compact": {
                "path": str(options.legacy_compact),
                "sha256": source_hashes["legacy_compact"],
            },
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
                "forensic_readiness": "bounded_candidate_reverse_graph_only",
            },
            "reward_skill_dossier": {
                "id": REWARD_SKILL_ID,
                "sha256": REWARD_SKILL_DOSSIER_SHA256,
                "forensic_readiness": "profile_complete",
            },
            "wiki": {
                "authority": "corroboration_only",
                "quest": "https://wiki.archerage.to/na-en/db/quests/2265",
                "item": "https://wiki.archerage.to/na-en/db/items/21604",
            },
        },
        "transversal_policy": {
            "native_initial_supply": True,
            "selection_mode": "fixed",
            "crosswalk_overall_state": "match",
            "crosswalk_role_state": "match",
            "crosswalk_count_state": "match",
            "native_item_lifecycle": "tombstone",
            "runtime_shape": {
                "category_id": 64,
                "impl_id": 0,
                "sellable": 0,
                "use_skill_id": 0,
                "buff_id": 0,
                "craft_id": 0,
            },
            "selected_before": 1,
            "selected_after": 0,
            "selected_quest_items": [{"quest_id": QUEST_ID, "item_id": ITEM_ID}],
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "item_ids": [ITEM_ID, 23633, REWARD_ITEM_ID],
            "skill_ids": [REWARD_SKILL_ID],
            "legacy_rows_promoted": 1,
            "legacy_rows_imported": 0,
            "legacy_field_overrides": 0,
            "legacy_schema_padding_fields": len(schema_padding),
            "native_reward_item_promotions": 1,
        },
        "safety": {
            "enabled_capabilities": [
                "initial_supply",
                "inventory",
                "quest_ready_transition",
                "persistence",
                "cleanup",
            ],
            "disabled_item_capabilities": [
                "item_use",
                "skill",
                "buff",
                "craft",
                "equipment",
                "sale",
                "trade",
                "auction",
            ],
        },
        "initial_supply_gap_census": {
            "before": gaps_before,
            "after": checks["initial_supply_gaps_after"],
        },
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
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--legacy-compact", type=Path, default=DEFAULT_LEGACY)
    options = parser.parse_args()
    print(json.dumps(build(options), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
