#!/usr/bin/env python3
"""Build the native AA8 Explorer -> Hiram T1 runtime closure.

All raw gameplay rows are decoded from Kakao 8.0.3.12 game11 or copied from
the decrypted AA8 compact. Server-derived rows are limited to relations that
do not exist in the client schema (loot contents and the ranged-box binding)
and are identified as such in the manifest.
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
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = ROOT / "reconstruccion_skills_8"
SYNTHESIS_SOURCE = (
    ROOT / "reconstruccion_items_8" / "phase_b_synthesis"
    / "extract_native_synthesis.py"
)
EVOLUTION_SOURCE = (
    ROOT / "reconstruccion_items_8" / "phase_b_synthesis_awaken"
    / "build_native_evolution_runtime.py"
)

EXPLORER_TARGET_GROUPS = {11, 31, 33}
EXPLORER_MATERIAL_GROUPS = {12, 32, 34}
EXPLORER_MAPPING_GROUPS = {48, 49, 50}
INFUSIONS = {48845: (50, 2), 48846: (130, 3), 48847: (250, 4)}
SCROLLS = {47866: 42200, 47867: 42201, 47952: 42202}
WRAPPERS = {48507: 43013, 48508: 43014, 48509: 43015}
ARMOR_BOXES = list(range(48087, 48099))
WEAPON_BOXES = [47868, 47869, 51185]
ARMOR_LOOT_PACKS = dict(zip(ARMOR_BOXES, range(12971, 12983)))
MERCHANT_PACKS = {
    "weapon": 914119,
    "general": 914145,
    "armor": 914219,
}

QUEST_ITEM_IDS = set(INFUSIONS) | set(SCROLLS) | set(WRAPPERS)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def cached_reader(game11: Path):
    sys.path.insert(0, str(SKILLS_ROOT))
    from extract_battlerage_manifest import CachedResultReader

    return CachedResultReader(game11.read_bytes())


def cached_rows(
    reader,
    start: int,
    columns: list[str],
    layout: list[str],
    first_string_reference: int | None = None,
) -> tuple[list[dict[str, Any]], int, dict[int, str]]:
    from extract_battlerage_manifest import read_cached_result

    if first_string_reference is not None:
        reader.begin_string_cache_capture(first_string_reference)
    rows, end = read_cached_result(reader, start, layout)
    captured = (
        reader.end_string_cache_capture()
        if first_string_reference is not None
        else {}
    )
    return [dict(zip(columns, row)) for row in rows], end, captured


def query_rows(
    connection: sqlite3.Connection,
    table: str,
    ids: Iterable[int],
) -> list[dict[str, Any]]:
    identifiers = sorted(set(int(value) for value in ids))
    if not identifiers:
        return []
    placeholders = ",".join("?" for _ in identifiers)
    connection.row_factory = sqlite3.Row
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {table} WHERE id IN ({placeholders})",
            identifiers,
        )
    ]


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    key: str = "id",
) -> None:
    if not rows:
        return
    available = {
        row[1] for row in connection.execute(f"PRAGMA table_info({table})")
    }
    columns = [column for column in rows[0] if column in available]
    if not columns:
        raise RuntimeError(f"No compatible columns for {table}")
    placeholders = ",".join(f":{column}" for column in columns)
    connection.executemany(
        f"""
        INSERT OR REPLACE INTO {table} ({','.join(columns)})
        VALUES ({placeholders})
        """,
        sorted(rows, key=lambda row: int(row.get(key, 0))),
    )


def extract_evolution(
    game11: Path,
    base_runtime: Path,
    client_compact: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], dict]:
    synthesis = load_module(SYNTHESIS_SOURCE, "aa8_b14_synthesis")
    evolution = load_module(EVOLUTION_SOURCE, "aa8_b14_evolution")
    tables, ranges = synthesis.extract(game11)

    mappings = [
        row
        for row in tables["item_change_mappings"]
        if int(row["mapping_group_id"]) in EXPLORER_MAPPING_GROUPS
    ]
    family_items = {
        int(row[field])
        for row in mappings
        for field in ("source_item_id", "target_item_id")
    }
    if len(mappings) != 184:
        raise RuntimeError(f"Expected 184 Explorer mappings, found {len(mappings)}")

    with sqlite3.connect(base_runtime) as connection:
        connection.row_factory = sqlite3.Row
        category_ids = {
            int(row[0])
            for item_id in family_items
            for row in connection.execute(
                """
                SELECT item_rnd_attr_category_id FROM item_weapons WHERE item_id=?
                UNION ALL
                SELECT item_rnd_attr_category_id FROM item_armors WHERE item_id=?
                """,
                (item_id, item_id),
            )
            if int(row[0] or 0) > 0
        }

    enabled_groups = EXPLORER_TARGET_GROUPS | EXPLORER_MATERIAL_GROUPS
    categories = [
        row
        for row in tables["item_rnd_attr_categories"]
        if int(row["item_rnd_attr_category_group_id"]) in enabled_groups
    ]
    category_ids |= {int(row["id"]) for row in categories}
    material_category_ids = {
        int(row["id"])
        for row in categories
        if int(row["item_rnd_attr_category_group_id"]) in EXPLORER_MATERIAL_GROUPS
    }

    sets_by_id = {
        int(row["id"]): row
        for row in tables["item_rnd_attr_unit_modifier_group_sets"]
    }
    required_sets = {
        int(row["id"])
        for row in sets_by_id.values()
        if int(row["item_rnd_attr_category_id"]) in category_ids
    }
    frontier = list(required_sets)
    while frontier:
        parent = int(sets_by_id[frontier.pop()]["inherit_priority_id"])
        if parent and parent in sets_by_id and parent not in required_sets:
            required_sets.add(parent)
            frontier.append(parent)
    modifier_groups = [
        row
        for row in tables["item_rnd_attr_unit_modifier_groups"]
        if int(row["item_rnd_attr_unit_modifier_group_set_id"]) in required_sets
    ]
    modifier_group_ids = {int(row["id"]) for row in modifier_groups}

    filtered = {
        "item_rnd_attr_categories": categories,
        "item_rnd_attr_category_groups": [
            row
            for row in tables["item_rnd_attr_category_groups"]
            if int(row["id"]) in enabled_groups
        ],
        "item_rnd_attr_category_properties": [
            row
            for row in tables["item_rnd_attr_category_properties"]
            if int(row["item_rnd_attr_category_id"]) in category_ids
        ],
        "item_rnd_attr_category_elements": [
            row
            for row in tables["item_rnd_attr_category_elements"]
            if int(row["item_rnd_attr_category_id"]) in category_ids
        ],
        "item_rnd_attr_category_relations": [
            row
            for row in tables["item_rnd_attr_category_relations"]
            if int(row["item_rnd_attr_category_group_id"]) in EXPLORER_TARGET_GROUPS
            and int(row["material_id"]) in INFUSIONS
        ],
        "item_evolving_materials": [
            row
            for row in tables["item_evolving_materials"]
            if int(row["item_id"]) in INFUSIONS
            and int(row["item_rnd_attr_category_id"]) in material_category_ids
        ],
        "item_change_mapping_groups": [
            row
            for row in tables["item_change_mapping_groups"]
            if int(row["id"]) in EXPLORER_MAPPING_GROUPS
        ],
        "item_change_mappings": mappings,
        "item_rnd_attr_unit_modifier_group_sets": [
            row for row in sets_by_id.values() if int(row["id"]) in required_sets
        ],
        "item_rnd_attr_unit_modifier_groups": modifier_groups,
        "item_rnd_attr_unit_modifiers": [
            row
            for row in tables["item_rnd_attr_unit_modifiers"]
            if int(row["group_id"]) in modifier_group_ids
        ],
    }
    reactives = evolution.extract_awakening_reactives(
        game11,
        client_compact,
        EXPLORER_MAPPING_GROUPS,
    )
    facts = {
        "family_items": sorted(family_items),
        "category_ids": sorted(category_ids),
        "source_ranges": ranges,
    }
    return filtered, reactives, facts


def extract_skills_and_boxes(
    game11: Path,
    client_compact: Path,
) -> tuple[dict[str, list[dict[str, Any]]], dict]:
    sys.path.insert(0, str(SKILLS_ROOT))
    from extract_battlerage_manifest import extract_client_relationships

    relationships = extract_client_relationships(game11)
    skill_ids = set(WRAPPERS.values()) | {
        42428, 42429, 42430, 42431, 42432, 42433,
        42435, 42436, 42437, 42438, 42439, 42440,
    }
    armor_skill_ids = skill_ids - set(WRAPPERS.values())
    armor_skill_effects = [
        {
            **dict(row),
            "end_level": 255
            if int(row.get("end_level") or 0) == 99
            else int(row.get("end_level") or 0),
        }
        for row in relationships["skill_effects"]
        if int(row["skill_id"]) in armor_skill_ids
    ]
    effect_ids = {int(row["effect_id"]) for row in armor_skill_effects}
    with sqlite3.connect(client_compact) as connection:
        connection.row_factory = sqlite3.Row
        skills = query_rows(connection, "skills", skill_ids)
        effects = query_rows(connection, "effects", effect_ids)
        gain_effects = query_rows(
            connection,
            "gain_loot_pack_item_effects",
            {int(row["actual_id"]) for row in effects},
        )
        item_rows = {
            int(row["id"]): dict(row)
            for row in connection.execute(
                f"""
                SELECT id,name,description,use_skill_id,uid
                FROM items WHERE id IN (
                    {','.join('?' for _ in ARMOR_BOXES)}
                )
                """,
                ARMOR_BOXES,
            )
        }
        all_items = [
            dict(row)
            for row in connection.execute("SELECT id,name,uid FROM items")
        ]

    for row in effects:
        row["actual_type"] = "GainLootPackItemEffect"
    if len(skills) != len(skill_ids) or len(armor_skill_effects) != 12:
        raise RuntimeError("Explorer wrapper/armor skill closure is incomplete")
    if len(effects) != 12 or len(gain_effects) != 12:
        raise RuntimeError("Explorer armor GainLootPack closure is incomplete")

    ids_by_name: dict[str, list[int]] = defaultdict(list)
    for row in all_items:
        ids_by_name[str(row["name"])].append(int(row["id"]))
    armor_contents: dict[int, list[int]] = {}
    for box_id in ARMOR_BOXES:
        names = [
            line[2:].strip()
            for line in str(item_rows[box_id]["description"]).splitlines()
            if line.startswith("- ")
        ]
        result_ids: list[int] = []
        for name in names:
            matches = ids_by_name.get(name, [])
            # Three Blizzard descriptions contain the AA8 client typo 설윈;
            # the corresponding native item names use 설원의.
            if not matches and name.startswith("설윈의 "):
                matches = ids_by_name.get("설원의 " + name[len("설윈의 "):], [])
            if len(matches) != 1:
                raise RuntimeError(
                    f"Armor box {box_id} result {name!r} has {len(matches)} matches"
                )
            result_ids.append(matches[0])
        if len(result_ids) != 7:
            raise RuntimeError(
                f"Armor box {box_id} has {len(result_ids)} native description results"
            )
        armor_contents[box_id] = result_ids

    reader = cached_reader(game11)
    reagents, reagent_end, _ = cached_rows(
        reader,
        0x8CC11E,
        "id amount item_id skill_id".split(),
        "68 68 68 68".split(),
    )
    products, product_end, _ = cached_rows(
        reader,
        0x8D753C,
        "id amount item_id skill_id".split(),
        "68 68 68 68".split(),
    )
    reagents = [
        row for row in reagents if int(row["skill_id"]) in WRAPPERS.values()
    ]
    products = [
        row for row in products if int(row["skill_id"]) in WRAPPERS.values()
    ]
    if len(reagents) != 3 or len(products) != 3:
        raise RuntimeError("Explorer infusion wrapper closure is incomplete")

    return {
        "skills": skills,
        "skill_effects": armor_skill_effects,
        "effects": effects,
        "gain_loot_pack_item_effects": gain_effects,
        "skill_reagents": reagents,
        "skill_products": products,
    }, {
        "armor_contents": armor_contents,
        "ranges": {
            "skill_reagents": {"start": 0x8CC11E, "end": reagent_end},
            "skill_products": {"start": 0x8D753C, "end": product_end},
        },
    }


def extract_selective_actions(client_compact: Path) -> list[dict[str, Any]]:
    with sqlite3.connect(client_compact) as connection:
        connection.row_factory = sqlite3.Row
        uid_by_id = {
            int(row["id"]): f"{int(row['uid']) & 0xFFFFFFFF:08x}"
            for row in connection.execute(
                """
                SELECT id,uid FROM items
                WHERE id BETWEEN 47776 AND 47790 OR id=50799
                """
            )
        }
    actions = [
        {
            "source_item_id": 47868,
            "skill_id": 42205,
            "alias": "main_left_weapon",
            "select_count": 1,
            "consume_item_count": 1,
            "is_multi": 1,
            "popup_text": "confirm_using_selective_item",
            "source_offset": 0x892B18C,
            "provenance":
                "game11_native_payload+client_compact_source_item;"
                "skill_id_non_unique_metadata",
            "options": [47776, 47777, 47778, 47779, 47780, 47781, 47782, 47789],
        },
        {
            "source_item_id": 47869,
            "skill_id": 42209,
            "alias": "main_twohand",
            "select_count": 1,
            "consume_item_count": 1,
            "is_multi": 1,
            "popup_text": "confirm_using_selective_item",
            "source_offset": 0x892B405,
            "provenance":
                "game11_native_payload_skill_42204+client_compact_source_"
                "use_skill_42209;source_item_authoritative",
            "options": [47783, 47784, 47785, 47786, 47787, 47788],
        },
        {
            "source_item_id": 51185,
            "skill_id": 46956,
            "alias": "explorer_ranged_category_638",
            "select_count": 1,
            "consume_item_count": 1,
            "is_multi": 1,
            "popup_text": "confirm_using_selective_item",
            "source_offset": -1,
            "provenance":
                "server_derived_from_AA8_source_description_and_complete_"
                "native_category_638_membership;raw_action_collision_blocked",
            "options": [47790, 50799],
        },
    ]
    for action in actions:
        action["option_rows"] = [
            {
                "source_item_id": action["source_item_id"],
                "option_index": index,
                "result_item_id": item_id,
                "result_count": 1,
                "result_grade": None,
                "result_uid": uid_by_id[item_id],
                "provenance": action["provenance"],
            }
            for index, item_id in enumerate(action["options"], start=1)
        ]
    return actions


def extract_merchants(game11: Path) -> tuple[dict[str, Any], dict]:
    reader = cached_reader(game11)
    columns = (
        "npc_id item_id grade_id kind_id cost item_point_id "
        "item_point_icon item_point_icon_key"
    ).split()
    layout = "68 68 68 68 68 68 78 78".split()
    joined, joined_end, _ = cached_rows(
        reader,
        0x8AB440D,
        columns,
        layout,
    )
    pack_columns = (
        "pack_id kind_id item_id grade_id cost item_point_id "
        "item_point_icon item_point_icon_key"
    ).split()
    packs, packs_end, _ = cached_rows(
        reader,
        0x8CA020F,
        pack_columns,
        layout,
    )

    relevant = {
        "weapon": set(WEAPON_BOXES),
        "armor": set(ARMOR_BOXES),
        "general": set(INFUSIONS) | {47866, 47867},
    }
    npc_items: dict[int, set[int]] = defaultdict(set)
    for row in joined:
        npc_items[int(row["npc_id"])].add(int(row["item_id"]))
    sellers = {
        kind: sorted(
            npc_id
            for npc_id, item_ids in npc_items.items()
            if expected <= item_ids
        )
        for kind, expected in relevant.items()
    }
    expected_counts = {"weapon": 62, "armor": 63, "general": 379}
    if {kind: len(ids) for kind, ids in sellers.items()} != expected_counts:
        raise RuntimeError(
            "Unexpected native Explorer seller counts: "
            f"{ {kind: len(ids) for kind, ids in sellers.items()} }"
        )
    if len(set().union(*(set(ids) for ids in sellers.values()))) != 504:
        raise RuntimeError("Explorer seller templates overlap unexpectedly")

    pack_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in packs:
        pack_by_id[int(row["pack_id"])].append(row)
    native_pack_ids = {"weapon": (119, 120), "general": (145,), "armor": (219,)}
    goods: dict[str, list[dict[str, Any]]] = {}
    for kind, pack_ids in native_pack_ids.items():
        candidates = [
            row
            for pack_id in pack_ids
            for row in pack_by_id[pack_id]
            if int(row["item_id"]) in relevant[kind]
        ]
        unique: dict[tuple[int, int], dict[str, Any]] = {}
        for row in candidates:
            unique[(int(row["item_id"]), int(row["grade_id"]))] = row
        goods[kind] = [
            unique[key] for key in sorted(unique, key=lambda value: value[0])
        ]
        if {int(row["item_id"]) for row in goods[kind]} != relevant[kind]:
            raise RuntimeError(f"Native merchant pack {kind} closure is incomplete")

    return {
        "sellers": sellers,
        "goods": goods,
        "native_pack_ids": native_pack_ids,
    }, {
        "joined": {"start": 0x8AB440D, "end": joined_end, "rows": len(joined)},
        "packs": {"start": 0x8CA020F, "end": packs_end, "rows": len(packs)},
    }


def extract_quests(game11: Path, base_runtime: Path) -> tuple[dict[str, list[dict]], dict]:
    reader = cached_reader(game11)
    ranges: dict[str, dict[str, int]] = {}

    def read(name, start, columns, layout, first_ref=None):
        rows, end, _ = cached_rows(
            reader, start, columns.split(), layout.split(), first_ref
        )
        ranges[name] = {"start": start, "end": end, "rows": len(rows)}
        return rows

    supply_items = read(
        "quest_act_supply_items",
        0x6D6B51B,
        "id cleanup count destroy_when_drop drop_when_destroy grade_id "
        "item_id show_action_bar try_equip",
        "68 38 68 38 38 68 68 38 38",
    )
    supply_selective = read(
        "quest_act_supply_selective_items",
        0x6D9BD7A,
        "id count grade_id item_id",
        "68 68 68 68",
    )
    acts = read(
        "quest_acts",
        0x6DB2158,
        "id act_detail_type act_detail_id quest_component_id",
        "68 78 68 68",
        320614,
    )
    components = read(
        "quest_components",
        121996619,
        "id ai_command_set_id ai_path_name ai_path_type_id buff_id cinema_id "
        "component_kind_id hide_quest_marker next_component npc_ai_id "
        "npc_spawner_id npc_id or_unit_reqs play_cinema_before_bubble "
        "quest_context_id skill_self skill_id sound_id summary_voice_id",
        "68 68 78 68 68 68 68 38 68 68 68 68 38 38 68 38 68 68 68",
    )
    contexts = read(
        "quest_contexts",
        124139000,
        "id category_id chapter_idx degree detail_id grade_id "
        "hide_chapter_index let_it_done level max_level min_level name "
        "only_one_score_title priority quest_idx race repeatable "
        "restart_on_fail score selective successive use_accept_message "
        "use_complete_message use_quest_camera zone_id",
        "68 68 68 68 68 68 38 38 68 68 68 78 38 68 68 68 38 38 68 "
        "38 38 38 38 38 68",
    )
    accept_groups = read(
        "quest_act_con_accept_npc_groups",
        115014414,
        "id quest_monster_group_id",
        "68 68",
    )
    accept_npcs = read(
        "quest_act_con_accept_npcs",
        0x6D3DC71,
        "id npc_id quest_act_obj_alias_id use_alias",
        "68 68 68 38",
    )
    auto_complete = read(
        "quest_act_con_auto_completes",
        0x6D535A6,
        "id",
        "68",
    )
    spheres = read(
        "quest_act_obj_spheres",
        0x6D396B7,
        "id cinema highlight_doodad_phase highlight_doodad_id name npc_id "
        "quest_act_obj_alias_id sphere_id use_alias",
        "68 78 68 68 78 68 68 68 38",
    )
    supply_exps = read(
        "quest_act_supply_exps",
        0x6D89D77,
        "id exp",
        "68 68",
    )
    supply_coppers = read(
        "quest_act_supply_coppers",
        0x6D9309E,
        "id amount",
        "68 68",
    )
    monster_npcs = read(
        "quest_monster_npcs",
        114003821,
        "id npc_id quest_monster_group_id",
        "68 68 68",
    )

    relevant_supply_items = [
        row for row in supply_items if int(row["item_id"]) in QUEST_ITEM_IDS
    ]
    relevant_selective = [
        row
        for row in supply_selective
        if int(row["item_id"]) in {47868, 47869, 51185}
    ]
    detail_keys = {
        ("QuestActSupplyItem", int(row["id"]))
        for row in relevant_supply_items
    } | {
        ("QuestActSupplySelectiveItem", int(row["id"]))
        for row in relevant_selective
    }
    seed_acts = [
        row
        for row in acts
        if (str(row["act_detail_type"]), int(row["act_detail_id"])) in detail_keys
    ]
    seed_components = {int(row["quest_component_id"]) for row in seed_acts}
    component_by_id = {int(row["id"]): row for row in components}
    context_ids = {
        int(component_by_id[component_id]["quest_context_id"])
        for component_id in seed_components
    }

    with sqlite3.connect(base_runtime) as connection:
        existing_contexts = {
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM quest_contexts"
            )
        }
    missing_contexts = context_ids - existing_contexts
    missing_components = [
        row
        for row in components
        if int(row["quest_context_id"]) in missing_contexts
    ]
    missing_component_ids = {int(row["id"]) for row in missing_components}
    missing_acts = [
        row for row in acts if int(row["quest_component_id"]) in missing_component_ids
    ]
    all_import_acts = {
        int(row["id"]): row for row in seed_acts + missing_acts
    }

    detail_ids: dict[str, set[int]] = defaultdict(set)
    for row in all_import_acts.values():
        detail_ids[str(row["act_detail_type"])].add(int(row["act_detail_id"]))
    detail_sources = {
        "QuestActSupplyItem": ("quest_act_supply_items", supply_items),
        "QuestActSupplySelectiveItem":
            ("quest_act_supply_selective_items", supply_selective),
        "QuestActConAcceptNpcGroup":
            ("quest_act_con_accept_npc_groups", accept_groups),
        "QuestActConAcceptNpc": ("quest_act_con_accept_npcs", accept_npcs),
        "QuestActConAutoComplete":
            ("quest_act_con_auto_completes", auto_complete),
        "QuestActObjSphere": ("quest_act_obj_spheres", spheres),
        "QuestActSupplyExp": ("quest_act_supply_exps", supply_exps),
        "QuestActSupplyCopper": ("quest_act_supply_coppers", supply_coppers),
    }
    result: dict[str, list[dict]] = {
        "quest_contexts": [
            row for row in contexts if int(row["id"]) in missing_contexts
        ],
        "quest_components": missing_components,
        "quest_acts": list(all_import_acts.values()),
    }
    for detail_type, ids in detail_ids.items():
        if detail_type not in detail_sources:
            raise RuntimeError(
                f"Missing B14 quest detail extractor for {detail_type}"
            )
        table, source_rows = detail_sources[detail_type]
        selected = [row for row in source_rows if int(row["id"]) in ids]
        if len(selected) != len(ids):
            raise RuntimeError(
                f"Quest detail closure incomplete for {detail_type}: "
                f"{len(selected)}/{len(ids)}"
            )
        result.setdefault(table, []).extend(selected)

    group_ids = {
        int(row["quest_monster_group_id"])
        for row in result.get("quest_act_con_accept_npc_groups", [])
    }
    result["quest_monster_npcs"] = [
        row
        for row in monster_npcs
        if int(row["quest_monster_group_id"]) in group_ids
    ]
    if len(relevant_supply_items) != 128 or len(relevant_selective) != 12:
        raise RuntimeError(
            "Unexpected Explorer quest reward counts: "
            f"items={len(relevant_supply_items)} selective={len(relevant_selective)}"
        )
    facts = {
        "context_ids": sorted(context_ids),
        "missing_context_ids": sorted(missing_contexts),
        "seed_acts": len(seed_acts),
        "imported_acts": len(all_import_acts),
        "ranges": ranges,
    }
    return result, facts


def ensure_merchant_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(merchant_goods)")
    }
    if "currency_id" not in columns:
        connection.execute(
            "ALTER TABLE merchant_goods ADD COLUMN currency_id INTEGER NOT NULL DEFAULT 0"
        )
    if "price" not in columns:
        connection.execute(
            "ALTER TABLE merchant_goods ADD COLUMN price INTEGER NOT NULL DEFAULT -1"
        )
    if "sort_order" not in columns:
        connection.execute(
            "ALTER TABLE merchant_goods ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
        )


def install_selective(
    connection: sqlite3.Connection,
    explorer_actions: list[dict[str, Any]],
) -> None:
    connection.row_factory = sqlite3.Row
    old_actions = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM aaemu_selective_item_actions"
        )
    ]
    old_options = [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM aaemu_selective_item_options"
        )
    ]
    old_by_skill = {
        int(row["skill_id"]): int(row["source_item_id"]) for row in old_actions
    }
    connection.executescript(
        """
        DROP TABLE aaemu_selective_item_options;
        DROP TABLE aaemu_selective_item_actions;
        CREATE TABLE aaemu_selective_item_actions (
            source_item_id INTEGER PRIMARY KEY,
            skill_id INTEGER NOT NULL,
            alias TEXT NOT NULL,
            select_count INTEGER NOT NULL,
            consume_item_count INTEGER NOT NULL,
            is_multi INTEGER NOT NULL,
            popup_text TEXT NOT NULL,
            provenance TEXT NOT NULL,
            source_offset INTEGER NOT NULL
        );
        CREATE INDEX aaemu_selective_item_actions_skill_idx
          ON aaemu_selective_item_actions(skill_id);
        CREATE TABLE aaemu_selective_item_options (
            source_item_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            result_item_id INTEGER NOT NULL,
            result_count INTEGER NOT NULL,
            result_grade INTEGER,
            result_uid TEXT NOT NULL,
            provenance TEXT NOT NULL,
            PRIMARY KEY (source_item_id, option_index),
            FOREIGN KEY (source_item_id)
              REFERENCES aaemu_selective_item_actions(source_item_id)
        );
        """
    )
    for row in old_actions:
        insert_rows(connection, "aaemu_selective_item_actions", [row], "source_item_id")
    for row in old_options:
        if "source_item_id" not in row:
            row["source_item_id"] = old_by_skill[int(row["skill_id"])]
        insert_rows(connection, "aaemu_selective_item_options", [row], "option_index")
    for action in explorer_actions:
        action_row = {
            key: value
            for key, value in action.items()
            if key not in {"options", "option_rows"}
        }
        insert_rows(
            connection,
            "aaemu_selective_item_actions",
            [action_row],
            "source_item_id",
        )
        insert_rows(
            connection,
            "aaemu_selective_item_options",
            action["option_rows"],
            "option_index",
        )


def build(
    base: Path,
    output: Path,
    evolution_tables: dict[str, list[dict[str, Any]]],
    reactives: dict[str, list[dict[str, Any]]],
    skill_box_tables: dict[str, list[dict[str, Any]]],
    armor_contents: dict[int, list[int]],
    selective_actions: list[dict[str, Any]],
    merchants: dict[str, Any],
    quests: dict[str, list[dict]],
    family_items: list[int],
) -> dict[str, Any]:
    shutil.copyfile(base, output)
    connection = sqlite3.connect(output)
    try:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")

        for table, rows in evolution_tables.items():
            insert_rows(
                connection,
                table,
                rows,
                "item_id" if table == "item_evolving_materials" else "id",
            )
        for table in ("skills", "special_effects", "effects", "skill_effects"):
            combined = list(reactives.get(table, []))
            if table in skill_box_tables:
                combined.extend(skill_box_tables[table])
            insert_rows(connection, table, combined)
        for table in (
            "gain_loot_pack_item_effects",
            "skill_reagents",
            "skill_products",
        ):
            insert_rows(connection, table, skill_box_tables[table])

        for box_id, pack_id in ARMOR_LOOT_PACKS.items():
            connection.execute("DELETE FROM loots WHERE loot_pack_id=?", (pack_id,))
            connection.execute("DELETE FROM loot_groups WHERE pack_id=?", (pack_id,))
            for group_no, item_id in enumerate(armor_contents[box_id], start=1):
                row_id = 91_400_000 + pack_id * 10 + group_no
                connection.execute(
                    """
                    INSERT INTO loots (
                        id,"group",item_id,drop_rate,min_amount,max_amount,
                        loot_pack_id,grade_id,always_drop
                    ) VALUES (?,?,?,10000000,1,1,?,0,'t')
                    """,
                    (row_id, group_no, item_id, pack_id),
                )

        install_selective(connection, selective_actions)
        ensure_merchant_columns(connection)
        for pack_id in MERCHANT_PACKS.values():
            connection.execute(
                "DELETE FROM merchant_goods WHERE merchant_pack_id=?",
                (pack_id,),
            )
        for kind, native_rows in merchants["goods"].items():
            pack_id = MERCHANT_PACKS[kind]
            for order, row in enumerate(native_rows):
                item_id = int(row["item_id"])
                template_price = connection.execute(
                    "SELECT price FROM items WHERE id=?",
                    (item_id,),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO merchant_goods (
                        id,merchant_pack_id,item_id,grade_id,
                        currency_id,price,sort_order
                    ) VALUES (?,?,?,?,0,?,?)
                    """,
                    (
                        91_500_000 + pack_id * 100 + order,
                        pack_id,
                        item_id,
                        int(row["grade_id"]),
                        int(template_price),
                        order,
                    ),
                )
            for npc_id in merchants["sellers"][kind]:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO merchants (id,npc_id,merchant_pack_id)
                    VALUES (?,?,?)
                    """,
                    (91_600_000 + npc_id, npc_id, pack_id),
                )

        for table, rows in quests.items():
            insert_rows(connection, table, rows)

        complete_items = (
            set(family_items)
            | set(INFUSIONS)
            | set(SCROLLS)
            | set(WRAPPERS)
            | set(ARMOR_BOXES)
            | set(WEAPON_BOXES)
            | {item for values in armor_contents.values() for item in values}
            | {item for action in selective_actions for item in action["options"]}
        )
        for item_id in sorted(complete_items):
            concrete = connection.execute(
                """
                SELECT concrete_type FROM aaemu_item_definition_coverage
                WHERE item_id=?
                """,
                (item_id,),
            ).fetchone()
            if concrete is None:
                continue
            connection.execute(
                """
                UPDATE aaemu_item_definition_coverage
                SET coverage='complete', missing_dependencies='',
                    provenance=provenance || '+B14_AA8_native_closure'
                WHERE item_id=?
                """,
                (item_id,),
            )

        metadata = {
            "phase": "B14-native-explorer-to-hiram-t1",
            "authority": "AA8 client compact/game11/x2game; no 3.0 gameplay rows",
            "explorer.mapping_groups": "48,49,50",
            "explorer.infusions": "48845:50,48846:130,48847:250",
            "explorer.scrolls": "47866:42200,47867:42201,47952:42202",
            "explorer.wrappers": "48507:43013,48508:43014,48509:43015",
            "explorer.merchant_templates": "504",
            "explorer.ranged_box":
                "server_derived from AA8 category 638 complete membership",
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


def validate(connection: sqlite3.Connection) -> dict[str, Any]:
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check":
            connection.execute("PRAGMA integrity_check").fetchone()[0],
        "mapping_groups": connection.execute(
            """
            SELECT COUNT(*) FROM item_change_mapping_groups
            WHERE id IN (48,49,50) AND success=10000
            """
        ).fetchone()[0],
        "mappings": connection.execute(
            """
            SELECT COUNT(*) FROM item_change_mappings
            WHERE mapping_group_id IN (48,49,50)
            """
        ).fetchone()[0],
        "infusions": connection.execute(
            """
            SELECT COUNT(*) FROM item_evolving_materials
            WHERE item_id IN (48845,48846,48847)
            """
        ).fetchone()[0],
        "infusion_exp": [
            tuple(row)
            for row in connection.execute(
                """
                SELECT m.item_id,i.fixed_grade,p.gain_exp
                FROM item_evolving_materials m
                JOIN items i ON i.id=m.item_id
                JOIN item_rnd_attr_category_properties p
                  ON p.item_rnd_attr_category_id=m.item_rnd_attr_category_id
                 AND p.grade_id=i.fixed_grade
                WHERE m.item_id IN (48845,48846,48847)
                ORDER BY m.item_id
                """
            )
        ],
        "armor_pack_rows": connection.execute(
            """
            SELECT COUNT(*) FROM loots
            WHERE loot_pack_id BETWEEN 12971 AND 12982
            """
        ).fetchone()[0],
        "selective_actions": connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_selective_item_actions
            WHERE source_item_id IN (47868,47869,51185)
            """
        ).fetchone()[0],
        "selective_options": connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_selective_item_options
            WHERE source_item_id IN (47868,47869,51185)
            """
        ).fetchone()[0],
        "selective_option_bands": [
            tuple(row)
            for row in connection.execute(
                """
                SELECT source_item_id,COUNT(*)
                FROM aaemu_selective_item_options
                WHERE source_item_id IN (47868,47869,51185)
                GROUP BY source_item_id ORDER BY source_item_id
                """
            )
        ],
        "merchant_templates": connection.execute(
            """
            SELECT COUNT(DISTINCT npc_id) FROM merchants
            WHERE merchant_pack_id IN (914119,914145,914219)
            """
        ).fetchone()[0],
        "merchant_goods": connection.execute(
            """
            SELECT COUNT(*) FROM merchant_goods
            WHERE merchant_pack_id IN (914119,914145,914219)
            """
        ).fetchone()[0],
        "merchant_good_bands": [
            tuple(row)
            for row in connection.execute(
                """
                SELECT merchant_pack_id,COUNT(*)
                FROM merchant_goods
                WHERE merchant_pack_id IN (914119,914145,914219)
                GROUP BY merchant_pack_id ORDER BY merchant_pack_id
                """
            )
        ],
        "rank3_scroll_sold": connection.execute(
            """
            SELECT COUNT(*) FROM merchant_goods
            WHERE merchant_pack_id=914145 AND item_id=47952
            """
        ).fetchone()[0],
        "wrapper_reagents": connection.execute(
            """
            SELECT COUNT(*) FROM skill_reagents
            WHERE skill_id IN (43013,43014,43015)
            """
        ).fetchone()[0],
        "wrapper_products": connection.execute(
            """
            SELECT COUNT(*) FROM skill_products
            WHERE skill_id IN (43013,43014,43015)
            """
        ).fetchone()[0],
        "quest_reward_acts": connection.execute(
            """
            SELECT COUNT(*) FROM quest_acts
            WHERE (act_detail_type='QuestActSupplyItem'
                   AND act_detail_id IN (
                       SELECT id FROM quest_act_supply_items
                       WHERE item_id IN (
                           47866,47867,47952,48507,48508,48509,
                           48845,48846,48847
                       )
                   ))
               OR (act_detail_type='QuestActSupplySelectiveItem'
                   AND act_detail_id IN (
                       SELECT id FROM quest_act_supply_selective_items
                       WHERE item_id IN (47868,47869,51185)
                   ))
            """
        ).fetchone()[0],
        "orphan_selective": connection.execute(
            """
            SELECT COUNT(*) FROM aaemu_selective_item_options o
            LEFT JOIN aaemu_selective_item_actions a
              ON a.source_item_id=o.source_item_id
            LEFT JOIN items i ON i.id=o.result_item_id
            WHERE a.source_item_id IS NULL OR i.id IS NULL
            """
        ).fetchone()[0],
        "orphan_mappings": connection.execute(
            """
            SELECT COUNT(*) FROM item_change_mappings m
            LEFT JOIN items s ON s.id=m.source_item_id
            LEFT JOIN items t ON t.id=m.target_item_id
            WHERE m.mapping_group_id IN (48,49,50)
              AND (s.id IS NULL OR t.id IS NULL)
            """
        ).fetchone()[0],
        "closed_mapping_items": connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT source_item_id AS item_id FROM item_change_mappings
                WHERE mapping_group_id IN (48,49,50)
                UNION
                SELECT target_item_id FROM item_change_mappings
                WHERE mapping_group_id IN (48,49,50)
                UNION
                SELECT item_id FROM item_evolving_materials
                WHERE item_id IN (48845,48846,48847)
            ) x
            JOIN aaemu_item_definition_coverage c ON c.item_id=x.item_id
            WHERE c.coverage='complete' AND c.missing_dependencies=''
            """
        ).fetchone()[0],
    }
    expected = {
        "mapping_groups": 3,
        "mappings": 184,
        "infusions": 3,
        "armor_pack_rows": 84,
        "selective_actions": 3,
        "selective_options": 16,
        "merchant_templates": 504,
        "merchant_goods": 20,
        "wrapper_reagents": 3,
        "wrapper_products": 3,
        "quest_reward_acts": 140,
        "orphan_selective": 0,
        "orphan_mappings": 0,
        "closed_mapping_items": 225,
    }
    for key, value in expected.items():
        if checks[key] != value:
            raise RuntimeError(
                f"B14 validation {key}={checks[key]}, expected {value}"
            )
    if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
        raise RuntimeError(f"B14 SQLite validation failed: {checks}")
    if checks["infusion_exp"] != [
        (48845, 2, 50),
        (48846, 3, 130),
        (48847, 4, 250),
    ]:
        raise RuntimeError(f"B14 infusion EXP mismatch: {checks['infusion_exp']}")
    if checks["selective_option_bands"] != [
        (47868, 8),
        (47869, 6),
        (51185, 2),
    ]:
        raise RuntimeError(
            f"B14 weapon box option mismatch: {checks['selective_option_bands']}"
        )
    if checks["merchant_good_bands"] != [
        (914119, 3),
        (914145, 5),
        (914219, 12),
    ] or checks["rank3_scroll_sold"] != 0:
        raise RuntimeError(
            f"B14 merchant stock mismatch: {checks['merchant_good_bands']}"
        )
    return checks


