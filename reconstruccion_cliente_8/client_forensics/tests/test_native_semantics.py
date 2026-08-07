from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from client_forensics.native_semantics import (
    NativeSemanticConfig,
    _apply_review_consumer_resolutions,
    _closure_for_root,
    _domain_for_text,
    _load_semantic_reviews,
    _tier,
    locator_rvas,
    locator_has_explicit_architecture_pair,
    locator_to_rva,
    normalize_sql,
)
from client_forensics.native_code_schema import create_native_code_tables


class NativeSemanticTests(unittest.TestCase):
    @staticmethod
    def _config(root: Path, *, maximum: int = 2000) -> NativeSemanticConfig:
        return NativeSemanticConfig(
            path=root / "semantic.json",
            client_build="fixture",
            database=root / "semantic.sqlite",
            manifest=root / "semantic.manifest.json",
            dossier_root=root / "dossiers",
            required_stage_15_sha256="A" * 64,
            closure={
                "outbound_depth": 5,
                "inbound_depth": 3,
                "fanin_cutoff": 4,
                "max_functions": maximum,
            },
            impact={
                "consumer": 100,
                "query": 90,
                "native_symbol": 90,
                "rtti_vtable": 80,
                "blocker": 95,
                "outbound": [0, 80, 60, 40, 20, 10],
                "inbound": [0, 50, 30, 15],
            },
            uncertainty={},
            domains=(
                {"id": "protocol", "priority": 100, "keywords": ["packet", "serialize"]},
                {"id": "item_loot_economy", "priority": 95, "keywords": ["loot", "item"]},
            ),
            config_sha256="fixture",
        )

    def test_sql_normalization_is_deterministic_and_not_semantic_authority(self) -> None:
        first = normalize_sql(" SELECT  id, name\r\n FROM items ; ")
        second = normalize_sql("select id, name from items")
        self.assertEqual(first, second)
        self.assertEqual(first, "select id, name from items")
        self.assertEqual(normalize_sql(None), "")

    def test_locator_conversion_handles_aslr_and_multiple_architectures(self) -> None:
        self.assertEqual(locator_to_rva("x2game.dll FUN_39A365C0", 0x39000000), 0xA365C0)
        self.assertEqual(
            locator_rvas(
                "x2game.dll x64 FUN_39a365c0 + x2game.dll x86 FUN_39d2ec60",
                0x39000000,
            ),
            [0xA365C0, 0xD2EC60],
        )
        self.assertEqual(locator_to_rva("RVA FUN_00123456", 0x39000000), 0x123456)
        self.assertTrue(locator_has_explicit_architecture_pair(
            "x2game.dll x64 FUN_39a365c0 + x2game.dll x86 FUN_39d2ec60"
        ))
        self.assertFalse(locator_has_explicit_architecture_pair("x2game.dll FUN_39a365c0"))

    def test_domain_and_tier_order_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = self._config(Path(temporary))
            self.assertEqual(_domain_for_text(config, "loot packet"), ("protocol", 100))
            self.assertEqual(_tier(90), "critical")
            self.assertEqual(_tier(60), "high")
            self.assertEqual(_tier(30), "medium")
            self.assertEqual(_tier(1), "context")
            self.assertEqual(_tier(0), "low")

    def test_closure_handles_cycles_depth_fanin_and_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            connection = sqlite3.connect(":memory:")
            connection.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            create_native_code_tables(connection)
            edges = [
                ("a", "b"), ("b", "c"), ("c", "a"),
                ("a", "d"), ("d", "e"), ("x", "a"),
            ]
            for index, (caller, callee) in enumerate(edges):
                connection.execute(
                    """
                    INSERT INTO code_calls(
                        call_key,caller_function_key,callee_function_key,
                        callsite_rva,target_rva,target_name,call_kind,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (f"call:{index}", caller, callee, index, index, None, "direct", "confirmed", "{}"),
                )
            connection.commit()
            config = self._config(root, maximum=4)
            records, summary = _closure_for_root(
                config,
                connection,
                {"domain": "protocol"},
                {"a": {"relation": "seed", "state": "confirmed", "impact": 100, "evidence": {}}},
                {"a": 1, "b": 1, "c": 1, "d": 1, "e": 1},
                {},
            )
            self.assertEqual(records["a"]["depth"], 0)
            self.assertLessEqual(len(records), 4)
            self.assertEqual(summary["truncated"], 1)
            self.assertEqual(summary["truncation_reason"], "truncated_high_fanout")
            connection.close()

    def test_review_overlay_requires_exact_function_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            review_path = root / "reviews.json"
            connection = sqlite3.connect(":memory:")
            connection.executescript(
                """
                CREATE TABLE code_binaries(
                    binary_key TEXT PRIMARY KEY,
                    module_name TEXT NOT NULL,
                    architecture TEXT NOT NULL,
                    sha256 TEXT NOT NULL
                );
                CREATE TABLE code_functions(
                    function_key TEXT PRIMARY KEY,
                    binary_key TEXT NOT NULL,
                    entry_rva INTEGER NOT NULL,
                    byte_sha256 TEXT
                );
                CREATE TABLE code_regions(
                    region_key TEXT PRIMARY KEY,
                    binary_key TEXT NOT NULL,
                    start_rva INTEGER NOT NULL,
                    end_rva INTEGER NOT NULL,
                    region_kind TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO code_binaries VALUES(?,?,?,?)",
                ("bin", "x2game.dll", "x64", "C" * 64),
            )
            connection.execute(
                "INSERT INTO code_functions VALUES(?,?,?,?)",
                ("fn", "bin", 0x303A10, "B" * 64),
            )
            connection.execute(
                "INSERT INTO code_regions VALUES(?,?,?,?,?)",
                ("region", "bin", 0x4000, 0x4100, "opaque"),
            )
            payload = {
                "format": "AA8_NATIVE_SEMANTIC_REVIEW_V1",
                "client_build": "fixture",
                "required_stage_15_sha256": "A" * 64,
                "reviews": [{
                    "review_key": "loot",
                    "root_key": "root:loot",
                    "closure_status": "blocked_by_missing_native_data",
                    "state": "corroborated",
                    "dossier_name": "loot.json",
                    "summary": "The client displays a server-selected result.",
                    "functions": [{
                        "function_key": "fn",
                        "module_name": "x2game.dll",
                        "architecture": "x64",
                        "entry_rva": 0x303A10,
                        "byte_sha256": "B" * 64,
                        "role": "result_handler",
                        "state": "corroborated",
                    }],
                    "regions": [{
                        "region_key": "region",
                        "module_name": "x2game.dll",
                        "architecture": "x64",
                        "binary_sha256": "C" * 64,
                        "start_rva": 0x4000,
                        "end_rva": 0x4100,
                        "classification": "reachable_context",
                        "role": "compiler_switch_table",
                        "state": "corroborated",
                        "evidence": ["fn"],
                    }],
                    "findings": [{
                        "finding_key": "server_result",
                        "state": "corroborated",
                        "conclusion": "The packet carries the selected result.",
                        "evidence": ["fn"],
                    }],
                    "remaining_blocker": {
                        "kind": "missing_native_data",
                        "description": "Native loot rows are absent.",
                    },
                }],
            }
            review_path.write_text(json.dumps(payload), encoding="utf-8")
            config = replace(self._config(root), review_overrides=review_path)
            reviews, digest = _load_semantic_reviews(
                config, connection, {"root:loot": {"root_key": "root:loot"}}
            )
            self.assertEqual(reviews["root:loot"]["review_key"], "loot")
            self.assertEqual(len(digest or ""), 64)

            payload["reviews"][0]["regions"][0]["end_rva"] = 0x4101
            review_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "region identity mismatch"):
                _load_semantic_reviews(
                    config, connection, {"root:loot": {"root_key": "root:loot"}}
                )
            payload["reviews"][0]["regions"][0]["end_rva"] = 0x4100
            payload["reviews"][0]["functions"][0]["entry_rva"] = 0x303A11
            review_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                _load_semantic_reviews(
                    config, connection, {"root:loot": {"root_key": "root:loot"}}
                )
            connection.close()

    def test_review_consumer_resolution_replaces_false_ambiguous_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = self._config(Path(temporary))
            root_key = "consumer:consumer-33"
            roots = {
                root_key: {
                    "root_key": root_key,
                    "root_kind": "consumer",
                    "state": "candidate",
                    "evidence_json": json.dumps({"consumer_key": "consumer-33"}),
                }
            }
            seeds = {
                root_key: {
                    "false": {"relation": "locator_resolves_to_function"},
                    "x64": {"relation": "locator_resolves_to_function"},
                }
            }
            rows = [(
                "consumer-33", "query-33", "FUN_39a23770", None, 2,
                "architecture_ambiguous_locator", "ambiguous",
                json.dumps(["false", "x64"]), json.dumps({"root_key": root_key}),
            )]
            reviews = {
                root_key: {
                    "review_key": "item_accept_quests",
                    "consumer_resolution": {
                        "consumer_key": "consumer-33",
                        "function_keys": ["x64", "x86-real"],
                        "rejected_function_keys": ["false"],
                        "classification": "architecture_pair_corroborated",
                        "state": "corroborated",
                        "method": "exact_sql_and_loader_layout",
                        "evidence": ["same SQL"],
                    },
                }
            }
            result = _apply_review_consumer_resolutions(config, roots, seeds, rows, reviews)
            self.assertEqual(set(seeds[root_key]), {"x64", "x86-real"})
            self.assertEqual(result[0][4:7], (2, "architecture_pair_corroborated", "corroborated"))
            self.assertEqual(json.loads(result[0][7]), ["x64", "x86-real"])
            self.assertEqual(roots[root_key]["state"], "corroborated")


if __name__ == "__main__":
    unittest.main()
