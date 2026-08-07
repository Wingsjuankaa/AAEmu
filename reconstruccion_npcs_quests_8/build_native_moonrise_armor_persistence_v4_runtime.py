#!/usr/bin/env python3
"""Build the AA8 Moonrise armor-crate and direct-save closure V4."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
SKILL_EXTRACTOR = ROOT / "reconstruccion_skills_8" / "extract_battlerage_manifest.py"
AUTHORITY = "ArcheAge Kakao 8.0.3.12 r558734"
PHASE = "native-moonrise-armor-persistence-v4-runtime"

BOX_IDS = (47982, 47983, 47984)
BOX_SKILL_IDS = (42225, 42227, 42229)
SKILL_EFFECT_IDS = (59713, 59715, 59717)
EFFECT_IDS = (78589, 78591, 78593)
GAIN_EFFECT_IDS = (4215, 4217, 4219)
LOOT_PACK_IDS = (12950, 12952, 12954)
RESULT_ITEMS = {
    47982: (48015, 48016, 48017, 48019),
    47983: (48022, 48023, 48024, 48026),
    47984: (48029, 48030, 48031, 48033),
}

EXPECTED_HASHES = {
    "base_runtime": "171AABCAC72D1333439433396B70728F9786BB73E0A3054FA2A56E467EC53203",
    "client_compact": "4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57",
    "game11": "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
    "item_47982_dossier": "FBF297FB764CD259708FB1FD74823427D263DAC6546FE623E3C7D66E1C8CE1B6",
    "item_47983_dossier": "AAE7FB7ABEEA8A6486A21260F4821588954E440F862E98E002A88BEEA55C36D2",
    "item_47984_dossier": "525A9E96C411E79C0E2E5B76AD780DF287E0FC45607ECBE9123BE1FBE4E8A062",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require_hash(label: str, path: Path) -> str:
    actual = sha256(path)
    if actual != EXPECTED_HASHES[label]:
        raise RuntimeError(
            f"{label} hash mismatch: expected {EXPECTED_HASHES[label]}, got {actual}: {path}"
        )
    return actual


def load_skill_extractor():
    spec = importlib.util.spec_from_file_location("aa8_v4_skills", SKILL_EXTRACTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load skill extractor: {SKILL_EXTRACTOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_rows(
    connection: sqlite3.Connection, table: str, identifiers: Iterable[int]
) -> list[dict[str, Any]]:
    identifiers = tuple(identifiers)
    placeholders = ",".join("?" for _ in identifiers)
    connection.row_factory = sqlite3.Row
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {table} WHERE id IN ({placeholders}) ORDER BY id",
            identifiers,
        )
    ]


def extract_box_rows(
    client_compact: Path, game11: Path
) -> tuple[dict[str, list[dict[str, Any]]], dict[int, tuple[int, ...]]]:
    relationships = load_skill_extractor().extract_client_relationships(game11)
    skill_effects = [
        dict(row)
        for row in relationships["skill_effects"]
        if int(row["skill_id"]) in BOX_SKILL_IDS
    ]
    for row in skill_effects:
        if "start_combat_resource" in row:
            row["start_high_ability_resource"] = row.pop("start_combat_resource")
        if "end_combat_resource" in row:
            row["end_high_ability_resource"] = row.pop("end_combat_resource")
        if int(row.get("end_level") or 0) == 99:
            row["end_level"] = 255
    if sorted(int(row["id"]) for row in skill_effects) != list(SKILL_EFFECT_IDS):
        raise RuntimeError("Moonrise armor skill-effect closure is incomplete")

    with sqlite3.connect(f"file:{client_compact}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        skills = fetch_rows(connection, "skills", BOX_SKILL_IDS)
        effects = fetch_rows(connection, "effects", EFFECT_IDS)
        gain_effects = fetch_rows(
            connection, "gain_loot_pack_item_effects", GAIN_EFFECT_IDS
        )
        boxes = {
            int(row["id"]): dict(row)
            for row in connection.execute(
                "SELECT id,name,description,use_skill_id FROM items "
                "WHERE id IN (47982,47983,47984) ORDER BY id"
            )
        }
        all_item_names: dict[str, list[int]] = {}
        for row in connection.execute("SELECT id,name FROM items"):
            all_item_names.setdefault(str(row["name"]), []).append(int(row["id"]))

    if sorted(int(row["id"]) for row in skills) != list(BOX_SKILL_IDS):
        raise RuntimeError("Moonrise armor skill templates are incomplete")
    if sorted(int(row["id"]) for row in effects) != list(EFFECT_IDS):
        raise RuntimeError("Moonrise armor effect templates are incomplete")
    if sorted(int(row["id"]) for row in gain_effects) != list(GAIN_EFFECT_IDS):
        raise RuntimeError("Moonrise armor GainLootPack details are incomplete")
    for row in effects:
        row["actual_type"] = "GainLootPackItemEffect"

    contents: dict[int, tuple[int, ...]] = {}
    for box_id, skill_id in zip(BOX_IDS, BOX_SKILL_IDS):
        if int(boxes[box_id]["use_skill_id"]) != skill_id:
            raise RuntimeError(f"Moonrise armor box {box_id} use skill changed")
        names = [
            line[2:].strip()
            for line in str(boxes[box_id]["description"]).splitlines()
            if line.startswith("- ")
        ]
        item_ids: list[int] = []
        for name in names:
            matches = all_item_names.get(name, [])
            if len(matches) != 1:
                raise RuntimeError(
                    f"Moonrise armor box {box_id} item {name!r} has {len(matches)} matches"
                )
            item_ids.append(matches[0])
        contents[box_id] = tuple(item_ids)
        if contents[box_id] != RESULT_ITEMS[box_id]:
            raise RuntimeError(
                f"Moonrise armor box {box_id} result closure changed: {contents[box_id]}"
            )

    return {
        "skills": skills,
        "skill_effects": skill_effects,
        "effects": effects,
        "gain_loot_pack_item_effects": gain_effects,
    }, contents


def insert_rows(
    connection: sqlite3.Connection, table: str, rows: list[dict[str, Any]]
) -> None:
    available = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    columns = [column for column in rows[0] if column in available]
    identifiers = sorted({int(row["id"]) for row in rows})
    placeholders = ",".join("?" for _ in identifiers)
    connection.execute(f"DELETE FROM {table} WHERE id IN ({placeholders})", identifiers)
    connection.executemany(
        f"INSERT INTO {table} ({','.join(columns)}) "
        f"VALUES ({','.join(':' + column for column in columns)})",
        sorted(rows, key=lambda row: int(row["id"])),
    )


def install(
    base_runtime: Path,
    target: Path,
    box_rows: dict[str, list[dict[str, Any]]],
    contents: dict[int, tuple[int, ...]],
) -> None:
    if target.exists():
        target.unlink()
    shutil.copyfile(base_runtime, target)
    with sqlite3.connect(target) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for table in ("skills", "skill_effects", "effects", "gain_loot_pack_item_effects"):
            insert_rows(connection, table, box_rows[table])

        for box_id, pack_id in zip(BOX_IDS, LOOT_PACK_IDS):
            connection.execute("DELETE FROM loots WHERE loot_pack_id=?", (pack_id,))
            connection.execute("DELETE FROM loot_groups WHERE pack_id=?", (pack_id,))
            for group_no, item_id in enumerate(contents[box_id], start=1):
                connection.execute(
                    "INSERT INTO loots "
                    "(id,\"group\",item_id,drop_rate,min_amount,max_amount,"
                    "loot_pack_id,grade_id,always_drop) "
                    "VALUES (?,?,?,10000000,1,1,?,0,'t')",
                    (91_500_000 + pack_id * 10 + group_no, group_no, item_id, pack_id),
                )

        provenance = "client_compact_8+game11_native+moonrise_armor_v4"
        for item_id in BOX_IDS:
            connection.execute(
                "DELETE FROM aaemu_item_definition_coverage WHERE item_id=?", (item_id,)
            )
            connection.execute(
                "INSERT INTO aaemu_item_definition_coverage "
                "(item_id,concrete_type,coverage,missing_dependencies,provenance) "
                "VALUES (?,'generic','complete','',?)",
                (item_id, provenance),
            )

        connection.execute(
            "CREATE TABLE IF NOT EXISTS aaemu_moonrise_armor_closure_manifest "
            "(phase TEXT PRIMARY KEY,authority TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO aaemu_moonrise_armor_closure_manifest "
            "(phase,authority) VALUES (?,?)",
            (PHASE, AUTHORITY),
        )
        connection.commit()
        connection.execute("VACUUM")
    connection.close()


def validate(path: Path) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        checks = {
            "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
            "integrity_check": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "skill_effects": connection.execute(
                "SELECT id,skill_id,effect_id,consume_source_item,end_level "
                "FROM skill_effects WHERE id IN (59713,59715,59717) ORDER BY id"
            ).fetchall(),
            "effects": connection.execute(
                "SELECT id,actual_type,actual_id FROM effects "
                "WHERE id IN (78589,78591,78593) ORDER BY id"
            ).fetchall(),
            "gain_effects": connection.execute(
                "SELECT id,loot_pack_id FROM gain_loot_pack_item_effects "
                "WHERE id IN (4215,4217,4219) ORDER BY id"
            ).fetchall(),
            "loot_rows": connection.execute(
                "SELECT loot_pack_id,\"group\",item_id,min_amount,max_amount,always_drop "
                "FROM loots WHERE loot_pack_id IN (12950,12952,12954) "
                "ORDER BY loot_pack_id,\"group\""
            ).fetchall(),
            "coverage": connection.execute(
                "SELECT item_id,coverage,missing_dependencies FROM aaemu_item_definition_coverage "
                "WHERE item_id IN (47982,47983,47984) ORDER BY item_id"
            ).fetchall(),
            "wrapper_exchange": connection.execute(
                "SELECT r.skill_id,r.item_id,r.amount,p.item_id,p.amount "
                "FROM skill_reagents r JOIN skill_products p ON p.skill_id=r.skill_id "
                "WHERE r.skill_id=43013"
            ).fetchall(),
            "orphan_loot_items": connection.execute(
                "SELECT COUNT(*) FROM loots l LEFT JOIN items i ON i.id=l.item_id "
                "LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=l.item_id "
                "WHERE l.loot_pack_id IN (12950,12952,12954) "
                "AND (i.id IS NULL OR c.coverage!='complete')"
            ).fetchone()[0],
        }
    connection.close()
    if checks["quick_check"] != "ok" or checks["integrity_check"] != "ok":
        raise RuntimeError("Generated SQLite failed integrity checks")
    if len(checks["skill_effects"]) != 3 or len(checks["gain_effects"]) != 3:
        raise RuntimeError("Moonrise armor skill/effect closure is incomplete")
    if len(checks["loot_rows"]) != 12 or checks["orphan_loot_items"] != 0:
        raise RuntimeError("Moonrise armor loot closure is incomplete")
    if checks["coverage"] != [(47982, "complete", ""), (47983, "complete", ""), (47984, "complete", "")]:
        raise RuntimeError("Moonrise armor source boxes are not complete")
    if checks["wrapper_exchange"] != [(43013, 48507, 1, 48845, 1)]:
        raise RuntimeError("Rank 1 story infusion exchange was not preserved")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--client-compact", type=Path, required=True)
    parser.add_argument("--game11", type=Path, required=True)
    parser.add_argument("--item-dossier-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    source_hashes = {
        "base_runtime": require_hash("base_runtime", args.base_runtime),
        "client_compact": require_hash("client_compact", args.client_compact),
        "game11": require_hash("game11", args.game11),
    }
    for item_id in BOX_IDS:
        source_hashes[f"item_{item_id}_dossier"] = require_hash(
            f"item_{item_id}_dossier", args.item_dossier_dir / f"item-{item_id}.json"
        )

    box_rows, contents = extract_box_rows(args.client_compact, args.game11)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    first = args.output.with_suffix(args.output.suffix + ".build-a")
    second = args.output.with_suffix(args.output.suffix + ".build-b")
    for candidate in (first, second):
        install(args.base_runtime, candidate, box_rows, contents)
    first_hash = sha256(first)
    second_hash = sha256(second)
    if first_hash != second_hash:
        raise RuntimeError(f"Non-deterministic builds: {first_hash} != {second_hash}")
    checks = validate(second)
    if args.output.exists():
        args.output.unlink()
    os.replace(second, args.output)
    first.unlink()

    manifest = {
        "format_version": 4,
        "phase": PHASE,
        "authority": AUTHORITY,
        "sources": {
            "base_runtime": {"path": str(args.base_runtime), "sha256": source_hashes["base_runtime"]},
            "client_compact": {"path": str(args.client_compact), "sha256": source_hashes["client_compact"]},
            "game11": {"path": str(args.game11), "sha256": source_hashes["game11"]},
            "item_dossiers": {
                str(item_id): {
                    "path": str(args.item_dossier_dir / f"item-{item_id}.json"),
                    "sha256": source_hashes[f"item_{item_id}_dossier"],
                }
                for item_id in BOX_IDS
            },
            "wiki": {
                "urls": [f"https://wiki.archerage.to/na-en/db/items/{item_id}" for item_id in BOX_IDS],
                "authority": "corroboration_only",
            },
        },
        "scope": {
            "armor_boxes": list(BOX_IDS),
            "box_skills": list(BOX_SKILL_IDS),
            "loot_packs": list(LOOT_PACK_IDS),
            "result_items": {str(key): list(value) for key, value in contents.items()},
            "preserved_wrapper_exchange": {"skill_id": 43013, "reagent": 48507, "product": 48845},
            "server_derived": [
                "loots rows only: exact AA8 item descriptions exhaustively enumerate each result; loots is server-only"
            ],
            "historical_3_0_rows": 0,
        },
        "determinism": {
            "build_a_sha256": first_hash,
            "build_b_sha256": second_hash,
            "identical": True,
        },
        "validation": checks,
        "output": {
            "path": str(args.output),
            "bytes": args.output.stat().st_size,
            "sha256": sha256(args.output),
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
