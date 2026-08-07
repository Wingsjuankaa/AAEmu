from __future__ import annotations

import sqlite3
import struct
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from client_forensics.config import load_config
from client_forensics.build import (
    ITEM_GRADE_DESCRIPTOR_SQL,
    ITEM_GRADE_ORDER_SQL,
    _import_native_code_evidence_links,
)
from client_forensics.cross_stage import (
    CrossStageResolver,
    relation_can_close_from_destination,
    relation_is_asset_corroboration,
)
from client_forensics.native_domains import (
    QUEST_DETAIL_LABELS,
    audit_quest_detail_parity,
    audit_scalar_domains,
    quest_detail_reference_counts,
)
from client_forensics.closure_frontier import (
    LOOT_QUERIES,
    audit_loot_native_result,
)
from client_forensics.item_grade_secondary import (
    ITEM_GRADE_BUFFS_SQL,
    ITEM_GRADE_SECONDARY_SPECS,
    audit_item_grade_secondary,
)
from client_forensics.item_endpoint_lifecycle import (
    reconcile_native_item_endpoints,
)
from client_forensics.buff_endpoint_lifecycle import (
    reconcile_native_buff_endpoints,
)
from client_forensics.craft_identity import (
    CRAFTS_DISABLED_ROWS,
    CRAFTS_ENABLED_ID_DIGEST,
    CRAFTS_ENABLED_ROWS,
    CRAFTS_HISTORICAL_ROWS,
    CRAFTS_NON_ENABLED_OBSERVED_IDS,
    CRAFTS_OBSERVED_ID_DIGEST,
    CRAFTS_OBSERVED_IDS,
    CRAFTS_TOTAL_ROWS,
    native_craft_identity_constraints,
    reconcile_native_craft_endpoints,
)
from client_forensics.craft_pack_lifecycle import (
    CRAFT_PACK_FRONTIER_DIGEST,
    CRAFT_PACK_ID_DIGEST,
    CRAFT_PACK_ROW_DIGEST,
    CRAFT_PACK_ROWS,
    CRAFT_PACK_TOMBSTONES,
    native_craft_pack_evidence,
    reconcile_native_craft_pack_endpoints,
)
from client_forensics.item_guide_lifecycle import (
    ITEM_GUIDE_ID_DIGEST,
    ITEM_GUIDE_ROWS,
    ITEM_GUIDE_TOMBSTONE_IDS,
    native_item_guide_evidence,
    reconcile_native_item_guide_endpoints,
)
from client_forensics.tag_lifecycle import (
    TAG_ID_DIGEST,
    TAG_ROWS,
    TAG_TOMBSTONE_IDS,
    native_tag_evidence,
    reconcile_native_tag_endpoints,
)
from client_forensics.npc_groups import (
    NPC_GROUP_DONE,
    NPC_GROUP_HEADER,
    NPC_GROUP_ID_DIGEST,
    NPC_GROUP_ROWS,
    NPC_GROUP_START,
    native_npc_group_identity_catalog,
)
from client_forensics.npc_endpoint_lifecycle import (
    NPCS_ID_DIGEST,
    NPCS_NATIVE_ROWS,
    native_npc_identity_catalog,
    reconcile_native_npc_endpoints,
)
from client_forensics.skill_endpoint_lifecycle import (
    reconcile_native_skill_endpoints,
)
from client_forensics.global_strings import (
    cached_string_signatures,
    string_cache_digest,
)
from client_forensics.assets60 import (
    asset_query_inventory,
    classify_asset,
    decode_string_prefix,
    lookup_path,
)
from client_forensics.schema import create_database
from client_forensics.stage90 import (
    ClosureBuilder,
    classify_gap,
    classify_opaque,
    owner_stage_for_kind,
)
from client_forensics.skills import (
    BUFFS_ID_DIGEST,
    BUFFS_NATIVE_ROWS,
    SKILLS_ID_DIGEST,
    SKILLS_NATIVE_ROWS,
    compare_skill_layouts,
    load_stage50_results,
    native_buff_identity_catalog,
    native_skill_identity_catalog,
    skill_query_inventory,
)
from client_forensics.quests import (
    _parse_loader_layouts,
    act_detail_table,
    compare_quest_layouts,
    decode_effect_fire_details,
    decode_quest_core,
    quest_act_detail_counts,
    quest_loader_inventory,
)
from client_forensics.quest_text_kinds import (
    QUEST_CONTEXT_TEXT_KIND_COUNTS,
    QUEST_CONTEXT_TEXT_KIND_LABELS,
    QUEST_NAME_KIND_COUNTS,
    QUEST_NAME_KIND_LABELS,
    audit_quest_text_kind_domains,
)
from client_forensics.quest_inline_semantics import (
    CHAT_BUBBLE_KIND_LABELS,
    QUEST_COMPONENT_TEXT_KIND_LABELS,
    audit_inline_quest_semantics,
)
from client_forensics.util import canonical_json, entity_key, stable_key, typed_value
from client_forensics.validate import validate_database
from client_forensics.wiki70 import parse_catalog_page
from client_forensics.world_actors import (
    CachedResultReader,
    audit_absent_appearance_results,
    decode_signed_modifier,
    face_profile_key_from_model_file,
    load_face_target_profiles,
)
from client_forensics.world_interactions import (
    WORLD_INTERACTION_INVALID_ID,
    WORLD_INTERACTION_LABELS,
    audit_world_interactions,
    parse_world_interaction_switch,
)


