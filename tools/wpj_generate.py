#!/usr/bin/env python3
"""Show generator: an intention + the rig read from the donor → a .wpj.

What this composes is a show's **preset bank**: one mood of the intention
becomes a named preset, placed on a free page, with its static colour, its
per-group dimmers, its position and its FX. The rig is not described by hand —
it is **read from the donor** (groups, fixtures, named positions, per-group
palettes), which avoids inventing a patch nothing would validate.

Three things it does not do, and why:
- it creates no fixture, no group and no profile: nothing was measured in that
  direction, and a synthesised patch would have no evidence behind it;
- it does not write `165.f16` (the engine masks): it **picks** a donor preset
  whose engines match the mood, and clones it. Writing f16 without writing its
  twin `color_fx_active`/`move_fx_active` would produce a preset the device
  renders differently from what the file says (registry, ACC-03);
- it recalls nothing: deploying and driving stay
  `wolfmix_experiment.py deploy`, then ONE manual open, then `wolfmix.py mode`
  + `wolfmix.py preset <id>`.

Usage:
  wpj_generate.py rig donor.wpj                     the rig read from the donor
  wpj_generate.py compose intention.json out.wpj    [--spec spec.json]
  wpj_generate.py                                   self-check (corpus)
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
SINGLE = 9                     # `f30`: PATTERN = SINGLE — device-confirmed

# Bits of `165.f10`, in PRESET EDIT screen order; a SET bit = the toggle is
# OFF = that content is not applied (F4-02).
BIT_COLOR, BIT_MOVE, BIT_BEAM, BIT_GOBO, BIT_LIVE, BIT_OTHER = range(6)

# Families = the (colour, move, beam) state of the first three engines of
# `f16`. All of them keep the COLOUR engine off: that is what makes the mood's
# static colour visible instead of being overwritten by a Color FX. Ordered by
# increasing activity.
FAMILLES = {
    "static": (False, False, False),
    "beam": (False, False, True),
    "move": (False, True, False),
    "move+beam": (False, True, True),
}
# Energy steps — SETTINGS, not measurements: retune them on your rig.
# (max energy, family, dimmer, beam effect, speed %)
# The 45/110/170 speeds from before FX6-02 went to f2 believing they set the
# speed: f2 is the fade, so the two upper steps lengthened the fade instead of
# speeding the effect up — and 110/170 fell into the "Flick" range. The `speed`
# key now targets f9, and the steps fit inside 0–100.
PALIERS = (
    (24, "static", 120, None, None),
    (49, "beam", 180, 1, 45),                  # 1 = Sparkle
    (74, "move", 225, None, 70),
    (100, "move+beam", 255, 2, 95),            # 2 = Chaser
)
_INTENTION_CLES = ("base", "name", "page", "moods")
_AMBIANCE_CLES = ("name", "energy", "color", "groups", "position",
                  "template", "dimmer", "live_edit")


# --- reading the rig ---------------------------------------------------------

def _moteurs(preset):
    """The twelve 9-bit slices of `f16`, or None when the field is missing."""
    h = preset.get("f16")
    if not isinstance(h, dict) or "hex" not in h:
        return None
    octets = wpj_identities._varints(h["hex"])
    if any(o > 255 for o in octets):
        return None
    gros = int.from_bytes(bytes(octets), "little")
    return [(gros >> (9 * i)) & 0x1FF for i in range(12)]


def lire_rig(chemin):
    """The rig as the donor carries it: groups, fixtures, positions, palettes,
    and the presets usable as templates."""
    w = wpjlib.Wpj.load(chemin)
    profils = wpj_codec.decode(116, w.get(116)).get("profiles", [])
    groupes = {g: [] for g in range(len(GROUPES))}
    # Every entry of 115 is a real fixture — checked over the corpus files:
    # their count equals the number of `fixture` indexes in record 105.
    # An absent `dmx_address` = 0 = DMX address 1 (the field is 0-based).
    for f in wpj_codec.decode(115, w.get(115)).get("fixtures", []):
        if not isinstance(f, dict):
            continue
        g = f.get("group", 0)
        if g in groupes:
            i = f.get("profile", 0)
            p = profils[i] if i < len(profils) and isinstance(profils[i], dict) \
                else {}
            groupes[g].append({"dmx_address": f.get("dmx_address", 0) + 1,
                               "profile": p.get("name", "?"),
                               "channel_count": p.get("channel_count", 0)})
    positions = []
    for occ in range(len(GROUPES)):
        entrees = wpj_codec.decode(150, w.get(150, occ)).get("positions", [])
        positions.append({e["name"]: i for i, e in enumerate(entrees)
                          if isinstance(e, dict) and e.get("name")})
    palettes = []
    for occ in range(len(GROUPES)):
        pads = wpj_codec.decode(140, w.get(140, occ)).get("pads", [])
        palettes.append([(p.get("red", 0), p.get("green", 0), p.get("blue", 0))
                         for p in pads])
    presets = wpj_codec.decode(165, w.get(165)).get("presets", [])
    return {"fichier": chemin, "groups": groupes, "positions": positions,
            "palettes": palettes, "presets": presets,
            "id_max": max(p.get("id", 0) for p in presets)}


def modeles(rig):
    """family → id of the donor preset that carries it (the smallest id)."""
    trouves = {}
    for p in rig["presets"]:
        if "id" not in p:                  # id 0 omits the field: not clonable
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
    """The 1-based pad whose colour is nearest, squared RGB distance. No palette
    is written: we choose from what the group already carries."""
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
    """The family asked for, or the nearest one below that the donor carries."""
    echelle = list(FAMILLES)
    for nom in reversed(echelle[:echelle.index(voulue) + 1]):
        if nom in dispo:
            return nom
    raise ValueError(f"no donor preset carries the family {voulue!r} nor a "
                     f"quieter one; families found: {sorted(dispo)}")


def composer(intention):
    """intention → (spec for wpj_show.compiler, a line-by-line report)."""
    wpj_show.cles(intention, _INTENTION_CLES, "intention")
    if "base" not in intention:
        raise ValueError("intention: the 'base' key (donor .wpj) is required")
    rig = lire_rig(intention["base"])
    dispo = modeles(rig)
    peuples = [g for g, f in rig["groups"].items() if f]
    if not peuples:
        raise ValueError(f"{intention['base']}: no fixture assigned to a group "
                         "A–H, there is nothing to drive")
    page = intention.get("page") or rig["id_max"] // PADS + 2
    wpj_show.borne("intention", "page", page, 1, 10)
    if (page - 1) * PADS <= rig["id_max"]:
        raise ValueError(f"page {page}: its ids start at {(page - 1) * PADS} "
                         f"and the donor already reaches {rig['id_max']} — "
                         "creation happens at the tail")

    presets, rapport = [], []
    for n, amb in enumerate(intention.get("moods", [])):
        wpj_show.cles(amb, _AMBIANCE_CLES, f"ambiance {n}")
        nom = amb.get("name", f"CUE {n + 1}")
        energie = wpj_show.borne(f"ambiance {nom!r}", "energy",
                                  amb.get("energy", 50), 0, 100)
        famille, dimmer, effet, vitesse = _palier(energie)
        if "dimmer" in amb:               # energy says activity, not
            dimmer = wpj_show.borne(      # brightness: an explicit override
                f"ambiance {nom!r}", "dimmer", amb["dimmer"], 0, 255)
        famille = _famille_disponible(famille, dispo)
        _, mouvement, faisceau = FAMILLES[famille]
        modele = amb.get("template", dispo[famille])
        pid = (page - 1) * PADS + n
        if "groups" in amb:
            lus = [_index_groupe(nom, g) for g in amb["groups"]]
            inconnus = [g for g in lus if g not in peuples]
            if inconnus:
                raise ValueError(f"mood {nom!r}: groups with no fixture "
                                 f"{[GROUPES[g] for g in inconnus]}")
        else:
            lus = peuples
        rgb = _couleur(amb["color"]) if "color" in amb else None
        pads = [[] for _ in GROUPES]
        if rgb is not None:
            for g in lus:
                pad = _pad_le_plus_proche(rig["palettes"][g], rgb)
                if pad:
                    pads[g] = [pad]

        entree = {"id": pid, "template": modele, "name": _coupe(nom),
                  "dimmers": [dimmer if g in lus else 0
                              for g in range(len(GROUPES))],
                  "content_mask": _masque(mouvement or "position" in amb,
                                            faisceau, rig, modele,
                                            amb.get("live_edit"))}
        if rgb is not None:
            entree["static_color"] = pads
            entree["color_pattern"] = [SINGLE] * len(GROUPES)
        if "position" in amb:
            entree["positions"] = _positions(nom, amb["position"], rig, lus,
                                             modele)
        if faisceau and effet is not None:
            entree["beam_fx1"] = {"effect": effet, "speed": vitesse}
        if mouvement and vitesse is not None:
            # no `effect` on a Move slot: no enum is published for that
            # family, so only the speed is set.
            entree["move_fx1"] = {"speed": vitesse}
        presets.append(entree)
        rapport.append(f"id {pid:3d} (page {pid // PADS + 1} slot "
                       f"{pid % PADS + 1:2d})  {_coupe(nom):<19s}  "
                       f"energy {energie:3d}  {famille:<18s} template {modele:3d}  "
                       f"groupes {''.join(GROUPES[g] for g in lus) or '-':<8s} "
                       f"pad {pads[lus[0]][0] if lus and pads[lus[0]] else '-'}")

    spec = {"base": intention["base"], "presets": presets}
    if "name" in intention:
        spec["name"] = intention["name"]
    return spec, rapport


def _index_groupe(nom, lettre):
    if not isinstance(lettre, str) or lettre.upper() not in GROUPES:
        raise ValueError(f"ambiance {nom!r} : groupe {lettre!r} hors de A–H")
    return GROUPES.index(lettre.upper())


def _coupe(nom):
    """Truncates on a UTF-8 boundary: past 19 bytes, the project
    ENTIER refuse de s'ouvrir (PRESET-05)."""
    b = nom.encode("utf-8")[:wpj_show.NOM_MAX_OCTETS]
    while b:
        try:
            return b.decode("utf-8")
        except UnicodeDecodeError:
            b = b[:-1]
    return "?"


