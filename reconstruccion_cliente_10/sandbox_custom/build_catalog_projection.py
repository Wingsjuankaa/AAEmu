"""Consistent, bounded, read-only-source AA10 catalog export for REA's SQLite input budget."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

TABLES = ['npcs', 'models', 'actor_models', 'zones', 'zone_groups', 'sub_zones',
          'world_groups', 'global_world_names', 'world_contents', 'npc_interaction_sets',
          'npc_interactions', 'skills', 'factions']


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(4*1024*1024), b''):
            result.update(chunk)
    return result.hexdigest()


def build(source, output):
    source, output = source.resolve(), output.resolve()
    allowed = Path('E:/AAEmu/rama_10/forensics/output/aa10-client-forensics/sandbox-custom-20261029').resolve()
    if output.drive.upper() != 'E:' or not output.is_relative_to(allowed) or output.exists():
        raise ValueError('Output must be a new snapshot under the E-only investigation directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    source_hash = digest(source)
    connection = sqlite3.connect(output.as_uri(), uri=True)
    connection.execute('ATTACH DATABASE ? AS source', (source.as_uri()+'?mode=ro&immutable=1',))
    schemas = dict(connection.execute("SELECT name,sql FROM source.sqlite_master WHERE type='table'"))
    manifest = {'kind': 'partial_catalog_projection', 'source': str(source), 'source_sha256': source_hash,
                'source_size': source.stat().st_size, 'scope': 'complete rows of selected tables; not the whole source DB',
                'tables': {}, 'omitted_requested_tables': sorted(set(TABLES)-schemas.keys())}
    with connection:
        for table in sorted(set(TABLES)&schemas.keys()):
            original = schemas[table]
            schema = original[original.index('('):]
            connection.execute(f'CREATE TABLE "{table}" '+schema)
            connection.execute(f'INSERT INTO main."{table}" SELECT * FROM source."{table}" ORDER BY rowid')
            count = connection.execute(f'SELECT count(*) FROM main."{table}"').fetchone()[0]
            assert count == connection.execute(f'SELECT count(*) FROM source."{table}"').fetchone()[0]
            manifest['tables'][table] = {'count': count, 'source_query': f'SELECT * FROM "{table}" ORDER BY rowid',
                                         'original_schema': original}
        connection.execute('CREATE TABLE projection_provenance (manifest_json TEXT NOT NULL)')
        connection.execute('INSERT INTO projection_provenance VALUES (?)', (json.dumps(manifest, sort_keys=True),))
    assert connection.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
    assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    connection.close()
    manifest.update(snapshot_sha256=digest(output), snapshot_size=output.stat().st_size,
                    quick_check='ok', integrity_check='ok')
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'snapshot': str(output), 'sha256': manifest['snapshot_sha256'],
                      'bytes': manifest['snapshot_size'], 'tables': {k:v['count'] for k,v in manifest['tables'].items()}}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output)
