from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "PatchAa10ItemStackLimit.py"
SPEC = importlib.util.spec_from_file_location("patch_aa10_item_stack_limit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
PATCHER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PATCHER
SPEC.loader.exec_module(PATCHER)


def create_database(path: Path, limits: list[tuple[int, int]]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE items ("
            "id INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL, "
            "max_stack_size INTEGER NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO items (id, name, max_stack_size) VALUES (?, 'keep', ?)",
            limits,
        )
        connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO unrelated VALUES (1, 'unchanged')")
        connection.commit()
    finally:
        connection.close()


class ItemStackLimitPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / "compact.sqlite3"
        create_database(
            self.database,
            [(10, 1_000), (11, 1_000), (20, 9_999), (21, 9_999), (30, 100), (40, 1)],
        )
        profile = PATCHER.StackProfile(
            name="fixture",
            retail_1000_count=2,
            retail_1000_ids_sha256=PATCHER.ids_sha256([10, 11]),
            retail_9999_count=2,
            retail_9999_ids_sha256=PATCHER.ids_sha256([20, 21]),
            combined_count=4,
            combined_ids_sha256=PATCHER.ids_sha256([10, 11, 20, 21]),
        )
        self.profiles = mock.patch.object(PATCHER, "PROFILES", (profile,))
        self.profiles.start()

    def tearDown(self) -> None:
        self.profiles.stop()
        self.temporary.cleanup()

    def limits(self) -> list[tuple[int, int]]:
        connection = sqlite3.connect(self.database)
        try:
            return connection.execute(
                "SELECT id, max_stack_size FROM items ORDER BY id"
            ).fetchall()
        finally:
            connection.close()

    def test_applies_only_to_audited_retail_rows_and_is_idempotent(self) -> None:
        original_size = self.database.stat().st_size
        first = PATCHER.patch_database(self.database, True)

        self.assertEqual(first.changed_rows, 4)
        self.assertEqual(first.target_rows, 4)
        self.assertEqual(self.database.stat().st_size, original_size)
        self.assertEqual(
            self.limits(),
            [(10, 99_999), (11, 99_999), (20, 99_999), (21, 99_999), (30, 100), (40, 1)],
        )

        first_hash = PATCHER.sha256(self.database)
        second = PATCHER.patch_database(self.database, True)
        self.assertEqual(second.changed_rows, 0)
        self.assertEqual(PATCHER.sha256(self.database), first_hash)

    def test_dry_run_does_not_modify_database(self) -> None:
        before = PATCHER.sha256(self.database)
        result = PATCHER.patch_database(self.database, False)
        self.assertEqual(result.changed_rows, 4)
        self.assertEqual(PATCHER.sha256(self.database), before)

    def test_rejects_partial_patch(self) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE items SET max_stack_size = 99999 WHERE id = 10"
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(RuntimeError, "partial stack patch"):
            PATCHER.patch_database(self.database, False)

    def test_rejects_unknown_target_identity(self) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "INSERT INTO items (id, name, max_stack_size) VALUES (25, 'drift', 9999)"
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(RuntimeError, "unknown AA10 stack row identity"):
            PATCHER.patch_database(self.database, False)

    def test_upgrades_previous_1000_only_patch(self) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "UPDATE items SET max_stack_size = 99999 WHERE max_stack_size = 1000"
            )
            connection.commit()
        finally:
            connection.close()

        result = PATCHER.patch_database(self.database, True)
        self.assertEqual(result.changed_rows, 2)
        self.assertEqual(
            self.limits(),
            [(10, 99_999), (11, 99_999), (20, 99_999), (21, 99_999), (30, 100), (40, 1)],
        )


if __name__ == "__main__":
    unittest.main()