def _masque(mouvement, faisceau, rig, modele, live_edit):
    """`f10`: COLOR and OTHER on (the colour and the dimmers written are read),
    MOVE/BEAM per the family, GOBO off — we write no gobo.

    LIVE EDIT is taken from the template by default. `live_edit: false` turns it
    off — do that for any cue meant for a measurement: with it on, one gesture
    at the panel rewrites the cue's live copy **without touching the file**, and
    the recall then measures something other than what was deployed. That cost
    us a perfectly reproducible anomaly pointing at the wrong field (registry,
    "GEN-03 withdrawn").
    """
    src = next((p for p in rig["presets"] if p.get("id", 0) == modele), {})
    if live_edit is None:
        masque = src.get("content_mask", 0) & (1 << BIT_LIVE)
    else:
        masque = 0 if live_edit else 1 << BIT_LIVE
    masque |= 1 << BIT_GOBO
    if not mouvement:
        masque |= 1 << BIT_MOVE
    if not faisceau:
        masque |= 1 << BIT_BEAM
    return masque


def _positions(nom, voulue, rig, lus, modele):
    """The index of the named position, per group. Record 150 exists once per
    group, so the index can differ from one group to the next. A group that is
    off keeps the template's: otherwise we would move
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
                             f"of group {GROUPES[g]}; available: "
                             f"{sorted(table)}")
    return sortie


# --- sorties -----------------------------------------------------------------

def imprime_rig(rig):
    print(f"donneur : {rig['fichier']}")
    print(f"presets : {len(rig['presets'])}, id max {rig['id_max']} "
          f"(page {rig['id_max'] // PADS + 1}); first free page: "
          f"{rig['id_max'] // PADS + 2}")
    print("\ngroupes")
    for g, fixtures in rig["groups"].items():
        if not fixtures:
            continue
        detail = ", ".join(f"{f['profile']} ×{sum(1 for x in fixtures if x['profile'] == f['profile'])}"
                           for f in {x["profile"]: x for x in fixtures}.values())
        adr = ", ".join(str(f["dmx_address"]) for f in fixtures)
        print(f"  {GROUPES[g]} : {len(fixtures):2d} luminaires — {detail}")
        print(f"      adresses DMX (1-based) : {adr}")
    print("\nnamed positions, per group")
    for g, table in enumerate(rig["positions"]):
        if rig["groups"][g] and table:
            print(f"  {GROUPES[g]} : " + ", ".join(sorted(table)))
    print("\navailable templates (family → id of the cloned preset)")
    for famille in FAMILLES:
        trouve = modeles(rig).get(famille)
        nom = next((p.get("name", "?") for p in rig["presets"]
                    if p.get("id", 0) == trouve), None)
        print(f"  {famille:<18s} {trouve if trouve is not None else '— absent'}"
              + (f"  « {nom} »" if nom else ""))


def main(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commandes = parseur.add_subparsers(dest="commande")
    rig_cmd = commandes.add_parser(
        "rig", help="what a donor project offers: groups, palettes, ids")
    rig_cmd.add_argument("projet")
    compose_cmd = commandes.add_parser(
        "compose", help="a JSON intention in, a project out")
    compose_cmd.add_argument("intention", help="the intention file")
    compose_cmd.add_argument("sortie", help="new project; an existing one is refused")
    compose_cmd.add_argument("--spec", help="also write the intermediate "
                                            "wpj_show spec to this new file")
    args = parseur.parse_args(argv)
    if args.commande is None:
        demo()
        return 0
    if args.commande == "rig":
        imprime_rig(lire_rig(args.projet))
        return 0
    with open(args.intention, encoding="utf-8") as flux:
        intention = json.load(flux)
    spec, rapport = composer(intention)
    if args.spec:
        with open(args.spec, "x", encoding="utf-8") as flux:
            json.dump(spec, flux, ensure_ascii=False, indent=2)
        print(f"spec : {args.spec}")
    diffs = wpj_show.compiler(spec, args.sortie)
    for ligne in rapport:
        print(ligne)
    for t, occ, la, lb in diffs:
        print(f"record {t} occ {occ}: {la} -> {lb} bytes")
    print(f"ok : {args.sortie}")
    return 0


def demo():
    """Composes a three-mood show on the first usable donor."""
    for base in wpjlib.corpus_files():
        try:
            return _demo_sur(base)
        except (ValueError, KeyError, StopIteration, OSError):
            continue
    return wpjlib.pas_de_corpus("wpj_generate")


def _demo_sur(base):
    import tempfile
    rig = lire_rig(base)
    peuples = [g for g, f in rig["groups"].items() if f]
    assert peuples, "donor with no populated group"
    intention = {"base": base, "name": "WMX GEN DEMO",
                 "moods": [
                     {"name": "ouverture douce", "energy": 10,
                      "color": "#ff0000",
                      "groups": [GROUPES[peuples[0]]]},
                     {"name": "build-up", "energy": 60, "color": "#0000ff"},
                     {"name": "a name far too long for the memory",
                      "energy": 95, "color": "#ffffff"}]}
    spec, rapport = composer(intention)
    assert len(spec["presets"]) == 3 and len(rapport) == 3
    ids = [p["id"] for p in spec["presets"]]
    assert ids == [ids[0], ids[0] + 1, ids[0] + 2] and ids[0] > rig["id_max"]
    # the over-long name is cut BEFORE the compiler, which would refuse it
    assert all(len(p["name"].encode("utf-8")) <= wpj_show.NOM_MAX_OCTETS
               for p in spec["presets"])
    # red asked for on the first mood → one pad, and the reddest one
    pads = spec["presets"][0]["static_color"]
    g = peuples[0]
    assert len(pads[g]) == 1, pads
    palette = rig["palettes"][g]
    assert palette[pads[g][0] - 1] == max(palette, key=lambda c:
                                          -sum((a - b) ** 2 for a, b in
                                               zip(c, (255, 0, 0))))
    # groups not named = off, and no colour placed on them
    d = spec["presets"][0]["dimmers"]
    assert d[g] > 0 and all(v == 0 for i, v in enumerate(d) if i != g)
    assert all(not pads[i] for i in range(len(GROUPES)) if i != g)
    # the content mask leaves COLOR and OTHER on in all three cases
    for p in spec["presets"]:
        assert not p["content_mask"] & (1 << BIT_COLOR)
        assert not p["content_mask"] & (1 << BIT_OTHER)
    # live_edit: false locks the cue against a rewrite at the panel
    verrou, _ = composer({**intention, "moods": [
        {**intention["moods"][0], "live_edit": False}]})
    assert verrou["presets"][0]["content_mask"] & (1 << BIT_LIVE)
    ouvert, _ = composer({**intention, "moods": [
        {**intention["moods"][0], "live_edit": True}]})
    assert not ouvert["presets"][0]["content_mask"] & (1 << BIT_LIVE)
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "gen.wpj")
        diffs = wpj_show.compiler(spec, out)
        assert {(t, o) for t, o, *_ in diffs} == {(101, 0), (165, 0)}, diffs
        w = wpjlib.Wpj.load(out)
        presets = wpj_codec.decode(165, w.get(165))["presets"]
        assert [p.get("id") for p in presets[-3:]] == ids
        assert wpj_show.masques_vers_pads(
            presets[-3]["static_color"])[g] == pads[g]
        # a page already occupied is refused
        try:
            composer({**intention, "page": 1})
            raise AssertionError("occupied page: an error was expected")
        except ValueError:
            pass
        # an unknown position is refused, with the list of known ones
        try:
            composer({**intention, "moods": [
                {"name": "x", "energy": 50, "position": "Nulle Part"}]})
            raise AssertionError("unknown position: an error was expected")
        except ValueError:
            pass
    print(f"self-check ok: 3 moods composed and compiled on "
          f"{os.path.basename(base)}", file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError) as e:
        print(f"erreur : {e}", file=sys.stderr)
        sys.exit(1)
