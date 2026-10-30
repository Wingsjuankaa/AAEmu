import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
import aa10_sandbox as sandbox
import aa10_sandbox_scenarios as scenes
import aa10_sandbox_hub as hub


class ScenarioIdentityTests(unittest.TestCase):
    def test_unknown_profiles_and_mismatched_name_are_rejected(self):
        for zone in (0, 392, 406, 412, 65535):
            with self.assertRaises(ValueError):
                scenes.definition(zone)
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            sandbox.write_json(root/'sandbox.json', {'zoneKey': 411, 'zoneName': 'gatekeeper_hall'})
            with self.assertRaises(ValueError):
                scenes.selected(root)

    def test_new_zone_cannot_start_without_verified_installed_package_identities(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            sandbox.write_json(root/'sandbox.json', scenes.LAB)
            with self.assertRaises(FileNotFoundError):
                scenes.verify_installation(root)
            records = {}
            for role, relative in [('client', 'client/game_pak'), ('native', 'zone/game_pak')]:
                path = root/relative
                path.parent.mkdir(parents=True)
                path.write_bytes(role.encode())
                stat = path.stat()
                records[role] = {'path': str(path), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'inode': stat.st_ino}
            marker = {'patch_id': 'aa10-sandbox-zone411-v1', 'zoneKey': 411,
                      'zoneName': scenes.LAB['zoneName'], 'worldId': 0,
                      'state': 'resources_verified', 'packages': records}
            sandbox.write_json(root/'zone411-installed.json', marker)
            scenes.verify_installation(root)
            (root/'zone/game_pak').write_bytes(b'drift')
            with self.assertRaises(ValueError):
                scenes.verify_installation(root)

    def test_lab_hub_uses_its_own_origin_and_cannot_migrate_the_hall(self):
        preset = sandbox.read_jsonc(hub.PRESET.with_name('aa10_sandbox_training_hub_zone411.json'))
        doc = {'MechanicsSandbox': {'Enabled': True, 'CharacterName': 'Sandbox', 'CharacterId': 1001,
               'AccountId': 1, 'WorldId': 0, 'InstanceId': 0, 'ZoneKey': 411, 'DummyTemplateId': 7512}}
        value = hub.plan(doc, preset)
        self.assertEqual(value['MechanicsSandbox']['Origin'], scenes.LAB['origin'])
        doc['MechanicsSandbox']['ZoneKey'] = 379
        with self.assertRaises(ValueError):
            hub.plan(doc, preset)


if __name__ == '__main__':
    unittest.main()
