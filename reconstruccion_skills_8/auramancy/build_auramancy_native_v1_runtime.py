#!/usr/bin/env python3
"""Build the closed AA8 Auramancy stage-1 runtime.

The static AA8 skills result omits Teleportation 10152 even though the live
client learns it and nine exact AA8 relations still reference it.  This
builder therefore uses the same bounded tombstone policy already accepted for
Sorcery: only the missing parent row comes from the structural AA10 candidate;
its effects, tags, modifier, localization and ancestral links remain AA8 data.

The four Conversion Shield roots previously quarantined by the generic graph
are promoted only for the proven AA8 DamagedSpell -> fixed-per-mille HealEffect
subset.  This does not claim general HealEffect completeness.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SPECIALIZATIONS = ROOT / "reconstruccion_skills_8" / "specializations"
NATIVE_COMBAT = ROOT / "reconstruccion_skills_8" / "native_combat"
sys.path.insert(0, str(SPECIALIZATIONS))
sys.path.insert(0, str(NATIVE_COMBAT))

from build_native_combat_runtime import columns, normalize, sha256_file, upsert_rows  # noqa: E402
from build_specialization_runtime import (  # noqa: E402
    extend_interaction_doodad_closure,
    select_runtime_rows,
    validate_graph,
)


CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
ABILITY_ID = 4
ABILITY_NAME = "Auramancy"
ABILITY_SLUG = "auramancy"
TELEPORTATION = 10152
PROMOTED_CONVERSION_SHIELD_ROOTS = (11869, 36464, 36465, 46137)
EXPECTED_ROOTS = (
    10152, 10710, 10714, 11380, 11424, 11429, 11869, 11989, 11991,
    16486, 18222, 23589, 36462, 36463, 36464, 36465, 36466, 36467,
    39293, 39294, 40781, 40782, 44348, 46137, 46138,
)
EXPECTED_VISIBLE = (
    10152, 10710, 10714, 11380, 11424, 11429,
    11869, 11989, 11991, 16486, 18222, 23589,
)
EXPECTED_PASSIVES = {
    13: (498, 8),
    21: (621, 5),
    98: (2784, 6),
    251: (7554, 7),
    252: (7553, 4),
    298: (927, 3),
}
TELEPORTATION_NATIVE_ROWS = {
    "skill_effects": (273, 20536),
    "effects": (235, 26043),
    "special_effects": (27,),
    "dispel_effects": (631,),
    "tagged_skills": (767, 3590, 8441, 19736, 23666, 26101),
}
CONVERSION_HEAL_EFFECTS = (1021, 1022, 1023, 1024, 1025, 1026, 1027, 1465)
CONVERSION_TRIGGER_BUFFS = (745, 854, 855, 856, 857, 21416, 21375, 28209)

DEFAULT_CARRIER = Path(r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-shadowplay-v6.sqlite3")
DEFAULT_GRAPH = Path(r"E:\AAEmu-Research\output\aa8-client-forensics\auramancy-specialization-graph-v1.sqlite3")
DEFAULT_GRAPH_MANIFEST = DEFAULT_GRAPH.with_name("auramancy-specialization-graph-v1.manifest.json")
DEFAULT_CATALOG = NATIVE_COMBAT / "generated" / "native-combat-catalog-v1.json"
DEFAULT_KNOWLEDGE = Path(r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-client-knowledge.sqlite")
DEFAULT_CROSSWALK = Path(r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3")
DEFAULT_AA10 = Path(r"E:\AAEmu-Research\test\ArcheAge Returns 10.0.2.13 - 8yx - r575 - 2026-06-18\game\db\game.sqlite3")
DEFAULT_AA8_COMPACT = Path(r"D:\Proyectos\AAemu\client_kakao\compact-client-8.0-decrypted.sqlite")
DEFAULT_OUTPUT = Path(r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-auramancy-v2.sqlite3")
DEFAULT_MANIFEST = HERE / "generated" / "auramancy-native-v2.manifest.json"

EXPECTED_HASHES = {
    "carrier": "01088F9835AFD9BA72E2A86504A63909F468154458D36DBAAB08164362C6BAD3",
    "graph": "A67B3414E67FF907D9E298185F5AD67A9ADD1041F3DBAE1F179C031E1E1DC65E",
    "graph_manifest": "BEE306BF9DC8D4FDD40B53EF6199D30F7641AB901A8C0DC5F2151481B54DF85F",
    "catalog": "A6F255B09ED75903D19A25654C5D5E710C5A849A329031D5093288D4BF7ACF81",
    "knowledge": "A3AB85F0F033407845651AD9277EFBBB4E772A1A8FCD20D973C2DCB5A3848559",
    "crosswalk": "44CFFDAF41BCE8F7B99FC7AB1A85E72F921D77CDF1CC2E51333D6A97E7C01A71",
    "aa10": "87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F",
    "aa8_compact": "4586F4F602C1C2BC9FBE5F376F412BC1277F813922C90AFD5DA8653FF6464F57",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-carrier", type=Path, default=DEFAULT_CARRIER)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--graph-manifest", type=Path, default=DEFAULT_GRAPH_MANIFEST)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--aa10", type=Path, default=DEFAULT_AA10)
    parser.add_argument("--aa8-compact", type=Path, default=DEFAULT_AA8_COMPACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--determinism-output", type=Path)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def ro(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def validate_source(path: Path, expected: str) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"Unexpected source SHA-256 for {path}: {actual}")
    return {"path": str(path.resolve()), "sha256": actual}


def exact_native_row(connection: sqlite3.Connection, table: str, row_id: int) -> dict[str, Any]:
    matches = []
    for row in connection.execute(
        "SELECT state,row_json FROM native_rows WHERE source_table=?", (table,)
    ):
        payload = json.loads(str(row["row_json"]))
        if int(payload.get("id", -1)) == row_id:
            matches.append((str(row["state"]), payload))
    if len(matches) != 1 or matches[0][0] != "confirmed":
        raise RuntimeError(f"AA8 native row gate failed for {table}.{row_id}: {matches}")
    return matches[0][1]


def merge_selected(selected: dict[str, list[dict[str, Any]]], table: str, rows: list[dict[str, Any]]) -> None:
    by_id = {int(row["id"]): row for row in selected.get(table, [])}
    for row in rows:
        row_id = int(row["id"])
        previous = by_id.get(row_id)
        if previous is not None and previous != row:
            raise RuntimeError(f"Conflicting Auramancy row {table}.{row_id}")
        by_id[row_id] = row
    selected[table] = [by_id[row_id] for row_id in sorted(by_id)]


def normalize_candidate(source: sqlite3.Row, runtime: sqlite3.Connection) -> dict[str, Any]:
    source_dict = dict(source)
    result: dict[str, Any] = {}
    for name, sql_type in columns(runtime, "skills").items():
        if name in source_dict:
            value = source_dict[name]
            if value == "t":
                value = 1
            elif value == "f":
                value = 0
            result[name] = value
        elif name == "need_learn":
            result[name] = 1
        else:
            result[name] = None if "TEXT" in sql_type.upper() else 0
    return result


def collect_contract(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, Any], dict[str, Any]]:
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    contract = validate_graph(
        args.graph, args.graph_manifest, ABILITY_ID, ABILITY_NAME, ABILITY_SLUG, args.catalog
    )

    promoted_catalog = copy.deepcopy(catalog)
    for status in promoted_catalog["skill_status"]:
        skill_id = int(status["skill_id"])
        if skill_id in PROMOTED_CONVERSION_SHIELD_ROOTS:
            status["status"] = "enabled"
            status["reason"] = (
                "AA8 bounded DamagedSpell trigger subset: fixed per-mille HealEffect "
                "converts the triggering magic-damage amount"
            )
    for primitive in promoted_catalog["coverage"]["effect_primitives"]:
        if primitive["primitive"] == "HealEffect":
            primitive["state"] = "native_implemented"
    for skill_id in PROMOTED_CONVERSION_SHIELD_ROOTS:
        contract["audit"][skill_id] = {
            "status": "enabled",
            "reason": "bounded_aa8_damaged_spell_conversion_subset",
        }

    selected, selection = select_runtime_rows(contract, promoted_catalog)
    doodads = extend_interaction_doodad_closure(selected, selection, promoted_catalog, ABILITY_ID)

    knowledge = ro(args.knowledge)
    crosswalk = ro(args.crosswalk)
    aa10 = ro(args.aa10)
    carrier = ro(args.runtime_carrier)
    try:
        entity = knowledge.execute(
            "SELECT lifecycle,state,authority FROM entities WHERE entity_key='skill:10152'"
        ).fetchone()
        incoming = int(knowledge.execute(
            "SELECT COUNT(*) FROM relations WHERE dst_entity_key='skill:10152' "
            "AND state='confirmed' AND authority='client_native'"
        ).fetchone()[0])
        if entity is None or tuple(entity[:2]) != ("tombstone", "tombstone") or incoming != 9:
            raise RuntimeError(f"Teleportation AA8 tombstone gate changed: {entity}, incoming={incoming}")
        cross = crosswalk.execute(
            "SELECT classification,relation_state,natural_key_json FROM row_comparisons "
            "WHERE table_name='skills' AND aa10_id='10152' AND aa8_id IS NULL"
        ).fetchone()
        if cross is None or tuple(cross[:2]) != ("aa10_only", "stable"):
            raise RuntimeError(f"Teleportation crosswalk gate changed: {cross}")
        candidate = aa10.execute("SELECT * FROM skills WHERE id=10152").fetchone()
        if candidate is None:
            raise RuntimeError("AA10 structural Teleportation candidate is absent")
        root = normalize_candidate(candidate, carrier)
        expected_parent = {
            "id": 10152, "ability_id": 4, "ability_level": 20,
            "cooldown_time": 35000, "cooldown_tag_id": 3786,
            "fire_anim_id": 264, "fx_group_id": 271, "icon_id": 1309,
            "ignore_global_cooldown": 1, "default_gcd": 0,
        }
        for key, value in expected_parent.items():
            if root.get(key) != value:
                raise RuntimeError(f"Teleportation candidate {key}={root.get(key)} != {value}")

        merge_selected(selected, "skills", [root])
        for table, row_ids in TELEPORTATION_NATIVE_ROWS.items():
            merge_selected(
                selected, table,
                [exact_native_row(knowledge, table, row_id) for row_id in row_ids],
            )
    finally:
        knowledge.close()
        crosswalk.close()
        aa10.close()
        carrier.close()

    contract["root_skill_ids"] = sorted((*contract["root_skill_ids"], TELEPORTATION))
    contract["visible_skill_ids"] = sorted((*contract["visible_skill_ids"], TELEPORTATION))
    contract["audit"][TELEPORTATION] = {
        "status": "enabled",
        "reason": "live_aa8_tombstone_parent_plus_exact_aa8_descendants",
    }
    selection["enabled_skill_ids"] = sorted((*selection["enabled_skill_ids"], TELEPORTATION))
    selection["root_status"][str(TELEPORTATION)] = contract["audit"][TELEPORTATION]
    selection["selected_table_ids"] = {
        table: sorted(int(row["id"]) for row in rows)
        for table, rows in sorted(selected.items())
    }
    selection["quarantined_skill_ids"] = []

    tombstone = {
        "skill_id": TELEPORTATION,
        "lifecycle": "tombstone",
        "confirmed_incoming_relations": 9,
        "parent_authority": "bounded_aa10_structural_candidate",
        "closure_authority": "aa8_client_native",
    }
    return contract, selected, selection, {"doodads": doodads, "tombstone": tombstone}


def apply_localization(connection: sqlite3.Connection, aa8_compact: Path) -> list[dict[str, Any]]:
    source = ro(aa8_compact)
    try:
        rows = [dict(row) for row in source.execute(
            "SELECT tbl_name,tbl_column_name,idx,text,locale FROM localized_texts "
            "WHERE tbl_name='skills' AND idx=10152 AND locale='en_us' "
            "ORDER BY tbl_column_name"
        )]
    finally:
        source.close()
    if [row["tbl_column_name"] for row in rows] != ["desc", "name", "web_desc"]:
        raise RuntimeError(f"Teleportation AA8 localization closure changed: {rows}")
    for row in rows:
        connection.execute(
            "DELETE FROM localized_texts WHERE tbl_name=? AND tbl_column_name=? AND idx=?",
            (row["tbl_name"], row["tbl_column_name"], row["idx"]),
        )
        connection.execute(
            "INSERT INTO localized_texts(tbl_name,tbl_column_name,idx,en_us) VALUES(?,?,?,?)",
            (row["tbl_name"], row["tbl_column_name"], row["idx"], row["text"]),
        )
    return [
        {
            "column": str(row["tbl_column_name"]),
            "sha256": hashlib.sha256(str(row["text"]).encode("utf-8")).hexdigest().upper(),
        }
        for row in rows
    ]


def verify_runtime(connection: sqlite3.Connection, selected: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    errors: list[str] = []
    for table, rows in selected.items():
        available = columns(connection, table)
        for source in rows:
            expected, _ = normalize(table, source)
            names = [name for name in expected if name in available]
            quoted = ",".join('"' + name.replace('"', '""') + '"' for name in names)
            actual = connection.execute(
                f'SELECT {quoted} FROM "{table}" WHERE id=?', (int(source["id"]),)
            ).fetchone()
            if actual is None or tuple(actual) != tuple(expected[name] for name in names):
                errors.append(f"{table}.{source['id']} differs from selected source")

    roots = tuple(int(row[0]) for row in connection.execute(
        "SELECT id FROM skills WHERE ability_id=4 AND id IN (" +
        ",".join("?" for _ in EXPECTED_ROOTS) + ") ORDER BY id", EXPECTED_ROOTS
    ))
    if roots != EXPECTED_ROOTS:
        errors.append(f"Auramancy root set differs: {roots}")
    learnable = tuple(tuple(row) for row in connection.execute(
        "SELECT id,need_learn FROM skills WHERE id IN (" +
        ",".join("?" for _ in EXPECTED_VISIBLE) + ") ORDER BY id", EXPECTED_VISIBLE
    ))
    expected_learnable = tuple((skill_id, 1) for skill_id in EXPECTED_VISIBLE)
    if learnable != expected_learnable:
        errors.append(f"Auramancy visible learnability differs: {learnable}")
    statuses = tuple(tuple(row) for row in connection.execute(
        "SELECT skill_id,status FROM native_combat_skill_status WHERE skill_id IN (" +
        ",".join("?" for _ in EXPECTED_ROOTS) + ") ORDER BY skill_id", EXPECTED_ROOTS
    ))
    if statuses != tuple((skill_id, "enabled") for skill_id in EXPECTED_ROOTS):
        errors.append(f"Auramancy status set differs: {statuses}")

    passives = tuple(tuple(row) for row in connection.execute(
        "SELECT id,buff_id,req_points,skill_points FROM passive_buffs "
        "WHERE ability_id=4 ORDER BY id"
    ))
    expected_passives = tuple(
        (passive_id, buff_id, req_points, 0)
        for passive_id, (buff_id, req_points) in sorted(EXPECTED_PASSIVES.items())
    )
    if passives != expected_passives:
        errors.append(f"Auramancy passives differ: {passives}")

    teleport_effects = tuple(row[0] for row in connection.execute(
        "SELECT id FROM skill_effects WHERE skill_id=10152 ORDER BY id"
    ))
    if teleport_effects != TELEPORTATION_NATIVE_ROWS["skill_effects"]:
        errors.append(f"Teleportation effects differ: {teleport_effects}")
    parent = connection.execute(
        "SELECT cooldown_time,cooldown_tag_id,ignore_global_cooldown,default_gcd,"
        "fire_anim_id,fx_group_id FROM skills WHERE id=10152"
    ).fetchone()
    if parent is None or tuple(parent) != (35000, 3786, 1, 0, 264, 271):
        errors.append(f"Teleportation parent differs: {tuple(parent) if parent else None}")

    conversion_heals = tuple(row[0] for row in connection.execute(
        "SELECT id FROM heal_effects WHERE id IN (" +
        ",".join("?" for _ in CONVERSION_HEAL_EFFECTS) + ") ORDER BY id",
        CONVERSION_HEAL_EFFECTS,
    ))
    if conversion_heals != CONVERSION_HEAL_EFFECTS:
        errors.append(f"Conversion Shield HealEffect closure differs: {conversion_heals}")
    triggers = tuple(tuple(row) for row in connection.execute(
        "SELECT b.id,t.event_id,t.use_damage_amount FROM buffs b "
        "JOIN buff_triggers t ON t.buff_id=b.id "
        "WHERE b.id IN (" + ",".join("?" for _ in CONVERSION_TRIGGER_BUFFS) + ") "
        "AND t.event_id=9 "
        "ORDER BY b.id", CONVERSION_TRIGGER_BUFFS,
    ))
    if len(triggers) != len(CONVERSION_TRIGGER_BUFFS) or any(
        int(row[1]) != 9 or int(row[2]) != 1 for row in triggers
    ):
        errors.append(f"Conversion Shield trigger closure differs: {triggers}")

    name = connection.execute(
        "SELECT en_us FROM localized_texts WHERE tbl_name='skills' "
        "AND tbl_column_name='name' AND idx=10152"
    ).fetchone()
    if name is None or str(name[0]) != "Teleportation":
        errors.append(f"Teleportation localization differs: {name}")
    quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    if quick != "ok" or integrity != "ok":
        errors.append(f"SQLite checks differ: {quick}/{integrity}")
    if errors:
        raise RuntimeError("\n".join(errors[:100]))
    return {
        "root_count": len(roots),
        "visible_root_count": len(EXPECTED_VISIBLE),
        "learnable_visible_root_count": len(learnable),
        "enabled_root_count": len(statuses),
        "quarantined_root_count": 0,
        "passive_count": len(passives),
        "teleportation_skill_effects": list(teleport_effects),
        "conversion_trigger_count": len(triggers),
        "quick_check": quick,
        "integrity_check": integrity,
    }


def build_one(
    carrier: Path,
    output: Path,
    aa8_compact: Path,
    contract: dict[str, Any],
    selected: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if output.resolve() == carrier.resolve():
        raise ValueError("Output must not replace the runtime carrier")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(carrier, output)
    connection = sqlite3.connect(output)
    connection.row_factory = sqlite3.Row
    try:
        # The AA10 Teleportation parent contains carrier-only/server columns that
        # are absent from the static AA8 skill rows.  upsert_rows derives its
        # column set from the first row, so mixing both shapes would write NULL
        # into fields such as need_learn for every native Auramancy root.  Keep
        # the bounded structural parent isolated and preserve the carrier fields
        # of all AA8-native rows exactly.
        native_skill_rows = [
            row for row in selected["skills"] if int(row["id"]) != TELEPORTATION
        ]
        teleportation_rows = [
            row for row in selected["skills"] if int(row["id"]) == TELEPORTATION
        ]
        if len(teleportation_rows) != 1:
            raise RuntimeError(f"Unexpected Teleportation parent rows: {len(teleportation_rows)}")
        merge = {
            "skills_aa8_native": upsert_rows(connection, "skills", native_skill_rows),
            "skills_teleportation_parent": upsert_rows(
                connection, "skills", teleportation_rows
            ),
        }
        merge.update({
            table: upsert_rows(connection, table, rows)
            for table, rows in sorted(selected.items())
            if table != "skills"
        })
        connection.executemany(
            "INSERT INTO native_combat_skill_status(skill_id,ability_id,status,reason,provenance) "
            "VALUES(?,4,'enabled',?,?) ON CONFLICT(skill_id) DO UPDATE SET "
            "ability_id=excluded.ability_id,status=excluded.status,reason=excluded.reason,"
            "provenance=excluded.provenance",
            [
                (
                    skill_id,
                    str(contract["audit"][skill_id]["reason"] or "exact_aa8_native_closure"),
                    "aa8_auramancy_native_v2",
                )
                for skill_id in EXPECTED_ROOTS
            ],
        )
        localization = apply_localization(connection, aa8_compact)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS auramancy_reconstruction_v2_metadata("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL,provenance TEXT NOT NULL)"
        )
        metadata = {
            "client_build": CLIENT_BUILD,
            "root_ids": ",".join(str(value) for value in EXPECTED_ROOTS),
            "visible_root_ids": ",".join(str(value) for value in EXPECTED_VISIBLE),
            "passive_ids": ",".join(str(value) for value in sorted(EXPECTED_PASSIVES)),
            "teleportation_parent": "live_aa8_tombstone_identity_plus_bounded_aa10_parent",
            "teleportation_closure": "exact_aa8_native",
            "conversion_shield": "bounded_damaged_spell_fixed_per_mille_subset",
            "mixed_shape_skill_upsert": "forbidden_preserve_carrier_only_fields",
            "custom_runtime_logic": "none",
        }
        connection.executemany(
            "INSERT INTO auramancy_reconstruction_v2_metadata(key,value,provenance) "
            "VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET "
            "value=excluded.value,provenance=excluded.provenance",
            [(key, value, "aa8_auramancy_native_v2") for key, value in sorted(metadata.items())],
        )
        connection.commit()
        verification = verify_runtime(connection, selected)
        connection.execute("VACUUM")
    except Exception:
        connection.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        connection.close()
    return {"merge": merge, "verification": verification}, localization


def build(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "runtime_carrier": validate_source(args.runtime_carrier, EXPECTED_HASHES["carrier"]),
        "graph": validate_source(args.graph, EXPECTED_HASHES["graph"]),
        "graph_manifest": validate_source(args.graph_manifest, EXPECTED_HASHES["graph_manifest"]),
        "catalog": validate_source(args.catalog, EXPECTED_HASHES["catalog"]),
        "knowledge": validate_source(args.knowledge, EXPECTED_HASHES["knowledge"]),
        "crosswalk": validate_source(args.crosswalk, EXPECTED_HASHES["crosswalk"]),
        "aa10": validate_source(args.aa10, EXPECTED_HASHES["aa10"]),
        "aa8_compact": validate_source(args.aa8_compact, EXPECTED_HASHES["aa8_compact"]),
    }
    contract, selected, selection, evidence = collect_contract(args)
    if tuple(contract["root_skill_ids"]) != EXPECTED_ROOTS:
        raise RuntimeError(f"Auramancy root contract changed: {contract['root_skill_ids']}")
    if tuple(contract["visible_skill_ids"]) != EXPECTED_VISIBLE:
        raise RuntimeError(f"Auramancy visible contract changed: {contract['visible_skill_ids']}")

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    first, localization = build_one(
        args.runtime_carrier, args.output, args.aa8_compact, contract, selected
    )
    second_path = args.determinism_output or args.output.with_name(
        args.output.stem + ".determinism" + args.output.suffix
    )
    second, second_localization = build_one(
        args.runtime_carrier, second_path, args.aa8_compact, contract, selected
    )
    first_hash = sha256_file(args.output)
    second_hash = sha256_file(second_path)
    if first_hash != second_hash or localization != second_localization:
        raise RuntimeError(f"Auramancy deterministic build mismatch: {first_hash} != {second_hash}")

    manifest = {
        "format_version": 2,
        "client_build": CLIENT_BUILD,
        "authority": {
            "runtime": "AA8 r558734",
            "teleportation_parent": "bounded AA10 structural candidate after live AA8 tombstone proof",
            "teleportation_closure": "exact AA8 native rows",
            "modern": "structural comparator only",
        },
        "sources": sources,
        "scope": {
            "root_skill_ids": list(EXPECTED_ROOTS),
            "visible_skill_ids": list(EXPECTED_VISIBLE),
            "passive_ids": sorted(EXPECTED_PASSIVES),
            "promoted_conversion_shield_roots": list(PROMOTED_CONVERSION_SHIELD_ROOTS),
            "selected_table_ids": selection["selected_table_ids"],
        },
        "evidence": evidence,
        "localization": localization,
        "verification": first["verification"],
        "determinism": {
            "status": "confirmed",
            "first": {"path": str(args.output.resolve()), "sha256": first_hash},
            "second": {"path": str(second_path.resolve()), "sha256": second_hash},
            "second_verification": second["verification"],
        },
        "output": {"path": str(args.output.resolve()), "sha256": first_hash},
    }
    args.manifest.write_text(canonical(manifest), encoding="utf-8")
    print(canonical({
        "manifest": str(args.manifest.resolve()),
        "manifest_sha256": sha256_file(args.manifest),
        "output": manifest["output"],
        "verification": manifest["verification"],
        "determinism": manifest["determinism"],
    }), end="")
    return manifest


def main(argv: list[str] | None = None) -> int:
    return 0 if build(parse_args(argv)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
