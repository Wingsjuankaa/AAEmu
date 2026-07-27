#!/usr/bin/env python3
"""Artifact tests for the AA8-native quest 2257 V4 runtime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v4.sqlite3"
)
VERIFY_RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-native-nuian-green-arc-v4.verify.sqlite3"
)
MANIFEST = (
    ROOT / "generated" / "native-quest-2257-warning-villagers-v1-runtime-manifest.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


class NativeQuest2257Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.connection = sqlite3.connect(
            f"file:{RUNTIME.resolve().as_posix()}?mode=ro", uri=True
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_runtime_is_deterministic_and_integral(self) -> None:
        self.assertEqual(sha256(RUNTIME), sha256(VERIFY_RUNTIME))
        self.assertEqual(
            self.connection.execute("PRAGMA quick_check").fetchone()[0], "ok"
        )
        self.assertEqual(
            self.connection.execute("PRAGMA integrity_check").fetchone()[0], "ok"
        )

    def test_native_quest_graph_replaces_historical_rows(self) -> None:
        context = self.connection.execute(
            "SELECT category_id,chapter_idx,quest_idx,successive,race "
            "FROM quest_contexts WHERE id=2257"
        ).fetchone()
        self.assertEqual(context, (3, 1, 6, 1, 1))
        acts = self.connection.execute(
            "SELECT id,act_detail_type,act_detail_id,quest_component_id "
            "FROM quest_acts WHERE quest_component_id IN "
            "(9947,9949,9950,9998,17567) ORDER BY id"
        ).fetchall()
        self.assertEqual(
            acts,
            [
                (14149, "QuestActConReportNpc", 2089, 9949),
                (40846, "QuestActSupplyItem", 4813, 9950),
                (63968, "QuestActObjItemGather", 4330, 17567),
                (63969, "QuestActConAcceptDoodad", 795, 9947),
                (63970, "QuestActObjInteraction", 1113, 9998),
                (64097, "QuestActSupplyExp", 3927, 9950),
                (65625, "QuestActSupplyItem", 8875, 9950),
            ],
        )

    def test_corpse_accept_and_personal_interaction_phase_are_closed(self) -> None:
        funcs = self.connection.execute(
            "SELECT id,actual_func_type,actual_func_id,doodad_func_group_id,"
            "func_skill_id,next_phase FROM doodad_funcs "
            "WHERE id IN (38376,38377) ORDER BY id"
        ).fetchall()
        self.assertEqual(
            funcs,
            [
                (38376, "DoodadFuncQuest", 1507, 41492, 0, 41493),
                (38377, "DoodadFuncUse", 10813, 41493, 41925, 41494),
            ],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT quest_kind_id,quest_id FROM doodad_func_quests WHERE id=1507"
            ).fetchone(),
            (1, 2257),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT skill_id FROM doodad_func_uses WHERE id=10813"
            ).fetchone(),
            (0,),
        )

    def test_examination_skill_effect_chain_is_closed(self) -> None:
        rows = self.connection.execute(
            "SELECT se.id,se.effect_id,e.actual_type,e.actual_id "
            "FROM skill_effects se JOIN effects e ON e.id=se.effect_id "
            "WHERE se.skill_id=41925 ORDER BY se.id"
        ).fetchall()
        self.assertEqual(
            rows,
            [
                (59150, 77705, "InteractionEffect", 7864),
                (59152, 77710, "GainLootPackItemEffect", 4165),
            ],
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT doodad_id,source_direction,wi_id "
                "FROM interaction_effects WHERE id=7864"
            ).fetchone(),
            (0, 1, 19),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT loot_pack_id,consume_source_item,inherit_grade "
                "FROM gain_loot_pack_item_effects WHERE id=4165"
            ).fetchone(),
            (12908, 0, 0),
        )

    def test_native_quest_item_and_explicit_server_derived_loot(self) -> None:
        self.assertEqual(
            self.connection.execute(
                "SELECT loot_quest_id,category_id,max_stack_size "
                "FROM items WHERE id=16287"
            ).fetchone(),
            (2257, 64, 10),
        )
        self.assertEqual(
            self.connection.execute(
                "SELECT item_id,min_amount,max_amount,drop_rate "
                "FROM loots WHERE loot_pack_id=12908"
            ).fetchall(),
            [(16287, 1, 1, 10000000)],
        )
        derived = self.manifest["server_derived_rows"]
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0]["loot_pack_id"], 12908)
        self.assertEqual(derived[0]["item_id"], 16287)

    def test_adjacent_quest_remains_out_of_scope(self) -> None:
        self.assertEqual(
            self.manifest["scope"]["suppressed_adjacent_quest_ids"], [2258]
        )


if __name__ == "__main__":
    unittest.main()
