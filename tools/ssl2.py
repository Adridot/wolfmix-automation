#!/usr/bin/env python3
"""Read, write and generate Nicolaudie `.ssl2` fixture profiles.

Module group: Resources. Reference: docs/tools.md.

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

from __future__ import annotations
from os import PathLike
from collections.abc import Iterable, Iterator, Sequence
import argparse
import copy
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


def transforme(data: bytes, key: str = CLE_DEFAUT) -> bytes:
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


class VersionNonPriseEnCharge(ValueError):
    """A real .ssl2 of a version this codec does not decode. Not a failure of
    the file, and not the same thing as "this is not an .ssl2" — an older
    library is full of these, and calling them corrupt would be a lie."""


def classe(clair: bytes) -> str | None:
    """What a decrypted payload is: "v3", "v2", or None if it is not SSL2.

    The prolog cannot carry this: `VERSION="2"` files have no `<?xml` at all,
    and three V3 files write one with no encoding. `<DLMFILE` is the marker.
    """
    tete = clair[:400]
    if b"<DLMFILE" not in tete:
        return None
    version = re.search(rb'<DLMFILE[^>]*VERSION="(\d+)"', tete)
    return f"v{version.group(1).decode()}" if version else "v?"


def charge_xml(chemin: str | PathLike[str], key: str = CLE_DEFAUT) -> bytes:
    """Decrypt a file, and say precisely what it is when we cannot read it."""
    with open(chemin, "rb") as flux:
        clair = dechiffre(flux.read(), key)
    quoi = classe(clair)
    if quoi is None:
        raise ValueError(f"{chemin} : le contenu déchiffré ne contient pas "
                         f"<DLMFILE — ce n'est pas un .ssl2 (ou la clé est "
                         f"fausse) ; il commence par {clair[:24]!r}")
    if quoi != "v3":
        raise VersionNonPriseEnCharge(
            f"{chemin} : SSL2 {quoi} (TYPE=SSLLIBRARY2008 sur cette version), "
            f"non décodé ici — seul VERSION=\"3\" l'est. Le fichier est "
            f"valide, c'est le codec qui s'arrête")
    return clair


# --- Local library ----------------------------------------------------------
# The vendor's own ScanLibrary, on this machine. It is the round-trip oracle,
# exactly as corpus/ is for the .wpj tools: read, never copied into the tree.
BIBLIO_ENV = "SSL2_LIBRARY"
BIBLIO_DEFAUT = "/Applications/Easy View/ScanLibrary"
ABSTENTION = "ABSTAINED"


def fichiers_biblio() -> list[str]:
    racine = os.environ.get(BIBLIO_ENV) or BIBLIO_DEFAUT
    return sorted(glob.glob(os.path.join(racine, "**", "*.ssl2"), recursive=True))


def pas_de_biblio() -> None:
    racine = os.environ.get(BIBLIO_ENV) or BIBLIO_DEFAUT
    print(f"ssl2: {ABSTENTION} — aucune bibliothèque dans {racine}, rien n'a "
          f"été vérifié (voir docs/ssl2-format.md)", file=sys.stderr)


# --- XML codec -------------------------------------------------------------
# What every library agrees on: no text content, no comment, no CDATA;
# attributes always double-quoted and separated by one space; an open tag ends
# `>`, an empty one ` />`.
#
# What they do NOT agree on, and the correction that cost the most here: the
# Easy View 3 library is a *normalised export* — one prolog, and not one byte
# between two tags in 25 610 files. Read that as a property of the format and
# you write a parser that refuses a third of an older library: the one shipped
# with EasyViewConnect indents its XML with newlines (5 668 files) and writes
# `<?xml version="1.0"?>` with no encoding (3 files). Uniformity over thousands
# of samples is evidence about the corpus, not the format — AGENTS.md, trap 1.
#
# So the prolog and every gap between tags are *recorded* and re-emitted
# verbatim, exactly as the unknown-bytes rule requires elsewhere in this tree.
PROLOG = '<?xml version="1.0" encoding="UTF-8"?>'   # what the generator emits
# The optional BOM is one file in 33 000 — kept because dropping it would be a
# silent edit, and this codec does not make those.
_PROLOG = re.compile(r"(?:\xef\xbb\xbf)?<\?xml[^>]*\?>")
_BALISE = re.compile(r'<(/?)([A-Z0-9]+)((?:\s+[A-Z0-9]+="[^"]*")*)(\s*)(/?)>')
_ATTR = re.compile(r'\s+([A-Z0-9]+)="([^"]*)"')

# Bytes travel as latin-1 text: every byte round-trips, and a name the vendor
# stored as mojibake stays the bytes it was rather than being "fixed" on the
# way through. `vers_utf8`/`depuis_utf8` are the two doors in and out.
def depuis_utf8(s: str) -> str:
    return s.encode("utf-8").decode("latin-1")


def vers_utf8(s: str) -> str:
    return s.encode("latin-1").decode("utf-8", "replace")


class Element:
    """One XML element, faithful to the stream: attribute order included."""

    __slots__ = ("tag", "attrs", "enfants", "vide", "avant", "fin", "blancfin",
                 "prologue", "queue")

    def __init__(
        self,
        tag: str,
        attrs: dict[str, str] | None = None,
        enfants: list[Element] | None = None,
        vide: bool | None = None,
    ) -> None:
        self.tag = tag
        # Whitespace as it was found: `avant` precedes this element's `<`,
        # `fin` precedes its `</`. On the root, `prologue` and `queue` hold the
        # declaration and whatever trails the document. All empty by default,
        # so a generated tree emits the normalised form.
        self.avant = self.fin = self.queue = ""
        self.prologue = PROLOG
        self.attrs = dict(attrs or {})      # insertion order = stream order
        self.enfants = list(enfants or [])
        # `vide` is how it was written, not whether it has children: the corpus
        # has both `<SSLPRESETS ... />` and `<SSLPRESETS ...></SSLPRESETS>`,
        # and re-emitting one as the other is not a byte-identical round trip.
        self.vide = not self.enfants if vide is None else vide
        # The space before `>` / `/>`. Easy View 3 always writes ` />` and
        # never ` >`; the older library writes `/>` with no space at all. It is
        # one byte and it is the difference between a round trip and a diff.
        self.blancfin = " " if self.vide else ""

    def __getitem__(self, nom: str) -> str:
        return self.attrs[nom]

    def get(self, nom: str, defaut: str | int | None = None) -> str | int | None:
        return self.attrs.get(nom, defaut)

    def trouve(self, tag: str) -> Iterator[Element]:
        """Every descendant with this tag, in document order."""
        for e in self.enfants:
            if e.tag == tag:
                yield e
            yield from e.trouve(tag)

    def __repr__(self) -> str:
        return f"<{self.tag} {len(self.attrs)} attrs, {len(self.enfants)} enfants>"


def parse(xml: bytes, source: str = '<xml>') -> Element:
    """XML bytes → Element tree. Raises rather than reading a file partly."""
    if isinstance(xml, bytes):
        xml = xml.decode("latin-1")
    tete = _PROLOG.match(xml)
    if not tete:
        raise ValueError(f"{source} : prologue inattendu {xml[:40]!r}")
    prologue = tete.group(0)
    pos, pile, racine = tete.end(), [], None
    for m in _BALISE.finditer(xml, pos):
        blanc = xml[pos:m.start()]
        if blanc.strip():
            raise ValueError(f"{source} : contenu hors balise à l'offset "
                             f"{pos} : {blanc[:40]!r}")
        pos = m.end()
        ferme, tag, corps, blancfin, vide = m.groups()
        if ferme:
            if not pile or pile[-1].tag != tag:
                raise ValueError(f"{source} : </{tag}> ferme "
                                 f"{pile[-1].tag if pile else 'rien'}")
            pile.pop().fin = blanc
            continue
        e = Element(tag, _ATTR.findall(corps), vide=bool(vide))
        e.avant, e.blancfin = blanc, blancfin
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
    if xml[pos:].strip():
        raise ValueError(f"{source} : queue non balisée {xml[pos:][:40]!r}")
    if pile:
        raise ValueError(f"{source} : <{pile[-1].tag}> jamais fermée")
    if racine is None:
        raise ValueError(f"{source} : document vide")
    racine.prologue, racine.queue = prologue, xml[pos:]
    return racine


def write(racine: Element) -> bytes:
    """Element tree → XML bytes. Deterministic: no option, no choice."""
    morceaux = [racine.prologue]

    def emets(e):
        morceaux.append(e.avant + f"<{e.tag}")
        for nom, valeur in e.attrs.items():
            morceaux.append(f' {nom}="{valeur}"')
        if e.vide:
            morceaux.append(e.blancfin + "/>")
            if e.enfants:
                raise ValueError(f"<{e.tag}> marquée vide mais a des enfants")
            return
        morceaux.append(e.blancfin + ">")
        for enfant in e.enfants:
            emets(enfant)
        morceaux.append(f"{e.fin}</{e.tag}>")

    emets(racine)
    morceaux.append(racine.queue)
    return "".join(morceaux).encode("latin-1")


def charge(chemin: str | PathLike[str], key: str = CLE_DEFAUT) -> Element:
    """A `.ssl2` on disk → the parsed tree, root checked."""
    racine = parse(charge_xml(chemin, key), chemin)
    verifie_racine(racine, chemin)
    return racine


def verifie_racine(racine: Element, source: str = '<xml>') -> Element:
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


def echappe(s: str) -> str:
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

# --- SSLPRESETTARGET -------------------------------------------------------
# The index, **within the mode**, of the channel that holds the physical object
# the preset acts on — the wheel a rotation turns, the prism a rotation index
# steps — and `-1` when the preset acts on its own channel's object or on none.
#
# Derived, not assumed. `ssl2.py enums` recomputes both halves of the reading:
#
#   1. Which preset types point at all. 40 of the 63 types in the library write
#      `-1` on **100 %** of their presets (Shutter Open, Strobe, Iris, Colour…).
#      The rest split, and a type is listed below only when a majority of its
#      presets point (>= 50 %) *and* the channel type they point at is settled
#      (>= 80 % of the pointing ones). Preset 7 (Gobo) fails the first test —
#      it points 1 % of the time; preset 28 (Speed) fails the second — its
#      target is Pan 39 %, a generic channel 24 %, a macro 21 %, because what a
#      speed governs is not a property of the preset type. Both are left out
#      rather than guessed at.
#   2. *Which* channel of that type, when a fixture has two gobo wheels. The
#      rule: the preset's own channel if it is already of the target type,
#      otherwise the channel of the target type with the **same**
#      `SSLCHANNELTYPEINDEX` as the channel carrying the preset — the second
#      gobo-rotation channel drives the second wheel — falling back to the
#      first channel of that type.
#
# That rule reproduces the library's own value on 97.4 % of 1 981 368 presets;
# `enums` prints the residue per type. It is what the generator writes when a
# description says nothing, and `target` in the description overrides it.
CIBLE_PRESET = {
    3: 5,     # Color Wheel Rotation   → Color Wheel
    8: 8,     # Gobo Rotation          → Gobo Wheel
    9: 8,     # Rotation Index         → Gobo Wheel
    10: 8,    # Gobo Shake             → Gobo Wheel
    11: 8,    # Gobo Wheel Rotation    → Gobo Wheel
    29: 1,    # Speed Tracking         → Pan
    32: 19,   # Prism Rotation         → Prism
    33: 19,   # Prism Rotation Index   → Prism
    45: 5,    # Color Wheel Index      → Color Wheel
    51: 33,   # Framing Rotation       → Framing Rotation
    53: 35, 54: 35, 55: 35, 56: 35,        # Framing Blade 1-4 → Framing Blade
    57: 34, 58: 34, 59: 34, 60: 34,        # …Rotation → Framing Blade Rotation
    61: 8,    # Gobo Bounce            → Gobo Wheel
}

# --- The five optional preset attributes -----------------------------------
# `(LEVELMIN, LEVELMAX, PARAMMIN, PARAMMAX, COLOR)`; `None` = the library does
# not write that attribute for that preset type, so neither does the generator.
#
# Whether an attribute is written at all is a property of the **preset type**,
# and the distribution says so without a threshold having to be chosen: over
# the 315 (type, attribute) cells, every one is either <= 21 % present or
# >= 94 % present. Nothing lands in the 73-point gap, so the cut below is not a
# tuning knob. What the *value* is, is a second question with a much weaker
# answer for some types, and `enums` prints that share per cell.
#
# Two readings worth keeping in mind, both of which cost a wrong guess:
#
#   `LEVELMIN`/`LEVELMAX` are **not** the preset's DMX range. They are 0 and
#   255 on 21 679 of 21 679 gobo presets whatever the range those presets cover
#   — a level scale of its own, in its own units.
#
#   `SSLPRESETCOLOR` is **0xBBGGRR**, not 0xRRGGBB: the library's "Red" presets
#   carry 255 and its "Blue" ones 16 711 680. `_couleur` takes `"#rrggbb"` and
#   does the swap, which is why a description should prefer the string form.
DEFAUTS_PRESET = {
      0: ("0", "255", "0", "100", None),          # No Function, n=939438
      1: (None, None, None, None, "16777215"),    # Color, n=258783 (10 %)
      2: (None, None, None, None, "255"),         # Color Combination 2, n=50155
      3: ("0", "255", "0", "100", None),          # Color Wheel Rotation, n=16975
      4: (None, None, "0", "100", "16777215"),    # Dimmer, n=64216
      5: (None, None, "0", None, "16777215"),     # Dimmer Simple, n=590
      6: ("0", "255", "0", "100", None),          # Dimmer Pulse, n=18899
      7: ("0", "255", "0", "100", "16777215"),    # Gobo, n=225493
      8: ("0", "255", "0", "100", None),          # Gobo Rotation, n=12447
      9: ("0", "255", "0", "720", None),          # Rotation Index, n=5293
     10: ("0", "255", "0", "100", None),          # Gobo Shake, n=3900
     11: ("0", "255", "0", "100", None),          # Gobo Wheel Rotation, n=19572
     12: (None, None, "100", "0", None),          # Iris, n=2038
     13: (None, None, "100", None, None),         # Iris Open/Closed, n=874
     14: ("0", "255", "0", "100", None),          # Iris Pulse, n=3793
     15: (None, None, "0", "16", None),           # Zoom, n=11502
     16: (None, None, "8", None, None),           # Zoom In/Out, n=1437
     17: (None, None, "0", None, None),           # Lamp On, n=2761
     18: (None, None, "0", None, None),           # Lamp Off, n=2647
     21: ("0", "255", "0", "250", None),          # Strobe, n=69503
     22: ("0", "255", "0", "250", None),          # Pulse Strobe, n=14566
     24: (None, None, "0", "100", None),          # Focus, n=6286
     25: (None, None, "50", None, None),          # Focus Simple, n=258
     26: (None, None, "0", "100", None),          # Frost, n=4359
     27: (None, None, "100", None, None),         # Frost Simple, n=831
     28: ("0", "255", "0", "100", None),          # Speed, n=35215
     29: ("0", "255", "0", "100", None),          # Speed Tracking, n=516
     30: ("0", "255", "50", None, None),          # Speed Simple, n=1686
     31: ("0", "255", "0", "100", None),          # Prism, n=20137
     32: ("0", "255", "0", "100", None),          # Prism Rotation, n=12547
     33: ("0", "255", "0", "720", None),          # Prism Rotation Index, n=6121
     34: (None, None, "1", "22", None),           # Color Temperature, n=7364
     35: (None, None, "7", None, None),           # Color Temperature Step, n=1607
     36: ("0", "255", "0", "100", None),          # Barrel Roll Rotation, n=383
     37: (None, None, "0", "100", None),          # Smoke, n=1763
     38: (None, None, "50", None, None),          # Smoke Simple, n=134
     39: ("0", "255", "0", "100", None),          # Frost Pulse, n=1014
     43: (None, None, None, None, "255"),         # Color Combination 3, n=9177
     44: (None, None, None, None, "255"),         # Color Combination 4, n=3177
     45: ("0", "255", "0", "720", None),          # Color Wheel Index, n=1054
     51: ("0", "255", "0", "100", None),          # Framing Rotation, n=297
     52: ("0", "255", "0", "720", None),          # Framing Rotation Index, n=119
     53: ("0", "255", "0", "100", None),          # Framing Blade 1, n=371
     54: ("0", "255", "0", "100", None),          # Framing Blade 2, n=355
     55: ("0", "255", "0", "100", None),          # Framing Blade 3, n=355
     56: ("0", "255", "0", "100", None),          # Framing Blade 4, n=355
     57: ("0", "255", "-180", "180", None),       # Framing Blade 1 Rot., n=68
     58: ("0", "255", "-180", "180", None),       # Framing Blade 2 Rot., n=52
     59: ("0", "255", "-180", "180", None),       # Framing Blade 4 Rot., n=56
     60: ("0", "255", "-180", "180", None),       # Framing Blade 3 Rot., n=55
     61: ("0", "255", "0", "100", None),          # Gobo Bounce, n=302
    100: (None, None, "0", "100", None),          # Fan Speed, n=185
}
ATTRS_PRESET = ("SSLPRESETLEVELMIN", "SSLPRESETLEVELMAX", "SSLPRESETPARAMMIN",
                "SSLPRESETPARAMMAX", "SSLPRESETCOLOR")

# Name → number, for descriptions written by hand. Case-insensitive.
NUM_CANAL = {nom.lower(): n for n, (nom, _, _) in TYPE_CANAL.items()}
NUM_PRESET = {nom.lower(): n for n, (nom, _, _) in TYPE_PRESET.items()}


def num_canal(nom: str | int) -> int:
    """A channel type by name or by number. Refuses anything else — an unknown
    type would be written into the file and silently mean something."""
    return _num(nom, NUM_CANAL, TYPE_CANAL, "canal")


def num_preset(nom: str | int) -> int:
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
    # A V2 payload is a refusal with its own type, not "this is not an .ssl2".
    assert classe(b'<DLMFILE TYPE="SSLLIBRARY2008" VERSION="2">') == "v2"
    assert classe(b'<?xml version="1.0"?><DLMFILE VERSION="3">') == "v3"
    assert classe(b"nawak") is None
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


# The fine (LSB) half of a 16-bit pair is marked with µ in 87 % of the
# library's 62 400 pairs, and stored **double-encoded**: the file's UTF-8 text
# is `Âµ`, which is the UTF-8 of the UTF-8 of `µ`. Writing a clean `µ` would be
# a different name from every one of the library's, so the marker is built by
# doing to `µ` exactly what the vendor's tooling did to it. The parenthesised
# suffix is the plurality form, 28 113 of 62 400; `Âµ{}` is next at 15 379.
MARQUEUR_FIN = "µ".encode("utf-8").decode("latin-1")     # « Âµ »
NOM_FIN = "{} (" + MARQUEUR_FIN + ")"


def genere(description: dict[str, object]) -> Element:
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

    globaux = _Globaux(graine) if description.get("gchannels") else None
    el_modes = Element("SSLMODES", {"SSLNBMODE": str(len(modes))})
    for i, mode in enumerate(modes):
        el_modes.enfants.append(_genere_mode(graine, i, mode, globaux))
    el_modes.vide = False

    enfants = [Element("SSLPROPERTIES", props, vide=True), el_modes]
    if globaux is not None:
        enfants.append(globaux.element())
    biblio = Element("SSLLIBRARY", {
        "SSLNAME": echappe(depuis_utf8(nom)),
        "SSLLCUID": _uid_long(graine, "library"),
        "SSLLCOWNERUID": _uid_uuid(graine, "owner"),
    }, enfants, vide=False)
    return Element("DLMFILE", {"VERSION": "3", "TYPE": "SSLLIBRARY"},
                   [biblio], vide=False)


class _Globaux:
    """`SSLGCHANNELS`: the profile's channel list, shared by every mode.

    A mode's channel points at its entry with `SSLCHANNELLINKED`, and the
    library's identity is that the two counts match — one `SSLCHANNEL` under
    `SSLGCHANNELS` per distinct `SSLCHANNELLINKED`, on 9 084 of its 9 848
    profiles that carry the element. The 764 that diverge all diverge the same
    way: 2 077 entries no mode points at, never a link with no entry. That
    reads as an editor keeping a channel it has removed from every mode, and
    it is the one thing this class deliberately does not reproduce.

    A 16-bit pair collapses into one 8-bit entry, which is not an assumption
    either: all 120 869 `SSLGCHANNELS` channels carry MSB=0, LSB=0 and
    `SSLCHANNEL16BITSINDEX="-1"`, and the fine half of a pair never points
    anywhere else than its coarse half — 26 947 pairs share one entry, 35 453
    leave the fine half unlinked, none point at two.

    Which mode channels are "the same channel" is the vendor editor's own
    bookkeeping and cannot be read off a file, so this uses `(type, name)`.
    """

    def __init__(self, graine: str) -> None:
        self.graine, self.par_cle, self.canaux = graine, {}, []

    def lien(self, el: Element) -> str:
        """The UID of `el`'s global entry, creating it on first sight."""
        cle = (el["SSLCHANNELTYPE"], el["SSLCHANNELNAME"])
        uid = self.par_cle.get(cle)
        if uid is None:
            uid = self.par_cle[cle] = _uid_element(
                self.graine, len(self.canaux), "global", *cle)
            self.canaux.append(_copie_globale(el, uid))
        return uid

    def element(self) -> Element:
        return Element("SSLGCHANNELS", {"SSLNBCHANNEL": str(len(self.canaux))},
                       self.canaux, vide=not self.canaux)


