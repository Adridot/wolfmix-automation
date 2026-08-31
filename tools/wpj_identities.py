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
    255. Voir le registre, « f16 » et « FLASH-01 ».
    """
    for pre in _items(w, 165):
        h = pre.get("f16")
        if not h:
            continue
        oct_ = _varints(h["hex"])
        assert all(o < 256 for o in oct_), \
            f"165.f16 : varint hors d'un octet dans {h['hex']}"
        gros = int.from_bytes(bytes(oct_), "little")
        # Le 9e bit — le slot des effets — n'est allumé que par les moteurs
        # flash, à partir de la tranche 6 : WOLF frappe tout, fumigène compris.
        # Voir le registre, « FLASH-01 ».
        for m in range(6):
            assert not (gros >> (9 * m)) & 0x100, \
                f"165.f16 : moteur {m} allume le 9e slot dans {h['hex']}"
        actif = _varints(pre.get("f24", {}).get("hex", ""))
        assert (gros >> 9) & 0x1FF == (actif[0] if actif else 0), \
            f"165.f16 : moteur 1 = {(gros >> 9) & 0x1FF} != move_fx_actif " \
            f"{actif} dans {h['hex']}"


def tranche5_f16(w):
    """165.f16 tranche 5 == le masque des groupes dont le dimmer f17 est non nul.

    Le registre lisait « tranche 5 = 255 toujours » sur 2446 presets. C'était
    le piège de l'uniformité : dans tout le corpus, `f17` vaut [255]×8, donc le
    masque vaut 255 et rien ne pouvait varier. Le graveur de l'appareil l'a
    cassé en récrivant un fichier que nous avions écrit (registre, « GEN-03
    retiré ») : sur des cues qui n'allument qu'un groupe, il a mis la tranche 5
    à 2 = B, et à 7 = A+B+C sur celles qui en allument trois.

    Contestation levée le 2026-08-27 (registre, « FX2-01 mesuré ») : sur un
    preset que L'APPAREIL a créé de zéro — pas un clone du nôtre — la tranche 5
    vaut 2 = B, exactement le seul groupe dont `f17` est non nul, alors que le
    moteur faisceau est ÉTEINT. La lecture rivale « tranche 5 = masque de
    Beam FX 2 » ne survit pas à ça.

    L'identité est donc trivialement vraie sur le corpus et discriminante sur
    tout fichier où un preset n'allume pas tous les groupes — le nôtre, ou
    n'importe quel projet où l'opérateur a éteint un groupe dans un preset.
    Déposez-en un dans `corpus/` et cette assertion le vérifiera.
    """
    for pre in _items(w, 165):
        h, d = pre.get("f16"), pre.get("f17")
        if not h or not d:
            continue
        gros = int.from_bytes(bytes(_varints(h["hex"])), "little")
        tranche = (gros >> (9 * 5)) & 0x1FF
        dimmers = _varints(d["hex"])
        attendu = sum(1 << i for i, v in enumerate(dimmers[:8]) if v)
        assert tranche == attendu, \
            f"165.f16 : tranche 5 = {tranche} mais les dimmers non nuls " \
            f"donnent {attendu} ({dimmers})"


def plages_111(w):
    """111.f1/f2 = bornes DMX d'une plage, et tout canal tombe dans un cas.

    Trichotomie exhaustive sur le corpus : un canal de 110 est soit
    **non attribué** (pas de `f4`, une unique plage vide), soit le motif
    isolé `f4 = 18` (une unique plage `{f1: 255, f3: 41}`), soit ses plages
    **pavent [0, 255]** — une fois triées par `f1` : la première à 0, chacune
    suivant le `f2` de la précédente, la dernière finissant à 255.

    Le tri n'est pas cosmétique. L'ordre de stockage n'est **pas** croissant en
    général : réordonner la page gobos permute ces entrées (SORT-01,
    device-confirmed) sans toucher au pavage. La version antérieure marchait par
    accident sur un corpus dont aucune page n'avait jamais été réordonnée, et
    tombe sur le premier projet qui l'a été.
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
        for r in sorted(tr, key=lambda r: r.get("f1", 0)):
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
    nfx = len(_items(w, 115))
    for k, e in enumerate(_items(w, 151) if w.get(151) else []):
        assert e.get("f1", 0) < nfx, \
            f"151[{k}].f1 = {e.get('f1', 0)} hors des {nfx} fixtures"


# Les treize champs du preset qui portent une valeur par groupe A–H. Tous
# font exactement 8 varints packés, sans exception dans le corpus — voir le
# registre, « les tableaux par groupe ».
TABLEAUX_PAR_GROUPE = (3, 7, 14, 17, 23, 27, 28, 29, 30, 32, 33, 34, 35)


