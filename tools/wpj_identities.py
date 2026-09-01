#!/usr/bin/env python3
"""Structural identities of the variant-A .wpj, checked over the whole corpus.

Each identity is an arithmetic constraint between two records. It is either
true everywhere or false — so a reading that breaks one is refuted without
touching hardware. Proof: demo() over the corpus.

Usage: python3 tools/wpj_identities.py   (from the repository root)
"""
import sys

import wpj_codec
import wpjlib

GOBO_FN = 14          # 111.f3 = the "gobo" function (registry, type 145)
_ITEMS = {5: ("items", {})}


def _varints(hexa):
    """The bytes of a packed-varint field: the list of decoded values."""
    out, v, sh = [], 0, 0
    for c in bytes.fromhex(hexa):
        v |= (c & 0x7f) << sh
        if c & 0x80:
            sh += 7
        else:
            out.append(v); v, sh = 0, 0
    return out


def _items(w, typ, occurrence=0):
    # an empty table (0 entries) is legitimate — seen on 130 of an import
    return wpj_codec._decode_msg(w.get(typ, occurrence), _ITEMS).get("items", [])


def ranges_par_canal(w):
    """110[c].f2 == the size of the slice of 111 that belongs to channel c."""
    c110, c111 = _items(w, 110), _items(w, 111)
    debuts = [c.get("f3", 0) for c in c110] + [len(c111)]
    for i, c in enumerate(c110):
        assert c.get("f2", 0) == debuts[i + 1] - debuts[i], \
            f"110[{i}].f2 = {c.get('f2', 0)} but the slice is " \
            f"{debuts[i + 1] - debuts[i]}"


def palette_gobo(w):
    """Every f2 of type 145 is an f4 of the gobo ranges of 111.

    The ordered equality ("the palette is derived from the patch") held on
    every project born on the device — and was REFUTED on 2026-08-31 by a
    project imported from WTOOLS (EXP-06): its palette is the 10-slot selection
    of the B side (f9 + f31), duplicates included. The invariant that survives
    is membership: a palette id that is not on the wheel stays impossible.
    Registry, "EXP-06 — the Rosetta pair, measured"."""
    ids = {e["f4"] for e in _items(w, 111)
           if e.get("f3") == GOBO_FN and "f4" in e}
    palette = [it["f2"]
               for typ, payload in w.records if typ == 145
               for it in wpj_codec._decode_msg(payload, _ITEMS)["items"]
               if "f2" in it]
    hors = [g for g in palette if g not in ids]
    assert not hors, f"palette off the wheel: {hors} (wheel {sorted(ids)})"


def tranches_106(w):
    """105.f4/f7 = a slice of record 106, not a DMX address.

    The intervals [f4, f4+f7) tile [0, count(106)) exactly, and every entry of
    106 falls inside its fixture's DMX window. Reading f4 as a starting DMX
    address breaks both (registry, "record 105").
    """
    p105, p106 = _items(w, 105), _items(w, 106)
    p115, p116 = _items(w, 115), _items(w, 116)
    pos = 0
    for e in sorted(p105, key=lambda e: (e.get("f4", 0), e.get("f7", 0))):
        assert e.get("f4", 0) == pos, \
            f"105: slice at {e.get('f4', 0)} but {pos} entries of 106 consumed"
        pos += e.get("f7", 0)
    assert pos == len(p106), f"105: Σf7 = {pos} != count(106) = {len(p106)}"
    for e in p105:
        f = p115[e.get("f5", 0)]
        base = f.get("f2", 0)
        span = p116[f.get("f3", 0)].get("f2", 0)
        for k in range(e.get("f4", 0), e.get("f4", 0) + e.get("f7", 0)):
            canal = p106[k].get("f2", 0)
            assert base <= canal < base + span, \
                f"106[{k}].f2 = {canal} outside the DMX window " \
                f"[{base}, {base + span}) of fixture {e.get('f5', 0)}"