def _copie_globale(el, uid):
    """A mode channel as its `SSLGCHANNELS` entry: its own UID, no
    `SSLCHANNELTYPEINDEX` (absent from all 120 869 in the library), 8 bits, and
    every preset's `SSLPRESETTARGET` back to `-1` — a mode-relative channel
    index means nothing in a list that belongs to no mode, and the library
    agrees on 421 260 of 421 260."""
    copie = copy.deepcopy(el)
    copie.attrs["SSLCHANNELUID"] = uid
    copie.attrs.pop("SSLCHANNELTYPEINDEX", None)
    copie.attrs["SSLCHANNELMSB"] = copie.attrs["SSLCHANNELLSB"] = "0"
    copie.attrs["SSLCHANNEL16BITSINDEX"] = "-1"
    for preset in copie.trouve("SSLPRESET"):
        preset.attrs["SSLPRESETTARGET"] = "-1"
    return copie


def _genere_mode(graine, index, mode, globaux=None):
    canaux = mode.get("channels")
    if not isinstance(canaux, list) or not canaux:
        raise ValueError(f"mode {index} : 'channels' doit être une liste non vide")
    if len(canaux) > MAX_CANAUX:
        raise ValueError(f"mode {index} : {len(canaux)} canaux, maximum "
                         f"{MAX_CANAUX} (un univers DMX)")
    for i, canal in enumerate(canaux):
        if not isinstance(canal, dict) or "type" not in canal:
            raise ValueError(f"canal {i} : il faut au moins un 'type'")
    graine = f"{graine}\nmode{index}"
    types = [num_canal(c["type"]) for c in canaux]
    paires = _apparie(canaux, types)              # {fin: grossier}
    tis = _type_index(types, paires)
    el = Element("SSLMODE", {
        "SSLMODEUID": _uid_element(graine, index, "mode"),
        "SSLMODEINDEX": str(index),
        "SSLMODENAME": echappe(depuis_utf8(str(mode.get("name", "")))),
        "SSLNBCHANNEL": str(len(canaux)),
    }, vide=False)
    grossier = {g: f for f, g in paires.items()}  # l'autre sens de l'appariement
    for i, canal in enumerate(canaux):
        el.enfants.append(_genere_canal(graine, i, canal, types, tis, paires,
                                        grossier, canaux))
    if globaux is not None:
        liens = {}
        for i, enfant in enumerate(el.enfants):
            porteur = paires.get(i, i)            # le fin passe par son grossier
            if porteur not in liens:
                liens[porteur] = globaux.lien(el.enfants[porteur])
            enfant.attrs = _insere(enfant.attrs, "SSLCHANNEL2PRESETSINDEX",
                                   "SSLCHANNELLINKED", liens[porteur])
    return el


