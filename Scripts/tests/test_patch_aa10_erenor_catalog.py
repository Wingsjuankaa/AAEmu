from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "PatchAa10ErenorCatalog.py"
SPEC = importlib.util.spec_from_file_location("patch_aa10_erenor_catalog", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PATCHER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PATCHER
SPEC.loader.exec_module(PATCHER)


ARMOR_SLOTS = (1, 2, 7, 5, 8, 4, 3)
WEAPON_CATEGORIES = (69, 70, 127, 72, 128, 73, 129, 74, 130, 76, 132, 75, 131, 77, 79, 80, 81, 203)


def create_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE crafts (id INTEGER PRIMARY KEY, craft_c_category_id INTEGER, craft_d_category_id INTEGER);
            CREATE TABLE craft_products (id INTEGER PRIMARY KEY, craft_id INTEGER, item_id INTEGER);
            CREATE TABLE items (id INTEGER PRIMARY KEY, category_id INTEGER);
            CREATE TABLE craft_c_categories (
                id INTEGER PRIMARY KEY, craft_b_category_id INTEGER, use_only_doodad TEXT);
            CREATE TABLE craft_d_categories (id INTEGER PRIMARY KEY, use_only_doodad TEXT);
            CREATE TABLE item_change_mappings (
                id INTEGER PRIMARY KEY, mapping_group_id INTEGER, source_item_id INTEGER,
                target_item_id INTEGER, source_grade_id INTEGER, target_grade_id INTEGER);
            CREATE TABLE item_guides (id INTEGER PRIMARY KEY);
            CREATE TABLE item_guide_elems (
                item_id INTEGER, item_guide_id INTEGER, visible_order INTEGER,
                item_guide_a_category_id INTEGER, item_guide_b_category_id INTEGER,
                show_craft TEXT);
            CREATE TABLE item_rnd_attr_categories (
                id INTEGER PRIMARY KEY, max_evolving_grade INTEGER);
            """
        )

        products: list[int] = []
        craft_rows = []
        product_rows = []
        item_rows = []
        c_rows: dict[int, tuple[int, str]] = {}
        d_rows = []
        product_id = 43003
        product_row_id = 1

        # 21 armor recipes: plate, leather, cloth; seven body slots each.
        for material_category, first_craft in ((85, 9918), (84, 9925), (83, 9932)):
            for offset, craft_b in enumerate(ARMOR_SLOTS):
                craft_id = first_craft + offset
                c_id = craft_id
                d_id = 20_000 + craft_id
                craft_rows.append((craft_id, c_id, d_id))
                product_rows.append((product_row_id, craft_id, product_id))
                item_rows.append((product_id, material_category))
                c_rows[c_id] = (craft_b, "f")
                d_rows.append((d_id, "t"))
                products.append(product_id)
                product_id += 1
                product_row_id += 1

        # 17 legacy weapons/instruments plus the r575 rifle.
        weapon_crafts = list(range(9939, 9956)) + [11934]
        for craft_id, category_id in zip(weapon_crafts, WEAPON_CATEGORIES, strict=True):
            c_id = craft_id
            d_id = 20_000 + craft_id
            craft_rows.append((craft_id, c_id, d_id))
            product_rows.append((product_row_id, craft_id, product_id))
            item_rows.append((product_id, category_id))
            c_rows[c_id] = (14, "f")
            d_rows.append((d_id, "t"))
            products.append(product_id)
            product_id += 1
            product_row_id += 1

        for craft_id, c_id, craft_b, category_id in (
            (9956, 236, 11, 86), (9957, 237, 12, 125), (9958, 238, 13, 87)
        ):
            craft_rows.append((craft_id, c_id, None))
            product_rows.append((product_row_id, craft_id, product_id))
            item_rows.append((product_id, category_id))
            c_rows[c_id] = (craft_b, "t")
            products.append(product_id)
            product_id += 1
            product_row_id += 1

        connection.executemany("INSERT INTO crafts VALUES (?,?,?)", craft_rows)
        connection.executemany("INSERT INTO craft_products VALUES (?,?,?)", product_rows)
        connection.executemany("INSERT INTO items VALUES (?,?)", item_rows)
        connection.executemany(
            "INSERT INTO craft_c_categories VALUES (?,?,?)",
            ((c_id, values[0], values[1]) for c_id, values in c_rows.items()),
        )
        connection.executemany("INSERT INTO craft_d_categories VALUES (?,?)", d_rows)

        mapping_rows = []
        row_id = 1
        tier2 = []
        for source in products:
            target = source + 100_000
            tier2.append(target)
            mapping_rows.append((row_id, 23, source, target, 10, -1))
            row_id += 1
        tier3 = []
        for source in tier2:
            target = source + 100_000
            tier3.append(target)
            mapping_rows.append((row_id, 275, source, target, 11, -1))
            row_id += 1
        for source in tier3[:39]:
            mapping_rows.append((row_id, 311, source, source + 100_000, 12, -1))
            row_id += 1
        connection.executemany("INSERT INTO item_change_mappings VALUES (?,?,?,?,?,?)", mapping_rows)

        guide_ids = set(PATCHER.TIER_GUIDES) | set(PATCHER.EXTRA_GUIDE_ROWS)
        connection.executemany("INSERT INTO item_guides VALUES (?)", ((guide_id,) for guide_id in guide_ids))
        connection.execute("INSERT INTO item_guide_elems VALUES (48595,922,1,1,4,'t')")
        connection.execute("INSERT INTO item_guide_elems VALUES (53096,994,1,1,4,'t')")
        for guide_id, expected in PATCHER.EXTRA_GUIDE_ROWS.items():
            original_length = {836: 5, 892: 3, 954: 4, 962: 4}[guide_id]
            connection.executemany(
                "INSERT INTO item_guide_elems VALUES (?,?,?,?,?,?)",
                ((item_id, guide_id, order, cat_a, cat_b, show)
                 for item_id, order, cat_a, cat_b, show in expected[:original_length]),
            )

        cap_ids = sorted({category for ids in PATCHER.CAPS.values() for category in ids})
        connection.executemany(
            "INSERT INTO item_rnd_attr_categories VALUES (?,7)",
            ((category_id,) for category_id in cap_ids),
        )
        connection.commit()
    finally:
        connection.close()


class ErenorCatalogPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "compact.sqlite3"
        create_database(self.database)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def query_value(self, sql: str) -> int:
        connection = sqlite3.connect(self.database)
        try:
            return int(connection.execute(sql).fetchone()[0])
        finally:
            connection.close()

    def test_reconstructs_complete_catalog_and_is_idempotent(self) -> None:
        first = PATCHER.patch_database(self.database, True)
        self.assertEqual(first.folio_categories_changed, 42)
        self.assertEqual(first.grade_caps_changed, 78)
        self.assertEqual(first.guide_rows_changed, 199)
        self.assertEqual(self.query_value("SELECT COUNT(*) FROM item_guide_elems WHERE item_guide_id=619"), 42)
        self.assertEqual(self.query_value("SELECT COUNT(*) FROM item_guide_elems WHERE item_guide_id=873"), 42)
        self.assertEqual(self.query_value("SELECT COUNT(*) FROM item_guide_elems WHERE item_guide_id=922"), 42)
        self.assertEqual(self.query_value("SELECT COUNT(*) FROM item_guide_elems WHERE item_guide_id=994"), 39)
        self.assertEqual(self.query_value("SELECT COUNT(*) FROM item_guide_elems WHERE item_id=48595"), 0)
        self.assertEqual(self.query_value("SELECT COUNT(*) FROM craft_d_categories WHERE use_only_doodad='f'"), 39)

        patched_hash = PATCHER.sha256(self.database)
        second = PATCHER.patch_database(self.database, True)
        self.assertEqual(second.folio_categories_changed, 0)
        self.assertEqual(second.grade_caps_changed, 0)
        self.assertEqual(second.guide_rows_changed, 0)
        self.assertEqual(PATCHER.sha256(self.database), patched_hash)

    def test_dry_run_is_read_only(self) -> None:
        before = PATCHER.sha256(self.database)
        result = PATCHER.patch_database(self.database, False)
        self.assertEqual(result.folio_categories_changed, 42)
        self.assertEqual(PATCHER.sha256(self.database), before)

    def test_rejects_partial_visibility_patch(self) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE craft_d_categories SET use_only_doodad='f' "
                "WHERE id=(SELECT MIN(id) FROM craft_d_categories)"
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(RuntimeError, "partial or unknown Erenor D-category visibility"):
            PATCHER.patch_database(self.database, False)


if __name__ == "__main__":
    unittest.main()
