from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from client_forensics.closure import (
    DOSSIER_FORMAT,
    _readiness,
    build_reconstruction_dossier,
    default_dossier_paths,
    render_dossier_html,
    write_reconstruction_dossier,
)
from client_forensics.schema import create_database
from client_forensics.util import canonical_json


class ClosureDossierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = self.root / "fixture.sqlite"
        connection = create_database(self.database)
        try:
            connection.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    self._entity("quest:330", "quest", "330", 40),
                    self._entity(
                        "quest_component:1520", "quest_component", "1520", 40
                    ),
                    self._entity("quest_act:9874", "quest_act", "9874", 40),
                    self._entity(
                        "quest_act_detail:accept:1250",
                        "quest_act_detail",
                        "accept:1250",
                        40,
                        subtype="accept",
                    ),
                    self._entity("npc:3597", "npc", "3597", 30),
                    self._entity("model:10", "model", "10", 30),
                    self._entity("item:51185", "item", "51185", 20),
                    self._entity("skill:46956", "skill", "46956", 50),
                    self._entity(
                        "skill_effect_application:1",
                        "skill_effect_application",
                        "1",
                        50,
                    ),
                    self._entity("effect:900", "effect", "900", 50),
                    self._entity(
                        "effect_detail:open:900",
                        "effect_detail",
                        "open:900",
                        50,
                        subtype="open",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    self._relation(
                        "r1",
                        "quest_component:1520",
                        "belongs_to_quest",
                        "quest:330",
                    ),
                    self._relation(
                        "r2",
                        "quest_act:9874",
                        "references_component",
                        "quest_component:1520",
                    ),
                    self._relation(
                        "r3",
                        "quest_act:9874",
                        "uses_act_detail",
                        "quest_act_detail:accept:1250",
                    ),
                    self._relation(
                        "r4",
                        "quest_act_detail:accept:1250",
                        "references_npc",
                        "npc:3597",
                    ),
                    self._relation(
                        "r5",
                        "quest_act_detail:accept:1250",
                        "references_item",
                        "item:51185",
                    ),
                    self._relation("r6", "npc:3597", "uses_model", "model:10"),
                    self._relation(
                        "r7", "item:51185", "use_skill_id", "skill:46956"
                    ),
                    self._relation(
                        "r8",
                        "skill_effect_application:1",
                        "references_skill",
                        "skill:46956",
                    ),
                    self._relation(
                        "r9",
                        "skill_effect_application:1",
                        "references_effect",
                        "effect:900",
                    ),
                    self._relation(
                        "r10",
                        "effect:900",
                        "uses_concrete_effect",
                        "effect_detail:open:900",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO localizations(
                    localization_key,locale,text_value,entity_key,state,
                    source_artifact_key,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                [
                    (
                        "l1",
                        "en_us",
                        "Exciting News",
                        "quest:330",
                        "confirmed",
                        None,
                        canonical_json({"table": "quest_contexts", "column": "name"}),
                    ),
                    (
                        "l2",
                        "en_us",
                        "Explorer's Ranged Weapon Crate",
                        "item:51185",
                        "confirmed",
                        None,
                        canonical_json({"table": "items", "column": "name"}),
                    ),
                ],
            )
            connection.executemany(
                "INSERT INTO metadata(key,value) VALUES(?,?)",
                [
                    ("client_build", "fixture"),
                    ("tool_version", "fixture"),
                ],
            )
            connection.commit()
        finally:
            connection.close()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _entity(
        key: str,
        kind: str,
        native_id: str,
        stage: int,
        *,
        subtype: str | None = None,
    ) -> tuple[object, ...]:
        return (
            key,
            kind,
            native_id,
            subtype,
            "present",
            "confirmed",
            "client_native",
            stage,
            "fixture",
            "{}",
        )

    @staticmethod
    def _relation(
        key: str,
        source: str,
        relation: str,
        destination: str,
        *,
        state: str = "confirmed",
    ) -> tuple[object, ...]:
        return (
            key,
            source,
            relation,
            destination,
            0,
            None,
            state,
            1,
            "client_native",
            None,
            f"fixture:{key}",
            "fixture_loader",
            "fixture",
            "{}",
        )

    def test_quest_profile_traverses_reverse_ownership_and_dependencies(
        self,
    ) -> None:
        dossier = build_reconstruction_dossier(
            self.database, "quest", "330"
        )
        keys = {
            node["entity_key"]: node for node in dossier["graph"]["nodes"]
        }
        self.assertEqual(dossier["format"], DOSSIER_FORMAT)
        self.assertEqual(dossier["profile"]["name"], "quest")
        self.assertEqual(keys["quest:330"]["display_name"], "Exciting News")
        self.assertEqual(keys["quest_component:1520"]["depth"], 1)
        self.assertEqual(keys["quest_act:9874"]["depth"], 2)
        self.assertEqual(keys["quest_act_detail:accept:1250"]["depth"], 3)
        self.assertEqual(keys["item:51185"]["depth"], 4)
        self.assertEqual(keys["skill:46956"]["depth"], 5)
        self.assertEqual(keys["skill_effect_application:1"]["depth"], 6)
        self.assertEqual(keys["effect:900"]["depth"], 7)
        self.assertEqual(keys["effect_detail:open:900"]["depth"], 8)
        self.assertEqual(
            dossier["readiness"]["forensic"]["state"], "profile_complete"
        )
        self.assertEqual(
            dossier["readiness"]["reconstruction"]["state"],
            "runtime_audit_required",
        )

    def test_item_and_skill_profiles_reuse_the_same_engine(self) -> None:
        item = build_reconstruction_dossier(
            self.database, "item", "51185"
        )
        skill = build_reconstruction_dossier(
            self.database, "skill", "46956"
        )
        item_keys = {node["entity_key"] for node in item["graph"]["nodes"]}
        skill_keys = {node["entity_key"] for node in skill["graph"]["nodes"]}
        self.assertEqual(item["profile"]["name"], "item")
        self.assertEqual(skill["profile"]["name"], "skill")
        self.assertIn("effect:900", item_keys)
        self.assertIn("skill_effect_application:1", skill_keys)
        self.assertIn("effect_detail:open:900", skill_keys)
        self.assertIn("item:51185", skill_keys)

    def test_required_unknown_relation_blocks_forensic_readiness(self) -> None:
        connection = create_database(self.root / "blocked.sqlite")
        try:
            connection.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    self._entity("item:1", "item", "1", 20),
                    self._entity("skill:2", "skill", "2", 50),
                ],
            )
            connection.execute(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                self._relation(
                    "blocked-r1",
                    "item:1",
                    "use_skill_id",
                    "skill:2",
                    state="unknown",
                ),
            )
            connection.commit()
        finally:
            connection.close()
        dossier = build_reconstruction_dossier(
            self.root / "blocked.sqlite", "item", "1"
        )
        self.assertEqual(
            dossier["readiness"]["forensic"]["state"], "blocked"
        )
        self.assertEqual(
            dossier["readiness"]["reconstruction"]["state"],
            "blocked_by_native_evidence",
        )

    def test_json_and_html_exports_are_deterministic_and_self_contained(
        self,
    ) -> None:
        dossier = build_reconstruction_dossier(
            self.database, "quest", "330"
        )
        first_json, first_html = default_dossier_paths(
            self.root / "one", "quest", "330"
        )
        second_json, second_html = default_dossier_paths(
            self.root / "two", "quest", "330"
        )
        first = write_reconstruction_dossier(
            dossier, first_json, first_html
        )
        second = write_reconstruction_dossier(
            dossier, second_json, second_html
        )
        self.assertEqual(first["json"]["sha256"], second["json"]["sha256"])
        self.assertEqual(first["html"]["sha256"], second["html"]["sha256"])
        html = render_dossier_html(dossier)
        self.assertIn("quest:330", html)
        self.assertIn("Exciting News", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_visual_and_server_blockers_are_audits_not_native_issues(
        self,
    ) -> None:
        readiness = _readiness(
            [
                {
                    "entity_key": "item:1",
                    "kind": "item",
                    "state": "confirmed",
                    "path_importance": "root",
                    "gaps": [],
                }
            ],
            [],
            [],
            [
                {
                    "blocker_root_key": "asset",
                    "root_code": "asset_reference_relation_unknown:item",
                    "category": "asset_resolution",
                    "state": "unknown",
                    "disposition": "actionable",
                    "recommended_action": "resolve asset",
                    "impacts": [{"entity_key": "item:1"}],
                },
                {
                    "blocker_root_key": "server",
                    "root_code": "protocol_unknown:item",
                    "category": "downstream_server",
                    "state": "unknown",
                    "disposition": "downstream_out_of_scope",
                    "recommended_action": "audit runtime",
                    "impacts": [{"entity_key": "item:1"}],
                },
            ],
        )
        self.assertEqual(readiness["forensic"]["state"], "profile_complete")
        self.assertEqual(
            readiness["reconstruction"]["state"], "runtime_audit_required"
        )
        scopes = {
            audit["audit_scope"]
            for audit in readiness["reconstruction"]["audits"]
        }
        self.assertEqual(scopes, {"presentation", "runtime"})


if __name__ == "__main__":
    unittest.main()
