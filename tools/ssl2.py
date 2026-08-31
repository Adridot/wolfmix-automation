#!/usr/bin/env python3
"""Read, write and generate Nicolaudie `.ssl2` fixture profiles.

An `.ssl2` file is XML under AraCrypt, a three-LFSR stream cipher. Why that is
read here at all, and the four conditions it depends on, is `LEGAL.md`; the
format itself is `docs/ssl2-format.md`. Nothing from the vendor's library is
committed — the tools read the copy already installed on this machine.

Three layers, each with its own oracle:

- crypto: `transform` is its own inverse, except that a plaintext NUL comes
  back as the keystream byte. XML has no NUL, so decrypt/encrypt round-trips.
- codec: `parse` → `write` reproduces the input byte for byte, or `parse`
  raises. There is no partial read; an unknown attribute passes through
  verbatim, in its original order and quoting.
- generator: a JSON description → a profile shaped like the library's own
  `_Generic` fixtures, because a file the software refuses is worth nothing.

`verify` runs the first two over the local library and is the self-check.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

# --- AraCrypt ---------------------------------------------------------------
# Ported from the published reference: HakanL's gist, by way of the MIT-licensed
# `ssl2-tools` (npm), itself over Ara Abrahamian's CodeProject class. No key was
# recovered here — see LEGAL.md, "`.ssl2` fixture profiles".
CLE_DEFAUT = "DasCryptKey"

_MASK = (0x80000062, 0x40000020, 0x10000002)
_ROT0 = (0x7FFFFFFF, 0x3FFFFFFF, 0x0FFFFFFF)
_ROT1 = (0x80000000, 0xC0000000, 0xF0000000)
_SEED = (0x13579BDF, 0x2468ACE0, 0xFDB97531)


def _keystream(n, key=CLE_DEFAUT):
    """`n` bytes of keystream for `key`, generated once and kept.

    The LFSRs never look at the data — the stream is a pure function of the
    key. That is what makes a 25 610-file sweep tractable in Python: generate
    the stream once, then the per-file work is an XOR. It is also why one
    keystream must never be reused across two *streams* of one file: an .ssl2
    is one stream from offset 0, and that is the only way it is used here.
    """
    if not key:
        raise ValueError("clé vide")
    cle = key.encode("latin-1") if isinstance(key, str) else bytes(key)
    etat = _CACHE.get(cle)
    if etat is None:
        # The key is grown to 12 bytes by appending its own bytes from the
        # start — from the string as it grows, not the original, which only
        # shows for keys shorter than 6.
        seed, i = bytearray(cle), 0
        while len(seed) < 12:
            seed.append(seed[i])
            i += 1
        a, b, c = _SEED
        for i in range(4):
            a = ((a << 8) | seed[i + 0]) & 0xFFFFFFFF
            b = ((b << 8) | seed[i + 4]) & 0xFFFFFFFF
            c = ((c << 8) | seed[i + 8]) & 0xFFFFFFFF
        etat = _CACHE[cle] = [a or _SEED[0], b or _SEED[1], c or _SEED[2],
                              bytearray()]
    a, b, c, flux = etat
    while len(flux) < n:
        octet = 0
        sortie_b, sortie_c = b & 1, c & 1
        for _ in range(8):
            if a & 1:
                a = ((a ^ _MASK[0]) >> 1) | _ROT1[0]
                if b & 1:
                    b, sortie_b = ((b ^ _MASK[1]) >> 1) | _ROT1[1], 1
                else:
                    b, sortie_b = (b >> 1) & _ROT0[1], 0
            else:
                a = (a >> 1) & _ROT0[0]
                if c & 1:
                    c, sortie_c = ((c ^ _MASK[2]) >> 1) | _ROT1[2], 1
                else:
                    c, sortie_c = (c >> 1) & _ROT0[2], 0
            octet = ((octet << 1) | (sortie_b ^ sortie_c)) & 0xFF
        flux.append(octet)
    etat[0], etat[1], etat[2] = a, b, c
    return flux


_CACHE = {}


def transforme(data, key=CLE_DEFAUT):
    """Encrypt or decrypt: the same operation, on the NUL caveat below."""
    n = len(data)
    if not n:
        return b""
    flux = _keystream(n, key)[:n]
    out = bytearray((int.from_bytes(data, "big")
                     ^ int.from_bytes(flux, "big")).to_bytes(n, "big"))
    # The trap: a result of 0 is replaced by the keystream byte. Not a pure
    # XOR, and the reason a plaintext NUL does not survive a round trip.
    i = out.find(0)
    while i >= 0:
        out[i] = flux[i]
        i = out.find(0, i + 1)
    return bytes(out)


dechiffre = transforme
chiffre = transforme  # same operation; named twice because callers mean two things


def charge_xml(chemin, key=CLE_DEFAUT):
    """Decrypt a file and refuse anything whose payload is not XML."""
    with open(chemin, "rb") as flux:
        clair = dechiffre(flux.read(), key)
    if not clair.lstrip()[:5].startswith(b"<?xml"):
        raise ValueError(f"{chemin} : le contenu déchiffré ne commence pas par "
                         f"<?xml — ce n'est pas un .ssl2 (ou la clé est fausse)")
    return clair


# --- Local library ----------------------------------------------------------
# The vendor's own ScanLibrary, on this machine. It is the round-trip oracle,
# exactly as corpus/ is for the .wpj tools: read, never copied into the tree.
BIBLIO_ENV = "SSL2_LIBRARY"
BIBLIO_DEFAUT = "/Applications/Easy View/ScanLibrary"
ABSTENTION = "ABSTAINED"


def fichiers_biblio():
    racine = os.environ.get(BIBLIO_ENV) or BIBLIO_DEFAUT
    return sorted(glob.glob(os.path.join(racine, "**", "*.ssl2"), recursive=True))


def pas_de_biblio():
    racine = os.environ.get(BIBLIO_ENV) or BIBLIO_DEFAUT
    print(f"ssl2: {ABSTENTION} — aucune bibliothèque dans {racine}, rien n'a "
          f"été vérifié (voir docs/ssl2-format.md)", file=sys.stderr)


# --- XML codec -------------------------------------------------------------
# Measured over the 25 610 files of a local library, and the reason the writer
# needs no options: the emission is uniform. One prolog, no text content, no
# comment, no CDATA, no gap between tags; attributes always separated by one
# space and always double-quoted; an open tag ends `>`, an empty one ` />`.
# Deviating from any of that would break the round trip, and `verify` is what
# says so.
PROLOG = '<?xml version="1.0" encoding="UTF-8"?>'
_BALISE = re.compile(r'<(/?)([A-Z0-9]+)((?:\s+[A-Z0-9]+="[^"]*")*)\s*(/?)>')
_ATTR = re.compile(r'\s+([A-Z0-9]+)="([^"]*)"')

# Bytes travel as latin-1 text: every byte round-trips, and a name the vendor
# stored as mojibake stays the bytes it was rather than being "fixed" on the
# way through. `vers_utf8`/`depuis_utf8` are the two doors in and out.
def depuis_utf8(s):
    return s.encode("utf-8").decode("latin-1")


def vers_utf8(s):
    return s.encode("latin-1").decode("utf-8", "replace")


class Element:
    """One XML element, faithful to the stream: attribute order included."""

    __slots__ = ("tag", "attrs", "enfants", "vide")

    def __init__(self, tag, attrs=None, enfants=None, vide=None):
        self.tag = tag
        self.attrs = dict(attrs or {})      # insertion order = stream order
        self.enfants = list(enfants or [])
        # `vide` is how it was written, not whether it has children: the corpus
        # has both `<SSLPRESETS ... />` and `<SSLPRESETS ...></SSLPRESETS>`,
        # and re-emitting one as the other is not a byte-identical round trip.
        self.vide = not self.enfants if vide is None else vide

    def __getitem__(self, nom):
        return self.attrs[nom]

    def get(self, nom, defaut=None):
        return self.attrs.get(nom, defaut)

    def trouve(self, tag):
        """Every descendant with this tag, in document order."""
        for e in self.enfants:
            if e.tag == tag:
                yield e
            yield from e.trouve(tag)

    def __repr__(self):
        return f"<{self.tag} {len(self.attrs)} attrs, {len(self.enfants)} enfants>"


def parse(xml, source="<xml>"):
    """XML bytes → Element tree. Raises rather than reading a file partly."""
    if isinstance(xml, bytes):
        xml = xml.decode("latin-1")
    if not xml.startswith(PROLOG):
        raise ValueError(f"{source} : prologue inattendu {xml[:40]!r}")
    pos, pile, racine = len(PROLOG), [], None
    for m in _BALISE.finditer(xml, pos):
        if m.start() != pos:
            raise ValueError(f"{source} : contenu hors balise à l'offset "
                             f"{pos} : {xml[pos:m.start()][:40]!r}")
        pos = m.end()
        ferme, tag, corps, vide = m.groups()
        if ferme:
            if not pile or pile[-1].tag != tag:
                raise ValueError(f"{source} : </{tag}> ferme "
                                 f"{pile[-1].tag if pile else 'rien'}")
            pile.pop()
            continue
        e = Element(tag, _ATTR.findall(corps), vide=bool(vide))
        if len(e.attrs) != len(_ATTR.findall(corps)):
            raise ValueError(f"{source} : attribut répété dans <{tag}>")
        if pile:
            pile[-1].enfants.append(e)
        elif racine is None:
            racine = e
        else:
            raise ValueError(f"{source} : deuxième racine <{tag}>")
        if not vide:
            pile.append(e)
    if pos != len(xml):
        raise ValueError(f"{source} : queue non balisée {xml[pos:][:40]!r}")
    if pile:
        raise ValueError(f"{source} : <{pile[-1].tag}> jamais fermée")
    if racine is None:
        raise ValueError(f"{source} : document vide")
    return racine


def write(racine):
    """Element tree → XML bytes. Deterministic: no option, no choice."""
    morceaux = [PROLOG]

    def emets(e):
        morceaux.append(f"<{e.tag}")
        for nom, valeur in e.attrs.items():
            morceaux.append(f' {nom}="{valeur}"')
        if e.vide:
            morceaux.append(" />")
            if e.enfants:
                raise ValueError(f"<{e.tag}> marquée vide mais a des enfants")
            return
        morceaux.append(">")
        for enfant in e.enfants:
            emets(enfant)
        morceaux.append(f"</{e.tag}>")

    emets(racine)
    return "".join(morceaux).encode("latin-1")


def charge(chemin, key=CLE_DEFAUT):
    """A `.ssl2` on disk → the parsed tree, root checked."""
    racine = parse(charge_xml(chemin, key), chemin)
    verifie_racine(racine, chemin)
    return racine


def verifie_racine(racine, source="<xml>"):
    """What this codec claims to understand, and nothing wider.

    The online store also serves VERSION="2" and files that are not well-formed
    XML at all. Reading one of those with the V3 model would not fail loudly,
    it would fail quietly — so it is refused here instead.
    """
    if racine.tag != "DLMFILE":
        raise ValueError(f"{source} : racine <{racine.tag}>, attendu <DLMFILE>")
    version, type_ = racine.get("VERSION"), racine.get("TYPE")
    if version != "3":
        raise ValueError(f"{source} : DLMFILE VERSION={version!r} non pris en "
                         f"charge (seul VERSION=\"3\" est décodé)")
    if type_ != "SSLLIBRARY":
        raise ValueError(f"{source} : DLMFILE TYPE={type_!r}, attendu "
                         f"\"SSLLIBRARY\"")
    return racine


def echappe(s):
    """Escape a value for an attribute. Used by the generator, never by the
    codec: the corpus's own escaping passes through verbatim."""
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


