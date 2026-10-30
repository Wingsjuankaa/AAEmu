"""Pure UI coordination checks: no native client, Docker, service, or Tk window starts."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.dont_write_bytecode = True
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))
SPEC = importlib.util.spec_from_file_location('aa10_sandbox_tool', SCRIPT_ROOT/'aa10_sandbox_tool.py')
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


class SandboxToolTests(unittest.TestCase):
    def test_world_restart_remains_observable_while_character_is_offline(self):
        runtime = {'pid': 42, 'updateCount': 0}
        observed = tool.poll_observation(lambda: runtime, Mock(side_effect=RuntimeError('offline')))
        self.assertEqual(observed, (runtime, None))

    def test_scenario_is_observed_even_if_runtime_diagnostics_temporarily_fail(self):
        scenario = {'state': 'ready', 'attempt': 3}
        observed = tool.poll_observation(Mock(side_effect=RuntimeError('restarting')), lambda: scenario)
        self.assertEqual(observed, (None, scenario))
        self.assertEqual(tool.poll_observation(Mock(side_effect=RuntimeError()),
                                               Mock(side_effect=RuntimeError())), (None, None))

    def test_busy_worker_does_not_consume_pending_auto_reset(self):
        pending = tool.PendingAutoReset()
        pending.request()
        start = Mock(side_effect=[False, True])
        self.assertFalse(pending.try_start(True, True, start))
        self.assertTrue(pending.pending)
        self.assertTrue(pending.try_start(True, True, start))
        self.assertFalse(pending.pending)
        self.assertFalse(pending.try_start(True, True, start))
        self.assertEqual(start.call_count, 2)

    def test_multiple_updates_coalesce_and_wait_for_ready_scenario(self):
        pending = tool.PendingAutoReset()
        pending.request()
        pending.request()
        start = Mock(return_value=True)
        self.assertFalse(pending.try_start(True, False, start))
        start.assert_not_called()
        self.assertTrue(pending.pending)
        self.assertTrue(pending.try_start(True, True, start))
        self.assertFalse(pending.try_start(True, True, start))
        start.assert_called_once()

    def test_disabling_auto_reset_or_restarting_world_clears_the_pending_request(self):
        pending = tool.PendingAutoReset()
        pending.request()
        start = Mock(return_value=True)
        self.assertFalse(pending.try_start(False, True, start))
        self.assertFalse(pending.pending)
        pending.request()
        pending.clear()
        self.assertFalse(pending.try_start(True, True, start))
        start.assert_not_called()

    def test_combined_layout_limits_are_validated_before_reconfigure(self):
        with self.assertRaisesRegex(ValueError, '60 m'):
            tool.layout(16, 40, 8)
        for count, distance, separation in [(1, 40, 8), (16, 20, 8), (4, 5, 2)]:
            result = tool.layout(count, distance, separation)
            self.assertEqual(len(result), count)
            self.assertTrue(all(abs(p['Forward']) <= 60 and abs(p['Right']) <= 60 for p in result))

    def test_invalid_numeric_layout_is_rejected(self):
        for values in [(0, 5, 2), (17, 5, 2), (4, float('nan'), 2),
                       (4, 5, float('inf')), (4, 0, 2), (4, 5, 0)]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                tool.layout(*values)

    def test_leaving_the_ui_main_loop_does_not_abandon_owned_startup(self):
        root = tool.sandbox.PROJECT/'artifacts/tests/sandbox-tool'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            marker = Path(directory)/'startup-finished.txt'
            script = (
                'import sys,time\n'
                'from pathlib import Path\n'
                f'sys.path.insert(0,{str(SCRIPT_ROOT)!r})\n'
                'import aa10_sandbox_tool as tool\n'
                'def finish_owned_startup():\n'
                '    time.sleep(.1)\n'
                f'    Path({str(marker)!r}).write_text("reveal-or-cancel-completed")\n'
                'tool.start_owned_operation(finish_owned_startup)\n'
                '# The main thread returns just as it would after closing Tk controls.\n')
            env = dict(os.environ, TEMP=directory, TMP=directory, PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-B', '-c', script], env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(marker.read_text(), 'reveal-or-cancel-completed')


if __name__ == '__main__':
    unittest.main()
