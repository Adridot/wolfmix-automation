#!/usr/bin/env python3
"""The semantic JSON ↔ bytes codec for variant-A TLV records (on wpjlib).

The safety contract: decode(type, payload) returns a JSON-compatible dict whose
encode(type, dict) reproduces the EXACT bytes. decode checks that round trip
itself; on failure (unsupported type, unexpected protobuf) it returns
{"raw": hex} — never a loss, never an approximation. Proof: demo() over the
whole variant-A corpus.

Representation:
- a named field (proof: research/rig-c-bug.md) → a semantic key;
- an unidentified field → the neutral "fN" key: varint = int, length =
  {"hex":…}, fixed = {"f32":…}/{"f64":…};
- an absent field is absent from the dict (≠ an explicit zero); the dict's
  order is the wire order.
"""
import json
import sys

import wpj_wire
import wpjlib

# Schemas: field → (name, kind). kind: "v" varint, "str" UTF-8, "hex" raw
# bytes, "packed" = packed varints (a list of ints), dict = sub-message
# (repeated for lists of entries).
# 105: f4/f7 delimit the slice of record 106 that belongs to the entry, NOT a
# DMX address (the address is 115.f2). See the registry, "record 105".
# f6 = the group index (0-7 = A-H, 8 = the effects slot), redundant with
# 115.f4 — see the registry, "the fixture → group assignment".
_PATCH = {1: ("profile", "v"), 4: ("offset_106", "v"), 5: ("fixture", "v"),
          6: ("group", "v"), 7: ("entry_count_106", "v")}
_PROFIL = {2: ("channel_count", "v"), 8: ("name", "str"), 9: ("hash", "hex"),
           11: ("timestamp", "v")}
# The order of a pad's 7 channels: device-confirmed (the W1's RGB+ view, raw 0-255)
_PAD = {1: ("red", "v"), 2: ("green", "v"), 3: ("blue", "v"),
        4: ("white", "v"), 5: ("amber", "v"), 6: ("lime", "v"), 7: ("uv", "v")}

# Sous-message FX (commun Beam/Color/Move) — research/preset-format-165.md.
# FX6-02/03: f6 = Phase, f8 = Size, f9 = Speed, f2 = Fade. The speed had been
# read on f2 since ACC-04; the screen says f9, and f2 follows the fade all the
# way to vanishing when it reaches 0. "speed" stays the name of the speed: it
# changes field, not meaning, and callers keep their intent.
# f3 and f5 stay neutral keys: their meaning depends on the engine (f3 =
# Feature on beam, measured; Fan on move, inferred), and one shared schema
# cannot carry two names.
_FX = {7: ("effect", "v"), 4: ("link_order", "v"), 10: ("speed_source", "v"),
       1: ("bpm_division", "v"), 2: ("fade", "v"),
       6: ("phase", "v"), 8: ("size", "v"), 9: ("speed", "v")}
_PRESET = {
    19: ("id", "v"), 25: ("name", "str"),
    1: ("beam_fx1", _FX), 2: ("beam_fx2", _FX),
    5: ("color_fx1", _FX), 6: ("color_fx2", _FX),
    21: ("move_fx1", _FX), 22: ("move_fx2", _FX),
    28: ("positions", "packed"),          # position index per group A–H
    29: ("gobos", "packed"),              # gobo index (type 145) per group,
                                          # 0-based, 255 = none — device-confirmed
    30: ("color_pattern", "packed"),    # the static colour's PATTERN per group
                                          # A–H (name read on screen) — device-confirmed
    # f31: 20 packed varints = the bytes of a 160-bit field, cut into eight
    # 20-bit masks, one per group A–H; bit n of group g = pad n+1 of that
    # group's palette 140 — device-confirmed, registry
    # « f31 — one 20-pad mask per group A–H ».
    31: ("static_color", "packed"),
    # f10: the content mask, six bits, 1 = toggle OFF, in PRESET EDIT screen
    # order — bit0 COLOR, 1 MOVE, 2 BEAM, 3 GOBO, 4 LIVE EDIT, 5 OTHER
    # (bit 5 predicted, not yet measured). See the registry, F4-02.
    10: ("content_mask", "v"),
    17: ("dimmers", "packed"),            # dimmer per group A–H
    # The five features of the STATIC GOBO screen, as a percentage per group
    # A–H — device-confirmed by a preset capture, see "GOBO-02".
    14: ("gobo_rotate", "packed"), 32: ("gobo_focus", "packed"),
    33: ("gobo_prism", "packed"), 34: ("gobo_zoom", "packed"),
    35: ("gobo_iris", "packed"),
    8: ("color_fx_active", "packed"), 24: ("move_fx_active", "packed"),
    # The page selector per group A–H: 0 = FX1, 1 = FX2. The record files each
    # engine as a quadruple — pair, selector, active: f1/f2/f3 for beam,
    # f5/f6/f7/f8 for colour, f21/f22/f23/f24 for move. All three are measured,
    # one shot each: F7-01 colour, F7-03 move, F7-04 beam. Independent of the
    # `f16` mask: a group keeps its pending page even when the engine is off.
    # A page 1 set by hand reads 0, like a page never set — the field encodes
    # the page, not the fact of having been set (F7-04's control).
    3: ("page_beam_fx", "packed"),
    7: ("page_color_fx", "packed"), 23: ("page_move_fx", "packed"),
}