# --- Enums -----------------------------------------------------------------
# Rebuilt from a local library by `ssl2.py enums`, which recomputes both tables
# and refuses a value it cannot account for. Each entry is
# `numéro: (lecture, part, n)`:
#
#   n     = how many channels/presets in the library carry that number;
#   part  = what share of them agree on the name, once the obvious variants
#           are folded together (case, spacing, a "1." prefix, the fine-channel
#           marker the corpus writes as mojibake);
#   lecture = the name — the vote's when the vote is clear, the family's when
#           the vote splits across variants of one idea (0 "Generic" is 5%
#           because a generic channel is called anything at all), and a
#           preset's parent channel type when that is what settles it: preset
#           3 is 96% under channel 5, which is what makes it the colour
#           wheel's rotation rather than some other wheel's.
#
# `INCERTAINS` names the numbers whose reading is NOT established — a split
# vote, a family that does not hold together, or too few samples to mean
# anything. They are readable and writable like any other; they are simply not
# claims. Never turn one into a plain name without a measurement.
# Corroboration: the public table in `ssl2-tools` covers 16 channel numbers and
# agrees with every one of them, except 37, which it reads "Auto Programs".
TYPE_CANAL = {
    0: ("Generic", 5, 158410),
    1: ("Pan", 82, 37992),
    2: ("Tilt", 82, 44094),
    3: ("Barrel Roll", 28, 164),
    4: ("Barrel Pan", 17, 225),
    5: ("Color Wheel", 41, 18957),
    6: ("Color Wheel Rotation", 34, 189),
    7: ("Dimmer", 69, 78378),
    8: ("Gobo Wheel", 23, 16068),
    9: ("Gobo Rotation", 65, 7697),
    10: ("Gobo Index", 31, 351),
    11: ("Gobo Shake", 66, 448),
    12: ("Gobo Wheel Rotation", 41, 304),
    13: ("Iris", 94, 2408),
    14: ("Zoom", 89, 14246),
    15: ("Shutter / Strobe", 45, 55666),
    16: ("Focus", 98, 9328),
    17: ("Frost", 85, 5188),
    18: ("Speed", 25, 43923),
    19: ("Prism", 66, 9390),
    20: ("Prism Rotation", 62, 6714),
    21: ("Prism Index", 31, 71),
    22: ("Lamp", 69, 2271),
    23: ("Color Temperature", 26, 8575),
    24: ("Smoke", 19, 1780),
    25: ("Red", 68, 132006),
    26: ("Green", 67, 132003),
    27: ("Blue", 68, 132003),
    28: ("Cyan", 99, 2972),
    29: ("Magenta", 99, 2970),
    30: ("Yellow", 99, 2969),
    31: ("White", 70, 70545),
    32: ("Gobo Bounce", 33, 12),
    33: ("Framing Rotation", 20, 448),
    34: ("Framing Blade Rotation", 6, 248),
    35: ("Framing Blade", 5, 2408),
    36: ("Animation Wheel", 70, 523),
    37: ("Macro", 9, 25850),
    43: ("Warm White", 65, 6191),
    44: ("Cold White", 64, 4080),
    45: ("Amber", 76, 16108),
    46: ("Uv", 82, 7329),
    47: ("Lime", 33, 1810),
    48: ("Lime", 94, 2386),
    50: ("Cyan", 71, 63),
    52: ("Pink", 27, 11),
    53: ("Mint", 100, 331),
}
TYPE_PRESET = {
    0: ("No Function", 9, 1139945),
    1: ("Color", 7, 309103),
    2: ("Color Combination 2", 3, 63545),
    3: ("Color Wheel Rotation", 37, 20609),
    4: ("Dimmer", 82, 73992),
    5: ("Dimmer Simple", 19, 593),
    6: ("Dimmer Pulse", 24, 21808),
    7: ("Gobo", 4, 279288),
    8: ("Gobo Rotation", 33, 14449),
    9: ("Rotation Index", 56, 6249),
    10: ("Gobo Shake", 24, 4129),
    11: ("Gobo Wheel Rotation", 45, 24342),
    12: ("Iris", 34, 2277),
    13: ("Iris Open/Closed", 13, 965),
    14: ("Iris Pulse", 19, 4314),
    15: ("Zoom", 62, 13638),
    16: ("Zoom In/Out", 8, 1780),
    17: ("Lamp On", 89, 3402),
    18: ("Lamp Off", 94, 3274),
    19: ("Shutter Open", 52, 73838),
    20: ("Shutter Closed", 48, 22863),
    21: ("Strobe", 59, 83629),
    22: ("Pulse Strobe", 13, 17473),
    23: ("Blackout While Moving", 73, 5310),
    24: ("Focus", 57, 7866),
    25: ("Focus Simple", 8, 274),
    26: ("Frost", 63, 5593),
    27: ("Frost Simple", 12, 932),
    28: ("Speed", 89, 45355),
    29: ("Speed Tracking", 34, 595),
    30: ("Speed Simple", 11, 1780),
    31: ("Prism", 33, 25837),
    32: ("Prism Rotation", 39, 15545),
    33: ("Prism Rotation Index", 58, 7421),
    34: ("Color Temperature", 12, 9387),
    35: ("Color Temperature Step", 12, 1827),
    36: ("Barrel Roll Rotation", 18, 473),
    37: ("Smoke", 13, 2652),
    38: ("Smoke Simple", 10, 163),
    39: ("Frost Pulse", 20, 1186),
    40: ("Rotation Off", 95, 22266),
    41: ("Reset", 27, 9411),
    42: ("Strobe Off", 95, 29456),
    43: ("Color Combination 3", 15, 10436),
    44: ("Color Combination 4", 36, 3630),
    45: ("Color Wheel Index", 62, 1414),
    46: ("Animation Wheel Rotation", 12, 1026),
    47: ("Blackout While Gobo Wheel Changing", 82, 995),
    48: ("Blackout While Color Wheel Changing", 85, 1044),
    49: ("Blackout While Wheel Changing", 62, 1451),
    51: ("Framing Rotation", 19, 413),
    52: ("Framing Rotation Index", 29, 156),
    53: ("Framing Blade 1", 38, 523),
    54: ("Framing Blade 2", 39, 499),
    55: ("Framing Blade 3", 39, 499),
    56: ("Framing Blade 4", 39, 499),
    57: ("Framing Blade 1 Rotation", 11, 105),
    58: ("Framing Blade 2 Rotation", 15, 78),
    59: ("Framing Blade 4 Rotation", 14, 86),
    60: ("Framing Blade 3 Rotation", 14, 85),
    61: ("Gobo Bounce", 75, 387),
    62: ("Barrel Pan", 51, 112),
    100: ("Fan Speed", 62, 349),
}

