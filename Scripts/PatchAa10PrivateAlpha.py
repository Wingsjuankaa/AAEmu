"""Build the private-alpha r575 key/UI/catalog from pinned effective inputs.

The full authoritative items catalog supplies missing rows only. Existing Spanish
rows and all existing mechanics remain byte-for-byte equal at the SQL row level.
VACUUM plus registered SQLite freelist pages keeps the game_pak entry capacity.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct

import PatchAa10SpanishUiLayout as codec
from SyncAa10GrowthRateTooltip import preserve_sqlite_size

CONTRACT = Path(__file__).with_name('Aa10PrivateAlpha.contracts.json')
LUA = Path(__file__).with_name('lua') / 'PrivateAlphaPanel.lua'
KEY = 900001
NATIVE = Path('E:/AAEmu/rama_10/data/sqlite/authoritative/game_decrypted.sqlite3')
SUBTYPES = ('item_weapons', 'item_armors', 'item_accessories', 'item_backpacks',
            'item_bags', 'item_body_parts', 'item_tools', 'item_housings',
            'item_housing_decorations', 'item_summon_mates', 'item_summon_slaves',
            'item_accept_quests', 'item_spawn_doodads', 'item_recipes',
            'item_shipyards', 'item_open_papers', 'item_enchanting_gems',
            'item_slave_equipments')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest().upper()


def require(test, message):
    if not test:
        raise ValueError(message)


def verify_sqlite_layout(path, size, schema_version):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        page_size = db.execute('PRAGMA page_size').fetchone()[0]
        page_count = db.execute('PRAGMA page_count').fetchone()[0]
        require(path.stat().st_size == size == page_size * page_count,
                'Unregistered SQLite pages: physical/logical size differs')
        require(db.execute('PRAGMA schema_version').fetchone()[0] == schema_version,
                'Native schema version drift')
        require(db.execute('PRAGMA integrity_check').fetchall() == [('ok',)],
                'SQLite integrity failed')
    read_freelist(path, legacy=True)


def read_freelist(path, legacy=False):
    with path.open('rb') as f:
        header = f.read(100)
        page_size = struct.unpack_from('>H', header, 16)[0]
        usable = page_size - header[20]
        trunk, count = struct.unpack_from('>II', header, 32)
        pages = set()
        while trunk:
            require(trunk not in pages, 'Freelist cycle')
            pages.add(trunk)
            f.seek((trunk - 1) * page_size)
            data = f.read(page_size)
            trunk, leaves = struct.unpack_from('>II', data)
            require(leaves <= usable // 4 - (8 if legacy else 2),
                    'Native freelist leaf count too big')
            for offset in range(leaves):
                leaf = struct.unpack_from('>I', data, 8 + offset * 4)[0]
                require(leaf not in pages, 'Duplicate freelist page')
                pages.add(leaf)
        require(len(pages) == count, 'Freelist count differs')
        return page_size, usable, sorted(pages)


def make_freelist_native_compatible(path):
    # r575 rejects the final six trunk slots, as documented by SQLite's
    # legacy file-format contract: https://sqlite.org/fileformat.html#the_freelist
    page_size, usable, pages = read_freelist(path)
    if not pages:
        return
    capacity = usable // 4 - 8
    groups = [pages[i:i + capacity + 1] for i in range(0, len(pages), capacity + 1)]
    with path.open('r+b') as f:
        # Clear all free pages so rebuilding V1, V2 or baseline is deterministic.
        for page in pages:
            f.seek((page - 1) * page_size)
            f.write(bytes(page_size))
        for i, group in enumerate(groups):
            data = bytearray(page_size)
            next_trunk = groups[i + 1][0] if i + 1 < len(groups) else 0
            struct.pack_into('>II', data, 0, next_trunk, len(group) - 1)
            for j, leaf in enumerate(group[1:]):
                struct.pack_into('>I', data, 8 + j * 4, leaf)
            f.seek((group[0] - 1) * page_size)
            f.write(data)
        f.seek(32)
        f.write(struct.pack('>I', pages[0]))


def modify_source(source):
    anchor = 'function bagInjector:PreUseSlot(realSlot)'
    require(source.count(anchor) == 1, 'PreUse consumer drift')
    return LUA.read_text(encoding='utf-8') + '\n' + source.replace(anchor,
        anchor + '\n    if Aa10PrivateAlpha.PreUse(realSlot) then return true end')


def add_catalog(db):
    db.execute('CREATE TEMP TABLE missing_alpha_items AS SELECT id FROM native.items EXCEPT SELECT id FROM main.items')
    added = {}
    for table in ('items', *SUBTYPES):
        cols = [r[1] for r in db.execute(f'pragma main.table_info("{table}")')]
        native_cols = [r[1] for r in db.execute(f'pragma native.table_info("{table}")')]
        require(cols and cols == native_cols, f'Schema drift: {table}')
        names = ','.join(f'"{c}"' for c in cols)
        key = 'id' if table == 'items' else 'item_id'
        before = db.total_changes
        db.execute(f'INSERT INTO main."{table}"({names}) SELECT {names} FROM native."{table}" '
                   f'WHERE "{key}" IN (SELECT id FROM missing_alpha_items) '
                   f'AND id NOT IN (SELECT id FROM main."{table}")')
        added[table] = db.total_changes - before
    # Add a dedicated custom template, without reusing or changing a native item.
    cols = [r[1] for r in db.execute('pragma table_info(items)')]
    values = dict(zip(cols, db.execute('SELECT * FROM items WHERE id=16263').fetchone()))
    values.update(id=KEY, name='Llave de alpha privada', description='Haz clic derecho para abrir las herramientas de la alpha privada. Acceso personal autorizado.',
                  category_id=64, bind_id=2, max_stack_size=1, sellable='f', impl_id=0,
                  use_skill_id=0, use_skill_as_reagent='f', loot_multi='f', loot_quest_id=0,
                  fixed_grade=0, disenchantable='f', translate='f', uid=900000000001,
                  auction_a_category_id=0, auction_b_category_id=0, auction_c_category_id=0)
    db.execute('INSERT INTO items (' + ','.join(cols) + ') VALUES (' + ','.join('?' for _ in cols) + ')', tuple(values[c] for c in cols))
    return added


def verify_preserved(db, allowed):
    # Attached "before" is immutable; EXCEPT checks every original row including all locales.
    for (table,) in db.execute("SELECT name FROM before.sqlite_master WHERE type='table'"):
        if table == 'sqlite_sequence':
            continue
        require(db.execute(f'SELECT * FROM before."{table}" EXCEPT SELECT * FROM main."{table}" LIMIT 1').fetchone() is None,
                f'Existing rows changed: {table}')
        if table not in allowed:
            require(db.execute(f'SELECT * FROM main."{table}" EXCEPT SELECT * FROM before."{table}" LIMIT 1').fetchone() is None,
                    f'Unrelated rows added: {table}')
    require(db.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'SQLite integrity failed')


def build(effective, output, luac):
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    codec.v1.require_exact(NATIVE, contract['native_sha256'])
    codec.v1.require_exact(luac, contract['luac_sha256'])
    output.mkdir(parents=True, exist_ok=False)
    entries = []
    for entry in contract['entries']:
        source = effective / entry['entry'].removeprefix('game/')
        before = sha(source)
        require(source.stat().st_size == entry['size'] and before in entry['accepted_sha256'], 'Unknown input: ' + entry['entry'])
        target = output / source.name
        if source.suffix == '.alb':
            lua = effective / 'scripts/x2ui/inventory/sort_bag.lua'
            codec.v1.require_exact(lua, contract['source_sha256'])
            text = lua.read_text(encoding='utf-8-sig')
            if before == entry['baseline_sha256']:
                require(codec.semantic_chunk(codec.compile_source(text, luac)) == codec.semantic_chunk(source.read_bytes()), 'Native source/ALB mismatch')
            data = codec.compile_source(modify_source(text), luac)
            require(len(data) <= entry['size'], 'Custom UI exceeds entry capacity')
            target.write_bytes(data + b'\0' * (entry['size'] - len(data)))
        else:
            shutil.copy2(source, target)
            if before == entry['baseline_sha256']:
                with closing(sqlite3.connect(target)) as db:
                    db.execute('ATTACH DATABASE ? AS native', (str(NATIVE),))
                    require(db.execute('SELECT 1 FROM items WHERE id=?', (KEY,)).fetchone() is None, 'Key id collision')
                    added = add_catalog(db)
                    db.commit()
                    db.execute('ATTACH DATABASE ? AS before', (str(source),))
                    verify_preserved(db, {'items', *SUBTYPES})
                    require(db.execute('SELECT count(*) FROM items').fetchone()[0] == 51011, 'Full catalog count differs')
                    db.execute('VACUUM')
            if before != entry['patched_sha256']:
                # V2 already has the correct header/schema; only its freelist
                # needs repartitioning. Avoid changing header counters again.
                if before != entry.get('rejected_native_v2_sha256'):
                    preserve_sqlite_size(target, entry['size'], entry['schema_version'])
                make_freelist_native_compatible(target)
            verify_sqlite_layout(target, entry['size'], entry['schema_version'])
            with closing(sqlite3.connect(target.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                require(db.execute('PRAGMA integrity_check').fetchall() == [('ok',)], 'Padded SQLite invalid')
                catalog = dict(db.execute("SELECT i.id,COALESCE(NULLIF(l.en_us,''),i.name) FROM items i LEFT JOIN localized_texts l ON l.tbl_name='items' AND l.tbl_column_name='name' AND l.idx=i.id ORDER BY i.id"))
            (output / 'private_alpha_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        after = sha(target)
        require(after == entry['patched_sha256'], 'Output hash drift: ' + entry['entry'])
        entries.append(dict(entry=entry['entry'], before=before, after=after, size=entry['size'], replacement=str(target), rollback=str(source)))
    return entries
