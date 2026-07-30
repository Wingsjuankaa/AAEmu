#!/usr/bin/env python3
"""Build reviewed repair proposals from AA8 runtime observations.

All inputs are opened read-only. Observations remain runtime evidence and are
never promoted to client-native authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path


SCHEMA_VERSION = 1
AUTHORITY_BOUNDARY = "observed_runtime_only_not_native_authority"
WIKI_PREFIX = "https://wiki.archerage.to/na-en/db/quests/"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)


def require_checkpointed_observations(path: Path) -> None:
    wal = Path(str(path) + "-wal")
    if wal.exists() and wal.stat().st_size > 0:
        raise RuntimeError(
            "The observation database has an active WAL. Stop the game or "
            "flush/checkpoint the recorder before analysis."
        )


def forensic_graph_identity(path: Path) -> tuple[str, str]:
    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.is_file():
        return file_sha256(path), ""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    database = manifest.get("database", {})
    declared_size = int(database.get("bytes", -1))
    declared_sha = str(database.get("sha256", "")).upper()
    if declared_size != path.stat().st_size or len(declared_sha) != 64:
        raise RuntimeError(
            "Forensic graph does not match its adjacent manifest identity."
        )
    return declared_sha, file_sha256(manifest_path)


def json_array(value: str | None) -> list:
    parsed = json.loads(value or "[]")
    return parsed if isinstance(parsed, list) else []


def load_events(connection: sqlite3.Connection) -> list[dict]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT event_id,session_id,interaction_id,captured_utc,phase,status,
               operation,quest_id,component_id,act_type,detail_id,
               dependency_kind,dependency_id,expected_json,actual_json,
               blocker_code,exception_summary
        FROM observation_events
        ORDER BY captured_utc,event_id
        """
    )
    return [dict(row) for row in rows]


def load_catalog(connection: sqlite3.Connection) -> dict[int, dict]:
    connection.row_factory = sqlite3.Row
    result: dict[int, dict] = {}
    for row in connection.execute(
        """
        SELECT quest_id,state,reasons_json,act_types_json,item_ids_json,
               npc_ids_json,doodad_ids_json,authority
        FROM aaemu_native_quest_runtime_catalog
        ORDER BY quest_id
        """
    ):
        data = dict(row)
        data["act_types"] = set(json_array(data["act_types_json"]))
        data["item_ids"] = {int(value) for value in json_array(data["item_ids_json"])}
        result[int(data["quest_id"])] = data
    return result


def load_native_item_relations(connection: sqlite3.Connection) -> list[dict]:
    def rows(source_table: str) -> list[dict]:
        result = []
        for state, row_json, provenance in connection.execute(
            """
            SELECT state,row_json,provenance
            FROM native_rows
            WHERE source_table=?
            ORDER BY native_id
            """,
            (source_table,),
        ):
            if state != "confirmed":
                continue
            row = json.loads(row_json)
            row["_provenance"] = provenance
            result.append(row)
        return result

    components = {
        int(row["id"]): int(row["quest_context_id"])
        for row in rows("quest_components")
    }
    relevant_types = {
        "QuestActSupplyItem": "quest_act_supply_items",
        "QuestActSupplySelectiveItem": "quest_act_supply_selective_items",
    }
    acts = []
    for row in rows("quest_acts"):
        if row.get("act_detail_type") in relevant_types:
            acts.append(row)
    details = {}
    for act_type, source_table in relevant_types.items():
        for row in rows(source_table):
            details[(act_type, int(row["id"]))] = (row, source_table)

    result = []
    for act in acts:
        act_type = act["act_detail_type"]
        detail_id = int(act["act_detail_id"])
        component_id = int(act["quest_component_id"])
        quest_id = components.get(component_id)
        detail = details.get((act_type, detail_id))
        if quest_id is None or detail is None:
            continue
        detail_row, source_table = detail
        result.append(
            {
                "quest_id": quest_id,
                "act_type": act_type,
                "item_id": int(detail_row["item_id"]),
                "detail_native_id": f"{source_table}:{detail_id}",
                "relation_state": "confirmed",
                "relation_authority": "client_native",
                "provenance": detail_row["_provenance"],
                "locator": f"{source_table}[{detail_id}].item_id",
            }
        )
    return sorted(
        result,
        key=lambda row: (
            row["quest_id"],
            row["act_type"],
            row["item_id"],
            row["detail_native_id"],
        ),
    )


