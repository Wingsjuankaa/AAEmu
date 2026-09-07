#!/usr/bin/env python3
"""Dry-run/apply both r575 Dwarf/Warborn client patches with per-entry rollback."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile

import ApplyAa10SpanishUiLayout as pak_tools
import PatchAa10DwarfWarborn as patch

SENTINELS = pak_tools.SENTINELS + [
    'game/scriptsbin64/x2ui/characterinfo/equip_slot_reinforce/info.alb',
    'game/objects/characters/dwarf/female/hair/hair01/dw_f_hair01.chr',
]
PLAIN_HASHES = ('87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F',
                'ED288C43AA1D459BCFC56D5433A6E52D1EECF42E2D3F1C25D8BC9BF4F13860B3')


def atomic_copy(source, destination):
    destination = Path(destination)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.aa10-dwarf-', delete=False) as stream:
        staging = Path(stream.name)
        with Path(source).open('rb') as src:
            shutil.copyfileobj(src, stream)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(staging, destination)
    finally:
        staging.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, default=pak_tools.CLIENT)
    parser.add_argument('--backup-root', type=Path, default=pak_tools.ROOT / 'backups/client-patches')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    pak = pak_tools.preflight(args.client, args.apply)
    patch.require(not (args.client / patch.RACE_ENTRY).exists(), 'Loose race ALB shadows package')
    loose = args.client / patch.DB_ENTRY
    if loose.exists():
        patch.require(loose.resolve() == loose.absolute() and loose.stat().st_nlink == 1,
                      'Loose DB is shared or redirected')
        patch.require(patch.hashes.sha256(loose) in PLAIN_HASHES, 'Unknown loose DB')
    now = datetime.now(timezone.utc)
    work = args.backup_root / now.strftime('aa10-dwarf-warborn-%Y%m%d-%H%M%S-%fZ')
    work.mkdir(parents=True, exist_ok=False)
    effective = work / 'effective'
    listing = work / 'entries.txt'
    listing.write_text('\n'.join([*patch.CONTRACTS, *SENTINELS]) + '\n', encoding='utf-8')
    print(pak_tools.run('dotnet', pak_tools.BATCH, pak, listing, effective), flush=True)
    entries = patch.build(effective, work / 'replacements', args.client / 'Bin64/archeage.exe')
    if loose.exists():
        plain = work / 'replacements/game.patched.plain.sqlite3'
        if not plain.exists():
            patch.transform(work / 'replacements/game.sqlite3', plain,
                            patch.read_key(args.client / 'Bin64/archeage.exe'))
        patch.hashes.require_exact(plain, PLAIN_HASHES[1], patch.CONTRACTS[patch.DB_ENTRY][0])
        backup = work / 'loose-backup/game.sqlite3'
        backup.parent.mkdir(parents=True)
        shutil.copy2(loose, backup)
        entries.append(dict(kind='loose', entry=str(loose), size=loose.stat().st_size,
                            before=patch.hashes.sha256(backup), after=PLAIN_HASHES[1],
                            replacement=str(plain), rollback=str(backup)))
    sentinels = {name: patch.hashes.sha256(effective / name.removeprefix('game/')) for name in SENTINELS}
    size = pak.stat().st_size
    print('Hashing complete game_pak before operation...', flush=True)
    before = patch.hashes.sha256(pak)
    manifest = dict(schema_version=1, patch_id='aa10-dwarf-warborn-hair-v1',
                    time_utc=now.isoformat(), applied=False, game_pak=str(pak),
                    repository_head=pak_tools.run('git', '-C', pak_tools.REPO, 'rev-parse', 'HEAD'),
                    sha256_before=before, size_before=size, entries=entries, sentinels=sentinels,
                    x2game_sha256=pak_tools.X2_HASH,
                    executable_sha256=patch.hashes.sha256(args.client / 'Bin64/archeage.exe'),
                    retail_acceptance='pending')
    path = work / 'manifest.json'

    def save():
        path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    def write(entry):
        if entry.get('kind') == 'loose':
            patch.hashes.require_exact(Path(entry['entry']), entry['before'], entry['size'])
            atomic_copy(entry['replacement'], entry['entry'])
            return
        print(pak_tools.run('dotnet', pak_tools.REPLACE, pak, entry['entry'], entry['replacement'], entry['before']), flush=True)

    def verify():
        for entry in entries:
            if entry.get('kind') == 'loose':
                patch.hashes.require_exact(Path(entry['entry']), entry['after'], entry['size'])
                entry['verified_sha256'] = entry['after']
                continue
            destination = work / 'verified' / entry['entry']
            actual = pak_tools.extract(pak, entry['entry'], destination)
            patch.require(actual == entry['after'] and destination.stat().st_size == entry['size'], 'Entry verification failed')
            entry['verified_sha256'] = actual
        for name, expected in sentinels.items():
            patch.require(pak_tools.extract(pak, name, work / 'verified' / name) == expected, f'Sentinel changed: {name}')
        patch.require(pak.stat().st_size == size, 'Package length changed')

    def restore(entry):
        if entry.get('kind') == 'loose':
            current = patch.hashes.sha256(Path(entry['entry']))
            if current == entry['before']:
                return
            patch.require(current == entry['after'], 'Unknown loose DB after failure')
            atomic_copy(entry['rollback'], entry['entry'])
            patch.hashes.require_exact(Path(entry['entry']), entry['before'])
            return
        output = work / 'rollback-inspect' / entry['entry']
        current = pak_tools.extract(pak, entry['entry'], output)
        if current == entry['before']:
            return
        patch.require(current == entry['after'], f'Unknown post-failure entry: {entry["entry"]}')
        pak_tools.run('dotnet', pak_tools.REPLACE, pak, entry['entry'], entry['rollback'], current)
        patch.require(pak_tools.extract(pak, entry['entry'], output) == entry['before'], 'Rollback verification failed')

    save()
    try:
        if args.apply:
            # Recheck that the client did not start during extraction/hashing.
            pak_tools.preflight(args.client, True)
            pak_tools.transaction(entries, write, verify, restore)
            manifest['applied'] = True
        changed = args.apply and any(e['before'] != e['after'] for e in entries)
        print('Hashing complete game_pak after operation...' if changed else 'No package bytes changed.', flush=True)
        manifest['sha256_after'] = patch.hashes.sha256(pak) if changed else before
        manifest['size_after'] = pak.stat().st_size
        manifest['state'] = 'applied' if changed else 'already_patched' if args.apply else 'dry_run'
    except Exception as error:
        manifest['state'], manifest['error'] = 'failed', str(error)
        raise
    finally:
        save()
    print(f"{manifest['state']}: {path}", flush=True)


if __name__ == '__main__':
    main()
