#!/usr/bin/env python3
"""Compilateur de show minimal, template-based (sur wpjlib + wpj_codec).

Principe : on part TOUJOURS d'un projet donneur variante A existant et on
applique une spec JSON d'édition. Tout ce que la spec ne nomme pas est
préservé octet pour octet par wpjlib. Une position et une entrée de palette
éditées doivent exister dans le donneur ; un preset peut en plus être **créé
en queue** en clonant un preset du donneur (clé `modele`) — l'ajout d'une
entrée `165.f5` avec l'id suivant est device-confirmed, `165.f1` reste
verbatim (registre, PRESET-01).
Périmètre = champs à statut ≥ correlated (records 101, 111, 130, 135, 145,
150, 165). Phase, Size et Fade sont mesurées (FX6-02/03) mais restent hors des
clés écrites : lues, pas écrites — la liste des clés est `_FX_CLES`.

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
# clé FX → bornes (statuts correlated, research/preset-format-165.md).
# `vitesse` était bornée à 200 quand elle désignait f2 ; f2 est le fondu, et la
# vitesse est un pourcentage — jamais au-dessus de 100 sur 352 presets (FX6-02).
# phase/size/fade sont nommés mais restent hors de la liste : lus, pas écrits.
_FX_CLES = {"effect": (0, 8), "speed": (0, 100), "link_order": (10, 13),
            "speed_source": (0, 2), "bpm_division": (0, 1 << 31)}
_SHOW_CLES = ("base", "name", "presets", "positions", "palette",
              "gobo_names", "gobo_order", "mappings")
_PRESET_CLES = ("id", "template", "name", "positions", "dimmers",
                "content_mask", "color_pattern",
                "static_color") + _FX_NOMS
NOM_MAX_OCTETS = 19          # au-delà, le projet entier refuse de s'ouvrir
NB_GROUPES = 8               # A–H
PADS_PAR_GROUPE = 20         # un masque de 20 bits par groupe dans f31
# Attribution device-confirmed (registre, type 150) : f6 = PAN, f7 = TILT,
# f3 = FAN, f4 = FOCUS OFFSET. Une lecture antérieure plaçait pan/tilt en
# f3/f4 ; elle est réfutée par l'écran d'édition du W1.
_POS_CLES = ("page", "index", "name", "pan", "tilt", "fan")
_POS_CHAMPS = {"pan": "f6", "tilt": "f7", "fan": "f3"}
_PAL_CLES = ("index", "red", "green", "blue")
# Record 130 = la carte de mapping DMX IN (SPEC §7.3, MAP-01..09). `f4` est la
# FONCTION visée, pas la catégorie de l'écran : les sept fonctions `Flash` en
# portent sept différents. Les quinze ci-dessous sont l'inventaire complet des
# cinq catégories, chacune mesurée par l'entrée que l'appareil a créée quand
# l'opérateur l'a sélectionnée à l'écran (MAP-09, dix d'un coup, chaque canal
# étiquetant son entrée).
#
# Valeur = (f4, instance fixe) ; `None` = l'instance vient de la spec.
# L'instance vaut **255** dès que la fonction n'est pas liée à une instance
# numérotée — y compris `select_preset` et `jump_preset`, où c'est la VALEUR
# reçue qui choisit. Deux fonctions partagent un `f4` avec `preset` (70) et
# trois avec `jump_preset` (78) : c'est le couple (f4, instance) qui identifie.
_MAP_FONCTIONS = {
    "group_dimmer":   (20, None),   # instance = le groupe A–H
    "main":            (27, 0),      # l'entrée d'usine ne porte pas de f7
    "preset":          (70, None),   # instance = l'index du preset
    "select_preset":   (70, 255),    # même f4 : la valeur reçue choisit
    "preset_page":     (82, None),   # instance = la page, base zéro
    "bpm_tap":         (17, 255),
    "wolf":            (10, 255),
    "strobe":          (11, 255),
    "blinder":         (12, 255),
    "speed":           (13, 255),
    "blackout":        (14, 255),
    "smoke":           (15, 255),
    "jump_preset":     (78, 255),    # la valeur reçue choisit
    "previous_preset": (78, 1),
    "next_preset":     (78, 2),
}
_MAP_CLES = ("target", "group", "index", "page", "channel")
PAGES_PRESET = 7             # Page 1 à 7, l'écran n'en propose pas d'autres
PRESETS_MAX = 200            # 0–199, la borne du panneau
# L'appareil écrit ses champs dans l'ordre numérique et OMET tout champ nul —
# `28 00` n'apparaît jamais chez lui. Une entrée éditée doit être remise dans
# cette forme, sinon le fichier diverge des octets de l'appareil alors même que
# sa sémantique est juste : c'est invisible à une comparaison décodée, et ça
# casserait tout diff ultérieur contre un fichier que l'appareil a récrit.
_MAP_ORDRE = (("instance", 2), ("function", 4), ("channel_high_byte", 5),
              ("channel_low_byte", 6), ("f7", 7), ("f8", 8))


def _normalise_mapping(entree):
    """Rend l'entrée dans l'ordre des champs de l'appareil, sans champ nul."""
    connus = {nom for nom, _ in _MAP_ORDRE}
    propre = {nom: entree[nom] for nom, _ in _MAP_ORDRE
              if entree.get(nom)}
    propre.update({k: v for k, v in entree.items() if k not in connus})
    entree.clear()
    entree.update(propre)
    return entree
