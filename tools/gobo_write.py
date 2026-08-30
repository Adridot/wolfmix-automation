#!/usr/bin/env python3
"""Écrit des icônes de gobo dans une copie de l'image flash du W1.

Inverse exact de `gobo_library.Library.icon()` : une icône est un bloc de
1728 octets, 24x24 pixels, 3 octets par pixel entrelacés — RGB565
little-endian puis alpha 8 bits. La taille est fixe et les pointeurs de la
table sont absolus : on réécrit sur place, on n'insère jamais.

L'image flash d'origine n'est jamais touchée ; `patch` écrit un fichier neuf
et vérifie que le diff tient dans les seules fenêtres visées.

  self-test                      round-trip sur les 705 icônes distinctes
  patch SORTIE id=img.png ...    id=#RRGGBB pour une icône unie

Les icônes d'origine sont l'oeuvre du fabricant : rien n'est extrait ici.
"""
import collections
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gobo_library import ICON, SIDE, Library, find_flash, write_png

PIXELS = SIDE * SIDE


def raw_icon(lib, gobo_id):
    off = lib.ptrs[gobo_id] - lib.base
    return lib.data[off:off + ICON]


def decode_raw(raw):
    """1728 octets → 576 quadruplets (r, g, b, a) sur 8 bits."""
    out = []
    for i in range(0, ICON, 3):
        v = raw[i] | (raw[i + 1] << 8)
        out.append(((v >> 11 & 31) * 255 // 31,
                    (v >> 5 & 63) * 255 // 63,
                    (v & 31) * 255 // 31,
                    raw[i + 2]))
    return out


