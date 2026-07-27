#!/usr/bin/env python3
"""Extract the AA8-native quest 2256 and Bloodhand Corpse closure.

Quest 2257 is decoded as adjacent evidence because the same client doodad
offers it.  It is deliberately excluded from the deployable subset until its
interaction-skill and quest-item closure is reconstructed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any


DOMAIN = Path(__file__).resolve().parent
DEFAULT_GAME11 = Path(r"E:\AAEmu-Research\output\compact-8.0-extracted\game11")
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v2.sqlite3"
)
DEFAULT_OUTPUT = (
    DOMAIN / "generated" / "native-quest-2256-client-doodad-v1-manifest.json"
)
AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
QUEST_IDS = {2256, 2257}
DEPLOYED_QUEST_ID = 2256
DOODAD_ID = 14073

OBJ_INTERACTION_SPEC = {
    "type": "QuestActObjInteraction",
    "columns": (
        "id count doodad_id highlight_doodad_phase highlight_doodad_id phase "
        "quest_act_obj_alias_id quest_doodad_group_id team_share use_alias wi_id"
    ).split(),
    "layout": "68 68 68 68 68 68 68 68 38 38 68".split(),
    "start": 0x6D33051,
    "done": 0x6D396B1,
    "rows": 672,
}


def load_green_extractor():
    path = DOMAIN / "extract_native_nuian_green_arc.py"
    spec = importlib.util.spec_from_file_location("green_arc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def select_graph(green, catalog, game11: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    decoded: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table in ("quest_contexts", "quest_components", "quest_acts"):
        decoded[table], evidence[table] = green.decode_rows(
            catalog.CachedResultReader,
            game11,
            table,
            catalog.TABLE_SPECS[table],
        )

    contexts = [
        row for row in decoded["quest_contexts"] if int(row["id"]) in QUEST_IDS
    ]
    if {int(row["id"]) for row in contexts} != QUEST_IDS:
        raise RuntimeError("native quest 2256/2257 contexts changed")
    component_ids = {
        int(row["id"])
        for row in decoded["quest_components"]
        if int(row["quest_context_id"]) in QUEST_IDS
    }
    components = [
        row
        for row in decoded["quest_components"]
        if int(row["id"]) in component_ids
    ]
    acts = [
        row
        for row in decoded["quest_acts"]
        if int(row["quest_component_id"]) in component_ids
    ]
    if (len(contexts), len(components), len(acts)) != (2, 8, 11):
        raise RuntimeError(
            "native quest 2256/2257 graph changed: "
            f"{len(contexts)} contexts, {len(components)} components, "
            f"{len(acts)} acts"
        )
    return {
        "quest_contexts": contexts,
        "quest_components": components,
        "quest_acts": acts,
    }, evidence


def select_concrete(green, catalog, game11: bytes, acts: list[dict[str, Any]]):
    specs = dict(green.CONCRETE_SPECS)
    specs["quest_act_obj_interactions"] = OBJ_INTERACTION_SPEC
    wanted: dict[str, set[int]] = {}
    for act in acts:
        wanted.setdefault(str(act["act_detail_type"]), set()).add(
            int(act["act_detail_id"])
        )
    known = {str(spec["type"]) for spec in specs.values()}
    if set(wanted) - known:
        raise RuntimeError(f"unclassified quest acts: {sorted(set(wanted) - known)}")

    selected: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table, spec in specs.items():
        rows, table_evidence = green.decode_rows(
            catalog.CachedResultReader, game11, table, spec
        )
        ids = wanted.get(str(spec["type"]), set())
        chosen = [row for row in rows if int(row["id"]) in ids]
        if {int(row["id"]) for row in chosen} != ids:
            raise RuntimeError(f"{table}: native detail rows are incomplete")
        selected[table] = chosen
        table_evidence["selected_ids"] = sorted(ids)
        table_evidence["selected_rows_sha256"] = green.canonical_sha256(chosen)
        evidence[table] = table_evidence
    return selected, evidence, specs


def select_doodad(green, catalog, game11: bytes):
    decoded: dict[str, list[dict[str, Any]]] = {}
    evidence: dict[str, Any] = {}
    for table, spec in green.DOODAD_SPECS.items():
        decoded[table], evidence[table] = green.decode_rows(
            catalog.CachedResultReader, game11, table, spec
        )

    almighties = [
        row for row in decoded["doodad_almighties"] if int(row["id"]) == DOODAD_ID
    ]
    groups = [
        row
        for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) == DOODAD_ID
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
    if len(almighties) != 1:
        raise RuntimeError("native Bloodhand Corpse doodad is missing")
    if {int(row["id"]) for row in groups} != {41492, 41493, 41494}:
        raise RuntimeError("native Bloodhand Corpse phase groups changed")
    if {int(row["id"]) for row in funcs} != {38376, 38377, 38382}:
        raise RuntimeError("native Bloodhand Corpse functions changed")
    if {int(row["id"]) for row in quest_funcs} != {1507, 1512}:
        raise RuntimeError("native Bloodhand Corpse quest functions changed")

    start = next(row for row in groups if int(row["id"]) == 41492)
    if (
        int(almighties[0]["client_doodad"]) != 1
        or start["model"] != "npctype://10646"
        or int(start["doodad_func_group_kind_id"]) != 1
        or int(almighties[0]["use_target_highlight"]) != 1
    ):
        raise RuntimeError("Bloodhand Corpse client-doodad proxy changed")

    full = {
        "doodad_almighties": almighties,
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_quests": quest_funcs,
    }
    safe = {
        "doodad_almighties": almighties,
        "doodad_func_groups": [start],
        "doodad_funcs": [
            row for row in funcs if int(row["id"]) == 38382
        ],
        "doodad_func_quests": [
            row for row in quest_funcs if int(row["id"]) == 1512
        ],
    }
    for table, rows in full.items():
        evidence[table]["selected_ids"] = sorted(int(row["id"]) for row in rows)
        evidence[table]["selected_rows_sha256"] = green.canonical_sha256(rows)
    return full, safe, evidence


def quest_summary(
    graph: dict[str, list[dict[str, Any]]],
    concrete: dict[str, list[dict[str, Any]]],
    specs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    by_type = {
        (str(spec["type"]), int(row["id"])): row
        for table, spec in specs.items()
        for row in concrete[table]
    }
    components_by_quest: dict[int, list[dict[str, Any]]] = {}
    for component in graph["quest_components"]:
        components_by_quest.setdefault(
            int(component["quest_context_id"]), []
        ).append(component)
    acts_by_component: dict[int, list[dict[str, Any]]] = {}
    for act in graph["quest_acts"]:
        acts_by_component.setdefault(int(act["quest_component_id"]), []).append(act)

    result: list[dict[str, Any]] = []
    for context in sorted(graph["quest_contexts"], key=lambda row: int(row["id"])):
        components = []
        for component in sorted(
            components_by_quest[int(context["id"])],
            key=lambda row: int(row["id"]),
        ):
            acts = []
            for act in acts_by_component.get(int(component["id"]), []):
                key = (str(act["act_detail_type"]), int(act["act_detail_id"]))
                acts.append({**act, "detail": by_type[key]})
            components.append({**component, "acts": acts})
        result.append({"context": context, "components": components})
    return result


def runtime_comparison(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        current_2256 = [
            dict(row)
            for row in connection.execute(
                "SELECT qa.* FROM quest_acts qa "
                "JOIN quest_components qc ON qc.id=qa.quest_component_id "
                "WHERE qc.quest_context_id=2256 ORDER BY qa.id"
            )
        ]
        missing_2257 = {
            "item_templates": [
                item_id
                for item_id in (16287,)
                if connection.execute(
                    "SELECT 1 FROM items WHERE id=?", (item_id,)
                ).fetchone()
                is None
            ],
            "skill_effect_ids": [
                effect_id
                for effect_id in (59150, 59152)
                if connection.execute(
                    "SELECT 1 FROM skill_effects WHERE id=?", (effect_id,)
                ).fetchone()
                is None
            ],
            "effect_ids": [
                effect_id
                for effect_id in (77705, 77710)
                if connection.execute(
                    "SELECT 1 FROM effects WHERE id=?", (effect_id,)
                ).fetchone()
                is None
            ],
        }
        reward_coverage = [
            dict(row)
            for row in connection.execute(
                "SELECT item_id,concrete_type,coverage,missing_dependencies,"
                "provenance FROM aaemu_item_definition_coverage "
                "WHERE item_id=18791"
            )
        ]
    finally:
        connection.close()
    return {
        "path": str(path),
        "sha256": load_green_extractor().file_sha256(path),
        "historical_quest_2256_acts": current_2256,
        "quest_2256_reward_coverage": reward_coverage,
        "quest_2257_missing_runtime_dependencies": missing_2257,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    options = parser.parse_args()
    for path in (options.game11, options.runtime):
        if not path.is_file():
            raise FileNotFoundError(path)

    green = load_green_extractor()
    catalog = green.load_catalog()
    game11 = options.game11.read_bytes()
    graph, graph_evidence = select_graph(green, catalog, game11)
    concrete, concrete_evidence, specs = select_concrete(
        green, catalog, game11, graph["quest_acts"]
    )
    full_doodad, safe_doodad, doodad_evidence = select_doodad(
        green, catalog, game11
    )
    summaries = quest_summary(graph, concrete, specs)
    deployed_graph = [
        quest
        for quest in summaries
        if int(quest["context"]["id"]) == DEPLOYED_QUEST_ID
    ]

    manifest = {
        "format_version": 1,
        "phase": "native-quest-2256-client-doodad-v1",
        "authority": AUTHORITY,
        "sources": {
            "game11": {
                "path": str(options.game11),
                "sha256": green.file_sha256(options.game11),
            },
            "runtime_comparison_only": runtime_comparison(options.runtime),
            "visible_behavior_corroboration": {
                "quest": "https://wiki.archerage.to/na-en/db/quests/2256",
                "object": "https://wiki.archerage.to/na-en/db/doodads/14073",
                "authority": "corroboration_only",
            },
        },
        "native_quest_graph": summaries,
        "deployable_quest_graph": deployed_graph,
        "native_doodad_closure": full_doodad,
        "deployable_doodad_subset": safe_doodad,
        "native_evidence": {
            "quest_tables": graph_evidence,
            "concrete_tables": concrete_evidence,
            "doodad_tables": doodad_evidence,
        },
        "proof": {
            "quest_2256": (
                "AcceptDoodad 14074 (Marian) -> ReportDoodad 14073 "
                "(Bloodhand Corpse) -> 1800 EXP + item 18791 x5"
            ),
            "client_doodad_14073": {
                "client_doodad": 1,
                "npc_proxy_model": "npctype://10646",
                "npc_proxy_group_kind": "Start",
                "use_target_highlight": 1,
                "quest_completion_function": 1512,
            },
            "same_name_decorations": (
                "Only NPC template 10646 is replaced. NPC template 11544 "
                "remains decorative."
            ),
        },
        "deployment_gate": {
            "deployable_quest_ids": [2256],
            "suppressed_adjacent_quest_ids": [2257],
            "suppressed_doodad_func_ids": [38376, 38377],
            "reason": (
                "Quest 2257 shares doodad 14073 but its AA8 interaction skill "
                "41925, effects 77705/77710, concrete effects and quest item "
                "16287 are not yet closed in the current runtime."
            ),
        },
    }
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
