#!/usr/bin/env python3
"""A minimal, template-based show compiler (on wpjlib + wpj_codec).

Module group: Composition. Reference: docs/show-format.md.

The principle: we ALWAYS start from an existing variant-A donor project and
apply a JSON edit spec. Everything the spec does not name is preserved byte for
byte by wpjlib. An edited position or palette entry must already exist in the
donor; a preset may additionally be **created at the tail** by cloning a donor
preset (the `template` key) — appending a `165.f5` entry with the next id is
device-confirmed, and `165.f1` is left verbatim (registry, PRESET-01).

Scope = fields at status >= correlated (records 101, 111, 130, 135, 145, 150,
165). Phase, Size and Fade are measured (FX6-02/03) but stay outside the keys
that get written: read, not written — the key list is `_FX_CLES`.

Usage:
  wpj_show.py compile show.json out.wpj   compile + self-verify
  wpj_show.py verify base.wpj out.wpj     list the records that differ
  wpj_show.py                             self-check (corpus, leaves no trace)
"""

from __future__ import annotations
from os import PathLike
from collections.abc import Iterable, Mapping
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpjlib
import wpj_codec

_FX_NOMS = ("beam_fx1", "beam_fx2", "color_fx1", "color_fx2",
            "move_fx1", "move_fx2")
# FX key → bounds (correlated statuses, SPEC.md §5, FX submessage).
# `speed` was bounded to 200 while it pointed at f2; f2 is the fade, and the
# speed is a percentage — never above 100 across 352 presets (FX6-02).
# phase/size/fade are named but stay off this list: read, not written.
_FX_CLES = {"effect": (0, 8), "speed": (0, 100), "link_order": (10, 13),
            "speed_source": (0, 2), "bpm_division": (0, 1 << 31)}
_SHOW_CLES = ("base", "name", "presets", "positions", "palette",
              "gobo_names", "gobo_order", "mappings")
_PRESET_CLES = ("id", "template", "name", "positions", "dimmers",
                "content_mask", "color_pattern",
                "static_color") + _FX_NOMS
NOM_MAX_OCTETS = 19          # past this, the whole project refuses to open
NB_GROUPES = 8               # A–H
PADS_PAR_GROUPE = 20         # one 20-bit mask per group in f31
# Device-confirmed attribution (registry, type 150): f6 = PAN, f7 = TILT,
# f3 = FAN, f4 = FOCUS OFFSET. An earlier reading put pan/tilt on f3/f4; the
# W1's own edit screen refuted it.
_POS_CLES = ("page", "index", "name", "pan", "tilt", "fan")
_POS_CHAMPS = ("pan", "tilt", "fan")   # codec keys since 2026-09-01
_PAL_CLES = ("index", "red", "green", "blue")
# Record 130 = the DMX IN mapping table (SPEC §7.3, MAP-01..09). `f4` is the
# FUNCTION targeted, not the screen's category: the seven `Flash` functions
# carry seven different ones. The fifteen below are the complete inventory of
# the five categories, each measured through the entry the device created when
# the operator selected it on screen (MAP-09, ten at once, each channel
# labelling its own entry).
#
# Value = (f4, fixed instance); `None` = the instance comes from the spec.
# The instance is **255** as soon as the function is not bound to a numbered
# instance — including `select_preset` and `jump_preset`, where the incoming
# VALUE picks. Two functions share an `f4` with `preset` (70) and three with
# `jump_preset` (78): the pair (f4, instance) is what identifies an entry.
_MAP_FONCTIONS = {
    "group_dimmer":    (20, None),   # instance = the group A–H
    "main":            (27, 0),      # the factory entry carries no f7
    "preset":          (70, None),   # instance = the preset index
    "select_preset":   (70, 255),    # same f4: the incoming value picks
    "preset_page":     (82, None),   # instance = the page, zero-based
    "bpm_tap":         (17, 255),
    "wolf":            (10, 255),
    "strobe":          (11, 255),
    "blinder":         (12, 255),
    "speed":           (13, 255),
    "blackout":        (14, 255),
    "smoke":           (15, 255),
    "jump_preset":     (78, 255),    # the incoming value picks
    "previous_preset": (78, 1),
    "next_preset":     (78, 2),
}
_MAP_CLES = ("target", "group", "index", "page", "channel")
PAGES_PRESET = 7             # Page 1 to 7, the screen offers no others
PRESETS_MAX = 200            # 0–199, the panel's own bound
# The device writes its fields in numeric order and OMITS any zero field —
# `28 00` never appears in its output. An edited entry must be put back into
# that shape, or the file diverges from the device's bytes even though its
# semantics are right: invisible to a decoded comparison, and it would break
# every later diff against a file the device rewrote.
_MAP_ORDRE = (("instance", 2), ("function", 4), ("channel_high_byte", 5),
              ("channel_low_byte", 6), ("f7", 7), ("f8", 8))


