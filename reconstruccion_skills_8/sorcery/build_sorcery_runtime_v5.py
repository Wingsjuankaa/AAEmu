#!/usr/bin/env python3
"""Build Sorcery v5 with exact AA8 English localization closure.

The two live roots 10151/10153 are confirmed AA8 tombstones: the complete
unfiltered skills result omits their parent rows while exact native relations
and the client itself still reference them.  V5 preserves the bounded v4
server materialization, but replaces every available Sorcery skill/buff
localization row with the exact Kakao r558734 compact value.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SORCERY_DIR = Path(__file__).resolve().parent
DEFAULT_CATALOG = (
    ROOT
    / "reconstruccion_skills_8"
    / "native_combat"
    / "generated"
    / "native-combat-catalog-v1.json"
)
DEFAULT_V4_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v4.sqlite3"
)
DEFAULT_V4_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v4.manifest.json"
DEFAULT_AA8_COMPACT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite"
)
DEFAULT_KNOWLEDGE = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite"
)
DEFAULT_OUTPUT = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v5.sqlite3"
)
DEFAULT_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v5.manifest.json"

CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
LIVE_TOMBSTONE_ROOTS = (10151, 10153)
PASSIVE_BUFFS = (536, 962, 963, 2910, 7566, 7567)
DOODAD_BUFFS = (25646, 25647)
EXPECTED_HASHES = {
    "v4_runtime": "5496A350F6A18D19547DFA53EB8E7E8E79E5BC6ED8880698EAAE6114A6743011",
    "v4_manifest": "FBC084C38AD47E3AF5EE0EA3A1C27750F5F8C2BDA1461992D0EA5E93E77F4987",
    "aa8_compact": "4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57",
    "knowledge": "92CDF5D1EB16DAF0C4D5ABFCB80B510DFDF827708D4F8087235CCFACE3CE3C4F",
    "catalog": "9849E3CF5C52702CC0CEB71B9DBBFB343E29880924DA4AFF13C3C5F33B2DD027",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", type=Path, default=DEFAULT_V4_RUNTIME)
    parser.add_argument("--runtime-manifest", type=Path, default=DEFAULT_V4_MANIFEST)
    parser.add_argument("--aa8-compact", type=Path, default=DEFAULT_AA8_COMPACT)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def validate_source(path: Path, expected: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Unexpected source SHA-256 for {path}: {actual}")
    return {"path": str(path.resolve()), "sha256": actual}


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def sorcery_ids(catalog: dict[str, Any]) -> tuple[set[int], set[int]]:
    skill_ids = set(LIVE_TOMBSTONE_ROOTS)
    buff_ids = set(PASSIVE_BUFFS) | set(DOODAD_BUFFS) | {95}
    for status in catalog["skill_status"]:
        if int(status["ability_id"]) != 7:
            continue
        for skill_id in status["closure_skill_ids"]:
            skill_ids.add(int(skill_id))
            table_ids = catalog["skill_table_ids"][str(skill_id)]
            buff_ids.update(int(value) for value in table_ids.get("buffs", ()))
    return skill_ids, buff_ids


def validate_tombstone_roots(
    compact: sqlite3.Connection, knowledge: sqlite3.Connection
) -> dict[str, Any]:
    result = {}
    for skill_id in LIVE_TOMBSTONE_ROOTS:
        if compact.execute("SELECT 1 FROM skills WHERE id=?", (skill_id,)).fetchone():
            raise RuntimeError(f"AA8 tombstone root unexpectedly materialized: {skill_id}")
        entity = knowledge.execute(
            "SELECT lifecycle,state,authority,provenance,evidence_json FROM entities "
            "WHERE entity_key=?",
            (f"skill:{skill_id}",),
        ).fetchone()
        if entity is None or tuple(entity[:2]) != ("tombstone", "tombstone"):
            raise RuntimeError(f"AA8 lifecycle gate changed for {skill_id}: {entity}")
        incoming = int(
            knowledge.execute(
                "SELECT COUNT(*) FROM relations WHERE dst_entity_key=? "
                "AND state='confirmed' AND authority='client_native'",
                (f"skill:{skill_id}",),
            ).fetchone()[0]
        )
        if incoming <= 0:
            raise RuntimeError(f"AA8 tombstone root has no confirmed references: {skill_id}")
        result[str(skill_id)] = {
            "compact_skills_row": "absent_in_complete_unfiltered_result",
            "lifecycle": str(entity["lifecycle"]),
            "state": str(entity["state"]),
            "authority": str(entity["authority"]),
            "provenance": str(entity["provenance"]),
            "confirmed_incoming_relations": incoming,
            "catalog_evidence_sha256": text_sha256(str(entity["evidence_json"])),
            "materialization_policy": (
                "bounded_server_candidate_parent_with_exact_aa8_descendants_and_localization"
            ),
        }
    return result


def collect_localizations(
    compact: sqlite3.Connection,
    skill_ids: set[int],
    buff_ids: set[int],
) -> list[dict[str, Any]]:
    rows = []
    for table, ids in (("skills", skill_ids), ("buffs", buff_ids)):
        placeholders = ",".join("?" for _ in ids)
        for row in compact.execute(
            "SELECT tbl_name,tbl_column_name,idx,text,locale FROM localized_texts "
            f"WHERE tbl_name=? AND locale='en_us' AND idx IN ({placeholders}) "
            "ORDER BY tbl_name,idx,tbl_column_name",
            (table, *sorted(ids)),
        ):
            rows.append(dict(row))
    if not rows:
        raise RuntimeError("AA8 Sorcery localization closure is empty")
    return rows


def apply_localizations(
    connection: sqlite3.Connection, rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], Counter[str]]:
    evidence = []
    states: Counter[str] = Counter()
    for row in rows:
        key = (str(row["tbl_name"]), str(row["tbl_column_name"]), int(row["idx"]))
        previous = connection.execute(
            "SELECT en_us FROM localized_texts WHERE tbl_name=? "
            "AND tbl_column_name=? AND idx=?",
            key,
        ).fetchone()
        if previous is None:
            prior_state = "missing"
        elif str(previous[0]) == str(row["text"]):
            prior_state = "exact"
        else:
            prior_state = "different"
        states[prior_state] += 1
        connection.execute(
            "DELETE FROM localized_texts WHERE tbl_name=? AND tbl_column_name=? AND idx=?",
            key,
        )
        connection.execute(
            "INSERT INTO localized_texts(tbl_name,tbl_column_name,idx,en_us) "
            "VALUES(?,?,?,?)",
            (*key, str(row["text"])),
        )
        evidence.append(
            {
                "tbl_name": key[0],
                "tbl_column_name": key[1],
                "idx": key[2],
                "locale": "en_us",
                "prior_state": prior_state,
                "text_sha256": text_sha256(str(row["text"])),
                "authority": "aa8_compact_r558734_exact_localization",
            }
        )
    return evidence, states


def verify_localizations(
    connection: sqlite3.Connection, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    errors = []
    for row in rows:
        actual = connection.execute(
            "SELECT en_us FROM localized_texts WHERE tbl_name=? "
            "AND tbl_column_name=? AND idx=?",
            (row["tbl_name"], row["tbl_column_name"], int(row["idx"])),
        ).fetchall()
        if len(actual) != 1 or str(actual[0][0]) != str(row["text"]):
            errors.append(
                f"{row['tbl_name']}.{row['idx']}.{row['tbl_column_name']}"
            )
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        errors.append(f"sqlite:{quick}/{integrity}")
    if errors:
        raise RuntimeError("Sorcery v5 verification failed: " + ", ".join(errors))
    return {
        "localized_rows_exact": len(rows),
        "quick_check": quick,
        "integrity_check": integrity,
        "duplicate_runtime_keys": 0,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "runtime_carrier": validate_source(
            args.runtime_carrier, EXPECTED_HASHES["v4_runtime"]
        ),
        "runtime_manifest": validate_source(
            args.runtime_manifest, EXPECTED_HASHES["v4_manifest"]
        ),
        "aa8_compact": validate_source(args.aa8_compact, EXPECTED_HASHES["aa8_compact"]),
        "knowledge": validate_source(args.knowledge, EXPECTED_HASHES["knowledge"]),
        "catalog": validate_source(args.catalog, EXPECTED_HASHES["catalog"]),
    }
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    skill_ids, buff_ids = sorcery_ids(catalog)
    compact = ro(args.aa8_compact)
    knowledge = ro(args.knowledge)
    try:
        tombstones = validate_tombstone_roots(compact, knowledge)
        localizations = collect_localizations(compact, skill_ids, buff_ids)
    finally:
        compact.close()
        knowledge.close()

    output = args.output.resolve()
    if output == args.runtime_carrier.resolve():
        raise ValueError("Output must not replace its runtime carrier")
    output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.runtime_carrier, output)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        evidence, prior_states = apply_localizations(connection, localizations)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS sorcery_reconstruction_v5_metadata("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance TEXT NOT NULL)"
        )
        metadata = {
            "client_build": CLIENT_BUILD,
            "base_runtime": EXPECTED_HASHES["v4_runtime"],
            "localization_authority": "aa8_compact_r558734_exact",
            "localized_skill_ids": ",".join(str(value) for value in sorted(skill_ids)),
            "localized_buff_ids": ",".join(str(value) for value in sorted(buff_ids)),
            "live_root_lifecycle": "10151:tombstone,10153:tombstone",
            "live_root_parent_policy": "bounded_crosswalk_candidate",
        }
        connection.executemany(
            "INSERT INTO sorcery_reconstruction_v5_metadata(key,value,provenance) "
            "VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET "
            "value=excluded.value,provenance=excluded.provenance",
            [
                (key, value, "aa8_sorcery_v5_localization_closure")
                for key, value in sorted(metadata.items())
            ],
        )
        connection.commit()
        verification = verify_localizations(connection, localizations)
        connection.execute("VACUUM")
    except Exception:
        connection.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        connection.close()

    manifest = {
        "format_version": 5,
        "client_build": CLIENT_BUILD,
        "authority": {
            "skill_and_buff_localization": "aa8_compact_r558734_exact",
            "live_root_identity_and_reachability": "aa8_client_native",
            "live_root_parent_properties": "bounded_aa10_crosswalk_candidate",
            "live_root_descendants": "aa8_client_native",
            "balance_protocol_and_behavior": "unchanged_from_v4",
        },
        "sources": sources,
        "scope": {
            "skill_ids": sorted(skill_ids),
            "buff_ids": sorted(buff_ids),
            "localized_rows": len(localizations),
            "prior_state_counts": dict(sorted(prior_states.items())),
        },
        "tombstone_roots": tombstones,
        "localization_rows": evidence,
        "verification": verification,
        "output": {"path": str(output), "sha256": sha256_file(output)},
    }
    args.manifest.write_text(canonical(manifest), encoding="utf-8")
    print(
        canonical(
            {
                "manifest": str(args.manifest.resolve()),
                "manifest_sha256": sha256_file(args.manifest),
                "output": str(output),
                "output_sha256": manifest["output"]["sha256"],
                "scope": manifest["scope"],
                "verification": verification,
            }
        ),
        end="",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    return 0 if build(parse_args(argv)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
