"""Real r575 sandbox save-directory patch tests; all writable paths are on E:."""

import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("sandbox_profile", REPO / "Scripts/PatchAa10SandboxProfile.py")
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)
TEST_ROOT = Path("E:/AAEmu/rama_10/artifacts/tests/sandbox-profile")


def native_child(dll_path, profile):
    search = os.add_dll_directory(str(PROFILE.PRIMARY / "Bin64"))
    library = ctypes.CDLL(str(dll_path))
    # The original folder query must not execute: record it and return an E-only
    # location even if a regression restores a Windows folder lookup.
    callbacks = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int,
                                      ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p)

    def folder_query(hwnd, csidl, token, flags, output):
        callbacks.append((csidl, flags))
        value = ctypes.create_unicode_buffer(str(TEST_ROOT / "unexpected-folder-query"))
        ctypes.memmove(output, value, ctypes.sizeof(value))
        return 0

    callback = callback_type(folder_query)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong,
                                     ctypes.POINTER(ctypes.c_ulong)]
    kernel.VirtualProtect.restype = ctypes.c_int
    slot = library._handle + 0x16BA00
    old = ctypes.c_ulong()
    assert kernel.VirtualProtect(slot, 8, 0x04, ctypes.byref(old))
    saved = ctypes.c_void_p.from_address(slot).value
    ctypes.c_void_p.from_address(slot).value = ctypes.cast(callback, ctypes.c_void_p).value
    unused = ctypes.c_ulong()
    assert kernel.VirtualProtect(slot, 8, old.value, ctypes.byref(unused))
    get_safe = getattr(library, PROFILE.EXPORT)
    get_safe.argtypes = [ctypes.c_void_p, ctypes.c_int]
    get_safe.restype = ctypes.c_bool
    units = len(profile.encode("utf-16-le")) // 2 + 1
    buffer = ctypes.create_unicode_buffer(units + 8)
    ctypes.memset(ctypes.addressof(buffer), 0x5A, ctypes.sizeof(buffer))
    assert get_safe(buffer, units)
    assert buffer.value == profile, repr(buffer.value)
    raw = bytes(buffer)
    assert raw[:units * 2] == profile.encode("utf-16-le") + b"\x00\x00"
    assert raw[units * 2:] == b"\x5A" * 16
    for count in (-1, 0, 1, units - 1):
        ctypes.memset(ctypes.addressof(buffer), 0x5A, ctypes.sizeof(buffer))
        before = bytes(buffer)
        assert not get_safe(buffer, count), count
        assert bytes(buffer) == before, count
    assert not get_safe(None, units)
    assert callbacks == [], callbacks
    assert kernel.VirtualProtect(slot, 8, 0x04, ctypes.byref(old))
    ctypes.c_void_p.from_address(slot).value = saved
    assert kernel.VirtualProtect(slot, 8, old.value, ctypes.byref(unused))
    print(json.dumps({"native_export": True, "unicode": True, "exact_buffer": True,
                      "small_negative_null_rejected": True, "windows_folder_calls": len(callbacks)}))
    search.close()


class SandboxProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        cls.source = PROFILE.DEFAULT_SOURCE.read_bytes()
        if PROFILE.sha256(cls.source) != PROFILE.SOURCE_SHA256:
            raise AssertionError("The canonical source has changed: re-anchor this patch first")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="case-", dir=TEST_ROOT)
        self.root = Path(self.temporary.name)
        (self.root / "Bin64").mkdir()
        self.dll = self.root / "Bin64/xlcommon.dll"
        self.dll.write_bytes(self.source)
        self.profile = str(self.root / "perfil-á-ñ-🙂/ArcheAge")
        Path(self.profile).mkdir(parents=True)

    def tearDown(self):
        self.temporary.cleanup()

    def test_deterministic_patch_with_only_original_function_changed(self):
        first, manifest = PROFILE.build_patch(self.source, self.profile)
        second, repeated = PROFILE.build_patch(self.source, self.profile)
        self.assertEqual(first, second)
        self.assertEqual(manifest, repeated)
        self.assertEqual(len(first), len(self.source))
        start = PROFILE.FUNCTION_OFFSET
        end = start + PROFILE.FUNCTION_END - PROFILE.FUNCTION_RVA
        self.assertEqual(first[:start + len(PROFILE.PROLOGUE)], self.source[:start + len(PROFILE.PROLOGUE)])
        self.assertEqual(first[end:], self.source[end:])
        self.assertEqual(manifest["function"]["span"], 496)
        self.assertEqual(manifest["function"]["relocations_in_patch"], 0)

    def test_native_export_unicode_exact_buffer_and_failure_branches(self):
        PROFILE.process(self.root, self.profile, "apply")
        env = dict(os.environ, TEMP=str(self.root), TMP=str(self.root), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()),
                                 "--native-check", str(self.dll), self.profile],
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["windows_folder_calls"], 0)

    def test_apply_repeat_and_rollback_preserve_primary(self):
        primary_before = PROFILE.sha256(PROFILE.DEFAULT_SOURCE.read_bytes())
        inspected = PROFILE.process(self.root, self.profile)
        self.assertEqual(inspected["state"], "original")
        self.assertFalse((self.root / ".aa10-sandbox-profile-backup").exists())
        first = PROFILE.process(self.root, self.profile, "apply")
        manifest_path = Path(first["manifest"])
        manifest_bytes, manifest_time = manifest_path.read_bytes(), manifest_path.stat().st_mtime_ns
        dll_time = self.dll.stat().st_mtime_ns
        repeated = PROFILE.process(self.root, self.profile, "apply")
        self.assertFalse(repeated["changed"])
        self.assertEqual(manifest_path.read_bytes(), manifest_bytes)
        self.assertEqual(manifest_path.stat().st_mtime_ns, manifest_time)
        self.assertEqual(self.dll.stat().st_mtime_ns, dll_time)
        PROFILE.process(self.root, self.profile, "rollback")
        self.assertEqual(self.dll.read_bytes(), self.source)
        self.assertFalse(PROFILE.process(self.root, self.profile, "rollback")["changed"])
        self.assertEqual(PROFILE.sha256(PROFILE.DEFAULT_SOURCE.read_bytes()), primary_before)

    def test_unknown_source_and_target_rejected_without_mutation(self):
        unknown = bytearray(self.source)
        unknown[-1] ^= 1
        with self.assertRaises(ValueError):
            PROFILE.build_patch(bytes(unknown), self.profile)
        self.dll.write_bytes(unknown)
        with self.assertRaises(ValueError):
            PROFILE.process(self.root, self.profile, "apply")
        self.assertEqual(self.dll.read_bytes(), bytes(unknown))
        self.assertFalse((self.root / ".aa10-sandbox-profile-backup").exists())

    def test_non_e_relative_and_oversized_profiles_rejected(self):
        for value in (r"C:\Users\test", r"profile", "E:\\", "E:\\" + "ñ" * 200,
                      "E:\\perfil\x00mal"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                PROFILE.build_patch(self.source, value)

    def test_primary_and_hardlink_targets_rejected(self):
        with self.assertRaises(ValueError):
            PROFILE.process(PROFILE.PRIMARY, self.profile, "apply")
        with self.assertRaises(ValueError):
            PROFILE.process(PROFILE.PRIMARY.parent / "unused/.." / PROFILE.PRIMARY.name,
                            self.profile, "apply")
        linked = self.root / "linked.dll"
        os.link(self.dll, linked)
        with self.assertRaises(ValueError):
            PROFILE.process(self.root, self.profile, "apply")
        self.assertEqual(self.dll.read_bytes(), self.source)

    def test_corrupt_backup_and_manifest_rejected(self):
        result = PROFILE.process(self.root, self.profile, "apply")
        patched = self.dll.read_bytes()
        backup = Path(result["backup"])
        backup.write_bytes(b"unknown")
        with self.assertRaises(ValueError):
            PROFILE.process(self.root, self.profile, "rollback")
        self.assertEqual(self.dll.read_bytes(), patched)
        backup.write_bytes(self.source)
        manifest = Path(result["manifest"])
        value = json.loads(manifest.read_bytes())
        value["profile_path"] = "E:\\otro"
        manifest.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(ValueError):
            PROFILE.process(self.root, self.profile, "apply")
        self.assertEqual(self.dll.read_bytes(), patched)

    def test_failed_manifest_write_restores_dll(self):
        original_write = PROFILE.atomic_write

        def write(path, data):
            if path.name == "manifest.json":
                raise OSError("simulated manifest failure")
            return original_write(path, data)

        with patch.object(PROFILE, "atomic_write", side_effect=write), self.assertRaises(OSError):
            PROFILE.process(self.root, self.profile, "apply")
        self.assertEqual(self.dll.read_bytes(), self.source)
        self.assertFalse((self.root / ".aa10-sandbox-profile-backup/manifest.json").exists())

    def test_marker_describes_native_hash_and_rejects_unknown_changes(self):
        result = PROFILE.process(self.root, self.profile, "apply")
        marker = Path(result["marker"])
        value = json.loads(marker.read_bytes())
        self.assertEqual(value["profilePath"], PROFILE.profile_value(self.profile))
        self.assertEqual(value["currentSha256"], hashlib.sha256(self.dll.read_bytes()).hexdigest())
        self.assertEqual(value["originalSha256"], PROFILE.SOURCE_SHA256)
        value["unreviewed"] = True
        marker.write_text(json.dumps(value), encoding="utf-8")
        before = self.dll.read_bytes()
        with self.assertRaises(ValueError):
            PROFILE.process(self.root, self.profile, "rollback")
        self.assertEqual(before, self.dll.read_bytes())

    def test_failed_marker_write_restores_dll_and_manifest(self):
        original_write = PROFILE.atomic_write

        def write(path, data):
            if path.name == ".aa10-sandbox-profile.json":
                raise OSError("simulated marker failure")
            return original_write(path, data)

        with patch.object(PROFILE, "atomic_write", side_effect=write), self.assertRaises(OSError):
            PROFILE.process(self.root, self.profile, "apply")
        self.assertEqual(self.dll.read_bytes(), self.source)
        self.assertFalse((self.root / ".aa10-sandbox-profile-backup/manifest.json").exists())
        self.assertFalse((self.root / ".aa10-sandbox-profile.json").exists())

    def test_concurrent_change_detected_before_publication_is_preserved(self):
        original_write = PROFILE.atomic_write
        changed = bytearray(self.source)
        changed[-1] ^= 1

        def write(path, data):
            original_write(path, data)
            if path.name == PROFILE.SOURCE_SHA256 + ".xlcommon.dll":
                self.dll.write_bytes(changed)

        with patch.object(PROFILE, "atomic_write", side_effect=write), self.assertRaises(ValueError):
            PROFILE.process(self.root, self.profile, "apply")
        self.assertEqual(self.dll.read_bytes(), bytes(changed))
        self.assertFalse((self.root / ".aa10-sandbox-profile.json").exists())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--native-check":
        native_child(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
