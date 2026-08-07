#!/usr/bin/env python3
"""Build an auditable cumulative AA8 Nuia story runtime through chapter 31.

The frozen V2 forensic graph is authoritative for quest membership, native
components, acts, detail rows, direct items, endpoints, order and transition
gates.  The chapter-6 V1 runtime is an immutable prefix.  Post-V1 quests are
only copied into executable compact tables when their direct runtime closure
is complete; every other quest remains present in the audit inventory with an
explicit stop point and evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = Path(__file__).resolve().parent
CLIENT_ROOT = Path(r"D:\Proyectos\AAemu\client_kakao")
DEFAULT_BASE = CLIENT_ROOT / "compact-8.0-runtime-nuia-story-chapter6-v1.sqlite3"
DEFAULT_GRAPH = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\nuia-story-quest-graph-v2.sqlite3"
)
DEFAULT_STAGE50 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-50-skills.sqlite"
)
DEFAULT_STAGE30 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-30-world-actors.sqlite"
)
DEFAULT_STAGE20 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-20-items.sqlite"
)
DEFAULT_STAGE40 = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage-40-quests.sqlite"
)
DEFAULT_LEGACY_COMPACT = (
    ROOT / "assets" / "compact-3.0.3.0" / "3030.14082023" /
    "win10-x64" / "AAEmu.Game" / "Data" / "compact.sqlite3"
)
DEFAULT_GAME11 = Path(
    r"E:\AAEmu-Research\output\compact-8.0-extracted\game11"
)
DEFAULT_NPC_SPAWNS = ROOT / "AAEmu.Game" / "Data" / "Worlds" / "main_world" / "npc_spawns.json"
DEFAULT_WORLDGATES = ROOT / "AAEmu.Game" / "Data" / "Portal" / "worldgates.json"
DEFAULT_OUTPUT = CLIENT_ROOT / "compact-8.0-runtime-nuia-story-v2-chapter31.sqlite3"
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-nuia-story-v2-runtime-manifest.json"
)

EXPECTED_BASE_SHA256 = (
    "2ABB3724CE94106E2DEE0FB5D638CCBC5572A43143FC3DCAFD430A99C059B6B6"
)
EXPECTED_GRAPH_SHA256 = (
    "39FD2589DC095E80722B94D3EB1D307E649C28AEAEB486AEF8725AD33DE82B5A"
)
EXPECTED_STAGE50_SHA256 = (
    "B15853F5E1D24FC9FAF77C9F4F1697262F32525E6CCDE4EC96D943DD938E9E07"
)
EXPECTED_STAGE30_SHA256 = (
    "D9696D2B5048C9103928E98D94C927474E97F9ADC45D664AC9AAEC3C7FA3CD11"
)
EXPECTED_STAGE20_SHA256 = (
    "1274D10712A913A667364B7B75C47F1DE12013AE77AA7CF41E79F138F3FC979E"
)
EXPECTED_STAGE40_SHA256 = (
    "0BB127E819232BFEE6D6559000E845B8C36E7F4C56A5ED64234DCD28B793D72C"
)
EXPECTED_LEGACY_COMPACT_SHA256 = (
    "9FB1838113820D4F5BAC93BB7E79A3E51613CF7B2828B28545B59F506B4F4397"
)
EXPECTED_GAME11_SHA256 = (
    "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031"
)
EXPECTED_NPC_SPAWNS_SHA256 = (
    "5CF207DA538EB9A580ECAE94CE9677C02F54C4F8ACD19AAEC8FCC15E8A84DB97"
)
EXPECTED_WORLDGATES_SHA256 = (
    "B3E90510424A88E487CD3534B8B99BAA8EA8B441E49F60D5A88EED7374CB83A3"
)
V1_MAX_CHAPTER = 6
FINAL_CHAPTER = 31
EXPECTED_TOTALS = {
    "quests": 294,
    "components": 1294,
    "acts": 1354,
    "act_types": 27,
    "endpoints": 559,
    "items": 428,
}


DETAIL_TABLES = {
    "QuestActCheckCompleteComponent": "quest_act_check_complete_components",
    "QuestActCheckTimer": "quest_act_check_timers",
    "QuestActConAcceptComponent": "quest_act_con_accept_components",
    "QuestActConAcceptDoodad": "quest_act_con_accept_doodads",
    "QuestActConAcceptItem": "quest_act_con_accept_items",
    "QuestActConAcceptNpc": "quest_act_con_accept_npcs",
    "QuestActConAcceptNpcGroup": "quest_act_con_accept_npc_groups",
    "QuestActConAcceptSphere": "quest_act_con_accept_spheres",
    "QuestActConAutoComplete": "quest_act_con_auto_completes",
    "QuestActConReportDoodad": "quest_act_con_report_doodads",
    "QuestActConReportNpc": "quest_act_con_report_npcs",
    "QuestActConReportNpcGroup": "quest_act_con_report_npc_groups",
    "QuestActObjCinema": "quest_act_obj_cinemas",
    "QuestActObjDoodadPhaseCheck": "quest_act_obj_doodad_phase_checks",
    "QuestActObjEffectFire": "quest_act_obj_effect_fires",
    "QuestActObjInteraction": "quest_act_obj_interactions",
    "QuestActObjItemGather": "quest_act_obj_item_gathers",
    "QuestActObjItemUse": "quest_act_obj_item_uses",
    "QuestActObjMonsterGroupHunt": "quest_act_obj_monster_group_hunts",
    "QuestActObjMonsterHunt": "quest_act_obj_monster_hunts",
    "QuestActObjSphere": "quest_act_obj_spheres",
    "QuestActObjTalk": "quest_act_obj_talks",
    "QuestActSupplyAppellation": "quest_act_supply_appellations",
    "QuestActSupplyCopper": "quest_act_supply_coppers",
    "QuestActSupplyExp": "quest_act_supply_exps",
    "QuestActSupplyItem": "quest_act_supply_items",
    "QuestActSupplySelectiveItem": "quest_act_supply_selective_items",
}

# These classes are known to be absent, unconditional-false, or disconnected
# in the current backend.  They remain a hard readiness gate until the generic
# primitive and its regression tests are added.
INCOMPLETE_PRIMITIVES = {
}

COMPONENT_KIND_STOP_POINT = {
    2: "stop_before_acceptance",
    3: "stop_before_acceptance_supply",
    4: "stop_before_or_during_objective_dependency",
    6: "stop_before_report",
    8: "stop_before_reward",
}

EFFECT_TABLES = {
    "BuffEffect": "buff_effects",
    "DispelEffect": "dispel_effects",
    "NpcSpawnerSpawnEffect": "npc_spawner_spawn_effects",
    "KillNpcWithoutCorpseEffect": "kill_npc_without_corpse_effects",
}

BLOCK_A_CLIENT_DOODAD_IDS = {
    14237, 14239, 14240, 14241, 14242,
    14243, 14244, 14245, 14246, 14309,
}
BLOCK_A_CLIENT_DOODAD_QUESTS = {
    (7130, 1), (7132, 2), (7133, 1), (7134, 1), (7134, 2),
    (7135, 1), (7137, 2), (7138, 1), (7138, 2), (7139, 1),
    (7139, 2), (7140, 1), (7145, 2), (7146, 1), (7146, 2),
    (7147, 1), (7147, 2), (7148, 1),
}
BLOCK_A_NATIVE_SKILL_APPLICATIONS = {
    29806: (59483,),
    29817: (59484, 59567),
}
BLOCK_A_SIMPLE_ITEMS = {
    37881: "open_paper",
    37883: "open_paper",
    37884: "open_paper",
    37885: "open_paper",
    37886: "open_paper",
    37887: "generic",
    37888: "generic",
    37889: "generic",
    37890: "generic",
    37891: "generic",
    37892: "generic",
    38093: "generic",
    38183: "armor",
    52815: "generic",
    52816: "generic",
}

POST_V1_STORY_CHAPTERS = range(7, FINAL_CHAPTER + 1)

POST_V1_RETURN_POINT_PROXIES = {
    708: {
        "quest_ids": [8539, 8545],
        "report_npc_id": 15144,
        "zone_id": 200,
        "x": 17233.918,
        "y": 27511.28,
        "z": 141.0,
    },
    863: {
        "quest_ids": [8556],
        "report_npc_id": 17828,
        "zone_id": 258,
        "x": 14434.6895,
        "y": 26684.73,
        "z": 134.25,
    },
    998: {
        "quest_ids": [8550],
        "report_npc_id": 17823,
        "zone_id": 149,
        "x": 16482.9,
        "y": 28100.27,
        "z": 105.262,
    },
}

# These buffs are direct dependencies of post-V1 Nuia story items or
# QuestActObjEffectFire rows.  They were selected only after auditing their
# complete Stage 50 rows, trigger/tick effects and recursive buff references.
# The resolver below still revalidates the native graph on every build; this
# set is a scope boundary, not replacement data.
POST_V1_SAFE_STORY_BUFF_ROOTS = {
    26148,
    26178,
    26190,
    26211,
    26212,
    26213,
    26240,
    26241,
    26317,
    26689,
}
BLOCK_B_CHAPTERS = range(12, 18)
BLOCK_B_TOMBSTONE_ITEMS = {8318, 16353, 16354, 16355}
BLOCK_B_NATIVE_NPCS = {17818, 17821, 17822, 17823, 17828, 18039, 18624}
BLOCK_B_MONSTER_GROUPS = {794, 807, 808, 930, 932}
BLOCK_B_CLIENT_DOODAD_IDS = {12214, 14248, 14250, 14253, 14313}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    return connection


def load_effective_npc_spawn_ids(path: Path) -> set[int]:
    rows = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        int(row["UnitId"])
        for row in rows
        if isinstance(row, dict) and int(row.get("UnitId", 0) or 0) > 0
    }


def load_worldgate_ids(path: Path) -> set[int]:
    # AAEmu's portal catalog intentionally permits // and /* */ comments, so
    # it is not strict JSON.  IDs are scalar decimal fields and can be audited
    # without rewriting or normalizing the source file.
    contents = path.read_text(encoding="utf-8-sig")
    return {
        int(value)
        for value in re.findall(r'"Id"\s*:\s*(\d+)\b', contents)
    }


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    ]


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def upsert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: Iterable[dict[str, Any]],
) -> None:
    rows = list(rows)
    if not rows:
        return
    columns = list(rows[0])
    available = set(table_columns(connection, table))
    missing = set(columns) - available
    if missing:
        raise RuntimeError(f"{table} schema lacks native columns {sorted(missing)}")
    quoted = ",".join(f'"{column}"' for column in columns)
    placeholders = ",".join("?" for _ in columns)
    connection.executemany(
        f'INSERT OR REPLACE INTO "{table}" ({quoted}) VALUES ({placeholders})',
        [[row[column] for column in columns] for row in rows],
    )


def sanitize_strings(
    connection: sqlite3.Connection,
    table: str,
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep unresolved client string references out of the server runtime.

    game11 proves the row and relationship identity, but some cached strings
    are references into client-only pools.  Prefer an already-proven runtime
    value for the same row/column; otherwise use the empty string and retain
    the exact native reference in the materialization evidence.
    """
    clean_rows: list[dict[str, Any]] = []
    fallbacks: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        previous = connection.execute(
            f'SELECT * FROM "{table}" WHERE id=?', (int(row["id"]),)
        ).fetchone()
        previous_values = dict(previous) if previous else {}
        for column, value in list(row.items()):
            if not (
                isinstance(value, str)
                and value.startswith("<ref:")
                and value.endswith(">")
            ):
                continue
            replacement = previous_values.get(column) or ""
            row[column] = replacement
            fallbacks.append(
                {
                    "table": table,
                    "id": int(row["id"]),
                    "column": column,
                    "native_reference": value,
                    "runtime_value": replacement,
                }
            )
        clean_rows.append(row)
    return clean_rows, fallbacks


