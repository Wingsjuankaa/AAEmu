"""Read-only racial quest audit for the Nuia alpha; writes evidence only.

Run once to produce requested-ids.txt, run PakDoodadScan against those IDs,
then run again with placements.csv in the output directory. Absence without
native placement evidence is never classified as a missing spawn.
"""
import argparse
import csv
import json
import sqlite3
from collections import Counter
from pathlib import Path

import audit_hiram_onward_quests as spatial
from build_quest_stage40 import inspect_server, inspect_loader_tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=spatial.ROOT /
                        'forensics/output/aa10-client-forensics/nuia-alpha-20260915')
    args = parser.parse_args()
    # Race is a bit mask: Elf=8 and Dwarf=4, not their enum values 4 and 3.
    spatial.SCOPE = 'category_id IN (8,93) OR (category_id=131 AND (race & 12) != 0)'
    spatial.OUT = args.output
    spatial.main(validate_overlay=False)
    report = json.loads((args.output / 'audit.json').read_text(encoding='utf-8'))
    root, repo = spatial.ROOT, spatial.REPO

    def connect(path):
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        db.row_factory = sqlite3.Row
        return db

    full = connect(root / 'data/sqlite/authoritative/game_decrypted.sqlite3')
    client_path = root / 'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/game/db/compact.sqlite3'
    client = connect(client_path)
    tm_path = root / 'localization/aa10-es-es/translation_memory.sqlite3'
    tm = connect(tm_path)
    classes, loaders, objective_types, stubs, _, _ = inspect_server(repo)
    loader_tables = inspect_loader_tables(repo)
    all_ids = ','.join(str(q['id']) for q in report['quests'])
    components = spatial.rows(full, f'SELECT * FROM quest_components WHERE quest_context_id IN ({all_ids})')
    component_quest = {c['id']: c['quest_context_id'] for c in components}
    acts = spatial.rows(full, f'SELECT * FROM quest_acts WHERE quest_component_id IN '
                        f'(SELECT id FROM quest_components WHERE quest_context_id IN ({all_ids})) ORDER BY id')
    details = {}
    unsupported = []
    for act in acts:
        if act['enable'] != 't':
            continue
        typ = act['act_detail_type']
        if typ not in classes or typ not in loaders or typ in stubs:
            unsupported.append(dict(quest=component_quest[act['quest_component_id']], **act))
        table = loader_tables.get(typ, spatial.table_name(typ))
        details[act['id']] = spatial.rows(full, f'SELECT * FROM {table} WHERE id=?', (act['act_detail_id'],))[0]

    zones = {r['id']: r for r in spatial.rows(full, '''SELECT z.id,z.name,z.zone_key,z.group_id,g.target_id
        FROM zones z JOIN zone_groups g ON g.id=z.group_id''')}
    missing_by_quest = {}
    for missing in report['missing_placements']:
        actor = next(a for a in report['actors'] if a['id'] == missing['actor'])
        for quest in actor['quests']:
            missing_by_quest.setdefault(quest, set()).add(actor['id'])
    loc_rows, matrix, crossrefs = [], [], []
    tables = [('quest_contexts', 'name', 'id'), ('quest_names', 'name', 'quest_context_id'),
              ('quest_context_texts', 'text', 'quest_context_id'),
              ('quest_component_texts', 'text', 'quest_component_id'),
              ('quest_chat_bubbles', 'speech', 'quest_component_id')]
    selected_tables = {t[0] for t in tables}
    units = {(r['tbl_name'], r['tbl_column_name'], r['idx']): r
             for r in tm.execute('SELECT * FROM units') if r['tbl_name'] in selected_tables}
    installed = {(r['tbl_name'], r['tbl_column_name'], r['idx']): (r['en_us'],)
                 for r in client.execute('SELECT tbl_name,tbl_column_name,idx,en_us FROM localized_texts')
                 if r['tbl_name'] in selected_tables}
    by_quest = {q['id']: [] for q in report['quests']}
    for table, column, foreign in tables:
        # Read projected text identities, including disabled authored rows; retain
        # enabled metadata separately rather than silently approving/excluding them.
        for row in spatial.rows(full, f'SELECT * FROM {table}'):
            quest = component_quest.get(row[foreign]) if foreign == 'quest_component_id' else row[foreign]
            if quest not in by_quest:
                continue
            key = (table, column, row['id'])
            unit = units.get(key)
            # The generated TM can predate editorial review. The contextual JSONL
            # shadows it even when the new revision is blocked or draft.
            editorial = root / f'localization/aa10-es-es/segments/contextual/{table}/{column}--{row["id"]}.jsonl'
            if editorial.exists():
                lines = [json.loads(line) for line in editorial.read_text(encoding='utf-8').splitlines() if line.strip()]
                if len(lines) != 1 or (lines[0]['key']['tbl_name'], lines[0]['key']['tbl_column_name'], lines[0]['key']['idx']) != key:
                    raise ValueError(f'Ambiguous editorial identity: {editorial}')
                target = lines[0]['target']
                unit = dict(status=target['status'], target_es=target['es_ES'], segment_path=str(editorial), line_number=1)
            text = installed.get(key)
            if not text and not unit:
                continue
            state = 'approved_installed' if unit and unit['status'] == 'approved' and text and text[0] == unit['target_es'] else (
                'approved_drift' if unit and unit['status'] == 'approved' else (unit['status'] if unit else 'missing_unit'))
            loc = dict(quest=quest, table=table, column=column, idx=row['id'], state=state,
                       enabled=row.get('enable'), installed=text[0] if text else None,
                       segment=unit['segment_path'] if unit else None, line=unit['line_number'] if unit else None)
            loc_rows.append(loc)
            by_quest[quest].append(loc)
    for q in sorted(report['quests'], key=lambda q: (q['category_id'],q['chapter_idx'],q['quest_idx'],q['id'])):
        qacts = [a for a in acts if component_quest[a['quest_component_id']] == q['id'] and a['enable'] == 't']
        for act in qacts:
            detail = details[act['id']]
            if act['act_detail_type'] == 'QuestActConAcceptComponent' and detail['quest_context_id'] != q['id']:
                crossrefs.append(dict(quest=q['id'], component=act['quest_component_id'], linked_quest=detail['quest_context_id']))
        zone = zones.get(q['zone_id'], {})
        title = next((r['installed'] for r in by_quest[q['id']] if r['table'] == 'quest_contexts'), '')
        matrix.append(dict(**q, title_es=title, race='elf' if q['category_id']==8 else 'dwarf' if q['category_id']==93 else 'shared',
                           profile=zone.get('name'), zone_key=zone.get('zone_key'), continent=zone.get('target_id'),
                           geography='nuia' if zone.get('target_id')==3 else 'outside_nuia_or_unresolved',
                           enabled_acts=len(qacts), act_types=sorted({a['act_detail_type'] for a in qacts}),
                           missing_doodads=sorted(missing_by_quest.get(q['id'], set())),
                           localization=dict(Counter(r['state'] for r in by_quest[q['id']])),
                           acceptance='pending_retail'))
    groups = {}
    for race in ('elf','dwarf','shared'):
        subset = [r for r in matrix if r['race']==race]
        groups[race] = dict(quests=len(subset), enabled_acts=sum(r['enabled_acts'] for r in subset),
                           act_types=sorted({t for r in subset for t in r['act_types']}),
                           quest_zones=sorted({r['zone_key'] for r in subset if r['zone_key']}),
                           outside_nuia=[r['id'] for r in subset if r['geography']!='nuia'],
                           missing_spawn_quests=[r['id'] for r in subset if r['missing_doodads']])
    report.update(groups=groups, unsupported_acts=unsupported, crossrefs=crossrefs,
                  localization_summary=dict(Counter(r['state'] for r in loc_rows)),
                  client_compact_sha256=spatial.sha(client_path), tm_sha256=spatial.sha(tm_path),
                  limitations=['Static coverage is not retail acceptance.',
                               'Quest zone is a catalog hint, not a proof of every spatial dependency.',
                               'NPC spawn lifecycle, item producers, cinematics and transformation require dedicated acceptance.',
                               'Localization reads loose compact, TM fallback and authoritative contextual JSONL overrides; package extraction is not performed.'])
    for name, data in [('audit.json', report), ('quest-matrix.json', matrix), ('localization.json', loc_rows)]:
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    with (args.output / 'quest-matrix.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f,fieldnames=matrix[0].keys());writer.writeheader();writer.writerows(matrix)
    if (args.output / 'npc-native').exists():
        import audit_hiram_quest_suppliers as suppliers
        suppliers.OUT = args.output
        suppliers.main()
    print(json.dumps(dict(groups=groups,unsupported=len(unsupported),localization=report['localization_summary'])))


if __name__ == '__main__':
    main()
