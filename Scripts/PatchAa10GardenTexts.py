"""Restore empty native Garden phase texts polluted by unrelated localization.

Only the reviewed eight en_us cells change. Mechanical fields and other locales
are preserved; the exact effective Spanish compact is the input contract.
"""
import argparse
from contextlib import closing
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import sqlite3

CONTRACT = Path(__file__).with_name('data') / 'aa10-garden-text-contract.json'
ENTRY = 'game/db/compact.sqlite3'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ro(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)


def repair(db, entries):
    require(not db.execute("select 1 from sqlite_master where type='trigger'").fetchall(), 'Unexpected triggers')
    changed = 0
    for e in entries:
        require(e['table'] == 'doodad_func_groups' and e['column'] in ('name', 'phase_msg', 'title_msg'), 'Unknown field')
        raw = db.execute(f"select {e['column']},doodad_almighty_id from doodad_func_groups where id=?", (e['id'],)).fetchall()
        require(raw == [('', e['doodad'])], 'Native phase identity or empty text differs')
        key = e['table'], e['column'], e['id']
        values = db.execute('select en_us from localized_texts where tbl_name=? and tbl_column_name=? and idx=?', key).fetchall()
        require(values in [[(e['before'],)], [(e['after'],)]], 'Unknown localized text or duplicate identity')
        if values == [(e['before'],)]:
            db.execute('update localized_texts set en_us=? where tbl_name=? and tbl_column_name=? and idx=?', (e['after'], *key))
            changed += 1
    return changed


def verify(before, after, entries):
    allowed = {(e['table'], e['column'], e['id']): e['after'] for e in entries}
    with closing(ro(before)) as a, closing(ro(after)) as b:
        schema = 'select type,name,tbl_name,sql from sqlite_master order by type,name'
        require(a.execute(schema).fetchall() == b.execute(schema).fetchall(), 'Schema changed')
        for (table,) in a.execute("select name from sqlite_master where type='table' order by name"):
            if table == 'localized_texts':
                columns = [r[1] for r in a.execute('pragma table_info(localized_texts)')]
                en = columns.index('en_us')
                for x, y in itertools.zip_longest(a.execute('select * from localized_texts order by id'), b.execute('select * from localized_texts order by id')):
                    require(x is not None and y is not None, 'Row count changed')
                    key = tuple(x[columns.index(k)] for k in ('tbl_name','tbl_column_name','idx'))
                    expected = list(x)
                    if key in allowed:
                        expected[en] = allowed[key]
                    require(tuple(expected) == y, 'Unrelated localization changed')
            else:
                require(all(x == y for x, y in itertools.zip_longest(a.execute(f'SELECT * FROM "{table}"'), b.execute(f'SELECT * FROM "{table}"'))), f'Mechanical table changed: {table}')
        require(b.execute('pragma integrity_check').fetchall() == [('ok',)], 'SQLite integrity failed')


def build(source, output):
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    before = sha(source)
    require(source.stat().st_size == contract['size'], 'Unknown compact size')
    require(before in (contract['input_sha256'], contract.get('output_sha256')), 'Unknown compact hash')
    require(not output.exists() and source.resolve() != output.resolve(), 'Output must be new')
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    with closing(sqlite3.connect(output)) as db, db:
        changed = repair(db, contract['entries'])
        require(repair(db, contract['entries']) == 0, 'Repair is not idempotent')
    require(output.stat().st_size == contract['size'], 'Compact grew')
    verify(source, output, contract['entries'])
    after = sha(output)
    if contract.get('output_sha256'):
        require(after == contract['output_sha256'], 'Non-deterministic output')
    return dict(entry=ENTRY, before=before, after=after, size=output.stat().st_size,
                replacement=str(output), rollback=str(source), changed_cells=changed)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(args.input, args.output), indent=2))
