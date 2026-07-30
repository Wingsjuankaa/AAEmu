from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ..config import ForensicsConfig
from ..db import create_database, finalize_database
from ..native_catalogs import rebuild_native_catalogs
from ..native_closure import generate_native_closure_audit


class NativeCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        repo = root / "repo"
        repo.mkdir()
        streams = root / "streams"
        streams.mkdir()
        client = root / "client.sqlite"
        client.touch()
        runtime = root / "runtime.sqlite"
        runtime.touch()
        runtime_env = repo / ".env"
        runtime_env.write_text(f"COMPACT_DB={runtime}\n", encoding="utf-8")
        self.config = ForensicsConfig(
            client_build="Kakao 8.0.3.12 r558734",
            client_compact=client,
            streams_root=streams,
            repo_root=repo,
            legacy_item_root=repo,
            output_dir=root / "output",
            runtime_env=runtime_env,
            runtime=runtime,
            sql_manifest=None,
            surface_manifest=None,
            gamepak_index=None,
            x2game=(),
        )
        self.connection = create_database(self.config.database)
        self.connection.executemany(
            """
            INSERT INTO items(
                item_id,impl_id,name,description,category_id,level,
                use_skill_id,buff_id,craft_id,loot_quest_id,
                client_row_json,client_provenance
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                (100, 0, "Product", "", 1, 1, 0, 0, 0, 0, "{}", "native"),
                (101, 12, "Design", "", 65, 1, 0, 0, 0, 0, "{}", "native"),
            ),
        )
        self.connection.execute(
            """
            INSERT INTO descriptors(
                item_id,family,table_name,row_key,descriptor_json,state,
                provenance,evidence_json
            ) VALUES (101,'recipe','item_recipes','101','{}','missing',
                      'game11_native','{}')
            """
        )

    def tearDown(self) -> None:
        self.connection.close()
        self.temporary.cleanup()

    def _result(
        self,
        table: str,
        rows: list[dict[str, object]],
        *,
        result_status: str = "confirmed",
    ) -> None:
        columns = list(rows[0]) if rows else ["id"]
        cursor = self.connection.execute(
            """
            INSERT INTO query_specs(
                table_name,source_module,sql_text,columns_json,layout_json,
                stream_name,start_offset,expected_rows,anchor_json,
                loader_consumer,status,evidence_json
            ) VALUES (?,?,?,?,?,'game11',0,?,'{}','fixture','registered','{}')
            """,
            (
                table,
                "fixture",
                f"SELECT {','.join(columns)} FROM {table}",
                json.dumps(columns),
                json.dumps(["68"] * len(columns)),
                len(rows),
            ),
        )
        query_spec_id = int(cursor.lastrowid)
        self.connection.execute(
            """
            INSERT INTO cached_results(
                query_spec_id,artifact_id,start_offset,end_offset,row_count,
                row_digest,raw_references_json,unresolved_references_json,
                resolution_evidence_json,status,error
            ) VALUES (?,NULL,0,1,?,'fixture','[]','[]','{}',?,NULL)
            """,
            (query_spec_id, len(rows), result_status),
        )
        self.connection.executemany(
            """
            INSERT INTO cached_result_rows(query_spec_id,row_index,row_json)
            VALUES (?,?,?)
            """,
            (
                (query_spec_id, index, json.dumps(row, sort_keys=True))
                for index, row in enumerate(rows)
            ),
        )

    def test_catalogs_confirm_native_entities_and_alternate_consumer(self) -> None:
        self._result(
            "craft_materials",
            [
                {
                    "id": 1,
                    "amount": 1,
                    "craft_id": 900,
                    "item_id": 101,
                    "main_grade": 0,
                    "require_grade": -1,
                    "upper_grade": 0,
                }
            ],
        )
        self._result(
            "craft_products",
            [
                {
                    "id": 2,
                    "amount": 1,
                    "craft_id": 900,
                    "item_grade_id": 0,
                    "item_id": 100,
                    "rate": 100,
                    "use_grade": 0,
                }
            ],
        )
        self._result(
            "crafts",
            [{"id": 900}],
            result_status="confirmed_id_scope_with_opaque_text",
        )
        self._result(
            "buffs",
            [{"id": 3459}],
            result_status="confirmed_id_scope_with_opaque_text",
        )
        self._result(
            "doodad_almighties",
            [{"id": 14424}],
            result_status="confirmed_id_scope_with_opaque_text",
        )
        summary = rebuild_native_catalogs(self.connection)
        self.assertEqual(summary["orphan_craft_item_edges"], 0)
        entities = {
            (row[0], row[1])
            for row in self.connection.execute(
                """
                SELECT entity_kind,entity_id FROM native_entities
                ORDER BY entity_kind,entity_id
                """
            )
        }
        self.assertIn(("craft", 900), entities)
        self.assertIn(("buff", 3459), entities)
        self.assertIn(("doodad", 14424), entities)
        reverse = self.connection.execute(
            """
            SELECT state FROM dependency_edges
            WHERE src_kind='item' AND src_id='101'
              AND relation='used_as_craft_material'
              AND dst_kind='craft' AND dst_id='900'
            """
        ).fetchone()
        self.assertEqual(reverse[0], "confirmed")
        finalize_database(self.connection)
        report = generate_native_closure_audit(self.config)
        self.assertEqual(
            report["closure_states"],
            {"native_relation_confirmed_descriptor_unresolved": 1},
        )

    def test_conversion_graph_closes_native_reagent_consumer(self) -> None:
        self.connection.execute(
            """
            INSERT INTO items(
                item_id,impl_id,name,description,category_id,level,
                use_skill_id,buff_id,craft_id,loot_quest_id,
                client_row_json,client_provenance
            ) VALUES (
                102,12,'Conversion reagent','',65,1,0,0,0,0,'{}','native'
            )
            """
        )
        self.connection.execute(
            """
            INSERT INTO descriptors(
                item_id,family,table_name,row_key,descriptor_json,state,
                provenance,evidence_json
            ) VALUES (
                102,'recipe','item_recipes','102','{}','missing',
                'game11_native','{}'
            )
            """
        )
        self._result("item_conv_epacks", [{"id": 1}])
        self._result("item_conv_rpacks", [{"id": 442}])
        self._result("item_conv_ppacks", [{"id": 513, "chance_rate": 10000}])
        self._result(
            "item_conv_sets",
            [{"id": 3, "dialog_content": "Salvage?", "dialog_title": "Salvage"}],
        )
        self._result("item_convs", [{"id": 440, "item_conv_set_id": 3}])
        self._result(
            "item_conv_reagents",
            [
                {
                    "id": 1,
                    "grade_id": 0,
                    "item_conv_rpack_id": 442,
                    "item_id": 102,
                    "max_grade_id": 11,
                }
            ],
        )
        self._result(
            "item_conv_rpack_members",
            [{"id": 1, "item_conv_rpack_id": 442, "item_conv_id": 440}],
        )
        self._result(
            "item_conv_ppack_members",
            [{"id": 1, "item_conv_ppack_id": 513, "item_conv_id": 440}],
        )
        self._result(
            "item_conv_products",
            [
                {
                    "id": 1,
                    "item_conv_ppack_id": 513,
                    "item_grade_id": -1,
                    "item_id": 100,
                    "max": 1,
                    "min": 1,
                    "weight": 1,
                }
            ],
        )

        rebuild_native_catalogs(self.connection)
        edge = self.connection.execute(
            """
            SELECT state FROM dependency_edges
            WHERE src_kind='item' AND src_id='102'
              AND relation='conversion_reagent_in_pack'
              AND dst_kind='item_conv_rpack' AND dst_id='442'
            """
        ).fetchone()
        self.assertEqual(edge[0], "confirmed")

        chain = {
            (row[0], row[1], row[2], row[3])
            for row in self.connection.execute(
                """
                SELECT src_kind,relation,dst_kind,dst_id
                FROM dependency_edges
                WHERE (src_kind='item_conv_rpack' AND src_id='442')
                   OR (src_kind='item_conv' AND src_id='440')
                   OR (src_kind='item_conv_ppack' AND src_id='513')
                """
            )
        }
        self.assertIn(
            ("item_conv_rpack", "enables_conversion", "item_conv", "440"),
            chain,
        )
        self.assertIn(
            ("item_conv", "outputs_product_pack", "item_conv_ppack", "513"),
            chain,
        )
        self.assertIn(
            ("item_conv_ppack", "contains_conversion_product", "item", "100"),
            chain,
        )

        finalize_database(self.connection)
        report = generate_native_closure_audit(self.config)
        document = json.loads(
            self.config.native_closure_report.read_text(encoding="utf-8")
        )
        item = next(row for row in document["items"] if row["item_id"] == 102)
        self.assertEqual(item["consumer_roles"], ["conversion_reagent"])
        self.assertEqual(
            item["closure_state"],
            "native_relation_confirmed_descriptor_unresolved",
        )

    def test_tag_graph_closes_native_item_metadata_consumer(self) -> None:
        self.connection.execute(
            """
            INSERT INTO items(
                item_id,impl_id,name,description,category_id,level,
                use_skill_id,buff_id,craft_id,loot_quest_id,
                client_row_json,client_provenance
            ) VALUES (
                103,2,'Tagged armor','',199,0,0,0,0,0,'{}','native'
            )
            """
        )
        self.connection.execute(
            """
            INSERT INTO descriptors(
                item_id,family,table_name,row_key,descriptor_json,state,
                provenance,evidence_json
            ) VALUES (
                103,'armor','item_armors','103','{}','missing',
                'game11_native','{}'
            )
            """
        )
        self._result("tags", [{"id": 1157, "name": "Production tag"}])
        self._result(
            "tagged_items",
            [{"id": 1, "item_id": 103, "tag_id": 1157}],
        )

        rebuild_native_catalogs(self.connection)
        edge = self.connection.execute(
            """
            SELECT state FROM dependency_edges
            WHERE src_kind='item' AND src_id='103'
              AND relation='tagged_with'
              AND dst_kind='tag' AND dst_id='1157'
            """
        ).fetchone()
        self.assertEqual(edge[0], "confirmed")

        finalize_database(self.connection)
        generate_native_closure_audit(self.config)
        document = json.loads(
            self.config.native_closure_report.read_text(encoding="utf-8")
        )
        item = next(row for row in document["items"] if row["item_id"] == 103)
        self.assertEqual(item["consumer_roles"], ["item_tag"])
        self.assertEqual(
            item["closure_state"],
            "native_metadata_confirmed_consumer_unresolved",
        )

    def test_skill_reagent_graph_preserves_referenced_skill_endpoint(self) -> None:
        self._result(
            "skill_reagents",
            [{"id": 4708, "amount": 1, "item_id": 100, "skill_id": 45719}],
        )
        self._result(
            "skill_products",
            [{"id": 1, "amount": 2, "item_id": 101, "skill_id": 50000}],
        )

        summary = rebuild_native_catalogs(self.connection)
        self.assertEqual(
            summary["edge_counts"]["item_to_skill:referenced"],
            2,
        )
        reagent = self.connection.execute(
            """
            SELECT state,evidence_json FROM dependency_edges
            WHERE src_kind='item' AND src_id='100'
              AND relation='used_as_skill_reagent'
              AND dst_kind='skill' AND dst_id='45719'
            """
        ).fetchone()
        self.assertEqual(reagent["state"], "referenced")
        self.assertEqual(
            json.loads(reagent["evidence_json"])["query_filter"],
            "enable = 't'",
        )
        product = self.connection.execute(
            """
            SELECT state FROM dependency_edges
            WHERE src_kind='skill' AND src_id='50000'
              AND relation='produces_item'
              AND dst_kind='item' AND dst_id='101'
            """
        ).fetchone()
        self.assertEqual(product["state"], "confirmed")


if __name__ == "__main__":
    unittest.main()
