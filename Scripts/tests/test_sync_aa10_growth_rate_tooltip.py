from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "SyncAa10GrowthRateTooltip.py"
SPEC = importlib.util.spec_from_file_location("growth_rate_sync", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def create_database(path: Path, delays: list[tuple[int, int]]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE doodad_func_growths "
            "(id INTEGER PRIMARY KEY, delay INTEGER NOT NULL, tip TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO doodad_func_growths (id, delay, tip) VALUES (?, ?, 'keep')",
            delays,
        )
        connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES (1, 'unchanged')")
        connection.commit()
    finally:
        connection.close()


class GrowthRateTooltipSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.world = self.root / "World.json"
        self.retail = self.root / "retail.sqlite3"
        self.client = self.root / "client.sqlite3"
        create_database(self.retail, [(1, 0), (2, 1_000), (3, 1_550)])
        create_database(self.client, [(1, 0), (2, 1_000), (3, 1_550)])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def set_rate(self, value: object) -> None:
        self.world.write_text(
            json.dumps({"World": {"GrowthRate": value}}), encoding="utf-8"
        )

    def delays(self) -> list[tuple[int, int]]:
        connection = sqlite3.connect(self.client)
        try:
            return connection.execute(
                "SELECT id, delay FROM doodad_func_growths ORDER BY id"
            ).fetchall()
        finally:
            connection.close()

    def test_recalculates_from_retail_baseline_and_is_idempotent(self) -> None:
        self.set_rate(100)
        first = MODULE.sync_database(self.world, self.retail, self.client, True)
        self.assertEqual(first.changed_rows, 2)
        self.assertEqual(self.delays(), [(1, 0), (2, 10), (3, 15)])

        second = MODULE.sync_database(self.world, self.retail, self.client, True)
        self.assertEqual(second.changed_rows, 0)

        self.set_rate(20)
        third = MODULE.sync_database(self.world, self.retail, self.client, True)
        self.assertEqual(third.changed_rows, 2)
        self.assertEqual(self.delays(), [(1, 0), (2, 50), (3, 77)])

        connection = sqlite3.connect(self.client)
        try:
            self.assertEqual(
                connection.execute("SELECT value FROM unrelated WHERE id = 1").fetchone(),
                ("unchanged",),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT DISTINCT tip FROM doodad_func_growths"
                ).fetchall(),
                [("keep",)],
            )
        finally:
            connection.close()

    def test_dry_run_does_not_modify_client(self) -> None:
        self.set_rate(100)
        before = MODULE.sha256(self.client)
        result = MODULE.sync_database(self.world, self.retail, self.client, False)
        self.assertEqual(result.changed_rows, 2)
        self.assertEqual(MODULE.sha256(self.client), before)

    def test_preserves_exact_size_for_pak_replacement(self) -> None:
        self.set_rate(100)
        with self.client.open("ab") as output:
            output.write(b"\0" * 8192)
        original_size = self.client.stat().st_size

        result = MODULE.sync_database(
            self.world, self.retail, self.client, True, preserve_size=True
        )

        self.assertTrue(result.size_preserved)
        self.assertEqual(self.client.stat().st_size, original_size)
        self.assertEqual(self.delays(), [(1, 0), (2, 10), (3, 15)])
        connection = sqlite3.connect(self.client)
        try:
            page_size = connection.execute("PRAGMA page_size").fetchone()[0]
            page_count = connection.execute("PRAGMA page_count").fetchone()[0]
            self.assertEqual(page_size * page_count, original_size)
            self.assertGreater(connection.execute("PRAGMA freelist_count").fetchone()[0], 0)
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")
        finally:
            connection.close()

        first_hash = MODULE.sha256(self.client)
        second = MODULE.sync_database(
            self.world, self.retail, self.client, True, preserve_size=True
        )
        self.assertEqual(second.changed_rows, 0)
        self.assertEqual(self.client.stat().st_size, original_size)
        self.assertEqual(MODULE.sha256(self.client), first_hash)

    def test_rejects_invalid_rate(self) -> None:
        self.set_rate(0)
        with self.assertRaisesRegex(RuntimeError, "must be between"):
            MODULE.sync_database(self.world, self.retail, self.client, True)

    def test_rejects_different_growth_row_identity(self) -> None:
        self.set_rate(100)
        connection = sqlite3.connect(self.client)
        try:
            connection.execute("DELETE FROM doodad_func_growths WHERE id = 3")
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(RuntimeError, "row identity differs"):
            MODULE.sync_database(self.world, self.retail, self.client, True)


if __name__ == "__main__":
    unittest.main()
