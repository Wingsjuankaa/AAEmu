"""Reproducible, read-only AA10 quest dependency / native placement sweep."""
import csv
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path('E:/AAEmu/rama_10')
REPO = ROOT / 'server/AAEmu'
OUT = ROOT / 'forensics/output/aa10-client-forensics/hiram-onward-sweep'
SCOPE = ('chapter_idx>=18 OR category_id IN (180,183,200,206,208,210,225) '
         'OR zone_id IN (266,270,294,295,297,298,299,301,302,304,305,311)')


def read_json(path):
    # Preserve strings (including prefab://) while removing Json.NET comments.
    text = path.read_text(encoding='utf-8-sig')
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
                  lambda m: m[0] if m[0].startswith('"') else '', text)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return json.loads(text)


def table_name(type_name):
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', type_name).lower()
    return name[:-1] + 'ies' if name.endswith('y') else name + 's'


def rows(db, sql, args=()):
    return [dict(r) for r in db.execute(sql, args)]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    full_path = ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3'
    compact_path = ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3'
    db = sqlite3.connect(full_path.as_uri()+'?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    compact = sqlite3.connect(compact_path.as_uri()+'?mode=ro', uri=True)
    compact.row_factory = sqlite3.Row
    quests = rows(db, f'SELECT id,category_id,chapter_idx,quest_idx,zone_id FROM quest_contexts WHERE {SCOPE} ORDER BY id')
    quest_ids = {q['id'] for q in quests}
    ids = ','.join(map(str, sorted(quest_ids)))
    components = rows(db, f'SELECT * FROM quest_components WHERE quest_context_id IN ({ids}) ORDER BY id')
    component_quests = {r['id']: r['quest_context_id'] for r in components}
    acts = rows(db, f'SELECT * FROM quest_acts WHERE quest_component_id IN (SELECT id FROM quest_components WHERE quest_context_id IN ({ids})) ORDER BY id')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    references, missing_details, differences = [], [], []
    doodad_quests, npc_quests, item_quests = {}, {}, {}

    def link(target, entity, quest, reason):
        if entity and entity > 0:
            target.setdefault(entity, set()).add(quest)
            references.append(dict(quest=quest, entity=entity, reason=reason))

    for act in acts:
        if act['enable'] != 't':
            continue
        quest = component_quests[act['quest_component_id']]
        table = table_name(act['act_detail_type'])
        detail = rows(db, f'SELECT * FROM {table} WHERE id=?', (act['act_detail_id'],)) if table in tables else []
        if not detail:
            missing_details.append(act)
            continue
        other = rows(compact, f'SELECT * FROM {table} WHERE id=?', (act['act_detail_id'],))
        if detail != other:
            differences.append(dict(act=act['id'], table=table))
        detail = detail[0]
        for key, value in detail.items():
            if key in ('doodad_id', 'highlight_doodad_id'):
                link(doodad_quests, value, quest, f'{table}.{key}')
            elif key in ('npc_id',):
                link(npc_quests, value, quest, f'{table}.{key}')
            elif key == 'quest_doodad_group_id' and value:
                for member in rows(db, 'SELECT doodad_id FROM quest_doodads WHERE quest_doodad_group_id=?', (value,)):
                    link(doodad_quests, member['doodad_id'], quest, f'{table}.doodad_group{value}')
            elif key == 'item_group_id' and value:
                for member in rows(db, 'SELECT item_id FROM quest_item_group_items WHERE quest_item_group_id=?', (value,)):
                    link(item_quests, member['item_id'], quest, f'{table}.item_group{value}')
            elif key in ('quest_monster_group_id', 'npc_group_id') and value:
                for member in rows(db, 'SELECT npc_id FROM quest_monster_npcs WHERE quest_monster_group_id=?', (value,)):
                    link(npc_quests, member['npc_id'], quest, f'{table}.npc_group{value}')
            elif key == 'item_id':
                link(item_quests, value, quest, f'{table}.{key}')

    # Actors may offer/report/react without being directly highlighted by a quest act.
    for func_table, actual_type in [('doodad_func_quests','DoodadFuncQuest'), ('doodad_func_quest_reacts','DoodadFuncQuestReact')]:
        for row in rows(db, f'''SELECT g.doodad_almighty_id, d.quest_id FROM {func_table} d
            JOIN (SELECT doodad_func_group_id,actual_func_id,actual_func_type FROM doodad_funcs UNION ALL SELECT doodad_func_group_id,actual_func_id,actual_func_type FROM doodad_phase_funcs) f
            ON f.actual_func_id=d.id AND f.actual_func_type=?
            JOIN doodad_func_groups g ON g.id=f.doodad_func_group_id WHERE d.quest_id IN ({ids})''', (actual_type,)):
            link(doodad_quests, row['doodad_almighty_id'], row['quest_id'], actual_type)

    # Include native world suppliers of quest items, not just highlighted objects.
    for item, quest_set in item_quests.items():
        for row in rows(db, '''SELECT DISTINCT g.doodad_almighty_id FROM doodad_func_loot_items l
            JOIN (SELECT doodad_func_group_id,actual_func_id,actual_func_type FROM doodad_funcs
                  UNION ALL SELECT doodad_func_group_id,actual_func_id,actual_func_type FROM doodad_phase_funcs) f
            ON f.actual_func_type='DoodadFuncLootItem' AND f.actual_func_id=l.id
            JOIN doodad_func_groups g ON g.id=f.doodad_func_group_id WHERE l.item_id=?''', (item,)):
            for quest in quest_set:
                link(doodad_quests, row['doodad_almighty_id'], quest, f'loot_item{item}')

    (OUT/'requested-ids.txt').write_text(','.join(map(str, sorted(doodad_quests))), encoding='utf-8')
    catalogs = {}
    for label, base in [('source', REPO), ('runtime', REPO/'.server_files')]:
        world = base/'AAEmu.Game/Data/Worlds/main_world'
        replacements = read_json(world/'doodad_spawn_replacements.json')
        catalog = []
        for path in sorted(world.glob('doodad_spawns*.json'), reverse=True):
            for row in read_json(path):
                pos = row['Position']
                if any(r['SourceFile']==path.name and r['MinX'] <= pos['X'] < r['MaxX'] and r['MinY'] <= pos['Y'] < r['MaxY'] for r in replacements):
                    continue
                catalog.append(dict(file=path.name, **row))
        catalogs[label] = {}
        for row in catalog:
            catalogs[label].setdefault(row['UnitId'], []).append(row)

    native = list(csv.DictReader((OUT/'placements.csv').read_text(encoding='utf-8-sig').splitlines())) if (OUT/'placements.csv').exists() else []
    actors, missing, contracts = [], [], {}
    all_world_native = list(csv.DictReader((OUT/"all-world-placements.csv").read_text(encoding="utf-8-sig").splitlines())) if (OUT/"all-world-placements.csv").exists() else []
    for actor_id, quest_set in sorted(doodad_quests.items()):
        template = rows(db, 'SELECT id,model,client_doodad,once_one_man FROM doodad_almighties WHERE id=?', (actor_id,))
        groups = rows(db, 'SELECT id,model,doodad_func_group_kind_id FROM doodad_func_groups WHERE doodad_almighty_id=? ORDER BY id', (actor_id,))
        starts = [g['id'] for g in groups if g['doodad_func_group_kind_id']==1]
        placements = [r for r in native if int(r['doodad_id'])==actor_id]
        actor = dict(id=actor_id,quests=sorted(quest_set),template=template,starts=starts,placements=len(placements))
        for placement in placements:
            coverage = {}
            for label, catalog in catalogs.items():
                coverage[label] = [r['file'] for r in catalog.get(actor_id, []) if all(abs(r['Position'][key]-float(placement[key.lower()]))<0.01 for key in ('X','Y','Z'))]
            if not coverage['source'] or not coverage['runtime']:
                missing.append(dict(actor=actor_id,placement=placement,coverage=coverage,starts=starts))
        actor['instance_worlds'] = sorted({r['entry'].split('/')[2] for r in all_world_native if int(r['doodad_id'])==actor_id and '/main_world/' not in r['entry']})
        actor['item_spawn_sources'] = rows(db, 'SELECT * FROM item_spawn_doodads WHERE doodad_id=?', (actor_id,))
        actor['status'] = 'static_placements_audited' if placements else ('instance_placement' if actor['instance_worlds'] else 'no_world_placement_not_proven_missing')
        if placements:
            contract = {}
            queries = {
                'template': f'SELECT * FROM doodad_almighties WHERE id={actor_id}',
                'groups': f'SELECT * FROM doodad_func_groups WHERE doodad_almighty_id={actor_id} ORDER BY id',
                'functions': f'SELECT * FROM doodad_funcs WHERE doodad_func_group_id IN (SELECT id FROM doodad_func_groups WHERE doodad_almighty_id={actor_id}) ORDER BY id',
                'phase_functions': f'SELECT * FROM doodad_phase_funcs WHERE doodad_func_group_id IN (SELECT id FROM doodad_func_groups WHERE doodad_almighty_id={actor_id}) ORDER BY id',
            }
            for label, query in queries.items():
                contract[label] = rows(db, query)
                assert contract[label] == rows(compact, query), f'Actor {actor_id} full/compact {label} mismatch'
            contract['details'] = {}
            for func in contract['functions'] + contract['phase_functions']:
                table = table_name(func['actual_func_type'])
                detail = rows(db, f'SELECT * FROM {table} WHERE id=?', (func['actual_func_id'],))
                assert detail and detail == rows(compact, f'SELECT * FROM {table} WHERE id=?', (func['actual_func_id'],)), f'Missing/different {func}'
                contract['details'][f"{table}:{func['actual_func_id']}"] = detail
            contracts[str(actor_id)] = contract
        actors.append(actor)
    report = dict(scope_sql=SCOPE,quests=quests,components=len(components),enabled_acts=sum(a['enable']=='t' for a in acts),
                  missing_act_details=missing_details,full_compact_detail_differences=differences,references=references,
                  actors=actors,missing_placements=missing,npcs={str(k):sorted(v) for k,v in npc_quests.items()},
                  items={str(k):sorted(v) for k,v in item_quests.items()},
                  sources={str(p):sha(p) for p in (full_path,compact_path)})
    report['missing_npc_templates'] = [i for i in npc_quests if not rows(db,'SELECT id FROM npcs WHERE id=?',(i,))]
    report['missing_item_templates'] = [i for i in item_quests if not rows(db,'SELECT id FROM items WHERE id=?',(i,))]
    (OUT/'native-contracts.json').write_text(json.dumps(contracts,indent=2)+'\n',encoding='utf-8')
    overlay_path = REPO/'AAEmu.Game/Data/Worlds/main_world/doodad_spawns_aa10_hiram_onward_r575.json'
    if '--write-overlay' in sys.argv or '--extend-overlay' in sys.argv:
        assert native
        extending = '--extend-overlay' in sys.argv
        assert overlay_path.exists() == extending, 'Generate new or explicitly extend an existing overlay'
        assert not missing_details and not differences
        additions = read_json(overlay_path) if extending else []
        for entry in missing:
            assert not entry['coverage']['source'] and not entry['coverage']['runtime'], 'Source/runtime disagreement'
            assert len(entry['starts']) == 1
            placement = entry['placement']
            additions.append(dict(Id=0,UnitId=entry['actor'],Title=f"AA10 r575 quest object {entry['actor']}",
                Position={key:float(placement[column]) for key,column in [('X','x'),('Y','y'),('Z','z'),('Roll','roll_degrees'),('Pitch','pitch_degrees'),('Yaw','yaw_degrees')]},
                FuncGroupId=entry['starts'][0],Scale=float(placement['scale'])))
        overlay_path.write_text(json.dumps(additions,indent=2)+'\n',encoding='utf-8')
        (OUT/('audit-before-groups.json' if extending else 'audit-before.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(f'Generated {len(additions)} native placements')
    if overlay_path.exists():
        overlay = read_json(overlay_path)
        keys = [(r['UnitId'],r['Position']['X'],r['Position']['Y'],r['Position']['Z']) for r in overlay]
        assert len(keys)==len(set(keys)), 'Duplicate placement'
        for actor in overlay:
            placement = [r for r in native if int(r['doodad_id'])==actor['UnitId'] and all(abs(actor['Position'][k]-float(r[k.lower()]))<0.001 for k in ('X','Y','Z'))]
            assert len(placement)==1, f'No unique native placement {actor}'
            assert actor['FuncGroupId'] == next(r for r in actors if r['id']==actor['UnitId'])['starts'][0]
            for key,column in [('Roll','roll_degrees'),('Pitch','pitch_degrees'),('Yaw','yaw_degrees')]:
                assert abs(actor['Position'][key]-float(placement[0][column]))<0.001
            assert actor['Scale']==float(placement[0]['scale'])
        report['overlay_validation'] = dict(status='pass',count=len(overlay),sha256=sha(overlay_path))
    (OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(quests=len(quests),actors=len(actors),npc_templates=len(npc_quests),items=len(item_quests),missing_details=len(missing_details),full_compact_differences=len(differences),native_placements=len(native),missing_placements=len(missing))))


if __name__ == '__main__':
    main()
