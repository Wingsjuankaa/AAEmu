from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from client_forensics.native_code import (
    NativeCodeConfig,
    PeImage,
    Stage15BuildTuning,
    Stage15Progress,
    _apply_review_overrides,
    _build_review_queue,
    _build_search,
    _ensure_engine_matrix,
    _import_reko,
    _load_review_overrides,
    _resume_manifest,
    _stage_15_build_activity,
    _stage_15_build_lock,
    _terminal_batch_manifest,
    _wave_targets,
    binary_key,
    build_stage_15,
    classify_binary,
    diff_native_architectures,
    export_native_anchor_dossiers,
    export_native_function,
    function_key,
    normalize_drcov_trace,
    register_dynamic_coverage,
    resolve_stage_15_tuning,
    validate_native_code_database,
)
from client_forensics.native_code_schema import create_native_code_tables
from client_forensics.schema import create_database


def _minimal_pe(*, x64: bool) -> bytes:
    pe_offset = 0x80
    optional_size = 0xF0 if x64 else 0xE0
    image = bytearray(0x400)
    image[:2] = b"MZ"
    struct.pack_into("<I", image, 0x3C, pe_offset)
    image[pe_offset : pe_offset + 4] = b"PE\0\0"
    machine = 0x8664 if x64 else 0x14C
    struct.pack_into(
        "<HHIIIHH",
        image,
        pe_offset + 4,
        machine,
        1,
        0x61B7E000,
        0,
        0,
        optional_size,
        0x210E,
    )
    optional = pe_offset + 24
    struct.pack_into("<H", image, optional, 0x20B if x64 else 0x10B)
    image[optional + 2] = 14
    image[optional + 3] = 35
    struct.pack_into("<I", image, optional + 16, 0x1000)
    if x64:
        struct.pack_into("<Q", image, optional + 24, 0x140000000)
        struct.pack_into("<I", image, optional + 108, 16)
    else:
        struct.pack_into("<I", image, optional + 28, 0x400000)
        struct.pack_into("<I", image, optional + 92, 16)
    struct.pack_into("<I", image, optional + 56, 0x2000)
    section = optional + optional_size
    image[section : section + 8] = b".text\0\0\0"
    struct.pack_into(
        "<IIIIIIHHI",
        image,
        section + 8,
        0x100,
        0x1000,
        0x200,
        0x200,
        0,
        0,
        0,
        0,
        0x60000020,
    )
    image[0x200:0x400] = bytes(range(256)) * 2
    return bytes(image)


