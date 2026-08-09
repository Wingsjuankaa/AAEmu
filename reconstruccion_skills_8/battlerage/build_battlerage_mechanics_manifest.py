#!/usr/bin/env python3
"""Certify two isolated Battlerage Mechanics Lab matrices."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIOS = ROOT / "mechanics-lab" / "scenarios"
DEFAULT_OUTPUT = (
    ROOT
    / "reconstruccion_skills_8"
    / "battlerage"
    / "generated"
    / "battlerage-v2-mechanics-certification.json"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def load_result(run: Path, scenario: str) -> dict:
    path = run / scenario / f"{scenario}.result.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    names = sorted(path.stem for path in args.scenarios.glob("battlerage_*.json"))
    if len(names) != 24:
        raise RuntimeError(f"expected 24 Battlerage scenarios, found {len(names)}")

    rows = []
    compact_hashes = set()
    for name in names:
        first = load_result(args.run_a, name)
        second = load_result(args.run_b, name)
        if not first["Passed"] or not second["Passed"]:
            raise RuntimeError(f"scenario failed: {name}")
        if first["ResultSha256"] != second["ResultSha256"]:
            raise RuntimeError(
                f"non-deterministic result: {name}: "
                f"{first['ResultSha256']} != {second['ResultSha256']}"
            )
        if first["ScenarioSha256"] != second["ScenarioSha256"]:
            raise RuntimeError(f"scenario input mismatch: {name}")
        compact_hashes.update((first["CompactSha256"], second["CompactSha256"]))
        rows.append(
            {
                "scenario": name,
                "scenario_sha256": first["ScenarioSha256"],
                "result_sha256": first["ResultSha256"],
                "packet_count": len(first["Packets"]),
                "validation_count": len(first["Validations"]),
            }
        )

    if len(compact_hashes) != 1:
        raise RuntimeError(f"matrix used different compacts: {sorted(compact_hashes)}")

    payload = {
        "format_version": 1,
        "ability": "Battlerage",
        "client": "ArcheAge Kakao 8.0.3.12 r558734",
        "compact_sha256": next(iter(compact_hashes)),
        "scenario_count": len(rows),
        "passed_run_a": len(rows),
        "passed_run_b": len(rows),
        "identical_result_hashes": len(rows),
        "scenarios": rows,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["certification_sha256"] = sha256_bytes(canonical.encode("utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    print(payload["certification_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
