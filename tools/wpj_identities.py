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


def _varints(hexa):
    """Octets d'un champ « packed varint » : la liste des valeurs décodées."""
    out, v, sh = [], 0, 0
    for c in bytes.fromhex(hexa):
        v |= (c & 0x7f) << sh
        if c & 0x80:
            sh += 7
        else:
            out.append(v); v, sh = 0, 0
    return out


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


def tranches_106(w):
    """105.f4/f7 = tranche du record 106, pas une adresse DMX.

    Les intervalles [f4, f4+f7) pavent exactement [0, count(106)), et chaque
    entrée de 106 tombe dans la fenêtre DMX de sa fixture. Une lecture de f4
    comme adresse DMX de départ casse les deux (registre, « record 105 »).
    """
    p105, p106 = _items(w, 105), _items(w, 106)
    p115, p116 = _items(w, 115), _items(w, 116)
    pos = 0
    for e in sorted(p105, key=lambda e: (e.get("f4", 0), e.get("f7", 0))):
        assert e.get("f4", 0) == pos, \
            f"105 : tranche à {e.get('f4', 0)} mais {pos} entrées de 106 consommées"
        pos += e.get("f7", 0)
    assert pos == len(p106), f"105 : Σf7 = {pos} != count(106) = {len(p106)}"
    for e in p105:
        f = p115[e.get("f5", 0)]
        base = f.get("f2", 0)
        span = p116[f.get("f3", 0)].get("f2", 0)
        for k in range(e.get("f4", 0), e.get("f4", 0) + e.get("f7", 0)):
            canal = p106[k].get("f2", 0)
            assert base <= canal < base + span, \
                f"106[{k}].f2 = {canal} hors de la fenêtre DMX " \
                f"[{base}, {base + span}) de la fixture {e.get('f5', 0)}"


def patch_disjoint(w):
    """115.f2 = adresse DMX de départ : les fenêtres ne se recouvrent pas."""
    p115, p116 = _items(w, 115), _items(w, 116)
    fen = sorted((f.get("f2", 0), p116[f.get("f3", 0)].get("f2", 0)) for f in p115)
    for (a, n), (b, _) in zip(fen, fen[1:]):
        assert a + n <= b, f"fenêtres DMX qui se recouvrent : {a}+{n} > {b}"


def groupe_fixture(w):
    """115.f4 == 105.f6 == l'index de groupe de la fixture, et 125 en découle.

    Deux records portent l'affectation, redondants : 115[r].f4 par fixture et
    105[e].f6 par entrée de patch. Le masque 125[i].f4 (6 octets, LE) est le OU
    des 1 << 115[r].f3 des fixtures du slot i — donc un slot qui mélange deux
    profils y allume deux bits. Neuf slots : A–H plus un 9e (index 8).
    """
    p105, p115 = _items(w, 105), _items(w, 115)
    p125 = _items(w, 125)
    assert len(p125) == 9, f"125 : {len(p125)} slots au lieu de 9"
    for e in p105:
        r = e.get("f5", 0)
        assert e.get("f6", 0) == p115[r].get("f4", 0), \
            f"105 : fixture {r} en groupe {e.get('f6', 0)} mais 115.f4 = " \
            f"{p115[r].get('f4', 0)}"
    for i, slot in enumerate(p125):
        attendu = 0
        for f in p115:
            if f.get("f4", 0) == i:
                attendu |= 1 << f.get("f3", 0)
        masque = int.from_bytes(bytes.fromhex(slot["f4"]["hex"])[:6], "little")
        assert masque == attendu, \
            f"125[{i}] : masque {masque:#x} != profils du groupe {attendu:#x}"


def moteurs_f16(w):
    """165.f16 = douze masques de groupes de 9 bits, un par « moteur ».

    Les varints packés sont les octets d'un champ de bits little-endian
    découpé en tranches de **9** bits — 9 et non 8, parce que le record 125
    a neuf slots : les groupes A–H plus celui des effets. L'alignement se
    teste tout seul : à 9 bits le moteur 1 vaut exactement `move_fx_actif`
    sur tout le corpus, à 8 bits il vaudrait 254 là où `move_fx_actif` vaut
    255. Voir le registre, « f16 ».
    """
    for pre in _items(w, 165):
        h = pre.get("f16")
        if not h:
            continue
        oct_ = _varints(h["hex"])
        assert all(o < 256 for o in oct_), \
            f"165.f16 : varint hors d'un octet dans {h['hex']}"
        gros = int.from_bytes(bytes(oct_), "little")
        for m in range(12):
            assert not (gros >> (9 * m)) & 0x100, \
                f"165.f16 : moteur {m} allume le 9e slot dans {h['hex']}"
        actif = _varints(pre.get("f24", {}).get("hex", ""))
        assert (gros >> 9) & 0x1FF == (actif[0] if actif else 0), \
            f"165.f16 : moteur 1 = {(gros >> 9) & 0x1FF} != move_fx_actif " \
            f"{actif} dans {h['hex']}"


def plages_111(w):
    """111.f1/f2 = bornes DMX d'une plage, et tout canal tombe dans un cas.

    Trichotomie exhaustive sur le corpus : un canal de 110 est soit
    **non attribué** (pas de `f4`, une unique plage vide), soit le motif
    isolé `f4 = 18` (une unique plage `{f1: 255, f3: 41}`), soit ses plages
    **pavent [0, 255]** — `f1` du premier à 0, `f1` de chacune suivant le
    `f2` de la précédente, `f2` de la dernière à 255.
    """
    c110, c111 = _items(w, 110), _items(w, 111)
    pos = 0
    for i, c in enumerate(c110):
        n = c.get("f2", 0)
        tr, pos = c111[pos:pos + n], pos + n
        if n == 1 and not tr[0]:
            assert "f4" not in c, \
                f"110[{i}] : plage vide mais le canal porte f4 = {c['f4']}"
            continue
        att = 0
        for r in tr:
            if r.get("f1", 0) != att:
                break
            att = r.get("f2", 0) + 1
        else:
            if att == 256:
                continue                       # le cas courant : les plages pavent
        assert c.get("f4") == 18 and n == 1 and tr[0] == {"f1": 255, "f3": 41}, \
            f"110[{i}] : plages ni pavantes ni du motif f4 = 18 : {tr}"


IDENTITES = (ranges_par_canal, palette_gobo, tranches_106, patch_disjoint,
              groupe_fixture, moteurs_f16, plages_111)


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
