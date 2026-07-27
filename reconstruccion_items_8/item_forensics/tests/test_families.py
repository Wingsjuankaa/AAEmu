from __future__ import annotations

import unittest

from ..families import (
    FAMILIES,
    X2GAME_ITEM_IMPL_EVIDENCE,
    X2GAME_ITEM_IMPL_NAMES,
)


class ItemImplFamilyTests(unittest.TestCase):
    def test_x2game_switch_covers_every_native_impl_value(self) -> None:
        self.assertEqual(set(range(36)), set(X2GAME_ITEM_IMPL_NAMES))
        self.assertEqual("x2game.dll FUN_39874940", X2GAME_ITEM_IMPL_EVIDENCE)

    def test_previously_opaque_positive_item_impls_are_mapped(self) -> None:
        expected = {
            4: "bag",
            14: "portal",
            26: "music_sheet",
            31: "location",
            32: "rename_character",
            35: "bless_uthstin",
        }
        self.assertEqual(
            expected,
            {impl_id: FAMILIES[impl_id].name for impl_id in expected},
        )
        self.assertEqual(("item_bags",), FAMILIES[4].descriptor_tables)
        self.assertEqual(
            ("item_bless_uthstins",),
            FAMILIES[35].descriptor_tables,
        )


if __name__ == "__main__":
    unittest.main()
