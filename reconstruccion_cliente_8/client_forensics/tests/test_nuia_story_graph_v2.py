from __future__ import annotations

import sqlite3
import unittest

from client_forensics.config import load_config
from client_forensics.nuia_story_graph_v2 import (
    EXPECTED_CATEGORY_COUNTS,
    EXPECTED_QUEST_COUNT,
    _native_story_v2,
    _race_compatible,
    parse_story_page_v2,
    story_v2_paths,
)


class StoryWikiV2ParserTests(unittest.TestCase):
    def test_completed_quest_stage_is_a_requirement(self) -> None:
        payload = b"""<html><head><title>Next - Quest - ArcheRage Wiki</title></head><body>
        <div>ID: 2</div>
        <div class='mb-2'>Completed the quest <a href='/na-en/db/quests/1'>First</a></div>
        <nav><a href='/na-en/db/quests/9'>NA Server</a></nav>
        </body></html>"""
        page = parse_story_page_v2(payload, quest_id=2)
        self.assertEqual(
            [(edge.relation, edge.dst_quest_id) for edge in page.edges],
            [("requires_precompleted_quest", 1)],
        )

    def test_nuia_bitmask_accepts_alliance_and_universal(self) -> None:
        self.assertTrue(_race_compatible(1))
        self.assertTrue(_race_compatible(13))
        self.assertTrue(_race_compatible(255))
        self.assertFalse(_race_compatible(2))


class NativeStoryV2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()
        cls.story = _native_story_v2(cls.config)

    def test_full_native_selection_reaches_chapter_31(self) -> None:
        rows = [source["row"] for source in self.story["contexts"]]
        self.assertEqual(len(rows), EXPECTED_QUEST_COUNT)
        self.assertEqual(int(rows[-1]["id"]), 10682)
        self.assertEqual(sorted({int(row["chapter_idx"]) for row in rows}), list(range(32)))
        counts = {}
        for row in rows:
            category = int(row["category_id"])
            counts[category] = counts.get(category, 0) + 1
        self.assertEqual(counts, EXPECTED_CATEGORY_COUNTS)

    def test_built_artifact_has_resolutions_transitions_and_terminal_audit(self) -> None:
        path = story_v2_paths(self.config)["database"]
        if not path.is_file():
            self.skipTest("Nuian story V2 artifact has not been built")
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quests").fetchone()[0], EXPECTED_QUEST_COUNT)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM validation_events WHERE state<>'confirmed'").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_transition_gates").fetchone()[0], 4)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_terminal_audits WHERE quest_id=10682").fetchone()[0], 4)
            self.assertEqual(connection.execute("SELECT resolved_dst_quest_id FROM story_wiki_edge_resolutions WHERE src_quest_id=7115 AND raw_dst_quest_id=7325 AND relation='opens_access_to'").fetchone()[0], 7119)
            self.assertEqual(connection.execute("SELECT resolved_dst_quest_id FROM story_wiki_edge_resolutions WHERE src_quest_id=7119 AND raw_dst_quest_id=7124 AND relation='opens_access_to'").fetchone()[0], 7123)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