# Split votes and thin samples. The rule of the house: an ambiguous value is
# recorded as candidates, never resolved by preference.
INCERTAINS_CANAL = {
    3: "Barrel Roll / Barrel Tilt / declination of the drum (n=164, 28 %)",
    4: "Barrel Pan / rotation of the drum / head motor (n=225, 17 %)",
    24: "Smoke / Fog, but 14 % of the names are Fan or Fan Speed (n=1780)",
    32: "Gobo Bounce — rotating or static, 12 samples in the whole library",
    47: "Lime 33 % / Cyan 24 % / Lemon 6 % — and 48 is Lime at 94 %",
    50: "Cyan 71 % / Royal Blue 25 %, n=63",
    52: "Pink — 11 samples",
}
INCERTAINS_PRESET = {
    5: "Dimmer Simple — off / dimmer simple / blackout / on, n=593",
    13: "Iris Open/Closed — the two names split 13/12 %",
    16: "Zoom In/Out — in and out split 8/8 %, direction unresolved",
    25: "Focus Simple — read from the channel (78 % under Focus), not the names",
    30: "Speed Simple — max speed / speed simple / default",
    57: "Framing blade rotations 57-60 come out 1, 2, 4, 3 — against the",
    58: "  order of 53-56, which is 1, 2, 3, 4. n is 78-105 with an 11-15 %",
    59: "  plurality, so the index of each is a candidate, not a reading.",
    60: "  Bottom/left/right disagree with the numbered names.",
}

