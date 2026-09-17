"""Windows integration checks against the exact r575 native DLL, in isolated directories."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path('E:/AAEmu/rama_10')
BIN = ROOT/'client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview/Bin64'
PACKAGE = ROOT/'artifacts/client-distribution/local-profile-20260916/AA10-Perfil-local-20260916-r2'
BEFORE = 'd81ba53e5df0dc6b5031d3d423a6a2720288d6ca40be0768aae85e2f30ea4113'
AFTER = '513cbce7c62c734b504adeb0bf7bb7e52feac74166ec67b131a322be4bd8e565'
CODE = bytes.fromhex('6a014159488d8424d00400004533c06a055a33c94889442420')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def original_dll():
    data = bytearray((BIN/'xlcommon.dll').read_bytes())
    data[0x1b121:0x1b13a] = bytes.fromhex('4533c9488d8424d00400004533c0418d510533c94889442420')
    assert hashlib.sha256(data).hexdigest() == BEFORE
    return data

def native_child(dll_path, sandbox, expected_flags):
    """Mock only SHGetFolderPathW's OS response; execute native query/append/create/junction code."""
    sandbox = Path(sandbox)
    default = sandbox/'usuario-á'/'Documents'
    redirected = sandbox/'OneDrive'/'Documentos'
    default.mkdir(parents=True)
    redirected.mkdir(parents=True)
    search = os.add_dll_directory(str(BIN))
    lib = ctypes.CDLL(dll_path)
    set_product = getattr(lib, '?XlSetProduct@@YAXPEBD@Z')
    set_product.argtypes = [ctypes.c_char_p]
    set_product.restype = None
    set_product(b'ArcheAge')
    seen = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int,
                                      ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)
    def get_folder(hwnd, csidl, token, flags, output):
        seen.append((csidl, flags))
        value = str(default if flags == 1 else redirected)
        data = ctypes.create_unicode_buffer(value)
        ctypes.memmove(output, data, ctypes.sizeof(data))
        return 0
    callback = callback_type(get_folder)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong,
                                     ctypes.POINTER(ctypes.c_ulong)]
    kernel.VirtualProtect.restype = ctypes.c_int
    slot = lib._handle + 0x16ba00
    old = ctypes.c_ulong()
    assert kernel.VirtualProtect(slot, 8, 0x04, ctypes.byref(old))
    saved = ctypes.c_void_p.from_address(slot).value
    ctypes.c_void_p.from_address(slot).value = ctypes.cast(callback, ctypes.c_void_p).value
    unused = ctypes.c_ulong()
    assert kernel.VirtualProtect(slot, 8, old.value, ctypes.byref(unused))
    get_safe = getattr(lib, '?XlGetSafeSaveGameDir@@YA_NPEAGH@Z')
    get_safe.argtypes = [ctypes.c_wchar_p, ctypes.c_int]
    get_safe.restype = ctypes.c_bool
    output = ctypes.create_unicode_buffer(260)
    assert get_safe(output, 260)
    expected = (default if expected_flags == 1 else redirected)/'ArcheAge'
    assert Path(output.value).resolve() == expected.resolve(), output.value
    assert expected.is_dir()
    assert seen == [(5, expected_flags)], seen
    # Existing client alias must retarget without touching the old directory's contents.
    junction = sandbox/'DocumentsAlias'
    old_target = redirected/'OldArcheAge'
    old_target.mkdir()
    marker = old_target/'preserve.txt'
    marker.write_text('preserve')
    make_junction = getattr(lib, '?XlCreateJunction@@YA_NPEBDPEBG@Z')
    make_junction.argtypes = [ctypes.c_char_p, ctypes.c_wchar_p]
    make_junction.restype = ctypes.c_bool
    # ASCII junction path; Unicode destination is handled by the native wide API.
    assert make_junction(str(junction).encode('ascii'), str(old_target))
    assert make_junction(str(junction).encode('ascii'), str(expected))
    assert junction.resolve() == expected.resolve()
    assert marker.read_text() == 'preserve'
    os.rmdir(junction)  # unlink only the sandbox junction, never recurse into its destination
    assert kernel.VirtualProtect(slot, 8, 0x04, ctypes.byref(old))
    ctypes.c_void_p.from_address(slot).value = saved
    kernel.VirtualProtect(slot, 8, old.value, ctypes.byref(unused))
    print(json.dumps({'native_flags': seen, 'unicode_path': True, 'junction_retarget': True}))
    search.close()

class LocalProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aa10-profile-')
        self.root = Path(self.temp.name)
        (self.root/'Bin64').mkdir()
        shutil.copyfile(BIN/'archeage.exe', self.root/'Bin64/archeage.exe')
        self.dll = self.root/'Bin64/xlcommon.dll'
        self.dll.write_bytes(original_dll())

    def tearDown(self):
        self.temp.cleanup()

    def run_patch(self, mode, success=True):
        env = {k:v for k,v in os.environ.items() if k.upper() != 'PSMODULEPATH'}
        result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
            '-File',str(PACKAGE/'Perfil-local.ps1'),'-ClientRoot',str(self.root),
            '-Mode',mode,'-SkipProfileInitialization'], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_apply_repeat_verify_manifest_and_rollback(self):
        self.run_patch('Inspect')
        self.assertFalse((self.root/'.aa10-local-profile-backup').exists())
        self.run_patch('Apply')
        self.assertEqual(digest(self.dll), AFTER)
        manifest = self.root/'MANIFEST-SHA256.json'
        data = json.loads(manifest.read_text(encoding='utf-8-sig'))
        row = next(x for x in data['files'] if x['path'] == 'Bin64/xlcommon.dll')
        self.assertEqual(row['sha256'].lower(), AFTER)
        first = manifest.read_bytes()
        self.run_patch('Apply')
        self.assertEqual(manifest.read_bytes(), first)
        self.assertEqual(digest(self.dll), AFTER)
        self.run_patch('Rollback')
        self.assertEqual(digest(self.dll), BEFORE)
        self.assertEqual(manifest.read_bytes(), (PACKAGE/'MANIFEST-SHA256.original.json').read_bytes())
        self.run_patch('Rollback')

    def test_unknown_dll_rejected_without_mutation(self):
        data = bytearray(self.dll.read_bytes()); data[-1] ^= 1
        self.dll.write_bytes(data)
        self.run_patch('Apply', False)
        self.assertEqual(self.dll.read_bytes(), data)
        self.assertFalse((self.root/'.aa10-local-profile-backup').exists())

    def test_file_entrypoint_uses_script_directory_without_clientroot(self):
        # Match the shipped CMD's powershell.exe -File entrypoint (PS 5.1).
        # -Command and explicit -ClientRoot do not expose the parameter-default bug.
        for source in PACKAGE.iterdir():
            if source.is_file():
                shutil.copyfile(source, self.root/source.name)
        env = {k:v for k,v in os.environ.items() if k.upper() != 'PSMODULEPATH'}
        result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
            '-File',str(self.root/'Perfil-local.ps1'),'-Mode','Inspect'],
            cwd=str(PACKAGE), capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Perfil local:', result.stdout)
        self.assertEqual(digest(self.dll), BEFORE)
        self.assertFalse((self.root/'.aa10-local-profile-backup').exists())

    def test_shipped_cmd_apply_and_restore_from_other_working_directory(self):
        for source in PACKAGE.iterdir():
            if source.is_file():
                shutil.copyfile(source, self.root/source.name)
        # Keep the real CMD entrypoints and default ClientRoot; skip only personal
        # profile writes in this isolated install/rollback test.
        script = self.root/'Perfil-local.ps1'
        script.write_text(script.read_text().replace(
            '[switch]$SkipProfileInitialization,',
            '[switch]$SkipProfileInitialization = $true,'))
        for name, expected in [('Activar perfil local.cmd', AFTER),
                               ('Restaurar perfil original.cmd', BEFORE)]:
            result = subprocess.run(['cmd.exe','/d','/c',str(self.root/name)],
                cwd=str(PACKAGE), input='\n', capture_output=True, text=True)
            self.assertIn('OK:', result.stdout, result.stdout + result.stderr)
            self.assertEqual(digest(self.dll), expected)

    def test_unknown_manifest_rejected_without_mutation(self):
        (self.root/'MANIFEST-SHA256.json').write_text('{}')
        self.run_patch('Apply', False)
        self.assertEqual(digest(self.dll), BEFORE)

    def test_manifest_write_failure_restores_dll(self):
        # Fail the second write after DLL replacement, without damaging any existing file.
        target = self.root/'MANIFEST-SHA256.json'
        target.mkdir()
        (target/'preserve.txt').write_text('preserve')
        self.run_patch('Apply', False)
        self.assertEqual(digest(self.dll), BEFORE)
        self.assertEqual((target/'preserve.txt').read_text(), 'preserve')

    def test_native_original_uses_redirected_documents(self):
        self.check_native(0)

    def test_native_patch_uses_default_documents_and_retargets_alias(self):
        data = bytearray(self.dll.read_bytes()); data[0x1b121:0x1b13a] = CODE
        self.dll.write_bytes(data)
        self.check_native(1)

    def check_native(self, flags):
        result = subprocess.run([sys.executable,__file__,'native',str(self.dll),
            str(self.root/'native'),str(flags)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='native':
        native_child(sys.argv[2],sys.argv[3],int(sys.argv[4]))
    else:
        unittest.main()
