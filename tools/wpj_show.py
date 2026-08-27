#!/usr/bin/env python3
"""Compilateur de show minimal, template-based (sur wpjlib + wpj_codec).

Principe : on part TOUJOURS d'un projet donneur variante A existant et on
applique une spec JSON d'édition. Tout ce que la spec ne nomme pas est
préservé octet pour octet par wpjlib. Une position et une entrée de palette
éditées doivent exister dans le donneur ; un preset peut en plus être **créé
en queue** en clonant un preset du donneur (clé `modele`) — l'ajout d'une
entrée `165.f5` avec l'id suivant est device-confirmed, `165.f1` reste
verbatim (registre, PRESET-01).
Périmètre v1 = champs à statut ≥ correlated uniquement (records 101, 165,
150, 135) ; size/fade/phase (f8/f6/f9, attribution hypothesized) exclus.

Usage :
  wpj_show.py compile show.json sortie.wpj   compile + auto-verify
  wpj_show.py verify base.wpj sortie.wpj     liste les records qui diffèrent
  wpj_show.py                                self-check (corpus, sans trace)
"""
import copy
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
_PRESET_CLES = ("id", "modele", "nom", "positions", "dimmers",
                "masque_contenu", "pattern_couleur",
                "couleur_statique") + _FX_NOMS
NOM_MAX_OCTETS = 19          # au-delà, le projet entier refuse de s'ouvrir
NB_GROUPES = 8               # A–H
PADS_PAR_GROUPE = 20         # un masque de 20 bits par groupe dans f31
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


