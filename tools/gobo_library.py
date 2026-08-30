#!/usr/bin/env python3
"""Bibliothèque d'icônes gobo du W1, lue dans l'image flash locale (lecture seule).

Table de 800 entrées de 30 octets à la fin de `wolfmixFlash.bin` :
`ptr u32 LE | 6 octets (couleur/flags) | nom 20o NUL-terminé`. Chaque `ptr`
vise une icône de 1728 octets = 24x24 px, RGB565 LE + alpha 8 bits.
L'index de l'entrée EST l'id gobo qu'on lit dans `145.f2` du .wpj et dans
`userNum` du profil de luminaire. Rien n'est écrit, ici ni ailleurs.

Les icônes sont l'oeuvre du fabricant : les rendus restent hors du dépôt.
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


def find_flash(path=None):
    if path:
        return path
    for pattern in FLASH_GLOBS:
        hits = sorted(glob.glob(os.path.expanduser(pattern)))
        if hits:
            return hits[-1]
    return None


class Library:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        anchor = self.data.find(ANCHOR)
        if anchor < 0:
            raise ValueError("table gobo introuvable dans cette image flash")
        self.table = anchor - 4
        while self._ptr(self.table - ENTRY) >> 24 == 0x10:
            self.table -= ENTRY
        ptrs = [self._ptr(self.table + k * ENTRY) for k in range(TABLE_LEN)]
        # La zone d'images se termine exactement là où la table commence :
        # c'est ce qui fixe l'adresse de base du flash (0x10100000 en 2.0.18).
        self.base = max(ptrs) + ICON - self.table
        self.ptrs = ptrs

    def _ptr(self, off):
        return struct.unpack_from("<I", self.data, off)[0] if off >= 0 else 0

    def name(self, gobo_id):
        off = self.table + gobo_id * ENTRY + 10
        return self.data[off:off + 20].split(b"\x00")[0].decode("latin1")

    def icon(self, gobo_id):
        """Rend l'icône en RGB 24x24 aplati sur fond noir."""
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

    with open(path, "wb") as out:
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
    """Palettes gobo (record 145) d'un projet, id → nom d'icône."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from tlv import load, walk
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
    print(f"ok — {TABLE_LEN} entrées, {len(set(lib.ptrs))} icônes distinctes")


def main(argv):
    command = argv[1] if len(argv) > 1 else "self-test"
    path = find_flash(os.environ.get("WOLFMIX_FLASH"))
    if not path:
        print("aucune image flash locale (WTOOLS n'a jamais téléchargé le "
              "firmware) — rien à faire", file=sys.stderr)
        return 0
    if command == "self-test":
        self_test(path)
        return 0
    lib = Library(path)
    if command == "list":
        for gobo_id in range(TABLE_LEN):
            print(f"{gobo_id}\t{lib.name(gobo_id)}")
    elif command == "sheet":
        out = argv[2]
        # Par défaut la planche entière, dans l'ordre des id : la case
        # (ligne, colonne) vaut donc l'id `ligne * 20 + colonne`.
        ids = ([int(x) for x in argv[3].split(",")] if len(argv) > 3
               else list(range(TABLE_LEN)))
        sheet(lib, ids, out)
        print(f"{len(ids)} icônes → {out}")
    elif command == "palette":
        for group, pads in palette(lib, argv[2]):
            print(f"groupe {group}")
            for slot, (gobo_id, name) in enumerate(pads, 1):
                if gobo_id is None:
                    continue
                label = f"  nom « {name} »" if name else ""
                print(f"  pad {slot:2d}  id={gobo_id:3d}  "
                      f"{lib.name(gobo_id)}{label}")
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