def _apparie(canaux, types):
    """`{index du canal fin: index de son grossier}`, from the `fine` key.

    `fine: true` pairs with the nearest earlier channel of the same type that
    is not itself fine and not already paired — which is what makes both of the
    library's layouts expressible, `Pan µPan Tilt µTilt` and the 7 % that read
    `Pan Tilt µPan µTilt`. `fine: <index>` says it outright.
    """
    paires, pris = {}, set()
    for i, canal in enumerate(canaux):
        fin = canal.get("fine")
        if fin is None or fin is False:
            continue
        if fin is True:
            libres = [j for j in range(i) if types[j] == types[i]
                      and j not in pris and not canaux[j].get("fine")]
            if not libres:
                raise ValueError(
                    f"canal {i} : 'fine' sans canal grossier libre de type "
                    f"{TYPE_CANAL[types[i]][0]!r} avant lui — donnez l'index")
            j = libres[-1]
        elif isinstance(fin, int) and not isinstance(fin, bool):
            j = fin
            if not 0 <= j < len(canaux):
                raise ValueError(f"canal {i} : 'fine' {j} hors du mode "
                                 f"(0-{len(canaux) - 1})")
            if j == i:
                raise ValueError(f"canal {i} : 'fine' pointe sur lui-même")
            if canaux[j].get("fine"):
                raise ValueError(f"canal {i} : 'fine' pointe le canal {j}, "
                                 f"lui-même marqué 'fine'")
        else:
            raise ValueError(f"canal {i} : 'fine' vaut {fin!r}, attendu true "
                             f"ou l'index du canal grossier")
        if j in pris:
            raise ValueError(f"canal {i} : le canal {j} est déjà apparié au "
                             f"canal {[f for f, g in paires.items() if g == j][0]}")
        paires[i], _ = j, pris.add(j)
    return paires


