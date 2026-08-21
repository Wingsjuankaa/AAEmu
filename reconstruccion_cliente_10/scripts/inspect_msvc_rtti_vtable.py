#!/usr/bin/env python3
"""Locate MSVC x64 RTTI vtables in a PE and disassemble their entries.

This is a read-only lead generator for the AA10 native corpus.  It does not
promote semantics by itself: callers must still identify the virtual entry and
validate every field against the exact client/Zone build.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86 import X86_OP_MEM, X86_REG_RIP


def iter_occurrences(blob: bytes, needle: bytes):
    start = 0
    while True:
        offset = blob.find(needle, start)
        if offset < 0:
            return
        yield offset
        start = offset + 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pe", type=Path)
    parser.add_argument("type_name", nargs="?", help="substring of the decorated RTTI type name")
    parser.add_argument("--function-rva", help="disassemble one function RVA instead of resolving RTTI")
    parser.add_argument("--entries", type=int, default=12)
    parser.add_argument("--entry", type=int, help="disassemble only this zero-based vtable entry")
    parser.add_argument("--instructions", type=int, default=60)
    args = parser.parse_args()

    blob = args.pe.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    image = pe.get_memory_mapped_image()
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    def rip_comment(insn) -> str:
        for operand in insn.operands:
            if operand.type != X86_OP_MEM or operand.mem.base != X86_REG_RIP:
                continue
            target_va = insn.address + insn.size + operand.mem.disp
            target_rva = target_va - image_base
            if target_rva < 0 or target_rva >= len(image):
                continue
            raw = image[target_rva : target_rva + 160]
            end = raw.find(b"\0")
            if end <= 0:
                continue
            candidate = raw[:end]
            if all(0x20 <= value < 0x7F for value in candidate):
                return f' ; 0x{target_va:X} "{candidate.decode("ascii")}"'
        return ""

    def disassemble(function_rva: int, indent: str = "") -> None:
        function_va = image_base + function_rva
        code = image[function_rva : function_rva + 0x1000]
        for insn_index, insn in enumerate(md.disasm(code, function_va)):
            if insn_index >= args.instructions:
                break
            print(
                f"{indent}{insn.address:016X}  {insn.mnemonic:8} {insn.op_str}"
                f"{rip_comment(insn)}"
            )
            if insn.mnemonic.startswith("ret"):
                break

    if args.function_rva:
        function_rva = int(args.function_rva, 0)
        print(f"FUNCTION rva=0x{function_rva:X} va=0x{image_base + function_rva:X}")
        disassemble(function_rva, "  ")
        return 0

    if not args.type_name:
        parser.error("type_name is required unless --function-rva is supplied")

    executable_ranges = []
    for section in pe.sections:
        if section.Characteristics & 0x20000000:
            start = image_base + section.VirtualAddress
            size = max(section.Misc_VirtualSize, section.SizeOfRawData)
            executable_ranges.append((start, start + size))

    def executable(va: int) -> bool:
        return any(start <= va < end for start, end in executable_ranges)

    matches = []
    for raw_offset in iter_occurrences(blob, args.type_name.encode("ascii")):
        string_rva = pe.get_rva_from_offset(raw_offset)
        type_descriptor_rva = string_rva - 16
        matches.append((raw_offset, type_descriptor_rva))

    if not matches:
        raise SystemExit(f"RTTI string not found: {args.type_name}")

    for raw_offset, type_descriptor_rva in matches:
        end = blob.find(b"\0", raw_offset)
        decorated = blob[raw_offset:end].decode("ascii", errors="replace")
        print(f"TYPE {decorated} type_descriptor_rva=0x{type_descriptor_rva:X}")

        encoded_type = struct.pack("<I", type_descriptor_rva)
        col_rvas = []
        for type_ref_offset in iter_occurrences(image, encoded_type):
            col_rva = type_ref_offset - 12
            if col_rva < 0 or col_rva + 24 > len(image):
                continue
            signature, offset, cd_offset, p_type, p_class, p_self = struct.unpack_from(
                "<IIIIII", image, col_rva
            )
            if signature not in (0, 1) or p_type != type_descriptor_rva:
                continue
            if signature == 1 and p_self != col_rva:
                continue
            if col_rva not in col_rvas:
                col_rvas.append(col_rva)

        for col_rva in col_rvas:
            col_va = image_base + col_rva
            print(f"  COL rva=0x{col_rva:X} va=0x{col_va:X}")
            encoded_col = struct.pack("<Q", col_va)
            for col_ref_offset in iter_occurrences(image, encoded_col):
                vtable_rva = col_ref_offset + 8
                first_va = struct.unpack_from("<Q", image, vtable_rva)[0]
                if not executable(first_va):
                    continue
                print(f"    VTABLE rva=0x{vtable_rva:X} va=0x{image_base + vtable_rva:X}")
                entry_indexes = [args.entry] if args.entry is not None else range(args.entries)
                for index in entry_indexes:
                    slot_rva = vtable_rva + index * 8
                    if slot_rva + 8 > len(image):
                        break
                    function_va = struct.unpack_from("<Q", image, slot_rva)[0]
                    if not executable(function_va):
                        break
                    function_rva = function_va - image_base
                    print(f"      ENTRY {index} rva=0x{function_rva:X} va=0x{function_va:X}")
                    disassemble(function_rva, "        ")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
