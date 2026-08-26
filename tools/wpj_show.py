#!/usr/bin/env python3
"""Compilateur de show minimal, template-based (sur wpjlib + wpj_codec).

Principe : on part TOUJOURS d'un projet donneur variante A existant et on
applique une spec JSON d'édition. Aucune structure synthétisée from scratch :
un preset / une position / une entrée de palette éditée doit déjà exister
dans le donneur ; tout le reste est préservé octet pour octet par wpjlib.
Périmètre v1 = champs à statut ≥ correlated uniquement (records 101, 165,
150, 135) ; size/fade/phase (f8/f6/f9, attribution hypothesized) exclus.

Usage :
  wpj_show.py compile show.json sortie.wpj   compile + auto-verify
  wpj_show.py verify base.wpj sortie.wpj     liste les records qui diffèrent
  wpj_show.py                                self-check (corpus, sans trace)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpjlib
import wpj_codec

_FX_NOMS = ("beam_fx1", "beam_fx2", "color_fx1", "color_fx2",
            "move_fx1", "move_fx2")
# clé FX → bornes (statuts correlated, research/preset-format-165.md)
_FX_CLES = {"effet": (0, 8), "vitesse": (0, 200), "link_order": (10, 13),
            "speed_source": (0, 2), "bpm_division": (0, 1 << 31)}
_SHOW_CLES = ("base", "nom", "presets", "positions", "palette")
_PRESET_CLES = ("id", "nom", "positions", "dimmers") + _FX_NOMS
# Attribution device-confirmed (registre, type 150) : f6 = PAN, f7 = TILT,
# f3 = FAN, f4 = FOCUS OFFSET. Une lecture antérieure plaçait pan/tilt en
# f3/f4 ; elle est réfutée par l'écran d'édition du W1.
_POS_CLES = ("page", "index", "nom", "pan", "tilt", "fan")
_POS_CHAMPS = {"pan": "f6", "tilt": "f7", "fan": "f3"}
_PAL_CLES = ("index", "rouge", "vert", "bleu")


def _cles(d, permises, contexte):
    inconnues = [k for k in d if k not in permises]
    if inconnues:
        raise ValueError(f"{contexte} : clés hors périmètre {inconnues} ; "
                         f"permises : {list(permises)}")


def _borne(contexte, nom, v, lo, hi):
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise ValueError(f"{contexte} : {nom}={v!r} hors bornes [{lo}, {hi}]")
    return v


def _liste8(contexte, nom, v, lo, hi):
    if not isinstance(v, list) or len(v) != 8:
        raise ValueError(f"{contexte} : {nom} doit être une liste de 8 entiers")
    return [_borne(contexte, f"{nom}[{i}]", x, lo, hi) for i, x in enumerate(v)]


def compiler(spec, sortie):
    """Applique la spec au donneur, écrit sortie, auto-vérifie.
    Rend la liste des diffs [(type, occ, taille_avant, taille_après)]."""
    _cles(spec, _SHOW_CLES, "show")
    if "base" not in spec:
        raise ValueError("show : clé 'base' (donneur .wpj) obligatoire")
    w = wpjlib.Wpj.load(spec["base"])
    cache = {}      # (type, occ) -> dict décodé, réencodé à la fin
    verifs = []     # (type, occ, description, fn(dict décodé) -> bool)

    def rec(typ, occ=0):
        if (typ, occ) not in cache:
            d = wpj_codec.decode(typ, w.get(typ, occ))
            if set(d) == {"raw"}:
                raise ValueError(f"record {typ} occ {occ} : non décodable")
            cache[(typ, occ)] = d
        return cache[(typ, occ)]

    # --- record 101 : nom du projet (device-confirmed, ACC-01) ---
    if "nom" in spec:
        nom = spec["nom"]
        if not isinstance(nom, str) or not nom:
            raise ValueError("show : 'nom' doit être une chaîne non vide")
        rec(101)["nom"] = nom
        verifs.append((101, 0, "nom projet", lambda d, v=nom: d.get("nom") == v))

    # --- record 165 : presets, adressés par id ---
    for pe in spec.get("presets", []):
        _cles(pe, _PRESET_CLES, "preset")
        pid = _borne("preset", "id", pe.get("id", -1), 0, 1 << 31)
        d165 = rec(165)
        cible = next((p for p in d165["presets"]
                      if isinstance(p, dict) and p.get("id", 0) == pid), None)
        if cible is None:
            raise ValueError(f"preset id {pid} : création de preset non "
                             "validée, utiliser un donneur qui a un preset "
                             "à cet id")
        ctx = f"preset id {pid}"
        if "nom" in pe:
            if not isinstance(pe["nom"], str):
                raise ValueError(f"{ctx} : nom doit être une chaîne")
            cible["nom"] = pe["nom"]
        if "positions" in pe:
            cible["positions"] = _liste8(ctx, "positions", pe["positions"],
                                         0, 1 << 31)
        if "dimmers" in pe:
            cible["dimmers"] = _liste8(ctx, "dimmers", pe["dimmers"], 0, 255)
        for fx in _FX_NOMS:
            if fx not in pe:
                continue
            _cles(pe[fx], _FX_CLES, f"{ctx} {fx}")
            for k, v in pe[fx].items():
                _borne(f"{ctx} {fx}", k, v, *_FX_CLES[k])
            if fx not in cible:
                raise ValueError(f"{ctx} : {fx} absent du donneur — création "
                                 "de sous-message FX non validée, utiliser un "
                                 "donneur où ce FX existe")
            cible[fx][0].update(pe[fx])
        attendu = {k: pe[k] for k in pe if k != "id"}
        verifs.append((165, 0, ctx, lambda d, pid=pid, att=attendu:
                       _verif_preset(d, pid, att)))

    # --- record 150 ×8 : positions pan/tilt nommées ---
    for pos in spec.get("positions", []):
        _cles(pos, _POS_CLES, "position")
        page = _borne("position", "page", pos.get("page", 0), 1, 8)
        idx = _borne("position", "index", pos.get("index", -1), 0, 1 << 31)
        d150 = rec(150, page - 1)
        entrees = d150.get("positions", [])
        if idx >= len(entrees) or not isinstance(entrees[idx], dict) or \
                set(entrees[idx]) == {"hex"}:
            raise ValueError(f"position page {page} index {idx} : l'entrée "
                             "doit exister dans le donneur")
        e = entrees[idx]
        ctx = f"position page {page} index {idx}"
        if "nom" in pos:
            if not isinstance(pos["nom"], str):
                raise ValueError(f"{ctx} : nom doit être une chaîne")
            e["nom"] = pos["nom"]
        for cle, champ in _POS_CHAMPS.items():
            if cle in pos:
                e[champ] = _borne(ctx, cle, pos[cle], 0, 65535)
        attendu = {("nom" if k == "nom" else _POS_CHAMPS[k]): v
                   for k, v in pos.items() if k in ("nom",) + tuple(_POS_CHAMPS)}
        verifs.append((150, page - 1, ctx, lambda d, i=idx, att=attendu:
                       all(d["positions"][i].get(k, 0) == v
                           for k, v in att.items())))

    # --- record 135 : palette ColorFX ---
    for pal in spec.get("palette", []):
        _cles(pal, _PAL_CLES, "palette")
        idx = _borne("palette", "index", pal.get("index", -1), 0, 1 << 31)
        d135 = rec(135)
        pads = d135.get("pads", [])
        if idx >= len(pads) or not isinstance(pads[idx], dict) or \
                set(pads[idx]) == {"hex"}:
            raise ValueError(f"palette index {idx} : l'entrée doit exister "
                             "dans le donneur")
        ctx = f"palette index {idx}"
        for k in ("rouge", "vert", "bleu"):
            if k in pal:
                pads[idx][k] = _borne(ctx, k, pal[k], 0, 255)
        attendu = {k: pal[k] for k in ("rouge", "vert", "bleu") if k in pal}
        verifs.append((135, 0, ctx, lambda d, i=idx, att=attendu:
                       all(d["pads"][i].get(k, 0) == v
                           for k, v in att.items())))

    # --- réencodage + écriture (nouveau fichier, jamais d'écrasement) ---
    for (typ, occ), d in cache.items():
        w.replace(typ, wpj_codec.encode(typ, d), occ)
    try:
        w.save(sortie)
    except FileExistsError:
        raise ValueError(f"{sortie} existe déjà — écrasement refusé")

    # --- auto-verify : recharge (SHA-1 revalidé), re-décode, compare ---
    try:
        w2 = wpjlib.Wpj.load(sortie)                 # SHA-1 vérifié par load
        for typ, occ, desc, ok in verifs:
            d = wpj_codec.decode(typ, w2.get(typ, occ))
            if not ok(d):
                raise ValueError(f"auto-verify : {desc} ne relit pas la "
                                 "valeur demandée")
        diffs = verifier(spec["base"], sortie)
        en_trop = [d for d in diffs if (d[0], d[1]) not in cache]
        if en_trop:
            raise ValueError(f"auto-verify : records modifiés hors édition : "
                             f"{en_trop}")
    except Exception:
        os.unlink(sortie)
        raise
    return diffs


def _verif_preset(d165, pid, attendu):
    p = next((p for p in d165["presets"]
              if isinstance(p, dict) and p.get("id", 0) == pid), None)
    if p is None:
        return False
    for k, v in attendu.items():
        if k in _FX_NOMS:
            fx = p.get(k, [{}])[0]
            if any(fx.get(kk, 0) != vv for kk, vv in v.items()):
                return False
        elif p.get(k) != v:
            return False
    return True


def verifier(base, sortie):
    """Rend les records qui diffèrent : [(type, occ, taille_avant, taille_après)]."""
    a, b = wpjlib.Wpj.load(base), wpjlib.Wpj.load(sortie)
    if [t for t, _ in a.records] != [t for t, _ in b.records]:
        raise ValueError("séquences de types différentes : comparaison "
                         "record à record impossible")
    diffs, occs = [], {}
    for (t, pa), (_, pb) in zip(a.records, b.records):
        occ = occs.get(t, 0)
        occs[t] = occ + 1
        if pa != pb:
            diffs.append((t, occ, len(pa), len(pb)))
    return diffs


def _imprime(diffs):
    if not diffs:
        print("aucun record modifié")
    for t, occ, la, lb in diffs:
        print(f"type {t} occ {occ} : {la} -> {lb} octets")


def demo():
    """Cherche un donneur utilisable dans le corpus local ; s'abstient sinon.

    Aucun .wpj n'est distribué avec ce dépôt (docs/corpus.md) : le self-check
    prend le premier fichier variante A du corpus qui porte les emplacements
    édités (preset 80, position page 1 index 1, pad 0).
    """
    for base in wpjlib.corpus_files():
        try:
            return _demo_sur(base)
        except (ValueError, KeyError, StopIteration, OSError):
            continue                      # donneur sans les emplacements voulus
    return wpjlib.pas_de_corpus("wpj_show")


def _demo_sur(base):
    import tempfile
    spec = {"base": base, "nom": "WMX SHOW DEMO",
            "presets": [{"id": 80, "nom": "demo",
                         "beam_fx1": {"effet": 1, "vitesse": 120},
                         "positions": [4, 1, 1, 1, 1, 1, 1, 1],
                         "dimmers": [200] * 8}],
            "positions": [{"page": 1, "index": 1, "nom": "DemoPos",
                           "pan": 12345, "tilt": 54321, "fan": 32768}],
            "palette": [{"index": 0, "rouge": 10, "vert": 20, "bleu": 30}]}
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "demo.wpj")
        diffs = compiler(spec, out)
        assert {(t, o) for t, o, *_ in diffs} == {(101, 0), (165, 0),
                                                 (150, 0), (135, 0)}, diffs
        # relecture indépendante des valeurs demandées
        w = wpjlib.Wpj.load(out)
        assert wpj_codec.decode(101, w.get(101))["nom"] == "WMX SHOW DEMO"
        p = next(p for p in wpj_codec.decode(165, w.get(165))["presets"]
                 if p.get("id", 0) == 80)
        assert p["nom"] == "demo" and p["dimmers"] == [200] * 8
        assert p["beam_fx1"][0]["effet"] == 1 and p["beam_fx1"][0]["vitesse"] == 120
        e = wpj_codec.decode(150, w.get(150, 0))["positions"][1]
        assert e["nom"] == "DemoPos" and e["f6"] == 12345 and e["f7"] == 54321
        assert e["f3"] == 32768
        assert wpj_codec.decode(135, w.get(135))["pads"][0] == \
            {"rouge": 10, "vert": 20, "bleu": 30}
        # spec vide = round-trip octet-identique du donneur
        out2 = os.path.join(tmp, "ident.wpj")
        assert compiler({"base": base}, out2) == []
        assert open(out2, "rb").read() == open(base, "rb").read()
        # erreurs attendues : clé inconnue, entrée absente
        for mauvais in [{"base": base, "fondu": 1},
                        {"base": base, "presets": [{"id": 9999, "nom": "x"}]},
                        {"base": base, "presets": [{"id": 80, "size": 5}]},
                        {"base": base, "palette": [{"index": 999, "rouge": 1}]}]:
            try:
                compiler(mauvais, os.path.join(tmp, "err.wpj"))
                raise AssertionError(f"erreur attendue : {mauvais}")
            except ValueError:
                pass
        assert not os.path.exists(os.path.join(tmp, "err.wpj"))
    print("self-check ok : compile + auto-verify + erreurs sur "
          + os.path.basename(base), file=sys.stderr)


def main(argv):
    if not argv:
        demo()
        return 0
    if argv[0] == "compile" and len(argv) == 3:
        spec = json.load(open(argv[1], encoding="utf-8"))
        _imprime(compiler(spec, argv[2]))
        print(f"ok : {argv[2]}")
        return 0
    if argv[0] == "verify" and len(argv) == 3:
        _imprime(verifier(argv[1], argv[2]))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, KeyError, OSError) as e:
        print(f"erreur : {e}", file=sys.stderr)
        sys.exit(1)
