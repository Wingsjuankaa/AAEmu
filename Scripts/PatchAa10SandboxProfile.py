"""Route only a dedicated r575 sandbox client's native save directory to E:.

The approved xlcommon.dll export is replaced within its own .pdata function
extent. Its original prologue and unwind contract stay intact. The replacement
copies a bounded UTF-16 path without querying Windows folders or creating them.
The sandbox launcher must prepare the directory before opening the client.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath
import struct
import sys
import uuid


PATCH_ID = "aa10-sandbox-e-profile-v1"
SOURCE_SHA256 = "513cbce7c62c734b504adeb0bf7bb7e52feac74166ec67b131a322be4bd8e565"
EXPORT = "?XlGetSafeSaveGameDir@@YA_NPEAGH@Z"
FUNCTION_RVA = 0x1BCB0
FUNCTION_END = 0x1BEA0
FUNCTION_OFFSET = 0x1B0B0
PROLOGUE = bytes.fromhex("48895c24084889742410574881ece0060000")
PROJECT = Path("E:/AAEmu/rama_10")
PRIMARY = PROJECT / "client/ArcheAge-Returns-10.0.2.13-r575-es_ES-full-preview"
REFERENCE = PROJECT / "client/ArcheAge-Returns-10.0.2.13-r575"
DEFAULT_SOURCE = PRIMARY / "Bin64/xlcommon.dll"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def profile_value(value: str) -> str:
    if "\x00" in value:
        raise ValueError("El perfil contiene NUL.")
    path = PureWindowsPath(value)
    if not path.is_absolute() or path.drive.upper() != "E:":
        raise ValueError("El perfil sandbox debe ser una ruta absoluta del disco E.")
    normalized = ntpath.normpath(str(path))
    if normalized == "E:\\":
        raise ValueError("El perfil no puede ser la raíz del disco.")
    # Windows counts UTF-16 code units, not Python Unicode code points.
    if len(normalized.encode("utf-16-le")) // 2 + 1 > 200:
        raise ValueError("El perfil excede el espacio acotado del parche (199 unidades UTF-16).")
    return normalized


def pe_contract(data: bytes) -> dict:
    if data[:2] != b"MZ":
        raise ValueError("No es un PE válido.")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\x00\x00" or struct.unpack_from("<H", data, pe + 4)[0] != 0x8664:
        raise ValueError("Se requiere el PE x64 r575.")
    optional = pe + 24
    if struct.unpack_from("<H", data, optional)[0] != 0x20B:
        raise ValueError("Se requiere PE32+.")
    count = struct.unpack_from("<H", data, pe + 6)[0]
    table = optional + struct.unpack_from("<H", data, pe + 20)[0]
    sections = []
    for index in range(count):
        offset = table + 40 * index
        virtual_size, rva, raw_size, raw = struct.unpack_from("<IIII", data, offset + 8)
        flags = struct.unpack_from("<I", data, offset + 36)[0]
        sections.append((rva, raw_size, raw, flags, virtual_size))

    def offset(rva: int) -> int:
        for start, size, raw, _, _ in sections:
            if start <= rva < start + size:
                return raw + rva - start
        raise ValueError(f"RVA fuera de secciones: {rva:#x}")

    export_rva, _ = struct.unpack_from("<II", data, optional + 112)
    export_offset = offset(export_rva)
    _, functions, names, function_table, name_table, ordinal_table = struct.unpack_from(
        "<IIIIII", data, export_offset + 16)
    found = None
    for index in range(names):
        name_rva = struct.unpack_from("<I", data, offset(name_table) + 4 * index)[0]
        start = offset(name_rva)
        name = data[start:data.index(b"\x00", start)].decode("ascii")
        if name == EXPORT:
            ordinal = struct.unpack_from("<H", data, offset(ordinal_table) + 2 * index)[0]
            if ordinal >= functions:
                raise ValueError("Ordinal inválido.")
            found = struct.unpack_from("<I", data, offset(function_table) + 4 * ordinal)[0]
    if found != FUNCTION_RVA:
        raise ValueError("El export no coincide con el contrato r575.")
    pdata_rva, pdata_size = struct.unpack_from("<II", data, optional + 112 + 3 * 8)
    bounds = []
    for entry in range(offset(pdata_rva), offset(pdata_rva) + pdata_size, 12):
        begin, end, unwind = struct.unpack_from("<III", data, entry)
        if begin <= FUNCTION_RVA < end:
            bounds.append((begin, end, unwind))
    if len(bounds) != 1 or bounds[0][:2] != (FUNCTION_RVA, FUNCTION_END):
        raise ValueError("La frontera .pdata no coincide con la función aprobada.")
    if offset(FUNCTION_RVA) != FUNCTION_OFFSET:
        raise ValueError("Offset de la función inesperado.")
    if not any(start <= FUNCTION_RVA < FUNCTION_END <= start + size and flags & 0x20000000
               for start, size, _, flags, _ in sections):
        raise ValueError("La función no está contenida en una sección ejecutable.")
    if data[FUNCTION_OFFSET:FUNCTION_OFFSET + len(PROLOGUE)] != PROLOGUE:
        raise ValueError("El prólogo/unwind nativo no coincide.")
    reloc_rva, reloc_size = struct.unpack_from("<II", data, optional + 112 + 5 * 8)
    cursor, limit = offset(reloc_rva), offset(reloc_rva) + reloc_size
    while cursor < limit:
        page, size = struct.unpack_from("<II", data, cursor)
        if size < 8 or cursor + size > limit:
            raise ValueError("Directorio de relocaciones inválido.")
        for entry in range(cursor + 8, cursor + size, 2):
            kind_offset = struct.unpack_from("<H", data, entry)[0]
            if kind_offset >> 12 and FUNCTION_RVA <= page + (kind_offset & 0xFFF) < FUNCTION_END:
                raise ValueError("Una relocación se superpone al reemplazo.")
        cursor += size
    return {"rva": FUNCTION_RVA, "end_rva": FUNCTION_END, "file_offset": FUNCTION_OFFSET,
            "span": FUNCTION_END - FUNCTION_RVA, "unwind_rva": bounds[0][2],
            "prologue_preserved_bytes": len(PROLOGUE), "relocations_in_patch": 0}


def build_patch(source: bytes, profile: str) -> tuple[bytes, dict]:
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("xlcommon.dll no tiene el SHA-256 r575 aprobado; no se modificó.")
    contract = pe_contract(source)
    profile = profile_value(profile)
    path = profile.encode("utf-16-le") + b"\x00\x00"
    units = len(path) // 2
    code = bytearray(PROLOGUE)
    labels, fixups = {}, []

    def jump(opcode: int, label: str) -> None:
        code.extend((opcode, 0))
        fixups.append((len(code) - 1, label))

    code.extend(bytes.fromhex("4885c9"))             # test rcx,rcx (output)
    jump(0x74, "fail")                              # null: return false
    code.extend(bytes.fromhex("81fa") + struct.pack("<I", units))
    jump(0x7C, "fail")                              # signed count < path+NUL
    code.extend(bytes.fromhex("4c8d05"))             # lea r8,[rip+path]
    rip_fixup = len(code)
    code.extend(b"\x00" * 4)
    code.extend(bytes.fromhex("41b9") + struct.pack("<I", units))
    labels["copy"] = len(code)
    code.extend(bytes.fromhex("410fb7006689014983c0024883c10241ffc9"))
    jump(0x75, "copy")                              # includes terminating NUL
    code.extend(bytes.fromhex("b801000000"))         # bool true
    jump(0xEB, "return")
    labels["fail"] = len(code)
    code.extend(bytes.fromhex("31c0"))
    labels["return"] = len(code)
    code.extend(bytes.fromhex("4881c4e00600005fc3")) # original stack frame/pop rdi
    path_offset = len(code)
    struct.pack_into("<i", code, rip_fixup, path_offset - (rip_fixup + 4))
    for position, label in fixups:
        relative = labels[label] - (position + 1)
        if not -128 <= relative <= 127:
            raise ValueError("Salto fuera del stub acotado.")
        code[position] = relative & 0xFF
    payload = bytes(code) + path
    if len(payload) > contract["span"]:
        raise ValueError("El stub excede la frontera original.")
    payload += b"\xCC" * (contract["span"] - len(payload))
    patched = source[:FUNCTION_OFFSET] + payload + source[FUNCTION_OFFSET + contract["span"]:]
    assert len(patched) == len(source)
    return patched, {"patch_id": PATCH_ID, "source_sha256": SOURCE_SHA256,
                     "target_sha256": sha256(patched), "profile_path": profile,
                     "bytes": len(source), "function": contract,
                     "stub_code_bytes": len(code), "path_utf16_units_with_nul": units}


def local_e_path(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    if absolute.drive.upper() != "E:":
        raise ValueError("Los archivos del sandbox deben residir en E.")
    for candidate in (absolute, *absolute.parents):
        if candidate.exists() and candidate.stat(follow_symlinks=False).st_file_attributes & 0x400:
            raise ValueError(f"La ruta contiene una redirección: {candidate}")
    return absolute


def atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        if path.read_bytes() != data:
            raise OSError(f"No se verificó la escritura: {path}")
    finally:
        temporary.unlink(missing_ok=True)


def process(client_root: Path, profile: str, mode: str = "inspect", source_dll: Path = DEFAULT_SOURCE) -> dict:
    if mode not in {"inspect", "apply", "rollback"}:
        raise ValueError("Modo desconocido.")
    root = local_e_path(client_root)
    for protected in (PRIMARY, REFERENCE):
        if root == protected or root.is_relative_to(protected):
            raise ValueError("Este parche sólo admite una copia dedicada del sandbox.")
    dll = local_e_path(root / "Bin64/xlcommon.dll")
    if dll.stat().st_nlink != 1:
        raise ValueError("La DLL no puede ser un hardlink a otro cliente.")
    source = source_dll.read_bytes()
    patched, manifest = build_patch(source, profile)
    current = dll.read_bytes()
    current_hash = sha256(current)
    if current_hash not in {SOURCE_SHA256, manifest["target_sha256"]}:
        raise ValueError("La DLL de destino tiene cambios desconocidos; no se modificó.")
    backup_root = local_e_path(root / ".aa10-sandbox-profile-backup")
    manifest_path = backup_root / "manifest.json"
    old_manifest = manifest_path.read_bytes() if manifest_path.exists() else None
    if old_manifest is not None:
        previous = json.loads(old_manifest)
        if {k: v for k, v in previous.items() if k != "state"} != manifest:
            raise ValueError("El manifiesto existente pertenece a otro perfil/parche.")
    marker_path = local_e_path(root / ".aa10-sandbox-profile.json")
    old_marker = marker_path.read_bytes() if marker_path.exists() else None
    marker_base = {"schemaVersion": 1, "patchId": PATCH_ID,
                   "profilePath": manifest["profile_path"], "originalSha256": SOURCE_SHA256,
                   "dllPath": "Bin64/xlcommon.dll"}
    if old_marker is not None and json.loads(old_marker) != {**marker_base, "currentSha256": current_hash}:
        raise ValueError("El marcador de perfil sandbox tiene cambios desconocidos.")
    result = {**manifest, "state": "applied" if current_hash == manifest["target_sha256"] else "original",
              "client_root": str(root), "current_sha256": current_hash, "mode": mode}
    if mode == "inspect":
        return result
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / (SOURCE_SHA256 + ".xlcommon.dll")
    if backup.exists() and backup.read_bytes() != source:
        raise ValueError("El respaldo existente no coincide con la DLL aprobada.")
    if not backup.exists():
        atomic_write(backup, source)
    desired = source if mode == "rollback" else patched
    state = "original" if mode == "rollback" else "applied"
    new_manifest = (json.dumps({**manifest, "state": state}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    new_marker = (json.dumps({**marker_base, "currentSha256": sha256(desired)},
                             ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if dll.read_bytes() != current:
        raise ValueError("La DLL cambió durante la preparación; no se aplicó el parche.")
    try:
        if current != desired:
            atomic_write(dll, desired)
        if old_manifest != new_manifest:
            atomic_write(manifest_path, new_manifest)
        if mode == "rollback":
            marker_path.unlink(missing_ok=True)
        elif old_marker != new_marker:
            atomic_write(marker_path, new_marker)
    except BaseException:
        if dll.read_bytes() != current:
            atomic_write(dll, current)
        if old_manifest is not None:
            atomic_write(manifest_path, old_manifest)
        else:
            manifest_path.unlink(missing_ok=True)
        if old_marker is not None:
            atomic_write(marker_path, old_marker)
        else:
            marker_path.unlink(missing_ok=True)
        raise
    return {**result, "state": state, "current_sha256": sha256(desired), "changed": current != desired,
            "backup": str(backup), "manifest": str(manifest_path), "marker": str(marker_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-root", type=Path, required=True)
    parser.add_argument("--profile-path", required=True)
    parser.add_argument("--mode", choices=("inspect", "apply", "rollback"), default="inspect")
    parser.add_argument("--source-dll", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    try:
        result = process(args.client_root, args.profile_path, args.mode, args.source_dll)
    except (OSError, ValueError, struct.error) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