def _normalise_mapping(entree):
    """Returns the entry in the device's field order, with no zero field."""
    connus = {nom for nom, _ in _MAP_ORDRE}
    propre = {nom: entree[nom] for nom, _ in _MAP_ORDRE
              if entree.get(nom)}
    propre.update({k: v for k, v in entree.items() if k not in connus})
    entree.clear()
    entree.update(propre)
    return entree
CANAL_MAX = 512              # the panel encoder's bound, measured


def cles(d: Mapping[str, object], permises: Iterable[str], contexte: str) -> None:
    """Public: `wpj_generate` validates its intentions with the same rules."""
    inconnues = [k for k in d if k not in permises]
    retirees = {k: wpj_codec.remplacante(k) for k in inconnues
                if wpj_codec.remplacante(k)}
    if retirees:
        detail = ", ".join(f"{v!r} → {n!r}" for v, n in sorted(retirees.items()))
        raise ValueError(f"{contexte}: keys retired on 2026-08-31, write "
                         f"their replacement: {detail}")
    if inconnues:
        raise ValueError(f"{contexte}: keys out of scope {inconnues}; "
                         f"allowed: {list(permises)}")


def borne(contexte: str, nom: str, v: int, lo: int, hi: int) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise ValueError(f"{contexte} : {nom}={v!r} hors bornes [{lo}, {hi}]")
    return v


def liste8(contexte: str, nom: str, v: list[int], lo: int, hi: int) -> list[int]:
    if not isinstance(v, list) or len(v) != 8:
        raise ValueError(f"{contexte}: {nom} must be a list of 8 integers")
    return [borne(contexte, f"{nom}[{i}]", x, lo, hi) for i, x in enumerate(v)]


