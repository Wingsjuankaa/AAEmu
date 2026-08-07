#!/usr/bin/env python3
"""Remove the legacy 3.0-only talk step from AA8 quest 3993.

The Kakao 8 quest graph contains one Progress component (17209).  Component
19840 and QuestAct 27031 survive only in the 3.0 runtime base; retaining them
prevents the completed item-use objective from crossing the native Ready
frontier 19841.
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


DOMAIN = Path(__file__).resolve().parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-shadowplay-v2.sqlite3"
)
DEFAULT_GRAPH = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics"
    r"\nuia-story-quest-graph-v2.sqlite3"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest3993-v3.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-quest-3993-aa8-prune-v3-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "AD62A01CF762317CFF49624AB2191B2289B096004C48735B95A2A9156587E5F7"
)
EXPECTED_GRAPH_SHA256 = (
    "39FD2589DC095E80722B94D3EB1D307E649C28AEAEB486AEF8725AD33DE82B5A"
)
QUEST_ID = 3993
LEGACY_COMPONENT_ID = 19840
LEGACY_ACT_ID = 27031
NATIVE_COMPONENTS = [
    (17208, 2),
    (17209, 4),
    (17210, 8),
    (19841, 6),
    (21472, 3),
]
NATIVE_ACTS = [
    (29899, "QuestActObjItemUse", 686, 17209),
    (29904, "QuestActSupplyItem", 3410, 21472),
    (40872, "QuestActSupplyItem", 4839, 17210),
    (64077, "QuestActConAcceptDoodad", 806, 17208),
    (64079, "QuestActConReportDoodad", 175, 19841),
    (64144, "QuestActSupplyExp", 3973, 17210),
    (65339, "QuestActSupplyItem", 8720, 17210),
    (65672, "QuestActSupplyItem", 8922, 17210),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rows(
    connection: sqlite3.Connection,
    sql: str,
    parameters: tuple[Any, ...] = (),
) -> list[tuple[Any, ...]]:
    return [tuple(row) for row in connection.execute(sql, parameters)]


def validate_authority(graph_path: Path) -> dict[str, Any]:
    graph_hash = sha256(graph_path)
    if graph_hash != EXPECTED_GRAPH_SHA256:
        raise RuntimeError(
            f"AA8 graph differs: expected {EXPECTED_GRAPH_SHA256}, got {graph_hash}"
        )

    connection = sqlite3.connect(f"file:{graph_path}?mode=ro", uri=True)
    try:
        components = rows(
            connection,
            "SELECT component_id,component_kind_id "
            "FROM story_quest_components WHERE quest_id=? ORDER BY component_id",
            (QUEST_ID,),
        )
        acts = rows(
            connection,
            "SELECT quest_act_id,act_detail_type,act_detail_id,component_id "
            "FROM story_quest_acts WHERE quest_id=? ORDER BY quest_act_id",
            (QUEST_ID,),
        )
    finally:
        connection.close()

    if components != NATIVE_COMPONENTS:
        raise RuntimeError(
            f"AA8 quest 3993 component closure differs: {components}"
        )
    if acts != NATIVE_ACTS:
        raise RuntimeError(f"AA8 quest 3993 act closure differs: {acts}")
    if any(component[0] == LEGACY_COMPONENT_ID for component in components):
        raise RuntimeError("legacy component 19840 unexpectedly exists in AA8 graph")
    return {"components": components, "acts": acts}


def validate_runtime(connection: sqlite3.Connection) -> dict[str, Any]:
    checks = {
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
        "integrity_check": connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0],
        "components": rows(
            connection,
            "SELECT id,component_kind_id FROM quest_components "
            "WHERE quest_context_id=? ORDER BY id",
            (QUEST_ID,),
        ),
        "acts": rows(
            connection,
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE quest_component_id IN "
            "(SELECT id FROM quest_components WHERE quest_context_id=?) "
            "ORDER BY id",
            (QUEST_ID,),
        ),
        "legacy_component_rows": connection.execute(
            "SELECT COUNT(*) FROM quest_components WHERE id=?",
            (LEGACY_COMPONENT_ID,),
        ).fetchone()[0],
        "legacy_act_rows": connection.execute(
            "SELECT COUNT(*) FROM quest_acts WHERE id=?",
            (LEGACY_ACT_ID,),
        ).fetchone()[0],
        "ready_endpoint": tuple(
            connection.execute(
                "SELECT qa.id,qa.act_detail_type,qa.act_detail_id,"
                "qr.doodad_id FROM quest_acts qa "
                "JOIN quest_act_con_report_doodads qr "
                "ON qr.id=qa.act_detail_id "
                "WHERE qa.quest_component_id=19841"
            ).fetchone()
        ),
    }
    expected = {
        "quick_check": "ok",
        "integrity_check": "ok",
        "components": NATIVE_COMPONENTS,
        "acts": NATIVE_ACTS,
        "legacy_component_rows": 0,
        "legacy_act_rows": 0,
        "ready_endpoint": (64079, "QuestActConReportDoodad", 175, 14124),
    }
    failures = {
        key: {"expected": expected[key], "actual": checks[key]}
        for key in expected
        if checks[key] != expected[key]
    }
    if failures:
        raise RuntimeError(f"generated runtime validation failed: {failures}")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

    base_hash = sha256(options.base_runtime)
    if base_hash != EXPECTED_BASE_SHA256:
        raise RuntimeError(
            f"base runtime differs: expected {EXPECTED_BASE_SHA256}, got {base_hash}"
        )
    authority = validate_authority(options.graph)

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        deleted_act = connection.execute(
            "DELETE FROM quest_acts WHERE id=? AND quest_component_id=?",
            (LEGACY_ACT_ID, LEGACY_COMPONENT_ID),
        ).rowcount
        deleted_component = connection.execute(
            "DELETE FROM quest_components WHERE id=? AND quest_context_id=?",
            (LEGACY_COMPONENT_ID, QUEST_ID),
        ).rowcount
        if (deleted_act, deleted_component) != (1, 1):
            raise RuntimeError(
                "legacy quest 3993 closure was not uniquely present in base runtime"
            )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                "native-quest-3993-aa8-prune-v3",
                "ArcheAge Kakao 8.0.3.12 r558734",
                sha256(options.graph),
                str(QUEST_ID),
            ),
        )
        checks = validate_runtime(connection)
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
        "phase": "native-quest-3993-aa8-prune-v3-runtime",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base_runtime": {
                "path": str(options.base_runtime),
                "sha256": base_hash,
            },
            "aa8_quest_graph": {
                "path": str(options.graph),
                "sha256": sha256(options.graph),
            },
        },
        "scope": {
            "quest_id": QUEST_ID,
            "removed_legacy_component_id": LEGACY_COMPONENT_ID,
            "removed_legacy_act_id": LEGACY_ACT_ID,
        },
        "native_closure": authority,
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
