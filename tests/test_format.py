"""The file boundary: truncation, varints, and the refusal to overwrite."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

import wpj_codec
import wpj_wire
import wpjlib

from . import fixtures


class TruncatedFile(unittest.TestCase):
    """Every cut must be a named format error, never a stray struct.error."""

    def test_round_trip_is_byte_identical(self):
        data = fixtures.project_bytes()
        project = wpjlib.Wpj.from_bytes(data)
        body = project.body()
        self.assertEqual(hashlib.sha1(body).digest() + body, data)

    def test_too_short_for_a_header(self):
        for size in (0, 10, wpjlib.BODY_OFF - 20):
            body = b"x" * size
            with self.assertRaises(ValueError) as caught:
                wpjlib.Wpj.from_bytes(hashlib.sha1(body).digest() + body, "<cut>")
            self.assertRegex(str(caught.exception), "short|root container")

    def test_record_running_past_the_body(self):
        data = bytearray(fixtures.project_bytes())
        # Claim a record 4096 bytes long inside a container that has 10.
        struct.pack_into("<I", data, wpjlib.BODY_OFF + 6, 4096)
        body = bytes(data[20:])
        with self.assertRaises(ValueError) as caught:
            wpjlib.Wpj.from_bytes(hashlib.sha1(body).digest() + body, "<cut>")
        self.assertIn("truncated", str(caught.exception))

    def test_sha1_header_must_match(self):
        data = bytearray(fixtures.project_bytes())
        data[-1] ^= 0xFF
        with self.assertRaises(ValueError) as caught:
            wpjlib.Wpj.from_bytes(bytes(data), "<tampered>")
        self.assertIn("SHA-1", str(caught.exception))

    def test_wire_reader_refuses_the_same_cuts(self):
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


class Varints(unittest.TestCase):
    """Reading refuses what cannot terminate; writing refuses what is not a
    natural number — `-1` would shift forever, `True` would encode as 1."""

    def test_truncated_varint(self):
        with self.assertRaises(wpj_wire.WireError):
            wpj_wire.read_varint(b"\x80\x80", 0)

    def test_endless_varint(self):
        with self.assertRaises(wpj_wire.WireError) as caught:
            wpj_wire.read_varint(b"\x80" * 20, 0)
        self.assertIn("too long", str(caught.exception))

    def test_field_number_zero(self):
        with self.assertRaises(wpj_wire.WireError):
            list(wpj_wire.fields(b"\x00\x01"))

    def test_unknown_wire_type(self):
        with self.assertRaises(wpj_wire.WireError):
            list(wpj_wire.fields(b"\x07\xff"))

    def test_length_running_past_the_buffer(self):
        with self.assertRaises(wpj_wire.WireError):
            list(wpj_wire.fields(b"\x12\x05abc"))

    def test_negative_varint_is_not_written(self):
        with self.assertRaises(ValueError) as caught:
            wpj_codec._wvarint(-1)
        self.assertIn("negative", str(caught.exception))

    def test_bool_and_str_are_not_varints(self):
        for value in (True, False, "3", 3.0, None):
            with self.assertRaises(ValueError):
                wpj_codec._wvarint(value)

    def test_what_is_written_reads_back(self):
        for value in (0, 1, 127, 128, 300, 2 ** 32, 2 ** 63 - 1):
            encoded = wpj_codec._wvarint(value)
            self.assertEqual(wpj_wire.read_varint(encoded, 0),
                             (value, len(encoded)))


class RefusedOverwrite(unittest.TestCase):
    """An overwritten project is an unrecoverable show (AGENTS.md)."""

    def test_save_refuses_an_existing_path(self):
        project = wpjlib.Wpj.from_bytes(fixtures.project_bytes())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "out.wpj"
            project.save(target)
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                project.save(target)
            self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
