#!/usr/bin/env python3
"""Materialize the evidenced AA8 Insulating Lens charge contract over v7."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
DEFAULT_BASE = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v7.sqlite3"
)
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_AA10 = Path(
    r"E:\AAEmu-Research\test\ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18\game\db\game.sqlite3"
)
DEFAULT_WIKI = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\stage70-wiki-cache"
    r"\specializations\na-en\sorcery\skills\10153.html"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v8.sqlite3"
)
DEFAULT_MANIFEST = Path(__file__).with_name("generated") / "sorcery-specialization-v8.manifest.json"

EXPECTED_HASHES = {
    "base": "6680B69159285BC817732DAD24707BB1A4B2625C77718FEA9A02E72BD8E17159",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "aa10": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
    "wiki": "BE74FE80728865A1D1DE7B1CCB7AEC9638ABF0250B92797C791481E5DEDE06DE",
}

AA8_ROW = {
    "id": 1,
    "charge_buff_id": 95,
    "damage_type_id": 2,
    "dps_inc_multiplier": 1.5,
    "dps_multiplier": 1.0,
    "fixed_max": 0,
    "fixed_min": 0,
    "level_md": 3.0,
    "level_va_end": 1,
    "level_va_start": 1,
    "percent_max": 100,
    "percent_min": 0,
    "use_current_health": 0,
    "use_dps_charge": 1,
    "use_fixed_charge": 0,
    "use_level_charge": 1,
    "use_mainhand_weapon": 0,
    "use_offhand_weapon": 0,
    "use_percent_charge": 0,
    "use_ranged_weapon": 0,
}

PROMOTED_ROW = {
    **AA8_ROW,
    "percent_max": 5,
    "percent_min": 5,
    "use_percent_charge": 1,
    "percent_damage_resource_type_id": 4,
    "use_source_health": 0,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def verify_hash(path: Path, expected: str) -> str:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Unexpected SHA-256 for {path}: {actual} != {expected}")
    return actual


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--aa10", type=Path, default=DEFAULT_AA10)
    parser.add_argument("--wiki", type=Path, default=DEFAULT_WIKI)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def row_dict(connection: sqlite3.Connection, sql: str, args: tuple[Any, ...]) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    row = connection.execute(sql, args).fetchone()
    if row is None:
        raise RuntimeError(f"Required evidence row missing: {sql} {args}")
    return dict(row)


def validate_sources(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.base, args.crosswalk, args.aa10, args.wiki):
        if not path.is_file():
            raise FileNotFoundError(path)
    hashes = {
        key: verify_hash(getattr(args, key), expected)
        for key, expected in EXPECTED_HASHES.items()
    }

    with sqlite3.connect(args.base) as connection:
        aa8 = row_dict(connection, "SELECT * FROM extend_charge_effects WHERE id=?", (1,))
        if aa8 != AA8_ROW:
            raise RuntimeError(f"Unexpected AA8 ExtendCharge row: {aa8}")
        skill = row_dict(
            connection,
            "SELECT id,ability_id,ability_level,casting_inc,casting_time FROM skills WHERE id=?",
            (10153,),
        )
        localization = row_dict(
            connection,
            "SELECT en_us FROM localized_texts "
            "WHERE tbl_name='skills' AND tbl_column_name='desc' AND idx=?",
            (10153,),
        )["en_us"]
        if "#{avg_damage}#{detail_spell_damage}" not in localization:
            raise RuntimeError("AA8 Insulating Lens tooltip placeholders changed")

    with sqlite3.connect(args.crosswalk) as connection:
        comparison = row_dict(
            connection,
            "SELECT classification,relation_state,property_state,exact_columns_json,"
            "changed_property_columns_json,aa8_locator,aa10_locator "
            "FROM row_comparisons WHERE table_name='extend_charge_effects' AND aa8_id='1'",
            (),
        )
        if comparison["classification"] != "stable_id_changed_properties":
            raise RuntimeError(f"Unexpected crosswalk classification: {comparison}")
        exact = set(json.loads(comparison["exact_columns_json"]))
        required_exact = {
            "charge_buff_id", "damage_type_id", "dps_inc_multiplier", "dps_multiplier",
            "fixed_max", "fixed_min", "level_md", "level_va_end", "level_va_start",
            "use_dps_charge", "use_fixed_charge", "use_level_charge",
            "use_mainhand_weapon", "use_offhand_weapon", "use_ranged_weapon",
        }
        if not required_exact.issubset(exact):
            raise RuntimeError("Crosswalk does not preserve the AA8 charge identity/formula spine")

    with sqlite3.connect(args.aa10) as connection:
        aa10 = row_dict(connection, "SELECT * FROM extend_charge_effects WHERE id=?", (1,))
        boolean_columns = {
            "use_dps_charge", "use_fixed_charge", "use_level_charge",
            "use_mainhand_weapon", "use_offhand_weapon", "use_percent_charge",
            "use_ranged_weapon", "use_source_health",
        }
        for key, expected in PROMOTED_ROW.items():
            if key == "use_current_health":
                continue
            actual = aa10.get(key)
            if key in boolean_columns:
                actual = 1 if str(actual).lower() in {"1", "t", "true"} else 0
            if actual != expected:
                raise RuntimeError(f"Unexpected AA10 ExtendCharge value {key}: {aa10.get(key)}")
        enum_row = row_dict(
            connection,
            "SELECT id,name FROM enum_percent_damage_resource_types WHERE id=?",
            (4,),
        )
        if enum_row != {"id": 4, "name": "max_mana"}:
            raise RuntimeError(f"Unexpected resource enum: {enum_row}")

    wiki = args.wiki.read_text(encoding="utf-8")
    for fragment in ("792 + 225% Magic Attack", "5%", "max Mana"):
        if fragment not in wiki:
            raise RuntimeError(f"Missing AA8-compatible visible corroboration: {fragment}")

    return {
        "hashes": hashes,
        "aa8_row": aa8,
        "aa10_row": aa10,
        "skill": skill,
        "localization": localization,
        "crosswalk": comparison,
        "resource_enum": enum_row,
    }


def add_column(connection: sqlite3.Connection, name: str, declaration: str) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(extend_charge_effects)")}
    if name not in columns:
        connection.execute(
            f'ALTER TABLE extend_charge_effects ADD COLUMN "{name}" {declaration}'
        )


def materialize(connection: sqlite3.Connection, evidence: dict[str, Any]) -> None:
    add_column(connection, "percent_damage_resource_type_id", "INTEGER DEFAULT 0 NOT NULL")
    add_column(connection, "use_source_health", "BOOLEAN DEFAULT 0 NOT NULL")
    connection.execute(
        "UPDATE extend_charge_effects SET percent_min=5,percent_max=5,"
        "use_percent_charge=1,percent_damage_resource_type_id=4,use_source_health=0 "
        "WHERE id=1"
    )
    actual = row_dict(connection, "SELECT * FROM extend_charge_effects WHERE id=?", (1,))
    if actual != PROMOTED_ROW:
        raise RuntimeError(f"Materialized ExtendCharge row mismatch: {actual}")

    connection.execute(
        "CREATE TABLE IF NOT EXISTS sorcery_extend_charge_v8_evidence("
        "evidence_key TEXT PRIMARY KEY NOT NULL,evidence_json TEXT NOT NULL) WITHOUT ROWID"
    )
    connection.execute("DELETE FROM sorcery_extend_charge_v8_evidence")
    payloads = {
        "aa8_native_descriptor": evidence["aa8_row"],
        "aa8_skill_contract": evidence["skill"],
        "aa8_tooltip_template": {"en_us": evidence["localization"]},
        "aa10_stable_row": evidence["aa10_row"],
        "aa10_resource_enum": evidence["resource_enum"],
        "crosswalk_classification": evidence["crosswalk"],
        "promoted_runtime_row": actual,
        "native_formula_contract": {
            "level_base": "level_dps * (rank_scale + 1) * level_md",
            "dps_charge": "effective_casting_time * (dps_stat/1000*dps_inc_multiplier + weapon_dps/1000*dps_multiplier) / 1000",
            "insulating_lens_visible_level_50": "792 + 225% Magic Attack + 5% Max Mana",
            "aa8_x2game_tooltip_functions": [
                "FUN_396bc6a0", "FUN_396b4f80", "FUN_396b3df0", "FUN_396b3c70",
            ],
        },
    }
    connection.executemany(
        "INSERT INTO sorcery_extend_charge_v8_evidence VALUES(?,?)",
        [
            (key, json.dumps(value, ensure_ascii=False, sort_keys=True))
            for key, value in sorted(payloads.items())
        ],
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    evidence = validate_sources(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.base, args.output)
    with sqlite3.connect(args.output) as connection:
        materialize(connection, evidence)
        connection.commit()
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        evidence_rows = int(
            connection.execute("SELECT count(*) FROM sorcery_extend_charge_v8_evidence").fetchone()[0]
        )
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite verification failed: {quick}/{integrity}")

    manifest = {
        "format_version": 8,
        "client_build": CLIENT_BUILD,
        "sources": {
            key: {"path": str(getattr(args, key).resolve()), "sha256": value}
            for key, value in evidence["hashes"].items()
        },
        "authority": {
            "formula_spine": "aa8_native_descriptor_and_tooltip_evaluator",
            "percent_contract": "aa8_visible_semantics_corroborated_by_stable_aa10_crosswalk_row",
            "aa10_role": "mandatory_gap_reduction_not_balance_authority",
            "manual_gate": "shield_absorption_and_break_trigger_remain_live_acceptance_items",
        },
        "scope": {
            "skill_id": 10153,
            "effect_id": 68337,
            "extend_charge_id": 1,
            "charge_buff_id": 95,
            "evidence_rows": evidence_rows,
        },
        "promoted_runtime_row": PROMOTED_ROW,
        "verification": {"quick_check": quick, "integrity_check": integrity},
        "output": {"path": str(args.output.resolve()), "sha256": sha256_file(args.output)},
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(canonical_json(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    manifest = build(parse_args())
    print(canonical_json({"output": manifest["output"], "scope": manifest["scope"]}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