class CoreSchemaTests(unittest.TestCase):
    def test_keys_and_json_are_stable(self) -> None:
        self.assertEqual(entity_key("NPC", 123), "npc:123")
        self.assertEqual(
            stable_key("relation", "npc:1", "uses_model", "model:2"),
            stable_key("relation", "npc:1", "uses_model", "model:2"),
        )
        self.assertEqual(canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')

    def test_global_string_signatures_require_valid_utf8_and_digest_order(
        self,
    ) -> None:
        marker = b"\x01\xff\xff\xff\xff"
        payload = (
            b"noise"
            + marker
            + "첫째".encode("utf-8")
            + b"\0"
            + marker
            + b"\xff\0"
            + marker
            + b"second\0"
        )
        signatures = cached_string_signatures(payload)
        self.assertEqual(
            [(value.offset, value.value) for value in signatures],
            [(5, "첫째"), (24, "second")],
        )
        self.assertEqual(
            string_cache_digest({0: "첫째", 1: "second"}, 2),
            "A9D969F84AC11A7AA1661E09DFFC32739CA0900E9C5F2D03A023F9C4680CD9B8",
        )
        with self.assertRaises(ValueError):
            string_cache_digest({0: "first", 2: "third"}, 3)

    def test_native_item_endpoint_lifecycle_closes_present_and_tombstone(
        self,
    ) -> None:
        source = sqlite3.connect(":memory:")
        source.row_factory = sqlite3.Row
        source.executescript(
            """
            CREATE TABLE query_specs(
                query_spec_id INTEGER PRIMARY KEY,
                table_name TEXT,
                sql_text TEXT
            );
            CREATE TABLE cached_results(
                cached_result_id INTEGER PRIMARY KEY,
                query_spec_id INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                row_count INTEGER,
                row_digest TEXT,
                status TEXT,
                error TEXT
            );
            CREATE TABLE items(item_id INTEGER PRIMARY KEY);
            INSERT INTO query_specs VALUES(
                117,'items','SELECT id FROM items'
            );
            INSERT INTO cached_results VALUES(
                117,117,80917979,89076696,21420,'fixture','confirmed',NULL
            );
            """
        )
        source.executemany(
            "INSERT INTO items(item_id) VALUES(?)",
            [(value,) for value in range(1, 21_420)],
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "item-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "source:item-forensics-database",
                    20,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "derived_forensic",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "craft:1",
                        "craft",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "craft:2",
                        "craft",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "item:1",
                        "item",
                        "1",
                        None,
                        "referenced",
                        "unknown",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "item:50000",
                        "item",
                        "50000",
                        None,
                        "unknown",
                        "missing",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:1",
                        "craft:1",
                        "material_item_id",
                        "item:1",
                        0,
                        "one",
                        "unknown",
                        1,
                        "client_native",
                        "source:item-forensics-database",
                        "craft:1.item_id",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                    (
                        "relation:2",
                        "craft:2",
                        "material_item_id",
                        "item:50000",
                        0,
                        "one",
                        "missing",
                        1,
                        "client_reference",
                        "source:item-forensics-database",
                        "craft:2.item_id",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "gap:1",
                        "item:1",
                        "identity",
                        "unknown",
                        3,
                        "referenced_endpoint_not_in_prior_stages",
                        "fixture",
                        "catalog",
                        "aa8-client-forensics",
                    ),
                    (
                        "gap:2",
                        "item:50000",
                        "identity",
                        "missing",
                        3,
                        "referenced_endpoint_not_in_prior_stages",
                        "fixture",
                        "catalog",
                        "aa8-client-forensics",
                    ),
                ],
            )
            summary = reconcile_native_item_endpoints(
                destination,
                source,
                stage=20,
                source_artifact_key="source:item-forensics-database",
                expected={
                    "relations": 2,
                    "endpoints": 2,
                    "present": 1,
                    "tombstone": 1,
                },
            )
            entity_rows = [
                tuple(row)
                for row in destination.execute(
                    """
                    SELECT native_id,lifecycle,state
                    FROM entities WHERE kind='item' ORDER BY native_id
                    """
                )
            ]
            relation_states = [
                tuple(row)
                for row in destination.execute(
                    "SELECT DISTINCT state FROM relations"
                )
            ]
            remaining_gaps = destination.execute(
                "SELECT COUNT(*) FROM gaps"
            ).fetchone()[0]
            destination.close()
            self.assertEqual(summary["superseded_gaps"], 2)
            self.assertEqual(
                entity_rows,
                [
                    ("1", "present", "confirmed"),
                    ("50000", "tombstone", "tombstone"),
                ],
            )
            self.assertEqual(
                relation_states,
                [("confirmed",)],
            )
            self.assertEqual(remaining_gaps, 0)
        source.close()

    def test_native_skill_identity_catalog_is_complete_and_unfiltered(
        self,
    ) -> None:
        config = load_config()
        active_ids, evidence = native_skill_identity_catalog(config)
        self.assertEqual(len(active_ids), SKILLS_NATIVE_ROWS)
        self.assertEqual(min(active_ids), 10_202)
        self.assertEqual(max(active_ids), 49_202)
        self.assertEqual(evidence["identity_digest"], SKILLS_ID_DIGEST)
        self.assertTrue(evidence["unfiltered_positive_scope"])
        self.assertEqual(
            evidence["range"],
            {
                "raw_start": 22_360_912,
                "start": 22_361_437,
                "end": 42_803_022,
                "raw_rows": 33_467,
                "rows": 33_466,
                "discarded_leading_rows": 1,
            },
        )
        self.assertEqual(
            evidence["false_leading_structural_row"]["id"],
            1_734_438_241,
        )
        self.assertEqual(
            len(
                evidence["false_leading_structural_row"][
                    "invalid_boolean_columns"
                ]
            ),
            16,
        )
        self.assertTrue(evidence["architecture"]["x86"]["sql_task_present"])

    def test_native_buff_identity_catalog_is_complete_and_unfiltered(
        self,
    ) -> None:
        config = load_config()
        active_ids, evidence = native_buff_identity_catalog(config)
        self.assertEqual(len(active_ids), BUFFS_NATIVE_ROWS)
        self.assertEqual(min(active_ids), 1)
        self.assertEqual(max(active_ids), 31_308)
        self.assertEqual(evidence["identity_digest"], BUFFS_ID_DIGEST)
        self.assertTrue(evidence["unfiltered_positive_scope"])
        self.assertEqual(
            evidence["range"],
            {
                "header": 44_170_889,
                "start": 44_170_895,
                "end": 64_403_064,
                "rows": 27_303,
            },
        )
        self.assertTrue(evidence["boundary"]["structural_header_exact"])
        self.assertEqual(
            evidence["unresolved_string_references"],
            {"occurrences": 23_060, "unique_indices": 8_442},
        )
        self.assertTrue(evidence["architecture"]["x86"]["sql_task_present"])

    def test_native_craft_identity_constraints_preserve_partition(
        self,
    ) -> None:
        config = load_config()
        enabled, referenced, observed, evidence = (
            native_craft_identity_constraints(config)
        )
        self.assertEqual(len(enabled), CRAFTS_ENABLED_ROWS)
        self.assertEqual(len(referenced), 11_946)
        self.assertEqual(len(observed), CRAFTS_OBSERVED_IDS)
        self.assertEqual(
            evidence["enabled"]["identity_digest"],
            CRAFTS_ENABLED_ID_DIGEST,
        )
        self.assertEqual(
            evidence["observed_universe"]["identity_digest"],
            CRAFTS_OBSERVED_ID_DIGEST,
        )
        self.assertEqual(
            evidence["observed_universe"]["non_enabled_ids"],
            CRAFTS_NON_ENABLED_OBSERVED_IDS,
        )
        self.assertEqual(
            evidence["partition"],
            {
                "current_disabled_rows": CRAFTS_DISABLED_ROWS,
                "enabled_rows": CRAFTS_ENABLED_ROWS,
                "historical_or_tombstone_identities": CRAFTS_HISTORICAL_ROWS,
                "physical_rows": CRAFTS_TOTAL_ROWS,
                "status": "identity_assignment_underdetermined",
            },
        )

    def test_craft_endpoint_constraints_confirm_edges_without_guessing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "craft-endpoints.sqlite"
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "item:1",
                        "item",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "item:2",
                        "item",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "craft:1",
                        "craft",
                        "1",
                        None,
                        "present",
                        "unknown",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "craft:2",
                        "craft",
                        "2",
                        None,
                        "present",
                        "unknown",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:craft:enabled",
                        "item:1",
                        "references_craft",
                        "craft:1",
                        0,
                        "one",
                        "missing",
                        1,
                        "client_reference",
                        None,
                        "fixture",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                    (
                        "relation:craft:unresolved",
                        "item:2",
                        "references_craft",
                        "craft:2",
                        0,
                        "one",
                        "unknown",
                        1,
                        "client_native",
                        None,
                        "fixture",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                ],
            )
            summary = reconcile_native_craft_endpoints(
                destination,
                enabled_ids=frozenset({1}),
                reference_ids=frozenset({1, 2}),
                observed_ids=frozenset({1, 2, 3}),
                catalog_evidence={"fixture": True},
                stage=20,
                source_artifact_key=None,
                materialize_observed_universe=True,
                expected={
                    "entities": 3,
                    "enabled": 1,
                    "disabled_or_tombstone": 2,
                    "relations": 2,
                    "relation_endpoints": 2,
                },
            )
            self.assertEqual(summary["relations"], 2)
            self.assertEqual(
                tuple(
                    destination.execute(
                        """
                        SELECT lifecycle,state FROM entities
                        WHERE entity_key='craft:2'
                        """
                    ).fetchone()
                ),
                ("disabled_or_tombstone", "unknown"),
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM relations WHERE state='confirmed'"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM opaque_regions"
                ).fetchone()[0],
                1,
            )
            destination.close()

    def test_native_npc_group_identity_projection_is_complete(
        self,
    ) -> None:
        rows, active_ids, evidence = native_npc_group_identity_catalog(
            load_config()
        )
        self.assertEqual(len(rows), NPC_GROUP_ROWS)
        self.assertEqual(len(active_ids), NPC_GROUP_ROWS)
        self.assertEqual(min(active_ids), 1)
        self.assertEqual(max(active_ids), 482)
        self.assertEqual(
            evidence["identity"]["digest"],
            NPC_GROUP_ID_DIGEST,
        )
        self.assertEqual(
            evidence["boundary"],
            {
                "advertised_rows": NPC_GROUP_ROWS,
                "call_index": 251,
                "header": NPC_GROUP_HEADER,
                "header_index": 216,
                "next_header": NPC_GROUP_DONE,
                "npc_anchor_call": 248,
                "npc_anchor_header_index": 213,
                "start": NPC_GROUP_START,
                "stride": 17,
            },
        )
        self.assertEqual(
            evidence["projection"]["secondary_field_semantics"],
            "opaque",
        )
        self.assertTrue(
            evidence["architecture"]["x86"]["sql_surface_present"]
        )

    def test_native_skill_endpoint_lifecycle_closes_edges_and_gaps(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "skill-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:game11",
                    50,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "client_native",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "npc:1",
                        "npc",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        30,
                        "fixture",
                        "{}",
                    ),
                    (
                        "npc:2",
                        "npc",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        30,
                        "fixture",
                        "{}",
                    ),
                    (
                        "skill:10202",
                        "skill",
                        "10202",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        30,
                        "fixture",
                        "{}",
                    ),
                    (
                        "skill:10001",
                        "skill",
                        "10001",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        30,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:skill:present",
                        "npc:1",
                        "uses_base_skill",
                        "skill:10202",
                        0,
                        "one",
                        "confirmed",
                        1,
                        "client_native",
                        "fixture:game11",
                        "npcs[1].base_skill_id",
                        "fixture",
                        "aa8-client-forensics",
                        "{}",
                    ),
                    (
                        "relation:skill:tombstone",
                        "npc:2",
                        "uses_base_skill",
                        "skill:10001",
                        0,
                        "one",
                        "unknown",
                        1,
                        "client_native",
                        "fixture:game11",
                        "npcs[2].base_skill_id",
                        "fixture",
                        "aa8-client-forensics",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "gap:skill:present",
                        "skill:10202",
                        "identity",
                        "unknown",
                        2,
                        "referenced_endpoint_not_in_prior_stages",
                        "fixture",
                        "catalog",
                        "fixture",
                    ),
                    (
                        "gap:skill:tombstone",
                        "skill:10001",
                        "identity",
                        "unknown",
                        2,
                        "referenced_endpoint_not_in_decoded_stages",
                        "fixture",
                        "catalog",
                        "fixture",
                    ),
                ],
            )
            summary = reconcile_native_skill_endpoints(
                destination,
                active_ids=frozenset({10_202}),
                catalog_evidence={
                    "identity_digest": "fixture",
                    "sql": "SELECT id FROM skills",
                },
                stage=30,
                source_artifact_key="fixture:game11",
                expected={
                    "relations": 2,
                    "endpoints": 2,
                    "present": 1,
                    "tombstone": 1,
                },
            )
            self.assertEqual(summary["superseded_gaps"], 2)
            self.assertEqual(
                [
                    tuple(row)
                    for row in destination.execute(
                        """
                        SELECT native_id,lifecycle,state FROM entities
                        WHERE kind='skill' ORDER BY native_id
                        """
                    )
                ],
                [
                    ("10001", "tombstone", "tombstone"),
                    ("10202", "present", "confirmed"),
                ],
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM relations WHERE state='confirmed'"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                destination.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
                0,
            )
            destination.close()

    def test_native_buff_endpoint_lifecycle_closes_edges_and_gaps(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "buff-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:game11",
                    50,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "client_native",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "skill:1",
                        "skill",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "skill:2",
                        "skill",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "buff:1",
                        "buff",
                        "1",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "buff:9",
                        "buff",
                        "9",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:buff:present",
                        "skill:1",
                        "applies_buff",
                        "buff:1",
                        0,
                        "one",
                        "unknown",
                        1,
                        "client_native",
                        "fixture:game11",
                        "skills[1].buff_id",
                        "fixture",
                        "aa8-client-forensics",
                        "{}",
                    ),
                    (
                        "relation:buff:tombstone",
                        "skill:2",
                        "applies_buff",
                        "buff:9",
                        0,
                        "one",
                        "missing",
                        1,
                        "client_native",
                        "fixture:game11",
                        "skills[2].buff_id",
                        "fixture",
                        "aa8-client-forensics",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "gap:buff:present",
                        "buff:1",
                        "identity",
                        "unknown",
                        2,
                        "referenced_endpoint_not_in_prior_stages",
                        "fixture",
                        "catalog",
                        "fixture",
                    ),
                    (
                        "gap:buff:tombstone",
                        "buff:9",
                        "identity",
                        "missing",
                        2,
                        "referenced_endpoint_not_in_decoded_stages",
                        "fixture",
                        "catalog",
                        "fixture",
                    ),
                ],
            )
            summary = reconcile_native_buff_endpoints(
                destination,
                active_ids=frozenset({1}),
                catalog_evidence={
                    "identity_digest": "fixture",
                    "sql": "SELECT id FROM buffs",
                },
                stage=50,
                source_artifact_key="fixture:game11",
                expected={
                    "relations": 2,
                    "endpoints": 2,
                    "present": 1,
                    "tombstone": 1,
                },
            )
            self.assertEqual(summary["superseded_gaps"], 2)
            self.assertEqual(
                [
                    tuple(row)
                    for row in destination.execute(
                        """
                        SELECT native_id,lifecycle,state FROM entities
                        WHERE kind='buff' ORDER BY native_id
                        """
                    )
                ],
                [
                    ("1", "present", "confirmed"),
                    ("9", "tombstone", "tombstone"),
                ],
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM relations WHERE state='confirmed'"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                destination.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
                0,
            )
            destination.close()

    def test_native_npc_identity_catalog_is_complete_and_unfiltered(
        self,
    ) -> None:
        active_ids, evidence = native_npc_identity_catalog(load_config())
        self.assertEqual(len(active_ids), NPCS_NATIVE_ROWS)
        self.assertEqual(min(active_ids), 1)
        self.assertEqual(max(active_ids), 21_626)
        self.assertEqual(evidence["identity_digest"], NPCS_ID_DIGEST)
        self.assertIsNone(evidence["native_filter"])
        self.assertTrue(evidence["identity_field"]["string_cache_independent"])
        self.assertEqual(
            evidence["row_digest"],
            "963767D30141EBC0CF87F1284D39E4754B2EEF005F4DB982C56B6E87BB27D704",
        )

    def test_native_npc_endpoint_lifecycle_closes_edges_and_gaps(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "npc-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:game11",
                    40,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "client_native",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "quest:1",
                        "quest",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        40,
                        "fixture",
                        "{}",
                    ),
                    (
                        "quest:2",
                        "quest",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        40,
                        "fixture",
                        "{}",
                    ),
                    (
                        "npc:1",
                        "npc",
                        "1",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        40,
                        "fixture",
                        "{}",
                    ),
                    (
                        "npc:9",
                        "npc",
                        "9",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        40,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:npc:present",
                        "quest:1",
                        "references_npc",
                        "npc:1",
                        0,
                        "one",
                        "missing",
                        1,
                        "client_reference",
                        "fixture:game11",
                        "quests[1].npc_id",
                        "fixture",
                        "x2game_confirmed",
                        "{}",
                    ),
                    (
                        "relation:npc:tombstone",
                        "quest:2",
                        "references_npc",
                        "npc:9",
                        0,
                        "one",
                        "unknown",
                        1,
                        "client_native",
                        "fixture:game11",
                        "quests[2].npc_id",
                        "fixture",
                        "aa8-client-forensics",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "gap:npc:present",
                        "npc:1",
                        "identity",
                        "missing",
                        2,
                        "referenced_endpoint_not_in_prior_stages",
                        "fixture",
                        "catalog",
                        "fixture",
                    ),
                    (
                        "gap:npc:tombstone",
                        "npc:9",
                        "identity",
                        "unknown",
                        2,
                        "referenced_endpoint_not_in_decoded_stages",
                        "fixture",
                        "catalog",
                        "fixture",
                    ),
                ],
            )
            summary = reconcile_native_npc_endpoints(
                destination,
                active_ids=frozenset({1}),
                catalog_evidence={
                    "identity_digest": "fixture",
                    "loader": "fixture",
                    "sql": "SELECT id FROM npcs",
                },
                stage=40,
                source_artifact_key="fixture:game11",
                expected={
                    "relations": 2,
                    "endpoints": 2,
                    "present": 1,
                    "tombstone": 1,
                },
            )
            self.assertEqual(summary["superseded_gaps"], 2)
            self.assertEqual(
                [
                    tuple(row)
                    for row in destination.execute(
                        """
                        SELECT native_id,lifecycle,state FROM entities
                        WHERE kind='npc' ORDER BY native_id
                        """
                    )
                ],
                [
                    ("1", "present", "confirmed"),
                    ("9", "tombstone", "tombstone"),
                ],
            )
            self.assertEqual(
                destination.execute(
                    """
                    SELECT COUNT(*) FROM relations
                    WHERE state='confirmed' AND authority='client_native'
                    """
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                destination.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
                0,
            )
            destination.close()

    def test_native_craft_pack_catalog_and_frontier_are_complete(
        self,
    ) -> None:
        config = load_config()
        source = sqlite3.connect(
            f"file:{config.source_item_database.resolve().as_posix()}?mode=ro",
            uri=True,
        )
        source.row_factory = sqlite3.Row
        try:
            active_ids, evidence = native_craft_pack_evidence(source)
        finally:
            source.close()
        self.assertEqual(len(active_ids), CRAFT_PACK_ROWS)
        self.assertEqual(len(active_ids), 466)
        self.assertEqual(min(active_ids), 1)
        self.assertEqual(max(active_ids), 549)
        self.assertEqual(
            evidence["active_identity_digest"],
            CRAFT_PACK_ID_DIGEST,
        )
        self.assertEqual(
            evidence["queries"]["craft_packs"]["row_digest"],
            CRAFT_PACK_ROW_DIGEST,
        )
        self.assertEqual(
            evidence["frontier"]["endpoint_digest"],
            CRAFT_PACK_FRONTIER_DIGEST,
        )
        self.assertEqual(
            evidence["frontier"]["tombstones"],
            CRAFT_PACK_TOMBSTONES,
        )
        self.assertTrue(
            evidence["queries"]["craft_packs"]["x86_x64_layout_parity"]
        )

    def test_native_craft_pack_lifecycle_closes_edges(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "craft-pack-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:game11",
                    20,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "client_native",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "craft:1",
                        "craft",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "craft:2",
                        "craft",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "craft_pack:1",
                        "craft_pack",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "craft_pack:9",
                        "craft_pack",
                        "9",
                        None,
                        "unknown",
                        "missing",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:craft-pack:present",
                        "craft:1",
                        "member_of_craft_pack",
                        "craft_pack:1",
                        0,
                        "one",
                        "confirmed",
                        0,
                        "client_native",
                        "fixture:game11",
                        "fixture",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                    (
                        "relation:craft-pack:tombstone",
                        "craft:2",
                        "member_of_craft_pack",
                        "craft_pack:9",
                        0,
                        "one",
                        "missing",
                        0,
                        "client_reference",
                        "fixture:game11",
                        "fixture",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                ],
            )
            summary = reconcile_native_craft_pack_endpoints(
                destination,
                active_ids=frozenset({1}),
                catalog_evidence={
                    "active_identity_digest": "fixture",
                    "queries": {
                        "craft_packs": {
                            "sql": "SELECT id FROM craft_packs",
                        }
                    },
                },
                stage=20,
                source_artifact_key="fixture:game11",
                expected={
                    "relations": 2,
                    "endpoints": 2,
                    "present": 1,
                    "tombstone": 1,
                },
            )
            self.assertEqual(summary["relations"], 2)
            self.assertEqual(
                [
                    tuple(row)
                    for row in destination.execute(
                        """
                        SELECT native_id,lifecycle,state FROM entities
                        WHERE kind='craft_pack' ORDER BY native_id
                        """
                    )
                ],
                [
                    ("1", "present", "confirmed"),
                    ("9", "tombstone", "tombstone"),
                ],
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM relations WHERE state='confirmed'"
                ).fetchone()[0],
                2,
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM coverage"
                ).fetchone()[0],
                6,
            )
            destination.close()

    def test_native_item_guide_catalog_and_frontier_are_complete(
        self,
    ) -> None:
        config = load_config()
        source = sqlite3.connect(
            f"file:{config.source_item_database.resolve().as_posix()}?mode=ro",
            uri=True,
        )
        source.row_factory = sqlite3.Row
        try:
            active_ids, evidence = native_item_guide_evidence(source, config)
        finally:
            source.close()
        self.assertEqual(len(active_ids), ITEM_GUIDE_ROWS)
        self.assertEqual(evidence["active_identity_digest"], ITEM_GUIDE_ID_DIGEST)
        self.assertEqual(evidence["frontier"]["relations"], 4_459)
        self.assertEqual(evidence["frontier"]["endpoints"], 386)
        self.assertEqual(
            evidence["frontier"]["tombstone_ids"],
            sorted(ITEM_GUIDE_TOMBSTONE_IDS),
        )
        self.assertTrue(evidence["ghidra"]["x86_x64_layout_parity"])
        self.assertTrue(evidence["ghidra"]["sqlite_done_guard_confirmed"])

    def test_native_item_guide_lifecycle_covers_complete_owner_universe(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "item-guide-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:game11",
                    20,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "client_native",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        f"item:{native_id}",
                        "item",
                        str(native_id),
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    )
                    for native_id in (10, 11)
                ]
                + [
                    (
                        "item_guide:1",
                        "item_guide",
                        "1",
                        "item_guide_elems",
                        "present",
                        "unknown",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "item_guide:2",
                        "item_guide",
                        "2",
                        "item_guides",
                        "present",
                        "confirmed",
                        "client_native",
                        20,
                        "fixture",
                        "{}",
                    ),
                    (
                        "item_guide:9",
                        "item_guide",
                        "9",
                        "item_guide_elems",
                        "unknown",
                        "missing",
                        "client_reference",
                        20,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:item-guide:present",
                        "item:10",
                        "listed_in_item_guide",
                        "item_guide:1",
                        0,
                        "one",
                        "confirmed",
                        0,
                        "client_native",
                        "fixture:game11",
                        "fixture",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                    (
                        "relation:item-guide:tombstone",
                        "item:11",
                        "listed_in_item_guide",
                        "item_guide:9",
                        0,
                        "one",
                        "missing",
                        0,
                        "client_reference",
                        "fixture:game11",
                        "fixture",
                        "fixture",
                        "game11_native",
                        "{}",
                    ),
                ],
            )
            summary = reconcile_native_item_guide_endpoints(
                destination,
                active_ids=frozenset({1, 2}),
                catalog_evidence={"active_identity_digest": "fixture"},
                stage=20,
                source_artifact_key="fixture:game11",
                expected={
                    "active": 2,
                    "active_without_incoming": 1,
                    "endpoints": 2,
                    "present_endpoints": 1,
                    "relations": 2,
                    "tombstones": 1,
                    "universe": 3,
                },
            )
            self.assertEqual(summary["universe"], 3)
            self.assertEqual(
                [
                    tuple(row)
                    for row in destination.execute(
                        """
                        SELECT native_id,lifecycle,state FROM entities
                        WHERE kind='item_guide' ORDER BY native_id
                        """
                    )
                ],
                [
                    ("1", "present", "confirmed"),
                    ("2", "present", "confirmed"),
                    ("9", "tombstone", "tombstone"),
                ],
            )
            self.assertEqual(
                destination.execute(
                    """
                    SELECT COUNT(*) FROM coverage
                    WHERE dimension='incoming_relations'
                      AND state='not_applicable'
                    """
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                destination.execute(
                    "SELECT COUNT(*) FROM coverage"
                ).fetchone()[0],
                9,
            )
            destination.close()

    def test_native_tag_catalog_has_exact_dual_loader_authority(
        self,
    ) -> None:
        config = load_config()
        source = sqlite3.connect(
            f"file:{config.source_item_database.resolve().as_posix()}?mode=ro",
            uri=True,
        )
        source.row_factory = sqlite3.Row
        try:
            active_ids, evidence = native_tag_evidence(source, config)
        finally:
            source.close()
        self.assertEqual(len(active_ids), TAG_ROWS)
        self.assertEqual(evidence["active_identity_digest"], TAG_ID_DIGEST)
        self.assertEqual(evidence["query"]["row_count"], 5_280)
        self.assertEqual(evidence["query"]["x64_loader"], "FUN_39969130")
        self.assertEqual(evidence["query"]["x86_loader"], "FUN_39b43210")
        self.assertTrue(evidence["ghidra"]["x86_x64_layout_parity"])
        self.assertTrue(evidence["ghidra"]["sqlite_done_guard_confirmed"])

    def test_native_tag_lifecycle_closes_reference_only_ids(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = create_database(
                Path(temporary) / "tag-endpoints.sqlite"
            )
            destination.execute(
                """
                INSERT INTO artifacts(
                    artifact_key,source_stage,role,path,bytes,sha256,build,
                    authority,state,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:game11",
                    50,
                    "fixture",
                    "fixture",
                    0,
                    None,
                    "fixture",
                    "client_native",
                    "confirmed",
                    "fixture",
                    "{}",
                ),
            )
            destination.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "skill:10",
                        "skill",
                        "10",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "skill:11",
                        "skill",
                        "11",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "tag:1",
                        "tag",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "tag:2",
                        "tag",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                    (
                        "tag:9",
                        "tag",
                        "9",
                        None,
                        "referenced",
                        "unknown",
                        "client_native",
                        50,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            destination.executemany(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,
                    ordinal,cardinality,state,required,authority,
                    source_artifact_key,locator,loader_or_consumer,
                    provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "relation:tag:present",
                        "skill:10",
                        "references_tag",
                        "tag:1",
                        0,
                        "one",
                        "confirmed",
                        0,
                        "client_native",
                        "fixture:game11",
                        "fixture",
                        "fixture",
                        "fixture",
                        "{}",
                    ),
                    (
                        "relation:tag:tombstone",
                        "skill:11",
                        "references_tag",
                        "tag:9",
                        0,
                        "one",
                        "unknown",
                        0,
                        "client_native",
                        "fixture:game11",
                        "fixture",
                        "fixture",
                        "fixture",
                        "{}",
                    ),
                ],
            )
            summary = reconcile_native_tag_endpoints(
                destination,
                active_ids=frozenset({1, 2}),
                catalog_evidence={"active_identity_digest": "fixture"},
                stage=50,
                source_artifact_key="fixture:game11",
                expected={
                    "active": 2,
                    "active_without_incoming": 1,
                    "endpoints": 2,
                    "present_endpoints": 1,
                    "relation_pairs": 2,
                    "relations": 2,
                    "tombstones": 1,
                    "universe": 3,
                },
                strict_native_digests=False,
            )
            self.assertEqual(summary["universe"], 3)
            self.assertEqual(
                [
                    tuple(row)
                    for row in destination.execute(
                        """
                        SELECT native_id,lifecycle,state FROM entities
                        WHERE kind='tag' ORDER BY native_id
                        """
                    )
                ],
                [
                    ("1", "present", "confirmed"),
                    ("2", "present", "confirmed"),
                    ("9", "tombstone", "tombstone"),
                ],
            )
            self.assertEqual(
                destination.execute(
                    """
                    SELECT COUNT(*) FROM coverage
                    WHERE dimension='incoming_relations'
                      AND state='not_applicable'
                    """
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                destination.execute("SELECT COUNT(*) FROM coverage").fetchone()[0],
                9,
            )
            destination.close()

    def test_typed_values_do_not_confuse_bool_and_integer(self) -> None:
        self.assertEqual(typed_value(True), ("boolean", None, None, None, 1, None))
        self.assertEqual(typed_value(1), ("integer", None, 1, None, None, None))
        self.assertEqual(
            typed_value({"b": 2, "a": 1}),
            ("json", None, None, None, None, '{"a":1,"b":2}'),
        )

    def test_canonical_schema_accepts_a_closed_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.sqlite"
            connection = create_database(path)
            connection.executemany(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,authority,
                    source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "npc:1",
                        "npc",
                        "1",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        30,
                        "fixture",
                        "{}",
                    ),
                    (
                        "model:2",
                        "model",
                        "2",
                        None,
                        "present",
                        "confirmed",
                        "client_native",
                        30,
                        "fixture",
                        "{}",
                    ),
                ],
            )
            connection.execute(
                """
                INSERT INTO relations(
                    relation_key,src_entity_key,relation,dst_entity_key,ordinal,
                    cardinality,state,required,authority,source_artifact_key,
                    locator,loader_or_consumer,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:relation:1",
                    "npc:1",
                    "uses_model",
                    "model:2",
                    0,
                    "one",
                    "confirmed",
                    1,
                    "client_native",
                    None,
                    "fixture",
                    "fixture_loader",
                    "fixture",
                    "{}",
                ),
            )
            connection.commit()
            connection.close()
            result = validate_database(path, consolidated=False)
            self.assertEqual(result["quick_check"], "ok")
            self.assertEqual(result["orphan_relation_sources"], 0)
            self.assertEqual(result["orphan_relation_destinations"], 0)

    def test_stage90_schema_and_authority_separation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.sqlite"
            connection = create_database(path)
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            connection.close()
            self.assertTrue(
                {
                    "blocker_roots",
                    "blocker_impacts",
                    "blocker_evidence",
                    "work_queue",
                    "native_code_evidence_links",
                }.issubset(tables)
            )

    def test_native_code_evidence_links_preserve_consumer_relationship(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            main_path = root / "main.sqlite"
            native_path = root / "native.sqlite"
            connection = create_database(main_path)
            connection.execute(
                """
                INSERT INTO consumers(
                    consumer_key,scope_key,consumer_kind,name,module,locator,
                    architecture,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    "consumer:fixture",
                    "fixture:scope",
                    "native_loader",
                    "Fixture",
                    "x2game.dll",
                    "FUN_39001000",
                    "x64",
                    "confirmed",
                    "{}",
                ),
            )
            native = sqlite3.connect(native_path)
            native.execute(
                """
                CREATE TABLE code_evidence_links(
                    evidence_link_key TEXT PRIMARY KEY,
                    function_key TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    source_locator TEXT NOT NULL,
                    state TEXT NOT NULL,
                    evidence_json TEXT NOT NULL
                )
                """
            )
            native.execute(
                """
                INSERT INTO code_evidence_links VALUES(?,?,?,?,?,?,?)
                """,
                (
                    "link:fixture",
                    "fn:x64:sha:00001000",
                    "fixture:scope",
                    "native_consumer",
                    "FUN_39001000",
                    "confirmed",
                    '{"consumer_key":"consumer:fixture"}',
                ),
            )
            native.commit()
            native.close()
            connection.execute(
                "ATTACH DATABASE ? AS stage_15",
                (native_path.as_posix(),),
            )
            imported = _import_native_code_evidence_links(
                connection,
                "stage_15",
            )
            row = connection.execute(
                """
                SELECT consumer_key,function_key,source_stage
                FROM native_code_evidence_links
                """
            ).fetchone()
            connection.close()
            self.assertEqual(imported, 1)
            self.assertEqual(row[0], "consumer:fixture")
            self.assertEqual(row[1], "fn:x64:sha:00001000")
            self.assertEqual(row[2], 15)
        self.assertEqual(
            classify_gap(
                "protocol_unknown",
                provenance="aa8-item-forensics",
                entity_kind="item",
            ),
            ("downstream_server", "downstream_out_of_scope"),
        )
        self.assertEqual(
            classify_gap(
                "referenced_endpoint_not_in_decoded_stages",
                provenance="aa8-client-forensics",
                entity_kind="skill",
            ),
            ("native_closure", "actionable"),
        )
        self.assertEqual(
            classify_opaque(
                "wiki_catalog_absence_not_http_absence",
                surface="wiki.catalog.items",
            ),
            ("wiki_corroboration", "corroborative_only"),
        )
        self.assertEqual(owner_stage_for_kind("quest"), 40)

    def test_cross_stage_resolver_preserves_source_gap_and_finds_strong_entity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "source.sqlite"
            stage_path = root / "stage.sqlite"
            source = create_database(source_path)
            source.execute(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "icon:42",
                    "icon",
                    "42",
                    None,
                    "referenced",
                    "unknown",
                    "client_native",
                    50,
                    "fixture",
                    "{}",
                ),
            )
            source.execute(
                """
                INSERT INTO gaps(
                    gap_key,entity_key,dimension,state,severity,blocker_code,
                    reason,required_evidence,provenance
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    "fixture:gap",
                    "icon:42",
                    "dependency_closure",
                    "unknown",
                    2,
                    "referenced_endpoint_not_in_decoded_stages",
                    "fixture",
                    "decode icon",
                    "aa8-client-forensics",
                ),
            )
            source.commit()
            stage = create_database(stage_path)
            stage.execute(
                """
                INSERT INTO entities(
                    entity_key,kind,native_id,subtype,lifecycle,state,
                    authority,source_stage,provenance,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "icon:42",
                    "icon",
                    "42",
                    None,
                    "present",
                    "confirmed",
                    "client_native",
                    60,
                    "fixture",
                    "{}",
                ),
            )
            stage.commit()
            stage.close()
            resolver = CrossStageResolver.from_stage_databases(
                source,
                [(60, stage_path)],
            )
            resolution = resolver.resolve("icon:42")
            self.assertIsNotNone(resolution)
            assert resolution is not None
            self.assertEqual(resolution.state, "confirmed")
            self.assertEqual(resolution.stages, (60,))
            self.assertEqual(
                source.execute("SELECT COUNT(*) FROM gaps").fetchone()[0],
                1,
            )
            source.close()

    def test_relation_reconciliation_separates_native_and_asset_evidence(
        self,
    ) -> None:
        self.assertTrue(
            relation_can_close_from_destination(
                authority="client_native",
                provenance="aa8-client-forensics",
            )
        )
        self.assertTrue(
            relation_can_close_from_destination(
                authority="client_reference",
                provenance="game11_native",
            )
        )
        self.assertFalse(
            relation_can_close_from_destination(
                authority="client_reference",
                provenance="gamepak_xml_extracted",
            )
        )
        self.assertTrue(
            relation_is_asset_corroboration(
                authority="client_reference",
                provenance="gamepak_xml_extracted",
            )
        )

    def test_loot_frontier_preserves_native_result_absence(self) -> None:
        audit = audit_loot_native_result(load_config())
        self.assertEqual(
            [query.table for query in LOOT_QUERIES],
            ["loot_packs", "loots"],
        )
        self.assertEqual(
            audit["compact_tables"],
            {"loot_packs": False, "loots": False},
        )
        self.assertEqual(
            audit["execution_sequence_hits"],
            {"loot_packs": False, "loots": False},
        )
        self.assertEqual(audit["x64_loader"], "FUN_398f70e0")
        self.assertEqual(audit["x86_loader"], "FUN_39a07180")
        self.assertTrue(audit["x86_layout_parity"])
        self.assertEqual(
            audit["x86_loader_sha256"],
            "21B806B5EBD0716DA1CDE4094880D1C16B98D24125284441F5B6492CD1EE1090",
        )
        self.assertFalse(
            any(
                candidate["loot_packs"]["rows"] > 0
                or candidate["loots"]["rows"] > 0
                for candidate in audit["consecutive_layout_candidates"]
            )
        )

    def test_item_grade_catalog_has_exact_dual_loader_authority(self) -> None:
        config = load_config()
        x64 = _parse_loader_layouts(config.source_ghidra_sql_loaders_64)
        self.assertEqual(
            x64[ITEM_GRADE_ORDER_SQL]["layout"],
            ("68",),
        )
        self.assertEqual(
            x64[ITEM_GRADE_ORDER_SQL]["loader"],
            "FUN_39893a10",
        )
        self.assertEqual(
            x64[ITEM_GRADE_DESCRIPTOR_SQL]["layout"],
            (
                "68",
                "78",
                "60",
                "68",
                "68",
                "78",
                "68",
                "68",
                "68",
                "60",
                "60",
                "60",
                "60",
                "60",
                "60",
                "60",
            ),
        )
        self.assertEqual(
            x64[ITEM_GRADE_DESCRIPTOR_SQL]["loader"],
            "FUN_39a365c0",
        )
        x86_order = config.source_ghidra_item_grade_order_x86.read_text(
            encoding="utf-8"
        )
        x86_descriptor = (
            config.source_ghidra_item_grade_descriptor_x86.read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("FUN_39968900", x86_order)
        self.assertIn(ITEM_GRADE_ORDER_SQL, x86_order)
        self.assertIn("FUN_39d2ec60", x86_descriptor)
        self.assertIn(ITEM_GRADE_DESCRIPTOR_SQL, x86_descriptor)
        self.assertEqual(x86_descriptor.count("(&local_14,"), 16)

    def test_item_grade_secondary_catalogs_have_exact_native_authority(
        self,
    ) -> None:
        audit = audit_item_grade_secondary(load_config())
        self.assertEqual(audit["tables"], 3)
        self.assertEqual(audit["rows"], 8_386)
        self.assertEqual(
            audit["item_grade_buff_zero_endpoint_rows"],
            64,
        )
        self.assertEqual(
            audit["item_grade_distribution_positive_weights"],
            143,
        )
        self.assertTrue(audit["x86_x64_layout_parity"])
        self.assertEqual(
            {
                spec.table: (
                    spec.call_index,
                    spec.header_index,
                    spec.start,
                    spec.done,
                    spec.rows,
                )
                for spec in ITEM_GRADE_SECONDARY_SPECS
            },
            {
                "item_grade_buffs": (
                    138,
                    114,
                    0x3F71DC4,
                    0x3F9C8EC,
                    8_328,
                ),
                "item_grade_skills": (
                    139,
                    115,
                    0x3F9C8F2,
                    0x3F9C97A,
                    8,
                ),
                "item_grade_distributions": (
                    145,
                    121,
                    0x46AFDF7,
                    0x46B0919,
                    50,
                ),
            },
        )

    def test_stage90_suppresses_equivalent_confirmed_query(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.sqlite"
            connection = create_database(path)
            common = (
                "item_grades",
                "fixture",
                ITEM_GRADE_DESCRIPTOR_SQL,
                canonical_json(["id"]),
                canonical_json(["68"]),
                "game11",
                100,
                13,
                canonical_json({}),
                "fixture_loader",
                canonical_json({}),
            )
            connection.executemany(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,
                    evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    ("stage10:query", 1, *common[:-1], "unknown", common[-1]),
                    ("stage20:query", 1, *common[:-1], "confirmed", common[-1]),
                ],
            )
            builder = ClosureBuilder(connection, resolver=None)  # type: ignore[arg-type]
            self.assertEqual(builder.add_queries(), 1)
            self.assertEqual(builder.roots, {})
            self.assertEqual(len(builder.superseded_queries), 1)
            self.assertEqual(
                builder.superseded_queries[0]["replacement_query_key"],
                "stage20:query",
            )
            connection.close()

    def test_stage90_splits_historical_query_association(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.sqlite"
            connection = create_database(path)
            descriptor_columns = canonical_json(
                ["id", "color_argb", "durability_value"]
            )
            descriptor_layout = canonical_json(["68", "78", "60"])
            rows = [
                (
                    "stage10:hybrid",
                    1,
                    "item_grades",
                    "fixture",
                    ITEM_GRADE_ORDER_SQL,
                    descriptor_columns,
                    descriptor_layout,
                    "game11",
                    None,
                    13,
                    canonical_json({}),
                    None,
                    "unknown",
                    canonical_json({}),
                ),
                (
                    "stage20:order",
                    2,
                    "item_grades",
                    "fixture",
                    ITEM_GRADE_ORDER_SQL,
                    canonical_json(["id"]),
                    canonical_json(["68"]),
                    None,
                    None,
                    13,
                    canonical_json({}),
                    "order_loader",
                    "confirmed",
                    canonical_json({}),
                ),
                (
                    "stage20:descriptor",
                    3,
                    "item_grades",
                    "fixture",
                    (
                        "SELECT id, color_argb, durability_value "
                        "FROM item_grades"
                    ),
                    descriptor_columns,
                    descriptor_layout,
                    "game11",
                    100,
                    13,
                    canonical_json({}),
                    "descriptor_loader",
                    "confirmed",
                    canonical_json({}),
                ),
            ]
            connection.executemany(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,
                    evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                rows,
            )
            builder = ClosureBuilder(connection, resolver=None)  # type: ignore[arg-type]
            self.assertEqual(builder.add_queries(), 1)
            self.assertEqual(builder.roots, {})
            self.assertEqual(
                builder.superseded_queries[0]["replacement_query_keys"],
                ["stage20:descriptor", "stage20:order"],
            )
            connection.close()

    def test_stage90_replaces_malformed_projection_with_native_result(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.sqlite"
            connection = create_database(path)
            connection.executemany(
                """
                INSERT INTO query_specs(
                    query_key,source_query_spec_id,table_name,source_module,
                    sql_text,columns_json,layout_json,stream_name,start_offset,
                    expected_rows,anchor_json,loader_consumer,state,
                    evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                [
                    (
                        "stage10:item-grade-buffs",
                        1,
                        "item_grade_buffs",
                        "fixture",
                        ITEM_GRADE_BUFFS_SQL,
                        canonical_json(
                            ["id", "buff_id", "item_grade_id", "item_id"]
                        ),
                        canonical_json(["68", "68", "68", "68"]),
                        "game11",
                        100,
                        103,
                        canonical_json({}),
                        None,
                        "unknown",
                        canonical_json({}),
                    ),
                    (
                        "stage20:item-grade-buffs",
                        2,
                        "item_grade_buffs",
                        "fixture",
                        ITEM_GRADE_BUFFS_SQL,
                        canonical_json(
                            [
                                "id",
                                "buff_id",
                                "item_grade_id",
                                "item_id",
                                "num_pieces",
                            ]
                        ),
                        canonical_json(["68", "68", "68", "68", "68"]),
                        "game11",
                        200,
                        8_328,
                        canonical_json({}),
                        "x64 loader; x86 loader",
                        "confirmed",
                        canonical_json({}),
                    ),
                ],
            )
            connection.execute(
                """
                INSERT INTO cached_results(
                    cached_result_key,source_cached_result_id,query_key,
                    artifact_key,start_offset,end_offset,row_count,row_digest,
                    raw_references_json,unresolved_references_json,
                    resolution_evidence_json,state,error
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "stage20:item-grade-buffs-result",
                    2,
                    "stage20:item-grade-buffs",
                    None,
                    200,
                    300,
                    8_328,
                    "fixture",
                    canonical_json([]),
                    canonical_json([]),
                    canonical_json({}),
                    "confirmed",
                    None,
                ),
            )
            builder = ClosureBuilder(
                connection,
                resolver=None,  # type: ignore[arg-type]
            )
            self.assertEqual(builder.add_queries(), 1)
            self.assertEqual(builder.roots, {})
            self.assertEqual(
                builder.superseded_queries[0]["replacement_query_keys"],
                ["stage20:item-grade-buffs"],
            )
            connection.close()

    def test_wiki_catalog_parser_keeps_typed_columns_and_entity_id(self) -> None:
        payload = b"""
        <table id="items-list"><thead><tr>
        <th data-data="id">ID</th><th data-data="icon">Icon</th>
        <th data-data="name">Name</th><th data-data="grade_name">Grade</th>
        </tr></thead><tbody><tr>
        <td><a href="/na-en/db/items/52816">52816</a></td>
        <td><img src="/static/images/icons/thistle.png"></td>
        <td><a href="/na-en/db/items/52816">Thistle</a></td>
        <td>Basic</td></tr></tbody></table>
        """
        rows = parse_catalog_page(payload, kind="items", locale="na-en")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].entity_id, 52816)
        self.assertEqual(rows[0].values["name"], "Thistle")
        self.assertEqual(rows[0].values["grade_name"], "Basic")
        self.assertEqual(
            rows[0].values["icon"],
            "/static/images/icons/thistle.png",
        )

    def test_world_actor_cached_result_primitives_and_string_cache(self) -> None:
        row = (
            bytes([100, 1])
            + struct.pack("<i", -2)
            + struct.pack("<d", 1.5)
            + bytes([0])
            + b"literal\x00"
            + bytes([2])
            + bytes([1])
            + struct.pack("<I", 0xFFFFFFFF)
            + b"cached\x00"
            + bytes([1])
            + struct.pack("<I", 10)
        )
        reader = CachedResultReader(row, first_string_reference=10)
        values, cursor = reader.row(0, ["38", "68", "60", "78", "78", "78", "78"])
        self.assertEqual(
            values,
            [1, -2, 1.5, "literal", None, "cached", "cached"],
        )
        self.assertEqual(cursor, len(row))
        self.assertEqual(reader.tokens["resolved_reference"], 1)

    def test_world_actor_cached_result_fixed_blob(self) -> None:
        blob = bytes(range(128))
        row = bytes([100]) + struct.pack("<I", len(blob)) + blob
        reader = CachedResultReader(row, first_string_reference=None)
        values, cursor = reader.row(0, ["blob:128"])
        self.assertEqual(cursor, len(row))
        self.assertEqual(values[0]["bytes"], 128)
        self.assertEqual(values[0]["value"], blob.hex().upper())
        self.assertEqual(len(values[0]["sha256"]), 64)

        invalid = bytes([100]) + struct.pack("<I", 127) + bytes(127)
        with self.assertRaises(ValueError):
            CachedResultReader(
                invalid, first_string_reference=None
            ).row(0, ["blob:128"])

    def test_custom_model_modifier_is_signed_int8_128(self) -> None:
        payload = bytes([0, 1, 127, 128, 156, 255]) + bytes(122)
        values = decode_signed_modifier(
            {
                "bytes": 128,
                "encoding": "hex",
                "value": payload.hex().upper(),
            }
        )
        self.assertEqual(len(values), 128)
        self.assertEqual(values[:6], (0, 1, 127, -128, -100, -1))

    def test_actor_model_path_selects_face_target_profile(self) -> None:
        self.assertEqual(
            face_profile_key_from_model_file(
                r"objects\Characters\nuian\male\nude\nu_m.cdf"
            ),
            "nuian/male",
        )
        self.assertIsNone(
            face_profile_key_from_model_file("objects/vehicles/car.cdf")
        )

    def test_configured_face_target_profiles_are_complete(self) -> None:
        profiles = load_face_target_profiles(load_config().source_gamepak_xml_root)
        self.assertEqual(len(profiles), 12)
        self.assertEqual(sum(len(value.targets) for value in profiles.values()), 966)
        self.assertEqual(
            {value.gender for value in profiles.values()},
            {"female", "male"},
        )

    def test_absent_appearance_audit_detects_an_exact_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row = bytes([100])
            row += b"".join(struct.pack("<i", value) for value in range(1, 10))
            row += bytes([0]) + b"material\x00"
            row += struct.pack("<i", 10)
            row += struct.pack("<d", 0.25)
            row += struct.pack("<i", 11)
            row += struct.pack("<d", 0.5)
            payload = (
                bytes([101, 100])
                + struct.pack("<I", 1)
                + row
                + bytes([101])
            )
            (root / "game0").write_bytes(payload)
            (root / "game1").write_bytes(b"")
            audit = audit_absent_appearance_results(root)
            result = audit["tables"]["customizing_item_asset_colors"]
            self.assertEqual(result["exact_layout_match_count"], 1)
            self.assertEqual(result["exact_layout_matches"][0]["rows"], 1)

    def test_quest_frontier_native_closure_and_architecture_parity(self) -> None:
        config = load_config()
        decoded = decode_quest_core(
            config.source_game11,
            config.source_ghidra_sql_loaders_64,
            config.source_ghidra_sql_call_sequence,
        )
        effect_fires = decode_effect_fire_details(
            config.source_game11,
            config.source_ghidra_sql_loaders_64,
        )
        closure = quest_act_detail_counts(decoded, effect_fires)
        parity = compare_quest_layouts(
            config.source_ghidra_sql_loaders_64,
            config.source_ghidra_quest_loaders_x86,
            config.source_ghidra_sql_call_sequence,
        )
        self.assertEqual(len(decoded), 125)
        self.assertEqual(sum(len(value.rows) for value in decoded.values()), 180730)
        self.assertEqual(len(effect_fires.rows), 143)
        self.assertEqual(closure["act_rows"], 42446)
        self.assertEqual(closure["detail_types"], 85)
        self.assertEqual(closure["missing"], {})
        self.assertEqual(parity["queries_compared"], 126)
        self.assertEqual(parity["mismatches"], [])
        self.assertTrue(
            all(
                not value.unresolved_references
                for value in decoded.values()
            )
        )
        inventory = quest_loader_inventory(config.source_ghidra_sql_loaders_64)
        scalar_domains = audit_scalar_domains(
            decoded,
            native_sql_tables={
                str(value["table"]) for value in inventory
            },
        )
        quest_detail = audit_quest_detail_parity(
            config.source_ghidra_enum_consumers_x64,
            config.source_ghidra_enum_consumers_x86,
        )
        detail_counts = quest_detail_reference_counts(decoded)
        text_kind_domains = audit_quest_text_kind_domains(
            decoded,
            native_sql_tables={
                str(value["table"]) for value in inventory
            },
            api_x64_path=config.source_ghidra_quest_scalar_api_x64,
            consumers_x64_path=(
                config.source_ghidra_quest_scalar_consumers_x64
            ),
            consumers_x86_path=(
                config.source_ghidra_quest_scalar_consumers_x86
            ),
        )
        inline_semantics = audit_inline_quest_semantics(
            decoded,
            enum_x64_path=config.source_ghidra_enum_consumers_x64,
            enum_x86_path=config.source_ghidra_enum_consumers_x86,
            component_context_x64_path=(
                config.source_ghidra_component_accessor_context_x64
            ),
            component_context_x86_path=(
                config.source_ghidra_component_accessor_context_x86
            ),
            component_copy_x64_path=(
                config.source_ghidra_quest_component_struct_x64
            ),
            component_copy_x86_path=(
                config.source_ghidra_quest_component_copy_x86
            ),
            npc_ai_field_trace_x64_path=(
                config.source_ghidra_npc_ai_field_trace_x64
            ),
            npc_ai_field_trace_x86_path=(
                config.source_ghidra_npc_ai_field_trace_x86
            ),
            npc_ai_forwarded_helpers_x64_path=(
                config.source_ghidra_npc_ai_forwarded_helpers_x64
            ),
            npc_ai_forwarded_helpers_x86_path=(
                config.source_ghidra_npc_ai_forwarded_helpers_x86
            ),
            npc_ai_raw_vector_x64_path=(
                config.source_ghidra_npc_ai_raw_vector_x64
            ),
            npc_ai_raw_vector_x86_path=(
                config.source_ghidra_npc_ai_raw_vector_x86
            ),
            npc_ai_lua_bindings_x64_path=(
                config.source_ghidra_npc_ai_lua_bindings_x64
            ),
            npc_ai_lua_bindings_x86_path=(
                config.source_ghidra_npc_ai_lua_bindings_x86
            ),
            npc_ai_script_stubs_x64_path=(
                config.source_ghidra_npc_ai_script_stubs_x64
            ),
            npc_ai_script_stubs_x86_path=(
                config.source_ghidra_npc_ai_script_stubs_x86
            ),
            npc_ai_surface_snapshot_path=(
                config.source_npc_ai_surface_snapshot
            ),
            component_text_vector_trace_x64_path=(
                config.source_ghidra_component_text_vector_trace_x64
            ),
            component_text_vector_trace_x86_path=(
                config.source_ghidra_component_text_vector_trace_x86
            ),
            component_text_data_x64_path=(
                config.source_ghidra_component_text_data_x64
            ),
            component_text_data_x86_path=(
                config.source_ghidra_component_text_data_x86
            ),
            ui_event_core_x64_path=config.source_ghidra_ui_event_core_x64,
            ui_event_core_x86_path=config.source_ghidra_ui_event_core_x86,
            component_text_surface_snapshot_path=(
                config.source_component_text_surface_snapshot
            ),
            lua64_root=config.source_gamepak_lua64_root,
        )
        self.assertEqual(set(quest_detail["labels"]), {str(i) for i in QUEST_DETAIL_LABELS})
        self.assertEqual(sum(detail_counts.values()), 7_826)
        self.assertEqual(
            scalar_domains["quest_component_text_kind"]["counts"],
            {"4": 13_525, "5": 4, "6": 2},
        )
        component_texts = decoded["quest_component_texts"]
        self.assertEqual(component_texts.unresolved_references, {})
        pre_quest_evidence = component_texts.resolution_evidence[
            "external_string_seed"
        ]
        self.assertEqual(
            pre_quest_evidence["format"],
            "AA8_PRE_QUEST_GLOBAL_STRING_CACHE_V1",
        )
        self.assertEqual(pre_quest_evidence["first_reference"], 0)
        self.assertEqual(pre_quest_evidence["next_reference"], 315_732)
        self.assertEqual(pre_quest_evidence["value_count"], 315_732)
        self.assertEqual(
            pre_quest_evidence["value_digest"],
            "C9DC2FCDFEEF4D66CC6B9989145EC290CEF613CF34B5B2C50877BC8BD3046E8D",
        )
        self.assertEqual(
            pre_quest_evidence["exact_replay"]["skills_first_reference"],
            75_557,
        )
        self.assertEqual(
            pre_quest_evidence["exact_replay"][
                "attach_anims_first_reference"
            ],
            150_126,
        )
        self.assertEqual(
            [
                value["candidate_index_delta"]
                for value in pre_quest_evidence["calibrations"]
            ],
            [395, 395, 1_099, 1_099, 1_099, 1_099],
        )
        globally_closed_results = {
            "cinema_subtitles": (
                3,
                "C2640CDB9825E4E70B81B5DE3145B06752BBCD96DCA576231E1533508B28CE88",
            ),
            "quest_act_con_accept_npc_emotions": (
                2,
                "80E571BDD81B05DA017960E164F960C529490DF70376A9FC14B91DA1AC17917C",
            ),
            "quest_act_obj_aliases": (
                4_962,
                "57CBE186D9FAAB285D5F9CEE21DE889D9CC974335CE024004DFE0C760061261A",
            ),
            "quest_act_obj_sell_backpack_goods": (
                7,
                "109A41E741ECD03AF62C6DCB94E661B3D47C4FB275766F57EF9EEA34DD9FF139",
            ),
            "quest_act_obj_spheres": (
                258,
                "9C89CC2849DA771DAE417355B23309136F6FBC8EEBD20DD28B188740CF4B439B",
            ),
            "quest_cameras": (
                104,
                "B9B72C745C17EB8D59D7C2FBD795FA9338FC49177E5AAEBD7CCE2B12114BB7A8",
            ),
            "quest_categories": (
                200,
                "4B1C643204B13816313DCD524FCE40DF0C3CC0817A3CD0567F902A05907B41E5",
            ),
            "quest_chat_bubbles": (
                25_939,
                "020EC7EBC1CA1134A62D2F77F871E6B72E8F6E8768FDD8DFA12B2A36402DFE8A",
            ),
            "quest_context_groups": (
                36,
                "5932F6EC34383A0A30D256147C1C4DBA957A8780FE6A1FCA77A21FEE96279629",
            ),
            "quest_contexts": (
                7_826,
                "B1B21871478BBBA3E7D336959891197087825A1E9E98FCCF43BA8E8B4660EC7B",
            ),
            "quest_doodad_groups": (
                18,
                "71ADDE47998F2BFB50007FD1AA49173DBB9D44CE2D09EC5496EB5ECAB84489D2",
            ),
            "quest_item_groups": (
                81,
                "49B14C0D7DCE7162CFF9BB10D7804C8E662AC81B1D172087C6582FBC2132E8D2",
            ),
            "quest_monster_groups": (
                1_006,
                "F917C5D891EE118D9CA17D235D131FBAD77458C6B4FF269F9559CEC029D71902",
            ),
            "quest_names": (
                1_673,
                "52FB6D21235A10A106A015C48EF263D044896D20206658EDA61A5212A9086DFE",
            ),
            "today_quest_groups": (
                128,
                "BFCE00B4FF7681F6F02B3B61429793E13357BE6C43484664C81AAD5446C948D7",
            ),
            "today_quest_steps": (
                25,
                "9FF180BECFD8C20A7A9F391A35A608F215481C67A33A649DD9FEF15294B74886",
            ),
        }
        for table, (row_count, digest) in globally_closed_results.items():
            result = decoded[table]
            self.assertEqual(len(result.rows), row_count)
            self.assertEqual(result.digest, digest)
            self.assertEqual(result.unresolved_references, {})
        collateral_replay_results = {
            "quest_mails": (
                2,
                "9A7B8B08E67231172276D798036E4995F328A094F1BB9342D6F00A990CF6F608",
            ),
            "cinema_captions": (
                224,
                "64BCC5DAB60A8661E6A1285DA76734CF14CCE24A918234DFDDF7FB89757B993D",
            ),
            "quest_context_texts": (
                918,
                "28E6CC992FF7F2A1812E6429F6B81D2ED2C2D9EC192A244AEE5F9B1A88AB5D3F",
            ),
        }
        for table, (row_count, digest) in collateral_replay_results.items():
            result = decoded[table]
            self.assertEqual(len(result.rows), row_count)
            self.assertEqual(result.digest, digest)
            self.assertEqual(result.unresolved_references, {})
        self.assertEqual(
            component_texts.token_counts,
            {
                "externally_resolved_reference": 2,
                "insert": 9_094,
                "literal": 8,
                "reference": 4_429,
                "resolved_reference": 4_427,
                "unresolved_reference": 2,
            },
        )
        self.assertEqual(
            component_texts.resolution_evidence[
                "quest_core_global_replay"
            ]["query_first_reference"],
            320_790,
        )
        self.assertEqual(
            component_texts.resolution_evidence[
                "quest_core_global_replay"
            ]["query_next_reference"],
            329_884,
        )
        chat_bubbles = decoded["quest_chat_bubbles"]
        self.assertEqual(
            [
                (
                    int(chat_bubbles.rows[index]["id"]),
                    str(chat_bubbles.rows[index]["speech"]),
                )
                for index in (0, 1_000, 25_938)
            ],
            [
                (
                    32,
                    "/결론 어, 어쩌지... 도적단 녀석들 계획서에, 계획서에! "
                    '"폭력배와 칼잡이, 싸움꾼과 마법사가 야영지로 침입한다." '
                    "라고 쓰여 있어요!",
                ),
                (
                    6_724,
                    "/주저 난 분명히 한 시간쯤 전에 나왔다고요!",
                ),
                (
                    44_534,
                    "/주기 여기 엉겅퀴와 선인장이에요. 상하지 않게 잘 "
                    "가져가세요.",
                ),
            ],
        )
        resolved_by_id = {
            int(row["id"]): str(row["text"])
            for row in component_texts.rows
            if int(row["id"]) in {5_802, 20_616, 20_617}
        }
        self.assertEqual(
            resolved_by_id,
            {
                5_802: (
                    "염색약의 효과가 사라지기 전에 마지의 양 목장으로 "
                    "염색한 갈색 산양을 데려가세요!"
                ),
                20_616: "피 묻은 손의 시체를 조사합니다.",
                20_617: "피 묻은 손의 시체를 조사합니다.",
            },
        )
        self.assertEqual(
            scalar_domains["chat_bubble_kind"]["counts"],
            {"1": 25_192, "2": 151, "3": 596},
        )
        self.assertEqual(
            scalar_domains["npc_ai"]["counts"],
            {"1": 32_139, "2": 3, "3": 18, "4": 4, "6": 27},
        )
        self.assertEqual(
            inline_semantics["chat_bubble_kind"]["labels"],
            CHAT_BUBBLE_KIND_LABELS,
        )
        self.assertEqual(
            inline_semantics["chat_bubble_kind"][
                "unresolved_semantic_ids"
            ],
            [],
        )
        self.assertEqual(
            inline_semantics["quest_component_text_kind"]["labels"],
            QUEST_COMPONENT_TEXT_KIND_LABELS,
        )
        self.assertEqual(
            inline_semantics["quest_component_text_kind"][
                "unresolved_semantic_ids"
            ],
            [],
        )
        component_text = inline_semantics["quest_component_text_kind"]
        self.assertEqual(
            component_text["consumers"][6]["api"],
            "DOODAD_PHASE_MSG",
        )
        self.assertEqual(
            component_text["consumers"][6]["event_id"],
            0x102,
        )
        self.assertEqual(
            component_text["value_properties"][5]["owning_quest_id"]["value"],
            598,
        )
        self.assertEqual(
            component_text["value_properties"][6][
                "native_row_population_state"
            ]["value"],
            "orphaned_parent_context",
        )
        self.assertEqual(
            component_text["value_properties"][6][
                "unresolved_text_reference_count"
            ]["value"],
            0,
        )
        self.assertEqual(
            inline_semantics["npc_ai"]["semantic_candidates"],
            {3: "follow_path", 6: "run_command_set"},
        )
        self.assertTrue(inline_semantics["npc_ai"]["architecture_parity"])
        self.assertEqual(
            inline_semantics["npc_ai"]["client_consumer_state"],
            "confirmed_unconsumed_in_traced_paths",
        )
        npc_ai_negative = inline_semantics["npc_ai"][
            "negative_consumer_evidence"
        ]
        self.assertEqual(
            npc_ai_negative["accessor_traces"]["x64"]["field_loads"],
            0,
        )
        self.assertEqual(
            npc_ai_negative["accessor_traces"]["x86"]["field_loads"],
            0,
        )
        self.assertEqual(
            npc_ai_negative["raw_vectors"]["x64"]["npc_ai_reads"],
            0,
        )
        self.assertEqual(
            npc_ai_negative["raw_vectors"]["x86"]["npc_ai_reads"],
            0,
        )
        self.assertEqual(
            npc_ai_negative["script_stubs"][
                "client_implementation_state"
            ],
            "explicitly_unsupported",
        )
        self.assertEqual(
            text_kind_domains["quest_name_kind"]["labels"],
            QUEST_NAME_KIND_LABELS,
        )
        self.assertEqual(
            text_kind_domains["quest_name_kind"]["counts"],
            {
                str(key): value
                for key, value in QUEST_NAME_KIND_COUNTS.items()
            },
        )
        self.assertEqual(
            text_kind_domains["quest_context_text_kind"]["labels"],
            QUEST_CONTEXT_TEXT_KIND_LABELS,
        )
        self.assertEqual(
            text_kind_domains["quest_context_text_kind"]["counts"],
            {
                str(key): value
                for key, value in QUEST_CONTEXT_TEXT_KIND_COUNTS.items()
            },
        )
        self.assertEqual(
            text_kind_domains["quest_context_text_kind"][
                "negative_consumer_evidence"
            ]["dedicated_comparisons"],
            0,
        )

    def test_quest_act_type_maps_to_native_detail_table(self) -> None:
        self.assertEqual(
            act_detail_table("QuestActConAcceptNpc"),
            "quest_act_con_accept_npcs",
        )
        self.assertEqual(
            act_detail_table("QuestActSupplyActability"),
            "quest_act_supply_actabilities",
        )

    def test_skill_frontier_native_inventory_and_type_resolution(self) -> None:
        config = load_config()
        inventory = skill_query_inventory(
            config.source_ghidra_sql_loaders_64,
            config.source_ghidra_skill_loaders_x86,
            config.source_ghidra_sql_call_sequence,
            config.source_skill_loader_tasks,
        )
        parity = compare_skill_layouts(inventory)
        decoded, diagnostics = load_stage50_results(config, inventory)
        self.assertEqual(parity["queries_compared"], 141)
        self.assertEqual(parity["x86_x64_exact"], 137)
        self.assertEqual(parity["mismatches"], 0)
        self.assertEqual(parity["blocked"], 0)
        self.assertEqual(len(decoded), 101)
        self.assertEqual(
            sum(len(value.rows) for value in decoded.values()), 657_459
        )
        self.assertEqual(len(decoded["skills"].rows), 33_466)
        self.assertEqual(len(decoded["buffs"].rows), 27_303)
        self.assertEqual(len(decoded["effects"].rows), 60_885)
        self.assertEqual(
            len(decoded["npc_spawner_despawn_effects"].rows), 3
        )
        self.assertFalse(
            any(
                str(row["actual_type"]).startswith("<ref:")
                for row in decoded["effects"].rows
            )
        )
        self.assertFalse(
            any(
                str(row["actual_type"]).startswith("<ref:")
                for row in decoded["plot_effects"].rows
            )
        )
        self.assertEqual(
            diagnostics["native_result_absent_calls"],
            [67, 95, 96, 97, 287],
        )
        plot_event_ids = {
            int(row["id"]) for row in decoded["plot_events"].rows
        }
        missing_plot_events = Counter(
            int(row["event_id"])
            for row in decoded["buff_triggers"].rows
            if int(row["event_id"]) > 0
            and int(row["event_id"]) not in plot_event_ids
        )
        self.assertEqual(
            missing_plot_events,
            Counter(
                {
                    4: 431,
                    5: 126,
                    6: 3_804,
                    7: 19,
                    8: 20,
                    9: 29,
                    10: 154,
                    11: 168,
                    15: 8,
                    19: 1,
                    20: 15,
                    21: 177,
                    22: 9,
                    31: 2,
                }
            ),
        )

    def test_world_interaction_enum_and_optional_details_are_native_closed(
        self,
    ) -> None:
        config = load_config()
        x64 = parse_world_interaction_switch(
            config.source_ghidra_world_interaction_enum_x64
        )
        x86 = parse_world_interaction_switch(
            config.source_ghidra_world_interaction_enum_x86
        )
        self.assertEqual(x64["labels"], x86["labels"])
        self.assertEqual(x64["labels"], WORLD_INTERACTION_LABELS)
        self.assertEqual(len(x64["labels"]), 105)
        self.assertNotIn(WORLD_INTERACTION_INVALID_ID, x64["labels"])
        self.assertEqual(x64["labels"][0], "looting")
        self.assertEqual(x64["labels"][94], "demolish")
        self.assertEqual(x64["labels"][96], "craft_start_ship")
        self.assertEqual(x64["labels"][105], "sell_backpack")

        audit = audit_world_interactions(config)
        self.assertEqual(
            audit["columns"],
            ("wi_id", "apply_expert", "distance_sqrt", "lp"),
        )
        self.assertEqual(audit["layout"], ("68", "38", "68", "68"))
        self.assertEqual(len(audit["result"].rows), 60)
        self.assertEqual(audit["result"].advertised_rows, 60)
        self.assertEqual(len(audit["detail_ids"]), 60)
        self.assertTrue(audit["detail_ids"].issubset(x64["labels"]))
        self.assertEqual(
            audit["detail_value_counts"]["apply_expert"],
            {0: 1, 1: 59},
        )

    def test_stage60_path_normalization_and_classification(self) -> None:
        self.assertEqual(
            lookup_path(r"GAME\Objects\Characters\sample.cdf"),
            "objects/characters/sample.cdf",
        )
        self.assertEqual(classify_asset("game/ui/icon/a.dds"), "ui_asset")
        self.assertEqual(
            classify_asset("game/objects/characters/a.cdf"), "model_asset"
        )

    def test_stage60_global_string_prefix_and_icon_closure(self) -> None:
        config = load_config()
        inventory = asset_query_inventory(config)
        decoded, diagnostics = decode_string_prefix(config)
        states = Counter(value.architecture_state for value in inventory)
        self.assertEqual(len(inventory), 207)
        self.assertEqual(states["architecture_mismatch"], 0)
        self.assertEqual(len(decoded), 28)
        self.assertEqual(len(decoded[30].rows), 18_263)
        self.assertEqual(diagnostics["unresolved_references"], 0)
        self.assertEqual(diagnostics["cached_strings"], 69_516)
        self.assertEqual(diagnostics["icon_12519"], "test")


if __name__ == "__main__":
    unittest.main()
