"""Read-only AA10 skill closure and deterministic knowledge database. Python 3.13.

Run: python audit.py --output <new forensic output directory>
The original sources and runtime are never modified. Outputs are replaceable evidence.
"""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path('E:/AAEmu/rama_10')
SOURCE = ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3'
EXPECTED_SHA = '87531f4bf066904b4b82d0324c6a9c741de38df4fbf9fc95d0ba211287e3702f'
TABLE_QUERIES = {
    'skills': 'id=36473',
    'plots': 'id=2957',
    'plot_events': 'plot_id=2957',
    'plot_next_events': 'event_id IN (SELECT id FROM plot_events WHERE plot_id=2957)',
    'plot_effects': 'event_id IN (SELECT id FROM plot_events WHERE plot_id=2957)',
    'plot_event_conditions': 'event_id IN (SELECT id FROM plot_events WHERE plot_id=2957)',
    'plot_aoe_conditions': 'event_id IN (SELECT id FROM plot_events WHERE plot_id=2957)',
    'plot_conditions': 'id IN (SELECT condition_id FROM plot_event_conditions WHERE event_id IN (SELECT id FROM plot_events WHERE plot_id=2957))',
    'special_effects': "id IN (SELECT actual_id FROM plot_effects WHERE actual_type='SpecialEffect' AND event_id IN (SELECT id FROM plot_events WHERE plot_id=2957))",
    'damage_effects': "id IN (SELECT actual_id FROM plot_effects WHERE actual_type='DamageEffect' AND event_id IN (SELECT id FROM plot_events WHERE plot_id=2957))",
    'buff_effects': "id IN (SELECT actual_id FROM plot_effects WHERE actual_type='BuffEffect' AND event_id IN (SELECT id FROM plot_events WHERE plot_id=2957))",
    'aoe_shapes': 'id IN (SELECT target_update_method_param1 FROM plot_events WHERE plot_id=2957 AND target_update_method_id IN (5,6,7))',
    'projectiles': 'id IN (840,1400)',
    'projectile_params': "owner_type='Projectile' AND owner_id IN (840,1400)",
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    actual_sha = sha(SOURCE)
    if actual_sha != EXPECTED_SHA:
        raise SystemExit('Source hash changed: review this fixture before regenerating evidence.')
    args.output.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(SOURCE.as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    rows = {table: [dict(r) for r in source.execute(f'SELECT * FROM "{table}" WHERE {query} ORDER BY id')]
            for table, query in TABLE_QUERIES.items()}
    nodes = {r['id'] for r in rows['plot_events']}
    edges = rows['plot_next_events']
    reached, pending = set(), [24561]
    while pending:
        current = pending.pop()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(r['next_event_id'] for r in edges if r['event_id'] == current)
    dangling = [r['id'] for r in edges if r['event_id'] not in nodes or r['next_event_id'] not in nodes]
    if dangling:
        raise SystemExit(f'Dangling edges: {dangling}')
    fixture = ROOT / 'server/AAEmu/AAEmu.UnitTests/Game/Models/Game/Skills/Plots/Fixtures/Neblina2957.json'
    expected_fixture = json.loads(fixture.read_text(encoding='utf8'))
    projected = {t: [{k: v for k, v in r.items() if k not in ('name', 'comments')} for r in rows[t]]
                 for t in expected_fixture}
    if projected != expected_fixture:
        raise SystemExit('Embedded test fixture differs from authoritative rows.')
    db_path = args.output / 'knowledge.sqlite3'
    if db_path.exists():
        raise SystemExit('Use a new output directory; existing knowledge database is preserved.')
    db = sqlite3.connect(db_path)
    db.executescript('''
        CREATE TABLE source(id TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL);
        CREATE TABLE entity(source_id TEXT NOT NULL REFERENCES source(id), table_name TEXT NOT NULL,
          row_id INTEGER NOT NULL, row_json TEXT NOT NULL, PRIMARY KEY(source_id,table_name,row_id));
        CREATE TABLE event(event_id INTEGER PRIMARY KEY, reachable INTEGER NOT NULL, tickets INTEGER NOT NULL);
        CREATE TABLE edge(edge_id INTEGER PRIMARY KEY, source_event INTEGER NOT NULL REFERENCES event(event_id),
          target_event INTEGER NOT NULL REFERENCES event(event_id), per_target INTEGER NOT NULL, delay_ms INTEGER NOT NULL,
          failure_edge INTEGER NOT NULL);
        CREATE TABLE finding(id TEXT PRIMARY KEY, status TEXT NOT NULL, evidence TEXT NOT NULL);
    ''')
    db.execute('INSERT INTO source VALUES(?,?,?)', ('full', str(SOURCE), actual_sha))
    for table, entries in rows.items():
        db.executemany('INSERT INTO entity VALUES(?,?,?,?)',
                       [('full', table, r['id'], json.dumps(r, ensure_ascii=False, sort_keys=True)) for r in entries])
    db.executemany('INSERT INTO event VALUES(?,?,?)', [(r['id'], int(r['id'] in reached), r['tickets']) for r in rows['plot_events']])
    db.executemany('INSERT INTO edge VALUES(?,?,?,?,?,?)',
                   [(r['id'], r['event_id'], r['next_event_id'], int(r['per_target'] == 't'), r['delay'], int(r['fail'] == 't')) for r in edges])
    findings = [
        ('unit_list', 'client-native', 'r575 x64 SHA405242e0... RVA0xAB74D0: u8 count then actual Bc unit references; locations are separate PlotObj values.'),
        ('fixed_effect', 'client-native', 'RVA0x6CE380/0x6CDC70: source=4 or target=4 iterates unit list; all other selectors execute once.'),
        ('position_projectile', 'client-native', 'RVA0x6CB250 supports PlotObj type2 independently of a target unit.'),
        ('nested_tickets', 'server-required', 'Native graph: event24562 budget10 forks into subcycle24565 budget6. Sibling histories must not spend each other budgets.'),
        ('range8', 'server-required', 'condition8619 has range0..8 independently of selection shape11421 radius30.'),
        ('sixth_filler', 'open', 'Real PlotTree filler fixture emits5; SetVariable36838 increments a before NOT(a>5) on24575. No proven native World ordering/snapshot contract yet.'),
        ('random_area_height', 'open', 'Full AA10 p4 terrain semantics remain unproven. The additive +8m lift was removed after the 20260911 videos; existing terrain/water/portal policy is preserved.'),
        ('random_area_additive_lift', 'server-required', 'Video1812 shows upward filler. Native chain24565/24854/24575 was Z+0,+8,+1. Removing the unconfirmed p4 addition leaves the explicit Area.p5=1000; geometry tested at four headings.'),
        ('close_damage', 'open', 'Tooltip20% reduction is not acceptance of a damage formula. adjust_damage_by_range and native formula require further closure.'),
        ('retail_acceptance', 'pending', 'User confirms restored volleys but rejects upward trajectories and apparent homing. Direction correction is deployed separately; final rendering/targeting acceptance remains open.'),
    ]
    db.executemany('INSERT INTO finding VALUES(?,?,?)', findings)
    db.commit()
    integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    foreign_keys = db.execute('PRAGMA foreign_key_check').fetchall()
    db.close()
    manifest = {'source': str(SOURCE), 'source_sha256': actual_sha, 'fixture_sha256': sha(fixture),
                'skill_id': 36473, 'plot_id': 2957, 'event_count': len(nodes),
                'reachable_events': sorted(reached), 'unreachable_events': sorted(nodes - reached),
                'dangling_edges': dangling, 'integrity_check': integrity, 'foreign_key_errors': foreign_keys,
                'knowledge_sha256': sha(db_path), 'findings': findings}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: manifest[k] for k in ('event_count', 'integrity_check', 'knowledge_sha256')}))


if __name__ == '__main__':
    main()
