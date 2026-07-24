#!/usr/bin/env python3
"""Activate the observed AA8 deterministic socket family.

The public Kakao 8.0 client contains the short item_socket_chances layout
(id, fail_break, cost_ratio); socket0..socket9 are server-private.  This
builder therefore does not invent probability rows.  It only marks chance
set 7 as deterministic, matching the behavior observed with the local
8.0.3.12 client for the modern Fireglow/Copperglow/Waveglow/Galeglow/
Earthglow/Sunglow Lunagem family.  Its increasing price remains governed by
AA8 FormulaKind 38 and item_used_socket.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path


DETERMINISTIC_CHANCE_SET_IDS = (7,)
PROVENANCE = "server_derived"
EVIDENCE = (
    "Observed with Kakao 8.0.3.12 r558734 local client: modern Lunagem "
    "chance set 7 has a deterministic socket result; progression is the "
    "AA8 gold cost by item level and occupied socket count."
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def build(base: Path, destination: Path) -> dict:
    shutil.copy2(base, destination)
    connection = sqlite3.connect(destination)
    try:
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("BEGIN IMMEDIATE")

        placeholders = ",".join("?" for _ in DETERMINISTIC_CHANCE_SET_IDS)
        rows = connection.execute(
            f"""
            SELECT item_id, item_socket_chance_id
            FROM item_sockets
            WHERE item_socket_chance_id IN ({placeholders})
            ORDER BY item_id
            """,
            DETERMINISTIC_CHANCE_SET_IDS,
        ).fetchall()
        if not rows:
            raise RuntimeError("No AA8 chance-set 7 Lunagem definitions found")

        connection.executemany(
            """
            INSERT INTO aaemu_item_socket_policies
                (item_id, guaranteed, provenance, evidence)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                guaranteed = excluded.guaranteed,
                provenance = excluded.provenance,
                evidence = excluded.evidence
            """,
            [(int(row[0]), PROVENANCE, EVIDENCE) for row in rows],
        )

        formula = connection.execute(
            "SELECT formula FROM formulas WHERE id = 38"
        ).fetchone()
        if formula is None:
            raise RuntimeError("AA8 ItemSocketingCost formula 38 is absent")
        formula_text = str(formula[0])
        for variable in (
            "item_level",
            "socket_item_level",
            "item_used_socket",
            "item_socketing_cost_mul",
        ):
            if variable not in formula_text:
                raise RuntimeError(
                    f"AA8 socket cost formula is missing {variable}"
                )

        connection.commit()
        connection.execute("VACUUM")
        return {
            "activated_item_count": len(rows),
            "activated_item_ids": [int(row[0]) for row in rows],
            "chance_set_ids": list(DETERMINISTIC_CHANCE_SET_IDS),
            "formula_id": 38,
            "formula": formula_text,
            "provenance": PROVENANCE,
            "evidence": EVIDENCE,
        }
    finally:
        connection.close()


def validate(path: Path, expected_count: int) -> dict:
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro",
        uri=True,
    )
    try:
        quick = connection.execute("PRAGMA quick_check").fetchone()[0]
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM item_sockets s
            JOIN aaemu_item_socket_policies p ON p.item_id = s.item_id
            WHERE s.item_socket_chance_id = 7
              AND p.guaranteed = 1
              AND p.provenance = ?
            """,
            (PROVENANCE,),
        ).fetchone()[0]
        unresolved = connection.execute(
            """
            SELECT COUNT(*)
            FROM item_socket_chances
            WHERE id NOT IN (7)
              AND socket0 IS NULL
            """
        ).fetchone()[0]
        if quick != "ok" or integrity != "ok":
            raise RuntimeError(
                f"SQLite validation failed: quick={quick}, integrity={integrity}"
            )
        if int(count) != expected_count:
            raise RuntimeError(
                f"Activated {count} policies, expected {expected_count}"
            )
        return {
            "quick_check": quick,
            "integrity_check": integrity,
            "activated_policy_count": int(count),
            "other_private_chance_sets_still_gated": int(unresolved),
        }
    finally:
        connection.close()


def main() -> None:
    options = arguments()
    source_hash = sha256(options.base_runtime)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.manifest.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="aa8-socket-b12-") as temp:
        first = Path(temp) / "first.sqlite3"
        second = Path(temp) / "second.sqlite3"
        build_info = build(options.base_runtime, first)
        second_info = build(options.base_runtime, second)
        first_hash = sha256(first)
        second_hash = sha256(second)
        if first_hash != second_hash or build_info != second_info:
            raise RuntimeError("B12 socket runtime build is not deterministic")

        validation = validate(first, build_info["activated_item_count"])
        shutil.copy2(first, options.output)

    manifest = {
        "phase": "B12-native-socket-execution",
        "base_runtime": str(options.base_runtime),
        "base_runtime_sha256": source_hash,
        "output": str(options.output),
        "output_sha256": sha256(options.output),
        "deterministic_build_sha256": first_hash,
        "build": build_info,
        "validation": validation,
        "blocked": [
            "socket0..socket9 for historical/probabilistic chance sets are "
            "server-private and remain NULL",
            "probabilistic failure and fail_break are not activated without "
            "a native AA8 server data source",
        ],
    }
    options.manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