def tableaux_par_groupe_165(w):
    """Les champs par groupe du preset font exactement 8 varints.

    Contrainte non triviale : un découpage varint erroné, ou un champ pris
    pour un scalaire, change immédiatement le compte. C'est ce qui a rangé
    `f3`, `f7`, `f14`, `f23` et `f27` — alors tous nuls dans le corpus — parmi
    les valeurs par groupe plutôt que parmi les inconnues sans forme. Le pari a
    payé sur trois des quatre : `f3`, `f7` et `f23` sont les sélecteurs de page
    du faisceau, de la couleur et du mouvement (registre, F7-01/03/04), et ce
    sont bien des tableaux de huit. `f27` reste nul et non attribué.
    """
    for pre in _items(w, 165):
        for n in TABLEAUX_PAR_GROUPE:
            champ = pre.get(f"f{n}")
            if champ is None:
                continue
            vals = _varints(champ["hex"] if isinstance(champ, dict) else champ)
            assert len(vals) == 8, \
                f"165.f{n} : {len(vals)} varints au lieu de 8"


# Moteur de f16 -> bit de 165.f4 qui doit être mis pour qu'il puisse agir.
# 0 = Color FX, 1 = Move FX, 2 = Beam FX ; voir le registre, « F4-03 ».
MOTEUR_VERS_F4 = {0: 3, 1: 2, 2: 4}


def f4_autorise_les_moteurs(w):
    """Un moteur actif dans f16 implique son bit dans le masque 165.f4.

    L'implication est unilatérale : une page peut autoriser un moteur sans
    qu'aucun preset ne l'emploie. C'est ce qui identifie la tranche 2 de f16
    comme le Beam FX — elle n'est jamais active hors des presets dont le `f4`
    porte le bit 4.
    """
    for pre in _items(w, 165):
        h = pre.get("f16")
        if not h:
            continue
        gros = int.from_bytes(bytes(_varints(h["hex"])), "little")
        f4 = pre.get("f4", 0)
        for m, bit in MOTEUR_VERS_F4.items():
            if (gros >> (9 * m)) & 0x1FF:
                assert f4 >> bit & 1, \
                    f"165 : moteur {m} actif mais f4 = {f4} n'a pas le bit {bit}"


def schema_du_prefixe(w):
    """L'octet 50 est la version de schéma, et 165.f32–f35 arrivent à 10.

    Le préfixe est constant sauf l'UUID (20–35), le compteur de version
    (40–47) et cet octet. La corrélation est totale sur le corpus : schéma 8
    sans `f32`, schémas 10 et 11 avec. Voir le registre, « le préfixe ».
    """
    schema = w.prefix[30]
    assert w.prefix[16:20].hex() == "152b10c0", "préfixe : constante 36-39 changée"
    assert w.prefix[28:30].hex() == "01f9", "préfixe : constante 48-49 changée"
    assert w.prefix[31] == 0, "préfixe : octet 51 non nul"
    assert w.prefix[32:].hex() == "02bee81ca26ccb546dc7b6ec", \
        "préfixe : constante 52-63 changée"
    a32 = any("f32" in pre for pre in _items(w, 165))
    assert a32 == (schema >= 10), \
        f"préfixe : schéma {schema} mais f32 {'présent' if a32 else 'absent'}"


def canal_principal_110(w):
    """110.f5 = l'index, dans le profil, du canal principal de ce canal.

    Un canal principal se désigne lui-même ; un canal **fin** désigne son
    canal grossier. Le canal pointé porte toujours la même `f4`, ce qui rend
    le couple 16 bits lisible sans deviner l'ordre des octets. Vérifié sans
    exception sur les 1100 canaux du corpus.
    """
    p110, p116 = _items(w, 110), _items(w, 116)
    for pr in p116:
        off, n = pr.get("f3", 0), pr.get("f2", 0)
        for j in range(n):
            c = p110[off + j]
            m = c.get("f5", 0)
            assert m <= j, f"110[{off + j}] : f5 = {m} pointe en avant"
            assert p110[off + m].get("f4") == c.get("f4"), \
                f"110[{off + j}] : f5 pointe un canal de feature " \
                f"{p110[off + m].get('f4')}, pas {c.get('f4')}"