SCHEMAS = {
    101: {1: ("name", "str")},
    102: {},                                  # 16 bytes, unidentified fields
    105: {5: ("patch", _PATCH)},
    115: {5: ("fixtures", {2: ("dmx_address", "v"), 3: ("profile", "v"),
                          4: ("group", "v")})},
    116: {5: ("profiles", _PROFIL)},
    120: {5: ("channels", {})},                 # an empty {} entry = `2a 00` = all zero
    125: {5: ("groups", {8: ("name", "str")})},
    135: {5: ("pads", _PAD)},
    140: {2: ("page", "v"), 5: ("pads", _PAD)},
    # 111: the value ranges of a channel (SPEC §7.6). f1/f2 = first and last
    # DMX value, f3 = function (14 = gobo wheel), f4 = the gobo image id of the
    # wheel ranges (= 145.f2, identity checked). The wire order is the pad
    # order, and it is free — device-confirmed, SORT-01.
    111: {5: ("ranges", {1: ("start", "v"), 2: ("end", "v"),
                         3: ("function", "v"), 4: ("gobo_id", "v")})},
    # 145: the gobo palette. f1 = icon-font glyph (' ' = empty), f2 = gobo
    # image id (= 111[range].f4), f3 = an optional name, operator-assignable and
    # written off-device — device-confirmed, RENAME-01. See the registry.
    145: {5: ("gobos", {1: ("glyph", "str"), 2: ("gobo_id", "v"),
                        3: ("name", "str")})},
    150: {5: ("positions", {5: ("name", "str")})},
    # 151: the positions of fixtures "detached" from a slot of 150, cut by
    # 150.f1/f2. Three signed offsets, value = (v - 32768) / 32767 —
    # device-confirmed on the POSITION screen. See the registry, "POS-04".
    151: {5: ("detached", {1: ("fixture", "v"), 2: ("focus_offset", "v"),
                            3: ("pan_offset", "v"), 4: ("tilt_offset", "v")})},
    # 130: the DMX IN mapping table (MAP-01..05, registry). f4 = the function
    # targeted — 20 = group dimmer, 27 = MAIN, 70 = preset, 17 = BPM Tap,
    # 10 = Wolf: this is NOT the screen's category, two entries of the same
    # category carry different f4. f2 = the instance index when the function is
    # instanced (group 0-7, preset 0-n), and **255** when it is not. The DMX IN
    # channel is **16 bits spread over two fields**: `channel_base0 = f5 * 256
    # + f6`, the displayed channel being channel_base0 + 1. f5 stayed invisible
    # until CH300 because the whole corpus fit under 256 — measured at CH300
    # (f5=1, f6=43) and CH512 (f5=1, f6=255). An unmapped function has **no
    # entry**: absence, not a sentinel. An entry's key is (f4, f2), never its
    # rank: the wire order moves without the content changing. f1 = the number
    # of entries. f7 and f8 are 1 everywhere, have never moved, and stay
    # unnamed.
    130: {5: ("mappings", {2: ("instance", "v"), 4: ("function", "v"),
                           5: ("channel_high_byte", "v"),
                           6: ("channel_low_byte", "v")})},
    160: {5: ("macros", {6: ("name", "str")})},
    165: {5: ("presets", _PRESET)},
}
# Deliberate passthrough: a documented structure, no schema yet. Data rather
# than a comment, because `tools/wpj_counts.py` checks the documents against it
# — a record that moves from here to SCHEMAS must not need a doc edit to stay
# true, it must make the gate fail until one happens.
PASSTHROUGH = (106, 110, 155, 161)

