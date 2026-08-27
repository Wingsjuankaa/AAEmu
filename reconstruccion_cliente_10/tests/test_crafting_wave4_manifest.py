import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generated" / "aa10-crafting-wave4-manifest.json"
RUNTIME_POLICY = ROOT.parent / "AAEmu.Game" / "Data" / "aa10-crafting-wave4-policy.json"


class CraftingWave4ManifestTests(unittest.TestCase):
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
            if row["state"] == "executable_wave4":
                self.assertEqual([], row["blockers"])
            else:
                self.assertEqual("blocked", row["state"])
                self.assertTrue(row["blockers"])

    def test_wave4_promotes_only_native_autoequip_backpacks(self):
        blockers = self.data["coverage"]["blockers"]
        self.assertNotIn("backpack_deferred", blockers)
        self.assertEqual(91, blockers["missing_native_rate_consumer"])
        self.assertEqual(
            "bag plus atomic auto-equipped BackpackTemplate; an equipped glider moves "
            "only when post-consumption bag capacity exists",
            self.data["policy"]["product_destination"])

    def test_runtime_policy_is_exact_allowlist(self):
        expected = [
            row["craft_id"] for row in self.data["recipes"]
            if row["state"] == "executable_wave4"
        ]
        self.assertEqual("aa10-crafting-runtime-policy-v4", self.runtime_policy["format"])
        self.assertEqual(expected, self.runtime_policy["executableCraftIds"])
        self.assertEqual(8835, len(expected))
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
