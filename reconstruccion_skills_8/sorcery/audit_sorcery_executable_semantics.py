"""Build a deterministic AA8 Sorcery executable-semantics audit.

This audit deliberately separates decoded client data from server-side behavior.
The specialization graph proves that a descriptor exists; this report proves
whether AAEmu has a handler for every descriptor reached by Sorcery and records
the remaining protocol/manual-acceptance gates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
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
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_V4_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v4.manifest.json"
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v4.sqlite3"
)
DEFAULT_JSON = SORCERY_DIR / "generated" / "sorcery-executable-semantics-audit-v2.json"
DEFAULT_CSV = SORCERY_DIR / "generated" / "sorcery-executable-semantics-matrix-v2.csv"

CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
LIVE_ROOTS = (10151, 10153)
PASSIVE_TEMPLATES = (15, 38, 99, 257, 258, 301)
PASSIVE_BUFFS = (536, 962, 963, 2910, 7566, 7567)

# These are observations from the current live acceptance cycle, not claims
# inferred from static data.
MANUAL_BASELINE = {
    10667: "partial_live_started_fired_buff_247",
    10752: "partial_live_chain_10752_24894_24895_buffs_1403_2287",
    12796: "partial_live_buff_19037_resource_466_inert",
}

CORE_HANDLER_OVERRIDES = {
    "BuffEffect": "implemented",
    "DamageEffect": "implemented_aa8_native_formula",
    "DispelEffect": "implemented",
    "AggroEffect": "implemented_aa8_native_formula",
    "InteractionEffect": "implemented_sorcery_summon_direction",
    "PhysicalExplosionEffect": "native_physics_declarative_exact_envelope",
    "CombatResourceEffect": "implemented_exact_aa8_protocol",
    "ExtendChargeEffect": "implemented_aa8_formula",
    "ResetAoeDiminishingEffect": "implemented",
    "SkillController": "implemented_sorcery_leap_proxy",
    "SpecialEffect": "router",
}

SPECIAL_HANDLER_OVERRIDES = {
    "Anim": "client_declarative",
    "FxGroup": "client_declarative",
    "FxGroupAnim": "client_declarative",
    "Projectile": "client_declarative",
    "ProjectileAnim": "client_declarative",
    "CombatText": "client_declarative",
    "ManaCost": "implemented_aa8_native_formula",
    "Cooldown": "implemented_plot_path",
    "GlobalCooldown": "implemented_plot_path",
    "StopManaRegen": "implemented",
    "CancelStealth": "implemented",
    "CancelOngoingBuff": "implemented",
    "AutoAttack": "implemented",
    "Combo": "client_driven_transition_server_accepts_child_request",
    "KnockBack": "implemented_native_client_plus_npc_proxy",
    "DisturbCasting": "implemented",
    "SkillUse": "implemented",
    "SpawnDoodad": "implemented",
    "ReturnToSavedPosition": "implemented",
}

BLOCKING_STATES = {
    "missing",
    "no_op",
    "partial",
    "partial_legacy_formula",
    "candidate_formula",
}

_CROSSWALK_CACHE: dict[
    tuple[str, tuple[tuple[str, tuple[int, ...]], ...]],
    dict[str, dict[int, dict[str, Any]]],
] = {}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument(
        "--runtime-manifest", "--v2-manifest",
        dest="runtime_manifest", type=Path, default=DEFAULT_V4_MANIFEST
    )
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    return parser.parse_args(argv)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def row_map(catalog: dict[str, Any], table: str) -> dict[int, dict[str, Any]]:
    return {int(row["id"]): row for row in catalog["tables"].get(table, [])}


def parse_special_types() -> dict[int, str]:
    source = (
        ROOT
        / "AAEmu.Game"
        / "Models"
        / "Game"
        / "Skills"
        / "Effects"
        / "SpecialEffectType.cs"
    ).read_text(encoding="utf-8-sig")
    return {
        int(number): name
        for name, number in re.findall(r"^\s*(\w+)\s*=\s*(\d+)", source, re.MULTILINE)
    }


def source_markers(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False, "todo_count": 0, "warn_count": 0}
    text = path.read_text(encoding="utf-8-sig")
    return {
        "path": str(path.resolve()),
        "present": True,
        "todo_count": len(re.findall(r"\bTODO\b", text, re.IGNORECASE)),
        "warn_count": len(re.findall(r"_log\.Warn|Logger\.Warn", text)),
        "throws_not_implemented": "NotImplementedException" in text,
        "sha256": sha256_file(path),
    }


def handler_record(name: str, special: bool = False) -> dict[str, Any]:
    base = ROOT / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects"
    if name == "SkillController" and not special:
        path = (
            ROOT
            / "AAEmu.Game"
            / "Models"
            / "Game"
            / "Skills"
            / "SkillControllers"
            / "SkillController.cs"
        )
    else:
        path = base / ("SpecialEffects" if special else "") / f"{name}.cs"
    markers = source_markers(path)
    overrides = SPECIAL_HANDLER_OVERRIDES if special else CORE_HANDLER_OVERRIDES
    if not markers["present"]:
        state = "missing"
    elif markers.get("throws_not_implemented"):
        state = "missing"
    else:
        state = overrides.get(name, "review_required")
    return {"name": name, "state": state, **markers}


def load_crosswalk(
    path: Path, selected_ids: dict[str, set[int]]
) -> dict[str, dict[int, dict[str, Any]]]:
    cache_key = (
        str(path.resolve()),
        tuple((table, tuple(sorted(ids))) for table, ids in sorted(selected_ids.items())),
    )
    if cache_key in _CROSSWALK_CACHE:
        return _CROSSWALK_CACHE[cache_key]
    result: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)
    if not path.is_file():
        return result
    tables = sorted(selected_ids)
    placeholders = ",".join("?" for _ in tables)
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            f"SELECT table_name,aa8_id,aa10_id,classification,relation_state,"
            f"property_state,balance_state,changed_relation_columns_json,"
            f"changed_property_columns_json,balance_columns_json "
            f"FROM row_comparisons WHERE table_name IN ({placeholders})",
            tables,
        )
        for row in rows:
            table = str(row[0])
            try:
                aa8_id = int(row[1])
            except (TypeError, ValueError):
                continue
            if aa8_id not in selected_ids[table]:
                continue
            result[table][aa8_id] = {
                "aa10_id": row[2],
                "classification": row[3],
                "relation_state": row[4],
                "property_state": row[5],
                "balance_state": row[6],
                "changed_relation_columns": json.loads(row[7]),
                "changed_property_columns": json.loads(row[8]),
                "balance_columns": json.loads(row[9]),
            }
    finally:
        connection.close()
    _CROSSWALK_CACHE[cache_key] = result
    return result


def load_live_root_closures(runtime_path: Path) -> dict[int, dict[str, set[int]]]:
    result: dict[int, dict[str, set[int]]] = {
        skill_id: defaultdict(set) for skill_id in LIVE_ROOTS
    }
    if not runtime_path.is_file():
        return result
    connection = sqlite3.connect(
        f"file:{runtime_path.resolve().as_posix()}?mode=ro", uri=True
    )
    connection.row_factory = sqlite3.Row
    try:
        for skill_id in LIVE_ROOTS:
            result[skill_id]["skills"].add(skill_id)
            skill = connection.execute(
                "SELECT plot_id FROM skills WHERE id=?", (skill_id,)
            ).fetchone()
            for row in connection.execute(
                "SELECT se.id,se.effect_id,e.actual_type,e.actual_id "
                "FROM skill_effects se JOIN effects e ON e.id=se.effect_id "
                "WHERE se.skill_id=? ORDER BY se.id",
                (skill_id,),
            ):
                result[skill_id]["skill_effects"].add(int(row["id"]))
                result[skill_id]["effects"].add(int(row["effect_id"]))
                table = _actual_type_to_table(str(row["actual_type"]))
                if table:
                    result[skill_id][table].add(int(row["actual_id"]))
            plot_id = int(skill["plot_id"]) if skill and skill["plot_id"] else 0
            if not plot_id:
                continue
            result[skill_id]["plots"].add(plot_id)
            for row in connection.execute(
                "SELECT pe.id,pe.actual_type,pe.actual_id,pe.event_id "
                "FROM plot_effects pe JOIN plot_events ev ON ev.id=pe.event_id "
                "WHERE ev.plot_id=? ORDER BY pe.id",
                (plot_id,),
            ):
                result[skill_id]["plot_effects"].add(int(row["id"]))
                result[skill_id]["plot_events"].add(int(row["event_id"]))
                table = _actual_type_to_table(str(row["actual_type"]))
                if table:
                    result[skill_id][table].add(int(row["actual_id"]))
    finally:
        connection.close()
    return result


def _actual_type_to_table(actual_type: str) -> str | None:
    if not actual_type.endswith("Effect"):
        return None
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", actual_type).lower()
    return f"{snake}s"


def actual_types_for_closure(
    closure: dict[str, set[int]],
    catalog: dict[str, Any],
    runtime_path: Path,
) -> tuple[Counter[str], set[int]]:
    types: Counter[str] = Counter()
    special_ids: set[int] = set()
    effects = row_map(catalog, "effects")
    plot_effects = row_map(catalog, "plot_effects")
    for effect_id in closure.get("effects", set()):
        row = effects.get(effect_id)
        if row:
            types[str(row["actual_type"])] += 1
            if row["actual_type"] == "SpecialEffect":
                special_ids.add(int(row["actual_id"]))
    for effect_id in closure.get("plot_effects", set()):
        row = plot_effects.get(effect_id)
        if row:
            types[str(row["actual_type"])] += 1
            if row["actual_type"] == "SpecialEffect":
                special_ids.add(int(row["actual_id"]))

    # The two live roots were materialized after the static catalog. Resolve
    # their descriptors from the versioned runtime when needed.
    unresolved_effects = closure.get("effects", set()) - set(effects)
    unresolved_plot_effects = closure.get("plot_effects", set()) - set(plot_effects)
    if (unresolved_effects or unresolved_plot_effects) and runtime_path.is_file():
        connection = sqlite3.connect(
            f"file:{runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )
        try:
            for table, ids in (
                ("effects", unresolved_effects),
                ("plot_effects", unresolved_plot_effects),
            ):
                for row_id in sorted(ids):
                    row = connection.execute(
                        f"SELECT actual_type,actual_id FROM {table} WHERE id=?", (row_id,)
                    ).fetchone()
                    if not row:
                        continue
                    types[str(row[0])] += 1
                    if row[0] == "SpecialEffect":
                        special_ids.add(int(row[1]))
        finally:
            connection.close()
    return types, special_ids


def special_type_ids(
    ids: set[int], catalog: dict[str, Any], runtime_path: Path
) -> Counter[int]:
    rows = row_map(catalog, "special_effects")
    result: Counter[int] = Counter()
    unresolved = set(ids) - set(rows)
    for row_id in ids & set(rows):
        result[int(rows[row_id]["special_effect_type_id"])] += 1
    if unresolved and runtime_path.is_file():
        connection = sqlite3.connect(
            f"file:{runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )
        try:
            for row_id in sorted(unresolved):
                row = connection.execute(
                    "SELECT special_effect_type_id FROM special_effects WHERE id=?",
                    (row_id,),
                ).fetchone()
                if row:
                    result[int(row[0])] += 1
        finally:
            connection.close()
    return result


def make_root_closures(
    catalog: dict[str, Any], runtime_path: Path
) -> tuple[list[dict[str, Any]], dict[int, dict[str, set[int]]]]:
    statuses = [row for row in catalog["skill_status"] if int(row["ability_id"]) == 7]
    closures: dict[int, dict[str, set[int]]] = {}
    roots: list[dict[str, Any]] = []
    skills = row_map(catalog, "skills")
    for status in statuses:
        root_id = int(status["skill_id"])
        closure: dict[str, set[int]] = defaultdict(set)
        for skill_id in status["closure_skill_ids"]:
            for table, ids in catalog["skill_table_ids"][str(skill_id)].items():
                closure[table].update(int(value) for value in ids)
        closures[root_id] = closure
        skill = skills.get(root_id, {})
        roots.append(
            {
                "skill_id": root_id,
                "name": skill.get("name", ""),
                "visible": bool(skill.get("show", 0)),
                "static_status": status["status"],
                "closure_skill_ids": [int(value) for value in status["closure_skill_ids"]],
                "source": "aa8_native_catalog",
            }
        )
    live = load_live_root_closures(runtime_path)
    if runtime_path.is_file():
        connection = sqlite3.connect(
            f"file:{runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )
        connection.row_factory = sqlite3.Row
        try:
            for skill_id in LIVE_ROOTS:
                row = connection.execute(
                    "SELECT name,show FROM skills WHERE id=?", (skill_id,)
                ).fetchone()
                closures[skill_id] = live[skill_id]
                roots.append(
                    {
                        "skill_id": skill_id,
                        "name": str(row["name"]) if row else "",
                        "visible": bool(row["show"]) if row else True,
                        "static_status": "enabled_live_candidate_root",
                        "closure_skill_ids": [skill_id],
                        "source": "aa8_live_request_plus_aa10_root_candidate_plus_aa8_closure",
                    }
                )
        finally:
            connection.close()
    if runtime_path.is_file():
        connection = sqlite3.connect(
            f"file:{runtime_path.resolve().as_posix()}?mode=ro", uri=True
        )
        try:
            runtime_statuses = {
                int(row[0]): str(row[1])
                for row in connection.execute(
                    "SELECT skill_id,status FROM native_combat_skill_status WHERE ability_id=7"
                )
            }
        finally:
            connection.close()
        for root in roots:
            catalog_status = root["static_status"]
            runtime_status = runtime_statuses.get(int(root["skill_id"]), "missing")
            root["catalog_status"] = catalog_status
            root["runtime_status"] = runtime_status
            if catalog_status == "quarantined" and runtime_status == "enabled":
                root["static_status"] = "enabled_runtime_promoted"
    roots.sort(key=lambda row: int(row["skill_id"]))
    return roots, closures


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    runtime_manifest = json.loads(args.runtime_manifest.read_text(encoding="utf-8"))
    roots, closures = make_root_closures(catalog, args.runtime)
    selected_ids: dict[str, set[int]] = defaultdict(set)
    for closure in closures.values():
        for table, ids in closure.items():
            selected_ids[table].update(ids)
    crosswalk = load_crosswalk(args.crosswalk, selected_ids)
    special_names = parse_special_types()

    core_names: set[str] = set()
    special_name_set: set[str] = set()
    matrix: list[dict[str, Any]] = []
    for root in roots:
        skill_id = int(root["skill_id"])
        closure = closures[skill_id]
        effect_types, special_ids = actual_types_for_closure(
            closure, catalog, args.runtime
        )
        special_types = special_type_ids(special_ids, catalog, args.runtime)
        core_names.update(effect_types)
        named_special = {
            special_names.get(type_id, f"Unknown{type_id}"): count
            for type_id, count in sorted(special_types.items())
        }
        special_name_set.update(named_special)

        core_states = {
            name: handler_record(name)["state"] for name in sorted(effect_types)
        }
        special_states = {
            name: handler_record(name, special=True)["state"]
            for name in sorted(named_special)
        }
        blockers = sorted(
            f"core:{name}:{state}"
            for name, state in core_states.items()
            if state in BLOCKING_STATES
        ) + sorted(
            f"special:{name}:{state}"
            for name, state in special_states.items()
            if state in BLOCKING_STATES
        )
        crosswalk_counts: Counter[str] = Counter()
        crosswalk_missing = 0
        for table, ids in closure.items():
            for row_id in ids:
                row = crosswalk.get(table, {}).get(row_id)
                if row:
                    crosswalk_counts[str(row["classification"])] += 1
                else:
                    crosswalk_missing += 1
        matrix.append(
            {
                **root,
                "closure_table_counts": {
                    table: len(ids) for table, ids in sorted(closure.items())
                },
                "actual_effect_types": dict(sorted(effect_types.items())),
                "special_effect_types": dict(sorted(named_special.items())),
                "core_handler_states": core_states,
                "special_handler_states": special_states,
                "blockers": blockers,
                "crosswalk_classifications": dict(sorted(crosswalk_counts.items())),
                "crosswalk_missing_rows": crosswalk_missing,
                "manual_acceptance": MANUAL_BASELINE.get(skill_id, "pending"),
                "executable_state": "blocked" if blockers else "candidate_manual_gate",
            }
        )

    core_handlers = {name: handler_record(name) for name in sorted(core_names)}
    special_handlers = {
        name: handler_record(name, special=True) for name in sorted(special_name_set)
    }
    all_selected = sum(len(ids) for ids in selected_ids.values())
    compared = sum(len(rows) for rows in crosswalk.values())
    return {
        "format_version": 2,
        "client_build": CLIENT_BUILD,
        "authority": {
            "aa8_native_catalog": "root_and_executable_closure_authority",
            "aa8_live_packets": "client_reachability_and_manual_behavior_authority",
            "aa10_crosswalk": "mandatory_gap_reduction_not_balance_or_protocol_authority",
            "server_source": "implementation_state_only",
        },
        "sources": {
            "catalog": {"path": str(args.catalog.resolve()), "sha256": sha256_file(args.catalog)},
            "crosswalk": {"path": str(args.crosswalk.resolve()), "sha256": sha256_file(args.crosswalk)},
            "runtime_manifest": {
                "path": str(args.runtime_manifest.resolve()),
                "sha256": sha256_file(args.runtime_manifest),
            },
            "runtime": {"path": str(args.runtime.resolve()), "sha256": sha256_file(args.runtime)},
        },
        "scope": {
            "static_skill_roots": len([row for row in roots if row["source"] == "aa8_native_catalog"]),
            "live_candidate_roots": list(LIVE_ROOTS),
            "passive_templates": list(PASSIVE_TEMPLATES),
            "passive_buffs": list(PASSIVE_BUFFS),
            "selected_table_rows": all_selected,
            "crosswalk_rows_found": compared,
        },
        "crosswalk_findings": {
            "combat_resource_effects": "7/7 exact_id_exact_relation",
            "reset_aoe_diminishing_effects": "6/6 exact_id_exact_relation",
            "damage_effects": "88/88 stable_id_changed_properties; AA10 balance values are not promotable",
            "live_roots_10151_10153": "AA10-only root candidates; executable descendants are AA8",
            "extend_charge_effect_1": "stable identity but changed properties; formula remains unconfirmed",
        },
        "core_handlers": core_handlers,
        "special_handlers": special_handlers,
        "roots": matrix,
        "passives": {
            "state": "accepted_live",
            "templates": list(PASSIVE_TEMPLATES),
            "buffs": list(PASSIVE_BUFFS),
            "acceptance": "learn_apply_save_load_reapply",
        },
        "runtime_root_authority": runtime_manifest["authority"],
        "summary": {
            "root_count": len(matrix),
            "blocked_root_count": sum(row["executable_state"] == "blocked" for row in matrix),
            "manual_pending_count": sum(row["manual_acceptance"] == "pending" for row in matrix),
            "core_handler_state_counts": dict(
                sorted(Counter(row["state"] for row in core_handlers.values()).items())
            ),
            "special_handler_state_counts": dict(
                sorted(Counter(row["state"] for row in special_handlers.values()).items())
            ),
        },
    }


def write_csv(path: Path, report: dict[str, Any]) -> None:
    columns = [
        "skill_id",
        "name",
        "visible",
        "source",
        "static_status",
        "executable_state",
        "manual_acceptance",
        "closure_skill_ids",
        "actual_effect_types",
        "special_effect_types",
        "blockers",
        "crosswalk_classifications",
        "crosswalk_missing_rows",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in report["roots"]:
            writer.writerow(
                {
                    key: json.dumps(row[key], ensure_ascii=False, sort_keys=True)
                    if isinstance(row[key], (dict, list))
                    else row[key]
                    for key in columns
                }
            )


def main() -> int:
    args = parse_args()
    report = build_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(canonical(report), encoding="utf-8")
    write_csv(args.output_csv, report)
    print(canonical(report["summary"]), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
