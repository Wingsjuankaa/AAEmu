from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ..db import create_database
from ..descriptor_lifecycle import rebuild_descriptor_lifecycle


class DescriptorLifecycleTests(unittest.TestCase):
    def test_classifies_all_resolved_descriptor_lifecycles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            connection = create_database(Path(temporary) / "fixture.sqlite")
            for item_id, impl_id, category_id in (
                (1, 12, 65),
                (2, 12, 65),
                (3, 12, 65),
                (4, 12, 65),
                (5, 12, 65),
                (6, 12, 65),
                (7, 12, 65),
                (8, 2, 199),
                (9, 27, 33),
                (10, 24, 86),
                (11, 24, 86),
                (12, 28, 143),
                (13, 28, 143),
            ):
                connection.execute(
                    """
                    INSERT INTO items(
                        item_id,impl_id,name,description,category_id,level,
                        use_skill_id,buff_id,craft_id,loot_quest_id,
                        client_row_json,client_provenance
                    ) VALUES (?,?,?,'',?,0,0,0,0,0,'{}','client_compact_8')
                    """,
                    (item_id, impl_id, f"item-{item_id}", category_id),
                )
            specs = {}
            for table_name, sql in (
                (
                    "item_recipes",
                    "SELECT item_id, craft_id FROM item_recipes",
                ),
                (
                    "item_armors",
                    "SELECT id, item_id FROM item_armors",
                ),
                (
                    "item_categories",
                    "SELECT id, name FROM item_categories",
                ),
                (
                    "dyeable_items",
                    "SELECT item_id, color FROM dyeable_items",
                ),
                (
                    "item_accessories",
                    "SELECT id, item_id FROM item_accessories",
                ),
                (
                    "item_slave_equipments",
                    "SELECT id, item_id FROM item_slave_equipments",
                ),
                (
                    "skill_reagents",
                    "SELECT id, amount, item_id, skill_id "
                    "FROM skill_reagents WHERE enable = 't'",
                ),
            ):
                cursor = connection.execute(
                    """
                    INSERT INTO query_specs(
                        table_name,source_module,sql_text,columns_json,
                        layout_json,stream_name,start_offset,expected_rows,
                        anchor_json,loader_consumer,status,evidence_json
                    ) VALUES (?, 'fixture', ?, '[]', '[]', 'game11',
                              1, 1, '{}', 'fixture', 'registered', '{}')
                    """,
                    (table_name, sql),
                )
                query_spec_id = int(cursor.lastrowid)
                specs[table_name] = query_spec_id
                connection.execute(
                    """
                    INSERT INTO cached_results(
                        query_spec_id,artifact_id,start_offset,end_offset,
                        row_count,row_digest,raw_references_json,
                        unresolved_references_json,resolution_evidence_json,
                        status,error
                    ) VALUES (?,NULL,1,2,1,'digest','[]','[]','{}',
                              'confirmed',NULL)
                    """,
                    (query_spec_id,),
                )
            connection.execute(
                """
                INSERT INTO cached_result_rows(query_spec_id,row_index,row_json)
                VALUES (?,0,?)
                """,
                (
                    specs["item_categories"],
                    json.dumps({"id": 199, "name": "합성재료"}),
                ),
            )
            for item_id, state, descriptor in (
                (1, "confirmed", {"item_id": 1, "craft_id": 101}),
                (2, "confirmed", {"item_id": 2, "craft_id": 102}),
                (3, "missing", {}),
                (4, "missing", {}),
                (5, "missing", {}),
                (6, "missing", {}),
                (7, "missing", {}),
            ):
                connection.execute(
                    """
                    INSERT INTO descriptors(
                        item_id,family,table_name,row_key,descriptor_json,
                        state,provenance,evidence_json
                    ) VALUES (?,'recipe','item_recipes',?,?,?,
                              'x2game_confirmed','{}')
                    """,
                    (item_id, str(item_id), json.dumps(descriptor), state),
                )
            connection.execute(
                """
                INSERT INTO descriptors(
                    item_id,family,table_name,row_key,descriptor_json,state,
                    provenance,evidence_json
                ) VALUES (8,'armor','item_armors','8','{}','missing',
                          'x2game_confirmed','{}')
                """
            )
            connection.execute(
                """
                UPDATE items
                SET use_skill_id=39137,
                    client_row_json='{"impl_id":27,"use_skill_id":39137,
                                      "use_skill_as_reagent":1}'
                WHERE item_id=9
                """
            )
            connection.execute(
                """
                UPDATE items SET buff_id=3459 WHERE item_id=11
                """
            )
            for item_id, family, table_name, state, descriptor in (
                (9, "dyeing", None, "confirmed", {"impl_id": 27}),
                (
                    10,
                    "accessory",
                    "item_accessories",
                    "confirmed",
                    {"id": 1, "item_id": 10},
                ),
                (11, "accessory", "item_accessories", "missing", {}),
                (
                    12,
                    "slave_equipment",
                    "item_slave_equipments",
                    "confirmed",
                    {"id": 1, "item_id": 12},
                ),
                (13, "slave_equipment", "item_slave_equipments", "missing", {}),
            ):
                connection.execute(
                    """
                    INSERT INTO descriptors(
                        item_id,family,table_name,row_key,descriptor_json,
                        state,provenance,evidence_json
                    ) VALUES (?,?,?,?,? ,?,'x2game_confirmed','{}')
                    """,
                    (
                        item_id,
                        family,
                        table_name,
                        str(item_id),
                        json.dumps(descriptor),
                        state,
                    ),
                )
            connection.execute(
                """
                INSERT INTO cached_result_rows(query_spec_id,row_index,row_json)
                VALUES (?,0,?)
                """,
                (
                    specs["skill_reagents"],
                    json.dumps(
                        {
                            "id": 1,
                            "amount": 1,
                            "item_id": 13,
                            "skill_id": 777,
                        }
                    ),
                ),
            )
            edges = (
                (1, "unlocks_craft", "craft", 101, "confirmed"),
                (2, "unlocks_craft", "craft", 102, "missing"),
                (
                    3,
                    "conversion_reagent_in_pack",
                    "item_conv_rpack",
                    201,
                    "confirmed",
                ),
                (4, "used_as_craft_material", "craft", 103, "confirmed"),
                (5, "use_skill_id", "skill", 301, "confirmed"),
                (6, "used_as_craft_material", "craft", 104, "missing"),
                (7, "tagged_with", "tag", 401, "confirmed"),
            )
            for item_id, relation, kind, target_id, state in edges:
                connection.execute(
                    """
                    INSERT INTO dependency_edges(
                        src_kind,src_id,relation,dst_kind,dst_id,required,
                        state,provenance,evidence_json
                    ) VALUES ('item',?,?,?,?,0,?,'game11_native','{}')
                    """,
                    (str(item_id), relation, kind, str(target_id), state),
                )

            summary = rebuild_descriptor_lifecycle(connection)
            self.assertEqual(summary["rows"], 13)
            actual = {
                int(row["item_id"]): (
                    str(row["lifecycle_state"]),
                    str(row["operational_state"]),
                )
                for row in connection.execute(
                    """
                    SELECT item_id,lifecycle_state,operational_state
                    FROM descriptor_lifecycle ORDER BY item_id
                    """
                )
            }
            self.assertEqual(actual[1], ("enabled", "recipe_unlock"))
            self.assertEqual(actual[2], ("disabled", "recipe_unlock"))
            self.assertEqual(
                actual[3],
                ("tombstone", "active_conversion_reagent"),
            )
            self.assertEqual(
                actual[4],
                ("tombstone", "active_craft_material"),
            )
            self.assertEqual(
                actual[5],
                ("tombstone", "active_skill_consumer"),
            )
            self.assertEqual(
                actual[6],
                ("tombstone", "inactive_craft_only"),
            )
            self.assertEqual(actual[7], ("tombstone", "metadata_only"))
            self.assertEqual(
                actual[8],
                ("tombstone", "native_synthesis_material_catalog"),
            )
            self.assertEqual(
                actual[9],
                ("present", "native_base_item_skill_driven"),
            )
            self.assertEqual(
                actual[10],
                ("present", "accessory_descriptor"),
            )
            self.assertEqual(
                actual[11],
                ("tombstone", "buff_metadata_only"),
            )
            self.assertEqual(
                actual[12],
                ("present", "slave_equipment_descriptor"),
            )
            self.assertEqual(
                actual[13],
                (
                    "tombstone",
                    "active_skill_reagent_and_craft_product",
                ),
            )
            connection.close()


if __name__ == "__main__":
    unittest.main()
