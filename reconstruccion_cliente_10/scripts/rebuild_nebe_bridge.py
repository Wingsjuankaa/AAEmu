"""Restore only quest10028's r575 native bridge placements; no invented coordinates.

Input: PakDoodadScan output for 14934,14935,14936,14937,14948,14949.
Regenerate that CSV from the immutable r575 game_pak before changing its pinned hash.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

from audit_hiram_onward_quests import read_json

ROOT = Path('E:/AAEmu/rama_10')
REPO = ROOT / 'server/AAEmu'
IDS = {14934, 14935, 14936, 14937, 14948, 14949}
NAME = 'doodad_spawns_aa10_nebe_bridge_r575.json'
PLACEMENTS_SHA256 = 'f779c64bc6d5464efa7e34ae2d267b22f7535c30580371ffb2fc2e89bded3286'


def build(csv_path):
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == PLACEMENTS_SHA256, 'Native CSV hash mismatch'
    placements = list(csv.DictReader(csv_path.open(encoding='utf-8-sig')))
    assert len(placements) == 21 and {int(r['doodad_id']) for r in placements} == IDS
    assert {r['entry'] for r in placements} == {
        f'game/worlds/main_world/level_design/cells/{cell}/doodad.g' for cell in ('030_034', '031_034')}
    starts = []
    for path in [ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3',
                 REPO/'.server_files/AAEmu.Game/Data/compact.sqlite3']:
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            rows = db.execute('SELECT doodad_almighty_id,id,model FROM doodad_func_groups '
                              'WHERE doodad_almighty_id IN (14934,14935,14936,14937,14948,14949) '
                              'AND doodad_func_group_kind_id=1 ORDER BY doodad_almighty_id').fetchall()
            assert len(rows) == len(IDS) and {r[0] for r in rows} == IDS
            starts.append(rows)
    assert starts[0] == starts[1], 'Authoritative/runtime phase mismatch'
    phases = {r[0]: r[1] for r in starts[0]}
    output = []
    for row in placements:
        actor = int(row['doodad_id'])
        output.append(dict(Id=0, UnitId=actor, Title=f'AA10 r575 Nebe bridge {actor}',
            Position={k: float(row[col]) for k,col in [('X','x'),('Y','y'),('Z','z'),
                ('Roll','roll_degrees'),('Pitch','pitch_degrees'),('Yaw','yaw_degrees')]},
            FuncGroupId=phases[actor], Scale=float(row['scale'])))
    def key(r): return (r['UnitId'], *(r['Position'][a] for a in ('X','Y','Z')))
    keys = {key(r) for r in output}
    assert len(keys) == len(output), 'Duplicate native placements'
    for base in (REPO, REPO/'.server_files'):
        for path in (base/'AAEmu.Game/Data/Worlds/main_world').glob('doodad_spawns*.json'):
            if path.name != NAME:
                assert not keys.intersection(key(r) for r in read_json(path)), f'Already loaded in {path}'
    return (json.dumps(output, indent=2)+'\n').encode('utf8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placements', type=Path, required=True)
    parser.add_argument('--write', action='store_true', help='Write source overlay; does not deploy')
    args = parser.parse_args()
    result = build(args.placements)
    destination = REPO/'AAEmu.Game/Data/Worlds/main_world'/NAME
    if args.write:
        destination.write_bytes(result)
    else:
        assert destination.read_bytes() == result, 'Source overlay differs from native placement build'
    print(json.dumps({'placements':21,'sha256':hashlib.sha256(result).hexdigest(),
                      'source':str(destination),'phaseDefinitionsMatchRuntime':True}))
