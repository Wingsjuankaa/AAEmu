"""Read-only AA10 house 437 door/window graph audit. Outputs evidence, not runtime data."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


ROOT = Path("E:/AAEmu/rama_10")
SOURCES = {
    "authoritative_full": ROOT / "data/sqlite/authoritative/game_decrypted.sqlite3",
    "retail_compact": ROOT / "client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3",
    "server_observed_compact": ROOT / "server/AAEmu/.server_files/AAEmu.Game/Data/compact.sqlite3",
}
GROUPS = "select id from doodad_func_groups where doodad_almighty_id in (4566,4568)"
QUERIES = {
    "bindings": "select * from housing_binding_doodads where housing_id=437 order by id",
    "templates": "select * from doodad_almighties where id in (4566,4568) order by id",
    "groups": "select * from doodad_func_groups where doodad_almighty_id in (4566,4568) order by id",
    "phase_functions": f"select * from doodad_phase_funcs where doodad_func_group_id in ({GROUPS}) order by id",
    "use_functions": f"select * from doodad_funcs where doodad_func_group_id in ({GROUPS}) order by id",
    "timers": f"""select * from doodad_func_timers where id in
        (select actual_func_id from doodad_phase_funcs where actual_func_type='DoodadFuncTimer'
         and doodad_func_group_id in ({GROUPS})) order by id""",
    "animations": f"""select * from doodad_func_animates where id in
        (select actual_func_id from doodad_phase_funcs where actual_func_type='DoodadFuncAnimate'
         and doodad_func_group_id in ({GROUPS})) order by id""",
}


def audit(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        db.row_factory = sqlite3.Row
        checks = {check: [row[0] for row in db.execute("PRAGMA " + check)]
                  for check in ("quick_check", "integrity_check")}
        if any(value != ["ok"] for value in checks.values()):
            raise ValueError((path, checks))
        rows = {name: [dict(row) for row in db.execute(query)] for name, query in QUERIES.items()}
    stable = {str(group): [row for row in rows["phase_functions"]
                          if row["doodad_func_group_id"] == group] for group in (11165, 11173)}
    return {"path": str(path), "sha256": digest, "checks": checks, "rows": rows,
            "stable_open_phase_functions": stable}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"scope": {"housing_template": 437, "doodads": [4566, 4568]},
              "queries": QUERIES, "sources": {name: audit(path) for name, path in SOURCES.items()},
              "native_restart_persistence": "unresolved: a loader and force_db_save=false do not prove the World save policy"}
    for source in result["sources"].values():
        for rows in source["stable_open_phase_functions"].values():
            if not rows or any(row["actual_func_type"] != "DoodadFuncAnimate" for row in rows):
                raise ValueError("Stable open graph changed; re-investigate timers and transitions")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      "sources": {name: {"sha256": value["sha256"], "checks": value["checks"]}
                                  for name, value in result["sources"].items()}}, indent=2))


if __name__ == "__main__":
    main()
