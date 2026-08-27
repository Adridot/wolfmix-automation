#!/usr/bin/env python3
"""Générateur de shows : une intention + le rig lu dans le donneur → un .wpj.

Ce que l'outil compose, c'est la **banque de presets** d'un show : une
ambiance de l'intention devient un preset nommé, posé sur une page libre,
avec sa couleur statique, ses dimmers par groupe, sa position et ses FX.
Le rig n'est pas décrit à la main — il est **lu dans le donneur** (groupes,
luminaires, positions nommées, palettes par groupe), ce qui évite d'inventer
un patch que rien ne validerait.

Trois choses qu'il ne fait pas, et pourquoi :
- il ne crée ni luminaire ni groupe ni profil : rien n'a été mesuré dans ce
  sens, et un patch synthétisé n'aurait aucune preuve derrière lui ;
- il n'écrit pas `165.f16` (les masques de moteurs) : il **choisit** un
  preset du donneur dont les moteurs correspondent à l'ambiance et le clone.
  Écrire f16 sans écrire son doublon `color_fx_actif`/`move_fx_actif`
  produirait un preset que l'appareil rend autrement que le fichier ne le
  dit (registre, ACC-03) ;
- il ne rappelle rien : le déploiement et le pilotage restent
  `wolfmix_experiment.py deploy` puis UNE ouverture manuelle, puis
  `wolfmix.py mode` + `wolfmix.py preset <id>`.

Usage :
  wpj_generate.py rig donneur.wpj                    le rig lu dans le donneur
  wpj_generate.py compose intention.json sortie.wpj  [--spec spec.json]
  wpj_generate.py                                    self-check (corpus)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpjlib
import wpj_codec
import wpj_show
import wpj_identities

GROUPES = "ABCDEFGH"
PADS = wpj_show.PADS_PAR_GROUPE
SINGLE = 9                     # `f30` : PATTERN = SINGLE — device-confirmed

# Bits de `165.f10`, dans l'ordre de l'écran PRESET EDIT ; un bit MIS =
# bascule ÉTEINTE = ce contenu-là n'est pas appliqué (F4-02).
BIT_COLOR, BIT_MOVE, BIT_BEAM, BIT_GOBO, BIT_LIVE, BIT_OTHER = range(6)

# Familles = l'état (couleur, mouvement, faisceau) des trois premiers
# moteurs de `f16`. Toutes ont le moteur COULEUR à l'arrêt : c'est ce qui
# rend la couleur statique de l'ambiance visible plutôt qu'écrasée par un
# Color FX. Échelle d'activité croissante.
FAMILLES = {
    "statique": (False, False, False),
    "faisceau": (False, False, True),
    "mouvement": (False, True, False),
    "mouvement+faisceau": (False, True, True),
}
# Paliers d'énergie — RÉGLAGES, pas des mesures : à retoucher sur le rig.
# (énergie max, famille, dimmer, effet de faisceau, vitesse %)
PALIERS = (
    (24, "statique", 120, None, None),
    (49, "faisceau", 180, 1, 45),            # 1 = Sparkle
    (74, "mouvement", 225, None, 110),
    (100, "mouvement+faisceau", 255, 2, 170),  # 2 = Chaser
)
_INTENTION_CLES = ("base", "nom", "page", "ambiances")
_AMBIANCE_CLES = ("nom", "energie", "couleur", "groupes", "position",
                  "modele", "dimmer", "live_edit")


# --- lecture du rig ----------------------------------------------------------

def _moteurs(preset):
    """Les douze tranches de 9 bits de `f16`, ou None si le champ manque."""
    h = preset.get("f16")
    if not isinstance(h, dict) or "hex" not in h:
        return None
    octets = wpj_identities._varints(h["hex"])
    if any(o > 255 for o in octets):
        return None
    gros = int.from_bytes(bytes(octets), "little")
    return [(gros >> (9 * i)) & 0x1FF for i in range(12)]


def lire_rig(chemin):
    """Le rig tel que le donneur le porte : groupes, luminaires, positions,
    palettes, et les presets utilisables comme modèles."""
    w = wpjlib.Wpj.load(chemin)
    profils = wpj_codec.decode(116, w.get(116)).get("profils", [])
    groupes = {g: [] for g in range(len(GROUPES))}
    # Chaque entrée de 115 est un luminaire réel — vérifié sur les 45 fichiers
    # du corpus : leur nombre égale celui des index `fixture` du record 105.
    # `adresse_dmx` absent = 0 = adresse DMX 1 (le champ est 0-based).
    for f in wpj_codec.decode(115, w.get(115)).get("fixtures", []):
        if not isinstance(f, dict):
            continue
        g = f.get("groupe", 0)
        if g in groupes:
            i = f.get("profil", 0)
            p = profils[i] if i < len(profils) and isinstance(profils[i], dict) \
                else {}
            groupes[g].append({"adresse_dmx": f.get("adresse_dmx", 0) + 1,
                               "profil": p.get("nom", "?"),
                               "nb_canaux": p.get("nb_canaux", 0)})
    positions = []
    for occ in range(len(GROUPES)):
        entrees = wpj_codec.decode(150, w.get(150, occ)).get("positions", [])
        positions.append({e["nom"]: i for i, e in enumerate(entrees)
                          if isinstance(e, dict) and e.get("nom")})
    palettes = []
    for occ in range(len(GROUPES)):
        pads = wpj_codec.decode(140, w.get(140, occ)).get("pads", [])
        palettes.append([(p.get("rouge", 0), p.get("vert", 0), p.get("bleu", 0))
                         for p in pads])
    presets = wpj_codec.decode(165, w.get(165)).get("presets", [])
    return {"fichier": chemin, "groupes": groupes, "positions": positions,
            "palettes": palettes, "presets": presets,
            "id_max": max(p.get("id", 0) for p in presets)}


def modeles(rig):
    """famille → id du preset du donneur qui la porte (le plus petit id)."""
    trouves = {}
    for p in rig["presets"]:
        if "id" not in p:                  # l'id 0 omet le champ : inclonable
            continue
        m = _moteurs(p)
        if m is None:
            continue
        etat = tuple(bool(m[i]) for i in range(3))
        for nom, attendu in FAMILLES.items():
            if etat == attendu and nom not in trouves:
                trouves[nom] = p["id"]
    return trouves


# --- composition -------------------------------------------------------------

def _couleur(valeur):
    v = valeur.lstrip("#") if isinstance(valeur, str) else None
    if not v or len(v) != 6:
        raise ValueError(f"couleur {valeur!r} : attendu « #rrggbb »")
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        raise ValueError(f"couleur {valeur!r} : attendu « #rrggbb »") from None


def _pad_le_plus_proche(palette, rgb):
    """Le pad 1-based dont la couleur est la plus proche, distance RGB au carré.
    Aucune écriture de palette : on choisit dans ce que le groupe porte déjà."""
    if not palette:
        return None
    ecart = [sum((a - b) ** 2 for a, b in zip(pad, rgb)) for pad in palette]
    return ecart.index(min(ecart)) + 1


def _palier(energie):
    for maxi, famille, dimmer, effet, vitesse in PALIERS:
        if energie <= maxi:
            return famille, dimmer, effet, vitesse
    raise ValueError(f"energie {energie} hors de [0, 100]")


def _famille_disponible(voulue, dispo):
    """La famille voulue, ou la plus proche vers le bas que le donneur porte."""
    echelle = list(FAMILLES)
    for nom in reversed(echelle[:echelle.index(voulue) + 1]):
        if nom in dispo:
            return nom
    raise ValueError(f"aucun preset du donneur ne porte la famille {voulue!r} "
                     f"ni une plus sobre ; familles trouvées : {sorted(dispo)}")


def composer(intention):
    """intention → (spec pour wpj_show.compiler, rapport ligne par ligne)."""
    wpj_show._cles(intention, _INTENTION_CLES, "intention")
    if "base" not in intention:
        raise ValueError("intention : clé 'base' (donneur .wpj) obligatoire")
    rig = lire_rig(intention["base"])
    dispo = modeles(rig)
    peuples = [g for g, f in rig["groupes"].items() if f]
    if not peuples:
        raise ValueError(f"{intention['base']} : aucun luminaire affecté à un "
                         "groupe A–H, il n'y a rien à piloter")
    page = intention.get("page") or rig["id_max"] // PADS + 2
    wpj_show._borne("intention", "page", page, 1, 10)
    if (page - 1) * PADS <= rig["id_max"]:
        raise ValueError(f"page {page} : ses ids commencent à "
                         f"{(page - 1) * PADS} et le donneur va déjà jusqu'à "
                         f"{rig['id_max']} — la création se fait en queue")

    presets, rapport = [], []
    for n, amb in enumerate(intention.get("ambiances", [])):
        wpj_show._cles(amb, _AMBIANCE_CLES, f"ambiance {n}")
        nom = amb.get("nom", f"CUE {n + 1}")
        energie = wpj_show._borne(f"ambiance {nom!r}", "energie",
                                  amb.get("energie", 50), 0, 100)
        famille, dimmer, effet, vitesse = _palier(energie)
        if "dimmer" in amb:               # l'énergie dit l'activité, pas la
            dimmer = wpj_show._borne(     # luminosité : override explicite
                f"ambiance {nom!r}", "dimmer", amb["dimmer"], 0, 255)
        famille = _famille_disponible(famille, dispo)
        _, mouvement, faisceau = FAMILLES[famille]
        modele = amb.get("modele", dispo[famille])
        pid = (page - 1) * PADS + n
        if "groupes" in amb:
            lus = [_index_groupe(nom, g) for g in amb["groupes"]]
            inconnus = [g for g in lus if g not in peuples]
            if inconnus:
                raise ValueError(f"ambiance {nom!r} : groupes sans luminaire "
                                 f"{[GROUPES[g] for g in inconnus]}")
        else:
            lus = peuples
        rgb = _couleur(amb["couleur"]) if "couleur" in amb else None
        pads = [[] for _ in GROUPES]
        if rgb is not None:
            for g in lus:
                pad = _pad_le_plus_proche(rig["palettes"][g], rgb)
                if pad:
                    pads[g] = [pad]

        entree = {"id": pid, "modele": modele, "nom": _coupe(nom),
                  "dimmers": [dimmer if g in lus else 0
                              for g in range(len(GROUPES))],
                  "masque_contenu": _masque(mouvement or "position" in amb,
                                            faisceau, rig, modele,
                                            amb.get("live_edit"))}
        if rgb is not None:
            entree["couleur_statique"] = pads
            entree["pattern_couleur"] = [SINGLE] * len(GROUPES)
        if "position" in amb:
            entree["positions"] = _positions(nom, amb["position"], rig, lus,
                                             modele)
        if faisceau and effet is not None:
            entree["beam_fx1"] = {"effet": effet, "vitesse": vitesse}
        if mouvement and vitesse is not None:
            # pas d'`effet` sur un slot Move : aucun enum n'est publié pour
            # cette famille, on ne pose que la vitesse.
            entree["move_fx1"] = {"vitesse": vitesse}
        presets.append(entree)
        rapport.append(f"id {pid:3d} (page {pid // PADS + 1} slot "
                       f"{pid % PADS + 1:2d})  {_coupe(nom):<19s}  "
                       f"énergie {energie:3d}  {famille:<18s} modèle {modele:3d}  "
                       f"groupes {''.join(GROUPES[g] for g in lus) or '-':<8s} "
                       f"pad {pads[lus[0]][0] if lus and pads[lus[0]] else '-'}")

    spec = {"base": intention["base"], "presets": presets}
    if "nom" in intention:
        spec["nom"] = intention["nom"]
    return spec, rapport


def _index_groupe(nom, lettre):
    if not isinstance(lettre, str) or lettre.upper() not in GROUPES:
        raise ValueError(f"ambiance {nom!r} : groupe {lettre!r} hors de A–H")
    return GROUPES.index(lettre.upper())


def _coupe(nom):
    """Tronque sur une frontière UTF-8 : au-delà de 19 octets, le projet
    ENTIER refuse de s'ouvrir (PRESET-05)."""
    b = nom.encode("utf-8")[:wpj_show.NOM_MAX_OCTETS]
    while b:
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            b = b[:-1]
    return "?"


