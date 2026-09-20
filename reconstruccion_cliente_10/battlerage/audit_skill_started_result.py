"""Reanchor the five Ghidra result-lifecycle functions to the effective r575 PE.

Read-only. Usage: python audit_skill_started_result.py RELEASE EFFECTIVE GHIDRA_LOG
Prints JSON; rejects another binary revision or any changed consumer byte range.
"""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

EXPECTED = (
    "2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76",
    "405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734",
)
BASE = 0x39000000


def load_pe(path, expected):
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != expected:
        raise ValueError(f"Unexpected SHA-256: {path}: {sha}")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    machine, count = struct.unpack_from("<HH", data, pe + 4)
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    magic = struct.unpack_from("<H", data, pe + 24)[0]
    image_base = struct.unpack_from("<Q", data, pe + 48)[0]
    if data[pe:pe + 4] != b"PE\0\0" or machine != 0x8664 or magic != 0x20B or image_base != BASE:
        raise ValueError("Expected r575 x64 image base 0x39000000")
    sections = []
    for index in range(count):
        offset = pe + 24 + optional_size + 40 * index
        _, rva, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((rva, raw_size, raw_offset))
    return data, sections


def extract(pe, start, end):
    data, sections = pe
    for rva, size, offset in sections:
        if rva <= start <= end < rva + size:
            return data[offset + start - rva:offset + end - rva + 1]
    raise ValueError(f"Unmapped function span: {start:x}-{end:x}")


def main():
    release = load_pe(sys.argv[1], EXPECTED[0])
    effective = load_pe(sys.argv[2], EXPECTED[1])
    log = Path(sys.argv[3]).read_text(encoding="utf-8-sig")
    ranges = re.findall(r"FUNCTION=([0-9a-f]+) END=([0-9a-f]+)", log)
    if {start for start, _ in ranges} != {"39ac68c0", "3933bcd0", "396dee00", "396d5290", "396d6240"}:
        raise ValueError("Missing or unexpected consumer functions")
    functions = []
    for start, end in ranges:
        start, end = int(start, 16) - BASE, int(end, 16) - BASE
        original, current = extract(release, start, end), extract(effective, start, end)
        if original != current:
            raise ValueError(f"Changed native consumer: RVA {start:x}")
        functions.append({"rva": hex(start), "end_rva": hex(end), "length": len(original),
                          "sha256": hashlib.sha256(original).hexdigest(), "effective_equal": True})
    print(json.dumps({"release_sha256": EXPECTED[0], "effective_sha256": EXPECTED[1],
                      "image_base": hex(BASE), "functions": functions}, indent=2))


if __name__ == "__main__":
    main()
