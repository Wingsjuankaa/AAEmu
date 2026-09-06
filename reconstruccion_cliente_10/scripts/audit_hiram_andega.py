"""Read-only r575 Joining Forces actor closure; uses PakDoodadScan placements.csv."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path("E:/AAEmu/rama_10")
OUT = ROOT / "forensics/output/aa10-client-forensics/hiram-andega-frontier"
QUERIES = {
    "quests": "SELECT id,category_id,chapter_idx,race FROM quest_contexts WHERE id IN (9174,9175) ORDER BY id",
    "components": "SELECT id,quest_context_id,component_kind_id FROM quest_components WHERE quest_context_id IN (9174,9175) ORDER BY id",
    "acts": "SELECT * FROM quest_acts WHERE quest_component_id IN (SELECT id FROM quest_components WHERE quest_context_id IN (9174,9175)) ORDER BY id",
    "report": "SELECT * FROM quest_act_con_report_doodads WHERE id=88",
    "offer": "SELECT * FROM quest_act_con_accept_doodads WHERE id=618",
    "actor": "SELECT id,model,client_doodad,once_one_man FROM doodad_almighties WHERE id=13376",
    "groups": "SELECT id,model,doodad_func_group_kind_id FROM doodad_func_groups WHERE doodad_almighty_id=13376 ORDER BY id",
    "functions": "SELECT * FROM doodad_funcs WHERE doodad_func_group_id IN (38575,38939) ORDER BY id",
    "phase_functions": "SELECT * FROM doodad_phase_funcs WHERE doodad_func_group_id IN (38575,38939) ORDER BY id",
    "reactions": "SELECT * FROM doodad_func_quest_reacts WHERE id IN (90,108) ORDER BY id",
    "models": "SELECT * FROM doodad_func_model_changes WHERE id IN (10,94) ORDER BY id",
    "quest_functions": "SELECT * FROM doodad_func_quests WHERE id IN (1111,1112,1192,1409) ORDER BY id",
}


def sha256(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    result = {"queries": QUERIES, "databases": {}}
    for label, relative in {
        "full": "data/sqlite/authoritative/game_decrypted.sqlite3",
        "compact": "client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3",
    }.items():
        path = ROOT / relative
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            rows = {name: [dict(r) for r in db.execute(q)] for name, q in QUERIES.items()}
        result["databases"][label] = {"path": str(path), "sha256": sha256(path), "rows": rows}
    assert result["databases"]["full"]["rows"] == result["databases"]["compact"]["rows"]
    placement_path = OUT / "placements.csv"
    placements = list(csv.DictReader(placement_path.read_text(encoding="utf-8-sig").splitlines()))
    native = [r for r in placements if int(r["doodad_id"]) == 13376]
    assert len(native) == 1
    overlay_path = ROOT / "server/AAEmu/AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_client_quest_proxies.json"
    overlay = json.loads(overlay_path.read_text(encoding="utf-8-sig"))
    actors = [r for r in overlay if r["UnitId"] == 13376]
    assert len(actors) == 1
    actor = actors[0]
    assert actor["FuncGroupId"] == 38575
    for key in ("X", "Y", "Z"):
        assert abs(actor["Position"][key] - float(native[0][key.lower()])) < 0.001
    assert abs(actor["Position"]["Yaw"] - float(native[0]["yaw_degrees"])) < 0.001
    assert actor["Scale"] == float(native[0]["scale"]) == 1
    result.update(status="pass", placements=placements, placements_sha256=sha256(placement_path),
                  overlay_sha256=sha256(overlay_path), retail_acceptance="pending")
    (OUT / "native-contract.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS: full/compact agree; Andega placement and Start38575 match r575")


if __name__ == "__main__":
    main()
