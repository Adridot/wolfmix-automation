"""The file boundary: truncation, varints, and the refusal to overwrite."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

import wpj_codec
import wpj_coverage
import wpj_wire
import wpjlib
import wolfmix_protocol

from . import fixtures


class TruncatedFile(unittest.TestCase):
    """Every cut must be a named format error, never a stray struct.error."""

    def test_round_trip_is_byte_identical(self) -> None:
        data = fixtures.project_bytes()
        project = wpjlib.Wpj.from_bytes(data)
        body = project.body()
        self.assertEqual(hashlib.sha1(body).digest() + body, data)

    def test_too_short_for_a_header(self) -> None:
        for size in (0, 10, wpjlib.BODY_OFF - 20):
            body = b"x" * size
            with self.assertRaises(ValueError) as caught:
                wpjlib.Wpj.from_bytes(hashlib.sha1(body).digest() + body, "<cut>")
            self.assertRegex(str(caught.exception), "short|root container")

    def test_record_running_past_the_body(self) -> None:
        data = bytearray(fixtures.project_bytes())
        # Claim a record 4096 bytes long inside a container that has 10.
        struct.pack_into("<I", data, wpjlib.BODY_OFF + 6, 4096)
        body = bytes(data[20:])
        with self.assertRaises(ValueError) as caught:
            wpjlib.Wpj.from_bytes(hashlib.sha1(body).digest() + body, "<cut>")
        self.assertIn("truncated", str(caught.exception))

    def test_sha1_header_must_match(self) -> None:
        data = bytearray(fixtures.project_bytes())
        data[-1] ^= 0xFF
        with self.assertRaises(ValueError) as caught:
            wpjlib.Wpj.from_bytes(bytes(data), "<tampered>")
        self.assertIn("SHA-1", str(caught.exception))

    def test_wire_reader_refuses_the_same_cuts(self) -> None:
        with self.assertRaises(wpj_wire.WireError):
            wpj_wire.parse_container(b"\x00" * 8)
        good = fixtures.project_bytes()
        self.assertEqual(
            [(index, kind) for index, kind, _, _ in wpj_wire.parse_container(good)],
            [(0, 101)])
        # A root container of another type is not read as if it were one.
        data = bytearray(good)
        struct.pack_into("<H", data, wpjlib.BODY_OFF + 4, 99)
        with self.assertRaises(wpj_wire.WireError):
            wpj_wire.parse_container(bytes(data))

    def test_project_reader_preserves_its_stricter_boundary_and_diagnostics(self) -> None:
        good = fixtures.project_bytes()
        body = good[20:] + b"extra"
        trailing = hashlib.sha1(body).digest() + body
        self.assertEqual(wpj_wire.parse_container(trailing),
                         wpj_wire.parse_container(good))
        with self.assertRaisesRegex(ValueError, "not a root container"):
            wpjlib.Wpj.from_bytes(trailing)
        for inner, message in ((b"xx", "record header"),
                               (struct.pack("<IH", 8, 101) + b"x", "record")):
            body = good[20:64] + struct.pack("<IH", len(inner), 100) + inner
            data = hashlib.sha1(body).digest() + body
            with self.assertRaises(ValueError) as caught:
                wpjlib.Wpj.from_bytes(data, "<cut>")
            self.assertIs(type(caught.exception), ValueError)
            self.assertEqual(str(caught.exception), f"<cut>: truncated {message} at 70")


class Varints(unittest.TestCase):
    """Reading refuses what cannot terminate; writing refuses what is not a
    natural number — `-1` would shift forever, `True` would encode as 1."""

    def test_truncated_varint(self) -> None:
        with self.assertRaises(wpj_wire.WireError):
            wpj_wire.read_varint(b"\x80\x80", 0)

    def test_endless_varint(self) -> None:
        with self.assertRaises(wpj_wire.WireError) as caught:
            wpj_wire.read_varint(b"\x80" * 20, 0)
        self.assertIn("too long", str(caught.exception))

    def test_field_number_zero(self) -> None:
        with self.assertRaises(wpj_wire.WireError):
            list(wpj_wire.fields(b"\x00\x01"))

    def test_unknown_wire_type(self) -> None:
        with self.assertRaises(wpj_wire.WireError):
            list(wpj_wire.fields(b"\x07\xff"))

    def test_length_running_past_the_buffer(self) -> None:
        with self.assertRaises(wpj_wire.WireError):
            list(wpj_wire.fields(b"\x12\x05abc"))

    def test_negative_varint_is_not_written(self) -> None:
        with self.assertRaises(ValueError) as caught:
            wpj_codec._wvarint(-1)
        self.assertIn("negative", str(caught.exception))

    def test_bool_and_str_are_not_varints(self) -> None:
        for value in (True, False, "3", 3.0, None):
            with self.assertRaises(ValueError):
                wpj_codec._wvarint(value)

    def test_what_is_written_reads_back(self) -> None:
        for value in (0, 1, 127, 128, 300, 2 ** 32, 2 ** 63 - 1):
            encoded = wpj_codec._wvarint(value)
            self.assertEqual(wpj_wire.read_varint(encoded, 0),
                             (value, len(encoded)))

    def test_protocol_adapter_keeps_its_input_contract(self) -> None:
        for value, expected in ((False, b"\x00"), (True, b"\x01"),
                                (127, b"\x7f"), (128, b"\x80\x01"),
                                (300, b"\xac\x02")):
            self.assertEqual(wolfmix_protocol.encode_varint(value), expected)
        for value, error in ((-1, ValueError), ("3", TypeError),
                             (3.0, TypeError), (None, TypeError)):
            with self.assertRaises(error):
                wolfmix_protocol.encode_varint(value)

    def test_schema_lookup_preserves_neutral_fields_and_wire_order(self) -> None:
        schema = {19: ("id", "v"), 25: ("name", "str")}
        self.assertEqual(wpj_codec.field_number(schema, "id"), 19)
        self.assertEqual(wpj_codec.field_number(schema, "f7"), 7)
        with self.assertRaises(KeyError):
            wpj_codec.field_number(schema, "missing")
        self.assertEqual(sorted(["name", "f7", "id"],
                                key=lambda key: wpj_codec.field_number(schema, key)),
                         ["f7", "id", "name"])


class RefusedOverwrite(unittest.TestCase):
    """An overwritten project is an unrecoverable show (AGENTS.md)."""

    def test_save_refuses_an_existing_path(self) -> None:
        project = wpjlib.Wpj.from_bytes(fixtures.project_bytes())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.wpj"
            project.save(target)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                project.save(target)
            self.assertEqual(target.read_bytes(), before)


class InertAndSplit(unittest.TestCase):
    """The two claims `wpj_coverage` makes about bytes no name explains.

    Corpus-free on purpose: `demo()` proves them on the corpus and abstains
    without one, and an abstention is exactly where a rotted guard would go
    unnoticed."""

    def _project(self, typ, payload):
        return fixtures.project_bytes(records=((typ, payload),),
                                      prefix=fixtures.prefix_bytes())

    def _record_116(self, f1):
        """Record 116 with one profile whose f1 carries `f1`. (Record 110's
        `f1` played this part until COV-67 read it — `pair_member`.)"""
        item = bytes((8, f1))                        # field 1, varint
        return bytes((8, 1)) + bytes((0x2a, len(item))) + item

    def test_a_declared_inert_field_is_counted_inert(self) -> None:
        acc = wpj_coverage.coverage(self._project(116, self._record_116(1)))
        self.assertEqual(acc[(wpj_coverage.INERT, "116.profiles.f1")], 2)
        self.assertEqual(wpj_coverage.totals(acc)[wpj_coverage.PARTIAL], 0)

    def test_a_second_value_stops_the_run(self) -> None:
        with self.assertRaises(wpj_coverage.InertBroken):
            wpj_coverage.coverage(self._project(116, self._record_116(2)))

    def test_inert_broken_is_not_a_valueerror(self) -> None:
        """The corpus walk catches ValueError to skip variants B and C. If this
        were one, a field that stopped being inert would be skipped in silence
        — the exact failure the bucket exists to prevent."""
        self.assertNotIsInstance(wpj_coverage.InertBroken(""), ValueError)

    def test_a_prefix_constant_that_moves_stops_the_run(self) -> None:
        broken = bytearray(fixtures.prefix_bytes())
        broken[16] ^= 1
        with self.assertRaises(wpj_coverage.InertBroken):
            wpj_coverage.coverage(fixtures.project_bytes(prefix=bytes(broken)))

    def test_a_split_round_trips_and_is_attributed_in_pieces(self) -> None:
        blob = bytes.fromhex("0e000000000038")
        item = bytes((0x22, 7)) + blob               # field 4, 7 bytes
        payload = bytes((8, 1)) + bytes((0x2a, len(item))) + item
        decoded = wpj_codec.decode(125, payload)
        self.assertEqual(decoded["groups"][0]["mask"],
                         {"profile_mask": 14, "f4_tail": 0x38})
        self.assertEqual(wpj_codec.encode(125, decoded), payload)
        acc = wpj_coverage.coverage(self._project(125, payload))
        self.assertEqual(acc[(wpj_coverage.READ,
                              "125.groups.mask.profile_mask")], 6)
        self.assertEqual(acc[(wpj_coverage.PARTIAL,
                              "125.groups.mask.f4_tail")], 1)

    def test_a_split_tail_that_grew_past_one_byte(self) -> None:
        """125.f4's tail is a varint: one byte under 128, two above (COV-51)."""
        blob = bytes.fromhex("0e000000000038")
        wide = bytes.fromhex("0e00000000000000") [:6] + bytes.fromhex("b801")
        for payload_blob, expected in ((blob, 0x38), (wide, 184)):
            item = bytes((0x22, len(payload_blob))) + payload_blob
            payload = bytes((8, 1)) + bytes((0x2a, len(item))) + item
            decoded = wpj_codec.decode(125, payload)
            self.assertEqual(decoded["groups"][0]["mask"],
                             {"profile_mask": 14, "f4_tail": expected})
            self.assertEqual(wpj_codec.encode(125, decoded), payload)

    def test_a_split_of_the_wrong_length_stays_opaque(self) -> None:
        item = bytes((0x22, 3)) + b"\x01\x02\x03"
        payload = bytes((8, 1)) + bytes((0x2a, len(item))) + item
        decoded = wpj_codec.decode(125, payload)
        self.assertEqual(decoded["groups"][0]["mask"], {"hex": "010203"})
        self.assertEqual(wpj_codec.encode(125, decoded), payload)
        acc = wpj_coverage.coverage(self._project(125, payload))
        self.assertEqual(acc[(wpj_coverage.PARTIAL,
                              "125.groups.mask.<unsplit>")], 3)


if __name__ == "__main__":
    unittest.main()
