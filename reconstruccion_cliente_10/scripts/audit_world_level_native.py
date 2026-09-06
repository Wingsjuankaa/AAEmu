"""Read-only identity audit of the r575 World Level dossier (requires pefile).

First export functions with Aa10WorldLevelNativeAudit.java in read-only Ghidra.
This compares those bytes with the operational x64 binary, not just its project.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import pefile

ROOT = Path('E:/AAEmu/rama_10')
OUT = ROOT / 'forensics/output/aa10-client-forensics/world-level-frontier'
CLIENT = ROOT / 'client/ArcheAge-Returns-10.0.2.13-r575'
EXPECTED_CLIENT = '405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


binary = CLIENT / 'Bin64/x2game.dll'
if sha(binary) != EXPECTED_CLIENT:
    raise ValueError('Unknown operational client binary')
pe = pefile.PE(str(binary))
if pe.FILE_HEADER.Machine != 0x8664:
    raise ValueError('Expected x86-64')
report = dict(client_sha256=EXPECTED_CLIENT, native=[], databases={}, effective_alb={})
for directory in ('native-client', 'native-disable'):
    files = list((OUT / directory).glob('*.bytes'))
    if not files:
        raise ValueError(f'Missing native exports: {directory}')
    for path in files:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rva, encoded = line.split()
            expected = bytes.fromhex(encoded)
            if pe.get_data(int(rva), len(expected)) != expected:
                raise ValueError(f'Operational bytes mismatch: {path.name}, RVA {rva}')
            report['native'].append(dict(function=path.stem, rva=hex(int(rva)),
                                         size=len(expected), code_sha256=hashlib.sha256(expected).hexdigest()))
for label, path in {
    'authoritative_original': ROOT / 'data/sqlite/authoritative/game_decrypted.sqlite3',
    'embedded_original': OUT / 'pak/db/compact.sqlite3',
    'client_loose_current': CLIENT / 'game/db/compact.sqlite3',
}.items():
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
        report['databases'][label] = dict(path=str(path), sha256=sha(path),
            controls=db.execute('SELECT * FROM system_feature_controls ORDER BY id').fetchall(),
            world_level_tables={table: db.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
                for table in ('world_level_configs', 'world_level_exp_modifiers', 'world_level_hard_caps')})
for path in (OUT / 'pak/scriptsbin64/x2ui').rglob('*.alb'):
    report['effective_alb'][str(path.relative_to(OUT))] = sha(path)
(OUT / 'world-level-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(f'Verified {len(report["native"])} native ranges; saved {OUT / "world-level-audit.json"}')