# Every record type the container is known to carry.
TYPES = tuple(sorted(set(SCHEMAS) | set(PASSTHROUGH)))


# --- wire protobuf -----------------------------------------------------------

_rvarint = wpj_wire.read_varint          # one varint reader for the repository
                                         # (WireError is a ValueError, so the
                                         # existing `except` clauses still catch)


def _wvarint(v):
    # -1 would not terminate (the arithmetic shift stays at -1) and True would
    # encode as 1 without anyone asking for it.
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"varint: integer expected, got {v!r}")
    if v < 0:
        raise ValueError(f"varint: negative value {v}")
    out = bytearray()
    while True:
        b = v & 0x7F; v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


# The public keys were French until 2026-08-31. They are not accepted as
# aliases: a retired key is an error, and the error names its replacement. The
# repository had no tag, no release and no known consumer — the moment was
# right, and an alias layer would have been code written to be deleted.
CLES_RETIREES = {
    "adresse_dmx": "dmx_address",
    "ambiances": "moods",
    "ambre": "amber",
    "blanc": "white",
    "bleu": "blue",
    "canal": "channel",
    "canal_octet_bas": "channel_low_byte",
    "canal_octet_haut": "channel_high_byte",
    "canaux": "channels",
    "cible": "target",
    "color_fx_actif": "color_fx_active",
    "couleur": "color",
    "couleur_statique": "static_color",
    "debut": "start",
    "detachees": "detached",
    "effet": "effect",
    "energie": "energy",
    "fin": "end",
    "fonction": "function",
    "glyphe": "glyph",
    "gobo_noms": "gobo_names",
    "gobo_ordre": "gobo_order",
    "groupe": "group",
    "groupes": "groups",
    "masque_contenu": "content_mask",
    "modele": "template",
    "move_fx_actif": "move_fx_active",
    "nb_canaux": "channel_count",
    "nb_entrees_106": "entry_count_106",
    "nom": "name",
    "pattern_couleur": "color_pattern",
    "plages": "ranges",
    "profil": "profile",
    "profils": "profiles",
    "rouge": "red",
    "vert": "green",
    "vitesse": "speed",
}


def remplacante(cle):
    """The English name of a retired French key, or None."""
    return CLES_RETIREES.get(cle)


def _decode_msg(buf, schema):
    out, i = {}, 0
    while i < len(buf):
        tag, i = _rvarint(buf, i)
        f, wt = tag >> 3, tag & 7
        if f == 0:
            raise ValueError("champ 0")
        nom, genre = schema.get(f, (f"f{f}", None))
        if wt == 0:
            v, i = _rvarint(buf, i)
        elif wt == 2:
            ln, i = _rvarint(buf, i)
            if i + ln > len(buf):
                raise ValueError("longueur")
            chunk = buf[i:i + ln]; i += ln
            if genre == "str":
                try:
                    v = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    v = {"hex": chunk.hex()}
            elif genre == "packed":
                try:
                    v, j = [], 0
                    while j < len(chunk):
                        x, j = _rvarint(chunk, j)
                        v.append(x)
                except ValueError:
                    v = {"hex": chunk.hex()}
            elif genre == "hex":
                v = chunk.hex()
            elif isinstance(genre, dict):
                try:
                    v = _decode_msg(chunk, genre)
                except ValueError:
                    v = {"hex": chunk.hex()}
            else:
                v = {"hex": chunk.hex()}
        elif wt == 5:
            if i + 4 > len(buf):
                raise ValueError("f32")
            v = {"f32": buf[i:i + 4].hex()}; i += 4
        elif wt == 1:
            if i + 8 > len(buf):
                raise ValueError("f64")
            v = {"f64": buf[i:i + 8].hex()}; i += 8
        else:
            raise ValueError(f"wire type {wt}")
        if isinstance(genre, dict):          # a list of entries: always a list
            out.setdefault(nom, []).append(v)
        elif nom in out:                     # unexpected repeat → list
            if not isinstance(out[nom], list):
                out[nom] = [out[nom]]
            out[nom].append(v)
        else:
            out[nom] = v
    return out


