#!/usr/bin/env python3
"""Build the conservative, transversal AA8 native quest runtime catalog.

The builder starts from the validated NPC-visual runtime, replaces the active
quest graph with confirmed Kakao 8.0.3.12 rows that the current server can
execute, and records every excluded quest with machine-readable reasons.
Previously validated quest reconstructions are preserved byte-for-row from the
base runtime because some of them intentionally repair opaque native links.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable


AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
PHASE = "native-quest-catalog-v2"
DOMAIN = Path(__file__).resolve().parent
REPO = DOMAIN.parent
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-npc-visual-v1.sqlite3"
)
DEFAULT_GRAPH = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics"
    r"\aa8-client-knowledge.sqlite"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest-catalog-v2.sqlite3"
)
DEFAULT_MANIFEST = (
    DOMAIN / "generated" / "native-quest-catalog-v2-runtime-manifest.json"
)
EXPECTED_BASE_SHA256 = (
    "A97D4162020F02AA579D2F95AA41B02F90302EC708E3ADD30A0156467281F5F7"
)
EXPECTED_GRAPH_SHA256 = (
    "807BDABAC73BEDE4D5477BDF6A953C709B8D7007BAFB5286EB3C36575D9D36EC"
)

# These quests have explicit runtime/client acceptance checkpoints. Their base
# rows contain bounded repairs (for example quest 330's opaque next_component)
# and therefore remain authoritative validated overrides.
VALIDATED_OVERRIDE_IDS = frozenset({330, 2255, 2256, 2257, 2258, 2532})

# A type enters the active transversal catalog only when it has a concrete
# class, a QuestManager loader, and a confirmed runtime event/reward consumer.
ACT_TABLES = {
    "QuestActConAcceptItem": "quest_act_con_accept_items",
    "QuestActConAcceptNpc": "quest_act_con_accept_npcs",
    "QuestActConAcceptDoodad": "quest_act_con_accept_doodads",
    "QuestActConReportNpc": "quest_act_con_report_npcs",
    "QuestActConReportDoodad": "quest_act_con_report_doodads",
    "QuestActConAutoComplete": "quest_act_con_auto_completes",
    "QuestActObjMonsterHunt": "quest_act_obj_monster_hunts",
    "QuestActObjMonsterGroupHunt": "quest_act_obj_monster_group_hunts",
    "QuestActObjItemGather": "quest_act_obj_item_gathers",
    "QuestActObjItemUse": "quest_act_obj_item_uses",
    "QuestActObjTalk": "quest_act_obj_talks",
    "QuestActObjInteraction": "quest_act_obj_interactions",
    "QuestActSupplyItem": "quest_act_supply_items",
    "QuestActSupplySelectiveItem": "quest_act_supply_selective_items",
    "QuestActSupplyExp": "quest_act_supply_exps",
    "QuestActSupplyCopper": "quest_act_supply_coppers",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    columns = [str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')]
    if not columns:
        raise RuntimeError(f"runtime table is missing: {table}")
    return columns


def confirmed_native_rows(
    graph: sqlite3.Connection, table: str
) -> list[dict[str, Any]]:
    catalog = graph.execute(
        "SELECT state,row_count FROM native_catalogs WHERE table_name=?", (table,)
    ).fetchone()
    if catalog is None or catalog[0] != "confirmed":
        raise RuntimeError(f"native catalog is not confirmed: {table} {catalog}")
    rows = [
        json.loads(row[0])
        for row in graph.execute(
            "SELECT row_json FROM native_rows "
            "WHERE source_table=? AND state='confirmed' ORDER BY CAST(native_id AS INTEGER)",
            (table,),
        )
    ]
    if len(rows) != int(catalog[1]):
        raise RuntimeError(
            f"native row count differs for {table}: {len(rows)} != {catalog[1]}"
        )
    return rows


def rows_by_id(rows: Iterable[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        native_id = int(row["id"])
        if native_id in result:
            raise RuntimeError(f"duplicate native id {native_id}")
        result[native_id] = row
    return result


def select_rows(
    connection: sqlite3.Connection,
    table: str,
    where: str = "",
    parameters: Iterable[Any] = (),
) -> list[dict[str, Any]]:
    connection.row_factory = sqlite3.Row
    sql = f'SELECT * FROM "{table}"'
    if where:
        sql += f" WHERE {where}"
    columns = table_columns(connection, table)
    order = "id" if "id" in columns else columns[0]
    sql += f' ORDER BY "{order}"'
    return [dict(row) for row in connection.execute(sql, tuple(parameters))]


def insert_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: Iterable[dict[str, Any]],
    *,
    replace: bool = False,
) -> int:
    runtime_columns = table_columns(connection, table)
    count = 0
    for row in rows:
        columns = [column for column in runtime_columns if column in row]
        if not columns:
            raise RuntimeError(f"{table}: no shared columns for row {row}")
        verb = "INSERT OR REPLACE" if replace else "INSERT"
        connection.execute(
            f'{verb} INTO "{table}" ('
            + ",".join(f'"{column}"' for column in columns)
            + ") VALUES ("
            + ",".join("?" for _ in columns)
            + ")",
            [row[column] for column in columns],
        )
        count += 1
    return count


def load_sources(
    graph: sqlite3.Connection,
) -> dict[str, Any]:
    tables = {
        "quest_contexts",
        "quest_components",
        "quest_acts",
        "quest_supplies",
        "quest_monster_groups",
        "quest_monster_npcs",
        *ACT_TABLES.values(),
    }
    native = {table: confirmed_native_rows(graph, table) for table in sorted(tables)}
    return {
        "rows": native,
        "contexts": rows_by_id(native["quest_contexts"]),
        "components": rows_by_id(native["quest_components"]),
        "acts": rows_by_id(native["quest_acts"]),
        "details": {
            act_type: rows_by_id(native[table])
            for act_type, table in ACT_TABLES.items()
        },
    }


def audit_server_support(
    native_acts: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    manager_path = REPO / "AAEmu.Game" / "Core" / "Managers" / "QuestManager.cs"
    acts_root = (
        REPO / "AAEmu.Game" / "Models" / "Game" / "Quests" / "Acts"
    )
    manager = manager_path.read_text(encoding="utf-8")
    counts = collections.Counter(row["act_detail_type"] for row in native_acts)
    records: list[dict[str, Any]] = []
    for act_type in sorted(counts):
        has_class = (acts_root / f"{act_type}.cs").is_file()
        has_loader = f'_actTemplates["{act_type}"]' in manager
        enabled = act_type in ACT_TABLES and has_class and has_loader
        reasons = []
        if not has_class:
            reasons.append("missing_backend_class")
        if not has_loader:
            reasons.append("missing_quest_manager_loader")
        if act_type not in ACT_TABLES:
            reasons.append("runtime_consumer_not_confirmed")
        records.append(
            {
                "act_type": act_type,
                "native_rows": counts[act_type],
                "detail_table": ACT_TABLES.get(act_type),
                "has_backend_class": has_class,
                "has_loader": has_loader,
                "enabled": enabled,
                "reason": ",".join(reasons),
            }
        )
    return records


def classify_quests(
    output: sqlite3.Connection,
    source: dict[str, Any],
) -> dict[str, Any]:
    base_context_ids = {
        int(row[0]) for row in output.execute("SELECT id FROM quest_contexts")
    }
    contexts = source["contexts"]
    components_by_quest: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    acts_by_component: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for component in source["components"].values():
        components_by_quest[int(component["quest_context_id"])].append(component)
    for act in source["acts"].values():
        acts_by_component[int(act["quest_component_id"])].append(act)

    npc_ids = {int(row[0]) for row in output.execute("SELECT id FROM npcs")}
    doodad_ids = {
        int(row[0]) for row in output.execute("SELECT id FROM doodad_almighties")
    }
    complete_item_ids = {
        int(row[0])
        for row in output.execute(
            "SELECT item_id FROM aaemu_item_definition_coverage "
            "WHERE coverage='complete' AND missing_dependencies=''"
        )
    }

    monster_members: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for member in source["rows"]["quest_monster_npcs"]:
        monster_members[int(member["quest_monster_group_id"])].append(member)

    records: dict[int, dict[str, Any]] = {}
    enabled_ids: set[int] = set()
    safe_ids: set[int] = set()
    reason_counts: collections.Counter[str] = collections.Counter()
    referenced_group_ids: set[int] = set()

    for quest_id in sorted(contexts):
        components = sorted(
            components_by_quest.get(quest_id, []),
            key=lambda row: (int(row["component_kind_id"]), int(row["id"])),
        )
        component_ids = {int(row["id"]) for row in components}
        reasons: set[str] = set()
        act_types: set[str] = set()
        item_refs: set[int] = set()
        npc_refs: set[int] = set()
        doodad_refs: set[int] = set()
        quest_group_ids: set[int] = set()

        if not components:
            reasons.add("no_components")
        if len(components) < 2:
            reasons.add("unsafe_component_shape")
        kinds = collections.Counter(int(row["component_kind_id"]) for row in components)
        if kinds[2] == 0 or not any(kinds[kind] for kind in (4, 6, 8)):
            reasons.add("unsafe_component_shape")
        if any(count > 10 for count in kinds.values()):
            reasons.add("objective_width_exceeds_server")

        quest_acts: list[dict[str, Any]] = []
        for component in components:
            component_id = int(component["id"])
            component_acts = acts_by_component.get(component_id, [])
            # Empty Supply/Drop/Reward components are valid native shapes: the
            # server either has nothing to grant/remove or uses level supplies.
            # Start, Progress and Ready need at least one executable act.
            if not component_acts and int(component["component_kind_id"]) in {
                1,
                2,
                4,
                6,
            }:
                reasons.add("component_without_executable_act")
            quest_acts.extend(component_acts)

            next_component = int(component.get("next_component") or 0)
            if next_component and next_component not in component_ids:
                reasons.add("dangling_next_component")
            component_npc = int(component.get("npc_id") or 0)
            if component_npc:
                npc_refs.add(component_npc)
                if component_npc not in npc_ids:
                    reasons.add("missing_component_npc")
            for column, reason in (
                ("npc_spawner_id", "component_spawner_dependency"),
                ("skill_id", "component_skill_dependency"),
                ("buff_id", "component_buff_dependency"),
                ("ai_command_set_id", "component_ai_dependency"),
            ):
                if int(component.get(column) or 0):
                    reasons.add(reason)

        for act in quest_acts:
            act_type = str(act["act_detail_type"])
            act_types.add(act_type)
            if act_type not in ACT_TABLES:
                reasons.add(f"unsupported_act:{act_type}")
                continue
            detail = source["details"][act_type].get(int(act["act_detail_id"]))
            if detail is None:
                reasons.add(f"missing_detail:{act_type}")
                continue
            npc_id = int(detail.get("npc_id") or 0)
            if npc_id:
                npc_refs.add(npc_id)
                if npc_id not in npc_ids:
                    reasons.add("missing_npc")

            for column in ("doodad_id", "highlight_doodad_id"):
                doodad_id = int(detail.get(column) or 0)
                if doodad_id:
                    doodad_refs.add(doodad_id)
                    if doodad_id not in doodad_ids:
                        reasons.add("missing_doodad")

            item_id = int(detail.get("item_id") or 0)
            if item_id:
                item_refs.add(item_id)
                if item_id not in complete_item_ids:
                    reasons.add("incomplete_item_definition")

            if act_type == "QuestActObjMonsterGroupHunt":
                group_id = int(detail["quest_monster_group_id"])
                quest_group_ids.add(group_id)
                members = monster_members.get(group_id, [])
                if not members:
                    reasons.add("missing_monster_group")
                elif any(int(member["npc_id"]) not in npc_ids for member in members):
                    reasons.add("monster_group_has_missing_npc")

        if quest_id in VALIDATED_OVERRIDE_IDS:
            state = "validated_override"
            reasons.clear()
            enabled_ids.add(quest_id)
        elif not reasons:
            state = "native_safe"
            enabled_ids.add(quest_id)
            safe_ids.add(quest_id)
            referenced_group_ids.update(quest_group_ids)
        else:
            state = "quarantined"
            reason_counts.update(reasons)

        records[quest_id] = {
            "quest_id": quest_id,
            "state": state,
            "reasons": sorted(reasons),
            "act_types": sorted(act_types),
            "item_ids": sorted(item_refs),
            "npc_ids": sorted(npc_refs),
            "doodad_ids": sorted(doodad_refs),
        }

    missing_overrides = VALIDATED_OVERRIDE_IDS - set(contexts)
    if missing_overrides:
        raise RuntimeError(f"validated overrides absent from native catalog: {missing_overrides}")
    return {
        "records": records,
        "enabled_ids": enabled_ids,
        "safe_ids": safe_ids,
        "override_ids": set(VALIDATED_OVERRIDE_IDS),
        "reason_counts": dict(sorted(reason_counts.items())),
        "components_by_quest": components_by_quest,
        "acts_by_component": acts_by_component,
        "monster_members": monster_members,
        "referenced_group_ids": referenced_group_ids,
        "base_context_ids": base_context_ids,
    }


def capture_overrides(
    output: sqlite3.Connection, classification: dict[str, Any]
) -> dict[str, Any]:
    quest_ids = sorted(classification["override_ids"])
    placeholders = ",".join("?" for _ in quest_ids)
    contexts = select_rows(output, "quest_contexts", f"id IN ({placeholders})", quest_ids)
    if {int(row["id"]) for row in contexts} != set(quest_ids):
        raise RuntimeError("base runtime does not contain every validated override quest")
    components = select_rows(
        output,
        "quest_components",
        f"quest_context_id IN ({placeholders})",
        quest_ids,
    )
    component_ids = [int(row["id"]) for row in components]
    component_placeholders = ",".join("?" for _ in component_ids)
    acts = select_rows(
        output,
        "quest_acts",
        f"quest_component_id IN ({component_placeholders})",
        component_ids,
    )
    details: dict[str, list[dict[str, Any]]] = {}
    for act_type, table in ACT_TABLES.items():
        ids = sorted(
            {
                int(row["act_detail_id"])
                for row in acts
                if row["act_detail_type"] == act_type
            }
        )
        if not ids:
            details[act_type] = []
            continue
        detail_placeholders = ",".join("?" for _ in ids)
        details[act_type] = select_rows(
            output, table, f"id IN ({detail_placeholders})", ids
        )
        if {int(row["id"]) for row in details[act_type]} != set(ids):
            raise RuntimeError(f"validated override has missing {act_type} details")
    unit_reqs = []
    if component_ids:
        unit_reqs = select_rows(
            output,
            "unit_reqs",
            "owner_type='QuestComponent' "
            f"AND owner_id IN ({component_placeholders})",
            component_ids,
        )
    return {
        "contexts": contexts,
        "components": components,
        "acts": acts,
        "details": details,
        "unit_reqs": unit_reqs,
    }


def native_safe_closure(
    source: dict[str, Any], classification: dict[str, Any]
) -> dict[str, Any]:
    safe_ids = classification["safe_ids"]
    contexts = [source["contexts"][quest_id] for quest_id in sorted(safe_ids)]
    components = sorted(
        (
            row
            for quest_id in safe_ids
            for row in classification["components_by_quest"][quest_id]
        ),
        key=lambda row: int(row["id"]),
    )
    component_ids = {int(row["id"]) for row in components}
    acts = sorted(
        (
            row
            for component_id in component_ids
            for row in classification["acts_by_component"][component_id]
        ),
        key=lambda row: int(row["id"]),
    )
    details: dict[str, list[dict[str, Any]]] = {}
    for act_type in ACT_TABLES:
        detail_ids = {
            int(row["act_detail_id"])
            for row in acts
            if row["act_detail_type"] == act_type
        }
        details[act_type] = [
            source["details"][act_type][detail_id]
            for detail_id in sorted(detail_ids)
        ]
    group_ids = {
        int(detail["quest_monster_group_id"])
        for detail in details["QuestActObjMonsterGroupHunt"]
    }
    group_rows = [
        row
        for row in source["rows"]["quest_monster_groups"]
        if int(row["id"]) in group_ids
    ]
    member_rows = sorted(
        (
            row
            for group_id in group_ids
            for row in classification["monster_members"][group_id]
        ),
        key=lambda row: int(row["id"]),
    )
    return {
        "contexts": contexts,
        "components": components,
        "acts": acts,
        "details": details,
        "groups": group_rows,
        "members": member_rows,
    }


def mutate_runtime(
    output: sqlite3.Connection,
    source: dict[str, Any],
    classification: dict[str, Any],
    safe: dict[str, Any],
    overrides: dict[str, Any],
    source_hashes: dict[str, str],
    support: list[dict[str, Any]],
) -> dict[str, Any]:
    output.execute("PRAGMA foreign_keys=OFF")
    output.execute("BEGIN IMMEDIATE")

    for table in ("quest_acts", "quest_components", "quest_contexts"):
        output.execute(f'DELETE FROM "{table}"')
    for table in ACT_TABLES.values():
        output.execute(f'DELETE FROM "{table}"')
    for table in ("quest_supplies", "quest_monster_npcs", "quest_monster_groups"):
        output.execute(f'DELETE FROM "{table}"')
    output.execute("DELETE FROM unit_reqs WHERE owner_type='QuestComponent'")

    counts: dict[str, int] = {}
    for table, key in (
        ("quest_contexts", "contexts"),
        ("quest_components", "components"),
        ("quest_acts", "acts"),
    ):
        counts[f"native_{table}"] = insert_rows(output, table, safe[key])
        counts[f"override_{table}"] = insert_rows(
            output, table, overrides[key], replace=True
        )
    for act_type, table in ACT_TABLES.items():
        counts[f"native_{table}"] = insert_rows(output, table, safe["details"][act_type])
        counts[f"override_{table}"] = insert_rows(
            output, table, overrides["details"][act_type], replace=True
        )

    counts["quest_supplies"] = insert_rows(
        output, "quest_supplies", source["rows"]["quest_supplies"]
    )
    counts["quest_monster_groups"] = insert_rows(
        output, "quest_monster_groups", safe["groups"]
    )
    counts["quest_monster_npcs"] = insert_rows(
        output, "quest_monster_npcs", safe["members"]
    )
    counts["override_unit_reqs"] = insert_rows(
        output, "unit_reqs", overrides["unit_reqs"], replace=True
    )

    output.executescript(
        """
        DROP TABLE IF EXISTS aaemu_native_quest_runtime_catalog;
        CREATE TABLE aaemu_native_quest_runtime_catalog (
            quest_id INTEGER PRIMARY KEY,
            state TEXT NOT NULL,
            reasons_json TEXT NOT NULL,
            act_types_json TEXT NOT NULL,
            item_ids_json TEXT NOT NULL,
            npc_ids_json TEXT NOT NULL,
            doodad_ids_json TEXT NOT NULL,
            authority TEXT NOT NULL
        );
        DROP TABLE IF EXISTS aaemu_native_quest_runtime_act_support;
        CREATE TABLE aaemu_native_quest_runtime_act_support (
            act_type TEXT PRIMARY KEY,
            native_rows INTEGER NOT NULL,
            detail_table TEXT,
            has_backend_class INTEGER NOT NULL,
            has_loader INTEGER NOT NULL,
            enabled INTEGER NOT NULL,
            reason TEXT NOT NULL
        );
        """
    )
    for record in classification["records"].values():
        output.execute(
            "INSERT INTO aaemu_native_quest_runtime_catalog VALUES (?,?,?,?,?,?,?,?)",
            (
                record["quest_id"],
                record["state"],
                json.dumps(record["reasons"], separators=(",", ":")),
                json.dumps(record["act_types"], separators=(",", ":")),
                json.dumps(record["item_ids"], separators=(",", ":")),
                json.dumps(record["npc_ids"], separators=(",", ":")),
                json.dumps(record["doodad_ids"], separators=(",", ":")),
                AUTHORITY,
            ),
        )
    for record in support:
        output.execute(
            "INSERT INTO aaemu_native_quest_runtime_act_support VALUES (?,?,?,?,?,?,?)",
            (
                record["act_type"],
                record["native_rows"],
                record["detail_table"],
                int(record["has_backend_class"]),
                int(record["has_loader"]),
                int(record["enabled"]),
                record["reason"],
            ),
        )

    quest_ids_csv = ",".join(str(value) for value in sorted(classification["enabled_ids"]))
    output.execute(
        "INSERT OR REPLACE INTO aaemu_native_quest_reconstruction "
        "(phase,authority,source_manifest_sha256,quest_ids) VALUES (?,?,?,?)",
        (PHASE, AUTHORITY, source_hashes["graph"], quest_ids_csv),
    )
    output.commit()
    output.execute("VACUUM")
    output.execute("PRAGMA optimize")
    return counts


def canonical_rows(
    connection: sqlite3.Connection, table: str, ids: set[int]
) -> list[tuple[Any, ...]]:
    if not ids:
        return []
    columns = table_columns(connection, table)
    placeholders = ",".join("?" for _ in ids)
    return [
        tuple(row)
        for row in connection.execute(
        f'SELECT {",".join(f"""\"{column}\"""" for column in columns)} '
        f'FROM "{table}" WHERE id IN ({placeholders}) ORDER BY id',
        sorted(ids),
        ).fetchall()
    ]