def main() -> None:
    args = arguments()
    evolution_tables, reactives, evolution_facts = extract_evolution(
        args.game11,
        args.base_runtime,
        args.client_compact,
    )
    skill_box_tables, box_facts = extract_skills_and_boxes(
        args.game11,
        args.client_compact,
    )
    selective_actions = extract_selective_actions(args.client_compact)
    merchants, merchant_ranges = extract_merchants(args.game11)
    quests, quest_facts = extract_quests(args.game11, args.base_runtime)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aa8-b14-") as directory:
        first = Path(directory) / "first.sqlite3"
        second = Path(directory) / "second.sqlite3"
        checks = build(
            args.base_runtime,
            first,
            evolution_tables,
            reactives,
            skill_box_tables,
            box_facts["armor_contents"],
            selective_actions,
            merchants,
            quests,
            evolution_facts["family_items"],
        )
        second_checks = build(
            args.base_runtime,
            second,
            evolution_tables,
            reactives,
            skill_box_tables,
            box_facts["armor_contents"],
            selective_actions,
            merchants,
            quests,
            evolution_facts["family_items"],
        )
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash or checks != second_checks:
            raise RuntimeError("B14 build is not deterministic")
        shutil.copyfile(first, args.output)

    manifest = {
        "phase": "B14-native-explorer-to-hiram-t1",
        "authority_order": [
            "compact-client-8.0-decrypted.sqlite",
            "game11_native",
            "x2game_confirmed",
            "server_derived_only_where_client_has_no_server_table",
        ],
        "sources": {
            "game11": {"path": str(args.game11), "sha256": sha256(args.game11)},
            "client_compact": {
                "path": str(args.client_compact),
                "sha256": sha256(args.client_compact),
            },
            "base_runtime": {
                "path": str(args.base_runtime),
                "sha256": sha256(args.base_runtime),
            },
        },
        "output": {"path": str(args.output), "sha256": sha256(args.output)},
        "validation": checks,
        "evolution": {
            "mapping_groups": [48, 49, 50],
            "family_item_count": len(evolution_facts["family_items"]),
            "category_ids": evolution_facts["category_ids"],
            "table_counts": {
                table: len(rows)
                for table, rows in sorted(evolution_tables.items())
            },
            "reactive_counts": {
                table: len(rows)
                for table, rows in sorted(reactives.items())
            },
            "source_ranges": evolution_facts["source_ranges"],
        },
        "infusions": {
            str(item_id): {"gain_exp": gain_exp, "grade": grade}
            for item_id, (gain_exp, grade) in INFUSIONS.items()
        },
        "armor_boxes": {
            str(box_id): {
                "loot_pack_id": ARMOR_LOOT_PACKS[box_id],
                "items": box_facts["armor_contents"][box_id],
                "provenance":
                    "client_compact_8 exact item description; server loot rows derived",
            }
            for box_id in ARMOR_BOXES
        },
        "weapon_boxes": [
            {
                key: value
                for key, value in action.items()
                if key != "option_rows"
            }
            for action in selective_actions
        ],
        "merchants": {
            "seller_counts": {
                kind: len(ids) for kind, ids in merchants["sellers"].items()
            },
            "seller_template_ids": merchants["sellers"],
            "runtime_pack_ids": MERCHANT_PACKS,
            "native_pack_ids": merchants["native_pack_ids"],
            "source_ranges": merchant_ranges,
            "omitted_native_pack_goods":
                "out of B14 closure; not enabled until their item definitions close",
        },
        "quests": quest_facts,
        "wrapper_and_box_ranges": box_facts["ranges"],
        "blocked_or_derived": [
            {
                "reference": "51185 selective action payload",
                "status": "server_derived",
                "reason":
                    "skill 46956 raw action collides with crafted shotgun action; "
                    "AA8 source description plus complete category 638 membership "
                    "uniquely closes bow 47790 and rifle 50799",
            },
            {
                "reference": "loot packs 12971-12982 server rows",
                "status": "server_derived",
                "reason":
                    "client has GainLootPack relation and exact seven-result "
                    "descriptions; loots table is server-only",
            },
            {
                "reference": "91 unplaced merchant templates",
                "status": "not_spawned",
                "reason": "no AA8 map/world/position/orientation source in closure",
            },
            {
                "reference": "native pack 145 rank 3 awakening scroll",
                "status": "absent_by_design",
                "reason": "AA8 general merchant does not sell item 47952",
            },
        ],
        "historical_3_0_rows": 0,
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(checks, ensure_ascii=False, sort_keys=True))
    print(manifest["output"]["sha256"])


if __name__ == "__main__":
    main()
