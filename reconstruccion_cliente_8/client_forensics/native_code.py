from __future__ import annotations

import fnmatch
import hashlib
import csv
import json
import math
import os
import re
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, quote, unquote, urlparse

from . import SCHEMA_VERSION, TOOL_NAME, TOOL_VERSION
from .native_code_schema import NATIVE_CODE_STATES, create_native_code_tables
from .schema import create_database, open_read_only
from .util import atomic_text, canonical_json, sha256_file, sha256_text, stable_key


NATIVE_CODE_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "native-code-corpus.json"
)
NATIVE_CODE_WAVES = (
    Path(__file__).resolve().parents[1] / "config" / "native-code-waves.json"
)
NATIVE_CODE_REVIEW_OVERRIDES = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "native-code-review-overrides.json"
)
NATIVE_CODE_FORMAT = "AA8_NATIVE_CODE_CORPUS_V1"
_TERMINAL_RUN_STATES = {"confirmed", "failed", "timeout", "unsupported"}
_FUNCTION_LOCATOR = re.compile(r"\b(?:FUN_|0x)?([0-9a-fA-F]{6,16})\b")
_DEFAULT_NAME = re.compile(r"^(?:FUN|SUB|THUNK)_[0-9A-Fa-f]+$")
_SQL_TOKEN = re.compile(
    r"\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|FROM|WHERE|JOIN)\b",
    re.IGNORECASE,
)
_THIS_OFFSET = re.compile(
    r"\b(?:this|this_[A-Za-z0-9_]*|param_1)\s*\+\s*(0x[0-9a-fA-F]+|\d+)"
)


@dataclass(frozen=True)
class NativeCodeConfig:
    path: Path
    client_build: str
    client_root: Path
    output_root: Path
    forensics_database: Path
    tool_manifest: Path
    batch_size: int
    timeouts: dict[str, int]
    architectures: dict[str, str]
    classification: dict[str, tuple[str, ...]]
    required_engines: dict[str, tuple[str, ...]]
    tools: dict[str, str]
    ghidra_projects: dict[str, dict[str, str]]
    revng_image: str
    policy: dict[str, Any]
    config_sha256: str

    @property
    def inventory_path(self) -> Path:
        return self.output_root / "inventory.json"

    @property
    def inventory_manifest(self) -> Path:
        return self.output_root / "inventory.manifest.json"

    @property
    def raw_root(self) -> Path:
        return self.output_root / "raw"

    @property
    def anchors_path(self) -> Path:
        return self.output_root / "anchors.json"

    @property
    def stage_database(self) -> Path:
        return self.output_root / "stage-15-native-code.sqlite"

    @property
    def stage_manifest(self) -> Path:
        return self.output_root / "stage-15-native-code.manifest.json"

    @property
    def dossier_root(self) -> Path:
        return self.output_root / "dossiers"

    @property
    def dynamic_root(self) -> Path:
        return self.raw_root / "dynamic"

    @property
    def waves_path(self) -> Path:
        return NATIVE_CODE_WAVES

    @property
    def review_overrides_path(self) -> Path:
        return NATIVE_CODE_REVIEW_OVERRIDES

    @property
    def batch_root(self) -> Path:
        return self.output_root / "batches"

    @property
    def stage_build_progress(self) -> Path:
        return self.output_root / "stage-15-build-progress.json"


@dataclass(frozen=True)
class Stage15BuildTuning:
    profile: str
    workers: int
    memory_mb: int
    hash_workers: int
    sqlite_threads: int
    cache_mb: int
    mmap_mb: int


_STAGE15_PHASES: tuple[tuple[str, float], ...] = (
    ("preflight", 4.0),
    ("initialize", 2.0),
    ("inventory", 3.0),
    ("engine_imports", 36.0),
    ("native_enrichment", 4.0),
    ("call_resolution", 3.0),
    ("executable_regions", 8.0),
    ("coverage_and_engine_matrix", 5.0),
    ("architecture_equivalences", 5.0),
    ("review_overlay", 2.0),
    ("review_queue", 8.0),
    ("search_index", 12.0),
    ("coverage_records", 2.0),
    ("compact", 4.0),
    ("validate", 1.5),
    ("hash_and_publish", 0.5),
)


