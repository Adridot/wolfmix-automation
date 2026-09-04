#!/usr/bin/env python3
"""The W1's gobo icon library, read from the local flash image (read-only).

A table of 800 30-byte entries at the end of `wolfmixFlash.bin`:
`ptr u32 LE | 6 bytes (colour/flags) | 20-byte NUL-terminated name`. Each `ptr`
points at a 1728-byte icon = 24x24 px, RGB565 LE + 8-bit alpha. The entry's
index IS the gobo id read from `145.f2` in the .wpj and from `userNum` in the
fixture profile. This module is read-only; the guarded device upload lives in
`wolfmix.py`.

The icons are the manufacturer's work: renders stay outside the repository.
"""
import glob
import os
import struct
import sys
import zlib

TABLE_LEN = 800
ENTRY = 30
ICON = 1728          # 24 * 24 * 3
SIDE = 24
ANCHOR = b"\x00\x00\x00\x00\x00\x01Open\x00"

FLASH_GLOBS = (
    "~/Library/Application Support/com.nicolaudiegroup.wtools/"
    "wm-fw-bundle-*/wolfmixFlash.bin",
    "~/Library/Application Support/WTOOLS/wlinkData/temp/firmware/"
    "wm-fw-bundle/wolfmixFlash.bin",
)


def version_tuple(chemin):
    """`wm-fw-bundle-2.0.18` → (2, 0, 18); with no number, (-1,) — never chosen
    over a readable version. Lexical order put 2.0.9 after 2.0.18."""
    nom = os.path.basename(os.path.dirname(chemin))
    _, _, version = nom.partition("wm-fw-bundle-")
    morceaux = [m for m in version.split(".") if m.isdigit()]
    return tuple(int(m) for m in morceaux) if morceaux else (-1,)


def flash_bundles():
    """Every installed flash image, the most recent one first."""
    trouves = []
    for pattern in FLASH_GLOBS:
        trouves += glob.glob(os.path.expanduser(pattern))
    return sorted(set(trouves), key=version_tuple, reverse=True)


def find_flash(path=None, version=None):
    """The flash image to read: the one named, the one of a requested version,
    or the most recent installed."""
    if path:
        return path
    bundles = flash_bundles()
    if version:
        vise = tuple(int(m) for m in version.split(".") if m.isdigit())
        bundles = [b for b in bundles if version_tuple(b) == vise]
    return bundles[0] if bundles else None


class Library:
    def __init__(self, path):
        with open(path, "rb") as flux:
            self.data = flux.read()
        anchor = self.data.find(ANCHOR)
        if anchor < 0:
            raise ValueError("no gobo table found in this flash image")
        self.table = anchor - 4
        while self._ptr(self.table - ENTRY) >> 24 == 0x10:
            self.table -= ENTRY
        ptrs = [self._ptr(self.table + k * ENTRY) for k in range(TABLE_LEN)]
        # The image area ends exactly where the table begins: that is what
        # fixes the flash base address (0x10100000 in 2.0.18).
        self.base = max(ptrs) + ICON - self.table
        self.ptrs = ptrs

    def _ptr(self, off):
        return struct.unpack_from("<I", self.data, off)[0] if off >= 0 else 0

    def check_id(self, gobo_id):
        """Python would index -1 onto the last entry and raise past 800: both
        are refusals here, with the range spelled out."""
        if not isinstance(gobo_id, int) or isinstance(gobo_id, bool):
            raise ValueError(f"integer gobo id expected, got {gobo_id!r}")
        if not 0 <= gobo_id < TABLE_LEN:
            raise ValueError(
                f"gobo id {gobo_id} is out of table: the range is "
                f"0-{TABLE_LEN - 1}")
        return gobo_id

    def name(self, gobo_id):
        self.check_id(gobo_id)
        off = self.table + gobo_id * ENTRY + 10
        return self.data[off:off + 20].split(b"\x00")[0].decode("latin1")

    def icon(self, gobo_id):
        """Renders the icon as 24x24 RGB, flattened onto black."""
        self.check_id(gobo_id)
        raw = self.data[self.ptrs[gobo_id] - self.base:][:ICON]
        out = bytearray()
        for i in range(0, ICON, 3):
            v = raw[i] | (raw[i + 1] << 8)
            a = raw[i + 2]
            out += bytes((((v >> 11) & 31) * 255 // 31 * a // 255,
                          ((v >> 5) & 63) * 255 // 63 * a // 255,
                          (v & 31) * 255 // 31 * a // 255))
        return bytes(out)


def write_png(path, width, height, rgb):
    rows = b"".join(b"\x00" + rgb[y * width * 3:(y + 1) * width * 3]
                    for y in range(height))

    def chunk(tag, payload):
        body = tag + payload
        return (struct.pack(">I", len(payload)) + body
                + struct.pack(">I", zlib.crc32(body)))

    with open(path, "xb") as out:            # outputs are never overwritten
        out.write(b"\x89PNG\r\n\x1a\n"
                  + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height,
                                               8, 2, 0, 0, 0))
                  + chunk(b"IDAT", zlib.compress(rows))
                  + chunk(b"IEND", b""))