CANAL_MAX = 512              # borne de l'encodeur du panneau, mesurée


def cles(d, permises, contexte):
    """Publique : `wpj_generate` valide ses intentions avec les memes regles."""
    inconnues = [k for k in d if k not in permises]
    retirees = {k: wpj_codec.remplacante(k) for k in inconnues
                if wpj_codec.remplacante(k)}
    if retirees:
        detail = ", ".join(f"{v!r} → {n!r}" for v, n in sorted(retirees.items()))
        raise ValueError(f"{contexte} : clés retirées le 2026-08-31, "
                         f"écrire leur remplaçante : {detail}")
    if inconnues:
        raise ValueError(f"{contexte} : clés hors périmètre {inconnues} ; "
                         f"permises : {list(permises)}")


def borne(contexte, nom, v, lo, hi):
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise ValueError(f"{contexte} : {nom}={v!r} hors bornes [{lo}, {hi}]")
    return v


def liste8(contexte, nom, v, lo, hi):
    if not isinstance(v, list) or len(v) != 8:
        raise ValueError(f"{contexte} : {nom} doit être une liste de 8 entiers")
    return [borne(contexte, f"{nom}[{i}]", x, lo, hi) for i, x in enumerate(v)]


def _pads_vers_masques(contexte, pads8):
    """8 listes de numéros de pad (1–20) → les 20 octets packés de `f31`.

    `f31` = 20 varints = 160 bits en petit-boutien, découpés en huit masques
    de 20 bits (un par groupe A–H) ; le bit n du groupe g allume le pad n+1
    de la palette 140 de ce groupe — device-confirmed.
    """
    if not isinstance(pads8, list) or len(pads8) != NB_GROUPES:
        raise ValueError(f"{contexte} : static_color doit être "
                         f"{NB_GROUPES} listes de numéros de pad (1–"
                         f"{PADS_PAR_GROUPE}), une par groupe A–H")
    bits = 0
    for g, pads in enumerate(pads8):
        if not isinstance(pads, list):
            raise ValueError(f"{contexte} : static_color[{g}] doit être "
                             "une liste de numéros de pad")
        for pad in pads:
            borne(contexte, f"static_color[{g}]", pad, 1, PADS_PAR_GROUPE)
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
    cles(spec, _SHOW_CLES, "show")
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
    if "name" in spec:
        nom = spec["name"]
        if not isinstance(nom, str) or not nom:
            raise ValueError("show : 'name' doit être une chaîne non vide")
        rec(101)["name"] = nom
        verifs.append((101, 0, "nom projet", lambda d, v=nom: d.get("name") == v))

    # --- record 165 : presets, adressés par id ---
    for pe in spec.get("presets", []):
        cles(pe, _PRESET_CLES, "preset")
        pid = borne("preset", "id", pe.get("id", -1), 0, 1 << 31)
        d165 = rec(165)
        ctx = f"preset id {pid}"
        cible = next((p for p in d165["presets"]
                      if isinstance(p, dict) and p.get("id", 0) == pid), None)
        if cible is None:
            cible = _cree_preset(ctx, d165, pid, pe)
        elif "template" in pe:
            raise ValueError(f"{ctx} : déjà présent dans le donneur, "
                             "'template' ne s'applique qu'à une création")
        if "name" in pe:
            if not isinstance(pe["name"], str):
                raise ValueError(f"{ctx} : nom doit être une chaîne")
            octets = len(pe["name"].encode("utf-8"))
            if octets > NOM_MAX_OCTETS:
                raise ValueError(f"{ctx} : nom de {octets} octets UTF-8 > "
                                 f"{NOM_MAX_OCTETS} — le projet ENTIER "
                                 "refuserait de s'ouvrir (PRESET-05)")
            cible["name"] = pe["name"]
        if "positions" in pe:
            cible["positions"] = liste8(ctx, "positions", pe["positions"],
                                         0, 1 << 31)
        if "dimmers" in pe:
            cible["dimmers"] = liste8(ctx, "dimmers", pe["dimmers"], 0, 255)
        if "content_mask" in pe:
            cible["content_mask"] = borne(ctx, "content_mask",
                                             pe["content_mask"], 0, 63)
        if "color_pattern" in pe:
            cible["color_pattern"] = liste8(ctx, "color_pattern",
                                               pe["color_pattern"], 0, 10)
        if "static_color" in pe:
            cible["static_color"] = _pads_vers_masques(
                ctx, pe["static_color"])
        for fx in _FX_NOMS:
            if fx not in pe:
                continue
            cles(pe[fx], _FX_CLES, f"{ctx} {fx}")
            for k, v in pe[fx].items():
                borne(f"{ctx} {fx}", k, v, *_FX_CLES[k])
            if fx not in cible:
                raise ValueError(f"{ctx} : {fx} absent du donneur — création "
                                 "de sous-message FX non validée, utiliser un "
                                 "donneur où ce FX existe")
            cible[fx][0].update(pe[fx])
        attendu = {k: (_pads_vers_masques(ctx, v)
                       if k == "static_color" else v)
                   for k, v in pe.items() if k not in ("id", "template")}
        verifs.append((165, 0, ctx, lambda d, pid=pid, att=attendu:
                       _verif_preset(d, pid, att)))

    # --- record 150 ×8 : positions pan/tilt nommées ---
    for pos in spec.get("positions", []):
        cles(pos, _POS_CLES, "position")
        page = borne("position", "page", pos.get("page", 0), 1, 8)
        idx = borne("position", "index", pos.get("index", -1), 0, 1 << 31)
        d150 = rec(150, page - 1)
        entrees = d150.get("positions", [])
        if idx >= len(entrees) or not isinstance(entrees[idx], dict) or \
                set(entrees[idx]) == {"hex"}:
            raise ValueError(f"position page {page} index {idx} : l'entrée "
                             "doit exister dans le donneur")
        e = entrees[idx]
        ctx = f"position page {page} index {idx}"
        if "name" in pos:
            if not isinstance(pos["name"], str):
                raise ValueError(f"{ctx} : nom doit être une chaîne")
            e["name"] = pos["name"]
        for cle, champ in _POS_CHAMPS.items():
            if cle in pos:
                e[champ] = borne(ctx, cle, pos[cle], 0, 65535)
        attendu = {("name" if k == "name" else _POS_CHAMPS[k]): v
                   for k, v in pos.items() if k in ("name",) + tuple(_POS_CHAMPS)}
        verifs.append((150, page - 1, ctx, lambda d, i=idx, att=attendu:
                       all(d["positions"][i].get(k, 0) == v
                           for k, v in att.items())))

    # --- record 135 : palette ColorFX ---
    for pal in spec.get("palette", []):
        cles(pal, _PAL_CLES, "palette")
        idx = borne("palette", "index", pal.get("index", -1), 0, 1 << 31)
        d135 = rec(135)
        pads = d135.get("pads", [])
        if idx >= len(pads) or not isinstance(pads[idx], dict) or \
                set(pads[idx]) == {"hex"}:
            raise ValueError(f"palette index {idx} : l'entrée doit exister "
                             "dans le donneur")
        ctx = f"palette index {idx}"
        for k in ("red", "green", "blue"):
            if k in pal:
                pads[idx][k] = borne(ctx, k, pal[k], 0, 255)
        attendu = {k: pal[k] for k in ("red", "green", "blue") if k in pal}
        verifs.append((135, 0, ctx, lambda d, i=idx, att=attendu:
                       all(d["pads"][i].get(k, 0) == v
                           for k, v in att.items())))

    # --- records 145 + 111 : page gobos du groupe A ---
    # Device-confirmed (RENAME-01, SORT-01) : le nom d'un pad est `145.f3`,
    # et l'ordre des pads est l'ordre du fil des plages roue (fonction 14)
    # du record 111 — plages non monotones acceptées, bornes DMX embarquées.
    if "gobo_names" in spec:
        d145 = rec(145)
        att_noms = {}
        for cle, nom in spec["gobo_names"].items():
            gid = int(cle)
            ctx = f"gobo_names id {gid}"
            if not isinstance(nom, str) or not nom:
                raise ValueError(f"{ctx} : nom doit être une chaîne non vide")
            if len(nom.encode("utf-8")) > NOM_MAX_OCTETS:
                raise ValueError(f"{ctx} : nom > {NOM_MAX_OCTETS} octets "
                                 "UTF-8 — limite mesurée sur les presets "
                                 "(PRESET-05), non mesurée ici, donc refusée")
            slot = next((s for s in d145.get("gobos", [])
                         if isinstance(s, dict) and s.get("gobo_id") == gid),
                        None)
            if slot is None:
                raise ValueError(f"{ctx} : absent de la palette du donneur")
            slot["name"] = nom
            att_noms[gid] = nom
        verifs.append((145, 0, "gobo_names", lambda d, att=att_noms: all(
            next((s.get("name") for s in d["gobos"]
                  if s.get("gobo_id") == g), None) == n
            for g, n in att.items())))

    if "gobo_order" in spec:
        ordre = spec["gobo_order"]
        d145 = rec(145)
        slots = d145.get("gobos", [])
        pleins = [s for s in slots if isinstance(s, dict) and "gobo_id" in s]
        if sorted(s["gobo_id"] for s in pleins) != sorted(ordre):
            raise ValueError("gobo_order : la liste doit porter exactement "
                             "les ids de la palette du donneur")
        # roue partagée par un autre groupe = non mesuré : refus.
        for occ in range(1, sum(1 for t, _ in w.records if t == 145)):
            autres = wpj_codec.decode(145, w.get(145, occ)).get("gobos", [])
            ids = sorted(s["gobo_id"] for s in autres
                         if isinstance(s, dict) and "gobo_id" in s)
            if ids == sorted(ordre):
                raise ValueError(f"gobo_order : le groupe {occ} porte la "
                                 "même roue — cas non mesuré, refusé")
        par_id = {s["gobo_id"]: s for s in pleins}
        nouveaux = [par_id[g] for g in ordre]
        for k, s in enumerate(nouveaux):
            s["glyph"] = chr(0x21 + k)      # séquence, la forme de l'appareil
        d145["gobos"] = nouveaux + slots[len(pleins):]
        verifs.append((145, 0, "gobo_order palette",
                       lambda d, o=list(ordre):
                       [s["gobo_id"] for s in d["gobos"]
                        if "gobo_id" in s] == o))
        touchees = 0
        for occ in range(sum(1 for t, _ in w.records if t == 111)):
            d111 = rec(111, occ)
            plages = d111.get("ranges", [])
            roue = [k for k, p in enumerate(plages)
                    if isinstance(p, dict) and p.get("function") == 14]
            ids = [plages[k]["gobo_id"] for k in roue
                   if "gobo_id" in plages[k]]
            if sorted(ids) != sorted(ordre):
                continue
            par_id = {plages[k]["gobo_id"]: plages[k] for k in roue
                      if "gobo_id" in plages[k]}
            sans_id = [plages[k] for k in roue if "gobo_id" not in plages[k]]
            for k, p in zip(roue, sans_id + [par_id[g] for g in ordre]):
                plages[k] = p
            touchees += 1
            verifs.append((111, occ, f"gobo_order roue occ {occ}",
                           lambda d, o=list(ordre):
                           [p["gobo_id"] for p in d["ranges"]
                            if p.get("function") == 14 and "gobo_id" in p]
                           == o))
        if not touchees:
            raise ValueError("gobo_order : aucune roue du donneur ne porte "
                             "ces ids dans un record 111 décodable")

    # --- record 130 : la carte de mapping DMX IN (device-confirmed, MAP-01..07) ---
    # Une entrée est identifiée par (fonction, instance), JAMAIS par son rang :
    # l'ordre du fil bouge sans que le contenu change, deux fois observé en onze
    # sauvegardes, sans lecture. `canal: null` retire l'entrée — « non mappé »
    # est l'absence, il n'existe pas de sentinelle.
    if "mappings" in spec:
        d130 = rec(130)
        entrees = d130.setdefault("mappings", [])
        attendu = {}
        for me in spec["mappings"]:
            cles(me, _MAP_CLES, "mapping")
            cible = me.get("target")
            if cible not in _MAP_FONCTIONS:
                raise ValueError(
                    f"mapping : cible {cible!r} hors périmètre ; mesurées : "
                    f"{sorted(_MAP_FONCTIONS)}")
            ctx = f"mapping {cible}"
            fonction, instance = _MAP_FONCTIONS[cible]
            if cible == "group_dimmer":
                g = me.get("group")
                if g not in list("ABCDEFGH"):
                    raise ValueError(f"{ctx} : 'group' doit être A–H")
                instance = ord(g) - ord("A")
            elif cible == "preset":
                instance = borne(ctx, "index", me.get("index", -1),
                                  0, PRESETS_MAX - 1)
            elif cible == "preset_page":
                # la page s'écrit comme elle s'affiche, 1–7 ; stockée en base zéro
                instance = borne(ctx, "page", me.get("page", -1),
                                  1, PAGES_PRESET) - 1
            if any(k in me for k in ("group", "index", "page")
                   if k != {"group_dimmer": "group", "preset": "index",
                            "preset_page": "page"}.get(cible)):
                raise ValueError(f"{ctx} : clé d'instance qui ne s'applique pas "
                                 "à cette fonction")
            canal = me.get("channel", "absent")
            if canal == "absent":
                raise ValueError(f"{ctx} : clé 'channel' obligatoire "
                                 "(un entier 1–512, ou null pour retirer)")
            trouve = next((e for e in entrees
                           if e.get("function") == fonction
                           and e.get("instance", 0) == instance), None)
            if canal is None:
                if trouve is None:
                    raise ValueError(f"{ctx} : aucune entrée à retirer")
                entrees.remove(trouve)
                attendu[(fonction, instance)] = None
                continue
            canal = borne(ctx, "channel", canal, 1, CANAL_MAX)
            haut, bas = divmod(canal - 1, 256)
            if trouve is None:
                # forme d'une entrée créée par l'appareil : f7 = 1, f8 = 1,
                # observée sur les treize qu'il a créées (MAP-02, MAP-09).
                trouve = {"instance": instance, "function": fonction,
                          "f7": 1, "f8": 1}
                entrees.append(trouve)
            trouve["channel_high_byte"], trouve["channel_low_byte"] = haut, bas
            _normalise_mapping(trouve)
            attendu[(fonction, instance)] = canal
        d130["f1"] = len(entrees)             # device-confirmed : f1 = le compte

        def _verif_130(d, att=attendu):
            if d.get("f1") != len(d.get("mappings", [])):
                return False
            for (fonction, instance), canal in att.items():
                e = next((x for x in d["mappings"]
                          if x.get("function") == fonction
                          and x.get("instance", 0) == instance), None)
                if canal is None:
                    if e is not None:
                        return False
                    continue
                if e is None or (e.get("channel_high_byte", 0) * 256
                                 + e.get("channel_low_byte", 0) + 1) != canal:
                    return False
            return True

        verifs.append((130, 0, "mappings", _verif_130))

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
    if "template" not in pe:
        raise ValueError(f"{ctx} : absent du donneur — donner 'template' "
                         "(id du preset à cloner) pour le créer en queue")
    mid = borne(ctx, "template", pe["template"], 0, 1 << 31)
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
        # `SET_PRESET` porte l'id sur un seul octet (RECALL-03) et le deuxième
        # n'est pas lu (RAW-02) ; tous les tirs publiés tiennent dans 0–127.
        # Au-delà, rappel exact, troncature à 7 bits et no-op restent tous
        # possibles. Le panneau, lui, va jusqu'à 199 : la cue est rappelable
        # à la main, pas forcément à distance.
        print(f"attention : {ctx} — le rappel par USB n'a jamais été mesuré "
              "au-dessus de l'id 127 (RECALL-06) ; au panneau, oui",
              file=sys.stderr)
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
    spec = {"base": base, "name": "WMX SHOW DEMO",
            "presets": [{"id": 80, "name": "demo",
                         "beam_fx1": {"effect": 1, "speed": 80},
                         "positions": [4, 1, 1, 1, 1, 1, 1, 1],
                         "dimmers": [200] * 8},
                        {"id": neuf, "template": 23, "name": "cree",
                         "content_mask": 24, "dimmers": [128] * 8,
                         "color_pattern": [9] * 8,
                         "static_color": [[6]] * 2 + [[]] * 6}],
            "positions": [{"page": 1, "index": 1, "name": "DemoPos",
                           "pan": 12345, "tilt": 54321, "fan": 32768}],
            "palette": [{"index": 0, "red": 10, "green": 20, "blue": 30}],
            "mappings": [{"target": "group_dimmer", "group": "B",
                          "channel": 300},          # deux octets : f5 = 1
                         {"target": "preset", "index": 4, "channel": 40},
                         {"target": "wolf", "channel": 45},
                         {"target": "preset_page", "page": 3, "channel": 101},
                         {"target": "smoke", "channel": 106},
                         {"target": "select_preset", "channel": 107},
                         {"target": "next_preset", "channel": 110},
                         {"target": "group_dimmer", "group": "D",
                          "channel": 1},          # octet haut nul : doit être omis
                         {"target": "group_dimmer", "group": "C",
                          "channel": None}]}        # retrait
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "demo.wpj")
        diffs = compiler(spec, out)
        assert {(t, o) for t, o, *_ in diffs} == {(101, 0), (165, 0),
                                                 (150, 0), (135, 0),
                                                 (130, 0)}, diffs
        # relecture indépendante des valeurs demandées
        w = wpjlib.Wpj.load(out)
        assert wpj_codec.decode(101, w.get(101))["name"] == "WMX SHOW DEMO"
        p = next(p for p in wpj_codec.decode(165, w.get(165))["presets"]
                 if p.get("id", 0) == 80)
        assert p["name"] == "demo" and p["dimmers"] == [200] * 8
        assert p["beam_fx1"][0]["effect"] == 1 and p["beam_fx1"][0]["speed"] == 80
        e = wpj_codec.decode(150, w.get(150, 0))["positions"][1]
        assert e["name"] == "DemoPos" and e["f6"] == 12345 and e["f7"] == 54321
        assert e["f3"] == 32768
        assert wpj_codec.decode(135, w.get(135))["pads"][0] == \
            {"red": 10, "green": 20, "blue": 30}
        # le preset créé : cloné, en queue, relu champ par champ
        presets = wpj_codec.decode(165, w.get(165))["presets"]
        c = presets[-1]
        assert c["id"] == neuf and c["name"] == "cree", c.get("id")
        assert c["content_mask"] == 24 and c["dimmers"] == [128] * 8
        assert masques_vers_pads(c["static_color"]) == \
            [[6], [6], [], [], [], [], [], []]
        modele = next(p for p in presets if p.get("id", 0) == 23)
        assert {k: v for k, v in c.items() if k not in
                ("id", "name", "content_mask", "dimmers", "color_pattern",
                 "static_color")} == \
               {k: v for k, v in modele.items() if k not in
                ("id", "name", "content_mask", "dimmers", "color_pattern",
                 "static_color")}, "le clone doit être le modèle verbatim"
        # spec vide = round-trip octet-identique du donneur
        out2 = os.path.join(tmp, "ident.wpj")
        assert compiler({"base": base}, out2) == []
        assert open(out2, "rb").read() == open(base, "rb").read()
        # page gobos : nom + rotation, valeurs relues
        pal = wpj_codec.decode(145, wpjlib.Wpj.load(base).get(145))["gobos"]
        gids = [s["gobo_id"] for s in pal
                if isinstance(s, dict) and "gobo_id" in s]
        if len(gids) < 2:
            raise ValueError("donneur sans palette gobo")
        rot = gids[1:] + gids[:1]
        out3 = os.path.join(tmp, "gobo.wpj")
        compiler({"base": base, "gobo_names": {str(gids[0]): "DemoGobo"},
                  "gobo_order": rot}, out3)
        d = wpj_codec.decode(145, wpjlib.Wpj.load(out3).get(145))["gobos"]
        assert [s["gobo_id"] for s in d if "gobo_id" in s] == rot
        assert next(s["name"] for s in d
                    if s.get("gobo_id") == gids[0]) == "DemoGobo"
        # rotation puis rotation inverse, sans renommage : donneur intact à
        # l'octet près (glyphes séquentiels = la forme que l'appareil écrit)
        if [s.get("glyph") for s in pal if "gobo_id" in s] == \
                [chr(0x21 + k) for k in range(len(gids))]:
            ga, gb = os.path.join(tmp, "ga.wpj"), os.path.join(tmp, "gb.wpj")
            compiler({"base": base, "gobo_order": rot}, ga)
            compiler({"base": ga, "gobo_order": gids}, gb)
            assert open(gb, "rb").read() == open(base, "rb").read()
        # erreurs attendues : clé inconnue, entrée absente
        # --- la carte, relue indépendamment ---
        d130 = wpj_codec.decode(130, w.get(130))
        carte = {(e.get("function"), e.get("instance", 0)):
                 e.get("channel_high_byte", 0) * 256
                 + e.get("channel_low_byte", 0) + 1
                 for e in d130["mappings"]}
        assert carte[(20, 1)] == 300, carte          # modifiée, sur deux octets
        assert carte[(70, 4)] == 40, carte           # créée
        assert carte[(10, 255)] == 45, carte         # créée, instance 255
        assert (20, 2) not in carte, carte           # retirée
        assert carte[(20, 0)] == 1 and carte[(27, 0)] == 9, carte  # intactes
        assert carte[(82, 2)] == 101, carte      # page 3 -> instance 2
        assert carte[(15, 255)] == 106, carte
        assert carte[(70, 255)] == 107, carte    # même f4 que preset, inst. 255
        assert carte[(78, 2)] == 110, carte      # f4 partagé, instance fixe 2
        assert carte[(70, 4)] != carte[(70, 255)], "les deux f4=70 confondus"
        assert d130["f1"] == len(d130["mappings"]) == 9 - 1 + 6, d130["f1"]

        # --- la forme des octets, pas seulement la sémantique ---
        # L'appareil écrit ses champs dans l'ordre numérique et n'émet jamais
        # un champ nul. Une divergence ici est invisible au décodage et rendrait
        # tout diff futur illisible contre un fichier que l'appareil a récrit.
        import wpj_wire
        brut = [x for x in wpj_wire.load(out)[1] if x[1] == 130][0][3]
        for e in wpj_wire.walk(brut):
            if e[0] != 5:
                continue
            octets = e[2]
            assert b"\x28\x00" not in octets, \
                f"champ 5 nul émis : {octets.hex()}"
            numeros = [c[0] for c in e[3]]
            assert numeros == sorted(numeros), \
                f"champs hors de l'ordre numérique : {octets.hex()}"

        for mauvais in [{"base": base, "fondu": 1},
                        {"base": base, "presets": [{"id": 9999, "name": "x"}]},
                        {"base": base, "presets": [{"id": 80, "size": 5}]},
                        {"base": base, "palette": [{"index": 999, "red": 1}]},
                        # nom de 20 octets : tueur device-confirmed
                        {"base": base, "presets": [{"id": 80,
                                                    "name": "a" * 20}]},
                        # création sous l'id le plus grand du donneur
                        {"base": base, "presets": [{"id": 1, "template": 23}]},
                        # 'template' sur un preset qui existe déjà
                        {"base": base, "presets": [{"id": 80, "template": 23}]},
                        # pad hors de la grille de 20
                        {"base": base, "presets": [
                            {"id": neuf, "template": 23,
                             "static_color": [[21]] + [[]] * 7}]},
                        # gobo inconnu, ordre incomplet, nom trop long
                        {"base": base, "gobo_names": {"999999": "x"}},
                        {"base": base, "gobo_order": gids[:-1]},
                        {"base": base, "gobo_names": {str(gids[0]): "a" * 20}},
                        # fonction non mesurée : on ne devine pas un f4
                        {"base": base, "mappings": [{"target": "preset_page",
                                                     "channel": 5}]},
                        # canal hors de l'univers
                        {"base": base, "mappings": [
                            {"target": "group_dimmer", "group": "A",
                             "channel": 513}]},
                        # groupe hors A–H
                        {"base": base, "mappings": [
                            {"target": "group_dimmer", "group": "I",
                             "channel": 5}]},
                        # une fonction sans instance n'en prend pas
                        {"base": base, "mappings": [{"target": "wolf",
                                                     "index": 2, "channel": 5}]},
                        # 'channel' obligatoire, même pour retirer
                        {"base": base, "mappings": [{"target": "wolf"}]},
                        # retirer une entrée absente
                        {"base": base, "mappings": [{"target": "bpm_tap",
                                                     "channel": None}]},
                        # page hors 1–7
                        {"base": base, "mappings": [{"target": "preset_page",
                                                     "page": 8, "channel": 5}]},
                        # clé d'instance qui ne s'applique pas à la fonction
                        {"base": base, "mappings": [{"target": "preset_page",
                                                     "group": "A", "page": 1,
                                                     "channel": 5}]},
                        {"base": base, "mappings": [{"target": "select_preset",
                                                     "index": 3, "channel": 5}]}]:
            try:
                compiler(mauvais, os.path.join(tmp, "err.wpj"))
                raise AssertionError(f"erreur attendue : {mauvais}")
            except ValueError:
                pass
        assert not os.path.exists(os.path.join(tmp, "err.wpj"))
    # Aucun exemple suivi ne doit encore porter une clé retirée : c'est la
    # moitié du contrat qui vit dans les fichiers, pas dans le code.
    import glob
    suivis = (sorted(glob.glob("corpus/**/*.json", recursive=True))
              + sorted(glob.glob("docs/*.md")) + ["README.md", "AGENTS.md"])
    for exemple in suivis:
        try:
            with open(exemple, encoding="utf-8") as flux:
                texte = flux.read()
        except OSError:
            continue
        perimees = [k for k in wpj_codec.CLES_RETIREES
                    if f'"{k}"' in texte or f"`{k}`" in texte]
        assert not perimees, f"{exemple}: retired keys {perimees}"

    # Une clé française retirée est une erreur qui nomme sa remplaçante.
    for essai in ({"base": "x", "nom": "y"}, {"base": "x", "gobo_ordre": []}):
        try:
            cles(essai, _SHOW_CLES, "show.json")
            raise AssertionError(f"clé retirée acceptée : {essai}")
        except ValueError as erreur:
            assert "retirées" in str(erreur) and "→" in str(erreur), erreur

    print("self-check ok : compile + création + auto-verify + erreurs sur "
          + os.path.basename(base), file=sys.stderr)


def main(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commandes = parseur.add_subparsers(dest="commande")
    compile_cmd = commandes.add_parser(
        "compile", help="applique une spec JSON a un projet donneur")
    compile_cmd.add_argument("spec", help="le show.json")
    compile_cmd.add_argument("sortie", help="projet neuf ; un existant est refuse")
    verify_cmd = commandes.add_parser(
        "verify", help="liste les records qui different entre deux projets")
    verify_cmd.add_argument("base")
    verify_cmd.add_argument("sortie")
    args = parseur.parse_args(argv)
    if args.commande is None:
        demo()
        return 0
    if args.commande == "compile":
        with open(args.spec, encoding="utf-8") as flux:
            spec = json.load(flux)
        _imprime(compiler(spec, args.sortie))
        print(f"ok : {args.sortie}")
        return 0
    _imprime(verifier(args.base, args.sortie))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError) as e:
        print(f"erreur : {e}", file=sys.stderr)
        sys.exit(1)
