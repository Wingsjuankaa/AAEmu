#!/usr/bin/env python3
"""Build the AA8-native quest 2256/client-doodad runtime (green arc V3)."""

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
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-quest-2256-client-doodad-v1-manifest.json"
)
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v2.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v3.sqlite3"
)
DEFAULT_BUILD_MANIFEST = (
    DOMAIN
    / "generated"
    / "native-quest-2256-client-doodad-v1-runtime-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "98E0AB85FABDBD38CFD46B0DED19447E8DCC3D2EE384A6C2DE967628A67CA69C"
)
QUEST_ID = 2256
COMPONENT_IDS = {10362, 10364, 10366}
ACT_IDS = {63974, 63975, 64096, 65624}


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


def flatten(graph: list[dict[str, Any]]):
    contexts: list[dict[str, Any]] = []
    components: list[dict[str, Any]] = []
    acts: list[dict[str, Any]] = []
    concrete: dict[str, dict[int, dict[str, Any]]] = {}
    for quest in graph:
        contexts.append(dict(quest["context"]))
        for component_with_acts in quest["components"]:
            components.append(
                {
                    key: value
                    for key, value in component_with_acts.items()
                    if key != "acts"
                }
            )
            for act_with_detail in component_with_acts["acts"]:
                detail = dict(act_with_detail["detail"])
                act = {
                    key: value
                    for key, value in act_with_detail.items()
                    if key != "detail"
                }
                acts.append(act)
                concrete.setdefault(str(act["act_detail_type"]), {})[
                    int(detail["id"])
                ] = detail
    return contexts, components, acts, concrete