def _physical_memory_mb() -> int:
    if os.name == "nt":
        try:
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong),
                    ("memory_load", ctypes.c_ulong),
                    ("total_physical", ctypes.c_ulonglong),
                    ("available_physical", ctypes.c_ulonglong),
                    ("total_page_file", ctypes.c_ulonglong),
                    ("available_page_file", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong),
                    ("available_virtual", ctypes.c_ulonglong),
                    ("available_extended_virtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatus()
            status.length = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return max(1024, int(status.total_physical // (1024 * 1024)))
        except (AttributeError, OSError):
            pass
    try:
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        return max(1024, pages * page_size // (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        return 8192


def resolve_stage_15_tuning(
    *,
    profile: str = "balanced",
    workers: int | None = None,
    memory_mb: int | None = None,
) -> Stage15BuildTuning:
    if profile not in {"balanced", "max"}:
        raise ValueError(f"Unsupported Stage 15 performance profile: {profile}")
    logical = max(1, os.cpu_count() or 1)
    total_memory = _physical_memory_mb()
    if workers is None:
        workers = (
            max(1, logical - 2)
            if profile == "max"
            else max(1, min(8, logical - 1))
        )
    if memory_mb is None:
        memory_mb = (
            min(32768, max(4096, total_memory // 2))
            if profile == "max"
            else min(8192, max(2048, total_memory // 4))
        )
    workers = int(workers)
    memory_mb = int(memory_mb)
    if workers < 1 or workers > logical:
        raise ValueError(
            f"Stage 15 workers must be between 1 and {logical}: {workers}"
        )
    if memory_mb < 512 or memory_mb > max(512, total_memory - 2048):
        raise ValueError(
            "Stage 15 memory budget must leave at least 2048 MiB for Windows: "
            f"requested={memory_mb} total={total_memory}"
        )
    cache_mb = max(256, memory_mb * 3 // 5)
    mmap_mb = max(256, memory_mb - cache_mb)
    return Stage15BuildTuning(
        profile=profile,
        workers=workers,
        memory_mb=memory_mb,
        hash_workers=max(1, min(workers, 8)),
        sqlite_threads=workers,
        cache_mb=cache_mb,
        mmap_mb=mmap_mb,
    )


class Stage15Progress:
    def __init__(
        self,
        path: Path,
        *,
        input_sha256: str,
        tuning: Stage15BuildTuning,
        console: bool,
        heartbeat_seconds: float = 0.0,
    ) -> None:
        self.path = path
        self.input_sha256 = input_sha256
        self.tuning = tuning
        self.console = console
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.phase = ""
        self.phase_index = 0
        self.phase_completed = 0
        self.phase_total: int | None = None
        self.detail = ""
        self.state = "running"
        self.error: str | None = None
        self.temporary_database: str | None = None
        self.completed_phases: set[str] = set()
        self._last_write = 0.0
        self._last_console_length = 0
        self._lock = threading.Lock()
        self._heartbeat_seconds = max(0.0, float(heartbeat_seconds))
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._write(force=True)
        if self._heartbeat_seconds:
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name="stage15-progress-heartbeat",
                daemon=True,
            )
            self._heartbeat_thread.start()

    def _heartbeat_loop(self) -> None:
        while not self._heartbeat_stop.wait(self._heartbeat_seconds):
            self._write(force=True)

    def _stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        thread = self._heartbeat_thread
        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=min(1.0, self._heartbeat_seconds))

    def _phase_weight(self, name: str) -> float:
        return dict(_STAGE15_PHASES)[name]

    def _percent(self) -> float:
        total_weight = sum(weight for _, weight in _STAGE15_PHASES)
        completed_weight = sum(
            self._phase_weight(name) for name in self.completed_phases
        )
        current_weight = 0.0
        if self.phase and self.phase not in self.completed_phases:
            if self.phase_total:
                current_weight = self._phase_weight(self.phase) * min(
                    1.0, self.phase_completed / self.phase_total
                )
        return round(100.0 * (completed_weight + current_weight) / total_weight, 2)

    def payload(self) -> dict[str, Any]:
        elapsed = max(
            0.0,
            time.time()
            - datetime.fromisoformat(self.started_at).timestamp(),
        )
        database_bytes = None
        if self.temporary_database:
            candidate = Path(self.temporary_database)
            if candidate.is_file():
                database_bytes = candidate.stat().st_size
        return {
            "schema": "AA8_STAGE15_BUILD_PROGRESS_V1",
            "state": self.state,
            "pid": os.getpid(),
            "started_at_utc": self.started_at,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed, 3),
            "input_sha256": self.input_sha256,
            "phase": self.phase,
            "phase_index": self.phase_index,
            "phase_count": len(_STAGE15_PHASES),
            "phase_completed": self.phase_completed,
            "phase_total": self.phase_total,
            "overall_percent": self._percent(),
            "detail": self.detail,
            "completed_phases": sorted(self.completed_phases),
            "temporary_database": self.temporary_database,
            "temporary_database_bytes": database_bytes,
            "tuning": {
                "profile": self.tuning.profile,
                "workers": self.tuning.workers,
                "memory_mb": self.tuning.memory_mb,
                "hash_workers": self.tuning.hash_workers,
                "sqlite_threads": self.tuning.sqlite_threads,
                "cache_mb": self.tuning.cache_mb,
                "mmap_mb": self.tuning.mmap_mb,
            },
            "error": self.error,
        }

    def _render_console(self, payload: dict[str, Any]) -> None:
        if not self.console:
            return
        percent = float(payload["overall_percent"])
        filled = min(30, int(percent * 30 / 100))
        bar = "#" * filled + "-" * (30 - filled)
        item = ""
        if self.phase_total:
            item = f" {self.phase_completed}/{self.phase_total}"
        line = (
            f"\r[{bar}] {percent:6.2f}% {self.phase}{item} "
            f"{self.detail}".rstrip()
        )
        padding = " " * max(0, self._last_console_length - len(line))
        sys.stderr.write(line + padding)
        sys.stderr.flush()
        self._last_console_length = len(line)

    def _write(self, *, force: bool = False) -> None:
        with self._lock:
            now = time.monotonic()
            if not force and now - self._last_write < 0.5:
                return
            payload = self.payload()
            for attempt in range(10):
                try:
                    atomic_text(
                        self.path, canonical_json(payload, pretty=True)
                    )
                    break
                except PermissionError:
                    if attempt == 9:
                        raise
                    time.sleep(0.025 * (attempt + 1))
            self._render_console(payload)
            self._last_write = now

    def set_temporary_database(self, path: Path) -> None:
        self.temporary_database = path.resolve().as_posix()
        self._write(force=True)

    def start_phase(
        self, name: str, *, total: int | None = None, detail: str = ""
    ) -> None:
        names = [phase for phase, _ in _STAGE15_PHASES]
        self.phase = name
        self.phase_index = names.index(name) + 1
        self.phase_completed = 0
        self.phase_total = total
        self.detail = detail
        self._write(force=True)

    def update(
        self,
        completed: int | None = None,
        *,
        total: int | None = None,
        detail: str | None = None,
        force: bool = False,
    ) -> None:
        if completed is not None:
            self.phase_completed = completed
        if total is not None:
            self.phase_total = total
        if detail is not None:
            self.detail = detail
        self._write(force=force)

    def complete_phase(self, name: str, *, detail: str = "") -> None:
        if self.phase_total is not None:
            self.phase_completed = self.phase_total
        self.detail = detail
        self.completed_phases.add(name)
        self._write(force=True)

    def complete(self, *, detail: str = "") -> None:
        self._stop_heartbeat()
        self.completed_phases = {name for name, _ in _STAGE15_PHASES}
        self.state = "confirmed"
        self.detail = detail
        self._write(force=True)
        if self.console:
            sys.stderr.write("\n")
            sys.stderr.flush()

    def fail(self, error: BaseException) -> None:
        self._stop_heartbeat()
        self.state = "failed"
        self.error = f"{type(error).__name__}: {error}"
        self._write(force=True)
        if self.console:
            sys.stderr.write("\n")
            sys.stderr.flush()


def load_native_code_config(path: Path | None = None) -> NativeCodeConfig:
    resolved = (path or NATIVE_CODE_CONFIG).resolve()
    raw = json.loads(resolved.read_text(encoding="utf-8"))
    if raw.get("schema") != "AA8_NATIVE_CODE_CONFIG_V1":
        raise ValueError("Unsupported native-code configuration schema")

    def as_path(value: str) -> Path:
        candidate = Path(value)
        return (
            candidate if candidate.is_absolute() else resolved.parent / candidate
        ).resolve()

    policy = dict(raw["policy"])
    if policy.get("cloud_uploads") is not False:
        raise ValueError("Native-code policy must forbid cloud uploads")
    if policy.get("anticheat_analysis") is not False:
        raise ValueError("Native-code policy must forbid anticheat analysis")
    return NativeCodeConfig(
        path=resolved,
        client_build=str(raw["client_build"]),
        client_root=as_path(raw["client_root"]),
        output_root=as_path(raw["output_root"]),
        forensics_database=as_path(raw["forensics_database"]),
        tool_manifest=as_path(raw["tool_manifest"]),
        batch_size=int(raw["batch_size"]),
        timeouts={str(k): int(v) for k, v in raw["timeouts"].items()},
        architectures={str(k): str(v) for k, v in raw["architectures"].items()},
        classification={
            str(k): tuple(str(item).lower() for item in values)
            for k, values in raw["classification"].items()
        },
        required_engines={
            str(k): tuple(str(item) for item in values)
            for k, values in raw["required_engines"].items()
        },
        tools={str(k): str(v) for k, v in raw["tools"].items()},
        ghidra_projects={
            str(k): {str(a): str(b) for a, b in value.items()}
            for k, value in raw["ghidra_projects"].items()
        },
        revng_image=str(raw["revng_image"]),
        policy=policy,
        config_sha256=sha256_file(resolved),
    )


def _load_native_waves(config: NativeCodeConfig) -> dict[str, Any]:
    path = config.waves_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "AA8_NATIVE_CODE_WAVES_V1":
        raise ValueError("Unsupported native-code wave configuration")
    if payload.get("client_build") != config.client_build:
        raise ValueError("Native-code waves belong to another client build")
    return payload


def _load_review_overrides(config: NativeCodeConfig) -> dict[str, Any]:
    path = config.review_overrides_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "AA8_NATIVE_CODE_REVIEW_OVERRIDES_V1":
        raise ValueError("Unsupported native-code review overlay")
    if payload.get("client_build") != config.client_build:
        raise ValueError("Native-code review overlay belongs to another client build")
    if not isinstance(payload.get("decisions"), list):
        raise ValueError("Native-code review overlay decisions must be a list")
    decisions = list(payload["decisions"])
    for review_set in payload.get("equivalence_review_sets", []):
        if not isinstance(review_set.get("pairs"), list):
            raise ValueError("Equivalence review set pairs must be a list")
        for index, pair in enumerate(review_set["pairs"], 1):
            decisions.append(
                {
                    "decision_id": (
                        f"{review_set['id']}-{index:02d}"
                    ),
                    "kind": "equivalence",
                    "function": pair["function"],
                    "related_function": pair["related_function"],
                    "state": review_set["state"],
                    "source_locator": review_set["source_locator"],
                    "payload": {
                        **review_set.get("payload", {}),
                        "mnemonic_sha256": pair["mnemonic_sha256"],
                    },
                    "evidence": [
                        *review_set["evidence"],
                        (
                            "unique_normalized_mnemonic_hash:"
                            + pair["mnemonic_sha256"]
                        ),
                    ],
                }
            )
    payload["decisions"] = decisions
    return payload


def _read_c_string(data: bytes, offset: int, maximum: int = 32768) -> str:
    if offset < 0 or offset >= len(data):
        return ""
    end = data.find(b"\0", offset, min(len(data), offset + maximum))
    if end < 0:
        end = min(len(data), offset + maximum)
    return data[offset:end].decode("utf-8", errors="replace")


def _entropy(value: bytes) -> float:
    if not value:
        return 0.0
    counts = [0] * 256
    for byte in value:
        counts[byte] += 1
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts
        if count
    )


class PeImage:
    """Minimal, deterministic PE32/PE32+ reader for evidence inventory."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.data = self.path.read_bytes()
        if len(self.data) < 0x100 or self.data[:2] != b"MZ":
            raise ValueError(f"Not a PE image: {self.path}")
        pe_offset = struct.unpack_from("<I", self.data, 0x3C)[0]
        if self.data[pe_offset : pe_offset + 4] != b"PE\0\0":
            raise ValueError(f"Invalid PE signature: {self.path}")
        (
            self.machine,
            self.section_count,
            self.timestamp,
            _,
            _,
            optional_size,
            self.characteristics,
        ) = struct.unpack_from("<HHIIIHH", self.data, pe_offset + 4)
        optional = pe_offset + 24
        self.optional_magic = struct.unpack_from("<H", self.data, optional)[0]
        if self.optional_magic == 0x20B:
            self.architecture = "x64"
            self.bits = 64
            self.image_base = struct.unpack_from("<Q", self.data, optional + 24)[0]
            directory_offset = optional + 112
            number_offset = optional + 108
            self.thunk_size = 8
        elif self.optional_magic == 0x10B:
            self.architecture = "x86"
            self.bits = 32
            self.image_base = struct.unpack_from("<I", self.data, optional + 28)[0]
            directory_offset = optional + 96
            number_offset = optional + 92
            self.thunk_size = 4
        else:
            raise ValueError(
                f"Unsupported PE optional header 0x{self.optional_magic:X}: {path}"
            )
        self.linker_version = (
            f"{self.data[optional + 2]}.{self.data[optional + 3]}"
        )
        self.entry_rva = struct.unpack_from("<I", self.data, optional + 16)[0]
        self.image_size = struct.unpack_from("<I", self.data, optional + 56)[0]
        count = min(struct.unpack_from("<I", self.data, number_offset)[0], 16)
        self.directories: list[tuple[int, int]] = []
        for index in range(count):
            self.directories.append(
                struct.unpack_from("<II", self.data, directory_offset + index * 8)
            )
        while len(self.directories) < 16:
            self.directories.append((0, 0))
        section_offset = optional + optional_size
        self.sections: list[dict[str, Any]] = []
        for ordinal in range(self.section_count):
            offset = section_offset + ordinal * 40
            name = self.data[offset : offset + 8].rstrip(b"\0").decode(
                "ascii", errors="replace"
            )
            (
                virtual_size,
                rva,
                raw_size,
                raw_offset,
                _,
                _,
                _,
                _,
                flags,
            ) = struct.unpack_from("<IIIIIIHHI", self.data, offset + 8)
            raw = self.data[raw_offset : raw_offset + raw_size]
            self.sections.append(
                {
                    "ordinal": ordinal,
                    "name": name,
                    "rva": rva,
                    "virtual_size": virtual_size,
                    "raw_offset": raw_offset,
                    "raw_size": raw_size,
                    "characteristics": flags,
                    "executable": bool(flags & 0x20000000),
                    "entropy": round(_entropy(raw), 8),
                    "sha256": hashlib.sha256(raw).hexdigest().upper(),
                }
            )

    def rva_offset(self, rva: int) -> int | None:
        for section in self.sections:
            start = int(section["rva"])
            span = max(
                int(section["virtual_size"]),
                int(section["raw_size"]),
            )
            if start <= rva < start + span:
                offset = int(section["raw_offset"]) + (rva - start)
                return offset if offset < len(self.data) else None
        return rva if 0 <= rva < len(self.data) else None

    def imports(self) -> list[dict[str, Any]]:
        directory_rva, _ = self.directories[1]
        offset = self.rva_offset(directory_rva) if directory_rva else None
        if offset is None:
            return []
        result: list[dict[str, Any]] = []
        descriptor = 0
        while offset + descriptor * 20 + 20 <= len(self.data):
            values = struct.unpack_from("<IIIII", self.data, offset + descriptor * 20)
            if not any(values):
                break
            original_thunk, _, _, name_rva, first_thunk = values
            name_offset = self.rva_offset(name_rva)
            library = (
                _read_c_string(self.data, name_offset).lower()
                if name_offset is not None
                else ""
            )
            thunk_rva = original_thunk or first_thunk
            thunk_offset = self.rva_offset(thunk_rva)
            if thunk_offset is not None:
                index = 0
                mask = (1 << (self.thunk_size * 8 - 1))
                fmt = "<Q" if self.thunk_size == 8 else "<I"
                while thunk_offset + (index + 1) * self.thunk_size <= len(self.data):
                    value = struct.unpack_from(
                        fmt,
                        self.data,
                        thunk_offset + index * self.thunk_size,
                    )[0]
                    if value == 0:
                        break
                    symbol = None
                    ordinal = None
                    if value & mask:
                        ordinal = value & 0xFFFF
                    else:
                        hint_name = self.rva_offset(int(value))
                        if hint_name is not None:
                            symbol = _read_c_string(self.data, hint_name + 2)
                    result.append(
                        {
                            "library": library,
                            "symbol": symbol,
                            "ordinal": ordinal,
                            "iat_rva": first_thunk + index * self.thunk_size,
                        }
                    )
                    index += 1
                    if index > 100000:
                        break
            descriptor += 1
            if descriptor > 4096:
                break
        return result

    def exports(self) -> list[dict[str, Any]]:
        directory_rva, _ = self.directories[0]
        offset = self.rva_offset(directory_rva) if directory_rva else None
        if offset is None or offset + 40 > len(self.data):
            return []
        values = struct.unpack_from("<IIHHIIIIIII", self.data, offset)
        base = values[5]
        function_count = values[6]
        name_count = values[7]
        functions_offset = self.rva_offset(values[8])
        names_offset = self.rva_offset(values[9])
        ordinals_offset = self.rva_offset(values[10])
        if functions_offset is None:
            return []
        names: dict[int, str] = {}
        if names_offset is not None and ordinals_offset is not None:
            for index in range(min(name_count, 100000)):
                name_rva = struct.unpack_from(
                    "<I", self.data, names_offset + index * 4
                )[0]
                ordinal_index = struct.unpack_from(
                    "<H", self.data, ordinals_offset + index * 2
                )[0]
                name_offset = self.rva_offset(name_rva)
                if name_offset is not None:
                    names[ordinal_index] = _read_c_string(self.data, name_offset)
        result: list[dict[str, Any]] = []
        export_start, export_size = self.directories[0]
        for index in range(min(function_count, 100000)):
            rva = struct.unpack_from(
                "<I", self.data, functions_offset + index * 4
            )[0]
            forwarded = None
            if export_start <= rva < export_start + export_size:
                forward_offset = self.rva_offset(rva)
                if forward_offset is not None:
                    forwarded = _read_c_string(self.data, forward_offset)
            result.append(
                {
                    "symbol": names.get(index),
                    "ordinal": base + index,
                    "rva": rva,
                    "forwarded_to": forwarded,
                }
            )
        return result

    def codeview(self) -> dict[str, Any] | None:
        directory_rva, directory_size = self.directories[6]
        offset = self.rva_offset(directory_rva) if directory_rva else None
        if offset is None:
            return None
        for cursor in range(offset, offset + directory_size, 28):
            if cursor + 28 > len(self.data):
                break
            values = struct.unpack_from("<IIHHIIII", self.data, cursor)
            debug_type, size, raw_pointer = values[4], values[5], values[7]
            if debug_type != 2 or size < 24 or raw_pointer + size > len(self.data):
                continue
            payload = self.data[raw_pointer : raw_pointer + size]
            if payload[:4] != b"RSDS":
                continue
            guid = uuid.UUID(bytes_le=payload[4:20]).hex.upper()
            age = struct.unpack_from("<I", payload, 20)[0]
            return {
                "pdb_path": _read_c_string(payload, 24),
                "pdb_guid": guid,
                "pdb_age": age,
                "pdb_signature": f"{guid}{age:X}",
            }
        return None

    def inventory(self) -> dict[str, Any]:
        codeview = self.codeview() or {}
        security_rva, security_size = self.directories[4]
        return {
            "architecture": self.architecture,
            "bits": self.bits,
            "machine": self.machine,
            "timestamp": self.timestamp,
            "linker_version": self.linker_version,
            "image_base": self.image_base,
            "entry_rva": self.entry_rva,
            "image_size": self.image_size,
            "characteristics": self.characteristics,
            "signed": bool(security_rva and security_size),
            **codeview,
            "sections": self.sections,
            "imports": self.imports(),
            "exports": self.exports(),
        }


def _matches(name: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(name.lower(), pattern) for pattern in patterns)


def classify_binary(config: NativeCodeConfig, name: str) -> str:
    order = (
        "excluded_anticheat",
        "game_primary",
        "game_support",
        "engine_modified",
    )
    for classification in order:
        if _matches(name, config.classification.get(classification, ())):
            return classification
    return "third_party"


def binary_key(sha256: str, architecture: str) -> str:
    return f"pe:{architecture}:{sha256.lower()}"


def function_key(binary: str, entry_rva: int) -> str:
    return f"fn:{binary.split(':', 2)[1]}:{binary.rsplit(':', 1)[1]}:{entry_rva:08x}"


def inventory_native_code(config: NativeCodeConfig) -> dict[str, Any]:
    if not config.client_root.is_dir():
        raise FileNotFoundError(config.client_root)
    by_key: dict[str, dict[str, Any]] = {}
    source_files = 0
    priority = {
        "excluded_anticheat": 0,
        "game_primary": 1,
        "game_support": 2,
        "engine_modified": 3,
        "third_party": 4,
    }
    for directory_architecture, directory in sorted(config.architectures.items()):
        root = config.client_root / directory
        if not root.is_dir():
            raise FileNotFoundError(root)
        for path in sorted(root.iterdir(), key=lambda value: value.name.lower()):
            if not path.is_file() or path.suffix.lower() not in {".dll", ".exe"}:
                continue
            source_files += 1
            classification = classify_binary(config, path.name)
            pe = PeImage(path)
            architecture = pe.architecture
            if architecture != directory_architecture:
                architecture_state = "ambiguous"
            else:
                architecture_state = "confirmed"
            digest = sha256_file(path)
            details = pe.inventory()
            key = binary_key(digest, architecture)
            alias = {
                "module_name": path.name,
                "source_path": path.as_posix(),
                "directory_architecture": directory_architecture,
                "architecture_state": architecture_state,
                "classification": classification,
            }
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = {
                    "binary_key": key,
                    "module_name": path.name,
                    "architecture": architecture,
                    "classification": classification,
                    "analysis_enabled": classification
                    in {"game_primary", "game_support", "engine_modified"},
                    "source_path": path.as_posix(),
                    "source_aliases": [alias],
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                    "architecture_state": architecture_state,
                    **details,
                }
                continue
            existing["source_aliases"].append(alias)
            if priority[classification] < priority[existing["classification"]]:
                existing["module_name"] = path.name
                existing["source_path"] = path.as_posix()
                existing["classification"] = classification
            existing["analysis_enabled"] = bool(
                existing["analysis_enabled"]
                or classification in {"game_primary", "game_support", "engine_modified"}
            )
            if architecture_state == "confirmed":
                existing["architecture_state"] = "confirmed"
    binaries = sorted(
        by_key.values(),
        key=lambda value: (value["architecture"], value["module_name"].lower()),
    )
    payload = {
        "schema": "AA8_NATIVE_CODE_INVENTORY_V1",
        "client_build": config.client_build,
        "config_sha256": config.config_sha256,
        "policy": {
            "cloud_uploads": False,
            "anticheat_analysis": False,
            "third_party_full_decompilation": False,
        },
        "binaries": binaries,
        "summary": {
            "binaries": len(binaries),
            "source_files": source_files,
            "deduplicated_aliases": source_files - len(binaries),
            "analysis_enabled": sum(item["analysis_enabled"] for item in binaries),
            "excluded_anticheat": sum(
                item["classification"] == "excluded_anticheat" for item in binaries
            ),
            "third_party": sum(
                item["classification"] == "third_party" for item in binaries
            ),
            "bytes": sum(int(item["bytes"]) for item in binaries),
        },
    }
    atomic_text(config.inventory_path, canonical_json(payload, pretty=True))
    manifest = {
        "schema": "AA8_NATIVE_CODE_INVENTORY_MANIFEST_V1",
        "client_build": config.client_build,
        "config": {
            "path": config.path.as_posix(),
            "sha256": config.config_sha256,
        },
        "inventory": {
            "path": config.inventory_path.as_posix(),
            "bytes": config.inventory_path.stat().st_size,
            "sha256": sha256_file(config.inventory_path),
        },
        "source_root": config.client_root.as_posix(),
        "summary": payload["summary"],
        "determinism": {
            "stable_ordering": True,
            "timestamps_in_reproducible_artifacts": False,
        },
    }
    atomic_text(config.inventory_manifest, canonical_json(manifest, pretty=True))
    return manifest


def _load_inventory(config: NativeCodeConfig) -> dict[str, Any]:
    if not config.inventory_path.is_file():
        raise FileNotFoundError(config.inventory_path)
    payload = json.loads(config.inventory_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "AA8_NATIVE_CODE_INVENTORY_V1":
        raise ValueError("Unsupported native-code inventory")
    if payload.get("client_build") != config.client_build:
        raise ValueError("Native-code inventory belongs to another client build")
    if payload.get("config_sha256") != config.config_sha256:
        raise ValueError("Native-code inventory was built with another config")
    return payload


def _selected_binary(
    config: NativeCodeConfig,
    key_or_name: str,
    architecture: str | None = None,
) -> dict[str, Any]:
    candidates = []
    for item in _load_inventory(config)["binaries"]:
        if key_or_name in {item["binary_key"], item["module_name"]}:
            if architecture is None or item["architecture"] == architecture:
                candidates.append(item)
    if not candidates:
        raise KeyError(f"Unknown binary: {key_or_name}")
    if len(candidates) != 1:
        raise ValueError(
            f"Binary name is ambiguous; pass --architecture: {key_or_name}"
        )
    return candidates[0]


def register_dynamic_coverage(
    config: NativeCodeConfig,
    source_manifest: Path,
) -> dict[str, Any]:
    """Freeze a normalized, local-only dynamic coverage observation.

    Collection remains an operator-controlled action.  This importer refuses
    manifests that report a public network or an active anticheat process.
    """
    source_manifest = source_manifest.resolve()
    payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    if payload.get("schema") != "AA8_NATIVE_COVERAGE_V1":
        raise ValueError("Unsupported native coverage manifest")
    if payload.get("client_build") != config.client_build:
        raise ValueError("Dynamic coverage belongs to another client build")
    if payload.get("network_scope") not in {"offline", "local_only"}:
        raise ValueError("Dynamic coverage must be offline or local-only")
    if payload.get("anticheat_state") != "not_running":
        raise ValueError("Dynamic coverage with anticheat present is forbidden")

    trace_path = Path(str(payload["trace_path"])).resolve()
    if not trace_path.is_file():
        raise FileNotFoundError(trace_path)
    observed_trace_hash = sha256_file(trace_path)
    declared_trace_hash = str(payload.get("trace_sha256", "")).upper()
    if declared_trace_hash and declared_trace_hash != observed_trace_hash:
        raise ValueError("Dynamic trace hash mismatch")

    modules: list[dict[str, Any]] = []
    seen_hits: set[tuple[str, int]] = set()
    for module in payload.get("modules", []):
        selected = _selected_binary(
            config,
            str(module["binary"]),
            str(module["architecture"]),
        )
        if selected["classification"] == "excluded_anticheat":
            raise ValueError("Anticheat dynamic coverage is forbidden")
        hits: list[dict[str, int]] = []
        for hit in module.get("hits", []):
            rva = int(hit["rva"], 0) if isinstance(hit["rva"], str) else int(hit["rva"])
            hit_count = max(1, int(hit.get("hit_count", 1)))
            identity = (selected["binary_key"], rva)
            if identity in seen_hits:
                raise ValueError(f"Duplicate dynamic coverage hit: {identity}")
            seen_hits.add(identity)
            hits.append({"rva": rva, "hit_count": hit_count})
        modules.append(
            {
                "binary_key": selected["binary_key"],
                "module_name": selected["module_name"],
                "architecture": selected["architecture"],
                "loaded_base": int(module.get("loaded_base", 0)),
                "hits": sorted(hits, key=lambda item: item["rva"]),
            }
        )
    if not modules:
        raise ValueError("Dynamic coverage manifest contains no modules")

    normalized = {
        "schema": "AA8_NATIVE_COVERAGE_V1",
        "client_build": config.client_build,
        "scenario": str(payload["scenario"]),
        "tool": {
            "id": str(payload["tool"]["id"]),
            "version": str(payload["tool"]["version"]),
        },
        "trace_path": trace_path.as_posix(),
        "trace_sha256": observed_trace_hash,
        "network_scope": str(payload["network_scope"]),
        "anticheat_state": "not_running",
        "status": str(payload.get("status", "confirmed")),
        "modules": sorted(
            modules,
            key=lambda item: (item["binary_key"], item["architecture"]),
        ),
        "source_manifest_sha256": sha256_file(source_manifest),
    }
    if normalized["status"] not in NATIVE_CODE_STATES:
        raise ValueError(f"Unsupported dynamic coverage state: {normalized['status']}")
    run_hash = sha256_text(canonical_json(normalized))
    destination = config.dynamic_root / f"{run_hash.lower()}.manifest.json"
    atomic_text(destination, canonical_json(normalized, pretty=True))
    return {
        "status": "confirmed",
        "dynamic_run_sha256": run_hash,
        "manifest": {
            "path": destination.as_posix(),
            "sha256": sha256_file(destination),
        },
        "modules": len(modules),
        "hits": sum(len(item["hits"]) for item in modules),
    }


def normalize_drcov_trace(
    config: NativeCodeConfig,
    trace_path: Path,
    *,
    scenario: str,
    architecture: str,
    output_path: Path,
    network_scope: str = "offline",
    tool_version: str = "11.3.0",
) -> dict[str, Any]:
    """Convert a DynamoRIO drcov log into the guarded coverage manifest."""
    if architecture not in {"x86", "x64"}:
        raise ValueError(f"Unsupported drcov architecture: {architecture}")
    if network_scope not in {"offline", "local_only"}:
        raise ValueError("drcov normalization rejects public network scope")
    scenario = scenario.strip()
    if not scenario:
        raise ValueError("drcov scenario is required")
    trace_path = trace_path.resolve()
    if not trace_path.is_file():
        raise FileNotFoundError(trace_path)
    data = trace_path.read_bytes()
    marker = b"BB Table:"
    marker_offset = data.find(marker)
    if marker_offset < 0:
        raise ValueError("drcov BB Table header is missing")
    header_end = data.find(b"\n", marker_offset)
    if header_end < 0:
        raise ValueError("drcov BB Table header is truncated")
    header_text = data[: header_end + 1].decode("utf-8", errors="replace")
    version = re.search(r"^DRCOV VERSION:\s*(\d+)\s*$", header_text, re.MULTILINE)
    if version is None or int(version.group(1)) != 2:
        raise ValueError("Only DRCOV VERSION 2 is supported")
    count_match = re.search(
        r"^BB Table:\s*(\d+)\s+bbs\s*$", header_text, re.MULTILINE
    )
    if count_match is None:
        raise ValueError("Unsupported drcov BB Table declaration")
    bb_count = int(count_match.group(1))
    bb_bytes = data[header_end + 1 :]
    expected_bytes = bb_count * 8
    if len(bb_bytes) < expected_bytes:
        raise ValueError("drcov basic-block table is truncated")

    lines = header_text.splitlines()
    module_line = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("Module Table:")
        ),
        None,
    )
    columns_line = next(
        (
            index
            for index, line in enumerate(lines)
            if module_line is not None
            and index > module_line
            and line.startswith("Columns:")
        ),
        None,
    )
    bb_line = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("BB Table:")
        ),
        None,
    )
    if module_line is None or columns_line is None or bb_line is None:
        raise ValueError("drcov module table is incomplete")
    module_count_match = re.match(
        r"^Module Table:\s*version\s+\d+,\s*count\s+(\d+)\s*$",
        lines[module_line],
    )
    if module_count_match is None:
        raise ValueError("Unsupported drcov Module Table declaration")
    declared_module_count = int(module_count_match.group(1))
    columns = [
        item.strip().lower().replace(" ", "_")
        for item in lines[columns_line].split(":", 1)[1].split(",")
    ]
    required_columns = {"id", "path"}
    if not required_columns.issubset(columns):
        raise ValueError("drcov module table lacks id/path columns")
    start_column = "base" if "base" in columns else "start"
    if start_column not in columns:
        raise ValueError("drcov module table lacks base/start column")

    modules_by_id: dict[int, dict[str, Any]] = {}
    module_rows = csv.reader(lines[columns_line + 1 : bb_line])
    for values in module_rows:
        if not values or len(values) < len(columns):
            continue
        row = {
            column: value.strip()
            for column, value in zip(columns, values, strict=False)
        }
        try:
            module_id = int(row["id"], 0)
            loaded_base = int(row[start_column], 0)
        except ValueError as exc:
            raise ValueError(f"Invalid drcov module row: {values}") from exc
        path_value = row["path"].strip().strip('"')
        modules_by_id[module_id] = {
            "module_name": Path(path_value).name.lower(),
            "loaded_base": loaded_base,
            "source_path": path_value,
        }
    if len(modules_by_id) != declared_module_count:
        raise ValueError(
            "drcov module count mismatch: "
            f"declared={declared_module_count} parsed={len(modules_by_id)}"
        )

    inventory = _load_inventory(config)
    inventory_index = {
        (str(item["module_name"]).lower(), str(item["architecture"])): item
        for item in inventory["binaries"]
    }
    for module in modules_by_id.values():
        selected = inventory_index.get(
            (module["module_name"], architecture)
        )
        if selected and selected["classification"] == "excluded_anticheat":
            raise ValueError(
                f"Anticheat module in drcov trace: {module['module_name']}"
            )
        if classify_binary(config, module["module_name"]) == "excluded_anticheat":
            raise ValueError(
                f"Anticheat module in drcov trace: {module['module_name']}"
            )

    hits_by_binary: dict[str, dict[int, int]] = {}
    for offset in range(0, expected_bytes, 8):
        start_rva, _size, module_id = struct.unpack_from(
            "<IHH", bb_bytes, offset
        )
        module = modules_by_id.get(module_id)
        if module is None:
            continue
        selected = inventory_index.get(
            (module["module_name"], architecture)
        )
        if selected is None or not selected["analysis_enabled"]:
            continue
        image_size = int(selected.get("image_size", 0))
        if image_size and start_rva >= image_size:
            raise ValueError(
                f"drcov RVA 0x{start_rva:X} exceeds "
                f"{selected['module_name']} image size"
            )
        hits = hits_by_binary.setdefault(str(selected["binary_key"]), {})
        hits[start_rva] = hits.get(start_rva, 0) + 1

    if not hits_by_binary:
        raise ValueError(
            "drcov trace contains no basic blocks from analysis-enabled modules"
        )

    normalized_modules = []
    for binary_key_value, hits in sorted(hits_by_binary.items()):
        selected = next(
            item
            for item in inventory["binaries"]
            if item["binary_key"] == binary_key_value
        )
        observed = next(
            item
            for item in modules_by_id.values()
            if item["module_name"] == str(selected["module_name"]).lower()
        )
        normalized_modules.append(
            {
                "binary": selected["module_name"],
                "architecture": architecture,
                "loaded_base": observed["loaded_base"],
                "hits": [
                    {"rva": f"0x{rva:X}", "hit_count": count}
                    for rva, count in sorted(hits.items())
                ],
            }
        )
    manifest = {
        "schema": "AA8_NATIVE_COVERAGE_V1",
        "client_build": config.client_build,
        "scenario": scenario,
        "tool": {"id": "drcov", "version": tool_version},
        "trace_path": trace_path.as_posix(),
        "trace_sha256": sha256_file(trace_path),
        "network_scope": network_scope,
        "anticheat_state": "not_running",
        "status": "confirmed",
        "modules": normalized_modules,
    }
    atomic_text(output_path.resolve(), canonical_json(manifest, pretty=True))
    return {
        "status": "confirmed",
        "trace_sha256": manifest["trace_sha256"],
        "modules": len(normalized_modules),
        "basic_blocks": sum(
            len(item["hits"]) for item in normalized_modules
        ),
        "manifest": output_path.resolve().as_posix(),
    }


def _locator_address(locator: str, name: str) -> int | None:
    for value in (locator, name):
        match = _FUNCTION_LOCATOR.search(value or "")
        if match:
            return int(match.group(1), 16)
    return None


def build_anchor_inventory(config: NativeCodeConfig) -> dict[str, Any]:
    if not config.forensics_database.is_file():
        raise FileNotFoundError(config.forensics_database)
    inventory = _load_inventory(config)
    x2game = {
        str(item["architecture"]): item
        for item in inventory["binaries"]
        if item["module_name"].lower() == "x2game.dll"
    }
    connection = open_read_only(config.forensics_database)
    anchors: dict[tuple[str, int], dict[str, Any]] = {}
    try:
        rows = connection.execute(
            """
            SELECT consumer_key,scope_key,consumer_kind,name,module,locator,
                   architecture,state,evidence_json
            FROM consumers
            WHERE lower(coalesce(module,''))='x2game.dll'
              AND state IN ('confirmed','corroborated')
            ORDER BY architecture,locator,consumer_key
            """
        )
        for row in rows:
            architecture = str(row["architecture"] or "").lower()
            binary = x2game.get(architecture)
            if binary is None:
                continue
            address = _locator_address(str(row["locator"]), str(row["name"]))
            if address is None:
                continue
            image_base = int(binary["image_base"])
            rva = address - image_base if address >= image_base else address
            if not 0 <= rva < int(binary["image_size"]):
                continue
            key = (str(binary["binary_key"]), rva)
            anchor = anchors.setdefault(
                key,
                {
                    "binary_key": binary["binary_key"],
                    "architecture": architecture,
                    "entry_rva": rva,
                    "locators": [],
                },
            )
            anchor["locators"].append(
                {
                    "consumer_key": row["consumer_key"],
                    "scope_key": row["scope_key"],
                    "consumer_kind": row["consumer_kind"],
                    "name": row["name"],
                    "locator": row["locator"],
                    "state": row["state"],
                }
            )
    finally:
        connection.close()
    payload = {
        "schema": "AA8_NATIVE_CODE_ANCHORS_V1",
        "client_build": config.client_build,
        "inventory_sha256": sha256_file(config.inventory_path),
        "forensics_database_sha256": sha256_file(config.forensics_database),
        "anchors": sorted(
            anchors.values(),
            key=lambda item: (item["architecture"], item["entry_rva"]),
        ),
    }
    atomic_text(config.anchors_path, canonical_json(payload, pretty=True))
    return {
        "anchors": len(payload["anchors"]),
        "path": config.anchors_path.as_posix(),
        "sha256": sha256_file(config.anchors_path),
    }


def _tool_version(executable: Path, arguments: list[str]) -> str:
    completed = subprocess.run(
        [str(executable), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    text = (completed.stdout + "\n" + completed.stderr).strip()
    return text.splitlines()[0].strip() if text else "unknown"


def _run_process(
    command: list[str],
    *,
    timeout: int,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout.replace("\r\n", "\n"),
            "stderr": completed.stderr.replace("\r\n", "\n"),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "status": "confirmed" if completed.returncode == 0 else "failed",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "exit_code": None,
            "stdout": (exc.stdout or "")
            if isinstance(exc.stdout, str)
            else (exc.stdout or b"").decode("utf-8", errors="replace"),
            "stderr": (exc.stderr or "")
            if isinstance(exc.stderr, str)
            else (exc.stderr or b"").decode("utf-8", errors="replace"),
            "duration_ms": int((time.monotonic() - started) * 1000),
            "status": "timeout",
        }


def _run_output_dir(
    config: NativeCodeConfig,
    engine: str,
    binary: dict[str, Any],
    scope: str,
) -> Path:
    safe_scope = re.sub(r"[^A-Za-z0-9_.-]+", "-", scope)
    return (
        config.raw_root
        / engine
        / f"{binary['module_name']}-{binary['architecture']}-{binary['sha256'][:12]}"
        / safe_scope
    )


def _resume_manifest(
    config: NativeCodeConfig,
    manifest_path: Path,
    binary: dict[str, Any],
    expected_engine: str,
) -> dict[str, Any] | None:
    if not manifest_path.is_file():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("status") not in _TERMINAL_RUN_STATES:
        return None
    if payload.get("schema") != "AA8_NATIVE_CODE_ENGINE_RUN_V1":
        raise ValueError(f"Unsupported engine run manifest: {manifest_path}")
    if payload.get("client_build") != config.client_build:
        raise ValueError(f"Engine run belongs to another build: {manifest_path}")
    if payload.get("config_sha256") != config.config_sha256:
        raise ValueError(f"Engine run config mismatch: {manifest_path}")
    inventory_sha256 = sha256_file(config.inventory_path)
    if payload.get("inventory_sha256") != inventory_sha256:
        raise ValueError(f"Engine run inventory mismatch: {manifest_path}")
    recorded = payload.get("binary", {})
    if (
        recorded.get("binary_key") != binary["binary_key"]
        or str(recorded.get("sha256", "")).upper()
        != str(binary["sha256"]).upper()
        or recorded.get("architecture") != binary["architecture"]
    ):
        raise ValueError(f"Engine run binary identity mismatch: {manifest_path}")
    if payload.get("engine", {}).get("id") != expected_engine:
        raise ValueError(f"Engine run engine mismatch: {manifest_path}")
    _validate_run_outputs(
        config,
        payload,
        manifest_path,
        verify_hashes=True,
    )
    payload["manifest"] = {
        "path": manifest_path.resolve().as_posix(),
        "sha256": sha256_file(manifest_path),
    }
    return payload


def _write_run_manifest(
    config: NativeCodeConfig,
    output: Path,
    *,
    engine: str,
    version: str,
    binary: dict[str, Any],
    scope: str,
    timeout: int,
    result: dict[str, Any],
    outputs: Iterable[Path],
    command: list[str],
) -> dict[str, Any]:
    files = []
    for path in sorted(
        (
            item
            for item in outputs
            if item.is_file() and item.name != "run.manifest.json"
        ),
        key=lambda item: item.as_posix(),
    ):
        files.append(
            {
                "path": path.resolve().as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    engine_path = Path(command[0]) if command else None
    manifest = {
        "schema": "AA8_NATIVE_CODE_ENGINE_RUN_V1",
        "client_build": config.client_build,
        "config_sha256": config.config_sha256,
        "inventory_sha256": sha256_file(config.inventory_path),
        "binary": {
            "binary_key": binary["binary_key"],
            "path": binary["source_path"],
            "sha256": binary["sha256"],
            "architecture": binary["architecture"],
        },
        "engine": {
            "id": engine,
            "version": version,
            "path": engine_path.resolve().as_posix()
            if engine_path and engine_path.is_file()
            else command[0] if command else None,
            "sha256": sha256_file(engine_path)
            if engine_path and engine_path.is_file()
            else None,
        },
        "scope": scope,
        "timeout_seconds": timeout,
        "command": command,
        "exit_code": result["exit_code"],
        "duration_ms": result["duration_ms"],
        "status": result["status"],
        "stdout": result["stdout"][-20000:],
        "stderr": result["stderr"][-20000:],
        "outputs": files,
    }
    path = output / "run.manifest.json"
    atomic_text(path, canonical_json(manifest, pretty=True))
    manifest["manifest"] = {
        "path": path.resolve().as_posix(),
        "sha256": sha256_file(path),
    }
    return manifest


def _run_rizin(
    config: NativeCodeConfig,
    binary: dict[str, Any],
    scope: str,
    resume: bool,
) -> dict[str, Any]:
    output = _run_output_dir(config, "rizin", binary, scope)
    manifest_path = output / "run.manifest.json"
    if resume:
        prior = _resume_manifest(config, manifest_path, binary, "rizin")
        if prior is not None:
            return prior
    executable = Path(config.tools["rizin"]).resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output / "functions.json"
    command = [
        str(executable),
        "-2",
        "-A",
        "-q",
        "-c",
        "aflj",
        str(Path(binary["source_path"])),
    ]
    result = _run_process(
        command,
        timeout=config.timeouts["whole_module_seconds"],
    )
    if result["stdout"].strip():
        atomic_text(raw_path, result["stdout"])
    version = _tool_version(executable, ["-v"])
    return _write_run_manifest(
        config,
        output,
        engine="rizin",
        version=version,
        binary=binary,
        scope=scope,
        timeout=config.timeouts["whole_module_seconds"],
        result=result,
        outputs=[raw_path],
        command=command,
    )


def _ghidra_process_name(binary: dict[str, Any]) -> str:
    return str(binary["module_name"])


def _run_ghidra(
    config: NativeCodeConfig,
    binary: dict[str, Any],
    scope: str,
    resume: bool,
) -> dict[str, Any]:
    output = _run_output_dir(config, "ghidra", binary, scope)
    manifest_path = output / "run.manifest.json"
    if resume:
        prior = _resume_manifest(config, manifest_path, binary, "ghidra")
        if prior is not None:
            return prior
    output.mkdir(parents=True, exist_ok=True)
    executable = Path(config.tools["ghidra_headless"]).resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)
    project = config.ghidra_projects.get(str(binary["architecture"]))
    if project is None:
        raise KeyError(f"No Ghidra project configured for {binary['architecture']}")
    script_root = Path(__file__).resolve().parents[1] / "ghidra"
    anchors = config.anchors_path if scope == "anchors" else Path("-")
    project_directory = Path(project["directory"]).resolve()
    module_name = str(binary["module_name"]).lower()
    use_shared_project = module_name == "x2game.dll" or (
        module_name == "xlcommon.dll" and binary["architecture"] == "x64"
    )
    project_name = (
        str(project["name"])
        if use_shared_project
        else (
            f"AA8Native_{binary['architecture']}_"
            f"{re.sub(r'[^A-Za-z0-9]+', '_', module_name).strip('_')}_"
            f"{binary['sha256'][:12]}"
        )
    )
    project_exists = (project_directory / f"{project_name}.gpr").is_file()
    command = [
        str(executable),
        str(project_directory),
        project_name,
    ]
    if use_shared_project or project_exists:
        command.extend(
            [
                "-process",
                _ghidra_process_name(binary),
                "-readOnly",
                "-noanalysis",
            ]
        )
    else:
        command.extend(
            [
                "-import",
                str(Path(binary["source_path"]).resolve()),
                "-analysisTimeoutPerFile",
                str(config.timeouts["whole_module_seconds"]),
            ]
        )
    command.extend(
        [
        "-scriptPath",
        str(script_root),
        "-postScript",
        "DumpAa8NativeCorpus.java",
        str(output),
        str(binary["sha256"]),
        str(binary["architecture"]),
        str(config.batch_size),
        str(config.timeouts["ghidra_function_seconds"]),
        str(anchors),
        ]
    )
    environment = os.environ.copy()
    environment["JAVA_HOME"] = str(Path(config.tools["java_home"]).resolve())
    result = _run_process(
        command,
        timeout=config.timeouts["whole_module_seconds"],
        env=environment,
    )
    outputs = list(output.glob("batch-*.jsonl")) + list(output.glob("*.json"))
    version = "12.1.2"
    return _write_run_manifest(
        config,
        output,
        engine="ghidra",
        version=version,
        binary=binary,
        scope=scope,
        timeout=config.timeouts["whole_module_seconds"],
        result=result,
        outputs=outputs,
        command=command,
    )


def _run_reko(
    config: NativeCodeConfig,
    binary: dict[str, Any],
    scope: str,
    resume: bool,
) -> dict[str, Any]:
    output = _run_output_dir(config, "reko", binary, scope)
    manifest_path = output / "run.manifest.json"
    if resume:
        prior = _resume_manifest(config, manifest_path, binary, "reko")
        if prior is not None:
            return prior
    executable = Path(config.tools["reko"]).resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)
    output.mkdir(parents=True, exist_ok=True)
    local_binary = output / Path(binary["source_path"]).name
    if not local_binary.is_file():
        import shutil

        shutil.copy2(Path(binary["source_path"]), local_binary)
    command = [
        str(executable),
        "decompile",
        "--time-limit",
        str(config.timeouts["whole_module_seconds"]),
        str(local_binary),
    ]
    result = _run_process(
        command,
        timeout=config.timeouts["whole_module_seconds"],
        cwd=output,
    )
    outputs = [
        path
        for path in output.rglob("*")
        if path.is_file() and path not in {local_binary, manifest_path}
    ]
    version = _tool_version(executable, ["--version"])
    return _write_run_manifest(
        config,
        output,
        engine="reko",
        version=version,
        binary=binary,
        scope=scope,
        timeout=config.timeouts["whole_module_seconds"],
        result=result,
        outputs=outputs,
        command=command,
    )


def _run_revng(
    config: NativeCodeConfig,
    binary: dict[str, Any],
    scope: str,
    resume: bool,
) -> dict[str, Any]:
    output = _run_output_dir(config, "revng", binary, scope)
    manifest_path = output / "run.manifest.json"
    if resume:
        prior = _resume_manifest(config, manifest_path, binary, "revng")
        if prior is not None:
            return prior
    output.mkdir(parents=True, exist_ok=True)
    docker = config.tools["docker"]
    source = Path(binary["source_path"]).resolve()
    artifact = output / "decompiled"
    command = [
        docker,
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{source.parent.as_posix()}:/input:ro",
        "-v",
        f"{output.as_posix()}:/output",
        config.revng_image,
        "revng",
        "artifact",
        "emit-c-as-single-file",
        f"/input/{source.name}",
        "--analyze",
        "-o=/output/decompiled",
    ]
    result = _run_process(
        command,
        timeout=config.timeouts["whole_module_seconds"],
    )
    version = config.revng_image.rsplit("@", 1)[-1][:19]
    return _write_run_manifest(
        config,
        output,
        engine="revng",
        version=version,
        binary=binary,
        scope=scope,
        timeout=config.timeouts["whole_module_seconds"],
        result=result,
        outputs=[artifact],
        command=command,
    )


def _run_angr(
    config: NativeCodeConfig,
    binary: dict[str, Any],
    scope: str,
    resume: bool,
) -> dict[str, Any]:
    output = _run_output_dir(config, "angr", binary, scope)
    manifest_path = output / "run.manifest.json"
    if resume:
        prior = _resume_manifest(config, manifest_path, binary, "angr")
        if prior is not None:
            return prior
    if scope != "anchors":
        raise ValueError("angr is scheduled only for --scope anchors")
    executable = Path(config.tools["angr_python"]).resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)
    if not config.anchors_path.is_file():
        build_anchor_inventory(config)
    output.mkdir(parents=True, exist_ok=True)
    helper = Path(__file__).resolve().parents[1] / "tools" / "run_angr_corpus.py"
    raw_path = output / "functions.jsonl"
    command = [
        str(executable),
        str(helper),
        "--binary",
        str(binary["source_path"]),
        "--binary-key",
        str(binary["binary_key"]),
        "--anchors",
        str(config.anchors_path),
        "--output",
        str(raw_path),
        "--timeout",
        str(config.timeouts["angr_function_seconds"]),
    ]
    result = _run_process(
        command,
        timeout=config.timeouts["whole_module_seconds"],
    )
    version = "9.3.1.post1"
    return _write_run_manifest(
        config,
        output,
        engine="angr",
        version=version,
        binary=binary,
        scope=scope,
        timeout=config.timeouts["whole_module_seconds"],
        result=result,
        outputs=[raw_path],
        command=command,
    )


def run_native_decompiler(
    config: NativeCodeConfig,
    *,
    engine: str,
    binary: str,
    architecture: str | None = None,
    scope: str = "full",
    resume: bool = False,
) -> dict[str, Any]:
    selected = _selected_binary(config, binary, architecture)
    if selected["classification"] == "excluded_anticheat":
        raise ValueError("Anticheat binaries are excluded by policy")
    if selected["classification"] == "third_party":
        raise ValueError("Third-party full decompilation is excluded by policy")
    runners = {
        "ghidra": _run_ghidra,
        "rizin": _run_rizin,
        "reko": _run_reko,
        "revng": _run_revng,
        "angr": _run_angr,
    }
    if engine not in runners:
        raise KeyError(f"Unsupported engine: {engine}")
    return runners[engine](config, selected, scope, resume)


def _wave_definition(config: NativeCodeConfig, wave_id: str) -> dict[str, Any]:
    waves = _load_native_waves(config)
    matches = [item for item in waves["waves"] if item.get("id") == wave_id]
    if len(matches) != 1:
        raise KeyError(f"Unknown native-code wave: {wave_id}")
    return matches[0]


def _wave_targets(
    config: NativeCodeConfig,
    wave_id: str,
    engines: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    wave = _wave_definition(config, wave_id)
    allowed_engines = tuple(str(item) for item in wave["engines"])
    requested = tuple(engines or allowed_engines)
    if not requested or len(set(requested)) != len(requested):
        raise ValueError("A batch needs a non-duplicated engine list")
    unsupported = sorted(set(requested) - set(allowed_engines))
    if unsupported:
        raise ValueError(
            f"Wave {wave_id} does not schedule engines: {', '.join(unsupported)}"
        )
    inventory = _load_inventory(config)
    inventory_index = {
        (str(item["module_name"]).lower(), str(item["architecture"])): item
        for item in inventory["binaries"]
    }
    targets: list[dict[str, Any]] = []
    for declaration in wave["binaries"]:
        module = str(declaration["module"]).lower()
        for architecture in declaration["architectures"]:
            selected = inventory_index.get((module, str(architecture)))
            if selected is None:
                raise KeyError(f"Unknown binary: {module} {architecture}")
            if selected["classification"] in {"excluded_anticheat", "third_party"}:
                raise ValueError(
                    f"Wave {wave_id} contains forbidden binary {module} {architecture}"
                )
            for engine in requested:
                targets.append(
                    {
                        "wave": wave_id,
                        "engine": engine,
                        "module": selected["module_name"],
                        "architecture": selected["architecture"],
                        "binary_key": selected["binary_key"],
                        "sha256": selected["sha256"],
                    }
                )
    return targets


def _terminal_batch_manifest(
    config: NativeCodeConfig,
    target: dict[str, Any],
    *,
    verify_outputs: bool = False,
) -> dict[str, Any] | None:
    binary = {
        "binary_key": target["binary_key"],
        "module_name": target["module"],
        "architecture": target["architecture"],
        "sha256": target["sha256"],
    }
    path = (
        _run_output_dir(config, target["engine"], binary, "full")
        / "run.manifest.json"
    )
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    recorded = payload.get("binary", {})
    if payload.get("client_build") != config.client_build:
        raise ValueError(f"Run manifest build mismatch: {path}")
    if payload.get("inventory_sha256") != sha256_file(config.inventory_path):
        raise ValueError(f"Run manifest inventory mismatch: {path}")
    if recorded.get("binary_key") != binary["binary_key"]:
        raise ValueError(f"Run manifest binary mismatch: {path}")
    if recorded.get("sha256") != binary["sha256"]:
        raise ValueError(f"Run manifest SHA-256 mismatch: {path}")
    if recorded.get("architecture") != binary["architecture"]:
        raise ValueError(f"Run manifest architecture mismatch: {path}")
    if payload.get("engine", {}).get("id") != target["engine"]:
        raise ValueError(f"Run manifest engine mismatch: {path}")
    if payload.get("status") not in _TERMINAL_RUN_STATES:
        return None
    output_audit = _validate_run_outputs(
        config, payload, path, verify_hashes=verify_outputs
    )
    payload["_output_audit"] = output_audit
    payload["_path"] = path.resolve().as_posix()
    return payload


def _validate_run_outputs(
    config: NativeCodeConfig,
    payload: dict[str, Any],
    manifest_path: Path,
    *,
    verify_hashes: bool,
) -> dict[str, int]:
    seen: set[Path] = set()
    files = total_bytes = hashes = self_references = 0
    resolved_manifest = manifest_path.resolve()
    for item in payload.get("outputs", []):
        path = Path(str(item["path"])).resolve()
        if path == resolved_manifest:
            # Legacy manifests could accidentally enumerate the manifest
            # itself after a prior run.  Such a recursive hash can never be
            # stable; preserve the raw manifest but exclude only this entry.
            self_references += 1
            continue
        if path in seen:
            raise ValueError(f"Duplicate run output: {manifest_path}: {path}")
        seen.add(path)
        try:
            path.relative_to(config.output_root.resolve())
        except ValueError as exc:
            raise ValueError(
                f"Run output escapes native-code root: {manifest_path}: {path}"
            ) from exc
        if not path.is_file():
            raise ValueError(f"Run output is missing: {manifest_path}: {path}")
        observed_bytes = path.stat().st_size
        declared_bytes = int(item["bytes"])
        if observed_bytes != declared_bytes:
            raise ValueError(
                f"Run output size mismatch: {manifest_path}: {path}"
            )
        if verify_hashes:
            observed_sha256 = sha256_file(path)
            if observed_sha256 != str(item["sha256"]).upper():
                raise ValueError(
                    f"Run output SHA-256 mismatch: {manifest_path}: {path}"
                )
            hashes += 1
        files += 1
        total_bytes += observed_bytes
    if payload.get("status") == "confirmed" and not files:
        raise ValueError(f"Confirmed run has no preserved outputs: {manifest_path}")
    return {
        "files": files,
        "bytes": total_bytes,
        "hashes_verified": hashes,
        "self_references_ignored": self_references,
    }


def _native_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match "
        "'run-native-decompiler|run-native-batch|analyzeHeadless|reko\\.exe|rizin\\.exe' } | "
        "Select-Object ProcessId,ParentProcessId,Name,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        if completed.returncode or not completed.stdout.strip():
            return []
        payload = json.loads(completed.stdout)
        values = payload if isinstance(payload, list) else [payload]
        return [
            {
                "pid": int(item["ProcessId"]),
                "parent_pid": int(item["ParentProcessId"]),
                "name": str(item["Name"]),
                "command_line": str(item.get("CommandLine") or ""),
            }
            for item in values
            if str(item.get("Name") or "").lower()
            not in {"powershell.exe", "pwsh.exe"}
        ]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError):
        return []


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _stage_15_build_activity(config: NativeCodeConfig) -> dict[str, Any]:
    def payload_pid(payload: dict[str, Any] | None) -> int:
        try:
            return int(payload.get("pid", -1)) if payload else -1
        except (TypeError, ValueError):
            return -1

    progress: dict[str, Any] | None = None
    if config.stage_build_progress.is_file():
        try:
            loaded = json.loads(
                config.stage_build_progress.read_text(encoding="utf-8")
            )
            if isinstance(loaded, dict):
                progress = loaded
        except (OSError, json.JSONDecodeError):
            progress = {
                "state": "invalid",
                "error": "Stage 15 progress file is not valid JSON",
            }
    lock_path = config.output_root / ".stage-15-build.lock"
    lock: dict[str, Any] | None = None
    if lock_path.is_file():
        try:
            loaded = json.loads(lock_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                lock = loaded
        except (OSError, json.JSONDecodeError):
            lock = {"pid": -1, "state": "invalid"}
    progress_pid = payload_pid(progress)
    lock_pid = payload_pid(lock)
    progress_pid_active = _pid_is_running(progress_pid)
    lock_pid_active = _pid_is_running(lock_pid)
    reported_state = str(progress.get("state", "unknown")) if progress else "absent"
    if reported_state == "running" and not progress_pid_active:
        reported_state = "interrupted"
    return {
        "active": progress_pid_active or lock_pid_active,
        "reported_state": reported_state,
        "progress_path": config.stage_build_progress.resolve().as_posix(),
        "progress_pid_active": progress_pid_active,
        "lock_path": lock_path.resolve().as_posix(),
        "lock_pid_active": lock_pid_active,
        "progress": progress,
        "lock": lock,
    }


def native_code_status(
    config: NativeCodeConfig,
    *,
    wave: str | None = None,
    verify_outputs: bool = False,
) -> dict[str, Any]:
    wave_payload = _load_native_waves(config)
    wave_ids = (
        [wave]
        if wave
        else [str(item["id"]) for item in wave_payload["waves"]]
    )
    coverage: list[dict[str, Any]] = []
    audited_files = audited_bytes = audited_hashes = 0
    all_manifests: list[Path] = []
    pending = 0
    for wave_id in wave_ids:
        targets = _wave_targets(config, wave_id)
        statuses: dict[str, int] = {}
        details: list[dict[str, Any]] = []
        for target in targets:
            terminal = _terminal_batch_manifest(
                config, target, verify_outputs=verify_outputs
            )
            status = str(terminal["status"]) if terminal else "pending"
            statuses[status] = statuses.get(status, 0) + 1
            if terminal:
                all_manifests.append(Path(terminal["_path"]))
                audit = terminal["_output_audit"]
                audited_files += int(audit["files"])
                audited_bytes += int(audit["bytes"])
                audited_hashes += int(audit["hashes_verified"])
            else:
                pending += 1
            details.append({**target, "status": status})
        modules: dict[tuple[str, str], dict[str, Any]] = {}
        for item in details:
            identity = (str(item["module"]), str(item["architecture"]))
            module = modules.setdefault(
                identity,
                {
                    "module": item["module"],
                    "architecture": item["architecture"],
                    "engines": {},
                },
            )
            module["engines"][item["engine"]] = item["status"]
        module_rows = []
        for module in modules.values():
            values = list(module["engines"].values())
            module["terminal"] = all(
                status in _TERMINAL_RUN_STATES for status in values
            )
            module_rows.append(module)
        coverage.append(
            {
                "wave": wave_id,
                "expected_runs": len(targets),
                "terminal_runs": len(targets) - statuses.get("pending", 0),
                "status_counts": statuses,
                "modules": module_rows,
                "runs": details,
            }
        )

    processes = _native_processes()
    stage_inputs: set[tuple[str, str]] = set()
    stage_manifest = None
    if config.stage_manifest.is_file():
        stage_manifest = json.loads(
            config.stage_manifest.read_text(encoding="utf-8")
        )
        for item in stage_manifest.get("inputs", {}).get(
            "engine_run_manifests", []
        ):
            stage_inputs.add((str(item["path"]).lower(), str(item["sha256"])))
    current_manifests = _engine_manifests(config)
    changed_inputs: list[str] = []
    for payload in current_manifests:
        path = Path(payload["_path"]).resolve()
        identity = (path.as_posix().lower(), sha256_file(path))
        if identity not in stage_inputs:
            changed_inputs.append(path.as_posix())
    manifest_matrix: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for payload in current_manifests:
        identity = (
            str(payload["binary"]["binary_key"]),
            str(payload["engine"]["id"]),
        )
        manifest_matrix.setdefault(identity, []).append(payload)
    required_missing: list[dict[str, str]] = []
    required_states: dict[str, int] = {}
    required_expected = required_terminal = 0
    for binary in _load_inventory(config)["binaries"]:
        if not binary["analysis_enabled"]:
            continue
        for engine in config.required_engines.get(
            str(binary["classification"]), ()
        ):
            required_expected += 1
            matches = manifest_matrix.get(
                (str(binary["binary_key"]), engine), []
            )
            matches.sort(
                key=lambda item: (
                    0 if item.get("scope") == "full" else 1,
                    str(item["_path"]),
                )
            )
            selected = matches[0] if matches else None
            state = (
                str(selected["status"])
                if selected
                and selected.get("status") in _TERMINAL_RUN_STATES
                else "pending"
            )
            required_states[state] = required_states.get(state, 0) + 1
            if state in _TERMINAL_RUN_STATES:
                required_terminal += 1
            else:
                required_missing.append(
                    {
                        "module": str(binary["module_name"]),
                        "architecture": str(binary["architecture"]),
                        "engine": engine,
                    }
                )
    overlay_sha = sha256_file(config.review_overrides_path)
    recorded_overlay = (
        stage_manifest.get("inputs", {}).get("review_overrides_sha256")
        if stage_manifest
        else None
    )
    waves_sha = sha256_file(config.waves_path)
    recorded_waves = (
        stage_manifest.get("inputs", {}).get("waves_sha256")
        if stage_manifest
        else None
    )
    stage_build = _stage_15_build_activity(config)
    stage_stale = (
        not config.stage_database.is_file()
        or bool(changed_inputs)
        or recorded_overlay != overlay_sha
        or recorded_waves != waves_sha
        or bool(processes)
        or bool(stage_build["active"])
    )
    reko = [
        item
        for item in processes
        if "reko" in (item["name"] + " " + item["command_line"]).lower()
    ]
    pending_batches = []
    if config.batch_root.is_dir():
        for path in sorted(config.batch_root.glob("*/run.manifest.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("status") not in _TERMINAL_RUN_STATES:
                pending_batches.append(path.resolve().as_posix())
    return {
        "client_build": config.client_build,
        "wave_filter": wave,
        "processes": processes,
        "reko": {
            "active": bool(reko),
            "processes": reko,
        },
        "pending_manifests": pending,
        "pending_batch_manifests": pending_batches,
        "output_audit": {
            "hashes_verified": audited_hashes,
            "files": audited_files,
            "bytes": audited_bytes,
            "terminal_runs_verified": sum(
                item["terminal_runs"] for item in coverage
            ),
        },
        "required_engine_coverage": {
            "expected": required_expected,
            "terminal": required_terminal,
            "status_counts": required_states,
            "missing": required_missing,
        },
        "coverage": coverage,
        "stage_15": {
            "present": config.stage_database.is_file(),
            "stale": stage_stale or bool(pending_batches),
            "build_progress": stage_build,
            "changed_engine_manifests": changed_inputs,
            "changed_engine_manifest_count": len(changed_inputs),
            "review_overrides_sha256": overlay_sha,
            "recorded_review_overrides_sha256": recorded_overlay,
            "waves_sha256": waves_sha,
            "recorded_waves_sha256": recorded_waves,
            "build_ready": (
                not processes
                and not stage_build["active"]
                and not pending_batches
                and pending == 0
                and not required_missing
            ),
        },
    }


def run_native_batch(
    config: NativeCodeConfig,
    *,
    wave: str,
    engines: Iterable[str],
    resume: bool = False,
) -> dict[str, Any]:
    requested = tuple(str(item).strip() for item in engines if str(item).strip())
    targets = _wave_targets(config, wave, requested)
    by_engine: dict[str, list[dict[str, Any]]] = {
        engine: [item for item in targets if item["engine"] == engine]
        for engine in requested
    }
    locks = config.batch_root / ".locks"
    locks.mkdir(parents=True, exist_ok=True)
    acquired: list[Path] = []
    try:
        for engine in requested:
            lock = locks / f"{engine}.lock"
            if lock.is_file():
                try:
                    lock_payload = json.loads(lock.read_text(encoding="utf-8"))
                    lock_pid = int(lock_payload["pid"])
                except (ValueError, KeyError, OSError, json.JSONDecodeError):
                    lock_pid = -1
                active_processes = _native_processes()
                active_pids = {item["pid"] for item in active_processes}
                engine_active = any(
                    (
                        engine == "ghidra"
                        and "analyzeheadless" in item["command_line"].lower()
                    )
                    or (
                        engine == "rizin"
                        and (
                            item["name"].lower() == "rizin.exe"
                            or " --engine rizin " in item["command_line"].lower()
                        )
                    )
                    for item in active_processes
                )
                if lock_pid not in active_pids and not engine_active:
                    lock.unlink(missing_ok=True)
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(canonical_json({"pid": os.getpid(), "wave": wave}))
            acquired.append(lock)
    except FileExistsError as exc:
        for lock in acquired:
            lock.unlink(missing_ok=True)
        raise RuntimeError(
            f"A native-code {Path(exc.filename).stem} batch is already active"
        ) from exc

    def worker(engine: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for target in by_engine[engine]:
            prior = (
                _terminal_batch_manifest(
                    config, target, verify_outputs=True
                )
                if resume
                else None
            )
            if prior is not None:
                results.append(
                    {
                        **target,
                        "status": prior["status"],
                        "resumed": True,
                        "manifest": prior["_path"],
                    }
                )
                continue
            binary = _selected_binary(
                config, target["binary_key"], target["architecture"]
            )
            try:
                result = run_native_decompiler(
                    config,
                    engine=engine,
                    binary=target["binary_key"],
                    architecture=target["architecture"],
                    scope="full",
                    resume=False,
                )
            except Exception as exc:  # Preserve a terminal evidence record.
                output = _run_output_dir(config, engine, binary, "full")
                output.mkdir(parents=True, exist_ok=True)
                result = _write_run_manifest(
                    config,
                    output,
                    engine=engine,
                    version="unknown",
                    binary=binary,
                    scope="full",
                    timeout=config.timeouts["whole_module_seconds"],
                    result={
                        "exit_code": None,
                        "stdout": "",
                        "stderr": f"{type(exc).__name__}: {exc}",
                        "duration_ms": 0,
                        "status": "failed",
                    },
                    outputs=[],
                    command=[],
                )
            results.append(
                {
                    **target,
                    "status": result["status"],
                    "resumed": False,
                    "manifest": result["manifest"]["path"],
                }
            )
        return results

    started = time.monotonic()
    results: list[dict[str, Any]] = []
    destination = config.batch_root / wave / "run.manifest.json"
    running_manifest = {
        "schema": "AA8_NATIVE_CODE_BATCH_RUN_V1",
        "client_build": config.client_build,
        "wave": wave,
        "waves_sha256": sha256_file(config.waves_path),
        "inventory_sha256": sha256_file(config.inventory_path),
        "engines": list(requested),
        "status": "not_scheduled",
        "runs": [],
    }
    atomic_text(destination, canonical_json(running_manifest, pretty=True))
    try:
        with ThreadPoolExecutor(max_workers=min(2, len(requested))) as executor:
            futures = {
                executor.submit(worker, engine): engine for engine in requested
            }
            for future in as_completed(futures):
                results.extend(future.result())
    finally:
        for lock in acquired:
            lock.unlink(missing_ok=True)
    results.sort(
        key=lambda item: (
            item["engine"],
            item["module"].lower(),
            item["architecture"],
        )
    )
    terminal = all(item["status"] in _TERMINAL_RUN_STATES for item in results)
    manifest = {
        "schema": "AA8_NATIVE_CODE_BATCH_RUN_V1",
        "client_build": config.client_build,
        "wave": wave,
        "waves_sha256": sha256_file(config.waves_path),
        "inventory_sha256": sha256_file(config.inventory_path),
        "engines": list(requested),
        "duration_ms": int((time.monotonic() - started) * 1000),
        "status": "confirmed" if terminal else "failed",
        "runs": results,
    }
    atomic_text(destination, canonical_json(manifest, pretty=True))
    manifest["manifest"] = {
        "path": destination.resolve().as_posix(),
        "sha256": sha256_file(destination),
    }
    return manifest


def _json_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end < start:
            return []
        payload = json.loads(text[start : end + 1])
    if isinstance(payload, dict):
        for key in ("functions", "result"):
            if isinstance(payload.get(key), list):
                return list(payload[key])
        return []
    return list(payload) if isinstance(payload, list) else []


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                yield value


def _engine_manifests(config: NativeCodeConfig) -> list[dict[str, Any]]:
    result = []
    if not config.raw_root.is_dir():
        return result
    for path in sorted(config.raw_root.rglob("run.manifest.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = path
        result.append(payload)
    return result


def _insert_common_artifact(
    connection: sqlite3.Connection,
    *,
    key: str,
    path: Path,
    role: str,
    state: str,
    evidence: dict[str, Any],
    sha256: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO artifacts(
            artifact_key,source_stage,role,path,bytes,sha256,build,
            authority,state,provenance,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            15,
            role,
            path.resolve().as_posix(),
            path.stat().st_size if path.is_file() else 0,
            sha256 or (sha256_file(path) if path.is_file() else None),
            None,
            "derived_forensic",
            state,
            "native_code_forensic",
            canonical_json(evidence),
        ),
    )


def _insert_inventory(
    connection: sqlite3.Connection,
    config: NativeCodeConfig,
    inventory: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    binaries: dict[str, dict[str, Any]] = {}
    for item in sorted(
        inventory["binaries"],
        key=lambda value: (value["architecture"], value["module_name"].lower()),
    ):
        key = str(item["binary_key"])
        binaries[key] = item
        connection.execute(
            """
            INSERT INTO code_binaries(
                binary_key,module_name,architecture,classification,source_path,
                bytes,sha256,machine,image_base,entry_rva,image_size,timestamp,
                linker_version,signed,pdb_path,pdb_guid,pdb_age,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                key,
                item["module_name"],
                item["architecture"],
                item["classification"],
                item["source_path"],
                item["bytes"],
                item["sha256"],
                item["machine"],
                item["image_base"],
                item["entry_rva"],
                item["image_size"],
                item["timestamp"],
                item["linker_version"],
                int(item["signed"]),
                item.get("pdb_path"),
                item.get("pdb_guid"),
                item.get("pdb_age"),
                item["architecture_state"],
                canonical_json(
                    {
                        "bits": item["bits"],
                        "characteristics": item["characteristics"],
                        "analysis_enabled": item["analysis_enabled"],
                        "source_aliases": item.get("source_aliases", []),
                        "pdb_lookup": {
                            "declared_path": item.get("pdb_path"),
                            "declared_path_exists": bool(
                                item.get("pdb_path")
                                and Path(str(item["pdb_path"])).is_file()
                            ),
                            "adjacent_candidate": (
                                (
                                    Path(item["source_path"]).parent
                                    / Path(str(item["pdb_path"])).name
                                ).as_posix()
                                if item.get("pdb_path")
                                else None
                            ),
                            "adjacent_candidate_exists": bool(
                                item.get("pdb_path")
                                and (
                                    Path(item["source_path"]).parent
                                    / Path(str(item["pdb_path"])).name
                                ).is_file()
                            ),
                            "official_server": (
                                "not_applicable_for_xlgames_private_symbols"
                                if item["classification"]
                                in {"game_primary", "game_support", "engine_modified"}
                                else "applicable_only_for_vendor-owned_modules"
                            ),
                            "state": (
                                "confirmed"
                                if item.get("pdb_path")
                                and (
                                    Path(str(item["pdb_path"])).is_file()
                                    or (
                                        Path(item["source_path"]).parent
                                        / Path(str(item["pdb_path"])).name
                                    ).is_file()
                                )
                                else "opaque"
                            ),
                        },
                    }
                ),
            ),
        )
        for section in item["sections"]:
            section_key = stable_key("code-section", key, section["ordinal"])
            connection.execute(
                """
                INSERT INTO code_sections(
                    section_key,binary_key,ordinal,name,rva,virtual_size,
                    raw_offset,raw_size,characteristics,executable,entropy,
                    sha256,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    section_key,
                    key,
                    section["ordinal"],
                    section["name"],
                    section["rva"],
                    section["virtual_size"],
                    section["raw_offset"],
                    section["raw_size"],
                    section["characteristics"],
                    int(section["executable"]),
                    section["entropy"],
                    section["sha256"],
                    "confirmed",
                    "{}",
                ),
            )
        for imp in item["imports"]:
            import_key = stable_key(
                "code-import",
                key,
                imp["library"],
                imp.get("symbol"),
                imp.get("ordinal"),
                imp["iat_rva"],
            )
            connection.execute(
                """
                INSERT INTO code_imports(
                    import_key,binary_key,library_name,symbol_name,ordinal,
                    iat_rva,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    import_key,
                    key,
                    imp["library"],
                    imp.get("symbol"),
                    imp.get("ordinal"),
                    imp["iat_rva"],
                    "confirmed",
                    "{}",
                ),
            )
        for exp in item["exports"]:
            export_key = stable_key("code-export", key, exp["ordinal"], exp["rva"])
            connection.execute(
                """
                INSERT INTO code_exports(
                    export_key,binary_key,symbol_name,ordinal,rva,forwarded_to,
                    state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    export_key,
                    key,
                    exp.get("symbol"),
                    exp["ordinal"],
                    exp["rva"],
                    exp.get("forwarded_to"),
                    "confirmed",
                    "{}",
                ),
            )
    _insert_common_artifact(
        connection,
        key="stage15:native-code-inventory",
        path=config.inventory_path,
        role="native_code_inventory",
        state="confirmed",
        evidence={"schema": inventory["schema"], "summary": inventory["summary"]},
    )
    return binaries


def _upsert_function(
    connection: sqlite3.Connection,
    *,
    binary: dict[str, Any],
    entry_rva: int,
    end_rva: int | None,
    size: int | None,
    byte_sha256: str | None,
    mnemonic_sha256: str | None,
    engine: str,
    kind: str,
    state: str,
    evidence: dict[str, Any],
) -> str:
    key = function_key(str(binary["binary_key"]), entry_rva)
    connection.execute(
        """
        INSERT INTO code_functions(
            function_key,binary_key,entry_rva,end_rva,size,byte_sha256,
            mnemonic_sha256,discovery_engine,function_kind,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(binary_key,entry_rva) DO UPDATE SET
            end_rva=CASE
                WHEN excluded.discovery_engine='ghidra' THEN excluded.end_rva
                WHEN code_functions.discovery_engine='ghidra'
                    THEN code_functions.end_rva
                ELSE COALESCE(code_functions.end_rva,excluded.end_rva) END,
            size=CASE
                WHEN excluded.discovery_engine='ghidra' THEN excluded.size
                WHEN code_functions.discovery_engine='ghidra'
                    THEN code_functions.size
                ELSE COALESCE(code_functions.size,excluded.size) END,
            byte_sha256=COALESCE(
                code_functions.byte_sha256,excluded.byte_sha256
            ),
            mnemonic_sha256=COALESCE(
                code_functions.mnemonic_sha256,excluded.mnemonic_sha256
            ),
            discovery_engine=CASE
                WHEN excluded.discovery_engine='ghidra' THEN 'ghidra'
                ELSE code_functions.discovery_engine END,
            function_kind=CASE
                WHEN excluded.discovery_engine='ghidra'
                    THEN excluded.function_kind
                ELSE code_functions.function_kind END,
            evidence_json=CASE
                WHEN excluded.discovery_engine='ghidra'
                    THEN excluded.evidence_json
                ELSE code_functions.evidence_json END,
            state=CASE
                WHEN code_functions.state='confirmed' THEN code_functions.state
                ELSE excluded.state END
        """,
        (
            key,
            binary["binary_key"],
            entry_rva,
            end_rva,
            size,
            byte_sha256,
            mnemonic_sha256,
            engine,
            kind,
            state,
            canonical_json(evidence),
        ),
    )
    return key


def _insert_name(
    connection: sqlite3.Connection,
    function: str,
    name: str | None,
    *,
    source_kind: str,
    source_locator: str,
    primary: bool,
    state: str,
    namespace: str | None = None,
    evidence: dict[str, Any] | None = None,
) -> None:
    if not name:
        return
    key = stable_key("code-name", function, name, source_kind, source_locator)
    connection.execute(
        """
        INSERT OR IGNORE INTO code_names(
            name_key,function_key,name,namespace,source_kind,source_locator,
            primary_name,state,evidence_json
        ) VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            key,
            function,
            name,
            namespace,
            source_kind,
            source_locator,
            int(primary),
            state,
            canonical_json(evidence or {}),
        ),
    )


def _insert_engine_run(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    path: Path,
) -> str:
    binary = payload["binary"]
    engine = payload["engine"]
    engine_sha256 = engine.get("sha256")
    if not engine_sha256 and payload.get("command"):
        executable = Path(str(payload["command"][0]))
        if executable.is_file():
            engine_sha256 = sha256_file(executable)
    run_key = stable_key(
        "code-run",
        binary["binary_key"],
        engine["id"],
        engine["version"],
        payload["scope"],
    )
    outputs_digest = sha256_text(
        canonical_json(
            [
                {"path": item["path"], "sha256": item["sha256"]}
                for item in payload.get("outputs", [])
            ]
        )
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
            run_key,
            binary["binary_key"],
            engine["id"],
            engine["version"],
            engine_sha256,
            payload["scope"],
            payload["inventory_sha256"],
            path.parent.resolve().as_posix(),
            outputs_digest,
            payload["timeout_seconds"],
            payload.get("exit_code"),
            payload["status"],
            payload.get("stderr") or None,
            canonical_json(
                {
                    "duration_ms": payload.get("duration_ms"),
                    "manifest_sha256": sha256_file(path),
                    "outputs": payload.get("outputs", []),
                }
            ),
        ),
    )
    return run_key


def _import_ghidra(
    connection: sqlite3.Connection,
    binaries: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    path: Path,
    run_key: str,
) -> int:
    binary = binaries[payload["binary"]["binary_key"]]
    count = 0
    for output in payload.get("outputs", []):
        output_path = Path(output["path"])
        if output_path.suffix.lower() != ".jsonl" or not output_path.is_file():
            continue
        batch_header: dict[str, Any] | None = None
        batch_functions = 0
        for row in _iter_jsonl(output_path):
            if row.get("record") == "batch":
                batch_header = row
                if str(row.get("binary_sha256", "")).upper() != str(
                    binary["sha256"]
                ).upper():
                    raise ValueError(f"Ghidra batch binary mismatch: {output_path}")
                if row.get("architecture") != binary["architecture"]:
                    raise ValueError(
                        f"Ghidra batch architecture mismatch: {output_path}"
                    )
                continue
            if row.get("record") != "function":
                continue
            batch_functions += 1
            entry = int(row["entry_rva"])
            size = int(row.get("size") or 0)
            key = _upsert_function(
                connection,
                binary=binary,
                entry_rva=entry,
                end_rva=(
                    int(row["end_rva"])
                    if row.get("end_rva") is not None
                    else entry + size if size else None
                ),
                size=size or None,
                byte_sha256=row.get("byte_sha256"),
                mnemonic_sha256=row.get("mnemonic_sha256"),
                engine="ghidra",
                kind=str(row.get("function_kind") or "function"),
                state="confirmed",
                evidence={
                    "batch": output_path.name,
                    "entry_va": row.get("entry_va"),
                },
            )
            name = row.get("name")
            _insert_name(
                connection,
                key,
                name,
                source_kind=(
                    "ghidra_default"
                    if not name or _DEFAULT_NAME.match(str(name))
                    else "ghidra_symbol"
                ),
                source_locator=f"{output_path.as_posix()}:{entry:X}",
                primary=True,
                state=(
                    "candidate"
                    if not name or _DEFAULT_NAME.match(str(name))
                    else "corroborated"
                ),
                namespace=row.get("namespace"),
            )
            instruction_rows = []
            for instruction in row.get("instructions", []):
                instruction_rva = int(instruction["rva"])
                instruction_rows.append(
                    (
                        (
                            f"insn:{binary['architecture']}:"
                            f"{binary['sha256'][:16].lower()}:"
                            f"{entry:08x}:{instruction_rva:08x}"
                        ),
                        key,
                        instruction_rva,
                        instruction["mnemonic"],
                        instruction["text"],
                        instruction["bytes"],
                        "confirmed",
                        "{}",
                    )
                )
            if instruction_rows:
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO code_instructions(
                        instruction_key,function_key,rva,mnemonic,
                        instruction_text,bytes_hex,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    instruction_rows,
                )
            for block in row.get("basic_blocks", []):
                block_key = stable_key(
                    "code-block", key, block["start_rva"], block["end_rva"]
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_basic_blocks(
                        block_key,function_key,start_rva,end_rva,
                        instruction_count,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        block_key,
                        key,
                        block["start_rva"],
                        block["end_rva"],
                        block.get("instruction_count", 0),
                        "confirmed",
                        "{}",
                    ),
                )
            for call in row.get("calls", []):
                target_rva = call.get("target_rva")
                target_key = (
                    function_key(str(binary["binary_key"]), int(target_rva))
                    if target_rva is not None
                    else None
                )
                call_key = stable_key(
                    "code-call",
                    key,
                    call.get("callsite_rva"),
                    target_rva,
                    call.get("target_name"),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_calls(
                        call_key,caller_function_key,callee_function_key,
                        callsite_rva,target_rva,target_name,call_kind,state,
                        evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        call_key,
                        key,
                        target_key
                        if target_rva is not None
                        and connection.execute(
                            "SELECT 1 FROM code_functions WHERE function_key=?",
                            (target_key,),
                        ).fetchone()
                        else None,
                        call.get("callsite_rva", entry),
                        target_rva,
                        call.get("target_name"),
                        call.get("call_kind", "direct"),
                        call.get("state", "confirmed"),
                        "{}",
                    ),
                )
            for reference in row.get("data_references", []):
                reference_key = stable_key(
                    "code-reference",
                    key,
                    reference["from_rva"],
                    reference["to_rva"],
                    reference.get("kind"),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_data_references(
                        reference_key,function_key,from_rva,to_rva,
                        reference_kind,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        reference_key,
                        key,
                        reference["from_rva"],
                        reference["to_rva"],
                        reference.get("kind", "data"),
                        "confirmed",
                        "{}",
                    ),
                )
            for string in row.get("strings", []):
                value = str(string["value"])
                string_key = stable_key(
                    "code-string",
                    binary["binary_key"],
                    string["rva"],
                    string.get("encoding", "utf-8"),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_strings(
                        string_key,binary_key,rva,encoding,value,value_sha256,
                        state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        string_key,
                        binary["binary_key"],
                        string["rva"],
                        string.get("encoding", "utf-8"),
                        value,
                        sha256_text(value),
                        "confirmed",
                        canonical_json({"sql_like": bool(_SQL_TOKEN.search(value))}),
                    ),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_function_strings(
                        function_key,string_key,reference_rva,state,evidence_json
                    ) VALUES(?,?,?,?,?)
                    """,
                    (
                        key,
                        string_key,
                        string.get("reference_rva", entry),
                        "confirmed",
                        "{}",
                    ),
                )
            pseudocode = row.get("pseudocode")
            status = str(row.get("decompile_status") or "failed")
            if status not in NATIVE_CODE_STATES:
                status = "confirmed" if pseudocode else "failed"
            decompilation_key = stable_key("code-decompilation", key, run_key)
            connection.execute(
                """
                INSERT OR REPLACE INTO code_decompilations(
                    decompilation_key,function_key,run_key,engine_id,prototype,
                    calling_convention,pseudocode,pseudocode_sha256,duration_ms,
                    status,error,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    decompilation_key,
                    key,
                    run_key,
                    "ghidra",
                    row.get("prototype"),
                    row.get("calling_convention"),
                    pseudocode,
                    sha256_text(pseudocode) if pseudocode else None,
                    row.get("duration_ms"),
                    status,
                    row.get("error"),
                    canonical_json(
                        {
                            "parameters": row.get("parameters", []),
                            "locals": row.get("locals", []),
                        }
                    ),
                ),
            )
            count += 1
        if batch_header is None:
            raise ValueError(f"Ghidra batch header missing: {output_path}")
        expected = int(batch_header["function_count"])
        if batch_functions != expected:
            raise ValueError(
                f"Ghidra batch incomplete: {output_path} "
                f"expected={expected} actual={batch_functions}"
            )
    for output in payload.get("outputs", []):
        metadata_path = Path(output["path"])
        if metadata_path.name != "metadata.json" or not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if str(metadata.get("binary_sha256", "")).upper() != str(
            binary["sha256"]
        ).upper():
            raise ValueError(f"Ghidra metadata binary mismatch: {metadata_path}")
        type_keys: dict[tuple[str, str], str] = {}
        for native_type in metadata.get("types", []):
            identity = (
                str(native_type.get("category") or ""),
                str(native_type["name"]),
            )
            type_key = stable_key(
                "code-type",
                binary["binary_key"],
                identity[0],
                identity[1],
            )
            type_keys[identity] = type_key
            connection.execute(
                """
                INSERT OR IGNORE INTO code_types(
                    type_key,binary_key,type_name,type_kind,size,source_kind,
                    source_locator,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    type_key,
                    binary["binary_key"],
                    identity[1],
                    "structure",
                    native_type.get("length"),
                    "ghidra_data_type",
                    f"{metadata_path.as_posix()}:{identity[0]}",
                    "candidate",
                    canonical_json({"category": identity[0]}),
                ),
            )
            for field in native_type.get("fields", []):
                field_key = stable_key(
                    "code-field",
                    type_key,
                    field["offset"],
                    field.get("name"),
                    field.get("type"),
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_type_fields(
                        field_key,type_key,offset,field_name,field_type,size,
                        source_locator,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        field_key,
                        type_key,
                        field["offset"],
                        field.get("name"),
                        field.get("type"),
                        field.get("length"),
                        f"{metadata_path.as_posix()}:{identity[0]}/{identity[1]}",
                        "candidate",
                        canonical_json({"ordinal": field.get("ordinal")}),
                    ),
                )
        for table in metadata.get("vtables", []):
            vtable_key = stable_key(
                "code-vtable",
                binary["binary_key"],
                table["rva"],
            )
            slots = table.get("slots", [])
            table_name = str(table.get("name") or "").strip()
            vtable_type_key = None
            if table_name:
                vtable_type_key = stable_key(
                    "code-type",
                    binary["binary_key"],
                    "vtable-symbol",
                    table_name,
                )
                connection.execute(
                    """
                    INSERT OR IGNORE INTO code_types(
                        type_key,binary_key,type_name,type_kind,size,source_kind,
                        source_locator,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        vtable_type_key,
                        binary["binary_key"],
                        table_name,
                        "class_vtable_symbol",
                        None,
                        "ghidra_symbol",
                        f"{metadata_path.as_posix()}:{table['rva']:X}",
                        "candidate",
                        canonical_json({"symbol_type": table.get("symbol_type")}),
                    ),
                )
            connection.execute(
                """
                INSERT INTO code_vtables(
                    vtable_key,binary_key,type_key,rva,slot_count,
                    source_locator,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(vtable_key) DO UPDATE SET
                    type_key=COALESCE(excluded.type_key,code_vtables.type_key),
                    slot_count=MAX(excluded.slot_count,code_vtables.slot_count)
                """,
                (
                    vtable_key,
                    binary["binary_key"],
                    vtable_type_key,
                    table["rva"],
                    len(slots),
                    f"{metadata_path.as_posix()}:{table['rva']:X}",
                    "candidate",
                    canonical_json(
                        {
                            "name": table.get("name"),
                            "symbol_type": table.get("symbol_type"),
                        }
                    ),
                ),
            )
            for slot in slots:
                target_key = function_key(
                    str(binary["binary_key"]),
                    int(slot["target_rva"]),
                )
                if not connection.execute(
                    "SELECT 1 FROM code_functions WHERE function_key=?",
                    (target_key,),
                ).fetchone():
                    target_key = None
                slot_key = stable_key(
                    "code-vtable-slot",
                    vtable_key,
                    slot["ordinal"],
                    slot["target_rva"],
                )
                connection.execute(
                    """
                    INSERT INTO code_vtable_slots(
                        slot_key,vtable_key,ordinal,target_function_key,
                        target_rva,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(slot_key) DO UPDATE SET
                        target_function_key=COALESCE(
                            excluded.target_function_key,
                            code_vtable_slots.target_function_key
                        ),
                        target_rva=excluded.target_rva
                    """,
                    (
                        slot_key,
                        vtable_key,
                        slot["ordinal"],
                        target_key,
                        slot["target_rva"],
                        "candidate",
                        canonical_json(
                            {
                                "slot_rva": slot.get("slot_rva"),
                                "target_name": slot.get("target_name"),
                            }
                        ),
                    ),
                )
    return count


def _import_rizin(
    connection: sqlite3.Connection,
    binaries: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    run_key: str,
) -> int:
    binary = binaries[payload["binary"]["binary_key"]]
    output = next(
        (
            Path(item["path"])
            for item in payload.get("outputs", [])
            if Path(item["path"]).name == "functions.json"
        ),
        None,
    )
    if output is None or not output.is_file():
        return 0
    count = 0
    for row in _json_rows(output):
        address = row.get("offset")
        if address is None:
            continue
        address = int(address)
        image_base = int(binary["image_base"])
        entry = address - image_base if address >= image_base else address
        if not 0 <= entry < int(binary["image_size"]):
            continue
        size = int(row.get("size") or 0)
        key = _upsert_function(
            connection,
            binary=binary,
            entry_rva=entry,
            end_rva=entry + size if size else None,
            size=size or None,
            byte_sha256=None,
            mnemonic_sha256=None,
            engine="rizin",
            kind=str(row.get("type") or "function"),
            state="candidate",
            evidence={"rizin": row},
        )
        _insert_name(
            connection,
            key,
            row.get("name"),
            source_kind="rizin_analysis",
            source_locator=f"{output.as_posix()}:{entry:X}",
            primary=False,
            state="candidate",
        )
        decompilation_key = stable_key("code-decompilation", key, run_key)
        connection.execute(
            """
            INSERT OR IGNORE INTO code_decompilations(
                decompilation_key,function_key,run_key,engine_id,prototype,
                calling_convention,pseudocode,pseudocode_sha256,duration_ms,
                status,error,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                decompilation_key,
                key,
                run_key,
                "rizin",
                None,
                None,
                None,
                None,
                None,
                "candidate",
                None,
                canonical_json(
                    {
                        "boundary_vote": True,
                        "entry_rva": entry,
                        "end_rva": entry + size if size else None,
                        "size": size or None,
                    }
                ),
            ),
        )
        count += 1
    return count


def _import_angr(
    connection: sqlite3.Connection,
    binaries: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    run_key: str,
) -> int:
    binary = binaries[payload["binary"]["binary_key"]]
    output = next(
        (
            Path(item["path"])
            for item in payload.get("outputs", [])
            if Path(item["path"]).name == "functions.jsonl"
        ),
        None,
    )
    if output is None or not output.is_file():
        return 0
    count = 0
    for row in _iter_jsonl(output):
        entry = int(row["entry_rva"])
        key = _upsert_function(
            connection,
            binary=binary,
            entry_rva=entry,
            end_rva=None,
            size=None,
            byte_sha256=None,
            mnemonic_sha256=None,
            engine="angr",
            kind="function",
            state="corroborated" if row.get("status") == "confirmed" else "candidate",
            evidence={"angr_function_address": row.get("address")},
        )
        pseudocode = row.get("pseudocode")
        status = row.get("status", "failed")
        connection.execute(
            """
            INSERT OR REPLACE INTO code_decompilations(
                decompilation_key,function_key,run_key,engine_id,prototype,
                calling_convention,pseudocode,pseudocode_sha256,duration_ms,
                status,error,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("code-decompilation", key, run_key),
                key,
                run_key,
                "angr",
                row.get("prototype"),
                row.get("calling_convention"),
                pseudocode,
                sha256_text(pseudocode) if pseudocode else None,
                row.get("duration_ms"),
                status if status in NATIVE_CODE_STATES else "failed",
                row.get("error"),
                canonical_json({"anchor": True}),
            ),
        )
        count += 1
    return count


_REKO_FUNCTION = re.compile(
    r"(?ms)^//\s+([0-9A-Fa-f]{8,16}):\s+([^\r\n]+)\r?\n"
    r"(.*?)(?=^//\s+[0-9A-Fa-f]{8,16}:\s+|\Z)"
)
_REKO_CRASH = re.compile(
    r"(?ms)^//\s+fn([0-9A-Fa-f]{8,16})\s+=+\s*\r?\n"
    r"(.*?)(?=^//\s+fn[0-9A-Fa-f]{8,16}\s+=+\s*$|\Z)"
)


def _import_reko(
    connection: sqlite3.Connection,
    binaries: dict[str, dict[str, Any]],
    payload: dict[str, Any],
    run_key: str,
) -> int:
    """Map Reko's address-labelled C fragments back to stable RVAs."""
    binary = binaries[payload["binary"]["binary_key"]]
    image_base = int(binary["image_base"])
    image_size = int(binary["image_size"])
    mapped: dict[int, dict[str, Any]] = {}
    crashes: dict[int, dict[str, str]] = {}
    for output in sorted(
        Path(item["path"])
        for item in payload.get("outputs", [])
        if Path(item["path"]).suffix.lower() == ".c"
    ):
        if not output.is_file():
            continue
        text = output.read_text(encoding="utf-8-sig", errors="replace").replace(
            "\r\n", "\n"
        )
        for match in _REKO_FUNCTION.finditer(text):
            address = int(match.group(1), 16)
            rva = address - image_base
            if rva < 0 or rva >= image_size:
                continue
            body = (
                f"// {match.group(1).upper()}: {match.group(2)}\n"
                f"{match.group(3).rstrip()}\n"
            )
            current = mapped.get(rva)
            if current is None or len(body) > len(current["pseudocode"]):
                mapped[rva] = {
                    "prototype": match.group(2).strip(),
                    "pseudocode": body,
                    "source": output.resolve().as_posix(),
                }
    for output in sorted(
        Path(item["path"])
        for item in payload.get("outputs", [])
        if Path(item["path"]).name.lower() == "analysis_99_crash.txt"
    ):
        if not output.is_file():
            continue
        text = output.read_text(encoding="utf-8-sig", errors="replace").replace(
            "\r\n", "\n"
        )
        for match in _REKO_CRASH.finditer(text):
            address = int(match.group(1), 16)
            rva = address - image_base
            if rva < 0 or rva >= image_size:
                continue
            details = match.group(2).strip()
            error = next(
                (
                    line.strip()
                    for line in details.splitlines()
                    if line.strip() and not line.lstrip().startswith("//")
                ),
                "Reko function analysis crashed",
            )
            crashes[rva] = {
                "error": error,
                "source": output.resolve().as_posix(),
                "details_sha256": sha256_text(details),
            }
    for rva, item in sorted(mapped.items()):
        key = _upsert_function(
            connection,
            binary=binary,
            entry_rva=rva,
            end_rva=None,
            size=None,
            byte_sha256=None,
            mnemonic_sha256=None,
            engine="reko",
            kind="function",
            state="candidate",
            evidence={"source": item["source"], "address_labelled": True},
        )
        _insert_name(
            connection,
            key,
            f"fn{image_base + rva:X}",
            source_kind="reko_address_label",
            source_locator=item["source"],
            primary=False,
            state="candidate",
        )
        pseudocode = item["pseudocode"]
        connection.execute(
            """
            INSERT OR REPLACE INTO code_decompilations(
                decompilation_key,function_key,run_key,engine_id,prototype,
                calling_convention,pseudocode,pseudocode_sha256,duration_ms,
                status,error,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("code-decompilation", key, run_key),
                key,
                run_key,
                "reko",
                item["prototype"],
                None,
                pseudocode,
                sha256_text(pseudocode),
                None,
                "candidate",
                None,
                canonical_json(
                    {
                        "source": item["source"],
                        "mapping_state": "address_labelled",
                    }
                ),
            ),
        )
    for rva, item in sorted(crashes.items()):
        key = _upsert_function(
            connection,
            binary=binary,
            entry_rva=rva,
            end_rva=None,
            size=None,
            byte_sha256=None,
            mnemonic_sha256=None,
            engine="reko",
            kind="function",
            state="candidate",
            evidence={
                "source": item["source"],
                "function_analysis_crash": True,
            },
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO code_decompilations(
                decompilation_key,function_key,run_key,engine_id,prototype,
                calling_convention,pseudocode,pseudocode_sha256,duration_ms,
                status,error,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("code-decompilation", key, run_key),
                key,
                run_key,
                "reko",
                None,
                None,
                None,
                None,
                None,
                "failed",
                item["error"],
                canonical_json(
                    {
                        "source": item["source"],
                        "function_analysis_crash": True,
                        "details_sha256": item["details_sha256"],
                    }
                ),
            ),
        )
    return len(set(mapped) | set(crashes))


def _import_whole_module_vote(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    run_key: str,
) -> int:
    """Record Reko/rev.ng as a module vote without inventing RVA mappings."""
    functions = list(
        connection.execute(
            "SELECT function_key FROM code_functions WHERE binary_key=?",
            (payload["binary"]["binary_key"],),
        )
    )
    status = "not_scheduled"
    if payload["status"] == "confirmed":
        status = "opaque"
    elif payload["status"] in NATIVE_CODE_STATES:
        status = payload["status"]
    for row in functions:
        key = str(row["function_key"])
        connection.execute(
            """
            INSERT OR IGNORE INTO code_decompilations(
                decompilation_key,function_key,run_key,engine_id,prototype,
                calling_convention,pseudocode,pseudocode_sha256,duration_ms,
                status,error,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                stable_key("code-decompilation", key, run_key),
                key,
                run_key,
                payload["engine"]["id"],
                None,
                None,
                None,
                None,
                None,
                status,
                (
                    "Whole-module output has not yet been mapped to this RVA"
                    if status == "opaque"
                    else payload.get("stderr")
                ),
                canonical_json(
                    {
                        "whole_module_vote": True,
                        "mapping_state": "pending_rva_mapping",
                    }
                ),
            ),
        )
    return len(functions)


def _insert_anchor_links(
    connection: sqlite3.Connection,
    config: NativeCodeConfig,
) -> int:
    if not config.anchors_path.is_file():
        build_anchor_inventory(config)
    anchors = json.loads(config.anchors_path.read_text(encoding="utf-8"))
    count = 0
    for anchor in anchors["anchors"]:
        key = function_key(anchor["binary_key"], int(anchor["entry_rva"]))
        if not connection.execute(
            "SELECT 1 FROM code_functions WHERE function_key=?", (key,)
        ).fetchone():
            continue
        for locator in anchor["locators"]:
            link_key = stable_key(
                "code-evidence",
                key,
                locator["scope_key"],
                locator["consumer_key"],
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO code_evidence_links(
                    evidence_link_key,function_key,scope_key,relation,
                    source_locator,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    link_key,
                    key,
                    locator["scope_key"],
                    "native_consumer",
                    locator["locator"],
                    locator["state"],
                    canonical_json(locator),
                ),
            )
            _insert_name(
                connection,
                key,
                locator["name"],
                source_kind="confirmed_forensic_consumer",
                source_locator=locator["consumer_key"],
                primary=True,
                state=locator["state"],
                evidence={"scope_key": locator["scope_key"]},
            )
            count += 1
    return count


def _apply_native_export_names(connection: sqlite3.Connection) -> int:
    count = 0
    for row in connection.execute(
        """
        SELECT f.function_key,e.symbol_name,e.export_key
        FROM code_exports e
        JOIN code_functions f
          ON f.binary_key=e.binary_key AND f.entry_rva=e.rva
        WHERE e.symbol_name IS NOT NULL AND e.symbol_name<>''
        ORDER BY f.function_key,e.symbol_name
        """
    ):
        _insert_name(
            connection,
            str(row["function_key"]),
            str(row["symbol_name"]),
            source_kind="pe_export",
            source_locator=str(row["export_key"]),
            primary=True,
            state="confirmed",
            evidence={"native_export": True},
        )
        count += 1
    return count


def _infer_vtable_this_offsets(connection: sqlite3.Connection) -> int:
    """Recover candidate class fields from methods already tied to a vtable."""
    inserted = 0
    for row in connection.execute(
        """
        SELECT DISTINCT v.type_key,d.function_key,d.pseudocode
        FROM code_vtable_slots s
        JOIN code_vtables v ON v.vtable_key=s.vtable_key
        JOIN code_decompilations d
          ON d.function_key=s.target_function_key
        WHERE v.type_key IS NOT NULL
          AND d.engine_id='ghidra'
          AND d.pseudocode IS NOT NULL
        ORDER BY v.type_key,d.function_key
        """
    ):
        offsets = sorted(
            {
                int(match.group(1), 0)
                for match in _THIS_OFFSET.finditer(str(row["pseudocode"]))
                if int(match.group(1), 0) <= 0x100000
            }
        )
        for offset in offsets:
            field_key = stable_key(
                "code-field",
                row["type_key"],
                offset,
                "observed-this-offset",
            )
            before = connection.total_changes
            connection.execute(
                """
                INSERT OR IGNORE INTO code_type_fields(
                    field_key,type_key,offset,field_name,field_type,size,
                    source_locator,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    field_key,
                    row["type_key"],
                    offset,
                    f"field_0x{offset:X}",
                    "unknown",
                    None,
                    str(row["function_key"]),
                    "candidate",
                    canonical_json(
                        {
                            "method": "ghidra_this_plus_offset",
                            "function_key": row["function_key"],
                        }
                    ),
                ),
            )
            if connection.total_changes > before:
                inserted += 1
    return inserted


def _ensure_engine_matrix(
    connection: sqlite3.Connection,
    config: NativeCodeConfig,
    binaries: dict[str, dict[str, Any]],
) -> None:
    for key, binary in sorted(binaries.items()):
        required = config.required_engines.get(binary["classification"], ())
        if binary["classification"] == "game_primary" and "angr" not in required:
            required = (*required, "angr")
        if not required:
            continue
        functions = [
            str(row["function_key"])
            for row in connection.execute(
                "SELECT function_key FROM code_functions WHERE binary_key=?",
                (key,),
            )
        ]
        for engine in required:
            run = connection.execute(
                """
                SELECT run_key,status,error FROM code_engine_runs
                WHERE binary_key=? AND engine_id=?
                ORDER BY CASE scope WHEN 'full' THEN 0 ELSE 1 END,run_key
                LIMIT 1
                """,
                (key, engine),
            ).fetchone()
            if run is None:
                run_key = stable_key(
                    "code-run", key, engine, "not-installed-or-not-scheduled", "full"
                )
                connection.execute(
                    """
                    INSERT INTO code_engine_runs(
                        run_key,binary_key,engine_id,engine_version,engine_sha256,
                        scope,input_manifest_sha256,output_path,output_sha256,
                        timeout_seconds,exit_code,status,error,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_key,
                        key,
                        engine,
                        "not-recorded",
                        None,
                        "full",
                        sha256_file(config.inventory_path),
                        "",
                        None,
                        config.timeouts.get("whole_module_seconds", 0),
                        None,
                        "not_scheduled",
                        "No reproducible run manifest was found",
                        "{}",
                    ),
                )
                run_status = "not_scheduled"
                run_error = "No function-level result was mapped"
            else:
                run_key = str(run["run_key"])
                if run["status"] == "confirmed":
                    run_status = "opaque"
                    run_error = (
                        "Engine completed but no function-level result was mapped"
                    )
                elif run["status"] in {"failed", "timeout", "unsupported"}:
                    run_status = str(run["status"])
                    run_error = (
                        str(run["error"])
                        if run["error"]
                        else "Whole-module engine run did not complete"
                    )
                else:
                    run_status = "not_scheduled"
                    run_error = "No function-level result was mapped"
            for function in functions:
                present = connection.execute(
                    """
                    SELECT 1 FROM code_decompilations
                    WHERE function_key=? AND engine_id=?
                    """,
                    (function, engine),
                ).fetchone()
                if present:
                    continue
                connection.execute(
                    """
                    INSERT INTO code_decompilations(
                        decompilation_key,function_key,run_key,engine_id,
                        prototype,calling_convention,pseudocode,
                        pseudocode_sha256,duration_ms,status,error,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("code-decompilation", function, run_key),
                        function,
                        run_key,
                        engine,
                        None,
                        None,
                        None,
                        None,
                        None,
                        run_status,
                        run_error,
                        canonical_json(
                            {
                                "whole_module_vote": run_status == "opaque",
                                "mapping_state": (
                                    "function_not_recovered"
                                    if run_status == "opaque"
                                    else "no_function_result"
                                ),
                                "whole_module_failure": (
                                    run_status
                                    in {"failed", "timeout", "unsupported"}
                                )
                            }
                        ),
                    ),
                )
        if binary["classification"] == "game_primary":
            run = connection.execute(
                """
                SELECT run_key FROM code_engine_runs
                WHERE binary_key=? AND engine_id='angr'
                ORDER BY run_key LIMIT 1
                """,
                (key,),
            ).fetchone()
            if run is None:
                run_key = stable_key("code-run", key, "angr", "anchor-policy", "anchors")
                connection.execute(
                    """
                    INSERT INTO code_engine_runs(
                        run_key,binary_key,engine_id,engine_version,engine_sha256,
                        scope,input_manifest_sha256,output_path,output_sha256,
                        timeout_seconds,exit_code,status,error,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        run_key,
                        key,
                        "angr",
                        "9.3.1.post1",
                        None,
                        "anchors",
                        sha256_file(config.inventory_path),
                        "",
                        None,
                        config.timeouts["angr_function_seconds"],
                        None,
                        "not_scheduled",
                        "angr is intentionally scheduled only for anchors/blockers",
                        canonical_json({"policy": "anchors_and_blockers"}),
                    ),
                )


def _build_equivalences(connection: sqlite3.Connection) -> int:
    count = 0

    def add(
        left: str,
        right: str,
        method: str,
        score: float | None,
        state: str,
        evidence: dict[str, Any],
    ) -> None:
        nonlocal count
        key = stable_key("code-equivalence", left, right, method)
        before = connection.total_changes
        connection.execute(
            """
            INSERT OR IGNORE INTO code_equivalences(
                equivalence_key,left_function_key,right_function_key,method,
                rank_score,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (key, left, right, method, score, state, canonical_json(evidence)),
        )
        if connection.total_changes > before:
            count += 1

    rows = connection.execute(
        """
        SELECT scope_key,
               GROUP_CONCAT(DISTINCT function_key) AS functions
        FROM code_evidence_links
        GROUP BY scope_key
        HAVING COUNT(DISTINCT function_key)>=2
        ORDER BY scope_key
        """
    )
    for row in rows:
        functions = sorted(str(row["functions"]).split(","))
        left = next((value for value in functions if value.startswith("fn:x86:")), None)
        right = next((value for value in functions if value.startswith("fn:x64:")), None)
        if left is None or right is None:
            continue
        add(
            left,
            right,
            "shared_confirmed_forensic_scope",
            1.0,
            "confirmed",
            {"scope_key": row["scope_key"]},
        )

    # Exact, non-default names are independent architecture votes.  They do
    # not propagate names; they only create a provenance-bearing relation.
    by_name: dict[str, dict[str, set[str]]] = {}
    for row in connection.execute(
        """
        SELECT lower(n.name) AS normalized,b.architecture,f.function_key,n.name
        FROM code_names n
        JOIN code_functions f ON f.function_key=n.function_key
        JOIN code_binaries b ON b.binary_key=f.binary_key
        WHERE b.module_name='x2game.dll'
          AND b.architecture IN ('x86','x64')
          AND n.state IN ('confirmed','corroborated')
        ORDER BY normalized,b.architecture,f.function_key
        """
    ):
        name = str(row["name"])
        if _DEFAULT_NAME.match(name) or name.lower().startswith(("fn", "sub_")):
            continue
        by_name.setdefault(str(row["normalized"]), {}).setdefault(
            str(row["architecture"]), set()
        ).add(str(row["function_key"]))
    for name, architectures in sorted(by_name.items()):
        lefts = architectures.get("x86", set())
        rights = architectures.get("x64", set())
        if len(lefts) == len(rights) == 1:
            add(
                next(iter(lefts)),
                next(iter(rights)),
                "shared_nondefault_name",
                0.90,
                "corroborated",
                {"normalized_name": name},
            )

    # A unique normalized instruction signature is useful but remains a
    # candidate because compiler/codegen differences can create collisions.
    signatures: dict[str, dict[str, list[str]]] = {}
    for row in connection.execute(
        """
        SELECT f.mnemonic_sha256,b.architecture,f.function_key
        FROM code_functions f
        JOIN code_binaries b ON b.binary_key=f.binary_key
        WHERE b.module_name='x2game.dll'
          AND f.mnemonic_sha256 IS NOT NULL
        ORDER BY f.mnemonic_sha256,b.architecture,f.function_key
        """
    ):
        signatures.setdefault(str(row["mnemonic_sha256"]), {}).setdefault(
            str(row["architecture"]), []
        ).append(str(row["function_key"]))
    for signature, architectures in sorted(signatures.items()):
        lefts = architectures.get("x86", [])
        rights = architectures.get("x64", [])
        if len(lefts) == len(rights) == 1:
            add(
                lefts[0],
                rights[0],
                "unique_normalized_mnemonic_hash",
                0.65,
                "candidate",
                {"mnemonic_sha256": signature},
            )

    # Shared string/SQL evidence is architecture-neutral.  Require a unique
    # signature in each architecture to avoid combinatorial false matches.
    string_sets: dict[str, dict[str, list[str]]] = {}
    for row in connection.execute(
        """
        SELECT f.function_key,b.architecture,
               GROUP_CONCAT(s.value,char(10)) AS values_text,
               COUNT(DISTINCT s.value) AS value_count
        FROM code_functions f
        JOIN code_binaries b ON b.binary_key=f.binary_key
        JOIN code_function_strings fs ON fs.function_key=f.function_key
        JOIN code_strings s ON s.string_key=fs.string_key
        WHERE b.module_name='x2game.dll'
        GROUP BY f.function_key,b.architecture
        ORDER BY f.function_key
        """
    ):
        values = sorted(set(str(row["values_text"]).split("\n")))
        signature = sha256_text(canonical_json(values))
        string_sets.setdefault(signature, {}).setdefault(
            str(row["architecture"]), []
        ).append(str(row["function_key"]))
    for signature, architectures in sorted(string_sets.items()):
        lefts = architectures.get("x86", [])
        rights = architectures.get("x64", [])
        if len(lefts) == len(rights) == 1:
            add(
                lefts[0],
                rights[0],
                "unique_shared_string_set",
                0.80,
                "corroborated",
                {"string_set_sha256": signature},
            )
    return count


def _resolve_review_function(
    connection: sqlite3.Connection, identity: dict[str, Any]
) -> str:
    required = {"binary_sha256", "architecture", "rva"}
    if not required.issubset(identity):
        raise ValueError(
            "Review function identity requires binary_sha256, architecture and rva"
        )
    sha256 = str(identity["binary_sha256"]).upper()
    architecture = str(identity["architecture"])
    rva = (
        int(identity["rva"], 0)
        if isinstance(identity["rva"], str)
        else int(identity["rva"])
    )
    row = connection.execute(
        """
        SELECT f.function_key
        FROM code_functions f
        JOIN code_binaries b ON b.binary_key=f.binary_key
        WHERE upper(b.sha256)=? AND b.architecture=? AND f.entry_rva=?
        """,
        (sha256, architecture, rva),
    ).fetchone()
    if row is None:
        raise ValueError(
            f"Review decision references an absent function: "
            f"{architecture} {sha256} RVA 0x{rva:X}"
        )
    return str(row[0])


def _apply_review_overrides(
    connection: sqlite3.Connection, config: NativeCodeConfig
) -> dict[str, int]:
    overlay = _load_review_overrides(config)
    allowed_kinds = {
        "name",
        "equivalence",
        "boundary",
        "type",
        "indirect_dispatch",
    }
    allowed_states = {"confirmed", "corroborated", "candidate", "ambiguous"}
    seen: set[str] = set()
    counts = {"decisions": 0, "names": 0, "equivalences": 0}
    for item in overlay["decisions"]:
        decision_id = str(item.get("decision_id") or "").strip()
        kind = str(item.get("kind") or "").strip()
        state = str(item.get("state") or "").strip()
        source = str(item.get("source_locator") or "").strip()
        evidence = item.get("evidence")
        payload = item.get("payload", {})
        if not decision_id or decision_id in seen:
            raise ValueError(f"Missing or duplicate review decision id: {decision_id!r}")
        seen.add(decision_id)
        if kind not in allowed_kinds:
            raise ValueError(f"Unsupported review decision kind: {kind}")
        if state not in allowed_states:
            raise ValueError(f"Unsupported review decision state: {state}")
        if not source:
            raise ValueError(f"Review decision lacks source locator: {decision_id}")
        if not evidence or not isinstance(evidence, (list, dict)):
            raise ValueError(f"Review decision lacks evidence: {decision_id}")
        if not isinstance(payload, dict):
            raise ValueError(f"Review decision payload must be an object: {decision_id}")
        function = _resolve_review_function(connection, item.get("function", {}))
        related = None
        if kind == "equivalence":
            related = _resolve_review_function(
                connection, item.get("related_function", {})
            )
            if function == related:
                raise ValueError(f"Self equivalence is invalid: {decision_id}")
        decision_key = stable_key("code-review-decision", decision_id)
        connection.execute(
            """
            INSERT INTO code_review_decisions(
                decision_key,decision_kind,function_key,related_function_key,
                state,source_locator,payload_json,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                decision_key,
                kind,
                function,
                related,
                state,
                source,
                canonical_json(payload),
                canonical_json(evidence),
            ),
        )
        counts["decisions"] += 1
        if kind == "name":
            name = str(payload.get("name") or "").strip()
            if not name or _DEFAULT_NAME.match(name):
                raise ValueError(f"Review name is empty/default: {decision_id}")
            _insert_name(
                connection,
                function=function,
                name=name,
                namespace=payload.get("namespace"),
                source_kind="review_overlay",
                source_locator=source,
                primary=bool(payload.get("primary", True)),
                state=state,
                evidence={
                    "decision_id": decision_id,
                    "evidence": evidence,
                    "overlay_sha256": sha256_file(config.review_overrides_path),
                },
            )
            counts["names"] += 1
        elif kind == "equivalence":
            left, right = sorted((function, str(related)))
            key = stable_key(
                "code-equivalence", left, right, "review_overlay"
            )
            connection.execute(
                """
                INSERT INTO code_equivalences(
                    equivalence_key,left_function_key,right_function_key,
                    method,rank_score,state,evidence_json
                ) VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(equivalence_key) DO UPDATE SET
                    rank_score=excluded.rank_score,
                    state=excluded.state,
                    evidence_json=excluded.evidence_json
                """,
                (
                    key,
                    left,
                    right,
                    "review_overlay",
                    payload.get("rank_score"),
                    state,
                    canonical_json(
                        {
                            "decision_id": decision_id,
                            "source_locator": source,
                            "evidence": evidence,
                        }
                    ),
                ),
            )
            counts["equivalences"] += 1
    return counts


def _build_review_queue(
    connection: sqlite3.Connection,
    progress: Callable[[int, int, str], None] | None = None,
    *,
    chunk_size: int = 5000,
) -> dict[str, int]:
    if chunk_size < 1:
        raise ValueError("Review queue chunk size must be positive")
    connection.create_function(
        "aa8_stable_key", -1, stable_key, deterministic=True
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_code_evidence_function
        ON code_evidence_links(function_key)
        """
    )
    connection.commit()

    group_marker = "stage15_review_failure_groups"
    group_row = connection.execute(
        "SELECT value FROM metadata WHERE key=?", (group_marker,)
    ).fetchone()
    if group_row is None:
        connection.execute("DELETE FROM code_review_groups")
        group_count = 0
        for row in connection.execute(
            """
            SELECT r.run_key,r.engine_id,r.status,r.error,
                   (
                       SELECT COUNT(*)
                       FROM code_functions f
                       WHERE f.binary_key=r.binary_key
                   ) AS affected_functions
            FROM code_engine_runs r
            WHERE r.status IN ('failed','timeout','unsupported')
            ORDER BY r.engine_id,r.run_key
            """
        ):
            error = str(row["error"] or "")
            signature = sha256_text(
                canonical_json(
                    {
                        "engine": row["engine_id"],
                        "status": row["status"],
                        "error": error[:4000],
                    }
                )
            )
            connection.execute(
                """
                INSERT INTO code_review_groups(
                    review_group_key,engine_id,run_key,reason_code,
                    affected_functions,priority,state,error_signature,evidence_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key(
                        "code-review-group", row["run_key"], signature
                    ),
                    row["engine_id"],
                    row["run_key"],
                    "engine_run_failure",
                    int(row["affected_functions"]),
                    100,
                    "candidate",
                    signature,
                    canonical_json(
                        {
                            "run_status": row["status"],
                            "error": error,
                            "grouping": "one row per failed engine run",
                        }
                    ),
                ),
            )
            group_count += 1
        connection.execute(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            (group_marker, canonical_json({"count": group_count})),
        )
        connection.commit()
    else:
        group_count = int(json.loads(str(group_row[0]))["count"])

    reason_queries: tuple[tuple[str, int, str, str], ...] = (
        (
            "decompiler_failure",
            100,
            "{}",
            """
            EXISTS(
                SELECT 1
                FROM code_decompilations d
                JOIN code_engine_runs r ON r.run_key=d.run_key
                WHERE d.function_key=f.function_key
                  AND d.status IN ('failed','timeout','opaque')
                  AND COALESCE(
                      json_extract(d.evidence_json,'$.whole_module_vote'),0
                  )=0
                  AND r.status NOT IN ('failed','timeout','unsupported')
            )
            """,
        ),
        (
            "function_boundary_disagreement",
            95,
            "{}",
            """
            EXISTS(
                SELECT 1 FROM code_decompilations d
                WHERE d.function_key=f.function_key
                  AND d.engine_id='rizin'
                  AND json_extract(d.evidence_json,'$.end_rva') IS NOT NULL
                  AND json_extract(d.evidence_json,'$.end_rva')<>f.end_rva
            )
            """,
        ),
        (
            "anchor_missing_engine_vote",
            90,
            "{}",
            """
            EXISTS(
                SELECT 1 FROM code_evidence_links l
                WHERE l.function_key=f.function_key
            )
            AND EXISTS(
                SELECT 1 FROM code_decompilations d
                WHERE d.function_key=f.function_key
                  AND d.status='not_scheduled'
            )
            """,
        ),
        (
            "confirmed_consumer_without_calls",
            80,
            "{}",
            """
            EXISTS(
                SELECT 1 FROM code_evidence_links l
                WHERE l.function_key=f.function_key
            )
            AND NOT EXISTS(
                SELECT 1 FROM code_calls c
                WHERE c.caller_function_key=f.function_key
            )
            AND NOT EXISTS(
                SELECT 1 FROM code_review_decisions rd
                WHERE rd.function_key=f.function_key
                  AND rd.decision_kind='indirect_dispatch'
                  AND rd.state IN ('confirmed','corroborated')
            )
            """,
        ),
        (
            "indirect_call_requires_resolution",
            85,
            "{}",
            """
            EXISTS(
                SELECT 1 FROM code_calls c
                WHERE c.caller_function_key=f.function_key
                  AND c.call_kind='indirect'
            )
            """,
        ),
        (
            "architecture_equivalence_requires_review",
            70,
            "{}",
            """
            (
                EXISTS(
                    SELECT 1 FROM code_equivalences e
                    WHERE e.left_function_key=f.function_key
                      AND e.state IN ('candidate','ambiguous')
                )
                OR EXISTS(
                    SELECT 1 FROM code_equivalences e
                    WHERE e.right_function_key=f.function_key
                      AND e.state IN ('candidate','ambiguous')
                )
            )
            AND NOT EXISTS(
                SELECT 1 FROM code_review_decisions rd
                WHERE rd.function_key=f.function_key
                  AND rd.decision_kind='equivalence'
                  AND json_extract(
                      rd.payload_json,'$.review_outcome'
                  )='retain_candidate'
            )
            """,
        ),
        (
            "incompatible_type_requires_review",
            88,
            "{}",
            """
            EXISTS(
                SELECT 1 FROM code_review_decisions rd
                WHERE rd.function_key=f.function_key
                  AND rd.decision_kind='type'
                  AND rd.state='ambiguous'
            )
            """,
        ),
        (
            "opaque_critical",
            92,
            canonical_json({"consumer_linked": True, "actionable": True}),
            """
            EXISTS(
                SELECT 1 FROM code_evidence_links l
                WHERE l.function_key=f.function_key
            )
            AND EXISTS(
                SELECT 1
                FROM code_regions opaque
                WHERE opaque.binary_key=f.binary_key
                  AND opaque.region_kind='opaque'
                  AND (
                      EXISTS(
                          SELECT 1 FROM code_calls c
                          WHERE c.caller_function_key=f.function_key
                            AND c.target_rva>=opaque.start_rva
                            AND c.target_rva<opaque.end_rva
                      )
                      OR EXISTS(
                          SELECT 1 FROM code_data_references d
                          WHERE d.function_key=f.function_key
                            AND d.to_rva>=opaque.start_rva
                            AND d.to_rva<opaque.end_rva
                      )
                  )
            )
            """,
        ),
    )

    total_functions = int(
        connection.execute("SELECT COUNT(*) FROM code_functions").fetchone()[0]
    )
    processed = 0
    binaries = list(
        connection.execute(
            """
            SELECT b.binary_key,b.module_name,b.architecture,COUNT(*) AS functions
            FROM code_binaries b
            JOIN code_functions f ON f.binary_key=b.binary_key
            GROUP BY b.binary_key,b.module_name,b.architecture
            ORDER BY b.binary_key
            """
        )
    )
    for binary in binaries:
        binary_key_value = str(binary["binary_key"])
        checkpoint_key = f"stage15_review_checkpoint:{binary_key_value}"
        checkpoint_row = connection.execute(
            "SELECT value FROM metadata WHERE key=?", (checkpoint_key,)
        ).fetchone()
        checkpoint = (
            json.loads(str(checkpoint_row[0])) if checkpoint_row else None
        )
        if checkpoint and bool(checkpoint.get("complete")):
            processed += int(binary["functions"])
            if progress:
                progress(
                    processed,
                    total_functions,
                    f"resumed {binary['module_name']} {binary['architecture']}",
                )
            continue
        if checkpoint is None:
            connection.execute(
                """
                DELETE FROM code_review_queue
                WHERE function_key IN (
                    SELECT function_key FROM code_functions WHERE binary_key=?
                )
                """,
                (binary_key_value,),
            )
            connection.commit()
            last_function_key = ""
            processed_in_binary = 0
        else:
            last_function_key = str(
                checkpoint.get("last_function_key") or ""
            )
            processed_in_binary = int(
                checkpoint.get("processed_functions") or 0
            )
            processed += processed_in_binary

        while True:
            function_rows = connection.execute(
                """
                SELECT function_key
                FROM code_functions
                WHERE binary_key=? AND function_key>?
                ORDER BY function_key
                LIMIT ?
                """,
                (binary_key_value, last_function_key, chunk_size),
            ).fetchall()
            if not function_rows:
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                    (
                        checkpoint_key,
                        canonical_json(
                            {
                                "complete": True,
                                "last_function_key": last_function_key,
                                "processed_functions": processed_in_binary,
                            }
                        ),
                    ),
                )
                connection.commit()
                break
            first_function_key = str(function_rows[0]["function_key"])
            chunk_last_function_key = str(function_rows[-1]["function_key"])
            try:
                for reason, priority, evidence_json, predicate in reason_queries:
                    connection.execute(
                        f"""
                        INSERT OR IGNORE INTO code_review_queue(
                            review_key,function_key,reason_code,priority,
                            state,evidence_json
                        )
                        SELECT
                            aa8_stable_key(
                                'code-review',f.function_key,'{reason}'
                            ),
                            f.function_key,'{reason}',{priority},
                            'candidate',?
                        FROM code_functions f
                        WHERE f.binary_key=?
                          AND f.function_key>=?
                          AND f.function_key<=?
                          AND ({predicate})
                        """,
                        (
                            evidence_json,
                            binary_key_value,
                            first_function_key,
                            chunk_last_function_key,
                        ),
                    )
                processed_in_binary += len(function_rows)
                processed += len(function_rows)
                last_function_key = chunk_last_function_key
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                    (
                        checkpoint_key,
                        canonical_json(
                            {
                                "complete": False,
                                "last_function_key": last_function_key,
                                "processed_functions": processed_in_binary,
                            }
                        ),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            if progress:
                progress(
                    processed,
                    total_functions,
                    (
                        f"{binary['module_name']} {binary['architecture']} "
                        f"{processed_in_binary}/{binary['functions']}"
                    ),
                )

    count = int(
        connection.execute("SELECT COUNT(*) FROM code_review_queue").fetchone()[0]
    )
    return {"function_rows": count, "failure_groups": group_count}


def _build_search(
    connection: sqlite3.Connection,
    progress: Callable[[int, int, str], None] | None = None,
    *,
    chunk_size: int = 1000,
) -> int:
    if chunk_size < 1:
        raise ValueError("Search index chunk size must be positive")
    total = int(
        connection.execute("SELECT COUNT(*) FROM code_functions").fetchone()[0]
    )
    processed = 0
    binaries = list(
        connection.execute(
            """
            SELECT b.binary_key,b.module_name,b.architecture,COUNT(*) AS functions
            FROM code_binaries b
            JOIN code_functions f ON f.binary_key=b.binary_key
            GROUP BY b.binary_key,b.module_name,b.architecture
            ORDER BY b.binary_key
            """
        )
    )
    for binary in binaries:
        binary_key_value = str(binary["binary_key"])
        checkpoint_key = f"stage15_search_checkpoint:{binary_key_value}"
        checkpoint_row = connection.execute(
            "SELECT value FROM metadata WHERE key=?", (checkpoint_key,)
        ).fetchone()
        checkpoint = (
            json.loads(str(checkpoint_row[0])) if checkpoint_row else None
        )
        if checkpoint and bool(checkpoint.get("complete")):
            processed += int(binary["functions"])
            if progress:
                progress(
                    processed,
                    total,
                    f"resumed {binary['module_name']} {binary['architecture']}",
                )
            continue
        if checkpoint is None:
            connection.execute(
                """
                DELETE FROM code_search
                WHERE function_key IN (
                    SELECT function_key FROM code_functions WHERE binary_key=?
                )
                """,
                (binary_key_value,),
            )
            connection.commit()
            last_function_key = ""
            processed_in_binary = 0
        else:
            last_function_key = str(
                checkpoint.get("last_function_key") or ""
            )
            processed_in_binary = int(
                checkpoint.get("processed_functions") or 0
            )
            processed += processed_in_binary

        while True:
            rows = connection.execute(
                """
                SELECT f.function_key,b.module_name,b.architecture,
                       COALESCE((
                           SELECT n.name FROM code_names n
                           WHERE n.function_key=f.function_key
                           ORDER BY n.primary_name DESC,
                                    CASE n.state
                                      WHEN 'confirmed' THEN 0
                                      WHEN 'corroborated' THEN 1
                                      ELSE 2 END,
                                    n.name
                           LIMIT 1
                       ),printf('FUN_%x',b.image_base+f.entry_rva))
                           AS primary_name,
                       COALESCE((
                           SELECT GROUP_CONCAT(s.value,char(10))
                           FROM code_function_strings fs
                           JOIN code_strings s
                             ON s.string_key=fs.string_key
                           WHERE fs.function_key=f.function_key
                       ),'') AS strings,
                       COALESCE((
                           SELECT GROUP_CONCAT(
                               i.mnemonic || ' ' || i.instruction_text,
                               char(10)
                           )
                           FROM code_instructions i
                           WHERE i.function_key=f.function_key
                       ),'') AS instructions,
                       COALESCE((
                           SELECT GROUP_CONCAT(d.pseudocode,char(10))
                           FROM code_decompilations d
                           WHERE d.function_key=f.function_key
                             AND d.pseudocode IS NOT NULL
                       ),'') AS pseudocode
                FROM code_functions f
                JOIN code_binaries b ON b.binary_key=f.binary_key
                WHERE f.binary_key=? AND f.function_key>?
                ORDER BY f.function_key
                LIMIT ?
                """,
                (binary_key_value, last_function_key, chunk_size),
            ).fetchall()
            if not rows:
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                    (
                        checkpoint_key,
                        canonical_json(
                            {
                                "complete": True,
                                "last_function_key": last_function_key,
                                "processed_functions": processed_in_binary,
                            }
                        ),
                    ),
                )
                connection.commit()
                break
            try:
                connection.executemany(
                    """
                    INSERT INTO code_search(
                        function_key,module_name,architecture,primary_name,
                        strings,instructions,pseudocode
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (tuple(row) for row in rows),
                )
                processed_in_binary += len(rows)
                processed += len(rows)
                last_function_key = str(rows[-1]["function_key"])
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                    (
                        checkpoint_key,
                        canonical_json(
                            {
                                "complete": False,
                                "last_function_key": last_function_key,
                                "processed_functions": processed_in_binary,
                            }
                        ),
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            if progress:
                progress(
                    processed,
                    total,
                    (
                        f"{binary['module_name']} {binary['architecture']} "
                        f"{processed_in_binary}/{binary['functions']}"
                    ),
                )
    return int(connection.execute("SELECT COUNT(*) FROM code_search").fetchone()[0])


def _build_executable_regions(
    connection: sqlite3.Connection,
    binaries: dict[str, dict[str, Any]],
    progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, int]:
    counts = {"function": 0, "thunk": 0, "padding": 0, "opaque": 0}
    enabled = [
        item
        for item in sorted(binaries.values(), key=lambda value: value["binary_key"])
        if item["analysis_enabled"]
    ]

    def insert_region(
        *,
        binary: dict[str, Any],
        section_key: str,
        function: str | None,
        start: int,
        end: int,
        kind: str,
        state: str,
        evidence: dict[str, Any],
    ) -> None:
        if end <= start:
            return
        key = stable_key("code-region", binary["binary_key"], start, end, kind)
        connection.execute(
            """
            INSERT OR IGNORE INTO code_regions(
                region_key,binary_key,section_key,function_key,start_rva,
                end_rva,region_kind,state,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                key,
                binary["binary_key"],
                section_key,
                function,
                start,
                end,
                kind,
                state,
                canonical_json(evidence),
            ),
        )
        counts[kind] += 1
        if kind == "opaque":
            connection.execute(
                """
                INSERT OR IGNORE INTO opaque_regions(
                    opaque_key,surface,locator,blocker_code,reason,
                    searched_evidence_json,source_stage,state
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    stable_key("opaque", binary["binary_key"], start, end),
                    binary["module_name"],
                    f"RVA 0x{start:X}-0x{end:X}",
                    "unclassified_executable_bytes",
                    "Executable bytes are neither a recovered function nor padding",
                    canonical_json(evidence),
                    15,
                    "opaque",
                ),
            )

    for ordinal, binary in enumerate(enabled, start=1):
        functions = [
            dict(row)
            for row in connection.execute(
                """
                SELECT function_key,entry_rva,end_rva,size,function_kind,state
                FROM code_functions WHERE binary_key=?
                ORDER BY entry_rva,COALESCE(end_rva,entry_rva+COALESCE(size,1))
                """,
                (binary["binary_key"],),
            )
        ]
        if not functions:
            if progress:
                progress(
                    ordinal,
                    len(enabled),
                    f"{binary['module_name']} {binary['architecture']}",
                )
            continue
        image = PeImage(Path(binary["source_path"]))
        for section in binary["sections"]:
            if not section["executable"]:
                continue
            section_start = int(section["rva"])
            section_end = section_start + max(
                int(section["virtual_size"]), int(section["raw_size"])
            )
            section_key = stable_key(
                "code-section", binary["binary_key"], section["ordinal"]
            )

            def section_bytes(start: int, end: int) -> bytes:
                delta = start - section_start
                raw_size = int(section["raw_size"])
                if delta < 0 or delta >= raw_size:
                    return b""
                length = min(end - start, raw_size - delta)
                offset = int(section["raw_offset"]) + delta
                return image.data[offset : offset + length]

            selected = [
                item
                for item in functions
                if section_start <= int(item["entry_rva"]) < section_end
            ]
            cursor = section_start
            for item in selected:
                start = int(item["entry_rva"])
                end = int(item["end_rva"] or start + int(item["size"] or 1))
                end = min(max(end, start + 1), section_end)
                if start > cursor:
                    raw = section_bytes(cursor, start)
                    padding = not raw or set(raw).issubset({0x00, 0x90, 0xCC})
                    insert_region(
                        binary=binary,
                        section_key=section_key,
                        function=None,
                        start=cursor,
                        end=start,
                        kind="padding" if padding else "opaque",
                        state="confirmed" if padding else "opaque",
                        evidence={"section": section["name"]},
                    )
                visible_start = max(cursor, start)
                if end > visible_start:
                    kind = (
                        "thunk"
                        if str(item["function_kind"]).lower() == "thunk"
                        else "function"
                    )
                    insert_region(
                        binary=binary,
                        section_key=section_key,
                        function=str(item["function_key"]),
                        start=visible_start,
                        end=end,
                        kind=kind,
                        state=str(item["state"]),
                        evidence={
                            "section": section["name"],
                            "declared_entry_rva": start,
                            "overlap_trimmed": visible_start != start,
                        },
                    )
                cursor = max(cursor, end)
            if cursor < section_end:
                raw = section_bytes(cursor, section_end)
                padding = not raw or set(raw).issubset({0x00, 0x90, 0xCC})
                insert_region(
                    binary=binary,
                    section_key=section_key,
                    function=None,
                    start=cursor,
                    end=section_end,
                    kind="padding" if padding else "opaque",
                    state="confirmed" if padding else "opaque",
                    evidence={"section": section["name"]},
                )
        if progress:
            progress(
                ordinal,
                len(enabled),
                f"{binary['module_name']} {binary['architecture']}",
            )
    return counts


def _stage_counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = [
        str(row[0])
        for row in connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
              AND name LIKE 'code_%'
              AND name NOT LIKE 'code_search_%'
            ORDER BY name
            """
        )
    ]
    return {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in tables
    }


def validate_native_code_database(
    path: Path,
    *,
    tuning: Stage15BuildTuning | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    connection = sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro&immutable=1", uri=True
    )
    connection.row_factory = sqlite3.Row
    if tuning:
        connection.execute(f"PRAGMA cache_size = {-tuning.cache_mb * 1024}")
        connection.execute(f"PRAGMA mmap_size = {tuning.mmap_mb * 1024 * 1024}")
        connection.execute(f"PRAGMA threads = {tuning.sqlite_threads}")
    validation_step = ["quick_check"]
    if progress:
        connection.set_progress_handler(
            lambda: (progress(validation_step[0]), 0)[1],
            100000,
        )
    try:
        if progress:
            progress("quick_check")
        quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        validation_step[0] = "integrity_check"
        if progress:
            progress("integrity_check")
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        validation_step[0] = "foreign_key_check"
        if progress:
            progress("foreign_key_check")
        foreign_keys = list(connection.execute("PRAGMA foreign_key_check"))
        required = {
            "code_binaries",
            "code_sections",
            "code_regions",
            "code_functions",
            "code_names",
            "code_instructions",
            "code_calls",
            "code_strings",
            "code_types",
            "code_vtables",
            "code_engine_runs",
            "code_decompilations",
            "code_equivalences",
            "code_evidence_links",
            "code_dynamic_runs",
            "code_dynamic_coverage",
            "code_review_queue",
            "code_review_groups",
            "code_review_decisions",
            "code_search",
        }
        present = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            )
        }
        missing = sorted(required - present)
        invalid_states = {}
        for table, column in (
            ("code_binaries", "state"),
            ("code_regions", "state"),
            ("code_functions", "state"),
            ("code_names", "state"),
            ("code_engine_runs", "status"),
            ("code_decompilations", "status"),
            ("code_equivalences", "state"),
            ("code_dynamic_runs", "status"),
            ("code_dynamic_coverage", "state"),
            ("code_review_queue", "state"),
            ("code_review_groups", "state"),
            ("code_review_decisions", "state"),
        ):
            values = [
                str(row[0])
                for row in connection.execute(
                    f"SELECT DISTINCT {column} FROM {table} ORDER BY {column}"
                )
                if str(row[0]) not in NATIVE_CODE_STATES
            ]
            if values:
                invalid_states[table] = values
        anticheat_runs = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM code_engine_runs r
                JOIN code_binaries b ON b.binary_key=r.binary_key
                WHERE b.classification='excluded_anticheat'
                """
            ).fetchone()[0]
        )
        invalid_dynamic_runs = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM code_dynamic_runs
                WHERE network_scope NOT IN ('offline','local_only')
                   OR anticheat_state<>'not_running'
                """
            ).fetchone()[0]
        )
        missing_engine_results = int(
            connection.execute(
                """
                WITH required(classification,engine_id) AS (
                    VALUES
                    ('game_primary','ghidra'),
                    ('game_primary','rizin'),
                    ('game_primary','reko'),
                    ('game_primary','revng'),
                    ('game_primary','angr'),
                    ('game_support','ghidra'),
                    ('game_support','rizin'),
                    ('engine_modified','ghidra'),
                    ('engine_modified','rizin')
                )
                SELECT COUNT(*)
                FROM code_functions f
                JOIN code_binaries b ON b.binary_key=f.binary_key
                JOIN required r ON r.classification=b.classification
                WHERE NOT EXISTS(
                    SELECT 1 FROM code_decompilations d
                    WHERE d.function_key=f.function_key
                      AND d.engine_id=r.engine_id
                )
                """
            ).fetchone()[0]
        )
        incomplete_executable_sections = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM code_sections s
                WHERE s.executable=1
                  AND EXISTS(
                    SELECT 1 FROM code_functions f
                    WHERE f.binary_key=s.binary_key
                  )
                  AND COALESCE((
                    SELECT SUM(r.end_rva-r.start_rva)
                    FROM code_regions r WHERE r.section_key=s.section_key
                  ),0)<>MAX(s.virtual_size,s.raw_size)
                """
            ).fetchone()[0]
        )
        if (
            quick != "ok"
            or integrity != "ok"
            or foreign_keys
            or missing
            or invalid_states
            or anticheat_runs
            or invalid_dynamic_runs
            or missing_engine_results
            or incomplete_executable_sections
        ):
            raise RuntimeError(
                "Native corpus validation failed: "
                f"quick={quick} integrity={integrity} "
                f"foreign_keys={len(foreign_keys)} missing={missing} "
                f"invalid_states={invalid_states} anticheat_runs={anticheat_runs} "
                f"invalid_dynamic_runs={invalid_dynamic_runs} "
                f"missing_engine_results={missing_engine_results} "
                f"incomplete_executable_sections={incomplete_executable_sections}"
            )
        return {
            "quick_check": quick,
            "integrity_check": integrity,
            "foreign_key_violations": 0,
            "anticheat_engine_runs": 0,
            "invalid_dynamic_runs": 0,
            "missing_engine_results": 0,
            "incomplete_executable_sections": 0,
            "counts": _stage_counts(connection),
        }
    finally:
        connection.set_progress_handler(None, 0)
        connection.close()


def _dynamic_manifests(config: NativeCodeConfig) -> list[tuple[Path, dict[str, Any]]]:
    if not config.dynamic_root.is_dir():
        return []
    result: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(config.dynamic_root.glob("*.manifest.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != "AA8_NATIVE_COVERAGE_V1":
            raise ValueError(f"Unsupported dynamic coverage manifest: {path}")
        result.append((path, payload))
    return result


def _import_dynamic_coverage(
    connection: sqlite3.Connection,
    config: NativeCodeConfig,
    binaries: dict[str, dict[str, Any]],
) -> dict[str, int]:
    runs = hits = unmapped = 0
    for path, payload in _dynamic_manifests(config):
        if payload.get("client_build") != config.client_build:
            raise ValueError(f"Dynamic coverage belongs to another build: {path}")
        if payload.get("network_scope") not in {"offline", "local_only"}:
            raise ValueError(f"Public-network dynamic coverage rejected: {path}")
        if payload.get("anticheat_state") != "not_running":
            raise ValueError(f"Anticheat dynamic coverage rejected: {path}")
        trace = Path(str(payload["trace_path"]))
        if not trace.is_file() or sha256_file(trace) != payload["trace_sha256"]:
            raise ValueError(f"Dynamic trace evidence mismatch: {path}")
        state = str(payload.get("status", "confirmed"))
        if state not in NATIVE_CODE_STATES:
            raise ValueError(f"Unsupported dynamic coverage state: {state}")
        run_key = stable_key(
            "dynamic-run",
            payload["trace_sha256"],
            payload["scenario"],
            payload["tool"]["id"],
        )
        connection.execute(
            """
            INSERT INTO code_dynamic_runs(
                dynamic_run_key,scenario,tool_id,tool_version,trace_path,
                trace_sha256,network_scope,anticheat_state,status,evidence_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_key,
                payload["scenario"],
                payload["tool"]["id"],
                payload["tool"]["version"],
                trace.resolve().as_posix(),
                payload["trace_sha256"],
                payload["network_scope"],
                payload["anticheat_state"],
                state,
                canonical_json(
                    {
                        "manifest": path.resolve().as_posix(),
                        "manifest_sha256": sha256_file(path),
                    }
                ),
            ),
        )
        runs += 1
        for module in payload["modules"]:
            binary_key = module["binary_key"]
            if binary_key not in binaries:
                raise ValueError(f"Dynamic module absent from inventory: {binary_key}")
            if binaries[binary_key]["classification"] == "excluded_anticheat":
                raise ValueError(f"Anticheat dynamic module rejected: {binary_key}")
            for observation in module["hits"]:
                rva = int(observation["rva"])
                row = connection.execute(
                    """
                    SELECT function_key
                    FROM code_functions
                    WHERE binary_key=?
                      AND entry_rva<=?
                      AND ?<COALESCE(end_rva,entry_rva+COALESCE(size,1))
                    ORDER BY entry_rva DESC
                    LIMIT 1
                    """,
                    (binary_key, rva, rva),
                ).fetchone()
                if row is None:
                    unmapped += 1
                    connection.execute(
                        """
                        INSERT OR REPLACE INTO opaque_regions(
                            opaque_key,surface,locator,blocker_code,reason,
                            searched_evidence_json,source_stage,state
                        ) VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            stable_key("opaque", run_key, binary_key, str(rva)),
                            binaries[binary_key]["module_name"],
                            f"RVA 0x{rva:X}",
                            "dynamic_hit_without_static_function",
                            "Executed RVA is not covered by an imported static function",
                            canonical_json(
                                {
                                    "dynamic_run_key": run_key,
                                    "binary_key": binary_key,
                                    "hit_count": int(observation["hit_count"]),
                                }
                            ),
                            15,
                            "opaque",
                        ),
                    )
                    continue
                function = str(row[0])
                connection.execute(
                    """
                    INSERT INTO code_dynamic_coverage(
                        coverage_key,dynamic_run_key,function_key,hit_count,
                        first_observed_rva,state,evidence_json
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("dynamic-coverage", run_key, function, str(rva)),
                        run_key,
                        function,
                        int(observation["hit_count"]),
                        rva,
                        state,
                        canonical_json(
                            {
                                "loaded_base": int(module["loaded_base"]),
                                "module_name": module["module_name"],
                                "manifest": path.resolve().as_posix(),
                            }
                        ),
                    ),
                )
                hits += 1
    return {"runs": runs, "mapped_hits": hits, "unmapped_hits": unmapped}


