#!/usr/bin/env python3
"""Identités structurelles du .wpj variante A, vérifiées sur tout le corpus.

Chaque identité est une contrainte arithmétique entre deux records. Elle est
soit vraie partout, soit fausse — donc une lecture qui la casse est réfutée
sans passer par le matériel. Preuve : demo() sur le corpus.

Usage : python3 tools/wpj_identities.py   (depuis la racine du dépôt)
"""
import sys

import wpj_codec
import wpjlib

GOBO_FN = 14          # 111.f3 = fonction « gobo » (registre, type 145)
_ITEMS = {5: ("items", {})}


def _items(w, typ):
    return wpj_codec._decode_msg(w.get(typ), _ITEMS)["items"]


def ranges_par_canal(w):
    """110[c].f2 == taille de la tranche de 111 qui appartient au canal c."""
    c110, c111 = _items(w, 110), _items(w, 111)
    debuts = [c.get("f3", 0) for c in c110] + [len(c111)]
    for i, c in enumerate(c110):
        assert c.get("f2", 0) == debuts[i + 1] - debuts[i], \
            f"110[{i}].f2 = {c.get('f2', 0)} mais la tranche fait " \
            f"{debuts[i + 1] - debuts[i]}"


def palette_gobo(w):
    """Les f2 du type 145 == les f4 des plages gobo de 111, dans l'ordre."""
    ids = [e["f4"] for e in _items(w, 111)
           if e.get("f3") == GOBO_FN and "f4" in e]
    palette = [it["f2"]
               for typ, payload in w.records if typ == 145
               for it in wpj_codec._decode_msg(payload, _ITEMS)["items"]
               if "f2" in it]
    assert palette == ids, f"palette {palette} != ids gobo {ids}"


IDENTITES = (ranges_par_canal, palette_gobo)


def demo():
    files = wpjlib.corpus_files()
    if not files:
        return wpjlib.pas_de_corpus("wpj_identities")
    n = 0
    for path in files:
        try:
            w = wpjlib.Wpj.load(path)
        except (ValueError, OSError):
            continue                      # variantes B/C : hors périmètre
        n += 1
        for verif in IDENTITES:
            try:
                verif(w)
            except AssertionError as e:
                raise AssertionError(f"{path} : {verif.__name__} : {e}") from None
    if not n:
        return wpjlib.pas_de_corpus("wpj_identities")
    print(f"{len(IDENTITES)} identités vérifiées sur {n} fichiers variante A",
          file=sys.stderr)


if __name__ == "__main__":
    demo()
