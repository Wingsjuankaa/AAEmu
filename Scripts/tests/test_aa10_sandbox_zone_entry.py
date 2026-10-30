import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
import BuildAa10SandboxZoneEntry as entry
import PatchAa10SandboxAutoEntry as accepted
import test_patch_aa10_sandbox_autoentry as retail


class ZoneEntryTests(unittest.TestCase):
    def test_reproduces_v3_then_derives_identical_zone411_payloads(self):
        with tempfile.TemporaryDirectory(dir=accepted.TEMP) as directory:
            a = entry.build(Path(directory)/'a.alb')
            b = entry.build(Path(directory)/'b.alb')
            self.assertEqual(a['after_sha256'], b['after_sha256'])
            self.assertEqual(a['size'], 13846)
            self.assertNotEqual(a['before_sha256'], a['after_sha256'])
            self.assertEqual(hashlib.sha256((Path(directory)/'a.alb').read_bytes()).hexdigest().upper(), a['after_sha256'])
            with self.assertRaises(ValueError):
                entry.build(Path(directory)/'a.alb')

    def test_real_retail_handlers_enter_exact_realm_and_new_zone_with_release_flags(self):
        source = entry.source_for_zone(entry.SOURCE.read_text(encoding='utf-8-sig'))
        fixture = retail.RetailTests().widget_fixture()
        assertions = '''
local wnd=CreateServerWnd("serverWnd")
wnd:Show(true)
worldInfos={{id=1,name="Ordinary World"}}
wnd.handlers.OnUpdate(wnd,250);assert(#requests==0)
worldInfos={{id=1,name="AA10 Sandbox"}}
wnd.handlers.OnUpdate(wnd,250);assert(#requests==1)
assert(requests[1].world==1 and requests[1].zone==411)
wnd.handlers.OnUpdate(wnd,1000);assert(#requests==1)
'''
        result = subprocess.run([str(retail.LUA), '-'], input=(fixture+source+assertions).encode(), capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))

    def test_missing_source_anchors_are_rejected(self):
        with self.assertRaises(RuntimeError):
            entry.source_for_zone('')


if __name__ == '__main__':
    unittest.main()
