"""Build an independent, hash-verified r575 Spanish LAN client snapshot.

Dry-run by default. Never edits the source, a PAK entry, server config or Zones.
No hardlinks, credentials, user profiles or translation editor are distributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from datetime import datetime, timezone

ROOT = Path('E:/AAEmu/rama_10')
REPO = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview'
DESTINATION = ROOT/'distributions/AA10-Nuia-Alpha-es_ES-LAN-20260915'
EVIDENCE = ROOT/'artifacts/client-distribution/nuia-lan-20260915'
LAUNCHER = 'AAEmu-Simple-Launcher-Portable-0.2.1-x64.exe'
PINS = {
    'game_pak': 'B70AA4AA707E188BA8736D9770F542109377446EABFCA8142A7517B811FC8C22',
    'Bin64/archeage.exe': '6DF26B74D545313C4E6C3EA195DDABCC0CCED7AA8035986EFD6C31B075A4C248',
    'Bin64/x2game.dll': '405242E05FFF98BD337296355941C657445A65720902DB1D2C905A0CFF549734',
    'game/db/compact.sqlite3': 'E5947F15726BF05C392CDC912BC778F2BFE6E407349A1F3A89BAA818B56C3187',
    'game/db/game.sqlite3': 'ED288C43AA1D459BCFC56D5433A6E52D1EECF42E2D3F1C25D8BC9BF4F13860B3',
    LAUNCHER: '50B6FAB4DAC1485F7F8A4E063A202EF5419BF0B38F49264954BB080B864DCBFF',
}


def sha(path, progress=False):
    h = hashlib.sha256()
    size = path.stat().st_size
    done = 0
    next_notice = 8 * 1024**3
    with path.open('rb') as stream:
        while block := stream.read(16 * 1024**2):
            h.update(block)
            done += len(block)
            if progress and done >= next_notice:
                print(f'Verifying {path.name}: {done/1024**3:.1f}/{size/1024**3:.1f} GiB', flush=True)
                next_notice += 8 * 1024**3
    return h.hexdigest().upper()


def classify(relative):
    name = relative.name.lower()
    parts = tuple(p.lower() for p in relative.parts)
    if relative.as_posix() in PINS:
        return True, 'pinned client runtime'
    if '.bak' in name or 'backups' in parts or '.zonehost-updates' in parts:
        return False, 'development backup/update state'
    if 'gpucache' in parts or name.endswith(('.log', '.dmp')):
        return False, 'local cache or diagnostic log'
    if name.startswith('aaemu.zonehost'):
        return False, 'server ZoneHost executable'
    if parts[0] == 'bin64':
        return True, 'original client libraries/resources retained'
    if relative.as_posix() == 'game/game_decrypted.sqlite3':
        return False, 'empty forensic placeholder (not a runtime database)'
    if len(parts) == 1 and (name.startswith('es_es-') or name.endswith('.cmd')):
        return False, 'local editorial manifest/shortcut; replaced by player launcher'
    raise ValueError(f'Unclassified source file, review before shipping: {relative}')


def inventory():
    rows = []
    for path in sorted(SOURCE.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Redirected source path: {path}')
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE)
        include, reason = classify(relative)
        stat = path.stat()
        if relative.as_posix() == 'game/game_decrypted.sqlite3' and stat.st_size != 0:
            raise ValueError('Forensic placeholder changed; inspect before excluding')
        rows.append(dict(path=relative.as_posix(), bytes=stat.st_size,
                         mtime_ns=stat.st_mtime_ns, include=include, reason=reason))
    selected = {r['path'] for r in rows if r['include']}
    if not set(PINS) <= selected:
        raise ValueError('A required client file is missing')
    for relative, expected in PINS.items():
        if relative != 'game_pak' and sha(SOURCE/relative) != expected:
            raise ValueError(f'Pinned source changed: {relative}')
    if (SOURCE/'game_pak').stat().st_size != 92412641792:
        raise ValueError('PAK size changed; inspect latest patch checkpoint')
    for name in ('compact.sqlite3', 'game.sqlite3'):
        path = SOURCE/'game/db'/name
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
                raise ValueError(f'Invalid SQLite: {name}')
    return rows


def copy_verified_source(row, destination):
    source = SOURCE/row['path']
    target = destination/row['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name+'.partial')
    h = hashlib.sha256()
    count = 0
    next_notice = 8 * 1024**3
    with source.open('rb') as incoming, temporary.open('xb') as outgoing:
        while block := incoming.read(16 * 1024**2):
            outgoing.write(block)
            h.update(block)
            count += len(block)
            if count >= next_notice:
                print(f'Copying {row["path"]}: {count/1024**3:.1f}/{row["bytes"]/1024**3:.1f} GiB', flush=True)
                next_notice += 8 * 1024**3
        outgoing.flush()
        os.fsync(outgoing.fileno())
    after = source.stat()
    if count != row['bytes'] or after.st_size != row['bytes'] or after.st_mtime_ns != row['mtime_ns']:
        raise ValueError(f'Source changed during copy: {row["path"]}')
    digest = h.hexdigest().upper()
    if row['path'] in PINS and digest != PINS[row['path']]:
        raise ValueError(f'Copy source does not match approved identity: {row["path"]}')
    temporary.rename(target)
    if os.path.samefile(source, target) or target.stat().st_nlink != 1:
        raise ValueError(f'Distribution aliases the source: {target}')
    return dict(path=row['path'], bytes=count, sha256=digest, origin='client snapshot')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    rows = inventory()
    selected = [r for r in rows if r['include']]
    total = sum(r['bytes'] for r in selected)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    plan = dict(source=str(SOURCE), destination=str(DESTINATION), files=len(selected),
                bytes=total, gib=round(total/1024**3, 3),
                excluded_files=len(rows)-len(selected),
                excluded_bytes=sum(r['bytes'] for r in rows if not r['include']), inventory=rows)
    (EVIDENCE/'inventory.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in plan.items() if k!='inventory'}), flush=True)
    if not args.apply:
        return
    if DESTINATION.exists():
        raise ValueError('Destination exists; do not overwrite a previous distribution')
    if DESTINATION.is_relative_to(SOURCE) or SOURCE.is_relative_to(DESTINATION):
        raise ValueError('Source/destination overlap')
    if shutil.disk_usage(DESTINATION.parent).free < total + 2*1024**3:
        raise ValueError('Insufficient space for an independent physical copy')
    DESTINATION.mkdir()
    (DESTINATION/'BUILD-INCOMPLETE.txt').write_text('Do not distribute: verification pending.\n')
    # Copy PAK first so the large immutable content is pinned before shipping extras.
    selected.sort(key=lambda r: (r['path'] != 'game_pak', r['path']))
    files = [copy_verified_source(row, DESTINATION) for row in selected]
    for path in sorted((REPO/'Scripts/ClientDistribution').iterdir()):
        if not path.is_file():
            continue
        target = DESTINATION/path.name
        with path.open('rb') as src, target.open('xb') as dest:
            shutil.copyfileobj(src, dest)
        files.append(dict(path=path.name, bytes=target.stat().st_size,
                          sha256=sha(target), origin='distribution helper'))
    print('Checking every destination hash independently...', flush=True)
    for row in files:
        target = DESTINATION/row['path']
        if target.stat().st_size != row['bytes'] or sha(target, row['path']=='game_pak') != row['sha256']:
            raise ValueError(f'Destination verification failed: {row["path"]}')
    for row in rows:
        source = SOURCE/row['path']
        if row['include'] and (source.stat().st_mtime_ns != row['mtime_ns'] or source.stat().st_size != row['bytes']):
            raise ValueError(f'Source changed after snapshot: {row["path"]}')
    manifest = dict(schema=1, build='AA10-Nuia-Alpha-es_ES-LAN-20260915',
                    created_utc=datetime.now(timezone.utc).isoformat(),
                    product_locale='es_ES', runtime_locale='en_us',
                    login_host='192.168.100.20', login_port=1237, player_tcp_ports=[1237,1239,1250],
                    source_pak_sha256=PINS['game_pak'], source_unchanged=True,
                    physical_copy=True, all_destination_hashes_verified=True,
                    acceptance_on_second_pc='pending', files=files,
                    total_bytes=sum(row['bytes'] for row in files))
    content=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    (DESTINATION/'MANIFEST-SHA256.json').write_text(content, encoding='utf-8')
    (EVIDENCE/'distribution-manifest.json').write_text(content, encoding='utf-8')
    (DESTINATION/'BUILD-INCOMPLETE.txt').unlink()
    print(f'VERIFIED DISTRIBUTION: {DESTINATION}', flush=True)


if __name__ == '__main__':
    main()