# Name → number, for descriptions written by hand. Case-insensitive.
NUM_CANAL = {nom.lower(): n for n, (nom, _, _) in TYPE_CANAL.items()}
NUM_PRESET = {nom.lower(): n for n, (nom, _, _) in TYPE_PRESET.items()}


def num_canal(nom):
    """A channel type by name or by number. Refuses anything else — an unknown
    type would be written into the file and silently mean something."""
    return _num(nom, NUM_CANAL, TYPE_CANAL, "canal")


def num_preset(nom):
    return _num(nom, NUM_PRESET, TYPE_PRESET, "preset")


def _num(nom, index, table, quoi):
    if isinstance(nom, int) or (isinstance(nom, str) and nom.isdigit()):
        n = int(nom)
        if n not in table:
            raise ValueError(f"type de {quoi} {n} absent de la bibliothèque "
                             f"locale — refusé faute de savoir ce qu'il vaut")
        return n
    n = index.get(str(nom).strip().lower())
    if n is None:
        proches = [x for x in index if str(nom).strip().lower() in x]
        raise ValueError(f"type de {quoi} inconnu : {nom!r}"
                         + (f" (proche : {', '.join(sorted(proches)[:4])})"
                            if proches else ""))
    return n


def _auto_test_crypto():
    """The cipher's two properties, without any file: involution, and the NUL."""
    clair = b'<?xml version="1.0"?><A B="1"/>'
    assert dechiffre(chiffre(clair)) == clair
    # A NUL does not survive — which is why the codec works on XML only.
    assert dechiffre(chiffre(b"\x00")) != b"\x00"
    # Every stream starts at offset 0: a two-byte block is not two one-byte
    # blocks, and the keystream cache must not have quietly made it so.
    assert transforme(b"ab") != transforme(b"a") + transforme(b"b")
    assert transforme(b"ab")[:1] == transforme(b"a")
    # A different key is a different stream, and the cache keeps them apart.
    assert transforme(b"hello", "autre") != transforme(b"hello")
    assert dechiffre(chiffre(clair, "autre"), "autre") == clair
    for cle in ("", None, b""):
        try:
            transforme(b"x", cle)
            raise AssertionError(f"clé {cle!r} acceptée")
        except ValueError:
            pass


# --- Generator --------------------------------------------------------------
# A description is JSON, and small enough to write by hand:
#
#   {"name": "Acme Par 18", "brand": "Acme",
#    "modes": [{"name": "3ch", "channels": [
#        {"type": "Red"}, {"type": "Green"}, {"type": "Blue"}]}]}
#
# Everything else — UIDs, counters, indexes, the physical block — is filled in
# from the shape the library's own `_Generic` fixtures have, because a profile
# the software refuses is worth nothing. A channel may carry `name`, `icon` and
# `presets`; a preset carries `type`, `name`, `dmx: [début, fin]`, and
# optionally `default` (the DMX value the preset opens on), `defaut: true` (the
# one preset of the channel the software starts on) and `icon`.
#
# `properties` passes values straight into SSLPROPERTIES, overriding the
# defaults below — that is where beam angle, size, weight and the 3D object go.

# The physical block: the 34 attributes carried by 100 % of the library's
# SSLPROPERTIES, in that order, plus SSLBEAMOPENING2 (99 %). The values are the
# generic LED panel's — 15 x 2 x 15 cm, LED at 7000 K, a 1° beam — so that a
# generated profile differs from `_GENERIC/RGB.ssl2` in its identity and
# nothing else. `properties` in the description overrides any of them, and is
# also the only way to add SSLCATEGORY (8 %).
DEFAUTS_PROPRIETES = {
    "SSLBRAND": "", "SSLCREATOR": "", "SSLRDMFIXTURENAME": "",
    "SSLRDMMANUFACTURERNAME": "", "SSLFIXTFAMILY": "1", "SSLFIXTTYPE": "6",
    "SSLLAMPTYPE": "LED", "SSLLAMPTEMP": "7000", "SSLLAMPPOWER": "0",
    "SSLLAMPLUX": "0", "SSLLAMPLIFE": "-1", "SSLLAMPREF": "",
    "SSLBEAMTYPE": "0", "SSLBEAMOPENING": "1", "SSLBEAMOPENING2": "60",
    "SSLAMPLIPAN": "0", "SSLAMPLITILT": "0", "SSLPANCENTER": "127",
    "SSLTILTCENTER": "127", "SSLINVPAN": "0", "SSLINVTILT": "0",
    "SSLTIMEPAN": "0", "SSLTIMETILT": "0", "SSLSIZEX": "15", "SSLSIZEY": "2",
    "SSLSIZEZ": "15", "SSLWEIGHT": "0", "SSLRDMMANUFACTURERID": "0",
    "SSLRDMFIXTUREID": "0",
    "SSLICON": "ScanLibrary/icon/Fixtures/_Generic/Panel.ico",
    "SSL3DOBJECTFILE": "Panels/Panel.x1",
    "SSL3DOBJECTFILE2": ":/FIXTURES/PANELS/PANEL",
    "SSLCOLOR": "255", "SSLTYPEDRAW": "1",
}

