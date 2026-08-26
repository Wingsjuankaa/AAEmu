import json
import hashlib
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generated" / "aa10-crafting-wave1-manifest.json"
RUNTIME_POLICY = ROOT.parent / "AAEmu.Game" / "Data" / "aa10-crafting-wave1-policy.json"


class CraftingWave1ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.runtime_policy = json.loads(RUNTIME_POLICY.read_text(encoding="utf-8"))

    def test_complete_enabled_recipe_partition(self):
        recipes = self.data["recipes"]
        self.assertEqual(9949, len(recipes))
        self.assertEqual(9949, len({row["craft_id"] for row in recipes}))
        self.assertEqual(
            [row["craft_id"] for row in recipes],
            sorted(row["craft_id"] for row in recipes))
        self.assertEqual(
            self.data["coverage"]["states"],
            dict(sorted(Counter(row["state"] for row in recipes).items())))

    def test_executable_and_blocked_states_are_closed(self):
        for row in self.data["recipes"]:
            if row["state"] == "executable_wave1":
                self.assertEqual([], row["blockers"])
            else:
                self.assertEqual("blocked", row["state"])
                self.assertTrue(row["blockers"])
                self.assertEqual(sorted(set(row["blockers"])), row["blockers"])

    def test_sources_are_hashed_and_integrity_checked(self):
        for source in self.data["sources"].values():
            self.assertEqual(64, len(source["sha256"]))
            self.assertEqual("ok", source["checks"]["quick_check"])
            self.assertEqual("ok", source["checks"]["integrity_check"])

    def test_manifest_has_no_nondeterministic_timestamp(self):
        self.assertNotIn("generated_at", self.data)
        self.assertFalse(self.data["policy"]["legacy_fallback"])
        self.assertEqual("excluded", self.data["policy"]["craft_orders"])

    def test_runtime_policy_is_exact_manifest_allowlist(self):
        expected = [
            row["craft_id"] for row in self.data["recipes"]
            if row["state"] == "executable_wave1"
        ]
        self.assertEqual("aa10-crafting-runtime-policy-v1", self.runtime_policy["format"])
        self.assertEqual(expected, self.runtime_policy["executableCraftIds"])
        self.assertEqual(len(expected), len(set(expected)))
        self.assertEqual(
            hashlib.sha256(MANIFEST.read_bytes()).hexdigest().upper(),
            self.runtime_policy["sourceManifestSha256"])


if __name__ == "__main__":
    unittest.main()