def _type_index(types, paires):
    """`SSLCHANNELTYPEINDEX` for each channel: how many channels of the same
    type came before — counting a 16-bit **pair** once, the fine half taking
    its coarse half's index. Measured on the library's 58 463 modes: that rule
    holds on 56 551 of them, against 41 609 for counting every channel."""
    vus, tis = {}, [None] * len(types)
    for i, t in enumerate(types):
        if i in paires:
            continue
        tis[i] = vus.get(t, 0)
        vus[t] = tis[i] + 1
    for fin, gros in paires.items():
        tis[fin] = tis[gros]
    return [str(t) for t in tis]


def _insere(attrs, apres, nom, valeur):
    """`attrs` with one attribute inserted right after another. Attribute order
    is stream order here, so it cannot just be appended."""
    out = {}
    for cle, val in attrs.items():
        out[cle] = val
        if cle == apres:
            out[nom] = valeur
    return out


def _genere_canal(graine, index, canal, types, tis, paires, grossier, descriptions):
    type_ = types[index]
    graine = f"{graine}\ncanal{index}"
    fin, gros = index in paires, grossier.get(index)
    # 16 bits, câblé dans les deux sens : chacun porte l'index de l'autre, et
    # les 62 400 paires de la bibliothèque sont symétriques sans exception.
    if fin:
        autre = paires[index]
    elif gros is not None:
        autre = gros
    else:
        autre = -1
    defaut_nom = TYPE_CANAL[type_][0]
    if fin:
        defaut_nom = NOM_FIN.format(descriptions[paires[index]].get("name")
                                    or TYPE_CANAL[types[paires[index]]][0])
    el = Element("SSLCHANNEL", {
        "SSLCHANNELUID": _uid_element(graine, index, "canal"),
        "SSLCHANNELTYPE": str(type_),
        "SSLCHANNELNAME": echappe(depuis_utf8(str(canal.get("name") or defaut_nom))),
        "SSLCHANNELICON": echappe(depuis_utf8(str(canal.get("icon", "")))),
        "SSLCHANNELMSB": "1" if gros is not None else "0",
        "SSLCHANNELLSB": "1" if fin else "0",
        "SSLCHANNEL2PRESETS": "0", "SSLCHANNEL2PRESETSINDEX": "-1",
        "SSLCHANNELTYPEINDEX": tis[index],
        "SSLCHANNEL16BITSINDEX": str(autre),
    }, vide=False)
    el.enfants.append(_genere_presets(graine, canal.get("presets") or [],
                                      index, types, tis))
    return el