def sheet(lib, ids, path, scale=4, cols=20):
    rows = (len(ids) + cols - 1) // cols
    cell = SIDE * scale
    width, height = cols * cell, rows * cell
    buf = bytearray(width * height * 3)
    for n, gobo_id in enumerate(ids):
        icon = lib.icon(gobo_id)
        ox, oy = (n % cols) * cell, (n // cols) * cell
        for y in range(SIDE):
            for x in range(SIDE):
                px = icon[(y * SIDE + x) * 3:(y * SIDE + x) * 3 + 3]
                for sy in range(scale):
                    row = (oy + y * scale + sy) * width
                    for sx in range(scale):
                        off = (row + ox + x * scale + sx) * 3
                        buf[off:off + 3] = px
    write_png(path, width, height, bytes(buf))


def palette(lib, wpj):
    """A project's gobo palettes (record 145), id → icon name."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from wpj_wire import load, walk
    _, records = load(wpj)
    for _, record_type, _, payload in records:
        if record_type != 145:
            continue
        group, pads = 0, []
        for field in walk(payload):
            if field[0] == 2 and field[1] == "v":
                group = field[2]
            if field[0] == 5 and field[1] == "len":
                gobo_id = name = None
                for sub in field[3] or []:
                    if sub[0] == 2 and sub[1] == "v":
                        gobo_id = sub[2]
                    if sub[0] == 3:
                        name = sub[2].decode("utf-8", "replace")
                pads.append((gobo_id, name))
        if any(gobo_id is not None for gobo_id, _ in pads):
            yield group, pads


def self_test(path):
    lib = Library(path)
    assert lib.base == 0x10100000, hex(lib.base)
    for gobo_id, expected in ((0, "Open"), (342, "Gobo01"), (352, "Gobo11"),
                              (420, "Open2"), (425, "Open7")):
        assert lib.name(gobo_id) == expected, (gobo_id, lib.name(gobo_id))
    assert len(lib.icon(425)) == SIDE * SIDE * 3
    assert len(set(lib.ptrs)) == 705, len(set(lib.ptrs))

    # Sorted by version, not lexically: 2.0.9 comes before 2.0.18.
    assert version_tuple("/x/wm-fw-bundle-2.0.18/wolfmixFlash.bin") == (2, 0, 18)
    assert (version_tuple("/x/wm-fw-bundle-2.0.9/f.bin")
            < version_tuple("/x/wm-fw-bundle-2.0.18/f.bin"))
    assert version_tuple("/x/wm-fw-bundle/f.bin") == (-1,)

    # An out-of-table id is refused at both ends, with no silent fallback.
    for refuse in (-1, TABLE_LEN, TABLE_LEN + 10, True, "342"):
        try:
            lib.check_id(refuse)
            raise AssertionError(f"id accepted: {refuse!r}")
        except ValueError:
            pass
    assert lib.check_id(0) == 0 and lib.check_id(TABLE_LEN - 1) == TABLE_LEN - 1

    print(f"ok — {TABLE_LEN} entries, {len(set(lib.ptrs))} distinct icons")


def annonce_bundle(path):
    """Say which one was picked: several bundles can coexist."""
    autres = [b for b in flash_bundles() if b != path]
    if autres and not os.environ.get("WOLFMIX_FLASH"):
        print(f"bundle chosen: {os.path.basename(os.path.dirname(path))} "
              f"({len(autres)} other(s) installed)", file=sys.stderr)
    return path


def _parseur():
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--flash", help="flash image to read; by default the "
                                         "most recent installed, or "
                                         "$WOLFMIX_FLASH")
    commandes = parseur.add_subparsers(dest="commande")
    commandes.add_parser("self-test", help="check the table on the local image")
    commandes.add_parser("list", help="the 800 entries, id and stock name")
    planche = commandes.add_parser("sheet", help="PNG contact sheet of the icons")
    planche.add_argument("sortie", help="new PNG file; an existing one is refused")
    planche.add_argument("ids", nargs="?",
                         help="ids separated by commas; by default the whole "
                              "table, cell (row, column) = row * 20 + column")
    pal = commandes.add_parser("palette", help="the ids a project displays")
    pal.add_argument("projet", help="the .wpj to read")
    return parseur


def main(argv=None):
    parseur = _parseur()
    args = parseur.parse_args(argv)
    commande = args.commande or "self-test"
    path = find_flash(args.flash or os.environ.get("WOLFMIX_FLASH"))
    if not path:
        print("no local flash image (WTOOLS never downloaded the firmware) — "
              "nothing to do", file=sys.stderr)
        return 0
    annonce_bundle(path)
    if commande == "self-test":
        self_test(path)
        return 0
    lib = Library(path)
    if commande == "list":
        for gobo_id in range(TABLE_LEN):
            print(f"{gobo_id}\t{lib.name(gobo_id)}")
    elif commande == "sheet":
        ids = ([int(x) for x in args.ids.split(",")] if args.ids
               else list(range(TABLE_LEN)))
        try:
            sheet(lib, ids, args.sortie)
        except FileExistsError:
            print(f"refused: {args.sortie} already exists", file=sys.stderr)
            return 2
        except ValueError as erreur:
            print(f"refused: {erreur}", file=sys.stderr)
            return 2
        print(f"{len(ids)} icons → {args.sortie}")
    elif commande == "palette":
        for group, pads in palette(lib, args.projet):
            print(f"group {group}")
            for slot, (gobo_id, name) in enumerate(pads, 1):
                if gobo_id is None:
                    continue
                label = f"  name \"{name}\"" if name else ""
                print(f"  pad {slot:2d}  id={gobo_id:3d}  "
                      f"{lib.name(gobo_id)}{label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