def patch_disjoint(w):
    """115.f2 = the starting DMX address: the windows never overlap."""
    p115, p116 = _items(w, 115), _items(w, 116)
    fen = sorted((f.get("f2", 0), p116[f.get("f3", 0)].get("f2", 0)) for f in p115)
    for (a, n), (b, _) in zip(fen, fen[1:]):
        assert a + n <= b, f"overlapping DMX windows: {a}+{n} > {b}"


def groupe_fixture(w):
    """115.f4 == 105.f6 == the fixture's group index, and 125 follows from it.

    Two records carry the assignment, redundantly: 115[r].f4 per fixture and
    105[e].f6 per patch entry. The 125[i].f4 mask (6 bytes, LE) **contains** the
    OR of the 1 << 115[r].f3 of the fixtures in slot i — so a slot mixing two
    profiles lights two bits there. Nine slots: A–H plus a ninth (index 8).

    **Containment, not equality (COV-26).** Equality held on 746 of 747 corpus
    slots and is broken by a file the device wrote: reordering record 116
    changes every profile index, and the firmware **ORs the new bit in without
    clearing the stale one** — a slot whose two fixtures give 0x6 stores 0xe,
    keeping a bit from the ordering before. So the mask is not recomputed from
    the patch, it accumulates, and a reader must not treat it as derived.
    Containment is exact on all 747.
    """
    p105, p115 = _items(w, 105), _items(w, 115)
    p125 = _items(w, 125)
    assert len(p125) == 9, f"125: {len(p125)} slots instead of 9"
    for e in p105:
        r = e.get("f5", 0)
        assert e.get("f6", 0) == p115[r].get("f4", 0), \
            f"105: fixture {r} in group {e.get('f6', 0)} but 115.f4 = " \
            f"{p115[r].get('f4', 0)}"
    for i, slot in enumerate(p125):
        attendu = 0
        for f in p115:
            if f.get("f4", 0) == i:
                attendu |= 1 << f.get("f3", 0)
        masque = int.from_bytes(bytes.fromhex(slot["f4"]["hex"])[:6], "little")
        assert masque | attendu == masque, \
            f"125[{i}]: mask {masque:#x} does not contain the group's " \
            f"profiles {attendu:#x}"


def moteurs_f16(w):
    """165.f16 = twelve 9-bit group masks, one per "engine".

    The packed varints are the bytes of a little-endian bit field cut into
    **9**-bit slices — 9 and not 8, because record 125 has nine slots: groups
    A–H plus the effects one.

    The alignment still tests itself, but through a **containment** and no
    longer an equality. Slice 1 was asserted equal to `move_fx_active` and that
    held on 3697 presets; a preset the device composed on 2026-09-01 carries
    slice 1 = 1 with `move_fx_active` = 0 (COV-14). What survives is
    `slice 1 ⊇ move_fx_active`, exact on every preset of the corpus, and it
    keeps the whole refuting power: at a stride of 8 slice 1 reads 254 where
    `move_fx_active` reads 255, and 254 does not contain 255.

    Slice 0 against `color_fx_active` is asserted **not at all**. Neither
    containment holds on today's corpus — 6 presets one way, 18 the other —
    so there is nothing here to check that would not be fitted.
    """
    for pre in _items(w, 165):
        h = pre.get("f16")
        if not h:
            continue
        oct_ = _varints(h["hex"])
        assert all(o < 256 for o in oct_), \
            f"165.f16: a varint larger than a byte in {h['hex']}"
        gros = int.from_bytes(bytes(oct_), "little")
        # The 9th bit — the effects slot — is only lit by the flash engines,
        # from slice 6 onwards: WOLF hits everything, smoke included. See the
        # registry, "FLASH-01".
        for m in range(6):
            assert not (gros >> (9 * m)) & 0x100, \
                f"165.f16: engine {m} lights the 9th slot in {h['hex']}"
        actif = _varints(pre.get("f24", {}).get("hex", ""))
        a = actif[0] if actif else 0
        tranche = (gros >> 9) & 0x1FF
        assert tranche | a == tranche, \
            f"165.f16: engine 1 = {tranche} does not contain move_fx_active " \
            f"{actif} in {h['hex']}"


