#!/usr/bin/env python3
import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-point0-merchant-deven-v1.sqlite3"
)
MANIFEST = Path(__file__).with_name("manifest-b14c-deven-merchant.json")
PACK_ID = 914119
CLOAKED = {
    23862, 23866, 23870, 23874, 23878, 23882, 23886, 23890, 23894,
    31693, 31694, 31695, 31696, 31697, 31698, 31699, 31700, 51194,
}
HONOR = {
    18391, 18393, 18395, 18397, 18399, 18401, 18403, 18405,
    18407, 18409, 18411, 18413, 18415, 18417, 18419, 50802,
}
BOXES = {47868, 47869, 51185}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class B14cDevenMerchantRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect(RUNTIME)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_manifest_matches_runtime(self):
        self.assertEqual(sha256(RUNTIME), self.manifest["output"]["sha256"])
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])

    def test_stock_is_the_exact_37_row_native_pack(self):
        rows = self.connection.execute(
            "SELECT item_id,grade_id,currency_id,sort_order FROM merchant_goods "
            "WHERE merchant_pack_id=? ORDER BY sort_order",
            (PACK_ID,),
        ).fetchall()
        self.assertEqual(37, len(rows))
        self.assertEqual(CLOAKED | HONOR | BOXES, {row[0] for row in rows})
        self.assertEqual(list(range(37)), [row[3] for row in rows])
        self.assertTrue(all(row[2] == 0 for row in rows))
        self.assertEqual(21, sum(row[1] == 0 for row in rows))
        self.assertEqual(16, sum(row[1] == 2 for row in rows))

    def test_every_stock_item_has_a_complete_definition(self):
        rows = self.connection.execute(
            """
            SELECT g.item_id,i.id,c.coverage,c.missing_dependencies
            FROM merchant_goods g
            LEFT JOIN items i ON i.id=g.item_id
            LEFT JOIN aaemu_item_definition_coverage c ON c.item_id=g.item_id
            WHERE g.merchant_pack_id=?
            """,
            (PACK_ID,),
        ).fetchall()
        self.assertEqual(37, len(rows))
        self.assertTrue(all(row[1] == row[0] for row in rows))
        self.assertTrue(all(row[2] == "complete" and row[3] == "" for row in rows))

    def test_visible_shop_prices_match_corroborated_values(self):
        placeholders = ",".join("?" for _ in CLOAKED)
        prices = {
            row[0]: row[1]
            for row in self.connection.execute(
                f"SELECT id,price FROM items WHERE id IN ({placeholders})",
                sorted(CLOAKED),
            )
        }
        self.assertEqual({500_000}, set(prices.values()))
        honor_placeholders = ",".join("?" for _ in HONOR)
        honor_prices = {
            row[1]
            for row in self.connection.execute(
                f"SELECT id,price FROM items WHERE id IN ({honor_placeholders})",
                sorted(HONOR),
            )
        }
        self.assertEqual({1_000_000, 1_400_000}, honor_prices)

    def test_honor_descriptors_and_every_use_skill_are_loaded(self):
        placeholders = ",".join("?" for _ in HONOR)
        weapon_ids = {
            row[0]
            for row in self.connection.execute(
                f"SELECT item_id FROM item_weapons WHERE item_id IN ({placeholders})",
                sorted(HONOR),
            )
        }
        self.assertEqual(HONOR, weapon_ids)
        missing_skills = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM merchant_goods g
            JOIN items i ON i.id=g.item_id
            LEFT JOIN skills s ON s.id=i.use_skill_id
            WHERE g.merchant_pack_id=? AND i.use_skill_id>0 AND s.id IS NULL
            """,
            (PACK_ID,),
        ).fetchone()[0]
        self.assertEqual(0, missing_skills)


if __name__ == "__main__":
    unittest.main()
