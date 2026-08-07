#!/usr/bin/env python3

import json
import sqlite3
import unittest
from pathlib import Path


DOMAIN = Path(__file__).resolve().parent
RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-quest4411-v2.sqlite3"
)
MANIFEST = DOMAIN / "generated" / "native-quest-4411-marian-v2-manifest.json"


class NativeQuest4411Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect(
            f"file:{RUNTIME.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_manifest_and_integrity(self):
        document = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual("native-quest-4411-marian-v1-runtime", document["phase"])
        self.assertEqual("B3514EB99127BEACBC469A52789D7C99C3347CE43B2F2AB661984E644EE178C8", document["output"]["sha256"])
        self.assertEqual("ok", self.connection.execute("PRAGMA quick_check").fetchone()[0])
        self.assertEqual("ok", self.connection.execute("PRAGMA integrity_check").fetchone()[0])

    def test_quest_targets_native_marian_doodad(self):
        row = self.connection.execute(
            "SELECT count,doodad_id,wi_id FROM quest_act_obj_interactions WHERE id=1115"
        ).fetchone()
        self.assertEqual((1, 14125, 19), row)

    def test_marian_proxy_uses_interactive_native_phase(self):
        self.assertEqual(
            (1, 1, 1),
            self.connection.execute(
                "SELECT client_doodad,once_one_interaction,once_one_man "
                "FROM doodad_almighties WHERE id=14125"
            ).fetchone(),
        )
        self.assertEqual(
            (14125, "npctype://10797"),
            self.connection.execute(
                "SELECT doodad_almighty_id,model FROM doodad_func_groups WHERE id=41603"
            ).fetchone(),
        )
        self.assertEqual(
            ("DoodadFuncUse", 10936, 41603, 41999, -1),
            self.connection.execute(
                "SELECT actual_func_type,actual_func_id,doodad_func_group_id,"
                "func_skill_id,next_phase FROM doodad_funcs WHERE id=38602"
            ).fetchone(),
        )
        self.assertEqual(
            (41999,),
            self.connection.execute(
                "SELECT skill_id FROM doodad_func_uses WHERE id=10936"
            ).fetchone(),
        )

    def test_talk_skill_emits_interaction_and_farewell(self):
        self.assertEqual(
            [(59299, 77957), (59325, 77994)],
            self.connection.execute(
                "SELECT id,effect_id FROM skill_effects WHERE skill_id=41999 ORDER BY id"
            ).fetchall(),
        )
        self.assertEqual(
            (0, 19, 1),
            self.connection.execute(
                "SELECT doodad_id,wi_id,source_direction "
                "FROM interaction_effects WHERE id=7874"
            ).fetchone(),
        )
        speech = self.connection.execute(
            "SELECT speech FROM bubble_effects WHERE id=6013"
        ).fetchone()
        self.assertTrue(speech and speech[0].strip())

    def test_report_and_rewards_are_present_for_next_frontier(self):
        report = self.connection.execute(
            "SELECT r.npc_id FROM quest_components qc "
            "JOIN quest_acts qa ON qa.quest_component_id=qc.id "
            "JOIN quest_act_con_report_npcs r ON r.id=qa.act_detail_id "
            "WHERE qc.quest_context_id=4411 AND qa.act_detail_type='QuestActConReportNpc'"
        ).fetchall()
        self.assertEqual([(11283,)], report)
        reward_items = self.connection.execute(
            "SELECT DISTINCT s.item_id FROM quest_components qc "
            "JOIN quest_acts qa ON qa.quest_component_id=qc.id "
            "JOIN quest_act_supply_items s ON s.id=qa.act_detail_id "
            "WHERE qc.quest_context_id=4411 AND qa.act_detail_type='QuestActSupplyItem' "
            "ORDER BY s.item_id"
        ).fetchall()
        self.assertEqual([(23633,), (24087,), (25076,), (34003,), (47866,)], reward_items)
        for item_id, in reward_items:
            self.assertIsNotNone(
                self.connection.execute("SELECT 1 FROM items WHERE id=?", (item_id,)).fetchone()
            )


if __name__ == "__main__":
    unittest.main()
