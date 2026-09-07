import os
from pathlib import Path
import sqlite3
from contextlib import closing
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import PatchAa10DwarfWarborn as patch
from ApplyAa10SpanishUiLayout import transaction
from ApplyAa10DwarfWarborn import atomic_copy


class HairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / 'fixture.sqlite3'
        with closing(sqlite3.connect(self.db)) as db, db:
            db.executescript('''
                create table items(id integer primary key, name text);
                insert into items values(407,'dw_f_hair03');
                create table item_body_parts(item_id,slot_type_id,model_id,asset_id);
                insert into item_body_parts values(407,24,15,122);
                create table item_assets(id,path);
                insert into item_assets values(122,'objects/characters/dwarf/female/hair/hair01/dw_f_hair01.chr');
                create table customizing_item_assets(id integer primary key,display_order,item_id,is_new,model_id,two_tone,category_id,use_pallet);
            ''')
            db.executemany('insert into customizing_item_assets values(?,?,?,\'f\',15,\'t\',1,\'t\')', [(i, i, 1000+i) for i in range(1,24)])

    def test_adds_only_missing_row_and_is_idempotent(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            original = db.execute('select * from customizing_item_assets order by id').fetchall()
        self.assertTrue(patch.patch_hair(self.db))
        digest = patch.hashes.sha256(self.db)
        self.assertFalse(patch.patch_hair(self.db))
        self.assertEqual(digest, patch.hashes.sha256(self.db))
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(original + [patch.HAIR_ROW], db.execute('select * from customizing_item_assets order by id').fetchall())

    def reject_without_mutation(self, statement):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute(statement)
        digest = patch.hashes.sha256(self.db)
        with self.assertRaises(RuntimeError):
            patch.patch_hair(self.db)
        self.assertEqual(digest, patch.hashes.sha256(self.db))

    def test_wrong_item(self):
        self.reject_without_mutation("update items set name='wrong'")

    def test_wrong_asset(self):
        self.reject_without_mutation("update item_assets set path='wrong'")

    def test_wrong_count(self):
        self.reject_without_mutation('delete from customizing_item_assets where id=1')

    def test_conflicting_existing_row(self):
        self.reject_without_mutation('update customizing_item_assets set item_id=407 where id=1')

    def test_triggers_rejected(self):
        self.reject_without_mutation('create trigger unexpected after insert on customizing_item_assets begin update items set name=\'wrong\'; end')

    def test_alb_unknown_rejected(self):
        with self.assertRaises(RuntimeError):
            patch.patch_races(bytes(26785))

    def test_loose_database_atomic_replacement(self):
        source = Path(self.temp.name) / 'replacement'
        source.write_bytes(b'new database bytes')
        target = Path(self.temp.name) / 'loose'
        target.write_bytes(b'old database bytes')
        atomic_copy(source, target)
        self.assertEqual(source.read_bytes(), target.read_bytes())
        self.assertFalse(list(Path(self.temp.name).glob('.aa10-dwarf-*')))

    def test_multi_entry_failure_rolls_back_in_reverse_order(self):
        calls = []
        entries = [dict(before='a', after='b', id=i) for i in (1,2)]
        def write(entry):
            calls.append(('write', entry['id']))
            if entry['id'] == 2:
                raise RuntimeError('simulated write failure')
        with self.assertRaises(RuntimeError):
            transaction(entries, write, lambda: None, lambda e: calls.append(('restore',e['id'])))
        self.assertEqual(calls, [('write',1),('write',2),('restore',2),('restore',1)])


@unittest.skipUnless(os.environ.get('AA10_DWARF_EFFECTIVE'), 'requires exact extracted retail evidence')
class RetailTests(unittest.TestCase):
    def test_frozen_alb_community_identity_and_idempotence(self):
        root = Path(os.environ['AA10_DWARF_EFFECTIVE'])
        data = (root / patch.RACE_ENTRY.removeprefix('game/')).read_bytes()
        result = patch.patch_races(data)
        self.assertEqual(result, patch.patch_races(result))
        self.assertEqual(len(data), len(result))
        self.assertEqual(patch.COMMUNITY_ALB_SHA, __import__('hashlib').sha256(result[:-1]).hexdigest().upper())

    def test_frozen_full_builder(self):
        root = Path(os.environ['AA10_DWARF_EFFECTIVE'])
        exe = Path(os.environ['AA10_DWARF_EXE'])
        with tempfile.TemporaryDirectory() as tmp:
            entries = patch.build(root, Path(tmp), exe)
            self.assertEqual(len(entries), 2)
            for entry in entries:
                self.assertEqual(entry['after'], patch.hashes.sha256(Path(entry['replacement'])))


if __name__ == '__main__':
    unittest.main()