# The owner of every profile in the vendor's library is one constant UUID —
# their cloud account. A profile generated here is not theirs, so it gets its
# own, derived from the description like every other UID. The prediction that
# went with the first software test: an unknown owner means "not from the
# cloud", not "invalid". See docs/ssl2-format.md.
MAX_CANAUX = 512


def _uid(graine, *parties):
    return hashlib.sha256(("/".join([graine, *map(str, parties)]))
                          .encode("utf-8")).hexdigest()


def _uid_element(graine, index, *parties):
    """`8hex-8hex-index`, the shape SSLMODEUID/SSLCHANNELUID/SSLPRESETUID take."""
    h = _uid(graine, *parties)
    return f"{h[:8]}-{h[8:16]}-{index}"


def _uid_uuid(graine, *parties):
    """A plain UUID, the shape SSLLCOWNERUID and SSLPRESETDEFAULTUID take."""
    h = _uid(graine, *parties)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _uid_long(graine, *parties):
    """SSLLCUID's shape: a UUID, then a dash, then 8 more hex."""
    return f"{_uid_uuid(graine, *parties)}-{_uid(graine, *parties)[32:40]}"


def genere(description):
    """A description → the Element tree of a profile. Deterministic: the same
    description gives the same bytes, which is what makes a diff meaningful."""
    nom = _texte(description, "name")
    marque = _texte(description, "brand")
    modes = description.get("modes")
    if not isinstance(modes, list) or not modes:
        raise ValueError("description : 'modes' doit être une liste non vide")
    graine = f"{marque}\n{nom}"

    props = dict(DEFAUTS_PROPRIETES)
    props["SSLBRAND"] = echappe(depuis_utf8(marque))
    supplement = description.get("properties") or {}
    inconnus = set(supplement) - set(props) - {"SSLCATEGORY"}
    if inconnus:
        raise ValueError(f"properties : attribut(s) inconnu(s) "
                         f"{', '.join(sorted(inconnus))}")
    for cle, valeur in supplement.items():
        props[cle] = echappe(depuis_utf8(str(valeur)))

    el_modes = Element("SSLMODES", {"SSLNBMODE": str(len(modes))})
    for i, mode in enumerate(modes):
        el_modes.enfants.append(_genere_mode(graine, i, mode))
    el_modes.vide = False

    biblio = Element("SSLLIBRARY", {
        "SSLNAME": echappe(depuis_utf8(nom)),
        "SSLLCUID": _uid_long(graine, "library"),
        "SSLLCOWNERUID": _uid_uuid(graine, "owner"),
    }, [Element("SSLPROPERTIES", props, vide=True), el_modes], vide=False)
    return Element("DLMFILE", {"VERSION": "3", "TYPE": "SSLLIBRARY"},
                   [biblio], vide=False)


def _genere_mode(graine, index, mode):
    canaux = mode.get("channels")
    if not isinstance(canaux, list) or not canaux:
        raise ValueError(f"mode {index} : 'channels' doit être une liste non vide")
    if len(canaux) > MAX_CANAUX:
        raise ValueError(f"mode {index} : {len(canaux)} canaux, maximum "
                         f"{MAX_CANAUX} (un univers DMX)")
    graine = f"{graine}\nmode{index}"
    el = Element("SSLMODE", {
        "SSLMODEUID": _uid_element(graine, index, "mode"),
        "SSLMODEINDEX": str(index),
        "SSLMODENAME": echappe(depuis_utf8(str(mode.get("name", "")))),
        "SSLNBCHANNEL": str(len(canaux)),
    }, vide=False)
    vus = {}          # type → how many of that type came before, for TYPEINDEX
    for i, canal in enumerate(canaux):
        el.enfants.append(_genere_canal(graine, i, canal, vus))
    return el


def _genere_canal(graine, index, canal, vus):
    if not isinstance(canal, dict) or "type" not in canal:
        raise ValueError(f"canal {index} : il faut au moins un 'type'")
    type_ = num_canal(canal["type"])
    graine = f"{graine}\ncanal{index}"
    el = Element("SSLCHANNEL", {
        "SSLCHANNELUID": _uid_element(graine, index, "canal"),
        "SSLCHANNELTYPE": str(type_),
        "SSLCHANNELNAME": echappe(depuis_utf8(
            str(canal.get("name") or TYPE_CANAL[type_][0]))),
        "SSLCHANNELICON": echappe(depuis_utf8(str(canal.get("icon", "")))),
        # 16-bit pairs are readable but not generated: a fine channel needs
        # MSB/LSB and SSLCHANNEL16BITSINDEX wired both ways, and nothing here
        # has been measured on the software yet. docs/ssl2-format.md, "Limites".
        "SSLCHANNELMSB": "0", "SSLCHANNELLSB": "0",
        "SSLCHANNEL2PRESETS": "0", "SSLCHANNEL2PRESETSINDEX": "-1",
        "SSLCHANNELTYPEINDEX": str(vus.get(type_, 0)),
        "SSLCHANNEL16BITSINDEX": "-1",
    }, vide=False)
    vus[type_] = vus.get(type_, 0) + 1
    el.enfants.append(_genere_presets(graine, canal.get("presets") or []))
    return el


def _genere_presets(graine, presets):
    el = Element("SSLPRESETS", {"SSLNBPRESET": str(len(presets))}, vide=True)
    if not presets:
        return el                      # `<SSLPRESETS SSLNBPRESET="0" />`
    # A range UID appears exactly when the channel has presets — measured on
    # 456 260 of the library's 456 266 non-empty SSLPRESETS.
    uid = _uid_element(graine, 0, "plage")
    el.attrs["SSLPRESETRANGEUID"] = uid
    el.attrs["SSLPRESETRANGETEMPLATEUID"] = uid
    el.vide = False
    defaut = _preset_par_defaut(presets)
    occupe = {}
    for i, preset in enumerate(presets):
        el.enfants.append(_genere_preset(graine, i, preset, i == defaut, occupe))
    return el


def _preset_par_defaut(presets):
    """Exactly one preset per channel carries SSLPRESETDEFAULTPRESET="1" in the
    library. The description may say which; otherwise it is the first."""
    marques = [i for i, p in enumerate(presets) if p.get("defaut")]
    if len(marques) > 1:
        raise ValueError(f"presets : {len(marques)} marqués 'defaut', un seul "
                         f"peut l'être")
    return marques[0] if marques else 0


