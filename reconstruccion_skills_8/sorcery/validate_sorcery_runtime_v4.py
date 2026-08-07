#!/usr/bin/env python3
"""Validate the complete executable AA8 Sorcery runtime closure.

The executable-semantics audit proves that AAEmu has a handler for each
descriptor type.  This validator provides the complementary materialization
gate: every Sorcery row must be present, native AA8 rows must match the frozen
catalog field-for-field, and every executable relation must resolve in the
versioned runtime.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SORCERY_DIR = Path(__file__).resolve().parent
NATIVE_COMBAT = ROOT / "reconstruccion_skills_8" / "native_combat"
sys.path.insert(0, str(NATIVE_COMBAT))

from build_native_combat_runtime import CONCRETE_EFFECT_TABLES, normalize  # noqa: E402


DEFAULT_CATALOG = NATIVE_COMBAT / "generated" / "native-combat-catalog-v1.json"
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v4.sqlite3"
)
DEFAULT_MANIFEST = SORCERY_DIR / "generated" / "sorcery-specialization-v4.manifest.json"
DEFAULT_AUDIT = SORCERY_DIR / "generated" / "sorcery-executable-semantics-audit-v2.json"
DEFAULT_JSON = SORCERY_DIR / "generated" / "sorcery-runtime-acceptance-v4.json"
DEFAULT_CSV = SORCERY_DIR / "generated" / "sorcery-runtime-acceptance-v4.csv"

CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
LIVE_ROOTS = (10151, 10153)
VISIBLE_ROOTS = (
    10151,
    10153,
    10664,
    10667,
    10670,
    10752,
    11314,
    11939,
    11967,
    12796,
    14774,
    23593,
)
EXPECTED_ENGLISH_NAMES = {
    10151: "Freezing Earth",
    10153: "Insulating Lens",
    10664: "Meteor Strike",
    10667: "Freezing Arrow",
    10670: "Arc Lightning",
    10752: "Flamebolt",
    11314: "Frigid Tracks",
    11939: "Searing Rain",
    11967: "Chain Lightning",
    12796: "Magic Circle",
    14774: "Flame Barrier",
    23593: "Gods' Whip",
}
PASSIVE_TEMPLATES = (15, 38, 99, 257, 258, 301)
PASSIVE_BUFFS = (536, 962, 963, 2910, 7566, 7567)
PASSIVE_CONTRACTS = {
    15: 536,
    38: 962,
    99: 2910,
    257: 7566,
    258: 7567,
    301: 963,
}
AA8_DOODADS = (13406, 13407, 14623, 14666)

# Direct foreign-key-like relations consumed by the server.  SQLite does not
# declare these as FKs, so the acceptance gate validates them explicitly.
REFERENCE_RULES = {
    "skill_effects": (("skill_id", "skills"), ("effect_id", "effects")),
    "plot_events": (("plot_id", "plots"),),
    "plot_effects": (("event_id", "plot_events"),),
    "plot_event_conditions": (
        ("event_id", "plot_events"),
        ("condition_id", "plot_conditions"),
    ),
    "plot_aoe_conditions": (
        ("event_id", "plot_events"),
        ("condition_id", "plot_conditions"),
    ),
    "plot_next_events": (
        ("event_id", "plot_events"),
        ("next_event_id", "plot_events"),
    ),
    "buff_effects": (("buff_id", "buffs"),),
    "buff_tick_effects": (("buff_id", "buffs"), ("effect_id", "effects")),
    "buff_triggers": (("buff_id", "buffs"), ("effect_id", "effects")),
    "buff_unit_modifiers": (("buff_id", "buffs"),),
    "tagged_buffs": (("buff_id", "buffs"),),
    "passive_buffs": (("buff_id", "buffs"),),
    "interaction_effects": (("doodad_id", "doodad_almighties"),),
    "doodad_func_groups": (("doodad_almighty_id", "doodad_almighties"),),
    "doodad_func_clouts": (
        ("buff_id", "buffs"),
        ("projectile_id", "projectiles"),
        ("aoe_shape_id", "aoe_shapes"),
        ("next_phase", "doodad_func_groups"),
    ),
    "doodad_func_timers": (("next_phase", "doodad_func_groups"),),
}

SKILL_REFERENCE_RULES = (
    ("plot_id", "plots"),
    ("projectile_id", "projectiles"),
    ("skill_controller_id", "skill_controllers"),
    ("toggle_buff_id", "buffs"),
    ("channeling_buff_id", "buffs"),
    ("channeling_target_buff_id", "buffs"),
    ("precedence_skill_id", "skills"),
    ("switch_to_skill_cooldown", "skills"),
)

BUFF_REFERENCE_RULES = (
    ("add_duration_buff_id", "buffs"),
    ("aura_slave_buff_id", "buffs"),
    ("cooldown_skill_id", "skills"),
    ("crowd_buff_id", "buffs"),
    ("crowd_check_buff_id", "buffs"),
    ("link_buff_id", "buffs"),
    ("require_buff_id", "buffs"),
    ("skill_controller_id", "skill_controllers"),
    ("transform_buff_id", "buffs"),
)

CHARGED_BUFF_RULES = {
    "aggro_effects": ("charged_buff_id",),
    "damage_effects": ("charged_buff_id", "target_charged_buff_id"),
    "extend_charge_effects": ("charge_buff_id",),
    "heal_effects": ("charged_buff_id",),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV)
    return parser.parse_args(argv)


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({quote(table)})")}


def row_exists(connection: sqlite3.Connection, table: str, row_id: int) -> bool:
    if not table_exists(connection, table):
        return False
    return connection.execute(
        f"SELECT 1 FROM {quote(table)} WHERE id=?", (int(row_id),)
    ).fetchone() is not None


def catalog_row_maps(catalog: dict[str, Any]) -> dict[str, dict[int, dict[str, Any]]]:
    result: dict[str, dict[int, dict[str, Any]]] = {}
    for table, rows in catalog["tables"].items():
        if rows and "id" in rows[0]:
            result[table] = {int(row["id"]): row for row in rows}
    return result


def static_ability_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in catalog["skill_status"] if int(row["ability_id"]) == 7]


def static_root_closure(
    catalog: dict[str, Any], status: dict[str, Any]
) -> dict[str, set[int]]:
    closure: dict[str, set[int]] = defaultdict(set)
    for skill_id in status["closure_skill_ids"]:
        for table, ids in catalog["skill_table_ids"][str(skill_id)].items():
            closure[table].update(int(value) for value in ids)
    return closure


def compare_native_rows(
    connection: sqlite3.Connection,
    row_maps: dict[str, dict[int, dict[str, Any]]],
    selected: dict[str, set[int]],
) -> tuple[list[str], int]:
    errors: list[str] = []
    compared = 0
    for table, ids in sorted(selected.items()):
        if not ids:
            continue
        if not table_exists(connection, table):
            errors.append(f"missing_table:{table}")
            continue
        available = table_columns(connection, table)
        source_rows = row_maps.get(table, {})
        for row_id in sorted(ids):
            source = source_rows.get(row_id)
            if source is None:
                errors.append(f"catalog_payload_missing:{table}.{row_id}")
                continue
            expected, _ = normalize(table, source)
            names = [name for name in expected if name in available]
            actual = connection.execute(
                f"SELECT {','.join(quote(name) for name in names)} "
                f"FROM {quote(table)} WHERE id=?",
                (row_id,),
            ).fetchone()
            if actual is None:
                errors.append(f"runtime_row_missing:{table}.{row_id}")
                continue
            expected_values = tuple(expected[name] for name in names)
            actual_values = tuple(actual[name] for name in names)
            if actual_values != expected_values:
                mismatches = [
                    name
                    for name in names
                    if actual[name] != expected[name]
                ]
                errors.append(
                    f"native_payload_mismatch:{table}.{row_id}:"
                    + ",".join(mismatches)
                )
                continue
            compared += 1
    return errors, compared


def effect_table(actual_type: str) -> str | None:
    if actual_type == "SkillController":
        return "skill_controllers"
    return CONCRETE_EFFECT_TABLES.get(actual_type)


def phase_func_table(actual_type: str) -> str | None:
    if not actual_type.startswith("DoodadFunc"):
        return None
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", actual_type).lower()
    return f"{snake}s"


def add_reference_error(
    errors: list[str],
    connection: sqlite3.Connection,
    source_table: str,
    source_id: int,
    column: str,
    target_table: str,
    target_id: Any,
) -> None:
    if target_id is None:
        return
    try:
        target = int(target_id)
    except (TypeError, ValueError):
        errors.append(
            f"invalid_reference:{source_table}.{source_id}.{column}={target_id!r}"
        )
        return
    if target <= 0:
        return
    if not row_exists(connection, target_table, target):
        errors.append(
            f"orphan_reference:{source_table}.{source_id}.{column}"
            f"->{target_table}.{target}"
        )


def validate_references(
    connection: sqlite3.Connection, selected: dict[str, set[int]]
) -> tuple[list[str], int]:
    errors: list[str] = []
    checked = 0
    for table, ids in sorted(selected.items()):
        if not ids or not table_exists(connection, table):
            continue
        available = table_columns(connection, table)
        direct_rules = list(REFERENCE_RULES.get(table, ()))
        if table == "skills":
            direct_rules.extend(SKILL_REFERENCE_RULES)
        elif table == "buffs":
            direct_rules.extend(BUFF_REFERENCE_RULES)
        direct_rules.extend((name, "buffs") for name in CHARGED_BUFF_RULES.get(table, ()))
        direct_rules = [(column, target) for column, target in direct_rules if column in available]
        extra = []
        if table in ("effects", "plot_effects"):
            extra.extend(name for name in ("actual_type", "actual_id") if name in available)
        if table == "doodad_phase_funcs":
            extra.extend(name for name in ("actual_func_type", "actual_func_id") if name in available)
        names = ["id", *(column for column, _ in direct_rules), *extra]
        names = list(dict.fromkeys(names))
        placeholders = ",".join("?" for _ in ids)
        for row in connection.execute(
            f"SELECT {','.join(quote(name) for name in names)} FROM {quote(table)} "
            f"WHERE id IN ({placeholders}) ORDER BY id",
            tuple(sorted(ids)),
        ):
            source_id = int(row["id"])
            for column, target_table in direct_rules:
                add_reference_error(
                    errors,
                    connection,
                    table,
                    source_id,
                    column,
                    target_table,
                    row[column],
                )
                if row[column] not in (None, 0, "0"):
                    checked += 1
            if table in ("effects", "plot_effects"):
                target_table = effect_table(str(row["actual_type"]))
                if target_table is None:
                    errors.append(
                        f"unknown_effect_type:{table}.{source_id}:{row['actual_type']}"
                    )
                else:
                    add_reference_error(
                        errors,
                        connection,
                        table,
                        source_id,
                        "actual_id",
                        target_table,
                        row["actual_id"],
                    )
                    checked += 1
            elif table == "doodad_phase_funcs":
                target_table = phase_func_table(str(row["actual_func_type"]))
                if target_table is None:
                    errors.append(
                        f"unknown_phase_func_type:{source_id}:{row['actual_func_type']}"
                    )
                else:
                    add_reference_error(
                        errors,
                        connection,
                        table,
                        source_id,
                        "actual_func_id",
                        target_table,
                        row["actual_func_id"],
                    )
                    checked += 1
    return errors, checked


def add_runtime_row(
    closure: dict[str, set[int]], table: str, row_id: Any
) -> bool:
    try:
        value = int(row_id or 0)
    except (TypeError, ValueError):
        return False
    if value <= 0 or value in closure[table]:
        return False
    closure[table].add(value)
    return True


def discover_live_closure(
    connection: sqlite3.Connection, root_id: int
) -> dict[str, set[int]]:
    """Traverse the two roots whose parent skill rows cross the AA8 cache boundary."""
    closure: dict[str, set[int]] = defaultdict(set)
    skill_queue: deque[int] = deque([root_id])
    effect_queue: deque[int] = deque()
    buff_queue: deque[int] = deque()
    seen_skills: set[int] = set()
    seen_effects: set[int] = set()
    seen_buffs: set[int] = set()

    while skill_queue or effect_queue or buff_queue:
        while skill_queue:
            skill_id = skill_queue.popleft()
            if skill_id in seen_skills:
                continue
            seen_skills.add(skill_id)
            add_runtime_row(closure, "skills", skill_id)
            skill = connection.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
            if skill is None:
                continue
            for column, table in SKILL_REFERENCE_RULES:
                if column not in skill.keys():
                    continue
                value = skill[column]
                if table == "skills" and int(value or 0) > 0:
                    skill_queue.append(int(value))
                else:
                    add_runtime_row(closure, table, value)
            for row in connection.execute(
                "SELECT id,effect_id FROM skill_effects WHERE skill_id=? ORDER BY id",
                (skill_id,),
            ):
                add_runtime_row(closure, "skill_effects", row["id"])
                effect_queue.append(int(row["effect_id"]))
            plot_id = int(skill["plot_id"] or 0)
            if plot_id:
                add_runtime_row(closure, "plots", plot_id)
                events = list(
                    connection.execute(
                        "SELECT id FROM plot_events WHERE plot_id=? ORDER BY id", (plot_id,)
                    )
                )
                for event in events:
                    event_id = int(event["id"])
                    add_runtime_row(closure, "plot_events", event_id)
                    for table in (
                        "plot_effects",
                        "plot_event_conditions",
                        "plot_aoe_conditions",
                        "plot_next_events",
                    ):
                        if not table_exists(connection, table):
                            continue
                        for relation in connection.execute(
                            f"SELECT * FROM {quote(table)} WHERE event_id=? ORDER BY id",
                            (event_id,),
                        ):
                            add_runtime_row(closure, table, relation["id"])
                            if table == "plot_effects":
                                target_table = effect_table(str(relation["actual_type"]))
                                if target_table:
                                    add_runtime_row(closure, target_table, relation["actual_id"])
                                    if target_table == "buff_effects":
                                        concrete = connection.execute(
                                            "SELECT buff_id FROM buff_effects WHERE id=?",
                                            (int(relation["actual_id"]),),
                                        ).fetchone()
                                        if concrete:
                                            buff_queue.append(int(concrete["buff_id"]))
                            elif table in ("plot_event_conditions", "plot_aoe_conditions"):
                                add_runtime_row(closure, "plot_conditions", relation["condition_id"])

        while effect_queue:
            effect_id = effect_queue.popleft()
            if effect_id in seen_effects:
                continue
            seen_effects.add(effect_id)
            add_runtime_row(closure, "effects", effect_id)
            effect = connection.execute(
                "SELECT actual_type,actual_id FROM effects WHERE id=?", (effect_id,)
            ).fetchone()
            if effect is None:
                continue
            table = effect_table(str(effect["actual_type"]))
            if table:
                add_runtime_row(closure, table, effect["actual_id"])
                concrete = connection.execute(
                    f"SELECT * FROM {quote(table)} WHERE id=?", (int(effect["actual_id"]),)
                ).fetchone()
                if concrete is not None:
                    if table == "buff_effects":
                        buff_queue.append(int(concrete["buff_id"]))
                    for column in CHARGED_BUFF_RULES.get(table, ()):
                        if column in concrete.keys() and int(concrete[column] or 0) > 0:
                            buff_queue.append(int(concrete[column]))

        while buff_queue:
            buff_id = buff_queue.popleft()
            if buff_id in seen_buffs:
                continue
            seen_buffs.add(buff_id)
            add_runtime_row(closure, "buffs", buff_id)
            buff = connection.execute("SELECT * FROM buffs WHERE id=?", (buff_id,)).fetchone()
            if buff is not None:
                for column, table in BUFF_REFERENCE_RULES:
                    if column not in buff.keys() or int(buff[column] or 0) <= 0:
                        continue
                    if table == "buffs":
                        buff_queue.append(int(buff[column]))
                    elif table == "skills":
                        skill_queue.append(int(buff[column]))
                    else:
                        add_runtime_row(closure, table, buff[column])
            for table in ("buff_tick_effects", "buff_triggers", "buff_unit_modifiers", "tagged_buffs"):
                if not table_exists(connection, table):
                    continue
                for relation in connection.execute(
                    f"SELECT * FROM {quote(table)} WHERE buff_id=? ORDER BY id", (buff_id,)
                ):
                    add_runtime_row(closure, table, relation["id"])
                    if table in ("buff_tick_effects", "buff_triggers"):
                        effect_queue.append(int(relation["effect_id"]))
    return closure


def merge_ids(target: dict[str, set[int]], source: dict[str, Iterable[int]]) -> None:
    for table, ids in source.items():
        target[table].update(int(value) for value in ids)


def manifest_ids(manifest: dict[str, Any]) -> dict[str, set[int]]:
    result: dict[str, set[int]] = defaultdict(set)
    merge_ids(result, manifest.get("native_table_ids", {}))
    for table, record in manifest.get("aa10_structural_candidates", {}).items():
        result[table].update(int(value) for value in record["ids"])
    result["doodad_almighties"].update(AA8_DOODADS)
    result["skills"].update(LIVE_ROOTS)
    return result


def validate_statuses(
    connection: sqlite3.Connection, static_rows: list[dict[str, Any]]
) -> tuple[list[str], dict[int, str]]:
    expected = {int(row["skill_id"]) for row in static_rows} | set(LIVE_ROOTS)
    actual = {
        int(row[0]): str(row[1])
        for row in connection.execute(
            "SELECT skill_id,status FROM native_combat_skill_status WHERE ability_id=7"
        )
        if int(row[0]) in expected
    }
    errors = []
    for skill_id in sorted(expected):
        if actual.get(skill_id) != "enabled":
            errors.append(f"skill_status_not_enabled:{skill_id}:{actual.get(skill_id, 'missing')}")
    return errors, actual


def validate_localization(connection: sqlite3.Connection) -> tuple[list[str], dict[int, str]]:
    errors = []
    names = {}
    for skill_id, expected in EXPECTED_ENGLISH_NAMES.items():
        row = connection.execute(
            "SELECT en_us FROM localized_texts WHERE tbl_name='skills' "
            "AND tbl_column_name='name' AND idx=?",
            (skill_id,),
        ).fetchone()
        actual = str(row[0]) if row and row[0] is not None else ""
        names[skill_id] = actual
        if actual != expected:
            errors.append(f"english_name_mismatch:{skill_id}:{actual!r}!={expected!r}")
    return errors, names


def validate_passives(
    connection: sqlite3.Connection, audit: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    errors = []
    rows = []
    for template_id, expected_buff in PASSIVE_CONTRACTS.items():
        row = connection.execute(
            "SELECT id,ability_id,buff_id,active,level,req_points,skill_points "
            "FROM passive_buffs WHERE id=?",
            (template_id,),
        ).fetchone()
        if row is None:
            errors.append(f"passive_template_missing:{template_id}")
            continue
        record = dict(row)
        rows.append(record)
        if int(row["ability_id"]) != 7 or int(row["buff_id"]) != expected_buff:
            errors.append(f"passive_contract_mismatch:{template_id}:{dict(row)}")
        if not row_exists(connection, "buffs", expected_buff):
            errors.append(f"passive_buff_missing:{template_id}->{expected_buff}")
    accepted = audit.get("passives", {})
    if accepted.get("state") != "accepted_live":
        errors.append(f"passive_live_acceptance_missing:{accepted.get('state')}")
    if set(accepted.get("templates", ())) != set(PASSIVE_TEMPLATES):
        errors.append("passive_audit_template_set_mismatch")
    if set(accepted.get("buffs", ())) != set(PASSIVE_BUFFS):
        errors.append("passive_audit_buff_set_mismatch")
    return errors, rows


def validate_doodads(connection: sqlite3.Connection) -> tuple[list[str], dict[str, Any]]:
    errors = []
    groups = {}
    for doodad_id in AA8_DOODADS:
        if not row_exists(connection, "doodad_almighties", doodad_id):
            errors.append(f"sorcery_doodad_missing:{doodad_id}")
            continue
        ids = [
            int(row[0])
            for row in connection.execute(
                "SELECT id FROM doodad_func_groups WHERE doodad_almighty_id=? ORDER BY id",
                (doodad_id,),
            )
        ]
        groups[str(doodad_id)] = ids
        if not ids:
            errors.append(f"sorcery_doodad_group_missing:{doodad_id}")
    return errors, {"doodad_groups": groups}


def root_report(
    root_id: int,
    closure: dict[str, set[int]],
    english_names: dict[int, str],
    status: str,
    source: str,
) -> dict[str, Any]:
    return {
        "skill_id": root_id,
        "english_name": english_names[root_id],
        "source": source,
        "runtime_status": status,
        "closure_tables": len([ids for ids in closure.values() if ids]),
        "closure_rows": sum(len(ids) for ids in closure.values()),
        "closure_table_counts": {
            table: len(ids) for table, ids in sorted(closure.items()) if ids
        },
        "static_payload_state": (
            "aa10_root_candidate_with_aa8_native_descendants"
            if root_id in LIVE_ROOTS
            else "exact_aa8_native"
        ),
        "acceptance_state": "static_runtime_closed_manual_live_pending",
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    for path in (args.catalog, args.runtime, args.manifest, args.audit):
        if not path.is_file():
            raise FileNotFoundError(path)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    runtime_hash = sha256_file(args.runtime)
    errors: list[str] = []
    warnings: list[str] = []

    if manifest.get("client_build") != CLIENT_BUILD:
        errors.append(f"manifest_client_build_mismatch:{manifest.get('client_build')}")
    if manifest.get("format_version") != 4:
        errors.append(f"manifest_format_mismatch:{manifest.get('format_version')}")
    if str(manifest.get("output", {}).get("sha256", "")).upper() != runtime_hash:
        errors.append("runtime_hash_does_not_match_manifest")
    if audit.get("summary", {}).get("blocked_root_count") != 0:
        errors.append(f"handler_audit_blocked:{audit.get('summary', {}).get('blocked_root_count')}")
    if audit.get("scope", {}).get("live_candidate_roots") != list(LIVE_ROOTS):
        errors.append("handler_audit_live_root_set_mismatch")

    connection = sqlite3.connect(f"file:{args.runtime.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if quick != "ok" or integrity != "ok":
            errors.append(f"sqlite_integrity:{quick}/{integrity}")

        static_rows = static_ability_rows(catalog)
        static_by_root = {int(row["skill_id"]): row for row in static_rows}
        row_maps = catalog_row_maps(catalog)
        all_static: dict[str, set[int]] = defaultdict(set)
        static_closures: dict[int, dict[str, set[int]]] = {}
        for status_row in static_rows:
            root_id = int(status_row["skill_id"])
            closure = static_root_closure(catalog, status_row)
            static_closures[root_id] = closure
            merge_ids(all_static, closure)

        compare_errors, compared_rows = compare_native_rows(
            connection, row_maps, all_static
        )
        errors.extend(compare_errors)

        selected: dict[str, set[int]] = defaultdict(set)
        merge_ids(selected, all_static)
        merge_ids(selected, manifest_ids(manifest))
        live_closures = {
            root_id: discover_live_closure(connection, root_id) for root_id in LIVE_ROOTS
        }
        for closure in live_closures.values():
            merge_ids(selected, closure)

        # Manifest-only rows are still required even when not part of the
        # frozen static catalog (AA8 cached doodads and bounded AA10 links).
        for table, ids in sorted(selected.items()):
            for row_id in sorted(ids):
                if not row_exists(connection, table, row_id):
                    errors.append(f"selected_runtime_row_missing:{table}.{row_id}")

        reference_errors, checked_references = validate_references(connection, selected)
        errors.extend(reference_errors)
        status_errors, statuses = validate_statuses(connection, static_rows)
        errors.extend(status_errors)
        localization_errors, english_names = validate_localization(connection)
        errors.extend(localization_errors)
        passive_errors, passive_rows = validate_passives(connection, audit)
        errors.extend(passive_errors)
        doodad_errors, doodad_report = validate_doodads(connection)
        errors.extend(doodad_errors)

        visible_static = {
            int(row["skill_id"])
            for row in static_rows
            if int(row["skill_id"]) in VISIBLE_ROOTS
        }
        expected_static_visible = set(VISIBLE_ROOTS) - set(LIVE_ROOTS)
        if visible_static != expected_static_visible:
            errors.append(
                f"visible_static_root_set_mismatch:{sorted(visible_static)}"
            )

        roots = []
        for root_id in VISIBLE_ROOTS:
            if root_id in LIVE_ROOTS:
                closure = live_closures[root_id]
                source = "aa10_root_candidate_plus_aa8_native_descendants"
            else:
                closure = static_closures[root_id]
                source = "aa8_native_catalog"
            roots.append(
                root_report(
                    root_id,
                    closure,
                    english_names,
                    statuses.get(root_id, "missing"),
                    source,
                )
            )

        special_enum = {
            int(number): name
            for name, number in re.findall(
                r"^\s*(\w+)\s*=\s*(\d+)",
                (ROOT / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects" / "SpecialEffectType.cs").read_text(encoding="utf-8-sig"),
                re.MULTILINE,
            )
        }
        special_ids = selected.get("special_effects", set())
        unknown_special = []
        if special_ids:
            placeholders = ",".join("?" for _ in special_ids)
            for row in connection.execute(
                f"SELECT id,special_effect_type_id FROM special_effects "
                f"WHERE id IN ({placeholders}) ORDER BY id",
                tuple(sorted(special_ids)),
            ):
                if int(row["special_effect_type_id"]) not in special_enum:
                    unknown_special.append(dict(row))
        if unknown_special:
            errors.append(f"unknown_special_effect_enums:{unknown_special}")

        crosswalk_classes = Counter()
        for root in audit.get("roots", []):
            crosswalk_classes.update(root.get("crosswalk_classifications", {}))
        if crosswalk_classes.get("conflict", 0):
            warnings.append(
                "AA10 crosswalk conflicts remain comparative only; they do not override "
                "the exact AA8 catalog rows or the explicitly bounded root/structural candidates."
            )

        errors = sorted(set(errors))
        return {
            "format_version": 4,
            "client_build": CLIENT_BUILD,
            "authority": {
                "aa8_native_catalog": "field_exact_runtime_authority",
                "aa8_runtime_packets": "live_root_identity_and_client_reachability",
                "aa10_crosswalk": "gap_reduction_only",
                "aa10_structural_candidates": "bounded_doodad_relation_shape_only",
                "manual_live_test": "final_behavioral_acceptance_pending",
            },
            "sources": {
                "catalog": {"path": str(args.catalog.resolve()), "sha256": sha256_file(args.catalog)},
                "runtime": {"path": str(args.runtime.resolve()), "sha256": runtime_hash},
                "manifest": {"path": str(args.manifest.resolve()), "sha256": sha256_file(args.manifest)},
                "handler_audit": {"path": str(args.audit.resolve()), "sha256": sha256_file(args.audit)},
            },
            "roots": roots,
            "passives": {
                "state": "accepted_live_and_runtime_resolved" if not passive_errors else "failed",
                "templates": passive_rows,
            },
            "doodads": doodad_report,
            "crosswalk_classifications": dict(sorted(crosswalk_classes.items())),
            "warnings": warnings,
            "errors": errors,
            "checks": {
                "quick_check": quick,
                "integrity_check": integrity,
                "static_ability_roots": len(static_rows),
                "visible_active_roots": len(roots),
                "exact_aa8_rows_compared": compared_rows,
                "selected_runtime_rows": sum(len(ids) for ids in selected.values()),
                "selected_runtime_tables": len([ids for ids in selected.values() if ids]),
                "references_checked": checked_references,
                "special_effect_descriptors": len(special_ids),
                "unknown_special_effect_enums": len(unknown_special),
            },
            "summary": {
                "root_count": len(roots),
                "passive_count": len(passive_rows),
                "error_count": len(errors),
                "warning_count": len(warnings),
                "static_runtime_state": "closed" if not errors else "failed",
                "manual_live_state": "pending",
            },
        }
    finally:
        connection.close()


def write_csv(path: Path, report: dict[str, Any]) -> None:
    columns = (
        "skill_id",
        "english_name",
        "source",
        "runtime_status",
        "closure_tables",
        "closure_rows",
        "static_payload_state",
        "acceptance_state",
        "closure_table_counts",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in report["roots"]:
            writer.writerow(
                {
                    key: json.dumps(row[key], ensure_ascii=False, sort_keys=True)
                    if isinstance(row[key], dict)
                    else row[key]
                    for key in columns
                }
            )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(canonical(report), encoding="utf-8")
    write_csv(args.output_csv, report)
    print(canonical(report["summary"]), end="")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