def event_family_keys(event: dict) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    if event["act_type"]:
        keys.append((f"quest_act:{event['act_type']}", "capability"))
    if event["dependency_kind"] and event["dependency_id"]:
        keys.append(
            (
                f"dependency:{event['dependency_kind']}:{event['dependency_id']}",
                "dependency",
            )
        )
    if event["blocker_code"]:
        keys.append((f"blocker:{event['blocker_code']}", "blocker"))
    if not keys:
        keys.append((f"operation:{event['operation']}", "operation"))
    return keys


def proposal_for(key: str) -> str:
    if key == "quest_act:QuestActSupplyItem":
        return (
            "Review the generic QuestActSupplyItem materialization path and "
            "close each referenced item definition before catalog promotion."
        )
    if key == "quest_act:QuestActSupplySelectiveItem":
        return (
            "Review the generic selective reward path, 1-based selection, "
            "atomic inventory preflight, and referenced item definitions."
        )
    if key.startswith("dependency:item:"):
        return (
            f"Close native item {key.rsplit(':', 1)[-1]} and its reachable "
            "descriptor/use-skill dependencies; then re-evaluate every linked quest."
        )
    if key.startswith("blocker:"):
        return (
            "Reproduce one representative case, resolve the shared blocker, "
            "and rebuild the strict catalog before enabling affected quests."
        )
    return "Review the shared runtime primitive and its native AA8 closure."


