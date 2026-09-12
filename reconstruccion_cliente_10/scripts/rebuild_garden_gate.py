"""Rebuild the Garden portal overlay from read-only PakDoodadScan evidence."""
import argparse
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
REPO = ROOT / 'server/AAEmu'
IDS = {14855, 14856, 14857, 14858, 14859, 14861, 14862, 14864, 14865, 14866, 14867, 14868, 16879}


def build(evidence):
    full = sqlite3.connect((ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3').as_uri() + '?mode=ro', uri=True)
    compact = sqlite3.connect((REPO / '.server_files/AAEmu.Game/Data/compact.sqlite3').as_uri() + '?mode=ro', uri=True)
    placements = []
    for filename in ['placements.csv', 'placements-active.csv']:
        with (evidence / filename).open(encoding='utf-8-sig') as stream:
            for row in csv.DictReader(stream):
                template = int(row['doodad_id'])
                if template not in IDS or not row['entry'].startswith('game/worlds/main_world/'):
                    continue
                query = 'SELECT id FROM doodad_func_groups WHERE doodad_almighty_id=? AND doodad_func_group_kind_id=1'
                groups = full.execute(query, (template,)).fetchall()
                assert len(groups) == 1 and groups == compact.execute(query, (template,)).fetchall(), template
                placements.append(dict(Id=0, UnitId=template, Title=f'AA10 Garden portal {template}',
                    Position=dict(X=float(row['x']), Y=float(row['y']), Z=float(row['z']),
                                  Roll=float(row['roll_degrees']), Pitch=float(row['pitch_degrees']),
                                  Yaw=float(row['yaw_degrees'])), FuncGroupId=groups[0][0], Scale=float(row['scale'])))
    assert len(placements) == 13 and {p['UnitId'] for p in placements} == IDS
    return sorted(placements, key=lambda p: p['UnitId'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT / 'forensics/output/aa10-client-forensics/garden-gate')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    result = build(args.evidence)
    output = REPO / 'AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_garden_gates.json'
    payload = json.dumps(result, indent=2) + '\n'
    if args.write:
        if output.exists() and output.read_text(encoding='utf-8') != payload:
            raise SystemExit('Existing overlay differs; review before replacing it.')
        output.write_text(payload, encoding='utf-8')
    else:
        assert output.read_text(encoding='utf-8') == payload, 'Overlay differs from native evidence'
    print(f'Validated {len(result)} Garden placements: {output}')
