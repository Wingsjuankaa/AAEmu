"""Read-only r575 branch inventory; AA8 is a comparison, never a data source.

Outputs an explicit dependency graph. Tag memberships are boundary evidence, not
an invitation to import every skill which shares a generic tag such as stun.
Runtime/client comparisons exclude names/descriptions only; field differences
remain visible. Presence in this report does not certify gameplay.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def digest(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class Database:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        self.db.row_factory = sqlite3.Row
        self.names = {r[0] for r in self.db.execute("select name from sqlite_master where type='table'")}
        self.cache = {}
        self.indexes = {}

    def rows(self, table):
        if table not in self.cache:
            self.cache[table] = [dict(r) for r in self.db.execute(f'SELECT * FROM "{table}" ORDER BY id')] if table in self.names else []
        return self.cache[table]

    def by(self, table, key, value):
        if (table, key) not in self.indexes:
            index = collections.defaultdict(list)
            for row in self.rows(table):
                index[row.get(key)].append(row)
            self.indexes[table, key] = index
        return self.indexes[table, key].get(value, [])


def normalized(key, value):
    # AA8's recovered runtime serializes PostgreSQL booleans as 0/1 and
    # nullable numeric references as zero. Keep original values in the report.
    if value in ('t', 'f'):
        return int(value == 't')
    if value is None and key.endswith('_id'):
        return 0
    return value


def build(args):
    full, runtime, client = (Database(p) for p in (args.full, args.runtime, args.client))
    result = {'schema_version': 1, 'ability_id': args.ability, 'sources': {},
              'boundary': 'Reachable skill/effect/plot/buff/controller rows and authored requirements; tags are terminal membership evidence. Dynamic acceptance is not inferred.',
              'tables': {}, 'missing': [], 'invalid_references': [], 'edges': [], 'skills': []}
    for name, db in [('full', full), ('runtime', runtime), ('localized_client', client)]:
        result['sources'][name] = {'path': str(db.path), 'sha256': digest(db.path),
            'quick_check': db.db.execute('pragma quick_check').fetchone()[0],
            'integrity_check': db.db.execute('pragma integrity_check').fetchone()[0]}
    roots = full.by('skills', 'ability_id', args.ability)
    passives = full.by('passive_buffs', 'ability_id', args.ability)
    queue = collections.deque()
    visited = set()
    tables = collections.defaultdict(dict)
    def add(table, row):
        tables[table][row['id']] = row
    def link(table, ident, origin, relation):
        if not ident:
            return
        if not isinstance(ident, int):
            result['invalid_references'].append({'from': origin, 'relation': relation, 'value': ident})
            return
        result['edges'].append({'from': origin, 'relation': relation, 'to': f'{table}:{ident}'})
        queue.append((table, ident))
    def related(table, key, ident):
        rows = full.by(table, key, ident)
        for row in rows:
            add(table, row)
        return rows
    def concrete(kind):
        return re.sub(r'(?<!^)(?=[A-Z])', '_', kind).lower() + 's'
    def owners(kind, ident):
        for table in ('unit_reqs', 'skill_modifiers', 'unit_modifiers', 'buff_unit_modifiers', 'buff_modifiers', 'dynamic_unit_modifiers'):
            for row in full.by(table, 'owner_id', ident):
                if row.get('owner_type') == kind:
                    add(table, row)
                    result['edges'].append({'from': f'{kind}:{ident}', 'relation': table, 'to': f"{table}:{row['id']}"})
                    if table == 'buff_unit_modifiers' and row.get('enable') == 't':
                        link('buffs', row.get('buff_id'), f'{kind}:{ident}', 'modifier_buff')
    for row in roots:
        queue.append(('skills', row['id']))
    for row in passives:
        add('passive_buffs', row)
        link('buffs', row['buff_id'], f"passive_buffs:{row['id']}", 'passive')
    while queue:
        table, ident = queue.popleft()
        if (table, ident) in visited:
            continue
        visited.add((table, ident))
        rows = full.by(table, 'id', ident)
        if not rows:
            result['missing'].append({'table': table, 'id': ident})
            continue
        row = rows[0]
        add(table, row)
        origin = f'{table}:{ident}'
        if table == 'skills':
            owners('Skill', ident)
            link('plots', row.get('plot_id'), origin, 'plot')
            link('skill_controllers', row.get('skill_controller_id'), origin, 'controller')
            link('combat_resources', row.get('combat_resource_id'), origin, 'resource')
            for col in ('toggle_buff_id', 'channeling_buff_id', 'channeling_target_buff_id'):
                link('buffs', row.get(col), origin, col)
            for effect in related('skill_effects', 'skill_id', ident):
                if effect.get('enable') == 't':
                    link('effects', effect['effect_id'], origin, 'enabled_skill_effect')
            for heir in related('heir_skills', 'skill_id', ident):
                for detail in related('heir_skill_details', 'heir_skill_id', heir['id']):
                    link('skills', detail['skill_id'], origin, 'ancestral')
            for req in related('skill_req_skills', 'skill_id', ident):
                link('skill_reqs', req['skill_req_id'], origin, 'requirement')
            related('tagged_skills', 'skill_id', ident)
        elif table == 'plots':
            for event in related('plot_events', 'plot_id', ident):
                eid = event['id']
                result['edges'].append({'from': origin, 'relation': 'contains_event', 'to': f'plot_events:{eid}'})
                for effect in related('plot_effects', 'event_id', eid):
                    link(concrete(effect['actual_type']), effect['actual_id'], f'plot_events:{eid}', 'effect')
                for rel in ('plot_event_conditions', 'plot_aoe_conditions'):
                    for cond in related(rel, 'event_id', eid):
                        link('plot_conditions', cond['condition_id'], f'plot_events:{eid}', rel)
                for edge in related('plot_next_events', 'event_id', eid):
                    nextrow = full.by('plot_events', 'id', edge['next_event_id'])
                    if not nextrow:
                        result['missing'].append({'table': 'plot_events', 'id': edge['next_event_id']})
                    elif nextrow[0]['plot_id'] != ident:
                        link('plots', nextrow[0]['plot_id'], f'plot_events:{eid}', 'cross_plot_edge')
                if event['target_update_method_id'] in (5, 7):
                    link('aoe_shapes', event['target_update_method_param1'], f'plot_events:{eid}', 'shape')
        elif table == 'effects':
            link(concrete(row['actual_type']), row['actual_id'], origin, 'concrete_effect')
        elif table == 'buff_effects':
            link('buffs', row['buff_id'], origin, 'applied_buff')
        elif table == 'combat_resource_effects':
            link('combat_resources', row.get('combat_resource_id'), origin, 'resource')
        elif table == 'combat_resources':
            link('buffs', row.get('buff_id'), origin, 'resource_buff')
        elif table == 'buffs':
            owners('Buff', ident)
            owners('Buffs', ident)
            for col in ('link_buff_id', 'aura_slave_buff_id', 'transform_buff_id', 'crowd_buff_id', 'require_buff_id'):
                link('buffs', row.get(col), origin, col)
            for combat in related('combat_buffs', 'req_buff_id', ident):
                link('buffs', combat['buff_id'], origin, 'combat_buff')
            link('skill_controllers', row.get('skill_controller_id'), origin, 'controller')
            for rel in ('buff_triggers', 'buff_tick_effects'):
                for effect in related(rel, 'buff_id', ident):
                    if effect.get('enable', 't') == 't':
                        link('effects', effect['effect_id'], origin, rel)
                        owners('BuffTrigger' if rel == 'buff_triggers' else 'BuffTickEffect', effect['id'])
            for skill in related('buff_skills', 'buff_id', ident):
                if skill.get('enable') == 't':
                    link('skills', skill['skill_id'], origin, 'buff_skill')
            for swap in related('buff_swap_skills', 'buff_id', ident):
                link('skills', swap['new_skill_id'], origin, 'swap_skill')
            for passive in related('buff_passive_buffs', 'buff_id', ident):
                link('passive_buffs', passive['passive_buff_id'], origin, 'granted_passive')
            related('tagged_buffs', 'buff_id', ident)
            for rel in ('tagged_immune_buffs', 'tagged_require_buffs'):
                related(rel, 'buff_id', ident)
        elif table == 'passive_buffs':
            link('buffs', row['buff_id'], origin, 'passive')
        elif table == 'skill_reqs':
            related('skill_req_skill_tags', 'skill_req_id', ident)
        elif table == 'special_effects':
            if row.get('special_effect_type_id') in (33, 48):
                link('skills', row.get('value1'), origin, 'skill_or_combo')
        elif table == 'skill_controllers':
            link('skills', row.get('end_skill_id'), origin, 'controller_end')
        elif table == 'plot_conditions':
            owners('PlotCondition', ident)
        else:
            owners(''.join(word.title() for word in table.rstrip('s').split('_')), ident)

    result['tables'] = {t: [rows[k] for k in sorted(rows)] for t, rows in sorted(tables.items())}
    # Compare AA8 recovered rows only for common columns, retaining changed values.
    aa8 = json.loads(Path(args.aa8).read_text(encoding='utf-8')) if args.aa8 else {'tables': {}}
    result['aa8_source'] = {'path': args.aa8, 'sha256': digest(args.aa8)} if args.aa8 else None
    ignored = {'name', 'desc', 'web_desc', 'comments', 'name_tr', 'desc_tr', 'web_desc_tr'}
    # Compare the whole extracted runtime graph, not just the root skill rows.
    result['runtime_graph_differences'] = []
    for table, rows in result['tables'].items():
        for row in rows:
            other = runtime.by(table, 'id', row['id'])
            changes = {k: {'full': v, 'runtime': other[0].get(k)} for k, v in row.items()
                       if other and k not in ignored and normalized(k, v) != normalized(k, other[0].get(k))}
            if not other or changes:
                result['runtime_graph_differences'].append({'table': table, 'id': row['id'], 'present': bool(other), 'differences': changes})
    for row in roots:
        ident = row['id']
        localized = client.by('localized_texts', 'idx', ident)
        name = next((r['en_us'] for r in localized if r['tbl_name'] == 'skills' and r['tbl_column_name'] == 'name'), row['name'])
        entry = {'id': ident, 'name': name, 'visible': row['show'] == 't', 'plot_id': row['plot_id'],
                 'range': row['max_range'], 'validation': 'catalog_only', 'comparisons': {}}
        for label, other in [('runtime', runtime.by('skills', 'id', ident)), ('client', client.by('skills', 'id', ident)),
                             ('aa8', [r for r in aa8['tables'].get('skills', []) if r['id'] == ident])]:
            entry['comparisons'][label] = {'present': bool(other), 'differences':
                {k: {'aa10': v, label: other[0][k]} for k, v in row.items() if other and k in other[0] and k not in ignored and normalized(k, v) != normalized(k, other[0][k])}}
        entry['direct_effects'] = len([r for r in full.by('skill_effects', 'skill_id', ident) if r['enable'] == 't'])
        entry['plot_events'] = len(full.by('plot_events', 'plot_id', row['plot_id'])) if row['plot_id'] else 0
        result['skills'].append(entry)
    result['counts'] = {t: len(rows) for t, rows in result['tables'].items()}
    result['missing'] = sorted(result['missing'], key=lambda r: (r['table'], r['id']))
    result['edges'] = sorted(result['edges'], key=lambda r: (r['from'], r['relation'], r['to']))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'catalog.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# Inventario Battlerage r575', '', 'La presencia de datos no equivale a aceptación jugable.', '',
             '| ID | Nombre del cliente | Visible | Plot | Efectos directos | Diferencias AA8 |', '|---:|---|:---:|---:|---:|---:|']
    for r in result['skills']:
        delta = len(r['comparisons']['aa8']['differences']) if r['comparisons']['aa8']['present'] else 'ausente'
        lines.append(f"| {r['id']} | {r['name']} | {'sí' if r['visible'] else 'no'} | {r['plot_id'] or '—'} | {r['direct_effects']} | {delta} |")
    (out / 'inventory.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'roots': len(roots), 'visible': sum(r['show'] == 't' for r in roots),
                      'passives': len(passives), 'counts': result['counts'], 'missing': result['missing']}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ability', type=int, default=1)
    for option in ('full', 'runtime', 'client', 'output'):
        parser.add_argument('--' + option, required=True)
    parser.add_argument('--aa8')
    build(parser.parse_args())
