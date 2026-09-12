import io
import os
from pathlib import Path
import tempfile
import unittest
from test_pak_append import fixture
import Aa10PakAppend as a
import ApplyAa10AlphaShortcut as install
import ApplyAa10SpanishUiLayout as tools


class AlphaHudInstallTests(unittest.TestCase):
    def test_native_replace_append_reextract_and_exact_rollback(self):
        original = fixture()[:-480]+bytes(480) # Native footer encrypts only its 32-byte header.
        entry = 'game/ui/original.bin'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); pak = root/'test.pak'; pak.write_bytes(original)
            backup = root/'before.alb'; backup.write_bytes(b'native data')
            replacement = root/'after.alb'; replacement.write_bytes(b'alpha data!')
            os.utime(replacement, (install.STAMP, install.STAMP))
            offset, tail, count, _ = a.read_tail(io.BytesIO(original))
            index, payload_offset, _ = install.locate(tail, count, [entry])[entry]
            tools.run('dotnet', tools.REPLACE, pak, entry, replacement, a.sha(backup.read_bytes()))
            with pak.open('rb') as stream: plan = a.prepare(stream, 'game/ui/custom/aaemu/private_alpha.dds', b'icon')
            install.require_only_record_changed(tail, plan['before'], index)
            a.write_suffix(pak, offset, plan['before'], plan['after'])
            self.assertEqual(tools.extract(pak, entry, root/'verified.alb'), a.sha(replacement.read_bytes()))
            actual = a.sha(pak.read_bytes())
            install.rollback(pak, entry, backup, a.sha(replacement.read_bytes()), index, tail, plan)
            self.assertEqual(pak.read_bytes(), original)
            before, after = install.hash_pair(pak, payload_offset, replacement.read_bytes(), offset, plan['after'])
            self.assertEqual(before, a.sha(original)); self.assertEqual(after, actual)
            # Failure after ALB write but before append also rolls back exactly.
            tools.run('dotnet', tools.REPLACE, pak, entry, replacement, a.sha(backup.read_bytes()))
            install.rollback(pak, entry, backup, a.sha(replacement.read_bytes()), index, tail, plan)
            self.assertEqual(pak.read_bytes(), original)

    def test_unrelated_index_drift_is_rejected(self):
        _, tail, count, _ = a.read_tail(io.BytesIO(fixture()))
        altered = tail[:-1]+bytes([tail[-1]^1])
        with self.assertRaises(ValueError): install.require_only_record_changed(tail, altered, 0)
        with self.assertRaises(ValueError): install.locate(tail, count, ['missing'])


if __name__ == '__main__': unittest.main()
