import sqlite3
import unittest
from PatchAa10GardenTexts import repair


class GardenTextRepairTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript("""
            create table doodad_func_groups(id integer, name text, doodad_almighty_id integer);
            create table localized_texts(tbl_name text,tbl_column_name text,idx integer,en_us text);
            insert into doodad_func_groups values(45009,'',14855);
            insert into localized_texts values('doodad_func_groups','name',45009,'wrong damage #{max_damage}');
            insert into localized_texts values('skills','name',45009,'keep this skill');
        """)
        self.entries = [dict(table='doodad_func_groups', column='name', id=45009, doodad=14855,
                             before='wrong damage #{max_damage}', after='')]

    def tearDown(self):
        self.db.close()

    def test_exact_identity_and_repetition(self):
        self.assertEqual(repair(self.db, self.entries), 1)
        self.assertEqual(repair(self.db, self.entries), 0)
        self.assertEqual(self.db.execute("select en_us from localized_texts where tbl_name='skills'").fetchone(), ('keep this skill',))

    def test_native_nonempty_rejected(self):
        self.db.execute("update doodad_func_groups set name='real description'")
        with self.assertRaises(ValueError):
            repair(self.db, self.entries)

    def test_localized_drift_rejected(self):
        self.db.execute("update localized_texts set en_us='new review' where tbl_name='doodad_func_groups'")
        with self.assertRaises(ValueError):
            repair(self.db, self.entries)


if __name__ == '__main__':
    unittest.main()
