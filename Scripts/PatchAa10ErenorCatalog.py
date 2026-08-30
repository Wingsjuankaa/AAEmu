#!/usr/bin/env python3
"""Reconstruct the AA10 r575 Erenor Folio, Item Encyclopedia and grade flow.

The retail compact already contains the recipes, products, materials, workbench
packs and awakening mappings.  The damaged projection is narrower:

* the 39 equipment-designer D categories and three accessory C categories are
  marked as doodad-only, which removes the finished products from Folio search;
* the Erenor T1/T2 guides are empty and T3/T4 contain only a stale/partial shield;
* later scrolls and infusions are absent from their existing guide families;
* every Erenor synthesis category is capped at Celestial despite native mapping
  groups requiring Divine, Epic, Mythic or Eternal.

This builder derives equipment rows from the native mapping chains 23, 275 and
311, validates the exact r575 topology, changes only the audited catalog fields,
and is idempotent.  Backups and game_pak replacement belong to the PowerShell
applicator.  Dry-run is the default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


BASE_CRAFT_IDS = tuple(range(9918, 9959)) + (11934,)
TIER_GUIDES = (619, 873, 922, 994)

# category -> (visible order, encyclopedia A category, encyclopedia B category)
NON_ARMOR_POSITIONS: dict[int, tuple[int, int, int]] = {
    69: (1, 1, 1),    # dagger
    70: (5, 1, 1),    # sword
    72: (10, 1, 1),   # katana
    73: (15, 1, 1),   # axe
    76: (18, 1, 1),   # shortspear
    74: (20, 1, 1),   # club
    75: (25, 1, 1),   # scepter
    127: (30, 1, 2),  # greatsword
    128: (35, 1, 2),  # nodachi
    129: (40, 1, 2),  # greataxe
    130: (45, 1, 2),  # greatclub
    132: (50, 1, 2),  # longspear
    131: (55, 1, 2),  # staff
    77: (60, 1, 3),   # bow
    203: (63, 1, 3),  # rifle
    79: (65, 1, 4),   # shield
    80: (70, 1, 5),   # lute
    81: (75, 1, 5),   # flute
    125: (1, 3, 14),  # earring
    86: (1, 3, 15),   # necklace
    87: (1, 3, 16),   # ring
}

# craft B category -> (guide B category, cloth/leather/plate visible orders)
ARMOR_POSITIONS: dict[int, tuple[int, tuple[int, int, int]]] = {
    1: (6, (80, 85, 90)),
    2: (7, (95, 100, 105)),
    3: (8, (110, 115, 120)),
    4: (9, (122, 124, 126)),
    5: (10, (128, 130, 132)),
    7: (11, (134, 136, 138)),
    8: (12, (140, 142, 144)),
}
ARMOR_MATERIAL_INDEX = {83: 0, 84: 1, 85: 2}

EXTRA_GUIDE_ROWS: dict[int, tuple[tuple[int, int, int, int, str], ...]] = {
    836: (
        (48829, 1, 17, 43, "t"), (48830, 2, 17, 43, "t"),
        (48831, 3, 17, 43, "t"), (48832, 4, 17, 43, "t"),
        (48833, 5, 17, 43, "t"), (48836, 6, 17, 43, "t"),
        (48853, 7, 17, 43, "t"), (54329, 8, 17, 43, "t"),
    ),
    892: (
        (48849, 1, 17, 43, "t"), (48850, 2, 17, 43, "t"),
        (48851, 3, 17, 43, "t"),
    ),
    954: (
        (45994, 1, 21, 58, "t"), (46022, 2, 21, 58, "t"),
        (49205, 3, 21, 58, "t"), (49206, 4, 21, 58, "t"),
        (52913, 5, 21, 58, "t"),
    ),
    962: (
        (47032, 1, 21, 54, "t"), (47050, 2, 21, 54, "t"),
        (49173, 3, 21, 54, "t"), (49174, 4, 21, 54, "t"),
        (53793, 5, 21, 54, "t"), (53794, 6, 21, 54, "t"),
    ),
}

CAPS: dict[int, tuple[int, ...]] = {
    10: tuple(range(49, 63)),
    11: (
        tuple(range(466, 476)) + tuple(range(594, 597)) + tuple(range(598, 606))
        + tuple(range(681, 684)) + tuple(range(726, 731)) + tuple(range(734, 739))
    ),
    12: tuple(range(712, 726)) + tuple(range(805, 810)) + tuple(range(811, 815)) + tuple(range(816, 823)),
}


@dataclass(frozen=True)
class PatchResult:
    applied: bool
    before_hash: str
    after_hash: str
    before_size: int
    after_size: int
    folio_categories_changed: int
    guide_rows_changed: int
    grade_caps_changed: int


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def quick_check(connection: sqlite3.Connection, path: Path, phase: str) -> None:
    row = connection.execute("PRAGMA quick_check").fetchone()
    if row is None or row[0] != "ok":
        raise RuntimeError(f"{path}: quick_check failed {phase}: {row}")


def require_tables(connection: sqlite3.Connection, path: Path) -> None:
    required = {
        "crafts", "craft_products", "items", "craft_c_categories", "craft_d_categories",
        "item_change_mappings", "item_guides", "item_guide_elems", "item_rnd_attr_categories",
    }
    present = {str(row[0]) for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    missing = sorted(required - present)
    if missing:
        raise RuntimeError(f"{path}: missing AA10 catalog tables: {missing}")


def _rows_for_guide(connection: sqlite3.Connection, guide_id: int) -> tuple[tuple[int, int, int, int, str], ...]:
    return tuple(
        (int(row[0]), int(row[1]), int(row[2]), int(row[3]), str(row[4]))
        for row in connection.execute(
            "SELECT item_id, visible_order, item_guide_a_category_id, "
            "item_guide_b_category_id, show_craft FROM item_guide_elems "
            "WHERE item_guide_id=? ORDER BY item_id, visible_order",
            (guide_id,),
        )
    )


def _position_for_base(category_id: int, craft_b_category_id: int) -> tuple[int, int, int]:
    if category_id in ARMOR_MATERIAL_INDEX and craft_b_category_id in ARMOR_POSITIONS:
        guide_b, orders = ARMOR_POSITIONS[craft_b_category_id]
        return orders[ARMOR_MATERIAL_INDEX[category_id]], 2, guide_b
    position = NON_ARMOR_POSITIONS.get(category_id)
    if position is None:
        raise RuntimeError(
            f"unsupported Erenor item category {category_id} in craft B category {craft_b_category_id}"
        )
    return position


def derive_tier_guide_rows(
    connection: sqlite3.Connection, path: Path
) -> tuple[dict[int, tuple[tuple[int, int, int, int, str], ...]], tuple[int, ...], tuple[int, ...]]:
    placeholders = ",".join("?" for _ in BASE_CRAFT_IDS)
    base_rows = connection.execute(
        f"SELECT c.id, cp.item_id, i.category_id, cc.craft_b_category_id, "
        f"c.craft_d_category_id FROM crafts c "
        f"JOIN craft_products cp ON cp.craft_id=c.id "
        f"JOIN items i ON i.id=cp.item_id "
        f"JOIN craft_c_categories cc ON cc.id=c.craft_c_category_id "
        f"WHERE c.id IN ({placeholders}) ORDER BY c.id",
        BASE_CRAFT_IDS,
    ).fetchall()
    if len(base_rows) != 42 or {int(row[0]) for row in base_rows} != set(BASE_CRAFT_IDS):
        raise RuntimeError(f"{path}: expected the exact 42 r575 base Erenor crafts")

    positions: dict[int, tuple[int, int, int]] = {}
    d_categories: set[int] = set()
    for _, item_id, category_id, craft_b_id, d_category_id in base_rows:
        item_id = int(item_id)
        if item_id in positions:
            raise RuntimeError(f"{path}: duplicate base Erenor product {item_id}")
        positions[item_id] = _position_for_base(int(category_id), int(craft_b_id))
        if d_category_id is not None:
            d_categories.add(int(d_category_id))
    if len(positions) != 42 or len(d_categories) != 39:
        raise RuntimeError(
            f"{path}: unexpected Erenor topology products={len(positions)} D-categories={len(d_categories)}"
        )

    def mapping(group_id: int, count: int, grade: int) -> dict[int, int]:
        rows = connection.execute(
            "SELECT source_item_id, target_item_id, source_grade_id, target_grade_id "
            "FROM item_change_mappings WHERE mapping_group_id=? ORDER BY id",
            (group_id,),
        ).fetchall()
        if len(rows) != count:
            raise RuntimeError(f"{path}: mapping group {group_id} expected {count} rows, got {len(rows)}")
        if any(int(row[2]) != grade or int(row[3]) != -1 for row in rows):
            raise RuntimeError(f"{path}: mapping group {group_id} grade contract drifted")
        result = {int(row[0]): int(row[1]) for row in rows}
        if len(result) != count or len(set(result.values())) != count:
            raise RuntimeError(f"{path}: mapping group {group_id} is not one-to-one")
        return result

    tier1_to_tier2 = mapping(23, 42, 10)
    tier2_to_tier3 = mapping(275, 42, 11)
    tier3_to_tier4 = mapping(311, 39, 12)
    if set(tier1_to_tier2) != set(positions):
        raise RuntimeError(f"{path}: group 23 does not cover the 42 base Erenor products")
    if set(tier2_to_tier3) != set(tier1_to_tier2.values()):
        raise RuntimeError(f"{path}: group 275 does not continue the complete Erenor chain")
    if not set(tier3_to_tier4).issubset(set(tier2_to_tier3.values())):
        raise RuntimeError(f"{path}: group 311 is not a valid Erenor T3 subset")

    tier2_positions = {tier1_to_tier2[item_id]: value for item_id, value in positions.items()}
    tier3_positions = {tier2_to_tier3[item_id]: value for item_id, value in tier2_positions.items()}
    tier4_positions = {tier3_to_tier4[item_id]: tier3_positions[item_id] for item_id in tier3_to_tier4}

    def guide_rows(entries: dict[int, tuple[int, int, int]]) -> tuple[tuple[int, int, int, int, str], ...]:
        return tuple(sorted(
            ((item_id, order, category_a, category_b, "t")
             for item_id, (order, category_a, category_b) in entries.items()),
            key=lambda row: (row[2], row[3], row[1], row[0]),
        ))

    return {
        619: guide_rows(positions),
        873: guide_rows(tier2_positions),
        922: guide_rows(tier3_positions),
        994: guide_rows(tier4_positions),
    }, tuple(sorted(d_categories)), (236, 237, 238)


def _replace_guide(
    connection: sqlite3.Connection,
    path: Path,
    guide_id: int,
    expected: tuple[tuple[int, int, int, int, str], ...],
    allowed_originals: tuple[tuple[tuple[int, int, int, int, str], ...], ...],
    apply_changes: bool,
) -> int:
    if connection.execute("SELECT COUNT(*) FROM item_guides WHERE id=?", (guide_id,)).fetchone()[0] != 1:
        raise RuntimeError(f"{path}: item guide {guide_id} is missing")
    current = _rows_for_guide(connection, guide_id)
    expected_normalized = tuple(sorted(expected, key=lambda row: (row[0], row[1])))
    if current == expected_normalized:
        return 0
    allowed = {tuple(sorted(rows, key=lambda row: (row[0], row[1]))) for rows in allowed_originals}
    if current not in allowed:
        raise RuntimeError(f"{path}: partial or unknown state in item guide {guide_id}")
    changed = len(current) + len(expected_normalized)
    if apply_changes:
        connection.execute("DELETE FROM item_guide_elems WHERE item_guide_id=?", (guide_id,))
        connection.executemany(
            "INSERT INTO item_guide_elems "
            "(item_id,item_guide_id,visible_order,item_guide_a_category_id,item_guide_b_category_id,show_craft) "
            "VALUES (?,?,?,?,?,?)",
            ((item_id, guide_id, order, category_a, category_b, show_craft)
             for item_id, order, category_a, category_b, show_craft in expected_normalized),
        )
    return changed


def patch_database(path: Path, apply_changes: bool, preserve_size: bool = False) -> PatchResult:
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    before_hash = sha256(path)
    before_size = path.stat().st_size
    connection = sqlite3.connect(path, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        quick_check(connection, path, "before Erenor patch")
        require_tables(connection, path)
        connection.execute("BEGIN IMMEDIATE")
        tier_rows, d_categories, accessory_c_categories = derive_tier_guide_rows(connection, path)

        d_placeholders = ",".join("?" for _ in d_categories)
        d_state = [str(row[0]) for row in connection.execute(
            f"SELECT use_only_doodad FROM craft_d_categories WHERE id IN ({d_placeholders}) ORDER BY id",
            d_categories,
        )]
        if len(d_state) != 39 or set(d_state) not in ({"t"}, {"f"}):
            raise RuntimeError(f"{path}: partial or unknown Erenor D-category visibility")
        c_placeholders = ",".join("?" for _ in accessory_c_categories)
        c_state = [str(row[0]) for row in connection.execute(
            f"SELECT use_only_doodad FROM craft_c_categories WHERE id IN ({c_placeholders}) ORDER BY id",
            accessory_c_categories,
        )]
        if len(c_state) != 3 or set(c_state) not in ({"t"}, {"f"}):
            raise RuntimeError(f"{path}: partial or unknown Erenor accessory visibility")
        folio_changed = (39 if d_state[0] == "t" else 0) + (3 if c_state[0] == "t" else 0)
        if apply_changes and d_state[0] == "t":
            connection.execute(
                f"UPDATE craft_d_categories SET use_only_doodad='f' WHERE id IN ({d_placeholders})",
                d_categories,
            )
        if apply_changes and c_state[0] == "t":
            connection.execute(
                f"UPDATE craft_c_categories SET use_only_doodad='f' WHERE id IN ({c_placeholders})",
                accessory_c_categories,
            )

        guide_changes = 0
        guide_changes += _replace_guide(connection, path, 619, tier_rows[619], ((),), apply_changes)
        guide_changes += _replace_guide(connection, path, 873, tier_rows[873], ((),), apply_changes)
        guide_changes += _replace_guide(
            connection, path, 922, tier_rows[922],
            (((48595, 1, 1, 4, "t"),),), apply_changes,
        )
        guide_changes += _replace_guide(
            connection, path, 994, tier_rows[994],
            (((53096, 1, 1, 4, "t"),),), apply_changes,
        )
        for guide_id, expected in EXTRA_GUIDE_ROWS.items():
            original_length = {836: 5, 892: 3, 954: 4, 962: 4}[guide_id]
            guide_changes += _replace_guide(
                connection, path, guide_id, expected, (expected[:original_length],), apply_changes,
            )

        cap_changes = 0
        for desired, category_ids in CAPS.items():
            placeholders = ",".join("?" for _ in category_ids)
            rows = connection.execute(
                f"SELECT id,max_evolving_grade FROM item_rnd_attr_categories "
                f"WHERE id IN ({placeholders}) ORDER BY id",
                category_ids,
            ).fetchall()
            if len(rows) != len(category_ids):
                raise RuntimeError(
                    f"{path}: expected {len(category_ids)} Erenor synthesis categories for cap {desired}"
                )
            values = {int(row[1]) for row in rows}
            if values not in ({7}, {desired}):
                raise RuntimeError(f"{path}: partial or unknown Erenor cap state for grade {desired}: {values}")
            if values == {7} and desired != 7:
                cap_changes += len(rows)
                if apply_changes:
                    connection.execute(
                        f"UPDATE item_rnd_attr_categories SET max_evolving_grade=? "
                        f"WHERE id IN ({placeholders})",
                        (desired, *category_ids),
                    )

        if apply_changes:
            # Re-derive after replacement and require the exact final guide identities.
            for guide_id, expected in {**tier_rows, **EXTRA_GUIDE_ROWS}.items():
                if _rows_for_guide(connection, guide_id) != tuple(
                    sorted(expected, key=lambda row: (row[0], row[1]))
                ):
                    raise RuntimeError(f"{path}: post-patch guide verification failed for {guide_id}")
        quick_check(connection, path, "after Erenor patch")
        if apply_changes:
            connection.commit()
        else:
            connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    after_size = path.stat().st_size
    if preserve_size and after_size != before_size:
        raise RuntimeError(f"{path}: compact size changed {before_size}->{after_size}")
    return PatchResult(
        applied=apply_changes,
        before_hash=before_hash,
        after_hash=sha256(path),
        before_size=before_size,
        after_size=after_size,
        folio_categories_changed=folio_changed,
        guide_rows_changed=guide_changes,
        grade_caps_changed=cap_changes,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("databases", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--preserve-size", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = []
    for database in args.databases:
        result = patch_database(database, args.apply, args.preserve_size)
        results.append({"path": str(database.resolve()), **asdict(result)})
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for result in results:
            print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
