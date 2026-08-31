#!/usr/bin/env python3
"""Lecteur des variantes B et C du .wpj (sérialisation WTOOLS). LECTURE SEULE.

Trois dispositions partagent l'extension .wpj (registre, « Trois variantes ») :
  A  SHA-1 + conteneur TLV        — dumps appareil ; wpjlib/wpj_codec
  B  SHA-1 + protobuf à l'offset 20 — projets WTOOLS courants (champ 1 = 7 ou 8)
  C  protobuf nu à l'offset 0       — projets WTOOLS anciens (champ 1 = 6)

B et C portent le MÊME schéma top-level : C est une version antérieure du même
format, pas une autre disposition. Ce module rend ce schéma lisible au niveau
des champs identifiés (registre, « Variant B/C top-level map ») et laisse le
reste en hex verbatim. Aucune écriture : la règle « lecture avant écriture »
tient tant que le round-trip différentiel et l'acceptation aval n'existent pas.

Usage :
  wpj_bc.py fichier.wpj      décode en JSON sur stdout
  wpj_bc.py                  self-check sur le corpus (abstention sans corpus)
"""
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpj_wire
import wpjlib


def variante(data):
    """'A', 'B', 'C' ou None (fichier non reconnu)."""
    if len(data) > 0x46 and data[:20] == hashlib.sha1(data[20:]).digest():
        if int.from_bytes(data[0x44:0x46], "little") == 100:
            return "A"
        return "B"
    try:
        _walk_top(data)
        return "C"
    except ValueError:
        return None


def charger(path):
    """(variante, corps protobuf) d'un fichier B ou C. ValueError sur A/illisible."""
    data = open(path, "rb").read()
    v = variante(data)
    if v == "A":
        raise ValueError("variante A : utiliser wpjlib/wpj_codec")
    if v is None:
        raise ValueError("ni TLV ni protobuf : fichier non reconnu")
    return v, (data[20:] if v == "B" else data)


def _walk_top(body):
    """[(champ, wt, valeur|octets)] au niveau 0, sans descendre.

    Le lecteur de production fait exactement ça, et ses refus sont nommés.
    """
    return list(wpj_wire.fields(body))


def _msg(chunk):
    """Sous-message → dict {champ: valeur} ; répétition → liste. Varints et str seuls."""
    out = {}
    for f, wt, v in _walk_top(chunk):
        if wt == 2:
            try:
                s = v.decode("utf-8")
                v = s if s.isprintable() or s == "" else {"hex": v.hex()}
            except UnicodeDecodeError:
                v = {"hex": v.hex()}
        if f in out:
            if not isinstance(out[f], list):
                out[f] = [out[f]]
            out[f].append(v)
        else:
            out[f] = v
    return out


def _packed(chunk):
    out, i = [], 0
    while i < len(chunk):
        v, i = wpj_wire.read_varint(chunk, i)
        out.append(v)
    return out


def _str(chunk, f):
    d = _msg(chunk)
    return d.get(f) if isinstance(d.get(f), str) else None


def projet_vers_dict(path):
    """Décode les champs identifiés (statuts : registre) ; le reste en compteurs."""
    var, body = charger(path)
    top = {}
    for f, wt, v in _walk_top(body):
        top.setdefault(f, []).append((wt, v))

    def uns(f):
        e = top.get(f)
        return e[0][1] if e and e[0][0] == 0 else None

    def blobs(f):
        return [v for wt, v in top.get(f, []) if wt == 2]

    profils = []
    for b in blobs(13):
        d = _msg(b)
        h = d.get(3)
        profils.append({"name": d.get(2), "hash": h["hex"] if isinstance(h, dict) else h,
                        "channel_count": d.get(5), "timestamp": d.get(11)})
    patch = []
    for b in blobs(12):
        d = _msg(b)
        patch.append({"profile": d.get(2, 0), "adresse_base0": d.get(3, 0),
                      "group": d.get(4, 0), "f6": d.get(6)})
    # Presets (EXP-06) : les tableaux de 81 o sont des banques PAR EFFET —
    # ligne e = tuple de l'effet e : [vitesse, ?, phase, fade, size, ?, fan,
    # bpm_division, link_order]. Les tableaux de 8 o sont par groupe A-H.
    presets = []
    for b in blobs(3):
        d = _msg(b)
        pr = {"name": d.get(1)}
        for f, nom in ((13, "banque_beam"), (5, "banque_color"), (9, "banque_move")):
            v = d.get(f)
            if isinstance(v, dict) and len(bytes.fromhex(v["hex"])) == 81:
                raw = bytes.fromhex(v["hex"])
                pr[nom] = [list(raw[i:i + 9]) for i in range(0, 81, 9)]
        for f, nom in ((24, "positions"), (25, "gobos"), (21, "color_pattern"),
                       (26, "gobo_rotate"), (8, "color_actif"), (12, "move_actif")):
            v = d.get(f)
            if isinstance(v, dict):
                pr[nom] = list(bytes.fromhex(v["hex"]))
        presets.append(pr)
    positions = []
    for b in blobs(6):
        d = _msg(b)
        positions.append({"name": d.get(5), "pan": d.get(1), "tilt": d.get(2),
                          "f6": d.get(6), "f7": d.get(7)})
    edits = []
    for b in blobs(7):
        d = _msg(b)
        edits.append({"name": d.get(1)})
    gobos = []
    for f in (9, 31):
        for b in blobs(f):
            d = _msg(b)
            lst = d.get(1)
            vals = _packed(bytes.fromhex(lst["hex"])) if isinstance(lst, dict) else []
            gobos.append({"name": d.get(2), "glyph": d.get(3),
                          "valeur_par_profil": {i: x for i, x in enumerate(vals) if x != 65535}})
    groupes = [{"name": _msg(b).get(1)} for b in blobs(10)]
    noms = blobs(2)
    if not noms:
        raise ValueError(f"{path} : champ 2 (nom du projet) absent")
    autres = sorted(f for f in top if f not in
                    (1, 2, 3, 6, 7, 9, 10, 12, 13, 31))
    return {
        "fichier": path, "variante": var, "version_format": uns(1),
        "name": noms[0].decode("utf-8", "replace"),
        "profiles": profils, "patch": patch, "groups": groupes,
        "presets": presets, "positions": positions, "edits": edits, "gobos": gobos,
        "nb_canaux_patches": uns(23),
        "champs_non_identifies": {f"f{f}": len(top[f]) for f in autres},
    }