class NativeCodeTests(unittest.TestCase):
    @staticmethod
    def _fixture_config(root: Path) -> NativeCodeConfig:
        return NativeCodeConfig(
            path=root / "config.json",
            client_build="fixture",
            client_root=root,
            output_root=root / "output",
            forensics_database=root / "forensics.sqlite",
            tool_manifest=root / "tools.json",
            batch_size=500,
            timeouts={},
            architectures={},
            classification={},
            required_engines={},
            tools={},
            ghidra_projects={},
            revng_image="fixture",
            policy={"cloud_uploads": False, "anticheat_analysis": False},
            config_sha256="fixture",
        )

    def test_pe32_and_pe32_plus_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for x64, expected_architecture, expected_base in (
                (False, "x86", 0x400000),
                (True, "x64", 0x140000000),
            ):
                path = Path(temporary) / f"fixture-{expected_architecture}.dll"
                path.write_bytes(_minimal_pe(x64=x64))
                image = PeImage(path)
                self.assertEqual(image.architecture, expected_architecture)
                self.assertEqual(image.image_base, expected_base)
                self.assertEqual(image.entry_rva, 0x1000)
                self.assertTrue(image.sections[0]["executable"])
                self.assertEqual(image.rva_offset(0x1000), 0x200)

    def test_function_identity_is_rva_based(self) -> None:
        digest = "AB" * 32
        binary = binary_key(digest, "x64")
        self.assertEqual(
            function_key(binary, 0x1234),
            f"fn:x64:{digest.lower()}:00001234",
        )
        self.assertNotIn("140001234", function_key(binary, 0x1234))

    def test_stage_15_max_profile_uses_declared_cpu_and_memory_budget(self) -> None:
        with (
            patch("client_forensics.native_code.os.cpu_count", return_value=32),
            patch(
                "client_forensics.native_code._physical_memory_mb",
                return_value=65536,
            ),
        ):
            tuning = resolve_stage_15_tuning(profile="max")
            self.assertEqual(tuning.workers, 30)
            self.assertEqual(tuning.memory_mb, 32768)
            self.assertEqual(tuning.sqlite_threads, 30)
            self.assertEqual(tuning.hash_workers, 8)
            self.assertEqual(tuning.cache_mb + tuning.mmap_mb, 32768)
            with self.assertRaisesRegex(ValueError, "leave at least"):
                resolve_stage_15_tuning(profile="max", memory_mb=65000)

    def test_stage_15_progress_is_persistent_and_detects_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir()
            tuning = Stage15BuildTuning(
                profile="max",
                workers=4,
                memory_mb=4096,
                hash_workers=4,
                sqlite_threads=4,
                cache_mb=2457,
                mmap_mb=1639,
            )
            progress = Stage15Progress(
                config.stage_build_progress,
                input_sha256="A" * 64,
                tuning=tuning,
                console=False,
            )
            progress.start_phase("preflight", total=10, detail="hashes")
            progress.update(5, force=True)
            payload = json.loads(
                config.stage_build_progress.read_text(encoding="utf-8")
            )
            self.assertEqual(payload["state"], "running")
            self.assertEqual(payload["phase_completed"], 5)
            self.assertGreater(payload["overall_percent"], 0)
            with patch(
                "client_forensics.native_code._pid_is_running",
                return_value=False,
            ):
                activity = _stage_15_build_activity(config)
            self.assertEqual(activity["reported_state"], "interrupted")
            self.assertFalse(activity["active"])

    def test_stage_15_lock_rejects_a_second_builder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir()
            with _stage_15_build_lock(config, input_sha256="A" * 64):
                self.assertTrue(
                    (config.output_root / ".stage-15-build.lock").is_file()
                )
                with self.assertRaisesRegex(RuntimeError, "already active"):
                    with _stage_15_build_lock(
                        config, input_sha256="A" * 64
                    ):
                        self.fail("second Stage 15 lock was acquired")
            self.assertFalse(
                (config.output_root / ".stage-15-build.lock").exists()
            )

    def test_review_queue_and_search_build_without_relation_multiplication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "stage.sqlite"
            connection = create_database(database)
            create_native_code_tables(connection)
            digest = hashlib.sha256(b"review-fixture").hexdigest().upper()
            binary = binary_key(digest, "x64")
            connection.execute(
                """
                INSERT INTO code_binaries(
                    binary_key,module_name,architecture,classification,
                    source_path,bytes,sha256,machine,image_base,entry_rva,
                    image_size,timestamp,linker_version,signed,pdb_path,
                    pdb_guid,pdb_age,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    binary,
                    "x2game.dll",
                    "x64",
                    "game_primary",
                    "fixture",
                    3,
                    digest,
                    0x8664,
                    0x140000000,
                    0x1000,
                    0x4000,
                    0,
                    "fixture",
                    0,
                    None,
                    None,
                    None,
                    "confirmed",
                    "{}",
                ),
            )
            functions = [
                function_key(binary, rva) for rva in (0x1000, 0x2000, 0x3000)
            ]
            for function, rva in zip(functions, (0x1000, 0x2000, 0x3000)):
                connection.execute(
                    """
                    INSERT INTO code_functions(
                        function_key,binary_key,entry_rva,end_rva,size,
                        discovery_engine,function_kind,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        function,
                        binary,
                        rva,
                        rva + 16,
                        16,
                        "ghidra",
                        "function",
                        "confirmed",
                        "{}",
                    ),
                )
            connection.executemany(
                """
                INSERT INTO code_engine_runs(
                    run_key,binary_key,engine_id,engine_version,engine_sha256,
                    scope,input_manifest_sha256,output_path,output_sha256,
                    timeout_seconds,exit_code,status,error,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    (
                        "run:confirmed",
                        binary,
                        "angr",
                        "fixture",
                        None,
                        "anchors",
                        "A" * 64,
                        "fixture",
                        None,
                        120,
                        0,
                        "confirmed",
                        None,
                        "{}",
                    ),
                    (
                        "run:failed",
                        binary,
                        "revng",
                        "fixture",
                        None,
                        "full",
                        "B" * 64,
                        "fixture",
                        None,
                        120,
                        1,
                        "failed",
                        "module failure",
                        "{}",
                    ),
                ),
            )
            connection.execute(
                """
                INSERT INTO code_decompilations(
                    decompilation_key,function_key,run_key,engine_id,
                    prototype,calling_convention,pseudocode,pseudocode_sha256,
                    duration_ms,status,error,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "decomp:not-scheduled",
                    functions[0],
                    "run:confirmed",
                    "angr",
                    None,
                    None,
                    None,
                    None,
                    None,
                    "not_scheduled",
                    None,
                    "{}",
                ),
            )
            connection.execute(
                """
                INSERT INTO code_calls(
                    call_key,caller_function_key,callee_function_key,
                    callsite_rva,target_rva,target_name,call_kind,state,
                    evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    "call:indirect",
                    functions[0],
                    None,
                    0x1004,
                    None,
                    None,
                    "indirect",
                    "candidate",
                    "{}",
                ),
            )
            connection.execute(
                """
                INSERT INTO code_evidence_links(
                    evidence_link_key,function_key,scope_key,relation,
                    source_locator,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    "evidence:consumer",
                    functions[0],
                    "consumer:fixture",
                    "consumer_function",
                    "fixture",
                    "confirmed",
                    "{}",
                ),
            )
            connection.execute(
                """
                INSERT INTO code_equivalences(
                    equivalence_key,left_function_key,right_function_key,
                    method,rank_score,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    "equivalence:fixture",
                    functions[0],
                    functions[1],
                    "fixture",
                    0.5,
                    "candidate",
                    "{}",
                ),
            )
            review_progress: list[tuple[int, int, str]] = []
            with self.assertRaisesRegex(
                RuntimeError, "simulated review interruption"
            ):
                _build_review_queue(
                    connection,
                    lambda completed, total, detail: (
                        review_progress.append((completed, total, detail)),
                        (_ for _ in ()).throw(
                            RuntimeError("simulated review interruption")
                        ),
                    )[1],
                    chunk_size=1,
                )
            checkpoint = json.loads(
                connection.execute(
                    """
                    SELECT value FROM metadata
                    WHERE key=?
                    """,
                    (f"stage15_review_checkpoint:{binary}",),
                ).fetchone()[0]
            )
            self.assertEqual(checkpoint["processed_functions"], 1)
            result = _build_review_queue(
                connection,
                lambda completed, total, detail: review_progress.append(
                    (completed, total, detail)
                ),
                chunk_size=1,
            )
            reasons = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT reason_code FROM code_review_queue
                    WHERE function_key=?
                    """,
                    (functions[0],),
                )
            }
            self.assertEqual(
                reasons,
                {
                    "anchor_missing_engine_vote",
                    "indirect_call_requires_resolution",
                    "architecture_equivalence_requires_review",
                },
            )
            self.assertEqual(result["failure_groups"], 1)
            self.assertEqual(
                connection.execute(
                    "SELECT affected_functions FROM code_review_groups"
                ).fetchone()[0],
                3,
            )
            self.assertTrue(review_progress)

            search_progress: list[tuple[int, int, str]] = []
            with self.assertRaisesRegex(
                RuntimeError, "simulated search interruption"
            ):
                _build_search(
                    connection,
                    lambda completed, total, detail: (
                        search_progress.append((completed, total, detail)),
                        (_ for _ in ()).throw(
                            RuntimeError("simulated search interruption")
                        ),
                    )[1],
                    chunk_size=1,
                )
            search_checkpoint = json.loads(
                connection.execute(
                    """
                    SELECT value FROM metadata
                    WHERE key=?
                    """,
                    (f"stage15_search_checkpoint:{binary}",),
                ).fetchone()[0]
            )
            self.assertEqual(search_checkpoint["processed_functions"], 1)
            self.assertEqual(
                _build_search(
                    connection,
                    lambda completed, total, detail: search_progress.append(
                        (completed, total, detail)
                    ),
                    chunk_size=1,
                ),
                3,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM code_search WHERE code_search MATCH 'x2game'"
                ).fetchone()[0],
                3,
            )
            self.assertEqual(search_progress[-1][:2], (3, 3))
            connection.close()

    def test_stage_15_progress_retries_transient_windows_replace_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tuning = Stage15BuildTuning(
                profile="balanced",
                workers=2,
                memory_mb=1024,
                hash_workers=2,
                sqlite_threads=2,
                cache_mb=614,
                mmap_mb=410,
            )
            progress = Stage15Progress(
                root / "progress.json",
                input_sha256="A" * 64,
                tuning=tuning,
                console=False,
            )
            with patch(
                "client_forensics.native_code.atomic_text",
                side_effect=(
                    PermissionError("reader temporarily holds destination"),
                    PermissionError("reader temporarily holds destination"),
                    None,
                ),
            ) as writer:
                progress.update(1, total=2, force=True)
            self.assertEqual(writer.call_count, 3)

    def test_minimal_stage_15_build_is_reproducible_and_publishes_progress(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir()
            inventory = {
                "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
                "client_build": "fixture",
                "config_sha256": "fixture",
                "binaries": [],
                "summary": {},
            }
            config.inventory_path.write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            config.anchors_path.write_text(
                json.dumps({"anchors": []}), encoding="utf-8"
            )
            patches = (
                patch(
                    "client_forensics.native_code._load_inventory",
                    return_value=inventory,
                ),
                patch(
                    "client_forensics.native_code._engine_manifests",
                    return_value=[],
                ),
                patch(
                    "client_forensics.native_code._native_processes",
                    return_value=[],
                ),
                patch(
                    "client_forensics.native_code._apply_review_overrides",
                    return_value={
                        "names": 0,
                        "equivalences": 0,
                        "boundaries": 0,
                        "types": 0,
                        "indirect_dispatch": 0,
                        "decisions": 0,
                    },
                ),
            )
            for current in patches:
                current.start()
            try:
                first = build_stage_15(
                    config,
                    workers=2,
                    memory_mb=1024,
                    console_progress=False,
                )
                first_sha256 = first["database"]["sha256"]
                second = build_stage_15(
                    config,
                    workers=2,
                    memory_mb=1024,
                    console_progress=False,
                )
            finally:
                for current in reversed(patches):
                    current.stop()

            self.assertEqual(first_sha256, second["database"]["sha256"])
            self.assertTrue(config.stage_database.is_file())
            self.assertFalse(
                list(config.output_root.glob(".stage-15-native-code.work-*.sqlite"))
            )
            progress = json.loads(
                config.stage_build_progress.read_text(encoding="utf-8")
            )
            self.assertEqual(progress["state"], "confirmed")
            self.assertEqual(progress["overall_percent"], 100.0)

    def test_stage_15_resumes_committed_phases_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir()
            inventory = {
                "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
                "client_build": "fixture",
                "config_sha256": "fixture",
                "binaries": [],
                "summary": {},
            }
            config.inventory_path.write_text(
                json.dumps(inventory), encoding="utf-8"
            )
            config.anchors_path.write_text(
                json.dumps({"anchors": []}), encoding="utf-8"
            )
            base_patches = (
                patch(
                    "client_forensics.native_code._load_inventory",
                    return_value=inventory,
                ),
                patch(
                    "client_forensics.native_code._engine_manifests",
                    return_value=[],
                ),
                patch(
                    "client_forensics.native_code._native_processes",
                    return_value=[],
                ),
                patch(
                    "client_forensics.native_code._apply_review_overrides",
                    return_value={
                        "names": 0,
                        "equivalences": 0,
                        "boundaries": 0,
                        "types": 0,
                        "indirect_dispatch": 0,
                        "decisions": 0,
                    },
                ),
            )
            for current in base_patches:
                current.start()
            try:
                with patch(
                    "client_forensics.native_code._build_equivalences",
                    side_effect=RuntimeError("simulated interruption"),
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "simulated interruption"
                    ):
                        build_stage_15(
                            config,
                            workers=2,
                            memory_mb=1024,
                            console_progress=False,
                        )
                self.assertTrue(
                    list(
                        config.output_root.glob(
                            ".stage-15-native-code.work-*.sqlite"
                        )
                    )
                )
                with patch(
                    "client_forensics.native_code._insert_inventory",
                    side_effect=AssertionError(
                        "inventory checkpoint was unexpectedly repeated"
                    ),
                ):
                    result = build_stage_15(
                        config,
                        workers=2,
                        memory_mb=1024,
                        console_progress=False,
                    )
            finally:
                for current in reversed(base_patches):
                    current.stop()

            self.assertEqual(result["validation"]["quick_check"], "ok")
            self.assertFalse(
                list(config.output_root.glob(".stage-15-native-code.work-*.sqlite"))
            )

    def test_classification_excludes_anticheat_before_other_rules(self) -> None:
        config = NativeCodeConfig(
            path=Path("config.json"),
            client_build="fixture",
            client_root=Path("."),
            output_root=Path("."),
            forensics_database=Path("forensics.sqlite"),
            tool_manifest=Path("tools.json"),
            batch_size=500,
            timeouts={},
            architectures={},
            classification={
                "excluded_anticheat": ("mrac*.dll",),
                "game_primary": ("x2game.dll",),
                "game_support": ("*.dll",),
                "engine_modified": ("cry*.dll",),
            },
            required_engines={},
            tools={},
            ghidra_projects={},
            revng_image="fixture",
            policy={
                "cloud_uploads": False,
                "anticheat_analysis": False,
            },
            config_sha256="fixture",
        )
        self.assertEqual(classify_binary(config, "mrac64.dll"), "excluded_anticheat")
        self.assertEqual(classify_binary(config, "x2game.dll"), "game_primary")
        self.assertEqual(classify_binary(config, "cryaction.dll"), "game_support")

    def test_native_schema_supports_fts_and_policy_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stage-15.sqlite"
            connection = create_database(path)
            create_native_code_tables(connection)
            digest = hashlib.sha256(b"fixture").hexdigest().upper()
            binary = binary_key(digest, "x64")
            function = function_key(binary, 0x1000)
            connection.execute(
                """
                INSERT INTO code_binaries(
                    binary_key,module_name,architecture,classification,source_path,
                    bytes,sha256,machine,image_base,entry_rva,image_size,timestamp,
                    linker_version,signed,pdb_path,pdb_guid,pdb_age,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    binary,
                    "x2game.dll",
                    "x64",
                    "third_party",
                    "fixture",
                    7,
                    digest,
                    0x8664,
                    0x39000000,
                    0x1000,
                    0x2000,
                    0,
                    "14.35",
                    0,
                    None,
                    None,
                    None,
                    "confirmed",
                    "{}",
                ),
            )
            connection.execute(
                """
                INSERT INTO code_functions(
                    function_key,binary_key,entry_rva,end_rva,size,byte_sha256,
                    mnemonic_sha256,discovery_engine,function_kind,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    function,
                    binary,
                    0x1000,
                    0x1010,
                    16,
                    digest,
                    digest,
                    "ghidra",
                    "function",
                    "confirmed",
                    "{}",
                ),
            )
            connection.execute(
                """
                INSERT INTO code_search(
                    function_key,module_name,architecture,primary_name,strings,pseudocode
                ) VALUES(?,?,?,?,?,?)
                """,
                (function, "x2game.dll", "x64", "LoadSkills", "SELECT id", "return 1;"),
            )
            connection.commit()
            self.assertEqual(
                connection.execute(
                    "SELECT function_key FROM code_search WHERE code_search MATCH 'LoadSkills'"
                ).fetchone()[0],
                function,
            )
            connection.close()
            result = validate_native_code_database(path)
            self.assertEqual(result["quick_check"], "ok")
            self.assertEqual(result["anticheat_engine_runs"], 0)

    def test_schema_rejects_anticheat_engine_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "stage-15.sqlite"
            connection = create_database(path)
            create_native_code_tables(connection)
            digest = "CD" * 32
            binary = binary_key(digest, "x64")
            connection.execute(
                """
                INSERT INTO code_binaries(
                    binary_key,module_name,architecture,classification,source_path,
                    bytes,sha256,machine,image_base,entry_rva,image_size,timestamp,
                    linker_version,signed,pdb_path,pdb_guid,pdb_age,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    binary,
                    "mrac64.dll",
                    "x64",
                    "excluded_anticheat",
                    "fixture",
                    1,
                    digest,
                    0x8664,
                    0,
                    0,
                    1,
                    0,
                    "0.0",
                    0,
                    None,
                    None,
                    None,
                    "confirmed",
                    "{}",
                ),
            )
            connection.execute(
                """
                INSERT INTO code_engine_runs(
                    run_key,binary_key,engine_id,engine_version,engine_sha256,scope,
                    input_manifest_sha256,output_path,output_sha256,timeout_seconds,
                    exit_code,status,error,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    "run:fixture",
                    binary,
                    "ghidra",
                    "fixture",
                    None,
                    "full",
                    digest,
                    "",
                    None,
                    1,
                    0,
                    "confirmed",
                    None,
                    "{}",
                ),
            )
            connection.commit()
            connection.close()
            with self.assertRaises(RuntimeError):
                validate_native_code_database(path)

    def test_dynamic_coverage_rejects_public_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "coverage.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_COVERAGE_V1",
                        "client_build": "fixture",
                        "network_scope": "public",
                        "anticheat_state": "not_running",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                register_dynamic_coverage(self._fixture_config(root), manifest)

    def test_review_overlay_requires_evidence_and_exact_function_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            digest = hashlib.sha256(b"review-fixture").hexdigest().upper()
            binary = binary_key(digest, "x64")
            function = function_key(binary, 0x1234)
            database = create_database(root / "review.sqlite")
            create_native_code_tables(database)
            database.execute(
                """
                INSERT INTO code_binaries(
                    binary_key,module_name,architecture,classification,source_path,
                    bytes,sha256,machine,image_base,entry_rva,image_size,timestamp,
                    linker_version,signed,pdb_path,pdb_guid,pdb_age,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    binary, "x2game.dll", "x64", "game_primary", "fixture", 1,
                    digest, 0x8664, 0, 0, 0x2000, 0, "0.0", 0, None, None,
                    None, "confirmed", "{}",
                ),
            )
            database.execute(
                """
                INSERT INTO code_functions(
                    function_key,binary_key,entry_rva,end_rva,size,byte_sha256,
                    mnemonic_sha256,discovery_engine,function_kind,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    function, binary, 0x1234, 0x1240, 12, digest, digest,
                    "ghidra", "function", "confirmed", "{}",
                ),
            )
            overlay = root / "review.json"
            overlay.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_REVIEW_OVERRIDES_V1",
                        "client_build": "fixture",
                        "decisions": [
                            {
                                "decision_id": "fixture-name",
                                "kind": "name",
                                "function": {
                                    "binary_sha256": digest,
                                    "architecture": "x64",
                                    "rva": "0x1234",
                                },
                                "state": "corroborated",
                                "source_locator": "test",
                                "payload": {"name": "ReviewedName"},
                                "evidence": ["fixture evidence"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "client_forensics.native_code.NATIVE_CODE_REVIEW_OVERRIDES",
                overlay,
            ):
                self.assertEqual(len(_load_review_overrides(config)["decisions"]), 1)
                self.assertEqual(
                    _apply_review_overrides(database, config)["names"], 1
                )
            database.close()

    def test_wave_targets_and_terminal_resume_validate_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir(parents=True)
            digest = hashlib.sha256(b"wave-fixture").hexdigest().upper()
            binary = binary_key(digest, "x64")
            config.inventory_path.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
                        "client_build": "fixture",
                        "config_sha256": "fixture",
                        "binaries": [
                            {
                                "binary_key": binary,
                                "module_name": "crygame.dll",
                                "architecture": "x64",
                                "classification": "engine_modified",
                                "sha256": digest,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            waves = root / "waves.json"
            waves.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_WAVES_V1",
                        "client_build": "fixture",
                        "waves": [
                            {
                                "id": "fixture",
                                "engines": ["ghidra", "rizin"],
                                "binaries": [
                                    {
                                        "module": "crygame.dll",
                                        "architectures": ["x64"],
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with patch("client_forensics.native_code.NATIVE_CODE_WAVES", waves):
                target = _wave_targets(config, "fixture", ["ghidra"])[0]
            manifest_path = (
                config.raw_root
                / "ghidra"
                / f"crygame.dll-x64-{digest[:12]}"
                / "full"
                / "run.manifest.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest = {
                "client_build": "fixture",
                "inventory_sha256": hashlib.sha256(
                    config.inventory_path.read_bytes()
                ).hexdigest().upper(),
                "binary": {
                    "binary_key": binary,
                    "sha256": digest,
                    "architecture": "x64",
                },
                "engine": {"id": "ghidra"},
                "status": "failed",
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(
                _terminal_batch_manifest(config, target)["status"], "failed"
            )
            manifest["binary"]["sha256"] = "00" * 32
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                _terminal_batch_manifest(config, target)
            output = manifest_path.parent / "functions.json"
            output.write_text("[]", encoding="utf-8")
            manifest["binary"]["sha256"] = digest
            manifest["status"] = "confirmed"
            manifest["outputs"] = [
                {
                    "path": output.resolve().as_posix(),
                    "bytes": output.stat().st_size,
                    "sha256": hashlib.sha256(output.read_bytes())
                    .hexdigest()
                    .upper(),
                },
                {
                    "path": manifest_path.resolve().as_posix(),
                    "bytes": 1,
                    "sha256": "00" * 32,
                },
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            audit = _terminal_batch_manifest(
                config, target, verify_outputs=True
            )["_output_audit"]
            self.assertEqual(audit["hashes_verified"], 1)
            self.assertEqual(audit["self_references_ignored"], 1)
            output.write_text("[1]", encoding="utf-8")
            with self.assertRaises(ValueError):
                _terminal_batch_manifest(
                    config, target, verify_outputs=True
                )

    def test_direct_resume_preserves_failed_and_timeout_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir(parents=True)
            config.inventory_path.write_text("{}", encoding="utf-8")
            inventory_sha256 = hashlib.sha256(b"{}").hexdigest().upper()
            digest = hashlib.sha256(b"resume").hexdigest().upper()
            selected = {
                "binary_key": binary_key(digest, "x64"),
                "architecture": "x64",
                "sha256": digest,
            }
            for status in ("failed", "timeout"):
                manifest_path = config.output_root / status / "run.manifest.json"
                manifest_path.parent.mkdir(parents=True)
                manifest_path.write_text(
                    json.dumps(
                        {
                            "schema": "AA8_NATIVE_CODE_ENGINE_RUN_V1",
                            "client_build": config.client_build,
                            "config_sha256": config.config_sha256,
                            "inventory_sha256": inventory_sha256,
                            "binary": selected,
                            "engine": {"id": "reko"},
                            "status": status,
                            "outputs": [],
                        }
                    ),
                    encoding="utf-8",
                )
                resumed = _resume_manifest(
                    config, manifest_path, selected, "reko"
                )
                self.assertEqual(resumed["status"], status)
                self.assertEqual(
                    json.loads(manifest_path.read_text(encoding="utf-8"))[
                        "status"
                    ],
                    status,
                )

    def test_reko_crashes_and_unmapped_results_have_explicit_states(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = self._fixture_config(root)
            config = NativeCodeConfig(
                **{
                    **base.__dict__,
                    "required_engines": {"game_primary": ("reko",)},
                }
            )
            config.output_root.mkdir(parents=True)
            config.inventory_path.write_text("{}", encoding="utf-8")
            digest = hashlib.sha256(b"reko-crash").hexdigest().upper()
            binary = binary_key(digest, "x64")
            database = create_database(root / "stage.sqlite")
            create_native_code_tables(database)
            database.execute(
                """
                INSERT INTO code_binaries(
                    binary_key,module_name,architecture,classification,
                    source_path,bytes,sha256,machine,image_base,entry_rva,
                    image_size,timestamp,linker_version,signed,pdb_path,
                    pdb_guid,pdb_age,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    binary,
                    "x2game.dll",
                    "x64",
                    "game_primary",
                    "fixture",
                    1,
                    digest,
                    0x8664,
                    0x39000000,
                    0x1000,
                    0x01000000,
                    0,
                    "fixture",
                    0,
                    None,
                    None,
                    None,
                    "confirmed",
                    "{}",
                ),
            )
            run_key = "run:reko"
            database.execute(
                """
                INSERT INTO code_engine_runs(
                    run_key,binary_key,engine_id,engine_version,engine_sha256,
                    scope,input_manifest_sha256,output_path,output_sha256,
                    timeout_seconds,exit_code,status,error,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    run_key,
                    binary,
                    "reko",
                    "fixture",
                    None,
                    "full",
                    "fixture",
                    "fixture",
                    None,
                    1,
                    0,
                    "confirmed",
                    None,
                    "{}",
                ),
            )
            crash = config.output_root / "analysis_99_crash.txt"
            crash.write_text(
                "\ufeff// fn0000000039003F10 ===========\n"
                "Object reference not set to an instance of an object.\n"
                "   at Reko.Analysis.Worker()\n",
                encoding="utf-8",
            )
            imported = _import_reko(
                database,
                {
                    binary: {
                        "binary_key": binary,
                        "image_base": 0x39000000,
                        "image_size": 0x01000000,
                    }
                },
                {
                    "binary": {"binary_key": binary},
                    "outputs": [{"path": crash.as_posix()}],
                },
                run_key,
            )
            self.assertEqual(imported, 1)
            failed = database.execute(
                """
                SELECT status,error FROM code_decompilations
                WHERE engine_id='reko'
                """
            ).fetchone()
            self.assertEqual(failed["status"], "failed")
            self.assertIn("Object reference", failed["error"])

            second_function = function_key(binary, 0x5000)
            database.execute(
                """
                INSERT INTO code_functions(
                    function_key,binary_key,entry_rva,end_rva,size,
                    discovery_engine,function_kind,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    second_function,
                    binary,
                    0x5000,
                    0x5001,
                    1,
                    "ghidra",
                    "function",
                    "confirmed",
                    "{}",
                ),
            )
            _ensure_engine_matrix(
                database,
                config,
                {
                    binary: {
                        "binary_key": binary,
                        "classification": "game_primary",
                    }
                },
            )
            opaque = database.execute(
                """
                SELECT status,error,evidence_json FROM code_decompilations
                WHERE function_key=? AND engine_id='reko'
                """,
                (second_function,),
            ).fetchone()
            self.assertEqual(opaque["status"], "opaque")
            self.assertIn("completed", opaque["error"])
            self.assertTrue(
                json.loads(opaque["evidence_json"])["whole_module_vote"]
            )
            database.close()

    def test_repository_review_overlay_covers_chat_and_all_candidates(self) -> None:
        root = Path(__file__).resolve().parents[2]
        payload = json.loads(
            (root / "config" / "native-code-review-overrides.json").read_text(
                encoding="utf-8"
            )
        )
        chat = [
            item
            for item in payload["decisions"]
            if item["decision_id"].startswith("chat-bubble-")
        ]
        self.assertEqual(len(chat), 4)
        self.assertEqual(
            {item["kind"] for item in chat},
            {"name", "indirect_dispatch"},
        )
        self.assertTrue(all(item["evidence"] for item in chat))
        review_set = payload["equivalence_review_sets"][0]
        self.assertEqual(len(review_set["pairs"]), 42)
        identities = {
            (
                pair["function"]["binary_sha256"],
                pair["function"]["architecture"],
                pair["function"]["rva"],
                pair["related_function"]["binary_sha256"],
                pair["related_function"]["architecture"],
                pair["related_function"]["rva"],
            )
            for pair in review_set["pairs"]
        }
        self.assertEqual(len(identities), 42)

    def test_repository_waves_cover_declared_run_counts(self) -> None:
        root = Path(__file__).resolve().parents[2]
        payload = json.loads(
            (root / "config" / "native-code-waves.json").read_text(
                encoding="utf-8"
            )
        )
        counts = {}
        for wave in payload["waves"]:
            binaries = sum(
                len(item["architectures"]) for item in wave["binaries"]
            )
            counts[wave["id"]] = binaries * len(wave["engines"])
        self.assertEqual(
            counts,
            {
                "gameplay-1": 26,
                "engine-core-2": 16,
                "xl-support-3": 20,
                "presentation-4": 32,
            },
        )

    def test_repository_dynamic_scenarios_are_guarded_and_complete(self) -> None:
        root = Path(__file__).resolve().parents[2]
        payload = json.loads(
            (root / "config" / "native-coverage-scenarios.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            payload["schema"], "AA8_NATIVE_COVERAGE_SCENARIOS_V1"
        )
        self.assertTrue(payload["collection_gate"]["static_waves_terminal"])
        self.assertTrue(payload["collection_gate"]["stage_15_validated"])
        self.assertFalse(payload["safety"]["public_network"])
        self.assertEqual(
            payload["safety"]["anticheat_state"], "not_running"
        )
        self.assertEqual(
            [item["id"] for item in payload["scenarios"]],
            [
                "startup",
                "character_selection",
                "world_load",
                "npc_interaction",
                "quest_interaction",
                "item_interaction",
                "skill_interaction",
            ],
        )

    def test_function_dossiers_keep_module_architecture_and_rva(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir(parents=True)
            digest = hashlib.sha256(b"dossier-fixture").hexdigest().upper()
            binary = binary_key(digest, "x64")
            config.inventory_path.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
                        "client_build": config.client_build,
                        "config_sha256": config.config_sha256,
                        "binaries": [
                            {
                                "binary_key": binary,
                                "module_name": "x2game.dll",
                                "architecture": "x64",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            connection = create_database(config.stage_database)
            create_native_code_tables(connection)
            connection.execute(
                """
                INSERT INTO code_binaries(
                    binary_key,module_name,architecture,classification,source_path,
                    bytes,sha256,machine,image_base,entry_rva,image_size,timestamp,
                    linker_version,signed,pdb_path,pdb_guid,pdb_age,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    binary,
                    "x2game.dll",
                    "x64",
                    "game_primary",
                    "fixture",
                    1,
                    digest,
                    0x8664,
                    0x140000000,
                    0x1000,
                    0x3000,
                    0,
                    "14.35",
                    0,
                    None,
                    None,
                    None,
                    "confirmed",
                    "{}",
                ),
            )
            for rva in (0x1000, 0x2000):
                connection.execute(
                    """
                    INSERT INTO code_functions(
                        function_key,binary_key,entry_rva,end_rva,size,
                        discovery_engine,function_kind,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        function_key(binary, rva),
                        binary,
                        rva,
                        rva + 1,
                        1,
                        "ghidra",
                        "function",
                        "confirmed",
                        "{}",
                    ),
                )
            connection.commit()
            connection.close()

            first = export_native_function(
                config, "x2game.dll", 0x1000, architecture="x64"
            )
            second = export_native_function(
                config, "x2game.dll", 0x2000, architecture="x64"
            )
            self.assertNotEqual(first["json"]["path"], second["json"]["path"])
            self.assertTrue(first["json"]["path"].endswith("x2game.dll-x64-00001000.json"))
            self.assertTrue(second["html"]["path"].endswith("x2game.dll-x64-00002000.html"))
            config.anchors_path.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_ANCHORS_V1",
                        "client_build": config.client_build,
                        "anchors": [
                            {
                                "binary_key": binary,
                                "architecture": "x64",
                                "entry_rva": rva,
                                "locators": [],
                            }
                            for rva in (0x1000, 0x2000)
                        ],
                    }
                ),
                encoding="utf-8",
            )
            batch = export_native_anchor_dossiers(config)
            self.assertEqual(batch["anchors"]["count"], 2)
            self.assertEqual(len(batch["dossiers"]), 2)
            self.assertEqual(
                len({item["function_key"] for item in batch["dossiers"]}), 2
            )
            self.assertTrue(Path(batch["manifest"]["path"]).is_file())
            for item in batch["dossiers"]:
                document = json.loads(
                    Path(item["json"]["path"]).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    document["database_sha256"],
                    batch["database"]["sha256"],
                )

    def test_architecture_diff_does_not_duplicate_multi_source_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = self._fixture_config(Path(temporary))
            config.output_root.mkdir(parents=True)
            connection = create_database(config.stage_database)
            create_native_code_tables(connection)
            functions = []
            for architecture, machine, seed in (
                ("x86", 0x14C, b"x86"),
                ("x64", 0x8664, b"x64"),
            ):
                digest = hashlib.sha256(seed).hexdigest().upper()
                binary = binary_key(digest, architecture)
                function = function_key(binary, 0x1000)
                functions.append(function)
                connection.execute(
                    """
                    INSERT INTO code_binaries(
                        binary_key,module_name,architecture,classification,
                        source_path,bytes,sha256,machine,image_base,entry_rva,
                        image_size,timestamp,linker_version,signed,pdb_path,
                        pdb_guid,pdb_age,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        binary,
                        "x2game.dll",
                        architecture,
                        "game_primary",
                        architecture,
                        1,
                        digest,
                        machine,
                        0,
                        0x1000,
                        0x2000,
                        0,
                        "fixture",
                        0,
                        None,
                        None,
                        None,
                        "confirmed",
                        "{}",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO code_functions(
                        function_key,binary_key,entry_rva,end_rva,size,
                        discovery_engine,function_kind,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        function,
                        binary,
                        0x1000,
                        0x1001,
                        1,
                        "ghidra",
                        "function",
                        "confirmed",
                        "{}",
                    ),
                )
                for index, name in enumerate(("native_name", "forensic_name")):
                    connection.execute(
                        """
                        INSERT INTO code_names(
                            name_key,function_key,name,namespace,source_kind,
                            source_locator,primary_name,state,evidence_json
                        ) VALUES(?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            f"name:{architecture}:{index}",
                            function,
                            name,
                            None,
                            "fixture",
                            str(index),
                            1,
                            "confirmed" if index == 0 else "corroborated",
                            "{}",
                        ),
                    )
            connection.execute(
                """
                INSERT INTO code_equivalences(
                    equivalence_key,left_function_key,right_function_key,
                    method,rank_score,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    "equivalence:fixture",
                    functions[0],
                    functions[1],
                    "fixture",
                    1.0,
                    "confirmed",
                    "{}",
                ),
            )
            connection.commit()
            connection.close()
            result = diff_native_architectures(config)
            self.assertEqual(len(result["equivalences"]), 1)
            self.assertEqual(result["equivalences"][0]["left_name"], "native_name")

    def test_normalize_drcov_trace_maps_rvas_and_duplicate_hits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir(parents=True)
            digest = hashlib.sha256(b"x2game-x64").hexdigest().upper()
            binary = binary_key(digest, "x64")
            config.inventory_path.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
                        "client_build": "fixture",
                        "config_sha256": "fixture",
                        "binaries": [
                            {
                                "binary_key": binary,
                                "module_name": "x2game.dll",
                                "architecture": "x64",
                                "classification": "game_primary",
                                "analysis_enabled": True,
                                "sha256": digest,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            trace = root / "scenario.log"
            header = (
                "DRCOV VERSION: 2\n"
                "DRCOV FLAVOR: drcov\n"
                "Module Table: version 2, count 1\n"
                "Columns: id, base, end, entry, checksum, timestamp, path\n"
                "0, 0x140000000, 0x140002000, 0x0, 0x0, 0x0, "
                "C:\\AA8\\x2game.dll\n"
                "BB Table: 3 bbs\n"
            ).encode("utf-8")
            trace.write_bytes(
                header
                + struct.pack("<IHH", 0x1000, 5, 0)
                + struct.pack("<IHH", 0x1000, 5, 0)
                + struct.pack("<IHH", 0x1010, 4, 0)
            )
            output = root / "coverage.json"

            result = normalize_drcov_trace(
                config,
                trace,
                scenario="startup",
                architecture="x64",
                output_path=output,
            )

            self.assertEqual(result["modules"], 1)
            self.assertEqual(result["basic_blocks"], 2)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["network_scope"], "offline")
            self.assertEqual(payload["anticheat_state"], "not_running")
            self.assertEqual(
                payload["modules"][0]["hits"],
                [
                    {"hit_count": 2, "rva": "0x1000"},
                    {"hit_count": 1, "rva": "0x1010"},
                ],
            )
            registered = register_dynamic_coverage(config, output)
            self.assertEqual(registered["modules"], 1)
            self.assertEqual(registered["hits"], 2)

    def test_normalize_drcov_trace_rejects_anticheat_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._fixture_config(root)
            config.output_root.mkdir(parents=True)
            digest = hashlib.sha256(b"anticheat").hexdigest().upper()
            config.inventory_path.write_text(
                json.dumps(
                    {
                        "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
                        "client_build": "fixture",
                        "config_sha256": "fixture",
                        "binaries": [
                            {
                                "binary_key": binary_key(digest, "x64"),
                                "module_name": "mrac64.dll",
                                "architecture": "x64",
                                "classification": "excluded_anticheat",
                                "analysis_enabled": False,
                                "sha256": digest,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            trace = root / "forbidden.log"
            trace.write_bytes(
                (
                    "DRCOV VERSION: 2\n"
                    "DRCOV FLAVOR: drcov\n"
                    "Module Table: version 2, count 1\n"
                    "Columns: id, base, end, entry, checksum, timestamp, path\n"
                    "0, 0x180000000, 0x180001000, 0x0, 0x0, 0x0, "
                    "C:\\AA8\\mrac64.dll\n"
                    "BB Table: 1 bbs\n"
                ).encode("utf-8")
                + struct.pack("<IHH", 0x100, 4, 0)
            )

            with self.assertRaisesRegex(ValueError, "Anticheat"):
                normalize_drcov_trace(
                    config,
                    trace,
                    scenario="startup",
                    architecture="x64",
                    output_path=root / "coverage.json",
                )


if __name__ == "__main__":
    unittest.main()
