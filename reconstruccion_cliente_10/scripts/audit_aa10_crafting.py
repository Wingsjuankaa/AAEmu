#!/usr/bin/env python3
"""Build deterministic AA10 r575 crafting manifests from read-only SQLite sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


CRAFT_COLUMNS = (
    "id", "cast_delay", "skill_id", "wi_id", "milestone_id", "req_doodad_id",
    "actability_limit", "recommend_level", "visible_order", "enable", "products_pack_id",
    "use_only_actability", "craft_c_category_id", "craft_d_category_id", "orderable", "cost",
)
MATERIAL_COLUMNS = (
    "id", "craft_id", "item_id", "amount", "main_grade", "require_grade", "upper_grade",
)
PRODUCT_COLUMNS = (
    "id", "craft_id", "item_id", "amount", "rate", "use_grade", "item_grade_id",
)
BOOL_COLUMNS = {
    "enable", "use_only_actability", "orderable", "main_grade", "upper_grade", "use_grade",
}

# These contracts are intentionally empty, not incomplete loader output.  Every ID is closed by
# exact AA10 fields plus versioned external corroboration; all other empty recipes remain blocked.
_ARCHEPAPER_PRODUCTS = {
    12149: 52480, 12150: 52469, 12151: 52476, 12152: 52477,
    12177: 52722, 12178: 52723, 12189: 52871, 12190: 52872,
    12250: 52923, 12251: 52924, 12252: 52925, 12253: 52926, 12254: 52927,
}
MATERIAL_FREE_CONTRACTS: dict[int, dict[str, Any]] = {
    9267: {
        "classification": "persistent_candidate",
        "skill_id": 34912,
        "skill_labor": 300,
        "req_doodad_id": 2392,
        "actability_limit": 230000,
        "use_only_actability": True,
        "cost": 230,
        "cast_delay": 3000,
        "product": (31891, 5, 100, False, 0),
        "sources": [
            "https://archeagecodex.com/us/recipe/9267/",
            "https://wiki.archerage.to/na-en/db/crafts/9267",
        ],
    },
    **{
        craft_id: {
            "classification": "persistent_candidate",
            "skill_id": 48802,
            "skill_labor": 0,
            "req_doodad_id": 17370,
            "actability_limit": 0,
            "use_only_actability": False,
            "cost": 0,
            "cast_delay": 1000,
            "product": (item_id, 1, 100, False, 0),
            "sources": [
                "https://store.steampowered.com/news/posts/?appids=304030&enddate=1655915584&feed=steam_community_announcements",
                "https://archeagecodex.com/us/quest/11006/",
            ],
        }
        for craft_id, item_id in _ARCHEPAPER_PRODUCTS.items()
    },
}


def parse_args() -> argparse.Namespace:
    root = Path(r"E:\AAEmu\rama_10")
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", type=Path, default=root / "data/sqlite/authoritative/game_decrypted.sqlite3")
    parser.add_argument(
        "--retail-compact", type=Path,
        default=root / "client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3")
    parser.add_argument(
        "--runtime-compact", type=Path,
        default=root / "server/AAEmu/.server_files/AAEmu.Game/Data/compact.sqlite3")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-policy-output", type=Path, action="append")
    parser.add_argument("--expected-enabled", type=int, default=9949)
    parser.add_argument("--wave", type=int, choices=(1, 2, 3, 4, 5), default=1)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    return connection


def bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"t", "true", "1"}
    return bool(value)


def normalized_row(columns: tuple[str, ...], row: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(bool_value(value) if column in BOOL_COLUMNS else value
                 for column, value in zip(columns, row, strict=True))


def table_rows(connection: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> list[tuple[Any, ...]]:
    sql = f"SELECT {', '.join(columns)} FROM {table} ORDER BY id"
    return [normalized_row(columns, row) for row in connection.execute(sql)]


def group_rows(rows: Iterable[tuple[Any, ...]], craft_index: int) -> dict[int, tuple[tuple[Any, ...], ...]]:
    grouped: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        grouped[int(row[craft_index])].append(row)
    return {key: tuple(value) for key, value in grouped.items()}


def schema(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    return [
        {"ordinal": row[0], "name": row[1], "type": row[2], "not_null": bool(row[3]),
         "default": row[4], "primary_key": bool(row[5])}
        for row in connection.execute(f"PRAGMA table_info({table})")
    ]


def checks(connection: sqlite3.Connection) -> dict[str, str]:
    quick = connection.execute("PRAGMA quick_check").fetchone()[0]
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if quick != "ok" or integrity != "ok":
        raise RuntimeError(f"SQLite integrity failed: quick={quick}, integrity={integrity}")
    return {"quick_check": quick, "integrity_check": integrity}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    paths = {
        "full": args.full.resolve(),
        "retail_compact": args.retail_compact.resolve(),
        "runtime_compact": args.runtime_compact.resolve(),
    }
    databases = {name: connect(path) for name, path in paths.items()}
    try:
        source_info = {
            name: {
                "path": str(paths[name]),
                "bytes": paths[name].stat().st_size,
                "sha256": sha256(paths[name]),
                "checks": checks(connection),
                "schemas": {
                    table: schema(connection, table)
                    for table in ("crafts", "craft_materials", "craft_products", "craft_pack_crafts")
                },
            }
            for name, connection in databases.items()
        }

        crafts_by_source: dict[str, dict[int, tuple[Any, ...]]] = {}
        materials_by_source: dict[str, dict[int, tuple[tuple[Any, ...], ...]]] = {}
        products_by_source: dict[str, dict[int, tuple[tuple[Any, ...], ...]]] = {}
        for name, connection in databases.items():
            crafts_by_source[name] = {
                int(row[0]): row for row in table_rows(connection, "crafts", CRAFT_COLUMNS)
            }
            materials_by_source[name] = group_rows(
                table_rows(connection, "craft_materials", MATERIAL_COLUMNS), 1)
            products_by_source[name] = group_rows(
                table_rows(connection, "craft_products", PRODUCT_COLUMNS), 1)

        runtime = databases["runtime_compact"]
        item_ids = {int(row[0]) for row in runtime.execute("SELECT id FROM items")}
        skill_ids = {int(row[0]) for row in runtime.execute("SELECT id FROM skills")}
        skill_actability_groups = {
            int(row[0]): int(row[1] or 0)
            for row in runtime.execute("SELECT id, actability_group_id FROM skills")
        }
        skill_labor_costs = {
            int(row[0]): int(row[1] or 0)
            for row in runtime.execute("SELECT id, consume_lp FROM skills")
        }
        craft_effect_skills = {
            int(row[0]) for row in runtime.execute(
                "SELECT DISTINCT se.skill_id FROM skill_effects se "
                "JOIN effects e ON e.id=se.effect_id WHERE e.actual_type='CraftEffect'")
        }
        autoequip_backpacks = {
            int(row[0]) for row in runtime.execute(
                "SELECT ib.item_id FROM item_backpacks ib JOIN items i ON i.id=ib.item_id "
                "WHERE COALESCE(i.bind_id, 0) <> 3")
        }
        # A probabilistic product contract is only promoted when AA10 also exposes a
        # live native consumer for the recipe.  The 90 rate-50 rows point at missing
        # craft-start records in r575, and the sole rate-200 row is an explicitly
        # disabled developer path (its Korean title says it does not work).  Keeping
        # the RNG implementation testable does not make those orphan recipes callable.
        folio_crafts = {
            int(row[0]) for row in runtime.execute(
                "SELECT DISTINCT craft_id FROM craft_line_components")
        }
        craft_pack_crafts = {
            int(row[0]) for row in runtime.execute(
                "SELECT DISTINCT craft_id FROM craft_pack_crafts")
        }
        item_recipe_crafts = {
            int(row[0]) for row in runtime.execute(
                "SELECT DISTINCT craft_id FROM item_recipes")
        }
        item_linked_crafts = {
            int(row[0]) for row in runtime.execute(
                "SELECT DISTINCT craft_id FROM items "
                "WHERE craft_id IS NOT NULL AND craft_id <> 0")
        }
        live_direct_crafts = {
            int(row[0]) for row in runtime.execute(
                "SELECT DISTINCT sc.craft_id "
                "FROM doodad_func_craft_start_crafts sc "
                "JOIN doodad_func_craft_starts s "
                "  ON s.id=sc.doodad_func_craft_start_id "
                "JOIN doodad_funcs df "
                "  ON df.actual_func_type='DoodadFuncCraftStart' "
                " AND df.actual_func_id=s.id")
        }
        native_consumer_sets = {
            "folio_craft_line": folio_crafts,
            "doodad_craft_pack": craft_pack_crafts,
            "item_recipe": item_recipe_crafts,
            "item_craft_link": item_linked_crafts,
            "live_doodad_craft_start": live_direct_crafts,
        }
        native_consumer_crafts = set().union(*native_consumer_sets.values())
        # These rows prove that a recipe is referenced, but not that this server can
        # execute it through the native AA10 crafting transaction.  Quest rows only
        # observe progress and the butler request packet is deliberately TODO.
        excluded_consumer_sets = {
            "butler_specialty_trade_todo": {
                int(row[0]) for row in runtime.execute(
                    "SELECT DISTINCT craft_id FROM butler_specialty_trades")
            },
            "quest_progress_observer": {
                int(row[0]) for row in runtime.execute(
                    "SELECT DISTINCT craft_id FROM quest_act_obj_crafts")
            },
        }

        enabled = [
            row for row in crafts_by_source["full"].values()
            if bool(row[CRAFT_COLUMNS.index("enable")])
        ]
        if len(enabled) != args.expected_enabled:
            raise RuntimeError(
                f"Expected {args.expected_enabled} enabled recipes, observed {len(enabled)}")
        enabled_ids = {int(row[0]) for row in enabled}

        recipes: list[dict[str, Any]] = []
        blocker_counts: Counter[str] = Counter()
        state_counts: Counter[str] = Counter()
        craft_mismatch_fields: dict[str, Counter[str]] = {
            "retail_compact": Counter(),
            "runtime_compact": Counter(),
        }
        for craft_row in sorted(enabled, key=lambda row: row[0]):
            craft_id = int(craft_row[0])
            craft = dict(zip(CRAFT_COLUMNS, craft_row, strict=True))
            materials = materials_by_source["full"].get(craft_id, ())
            products = products_by_source["full"].get(craft_id, ())
            blockers: set[str] = set()
            contract_mismatches: dict[str, list[str]] = {}
            material_free_contract = MATERIAL_FREE_CONTRACTS.get(craft_id)
            material_free_issues: list[str] = []
            if material_free_contract is not None and materials:
                material_free_issues.append("unexpected_material_rows")
                blockers.add("material_free_contract_mismatch")

            for source in ("retail_compact", "runtime_compact"):
                source_craft = crafts_by_source[source].get(craft_id)
                if source_craft != craft_row:
                    blockers.add(f"{source}_craft_contract_mismatch")
                    fields = (["__missing__"] if source_craft is None else [
                        column for column, full_value, source_value
                        in zip(CRAFT_COLUMNS, craft_row, source_craft, strict=True)
                        if full_value != source_value
                    ])
                    contract_mismatches[f"{source}_craft"] = fields
                    craft_mismatch_fields[source].update(fields)
                if materials_by_source[source].get(craft_id, ()) != materials:
                    blockers.add(f"{source}_material_contract_mismatch")
                if products_by_source[source].get(craft_id, ()) != products:
                    blockers.add(f"{source}_product_contract_mismatch")

            if not materials:
                if material_free_contract is None:
                    blockers.add("missing_materials")
                else:
                    for field in (
                            "skill_id", "req_doodad_id", "actability_limit",
                            "use_only_actability", "cost", "cast_delay"):
                        expected = material_free_contract[field]
                        actual = bool(craft[field]) if isinstance(expected, bool) else int(craft[field] or 0)
                        if actual != expected:
                            material_free_issues.append(field)
                    if skill_labor_costs.get(int(craft["skill_id"] or 0)) != material_free_contract["skill_labor"]:
                        material_free_issues.append("skill.consume_lp")
                    actual_products = tuple(
                        (int(row[2] or 0), int(row[3] or 0), int(row[4] or 0),
                         bool(row[5]), int(row[6] or 0))
                        for row in products)
                    if actual_products != (material_free_contract["product"],):
                        material_free_issues.append("craft_products")
                    if material_free_issues:
                        blockers.add("material_free_contract_mismatch")
            if not products:
                blockers.add("missing_products")
            if int(craft["skill_id"] or 0) not in skill_ids:
                blockers.add("missing_skill")
            elif int(craft["skill_id"] or 0) not in craft_effect_skills:
                blockers.add("missing_craft_effect")
            cost = int(craft["cost"] or 0)
            actability_limit = int(craft["actability_limit"] or 0)
            cast_delay = int(craft["cast_delay"] or 0)
            skill_actability_group = skill_actability_groups.get(int(craft["skill_id"] or 0), 0)
            if args.wave == 1:
                if cost != 0:
                    blockers.add("cost_deferred")
                if actability_limit != 0 or bool(craft["use_only_actability"]):
                    blockers.add("actability_deferred")
            else:
                if cost < 0:
                    blockers.add("invalid_cost")
                if actability_limit < 0:
                    blockers.add("invalid_actability_limit")
                if cast_delay < 0:
                    blockers.add("invalid_cast_delay")
                if (actability_limit > 0 or bool(craft["use_only_actability"])) and skill_actability_group == 0:
                    blockers.add("missing_actability_group")

            for material in materials:
                row = dict(zip(MATERIAL_COLUMNS, material, strict=True))
                if int(row["item_id"] or 0) not in item_ids:
                    blockers.add("missing_material_item")
                if int(row["amount"] or 0) <= 0:
                    blockers.add("invalid_material_amount")
                require_grade = int(row["require_grade"] if row["require_grade"] is not None else -1)
                if args.wave < 3:
                    if require_grade != -1 or bool(row["upper_grade"]):
                        blockers.add("material_grade_deferred")
                else:
                    if require_grade < -1 or require_grade > 255:
                        blockers.add("invalid_material_grade")
                    if bool(row["upper_grade"]) and require_grade == -1:
                        blockers.add("invalid_upper_grade_contract")

            for product in products:
                row = dict(zip(PRODUCT_COLUMNS, product, strict=True))
                item_id = int(row["item_id"] or 0)
                if item_id not in item_ids:
                    blockers.add("missing_product_item")
                if int(row["amount"] or 0) <= 0:
                    blockers.add("invalid_product_amount")
                rate = int(row["rate"] or 0)
                item_grade_id = int(row["item_grade_id"] or 0)
                if args.wave < 3:
                    if rate != 100:
                        blockers.add("product_rate_deferred")
                    if bool(row["use_grade"]) or item_grade_id != 0:
                        blockers.add("product_grade_deferred")
                else:
                    if rate not in (50, 100, 200):
                        blockers.add("invalid_product_rate")
                    if rate != 100 and craft_id not in native_consumer_crafts:
                        blockers.add("missing_native_rate_consumer")
                    if item_grade_id < 0 or item_grade_id > 255:
                        blockers.add("invalid_product_grade")
                if args.wave < 4 and item_id in autoequip_backpacks:
                    blockers.add("backpack_deferred")

            if args.wave >= 5 and craft_id not in native_consumer_crafts:
                blockers.add("missing_native_consumer")

            ordered_blockers = sorted(blockers)
            executable_state = f"executable_wave{args.wave}"
            state = executable_state if not ordered_blockers else "blocked"
            state_counts[state] += 1
            blocker_counts.update(ordered_blockers)
            recipe = {
                "craft_id": craft_id,
                "state": state,
                "blockers": ordered_blockers,
                "skill_id": int(craft["skill_id"] or 0),
                "required_doodad_id": int(craft["req_doodad_id"] or 0),
                "cast_delay": int(craft["cast_delay"] or 0),
                "cost": int(craft["cost"] or 0),
                "material_rows": len(materials),
                "product_rows": len(products),
                "orderable": bool(craft["orderable"]),
            }
            if material_free_contract is not None:
                recipe["material_contract"] = (
                    "intentional_empty" if not material_free_issues and not materials
                    else "blocked_contract_mismatch")
                recipe["external_corroboration"] = {
                    "classification": material_free_contract["classification"],
                    "sources": material_free_contract["sources"],
                }
                if material_free_issues:
                    recipe["material_contract_mismatches"] = sorted(material_free_issues)
            if contract_mismatches:
                recipe["contract_mismatches"] = contract_mismatches
            if args.wave >= 2:
                recipe.update({
                    "actability_limit": actability_limit,
                    "use_only_actability": bool(craft["use_only_actability"]),
                    "actability_group_id": skill_actability_group,
                })
            if args.wave >= 5:
                recipe["native_consumers"] = sorted(
                    name for name, craft_ids in native_consumer_sets.items()
                    if craft_id in craft_ids)
                recipe["excluded_consumer_evidence"] = sorted(
                    name for name, craft_ids in excluded_consumer_sets.items()
                    if craft_id in craft_ids)
            recipes.append(recipe)

        orphan_counts = {}
        full_craft_ids = set(crafts_by_source["full"])
        for table_name, rows in (
            ("craft_materials", table_rows(databases["full"], "craft_materials", MATERIAL_COLUMNS)),
            ("craft_products", table_rows(databases["full"], "craft_products", PRODUCT_COLUMNS)),
        ):
            orphan_counts[table_name] = sum(1 for row in rows if int(row[1]) not in full_craft_ids)

        query_specs = {
            "crafts": f"SELECT {', '.join(CRAFT_COLUMNS)} FROM crafts ORDER BY id",
            "materials": f"SELECT {', '.join(MATERIAL_COLUMNS)} FROM craft_materials ORDER BY id",
            "products": f"SELECT {', '.join(PRODUCT_COLUMNS)} FROM craft_products ORDER BY id",
            "craft_effect_skills": "SELECT DISTINCT se.skill_id FROM skill_effects se JOIN effects e ON e.id=se.effect_id WHERE e.actual_type='CraftEffect'",
            "autoequip_backpacks": "SELECT ib.item_id FROM item_backpacks ib JOIN items i ON i.id=ib.item_id WHERE COALESCE(i.bind_id, 0) <> 3",
            "native_rate_consumers": (
                "union of craft_line_components, craft_pack_crafts, item_recipes, "
                "items.craft_id and live DoodadFuncCraftStart rows"),
        }
        if args.wave >= 5:
            query_specs["native_execution_consumers"] = (
                "union of craft_line_components, craft_pack_crafts, item_recipes, "
                "items.craft_id and live DoodadFuncCraftStart rows; "
                "butler_specialty_trades is excluded because its packet consumer is TODO; "
                "quest_act_obj_crafts only observes progress")
        if args.wave >= 2:
            query_specs["skill_actability_groups"] = "SELECT id, actability_group_id FROM skills"
        query_specs["skill_labor_costs"] = "SELECT id, consume_lp FROM skills"
        query_specs["intentional_empty_material_contracts"] = (
            "closed allowlist: exact craft, skill.consume_lp and product tuple; "
            "all other empty material lists remain blocked")

        return {
            "format": f"aa10-crafting-wave{args.wave}-manifest-v1",
            "build": "ArcheAge Returns 10.0.2.13 r575",
            "target": {
                "repository": "Wingsjuankaa/AAEmu",
                "branch": "rama_10",
                "baseline_head": (
                    "482bb1118a57bd5c7200fd0bbdda790744674a78" if args.wave == 1
                    else "e2ef3d7dfa241a305c887b95cb257fb97863146a" if args.wave == 2
                    else "fc30df0ae12a998033228f197934cc84e84c992a" if args.wave == 3
                    else "6054192ca2a3d6906776bcd6bcd15392617aae44" if args.wave == 4
                    else "d357d9b8f0a04aff501da7b4f8c50240009be07f"),
                "upstream_parent": "AAEmu/AAEmu:client_version/zone-10.0.2_r575",
                "aa8_classification": "structural_candidate",
            },
            "policy": {
                "wave": args.wave,
                "count": 1 if args.wave == 1 else "positive; committed one unit at a time",
                "money_cost": 0 if args.wave == 1 else "base copper cost per committed unit",
                "product_rate": (
                    100 if args.wave < 3
                    else "50/100/200; injected integer roll 0..99; rates >=100 guaranteed"),
                "material_grade_contract": (
                    "default_only" if args.wave < 3
                    else "require_grade exact; upper_grade accepts greater or equal; -1 wildcard"),
                "product_grade_contract": (
                    "default_only" if args.wave < 3
                    else "use_grade fixes item_grade_id; otherwise main_grade then highest same-impl material"),
                "actability_contract": (
                    "no_recipe_specific_gate" if args.wave == 1
                    else "skill actability group; bonuses excluded when use_only_actability"),
                "product_destination": (
                    "bag_only" if args.wave < 4
                    else "bag plus atomic auto-equipped BackpackTemplate; an equipped glider moves "
                         "only when post-consumption bag capacity exists"),
                "legacy_fallback": False,
                "craft_orders": "excluded",
                "station_and_permission": "revalidated_at_start_and_commit; non-public permissions fail closed",
                "native_consumer_contract": (
                    "not_closed_before_wave5" if args.wave < 5
                    else "recipe must have a demonstrated client/runtime execution consumer; "
                         "observer-only and TODO consumers fail closed"),
            },
            "sources": source_info,
            "query_specs": query_specs,
            "coverage": {
                "enabled_recipes": len(recipes),
                "states": dict(sorted(state_counts.items())),
                "blockers": dict(sorted(blocker_counts.items())),
                "craft_contract_mismatch_fields": {
                    source: dict(sorted(counter.items()))
                    for source, counter in craft_mismatch_fields.items()
                },
                "orphan_rows_full": orphan_counts,
                **({
                    "native_consumer_sources": {
                        name: len(craft_ids & enabled_ids)
                        for name, craft_ids in sorted(native_consumer_sets.items())
                    },
                    "native_consumer_union": len(native_consumer_crafts & enabled_ids),
                    "excluded_consumer_sources": {
                        name: len(craft_ids & enabled_ids)
                        for name, craft_ids in sorted(excluded_consumer_sets.items())
                    },
                } if args.wave >= 5 else {}),
            },
            "recipes": recipes,
        }
    finally:
        for connection in databases.values():
            connection.close()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8", newline="\n")
    manifest_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
    if args.runtime_policy_output:
        policy = {
            "format": f"aa10-crafting-runtime-policy-v{args.wave}",
            "sourceManifestSha256": manifest_sha256,
            "executableCraftIds": [
                recipe["craft_id"] for recipe in manifest["recipes"]
                if recipe["state"] == f"executable_wave{args.wave}"
            ],
            "materialFreeCraftIds": [
                recipe["craft_id"] for recipe in manifest["recipes"]
                if recipe.get("material_contract") == "intentional_empty" and
                   recipe["state"] == f"executable_wave{args.wave}"
            ],
        }
        policy_payload = json.dumps(policy, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        for policy_output in args.runtime_policy_output:
            policy_output.parent.mkdir(parents=True, exist_ok=True)
            policy_output.write_text(policy_payload, encoding="utf-8", newline="\n")
            print(f"runtime_policy={policy_output.resolve()}")
        print(f"runtime_policy_sha256={hashlib.sha256(policy_payload.encode('utf-8')).hexdigest().upper()}")
    print(json.dumps(manifest["coverage"], sort_keys=True))
    print(f"output={args.output.resolve()}")
    print(f"sha256={manifest_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