# --- self-check : le treillis d'identités du registre, sur tout le corpus ----

def _identites(body):
    top = {}
    for f, wt, v in _walk_top(body):
        top.setdefault(f, []).append((wt, v))
    n = lambda f: sum(1 for wt, _ in top.get(f, []) if wt == 2)
    uns = lambda f: next((v for wt, v in top.get(f, []) if wt == 0), None)
    def blob(f):
        trouve = next((v for wt, v in top.get(f, []) if wt == 2), None)
        if trouve is None:
            raise ValueError(f"champ {f} absent : fichier B/C incomplet")
        return trouve

    prof_ch = [_msg(b).get(5, 0)
               for b in (v for wt, v in top.get(13, []) if wt == 2)]
    occupe = set()
    for b in (v for wt, v in top.get(12, []) if wt == 2):
        d = _msg(b)
        p, adr = d.get(2, 0), d.get(3, 0)
        occupe.update(range(adr, adr + (prof_ch[p] if p < len(prof_ch) else 0)))
    f15 = [v for wt, v in top.get(15, []) if wt == 2]
    assert uns(1) in (6, 7, 8), "champ 1 hors 6/7/8"
    assert n(3) == 100 and uns(33) == 100, "presets ≠ 100"
    assert len(f15) == 2048, "f15 ≠ 2048"
    assert uns(18) == n(12) and uns(19) == n(13), "compteurs f18/f19"
    assert uns(20) == n(14) and uns(21) == n(17), "compteurs f20/f21"
    assert uns(22) == n(11) == n(29), "compteur f22"
    assert uns(23) == len(occupe), "f23 ≠ canaux patchés"
    assert {i for i, o in enumerate(blob(16)) if o} == occupe, "masque f16"
    assert {i for i, c in enumerate(f15) if c} <= occupe, "f15 hors patch"
    assert sum(1 for o in blob(25) if o) == n(12), "f25 ≠ nb fixtures"
    assert sum(1 for o in blob(26) if o) == n(13), "f26 ≠ nb profils"
    assert sum(1 for o in blob(27) if o) == n(14), "f27 ≠ nb entrées f14"


def _refus():
    """Les refus qui ne dépendent d'aucun corpus — et qui tiennent sous -O.

    Ces cas vivent ici parce que `wpj_bc` est déjà dans `make check` et lit le
    wire de bout en bout ; le conteneur lui-même est couvert par le self-check
    de `wpj_wire`.
    """
    for tronque in (b"\x0d\x01\x02", b"\x09\x01\x02\x03"):
        try:
            _walk_top(tronque)
            raise AssertionError(f"bloc fixe tronqué accepté : {tronque!r}")
        except ValueError:
            pass
    entete = hashlib.sha1(b"").digest()
    # Le conteneur lui-même est couvert par le self-check de wpj_wire ; ici on
    # vérifie seulement que wpj_bc passe bien par lui.
    try:
        wpj_wire.parse_container(entete)
        raise AssertionError("conteneur trop court accepté")
    except wpj_wire.WireError:
        pass
    # Un blob obligatoire absent se nomme, au lieu de lever un IndexError.
    import tempfile
    with tempfile.TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "sans-nom.wpj")
        with open(chemin, "xb") as flux:
            flux.write(b"\x08\x06")          # champ 1 = 6, et rien d'autre
        try:
            projet_vers_dict(chemin)
            raise AssertionError("projet sans nom accepté")
        except ValueError as err:
            assert "champ 2" in str(err), err


def demo():
    _refus()
    files = wpjlib.corpus_files()
    if not files:
        return wpjlib.pas_de_corpus("wpj_bc")
    nb = {"B": 0, "C": 0}
    for path in files:
        data = open(path, "rb").read()
        v = variante(data)
        if v in ("B", "C"):
            _identites(data[20:] if v == "B" else data)
            projet_vers_dict(path)
            nb[v] += 1
    if not nb["B"] and not nb["C"]:
        print("wpj_bc : ignoré, aucun fichier B/C dans le corpus")
        return
    print(f"treillis d'identités vérifié sur {nb['B']} fichiers B et {nb['C']} fichier(s) C")


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("projet", nargs="?", help="decode un projet variante B ou C en JSON ; sans argument, self-check")
    args = parseur.parse_args(argv)
    if args.projet is None:
        demo()
        return 0
    print(json.dumps(projet_vers_dict(args.projet), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
