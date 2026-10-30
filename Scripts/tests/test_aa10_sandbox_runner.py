import datetime as dt
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import sys
import os
import unittest
from unittest.mock import patch, Mock

SPEC = importlib.util.spec_from_file_location('aa10_sandbox', Path(__file__).parents[1]/'aa10_sandbox.py')
sys.path.insert(0, str(Path(__file__).parents[1]))
sandbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sandbox)


class SandboxRunnerTests(unittest.TestCase):
    def test_compose_is_separate_and_does_not_publish_admin_or_db(self):
        value = sandbox.make_compose(sandbox.DEFAULT_ROOT, '192.168.1.94', 'example-only', 'login:existing')
        self.assertNotIn('ports', value['services']['db'])
        ports = sum((s.get('ports', []) for s in value['services'].values()), [])
        self.assertEqual(ports, ['127.0.0.1:3237:1237', '127.0.0.1:3239:1239',
                                 '127.0.0.1:3250:1250', '192.168.1.94:3240:1240'])
        for service in value['services'].values():
            for mount in service.get('volumes', []):
                self.assertTrue(mount['source'].startswith('E:/'))
                if not mount['read_only']:
                    self.assertTrue(mount['source'].startswith(str(sandbox.DEFAULT_ROOT).replace('\\', '/')))

    def test_ready_requires_exact_zone_instance_and_recent_heartbeat(self):
        zone = {'ZoneId': 379, 'InstanceId': 0, 'State': 'ZoneLoaded',
                'LastHeartbeatAtUtc': dt.datetime.now(dt.timezone.utc).isoformat()}
        self.assertTrue(sandbox.zone_ready({'Zones': [zone]}))
        for changed in [{'ZoneId': 179}, {'InstanceId': 1}, {'State': 'Joined'},
                        {'LastHeartbeatAtUtc': '2020-01-01T00:00:00Z'},
                        {'LastHeartbeatAtUtc': None}]:
            self.assertFalse(sandbox.zone_ready({'Zones': [zone | changed]}))

    def test_root_cannot_be_source_or_c_drive(self):
        for value in ['C:/sandbox', sandbox.PROJECT, sandbox.SOURCE_CLIENT, sandbox.SOURCE_ZONE,
                      sandbox.DEFAULT_ROOT/'../../../client', sandbox.PROJECT/'runtime']:
            with self.assertRaises(ValueError):
                sandbox.safe_root(value)
        self.assertEqual(sandbox.safe_root(sandbox.DEFAULT_ROOT), sandbox.DEFAULT_ROOT)

    def test_json_comments_preserve_paths_urls_and_escaped_quotes(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            path = Path(directory)/'settings.json'
            path.write_text('{// comment\n"url":"http://127.0.0.1", /* c */ "q":"a\\\"//b"}', encoding='utf-8')
            self.assertEqual(sandbox.read_jsonc(path), {'url': 'http://127.0.0.1', 'q': 'a"//b'})

    def test_faulted_scenario_is_fatal_instead_of_retried_until_timeout(self):
        response = {'success': False, 'state': 'faulted', 'message': 'old cast failed'}
        with patch.object(sandbox, 'api', return_value=response):
            with self.assertRaisesRegex(ValueError, 'old cast failed'):
                sandbox.ready_result(sandbox.DEFAULT_ROOT)

    def test_rejected_preparation_is_fatal_without_waiting_four_minutes_to_drop_the_session(self):
        with patch.object(sandbox, 'api', return_value={'success': False, 'state': 'rejected',
                                                       'message': 'unsupported passive producer'}):
            with self.assertRaisesRegex(ValueError, 'unsupported passive producer'):
                sandbox.command(sandbox.DEFAULT_ROOT, 'begin')

    def test_scene_rejection_after_entry_releases_panel_but_keeps_connected_client(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            (root/'client').mkdir()
            (root/'client/.aa10-sandbox-profile.json').touch()
            (root/'autoentry-applied.json').touch()
            presentation = Mock()
            presentation._error = None
            presentation.process.pid = 123
            presentation.process.poll.return_value = None
            module = types.SimpleNamespace(LoadingClient=Mock(return_value=presentation), VisibleClient=Mock())
            with patch.object(sandbox, 'prepare', return_value={}), patch.object(sandbox, 'seed'), \
                    patch.object(sandbox, 'compose'), patch.object(sandbox, 'ensure_credentials', return_value='fixture'), \
                    patch.object(sandbox, 'validate_client'), patch.object(sandbox, 'zone_ready', return_value=True), \
                    patch.object(sandbox, 'api', return_value={'Players': []}), \
                    patch.object(sandbox, 'client_running', return_value=False), \
                    patch.object(sandbox, 'close_disconnected_client'), \
                    patch.object(sandbox, 'character_ready', return_value=True), \
                    patch.object(sandbox, 'wait_for', side_effect=lambda predicate, *a, **k: predicate()), \
                    patch.object(sandbox, 'command', side_effect=ValueError('profile blocked')), \
                    patch.object(sandbox, 'capture'), \
                    patch.dict(sandbox.sys.modules, {'aa10_sandbox_window': module}):
                with self.assertRaisesRegex(ValueError, 'profile blocked'):
                    sandbox._start(root, authorize_zone=True)
                presentation.reveal.assert_called_once()
                presentation.cancel.assert_not_called()
                presentation.process.terminate.assert_not_called()

    def test_zone_in_startup_is_never_started_twice(self):
        with patch.object(sandbox, 'sha256', return_value=sandbox.ZONE_HASH), \
                patch.object(sandbox, 'sandbox_zone_processes', return_value=[{'ProcessId': 123}]), \
                patch.object(sandbox, 'wait_for', return_value=True), \
                patch.object(sandbox.subprocess, 'Popen') as start:
            sandbox.start_zone(sandbox.DEFAULT_ROOT, {'worldHost': '192.168.1.94'})
            start.assert_not_called()

    def test_cleanup_requires_final_idle_state(self):
        with patch.object(sandbox, 'command', return_value={'state': 'clearing'}):
            self.assertIsNone(sandbox.idle_result(sandbox.DEFAULT_ROOT))
        with patch.object(sandbox, 'command', return_value={'state': 'idle', 'dummies': []}):
            self.assertEqual(sandbox.idle_result(sandbox.DEFAULT_ROOT)['dummies'], [])

    def test_entry_wait_requires_live_validated_character_not_a_cached_world_avatar(self):
        for value in [{'state': 'offline'}, {'state': 'rejected', 'characterId': 1001},
                      {'state': 'ready', 'characterId': 999}]:
            with patch.object(sandbox, 'api', return_value=value):
                self.assertFalse(sandbox.character_ready(sandbox.DEFAULT_ROOT))
        for state in ('idle', 'ready', 'faulted'):
            with patch.object(sandbox, 'api', return_value={'state': state, 'characterId': 1001}):
                self.assertTrue(sandbox.character_ready(sandbox.DEFAULT_ROOT))

    def test_concurrent_launcher_cannot_replace_a_startup_in_progress(self):
        import msvcrt
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            (root/'temp').mkdir()
            with (root/'temp/launcher.lock').open('w+b') as lock:
                lock.write(b'0')
                lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    with patch.object(sandbox, '_start') as operation:
                        with self.assertRaisesRegex(RuntimeError, 'arranque en curso'):
                            sandbox.start(root, True)
                        operation.assert_not_called()
                finally:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            with patch.object(sandbox, '_start', return_value='ready') as operation:
                self.assertEqual(sandbox.start(root, True), 'ready')
                operation.assert_called_once_with(root, True, False, False)

    def test_zone_recovery_rejects_unowned_or_reused_pids_without_stopping_anything(self):
        root = sandbox.DEFAULT_ROOT
        executable = str(root/'zone/Bin64/AAEmu.ZoneHost.exe')
        helper = str(sandbox.PROJECT/'tools/AAEmu.ControlCenter/resources/native/win-x64/AAEmu.ZoneProcessHost.exe')
        owner = {'executable': executable, 'zoneKey': 379, 'worldPort': 3240,
                 'helperPid': 123, 'requestedAtUtc': '20261029T225455Z'}
        pair = [{'ProcessId': 123, 'ParentProcessId': 50, 'ExecutablePath': helper,
                 'CreatedUtc': '2026-10-29T22:54:55+00:00'},
                {'ProcessId': 124, 'ParentProcessId': 123, 'ExecutablePath': executable,
                 'CreatedUtc': '2026-10-29T22:54:55+00:00'}]
        for invalid in [pair[:1], pair + [pair[1]],
                        [pair[0], pair[1] | {'ParentProcessId': 999}],
                        [pair[0] | {'CreatedUtc': '2026-10-29T23:00:00+00:00'}, pair[1]]]:
            with self.subTest(invalid=invalid), patch.object(sandbox, 'read_jsonc', return_value=owner), \
                    patch.object(sandbox, 'run') as stopped:
                with self.assertRaises(ValueError):
                    sandbox.stop_owned_zone(root, invalid)
                stopped.assert_not_called()

    def test_recorded_processes_that_exit_before_stop_are_safe_without_weakening_pid_reuse_checks(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            helper = str(sandbox.PROJECT/'tools/AAEmu.ControlCenter/resources/native/win-x64/AAEmu.ZoneProcessHost.exe')
            executable = str(root/'zone/Bin64/AAEmu.ZoneHost.exe')
            stamp = dt.datetime.now(dt.timezone.utc)
            created = stamp.isoformat()
            owner = {'executable': executable, 'zoneKey': 379, 'worldPort': 3240,
                     'helperPid': 2147483504, 'requestedAtUtc': stamp.strftime('%Y%m%dT%H%M%SZ')}
            sandbox.write_json(root/'zone-owner.json', owner)
            pair = [{'ProcessId': 2147483504, 'ParentProcessId': 0, 'ExecutablePath': helper, 'CreatedUtc': created},
                    {'ProcessId': 2147483508, 'ParentProcessId': 2147483504, 'ExecutablePath': executable, 'CreatedUtc': created}]
            with patch.object(sandbox, 'capture') as captured:
                sandbox.stop_owned_zone(root, pair, planned_replacement=True)
            result = captured.call_args.args[2]
            self.assertEqual(result['stoppedPids'], [])
            self.assertEqual([item['state'] for item in result['processOutcomes']], ['already-exited', 'already-exited'])

    def test_live_identity_guard_accepts_equivalent_utc_formats_and_rejects_a_reused_pid(self):
        pid = os.getpid()
        stamp = sandbox.run(['powershell.exe', '-NoProfile', '-Command',
            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CreationDate.ToUniversalTime().ToString('o')"]).stdout.decode().strip()
        process = {'ProcessId': pid, 'ExecutablePath': sys.executable, 'CreatedUtc': stamp.replace('Z', '+00:00')}
        checked = sandbox.run(['powershell.exe', '-NoProfile', '-Command', sandbox.owned_process_guard(process, stop=False)])
        self.assertEqual(checked.stdout.decode().strip(), 'identity-confirmed')
        process['CreatedUtc'] = '1999-01-01T00:00:00Z'
        rejected = sandbox.run(['powershell.exe', '-NoProfile', '-Command', sandbox.owned_process_guard(process, stop=False)], check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('identity changed', rejected.stderr.decode(errors='replace'))

    def test_launch_verifies_profile_and_package_identity_without_rehashing_package(self):
        with tempfile.TemporaryDirectory(dir=sandbox.DEFAULT_ROOT/'temp') as directory:
            root = Path(directory)
            (root/'client').mkdir()
            package = root/'client/game_pak'
            package.write_bytes(b'independent-package-fixture')
            profile = {'patchId': 'aa10-sandbox-e-profile-v1', 'profilePath': str(root/'profile'),
                       'currentSha256': 'AB'}
            sandbox.write_json(root/'client/.aa10-sandbox-profile.json', profile)
            marker = {'character': 'Sandbox', 'world_id': 1, 'zone_key': 379,
                      'patch_id': 'aa10-sandbox-autoentry-v3',
                      'package_path': str(package), 'package_size': package.stat().st_size,
                      'package_mtime_ns': package.stat().st_mtime_ns, 'x2game_sha256': 'AB'}
            marker['package_inode'] = package.stat().st_ino
            sandbox.write_json(root/'autoentry-applied.json', marker)
            with patch.object(sandbox, 'sha256', return_value='ab') as hashed:
                sandbox.validate_client(root)
                self.assertEqual(hashed.call_count, 2)
                self.assertNotIn(package, [call.args[0] for call in hashed.call_args_list])
            package.write_bytes(b'changed')
            with patch.object(sandbox, 'sha256', return_value='ab'):
                with self.assertRaisesRegex(ValueError, 'package changed'):
                    sandbox.validate_client(root)

    def test_generated_launcher_proof_matches_legacy_db_contract(self):
        value = sandbox.credential_material()
        self.assertTrue(value['token'].startswith('aaemu-sha256-v1:'))
        proof = value['token'].split(':', 1)[1]
        self.assertEqual(len(proof), 64)
        self.assertEqual(bytes.fromhex(proof), base64.b64decode(value['storage']))
        self.assertNotIn('password', value)


if __name__ == '__main__':
    unittest.main()
