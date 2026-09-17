"""Read-only r575 audit for jump AI and caught-fish backpack routing."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def audit(path):
    path = Path(path).resolve()
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    def rows(query):
        return [dict(r) for r in con.execute(query)]
    result = {
        "path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "skills": rows("SELECT id,target_type_id,target_selection_id,min_range,max_range,plot_id "
                       "FROM skills WHERE id IN (21096,21097,21098,21099,21289,21322) ORDER BY id"),
        "requirements": rows("SELECT * FROM unit_reqs WHERE owner_type='Skill' "
                             "AND owner_id IN (21096,21097,21098,21099,21289) ORDER BY id"),
        "fish_loot": rows("SELECT n.id AS npc_id,n.npc_ai_param_id,l.loot_pack_id,l.item_id,"
                          "b.backpack_type_id,i.bind_id,fd.min_weight,fd.max_weight,fd.min_length,fd.max_length "
                          "FROM npcs n JOIN loot_pack_dropping_npcs d ON d.npc_id=n.id "
                          "JOIN loots l ON l.loot_pack_id=d.loot_pack_id "
                          "JOIN items i ON i.id=l.item_id JOIN item_backpacks b ON b.item_id=i.id "
                          "JOIN fish_details fd ON fd.item_id=i.id WHERE n.id IN (12979,13093)"),
        "ai": rows("SELECT id,ai_param FROM npc_ai_params WHERE id IN (3230,3282) ORDER BY id")
              if "npc_ai_params" in tables else None,
        "ai_table_present": "npc_ai_params" in tables
    }
    con.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("databases", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps([audit(p) for p in args.databases],
                                          ensure_ascii=False, indent=2), encoding="utf-8")