def _configure_stage_15_connection(
    connection: sqlite3.Connection, tuning: Stage15BuildTuning
) -> None:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute(f"PRAGMA threads = {tuning.sqlite_threads}")
    connection.execute(f"PRAGMA cache_size = {-tuning.cache_mb * 1024}")
    connection.execute(f"PRAGMA mmap_size = {tuning.mmap_mb * 1024 * 1024}")
    connection.execute("PRAGMA foreign_keys = ON")


def _stage_15_input_snapshot(
    config: NativeCodeConfig,
    manifests: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    snapshot = {
        "client_build": config.client_build,
        "tool_version": TOOL_VERSION,
        "config_sha256": config.config_sha256,
        "inventory_sha256": sha256_file(config.inventory_path),
        "anchors_sha256": sha256_file(config.anchors_path),
        "waves_sha256": sha256_file(config.waves_path),
        "review_overrides_sha256": sha256_file(config.review_overrides_path),
        "engine_manifests": [
            {
                "path": Path(payload["_path"]).resolve().as_posix(),
                "sha256": sha256_file(Path(payload["_path"])),
            }
            for payload in manifests
        ],
        "dynamic_manifests": [
            {
                "path": path.resolve().as_posix(),
                "sha256": sha256_file(path),
            }
            for path, _ in _dynamic_manifests(config)
        ],
    }
    return sha256_text(canonical_json(snapshot)), snapshot


def _preflight_stage_15_outputs(
    config: NativeCodeConfig,
    manifests: list[dict[str, Any]],
    *,
    workers: int,
    progress: Stage15Progress,
) -> dict[str, dict[str, int]]:
    audits: dict[str, dict[str, int]] = {}

    def validate(payload: dict[str, Any]) -> tuple[str, dict[str, int]]:
        path = Path(payload["_path"])
        return (
            path.resolve().as_posix(),
            _validate_run_outputs(
                config,
                payload,
                path,
                verify_hashes=True,
            ),
        )

    progress.start_phase(
        "preflight",
        total=len(manifests),
        detail=f"hash verification with {workers} workers",
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(validate, payload): payload for payload in manifests}
        completed = 0
        for future in as_completed(futures):
            path, audit = future.result()
            audits[path] = audit
            completed += 1
            progress.update(
                completed,
                detail=f"verified {Path(path).parent.name}",
            )
    progress.complete_phase("preflight", detail=f"{len(audits)} manifests verified")
    return audits


def _stage_15_phase_key(name: str) -> str:
    return f"stage15_build_phase:{name}"


def _stage_15_phase_result(
    connection: sqlite3.Connection, name: str
) -> Any | None:
    row = connection.execute(
        "SELECT value FROM metadata WHERE key=?",
        (_stage_15_phase_key(name),),
    ).fetchone()
    return json.loads(str(row[0])) if row else None


def _complete_stage_15_phase(
    connection: sqlite3.Connection, name: str, result: Any
) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        (_stage_15_phase_key(name), canonical_json(result)),
    )
    connection.commit()


