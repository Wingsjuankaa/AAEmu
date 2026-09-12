"""Restore exactly one V3 installation suffix; refuse any later client changes."""
import argparse
import json
from pathlib import Path
import Aa10PakAppend as append
import ApplyAa10SpanishUiLayout as tools
import PatchAa10BugReports as patch

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();m=json.loads(args.manifest.read_text(encoding='utf-8'))
    if m['patch_id']!='aa10-bug-reports-v3-packed-icon' or m['state']!='applied': raise ValueError('Not an applied V3 manifest')
    if m['sha256_before']==m['sha256_after']: raise ValueError('Not an insertion manifest')
    pak=tools.preflight(tools.CLIENT,args.apply)
    if str(pak)!=m['game_pak']: raise ValueError('Client mismatch')
    patch.v1.require_exact(pak,m['sha256_after'])
    work=args.manifest.parent;before=(work/'tail.before.bin').read_bytes();after=(work/'tail.after.bin').read_bytes()
    if append.sha(before)!=m['suffix_before_sha256'] or append.sha(after)!=m['suffix_after_sha256']: raise ValueError('Backup drift')
    loose=tools.CLIENT/m['asset']['entry']
    if not loose.resolve().is_relative_to(tools.CLIENT.resolve()) or loose.exists(): raise ValueError('Unexpected loose asset')
    if m['loose_before']: patch.v1.require_exact(work/'loose.before.dds',m['loose_before'])
    if args.apply:
        append.write_suffix(pak,m['suffix_offset'],after,before)
        patch.v1.require_exact(pak,m['sha256_before'])
        if m['loose_before']: loose.write_bytes((work/'loose.before.dds').read_bytes())
    print('Restored exact pre-V3 package' if args.apply else 'Rollback verified; use --apply with client closed')

if __name__=='__main__': main()
