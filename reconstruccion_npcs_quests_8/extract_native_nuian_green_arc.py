#!/usr/bin/env python3
"""Audit the first Nuian green quest arc against Kakao AA8 game11.

This tool is intentionally read-only.  It proves the native quest graph,
extracts every concrete act row used by the graph, compares it with the
currently deployed compact, and refuses to call the arc deployable while a
native dependency (for example a doodad template/placement) is unresolved.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any


DOMAIN = Path(__file__).resolve().parent
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest330-v5.sqlite3"
)
DEFAULT_CLIENT_COMPACT = Path(r"D:\Proyectos\AAemu\client_kakao\compact.sqlite3")
DEFAULT_OUTPUT = DOMAIN / "generated" / "native-nuian-green-arc-v1-manifest.json"
AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"

EXPECTED_QUEST_IDS = {2255, 2262, 2264, 2265, 2266, 2531, 2532}


CONCRETE_SPECS: dict[str, dict[str, Any]] = {
    "quest_act_con_accept_npcs": {
        "type": "QuestActConAcceptNpc",
        "columns": "id npc_id quest_act_obj_alias_id use_alias".split(),
        "layout": "68 68 68 38".split(),
        "start": 0x6D3DC71,
        "done": 0x6D4B379,
        "rows": 3932,
    },
    "quest_act_con_accept_doodads": {
        "type": "QuestActConAcceptDoodad",
        "columns": "id doodad_id quest_act_obj_alias_id use_alias".split(),
        "layout": "68 68 68 38".split(),
        "start": 0x6D4DB06,
        "done": 0x6D50B5E,
        "rows": 884,
    },
    "quest_act_con_report_npcs": {
        "type": "QuestActConReportNpc",
        "columns": "id npc_id quest_act_obj_alias_id use_alias".split(),
        "layout": "68 68 68 38".split(),
        "start": 0x6D57198,
        "done": 0x6D6731E,
        "rows": 4709,
    },
    "quest_act_con_report_doodads": {
        "type": "QuestActConReportDoodad",
        "columns": "id doodad_id quest_act_obj_alias_id use_alias".split(),
        "layout": "68 68 68 38".split(),
        "start": 0x6D67324,
        "done": 0x6D689C8,
        "rows": 414,
    },
    "quest_act_supply_items": {
        "type": "QuestActSupplyItem",
        "columns": (
            "id cleanup count destroy_when_drop drop_when_destroy grade_id "
            "item_id show_action_bar try_equip"
        ).split(),
        "layout": "68 38 68 38 38 68 68 38 38".split(),
        "start": 0x6D6B51B,
        "done": 0x6D89A23,
        "rows": 5644,
    },
    "quest_act_supply_exps": {
        "type": "QuestActSupplyExp",
        "columns": "id exp".split(),
        "layout": "68 68".split(),
        "start": 0x6D89D77,
        "done": 0x6D93098,
        "rows": 4185,
    },
    "quest_act_supply_selective_items": {
        "type": "QuestActSupplySelectiveItem",
        "columns": "id count grade_id item_id".split(),
        "layout": "68 68 68 68".split(),
        "start": 0x6D9BD7A,
        "done": 0x6D9E222,
        "rows": 552,
    },
    "quest_act_obj_item_gathers": {
        "type": "QuestActObjItemGather",
        "columns": (
            "id cleanup count destroy_when_drop drop_when_destroy "
            "highlight_doodad_phase highlight_doodad_id item_grade_id item_id "
            "quest_act_obj_alias_id use_alias use_grade"
        ).split(),
        "layout": "68 38 68 38 38 68 68 68 68 68 38 38".split(),
        "start": 0x6D181C6,
        "done": 0x6D2DC6A,
        "rows": 2610,
    },
    "quest_act_obj_item_uses": {
        "type": "QuestActObjItemUse",
        "columns": (
            "id cinema count drop_when_destroy highlight_doodad_phase "
            "highlight_doodad_id item_id quest_act_obj_alias_id use_alias"
        ).split(),
        "layout": "68 78 68 38 68 68 68 68 38".split(),
        "start": 0x6D302A4,
        "done": 0x6D3304B,
        "rows": 403,
        "first_string_reference": None,
    },
}


DOODAD_SPECS: dict[str, dict[str, Any]] = {
    "doodad_func_quests": {
        "columns": "id quest_kind_id quest_id".split(),
        "layout": "68 68 68".split(),
        "start": 0x63AF0F4,
        "done": 0x63B4A61,
        "rows": 1761,
    },
    "doodad_funcs": {
        "columns": (
            "id act_count actual_func_type actual_func_id doodad_func_group_id "
            "forbid_on_climb func_skill_id next_phase perm_id popup_desc "
            "popup_warn reset_first_interaction sound_id"
        ).split(),
        "layout": "68 68 78 68 68 38 68 68 68 78 38 38 68".split(),
        "start": 0x64B5F4C,
        "done": 0x6603655,
        "rows": 31625,
        "first_string_reference": 288531,
    },
    "doodad_func_groups": {
        "columns": (
            "id color doodad_almighty_id doodad_func_group_kind_id icon_key "
            "is_msg_to_world is_msg_to_zone model msg_to_faction_id name "
            "over_head_mark_gap phase_msg sound_time sound_id title_color "
            "title_msg use_ui_msg"
        ).split(),
        "layout": "68 78 68 68 78 38 38 78 68 78 68 78 68 68 78 78 38".split(),
        "start": 0x66D3C1A,
        "done": 0x69D7173,
        "rows": 43792,
    },
    "doodad_almighties": {
        "columns": (
            "id childable client_doodad climate_id collide_ship collide_vehicle "
            "custom_dual_material_id delete_when_not_exist_creator "
            "despawn_on_collision faction_id force_tod_top_priority "
            "force_up_action group_id growth_time load_model_from_world mark_model "
            "max_time mgmt_spawn min_time model model_kind_id name no_collision "
            "once_one_interaction once_one_man or_unit_reqs parentable "
            "pass_through_innerside pass_through_outerside pass_update_dist "
            "percent place_area_kind_id reset_data restrict_zone_id save_indun "
            "show_minimap show_name sim_height sim_radius spawn_fx_group_id "
            "system_doodad target_decal_size use_creator_faction use_target_decal "
            "use_target_highlight use_target_silhouette view_dist_ratio"
        ).split(),
        "layout": (
            "68 38 38 68 38 38 68 38 38 68 38 38 68 68 38 78 68 38 "
            "68 78 68 78 38 38 38 38 38 38 38 38 68 68 38 68 38 38 "
            "38 68 68 68 38 60 38 38 38 38 68"
        ).split(),
        "start": 0x69E2DCB,
        "done": 0x6BC0107,
        "rows": 15290,
    },
}


def load_catalog():
    path = DOMAIN / "extract_native_npc_quest_catalog.py"
    spec = importlib.util.spec_from_file_location("native_catalog", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_sha256(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            json.dumps(
                row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        )
        digest.update(b"\n")
    return digest.hexdigest().upper()


def decode_rows(reader_type, data: bytes, name: str, spec: dict[str, Any]):
    columns = list(spec["columns"])
    layout = list(spec["layout"])
    if len(columns) != len(layout):
        raise RuntimeError(f"{name}: columns/layout mismatch")
    reader = reader_type(data, spec.get("first_string_reference"))
    cursor = int(spec["start"])
    rows: list[dict[str, Any]] = []
    while cursor < len(data) and data[cursor] == 100:
        values, cursor = reader.row(cursor, layout)
        rows.append(dict(zip(columns, values)))
    if cursor != int(spec["done"]) or data[cursor] != 101:
        raise RuntimeError(
            f"{name}: expected SQLITE_DONE at 0x{spec['done']:X}, "
            f"found 0x{cursor:X}"
        )
    if len(rows) != int(spec["rows"]):
        raise RuntimeError(
            f"{name}: expected {spec['rows']} rows, found {len(rows)}"
        )
    ids = [int(row["id"]) for row in rows]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise RuntimeError(f"{name}: IDs are not sorted and unique")
    evidence = {
        "cached_result": {
            "start_hex": f"0x{spec['start']:X}",
            "done_hex": f"0x{spec['done']:X}",
            "row_count": len(rows),
            "id_min": min(ids),
            "id_max": max(ids),
            "canonical_rows_sha256": canonical_sha256(rows),
        },
        "columns": columns,
        "layout": layout,
    }
    return rows, evidence


def select_native_graph(catalog, game11: bytes):
    decoded: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for table in ("quest_contexts", "quest_components", "quest_acts"):
        decoded[table], evidence[table] = decode_rows(
            catalog.CachedResultReader, game11, table, catalog.TABLE_SPECS[table]
        )

    contexts = [
        row
        for row in decoded["quest_contexts"]
        if int(row["category_id"]) == 3
        and int(row["race"]) == 1
        and int(row["zone_id"]) == 9
    ]
    quest_ids = {int(row["id"]) for row in contexts}
    if quest_ids != EXPECTED_QUEST_IDS:
        raise RuntimeError(
            "native Nuian green arc changed: "
            f"expected {sorted(EXPECTED_QUEST_IDS)}, found {sorted(quest_ids)}"
        )
    components = [
        row
        for row in decoded["quest_components"]
        if int(row["quest_context_id"]) in quest_ids
    ]
    component_ids = {int(row["id"]) for row in components}
    acts = [
        row
        for row in decoded["quest_acts"]
        if int(row["quest_component_id"]) in component_ids
    ]
    if (len(contexts), len(components), len(acts)) != (7, 25, 40):
        raise RuntimeError(
            "native Nuian green arc structural count changed: "
            f"{len(contexts)} contexts, {len(components)} components, {len(acts)} acts"
        )
    return {
        "quest_contexts": contexts,
        "quest_components": components,
        "quest_acts": acts,
    }, evidence


def select_concrete_rows(catalog, game11: bytes, acts: list[dict[str, Any]]):
    detail_ids_by_type: dict[str, set[int]] = {}
    for act in acts:
        detail_ids_by_type.setdefault(str(act["act_detail_type"]), set()).add(
            int(act["act_detail_id"])
        )

    known_types = {spec["type"] for spec in CONCRETE_SPECS.values()}
    unsupported = sorted(set(detail_ids_by_type) - known_types)
    if unsupported:
        raise RuntimeError(f"arc uses unclassified act types: {unsupported}")

    selected: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for table, spec in CONCRETE_SPECS.items():
        rows, table_evidence = decode_rows(
            catalog.CachedResultReader, game11, table, spec
        )
        wanted = detail_ids_by_type.get(spec["type"], set())
        chosen = [row for row in rows if int(row["id"]) in wanted]
        found = {int(row["id"]) for row in chosen}
        if found != wanted:
            raise RuntimeError(
                f"{table}: missing native details {sorted(wanted - found)}"
            )
        selected[table] = chosen
        table_evidence["selected_ids"] = sorted(wanted)
        table_evidence["selected_rows_sha256"] = canonical_sha256(chosen)
        evidence[table] = table_evidence
    return selected, evidence


def select_doodad_closure(
    catalog,
    game11: bytes,
    concrete: dict[str, list[dict[str, Any]]],
):
    decoded: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, dict[str, Any]] = {}
    for table, spec in DOODAD_SPECS.items():
        decoded[table], evidence[table] = decode_rows(
            catalog.CachedResultReader, game11, table, spec
        )

    doodad_ids = {
        int(row["doodad_id"])
        for table in (
            "quest_act_con_accept_doodads",
            "quest_act_con_report_doodads",
        )
        for row in concrete[table]
        if not int(row["use_alias"])
    }
    almighties = [
        row
        for row in decoded["doodad_almighties"]
        if int(row["id"]) in doodad_ids
    ]
    found_doodads = {int(row["id"]) for row in almighties}
    if found_doodads != doodad_ids:
        raise RuntimeError(
            "native doodad templates missing: "
            f"{sorted(doodad_ids - found_doodads)}"
        )

    groups = [
        row
        for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in doodad_ids
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        row
        for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    quest_func_ids = {
        int(row["actual_func_id"])
        for row in funcs
        if row["actual_func_type"] == "DoodadFuncQuest"
    }
    quest_funcs = [
        row
        for row in decoded["doodad_func_quests"]
        if int(row["id"]) in quest_func_ids
    ]
    found_quest_funcs = {int(row["id"]) for row in quest_funcs}
    if found_quest_funcs != quest_func_ids:
        raise RuntimeError(
            "native doodad quest functions missing: "
            f"{sorted(quest_func_ids - found_quest_funcs)}"
        )

    selected = {
        "doodad_almighties": almighties,
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_quests": quest_funcs,
    }
    for table, rows in selected.items():
        evidence[table]["selected_ids"] = sorted(int(row["id"]) for row in rows)
        evidence[table]["selected_rows_sha256"] = canonical_sha256(rows)

    marian = next(row for row in almighties if int(row["id"]) == 14074)
    marian_groups = [
        row
        for row in groups
        if int(row["doodad_almighty_id"]) == 14074
    ]
    marian_proxy = [
        row
        for row in marian_groups
        if row["model"] == "npctype://10581"
    ]
    marian_report = [
        row
        for row in quest_funcs
        if int(row["id"]) == 1508
        and int(row["quest_kind_id"]) == 2
        and int(row["quest_id"]) == 2532
    ]
    if (
        int(marian["client_doodad"]) != 1
        or len(marian_proxy) != 1
        or len(marian_report) != 1
    ):
        raise RuntimeError("native Marian client-doodad closure changed")

    return selected, evidence, {
        "doodad_id": 14074,
        "client_doodad": 1,
        "npc_proxy_model": "npctype://10581",
        "npc_template_id": 10581,
        "quest_func": marian_report[0],
        "classification": (
            "AA8 client-side logical doodad backed by Marian's NPC model; "
            "not an ordinary standalone world prop."
        ),
    }


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    ]


def fetch_by_ids(
    connection: sqlite3.Connection, table: str, ids: set[int]
) -> list[dict[str, Any]]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    connection.row_factory = sqlite3.Row
    return [
        dict(row)
        for row in connection.execute(
            f'SELECT * FROM "{table}" WHERE id IN ({placeholders}) ORDER BY id',
            sorted(ids),
        )
    ]


def normalize(value: Any) -> Any:
    if isinstance(value, bool):
        return int(value)
    return value


def compare_rows(
    native: list[dict[str, Any]],
    runtime: list[dict[str, Any]],
    native_columns: list[str],
    runtime_columns: list[str],
):
    native_by_id = {int(row["id"]): row for row in native}
    runtime_by_id = {int(row["id"]): row for row in runtime}
    common_columns = [
        column
        for column in native_columns
        if column in runtime_columns
    ]
    differences: list[dict[str, Any]] = []
    for row_id in sorted(set(native_by_id) & set(runtime_by_id)):
        fields = {
            column: {
                "native": native_by_id[row_id][column],
                "runtime": runtime_by_id[row_id][column],
            }
            for column in common_columns
            if normalize(native_by_id[row_id][column])
            != normalize(runtime_by_id[row_id][column])
        }
        if fields:
            differences.append({"id": row_id, "fields": fields})
    return {
        "native_ids": sorted(native_by_id),
        "runtime_ids": sorted(runtime_by_id),
        "missing_native_ids_in_runtime": sorted(set(native_by_id) - set(runtime_by_id)),
        "runtime_only_ids_in_scope": sorted(set(runtime_by_id) - set(native_by_id)),
        "native_only_columns": sorted(set(native_columns) - set(runtime_columns)),
        "runtime_only_columns": sorted(set(runtime_columns) - set(native_columns)),
        "row_differences": differences,
        "matches": (
            set(native_by_id) == set(runtime_by_id)
            and not differences
            and not (set(native_columns) - set(runtime_columns))
        ),
    }


def compare_runtime(
    runtime_path: Path,
    graph: dict[str, list[dict[str, Any]]],
    concrete: dict[str, list[dict[str, Any]]],
    doodad_closure: dict[str, list[dict[str, Any]]],
):
    connection = sqlite3.connect(
        f"file:{runtime_path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        quest_ids = {int(row["id"]) for row in graph["quest_contexts"]}
        component_ids = {int(row["id"]) for row in graph["quest_components"]}
        runtime_contexts = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM quest_contexts WHERE id IN "
                f"({','.join('?' for _ in quest_ids)}) ORDER BY id",
                sorted(quest_ids),
            )
        ]
        runtime_components = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM quest_components WHERE quest_context_id IN "
                f"({','.join('?' for _ in quest_ids)}) ORDER BY id",
                sorted(quest_ids),
            )
        ]
        runtime_acts = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM quest_acts WHERE quest_component_id IN "
                f"({','.join('?' for _ in component_ids)}) ORDER BY id",
                sorted(component_ids),
            )
        ]

        comparisons: dict[str, Any] = {}
        runtime_core = {
            "quest_contexts": runtime_contexts,
            "quest_components": runtime_components,
            "quest_acts": runtime_acts,
        }
        for table, native_rows in graph.items():
            comparisons[table] = compare_rows(
                native_rows,
                runtime_core[table],
                list(native_rows[0]),
                table_columns(connection, table),
            )
        for table, native_rows in concrete.items():
            native_columns = list(CONCRETE_SPECS[table]["columns"])
            runtime_columns = table_columns(connection, table)
            runtime_rows = fetch_by_ids(
                connection, table, {int(row["id"]) for row in native_rows}
            )
            comparisons[table] = compare_rows(
                native_rows, runtime_rows, native_columns, runtime_columns
            )
        doodad_comparisons: dict[str, Any] = {}
        for table, native_rows in doodad_closure.items():
            native_columns = list(DOODAD_SPECS[table]["columns"])
            runtime_columns = table_columns(connection, table)
            runtime_rows = fetch_by_ids(
                connection, table, {int(row["id"]) for row in native_rows}
            )
            doodad_comparisons[table] = compare_rows(
                native_rows, runtime_rows, native_columns, runtime_columns
            )

        npc_ids = {
            int(row["npc_id"])
            for table in (
                "quest_act_con_accept_npcs",
                "quest_act_con_report_npcs",
            )
            for row in concrete[table]
            if not int(row["use_alias"])
        }
        doodad_ids = {
            int(row["doodad_id"])
            for table in (
                "quest_act_con_accept_doodads",
                "quest_act_con_report_doodads",
            )
            for row in concrete[table]
            if not int(row["use_alias"])
        }
        present_npcs = {
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM npcs WHERE id IN "
                f"({','.join('?' for _ in npc_ids)})",
                sorted(npc_ids),
            )
        }
        present_doodads = {
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM doodad_almighties WHERE id IN "
                f"({','.join('?' for _ in doodad_ids)})",
                sorted(doodad_ids),
            )
        }

        native_2532 = [
            row
            for row in graph["quest_acts"]
            if int(row["quest_component_id"]) in {10965, 10966, 10967}
        ]
        runtime_2532 = [
            row
            for row in runtime_acts
            if int(row["quest_component_id"]) in {10965, 10966, 10967}
        ]
        return {
            "path": str(runtime_path),
            "sha256": file_sha256(runtime_path),
            "tables": comparisons,
            "doodad_tables": doodad_comparisons,
            "dependency_closure": {
                "native_npc_ids": sorted(npc_ids),
                "missing_npc_template_ids": sorted(npc_ids - present_npcs),
                "native_doodad_ids": sorted(doodad_ids),
                "missing_doodad_template_ids": sorted(doodad_ids - present_doodads),
            },
            "quest_2532_proof": {
                "native_acts": native_2532,
                "runtime_acts": runtime_2532,
                "conclusion": (
                    "AA8 requires QuestActConReportDoodad detail 163 "
                    "(doodad 14074); the historical runtime substitutes "
                    "QuestActConReportNpc detail 2301 (Marian 10581)."
                ),
            },
        }
    finally:
        connection.close()


def quest_summaries(
    graph: dict[str, list[dict[str, Any]]],
    concrete: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    detail_lookup = {
        (spec["type"], int(row["id"])): row
        for table, spec in CONCRETE_SPECS.items()
        for row in concrete[table]
    }
    components_by_quest: dict[int, list[dict[str, Any]]] = {}
    for row in graph["quest_components"]:
        components_by_quest.setdefault(int(row["quest_context_id"]), []).append(row)
    acts_by_component: dict[int, list[dict[str, Any]]] = {}
    for row in graph["quest_acts"]:
        acts_by_component.setdefault(int(row["quest_component_id"]), []).append(row)

    result: list[dict[str, Any]] = []
    for context in sorted(graph["quest_contexts"], key=lambda row: int(row["quest_idx"])):
        components: list[dict[str, Any]] = []
        for component in sorted(
            components_by_quest[int(context["id"])],
            key=lambda row: int(row["id"]),
        ):
            acts = []
            for act in acts_by_component.get(int(component["id"]), []):
                key = (str(act["act_detail_type"]), int(act["act_detail_id"]))
                acts.append({**act, "detail": detail_lookup[key]})
            components.append({**component, "acts": acts})
        result.append({"context": context, "components": components})
    return result


def audit_item_closure(
    runtime_path: Path,
    client_compact: Path,
    concrete: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    item_ids = {
        int(row["item_id"])
        for rows in concrete.values()
        for row in rows
        if "item_id" in row and int(row["item_id"]) > 0
    }
    result: dict[str, Any] = {"native_quest_item_ids": sorted(item_ids)}
    for label, path in (
        ("runtime", runtime_path),
        ("aa8_client_compact", client_compact),
    ):
        connection = sqlite3.connect(
            f"file:{path.resolve().as_posix()}?mode=ro", uri=True
        )
        try:
            found = {
                int(row[0])
                for row in connection.execute(
                    "SELECT id FROM items WHERE id IN "
                    f"({','.join('?' for _ in item_ids)})",
                    sorted(item_ids),
                )
            }
        finally:
            connection.close()
        result[label] = {
            "path": str(path),
            "sha256": file_sha256(path),
            "present_ids": sorted(found),
            "missing_ids": sorted(item_ids - found),
        }
    runtime_ids = set(result["runtime"]["present_ids"])
    client_ids = set(result["aa8_client_compact"]["present_ids"])
    result["unresolved_ids"] = sorted(item_ids - runtime_ids - client_ids)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument(
        "--client-compact", type=Path, default=DEFAULT_CLIENT_COMPACT
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    options = parser.parse_args()
    if not options.game11.is_file():
        raise FileNotFoundError(options.game11)
    if not options.runtime.is_file():
        raise FileNotFoundError(options.runtime)
    if not options.client_compact.is_file():
        raise FileNotFoundError(options.client_compact)

    catalog = load_catalog()
    game11 = options.game11.read_bytes()
    graph, core_evidence = select_native_graph(catalog, game11)
    concrete, concrete_evidence = select_concrete_rows(
        catalog, game11, graph["quest_acts"]
    )
    doodad_closure, doodad_evidence, marian_client_doodad = (
        select_doodad_closure(catalog, game11, concrete)
    )
    runtime = compare_runtime(
        options.runtime, graph, concrete, doodad_closure
    )
    item_closure = audit_item_closure(
        options.runtime, options.client_compact, concrete
    )
    runtime["item_closure"] = item_closure

    schema_gaps = {
        table: comparison["native_only_columns"]
        for table, comparison in {
            **runtime["tables"],
            **runtime["doodad_tables"],
        }.items()
        if comparison["native_only_columns"]
    }
    structural_mismatches = [
        table
        for table, comparison in {
            **runtime["tables"],
            **runtime["doodad_tables"],
        }.items()
        if not comparison["matches"]
    ]
    blockers: list[str] = []
    missing_doodads = runtime["dependency_closure"]["missing_doodad_template_ids"]
    if missing_doodads:
        blockers.append(
            "Native doodad templates/functions/placements are not closed: "
            + ", ".join(map(str, missing_doodads))
        )
    if schema_gaps:
        blockers.append(
            "Runtime schema cannot preserve every AA8-native quest-act field."
        )
    if structural_mismatches:
        blockers.append(
            "Historical runtime rows diverge from the native graph and concrete acts."
        )
    if item_closure["runtime"]["missing_ids"]:
        blockers.append(
            "Quest item templates are absent from the runtime: "
            + ", ".join(map(str, item_closure["runtime"]["missing_ids"]))
        )
    if item_closure["unresolved_ids"]:
        blockers.append(
            "Quest item templates remain unresolved after combining the "
            "runtime and AA8 client compact: "
            + ", ".join(map(str, item_closure["unresolved_ids"]))
        )

    manifest = {
        "format_version": 1,
        "phase": "native-nuian-green-arc-v1",
        "authority": AUTHORITY,
        "sources": {
            "game11": {
                "path": str(options.game11),
                "sha256": file_sha256(options.game11),
            },
            "runtime_comparison_only": {
                "path": str(options.runtime),
                "sha256": file_sha256(options.runtime),
            },
            "aa8_client_compact": {
                "path": str(options.client_compact),
                "sha256": file_sha256(options.client_compact),
            },
        },
        "selection": {
            "predicate": "category_id=3, race=1, zone_id=9",
            "quest_ids": sorted(EXPECTED_QUEST_IDS),
            "counts": {
                "quest_contexts": len(graph["quest_contexts"]),
                "quest_components": len(graph["quest_components"]),
                "quest_acts": len(graph["quest_acts"]),
            },
        },
        "native_quest_graph": quest_summaries(graph, concrete),
        "native_evidence": {
            "core_tables": core_evidence,
            "concrete_tables": concrete_evidence,
            "doodad_tables": doodad_evidence,
        },
        "native_doodad_closure": doodad_closure,
        "marian_client_doodad_proof": marian_client_doodad,
        "runtime_comparison": runtime,
        "deployment_gate": {
            "deployable": not blockers,
            "blockers": blockers,
            "schema_gaps": schema_gaps,
            "mismatching_tables": structural_mismatches,
            "policy": (
                "Do not rewrite the live compact until every native dependency "
                "used by this arc is present and validated."
            ),
        },
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {options.output} "
        f"(deployable={manifest['deployment_gate']['deployable']}, "
        f"mismatches={len(structural_mismatches)}, blockers={len(blockers)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
