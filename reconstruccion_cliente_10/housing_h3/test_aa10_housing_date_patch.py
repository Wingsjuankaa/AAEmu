import unittest

from Scripts.PatchAa10HousingDateFormatting import patch_maintain_source, patch_maintain_view_source


class HousingDatePatchTests(unittest.TestCase):
    def test_maintain_patch_is_scoped_to_calendar_format_and_suffix(self) -> None:
        source = """
local dueStr = locale.time.GetDateToDateFormat(taxInfo.dueTime)
dueDate = string.format("%s%s%s|r", redHexColor, dueStr, locale.housing.untilTerm)
dueDate = string.format("%s%s", dueStr, locale.housing.untilTerm)
"""

        patched = patch_maintain_source(source)

        self.assertIn("GetDateToSimpleDateFormat(taxInfo.dueTime)", patched)
        self.assertIn('string.format("%s%s|r", redHexColor, dueStr)', patched)
        self.assertIn("dueDate = dueStr", patched)
        self.assertNotIn("untilTerm", patched)


    def test_prepay_patch_uses_native_simple_calendar_date(self) -> None:
        source = (
            "local prepayTimeStr = "
            "locale.time.GetDateToDateFormat(window.taxInfo.prepayTime)"
        )

        patched = patch_maintain_view_source(source)

        self.assertEqual(
            patched,
            "local prepayTimeStr = "
            "locale.time.GetDateToSimpleDateFormat(window.taxInfo.prepayTime)",
        )


if __name__ == "__main__":
    unittest.main()