def encode(pixels):
    """576 quadruplets (r, g, b, a) → 1728 octets.

    L'arrondi (+127) est ce qui rend l'aller-retour exact : la troncature
    ferait perdre un pas de quantification sur la moitié des valeurs.
    """
    if len(pixels) != PIXELS:
        raise ValueError(f"{len(pixels)} pixels, il en faut {PIXELS}")
    out = bytearray()
    for r, g, b, a in pixels:
        v = ((((r * 31 + 127) // 255) << 11)
             | (((g * 63 + 127) // 255) << 5)
             | ((b * 31 + 127) // 255))
        out += struct.pack("<HB", v, a)
    return bytes(out)


def read_png(path):
    """Lecteur PNG minimal : 8 bits par canal, RGB ou RGBA, non entrelacé."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} n'est pas un PNG")
    width = height = mode = None
    idat, off = bytearray(), 8
    while off + 8 <= len(data):
        size, tag = struct.unpack_from(">I4s", data, off)
        body = data[off + 8:off + 8 + size]
        if tag == b"IHDR":
            width, height, depth, mode, _, _, interlace = struct.unpack(
                ">IIBBBBB", body)
            if depth != 8 or mode not in (2, 6) or interlace:
                raise ValueError(
                    f"{path} : PNG attendu en 8 bits, RGB ou RGBA, "
                    "non entrelacé")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        off += 12 + size
    if width is None:
        raise ValueError(f"{path} : IHDR absent")
    step = 3 if mode == 2 else 4
    stride = width * step
    raw = zlib.decompress(bytes(idat))
    out, prev, pos = bytearray(), bytearray(stride), 0
    for _ in range(height):
        kind, pos = raw[pos], pos + 1
        line, pos = bytearray(raw[pos:pos + stride]), pos + stride
        for i in range(stride):
            left = line[i - step] if i >= step else 0
            up = prev[i]
            corner = prev[i - step] if i >= step else 0
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                p = left + up - corner
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - corner)
                near = (left if pa <= pb and pa <= pc
                        else up if pb <= pc else corner)
                line[i] = (line[i] + near) & 255
            elif kind:
                raise ValueError(f"{path} : filtre PNG {kind} inconnu")
        out += line
        prev = line
    pixels = [(out[i], out[i + 1], out[i + 2],
               out[i + 3] if step == 4 else 255)
              for i in range(0, len(out), step)]
    return width, height, pixels


def load_image(path):
    """Un PNG sans canal alpha rend l'icône entièrement opaque : les icônes
    du fabricant sont détourées, donc exporter en RGB écrase leur découpe."""
    width, height, pixels = read_png(path)
    if (width, height) != (SIDE, SIDE):
        raise ValueError(f"{path} : {width}x{height}, il faut {SIDE}x{SIDE}")
    return pixels


def solid(spec):
    """`#RRGGBB` → une icône unie, opaque."""
    if len(spec) != 7:
        raise ValueError(f"couleur attendue en #RRGGBB, reçu « {spec} »")
    r, g, b = (int(spec[k:k + 2], 16) for k in (1, 3, 5))
    return [(r, g, b, 255)] * PIXELS


def patch(lib, edits):
    """edits : {gobo_id: pixels} → image flash modifiée, longueur inchangée.

    Refuse toute icône dont le pointeur est partagé : dans la table 2.0.18,
    « Open » (0x1029417E) sert 96 entrées, et la réécrire les repeindrait
    toutes d'un coup.
    """
    uses = collections.Counter(lib.ptrs)
    data = bytearray(lib.data)
    for gobo_id, pixels in edits.items():
        ptr = lib.ptrs[gobo_id]
        if uses[ptr] > 1:
            others = [i for i, p in enumerate(lib.ptrs) if p == ptr]
            raise ValueError(
                f"l'icône {gobo_id} (« {lib.name(gobo_id)} ») partage son "
                f"pointeur avec {len(others) - 1} autres entrées "
                f"({others[:6]}…) : la réécrire les repeindrait toutes")
        off = ptr - lib.base
        data[off:off + ICON] = encode(pixels)
    return bytes(data)


def verify(before, after, lib, ids):
    """Le diff doit tenir exactement dans les fenêtres des icônes visées."""
    if len(before) != len(after):
        raise AssertionError("la longueur de l'image flash a changé")
    windows = [(lib.ptrs[i] - lib.base, lib.ptrs[i] - lib.base + ICON)
               for i in ids]
    scratch = bytearray(after)
    for lo, hi in windows:
        scratch[lo:hi] = before[lo:hi]
    if bytes(scratch) != before:
        raise AssertionError("des octets ont changé hors des icônes visées")
    return sum(x != y
               for lo, hi in windows
               for x, y in zip(before[lo:hi], after[lo:hi]))


def self_test(path):
    # La quantification doit être réversible sur toute la plage, sinon le
    # round-trip ne tiendrait que par chance sur les icônes du fabricant.
    for v in range(32):
        assert ((v * 255 // 31) * 31 + 127) // 255 == v, v
    for v in range(64):
        assert ((v * 255 // 63) * 63 + 127) // 255 == v, v

    lib = Library(path)
    distinct = sorted(set(lib.ptrs))
    for gobo_id in (lib.ptrs.index(p) for p in distinct):
        raw = raw_icon(lib, gobo_id)
        assert encode(decode_raw(raw)) == raw, gobo_id
    assert len(distinct) == 705, len(distinct)

    # Un PNG écrit par le dépôt doit se relire à l'identique.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "t.png")
        rgb = bytes(range(256)) * ((SIDE * SIDE * 3 + 255) // 256)
        rgb = rgb[:SIDE * SIDE * 3]
        write_png(png, SIDE, SIDE, rgb)
        _, _, pixels = read_png(png)
        assert [p[:3] for p in pixels] == [
            tuple(rgb[k:k + 3]) for k in range(0, len(rgb), 3)]
        assert all(p[3] == 255 for p in pixels)

    # Un patch ne doit toucher que sa propre fenêtre.
    target = next(i for i in range(len(lib.ptrs))
                  if collections.Counter(lib.ptrs)[lib.ptrs[i]] == 1)
    after = patch(lib, {target: solid("#ff00ff")})
    changed = verify(lib.data, after, lib, [target])
    assert changed > 0, "le patch n'a rien écrit"
    assert len(after) == len(lib.data)

    print(f"ok — {len(distinct)} icônes ré-encodées à l'octet près, "
          f"patch confiné ({changed} octets sur l'icône {target})")


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
    if command != "patch" or len(argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2

    out = argv[2]
    if os.path.abspath(out) == os.path.abspath(path):
        print("refus : la sortie écraserait l'image flash d'origine",
              file=sys.stderr)
        return 2
    lib = Library(path)
    edits = {}
    try:
        for spec in argv[3:]:
            key, _, value = spec.partition("=")
            if not value:
                raise ValueError(f"argument attendu en id=source, "
                                 f"reçu « {spec} »")
            gobo_id = int(key)
            edits[gobo_id] = (solid(value) if value.startswith("#")
                              else load_image(value))
        data = patch(lib, edits)
        changed = verify(lib.data, data, lib, list(edits))
    except ValueError as err:
        print(f"refus : {err}", file=sys.stderr)
        return 2
    with open(out, "wb") as handle:
        handle.write(data)
    names = ", ".join(f"{i} (« {lib.name(i)} »)" for i in sorted(edits))
    print(f"{out} — {len(data)} octets, {changed} modifiés sur {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
