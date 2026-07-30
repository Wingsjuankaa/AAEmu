from __future__ import annotations

import unittest

from reconstruccion_items_8.extract_native_equipment import TABLES

from ..registry import QuerySpec, attach_sql


class RegistrySqlSelectionTests(unittest.TestCase):
    def test_item_grade_buffs_registry_uses_native_five_column_result(
        self,
    ) -> None:
        spec = TABLES["item_grade_buffs"]
        self.assertEqual(
            spec["columns"],
            ["id", "buff_id", "item_grade_id", "item_id", "num_pieces"],
        )
        self.assertEqual(spec["layout"], ["68", "68", "68", "68", "68"])
        self.assertEqual(spec["start"], 0x3F71DC4)
        self.assertEqual(spec["expected"], 8_328)

    def test_explicit_sql_wins_when_table_has_multiple_queries(self) -> None:
        ordered_ids = (
            "SELECT id FROM item_grades ORDER BY grade_order ASC"
        )
        full_descriptor = (
            "SELECT id, color_argb, durability_value FROM item_grades"
        )
        spec = QuerySpec(
            table_name="item_grades",
            source_module="test",
            columns=("id", "color_argb", "durability_value"),
            layout=("68", "78", "60"),
            sql_text=full_descriptor,
        )

        attached = attach_sql(
            [spec],
            {
                "item_grades": [
                    {"sql": ordered_ids, "offset": 1},
                    {"sql": full_descriptor, "offset": 2},
                ]
            },
        )

        self.assertEqual(attached[0].sql_text, full_descriptor)
        self.assertEqual(attached[0].evidence["embedded_sql"]["offset"], 2)


if __name__ == "__main__":
    unittest.main()