def _encode_msg(d, schema):
    inv = {nom: (f, genre) for f, (nom, genre) in schema.items()}
    out = bytearray()
    for nom, val in d.items():
        if nom in inv:
            f, genre = inv[nom]
        elif nom.startswith("f") and nom[1:].isdigit():
            f, genre = int(nom[1:]), None
        else:
            neuve = remplacante(nom)
            if neuve:
                raise ValueError(
                    f"key {nom!r} was retired on 2026-08-31: write {neuve!r}")
            raise ValueError(f"unknown key {nom!r}")
        if genre == "packed" and isinstance(val, list) and \
                not (val and isinstance(val[0], (list, dict))):
            vals = [val]                     # one occurrence = one list of ints
        else:
            vals = val if isinstance(val, list) else [val]
        for v in vals:
            out += _emit(f, genre, v)
    return bytes(out)


def _emit(f, genre, v):
    if isinstance(v, dict) and set(v) == {"f32"}:
        return _wvarint(f << 3 | 5) + bytes.fromhex(v["f32"])
    if isinstance(v, dict) and set(v) == {"f64"}:
        return _wvarint(f << 3 | 1) + bytes.fromhex(v["f64"])
    if isinstance(v, int):
        return _wvarint(f << 3) + _wvarint(v)
    if isinstance(v, dict) and set(v) == {"hex"}:
        pl = bytes.fromhex(v["hex"])
    elif genre == "packed" and isinstance(v, list):
        pl = b"".join(_wvarint(x) for x in v)
    elif genre == "hex":
        pl = bytes.fromhex(v)
    elif genre == "str" or isinstance(v, str):
        pl = v.encode("utf-8")
    elif isinstance(v, dict):
        pl = _encode_msg(v, genre if isinstance(genre, dict) else {})
    else:
        raise ValueError(f"value cannot be encoded for f{f}: {v!r}")
    return _wvarint(f << 3 | 2) + _wvarint(len(pl)) + pl


# --- API ---------------------------------------------------------------------

def encode(typ, d):
    if set(d) == {"raw"}:
        return bytes.fromhex(d["raw"])
    return _encode_msg(d, SCHEMAS.get(typ, {}))


def decode(typ, payload):
    if typ in SCHEMAS:
        try:
            d = _decode_msg(payload, SCHEMAS[typ])
            if encode(typ, d) == payload:    # byte-level self-check
                return d
        except ValueError:
            pass
    return {"raw": payload.hex()}


def projet_vers_dict(path):
    w = wpjlib.Wpj.load(path)
    return {"fichier": path, "prefixe": w.prefix.hex(),
            "records": [{"type": t, **decode(t, p)} for t, p in w.records]}


# --- the fidelity proof ------------------------------------------------------

def demo():
    files = wpjlib.corpus_files()
    if not files:
        return wpjlib.pas_de_corpus("wpj_codec")
    stats, nb_fichiers = {}, 0
    for path in files:
        try:
            w = wpjlib.Wpj.load(path)
        except (ValueError, OSError):
            continue                          # variantes B/C ou illisible
        nb_fichiers += 1
        for t, p in w.records:
            d = decode(t, p)
            assert encode(t, d) == p, f"fidelity broken: type {t} in {path}"
            occ, raw = stats.get(t, (0, 0))
            stats[t] = (occ + 1, raw + ("raw" in d))
    if not nb_fichiers:
        return wpjlib.pas_de_corpus("wpj_codec")
    print(f"byte fidelity verified on {nb_fichiers} variant-A files")
    print("type  occ  decoded")
    for t in sorted(stats):
        occ, raw = stats[t]
        etat = "yes" if t in SCHEMAS and raw == 0 else "no (passthrough)"
        print(f"{t:4d} {occ:4d}  {etat}")
        assert t not in SCHEMAS or raw == 0, f"type {t}: {raw}/{occ} as raw"


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("projet", nargs="?",
                         help="decode a variant-A project to JSON; "
                              "with no argument, self-check")
    args = parseur.parse_args(argv)
    if args.projet is None:
        demo()
        return 0
    print(json.dumps(projet_vers_dict(args.projet), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
