from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from client_forensics.config import load_config
from client_forensics.nuia_story_graph import (
    EXPECTED_ACT_TYPES,
    EXPECTED_CHAPTERS,
    EXPECTED_QUEST_IDS,
    _create_database,
    _native_story,
    _order_edges,
    parse_story_page,
    story_paths,
)
from client_forensics.quest_item_crosswalk import _write_snapshot


class StoryWikiParserTests(unittest.TestCase):
    def test_requires_and_opens_are_structural_and_reciprocal(self) -> None:
        payload = b"""<html><head><title>Middle - Quest - ArcheRage Wiki</title></head><body>
        <div>ID: 2</div>
        <div class='m-0 cl-l-yellow'><span>Requires precompleted quest:</span>
          <a href='/na-en/db/quests/1'>First</a></div>
        <div class='m-0 cl-l-yellow'><span>Opens access to the quest:</span>
          <a href='/na-en/db/quests/3'>Third</a></div>
        </body></html>"""
        page = parse_story_page(payload, quest_id=2)
        self.assertEqual(page.parse_state, "confirmed")
        self.assertEqual(
            [(row.relation, row.dst_quest_id) for row in page.edges],
            [("requires_precompleted_quest", 1), ("opens_access_to", 3)],
        )

    def test_navigation_links_do_not_become_story_edges(self) -> None:
        payload = b"""<html><head><title>Quest - Quest - ArcheRage Wiki</title></head><body>
        <div>ID: 9</div><nav><a href='/na-en/db/quests/10'>Quest catalog</a></nav>
        </body></html>"""
        self.assertEqual(parse_story_page(payload, quest_id=9).edges, ())

    def test_6839_terminal_states_include_present_404_transient_and_parse_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            cases = (
                (200, b"<html><title>Root - Quest - ArcheRage Wiki</title><body>ID: 6839</body></html>", "confirmed"),
                (404, b"missing", "permanent_missing"),
                (503, b"retry", "transient_error"),
                (200, b"<html><title>bad</title></html>", "parse_failed"),
            )
            for status, payload, expected in cases:
                metadata = _write_snapshot(
                    cache,
                    quest_id=6839,
                    canonical_url="https://example/na-en/db/quests/6839",
                    status_code=status,
                    payload=payload,
                    content_type="text/html",
                    final_url="https://example/na-en/db/quests/6839",
                    locale="na-en",
                    error=None,
                )
                self.assertEqual(metadata["page_state"], expected)


class StoryOrderTests(unittest.TestCase):
    @staticmethod
    def source(quest_id: int, chapter: int, index: int) -> dict[str, object]:
        return {"row": {"id": quest_id, "chapter_idx": chapter, "quest_idx": index}}

    def test_native_ordinal_never_becomes_native_dependency(self) -> None:
        contexts = [self.source(1, 1, 1), self.source(2, 1, 2), self.source(3, 2, 1)]
        edges = _order_edges(contexts, [])
        self.assertEqual(edges[0]["overall_state"], "native_ordinal_candidate")
        self.assertEqual(edges[1]["overall_state"], "chapter_boundary_unresolved")
        self.assertTrue(all(row["native_edge_state"] == "not_demonstrated" for row in edges))

    def test_wiki_reciprocity_only_corroborates_order(self) -> None:
        contexts = [self.source(1, 1, 1), self.source(2, 1, 2)]
        wiki = [
            {"relation": "opens_access_to", "src_quest_id": 1, "dst_quest_id": 2},
            {"relation": "requires_precompleted_quest", "src_quest_id": 2, "dst_quest_id": 1},
        ]
        edge = _order_edges(contexts, wiki)[0]
        self.assertEqual(edge["overall_state"], "corroborated_order")
        self.assertNotEqual(edge["overall_state"], "confirmed_native_dependency")


class StorySchemaTests(unittest.TestCase):
    def test_required_tables_and_indexes_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            connection = _create_database(Path(temporary) / "story.sqlite3")
            objects = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
            connection.close()
        self.assertTrue(
            {
                "story_quests", "scope_boundary_candidates", "story_order_edges",
                "story_quest_components", "story_quest_acts", "story_quest_endpoints",
                "story_quest_items", "story_dependency_closure", "wiki_story_pages",
                "wiki_story_edges", "downstream_audit_queue", "idx_story_quests_order",
                "idx_story_closure_dst_state", "idx_audit_order_severity",
            }.issubset(objects)
        )


class NativeStoryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()
        cls.story = _native_story(cls.config)

    def test_root_is_exact_native_category_and_race_partition(self) -> None:
        ids = tuple(int(row["row"]["id"]) for row in self.story["contexts"])
        self.assertEqual(ids, EXPECTED_QUEST_IDS)
        self.assertTrue(all(int(row["row"]["category_id"]) == 3 and int(row["row"]["race"]) == 1 for row in self.story["contexts"]))

    def test_counts_chapters_and_all_act_types(self) -> None:
        self.assertEqual((len(self.story["contexts"]), len(self.story["components"]), len(self.story["acts"])), (55, 222, 344))
        chapters = {}
        for source in self.story["contexts"]:
            chapter = int(source["row"]["chapter_idx"])
            chapters[chapter] = chapters.get(chapter, 0) + 1
        self.assertEqual(chapters, EXPECTED_CHAPTERS)
        act_types = {}
        for source in self.story["acts"]:
            value = str(source["row"]["act_detail_type"])
            act_types[value] = act_types.get(value, 0) + 1
        self.assertEqual(act_types, EXPECTED_ACT_TYPES)

    def test_external_neighbors_are_not_selected_by_id_zone_or_name(self) -> None:
        selected = {int(row["row"]["id"]) for row in self.story["contexts"]}
        external = [row["row"] for row in self.story["contexts_all"] if int(row["row"]["id"]) not in selected]
        self.assertTrue(any(int(row.get("race", 0)) == 1 for row in external))
        self.assertTrue(all(not (int(row.get("category_id", 0)) == 3 and int(row.get("race", 0)) == 1) for row in external))

    def test_final_artifact_anchor_cases_when_present(self) -> None:
        path = story_paths(self.config)["database"]
        if not path.is_file():
            self.skipTest("Nuian story artifact has not been built")
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints WHERE quest_id=2532 AND endpoint_kind='doodad' AND endpoint_id=14074 AND proxy_npc_id=10581").fetchone()[0], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints WHERE quest_id=2532 AND endpoint_kind='npc' AND endpoint_id=14074").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE quest_id=2264 AND item_id=24967 AND item_role='objective_gather' AND item_closure_state='tombstone'").fetchone()[0], 1)
            self.assertGreater(
                connection.execute(
                    "SELECT COUNT(*) FROM story_dependency_closure "
                    "WHERE root_quest_id=2264 AND dst_entity_key='world_interaction:19'"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE root_quest_id=2265 AND src_entity_key='item:34000' AND dst_entity_key='skill:35238'").fetchone()[0], 1)
            self.assertEqual(
                dict(connection.execute("SELECT dst_id,relation FROM wiki_story_relations WHERE quest_id=2258 AND dst_kind='item' AND dst_id IN (16288,23633) ORDER BY dst_id")),
                {16288: "quest_item", 23633: "fixed_reward"},
            )
            self.assertEqual(
                dict(connection.execute("SELECT selection_mode,COUNT(*) FROM story_quest_items WHERE quest_id=330 GROUP BY selection_mode ORDER BY selection_mode")),
                {"fixed": 3, "selective": 2},
            )
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM validation_events WHERE state<>'confirmed'").fetchone()[0], 0)
        finally:
            connection.close()

    def test_final_artifact_preserves_all_rows_and_terminal_states(self) -> None:
        path = story_paths(self.config)["database"]
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            counts = {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "story_quests", "story_quest_components", "story_quest_acts",
                    "story_quest_endpoints", "story_quest_items", "wiki_story_pages",
                )
            }
            self.assertEqual(counts, {
                "story_quests": 55, "story_quest_components": 222,
                "story_quest_acts": 344, "story_quest_endpoints": 108,
                "story_quest_items": 156, "wiki_story_pages": 55,
            })
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE crosswalk_state='linked'").fetchone()[0], 130)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE item_role='objective_gather'").fetchone()[0], 17)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE item_role='objective_use'").fetchone()[0], 9)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_order_edges WHERE reciprocal_state='reciprocal'").fetchone()[0], 48)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_order_edges WHERE overall_state='chapter_boundary_unresolved'").fetchone()[0], 6)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_endpoints WHERE closure_state IS NULL OR spawn_state IS NULL").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_quest_items WHERE item_closure_state IS NULL").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM story_dependency_closure WHERE closure_state IS NULL").fetchone()[0], 0)
            self.assertGreater(connection.execute("SELECT COUNT(*) FROM scope_boundary_candidates").fetchone()[0], 0)
        finally:
            connection.close()

    def test_item_skill_effect_and_buff_closure_is_reachable(self) -> None:
        path = story_paths(self.config)["database"]
        connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            terminal_paths = connection.execute(
                "WITH RECURSIVE paths(root,node,depth,path) AS ("
                " SELECT root_quest_id,dst_entity_key,1,src_entity_key||'>'||dst_entity_key"
                " FROM story_dependency_closure WHERE src_entity_key LIKE 'item:%' AND dst_entity_key LIKE 'skill:%'"
                " UNION ALL"
                " SELECT p.root,e.dst_entity_key,p.depth+1,p.path||'>'||e.dst_entity_key"
                " FROM paths p JOIN story_dependency_closure e"
                " ON e.root_quest_id=p.root AND e.src_entity_key=p.node"
                " WHERE p.depth<8 AND instr(p.path,e.dst_entity_key)=0"
                ") SELECT"
                " SUM(CASE WHEN node LIKE 'effect:%' THEN 1 ELSE 0 END),"
                " SUM(CASE WHEN node LIKE 'buff:%' OR node LIKE 'plot:%' THEN 1 ELSE 0 END)"
                " FROM paths"
            ).fetchone()
            self.assertGreater(terminal_paths[0], 0)
            self.assertGreater(terminal_paths[1], 0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
