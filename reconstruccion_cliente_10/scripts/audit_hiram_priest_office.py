"""Read-only r575 quest 9173 closure; requires PakDoodadScan placements.csv."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path("E:/AAEmu/rama_10")
REPO = ROOT / "server/AAEmu"
OUT = ROOT / "forensics/output/aa10-client-forensics/hiram-priest-office-frontier"
DATABASES = {
    "full": ROOT / "data/sqlite/authoritative/game_decrypted.sqlite3",
    "compact": ROOT / "client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3",
}
QUERIES = {
    "quest": "SELECT id, category_id, chapter_idx, race, selective FROM quest_contexts WHERE id=9173",
    "components": "SELECT id, component_kind_id, next_component FROM quest_components WHERE quest_context_id=9173 ORDER BY id",
    "acts": "SELECT * FROM quest_acts WHERE quest_component_id IN (39848,39849,39850,39851,39998) ORDER BY id",
    "sphere_objective": "SELECT * FROM quest_act_obj_spheres WHERE id=754",
    "talk_objective": "SELECT * FROM quest_act_obj_effect_fires WHERE id=80",
    "report": "SELECT * FROM quest_act_con_report_doodads WHERE id=87",
    "effect": "SELECT * FROM effects WHERE id=72642",
    "interaction": "SELECT * FROM interaction_effects WHERE id=7306",
    "skill_effect": "SELECT id, skill_id, effect_id, enable FROM skill_effects WHERE effect_id=72642",
    "actors": "SELECT id, model, client_doodad, once_one_man, once_one_interaction FROM doodad_almighties WHERE id IN (13374,13375) ORDER BY id",
    "groups": "SELECT id, doodad_almighty_id, model, doodad_func_group_kind_id FROM doodad_func_groups WHERE doodad_almighty_id IN (13374,13375) ORDER BY id",
    "functions": "SELECT * FROM doodad_funcs WHERE doodad_func_group_id IN (SELECT id FROM doodad_func_groups WHERE doodad_almighty_id IN (13374,13375)) ORDER BY id",
    "phase_functions": "SELECT * FROM doodad_phase_funcs WHERE doodad_func_group_id IN (SELECT id FROM doodad_func_groups WHERE doodad_almighty_id IN (13374,13375)) ORDER BY id",
    "reactions": "SELECT * FROM doodad_func_quest_reacts WHERE id IN (43,52,60,61,66,67,91,98,203) ORDER BY id",
    "models": "SELECT * FROM doodad_func_model_changes WHERE id IN (12,13,35) ORDER BY id",
    "report_offer": "SELECT * FROM doodad_func_quests WHERE id IN (1133,1134) ORDER BY id",
}


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    result = {"quest_id": 9173, "queries": QUERIES, "databases": {}}
    for label, path in DATABASES.items():
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            db.row_factory = sqlite3.Row
            rows = {name: [dict(r) for r in db.execute(sql)] for name, sql in QUERIES.items()}
        result["databases"][label] = {"path": str(path), "sha256": sha256(path), "rows": rows}
    assert result["databases"]["full"]["rows"] == result["databases"]["compact"]["rows"], "Full/compact contract differs"
    placements_path = OUT / "placements.csv"
    placements = list(csv.DictReader(placements_path.read_text(encoding="utf-8-sig").splitlines()))
    assert sorted(int(row["doodad_id"]) for row in placements) == [13374, 13375]
    overlay_path = REPO / "AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_client_quest_proxies.json"
    overlay = json.loads(overlay_path.read_text(encoding="utf-8-sig"))
    expected_phases = {13374: 38776, 13375: 38772}
    for placement in placements:
        actor_id = int(placement["doodad_id"])
        actors = [r for r in overlay if r["UnitId"] == actor_id]
        assert len(actors) == 1, f"Missing/duplicated actor {actor_id}"
        actor = actors[0]
        assert actor["FuncGroupId"] == expected_phases[actor_id]
        for key in ("X", "Y", "Z"):
            assert abs(actor["Position"][key] - float(placement[key.lower()])) < 0.001
        assert abs(actor["Position"]["Yaw"] - float(placement["yaw_degrees"])) < 0.001
        assert actor["Scale"] == float(placement["scale"]) == 1
    result.update(status="pass", placements=placements, placements_sha256=sha256(placements_path),
                  overlay_sha256=sha256(overlay_path), retail_acceptance="pending")
    (OUT / "native-contract.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS: full/compact contracts agree; both placements match r575 and preserve native Start phases")


if __name__ == "__main__":
    main()
