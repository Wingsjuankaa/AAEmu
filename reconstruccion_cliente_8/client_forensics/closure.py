from __future__ import annotations

import fnmatch
import json
import re
import sqlite3
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import TOOL_NAME, TOOL_VERSION
from .schema import open_read_only
from .util import atomic_text, canonical_json, sha256_file


POLICY_FORMAT = "AA8_CLOSURE_POLICY_V1"
DOSSIER_FORMAT = "AA8_RECONSTRUCTION_DOSSIER_V1"
DEFAULT_POLICY_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "closure-profiles.json"
)
ISSUE_STATES = {"blocked", "missing", "opaque", "unknown"}
EXPANDABLE_STATES = {"confirmed", "corroborated", "not_applicable"}
DOWNSTREAM_BLOCKER_CODES = {
    "backend_missing",
    "backend_unknown",
    "dependency_closure_unknown",
    "persistence_unknown",
    "protocol_unknown",
    "validation_unknown",
}
PRESENTATION_BLOCKER_CATEGORIES = {"asset_resolution"}


@dataclass(frozen=True)
class TraversalDecision:
    action: str
    importance: str
    rule: str


@dataclass(frozen=True)
class TraversalRule:
    name: str
    current_kind: str
    direction: str
    relation: str
    neighbor_kind: str
    action: str
    importance: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any], ordinal: int) -> "TraversalRule":
        action = str(value.get("action", "expand"))
        if action not in {"expand", "skip", "terminal"}:
            raise ValueError(f"Unsupported closure action: {action}")
        direction = str(value.get("direction", "*"))
        if direction not in {"*", "incoming", "outgoing"}:
            raise ValueError(f"Unsupported closure direction: {direction}")
        importance = str(value.get("importance", "contextual"))
        if importance not in {"contextual", "required", "structural"}:
            raise ValueError(f"Unsupported closure importance: {importance}")
        return cls(
            name=str(value.get("name", f"rule-{ordinal}")),
            current_kind=str(value.get("current_kind", "*")),
            direction=direction,
            relation=str(value.get("relation", "*")),
            neighbor_kind=str(value.get("neighbor_kind", "*")),
            action=action,
            importance=importance,
        )

    def matches(
        self,
        *,
        current_kind: str,
        direction: str,
        relation: str,
        neighbor_kind: str,
    ) -> bool:
        return (
            fnmatch.fnmatchcase(current_kind, self.current_kind)
            and fnmatch.fnmatchcase(direction, self.direction)
            and fnmatch.fnmatchcase(relation, self.relation)
            and fnmatch.fnmatchcase(neighbor_kind, self.neighbor_kind)
        )


@dataclass(frozen=True)
class ClosurePolicy:
    name: str
    max_depth: int
    max_nodes: int
    max_edges_per_node: int
    default_outgoing: TraversalDecision
    default_incoming: TraversalDecision
    rules: tuple[TraversalRule, ...]
    source_path: Path
    source_sha256: str

    def decide(
        self,
        *,
        current_kind: str,
        direction: str,
        relation: str,
        neighbor_kind: str,
    ) -> TraversalDecision:
        for rule in self.rules:
            if rule.matches(
                current_kind=current_kind,
                direction=direction,
                relation=relation,
                neighbor_kind=neighbor_kind,
            ):
                return TraversalDecision(
                    action=rule.action,
                    importance=rule.importance,
                    rule=rule.name,
                )
        if direction == "outgoing":
            return self.default_outgoing
        return self.default_incoming


def _decision(value: dict[str, Any], name: str) -> TraversalDecision:
    action = str(value.get("action", "skip"))
    importance = str(value.get("importance", "contextual"))
    if action not in {"expand", "skip", "terminal"}:
        raise ValueError(f"Unsupported default closure action: {action}")
    if importance not in {"contextual", "required", "structural"}:
        raise ValueError(f"Unsupported default closure importance: {importance}")
    return TraversalDecision(action=action, importance=importance, rule=name)


def _resolve_profile(
    profiles: dict[str, Any],
    name: str,
    stack: tuple[str, ...] = (),
) -> dict[str, Any]:
    if name not in profiles:
        raise KeyError(f"Closure profile not found: {name}")
    if name in stack:
        raise ValueError(f"Closure profile inheritance cycle: {stack + (name,)}")
    current = dict(profiles[name])
    parent_name = current.pop("extends", None)
    if parent_name is None:
        return current
    parent = _resolve_profile(profiles, str(parent_name), stack + (name,))
    merged = dict(parent)
    merged["limits"] = {
        **dict(parent.get("limits", {})),
        **dict(current.get("limits", {})),
    }
    merged["defaults"] = {
        **dict(parent.get("defaults", {})),
        **dict(current.get("defaults", {})),
    }
    # Child rules have precedence over inherited rules.
    merged["rules"] = [
        *list(current.get("rules", [])),
        *list(parent.get("rules", [])),
    ]
    for key, value in current.items():
        if key not in {"limits", "defaults", "rules"}:
            merged[key] = value
    return merged


