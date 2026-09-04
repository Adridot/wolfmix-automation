"""The flash boundary: the right bundle, an id inside the table, a real image,
and a patch that cannot land on top of an existing file.

A resource flash is not firmware (`AGENTS.md`, `LEGAL.md`): it is read here,
patched into a **copy**, and may be uploaded only after the guards below make
that copy accountable. The image built by `tests/fixtures.py` stands in for
the manufacturer's, which never enters this repository.
"""
import json
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import gobo_library
import gobo_run
import gobo_write

from . import fixtures


class Flash(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, "wolfmixFlash.bin")
        with open(self.path, "wb") as stream:
            stream.write(fixtures.flash_bytes())
        self.lib = gobo_library.Library(self.path)


class IconIdRange(Flash):
    """Python would index -1 onto the last entry and raise past 800. Both are
    refusals here, with the range spelled out."""

    def test_an_id_outside_the_table_is_refused(self) -> None:
        for bad in (-1, gobo_library.TABLE_LEN, 10 ** 6):
            with self.assertRaises(ValueError) as caught:
                self.lib.check_id(bad)
            self.assertIn("out of table", str(caught.exception))

    def test_a_non_integer_id_is_refused(self) -> None:
        for bad in ("3", 3.0, True, None):
            with self.assertRaises(ValueError):
                self.lib.check_id(bad)

    def test_patching_an_out_of_range_id_writes_nothing(self) -> None:
        for bad in (-1, gobo_library.TABLE_LEN):
            with self.assertRaises(ValueError):
                gobo_write.patch(self.lib, {bad: fixtures.solid_icon()})

    def test_a_shared_pointer_is_refused_by_name(self) -> None:
        """"Open" serves 796 entries in the fixture and 96 on the device:
        rewriting it would repaint them all."""
        with self.assertRaises(ValueError) as caught:
            gobo_write.patch(self.lib, {700: fixtures.solid_icon()})
        self.assertIn("shares its pointer", str(caught.exception))

    def test_a_patch_stays_inside_its_own_window(self) -> None:
        after = gobo_write.patch(self.lib, {0: fixtures.solid_icon()})
        self.assertEqual(len(after), len(self.lib.data))
        changed = gobo_write.verify(self.lib.data, after, self.lib, [0])
        self.assertGreater(changed, 0, "the patch wrote nothing")

    def test_a_byte_outside_the_window_is_a_refusal(self) -> None:
        after = bytearray(gobo_write.patch(self.lib, {0: fixtures.solid_icon()}))
        start = self.lib.ptrs[0] - self.lib.base
        after[start + gobo_library.ICON] ^= 0xFF
        with self.assertRaises(ValueError) as caught:
            gobo_write.verify(self.lib.data, bytes(after), self.lib, [0])
        self.assertIn("outside", str(caught.exception))


