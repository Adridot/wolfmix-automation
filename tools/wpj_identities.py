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


def _items(w, typ, occurrence=0):
    return wpj_codec._decode_msg(w.get(typ, occurrence), _ITEMS)["items"]


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


# 106.f4 = rôle du canal dans le moteur du W1, en bijection avec la
# « feature » 110.f4 du profil. Table observée sur tout le corpus ; un rôle
# inconnu doit faire échouer l'identité plutôt que passer inaperçu.
ROLES_106 = {0: 7, 1: 1, 2: 2, 3: 25, 4: 26, 5: 27, 6: 31, 7: 32, 8: 33,
             9: 15, 10: 15, 11: 5, 12: 8, 14: 22, 15: 16, 21: 20, 22: 19}


def roles_106(w):
    """106.f4 = rôle moteur du canal ; il détermine la feature 110.f4.

    Chaque entrée de 106 vise un canal du profil de sa fixture, via
    `106.f2 - 115.f2` ajouté à l'offset `116.f3`. Le rôle et la feature de ce
    canal se correspondent alors terme à terme sur tout le corpus — c'est ce
    qui rend lisible « quel canal DMX porte le rouge de cette fixture ».
    """
    p105, p106 = _items(w, 105), _items(w, 106)
    p110, p115, p116 = _items(w, 110), _items(w, 115), _items(w, 116)
    for e in p105:
        fx = p115[e.get("f5", 0)]
        base = fx.get("f2", 0)
        off = p116[fx.get("f3", 0)].get("f3", 0)
        for k in range(e.get("f4", 0), e.get("f4", 0) + e.get("f7", 0)):
            ent = p106[k]
            role = ent.get("f4", 0)
            feat = p110[off + ent.get("f2", 0) - base].get("f4")
            assert role in ROLES_106, f"106 : rôle inconnu {role}"
            assert ROLES_106[role] == feat, \
                f"106 : rôle {role} sur la feature {feat}, " \
                f"attendu {ROLES_106[role]}"


def ordre_fixtures_115(w):
    """115.f6 = une permutation complète des index de fixtures.

    Un octet par fixture, chaque index exactement une fois. Ce n'est ni le
    tri par groupe ni le tri par profil — les deux marchent sur une partie du
    corpus seulement, et sur des parties complémentaires. C'est un ordre
    d'affichage propre au projet. Voir le registre, « record 115 ».
    """
    d = wpj_codec._decode_msg(w.get(115), {5: ("items", {}), 6: ("ordre", "hex")})
    if "ordre" not in d:
        return
    o = d["ordre"]
    liste = list(bytes.fromhex(o if isinstance(o, str) else o["hex"]))
    assert sorted(liste) == list(range(len(d["items"]))), \
        f"115.f6 : {liste} n'est pas une permutation de 0..{len(d['items']) - 1}"


# Fonction 111.f3 de la plage que chaque rôle 106 utilise, quand il en vise
# une seule. Les roues (11, 12) n'en visent aucune et les rôles 1/2/10/21/22
# débordent ou portent une constante — voir le registre, « record 106 f1/f3 ».
PLAGE_DU_ROLE = {0: 12, 3: 50, 4: 51, 5: 52, 6: 56, 7: 57, 8: 58,
                 9: 34, 14: 48, 15: 38}


def bornes_106(w):
    """106.f1/f3 = les bornes DMX de la plage que le rôle pilote.

    Quand `[f1, f3]` coïncide avec une plage de 111 du canal — 2643 entrées du
    corpus sur 3775 — la fonction de cette plage est celle qu'impose le rôle :
    le rôle « rouge » tombe sur la plage `f3 = 50`, « dimmer » sur `12`, et
    ainsi de suite. L'identité ne contraint que ce cas ; les autres motifs sont
    décrits au registre et volontairement laissés libres.
    """
    p105, p106 = _items(w, 105), _items(w, 106)
    p110, p111 = _items(w, 110), _items(w, 111)
    p115, p116 = _items(w, 115), _items(w, 116)
    deb = [c.get("f3", 0) for c in p110]
    for e in p105:
        fx = p115[e.get("f5", 0)]
        base = fx.get("f2", 0)
        off = p116[fx.get("f3", 0)].get("f3", 0)
        for k in range(e.get("f4", 0), e.get("f4", 0) + e.get("f7", 0)):
            ent = p106[k]
            ci = off + ent.get("f2", 0) - base
            tranche = p111[deb[ci]:deb[ci] + p110[ci].get("f2", 0)]
            cible = (ent.get("f1", 0), ent.get("f3", 0))
            for r in tranche:
                if (r.get("f1", 0), r.get("f2", 0)) != cible:
                    continue
                role = ent.get("f4", 0)
                if role in PLAGE_DU_ROLE:
                    assert r.get("f3") == PLAGE_DU_ROLE[role], \
                        f"106 : rôle {role} sur la plage {r.get('f3')}, " \
                        f"attendu {PLAGE_DU_ROLE[role]}"
                break


def tranches_151(w):
    """150[slot].f2/f1 = tranche du record 151, et les tranches le pavent.

    Même construction que `105.f4/f7` dans 106 et `116.f3/f2` dans 110 : un
    couple (offset, longueur) qui découpe une liste plate. Les slots de
    position qui n'en utilisent pas ne portent ni `f1` ni `f2`. Voir le
    registre, « record 151 ».
    """
    n151 = len(_items(w, 151)) if w.get(151) else 0
    vus = []
    for g in range(8):
        for i, slot in enumerate(_items(w, 150, g)):
            if "f1" not in slot and "f2" not in slot:
                continue
            vus.append((slot.get("f2", 0), slot.get("f1", 0), g, i))
    pos = 0
    for debut, n, g, i in sorted(vus):
        assert debut == pos, \
            f"150[{'ABCDEFGH'[g]}][{i + 1}] : tranche à {debut} mais " \
            f"{pos} entrées de 151 consommées"
        pos += n
    assert pos == n151, f"151 : {pos} entrées référencées, {n151} présentes"


IDENTITES = (ranges_par_canal, palette_gobo, tranches_106, patch_disjoint,
              groupe_fixture, moteurs_f16, plages_111, roles_106,
              ordre_fixtures_115, bornes_106, tranches_151)


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
