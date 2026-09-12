"""Install V3 packed icon over pinned V2; dry-run default. Requires cryptography.

Separate index-append boundary, preserving all native entry bytes and offsets.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import ApplyAa10SpanishUiLayout as tools
import PatchAa10BugReports as patch
import Aa10PakAppend as append

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    client=tools.CLIENT;pak=tools.preflight(client,False)
    contract=json.loads(Path(__file__).with_name('Aa10BugReportPackedIcon.contracts.json').read_text(encoding='utf-8'))
    asset=contract['icon'];package=contract['packed_icon_package']
    source=Path(__file__).parent/asset['source'];patch.v1.require_exact(source,asset['sha256'])
    loose=client/asset['entry']
    if not loose.resolve().is_relative_to(client.resolve()): raise ValueError('Asset escapes client')
    loose_hash=patch.v1.sha256(loose) if loose.exists() else None
    if loose.exists() and (loose.stat().st_nlink!=1 or loose_hash!=asset['previous_loose_sha256']):
        raise ValueError('Unknown or shared loose icon')
    stat=pak.stat()
    with pak.open('rb') as stream: plan=append.prepare(stream,asset['entry'],source.read_bytes())
    print('Hashing pinned package and planned package...',flush=True)
    prefix=hashlib.sha256()
    with pak.open('rb') as stream:
        left=plan['offset']
        while left:
            block=stream.read(min(left,8*1024*1024))
            if not block: raise ValueError('Truncated package')
            prefix.update(block);left-=len(block)
    before_hash=prefix.copy();before_hash.update(plan['before']);before=before_hash.hexdigest().upper()
    after_hash=prefix.copy();after_hash.update(plan['after']);after=after_hash.hexdigest().upper()
    expected=package.get('after_sha256') if plan['already'] else package['before_sha256']
    if before!=expected: raise ValueError(f'Unrecognized package {before}')
    if package.get('after_sha256') and after!=package['after_sha256']: raise ValueError('Planned package drift')
    if args.apply and not package.get('after_sha256'): raise ValueError('Pin dry-run output before applying')
    work=tools.ROOT/'backups/client-patches'/datetime.now(timezone.utc).strftime('aa10-bug-reports-packed-icon-%Y%m%d-%H%M%S-%fZ')
    work.mkdir(parents=True)
    (work/'tail.before.bin').write_bytes(plan['before'])
    (work/'tail.after.bin').write_bytes(plan['after'])
    if loose_hash: (work/'loose.before.dds').write_bytes(loose.read_bytes())
    names=tools.SENTINELS+['game/scriptsbin64/x2ui/inventory/sort_bag.alb','game/scriptsbin64/x2ui/inventory/sort_inventory.alb']
    hashes={n:tools.extract(pak,n,work/'effective'/n) for n in names}
    if hashes[names[-1]]!=contract['entries'][0]['patched_sha256']: raise ValueError('Report Lua drift')
    manifest=dict(patch_id=contract['patch_id'],state='prepared',game_pak=str(pak),repository_head=tools.run('git','-C',tools.REPO,'rev-parse','HEAD'),
                  sha256_before=before,sha256_after=after,size_before=stat.st_size,size_after=plan['offset']+len(plan['after']),
                  suffix_offset=plan['offset'],suffix_before_sha256=append.sha(plan['before']),suffix_after_sha256=append.sha(plan['after']),
                  live_entries_before=plan['count'],live_entries_after=plan['count']+(not plan['already']),
                  preserved_encrypted_records=True,asset=asset,sentinels=hashes,loose_before=loose_hash,retail_visual_acceptance='pending')
    path=work/'manifest.json'
    def save(): path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save();changed=False;removed=False
    try:
        if args.apply:
            tools.preflight(client,True)
            if pak.stat().st_mtime_ns!=stat.st_mtime_ns or pak.stat().st_size!=stat.st_size: raise ValueError('Package drift')
            if not plan['already']:
                append.write_suffix(pak,plan['offset'],plan['before'],plan['after']);changed=True
            if tools.extract(pak,asset['entry'],work/'verified/bug_report.dds')!=asset['sha256']: raise ValueError('Packed DDS mismatch')
            for n,h in hashes.items():
                if tools.extract(pak,n,work/'verified'/n)!=h: raise ValueError(f'Sentinel drift: {n}')
            actual=patch.v1.sha256(pak) if changed else before
            if actual!=after or pak.stat().st_size!=manifest['size_after']: raise ValueError('Full package verification failed')
            if loose_hash:
                patch.v1.require_exact(loose,loose_hash)
                loose.unlink();removed=True # exact own stale DDS, already backed up
            manifest['state']='applied' if changed or removed else 'already_patched'
        else: manifest['state']='dry_run'
    except Exception as error:
        if removed: loose.write_bytes((work/'loose.before.dds').read_bytes())
        if changed:
            append.write_suffix(pak,plan['offset'],plan['after'],plan['before'])
            if patch.v1.sha256(pak)!=before: raise RuntimeError('Rollback hash failed') from error
        manifest.update(state='failed_rolled_back',error=str(error));raise
    finally: save()
    print(f"{manifest['state']}: {path}",flush=True)

if __name__=='__main__': main()
