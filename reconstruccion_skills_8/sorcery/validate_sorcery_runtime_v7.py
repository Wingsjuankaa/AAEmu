#!/usr/bin/env python3
"""Validate the exact AA8 heir-skill catalogue added by Sorcery runtime v7."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sqlite3
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
BUILDER_PATH = HERE / "build_sorcery_runtime_v7.py"
V6_VALIDATOR_PATH = HERE / "validate_sorcery_runtime_v6.py"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


builder = load_module("sorcery_runtime_v7_builder", BUILDER_PATH)
v6 = load_module("sorcery_runtime_v6_validator", V6_VALIDATOR_PATH)
DEFAULT_JSON = HERE / "generated" / "sorcery-runtime-acceptance-v7.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=builder.DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=builder.DEFAULT_MANIFEST)
    parser.add_argument("--base", type=Path, default=builder.DEFAULT_BASE)
    parser.add_argument("--game11", type=Path, default=builder.DEFAULT_GAME11)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    return parser.parse_args(argv)


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def compare_unchanged_tables(runtime: Path, base: Path) -> list[str]:
    errors: list[str] = []
    db = sqlite3.connect(runtime)
    db.execute("ATTACH DATABASE ? AS base", (str(base.resolve()),))
    try:
        main_tables = {row[0] for row in db.execute(
            "SELECT name FROM main.sqlite_master WHERE type='table'"
        )}
        base_tables = {row[0] for row in db.execute(
            "SELECT name FROM base.sqlite_master WHERE type='table'"
        )}
        expected_new = {
            "heir_levels",
            "heir_skills",
            "heir_skill_details",
            "sorcery_heir_aa8_v7_evidence",
        }
        if main_tables - base_tables != expected_new:
            errors.append(f"unexpected_new_tables:{sorted(main_tables - base_tables)}")
        if base_tables - main_tables:
            errors.append(f"missing_base_tables:{sorted(base_tables - main_tables)}")
        for table in sorted(base_tables):
            q = quote(table)
            if db.execute(f"SELECT * FROM main.{q} EXCEPT SELECT * FROM base.{q} LIMIT 1").fetchone():
                errors.append(f"base_forward_difference:{table}")
            if db.execute(f"SELECT * FROM base.{q} EXCEPT SELECT * FROM main.{q} LIMIT 1").fetchone():
                errors.append(f"base_reverse_difference:{table}")
    finally:
        db.close()
    return errors


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.runtime, args.manifest, args.base, args.game11):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    decoded, decoder = builder.decode_heir_results(args.game11)
    mapping = builder.validate_sorcery_mapping(decoded)
    errors = compare_unchanged_tables(args.runtime, args.base)
    v6_report = v6.build_report(v6.parse_args([]))
    errors.extend("v6:" + error for error in v6_report["errors"])
    if manifest.get("format_version") != 7:
        errors.append("manifest_format_is_not_v7")
    runtime_hash = builder.sha256_file(args.runtime)
    if runtime_hash != manifest.get("output", {}).get("sha256"):
        errors.append("runtime_hash_does_not_match_manifest")
    if decoder != manifest.get("decoder_evidence"):
        errors.append("decoder_evidence_mismatch")
    if mapping != manifest.get("sorcery_mapping"):
        errors.append("sorcery_mapping_mismatch")

    db = sqlite3.connect(args.runtime)
    db.row_factory = sqlite3.Row
    try:
        actual = {
            table: [dict(row) for row in db.execute(f"SELECT * FROM {quote(table)} ORDER BY id")]
            for table in ("heir_levels", "heir_skills", "heir_skill_details")
        }
        evidence_count = db.execute(
            "SELECT count(*) FROM sorcery_heir_aa8_v7_evidence"
        ).fetchone()[0]
        quick = db.execute("PRAGMA quick_check").fetchone()[0]
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        db.close()
    expected_skills = [dict(row, enable="t") for row in decoded["heir_skills"]]
    # AA8's loader filters the literal text value 't'; preserve it byte-for-byte.
    if actual["heir_levels"] != decoded["heir_levels"]:
        errors.append("runtime_heir_levels_mismatch")
    if actual["heir_skills"] != expected_skills:
        errors.append("runtime_heir_skills_mismatch")
    if actual["heir_skill_details"] != decoded["heir_skill_details"]:
        errors.append("runtime_heir_skill_details_mismatch")
    if evidence_count != 308:
        errors.append(f"evidence_count:{evidence_count}")
    if quick != "ok" or integrity != "ok":
        errors.append(f"sqlite:{quick}/{integrity}")
    return {
        "format_version": 7,
        "client_build": builder.CLIENT_BUILD,
        "runtime": {"path": str(args.runtime.resolve()), "sha256": runtime_hash},
        "summary": {
            "errors": len(errors),
            "aa8_heir_catalogue": "closed" if not errors else "failed",
            "manual_ancestral_acceptance": "pending",
            "base_active_runtime": v6_report["summary"]["static_runtime_state"],
        },
        "checks": {
            "heir_levels": len(decoded["heir_levels"]),
            "heir_skills": len(decoded["heir_skills"]),
            "heir_skill_details": len(decoded["heir_skill_details"]),
            "sorcery_heir_families": len(mapping),
            "sorcery_successors": sum(len(row["successors"]) for row in mapping),
            "evidence_rows": evidence_count,
        },
        "decoder_evidence": decoder,
        "sorcery_mapping": mapping,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(builder.canonical_json(report), encoding="utf-8")
    print(builder.canonical_json(report["summary"]), end="")
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
