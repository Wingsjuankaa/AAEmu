#!/usr/bin/env python3
"""Reproduce the reviewed community r575 race selector and dwarf hair fixes.

Never executes supplied ALB. Changes two serialized constants and one SQLite row.
The exact Spanish distribution inputs/outputs are frozen below; unknown data fails.
Requires cryptography (tested 50.0.1) and SQLite 3.45.3 for deterministic DB output.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import sqlite3
from contextlib import closing
import struct

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from PatchAa10SpanishUiLayout import semantic_chunk
import PatchAa10WesternUiLayout as hashes

RACE_ENTRY = 'game/scriptsbin64/x2ui/loginstage_new/character_create/character_create_race.alb'
DB_ENTRY = 'game/db/game.sqlite3'
CONTRACTS = {
    RACE_ENTRY: (26785, '89D549E2819AB31ECAC73B1D808CA37570C9BC23F4D20C56219E9AD9FF88D9BD',
                 '545FA08321F3159AEC4D4B4927FA6880330C8AB8CCDECD7293A9A9EFB79C1EA6'),
    DB_ENTRY: (552178688, 'E9EA3391B7B83C0510A096B4BEB87219703D8E2C8D8D222C9083D58163418301',
               '1387EC6535270F99D9469F7F895306673827AFB0861E1B4E5F7BAAA503F605EB'),
}
COMMUNITY_ALB_SHA = 'C118BD1D3347C0281B65DEB92E13900785D7199824A897F024CB6D48AA6622EF'
COMMUNITY_HAIR_SCRIPT_SHA = 'B9A4A67649E521F1A1EEA737D0B2AE0F1046414B582DF9F21B51560BA8CBB613'
HAIR_ROW = (486, 1500, 407, 'f', 15, 'f', 1, 'f')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def patch_races(data: bytes) -> bytes:
    size, before, after = CONTRACTS[RACE_ENTRY]
    digest = hashlib.sha256(data).hexdigest().upper()
    require(len(data) == size and digest in (before, after), 'Unknown race ALB')
    if digest == after:
        return data
    names = ['right', 'RACE_RETURNED', 'RACE_FERRE', 'RACE_HARIHARAN',
             'RACE_NUIAN', 'RACE_ELF', 'RACE_FAIRY']
    def constants(values):
        return b''.join(b'\x04' + struct.pack('<Q', len(v) + 1) + v.encode() + b'\0' for v in values)
    original = constants(names)
    names[1], names[-1] = 'RACE_WARBORN', 'RACE_DWARF'
    require(data.count(original) == 1, 'Ambiguous GetSortedRaces constants')
    replacement = data.replace(original, constants(names))
    require(hashlib.sha256(replacement).hexdigest().upper() == COMMUNITY_ALB_SHA,
            'Reconstruction differs from reviewed community ALB')
    # The community file is one byte shorter. Pad only after the complete Lua chunk.
    result = replacement + b'\0'
    before_tree, after_tree = semantic_chunk(data), semantic_chunk(result)
    expected_constants = tuple((4, n.encode() + b'\0') for n in names)
    children = list(before_tree[3])
    child = children[1]
    children[1] = (child[0], child[1], expected_constants, child[3])
    require(after_tree == (*before_tree[:3], tuple(children)), 'Unexpected semantic ALB change')
    require(hashlib.sha256(result).hexdigest().upper() == after, 'Unexpected ALB output')
    return result


def read_key(executable: Path) -> bytes:
    # Key stays in memory; no key literals or key output in the reproducible artifact.
    with executable.open('rb') as stream:
        require(stream.read(2) == b'MZ', 'Not a PE executable')
        stream.seek(0x3c)
        offset = struct.unpack('<I', stream.read(4))[0]
        stream.seek(offset)
        require(stream.read(4) == b'PE\0\0', 'Invalid PE signature')
        coff = stream.read(20)
        sections = struct.unpack_from('<H', coff, 2)[0]
        stream.seek(struct.unpack_from('<H', coff, 16)[0], 1)
        for _ in range(sections):
            section = stream.read(40)
            if section[:8] == b'.xlgames':
                raw = struct.unpack_from('<I', section, 20)[0]
                stream.seek(raw)
                require(struct.unpack('<I', stream.read(4))[0] == 575, 'Not revision 575')
                stream.seek(raw + 72)
                key = stream.read(16)
                require(len(key) == 16, 'Truncated key')
                return key
    raise RuntimeError('Missing .xlgames section')


def transform(source: Path, destination: Path, key: bytes, encrypt=False):
    require(source.stat().st_size % 16 == 0, 'Invalid AES length')
    cipher = Cipher(algorithms.AES(key), modes.CBC(bytes(16)))
    operation = cipher.encryptor() if encrypt else cipher.decryptor()
    with source.open('rb') as src, destination.open('wb') as dst:
        for block in iter(lambda: src.read(8 * 1024 * 1024), b''):
            dst.write(operation.update(block))
        dst.write(operation.finalize())


def patch_hair(database: Path) -> bool:
    with closing(sqlite3.connect(database)) as db, db:
        require(db.execute('pragma integrity_check').fetchall() == [('ok',)], 'SQLite integrity failure')
        require(db.execute('select name from items where id=407').fetchall() == [('dw_f_hair03',)], 'Wrong hair item')
        require(db.execute('select model_id,asset_id from item_body_parts where item_id=407 and slot_type_id=24').fetchall()
                == [(15, 122)], 'Wrong body link')
        require(db.execute('select path from item_assets where id=122').fetchall()
                == [('objects/characters/dwarf/female/hair/hair01/dw_f_hair01.chr',)], 'Wrong hair asset')
        rows = db.execute('select * from customizing_item_assets where model_id=15 and category_id=1 and item_id=407').fetchall()
        count = db.execute('select count(*) from customizing_item_assets where model_id=15 and category_id=1').fetchone()[0]
        if rows:
            require(rows == [HAIR_ROW] and count == 24, 'Conflicting existing hair row')
            return False
        require(count == 23, 'Unknown dwarf hair catalogue')
        require(not db.execute("select name from sqlite_master where type='trigger' and tbl_name='customizing_item_assets'").fetchall(), 'Unexpected customization trigger')
        db.execute('insert into customizing_item_assets (id,display_order,item_id,is_new,model_id,two_tone,category_id,use_pallet) values (?,?,?,?,?,?,?,?)', HAIR_ROW)
        require(db.total_changes == 1, 'Unexpected database mutations')
        return True


def build(effective: Path, output: Path, executable: Path):
    output.mkdir(parents=True, exist_ok=True)
    result = []
    for entry, (size, baseline, target) in CONTRACTS.items():
        source = effective / entry.removeprefix('game/')
        before = hashes.sha256(source)
        require(source.stat().st_size == size and before in (baseline, target), f'Unknown input: {entry}')
        replacement = output / Path(entry).name
        if before == target:
            shutil.copy2(source, replacement)
        elif entry == RACE_ENTRY:
            replacement.write_bytes(patch_races(source.read_bytes()))
        else:
            require(sqlite3.sqlite_version == '3.45.3', 'Use SQLite 3.45.3 for the frozen output')
            key = read_key(executable)
            plain = output / 'game.patched.plain.sqlite3'
            transform(source, plain, key)
            hashes.require_exact(plain, '87531F4BF066904B4B82D0324C6A9C741DE38DF4FBF9FC95D0BA211287E3702F')
            require(patch_hair(plain), 'Expected missing hair')
            require(not patch_hair(plain), 'Hair patch is not idempotent')
            transform(plain, replacement, key, True)
            roundtrip = output / 'game.roundtrip.sqlite3'
            transform(replacement, roundtrip, key)
            require(hashes.sha256(plain) == hashes.sha256(roundtrip), 'AES roundtrip mismatch')
        hashes.require_exact(replacement, target, size)
        result.append(dict(entry=entry, size=size, before=before, after=target,
                           replacement=str(replacement), rollback=str(source)))
    return result