def load_closure_policy(
    root_kind: str,
    *,
    profile: str = "auto",
    policy_path: Path | None = None,
    max_depth: int | None = None,
    max_nodes: int | None = None,
    max_edges_per_node: int | None = None,
) -> ClosurePolicy:
    path = (policy_path or DEFAULT_POLICY_PATH).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("format") != POLICY_FORMAT:
        raise ValueError(f"Unsupported closure policy format in {path}")
    profiles = dict(raw.get("profiles", {}))
    selected = root_kind if profile == "auto" and root_kind in profiles else profile
    if selected == "auto":
        selected = "generic"
    resolved = _resolve_profile(profiles, selected)
    limits = dict(resolved.get("limits", {}))
    defaults = dict(resolved.get("defaults", {}))
    depth = int(max_depth if max_depth is not None else limits.get("max_depth", 7))
    nodes = int(max_nodes if max_nodes is not None else limits.get("max_nodes", 300))
    edges = int(
        max_edges_per_node
        if max_edges_per_node is not None
        else limits.get("max_edges_per_node", 60)
    )
    if depth < 0 or nodes < 1 or edges < 1:
        raise ValueError("Closure limits must be non-negative and non-zero")
    rules = tuple(
        TraversalRule.from_mapping(value, ordinal)
        for ordinal, value in enumerate(resolved.get("rules", []), start=1)
    )
    return ClosurePolicy(
        name=selected,
        max_depth=depth,
        max_nodes=nodes,
        max_edges_per_node=edges,
        default_outgoing=_decision(
            dict(defaults.get("outgoing", {})), "default-outgoing"
        ),
        default_incoming=_decision(
            dict(defaults.get("incoming", {})), "default-incoming"
        ),
        rules=rules,
        source_path=path,
        source_sha256=sha256_file(path),
    )


def _relation_rows(
    connection: sqlite3.Connection,
    entity_key: str,
    direction: str,
) -> Iterable[sqlite3.Row]:
    if direction == "outgoing":
        return connection.execute(
            """
            SELECT r.*,src.kind AS src_kind,src.native_id AS src_native_id,
                   dst.kind AS dst_kind,dst.native_id AS dst_native_id,
                   dst.lifecycle AS neighbor_lifecycle,
                   dst.state AS neighbor_state
            FROM relations r
            JOIN entities src ON src.entity_key=r.src_entity_key
            JOIN entities dst ON dst.entity_key=r.dst_entity_key
            WHERE r.src_entity_key=?
            ORDER BY r.relation,r.dst_entity_key,r.ordinal,r.relation_key
            """,
            (entity_key,),
        )
    return connection.execute(
        """
        SELECT r.*,src.kind AS src_kind,src.native_id AS src_native_id,
               dst.kind AS dst_kind,dst.native_id AS dst_native_id,
               src.lifecycle AS neighbor_lifecycle,
               src.state AS neighbor_state
        FROM relations r
        JOIN entities src ON src.entity_key=r.src_entity_key
        JOIN entities dst ON dst.entity_key=r.dst_entity_key
        WHERE r.dst_entity_key=?
        ORDER BY r.relation,r.src_entity_key,r.ordinal,r.relation_key
        """,
        (entity_key,),
    )


def _path_importance(parent: str, edge: str) -> str:
    if parent == "required" and edge in {"required", "structural"}:
        return "required"
    if parent == "root" and edge in {"required", "structural"}:
        return "required"
    return "contextual"


