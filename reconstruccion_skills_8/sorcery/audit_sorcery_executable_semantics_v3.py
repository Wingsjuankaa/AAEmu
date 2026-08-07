"""Audit the executable AA8 Sorcery graph from every native AA8 entrypoint.

Unlike the legacy v2 audit, this tool does not inherit a pre-expanded static
catalogue closure.  It starts at the twelve player-facing AA8 Sorcery skills,
the twelve decoded heir successors, the three login-stage preview skills and
the three contextual Magic Circle return skills.  It follows the directed plot
graph from position 1 and recursively expands SkillUse and the client-driven
Combo transition graph, buff
ticks/triggers and skill controllers.  The output is evidence, not a claim of
live acceptance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DEFAULT_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v10.sqlite3"
)
DEFAULT_MANIFEST = HERE / "generated" / "sorcery-specialization-v10.manifest.json"
DEFAULT_CROSSWALK = Path(
    r"E:\AAEmu-Research\output\aa8-client-forensics\aa8-aa10-crosswalk-v1.sqlite3"
)
DEFAULT_JSON = HERE / "generated" / "sorcery-executable-semantics-audit-v3.json"
DEFAULT_CSV = HERE / "generated" / "sorcery-executable-semantics-matrix-v3.csv"

CLIENT_BUILD = "Kakao 8.0.3.12 r558734"
ABILITY_ID = 7
BASE_ROOTS = (
    10151, 10153, 10664, 10667, 10670, 10752,
    11314, 11939, 11967, 12796, 14774, 23593,
)
HEIR_ROOTS = (
    36474, 36475, 36476, 36477, 36478, 36479,
    39669, 39674, 41222, 41223, 43068, 43185,
)
PUBLIC_ROOTS = BASE_ROOTS + HEIR_ROOTS
LOGIN_STAGE_ROOTS = (12789, 12790, 12791)
CONTEXTUAL_ROOTS = (42012, 43464, 43465)
INTERNAL_ROOTS = LOGIN_STAGE_ROOTS + CONTEXTUAL_ROOTS
AUDITED_ROOTS = PUBLIC_ROOTS + INTERNAL_ROOTS

SPECIAL_SKILL_USE = 33
SPECIAL_COMBO = 48
AREA_TARGET_UPDATE_METHODS = (5, 6, 7)

BUFF_TRIGGER_EVENT_STATES = {
    "Started": "implemented_owner_buff_started",
    "Timeout": "implemented_owner_buff_timeout",
    "Absorption": "implemented_absorption_overflow_and_single_exhaustion",
}

BUFF_LINK_FIELDS = (
    "link_buff_id",
    "transform_buff_id",
    "aura_slave_buff_id",
    "crowd_buff_id",
)
SKILL_BUFF_FIELDS = (
    "channeling_buff_id",
    "channeling_target_buff_id",
    "toggle_buff_id",
)

CORE_STATES = {
    "AggroEffect": "implemented_aa8_native_formula",
    "BuffEffect": "implemented",
    "CombatResourceEffect": "implemented_aa8_resource_protocol",
    "DamageEffect": "implemented_aa8_native_formula",
    "DispelEffect": "implemented",
    "ExtendChargeEffect": "implemented_aa8_tooltip_formula_and_crosswalk_resource_contract",
    "HighAbilityResourceEffect": "implemented_from_stable_aa10_type_migration",
    "InteractionEffect": "implemented",
    "PhysicalExplosionEffect": "cryengine_boundary_declarative",
    "ResetAoeDiminishingEffect": "implemented",
    "SpecialEffect": "router",
}

SPECIAL_STATES = {
    "Anim": "client_declarative",
    "FxGroup": "client_declarative",
    "FxGroupAnim": "client_declarative",
    "Projectile": "client_declarative",
    "ProjectileAnim": "client_declarative",
    "CombatText": "client_declarative",
    "ManaCost": "implemented_aa8_native_formula",
    "Cooldown": "implemented",
    "GlobalCooldown": "implemented",
    "StopManaRegen": "implemented",
    "CancelStealth": "implemented",
    "CancelOngoingBuff": "implemented",
    "AutoAttack": "implemented",
    "Combo": "client_driven_transition_server_accepts_child_request",
    "KnockBack": "implemented_native_client_plus_npc_proxy",
    "DisturbCasting": "implemented",
    "SkillUse": "implemented_recursive_skill_use",
    "SpawnDoodad": "implemented",
    "ReturnToSavedPosition": "implemented",
}

CONDITION_STATES = {
    "Level": "implemented",
    "Relation": "implemented",
    "Direction": "implemented",
    "BuffTag": "implemented_stack_aware",
    "WeaponEquipStatus": "implemented_aa8_domain",
    "Chance": "review_off_by_one",
    "Dead": "implemented",
    "CombatDiceResult": "implemented_reuses_damage_roll",
    "InstrumentType": "implemented",
    "Range": "implemented_edge_to_edge_model_radii",
    "Variable": "implemented",
    "UnitAttrib": "no_op",
    "Actability": "no_op",
    "Stealth": "implemented",
    "Visible": "implemented",
    "ABLevel": "implemented",
}

BLOCKING_STATES = {
    "missing",
    "no_op",
    "review_required",
    "review_off_by_one",
    "candidate_formula_native_descriptor_only",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
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


def enum_values(path: Path, enum_name: str) -> dict[int, str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(
        rf"\benum\s+{re.escape(enum_name)}\s*\{{(?P<body>.*?)^\s*\}}",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"enum {enum_name} not found in {path}")
    return {
        int(number): name
        for name, number in re.findall(
            r"^\s*(\w+)\s*=\s*(\d+)", match.group("body"), re.MULTILINE
        )
    }


def descriptor_table(actual_type: str) -> str | None:
    if actual_type == "SkillController":
        return "skill_controllers"
    if not actual_type.endswith("Effect"):
        return None
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", actual_type).lower()
    return f"{snake}s"


class Runtime:
    def __init__(self, path: Path):
        self.path = path
        self.connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row
        self._tables = {
            str(row[0])
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        self._row_cache: dict[tuple[str, int], dict[str, Any] | None] = {}

    def close(self) -> None:
        self.connection.close()

    def has_table(self, table: str) -> bool:
        return table in self._tables

    def row(self, table: str, row_id: int) -> dict[str, Any] | None:
        key = (table, int(row_id))
        if key not in self._row_cache:
            if table not in self._tables:
                self._row_cache[key] = None
            else:
                row = self.connection.execute(
                    f"SELECT * FROM {table} WHERE id=?", (int(row_id),)
                ).fetchone()
                self._row_cache[key] = dict(row) if row else None
        return self._row_cache[key]

    def rows(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.connection.execute(sql, tuple(params))]


class Closure:
    def __init__(self, runtime: Runtime, special_names: dict[int, str]):
        self.runtime = runtime
        self.special_names = special_names
        self.ids: dict[str, set[int]] = defaultdict(set)
        self.edges: set[tuple[str, int, str, str, int]] = set()
        self.effect_types: Counter[str] = Counter()
        self.special_types: Counter[str] = Counter()
        self.condition_types: Counter[str] = Counter()
        self.controller_kinds: Counter[int] = Counter()
        self.buff_trigger_events: Counter[str] = Counter()
        self.nonzero_special_tail: list[dict[str, Any]] = []
        self.nonzero_skill_use_value4: list[dict[str, Any]] = []
        self.missing_rows: list[dict[str, Any]] = []
        self._skill_queue: deque[int] = deque()
        self._effect_queue: deque[int] = deque()
        self._buff_queue: deque[int] = deque()
        self._controller_queue: deque[int] = deque()
        self._processed_skills: set[int] = set()
        self._processed_effects: set[int] = set()
        self._processed_buffs: set[int] = set()
        self._processed_controllers: set[int] = set()

    def edge(
        self,
        source_table: str,
        source_id: int,
        relation: str,
        target_table: str,
        target_id: int,
    ) -> None:
        if int(target_id) > 0:
            self.edges.add(
                (source_table, int(source_id), relation, target_table, int(target_id))
            )

    def add_row(self, table: str, row_id: int, required: bool = True) -> dict[str, Any] | None:
        if int(row_id) <= 0:
            return None
        row = self.runtime.row(table, int(row_id))
        if row:
            self.ids[table].add(int(row_id))
        elif required:
            missing = {"table": table, "id": int(row_id)}
            if missing not in self.missing_rows:
                self.missing_rows.append(missing)
        return row

    def enqueue_skill(self, skill_id: int) -> None:
        if int(skill_id) > 0 and int(skill_id) not in self._processed_skills:
            self._skill_queue.append(int(skill_id))

    def enqueue_effect(self, effect_id: int) -> None:
        if int(effect_id) > 0 and int(effect_id) not in self._processed_effects:
            self._effect_queue.append(int(effect_id))

    def enqueue_buff(self, buff_id: int) -> None:
        if int(buff_id) > 0 and int(buff_id) not in self._processed_buffs:
            self._buff_queue.append(int(buff_id))

    def enqueue_controller(self, controller_id: int) -> None:
        if int(controller_id) > 0 and int(controller_id) not in self._processed_controllers:
            self._controller_queue.append(int(controller_id))

    def build(self, root_skill_id: int) -> "Closure":
        self.enqueue_skill(root_skill_id)
        while self._skill_queue or self._effect_queue or self._buff_queue or self._controller_queue:
            while self._skill_queue:
                self._process_skill(self._skill_queue.popleft())
            while self._effect_queue:
                self._process_effect(self._effect_queue.popleft())
            while self._buff_queue:
                self._process_buff(self._buff_queue.popleft())
            while self._controller_queue:
                self._process_controller(self._controller_queue.popleft())
        return self

    def _process_skill(self, skill_id: int) -> None:
        if skill_id in self._processed_skills:
            return
        self._processed_skills.add(skill_id)
        skill = self.add_row("skills", skill_id)
        if not skill:
            return

        for field in SKILL_BUFF_FIELDS:
            buff_id = int(skill.get(field) or 0)
            if buff_id:
                self.edge("skills", skill_id, field, "buffs", buff_id)
                self.enqueue_buff(buff_id)

        controller_id = int(skill.get("skill_controller_id") or 0)
        if controller_id:
            self.edge("skills", skill_id, "skill_controller_id", "skill_controllers", controller_id)
            self.enqueue_controller(controller_id)

        for row in self.runtime.rows(
            "SELECT * FROM skill_effects WHERE skill_id=? ORDER BY id", (skill_id,)
        ):
            self.ids["skill_effects"].add(int(row["id"]))
            effect_id = int(row["effect_id"])
            self.edge("skills", skill_id, "skill_effect", "effects", effect_id)
            self.enqueue_effect(effect_id)

        plot_id = int(skill.get("plot_id") or 0)
        if plot_id:
            self.edge("skills", skill_id, "plot_id", "plots", plot_id)
            self._process_plot(plot_id)

    def _process_plot(self, plot_id: int) -> None:
        if plot_id in self.ids["plots"]:
            return
        if not self.add_row("plots", plot_id):
            return
        roots = self.runtime.rows(
            "SELECT id FROM plot_events WHERE plot_id=? AND position=1 ORDER BY id",
            (plot_id,),
        )
        if not roots:
            self.missing_rows.append(
                {"table": "plot_events", "id": 0, "context": f"plot {plot_id} position 1"}
            )
            return
        event_queue = deque(int(row["id"]) for row in roots)
        seen_events: set[int] = set()
        while event_queue:
            event_id = event_queue.popleft()
            if event_id in seen_events:
                continue
            seen_events.add(event_id)
            event = self.add_row("plot_events", event_id)
            if not event:
                continue
            self.edge("plots", plot_id, "reachable_event", "plot_events", event_id)

            target_update_method_id = int(event.get("target_update_method_id") or 0)
            shape_id = int(event.get("target_update_method_param1") or 0)
            if target_update_method_id in AREA_TARGET_UPDATE_METHODS and shape_id:
                self.edge("plot_events", event_id, "area_shape", "aoe_shapes", shape_id)
                self.add_row("aoe_shapes", shape_id)

            for join_table in ("plot_event_conditions", "plot_aoe_conditions"):
                for join in self.runtime.rows(
                    f"SELECT * FROM {join_table} WHERE event_id=? ORDER BY position,id",
                    (event_id,),
                ):
                    self.ids[join_table].add(int(join["id"]))
                    condition_id = int(join["condition_id"])
                    self.edge(join_table, int(join["id"]), "condition", "plot_conditions", condition_id)
                    condition = self.add_row("plot_conditions", condition_id)
                    if condition:
                        kind_id = int(condition["kind_id"])
                        self.condition_types[self._condition_name(kind_id)] += 1

            for plot_effect in self.runtime.rows(
                "SELECT * FROM plot_effects WHERE event_id=? ORDER BY position,id",
                (event_id,),
            ):
                plot_effect_id = int(plot_effect["id"])
                self.ids["plot_effects"].add(plot_effect_id)
                self._process_descriptor(
                    str(plot_effect["actual_type"]),
                    int(plot_effect["actual_id"]),
                    "plot_effects",
                    plot_effect_id,
                )

            for next_event in self.runtime.rows(
                "SELECT * FROM plot_next_events WHERE event_id=? ORDER BY position,id",
                (event_id,),
            ):
                next_id = int(next_event["id"])
                target_event_id = int(next_event["next_event_id"])
                self.ids["plot_next_events"].add(next_id)
                self.edge("plot_events", event_id, "next_event", "plot_events", target_event_id)
                event_queue.append(target_event_id)

    def _condition_name(self, kind_id: int) -> str:
        return CONDITION_NAMES.get(kind_id, f"Unknown{kind_id}")

    def _process_effect(self, effect_id: int) -> None:
        if effect_id in self._processed_effects:
            return
        self._processed_effects.add(effect_id)
        effect = self.add_row("effects", effect_id)
        if not effect:
            return
        self._process_descriptor(
            str(effect["actual_type"]), int(effect["actual_id"]), "effects", effect_id
        )

    def _process_descriptor(
        self, actual_type: str, actual_id: int, source_table: str, source_id: int
    ) -> None:
        self.effect_types[actual_type] += 1
        table = descriptor_table(actual_type)
        if not table:
            self.missing_rows.append(
                {"table": "descriptor_mapping", "id": actual_id, "actual_type": actual_type}
            )
            return
        self.edge(source_table, source_id, "actual_descriptor", table, actual_id)
        descriptor = self.add_row(table, actual_id)
        if not descriptor:
            return
        if actual_type == "BuffEffect":
            buff_id = int(descriptor.get("buff_id") or 0)
            self.edge(table, actual_id, "buff_id", "buffs", buff_id)
            self.enqueue_buff(buff_id)
        elif actual_type == "ExtendChargeEffect":
            buff_id = int(descriptor.get("charge_buff_id") or 0)
            if buff_id:
                self.edge(table, actual_id, "charge_buff_id", "buffs", buff_id)
                self.enqueue_buff(buff_id)
        elif actual_type == "DamageEffect":
            for field in ("charged_buff_id", "target_charged_buff_id"):
                buff_id = int(descriptor.get(field) or 0)
                if buff_id:
                    self.edge(table, actual_id, field, "buffs", buff_id)
                    self.enqueue_buff(buff_id)
        elif actual_type == "SpecialEffect":
            special_id = int(descriptor["special_effect_type_id"])
            special_name = self.special_names.get(special_id, f"Unknown{special_id}")
            self.special_types[special_name] += 1
            if any(int(descriptor.get(f"value{index}") or 0) for index in (5, 6, 7)):
                self.nonzero_special_tail.append(
                    {
                        "id": actual_id,
                        "type_id": special_id,
                        "type": special_name,
                        "value5": int(descriptor.get("value5") or 0),
                        "value6": int(descriptor.get("value6") or 0),
                        "value7": int(descriptor.get("value7") or 0),
                    }
                )
            if special_id in (SPECIAL_SKILL_USE, SPECIAL_COMBO):
                next_skill_id = int(descriptor.get("value1") or 0)
                self.edge(table, actual_id, special_name, "skills", next_skill_id)
                self.enqueue_skill(next_skill_id)
                if special_id == SPECIAL_SKILL_USE and int(descriptor.get("value4") or 0):
                    self.nonzero_skill_use_value4.append(
                        {
                            "id": actual_id,
                            "child_skill_id": next_skill_id,
                            "delay": int(descriptor.get("value2") or 0),
                            "chance": int(descriptor.get("value3") or 0),
                            "value4": int(descriptor.get("value4") or 0),
                            "state": "preserved_not_consumed_by_supplied_r575_binaries",
                        }
                    )
        elif actual_type == "SkillController":
            self.enqueue_controller(actual_id)

    def _process_buff(self, buff_id: int) -> None:
        if buff_id in self._processed_buffs:
            return
        self._processed_buffs.add(buff_id)
        buff = self.add_row("buffs", buff_id)
        if not buff:
            return
        for field in BUFF_LINK_FIELDS:
            linked_id = int(buff.get(field) or 0)
            if linked_id and self.runtime.row("buffs", linked_id):
                self.edge("buffs", buff_id, field, "buffs", linked_id)
                self.enqueue_buff(linked_id)
        controller_id = int(buff.get("skill_controller_id") or 0)
        if controller_id:
            self.edge("buffs", buff_id, "skill_controller_id", "skill_controllers", controller_id)
            self.enqueue_controller(controller_id)
        for table in ("buff_triggers", "buff_tick_effects"):
            for row in self.runtime.rows(
                f"SELECT * FROM {table} WHERE buff_id=? ORDER BY id", (buff_id,)
            ):
                row_id = int(row["id"])
                effect_id = int(row["effect_id"])
                self.ids[table].add(row_id)
                if table == "buff_triggers":
                    event_id = int(row.get("event_id") or 0)
                    event_name = BUFF_EVENT_NAMES.get(event_id, f"Unknown{event_id}")
                    self.buff_trigger_events[event_name] += 1
                self.edge(table, row_id, "effect_id", "effects", effect_id)
                self.enqueue_effect(effect_id)

    def _process_controller(self, controller_id: int) -> None:
        if controller_id in self._processed_controllers:
            return
        self._processed_controllers.add(controller_id)
        controller = self.add_row("skill_controllers", controller_id)
        if not controller:
            return
        kind_id = int(controller.get("kind_id") or 0)
        self.controller_kinds[kind_id] += 1
        end_skill_id = int(controller.get("end_skill_id") or 0)
        if end_skill_id:
            self.edge("skill_controllers", controller_id, "end_skill_id", "skills", end_skill_id)
            self.enqueue_skill(end_skill_id)

    def record(self) -> dict[str, Any]:
        core_states = {
            name: handler_state(name, special=False)
            for name in sorted(self.effect_types)
        }
        special_states = {
            name: handler_state(name, special=True)
            for name in sorted(self.special_types)
        }
        condition_states = {
            name: CONDITION_STATES.get(name, "missing")
            for name in sorted(self.condition_types)
        }
        trigger_states = {
            name: BUFF_TRIGGER_EVENT_STATES.get(name, "missing")
            for name in sorted(self.buff_trigger_events)
        }
        blockers = []
        for family, states in (
            ("core", core_states),
            ("special", special_states),
            ("condition", condition_states),
            ("buff_trigger_event", trigger_states),
        ):
            blockers.extend(
                f"{family}:{name}:{state}"
                for name, state in states.items()
                if state in BLOCKING_STATES
            )
        if self.missing_rows:
            blockers.append(f"data:missing_rows:{len(self.missing_rows)}")
        return {
            "closure_ids": {table: sorted(ids) for table, ids in sorted(self.ids.items())},
            "closure_counts": {table: len(ids) for table, ids in sorted(self.ids.items())},
            "effect_types": dict(sorted(self.effect_types.items())),
            "special_types": dict(sorted(self.special_types.items())),
            "condition_types": dict(sorted(self.condition_types.items())),
            "controller_kinds": {str(key): value for key, value in sorted(self.controller_kinds.items())},
            "buff_trigger_events": dict(sorted(self.buff_trigger_events.items())),
            "buff_trigger_event_states": trigger_states,
            "core_handler_states": core_states,
            "special_handler_states": special_states,
            "condition_handler_states": condition_states,
            "nonzero_special_value5_7": sorted(self.nonzero_special_tail, key=lambda row: row["id"]),
            "nonzero_skill_use_value4": sorted(
                self.nonzero_skill_use_value4, key=lambda row: row["id"]
            ),
            "external_native_unknowns": (
                ["SkillUse.value4:present_but_not_consumed_by_supplied_r575_binaries"]
                if self.nonzero_skill_use_value4 else []
            ),
            "missing_rows": sorted(self.missing_rows, key=lambda row: (row["table"], row["id"])),
            "blockers": sorted(set(blockers)),
            "edges": [
                {
                    "source": f"{source_table}:{source_id}",
                    "relation": relation,
                    "target": f"{target_table}:{target_id}",
                }
                for source_table, source_id, relation, target_table, target_id
                in sorted(self.edges)
            ],
        }


def handler_state(name: str, special: bool) -> str:
    base = ROOT / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects"
    path = base / ("SpecialEffects" if special else "") / f"{name}.cs"
    if not path.is_file():
        # SkillController is a descriptor consumed by PlotTree's controller
        # scheduler, not an EffectTemplate class under Effects/.
        if not special and name == "SkillController":
            return CORE_STATES.get(name, "missing")
        return "missing"
    text = path.read_text(encoding="utf-8-sig")
    if "NotImplementedException" in text:
        return "missing"
    return (SPECIAL_STATES if special else CORE_STATES).get(name, "review_required")


def crosswalk_rows(
    path: Path, selected: dict[str, set[int]]
) -> tuple[dict[str, Counter[str]], list[dict[str, Any]]]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    details: list[dict[str, Any]] = []
    if not path.is_file():
        return result, details
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        for table, ids in sorted(selected.items()):
            if not ids:
                continue
            values = sorted(ids)
            for start in range(0, len(values), 500):
                chunk = values[start:start + 500]
                marks = ",".join("?" for _ in chunk)
                rows = connection.execute(
                    "SELECT table_name,aa8_id,aa10_id,classification,relation_state,"
                    "property_state,balance_state,changed_relation_columns_json,"
                    "changed_property_columns_json,balance_columns_json "
                    f"FROM row_comparisons WHERE table_name=? AND aa8_id IN ({marks})",
                    (table, *chunk),
                )
                for row in rows:
                    item = dict(row)
                    classification = str(item["classification"])
                    result[table][classification] += 1
                    if table in {
                        "extend_charge_effects",
                        "high_ability_resource_effects",
                        "combat_resource_effects",
                    }:
                        details.append(item)
    finally:
        connection.close()
    return result, details


def merge_selected(records: list[dict[str, Any]]) -> dict[str, set[int]]:
    selected: dict[str, set[int]] = defaultdict(set)
    for record in records:
        for table, ids in record["closure_ids"].items():
            selected[table].update(int(value) for value in ids)
    return selected


def unique_buff_trigger_events(
    runtime_path: Path, selected: dict[str, set[int]]
) -> dict[str, int]:
    """Count each reachable trigger once across overlapping root closures."""
    trigger_ids = sorted(selected.get("buff_triggers", set()))
    if not trigger_ids:
        return {}
    counts: Counter[str] = Counter()
    connection = sqlite3.connect(f"file:{runtime_path.as_posix()}?mode=ro", uri=True)
    try:
        for start in range(0, len(trigger_ids), 500):
            chunk = trigger_ids[start:start + 500]
            marks = ",".join("?" for _ in chunk)
            for (event_id,) in connection.execute(
                f"SELECT event_id FROM buff_triggers WHERE id IN ({marks})", chunk
            ):
                event_id = int(event_id or 0)
                counts[BUFF_EVENT_NAMES.get(event_id, f"Unknown{event_id}")] += 1
    finally:
        connection.close()
    return dict(sorted(counts.items()))


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    global CONDITION_NAMES, BUFF_EVENT_NAMES
    special_names = enum_values(
        ROOT / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Effects" / "SpecialEffectType.cs",
        "SpecialType",
    )
    CONDITION_NAMES = enum_values(
        ROOT / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Plots" / "PlotConditionType.cs",
        "PlotConditionType",
    )
    BUFF_EVENT_NAMES = enum_values(
        ROOT / "AAEmu.Game" / "Models" / "Game" / "Skills" / "Static" / "BuffTriggerEventKind.cs",
        "BuffTriggerEventKind",
    )
    runtime = Runtime(args.runtime)
    try:
        roots: list[dict[str, Any]] = []
        for root_id in AUDITED_ROOTS:
            closure = Closure(runtime, special_names).build(root_id).record()
            skill = runtime.row("skills", root_id) or {}
            roots.append(
                {
                    "skill_id": root_id,
                    "name": skill.get("name"),
                    "root_kind": (
                        "base" if root_id in BASE_ROOTS else
                        "heir" if root_id in HEIR_ROOTS else
                        "login_stage" if root_id in LOGIN_STAGE_ROOTS else
                        "contextual"
                    ),
                    **closure,
                }
            )

        # `active` is part of the native passive contract, not a catalogue
        # enable/disable flag.  All Sorcery passive rows are learnable and must
        # be included in the executable closure (AA8 currently stores 0 for all
        # six of them).
        passive_rows = runtime.rows(
            "SELECT * FROM passive_buffs WHERE ability_id=? ORDER BY id",
            (ABILITY_ID,),
        )
        passive_closures: list[dict[str, Any]] = []
        for passive in passive_rows:
            closure = Closure(runtime, special_names)
            closure.enqueue_buff(int(passive["buff_id"]))
            while closure._skill_queue or closure._effect_queue or closure._buff_queue or closure._controller_queue:
                while closure._skill_queue:
                    closure._process_skill(closure._skill_queue.popleft())
                while closure._effect_queue:
                    closure._process_effect(closure._effect_queue.popleft())
                while closure._buff_queue:
                    closure._process_buff(closure._buff_queue.popleft())
                while closure._controller_queue:
                    closure._process_controller(closure._controller_queue.popleft())
            passive_closures.append(
                {"passive": passive, **closure.record()}
            )
    finally:
        runtime.close()

    all_records = roots + passive_closures
    selected = merge_selected(all_records)
    crosswalk, crosswalk_details = crosswalk_rows(args.crosswalk, selected)
    reachable_buff_trigger_events = unique_buff_trigger_events(args.runtime, selected)

    blocker_roots = [row["skill_id"] for row in roots if row["blockers"]]
    missing_specials = sorted(
        {
            blocker.split(":")[1]
            for row in roots
            for blocker in row["blockers"]
            if blocker.startswith("special:")
        }
    )
    return {
        "format_version": 3,
        "client_build": CLIENT_BUILD,
        "authority": {
            "aa8_runtime": "root_rows_relations_and_directed_executable_graph",
            "aa10_crosswalk": "mandatory_gap_reduction_and_identity_migration_only",
            "server_source": "handler_presence_and_semantics_under_test",
            "manual_runtime": "final_behavioral_acceptance_only",
        },
        "sources": {
            "runtime": {"path": str(args.runtime.resolve()), "sha256": sha256_file(args.runtime)},
            "manifest": {"path": str(args.manifest.resolve()), "sha256": sha256_file(args.manifest)},
            "crosswalk": {"path": str(args.crosswalk.resolve()), "sha256": sha256_file(args.crosswalk)},
        },
        "scope": {
            "base_roots": list(BASE_ROOTS),
            "heir_roots": list(HEIR_ROOTS),
            "public_root_count": len(PUBLIC_ROOTS),
            "login_stage_roots": list(LOGIN_STAGE_ROOTS),
            "contextual_roots": list(CONTEXTUAL_ROOTS),
            "internal_root_count": len(INTERNAL_ROOTS),
            "audited_root_count": len(AUDITED_ROOTS),
            "passive_count": len(passive_closures),
            "selected_counts": {table: len(ids) for table, ids in sorted(selected.items())},
        },
        "crosswalk_classifications": {
            table: dict(sorted(counts.items())) for table, counts in sorted(crosswalk.items())
        },
        "crosswalk_resource_migration_details": crosswalk_details,
        "roots": roots,
        "passives": passive_closures,
        "summary": {
            "root_count": len(roots),
            "roots_with_blockers": blocker_roots,
            "blocked_root_count": len(blocker_roots),
            "missing_or_blocking_specials": missing_specials,
            "roots_with_missing_rows": [
                row["skill_id"] for row in roots if row["missing_rows"]
            ],
            "roots_using_special_values_5_to_7": [
                row["skill_id"] for row in roots if row["nonzero_special_value5_7"]
            ],
            "reachable_buff_trigger_events": reachable_buff_trigger_events,
            "roots_using_nonzero_skill_use_value4": [
                row["skill_id"] for row in roots if row["nonzero_skill_use_value4"]
            ],
            "roots_with_external_native_unknowns": [
                row["skill_id"] for row in roots if row["external_native_unknowns"]
            ],
        },
    }


def write_csv(path: Path, report: dict[str, Any]) -> None:
    columns = (
        "skill_id", "name", "root_kind", "closure_skill_ids", "effect_types",
        "special_types", "condition_types", "controller_kinds", "blockers",
        "buff_trigger_events", "missing_rows", "nonzero_special_value5_7",
        "nonzero_skill_use_value4",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in report["roots"]:
            writer.writerow(
                {
                    "skill_id": row["skill_id"],
                    "name": row["name"],
                    "root_kind": row["root_kind"],
                    "closure_skill_ids": json.dumps(row["closure_ids"].get("skills", [])),
                    "effect_types": json.dumps(row["effect_types"], sort_keys=True),
                    "special_types": json.dumps(row["special_types"], sort_keys=True),
                    "condition_types": json.dumps(row["condition_types"], sort_keys=True),
                    "controller_kinds": json.dumps(row["controller_kinds"], sort_keys=True),
                    "buff_trigger_events": json.dumps(row["buff_trigger_events"], sort_keys=True),
                    "blockers": json.dumps(row["blockers"], sort_keys=True),
                    "missing_rows": json.dumps(row["missing_rows"], sort_keys=True),
                    "nonzero_special_value5_7": json.dumps(row["nonzero_special_value5_7"], sort_keys=True),
                    "nonzero_skill_use_value4": json.dumps(row["nonzero_skill_use_value4"], sort_keys=True),
                }
            )


CONDITION_NAMES: dict[int, str] = {}
BUFF_EVENT_NAMES: dict[int, str] = {}


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
