#!/usr/bin/env python3
"""Codec sémantique JSON ↔ octets des records TLV variante A (sur wpjlib).

Contrat de sûreté : decode(type, payload) rend un dict JSON-compatible dont
encode(type, dict) reproduit les octets EXACTS. decode vérifie lui-même le
round-trip ; en cas d'échec (type non supporté, protobuf inattendu) il rend
{"raw": hex} — jamais de perte, jamais d'à-peu-près. Preuve : demo() sur
tout le corpus variante A.

Représentation :
- champ nommé (preuve : research/rig-c-bug.md) → clé sémantique ;
- champ non identifié → clé neutre "fN" : varint = int, longueur = {"hex":…},
  fixe = {"f32":…}/{"f64":…} ;
- champ absent = absent du dict (≠ zéro explicite) ; ordre du dict = ordre wire.
"""
import json
import sys

import wpjlib

# Schémas : champ → (nom, genre). genre : "v" varint, "str" UTF-8,
# "hex" octets bruts, "packed" = varints packés (liste d'ints),
# dict = sous-message (répété pour les listes d'entrées).
# 105 : f4/f7 délimitent la tranche du record 106 qui appartient à l'entrée,
# PAS une adresse DMX (l'adresse est 115.f2). Voir le registre, « record 105 ».
# f6 = index de groupe (0-7 = A-H, 8 = le slot des effets), redondant avec
# 115.f4 — voir le registre, « l'affectation luminaire → groupe ».
_PATCH = {1: ("profil", "v"), 4: ("offset_106", "v"), 5: ("fixture", "v"),
          6: ("groupe", "v"), 7: ("nb_entrees_106", "v")}
_PROFIL = {2: ("nb_canaux", "v"), 8: ("nom", "str"), 9: ("hash", "hex"),
           11: ("timestamp", "v")}
# Ordre des 7 canaux d'un pad : device-confirmed (vue RGB+ du W1, brut 0-255)
_PAD = {1: ("rouge", "v"), 2: ("vert", "v"), 3: ("bleu", "v"),
        4: ("blanc", "v"), 5: ("ambre", "v"), 6: ("lime", "v"), 7: ("uv", "v")}

# Sous-message FX (commun Beam/Color/Move) — research/preset-format-165.md.
# f8/f6/f9 (size/fade/phase, attribution permutable) et f3/f5 : clés neutres.
_FX = {7: ("effet", "v"), 4: ("link_order", "v"), 10: ("speed_source", "v"),
       1: ("bpm_division", "v"), 2: ("vitesse", "v")}
_PRESET = {
    19: ("id", "v"), 25: ("nom", "str"),
    1: ("beam_fx1", _FX), 2: ("beam_fx2", _FX),
    5: ("color_fx1", _FX), 6: ("color_fx2", _FX),
    21: ("move_fx1", _FX), 22: ("move_fx2", _FX),
    28: ("positions", "packed"),          # index de position par groupe A–H
    29: ("gobos", "packed"),              # index de gobo (type 145) par groupe,
                                          # 0-based, 255 = aucun — device-confirmed
    30: ("pattern_couleur", "packed"),    # PATTERN de la couleur statique par groupe
                                          # A–H (nom lu sur l'écran) — device-confirmed
    # f10 : masque de contenu, six bits, 1 = bascule ÉTEINTE, dans l'ordre de
    # l'écran PRESET EDIT — bit0 COLOR, 1 MOVE, 2 BEAM, 3 GOBO, 4 LIVE EDIT,
    # 5 OTHER (bit 5 prédit, pas encore mesuré). Voir le registre, F4-02.
    10: ("masque_contenu", "v"),
    17: ("dimmers", "packed"),            # dimmer par groupe A–H
    8: ("color_fx_actif", "packed"), 24: ("move_fx_actif", "packed"),
}

SCHEMAS = {
    101: {1: ("nom", "str")},
    102: {},                                  # 16 octets, champs non identifiés
    105: {5: ("patch", _PATCH)},
    115: {5: ("fixtures", {2: ("adresse_dmx", "v"), 3: ("profil", "v"),
                          4: ("groupe", "v")})},
    116: {5: ("profils", _PROFIL)},
    120: {5: ("canaux", {})},                 # entrée vide {} = `2a 00` = tout à 0
    125: {5: ("groupes", {8: ("nom", "str")})},
    135: {5: ("pads", _PAD)},
    140: {2: ("page", "v"), 5: ("pads", _PAD)},
    # 145 : palette gobo. f1 = glyphe police d'icônes (' ' = vide), f2 = id
    # d'image gobo (= 111[plage].f4), f3 = nom optionnel. Voir le registre.
    145: {5: ("gobos", {1: ("glyphe", "str"), 2: ("gobo_id", "v"),
                        3: ("nom", "str")})},
    150: {5: ("positions", {5: ("nom", "str")})},
    160: {5: ("macros", {6: ("nom", "str")})},
    165: {5: ("presets", _PRESET)},
}
# passthrough volontaire : 106, 110, 111, 130, 151, 155, 161


# --- wire protobuf -----------------------------------------------------------

def _rvarint(buf, i):
    v = shift = 0
    while True:
        if i >= len(buf) or shift > 70:
            raise ValueError("varint")
        b = buf[i]; i += 1
        v |= (b & 0x7F) << shift; shift += 7
        if not b & 0x80:
            return v, i


def _wvarint(v):
    out = bytearray()
    while True:
        b = v & 0x7F; v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


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
        if isinstance(genre, dict):          # liste d'entrées : toujours une liste
            out.setdefault(nom, []).append(v)
        elif nom in out:                     # répétition inattendue → liste
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
            raise ValueError(f"clé inconnue {nom!r}")
        if genre == "packed" and isinstance(val, list) and \
                not (val and isinstance(val[0], (list, dict))):
            vals = [val]                     # une occurrence = une liste d'ints
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
        raise ValueError(f"valeur inencodable pour f{f}: {v!r}")
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
            if encode(typ, d) == payload:    # auto-vérification octet
                return d
        except ValueError:
            pass
    return {"raw": payload.hex()}


def projet_vers_dict(path):
    w = wpjlib.Wpj.load(path)
    return {"fichier": path, "prefixe": w.prefix.hex(),
            "records": [{"type": t, **decode(t, p)} for t, p in w.records]}


# --- preuve de fidélité ------------------------------------------------------

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
            assert encode(t, d) == p, f"fidélité rompue : type {t} dans {path}"
            occ, raw = stats.get(t, (0, 0))
            stats[t] = (occ + 1, raw + ("raw" in d))
    if not nb_fichiers:
        return wpjlib.pas_de_corpus("wpj_codec")
    print(f"fidélité octet vérifiée sur {nb_fichiers} fichiers variante A")
    print("type  occ  décodé")
    for t in sorted(stats):
        occ, raw = stats[t]
        etat = "oui" if t in SCHEMAS and raw == 0 else "non (passthrough)"
        print(f"{t:4d} {occ:4d}  {etat}")
        assert t not in SCHEMAS or raw == 0, f"type {t} : {raw}/{occ} en raw"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(projet_vers_dict(sys.argv[1]), ensure_ascii=False, indent=1))
    else:
        demo()
