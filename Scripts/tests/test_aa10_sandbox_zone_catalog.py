import importlib.util
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('sandbox_zone_catalog',
    Path(__file__).parents[1]/'BuildAa10SandboxZoneCatalog.py')
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)
ARTIFACTS = catalog.ROOT/'artifacts/tests/sandbox-zone-catalog'
ARTIFACTS.mkdir(parents=True, exist_ok=True)


class ZoneCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ARTIFACTS)
        self.root = Path(self.temporary.name)
        self.source = self.root/'source.sqlite3'
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.executescript('''
                CREATE TABLE zones(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, zone_key INTEGER,
                    group_id INTEGER, closed TEXT, display_text TEXT, faction_id INTEGER,
                    zone_climate_id INTEGER, abox_show TEXT, integration TEXT, closed_to_foreigner TEXT);
                CREATE TABLE zone_groups(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, x REAL, y REAL,
                    w REAL, h REAL, sound_id INTEGER, target_id INTEGER, display_text TEXT,
                    faction_chat_region_id INTEGER, sound_pack_id INTEGER, pirate_desperado TEXT,
                    fishing_sea_loot_pack_id INTEGER, fishing_land_loot_pack_id INTEGER, buff_id INTEGER,
                    enable_physics_collision_damage TEXT, faction_id INTEGER, ocean_simulate TEXT,
                    dp_lv_min INTEGER, dp_lv_max INTEGER, hide_world_pos TEXT,
                    enable_special_resurrection_district TEXT);
                CREATE TABLE localized_texts(id INTEGER PRIMARY KEY AUTOINCREMENT, tbl_name TEXT,
                    tbl_column_name TEXT, idx INTEGER, ko TEXT, en_us TEXT, es TEXT, ru TEXT);
                CREATE TABLE world_groups(id INTEGER PRIMARY KEY, name TEXT, map_target_type TEXT);
                CREATE TABLE witness(label TEXT, payload BLOB, amount REAL, optional TEXT);
                CREATE INDEX witness_label ON witness(label);
                CREATE VIEW witness_view AS SELECT label,payload FROM witness;
                CREATE TABLE keyed(first TEXT,second INTEGER,payload BLOB,PRIMARY KEY(first,second)) WITHOUT ROWID;
            ''')
            connection.execute('INSERT INTO zones VALUES(318,?,?,?,?,?,?,?,?,?,?)',
                ('instance_training_camp_1on1_ga',406,153,'f','original title',None,None,'f','f','f'))
            connection.execute('INSERT INTO zones VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (296,'gatekeeper_hall',379,134,'f','keep Hall',None,None,'f','f','f'))
            connection.execute('INSERT INTO zone_groups VALUES('+','.join('?'*22)+')',
                (153,'instance_training_camp_1on1_ga',0,0,0,0,1,1,'original group',0,129,'f',None,None,None,'t',None,'f',0,0,'f','f'))
            connection.execute('INSERT INTO world_groups VALUES(1,?,?)',('none','WorldGroup'))
            for values in [(798811,'zones','display_text',318,'원본','Gladiator Arena','','Original RU'),
                           (798750,'zone_groups','display_text',153,'원본','Make a Splash','','Original RU'),
                           (810331,'witness','label',5,'원본','Unrelated','Conservar','Оригинал')]:
                connection.execute('INSERT INTO localized_texts VALUES(?,?,?,?,?,?,?,?)', values)
            # The full source has a sequence higher than its current MAX(id). Never lower it.
            connection.execute('UPDATE sqlite_sequence SET seq=1427106 WHERE name=?',('localized_texts',))
            connection.execute('INSERT INTO witness(rowid,label,payload,amount,optional) VALUES(5,?,?,?,?)',
                               ('área 🧪',b'\x00\xff\x08',-2.5,None))
            connection.execute('INSERT INTO witness(rowid,label,payload,amount,optional) VALUES(21,?,?,?,?)',
                               ('duplicates',b'',0.0,'same'))
            connection.execute("INSERT INTO witness(rowid,label) VALUES(27,CAST(x'FF0080' AS TEXT))")
            connection.execute('INSERT INTO keyed VALUES(?,?,?)',('z',2,b'unchanged'))
            connection.execute('INSERT INTO keyed VALUES(?,?,?)',('a',1,b'unchanged'))
            connection.execute('CREATE TABLE padding(data BLOB)')
            connection.execute('INSERT INTO padding VALUES(zeroblob(65536))')
            connection.execute('DROP TABLE padding')

    def tearDown(self):
        self.temporary.cleanup()

    def derive(self, filename='derived.sqlite3'):
        expected = {'sha256':catalog.digest(self.source),'bytes':self.source.stat().st_size}
        return catalog._derive_verified(self.source, self.root/filename, expected, 'fixture')

    def test_two_builds_are_identical_preserve_every_existing_rowid_and_schema_and_stay_same_size(self):
        before, size = catalog.digest(self.source), self.source.stat().st_size
        first, second = self.derive('a.sqlite3'), self.derive('b.sqlite3')
        self.assertEqual(first['output']['sha256'], second['output']['sha256'])
        self.assertEqual(first['output']['bytes'], size)
        self.assertEqual(catalog.digest(self.source), before)
        self.assertTrue(first['original_rows_and_rowids_equal'])
        self.assertTrue(first['preserved_tables']['witness']['rowids_compared'])
        self.assertFalse(first['preserved_tables']['keyed']['rowids_compared'])
        with catalog.readonly(self.root/'a.sqlite3') as connection:
            zone = catalog.row(connection,'SELECT * FROM zones WHERE zone_key=411')
            group = catalog.row(connection,'SELECT * FROM zone_groups WHERE id=159')
            self.assertEqual(zone['name'],'aa10_sandbox_lab')
            self.assertEqual(zone['closed'],'f')
            self.assertEqual(group['hide_world_pos'],'t')
            self.assertIsNone(group['buff_id'])
            self.assertEqual(group['target_id'],1)
            self.assertEqual(connection.execute('SELECT seq FROM sqlite_sequence WHERE name=?',
                                               ('localized_texts',)).fetchone()[0],1427106)
            self.assertEqual(connection.execute('SELECT count(*) FROM zones WHERE zone_key IN(379,406)').fetchone()[0],2)
            for label in connection.execute('SELECT en_us,es,ko,ru FROM localized_texts WHERE id IN(810332,810333)'):
                self.assertEqual(label,('Laboratorio AA10','Laboratorio AA10','Laboratorio AA10',''))

    def test_compact_style_sequence_advances_only_for_new_rows(self):
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute('UPDATE sqlite_sequence SET seq=810331 WHERE name=?',('localized_texts',))
        self.derive()
        with catalog.readonly(self.root/'derived.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT name,seq FROM sqlite_sequence ORDER BY name').fetchall(),
                             [('localized_texts',810333),('zone_groups',159),('zones',324)])

    def test_hash_drift_is_rejected_before_creating_output(self):
        with self.assertRaisesRegex(ValueError,'hash/size'):
            catalog._derive_verified(self.source,self.root/'bad.sqlite3',
                {'sha256':'0'*64,'bytes':self.source.stat().st_size},'fixture')
        self.assertFalse((self.root/'bad.sqlite3').exists())
        self.assertFalse((self.root/'bad.sqlite3.building').exists())
        with self.assertRaisesRegex(ValueError,'hash/size'):
            catalog.build(self.source,self.root/'untrusted.sqlite3','full')

    def test_occupied_zone_group_localization_and_donor_drift_fail_without_output(self):
        changes = [
            ('zone key','UPDATE zones SET zone_key=411 WHERE zone_key=379'),
            ('zone row','UPDATE zones SET id=324 WHERE zone_key=379'),
            ('zone name',"UPDATE zones SET name='AA10_SANDBOX_LAB' WHERE zone_key=379"),
            ('group row','UPDATE zone_groups SET id=159'),
            ('localization id','UPDATE localized_texts SET id=810332 WHERE id=810331'),
            ('localization key',"UPDATE localized_texts SET idx=324 WHERE tbl_name='zones'"),
            ('donor parent','UPDATE zone_groups SET target_id=7'),
            ('donor buff','UPDATE zone_groups SET buff_id=26321'),
        ]
        for index,(name,statement) in enumerate(changes):
            path = self.root/f'case-{index}.sqlite3'
            path.write_bytes(self.source.read_bytes())
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.execute(statement)
            with self.subTest(name=name), self.assertRaises(ValueError):
                catalog._derive_verified(path,self.root/f'rejected-{index}.sqlite3',
                    {'sha256':catalog.digest(path),'bytes':path.stat().st_size},'fixture')
            self.assertFalse((self.root/f'rejected-{index}.sqlite3').exists())

    def test_trigger_and_pending_journal_are_rejected_before_output(self):
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute('CREATE TRIGGER unexpected AFTER INSERT ON zones BEGIN DELETE FROM witness; END;')
        with self.assertRaisesRegex(ValueError,'triggers'):
            self.derive()
        with closing(sqlite3.connect(self.source)) as connection, connection:
            connection.execute('DROP TRIGGER unexpected')
        Path(str(self.source)+'-wal').write_bytes(b'pending')
        with self.assertRaisesRegex(ValueError,'WAL/journal'):
            self.derive()

    def test_output_cannot_overwrite_source_existing_files_or_escape_artifacts(self):
        for path in [self.source,self.root/'../..',Path('C:/catalog.sqlite3'),
                     catalog.ROOT/'runtime/sandbox-aa10/should-not-be-created.sqlite3']:
            with self.subTest(path=path), self.assertRaises((ValueError,FileExistsError)):
                catalog.output_path(path)
        output = self.root/'existing.sqlite3'
        output.write_bytes(b'keep me')
        with self.assertRaises(FileExistsError):
            self.derive('existing.sqlite3')
        self.assertEqual(output.read_bytes(),b'keep me')

    def test_complete_verifier_detects_an_unrelated_changed_value_with_same_row_count(self):
        result = self.derive()
        with closing(sqlite3.connect(self.root/'derived.sqlite3')) as connection, connection:
            connection.execute('UPDATE witness SET payload=? WHERE rowid=21',(b'changed',))
        with catalog.readonly(self.source) as original, catalog.readonly(self.root/'derived.sqlite3') as changed:
            with self.assertRaisesRegex(ValueError,'witness'):
                catalog.verify_original_rows(original,changed,result['inserted_rows'])


if __name__ == '__main__':
    unittest.main()
