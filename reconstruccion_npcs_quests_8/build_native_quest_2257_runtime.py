#!/usr/bin/env python3
"""Build the AA8-native quest 2257 runtime (Nuian green arc V4).

The quest graph, doodad phases, skill relations, concrete effects, and quest
item are native Kakao 8.0 evidence. The single loot row is explicitly marked
server_derived because Kakao game11 does not carry server-owned loot tables;
its result is uniquely constrained by effect 4165, item.loot_quest_id=2257,
and the native QuestActObjItemGather requirement.
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


DOMAIN = Path(__file__).resolve().parent
DEFAULT_FORENSIC = (
    DOMAIN / "generated" / "native-quest-2256-client-doodad-v1-manifest.json"
)
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v3.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v4.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-quest-2257-warning-villagers-v1-runtime-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "E28B9282307185A026EE13CBB8CCABED8B2E049338A8E4733771F30A5DEEFE59"
)
QUEST_ID = 2257
COMPONENT_IDS = {9947, 9949, 9950, 9998, 17567}
ACT_IDS = {14149, 40846, 63968, 63969, 63970, 64097, 65625}
DOODAD_FUNC_IDS = {38376, 38377, 38382}
LOOT_ROW_ID = 90012908

SKILL_EFFECTS = [
    {
        "id": 59150,
        "always_hit": 0,
        "application_method_id": 1,
        "back": 1,
        "chance": 100,
        "check_no_source_tag_src": 0,
        "check_no_target_tag_src": 0,
        "check_source_tag_src": 0,
        "check_target_tag_src": 0,
        "consume_item_count": 1,
        "consume_item_id": 0,
        "consume_source_item": 0,
        "effect_id": 77705,
        "end_casting_use_chance": 100,
        "end_high_ability_resource": 0,
        "end_level": 255,
        "friendly": 1,
        "front": 1,
        "interaction_success_hit": 0,
        "item_set_id": 0,
        "non_friendly": 1,
        "skill_id": 41925,
        "source_buff_tag_id": 0,
        "source_nobuff_tag_id": 0,
        "start_casting_use_chance": 1,
        "start_high_ability_resource": 0,
        "start_level": 1,
        "synergy_text": 0,
        "target_buff_tag_id": 0,
        "target_nobuff_tag_id": 0,
        "target_npc_tag_id": 0,
        "weight": 0,
        "excute_effect_on_fire": 0,
        "source_buff_stack_count_max": 0,
        "source_buff_stack_count_min": 0,
        "source_except_buff_stack_count_max": 0,
        "source_except_buff_stack_count_min": 0,
        "target_buff_stack_count_max": 0,
        "target_buff_stack_count_min": 0,
        "target_combat_resource_id": 0,
        "target_except_buff_stack_count_max": 0,
        "target_except_buff_stack_count_min": 0,
    },
    {
        "id": 59152,
        "always_hit": 0,
        "application_method_id": 1,
        "back": 1,
        "chance": 100,
        "check_no_source_tag_src": 0,
        "check_no_target_tag_src": 0,
        "check_source_tag_src": 0,
        "check_target_tag_src": 0,
        "consume_item_count": 1,
        "consume_item_id": 0,
        "consume_source_item": 0,
        "effect_id": 77710,
        "end_casting_use_chance": 100,
        "end_high_ability_resource": 0,
        "end_level": 255,
        "friendly": 1,
        "front": 1,
        "interaction_success_hit": 0,
        "item_set_id": 0,
        "non_friendly": 1,
        "skill_id": 41925,
        "source_buff_tag_id": 0,
        "source_nobuff_tag_id": 0,
        "start_casting_use_chance": 1,
        "start_high_ability_resource": 0,
        "start_level": 1,
        "synergy_text": 0,
        "target_buff_tag_id": 0,
        "target_nobuff_tag_id": 0,
        "target_npc_tag_id": 0,
        "weight": 0,
        "excute_effect_on_fire": 0,
        "source_buff_stack_count_max": 0,
        "source_buff_stack_count_min": 0,
        "source_except_buff_stack_count_max": 0,
        "source_except_buff_stack_count_min": 0,
        "target_buff_stack_count_max": 0,
        "target_buff_stack_count_min": 0,
        "target_combat_resource_id": 0,
        "target_except_buff_stack_count_max": 0,
        "target_except_buff_stack_count_min": 0,
    },
]

QUEST_ITEM = {
    "id": 16287,
    "actability_group_id": 0,
    "actability_requirement": 0,
    "auction_a_category_id": 10,
    "auction_b_category_id": 36,
    "auction_c_category_id": 0,
    "auction_charge": 0,
    "auction_charge_default": 1,
    "auction_only": 0,
    "auto_complete": 1,
    "auto_loot": 0,
    "auto_register_to_actionbar": 0,
    "bind_id": 2,
    "buff_id": 0,
    "cash_item": 0,
    "category_id": 64,
    "char_gender_id": 0,
    "contribution_point_price": 0,
    "craft_id": 0,
    "description": "피 묻은 손이 자신들의 상징으로 착용하는 붉은 장갑입니다.",
    "disenchantable": 1,
    "exp_abs_lifetime": 0,
    "exp_date": 0,
    "exp_day_of_week_id": 8,
    "exp_day_of_week_min": 0,
    "exp_online_lifetime": 0,
    "expedition_level": 0,
    "fixed_grade": -1,
    "gradable": 0,
    "honor_price": 0,
    "icon_id": 6360,
    "impl_id": 0,
    "ingameshop_main_category": 0,
    "ingameshop_sub_category": 0,
    "level": 1,
    "level_limit": 0,
    "level_requirement": 0,
    "limited_sale_count": 0,
    "living_point_price": 0,
    "loot_multi": 0,
    "loot_quest_id": 2257,
    "male_icon_id": 0,
    "max_enchant_scale_id": 0,
    "max_enchantable_grade": -1,
    "max_stack_size": 10,
    "name": "피 묻은 손의 장갑",
    "notify_ui": 0,
    "one_time_sale": 0,
    "over_icon_id": 0,
    "pickup_limit": 0,
    "pickup_sound_id": 204,
    "price": 0,
    "proc_lifetime": 0,
    "proc_recharge_restrict_item_id": 0,
    "refund": 0,
    "sellable": 0,
    "side_effect": 0,
    "specialty_zone_id": 0,
    "uid": 1180705403,
    "use_or_equipment_sound_id": 341,
    "use_skill_as_reagent": 0,
    "use_skill_lifetime": 0,
    "use_skill_recharge_restrict_item_id": 0,
    "use_skill_id": 0,
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


def quest_rows(forensic: dict[str, Any]):
    quest = next(
        row
        for row in forensic["native_quest_graph"]
        if int(row["context"]["id"]) == QUEST_ID
    )
    contexts = [dict(quest["context"])]
    components: list[dict[str, Any]] = []
    acts: list[dict[str, Any]] = []
    concrete: dict[str, list[dict[str, Any]]] = {}
    for component in quest["components"]:
        components.append({k: v for k, v in component.items() if k != "acts"})
        for act in component["acts"]:
            acts.append({k: v for k, v in act.items() if k != "detail"})
            concrete.setdefault(str(act["act_detail_type"]), []).append(
                dict(act["detail"])
            )
    return contexts, components, acts, concrete


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
        "context": tuple(
            connection.execute(
                "SELECT category_id,chapter_idx,quest_idx,successive,race "
                "FROM quest_contexts WHERE id=2257"
            ).fetchone()
        ),
        "components": [
            tuple(row)
            for row in connection.execute(
                "SELECT id,component_kind_id FROM quest_components "
                "WHERE quest_context_id=2257 ORDER BY id"
            )
        ],
        "acts": [
            tuple(row)
            for row in connection.execute(
                "SELECT id,act_detail_type,act_detail_id,quest_component_id "
                "FROM quest_acts WHERE quest_component_id IN "
                "(9947,9949,9950,9998,17567) ORDER BY id"
            )
        ],
        "doodad_funcs": [
            tuple(row)
            for row in connection.execute(
                "SELECT id,actual_func_type,actual_func_id,doodad_func_group_id,"
                "func_skill_id,next_phase FROM doodad_funcs "
                "WHERE id IN (38376,38377,38382) ORDER BY id"
            )
        ],
        "doodad_use": tuple(
            connection.execute(
                "SELECT id,skill_id FROM doodad_func_uses WHERE id=10813"
            ).fetchone()
        ),
        "skill_effects": [
            tuple(row)
            for row in connection.execute(
                "SELECT id,effect_id,application_method_id,chance "
                "FROM skill_effects WHERE skill_id=41925 ORDER BY id"
            )
        ],
        "effects": [
            tuple(row)
            for row in connection.execute(
                "SELECT id,actual_type,actual_id FROM effects "
                "WHERE id IN (77705,77710) ORDER BY id"
            )
        ],
        "interaction_effect": tuple(
            connection.execute(
                "SELECT id,doodad_id,source_direction,wi_id "
                "FROM interaction_effects WHERE id=7864"
            ).fetchone()
        ),
        "gain_effect": tuple(
            connection.execute(
                "SELECT id,loot_pack_id,consume_source_item,inherit_grade "
                "FROM gain_loot_pack_item_effects WHERE id=4165"
            ).fetchone()
        ),
        "quest_item": tuple(
            connection.execute(
                "SELECT id,category_id,loot_quest_id,icon_id,max_stack_size,"
                "auto_complete,bind_id,sellable FROM items WHERE id=16287"
            ).fetchone()
        ),
        "loot": tuple(
            connection.execute(
                "SELECT loot_pack_id,item_id,min_amount,max_amount,drop_rate,"
                "always_drop FROM loots WHERE id=?",
                (LOOT_ROW_ID,),
            ).fetchone()
        ),
        "coverage": tuple(
            connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=16287"
            ).fetchone()
        ),
    }
    expected = {
        "context": (3, 1, 6, 1, 1),
        "components": [(9947, 2), (9949, 6), (9950, 8), (9998, 4), (17567, 4)],
        "acts": [
            (14149, "QuestActConReportNpc", 2089, 9949),
            (40846, "QuestActSupplyItem", 4813, 9950),
            (63968, "QuestActObjItemGather", 4330, 17567),
            (63969, "QuestActConAcceptDoodad", 795, 9947),
            (63970, "QuestActObjInteraction", 1113, 9998),
            (64097, "QuestActSupplyExp", 3927, 9950),
            (65625, "QuestActSupplyItem", 8875, 9950),
        ],
        "doodad_funcs": [
            (38376, "DoodadFuncQuest", 1507, 41492, 0, 41493),
            (38377, "DoodadFuncUse", 10813, 41493, 41925, 41494),
            (38382, "DoodadFuncQuest", 1512, 41492, 0, -1),
        ],
        "doodad_use": (10813, 0),
        "skill_effects": [(59150, 77705, 1, 100), (59152, 77710, 1, 100)],
        "effects": [
            (77705, "InteractionEffect", 7864),
            (77710, "GainLootPackItemEffect", 4165),
        ],
        "interaction_effect": (7864, 0, 1, 19),
        "gain_effect": (4165, 12908, 0, 0),
        "quest_item": (16287, 64, 2257, 6360, 10, 1, 2, 0),
        "loot": (12908, 16287, 1, 1, 10000000, "1"),
        "coverage": (
            "generic",
            "complete",
            "",
            "game11_native_items+server_derived_loot_pack_12908",
        ),
    }
    failures = {
        key: {"expected": value, "actual": checks[key]}
        for key, value in expected.items()
        if checks[key] != value
    }
    if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
        failures["sqlite"] = {
            "quick_check": checks["quick_check"],
            "integrity_check": checks["integrity_check"],
        }
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forensic", type=Path, default=DEFAULT_FORENSIC)
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()
    if sha256(options.base_runtime) != EXPECTED_BASE_SHA256:
        raise RuntimeError("base V3 runtime differs from the validated input")

    forensic = json.loads(options.forensic.read_text(encoding="utf-8"))
    contexts, components, acts, concrete_by_type = quest_rows(forensic)
    if {int(row["id"]) for row in components} != COMPONENT_IDS:
        raise RuntimeError("native quest 2257 component IDs changed")
    if {int(row["id"]) for row in acts} != ACT_IDS:
        raise RuntimeError("native quest 2257 act IDs changed")

    green = load_module(
        "green_builder", DOMAIN / "build_native_nuian_green_arc_runtime.py"
    )
    green_extractor = load_module(
        "green_extractor", DOMAIN / "extract_native_nuian_green_arc.py"
    )
    quest_extractor = load_module(
        "quest2256_extractor", DOMAIN / "extract_native_quest_2256.py"
    )
    specs = dict(green_extractor.CONCRETE_SPECS)
    specs["quest_act_obj_interactions"] = quest_extractor.OBJ_INTERACTION_SPEC
    table_by_type = {
        str(spec["type"]): table for table, spec in specs.items()
    }

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)
    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    fallbacks: list[dict[str, Any]] = []
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DELETE FROM quest_acts WHERE quest_component_id IN "
            "(9947,9949,9950,9998,17567)"
        )
        green.replace_rows(connection, "quest_contexts", contexts)
        green.replace_rows(connection, "quest_components", components)
        green.replace_rows(connection, "quest_acts", acts)
        for detail_type, rows in concrete_by_type.items():
            table = table_by_type[detail_type]
            green.replace_rows(connection, table, rows)

        for table, rows in forensic["native_doodad_closure"].items():
            sanitized, cleaned = green.sanitize_unresolved_strings(
                connection, table, [dict(row) for row in rows]
            )
            fallbacks.extend(cleaned)
            green.replace_rows(connection, table, sanitized)

        green.replace_rows(
            connection, "doodad_func_uses", [{"id": 10813, "skill_id": 0}]
        )
        green.replace_rows(connection, "skill_effects", SKILL_EFFECTS)
        green.replace_rows(
            connection,
            "effects",
            [
                {
                    "id": 77705,
                    "actual_type": "InteractionEffect",
                    "actual_id": 7864,
                },
                {
                    "id": 77710,
                    "actual_type": "GainLootPackItemEffect",
                    "actual_id": 4165,
                },
            ],
        )
        green.replace_rows(
            connection,
            "interaction_effects",
            [{"id": 7864, "doodad_id": 0, "source_direction": 1, "wi_id": 19}],
        )
        green.replace_rows(
            connection,
            "gain_loot_pack_item_effects",
            [
                {
                    "id": 4165,
                    "consume_count": 0,
                    "consume_item_id": 0,
                    "consume_source_item": 0,
                    "inherit_grade": 0,
                    "loot_pack_id": 12908,
                }
            ],
        )
        green.replace_rows(connection, "items", [QUEST_ITEM])
        green.replace_rows(
            connection,
            "loots",
            [
                {
                    "id": LOOT_ROW_ID,
                    "group": 1,
                    "item_id": 16287,
                    "drop_rate": 10000000,
                    "min_amount": 1,
                    "max_amount": 1,
                    "loot_pack_id": 12908,
                    "grade_id": 0,
                    "always_drop": 1,
                }
            ],
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            (
                16287,
                "generic",
                "complete",
                "",
                "game11_native_items+server_derived_loot_pack_12908",
            ),
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-2257-warning-villagers-v1",
                forensic["authority"],
                sha256(options.forensic),
                "2257",
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
        "phase": "native-quest-2257-warning-villagers-v1-runtime",
        "authority": forensic["authority"],
        "sources": {
            "quest_and_doodad_forensic_manifest": {
                "path": str(options.forensic),
                "sha256": sha256(options.forensic),
            },
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": sha256(options.base_runtime),
            },
            "skill_effects": {
                "authority": "game11_native",
                "ids": [59150, 59152],
                "source_range": [15897520, 21888960],
            },
            "effects": {
                "authority": "client_compact_native",
                "ids": [77705, 77710],
            },
            "interaction_effect": {
                "authority": "game11_native",
                "id": 7864,
                "source_range": [14294213, 14390785],
            },
            "quest_item": {
                "authority": "game11_native_items",
                "id": 16287,
                "source_range": [75937116, 89076696],
            },
            "visible_behavior_corroboration": {
                "authority": "corroboration_only",
                "url": "https://wiki.archerage.to/na-en/db/quests/2257",
            },
        },
        "scope": {
            "quest_ids": [2257],
            "doodad_ids": [14073],
            "skill_ids": [41925],
            "item_ids": [16287],
            "suppressed_adjacent_quest_ids": [2258],
        },
        "server_derived_rows": [
            {
                "table": "loots",
                "id": LOOT_ROW_ID,
                "loot_pack_id": 12908,
                "item_id": 16287,
                "amount": 1,
                "reason": (
                    "The server-owned loot table is absent from game11. Native "
                    "effect 4165, item.loot_quest_id=2257, and native objective "
                    "4330 uniquely constrain the result to item 16287 x1."
                ),
            }
        ],
        "unresolved_string_fallbacks": fallbacks,
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {
            "deployed": False,
            "reason": "Offline build; controlled game-only restart pending.",
        },
    }
    options.manifest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {options.output} ({options.output.stat().st_size} bytes, "
        f"sha256={document['output']['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