def _stage_15_import_key(manifest_sha256: str) -> str:
    return f"stage15_build_import:{manifest_sha256.lower()}"


def _completed_stage_15_import(
    connection: sqlite3.Connection, manifest_sha256: str
) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT value FROM metadata WHERE key=?",
        (_stage_15_import_key(manifest_sha256),),
    ).fetchone()
    return json.loads(str(row[0])) if row else None


def _record_stage_15_import(
    connection: sqlite3.Connection,
    manifest_sha256: str,
    *,
    engine: str,
    count: int,
) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
        (
            _stage_15_import_key(manifest_sha256),
            canonical_json({"engine": engine, "count": count}),
        ),
    )
    connection.commit()


def _sha256_file_with_progress(
    path: Path,
    progress: Callable[[int, int, str], None] | None = None,
) -> str:
    total = path.stat().st_size
    completed = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            completed += len(chunk)
            if progress:
                progress(completed, total, "SHA-256")
    return digest.hexdigest().upper()


def _assert_stage_15_build_ready(config: NativeCodeConfig) -> None:
    active = _native_processes()
    if active:
        labels = ", ".join(
            f"{item['name']} pid={item['pid']}" for item in active
        )
        raise RuntimeError(
            "Stage 15 cannot be rebuilt while native decompilers are active: "
            + labels
        )
    if config.batch_root.is_dir():
        pending = []
        for path in sorted(config.batch_root.glob("*/run.manifest.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("status") not in _TERMINAL_RUN_STATES:
                pending.append(path.resolve().as_posix())
        if pending:
            raise RuntimeError(
                "Stage 15 cannot be rebuilt with pending batch manifests: "
                + ", ".join(pending)
            )


@contextmanager
def _stage_15_build_lock(
    config: NativeCodeConfig, *, input_sha256: str
) -> Iterable[Path]:
    lock = config.output_root / ".stage-15-build.lock"
    if lock.is_file():
        try:
            payload = json.loads(lock.read_text(encoding="utf-8"))
            lock_pid = int(payload.get("pid", -1))
        except (OSError, ValueError, json.JSONDecodeError):
            lock_pid = -1
        if not _pid_is_running(lock_pid):
            lock.unlink(missing_ok=True)
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(
            f"Another Stage 15 build is already active: {lock}"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(
                canonical_json(
                    {
                        "schema": "AA8_STAGE15_BUILD_LOCK_V1",
                        "pid": os.getpid(),
                        "input_sha256": input_sha256,
                        "started_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
        yield lock
    finally:
        lock.unlink(missing_ok=True)


def build_stage_15(
    config: NativeCodeConfig,
    *,
    performance_profile: str = "balanced",
    workers: int | None = None,
    memory_mb: int | None = None,
    resume: bool = True,
    progress_path: Path | None = None,
    console_progress: bool | None = None,
) -> dict[str, Any]:
    _assert_stage_15_build_ready(config)
    inventory = _load_inventory(config)
    config.output_root.mkdir(parents=True, exist_ok=True)
    manifests = _engine_manifests(config)
    input_sha256, input_snapshot = _stage_15_input_snapshot(config, manifests)
    tuning = resolve_stage_15_tuning(
        profile=performance_profile,
        workers=workers,
        memory_mb=memory_mb,
    )
    work_database = (
        config.output_root
        / f".stage-15-native-code.work-{input_sha256[:16].lower()}.sqlite"
    )
    compact_database = (
        config.output_root
        / f".stage-15-native-code.compact-{input_sha256[:16].lower()}.sqlite"
    )

    with _stage_15_build_lock(config, input_sha256=input_sha256):
        progress = Stage15Progress(
            (progress_path or config.stage_build_progress).resolve(),
            input_sha256=input_sha256,
            tuning=tuning,
            console=(
                bool(sys.stderr.isatty())
                if console_progress is None
                else bool(console_progress)
            ),
            heartbeat_seconds=2.0,
        )
        progress.set_temporary_database(work_database)
        try:
            return _build_stage_15_locked(
                config,
                inventory=inventory,
                manifests=manifests,
                input_sha256=input_sha256,
                input_snapshot=input_snapshot,
                tuning=tuning,
                progress=progress,
                work_database=work_database,
                compact_database=compact_database,
                resume=resume,
            )
        except Exception as exc:
            progress.fail(exc)
            raise


def _build_stage_15_locked(
    config: NativeCodeConfig,
    *,
    inventory: dict[str, Any],
    manifests: list[dict[str, Any]],
    input_sha256: str,
    input_snapshot: dict[str, Any],
    tuning: Stage15BuildTuning,
    progress: Stage15Progress,
    work_database: Path,
    compact_database: Path,
    resume: bool,
) -> dict[str, Any]:
    connection: sqlite3.Connection | None = None
    try:
        _preflight_stage_15_outputs(
            config,
            manifests,
            workers=tuning.hash_workers,
            progress=progress,
        )

        if work_database.is_file():
            if not resume:
                raise RuntimeError(
                    "A resumable Stage 15 work database already exists: "
                    f"{work_database}"
                )
            progress.start_phase("initialize", detail="opening resumable checkpoint")
            connection = sqlite3.connect(work_database)
            _configure_stage_15_connection(connection, tuning)
            row = connection.execute(
                "SELECT value FROM metadata WHERE key='stage15_build_input_sha256'"
            ).fetchone()
            if row is None or str(row[0]) != input_sha256:
                raise RuntimeError(
                    "Stage 15 checkpoint does not match the current inputs: "
                    f"{work_database}"
                )
            progress.complete_phase("initialize", detail="checkpoint recovered")
        else:
            progress.start_phase("initialize", detail="creating resumable database")
            connection = create_database(work_database)
            _configure_stage_15_connection(connection, tuning)
            create_native_code_tables(connection)
            connection.executemany(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                (
                    ("classification", "stage_15_native_code_corpus"),
                    ("client_build", config.client_build),
                    ("tool_name", TOOL_NAME),
                    ("tool_version", TOOL_VERSION),
                    ("schema_version", str(SCHEMA_VERSION)),
                    ("config_sha256", config.config_sha256),
                    ("inventory_sha256", input_snapshot["inventory_sha256"]),
                    ("native_code_waves_sha256", input_snapshot["waves_sha256"]),
                    (
                        "native_code_review_overrides_sha256",
                        input_snapshot["review_overrides_sha256"],
                    ),
                    ("stage15_build_input_sha256", input_sha256),
                    ("server_mutation", "forbidden"),
                ),
            )
            _complete_stage_15_phase(
                connection,
                "initialize",
                {"native_code_schema": "created"},
            )
            progress.complete_phase("initialize", detail="schema checkpoint committed")

        assert connection is not None

        def run_phase(
            name: str,
            callback: Callable[[], Any],
            *,
            total: int | None = None,
            detail: str = "",
        ) -> Any:
            prior = _stage_15_phase_result(connection, name)
            if prior is not None:
                progress.completed_phases.add(name)
                progress.start_phase(name, total=total, detail="resumed checkpoint")
                progress.complete_phase(name, detail="resumed checkpoint")
                return prior
            progress.start_phase(name, total=total, detail=detail)
            try:
                result = callback()
                _complete_stage_15_phase(connection, name, result)
            except Exception:
                connection.rollback()
                raise
            progress.complete_phase(name, detail="checkpoint committed")
            return result

        def inventory_phase() -> dict[str, int]:
            inserted = _insert_inventory(connection, config, inventory)
            return {"binaries": len(inserted)}

        run_phase(
            "inventory",
            inventory_phase,
            total=len(inventory["binaries"]),
            detail="PE inventory",
        )
        binaries = {
            str(item["binary_key"]): item for item in inventory["binaries"]
        }

        imported: dict[str, int] = {}
        progress.start_phase(
            "engine_imports",
            total=len(manifests),
            detail="resumable manifest imports",
        )
        inventory_sha256 = str(input_snapshot["inventory_sha256"])
        for ordinal, payload in enumerate(manifests, start=1):
            path = Path(payload["_path"])
            manifest_sha256 = sha256_file(path)
            completed = _completed_stage_15_import(connection, manifest_sha256)
            if completed is not None:
                engine = str(completed["engine"])
                imported[engine] = imported.get(engine, 0) + int(
                    completed["count"]
                )
                progress.update(
                    ordinal,
                    detail=f"resumed {engine} {path.parent.name}",
                )
                continue
            if payload.get("schema") != "AA8_NATIVE_CODE_ENGINE_RUN_V1":
                raise ValueError(f"Unsupported engine run manifest: {path}")
            if payload.get("client_build") != config.client_build:
                raise ValueError(f"Engine run belongs to another build: {path}")
            if payload.get("inventory_sha256") != inventory_sha256:
                raise ValueError(f"Engine run inventory mismatch: {path}")
            binary = str(payload["binary"]["binary_key"])
            if binary not in binaries:
                raise ValueError(f"Engine run binary not in inventory: {path}")
            recorded_binary = payload["binary"]
            if (
                str(recorded_binary.get("sha256", "")).upper()
                != str(binaries[binary]["sha256"]).upper()
                or recorded_binary.get("architecture")
                != binaries[binary]["architecture"]
            ):
                raise ValueError(f"Engine run binary identity mismatch: {path}")
            if binaries[binary]["classification"] == "excluded_anticheat":
                raise ValueError(f"Anticheat engine run rejected: {path}")
            _validate_run_outputs(
                config,
                payload,
                path,
                verify_hashes=False,
            )
            try:
                run_key = _insert_engine_run(connection, payload, path)
                engine = str(payload["engine"]["id"])
                if engine == "ghidra":
                    count = _import_ghidra(
                        connection, binaries, payload, path, run_key
                    )
                elif engine == "rizin":
                    count = _import_rizin(
                        connection, binaries, payload, run_key
                    )
                elif engine == "angr":
                    count = _import_angr(
                        connection, binaries, payload, run_key
                    )
                elif engine == "reko":
                    count = _import_reko(
                        connection, binaries, payload, run_key
                    )
                elif engine == "revng":
                    count = _import_whole_module_vote(
                        connection, payload, run_key
                    )
                else:
                    count = 0
                _insert_common_artifact(
                    connection,
                    key=f"stage15:engine-run:{manifest_sha256[:24].lower()}",
                    path=path,
                    role=f"native_code_engine_run_{engine}",
                    state=payload["status"],
                    evidence={
                        "binary_key": binary,
                        "engine": payload["engine"],
                        "scope": payload["scope"],
                    },
                    sha256=manifest_sha256,
                )
                _record_stage_15_import(
                    connection,
                    manifest_sha256,
                    engine=engine,
                    count=count,
                )
            except Exception:
                connection.rollback()
                raise
            imported[engine] = imported.get(engine, 0) + count
            progress.update(
                ordinal,
                detail=f"{engine} {path.parent.name}",
                force=True,
            )
        _complete_stage_15_phase(
            connection,
            "engine_imports",
            dict(sorted(imported.items())),
        )
        progress.complete_phase(
            "engine_imports", detail=f"{len(manifests)} manifests committed"
        )

        def native_enrichment_phase() -> dict[str, int]:
            result = {
                "anchor_links": _insert_anchor_links(connection, config),
                "native_export_names": _apply_native_export_names(connection),
                "inferred_this_offset_fields": _infer_vtable_this_offsets(
                    connection
                ),
            }
            anchor_payload = json.loads(
                config.anchors_path.read_text(encoding="utf-8")
            )
            missing_anchors = [
                function_key(anchor["binary_key"], int(anchor["entry_rva"]))
                for anchor in anchor_payload["anchors"]
                if connection.execute(
                    "SELECT 1 FROM code_functions WHERE function_key=?",
                    (
                        function_key(
                            anchor["binary_key"], int(anchor["entry_rva"])
                        ),
                    ),
                ).fetchone()
                is None
            ]
            if missing_anchors:
                raise ValueError(
                    "Golden anchor functions missing from Stage 15: "
                    + ", ".join(missing_anchors[:20])
                )
            return result

        enrichment = run_phase(
            "native_enrichment",
            native_enrichment_phase,
            detail="anchors, exports and this+offset fields",
        )

        def call_resolution_phase() -> dict[str, int]:
            before = connection.total_changes
            connection.execute(
                """
                UPDATE code_calls AS call
                SET callee_function_key=(
                    SELECT callee.function_key
                    FROM code_functions caller
                    JOIN code_functions callee
                      ON callee.binary_key=caller.binary_key
                     AND callee.entry_rva=call.target_rva
                    WHERE caller.function_key=call.caller_function_key
                )
                WHERE call.target_rva IS NOT NULL
                """
            )
            return {"updated": connection.total_changes - before}

        run_phase(
            "call_resolution",
            call_resolution_phase,
            detail="direct RVA caller/callee mapping",
        )

        executable_regions = run_phase(
            "executable_regions",
            lambda: _build_executable_regions(
                connection,
                binaries,
                lambda completed, total, detail: progress.update(
                    completed, total=total, detail=detail
                ),
            ),
            total=sum(1 for item in binaries.values() if item["analysis_enabled"]),
            detail="executable byte partition",
        )

        def coverage_and_matrix_phase() -> dict[str, Any]:
            dynamic = _import_dynamic_coverage(connection, config, binaries)
            _ensure_engine_matrix(connection, config, binaries)
            return {"dynamic_coverage": dynamic}

        coverage_and_matrix = run_phase(
            "coverage_and_engine_matrix",
            coverage_and_matrix_phase,
            detail="dynamic coverage and explicit engine states",
        )
        dynamic_coverage = coverage_and_matrix["dynamic_coverage"]

        equivalences = run_phase(
            "architecture_equivalences",
            lambda: _build_equivalences(connection),
            detail="x86/x64 evidence matching",
        )

        def review_overlay_phase() -> dict[str, int]:
            result = _apply_review_overrides(connection, config)
            _insert_common_artifact(
                connection,
                key="stage15:native-code-review-overrides",
                path=config.review_overrides_path,
                role="native_code_review_overrides",
                state="confirmed",
                evidence={
                    "schema": "AA8_NATIVE_CODE_REVIEW_OVERRIDES_V1",
                    "decisions": result["decisions"],
                },
            )
            return result

        review_overrides = run_phase(
            "review_overlay",
            review_overlay_phase,
            detail="provenance-bearing review decisions",
        )
        review_rows = run_phase(
            "review_queue",
            lambda: _build_review_queue(
                connection,
                lambda completed, total, detail: progress.update(
                    completed, total=total, detail=detail
                ),
            ),
            total=int(
                connection.execute(
                    "SELECT COUNT(*) FROM code_functions"
                ).fetchone()[0]
            ),
            detail="pre-aggregated actionable review",
        )
        search_rows = run_phase(
            "search_index",
            lambda: _build_search(
                connection,
                lambda completed, total, detail: progress.update(
                    completed, total=total, detail=detail
                ),
            ),
            total=int(
                connection.execute(
                    "SELECT COUNT(*) FROM code_functions"
                ).fetchone()[0]
            ),
            detail="FTS5 names, strings, instructions and pseudocode",
        )

        def coverage_records_phase() -> dict[str, int]:
            enabled = [
                item
                for item in sorted(
                    binaries.values(), key=lambda value: value["binary_key"]
                )
                if item["analysis_enabled"]
            ]
            opaque = 0
            for ordinal, binary in enumerate(enabled, start=1):
                key = binary["binary_key"]
                functions = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM code_functions WHERE binary_key=?",
                        (key,),
                    ).fetchone()[0]
                )
                state = "confirmed" if functions else "opaque"
                connection.execute(
                    """
                    INSERT INTO coverage(
                        coverage_key,scope_key,dimension,state,capability,
                        authority,provenance,evidence_json
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        stable_key("coverage", key, "native_code_functions"),
                        key,
                        "native_code_functions",
                        state,
                        "function_level_corpus",
                        "derived_forensic",
                        "native_code_forensic",
                        canonical_json({"functions": functions}),
                    ),
                )
                if not functions:
                    opaque += 1
                    connection.execute(
                        """
                        INSERT INTO opaque_regions(
                            opaque_key,surface,locator,blocker_code,reason,
                            searched_evidence_json,source_stage,state
                        ) VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            stable_key("opaque", key, "no-function-corpus"),
                            binary["module_name"],
                            binary["source_path"],
                            "native_code_not_decompiled",
                            "No function inventory has been imported for this module",
                            canonical_json(
                                {
                                    "binary_key": key,
                                    "classification": binary["classification"],
                                }
                            ),
                            15,
                            "opaque",
                        ),
                    )
                progress.update(
                    ordinal,
                    total=len(enabled),
                    detail=f"{binary['module_name']} {binary['architecture']}",
                )
            connection.execute(
                """
                INSERT INTO validation_events(
                    validation_key,scope_kind,scope_id,check_name,status,evidence_json
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    stable_key("validation", "stage15", "policy"),
                    "database",
                    "stage-15-native-code.sqlite",
                    "anticheat_and_cloud_policy",
                    "confirmed",
                    canonical_json(config.policy),
                ),
            )
            return {"binaries": len(enabled), "opaque_binaries": opaque}

        run_phase(
            "coverage_records",
            coverage_records_phase,
            total=sum(1 for item in binaries.values() if item["analysis_enabled"]),
            detail="per-binary coverage records",
        )

        connection.commit()
        progress.start_phase("compact", detail="VACUUM INTO compact candidate")
        if compact_database.is_file():
            compact_database.unlink()
        compact_sql = compact_database.resolve().as_posix().replace("'", "''")
        connection.set_progress_handler(
            lambda: (
                progress.update(detail="VACUUM INTO compact candidate"),
                0,
            )[1],
            100000,
        )
        try:
            connection.execute(f"VACUUM INTO '{compact_sql}'")
        finally:
            connection.set_progress_handler(None, 0)
        progress.complete_phase("compact", detail="compact candidate complete")
        connection.close()
        connection = None

        progress.start_phase("validate", detail="quick_check")
        validation = validate_native_code_database(
            compact_database,
            tuning=tuning,
            progress=lambda detail: progress.update(detail=detail),
        )
        progress.complete_phase("validate", detail="integrity confirmed")

        progress.start_phase(
            "hash_and_publish",
            total=compact_database.stat().st_size,
            detail="SHA-256",
        )
        database_sha256 = _sha256_file_with_progress(
            compact_database,
            lambda completed, total, detail: progress.update(
                completed, total=total, detail=detail
            ),
        )
        database_bytes = compact_database.stat().st_size
        compact_database.replace(config.stage_database)
        manifest = {
            "schema": "AA8_NATIVE_CODE_STAGE_MANIFEST_V1",
            "stage": 15,
            "classification": "stage_15_native_code_corpus",
            "client_build": config.client_build,
            "database": {
                "path": config.stage_database.as_posix(),
                "bytes": database_bytes,
                "sha256": database_sha256,
            },
            "inputs": {
                "config_sha256": input_snapshot["config_sha256"],
                "inventory_sha256": input_snapshot["inventory_sha256"],
                "anchors_sha256": input_snapshot["anchors_sha256"],
                "waves_sha256": input_snapshot["waves_sha256"],
                "review_overrides_sha256": input_snapshot[
                    "review_overrides_sha256"
                ],
                "engine_run_manifests": input_snapshot["engine_manifests"],
                "dynamic_coverage_manifests": input_snapshot[
                    "dynamic_manifests"
                ],
            },
            "imported_function_results": dict(sorted(imported.items())),
            "anchor_links": enrichment["anchor_links"],
            "native_export_names": enrichment["native_export_names"],
            "inferred_this_offset_fields": enrichment[
                "inferred_this_offset_fields"
            ],
            "equivalences": equivalences,
            "review_overrides": review_overrides,
            "review_rows": review_rows,
            "search_rows": search_rows,
            "dynamic_coverage": dynamic_coverage,
            "executable_regions": executable_regions,
            "validation": validation,
            "table_counts": validation["counts"],
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "determinism": {
                "stable_ordering": True,
                "timestamps_in_reproducible_artifacts": False,
                "atomic_replace": True,
                "resumable_checkpoints": True,
                "vacuum_into_candidate": True,
            },
        }
        atomic_text(config.stage_manifest, canonical_json(manifest, pretty=True))
        manifest["manifest"] = {
            "path": config.stage_manifest.as_posix(),
            "sha256": sha256_file(config.stage_manifest),
        }
        progress.complete_phase("hash_and_publish", detail="published atomically")
        progress.set_temporary_database(config.stage_database)
        progress.complete(detail="Stage 15 confirmed")
        work_database.unlink(missing_ok=True)
        manifest["build_runtime"] = {
            "input_sha256": input_sha256,
            "progress_path": progress.path.as_posix(),
            "tuning": progress.payload()["tuning"],
        }
        return manifest
    except Exception:
        if connection is not None:
            connection.rollback()
            connection.close()
        raise


def diff_native_architectures(config: NativeCodeConfig) -> dict[str, Any]:
    database = config.stage_database
    if not database.is_file():
        raise FileNotFoundError(database)
    connection = open_read_only(database)
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT e.equivalence_key,e.state,e.method,e.rank_score,
                       e.left_function_key,e.right_function_key,
                       (
                           SELECT n.name FROM code_names n
                           WHERE n.function_key=lf.function_key
                           ORDER BY n.primary_name DESC,
                                    CASE n.state
                                      WHEN 'confirmed' THEN 0
                                      WHEN 'corroborated' THEN 1
                                      ELSE 2 END,
                                    n.name
                           LIMIT 1
                       ) AS left_name,
                       (
                           SELECT n.name FROM code_names n
                           WHERE n.function_key=rf.function_key
                           ORDER BY n.primary_name DESC,
                                    CASE n.state
                                      WHEN 'confirmed' THEN 0
                                      WHEN 'corroborated' THEN 1
                                      ELSE 2 END,
                                    n.name
                           LIMIT 1
                       ) AS right_name,
                       lf.entry_rva AS left_rva,rf.entry_rva AS right_rva,
                       e.evidence_json
                FROM code_equivalences e
                JOIN code_functions lf
                  ON lf.function_key=e.left_function_key
                JOIN code_functions rf
                  ON rf.function_key=e.right_function_key
                ORDER BY e.state,e.left_function_key,e.right_function_key
                """
            )
        ]
        return {
            "schema": "AA8_NATIVE_CODE_ARCHITECTURE_DIFF_V1",
            "client_build": config.client_build,
            "database_sha256": sha256_file(database),
            "equivalences": rows,
        }
    finally:
        connection.close()


def _function_payload(
    connection: sqlite3.Connection, function: str
) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT f.*,b.module_name,b.architecture,b.sha256 AS binary_sha256,
               b.image_base,b.classification
        FROM code_functions f
        JOIN code_binaries b ON b.binary_key=f.binary_key
        WHERE f.function_key=?
        """,
        (function,),
    ).fetchone()
    if row is None:
        raise KeyError(function)
    payload = dict(row)
    for key in ("evidence_json",):
        payload[key[:-5]] = json.loads(payload.pop(key))
    payload["names"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT name,namespace,source_kind,source_locator,primary_name,state,
                   evidence_json
            FROM code_names WHERE function_key=?
            ORDER BY primary_name DESC,state,name
            """,
            (function,),
        )
    ]
    payload["decompilations"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT d.engine_id,d.prototype,d.calling_convention,d.pseudocode,
                   d.pseudocode_sha256,d.duration_ms,d.status,d.error,
                   d.evidence_json,r.engine_version,r.scope
            FROM code_decompilations d
            JOIN code_engine_runs r ON r.run_key=d.run_key
            WHERE d.function_key=?
            ORDER BY d.engine_id,r.scope
            """,
            (function,),
        )
    ]
    payload["calls"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT callsite_rva,target_rva,target_name,call_kind,state,
                   callee_function_key
            FROM code_calls WHERE caller_function_key=?
            ORDER BY callsite_rva,call_key
            """,
            (function,),
        )
    ]
    payload["basic_blocks"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT start_rva,end_rva,instruction_count,state
            FROM code_basic_blocks WHERE function_key=?
            ORDER BY start_rva
            """,
            (function,),
        )
    ]
    payload["instructions"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT rva,mnemonic,instruction_text,bytes_hex,state
            FROM code_instructions WHERE function_key=?
            ORDER BY rva
            """,
            (function,),
        )
    ]
    payload["data_references"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT from_rva,to_rva,reference_kind,state,evidence_json
            FROM code_data_references WHERE function_key=?
            ORDER BY from_rva,to_rva
            """,
            (function,),
        )
    ]
    payload["callers"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT caller_function_key,callsite_rva,target_rva,target_name,
                   call_kind,state
            FROM code_calls WHERE callee_function_key=?
            ORDER BY caller_function_key,callsite_rva
            """,
            (function,),
        )
    ]
    payload["strings"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT s.rva,s.encoding,s.value,s.state,fs.reference_rva
            FROM code_function_strings fs
            JOIN code_strings s ON s.string_key=fs.string_key
            WHERE fs.function_key=?
            ORDER BY s.rva,s.value
            """,
            (function,),
        )
    ]
    payload["evidence_links"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT scope_key,relation,source_locator,state,evidence_json
            FROM code_evidence_links WHERE function_key=?
            ORDER BY scope_key,relation
            """,
            (function,),
        )
    ]
    payload["equivalences"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT * FROM code_equivalences
            WHERE left_function_key=? OR right_function_key=?
            ORDER BY state,equivalence_key
            """,
            (function, function),
        )
    ]
    payload["vtable_slots"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT v.vtable_key,v.rva AS vtable_rva,t.type_name,
                   s.ordinal,s.target_rva,s.state,s.evidence_json
            FROM code_vtable_slots s
            JOIN code_vtables v ON v.vtable_key=s.vtable_key
            LEFT JOIN code_types t ON t.type_key=v.type_key
            WHERE s.target_function_key=?
            ORDER BY v.rva,s.ordinal
            """,
            (function,),
        )
    ]
    payload["dynamic_coverage"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT c.hit_count,c.first_observed_rva,c.state,
                   r.scenario,r.tool_id,r.tool_version,r.trace_sha256
            FROM code_dynamic_coverage c
            JOIN code_dynamic_runs r
              ON r.dynamic_run_key=c.dynamic_run_key
            WHERE c.function_key=?
            ORDER BY r.scenario,r.tool_id
            """,
            (function,),
        )
    ]
    payload["review_queue"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT reason_code,priority,state,evidence_json
            FROM code_review_queue WHERE function_key=?
            ORDER BY priority DESC,reason_code
            """,
            (function,),
        )
    ]
    payload["review_decisions"] = [
        dict(value)
        for value in connection.execute(
            """
            SELECT decision_kind,function_key,related_function_key,state,
                   source_locator,payload_json,evidence_json
            FROM code_review_decisions
            WHERE function_key=? OR related_function_key=?
            ORDER BY decision_kind,decision_key
            """,
            (function, function),
        )
    ]
    return payload