def _genere_presets(graine, presets, canal=0, types=(), tis=()):
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
        el.enfants.append(_genere_preset(graine, i, preset, i == defaut, occupe,
                                         canal, types, tis))
    return el


def _preset_par_defaut(presets):
    """Exactly one preset per channel carries SSLPRESETDEFAULTPRESET="1" in the
    library. The description may say which; otherwise it is the first."""
    marques = [i for i, p in enumerate(presets) if p.get("defaut")]
    if len(marques) > 1:
        raise ValueError(f"presets : {len(marques)} marqués 'defaut', un seul "
                         f"peut l'être")
    return marques[0] if marques else 0


def _genere_preset(graine, index, preset, est_defaut, occupe,
                   canal=0, types=(), tis=()):
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
    attrs = {
        "SSLPRESETUID": uid, "SSLPRESETTEMPLATEUID": uid,
        "SSLPRESETDEFAULTUID": _uid_uuid(graine, "preset", index),
        "SSLPRESETTYPE": str(type_),
        "SSLPRESETNAME": echappe(depuis_utf8(
            str(preset.get("name") or TYPE_PRESET[type_][0]))),
        "SSLPRESETICON": echappe(depuis_utf8(str(preset.get("icon", "NoIcon")))),
        "SSLPRESETDMXSTART": str(debut), "SSLPRESETDMXEND": str(fin),
        "SSLPRESETDMXDEFAULT": str(int(par_defaut)),
        "SSLPRESETDEFAULTPRESET": "1" if est_defaut else "0",
        # SHOWDIMMER is written at the value 65 % of the library uses and is
        # still not understood, so it is still not offered as an option.
        "SSLPRESETSHOWDIMMER": "0",
    }
    # The five optional attributes, in the library's own order: COLOR, then the
    # parameter range, then the level range. Their default is what the library
    # writes for this preset type (DEFAUTS_PRESET); `null` in the description
    # drops one, a value replaces it.
    niveau, parametre, couleur = _attributs_preset(preset, index, type_)
    for nom, valeur in (("COLOR", couleur), ("PARAMMIN", parametre[0]),
                        ("PARAMMAX", parametre[1]), ("LEVELMIN", niveau[0]),
                        ("LEVELMAX", niveau[1])):
        if valeur is not None:
            attrs["SSLPRESET" + nom] = valeur
    attrs["SSLPRESETID"] = ""
    attrs["SSLPRESETTARGET"] = str(_cible(preset, index, type_, canal, types, tis))
    return Element("SSLPRESET", attrs, vide=True)


def _attributs_preset(preset, index, type_):
    """`(level, param, colour)` for one preset: the description's, or this
    preset type's measured default."""
    niv_min, niv_max, par_min, par_max, couleur = DEFAUTS_PRESET.get(
        type_, (None, None, None, None, None))
    niveau = _borne(preset, "level", (niv_min, niv_max), index)
    parametre = _borne(preset, "param", (par_min, par_max), index)
    if "color" in preset:
        couleur = _couleur(preset["color"], index)
    return niveau, parametre, couleur


def _borne(preset, cle, defaut, index):
    """`[min, max]` from the description — `null` drops the pair, and `null`
    inside it drops one half."""
    if cle not in preset:
        return defaut
    valeur = preset[cle]
    if valeur is None:
        return (None, None)
    if (not isinstance(valeur, (list, tuple)) or len(valeur) != 2
            or not all(v is None or (isinstance(v, int)
                                     and not isinstance(v, bool))
                       for v in valeur)):
        raise ValueError(f"preset {index} : {cle!r} doit être [min, max], deux "
                         f"entiers (ou null) — reçu {valeur!r}")
    return tuple(None if v is None else str(v) for v in valeur)


