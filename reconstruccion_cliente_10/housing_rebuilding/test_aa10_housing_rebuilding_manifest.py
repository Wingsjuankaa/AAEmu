import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "generated" / "aa10-housing-rebuilding-manifest.json"


class HousingRebuildingManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_closed_catalogue_counts(self):
        summary = self.manifest["summary"]
        self.assertEqual(837, summary["housing_templates"])
        self.assertEqual(499, summary["templates_with_pack"])
        self.assertEqual(223, summary["definitions"])
        self.assertEqual(1486, summary["materials"])
        self.assertEqual(2958, summary["pack_routes"])
        self.assertEqual(
            {
                "executable": 219,
                "missing_materials": 1,
                "missing_skill_consumer": 1,
                "territorial_subsystem_required": 2,
            },
            summary["classification"],
        )

    def test_every_definition_has_one_explicit_status(self):
        allowed = {
            "executable",
            "missing_target_housing",
            "missing_skill_consumer",
            "territorial_subsystem_required",
            "missing_materials",
            "missing_item",
        }
        definitions = self.manifest["definitions"]
        self.assertEqual(223, len({definition["id"] for definition in definitions}))
        self.assertTrue(all(definition["status"] in allowed for definition in definitions))

    def test_stone_rose_manor_pack_has_twelve_native_routes(self):
        pack = next(pack for pack in self.manifest["packs"] if pack["id"] == 15)
        self.assertIn(313, pack["source_housing_ids"])
        self.assertEqual(12, len(pack["routes"]))
        self.assertEqual(
            {6, 7, 8, 73, 74, 75, 76, 77, 78, 79, 80, 81},
            {route["rebuilding_id"] for route in pack["routes"]},
        )


if __name__ == "__main__":
    unittest.main()