class InvalidImage(unittest.TestCase):
    """An almost-valid PNG is refused class by class, not read half-way."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.good = os.path.join(self.directory.name, "good.png")
        side = gobo_library.SIDE
        gobo_library.write_png(self.good, side, side, bytes(side * side * 3))
        self.bytes = Path(self.good).read_bytes()

    def _write(self, name, body):
        path = os.path.join(self.directory.name, name)
        Path(path).write_bytes(body)
        return path

    def test_a_good_png_reads_back(self) -> None:
        width, height, pixels = gobo_write.read_png(self.good)
        self.assertEqual((width, height), (gobo_library.SIDE, gobo_library.SIDE))
        self.assertEqual(len(pixels), gobo_library.SIDE ** 2)

    def test_not_a_png_at_all(self) -> None:
        with self.assertRaises(ValueError) as caught:
            gobo_write.read_png(self._write("text.png", b"not a png at all"))
        self.assertIn("not a PNG", str(caught.exception))

    def test_a_broken_crc(self) -> None:
        # The IHDR checksum, at 8 (signature) + 8 (size and tag) + 13 (body).
        body = bytearray(self.bytes)
        body[8 + 8 + 13] ^= 0xFF
        with self.assertRaises(ValueError) as caught:
            gobo_write.read_png(self._write("crc.png", bytes(body)))
        self.assertIn("CRC", str(caught.exception))

    def test_a_missing_iend(self) -> None:
        with self.assertRaises(ValueError) as caught:
            gobo_write.read_png(self._write("iend.png", self.bytes[:-12]))
        self.assertIn("IEND", str(caught.exception))

    def test_a_truncated_file(self) -> None:
        with self.assertRaises(ValueError):
            gobo_write.read_png(self._write("cut.png", self.bytes[:-20]))

    def test_a_height_the_data_does_not_cover(self) -> None:
        body = bytearray(self.bytes)
        header = body.index(b"IHDR")
        struct.pack_into(">I", body, header + 8, gobo_library.SIDE * 2)
        struct.pack_into(">I", body, header + 12 + 13,
                         zlib.crc32(bytes(body[header:header + 4 + 13])))
        with self.assertRaises(ValueError):
            gobo_write.read_png(self._write("short.png", bytes(body)))

    def test_an_image_smaller_than_an_icon(self) -> None:
        small = os.path.join(self.directory.name, "small.png")
        gobo_library.write_png(small, 8, 8, bytes(8 * 8 * 3))
        with self.assertRaises(ValueError) as caught:
            gobo_write.load_image(small)
        self.assertIn("24x24", str(caught.exception))

    def test_a_colour_that_is_not_rrggbb(self) -> None:
        for bad in ("ff00ff", "#f0f", "#ff00ff00"):
            with self.assertRaises(ValueError):
                gobo_write.solid(bad)


class RefusedOverwrite(Flash):
    """The patched file and its manifest live or die together, and neither
    lands on top of something that is already there."""

    def test_the_pair_is_written_then_refused_a_second_time(self) -> None:
        after = gobo_write.patch(self.lib, {0: fixtures.solid_icon()})
        changed = gobo_write.verify(self.lib.data, after, self.lib, [0])
        output = os.path.join(self.directory.name, "flash-custom.bin")
        manifest = gobo_write.manifeste(self.path, self.lib, output, after,
                                        {0: None}, changed)
        gobo_write.ecrire(output, after, manifest)
        recorded = json.loads(Path(output + ".json").read_text(encoding="utf-8"))
        self.assertEqual(recorded["result"]["sha256"],
                         gobo_write.sha256(Path(output).read_bytes()))
        self.assertEqual(recorded["source"]["sha256"],
                         gobo_write.sha256(self.lib.data))
        before = Path(output).read_bytes()
        with self.assertRaises(FileExistsError):
            gobo_write.ecrire(output, after, manifest)
        # The refusal must leave both halves standing: `ecrire` removes the
        # patch when the manifest fails, so a write that got as far as the
        # file would take the earlier one with it.
        self.assertTrue(Path(output).exists(), "the earlier patch was removed")
        self.assertEqual(Path(output).read_bytes(), before)


class UploadPlan(unittest.TestCase):
    """Only a manifest-bound gobo diff with a verified backup can be sent."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        self.backup = self.work / gobo_run.BACKUP
        self.backup.mkdir()
        self.source = self.backup / "wolfmixFlash.bin"
        self.source.write_bytes(fixtures.flash_bytes())
        source_hash = gobo_run.sha256(str(self.source))
        (self.backup / gobo_run.MANIFEST).write_text(json.dumps({
            "files": [{"file": self.source.name, "sha256": source_hash}],
        }), encoding="utf-8")
        lib = gobo_library.Library(str(self.source))
        after = gobo_write.patch(lib, {0: fixtures.solid_icon()})
        changed = gobo_write.verify(lib.data, after, lib, [0])
        self.patched = self.work / gobo_run.PATCHED
        manifest = gobo_write.manifeste(
            str(self.source), lib, str(self.patched), after, {0: None}, changed
        )
        gobo_write.ecrire(str(self.patched), after, manifest)
        (self.work / gobo_run.SHEET).write_bytes(b"reviewed sheet")

    def test_verified_gobo_patch_is_returned(self) -> None:
        data, summary = gobo_run.upload_plan(str(self.work))
        self.assertEqual(data, self.patched.read_bytes())
        self.assertEqual(summary["ids"], [0])
        self.assertGreater(summary["bytesChanged"], 0)

    def test_change_outside_the_icon_window_is_refused(self) -> None:
        data = bytearray(self.patched.read_bytes())
        data[-1] ^= 0xFF
        self.patched.write_bytes(data)
        manifest_path = Path(str(self.patched) + ".json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["result"]["sha256"] = gobo_write.sha256(bytes(data))
        manifest["bytesChanged"] += 1
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "outside"):
            gobo_run.upload_plan(str(self.work))

    def test_backup_without_vendor_manifest_is_refused(self) -> None:
        (self.backup / gobo_run.MANIFEST).unlink()
        with self.assertRaisesRegex(ValueError, "not verified"):
            gobo_run.upload_plan(str(self.work))