def tranche5_f16(w):
    """165.f16 slice 5 == the mask of the groups whose f17 dimmer is non-zero.

    The registry read "slice 5 = always 255" over 2446 presets. That was the
    uniformity trap: across the whole corpus `f17` is [255]×8, so the mask is
    255 and nothing could vary. The device's own writer broke it by rewriting a
    file we had written (registry, "GEN-03 withdrawn"): on cues that light only
    one group it put slice 5 at 2 = B, and at 7 = A+B+C on those lighting three.

    The objection was lifted on 2026-08-27 (registry, "FX2-01 measured"): on a
    preset THE DEVICE created from scratch — not a clone of ours — slice 5 reads
    2 = B, exactly the only group whose `f17` is non-zero, while the beam engine
    is OFF. The rival reading "slice 5 = the Beam FX 2 mask" does not survive
    that.

    The identity is therefore trivially true on the corpus and discriminating on
    any file where a preset does not light every group — ours, or any project
    where the operator turned a group off in a preset. Drop one into `corpus/`
    and this assertion will check it.
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
            f"165.f16: slice 5 = {tranche} but the non-zero dimmers give " \
            f"{attendu} ({dimmers})"


def plages_111(w):
    """111.f1/f2 = the DMX bounds of a range, and every channel falls in a case.

    An exhaustive trichotomy over the corpus: a channel of 110 is either
    **unattributed** (no `f4`, a single empty range), or the isolated pattern
    `f4 = 18` (a single range `{f1: 255, f3: 41}`), or its ranges **tile
    [0, 255]** — once sorted by `f1`: the first at 0, each following the
    previous one's `f2`, the last ending at 255.

    The sort is not cosmetic. The storage order is **not** increasing in
    general: reordering the gobo page permutes these entries (SORT-01,
    device-confirmed) without touching the tiling. The earlier version worked by
    accident on a corpus where no page had ever been reordered, and falls over
    on the first project where one was.
    """
    c110, c111 = _items(w, 110), _items(w, 111)
    pos = 0
    for i, c in enumerate(c110):
        n = c.get("f2", 0)
        tr, pos = c111[pos:pos + n], pos + n
        if n == 1 and not tr[0]:
            assert "f4" not in c, \
                f"110[{i}]: an empty range but the channel carries f4 = {c['f4']}"
            continue
        att = 0
        for r in sorted(tr, key=lambda r: r.get("f1", 0)):
            if r.get("f1", 0) != att:
                break
            att = r.get("f2", 0) + 1
        else:
            if att == 256:
                continue                       # the common case: the ranges tile
        assert c.get("f4") == 18 and n == 1 and tr[0] == {"f1": 255, "f3": 41}, \
            f"110[{i}]: ranges neither tiling nor of the f4 = 18 pattern: {tr}"


# 106.f4 = the channel's role in the W1's engine, in bijection with the
# profile's "feature" 110.f4. A table observed across the whole corpus; an
# unknown role must fail the identity rather than slip by unnoticed.
ROLES_106 = {0: 7, 1: 1, 2: 2, 3: 25, 4: 26, 5: 27, 6: 31, 7: 32, 8: 33,
             9: 15, 10: 15, 11: 5, 12: 8, 14: 22, 15: 16, 21: 20, 22: 19}


def roles_106(w):
    """106.f4 = the channel's engine role; it determines the feature 110.f4.

    Every entry of 106 targets a channel of its fixture's profile, through
    `106.f2 - 115.f2` added to the `116.f3` offset. That channel's role and
    feature then match term for term across the whole corpus — which is what
    makes "which DMX channel carries this fixture's red" readable.
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
            assert role in ROLES_106, f"106: unknown role {role}"
            assert ROLES_106[role] == feat, \
                f"106: role {role} on feature {feat}, " \
                f"expected {ROLES_106[role]}"


