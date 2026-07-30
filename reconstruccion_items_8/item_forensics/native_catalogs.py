from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from typing import Any

from .util import canonical_json, sha256_bytes


CATALOG_SPECS: dict[str, tuple[str, str, str]] = {
    "actability_groups": ("actability_group", "id", "confirmed"),
    "buffs": ("buff", "id", "confirmed"),
    "craft_a_categories": ("craft_a_category", "id", "confirmed"),
    "craft_b_categories": ("craft_b_category", "id", "confirmed"),
    "craft_c_categories": ("craft_c_category", "id", "confirmed"),
    "craft_d_categories": ("craft_d_category", "id", "confirmed"),
    "craft_lines": ("craft_line", "id", "confirmed"),
    "craft_materials": ("craft", "craft_id", "referenced"),
    "craft_packs": ("craft_pack", "id", "confirmed"),
    "craft_products": ("craft", "craft_id", "referenced"),
    "crafts": ("craft", "id", "confirmed"),
    "doodad_almighties": ("doodad", "id", "confirmed"),
    "item_categories": ("item_category", "id", "confirmed"),
    "item_conv_epacks": ("item_conv_epack", "id", "confirmed"),
    "item_conv_ppacks": ("item_conv_ppack", "id", "confirmed"),
    "item_conv_rpacks": ("item_conv_rpack", "id", "confirmed"),
    "item_conv_sets": ("item_conv_set", "id", "confirmed"),
    "item_convs": ("item_conv", "id", "confirmed"),
    "item_guide_elems": ("item_guide", "item_guide_id", "referenced"),
    "item_guides": ("item_guide", "id", "confirmed"),
    "item_recipes": ("craft", "craft_id", "referenced"),
    "skill_products": ("skill", "skill_id", "referenced"),
    "skill_reagents": ("skill", "skill_id", "referenced"),
    "tags": ("tag", "id", "confirmed"),
}