def flavours_155(w):
    """155.f2 = le moteur de la séquence, et il détermine le domaine des valeurs.

    Le record tient quatre séquenceurs : l'item 0 est celui du **mouvement**
    (`f2` = 1), les items 1 à 3 ceux du **faisceau** (`f2` = 2) — les trois
    `FX Seq` que l'énumération du Beam FX propose. Les deux moteurs ne stockent
    pas la même chose au même endroit :

    - mouvement : un **index de position** dans la palette 150 du groupe,
      domaine 0–19, plus 255 = « pas de position à ce pas » ;
    - faisceau : un **masque de 4 bits** sur les quatre segments du groupe,
      domaine 0–15. Huit groupes × quatre segments = les 32 sélections que le
      manuel annonce.

    Mesuré par FX6-05 : segments 1 et 4 cochés sur le groupe A du pas 1 ont
    écrit 15 → 9, soit 0b1111 → 0b1001, dans l'item 1.
    """
    seqs = _items(w, 155)
    assert len(seqs) == 4, f"155 : {len(seqs)} séquences, 4 attendues"
    for i, s in enumerate(seqs):
        fl = s.get("f2")
        attendu = 1 if i == 0 else 2
        assert fl == attendu, f"155[{i}] : flavour {fl}, {attendu} attendu"
        vals = _varints(s["f4"]["hex"]) if isinstance(s.get("f4"), dict) \
            else s.get("f4", [])
        assert len(vals) == 128, f"155[{i}] : {len(vals)} valeurs, 128 attendues"
        haut = 19 if fl == 1 else 15
        for k, v in enumerate(vals):
            if fl == 1 and v == 255:
                continue                 # sentinelle « pas de position »
            assert v <= haut, \
                f"155[{i}] : valeur {v} au pas {k // 8} groupe {chr(65 + k % 8)}, " \
                f"hors du domaine 0–{haut} du flavour {fl}"


def _entrees_165(payload):
    """(f1, [entrées brutes]) du record 165, sans interpréter les entrées."""
    i, f1, entrees = 0, None, []
    while i < len(payload):
        tag, i = wpj_codec._rvarint(payload, i)
        if tag == 0x08:                      # f1 varint
            f1, i = wpj_codec._rvarint(payload, i)
        elif tag == 0x2A:                    # f5 : une entrée preset
            ln, i = wpj_codec._rvarint(payload, i)
            entrees.append(payload[i:i + ln]); i += ln
        else:
            raise AssertionError(f"165 : tag inattendu {tag:#x}")
    return f1, entrees


def noms_de_preset_bornes(w):
    """Aucun nom de preset ne dépasse 19 octets UTF-8.

    Limite device-confirmed (PRESET-05, 2026-08-26) : l'UI de renommage du
    W1 plafonne à 19 caractères et le chargeur fait respecter la même borne
    sur un nom écrit par fichier — au-delà, le projet entier refuse de
    s'ouvrir (« Error opening project »), bruyamment. Un générateur doit
    donc valider les noms AVANT d'écrire.
    """
    for pre in _items(w, 165):
        nom = pre.get("f25")
        if nom is None:
            continue
        octets = (bytes.fromhex(nom["hex"]) if isinstance(nom, dict)
                  else nom.encode("utf-8"))
        assert len(octets) <= 19, \
            f"165 : nom de {len(octets)} octets : {octets!r}"