def _couleur(valeur, index):
    """`SSLPRESETCOLOR` from `"#rrggbb"` or from the integer the file carries.

    The integer is **0xBBGGRR** — the library's "Red" presets carry 255 and its
    "Blue" ones 16 711 680 — so a description that means red should say so in
    hex and let this do the swap."""
    if valeur is None:
        return None
    if isinstance(valeur, str):
        texte = valeur.lstrip("#")
        if len(texte) != 6 or any(c not in "0123456789abcdefABCDEF" for c in texte):
            raise ValueError(f"preset {index} : 'color' {valeur!r}, attendu "
                             f"\"#rrggbb\" ou un entier 0xBBGGRR")
        r, v, b = (int(texte[i:i + 2], 16) for i in (0, 2, 4))
        return str(r | v << 8 | b << 16)
    if isinstance(valeur, int) and not isinstance(valeur, bool):
        if not 0 <= valeur <= 0xFFFFFF:
            raise ValueError(f"preset {index} : 'color' {valeur} hors "
                             f"0-16777215")
        return str(valeur)
    raise ValueError(f"preset {index} : 'color' {valeur!r}, attendu \"#rrggbb\" "
                     f"ou un entier")


def _cible(preset, index, type_, canal, types, tis):
    """`SSLPRESETTARGET`: the description's `target`, or CIBLE_PRESET's rule."""
    if "target" in preset:
        cible = preset["target"]
        if cible is None or cible is False:
            return -1
        if not isinstance(cible, int) or isinstance(cible, bool):
            raise ValueError(f"preset {index} : 'target' {cible!r}, attendu "
                             f"l'index d'un canal du mode, ou null")
        if cible != -1 and not 0 <= cible < len(types):
            raise ValueError(f"preset {index} : 'target' {cible} hors du mode "
                             f"(0-{len(types) - 1})")
        return cible
    vise = CIBLE_PRESET.get(type_)
    if vise is None:
        return -1
    if canal < len(types) and types[canal] == vise:
        return canal                       # le preset agit sur son propre canal
    memes = [j for j, t in enumerate(types) if t == vise]
    if not memes:
        return -1
    rang = [j for j in memes if tis[j] == tis[canal]]
    return (rang or memes)[0]


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


def compare(a: Element, b: Element, chemin: str = '', sortie: list[str] | None = None) -> list[str]:
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


def recalcule_enums(fichiers: Iterable[str | PathLike[str]]) -> dict[str, object]:
    """Recount every table from a library. What `enums` compares them to.

    Four accumulators, one pass:

    - `canal` / `preset`: `{n: (nom_dominant, part, total)}` — the same shape as
      the embedded tables, so the diff is a dict comparison and not a story
      about one;
    - `cible`: per preset type, what `SSLPRESETTARGET` points at — the **type**
      of the channel at that index, or `"-1"`;
    - `regle`: whether `CIBLE_PRESET`'s rule, applied to that mode, reproduces
      the value the file actually carries;
    - `defauts`: per preset type, the value of each of the five optional
      attributes, `None` counted as its own value.
    """
    import collections
    votes = {"canal": collections.defaultdict(collections.Counter),
             "preset": collections.defaultdict(collections.Counter)}
    cible = collections.defaultdict(collections.Counter)
    regle = collections.defaultdict(collections.Counter)
    defauts = collections.defaultdict(collections.Counter)
    for chemin in fichiers:
        racine = charge(chemin)
        for e in racine.trouve("SSLCHANNEL"):
            votes["canal"][int(e.get("SSLCHANNELTYPE", -1))][
                _normalise(e.get("SSLCHANNELNAME", ""))] += 1
        for e in racine.trouve("SSLPRESET"):
            votes["preset"][int(e.get("SSLPRESETTYPE", -1))][
                _normalise(e.get("SSLPRESETNAME", ""))] += 1
            for attr in ATTRS_PRESET:
                defauts[(int(e.get("SSLPRESETTYPE", -1)), attr)][
                    e.get(attr)] += 1
        for mode in racine.trouve("SSLMODE"):
            canaux = [c for c in mode.enfants if c.tag == "SSLCHANNEL"]
            types = [int(c.get("SSLCHANNELTYPE", -1)) for c in canaux]
            tis = [c.get("SSLCHANNELTYPEINDEX") for c in canaux]
            for i, c in enumerate(canaux):
                for p in c.trouve("SSLPRESET"):
                    tp = int(p.get("SSLPRESETTYPE", -1))
                    v = p.get("SSLPRESETTARGET")
                    if v is None:
                        continue
                    k = int(v)
                    cible[tp][types[k] if 0 <= k < len(types) else "-1"] += 1
                    regle[tp][_cible({}, 0, tp, i, types, tis) == k] += 1
    out = {}
    for quoi, par_type in votes.items():
        out[quoi] = {}
        for num, noms in par_type.items():
            nom, part = noms.most_common(1)[0]
            total = sum(noms.values())
            out[quoi][num] = (nom, round(100 * part / total), total)
    out["cible"], out["regle"], out["defauts"] = cible, regle, defauts
    return out


_VARIANTES = re.compile(r"\(?\s*(Âµ|µ)\s*\)?")
_INDEX = re.compile(r"^\s*\d+\s*[.)]\s*")
_PONCTU = re.compile(r"[^a-z0-9+/&]+")


def _normalise(nom):
    """Fold the variants of one name: "1. Red", "Red (Âµ)" and "RED" are one
    vote for red, and counting them apart is what makes a 68 % look like 25 %."""
    nom = _VARIANTES.sub("", nom.replace("&amp;", "&"))
    return _PONCTU.sub(" ", _INDEX.sub("", nom).lower()).strip()


def compare_enums(fichiers: Iterable[str | PathLike[str]]) -> int:
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
    ecarts += _compare_cibles(mesure)
    ecarts += _compare_defauts(mesure)
    print(f"{len(mesure['canal'])} types de canal, {len(mesure['preset'])} de "
          f"preset ; {ecarts} écart(s) de couverture", file=sys.stderr)
    return ecarts


# The two criteria the derived tables are built on, stated once so that reading
# them and re-deriving them cannot drift apart.
VISE_MIN, DOMINANT_MIN = 0.50, 0.80    # CIBLE_PRESET
PRESENT_MIN = 0.50                     # DEFAUTS_PRESET — see the table's note
                                       # on why no value in (0.21, 0.94) exists