def _genere_preset(graine, index, preset, est_defaut, occupe):
    if not isinstance(preset, dict) or "type" not in preset:
        raise ValueError(f"preset {index} : il faut au moins un 'type'")
    type_ = num_preset(preset["type"])
    debut, fin = _plage(preset, index, occupe)
    par_defaut = preset.get("default", debut)
    if not 0 <= int(par_defaut) <= 255:
        raise ValueError(f"preset {index} : 'default' {par_defaut} hors 0-255")
    if not debut <= int(par_defaut) <= fin:
        raise ValueError(f"preset {index} : 'default' {par_defaut} hors de sa "
                         f"propre plage {debut}-{fin}")
    uid = _uid_element(graine, index, "preset")
    return Element("SSLPRESET", {
        "SSLPRESETUID": uid, "SSLPRESETTEMPLATEUID": uid,
        "SSLPRESETDEFAULTUID": _uid_uuid(graine, "preset", index),
        "SSLPRESETTYPE": str(type_),
        "SSLPRESETNAME": echappe(depuis_utf8(
            str(preset.get("name") or TYPE_PRESET[type_][0]))),
        "SSLPRESETICON": echappe(depuis_utf8(str(preset.get("icon", "NoIcon")))),
        "SSLPRESETDMXSTART": str(debut), "SSLPRESETDMXEND": str(fin),
        "SSLPRESETDMXDEFAULT": str(int(par_defaut)),
        "SSLPRESETDEFAULTPRESET": "1" if est_defaut else "0",
        # SHOWDIMMER and TARGET are written at the value 65 % / 95 % of the
        # library uses. Neither is understood, so neither is offered as an
        # option: an unmeasured knob is worse than no knob.
        "SSLPRESETSHOWDIMMER": "0",
        "SSLPRESETID": "", "SSLPRESETTARGET": "-1",
    }, vide=True)


def _plage(preset, index, occupe):
    plage = preset.get("dmx", [0, 255])
    if (not isinstance(plage, (list, tuple)) or len(plage) != 2
            or not all(isinstance(v, int) for v in plage)):
        raise ValueError(f"preset {index} : 'dmx' doit être [début, fin], "
                         f"deux entiers — reçu {plage!r}")
    debut, fin = plage
    if not 0 <= debut <= fin <= 255:
        raise ValueError(f"preset {index} : plage DMX {debut}-{fin} invalide "
                         f"(attendu 0 <= début <= fin <= 255)")
    for valeur in range(debut, fin + 1):
        if valeur in occupe:
            raise ValueError(f"preset {index} : la valeur DMX {valeur} est "
                             f"déjà prise par le preset {occupe[valeur]}")
        occupe[valeur] = index
    return debut, fin


def _texte(description, cle):
    valeur = description.get(cle)
    if not isinstance(valeur, str) or not valeur.strip():
        raise ValueError(f"description : '{cle}' manquant ou vide")
    return valeur


def compare(a, b, chemin="", sortie=None):
    """Structural diff of two profiles: what differs, where, and how.

    Not a text diff — the point is to say "this attribute is missing" or "this
    element has three children where the other has two", which is what a
    bisection against a template needs to hear.
    """
    sortie = [] if sortie is None else sortie
    ou = f"{chemin}/{a.tag}"
    if a.tag != b.tag:
        sortie.append(f"{chemin}: <{a.tag}> contre <{b.tag}>")
        return sortie
    for nom in a.attrs:
        if nom not in b.attrs:
            sortie.append(f"{ou}: {nom} seulement à gauche ({a.attrs[nom]!r})")
        elif a.attrs[nom] != b.attrs[nom]:
            sortie.append(f"{ou}: {nom} {a.attrs[nom]!r} contre {b.attrs[nom]!r}")
    for nom in b.attrs:
        if nom not in a.attrs:
            sortie.append(f"{ou}: {nom} seulement à droite ({b.attrs[nom]!r})")
    if list(a.attrs) != list(b.attrs) and set(a.attrs) == set(b.attrs):
        sortie.append(f"{ou}: mêmes attributs, ordre différent")
    if a.vide != b.vide:
        sortie.append(f"{ou}: écrite {'vide' if a.vide else 'ouverte'} contre "
                      f"{'vide' if b.vide else 'ouverte'}")
    if len(a.enfants) != len(b.enfants):
        sortie.append(f"{ou}: {len(a.enfants)} enfant(s) contre "
                      f"{len(b.enfants)}")
    for i, (ea, eb) in enumerate(zip(a.enfants, b.enfants)):
        compare(ea, eb, f"{ou}[{i}]", sortie)
    return sortie


def recalcule_enums(fichiers):
    """Recount both enums from a library. What `enums` compares the tables to.

    Returns {"canal": {n: (nom_dominant, part, total)}, "preset": ...} — the
    same shape as the embedded tables, so the diff is a dict comparison and
    not a story about one.
    """
    import collections
    votes = {"canal": collections.defaultdict(collections.Counter),
             "preset": collections.defaultdict(collections.Counter)}
    for chemin in fichiers:
        racine = charge(chemin)
        for e in racine.trouve("SSLCHANNEL"):
            votes["canal"][int(e.get("SSLCHANNELTYPE", -1))][
                _normalise(e.get("SSLCHANNELNAME", ""))] += 1
        for e in racine.trouve("SSLPRESET"):
            votes["preset"][int(e.get("SSLPRESETTYPE", -1))][
                _normalise(e.get("SSLPRESETNAME", ""))] += 1
    out = {}
    for quoi, par_type in votes.items():
        out[quoi] = {}
        for num, noms in par_type.items():
            nom, part = noms.most_common(1)[0]
            total = sum(noms.values())
            out[quoi][num] = (nom, round(100 * part / total), total)
    return out


_VARIANTES = re.compile(r"\(?\s*(Âµ|µ)\s*\)?")
_INDEX = re.compile(r"^\s*\d+\s*[.)]\s*")
_PONCTU = re.compile(r"[^a-z0-9+/&]+")