def _pads_vers_masques(contexte, pads8):
    """8 lists of pad numbers (1–20) → the 20 packed bytes of `f31`.

    `f31` = 20 varints = 160 little-endian bits, cut into eight 20-bit masks
    (one per group A–H); bit n of group g lights pad n+1 of that group's
    palette 140 — device-confirmed.
    """
    if not isinstance(pads8, list) or len(pads8) != NB_GROUPES:
        raise ValueError(f"{contexte}: static_color must be {NB_GROUPES} "
                         f"lists of pad numbers (1–{PADS_PAR_GROUPE}), one "
                         "per group A–H")
    bits = 0
    for g, pads in enumerate(pads8):
        if not isinstance(pads, list):
            raise ValueError(f"{contexte}: static_color[{g}] must be a list "
                             "of pad numbers")
        for pad in pads:
            borne(contexte, f"static_color[{g}]", pad, 1, PADS_PAR_GROUPE)
            bits |= 1 << (g * PADS_PAR_GROUPE + pad - 1)
    return list(bits.to_bytes(NB_GROUPES * PADS_PAR_GROUPE // 8, "little"))


def masques_vers_pads(v20: list[int]) -> list[list[int]] | None:
    """The inverse of _pads_vers_masques: the 20 bytes → 8 pad lists."""
    if not isinstance(v20, list) or any(not isinstance(x, int) or not 0 <= x < 256
                                        for x in v20):
        return None                      # unreadable f31: no interpretation
    bits = int.from_bytes(bytes(v20), "little")
    return [[p + 1 for p in range(PADS_PAR_GROUPE)
             if bits >> (g * PADS_PAR_GROUPE + p) & 1]
            for g in range(NB_GROUPES)]


def compiler(
    spec: dict[str, object],
    sortie: str | PathLike[str],
) -> list[tuple[int, int, int, int]]:
    """Applies the spec to the donor, writes the output, self-verifies.
    Returns the diff list [(type, occ, size_before, size_after)]."""
    cles(spec, _SHOW_CLES, "show")
    if "base" not in spec:
        raise ValueError("show: the 'base' key (donor .wpj) is required")
    w = wpjlib.Wpj.load(spec["base"])
    cache = {}      # (type, occ) -> decoded dict, re-encoded at the end
    verifs = []     # (type, occ, description, fn(decoded dict) -> bool)

    def rec(typ, occ=0):
        if (typ, occ) not in cache:
            d = wpj_codec.decode(typ, w.get(typ, occ))
            if set(d) == {"raw"}:
                raise ValueError(f"record {typ} occ {occ}: not decodable")
            cache[(typ, occ)] = d
        return cache[(typ, occ)]

    # --- record 101: the project name (device-confirmed, ACC-01) ---
    if "name" in spec:
        nom = spec["name"]
        if not isinstance(nom, str) or not nom:
            raise ValueError("show: 'name' must be a non-empty string")
        rec(101)["name"] = nom
        verifs.append((101, 0, "nom projet", lambda d, v=nom: d.get("name") == v))

    # --- record 165: presets, addressed by id ---
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
            raise ValueError(f"{ctx}: already in the donor, 'template' only "
                             "applies to a creation")
        if "name" in pe:
            if not isinstance(pe["name"], str):
                raise ValueError(f"{ctx}: the name must be a string")
            octets = len(pe["name"].encode("utf-8"))
            if octets > NOM_MAX_OCTETS:
                raise ValueError(f"{ctx} : nom de {octets} octets UTF-8 > "
                                 f"{NOM_MAX_OCTETS} — the WHOLE project "
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
                raise ValueError(f"{ctx}: {fx} is absent from the donor — "
                                 "creating an FX sub-message is not validated, "
                                 "use a donor where this FX exists")
            cible[fx][0].update(pe[fx])
        attendu = {k: (_pads_vers_masques(ctx, v)
                       if k == "static_color" else v)
                   for k, v in pe.items() if k not in ("id", "template")}
        verifs.append((165, 0, ctx, lambda d, pid=pid, att=attendu:
                       _verif_preset(d, pid, att)))

    # --- record 150 ×8: named pan/tilt positions ---
    for pos in spec.get("positions", []):
        cles(pos, _POS_CLES, "position")
        page = borne("position", "page", pos.get("page", 0), 1, 8)
        idx = borne("position", "index", pos.get("index", -1), 0, 1 << 31)
        d150 = rec(150, page - 1)
        entrees = d150.get("positions", [])
        if idx >= len(entrees) or not isinstance(entrees[idx], dict) or \
                set(entrees[idx]) == {"hex"}:
            raise ValueError(f"position page {page} index {idx}: the entry "
                             "must exist in the donor")
        e = entrees[idx]
        ctx = f"position page {page} index {idx}"
        if "name" in pos:
            if not isinstance(pos["name"], str):
                raise ValueError(f"{ctx}: the name must be a string")
            e["name"] = pos["name"]
        for cle in _POS_CHAMPS:
            if cle in pos:
                e[cle] = borne(ctx, cle, pos[cle], 0, 65535)
        attendu = {k: v for k, v in pos.items()
                   if k in ("name",) + _POS_CHAMPS}
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
            raise ValueError(f"palette index {idx}: the entry must exist in "
                             "the donor")
        ctx = f"palette index {idx}"
        for k in ("red", "green", "blue"):
            if k in pal:
                pads[idx][k] = borne(ctx, k, pal[k], 0, 255)
        attendu = {k: pal[k] for k in ("red", "green", "blue") if k in pal}
        verifs.append((135, 0, ctx, lambda d, i=idx, att=attendu:
                       all(d["pads"][i].get(k, 0) == v
                           for k, v in att.items())))

    # --- records 145 + 111: group A's gobo page ---
    # Device-confirmed (RENAME-01, SORT-01): a pad's name is `145.f3`, and the
    # pad order is the wire order of the wheel ranges (function 14) of record
    # 111 — non-monotonic ranges accepted, DMX bounds travelling with them.
    if "gobo_names" in spec:
        d145 = rec(145)
        att_noms = {}
        for cle, nom in spec["gobo_names"].items():
            gid = int(cle)
            ctx = f"gobo_names id {gid}"
            if not isinstance(nom, str) or not nom:
                raise ValueError(f"{ctx}: the name must be a non-empty string")
            if len(nom.encode("utf-8")) > NOM_MAX_OCTETS:
                raise ValueError(f"{ctx} : nom > {NOM_MAX_OCTETS} octets "
                                 "UTF-8 — a limit measured on presets "
                                 "(PRESET-05), not measured here, so refused")
            slot = next((s for s in d145.get("gobos", [])
                         if isinstance(s, dict) and s.get("gobo_id") == gid),
                        None)
            if slot is None:
                raise ValueError(f"{ctx}: absent from the donor's palette")
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
            raise ValueError("gobo_order: the list must carry exactly the "
                             "ids of the donor's palette")
        # a wheel shared with another group = not measured: refused.
        for occ in range(1, sum(1 for t, _ in w.records if t == 145)):
            autres = wpj_codec.decode(145, w.get(145, occ)).get("gobos", [])
            ids = sorted(s["gobo_id"] for s in autres
                         if isinstance(s, dict) and "gobo_id" in s)
            if ids == sorted(ordre):
                raise ValueError(f"gobo_order: group {occ} carries the same "
                                 "wheel — an unmeasured case, refused")
        par_id = {s["gobo_id"]: s for s in pleins}
        nouveaux = [par_id[g] for g in ordre]
        for k, s in enumerate(nouveaux):
            s["glyph"] = chr(0x21 + k)      # a sequence, the device's own shape
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
            raise ValueError("gobo_order: no wheel of the donor carries these "
                             "ids in a decodable record 111")

    # --- record 130: the DMX IN mapping table (device-confirmed, MAP-01..07) ---
    # An entry is identified by (function, instance), NEVER by its rank: the
    # wire order moves without the content changing, seen twice across eleven
    # saves, with no read in between. `channel: null` removes the entry —
    # "unmapped" is absence, there is no sentinel.
    if "mappings" in spec:
        d130 = rec(130)
        entrees = d130.setdefault("mappings", [])
        attendu = {}
        for me in spec["mappings"]:
            cles(me, _MAP_CLES, "mapping")
            cible = me.get("target")
            if cible not in _MAP_FONCTIONS:
                raise ValueError(
                    f"mapping: target {cible!r} out of scope; measured: "
                    f"{sorted(_MAP_FONCTIONS)}")
            ctx = f"mapping {cible}"
            fonction, instance = _MAP_FONCTIONS[cible]
            if cible == "group_dimmer":
                g = me.get("group")
                if g not in list("ABCDEFGH"):
                    raise ValueError(f"{ctx}: 'group' must be A–H")
                instance = ord(g) - ord("A")
            elif cible == "preset":
                instance = borne(ctx, "index", me.get("index", -1),
                                  0, PRESETS_MAX - 1)
            elif cible == "preset_page":
                # the page is written as displayed, 1–7; stored zero-based
                instance = borne(ctx, "page", me.get("page", -1),
                                  1, PAGES_PRESET) - 1
            if any(k in me for k in ("group", "index", "page")
                   if k != {"group_dimmer": "group", "preset": "index",
                            "preset_page": "page"}.get(cible)):
                raise ValueError(f"{ctx}: an instance key that does not apply "
                                 "to this function")
            canal = me.get("channel", "absent")
            if canal == "absent":
                raise ValueError(f"{ctx}: the 'channel' key is required "
                                 "(an integer 1–512, or null to remove)")
            trouve = next((e for e in entrees
                           if e.get("function") == fonction
                           and e.get("instance", 0) == instance), None)
            if canal is None:
                if trouve is None:
                    raise ValueError(f"{ctx}: no entry to remove")
                entrees.remove(trouve)
                attendu[(fonction, instance)] = None
                continue
            canal = borne(ctx, "channel", canal, 1, CANAL_MAX)
            haut, bas = divmod(canal - 1, 256)
            if trouve is None:
                # the shape of an entry the device creates: f7 = 1, f8 = 1,
                # seen on the thirteen it created (MAP-02, MAP-09).
                trouve = {"instance": instance, "function": fonction,
                          "f7": 1, "f8": 1}
                entrees.append(trouve)
            trouve["channel_high_byte"], trouve["channel_low_byte"] = haut, bas
            _normalise_mapping(trouve)
            attendu[(fonction, instance)] = canal
        d130["entry_count"] = len(entrees)    # device-confirmed: f1 = the count

        def _verif_130(d, att=attendu):
            if d.get("entry_count") != len(d.get("mappings", [])):
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

    # --- re-encode + write (a new file, never an overwrite) ---
    for (typ, occ), d in cache.items():
        w.replace(typ, wpj_codec.encode(typ, d), occ)
    try:
        w.save(sortie)
    except FileExistsError:
        raise ValueError(f"{sortie} already exists — overwrite refused")

    # --- self-verify: reload (SHA-1 revalidated), re-decode, compare ---
    try:
        w2 = wpjlib.Wpj.load(sortie)                 # SHA-1 checked by load
        for typ, occ, desc, ok in verifs:
            d = wpj_codec.decode(typ, w2.get(typ, occ))
            if not ok(d):
                raise ValueError(f"self-verify: {desc} does not read back the "
                                 "value asked for")
        diffs = verifier(spec["base"], sortie)
        en_trop = [d for d in diffs if (d[0], d[1]) not in cache]
        if en_trop:
            raise ValueError(f"self-verify: records changed outside the edit: "
                             f"{en_trop}")
    except Exception:
        os.unlink(sortie)
        raise
    return diffs


def _cree_preset(ctx, d165, pid, pe):
    """Creates a preset at the tail of `165.f5` by cloning `template`.

    Device-confirmed (registry, PRESET-01/06/07): appending a well-formed entry
    with a free id is enough — the device stores it, displays it, recalls it and
    keeps it across store, RESTART and a cold reopen. `165.f1` tracks nothing
    (81 with 85 entries): left verbatim. Gaps in the ids get filled; the id must
    stay increasing, so creation happens at the tail, like the two measured
    additions.
    """
    if "template" not in pe:
        raise ValueError(f"{ctx}: absent from the donor — give 'template' "
                         "(the id of the preset to clone) to create it at the "
                         "tail")
    mid = borne(ctx, "template", pe["template"], 0, 1 << 31)
    modele = next((p for p in d165["presets"]
                   if isinstance(p, dict) and p.get("id", 0) == mid), None)
    if modele is None:
        raise ValueError(f"{ctx}: template {mid} is absent from the donor")
    maxi = max(p.get("id", 0) for p in d165["presets"] if isinstance(p, dict))
    if pid <= maxi:
        raise ValueError(f"{ctx}: tail creation only, the id must exceed "
                         f"{maxi} (the donor's largest)")
    if pid > 127:
        # `SET_PRESET` carries the id in a single byte (RECALL-03) and the
        # second is not read (RAW-02); every published shot fits in 0–127.
        # Above that, an exact recall, a 7-bit truncation and a no-op all stay
        # possible. The panel itself goes to 199: the cue is recallable by
        # hand, not necessarily from a distance.
        print(f"warning: {ctx} — USB recall has never been measured above "
              "id 127 (RECALL-06); at the panel, it has",
              file=sys.stderr)
    cible = copy.deepcopy(modele)
    cible["id"] = pid
    # preset 0 omits its id field, so a clone of it gains one: keep the wire
    # order by field number, which is how the device writes every entry
    schema = wpj_codec.SCHEMAS[165][5][1]

    def numero(cle):
        try:
            return wpj_codec.field_number(schema, cle)
        except KeyError:
            return int(cle[1:])  # Preserve this caller's legacy fallback.
    cible = {k: cible[k] for k in sorted(cible, key=numero)}
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


def verifier(
    base: str | PathLike[str],
    sortie: str | PathLike[str],
) -> list[tuple[int, int, int, int]]:
    """Returns the records that differ: [(type, occ, size_before, size_after)]."""
    a, b = wpjlib.Wpj.load(base), wpjlib.Wpj.load(sortie)
    if [t for t, _ in a.records] != [t for t, _ in b.records]:
        raise ValueError("different type sequences: a record-by-record "
                         "comparison is impossible")
    diffs, occs = [], {}
    for (t, pa), (_, pb) in zip(a.records, b.records):
        occ = occs.get(t, 0)
        occs[t] = occ + 1
        if pa != pb:
            diffs.append((t, occ, len(pa), len(pb)))
    return diffs


def _imprime(diffs):
    if not diffs:
        print("no record changed")
    for t, occ, la, lb in diffs:
        print(f"type {t} occ {occ}: {la} -> {lb} bytes")


def demo() -> None:
    """Looks for a usable donor in the local corpus; abstains otherwise.

    No .wpj ships with this repository (docs/corpus.md): the self-check takes
    the first variant-A file of the corpus that carries the edited slots
    (preset 80, position page 1 index 1, pad 0).
    """
    for base in wpjlib.corpus_files():
        try:
            return _demo_sur(base)
        except (ValueError, KeyError, StopIteration, OSError):
            continue                      # a donor without the wanted slots
    return wpjlib.pas_de_corpus("wpj_show")


def _demo_sur(base):
    import tempfile
    ids = [p.get("id", 0) for p in
           wpj_codec.decode(165, wpjlib.Wpj.load(base).get(165))["presets"]]
    neuf = max(ids) + 3                       # tail creation, leaving a gap
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
                          "channel": 1},          # zero high byte: must be omitted
                         {"target": "group_dimmer", "group": "C",
                          "channel": None}]}        # retrait
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "demo.wpj")
        diffs = compiler(spec, out)
        assert {(t, o) for t, o, *_ in diffs} == {(101, 0), (165, 0),
                                                 (150, 0), (135, 0),
                                                 (130, 0)}, diffs
        # an independent read-back of the values asked for
        w = wpjlib.Wpj.load(out)
        assert wpj_codec.decode(101, w.get(101))["name"] == "WMX SHOW DEMO"
        p = next(p for p in wpj_codec.decode(165, w.get(165))["presets"]
                 if p.get("id", 0) == 80)
        assert p["name"] == "demo" and p["dimmers"] == [200] * 8
        assert p["beam_fx1"][0]["effect"] == 1 and p["beam_fx1"][0]["speed"] == 80
        e = wpj_codec.decode(150, w.get(150, 0))["positions"][1]
        assert e["name"] == "DemoPos" and e["pan"] == 12345 and e["tilt"] == 54321
        assert e["fan"] == 32768
        assert wpj_codec.decode(135, w.get(135))["pads"][0] == \
            {"red": 10, "green": 20, "blue": 30}
        # the created preset: cloned, at the tail, read back field by field
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
                 "static_color")}, "the clone must be the template verbatim"
        # an empty spec = a byte-identical round trip of the donor
        out2 = os.path.join(tmp, "ident.wpj")
        assert compiler({"base": base}, out2) == []
        assert open(out2, "rb").read() == open(base, "rb").read()
        # page gobos : nom + rotation, valeurs relues
        pal = wpj_codec.decode(145, wpjlib.Wpj.load(base).get(145))["gobos"]
        gids = [s["gobo_id"] for s in pal
                if isinstance(s, dict) and "gobo_id" in s]
        if len(gids) < 2:
            raise ValueError("donor with no gobo palette")
        rot = gids[1:] + gids[:1]
        out3 = os.path.join(tmp, "gobo.wpj")
        compiler({"base": base, "gobo_names": {str(gids[0]): "DemoGobo"},
                  "gobo_order": rot}, out3)
        d = wpj_codec.decode(145, wpjlib.Wpj.load(out3).get(145))["gobos"]
        assert [s["gobo_id"] for s in d if "gobo_id" in s] == rot
        assert next(s["name"] for s in d
                    if s.get("gobo_id") == gids[0]) == "DemoGobo"
        # a rotation then its inverse, with no rename: the donor comes back
        # byte-identical (sequential glyphs = the shape the device writes)
        if [s.get("glyph") for s in pal if "gobo_id" in s] == \
                [chr(0x21 + k) for k in range(len(gids))]:
            ga, gb = os.path.join(tmp, "ga.wpj"), os.path.join(tmp, "gb.wpj")
            compiler({"base": base, "gobo_order": rot}, ga)
            compiler({"base": ga, "gobo_order": gids}, gb)
            assert open(gb, "rb").read() == open(base, "rb").read()
        # expected errors: unknown key, absent entry
        # --- the table, read back independently ---
        d130 = wpj_codec.decode(130, w.get(130))
        carte = {(e.get("function"), e.get("instance", 0)):
                 e.get("channel_high_byte", 0) * 256
                 + e.get("channel_low_byte", 0) + 1
                 for e in d130["mappings"]}
        assert carte[(20, 1)] == 300, carte          # changed, across two bytes
        assert carte[(70, 4)] == 40, carte           # created
        assert carte[(10, 255)] == 45, carte         # created, instance 255
        assert (20, 2) not in carte, carte           # removed
        assert carte[(20, 0)] == 1 and carte[(27, 0)] == 9, carte  # intactes
        assert carte[(82, 2)] == 101, carte      # page 3 -> instance 2
        assert carte[(15, 255)] == 106, carte
        assert carte[(70, 255)] == 107, carte    # same f4 as preset, inst. 255
        assert carte[(78, 2)] == 110, carte      # shared f4, fixed instance 2
        assert carte[(70, 4)] != carte[(70, 255)], "the two f4=70 were merged"
        assert d130["entry_count"] == len(d130["mappings"]) == 9 - 1 + 6

        # --- the shape of the bytes, not only the semantics ---
        # The device writes its fields in numeric order and never emits a zero
        # field. A divergence here is invisible to a decode and would make every
        # later diff unreadable against a file the device rewrote.
        import wpj_wire
        brut = [x for x in wpj_wire.load(out)[1] if x[1] == 130][0][3]
        for e in wpj_wire.walk(brut):
            if e[0] != 5:
                continue
            octets = e[2]
            assert b"\x28\x00" not in octets, \
                f"a zero field 5 was emitted: {octets.hex()}"
            numeros = [c[0] for c in e[3]]
            assert numeros == sorted(numeros), \
                f"fields out of numeric order: {octets.hex()}"

        for mauvais in [{"base": base, "fondu": 1},
                        {"base": base, "presets": [{"id": 9999, "name": "x"}]},
                        {"base": base, "presets": [{"id": 80, "size": 5}]},
                        {"base": base, "palette": [{"index": 999, "red": 1}]},
                        # nom de 20 octets : tueur device-confirmed
                        {"base": base, "presets": [{"id": 80,
                                                    "name": "a" * 20}]},
                        # creating below the donor's largest id
                        {"base": base, "presets": [{"id": 1, "template": 23}]},
                        # 'template' on a preset that already exists
                        {"base": base, "presets": [{"id": 80, "template": 23}]},
                        # a pad outside the grid of 20
                        {"base": base, "presets": [
                            {"id": neuf, "template": 23,
                             "static_color": [[21]] + [[]] * 7}]},
                        # gobo inconnu, ordre incomplet, nom trop long
                        {"base": base, "gobo_names": {"999999": "x"}},
                        {"base": base, "gobo_order": gids[:-1]},
                        {"base": base, "gobo_names": {str(gids[0]): "a" * 20}},
                        # an unmeasured function: we do not guess an f4
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
                        # a function with no instance does not take one
                        {"base": base, "mappings": [{"target": "wolf",
                                                     "index": 2, "channel": 5}]},
                        # 'channel' is required, even to remove
                        {"base": base, "mappings": [{"target": "wolf"}]},
                        # removing an absent entry
                        {"base": base, "mappings": [{"target": "bpm_tap",
                                                     "channel": None}]},
                        # page hors 1–7
                        {"base": base, "mappings": [{"target": "preset_page",
                                                     "page": 8, "channel": 5}]},
                        # an instance key that does not apply to the function
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
    # No tracked example may still carry a retired key: that is the half of
    # the contract that lives in files rather than in code.
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

    # A retired French key is an error that names its replacement.
    for essai in ({"base": "x", "nom": "y"}, {"base": "x", "gobo_ordre": []}):
        try:
            cles(essai, _SHOW_CLES, "show.json")
            raise AssertionError(f"retired key accepted: {essai}")
        except ValueError as erreur:
            assert "retired" in str(erreur) and "→" in str(erreur), erreur

    print("self-check ok: compile + creation + self-verify + errors on "
          + os.path.basename(base), file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commandes = parseur.add_subparsers(dest="commande")
    compile_cmd = commandes.add_parser(
        "compile", help="applies a JSON spec to a donor project")
    compile_cmd.add_argument("spec", help="the show.json")
    compile_cmd.add_argument("sortie", help="new project; an existing one is refused")
    verify_cmd = commandes.add_parser(
        "verify", help="lists the records that differ between two projects")
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
        print(f"ok: {args.sortie}")
        return 0
    _imprime(verifier(args.base, args.sortie))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError) as e:
        print(f"erreur : {e}", file=sys.stderr)
        sys.exit(1)