def _walk_graph(
    connection: sqlite3.Connection,
    root_key: str,
    policy: ClosurePolicy,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    root = connection.execute(
        "SELECT * FROM entities WHERE entity_key=?", (root_key,)
    ).fetchone()
    if root is None:
        raise KeyError(f"Entity not found: {root_key}")
    nodes: dict[str, dict[str, Any]] = {
        root_key: {
            **dict(root),
            "depth": 0,
            "path_importance": "root",
            "parent_entity_key": None,
            "via_relation_key": None,
        }
    }
    edges: dict[str, dict[str, Any]] = {}
    boundaries: list[dict[str, Any]] = []
    queue: deque[str] = deque((root_key,))
    expanded: set[str] = set()
    while queue:
        current_key = queue.popleft()
        if current_key in expanded:
            continue
        expanded.add(current_key)
        current = nodes[current_key]
        current_depth = int(current["depth"])
        if current_depth >= policy.max_depth:
            boundaries.append(
                {
                    "entity_key": current_key,
                    "reason": "max_depth_reached",
                    "limit": policy.max_depth,
                }
            )
            continue
        eligible: list[
            tuple[str, sqlite3.Row, str, TraversalDecision]
        ] = []
        skipped = Counter()
        for direction in ("outgoing", "incoming"):
            for row in _relation_rows(connection, current_key, direction):
                neighbor_key = (
                    str(row["dst_entity_key"])
                    if direction == "outgoing"
                    else str(row["src_entity_key"])
                )
                neighbor_kind = (
                    str(row["dst_kind"])
                    if direction == "outgoing"
                    else str(row["src_kind"])
                )
                decision = policy.decide(
                    current_kind=str(current["kind"]),
                    direction=direction,
                    relation=str(row["relation"]),
                    neighbor_kind=neighbor_kind,
                )
                if decision.action == "skip":
                    skipped[(direction, str(row["relation"]), decision.rule)] += 1
                    continue
                eligible.append((direction, row, neighbor_key, decision))
        if skipped:
            boundaries.extend(
                {
                    "entity_key": current_key,
                    "reason": "policy_excluded",
                    "direction": direction,
                    "relation": relation,
                    "rule": rule,
                    "count": count,
                }
                for (direction, relation, rule), count in sorted(skipped.items())
            )
        if len(eligible) > policy.max_edges_per_node:
            boundaries.append(
                {
                    "entity_key": current_key,
                    "reason": "max_edges_per_node",
                    "eligible": len(eligible),
                    "limit": policy.max_edges_per_node,
                    "skipped": len(eligible) - policy.max_edges_per_node,
                }
            )
            eligible = eligible[: policy.max_edges_per_node]
        for direction, row, neighbor_key, decision in eligible:
            relation_key = str(row["relation_key"])
            if neighbor_key not in nodes and len(nodes) >= policy.max_nodes:
                boundaries.append(
                    {
                        "entity_key": current_key,
                        "reason": "max_nodes",
                        "neighbor_entity_key": neighbor_key,
                        "relation_key": relation_key,
                        "limit": policy.max_nodes,
                    }
                )
                continue
            edge = dict(row)
            for key in (
                "src_kind",
                "src_native_id",
                "dst_kind",
                "dst_native_id",
                "neighbor_lifecycle",
                "neighbor_state",
            ):
                edge.pop(key, None)
            edge.update(
                {
                    "discovered_from": current_key,
                    "traversal_direction": direction,
                    "traversal_action": decision.action,
                    "importance": decision.importance,
                    "policy_rule": decision.rule,
                }
            )
            existing_edge = edges.get(relation_key)
            if existing_edge is None or (
                existing_edge["importance"] == "contextual"
                and decision.importance in {"required", "structural"}
            ):
                edges[relation_key] = edge
            if neighbor_key not in nodes:
                neighbor = connection.execute(
                    "SELECT * FROM entities WHERE entity_key=?", (neighbor_key,)
                ).fetchone()
                if neighbor is None:
                    # The canonical schema forbids this, but preserve an explicit
                    # boundary if a future external graph violates the invariant.
                    boundaries.append(
                        {
                            "entity_key": current_key,
                            "reason": "orphan_relation_destination",
                            "neighbor_entity_key": neighbor_key,
                            "relation_key": relation_key,
                        }
                    )
                    continue
                nodes[neighbor_key] = {
                    **dict(neighbor),
                    "depth": current_depth + 1,
                    "path_importance": _path_importance(
                        str(current["path_importance"]), decision.importance
                    ),
                    "parent_entity_key": current_key,
                    "via_relation_key": relation_key,
                }
            elif (
                nodes[neighbor_key]["path_importance"] == "contextual"
                and _path_importance(
                    str(current["path_importance"]), decision.importance
                )
                == "required"
            ):
                nodes[neighbor_key]["path_importance"] = "required"
            neighbor_state = str(nodes[neighbor_key]["state"])
            neighbor_lifecycle = str(nodes[neighbor_key]["lifecycle"])
            can_expand = (
                decision.action == "expand"
                and str(row["state"]) in EXPANDABLE_STATES
                and neighbor_state in EXPANDABLE_STATES
                and neighbor_lifecycle not in {"tombstone", "localization_only"}
            )
            if can_expand and neighbor_key not in expanded:
                queue.append(neighbor_key)
    return nodes, edges, boundaries


def _placeholders(size: int) -> str:
    return ",".join("?" for _ in range(size))


def _batches(values: list[str], size: int = 400) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def _rows_by_entity(
    connection: sqlite3.Connection,
    table: str,
    entity_column: str,
    order_by: str,
    entity_keys: list[str],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {key: [] for key in entity_keys}
    for batch in _batches(entity_keys):
        sql = (
            f'SELECT * FROM "{table}" WHERE "{entity_column}" '
            f"IN ({_placeholders(len(batch))}) ORDER BY {order_by}"
        )
        for row in connection.execute(sql, batch):
            result[str(row[entity_column])].append(dict(row))
    return result


def _display_name(
    node: dict[str, Any],
    properties: list[dict[str, Any]],
    localizations: list[dict[str, Any]],
) -> str:
    localized_candidates = []
    for row in localizations:
        text = str(row["text_value"]).strip()
        if not text or "\n" in text or len(text) > 120:
            continue
        try:
            evidence = json.loads(str(row["evidence_json"]))
        except (TypeError, ValueError):
            evidence = {}
        column = str(evidence.get("column", ""))
        score = (
            0 if str(row["locale"]).lower() == "en_us" else 2,
            0 if column == "name" else 1,
            len(text),
            text,
        )
        localized_candidates.append((score, text))
    if localized_candidates:
        return min(localized_candidates)[1]
    for row in properties:
        if str(row["property_name"]) != "name":
            continue
        value = row.get("value_text")
        if value not in (None, ""):
            return str(value)
    return str(node["entity_key"])


def _blocker_roots(
    connection: sqlite3.Connection,
    entity_keys: list[str],
) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for batch in _batches(entity_keys):
        rows = connection.execute(
            f"""
            SELECT r.*,i.subject_kind,i.subject_key,i.entity_key,
                   i.state AS impact_state,i.impact_count
            FROM blocker_impacts i
            JOIN blocker_roots r
              ON r.blocker_root_key=i.blocker_root_key
            WHERE i.entity_key IN ({_placeholders(len(batch))})
            ORDER BY r.priority_score DESC,r.blocker_root_key,
                     i.entity_key,i.subject_kind,i.subject_key
            """,
            batch,
        )
        for row in rows:
            key = str(row["blocker_root_key"])
            entry = result.setdefault(
                key,
                {
                    key_name: row[key_name]
                    for key_name in row.keys()
                    if key_name
                    not in {
                        "subject_kind",
                        "subject_key",
                        "entity_key",
                        "impact_state",
                        "impact_count",
                    }
                },
            )
            entry.setdefault("impacts", []).append(
                {
                    "subject_kind": row["subject_kind"],
                    "subject_key": row["subject_key"],
                    "entity_key": row["entity_key"],
                    "state": row["impact_state"],
                    "impact_count": row["impact_count"],
                }
            )
    return [result[key] for key in sorted(result)]


def _wiki_bundle(
    connection: sqlite3.Connection,
    entity_keys: list[str],
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    for batch in _batches(entity_keys):
        entities.extend(
            dict(row)
            for row in connection.execute(
                f"""
                SELECT * FROM wiki_entities
                WHERE entity_key IN ({_placeholders(len(batch))})
                ORDER BY entity_key,wiki_entity_key
                """,
                batch,
            )
        )
    wiki_keys = [str(row["wiki_entity_key"]) for row in entities]
    properties: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for batch in _batches(wiki_keys):
        properties.extend(
            dict(row)
            for row in connection.execute(
                f"""
                SELECT * FROM wiki_properties
                WHERE wiki_entity_key IN ({_placeholders(len(batch))})
                ORDER BY wiki_entity_key,property_name,wiki_property_key
                """,
                batch,
            )
        )
        relations.extend(
            dict(row)
            for row in connection.execute(
                f"""
                SELECT * FROM wiki_relations
                WHERE src_wiki_entity_key IN ({_placeholders(len(batch))})
                ORDER BY src_wiki_entity_key,relation,dst_kind,dst_id,
                         wiki_relation_key
                """,
                batch,
            )
        )
    return {
        "entities": entities,
        "properties": properties,
        "relations": relations,
    }


def _readiness(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    blocker_roots: list[dict[str, Any]],
) -> dict[str, Any]:
    native_issues: list[dict[str, Any]] = []
    downstream_audits: list[dict[str, Any]] = []
    required_entity_keys = {
        str(node["entity_key"])
        for node in nodes
        if node["path_importance"] in {"root", "required"}
    }
    for node in nodes:
        required = node["path_importance"] in {"root", "required"}
        if required and str(node["state"]) in ISSUE_STATES:
            native_issues.append(
                {
                    "kind": "entity_state",
                    "entity_key": node["entity_key"],
                    "state": node["state"],
                }
            )
        for gap in node["gaps"]:
            issue = {
                "kind": "gap",
                "entity_key": node["entity_key"],
                "state": gap["state"],
                "blocker_code": gap["blocker_code"],
                "severity": gap["severity"],
                "reason": gap["reason"],
            }
            if str(gap["blocker_code"]) in DOWNSTREAM_BLOCKER_CODES:
                downstream_audits.append(issue)
            elif required and str(gap["state"]) in ISSUE_STATES:
                native_issues.append(issue)
    for edge in edges:
        if (
            edge["importance"] in {"required", "structural"}
            and str(edge["state"]) in ISSUE_STATES
        ):
            native_issues.append(
                {
                    "kind": "relation_state",
                    "relation_key": edge["relation_key"],
                    "relation": edge["relation"],
                    "state": edge["state"],
                }
            )
    behavior_relations = {
        "produces_item",
        "references_buff",
        "references_effect",
        "references_plot",
        "uses_concrete_effect",
    }
    for node in nodes:
        if (
            node["path_importance"] not in {"root", "required"}
            or node["kind"] != "skill"
        ):
            continue
        behavior_edges = [
            edge
            for edge in edges
            if (
                edge["src_entity_key"] == node["entity_key"]
                and edge["relation"] in behavior_relations
            )
            or (
                edge["dst_entity_key"] == node["entity_key"]
                and edge["relation"] == "references_skill"
                and str(edge["src_entity_key"]).startswith(
                    "skill_effect_application:"
                )
            )
        ]
        if not behavior_edges:
            native_issues.append(
                {
                    "kind": "behavior_closure_not_projected",
                    "entity_key": node["entity_key"],
                    "state": "unknown",
                    "reason": (
                        "The required skill has no projected effect, plot, "
                        "buff, produced-item, or equivalent behavior edge."
                    ),
                }
            )
    for root in blocker_roots:
        issue = {
            "kind": "blocker_root",
            "blocker_root_key": root["blocker_root_key"],
            "root_code": root["root_code"],
            "category": root["category"],
            "state": root["state"],
            "disposition": root["disposition"],
            "recommended_action": root["recommended_action"],
        }
        required_impacts = [
            impact
            for impact in root.get("impacts", [])
            if impact.get("entity_key") in required_entity_keys
        ]
        if not required_impacts:
            continue
        issue["required_impacts"] = required_impacts
        if str(root["category"]) in PRESENTATION_BLOCKER_CATEGORIES:
            issue["audit_scope"] = "presentation"
            downstream_audits.append(issue)
        elif (
            str(root["category"]) == "downstream_server"
            or str(root["disposition"])
            in {"deferred_server", "downstream_out_of_scope"}
        ):
            issue["audit_scope"] = "runtime"
            downstream_audits.append(issue)
        elif str(root["disposition"]) == "actionable":
            native_issues.append(issue)
    hard_boundaries = [
        value
        for value in boundaries
        if value["reason"]
        in {"max_depth_reached", "max_edges_per_node", "max_nodes"}
        and value.get("entity_key") in required_entity_keys
    ]
    if native_issues:
        forensic_state = "blocked"
    elif hard_boundaries:
        forensic_state = "bounded_candidate"
    else:
        forensic_state = "profile_complete"
    reconstruction_state = (
        "blocked_by_native_evidence" if native_issues else "runtime_audit_required"
    )
    return {
        "forensic": {
            "state": forensic_state,
            "native_issue_count": len(native_issues),
            "hard_boundary_count": len(hard_boundaries),
            "issues": native_issues,
        },
        "reconstruction": {
            "state": reconstruction_state,
            "downstream_audit_count": len(downstream_audits),
            "audits": downstream_audits,
            "statement": (
                "This forensic dossier never confirms backend, protocol, "
                "persistence, tests, deployment, or in-client acceptance."
            ),
        },
    }


def _database_identity(database: Path) -> dict[str, Any]:
    resolved = database.resolve()
    manifest = resolved.with_suffix(".manifest.json")
    identity: dict[str, Any] = {
        "database": resolved.as_posix(),
        "database_bytes": resolved.stat().st_size,
        "database_sha256": None,
        "database_manifest": None,
        "database_manifest_sha256": None,
    }
    if not manifest.is_file():
        return identity
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return identity
    declared = payload.get("database")
    if not isinstance(declared, dict):
        return identity
    declared_path = Path(str(declared.get("path", "")))
    try:
        same_database = declared_path.resolve() == resolved
    except OSError:
        same_database = False
    if not same_database or int(declared.get("bytes", -1)) != resolved.stat().st_size:
        return identity
    identity["database_sha256"] = declared.get("sha256")
    identity["database_manifest"] = manifest.as_posix()
    identity["database_manifest_sha256"] = sha256_file(manifest)
    return identity


def build_reconstruction_dossier(
    database: Path,
    kind: str,
    native_id: str,
    *,
    profile: str = "auto",
    policy_path: Path | None = None,
    max_depth: int | None = None,
    max_nodes: int | None = None,
    max_edges_per_node: int | None = None,
    include_properties: bool = True,
) -> dict[str, Any]:
    root_kind = kind.strip().lower()
    root_id = native_id.strip()
    root_key = f"{root_kind}:{root_id}"
    policy = load_closure_policy(
        root_kind,
        profile=profile,
        policy_path=policy_path,
        max_depth=max_depth,
        max_nodes=max_nodes,
        max_edges_per_node=max_edges_per_node,
    )
    connection = open_read_only(database)
    try:
        graph_nodes, graph_edges, boundaries = _walk_graph(
            connection, root_key, policy
        )
        entity_keys = sorted(graph_nodes)
        properties = (
            _rows_by_entity(
                connection,
                "entity_properties",
                "entity_key",
                "entity_key,namespace,property_name,ordinal,property_key",
                entity_keys,
            )
            if include_properties
            else {key: [] for key in entity_keys}
        )
        localizations = _rows_by_entity(
            connection,
            "localizations",
            "entity_key",
            "entity_key,locale,localization_key",
            entity_keys,
        )
        coverage = _rows_by_entity(
            connection,
            "coverage",
            "scope_key",
            "scope_key,authority,dimension,coverage_key",
            entity_keys,
        )
        gaps = _rows_by_entity(
            connection,
            "gaps",
            "entity_key",
            "entity_key,severity DESC,dimension,gap_key",
            entity_keys,
        )
        consumers = _rows_by_entity(
            connection,
            "consumers",
            "scope_key",
            "scope_key,consumer_kind,name,consumer_key",
            entity_keys,
        )
        nodes = []
        for key in sorted(
            entity_keys,
            key=lambda value: (
                int(graph_nodes[value]["depth"]),
                str(graph_nodes[value]["kind"]),
                str(graph_nodes[value]["native_id"]),
                value,
            ),
        ):
            node = dict(graph_nodes[key])
            node["display_name"] = _display_name(
                node, properties[key], localizations[key]
            )
            node["properties"] = properties[key]
            node["localizations"] = localizations[key]
            node["coverage"] = coverage[key]
            node["gaps"] = gaps[key]
            node["consumers"] = consumers[key]
            nodes.append(node)
        edges = [
            graph_edges[key]
            for key in sorted(
                graph_edges,
                key=lambda value: (
                    str(graph_edges[value]["src_entity_key"]),
                    str(graph_edges[value]["relation"]),
                    str(graph_edges[value]["dst_entity_key"]),
                    int(graph_edges[value]["ordinal"]),
                    value,
                ),
            )
        ]
        blockers = _blocker_roots(connection, entity_keys)
        wiki = _wiki_bundle(connection, entity_keys)
        metadata = {
            str(row["key"]): str(row["value"])
            for row in connection.execute("SELECT key,value FROM metadata ORDER BY key")
        }
        readiness = _readiness(nodes, edges, boundaries, blockers)
        summary = {
            "nodes": len(nodes),
            "edges": len(edges),
            "max_depth_reached": max(int(node["depth"]) for node in nodes),
            "node_states": dict(
                sorted(Counter(str(node["state"]) for node in nodes).items())
            ),
            "edge_states": dict(
                sorted(Counter(str(edge["state"]) for edge in edges).items())
            ),
            "node_kinds": dict(
                sorted(Counter(str(node["kind"]) for node in nodes).items())
            ),
            "required_nodes": sum(
                node["path_importance"] in {"root", "required"} for node in nodes
            ),
            "required_edges": sum(
                edge["importance"] in {"required", "structural"} for edge in edges
            ),
            "boundaries": len(boundaries),
            "blocker_roots": len(blockers),
        }
        return {
            "format": DOSSIER_FORMAT,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "authority": "client_forensics_only",
            "server_mutation": "forbidden",
            "root": {
                "entity_key": root_key,
                "kind": root_kind,
                "native_id": root_id,
            },
            "profile": {
                "name": policy.name,
                "policy_path": policy.source_path.as_posix(),
                "policy_sha256": policy.source_sha256,
                "max_depth": policy.max_depth,
                "max_nodes": policy.max_nodes,
                "max_edges_per_node": policy.max_edges_per_node,
                "include_properties": include_properties,
            },
            "source": {**_database_identity(database), "metadata": metadata},
            "summary": summary,
            "readiness": readiness,
            "graph": {"nodes": nodes, "edges": edges},
            "boundaries": sorted(
                boundaries,
                key=lambda value: canonical_json(value),
            ),
            "blocker_roots": blockers,
            "wiki": wiki,
        }
    finally:
        connection.close()


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")
    return normalized or "entity"


def default_dossier_paths(
    output_dir: Path,
    kind: str,
    native_id: str,
) -> tuple[Path, Path]:
    stem = f"{_safe_slug(kind.lower())}-{_safe_slug(native_id)}"
    root = output_dir / "dossiers"
    return root / f"{stem}.json", root / f"{stem}.html"


DOSSIER_HTML = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 dossier — {title}</title>
<style>
:root{{--bg:#0d1117;--panel:#161b22;--line:#30363d;--text:#e6edf3;
--muted:#8b949e;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--accent:#58a6ff}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);
font:13px/1.4 system-ui,sans-serif;overflow:hidden}}header{{height:82px;padding:12px 18px;
border-bottom:1px solid var(--line);background:#010409}}h1{{font-size:20px;margin:0 0 5px}}
.muted{{color:var(--muted)}}.layout{{height:calc(100vh - 82px);display:grid;
grid-template-columns:300px 1fr 360px}}aside{{background:var(--panel);overflow:auto;
border-right:1px solid var(--line);padding:12px}}aside.right{{border-right:0;
border-left:1px solid var(--line)}}main{{position:relative;overflow:hidden}}
input,select,button{{background:#0d1117;color:var(--text);border:1px solid var(--line);
border-radius:6px;padding:7px}}input{{width:100%;margin-bottom:8px}}select{{width:100%;
margin-bottom:8px}}button{{cursor:pointer}}.stats{{display:grid;grid-template-columns:1fr 1fr;
gap:6px;margin:10px 0}}.stat{{background:#21262d;border-radius:6px;padding:7px}}
.badge{{display:inline-block;border:1px solid var(--line);border-radius:999px;
padding:2px 6px;margin:2px;font-size:11px}}.confirmed,.profile_complete{{color:var(--ok)}}
.unknown,.blocked,.bounded_candidate,.runtime_audit_required{{color:var(--warn)}}
.missing,.blocked_by_native_evidence{{color:var(--bad)}}svg{{width:100%;height:100%;
background:radial-gradient(circle at center,#161b22,#0d1117)}}.edge{{stroke:#48525e;
stroke-width:1.2;opacity:.7}}.edge.required{{stroke:#d29922;stroke-width:1.8}}
.node rect{{fill:#21262d;stroke:#48525e;stroke-width:1.3;rx:7}}
.node.required rect{{stroke:#d29922;stroke-width:2}}.node.root rect{{stroke:#58a6ff;
stroke-width:3}}.node.issue rect{{stroke:#f85149}}.node text{{fill:var(--text);
font-size:11px;pointer-events:none}}.node .sub{{fill:var(--muted);font-size:9px}}
.node{{cursor:pointer}}pre{{white-space:pre-wrap;word-break:break-word;background:#0d1117;
border:1px solid var(--line);border-radius:6px;padding:8px;max-height:360px;overflow:auto}}
.list{{display:flex;flex-direction:column;gap:5px}}.list button{{text-align:left}}
.controls{{position:absolute;right:10px;top:10px;display:flex;gap:5px;z-index:2}}
@media(max-width:1000px){{.layout{{grid-template-columns:240px 1fr}}
aside.right{{display:none}}}}
</style></head><body>
<header><h1>{title}</h1><div class="muted" id="subtitle"></div></header>
<div class="layout"><aside>
<input id="search" placeholder="Buscar nodo, ID o nombre">
<select id="kind"><option value="">Todos los tipos</option></select>
<select id="state"><option value="">Todos los estados</option></select>
<div class="stats" id="stats"></div>
<h3>Readiness</h3><div id="readiness"></div>
<h3>Nodos</h3><div class="list" id="nodeList"></div>
</aside><main>
<div class="controls"><button id="zoomIn">+</button><button id="zoomOut">−</button>
<button id="reset">Ajustar</button></div><svg id="graph"></svg>
</main><aside class="right"><div id="detail" class="muted">
Selecciona un nodo para inspeccionar su evidencia.</div></aside></div>
<script>
const D={payload};
const $=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({{
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const nodes=D.graph.nodes,edges=D.graph.edges,byKey=new Map(nodes.map(n=>[n.entity_key,n]));
$('subtitle').textContent=`${{D.source.metadata.client_build||''}} · ${{D.profile.name}} · evidencia forense`;
const statKeys=['nodes','edges','max_depth_reached','required_nodes','required_edges',
'boundaries','blocker_roots'];
$('stats').innerHTML=statKeys.map(k=>[k,D.summary[k]]).map(([k,v])=>
`<div class="stat"><b>${{typeof v==='number'?v.toLocaleString('es-CL'):esc(v)}}</b><br>
<span class="muted">${{esc(k)}}</span></div>`).join('');
const fr=D.readiness.forensic,re=D.readiness.reconstruction;
$('readiness').innerHTML=`<p class="${{esc(fr.state)}}"><b>Forense:</b> ${{esc(fr.state)}}</p>
<p class="${{esc(re.state)}}"><b>Reconstrucción:</b> ${{esc(re.state)}}</p>
<p class="muted">${{esc(re.statement)}}</p>`;
for(const [id,values] of [['kind',nodes.map(n=>n.kind)],['state',nodes.map(n=>n.state)]])
 for(const value of [...new Set(values)].sort()){{const o=document.createElement('option');
 o.value=value;o.textContent=value;$(id).append(o)}}
let scale=1,offsetX=20,offsetY=20,drag=null;
function filtered(){{
 const q=$('search').value.trim().toLowerCase(),kind=$('kind').value,state=$('state').value;
 return nodes.filter(n=>(!q||n.entity_key.toLowerCase().includes(q)||
 n.display_name.toLowerCase().includes(q))&&(!kind||n.kind===kind)&&(!state||n.state===state));
}}
function layout(values){{
 const groups=new Map();for(const n of values){{if(!groups.has(n.depth))groups.set(n.depth,[]);
 groups.get(n.depth).push(n)}}const pos=new Map();let maxY=0;
 for(const [depth,group] of [...groups.entries()].sort((a,b)=>a[0]-b[0])){{
  group.sort((a,b)=>a.kind.localeCompare(b.kind)||a.native_id.localeCompare(b.native_id));
  group.forEach((n,i)=>pos.set(n.entity_key,{{x:40+depth*280,y:35+i*82}}));
  maxY=Math.max(maxY,35+group.length*82)
 }}return {{pos,width:Math.max(700,100+groups.size*280),height:Math.max(500,maxY+40)}};
}}
function render(){{
 const values=filtered(),keys=new Set(values.map(n=>n.entity_key)),L=layout(values),svg=$('graph');
 svg.setAttribute('viewBox',`${{-offsetX/scale}} ${{-offsetY/scale}} ${{svg.clientWidth/scale}} ${{svg.clientHeight/scale}}`);
 const edgeHtml=edges.filter(e=>keys.has(e.src_entity_key)&&keys.has(e.dst_entity_key))
 .map(e=>{{const a=L.pos.get(e.src_entity_key),b=L.pos.get(e.dst_entity_key);
 return `<line class="edge ${{esc(e.importance)}}" x1="${{a.x+190}}" y1="${{a.y+24}}"
 x2="${{b.x}}" y2="${{b.y+24}}"><title>${{esc(e.relation)}} · ${{esc(e.state)}}</title></line>`}}).join('');
 const nodeHtml=values.map(n=>{{const p=L.pos.get(n.entity_key),issue=['unknown','missing','blocked'].includes(n.state);
 const cls=`node ${{n.path_importance}} ${{issue?'issue':''}}`;
 return `<g class="${{cls}}" data-key="${{esc(n.entity_key)}}" transform="translate(${{p.x}},${{p.y}})">
 <rect width="190" height="49"></rect><text x="9" y="18">${{esc(n.display_name.slice(0,28))}}</text>
 <text class="sub" x="9" y="36">${{esc(n.entity_key.slice(0,32))}} · d${{n.depth}}</text></g>`}}).join('');
 svg.innerHTML=`<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
 markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"
 fill="#48525e"/></marker></defs><g>${{edgeHtml.replaceAll('<line ','<line marker-end="url(#arrow)" ')}}${{nodeHtml}}</g>`;
 svg.querySelectorAll('.node').forEach(el=>el.onclick=()=>detail(byKey.get(el.dataset.key)));
 $('nodeList').innerHTML=values.slice(0,250).map(n=>`<button data-key="${{esc(n.entity_key)}}">
${{esc(n.display_name)}}<br><span class="muted">${{esc(n.entity_key)}}</span></button>`).join('');
 $('nodeList').querySelectorAll('button').forEach(el=>el.onclick=()=>detail(byKey.get(el.dataset.key)));
}}
function detail(n){{
 $('detail').innerHTML=`<h2>${{esc(n.display_name)}}</h2><p><span class="badge">${{esc(n.kind)}}</span>
 <span class="badge ${{esc(n.state)}}">${{esc(n.state)}}</span>
 <span class="badge">${{esc(n.lifecycle)}}</span></p>
 <dl><dt>Clave</dt><dd>${{esc(n.entity_key)}}</dd><dt>Profundidad</dt><dd>${{n.depth}}</dd>
 <dt>Importancia</dt><dd>${{esc(n.path_importance)}}</dd><dt>Autoridad</dt>
 <dd>${{esc(n.authority)}}</dd></dl><h3>Localizaciones</h3>
 <pre>${{esc(JSON.stringify(n.localizations,null,2))}}</pre><h3>Propiedades</h3>
 <pre>${{esc(JSON.stringify(n.properties,null,2))}}</pre><h3>Gaps</h3>
 <pre>${{esc(JSON.stringify(n.gaps,null,2))}}</pre><h3>Cobertura</h3>
 <pre>${{esc(JSON.stringify(n.coverage,null,2))}}</pre>`;
}}
for(const id of ['search','kind','state'])$(id).addEventListener('input',render);
$('zoomIn').onclick=()=>{{scale*=1.25;render()}};$('zoomOut').onclick=()=>{{scale/=1.25;render()}};
$('reset').onclick=()=>{{scale=1;offsetX=20;offsetY=20;render()}};
const svg=$('graph');svg.addEventListener('mousedown',e=>drag={{x:e.clientX,y:e.clientY,ox:offsetX,oy:offsetY}});
window.addEventListener('mouseup',()=>drag=null);window.addEventListener('mousemove',e=>{{if(!drag)return;
offsetX=drag.ox+(e.clientX-drag.x);offsetY=drag.oy+(e.clientY-drag.y);render()}});
svg.addEventListener('wheel',e=>{{e.preventDefault();scale*=e.deltaY<0?1.1:.9;render()}},{{passive:false}});
render();
</script></body></html>"""


def render_dossier_html(dossier: dict[str, Any]) -> str:
    root_key = str(dossier["root"]["entity_key"])
    root = next(
        node for node in dossier["graph"]["nodes"] if node["entity_key"] == root_key
    )
    title = f"{root_key} — {root['display_name']}"
    payload = canonical_json(dossier).replace("</", "<\\/")
    return DOSSIER_HTML.format(title=title, payload=payload)


def write_reconstruction_dossier(
    dossier: dict[str, Any],
    json_path: Path,
    html_path: Path,
) -> dict[str, Any]:
    json_text = canonical_json(dossier, pretty=True)
    html_text = render_dossier_html(dossier)
    atomic_text(json_path, json_text)
    atomic_text(html_path, html_text)
    return {
        "root": dossier["root"],
        "profile": dossier["profile"],
        "summary": dossier["summary"],
        "readiness": dossier["readiness"],
        "json": {
            "path": json_path.resolve().as_posix(),
            "bytes": json_path.stat().st_size,
            "sha256": sha256_file(json_path),
        },
        "html": {
            "path": html_path.resolve().as_posix(),
            "bytes": html_path.stat().st_size,
            "sha256": sha256_file(html_path),
        },
    }