def ajout_de_preset():
    """L'ajout d'un preset : ce que l'appareil écrit, ce qu'il jette.

    Deux paires d'expériences (registre, « F30-04 » et « FLASH-09 ») :

    - F30-04, l'appareil ajoute lui-même un preset : hors 165 ne changent
      que les records d'état vif {115, 125, 155, 161}. Le fichier ne porte
      donc AUCUN compte externe de presets. Et 165.f1 passe de 82 à 81
      pendant que le compte passe de 82 à 83, avec 81 nommés des deux
      côtés : « nombre de presets » est réfuté par l'après, « nombre de
      presets nommés » par l'avant.

    - FLASH-09 / PRESET-01, deux entrées ajoutées par fichier (copies de
      l'entrée 82, id et tranche f16 changés) : l'ajout est
      **device-confirmed** — stocké, rendu octet pour octet, affiché et
      rappelable après réouverture à froid (registre, « PRESET-01 »). La
      « suppression » initialement rapportée par FLASH-09 est rétractée :
      les nombres du téléchargement « rendu » étaient ceux de l'état
      pré-deploy. L'arithmétique de l'édit reste vérifiable :
      len(candidat.165) - len(avant.165) == 2 × (3 + len(entrée 82)).

    Paire absente du corpus = vérification sautée, pas réussie.
    """
    import os
    rac = os.path.join(os.environ.get(wpjlib.CORPUS_ENV)
                       or wpjlib.CORPUS_DEFAUT, "experiments")

    def charge(*p):
        chemin = os.path.join(rac, *p)
        return wpjlib.Wpj.load(chemin) if os.path.exists(chemin) else None

    av, ap = charge("F30-04", "before.wpj"), \
        charge("F30-04", "after-three-patterns.wpj")
    if av and ap:
        assert [t for t, _ in av.records] == [t for t, _ in ap.records]
        bouges = {t for (t, p1), (_, p2) in zip(av.records, ap.records)
                  if p1 != p2}
        assert bouges == {115, 125, 155, 161, 165}, \
            f"F30-04 : records changés {sorted(bouges)}"
        f1a, ea = _entrees_165(av.get(165))
        f1b, eb = _entrees_165(ap.get(165))
        noms_a = sum(1 for p in wpj_codec.decode(165, av.get(165))["presets"]
                     if p.get("nom"))
        noms_b = sum(1 for p in wpj_codec.decode(165, ap.get(165))["presets"]
                     if p.get("nom"))
        assert (len(ea), noms_a, f1a) == (82, 81, 82), \
            f"F30-04 avant : {(len(ea), noms_a, f1a)}"
        assert (len(eb), noms_b, f1b) == (83, 81, 81), \
            f"F30-04 après : {(len(eb), noms_b, f1b)}"

    av, ca = charge("FLASH-09", "before.wpj"), \
        charge("FLASH-09", "candidate.wpj")
    if av and ca:
        assert av.prefix == ca.prefix, "FLASH-09 : préfixe touché par l'édit"
        bouges = {t for (t, p1), (_, p2) in zip(av.records, ca.records)
                  if p1 != p2}
        assert bouges == {165}, f"FLASH-09 : records changés {sorted(bouges)}"
        f1a, ea = _entrees_165(av.get(165))
        f1c, ec = _entrees_165(ca.get(165))
        assert f1a == f1c == 81, f"FLASH-09 : f1 {f1a} / {f1c}"
        assert len(ec) == 85 and ec[:83] == ea, \
            "FLASH-09 : le candidat n'est pas avant + 2 entrées en queue"
        for e in ec[83:]:
            assert len(e) == len(ea[82]), "FLASH-09 : entrée d'autre taille"
            diffs = sum(x != y for x, y in zip(ea[82], e))
            assert 0 < diffs <= 6, \
                f"FLASH-09 : {diffs} octets d'écart avec l'entrée 82"
        entete = 1 + len(wpj_codec._wvarint(len(ea[82])))
        assert len(ca.get(165)) - len(av.get(165)) == 2 * (entete + len(ea[82])), \
            "FLASH-09 : l'écart de taille n'est pas « les deux ajouts, exactement »"


def carte_dmx_130(w):
    """130 = la carte de mapping DMX IN, et `f1` en compte les entrées.

    Mesuré sur l'appareil (MAP-01 / MAP-02, registre) : `f6` est le canal
    DMX IN de l'entrée, **en base zéro** — CH1 laisse `f6` absent, CH7 écrit
    6, CH20 écrit 19, CH30 écrit 29. `f4` est la cible : **20** = dimmer de
    groupe, **70** = preset. `f2` est l'instance dans la cible, l'index de
    groupe pour `f4 = 20` : c'est l'entrée `f2 = 1` qui a pris le canal 20
    quand l'opérateur a mappé le groupe B, alors qu'elle était en position 0
    — donc la clé est `f2`, pas le rang.

    La table est **appendable** : mapper un preset a ajouté une 10e entrée à
    une table qui en portait 9 depuis toujours, et `f1` a suivi de 9 à 10.
    Les 9 d'usine sont la carte identité — A–H sur les canaux 1 à 8, MAIN sur
    9 — ce qui explique que 130 ait été octet pour octet identique sur les
    51 premiers fichiers : personne n'y avait jamais touché.

    `f7` et `f8` n'ont jamais bougé et n'ont pas de nom.
    """
    for occurrence, (typ, _) in enumerate(
            [(t, p) for t, p in w.records if t == 130]):
        items = _items(w, 130, occurrence)
        annonce = wpj_codec._decode_msg(
            w.get(130, occurrence), {1: ("f1", "uint")}).get("f1", 0)
        assert annonce == len(items), \
            f"130.f1 = {annonce} mais la table porte {len(items)} entrées"
        for i, e in enumerate(items):
            assert e.get("f6", 0) < 512, \
                f"130[{i}] : canal DMX IN {e.get('f6', 0)} hors d'un univers"


IDENTITES = (ranges_par_canal, palette_gobo, tranches_106, patch_disjoint,
              groupe_fixture, moteurs_f16, tranche5_f16,
              plages_111, roles_106,
              ordre_fixtures_115, bornes_106, tranches_151,
              tableaux_par_groupe_165, f4_autorise_les_moteurs,
              schema_du_prefixe, canal_principal_110, noms_de_preset_bornes,
              flavours_155, carte_dmx_130)


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
    ajout_de_preset()
    print(f"{len(IDENTITES)} identités vérifiées sur {n} fichiers variante A"
          " (+ paires F30-04 / FLASH-09)", file=sys.stderr)


if __name__ == "__main__":
    demo()