def validate_output(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    actual_acts = [
        tuple(row)
        for row in connection.execute(
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE quest_component_id IN (10362,10364,10366) "
            "ORDER BY id"
        )
    ]
    expected_acts = [
        (63974, "QuestActConAcceptDoodad", 797, 10362),
        (63975, "QuestActConReportDoodad", 165, 10364),
        (64096, "QuestActSupplyExp", 3926, 10366),
        (65624, "QuestActSupplyItem", 8874, 10366),
    ]
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0],
        "quest_2256_acts": actual_acts,
        "accept_doodad": tuple(
            connection.execute(
                "SELECT doodad_id,use_alias FROM quest_act_con_accept_doodads "
                "WHERE id=797"
            ).fetchone()
        ),
        "report_doodad": tuple(
            connection.execute(
                "SELECT doodad_id,quest_act_obj_alias_id,use_alias "
                "FROM quest_act_con_report_doodads WHERE id=165"
            ).fetchone()
        ),
        "reward_exp": tuple(
            connection.execute(
                "SELECT exp FROM quest_act_supply_exps WHERE id=3926"
            ).fetchone()
        ),
        "reward_item": tuple(
            connection.execute(
                "SELECT item_id,count FROM quest_act_supply_items WHERE id=8874"
            ).fetchone()
        ),
        "corpse_doodad": tuple(
            connection.execute(
                "SELECT client_doodad,show_name,use_target_highlight,"
                "once_one_interaction,once_one_man "
                "FROM doodad_almighties WHERE id=14073"
            ).fetchone()
        ),
        "corpse_proxy_group": tuple(
            connection.execute(
                "SELECT id,doodad_func_group_kind_id,model "
                "FROM doodad_func_groups WHERE id=41492"
            ).fetchone()
        ),
        "corpse_complete_func": tuple(
            connection.execute(
                "SELECT df.id,df.actual_func_id,df.next_phase,q.quest_kind_id,"
                "q.quest_id FROM doodad_funcs df "
                "JOIN doodad_func_quests q ON q.id=df.actual_func_id "
                "WHERE df.id=38382"
            ).fetchone()
        ),
        "quest_2257_functions_suppressed": connection.execute(
            "SELECT COUNT(*) FROM doodad_funcs WHERE id IN (38376,38377)"
        ).fetchone()[0],
        "reward_item_coverage": tuple(
            connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies "
                "FROM aaemu_item_definition_coverage WHERE item_id=18791"
            ).fetchone()
        ),
    }
    expected = {
        "quest_2256_acts": expected_acts,
        "accept_doodad": (14074, 0),
        "report_doodad": (14073, 6695, 1),
        "reward_exp": (1800,),
        "reward_item": (18791, 5),
        "corpse_doodad": (1, 1, 1, 1, 1),
        "corpse_proxy_group": (41492, 1, "npctype://10646"),
        "corpse_complete_func": (38382, 1512, -1, 2, 2256),
        "quest_2257_functions_suppressed": 0,
        "reward_item_coverage": ("generic", "complete", ""),
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
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--build-manifest", type=Path, default=DEFAULT_BUILD_MANIFEST
    )
    options = parser.parse_args()
    for path in (options.manifest, options.base_runtime):
        if not path.is_file():
            raise FileNotFoundError(path)
    if sha256(options.base_runtime) != EXPECTED_BASE_SHA256:
        raise RuntimeError("base V2 runtime differs from the validated input")

    forensic = json.loads(options.manifest.read_text(encoding="utf-8"))
    if forensic["deployment_gate"]["deployable_quest_ids"] != [QUEST_ID]:
        raise RuntimeError("forensic manifest does not authorize quest 2256")
    contexts, components, acts, concrete_by_type = flatten(
        forensic["deployable_quest_graph"]
    )
    if {int(row["id"]) for row in contexts} != {QUEST_ID}:
        raise RuntimeError("unexpected quest contexts in deployable graph")
    if {int(row["id"]) for row in components} != COMPONENT_IDS:
        raise RuntimeError("quest 2256 component IDs changed")
    if {int(row["id"]) for row in acts} != ACT_IDS:
        raise RuntimeError("quest 2256 act IDs changed")

    green = load_module(
        "green_builder", DOMAIN / "build_native_nuian_green_arc_runtime.py"
    )
    extractor = load_module(
        "quest2256_extractor", DOMAIN / "extract_native_quest_2256.py"
    )
    green_extractor = load_module(
        "green_extractor", DOMAIN / "extract_native_nuian_green_arc.py"
    )
    specs = dict(green_extractor.CONCRETE_SPECS)
    specs["quest_act_obj_interactions"] = extractor.OBJ_INTERACTION_SPEC
    table_by_type = {
        str(spec["type"]): table for table, spec in specs.items()
    }
    concrete = {
        table_by_type[detail_type]: list(rows.values())
        for detail_type, rows in concrete_by_type.items()
    }
    doodads = forensic["deployable_doodad_subset"]

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.build_manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    additions: dict[str, list[str]] = {}
    fallbacks: list[dict[str, Any]] = []
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        for table, spec in specs.items():
            added = green.ensure_columns(
                connection, table, list(spec["columns"]), list(spec["layout"])
            )
            if added:
                additions[table] = added
        for table, spec in green_extractor.DOODAD_SPECS.items():
            added = green.ensure_columns(
                connection, table, list(spec["columns"]), list(spec["layout"])
            )
            if added:
                additions[table] = added

        contexts, cleaned = green.sanitize_unresolved_strings(
            connection, "quest_contexts", contexts
        )
        fallbacks.extend(cleaned)
        connection.execute(
            "DELETE FROM quest_acts WHERE quest_component_id IN "
            "(10362,10364,10366)"
        )
        green.replace_rows(connection, "quest_contexts", contexts)
        green.replace_rows(connection, "quest_components", components)
        green.replace_rows(connection, "quest_acts", acts)
        for table, rows in concrete.items():
            rows, cleaned = green.sanitize_unresolved_strings(
                connection, table, rows
            )
            fallbacks.extend(cleaned)
            green.replace_rows(connection, table, rows)
        for table in (
            "doodad_almighties",
            "doodad_func_groups",
            "doodad_funcs",
            "doodad_func_quests",
        ):
            rows, cleaned = green.sanitize_unresolved_strings(
                connection, table, list(doodads[table])
            )
            fallbacks.extend(cleaned)
            green.replace_rows(connection, table, rows)

        connection.execute(
            "DELETE FROM doodad_funcs WHERE id IN (38376,38377)"
        )
        connection.execute(
            "DELETE FROM doodad_func_quests WHERE id=1507"
        )
        connection.execute(
            "DELETE FROM doodad_func_groups WHERE id IN (41493,41494)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-2256-client-doodad-v1",
                forensic["authority"],
                sha256(options.manifest),
                str(QUEST_ID),
            ),
        )
        checks = validate_output(connection)
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
        "phase": "native-quest-2256-client-doodad-v1-runtime",
        "authority": forensic["authority"],
        "sources": {
            "forensic_manifest": {
                "path": str(options.manifest),
                "sha256": sha256(options.manifest),
            },
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": sha256(options.base_runtime),
            },
        },
        "scope": {
            "quest_ids": [QUEST_ID],
            "client_doodad_ids": [14073],
            "suppressed_adjacent_quest_ids": [2257],
        },
        "schema_additions": additions,
        "unresolved_string_fallbacks": fallbacks,
        "validation": checks,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {
            "deployed": False,
            "reason": "Offline build; controlled game restart pending.",
        },
    }
    options.build_manifest.write_text(
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
