#!/usr/bin/env python3
"""Writes gobo icons into a copy of the W1's flash image.

The exact inverse of `gobo_library.Library.icon()`: an icon is a 1728-byte
block, 24x24 pixels, 3 interleaved bytes per pixel — RGB565 little-endian then
8-bit alpha. The size is fixed and the table's pointers are absolute: we
rewrite in place, we never insert.

The original flash image is never touched; `patch` writes a new file and
checks that the diff stays inside the targeted windows.

  self-test                     round trip over the 705 distinct icons
  patch OUTPUT id=img.png ...   id=#RRGGBB for a solid icon,
                                id=mask:img.png for a silhouette
                                (also writes OUTPUT.json, the manifest)

A square image larger than 24x24 is reduced by area averaging. `mask:` reads
luminance as the alpha channel and renders the shape in white — the format an
image generator produces from "white motif on a black background".

The stock icons are the manufacturer's work: nothing is extracted here.
"""
import collections
import datetime
import hashlib
import json
import os
import struct
import sys
import tempfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gobo_library import ICON, SIDE, Library, find_flash, write_png

PIXELS = SIDE * SIDE


def raw_icon(lib, gobo_id):
    off = lib.ptrs[gobo_id] - lib.base
    return lib.data[off:off + ICON]


def decode_raw(raw):
    """1728 bytes → 576 (r, g, b, a) quadruples on 8 bits."""
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

    The +127 rounding is what makes the round trip exact: truncation would
    lose one quantisation step on half the values.
    """
    if len(pixels) != PIXELS:
        raise ValueError(f"{len(pixels)} pixels, {PIXELS} required")
    out = bytearray()
    for r, g, b, a in pixels:
        v = ((((r * 31 + 127) // 255) << 11)
             | (((g * 63 + 127) // 255) << 5)
             | ((b * 31 + 127) // 255))
        out += struct.pack("<HB", v, a)
    return bytes(out)


def read_png(path):
    """Minimal PNG reader: 8 bits per channel, RGB or RGBA, non-interlaced."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    width = height = mode = None
    idat, off, fin = bytearray(), 8, False
    while off + 12 <= len(data):
        size, tag = struct.unpack_from(">I4s", data, off)
        if off + 12 + size > len(data):
            raise ValueError(f"{path}: truncated {tag.decode('latin1')} chunk")
        body = data[off + 8:off + 8 + size]
        crc, = struct.unpack_from(">I", data, off + 8 + size)
        if zlib.crc32(tag + body) != crc:
            raise ValueError(
                f"{path}: invalid CRC on the {tag.decode('latin1')} chunk")
        if tag == b"IHDR":
            if size != 13:
                raise ValueError(f"{path}: {size}-byte IHDR")
            width, height, depth, mode, _, _, interlace = struct.unpack(
                ">IIBBBBB", body)
            if depth != 8 or mode not in (2, 6) or interlace:
                raise ValueError(
                    f"{path}: expected an 8-bit, RGB or RGBA, "
                    "non-interlaced PNG")
            if not width or not height:
                raise ValueError(f"{path}: {width}x{height} image")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            fin = True
            break
        off += 12 + size
    if width is None:
        raise ValueError(f"{path}: no IHDR")
    if not fin:
        raise ValueError(f"{path}: no IEND, truncated file")
    step = 3 if mode == 2 else 4
    stride = width * step
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as err:
        raise ValueError(f"{path}: unreadable IDAT data ({err})") from None
    if len(raw) != height * (1 + stride):
        raise ValueError(
            f"{path}: {len(raw)} bytes inflated, "
            f"{height * (1 + stride)} expected for {width}x{height}")
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
                raise ValueError(f"{path}: unknown PNG filter {kind}")
        out += line
        prev = line
    pixels = [(out[i], out[i + 1], out[i + 2],
               out[i + 3] if step == 4 else 255)
              for i in range(0, len(out), step)]
    return width, height, pixels


