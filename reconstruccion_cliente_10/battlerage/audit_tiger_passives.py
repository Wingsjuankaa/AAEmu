"""Read-only AA10 evidence snapshot; does not assert native scheduler semantics."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


QUERIES = {
    "tiger_skill": "SELECT * FROM skills WHERE id=36448",
    "tiger_events": "SELECT * FROM plot_events WHERE plot_id=2922",
    "tiger_edges": "SELECT * FROM plot_next_events WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=2922)",
    "tiger_effects": "SELECT * FROM plot_effects WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=2922)",
    "controllers": "SELECT * FROM skill_controllers WHERE id IN (11024,11025,11026,11067,11068)",
    "animations": "SELECT * FROM anims WHERE id IN (46,175)",
    "passives": "SELECT * FROM passive_buffs WHERE id IN (32,245,92,29,295,244)",
    "combat_buffs": "SELECT * FROM combat_buffs WHERE id IN (23,24,51)",
    "buffs": "SELECT * FROM buffs WHERE id IN (2610,2611,7542,7543,2621,2622,811,22277,831,7544,25650,25987)",
    "triggers": "SELECT * FROM buff_triggers WHERE buff_id IN (2611,2622,22277,25650,25987)",
    "resources": "SELECT * FROM combat_resources WHERE id IN (1,7,11,17,26,27)",
    "resource_modifiers": "SELECT * FROM unit_modifiers WHERE owner_type='CombatResource'",
    "buff_modifiers": "SELECT * FROM unit_modifiers WHERE owner_type='Buff' AND owner_id IN (7543,7544,25987)",
    "ranged_parry_tag": "SELECT * FROM const_tags WHERE name='ranged_parry'",
}


def snapshot(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        return {name: sorted((dict(row) for row in connection.execute(query)),
                            key=lambda row: json.dumps(row, sort_keys=True))
                for name, query in QUERIES.items()}


def source_info(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "sha256": digest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    full, runtime = snapshot(args.full), snapshot(args.runtime)
    result = {
        "sources": {name: source_info(path)
                    for name, path in (("full", args.full), ("runtime", args.runtime))},
        "parity": {name: full[name] == runtime[name] for name in QUERIES},
        "full": full,
        "runtime": runtime,
        "limits": ["Equality of data does not establish native timing or live client acceptance.",
                   "No database, client file, character or runtime process is modified."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"parity": result["parity"],
                      "rows": {name: len(rows) for name, rows in full.items()}}))
    if not all(result["parity"].values()):
        raise SystemExit("Full/runtime data differ; inspect snapshot before drawing conclusions.")


if __name__ == "__main__":
    main()