def _normalise(nom):
    """Fold the variants of one name: "1. Red", "Red (Âµ)" and "RED" are one
    vote for red, and counting them apart is what makes a 68 % look like 25 %."""
    nom = _VARIANTES.sub("", nom.replace("&amp;", "&"))
    return _PONCTU.sub(" ", _INDEX.sub("", nom).lower()).strip()


def compare_enums(fichiers):
    """Print the recomputed tables against the embedded ones.

    A number the library has and the table does not (or the reverse) is a
    failure: the table would then be silently incomplete, and the generator
    refuses what it cannot name. Counts and shares only *drift* — another
    Easy View version ships another library — so they are reported, not
    enforced.
    """
    mesure = recalcule_enums(fichiers)
    ecarts = 0
    for quoi, table in (("canal", TYPE_CANAL), ("preset", TYPE_PRESET)):
        vus = mesure[quoi]
        for num in sorted(set(table) | set(vus)):
            if num not in vus:
                print(f"{quoi} {num} : dans la table, absent de cette "
                      f"bibliothèque", file=sys.stderr)
                ecarts += 1
            elif num not in table:
                print(f"{quoi} {num} : dans cette bibliothèque, ABSENT DE LA "
                      f"TABLE ({vus[num][0]!r}, n={vus[num][2]})", file=sys.stderr)
                ecarts += 1
            else:
                nom, part, n = table[num]
                vnom, vpart, vn = vus[num]
                drapeau = " (incertain)" if num in (
                    INCERTAINS_CANAL if quoi == "canal" else INCERTAINS_PRESET
                ) else ""
                accord = "" if (part, n) == (vpart, vn) else \
                    f"   [table : {part} %, n={n}]"
                print(f"{quoi} {num:3} {nom:34}{drapeau} — vote {vnom!r} "
                      f"{vpart} %, n={vn}{accord}")
    print(f"{len(mesure['canal'])} types de canal, {len(mesure['preset'])} de "
          f"preset ; {ecarts} écart(s) de couverture", file=sys.stderr)
    return ecarts


def verifie(fichiers, bavard=False):
    """The oracle: decrypt → parse → write → encrypt, back to the same bytes.

    Both round trips at once, on real files, because they fail differently: a
    crypto bug moves every byte, a codec bug moves one attribute.
    """
    ok = echecs = 0
    for chemin in fichiers:
        try:
            with open(chemin, "rb") as flux:
                brut = flux.read()
            clair = dechiffre(brut)
            if not clair.lstrip()[:5].startswith(b"<?xml"):
                raise ValueError("déchiffré non-XML")
            racine = parse(clair, chemin)
            verifie_racine(racine, chemin)
            if write(racine) != clair:
                raise ValueError("parse→write non identique")
            if chiffre(clair) != brut:
                raise ValueError("chiffrement non identique")
        except (ValueError, OSError) as err:
            echecs += 1
            print(f"ÉCHEC {chemin} : {err}", file=sys.stderr)
        else:
            ok += 1
            if bavard:
                print(f"ok {chemin}")
    return ok, echecs


def _auto_test_generateur():
    """The generator, with no library at hand: counters, indexes, ranges, and
    the descriptions that must be refused rather than written out wrong."""
    rgb = {"name": "RGB", "brand": "_Generic",
           "modes": [{"channels": [{"type": "Red"}, {"type": "Green"},
                                   {"type": "Blue"}]}]}
    racine = genere(rgb)
    assert write(parse(write(racine))) == write(racine)   # generated re-parses
    assert genere(rgb) is not racine and write(genere(rgb)) == write(racine)
    mode = next(racine.trouve("SSLMODE"))
    canaux = list(racine.trouve("SSLCHANNEL"))
    assert mode["SSLNBCHANNEL"] == "3" == str(len(canaux))
    assert [c["SSLCHANNELTYPE"] for c in canaux] == ["25", "26", "27"]
    assert [c["SSLCHANNELNAME"] for c in canaux] == ["Red", "Green", "Blue"]
    assert [c["SSLCHANNELUID"].rsplit("-", 1)[1] for c in canaux] == ["0", "1", "2"]

    riche = {"name": "Test", "brand": "Nous", "modes": [{"name": "8ch",
        "channels": [
            {"type": "Dimmer"},
            {"type": "Shutter / Strobe", "name": "Shutter", "presets": [
                {"type": "Shutter Closed", "dmx": [0, 7]},
                {"type": "Shutter Open", "dmx": [8, 15], "defaut": True},
                {"type": "Strobe", "dmx": [16, 255], "default": 128}]},
            {"type": "Color Wheel", "presets": [
                {"type": "Color", "name": "White", "dmx": [0, 9]},
                {"type": "Color", "name": "Red", "dmx": [10, 19]}]},
            {"type": "Red"}, {"type": "Green"}, {"type": "Blue"},
            {"type": "Red", "name": "Red 2"}]}]}
    r2 = genere(riche)
    presets_par_canal = [(c["SSLCHANNELTYPE"],
                          [p for p in c.trouve("SSLPRESET")])
                         for c in r2.trouve("SSLCHANNEL")]
    for el in r2.trouve("SSLPRESETS"):
        assert el["SSLNBPRESET"] == str(len(el.enfants)), el.attrs
        assert ("SSLPRESETRANGEUID" in el.attrs) == bool(el.enfants)
    strobe = presets_par_canal[1][1]
    assert [(p["SSLPRESETDMXSTART"], p["SSLPRESETDMXEND"]) for p in strobe] == \
        [("0", "7"), ("8", "15"), ("16", "255")]
    assert [p["SSLPRESETDEFAULTPRESET"] for p in strobe] == ["0", "1", "0"]
    assert [p["SSLPRESETDMXDEFAULT"] for p in strobe] == ["0", "8", "128"]
    assert [p["SSLPRESETUID"].rsplit("-", 1)[1] for p in strobe] == ["0", "1", "2"]
    # SSLCHANNELTYPEINDEX counts channels of the same type, not all channels.
    types = [(c["SSLCHANNELTYPE"], c["SSLCHANNELTYPEINDEX"])
             for c in r2.trouve("SSLCHANNEL")]
    assert types == [("7", "0"), ("15", "0"), ("5", "0"), ("25", "0"),
                     ("26", "0"), ("27", "0"), ("25", "1")], types
    assert next(r2.trouve("SSLMODE"))["SSLNBCHANNEL"] == "7"
    # A name with an accent goes out as UTF-8, and an & does not break the XML.
    accent = genere({"name": "Té & Co", "brand": "Ω", "modes": [
        {"channels": [{"type": "Red", "name": "Rouge é"}]}]})
    assert b"T\xc3\xa9 &amp; Co" in write(accent)
    assert parse(write(accent)) is not None

    refus = [
        ({"brand": "b", "modes": []}, "name"),
        ({"name": "n", "brand": "b", "modes": []}, "modes"),
        ({"name": "n", "brand": "b", "modes": [{"channels": []}]}, "channels"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [{"type": "Nope"}]}]},
         "inconnu"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [
                {"type": "Color", "dmx": [0, 10]},
                {"type": "Color", "dmx": [10, 20]}]}]}]}, "déjà prise"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [{"type": "Color", "dmx": [10, 5]}]}]}]},
         "invalide"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [
                {"type": "Color", "dmx": [0, 5], "defaut": True},
                {"type": "Color", "dmx": [6, 9], "defaut": True}]}]}]}, "un seul"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [
                {"type": "Color", "dmx": [0, 5], "default": 200}]}]}]},
         "hors de sa propre plage"),
        ({"name": "n", "brand": "b", "properties": {"SSLNOPE": "1"},
          "modes": [{"channels": [{"type": "Red"}]}]}, "inconnu"),
        ({"name": "n", "brand": "b", "modes": [{"channels":
            [{"type": "Red"}] * (MAX_CANAUX + 1)}]}, "maximum"),
    ]
    for description, attendu in refus:
        try:
            genere(description)
        except ValueError as err:
            assert attendu in str(err), f"{attendu!r} absent de {err}"
        else:
            raise AssertionError(f"description acceptée : {attendu}")