def row_for_runtime_schema(
    connection: sqlite3.Connection,
    table: str,
    source: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Project a corroborated legacy row onto the current AA8 schema.

    This is deliberately used only for entities that AA8 still references but
    whose complete native catalogue marks them as tombstones.  Every padded
    column is retained in the materialization evidence.
    """
    result: dict[str, Any] = {}
    padded: list[str] = []
    for column in connection.execute(f'PRAGMA table_info("{table}")'):
        name = str(column[1])
        if name in source:
            result[name] = source[name]
        else:
            padded.append(name)
            result[name] = "" if "TEXT" in str(column[2]).upper() else 0
    return result, padded


def load_doodad_decoder():
    path = DOMAIN / "extract_native_nuian_green_arc.py"
    spec = importlib.util.spec_from_file_location("nuia_v2_doodad_decoder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import AA8 doodad decoder {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DECODED_DOODAD_TABLES: dict[str, list[dict[str, Any]]] | None = None


def decode_client_doodad_tables(
    game11_path: Path,
) -> dict[str, list[dict[str, Any]]]:
    global _DECODED_DOODAD_TABLES
    if _DECODED_DOODAD_TABLES is not None:
        return _DECODED_DOODAD_TABLES
    decoder = load_doodad_decoder()
    catalog = decoder.load_catalog()
    data = game11_path.read_bytes()
    decoded: dict[str, list[dict[str, Any]]] = {}
    for table, spec in decoder.DOODAD_SPECS.items():
        decoded[table], _ = decoder.decode_rows(
            catalog.CachedResultReader, data, table, spec
        )
    _DECODED_DOODAD_TABLES = decoded
    return decoded


def extract_block_a_client_doodads(
    game11_path: Path,
) -> dict[str, list[dict[str, Any]]]:
    decoded = decode_client_doodad_tables(game11_path)

    almighties = [
        row for row in decoded["doodad_almighties"]
        if int(row["id"]) in BLOCK_A_CLIENT_DOODAD_IDS
    ]
    if {int(row["id"]) for row in almighties} != BLOCK_A_CLIENT_DOODAD_IDS:
        raise RuntimeError("AA8 Block A client-doodad identity set changed")
    if any(int(row["client_doodad"]) != 1 for row in almighties):
        raise RuntimeError("AA8 Block A logical doodad is no longer client_doodad=1")

    groups = [
        row for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in BLOCK_A_CLIENT_DOODAD_IDS
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        row for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    if len(groups) != 23 or len(funcs) != 20:
        raise RuntimeError(
            f"AA8 Block A doodad closure changed: {len(groups)} groups/{len(funcs)} funcs"
        )
    actual_types = {str(row["actual_func_type"]) for row in funcs}
    if actual_types != {"DoodadFuncQuest", "DoodadFuncUse"}:
        raise RuntimeError(f"unsupported Block A doodad func types {actual_types}")

    quest_func_ids = {
        int(row["actual_func_id"])
        for row in funcs
        if str(row["actual_func_type"]) == "DoodadFuncQuest"
    }
    quest_funcs = [
        row for row in decoded["doodad_func_quests"]
        if int(row["id"]) in quest_func_ids
    ]
    if {int(row["id"]) for row in quest_funcs} != quest_func_ids:
        raise RuntimeError("AA8 Block A doodad quest-function closure is incomplete")
    observed_quests = {
        (int(row["quest_id"]), int(row["quest_kind_id"]))
        for row in quest_funcs
    }
    if observed_quests != BLOCK_A_CLIENT_DOODAD_QUESTS:
        raise RuntimeError(f"AA8 Block A doodad quest bindings changed: {observed_quests}")

    use_funcs = [
        row for row in funcs if str(row["actual_func_type"]) == "DoodadFuncUse"
    ]
    observed_uses = {
        (int(row["actual_func_id"]), int(row["func_skill_id"]))
        for row in use_funcs
    }
    if observed_uses != {(10951, 29817), (10952, 29806)}:
        raise RuntimeError(f"AA8 Block A doodad use bindings changed: {observed_uses}")

    return {
        "doodad_almighties": almighties,
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_quests": quest_funcs,
        "doodad_func_uses": [
            {"id": int(row["actual_func_id"]), "skill_id": int(row["func_skill_id"])}
            for row in use_funcs
        ],
    }


def extract_block_b_client_doodads(
    game11_path: Path,
) -> dict[str, list[dict[str, Any]]]:
    decoded = decode_client_doodad_tables(game11_path)
    almighties = [
        row for row in decoded["doodad_almighties"]
        if int(row["id"]) in BLOCK_B_CLIENT_DOODAD_IDS
    ]
    if {int(row["id"]) for row in almighties} != BLOCK_B_CLIENT_DOODAD_IDS:
        raise RuntimeError("AA8 Block B client-doodad identity set changed")
    groups = [
        row for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in BLOCK_B_CLIENT_DOODAD_IDS
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        row for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    allowed = {
        "DoodadFuncQuest", "DoodadFuncUse", "DoodadFuncOpenPaper",
        "DoodadFuncRecoverItem",
    }
    observed_types = {str(row["actual_func_type"]) for row in funcs}
    if not observed_types.issubset(allowed):
        raise RuntimeError(f"Block B doodad func types changed: {observed_types}")
    quest_ids = {
        int(row["actual_func_id"])
        for row in funcs if str(row["actual_func_type"]) == "DoodadFuncQuest"
    }
    quest_funcs = [
        row for row in decoded["doodad_func_quests"]
        if int(row["id"]) in quest_ids
    ]
    if {int(row["id"]) for row in quest_funcs} != quest_ids:
        raise RuntimeError("AA8 Block B doodad quest closure is incomplete")
    use_funcs = [
        row for row in funcs if str(row["actual_func_type"]) == "DoodadFuncUse"
    ]
    return {
        "doodad_almighties": almighties,
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_quests": quest_funcs,
        "doodad_func_uses": [
            {"id": int(row["actual_func_id"]), "skill_id": int(row["func_skill_id"])}
            for row in use_funcs
        ],
    }


def story_doodad_ids(
    story: dict[str, Any], through_chapter: int
) -> set[int]:
    quest_chapters = {
        int(row["quest_id"]): int(row["chapter_idx"])
        for row in story["quests"]
    }
    component_quests = {
        int(row["id"]): int(row["quest_context_id"])
        for row in story["components"]
    }
    details_by_type = {
        detail_type: {int(row["id"]): row for row in rows}
        for detail_type, rows in story["details"].items()
    }
    result = {
        int(row["endpoint_id"])
        for row in story["endpoints"]
        if V1_MAX_CHAPTER < quest_chapters[int(row["quest_id"])] <= through_chapter
        and str(row["endpoint_kind"]) == "doodad"
    }
    for act in story["acts"]:
        quest_id = component_quests[int(act["quest_component_id"])]
        if not V1_MAX_CHAPTER < quest_chapters[quest_id] <= through_chapter:
            continue
        detail = details_by_type[str(act["act_detail_type"])][
            int(act["act_detail_id"])
        ]
        for field in ("doodad_id", "highlight_doodad_id"):
            doodad_id = int(detail.get(field, 0) or 0)
            if doodad_id:
                result.add(doodad_id)
    return result


def extract_story_client_doodads(
    game11_path: Path, doodad_ids: set[int]
) -> dict[str, Any]:
    decoded = decode_client_doodad_tables(game11_path)
    almighties = [
        row for row in decoded["doodad_almighties"]
        if int(row["id"]) in doodad_ids
    ]
    found_ids = {int(row["id"]) for row in almighties}
    groups = [
        row for row in decoded["doodad_func_groups"]
        if int(row["doodad_almighty_id"]) in found_ids
    ]
    group_ids = {int(row["id"]) for row in groups}
    funcs = [
        row for row in decoded["doodad_funcs"]
        if int(row["doodad_func_group_id"]) in group_ids
    ]
    quest_detail_ids = {
        int(row["actual_func_id"])
        for row in funcs if str(row["actual_func_type"]) == "DoodadFuncQuest"
    }
    quest_funcs = [
        row for row in decoded["doodad_func_quests"]
        if int(row["id"]) in quest_detail_ids
    ]
    if {int(row["id"]) for row in quest_funcs} != quest_detail_ids:
        raise RuntimeError("AA8 story doodad quest-function closure is incomplete")
    use_funcs = [
        row for row in funcs if str(row["actual_func_type"]) == "DoodadFuncUse"
    ]
    return {
        "requested_ids": sorted(doodad_ids),
        "found_ids": sorted(found_ids),
        "missing_ids": sorted(doodad_ids - found_ids),
        "doodad_almighties": almighties,
        "doodad_func_groups": groups,
        "doodad_funcs": funcs,
        "doodad_func_quests": quest_funcs,
        "doodad_func_uses": [
            {"id": int(row["actual_func_id"]), "skill_id": int(row["func_skill_id"])}
            for row in use_funcs
        ],
    }


def record_materialization(
    connection: sqlite3.Connection,
    key: str,
    entity_kind: str,
    entity_id: int,
    authority: str,
    source_hash: str,
    evidence: dict[str, Any],
    state: str = "active",
) -> None:
    connection.execute(
        "INSERT INTO aaemu_nuia_story_v2_materializations VALUES (?,?,?,?,?,?,?)",
        (
            key,
            entity_kind,
            entity_id,
            authority,
            state,
            source_hash,
            json.dumps(
                evidence,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ),
    )


def actual_effect_table(actual_type: str) -> str:
    if actual_type in EFFECT_TABLES:
        return EFFECT_TABLES[actual_type]
    if not actual_type.endswith("Effect"):
        raise RuntimeError(f"unsupported effect type {actual_type}")
    stem = actual_type[:-6]
    chars: list[str] = []
    for index, char in enumerate(stem):
        if index and char.isupper() and stem[index - 1].islower():
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars) + "_effects"


@dataclass(frozen=True)
class Blocker:
    kind: str
    entity_kind: str
    entity_id: int
    severity: str
    stop_point: str
    evidence: dict[str, Any]

    def key(self, quest_id: int) -> str:
        return (
            f"q{quest_id}:{self.kind}:{self.entity_kind}:{self.entity_id}:"
            f"{self.stop_point}"
        )


def load_graph(path: Path) -> dict[str, Any]:
    connection = ro(path)
    try:
        quests: list[dict[str, Any]] = []
        for row in connection.execute(
            "SELECT * FROM story_quests ORDER BY chapter_idx,quest_idx,quest_id"
        ):
            quest = dict(row)
            evidence = json.loads(quest["evidence_json"])
            native_row = evidence.get("native_row")
            if not isinstance(native_row, dict) or int(native_row.get("id", 0)) != int(
                quest["quest_id"]
            ):
                raise RuntimeError(
                    f"quest {quest['quest_id']} lacks its authoritative native row"
                )
            quest["native_row"] = native_row
            quests.append(quest)

        components: list[dict[str, Any]] = []
        component_meta: dict[int, dict[str, Any]] = {}
        for row in connection.execute(
            "SELECT * FROM story_quest_components "
            "ORDER BY quest_id,ordinal,component_id"
        ):
            parsed = json.loads(row["row_json"])
            if int(parsed.get("id", 0)) != int(row["component_id"]):
                raise RuntimeError(
                    f"component {row['component_id']} lost its native row identity"
                )
            components.append(parsed)
            component_meta[int(row["component_id"])] = dict(row)

        acts: list[dict[str, Any]] = []
        details: dict[str, list[dict[str, Any]]] = {
            detail_type: [] for detail_type in DETAIL_TABLES
        }
        act_meta: dict[int, dict[str, Any]] = {}
        for row in connection.execute(
            "SELECT * FROM story_quest_acts "
            "ORDER BY quest_id,component_id,quest_act_id"
        ):
            detail_type = str(row["act_detail_type"])
            if detail_type not in DETAIL_TABLES:
                raise RuntimeError(f"unsupported native quest act type {detail_type}")
            if row["detail_row_json"] is None:
                raise RuntimeError(f"missing detail row for quest act {row['quest_act_id']}")
            detail = json.loads(row["detail_row_json"])
            if int(detail.get("id", 0)) != int(row["act_detail_id"]):
                raise RuntimeError(
                    f"act {row['quest_act_id']} lost its native detail identity"
                )
            act = {
                "id": int(row["quest_act_id"]),
                "act_detail_type": detail_type,
                "act_detail_id": int(row["act_detail_id"]),
                "quest_component_id": int(row["component_id"]),
            }
            acts.append(act)
            details[detail_type].append(detail)
            meta = dict(row)
            meta["detail"] = detail
            act_meta[int(row["quest_act_id"])] = meta

        result = {
            "quests": quests,
            "components": components,
            "component_meta": component_meta,
            "acts": acts,
            "act_meta": act_meta,
            "details": details,
            "items": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM story_quest_items "
                    "ORDER BY quest_id,component_id,quest_act_id,relation_key"
                )
            ],
            "endpoints": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM story_quest_endpoints "
                    "ORDER BY quest_id,phase,endpoint_key"
                )
            ],
            "transitions": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM story_transition_gates ORDER BY src_quest_id,dst_quest_id"
                )
            ],
            "terminal_audits": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM story_terminal_audits ORDER BY audit_key"
                )
            ],
            "wiki_resolutions": [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM story_wiki_edge_resolutions "
                    "ORDER BY src_quest_id,relation,resolution_key"
                )
            ],
        }
        totals = {
            "quests": len(result["quests"]),
            "components": len(result["components"]),
            "acts": len(result["acts"]),
            "act_types": len({row["act_detail_type"] for row in result["acts"]}),
            "endpoints": len(result["endpoints"]),
            "items": len(result["items"]),
        }
        if totals != EXPECTED_TOTALS:
            raise RuntimeError(f"V2 forensic cardinality changed: {totals}")
        return result
    finally:
        connection.close()


class RuntimeInspector:
    def __init__(
        self,
        connection: sqlite3.Connection,
        npc_spawn_ids: set[int],
        worldgate_ids: set[int],
        graph_component_owners: dict[int, int],
    ):
        self.connection = connection
        self.npc_spawn_ids = npc_spawn_ids
        self.worldgate_ids = worldgate_ids
        self.graph_component_owners = graph_component_owners

    def has(self, table: str, column: str, value: int) -> bool:
        if not table_exists(self.connection, table):
            return False
        return self.connection.execute(
            f'SELECT 1 FROM "{table}" WHERE "{column}"=? LIMIT 1', (value,)
        ).fetchone() is not None

    def effect_blockers(
        self,
        effect_id: int,
        stop_point: str,
        evidence: dict[str, Any],
    ) -> list[Blocker]:
        effect = self.connection.execute(
            "SELECT actual_type,actual_id FROM effects WHERE id=?", (effect_id,)
        ).fetchone()
        if effect is None:
            return [
                Blocker(
                    "missing_objective_effect",
                    "effect",
                    effect_id,
                    "high",
                    stop_point,
                    evidence,
                )
            ]
        actual_type = str(effect[0])
        actual_id = int(effect[1])
        detail_table = actual_effect_table(actual_type)
        detail = self.connection.execute(
            f'SELECT * FROM "{detail_table}" WHERE id=?', (actual_id,)
        ).fetchone() if table_exists(self.connection, detail_table) else None
        if detail is None:
            return [
                Blocker(
                    "missing_objective_effect_detail",
                    "effect",
                    effect_id,
                    "high",
                    stop_point,
                    {
                        **evidence,
                        "actual_type": actual_type,
                        "actual_id": actual_id,
                        "detail_table": detail_table,
                    },
                )
            ]
        detail = dict(detail)
        dependencies: list[tuple[str, str, int]] = []
        if actual_type == "BuffEffect":
            dependencies.append(("buff", "buffs", int(detail["buff_id"])))
        elif actual_type == "InteractionEffect":
            doodad_id = int(detail.get("doodad_id", 0) or 0)
            if doodad_id:
                dependencies.append(("doodad", "doodad_almighties", doodad_id))
        elif actual_type == "NpcSpawnerSpawnEffect":
            dependencies.append(("npc_spawner", "npc_spawners", int(detail["spawner_id"])))
        elif actual_type == "KillNpcWithoutCorpseEffect":
            dependencies.append(("npc", "npcs", int(detail["npc_id"])))
        blockers: list[Blocker] = []
        for entity_kind, table, entity_id in dependencies:
            if entity_id and not self.has(table, "id", entity_id):
                blockers.append(
                    Blocker(
                        "missing_objective_effect_dependency",
                        entity_kind,
                        entity_id,
                        "high",
                        stop_point,
                        {
                            **evidence,
                            "effect_id": effect_id,
                            "actual_type": actual_type,
                            "actual_id": actual_id,
                            "detail_table": detail_table,
                        },
                    )
                )
        if (
            actual_type == "SpecialEffect"
            and int(detail.get("special_effect_type_id", 0) or 0) == 25
            and int(detail.get("value1", 0) or 0) not in self.worldgate_ids
        ):
            blockers.append(
                Blocker(
                    "missing_objective_effect_dependency",
                    "return_point",
                    int(detail["value1"]),
                    "high",
                    stop_point,
                    {
                        **evidence,
                        "effect_id": effect_id,
                        "actual_type": actual_type,
                        "actual_id": actual_id,
                        "detail_table": detail_table,
                    },
                )
            )
        return blockers

    def item_blockers(
        self,
        item_id: int,
        stop_point: str,
        evidence: dict[str, Any],
    ) -> list[Blocker]:
        row = self.connection.execute(
            "SELECT use_skill_id FROM items WHERE id=?", (item_id,)
        ).fetchone()
        if row is None:
            return [
                Blocker(
                    "missing_item_definition",
                    "item",
                    item_id,
                    "high",
                    stop_point,
                    evidence,
                )
            ]
        coverage = self.connection.execute(
            "SELECT coverage,missing_dependencies,provenance "
            "FROM aaemu_item_definition_coverage WHERE item_id=?",
            (item_id,),
        ).fetchone()
        if coverage is None or str(coverage[0]) != "complete":
            return [
                Blocker(
                    "item_definition_not_creatable",
                    "item",
                    item_id,
                    "high",
                    stop_point,
                    {
                        **evidence,
                        "runtime_coverage": None if coverage is None else str(coverage[0]),
                        "missing_dependencies": "" if coverage is None else str(coverage[1]),
                    },
                )
            ]
        skill_id = int(row[0] or 0)
        if not skill_id:
            return []
        if not self.has("skills", "id", skill_id):
            return [
                Blocker(
                    "missing_item_use_skill",
                    "skill",
                    skill_id,
                    "high",
                    stop_point,
                    {**evidence, "item_id": item_id},
                )
            ]
        if (
            str(evidence.get("item_role", "")) == "objective_use"
            and not self.has("skill_effects", "skill_id", skill_id)
        ):
            return [
                Blocker(
                    "missing_item_use_skill_effects",
                    "skill",
                    skill_id,
                    "high",
                    stop_point,
                    {**evidence, "item_id": item_id},
                )
            ]
        blockers: list[Blocker] = []
        for effect in self.connection.execute(
            "SELECT e.id,e.actual_type,e.actual_id FROM skill_effects se "
            "JOIN effects e ON e.id=se.effect_id WHERE se.skill_id=? ORDER BY se.id",
            (skill_id,),
        ):
            table = actual_effect_table(str(effect[1]))
            if not self.has(table, "id", int(effect[2])):
                blockers.append(
                    Blocker(
                        "missing_item_use_effect_detail",
                        "effect",
                        int(effect[0]),
                        "high",
                        stop_point,
                        {
                            **evidence,
                            "item_id": item_id,
                            "skill_id": skill_id,
                            "actual_type": str(effect[1]),
                            "actual_id": int(effect[2]),
                            "detail_table": table,
                        },
                    )
                )
                continue
            if table == "special_effects":
                special = self.connection.execute(
                    "SELECT special_effect_type_id,value1 FROM special_effects WHERE id=?",
                    (int(effect[2]),),
                ).fetchone()
                if (
                    special is not None
                    and int(special[0]) == 25
                    and int(special[1]) not in self.worldgate_ids
                ):
                    blockers.append(
                        Blocker(
                            "missing_return_worldgate",
                            "return_point",
                            int(special[1]),
                            "high",
                            stop_point,
                            {
                                **evidence,
                                "item_id": item_id,
                                "skill_id": skill_id,
                                "effect_id": int(effect[0]),
                                "special_effect_id": int(effect[2]),
                            },
                        )
                    )
        return blockers

    def npc_blockers(
        self,
        npc_id: int,
        stop_point: str,
        evidence: dict[str, Any],
    ) -> list[Blocker]:
        blockers: list[Blocker] = []
        if not self.has("npcs", "id", npc_id):
            blockers.append(
                Blocker(
                    "missing_npc_template", "npc", npc_id, "high", stop_point, evidence
                )
            )
            return blockers
        npc = self.connection.execute(
            "SELECT model_id,equip_cloths_id,equip_weapons_id,npc_posture_set_id,"
            "npc_nickname_id,base_skill_id,faction_id,ai_file_id,sound_pack_id "
            "FROM npcs WHERE id=?",
            (npc_id,),
        ).fetchone()
        dependencies = (
            ("model", "models", int(npc[0] or 0)),
            ("equip_cloths", "equip_pack_cloths", int(npc[1] or 0)),
            ("equip_weapons", "equip_pack_weapons", int(npc[2] or 0)),
            ("base_skill", "skills", int(npc[5] or 0)),
            ("faction", "system_factions", int(npc[6] or 0)),
            ("ai_file", "ai_files", int(npc[7] or 0)),
        )
        for kind, table, dependency_id in dependencies:
            if dependency_id and not self.has(table, "id", dependency_id):
                blockers.append(
                    Blocker(
                        "missing_npc_runtime_dependency",
                        kind,
                        dependency_id,
                        "high",
                        stop_point,
                        {**evidence, "npc_id": npc_id, "runtime_table": table},
                    )
                )
        relation = self.connection.execute(
            "SELECT 1 FROM npc_spawner_npcs "
            "WHERE member_type='Npc' AND member_id=? LIMIT 1",
            (npc_id,),
        ).fetchone()
        if relation is None and npc_id not in self.npc_spawn_ids:
            blockers.append(
                Blocker(
                    "missing_npc_spawn_relation",
                    "npc",
                    npc_id,
                    "high",
                    stop_point,
                    evidence,
                )
            )
        return blockers

    def doodad_blockers(
        self,
        doodad_id: int,
        stop_point: str,
        evidence: dict[str, Any],
    ) -> list[Blocker]:
        if not self.has("doodad_almighties", "id", doodad_id):
            return [
                Blocker(
                    "missing_doodad_template",
                    "doodad",
                    doodad_id,
                    "high",
                    stop_point,
                    evidence,
                )
            ]
        blockers: list[Blocker] = []
        functions = list(
            self.connection.execute(
                "SELECT f.id,f.actual_func_type,f.actual_func_id,f.func_skill_id "
                "FROM doodad_func_groups g JOIN doodad_funcs f "
                "ON f.doodad_func_group_id=g.id "
                "WHERE g.doodad_almighty_id=? ORDER BY f.id",
                (doodad_id,),
            )
        )
        for func in functions:
            func_id = int(func[0])
            actual_type = str(func[1])
            actual_id = int(func[2])
            func_skill_id = int(func[3] or 0)
            if actual_type == "DoodadFuncQuest":
                if not self.has("doodad_func_quests", "id", actual_id):
                    blockers.append(
                        Blocker(
                            "missing_doodad_function_detail",
                            "doodad_func_quest",
                            actual_id,
                            "high",
                            stop_point,
                            {**evidence, "doodad_id": doodad_id, "doodad_func_id": func_id},
                        )
                    )
                continue
            if actual_type == "DoodadFuncUse":
                use = self.connection.execute(
                    "SELECT skill_id FROM doodad_func_uses WHERE id=?", (actual_id,)
                ).fetchone()
                if use is None or int(use[0]) != func_skill_id:
                    blockers.append(
                        Blocker(
                            "missing_doodad_function_detail",
                            "doodad_func_use",
                            actual_id,
                            "high",
                            stop_point,
                            {
                                **evidence,
                                "doodad_id": doodad_id,
                                "doodad_func_id": func_id,
                                "native_func_skill_id": func_skill_id,
                            },
                        )
                    )
                elif not self.has("skills", "id", func_skill_id) or not self.has(
                    "skill_effects", "skill_id", func_skill_id
                ):
                    blockers.append(
                        Blocker(
                            "missing_doodad_use_skill_closure",
                            "skill",
                            func_skill_id,
                            "high",
                            stop_point,
                            {**evidence, "doodad_id": doodad_id, "doodad_func_id": func_id},
                        )
                    )
                continue
            if actual_type == "DoodadFuncFakeUse":
                fake = self.connection.execute(
                    "SELECT fake_skill_id,skill_id FROM doodad_func_fake_uses WHERE id=?",
                    (actual_id,),
                ).fetchone()
                if fake is None:
                    blockers.append(
                        Blocker(
                            "missing_doodad_function_detail",
                            "doodad_func_fake_use",
                            actual_id,
                            "high",
                            stop_point,
                            {**evidence, "doodad_id": doodad_id, "doodad_func_id": func_id},
                        )
                    )
                else:
                    for skill_id in (int(fake[0] or 0), int(fake[1] or 0)):
                        if skill_id and not self.has("skills", "id", skill_id):
                            blockers.append(
                                Blocker(
                                    "missing_doodad_fake_use_skill",
                                    "skill",
                                    skill_id,
                                    "high",
                                    stop_point,
                                    {**evidence, "doodad_id": doodad_id, "doodad_func_id": func_id},
                                )
                            )
                continue
            if actual_type == "DoodadFuncLootItem":
                loot = self.connection.execute(
                    "SELECT item_id FROM doodad_func_loot_items WHERE id=?",
                    (actual_id,),
                ).fetchone()
                if loot is None:
                    blockers.append(
                        Blocker(
                            "missing_doodad_function_detail",
                            "doodad_func_loot_item",
                            actual_id,
                            "high",
                            stop_point,
                            {**evidence, "doodad_id": doodad_id, "doodad_func_id": func_id},
                        )
                    )
                else:
                    blockers.extend(
                        self.item_blockers(
                            int(loot[0]),
                            stop_point,
                            {**evidence, "doodad_id": doodad_id, "doodad_func_id": func_id},
                        )
                    )
                continue
            blockers.append(
                Blocker(
                    "unsupported_doodad_function_type",
                    "doodad_func",
                    func_id,
                    "high",
                    stop_point,
                    {**evidence, "doodad_id": doodad_id, "actual_func_type": actual_type},
                )
            )
        return blockers

    def endpoint_blockers(self, endpoint: dict[str, Any]) -> list[Blocker]:
        kind = str(endpoint["endpoint_kind"])
        entity_id = int(endpoint["endpoint_id"])
        phase = str(endpoint["phase"])
        stop_point = "stop_before_acceptance" if phase == "accept" else "stop_before_report"
        evidence = {
            "endpoint_key": endpoint["endpoint_key"],
            "act_detail_type": endpoint["act_detail_type"],
            "act_detail_id": endpoint["act_detail_id"],
            "forensic_spawn_state": endpoint["spawn_state"],
            "forensic_closure_state": endpoint["closure_state"],
        }
        if kind == "npc":
            return self.npc_blockers(entity_id, stop_point, evidence)
        if kind == "doodad":
            if not self.has("doodad_almighties", "id", entity_id):
                return [
                    Blocker(
                        "missing_doodad_template", "doodad", entity_id,
                        "high", stop_point, evidence,
                    )
                ]
            quest_kind_id = 1 if phase == "accept" else 2
            quest_func = self.connection.execute(
                "SELECT 1 FROM doodad_func_groups g "
                "JOIN doodad_funcs f ON f.doodad_func_group_id=g.id "
                "JOIN doodad_func_quests q ON q.id=f.actual_func_id "
                "WHERE g.doodad_almighty_id=? AND f.actual_func_type='DoodadFuncQuest' "
                "AND q.quest_id=? AND q.quest_kind_id=? LIMIT 1",
                (entity_id, int(endpoint["quest_id"]), quest_kind_id),
            ).fetchone()
            if quest_func is None:
                return [
                    Blocker(
                        "missing_doodad_quest_function",
                        "doodad",
                        entity_id,
                        "high",
                        stop_point,
                        evidence,
                    )
                ]
            return []
        if kind == "sphere":
            if not self.has("sphere_accept_quests", "id", entity_id):
                return [
                    Blocker(
                        "missing_sphere_endpoint",
                        "sphere",
                        entity_id,
                        "high",
                        stop_point,
                        evidence,
                    )
                ]
            return []
        return [
            Blocker(
                "unsupported_endpoint_kind",
                kind,
                entity_id,
                "high",
                stop_point,
                evidence,
            )
        ]


def item_stop_point(item: dict[str, Any]) -> str:
    role = str(item["item_role"])
    if role == "accept_requirement":
        return "stop_before_acceptance"
    if role == "initial_supply":
        return "stop_before_acceptance_supply"
    if role.startswith("objective_"):
        return "stop_before_or_during_objective_dependency"
    return "stop_before_reward"


def direct_act_blockers(
    inspector: RuntimeInspector,
    act: dict[str, Any],
    component_kind: int,
) -> list[Blocker]:
    detail_type = str(act["act_detail_type"])
    detail = act["detail"]
    stop_point = COMPONENT_KIND_STOP_POINT.get(
        component_kind, "stop_before_or_during_objective_dependency"
    )
    evidence = {
        "quest_act_id": int(act["quest_act_id"]),
        "component_id": int(act["component_id"]),
        "act_detail_type": detail_type,
        "act_detail_id": int(act["act_detail_id"]),
    }
    blockers: list[Blocker] = []
    if detail_type in INCOMPLETE_PRIMITIVES:
        blockers.append(
            Blocker(
                "runtime_primitive_incomplete",
                "quest_act_type",
                int(act["act_detail_id"]),
                "high",
                stop_point,
                evidence,
            )
        )

    npc_field = None
    if detail_type in {"QuestActObjTalk", "QuestActObjMonsterHunt"}:
        npc_field = "npc_id"
    if npc_field and int(detail.get(npc_field, 0)):
        blockers.extend(
            inspector.npc_blockers(int(detail[npc_field]), stop_point, evidence)
        )

    group_field = None
    if detail_type in {
        "QuestActConAcceptNpcGroup",
        "QuestActConReportNpcGroup",
        "QuestActObjMonsterGroupHunt",
    }:
        group_field = "quest_monster_group_id"
    if group_field and int(detail.get(group_field, 0)):
        group_id = int(detail[group_field])
        if not inspector.has("quest_monster_groups", "id", group_id):
            blockers.append(
                Blocker(
                    "missing_quest_monster_group",
                    "quest_monster_group",
                    group_id,
                    "high",
                    stop_point,
                    evidence,
                )
            )
        elif not inspector.has(
            "quest_monster_npcs",
            "quest_monster_group_id",
            group_id,
        ):
            blockers.append(
                Blocker(
                    "missing_quest_monster_group_members",
                    "quest_monster_group",
                    group_id,
                    "high",
                    stop_point,
                    evidence,
                )
            )
        else:
            for member in inspector.connection.execute(
                "SELECT id,npc_id FROM quest_monster_npcs "
                "WHERE quest_monster_group_id=? ORDER BY id",
                (group_id,),
            ):
                blockers.extend(
                    inspector.npc_blockers(
                        int(member[1]),
                        stop_point,
                        {
                            **evidence,
                            "quest_monster_group_id": group_id,
                            "quest_monster_npc_id": int(member[0]),
                        },
                    )
                )

    if detail_type in {"QuestActObjInteraction", "QuestActObjDoodadPhaseCheck"}:
        for field in ("doodad_id", "highlight_doodad_id"):
            doodad_id = int(detail.get(field, 0) or 0)
            if doodad_id:
                doodad_blockers = inspector.doodad_blockers(
                    doodad_id,
                    stop_point,
                    {**evidence, "source_field": field},
                )
                for blocker in doodad_blockers:
                    if blocker.kind == "missing_doodad_template":
                        blockers.append(
                            Blocker(
                                "missing_objective_doodad",
                                "doodad",
                                doodad_id,
                                "high",
                                stop_point,
                                blocker.evidence,
                            )
                        )
                    else:
                        blockers.append(blocker)

    if detail_type == "QuestActObjEffectFire":
        effect_id = int(detail.get("effect_id", 0))
        if effect_id:
            blockers.extend(
                inspector.effect_blockers(effect_id, stop_point, evidence)
            )
        if int(detail.get("team_share", 0) or 0):
            blockers.append(
                Blocker(
                    "effect_fire_team_share_not_validated",
                    "quest_act_type",
                    int(act["act_detail_id"]),
                    "high",
                    stop_point,
                    evidence,
                )
            )

    if detail_type == "QuestActObjCinema":
        cinema_id = int(detail.get("cinema_id", 0))
        if cinema_id and not inspector.has("cinemas", "id", cinema_id):
            blockers.append(
                Blocker(
                    "missing_cinema",
                    "cinema",
                    cinema_id,
                    "high",
                    stop_point,
                    evidence,
                )
            )

    if detail_type == "QuestActSupplyAppellation":
        appellation_id = int(detail.get("appellation_id", 0))
        if appellation_id and not inspector.has("appellations", "id", appellation_id):
            blockers.append(
                Blocker(
                    "missing_appellation",
                    "appellation",
                    appellation_id,
                    "high",
                    stop_point,
                    evidence,
                )
            )

    if detail_type == "QuestActCheckCompleteComponent":
        target = int(detail.get("complete_component", 0))
        target_owner = inspector.graph_component_owners.get(target)
        source_quest = int(act["quest_id"])
        if target and target_owner is None:
            blockers.append(
                Blocker(
                    "missing_complete_component_target",
                    "quest_component",
                    target,
                    "high",
                    stop_point,
                    evidence,
                )
            )
        elif target and target_owner != source_quest:
            blockers.append(
                Blocker(
                    "external_complete_component_target",
                    "quest_component",
                    target,
                    "high",
                    stop_point,
                    {**evidence, "target_quest_id": target_owner},
                )
            )

    if detail_type == "QuestActConAcceptComponent":
        target = int(detail.get("quest_context_id", 0))
        source_quest = int(act["quest_id"])
        if (
            target
            and target != source_quest
            and not inspector.has("quest_contexts", "id", target)
        ):
            blockers.append(
                Blocker(
                    "missing_accept_component_quest",
                    "quest",
                    target,
                    "high",
                    stop_point,
                    evidence,
                )
            )

    if detail_type == "QuestActCheckTimer":
        for field, table, entity_kind in (
            ("skill_id", "skills", "skill"),
            ("buff_id", "buffs", "buff"),
            ("timer_npc_id", "npcs", "npc"),
        ):
            entity_id = int(detail.get(field, 0) or 0)
            if entity_id and not inspector.has(table, "id", entity_id):
                blockers.append(
                    Blocker(
                        f"missing_timer_{entity_kind}",
                        entity_kind,
                        entity_id,
                        "high",
                        stop_point,
                        {**evidence, "source_field": field},
                    )
                )
    return blockers


def deduplicate(blockers: Iterable[Blocker]) -> list[Blocker]:
    unique: dict[tuple[Any, ...], Blocker] = {}
    for blocker in blockers:
        key = (
            blocker.kind,
            blocker.entity_kind,
            blocker.entity_id,
            blocker.stop_point,
        )
        unique.setdefault(key, blocker)
    return sorted(
        unique.values(),
        key=lambda item: (
            item.stop_point,
            item.kind,
            item.entity_kind,
            item.entity_id,
        ),
    )


def evaluate_readiness(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    npc_spawn_ids: set[int],
    worldgate_ids: set[int],
) -> tuple[list[dict[str, Any]], dict[int, list[Blocker]]]:
    graph_component_owners = {
        int(row["id"]): int(row["quest_context_id"])
        for row in story["components"]
    }
    inspector = RuntimeInspector(
        connection,
        npc_spawn_ids,
        worldgate_ids,
        graph_component_owners,
    )
    components_by_quest: dict[int, list[dict[str, Any]]] = {}
    for meta in story["component_meta"].values():
        components_by_quest.setdefault(int(meta["quest_id"]), []).append(meta)
    acts_by_quest: dict[int, list[dict[str, Any]]] = {}
    for meta in story["act_meta"].values():
        acts_by_quest.setdefault(int(meta["quest_id"]), []).append(meta)
    items_by_quest: dict[int, list[dict[str, Any]]] = {}
    for item in story["items"]:
        items_by_quest.setdefault(int(item["quest_id"]), []).append(item)
    endpoints_by_quest: dict[int, list[dict[str, Any]]] = {}
    for endpoint in story["endpoints"]:
        endpoints_by_quest.setdefault(int(endpoint["quest_id"]), []).append(endpoint)

    readiness: list[dict[str, Any]] = []
    blockers_by_quest: dict[int, list[Blocker]] = {}
    for quest in story["quests"]:
        quest_id = int(quest["quest_id"])
        chapter = int(quest["chapter_idx"])
        if chapter <= V1_MAX_CHAPTER:
            blockers: list[Blocker] = []
            state = "ready"
            evidence = {"authority": "preserved_v1_prefix", "runtime_audited": True}
        else:
            candidates: list[Blocker] = []
            for item in items_by_quest.get(quest_id, []):
                candidates.extend(
                    inspector.item_blockers(
                        int(item["item_id"]),
                        item_stop_point(item),
                        {
                            "relation_key": item["relation_key"],
                            "item_role": item["item_role"],
                            "selection_mode": item["selection_mode"],
                            "count": item["count"],
                            "grade_id": item["grade_id"],
                            "flags_json": item["flags_json"],
                            "forensic_item_closure_state": item["item_closure_state"],
                        },
                    )
                )
            for endpoint in endpoints_by_quest.get(quest_id, []):
                candidates.extend(inspector.endpoint_blockers(endpoint))
            component_kind = {
                int(row["component_id"]): int(row["component_kind_id"])
                for row in components_by_quest.get(quest_id, [])
            }
            for act in acts_by_quest.get(quest_id, []):
                candidates.extend(
                    direct_act_blockers(
                        inspector,
                        act,
                        component_kind[int(act["component_id"])],
                    )
                )
            blockers = deduplicate(candidates)
            if blockers:
                state = "blocked"
            else:
                state = "ready"
            evidence = {
                "authority": "AA8_nuia_story_graph_v2+runtime_direct_closure",
                "components": len(components_by_quest.get(quest_id, [])),
                "acts": len(acts_by_quest.get(quest_id, [])),
                "items": len(items_by_quest.get(quest_id, [])),
                "endpoints": len(endpoints_by_quest.get(quest_id, [])),
            }
        blockers_by_quest[quest_id] = blockers
        readiness.append(
            {
                "quest_id": quest_id,
                "chapter_idx": chapter,
                "quest_idx": int(quest["quest_idx"]),
                "state": state,
                "blocker_count": len(blockers),
                "recommended_stop_point": blockers[0].stop_point if blockers else "none",
                "evidence_json": json.dumps(
                    evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
            }
        )
    return readiness, blockers_by_quest


def create_audit_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS aaemu_nuia_story_v2_quest_readiness;
        CREATE TABLE aaemu_nuia_story_v2_quest_readiness (
            quest_id INTEGER PRIMARY KEY,
            chapter_idx INTEGER NOT NULL,
            quest_idx INTEGER NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('ready','blocked','pending_validation')),
            enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
            blocker_count INTEGER NOT NULL,
            recommended_stop_point TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );

        DROP TABLE IF EXISTS aaemu_nuia_story_v2_blockers;
        CREATE TABLE aaemu_nuia_story_v2_blockers (
            blocker_key TEXT PRIMARY KEY,
            quest_id INTEGER NOT NULL,
            blocker_kind TEXT NOT NULL,
            entity_kind TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            severity TEXT NOT NULL,
            recommended_stop_point TEXT NOT NULL,
            state TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );
        CREATE INDEX aaemu_nuia_story_v2_blockers_quest_idx
            ON aaemu_nuia_story_v2_blockers(quest_id,blocker_kind,entity_id);

        DROP TABLE IF EXISTS aaemu_nuia_story_v2_materializations;
        CREATE TABLE aaemu_nuia_story_v2_materializations (
            materialization_key TEXT PRIMARY KEY,
            entity_kind TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            authority TEXT NOT NULL,
            state TEXT NOT NULL,
            source_sha256 TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        );

        DROP TABLE IF EXISTS aaemu_nuia_story_v2_transition_gates;
        CREATE TABLE aaemu_nuia_story_v2_transition_gates (
            gate_key TEXT PRIMARY KEY,
            src_quest_id INTEGER NOT NULL,
            dst_quest_id INTEGER NOT NULL,
            gate_kind TEXT NOT NULL,
            forensic_state TEXT NOT NULL,
            enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
            evidence_json TEXT NOT NULL
        );
        """
    )


