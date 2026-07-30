from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

from . import TOOL_NAME, TOOL_VERSION
from .cross_stage import (
    CrossStageResolver,
    EntityResolution,
    relation_can_close_from_destination,
    relation_is_asset_corroboration,
)
from .schema import open_read_only
from .util import canonical_json, stable_key

if TYPE_CHECKING:
    from .build import BuildContext


STAGE = 90
PROVENANCE = "aa8-client-forensics-stage90"
UNRESOLVED_STATES = {"blocked", "missing", "opaque", "unknown"}
STATE_ORDER = {
    "confirmed": 0,
    "corroborated": 1,
    "unknown": 2,
    "opaque": 3,
    "missing": 4,
    "blocked": 5,
}


def _selected_sql_columns(sql_text: str | None) -> tuple[str, ...]:
    if not sql_text:
        return ()
    match = re.search(
        r"^\s*SELECT\s+(.*?)\s+FROM\s",
        sql_text,
        re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return ()
    return tuple(
        column.strip() for column in match.group(1).split(",")
    )
DOWNSTREAM_CODES = {
    "backend_missing",
    "backend_unknown",
    "dependency_closure_missing",
    "dependency_closure_unknown",
    "persistence_unknown",
    "protocol_unknown",
    "validation_unknown",
}
OWNER_KIND_STAGE = {
    "item": 20,
    "item_descriptor": 20,
    "craft": 20,
    "craft_pack": 20,
    "loot_pack": 20,
    "loot_pack": 20,
    "npc": 30,
    "npc_ai": 30,
    "npc_group": 30,
    "npc_spawner": 30,
    "doodad": 30,
    "model": 30,
    "sphere": 30,
    "quest": 40,
    "quest_component": 40,
    "quest_detail": 40,
    "quest_name_kind": 40,
    "quest_context_text_kind": 40,
    "skill": 50,
    "buff": 50,
    "effect": 50,
    "effect_detail": 50,
    "plot": 50,
    "plot_event": 50,
    "icon": 60,
    "asset_file": 60,
    "asset_reference": 60,
    "localized_record": 60,
}
CATEGORY_BASE = {
    "cached_result_decode": 92,
    "native_result_absent": 90,
    "query_layout": 86,
    "native_descriptor": 84,
    "native_closure": 78,
    "relation_closure": 74,
    "native_consumer": 72,
    "native_entity_state": 62,
    "native_lifecycle": 58,
    "asset_resolution": 52,
    "query_state_audit": 38,
    "negative_evidence": 36,
    "wiki_corroboration": 20,
    "downstream_server": -900,
}
EFFORT_BY_CATEGORY = {
    "cached_result_decode": 4,
    "native_result_absent": 5,
    "query_layout": 4,
    "native_descriptor": 4,
    "native_closure": 3,
    "relation_closure": 3,
    "native_consumer": 4,
    "native_entity_state": 3,
    "native_lifecycle": 3,
    "asset_resolution": 4,
    "query_state_audit": 2,
    "negative_evidence": 4,
    "wiki_corroboration": 2,
    "downstream_server": 5,
}


def _entity_kind(entity_key: str) -> str:
    return entity_key.split(":", 1)[0] if ":" in entity_key else "unknown"


def _worst_state(values: set[str]) -> str:
    return max(values or {"unknown"}, key=lambda value: STATE_ORDER.get(value, 2))


def classify_gap(
    blocker_code: str,
    *,
    provenance: str,
    entity_kind: str,
) -> tuple[str, str]:
    if blocker_code in DOWNSTREAM_CODES and provenance == "aa8-item-forensics":
        return "downstream_server", "downstream_out_of_scope"
    if blocker_code in {
        "referenced_endpoint_not_in_decoded_stages",
        "referenced_endpoint_not_in_prior_stages",
    }:
        return "native_closure", "actionable"
    if blocker_code in {"descriptor_missing", "referenced_icon_descriptor_absent"}:
        return "native_descriptor", "actionable"
    if "asset" in blocker_code or entity_kind in {"asset_file", "icon"}:
        return "asset_resolution", "actionable"
    if blocker_code in {
        "native_result_absent",
        "appearance_color_results_absent",
        "unresolved_global_string_references",
    }:
        return "native_result_absent", "actionable"
    return "native_closure", "actionable"


def classify_opaque(
    blocker_code: str,
    *,
    surface: str,
) -> tuple[str, str]:
    if blocker_code == "server_only_items" or surface.startswith("runtime."):
        return "downstream_server", "downstream_out_of_scope"
    if blocker_code == "wiki_catalog_absence_not_http_absence":
        return "wiki_corroboration", "corroborative_only"
    if blocker_code == "client_explicitly_unsupported_behavior":
        return "negative_evidence", "audit_required"
    if blocker_code in {
        "native_result_absent",
        "unresolved_string_cache_references",
        "cached_result_boundary_not_yet_mapped",
    }:
        return (
            "native_result_absent"
            if blocker_code == "native_result_absent"
            else "cached_result_decode",
            "actionable",
        )
    if "asset" in blocker_code or "icon" in blocker_code:
        return "asset_resolution", "actionable"
    if "consumer" in blocker_code:
        return "native_consumer", "actionable"
    if "signed_or_nonpositive" in blocker_code:
        return "native_lifecycle", "audit_required"
    return "negative_evidence", "actionable"


def owner_stage_for_kind(kind: str, default: int = 10) -> int:
    return OWNER_KIND_STAGE.get(kind, default)


def _query_stage(query_key: str) -> int:
    for stage in (30, 40, 50, 60, 70, 90):
        if query_key.startswith(f"stage{stage}:"):
            return stage
    if query_key.startswith("legacy:item-forensics:"):
        return 20
    return 10


def _category_lane(category: str) -> str:
    if category in {"cached_result_decode", "native_result_absent", "query_layout"}:
        return "P0_native_decode"
    if category in {
        "native_closure",
        "native_descriptor",
        "relation_closure",
    }:
        return "P1_native_closure"
    if category in {"native_consumer", "query_state_audit"}:
        return "P2_native_consumer"
    if category in {
        "native_entity_state",
        "native_lifecycle",
        "asset_resolution",
        "negative_evidence",
    }:
        return "P3_assets_lifecycle"
    if category == "wiki_corroboration":
        return "P4_wiki_corroboration"
    return "deferred_server"


def _recommended_action(
    category: str,
    scope_value: str,
    root_code: str | None = None,
) -> str:
    if root_code == "client_explicitly_unsupported_behavior":
        return (
            "Preserve the closed client-side negative evidence and continue "
            "only with native server/protocol authority; do not repeat the "
            "client search or promote historical enum labels. "
            f"Scope: {scope_value}."
        )
    actions = {
        "cached_result_decode": (
            "Recover the exact cached-result boundary/layout, replay the global "
            "string cache in execution order, and decode the native rows."
        ),
        "native_result_absent": (
            "Prove the execution mode or alternate authoritative database that "
            "emits the native result; retain negative evidence if it remains absent."
        ),
        "query_layout": (
            "Recover loader, columns, boundaries and x86/x64 layout for the query."
        ),
        "native_descriptor": (
            "Locate the concrete native descriptor row and its x2game factory/loader."
        ),
        "native_closure": (
            "Decode the authoritative owner table and close every referenced endpoint."
        ),
        "relation_closure": (
            "Resolve the destination family and reclassify all incoming native edges."
        ),
        "native_consumer": (
            "Confirm the native consumer and the fields/relations it actually reads."
        ),
        "native_entity_state": (
            "Determine whether the entity is present, referenced-only, tombstoned or missing."
        ),
        "native_lifecycle": (
            "Recover the native lifecycle/filter/tombstone rule for this scope."
        ),
        "asset_resolution": (
            "Recover the exact client resolver, alias, atlas or physical asset mapping."
        ),
        "query_state_audit": (
            "Reconcile registry state with the already observed result/loader evidence."
        ),
        "negative_evidence": (
            "Extend the targeted native search and record the searched surfaces and authority."
        ),
        "wiki_corroboration": (
            "Freeze only graph-prioritized detail pages and compare them without promoting authority."
        ),
        "downstream_server": (
            "Defer to the later AAEmu acceptance workflow; this does not block client decoding."
        ),
    }
    return f"{actions[category]} Scope: {scope_value}."


def _acceptance(category: str) -> list[str]:
    common = ["evidence provenance recorded", "deterministic Stage 90 rebuild"]
    values = {
        "cached_result_decode": [
            "exact stream boundaries",
            "zero unresolved string references",
            "row count and digest frozen",
        ],
        "native_result_absent": [
            "execution-mode search documented",
            "native result decoded or negative evidence complete",
        ],
        "query_layout": [
            "columns and primitive layout confirmed",
            "loader/consumer located",
            "x86/x64 compared when both exist",
        ],
        "native_descriptor": [
            "descriptor row or tombstone rule confirmed",
            "factory/loader mapped",
        ],
        "native_closure": ["all target IDs classified", "zero silent orphans"],
        "relation_closure": [
            "destination family decoded",
            "all affected edges reclassified",
        ],
        "native_consumer": ["consumer located", "read fields and semantics recorded"],
        "native_entity_state": ["identity and lifecycle classified"],
        "native_lifecycle": ["filter/tombstone rule confirmed"],
        "asset_resolution": ["exact resolver or documented physical absence"],
        "query_state_audit": ["query state matches observed evidence"],
        "negative_evidence": ["searched surfaces and hashes recorded"],
        "wiki_corroboration": ["HTTP snapshot frozen", "native comparison classified"],
        "downstream_server": ["handled in separate server reconstruction workflow"],
    }
    return values[category] + common


@dataclass
class Impact:
    subject_kind: str
    subject_key: str
    entity_key: str | None
    states: set[str] = field(default_factory=set)
    count: int = 0
    evidence_kinds: set[str] = field(default_factory=set)


@dataclass
class Evidence:
    evidence_kind: str
    source_key: str
    source_stage: int | None
    states: set[str] = field(default_factory=set)
    count: int = 0
    payloads: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Root:
    key: str
    root_code: str
    category: str
    scope_kind: str
    scope_value: str
    owner_stage: int
    disposition: str
    authorities: set[str] = field(default_factory=set)
    states: set[str] = field(default_factory=set)
    required_evidence: set[str] = field(default_factory=set)
    provenance: set[str] = field(default_factory=set)
    impacts: dict[tuple[str, str], Impact] = field(default_factory=dict)
    evidence: dict[tuple[str, str], Evidence] = field(default_factory=dict)
    max_severity: int = 0
    gap_count: int = 0
    opaque_count: int = 0
    coverage_count: int = 0
    query_count: int = 0
    consumer_count: int = 0
    relation_count: int = 0
    incoming_fanout: int = 0
    outgoing_fanout: int = 0
    effort_score: int = 0
    fanout_score: int = 0
    priority_score: int = 0

    def impact(
        self,
        *,
        subject_kind: str,
        subject_key: str,
        entity_key: str | None,
        state: str,
        evidence_kind: str,
        count: int = 1,
    ) -> None:
        key = (subject_kind, subject_key)
        value = self.impacts.setdefault(
            key,
            Impact(subject_kind, subject_key, entity_key),
        )
        value.states.add(state)
        value.evidence_kinds.add(evidence_kind)
        value.count += count

    def add_evidence(
        self,
        *,
        evidence_kind: str,
        source_key: str,
        source_stage: int | None,
        state: str,
        payload: dict[str, Any],
        count: int = 1,
    ) -> None:
        key = (evidence_kind, source_key)
        value = self.evidence.setdefault(
            key,
            Evidence(evidence_kind, source_key, source_stage),
        )
        value.states.add(state)
        value.count += count
        if len(value.payloads) < 8 and payload not in value.payloads:
            value.payloads.append(payload)


class ClosureBuilder:
    def __init__(
        self,
        source: sqlite3.Connection,
        resolver: CrossStageResolver,
    ) -> None:
        self.source = source
        self.resolver = resolver
        self.roots: dict[str, Root] = {}
        self.reconciliation_rows: list[tuple[Any, ...]] = []
        self.reconciliation_counts: Counter[str] = Counter()
        self.reconciliation_by_kind: Counter[str] = Counter()
        self.reconciled_asset_relation_count = 0
        self.relation_root_keys: set[str] = set()
        self.superseded_queries: list[dict[str, Any]] = []

    def reconcile(
        self,
        *,
        source_kind: str,
        source_key: str,
        entity_key: str,
        original_state: str,
        resolution: EntityResolution,
        evidence: dict[str, Any],
    ) -> None:
        kind = _entity_kind(entity_key)
        record = {
            "entity_key": entity_key,
            "original_state": original_state,
            "resolution": resolution.as_dict(),
            "source_key": source_key,
            "source_kind": source_kind,
            **evidence,
        }
        self.reconciliation_rows.append(
            (
                stable_key(
                    "stage90",
                    "cross-stage-reconciliation",
                    source_kind,
                    source_key,
                ),
                f"cross_stage_{source_kind}_reconciliations",
                source_key,
                canonical_json(record),
                "derived_forensic",
                PROVENANCE,
            )
        )
        self.reconciliation_counts[source_kind] += 1
        self.reconciliation_by_kind[f"{source_kind}:{kind}"] += 1
        if (
            source_kind == "relation"
            and relation_is_asset_corroboration(
                authority=str(evidence.get("authority", "")),
                provenance=str(evidence.get("provenance", "")),
            )
        ):
            self.reconciled_asset_relation_count += 1

    def reconciliation_summary(self) -> dict[str, Any]:
        digest = hashlib.sha256()
        for row in sorted(
            self.reconciliation_rows,
            key=lambda value: str(value[0]),
        ):
            digest.update(str(row[0]).encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(row[3]).encode("utf-8"))
            digest.update(b"\n")
        return {
            "candidate_entities": self.resolver.candidate_count,
            "entities_with_strong_observation": (
                self.resolver.resolved_candidate_count
            ),
            "records": len(self.reconciliation_rows),
            "records_sha256": digest.hexdigest().upper(),
            "by_source_kind": dict(sorted(self.reconciliation_counts.items())),
            "by_source_kind_and_entity_kind": dict(
                sorted(self.reconciliation_by_kind.items())
            ),
        }

    def root(
        self,
        identity: str,
        *,
        root_code: str,
        category: str,
        scope_kind: str,
        scope_value: str,
        owner_stage: int,
        disposition: str,
    ) -> Root:
        key = stable_key("blocker_root", identity)
        value = self.roots.get(key)
        if value is None:
            value = Root(
                key=key,
                root_code=root_code,
                category=category,
                scope_kind=scope_kind,
                scope_value=scope_value,
                owner_stage=owner_stage,
                disposition=disposition,
            )
            self.roots[key] = value
        return value

    def add_gaps(self) -> int:
        count = 0
        entity_stages = {
            str(row["entity_key"]): int(row["source_stage"])
            for row in self.source.execute(
                "SELECT entity_key,source_stage FROM entities ORDER BY entity_key"
            )
        }
        for row in self.source.execute("SELECT * FROM gaps ORDER BY gap_key"):
            count += 1
            entity = str(row["entity_key"])
            kind = _entity_kind(entity)
            code = str(row["blocker_code"])
            provenance = str(row["provenance"])
            resolution = self.resolver.resolve(entity)
            if (
                resolution is not None
                and code
                in {
                    "referenced_endpoint_not_in_decoded_stages",
                    "referenced_endpoint_not_in_prior_stages",
                }
                and provenance == "aa8-client-forensics"
            ):
                self.reconcile(
                    source_kind="gap",
                    source_key=str(row["gap_key"]),
                    entity_key=entity,
                    original_state=str(row["state"]),
                    resolution=resolution,
                    evidence={
                        "blocker_code": code,
                        "policy": (
                            "local endpoint gap resolved by a strong entity "
                            "observation in another native forensic stage"
                        ),
                        "provenance": provenance,
                    },
                )
                continue
            category, disposition = classify_gap(
                code,
                provenance=provenance,
                entity_kind=kind,
            )
            owner_stage = owner_stage_for_kind(
                kind,
                entity_stages.get(entity, 20),
            )
            root = self.root(
                f"gap:{code}:{kind}:{provenance}",
                root_code=code,
                category=category,
                scope_kind="entity_kind",
                scope_value=kind,
                owner_stage=owner_stage,
                disposition=disposition,
            )
            state = str(row["state"])
            root.states.add(state)
            root.authorities.add(
                "server_observed"
                if category == "downstream_server"
                else "client_native"
            )
            root.required_evidence.add(str(row["required_evidence"]))
            root.provenance.add(provenance)
            root.max_severity = max(root.max_severity, int(row["severity"]))
            root.gap_count += 1
            root.impact(
                subject_kind="entity",
                subject_key=entity,
                entity_key=entity,
                state=state,
                evidence_kind="gap",
            )
            signature = stable_key(
                "gap_signature",
                code,
                row["reason"],
                row["required_evidence"],
                provenance,
            )
            root.add_evidence(
                evidence_kind="gap_signature",
                source_key=signature,
                source_stage=owner_stage,
                state=state,
                payload={
                    "reason": str(row["reason"]),
                    "required_evidence": str(row["required_evidence"]),
                    "provenance": provenance,
                },
            )
        return count

    def add_opaque(self) -> int:
        count = 0
        for row in self.source.execute(
            """
            SELECT * FROM opaque_regions
            WHERE state IN ('blocked','missing','opaque','unknown')
            ORDER BY opaque_key
            """
        ):
            code = str(row["blocker_code"])
            surface = str(row["surface"])
            source_stage = int(row["source_stage"])
            category, disposition = classify_opaque(code, surface=surface)
            scope = (
                f"stage:{source_stage}"
                if code == "native_result_absent"
                else "cross_stage"
            )
            root = self.root(
                f"opaque:{code}:{scope}",
                root_code=code,
                category=category,
                scope_kind="surface_group",
                scope_value=scope,
                owner_stage=(
                    70 if category == "wiki_corroboration" else source_stage
                ),
                disposition=disposition,
            )
            state = str(row["state"])
            root.states.add(state)
            root.authorities.add(
                "wiki_visible"
                if category == "wiki_corroboration"
                else (
                    "server_observed"
                    if category == "downstream_server"
                    else "client_native"
                )
            )
            root.provenance.add(PROVENANCE)
            root.opaque_count += 1
            subject = f"stage{source_stage}:{surface}:{row['locator']}"
            root.impact(
                subject_kind="surface",
                subject_key=subject,
                entity_key=None,
                state=state,
                evidence_kind="opaque_region",
            )
            root.add_evidence(
                evidence_kind="opaque_region",
                source_key=str(row["opaque_key"]),
                source_stage=source_stage,
                state=state,
                payload={
                    "locator": str(row["locator"]),
                    "reason": str(row["reason"]),
                    "searched_evidence": json.loads(
                        str(row["searched_evidence_json"])
                    ),
                    "surface": surface,
                },
            )
            count += 1
        return count

    def add_coverage(self) -> int:
        count = 0
        for row in self.source.execute(
            """
            SELECT * FROM coverage
            WHERE state IN ('blocked','missing','opaque','unknown')
            ORDER BY coverage_key
            """
        ):
            dimension = str(row["dimension"])
            state = str(row["state"])
            authority = str(row["authority"])
            if authority == "server_observed":
                category, disposition, owner = (
                    "downstream_server",
                    "downstream_out_of_scope",
                    20,
                )
            elif dimension == "wiki":
                category, disposition, owner = (
                    "wiki_corroboration",
                    "corroborative_only",
                    70,
                )
            elif dimension in {"physical_asset", "textual_asset_references"}:
                category, disposition, owner = (
                    "asset_resolution",
                    "actionable",
                    60,
                )
            elif dimension == "lifecycle":
                category, disposition, owner = (
                    "native_lifecycle",
                    "actionable",
                    20,
                )
            elif dimension in {"schema_layout", "string_cache"}:
                category, disposition, owner = (
                    "query_layout",
                    "actionable",
                    10,
                )
            else:
                category, disposition, owner = (
                    "negative_evidence",
                    "actionable",
                    10,
                )
            root = self.root(
                f"coverage:{dimension}:{state}:{authority}",
                root_code=f"coverage_{dimension}_{state}",
                category=category,
                scope_kind="coverage_dimension",
                scope_value=dimension,
                owner_stage=owner,
                disposition=disposition,
            )
            scope = str(row["scope_key"])
            root.states.add(state)
            root.authorities.add(authority)
            root.provenance.add(str(row["provenance"]))
            root.coverage_count += 1
            root.impact(
                subject_kind="coverage_scope",
                subject_key=scope,
                entity_key=scope if ":" in scope else None,
                state=state,
                evidence_kind="coverage",
            )
            root.add_evidence(
                evidence_kind="coverage_signature",
                source_key=f"{dimension}:{state}:{authority}",
                source_stage=owner,
                state=state,
                payload={
                    "authority": authority,
                    "capability": row["capability"],
                    "dimension": dimension,
                    "provenance": str(row["provenance"]),
                },
            )
            count += 1
        return count

    def add_queries(self) -> int:
        count = 0
        rows = self.source.execute(
            """
            SELECT q.*,
                   COUNT(c.cached_result_key) AS result_count,
                   SUM(CASE WHEN c.state='blocked' THEN 1 ELSE 0 END)
                       AS blocked_results,
                   SUM(CASE WHEN c.state='confirmed' THEN 1 ELSE 0 END)
                       AS confirmed_results
            FROM query_specs q
            LEFT JOIN cached_results c ON c.query_key=q.query_key
            GROUP BY q.query_key
            HAVING q.state IN ('blocked','unknown')
                OR SUM(CASE WHEN c.state='blocked' THEN 1 ELSE 0 END)>0
            ORDER BY q.query_key
            """
        )
        for row in rows:
            query_key = str(row["query_key"])
            qstate = str(row["state"])
            blocked_results = int(row["blocked_results"] or 0)
            confirmed_results = int(row["confirmed_results"] or 0)
            result_count = int(row["result_count"] or 0)
            confirmed_equivalent = None
            replacement_keys: list[str] = []
            if not blocked_results and qstate == "unknown":
                confirmed_equivalent = self.source.execute(
                    """
                    SELECT q2.query_key
                    FROM query_specs q2
                    WHERE q2.query_key<>?
                      AND q2.state='confirmed'
                      AND q2.table_name=?
                      AND q2.sql_text IS ?
                      AND q2.columns_json=?
                      AND q2.layout_json=?
                    ORDER BY q2.query_key
                    LIMIT 1
                    """,
                    (
                        query_key,
                        row["table_name"],
                        row["sql_text"],
                        row["columns_json"],
                        row["layout_json"],
                    ),
                ).fetchone()
                if confirmed_equivalent is not None:
                    replacement_keys = [
                        str(confirmed_equivalent["query_key"])
                    ]
                else:
                    selected_columns = _selected_sql_columns(
                        row["sql_text"]
                    )
                    stored_columns = tuple(
                        json.loads(str(row["columns_json"]))
                    )
                    if selected_columns and selected_columns != stored_columns:
                        sql_replacement = self.source.execute(
                            """
                            SELECT q.query_key,q.start_offset,
                                   q.loader_consumer,
                                   EXISTS(
                                       SELECT 1 FROM cached_results c
                                       WHERE c.query_key=q.query_key
                                         AND c.state='confirmed'
                                   ) AS has_confirmed_result
                            FROM query_specs q
                            WHERE query_key<>?
                              AND q.state='confirmed'
                              AND q.table_name=?
                              AND q.sql_text IS ?
                              AND q.columns_json=?
                            ORDER BY q.query_key
                            LIMIT 1
                            """,
                            (
                                query_key,
                                row["table_name"],
                                row["sql_text"],
                                canonical_json(list(selected_columns)),
                            ),
                        ).fetchone()
                        descriptor_replacement = self.source.execute(
                            """
                            SELECT query_key FROM query_specs
                            WHERE query_key<>?
                              AND state='confirmed'
                              AND table_name=?
                              AND columns_json=?
                              AND layout_json=?
                              AND sql_text IS NOT ?
                            ORDER BY query_key
                            LIMIT 1
                            """,
                            (
                                query_key,
                                row["table_name"],
                                row["columns_json"],
                                row["layout_json"],
                                row["sql_text"],
                            ),
                        ).fetchone()
                        if sql_replacement is not None:
                            if descriptor_replacement is not None:
                                replacement_keys = sorted(
                                    {
                                        str(sql_replacement["query_key"]),
                                        str(
                                            descriptor_replacement[
                                                "query_key"
                                            ]
                                        ),
                                    }
                                )
                            elif (
                                int(
                                    sql_replacement[
                                        "has_confirmed_result"
                                    ]
                                )
                                and sql_replacement["start_offset"]
                                is not None
                                and sql_replacement["loader_consumer"]
                            ):
                                replacement_keys = [
                                    str(sql_replacement["query_key"])
                                ]
            if replacement_keys:
                replacement_key = replacement_keys[0]
                record = {
                    "original_query_key": query_key,
                    "replacement_query_key": replacement_key,
                    "replacement_query_keys": replacement_keys,
                    "table_name": str(row["table_name"]),
                    "sql_text": row["sql_text"],
                    "columns_json": json.loads(str(row["columns_json"])),
                    "layout_json": json.loads(str(row["layout_json"])),
                    "original_state": qstate,
                    "replacement_state": "confirmed",
                    "confirmed_results": confirmed_results,
                    "reason": (
                        "Equivalent canonical query evidence supersedes the "
                        "historical query association."
                    ),
                }
                self.superseded_queries.append(record)
                self.reconciliation_rows.append(
                    (
                        stable_key(
                            "stage90",
                            "cross-stage-query-reconciliation",
                            query_key,
                            *replacement_keys,
                        ),
                        "cross_stage_query_reconciliations",
                        query_key,
                        canonical_json(record),
                        "derived_forensic",
                        PROVENANCE,
                    )
                )
                self.reconciliation_counts["query"] += 1
                self.reconciliation_by_kind["query:query"] += 1
                count += 1
                continue
            if blocked_results:
                category, disposition = "cached_result_decode", "actionable"
            elif qstate == "blocked":
                category, disposition = "query_layout", "actionable"
            elif (
                confirmed_results > 0
                and row["loader_consumer"] is not None
                and row["start_offset"] is not None
            ):
                category, disposition = "query_state_audit", "audit_required"
            else:
                category, disposition = "query_layout", "actionable"
            owner = _query_stage(query_key)
            table = str(row["table_name"])
            root = self.root(
                f"query:{query_key}",
                root_code=f"query_incomplete:{table}",
                category=category,
                scope_kind="query",
                scope_value=table,
                owner_stage=owner,
                disposition=disposition,
            )
            root.states.add("blocked" if blocked_results else qstate)
            root.authorities.add("client_native")
            root.provenance.add(PROVENANCE)
            root.query_count += 1
            root.impact(
                subject_kind="query",
                subject_key=query_key,
                entity_key=None,
                state="blocked" if blocked_results else qstate,
                evidence_kind="query_spec",
            )
            root.add_evidence(
                evidence_kind="query_spec",
                source_key=query_key,
                source_stage=owner,
                state=qstate,
                payload={
                    "blocked_results": blocked_results,
                    "confirmed_results": confirmed_results,
                    "loader_consumer": row["loader_consumer"],
                    "result_count": result_count,
                    "source_module": str(row["source_module"]),
                    "start_offset": row["start_offset"],
                    "stream_name": row["stream_name"],
                    "table_name": table,
                },
            )
            count += 1
        return count

    def add_consumers(self) -> int:
        count = 0
        for row in self.source.execute(
            """
            SELECT * FROM consumers
            WHERE state IN ('blocked','missing','opaque','unknown')
            ORDER BY consumer_key
            """
        ):
            key = str(row["consumer_key"])
            scope = str(row["scope_key"])
            root = self.root(
                f"consumer:{key}",
                root_code=f"consumer_unconfirmed:{row['consumer_kind']}",
                category="native_consumer",
                scope_kind="consumer",
                scope_value=str(row["name"]),
                owner_stage=10,
                disposition="actionable",
            )
            state = str(row["state"])
            root.states.add(state)
            root.authorities.add("client_native")
            root.provenance.add(PROVENANCE)
            root.consumer_count += 1
            root.impact(
                subject_kind="consumer",
                subject_key=key,
                entity_key=scope if ":" in scope else None,
                state=state,
                evidence_kind="consumer",
            )
            root.add_evidence(
                evidence_kind="consumer",
                source_key=key,
                source_stage=10,
                state=state,
                payload={
                    "architecture": row["architecture"],
                    "locator": row["locator"],
                    "module": row["module"],
                    "name": str(row["name"]),
                    "scope_key": scope,
                },
            )
            count += 1
        return count

    def add_entities(self) -> int:
        count = 0
        for row in self.source.execute(
            """
            SELECT entity_key,kind,lifecycle,state,authority,source_stage
            FROM entities
            WHERE state IN ('blocked','missing','opaque','unknown')
              AND lifecycle NOT IN ('localization_only','tombstone')
            ORDER BY kind,entity_key
            """
        ):
            count += 1
            entity = str(row["entity_key"])
            resolution = self.resolver.resolve(entity)
            if resolution is not None:
                self.reconcile(
                    source_kind="entity",
                    source_key=entity,
                    entity_key=entity,
                    original_state=str(row["state"]),
                    resolution=resolution,
                    evidence={
                        "current_lifecycle": str(row["lifecycle"]),
                        "current_source_stage": int(row["source_stage"]),
                        "policy": (
                            "consolidation winner was unresolved, but another "
                            "native stage contains a strong observation"
                        ),
                    },
                )
                continue
            kind = str(row["kind"])
            state = str(row["state"])
            lifecycle = str(row["lifecycle"])
            category = (
                "native_lifecycle"
                if lifecycle == "unknown"
                else (
                    "asset_resolution"
                    if kind in {"asset_file", "asset_reference", "icon"}
                    else "native_entity_state"
                )
            )
            owner = owner_stage_for_kind(kind, int(row["source_stage"]))
            root = self.root(
                f"entity:{kind}:{state}:{lifecycle}",
                root_code=f"entity_{state}:{kind}",
                category=category,
                scope_kind="entity_kind",
                scope_value=kind,
                owner_stage=owner,
                disposition="actionable",
            )
            root.states.add(state)
            root.authorities.add(str(row["authority"]))
            root.provenance.add(PROVENANCE)
            root.impact(
                subject_kind="entity",
                subject_key=entity,
                entity_key=entity,
                state=state,
                evidence_kind="entity_state",
            )
        return count

    def add_relations(self) -> int:
        count = 0
        for row in self.source.execute(
            """
            SELECT r.relation_key,r.src_entity_key,r.dst_entity_key,r.relation,
                   r.state,r.authority,r.provenance,r.source_artifact_key,
                   r.locator,r.required,r.evidence_json,
                   e.kind AS dst_kind,e.source_stage
            FROM relations r
            JOIN entities e ON e.entity_key=r.dst_entity_key
            WHERE r.state IN ('blocked','missing','opaque','unknown')
            ORDER BY r.relation_key
            """
        ):
            count += 1
            dst_kind = str(row["dst_kind"])
            state = str(row["state"])
            authority = str(row["authority"])
            provenance = str(row["provenance"])
            destination = str(row["dst_entity_key"])
            resolution = self.resolver.resolve(destination)
            asset_corroboration = relation_is_asset_corroboration(
                authority=authority,
                provenance=provenance,
            )
            if (
                not asset_corroboration
                and resolution is not None
                and relation_can_close_from_destination(
                    authority=authority,
                    provenance=provenance,
                )
            ):
                self.reconcile(
                    source_kind="relation",
                    source_key=str(row["relation_key"]),
                    entity_key=destination,
                    original_state=state,
                    resolution=resolution,
                    evidence={
                        "authority": authority,
                        "locator": str(row["locator"]),
                        "policy": (
                            "native edge was observed; only its destination "
                            "closure was unresolved in the source stage"
                        ),
                        "provenance": provenance,
                        "relation": str(row["relation"]),
                        "source_artifact_key": row["source_artifact_key"],
                        "src_entity_key": str(row["src_entity_key"]),
                    },
                )
                continue
            category = (
                "asset_resolution"
                if asset_corroboration
                else "relation_closure"
            )
            owner = (
                60
                if asset_corroboration
                else owner_stage_for_kind(
                    dst_kind,
                    int(row["source_stage"]),
                )
            )
            root_code = (
                f"asset_reference_relation_{state}:{dst_kind}"
                if asset_corroboration
                else f"relation_{state}:{dst_kind}"
            )
            root = self.root(
                (
                    f"relation:{category}:{state}:{authority}:"
                    f"{provenance}:{dst_kind}"
                ),
                root_code=root_code,
                category=category,
                scope_kind="destination_kind",
                scope_value=dst_kind,
                owner_stage=owner,
                disposition="actionable",
            )
            self.relation_root_keys.add(root.key)
            root.states.add(state)
            root.authorities.add(authority)
            root.provenance.add(PROVENANCE)
            root.relation_count += 1
            root.impact(
                subject_kind="entity",
                subject_key=destination,
                entity_key=destination,
                state=state,
                evidence_kind="relation",
            )
        for root_key in sorted(self.relation_root_keys):
            root = self.roots[root_key]
            root.add_evidence(
                evidence_kind="relation_group",
                source_key=f"{root.root_code}:{_root_authority(root)}",
                source_stage=root.owner_stage,
                state=_worst_state(root.states),
                payload={
                    "authority": sorted(root.authorities),
                    "category": root.category,
                    "destination_kind": root.scope_value,
                    "relation_count": root.relation_count,
                },
                count=root.relation_count,
            )
        return count

    def add_wiki(self) -> dict[str, int]:
        counts = {"entity": 0, "property": 0, "relation": 0}
        for row in self.source.execute(
            """
            SELECT wiki_entity_key,entity_key,comparison_state
            FROM wiki_entities
            WHERE comparison_state='native_only'
            ORDER BY entity_key
            """
        ):
            entity = str(row["entity_key"])
            kind = _entity_kind(entity)
            root = self.root(
                f"wiki:native_only:{kind}",
                root_code=f"wiki_native_only:{kind}",
                category="wiki_corroboration",
                scope_kind="entity_kind",
                scope_value=kind,
                owner_stage=70,
                disposition="corroborative_only",
            )
            root.states.add("unknown")
            root.authorities.add("wiki_visible")
            root.provenance.add(PROVENANCE)
            root.impact(
                subject_kind="entity",
                subject_key=entity,
                entity_key=entity,
                state="unknown",
                evidence_kind="wiki_entity",
            )
            counts["entity"] += 1
        for row in self.source.execute(
            """
            SELECT e.entity_key,p.property_name,p.wiki_property_key
            FROM wiki_properties p
            JOIN wiki_entities e
              ON e.wiki_entity_key=p.wiki_entity_key
            WHERE p.comparison_state='conflict'
            ORDER BY e.entity_key,p.property_name
            """
        ):
            entity = str(row["entity_key"])
            kind = _entity_kind(entity)
            property_name = str(row["property_name"])
            root = self.root(
                f"wiki:conflict:{kind}:{property_name}",
                root_code=f"wiki_conflict:{property_name}",
                category="wiki_corroboration",
                scope_kind="entity_kind",
                scope_value=kind,
                owner_stage=70,
                disposition="corroborative_only",
            )
            root.states.add("unknown")
            root.authorities.add("wiki_visible")
            root.provenance.add(PROVENANCE)
            root.impact(
                subject_kind="entity",
                subject_key=entity,
                entity_key=entity,
                state="unknown",
                evidence_kind="wiki_property",
            )
            root.add_evidence(
                evidence_kind="wiki_property",
                source_key=str(row["wiki_property_key"]),
                source_stage=70,
                state="unknown",
                payload={"entity_key": entity, "property_name": property_name},
            )
            counts["property"] += 1
        for row in self.source.execute(
            """
            SELECT r.wiki_relation_key,r.dst_kind,r.comparison_state,
                   e.entity_key
            FROM wiki_relations r
            JOIN wiki_entities e
              ON e.wiki_entity_key=r.src_wiki_entity_key
            WHERE r.comparison_state IN ('wiki_only','unresolved')
            ORDER BY r.wiki_relation_key
            """
        ):
            comparison = str(row["comparison_state"])
            dst_kind = str(row["dst_kind"])
            root = self.root(
                f"wiki:relation:{comparison}:{dst_kind}",
                root_code=f"wiki_relation_{comparison}:{dst_kind}",
                category="wiki_corroboration",
                scope_kind="destination_kind",
                scope_value=dst_kind,
                owner_stage=70,
                disposition="corroborative_only",
            )
            entity = str(row["entity_key"])
            root.states.add("unknown")
            root.authorities.add("wiki_visible")
            root.provenance.add(PROVENANCE)
            root.relation_count += 1
            root.impact(
                subject_kind="entity",
                subject_key=entity,
                entity_key=entity,
                state="unknown",
                evidence_kind="wiki_relation",
            )
            counts["relation"] += 1
        return counts


def _root_authority(root: Root) -> str:
    return "+".join(sorted(root.authorities)) or "unknown"


def _compute_priority(root: Root) -> None:
    entity_count = sum(
        1 for impact in root.impacts.values() if impact.entity_key is not None
    )
    fanout_units = (
        entity_count
        + root.relation_count
        + root.incoming_fanout
        + root.outgoing_fanout
    )
    root.fanout_score = min(100, max(1, fanout_units + 1).bit_length() * 8)
    root.effort_score = EFFORT_BY_CATEGORY[root.category]
    state_bonus = {
        "blocked": 24,
        "missing": 20,
        "opaque": 16,
        "unknown": 8,
    }.get(_worst_state(root.states), 0)
    authority_bonus = (
        16
        if any(value.startswith("client_native") for value in root.authorities)
        else (8 if "client_asset" in root.authorities else 0)
    )
    root.priority_score = (
        CATEGORY_BASE[root.category]
        + root.max_severity * 8
        + root.fanout_score
        + state_bonus
        + authority_bonus
        - root.effort_score * 4
    )
    if root.disposition == "downstream_out_of_scope":
        root.priority_score -= 1000


def _insert_validation(
    connection: sqlite3.Connection,
    *,
    check_name: str,
    status: str,
    evidence: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO validation_events(
            validation_key,scope_kind,scope_id,check_name,status,evidence_json
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            stable_key("validation", "stage", "90", check_name),
            "stage",
            "90",
            check_name,
            status,
            canonical_json(evidence),
        ),
    )


def populate_stage_90(
    destination: sqlite3.Connection,
    _item_source: sqlite3.Connection,
    context: BuildContext,
) -> None:
    config = context.config
    if not config.consolidated.is_file():
        raise FileNotFoundError(config.consolidated)
    source = open_read_only(config.consolidated)
    upstream_lineage = [
        {
            "stage": int(row["stage_id"]),
            "database": str(row["database_name"]),
            "sha256": str(row["database_sha256"]),
            "schema_version": int(row["schema_version"]),
        }
        for row in source.execute(
            """
            SELECT stage_id,database_name,database_sha256,schema_version
            FROM stage_lineage
            WHERE stage_id<>90
            ORDER BY stage_id
            """
        )
    ]
    if not upstream_lineage:
        source.close()
        raise RuntimeError("Stage 90 requires upstream stage lineage")
    upstream_payload = canonical_json(upstream_lineage).encode("utf-8")
    source_sha = hashlib.sha256(upstream_payload).hexdigest().upper()
    stage_paths = (
        (0, config.stage_00),
        (10, config.stage_10),
        (20, config.stage_20),
        (30, config.stage_30),
        (40, config.stage_40),
        (50, config.stage_50),
        (60, config.stage_60),
        (70, config.stage_70),
    )
    resolver = CrossStageResolver.from_stage_databases(
        source,
        stage_paths,
    )
    builder = ClosureBuilder(source, resolver)
    source_counts = {
        "gaps": builder.add_gaps(),
        "opaque_regions": builder.add_opaque(),
        "coverage_unresolved": builder.add_coverage(),
        "queries_incomplete": builder.add_queries(),
        "consumers_unresolved": builder.add_consumers(),
        "entities_unresolved": builder.add_entities(),
        "relations_unresolved": builder.add_relations(),
    }
    wiki_counts = builder.add_wiki()
    reconciliation = builder.reconciliation_summary()
    roots = builder.roots

    artifact_key = "stage90:stage80-consolidated-input"
    destination.execute(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,authority,
            state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            artifact_key,
            STAGE,
            "stage80_consolidated_input",
            "stage-lineage://" + ",".join(
                str(item["stage"]) for item in upstream_lineage
            ),
            len(upstream_payload),
            source_sha,
            config.client_build,
            "derived_forensic",
            "confirmed",
            PROVENANCE,
            canonical_json(
                {
                    "immutable_input": True,
                    "source_stage": 80,
                    "upstream_lineage": upstream_lineage,
                }
            ),
        ),
    )
    destination.execute(
        """
        INSERT INTO decoders(
            decoder_key,name,version,sha256,status,inputs_json,
            assumptions_json,provenance
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            "stage90:coverage-closure-classifier",
            "AA8 cross-stage blocker root and fan-out classifier",
            TOOL_VERSION,
            None,
            "confirmed",
            canonical_json(
                {
                    "upstream_lineage_sha256": source_sha,
                    "source_counts": source_counts,
                    "wiki_counts": wiki_counts,
                    "cross_stage_reconciliation": reconciliation,
                }
            ),
            canonical_json(
                {
                    "server_acceptance_is_downstream": True,
                    "wiki_is_corroborative_only": True,
                    "priority_formula_is_integer_only": True,
                    "source_gaps_are_preserved": True,
                    "strong_cross_stage_states": ["confirmed", "tombstone"],
                }
            ),
            PROVENANCE,
        ),
    )

    preliminary_rows = []
    for root in sorted(roots.values(), key=lambda value: value.key):
        preliminary_rows.append(
            (
                root.key,
                root.root_code,
                root.category,
                root.scope_kind,
                root.scope_value,
                root.owner_stage,
                _worst_state(root.states),
                root.disposition,
                _root_authority(root),
                root.max_severity,
                root.gap_count,
                root.opaque_count,
                root.coverage_count,
                root.query_count,
                root.consumer_count,
                root.relation_count,
                sum(
                    1
                    for impact in root.impacts.values()
                    if impact.entity_key is not None
                ),
                0,
                0,
                0,
                0,
                0,
                canonical_json(sorted(root.required_evidence)),
                _recommended_action(
                    root.category,
                    root.scope_value,
                    root.root_code,
                ),
                "+".join(sorted(root.provenance)) or PROVENANCE,
                canonical_json({"classification_version": TOOL_VERSION}),
            )
        )
    destination.executemany(
        """
        INSERT INTO source_records(
            source_record_key,source_table,source_pk,record_json,
            authority,provenance
        ) VALUES(?,?,?,?,?,?)
        """,
        sorted(
            builder.reconciliation_rows,
            key=lambda value: str(value[0]),
        ),
    )
    destination.executemany(
        """
        INSERT INTO blocker_roots(
            blocker_root_key,root_code,category,scope_kind,scope_value,
            owner_stage,state,disposition,authority,max_severity,gap_count,
            opaque_count,coverage_count,query_count,consumer_count,
            relation_count,entity_count,incoming_fanout,outgoing_fanout,
            effort_score,fanout_score,priority_score,required_evidence_json,
            recommended_action,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        preliminary_rows,
    )
    impact_rows = []
    evidence_rows = []
    for root in sorted(roots.values(), key=lambda value: value.key):
        for impact in sorted(
            root.impacts.values(),
            key=lambda value: (value.subject_kind, value.subject_key),
        ):
            impact_rows.append(
                (
                    stable_key(
                        "blocker_impact",
                        root.key,
                        impact.subject_kind,
                        impact.subject_key,
                    ),
                    root.key,
                    impact.subject_kind,
                    impact.subject_key,
                    impact.entity_key,
                    _worst_state(impact.states),
                    impact.count,
                    canonical_json(
                        {"evidence_kinds": sorted(impact.evidence_kinds)}
                    ),
                )
            )
        for evidence in sorted(
            root.evidence.values(),
            key=lambda value: (value.evidence_kind, value.source_key),
        ):
            evidence_rows.append(
                (
                    stable_key(
                        "blocker_evidence",
                        root.key,
                        evidence.evidence_kind,
                        evidence.source_key,
                    ),
                    root.key,
                    evidence.evidence_kind,
                    evidence.source_key,
                    evidence.source_stage,
                    _worst_state(evidence.states),
                    canonical_json(
                        {
                            "count": evidence.count,
                            "samples": evidence.payloads,
                        }
                    ),
                )
            )
    destination.executemany(
        """
        INSERT INTO blocker_impacts(
            blocker_impact_key,blocker_root_key,subject_kind,subject_key,
            entity_key,state,impact_count,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        impact_rows,
    )
    destination.executemany(
        """
        INSERT INTO blocker_evidence(
            blocker_evidence_key,blocker_root_key,evidence_kind,source_key,
            source_stage,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?)
        """,
        evidence_rows,
    )

    destination.commit()
    # ATTACH does not inherit URI handling from Python's primary connection.
    # The build only issues SELECTs against this alias; use the resolved path
    # and preserve the source hash above as the immutability assertion.
    destination.execute(
        "ATTACH DATABASE ? AS baseline",
        (config.consolidated.resolve().as_posix(),),
    )
    for row in destination.execute(
        """
        SELECT bi.blocker_root_key,COUNT(DISTINCT r.relation_key) AS n
        FROM blocker_impacts bi
        JOIN baseline.relations r ON r.dst_entity_key=bi.entity_key
        WHERE bi.entity_key IS NOT NULL
        GROUP BY bi.blocker_root_key
        """
    ):
        roots[str(row["blocker_root_key"])].incoming_fanout = int(row["n"])
    for row in destination.execute(
        """
        SELECT bi.blocker_root_key,COUNT(DISTINCT r.relation_key) AS n
        FROM blocker_impacts bi
        JOIN baseline.relations r ON r.src_entity_key=bi.entity_key
        WHERE bi.entity_key IS NOT NULL
        GROUP BY bi.blocker_root_key
        """
    ):
        roots[str(row["blocker_root_key"])].outgoing_fanout = int(row["n"])
    destination.execute("DETACH DATABASE baseline")

    for root in roots.values():
        _compute_priority(root)
        destination.execute(
            """
            UPDATE blocker_roots
            SET incoming_fanout=?,outgoing_fanout=?,effort_score=?,
                fanout_score=?,priority_score=?,evidence_json=?
            WHERE blocker_root_key=?
            """,
            (
                root.incoming_fanout,
                root.outgoing_fanout,
                root.effort_score,
                root.fanout_score,
                root.priority_score,
                canonical_json(
                    {
                        "acceptance": _acceptance(root.category),
                        "lane": _category_lane(root.category),
                        "source_evidence_rows": len(root.evidence),
                    }
                ),
                root.key,
            ),
        )
    ordered = sorted(
        roots.values(),
        key=lambda root: (
            root.disposition == "downstream_out_of_scope",
            root.category == "wiki_corroboration",
            -root.priority_score,
            root.key,
        ),
    )
    queue_rows = []
    for rank, root in enumerate(ordered, 1):
        status = (
            "deferred"
            if root.disposition == "downstream_out_of_scope"
            else (
                "corroborative"
                if root.disposition == "corroborative_only"
                else (
                    "audit_required"
                    if root.disposition == "audit_required"
                    else "queued"
                )
            )
        )
        queue_rows.append(
            (
                stable_key("work_queue", root.key),
                rank,
                root.key,
                _category_lane(root.category),
                root.owner_stage,
                status,
                root.priority_score,
                root.effort_score,
                root.fanout_score,
                _recommended_action(
                    root.category,
                    root.scope_value,
                    root.root_code,
                ),
                canonical_json(_acceptance(root.category)),
                canonical_json(
                    {
                        "category_base": CATEGORY_BASE[root.category],
                        "disposition": root.disposition,
                        "incoming_fanout": root.incoming_fanout,
                        "max_severity": root.max_severity,
                        "outgoing_fanout": root.outgoing_fanout,
                        "relation_count": root.relation_count,
                        "state": _worst_state(root.states),
                    }
                ),
            )
        )
    destination.executemany(
        """
        INSERT INTO work_queue(
            work_queue_key,rank,blocker_root_key,lane,owner_stage,status,
            priority_score,effort_score,fanout_score,next_action,
            acceptance_json,rationale_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        queue_rows,
    )

    downstream_gaps = sum(
        root.gap_count
        for root in roots.values()
        if root.disposition == "downstream_out_of_scope"
    )
    metadata = {
        "stage90.blocker_roots": len(roots),
        "stage90.upstream_lineage_sha256": source_sha,
        "stage90.downstream_gap_rows": downstream_gaps,
        "stage90.evidence_rows": len(evidence_rows),
        "stage90.impact_rows": len(impact_rows),
        "stage90.source_gaps": source_counts["gaps"],
        "stage90.source_opaque_regions": source_counts["opaque_regions"],
        "stage90.work_queue_rows": len(queue_rows),
        "stage90.reconciled_gap_rows": builder.reconciliation_counts["gap"],
        "stage90.reconciled_entity_rows": builder.reconciliation_counts[
            "entity"
        ],
        "stage90.reconciled_relation_rows": builder.reconciliation_counts[
            "relation"
        ],
        "stage90.reconciliation_records_sha256": reconciliation[
            "records_sha256"
        ],
    }
    destination.executemany(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        sorted((key, str(value)) for key, value in metadata.items()),
    )

    root_gap_count = int(
        destination.execute(
            "SELECT COALESCE(SUM(gap_count),0) FROM blocker_roots"
        ).fetchone()[0]
    )
    root_opaque_count = int(
        destination.execute(
            "SELECT COALESCE(SUM(opaque_count),0) FROM blocker_roots"
        ).fetchone()[0]
    )
    expected_active_gaps = (
        source_counts["gaps"] - builder.reconciliation_counts["gap"]
    )
    if builder.reconciled_asset_relation_count:
        raise RuntimeError(
            "Asset-corroborative relations were promoted by cross-stage "
            f"reconciliation: {builder.reconciled_asset_relation_count}"
        )
    if root_gap_count != expected_active_gaps:
        raise RuntimeError(
            f"Stage 90 gap loss: roots={root_gap_count} "
            f"source={source_counts['gaps']} "
            f"reconciled={builder.reconciliation_counts['gap']}"
        )
    if root_opaque_count != source_counts["opaque_regions"]:
        raise RuntimeError(
            f"Stage 90 opaque loss: roots={root_opaque_count} "
            f"source={source_counts['opaque_regions']}"
        )
    checks = {
        "orphan_impacts": """
            SELECT COUNT(*) FROM blocker_impacts i
            LEFT JOIN blocker_roots r
              ON r.blocker_root_key=i.blocker_root_key
            WHERE r.blocker_root_key IS NULL
        """,
        "orphan_evidence": """
            SELECT COUNT(*) FROM blocker_evidence e
            LEFT JOIN blocker_roots r
              ON r.blocker_root_key=e.blocker_root_key
            WHERE r.blocker_root_key IS NULL
        """,
        "orphan_work_queue": """
            SELECT COUNT(*) FROM work_queue q
            LEFT JOIN blocker_roots r
              ON r.blocker_root_key=q.blocker_root_key
            WHERE r.blocker_root_key IS NULL
        """,
    }
    for name, sql in checks.items():
        value = int(destination.execute(sql).fetchone()[0])
        if value:
            raise RuntimeError(f"{name}={value}")
        _insert_validation(
            destination,
            check_name=name,
            status="confirmed",
            evidence={"count": value},
        )
    _insert_validation(
        destination,
        check_name="all_gap_rows_classified",
        status="confirmed",
        evidence={
            "active_root_gap_count": root_gap_count,
            "reconciled_gap_count": builder.reconciliation_counts["gap"],
            "source": source_counts["gaps"],
        },
    )
    _insert_validation(
        destination,
        check_name="cross_stage_reconciliation",
        status="confirmed",
        evidence=reconciliation,
    )
    _insert_validation(
        destination,
        check_name="equivalent_query_reconciliation",
        status="confirmed",
        evidence={
            "superseded_queries": len(builder.superseded_queries),
            "records": sorted(
                builder.superseded_queries,
                key=lambda row: (
                    str(row["table_name"]),
                    str(row["original_query_key"]),
                ),
            ),
        },
    )
    _insert_validation(
        destination,
        check_name="asset_corroboration_not_promoted",
        status="confirmed",
        evidence={
            "reconciled_asset_relation_count": (
                builder.reconciled_asset_relation_count
            )
        },
    )
    _insert_validation(
        destination,
        check_name="all_opaque_regions_classified",
        status="confirmed",
        evidence={
            "root_opaque_count": root_opaque_count,
            "source": source_counts["opaque_regions"],
        },
    )
    _insert_validation(
        destination,
        check_name="server_acceptance_separated",
        status="confirmed",
        evidence={"downstream_gap_rows": downstream_gaps},
    )
    _insert_validation(
        destination,
        check_name="work_queue_covers_every_root",
        status="confirmed" if len(queue_rows) == len(roots) else "blocked",
        evidence={"queue_rows": len(queue_rows), "roots": len(roots)},
    )
    source.close()
