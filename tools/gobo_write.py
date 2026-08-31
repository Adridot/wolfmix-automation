#!/usr/bin/env python3
"""Écrit des icônes de gobo dans une copie de l'image flash du W1.

Inverse exact de `gobo_library.Library.icon()` : une icône est un bloc de
1728 octets, 24x24 pixels, 3 octets par pixel entrelacés — RGB565
little-endian puis alpha 8 bits. La taille est fixe et les pointeurs de la
table sont absolus : on réécrit sur place, on n'insère jamais.

L'image flash d'origine n'est jamais touchée ; `patch` écrit un fichier neuf
et vérifie que le diff tient dans les seules fenêtres visées.

  self-test                      round-trip sur les 705 icônes distinctes
  patch SORTIE id=img.png ...    id=#RRGGBB pour une icône unie,
                                 id=mask:img.png pour une silhouette
                                 (écrit aussi SORTIE.json, le manifeste)

Une image carrée plus grande que 24x24 est réduite par moyenne de zone.
`mask:` lit la luminance comme canal alpha et rend la forme en blanc — le
format que produit « motif blanc sur fond noir » d'un générateur d'images.

Les icônes d'origine sont l'oeuvre du fabricant : rien n'est extrait ici.
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
    idat, off, fin = bytearray(), 8, False
    while off + 12 <= len(data):
        size, tag = struct.unpack_from(">I4s", data, off)
        if off + 12 + size > len(data):
            raise ValueError(f"{path} : chunk {tag.decode('latin1')} tronqué")
        body = data[off + 8:off + 8 + size]
        crc, = struct.unpack_from(">I", data, off + 8 + size)
        if zlib.crc32(tag + body) != crc:
            raise ValueError(
                f"{path} : CRC invalide sur le chunk {tag.decode('latin1')}")
        if tag == b"IHDR":
            if size != 13:
                raise ValueError(f"{path} : IHDR de {size} octets")
            width, height, depth, mode, _, _, interlace = struct.unpack(
                ">IIBBBBB", body)
            if depth != 8 or mode not in (2, 6) or interlace:
                raise ValueError(
                    f"{path} : PNG attendu en 8 bits, RGB ou RGBA, "
                    "non entrelacé")
            if not width or not height:
                raise ValueError(f"{path} : image {width}x{height}")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            fin = True
            break
        off += 12 + size
    if width is None:
        raise ValueError(f"{path} : IHDR absent")
    if not fin:
        raise ValueError(f"{path} : IEND absent, fichier tronqué")
    step = 3 if mode == 2 else 4
    stride = width * step
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error as err:
        raise ValueError(f"{path} : données IDAT illisibles ({err})") from None
    if len(raw) != height * (1 + stride):
        raise ValueError(
            f"{path} : {len(raw)} octets décompressés, "
            f"{height * (1 + stride)} attendus pour {width}x{height}")
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


def downscale(width, height, pixels, value):
    """Moyenne de zone d'un carré N×N vers 24×24, une valeur par pixel source.

    `value` extrait ce qui est moyenné : un tuple (canaux) ou un scalaire.
    Les bornes entières `k*N//24` couvrent chaque pixel source exactement une
    fois, quelle que soit la divisibilité de N.
    """
    if width != height or width < SIDE:
        raise ValueError(f"image carrée d'au moins {SIDE}x{SIDE} attendue, "
                         f"reçu {width}x{height}")
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
    """Un PNG sans canal alpha rend l'icône entièrement opaque : les icônes
    du fabricant sont détourées, donc exporter en RGB écrase leur découpe."""
    width, height, pixels = read_png(path)
    if (width, height) == (SIDE, SIDE):
        return pixels
    return downscale(width, height, pixels, lambda p: p)


def load_mask(path):
    """Silhouette : luminance × alpha du PNG source → canal alpha, forme
    rendue en blanc. C'est l'inverse d'un aplat « blanc sur fond noir »."""
    width, height, pixels = read_png(path)
    lum = downscale(width, height, pixels,
                    lambda p: ((p[0] * 299 + p[1] * 587 + p[2] * 114)
                               // 1000 * p[3] // 255,))
    return [(255, 255, 255, v[0]) for v in lum]


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
        lib.check_id(gobo_id)
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
        raise ValueError("la longueur de l'image flash a changé")
    windows = [(lib.ptrs[i] - lib.base, lib.ptrs[i] - lib.base + ICON)
               for i in ids]
    scratch = bytearray(after)
    for lo, hi in windows:
        scratch[lo:hi] = before[lo:hi]
    if bytes(scratch) != before:
        raise ValueError("des octets ont changé hors des icônes visées")
    return sum(x != y
               for lo, hi in windows
               for x, y in zip(before[lo:hi], after[lo:hi]))


def sha256(donnees):
    return hashlib.sha256(donnees).hexdigest()


def manifeste(source, lib, sortie, data, edits, changed):
    """Ce qu'il faut pour prouver plus tard que cette copie vient de ce bundle.

    La longueur seule ne prouve rien : n'importe quel fichier de même taille
    passait la garde d'upload. Les deux empreintes, elles, ferment la chaîne
    bundle installé → manifeste → fichier qui part dans l'appareil.
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
    """Le fichier patché puis son manifeste ; l'un sans l'autre ne sert à rien."""
    with open(sortie, "xb") as handle:
        handle.write(data)
    try:
        with open(sortie + ".json", "x", encoding="utf-8") as handle:
            json.dump(contenu, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    except OSError:
        os.remove(sortie)                # jamais de patch sans son manifeste
        raise


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
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "t.png")
        rgb = bytes(range(256)) * ((SIDE * SIDE * 3 + 255) // 256)
        rgb = rgb[:SIDE * SIDE * 3]
        write_png(png, SIDE, SIDE, rgb)
        _, _, pixels = read_png(png)
        assert [p[:3] for p in pixels] == [
            tuple(rgb[k:k + 3]) for k in range(0, len(rgb), 3)]
        assert all(p[3] == 255 for p in pixels)

    # Réduction et silhouette : un 48x48 moitié blanc / moitié noir doit
    # donner 12 colonnes pleines, 12 vides, sans demi-teinte hors frontière.
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "m.png")
        rgb = b"".join((b"\xff\xff\xff" if x < 24 else b"\x00\x00\x00")
                       for _ in range(48) for x in range(48))
        write_png(png, 48, 48, rgb)
        icon = load_mask(png)
        assert all(p == (255, 255, 255, 255) for i, p in enumerate(icon)
                   if i % SIDE < 12), "gauche : alpha plein attendu"
        assert all(p[3] == 0 for i, p in enumerate(icon)
                   if i % SIDE >= 12), "droite : alpha nul attendu"
        flat = load_image(png)
        assert flat[0] == (255, 255, 255, 255) and flat[23] == (0, 0, 0, 255)

    # Un patch ne doit toucher que sa propre fenêtre.
    target = next(i for i in range(len(lib.ptrs))
                  if collections.Counter(lib.ptrs)[lib.ptrs[i]] == 1)
    after = patch(lib, {target: solid("#ff00ff")})
    changed = verify(lib.data, after, lib, [target])
    assert changed > 0, "le patch n'a rien écrit"
    assert len(after) == len(lib.data)

    # Un octet changé hors des fenêtres visées est un refus, pas une trace.
    hors = bytearray(after)
    debut = lib.ptrs[target] - lib.base
    libre = 0 if debut > 0 else debut + ICON
    hors[libre] ^= 0xFF
    try:
        verify(lib.data, bytes(hors), lib, [target])
        raise AssertionError("un octet hors fenêtre est passé")
    except ValueError:
        pass

    # Le manifeste compte les octets réellement différents, et le patch et
    # son manifeste vivent ou meurent ensemble.
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
            raise AssertionError("une sortie existante a été écrasée")
        except FileExistsError:
            pass

    # Un PNG « presque valide » est refusé, classe par classe.
    with tempfile.TemporaryDirectory() as tmp:
        bon = os.path.join(tmp, "bon.png")
        write_png(bon, SIDE, SIDE, bytes(SIDE * SIDE * 3))
        octets = open(bon, "rb").read()
        casses = {
            "CRC": octets[:-5] + bytes([octets[-5] ^ 0xFF]) + octets[-4:],
            "IEND": octets[:-12],
            "tronqué": octets[:len(octets) - 20],
        }
        for nom, corps in casses.items():
            chemin = os.path.join(tmp, f"{nom}.png")
            open(chemin, "wb").write(corps)
            try:
                read_png(chemin)
                raise AssertionError(f"PNG accepté malgré : {nom}")
            except ValueError:
                pass
        # Un IDAT valide mais trop court pour la hauteur annoncée.
        court = bytearray(octets)
        entete = court.index(b"IHDR")
        struct.pack_into(">I", court, entete + 8, SIDE * 2)      # height x2
        struct.pack_into(">I", court, entete + 12 + 13,
                         zlib.crc32(bytes(court[entete:entete + 4 + 13])))
        chemin = os.path.join(tmp, "court.png")
        open(chemin, "wb").write(bytes(court))
        try:
            read_png(chemin)
            raise AssertionError("PNG accepté avec une hauteur incohérente")
        except ValueError:
            pass

    # Un id hors table ne patche rien.
    for refuse in (-1, 800):
        try:
            patch(lib, {refuse: solid("#000000")})
            raise AssertionError(f"id accepté : {refuse}")
        except ValueError:
            pass

    print(f"ok — {len(distinct)} icônes ré-encodées à l'octet près, "
          f"patch confiné ({changed} octets sur l'icône {target}), "
          "manifeste et PNG vérifiés")


def _parseur():
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--flash", help="image flash source ; par defaut la "
                                         "plus recente, ou $WOLFMIX_FLASH")
    commandes = parseur.add_subparsers(dest="commande")
    commandes.add_parser("self-test", help="round-trip sur les 705 icones")
    patch_cmd = commandes.add_parser(
        "patch", help="ecrit une COPIE patchee du flash, plus son manifeste")
    patch_cmd.add_argument("sortie", help="fichier neuf ; un existant est refuse")
    patch_cmd.add_argument("edits", nargs="+", metavar="id=source",
                           help="id=#RRGGBB, id=image.png ou id=mask:image.png")
    return parseur


def main(argv=None):
    parseur = _parseur()
    args = parseur.parse_args(argv)
    path = find_flash(args.flash or os.environ.get("WOLFMIX_FLASH"))
    if not path:
        print("aucune image flash locale (WTOOLS n'a jamais téléchargé le "
              "firmware) — rien à faire", file=sys.stderr)
        return 0
    if (args.commande or "self-test") == "self-test":
        self_test(path)
        return 0

    out = args.sortie
    if os.path.abspath(out) == os.path.abspath(path):
        print("refus : la sortie écraserait l'image flash d'origine",
              file=sys.stderr)
        return 2
    lib = Library(path)
    edits = {}
    try:
        for spec in args.edits:
            key, _, value = spec.partition("=")
            if not value:
                raise ValueError(f"argument attendu en id=source, "
                                 f"reçu « {spec} »")
            edits[int(key)] = (solid(value) if value.startswith("#")
                               else load_mask(value[5:])
                               if value.startswith("mask:")
                               else load_image(value))
        data = patch(lib, edits)
        changed = verify(lib.data, data, lib, list(edits))
        contenu = manifeste(path, lib, out, data, edits, changed)
    except (ValueError, struct.error, zlib.error, OSError) as err:
        print(f"refus : {err}", file=sys.stderr)
        return 2
    try:
        ecrire(out, data, contenu)
    except FileExistsError as err:
        print(f"refus : {err.filename} existe déjà", file=sys.stderr)
        return 2
    names = ", ".join(f"{i} (« {lib.name(i)} »)" for i in sorted(edits))
    print(f"{out} — {len(data)} octets, {changed} modifiés sur {names}\n"
          f"{out}.json — manifeste : {contenu['source']['bundle']}, "
          f"{len(contenu['ids'])} icône(s), {changed} octets modifiés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