def ensure_native_v2_schema(
    connection: sqlite3.Connection,
    graph_sha256: str,
) -> None:
    """Preserve AA8 fields that do not exist in the frozen V1 schema.

    This is an additive runtime materialization only.  The forensic graph and
    V1 source compact remain read-only and byte-for-byte unchanged.
    """
    effect_fire_columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(quest_act_obj_effect_fires)")
    }
    if "team_share" not in effect_fire_columns:
        connection.execute(
            "ALTER TABLE quest_act_obj_effect_fires "
            "ADD COLUMN team_share BOOLEAN NOT NULL DEFAULT 0"
        )

    connection.execute(
        "INSERT INTO aaemu_nuia_story_v2_materializations VALUES (?,?,?,?,?,?,?)",
        (
            "schema:quest_act_obj_effect_fires:team_share",
            "runtime_schema_column",
            0,
            "AA8_client_native",
            "active",
            graph_sha256,
            json.dumps(
                {
                    "column": "team_share",
                    "forensic_table": "story_quest_acts.detail_row_json",
                    "runtime_table": "quest_act_obj_effect_fires",
                    "reason": "AA8 QuestActObjEffectFire rows carry team_share; V1 omitted it",
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        ),
    )


def load_confirmed_native_row(
    stage50: sqlite3.Connection,
    entity_key: str,
) -> dict[str, Any]:
    row = stage50.execute(
        "SELECT native_row_key,source_table,state,row_json "
        "FROM native_rows WHERE entity_key=?",
        (entity_key,),
    ).fetchone()
    if row is None or str(row["state"]) != "confirmed":
        raise RuntimeError(f"AA8 Stage 50 row {entity_key} is not confirmed")
    return {
        "native_row_key": str(row["native_row_key"]),
        "source_table": str(row["source_table"]),
        "row": json.loads(str(row["row_json"])),
    }


def normalize_native_skill_effect(
    connection: sqlite3.Connection,
    native_row: dict[str, Any],
) -> dict[str, Any]:
    aliases = {
        "start_high_ability_resource": "start_combat_resource",
        "end_high_ability_resource": "end_combat_resource",
    }
    normalized: dict[str, Any] = {}
    for column in table_columns(connection, "skill_effects"):
        source_column = aliases.get(column, column)
        if source_column not in native_row:
            raise RuntimeError(
                f"AA8 skill effect {native_row.get('id')} lacks runtime field {source_column}"
            )
        normalized[column] = native_row[source_column]
    return normalized


def normalize_native_effect_detail(
    connection: sqlite3.Connection,
    table: str,
    native_row: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Preserve AA8 values across the runtime's pre-AA8 resource names."""
    normalized: dict[str, Any] = {}
    padded: list[str] = []
    for column in connection.execute(f'PRAGMA table_info("{table}")'):
        name = str(column[1])
        source = name.replace("high_ability_resource", "combat_resource")
        if source in native_row:
            normalized[name] = native_row[source]
        else:
            padded.append(name)
            normalized[name] = "" if "TEXT" in str(column[2]).upper() else 0
    return normalized, padded


def materialize_native_skill_closure(
    connection: sqlite3.Connection,
    stage50: sqlite3.Connection,
    skill_id: int,
    expected_application_ids: Iterable[int],
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    if not connection.execute(
        "SELECT 1 FROM skills WHERE id=?", (skill_id,)
    ).fetchone():
        raise RuntimeError(f"AA8 runtime lacks skill template {skill_id}")

    expected_ids = set(map(int, expected_application_ids))
    observed_rows = list(
        stage50.execute(
            "SELECT entity_key,state FROM native_rows "
            "WHERE source_table='skill_effects' "
            "AND CAST(json_extract(row_json,'$.skill_id') AS INTEGER)=?",
            (skill_id,),
        )
    )
    observed_ids = {
        int(str(row["entity_key"]).rsplit(":", 1)[1]) for row in observed_rows
    }
    if observed_ids != expected_ids or any(
        str(row["state"]) != "confirmed" for row in observed_rows
    ):
        raise RuntimeError(
            f"AA8 skill {skill_id} effect set changed: expected {sorted(expected_ids)}, "
            f"observed {sorted(observed_ids)}"
        )

    applications: list[dict[str, Any]] = []
    connection.execute("DELETE FROM skill_effects WHERE skill_id=?", (skill_id,))
    for application_id in sorted(expected_ids):
        application_native = load_confirmed_native_row(
            stage50, f"skill_effect_application:{application_id}"
        )
        application = application_native["row"]
        if int(application["skill_id"]) != skill_id:
            raise RuntimeError(
                f"AA8 application {application_id} no longer belongs to skill {skill_id}"
            )
        effect_id = int(application["effect_id"])
        effect_native = load_confirmed_native_row(stage50, f"effect:{effect_id}")
        effect = effect_native["row"]
        actual_type = str(effect["actual_type"])
        actual_id = int(effect["actual_id"])
        detail_table = actual_effect_table(actual_type)
        detail_native = load_confirmed_native_row(
            stage50, f"effect_detail:{detail_table}:{actual_id}"
        )
        detail = detail_native["row"]
        if int(effect["id"]) != effect_id or int(detail["id"]) != actual_id:
            raise RuntimeError(f"AA8 effect closure identity changed for {effect_id}")
        if not table_exists(connection, detail_table):
            raise RuntimeError(
                f"runtime lacks detail table {detail_table} for AA8 effect {effect_id}"
            )

        consumed_item_id = int(application.get("consume_item_id", 0) or 0)
        if consumed_item_id and not connection.execute(
            "SELECT 1 FROM items WHERE id=?", (consumed_item_id,)
        ).fetchone():
            raise RuntimeError(
                f"AA8 skill {skill_id} consumes missing item {consumed_item_id}"
            )
        if actual_type == "BuffEffect":
            buff_id = int(detail["buff_id"])
            if not connection.execute(
                "SELECT 1 FROM buffs WHERE id=?", (buff_id,)
            ).fetchone():
                raise RuntimeError(
                    f"AA8 skill {skill_id} references missing buff {buff_id}"
                )
        if actual_type == "SpecialEffect" and int(
            detail.get("special_effect_type_id", 0)
        ) == 25:
            return_point_id = int(detail["value1"])
            if return_point_id not in worldgate_ids:
                raise RuntimeError(
                    f"AA8 skill {skill_id} return point {return_point_id} lacks worldgate"
                )

        applications.append(normalize_native_skill_effect(connection, application))
        detail_runtime, detail_padded = normalize_native_effect_detail(
            connection, detail_table, detail
        )
        upsert_rows(connection, "effects", [effect])
        upsert_rows(connection, detail_table, [detail_runtime])
        record_materialization(
            connection,
            f"skill:{skill_id}:effect-application:{application_id}",
            "skill_effect_application",
            application_id,
            "AA8_client_native",
            source_hashes["stage50"],
            {
                "native_row_key": application_native["native_row_key"],
                "effect_native_row_key": effect_native["native_row_key"],
                "detail_native_row_key": detail_native["native_row_key"],
                "skill_id": skill_id,
                "effect_id": effect_id,
                "actual_type": actual_type,
                "actual_id": actual_id,
                "detail_padded_runtime_columns": detail_padded,
                "consume_item_id": consumed_item_id,
                "consume_item_count": int(application.get("consume_item_count", 0) or 0),
            },
        )

    upsert_rows(connection, "skill_effects", applications)


def materialize_block_a_simple_items(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    source_hashes: dict[str, str],
) -> None:
    graph_item_roles: dict[int, list[dict[str, Any]]] = {}
    for relation in story["items"]:
        item_id = int(relation["item_id"])
        if item_id in BLOCK_A_SIMPLE_ITEMS:
            graph_item_roles.setdefault(item_id, []).append(
                {
                    "quest_id": int(relation["quest_id"]),
                    "role": str(relation["item_role"]),
                    "count": int(relation["count"]),
                    "grade_id": int(relation["grade_id"]),
                    "flags": json.loads(str(relation["flags_json"])),
                }
            )
    if set(graph_item_roles) != set(BLOCK_A_SIMPLE_ITEMS):
        raise RuntimeError(
            "Block A item promotion set no longer matches the V2 forensic graph"
        )

    for item_id, concrete_type in sorted(BLOCK_A_SIMPLE_ITEMS.items()):
        item = connection.execute(
            "SELECT impl_id,use_skill_id FROM items WHERE id=?", (item_id,)
        ).fetchone()
        if item is None:
            raise RuntimeError(f"AA8 Block A item {item_id} is absent")
        impl_id, use_skill_id = map(int, item)
        if concrete_type == "open_paper":
            if impl_id != 23 or not connection.execute(
                "SELECT 1 FROM item_open_papers WHERE item_id=?", (item_id,)
            ).fetchone():
                raise RuntimeError(f"AA8 open-paper item {item_id} lost its concrete row")
        elif concrete_type == "armor":
            if impl_id != 2 or not connection.execute(
                "SELECT 1 FROM item_armors WHERE item_id=?", (item_id,)
            ).fetchone():
                raise RuntimeError(f"AA8 armor item {item_id} lost its concrete row")
        elif concrete_type == "generic":
            if impl_id != 0 or use_skill_id != 0:
                raise RuntimeError(
                    f"AA8 generic quest item {item_id} gained an unclosed implementation"
                )
        else:
            raise RuntimeError(f"unsupported bounded item type {concrete_type}")

        connection.execute(
            "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
            "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
            "VALUES (?,?,?,?,?)",
            (
                item_id,
                concrete_type,
                "complete",
                "",
                f"AA8_native:items[{item_id}]+{concrete_type}_runtime_row",
            ),
        )
        record_materialization(
            connection,
            f"item:{item_id}:block-a-runtime-definition",
            "item",
            item_id,
            "AA8_client_native",
            source_hashes["base"],
            {
                "concrete_type": concrete_type,
                "impl_id": impl_id,
                "use_skill_id": use_skill_id,
                "quest_roles": sorted(
                    graph_item_roles[item_id],
                    key=lambda row: (row["quest_id"], row["role"]),
                ),
                "scope_note": (
                    "open-paper reading is outside this quest runtime scope"
                    if concrete_type == "open_paper"
                    else "complete native runtime definition"
                ),
            },
        )


def story_item_roles_for_chapters(
    story: dict[str, Any], chapters: Iterable[int]
) -> dict[int, list[dict[str, Any]]]:
    chapter_set = set(map(int, chapters))
    quest_chapters = {
        int(row["quest_id"]): int(row["chapter_idx"])
        for row in story["quests"]
    }
    result: dict[int, list[dict[str, Any]]] = {}
    for relation in story["items"]:
        quest_id = int(relation["quest_id"])
        if quest_chapters[quest_id] not in chapter_set:
            continue
        item_id = int(relation["item_id"])
        result.setdefault(item_id, []).append(
            {
                "quest_id": quest_id,
                "role": str(relation["item_role"]),
                "count": relation["count"],
                "grade_id": relation["grade_id"],
                "flags_json": str(relation["flags_json"]),
                "native_relation_state": str(relation["native_relation_state"]),
                "item_closure_state": str(relation["item_closure_state"]),
            }
        )
    return result


def native_skill_application_ids(
    stage50: sqlite3.Connection, skill_id: int
) -> tuple[int, ...]:
    rows = list(
        stage50.execute(
            "SELECT entity_key,state FROM native_rows "
            "WHERE source_table='skill_effects' "
            "AND CAST(json_extract(row_json,'$.skill_id') AS INTEGER)=? "
            "ORDER BY entity_key",
            (skill_id,),
        )
    )
    if any(str(row["state"]) != "confirmed" for row in rows):
        raise RuntimeError(f"AA8 skill {skill_id} has non-confirmed applications")
    return tuple(
        sorted(int(str(row["entity_key"]).rsplit(":", 1)[1]) for row in rows)
    )


def native_skill_return_points(
    stage50: sqlite3.Connection, skill_id: int
) -> set[int]:
    result: set[int] = set()
    for application_id in native_skill_application_ids(stage50, skill_id):
        application = load_confirmed_native_row(
            stage50, f"skill_effect_application:{application_id}"
        )["row"]
        effect = load_confirmed_native_row(
            stage50, f"effect:{int(application['effect_id'])}"
        )["row"]
        if str(effect["actual_type"]) != "SpecialEffect":
            continue
        detail = load_confirmed_native_row(
            stage50,
            f"effect_detail:special_effects:{int(effect['actual_id'])}",
        )["row"]
        if int(detail.get("special_effect_type_id", 0)) == 25:
            result.add(int(detail["value1"]))
    return result


def native_skill_missing_dependencies(
    connection: sqlite3.Connection,
    stage50: sqlite3.Connection,
    skill_id: int,
    worldgate_ids: set[int],
) -> list[str]:
    missing: set[str] = set()
    for application_id in native_skill_application_ids(stage50, skill_id):
        application = load_confirmed_native_row(
            stage50, f"skill_effect_application:{application_id}"
        )["row"]
        consumed_item_id = int(application.get("consume_item_id", 0) or 0)
        if consumed_item_id and not connection.execute(
            "SELECT 1 FROM items WHERE id=?", (consumed_item_id,)
        ).fetchone():
            missing.add(f"item:{consumed_item_id}")
        effect = load_confirmed_native_row(
            stage50, f"effect:{int(application['effect_id'])}"
        )["row"]
        detail_table = actual_effect_table(str(effect["actual_type"]))
        if not table_exists(connection, detail_table):
            missing.add(f"runtime_table:{detail_table}")
            continue
        detail_key = f"effect_detail:{detail_table}:{int(effect['actual_id'])}"
        detail_native = stage50.execute(
            "SELECT state,row_json FROM native_rows WHERE entity_key=?",
            (detail_key,),
        ).fetchone()
        if detail_native is None or str(detail_native["state"]) != "confirmed":
            missing.add(detail_key)
            continue
        detail = json.loads(str(detail_native["row_json"]))
        if str(effect["actual_type"]) == "BuffEffect":
            buff_id = int(detail["buff_id"])
            if not connection.execute(
                "SELECT 1 FROM buffs WHERE id=?", (buff_id,)
            ).fetchone():
                missing.add(f"buff:{buff_id}")
        if (
            str(effect["actual_type"]) == "SpecialEffect"
            and int(detail.get("special_effect_type_id", 0)) == 25
            and int(detail["value1"]) not in worldgate_ids
        ):
            missing.add(f"return_point:{int(detail['value1'])}")
    return sorted(missing)


def story_objective_effect_ids(
    story: dict[str, Any], through_chapter: int
) -> set[int]:
    quest_chapters = {
        int(row["quest_id"]): int(row["chapter_idx"])
        for row in story["quests"]
    }
    component_quests = {
        int(row["id"]): int(row["quest_context_id"])
        for row in story["components"]
    }
    details = {
        int(row["id"]): row
        for row in story["details"]["QuestActObjEffectFire"]
    }
    result: set[int] = set()
    for act in story["acts"]:
        if str(act["act_detail_type"]) != "QuestActObjEffectFire":
            continue
        quest_id = component_quests[int(act["quest_component_id"])]
        chapter = quest_chapters[quest_id]
        if not V1_MAX_CHAPTER < chapter <= through_chapter:
            continue
        effect_id = int(details[int(act["act_detail_id"])].get("effect_id", 0) or 0)
        if effect_id:
            result.add(effect_id)
    return result


def materialize_story_objective_effects(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    through_chapter: int,
    stage50_path: Path,
    source_hashes: dict[str, str],
) -> None:
    """Import each exact AA8 effect/detail referenced by ObjEffectFire.

    Effect rows are data, not proof that the objective is executable.  The
    readiness inspector separately validates every runtime dependency exposed
    by the native detail row and keeps the quest blocked when one is absent.
    """
    stage50 = ro(stage50_path)
    try:
        for effect_id in sorted(story_objective_effect_ids(story, through_chapter)):
            effect_native = load_confirmed_native_row(stage50, f"effect:{effect_id}")
            effect = effect_native["row"]
            if int(effect["id"]) != effect_id:
                raise RuntimeError(
                    f"AA8 objective effect {effect_id} lost its native identity"
                )
            actual_type = str(effect["actual_type"])
            actual_id = int(effect["actual_id"])
            detail_table = actual_effect_table(actual_type)
            if not table_exists(connection, detail_table):
                record_materialization(
                    connection,
                    f"objective-effect:{effect_id}:missing-runtime-table",
                    "effect",
                    effect_id,
                    "AA8_client_native",
                    source_hashes["stage50"],
                    {
                        "actual_type": actual_type,
                        "actual_id": actual_id,
                        "detail_table": detail_table,
                    },
                    state="blocked",
                )
                continue
            detail_key = f"effect_detail:{detail_table}:{actual_id}"
            detail_row = stage50.execute(
                "SELECT native_row_key,state,row_json FROM native_rows WHERE entity_key=?",
                (detail_key,),
            ).fetchone()
            if detail_row is None or str(detail_row["state"]) != "confirmed":
                record_materialization(
                    connection,
                    f"objective-effect:{effect_id}:missing-native-detail",
                    "effect",
                    effect_id,
                    "AA8_client_native",
                    source_hashes["stage50"],
                    {
                        "actual_type": actual_type,
                        "actual_id": actual_id,
                        "detail_table": detail_table,
                        "detail_state": None if detail_row is None else str(detail_row["state"]),
                    },
                    state="blocked",
                )
                continue
            detail = json.loads(str(detail_row["row_json"]))
            if int(detail["id"]) != actual_id:
                raise RuntimeError(
                    f"AA8 objective effect {effect_id} detail identity changed"
                )
            effect_runtime, effect_padded = row_for_runtime_schema(
                connection, "effects", effect
            )
            detail_runtime, detail_padded = row_for_runtime_schema(
                connection, detail_table, detail
            )
            upsert_rows(connection, "effects", [effect_runtime])
            upsert_rows(connection, detail_table, [detail_runtime])
            record_materialization(
                connection,
                f"objective-effect:{effect_id}:native-closure",
                "effect",
                effect_id,
                "AA8_client_native",
                source_hashes["stage50"],
                {
                    "effect_native_row_key": effect_native["native_row_key"],
                    "detail_native_row_key": str(detail_row["native_row_key"]),
                    "actual_type": actual_type,
                    "actual_id": actual_id,
                    "detail_table": detail_table,
                    "effect_padded_runtime_columns": effect_padded,
                    "detail_padded_runtime_columns": detail_padded,
                },
            )
    finally:
        stage50.close()


def story_cinema_ids(story: dict[str, Any], through_chapter: int) -> set[int]:
    quest_chapters = {
        int(row["quest_id"]): int(row["chapter_idx"])
        for row in story["quests"]
    }
    component_quests = {
        int(row["id"]): int(row["quest_context_id"])
        for row in story["components"]
    }
    details = {
        int(row["id"]): row for row in story["details"]["QuestActObjCinema"]
    }
    result: set[int] = set()
    for act in story["acts"]:
        if str(act["act_detail_type"]) != "QuestActObjCinema":
            continue
        quest_id = component_quests[int(act["quest_component_id"])]
        chapter = quest_chapters[quest_id]
        if not V1_MAX_CHAPTER < chapter <= through_chapter:
            continue
        cinema_id = int(details[int(act["act_detail_id"])].get("cinema_id", 0) or 0)
        if cinema_id:
            result.add(cinema_id)
    return result


def materialize_story_cinemas(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    through_chapter: int,
    stage40_path: Path,
    source_hashes: dict[str, str],
) -> None:
    stage40 = ro(stage40_path)
    try:
        for cinema_id in sorted(story_cinema_ids(story, through_chapter)):
            native = stage40.execute(
                "SELECT native_row_key,state,row_json FROM native_rows WHERE entity_key=?",
                (f"cinema:{cinema_id}",),
            ).fetchone()
            if native is None or str(native["state"]) != "confirmed":
                record_materialization(
                    connection,
                    f"cinema:{cinema_id}:missing-native-row",
                    "cinema",
                    cinema_id,
                    "AA8_client_native",
                    source_hashes["stage40"],
                    {"native_state": None if native is None else str(native["state"])},
                    state="blocked",
                )
                continue
            row = json.loads(str(native["row_json"]))
            if int(row["id"]) != cinema_id:
                raise RuntimeError(f"AA8 cinema {cinema_id} lost its native identity")
            runtime_row, padded = row_for_runtime_schema(connection, "cinemas", row)
            upsert_rows(connection, "cinemas", [runtime_row])
            record_materialization(
                connection,
                f"cinema:{cinema_id}:native-closure",
                "cinema",
                cinema_id,
                "AA8_client_native",
                source_hashes["stage40"],
                {
                    "native_row_key": str(native["native_row_key"]),
                    "name": str(row["name"]),
                    "replay": int(row["replay"]),
                    "padded_runtime_columns": padded,
                    "client_asset_is_resolved_by_native_cinema_id": True,
                },
            )
    finally:
        stage40.close()


def normalize_native_buff(
    connection: sqlite3.Connection, native_row: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Map renamed AA8 combat-resource fields without losing native values."""
    aliases = {
        "max_high_ability_resource": "max_combat_resource",
        "min_high_ability_resource": "min_combat_resource",
    }
    normalized: dict[str, Any] = {}
    padded: list[str] = []
    for column in table_columns(connection, "buffs"):
        source = aliases.get(column, column)
        if source in native_row:
            normalized[column] = native_row[source]
        else:
            normalized[column] = 0 if column != "name" and column != "desc" else ""
            padded.append(column)
    return normalized, padded


def materialize_safe_story_buffs(
    connection: sqlite3.Connection,
    stage50_path: Path,
    source_hashes: dict[str, str],
) -> None:
    """Materialize only fully executable AA8 buff closures used by Nuia V2.

    Icon and FX-group references are client presentation dependencies and are
    retained in the audit evidence.  Buff references, trigger effects, tick
    effects and server-side SpecialEffect dependencies are closure gates.
    """
    stage50 = ro(stage50_path)
    planned: dict[int, dict[str, Any]] = {}
    visiting: set[int] = set()
    association_tables = (
        "buff_passive_buffs",
        "buff_swap_skills",
        "buff_tick_effects",
        "buff_triggers",
        "buff_unit_modifiers",
    )
    association_index: dict[str, dict[int, list[dict[str, Any]]]] = {}
    for table in association_tables:
        by_buff: dict[int, list[dict[str, Any]]] = {}
        for native in stage50.execute(
            "SELECT native_row_key,state,row_json FROM native_rows "
            "WHERE source_table=? ORDER BY native_row_key",
            (table,),
        ):
            row = json.loads(str(native["row_json"]))
            buff_id = int(row.get("buff_id", 0) or 0)
            if not buff_id:
                continue
            by_buff.setdefault(buff_id, []).append(
                {
                    "native_row_key": str(native["native_row_key"]),
                    "state": str(native["state"]),
                    "row": row,
                }
            )
        association_index[table] = by_buff

    def associated_rows(table: str, buff_id: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for native in association_index[table].get(buff_id, []):
            if str(native["state"]) != "confirmed":
                raise RuntimeError(
                    f"AA8 buff {buff_id} has non-confirmed {table} row "
                    f"{native['native_row_key']}"
                )
            rows.append(
                {
                    "native_row_key": str(native["native_row_key"]),
                    "row": native["row"],
                }
            )
        return rows

    def plan_effect(effect_id: int, owner_buff_id: int) -> dict[str, Any]:
        effect_native = load_confirmed_native_row(stage50, f"effect:{effect_id}")
        effect = effect_native["row"]
        actual_type = str(effect["actual_type"])
        actual_id = int(effect["actual_id"])
        detail_table = actual_effect_table(actual_type)
        if not table_exists(connection, detail_table):
            raise RuntimeError(
                f"AA8 buff {owner_buff_id} effect {effect_id} needs absent runtime "
                f"table {detail_table}"
            )
        detail_native = load_confirmed_native_row(
            stage50, f"effect_detail:{detail_table}:{actual_id}"
        )
        detail = detail_native["row"]

        if actual_type == "BuffEffect":
            plan_buff(int(detail["buff_id"]))
        elif actual_type == "SpecialEffect":
            special_type = int(detail.get("special_effect_type_id", 0) or 0)
            if special_type == 27:  # GainItem, reconstructed in AAEmu runtime.
                item_id = int(detail.get("value1", 0) or 0)
                coverage = connection.execute(
                    "SELECT coverage FROM aaemu_item_definition_coverage "
                    "WHERE item_id=?",
                    (item_id,),
                ).fetchone()
                if coverage is None or str(coverage[0]) != "complete":
                    raise RuntimeError(
                        f"AA8 buff {owner_buff_id} GainItem effect targets "
                        f"non-creatable item {item_id}"
                    )
            else:
                raise RuntimeError(
                    f"AA8 buff {owner_buff_id} needs unvalidated SpecialEffect "
                    f"type {special_type}"
                )
        elif actual_type == "KillNpcWithoutCorpseEffect":
            npc_id = int(detail.get("npc_id", 0) or 0)
            if not connection.execute(
                "SELECT 1 FROM npcs WHERE id=?", (npc_id,)
            ).fetchone():
                raise RuntimeError(
                    f"AA8 buff {owner_buff_id} needs missing NPC {npc_id}"
                )
        elif actual_type not in {"BubbleEffect", "ManaBurnEffect"}:
            raise RuntimeError(
                f"AA8 buff {owner_buff_id} effect type {actual_type} is not "
                "validated by the story-buff reducer"
            )

        return {
            "effect_native_row_key": effect_native["native_row_key"],
            "detail_native_row_key": detail_native["native_row_key"],
            "effect": effect,
            "detail": detail,
            "detail_table": detail_table,
        }

    def plan_buff(buff_id: int) -> None:
        if connection.execute("SELECT 1 FROM buffs WHERE id=?", (buff_id,)).fetchone():
            return
        if buff_id in planned or buff_id in visiting:
            return
        visiting.add(buff_id)
        try:
            native_row = stage50.execute(
                "SELECT native_row_key,source_table,state,row_json FROM native_rows "
                "WHERE entity_key=?",
                (f"buff:{buff_id}",),
            ).fetchone()
            entity = stage50.execute(
                "SELECT state,lifecycle FROM entities WHERE entity_key=?",
                (f"buff:{buff_id}",),
            ).fetchone()
            if (
                native_row is None
                or entity is None
                or str(entity["state"]) != "confirmed"
                or str(entity["lifecycle"]) != "present"
            ):
                raise RuntimeError(
                    f"AA8 buff {buff_id} lacks a confirmed present native entity"
                )
            native = {
                "native_row_key": str(native_row["native_row_key"]),
                "source_table": str(native_row["source_table"]),
                "native_row_state": str(native_row["state"]),
                "row": json.loads(str(native_row["row_json"])),
            }
            row = native["row"]
            presentation: list[dict[str, Any]] = []
            for relation in stage50.execute(
                "SELECT relation,dst_entity_key,state,required FROM relations "
                "WHERE src_entity_key=? AND required=1 "
                "ORDER BY relation,dst_entity_key",
                (f"buff:{buff_id}",),
            ):
                relation_kind = str(relation["relation"])
                destination = str(relation["dst_entity_key"])
                if relation_kind in {"references_icon", "references_fx_group"}:
                    presentation.append(
                        {
                            "relation": relation_kind,
                            "destination": destination,
                            "native_state": str(relation["state"]),
                            "runtime_policy": "client_presentation_nonblocking",
                        }
                    )
                    continue
                if relation_kind == "references_buff":
                    plan_buff(int(destination.rsplit(":", 1)[1]))
                    continue
                raise RuntimeError(
                    f"AA8 buff {buff_id} has unclassified required relation "
                    f"{relation_kind}->{destination}"
                )

            associations: dict[str, list[dict[str, Any]]] = {}
            for table in association_tables:
                associations[table] = associated_rows(table, buff_id)

            effects: dict[int, dict[str, Any]] = {}
            for table in ("buff_tick_effects", "buff_triggers"):
                for association in associations[table]:
                    effect_id = int(association["row"]["effect_id"])
                    effects[effect_id] = plan_effect(effect_id, buff_id)

            normalized, padded = normalize_native_buff(connection, row)
            planned[buff_id] = {
                "native": native,
                "row": normalized,
                "padded": padded,
                "presentation": presentation,
                "associations": associations,
                "effects": effects,
            }
        finally:
            visiting.remove(buff_id)

    try:
        for root_buff_id in sorted(POST_V1_SAFE_STORY_BUFF_ROOTS):
            try:
                plan_buff(root_buff_id)
            except RuntimeError as error:
                record_materialization(
                    connection,
                    f"buff:{root_buff_id}:post-v1-closure-blocked",
                    "buff",
                    root_buff_id,
                    "AA8_client_native",
                    source_hashes["stage50"],
                    {"reason": str(error)},
                    state="blocked",
                )

        for buff_id, bundle in sorted(planned.items()):
            upsert_rows(connection, "buffs", [bundle["row"]])
            for effect_id, effect in sorted(bundle["effects"].items()):
                effect_row, _ = row_for_runtime_schema(
                    connection, "effects", effect["effect"]
                )
                detail_row, _ = normalize_native_effect_detail(
                    connection, effect["detail_table"], effect["detail"]
                )
                upsert_rows(connection, "effects", [effect_row])
                upsert_rows(connection, effect["detail_table"], [detail_row])
            for table, associations in bundle["associations"].items():
                rows = [
                    row_for_runtime_schema(connection, table, entry["row"])[0]
                    for entry in associations
                ]
                if rows:
                    upsert_rows(connection, table, rows)
            record_materialization(
                connection,
                f"buff:{buff_id}:post-v1-native-closure",
                "buff",
                buff_id,
                "AA8_client_native",
                source_hashes["stage50"],
                {
                    "native_row_key": bundle["native"]["native_row_key"],
                    "native_row_state": bundle["native"]["native_row_state"],
                    "padded_runtime_columns": bundle["padded"],
                    "presentation_dependencies": bundle["presentation"],
                    "association_native_rows": {
                        table: [entry["native_row_key"] for entry in rows]
                        for table, rows in bundle["associations"].items()
                    },
                    "effect_ids": sorted(bundle["effects"]),
                    "policy": (
                        "all server-executable dependencies closed; icon and FX "
                        "relations remain client-resolved presentation context"
                    ),
                },
            )
    finally:
        stage50.close()


def materialize_block_b_items(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    stage20_path: Path,
    stage50_path: Path,
    legacy_path: Path,
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    roles = story_item_roles_for_chapters(story, POST_V1_STORY_CHAPTERS)
    stage20 = ro(stage20_path)
    stage50 = ro(stage50_path)
    legacy = ro(legacy_path)
    try:
        for item_id in sorted(roles):
            entity = stage20.execute(
                "SELECT state,lifecycle,authority,provenance,evidence_json "
                "FROM entities WHERE entity_key=?",
                (f"item:{item_id}",),
            ).fetchone()
            if entity is None:
                raise RuntimeError(f"Stage 20 lacks Block B item evidence {item_id}")

            if item_id in BLOCK_B_TOMBSTONE_ITEMS:
                materialization_key = (
                    f"item:{item_id}:block-b-tombstone-legacy-minimum"
                )
                if connection.execute(
                    "SELECT 1 FROM aaemu_nuia_story_v2_materializations "
                    "WHERE materialization_key=?",
                    (materialization_key,),
                ).fetchone():
                    continue
                if str(entity["state"]) != "tombstone":
                    raise RuntimeError(f"AA8 item {item_id} is no longer a tombstone")
                source = legacy.execute(
                    "SELECT * FROM items WHERE id=?", (item_id,)
                ).fetchone()
                if source is None:
                    raise RuntimeError(f"legacy item {item_id} is missing")
                runtime_row, padded = row_for_runtime_schema(
                    connection, "items", dict(source)
                )
                upsert_rows(connection, "items", [runtime_row])
                concrete_type = "generic"
                provenance = (
                    "legacy_3_0_minimal:AA8_native_quest_relation+"
                    f"stage20_tombstone:item{item_id}:nuia-v2-block-b"
                )
                connection.execute(
                    "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
                    "VALUES (?,?,?,?,?)",
                    (item_id, concrete_type, "complete", "", provenance),
                )
                record_materialization(
                    connection,
                    materialization_key,
                    "item",
                    item_id,
                    "AA8_native_relation_legacy_minimum",
                    source_hashes["legacy_compact"],
                    {
                        "stage20_sha256": source_hashes["stage20"],
                        "stage20_state": str(entity["state"]),
                        "stage20_lifecycle": str(entity["lifecycle"]),
                        "stage20_evidence": json.loads(str(entity["evidence_json"])),
                        "padded_runtime_columns": padded,
                        "quest_roles": roles[item_id],
                        "policy": "AA8 proves every quest relation; legacy supplies only the missing item row",
                    },
                )
                continue

            if str(entity["state"]) != "confirmed":
                continue
            item = connection.execute(
                "SELECT impl_id,use_skill_id,buff_id FROM items WHERE id=?",
                (item_id,),
            ).fetchone()
            coverage = connection.execute(
                "SELECT concrete_type,coverage FROM aaemu_item_definition_coverage "
                "WHERE item_id=?",
                (item_id,),
            ).fetchone()
            if item is None or coverage is None or str(coverage["coverage"]) == "complete":
                continue

            concrete_type = str(coverage["concrete_type"])
            descriptor_tables = {
                "armor": "item_armors",
                "accessory": "item_accessories",
                "weapon": "item_weapons",
            }
            descriptor_table = descriptor_tables.get(concrete_type)
            if descriptor_table and not connection.execute(
                f'SELECT 1 FROM "{descriptor_table}" WHERE item_id=?', (item_id,)
            ).fetchone():
                connection.execute(
                    "UPDATE aaemu_item_definition_coverage SET "
                    "missing_dependencies=? WHERE item_id=?",
                    (f"{descriptor_table}:{item_id}", item_id),
                )
                continue
            buff_id = int(item["buff_id"] or 0)
            if buff_id and not connection.execute(
                "SELECT 1 FROM buffs WHERE id=?", (buff_id,)
            ).fetchone():
                connection.execute(
                    "UPDATE aaemu_item_definition_coverage SET "
                    "missing_dependencies=? WHERE item_id=?",
                    (f"buff:{buff_id}", item_id),
                )
                continue

            skill_id = int(item["use_skill_id"] or 0)
            applications: tuple[int, ...] = ()
            if skill_id:
                applications = native_skill_application_ids(stage50, skill_id)
                if not applications:
                    connection.execute(
                        "UPDATE aaemu_item_definition_coverage SET "
                        "missing_dependencies=? WHERE item_id=?",
                        (f"skill:{skill_id}:native_effect_set_empty", item_id),
                    )
                    continue
                missing_skill_dependencies = native_skill_missing_dependencies(
                    connection, stage50, skill_id, worldgate_ids
                )
                if missing_skill_dependencies:
                    connection.execute(
                        "UPDATE aaemu_item_definition_coverage SET "
                        "missing_dependencies=? WHERE item_id=?",
                        (
                            ",".join(missing_skill_dependencies),
                            item_id,
                        ),
                    )
                    continue
                first_key = (
                    f"skill:{skill_id}:effect-application:{applications[0]}"
                )
                already_materialized = connection.execute(
                    "SELECT 1 FROM aaemu_nuia_story_v2_materializations "
                    "WHERE materialization_key=?",
                    (first_key,),
                ).fetchone()
                if already_materialized is None:
                    materialize_native_skill_closure(
                        connection,
                        stage50,
                        skill_id,
                        applications,
                        source_hashes,
                        worldgate_ids,
                    )
                observed_effects = {
                    int(row[0]) for row in connection.execute(
                        "SELECT id FROM skill_effects WHERE skill_id=?", (skill_id,)
                    )
                }
                if observed_effects != set(applications):
                    raise RuntimeError(
                        f"AA8 shared skill {skill_id} runtime effect set changed: "
                        f"{sorted(observed_effects)}"
                    )

            provenance = "AA8_client_native:stage20+runtime_descriptor:nuia-v2-block-b"
            connection.execute(
                "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
                "VALUES (?,?,?,?,?)",
                (item_id, concrete_type, "complete", "", provenance),
            )
            record_materialization(
                connection,
                f"item:{item_id}:block-b-native-runtime-definition",
                "item",
                item_id,
                "AA8_client_native",
                source_hashes["stage20"],
                {
                    "concrete_type": concrete_type,
                    "impl_id": int(item["impl_id"] or 0),
                    "use_skill_id": skill_id,
                    "skill_effect_application_ids": list(applications),
                    "buff_id": buff_id,
                    "quest_roles": roles[item_id],
                },
            )
    finally:
        legacy.close()
        stage50.close()
        stage20.close()


def record_post_v1_return_point_proxies(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    npc_spawns_path: Path,
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    spawns = json.loads(npc_spawns_path.read_text(encoding="utf-8-sig"))
    endpoints = {
        (int(row["quest_id"]), str(row["phase"]), str(row["endpoint_kind"]), int(row["endpoint_id"]))
        for row in story["endpoints"]
    }
    for return_point_id, proxy in sorted(POST_V1_RETURN_POINT_PROXIES.items()):
        if return_point_id not in worldgate_ids:
            raise RuntimeError(
                f"post-V1 return point {return_point_id} lacks its configured worldgate"
            )
        report_npc_id = int(proxy["report_npc_id"])
        for quest_id in proxy["quest_ids"]:
            if (int(quest_id), "report", "npc", report_npc_id) not in endpoints:
                raise RuntimeError(
                    f"return point {return_point_id} lost quest {quest_id} report NPC {report_npc_id}"
                )
        npc_rows = [
            row for row in spawns
            if int(row.get("UnitId", 0) or 0) == report_npc_id
        ]
        if len(npc_rows) != 1:
            raise RuntimeError(
                f"return point {return_point_id} report NPC {report_npc_id} "
                f"spawn count changed: {len(npc_rows)}"
            )
        position = npc_rows[0].get("Position") or {}
        for axis in ("X", "Y", "Z"):
            if abs(float(position[axis]) - float(proxy[axis.lower()])) > 0.0001:
                raise RuntimeError(
                    f"return point {return_point_id} proxy coordinate {axis} changed"
                )
        record_materialization(
            connection,
            f"return-point:{return_point_id}:worldgate-proxy",
            "return_point",
            return_point_id,
            "AA8_native_identity+AA8_npc_spawn_proxy",
            source_hashes["worldgates"],
            {
                "quest_ids": proxy["quest_ids"],
                "report_npc_id": report_npc_id,
                "coordinate_authority": (
                    f"npc_spawns[UnitId={report_npc_id}]"
                ),
                "npc_spawns_sha256": source_hashes["npc_spawns"],
                "zone_id": int(proxy["zone_id"]),
                "x": float(proxy["x"]),
                "y": float(proxy["y"]),
                "z": float(proxy["z"]),
                "proxy_reason": (
                    "AA8 proves the return-point identity but omits server coordinates; "
                    "the quest reports to this uniquely spawned NPC immediately after use"
                ),
            },
        )


def materialize_block_a_client_doodads(
    connection: sqlite3.Connection,
    game11_path: Path,
    stage50_path: Path,
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    doodads = extract_block_a_client_doodads(game11_path)
    stage50 = ro(stage50_path)
    try:
        for skill_id, applications in sorted(BLOCK_A_NATIVE_SKILL_APPLICATIONS.items()):
            materialize_native_skill_closure(
                connection,
                stage50,
                skill_id,
                applications,
                source_hashes,
                worldgate_ids,
            )
    finally:
        stage50.close()

    string_fallbacks: list[dict[str, Any]] = []
    for table in (
        "doodad_almighties",
        "doodad_func_groups",
        "doodad_funcs",
        "doodad_func_quests",
        "doodad_func_uses",
    ):
        clean, fallbacks = sanitize_strings(connection, table, doodads[table])
        string_fallbacks.extend(fallbacks)
        upsert_rows(connection, table, clean)

    for doodad_id in sorted(BLOCK_A_CLIENT_DOODAD_IDS):
        record_materialization(
            connection,
            f"doodad:{doodad_id}:block-a-client-closure",
            "doodad",
            doodad_id,
            "AA8_client_native",
            source_hashes["game11"],
            {
                "client_doodad": 1,
                "logical_identity_preserved": True,
                "string_reference_fallbacks": [
                    row for row in string_fallbacks
                    if row["table"] == "doodad_almighties" and row["id"] == doodad_id
                ],
            },
        )
    for use_id, skill_id in ((10951, 29817), (10952, 29806)):
        if not connection.execute(
            "SELECT 1 FROM doodad_func_uses WHERE id=? AND skill_id=?",
            (use_id, skill_id),
        ).fetchone():
            raise RuntimeError(f"doodad use {use_id} lost skill {skill_id}")
        if not connection.execute(
            "SELECT 1 FROM skill_effects WHERE skill_id=?", (skill_id,)
        ).fetchone():
            raise RuntimeError(f"doodad use skill {skill_id} lacks native effects")
        record_materialization(
            connection,
            f"doodad-func-use:{use_id}:skill:{skill_id}",
            "doodad_func_use",
            use_id,
            "AA8_client_native",
            source_hashes["game11"],
            {"skill_id": skill_id, "binding_source": "doodad_funcs.func_skill_id"},
        )
    record_materialization(
        connection,
        "block-a-client-doodads:string-reference-fallbacks",
        "doodad_string_fallback",
        0,
        "AA8_client_native",
        source_hashes["game11"],
        {"rows": string_fallbacks, "count": len(string_fallbacks)},
    )


def materialize_block_b_client_doodads(
    connection: sqlite3.Connection,
    game11_path: Path,
    stage50_path: Path,
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    doodads = extract_block_b_client_doodads(game11_path)
    use_skills = {
        int(row["skill_id"]) for row in doodads["doodad_func_uses"]
        if int(row["skill_id"])
    }
    stage50 = ro(stage50_path)
    try:
        for skill_id in sorted(use_skills):
            applications = native_skill_application_ids(stage50, skill_id)
            if not applications:
                raise RuntimeError(f"AA8 doodad use skill {skill_id} has no effects")
            materialize_native_skill_closure(
                connection,
                stage50,
                skill_id,
                applications,
                source_hashes,
                worldgate_ids,
            )
    finally:
        stage50.close()
    fallbacks: list[dict[str, Any]] = []
    for table in (
        "doodad_almighties", "doodad_func_groups", "doodad_funcs",
        "doodad_func_quests", "doodad_func_uses",
    ):
        clean, table_fallbacks = sanitize_strings(
            connection, table, doodads[table]
        )
        fallbacks.extend(table_fallbacks)
        upsert_rows(connection, table, clean)
    for doodad_id in sorted(BLOCK_B_CLIENT_DOODAD_IDS):
        record_materialization(
            connection,
            f"doodad:{doodad_id}:block-b-client-closure",
            "doodad",
            doodad_id,
            "AA8_client_native",
            source_hashes["game11"],
            {
                "logical_identity_preserved": True,
                "client_doodad": int(next(
                    row["client_doodad"] for row in doodads["doodad_almighties"]
                    if int(row["id"]) == doodad_id
                )),
                "string_reference_fallbacks": [
                    row for row in fallbacks
                    if row["table"] == "doodad_almighties" and row["id"] == doodad_id
                ],
            },
        )


def materialize_story_client_doodads(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    through_chapter: int,
    game11_path: Path,
    stage50_path: Path,
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    requested_doodads = story_doodad_ids(story, through_chapter)
    stage50 = ro(stage50_path)
    try:
        for effect_id in sorted(story_objective_effect_ids(story, through_chapter)):
            effect = load_confirmed_native_row(
                stage50, f"effect:{effect_id}"
            )["row"]
            if str(effect["actual_type"]) != "InteractionEffect":
                continue
            detail = load_confirmed_native_row(
                stage50,
                f"effect_detail:interaction_effects:{int(effect['actual_id'])}",
            )["row"]
            doodad_id = int(detail.get("doodad_id", 0) or 0)
            if doodad_id:
                requested_doodads.add(doodad_id)
    finally:
        stage50.close()
    closure = extract_story_client_doodads(
        game11_path, requested_doodads
    )
    stage50 = ro(stage50_path)
    try:
        use_skills = {
            int(use["skill_id"]): [
                row for row in closure["doodad_func_uses"]
                if int(row["skill_id"]) == int(use["skill_id"])
            ]
            for use in closure["doodad_func_uses"]
            if int(use["skill_id"])
        }
        for skill_id, uses in sorted(use_skills.items()):
            applications = native_skill_application_ids(stage50, skill_id)
            missing = (
                [f"skill:{skill_id}:native_effect_set_empty"]
                if not applications
                else native_skill_missing_dependencies(
                    connection, stage50, skill_id, worldgate_ids
                )
            )
            if missing:
                record_materialization(
                    connection,
                    f"doodad-use-skill:{skill_id}:post-v1-blocker",
                    "skill",
                    skill_id,
                    "AA8_client_native",
                    source_hashes["stage50"],
                    {"missing_dependencies": missing, "doodad_func_uses": uses},
                    state="blocked",
                )
                continue
            first_key = f"skill:{skill_id}:effect-application:{applications[0]}"
            if not connection.execute(
                "SELECT 1 FROM aaemu_nuia_story_v2_materializations "
                "WHERE materialization_key=?", (first_key,)
            ).fetchone():
                materialize_native_skill_closure(
                    connection,
                    stage50,
                    skill_id,
                    applications,
                    source_hashes,
                    worldgate_ids,
                )
    finally:
        stage50.close()

    fallbacks: list[dict[str, Any]] = []
    for table in (
        "doodad_almighties", "doodad_func_groups", "doodad_funcs",
        "doodad_func_quests", "doodad_func_uses",
    ):
        clean, table_fallbacks = sanitize_strings(
            connection, table, closure[table]
        )
        fallbacks.extend(table_fallbacks)
        upsert_rows(connection, table, clean)
    for doodad_id in closure["found_ids"]:
        record_materialization(
            connection,
            f"doodad:{doodad_id}:post-v1-native-client-closure",
            "doodad",
            int(doodad_id),
            "AA8_client_native",
            source_hashes["game11"],
            {
                "logical_identity_preserved": True,
                "string_reference_fallbacks": [
                    row for row in fallbacks
                    if row["table"] == "doodad_almighties"
                    and row["id"] == int(doodad_id)
                ],
            },
        )
    record_materialization(
        connection,
        "post-v1-story-doodads:game11-coverage",
        "doodad_catalog_coverage",
        0,
        "AA8_client_native",
        source_hashes["game11"],
        {
            "requested_ids": closure["requested_ids"],
            "found_ids": closure["found_ids"],
            "missing_ids": closure["missing_ids"],
        },
        state="blocked" if closure["missing_ids"] else "active",
    )


def materialize_block_a_npc_17903(
    connection: sqlite3.Connection,
    stage30_path: Path,
    npc_spawns_path: Path,
    source_hashes: dict[str, str],
) -> None:
    stage30 = ro(stage30_path)
    try:
        native = load_confirmed_native_row(stage30, "npc:17903")
        required_relations = list(
            stage30.execute(
                "SELECT relation,dst_entity_key,state,required FROM relations "
                "WHERE src_entity_key='npc:17903' AND required=1 "
                "ORDER BY relation,dst_entity_key"
            )
        )
    finally:
        stage30.close()
    npc = native["row"]
    if int(npc["id"]) != 17903:
        raise RuntimeError("AA8 NPC 17903 native identity changed")
    required = {
        (str(row["relation"]), str(row["dst_entity_key"]), str(row["state"]))
        for row in required_relations
    }
    if required != {("uses_model", "model:19", "confirmed")}:
        raise RuntimeError(f"AA8 NPC 17903 required closure changed: {required}")

    runtime_dependencies = {
        "models": 19,
        "equip_pack_cloths": 1184,
        "npc_posture_sets": 150,
        "npc_nicknames": 12,
        "skills": 2,
        "system_factions": 1,
        "ai_files": 15,
        "sound_packs": 148,
    }
    for table, entity_id in runtime_dependencies.items():
        if not connection.execute(
            f'SELECT 1 FROM "{table}" WHERE id=?', (entity_id,)
        ).fetchone():
            raise RuntimeError(
                f"AA8 NPC 17903 runtime dependency {table}[{entity_id}] is absent"
            )

    clean, fallbacks = sanitize_strings(connection, "npcs", [npc])
    upsert_rows(connection, "npcs", clean)
    spawn_rows = [
        row
        for row in json.loads(npc_spawns_path.read_text(encoding="utf-8-sig"))
        if int(row.get("UnitId", 0) or 0) == 17903
    ]
    if len(spawn_rows) != 1:
        raise RuntimeError(f"AA8 NPC 17903 effective spawn count changed: {len(spawn_rows)}")
    spawn = spawn_rows[0]
    position = spawn.get("Position") or {}
    if int(spawn.get("Zone", 0)) != 23 or any(
        key not in position for key in ("X", "Y", "Z")
    ):
        raise RuntimeError("AA8 NPC 17903 effective spawn evidence is incomplete")

    record_materialization(
        connection,
        "npc:17903:block-a-native-template",
        "npc",
        17903,
        "AA8_client_native",
        source_hashes["stage30"],
        {
            "native_row_key": native["native_row_key"],
            "required_relations": sorted(required),
            "runtime_dependencies": runtime_dependencies,
            "string_reference_fallbacks": fallbacks,
        },
    )
    record_materialization(
        connection,
        "npc:17903:effective-spawn",
        "npc_spawn",
        17903,
        "AA8_runtime_spawn_catalog",
        source_hashes["npc_spawns"],
        {
            "spawn_id": int(spawn["Id"]),
            "zone_group_id": int(spawn["Zone"]),
            "x": float(position["X"]),
            "y": float(position["Y"]),
            "z": float(position["Z"]),
            "title": str(spawn.get("Title", "")),
        },
    )


def ensure_stage30_model_schema(
    connection: sqlite3.Connection, stage30_sha256: str
) -> None:
    additions = {
        "models": {
            "auto_adjust_bind_offset": "INTEGER NOT NULL DEFAULT 0",
            "camera_distance_for_action_mode": "REAL NOT NULL DEFAULT 0",
            "camera_distance_for_wide_mode": "REAL NOT NULL DEFAULT 0",
        },
        "actor_models": {
            "model_view_offset_z": "REAL NOT NULL DEFAULT 0",
            "rope_walking_hand_offset_x": "REAL NOT NULL DEFAULT 0",
            "rope_walking_hand_offset_y": "REAL NOT NULL DEFAULT 0",
            "rope_walking_hand_offset_z": "REAL NOT NULL DEFAULT 0",
        },
    }
    added: dict[str, list[str]] = {}
    for table, columns in additions.items():
        existing = set(table_columns(connection, table))
        for column, definition in columns.items():
            if column in existing:
                continue
            connection.execute(
                f'ALTER TABLE "{table}" ADD COLUMN "{column}" {definition}'
            )
            added.setdefault(table, []).append(column)
    record_materialization(
        connection,
        "schema:stage30-aa8-model-columns",
        "runtime_schema_column",
        0,
        "AA8_client_native",
        stage30_sha256,
        {"added_columns": added},
    )


def normalize_stage30_model_row(
    connection: sqlite3.Connection, row: dict[str, Any]
) -> dict[str, Any]:
    result = dict(row)
    if "camera_distance_for_wide_angle" in table_columns(connection, "models"):
        result["camera_distance_for_wide_angle"] = result[
            "camera_distance_for_wide_mode"
        ]
    return result


def materialize_stage30_model_closure(
    connection: sqlite3.Connection,
    stage30: sqlite3.Connection,
    model_id: int,
    source_hashes: dict[str, str],
) -> None:
    if connection.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone():
        return
    native = load_confirmed_native_row(stage30, f"model:{model_id}")
    model = native["row"]
    if str(model["sub_type"]) != "ActorModel":
        raise RuntimeError(
            f"Block B model {model_id} has unsupported subtype {model['sub_type']}"
        )
    actor_model_id = int(model["sub_id"])
    actor_native = load_confirmed_native_row(
        stage30, f"actor_model:{actor_model_id}"
    )
    actor_clean, actor_fallbacks = sanitize_strings(
        connection, "actor_models", [actor_native["row"]]
    )
    upsert_rows(connection, "actor_models", actor_clean)
    model_clean, model_fallbacks = sanitize_strings(
        connection, "models", [normalize_stage30_model_row(connection, model)]
    )
    upsert_rows(connection, "models", model_clean)
    record_materialization(
        connection,
        f"model:{model_id}:block-b-native-closure",
        "model",
        model_id,
        "AA8_client_native",
        source_hashes["stage30"],
        {
            "native_row_key": native["native_row_key"],
            "actor_model_id": actor_model_id,
            "actor_native_row_key": actor_native["native_row_key"],
            "string_reference_fallbacks": actor_fallbacks + model_fallbacks,
            "asset_dependencies": "visual_only_non_required",
        },
    )


def load_story_monster_group_rows(
    stage40: sqlite3.Connection,
    group_ids: Iterable[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    for group_id in sorted(set(map(int, group_ids))):
        native_group = stage40.execute(
            "SELECT state,row_json FROM native_rows WHERE entity_key=?",
            (f"quest_monster_group:{group_id}",),
        ).fetchone()
        if native_group is None or str(native_group["state"]) != "confirmed":
            continue
        groups.append(json.loads(str(native_group["row_json"])))
        native_members = list(
            stage40.execute(
                "SELECT entity_key,state,row_json FROM native_rows "
                "WHERE source_table='quest_monster_npcs' "
                "AND CAST(json_extract(row_json,'$.quest_monster_group_id') AS INTEGER)=? "
                "ORDER BY CAST(json_extract(row_json,'$.id') AS INTEGER)",
                (group_id,),
            )
        )
        if not native_members or any(
            str(row["state"]) != "confirmed" for row in native_members
        ):
            raise RuntimeError(f"AA8 monster group {group_id} member closure changed")
        members.extend(json.loads(str(row["row_json"])) for row in native_members)
    return groups, members


def materialize_story_world_actors(
    connection: sqlite3.Connection,
    story: dict[str, Any],
    through_chapter: int,
    stage30_path: Path,
    stage40_path: Path,
    npc_spawns_path: Path,
    source_hashes: dict[str, str],
) -> None:
    stage30 = ro(stage30_path)
    stage40 = ro(stage40_path)
    try:
        quest_chapters = {
            int(row["quest_id"]): int(row["chapter_idx"])
            for row in story["quests"]
        }
        scoped_quest_ids = {
            quest_id for quest_id, chapter in quest_chapters.items()
            if V1_MAX_CHAPTER < chapter <= through_chapter
        }
        component_quests = {
            int(row["id"]): int(row["quest_context_id"])
            for row in story["components"]
        }
        details_by_type = {
            detail_type: {int(row["id"]): row for row in rows}
            for detail_type, rows in story["details"].items()
        }
        scoped_acts = [
            {
                **row,
                "detail": details_by_type[str(row["act_detail_type"])][
                    int(row["act_detail_id"])
                ],
            }
            for row in story["acts"]
            if component_quests[int(row["quest_component_id"])] in scoped_quest_ids
        ]
        group_ids = {
            int(row["detail"].get("quest_monster_group_id", 0) or 0)
            for row in scoped_acts
            if str(row["act_detail_type"]) in {
                "QuestActConAcceptNpcGroup", "QuestActConReportNpcGroup",
                "QuestActObjMonsterGroupHunt",
            }
        } - {0}
        groups, members = load_story_monster_group_rows(stage40, group_ids)
        upsert_rows(connection, "quest_monster_groups", groups)
        upsert_rows(connection, "quest_monster_npcs", members)
        npc_ids = {
            int(row["npc_id"]) for row in members
        }
        npc_ids |= {
            int(row["endpoint_id"])
            for row in story["endpoints"]
            if int(row["quest_id"]) in scoped_quest_ids
            and str(row["endpoint_kind"]) == "npc"
        }
        for act in scoped_acts:
            if str(act["act_detail_type"]) not in {
                "QuestActObjTalk", "QuestActObjMonsterHunt",
            }:
                continue
            npc_id = int(act["detail"].get("npc_id", 0) or 0)
            if npc_id:
                npc_ids.add(npc_id)
        spawns = json.loads(npc_spawns_path.read_text(encoding="utf-8-sig"))
        spawn_by_npc: dict[int, list[dict[str, Any]]] = {}
        for spawn in spawns:
            spawn_by_npc.setdefault(int(spawn.get("UnitId", 0) or 0), []).append(spawn)

        for npc_id in sorted(npc_ids):
            native_row = stage30.execute(
                "SELECT native_row_key,source_table,state,row_json "
                "FROM native_rows WHERE entity_key=?",
                (f"npc:{npc_id}",),
            ).fetchone()
            if native_row is None or str(native_row["state"]) != "confirmed":
                continue
            native = {
                "native_row_key": str(native_row["native_row_key"]),
                "source_table": str(native_row["source_table"]),
                "row": json.loads(str(native_row["row_json"])),
            }
            npc = native["row"]
            model_id = int(npc["model_id"])
            try:
                materialize_stage30_model_closure(
                    connection, stage30, model_id, source_hashes
                )
            except RuntimeError as error:
                record_materialization(
                    connection,
                    f"npc:{npc_id}:post-v1-model-blocker",
                    "npc",
                    npc_id,
                    "AA8_client_native",
                    source_hashes["stage30"],
                    {"model_id": model_id, "blocker": str(error)},
                    state="blocked",
                )
                continue
            clean, fallbacks = sanitize_strings(connection, "npcs", [npc])
            upsert_rows(connection, "npcs", clean)
            record_materialization(
                connection,
                f"npc:{npc_id}:post-v1-native-template",
                "npc",
                npc_id,
                "AA8_client_native",
                source_hashes["stage30"],
                {
                    "native_row_key": native["native_row_key"],
                    "model_id": model_id,
                    "effective_spawn_count": len(spawn_by_npc.get(npc_id, [])),
                    "string_reference_fallbacks": fallbacks,
                    "nonblocking_context_dependencies": {
                        "npc_nickname_id": int(npc.get("npc_nickname_id", 0) or 0),
                        "npc_posture_set_id": int(npc.get("npc_posture_set_id", 0) or 0),
                        "sound_pack_id": int(npc.get("sound_pack_id", 0) or 0),
                    },
                    "context_policy": (
                        "nickname is stored but never resolved by NpcManager; "
                        "posture and sound are presentation-only and do not gate "
                        "spawn, combat, quest interaction, or persistence"
                    ),
                },
            )
        for group in groups:
            group_id = int(group["id"])
            group_members = [
                row for row in members
                if int(row["quest_monster_group_id"]) == group_id
            ]
            record_materialization(
                connection,
                f"quest-monster-group:{group_id}:post-v1-native-closure",
                "quest_monster_group",
                group_id,
                "AA8_client_native",
                source_hashes["stage40"],
                {
                    "member_rows": group_members,
                    "member_count": len(group_members),
                },
            )
    finally:
        stage40.close()
        stage30.close()


def materialize_block_a_return_item_49628(
    connection: sqlite3.Connection,
    stage50_path: Path,
    source_hashes: dict[str, str],
    worldgate_ids: set[int],
) -> None:
    item = connection.execute(
        "SELECT impl_id,use_skill_id,use_skill_as_reagent FROM items WHERE id=49628"
    ).fetchone()
    if item is None or tuple(map(int, item)) != (0, 38883, 1):
        raise RuntimeError("AA8 item 49628 no longer uses reagent skill 38883")
    return_point = connection.execute(
        "SELECT editor_name,use_additional FROM return_points WHERE id=927"
    ).fetchone()
    if return_point is None or str(return_point[0]) != "quest_shining_shore":
        raise RuntimeError("AA8 return point 927 lost its quest_shining_shore identity")
    if 927 not in worldgate_ids:
        raise RuntimeError("AA8 return point 927 lacks its explicit runtime worldgate")

    stage50 = ro(stage50_path)
    try:
        materialize_native_skill_closure(
            connection,
            stage50,
            38883,
            (54281,),
            source_hashes,
            worldgate_ids,
        )
    finally:
        stage50.close()
    connection.execute(
        "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
        "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
        "VALUES (?,?,?,?,?)",
        (
            49628,
            "generic",
            "complete",
            "",
            "AA8_native:item49628+skill38883+effect70355+special35110+return_point927",
        ),
    )
    record_materialization(
        connection,
        "item:49628:block-a-runtime-closure",
        "item",
        49628,
        "AA8_client_native",
        source_hashes["stage50"],
        {
            "use_skill_id": 38883,
            "use_skill_as_reagent": 1,
            "return_point_id": 927,
            "coverage": "complete",
        },
    )
    record_materialization(
        connection,
        "return-point:927:worldgate-proxy",
        "return_point",
        927,
        "AA8_native_identity+AA8_npc_spawn_proxy",
        source_hashes["worldgates"],
        {
            "logical_identity": "return_points[927]/quest_shining_shore",
            "quest_transition": "7148 objective-use -> NPC 15623 report -> 7149 accept",
            "coordinate_authority": "npc_spawns[UnitId=15623,Zone=61]",
            "destination_zone_authority": "story_quests[7149].zone_id=197",
            "proxy_reason": "AA8 client omits server-side worldgate coordinates",
        },
    )


def ensure_stage30_npc_schema(
    connection: sqlite3.Connection,
    stage30_sha256: str,
) -> None:
    native_columns = {
        "armor_element_level": "INTEGER NOT NULL DEFAULT 0",
        "armor_type_id": "INTEGER NOT NULL DEFAULT 0",
        "engage_combat_bgm_id": "INTEGER NOT NULL DEFAULT 0",
        "friendly_near_quest_id": "INTEGER NOT NULL DEFAULT 0",
        "heir_level": "INTEGER NOT NULL DEFAULT 0",
        "merchant_random_pack_id": "INTEGER NOT NULL DEFAULT 0",
        "multi_jump": "BOOLEAN NOT NULL DEFAULT 0",
        "multi_jump_pow_y": "REAL NOT NULL DEFAULT 0",
        "multi_jump_pow_z": "REAL NOT NULL DEFAULT 0",
        "npc_ai_client_param_id": "INTEGER NOT NULL DEFAULT 0",
        "party_flag": "BOOLEAN NOT NULL DEFAULT 0",
        "ragdoll_after_death_anim": "BOOLEAN NOT NULL DEFAULT 0",
        "run_away_threshold": "REAL NOT NULL DEFAULT 0",
        "tradegood_buy": "BOOLEAN NOT NULL DEFAULT 0",
        "use_hp_bar_split": "BOOLEAN NOT NULL DEFAULT 0",
        "weapon_element_id": "INTEGER NOT NULL DEFAULT 0",
        "weapon_element_level": "INTEGER NOT NULL DEFAULT 0",
    }
    existing = set(table_columns(connection, "npcs"))
    added: list[str] = []
    for column, declaration in native_columns.items():
        if column in existing:
            continue
        connection.execute(f'ALTER TABLE npcs ADD COLUMN "{column}" {declaration}')
        added.append(column)
    record_materialization(
        connection,
        "schema:npcs:stage30-aa8-columns",
        "runtime_schema_columns",
        0,
        "AA8_client_native",
        stage30_sha256,
        {
            "columns": native_columns,
            "added_columns": added,
            "reason": "preserve the exact confirmed AA8 NPC 17903 native row",
        },
    )


def materialize_first_vertical_closure(
    connection: sqlite3.Connection,
    stage50_path: Path,
    source_hashes: dict[str, str],
) -> None:
    """Close quest 7115 with exact AA8 rows and one explicit location proxy.

    AA8 supplies the item, skill, return-point identity and full SpecialEffect
    chain.  The client does not contain server-side worldgate coordinates; the
    static worldgate catalog therefore uses the native AA8 Gleeman Orneon spawn
    in Cinderstone Moor as the minimal reachable proxy for return point 999.
    """
    stage50 = ro(stage50_path)
    try:
        native: dict[str, dict[str, Any]] = {}
        for entity_key in (
            "skill_effect_application:59478",
            "effect:78235",
            "effect_detail:special_effects:44393",
        ):
            row = stage50.execute(
                "SELECT source_table,state,row_json,native_row_key "
                "FROM native_rows WHERE entity_key=?",
                (entity_key,),
            ).fetchone()
            if row is None or str(row[1]) != "confirmed":
                raise RuntimeError(f"AA8 Stage 50 row {entity_key} is not confirmed")
            native[entity_key] = {
                "source_table": str(row[0]),
                "row": json.loads(str(row[2])),
                "native_row_key": str(row[3]),
            }
    finally:
        stage50.close()

    skill_effect = native["skill_effect_application:59478"]["row"]
    effect = native["effect:78235"]["row"]
    special = native["effect_detail:special_effects:44393"]["row"]
    if (
        int(skill_effect["skill_id"]) != 42069
        or int(skill_effect["effect_id"]) != 78235
        or str(effect["actual_type"]) != "SpecialEffect"
        or int(effect["actual_id"]) != 44393
        or int(special["special_effect_type_id"]) != 25
        or int(special["value1"]) != 999
    ):
        raise RuntimeError("quest 7115 AA8 item-use effect closure changed")

    item = connection.execute(
        "SELECT use_skill_id,use_skill_as_reagent FROM items WHERE id=47879"
    ).fetchone()
    return_point = connection.execute(
        "SELECT editor_name,use_additional FROM return_points WHERE id=999"
    ).fetchone()
    if item is None or tuple(map(int, item)) != (42069, 1):
        raise RuntimeError("AA8 item 47879 no longer uses reagent skill 42069")
    if return_point is None or str(return_point[0]) != "quest7115":
        raise RuntimeError("AA8 return point 999 no longer belongs to quest 7115")

    aliases = {
        "start_high_ability_resource": "start_combat_resource",
        "end_high_ability_resource": "end_combat_resource",
    }
    normalized_skill_effect: dict[str, Any] = {}
    for column in table_columns(connection, "skill_effects"):
        source_column = aliases.get(column, column)
        if source_column not in skill_effect:
            raise RuntimeError(
                f"AA8 skill effect 59478 lacks runtime field {source_column}"
            )
        normalized_skill_effect[column] = skill_effect[source_column]
    upsert_rows(connection, "skill_effects", [normalized_skill_effect])
    upsert_rows(connection, "effects", [effect])
    upsert_rows(connection, "special_effects", [special])
    connection.execute(
        "INSERT OR REPLACE INTO aaemu_item_definition_coverage "
        "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
        "VALUES (?,?,?,?,?)",
        (
            47879,
            "generic",
            "complete",
            "",
            "AA8_native:item47879+skill42069+effect78235+special44393+return_point999",
        ),
    )

    materializations = (
        (
            "item:47879:runtime-closure",
            "item",
            47879,
            "AA8_client_native",
            "active",
            source_hashes["stage50"],
            {
                "use_skill_id": 42069,
                "use_skill_as_reagent": 1,
                "coverage": "complete",
            },
        ),
        (
            "skill:42069:effect-application:59478",
            "skill_effect_application",
            59478,
            "AA8_client_native",
            "active",
            source_hashes["stage50"],
            {
                "native_row_key": native["skill_effect_application:59478"]["native_row_key"],
                "skill_id": 42069,
                "effect_id": 78235,
            },
        ),
        (
            "effect:78235:special:44393",
            "effect",
            78235,
            "AA8_client_native",
            "active",
            source_hashes["stage50"],
            {
                "native_row_key": native["effect:78235"]["native_row_key"],
                "actual_type": "SpecialEffect",
                "actual_id": 44393,
            },
        ),
        (
            "special-effect:44393:return-point:999",
            "special_effect",
            44393,
            "AA8_client_native",
            "active",
            source_hashes["stage50"],
            {
                "native_row_key": native["effect_detail:special_effects:44393"]["native_row_key"],
                "special_effect_type_id": 25,
                "return_point_id": 999,
            },
        ),
        (
            "npc:15558:effective-spawn",
            "npc_spawn",
            15558,
            "AA8_runtime_spawn_catalog",
            "active",
            source_hashes["npc_spawns"],
            {
                "zone_group_id": 20,
                "x": 14359.0,
                "y": 11280.0,
                "z": 175.667,
                "title": "Gleeman Orneon",
            },
        ),
        (
            "return-point:999:worldgate-proxy",
            "return_point",
            999,
            "AA8_native_identity+AA8_npc_spawn_proxy",
            "active",
            source_hashes["worldgates"],
            {
                "logical_identity": "return_points[999]/quest7115",
                "coordinate_authority": "npc_spawns[UnitId=15558,Zone=20]",
                "proxy_reason": "AA8 client omits server-side worldgate coordinates",
            },
        ),
    )
    for key, kind, entity_id, authority, state, source_hash, evidence in materializations:
        connection.execute(
            "INSERT INTO aaemu_nuia_story_v2_materializations VALUES (?,?,?,?,?,?,?)",
            (
                key,
                kind,
                entity_id,
                authority,
                state,
                source_hash,
                json.dumps(
                    evidence,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            ),
        )


def snapshot_v1_prefix(connection: sqlite3.Connection) -> dict[str, list[tuple[Any, ...]]]:
    quest_ids = [
        int(row[0])
        for row in connection.execute(
            "SELECT quest_id FROM aaemu_nuia_story_v2_quest_readiness "
            "WHERE chapter_idx<=? ORDER BY quest_id",
            (V1_MAX_CHAPTER,),
        )
    ]
    if len(quest_ids) != 55:
        raise RuntimeError(f"V1 prefix inventory changed: {len(quest_ids)} quests")
    marks = ",".join("?" for _ in quest_ids)
    component_ids = [
        int(row[0])
        for row in connection.execute(
            f"SELECT id FROM quest_components WHERE quest_context_id IN ({marks}) "
            "ORDER BY id",
            quest_ids,
        )
    ]
    component_marks = ",".join("?" for _ in component_ids)
    return {
        "quest_contexts": [
            tuple(row)
            for row in connection.execute(
                f"SELECT * FROM quest_contexts WHERE id IN ({marks}) ORDER BY id",
                quest_ids,
            )
        ],
        "quest_components": [
            tuple(row)
            for row in connection.execute(
                f"SELECT * FROM quest_components WHERE id IN ({component_marks}) ORDER BY id",
                component_ids,
            )
        ],
        "quest_acts": [
            tuple(row)
            for row in connection.execute(
                f"SELECT * FROM quest_acts WHERE quest_component_id IN ({component_marks}) "
                "ORDER BY id",
                component_ids,
            )
        ],
    }


def build(options: argparse.Namespace) -> dict[str, Any]:
    if not V1_MAX_CHAPTER < options.through_chapter <= FINAL_CHAPTER:
        raise RuntimeError("--through-chapter must be between 7 and 31")
    source_hashes = {
        "base": sha256(options.base_runtime),
        "graph": sha256(options.graph),
        "stage20": sha256(options.stage20),
        "stage30": sha256(options.stage30),
        "stage40": sha256(options.stage40),
        "stage50": sha256(options.stage50),
        "legacy_compact": sha256(options.legacy_compact),
        "game11": sha256(options.game11),
        "npc_spawns": sha256(options.npc_spawns),
        "worldgates": sha256(options.worldgates),
    }
    if source_hashes["base"] != EXPECTED_BASE_SHA256:
        raise RuntimeError(
            f"V1 base differs: expected {EXPECTED_BASE_SHA256}, got {source_hashes['base']}"
        )
    if source_hashes["graph"] != EXPECTED_GRAPH_SHA256:
        raise RuntimeError(
            f"V2 graph differs: expected {EXPECTED_GRAPH_SHA256}, got {source_hashes['graph']}"
        )
    expected_auxiliary_hashes = {
        "stage20": EXPECTED_STAGE20_SHA256,
        "stage30": EXPECTED_STAGE30_SHA256,
        "stage40": EXPECTED_STAGE40_SHA256,
        "stage50": EXPECTED_STAGE50_SHA256,
        "legacy_compact": EXPECTED_LEGACY_COMPACT_SHA256,
        "game11": EXPECTED_GAME11_SHA256,
        "npc_spawns": EXPECTED_NPC_SPAWNS_SHA256,
        "worldgates": EXPECTED_WORLDGATES_SHA256,
    }
    for source, expected in expected_auxiliary_hashes.items():
        if source_hashes[source] != expected:
            raise RuntimeError(
                f"{source} differs: expected {expected}, got {source_hashes[source]}"
            )

    npc_spawn_ids = load_effective_npc_spawn_ids(options.npc_spawns)
    worldgate_ids = load_worldgate_ids(options.worldgates)
    if 15558 not in npc_spawn_ids or 15623 not in npc_spawn_ids:
        raise RuntimeError("Block A effective NPC spawn closure is missing")
    if not {927, 999}.issubset(worldgate_ids):
        raise RuntimeError("Block A return-point worldgate closure is missing")

    story = load_graph(options.graph)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    connection = sqlite3.connect(temporary)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")
        create_audit_tables(connection)
        ensure_native_v2_schema(connection, source_hashes["graph"])
        materialize_first_vertical_closure(connection, options.stage50, source_hashes)
        materialize_block_a_simple_items(connection, story, source_hashes)
        materialize_block_a_return_item_49628(
            connection,
            options.stage50,
            source_hashes,
            worldgate_ids,
        )
        ensure_stage30_npc_schema(connection, source_hashes["stage30"])
        materialize_block_a_npc_17903(
            connection,
            options.stage30,
            options.npc_spawns,
            source_hashes,
        )
        materialize_block_a_client_doodads(
            connection,
            options.game11,
            options.stage50,
            source_hashes,
            worldgate_ids,
        )
        if options.through_chapter >= 12:
            record_post_v1_return_point_proxies(
                connection,
                story,
                options.npc_spawns,
                source_hashes,
                worldgate_ids,
            )
            ensure_stage30_model_schema(connection, source_hashes["stage30"])
            materialize_story_world_actors(
                connection,
                story,
                options.through_chapter,
                options.stage30,
                options.stage40,
                options.npc_spawns,
                source_hashes,
            )
            materialize_story_objective_effects(
                connection,
                story,
                options.through_chapter,
                options.stage50,
                source_hashes,
            )
            # First pass closes independent item definitions.  Buff triggers
            # can legitimately grant one of those items, while another story
            # item applies the buff, so the item/buff graph needs a small
            # deterministic fixpoint rather than a hand-authored cycle break.
            materialize_block_b_items(
                connection,
                story,
                options.stage20,
                options.stage50,
                options.legacy_compact,
                source_hashes,
                worldgate_ids,
            )
            materialize_safe_story_buffs(
                connection,
                options.stage50,
                source_hashes,
            )
            materialize_block_b_items(
                connection,
                story,
                options.stage20,
                options.stage50,
                options.legacy_compact,
                source_hashes,
                worldgate_ids,
            )
            materialize_story_cinemas(
                connection,
                story,
                options.through_chapter,
                options.stage40,
                source_hashes,
            )
            materialize_block_b_client_doodads(
                connection,
                options.game11,
                options.stage50,
                source_hashes,
                worldgate_ids,
            )
            materialize_story_client_doodads(
                connection,
                story,
                options.through_chapter,
                options.game11,
                options.stage50,
                source_hashes,
                worldgate_ids,
            )
        readiness, blockers_by_quest = evaluate_readiness(
            connection,
            story,
            npc_spawn_ids,
            worldgate_ids,
        )
        # The story is deployed as one cumulative canonical line.  A later
        # individually-ready quest must not become reachable while an earlier
        # quest remains blocked, otherwise client-side markers can expose an
        # isolated fragment.  V1 is already proven; V2 opens only the longest
        # contiguous ready prefix through the selected chapter.
        enabled_ids = {
            int(row["quest_id"])
            for row in readiness
            if int(row["chapter_idx"]) <= V1_MAX_CHAPTER
        }
        frontier_open = True
        for row in readiness:
            chapter = int(row["chapter_idx"])
            if chapter <= V1_MAX_CHAPTER or chapter > options.through_chapter:
                continue
            if row["state"] != "ready":
                frontier_open = False
            if frontier_open:
                enabled_ids.add(int(row["quest_id"]))

        for row in readiness:
            connection.execute(
                "INSERT INTO aaemu_nuia_story_v2_quest_readiness VALUES (?,?,?,?,?,?,?,?)",
                (
                    row["quest_id"],
                    row["chapter_idx"],
                    row["quest_idx"],
                    row["state"],
                    int(row["quest_id"] in enabled_ids),
                    row["blocker_count"],
                    row["recommended_stop_point"],
                    row["evidence_json"],
                ),
            )
        for quest_id in sorted(blockers_by_quest):
            for blocker in blockers_by_quest[quest_id]:
                connection.execute(
                    "INSERT INTO aaemu_nuia_story_v2_blockers VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        blocker.key(quest_id),
                        quest_id,
                        blocker.kind,
                        blocker.entity_kind,
                        blocker.entity_id,
                        blocker.severity,
                        blocker.stop_point,
                        "open",
                        json.dumps(
                            blocker.evidence,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ),
                )

        readiness_by_id = {int(row["quest_id"]): row for row in readiness}
        for gate in story["transitions"]:
            src = int(gate["src_quest_id"])
            dst = int(gate["dst_quest_id"])
            enabled = int(
                src in enabled_ids
                and dst in enabled_ids
                and readiness_by_id[src]["state"] == "ready"
                and readiness_by_id[dst]["state"] == "ready"
            )
            connection.execute(
                "INSERT INTO aaemu_nuia_story_v2_transition_gates VALUES (?,?,?,?,?,?,?)",
                (
                    gate["gate_key"],
                    src,
                    dst,
                    gate["gate_kind"],
                    gate["state"],
                    enabled,
                    gate["evidence_json"],
                ),
            )

        prefix_before = snapshot_v1_prefix(connection)
        post_v1_story_ids = sorted(
            int(quest["quest_id"])
            for quest in story["quests"]
            if int(quest["chapter_idx"]) > V1_MAX_CHAPTER
        )
        graph_post_v1_component_ids = {
            int(row["id"])
            for row in story["components"]
            if int(row["quest_context_id"]) in post_v1_story_ids
        }
        story_marks = ",".join("?" for _ in post_v1_story_ids)
        historical_post_v1_component_ids = {
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM quest_components WHERE quest_context_id IN "
                f"({story_marks})",
                post_v1_story_ids,
            )
        }
        post_v1_component_ids = sorted(
            graph_post_v1_component_ids | historical_post_v1_component_ids
        )
        # Quarantine every historical post-V1 row first.  The copied compact
        # predates the V2 audit and may contain partial legacy variants; merely
        # declining to upsert them would still leave those variants reachable.
        connection.execute(
            "DELETE FROM quest_acts WHERE quest_component_id IN "
            f"({','.join('?' for _ in post_v1_component_ids)})",
            post_v1_component_ids,
        )
        connection.execute(
            "DELETE FROM quest_components WHERE id IN "
            f"({','.join('?' for _ in post_v1_component_ids)})",
            post_v1_component_ids,
        )
        connection.execute(
            "DELETE FROM quest_contexts WHERE id IN "
            f"({','.join('?' for _ in post_v1_story_ids)})",
            post_v1_story_ids,
        )
        post_v1_enabled = sorted(
            quest_id
            for quest_id in enabled_ids
            if readiness_by_id[quest_id]["chapter_idx"] > V1_MAX_CHAPTER
        )
        if post_v1_enabled:
            quest_rows = [
                quest["native_row"]
                for quest in story["quests"]
                if int(quest["quest_id"]) in post_v1_enabled
            ]
            component_rows = [
                row
                for row in story["components"]
                if int(row["quest_context_id"]) in post_v1_enabled
            ]
            component_ids = {int(row["id"]) for row in component_rows}
            act_rows = [
                row
                for row in story["acts"]
                if int(row["quest_component_id"]) in component_ids
            ]
            upsert_rows(connection, "quest_contexts", quest_rows)
            connection.execute(
                "DELETE FROM quest_acts WHERE quest_component_id IN "
                f"({','.join('?' for _ in component_ids)})",
                sorted(component_ids),
            )
            upsert_rows(connection, "quest_components", component_rows)
            upsert_rows(connection, "quest_acts", act_rows)
            enabled_act_ids = {int(row["id"]) for row in act_rows}
            for detail_type, rows in story["details"].items():
                detail_ids = {
                    int(row["act_detail_id"])
                    for row in act_rows
                    if row["act_detail_type"] == detail_type
                    and int(row["id"]) in enabled_act_ids
                }
                upsert_rows(
                    connection,
                    DETAIL_TABLES[detail_type],
                    [row for row in rows if int(row["id"]) in detail_ids],
                )

        prefix_after = snapshot_v1_prefix(connection)
        if prefix_before != prefix_after:
            raise RuntimeError("V1 executable prefix changed during the V2 build")

        connection.execute(
            "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
            "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
            (
                f"native-nuia-story-v2-chapter{options.through_chapter}",
                "AA8 native Nuia story graph V2; readiness-gated direct closure",
                EXPECTED_GRAPH_SHA256,
                ",".join(map(str, sorted(enabled_ids))),
            ),
        )
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if quick_check != "ok" or integrity_check != "ok":
            raise RuntimeError(
                f"SQLite validation failed: quick={quick_check}, integrity={integrity_check}"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        connection.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        connection.close()

    os.replace(temporary, options.output)
    blocked = [row for row in readiness if row["state"] == "blocked"]
    ready = [row for row in readiness if row["state"] == "ready"]
    document = {
        "format_version": 2,
        "phase": f"native-nuia-story-v2-chapter{options.through_chapter}",
        "authority": "ArcheAge Kakao 8.0.3.12 r558734",
        "sources": {
            "base": {"path": str(options.base_runtime), "sha256": source_hashes["base"]},
            "graph": {"path": str(options.graph), "sha256": source_hashes["graph"]},
            "stage20": {"path": str(options.stage20), "sha256": source_hashes["stage20"]},
            "stage30": {"path": str(options.stage30), "sha256": source_hashes["stage30"]},
            "stage40": {"path": str(options.stage40), "sha256": source_hashes["stage40"]},
            "stage50": {"path": str(options.stage50), "sha256": source_hashes["stage50"]},
            "legacy_compact": {"path": str(options.legacy_compact), "sha256": source_hashes["legacy_compact"]},
            "game11": {"path": str(options.game11), "sha256": source_hashes["game11"]},
            "npc_spawns": {"path": str(options.npc_spawns), "sha256": source_hashes["npc_spawns"]},
            "worldgates": {"path": str(options.worldgates), "sha256": source_hashes["worldgates"]},
        },
        "scope": {
            **EXPECTED_TOTALS,
            "through_chapter": options.through_chapter,
            "v1_prefix_quests": 55,
            "ready_quests": len(ready),
            "blocked_quests": len(blocked),
            "enabled_quest_ids": sorted(enabled_ids),
            "post_v1_enabled_quest_ids": post_v1_enabled,
        },
        "readiness_counts": {
            state: sum(1 for row in readiness if row["state"] == state)
            for state in ("ready", "blocked", "pending_validation")
        },
        "blocker_counts": {
            kind: sum(
                1
                for rows in blockers_by_quest.values()
                for blocker in rows
                if blocker.kind == kind
            )
            for kind in sorted(
                {blocker.kind for rows in blockers_by_quest.values() for blocker in rows}
            )
        },
        "transition_gates": story["transitions"],
        "terminal_audits": story["terminal_audits"],
        "lateral_prerequisite_10159": [
            row
            for row in story["wiki_resolutions"]
            if int(row["raw_dst_quest_id"] or 0) == 10159
        ],
        "safety": {
            "v1_prefix_unchanged": True,
            "unknown_act_types_silently_discarded": False,
            "blocked_quests_materialized": False,
            "forensic_graph_modified": False,
            "wiki_creates_native_relations": False,
        },
        "validation": {
            "quick_check": "ok",
            "integrity_check": "ok",
            "inventory_quests": len(readiness),
            "classified_components": len(story["components"]),
            "classified_acts": len(story["acts"]),
            "classified_act_types": len(DETAIL_TABLES),
        },
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {"deployed": False},
    }
    options.manifest.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--stage20", type=Path, default=DEFAULT_STAGE20)
    parser.add_argument("--stage30", type=Path, default=DEFAULT_STAGE30)
    parser.add_argument("--stage40", type=Path, default=DEFAULT_STAGE40)
    parser.add_argument("--stage50", type=Path, default=DEFAULT_STAGE50)
    parser.add_argument("--legacy-compact", type=Path, default=DEFAULT_LEGACY_COMPACT)
    parser.add_argument("--game11", type=Path, default=DEFAULT_GAME11)
    parser.add_argument("--npc-spawns", type=Path, default=DEFAULT_NPC_SPAWNS)
    parser.add_argument("--worldgates", type=Path, default=DEFAULT_WORLDGATES)
    parser.add_argument("--through-chapter", type=int, default=FINAL_CHAPTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()
    print(json.dumps(build(options), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
