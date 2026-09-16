"""Restore proven regional Nuia quest props from r575 cells; never operate Zones.

Uses the frozen sidequest audit and native world.xml sector ownership. Dynamic,
client-only, generic-zone-only and unresolved function contracts stay excluded.
Only writes a source overlay, its native fixture and the boat replacement rule.
"""
import csv
import hashlib
import json
import math
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter

from audit_hiram_onward_quests import ROOT, REPO, read_json, sha

AUDIT = ROOT/'forensics/output/aa10-client-forensics/nuia-sidequests-20260915'
OUT = ROOT/'forensics/output/aa10-client-forensics/nuia-sidequests-repair-20260915'
WORLD = ROOT/'forensics/output/aa10-client-forensics/housing-h1-frontier/extracted/game/worlds/main_world/world.xml'
OVERLAY = 'doodad_spawns_aa10_nuia_sidequests_r575.json'
BOAT_RULE = dict(SourceFile='doodad_spawns.json',ReplacementFile=OVERLAY,
                 MinX=15217.0,MinY=13616.0,MaxX=15228.0,MaxY=13617.0)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report=json.loads((AUDIT/'audit.json').read_text(encoding='utf-8'))
    closure=json.loads((AUDIT/'classification.json').read_text(encoding='utf-8'))
    contracts=json.loads((AUDIT/'interaction-contracts.json').read_text(encoding='utf-8'))
    assert not report['missing_act_details'] and not report['full_compact_detail_differences']
    assert not closure['difference_tables']['server_compact']
    for path, expected in report['sources'].items():
        from pathlib import Path
        assert sha(Path(path))==expected, f'Source changed: {path}'
    # MD5 from the original package entry index; sector granularity = 64m in
    # XmlWorldSector/WorldManager (16 sectors per 1024m cell).
    assert hashlib.md5(WORLD.read_bytes()).hexdigest()=='44f5ea385afd79bf710c0d2f327b9f05'
    sectors={}
    for zone in ET.parse(WORLD).getroot().findall('ZoneList/Zone'):
        for cell in zone.findall('cellList/cell'):
            for sector in cell.findall('sectorList/sector'):
                key=(int(cell.get('x'))*16+int(sector.get('x')),int(cell.get('y'))*16+int(sector.get('y')))
                sectors[key]=int(zone.get('id'))
    db=sqlite3.connect((ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3').as_uri()+'?mode=ro',uri=True)
    nuia={r[0] for r in db.execute('SELECT zone_key FROM zones z JOIN zone_groups g ON z.group_id=g.id WHERE g.target_id=3')}
    actors={a['id']:a for a in report['actors']}
    quests={q['id']:q for q in report['quests']}
    missing_types=set(closure['missing_consumers'])
    # Newly implemented fixed-range NPC descriptor; validate each referenced row
    # before lifting the old audit's missing-consumer exclusion.
    def supported_spawn(detail):
        return (detail['owner_type_id']==1 and detail['sub_type']>0 and
                detail['pos_dir_id'] in (1,2) and detail['ori_dir_id'] in (1,2) and
                detail['pos_angle_min']==detail['pos_angle_max'] and
                detail['pos_distance_min']==detail['pos_distance_max'] and
                detail['pos_distance_min']>=0 and detail['life_time']>=0)
    catalogs={}
    for label,base in [('source',REPO),('runtime',REPO/'.server_files')]:
        folder=base/'AAEmu.Game/Data/Worlds/main_world'
        replacements=read_json(folder/'doodad_spawn_replacements.json')
        catalogs[label]={}
        for path in folder.glob('doodad_spawns*.json'):
            if path.name==OVERLAY:
                continue
            for row in read_json(path):
                pos=row['Position']
                if any(r['SourceFile']==path.name and r['ReplacementFile']!=OVERLAY and
                       r['MinX']<=pos['X']<r['MaxX'] and r['MinY']<=pos['Y']<r['MaxY'] for r in replacements):
                    continue
                catalogs[label].setdefault(row['UnitId'],[]).append(row)
        box=[r for r in read_json(folder/'doodad_spawns.json') if
             BOAT_RULE['MinX']<=r['Position']['X']<BOAT_RULE['MaxX'] and
             BOAT_RULE['MinY']<=r['Position']['Y']<BOAT_RULE['MaxY']]
        assert box and all(r['UnitId']==2853 for r in box), 'Boat box would remove unrelated content'

    excluded=Counter()
    chosen={}
    for gap in report['missing_placements']:
        aid=gap['actor'];actor=actors[aid];pos=gap['placement']
        zone=sectors.get((math.floor(float(pos['x'])/64),math.floor(float(pos['y'])/64)))
        reason=None
        if zone not in nuia: reason='outside_nuia'
        elif not any(quests[q]['zone_id']!=1 for q in actor['quests']): reason='generic_zone_only'
        elif actor['item_spawn_sources']: reason='plantable'
        elif not actor['template'] or actor['template'][0]['client_doodad']=='t': reason='client_or_missing_template'
        elif len(actor['starts'])!=1: reason='ambiguous_start'
        elif any(f['row']['actual_func_type'] in missing_types and not
                 (f['row']['actual_func_type']=='DoodadFuncSpawn' and supported_spawn(f['detail']))
                 for f in contracts[str(aid)]['functions']): reason='unresolved_consumer'
        if reason:
            excluded[reason]+=1
            continue
        # Do not create an almost coincident duplicate for a 1-5cm legacy roundoff.
        # Exact catalog matches will be deduplicated by the existing loader.
        near_inexact=False
        for catalog in catalogs.values():
            for row in catalog.get(aid,[]):
                delta=max(abs(row['Position'][k]-float(pos[k.lower()])) for k in ('X','Y','Z'))
                if 0.01<=delta<0.05: near_inexact=True
        if near_inexact and aid!=2853:
            excluded['near_legacy_roundoff']+=1
            continue
        key=(aid,*(float(pos[k]) for k in ('x','y','z')))
        if key in chosen:
            assert chosen[key]==(pos,actor['starts'][0],zone), 'Conflicting coincident native placements'
            excluded['identical_native_duplicate']+=1
            continue
        chosen[key]=(pos,actor['starts'][0],zone)

    # Replace the whole five-boat cluster, including the already-present ones.
    for pos in csv.DictReader((AUDIT/'placements.csv').open(encoding='utf-8-sig')):
        if int(pos['doodad_id'])!=2853: continue
        key=(2853,*(float(pos[k]) for k in ('x','y','z')))
        zone=sectors[(math.floor(key[1]/64),math.floor(key[2]/64))]
        assert zone==178 and zone in nuia
        chosen[key]=(pos,6378,zone)
    assert sum(k[0]==2853 for k in chosen)==5
    output=[];fixture=[]
    for (aid,x,y,z),(pos,start,zone) in sorted(chosen.items()):
        rotation=[float(pos[k]) for k in ('roll_degrees','pitch_degrees','yaw_degrees')]
        scale=float(pos['scale'])
        output.append(dict(Id=0,UnitId=aid,Title=f'AA10 r575 Nuia regional quest object {aid}',
                           Position=dict(zip(('X','Y','Z','Roll','Pitch','Yaw'),(x,y,z,*rotation))),FuncGroupId=start,Scale=scale))
        fixture.append((aid,x,y,z,*rotation,scale,start,zone,pos['entry']))
    source=REPO/'AAEmu.Game/Data/Worlds/main_world'/OVERLAY
    source.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    fixture_path=REPO/'AAEmu.UnitTests/Fixtures/nuia_sidequests_r575_placements.csv'
    with fixture_path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(('doodad_id','x','y','z','roll','pitch','yaw','scale','start_phase','zone_key','native_entry'));w.writerows(fixture)
    rules_path=REPO/'AAEmu.Game/Data/Worlds/main_world/doodad_spawn_replacements.json'
    rules=read_json(rules_path)
    existing=[r for r in rules if r.get('ReplacementFile')==OVERLAY]
    assert not existing or existing==[BOAT_RULE], 'Unexpected existing replacement'
    if not existing:rules.append(BOAT_RULE)
    rules_path.write_text(json.dumps(rules,indent=2)+'\n',encoding='utf-8')
    manifest=dict(placements=len(output),templates=len({k[0] for k in chosen}),
                  regional_quests=sorted({q for k in chosen for q in actors[k[0]]['quests'] if quests[q]['zone_id']!=1}),
                  by_zone=dict(Counter(row[-2] for row in fixture)),exclusions=dict(excluded),
                  source_sha256=sha(source),fixture_sha256=sha(fixture_path),world_sha256=sha(WORLD),
                  audit_sha256=sha(AUDIT/'audit.json'),scan_sha256=sha(AUDIT/'all-world-placements.csv'),
                  boat_replacement=BOAT_RULE)
    (OUT/'placement-build.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__':main()
