import argparse
import hashlib
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from reconstruccion_npcs_quests_8.build_runtime_quest_knowledge import build


class RuntimeQuestKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.observations = root / "observations.sqlite3"
        self.compact = root / "compact.sqlite3"
        self.graph = root / "graph.sqlite3"
        self._create_observations()
        self._create_compact()
        self._create_graph()

    def tearDown(self):
        self.temp.cleanup()

    def _create_observations(self):
        with closing(sqlite3.connect(self.observations)) as db:
            db.execute(
                """CREATE TABLE observation_events(
                event_id TEXT,session_id TEXT,interaction_id TEXT,captured_utc TEXT,
                phase TEXT,status TEXT,operation TEXT,quest_id INTEGER,
                component_id INTEGER,act_type TEXT,detail_id INTEGER,
                dependency_kind TEXT,dependency_id INTEGER,expected_json TEXT,
                actual_json TEXT,blocker_code TEXT,exception_summary TEXT)"""
            )
            db.execute(
                """INSERT INTO observation_events VALUES(
                'e1','s1','i1','2026-01-01T00:00:00Z','supply','blocked',
                'materialize_quest_item',2255,1,'QuestActSupplyItem',10,
                'item',16280,'{}','{}','item_coverage_PhaseACandidate',NULL)"""
            )
            db.commit()

    def _create_compact(self):
        with closing(sqlite3.connect(self.compact)) as db:
            db.execute(
                """CREATE TABLE aaemu_native_quest_runtime_catalog(
                quest_id INTEGER,state TEXT,reasons_json TEXT,act_types_json TEXT,
                item_ids_json TEXT,npc_ids_json TEXT,doodad_ids_json TEXT,
                authority TEXT)"""
            )
            db.executemany(
                "INSERT INTO aaemu_native_quest_runtime_catalog VALUES(?,?,?,?,?,?,?,?)",
                [
                    (
                        2255,
                        "validated_override",
                        "[]",
                        '["QuestActSupplyItem"]',
                        "[16280]",
                        "[]",
                        "[]",
                        "ArcheAge Kakao 8.0.3.12 r558734",
                    ),
                    (
                        9000,
                        "quarantined",
                        '["item_coverage"]',
                        '["QuestActSupplyItem"]',
                        "[16280]",
                        "[]",
                        "[]",
                        "ArcheAge Kakao 8.0.3.12 r558734",
                    ),
                ],
            )
            db.commit()

    def _create_graph(self):
        with closing(sqlite3.connect(self.graph)) as db:
            db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)")
            db.execute(
                "INSERT INTO metadata VALUES('client_build','Kakao 8.0.3.12 r558734')"
            )
            db.execute(
                """CREATE TABLE entities(
                entity_key TEXT PRIMARY KEY,kind TEXT,native_id TEXT,subtype TEXT)"""
            )
            db.execute(
                """CREATE TABLE relations(
                relation_key TEXT PRIMARY KEY,src_entity_key TEXT,relation TEXT,
                dst_entity_key TEXT,state TEXT,authority TEXT,provenance TEXT,
                locator TEXT)"""
            )
            db.execute(
                """CREATE TABLE native_rows(
                native_row_key TEXT PRIMARY KEY,entity_key TEXT,entity_kind TEXT,
                native_id TEXT,source_table TEXT,state TEXT,row_json TEXT,
                provenance TEXT,evidence_json TEXT)"""
            )
            for quest_id, suffix in [(2255, "a"), (9000, "b")]:
                entities = [
                    (f"quest:{quest_id}", "quest", str(quest_id), None),
                    (f"component:{suffix}", "quest_component", suffix, None),
                    (f"act:{suffix}", "quest_act", suffix, None),
                    (
                        f"detail:{suffix}",
                        "quest_act_detail",
                        f"quest_act_supply_items:{suffix}",
                        "quest_act_supply_items",
                    ),
                    ("item:16280", "item", "16280", "generic"),
                ]
                db.executemany(
                    "INSERT OR IGNORE INTO entities VALUES(?,?,?,?)", entities
                )
                relations = [
                    (
                        f"rq:{suffix}",
                        f"component:{suffix}",
                        "belongs_to_quest",
                        f"quest:{quest_id}",
                    ),
                    (
                        f"rc:{suffix}",
                        f"act:{suffix}",
                        "references_component",
                        f"component:{suffix}",
                    ),
                    (
                        f"rd:{suffix}",
                        f"act:{suffix}",
                        "uses_act_detail",
                        f"detail:{suffix}",
                    ),
                    (
                        f"ri:{suffix}",
                        f"detail:{suffix}",
                        "references_item",
                        "item:16280",
                    ),
                ]
                db.executemany(
                    """INSERT INTO relations VALUES(
                    ?,?,?,?,'confirmed','client_native','aa8-client-forensics',
                    'quest_act_supply_items.item_id')""",
                    relations,
                )
                native_rows = [
                    (
                        f"nr-component-{suffix}",
                        f"component:{suffix}",
                        "quest_component",
                        suffix,
                        "quest_components",
                        "confirmed",
                        (
                            '{"id":'
                            + str(100 + quest_id)
                            + ',"quest_context_id":'
                            + str(quest_id)
                            + "}"
                        ),
                        "aa8-client-forensics",
                        "{}",
                    ),
                    (
                        f"nr-act-{suffix}",
                        f"act:{suffix}",
                        "quest_act",
                        suffix,
                        "quest_acts",
                        "confirmed",
                        (
                            '{"id":1,"quest_component_id":'
                            + str(100 + quest_id)
                            + ',"act_detail_id":'
                            + str(200 + quest_id)
                            + ',"act_detail_type":"QuestActSupplyItem"}'
                        ),
                        "aa8-client-forensics",
                        "{}",
                    ),
                    (
                        f"nr-detail-{suffix}",
                        f"detail:{suffix}",
                        "quest_act_detail",
                        f"quest_act_supply_items:{200 + quest_id}",
                        "quest_act_supply_items",
                        "confirmed",
                        (
                            '{"id":'
                            + str(200 + quest_id)
                            + ',"item_id":16280,"count":1,"grade_id":0}'
                        ),
                        "aa8-client-forensics",
                        "{}",
                    ),
                ]
                db.executemany(
                    "INSERT INTO native_rows VALUES(?,?,?,?,?,?,?,?,?)",
                    native_rows,
                )
            db.commit()

    def test_build_is_deterministic_and_preserves_authority_boundary(self):
        root = Path(self.temp.name)
        hashes = []
        for name in ("out1", "out2"):
            output = root / name
            build(
                argparse.Namespace(
                    observations=str(self.observations),
                    compact=str(self.compact),
                    forensic_graph=str(self.graph),
                    output=str(output),
                )
            )
            data = (output / "aa8-runtime-knowledge-v1.sqlite3").read_bytes()
            hashes.append(hashlib.sha256(data).hexdigest())
            with closing(
                sqlite3.connect(output / "aa8-runtime-knowledge-v1.sqlite3")
            ) as db:
                self.assertEqual(
                    db.execute(
                        """SELECT affected_native_quests
                        FROM capability_families
                        WHERE family_key='quest_act:QuestActSupplyItem'"""
                    ).fetchone()[0],
                    2,
                )
                self.assertEqual(
                    db.execute(
                        """SELECT value FROM knowledge_metadata
                        WHERE key='authority_boundary'"""
                    ).fetchone()[0],
                    "observed_runtime_only_not_native_authority",
                )
        self.assertEqual(hashes[0], hashes[1])


if __name__ == "__main__":
    unittest.main()