def _pads_vers_masques(contexte, pads8):
    """8 listes de numéros de pad (1–20) → les 20 octets packés de `f31`.

    `f31` = 20 varints = 160 bits en petit-boutien, découpés en huit masques
    de 20 bits (un par groupe A–H) ; le bit n du groupe g allume le pad n+1
    de la palette 140 de ce groupe — device-confirmed.
    """
    if not isinstance(pads8, list) or len(pads8) != NB_GROUPES:
        raise ValueError(f"{contexte} : couleur_statique doit être "
                         f"{NB_GROUPES} listes de numéros de pad (1–"
                         f"{PADS_PAR_GROUPE}), une par groupe A–H")
    bits = 0
    for g, pads in enumerate(pads8):
        if not isinstance(pads, list):
            raise ValueError(f"{contexte} : couleur_statique[{g}] doit être "
                             "une liste de numéros de pad")
        for pad in pads:
            _borne(contexte, f"couleur_statique[{g}]", pad, 1, PADS_PAR_GROUPE)
            bits |= 1 << (g * PADS_PAR_GROUPE + pad - 1)
    return list(bits.to_bytes(NB_GROUPES * PADS_PAR_GROUPE // 8, "little"))


def masques_vers_pads(v20):
    """Inverse de _pads_vers_masques : les 20 octets → 8 listes de pads."""
    if not isinstance(v20, list) or any(not isinstance(x, int) or not 0 <= x < 256
                                        for x in v20):
        return None                      # f31 illisible : pas d'interprétation
    bits = int.from_bytes(bytes(v20), "little")
    return [[p + 1 for p in range(PADS_PAR_GROUPE)
             if bits >> (g * PADS_PAR_GROUPE + p) & 1]
            for g in range(NB_GROUPES)]


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
        ctx = f"preset id {pid}"
        cible = next((p for p in d165["presets"]
                      if isinstance(p, dict) and p.get("id", 0) == pid), None)
        if cible is None:
            cible = _cree_preset(ctx, d165, pid, pe)
        elif "modele" in pe:
            raise ValueError(f"{ctx} : déjà présent dans le donneur, "
                             "'modele' ne s'applique qu'à une création")
        if "nom" in pe:
            if not isinstance(pe["nom"], str):
                raise ValueError(f"{ctx} : nom doit être une chaîne")
            octets = len(pe["nom"].encode("utf-8"))
            if octets > NOM_MAX_OCTETS:
                raise ValueError(f"{ctx} : nom de {octets} octets UTF-8 > "
                                 f"{NOM_MAX_OCTETS} — le projet ENTIER "
                                 "refuserait de s'ouvrir (PRESET-05)")
            cible["nom"] = pe["nom"]
        if "positions" in pe:
            cible["positions"] = _liste8(ctx, "positions", pe["positions"],
                                         0, 1 << 31)
        if "dimmers" in pe:
            cible["dimmers"] = _liste8(ctx, "dimmers", pe["dimmers"], 0, 255)
        if "masque_contenu" in pe:
            cible["masque_contenu"] = _borne(ctx, "masque_contenu",
                                             pe["masque_contenu"], 0, 63)
        if "pattern_couleur" in pe:
            cible["pattern_couleur"] = _liste8(ctx, "pattern_couleur",
                                               pe["pattern_couleur"], 0, 10)
        if "couleur_statique" in pe:
            cible["couleur_statique"] = _pads_vers_masques(
                ctx, pe["couleur_statique"])
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
        attendu = {k: (_pads_vers_masques(ctx, v)
                       if k == "couleur_statique" else v)
                   for k, v in pe.items() if k not in ("id", "modele")}
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


def _cree_preset(ctx, d165, pid, pe):
    """Crée un preset en queue de `165.f5` en clonant `modele`.

    Device-confirmed (registre, PRESET-01/06/07) : appendre une entrée
    bien formée avec un id libre suffit — l'appareil la stocke, l'affiche,
    la rappelle et la conserve à travers store, RESTART et réouverture à
    froid. `165.f1` ne garde rien (81 avec 85 entrées) : laissé verbatim.
    Les trous d'id se chargent ; l'id doit rester croissant, donc la
    création se fait en queue, comme les deux ajouts mesurés.
    """
    if "modele" not in pe:
        raise ValueError(f"{ctx} : absent du donneur — donner 'modele' "
                         "(id du preset à cloner) pour le créer en queue")
    mid = _borne(ctx, "modele", pe["modele"], 0, 1 << 31)
    modele = next((p for p in d165["presets"]
                   if isinstance(p, dict) and p.get("id", 0) == mid), None)
    if modele is None:
        raise ValueError(f"{ctx} : modèle {mid} absent du donneur")
    if "id" not in modele:
        raise ValueError(f"{ctx} : le modèle {mid} n'écrit pas son id "
                         "(l'id 0 omet le champ) — choisir un autre modèle")
    maxi = max(p.get("id", 0) for p in d165["presets"] if isinstance(p, dict))
    if pid <= maxi:
        raise ValueError(f"{ctx} : création en queue seulement, l'id doit "
                         f"dépasser {maxi} (le plus grand du donneur)")
    if pid > 127:
        print(f"attention : {ctx} — aucun preset d'id > 127 n'a jamais été "
              "mesuré sur l'appareil", file=sys.stderr)
    cible = copy.deepcopy(modele)
    cible["id"] = pid
    d165["presets"].append(cible)
    return cible


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
    ids = [p.get("id", 0) for p in
           wpj_codec.decode(165, wpjlib.Wpj.load(base).get(165))["presets"]]
    neuf = max(ids) + 3                       # création en queue, avec un trou
    spec = {"base": base, "nom": "WMX SHOW DEMO",
            "presets": [{"id": 80, "nom": "demo",
                         "beam_fx1": {"effet": 1, "vitesse": 120},
                         "positions": [4, 1, 1, 1, 1, 1, 1, 1],
                         "dimmers": [200] * 8},
                        {"id": neuf, "modele": 23, "nom": "cree",
                         "masque_contenu": 24, "dimmers": [128] * 8,
                         "pattern_couleur": [9] * 8,
                         "couleur_statique": [[6]] * 2 + [[]] * 6}],
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
        # le preset créé : cloné, en queue, relu champ par champ
        presets = wpj_codec.decode(165, w.get(165))["presets"]
        c = presets[-1]
        assert c["id"] == neuf and c["nom"] == "cree", c.get("id")
        assert c["masque_contenu"] == 24 and c["dimmers"] == [128] * 8
        assert masques_vers_pads(c["couleur_statique"]) == \
            [[6], [6], [], [], [], [], [], []]
        modele = next(p for p in presets if p.get("id", 0) == 23)
        assert {k: v for k, v in c.items() if k not in
                ("id", "nom", "masque_contenu", "dimmers", "pattern_couleur",
                 "couleur_statique")} == \
               {k: v for k, v in modele.items() if k not in
                ("id", "nom", "masque_contenu", "dimmers", "pattern_couleur",
                 "couleur_statique")}, "le clone doit être le modèle verbatim"
        # spec vide = round-trip octet-identique du donneur
        out2 = os.path.join(tmp, "ident.wpj")
        assert compiler({"base": base}, out2) == []
        assert open(out2, "rb").read() == open(base, "rb").read()
        # erreurs attendues : clé inconnue, entrée absente
        for mauvais in [{"base": base, "fondu": 1},
                        {"base": base, "presets": [{"id": 9999, "nom": "x"}]},
                        {"base": base, "presets": [{"id": 80, "size": 5}]},
                        {"base": base, "palette": [{"index": 999, "rouge": 1}]},
                        # nom de 20 octets : tueur device-confirmed
                        {"base": base, "presets": [{"id": 80,
                                                    "nom": "a" * 20}]},
                        # création sous l'id le plus grand du donneur
                        {"base": base, "presets": [{"id": 1, "modele": 23}]},
                        # 'modele' sur un preset qui existe déjà
                        {"base": base, "presets": [{"id": 80, "modele": 23}]},
                        # pad hors de la grille de 20
                        {"base": base, "presets": [
                            {"id": neuf, "modele": 23,
                             "couleur_statique": [[21]] + [[]] * 7}]}]:
            try:
                compiler(mauvais, os.path.join(tmp, "err.wpj"))
                raise AssertionError(f"erreur attendue : {mauvais}")
            except ValueError:
                pass
        assert not os.path.exists(os.path.join(tmp, "err.wpj"))
    print("self-check ok : compile + création + auto-verify + erreurs sur "
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
