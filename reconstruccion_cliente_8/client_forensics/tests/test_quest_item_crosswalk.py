from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from client_forensics.quest_item_crosswalk import (
    QuestWikiClient,
    _comparison_rows,
    _create_database,
    _item_closure_row,
    _snapshot_paths,
    _snapshot_valid,
    _write_snapshot,
    build_quest_item_cache_manifest,
    extract_native_grants,
    parse_quest_item_page,
)
from client_forensics.util import canonical_json


FIXTURES = Path(__file__).parent / "fixtures" / "quest_item_wiki"


def _native_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE native_rows(
            native_row_key TEXT PRIMARY KEY,
            entity_key TEXT,
            entity_kind TEXT,
            native_id TEXT,
            source_table TEXT NOT NULL,
            state TEXT NOT NULL,
            row_json TEXT NOT NULL,
            provenance TEXT NOT NULL,
            evidence_json TEXT NOT NULL
        )
        """
    )

    def add(table: str, row: dict[str, object]) -> None:
        native_id = int(row["id"])
        connection.execute(
            "INSERT INTO native_rows VALUES(?,?,?,?,?,?,?,?,?)",
            (
                f"{table}:{native_id}",
                None,
                table,
                str(native_id),
                table,
                "confirmed",
                canonical_json(row),
                "fixture",
                "{}",
            ),
        )

    add("quest_contexts", {"id": 1})
    for component_id, kind in ((10, 3), (11, 8)):
        add(
            "quest_components",
            {
                "id": component_id,
                "component_kind_id": kind,
                "quest_context_id": 1,
            },
        )
    types = (
        ("QuestActSupplyItem", "quest_act_supply_items", 100, 200, 10),
        ("QuestActSupplySelectiveItem", "quest_act_supply_selective_items", 101, 201, 11),
        ("QuestActSupplyRankedItem", "quest_act_supply_ranked_items", 102, 202, 11),
        ("QuestActSupplyResultRankedItem", "quest_act_supply_result_ranked_items", 103, 203, 11),
    )
    for act_type, table, act_id, detail_id, component_id in types:
        add(
            "quest_acts",
            {
                "id": act_id,
                "act_detail_id": detail_id,
                "act_detail_type": act_type,
                "quest_component_id": component_id,
            },
        )
        detail = {"id": detail_id, "item_id": 1000 + detail_id, "count": 1, "grade_id": 0}
        if "Ranked" in act_type:
            detail["rank"] = 1
        if act_type == "QuestActSupplyResultRankedItem":
            detail["result"] = 0
        add(table, detail)
    add(
        "quest_act_supply_items",
        {"id": 999, "item_id": 1999, "count": 1, "grade_id": 0},
    )
    connection.commit()
    connection.close()


class QuestItemParserTests(unittest.TestCase):
    def test_2258_sections_ignore_context_contamination_and_auxiliary_table(self) -> None:
        page = parse_quest_item_page(
            (FIXTURES / "2258.html").read_bytes(), entity_id=2258
        )
        self.assertEqual(page.parse_state, "confirmed")
        self.assertEqual(
            [(row.item_id, row.section_kind) for row in page.mentions],
            [(16288, "quest_item"), (23633, "fixed_reward")],
        )
        self.assertNotIn("accept_from", {row.section_kind for row in page.mentions})
        self.assertNotIn("report_to", {row.section_kind for row in page.mentions})

    def test_330_preserves_fixed_and_selective_multiplicity(self) -> None:
        page = parse_quest_item_page(
            (FIXTURES / "330.html").read_bytes(), entity_id=330
        )
        self.assertEqual(len(page.mentions), 3)
        self.assertEqual(
            [row.section_kind for row in page.mentions],
            ["fixed_reward", "selective_reward", "selective_reward"],
        )
        self.assertEqual(
            [row.ordinal for row in page.mentions],
            [1, 1, 2],
        )

    def test_parse_failure_is_explicit(self) -> None:
        page = parse_quest_item_page(b"<html><title>Missing</title></html>", entity_id=5)
        self.assertEqual(page.parse_state, "parse_failed")
        self.assertEqual(page.mentions, ())

    def test_use_item_to_accept_quest_is_a_requirement(self) -> None:
        payload = b"""<html><head><title>Fixture - Quest - ArcheRage Wiki</title></head>
        <body><div>ID: 9</div><div class='mb-2'><p>Start</p>
        <div class='mb-2 ml-2'><div class='mb-1'><div>Use item to accept quest</div></div>
        <div class='mb-1 ml-2'><a href='/na-en/db/items/77'>1 Request</a></div>
        </div></div></body></html>"""
        page = parse_quest_item_page(payload, entity_id=9)
        self.assertEqual(page.mentions[0].section_kind, "requirement_item")

    def test_summon_level_item_is_an_objective(self) -> None:
        payload = b"""<html><head><title>Fixture - Quest - ArcheRage Wiki</title></head>
        <body><div>ID: 10</div><div class='mb-2'><p>Progress</p>
        <div class='mb-2 ml-2'><div class='mb-1'><div>Summon achieves level</div></div>
        <div class='mb-1 ml-2'><a href='/na-en/db/items/78'>1 Stormdarter</a></div>
        </div></div></body></html>"""
        page = parse_quest_item_page(payload, entity_id=10)
        self.assertEqual(page.mentions[0].section_kind, "objective_item")

    def test_2260_preserves_complete_visible_multiplicity(self) -> None:
        page = parse_quest_item_page(
            (FIXTURES / "2260.html").read_bytes(), entity_id=2260
        )
        self.assertEqual(
            [(row.item_id, row.visible_count, row.section_kind) for row in page.mentions],
            [
                (16260, 1, "quest_item"),
                (23633, 1, "fixed_reward"),
                (47985, 1, "selective_reward"),
                (47986, 1, "selective_reward"),
                (47987, 1, "selective_reward"),
                (54334, 2, "fixed_reward"),
            ],
        )


class NativeGrantTests(unittest.TestCase):
    def test_join_four_types_and_preserve_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stage40.sqlite"
            _native_db(path)
            extraction = extract_native_grants(path)
        self.assertEqual(len(extraction.grants), 4)
        self.assertEqual(
            {row["selection_mode"] for row in extraction.grants},
            {"fixed", "selective", "ranked", "result_ranked"},
        )
        self.assertEqual(extraction.quest_ids, (1,))
        self.assertEqual(len(extraction.orphans), 1)
        self.assertEqual(extraction.orphans[0]["act_detail_id"], 999)
        self.assertEqual(
            next(
                row["result"]
                for row in extraction.grants
                if row["selection_mode"] == "result_ranked"
            ),
            0,
        )

    def test_generation_inputs_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stage40.sqlite"
            _native_db(path)
            first = extract_native_grants(path)
            second = extract_native_grants(path)
        self.assertEqual(first, second)


class AcquisitionStateTests(unittest.TestCase):
    def test_cache_manifest_is_deterministic_and_identity_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "stage70-wiki-cache"
            cache = root / "detail" / "na-en" / "quests"
            cache.mkdir(parents=True)
            config = SimpleNamespace(stage_70_wiki_cache=root, wiki_locale="na-en")
            payload = b"<html><title>Quest - Quest - ArcheRage Wiki</title><body>ID: 1</body></html>"
            _write_snapshot(
                cache,
                quest_id=1,
                canonical_url="https://example/na-en/db/quests/1",
                status_code=200,
                payload=payload,
                content_type="text/html",
                final_url="https://example/na-en/db/quests/1",
                locale="na-en",
                error=None,
            )
            first = build_quest_item_cache_manifest(config, [1])
            first_bytes = (cache / "snapshot-manifest.json").read_bytes()
            second = build_quest_item_cache_manifest(config, [1])
            second_bytes = (cache / "snapshot-manifest.json").read_bytes()
            self.assertEqual(first, second)
            self.assertEqual(first_bytes, second_bytes)
            self.assertTrue(_snapshot_valid(cache, 1))
            metadata_path = _snapshot_paths(cache, 1)[1]
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["entity_id"] = 2
            metadata_path.write_text(canonical_json(metadata, pretty=True), encoding="utf-8")
            self.assertFalse(_snapshot_valid(cache, 1))

    def test_404_410_transient_and_parse_failure_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            cases = (
                (1, 404, b"missing", "permanent_missing"),
                (2, 410, b"gone", "permanent_missing"),
                (3, 503, b"retry", "transient_error"),
                (4, 200, b"<html><title>bad</title></html>", "parse_failed"),
            )
            for quest_id, status, payload, expected in cases:
                metadata = _write_snapshot(
                    cache,
                    quest_id=quest_id,
                    canonical_url=f"https://example/quests/{quest_id}",
                    status_code=status,
                    payload=payload,
                    content_type="text/html",
                    final_url=f"https://example/quests/{quest_id}",
                    locale="na-en",
                    error=None,
                )
                self.assertEqual(metadata["page_state"], expected)
                self.assertTrue(_snapshot_paths(cache, quest_id)[1].is_file())

    def test_client_retries_transient_without_sleeping_for_fixture(self) -> None:
        calls = []

        def fetcher(url: str):
            calls.append(url)
            return (503, b"retry", "text/plain", url)

        client = QuestWikiClient(
            base_url="https://example", requested_delay=1.0, fetcher=fetcher
        )
        status, _, _, _, _ = client.fetch("https://example/quest")
        self.assertEqual(status, 503)
        self.assertEqual(len(calls), 3)


class ComparisonTests(unittest.TestCase):
    @staticmethod
    def _grant(key: str, *, count: int = 1, mode: str = "fixed") -> dict[str, object]:
        return {
            "grant_key": key,
            "quest_id": 1,
            "item_id": 10,
            "grant_phase": "reward",
            "selection_mode": mode,
            "count": count,
        }

    @staticmethod
    def _mention(
        key: str, *, count: int | None = 1, section: str = "fixed_reward"
    ) -> dict[str, object]:
        return {
            "mention_key": key,
            "quest_id": 1,
            "item_id": 10,
            "visible_count": count,
            "section_kind": section,
        }

    def test_match_and_conflicts(self) -> None:
        pages = [{"quest_id": 1, "page_state": "confirmed", "detail_present": 1}]
        cases = (
            (self._grant("g1"), self._mention("m1"), "match"),
            (self._grant("g2", count=2), self._mention("m2", count=1), "count_conflict"),
            (self._grant("g3"), self._mention("m3", section="selective_reward"), "role_conflict"),
        )
        for grant, mention, expected in cases:
            rows = _comparison_rows([grant], [mention], pages)
            self.assertEqual(rows[0]["overall_state"], expected)

    def test_native_only_wiki_only_and_ambiguous(self) -> None:
        pages = [{"quest_id": 1, "page_state": "confirmed", "detail_present": 1}]
        native_only = _comparison_rows([self._grant("g1")], [], pages)
        self.assertEqual(native_only[0]["overall_state"], "native_only")
        wiki_only = _comparison_rows([], [self._mention("m1")], pages)
        self.assertEqual(wiki_only[0]["overall_state"], "wiki_only")
        ambiguous = _comparison_rows(
            [self._grant("g1"), self._grant("g2")],
            [self._mention("m1"), self._mention("m2")],
            pages,
        )
        self.assertEqual(
            {row["overall_state"] for row in ambiguous},
            {"ambiguous_many_to_many"},
        )


class SchemaTests(unittest.TestCase):
    def test_required_tables_and_indexes_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "crosswalk.sqlite3"
            connection = _create_database(path)
            objects = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
                )
            }
            connection.close()
        self.assertTrue(
            {
                "quest_item_grants",
                "orphan_grant_details",
                "wiki_quest_pages",
                "wiki_quest_item_mentions",
                "item_closure",
                "quest_item_comparisons",
                "idx_grants_quest_phase",
                "idx_mentions_quest_section",
                "idx_closure_state",
            }.issubset(objects)
        )

    def test_item_closure_uses_native_graph_without_wiki_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stage_path = Path(temporary) / "stage20.sqlite"
            consolidated_path = Path(temporary) / "all.sqlite"
            for path in (stage_path, consolidated_path):
                connection = sqlite3.connect(path)
                connection.executescript(
                    """
                    CREATE TABLE entities(
                        entity_key TEXT PRIMARY KEY,kind TEXT,native_id TEXT,
                        subtype TEXT,lifecycle TEXT,state TEXT,authority TEXT,
                        source_stage INTEGER,provenance TEXT,evidence_json TEXT
                    );
                    CREATE TABLE entity_properties(
                        property_key TEXT,entity_key TEXT,namespace TEXT,
                        property_name TEXT,ordinal INTEGER,value_type TEXT,
                        value_text TEXT,value_integer INTEGER,value_real REAL,
                        value_boolean INTEGER,value_json TEXT,state TEXT,
                        authority TEXT,source_artifact_key TEXT,locator TEXT,
                        consumer TEXT,evidence_json TEXT
                    );
                    CREATE TABLE coverage(
                        coverage_key TEXT,scope_key TEXT,dimension TEXT,state TEXT,
                        capability TEXT,authority TEXT,provenance TEXT,evidence_json TEXT
                    );
                    CREATE TABLE relations(
                        relation_key TEXT,src_entity_key TEXT,relation TEXT,
                        dst_entity_key TEXT,ordinal INTEGER,cardinality TEXT,
                        state TEXT,required INTEGER,authority TEXT,
                        source_artifact_key TEXT,locator TEXT,loader_or_consumer TEXT,
                        provenance TEXT,evidence_json TEXT
                    );
                    CREATE TABLE gaps(
                        gap_key TEXT,entity_key TEXT,dimension TEXT,state TEXT,
                        severity INTEGER,blocker_code TEXT,reason TEXT,
                        required_evidence TEXT,provenance TEXT
                    );
                    CREATE TABLE blocker_roots(
                        blocker_root_key TEXT,root_code TEXT,category TEXT,state TEXT,
                        disposition TEXT,priority_score INTEGER,recommended_action TEXT
                    );
                    CREATE TABLE blocker_impacts(
                        blocker_impact_key TEXT,blocker_root_key TEXT,subject_kind TEXT,
                        subject_key TEXT,entity_key TEXT,state TEXT,impact_count INTEGER,
                        evidence_json TEXT
                    );
                    """
                )
                connection.commit()
                connection.close()
            stage = sqlite3.connect(stage_path)
            stage.execute(
                "INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    "item:1",
                    "item",
                    "1",
                    "generic",
                    "present",
                    "confirmed",
                    "client_native",
                    20,
                    "fixture",
                    "{}",
                ),
            )
            stage.execute(
                "INSERT INTO coverage VALUES(?,?,?,?,?,?,?,?)",
                (
                    "c1",
                    "item:1",
                    "dependency_closure",
                    "confirmed",
                    "native closure",
                    "client_native",
                    "fixture",
                    "{}",
                ),
            )
            stage.commit()
            stage.close()
            stage_ro = sqlite3.connect(stage_path)
            stage_ro.row_factory = sqlite3.Row
            all_ro = sqlite3.connect(consolidated_path)
            all_ro.row_factory = sqlite3.Row
            row = _item_closure_row(stage_ro, all_ro, 1)
            stage_ro.close()
            all_ro.close()
            consolidated = sqlite3.connect(consolidated_path)
            consolidated.execute(
                "INSERT INTO entities VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    "item:1",
                    "item",
                    "1",
                    "generic",
                    "present",
                    "confirmed",
                    "client_native",
                    20,
                    "fixture",
                    "{}",
                ),
            )
            consolidated.execute(
                "INSERT INTO coverage VALUES(?,?,?,?,?,?,?,?)",
                (
                    "c2",
                    "item:1",
                    "dependency_closure",
                    "blocked",
                    "later-stage blocker",
                    "client_native",
                    "fixture",
                    "{}",
                ),
            )
            consolidated.commit()
            consolidated.close()
            stage_ro = sqlite3.connect(stage_path)
            stage_ro.row_factory = sqlite3.Row
            all_ro = sqlite3.connect(consolidated_path)
            all_ro.row_factory = sqlite3.Row
            enriched_row = _item_closure_row(stage_ro, all_ro, 1)
            stage_ro.close()
            all_ro.close()
        self.assertEqual(row["native_state"], "confirmed")
        self.assertEqual(row["closure_state"], "generic_dependency_free_candidate")
        self.assertNotIn("wiki", canonical_json(row))
        self.assertEqual(enriched_row["native_state"], "confirmed")
        self.assertEqual(enriched_row["closure_state"], "blocked")
        self.assertTrue(enriched_row["evidence"]["stage20_present"])
        self.assertTrue(enriched_row["evidence"]["consolidated_present"])


if __name__ == "__main__":
    unittest.main()