def _auto_test(echantillon=400):
    """The self-check `make check` runs: the crypto with no files at all, then
    the full round trip on a slice of the local library.

    A slice, not the whole thing: `ssl2.py verify` is the exhaustive pass and
    takes minutes. The slice is the head of a sorted list, so it is the same
    files every run — and the summary says how many, because a check that says
    "ok" without a number is the kind this repository does not keep.
    """
    _auto_test_crypto()
    _auto_test_generateur()
    fichiers = fichiers_biblio()
    if not fichiers:
        print("ssl2: crypto et générateur ok (hors fichiers)", file=sys.stderr)
        return pas_de_biblio()
    ok, echecs = verifie(fichiers[:echantillon])
    if echecs:
        raise SystemExit(f"ssl2: {echecs} échec(s) sur {ok + echecs}")
    print(f"self-check ok: générateur, puis aller-retour octet-près sur {ok} fichiers "
          f"(sur {len(fichiers)} — `ssl2.py verify` les fait tous)",
          file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cle", default=CLE_DEFAUT, help="clé AraCrypt")
    sous = ap.add_subparsers(dest="commande")
    for nom, aide in (("decrypt", "un .ssl2 → son XML"),
                      ("encrypt", "un XML → un .ssl2"),
                      ("dump", "le XML déchiffré sur la sortie standard")):
        s = sous.add_parser(nom, help=aide)
        s.add_argument("entree")
        if nom != "dump":
            s.add_argument("sortie", nargs="?")
    s = sous.add_parser("verify", help="aller-retour sur toute la bibliothèque")
    s.add_argument("--bavard", action="store_true")
    s.add_argument("fichiers", nargs="*")
    s = sous.add_parser("enums", help="recalcule les tables et les compare")
    s.add_argument("fichiers", nargs="*")
    s = sous.add_parser("gen", help="une description JSON → un .ssl2")
    s.add_argument("description")
    s.add_argument("sortie", nargs="?")
    s.add_argument("--xml", action="store_true", help="écrire le XML en clair")
    s = sous.add_parser("diff", help="diff structurel entre deux profils")
    s.add_argument("gauche")
    s.add_argument("droite")
    args = ap.parse_args(argv)

    if args.commande in ("decrypt", "dump"):
        clair = charge_xml(args.entree, args.cle)
        if args.commande == "dump":
            sys.stdout.buffer.write(clair)
            return 0
        return _ecrit(args.sortie or _suffixe(args.entree, ".xml"), clair)
    if args.commande == "encrypt":
        with open(args.entree, "rb") as flux:
            clair = flux.read()
        if not clair.lstrip()[:5].startswith(b"<?xml"):
            raise SystemExit(f"{args.entree} : ce n'est pas du XML")
        return _ecrit(args.sortie or _suffixe(args.entree, ".ssl2"),
                      chiffre(clair, args.cle))
    if args.commande == "verify":
        fichiers = args.fichiers or fichiers_biblio()
        if not fichiers:
            pas_de_biblio()
            return 3
        ok, echecs = verifie(fichiers, args.bavard)
        print(f"{ok}/{ok + echecs} aller-retours octet-près", file=sys.stderr)
        return 1 if echecs else 0
    if args.commande == "gen":
        with open(args.description, encoding="utf-8") as flux:
            xml = write(genere(json.load(flux)))
        cible = args.sortie or _suffixe(args.description,
                                        ".xml" if args.xml else ".ssl2")
        return _ecrit(cible, xml if args.xml else chiffre(xml, args.cle))
    if args.commande == "diff":
        ecarts = compare(charge(args.gauche, args.cle),
                         charge(args.droite, args.cle))
        for ligne in ecarts:
            print(ligne)
        print(f"{len(ecarts)} écart(s)", file=sys.stderr)
        return 0
    if args.commande == "enums":
        fichiers = args.fichiers or fichiers_biblio()
        if not fichiers:
            pas_de_biblio()
            return 3
        return 1 if compare_enums(fichiers) else 0
    _auto_test()
    return 0


def _suffixe(chemin, ext):
    base = chemin[:-5] if chemin.endswith(".ssl2") else chemin
    base = base[:-4] if base.endswith(".xml") else base
    return base + ext


def _ecrit(chemin, data):
    """Never over an existing file — the repository's write rule."""
    with open(chemin, "xb") as flux:
        flux.write(data)
    print(f"écrit {chemin} ({len(data)} octets)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as err:      # a refusal is a message, not a traceback
        raise SystemExit(str(err))
