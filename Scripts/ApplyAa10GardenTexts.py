"""Dry-run/apply the reviewed Garden compact repair, preserving entry rollback."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import ApplyAa10SpanishUiLayout as pak_tools
from ApplyAa10DwarfWarborn import atomic_copy
import PatchAa10GardenTexts as patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    client = pak_tools.CLIENT
    pak = pak_tools.preflight(client, args.apply)
    work = pak_tools.ROOT / 'backups/client-patches' / datetime.now(timezone.utc).strftime('aa10-garden-text-%Y%m%d-%H%M%S-%fZ')
    work.mkdir(parents=True)
    listing = work / 'entries.txt'
    listing.write_text('\n'.join([patch.ENTRY, *pak_tools.SENTINELS]) + '\n', encoding='utf-8')
    print(pak_tools.run('dotnet', pak_tools.BATCH, pak, listing, work / 'effective'), flush=True)
    source = work / 'effective/db/compact.sqlite3'
    entry = patch.build(source, work / 'replacement/compact.sqlite3')
    loose = client / patch.ENTRY
    patch.require(loose.stat().st_nlink == 1 and patch.sha(loose) == entry['before'], 'Loose compact differs or is shared')
    backup = work / 'loose.before.sqlite3'
    shutil.copy2(loose, backup)
    entries = [entry, dict(entry=str(loose), kind='loose', before=entry['before'], after=entry['after'],
                          replacement=entry['replacement'], rollback=str(backup), size=entry['size'])]
    sentinels = {n: patch.sha(work / 'effective' / n.removeprefix('game/')) for n in pak_tools.SENTINELS}
    print('Hashing complete game_pak before operation...', flush=True)
    stamp = pak.stat()
    before = patch.sha(pak)
    manifest = dict(patch_id='aa10-garden-text-v1', state='prepared', entries=entries, game_pak=str(pak),
                    sha256_before=before, size_before=stamp.st_size, sentinels=sentinels,
                    head=pak_tools.run('git', '-C', pak_tools.REPO, 'rev-parse', 'HEAD'), retail_acceptance='pending')
    path = work / 'manifest.json'
    def save():
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    def write(e):
        if e.get('kind') == 'loose':
            patch.require(patch.sha(loose) == e['before'], 'Loose compact changed during preparation')
            atomic_copy(e['replacement'], loose)
        else:
            print(pak_tools.run('dotnet', pak_tools.REPLACE, pak, e['entry'], e['replacement'], e['before']), flush=True)
    def verify():
        patch.require(pak_tools.extract(pak, patch.ENTRY, work / 'verified/compact.sqlite3') == entry['after'], 'Pak re-extraction differs')
        patch.require(patch.sha(loose) == entry['after'], 'Loose compact differs after operation')
        for n, expected in sentinels.items():
            patch.require(pak_tools.extract(pak, n, work / 'verified' / n) == expected, 'Unrelated sentinel changed')
        patch.require(pak.stat().st_size == stamp.st_size, 'Package grew')
    def restore(e):
        if e.get('kind') == 'loose':
            current = patch.sha(loose)
            if current == e['before']:
                return
            patch.require(current == e['after'], 'Unknown loose compact after failure')
            atomic_copy(e['rollback'], loose)
            patch.require(patch.sha(loose) == e['before'], 'Loose rollback failed')
        else:
            current = pak_tools.extract(pak, e['entry'], work / 'rollback-inspect/compact.sqlite3')
            if current == e['before']:
                return
            patch.require(current == e['after'], 'Unknown packed compact after failure')
            pak_tools.run('dotnet', pak_tools.REPLACE, pak, e['entry'], e['rollback'], current)
            patch.require(pak_tools.extract(pak, e['entry'], work / 'rollback-verified/compact.sqlite3') == e['before'], 'Pak rollback failed')
    save()
    try:
        if args.apply:
            pak_tools.preflight(client, True)
            patch.require(pak.stat().st_size == stamp.st_size and pak.stat().st_mtime_ns == stamp.st_mtime_ns,
                          'Package changed during preparation')
            pak_tools.transaction(entries, write, verify, restore)
        changed = args.apply and entry['before'] != entry['after']
        print('Hashing complete game_pak after operation...' if changed else 'No package bytes changed.', flush=True)
        manifest.update(state='applied' if changed else 'already_patched' if args.apply else 'dry_run',
                        sha256_after=patch.sha(pak) if changed else before, size_after=pak.stat().st_size)
    except Exception as error:
        manifest.update(state='failed', error=str(error))
        raise
    finally:
        save()
    print(f"{manifest['state']}: {path}", flush=True)


if __name__ == '__main__':
    main()
