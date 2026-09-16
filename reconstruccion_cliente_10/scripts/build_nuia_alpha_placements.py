"""Build only proven Elf/Dwarf placement gaps from the frozen read-only audit.

Does not deploy, operate Zones, change SQLite or edit an existing spawn catalog.
"""
import csv
import json
from pathlib import Path
from audit_hiram_onward_quests import ROOT, REPO, sha


def main():
    evidence = ROOT / 'forensics/output/aa10-client-forensics/nuia-alpha-20260915'
    report = json.loads((evidence / 'audit-before.json').read_text(encoding='utf-8'))
    for path, expected in report['sources'].items():
        if sha(Path(path)) != expected:
            raise ValueError(f'Source identity changed: {path}')
    quests = {q['id']: q for q in report['quests']}
    actors = {a['id']: a for a in report['actors']}
    gaps = [m for m in report['missing_placements']
            if any(quests[q]['category_id'] in (8, 93) for q in actors[m['actor']]['quests'])]
    output, fixture, keys = [], [], set()
    for gap in gaps:
        actor, pos = gap['actor'], gap['placement']
        if len(gap['starts']) != 1 or '/main_world/' not in pos['entry']:
            raise ValueError(f'Ambiguous native contract: {gap}')
        xyz = tuple(float(pos[k]) for k in ('x','y','z'))
        key = (actor, *xyz)
        if key in keys:
            raise ValueError(f'Duplicate native placement: {key}')
        keys.add(key)
        rotation = tuple(float(pos[k]) for k in ('roll_degrees','pitch_degrees','yaw_degrees'))
        scale, phase = float(pos['scale']), gap['starts'][0]
        output.append(dict(Id=0, UnitId=actor, Title=f'AA10 r575 Elf/Dwarf quest actor {actor}',
                           Position=dict(zip(('X','Y','Z','Roll','Pitch','Yaw'), (*xyz,*rotation))),
                           FuncGroupId=phase, Scale=scale))
        fixture.append((actor,*xyz,*rotation,scale,phase,pos['entry']))
    target = REPO / 'AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_nuia_alpha_r575.json'
    target.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    with (REPO/'AAEmu.UnitTests/Fixtures/nuia_alpha_r575_placements.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f)
        writer.writerow(('doodad_id','x','y','z','roll','pitch','yaw','scale','start_phase','native_entry'))
        writer.writerows(fixture)
    manifest = dict(count=len(output), templates=len({x['UnitId'] for x in output}), sha256=sha(target),
                    audit_before_sha256=sha(evidence/'audit-before.json'),
                    native_scan_sha256=sha(evidence/'all-world-placements.csv'),
                    source_only=sum(bool(x['coverage']['source']) for x in gaps),
                    runtime_only=sum(bool(x['coverage']['runtime']) for x in gaps),
                    absent_both=sum(not x['coverage']['source'] and not x['coverage']['runtime'] for x in gaps))
    (evidence/'placement-build.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
