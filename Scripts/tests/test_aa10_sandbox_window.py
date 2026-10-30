"""Loading panel regressions: mocks only, no real windows or desktop input."""
import importlib.util
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('sandbox_window', Path(__file__).parents[1]/'aa10_sandbox_window.py')
window = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(window)
ROOT = Path('E:/AAEmu/rama_10/artifacts/tests/sandbox-window')
ROOT.mkdir(parents=True, exist_ok=True)


class PresentationTests(unittest.TestCase):
    def test_access_denied_external_anchor_retries_only_own_panel_without_reordering_other_apps(self):
        api = Mock()
        api.SetWindowPos.side_effect = [False, True]
        with patch.object(window.ctypes, 'get_last_error', return_value=5):
            self.assertTrue(window.place_panel(api, 88, [(1000000, 99, 0, 0, 1280, 720)],
                                              previous=77, foreground=77))
        retry = api.SetWindowPos.call_args_list[1].args
        self.assertEqual(retry[0], 88)  # Only the owned panel is the mutation target.
        self.assertIsNone(retry[1])
        self.assertTrue(retry[-1] & 0x0004)  # Other apps keep their order.
        self.assertTrue(retry[-1] & 0x0010)  # No activation.

    def test_local_panel_order_uses_no_foreign_anchor_and_raises_only_above_foreground_game(self):
        api = Mock()
        self.assertTrue(window.place_panel(api, 88, [(1000000, 99, 0, 0, 1280, 720)],
                                          previous=77, foreground=99, local_order_only=True))
        args = api.SetWindowPos.call_args.args
        self.assertEqual(args[0], 88)
        self.assertIsNone(args[1])
        self.assertFalse(args[-1] & 0x0004)
        self.assertTrue(args[-1] & 0x0010)

    def test_unrelated_panel_failure_is_reported_without_repeated_access_attempts(self):
        api = Mock()
        api.SetWindowPos.return_value = False
        with patch.object(window.ctypes, 'get_last_error', return_value=1400), self.assertRaises(OSError):
            window.place_panel(api, 88, [(1000000, 99, 0, 0, 1280, 720)], previous=77, foreground=99)
        self.assertEqual(api.SetWindowPos.call_count, 1)

    def test_cover_keeps_other_apps_above_game_without_activating_any_window(self):
        windows = [(1280*768, 99, 381, 177, 1280, 768)]
        main, after, x, y, width, height, flags = window.placement(windows, cover=88, previous=77)
        self.assertEqual((main, after, x, y, width, height), (99, 77, 381, 177, 1280, 768))
        self.assertTrue(flags & 0x0010)
        self.assertFalse(flags & 0x0040)  # Does not show/hide the game.
        self.assertFalse(flags & 0x0080)

    def test_already_adjacent_panel_does_not_reorder_the_desktop(self):
        result = window.placement([(1280*768, 99, -1200, 177, 1280, 768)], cover=88, previous=88)
        self.assertEqual(result[2], -1200)
        self.assertTrue(result[-1] & 0x0004)
        self.assertTrue(result[-1] & 0x0010)

    def test_largest_rendering_window_is_selected(self):
        result = window.placement([(640*400, 10, 0, 0, 640, 400), (1280*768, 99, 381, 177, 1280, 768)],
                                  cover=88, previous=None)
        self.assertEqual(result[0], 99)

    def test_normal_game_start_uses_supported_flags_without_touching_profile_or_window(self):
        process = Mock()
        with patch.object(window.subprocess, 'Popen', return_value=process) as spawn:
            candidate = window.VisibleClient(['owned-fixture.exe'], Path('E:/fixture'), {})
            candidate.reveal()
            startup = spawn.call_args.kwargs['startupinfo']
            self.assertEqual(startup.dwFlags, window.subprocess.STARTF_USESHOWWINDOW)
            self.assertEqual(startup.wShowWindow, 4)
            self.assertIs(candidate.process, process)

    def test_loading_client_reveal_removes_its_panel_without_window_manipulation(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            candidate = self.candidate(directory)
            candidate.reveal()
            self.assertTrue(candidate.ready_path.exists())
            candidate.panel.wait.assert_called_once_with(timeout=5)
            candidate.process.terminate.assert_not_called()

    def candidate(self, directory):
        candidate = window.LoadingClient.__new__(window.LoadingClient)
        candidate.ready_path = Path(directory)/'ready.signal'
        candidate.error_path = Path(directory)/'error.json'
        candidate._closing = False
        candidate.panel = Mock()
        candidate.panel.wait.return_value = 0
        candidate.panel.poll.return_value = None
        candidate.process = Mock()
        candidate.process.poll.return_value = None
        return candidate

    def test_loading_panel_failure_is_not_a_successful_launch(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            candidate = self.candidate(directory)
            candidate.error_path.write_text(json.dumps({'error': 'fixture'}))
            with self.assertRaisesRegex(RuntimeError, 'Loading panel failed'):
                candidate.reveal()

    def test_cancel_terminates_only_its_child_and_releases_the_panel(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            candidate = self.candidate(directory)
            candidate.cancel()
            candidate.process.terminate.assert_called_once()
            candidate.process.wait.assert_called_once_with(timeout=5)
            self.assertEqual(candidate.ready_path.read_text(), 'cancelled')

    def test_panel_runs_in_its_own_pythonw_process_instead_of_a_tk_worker_thread(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            game, panel = Mock(pid=123), Mock()
            with patch.object(window.subprocess, 'Popen', side_effect=[game, panel]) as launch:
                candidate = window.LoadingClient(['E:/owned/client.exe'], Path(directory), {'TEMP': directory})
                args = launch.call_args_list[1].args[0]
                self.assertTrue(args[0].endswith('pythonw.exe'))
                self.assertIn('--game-pid', args)
                self.assertIn('123', args)
                self.assertIs(candidate.panel, panel)
                self.assertEqual(candidate.ready_path.drive.upper(), 'E:')

    def test_isolated_main_thread_tcl_exits_cleanly_without_loading_tk_or_creating_windows(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            env = dict(os.environ, TEMP=directory, TMP=directory, PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-B', '-c',
                'import tkinter; interp=tkinter.Tcl(); print(interp.eval("info exists tk_version"))'],
                env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '0')


if __name__ == '__main__':
    unittest.main()
