"""Dry-run/apply the r575 private-alpha UI and catalog with per-entry rollback."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import ApplyAa10SpanishUiLayout as pak_tools
from ApplyAa10DwarfWarborn import atomic_copy
import PatchAa10PrivateAlpha as patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    client = pak_tools.CLIENT
    # Reading/validating an already patched package is safe with the client open.
    # Require it closed before any operation that would actually write bytes.
    pak = pak_tools.preflight(client, False)
    work = pak_tools.ROOT / 'backups/client-patches' / datetime.now(timezone.utc).strftime('aa10-private-alpha-%Y%m%d-%H%M%S-%fZ')
    work.mkdir(parents=True)
    contract = json.loads(patch.CONTRACT.read_text(encoding='utf-8'))
    listing = work / 'entries.txt'
    names = [e['entry'] for e in contract['entries']] + ['game/scripts/x2ui/inventory/sort_bag.lua', *pak_tools.SENTINELS]
    listing.write_text('\n'.join(names) + '\n', encoding='utf-8')
    print(pak_tools.run('dotnet', pak_tools.BATCH, pak, listing, work / 'effective'), flush=True)
    entries = patch.build(work / 'effective', work / 'replacement', pak_tools.LUAC)
    packed = list(entries)
    compact = next(e for e in entries if e['entry'] == 'game/db/compact.sqlite3')
    loose = client / compact['entry']
    patch.require(loose.stat().st_nlink == 1 and patch.sha(loose) == compact['before'], 'Loose compact differs or is shared')
    for e in entries:
        if e['entry'].endswith('.alb'):
            patch.require(not (client / e['entry']).exists(), 'Loose ALB shadows the package')
    backup = work / 'loose.before.sqlite3'
    shutil.copy2(loose, backup)
    entries.append(dict(entry=str(loose), kind='loose', before=compact['before'], after=compact['after'],
                        replacement=compact['replacement'], rollback=str(backup), size=compact['size']))
    needs_write = any(e['before'] != e['after'] for e in entries)
    if args.apply and needs_write:
        pak_tools.preflight(client, True)
    sentinels = {n: patch.sha(work / 'effective' / n.removeprefix('game/')) for n in pak_tools.SENTINELS}
    print('Hashing complete game_pak before operation...', flush=True)
    stamp = pak.stat(); before = patch.sha(pak)
    manifest = dict(patch_id=contract['patch_id'], state='prepared', entries=entries, game_pak=str(pak),
                    sha256_before=before, size_before=stamp.st_size, sentinels=sentinels,
                    server_catalog=str(work / 'replacement/private_alpha_catalog.json'),
                    head=pak_tools.run('git', '-C', pak_tools.REPO, 'rev-parse', 'HEAD'), retail_acceptance='pending')
    path = work / 'manifest.json'
    def save(): path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    def write(e):
        if e.get('kind') == 'loose':
            patch.require(patch.sha(loose) == e['before'], 'Loose compact changed during preparation')
            atomic_copy(e['replacement'], loose)
        else:
            print(pak_tools.run('dotnet', pak_tools.REPLACE, pak, e['entry'], e['replacement'], e['before']), flush=True)
    def verify():
        for e in packed:
            target = work / 'verified' / e['entry']
            patch.require(pak_tools.extract(pak, e['entry'], target) == e['after'], 'Pak re-extraction differs')
            patch.require(target.stat().st_size == e['size'], 'Entry size changed')
        patch.require(patch.sha(loose) == compact['after'], 'Loose compact differs after operation')
        for n, expected in sentinels.items():
            patch.require(pak_tools.extract(pak, n, work / 'verified' / n) == expected, 'Unrelated sentinel changed')
        patch.require(pak.stat().st_size == stamp.st_size, 'Package grew')
    def restore(e):
        if e.get('kind') == 'loose':
            current = patch.sha(loose)
            if current == e['before']: return
            patch.require(current == e['after'], 'Unknown loose compact after failure')
            atomic_copy(e['rollback'], loose)
            patch.require(patch.sha(loose) == e['before'], 'Loose rollback failed')
        else:
            current = pak_tools.extract(pak, e['entry'], work / 'rollback-inspect' / e['entry'])
            if current == e['before']: return
            patch.require(current == e['after'], 'Unknown packed entry after failure')
            pak_tools.run('dotnet', pak_tools.REPLACE, pak, e['entry'], e['rollback'], current)
            patch.require(pak_tools.extract(pak, e['entry'], work / 'rollback-verified' / e['entry']) == e['before'], 'Pak rollback failed')
    save()
    try:
        if args.apply:
            if needs_write:
                pak_tools.preflight(client, True)
            patch.require(pak.stat().st_size == stamp.st_size and pak.stat().st_mtime_ns == stamp.st_mtime_ns, 'Package changed during preparation')
            pak_tools.transaction(entries, write, verify, restore)
        changed = args.apply and any(e['before'] != e['after'] for e in entries)
        print('Hashing complete game_pak after operation...' if changed else 'No package bytes changed.', flush=True)
        manifest.update(state='applied' if changed else 'already_patched' if args.apply else 'dry_run',
                        sha256_after=patch.sha(pak) if changed else before, size_after=pak.stat().st_size,
                        catalog_sha256=patch.sha(manifest['server_catalog']))
    except Exception as error:
        manifest.update(state='failed', error=str(error)); raise
    finally: save()
    print(f"{manifest['state']}: {path}", flush=True)


if __name__ == '__main__':
    main()
