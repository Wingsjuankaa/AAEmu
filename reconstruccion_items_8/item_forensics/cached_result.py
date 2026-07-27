from __future__ import annotations

import struct
from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Iterable


SQLITE_ROW = 100
SQLITE_DONE = 101
SUPPORTED_LAYOUTS = {"38", "40", "60", "68", "70", "78"}


class CachedResultError(ValueError):
    pass


@dataclass(frozen=True)
class DecodedResult:
    rows: tuple[tuple[Any, ...], ...]
    start: int
    end: int
    raw_references: tuple[int, ...]
    unresolved_references: tuple[int, ...]
    resolved_forward_references: tuple[int, ...]
    strings_captured: int


@dataclass(frozen=True)
class ResultHeader:
    header: int
    start: int
    row_count: int


@dataclass(frozen=True)
class CachedStringSignature:
    offset: int
    value: str


@dataclass(frozen=True)
class StringCacheRecovery:
    values: dict[int, str]
    candidate_index_delta: int
    calibration_evidence: tuple[dict[str, Any], ...]


def cached_string_signatures(
    data: bytes,
    *,
    max_string_bytes: int = 4096,
) -> tuple[CachedStringSignature, ...]:
    """Find structurally valid native "new interned string" encodings.

    The byte signature alone is not enough to assign reference numbers.  Call
    ``recover_calibrated_string_cache`` with independently proven loader
    boundaries before treating any candidate as authoritative.
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


def recover_calibrated_string_cache(
    data: bytes,
    references: Iterable[int],
    calibrations: Iterable[dict[str, Any]],
) -> StringCacheRecovery:
    """Recover global string references bracketed by native calibrations.

    A calibration states the first reference captured by a confirmed cached
    result and that result's byte range.  Every calibration must point to the
    same candidate-index delta.  Requested references must be bracketed by
    calibration points, preventing unproven extrapolation across opaque
    regions or cache resets.
    """
    requested = tuple(sorted(set(int(value) for value in references)))
    if not requested:
        return StringCacheRecovery({}, 0, ())
    signatures = cached_string_signatures(data)
    offsets = tuple(entry.offset for entry in signatures)
    evidence: list[dict[str, Any]] = []
    deltas: set[int] = set()
    points: list[tuple[int, int]] = []
    for raw in calibrations:
        start = int(raw["start"])
        end = int(raw["end"])
        first_reference = int(raw["first_reference"])
        candidate_index = bisect_left(offsets, start)
        if candidate_index >= len(signatures):
            raise CachedResultError(
                f"No cached-string signature after calibration 0x{start:X}"
            )
        signature = signatures[candidate_index]
        if signature.offset > end:
            raise CachedResultError(
                "Calibration has no cached-string signature inside "
                f"0x{start:X}-0x{end:X}"
            )
        delta = candidate_index - first_reference
        deltas.add(delta)
        points.append((first_reference, candidate_index))
        evidence.append(
            {
                "source": raw.get("source"),
                "start": start,
                "end": end,
                "first_reference": first_reference,
                "first_signature_offset": signature.offset,
                "candidate_index": candidate_index,
                "candidate_index_delta": delta,
            }
        )
    if len(deltas) != 1:
        raise CachedResultError(
            "String-cache calibrations disagree on candidate-index delta: "
            + ", ".join(str(value) for value in sorted(deltas))
        )
    lower = min(reference for reference, _ in points)
    upper = max(reference for reference, _ in points)
    if requested[0] < lower or requested[-1] >= upper:
        raise CachedResultError(
            "Requested string references are not bracketed by calibrations: "
            f"{requested[0]}..{requested[-1]} outside {lower}..{upper - 1}"
        )
    delta = next(iter(deltas))
    values: dict[int, str] = {}
    for reference in requested:
        candidate_index = reference + delta
        if candidate_index < 0 or candidate_index >= len(signatures):
            raise CachedResultError(
                f"Calibrated string reference {reference} is out of range"
            )
        values[reference] = signatures[candidate_index].value
    return StringCacheRecovery(
        values=values,
        candidate_index_delta=delta,
        calibration_evidence=tuple(evidence),
    )


class CachedResultReader:
    """Strict reader for the Kakao cached SQLite result encoding."""

    def __init__(self, data: bytes):
        self.data = data
        self._string_cache: dict[int, str] = {}
        self._next_string_reference: int | None = None
        self._capture_count = 0

    def seed_string_cache(
        self,
        values: dict[int, str] | None = None,
        next_reference: int | None = None,
    ) -> None:
        self._string_cache = dict(values or {})
        self._next_string_reference = next_reference
        self._capture_count = 0

    @property
    def string_cache(self) -> dict[int, str]:
        return dict(self._string_cache)

    @property
    def capture_count(self) -> int:
        return self._capture_count

    def _require(self, offset: int, size: int) -> None:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise CachedResultError(
                f"Cached result truncated at 0x{offset:X}; need {size} byte(s)"
            )

    def string(self, offset: int) -> tuple[str | None, int, int | None]:
        self._require(offset, 1)
        tag = self.data[offset]
        offset += 1
        if tag == 2:
            return None, offset, None
        if tag == 0:
            try:
                end = self.data.index(0, offset)
            except ValueError as exc:
                raise CachedResultError(
                    f"Unterminated direct string at 0x{offset:X}"
                ) from exc
            return self.data[offset:end].decode("utf-8", "replace"), end + 1, None
        self._require(offset, 4)
        reference = struct.unpack_from("<I", self.data, offset)[0]
        offset += 4
        if reference == 0xFFFFFFFF:
            try:
                end = self.data.index(0, offset)
            except ValueError as exc:
                raise CachedResultError(
                    f"Unterminated cached string at 0x{offset:X}"
                ) from exc
            value = self.data[offset:end].decode("utf-8", "replace")
            if self._next_string_reference is not None:
                self._string_cache[self._next_string_reference] = value
                self._next_string_reference += 1
                self._capture_count += 1
            return value, end + 1, None
        value = self._string_cache.get(reference)
        if value is None:
            return f"<ref:{reference}>", offset, reference
        return value, offset, None

    def row(
        self,
        offset: int,
        layout: Iterable[str],
    ) -> tuple[tuple[Any, ...], int, tuple[int, ...]]:
        layout_values = tuple(layout)
        unsupported = set(layout_values) - SUPPORTED_LAYOUTS
        if unsupported:
            raise CachedResultError(
                "Unsupported cached-result field type(s): "
                + ", ".join(sorted(unsupported))
            )
        self._require(offset, 1)
        if self.data[offset] != SQLITE_ROW:
            raise CachedResultError(f"Expected SQLITE_ROW at 0x{offset:X}")
        offset += 1
        values: list[Any] = []
        unresolved: list[int] = []
        for field_type in layout_values:
            if field_type == "38":
                self._require(offset, 1)
                values.append(self.data[offset])
                offset += 1
            elif field_type == "68":
                self._require(offset, 4)
                values.append(struct.unpack_from("<i", self.data, offset)[0])
                offset += 4
            elif field_type in ("40", "70"):
                self._require(offset, 8)
                values.append(struct.unpack_from("<q", self.data, offset)[0])
                offset += 8
            elif field_type == "60":
                self._require(offset, 8)
                values.append(struct.unpack_from("<d", self.data, offset)[0])
                offset += 8
            elif field_type == "78":
                value, offset, reference = self.string(offset)
                values.append(value)
                if reference is not None:
                    unresolved.append(reference)
        return tuple(values), offset, tuple(unresolved)

    def read_result(
        self,
        start: int,
        layout: Iterable[str],
        *,
        expected_rows: int | None = None,
        allow_adjacent_result: bool = False,
    ) -> DecodedResult:
        cursor = start
        rows: list[tuple[Any, ...]] = []
        raw_references: set[int] = set()
        while (
            cursor < len(self.data)
            and self.data[cursor] == SQLITE_ROW
            and (
                expected_rows is None
                or len(rows) < expected_rows
            )
        ):
            row, cursor, row_unresolved = self.row(cursor, layout)
            rows.append(row)
            raw_references.update(row_unresolved)
        if expected_rows is not None and len(rows) != expected_rows:
            raise CachedResultError(
                f"Expected {expected_rows} row(s), decoded {len(rows)}"
            )
        self._require(cursor, 1)
        if not allow_adjacent_result and self.data[cursor] != SQLITE_DONE:
            raise CachedResultError(
                f"Cached result does not end in SQLITE_DONE at 0x{cursor:X}"
            )
        resolved_forward = raw_references.intersection(self._string_cache)
        unresolved = raw_references.difference(self._string_cache)
        resolved_rows = tuple(
            tuple(
                self._string_cache.get(int(value[5:-1]), value)
                if isinstance(value, str)
                and value.startswith("<ref:")
                and value.endswith(">")
                else value
                for value in row
            )
            for row in rows
        )
        return DecodedResult(
            rows=resolved_rows,
            start=start,
            end=cursor,
            raw_references=tuple(sorted(raw_references)),
            unresolved_references=tuple(sorted(unresolved)),
            resolved_forward_references=tuple(sorted(resolved_forward)),
            strings_captured=self._capture_count,
        )

    def result_headers(self) -> tuple[ResultHeader, ...]:
        """Enumerate self-describing result boundaries in a native stream."""
        headers: list[ResultHeader] = []
        cursor = 0
        prefix = bytes((SQLITE_DONE, SQLITE_ROW))
        while True:
            header = self.data.find(prefix, cursor)
            if header < 0:
                break
            if header + 7 <= len(self.data):
                row_count = struct.unpack_from("<I", self.data, header + 2)[0]
                start = header + 6
                if (
                    (row_count > 0 and self.data[start] == SQLITE_ROW)
                    or (row_count == 0 and self.data[start] == SQLITE_DONE)
                ):
                    headers.append(
                        ResultHeader(
                            header=header,
                            start=start,
                            row_count=row_count,
                        )
                    )
            cursor = header + 1
        return tuple(headers)

    def find_result_start(self, seed: int, layout: Iterable[str]) -> int:
        layout_values = tuple(layout)
        current = seed
        while True:
            candidate = current
            lower = max(0, current - 8192)
            found: int | None = None
            while True:
                candidate = self.data.rfind(bytes([SQLITE_ROW]), lower, candidate)
                if candidate < 0:
                    break
                try:
                    _, end, _ = self.row(candidate, layout_values)
                    if end == current:
                        found = candidate
                        break
                except (CachedResultError, IndexError, struct.error):
                    pass
            if found is None:
                return current
            current = found

    def locate(
        self,
        columns: Iterable[str],
        layout: Iterable[str],
        anchor_id: int,
        anchor_values: dict[str, Any],
    ) -> int:
        column_values = tuple(columns)
        layout_values = tuple(layout)
        if len(column_values) != len(layout_values):
            raise CachedResultError("columns and layout lengths differ")
        pattern = bytes([SQLITE_ROW]) + struct.pack("<i", anchor_id)
        matches: list[int] = []
        cursor = 0
        while True:
            cursor = self.data.find(pattern, cursor)
            if cursor < 0:
                break
            try:
                values, end, _ = self.row(cursor, layout_values)
                row = dict(zip(column_values, values))
                if (
                    end < len(self.data)
                    and self.data[end] in (SQLITE_ROW, SQLITE_DONE)
                    and all(row.get(key) == value for key, value in anchor_values.items())
                ):
                    matches.append(cursor)
            except (CachedResultError, IndexError, struct.error):
                pass
            cursor += 1
        if len(matches) != 1:
            raise CachedResultError(
                f"Expected one anchor for id {anchor_id}, found {len(matches)}"
            )
        return self.find_result_start(matches[0], layout_values)