def downscale(width, height, pixels, value):
    """Area average of an N×N square down to 24×24, one value per source pixel.

    `value` extracts what gets averaged: a tuple (channels) or a scalar. The
    integer bounds `k*N//24` cover every source pixel exactly once, whatever
    N divides into.
    """
    if width != height or width < SIDE:
        raise ValueError(f"square image of at least {SIDE}x{SIDE} expected, "
                         f"got {width}x{height}")
    out = []
    for ty in range(SIDE):
        y0, y1 = ty * height // SIDE, (ty + 1) * height // SIDE
        for tx in range(SIDE):
            x0, x1 = tx * width // SIDE, (tx + 1) * width // SIDE
            acc, n = None, (x1 - x0) * (y1 - y0)
            for sy in range(y0, y1):
                row = sy * width
                for sx in range(x0, x1):
                    v = value(pixels[row + sx])
                    acc = v if acc is None else tuple(
                        a + b for a, b in zip(acc, v))
            out.append(tuple(c // n for c in acc))
    return out


def load_image(path):
    """A PNG with no alpha channel makes the icon fully opaque: the stock icons
    are cut out, so exporting as RGB flattens that cut-out away."""
    width, height, pixels = read_png(path)
    if (width, height) == (SIDE, SIDE):
        return pixels
    return downscale(width, height, pixels, lambda p: p)


def load_mask(path):
    """Silhouette: luminance × alpha of the source PNG → alpha channel, shape
    rendered in white. The inverse of a flat "white on black"."""
    width, height, pixels = read_png(path)
    lum = downscale(width, height, pixels,
                    lambda p: ((p[0] * 299 + p[1] * 587 + p[2] * 114)
                               // 1000 * p[3] // 255,))
    return [(255, 255, 255, v[0]) for v in lum]


def solid(spec):
    """`#RRGGBB` → a solid, opaque icon."""
    if len(spec) != 7:
        raise ValueError(f"colour expected as #RRGGBB, got \"{spec}\"")
    r, g, b = (int(spec[k:k + 2], 16) for k in (1, 3, 5))
    return [(r, g, b, 255)] * PIXELS


def patch(lib, edits):
    """edits: {gobo_id: pixels} → the modified flash image, same length.

    Refuses any icon whose pointer is shared: in the 2.0.18 table, "Open"
    (0x1029417E) serves 96 entries, and rewriting it would repaint all of
    them at once.
    """
    uses = collections.Counter(lib.ptrs)
    data = bytearray(lib.data)
    for gobo_id, pixels in edits.items():
        lib.check_id(gobo_id)
        ptr = lib.ptrs[gobo_id]
        if uses[ptr] > 1:
            others = [i for i, p in enumerate(lib.ptrs) if p == ptr]
            raise ValueError(
                f"icon {gobo_id} (\"{lib.name(gobo_id)}\") shares its pointer "
                f"with {len(others) - 1} other entries ({others[:6]}…): "
                "rewriting it would repaint them all")
        off = ptr - lib.base
        data[off:off + ICON] = encode(pixels)
    return bytes(data)


def verify(before, after, lib, ids):
    """The diff must fit exactly inside the targeted icons' windows."""
    if len(before) != len(after):
        raise ValueError("the flash image's length changed")
    windows = [(lib.ptrs[i] - lib.base, lib.ptrs[i] - lib.base + ICON)
               for i in ids]
    scratch = bytearray(after)
    for lo, hi in windows:
        scratch[lo:hi] = before[lo:hi]
    if bytes(scratch) != before:
        raise ValueError("bytes changed outside the targeted icons")
    return sum(x != y
               for lo, hi in windows
               for x, y in zip(before[lo:hi], after[lo:hi]))


def sha256(donnees):
    return hashlib.sha256(donnees).hexdigest()


def manifeste(source, lib, sortie, data, edits, changed):
    """What it takes to prove later that this copy came from that bundle.

    Length alone proves nothing: any file of the same size used to pass the
    upload guard. The two hashes close the chain installed bundle → manifest →
    the file that goes into the device.
    """
    dossier = os.path.basename(os.path.dirname(os.path.abspath(source)))
    return {
        "source": {"path": os.path.abspath(source), "bundle": dossier,
                   "sha256": sha256(lib.data), "size": len(lib.data)},
        "result": {"file": os.path.basename(sortie),
                   "sha256": sha256(data), "size": len(data)},
        "ids": sorted(edits),
        "windows": [[lib.ptrs[i] - lib.base, lib.ptrs[i] - lib.base + ICON]
                    for i in sorted(edits)],
        "bytesChanged": changed,
        "writtenAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def ecrire(sortie, data, contenu):
    """The patched file then its manifest; either one alone is useless."""
    with open(sortie, "xb") as handle:
        handle.write(data)
    try:
        with open(sortie + ".json", "x", encoding="utf-8") as handle:
            json.dump(contenu, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError:
        os.remove(sortie)                # never a patch without its manifest
        raise


def self_test(path):
    # Quantisation must be reversible over the whole range, or the round trip
    # would hold only by luck on the manufacturer's icons.
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

    # A PNG written by this repository must read back identical.
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "t.png")
        rgb = bytes(range(256)) * ((SIDE * SIDE * 3 + 255) // 256)
        rgb = rgb[:SIDE * SIDE * 3]
        write_png(png, SIDE, SIDE, rgb)
        _, _, pixels = read_png(png)
        assert [p[:3] for p in pixels] == [
            tuple(rgb[k:k + 3]) for k in range(0, len(rgb), 3)]
        assert all(p[3] == 255 for p in pixels)

    # Downscale and silhouette: a 48x48 half white / half black must give 12
    # full columns and 12 empty ones, with no half tone off the boundary.
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "m.png")
        rgb = b"".join((b"\xff\xff\xff" if x < 24 else b"\x00\x00\x00")
                       for _ in range(48) for x in range(48))
        write_png(png, 48, 48, rgb)
        icon = load_mask(png)
        assert all(p == (255, 255, 255, 255) for i, p in enumerate(icon)
                   if i % SIDE < 12), "left: full alpha expected"
        assert all(p[3] == 0 for i, p in enumerate(icon)
                   if i % SIDE >= 12), "right: zero alpha expected"
        flat = load_image(png)
        assert flat[0] == (255, 255, 255, 255) and flat[23] == (0, 0, 0, 255)

    # A patch must touch nothing but its own window.
    target = next(i for i in range(len(lib.ptrs))
                  if collections.Counter(lib.ptrs)[lib.ptrs[i]] == 1)
    after = patch(lib, {target: solid("#ff00ff")})
    changed = verify(lib.data, after, lib, [target])
    assert changed > 0, "the patch wrote nothing"
    assert len(after) == len(lib.data)

    # A byte changed outside the targeted windows is a refusal, not a log line.
    hors = bytearray(after)
    debut = lib.ptrs[target] - lib.base
    libre = 0 if debut > 0 else debut + ICON
    hors[libre] ^= 0xFF
    try:
        verify(lib.data, bytes(hors), lib, [target])
        raise AssertionError("an out-of-window byte got through")
    except ValueError:
        pass

    # The manifest counts the bytes that actually differ, and the patch and
    # its manifest live or die together.
    with tempfile.TemporaryDirectory() as tmp:
        sortie = os.path.join(tmp, "flash-custom.bin")
        contenu = manifeste(path, lib, sortie, after, {target: None}, changed)
        ecrire(sortie, after, contenu)
        releve = json.load(open(sortie + ".json", encoding="utf-8"))
        assert releve["bytesChanged"] == sum(
            x != y for x, y in zip(lib.data, after)), releve["bytesChanged"]
        assert releve["result"]["sha256"] == sha256(open(sortie, "rb").read())
        assert releve["source"]["sha256"] == sha256(lib.data)
        assert releve["result"]["size"] == releve["source"]["size"]
        try:
            ecrire(sortie, after, contenu)
            raise AssertionError("an existing output was overwritten")
        except FileExistsError:
            pass

    # An "almost valid" PNG is refused, class by class.
    with tempfile.TemporaryDirectory() as tmp:
        bon = os.path.join(tmp, "bon.png")
        write_png(bon, SIDE, SIDE, bytes(SIDE * SIDE * 3))
        octets = open(bon, "rb").read()
        casses = {
            "CRC": octets[:-5] + bytes([octets[-5] ^ 0xFF]) + octets[-4:],
            "IEND": octets[:-12],
            "truncated": octets[:len(octets) - 20],
        }
        for nom, corps in casses.items():
            chemin = os.path.join(tmp, f"{nom}.png")
            open(chemin, "wb").write(corps)
            try:
                read_png(chemin)
                raise AssertionError(f"PNG accepted despite: {nom}")
            except ValueError:
                pass
        # A valid IDAT, but too short for the height it declares.
        court = bytearray(octets)
        entete = court.index(b"IHDR")
        struct.pack_into(">I", court, entete + 8, SIDE * 2)      # height x2
        struct.pack_into(">I", court, entete + 12 + 13,
                         zlib.crc32(bytes(court[entete:entete + 4 + 13])))
        chemin = os.path.join(tmp, "court.png")
        open(chemin, "wb").write(bytes(court))
        try:
            read_png(chemin)
            raise AssertionError("PNG accepted with an inconsistent height")
        except ValueError:
            pass

    # An out-of-table id patches nothing.
    for refuse in (-1, 800):
        try:
            patch(lib, {refuse: solid("#000000")})
            raise AssertionError(f"id accepted: {refuse}")
        except ValueError:
            pass

    print(f"ok — {len(distinct)} icons re-encoded byte for byte, patch "
          f"confined ({changed} bytes on icon {target}), manifest and PNG "
          "verified")


def _parseur():
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--flash", help="source flash image; by default the "
                                         "most recent, or $WOLFMIX_FLASH")
    commandes = parseur.add_subparsers(dest="commande")
    commandes.add_parser("self-test", help="round trip over the 705 icons")
    patch_cmd = commandes.add_parser(
        "patch", help="writes a patched COPY of the flash, plus its manifest")
    patch_cmd.add_argument("sortie", help="new file; an existing one is refused")
    patch_cmd.add_argument("edits", nargs="+", metavar="id=source",
                           help="id=#RRGGBB, id=image.png ou id=mask:image.png")
    return parseur


def main(argv=None):
    parseur = _parseur()
    args = parseur.parse_args(argv)
    path = find_flash(args.flash or os.environ.get("WOLFMIX_FLASH"))
    if not path:
        print("no local flash image (WTOOLS never downloaded the firmware) — "
              "nothing to do", file=sys.stderr)
        return 0
    if (args.commande or "self-test") == "self-test":
        self_test(path)
        return 0

    out = args.sortie
    if os.path.abspath(out) == os.path.abspath(path):
        print("refused: the output would overwrite the original flash image",
              file=sys.stderr)
        return 2
    lib = Library(path)
    edits = {}
    try:
        for spec in args.edits:
            key, _, value = spec.partition("=")
            if not value:
                raise ValueError("argument expected as id=source, got "
                                 f"\"{spec}\"")
            edits[int(key)] = (solid(value) if value.startswith("#")
                               else load_mask(value[5:])
                               if value.startswith("mask:")
                               else load_image(value))
        data = patch(lib, edits)
        changed = verify(lib.data, data, lib, list(edits))
        contenu = manifeste(path, lib, out, data, edits, changed)
    except (ValueError, struct.error, zlib.error, OSError) as err:
        print(f"refused: {err}", file=sys.stderr)
        return 2
    try:
        ecrire(out, data, contenu)
    except FileExistsError as err:
        print(f"refused: {err.filename} already exists", file=sys.stderr)
        return 2
    names = ", ".join(f"{i} (\"{lib.name(i)}\")" for i in sorted(edits))
    print(f"{out} — {len(data)} bytes, {changed} changed on {names}\n"
          f"{out}.json — manifest: {contenu['source']['bundle']}, "
          f"{len(contenu['ids'])} icon(s), {changed} bytes changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
