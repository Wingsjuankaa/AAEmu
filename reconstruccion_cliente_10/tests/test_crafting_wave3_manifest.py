import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generated" / "aa10-crafting-wave3-manifest.json"
RUNTIME_POLICY = ROOT.parent / "AAEmu.Game" / "Data" / "aa10-crafting-wave3-policy.json"


class CraftingWave3ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runtime_policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))

    def test_complete_closed_partition(self):
        recipes = self.data["recipes"]
        self.assertEqual(9949, len(recipes))
        self.assertEqual(9949, len({row["craft_id"] for row in recipes}))
        self.assertEqual(
            self.data["coverage"]["states"],
            dict(sorted(Counter(row["state"] for row in recipes).items())))
        for row in recipes:
            if row["state"] == "executable_wave3":
                self.assertEqual([], row["blockers"])
            else:
                self.assertEqual("blocked", row["state"])
                self.assertTrue(row["blockers"])

    def test_wave3_promotes_grades_and_native_rates_but_not_backpacks(self):
        blockers = self.data["coverage"]["blockers"]
        self.assertNotIn("material_grade_deferred", blockers)
        self.assertNotIn("product_grade_deferred", blockers)
        self.assertNotIn("product_rate_deferred", blockers)
        self.assertNotIn("invalid_material_grade", blockers)
        self.assertNotIn("invalid_upper_grade_contract", blockers)
        self.assertNotIn("invalid_product_grade", blockers)
        self.assertNotIn("invalid_product_rate", blockers)
        self.assertEqual(389, blockers["backpack_deferred"])

    def test_runtime_policy_is_exact_allowlist(self):
        expected = [
            row["craft_id"] for row in self.data["recipes"]
            if row["state"] == "executable_wave3"
        ]
        self.assertEqual("aa10-crafting-runtime-policy-v3", self.runtime_policy["format"])
        self.assertEqual(expected, self.runtime_policy["executableCraftIds"])
        self.assertEqual(8541, len(expected))
        self.assertEqual(
            hashlib.sha256(MANIFEST.read_bytes()).hexdigest().upper(),
            self.runtime_policy["sourceManifestSha256"])

    def test_sources_are_exact_and_healthy(self):
        for source in self.data["sources"].values():
            self.assertEqual(64, len(source["sha256"]))
            self.assertEqual("ok", source["checks"]["quick_check"])
            self.assertEqual("ok", source["checks"]["integrity_check"])


if __name__ == "__main__":
    unittest.main()