def _cached_rows(
    connection: sqlite3.Connection,
    table_name: str,
) -> tuple[sqlite3.Row | None, list[tuple[int, dict[str, Any]]]]:
    result = connection.execute(
        """
        SELECT
            q.query_spec_id,q.table_name,q.columns_json,q.layout_json,
            q.loader_consumer,q.start_offset,q.expected_rows,q.evidence_json,
            cr.status AS result_status,cr.row_count,cr.row_digest,
            cr.start_offset AS result_start,cr.end_offset AS result_end,
            cr.unresolved_references_json
        FROM query_specs q
        JOIN cached_results cr ON cr.query_spec_id=q.query_spec_id
        WHERE q.table_name=?
        ORDER BY
            CASE WHEN cr.status LIKE 'confirmed%' THEN 0 ELSE 1 END,
            q.query_spec_id
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()
    if result is None or not str(result["result_status"]).startswith("confirmed"):
        return result, []
    rows = [
        (int(row["row_index"]), json.loads(str(row["row_json"])))
        for row in connection.execute(
            """
            SELECT row_index,row_json
            FROM cached_result_rows
            WHERE query_spec_id=?
            ORDER BY row_index
            """,
            (int(result["query_spec_id"]),),
        )
    ]
    return result, rows


def _insert_catalog(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    entity_kind: str,
    id_column: str,
    state: str,
    row_count: int,
    distinct_ids: int,
    provenance: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO native_catalogs(
            table_name,entity_kind,id_column,state,row_count,distinct_ids,
            provenance,evidence_json
        ) VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            table_name,
            entity_kind,
            id_column,
            state,
            row_count,
            distinct_ids,
            provenance,
            canonical_json(evidence),
        ),
    )


def _insert_entities(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    entity_kind: str,
    id_column: str,
    entity_state: str,
    rows: list[tuple[int, dict[str, Any]]],
    provenance: str,
    query_evidence: dict[str, Any],
) -> int:
    grouped: dict[int, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    for row_index, row in rows:
        value = row.get(id_column)
        if value in (None, 0, "0", ""):
            continue
        grouped[int(value)].append((row_index, row))
    for entity_id, matches in sorted(grouped.items()):
        canonical_rows = [row for _, row in matches]
        entity_query_evidence = {
            key: query_evidence.get(key)
            for key in (
                "query_spec_id",
                "result_status",
                "row_digest",
                "start",
                "end",
            )
        }
        connection.execute(
            """
            INSERT INTO native_entities(
                entity_kind,entity_id,source_table,state,row_json,provenance,
                evidence_json
            ) VALUES (?,?,?,?,?,?,?)
            """,
            (
                entity_kind,
                entity_id,
                table_name,
                entity_state,
                canonical_json(
                    {
                        "id_column": id_column,
                        "reference_count": len(matches),
                        "first_row_index": matches[0][0],
                        "last_row_index": matches[-1][0],
                    }
                ),
                provenance,
                canonical_json(
                    {
                        **entity_query_evidence,
                        "rows_digest": sha256_bytes(
                            canonical_json(canonical_rows).encode("utf-8")
                        ),
                    }
                ),
            ),
        )
    return len(grouped)


def _entity_exists(
    connection: sqlite3.Connection,
    entity_kind: str,
    entity_id: int,
) -> bool:
    if entity_kind == "item":
        return (
            connection.execute(
                "SELECT 1 FROM items WHERE item_id=? LIMIT 1",
                (entity_id,),
            ).fetchone()
            is not None
        )
    return (
        connection.execute(
            """
            SELECT 1 FROM native_entities
            WHERE entity_kind=? AND entity_id=? AND state='confirmed'
            LIMIT 1
            """,
            (entity_kind, entity_id),
        ).fetchone()
        is not None
    )


def _add_craft_edges(
    connection: sqlite3.Connection,
    table_name: str,
    rows: list[tuple[int, dict[str, Any]]],
) -> Counter[str]:
    relation = {
        "craft_materials": ("material_item_id", "used_as_craft_material"),
        "craft_products": ("product_item_id", "produced_by_craft"),
        "item_recipes": ("unlocked_by_recipe_item", "unlocks_craft"),
    }.get(table_name)
    counts: Counter[str] = Counter()
    if relation is None:
        return counts
    forward_relation, reverse_relation = relation
    for row_index, row in rows:
        craft_id = int(row.get("craft_id") or 0)
        item_id = int(row.get("item_id") or 0)
        if craft_id <= 0 or item_id <= 0:
            continue
        craft_state = (
            "confirmed" if _entity_exists(connection, "craft", craft_id) else "missing"
        )
        item_state = (
            "confirmed" if _entity_exists(connection, "item", item_id) else "missing"
        )
        evidence = canonical_json(
            {
                "query_table": table_name,
                "row_index": row_index,
                "row": row,
            }
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO dependency_edges(
                src_kind,src_id,relation,dst_kind,dst_id,required,state,
                provenance,evidence_json
            ) VALUES ('craft',?,?, 'item',?,1,?,'game11_native',?)
            """,
            (
                str(craft_id),
                forward_relation,
                str(item_id),
                item_state,
                evidence,
            ),
        )
        counts[f"craft_to_item:{item_state}"] += 1
        if reverse_relation is not None:
            connection.execute(
                """
                INSERT OR IGNORE INTO dependency_edges(
                    src_kind,src_id,relation,dst_kind,dst_id,required,state,
                    provenance,evidence_json
                ) VALUES ('item',?,?, 'craft',?,0,?,'game11_native',?)
                """,
                (
                    str(item_id),
                    reverse_relation,
                    str(craft_id),
                    craft_state,
                    evidence,
                ),
            )
            counts[f"item_to_craft:{craft_state}"] += 1
    return counts