def _compare_cibles(mesure):
    """Re-derive CIBLE_PRESET, diff it, and score the rule it stands for."""
    ecarts, derive = 0, {}
    for tp, votes in sorted(mesure["cible"].items()):
        total = sum(votes.values())
        vises = total - votes["-1"]
        if not vises:
            continue
        dom, ndom = max(((k, v) for k, v in votes.items() if k != "-1"),
                        key=lambda x: x[1])
        marque = ""
        if vises / total >= VISE_MIN and ndom / vises >= DOMINANT_MIN:
            derive[tp] = dom
            marque = "VISEUR"
        print(f"cible  preset {tp:3} {TYPE_PRESET.get(tp, ('?',))[0][:24]:26} "
              f"n={total:7}  vise {100 * vises / total:3.0f} %, canal {dom} "
              f"{TYPE_CANAL.get(dom, ('?',))[0][:18]!r} {100 * ndom / vises:3.0f} "
              f"%  {marque}")
    for tp in sorted(set(derive) | set(CIBLE_PRESET)):
        if derive.get(tp) != CIBLE_PRESET.get(tp):
            print(f"cible  preset {tp} : la table dit {CIBLE_PRESET.get(tp)}, "
                  f"cette bibliothèque dit {derive.get(tp)}", file=sys.stderr)
            ecarts += 1
    ok = n = 0
    for tp, votes in sorted(mesure["regle"].items()):
        ok, n = ok + votes[True], n + votes[True] + votes[False]
        if votes[False]:
            t = votes[True] + votes[False]
            print(f"règle  preset {tp:3} {TYPE_PRESET.get(tp, ('?',))[0][:24]:26} "
                  f"{votes[True]}/{t} ({100 * votes[True] / t:.1f} %)")
    if n:
        print(f"SSLPRESETTARGET : la règle reproduit {ok}/{n} "
              f"({100 * ok / n:.2f} %) des valeurs de la bibliothèque",
              file=sys.stderr)
    return ecarts


def _compare_defauts(mesure):
    """Re-derive DEFAUTS_PRESET and diff it. The share the dominant value wins
    by is printed, not enforced: it is what says which cells are firm."""
    ecarts, derive, parts = 0, {}, {}
    types = {tp for tp, _ in mesure["defauts"]}
    for tp in sorted(types):
        ligne, part = [], []
        for attr in ATTRS_PRESET:
            votes = mesure["defauts"][(tp, attr)]
            total = sum(votes.values())
            presents = total - votes[None]
            if not total or presents / total < PRESENT_MIN:
                ligne.append(None)
                part.append(None)
                continue
            v, n = max(((k, x) for k, x in votes.items() if k is not None),
                       key=lambda x: x[1])
            ligne.append(v)
            part.append(round(100 * n / presents))
        if any(x is not None for x in ligne):
            derive[tp], parts[tp] = tuple(ligne), part
    for tp in sorted(set(derive) | set(DEFAUTS_PRESET)):
        a, b = DEFAUTS_PRESET.get(tp), derive.get(tp)
        if a != b:
            print(f"défauts preset {tp} : la table dit {a}, cette "
                  f"bibliothèque dit {b}", file=sys.stderr)
            ecarts += 1
        if b is not None:
            print(f"défaut preset {tp:3} {TYPE_PRESET.get(tp, ('?',))[0][:24]:26} "
                  + "  ".join(
                      f"{a2[9:]}={v}({p} %)" for a2, v, p
                      in zip(ATTRS_PRESET, b, parts[tp]) if v is not None))
    return ecarts


def verifie(fichiers: Sequence[str | PathLike[str]], bavard: bool = False) -> tuple[int, int, int]:
    """The oracle: decrypt → parse → write → encrypt, back to the same bytes.

    Both round trips at once, on real files, because they fail differently: a
    crypto bug moves every byte, a codec bug moves one attribute.
    """
    ok = echecs = hors = 0
    for chemin in fichiers:
        try:
            with open(chemin, "rb") as flux:
                brut = flux.read()
            clair = dechiffre(brut)
            quoi = classe(clair)
            if quoi is None:
                raise ValueError(f"déchiffré non-SSL2 ({clair[:16]!r})")
            if quoi != "v3":
                hors += 1
                continue
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
    return ok, echecs, hors


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