def validate_output(
    output: sqlite3.Connection,
    source: dict[str, Any],
    classification: dict[str, Any],
    safe: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    enabled_ids = classification["enabled_ids"]
    runtime_ids = {int(row[0]) for row in output.execute("SELECT id FROM quest_contexts")}
    if runtime_ids != enabled_ids:
        raise RuntimeError(
            f"active quest ids differ: runtime={len(runtime_ids)} expected={len(enabled_ids)}"
        )

    audits = {
        "component_without_context": """
            SELECT COUNT(*) FROM quest_components c
            LEFT JOIN quest_contexts q ON q.id=c.quest_context_id
            WHERE q.id IS NULL
        """,
        "act_without_component": """
            SELECT COUNT(*) FROM quest_acts a
            LEFT JOIN quest_components c ON c.id=a.quest_component_id
            WHERE c.id IS NULL
        """,
        "unsupported_active_act": """
            SELECT COUNT(*) FROM quest_acts a
            LEFT JOIN aaemu_native_quest_runtime_act_support s
              ON s.act_type=a.act_detail_type
            WHERE COALESCE(s.enabled,0)=0
        """,
        "catalog_enabled_without_context": """
            SELECT COUNT(*) FROM aaemu_native_quest_runtime_catalog c
            LEFT JOIN quest_contexts q ON q.id=c.quest_id
            WHERE c.state<>'quarantined' AND q.id IS NULL
        """,
        "catalog_quarantined_is_active": """
            SELECT COUNT(*) FROM aaemu_native_quest_runtime_catalog c
            JOIN quest_contexts q ON q.id=c.quest_id
            WHERE c.state='quarantined'
        """,
    }
    for act_type, table in ACT_TABLES.items():
        audits[f"missing_detail:{act_type}"] = f"""
            SELECT COUNT(*) FROM quest_acts a
            LEFT JOIN {table} d ON d.id=a.act_detail_id
            WHERE a.act_detail_type='{act_type}' AND d.id IS NULL
        """
    results = {
        name: int(output.execute(sql).fetchone()[0]) for name, sql in audits.items()
    }
    nonzero = {name: value for name, value in results.items() if value}
    if nonzero:
        raise RuntimeError(f"quest runtime orphan audit failed: {nonzero}")

    # Every non-override row must equal its confirmed native source on the full
    # runtime schema. Overrides must remain equal to their validated base rows.
    equality: dict[str, bool] = {}
    for table, key in (
        ("quest_contexts", "contexts"),
        ("quest_components", "components"),
        ("quest_acts", "acts"),
    ):
        native_rows = safe[key]
        ids = {int(row["id"]) for row in native_rows}
        columns = table_columns(output, table)
        expected = sorted(
            [tuple(row[column] for column in columns) for row in native_rows],
            key=lambda row: row[columns.index("id")],
        )
        actual = canonical_rows(output, table, ids)
        equality[f"native_{table}"] = actual == expected

        override_rows = overrides[key]
        override_ids = {int(row["id"]) for row in override_rows}
        override_expected = sorted(
            [tuple(row[column] for column in columns) for row in override_rows],
            key=lambda row: row[columns.index("id")],
        )
        equality[f"override_{table}"] = (
            canonical_rows(output, table, override_ids) == override_expected
        )
    for act_type, table in ACT_TABLES.items():
        for prefix, rows in (
            ("native", safe["details"][act_type]),
            ("override", overrides["details"][act_type]),
        ):
            ids = {int(row["id"]) for row in rows}
            columns = table_columns(output, table)
            expected = sorted(
                [tuple(row[column] for column in columns) for row in rows],
                key=lambda row: row[columns.index("id")],
            )
            equality[f"{prefix}_{table}"] = canonical_rows(output, table, ids) == expected
    failed = sorted(name for name, equal in equality.items() if not equal)
    if failed:
        raise RuntimeError(f"native/base equality audit failed: {failed}")

    quick = output.execute("PRAGMA quick_check").fetchone()[0]
    integrity = output.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite validation failed: {quick=} {integrity=}")
    return {
        "quick_check": quick,
        "integrity_check": integrity,
        "orphan_audits": results,
        "row_equality": equality,
        "runtime_counts": {
            table: int(output.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in (
                "quest_contexts",
                "quest_components",
                "quest_acts",
                "quest_supplies",
                "quest_monster_groups",
                "quest_monster_npcs",
                "aaemu_native_quest_runtime_catalog",
                "aaemu_native_quest_runtime_act_support",
            )
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    options = parser.parse_args()

    expected = {
        "base_runtime": (options.base_runtime, EXPECTED_BASE_SHA256),
        "graph": (options.graph, EXPECTED_GRAPH_SHA256),
    }
    source_hashes: dict[str, str] = {}
    for name, (path, expected_hash) in expected.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = sha256(path)
        if actual != expected_hash:
            raise RuntimeError(
                f"{name} differs from audited input: {actual} != {expected_hash}"
            )
        source_hashes[name] = actual

    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(options.output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    shutil.copy2(options.base_runtime, temporary)

    output = sqlite3.connect(temporary)
    graph = sqlite3.connect(
        f"file:{options.graph.resolve().as_posix()}?mode=ro", uri=True
    )
    try:
        source = load_sources(graph)
        support = audit_server_support(source["rows"]["quest_acts"])
        classification = classify_quests(output, source)
        overrides = capture_overrides(output, classification)
        safe = native_safe_closure(source, classification)
        mutation = mutate_runtime(
            output,
            source,
            classification,
            safe,
            overrides,
            source_hashes,
            support,
        )
        validation = validate_output(
            output, source, classification, safe, overrides
        )
    except Exception:
        output.rollback()
        output.close()
        graph.close()
        temporary.unlink(missing_ok=True)
        raise
    else:
        output.close()
        graph.close()

    os.replace(temporary, options.output)
    state_counts = collections.Counter(
        record["state"] for record in classification["records"].values()
    )
    base_ids = classification["base_context_ids"]
    enabled_ids = classification["enabled_ids"]
    document = {
        "format_version": 1,
        "phase": PHASE,
        "authority": AUTHORITY,
        "sources": {
            name: {"path": str(path), "sha256": source_hashes[name]}
            for name, (path, _) in expected.items()
        },
        "dossier": {
            "root": "quest:330",
            "json_path": (
                r"E:\AAEmu-Research\output\aa8-client-forensics"
                r"\dossiers\quest-330.json"
            ),
            "json_sha256": (
                "C47AAF43F7BBA5F16D31CD30EBCB9B60A5103C07E13DE39D382DECFBBE82CD68"
            ),
            "readiness": "blocked; used as negative-evidence gate",
        },
        "scope": {
            "native_quest_count": len(source["contexts"]),
            "active_quest_count": len(classification["enabled_ids"]),
            "native_safe_count": state_counts["native_safe"],
            "validated_override_count": state_counts["validated_override"],
            "quarantined_count": state_counts["quarantined"],
            "enabled_act_types": sorted(ACT_TABLES),
            "enabled_act_type_count": len(ACT_TABLES),
            "native_act_type_count": len(support),
            "quarantine_reason_counts": classification["reason_counts"],
            "transition": {
                "base_runtime_quest_count": len(base_ids),
                "shared_with_base": len(base_ids & enabled_ids),
                "new_native_quests": len(enabled_ids - base_ids),
                "base_quests_not_in_candidate": len(base_ids - enabled_ids),
            },
        },
        "negative_evidence": [
            "unit_reqs has no confirmed global native projection; generic quests receive no historical requirements",
            "quest acts without a confirmed server consumer remain quarantined",
            "QuestActConAcceptItem has a native start and cleanup consumer, but its referenced item still requires complete AA8 coverage",
            "objective aliases are accepted only through act types whose server consumer uses a concrete native target",
            "items require complete AA8 runtime definition coverage",
            "NPC and doodad references require an existing AA8 runtime template",
        ],
        "audited_rejections": [
            {
                "root": "quest:1113",
                "dossier_json_path": (
                    r"E:\AAEmu-Research\output\aa8-client-forensics"
                    r"\dossiers\quest-1113.json"
                ),
                "dossier_json_sha256": (
                    "D63BF527EB92160D894ECABE159278986DD9AC81291B255F572B1A5E4B8ED739"
                ),
                "wiki": "https://wiki.archerage.to/na-en/db/quests/1113",
                "blocker": (
                    "item 13974 is a client-native tombstone: referenced by the "
                    "quest and wiki, absent from the complete positive AA8 item catalog"
                ),
            },
            {
                "root": "item:13974",
                "dossier_json_path": (
                    r"E:\AAEmu-Research\output\aa8-client-forensics"
                    r"\dossiers\item-13974.json"
                ),
                "dossier_json_sha256": (
                    "4286BB05D27A046C9957D5EA46BBB1A2F2A9D75E37AADC77CF774E95F887543B"
                ),
                "blocker": "positive identity absent; lifecycle classified as tombstone",
            },
        ],
        "server_support": support,
        "mutation": mutation,
        "validation": validation,
        "output": {
            "path": str(options.output),
            "bytes": options.output.stat().st_size,
            "sha256": sha256(options.output),
        },
        "deployment": {
            "deployed": False,
            "service": "game",
            "reason": (
                "Safety hold: this strict candidate would remove "
                f"{len(base_ids - enabled_ids)} base quest templates and has "
                "no fully closed native starting-zone family yet."
            ),
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
    print(json.dumps(document["scope"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
