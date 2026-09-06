#!/usr/bin/env python3
"""Default: dry-run. --apply installs; --rollback MANIFEST [--apply] restores.

Only the client embedded and loose compact are targets. Uses the native AAPak
tools with exact entry identities. Never edits the authoritative forensic DB.
"""
import argparse
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import PatchAa10WorldLevelDisabled as builder

REPO = Path(__file__).resolve().parents[1]
CLIENT = Path('E:/AAEmu/rama_10/client/ArcheAge-Returns-10.0.2.13-r575')
BACKUPS = Path('E:/AAEmu/rama_10/backups/client-patches')
ENTRY = 'game/db/compact.sqlite3'
EXTRACT = REPO / 'reconstruccion_cliente_10/tools/PakEntryExtract/bin/Release/net10.0/PakEntryExtract.dll'
REPLACE = REPO / 'Tools/PakEntryReplace/bin/Release/net10.0/PakEntryReplace.dll'
PROBES = {
    'game/ui/map/map_resources/w_white_forest/line.dds': 'D50E227CF4AE6C21156DF50577BFC1AB',
    'game/ui/icon/icon_item_shotgun_0024.dds': 'E448E8B3ADD4626B91701BC6A95B1B03',
}


def run(*args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'Command failed ({result.returncode}): {result.stdout}\n{result.stderr}')
    return result.stdout


def extract(pak, target):
    run('dotnet', EXTRACT, pak, ENTRY, target)


def replace(pak, target, expected):
    print(run('dotnet', REPLACE, pak, ENTRY, target, expected), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    pak, loose = CLIENT / 'game_pak', CLIENT / 'game/db/compact.sqlite3'
    if args.apply and 'archeage.exe' in run('tasklist', '/FI', 'IMAGENAME eq archeage.exe', '/FO', 'CSV').lower():
        raise RuntimeError('Close archeage.exe before applying this patch')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%fZ')
    work = BACKUPS / ('aa10-world-level-disabled-' + stamp)
    work.mkdir(parents=True, exist_ok=False)
    manifest = dict(patch='aa10-world-level-disabled-r575-v1', utc=stamp,
                    head=run('git', '-C', REPO, 'rev-parse', 'HEAD').strip(),
                    applied=False, rollback=bool(args.rollback), game_pak=str(pak),
                    size=pak.stat().st_size, artifacts={})
    def save():
        (work / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Manifest: {work / "manifest.json"}', flush=True)
    print('Hashing full game_pak before operation...', flush=True)
    initial_mtime = pak.stat().st_mtime_ns
    manifest['pak_before'] = builder.sha256(pak)
    save()
    extract(pak, work / 'embedded.before.sqlite3')
    shutil.copyfile(loose, work / 'loose.before.sqlite3')
    restore = None
    if args.rollback:
        restore = json.loads(args.rollback.read_text(encoding='utf-8-sig'))
        if restore.get('patch') != manifest['patch'] or not restore.get('applied') or restore.get('rollback'):
            raise ValueError('Rollback requires a successful installation manifest')
    for profile in ('embedded', 'loose'):
        source, output = work / f'{profile}.before.sqlite3', work / f'{profile}.after.sqlite3'
        before = builder.sha256(source)
        if (builder.PROFILES.get(before) or builder.PATCHED.get(before)) != profile:
            raise ValueError(f'Unknown {profile} identity: {before}')
        if restore:
            old = restore['artifacts'][profile]
            backup = Path(old['backup'])
            original_profile = builder.PROFILES.get(old['before']) or builder.PATCHED.get(old['before'])
            if original_profile != profile or before != old['after'] or builder.sha256(backup) != old['before']:
                raise ValueError('Rollback identity mismatch')
            shutil.copyfile(backup, output)
        else:
            builder.build(source, output)
        after = builder.sha256(output)
        if source.stat().st_size != output.stat().st_size:
            raise ValueError('Size changed')
        manifest['artifacts'][profile] = dict(before=before, after=after,
            backup=str(source), replacement=str(output), size=source.stat().st_size)
    save()
    attempted, loose_attempted = False, False
    try:
        if args.apply:
            if 'archeage.exe' in run('tasklist', '/FI', 'IMAGENAME eq archeage.exe', '/FO', 'CSV').lower():
                raise RuntimeError('Client opened during preparation; close it before applying')
            e, l = manifest['artifacts']['embedded'], manifest['artifacts']['loose']
            # Recheck loose immediately before mutations; AAPak checks the embedded hash.
            if builder.sha256(loose) != l['before']:
                raise ValueError('Loose database changed during preparation')
            if e['before'] != e['after']:
                attempted = True
                replace(pak, e['replacement'], e['before'])
            if l['before'] != l['after']:
                loose_attempted = True
                shutil.copyfile(l['replacement'], loose)
            extract(pak, work / 'embedded.verified.sqlite3')
            if builder.sha256(work / 'embedded.verified.sqlite3') != e['after'] or builder.sha256(loose) != l['after']:
                raise ValueError('Reextraction verification failed')
            manifest['applied'] = True
        if pak.stat().st_size != manifest['size']:
            raise ValueError('Package size changed')
    except Exception as error:
        manifest['error'] = str(error)
        save()
        if loose_attempted:
            shutil.copyfile(manifest['artifacts']['loose']['backup'], loose)
        if attempted:
            extract(pak, work / 'embedded.failure.sqlite3')
            actual = builder.sha256(work / 'embedded.failure.sqlite3')
            e = manifest['artifacts']['embedded']
            if actual == e['after']:
                replace(pak, e['backup'], actual)
                extract(pak, work / 'embedded.restored.sqlite3')
                if builder.sha256(work / 'embedded.restored.sqlite3') != e['before']:
                    raise RuntimeError('Rollback verification failed; preserve manifest for recovery')
            elif actual != e['before']:
                raise RuntimeError('Unexpected partial entry; preserve manifest for recovery')
        manifest['failure_rolled_back'] = True
        save()
        raise
    if attempted:
        print('Hashing full game_pak after operation...', flush=True)
        manifest['pak_after'] = builder.sha256(pak)
    else:
        if pak.stat().st_mtime_ns != initial_mtime:
            raise ValueError('Package modified outside this operation')
        manifest['pak_after'] = manifest['pak_before']
        manifest['pak_hash_reused_without_write'] = True
    if not attempted and manifest['pak_after'] != manifest['pak_before']:
        raise ValueError('Package changed outside this operation')
    manifest['unrelated_resources'] = {}
    for index, (entry, expected_md5) in enumerate(PROBES.items()):
        probe = work / f'probe-{index}.dds'
        run('dotnet', EXTRACT, pak, entry, probe)
        actual_md5 = hashlib.md5(probe.read_bytes()).hexdigest().upper()
        if actual_md5 != expected_md5:
            raise ValueError(f'Unrelated package resource integrity failed: {entry}')
        manifest['unrelated_resources'][entry] = dict(md5=actual_md5, sha256=builder.sha256(probe))
    save()
    changed = any(a['before'] != a['after'] for a in manifest['artifacts'].values())
    print('Applied' if args.apply and changed else 'Already patched' if args.apply else 'Dry-run passed', flush=True)


if __name__ == '__main__':
    main()
