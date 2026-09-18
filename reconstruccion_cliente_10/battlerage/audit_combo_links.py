"""Read-only r575 Combo evidence; no client or database mutations."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def extract(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("""
            SELECT se.*, s.value1, s.value2, k.casting_time, k.channeling_time,
                   k.cooldown_time, k.custom_gcd, k.default_gcd, k.ignore_global_cooldown
            FROM skill_effects se
            JOIN effects e ON e.id=se.effect_id
            JOIN special_effects s ON s.id=e.actual_id
            JOIN skills k ON k.id=se.skill_id
            WHERE e.actual_type='SpecialEffect' AND s.special_effect_type_id=48
              AND se.skill_id IN (18132,18134,13282,32040,36401,36402,36404,36405)
            ORDER BY se.skill_id,se.id
        """)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("full", type=Path)
    parser.add_argument("runtime", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    full, runtime = extract(args.full), extract(args.runtime)
    expected_sources = {18132, 18134, 13282, 32040, 36401, 36402, 36404, 36405}
    complete = len(full) == 8 and {row["skill_id"] for row in full} == expected_sources
    result = {
        "full_sha256": sha256(args.full),
        "runtime_sha256": sha256(args.runtime),
        "rows_equal": full == runtime,
        "complete": complete,
        "full": full,
        "runtime": runtime,
    }
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Combo links: {len(full)}; complete: {complete}; full/runtime identical: {full == runtime}")
    if not complete or full != runtime:
        raise SystemExit(1)
