#!/usr/bin/env python3
"""Compile a DMX patch into a variant-A project — no donor carries the patch.

The patch is eight record types the device derives from three things: a
**profile**, a **DMX address** and a **group** per fixture. This tool derives
them the same way, from profile *packages* read off projects the device wrote:

- 116 catalogue, 110 channels, 111 ranges — the profile, re-offset;
- 105 index (display order), 106 roles (fixture-index order), 120 values
  (DMX-address order) with its 16-bit pairing and the occupancy map;
- 125 group masks, and the eight 145 gobo palettes cut from the wheels.

Everything else — palettes, sequences, presets, the flash settings — comes
from a **skeleton**: a project of the operator's own, ideally one the W1
created from nothing, so the vendor's defaults are the device's and not ours.

The oracle is the corpus: `demo()` rebuilds every device-written file's patch
from its own packages and compares bytes. A record that does not come back
identical is a rule this file does not know, and the count is printed rather
than rounded. Unknown fields pass through verbatim; `115.f6`/`f7` are never
synthesised (COV-63); a wheel's `106.f5`/`f6` are recomputed because they are
its slice of record 111, not travel limits (COV-65).

  wpj_patch.py profiles a.wpj [b.wpj …]     the packages those files carry
  wpj_patch.py build rig.json out.wpj        compile, write (mode x), verify
  wpj_patch.py                               self-check on the corpus
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpjlib          # noqa: E402
import wpj_codec       # noqa: E402
import wpj_identities  # noqa: E402

ROUES = (11, 12)           # 106 roles whose f5/f6 are the wheel's 111 slice
AXES = (1, 2)              # pan and tilt: f5/f6 are the fixture's travel limits
PLEINE_COURSE = (0, 255)   # what a fresh patch writes for them (COV-24, stage0)
GOBO_WHEEL = 8             # 110.f4 of a gobo wheel
UNIVERS = 512
GROUPES = "ABCDEFGH"


# --- helpers ------------------------------------------------------------------

def _dec(w, typ, occ=0):
    d = wpj_codec.decode(typ, w.get(typ, occ))
    if set(d) == {"raw"}:
        raise ValueError(f"record {typ} occ {occ}: not decodable")
    return d


def _numero(schema, cle):
    for f, (nom, _) in schema.items():
        if nom == cle:
            return f
    if cle.startswith("f") and cle[1:].isdigit():
        return int(cle[1:])
    raise KeyError(cle)


def _ordonne(d, schema):
    """A dict in wire order — the encoder writes keys as they come, and the
    device writes fields by ascending number."""
    return {k: d[k] for k in sorted(d, key=lambda k: _numero(schema, k))}


def _sans_zero(d):
    return {k: v for k, v in d.items() if v not in (0, None, "", [])}


def _sous(typ, cle):
    return wpj_codec.SCHEMAS[typ][_numero(wpj_codec.SCHEMAS[typ], cle)][1]


# --- packages: a profile as the device wrote it ------------------------------

def paquets(w):
    """The packages of one variant-A project, indexed like its record 116.

    `blocs`, `library_id`, `drapeaux_115` and `gabarit_120` come from the first
    fixture using the profile; `gabarit_120` is None when the file's record
    120 does not count what the patch requires (the COV-53 defect)."""
    p105 = _dec(w, 105).get("patch", [])
    p106 = _dec(w, 106).get("channel_roles", [])
    p110 = _dec(w, 110).get("channels", [])
    p111 = _dec(w, 111).get("ranges", [])
    p115 = _dec(w, 115).get("fixtures", [])
    p116 = _dec(w, 116).get("profiles", [])
    p120 = _dec(w, 120).get("channels", [])
    ordre_dmx = sorted(range(len(p115)),
                       key=lambda i: (p115[i].get("dmx_address", 0), i))
    debut, k = {}, 0
    for i in ordre_dmx:
        debut[i] = k
        k += p116[p115[i].get("profile", 0)]["channel_count"]
    propre_120 = k == len(p120)
    out = []
    for pi, pr in enumerate(p116):
        off, n = pr.get("offset_110", 0), pr["channel_count"]
        canaux = []
        for j in range(n):
            c = dict(p110[off + j])
            o = c.pop("offset_111", 0)
            canaux.append({"champs": c,
                           "ranges": list(p111[o:o + c.get("range_count", 0)])})
        pk = {"uuid": pr.get("uuid"), "name": pr.get("name", ""),
              "entree_116": {a: b for a, b in pr.items() if a != "offset_110"},
              "canaux": canaux, "blocs": None, "library_id": None,
              "drapeaux_115": None, "gabarit_120": None}
        fi = next((i for i, f in enumerate(p115) if f.get("profile", 0) == pi),
                  None)
        if fi is not None:
            fx = p115[fi]
            base = fx.get("dmx_address", 0)
            blocs = []
            for e in p105:
                if e.get("fixture", 0) != fi:
                    continue
                pk["library_id"] = e.get("library_id", 0)
                ents = []
                a = e.get("offset_106", 0)
                for ent in p106[a:a + e.get("entry_count_106", 0)]:
                    ent = dict(ent)
                    ent["dmx_channel"] = ent.get("dmx_channel", 0) - base
                    if ent.get("role", 0) in ROUES + AXES:
                        ent.pop("limit_low", None)
                        ent.pop("limit_high", None)
                    ents.append(ent)
                blocs.append(ents)
            pk["blocs"] = blocs
            pk["drapeaux_115"] = {a: b for a, b in fx.items()
                                  if a not in ("dmx_address", "profile", "group",
                                               "slot_id", "f5", "f6", "f7")}
            if propre_120:
                gab = []
                for j in range(n):
                    e = dict(p120[debut[fi] + j])
                    e.pop("pair_half", None)
                    e.pop("partner_channel", None)
                    gab.append(e)
                pk["gabarit_120"] = gab
        out.append(pk)
    return out


def rig_du_fichier(w):
    """The rig a file describes, in the form `compiler` takes — the oracle's
    input, so the partial fields of 125 and the 115 flags travel through."""
    p115 = _dec(w, 115)
    p116 = _dec(w, 116).get("profiles", [])
    p125 = _dec(w, 125).get("groups", [])
    fixtures = [{"profile": f.get("profile", 0), "address": f.get("dmx_address", 0),
                 "group": f.get("group", 0), "slot_id": f.get("slot_id", 0),
                 "limits": {}}
                for f in p115["fixtures"]]
    p106 = _dec(w, 106).get("channel_roles", [])
    for e in _dec(w, 105).get("patch", []):
        fx = fixtures[e.get("fixture", 0)]
        a = e.get("offset_106", 0)
        for ent in p106[a:a + e.get("entry_count_106", 0)]:
            if ent.get("role", 0) in AXES:
                fx["limits"][ent["role"]] = (ent.get("limit_low", 0),
                                             ent.get("limit_high", 0))
    groupes = []
    for g in p125:
        d = {a: b for a, b in g.items() if a != "mask"}
        d["f4_tail"] = g["mask"]["f4_tail"]
        groupes.append(d)
    ordre = p115.get("display_order")
    return {"profiles": list(range(len(p116))), "fixtures": fixtures,
            "gobo_names": [[g.get("name") for g in _dec(w, 145, gi).get("gobos", [])]
                           for gi in range(8)],
            "display_order": list(bytes.fromhex(ordre)) if ordre else None,
            "groups": groupes}


# --- the compiler --------------------------------------------------------------

def _palette_145(paquets_groupe, noms=()):
    """The gobo pads of a group: the wheel's ranges after the open slot, up to
    the first range of another function (SPEC §3.4). `noms` names pads by
    position — operator data, never derived."""
    ids = []
    for pk in paquets_groupe:
        for c in pk["canaux"]:
            if c["champs"].get("feature") != GOBO_WHEEL:
                continue
            r = c["ranges"]
            fonction = r[1].get("function") if len(r) > 1 else None
            for x in r[1:]:
                if x.get("function") != fonction:
                    break
                ids.append(x.get("gobo_id"))
    if not ids:
        return [{} for _ in range(20)]
    pads = [_sans_zero({"glyph": chr(33 + i), "gobo_id": g})
            for i, g in enumerate(ids[:20])]
    pads += [{"glyph": " "}] * (20 - len(pads))
    for i, nom in enumerate(noms[:20]):
        if nom:
            pads[i]["name"] = nom
    return pads


def _occupation(occupe):
    runs, cur, ln = [], None, 0

    def flush():
        v, n = (128 if cur else 0), ln
        while n > 127:
            runs.append(v + 127)
            n -= 127
        if n:
            runs.append(v + n)
    for ch in range(UNIVERS):
        o = ch in occupe
        if o == cur:
            ln += 1
        else:
            if cur is not None:
                flush()
            cur, ln = o, 1
    flush()
    return runs


def compiler(paquets, rig):
    """rig -> {typ: [(occ, payload)]} for 105 106 110 111 115 116 120 125 and
    the eight 145. `paquets` is a list, `rig["profiles"]` indexes into it.
    Raises on a profile without a full package."""
    profils = [paquets[i] for i in rig["profiles"]]
    for pk in profils:
        if pk["blocs"] is None or pk["gabarit_120"] is None:
            raise ValueError(f"profile {pk['name']!r}: no clean fixture to "
                             f"learn the patch from")
    fixtures = rig["fixtures"]
    n = len(fixtures)
    # 116 / 110 / 111
    e116, e110, e111, off110, off111 = [], [], [], 0, 0
    base111 = []
    for pk in profils:
        e116.append(_ordonne(_sans_zero({**pk["entree_116"], "offset_110": off110}),
                             _sous(116, "profiles")))
        base111.append(off111)
        for c in pk["canaux"]:
            e110.append(_ordonne(_sans_zero({**c["champs"], "offset_111": off111}),
                                 _sous(110, "channels")))
            e111.extend(c["ranges"])
            off111 += c["champs"].get("range_count", 0)
        off110 += len(pk["canaux"])
    # 106 in fixture-index order, 105 in display order pointing into it
    e106, offsets = [], []
    for fx in fixtures:
        pk = profils[fx["profile"]]
        base = fx["address"]
        debut111 = [base111[fx["profile"]]]
        for c in pk["canaux"]:
            debut111.append(debut111[-1] + c["champs"].get("range_count", 0))
        offs = []
        for bloc in pk["blocs"]:
            offs.append(len(e106))
            for ent in bloc:
                e = dict(ent)
                rel = e["dmx_channel"]
                e["dmx_channel"] = base + rel
                if e.get("role", 0) in ROUES:
                    e["limit_low"] = debut111[rel]
                    e["limit_high"] = pk["canaux"][rel]["champs"].get("range_count", 0)
                elif e.get("role", 0) in AXES:
                    lo, hi = fx.get("limits", {}).get(e["role"], PLEINE_COURSE)
                    e["limit_low"], e["limit_high"] = lo, hi
                e106.append(_ordonne(_sans_zero(e), _sous(106, "channel_roles")))
        offsets.append(offs)
    ordre = rig.get("display_order") or list(range(n))
    e105 = []
    for i in ordre:
        fx = fixtures[i]
        pk = profils[fx["profile"]]
        for b, bloc in enumerate(pk["blocs"]):
            e105.append(_ordonne(_sans_zero(
                {"library_id": pk["library_id"], "offset_106": offsets[i][b],
                 "fixture": i, "group": fx["group"], "entry_count_106": len(bloc)}),
                _sous(105, "patch")))
    # 115
    e115 = []
    for fx in fixtures:
        pk = profils[fx["profile"]]
        e115.append(_ordonne(_sans_zero(
            {**pk["drapeaux_115"], "dmx_address": fx["address"],
             "profile": fx["profile"], "group": fx["group"], "f5": 65535,
             "slot_id": fx.get("slot_id", 0)}), _sous(115, "fixtures")))
    d115 = _sans_zero({"entry_count": n, "fixtures": e115,
                       "display_order": bytes(ordre).hex() if n else ""})
    # 120 in DMX order, the pairing from 110.f5, the map from the addresses
    e120, occupe = [], set()
    for i in sorted(range(n), key=lambda i: (fixtures[i]["address"], i)):
        fx = fixtures[i]
        pk = profils[fx["profile"]]
        base = fx["address"]
        princ = [c["champs"].get("principal_channel", 0) for c in pk["canaux"]]
        paire = [bool(c["champs"].get("pair_member")) for c in pk["canaux"]]
        fines = {p: j for j, p in enumerate(princ) if p != j and paire[j]}
        for j, gab in enumerate(pk["gabarit_120"]):
            e = dict(gab)
            if princ[j] != j and paire[j]:
                e.update(pair_half=2, partner_channel=base + princ[j])
            elif j in fines:
                e.update(pair_half=1, partner_channel=base + fines[j])
            e120.append(_ordonne(_sans_zero(e), _sous(120, "channels")))
            occupe.add(base + j)
    d120 = _sans_zero({"entry_count": len(e120), "occupancy": _occupation(occupe),
                       "channels": e120})
    # 125
    e125 = []
    for gi in range(9):
        g = dict(rig["groups"][gi]) if gi < len(rig["groups"]) else {}
        masque = 0
        for fx in fixtures:
            if fx["group"] == gi:
                masque |= 1 << fx["profile"]
        g["mask"] = {"profile_mask": masque, "f4_tail": g.pop("f4_tail", 0)}
        e125.append(_ordonne(_sans_zero(g), _sous(125, "groups")))
    # 145 ×8
    e145 = []
    for gi in range(8):
        pks = [profils[p] for p in sorted({fx["profile"] for fx in fixtures
                                           if fx["group"] == gi})]
        noms = rig.get("gobo_names") or [[]] * 8
        pads = _palette_145(pks, noms[gi])
        e145.append({"group": gi, "gobos": pads} if gi else {"gobos": pads})
    out = {
        105: [(0, wpj_codec.encode(105, _sans_zero({"entry_count": len(e105), "patch": e105})))],
        106: [(0, wpj_codec.encode(106, _sans_zero({"entry_count": len(e106), "channel_roles": e106})))],
        110: [(0, wpj_codec.encode(110, _sans_zero({"entry_count": len(e110), "channels": e110})))],
        111: [(0, wpj_codec.encode(111, _sans_zero({"entry_count": len(e111), "ranges": e111})))],
        115: [(0, wpj_codec.encode(115, d115))],
        116: [(0, wpj_codec.encode(116, _sans_zero({"entry_count": len(e116), "profiles": e116})))],
        120: [(0, wpj_codec.encode(120, d120))],
        125: [(0, wpj_codec.encode(125, {"entry_count": 9, "groups": e125}))],
        145: [(gi, wpj_codec.encode(145, e145[gi])) for gi in range(8)],
    }
    return out


# --- the oracle ------------------------------------------------------------------

TYPES = (105, 106, 110, 111, 115, 116, 120, 125, 145)


def _canonique_115(w):
    """The file's 115 with `f6`/`f7` dropped — a field a no-op save deletes is
    not one this compiler reproduces (COV-63)."""
    d = _dec(w, 115)
    d["fixtures"] = [{a: b for a, b in f.items() if a not in ("f6", "f7")}
                     for f in d["fixtures"]]
    return wpj_codec.encode(115, d)


def compare(w):
    """{typ: True/False/None} — identical, different, or not attempted."""
    res = {t: None for t in TYPES}
    try:
        cible = compiler(paquets(w), rig_du_fichier(w))
    except ValueError:
        return res
    for t in TYPES:
        for occ, payload in cible[t]:
            attendu = _canonique_115(w) if t == 115 else w.get(t, occ)
            ok = payload == attendu
            res[t] = ok if res[t] in (None, True) else False
    return res


def demo():
    """Every corpus file with no anomaly must rebuild byte-identical.

    Files a defect marks — the COV-53 drop, the WTOOLS split, an erased 120,
    a stale group mask — are counted and named, not skipped in silence."""
    fichiers = wpjlib.corpus_files()
    if not fichiers:
        wpjlib.pas_de_corpus("wpj_patch")
        return
    total, complets, marques, par_type = 0, 0, [], {t: [0, 0] for t in TYPES}
    for f in fichiers:
        try:
            w = wpjlib.Wpj.load(f)
        except ValueError:
            continue
        total += 1
        r = compare(w)
        anos = [a.__name__ for a in wpj_identities.ANOMALIES if a(w)]
        for t, v in r.items():
            if v is not None:
                par_type[t][v] += 1
        if all(r.values()):
            complets += 1
        elif anos:
            marques.append((os.path.basename(f), anos[0]))
        else:
            faux = [t for t, v in r.items() if not v]
            raise AssertionError(f"{f}: no anomaly, and records {faux} do not "
                                 f"rebuild — a rule this compiler lacks")
    assert total, "no variant-A file"
    for t, (ko, ok) in par_type.items():
        assert ok, f"record {t} never reproduced"
    print(f"self-check ok: the patch rebuilt byte-identical on {complets}/{total} "
          f"variant-A files; the {len(marques)} others each carry an anomaly "
          f"({', '.join(sorted({a for _, a in marques}))}); per record "
          + ", ".join(f"{t} {ok}/{ok + ko}" for t, (ko, ok) in par_type.items()))


# --- build -----------------------------------------------------------------------

def _resout(paquets_dispo, ref):
    if ref in paquets_dispo:
        return ref
    noms = [u for u, pk in paquets_dispo.items() if pk["name"] == ref]
    if len(noms) == 1:
        return noms[0]
    raise ValueError(f"profile {ref!r}: {'ambiguous' if noms else 'unknown'} — "
                     f"known: {sorted(pk['name'] for pk in paquets_dispo.values())}")


def construire(rig, sortie):
    """rig.json -> a project. Returns the sha256 of what was written."""
    for cle in rig:
        if cle not in ("skeleton", "profiles_from", "fixtures", "groups", "name",
                       "gobo_names"):
            raise ValueError(f"rig: unknown key {cle!r}")
    w = wpjlib.Wpj.load(rig["skeleton"])
    if any(t == 160 for t, _ in w.records):
        raise ValueError("skeleton carries record 160 (LIVE EDIT macros aimed "
                         "at its own fixtures): use a project without them")
    dispo = {}
    for f in rig.get("profiles_from", [rig["skeleton"]]):
        for pk in paquets(wpjlib.Wpj.load(f)):
            if pk["blocs"] is not None and pk["gabarit_120"] is not None:
                dispo.setdefault(pk["uuid"], pk)
    profils, fixtures, occupe = [], [], set()
    for i, fx in enumerate(rig["fixtures"]):
        for cle in fx:
            if cle not in ("profile", "dmx", "group"):
                raise ValueError(f"fixture {i}: unknown key {cle!r}")
        u = _resout(dispo, fx["profile"])
        if u not in profils:
            profils.append(u)
        g = fx.get("group", "A")
        g = GROUPES.index(g) if isinstance(g, str) else int(g)
        if not 0 <= g < 8:
            raise ValueError(f"fixture {i}: group {fx.get('group')!r}")
        adr = int(fx["dmx"]) - 1
        n = len(dispo[u]["canaux"])
        if adr < 0 or adr + n > UNIVERS:
            raise ValueError(f"fixture {i}: DMX {fx['dmx']} + {n} channels leaves the universe")
        fen = set(range(adr, adr + n))
        if fen & occupe:
            raise ValueError(f"fixture {i}: DMX {fx['dmx']} overlaps another fixture")
        occupe |= fen
        fixtures.append({"profile": profils.index(u), "address": adr, "group": g})
    if not fixtures:
        raise ValueError("rig: no fixture")
    skel125 = _dec(w, 125).get("groups", [])
    groupes = []
    noms = rig.get("groups", {})
    for gi in range(9):
        g = {}
        if any(fx["group"] == gi for fx in fixtures):
            g.update(f1=1, f2=1, f5=1, f7=1)     # the fresh project's pattern
        if gi < 8 and GROUPES[gi] in noms:
            g["name"] = noms[GROUPES[gi]]
        g["f4_tail"] = skel125[gi]["mask"]["f4_tail"] if gi < len(skel125) else 56
        groupes.append(g)
    liste = [dispo[u] for u in profils]
    noms_gobos = []
    for gi in range(8):
        voulus = rig.get("gobo_names", {}).get(GROUPES[gi], {})
        pads = _palette_145([liste[p] for p in sorted({fx["profile"] for fx in fixtures
                                                       if fx["group"] == gi})])
        noms_gobos.append([voulus.get(str(p.get("gobo_id", ""))) for p in pads])
        inconnus = set(voulus) - {str(p.get("gobo_id")) for p in pads}
        if inconnus:
            raise ValueError(f"gobo_names {GROUPES[gi]}: no pad carries id {sorted(inconnus)}")
    cible = compiler(liste, {"profiles": list(range(len(liste))), "fixtures": fixtures,
                             "display_order": None, "groups": groupes,
                             "gobo_names": noms_gobos})
    for t, occs in cible.items():
        for occ, payload in occs:
            w.replace(t, payload, occ)
    # the detached positions named the old fixtures
    w.replace(151, b"")
    for occ in range(8):
        d = _dec(w, 150, occ)
        for p in d.get("positions", []):
            p.pop("entry_count_151", None)
            p.pop("offset_151", None)
        w.replace(150, wpj_codec.encode(150, d), occ)
    # record 161's head is the mask over the fixtures (COV-45)
    d161 = _dec(w, 161)
    d161["items"][0]["f3"][0] = (1 << len(fixtures)) - 1
    w.replace(161, wpj_codec.encode(161, d161))
    if "name" in rig:
        d = _dec(w, 101)
        d["name"] = rig["name"]
        w.replace(101, wpj_codec.encode(101, d))
    empreinte = w.save(sortie)
    # verify: reload, every identity, and the patch reads back as compiled
    try:
        w2 = wpjlib.Wpj.load(sortie)
        for verif in wpj_identities.IDENTITES:
            verif(w2)
        for t, occs in cible.items():
            for occ, payload in occs:
                assert w2.get(t, occ) == payload, f"record {t} occ {occ} read back differently"
        for nom, msg in wpj_identities.anomalies(sortie):
            raise AssertionError(f"{nom}: {msg}")
    except Exception:
        os.unlink(sortie)
        raise
    return empreinte, profils, fixtures


def _imprime_paquets(fichiers):
    for f in fichiers:
        for pk in paquets(wpjlib.Wpj.load(f)):
            u = pk["uuid"]
            etat = ("ok" if pk["blocs"] is not None and pk["gabarit_120"] is not None
                    else "unusable: no clean fixture in this file")
            blocs = len(pk["blocs"]) if pk["blocs"] else 0
            print(f"{pk['name']:<20} {u}  {len(pk['canaux']):>3} ch  "
                  f"{blocs} block(s)  library_id {pk['library_id']}  {etat}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("profiles", help="the packages some projects carry")
    p.add_argument("projects", nargs="+")
    b = sub.add_parser("build", help="compile rig.json into a project")
    b.add_argument("rig")
    b.add_argument("out")
    args = ap.parse_args(argv)
    if args.cmd == "profiles":
        _imprime_paquets(args.projects)
        return 0
    if args.cmd == "build":
        with open(args.rig, encoding="utf-8") as f:
            rig = json.load(f)
        try:
            empreinte, profils, fixtures = construire(rig, args.out)
        except (ValueError, AssertionError, KeyError, FileExistsError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"{args.out}: {len(fixtures)} fixtures, {len(profils)} profiles, "
              f"identities verified, sha256 {empreinte}")
        print("next: open it once on the W1 — Main Menu > Projects — and check "
              "the FIXTURES screen before trusting it with a show (PATCH-02 is unrun)")
        return 0
    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
