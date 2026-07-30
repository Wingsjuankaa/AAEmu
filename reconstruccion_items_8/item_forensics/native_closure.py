from __future__ import annotations

import csv
import io
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .config import ForensicsConfig
from .util import (
    canonical_json,
    open_sqlite_read_only,
    sha256_file,
    write_text_atomic,
)


def _classify(
    family: str,
    dependencies: list[dict[str, Any]],
    lifecycle_state: str | None = None,
    operational_state: str | None = None,
) -> tuple[str, list[str]]:
    confirmed = {
        (str(edge["relation"]), str(edge["dst_kind"]))
        for edge in dependencies
        if edge["state"] == "confirmed"
    }
    roles: list[str] = []
    if ("used_as_craft_material", "craft") in confirmed:
        roles.append("craft_material")
    if ("produced_by_craft", "craft") in confirmed:
        roles.append("craft_product")
    if ("conversion_reagent_in_pack", "item_conv_rpack") in confirmed:
        roles.append("conversion_reagent")
    if ("produced_by_conversion_pack", "item_conv_ppack") in confirmed:
        roles.append("conversion_product")
    if any(kind == "tag" for _, kind in confirmed):
        roles.append("item_tag")
    if any(kind == "skill" for _, kind in confirmed):
        roles.append("skill_consumer")
    if any(
        edge["relation"] == "used_as_skill_reagent"
        and edge["dst_kind"] == "skill"
        and edge["state"] in {"confirmed", "referenced"}
        for edge in dependencies
    ):
        roles.append("skill_reagent")
    if any(kind == "buff" for _, kind in confirmed):
        roles.append("buff_consumer")
    behavioral_roles = [
        role for role in roles
        if role != "item_tag"
    ]
    if lifecycle_state == "tombstone":
        if operational_state and operational_state.startswith("active_"):
            return (
                "native_descriptor_tombstone_alternate_role_confirmed",
                sorted(set(roles)),
            )
        if operational_state == "inactive_craft_only":
            return "native_descriptor_tombstone_inactive", sorted(set(roles))
        if operational_state in {
            "buff_metadata_only",
            "metadata_only",
            "native_synthesis_material_catalog",
        }:
            return (
                "native_descriptor_tombstone_metadata_only",
                sorted(set(roles)),
            )
        return "native_descriptor_tombstone_consumer_unresolved", sorted(set(roles))
    if behavioral_roles:
        return "native_relation_confirmed_descriptor_unresolved", sorted(set(roles))
    if "item_tag" in roles:
        return "native_metadata_confirmed_consumer_unresolved", sorted(set(roles))
    if any(edge["state"] == "missing" for edge in dependencies):
        return "native_dependency_missing", roles
    if family in {"armor", "recipe", "slave_equipment"}:
        return "consumer_unresolved", roles
    return "descriptor_unresolved", roles


