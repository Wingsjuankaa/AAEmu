"""Classify the read-only yellow-quest sweep without treating missing spawns as bugs.

Consumes audit_nuia_sidequests.py + PakDoodadScan results. Never writes runtime,
client, SQLite, translations, or spawn catalogs. Closure is static evidence only.
"""
import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from audit_hiram_onward_quests import ROOT, REPO, read_json, sha, table_name
from audit_nuia_sidequests import OUT


def main():
    report = json.loads((OUT/'audit.json').read_text(encoding='utf-8'))
    paths = {
        'full': ROOT/'data/sqlite/authoritative/game_decrypted.sqlite3',
        'original_compact': ROOT/'client/ArcheAge-Returns-10.0.2.13-r575/game/db/compact.sqlite3',
        'es_compact': ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/game/db/compact.sqlite3',
        'server_compact': REPO/'.server_files/AAEmu.Game/Data/compact.sqlite3',
    }
    dbs, cache = {}, {}
    for label, path in paths.items():
        dbs[label] = sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)
        dbs[label].row_factory = sqlite3.Row

    def table(label, name):
        key = label, name
        if key not in cache:
            cache[key] = {r['id']: dict(r) for r in dbs[label].execute(f'SELECT * FROM {name}')}
        return cache[key]

    def emit(name, value):
        (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    funcs_by_actor, groups_by_actor, actors_by_quest = defaultdict(list), defaultdict(list), defaultdict(list)
    groups = table('full', 'doodad_func_groups')
    for g in groups.values():
        groups_by_actor[g['doodad_almighty_id']].append(g)
    orphan_functions = []
    for name in ['doodad_funcs', 'doodad_phase_funcs']:
        for f in table('full', name).values():
            group = groups.get(f['doodad_func_group_id'])
            if group is None:
                orphan_functions.append(dict(table=name, row=f))
                continue
            funcs_by_actor[group['doodad_almighty_id']].append((name, f))
    for actor in report['actors']:
        for q in actor['quests']:
            actors_by_quest[q].append(actor['id'])

    skills = table('full', 'skills')
    effects = table('full', 'effects')
    skill_effects = defaultdict(list)
    for row in table('full', 'skill_effects').values():
        skill_effects[row['skill_id']].append(row)
    changes, missing, consumers, contracts = [], [], {}, {}
    compared = set()

    def compare(name, row_id, actor):
        key = name, row_id
        full = table('full', name).get(row_id)
        if key in compared:
            return full
        compared.add(key)
        if full is None:
            missing.append(dict(actor=actor, table=name, id=row_id))
        for label in paths:
            if label == 'full':
                continue
            other = table(label, name).get(row_id)
            # Text columns are intentionally localized; mechanical comparisons only.
            fields = [k for k in full or {} if k not in ('name','desc','web_desc','tip','popup_desc','comments')
                      and (other is None or full[k] != other.get(k))]
            if fields or (full is None) != (other is None):
                changes.append(dict(actor=actor, table=name, id=row_id, projection=label,
                                    fields={k: dict(full=full[k], projected=None if other is None else other.get(k)) for k in fields},
                                    missing_full=full is None, missing_projection=other is None))
        return full

    loader = (REPO/'AAEmu.Game/Core/Managers/UnitManagers/DoodadManager.cs').read_text(encoding='utf-8-sig')
    funcs_root = REPO/'AAEmu.Game/Models/Game/DoodadObj/Funcs'
    for actor in report['actors']:
        aid = actor['id']
        contract = dict(template=compare('doodad_almighties', aid, aid), groups=[], functions=[], skills={})
        actor_skills = set()
        for g in groups_by_actor[aid]:
            contract['groups'].append(compare('doodad_func_groups',g['id'],aid))
        for source, f in funcs_by_actor[aid]:
            compare(source, f['id'], aid)
            typename = f['actual_func_type']
            detail = compare(table_name(typename), f['actual_func_id'], aid)
            contract['functions'].append(dict(source=source, row=f, detail=detail))
            actor_skills.update(value for key,value in (detail or {}).items()
                                if key in ('skill_id','fake_skill_id') and value and value > 0)
            if f.get('func_skill_id'):
                actor_skills.add(f['func_skill_id'])
            if typename not in consumers:
                path = funcs_root/(typename+'.cs')
                consumers[typename] = dict(source=str(path), exists=path.exists(),
                                           loader_present=bool(re.search(r'new\s+'+re.escape(typename)+r'\b', loader)),
                                           sha256=sha(path) if path.exists() else None)
        for sid in sorted(actor_skills):
            skill = compare('skills', sid, aid)
            effect_rows = []
            for se in skill_effects[sid]:
                compare('skill_effects',se['id'],aid)
                e = compare('effects',se['effect_id'],aid)
                effect_rows.append(dict(link=se, effect=e))
            contract['skills'][sid] = dict(skill=skill, effects=effect_rows)
        contracts[aid] = contract

    # Exact native placement presence is not a proof of correct phase/rotation or
    # geographical eligibility. Keep these findings separate in the matrix.
    gaps_by_actor = Counter(g['actor'] for g in report['missing_placements'])
    actor_map = {a['id']: a for a in report['actors']}
    zones = table('full', 'zones')
    qrows = table('full', 'quest_contexts')
    matrix = []
    for q in report['quests']:
        qid = q['id']
        aids = actors_by_quest[qid]
        row = dict(quest_id=qid,title_es=q.get('title_es'),category_id=q['category_id'],zone_id=q['zone_id'],
                   profile=zones[q['zone_id']]['name'],zone_key=zones[q['zone_id']]['zone_key'],
                   scope='generic_zone1_review_availability' if q['zone_id']==1 else 'regional_catalog_review_availability',
                   priority='P0_horse_boat' if qid in (2393,4292,4294,4295) else 'P1_regional' if q['zone_id']!=1 else 'P2_generic_catalog',
                   doodads=';'.join(map(str,sorted(aids))),
                   static_native_gaps=sum(gaps_by_actor[a] for a in aids),
                   plantable_doodads=';'.join(str(a) for a in aids if actor_map[a]['item_spawn_sources']),
                   unplaced_unclassified=';'.join(str(a) for a in aids if not actor_map[a]['placements']
                                                 and not actor_map[a]['item_spawn_sources'] and not actor_map[a]['instance_worlds']),
                   acceptance='pending_client', race_mask=qrows[qid]['race'])
        matrix.append(row)
    with (OUT/'quest-matrix.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(matrix[0]));writer.writeheader();writer.writerows(matrix)
    emit('quest-matrix.json', matrix)
    emit('interaction-contracts.json',contracts)
    emit('projection-differences.json',changes)
    emit('doodad-consumers.json',consumers)
    emit('orphan-functions-global-not-attributed.json',orphan_functions)

    function_impacts = []
    for typename, consumer in consumers.items():
        if consumer['exists'] and consumer['loader_present']:
            continue
        affected = [aid for aid,c in contracts.items() if any(f['row']['actual_func_type']==typename for f in c['functions'])]
        function_impacts.append(dict(type=typename,actors=affected,
                                     quests=sorted({q for aid in affected for q in actor_map[aid]['quests']}),
                                     classification='consumer_frontier_not_proven_client_or_server_required'))
    emit('missing-consumer-impacts.json',function_impacts)

    world_path = REPO/'.server_files/AAEmu.Game/Configurations/World.json'
    growth_rate = read_json(world_path)['World']['GrowthRate']
    growth_diffs = [c for c in changes if c['projection']=='es_compact' and c['table']=='doodad_func_growths']
    growth_aligned = [c for c in growth_diffs if set(c['fields'])=={'delay'} and
                      c['fields']['delay']['full']/growth_rate==c['fields']['delay']['projected']]
    emit('growth-rate-alignment.json',dict(runtime_config=str(world_path),sha256=sha(world_path),growth_rate=growth_rate,
                                         compared=len(growth_diffs),aligned_before_climate=len(growth_aligned),
                                         caveat='Static calculation before climate multiplier, not a captured client timer.'))

    native = list(csv.DictReader((OUT/'placements.csv').open(encoding='utf-8-sig')))
    boat = dict(quest=2393, actor=2853,native=[r for r in native if int(r['doodad_id'])==2853], catalogs={})
    for label, base in [('source',REPO),('runtime',REPO/'.server_files')]:
        boat['catalogs'][label]=[dict(file=p.name,**r) for p in (base/'AAEmu.Game/Data/Worlds/main_world').glob('doodad_spawns*.json')
                                 for r in read_json(p) if r['UnitId']==2853]
    emit('boat-placements.json',boat)

    summary = dict(quests=len(matrix),regional=sum(r['zone_id']!=1 for r in matrix),generic_zone1=sum(r['zone_id']==1 for r in matrix),
                   enabled_acts=report['enabled_acts'],act_types=len(report['act_types']),actors=len(actor_map),
                   plantable_actors=sum(bool(a['item_spawn_sources']) for a in actor_map.values()),
                   no_placements_and_no_item_source=sum(not a['placements'] and not a['instance_worlds'] and not a['item_spawn_sources'] for a in actor_map.values()),
                   native_mainworld_placements=len(native),native_catalog_gaps=len(report['missing_placements']),
                   actor_function_types=len(consumers),missing_consumers=[k for k,v in consumers.items() if not v['exists'] or not v['loader_present']],
                   compared_rows=len(compared), missing_full_rows=missing,
                   projection_differences=dict(Counter(c['projection'] for c in changes)),
                   difference_tables={label:dict(Counter(c['table'] for c in changes if c['projection']==label)) for label in paths if label!='full'},
                   growth_rate=growth_rate,growth_differences_aligned=len(growth_aligned),
                   limits=['Catalog membership does not prove an available quest.',
                           'Native main_world placements also include non-Nuia geography for shared actors.',
                           'Consumer presence does not prove implementation or end-to-end playability.',
                           'Comparison excludes localized text. Original package is reference, not edited.',
                           'No running-client reproduction of the reported horse/boat symptom. No gameplay changes deployed.'])
    emit('classification.json',summary)
    emit('sources.json', {str(p):sha(p) for p in [*paths.values(),OUT/'audit.json',OUT/'all-world-placements.csv',OUT/'placements.csv']})
    print(json.dumps(summary))


if __name__=='__main__':
    main()