def _add_typed_edge(
    connection: sqlite3.Connection,
    *,
    src_kind: str,
    src_id: int,
    relation: str,
    dst_kind: str,
    dst_id: int,
    state: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO dependency_edges(
            src_kind,src_id,relation,dst_kind,dst_id,required,state,
            provenance,evidence_json
        ) VALUES (?,?,?,?,?,0,?,'game11_native',?)
        """,
        (
            src_kind,
            str(src_id),
            relation,
            dst_kind,
            str(dst_id),
            state,
            canonical_json(evidence),
        ),
    )


def _add_craft_topology_edges(
    connection: sqlite3.Connection,
    cached: dict[str, list[tuple[int, dict[str, Any]]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row_index, row in cached.get("craft_line_components", []):
        craft_id = int(row.get("craft_id") or 0)
        line_id = int(row.get("craft_line_id") or 0)
        if craft_id <= 0 or line_id <= 0:
            continue
        craft_state = (
            "confirmed"
            if _entity_exists(connection, "craft", craft_id)
            else "missing"
        )
        line_state = (
            "confirmed"
            if _entity_exists(connection, "craft_line", line_id)
            else "missing"
        )
        evidence = {
            "query_table": "craft_line_components",
            "row_index": row_index,
            "row": row,
        }
        _add_typed_edge(
            connection,
            src_kind="craft",
            src_id=craft_id,
            relation="member_of_craft_line",
            dst_kind="craft_line",
            dst_id=line_id,
            state=line_state,
            evidence=evidence,
        )
        _add_typed_edge(
            connection,
            src_kind="craft_line",
            src_id=line_id,
            relation="contains_craft",
            dst_kind="craft",
            dst_id=craft_id,
            state=craft_state,
            evidence=evidence,
        )
        counts[f"craft_to_line:{line_state}"] += 1
        counts[f"line_to_craft:{craft_state}"] += 1

    for row_index, row in cached.get("craft_pack_crafts", []):
        craft_id = int(row.get("craft_id") or 0)
        pack_id = int(row.get("craft_pack_id") or 0)
        if craft_id <= 0 or pack_id <= 0:
            continue
        craft_state = (
            "confirmed"
            if _entity_exists(connection, "craft", craft_id)
            else "missing"
        )
        pack_state = (
            "confirmed"
            if _entity_exists(connection, "craft_pack", pack_id)
            else "missing"
        )
        evidence = {
            "query_table": "craft_pack_crafts",
            "row_index": row_index,
            "row": row,
        }
        _add_typed_edge(
            connection,
            src_kind="craft",
            src_id=craft_id,
            relation="member_of_craft_pack",
            dst_kind="craft_pack",
            dst_id=pack_id,
            state=pack_state,
            evidence=evidence,
        )
        _add_typed_edge(
            connection,
            src_kind="craft_pack",
            src_id=pack_id,
            relation="contains_craft",
            dst_kind="craft",
            dst_id=craft_id,
            state=craft_state,
            evidence=evidence,
        )
        counts[f"craft_to_pack:{pack_state}"] += 1
        counts[f"pack_to_craft:{craft_state}"] += 1
    return counts


def _add_item_conversion_edges(
    connection: sqlite3.Connection,
    cached: dict[str, list[tuple[int, dict[str, Any]]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()

    def add_pair(
        *,
        table: str,
        row_index: int,
        row: dict[str, Any],
        src_kind: str,
        src_id: int,
        relation: str,
        dst_kind: str,
        dst_id: int,
        reverse_relation: str,
    ) -> None:
        if src_id <= 0 or dst_id <= 0:
            return
        src_state = (
            "confirmed"
            if _entity_exists(connection, src_kind, src_id)
            else "missing"
        )
        dst_state = (
            "confirmed"
            if _entity_exists(connection, dst_kind, dst_id)
            else "missing"
        )
        evidence = {
            "query_table": table,
            "row_index": row_index,
            "row": row,
        }
        _add_typed_edge(
            connection,
            src_kind=src_kind,
            src_id=src_id,
            relation=relation,
            dst_kind=dst_kind,
            dst_id=dst_id,
            state=dst_state,
            evidence=evidence,
        )
        _add_typed_edge(
            connection,
            src_kind=dst_kind,
            src_id=dst_id,
            relation=reverse_relation,
            dst_kind=src_kind,
            dst_id=src_id,
            state=src_state,
            evidence=evidence,
        )
        counts[f"{src_kind}_to_{dst_kind}:{dst_state}"] += 1
        counts[f"{dst_kind}_to_{src_kind}:{src_state}"] += 1

    for row_index, row in cached.get("item_conv_reagents", []):
        add_pair(
            table="item_conv_reagents",
            row_index=row_index,
            row=row,
            src_kind="item",
            src_id=int(row.get("item_id") or 0),
            relation="conversion_reagent_in_pack",
            dst_kind="item_conv_rpack",
            dst_id=int(row.get("item_conv_rpack_id") or 0),
            reverse_relation="contains_conversion_reagent",
        )

    for row_index, row in cached.get("item_conv_rpack_members", []):
        add_pair(
            table="item_conv_rpack_members",
            row_index=row_index,
            row=row,
            src_kind="item_conv_rpack",
            src_id=int(row.get("item_conv_rpack_id") or 0),
            relation="enables_conversion",
            dst_kind="item_conv",
            dst_id=int(row.get("item_conv_id") or 0),
            reverse_relation="accepts_reagent_pack",
        )

    for row_index, row in cached.get("item_conv_ppack_members", []):
        add_pair(
            table="item_conv_ppack_members",
            row_index=row_index,
            row=row,
            src_kind="item_conv",
            src_id=int(row.get("item_conv_id") or 0),
            relation="outputs_product_pack",
            dst_kind="item_conv_ppack",
            dst_id=int(row.get("item_conv_ppack_id") or 0),
            reverse_relation="output_for_conversion",
        )

    for row_index, row in cached.get("item_conv_products", []):
        add_pair(
            table="item_conv_products",
            row_index=row_index,
            row=row,
            src_kind="item_conv_ppack",
            src_id=int(row.get("item_conv_ppack_id") or 0),
            relation="contains_conversion_product",
            dst_kind="item",
            dst_id=int(row.get("item_id") or 0),
            reverse_relation="produced_by_conversion_pack",
        )

    for row_index, row in cached.get("item_convs", []):
        add_pair(
            table="item_convs",
            row_index=row_index,
            row=row,
            src_kind="item_conv",
            src_id=int(row.get("id") or 0),
            relation="member_of_conversion_set",
            dst_kind="item_conv_set",
            dst_id=int(row.get("item_conv_set_id") or 0),
            reverse_relation="contains_conversion",
        )

    for row_index, row in cached.get("item_conv_reagent_filters", []):
        add_pair(
            table="item_conv_reagent_filters",
            row_index=row_index,
            row=row,
            src_kind="item_conv_rpack",
            src_id=int(row.get("item_conv_rpack_id") or 0),
            relation="uses_exception_pack",
            dst_kind="item_conv_epack",
            dst_id=int(row.get("item_conv_epack_id") or 0),
            reverse_relation="filters_reagent_pack",
        )

    for row_index, row in cached.get("item_conv_exception_filters", []):
        add_pair(
            table="item_conv_exception_filters",
            row_index=row_index,
            row=row,
            src_kind="item_conv_epack",
            src_id=int(row.get("item_conv_epack_id") or 0),
            relation="excludes_item_category",
            dst_kind="item_category",
            dst_id=int(row.get("item_category_id") or 0),
            reverse_relation="excluded_by_conversion_pack",
        )

    return counts


def _add_item_tag_edges(
    connection: sqlite3.Connection,
    rows: list[tuple[int, dict[str, Any]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row_index, row in rows:
        item_id = int(row.get("item_id") or 0)
        tag_id = int(row.get("tag_id") or 0)
        if item_id <= 0 or tag_id <= 0:
            continue
        item_state = (
            "confirmed" if _entity_exists(connection, "item", item_id) else "missing"
        )
        tag_state = (
            "confirmed" if _entity_exists(connection, "tag", tag_id) else "missing"
        )
        evidence = {
            "query_table": "tagged_items",
            "row_index": row_index,
            "row": row,
        }
        _add_typed_edge(
            connection,
            src_kind="item",
            src_id=item_id,
            relation="tagged_with",
            dst_kind="tag",
            dst_id=tag_id,
            state=tag_state,
            evidence=evidence,
        )
        _add_typed_edge(
            connection,
            src_kind="tag",
            src_id=tag_id,
            relation="contains_tagged_item",
            dst_kind="item",
            dst_id=item_id,
            state=item_state,
            evidence=evidence,
        )
        counts[f"item_to_tag:{tag_state}"] += 1
        counts[f"tag_to_item:{item_state}"] += 1
    return counts


def _add_item_guide_edges(
    connection: sqlite3.Connection,
    rows: list[tuple[int, dict[str, Any]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row_index, row in rows:
        item_id = int(row.get("item_id") or 0)
        guide_id = int(row.get("item_guide_id") or 0)
        if item_id <= 0 or guide_id <= 0:
            continue
        item_state = (
            "confirmed" if _entity_exists(connection, "item", item_id) else "missing"
        )
        guide_state = (
            "confirmed"
            if _entity_exists(connection, "item_guide", guide_id)
            else "missing"
        )
        evidence = {
            "query_table": "item_guide_elems",
            "row_index": row_index,
            "row": row,
        }
        _add_typed_edge(
            connection,
            src_kind="item",
            src_id=item_id,
            relation="listed_in_item_guide",
            dst_kind="item_guide",
            dst_id=guide_id,
            state=guide_state,
            evidence=evidence,
        )
        _add_typed_edge(
            connection,
            src_kind="item_guide",
            src_id=guide_id,
            relation="lists_item",
            dst_kind="item",
            dst_id=item_id,
            state=item_state,
            evidence=evidence,
        )
        counts[f"item_to_guide:{guide_state}"] += 1
        counts[f"guide_to_item:{item_state}"] += 1
    return counts


def _add_skill_item_edges(
    connection: sqlite3.Connection,
    table_name: str,
    rows: list[tuple[int, dict[str, Any]]],
) -> Counter[str]:
    counts: Counter[str] = Counter()
    relations = {
        "skill_reagents": ("consumes_item_reagent", "used_as_skill_reagent"),
        "skill_products": ("produces_item", "produced_by_skill"),
    }
    skill_relation, item_relation = relations[table_name]
    for row_index, row in rows:
        skill_id = int(row.get("skill_id") or 0)
        item_id = int(row.get("item_id") or 0)
        if skill_id <= 0 or item_id <= 0:
            continue
        item_state = (
            "confirmed"
            if _entity_exists(connection, "item", item_id)
            else "missing"
        )
        # These filtered native rows prove the relation and skill reference,
        # but the item forensic database does not yet import the full skills
        # result. Keep that distinction explicit on the skill endpoint.
        skill_state = "referenced"
        evidence = {
            "query_table": table_name,
            "query_filter": "enable = 't'",
            "row_index": row_index,
            "row": row,
        }
        _add_typed_edge(
            connection,
            src_kind="skill",
            src_id=skill_id,
            relation=skill_relation,
            dst_kind="item",
            dst_id=item_id,
            state=item_state,
            evidence=evidence,
        )
        _add_typed_edge(
            connection,
            src_kind="item",
            src_id=item_id,
            relation=item_relation,
            dst_kind="skill",
            dst_id=skill_id,
            state=skill_state,
            evidence=evidence,
        )
        counts[f"skill_to_item:{item_state}"] += 1
        counts[f"item_to_skill:{skill_state}"] += 1
    return counts


def rebuild_native_catalogs(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.execute("DELETE FROM native_entities")
    connection.execute("DELETE FROM native_catalogs")
    connection.execute(
        """
        DELETE FROM validation_events
        WHERE scope_kind='client' AND scope_id='native_dependency_catalogs'
        """
    )
    cached: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    catalog_states: Counter[str] = Counter()
    for table_name, (entity_kind, id_column, entity_state) in sorted(
        CATALOG_SPECS.items()
    ):
        result, rows = _cached_rows(connection, table_name)
        cached[table_name] = rows
        if result is None:
            continue
        result_status = str(result["result_status"])
        confirmed = result_status.startswith("confirmed")
        query_evidence = {
            "query_spec_id": int(result["query_spec_id"]),
            "loader_consumer": result["loader_consumer"],
            "query_evidence": json.loads(str(result["evidence_json"])),
            "result_status": result_status,
            "row_digest": result["row_digest"],
            "start": result["result_start"],
            "end": result["result_end"],
            "unresolved_references": len(
                json.loads(str(result["unresolved_references_json"]))
            ),
        }
        distinct_ids = 0
        if confirmed:
            distinct_ids = _insert_entities(
                connection,
                table_name=table_name,
                entity_kind=entity_kind,
                id_column=id_column,
                entity_state=entity_state,
                rows=rows,
                provenance="game11_native",
                query_evidence=query_evidence,
            )
            state = (
                "confirmed_id_scope_with_opaque_text"
                if result_status == "confirmed_id_scope_with_opaque_text"
                else "confirmed"
            )
        else:
            state = result_status
        _insert_catalog(
            connection,
            table_name=table_name,
            entity_kind=entity_kind,
            id_column=id_column,
            state=state,
            row_count=len(rows),
            distinct_ids=distinct_ids,
            provenance=(
                "game11_native+x2game_confirmed"
                if confirmed
                else "x2game_confirmed"
            ),
            evidence=query_evidence,
        )
        catalog_states[state] += 1

    for table_name in (
        "craft_line_components",
        "craft_pack_crafts",
        "item_conv_exception_filters",
        "item_conv_ppack_members",
        "item_conv_products",
        "item_conv_reagent_filters",
        "item_conv_reagents",
        "item_conv_rpack_members",
        "tagged_items",
    ):
        _, cached[table_name] = _cached_rows(connection, table_name)

    item_craft_rows: list[tuple[int, dict[str, Any]]] = []
    for row_index, row in enumerate(
        connection.execute(
            """
            SELECT item_id,craft_id FROM items
            WHERE craft_id>0 ORDER BY item_id
            """
        )
    ):
        item_craft_rows.append(
            (
                row_index,
                {"item_id": int(row["item_id"]), "craft_id": int(row["craft_id"])},
            )
        )
    item_craft_distinct = _insert_entities(
        connection,
        table_name="items.craft_id",
        entity_kind="craft",
        id_column="craft_id",
        entity_state="referenced",
        rows=item_craft_rows,
        provenance="client_compact_8",
        query_evidence={"source": "client_compact_8.items.craft_id"},
    )
    _insert_catalog(
        connection,
        table_name="items.craft_id",
        entity_kind="craft",
        id_column="craft_id",
        state="confirmed_reference",
        row_count=len(item_craft_rows),
        distinct_ids=item_craft_distinct,
        provenance="client_compact_8",
        evidence={"source": "client_compact_8.items.craft_id"},
    )
    catalog_states["confirmed_reference"] += 1
    for row_index, row in item_craft_rows:
        craft_id = int(row["craft_id"])
        craft_state = (
            "confirmed"
            if _entity_exists(connection, "craft", craft_id)
            else "missing"
        )
        _add_typed_edge(
            connection,
            src_kind="item",
            src_id=int(row["item_id"]),
            relation="direct_craft_reference",
            dst_kind="craft",
            dst_id=craft_id,
            state=craft_state,
            evidence={
                "query_table": "items",
                "column": "craft_id",
                "row_index": row_index,
                "row": row,
            },
        )

    edge_counts: Counter[str] = Counter()
    for table_name in ("craft_materials", "craft_products", "item_recipes"):
        edge_counts.update(_add_craft_edges(connection, table_name, cached[table_name]))
    edge_counts.update(_add_craft_topology_edges(connection, cached))
    edge_counts.update(_add_item_conversion_edges(connection, cached))
    edge_counts.update(_add_item_tag_edges(connection, cached["tagged_items"]))
    edge_counts.update(
        _add_item_guide_edges(connection, cached["item_guide_elems"])
    )
    for table_name in ("skill_reagents", "skill_products"):
        edge_counts.update(
            _add_skill_item_edges(connection, table_name, cached[table_name])
        )

    orphan_edges = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM dependency_edges
            WHERE src_kind='craft' AND dst_kind='item' AND state='missing'
            """
        ).fetchone()[0]
    )
    unavailable_craft_edges = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM dependency_edges
            WHERE src_kind='item' AND dst_kind='craft'
              AND state='missing' AND provenance='game11_native'
            """
        ).fetchone()[0]
    )
    entity_counts = {
        f"{row[0]}:{row[1]}": int(row[2])
        for row in connection.execute(
            """
            SELECT entity_kind,state,COUNT(DISTINCT entity_id)
            FROM native_entities
            GROUP BY entity_kind,state
            ORDER BY entity_kind,state
            """
        )
    }
    connection.execute(
        """
        INSERT INTO validation_events(
            scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES (
            'client','native_dependency_catalogs','craft_item_relations',
            ?,?
        )
        """,
        (
            "ok" if orphan_edges == 0 else "blocked",
            canonical_json(
                {
                    "edge_counts": dict(sorted(edge_counts.items())),
                    "orphan_craft_item_edges": orphan_edges,
                    "unavailable_craft_edges": unavailable_craft_edges,
                }
            ),
        ),
    )
    return {
        "catalog_states": dict(sorted(catalog_states.items())),
        "edge_counts": dict(sorted(edge_counts.items())),
        "entity_counts": entity_counts,
        "orphan_craft_item_edges": orphan_edges,
        "unavailable_craft_edges": unavailable_craft_edges,
    }