def _rows(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    unresolved = connection.execute(
        """
        SELECT
            i.item_id,i.impl_id,i.name,i.use_skill_id,i.buff_id,i.craft_id,
            d.family,d.state AS descriptor_state,d.table_name,
            d.provenance AS descriptor_provenance,
            dl.lifecycle_state,dl.operational_state,
            dl.provenance AS lifecycle_provenance
        FROM items i
        JOIN descriptors d ON d.item_id=i.item_id
        LEFT JOIN descriptor_lifecycle dl
          ON dl.item_id=d.item_id AND dl.table_name=d.table_name
        WHERE i.item_id>0 AND d.state IN ('missing','unknown','blocked')
        ORDER BY i.item_id,d.family,d.table_name
        """
    )
    for row in unresolved:
        item_id = int(row["item_id"])
        dependencies = [
            {
                "relation": str(edge["relation"]),
                "dst_kind": str(edge["dst_kind"]),
                "dst_id": str(edge["dst_id"]),
                "required": bool(edge["required"]),
                "state": str(edge["state"]),
                "provenance": str(edge["provenance"]),
            }
            for edge in connection.execute(
                """
                SELECT relation,dst_kind,dst_id,required,state,provenance
                FROM dependency_edges
                WHERE src_kind='item' AND src_id=?
                ORDER BY relation,dst_kind,dst_id
                """,
                (str(item_id),),
            )
        ]
        closure_state, roles = _classify(
            str(row["family"]),
            dependencies,
            row["lifecycle_state"],
            row["operational_state"],
        )
        result.append(
            {
                "item_id": item_id,
                "impl_id": int(row["impl_id"]),
                "name": row["name"],
                "family": str(row["family"]),
                "descriptor_state": str(row["descriptor_state"]),
                "descriptor_table": row["table_name"],
                "descriptor_provenance": str(row["descriptor_provenance"]),
                "lifecycle_state": row["lifecycle_state"],
                "operational_state": row["operational_state"],
                "lifecycle_provenance": row["lifecycle_provenance"],
                "closure_state": closure_state,
                "consumer_roles": roles,
                "dependencies": dependencies,
            }
        )
    return result


def _csv(rows: list[dict[str, Any]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        (
            "item_id",
            "impl_id",
            "name",
            "family",
            "descriptor_state",
            "lifecycle_state",
            "operational_state",
            "closure_state",
            "consumer_roles",
            "dependency_states",
        )
    )
    for row in rows:
        dependency_states = Counter(
            str(edge["state"]) for edge in row["dependencies"]
        )
        writer.writerow(
            (
                row["item_id"],
                row["impl_id"],
                row["name"] or "",
                row["family"],
                row["descriptor_state"],
                row["lifecycle_state"] or "",
                row["operational_state"] or "",
                row["closure_state"],
                ",".join(row["consumer_roles"]),
                ",".join(
                    f"{key}:{value}"
                    for key, value in sorted(dependency_states.items())
                ),
            )
        )
    return stream.getvalue()


def generate_native_closure_audit(
    config: ForensicsConfig,
    *,
    database: Path | None = None,
) -> dict[str, Any]:
    source = (database or config.database).resolve()
    connection = open_sqlite_read_only(source)
    try:
        rows = _rows(connection)
        catalogs = [
            {
                key: row[key]
                for key in (
                    "table_name",
                    "entity_kind",
                    "id_column",
                    "state",
                    "row_count",
                    "distinct_ids",
                    "provenance",
                )
            }
            for row in connection.execute(
                """
                SELECT
                    table_name,entity_kind,id_column,state,row_count,
                    distinct_ids,provenance
                FROM native_catalogs
                ORDER BY table_name
                """
            )
        ]
    finally:
        connection.close()
    family_states = Counter(
        f"{row['family']}:{row['descriptor_state']}" for row in rows
    )
    closure_states = Counter(str(row["closure_state"]) for row in rows)
    consumer_roles = Counter(
        role for row in rows for role in row["consumer_roles"]
    )
    lifecycle_states = Counter(
        ":".join(
            (
                str(row["family"]),
                str(row["lifecycle_state"] or "unclassified"),
                str(row["operational_state"] or "unclassified"),
            )
        )
        for row in rows
    )
    document = {
        "authority": "AA8 native evidence only",
        "classification": (
            "A native relation does not prove that its behavior is implemented or "
            "that a missing descriptor is intentional. Behavioral relations are "
            "reported separately from tag-only metadata, which cannot by itself "
            "prove an item consumer."
        ),
        "database": {
            "path": source.as_posix(),
            "sha256": sha256_file(source),
        },
        "summary": {
            "unresolved_descriptors": len(rows),
            "family_states": dict(sorted(family_states.items())),
            "closure_states": dict(sorted(closure_states.items())),
            "consumer_roles": dict(sorted(consumer_roles.items())),
            "lifecycle_states": dict(sorted(lifecycle_states.items())),
        },
        "native_catalogs": catalogs,
        "items": rows,
    }
    write_text_atomic(
        config.native_closure_report,
        canonical_json(document, pretty=True),
    )
    write_text_atomic(config.native_closure_csv, _csv(rows))
    return {
        "json": config.native_closure_report,
        "csv": config.native_closure_csv,
        "json_sha256": sha256_file(config.native_closure_report),
        "csv_sha256": sha256_file(config.native_closure_csv),
        **document["summary"],
    }
