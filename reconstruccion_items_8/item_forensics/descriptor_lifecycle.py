from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .util import canonical_json


def _query_evidence(
    connection: sqlite3.Connection,
    table_name: str,
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            q.query_spec_id,q.sql_text,q.loader_consumer,q.evidence_json,
            cr.status,cr.start_offset,cr.end_offset,cr.row_count,cr.row_digest
        FROM query_specs q
        JOIN cached_results cr USING(query_spec_id)
        WHERE q.table_name=? AND cr.status LIKE 'confirmed%'
        ORDER BY q.query_spec_id
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()
    if row is None:
        return {}
    return {
        "query_spec_id": int(row["query_spec_id"]),
        "sql": str(row["sql_text"] or ""),
        "loader": row["loader_consumer"],
        "result_status": str(row["status"]),
        "start": int(row["start_offset"]),
        "end": int(row["end_offset"]),
        "rows": int(row["row_count"]),
        "row_digest": str(row["row_digest"]),
        "query_evidence": json.loads(str(row["evidence_json"])),
    }


def _item_edges(
    connection: sqlite3.Connection,
    item_id: int,
) -> list[dict[str, Any]]:
    return [
        {
            "relation": str(row["relation"]),
            "dst_kind": str(row["dst_kind"]),
            "dst_id": str(row["dst_id"]),
            "state": str(row["state"]),
            "provenance": str(row["provenance"]),
        }
        for row in connection.execute(
            """
            SELECT relation,dst_kind,dst_id,state,provenance
            FROM dependency_edges
            WHERE src_kind='item' AND src_id=?
            ORDER BY relation,dst_kind,dst_id
            """,
            (str(item_id),),
        )
    ]


def _recipe_operational_state(edges: list[dict[str, Any]]) -> str:
    confirmed = {
        (edge["relation"], edge["dst_kind"])
        for edge in edges
        if edge["state"] == "confirmed"
    }
    if ("conversion_reagent_in_pack", "item_conv_rpack") in confirmed:
        return "active_conversion_reagent"
    if ("used_as_craft_material", "craft") in confirmed:
        return "active_craft_material"
    if any(
        edge["dst_kind"] == "skill" and edge["state"] == "confirmed"
        for edge in edges
    ):
        return "active_skill_consumer"
    if any(
        edge["relation"] == "used_as_craft_material"
        and edge["dst_kind"] == "craft"
        and edge["state"] == "missing"
        for edge in edges
    ):
        return "inactive_craft_only"
    if any(
        edge["dst_kind"] == "tag" and edge["state"] == "confirmed"
        for edge in edges
    ):
        return "metadata_only"
    return "consumer_unresolved"


def _category_row(
    connection: sqlite3.Connection,
    category_id: int,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT rr.row_json
        FROM query_specs q
        JOIN cached_results cr USING(query_spec_id)
        JOIN cached_result_rows rr USING(query_spec_id)
        WHERE q.table_name='item_categories'
          AND cr.status LIKE 'confirmed%'
          AND CAST(json_extract(rr.row_json,'$.id') AS INTEGER)=?
        LIMIT 1
        """,
        (category_id,),
    ).fetchone()
    return json.loads(str(row["row_json"])) if row is not None else None


def _cached_matches(
    connection: sqlite3.Connection,
    table_name: str,
    column: str,
    value: int,
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT rr.row_index,rr.row_json
        FROM query_specs q
        JOIN cached_results cr USING(query_spec_id)
        JOIN cached_result_rows rr USING(query_spec_id)
        WHERE q.table_name=? AND cr.status LIKE 'confirmed%'
          AND CAST(json_extract(rr.row_json,?) AS INTEGER)=?
        ORDER BY rr.row_index
        """,
        (table_name, f"$.{column}", value),
    )
    return [
        {
            "row_index": int(row["row_index"]),
            "row": json.loads(str(row["row_json"])),
        }
        for row in rows
    ]


def _negative_sql_evidence(
    connection: sqlite3.Connection,
    terms: tuple[str, ...],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    rows = connection.execute(
        """
        SELECT role,path,bytes,sha256
        FROM artifacts
        WHERE role IN (
            'all_sql_ghidra_tasks','x2game:bin32','x2game:bin64'
        )
        ORDER BY role
        """
    )
    for row in rows:
        path = Path(str(row["path"]))
        if not path.is_file():
            evidence.append(
                {
                    "role": str(row["role"]),
                    "path": path.as_posix(),
                    "sha256": str(row["sha256"]),
                    "status": "artifact_missing",
                }
            )
            continue
        data = path.read_bytes().lower()
        evidence.append(
            {
                "role": str(row["role"]),
                "path": path.as_posix(),
                "bytes": int(row["bytes"]),
                "sha256": str(row["sha256"]),
                "status": "searched",
                "matches": {
                    term: data.count(term.lower().encode("ascii"))
                    for term in terms
                },
            }
        )
    return evidence


def _insert(
    connection: sqlite3.Connection,
    *,
    item_id: int,
    family: str,
    table_name: str,
    lifecycle_state: str,
    operational_state: str,
    target_kind: str | None,
    target_id: str | None,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO descriptor_lifecycle(
            item_id,family,table_name,lifecycle_state,operational_state,
            target_kind,target_id,provenance,evidence_json
        ) VALUES (?,?,?,?,?,?,?,'game11_native+x2game_confirmed',?)
        """,
        (
            item_id,
            family,
            table_name,
            lifecycle_state,
            operational_state,
            target_kind,
            target_id,
            canonical_json(evidence),
        ),
    )


def rebuild_descriptor_lifecycle(
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    connection.execute("DELETE FROM descriptor_lifecycle")
    connection.execute(
        """
        DELETE FROM validation_events
        WHERE scope_kind='client' AND scope_id='descriptor_lifecycle'
        """
    )
    recipe_query = _query_evidence(connection, "item_recipes")
    armor_query = _query_evidence(connection, "item_armors")
    accessory_query = _query_evidence(connection, "item_accessories")
    dyeable_query = _query_evidence(connection, "dyeable_items")
    slave_equipment_query = _query_evidence(
        connection,
        "item_slave_equipments",
    )
    skill_reagent_query = _query_evidence(connection, "skill_reagents")
    dye_sql_negative = _negative_sql_evidence(
        connection,
        ("item_dyeings", "dyeing_colors"),
    )
    counts: Counter[str] = Counter()

    recipe_rows = list(
        connection.execute(
            """
            SELECT d.item_id,d.state,d.descriptor_json,i.name
            FROM descriptors d
            JOIN items i USING(item_id)
            WHERE d.family='recipe' AND d.table_name='item_recipes'
              AND d.item_id>0
            ORDER BY d.item_id
            """
        )
    )
    for row in recipe_rows:
        item_id = int(row["item_id"])
        descriptor = json.loads(str(row["descriptor_json"]))
        edges = _item_edges(connection, item_id)
        unlock = next(
            (
                edge for edge in edges
                if edge["relation"] == "unlocks_craft"
                and edge["dst_kind"] == "craft"
            ),
            None,
        )
        if str(row["state"]) == "confirmed" and unlock is not None:
            lifecycle = (
                "enabled"
                if unlock["state"] == "confirmed"
                else "disabled"
            )
            operational = "recipe_unlock"
            target_kind = "craft"
            target_id = unlock["dst_id"]
        elif str(row["state"]) == "confirmed":
            lifecycle = "unresolved"
            operational = "recipe_target_unresolved"
            target_kind = None
            target_id = None
        else:
            lifecycle = "tombstone"
            operational = _recipe_operational_state(edges)
            target_kind = None
            target_id = None
        _insert(
            connection,
            item_id=item_id,
            family="recipe",
            table_name="item_recipes",
            lifecycle_state=lifecycle,
            operational_state=operational,
            target_kind=target_kind,
            target_id=target_id,
            evidence={
                "item_name": row["name"],
                "descriptor_state": str(row["state"]),
                "descriptor_row": descriptor,
                "native_query": recipe_query,
                "native_query_is_unfiltered": (
                    " where " not in recipe_query.get("sql", "").lower()
                ),
                "item_edges": edges,
            },
        )
        counts[f"recipe:{lifecycle}:{operational}"] += 1

    armor_rows = list(
        connection.execute(
            """
            SELECT d.item_id,d.state,d.descriptor_json,i.name,i.category_id
            FROM descriptors d
            JOIN items i USING(item_id)
            WHERE d.family='armor' AND d.table_name='item_armors'
              AND d.item_id>0
            ORDER BY d.item_id
            """
        )
    )
    category_cache: dict[int, dict[str, Any] | None] = {}
    for row in armor_rows:
        item_id = int(row["item_id"])
        category_id = int(row["category_id"] or 0)
        if category_id not in category_cache:
            category_cache[category_id] = _category_row(connection, category_id)
        category = category_cache[category_id]
        edges = _item_edges(connection, item_id)
        if str(row["state"]) == "confirmed":
            lifecycle = "present"
            operational = "armor_descriptor"
        else:
            lifecycle = "tombstone"
            operational = (
                "native_synthesis_material_catalog"
                if category is not None
                and str(category.get("name", "")) == "합성재료"
                else "consumer_unresolved"
            )
        _insert(
            connection,
            item_id=item_id,
            family="armor",
            table_name="item_armors",
            lifecycle_state=lifecycle,
            operational_state=operational,
            target_kind=None,
            target_id=None,
            evidence={
                "item_name": row["name"],
                "descriptor_state": str(row["state"]),
                "descriptor_row": json.loads(str(row["descriptor_json"])),
                "native_query": armor_query,
                "native_query_is_unfiltered": (
                    " where " not in armor_query.get("sql", "").lower()
                ),
                "category": category,
                "item_edges": edges,
                "behavioral_consumer_confirmed": False
                if lifecycle == "tombstone"
                else True,
            },
        )
        counts[f"armor:{lifecycle}:{operational}"] += 1

    dye_rows = list(
        connection.execute(
            """
            SELECT
                d.item_id,d.state,d.descriptor_json,i.name,i.use_skill_id,
                i.client_row_json
            FROM descriptors d
            JOIN items i USING(item_id)
            WHERE d.family='dyeing' AND d.item_id>0
            ORDER BY d.item_id
            """
        )
    )
    for row in dye_rows:
        item_id = int(row["item_id"])
        use_skill_id = int(row["use_skill_id"] or 0)
        item_data = json.loads(str(row["client_row_json"]))
        dyeable_matches = _cached_matches(
            connection,
            "dyeable_items",
            "item_id",
            item_id,
        )
        edges = _item_edges(connection, item_id)
        lifecycle = "present"
        operational = "native_base_item_skill_driven"
        _insert(
            connection,
            item_id=item_id,
            family="dyeing",
            table_name="items",
            lifecycle_state=lifecycle,
            operational_state=operational,
            target_kind="skill" if use_skill_id > 0 else None,
            target_id=str(use_skill_id) if use_skill_id > 0 else None,
            evidence={
                "item_name": row["name"],
                "descriptor_state": str(row["state"]),
                "descriptor_row": json.loads(str(row["descriptor_json"])),
                "base_item_fields": {
                    "impl_id": int(item_data.get("impl_id") or 0),
                    "use_skill_id": use_skill_id,
                    "use_skill_as_reagent": int(
                        item_data.get("use_skill_as_reagent") or 0
                    ),
                },
                "native_descriptor_model": (
                    "fieldless_concrete_impl_plus_base_item_use_skill"
                ),
                "dedicated_item_dyeings_query": None,
                "full_sql_and_binary_negative_search": dye_sql_negative,
                "dyeable_items_query": dyeable_query,
                "dyeable_items_matches": dyeable_matches,
                "dyeable_items_semantic_role": (
                    "target equipment default color catalogue"
                ),
                "item_edges": edges,
            },
        )
        counts[f"dyeing:{lifecycle}:{operational}"] += 1

    accessory_rows = list(
        connection.execute(
            """
            SELECT
                d.item_id,d.state,d.descriptor_json,i.name,i.buff_id,
                i.category_id
            FROM descriptors d
            JOIN items i USING(item_id)
            WHERE d.family='accessory' AND d.table_name='item_accessories'
              AND d.item_id>0
            ORDER BY d.item_id
            """
        )
    )
    for row in accessory_rows:
        item_id = int(row["item_id"])
        buff_id = int(row["buff_id"] or 0)
        edges = _item_edges(connection, item_id)
        if str(row["state"]) == "confirmed":
            lifecycle = "present"
            operational = "accessory_descriptor"
            target_kind = None
            target_id = None
        else:
            lifecycle = "tombstone"
            operational = (
                "buff_metadata_only"
                if buff_id > 0
                else "consumer_unresolved"
            )
            target_kind = "buff" if buff_id > 0 else None
            target_id = str(buff_id) if buff_id > 0 else None
        _insert(
            connection,
            item_id=item_id,
            family="accessory",
            table_name="item_accessories",
            lifecycle_state=lifecycle,
            operational_state=operational,
            target_kind=target_kind,
            target_id=target_id,
            evidence={
                "item_name": row["name"],
                "category_id": int(row["category_id"] or 0),
                "buff_id": buff_id,
                "descriptor_state": str(row["state"]),
                "descriptor_row": json.loads(str(row["descriptor_json"])),
                "native_query": accessory_query,
                "native_query_is_unfiltered": (
                    " where " not in accessory_query.get("sql", "").lower()
                ),
                "item_edges": edges,
                "behavioral_consumer_confirmed": (
                    str(row["state"]) == "confirmed"
                ),
            },
        )
        counts[f"accessory:{lifecycle}:{operational}"] += 1

    slave_equipment_rows = list(
        connection.execute(
            """
            SELECT
                d.item_id,d.state,d.descriptor_json,i.name,i.category_id
            FROM descriptors d
            JOIN items i USING(item_id)
            WHERE d.family='slave_equipment'
              AND d.table_name='item_slave_equipments'
              AND d.item_id>0
            ORDER BY d.item_id
            """
        )
    )
    for row in slave_equipment_rows:
        item_id = int(row["item_id"])
        edges = _item_edges(connection, item_id)
        reagent_rows = _cached_matches(
            connection,
            "skill_reagents",
            "item_id",
            item_id,
        )
        if str(row["state"]) == "confirmed":
            lifecycle = "present"
            operational = "slave_equipment_descriptor"
            target_kind = None
            target_id = None
        elif reagent_rows:
            lifecycle = "tombstone"
            operational = "active_skill_reagent_and_craft_product"
            target_kind = "skill"
            target_id = str(reagent_rows[0]["row"]["skill_id"])
        else:
            lifecycle = "tombstone"
            operational = "consumer_unresolved"
            target_kind = None
            target_id = None
        _insert(
            connection,
            item_id=item_id,
            family="slave_equipment",
            table_name="item_slave_equipments",
            lifecycle_state=lifecycle,
            operational_state=operational,
            target_kind=target_kind,
            target_id=target_id,
            evidence={
                "item_name": row["name"],
                "category_id": int(row["category_id"] or 0),
                "descriptor_state": str(row["state"]),
                "descriptor_row": json.loads(str(row["descriptor_json"])),
                "native_query": slave_equipment_query,
                "native_query_is_unfiltered": (
                    " where "
                    not in slave_equipment_query.get("sql", "").lower()
                ),
                "skill_reagent_query": skill_reagent_query,
                "enabled_skill_reagent_rows": reagent_rows,
                "item_edges": edges,
            },
        )
        counts[f"slave_equipment:{lifecycle}:{operational}"] += 1

    lifecycle_rows = (
        len(recipe_rows)
        + len(armor_rows)
        + len(dye_rows)
        + len(accessory_rows)
        + len(slave_equipment_rows)
    )
    dye_negative_complete = (
        len(dye_sql_negative) == 3
        and all(
            entry.get("status") == "searched"
            and all(
                int(value) == 0
                for value in entry.get("matches", {}).values()
            )
            for entry in dye_sql_negative
        )
    )
    connection.execute(
        """
        INSERT INTO validation_events(
            scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES (
            'client','descriptor_lifecycle','native_descriptor_absence',
            ?,?
        )
        """,
        (
            "ok"
            if recipe_query
            and armor_query
            and accessory_query
            and dyeable_query
            and slave_equipment_query
            and skill_reagent_query
            and dye_negative_complete
            and " where " not in recipe_query["sql"].lower()
            and " where " not in armor_query["sql"].lower()
            and " where " not in accessory_query["sql"].lower()
            and " where " not in slave_equipment_query["sql"].lower()
            else "blocked",
            canonical_json(
                {
                    "classified_rows": lifecycle_rows,
                    "counts": dict(sorted(counts.items())),
                    "recipe_query": recipe_query,
                    "armor_query": armor_query,
                    "accessory_query": accessory_query,
                    "dyeable_items_query": dyeable_query,
                    "slave_equipment_query": slave_equipment_query,
                    "skill_reagent_query": skill_reagent_query,
                    "dye_descriptor_sql_negative_evidence": (
                        dye_sql_negative
                    ),
                }
            ),
        ),
    )
    return {
        "rows": lifecycle_rows,
        "states": dict(sorted(counts.items())),
    }
