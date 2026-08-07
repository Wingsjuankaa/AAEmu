from __future__ import annotations

import bisect
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from . import TOOL_NAME, TOOL_VERSION
from .config import ForensicsConfig
from .native_code import NativeCodeConfig
from .native_semantic_schema import (
    CLOSURE_STATES,
    FUNCTION_CATEGORIES,
    NATIVE_SEMANTIC_SCHEMA_VERSION,
    OPAQUE_CLASSIFICATIONS,
    create_native_semantic_tables,
)
from .schema import open_read_only
from .util import atomic_text, canonical_json, sha256_file, sha256_text, stable_key


NATIVE_SEMANTIC_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "native-semantic-domains.json"
)
NATIVE_SEMANTIC_FORMAT = "AA8_NATIVE_SEMANTIC_INDEX_V1"
NATIVE_SEMANTIC_REVIEW_FORMAT = "AA8_NATIVE_SEMANTIC_REVIEW_V1"
_LOCATOR = re.compile(r"\bFUN_([0-9a-fA-F]{6,16})\b")
_WS = re.compile(r"\s+")
_CALL_REGISTER = re.compile(
    r"\b(?:r(?:ax|bx|cx|dx|si|di|sp|bp|8|9|10|11|12|13|14|15)|"
    r"e(?:ax|bx|cx|dx|si|di|sp|bp)|[abcd]x|[sd]i|[sb]p)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NativeSemanticConfig:
    path: Path
    client_build: str
    database: Path
    manifest: Path
    dossier_root: Path
    required_stage_15_sha256: str
    closure: dict[str, int]
    impact: dict[str, Any]
    uncertainty: dict[str, int]
    domains: tuple[dict[str, Any], ...]
    config_sha256: str
    review_overrides: Path | None = None


def load_native_semantic_config(path: Path | None = None) -> NativeSemanticConfig:
    config_path = (path or NATIVE_SEMANTIC_CONFIG).resolve()
    raw_text = config_path.read_text(encoding="utf-8")
    raw = json.loads(raw_text)
    if raw.get("format") != NATIVE_SEMANTIC_FORMAT:
        raise ValueError(f"Unsupported native semantic format: {raw.get('format')}")

    def resolve(value: str) -> Path:
        candidate = Path(value)
        return (candidate if candidate.is_absolute() else config_path.parent / candidate).resolve()

    review_value = raw.get("review_overrides")
    return NativeSemanticConfig(
        path=config_path,
        client_build=str(raw["client_build"]),
        database=resolve(raw["database"]),
        manifest=resolve(raw["manifest"]),
        dossier_root=resolve(raw["dossier_root"]),
        required_stage_15_sha256=str(raw["required_stage_15_sha256"]).upper(),
        closure={key: int(value) for key, value in raw["closure"].items()},
        impact=dict(raw["impact"]),
        uncertainty={key: int(value) for key, value in raw["uncertainty"].items()},
        domains=tuple(dict(value) for value in raw["domains"]),
        config_sha256=sha256_text(raw_text),
        review_overrides=resolve(str(review_value)) if review_value else None,
    )


def _load_semantic_reviews(
    semantic: NativeSemanticConfig,
    stage: sqlite3.Connection,
    roots: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], str | None]:
    path = semantic.review_overrides
    if path is None:
        return {}, None
    raw_text = path.read_text(encoding="utf-8")
    raw = json.loads(raw_text)
    if raw.get("format") != NATIVE_SEMANTIC_REVIEW_FORMAT:
        raise ValueError(f"Unsupported native semantic review format: {raw.get('format')}")
    if str(raw.get("client_build")) != semantic.client_build:
        raise ValueError("Native semantic review belongs to a different client build")
    if str(raw.get("required_stage_15_sha256", "")).upper() != semantic.required_stage_15_sha256:
        raise ValueError("Native semantic review belongs to a different Stage 15")

    reviews: dict[str, dict[str, Any]] = {}
    review_keys: set[str] = set()
    reviewed_regions: set[str] = set()
    terminal_states = CLOSURE_STATES - {"pending_review"}
    evidence_states = {
        "confirmed", "corroborated", "candidate", "ambiguous", "opaque",
        "timeout", "failed", "unsupported", "not_scheduled",
    }
    for value in raw.get("reviews", []):
        review = dict(value)
        review_key = str(review.get("review_key", "")).strip()
        root_key = str(review.get("root_key", "")).strip()
        status = str(review.get("closure_status", "")).strip()
        state = str(review.get("state", "")).strip()
        dossier_name = str(review.get("dossier_name", "")).strip()
        if not review_key or review_key in review_keys:
            raise ValueError(f"Native semantic review key is absent or duplicated: {review_key!r}")
        if root_key not in roots:
            raise ValueError(f"Native semantic review root is absent: {root_key}")
        if root_key in reviews:
            raise ValueError(f"Multiple native semantic reviews target one root: {root_key}")
        if status not in terminal_states:
            raise ValueError(f"Native semantic review is not terminal: {review_key}={status}")
        if state not in evidence_states:
            raise ValueError(f"Invalid native semantic review state: {review_key}={state}")
        if not dossier_name or Path(dossier_name).name != dossier_name or not dossier_name.endswith(".json"):
            raise ValueError(f"Unsafe native semantic dossier name: {dossier_name!r}")
        if not str(review.get("summary", "")).strip():
            raise ValueError(f"Native semantic review has no summary: {review_key}")

        listed_functions: set[str] = set()
        for function in review.get("functions", []):
            function_key = str(function.get("function_key", ""))
            if not function_key or function_key in listed_functions:
                raise ValueError(f"Review function is absent or duplicated: {review_key}:{function_key}")
            row = stage.execute(
                """
                SELECT f.function_key,b.module_name,b.architecture,f.entry_rva,f.byte_sha256
                FROM code_functions f JOIN code_binaries b USING(binary_key)
                WHERE f.function_key=?
                """,
                (function_key,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Review function is absent from Stage 15: {function_key}")
            expected = (
                function_key,
                str(function.get("module_name", "")),
                str(function.get("architecture", "")),
                int(function.get("entry_rva", -1)),
                str(function.get("byte_sha256", "")).upper(),
            )
            actual = (str(row[0]), str(row[1]), str(row[2]), int(row[3]), str(row[4]).upper())
            if actual != expected:
                raise ValueError(
                    "Review function identity mismatch: "
                    f"{function_key} expected={expected[1:]} actual={actual[1:]}"
                )
            if str(function.get("state", "")) not in evidence_states:
                raise ValueError(f"Review function has invalid state: {function_key}")
            if not str(function.get("role", "")).strip():
                raise ValueError(f"Review function has no role: {function_key}")
            listed_functions.add(function_key)
        if not listed_functions:
            raise ValueError(f"Native semantic review has no functions: {review_key}")

        consumer_resolution = review.get("consumer_resolution")
        if consumer_resolution is not None:
            resolution = dict(consumer_resolution)
            consumer_key = str(resolution.get("consumer_key", "")).strip()
            accepted = sorted({str(item) for item in resolution.get("function_keys", [])})
            rejected = sorted({str(item) for item in resolution.get("rejected_function_keys", [])})
            if roots[root_key].get("root_kind") != "consumer" or root_key != f"consumer:{consumer_key}":
                raise ValueError(
                    f"Review consumer resolution targets a different root: {review_key}:{consumer_key}"
                )
            if not accepted:
                raise ValueError(f"Review consumer resolution has no accepted functions: {review_key}")
            missing = sorted((set(accepted) | set(rejected)) - listed_functions)
            if missing:
                raise ValueError(
                    f"Review consumer resolution references unlisted functions: {review_key}:{missing}"
                )
            overlap = sorted(set(accepted) & set(rejected))
            if overlap:
                raise ValueError(
                    f"Review consumer resolution accepts and rejects the same functions: {review_key}:{overlap}"
                )
            if str(resolution.get("state", "")) not in evidence_states:
                raise ValueError(f"Review consumer resolution has invalid state: {review_key}")
            if not str(resolution.get("classification", "")).strip():
                raise ValueError(f"Review consumer resolution has no classification: {review_key}")
            if not str(resolution.get("method", "")).strip() or not resolution.get("evidence"):
                raise ValueError(f"Review consumer resolution lacks method or evidence: {review_key}")

        for region in review.get("regions", []):
            region_key = str(region.get("region_key", ""))
            if not region_key or region_key in reviewed_regions:
                raise ValueError(
                    f"Review region is absent or duplicated: {review_key}:{region_key}"
                )
            row = stage.execute(
                """
                SELECT r.region_key,b.module_name,b.architecture,b.sha256,
                       r.start_rva,r.end_rva,r.region_kind
                FROM code_regions r JOIN code_binaries b USING(binary_key)
                WHERE r.region_key=?
                """,
                (region_key,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Review region is absent from Stage 15: {region_key}")
            expected = (
                region_key,
                str(region.get("module_name", "")),
                str(region.get("architecture", "")),
                str(region.get("binary_sha256", "")).upper(),
                int(region.get("start_rva", -1)),
                int(region.get("end_rva", -1)),
                "opaque",
            )
            actual = (
                str(row[0]), str(row[1]), str(row[2]), str(row[3]).upper(),
                int(row[4]), int(row[5]), str(row[6]),
            )
            if actual != expected:
                raise ValueError(
                    "Review region identity mismatch: "
                    f"{region_key} expected={expected[1:]} actual={actual[1:]}"
                )
            classification = str(region.get("classification", ""))
            if classification not in OPAQUE_CLASSIFICATIONS:
                raise ValueError(
                    f"Review region has invalid classification: {region_key}={classification}"
                )
            if str(region.get("state", "")) not in evidence_states:
                raise ValueError(f"Review region has invalid state: {region_key}")
            if not str(region.get("role", "")).strip():
                raise ValueError(f"Review region has no role: {region_key}")
            evidence = [str(item) for item in region.get("evidence", [])]
            missing = sorted(set(evidence) - listed_functions)
            if not evidence or missing:
                raise ValueError(
                    f"Review region lacks valid function evidence: {region_key}:{missing}"
                )
            reviewed_regions.add(region_key)

        findings = list(review.get("findings", []))
        if not findings:
            raise ValueError(f"Native semantic review has no findings: {review_key}")
        finding_keys: set[str] = set()
        for finding in findings:
            finding_key = str(finding.get("finding_key", ""))
            evidence = [str(item) for item in finding.get("evidence", [])]
            if not finding_key or finding_key in finding_keys:
                raise ValueError(f"Review finding is absent or duplicated: {review_key}:{finding_key}")
            if str(finding.get("state", "")) not in evidence_states:
                raise ValueError(f"Review finding has invalid state: {review_key}:{finding_key}")
            if not str(finding.get("conclusion", "")).strip() or not evidence:
                raise ValueError(f"Review finding lacks conclusion or evidence: {review_key}:{finding_key}")
            missing = sorted(set(evidence) - listed_functions)
            if missing:
                raise ValueError(f"Review finding references unlisted functions: {missing}")
            finding_keys.add(finding_key)
        blocker = dict(review.get("remaining_blocker", {}))
        if not blocker.get("kind") or not blocker.get("description"):
            raise ValueError(f"Native semantic review has no explicit remaining blocker: {review_key}")

        review_keys.add(review_key)
        reviews[root_key] = review
    return reviews, sha256_text(raw_text).upper()


def _apply_review_consumer_resolutions(
    config: NativeSemanticConfig,
    roots: dict[str, dict[str, Any]],
    seeds: dict[str, dict[str, dict[str, Any]]],
    consumer_rows: list[tuple[Any, ...]],
    reviews: dict[str, dict[str, Any]],
) -> list[tuple[Any, ...]]:
    """Replace ambiguous locator seeds only when an exact reviewed mapping exists."""
    by_consumer = {str(row[0]): tuple(row) for row in consumer_rows}
    for root_key, review in sorted(reviews.items()):
        value = review.get("consumer_resolution")
        if value is None:
            continue
        resolution = dict(value)
        consumer_key = str(resolution["consumer_key"])
        accepted = sorted({str(item) for item in resolution["function_keys"]})
        rejected = sorted({str(item) for item in resolution.get("rejected_function_keys", [])})
        state = str(resolution["state"])
        classification = str(resolution["classification"])
        method = str(resolution["method"])
        original = by_consumer[consumer_key]

        seeds[root_key] = {}
        for function_key in accepted:
            _add_seed(
                seeds,
                root_key,
                function_key,
                relation="reviewed_consumer_resolution",
                state=state,
                impact=int(config.impact["consumer"]),
                evidence={
                    "review_key": str(review["review_key"]),
                    "method": method,
                    "rejected_function_keys": rejected,
                },
            )
        evidence = {
            "root_key": root_key,
            "method": method,
            "review_key": str(review["review_key"]),
            "original_classification": str(original[5]),
            "original_function_keys": json.loads(str(original[7])),
            "rejected_function_keys": rejected,
            "evidence": list(resolution["evidence"]),
        }
        by_consumer[consumer_key] = (
            original[0], original[1], original[2], original[3], len(accepted),
            classification, state, canonical_json(accepted), canonical_json(evidence),
        )
        root = roots[root_key]
        root["state"] = state
        root_evidence = json.loads(str(root["evidence_json"]))
        root_evidence["reviewed_resolution"] = evidence
        root["evidence_json"] = canonical_json(root_evidence)
    return [by_consumer[key] for key in sorted(by_consumer)]


def _write_review_dossiers(
    semantic: NativeSemanticConfig,
    stage: sqlite3.Connection,
    reviews: dict[str, dict[str, Any]],
    *,
    review_sha256: str | None,
    index_sha256: str,
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    semantic.dossier_root.mkdir(parents=True, exist_ok=True)
    for root_key, review in sorted(reviews.items()):
        snapshots = []
        for function in review["functions"]:
            function_key = str(function["function_key"])
            names = [
                {"name": str(row[0]), "source": str(row[1]), "state": str(row[2])}
                for row in stage.execute(
                    "SELECT name,source_kind,state FROM code_names WHERE function_key=? ORDER BY primary_name DESC,name",
                    (function_key,),
                )
            ]
            strings = [
                {"value": str(row[0]), "reference_rva": int(row[1]), "state": str(row[2])}
                for row in stage.execute(
                    """
                    SELECT s.value,fs.reference_rva,fs.state
                    FROM code_function_strings fs JOIN code_strings s USING(string_key)
                    WHERE fs.function_key=? ORDER BY fs.reference_rva,s.string_key
                    """,
                    (function_key,),
                )
            ]
            decompilers = [
                {
                    "engine": str(row[0]), "status": str(row[1]),
                    "prototype": row[2], "pseudocode_sha256": row[3],
                }
                for row in stage.execute(
                    """
                    SELECT engine_id,status,prototype,pseudocode_sha256
                    FROM code_decompilations WHERE function_key=?
                    ORDER BY engine_id,run_key
                    """,
                    (function_key,),
                )
            ]
            snapshots.append({
                **dict(function),
                "names": names,
                "strings": strings,
                "decompilers": decompilers,
                "calls_out": int(stage.execute(
                    "SELECT COUNT(*) FROM code_calls WHERE caller_function_key=?", (function_key,)
                ).fetchone()[0]),
                "calls_in": int(stage.execute(
                    "SELECT COUNT(*) FROM code_calls WHERE callee_function_key=?", (function_key,)
                ).fetchone()[0]),
            })
        region_snapshots = []
        for region in review.get("regions", []):
            row = stage.execute(
                """
                SELECT r.region_key,b.binary_key,b.module_name,b.architecture,b.sha256,
                       r.start_rva,r.end_rva,r.region_kind,r.state,r.evidence_json
                FROM code_regions r JOIN code_binaries b USING(binary_key)
                WHERE r.region_key=?
                """,
                (str(region["region_key"]),),
            ).fetchone()
            region_snapshots.append(dict(row))
        dossier = {
            "format": "AA8_NATIVE_SEMANTIC_REVIEW_DOSSIER_V1",
            "client_build": semantic.client_build,
            "source_index_sha256": index_sha256,
            "stage_15_sha256": semantic.required_stage_15_sha256,
            "review_overrides_sha256": review_sha256,
            "root_key": root_key,
            "review": review,
            "function_snapshots": snapshots,
            "region_snapshots": region_snapshots,
            "authority_note": (
                "The review records corroborated static evidence. It does not promote "
                "decompiler pseudocode or inferred names to native authority."
            ),
        }
        output = semantic.dossier_root / str(review["dossier_name"])
        atomic_text(output, canonical_json(dossier, pretty=True))
        outputs.append({
            "review_key": str(review["review_key"]),
            "root_key": root_key,
            "closure_status": str(review["closure_status"]),
            "path": output.as_posix(),
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output).upper(),
        })
    return outputs


def normalize_sql(value: str | None) -> str:
    if not value:
        return ""
    normalized = _WS.sub(" ", value.strip()).rstrip(";").strip()
    return normalized.casefold()


def locator_to_rva(locator: str | None, image_base: int) -> int | None:
    if not locator:
        return None
    match = _LOCATOR.search(locator)
    if not match:
        return None
    value = int(match.group(1), 16)
    return value - image_base if value >= image_base else value


def locator_rvas(locator: str | None, image_base: int) -> list[int]:
    if not locator:
        return []
    values = []
    for match in _LOCATOR.finditer(locator):
        value = int(match.group(1), 16)
        values.append(value - image_base if value >= image_base else value)
    return sorted(set(values))


def locator_has_explicit_architecture_pair(locator: str | None) -> bool:
    text = (locator or "").casefold()
    return "x86" in text and "x64" in text


def _domain_for_text(config: NativeSemanticConfig, *values: str | None) -> tuple[str, int]:
    text = " ".join(value or "" for value in values).casefold()
    matches: list[tuple[int, int, str]] = []
    for index, domain in enumerate(config.domains):
        keywords = tuple(str(value).casefold() for value in domain.get("keywords", ()))
        if any(keyword in text for keyword in keywords):
            matches.append((int(domain["priority"]), -index, str(domain["id"])))
    if not matches:
        return "unclassified", 0
    priority, _, domain_id = max(matches)
    return domain_id, priority


def _tier(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    if score > 0:
        return "context"
    return "low"


def _chunks(values: Iterable[str], size: int = 700) -> Iterable[list[str]]:
    chunk: list[str] = []
    for value in values:
        chunk.append(value)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _manifest_database_sha(path: Path, *keys: str) -> str | None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    value: Any = raw
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return str(value).upper() if value else None


def _verify_inputs(
    semantic: NativeSemanticConfig,
    native: NativeCodeConfig,
    forensics: ForensicsConfig,
) -> dict[str, str]:
    if semantic.client_build != native.client_build or semantic.client_build != forensics.client_build:
        raise RuntimeError("Native semantic inputs belong to different client builds")
    stage_sha = sha256_file(native.stage_database).upper()
    if stage_sha != semantic.required_stage_15_sha256:
        raise RuntimeError(
            "Stage 15 SHA mismatch: "
            f"expected={semantic.required_stage_15_sha256} actual={stage_sha}"
        )
    manifest_sha = _manifest_database_sha(native.stage_manifest, "database", "sha256")
    if manifest_sha != stage_sha:
        raise RuntimeError("Stage 15 database does not match its manifest")
    consolidated_sha = sha256_file(forensics.consolidated).upper()
    consolidated_manifest_sha = _manifest_database_sha(
        forensics.manifest, "consolidated", "database", "sha256"
    )
    if consolidated_manifest_sha != consolidated_sha:
        raise RuntimeError("Consolidated forensics database does not match its manifest")
    main = open_read_only(forensics.consolidated)
    try:
        projection = hashlib.sha256()
        for table in ("consumers", "query_specs", "blocker_roots"):
            columns = [
                str(row[1])
                for row in main.execute(f"PRAGMA table_info({table})")
            ]
            projection.update((table + "\n").encode("utf-8"))
            order = columns[0]
            for row in main.execute(f'SELECT * FROM "{table}" ORDER BY "{order}"'):
                projection.update(
                    canonical_json(dict(zip(columns, tuple(row)))).encode("utf-8")
                )
                projection.update(b"\n")
        source_projection_sha = projection.hexdigest().upper()
    finally:
        main.close()
    return {
        "stage_15_sha256": stage_sha,
        "stage_15_manifest_sha256": sha256_file(native.stage_manifest).upper(),
        "consolidated_source_projection_sha256": source_projection_sha,
        "consolidated_source_projection_version": "1",
    }


def _create_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA page_size=4096")
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA foreign_keys=ON")
    create_native_semantic_tables(connection)
    return connection


def _add_root(
    roots: dict[str, dict[str, Any]],
    *,
    root_key: str,
    root_kind: str,
    scope_key: str,
    name: str,
    domain: str,
    priority: int,
    state: str,
    evidence: dict[str, Any],
) -> None:
    candidate = {
        "root_key": root_key,
        "root_kind": root_kind,
        "scope_key": scope_key,
        "name": name,
        "domain": domain,
        "backend_priority": priority,
        "state": state,
        "evidence_json": canonical_json(evidence),
    }
    current = roots.get(root_key)
    if current is None or (priority, state, name) > (
        current["backend_priority"], current["state"], current["name"]
    ):
        roots[root_key] = candidate


def _add_seed(
    seeds: dict[str, dict[str, dict[str, Any]]],
    root_key: str,
    function_key: str,
    *,
    relation: str,
    state: str,
    impact: int,
    evidence: dict[str, Any],
) -> None:
    candidate = {
        "relation": relation,
        "state": state,
        "impact": impact,
        "evidence": evidence,
    }
    current = seeds[root_key].get(function_key)
    order = {"confirmed": 4, "corroborated": 3, "candidate": 2, "ambiguous": 1}
    if current is None or (impact, order.get(state, 0), relation) > (
        current["impact"], order.get(current["state"], 0), current["relation"]
    ):
        seeds[root_key][function_key] = candidate


def _load_function_catalog(stage: sqlite3.Connection) -> tuple[
    dict[str, tuple[str, str, str, str]],
    dict[tuple[str, int], str],
    dict[str, tuple[str, str, int]],
]:
    binaries: dict[str, tuple[str, str, int]] = {}
    for row in stage.execute(
        "SELECT binary_key,module_name,architecture,image_base FROM code_binaries ORDER BY binary_key"
    ):
        binaries[str(row[0])] = (str(row[1]), str(row[2]), int(row[3]))
    functions: dict[str, tuple[str, str, str, str]] = {}
    rva_index: dict[tuple[str, int], str] = {}
    for row in stage.execute(
        """
        SELECT f.function_key,f.binary_key,f.entry_rva,b.module_name,b.architecture,b.classification
        FROM code_functions f JOIN code_binaries b USING(binary_key)
        ORDER BY f.function_key
        """
    ):
        key = str(row[0])
        binary_key = str(row[1])
        functions[key] = (binary_key, str(row[3]), str(row[4]), str(row[5]))
        rva_index[(binary_key, int(row[2]))] = key
    return functions, rva_index, binaries


def _collect_signal_domains(
    config: NativeSemanticConfig,
    stage: sqlite3.Connection,
) -> tuple[dict[str, tuple[str, int]], dict[str, list[str]]]:
    signals: dict[str, tuple[str, int]] = {}
    evidence: dict[str, list[str]] = defaultdict(list)

    def consider(function_key: str, text: str, source: str) -> None:
        domain, priority = _domain_for_text(config, text)
        if not priority:
            return
        current = signals.get(function_key)
        if current is None or (priority, domain) > (current[1], current[0]):
            signals[function_key] = (domain, priority)
        if len(evidence[function_key]) < 8:
            evidence[function_key].append(f"{source}:{text[:180]}")

    for row in stage.execute(
        """
        SELECT function_key,name,source_kind FROM code_names
        WHERE source_kind NOT IN ('ghidra_default','rizin_analysis','reko_address_label')
        ORDER BY function_key,name
        """
    ):
        consider(str(row[0]), str(row[1]), f"name/{row[2]}")
    for row in stage.execute(
        """
        SELECT fs.function_key,s.value FROM code_function_strings fs
        JOIN code_strings s USING(string_key)
        WHERE lower(s.value) LIKE '%packet%' OR lower(s.value) LIKE '%opcode%'
           OR lower(s.value) LIKE '%serializ%' OR lower(s.value) LIKE '%loot%'
           OR lower(s.value) LIKE '%quest%' OR lower(s.value) LIKE '%skill%'
           OR lower(s.value) LIKE '%lua%' OR lower(s.value) LIKE '%buff%'
        ORDER BY fs.function_key,s.string_key
        """
    ):
        consider(str(row[0]), str(row[1]), "string")
    return signals, evidence


def _build_roots(
    config: NativeSemanticConfig,
    stage: sqlite3.Connection,
    main: sqlite3.Connection,
    functions: dict[str, tuple[str, str, str, str]],
    rva_index: dict[tuple[str, int], str],
    binaries: dict[str, tuple[str, str, int]],
    signals: dict[str, tuple[str, int]],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, dict[str, Any]]],
    list[tuple[Any, ...]],
    list[tuple[Any, ...]],
]:
    roots: dict[str, dict[str, Any]] = {}
    seeds: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    consumer_rows: list[tuple[Any, ...]] = []
    query_rows: list[tuple[Any, ...]] = []
    existing_by_consumer: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in stage.execute("SELECT * FROM code_evidence_links ORDER BY evidence_link_key"):
        payload = json.loads(str(row[6]))
        consumer_key = str(payload.get("consumer_key", ""))
        if consumer_key:
            existing_by_consumer[consumer_key].append(row)

    x2_binaries = [
        (key, arch, image_base)
        for key, (module, arch, image_base) in binaries.items()
        if module.casefold() == "x2game.dll"
    ]
    for consumer in main.execute("SELECT * FROM consumers ORDER BY consumer_key"):
        consumer_key = str(consumer[0])
        scope_key = str(consumer[1])
        name = str(consumer[3])
        locator = str(consumer[5]) if consumer[5] is not None else None
        architecture = str(consumer[6]) if consumer[6] is not None else None
        domain, priority = _domain_for_text(config, scope_key, name, str(consumer[2]))
        if priority == 0:
            domain, priority = "state_sql", 88
        root_key = f"consumer:{consumer_key}"
        _add_root(
            roots,
            root_key=root_key,
            root_kind="consumer",
            scope_key=scope_key,
            name=name,
            domain=domain,
            priority=priority,
            state="confirmed" if existing_by_consumer.get(consumer_key) else "candidate",
            evidence={"consumer_key": consumer_key, "locator": locator, "source": "consumers"},
        )
        matches: list[str] = []
        if existing_by_consumer.get(consumer_key):
            for link in existing_by_consumer[consumer_key]:
                function_key = str(link[1])
                matches.append(function_key)
                _add_seed(
                    seeds, root_key, function_key,
                    relation=str(link[3]), state=str(link[5]),
                    impact=int(config.impact["consumer"]),
                    evidence={"source_locator": str(link[4]), "evidence_link_key": str(link[0])},
                )
            classification, state = "preserved_stage15_link", "confirmed"
        else:
            for binary_key, arch, image_base in x2_binaries:
                if architecture and architecture not in {arch, "x86+x64", "x64+x86"}:
                    continue
                for rva in locator_rvas(locator, image_base):
                    function_key = rva_index.get((binary_key, rva))
                    if function_key:
                        matches.append(function_key)
            matches = sorted(set(matches))
            if len(matches) == 1:
                classification, state = "unique_locator_match", "corroborated"
            elif len(matches) > 1 and (
                architecture in {"x86+x64", "x64+x86"}
                or locator_has_explicit_architecture_pair(locator)
            ):
                classification, state = "explicit_architecture_pair", "corroborated"
            elif len(matches) > 1:
                classification, state = "architecture_ambiguous_locator", "ambiguous"
            else:
                classification, state = "locator_without_function", "failed"
            for function_key in matches:
                _add_seed(
                    seeds, root_key, function_key,
                    relation="locator_resolves_to_function", state=state,
                    impact=int(config.impact["consumer"]),
                    evidence={"locator": locator, "match_count": len(matches)},
                )
        consumer_rows.append((
            consumer_key, scope_key, locator, architecture, len(matches), classification, state,
            canonical_json(matches),
            canonical_json({"root_key": root_key, "method": classification}),
        ))

    sql_strings: dict[str, list[str]] = defaultdict(list)
    for row in stage.execute(
        """
        SELECT s.string_key,s.value FROM code_strings s
        WHERE lower(s.value) LIKE 'select %' OR lower(s.value) LIKE 'insert %'
           OR lower(s.value) LIKE 'update %' OR lower(s.value) LIKE 'delete %'
        ORDER BY s.string_key
        """
    ):
        normalized = normalize_sql(str(row[1]))
        if normalized:
            sql_strings[normalized].append(str(row[0]))
    function_by_string: dict[str, list[str]] = defaultdict(list)
    relevant_string_keys = {key for values in sql_strings.values() for key in values}
    for chunk in _chunks(sorted(relevant_string_keys)):
        placeholders = ",".join("?" for _ in chunk)
        for row in stage.execute(
            f"SELECT string_key,function_key FROM code_function_strings WHERE string_key IN ({placeholders}) ORDER BY string_key,function_key",
            chunk,
        ):
            function_by_string[str(row[0])].append(str(row[1]))
    for query in main.execute(
        "SELECT query_key,table_name,sql_text,loader_consumer,state FROM query_specs WHERE sql_text IS NOT NULL AND trim(sql_text)<>'' ORDER BY query_key"
    ):
        query_key, table_name = str(query[0]), str(query[1])
        normalized = normalize_sql(str(query[2]))
        matched_strings = sql_strings.get(normalized, [])
        matches = sorted({fn for string_key in matched_strings for fn in function_by_string.get(string_key, [])})
        domain, priority = _domain_for_text(config, table_name, normalized)
        if priority == 0:
            domain, priority = "state_sql", 88
        root_key = f"query:{query_key}"
        state = "corroborated" if matches else "failed"
        classification = (
            "exact_sql_unique_function" if len(matches) == 1 else
            "exact_sql_multiple_functions" if matches else
            "exact_sql_without_function"
        )
        _add_root(
            roots, root_key=root_key, root_kind="query", scope_key=query_key,
            name=table_name, domain=domain, priority=priority, state=state,
            evidence={"query_key": query_key, "table_name": table_name, "method": "normalized_exact_sql"},
        )
        for function_key in matches:
            _add_seed(
                seeds, root_key, function_key,
                relation="contains_exact_normalized_sql", state="corroborated",
                impact=int(config.impact["query"]),
                evidence={"normalized_sql_sha256": sha256_text(normalized), "string_matches": len(matched_strings)},
            )
        query_rows.append((
            query_key, table_name, sha256_text(normalized), len(matches), classification, state,
            canonical_json(matches),
            canonical_json({"root_key": root_key, "string_matches": len(matched_strings)}),
        ))

    for blocker in main.execute(
        """
        SELECT blocker_root_key,root_code,category,scope_kind,scope_value,state,
               disposition,priority_score,recommended_action,evidence_json
        FROM blocker_roots ORDER BY blocker_root_key
        """
    ):
        blocker_key, scope_value = str(blocker[0]), str(blocker[4])
        root_key = f"blocker:{blocker_key}"
        domain, priority = _domain_for_text(config, str(blocker[1]), scope_value, str(blocker[2]))
        if priority == 0:
            domain, priority = "unclassified", min(70, int(blocker[7]))
        _add_root(
            roots, root_key=root_key, root_kind="blocker", scope_key=blocker_key,
            name=f"{blocker[1]}:{scope_value}", domain=domain,
            priority=max(priority, min(100, int(blocker[7]) // 2)), state=str(blocker[5]),
            evidence={
                "blocker_root_key": blocker_key, "scope_kind": str(blocker[3]),
                "scope_value": scope_value, "disposition": str(blocker[6]),
                "recommended_action": str(blocker[8]),
            },
        )
        token = scope_value.casefold().replace("_", " ").strip()
        # Domain-level candidates are deliberately capped and remain candidates.
        candidates: list[str] = []
        if token and domain != "unclassified":
            candidates = sorted(
                function_key for function_key, (signal_domain, _) in signals.items()
                if signal_domain == domain
            )[:25]
        for function_key in sorted(candidates)[:25]:
            _add_seed(
                seeds, root_key, function_key,
                relation="candidate_domain_signal", state="candidate",
                impact=int(config.impact["blocker"]),
                evidence={"scope_value": scope_value, "domain": domain, "capped": True},
            )

    structured_sources = {"pe_export", "confirmed_forensic_consumer", "review_overlay"}
    for row in stage.execute(
        "SELECT function_key,name,source_kind,state FROM code_names ORDER BY function_key,name"
    ):
        function_key, name, source_kind, state = map(str, row)
        if source_kind not in structured_sources:
            continue
        domain, priority = _domain_for_text(config, name)
        if priority < 80:
            continue
        root_key = f"native-symbol:{function_key}:{sha256_text(name)[:12]}"
        _add_root(
            roots, root_key=root_key, root_kind="native_symbol", scope_key=function_key,
            name=name, domain=domain, priority=priority,
            state="confirmed" if source_kind == "pe_export" else state,
            evidence={"source_kind": source_kind, "native_state": state},
        )
        _add_seed(
            seeds, root_key, function_key,
            relation="native_structured_name", state="confirmed" if source_kind == "pe_export" else state,
            impact=int(config.impact["native_symbol"]), evidence={"name": name, "source_kind": source_kind},
        )

    for row in stage.execute(
        """
        SELECT DISTINCT s.target_function_key,t.type_name,v.vtable_key,s.ordinal,s.state
        FROM code_vtable_slots s
        JOIN code_vtables v USING(vtable_key)
        JOIN code_types t USING(type_key)
        WHERE s.target_function_key IS NOT NULL
        ORDER BY s.target_function_key,v.vtable_key,s.ordinal
        """
    ):
        function_key, type_name = str(row[0]), str(row[1])
        domain, priority = _domain_for_text(config, type_name)
        if priority < 80:
            continue
        root_key = f"vtable:{row[2]}"
        _add_root(
            roots, root_key=root_key, root_kind="rtti_vtable", scope_key=str(row[2]),
            name=type_name, domain=domain, priority=priority, state=str(row[4]),
            evidence={"vtable_key": str(row[2]), "type_name": type_name},
        )
        _add_seed(
            seeds, root_key, function_key, relation="vtable_slot", state=str(row[4]),
            impact=int(config.impact["rtti_vtable"]), evidence={"ordinal": int(row[3])},
        )
    return roots, seeds, consumer_rows, query_rows


def _neighbors(
    stage: sqlite3.Connection,
    frontier: set[str],
    direction: str,
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for chunk in _chunks(sorted(frontier)):
        placeholders = ",".join("?" for _ in chunk)
        if direction == "outbound":
            sql = (
                "SELECT caller_function_key,callee_function_key FROM code_calls "
                f"WHERE caller_function_key IN ({placeholders}) AND callee_function_key IS NOT NULL "
                "ORDER BY caller_function_key,callee_function_key"
            )
        else:
            sql = (
                "SELECT callee_function_key,caller_function_key FROM code_calls "
                f"WHERE callee_function_key IN ({placeholders}) ORDER BY callee_function_key,caller_function_key"
            )
        for row in stage.execute(sql, chunk):
            result[str(row[0])].add(str(row[1]))
    return result


def _fan_counts(stage: sqlite3.Connection) -> tuple[dict[str, int], dict[str, int]]:
    fanin = {
        str(row[0]): int(row[1])
        for row in stage.execute(
            "SELECT callee_function_key,COUNT(*) FROM code_calls WHERE callee_function_key IS NOT NULL GROUP BY callee_function_key"
        )
    }
    fanout = {
        str(row[0]): int(row[1])
        for row in stage.execute(
            "SELECT caller_function_key,COUNT(*) FROM code_calls WHERE callee_function_key IS NOT NULL GROUP BY caller_function_key"
        )
    }
    return fanin, fanout


def _closure_for_root(
    config: NativeSemanticConfig,
    stage: sqlite3.Connection,
    root: dict[str, Any],
    direct: dict[str, dict[str, Any]],
    fanin: dict[str, int],
    signal_domains: dict[str, tuple[str, int]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for function_key, seed in sorted(direct.items()):
        records[function_key] = {
            "direction": "seed", "depth": 0, "impact": int(seed["impact"]),
            "state": seed["state"], "relation": seed["relation"],
            "path": [function_key], "evidence": seed["evidence"],
        }
    max_functions = int(config.closure["max_functions"])
    truncated = False
    truncation_reason: str | None = None
    counts = {"outbound": 0, "inbound": 0}
    for direction, max_depth in (
        ("outbound", int(config.closure["outbound_depth"])),
        ("inbound", int(config.closure["inbound_depth"])),
    ):
        visited = set(direct)
        paths = {function_key: [function_key] for function_key in direct}
        frontier = set(direct)
        for depth in range(1, max_depth + 1):
            if not frontier or len(records) >= max_functions:
                break
            expandable = {
                function_key for function_key in frontier
                if fanin.get(function_key, 0) < int(config.closure["fanin_cutoff"])
                or function_key in direct
                or signal_domains.get(function_key, (None, 0))[0] == root["domain"]
            }
            if not expandable:
                break
            neighbor_map = _neighbors(stage, expandable, direction)
            next_frontier: set[str] = set()
            for parent in sorted(neighbor_map):
                for child in sorted(neighbor_map[parent]):
                    if child in visited:
                        continue
                    if len(records) >= max_functions:
                        truncated = True
                        truncation_reason = "truncated_high_fanout"
                        break
                    visited.add(child)
                    next_frontier.add(child)
                    paths[child] = paths[parent] + [child]
                    impact_values = config.impact[direction]
                    impact = int(impact_values[min(depth, len(impact_values) - 1)])
                    candidate = {
                        "direction": direction, "depth": depth, "impact": impact,
                        "state": "candidate", "relation": f"{direction}_call",
                        "path": paths[child], "evidence": {"distance": depth},
                    }
                    current = records.get(child)
                    if current is None or (impact, -depth, direction) > (
                        current["impact"], -current["depth"], current["direction"]
                    ):
                        records[child] = candidate
                        counts[direction] += 1
                if truncated:
                    break
            frontier = next_frontier
            if truncated:
                break
        if truncated:
            break
    summary = {
        "outbound_functions": counts["outbound"],
        "inbound_functions": counts["inbound"],
        "total_functions": len(records),
        "max_outbound_depth": int(config.closure["outbound_depth"]),
        "max_inbound_depth": int(config.closure["inbound_depth"]),
        "truncated": int(truncated),
        "truncation_reason": truncation_reason,
    }
    return records, summary


def _insert_many(connection: sqlite3.Connection, sql: str, rows: list[tuple[Any, ...]], batch: int = 10000) -> None:
    for index in range(0, len(rows), batch):
        connection.executemany(sql, rows[index:index + batch])


def _validation_row(check: str, status: str, expected: Any, actual: Any, evidence: Any) -> tuple[str, str, str, str, str, str]:
    return (
        stable_key("semantic-validation", check), check, status,
        canonical_json(expected), canonical_json(actual), canonical_json(evidence),
    )


def build_native_semantic_index(
    semantic: NativeSemanticConfig,
    native: NativeCodeConfig,
    forensics: ForensicsConfig,
    *,
    resume: bool = False,
) -> dict[str, Any]:
    del resume  # The build is atomic; valid completed databases are never overwritten partially.
    inputs = _verify_inputs(semantic, native, forensics)
    semantic.database.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{semantic.database.stem}.", suffix=".sqlite", dir=semantic.database.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    temporary.unlink(missing_ok=True)
    stage = open_read_only(native.stage_database)
    main = open_read_only(forensics.consolidated)
    target: sqlite3.Connection | None = None
    try:
        stage.row_factory = sqlite3.Row
        main.row_factory = sqlite3.Row
        target = _create_database(temporary)
        functions, rva_index, binaries = _load_function_catalog(stage)
        signals, signal_evidence = _collect_signal_domains(semantic, stage)
        roots, seeds, consumer_rows, query_rows = _build_roots(
            semantic, stage, main, functions, rva_index, binaries, signals
        )
        reviews, review_sha256 = _load_semantic_reviews(semantic, stage, roots)
        consumer_rows = _apply_review_consumer_resolutions(
            semantic, roots, seeds, consumer_rows, reviews
        )
        root_rows = [
            (
                root["root_key"], root["root_kind"], root["scope_key"], root["name"],
                root["domain"], root["backend_priority"], root["state"], root["evidence_json"],
            )
            for root in sorted(roots.values(), key=lambda value: value["root_key"])
        ]
        _insert_many(target, "INSERT INTO semantic_roots VALUES(?,?,?,?,?,?,?,?)", root_rows)
        _insert_many(target, "INSERT INTO semantic_consumer_classification VALUES(?,?,?,?,?,?,?,?,?)", consumer_rows)
        _insert_many(target, "INSERT INTO semantic_query_classification VALUES(?,?,?,?,?,?,?,?)", query_rows)
        fanin, fanout = _fan_counts(stage)
        best: dict[str, dict[str, Any]] = {}
        root_links: list[tuple[Any, ...]] = []
        closure_rows: list[tuple[Any, ...]] = []
        closure_members: dict[str, set[str]] = {}
        root_max_impact: dict[str, int] = {}
        for root_key in sorted(roots):
            root = roots[root_key]
            records, summary = _closure_for_root(
                semantic, stage, root, seeds.get(root_key, {}), fanin, signals
            )
            closure_members[root_key] = set(records)
            root_max_impact[root_key] = max(
                (int(record["impact"]) for record in records.values()), default=0
            )
            for function_key, record in sorted(records.items()):
                link_key = stable_key("semantic-root-function", root_key, function_key, record["direction"])
                root_links.append((
                    link_key, root_key, function_key, record["relation"], record["direction"],
                    record["depth"], record["impact"], record["state"],
                    canonical_json(record["path"]), canonical_json(record["evidence"]),
                ))
                rank = (
                    int(record["impact"]), int(root["backend_priority"]),
                    -int(record["depth"]), root_key,
                )
                current = best.get(function_key)
                if current is None or rank > current["rank"]:
                    best[function_key] = {
                        "rank": rank, "root_key": root_key, "domain": root["domain"],
                        "impact": int(record["impact"]), "direction": record["direction"],
                        "depth": int(record["depth"]),
                    }
            closure_rows.append((
                root_key, summary["outbound_functions"], summary["inbound_functions"],
                summary["total_functions"], summary["max_outbound_depth"],
                summary["max_inbound_depth"], summary["truncated"],
                summary["truncation_reason"], "pending_review",
                canonical_json({"direct_seeds": len(seeds.get(root_key, {}))}),
            ))
            if len(root_links) >= 100000:
                _insert_many(target, "INSERT INTO semantic_root_functions VALUES(?,?,?,?,?,?,?,?,?,?)", root_links)
                root_links.clear()
        if root_links:
            _insert_many(target, "INSERT INTO semantic_root_functions VALUES(?,?,?,?,?,?,?,?,?,?)", root_links)
        _insert_many(target, "INSERT INTO semantic_closures VALUES(?,?,?,?,?,?,?,?,?,?)", closure_rows)

        review_reasons: dict[str, list[str]] = defaultdict(list)
        for row in stage.execute(
            "SELECT function_key,reason_code FROM code_review_queue ORDER BY function_key,reason_code"
        ):
            review_reasons[str(row[0])].append(str(row[1]))
        reason_rows: list[tuple[Any, ...]] = []
        classifications: dict[str, dict[str, Any]] = {}
        reason_score = {
            "decompiler_failure": semantic.uncertainty["decompiler_failure"],
            "function_boundary_disagreement": semantic.uncertainty["boundary_disagreement"],
            "architecture_equivalence_requires_review": semantic.uncertainty["architecture_equivalence"],
            "incompatible_type": semantic.uncertainty["incompatible_type"],
        }
        for function_key in sorted(functions):
            binary_key, module_name, architecture, binary_class = functions[function_key]
            primary = best.get(function_key)
            signal = signals.get(function_key)
            uncertainty = 0
            for reason in sorted(set(review_reasons.get(function_key, []))):
                delta = int(reason_score.get(reason, 0))
                uncertainty += delta
                reason_rows.append((
                    stable_key("semantic-reason", function_key, reason), function_key,
                    primary["root_key"] if primary else None, reason, "uncertainty", delta,
                    "candidate", canonical_json({"source": "code_review_queue"}),
                ))
            if primary:
                category = "critical_root" if primary["depth"] == 0 else (
                    "critical_reachable" if primary["impact"] >= 60 else "support_reachable"
                )
                domain, impact = primary["domain"], primary["impact"]
                primary_root = primary["root_key"]
                state = "corroborated" if primary["depth"] else roots[primary_root]["state"]
            elif signal:
                category, domain, impact, primary_root, state = (
                    "candidate_signal", signal[0], 20, None, "candidate"
                )
            elif binary_class == "third_party":
                category, domain, impact, primary_root, state = (
                    "external_or_not_backend_relevant", "external", 0, None, "confirmed"
                )
            elif binary_class == "engine_modified":
                category, domain, impact, primary_root, state = (
                    "external_or_not_backend_relevant", "engine_dependency", 0, None, "candidate"
                )
            else:
                category, domain, impact, primary_root, state = (
                    "unlinked", "unclassified", 0, None, "candidate"
                )
            classifications[function_key] = {
                "binary_key": binary_key, "module_name": module_name,
                "architecture": architecture, "domain": domain, "category": category,
                "impact": impact, "uncertainty": uncertainty, "tier": _tier(impact),
                "fanin": fanin.get(function_key, 0), "fanout": fanout.get(function_key, 0),
                "primary_root": primary_root, "state": state,
                "evidence": {
                    "signal_evidence": signal_evidence.get(function_key, []),
                    "binary_classification": binary_class,
                },
            }

        critical_keys = sorted(
            key for key, value in classifications.items()
            if value["category"] in {"critical_root", "critical_reachable", "support_reachable"}
        )
        resolved_callsites: dict[str, set[int]] = defaultdict(set)
        for chunk in _chunks(critical_keys):
            placeholders = ",".join("?" for _ in chunk)
            for row in stage.execute(
                f"SELECT caller_function_key,callsite_rva FROM code_calls WHERE caller_function_key IN ({placeholders}) AND callee_function_key IS NOT NULL",
                chunk,
            ):
                resolved_callsites[str(row[0])].add(int(row[1]))
        indirect_rows: list[tuple[Any, ...]] = []
        indirect_functions: set[str] = set()
        for chunk in _chunks(critical_keys):
            placeholders = ",".join("?" for _ in chunk)
            for row in stage.execute(
                f"SELECT function_key,rva,instruction_text FROM code_instructions WHERE function_key IN ({placeholders}) AND lower(mnemonic)='call' ORDER BY function_key,rva",
                chunk,
            ):
                function_key, rva, instruction = str(row[0]), int(row[1]), str(row[2])
                if rva in resolved_callsites.get(function_key, set()):
                    continue
                operand = instruction.split(None, 1)[1] if " " in instruction else instruction
                if "[" not in operand and not _CALL_REGISTER.search(operand):
                    continue
                pattern = "memory_indirect" if "[" in operand else "register_indirect"
                indirect_functions.add(function_key)
                indirect_rows.append((
                    stable_key("semantic-indirect", function_key, rva), function_key, rva,
                    instruction, pattern, None, "candidate",
                    canonical_json({"resolved_direct_call_present": False}),
                ))
        _insert_many(target, "INSERT INTO semantic_indirect_sites VALUES(?,?,?,?,?,?,?,?)", indirect_rows)
        for function_key in sorted(indirect_functions):
            delta = int(semantic.uncertainty["indirect_dispatch"])
            classifications[function_key]["uncertainty"] += delta
            reason_rows.append((
                stable_key("semantic-reason", function_key, "indirect_dispatch"), function_key,
                classifications[function_key]["primary_root"], "indirect_dispatch",
                "uncertainty", delta, "candidate", canonical_json({"source": "instruction_pattern"}),
            ))

        opaque_by_binary: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
        opaque_info: dict[str, tuple[str, int, int]] = {}
        for row in stage.execute(
            "SELECT region_key,binary_key,start_rva,end_rva FROM code_regions WHERE region_kind='opaque' ORDER BY binary_key,start_rva,region_key"
        ):
            region_key, binary_key, start_rva, end_rva = str(row[0]), str(row[1]), int(row[2]), int(row[3])
            opaque_by_binary[binary_key].append((start_rva, end_rva, region_key))
            opaque_info[region_key] = (binary_key, start_rva, end_rva)
        opaque_starts = {
            binary_key: [value[0] for value in values]
            for binary_key, values in opaque_by_binary.items()
        }
        opaque_hits: dict[str, dict[str, Any]] = {}

        def hit_region(function_key: str, target_rva: int) -> None:
            binary_key = functions[function_key][0]
            values = opaque_by_binary.get(binary_key, [])
            if not values:
                return
            index = bisect.bisect_right(opaque_starts[binary_key], target_rva) - 1
            if index < 0:
                return
            start_rva, end_rva, region_key = values[index]
            if not (start_rva <= target_rva < end_rva):
                return
            classification = classifications[function_key]
            critical = classification["category"] in {"critical_root", "critical_reachable"}
            impact = classification["impact"]
            candidate = {
                "function_key": function_key, "root_key": classification["primary_root"],
                "impact": impact, "critical": critical,
            }
            current = opaque_hits.get(region_key)
            if current is None or (critical, impact, function_key) > (
                current["critical"], current["impact"], current["function_key"]
            ):
                opaque_hits[region_key] = candidate

        for chunk in _chunks(critical_keys):
            placeholders = ",".join("?" for _ in chunk)
            for row in stage.execute(
                f"SELECT function_key,to_rva FROM code_data_references WHERE function_key IN ({placeholders}) ORDER BY function_key,to_rva",
                chunk,
            ):
                hit_region(str(row[0]), int(row[1]))
            for row in stage.execute(
                f"SELECT caller_function_key,target_rva FROM code_calls WHERE caller_function_key IN ({placeholders}) AND target_rva IS NOT NULL AND callee_function_key IS NULL ORDER BY caller_function_key,target_rva",
                chunk,
            ):
                hit_region(str(row[0]), int(row[1]))
        opaque_rows: list[tuple[Any, ...]] = []
        opaque_functions: set[str] = set()
        reviewed_region_overrides = {
            str(region["region_key"]): (root_key, review, region)
            for root_key, review in reviews.items()
            for region in review.get("regions", [])
        }
        for region_key in sorted(opaque_info):
            binary_key, start_rva, end_rva = opaque_info[region_key]
            hit = opaque_hits.get(region_key)
            if hit and hit["critical"]:
                classification, state = "critical_blocker", "corroborated"
            elif hit:
                classification, state = "reachable_context", "candidate"
            else:
                classification, state = "unlinked_no_demonstrated_impact", "confirmed"
            evidence = {
                "mapping": "direct_call_or_data_reference" if hit else "no_critical_reference"
            }
            reviewed = reviewed_region_overrides.get(region_key)
            if reviewed is not None:
                review_root_key, review, region = reviewed
                if hit is not None and hit.get("root_key") != review_root_key:
                    raise ValueError(
                        "Reviewed semantic region is linked to a different primary root: "
                        f"{region_key} expected={review_root_key} actual={hit.get('root_key')}"
                    )
                classification = str(region["classification"])
                state = str(region["state"])
                evidence.update({
                    "review_key": str(review["review_key"]),
                    "review_role": str(region["role"]),
                    "review_evidence": list(region["evidence"]),
                    "review_overrides_sha256": review_sha256,
                })
            if hit and not (reviewed is not None and classification != "critical_blocker"):
                opaque_functions.add(hit["function_key"])
            opaque_rows.append((
                region_key, binary_key, start_rva, end_rva, classification,
                int(hit["impact"]) if hit else 0,
                hit["function_key"] if hit else None, hit["root_key"] if hit else None,
                state, canonical_json(evidence),
            ))
        _insert_many(target, "INSERT INTO semantic_opaque_regions VALUES(?,?,?,?,?,?,?,?,?,?)", opaque_rows)
        for function_key in sorted(opaque_functions):
            delta = int(semantic.uncertainty["opaque"])
            classifications[function_key]["uncertainty"] += delta
            reason_rows.append((
                stable_key("semantic-reason", function_key, "opaque_reference"), function_key,
                classifications[function_key]["primary_root"], "opaque_reference",
                "uncertainty", delta, "corroborated", canonical_json({"source": "opaque_interval_mapping"}),
            ))
        classification_rows = [
            (
                function_key, value["binary_key"], value["module_name"], value["architecture"],
                value["domain"], value["category"], value["impact"], value["uncertainty"],
                value["tier"], value["fanin"], value["fanout"], value["primary_root"],
                value["state"], canonical_json(value["evidence"]),
            )
            for function_key, value in sorted(classifications.items())
        ]
        _insert_many(target, "INSERT INTO semantic_function_classifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", classification_rows)
        _insert_many(target, "INSERT INTO semantic_function_reasons VALUES(?,?,?,?,?,?,?,?)", reason_rows)

        closure_by_root = {row[0]: row for row in closure_rows}
        root_uncertainty: dict[str, int] = defaultdict(int)
        for function_key, value in classifications.items():
            root_key = value["primary_root"]
            if root_key:
                root_uncertainty[root_key] = max(root_uncertainty[root_key], value["uncertainty"])
        opaque_roots = {
            str(row[7]) for row in opaque_rows
            if row[4] == "critical_blocker" and row[7]
        }
        indirect_roots = {
            classifications[key]["primary_root"] for key in indirect_functions
            if classifications[key]["primary_root"]
        }
        ranked: list[tuple[Any, str, str]] = []
        for root_key, root in roots.items():
            closure = closure_by_root[root_key]
            members = closure_members[root_key]
            impact = root_max_impact[root_key]
            if not members:
                status = "blocked_by_missing_native_data"
            elif root_key in opaque_roots:
                status = "blocked_by_opaque_region"
            elif root_key in indirect_roots:
                status = "blocked_by_indirect_dispatch"
            elif root["domain"] == "external":
                status = "external_dependency"
            elif root["domain"] == "presentation":
                status = "not_backend_relevant"
            elif root["root_kind"] in {"consumer", "native_symbol"} and not closure[6]:
                status = "understood"
            else:
                status = "pending_review"
            review = reviews.get(root_key)
            if review is not None:
                status = str(review["closure_status"])
            ranked.append((
                (-impact, -int(root["backend_priority"]), -root_uncertainty[root_key], -int(closure[3]), root_key),
                root_key, status,
            ))
        ranked.sort(key=lambda value: value[0])
        forced: list[str] = []
        for predicate in (
            lambda key: "loot_pack" in roots[key]["name"].casefold(),
            lambda key: roots[key]["domain"] == "protocol" and roots[key]["root_kind"] in {"consumer", "native_symbol", "rtti_vtable"} and any(
                token in roots[key]["name"].casefold() for token in ("packet", "serial", "opcode", "message")
            ),
            lambda key: key in opaque_roots or key in indirect_roots,
        ):
            match = next((key for _, key, _ in ranked if key not in forced and predicate(key)), None)
            if match:
                forced.append(match)
        order = forced + [key for _, key, _ in ranked if key not in forced]
        status_by_root = {key: status for _, key, status in ranked}
        queue_rows: list[tuple[Any, ...]] = []
        for index, root_key in enumerate(order, start=1):
            root = roots[root_key]
            closure = closure_by_root[root_key]
            members = closure_members[root_key]
            impact = root_max_impact[root_key]
            status = status_by_root[root_key]
            queue_evidence = {
                "forced_first_wave": root_key in forced,
                "stable_tiebreaker": root_key,
            }
            review = reviews.get(root_key)
            if review is not None:
                queue_evidence.update({
                    "review_key": str(review["review_key"]),
                    "review_state": str(review["state"]),
                    "review_overrides_sha256": review_sha256,
                })
            queue_rows.append((
                stable_key("semantic-queue", root_key), index, ((index - 1) // 25) + 1,
                root_key, root["domain"], _tier(impact), impact, root["backend_priority"],
                root_uncertainty[root_key], int(closure[3]), status,
                "export and review semantic closure" if status == "pending_review" else status,
                canonical_json(queue_evidence),
            ))
        _insert_many(target, "INSERT INTO semantic_work_queue VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", queue_rows)
        for root_key, status in sorted(status_by_root.items()):
            evidence = json.loads(str(target.execute(
                "SELECT evidence_json FROM semantic_closures WHERE root_key=?", (root_key,)
            ).fetchone()[0]))
            review = reviews.get(root_key)
            if review is not None:
                evidence.update({
                    "review_key": str(review["review_key"]),
                    "review_state": str(review["state"]),
                    "review_overrides_sha256": review_sha256,
                })
            target.execute(
                "UPDATE semantic_closures SET closure_status=?,evidence_json=? WHERE root_key=?",
                (status, canonical_json(evidence), root_key),
            )

        actual_function_categories = {row[5] for row in classification_rows}
        actual_opaque_categories = {row[4] for row in opaque_rows}
        validation_rows = [
            _validation_row("all_consumers_classified", "confirmed" if len(consumer_rows) == 132 else "failed", 132, len(consumer_rows), {}),
            _validation_row("all_query_specs_classified", "confirmed" if len(query_rows) == 662 else "failed", 662, len(query_rows), {}),
            _validation_row("all_functions_classified", "confirmed" if len(classification_rows) == len(functions) else "failed", len(functions), len(classification_rows), {}),
            _validation_row("all_opaque_regions_classified", "confirmed" if len(opaque_rows) == 50011 else "failed", 50011, len(opaque_rows), {}),
            _validation_row("function_categories_closed", "confirmed" if actual_function_categories <= FUNCTION_CATEGORIES else "failed", sorted(FUNCTION_CATEGORIES), sorted(actual_function_categories), {}),
            _validation_row("opaque_categories_closed", "confirmed" if actual_opaque_categories <= OPAQUE_CLASSIFICATIONS else "failed", sorted(OPAQUE_CLASSIFICATIONS), sorted(actual_opaque_categories), {}),
        ]
        _insert_many(target, "INSERT INTO validation_events VALUES(?,?,?,?,?,?)", validation_rows)
        metadata = {
            "format": NATIVE_SEMANTIC_FORMAT,
            "schema_version": str(NATIVE_SEMANTIC_SCHEMA_VERSION),
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "client_build": semantic.client_build,
            "config_sha256": semantic.config_sha256,
            "review_overrides_sha256": review_sha256 or "",
            "semantic_review_count": str(len(reviews)),
            **inputs,
        }
        target.executemany(
            "INSERT INTO metadata(key,value) VALUES(?,?)",
            sorted(metadata.items()),
        )
        target.commit()
        foreign_keys = list(target.execute("PRAGMA foreign_key_check"))
        if foreign_keys:
            raise RuntimeError(f"Native semantic foreign-key failures: {len(foreign_keys)}")
        failed_validation = int(target.execute("SELECT COUNT(*) FROM validation_events WHERE status<>'confirmed'").fetchone()[0])
        if failed_validation:
            raise RuntimeError(f"Native semantic validation failures: {failed_validation}")
        target.execute("VACUUM")
        target.close()
        target = None
        os.replace(temporary, semantic.database)
        result = validate_native_semantic_index(semantic, native=native, forensics=forensics)
        index_sha256 = sha256_file(semantic.database).upper()
        review_dossiers = _write_review_dossiers(
            semantic,
            stage,
            reviews,
            review_sha256=review_sha256,
            index_sha256=index_sha256,
        )
        manifest = {
            "format": NATIVE_SEMANTIC_FORMAT,
            "classification": "native_semantic_triage_lateral_index",
            "client_build": semantic.client_build,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "schema_version": NATIVE_SEMANTIC_SCHEMA_VERSION,
            "database": {
                "path": semantic.database.as_posix(),
                "bytes": semantic.database.stat().st_size,
                "sha256": index_sha256,
            },
            "inputs": inputs,
            "config_sha256": semantic.config_sha256,
            "review_overrides": {
                "path": semantic.review_overrides.as_posix() if semantic.review_overrides else None,
                "sha256": review_sha256,
                "count": len(reviews),
            },
            "review_dossiers": review_dossiers,
            "determinism": {
                "atomic_replace": True,
                "stable_ordering": True,
                "timestamps_in_reproducible_artifacts": False,
                "pseudocode_copied": False,
            },
            "summary": result["counts"],
            "validation": result["validation"],
        }
        atomic_text(semantic.manifest, canonical_json(manifest, pretty=True))
        return manifest
    finally:
        stage.close()
        main.close()
        if target is not None:
            target.close()
        temporary.unlink(missing_ok=True)


def validate_native_semantic_index(
    semantic: NativeSemanticConfig,
    *,
    native: NativeCodeConfig | None = None,
    forensics: ForensicsConfig | None = None,
) -> dict[str, Any]:
    if not semantic.database.is_file():
        raise FileNotFoundError(semantic.database)
    if native is not None and forensics is not None:
        _verify_inputs(semantic, native, forensics)
    connection = open_read_only(semantic.database)
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = len(list(connection.execute("PRAGMA foreign_key_check")))
        counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "semantic_roots", "semantic_root_functions", "semantic_function_classifications",
                "semantic_function_reasons", "semantic_closures", "semantic_consumer_classification",
                "semantic_query_classification", "semantic_indirect_sites", "semantic_opaque_regions",
                "semantic_work_queue", "validation_events",
            )
        }
        failed = int(connection.execute("SELECT COUNT(*) FROM validation_events WHERE status<>'confirmed'").fetchone()[0])
        critical_without_path = int(connection.execute(
            """
            SELECT COUNT(*) FROM semantic_function_classifications f
            WHERE f.category IN ('critical_root','critical_reachable')
              AND (f.primary_root_key IS NULL OR NOT EXISTS(
                  SELECT 1 FROM semantic_root_functions r
                  WHERE r.root_key=f.primary_root_key AND r.function_key=f.function_key
              ))
            """
        ).fetchone()[0])
        orphan_links = int(connection.execute(
            "SELECT COUNT(*) FROM semantic_root_functions r LEFT JOIN semantic_roots s USING(root_key) WHERE s.root_key IS NULL"
        ).fetchone()[0])
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        errors = []
        if quick != "ok": errors.append(f"quick_check={quick}")
        if integrity != "ok": errors.append(f"integrity_check={integrity}")
        if foreign_keys: errors.append(f"foreign_keys={foreign_keys}")
        if failed: errors.append(f"validation_events_failed={failed}")
        if critical_without_path: errors.append(f"critical_without_path={critical_without_path}")
        if orphan_links: errors.append(f"orphan_links={orphan_links}")
        if counts["semantic_consumer_classification"] != 132: errors.append("consumer_count")
        if counts["semantic_query_classification"] != 662: errors.append("query_count")
        if counts["semantic_function_classifications"] != 387437: errors.append("function_count")
        if counts["semantic_opaque_regions"] != 50011: errors.append("opaque_count")
        if metadata.get("stage_15_sha256", "").upper() != semantic.required_stage_15_sha256:
            errors.append("stage_15_lineage")
        expected_review_sha256 = (
            sha256_text(semantic.review_overrides.read_text(encoding="utf-8")).upper()
            if semantic.review_overrides is not None else ""
        )
        if metadata.get("review_overrides_sha256", "").upper() != expected_review_sha256:
            errors.append("review_overrides_lineage")
        result = {
            "database": semantic.database.as_posix(),
            "sha256": sha256_file(semantic.database).upper(),
            "counts": counts,
            "validation": {
                "quick_check": quick, "integrity_check": integrity,
                "foreign_key_failures": foreign_keys,
                "failed_validation_events": failed,
                "critical_without_path": critical_without_path,
                "orphan_links": orphan_links,
                "status": "confirmed" if not errors else "failed",
                "errors": errors,
            },
        }
        if errors:
            raise RuntimeError("Native semantic validation failed: " + ", ".join(errors))
        return result
    finally:
        connection.close()


def native_semantic_status(
    semantic: NativeSemanticConfig,
    *,
    domain: str | None = None,
    tier: str | None = None,
) -> dict[str, Any]:
    if not semantic.database.is_file():
        return {"database": semantic.database.as_posix(), "present": False, "status": "not_built"}
    connection = open_read_only(semantic.database)
    try:
        clauses, parameters = [], []
        if domain:
            clauses.append("domain=?")
            parameters.append(domain)
        if tier:
            clauses.append("impact_tier=?")
            parameters.append(tier)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        categories = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                f"SELECT category,COUNT(*) FROM semantic_function_classifications{where} GROUP BY category ORDER BY category",
                parameters,
            )
        }
        queue_where, queue_parameters = [], []
        if domain:
            queue_where.append("domain=?")
            queue_parameters.append(domain)
        if tier:
            queue_where.append("impact_tier=?")
            queue_parameters.append(tier)
        queue_sql = " WHERE " + " AND ".join(queue_where) if queue_where else ""
        return {
            "database": semantic.database.as_posix(), "present": True,
            "sha256": sha256_file(semantic.database).upper(),
            "filters": {"domain": domain, "tier": tier},
            "function_categories": categories,
            "opaque_regions": dict(connection.execute(
                "SELECT classification,COUNT(*) FROM semantic_opaque_regions GROUP BY classification ORDER BY classification"
            )),
            "closure_status": dict(connection.execute(
                f"SELECT closure_status,COUNT(*) FROM semantic_work_queue{queue_sql} GROUP BY closure_status ORDER BY closure_status",
                queue_parameters,
            )),
            "next_roots": [
                dict(zip(("rank", "wave", "root_key", "domain", "tier", "impact", "uncertainty", "status"), row))
                for row in connection.execute(
                    f"SELECT rank,wave,root_key,domain,impact_tier,impact_score,uncertainty_score,closure_status FROM semantic_work_queue{queue_sql} ORDER BY rank LIMIT 25",
                    queue_parameters,
                )
            ],
        }
    finally:
        connection.close()


def export_native_closure(
    semantic: NativeSemanticConfig,
    native: NativeCodeConfig,
    root_kind: str,
    root_key: str,
) -> dict[str, Any]:
    connection = open_read_only(semantic.database)
    stage = open_read_only(native.stage_database)
    connection.row_factory = sqlite3.Row
    stage.row_factory = sqlite3.Row
    try:
        if semantic.manifest.is_file():
            semantic_sha = str(
                json.loads(semantic.manifest.read_text(encoding="utf-8"))["database"]["sha256"]
            ).upper()
        else:
            semantic_sha = sha256_file(semantic.database).upper()
        if not root_key.startswith(f"{root_kind}:"):
            candidates = connection.execute(
                "SELECT root_key FROM semantic_roots WHERE root_kind=? AND scope_key=? ORDER BY root_key",
                (root_kind, root_key),
            ).fetchall()
            if len(candidates) != 1:
                raise KeyError(f"Semantic root is absent or ambiguous: {root_kind} {root_key}")
            root_key = str(candidates[0][0])
        root = connection.execute("SELECT * FROM semantic_roots WHERE root_key=?", (root_key,)).fetchone()
        if root is None:
            raise KeyError(root_key)
        closure = connection.execute("SELECT * FROM semantic_closures WHERE root_key=?", (root_key,)).fetchone()
        members = connection.execute(
            """
            SELECT rf.*,f.module_name,f.architecture,f.category,f.uncertainty_score,f.fanin,f.fanout
            FROM semantic_root_functions rf
            JOIN semantic_function_classifications f USING(function_key)
            WHERE rf.root_key=?
            ORDER BY rf.depth,rf.direction,rf.function_key
            """,
            (root_key,),
        ).fetchall()
        function_keys = [str(row[2]) for row in members[:250]]
        details: dict[str, dict[str, Any]] = {key: {"names": [], "strings": []} for key in function_keys}
        for chunk in _chunks(function_keys):
            placeholders = ",".join("?" for _ in chunk)
            for row in stage.execute(
                f"SELECT function_key,name,source_kind,state FROM code_names WHERE function_key IN ({placeholders}) ORDER BY function_key,primary_name DESC,name",
                chunk,
            ):
                bucket = details[str(row[0])]["names"]
                if len(bucket) < 6:
                    bucket.append({"name": str(row[1]), "source": str(row[2]), "state": str(row[3])})
            for row in stage.execute(
                f"""
                SELECT fs.function_key,s.value,fs.state FROM code_function_strings fs
                JOIN code_strings s USING(string_key)
                WHERE fs.function_key IN ({placeholders}) ORDER BY fs.function_key,s.string_key
                """,
                chunk,
            ):
                bucket = details[str(row[0])]["strings"]
                if len(bucket) < 12:
                    bucket.append({"value": str(row[1])[:500], "state": str(row[2])})
        dossier = {
            "format": "AA8_NATIVE_SEMANTIC_DOSSIER_V1",
            "client_build": semantic.client_build,
            "source_index_sha256": semantic_sha,
            "stage_15_sha256": semantic.required_stage_15_sha256,
            "root": dict(root), "closure": dict(closure),
            "functions": [dict(row) | {"details": details.get(str(row[2]), {})} for row in members[:250]],
            "functions_total": len(members), "functions_exported": min(len(members), 250),
            "truncated_for_dossier": len(members) > 250,
            "indirect_sites": [dict(row) for row in connection.execute(
                "SELECT * FROM semantic_indirect_sites WHERE function_key IN (SELECT function_key FROM semantic_root_functions WHERE root_key=?) ORDER BY function_key,callsite_rva",
                (root_key,),
            )],
            "opaque_blockers": [dict(row) for row in connection.execute(
                "SELECT * FROM semantic_opaque_regions WHERE primary_root_key=? ORDER BY impact_score DESC,region_key",
                (root_key,),
            )],
            "authority_note": "Semantic triage is derived evidence; pseudocode and candidates are not native authority.",
        }
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", root_key)[:160]
        output = semantic.dossier_root / f"{safe_name}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        atomic_text(output, canonical_json(dossier, pretty=True))
        return {"path": output.as_posix(), "sha256": sha256_file(output).upper(), "dossier": dossier}
    finally:
        connection.close()
        stage.close()
