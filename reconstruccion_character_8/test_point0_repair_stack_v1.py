#!/usr/bin/env python3
import sqlite3
import unittest
from pathlib import Path


RUNTIME = Path(
    r"D:\Proyectos\AAemu\client_kakao"
    r"\compact-8.0-runtime-point0-repair-stack-v1.sqlite3"
)


class Point0RepairRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect(RUNTIME)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def actions(self, character_id, ability_id):
        return dict(
            self.connection.execute(
                "SELECT slot_index,action_id FROM native_character_creation_action_slots "
                "WHERE character_id=? AND ability_id=? AND action_type=2 ORDER BY slot_index",
                (character_id, ability_id),
            )
        )

    def test_full_matrix_is_preserved(self):
        self.assertEqual(
            20832,
            self.connection.execute(
                "SELECT COUNT(*) FROM native_character_creation_action_slots"
            ).fetchone()[0],
        )

    def test_nuian_female_has_initial_basic_and_only_her_racial_actions(self):
        actions = self.actions(2, 1)
        self.assertEqual(18132, actions[1])
        self.assertEqual(2, actions[13])
        self.assertEqual(16287, actions[16])
        self.assertEqual(35420, actions[17])
        self.assertEqual(35418, actions[18])
        self.assertEqual(14, len(actions))

    def test_every_combination_has_global_and_native_addable_template_actions(self):
        counts = self.connection.execute(
            "SELECT character_id,ability_id,COUNT(*) "
            "FROM native_character_creation_action_slots WHERE action_type=2 "
            "GROUP BY character_id,ability_id"
        ).fetchall()
        self.assertEqual(96, len(counts))
        expected_by_character = {
            1: 14, 2: 14, 3: 13, 4: 13, 5: 14, 6: 14,
            9: 14, 10: 14, 13: 13, 14: 13, 15: 14, 16: 14,
        }
        self.assertTrue(
            all(count == expected_by_character[character_id]
                for character_id, _, count in counts)
        )

    def test_no_action_references_missing_skill(self):
        missing = self.connection.execute(
            "SELECT COUNT(*) FROM native_character_creation_action_slots a "
            "LEFT JOIN skills s ON s.id=a.action_id "
            "WHERE a.action_type=2 AND s.id IS NULL"
        ).fetchone()[0]
        self.assertEqual(0, missing)


if __name__ == "__main__":
    unittest.main()
