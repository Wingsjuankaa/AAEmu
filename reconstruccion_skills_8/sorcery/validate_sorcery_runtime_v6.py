#!/usr/bin/env python3
"""Validate the AA8-native Sorcery doodad promotion in runtime v6."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any


SORCERY_DIR = Path(__file__).resolve().parent
V5_VALIDATOR_PATH = SORCERY_DIR / "validate_sorcery_runtime_v5.py"
V6_BUILDER_PATH = SORCERY_DIR / "build_sorcery_runtime_v6.py"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


v5 = load_module("sorcery_runtime_v5_validator", V5_VALIDATOR_PATH)
builder = load_module("sorcery_runtime_v6_builder", V6_BUILDER_PATH)

DEFAULT_RUNTIME = builder.DEFAULT_OUTPUT
DEFAULT_MANIFEST = builder.DEFAULT_MANIFEST
DEFAULT_JSON = SORCERY_DIR / "generated" / "sorcery-runtime-acceptance-v6.json"
DEFAULT_CSV = SORCERY_DIR / "generated" / "sorcery-runtime-acceptance-v6.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--base", type=Path, default=builder.DEFAULT_BASE)
    parser.add_argument("--game11", type=Path, default=builder.DEFAULT_GAME11)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    return parser.parse_args(argv)


def quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def compare_base(runtime_path: Path, base_path: Path) -> list[str]:
    errors: list[str] = []
    connection = sqlite3.connect(runtime_path)
    connection.row_factory = sqlite3.Row
    connection.execute("ATTACH DATABASE ? AS base", (str(base_path.resolve()),))
    try:
        runtime_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM main.sqlite_master WHERE type='table'"
            )
        }
        base_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM base.sqlite_master WHERE type='table'"
            )
        }
        if runtime_tables.difference(base_tables) != {"sorcery_doodad_aa8_v6_evidence"}:
            errors.append("unexpected_runtime_tables")
        if base_tables.difference(runtime_tables):
            errors.append("base_tables_missing_from_v6")
        for table in sorted(base_tables.difference({"sorcery_reconstruction_v4_metadata"})):
            q = quoted(table)
            main_count = int(connection.execute(f"SELECT count(*) FROM main.{q}").fetchone()[0])
            base_count = int(connection.execute(f"SELECT count(*) FROM base.{q}").fetchone()[0])
            if main_count != base_count:
                errors.append(f"base_row_count:{table}:{main_count}!={base_count}")
                continue
            if connection.execute(
                f"SELECT * FROM main.{q} EXCEPT SELECT * FROM base.{q} LIMIT 1"
            ).fetchone() is not None:
                errors.append(f"base_forward_difference:{table}")
            if connection.execute(
                f"SELECT * FROM base.{q} EXCEPT SELECT * FROM main.{q} LIMIT 1"
            ).fetchone() is not None:
                errors.append(f"base_reverse_difference:{table}")
        main_meta = {
            str(row[0]): (str(row[1]), str(row[2]))
            for row in connection.execute(
                "SELECT key,value,provenance FROM main.sorcery_reconstruction_v4_metadata"
            )
        }
        base_meta = {
            str(row[0]): (str(row[1]), str(row[2]))
            for row in connection.execute(
                "SELECT key,value,provenance FROM base.sorcery_reconstruction_v4_metadata"
            )
        }
        expected_changed = {
            "sorcery_doodad_authority",
            "sorcery_doodad_structural_candidates",
            "sorcery_doodad_reference_resolution",
        }
        changed = {key for key in set(main_meta) | set(base_meta) if main_meta.get(key) != base_meta.get(key)}
        if changed != expected_changed:
            errors.append(f"metadata_change_scope:{sorted(changed)}")
    finally:
        connection.close()
    return errors


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.runtime, args.manifest, args.base, args.game11):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.get("format_version") != 6:
        errors.append("manifest_format_is_not_v6")
    runtime_hash = builder.sha256_file(args.runtime)
    if runtime_hash != str(manifest.get("output", {}).get("sha256", "")):
        errors.append("runtime_hash_does_not_match_manifest")
    for key, expected in builder.EXPECTED_HASHES.items():
        source_key = "base_manifest" if key == "base_manifest" else key
        actual = str(manifest.get("sources", {}).get(source_key, {}).get("sha256", ""))
        if actual != expected:
            errors.append(f"source_hash:{key}")

    v5_report = v5.build_report(v5.parse_args([]))
    if v5_report["errors"]:
        errors.extend(f"v5:{error}" for error in v5_report["errors"])
    errors.extend(compare_base(args.runtime, args.base))

    selected, decoder = builder.decode_scope(args.game11)
    connection = sqlite3.connect(args.runtime)
    connection.row_factory = sqlite3.Row
    try:
        semantic_rows, counts = builder.compare_runtime(connection, selected)
        stored = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM sorcery_doodad_aa8_v6_evidence ORDER BY table_name,row_id"
            )
        ]
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        connection.close()
    if quick != "ok" or integrity != "ok":
        errors.append(f"sqlite:{quick}/{integrity}")
    if len(stored) != 21:
        errors.append(f"stored_evidence_rows:{len(stored)}")
    manifest_rows = manifest.get("rows", [])
    if semantic_rows != manifest_rows:
        errors.append("manifest_semantic_rows_mismatch")
    expected_decoder = manifest.get("decoder_evidence", {})
    if decoder != expected_decoder:
        errors.append("decoder_evidence_mismatch")
    if counts != manifest.get("scope", {}).get("field_counts"):
        errors.append("field_counts_mismatch")
    classifications: dict[str, int] = {}
    for row in semantic_rows:
        state = str(row["classification"])
        classifications[state] = classifications.get(state, 0) + 1
    if classifications != {
        "aa8_native_exact": 19,
        "aa8_native_with_bounded_string_reference_resolution": 2,
    }:
        errors.append(f"classification_counts:{classifications}")

    report = {
        "format_version": 6,
        "client_build": builder.CLIENT_BUILD,
        "runtime": {"path": str(args.runtime.resolve()), "sha256": runtime_hash},
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "static_runtime_state": "closed" if not v5_report["errors"] else "failed",
            "localization_state": v5_report["summary"]["localization_state"],
            "doodad_native_state": "closed" if not errors else "failed",
            "manual_state": "pending",
        },
        "checks": {
            "native_doodad_rows": len(semantic_rows),
            "native_exact_fields": counts["exact_fields"],
            "reference_resolved_fields": counts["reference_resolved_fields"],
            "runtime_schema_defaults": counts["schema_defaults"],
            "classifications": classifications,
            "v5_exact_localization_rows": v5_report["checks"]["exact_aa8_localization_rows"],
            "v5_exact_catalog_rows": v5_report["checks"]["exact_aa8_rows_compared"],
        },
        "decoder_evidence": decoder,
        "rows": semantic_rows,
        "errors": errors,
        "warnings": warnings,
    }
    return report


def write_report(report: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(builder.canonical_json(report), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("table", "row_id", "classification"))
        for row in report["rows"]:
            writer.writerow((row["table"], row["row_id"], row["classification"]))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    write_report(report, args.json, args.csv)
    print(builder.canonical_json(report["summary"]), end="")
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
