from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ..ghidra_sql_inventory import (
    build_all_sql_tasks,
    build_master_sql_call_sequence,
)


class GhidraSqlInventoryTests(unittest.TestCase):
    def test_builds_deduplicated_select_tasks_and_master_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "sql.json"
            manifest.write_text(
                json.dumps(
                    {
                        "binaries": [
                            {
                                "path": "client/bin64/x2game.dll",
                                "statements": [
                                    {
                                        "offset": 16,
                                        "tables": ["tags"],
                                        "value": "SELECT id, name FROM tags",
                                    },
                                    {
                                        "offset": 32,
                                        "tables": ["tags"],
                                        "value": "SELECT id, name FROM tags",
                                    },
                                    {
                                        "offset": 48,
                                        "tables": [],
                                        "value": "not a query",
                                    },
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            tasks = root / "tasks.tsv"
            task_summary = build_all_sql_tasks(manifest, tasks)
            self.assertEqual(task_summary["tasks"], 1)
            self.assertEqual(
                tasks.read_text(encoding="utf-8"),
                "tags@10\tSELECT id, name FROM tags\n",
            )

            loaders = root / "loaders.txt"
            loaders.write_text(
                "\n".join(
                    (
                        "TASK\ttags@10",
                        "SQL\tSELECT id, name FROM tags",
                        "FUNCTION_BEGIN\tFUN_1234abcd\t1234abcd",
                    )
                ),
                encoding="utf-8",
            )
            master = root / "master.txt"
            master.write_text(
                "\n".join(
                    (
                        "===== FUN_399005a0 @ 399005a0 =====",
                        "FUN_00000000();",
                        "FUN_1234abcd();",
                        "===== FUN_11111111 @ 11111111 =====",
                        "FUN_1234abcd();",
                    )
                ),
                encoding="utf-8",
            )
            sequence = root / "sequence.json"
            sequence_summary = build_master_sql_call_sequence(
                master,
                loaders,
                sequence,
            )
            self.assertEqual(sequence_summary["mapped_calls"], 1)
            document = json.loads(sequence.read_text(encoding="utf-8"))
            self.assertEqual(document[0]["function"], "FUN_1234abcd")
            self.assertEqual(document[0]["tasks"][0]["task"], "tags@10")


if __name__ == "__main__":
    unittest.main()
