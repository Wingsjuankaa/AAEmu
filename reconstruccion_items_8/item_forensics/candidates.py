from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import ForensicsConfig
from .db import open_database
from .families import FAMILIES
from .util import (
    canonical_json,
    sha256_file,
    write_text_atomic,
)


CANDIDATE_DDL = """CREATE TABLE IF NOT EXISTS aaemu_item_forensics_candidates (
    item_id INTEGER PRIMARY KEY,
    family TEXT NOT NULL,
    source_database_sha256 TEXT NOT NULL,
    readiness TEXT NOT NULL,
    provenance TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aaemu_item_capability_coverage (
    item_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    state TEXT NOT NULL,
    blocker_code TEXT NOT NULL,
    evidence TEXT NOT NULL,
    PRIMARY KEY(item_id, dimension)
);
"""


BUILDER_TEMPLATE = r'''#!/usr/bin/env python3
"""Build a review-only AA8 item family candidate.

This builder deliberately does not update aaemu_item_definition_coverage and
does not activate gameplay. It copies the selected base runtime and adds only
an audit table, so a reviewer can inspect the candidate closure safely.
"""

import argparse
import json
import shutil
import sqlite3
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.resolve() == args.base_runtime.resolve():
        raise ValueError("Output must not overwrite the base runtime")
    manifest = json.loads(
        (Path(__file__).resolve().parent / "candidate-manifest.json")
        .read_text(encoding="utf-8")
    )
    if manifest["deployable"]:
        raise RuntimeError("A forensics candidate must never be deployable")
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    shutil.copy2(args.base_runtime, temporary)
    connection = sqlite3.connect(temporary)
    try:
        connection.executescript("""{ddl}""")
        connection.execute("DELETE FROM aaemu_item_forensics_candidates")
        connection.execute("DELETE FROM aaemu_item_capability_coverage")
        connection.executemany(
            "INSERT INTO aaemu_item_forensics_candidates VALUES (?,?,?,?,?)",
            [
                (
                    item["item_id"],
                    manifest["family"],
                    manifest["source_database_sha256"],
                    item["readiness"],
                    item["provenance"],
                )
                for item in manifest["items"]
            ],
        )
        connection.executemany(
            "INSERT INTO aaemu_item_capability_coverage VALUES (?,?,?,?,?)",
            [
                (
                    item["item_id"],
                    capability["dimension"],
                    capability["state"],
                    capability["blocker_code"],
                    capability["evidence"],
                )
                for item in manifest["items"]
                for capability in item["capabilities"]
            ],
        )
        connection.commit()
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise RuntimeError("quick_check failed")
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("integrity_check failed")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    temporary.replace(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''.replace("{ddl}", CANDIDATE_DDL.replace('"""', r'\"\"\"'))


def _readiness(capabilities: list[dict[str, Any]]) -> str:
    states = {value["dimension"]: value["state"] for value in capabilities}
    if any(value == "blocked" for value in states.values()):
        return "blocked_native_evidence"
    if states.get("descriptor") == "missing":
        return "catalog_only"
    if states.get("descriptor") == "confirmed" and all(
        states.get(name) in ("confirmed", "not_applicable")
        for name in ("dependency_closure", "backend", "protocol", "persistence", "validation")
    ):
        return "native_complete"
    if states.get("descriptor") == "confirmed":
        return "candidate_data_complete"
    return "candidate_unresolved"


def generate_family(config: ForensicsConfig, family_name: str) -> dict[str, Any]:
    database_sha = sha256_file(config.database)
    connection = open_database(config.database, writable=False)
    try:
        rows = list(
            connection.execute(
                """
                SELECT * FROM item_summary WHERE family=?
                ORDER BY item_id
                """,
                (family_name,),
            )
        )
        if not rows:
            available = [
                str(row[0])
                for row in connection.execute(
                    "SELECT DISTINCT family FROM item_summary ORDER BY family"
                )
            ]
            raise KeyError(
                f"Unknown or empty family {family_name!r}; available: "
                + ", ".join(available)
            )
        items: list[dict[str, Any]] = []
        native_rows: list[dict[str, Any]] = []
        backend_contract: list[dict[str, Any]] = []
        for row in rows:
            item_id = int(row["item_id"])
            capabilities = [
                dict(value)
                for value in connection.execute(
                    """
                    SELECT dimension,state,capability,evidence_kind,evidence_json
                    FROM server_capabilities WHERE item_id=?
                    ORDER BY dimension
                    """,
                    (item_id,),
                )
            ]
            runtime = connection.execute(
                "SELECT * FROM runtime_coverage WHERE item_id=?",
                (item_id,),
            ).fetchone()
            descriptor_rows = [
                dict(value)
                for value in connection.execute(
                    """
                    SELECT table_name,descriptor_json,state,provenance,evidence_json
                    FROM descriptors WHERE item_id=? ORDER BY table_name
                    """,
                    (item_id,),
                )
            ]
            readiness = _readiness(capabilities)
            provenance = str(runtime["provenance"]) if runtime else ""
            items.append(
                {
                    "capabilities": [
                        {
                            "blocker_code": next(
                                (
                                    gap["blocker_code"]
                                    for gap in connection.execute(
                                        """
                                        SELECT blocker_code FROM gaps
                                        WHERE item_id=? AND dimension=?
                                        ORDER BY severity DESC,blocker_code LIMIT 1
                                        """,
                                        (item_id, value["dimension"]),
                                    )
                                ),
                                "",
                            ),
                            "dimension": value["dimension"],
                            "evidence": value["evidence_json"],
                            "state": value["state"],
                        }
                        for value in capabilities
                    ],
                    "item_id": item_id,
                    "readiness": readiness,
                    "runtime_coverage": (
                        str(runtime["coverage"]) if runtime else "unknown"
                    ),
                    "provenance": provenance,
                }
            )
            client = connection.execute(
                "SELECT client_row_json FROM items WHERE item_id=?",
                (item_id,),
            ).fetchone()
            native_rows.append(
                {
                    "item_id": item_id,
                    "items": json.loads(str(client[0])),
                    "descriptors": [
                        {
                            **value,
                            "descriptor": json.loads(value["descriptor_json"]),
                            "evidence": json.loads(value["evidence_json"]),
                        }
                        for value in descriptor_rows
                        if value["state"] == "confirmed"
                        and (
                            "client_compact_8" in value["provenance"]
                            or "game11_native" in value["provenance"]
                        )
                    ],
                }
            )
            backend_contract.append(
                {
                    "item_id": item_id,
                    "capabilities": [
                        {
                            "dimension": value["dimension"],
                            "state": value["state"],
                            "required_behavior": value["capability"],
                            "evidence_kind": value["evidence_kind"],
                        }
                        for value in capabilities
                    ],
                }
            )
        family = next(
            (value for value in FAMILIES.values() if value.name == family_name),
            None,
        )
        queue_key = {
            "native_data_complete": all(
                item["readiness"] in ("native_complete", "candidate_data_complete")
                for item in items
            ),
            "protocol_known": bool(family and family.protocol_known),
            "non_destructive": bool(family and not family.destructive),
            "non_economic": bool(family and not family.economic),
            "items_unlocked": len(items),
        }
    finally:
        connection.close()

    candidate_root = config.output_dir / "candidates"
    output = candidate_root / f"{family_name}-{database_sha[:12].lower()}"
    output.mkdir(parents=True, exist_ok=True)
    native_rows_path = output / "native-rows.json"
    contract_path = output / "backend-contract.json"
    fixtures_path = output / "test-fixtures.json"
    ddl_path = output / "candidate-schema.sql"
    builder_path = output / "build_candidate.py"
    warning_path = output / "DO_NOT_DEPLOY.txt"
    write_text_atomic(native_rows_path, canonical_json(native_rows, pretty=True))
    write_text_atomic(contract_path, canonical_json(backend_contract, pretty=True))
    write_text_atomic(
        fixtures_path,
        canonical_json(
            {
                "acceptance": [
                    "definition load",
                    "creation without generic fallback",
                    "request/result protocol",
                    "atomic mutation and rollback",
                    "immediate client refresh",
                    "rapid repeated action",
                    "persistence after relog",
                    "observer visibility when applicable",
                ],
                "item_ids": [item["item_id"] for item in items],
            },
            pretty=True,
        ),
    )
    write_text_atomic(ddl_path, CANDIDATE_DDL)
    write_text_atomic(builder_path, BUILDER_TEMPLATE)
    write_text_atomic(
        warning_path,
        (
            "REVIEW-ONLY AA8 FORENSICS CANDIDATE\n"
            "This package does not activate item definitions or gameplay.\n"
            "Do not deploy it as a server runtime.\n"
        ),
    )
    payload_files = (
        backend_contract and [contract_path] or []
    ) + [ddl_path, builder_path, native_rows_path, fixtures_path, warning_path]
    manifest = {
        "authority": "Kakao 8.0.3.12 r558734",
        "deployable": False,
        "family": family_name,
        "files": {
            path.name: sha256_file(path)
            for path in sorted(payload_files, key=lambda value: value.name)
        },
        "historical_3_0_gameplay_rows": 0,
        "items": items,
        "queue_key": queue_key,
        "source_database": config.database.resolve().as_posix(),
        "source_database_sha256": database_sha,
    }
    manifest_path = output / "candidate-manifest.json"
    write_text_atomic(manifest_path, canonical_json(manifest, pretty=True))
    return {
        "directory": output,
        "manifest": manifest_path,
        "items": len(items),
        "readiness": dict(
            sorted(
                {
                    state: sum(1 for item in items if item["readiness"] == state)
                    for state in {item["readiness"] for item in items}
                }.items()
            )
        ),
    }


def verify_candidate(path: Path) -> dict[str, Any]:
    root = path.resolve()
    manifest_path = root if root.name == "candidate-manifest.json" else root / "candidate-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if manifest.get("deployable") is not False:
        failures.append("deployable must be false")
    if int(manifest.get("historical_3_0_gameplay_rows", -1)) != 0:
        failures.append("historical_3_0_gameplay_rows must be zero")
    for name, expected in sorted(manifest.get("files", {}).items()):
        file_path = manifest_path.parent / name
        if not file_path.is_file():
            failures.append(f"missing file: {name}")
            continue
        actual = sha256_file(file_path)
        if actual != expected:
            failures.append(f"sha256 mismatch: {name}")
        if file_path.suffix in (".sqlite", ".sqlite3", ".db"):
            connection = sqlite3.connect(
                f"file:{file_path.as_posix()}?mode=ro",
                uri=True,
            )
            try:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    failures.append(f"quick_check failed: {name}")
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    failures.append(f"integrity_check failed: {name}")
            finally:
                connection.close()
    return {
        "candidate": manifest_path.parent,
        "files": len(manifest.get("files", {})),
        "failures": failures,
        "ok": not failures,
    }