def _masque(mouvement, faisceau, rig, modele, live_edit):
    """`f10` : COLOR et OTHER allumés (la couleur et les dimmers écrits sont
    lus), MOVE/BEAM selon la famille, GOBO éteint — on n'écrit pas de gobo.

    LIVE EDIT est repris du modèle par défaut. `live_edit: false` l'éteint —
    à faire pour toute cue destinée à une mesure : allumé, un geste au panneau
    réécrit la copie vive de la cue **sans toucher au fichier**, et le rappel
    mesure alors autre chose que ce qu'on croit avoir déployé. Ça a coûté une
    anomalie parfaitement reproductible qui pointait vers le mauvais champ
    (registre, « GEN-03 retiré »).
    """
    src = next((p for p in rig["presets"] if p.get("id", 0) == modele), {})
    if live_edit is None:
        masque = src.get("masque_contenu", 0) & (1 << BIT_LIVE)
    else:
        masque = 0 if live_edit else 1 << BIT_LIVE
    masque |= 1 << BIT_GOBO
    if not mouvement:
        masque |= 1 << BIT_MOVE
    if not faisceau:
        masque |= 1 << BIT_BEAM
    return masque


def _positions(nom, voulue, rig, lus, modele):
    """L'index de la position nommée, par groupe. Le record 150 existe une
    fois par groupe, donc l'index peut différer d'un groupe à l'autre. Un
    groupe éteint garde celle du modèle : sinon on ferait voyager des
    projecteurs noirs."""
    src = next((p for p in rig["presets"] if p.get("id", 0) == modele), {})
    defaut = src.get("positions") or [0] * len(GROUPES)
    sortie = []
    for g in range(len(GROUPES)):
        table = rig["positions"][g]
        if g not in lus:
            sortie.append(defaut[g] if g < len(defaut) else 0)
        elif voulue in table:
            sortie.append(table[voulue])
        else:
            raise ValueError(f"ambiance {nom!r} : position {voulue!r} absente "
                             f"du groupe {GROUPES[g]} ; disponibles : "
                             f"{sorted(table)}")
    return sortie


