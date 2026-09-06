import importlib.util
from pathlib import Path
import sqlite3
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch as mock_patch

spec = importlib.util.spec_from_file_location('patch', Path(__file__).parents[1] / 'PatchAa10WorldLevelDisabled.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class WorldLevelDisabledTests(unittest.TestCase):
    def database(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE system_feature_controls(id,control_type,condition_type,describe,state)')
        db.execute('INSERT INTO system_feature_controls VALUES(?,?,?,?,1)', patch.IDENTITY)
        db.execute("INSERT INTO system_feature_controls VALUES(2,2,1,'Sailing Activity',1)")
        db.commit()
        return db

    def test_native_gate_only_and_repeat(self):
        db = self.database()
        before = db.execute('SELECT * FROM system_feature_controls WHERE id=2').fetchall()
        self.assertEqual(patch.transform(db), 1)
        self.assertEqual(db.execute('SELECT state FROM system_feature_controls WHERE id=1').fetchone(), (0,))
        self.assertEqual(db.execute('SELECT * FROM system_feature_controls WHERE id=2').fetchall(), before)
        self.assertEqual(patch.transform(db), 0)

    def test_ambiguous_control_rejected_without_mutation(self):
        db = self.database()
        db.execute("INSERT INTO system_feature_controls VALUES(3,1,0,'other',1)")
        with self.assertRaises(ValueError):
            patch.transform(db)
        self.assertEqual(db.execute('SELECT state FROM system_feature_controls WHERE id=1').fetchone(), (1,))

    def test_identity_and_invalid_state_rejected(self):
        for column, value in [('condition_type', 999), ('control_type', 2), ('state', 2), ('describe', 'other')]:
            with self.subTest(column=column):
                db = self.database()
                db.execute(f'UPDATE system_feature_controls SET {column}=? WHERE id=1', (value,))
                before = db.iterdump()
                before = list(before)
                with self.assertRaises(ValueError):
                    patch.transform(db)
                self.assertEqual(list(db.iterdump()), before)

    def test_builder_releases_sqlite_file_before_return(self):
        # Windows AAPak opens the replacement with FileShare.Read. A leaked
        # writable SQLite handle prevents this and also prevents renaming.
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'source.sqlite3'
            output = Path(directory) / 'replacement.sqlite3'
            db = sqlite3.connect(source)
            fixture = self.database()
            fixture.backup(db)
            db.close()
            with mock_patch.dict(patch.PROFILES, {patch.sha256(source): 'fixture'}):
                result = patch.build(source, output)
            self.assertEqual(result['changed'], 1)
            output.rename(Path(directory) / 'released.sqlite3')


if __name__ == '__main__':
    unittest.main()
