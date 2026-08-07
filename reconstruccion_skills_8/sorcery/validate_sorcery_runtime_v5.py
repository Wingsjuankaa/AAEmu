#!/usr/bin/env python3
"""Validate Sorcery v5 behavior closure plus exact AA8 localization closure."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).with_name("validate_sorcery_runtime_v4.py")
SPEC = importlib.util.spec_from_file_location("sorcery_runtime_v4_validator", SCRIPT)
base = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(base)

SORCERY_DIR = Path(__file__).resolve().parent
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v5.sqlite3"
)
DEFAULT_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v5.manifest.json"
DEFAULT_BASE_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v4.manifest.json"
DEFAULT_AA8_COMPACT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite"
)
DEFAULT_JSON = SORCERY_DIR / "generated" / "sorcery-runtime-acceptance-v5.json"
DEFAULT_CSV = SORCERY_DIR / "generated" / "sorcery-runtime-acceptance-v5.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=base.DEFAULT_CATALOG)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--base-manifest", type=Path, default=DEFAULT_BASE_MANIFEST)
    parser.add_argument("--audit", type=Path, default=base.DEFAULT_AUDIT)
    parser.add_argument("--aa8-compact", type=Path, default=DEFAULT_AA8_COMPACT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    return parser.parse_args(argv)


def validate_exact_localizations(
    runtime: sqlite3.Connection,
    compact: sqlite3.Connection,
    manifest: dict[str, Any],
) -> tuple[list[str], Counter[str]]:
    errors = []
    counts: Counter[str] = Counter()
    records = manifest.get("localization_rows", [])
    if len(records) != 222:
        errors.append(f"localization_manifest_count:{len(records)}!=222")
    seen = set()
    for record in records:
        key = (
            str(record["tbl_name"]),
            str(record["tbl_column_name"]),
            int(record["idx"]),
        )
        if key in seen:
            errors.append(f"duplicate_localization_manifest_key:{key}")
            continue
        seen.add(key)
        source = compact.execute(
            "SELECT text FROM localized_texts WHERE tbl_name=? "
            "AND tbl_column_name=? AND idx=? AND locale='en_us'",
            key,
        ).fetchall()
        actual = runtime.execute(
            "SELECT en_us FROM localized_texts WHERE tbl_name=? "
            "AND tbl_column_name=? AND idx=?",
            key,
        ).fetchall()
        if len(source) != 1:
            errors.append(f"aa8_localization_source_cardinality:{key}:{len(source)}")
            continue
        if len(actual) != 1:
            errors.append(f"runtime_localization_cardinality:{key}:{len(actual)}")
            continue
        source_text = str(source[0][0])
        runtime_text = str(actual[0][0])
        digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest().upper()
        if digest != str(record["text_sha256"]):
            errors.append(f"localization_manifest_digest:{key}")
        if runtime_text != source_text:
            errors.append(f"runtime_localization_mismatch:{key}")
        else:
            counts[key[0]] += 1
    return errors, counts


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (
        args.catalog,
        args.runtime,
        args.manifest,
        args.base_manifest,
        args.audit,
        args.aa8_compact,
    ):
        if not path.is_file():
            raise FileNotFoundError(path)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    base_manifest = json.loads(args.base_manifest.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    runtime_hash = base.sha256_file(args.runtime)
    errors: list[str] = []
    warnings: list[str] = []

    if manifest.get("format_version") != 5:
        errors.append(f"manifest_format:{manifest.get('format_version')}!=5")
    if manifest.get("client_build") != base.CLIENT_BUILD:
        errors.append(f"manifest_client_build:{manifest.get('client_build')}")
    if str(manifest.get("output", {}).get("sha256", "")).upper() != runtime_hash:
        errors.append("runtime_hash_does_not_match_v5_manifest")
    if base_manifest.get("format_version") != 4:
        errors.append("base_manifest_is_not_v4")
    if audit.get("summary", {}).get("blocked_root_count") != 0:
        errors.append("handler_audit_has_blocked_roots")

    runtime = sqlite3.connect(f"file:{args.runtime.resolve().as_posix()}?mode=ro", uri=True)
    compact = sqlite3.connect(
        f"file:{args.aa8_compact.resolve().as_posix()}?mode=ro", uri=True
    )
    runtime.row_factory = sqlite3.Row
    compact.row_factory = sqlite3.Row
    try:
        quick = str(runtime.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(runtime.execute("PRAGMA integrity_check").fetchone()[0])
        if quick != "ok" or integrity != "ok":
            errors.append(f"sqlite_integrity:{quick}/{integrity}")

        static_rows = base.static_ability_rows(catalog)
        row_maps = base.catalog_row_maps(catalog)
        static_closures: dict[int, dict[str, set[int]]] = {}
        all_static: dict[str, set[int]] = defaultdict(set)
        for status_row in static_rows:
            root_id = int(status_row["skill_id"])
            closure = base.static_root_closure(catalog, status_row)
            static_closures[root_id] = closure
            base.merge_ids(all_static, closure)
        native_errors, compared = base.compare_native_rows(runtime, row_maps, all_static)
        errors.extend(native_errors)

        selected: dict[str, set[int]] = defaultdict(set)
        base.merge_ids(selected, all_static)
        base.merge_ids(selected, base.manifest_ids(base_manifest))
        live_closures = {
            root_id: base.discover_live_closure(runtime, root_id)
            for root_id in base.LIVE_ROOTS
        }
        for closure in live_closures.values():
            base.merge_ids(selected, closure)
        for table, ids in selected.items():
            for row_id in ids:
                if not base.row_exists(runtime, table, row_id):
                    errors.append(f"selected_runtime_row_missing:{table}.{row_id}")

        reference_errors, checked_references = base.validate_references(runtime, selected)
        errors.extend(reference_errors)
        status_errors, statuses = base.validate_statuses(runtime, static_rows)
        errors.extend(status_errors)
        name_errors, english_names = base.validate_localization(runtime)
        errors.extend(name_errors)
        passive_errors, passive_rows = base.validate_passives(runtime, audit)
        errors.extend(passive_errors)
        doodad_errors, doodad_report = base.validate_doodads(runtime)
        errors.extend(doodad_errors)
        localization_errors, localization_counts = validate_exact_localizations(
            runtime, compact, manifest
        )
        errors.extend(localization_errors)

        tombstones = manifest.get("tombstone_roots", {})
        expected_incoming = {"10151": 20, "10153": 18}
        for skill_id, incoming in expected_incoming.items():
            record = tombstones.get(skill_id, {})
            if record.get("lifecycle") != "tombstone":
                errors.append(f"tombstone_lifecycle_missing:{skill_id}")
            if record.get("confirmed_incoming_relations") != incoming:
                errors.append(f"tombstone_relation_count:{skill_id}")
            if compact.execute("SELECT 1 FROM skills WHERE id=?", (int(skill_id),)).fetchone():
                errors.append(f"tombstone_present_in_aa8_skills:{skill_id}")

        roots = []
        for root_id in base.VISIBLE_ROOTS:
            if root_id in base.LIVE_ROOTS:
                closure = live_closures[root_id]
                source = "aa8_tombstone_identity_plus_bounded_parent_plus_aa8_descendants"
            else:
                closure = static_closures[root_id]
                source = "aa8_native_catalog"
            root = base.root_report(
                root_id,
                closure,
                english_names,
                statuses.get(root_id, "missing"),
                source,
            )
            root["localization_state"] = "exact_aa8_compact_r558734"
            roots.append(root)

        crosswalk_classes = Counter()
        for root in audit.get("roots", []):
            crosswalk_classes.update(root.get("crosswalk_classifications", {}))
        if crosswalk_classes.get("conflict", 0):
            warnings.append(
                "Three AA10 comparison conflicts remain isolated from the exact AA8 runtime rows."
            )
        errors = sorted(set(errors))
        return {
            "format_version": 5,
            "client_build": base.CLIENT_BUILD,
            "authority": manifest["authority"],
            "sources": {
                "catalog": {"path": str(args.catalog.resolve()), "sha256": base.sha256_file(args.catalog)},
                "runtime": {"path": str(args.runtime.resolve()), "sha256": runtime_hash},
                "manifest": {"path": str(args.manifest.resolve()), "sha256": base.sha256_file(args.manifest)},
                "base_manifest": {"path": str(args.base_manifest.resolve()), "sha256": base.sha256_file(args.base_manifest)},
                "handler_audit": {"path": str(args.audit.resolve()), "sha256": base.sha256_file(args.audit)},
                "aa8_compact": {"path": str(args.aa8_compact.resolve()), "sha256": base.sha256_file(args.aa8_compact)},
            },
            "roots": roots,
            "passives": {
                "state": "accepted_live_and_runtime_resolved" if not passive_errors else "failed",
                "templates": passive_rows,
            },
            "doodads": doodad_report,
            "tombstone_roots": tombstones,
            "localization": {
                "state": "exact_aa8_compact_r558734" if not localization_errors else "failed",
                "row_counts": dict(sorted(localization_counts.items())),
                "total_rows": sum(localization_counts.values()),
                "prior_state_counts": manifest["scope"]["prior_state_counts"],
            },
            "crosswalk_classifications": dict(sorted(crosswalk_classes.items())),
            "warnings": warnings,
            "errors": errors,
            "checks": {
                "quick_check": quick,
                "integrity_check": integrity,
                "exact_aa8_rows_compared": compared,
                "selected_runtime_rows": sum(len(ids) for ids in selected.values()),
                "references_checked": checked_references,
                "exact_aa8_localization_rows": sum(localization_counts.values()),
                "tombstone_roots": len(tombstones),
            },
            "summary": {
                "root_count": len(roots),
                "passive_count": len(passive_rows),
                "error_count": len(errors),
                "warning_count": len(warnings),
                "static_runtime_state": "closed" if not errors else "failed",
                "localization_state": "closed" if not localization_errors else "failed",
                "manual_live_state": "pending",
            },
        }
    finally:
        compact.close()
        runtime.close()


def write_csv(path: Path, report: dict[str, Any]) -> None:
    columns = (
        "skill_id",
        "english_name",
        "source",
        "runtime_status",
        "closure_tables",
        "closure_rows",
        "localization_state",
        "static_payload_state",
        "acceptance_state",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in report["roots"]:
            writer.writerow({key: row[key] for key in columns})


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(base.canonical(report), encoding="utf-8")
    write_csv(args.output_csv, report)
    print(base.canonical(report["summary"]), end="")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