def _auto_test_16bits():
    """A 16-bit pair, its global entry, the targets and the five attributes.

    What this pins is the wiring, not the taste: each half carries the other's
    index, the pair counts once for SSLCHANNELTYPEINDEX and once in
    SSLGCHANNELS, and the channels come out in the description's order — which
    is the thing the software test looks at and the round trip cannot see.
    """
    d = {"name": "Test 16", "brand": "wolfmix-automation", "gchannels": True,
         "modes": [{"name": "10ch", "channels": [
             {"type": "Pan"}, {"type": "Tilt"},
             {"type": "Pan", "fine": True}, {"type": "Tilt", "fine": True},
             {"type": "Gobo Wheel", "name": "Gobo", "presets": [
                 {"type": "Gobo", "name": "Open", "dmx": [0, 7]}]},
             {"type": "Gobo Rotation", "name": "Gobo Rot", "presets": [
                 {"type": "Rotation Off", "dmx": [0, 7]},
                 {"type": "Gobo Wheel Rotation", "name": "CW", "dmx": [8, 255]}]},
             {"type": "Color Wheel", "name": "Color", "presets": [
                 {"type": "Color", "name": "Red", "dmx": [0, 9], "color": "#ff0000"},
                 {"type": "Color", "name": "Off", "dmx": [10, 19], "color": None},
                 {"type": "Color Wheel Rotation", "name": "Spin", "dmx": [20, 255]}]},
             {"type": "Shutter / Strobe", "name": "Strobe", "presets": [
                 {"type": "Shutter Open", "dmx": [0, 7], "defaut": True},
                 {"type": "Strobe", "dmx": [8, 255], "param": [1, 25]}]}]}]}
    racine = genere(d)
    assert write(parse(write(racine))) == write(racine)
    mode = next(racine.trouve("SSLMODE"))
    canaux = [c for c in mode.enfants if c.tag == "SSLCHANNEL"]
    assert mode["SSLNBCHANNEL"] == "8" == str(len(canaux))
    # l'ordre est celui de la description, pas un tri par type ou par paire
    assert [c["SSLCHANNELTYPE"] for c in canaux] == \
        ["1", "2", "1", "2", "8", "9", "5", "15"]
    # câblage 16 bits : symétrique, un grossier et un fin, l'un l'index de l'autre
    for i, j in ((0, 2), (1, 3)):
        gros, fin = canaux[i], canaux[j]
        assert (gros["SSLCHANNELMSB"], gros["SSLCHANNELLSB"]) == ("1", "0")
        assert (fin["SSLCHANNELMSB"], fin["SSLCHANNELLSB"]) == ("0", "1")
        assert gros["SSLCHANNEL16BITSINDEX"] == str(j)
        assert fin["SSLCHANNEL16BITSINDEX"] == str(i)
        # la paire compte pour un : le fin reprend l'index de type du grossier
        assert fin["SSLCHANNELTYPEINDEX"] == gros["SSLCHANNELTYPEINDEX"] == "0"
        # le marqueur µ, double-encodé comme la bibliothèque le stocke
        assert vers_utf8(fin["SSLCHANNELNAME"]) == \
            NOM_FIN.format(vers_utf8(gros["SSLCHANNELNAME"]))
    # les octets qui atterrissent dans le fichier sont bien le µ double-encodé
    assert depuis_utf8(MARQUEUR_FIN).encode("latin-1") == b"\xc3\x82\xc2\xb5"
    assert b"Pan (\xc3\x82\xc2\xb5)" in write(racine)
    for c in canaux[4:]:
        assert c["SSLCHANNEL16BITSINDEX"] == "-1"
        assert (c["SSLCHANNELMSB"], c["SSLCHANNELLSB"]) == ("0", "0")

    # SSLGCHANNELS : autant d'entrées que de SSLCHANNELLINKED distincts, la
    # paire 16 bits comptant pour une — l'identité mesurée sur la bibliothèque.
    gc = next(racine.trouve("SSLGCHANNELS"))
    entrees = [c for c in gc.enfants if c.tag == "SSLCHANNEL"]
    liens = {c["SSLCHANNELLINKED"] for c in canaux}
    assert gc["SSLNBCHANNEL"] == str(len(entrees)) == str(len(liens)) == "6"
    assert liens == {c["SSLCHANNELUID"] for c in entrees}
    assert canaux[0]["SSLCHANNELLINKED"] == canaux[2]["SSLCHANNELLINKED"]
    for e in entrees:
        assert "SSLCHANNELTYPEINDEX" not in e.attrs and "SSLCHANNELLINKED" not in e.attrs
        assert (e["SSLCHANNELMSB"], e["SSLCHANNELLSB"],
                e["SSLCHANNEL16BITSINDEX"]) == ("0", "0", "-1")
        for p in e.trouve("SSLPRESET"):
            assert p["SSLPRESETTARGET"] == "-1", p.attrs
    # sans `gchannels`, rien de tout cela n'apparaît
    sans = genere({**d, "gchannels": False})
    assert not list(sans.trouve("SSLGCHANNELS"))
    assert all("SSLCHANNELLINKED" not in c.attrs for c in sans.trouve("SSLCHANNEL"))

    # SSLPRESETTARGET : l'index du canal qui porte l'objet, -1 sinon.
    cibles = {p["SSLPRESETNAME"]: p["SSLPRESETTARGET"]
              for c in canaux for p in c.trouve("SSLPRESET")}
    assert cibles["CW"] == "4"          # Gobo Wheel Rotation → le canal Gobo
    assert cibles["Spin"] == "6"        # Color Wheel Rotation → son propre canal
    assert cibles["Open"] == cibles["Strobe"] == "-1"
    # les cinq attributs optionnels : le défaut du type, ou ce que dit la
    # description, et `null` retire l'attribut au lieu de le mettre à zéro.
    presets = {p["SSLPRESETNAME"]: p for c in canaux for p in c.trouve("SSLPRESET")}
    assert presets["Open"]["SSLPRESETLEVELMIN"] == "0"
    assert presets["Open"]["SSLPRESETLEVELMAX"] == "255" != \
        presets["Open"]["SSLPRESETDMXEND"]      # LEVEL n'est pas la plage DMX
    assert presets["Strobe"]["SSLPRESETPARAMMIN"] == "1"
    assert presets["Strobe"]["SSLPRESETPARAMMAX"] == "25"
    assert "SSLPRESETCOLOR" not in presets["Off"].attrs
    assert presets["Red"]["SSLPRESETCOLOR"] == "255"     # #ff0000 → 0xBBGGRR
    assert _couleur("#0000ff", 0) == "16711680" and _couleur("#00ff00", 0) == "65280"
    assert "SSLPRESETLEVELMIN" not in presets["Rotation Off"].attrs
    # l'ordre des attributs est celui de la bibliothèque
    ordre = [a for a in presets["Red"].attrs
             if a in ATTRS_PRESET or a in ("SSLPRESETSHOWDIMMER", "SSLPRESETID")]
    assert ordre == ["SSLPRESETSHOWDIMMER", "SSLPRESETCOLOR", "SSLPRESETID"], ordre

    # l'appariement explicite, pour les paires non adjacentes déjà croisées
    explicite = genere({"name": "n", "brand": "b", "modes": [{"channels": [
        {"type": "Pan"}, {"type": "Dimmer"}, {"type": "Pan", "fine": 0}]}]})
    ec = [c for c in next(explicite.trouve("SSLMODE")).enfants]
    assert (ec[0]["SSLCHANNEL16BITSINDEX"], ec[2]["SSLCHANNEL16BITSINDEX"]) == ("2", "0")
    assert ec[1]["SSLCHANNEL16BITSINDEX"] == "-1"

    refus = [
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red"}, {"type": "Pan", "fine": True}]}]}, "sans canal grossier"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Pan"}, {"type": "Pan", "fine": True},
            {"type": "Pan", "fine": 0}]}]}, "déjà apparié"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Pan"}, {"type": "Pan", "fine": 7}]}]}, "hors du mode"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Pan", "fine": 0}]}]}, "sur lui-même"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Pan"}, {"type": "Pan", "fine": "oui"}]}]}, "attendu true"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [
                {"type": "Color", "color": "rouge"}]}]}]}, "#rrggbb"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [
                {"type": "Color", "param": [1, 2, 3]}]}]}]}, "'param'"),
        ({"name": "n", "brand": "b", "modes": [{"channels": [
            {"type": "Red", "presets": [
                {"type": "Color", "target": 9}]}]}]}, "hors du mode"),
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
    _auto_test_16bits()
    fichiers = fichiers_biblio()
    if not fichiers:
        print("ssl2: crypto et générateur ok (hors fichiers)", file=sys.stderr)
        return pas_de_biblio()
    ok, echecs, hors = verifie(fichiers[:echantillon])
    if echecs:
        raise SystemExit(f"ssl2: {echecs} échec(s) sur {ok + echecs}")
    print(f"self-check ok: générateur, puis aller-retour octet-près sur {ok} fichiers "
          f"(sur {len(fichiers)} — `ssl2.py verify` les fait tous)",
          file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
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
        ok, echecs, hors = verifie(fichiers, args.bavard)
        print(f"{ok}/{ok + echecs} aller-retours octet-près"
              + (f", {hors} hors périmètre (SSL2 v2)" if hors else ""),
              file=sys.stderr)
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
