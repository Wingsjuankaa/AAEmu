from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class CachedStringSignature:
    offset: int
    value: str


def cached_string_signatures(
    data: bytes,
    *,
    max_string_bytes: int = 4096,
) -> tuple[CachedStringSignature, ...]:
    """Find structurally valid AA8 new-interned-string encodings.

    A signature is only a candidate.  Callers must bracket every ordinal
    projection with independently demonstrated reference anchors.
    """

    marker = b"\x01\xff\xff\xff\xff"
    result: list[CachedStringSignature] = []
    cursor = 0
    while True:
        offset = data.find(marker, cursor)
        if offset < 0:
            break
        cursor = offset + 1
        value_start = offset + len(marker)
        value_end = data.find(
            b"\0",
            value_start,
            min(len(data), value_start + max_string_bytes + 1),
        )
        if value_end < 0:
            continue
        raw = data[value_start:value_end]
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not all(char in "\t\r\n" or ord(char) >= 32 for char in value):
            continue
        result.append(CachedStringSignature(offset=offset, value=value))
    return tuple(result)


def string_cache_digest(values: dict[int, str], expected_count: int) -> str:
    """Hash an ordinal string map without materialising a large JSON value."""

    if set(values) != set(range(expected_count)):
        raise ValueError("String cache is not a continuous zero-based map")
    digest = hashlib.sha256()
    for reference in range(expected_count):
        raw = values[reference].encode("utf-8")
        digest.update(struct.pack("<II", reference, len(raw)))
        digest.update(raw)
    return digest.hexdigest().upper()