def _one_byte_apart(data):
    """The same length, different content — what the length gate cannot see."""
    changed = bytearray(data)
    changed[0] ^= 0xFF
    return bytes(changed)


class WrongBundle(unittest.TestCase):
    """Which flash the patch came from is a hash, not a length. Selecting one
    is by parsed version, because lexical order puts 2.0.9 after 2.0.18."""

    def test_versions_are_compared_as_numbers(self) -> None:
        newer = "wm-fw-bundle-2.0.18/wolfmixFlash.bin"
        older = "wm-fw-bundle-2.0.9/wolfmixFlash.bin"
        self.assertGreater(gobo_library.version_tuple(newer),
                           gobo_library.version_tuple(older))
        self.assertLess(gobo_library.version_tuple("wm-fw-bundle/x.bin"),
                        gobo_library.version_tuple(older))

    def test_an_absent_version_selects_nothing_rather_than_the_newest(self) -> None:
        self.assertIsNone(gobo_library.find_flash(version="99.99.99"))

    def test_a_patch_from_another_bundle_is_a_red_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            flash = work / "wolfmixFlash.bin"
            flash.write_bytes(fixtures.flash_bytes())
            patched = work / gobo_run.PATCHED
            patched.write_bytes(_one_byte_apart(flash.read_bytes()))
            (work / (gobo_run.PATCHED + ".json")).write_text(json.dumps({
                "source": {"sha256": "0" * 64, "bundle": "wm-fw-bundle-2.0.9"},
                "result": {"sha256": gobo_write.sha256(patched.read_bytes())},
                "ids": [0],
            }), encoding="utf-8")
            green, detail = gobo_run.gate_patched(str(patched), str(flash))
            self.assertFalse(green)
            self.assertIn("no longer the one the patch came from", detail)

    def test_the_same_length_with_other_content_is_a_red_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            flash = work / "wolfmixFlash.bin"
            flash.write_bytes(fixtures.flash_bytes())
            patched = work / gobo_run.PATCHED
            patched.write_bytes(_one_byte_apart(flash.read_bytes()))
            (work / (gobo_run.PATCHED + ".json")).write_text(json.dumps({
                "source": {"sha256": gobo_write.sha256(flash.read_bytes()),
                           "bundle": "wm-fw-bundle-2.0.18"},
                "result": {"sha256": "0" * 64},
                "ids": [0],
            }), encoding="utf-8")
            green, detail = gobo_run.gate_patched(str(patched), str(flash))
            self.assertFalse(green)
            self.assertIn("does not match its manifest", detail)

    def test_a_missing_manifest_is_a_red_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            flash = work / "wolfmixFlash.bin"
            flash.write_bytes(fixtures.flash_bytes())
            patched = work / gobo_run.PATCHED
            patched.write_bytes(fixtures.flash_bytes())
            green, detail = gobo_run.gate_patched(str(patched), str(flash))
            self.assertFalse(green)
            self.assertIn("missing", detail)


if __name__ == "__main__":
    unittest.main()
