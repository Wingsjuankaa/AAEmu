import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import aa10_sandbox as sandbox
import aa10_sandbox_hub as hub


class TrainingHubTests(unittest.TestCase):
    def setUp(self):
        self.preset = sandbox.read_jsonc(hub.PRESET)
        self.original = {'MechanicsSandbox': {'Enabled': True, 'CharacterName': 'Sandbox',
            'CharacterId': 1001, 'AccountId': 1, 'WorldId': 0, 'InstanceId': 0,
            'ZoneKey': 379, 'DummyTemplateId': 7512, 'Origin': copy.deepcopy(sandbox.ORIGIN),
            'Dummies': copy.deepcopy(self.preset['Dummies'])}}

    def test_plan_preserves_binding_and_does_not_alias_original_or_preset(self):
        candidate = hub.plan(self.original, self.preset)
        self.assertEqual(candidate['MechanicsSandbox']['DummyTemplateId'], 7512)
        self.assertEqual(candidate['MechanicsSandbox']['AccountId'], 1)
        self.assertNotIn('Services', self.original['MechanicsSandbox'])
        candidate['MechanicsSandbox']['Services'][0]['TemplateId'] = 0
        self.assertEqual(self.preset['Services'][0]['TemplateId'], 18870)

    def test_wrong_actor_zone_service_and_nonfinite_offsets_are_rejected(self):
        for key, value in [('AccountId', 2), ('CharacterId', 1002), ('ZoneKey', 198), ('Enabled', False)]:
            original = copy.deepcopy(self.original)
            original['MechanicsSandbox'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                hub.plan(original, self.preset)
        for change in ('zone', 'origin', 'quest_npc', 'duplicate', 'nan'):
            preset = copy.deepcopy(self.preset)
            if change == 'zone': preset['ZoneKey'] = 302
            if change == 'origin': preset['Origin']['Z'] += 10
            if change == 'quest_npc': preset['Services'][0]['TemplateId'] = 14168
            if change == 'duplicate': preset['Services'][1] = preset['Services'][0]
            if change == 'nan': preset['Services'][0]['Forward'] = float('nan')
            with self.subTest(change=change), self.assertRaises(ValueError):
                hub.plan(self.original, preset)

    def test_profile_rejection_stops_before_scene_mutation_and_restores_configuration(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            path = root/'config/Configurations/MechanicsSandbox.json'
            sandbox.write_json(path, self.original)
            good = {'success': True, 'state': 'validated'}
            expected = hub.plan(self.original, self.preset)['MechanicsSandbox']
            rejected = {'success': False, 'state': 'rejected', 'message': 'servicio inválido',
                        'sceneName': expected['SceneName'], 'services': [
                            {'role': role, 'templateId': ident} for role, ident in hub.ROLES.items()]}
            old = good | {'sceneName': 'Laboratorio AA10', 'services': []}
            def wait(predicate, *args, **kwargs):
                return predicate()
            def api(_, endpoint, body=None):
                return {'pid': 240} if endpoint.endswith('/runtime') else {}
            with patch.object(hub, 'validate', side_effect=[good, rejected, old, old]), \
                    patch.object(sandbox, 'api', side_effect=api), \
                    patch.object(sandbox, 'zone_ready', return_value=True), \
                    patch.object(sandbox, 'wait_for', side_effect=wait), \
                    patch.object(sandbox, 'command', return_value={'state': 'ready'}) as command:
                with self.assertRaisesRegex(ValueError, 'servicio inválido'):
                    hub.apply(root)
                self.assertEqual(sandbox.read_jsonc(path), self.original)
                self.assertEqual([call.args[1] for call in command.call_args_list], ['status'])

    def test_unknown_passive_preflight_does_not_write_configuration_or_clear_scene(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            path = root/'config/Configurations/MechanicsSandbox.json'
            sandbox.write_json(path, self.original)
            with patch.object(hub, 'validate', return_value={'success': False, 'message': 'Pasivo 123'}), \
                    patch.object(sandbox, 'command') as command:
                with self.assertRaisesRegex(ValueError, 'Pasivo 123'):
                    hub.apply(root)
                command.assert_not_called()
                self.assertEqual(sandbox.read_jsonc(path), self.original)
                self.assertFalse((root/'backups').exists())


if __name__ == '__main__':
    unittest.main()