_FUNCTION_HTML = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{color-scheme:dark;--bg:#0e1419;--panel:#172129;--line:#2b3b47;
--text:#e7eff4;--muted:#91a6b2;--accent:#5dd2bd;--warn:#f2c96d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}}header,main{{padding:18px 22px}}
header{{border-bottom:1px solid var(--line);background:#111a20}}h1{{margin:0}}
.muted{{color:var(--muted)}}section{{margin:14px 0;padding:14px;background:var(--panel);
border:1px solid var(--line);border-radius:9px}}pre{{white-space:pre-wrap;
word-break:break-word;background:#0d1318;padding:12px;border-radius:7px;
overflow:auto}}.engines{{display:grid;grid-template-columns:repeat(auto-fit,
minmax(420px,1fr));gap:12px}}.badge{{display:inline-block;padding:2px 7px;
border-radius:12px;background:#263844;color:var(--accent)}}a{{color:var(--accent)}}
</style></head><body><header><h1>{title}</h1><div class="muted">{subtitle}</div>
</header><main><section id="summary"></section><div class="engines" id="engines"></div>
<section><h2>Evidencia completa</h2><pre id="raw"></pre></section></main><script>
const D={payload}; const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({{
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
document.querySelector('#summary').innerHTML=`<b>RVA</b> 0x${{D.entry_rva.toString(16)}}
 · <b>arquitectura</b> ${{esc(D.architecture)}} · <b>estado</b> ${{esc(D.state)}}
<h3>Nombres</h3><pre>${{esc(JSON.stringify(D.names,null,2))}}</pre>`;
document.querySelector('#engines').innerHTML=D.decompilations.map(x=>`<section>
<h2>${{esc(x.engine_id)}} <span class="badge">${{esc(x.status)}}</span></h2>
<div class="muted">${{esc(x.engine_version)}} · ${{esc(x.scope)}}</div>
<pre>${{esc(x.pseudocode||x.error||'sin pseudocódigo')}}</pre></section>`).join('');
document.querySelector('#raw').textContent=JSON.stringify(D,null,2);
</script></body></html>"""


def export_native_function(
    config: NativeCodeConfig,
    binary: str,
    rva: int,
    *,
    architecture: str | None = None,
) -> dict[str, Any]:
    database = config.stage_database
    if not database.is_file():
        raise FileNotFoundError(database)
    selected = _selected_binary(config, binary, architecture)
    key = function_key(selected["binary_key"], rva)
    connection = open_read_only(database)
    try:
        payload = _function_payload(connection, key)
    finally:
        connection.close()
    return _write_native_function_dossier(
        config,
        payload,
        database_sha256=sha256_file(database),
    )


def _write_native_function_dossier(
    config: NativeCodeConfig,
    payload: dict[str, Any],
    *,
    database_sha256: str,
) -> dict[str, Any]:
    rva = int(payload["entry_rva"])
    output = config.dossier_root / (
        f"{payload['module_name']}-{payload['architecture']}-{rva:08x}"
    )
    # PE module names contain a suffix (for example ``x2game.dll``).
    # with_suffix() would therefore collapse distinct dossiers to x2game.json.
    json_path = Path(f"{output}.json")
    html_path = Path(f"{output}.html")
    document = {
        "schema": "AA8_NATIVE_FUNCTION_DOSSIER_V1",
        "client_build": config.client_build,
        "database_sha256": database_sha256,
        "function": payload,
    }
    atomic_text(json_path, canonical_json(document, pretty=True))
    title = (
        f"{payload['module_name']} {payload['architecture']} RVA 0x{rva:X}"
    )
    html = _FUNCTION_HTML.format(
        title=title,
        subtitle=f"{config.client_build} · evidencia forense, no fuente original",
        payload=canonical_json(payload).replace("</", "<\\/"),
    )
    atomic_text(html_path, html)
    return {
        "function_key": payload["function_key"],
        "module_name": payload["module_name"],
        "architecture": payload["architecture"],
        "entry_rva": rva,
        "json": {
            "path": json_path.as_posix(),
            "sha256": sha256_file(json_path),
        },
        "html": {
            "path": html_path.as_posix(),
            "sha256": sha256_file(html_path),
        },
    }


def export_native_anchor_dossiers(
    config: NativeCodeConfig,
) -> dict[str, Any]:
    database = config.stage_database
    if not database.is_file():
        raise FileNotFoundError(database)
    anchors = json.loads(config.anchors_path.read_text(encoding="utf-8"))
    if anchors.get("schema") != "AA8_NATIVE_CODE_ANCHORS_V1":
        raise ValueError("Unsupported native anchor inventory schema")
    if anchors.get("client_build") != config.client_build:
        raise ValueError("Native anchors belong to another client build")
    database_sha256 = sha256_file(database)
    expected_functions: set[str] = set()
    dossiers: list[dict[str, Any]] = []
    connection = open_read_only(database)
    try:
        for anchor in sorted(
            anchors["anchors"],
            key=lambda item: (
                str(item["architecture"]),
                str(item["binary_key"]),
                int(item["entry_rva"]),
            ),
        ):
            function = function_key(
                str(anchor["binary_key"]), int(anchor["entry_rva"])
            )
            if function in expected_functions:
                raise ValueError(f"Duplicate native anchor function: {function}")
            expected_functions.add(function)
            payload = _function_payload(connection, function)
            if payload["architecture"] != anchor["architecture"]:
                raise ValueError(
                    f"Native anchor architecture mismatch: {function}"
                )
            result = _write_native_function_dossier(
                config,
                payload,
                database_sha256=database_sha256,
            )
            result["anchor"] = {
                "locator_count": len(anchor.get("locators", [])),
                "locators": anchor.get("locators", []),
            }
            dossiers.append(result)
    finally:
        connection.close()
    manifest = {
        "schema": "AA8_NATIVE_ANCHOR_DOSSIERS_MANIFEST_V1",
        "client_build": config.client_build,
        "state": "confirmed",
        "database": {
            "path": database.resolve().as_posix(),
            "sha256": database_sha256,
        },
        "anchors": {
            "path": config.anchors_path.resolve().as_posix(),
            "sha256": sha256_file(config.anchors_path),
            "count": len(dossiers),
        },
        "dossiers": dossiers,
    }
    manifest_path = config.dossier_root / "golden-anchors-v3.manifest.json"
    atomic_text(manifest_path, canonical_json(manifest, pretty=True))
    return {
        **manifest,
        "manifest": {
            "path": manifest_path.as_posix(),
            "sha256": sha256_file(manifest_path),
        },
    }


_VIEWER_HTML = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA8 Native Code Corpus</title><style>
:root{color-scheme:dark;--bg:#0e1419;--panel:#172129;--line:#2b3b47;
--text:#e7eff4;--muted:#91a6b2;--accent:#5dd2bd;--warn:#f2c96d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:14px/1.45 system-ui,sans-serif}header{padding:18px 22px;border-bottom:1px solid
var(--line);background:#111a20;position:sticky;top:0;z-index:3}h1{margin:0 0 8px}
input,select{background:#0d1318;color:var(--text);border:1px solid var(--line);
padding:9px;border-radius:7px}input{width:min(700px,70vw)}main{display:grid;
grid-template-columns:minmax(400px,.8fr) minmax(520px,1.2fr);gap:14px;padding:14px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:9px;
overflow:auto;max-height:calc(100vh - 120px)}table{width:100%;border-collapse:collapse}
th,td{padding:8px;border-bottom:1px solid var(--line);text-align:left}
tr[data-key]{cursor:pointer}tr[data-key]:hover{background:#21303a}
#detail{padding:14px}pre{white-space:pre-wrap;word-break:break-word;background:#0d1318;
padding:10px;border-radius:7px}.engines{display:grid;grid-template-columns:
repeat(auto-fit,minmax(420px,1fr));gap:10px}.engine{padding:10px;border:1px solid
var(--line);border-radius:7px;min-width:0}
.muted{color:var(--muted)}.badge{padding:2px 7px;border-radius:12px;background:#263844;
color:var(--accent)}@media(max-width:950px){main{grid-template-columns:1fr}
.panel{max-height:none}}
</style></head><body><header><h1>AA8 Native Code Corpus</h1>
<input id="q" placeholder="nombre, rva:, hash:, opcode:, class:, caller:, callee:, SQL o string">
<select id="arch"><option value="">x86 + x64</option><option>x86</option>
<option>x64</option></select>
<select id="filter"><option value="actionable">accionables</option>
<option value="consumer-linked">con consumer</option>
<option value="opaque-critical">opacas críticas</option>
<option value="engine-failure-group">fallos agrupados</option>
<option value="critical-root">raíces semánticas críticas</option>
<option value="opaque-blocking">bloqueadas por opacidad</option>
<option value="indirect-dispatch">dispatch indirecto</option>
<option value="">todas</option></select>
<select id="domain"><option value="">todos los dominios</option>
<option>protocol</option><option>item_loot_economy</option><option>skill_buff_combat</option>
<option>quest_npc_world</option><option>lua_script</option><option>state_sql</option>
<option>engine_dependency</option><option>presentation</option></select>
<select id="tier"><option value="">todos los impactos</option><option>critical</option>
<option>high</option><option>medium</option><option>context</option><option>low</option></select>
<select id="uncertainty"><option value="">toda incertidumbre</option>
<option value="1">con incertidumbre</option></select>
<select id="closure"><option value="">todos los cierres</option>
<option>understood</option><option>blocked_by_indirect_dispatch</option>
<option>blocked_by_opaque_region</option><option>blocked_by_missing_native_data</option>
<option>external_dependency</option><option>not_backend_relevant</option>
<option>pending_review</option></select></header><main><section class="panel"><table>
<thead><tr><th>Módulo</th><th>Arch</th><th>RVA</th><th>Nombre</th></tr></thead>
<tbody id="rows"></tbody></table></section><section class="panel" id="detail">
<span class="muted">Selecciona una función.</span></section></main><script>
const $=s=>document.querySelector(s), esc=s=>String(s??"").replace(/[&<>"']/g,c=>({
'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let timer; async function search(){const q=$('#q').value.trim(),a=$('#arch').value,
f=$('#filter').value,domain=$('#domain').value,tier=$('#tier').value,
uncertainty=$('#uncertainty').value,closure=$('#closure').value;
const r=await fetch('/api/search?q='+encodeURIComponent(q)+'&arch='+encodeURIComponent(a)
+'&filter='+encodeURIComponent(f)+'&semantic_domain='+encodeURIComponent(domain)
+'&impact_tier='+encodeURIComponent(tier)+'&uncertainty='+encodeURIComponent(uncertainty)
+'&closure_status='+encodeURIComponent(closure));
const data=await r.json();if(data.groups){$('#rows').innerHTML=data.groups.map(x=>`<tr>
<td>${esc(x.engine_id)}</td><td>${esc(x.state)}</td>
<td>${Number(x.affected_functions)}</td><td>${esc(x.reason_code)}</td></tr>`).join('');return}
$('#rows').innerHTML=data.results.map(x=>`<tr data-key="${esc(x.function_key)}">
<td>${esc(x.module_name)}</td><td>${esc(x.architecture)}</td>
<td>0x${Number(x.entry_rva).toString(16)}</td><td>${esc(x.primary_name)}</td></tr>`).join('');
document.querySelectorAll('tr[data-key]').forEach(x=>x.onclick=()=>detail(x.dataset.key))}
async function detail(key){const r=await fetch('/api/function/'+encodeURIComponent(key));
const d=await r.json(), engines=d.decompilations.map(x=>`<div class="engine"><h3>${esc(x.engine_id)}
 <span class="badge">${esc(x.status)}</span></h3><div class="muted">${esc(x.engine_version)}
 · ${esc(x.scope)}</div><pre>${esc(x.pseudocode||x.error||'sin pseudocódigo')}</pre></div>`).join('');
$('#detail').innerHTML=`<div id="detail"><h2>${esc(d.module_name)}
 <span class="badge">${esc(d.architecture)}</span></h2><div>RVA 0x${Number(d.entry_rva).toString(16)}
 · ${esc(d.state)}</div><h3>Nombres</h3><pre>${esc(JSON.stringify(d.names,null,2))}</pre>
<h3>Strings</h3><pre>${esc(JSON.stringify(d.strings,null,2))}</pre>
<h3>Motores</h3><div class="engines">${engines}</div>
<h3>Relaciones y cobertura</h3><pre>${esc(JSON.stringify({
calls:d.calls,callers:d.callers,data_references:d.data_references,
equivalences:d.equivalences,vtable_slots:d.vtable_slots,
dynamic_coverage:d.dynamic_coverage,review_queue:d.review_queue,
review_decisions:d.review_decisions,semantic:d.semantic},null,2))}</pre></div>`}
$('#q').oninput=()=>{clearTimeout(timer);timer=setTimeout(search,180)};
$('#arch').onchange=search;$('#filter').onchange=search;$('#domain').onchange=search;
$('#tier').onchange=search;$('#uncertainty').onchange=search;$('#closure').onchange=search;search();
</script></body></html>"""


def serve_native_code(
    config: NativeCodeConfig,
    *,
    bind: str,
    port: int,
    semantic_database: Path | None = None,
) -> None:
    expected = str(config.policy.get("bind_host", "127.0.0.1"))
    if bind != expected or bind not in {"127.0.0.1", "localhost"}:
        raise ValueError("Native corpus server may bind only to localhost")
    database = config.stage_database.resolve()
    if not database.is_file():
        raise FileNotFoundError(database)
    semantic_database = semantic_database.resolve() if semantic_database else None
    semantic_available = bool(semantic_database and semantic_database.is_file())

    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: Any, status: int = 200) -> None:
            body = canonical_json(payload, pretty=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = _VIEWER_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            connection = open_read_only(database)
            try:
                if semantic_available and semantic_database is not None:
                    connection.execute(
                        "ATTACH DATABASE ? AS semantic",
                        (semantic_database.as_posix(),),
                    )
                if parsed.path == "/api/search":
                    params = parse_qs(parsed.query)
                    query = params.get("q", [""])[0].strip()
                    architecture = params.get("arch", [""])[0].strip()
                    filter_value = params.get("filter", ["actionable"])[0].strip()
                    semantic_domain = params.get("semantic_domain", [""])[0].strip()
                    impact_tier = params.get("impact_tier", [""])[0].strip()
                    uncertainty = params.get("uncertainty", [""])[0].strip()
                    closure_status = params.get("closure_status", [""])[0].strip()
                    supported_filters = {
                        "",
                        "actionable",
                        "consumer-linked",
                        "opaque-critical",
                        "engine-failure-group",
                        "critical-root",
                        "opaque-blocking",
                        "indirect-dispatch",
                    }
                    if filter_value not in supported_filters:
                        raise ValueError(f"Unsupported viewer filter: {filter_value}")
                    if filter_value == "engine-failure-group":
                        groups = [
                            dict(row)
                            for row in connection.execute(
                                """
                                SELECT g.engine_id,g.reason_code,
                                       g.affected_functions,g.priority,g.state,
                                       g.error_signature,r.status AS run_status,
                                       b.module_name,b.architecture
                                FROM code_review_groups g
                                LEFT JOIN code_engine_runs r
                                  ON r.run_key=g.run_key
                                LEFT JOIN code_binaries b
                                  ON b.binary_key=r.binary_key
                                WHERE (?='' OR b.architecture=?)
                                ORDER BY g.priority DESC,g.engine_id,
                                         b.module_name,b.architecture
                                LIMIT 250
                                """,
                                (architecture, architecture),
                            )
                        ]
                        self._json({"groups": groups})
                        return
                    rva_match = re.fullmatch(
                        r"(?:rva:)?(?:0x)?([0-9a-fA-F]{1,16})", query
                    )
                    hash_match = re.fullmatch(
                        r"hash:([0-9a-fA-F]{8,64})", query, re.IGNORECASE
                    )
                    type_match = re.fullmatch(
                        r"(?:class|vtable):(.+)", query, re.IGNORECASE
                    )
                    relation_match = re.fullmatch(
                        r"(caller|callee):(.+)", query, re.IGNORECASE
                    )
                    if not query and semantic_available and any(
                        (semantic_domain, impact_tier, uncertainty, closure_status)
                    ):
                        rows = connection.execute(
                            """
                            SELECT s.function_key,s.module_name,s.architecture,
                                   s.primary_name,f.entry_rva
                            FROM semantic.semantic_function_classifications sf
                            JOIN code_functions f USING(function_key)
                            JOIN code_search s USING(function_key)
                            WHERE (?='' OR sf.domain=?)
                              AND (?='' OR sf.impact_tier=?)
                              AND (?='' OR sf.uncertainty_score>0)
                              AND (?='' OR EXISTS(
                                  SELECT 1 FROM semantic.semantic_root_functions rf
                                  JOIN semantic.semantic_closures sc USING(root_key)
                                  WHERE rf.function_key=sf.function_key
                                    AND sc.closure_status=?
                              ))
                              AND (?='' OR s.architecture=?)
                            ORDER BY sf.impact_score DESC,sf.uncertainty_score DESC,
                                     s.module_name,f.entry_rva LIMIT 250
                            """,
                            (
                                semantic_domain, semantic_domain,
                                impact_tier, impact_tier,
                                uncertainty,
                                closure_status, closure_status,
                                architecture, architecture,
                            ),
                        )
                    elif not query and filter_value:
                        if filter_value == "actionable":
                            predicate = (
                                "EXISTS(SELECT 1 FROM code_review_queue q "
                                "WHERE q.function_key=f.function_key)"
                            )
                        elif filter_value == "consumer-linked":
                            predicate = (
                                "EXISTS(SELECT 1 FROM code_evidence_links l "
                                "WHERE l.function_key=f.function_key)"
                            )
                        elif filter_value == "opaque-critical":
                            predicate = (
                                "EXISTS(SELECT 1 FROM code_review_queue q "
                                "WHERE q.function_key=f.function_key "
                                "AND q.reason_code='opaque_critical')"
                            )
                        elif not semantic_available:
                            predicate = "0"
                        elif filter_value == "critical-root":
                            predicate = (
                                "EXISTS(SELECT 1 FROM semantic.semantic_function_classifications sf "
                                "WHERE sf.function_key=f.function_key AND sf.category='critical_root')"
                            )
                        elif filter_value == "opaque-blocking":
                            predicate = (
                                "EXISTS(SELECT 1 FROM semantic.semantic_opaque_regions so "
                                "WHERE so.primary_function_key=f.function_key "
                                "AND so.classification='critical_blocker')"
                            )
                        else:
                            predicate = (
                                "EXISTS(SELECT 1 FROM semantic.semantic_indirect_sites si "
                                "WHERE si.function_key=f.function_key)"
                            )
                        rows = connection.execute(
                            f"""
                            SELECT DISTINCT s.function_key,s.module_name,
                                   s.architecture,s.primary_name,f.entry_rva
                            FROM code_search s
                            JOIN code_functions f
                              ON f.function_key=s.function_key
                            WHERE {predicate}
                              AND (?='' OR s.architecture=?)
                            ORDER BY s.module_name,s.architecture,f.entry_rva
                            LIMIT 250
                            """,
                            (architecture, architecture),
                        )
                    elif rva_match:
                        rva = int(rva_match.group(1), 16)
                        rows = connection.execute(
                            """
                            SELECT function_key,module_name,architecture,
                                   primary_name,entry_rva
                            FROM (
                                SELECT s.function_key,s.module_name,
                                       s.architecture,s.primary_name,f.entry_rva
                                FROM code_functions f
                                JOIN code_search s
                                  ON s.function_key=f.function_key
                                WHERE f.entry_rva=?
                                  AND (?='' OR s.architecture=?)
                                UNION
                                SELECT s.function_key,s.module_name,
                                       s.architecture,s.primary_name,f.entry_rva
                                FROM code_vtables v
                                JOIN code_vtable_slots vs
                                  ON vs.vtable_key=v.vtable_key
                                JOIN code_functions f
                                  ON f.function_key=vs.target_function_key
                                JOIN code_search s
                                  ON s.function_key=f.function_key
                                WHERE v.rva=?
                                  AND (?='' OR s.architecture=?)
                            )
                            ORDER BY module_name,entry_rva LIMIT 250
                            """,
                            (
                                rva,
                                architecture,
                                architecture,
                                rva,
                                architecture,
                                architecture,
                            ),
                        )
                    elif hash_match:
                        prefix_value = hash_match.group(1).upper() + "%"
                        rows = connection.execute(
                            """
                            SELECT s.function_key,s.module_name,s.architecture,
                                   s.primary_name,f.entry_rva
                            FROM code_search s
                            JOIN code_functions f
                              ON f.function_key=s.function_key
                            JOIN code_binaries b ON b.binary_key=f.binary_key
                            WHERE (f.byte_sha256 LIKE ? OR
                                   f.mnemonic_sha256 LIKE ? OR b.sha256 LIKE ?)
                              AND (?='' OR s.architecture=?)
                            ORDER BY s.module_name,f.entry_rva LIMIT 250
                            """,
                            (
                                prefix_value,
                                prefix_value,
                                prefix_value,
                                architecture,
                                architecture,
                            ),
                        )
                    elif relation_match:
                        relation = relation_match.group(1).lower()
                        pattern = "%" + relation_match.group(2).strip() + "%"
                        if relation == "caller":
                            rows = connection.execute(
                                """
                                SELECT DISTINCT s.function_key,s.module_name,
                                       s.architecture,s.primary_name,f.entry_rva
                                FROM code_calls c
                                JOIN code_functions f
                                  ON f.function_key=c.caller_function_key
                                JOIN code_search s
                                  ON s.function_key=f.function_key
                                LEFT JOIN code_names target_name
                                  ON target_name.function_key=c.callee_function_key
                                WHERE (target_name.name LIKE ? OR
                                       c.target_name LIKE ?)
                                  AND (?='' OR s.architecture=?)
                                ORDER BY s.module_name,f.entry_rva LIMIT 250
                                """,
                                (pattern, pattern, architecture, architecture),
                            )
                        else:
                            rows = connection.execute(
                                """
                                SELECT DISTINCT target_search.function_key,
                                       target_search.module_name,
                                       target_search.architecture,
                                       target_search.primary_name,target.entry_rva
                                FROM code_calls c
                                JOIN code_functions source
                                  ON source.function_key=c.caller_function_key
                                JOIN code_names source_name
                                  ON source_name.function_key=source.function_key
                                JOIN code_functions target
                                  ON target.function_key=c.callee_function_key
                                JOIN code_search target_search
                                  ON target_search.function_key=target.function_key
                                WHERE source_name.name LIKE ?
                                  AND (?='' OR target_search.architecture=?)
                                ORDER BY target_search.module_name,target.entry_rva
                                LIMIT 250
                                """,
                                (pattern, architecture, architecture),
                            )
                    elif type_match:
                        pattern = "%" + type_match.group(1).strip() + "%"
                        rows = connection.execute(
                            """
                            SELECT DISTINCT s.function_key,s.module_name,
                                   s.architecture,s.primary_name,f.entry_rva
                            FROM code_search s
                            JOIN code_functions f
                              ON f.function_key=s.function_key
                            JOIN code_vtable_slots vs
                              ON vs.target_function_key=f.function_key
                            JOIN code_vtables v
                              ON v.vtable_key=vs.vtable_key
                            LEFT JOIN code_types t ON t.type_key=v.type_key
                            WHERE (t.type_name LIKE ? OR
                                   printf('0x%x',v.rva) LIKE ?)
                              AND (?='' OR s.architecture=?)
                            ORDER BY s.module_name,f.entry_rva LIMIT 250
                            """,
                            (pattern, pattern, architecture, architecture),
                        )
                    elif query:
                        search_value = re.sub(
                            r"^(?:opcode|sql|id|name|module|string):",
                            "",
                            query,
                            flags=re.IGNORECASE,
                        ).strip() or query
                        terms = " ".join(
                            f'"{token.replace(chr(34), "")}"'
                            for token in search_value.split()
                            if token
                        )
                        rows = connection.execute(
                            """
                            SELECT s.function_key,s.module_name,s.architecture,
                                   s.primary_name,f.entry_rva
                            FROM code_search s
                            JOIN code_functions f
                              ON f.function_key=s.function_key
                            WHERE code_search MATCH ?
                              AND (?='' OR s.architecture=?)
                            ORDER BY rank,s.module_name,f.entry_rva LIMIT 250
                            """,
                            (terms, architecture, architecture),
                        )
                    else:
                        rows = connection.execute(
                            """
                            SELECT s.function_key,s.module_name,s.architecture,
                                   s.primary_name,f.entry_rva
                            FROM code_search s
                            JOIN code_functions f
                              ON f.function_key=s.function_key
                            WHERE (?='' OR s.architecture=?)
                            ORDER BY s.module_name,s.architecture,f.entry_rva
                            LIMIT 250
                            """,
                            (architecture, architecture),
                        )
                    result_rows = [dict(row) for row in rows]
                    if query and semantic_available and result_rows and any(
                        (semantic_domain, impact_tier, uncertainty, closure_status)
                    ):
                        keys = [str(item["function_key"]) for item in result_rows]
                        placeholders = ",".join("?" for _ in keys)
                        semantic_rows = connection.execute(
                            f"""
                            SELECT sf.function_key
                            FROM semantic.semantic_function_classifications sf
                            WHERE sf.function_key IN ({placeholders})
                              AND (?='' OR sf.domain=?)
                              AND (?='' OR sf.impact_tier=?)
                              AND (?='' OR sf.uncertainty_score>0)
                              AND (?='' OR EXISTS(
                                  SELECT 1 FROM semantic.semantic_root_functions rf
                                  JOIN semantic.semantic_closures sc USING(root_key)
                                  WHERE rf.function_key=sf.function_key
                                    AND sc.closure_status=?
                              ))
                            """,
                            keys + [
                                semantic_domain, semantic_domain,
                                impact_tier, impact_tier,
                                uncertainty,
                                closure_status, closure_status,
                            ],
                        )
                        accepted_semantic = {str(row[0]) for row in semantic_rows}
                        result_rows = [
                            item for item in result_rows
                            if item["function_key"] in accepted_semantic
                        ]
                    if query and filter_value and result_rows:
                        keys = [str(item["function_key"]) for item in result_rows]
                        placeholders = ",".join("?" for _ in keys)
                        if filter_value == "actionable":
                            filter_sql = (
                                "SELECT DISTINCT function_key FROM code_review_queue "
                                f"WHERE function_key IN ({placeholders})"
                            )
                        elif filter_value == "consumer-linked":
                            filter_sql = (
                                "SELECT DISTINCT function_key FROM code_evidence_links "
                                f"WHERE function_key IN ({placeholders})"
                            )
                        elif filter_value == "opaque-critical":
                            filter_sql = (
                                "SELECT DISTINCT function_key FROM code_review_queue "
                                "WHERE reason_code='opaque_critical' AND "
                                f"function_key IN ({placeholders})"
                            )
                        elif filter_value == "critical-root" and semantic_available:
                            filter_sql = (
                                "SELECT function_key FROM semantic.semantic_function_classifications "
                                "WHERE category='critical_root' AND "
                                f"function_key IN ({placeholders})"
                            )
                        elif filter_value == "opaque-blocking" and semantic_available:
                            filter_sql = (
                                "SELECT DISTINCT primary_function_key FROM semantic.semantic_opaque_regions "
                                "WHERE classification='critical_blocker' AND "
                                f"primary_function_key IN ({placeholders})"
                            )
                        elif filter_value == "indirect-dispatch" and semantic_available:
                            filter_sql = (
                                "SELECT DISTINCT function_key FROM semantic.semantic_indirect_sites WHERE "
                                f"function_key IN ({placeholders})"
                            )
                        else:
                            filter_sql = "SELECT NULL WHERE 0"
                        accepted = {
                            str(row[0])
                            for row in connection.execute(filter_sql, keys)
                        }
                        result_rows = [
                            item
                            for item in result_rows
                            if item["function_key"] in accepted
                        ]
                    self._json({"results": result_rows})
                    return
                prefix = "/api/function/"
                if parsed.path.startswith(prefix):
                    key = unquote(parsed.path[len(prefix) :])
                    payload = _function_payload(connection, key)
                    if semantic_available:
                        classification = connection.execute(
                            "SELECT * FROM semantic.semantic_function_classifications WHERE function_key=?",
                            (key,),
                        ).fetchone()
                        payload["semantic"] = {
                            "classification": dict(classification) if classification else None,
                            "roots": [dict(row) for row in connection.execute(
                                """
                                SELECT r.root_kind,r.scope_key,r.name,r.domain,r.state,
                                       rf.direction,rf.depth,rf.impact_score,rf.path_json
                                FROM semantic.semantic_root_functions rf
                                JOIN semantic.semantic_roots r USING(root_key)
                                WHERE rf.function_key=?
                                ORDER BY rf.impact_score DESC,rf.root_key LIMIT 100
                                """,
                                (key,),
                            )],
                            "indirect_sites": [dict(row) for row in connection.execute(
                                "SELECT * FROM semantic.semantic_indirect_sites WHERE function_key=? ORDER BY callsite_rva",
                                (key,),
                            )],
                            "opaque_blockers": [dict(row) for row in connection.execute(
                                "SELECT * FROM semantic.semantic_opaque_regions WHERE primary_function_key=? ORDER BY impact_score DESC,region_key",
                                (key,),
                            )],
                        }
                    self._json(payload)
                    return
                self._json({"error": "not_found"}, status=404)
            except (KeyError, sqlite3.Error, ValueError) as exc:
                self._json({"error": str(exc)}, status=400)
            finally:
                connection.close()

        def log_message(self, format: str, *args: Any) -> None:
            print(f"native-code-viewer: {format % args}")

    server = ThreadingHTTPServer((bind, port), Handler)
    print(f"AA8 native-code viewer: http://{bind}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