# --- sorties -----------------------------------------------------------------

def imprime_rig(rig):
    print(f"donneur : {rig['fichier']}")
    print(f"presets : {len(rig['presets'])}, id max {rig['id_max']} "
          f"(page {rig['id_max'] // PADS + 1}) ; première page libre : "
          f"{rig['id_max'] // PADS + 2}")
    print("\ngroupes")
    for g, fixtures in rig["groupes"].items():
        if not fixtures:
            continue
        detail = ", ".join(f"{f['profil']} ×{sum(1 for x in fixtures if x['profil'] == f['profil'])}"
                           for f in {x["profil"]: x for x in fixtures}.values())
        adr = ", ".join(str(f["adresse_dmx"]) for f in fixtures)
        print(f"  {GROUPES[g]} : {len(fixtures):2d} luminaires — {detail}")
        print(f"      adresses DMX (1-based) : {adr}")
    print("\npositions nommées, par groupe")
    for g, table in enumerate(rig["positions"]):
        if rig["groupes"][g] and table:
            print(f"  {GROUPES[g]} : " + ", ".join(sorted(table)))
    print("\nmodèles disponibles (famille → id du preset cloné)")
    for famille in FAMILLES:
        trouve = modeles(rig).get(famille)
        nom = next((p.get("nom", "?") for p in rig["presets"]
                    if p.get("id", 0) == trouve), None)
        print(f"  {famille:<18s} {trouve if trouve is not None else '— absent'}"
              + (f"  « {nom} »" if nom else ""))


