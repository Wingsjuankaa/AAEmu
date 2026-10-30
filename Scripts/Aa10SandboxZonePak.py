"""Pinned, streaming WIBO batch append for the private AA10 sandbox world.

Preparation is read-only for the package. Runtime writes require an explicit
flag and a closed owned client/Zone; callers still own lifecycle authorization.
Only the old FAT suffix is replaced. Unchanged encrypted records and all old
payload bytes remain literal. This is not power-loss atomic: retain the backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
import Aa10PakAppend as wibo

ROOT = Path('E:/AAEmu/rama_10').resolve()
SANDBOX = ROOT/'runtime/sandbox-aa10'
RUNTIME_PAKS = {SANDBOX/'client/game_pak', SANDBOX/'zone/game_pak'}
FIXTURE_ROOTS = (ROOT/'forensics/output/aa10-client-forensics', ROOT/'artifacts/tests/aa10-zone-pak')
ALB = 'game/scriptsbin64/x2ui/loginstage_new/connect/stage_server.alb'
STAMP = 134336448000000000
BLOCK = 4 * 1024 * 1024


def sha_file(path, offset=0):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        stream.seek(offset)
        while block := stream.read(BLOCK): h.update(block)
    return h.hexdigest().upper()


def _path(value):
    requested = Path(value).absolute()
    path = requested.resolve()
    if path.drive.upper() != 'E:' or not path.is_relative_to(ROOT):
        raise ValueError('All sandbox package paths must stay inside the canonical project on E')
    if requested.exists() and (requested.is_symlink() or requested.is_junction()):
        raise ValueError('Aliased files are not allowed')
    return path


def _pak(value):
    path = _path(value)
    if path not in RUNTIME_PAKS and not any(path.is_relative_to(p) for p in FIXTURE_ROOTS):
        raise ValueError('Only the two private sandbox packages or forensic fixtures are allowed')
    if not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError('Package must be a physical, unshared file')
    return path


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-fA-F]{64}', value):
        raise ValueError('A pinned SHA-256 is required')
    return value.upper()


def _name(value):
    if not isinstance(value, str) or value != value.lower():
        raise ValueError('Entry names must be lowercase ASCII')
    raw = value.encode('ascii')
    if not raw or len(raw) >= 264 or any(c < 32 or c == 127 for c in raw) or '\\' in value or any(
            segment in ('', '.', '..') for segment in value.split('/')):
        raise ValueError('Invalid package path')
    if not (value.startswith('game/worlds/main_world/') or value in
            ('game/db/compact.sqlite3', 'game/db/game.sqlite3', ALB)):
        raise ValueError('Entry is outside the sandbox world allowlist')
    return raw


def _stat(path):
    s = path.stat()
    return dict(size=s.st_size, mtime_ns=s.st_mtime_ns, inode=s.st_ino, atime_ns=s.st_atime_ns)


def _matches_stat(actual, expected):
    return all(actual[key] == expected[key] for key in ('size', 'mtime_ns', 'inode'))


def _json(path, value):
    temporary = path.with_suffix(path.suffix+'.new')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


def _copy_payload(source, target):
    sha, md5 = hashlib.sha256(), hashlib.md5()
    total = 0
    while block := source.read(BLOCK):
        target.write(block); sha.update(block); md5.update(block); total += len(block)
    return total, sha.hexdigest().upper(), md5.digest()


def prepare(pak, contract, output):
    """Freeze a complete suffix and backup; do not open pak writable.

    contract schema1: patch_id, package(size,mtime_ns,inode,sha256), entries.
    Each entry: entry,payload_path,after_sha256,before_sha256,before_size.
    before_sha256=None and before_size=None means ADD, otherwise pinned REPLACE.
    Existing FILETIMEs are preserved unless explicitly supplied. New records
    use deterministic STAMP by default. No-op entries preserve their raw record.
    """
    pak, output = _pak(pak), _path(output)
    if contract.get('schema') != 1 or not isinstance(contract.get('patch_id'), str) or not contract['patch_id']:
        raise ValueError('Invalid sandbox package contract')
    expected = contract['package']
    _digest(expected['sha256'])
    before_stat = _stat(pak)
    if not _matches_stat(before_stat, expected): raise ValueError('Pinned package identity drift')
    entries = contract.get('entries')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 4096:
        raise ValueError('A finite exact asset allowlist is required')
    wanted = {}
    for entry in entries:
        raw = _name(entry['entry'])
        if raw in wanted: raise ValueError('Duplicate target entry')
        payload = _path(entry['payload_path'])
        if not payload.is_file() or payload == pak: raise ValueError('Payload is not a staged file')
        after = _digest(entry['after_sha256'])
        old_hash, old_size = entry.get('before_sha256'), entry.get('before_size')
        if (old_hash is None) != (old_size is None): raise ValueError('Incomplete before-entry identity')
        if old_hash is not None:
            old_hash = _digest(old_hash)
            if isinstance(old_size, bool) or not isinstance(old_size, int) or old_size < 0:
                raise ValueError('Invalid before size')
        for field in ('create_filetime', 'modify_filetime'):
            if field in entry and (isinstance(entry[field], bool) or not isinstance(entry[field], int)
                                   or not 0 <= entry[field] < 2**63):
                raise ValueError('Invalid FILETIME')
        if sha_file(payload) != after: raise ValueError('Staged payload hash drift: '+entry['entry'])
        wanted[raw] = dict(entry, payload_path=str(payload), after_sha256=after,
                           before_sha256=old_hash, before_size=old_size)
    with pak.open('rb') as stream:
        start, tail, count, extras = wibo.read_tail(stream)
        found = {}
        for index in range(count):
            raw_record = tail[index*wibo.RECORD:(index+1)*wibo.RECORD]
            record = wibo.aes(raw_record)
            raw_name = record[:264].split(b'\0', 1)[0]
            offset, size, duplicate, padding = struct.unpack_from('<qqqi', record, 264)
            if min(offset, size, padding) < 0 or size != duplicate or offset+size+padding > start:
                raise ValueError('Invalid original live extent: '+str(index))
            lowered = raw_name.lower()
            if lowered in wanted:
                if raw_name != lowered: raise ValueError('Case-fold collision with a native entry')
                if raw_name in found: raise ValueError('Duplicate original target')
                found[raw_name] = (index, record, offset, size)
        for raw, entry in wanted.items():
            if entry['before_sha256'] is None:
                if raw in found: raise ValueError('ADD target already exists: '+entry['entry'])
            else:
                if raw not in found: raise ValueError('REPLACE target missing: '+entry['entry'])
                _, _, offset, size = found[raw]
                if size != entry['before_size']: raise ValueError('Before-entry size drift: '+entry['entry'])
                stream.seek(offset)
                digest = hashlib.sha256()
                remaining = size
                while remaining:
                    block = stream.read(min(BLOCK, remaining))
                    if not block: raise ValueError('Truncated original payload')
                    digest.update(block); remaining -= len(block)
                if digest.hexdigest().upper() != entry['before_sha256']:
                    raise ValueError('Before-entry hash drift: '+entry['entry'])
    # All identity, allowlist and old payload checks precede output creation.
    output.mkdir(parents=True, exist_ok=False)
    before_path, after_path = output/'suffix.before.bin', output/'suffix.after.bin'
    with before_path.open('xb') as stream:
        stream.write(tail); stream.flush(); os.fsync(stream.fileno())
    replacements, added, planned = {}, [], []
    cursor = start
    with after_path.open('xb') as target:
        for raw, entry in sorted(wanted.items()):
            unchanged = entry['before_sha256'] == entry['after_sha256'] and entry['before_sha256'] is not None
            if unchanged:
                original = found[raw][1]
                unchanged = all(field not in entry or entry[field] == struct.unpack_from('<q', original, offset)[0]
                                for field, offset in (('create_filetime',312), ('modify_filetime',320)))
            if unchanged:
                index, _, offset, size = found[raw]
                planned.append(dict(entry, operation='unchanged', old_offset=offset, new_offset=offset,
                                    size=size, record_index=index))
                continue
            path = Path(entry['payload_path'])
            with path.open('rb') as payload:
                size, after_sha, md5 = _copy_payload(payload, target)
            if after_sha != entry['after_sha256']: raise ValueError('Payload changed while freezing suffix')
            padding = wibo.aligned(size)-size
            target.write(bytes(padding))
            if raw in found:
                index, original, old_offset, old_size = found[raw]
                record = bytearray(original)
                operation = 'replace'
            else:
                record = bytearray(wibo.RECORD); record[:len(raw)] = raw
                struct.pack_into('<qq', record, 312, STAMP, STAMP)
                index, old_offset, old_size, operation = count+len(added), None, None, 'add'
            struct.pack_into('<qqqi', record, 264, cursor, size, size, padding)
            record[292:308] = md5
            for field, offset in (('create_filetime', 312), ('modify_filetime', 320)):
                if field in entry:
                    value = entry[field]
                    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 2**63:
                        raise ValueError('Invalid FILETIME')
                    struct.pack_into('<q', record, offset, value)
            encrypted = wibo.aes(bytes(record), True)
            if operation == 'replace': replacements[index] = encrypted
            else: added.append(encrypted)
            planned.append(dict(entry, operation=operation, old_offset=old_offset, new_offset=cursor,
                                size=size, record_index=index))
            cursor += size+padding
        # Emit unchanged spans literally instead of reserializing every native record.
        previous = 0
        for index, replacement in sorted(replacements.items()):
            target.write(memoryview(tail)[previous:index*wibo.RECORD]); target.write(replacement)
            previous = (index+1)*wibo.RECORD
        target.write(memoryview(tail)[previous:count*wibo.RECORD])
        for record in added: target.write(record)
        target.write(memoryview(tail)[count*wibo.RECORD:(count+extras)*wibo.RECORD])
        records_size = (count+extras+len(added))*wibo.RECORD
        if added:
            target.write(bytes(wibo.aligned(records_size)-records_size))
        else:
            target.write(memoryview(tail)[(count+extras)*wibo.RECORD:-512])
        footer = bytearray(tail[-512:]); header = bytearray(wibo.aes(footer[:32]))
        struct.pack_into('<I', header, 8, count+len(added)); footer[:32] = wibo.aes(bytes(header), True)
        target.write(footer); target.flush(); os.fsync(target.fileno())
    if not _matches_stat(_stat(pak), before_stat): raise ValueError('Package changed while preparing')
    after_size = start+after_path.stat().st_size
    manifest = dict(schema=1, patch_id=contract['patch_id'], state='prepared', package_path=str(pak),
                    package_before=dict(before_stat, sha256=expected['sha256'].upper()),
                    package_after=dict(size=after_size), suffix_offset=start,
                    suffix_before=dict(path=str(before_path), size=len(tail), sha256=wibo.sha(tail)),
                    suffix_after=dict(path=str(after_path), size=after_path.stat().st_size, sha256=sha_file(after_path)),
                    live_before=count, live_after=count+len(added), extras_before=extras, extras_after=extras,
                    new_fat_offset=cursor, entries=planned,
                    untouched_encrypted_records_preserved=True, original_payload_prefix_preserved=True,
                    contract_sha256=hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper(),
                    full_package_hash_verification='caller must verify pinned before hash and final hash; preparation pins metadata and exact target bytes')
    _json(output/'manifest.json', manifest)
    return manifest


def _load_manifest(path, expected_sha256=None):
    path = _path(path)
    if expected_sha256 is not None and sha_file(path) != _digest(expected_sha256):
        raise ValueError('Manifest hash drift')
    m = json.loads(path.read_text(encoding='utf-8'))
    if m.get('schema') != 1: raise ValueError('Unknown package plan')
    pak = _pak(m['package_path'])
    for which, basename in (('suffix_before','suffix.before.bin'),('suffix_after','suffix.after.bin')):
        suffix = _path(m[which]['path'])
        if suffix != path.parent/basename or not suffix.is_file() or suffix.stat().st_nlink != 1:
            raise ValueError('Suffix is not the owned plan file')
        if suffix.stat().st_size != m[which]['size'] or sha_file(suffix) != _digest(m[which]['sha256']):
            raise ValueError('Frozen suffix drift')
    for entry in m['entries']: _name(entry['entry'])
    if m['suffix_offset'] + m['suffix_before']['size'] != m['package_before']['size'] or \
            m['suffix_offset'] + m['suffix_after']['size'] != m['package_after']['size']:
        raise ValueError('Invalid planned suffix sizes')
    return path, pak, m


def _require_offline(pak, allow_runtime):
    if pak not in RUNTIME_PAKS: return
    if not allow_runtime: raise ValueError('Runtime apply requires explicit allow_runtime and authorized lifecycle')
    executable = pak.parent/('Bin64/archeage.exe' if pak.parent.name=='client' else 'Bin64/AAEmu.ZoneHost.exe')
    script = ("@(Get-CimInstance Win32_Process -Filter \"Name='archeage.exe' OR Name='AAEmu.ZoneHost.exe'\" "
              "| Select-Object -ExpandProperty ExecutablePath) | ConvertTo-Json -Compress")
    result = subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,check=True)
    paths = json.loads(result.stdout) if result.stdout.strip() else []
    if isinstance(paths,str): paths=[paths]
    if any(value and Path(value).resolve()==executable.resolve() for value in paths):
        raise ValueError('Close only the owned sandbox client/Zone before writing its package')


def _open_exclusive(pak):
    if os.name != 'nt': return pak.open('r+b')
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,
                               wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(pak),0xC0000000,0,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    try: descriptor=msvcrt.open_osfhandle(handle,os.O_RDWR|os.O_BINARY)
    except Exception:
        kernel.CloseHandle(handle);raise
    return os.fdopen(descriptor,'r+b',buffering=0)


def _hash_handle(stream, offset):
    stream.seek(offset);digest=hashlib.sha256()
    while block:=stream.read(BLOCK):digest.update(block)
    return digest.hexdigest().upper()


def _replace_suffix(pak, offset, source, size, *, target=None):
    if target is None:
        with _open_exclusive(pak) as stream:
            return _replace_suffix(pak,offset,source,size,target=stream)
    with source.open('rb') as stream:
        target.seek(offset)
        while block := stream.read(BLOCK): target.write(block)
        target.truncate(size); target.flush(); os.fsync(target.fileno())


def apply_plan(manifest_path, *, allow_runtime=False, expected_manifest_sha256=None):
    path, pak, m = _load_manifest(manifest_path, expected_manifest_sha256)
    current = _stat(pak)
    if current['size']==m['package_after']['size'] and sha_file(pak,m['suffix_offset'])==m['suffix_after']['sha256']:
        return dict(state='already_patched', package_path=str(pak), package_after=current)
    if not _matches_stat(current,m['package_before']) or sha_file(pak,m['suffix_offset'])!=m['suffix_before']['sha256']:
        raise ValueError('Package drift before applying the frozen plan')
    _require_offline(pak, allow_runtime)
    restored=False
    try:
        # FILE_SHARE_NONE prevents a new client/Zone reader appearing between preflight and commit.
        with _open_exclusive(pak) as target:
            locked=os.fstat(target.fileno())
            if (locked.st_size,locked.st_mtime_ns,locked.st_ino)!=(current['size'],current['mtime_ns'],current['inode']) or \
                    _hash_handle(target,m['suffix_offset'])!=m['suffix_before']['sha256']:
                raise ValueError('Package drift while acquiring exclusive ownership')
            try:
                _replace_suffix(pak,m['suffix_offset'],Path(m['suffix_after']['path']),m['package_after']['size'],target=target)
                if _hash_handle(target,m['suffix_offset'])!=m['suffix_after']['sha256']:
                    raise ValueError('Post-write suffix hash mismatch')
            except Exception as error:
                try:
                    _replace_suffix(pak,m['suffix_offset'],Path(m['suffix_before']['path']),m['package_before']['size'],target=target)
                    if _hash_handle(target,m['suffix_offset'])!=m['suffix_before']['sha256']:
                        raise ValueError('Recovery hash mismatch')
                    restored=True
                except Exception as recovery:
                    raise RuntimeError(f'Package write failed: {error}; rollback failed: {recovery}; retain {path.parent}') from error
                raise
    except Exception:
        if restored: os.utime(pak,ns=(m['package_before']['atime_ns'],m['package_before']['mtime_ns']))
        raise
    return dict(state='applied',package_path=str(pak),package_after=_stat(pak),suffix_after_sha256=m['suffix_after']['sha256'])


def rollback_plan(manifest_path, *, allow_runtime=False, expected_manifest_sha256=None):
    _, pak, m = _load_manifest(manifest_path, expected_manifest_sha256)
    current_hash = sha_file(pak,m['suffix_offset'])
    if pak.stat().st_size==m['package_before']['size'] and current_hash==m['suffix_before']['sha256']:
        return dict(state='already_original',package_path=str(pak))
    if pak.stat().st_size!=m['package_after']['size'] or current_hash!=m['suffix_after']['sha256']:
        raise ValueError('Refusing rollback of an unknown package suffix')
    if pak.stat().st_ino!=m['package_before']['inode']: raise ValueError('Rollback package inode drift')
    _require_offline(pak,allow_runtime)
    with _open_exclusive(pak) as target:
        if _hash_handle(target,m['suffix_offset'])!=m['suffix_after']['sha256']:
            raise ValueError('Package drift while acquiring rollback ownership')
        _replace_suffix(pak,m['suffix_offset'],Path(m['suffix_before']['path']),m['package_before']['size'],target=target)
        if _hash_handle(target,m['suffix_offset'])!=m['suffix_before']['sha256']:
            raise ValueError('Rollback hash mismatch')
    os.utime(pak,ns=(m['package_before']['atime_ns'],m['package_before']['mtime_ns']))
    if sha_file(pak,m['suffix_offset'])!=m['suffix_before']['sha256']: raise ValueError('Rollback hash mismatch')
    return dict(state='rolled_back',package_path=str(pak),package_before=_stat(pak))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare'); p.add_argument('--pak',type=Path,required=True)
    p.add_argument('--contract',type=Path,required=True); p.add_argument('--expected-contract-sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    for name in ('apply','rollback'):
        p=sub.add_parser(name);p.add_argument('--manifest',type=Path,required=True)
        p.add_argument('--expected-manifest-sha256',required=True);p.add_argument('--allow-runtime',action='store_true')
    args=parser.parse_args()
    if args.action=='prepare':
        contract_path=_path(args.contract)
        if sha_file(contract_path)!=_digest(args.expected_contract_sha256): raise ValueError('Contract hash drift')
        result=prepare(args.pak,json.loads(contract_path.read_text(encoding='utf-8')),args.out)
        print(json.dumps({'state':'prepared','manifest':str(_path(args.out)/'manifest.json'),
                          'before_size':result['package_before']['size'],'after_size':result['package_after']['size']}))
    else:
        op=apply_plan if args.action=='apply' else rollback_plan
        print(json.dumps(op(args.manifest,allow_runtime=args.allow_runtime,
                            expected_manifest_sha256=args.expected_manifest_sha256)))


if __name__=='__main__': main()
