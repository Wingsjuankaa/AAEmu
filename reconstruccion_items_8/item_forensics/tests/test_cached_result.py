from __future__ import annotations

import struct
import unittest

from ..cached_result import (
    CachedResultError,
    CachedResultReader,
    recover_calibrated_string_cache,
)


class CachedResultReaderTests(unittest.TestCase):
    def test_decodes_all_supported_primitives(self) -> None:
        payload = (
            b"\x64"
            + b"\x07"
            + struct.pack("<i", -9)
            + struct.pack("<q", 2**40)
            + struct.pack("<d", 12.5)
            + b"\x00native\x00"
            + b"\x65"
        )
        result = CachedResultReader(payload).read_result(
            0,
            ["38", "68", "40", "60", "78"],
            expected_rows=1,
        )
        self.assertEqual(result.rows, ((7, -9, 2**40, 12.5, "native"),))
        self.assertEqual(result.end, len(payload) - 1)
        self.assertEqual(result.unresolved_references, ())

    def test_null_and_utf8_strings(self) -> None:
        text = "검증".encode("utf-8")
        payload = b"\x64\x02" + b"\x64\x00" + text + b"\x00\x65"
        result = CachedResultReader(payload).read_result(
            0,
            ["78"],
            expected_rows=2,
        )
        self.assertEqual(result.rows, ((None,), ("검증",)))

    def test_captures_and_reuses_interned_string(self) -> None:
        payload = (
            b"\x64\x01"
            + struct.pack("<I", 0xFFFFFFFF)
            + b"ItemToolDesc\x00"
            + b"\x64\x01"
            + struct.pack("<I", 900)
            + b"\x65"
        )
        reader = CachedResultReader(payload)
        reader.seed_string_cache(next_reference=900)
        result = reader.read_result(0, ["78"], expected_rows=2)
        self.assertEqual(
            result.rows,
            (("ItemToolDesc",), ("ItemToolDesc",)),
        )
        self.assertEqual(reader.string_cache, {900: "ItemToolDesc"})
        self.assertEqual(result.strings_captured, 1)

    def test_records_unresolved_reference_without_guessing(self) -> None:
        payload = b"\x64\x01" + struct.pack("<I", 12345) + b"\x65"
        result = CachedResultReader(payload).read_result(0, ["78"])
        self.assertEqual(result.rows, (("<ref:12345>",),))
        self.assertEqual(result.raw_references, (12345,))
        self.assertEqual(result.unresolved_references, (12345,))

    def test_resolves_forward_reference_after_later_cached_string(self) -> None:
        payload = (
            b"\x64\x01"
            + struct.pack("<I", 900)
            + b"\x64\x01"
            + struct.pack("<I", 0xFFFFFFFF)
            + b"native\x00"
            + b"\x65"
        )
        reader = CachedResultReader(payload)
        reader.seed_string_cache(next_reference=900)
        result = reader.read_result(0, ["78"], expected_rows=2)
        self.assertEqual(result.rows, (("native",), ("native",)))
        self.assertEqual(result.raw_references, (900,))
        self.assertEqual(result.unresolved_references, ())
        self.assertEqual(result.resolved_forward_references, (900,))

    def test_enumerates_native_result_headers(self) -> None:
        payload = (
            b"\x65\x64"
            + struct.pack("<I", 1)
            + b"\x64"
            + struct.pack("<i", 42)
            + b"\x65"
        )
        reader = CachedResultReader(payload)
        headers = reader.result_headers()
        self.assertEqual(1, len(headers))
        self.assertEqual(0, headers[0].header)
        self.assertEqual(6, headers[0].start)
        self.assertEqual(1, headers[0].row_count)
        decoded = reader.read_result(
            headers[0].start,
            ["68"],
            expected_rows=headers[0].row_count,
        )
        self.assertEqual(((42,),), decoded.rows)

    def test_enumerates_empty_native_result_header(self) -> None:
        reader = CachedResultReader(b"\x65\x64\x00\x00\x00\x00\x65")
        headers = reader.result_headers()
        self.assertEqual(1, len(headers))
        self.assertEqual(0, headers[0].row_count)
        decoded = reader.read_result(
            headers[0].start,
            ["68"],
            expected_rows=0,
        )
        self.assertEqual((), decoded.rows)

    def test_allows_evidenced_adjacent_result_boundary(self) -> None:
        payload = (
            b"\x64"
            + struct.pack("<i", 42)
            + b"\x64"
            + struct.pack("<i", 99)
            + b"\x65"
        )
        reader = CachedResultReader(payload)
        decoded = reader.read_result(
            0,
            ["68"],
            expected_rows=1,
            allow_adjacent_result=True,
        )
        self.assertEqual(((42,),), decoded.rows)
        self.assertEqual(5, decoded.end)

    def test_rejects_truncated_result(self) -> None:
        with self.assertRaises(CachedResultError):
            CachedResultReader(b"\x64\x01").read_result(0, ["68"])

    def test_locates_unique_anchor_and_rejects_ambiguous_anchor(self) -> None:
        row = b"\x64" + struct.pack("<ii", 77, 88) + b"\x65"
        reader = CachedResultReader(b"junk" + row)
        start = reader.locate(["id", "value"], ["68", "68"], 77, {"value": 88})
        self.assertEqual(start, 4)
        duplicate = CachedResultReader(row + row)
        with self.assertRaises(CachedResultError):
            duplicate.locate(["id", "value"], ["68", "68"], 77, {"value": 88})

    def test_recovers_bracketed_global_string_cache_reference(self) -> None:
        marker = b"\x01\xff\xff\xff\xff"
        false_candidate = marker + b"unrelated\x00"
        lower_start = len(false_candidate) + 4
        lower = marker + b"lower\x00"
        middle = marker + b"native/path.chr\x00"
        upper_start = lower_start + len(lower) + len(middle)
        upper = marker + b"upper\x00"
        payload = false_candidate + b"junk" + lower + middle + upper
        recovered = recover_calibrated_string_cache(
            payload,
            [11],
            [
                {
                    "source": "lower",
                    "start": lower_start,
                    "end": lower_start + len(lower),
                    "first_reference": 10,
                },
                {
                    "source": "upper",
                    "start": upper_start,
                    "end": upper_start + len(upper),
                    "first_reference": 12,
                },
            ],
        )
        self.assertEqual({11: "native/path.chr"}, recovered.values)
        self.assertEqual(-9, recovered.candidate_index_delta)

    def test_rejects_unbracketed_global_string_cache_reference(self) -> None:
        marker = b"\x01\xff\xff\xff\xff"
        payload = marker + b"lower\x00" + marker + b"upper\x00"
        with self.assertRaises(CachedResultError):
            recover_calibrated_string_cache(
                payload,
                [9],
                [
                    {
                        "start": 0,
                        "end": 10,
                        "first_reference": 10,
                    },
                    {
                        "start": 11,
                        "end": len(payload),
                        "first_reference": 11,
                    },
                ],
            )


if __name__ == "__main__":
    unittest.main()
