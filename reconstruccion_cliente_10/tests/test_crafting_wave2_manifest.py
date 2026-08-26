import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generated" / "aa10-crafting-wave2-manifest.json"
RUNTIME_POLICY = ROOT.parent / "AAEmu.Game" / "Data" / "aa10-crafting-wave2-policy.json"


class CraftingWave2ManifestTests(unittest.TestCase):
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
            if row["state"] == "executable_wave2":
                self.assertEqual([], row["blockers"])
            else:
                self.assertEqual("blocked", row["state"])
                self.assertTrue(row["blockers"])

    def test_wave2_promotes_economy_but_not_later_contracts(self):
        blockers = self.data["coverage"]["blockers"]
        self.assertNotIn("cost_deferred", blockers)
        self.assertNotIn("actability_deferred", blockers)
        self.assertEqual(15, blockers["missing_actability_group"])
        self.assertGreater(blockers["product_grade_deferred"], 0)
        self.assertGreater(blockers["product_rate_deferred"], 0)
        self.assertGreater(blockers["backpack_deferred"], 0)

    def test_runtime_policy_is_exact_allowlist(self):
        expected = [
            row["craft_id"] for row in self.data["recipes"]
            if row["state"] == "executable_wave2"
        ]
        self.assertEqual("aa10-crafting-runtime-policy-v2", self.runtime_policy["format"])
        self.assertEqual(expected, self.runtime_policy["executableCraftIds"])
        self.assertEqual(7064, len(expected))
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