def main(argv):
    if not argv:
        demo()
        return 0
    if argv[0] == "rig" and len(argv) == 2:
        imprime_rig(lire_rig(argv[1]))
        return 0
    if argv[0] == "compose" and len(argv) >= 3:
        intention = json.load(open(argv[1], encoding="utf-8"))
        spec, rapport = composer(intention)
        if "--spec" in argv:
            chemin = argv[argv.index("--spec") + 1]
            with open(chemin, "x", encoding="utf-8") as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
            print(f"spec : {chemin}")
        diffs = wpj_show.compiler(spec, argv[2])
        for ligne in rapport:
            print(ligne)
        for t, occ, la, lb in diffs:
            print(f"record {t} occ {occ} : {la} -> {lb} octets")
        print(f"ok : {argv[2]}")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


def demo():
    """Compose un show de trois ambiances sur le premier donneur utilisable."""
    for base in wpjlib.corpus_files():
        try:
            return _demo_sur(base)
        except (ValueError, KeyError, StopIteration, OSError):
            continue
    return wpjlib.pas_de_corpus("wpj_generate")


def _demo_sur(base):
    import tempfile
    rig = lire_rig(base)
    peuples = [g for g, f in rig["groupes"].items() if f]
    assert peuples, "donneur sans groupe peuplé"
    intention = {"base": base, "nom": "WMX GEN DEMO",
                 "ambiances": [
                     {"nom": "ouverture douce", "energie": 10,
                      "couleur": "#ff0000",
                      "groupes": [GROUPES[peuples[0]]]},
                     {"nom": "montée", "energie": 60, "couleur": "#0000ff"},
                     {"nom": "un nom beaucoup trop long pour la mémoire",
                      "energie": 95, "couleur": "#ffffff"}]}
    spec, rapport = composer(intention)
    assert len(spec["presets"]) == 3 and len(rapport) == 3
    ids = [p["id"] for p in spec["presets"]]
    assert ids == [ids[0], ids[0] + 1, ids[0] + 2] and ids[0] > rig["id_max"]
    # le nom trop long est coupé AVANT le compilateur, qui le refuserait
    assert all(len(p["nom"].encode("utf-8")) <= wpj_show.NOM_MAX_OCTETS
               for p in spec["presets"])
    # rouge demandé sur la première ambiance → un pad, et le plus rouge
    pads = spec["presets"][0]["couleur_statique"]
    g = peuples[0]
    assert len(pads[g]) == 1, pads
    palette = rig["palettes"][g]
    assert palette[pads[g][0] - 1] == max(palette, key=lambda c:
                                          -sum((a - b) ** 2 for a, b in
                                               zip(c, (255, 0, 0))))
    # groupes non nommés = éteints, et pas de couleur posée dessus
    d = spec["presets"][0]["dimmers"]
    assert d[g] > 0 and all(v == 0 for i, v in enumerate(d) if i != g)
    assert all(not pads[i] for i in range(len(GROUPES)) if i != g)
    # le masque de contenu laisse COLOR et OTHER allumés dans les trois cas
    for p in spec["presets"]:
        assert not p["masque_contenu"] & (1 << BIT_COLOR)
        assert not p["masque_contenu"] & (1 << BIT_OTHER)
    # live_edit: false verrouille la cue contre une réécriture au panneau
    verrou, _ = composer({**intention, "ambiances": [
        {**intention["ambiances"][0], "live_edit": False}]})
    assert verrou["presets"][0]["masque_contenu"] & (1 << BIT_LIVE)
    ouvert, _ = composer({**intention, "ambiances": [
        {**intention["ambiances"][0], "live_edit": True}]})
    assert not ouvert["presets"][0]["masque_contenu"] & (1 << BIT_LIVE)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "gen.wpj")
        diffs = wpj_show.compiler(spec, out)
        assert {(t, o) for t, o, *_ in diffs} == {(101, 0), (165, 0)}, diffs
        w = wpjlib.Wpj.load(out)
        presets = wpj_codec.decode(165, w.get(165))["presets"]
        assert [p.get("id") for p in presets[-3:]] == ids
        assert wpj_show.masques_vers_pads(
            presets[-3]["couleur_statique"])[g] == pads[g]
        # une page déjà occupée est refusée
        try:
            composer({**intention, "page": 1})
            raise AssertionError("page occupée : erreur attendue")
        except ValueError:
            pass
        # une position inconnue est refusée, avec la liste des connues
        try:
            composer({**intention, "ambiances": [
                {"nom": "x", "energie": 50, "position": "Nulle Part"}]})
            raise AssertionError("position inconnue : erreur attendue")
        except ValueError:
            pass
    print(f"self-check ok : 3 ambiances composées et compilées sur "
          f"{os.path.basename(base)}", file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (ValueError, KeyError, OSError) as e:
        print(f"erreur : {e}", file=sys.stderr)
        sys.exit(1)
