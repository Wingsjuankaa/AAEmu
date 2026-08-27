import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "generated" / "aa10-crafting-wave5-manifest.json"
RUNTIME_POLICY = ROOT.parent / "AAEmu.Game" / "Data" / "aa10-crafting-wave5-policy.json"


class CraftingWave5ManifestTests(unittest.TestCase):
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
            if row["state"] == "executable_wave5":
                self.assertEqual([], row["blockers"])
                self.assertTrue(row["native_consumers"])
            else:
                self.assertEqual("blocked", row["state"])
                self.assertTrue(row["blockers"])

    def test_missing_execution_consumer_fails_closed(self):
        blockers = self.data["coverage"]["blockers"]
        self.assertGreater(blockers["missing_native_consumer"], 0)
        self.assertEqual(
            9949,
            self.data["coverage"]["native_consumer_union"] +
            blockers["missing_native_consumer"])
        for row in self.data["recipes"]:
            if not row["native_consumers"]:
                self.assertIn("missing_native_consumer", row["blockers"])
            if row["state"] == "executable_wave5":
                self.assertNotIn("butler_specialty_trade_todo", row["native_consumers"])
                self.assertNotIn("quest_progress_observer", row["native_consumers"])

    def test_runtime_policy_is_exact_allowlist(self):
        expected = [
            row["craft_id"] for row in self.data["recipes"]
            if row["state"] == "executable_wave5"
        ]
        self.assertEqual("aa10-crafting-runtime-policy-v5", self.runtime_policy["format"])
        self.assertEqual(expected, self.runtime_policy["executableCraftIds"])
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
