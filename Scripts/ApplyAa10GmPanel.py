"""Atomic GM panel + DDS install; dry-run by default, sparse rehearsal and rollback."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import ApplyAa10SpanishUiLayout as tools
import ApplyAa10AlphaShortcut as hud
import Aa10PakAppend as append
import PatchAa10GmPanel as patch

STAMP = 1789862400

def unchanged_records(before, after, indices):
    if len(before) != len(after): raise ValueError('Unexpected index size')
    for index in indices:
        start = index * 336
        before = before[:start] + after[start:start+336] + before[start+336:]
    if before != after: raise ValueError('Unrelated index record changed')

def hashes(pak, changes, tail_offset, final_tail):
    before, after = hashlib.sha256(), hashlib.sha256()
    with pak.open('rb') as stream:
        def shared(length):
            while length:
                block = stream.read(min(length, 8*1024*1024))
                if not block: raise ValueError('Truncated package')
                before.update(block); after.update(block); length -= len(block)
        for offset, data in sorted(changes):
            shared(offset-stream.tell()); before.update(stream.read(len(data))); after.update(data)
        shared(tail_offset-stream.tell()); before.update(stream.read()); after.update(final_tail)
    return before.hexdigest().upper(), after.hexdigest().upper()

def restore(pak, results, original_tail, tail_offset, final_tail, indices, work):
    with pak.open('rb') as stream:
        stream.seek(tail_offset); current = stream.read()
    if current == final_tail:
        append.write_suffix(pak, tail_offset, current, (work/'tail.intermediate.bin').read_bytes())
    for result in reversed(results):
        current = tools.extract(pak, result['entry'], work/'rollback-inspect'/f"{Path(result['name']).name}.alb")
        if current == result['before']: continue
        if current != result['after']: raise ValueError('Unknown ALB during rollback')
        tools.run('dotnet', tools.REPLACE, pak, result['entry'], result['rollback'], result['after'])
    with pak.open('rb') as stream: offset, current, _, _ = append.read_tail(stream)
    if offset != tail_offset: raise ValueError('Unexpected table during rollback')
    unchanged_records(original_tail, current, indices)
    append.write_suffix(pak, offset, current, original_tail)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true'); args = parser.parse_args()
    pak = tools.preflight(tools.CLIENT, args.apply); stat = pak.stat()
    contract = json.loads(patch.CONTRACTS.read_text(encoding='utf-8'))
    asset = contract['icon']; package = contract['package']
    icon = Path(__file__).parent/asset['source']; patch.v1.require_exact(icon, asset['sha256'])
    work = tools.ROOT/'backups/client-patches'/datetime.now(timezone.utc).strftime('aa10-gm-panel-%Y%m%d-%H%M%S-%fZ')
    work.mkdir(parents=True)
    sentinels = tools.SENTINELS + ['game/scriptsbin64/x2ui/inventory/sort_bag.alb',
        'game/scriptsbin64/x2ui/inventory/sort_inventory.alb', 'game/ui/custom/aaemu/private_alpha.dds',
        'game/ui/custom/aaemu/bug_report.dds']
    names = list(sentinels)
    for entry in contract['entries']:
        names += [f"game/scriptsbin64/x2ui/{entry['name']}.alb", f"game/scripts/x2ui/{entry['name']}.lua"]
    for name in names+[asset['entry']]:
        if (tools.CLIENT/name).exists(): raise ValueError('Loose shadow: '+name)
    (work/'entries.txt').write_text('\n'.join(names)+'\n', encoding='utf-8')
    tools.run('dotnet', tools.BATCH, pak, work/'entries.txt', work/'effective')
    results = patch.build(work/'effective', work/'replacements', tools.LUAC)
    for r in results:
        r['entry'] = f"game/scriptsbin64/x2ui/{r['name']}.alb"
        r['rollback'] = str(work/'effective'/r['entry'].removeprefix('game/'))
        os.utime(r['replacement'], (STAMP, STAMP))
    checks = {n:patch.v1.sha256(work/'effective'/n.removeprefix('game/')) for n in sentinels}
    checks.update({r['entry']:r['after'] for r in results}); checks[asset['entry']] = asset['sha256']
    with pak.open('rb') as stream:
        tail_offset, original_tail, count, _ = append.read_tail(stream)
        initial = append.prepare(stream, asset['entry'], icon.read_bytes())
    positions = hud.locate(original_tail, count, names)
    indices = [positions[r['entry']][0] for r in results]
    already = all(r['before'] == r['after'] for r in results)
    if already != initial['already'] or any(r['before']==r['after'] for r in results) != already:
        raise ValueError('Partial install; use recorded rollback before retrying')
    (work/'tail.original.bin').write_bytes(original_tail)
    if already:
        plan = initial; before = after = patch.v1.sha256(pak)
    else:
        fixture = work/'rehearsal.pak'; fixture.touch()
        tools.run('fsutil', 'sparse', 'setflag', fixture)
        with fixture.open('r+b') as dest, pak.open('rb') as source:
            dest.seek(tail_offset); dest.write(original_tail)
            for _, offset, size in positions.values():
                source.seek(offset); dest.seek(offset); dest.write(source.read(size))
        for r in results: tools.run('dotnet', tools.REPLACE, fixture, r['entry'], r['replacement'], r['before'])
        with fixture.open('rb') as stream: plan = append.prepare(stream, asset['entry'], icon.read_bytes())
        unchanged_records(original_tail, plan['before'], indices)
        (work/'tail.intermediate.bin').write_bytes(plan['before'])
        append.write_suffix(fixture, tail_offset, plan['before'], plan['after'])
        for name, expected in checks.items():
            if tools.extract(fixture, name, work/'rehearsal-verified'/name) != expected: raise ValueError('Rehearsal mismatch: '+name)
        restore(fixture, results, original_tail, tail_offset, plan['after'], indices, work)
        for r in results:
            if tools.extract(fixture, r['entry'], work/'rehearsal-restored'/r['entry']) != r['before']: raise ValueError('Rollback mismatch')
        print('Sparse rehearsal, sentinels and rollback passed. Hashing package...', flush=True)
        changes = [(positions[r['entry']][1], Path(r['replacement']).read_bytes()) for r in results]
        before, after = hashes(pak, changes, tail_offset, plan['after'])
    if before != package['after_sha256' if already else 'before_sha256']: raise ValueError('Unrecognized package: '+before)
    if stat.st_size != package['after_size' if already else 'before_size']: raise ValueError('Package size drift')
    final_size = tail_offset + len(plan['after'])
    if package.get('after_sha256') and (after != package['after_sha256'] or final_size != package['after_size']):
        raise ValueError('Planned output drift')
    if args.apply and not package.get('after_sha256'): raise ValueError('Pin the dry-run output before applying')
    (work/'tail.intermediate.bin').write_bytes(plan['before']); (work/'tail.final.bin').write_bytes(plan['after'])
    manifest = dict(patch_id=contract['patch_id'], state='prepared', entries=results, asset=asset,
        sha256_before=before, sha256_after=after, size_before=stat.st_size, size_after=final_size,
        game_pak=str(pak), sentinels=checks, tail_offset=tail_offset, record_indices=indices,
        repository_head=tools.run('git','-C',tools.REPO,'rev-parse','HEAD'), retail_visual_acceptance='pending')
    path = work/'manifest.json'
    def save(): path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    save(); attempted = False
    try:
        if args.apply:
            tools.preflight(tools.CLIENT, True)
            if pak.stat().st_size != stat.st_size or pak.stat().st_mtime_ns != stat.st_mtime_ns: raise ValueError('Package changed')
            if not already:
                attempted = True
                for r in results: tools.run('dotnet', tools.REPLACE, pak, r['entry'], r['replacement'], r['before'])
                append.write_suffix(pak, tail_offset, plan['before'], plan['after'])
            for name, expected in checks.items():
                if tools.extract(pak, name, work/'verified'/name) != expected: raise ValueError('Reextraction mismatch')
            if pak.stat().st_size != final_size or (not already and patch.v1.sha256(pak) != after):
                raise ValueError('Full output mismatch')
            if already and pak.stat().st_mtime_ns != stat.st_mtime_ns:
                raise ValueError('Package changed during idempotence verification')
            manifest['state'] = 'already_patched' if already else 'applied'
        else: manifest['state'] = 'dry_run'
    except Exception as error:
        manifest.update(state='failed', error=str(error)); save()
        if attempted:
            restore(pak, results, original_tail, tail_offset, plan['after'], indices, work)
            if patch.v1.sha256(pak) != before: raise RuntimeError('Full rollback mismatch') from error
            manifest['state'] = 'failed_rolled_back'
        raise
    finally: save()
    print(f"{manifest['state']}: {path}\nSHA-256 after: {after}", flush=True)

if __name__ == '__main__': main()
