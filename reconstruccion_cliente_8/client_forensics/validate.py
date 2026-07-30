from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .schema import open_read_only, table_count


REQUIRED_TABLES = {
    "artifacts",
    "assets",
    "cached_result_rows",
    "cached_results",
    "consumers",
    "coverage",
    "decoders",
    "entities",
    "entity_properties",
    "gaps",
    "localizations",
    "metadata",
    "native_catalogs",
    "native_rows",
    "opaque_regions",
    "query_specs",
    "relations",
    "review_manifests",
    "source_records",
    "stage_lineage",
    "surface_inventory",
    "surfaces",
    "validation_events",
    "wiki_entities",
    "wiki_properties",
    "wiki_relations",
}

CLOSURE_TABLES = {
    "blocker_roots",
    "blocker_impacts",
    "blocker_evidence",
    "work_queue",
}


def _scalar(connection: sqlite3.Connection, sql: str) -> int:
    return int(connection.execute(sql).fetchone()[0])


def validate_database(path: Path, *, consolidated: bool | None = None) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = open_read_only(path)
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        present_tables = {
            str(row[0])
            for row in connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
            )
        }
        schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        required_tables = REQUIRED_TABLES | (
            CLOSURE_TABLES if schema_version >= 2 else set()
        )
        missing_tables = sorted(required_tables - present_tables)
        if missing_tables:
            raise RuntimeError(f"Missing canonical tables: {missing_tables}")

        checks = {
            "orphan_properties": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM entity_properties p
                LEFT JOIN entities e ON e.entity_key=p.entity_key
                WHERE e.entity_key IS NULL
                """,
            ),
            "orphan_relation_sources": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM relations r
                LEFT JOIN entities e ON e.entity_key=r.src_entity_key
                WHERE e.entity_key IS NULL
                """,
            ),
            "orphan_relation_destinations": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM relations r
                LEFT JOIN entities e ON e.entity_key=r.dst_entity_key
                WHERE e.entity_key IS NULL
                """,
            ),
            "orphan_cached_results": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM cached_results r
                LEFT JOIN query_specs q ON q.query_key=r.query_key
                WHERE q.query_key IS NULL
                """,
            ),
            "orphan_cached_rows": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM cached_result_rows r
                LEFT JOIN query_specs q ON q.query_key=r.query_key
                WHERE q.query_key IS NULL
                """,
            ),
            "orphan_wiki_properties": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM wiki_properties p
                LEFT JOIN wiki_entities e
                  ON e.wiki_entity_key=p.wiki_entity_key
                WHERE e.wiki_entity_key IS NULL
                """,
            ),
            "orphan_wiki_relation_sources": _scalar(
                connection,
                """
                SELECT COUNT(*) FROM wiki_relations r
                LEFT JOIN wiki_entities e
                  ON e.wiki_entity_key=r.src_wiki_entity_key
                WHERE e.wiki_entity_key IS NULL
                """,
            ),
        }
        if schema_version >= 2:
            checks.update(
                {
                    "orphan_blocker_impacts": _scalar(
                        connection,
                        """
                        SELECT COUNT(*) FROM blocker_impacts i
                        LEFT JOIN blocker_roots r
                          ON r.blocker_root_key=i.blocker_root_key
                        WHERE r.blocker_root_key IS NULL
                        """,
                    ),
                    "orphan_blocker_evidence": _scalar(
                        connection,
                        """
                        SELECT COUNT(*) FROM blocker_evidence e
                        LEFT JOIN blocker_roots r
                          ON r.blocker_root_key=e.blocker_root_key
                        WHERE r.blocker_root_key IS NULL
                        """,
                    ),
                    "orphan_work_queue": _scalar(
                        connection,
                        """
                        SELECT COUNT(*) FROM work_queue q
                        LEFT JOIN blocker_roots r
                          ON r.blocker_root_key=q.blocker_root_key
                        WHERE r.blocker_root_key IS NULL
                        """,
                    ),
                }
            )
        failed_checks = {key: value for key, value in checks.items() if value}
        if quick != "ok" or integrity != "ok" or failed_checks:
            raise RuntimeError(
                f"Validation failed: quick={quick} integrity={integrity} "
                f"orphans={failed_checks}"
            )

        lineage = table_count(connection, "stage_lineage")
        if consolidated is True:
            lineage_stages = {
                int(row[0])
                for row in connection.execute(
                    "SELECT stage_id FROM stage_lineage ORDER BY stage_id"
                )
            }
            expected_stages = {0, 10, 20, 30, 40, 50, 60, 70, 90}
            if lineage_stages != expected_stages:
                raise RuntimeError(
                    "Unexpected input stages: "
                    f"{sorted(lineage_stages)}; expected "
                    f"{sorted(expected_stages)}"
                )

        source_preservation_events = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM validation_events
            WHERE scope_kind='source_table'
              AND check_name='row_count_preserved'
              AND status='confirmed'
            """,
        )
        item_entities = _scalar(
            connection,
            "SELECT COUNT(*) FROM entities WHERE kind='item' AND state='confirmed'",
        )
        return {
            "database": path.resolve().as_posix(),
            "schema_version": schema_version,
            "quick_check": quick,
            "integrity_check": integrity,
            "tables": len(present_tables),
            "artifacts": table_count(connection, "artifacts"),
            "query_specs": table_count(connection, "query_specs"),
            "cached_results": table_count(connection, "cached_results"),
            "cached_result_rows": table_count(connection, "cached_result_rows"),
            "entities": table_count(connection, "entities"),
            "confirmed_items": item_entities,
            "entity_properties": table_count(connection, "entity_properties"),
            "relations": table_count(connection, "relations"),
            "coverage": table_count(connection, "coverage"),
            "gaps": table_count(connection, "gaps"),
            "opaque_regions": table_count(connection, "opaque_regions"),
            "blocker_roots": (
                table_count(connection, "blocker_roots")
                if schema_version >= 2
                else 0
            ),
            "work_queue": (
                table_count(connection, "work_queue")
                if schema_version >= 2
                else 0
            ),
            "stage_lineage": lineage,
            "source_tables_preserved": source_preservation_events,
            **checks,
        }
    finally:
        connection.close()


def explain_entity(path: Path, kind: str, native_id: str) -> dict[str, Any]:
    connection = open_read_only(path)
    try:
        key = f"{kind.strip().lower()}:{native_id.strip()}"
        entity = connection.execute(
            "SELECT * FROM entities WHERE entity_key=?",
            (key,),
        ).fetchone()
        if entity is None:
            raise KeyError(f"Entity not found: {key}")
        properties = [
            dict(row)
            for row in connection.execute(
                """
                SELECT namespace,property_name,ordinal,value_type,value_text,
                       value_integer,value_real,value_boolean,value_json,state,
                       authority,locator,consumer,evidence_json
                FROM entity_properties
                WHERE entity_key=?
                ORDER BY namespace,property_name,ordinal,property_key
                """,
                (key,),
            )
        ]
        outgoing = [
            dict(row)
            for row in connection.execute(
                """
                SELECT relation,dst_entity_key,state,required,authority,locator,
                       loader_or_consumer,provenance,evidence_json
                FROM relations WHERE src_entity_key=?
                ORDER BY relation,dst_entity_key,relation_key
                """,
                (key,),
            )
        ]
        incoming = [
            dict(row)
            for row in connection.execute(
                """
                SELECT src_entity_key,relation,state,required,authority,locator,
                       loader_or_consumer,provenance,evidence_json
                FROM relations WHERE dst_entity_key=?
                ORDER BY relation,src_entity_key,relation_key
                """,
                (key,),
            )
        ]
        coverage = [
            dict(row)
            for row in connection.execute(
                """
                SELECT dimension,state,capability,authority,provenance,evidence_json
                FROM coverage WHERE scope_key=?
                ORDER BY authority,dimension,coverage_key
                """,
                (key,),
            )
        ]
        gaps = [
            dict(row)
            for row in connection.execute(
                """
                SELECT dimension,state,severity,blocker_code,reason,
                       required_evidence,provenance
                FROM gaps WHERE entity_key=?
                ORDER BY severity DESC,dimension,gap_key
                """,
                (key,),
            )
        ]
        localizations = [
            dict(row)
            for row in connection.execute(
                """
                SELECT localization_key,locale,text_value,state,
                       source_artifact_key,evidence_json
                FROM localizations
                WHERE entity_key=?
                ORDER BY locale,localization_key
                """,
                (key,),
            )
        ]
        reconciliations = [
            {
                "source_table": str(row["source_table"]),
                "source_pk": str(row["source_pk"]),
                "record": json.loads(str(row["record_json"])),
            }
            for row in connection.execute(
                """
                SELECT source_table,source_pk,record_json
                FROM source_records
                WHERE source_table LIKE 'cross_stage_%_reconciliations'
                  AND (
                    record_json LIKE ?
                    OR record_json LIKE ?
                  )
                ORDER BY source_table,source_pk
                """,
                (
                    f'%\"entity_key\":\"{key}\"%',
                    f'%\"src_entity_key\":\"{key}\"%',
                ),
            )
        ]
        wiki_entities = [
            dict(row)
            for row in connection.execute(
                """
                SELECT wiki_entity_key,url,status_code,response_sha256,state,
                       comparison_state,evidence_json
                FROM wiki_entities
                WHERE entity_key=?
                ORDER BY wiki_entity_key
                """,
                (key,),
            )
        ]
        wiki_keys = [row["wiki_entity_key"] for row in wiki_entities]
        wiki_properties: list[dict[str, Any]] = []
        wiki_relations: list[dict[str, Any]] = []
        for wiki_key in wiki_keys:
            wiki_properties.extend(
                dict(row)
                for row in connection.execute(
                    """
                    SELECT wiki_entity_key,property_name,value_json,
                           comparison_state,evidence_json
                    FROM wiki_properties
                    WHERE wiki_entity_key=?
                    ORDER BY property_name,wiki_property_key
                    """,
                    (wiki_key,),
                )
            )
            wiki_relations.extend(
                dict(row)
                for row in connection.execute(
                    """
                    SELECT src_wiki_entity_key,relation,dst_kind,dst_id,
                           comparison_state,evidence_json
                    FROM wiki_relations
                    WHERE src_wiki_entity_key=?
                    ORDER BY relation,dst_kind,dst_id,wiki_relation_key
                    """,
                    (wiki_key,),
                )
            )
        return {
            "entity": dict(entity),
            "properties": properties,
            "localizations": localizations,
            "relations": {
                "outgoing": outgoing,
                "incoming": incoming,
            },
            "wiki": {
                "entities": wiki_entities,
                "properties": wiki_properties,
                "relations": wiki_relations,
            },
            "coverage": coverage,
            "gaps": gaps,
            "reconciliations": reconciliations,
        }
    finally:
        connection.close()