def ordre_fixtures_115(w):
    """115.f6 = a complete permutation of the fixture indexes.

    One byte per fixture, each index exactly once. It is neither the sort by
    group nor the sort by profile — each works on part of the corpus only, and
    on complementary parts. It is a display order specific to the project. See
    the registry, "record 115".
    """
    d = wpj_codec._decode_msg(w.get(115), {5: ("items", {}), 6: ("ordre", "hex")})
    if "ordre" not in d:
        return
    o = d["ordre"]
    liste = list(bytes.fromhex(o if isinstance(o, str) else o["hex"]))
    assert sorted(liste) == list(range(len(d["items"]))), \
        f"115.f6: {liste} is not a permutation of 0..{len(d['items']) - 1}"


# The 111.f3 function of the range each 106 role uses, when it targets a
# single one. The wheels (11, 12) target none, and roles 1/2/10/21/22 overflow
# or carry a constant — see the registry, "record 106 f1/f3".
PLAGE_DU_ROLE = {0: 12, 3: 50, 4: 51, 5: 52, 6: 56, 7: 57, 8: 58,
                 9: 34, 14: 48, 15: 38}


def bornes_106(w):
    """106.f1/f3 = the DMX bounds of the range the role drives.

    When `[f1, f3]` coincides with a range of the channel's 111 — 2643 corpus
    entries out of 3775 — that range's function is the one the role imposes:
    the "red" role lands on range `f3 = 50`, "dimmer" on `12`, and so on. The
    identity constrains only that case; the other patterns are described in the
    registry and deliberately left free.
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
                        f"106: role {role} on range {r.get('f3')}, " \
                        f"expected {PLAGE_DU_ROLE[role]}"
                break


def tranches_151(w):
    """150[slot].f2/f1 = a slice of record 151, contiguous, and nothing orphaned.

    The same construction as `105.f4/f7` inside 106 and `116.f3/f2` inside 110:
    an (offset, length) pair cutting a flat list. Position slots that use none
    of it carry neither `f1` nor `f2`. See the registry, "record 151".

    **The exact tiling fell (COV-32).** This asserted `referenced == present`
    on all 90 corpus files, and a save the device wrote on 2026-09-01 broke it:
    group A's slots claim **6** entries of 151 where the record holds **1**,
    the three slices themselves still contiguous from 0. Which side is stale is
    **not settled** — 120's surplus in the same file is decided by arithmetic
    and this is not, and the discriminator is the `ALL POSITIONS` page. What
    survives is containment, `referenced >= present`: no entry of 151 is
    orphaned, which is the half a reader needs. The half that fell is the one
    that says nothing is referenced that is not there, and a reader must now
    clamp a slice to the record instead of trusting it.
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
            f"150[{'ABCDEFGH'[g]}][{i + 1}]: slice at {debut} but " \
            f"{pos} entries of 151 consumed"
        pos += n
    assert pos >= n151, \
        f"151: {pos} entries referenced, {n151} present — an orphaned entry"
    nfx = len(_items(w, 115))
    for k, e in enumerate(_items(w, 151) if w.get(151) else []):
        assert e.get("f1", 0) < nfx, \
            f"151[{k}].f1 = {e.get('f1', 0)} outside the {nfx} fixtures"


# The thirteen preset fields that carry one value per group A–H. All are
# exactly 8 packed varints, with no exception in the corpus — see the registry,
# "the per-group arrays".
TABLEAUX_PAR_GROUPE = (3, 7, 14, 17, 23, 27, 28, 29, 30, 32, 33, 34, 35)