def create_output_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA page_size=4096;
        PRAGMA journal_mode=DELETE;
        PRAGMA synchronous=OFF;
        CREATE TABLE knowledge_metadata(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE capability_families(
            family_key TEXT PRIMARY KEY,
            family_kind TEXT NOT NULL,
            observed_count INTEGER NOT NULL,
            blocked_count INTEGER NOT NULL,
            affected_native_quests INTEGER NOT NULL,
            priority_score INTEGER NOT NULL,
            authority_boundary TEXT NOT NULL,
            proposal TEXT NOT NULL
        );
        CREATE TABLE family_observations(
            family_key TEXT NOT NULL,
            event_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            quest_id INTEGER,
            status TEXT NOT NULL,
            blocker_code TEXT,
            PRIMARY KEY(family_key,event_id)
        );
        CREATE TABLE family_quests(
            family_key TEXT NOT NULL,
            quest_id INTEGER NOT NULL,
            native_state TEXT NOT NULL,
            relation_state TEXT NOT NULL,
            relation_authority TEXT NOT NULL,
            evidence_locator TEXT NOT NULL,
            PRIMARY KEY(family_key,quest_id,evidence_locator)
        );
        CREATE TABLE quest_item_relations(
            quest_id INTEGER NOT NULL,
            act_type TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            detail_native_id TEXT NOT NULL,
            relation_state TEXT NOT NULL,
            relation_authority TEXT NOT NULL,
            provenance TEXT NOT NULL,
            locator TEXT NOT NULL,
            PRIMARY KEY(quest_id,act_type,item_id,detail_native_id)
        );
        CREATE TABLE wiki_review_queue(
            quest_id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            review_status TEXT NOT NULL,
            authority_boundary TEXT NOT NULL
        );
        CREATE INDEX ix_family_quests_quest
        ON family_quests(quest_id,family_key);
        CREATE INDEX ix_quest_item_relations_item
        ON quest_item_relations(item_id,act_type,quest_id);
        """
    )


def build(args: argparse.Namespace) -> dict:
    observations = Path(args.observations).resolve()
    compact = Path(args.compact).resolve()
    graph = Path(args.forensic_graph).resolve()
    output_dir = Path(args.output).resolve()
    for source in (observations, compact, graph):
        if not source.is_file():
            raise FileNotFoundError(source)
    require_checkpointed_observations(observations)
    output_dir.mkdir(parents=True, exist_ok=True)

    with closing(open_readonly(observations)) as observed_db:
        events = load_events(observed_db)
    with closing(open_readonly(compact)) as compact_db:
        catalog = load_catalog(compact_db)
    with closing(open_readonly(graph)) as graph_db:
        native_item_relations = load_native_item_relations(graph_db)
        graph_metadata = dict(
            graph_db.execute("SELECT key,value FROM metadata ORDER BY key")
        )
    graph_sha256, graph_manifest_sha256 = forensic_graph_identity(graph)
    input_hashes = {
        "observations": file_sha256(observations),
        "compact": file_sha256(compact),
        "forensic_graph": graph_sha256,
    }

    family_events: dict[str, list[dict]] = defaultdict(list)
    family_kinds: dict[str, str] = {}
    for event in events:
        for family_key, family_kind in event_family_keys(event):
            family_events[family_key].append(event)
            family_kinds[family_key] = family_kind

    item_relations_by_item: dict[int, list[dict]] = defaultdict(list)
    item_relations_by_act: dict[str, list[dict]] = defaultdict(list)
    for relation in native_item_relations:
        item_relations_by_item[int(relation["item_id"])].append(relation)
        item_relations_by_act[relation["act_type"]].append(relation)

    family_quests: dict[str, dict[tuple[int, str], dict]] = defaultdict(dict)
    for family_key in family_events:
        if family_key.startswith("quest_act:"):
            act_type = family_key.split(":", 1)[1]
            exact = item_relations_by_act.get(act_type, [])
            if exact:
                for relation in exact:
                    quest_id = int(relation["quest_id"])
                    if quest_id not in catalog:
                        continue
                    locator = relation["locator"]
                    family_quests[family_key][(quest_id, locator)] = {
                        "quest_id": quest_id,
                        "native_state": catalog[quest_id]["state"],
                        "relation_state": relation["relation_state"],
                        "relation_authority": relation["relation_authority"],
                        "evidence_locator": locator,
                    }
            else:
                for quest_id, entry in catalog.items():
                    if act_type in entry["act_types"]:
                        locator = (
                            "aaemu_native_quest_runtime_catalog"
                            f"[{quest_id}].act_types_json"
                        )
                        family_quests[family_key][(quest_id, locator)] = {
                            "quest_id": quest_id,
                            "native_state": entry["state"],
                            "relation_state": "catalog_classified",
                            "relation_authority": entry["authority"],
                            "evidence_locator": locator,
                        }
        elif family_key.startswith("dependency:item:"):
            item_id = int(family_key.rsplit(":", 1)[1])
            for relation in item_relations_by_item.get(item_id, []):
                quest_id = int(relation["quest_id"])
                if quest_id not in catalog:
                    continue
                locator = relation["locator"]
                family_quests[family_key][(quest_id, locator)] = {
                    "quest_id": quest_id,
                    "native_state": catalog[quest_id]["state"],
                    "relation_state": relation["relation_state"],
                    "relation_authority": relation["relation_authority"],
                    "evidence_locator": locator,
                }
        else:
            for event in family_events[family_key]:
                quest_id = int(event["quest_id"] or 0)
                if not quest_id or quest_id not in catalog:
                    continue
                locator = f"observation_event:{event['event_id']}"
                family_quests[family_key][(quest_id, locator)] = {
                    "quest_id": quest_id,
                    "native_state": catalog[quest_id]["state"],
                    "relation_state": "observed_only",
                    "relation_authority": AUTHORITY_BOUNDARY,
                    "evidence_locator": locator,
                }

    output_db = output_dir / "aa8-runtime-knowledge-v1.sqlite3"
    if output_db.exists():
        output_db.unlink()
    with closing(sqlite3.connect(output_db)) as out:
        create_output_schema(out)
        metadata = {
            "schema_name": "AA8_RUNTIME_KNOWLEDGE",
            "schema_version": str(SCHEMA_VERSION),
            "authority_boundary": AUTHORITY_BOUNDARY,
            "observations_sha256": input_hashes["observations"],
            "compact_sha256": input_hashes["compact"],
            "forensic_graph_sha256": input_hashes["forensic_graph"],
            "forensic_graph_manifest_sha256": graph_manifest_sha256,
            "client_build": graph_metadata.get("client_build", "unknown"),
        }
        out.executemany(
            "INSERT INTO knowledge_metadata(key,value) VALUES(?,?)",
            sorted(metadata.items()),
        )

        for relation in native_item_relations:
            out.execute(
                """
                INSERT INTO quest_item_relations VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    relation["quest_id"],
                    relation["act_type"],
                    relation["item_id"],
                    relation["detail_native_id"],
                    relation["relation_state"],
                    relation["relation_authority"],
                    relation["provenance"],
                    relation["locator"],
                ),
            )

        wiki_quests: set[int] = set()
        family_rows = []
        for family_key in sorted(family_events):
            observed = family_events[family_key]
            blocked = sum(
                event["status"] == "blocked" or bool(event["exception_summary"])
                for event in observed
            )
            affected = {
                row["quest_id"] for row in family_quests[family_key].values()
            }
            score = len(affected) * 100 + blocked * 10 + len(observed)
            family_rows.append(
                {
                    "family_key": family_key,
                    "family_kind": family_kinds[family_key],
                    "observed_count": len(observed),
                    "blocked_count": blocked,
                    "affected_native_quests": len(affected),
                    "priority_score": score,
                    "proposal": proposal_for(family_key),
                }
            )
            out.execute(
                "INSERT INTO capability_families VALUES(?,?,?,?,?,?,?,?)",
                (
                    family_key,
                    family_kinds[family_key],
                    len(observed),
                    blocked,
                    len(affected),
                    score,
                    AUTHORITY_BOUNDARY,
                    proposal_for(family_key),
                ),
            )
            for event in sorted(observed, key=lambda row: row["event_id"]):
                out.execute(
                    "INSERT INTO family_observations VALUES(?,?,?,?,?,?)",
                    (
                        family_key,
                        event["event_id"],
                        event["session_id"],
                        event["quest_id"],
                        event["status"],
                        event["blocker_code"],
                    ),
                )
                if event["quest_id"]:
                    wiki_quests.add(int(event["quest_id"]))
            for row in sorted(
                family_quests[family_key].values(),
                key=lambda value: (
                    value["quest_id"],
                    value["evidence_locator"],
                ),
            ):
                out.execute(
                    "INSERT INTO family_quests VALUES(?,?,?,?,?,?)",
                    (
                        family_key,
                        row["quest_id"],
                        row["native_state"],
                        row["relation_state"],
                        row["relation_authority"],
                        row["evidence_locator"],
                    ),
                )
                wiki_quests.add(row["quest_id"])

        for quest_id in sorted(wiki_quests):
            out.execute(
                "INSERT INTO wiki_review_queue VALUES(?,?,?,?)",
                (
                    quest_id,
                    f"{WIKI_PREFIX}{quest_id}",
                    "pending",
                    "visible_corroboration_only",
                ),
            )
        out.commit()
        out.execute("VACUUM")

    ranked = sorted(
        family_rows,
        key=lambda row: (-row["priority_score"], row["family_key"]),
    )
    summary = {
        "schema": "AA8_RUNTIME_KNOWLEDGE_SUMMARY_V1",
        "authority_boundary": AUTHORITY_BOUNDARY,
        "event_count": len(events),
        "family_count": len(ranked),
        "native_item_relation_count": len(native_item_relations),
        "ranked_families": ranked,
    }
    manifest = {
        "schema": "AA8_RUNTIME_KNOWLEDGE_MANIFEST_V1",
        "schema_version": SCHEMA_VERSION,
        "authority_boundary": AUTHORITY_BOUNDARY,
        "inputs": {
            "observations": {
                "path": str(observations),
                "sha256": input_hashes["observations"],
            },
            "compact": {
                "path": str(compact),
                "sha256": input_hashes["compact"],
            },
            "forensic_graph": {
                "path": str(graph),
                "sha256": input_hashes["forensic_graph"],
                "identity_source": (
                    "adjacent_manifest"
                    if graph_manifest_sha256
                    else "physical_file_hash"
                ),
                "manifest_sha256": graph_manifest_sha256,
            },
        },
        "outputs": {
            "database": output_db.name,
            "database_sha256": file_sha256(output_db),
            "summary": "aa8-runtime-knowledge-v1-summary.json",
            "report": "aa8-runtime-knowledge-v1-report.md",
        },
        "counts": {
            "events": len(events),
            "families": len(ranked),
            "catalog_quests": len(catalog),
            "native_item_relations": len(native_item_relations),
        },
    }

    (output_dir / "aa8-runtime-knowledge-v1-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report_lines = [
        "# AA8 runtime quest knowledge V1",
        "",
        f"Authority boundary: `{AUTHORITY_BOUNDARY}`.",
        "",
        "| Priority | Family | Observed | Blocked | Native quests |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in ranked:
        report_lines.append(
            f"| {row['priority_score']} | `{row['family_key']}` | "
            f"{row['observed_count']} | {row['blocked_count']} | "
            f"{row['affected_native_quests']} |"
        )
    report_lines.extend(
        [
            "",
            "Observations propose work; only confirmed client-native relations "
            "in the forensic graph may authorize runtime promotion.",
            "",
        ]
    )
    (output_dir / "aa8-runtime-knowledge-v1-report.md").write_text(
        "\n".join(report_lines),
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "aa8-runtime-knowledge-v1-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", required=True)
    parser.add_argument("--compact", required=True)
    parser.add_argument("--forensic-graph", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), indent=2, sort_keys=True))
