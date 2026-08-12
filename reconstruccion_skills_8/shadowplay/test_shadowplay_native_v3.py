#!/usr/bin/env python3
"""Validate the complete AA8 Shadowplay V6 runtime and its provenance."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_shadowplay_native_v3_runtime import (  # noqa: E402
    ALL_ROOTS,
    PASSIVES,
    SEED_KEYS,
    TOMBSTONE_ROOT_FIELDS,
    VISIBLE_ROOTS,
    columns,
    exact_native_row,
    normalize,
    ro,
    sha256_file,
    verify,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("unittest_args", nargs="*")
    return parser.parse_args()


class ShadowplayNativeV3Tests(unittest.TestCase):
    runtime_path: Path
    knowledge_path: Path
    manifest_path: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = ro(cls.runtime_path)
        cls.knowledge = ro(cls.knowledge_path)
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.runtime.close()
        cls.knowledge.close()

    def test_complete_runtime_contract(self) -> None:
        result = verify(self.runtime)
        self.assertEqual(31, result["roots"])
        self.assertEqual(12, result["visible_roots"])
        self.assertEqual(6, result["passives"])
        self.assertEqual(0, result["quarantined"])

    def test_manifest_covers_every_root_passive_and_required_seed(self) -> None:
        evidence_keys = set(self.manifest["evidence_keys"])
        self.assertTrue(SEED_KEYS.issubset(evidence_keys))
        self.assertTrue({f"skill:{skill_id}" for skill_id in ALL_ROOTS}.issubset(evidence_keys))
        self.assertTrue({f"passive_buff:{skill_id}" for skill_id, _, _ in PASSIVES}.issubset(evidence_keys))
        self.assertEqual("forbidden", self.manifest["authority"]["custom_hypothesis"])

    def test_every_imported_native_row_matches_current_knowledge(self) -> None:
        checked = 0
        for row in self.runtime.execute(
            "SELECT table_name,row_id,entity_key FROM shadowplay_v3_row_provenance "
            "WHERE classification='client-native' ORDER BY table_name,row_id"
        ):
            native = exact_native_row(self.knowledge, row["entity_key"])
            self.assertIsNotNone(native, row["entity_key"])
            _, table, payload, _, _ = native
            self.assertEqual(row["table_name"], table)
            expected, _ = normalize(table, payload)
            available = columns(self.runtime, table)
            names = [name for name in expected if name in available]
            quoted = ",".join('"' + name.replace('"', '""') + '"' for name in names)
            actual = self.runtime.execute(
                f'SELECT {quoted} FROM "{table}" WHERE id=?', (row["row_id"],)
            ).fetchone()
            self.assertIsNotNone(actual, f"{table}.{row['row_id']}")
            for index, name in enumerate(names):
                self.assertEqual(
                    expected[name], actual[index], f"{table}.{row['row_id']}.{name}"
                )
            checked += 1
        self.assertGreater(checked, 2500)

    def test_tombstone_roots_only_retain_individually_proven_fields(self) -> None:
        schema = columns(self.runtime, "skills")
        for skill_id, retained in TOMBSTONE_ROOT_FIELDS.items():
            row = self.runtime.execute("SELECT * FROM skills WHERE id=?", (skill_id,)).fetchone()
            self.assertIsNotNone(row)
            provenance = {
                item[0] for item in self.runtime.execute(
                    "SELECT field_name FROM shadowplay_v3_field_provenance "
                    "WHERE table_name='skills' AND row_id=?", (skill_id,)
                )
            }
            self.assertEqual(set(retained), provenance)
            for name, sql_type in schema.items():
                if name == "id" or name in retained:
                    continue
                expected = "" if "TEXT" in sql_type.upper() else 0
                self.assertEqual(expected, row[name], f"skills.{skill_id}.{name}")

    def test_no_historical_poison_scaffold_or_quarantine_remains(self) -> None:
        checks = {
            "buff_triggers": 88000001,
            "effects": 720,
            "buff_effects": 256,
        }
        for table, row_id in checks.items():
            self.assertEqual(
                0,
                self.runtime.execute(
                    f'SELECT COUNT(*) FROM "{table}" WHERE id=?', (row_id,)
                ).fetchone()[0],
            )
        self.assertEqual(
            [],
            list(self.runtime.execute(
                "SELECT skill_id FROM native_combat_skill_status "
                "WHERE ability_id=8 AND status!='enabled'"
            )),
        )
        server_hit_columns = {
            row[1] for row in self.runtime.execute(
                "PRAGMA table_info(native_server_hit_effects)"
            )
        }
        self.assertNotIn("triggered_skill_id", server_hit_columns)
        self.assertEqual(
            [(22266, 22271), (24093, 24095), (24235, 24236)],
            [tuple(row) for row in self.runtime.execute(
                "SELECT source_buff_id,impact_buff_id "
                "FROM native_server_hit_effects ORDER BY source_buff_id"
            )],
        )

    def test_ranged_admission_matches_complete_aa8_unit_requirements(self) -> None:
        self.assertEqual(
            [],
            list(self.runtime.execute(
                "SELECT kind_id,value1 FROM unit_reqs "
                "WHERE owner_type='Skill' AND owner_id=10481"
            )),
        )
        self.assertEqual(
            [(29, 0), (29, 2)],
            [tuple(row) for row in self.runtime.execute(
                "SELECT kind_id,value1 FROM unit_reqs "
                "WHERE owner_type='Skill' AND owner_id=12139 "
                "ORDER BY kind_id,value1"
            )],
        )
        provenance = [tuple(row) for row in self.runtime.execute(
            "SELECT value1,classification FROM shadowplay_v6_unit_req_provenance "
            "WHERE owner_type='Skill' AND owner_id=12139 ORDER BY value1"
        )]
        self.assertEqual(
            [(0, "legacy_3_0_corroborated"), (2, "client-native")],
            provenance,
        )
        self.assertEqual(
            [
                (9159, 38, 0), (9159, 38, 1), (9159, 38, 5),
                (21578, 38, 0), (21769, 38, 0), (21770, 38, 0),
            ],
            [tuple(row) for row in self.runtime.execute(
                "SELECT owner_id,kind_id,value1 FROM unit_reqs "
                "WHERE owner_type='PlotCondition' "
                "AND owner_id IN (9159,21578,21769,21770) "
                "ORDER BY owner_id,kind_id,value1"
            )],
        )
        self.assertEqual(6, self.manifest["format_version"])
        self.assertEqual(
            "E5083F4660698B1A4DCB13AEA37339C38ABD9D857261D9236E58EF9F47141031",
            self.manifest["sources"]["game11"]["sha256"],
        )

    def test_runtime_and_manifest_digest_match(self) -> None:
        self.assertEqual(self.manifest["output"]["sha256"], sha256_file(self.runtime_path))
        self.assertEqual(list(VISIBLE_ROOTS), [row[0] for row in self.runtime.execute(
            "SELECT id FROM skills WHERE ability_id=8 AND show=1 ORDER BY id"
        )])


if __name__ == "__main__":
    args = parse_args()
    ShadowplayNativeV3Tests.runtime_path = args.runtime.resolve()
    ShadowplayNativeV3Tests.knowledge_path = args.knowledge.resolve()
    ShadowplayNativeV3Tests.manifest_path = args.manifest.resolve()
    unittest.main(argv=[sys.argv[0], *args.unittest_args])