def tableaux_par_groupe_165(w):
    """The preset's per-group fields are exactly 8 varints.

    A non-trivial constraint: a wrong varint split, or a field taken for a
    scalar, changes the count immediately. That is what filed `f3`, `f7`,
    `f14`, `f23` and `f27` — all zero in the corpus at the time — among the
    per-group values rather than among the shapeless unknowns. The bet paid off
    on three of the four: `f3`, `f7` and `f23` are the page selectors of beam,
    colour and move (registry, F7-01/03/04), and they are indeed arrays of
    eight. `f27` stays zero and unattributed.
    """
    for pre in _items(w, 165):
        for n in TABLEAUX_PAR_GROUPE:
            champ = pre.get(f"f{n}")
            if champ is None:
                continue
            vals = _varints(champ["hex"] if isinstance(champ, dict) else champ)
            assert len(vals) == 8, \
                f"165.f{n}: {len(vals)} varints instead of 8"


# f16 engine -> the bit of 165.f4 that must be set for it to be able to act.
# 0 = Color FX, 1 = Move FX, 2 = Beam FX; see the registry, "F4-03".
MOTEUR_VERS_F4 = {0: 3, 1: 2, 2: 4}


# f4_autorise_les_moteurs ("an engine active in f16 implies its bit in
# 165.f4") was WITHDRAWN on 2026-08-31: the implication was a correlation of
# saves born on the device, refuted by a project imported from WTOOLS (EXP-06:
# engine 2 active, f4 = 12 without bit 4) that the W1 opens without complaint.
# What it earned — identifying slice 2 of f16 as the Beam FX — stays in the
# registry, together with the refutation.


def schema_du_prefixe(w):
    """Byte 50 is the schema version, and 165.f32–f35 arrive at 10.

    The prefix is constant except for the UUID (20–35), the version counter
    (40–47) and this byte. The correlation is total across the corpus: schema 8
    without `f32`, schemas 10 and 11 with it. See the registry, "the prefix".
    """
    schema = w.prefix[30]
    assert w.prefix[16:20].hex() == "152b10c0", "prefix: constant 36-39 changed"
    assert w.prefix[28:30].hex() == "01f9", "prefix: constant 48-49 changed"
    assert w.prefix[31] == 0, "prefix: byte 51 is not zero"
    assert w.prefix[32:].hex() == "02bee81ca26ccb546dc7b6ec", \
        "prefix: constant 52-63 changed"
    a32 = any("f32" in pre for pre in _items(w, 165))
    assert a32 == (schema >= 10), \
        f"prefix: schema {schema} but f32 {'present' if a32 else 'absent'}"


def canal_principal_110(w):
    """110.f5 = the profile index of this channel's principal channel.

    A principal channel points at itself; a **fine** channel points at its
    coarse one. The channel pointed to always carries the same `f4`, which makes
    the 16-bit pair readable without guessing the byte order. Verified with no
    exception across the corpus's 1100 channels.
    """
    p110, p116 = _items(w, 110), _items(w, 116)
    for pr in p116:
        off, n = pr.get("f3", 0), pr.get("f2", 0)
        for j in range(n):
            c = p110[off + j]
            m = c.get("f5", 0)
            assert m <= j, f"110[{off + j}]: f5 = {m} points forward"
            assert p110[off + m].get("f4") == c.get("f4"), \
                f"110[{off + j}]: f5 points at a channel of feature " \
                f"{p110[off + m].get('f4')}, not {c.get('f4')}"


def flavours_155(w):
    """155.f2 = the sequence's engine, and it determines the value domain.

    The record holds four sequencers: item 0 is the **move** one (`f2` = 1),
    items 1 to 3 the **beam** ones (`f2` = 2) — the three `FX Seq` the Beam FX
    enumeration offers. The two engines do not store the same thing in the same
    place:

    - move: a **position index** into the group's palette 150, domain 0–19,
      plus 255 = "no position at this step";
    - beam: a **4-bit mask** over the group's four segments, domain 0–15. Eight
      groups × four segments = the 32 selections the manual advertises.

    Measured by FX6-05: segments 1 and 4 ticked on group A of step 1 wrote
    15 → 9, that is 0b1111 → 0b1001, into item 1.
    """
    seqs = _items(w, 155)
    assert len(seqs) == 4, f"155: {len(seqs)} sequences, 4 expected"
    for i, s in enumerate(seqs):
        fl = s.get("f2")
        attendu = 1 if i == 0 else 2
        assert fl == attendu, f"155[{i}]: flavour {fl}, {attendu} expected"
        vals = _varints(s["f4"]["hex"]) if isinstance(s.get("f4"), dict) \
            else s.get("f4", [])
        assert len(vals) == 128, f"155[{i}]: {len(vals)} values, 128 expected"
        haut = 19 if fl == 1 else 15
        for k, v in enumerate(vals):
            if fl == 1 and v == 255:
                continue                 # the "no position" sentinel
            assert v <= haut, \
                f"155[{i}]: value {v} at step {k // 8} group {chr(65 + k % 8)}, " \
                f"outside the 0–{haut} domain of flavour {fl}"


