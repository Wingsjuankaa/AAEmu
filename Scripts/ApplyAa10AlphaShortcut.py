"""Install alpha HUD ALB plus packed DDS, with a full-index sparse rehearsal.

Dry-run by default. Pin the dry-run full SHA before --apply. Existing payloads
never move; PakEntryReplace owns the ALB write, Aa10PakAppend owns the new asset.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import struct
import uuid
import ApplyAa10SpanishUiLayout as tools
import PatchAa10AlphaShortcut as patch
import Aa10PakAppend as append

STAMP = 1789171200  # 2026-09-12 UTC; deterministic ALB metadata


def locate(tail, count, names):
    wanted = {name.encode('ascii'): name for name in names}
    found = {}
    for index in range(count):
        record = append.aes(tail[index*336:(index+1)*336])
        raw = record[:264].split(b'\0', 1)[0]
        if raw in wanted:
            name = wanted[raw]
            if name in found: raise ValueError('Duplicate entry: '+name)
            offset, size = struct.unpack_from('<qq', record, 264)
            found[name] = (index, offset, size)
    if len(found) != len(wanted): raise ValueError('Missing required package entry')
    return found


def require_only_record_changed(before, after, index):
    start, end = index*336, (index+1)*336
    if len(before) != len(after) or before[:start] != after[:start] or before[end:] != after[end:]:
        raise ValueError('Native writer changed unrelated index bytes')


def rollback(pak, entry, rollback_file, entry_after, index, original_tail, plan):
    with pak.open('rb') as stream: offset, current, _, _ = append.read_tail(stream)
    if current != original_tail:
        # An appended suffix starts at the old table offset, before the new FAT.
        with pak.open('rb') as stream:
            stream.seek(plan['offset']); suffix = stream.read()
        if suffix == plan['after']:
            append.write_suffix(pak, plan['offset'], plan['after'], plan['before'])
    current_hash = tools.extract(pak, entry, rollback_file.parent/f'rollback-current-{uuid.uuid4().hex}.alb')
    original_hash = patch.v1.sha256(rollback_file)
    if current_hash != original_hash:
        if current_hash != entry_after: raise ValueError('Unknown ALB after failure; inspect backup')
        tools.run('dotnet', tools.REPLACE, pak, entry, rollback_file, entry_after)
    with pak.open('rb') as stream: offset, current, _, _ = append.read_tail(stream)
    if offset != plan['offset']: raise ValueError('Unexpected rollback table offset')
    require_only_record_changed(original_tail, current, index)
    append.write_suffix(pak, offset, current, original_tail)


def hash_pair(pak, payload_offset, replacement, tail_offset, final_tail):
    before, after = hashlib.sha256(), hashlib.sha256()
    with pak.open('rb') as stream:
        def shared(length):
            while length:
                block = stream.read(min(length, 8*1024*1024))
                if not block: raise ValueError('Truncated package')
                before.update(block); after.update(block); length -= len(block)
        shared(payload_offset)
        before.update(stream.read(len(replacement))); after.update(replacement)
        shared(tail_offset-stream.tell())
        before.update(stream.read()); after.update(final_tail)
    return before.hexdigest().upper(), after.hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); args = parser.parse_args()
    pak = tools.preflight(tools.CLIENT, False); stat = pak.stat()
    contract = json.loads(patch.CONTRACTS.read_text(encoding='utf-8'))
    spec = contract['entries'][0]; asset = contract['icon']; package = contract['package']
    entry = f"game/scriptsbin64/x2ui/{spec['name']}.alb"
    source_name = f"game/scripts/x2ui/{spec['name']}.lua"
    icon = Path(__file__).parent/asset['source']; patch.v1.require_exact(icon, asset['sha256'])
    sentinels = tools.SENTINELS + ['game/scriptsbin64/x2ui/inventory/sort_bag.alb',
        'game/scriptsbin64/x2ui/inventory/sort_inventory.alb', 'game/ui/custom/aaemu/bug_report.dds']
    for name in [entry, asset['entry']]:
        if (tools.CLIENT/name).exists(): raise ValueError('Loose file shadows package: '+name)
    work = tools.ROOT/'backups/client-patches'/datetime.now(timezone.utc).strftime('aa10-alpha-hud-%Y%m%d-%H%M%S-%fZ')
    work.mkdir(parents=True)
    names = [entry, source_name]+sentinels
    (work/'entries.txt').write_text('\n'.join(names)+'\n', encoding='utf-8')
    tools.run('dotnet', tools.BATCH, pak, work/'entries.txt', work/'effective')
    result = patch.build(work/'effective', work/'replacements', tools.LUAC)[0]
    replacement = Path(result['replacement']); os.utime(replacement, (STAMP, STAMP))
    original = work/'effective'/entry.removeprefix('game/')
    hashes = {n:patch.v1.sha256(work/'effective'/n.removeprefix('game/')) for n in sentinels}
    with pak.open('rb') as stream:
        tail_offset, original_tail, count, extras = append.read_tail(stream)
        initial = append.prepare(stream, asset['entry'], icon.read_bytes())
    (work/'tail.original.bin').write_bytes(original_tail)
    positions = locate(original_tail, count, names)
    index, payload_offset, _ = positions[entry]
    already = result['before'] == result['after'] and initial['already']
    if initial['already'] != (result['before'] == result['after']):
        raise ValueError('Partial patch state; inspect previous rollback manifest')

    if already:
        plan = initial; before = after = patch.v1.sha256(pak)
    else:
        # Sparse full-index fixture: preserve absolute offsets and every encrypted
        # record; copy only changed/verified payloads. Never a runtime client.
        fixture = work/'rehearsal.pak'; fixture.touch(exist_ok=False)
        tools.run('fsutil', 'sparse', 'setflag', fixture)
        with fixture.open('r+b') as target, pak.open('rb') as source:
            target.seek(tail_offset); target.write(original_tail)
            for name, (_, offset, size) in positions.items():
                source.seek(offset); target.seek(offset); target.write(source.read(size))
        tools.run('dotnet', tools.REPLACE, fixture, entry, replacement, result['before'])
        with fixture.open('rb') as stream: plan = append.prepare(stream, asset['entry'], icon.read_bytes())
        require_only_record_changed(original_tail, plan['before'], index)
        append.write_suffix(fixture, plan['offset'], plan['before'], plan['after'])
        checks = {**hashes, entry:result['after'], asset['entry']:asset['sha256']}
        for name, expected in checks.items():
            if tools.extract(fixture, name, work/'rehearsal-verified'/name) != expected:
                raise ValueError('Rehearsal extraction mismatch: '+name)
        rollback(fixture, entry, original, result['after'], index, original_tail, plan)
        if tools.extract(fixture, entry, work/'rehearsal-rollback.alb') != result['before']:
            raise ValueError('Rehearsal rollback failed')
        print('Sparse rehearsal and exact index rollback passed; hashing package...', flush=True)
        before, after = hash_pair(pak, payload_offset, replacement.read_bytes(), tail_offset, plan['after'])
    expected = package.get('after_sha256') if already else package['before_sha256']
    if before != expected: raise ValueError('Unrecognized package: '+before)
    expected_size = package.get('after_size') if already else package['before_size']
    if stat.st_size != expected_size: raise ValueError('Package size drift')
    if package.get('after_size') and tail_offset+len(plan['after']) != package['after_size']:
        raise ValueError('Planned package size drift')
    if package.get('after_sha256') and after != package['after_sha256']: raise ValueError('Planned package drift')
    if args.apply and not package.get('after_sha256'): raise ValueError('Pin dry-run after_sha256 before applying')
    (work/'tail.intermediate.bin').write_bytes(plan['before'])
    (work/'tail.final.bin').write_bytes(plan['after'])
    manifest = dict(patch_id=contract['patch_id'], state='prepared', repository_head=tools.run('git','-C',tools.REPO,'rev-parse','HEAD'),
        game_pak=str(pak), sha256_before=before, sha256_after=after, size_before=stat.st_size,
        size_after=tail_offset+len(plan['after']), entries=[result], asset=asset, sentinels=hashes,
        suffix_offset=tail_offset, record_index=index, rollback=str(original), retail_visual_acceptance='pending')
    path = work/'manifest.json'
    def save(): path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(); attempted = False
    try:
        if args.apply:
            tools.preflight(tools.CLIENT, True)
            if pak.stat().st_mtime_ns != stat.st_mtime_ns or pak.stat().st_size != stat.st_size: raise ValueError('Package drift')
            if not already:
                attempted = True
                tools.run('dotnet', tools.REPLACE, pak, entry, replacement, result['before'])
                append.write_suffix(pak, tail_offset, plan['before'], plan['after'])
            for name, expected in {**hashes, entry:result['after'], asset['entry']:asset['sha256']}.items():
                if tools.extract(pak, name, work/'verified'/name) != expected: raise ValueError('Reextraction mismatch: '+name)
            if pak.stat().st_size != manifest['size_after']: raise ValueError('Package size mismatch')
            if not already and patch.v1.sha256(pak) != after: raise ValueError('Full package hash mismatch')
            manifest['state'] = 'already_patched' if already else 'applied'
        else: manifest['state'] = 'dry_run'
    except Exception as error:
        manifest.update(state='failed',error=str(error)); save()
        if attempted:
            rollback(pak, entry, original, result['after'], index, original_tail, plan)
            if patch.v1.sha256(pak) != before: raise RuntimeError('Full rollback hash mismatch') from error
            manifest['state'] = 'failed_rolled_back'
        raise
    finally: save()
    print(f"{manifest['state']}: {path}\nSHA-256 after: {after}",flush=True)


if __name__ == '__main__': main()
