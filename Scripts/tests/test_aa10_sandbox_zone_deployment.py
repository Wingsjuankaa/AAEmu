from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import aa10_sandbox as sandbox
import aa10_sandbox_zone as zone


class ZoneDeploymentTests(unittest.TestCase):
    def test_private_lobby_uses_installed_level_preserving_every_other_setting(self):
        document = {'InitialConfig': {'LobbyLevel': 'w_hanuimaru_1', 'LobbyImmersiveMode': True,
                                     'LobbyLevelChecksum': 0, 'Host': 'fixture'}}
        candidate = zone.lobby_configuration(document)
        self.assertEqual(candidate['InitialConfig']['LobbyLevel'], 'aa10_sandbox_lab')
        self.assertEqual(document['InitialConfig']['LobbyLevel'], 'w_hanuimaru_1')
        self.assertEqual({k: v for k, v in candidate['InitialConfig'].items() if k != 'LobbyLevel'},
                         {k: v for k, v in document['InitialConfig'].items() if k != 'LobbyLevel'})
        self.assertEqual(zone.lobby_configuration(candidate), candidate)
        document['InitialConfig']['LobbyLevel'] = 'unrelated'
        with self.assertRaises(ValueError): zone.lobby_configuration(document)

    def test_no_lifecycle_without_exact_test_authorization(self):
        with patch.object(zone, 'load_plan') as plan, patch.object(sandbox, 'compose') as compose:
            with self.assertRaisesRegex(ValueError, 'authorization'):
                zone.activate(Path('E:/missing.json'), 'A'*64)
            plan.assert_not_called(); compose.assert_not_called()

    def test_compose_rebind_is_private_and_keeps_database_service_and_source_object(self):
        source = {'services': {'db': {'environment': {'MYSQL_ROOT_PASSWORD': 'fixture'}},
                  'game': {'volumes': [
                      {'target': '/app/game/ClientData', 'source': str(sandbox.SOURCE_CLIENT), 'read_only': True},
                      {'target': '/app/game/Data', 'source': str(sandbox.REPO/'.server_files/AAEmu.Game/Data'), 'read_only': True}]}}}
        value = zone.replace_compose_bindings(source)
        self.assertEqual(value['services']['db'], source['services']['db'])
        self.assertEqual(source['services']['game']['volumes'][0]['source'], str(sandbox.SOURCE_CLIENT))
        volumes = value['services']['game']['volumes']
        self.assertEqual(len(volumes), 4)
        self.assertEqual(volumes[0]['source'], str(zone.ROOT/'client').replace('\\', '/'))
        self.assertTrue(all(mount['read_only'] for mount in volumes))
        source['services']['game']['volumes'][1]['source'] = str(sandbox.PROJECT/'runtime/another-stack/Data')
        with self.assertRaises(ValueError): zone.replace_compose_bindings(source)

    def test_exact_file_backup_restores_existing_removes_only_owned_new_files_and_rejects_escape(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            old, added, unrelated = root/'old.bin', root/'new.bin', root/'unrelated.bin'
            old.write_bytes(b'old'); unrelated.write_bytes(b'keep')
            with patch.object(zone, 'ROOT', root):
                records = zone.backup_files([old, added], root/'backup')
                old.write_bytes(b'changed'); added.write_bytes(b'added')
                zone.restore_files(records)
                self.assertEqual(old.read_bytes(), b'old')
                self.assertFalse(added.exists())
                self.assertEqual(unrelated.read_bytes(), b'keep')
                with self.assertRaises(ValueError): zone.owned_target(root/'../escape.bin')

    def test_character_relocation_rejects_other_zones_and_nonfinite_values_before_sql(self):
        good = dict(zone_id=411, x=575, y=506, z=260, yaw=0, pitch=0, roll=0)
        with patch.object(zone, 'actor_sql') as sql:
            for invalid in [good | {'zone_id': 406}, good | {'z': float('nan')}, good | {'x': '1; DROP TABLE characters'}]:
                with self.assertRaises(ValueError): zone.set_actor_position(invalid)
            sql.assert_not_called()

    def test_windows_filetime_source_binding_keeps_submicrosecond_precision(self):
        self.assertEqual(zone.epoch_ns('2026-09-04T17:08:15.5356651Z') % 1_000_000_000, 535665100)


if __name__ == '__main__':
    unittest.main()
