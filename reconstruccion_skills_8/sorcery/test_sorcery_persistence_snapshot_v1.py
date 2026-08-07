import unittest

from snapshot_sorcery_persistence_v1 import build_snapshot, parse_tsv


class SorceryPersistenceSnapshotV1Tests(unittest.TestCase):
    def test_tsv_parser_rejects_silent_column_loss(self):
        with self.assertRaises(ValueError):
            parse_tsv("1\t2", ["a", "b", "c"])

    def test_snapshot_filters_only_sorcery_and_preserves_heir_state(self):
        responses = {
            "characters": "1\tDannia\t55\t1\t10\t5000\t7\t6\t2\t0\t148\t2026-08-05 10:00:00\n",
            "abilities": "2\t100\n7\t999\n",
            "skills": "10664\t2\tSkill\n14376\t14\tSkill\n15\t1\tBuff\n500\t1\tBuff\n",
            "heir_skill_activations": "21\t36478\n",
            "character_skill_active_types": "21\t36478\t1\n",
        }

        def query(sql):
            for key, value in responses.items():
                if f"FROM {key}" in sql:
                    return value
            raise AssertionError(sql)

        snapshot = build_snapshot(1, query)

        self.assertEqual("7", snapshot["sorcery_ability"]["id"])
        self.assertEqual(["10664"], [row["id"] for row in snapshot["sorcery_skills"]])
        self.assertEqual(["15"], [row["id"] for row in snapshot["sorcery_passives"]])
        self.assertEqual("36478", snapshot["heir_activations"][0]["successor_skill_id"])
        self.assertEqual(1, snapshot["summary"]["active_type_count"])


if __name__ == "__main__":
    unittest.main()
