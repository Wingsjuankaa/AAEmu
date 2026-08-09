#!/usr/bin/env python3
"""Generate the permanent AA8 Battlerage V2 Mechanics Lab smoke matrix."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "mechanics-lab" / "scenarios"


CHARACTER = {
    "id": 189999,
    "kind": "character",
    "name": "Battlerage",
    "level": 55,
    "ability_level": 55,
    "hp": 100000,
    "max_hp": 100000,
    "mp": 100000,
    "max_mp": 100000,
    "faction_id": 1,
    "x": 0,
    "y": 0,
    "z": 0,
    # Unit combat attributes use the server's x1000 fixed-point scale.  These
    # values represent 800 weapon DPS and 500 additive melee DPS in AA8 UI
    # units; using the display values directly makes low-multiplier chains
    # randomly truncate to zero before the integer damage packet is built.
    "melee_dps": 800000,
    "melee_dps_inc": 500000,
    "level_dps": 100,
    "mainhand_item_id": 5569,
    "mainhand_holdable_id": 6,
}

TARGET = {
    "id": 61849,
    "kind": "npc",
    "template_id": 2308,
    "name": "Battlerage target",
    "level": 50,
    "hp": 1000000,
    "max_hp": 1000000,
    "mp": 1000,
    "max_mp": 1000,
    "faction_id": 2,
    "x": 0,
    "y": 3,
    "z": 0,
    "armor": 0,
    "magic_resistance": 0,
}


def cast(skill_id: int) -> dict:
    return {
        "type": "cast",
        "actor_id": CHARACTER["id"],
        "target_id": TARGET["id"],
        "skill_id": skill_id,
        "x": TARGET["x"],
        "y": TARGET["y"],
        "z": TARGET["z"],
    }


def advance(milliseconds: int = 6000) -> dict:
    return {"type": "advance", "milliseconds": milliseconds}


SCENARIOS = {
    "battlerage_frenzy_buff": ([cast(10455), advance(100)], False),
    "battlerage_precision_strike": ([cast(12026), advance()], True),
    "battlerage_bondbreaker_release": ([cast(12034), advance(100)], False),
    "battlerage_whirlwind_slash": ([cast(13282), advance()], True),
    "battlerage_tiger_strike": ([cast(13315), advance()], True),
    "battlerage_terrifying_roar": ([cast(18308), advance()], False),
    "battlerage_ollos_hammer": ([cast(18757), advance()], True),
    "battlerage_triple_slash_ancestral_flame": (
        [cast(36401), advance(600), cast(36402), advance(600), cast(36403), advance()],
        True,
    ),
    "battlerage_triple_slash_ancestral_lightning": (
        [cast(36404), advance(600), cast(36405), advance(600), cast(36406), advance()],
        True,
    ),
    "battlerage_precision_strike_ancestral_flame": ([cast(36446), advance()], True),
    "battlerage_precision_strike_ancestral_lightning": ([cast(36447), advance()], True),
    "battlerage_tiger_strike_ancestral_lightning": ([cast(36448), advance()], True),
    "battlerage_tiger_strike_ancestral_wave": ([cast(36449), advance()], True),
    "battlerage_behind_enemy_lines_ancestral_flame": ([cast(39661), advance()], True),
    "battlerage_behind_enemy_lines_ancestral_mist": ([cast(39662), advance()], True),
    "battlerage_sunder_earth_ancestral_flame": ([cast(41217), advance()], True),
    "battlerage_sunder_earth_ancestral_quake": ([cast(41218), advance()], True),
    "battlerage_frenzy_ancestral_flame": ([cast(43188), advance(100)], False),
    "battlerage_frenzy_ancestral_wave": ([cast(43189), advance(100)], False),
}


def build(name: str, actions: list[dict], expect_damage: bool, index: int) -> dict:
    actors = deepcopy([CHARACTER, TARGET])
    scenario_actions = deepcopy(actions)

    # Both Behind Enemy Lines ancestral variants have a native 6 m minimum
    # range. Keep their fixtures beyond that boundary instead of weakening the
    # production range check.
    if name.startswith("battlerage_behind_enemy_lines_ancestral_"):
        actors[1]["y"] = 12
        for action in scenario_actions:
            if action["type"] == "cast":
                action["y"] = 12

    # Match the already-proven root Triple Slash fixture orientation. It keeps
    # the target outside the defender's frontal defensive arc so this smoke
    # scenario validates the ancestral plot chain instead of a random miss.
    if name == "battlerage_triple_slash_ancestral_flame":
        actors[1]["x"] = 3
        actors[1]["y"] = 0
        for action in scenario_actions:
            if action["type"] == "cast":
                action["x"] = 3
                action["y"] = 0

    # A hit is required to exercise the three-stage Flame chain. This seed is
    # already proven to produce a hit with the same deterministic AA8 combat
    # inputs; random misses remain covered by the production CombatDice tests.
    seed = 558734 if name == "battlerage_triple_slash_ancestral_flame" else 558734 + index

    expected = {
        "timeline_sequence": [
            event
            for action in scenario_actions
            if action["type"] == "cast"
            for event in ("action:cast", "cast_result")
        ],
        "require_counter_monotonic_modulo_256": True,
        "require_wire_plaintext_order_match": True,
        "require_no_exceptions": True,
    }
    if expect_damage:
        expected["minimum_damage"] = 1

    initial_buffs = []
    if name == "battlerage_frenzy_buff":
        expected["caster_buff_ids"] = [22689]
    elif name == "battlerage_frenzy_ancestral_flame":
        expected["caster_buff_ids"] = [25651]
    elif name == "battlerage_frenzy_ancestral_wave":
        expected["caster_buff_ids"] = [25650]
    elif name == "battlerage_terrifying_roar":
        expected["caster_buff_ids"] = [7650]
        expected["target_buff_ids"] = [7649]
    elif name == "battlerage_bondbreaker_release":
        # Buff 82 is an AA8 root tagged with 27, the exact release category
        # consumed by Bondbreaker's DispelEffect 2633.
        initial_buffs = [
            {
                "actor_id": CHARACTER["id"],
                "caster_id": TARGET["id"],
                "buff_id": 82,
            }
        ]
        expected["caster_absent_buff_ids"] = [82]
    return {
        "schema_version": 1,
        "name": name,
        "seed": seed,
        "clock_utc": "2021-12-14T12:00:00Z",
        "dd05_initial": (200 + index * 7) % 256,
        "actors": actors,
        "initial_buffs": initial_buffs,
        "actions": scenario_actions,
        "expected": expected,
    }


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for index, (name, (actions, expect_damage)) in enumerate(sorted(SCENARIOS.items())):
        path = OUTPUT / f"{name}.json"
        path.write_text(
            json.dumps(build(name, actions, expect_damage, index), indent=2) + "\n",
            encoding="utf-8",
        )
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