def _entrees_165(payload):
    """(f1, [raw entries]) of record 165, without interpreting the entries."""
    i, f1, entrees = 0, None, []
    while i < len(payload):
        tag, i = wpj_codec._rvarint(payload, i)
        if tag == 0x08:                      # f1 varint
            f1, i = wpj_codec._rvarint(payload, i)
        elif tag == 0x2A:                    # f5: one preset entry
            ln, i = wpj_codec._rvarint(payload, i)
            entrees.append(payload[i:i + ln]); i += ln
        else:
            raise AssertionError(f"165: unexpected tag {tag:#x}")
    return f1, entrees


def noms_de_preset_bornes(w):
    """No preset name exceeds 19 UTF-8 bytes.

    A device-confirmed limit (PRESET-05, 2026-08-26): the W1's rename UI caps
    at 19 characters and the loader enforces the same bound on a name written
    from a file — past it, the whole project refuses to open ("Error opening
    project"), loudly. A generator must therefore validate names BEFORE writing.
    """
    for pre in _items(w, 165):
        nom = pre.get("f25")
        if nom is None:
            continue
        octets = (bytes.fromhex(nom["hex"]) if isinstance(nom, dict)
                  else nom.encode("utf-8"))
        assert len(octets) <= 19, \
            f"165: a {len(octets)}-byte name: {octets!r}"


