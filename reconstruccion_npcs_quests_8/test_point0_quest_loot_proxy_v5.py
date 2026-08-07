import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(r"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-point0-quest-loot-proxy-v5.sqlite3")
MANIFEST = ROOT / "reconstruccion_npcs_quests_8" / "generated" / "point0-quest-loot-proxy-v5-runtime-manifest.json"


class Point0QuestLootProxyV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect(RUNTIME)
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_exact_quest_objective_and_loot_relation_survive(self):
        self.assertEqual(
            (24126, 1, 1, 0, 0),
            self.connection.execute(
                "SELECT item_id,count,cleanup,destroy_when_drop,drop_when_destroy "
                "FROM quest_act_obj_item_gathers WHERE id=2046"
            ).fetchone(),
        )
        self.assertEqual(
            (8, 8, 10000000.0, 10000000.0, 1, 1),
            self.connection.execute(
                "SELECT COUNT(*),COUNT(DISTINCT loot_pack_id),MIN(drop_rate),MAX(drop_rate),"
                "MIN(min_amount),MAX(max_amount) FROM loots WHERE item_id=24126"
            ).fetchone(),
        )

    def test_proxy_is_generic_bounded_and_dependency_free(self):
        self.assertEqual(
            (24126, 18, 0, 1, 2, 1, 0, 0, 2263, 0, 0, 0, -1),
            self.connection.execute(
                "SELECT id,category_id,impl_id,level,bind_id,max_stack_size,sellable,"
                "gradable,loot_quest_id,use_skill_id,buff_id,craft_id,fixed_grade "
                "FROM items WHERE id=24126"
            ).fetchone(),
        )

    def test_proxy_is_explicitly_server_derived_not_native_recovered(self):
        self.assertEqual(
            ("generic", "complete", "", "server_derived_accepted:quest2263_native_tombstone_proxy:v1"),
            self.connection.execute(
                "SELECT concrete_type,coverage,missing_dependencies,provenance "
                "FROM aaemu_item_definition_coverage WHERE item_id=24126"
            ).fetchone(),
        )
        self.assertEqual("server_derived_accepted", self.manifest["classification"])
        self.assertEqual(0, self.manifest["scope"]["historical_3_0_rows"])
        self.assertEqual(0, self.manifest["scope"]["native_item_rows_claimed"])

    def test_gap_census_changes_only_by_the_bounded_proxy(self):
        self.assertEqual(
            {"relations": 743, "quests": 590, "items": 532},
            self.manifest["gap_census"]["before"],
        )
        self.assertEqual(
            {"relations": 742, "quests": 589, "items": 531},
            self.manifest["gap_census"]["after"],
        )
        self.assertEqual([24126], self.manifest["scope"]["item_ids"])

    def test_sqlite_integrity(self):
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
