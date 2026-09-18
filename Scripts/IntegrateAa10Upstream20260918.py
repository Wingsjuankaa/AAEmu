"""Additive AA10 schema migration. Default: validate and print the plan.
--apply requires stopped Game for the live database. Never rewrites existing player rows.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'upstream-20260918-30837660a'
FILES = [
    '2026-09-17_aaemu_game_rank_scores.sql',
    '2026-09-17_aaemu_game_rank_game_points.sql',
    '2026-09-17_aaemu_game_rank_payouts.sql',
    '2026-09-17_aaemu_game_second_passwords.sql',
    '2026-09-18_aaemu_game_rank_records.sql',
    '2026-09-18_aaemu_game_rank_scores_sub_data.sql',
]

def sql(query, database='aaemu_game'):
    if database not in ('aaemu_game', 'aaemu_mergecheck_20260918'):
        raise ValueError('Unexpected database')
    command = ['docker', 'exec', '-i', 'aaemu10-db-1', 'sh', '-c',
               'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -u root -N -B ' + database]
    result = subprocess.run(command, input=query.encode('utf-8'), capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout.decode('utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--database', default='aaemu_game',
                        choices=['aaemu_game', 'aaemu_mergecheck_20260918'])
    args = parser.parse_args()
    database = args.database
    columns = {}
    for row in sql('SELECT table_name,column_name FROM information_schema.columns '
                   'WHERE table_schema=DATABASE();', database).splitlines():
        table, column = row.split('\t')
        columns.setdefault(table, set()).add(column)
    plan = []
    for filename in FILES:
        source = (ROOT / 'SQL/updates' / filename).read_text(encoding='utf-8-sig')
        source = re.sub(r'^\s*USE aaemu_game;\s*', '', source, flags=re.I)
        match = re.search(r'CREATE TABLE IF NOT EXISTS `([^`]+)`', source)
        if match:
            table = match[1]
            expected = set(re.findall(r'^\s*`([^`]+)`', source, re.M))
            if table in columns:
                if not expected.issubset(columns[table]):
                    raise RuntimeError('Existing incompatible table: ' + table)
                continue
            plan.append(source)
            columns[table] = expected
        elif 'ADD COLUMN `sub_data`' in source:
            if 'sub_data' not in columns['character_rank_scores']:
                plan.append(source)
        else:
            raise RuntimeError('Unrecognized statement: ' + filename)
    plan.extend([
        'CREATE TABLE IF NOT EXISTS aa10_integration_migrations '
        '(id varchar(100) PRIMARY KEY, applied_at datetime NOT NULL);',
        "INSERT IGNORE INTO aa10_integration_migrations VALUES ('" + MARKER + "',UTC_TIMESTAMP());"
    ])
    if args.apply:
        if database == 'aaemu_game':
            state = subprocess.check_output(
                ['docker', 'inspect', '-f', '{{.State.Running}}', 'aaemu10-game-1'], text=True).strip()
            if state != 'false':
                raise RuntimeError('Stop Game after backing up before applying the live migration')
        for statement in plan:
            sql(statement, database)
        print(json.dumps({'database': database, 'marker': MARKER, 'statements': len(plan)}))
    else:
        print('\n\n'.join(plan))

if __name__ == '__main__':
    main()