def ajout_de_preset():
    """Adding a preset: what the device writes, and what it discards.

    Two pairs of experiments (registry, "F30-04" and "FLASH-09"):

    - F30-04, the device adds a preset itself: outside 165, only the live-state
      records {115, 125, 155, 161} change. The file therefore carries NO
      external count of presets. And 165.f1 goes from 82 to 81 while the count
      goes from 82 to 83, with 81 named on both sides: "number of presets" is
      refuted by the after, "number of named presets" by the before.

    - FLASH-09 / PRESET-01, two entries added from a file (copies of entry 82,
      id and f16 slice changed): the addition is **device-confirmed** — stored,
      returned byte for byte, displayed and recallable after a cold reopen
      (registry, "PRESET-01"). The "deletion" first reported by FLASH-09 is
      retracted: the numbers of the "returned" download were those of the
      pre-deploy state. The edit's arithmetic stays checkable:
      len(candidate.165) - len(before.165) == 2 × (3 + len(entry 82)).

    A pair absent from the corpus = a check skipped, not a check passed.
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
            f"F30-04: records changed {sorted(bouges)}"
        f1a, ea = _entrees_165(av.get(165))
        f1b, eb = _entrees_165(ap.get(165))
        noms_a = sum(1 for p in wpj_codec.decode(165, av.get(165))["presets"]
                     if p.get("name"))
        noms_b = sum(1 for p in wpj_codec.decode(165, ap.get(165))["presets"]
                     if p.get("name"))
        assert (len(ea), noms_a, f1a) == (82, 81, 82), \
            f"F30-04 avant : {(len(ea), noms_a, f1a)}"
        assert (len(eb), noms_b, f1b) == (83, 81, 81), \
            f"F30-04 after: {(len(eb), noms_b, f1b)}"

    av, ca = charge("FLASH-09", "before.wpj"), \
        charge("FLASH-09", "candidate.wpj")
    if av and ca:
        assert av.prefix == ca.prefix, "FLASH-09: the edit touched the prefix"
        bouges = {t for (t, p1), (_, p2) in zip(av.records, ca.records)
                  if p1 != p2}
        assert bouges == {165}, f"FLASH-09: records changed {sorted(bouges)}"
        f1a, ea = _entrees_165(av.get(165))
        f1c, ec = _entrees_165(ca.get(165))
        assert f1a == f1c == 81, f"FLASH-09: f1 {f1a} / {f1c}"
        assert len(ec) == 85 and ec[:83] == ea, \
            "FLASH-09: the candidate is not before + 2 entries at the tail"
        for e in ec[83:]:
            assert len(e) == len(ea[82]), "FLASH-09: an entry of another size"
            diffs = sum(x != y for x, y in zip(ea[82], e))
            assert 0 < diffs <= 6, \
                f"FLASH-09: {diffs} bytes apart from entry 82"
        entete = 1 + len(wpj_codec._wvarint(len(ea[82])))
        assert len(ca.get(165)) - len(av.get(165)) == 2 * (entete + len(ea[82])), \
            "FLASH-09: the size difference is not \"the two additions, exactly\""


def carte_dmx_130(w):
    """130 = the DMX IN mapping table, and `f1` counts its entries.

    Measured on the device (MAP-01..05, registry). `f4` is the **function**
    targeted, not the screen's category: 20 = group dimmer, 27 = MAIN,
    70 = preset, 17 = BPM Tap, 10 = Wolf — and BPM Tap and Wolf are two entries
    of the **same** `Flash` category with distinct `f4`. `f2` is the instance
    index when the function is instanced, **255** otherwise.

    The DMX IN channel is **16 bits, spread**: `f5 * 256 + f6`, zero-based.
    `f5` stayed invisible across the whole corpus and six writes because
    everything fit below channel 256; it appears at CH300 (1, 43) and at CH512
    (1, 255), both exact. The panel's encoder stops at 512.

    An unmapped function has no entry at all — removing a mapping deletes the
    row and decrements `f1`; there is no sentinel.

    `f7` and `f8` are 1 everywhere, have never moved, and have no name.
    """
    for occurrence, _ in enumerate([t for t, _ in w.records if t == 130]):
        items = _items(w, 130, occurrence)
        annonce = wpj_codec._decode_msg(
            w.get(130, occurrence), {1: ("f1", "uint")}).get("f1", 0)
        assert annonce == len(items), \
            f"130.f1 = {annonce} but the table carries {len(items)} entries"
        for i, e in enumerate(items):
            canal = e.get("f5", 0) * 256 + e.get("f6", 0)
            assert canal < 512, \
                f"130[{i}]: DMX IN channel {canal + 1} past the universe"


# The 15 record types whose field 1 is the number of field-5 items. 145 has no
# field 1 at all (its 20 slots are implicit) and 165's is something else.
COMPTES_DE_TETE = (105, 106, 110, 111, 115, 116, 120, 125, 130, 135, 140, 150,
                   151, 155, 160)


def comptes_de_tete(w):
    """Field 1 = the number of entries, on 15 of the 20 record types.

    Free to check and it refutes something real: a reader that treats field 1
    as a version, a flag or a capacity. An empty table writes **no** field 1
    rather than a zero, so absence is accepted and a mismatch is not.

    `165.f1` is deliberately outside the list. It disagrees with the count on
    19 corpus files — always low by exactly the entries a preset capture
    appended, 81 against 83 and 81 against 85 — so whatever it counts, it is
    not the entries present.

    **Record 120 is now checked at containment, not equality (COV-32).** A save
    the device wrote trimmed 120 from 221 entries to 215 and left `f1` at 221.
    Arithmetic says which side is right: 215 is exactly the sum of the
    `channel_count` of each fixture's profile, in that file and in the eight
    that preceded it, so the **content** was corrected and the **counter** was
    left behind. The surplus of 6 came from the WTOOLS 2.0.2 session of COV-23
    and rode along in the same eight files that carry the misplaced `116.f12`
    (COV-30) — one session, two artefacts. `f1 >= len` is what survives, and a
    writer must not derive the entry list from `f1`.
    """
    for typ in COMPTES_DE_TETE:
        for occ in range(8 if typ in (140, 145, 150) else 1):
            try:
                charge = w.get(typ, occ)
            except KeyError:
                break
            d = wpj_codec._decode_msg(charge, _ITEMS)
            f1 = d.get("f1")
            if f1 is None:
                assert not d.get("items"), \
                    f"{typ}: {len(d['items'])} entries and no field 1"
                continue
            n = len(d.get("items", []))
            if typ == 120:
                assert f1 >= n, f"120: field 1 = {f1} but {n} entries"
            else:
                assert f1 == n, f"{typ}: field 1 = {f1} but {n} entries"


def boutons_live_edit(w):
    """160.f5 = the LIVE EDIT button, and 165.f18 addresses the same 80.

    Three things at once, exact on every corpus file that has record 160:
    the buttons a file's macros occupy are **distinct**, they all fall inside
    the 4 pages × 20 grid, and **every bit any preset sets in `f18` lands on a
    button some macro occupies**. The last one is what ties the two records
    together — a preset cannot carry a Live Edit that is not defined.

    Their wire order is free: 65 of 71 files store the macros out of button
    order, the same freedom record 111 has for gobo pads (SORT-01).

    A fourth thing, on the macro itself: `f1` is a list of bit masks and `f8`
    gives **one value per set bit** — `popcount(f1) == len(f8)`, exact on all
    490 corpus macros. It refutes any reading of `f8` as a per-group array,
    which is what its `[50] × 8` shape invites.
    """
    try:
        charge = w.get(160)
    except KeyError:
        return                            # 9 corpus files have no macros at all
    macros = wpj_codec._decode_msg(charge, _ITEMS).get("items", [])
    boutons = [m.get("f5", 0) for m in macros]
    assert len(set(boutons)) == len(boutons), \
        f"160: two macros on one button: {boutons}"
    assert all(b < 80 for b in boutons), \
        f"160: a button outside the 4 x 20 grid: {boutons}"
    for m in macros:
        f1 = _varints(m.get("f1", {}).get("hex", ""))
        f8 = _varints(m.get("f8", {}).get("hex", ""))
        assert sum(bin(x).count("1") for x in f1) == len(f8), \
            f"160: {sum(bin(x).count('1') for x in f1)} mask bits but " \
            f"{len(f8)} values"
    for pre in _items(w, 165):
        masque = _varints(pre.get("f18", {}).get("hex", ""))
        if not masque or any(o > 255 for o in masque):
            continue
        gros = int.from_bytes(bytes(masque), "little")
        for bit in range(80):
            assert not (gros >> bit) & 1 or bit in boutons, \
                f"165.f18 sets button {bit}, which no macro defines"


IDENTITES = (comptes_de_tete, boutons_live_edit, ranges_par_canal, palette_gobo, tranches_106, patch_disjoint,
              groupe_fixture, moteurs_f16, tranche5_f16,
              plages_111, roles_106,
              ordre_fixtures_115, bornes_106, tranches_151,
              tableaux_par_groupe_165,
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
            continue                      # variants B/C: out of scope
        n += 1
        for verif in IDENTITES:
            try:
                verif(w)
            except AssertionError as e:
                raise AssertionError(f"{path}: {verif.__name__}: {e}") from None
    if not n:
        return wpjlib.pas_de_corpus("wpj_identities")
    ajout_de_preset()
    print(f"{len(IDENTITES)} identities verified on {n} variant-A files"
          " (+ the F30-04 / FLASH-09 pairs)", file=sys.stderr)


if __name__ == "__main__":
    demo()
