from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Family:
    impl_id: int
    name: str
    descriptor_tables: tuple[str, ...]
    destructive: bool
    economic: bool
    protocol_known: bool
    confidence: str


# Exact mappings are supported by matching AA8 item rows, native descriptor
# tables, and x2game RTTI/loader names. Unknown implementations intentionally
# stay unmapped; names are never borrowed from a historical compact.
X2GAME_ITEM_IMPL_NAMES: dict[int, str] = {
    0: "misc",
    1: "weapon",
    2: "armor",
    3: "body",
    4: "bag",
    5: "housing",
    6: "housing_decoration",
    7: "tool",
    8: "summon_slave",
    9: "spawn_doodad",
    10: "accept_quest",
    11: "summon_mate",
    12: "recipe",
    13: "crafting",
    14: "portal",
    15: "enchanting_gem",
    16: "report_crime",
    17: "logic_doodad",
    18: "has_ucc",
    19: "open_emblem_ui",
    20: "shipyard",
    21: "socket",
    22: "backpack",
    23: "open_paper",
    24: "accessory",
    25: "treasure",
    26: "music_sheet",
    27: "dyeing",
    28: "slave_equipment",
    29: "grade_enchanting_support",
    30: "mate_armor",
    31: "location",
    32: "rename_character",
    33: "evolving_material",
    34: "butler_armor",
    35: "bless_uthstin",
}
X2GAME_ITEM_IMPL_EVIDENCE = "x2game.dll FUN_39874940"


FAMILIES: dict[int, Family] = {
    0: Family(0, "generic", (), False, False, False, "client_compact_8"),
    1: Family(1, "weapon", ("item_weapons",), False, False, True, "game11_native+x2game_confirmed"),
    2: Family(2, "armor", ("item_armors",), False, False, True, "game11_native+x2game_confirmed"),
    3: Family(3, "body_part", ("item_body_parts",), False, False, True, "game11_native+x2game_confirmed"),
    4: Family(4, "bag", ("item_bags",), False, False, False, "game11_native+x2game_confirmed"),
    5: Family(5, "housing", ("item_housings",), True, True, False, "x2game_confirmed"),
    6: Family(6, "housing_decoration", ("item_housing_decorations",), True, True, False, "x2game_confirmed"),
    7: Family(7, "tool", ("item_tools",), False, False, False, "x2game_confirmed"),
    8: Family(8, "summon_slave", ("item_summon_slaves",), True, False, False, "x2game_confirmed"),
    9: Family(9, "spawn_doodad", ("item_spawn_doodads",), True, True, False, "x2game_confirmed"),
    10: Family(10, "accept_quest", ("item_accept_quests",), True, True, False, "x2game_confirmed"),
    11: Family(11, "summon_mate", ("item_summon_mates",), True, False, False, "x2game_confirmed"),
    12: Family(12, "recipe", ("item_recipes",), True, True, False, "x2game_confirmed"),
    14: Family(14, "portal", (), True, False, False, "client_compact_8+x2game_confirmed"),
    15: Family(15, "enchanting_gem", ("item_enchanting_gems",), True, True, True, "game11_native+x2game_confirmed"),
    20: Family(20, "shipyard", ("item_shipyards",), True, True, False, "x2game_confirmed"),
    21: Family(21, "socket", ("item_sockets",), True, True, True, "game11_native+x2game_confirmed"),
    22: Family(22, "backpack", ("item_backpacks",), False, False, True, "game11_native+x2game_confirmed"),
    23: Family(23, "open_paper", ("item_open_papers",), False, False, False, "x2game_confirmed"),
    24: Family(24, "accessory", ("item_accessories",), False, False, True, "game11_native+x2game_confirmed"),
    26: Family(26, "music_sheet", (), False, False, False, "client_compact_8+x2game_confirmed"),
    # AA8 has no item_dyeings/dyeing_colors SQL loader.  The concrete impl is
    # fieldless beyond the base items row and dispatches through use_skill_id.
    # dyeable_items describes target equipment and is a separate catalogue.
    27: Family(27, "dyeing", (), True, True, True, "client_compact_8+x2game_confirmed"),
    28: Family(28, "slave_equipment", ("item_slave_equipments",), True, True, False, "x2game_confirmed"),
    29: Family(29, "grade_enchanting_support", ("item_grade_enchanting_supports",), True, True, False, "x2game_confirmed"),
    30: Family(30, "armor", ("item_armors",), False, False, True, "game11_native+x2game_confirmed"),
    31: Family(31, "location", (), True, False, False, "client_compact_8+x2game_confirmed"),
    32: Family(32, "rename_character", (), True, True, False, "client_compact_8+x2game_confirmed"),
    33: Family(33, "evolving_material", ("item_evolving_materials",), True, True, True, "game11_native+x2game_confirmed"),
    34: Family(34, "armor", ("item_armors",), False, False, True, "game11_native+x2game_confirmed"),
    35: Family(35, "bless_uthstin", ("item_bless_uthstins",), True, True, False, "game11_native+x2game_confirmed"),
}


def family_for_impl(impl_id: int) -> Family | None:
    return FAMILIES.get(impl_id)


def family_name(impl_id: int) -> str:
    family = family_for_impl(impl_id)
    return family.name if family else f"unmapped_impl_{impl_id}"
