"""Derive an offline AA10 sandbox Zone411 catalog; never write a source or runtime DB.

The two known r575 databases retain their schemas, every original row/ROWID,
and their byte length. Only the new zone, its group, two explicit localized
labels and the affected sqlite_sequence values are added. Outputs live below
E:/AAEmu/rama_10/artifacts. Package application and runtime migration are separate.
"""
from __future__ import annotations

import argparse
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.dont_write_bytecode = True
ROOT = Path('E:/AAEmu/rama_10')
CONTRACTS_PATH = Path(__file__).with_name('Aa10SandboxZoneCatalog.contracts.json')
CONTRACTS = json.loads(CONTRACTS_PATH.read_text(encoding='utf-8'))
TABLES = ('zones', 'zone_groups', 'localized_texts')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def quote(identifier):
    return '"'+identifier.replace('"', '""')+'"'


@contextmanager
def readonly(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
    connection.text_factory = lambda value: value.decode('utf-8', errors='surrogateescape')
    try:
        yield connection
    finally:
        connection.close()


def output_path(path):
    path = Path(path).absolute()
    resolved = path.resolve()
    artifacts = (ROOT/'artifacts').resolve()
    if resolved.drive.upper() != 'E:' or not resolved.is_relative_to(artifacts) or resolved == artifacts:
        raise ValueError('Catalog output must stay below E:/AAEmu/rama_10/artifacts')
    if path.exists() or path.is_symlink():
        raise FileExistsError(f'Refusing to replace an existing output: {path}')
    return resolved


def row(connection, sql, args=()):
    cursor = connection.execute(sql, args)
    values = cursor.fetchall()
    if len(values) != 1:
        raise ValueError(f'Expected one exact donor/reference row, found {len(values)}')
    return dict(zip((column[0] for column in cursor.description), values[0]))


def schemas(connection):
    return connection.execute('SELECT type,name,tbl_name,rootpage,sql FROM sqlite_master ORDER BY type,name').fetchall()


def plan(connection):
    donor = CONTRACTS['donor']
    zone = row(connection, 'SELECT * FROM zones WHERE zone_key=?', (donor['zone_key'],))
    group = row(connection, 'SELECT * FROM zone_groups WHERE id=?', (donor['group_id'],))
    if (zone['id'] != donor['zone_row_id'] or zone['group_id'] != donor['group_id'] or
            zone['name'] != donor['name'] or group['name'] != donor['name'] or
            group['target_id'] != donor['group_target_id'] or group['buff_id'] != donor['group_buff_id']):
        raise ValueError('The donor406/group153 binding has drifted')
    # This is an existing retail parent-map reference, not a new WorldTemplateId.
    parent = row(connection, 'SELECT * FROM world_groups WHERE id=?', (group['target_id'],))
    if parent['name'] != 'none' or parent['map_target_type'] != 'WorldGroup':
        raise ValueError('Donor parent-map reference is not the expected retail world_group1')
    new_zone, new_group = CONTRACTS['zone'], CONTRACTS['group']
    if connection.execute('SELECT 1 FROM zones WHERE id=? OR zone_key=? OR lower(name)=lower(?) LIMIT 1',
                          (new_zone['id'], new_zone['zone_key'], new_zone['name'])).fetchone():
        raise ValueError('Zone411, row324 or its name is already occupied')
    if connection.execute('SELECT 1 FROM zone_groups WHERE id=? OR lower(name)=lower(?) LIMIT 1',
                          (new_group['id'], new_group['name'])).fetchone():
        raise ValueError('Zone group159 or its name is already occupied')
    if connection.execute('SELECT 1 FROM sqlite_master WHERE type=? AND tbl_name IN (?,?,?) LIMIT 1',
                          ('trigger', *TABLES)).fetchone():
        raise ValueError('Unexpected triggers on catalog tables')
    zone.update(new_zone)
    group.update(new_group)
    # Preserve physics, ocean, sound and parent-map fields exactly from group153.
    if group['buff_id'] is not None or group['target_id'] != 1:
        raise ValueError('Training group must not introduce a zone buff or a new parent-map link')
    localization = CONTRACTS['localization']
    labels = []
    for table, old_idx, idx, label_id in [
            ('zones', donor['zone_row_id'], new_zone['id'], localization['zones_id']),
            ('zone_groups', donor['group_id'], new_group['id'], localization['zone_groups_id'])]:
        if connection.execute('SELECT 1 FROM localized_texts WHERE id=? OR '
                              '(tbl_name=? AND tbl_column_name=? AND idx=?) LIMIT 1',
                              (label_id, table, localization['column'], idx)).fetchone():
            raise ValueError(f'Localization id/key already occupied for {table}')
        label = row(connection, 'SELECT * FROM localized_texts WHERE tbl_name=? AND tbl_column_name=? AND idx=?',
                    (table, localization['column'], old_idx))
        for key in label:
            if key not in ('id', 'tbl_name', 'tbl_column_name', 'idx'):
                label[key] = localization['text'] if key in localization['filled_language_columns'] else ''
        label.update(id=label_id, idx=idx)
        labels.append(label)
    return {'zones': [zone], 'zone_groups': [group], 'localized_texts': labels}


def stream_query(connection, table, excluded=()):
    info = connection.execute('PRAGMA table_info('+quote(table)+')').fetchall()
    names = {column[1].casefold() for column in info}
    schema = connection.execute('SELECT sql FROM sqlite_master WHERE type=? AND name=?', ('table', table)).fetchone()[0]
    if schema and schema.lstrip().upper().startswith('CREATE VIRTUAL TABLE'):
        raise ValueError(f'Virtual table preservation requires a separate contract: {table}')
    if schema and 'WITHOUT ROWID' in schema.upper():
        keys = [column[1] for column in sorted(info, key=lambda column: column[5]) if column[5]]
        if not keys:
            raise ValueError(f'Missing primary-key ordering for {table}')
        selection, ordering, has_rowid = '*', ','.join(map(quote, keys)), False
    else:
        alias = next((name for name in ('_rowid_', 'rowid', 'oid') if name not in names), None)
        if alias is None:
            raise ValueError(f'All hidden ROWID aliases are shadowed in {table}')
        selection, ordering, has_rowid = quote(alias)+',*', quote(alias), True
    where = ' WHERE id NOT IN ('+','.join('?' for _ in excluded)+')' if excluded else ''
    return connection.execute('SELECT '+selection+' FROM '+quote(table)+where+' ORDER BY '+ordering, excluded), has_rowid


def verify_original_rows(source, output, additions):
    if schemas(source) != schemas(output):
        raise ValueError('The catalog schema/root-page map changed')
    tables = [name for name, in source.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    preserved = {}
    for table in tables:
        if table == 'sqlite_sequence':
            before = source.execute('SELECT rowid,name,seq FROM sqlite_sequence ORDER BY rowid').fetchall()
            expected = [(rid, name, max(seq, max(record['id'] for record in additions[name])))
                        if name in additions else (rid, name, seq) for rid, name, seq in before]
            if expected != output.execute('SELECT rowid,name,seq FROM sqlite_sequence ORDER BY rowid').fetchall():
                raise ValueError('Unexpected sqlite_sequence changes')
            continue
        excluded = tuple(record['id'] for record in additions.get(table, []))
        left, has_rowid = stream_query(source, table)
        right, _ = stream_query(output, table, excluded)
        count = 0
        while True:
            old_rows, new_rows = left.fetchmany(4096), right.fetchmany(4096)
            if old_rows != new_rows:
                raise ValueError(f'An original row/value/ROWID changed in {table} near row {count}')
            count += len(old_rows)
            if not old_rows:
                break
        preserved[table] = {'rows': count, 'rowids_compared': has_rowid}
    for table, records in additions.items():
        for record in records:
            actual = row(output, 'SELECT * FROM '+quote(table)+' WHERE id=?', (record['id'],))
            if actual != record:
                raise ValueError(f'Inserted row does not match the plan: {table}:{record["id"]}')
    return preserved


def _derive_verified(source, output, expected, profile):
    """Internal test seam; the public builder only supplies the frozen production contracts."""
    source, output = Path(source).resolve(), output_path(output)
    if source.drive.upper() != 'E:' or not source.is_file():
        raise ValueError('The source catalog must be an existing file on E')
    for suffix in ('-wal', '-journal'):
        sidecar = Path(str(source)+suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ValueError('Source has pending WAL/journal state; acquire a clean snapshot first')
    identity = source.stat()
    if identity.st_size != expected['bytes'] or digest(source) != expected['sha256'].upper():
        raise ValueError('Input catalog hash/size differs from the frozen r575 source')
    with readonly(source) as original:
        additions = plan(original)  # No output is created on rejected occupancy or donor drift.
        original_schema = schemas(original)
        metadata = {key: original.execute('PRAGMA '+key).fetchone()[0]
                    for key in ('page_size', 'page_count', 'schema_version', 'user_version', 'application_id', 'encoding')}
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name(output.name+'.building')
    manifest_path = output.with_name(output.name+'.manifest.json')
    if stage.exists() or manifest_path.exists():
        raise FileExistsError('Staging file or manifest already exists; refusing to overwrite it')
    copy_hash = hashlib.sha256()
    with source.open('rb') as original, stage.open('xb') as staged:
        while data := original.read(4*1024*1024):
            staged.write(data)
            copy_hash.update(data)
        staged.flush()
        os.fsync(staged.fileno())
    if copy_hash.hexdigest().upper() != expected['sha256'].upper():
        raise ValueError('Source changed while copying; the staging file is not promotable')
    connection = sqlite3.connect(stage)
    connection.text_factory = lambda value: value.decode('utf-8', errors='surrogateescape')
    connection.execute('PRAGMA temp_store=MEMORY')
    connection.execute('PRAGMA journal_mode=DELETE')
    connection.execute('PRAGMA synchronous=FULL')
    connection.execute('PRAGMA foreign_keys=ON')
    def authorize(action, first, second, database, trigger):
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            permitted = (database == 'main' and trigger is None and
                         (action == sqlite3.SQLITE_INSERT and first in TABLES or
                          first == 'sqlite_sequence' and action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE)))
            return sqlite3.SQLITE_OK if permitted else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    connection.set_authorizer(authorize)
    try:
        with connection:
            for table, records in additions.items():
                for record in records:
                    columns = ','.join(map(quote, record))
                    placeholders = ','.join('?' for _ in record)
                    connection.execute('INSERT INTO '+quote(table)+' ('+columns+') VALUES ('+placeholders+')', tuple(record.values()))
        connection.set_authorizer(None)
        if connection.total_changes != 4:
            raise ValueError('The catalog transaction performed more than four inserts')
        for check in ('quick_check', 'integrity_check'):
            if connection.execute('PRAGMA '+check).fetchall() != [('ok',)]:
                raise ValueError(f'Derived catalog failed {check}')
        for key, value in metadata.items():
            if connection.execute('PRAGMA '+key).fetchone()[0] != value:
                raise ValueError(f'Derived catalog changed {key}; same-size/source metadata contract failed')
        with readonly(source) as original:
            preserved = verify_original_rows(original, connection, additions)
        if schemas(connection) != original_schema:
            raise ValueError('Schema changed during verification')
    finally:
        connection.close()
    if stage.stat().st_size != identity.st_size:
        raise ValueError('Derived catalog byte length changed')
    after_identity = source.stat()
    if ((identity.st_size, identity.st_mtime_ns, identity.st_ino) !=
            (after_identity.st_size, after_identity.st_mtime_ns, after_identity.st_ino) or
            digest(source) != expected['sha256'].upper()):
        raise ValueError('The original source changed during the build')
    if output.exists():
        raise FileExistsError('Output appeared during the build; refusing to overwrite it')
    stage.rename(output)
    manifest = {'patch_id': CONTRACTS['patch_id'], 'profile': profile, 'sqlite_version': sqlite3.sqlite_version,
                'source': {'path': str(source), 'sha256': expected['sha256'].upper(), 'bytes': identity.st_size},
                'output': {'path': str(output), 'sha256': digest(output), 'bytes': output.stat().st_size},
                'quick_check': 'ok', 'integrity_check': 'ok', 'source_unchanged': True,
                'schema_unchanged': True, 'original_rows_and_rowids_equal': True,
                'inserted_rows': additions, 'preserved_tables': preserved,
                'metadata': metadata, 'role': 'tool-authored derived sandbox catalog; not retail authority'}
    with manifest_path.open('x', encoding='utf-8') as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
        manifest_file.write('\n')
    return manifest


def build(source, output, profile):
    if profile not in CONTRACTS['sources']:
        raise ValueError('Choose the frozen full or compact source profile')
    return _derive_verified(source, output, CONTRACTS['sources'][profile], profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profile', choices=('full', 'compact'), required=True)
    args = parser.parse_args()
    manifest = build(args.source, args.output, args.profile)
    print(json.dumps({'manifest': str(args.output)+'.manifest.json', 'output': manifest['output'],
                      'preserved_tables': len(manifest['preserved_tables']),
                      'inserted_rows': {table: len(rows) for table, rows in manifest['inserted_rows'].items()}}))


if __name__ == '__main__':
    main()
