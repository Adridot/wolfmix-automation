#!/usr/bin/env python3
"""The semantic JSON ↔ bytes codec for variant-A TLV records (on wpjlib).

The safety contract: decode(type, payload) returns a JSON-compatible dict whose
encode(type, dict) reproduces the EXACT bytes. decode checks that round trip
itself; on failure (unsupported type, unexpected protobuf) it returns
{"raw": hex} — never a loss, never an approximation. Proof: demo() over the
whole variant-A corpus.

Representation:
- a named field (proof: research/evidence.md) → a semantic key;
- an unidentified field → the neutral "fN" key: varint = int, length =
  {"hex":…}, fixed = {"f32":…}/{"f64":…};
- an absent field is absent from the dict (≠ an explicit zero); the dict's
  order is the wire order.
"""
import json
import sys
import uuid

import wpj_wire
import wpjlib

# Schemas: field → (name, kind). kind: "v" varint, "str" UTF-8, "hex" raw
# bytes, "uuid" 16 bytes as a dashed string, "packed" = packed varints (a
# list of ints), dict = sub-message (repeated for lists of entries), and
# ("split", ((n, part), …)) = a fixed-width blob cut into little-endian
# integers, one per named part. A split exists for one reason: a field whose
# bytes are understood in *pieces* and not as a whole. Its value is a dict of
# the parts, and a payload whose length is not the sum falls back to
# {"hex": …} like any other blob, so the round trip cannot be lost.
# 105: f4/f7 delimit the slice of record 106 that belongs to the entry, NOT a
# DMX address (the address is 115.f2). See the registry, "record 105".
# f6 = the group index (0-7 = A-H, 8 = the effects slot), redundant with
# 115.f4 — see the registry, "the fixture → group assignment".
# f1 is the **library** fixture id, stable across projects (1017 is the same
# `6x18W 6in1 RGBAW UV` in two unrelated rigs) — NOT an index into record 116,
# which is what `115.f3` holds. It was called "profile" until 2026-09-01, the
# same name `115.f3` carries: the two never agree on a single one of the
# corpus's 1394 patch entries, so one name for both was one name too few.
_PATCH = {1: ("library_id", "v"), 4: ("offset_106", "v"), 5: ("fixture", "v"),
          6: ("group", "v"), 7: ("entry_count_106", "v")}
# f9 is the profile UUID, not a digest: it is the identifier `GET_PROFILE`
# takes and `wolfmix.py profiles` reports — the file and the controller
# share one key space. No version check: the locally-authored profiles
# carry serial-derived identifiers that are not RFC 4122 v5.
# f3 = the index of this profile's first channel in record 110; with f2 it is
# the (offset, length) pair that cuts 110, and identity 3 checks that the
# offsets are the running sum of the counts. Documented in §7 since the corpus
# mining and never named here.
# f12 is the profile's **per-channel names**, one repeated string per channel of
# this profile, empty where the channel type already names it — the labels the
# FIXTURE BUILDER screen shows. Device-confirmed on a project the panel created
# from scratch (COV-43): 16 entries for a 16-channel profile, aligned to its own
# `110.f4` types, and the two `Generic` channels carry `Color Effect` and
# `Reset`, name for name what that screen printed in COV-25.
# **A reader must not trust the alignment blindly.** WTOOLS 2.0.2 cut one
# profile-local array with each item's *global* offset into record 110, so in
# the files of COV-30 those same 16 names are spread across three other
# profiles and the profile they belong to carries none.
_PROFIL = {2: ("channel_count", "v"), 3: ("offset_110", "v"),
           8: ("name", "str"), 9: ("uuid", "uuid"), 11: ("timestamp", "v"),
           12: ("channel_names", "str")}
# The order of a pad's 7 channels: device-confirmed (the W1's RGB+ view, raw 0-255)
_PAD = {1: ("red", "v"), 2: ("green", "v"), 3: ("blue", "v"),
        4: ("white", "v"), 5: ("amber", "v"), 6: ("lime", "v"), 7: ("uv", "v")}

# FX sub-message, shared by Beam/Color/Move — SPEC.md §5, FX submessage.
# FX6-02/03: f6 = Phase, f8 = Size, f9 = Speed, f2 = Fade. The speed had been
# read on f2 since ACC-04; the screen says f9, and f2 follows the fade all the
# way to vanishing when it reaches 0. "speed" stays the name of the speed: it
# changes field, not meaning, and callers keep their intent.
# f3 and f5 mean different things per engine, so the schema stops being one:
# `_FX` holds what the three share, and each engine extends it. One shared
# schema could not carry two names, which is why both stayed neutral keys
# until 2026-09-01 — the fix is three dicts, not a compromise name.
_FX = {7: ("effect", "v"), 4: ("link_order", "v"), 10: ("speed_source", "v"),
       1: ("bpm_division", "v"), 2: ("fade", "v"),
       6: ("phase", "v"), 8: ("size", "v"), 9: ("speed", "v")}
# f3 is the third encoder's second mode: `Feature` on beam (FX6-03, `1` = Zoom
# measured, absent = 0 = Dimmer), `Fan` on move (FX6-04, a direct percentage,
# default 50 — present on every preset because a centred fan is not a null
# fan). Colour has no second mode and never carries f3.
# f5: a 16-bit mask over record 135's pads on colour (two packed varints, pads
# 1-8 then 9-16), the effect's position on move (one packed varint, 0/1/2/5/6
# seen). On beam it is absent from every preset of the corpus — SPEC's Q7,
# hypothesized inert, and nothing here names it.
_FX_BEAM = {**_FX, 3: ("feature", "v")}
_FX_COLOR = {**_FX, 5: ("color_mask", "packed")}
_FX_MOVE = {**_FX, 3: ("fan", "v"), 5: ("effect_position", "packed")}
_PRESET = {
    19: ("id", "v"), 25: ("name", "str"),
    1: ("beam_fx1", _FX_BEAM), 2: ("beam_fx2", _FX_BEAM),
    5: ("color_fx1", _FX_COLOR), 6: ("color_fx2", _FX_COLOR),
    21: ("move_fx1", _FX_MOVE), 22: ("move_fx2", _FX_MOVE),
    28: ("positions", "packed"),          # position index per group A–H
    29: ("gobos", "packed"),              # gobo index (type 145) per group,
                                          # 0-based, 255 = none — device-confirmed
    30: ("color_pattern", "packed"),    # the static colour's PATTERN per group
                                          # A–H (name read on screen) — device-confirmed
    # f31: 20 packed varints = the bytes of a 160-bit field, cut into eight
    # 20-bit masks, one per group A–H; bit n of group g = pad n+1 of that
    # group's palette 140 — device-confirmed, registry
    # « f31 — one 20-pad mask per group A–H ».
    31: ("static_color", "packed"),
    # f10: the content mask, six bits, 1 = toggle OFF, in PRESET EDIT screen
    # order — bit0 COLOR, 1 MOVE, 2 BEAM, 3 GOBO, 4 LIVE EDIT, 5 OTHER
    # (bit 5 predicted, not yet measured). See the registry, F4-02.
    10: ("content_mask", "v"),
    # f16: the bytes of a little-endian bit field cut at a stride of **9** —
    # nine because record 125 has nine slots. Twelve slices: 0 Color FX,
    # 1 Move FX, 2 Beam FX, 5 the groups the preset addresses, 6-10 the WOLF /
    # STROBE / BLACKOUT / BLINDER / SPEED flash keys (511 = latched, all nine
    # bits), 3/4/11 unattributed. Confirmed in both directions on the five
    # flash slices (§5.7). At a stride of 8, slice 1 would read 254 where
    # `move_fx_active` says 255 — the alignment tests itself.
    16: ("engine_masks", "packed"),
    # f18: 10 packed varints = 80 bits, one per LIVE EDIT button (4 pages of
    # 20). `f10`'s LIVE EDIT bit says *whether*, this says *which* (§5.5).
    18: ("live_edit_mask", "packed"),
    # The preset's own envelope, in milliseconds. `fade` on an FX sub-message
    # is a percentage of the step time — a different quantity, hence the unit
    # in the name here.
    11: ("fade_ms", "v"), 15: ("hold_ms", "v"),
    # f4: a permission mask over the three FX engines — engine 0 active in
    # `f16` implies bit 3 here, engine 1 bit 2, engine 2 bit 4, on every preset
    # of every file. One-directional: a page may permit an engine none of its
    # presets uses. Bit 0 is SPEC's Q2 and is not resolved by the name.
    4: ("engine_permissions", "v"),
    17: ("dimmers", "packed"),            # dimmer per group A–H
    # The five features of the STATIC GOBO screen, as a percentage per group
    # A–H — device-confirmed by a preset capture, see "GOBO-02".
    14: ("gobo_rotate", "packed"), 32: ("gobo_focus", "packed"),
    33: ("gobo_prism", "packed"), 34: ("gobo_zoom", "packed"),
    35: ("gobo_iris", "packed"),
    8: ("color_fx_active", "packed"), 24: ("move_fx_active", "packed"),
    # The page selector per group A–H: 0 = FX1, 1 = FX2. The record files each
    # engine as a quadruple — pair, selector, active: f1/f2/f3 for beam,
    # f5/f6/f7/f8 for colour, f21/f22/f23/f24 for move. All three are measured,
    # one shot each: F7-01 colour, F7-03 move, F7-04 beam. Independent of the
    # `f16` mask: a group keeps its pending page even when the engine is off.
    # A page 1 set by hand reads 0, like a page never set — the field encodes
    # the page, not the fact of having been set (F7-04's control).
    # f27: the per-group position FADE, in **milliseconds** — the `FADE` the
    # ALL POSITIONS page prints per group. Three points on one line: 0 ↔ 0s
    # on a panel-composed project, 1000 ↔ 1s on recall, and 3000 ↔ 3s written
    # by a capture (COV-10). It sits immediately before `f28`, the per-group
    # position index — two per-group tables side by side, which is what the
    # field numbering is good for. Measured on group A alone: this rig has no
    # fixture on the other seven, so their slots are read by position in an
    # array whose eight-element shape is correlated 45/45, not measured.
    27: ("position_fade_ms", "packed"),
    3: ("page_beam_fx", "packed"),
    7: ("page_color_fx", "packed"), 23: ("page_move_fx", "packed"),
}

# 102: the flash-FX settings, SPEC §6. Every field but `f11` was written by
# the device in a single-variable save and read back off the Settings screen.
# `f4` is packed rather than "hex": the release mode is an enumeration of five
# values, so no element can reach the two-byte varint that would change the
# length. `f11` stays a neutral key — it is `correlated` as *inert*, which is
# not a meaning, and naming it would be the exact lie this codec avoids.
_FLASH_FX = {1: ("blackout_excluded_groups", "v"),
             2: ("blinder_fade_out", "v"),
             3: ("blinder_excluded_groups", "v"),
             4: ("release_modes", "packed"),
             5: ("smoke_fan_speed", "v"), 6: ("smoke_intensity", "v"),
             7: ("speed_multiplier", "v"),
             8: ("strobe_excluded_groups", "v"), 9: ("strobe_speed", "v"),
             10: ("wolf_excluded_groups", "v")}

# 106: one entry per mapped channel, SPEC §7.5. `f1`/`f3` are the DMX window
# the role drives and `f5`/`f6` the fixture's travel limits — two pairs that
# read alike and mean different things, which is why both carry their axis in
# the name. `bornes_106` and `roles_106` in wpj_identities check f1/f3 and f4.
_CHANNEL_ROLE = {1: ("range_start", "v"), 2: ("dmx_channel", "v"),
                 3: ("range_end", "v"), 4: ("role", "v"),
                 5: ("limit_low", "v"), 6: ("limit_high", "v")}

# 110: the flattened channel table of every profile, SPEC §7.6.
# `f2` is the **range count** — the size of this channel's slice of 111 — not
# a feature enum: the identity `110[c].f2 == len(111 slice of c)` holds on the
# whole corpus and is what killed the enum reading. The feature is `f4`, in
# bijection with the engine role `106.f4` (`roles_106`). SPEC §7's bullet still
# says "f2 = feature enum, f4 = default value"; the identities are what run.
# `f1` = 1 on 568 of the corpus's channels and absent on the rest — a flag with
# no reading, left as a neutral key.
_CHANNEL = {2: ("range_count", "v"), 3: ("offset_111", "v"),
            4: ("feature", "v"), 5: ("principal_channel", "v")}

# 155: the four FX sequences, SPEC §8. `f2` says which engine owns the sequence
# and that sets the domain of `f4`: move (1) stores a position index per step
# and group, beam (2) a 4-bit segment mask. `f4` is 128 PACKED varints —
# 16 steps × 8 groups, step-major — and reading it as a byte array works by
# accident until one value exceeds 127 (FX6-05).
_SEQUENCE = {1: ("groups_per_step", "v"), 2: ("engine", "v"),
             3: ("step_count", "v"), 4: ("steps", "packed")}

# Field 1 is the item count on 15 of the 20 record types — checked as an
# identity (`comptes_de_tete`) with no exception on the corpus, an empty table
# writing no field 1 at all rather than a zero. Record 145 carries none (its 20
# slots are implicit, §3.4) and `165.f1` is NOT the count: it disagrees on 19
# corpus files, always by exactly the presets a capture appended, which is why
# SPEC leaves its meaning open.
_COUNT = ("entry_count", "v")

SCHEMAS = {
    101: {1: ("name", "str")},
    102: _FLASH_FX,
    105: {1: _COUNT, 5: ("patch", _PATCH)},
    106: {1: _COUNT, 5: ("channel_roles", _CHANNEL_ROLE)},
    110: {1: _COUNT, 5: ("channels", _CHANNEL)},
    155: {1: _COUNT, 5: ("sequences", _SEQUENCE)},
    # 115.f6 (on the record, not the items) is the fixture display order: a
    # complete permutation of 0…n−1, checked as an identity on every corpus
    # file. `f5` = 65535 on all 1381 fixture rows and has no reading.
    # `f9` is `slot_id`: a per-fixture identifier the panel allocates as the
    # **lowest free number**, distinct within a file, and it follows the
    # fixture rather than its rank — a deletion does not renumber the
    # survivors (COV-46), a reorder does not move them (COV-47), and a new row
    # takes the number a deleted one freed (COV-49) or the lowest unused one
    # (COV-52 = 5, COV-53 = 6). It is **not** a position index, which is the
    # reading COV-15 refuted: a six-fixture project carries 20…25.
    # **Absent is 0 only where the rest of the rows carry the field** (COV-49).
    # Twelve corpus files carry it on no row at all, and reading those as
    # twenty fixtures all holding slot 0 is the trap — absence has no general
    # rule here (COV-41 is the other direction).
    # The ITEMS' `f6`/`f7` are not per-fixture data: they are uniform within a
    # file when present, and a save **removes** them as readily as another save
    # adds them — COV-42 watched all four rows lose `177`/`124` on a save that
    # touched nothing about the patch. A writer must not synthesise them.
    # `f2` absent is DMX address **0**, not an unpatched fixture (COV-41).
    115: {1: _COUNT, 5: ("fixtures", {2: ("dmx_address", "v"),
                                      3: ("profile", "v"), 4: ("group", "v"),
                                      9: ("slot_id", "v")}),
          6: ("display_order", "hex")},
    116: {1: _COUNT, 5: ("profiles", _PROFIL)},
    # 120: one entry per (fixture, profile channel), the blocks in **ascending
    # DMX address** order — not the item order of 115. `f1` is the channel's
    # DMX value, emitted on every channel no engine role claims: eight such
    # channels were predicted from the file and read back off the live frame
    # exactly, and they stay put while an effect moves everything around them
    # (COV-16). The table is constant per profile.
    # `f4` (1 everywhere) and `f5` (1 or 2, and only on the moving heads) keep
    # neutral keys: `f5` is 1 on offsets 0-1 and 2 on offsets 2-3, and a shape
    # is not a reading.
    # `f6` is `dmx_channel`: an absolute DMX channel inside its own fixture's
    # span — a head at address 16 carries 18, 19, 16, 17 and the next, at 32,
    # carries 34, 35, 32, 33 (COV-50, device-confirmed). The name says that and
    # only that. **It is not this entry's own slot**: the entries are
    # positional in ascending DMX address (COV-16) and the quadruple is a
    # permutation of its block, so *which* channel of the block an entry names
    # is a second question and it is not read. The out-of-span cases are
    # checked as an anomaly rather than an identity — every one of them belongs
    # to a capture where a device save dropped an entry at the head of the
    # record (COV-53), which is what the anomaly exists to see.
    # The record's own `f4` is `occupancy`: a **run-length encoded map of the
    # 512 DMX channels**. One varint per run, in channel order — under 128 it
    # is a free run of that length, at or above 128 an occupied run of v − 128.
    # A run therefore caps at 127 and a longer one is split, which is why a
    # patch of four heads reads `[192, 127, 127, 127, 67]`: 64 occupied, then
    # 448 free. The runs sum to exactly **512** on all 104 corpus files, the
    # occupied count equals record 120's entry count on all 104, and the
    # reading re-encodes the stored bytes exactly on all 104 — including the
    # firmware's own choice of where to split. Single-variable differential:
    # COV-29 moved one fixture 500 → 300 and the map lost channel 499 and
    # gained 299, one channel, base 0. It maps the **record's entries**, not
    # the patch: on the eight files carrying COV-32's surplus of six it marks
    # six channels the patch does not justify, and on the four captures of the
    # COV-53 defect it is short by one. See COV-55.
    120: {1: _COUNT, 4: ("occupancy", "packed"),
          5: ("channels", {1: ("value", "v"),
                           6: ("dmx_channel", "v")})},                      # an empty {} entry = `2a 00` = all zero
    # 125: the nine group slots. `f4` is read in two pieces, which is why it is
    # a split and not one name: bytes 0-5 are the little-endian **profile
    # mask**, and the identity `groupe_fixture` checks `stored ⊇ derived` on it
    # — it accumulates, the firmware ORs a new profile index in without
    # clearing the stale one, so a reader must not recompute it (COV-26).
    # What follows is a **varint**, not the fixed byte this schema first
    # assumed: it read `0x30`/`0x38` on 891 corpus slots and grew to two bytes
    # when its value crossed 128, reaching 184 (COV-51). It keeps a neutral
    # key — it moves in the same save as record 161's shared tail without
    # either deriving from the other, and COV-22 refuted the preset-count
    # reading it had.
    125: {1: _COUNT, 5: ("groups", {
        4: ("mask", ("split", ((6, "profile_mask"), ("varint", "f4_tail")))),
        8: ("name", "str")})},
    135: {1: _COUNT, 5: ("pads", _PAD)},
    # f2 = the group index 0-7 (A-H), absent for A. SPEC §3.1 retracted the
    # earlier "page" reading in prose on three device readings; the codec
    # carried the retracted name until 2026-09-01.
    140: {1: _COUNT, 2: ("group", "v"), 5: ("pads", _PAD)},
    # 111: the value ranges of a channel (SPEC §7.6). f1/f2 = first and last
    # DMX value, f3 = function (14 = gobo wheel), f4 = the gobo image id of the
    # wheel ranges (= 145.f2, identity checked). The wire order is the pad
    # order, and it is free — device-confirmed, SORT-01.
    111: {1: _COUNT, 5: ("ranges", {1: ("start", "v"), 2: ("end", "v"),
                         3: ("function", "v"), 4: ("gobo_id", "v")})},
    # 145: the gobo palette. f1 = icon-font glyph (' ' = empty), f2 = gobo
    # image id (= 111[range].f4), f3 = an optional name, operator-assignable and
    # written off-device — device-confirmed, RENAME-01. See the registry.
    145: {2: ("group", "v"),
          5: ("gobos", {1: ("glyph", "str"), 2: ("gobo_id", "v"),
                        3: ("name", "str")})},
    # 150: the static POSITION palette of one group, 20 slots (SPEC §3.2).
    # `f1`/`f2` cut this slot's slice of record 151, the same (length, offset)
    # pair as 105 into 106 and 116 into 110 (§8.1, POS-03).
    # The four values are percentages stored as **percent × 65536**, not 65535:
    # 32768/65536 is exactly 0.5 and every predicted DMX channel lands, which
    # 32768/65535 misses by one unit on two of them (POS-02). `f4` is signed
    # around 32768.
    # An earlier revision of SPEC read `f3` as pan and `f4` as tilt. Both were
    # wrong, and the corpus could not catch it: every named slot of the group
    # examined reads PAN 50 %, indistinguishable from the neutral fields. Only
    # the device screen separated them.
    # `f8` is the CROSS half of the FAN | CROSS encoder and stays a neutral
    # key: SPEC §3.2 has it as [hypothesized], and a name is a claim.
    150: {1: _COUNT, 2: ("group", "v"),
          5: ("positions", {1: ("entry_count_151", "v"),
                            2: ("offset_151", "v"),
                            3: ("fan", "v"), 4: ("focus_offset", "v"),
                            5: ("name", "str"),
                            6: ("pan", "v"), 7: ("tilt", "v"),
                            8: ("cross", "v")})},
    # 151: the positions of fixtures "detached" from a slot of 150, cut by
    # 150.f1/f2. Three signed offsets, value = (v - 32768) / 32767 —
    # device-confirmed on the POSITION screen. See the registry, "POS-04".
    151: {1: _COUNT, 5: ("detached", {1: ("fixture", "v"), 2: ("focus_offset", "v"),
                            3: ("pan_offset", "v"), 4: ("tilt_offset", "v")})},
    # 130: the DMX IN mapping table (MAP-01..05, registry). f4 = the function
    # targeted — 20 = group dimmer, 27 = MAIN, 70 = preset, 17 = BPM Tap,
    # 10 = Wolf: this is NOT the screen's category, two entries of the same
    # category carry different f4. f2 = the instance index when the function is
    # instanced (group 0-7, preset 0-n), and **255** when it is not. The DMX IN
    # channel is **16 bits spread over two fields**: `channel_base0 = f5 * 256
    # + f6`, the displayed channel being channel_base0 + 1. f5 stayed invisible
    # until CH300 because the whole corpus fit under 256 — measured at CH300
    # (f5=1, f6=43) and CH512 (f5=1, f6=255). An unmapped function has **no
    # entry**: absence, not a sentinel. An entry's key is (f4, f2), never its
    # rank: the wire order moves without the content changing. f1 = the number
    # of entries. f7 and f8 are 1 everywhere, have never moved, and stay
    # unnamed.
    130: {1: _COUNT, 5: ("mappings", {2: ("instance", "v"), 4: ("function", "v"),
                           5: ("channel_high_byte", "v"),
                           6: ("channel_low_byte", "v")})},
    # 160: the LIVE EDIT macros, one per operator-defined button (COV-18).
    # `f5` is the **button index**, 0-based in a grid of 4 pages × 20 = 80 —
    # the same 80 the preset's `live_edit_mask` addresses, and every bit any
    # preset sets falls on a button a macro occupies (71/71 files). Measured:
    # a macro created on the button the panel labels "Live Edit 6" stores 5.
    # `f8` holds the values; the one set on screen, 200, is what came back.
    # Absent `f6` = the panel synthesises "Live Edit N", like `Position N`
    # and `Gobo N`. `f1` and `f7` stay neutral: no reading (COV-19).
    # `f1` is a list of bit masks and `f8` gives **one value per set bit**, in
    # order: `popcount(f1) == len(values)` on all 490 corpus macros, no
    # exception. `len(f1)` never exceeds the fixture count, which fits one mask
    # per targeted fixture — consistent, not measured, so the name says what
    # the identity says and no more.
    # `f7` keeps its NEUTRAL key and gains a wire kind, the same move record
    # 161's `f3` got: it is the **run-length map** record `120.f4` uses — under
    # 128 a free run, at or above 128 an occupied run of `v − 128` — its runs
    # summing to exactly 512 and its occupied slots numbering exactly `len(f1)`
    # on all 594 corpus macros, one slot per targeted fixture, the reading
    # re-encoding the stored bytes on all 594. **What a slot indexes is not
    # read** (COV-56), so `packed` types the bytes and claims nothing: a diff
    # can now point at which slot moved instead of at six varints of hex.
    160: {1: _COUNT, 5: ("macros", {1: ("value_masks", "packed"),
                                    5: ("button", "v"), 6: ("name", "str"),
                                    7: ("f7", "packed"),
                                    8: ("values", "packed")})},
    165: {5: ("presets", _PRESET)},
    # 161 — SPEC's Q8. Three items, each a packed array of exactly **188**
    # varints in all 270 corpus occurrences (COV-06); reading it as bytes works
    # by accident, which is the trap record 155 sprang first. `f3` keeps a
    # NEUTRAL key on purpose: the entry declares the wire kind and claims
    # nothing, and `wpj_coverage` counts an `fN` name as unread wherever it
    # comes from — the schema types these bytes, it does not read them. Of the
    # 564 values exactly six ever move (COV-21) and none is attributed, so Q8
    # is as open as it was. What changes is that a diff can now point at
    # *which* value moved instead of at 190 bytes of hex.
    161: {5: ("items", {3: ("f3", "packed")})},
}
# Nothing is a deliberate passthrough any more: every record type the container
# carries has a schema, and 161's names nothing inside it. Data rather than a
# comment, because `tools/wpj_counts.py` checks the documents against it — a
# record that moves in or out must make the gate fail until the prose follows.
PASSTHROUGH = ()

# Every record type the container is known to carry.
TYPES = tuple(sorted(set(SCHEMAS) | set(PASSTHROUGH)))


# --- wire protobuf -----------------------------------------------------------

_rvarint = wpj_wire.read_varint          # one varint reader for the repository
                                         # (WireError is a ValueError, so the
                                         # existing `except` clauses still catch)


def _wvarint(v):
    # -1 would not terminate (the arithmetic shift stays at -1) and True would
    # encode as 1 without anyone asking for it.
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"varint: integer expected, got {v!r}")
    if v < 0:
        raise ValueError(f"varint: negative value {v}")
    out = bytearray()
    while True:
        b = v & 0x7F; v >>= 7
        out.append(b | (0x80 if v else 0))
        if not v:
            return bytes(out)


# Two 2026-09-01 renames are deliberately NOT in this table: `105.f1`
# "profile" → "library_id" and `140.f2` "page" → "group". Both old names are
# still live elsewhere — `115.f3` is a profile index, and a show spec addresses
# record 150 by "page" — so an alias here would turn a correct key into a
# guided error. They fail as plain unknown keys instead.
#
# The public keys were French until 2026-08-31. They are not accepted as
# aliases: a retired key is an error, and the error names its replacement. The
# repository had no tag, no release and no known consumer — the moment was
# right, and an alias layer would have been code written to be deleted.
CLES_RETIREES = {
    "adresse_dmx": "dmx_address",
    "ambiances": "moods",
    "ambre": "amber",
    "blanc": "white",
    "bleu": "blue",
    "canal": "channel",
    "canal_octet_bas": "channel_low_byte",
    "canal_octet_haut": "channel_high_byte",
    "canaux": "channels",
    "cible": "target",
    "color_fx_actif": "color_fx_active",
    "couleur": "color",
    "couleur_statique": "static_color",
    "debut": "start",
    "detachees": "detached",
    "effet": "effect",
    "energie": "energy",
    "fin": "end",
    "fonction": "function",
    "glyphe": "glyph",
    "gobo_noms": "gobo_names",
    "gobo_ordre": "gobo_order",
    "groupe": "group",
    "groupes": "groups",
    "masque_contenu": "content_mask",
    "modele": "template",
    "move_fx_actif": "move_fx_active",
    "nb_canaux": "channel_count",
    "nb_entrees_106": "entry_count_106",
    "nom": "name",
    "pattern_couleur": "color_pattern",
    "plages": "ranges",
    "profil": "profile",
    "profils": "profiles",
    "rouge": "red",
    "vert": "green",
    "vitesse": "speed",
}


def remplacante(cle):
    """The English name of a retired French key, or None."""
    return CLES_RETIREES.get(cle)


def _split(chunk, parts):
    """A blob cut into named pieces → {part: int}, or {"hex": …}.

    A piece is `(n, name)` for n little-endian bytes, or `("varint", name)` for
    a varint, which may only be the last piece. The varint form is not
    decoration: `125.f4`'s tail was a single byte on 891 corpus slots and grew
    to **two** when its value crossed 128 (COV-51), so a fixed width was wrong
    and the fallback below is what caught it.
    """
    out, i = {}, 0
    for n, nom in parts:
        if n == "varint":
            try:
                out[nom], i = _rvarint(chunk, i)
            except ValueError:
                return {"hex": chunk.hex()}
        else:
            if i + n > len(chunk):
                return {"hex": chunk.hex()}
            out[nom] = int.from_bytes(chunk[i:i + n], "little"); i += n
    return out if i == len(chunk) else {"hex": chunk.hex()}


def _unsplit(v, parts):
    """The inverse. Raises rather than truncate — decode() re-checks anyway."""
    if set(v) != {nom for _, nom in parts}:
        raise ValueError(f"split: expected {[n for _, n in parts]}, got {list(v)}")
    return b"".join(_wvarint(int(v[nom])) if n == "varint"
                    else int(v[nom]).to_bytes(n, "little")
                    for n, nom in parts)


def _decode_msg(buf, schema):
    out, i = {}, 0
    while i < len(buf):
        tag, i = _rvarint(buf, i)
        f, wt = tag >> 3, tag & 7
        if f == 0:
            raise ValueError("champ 0")
        nom, genre = schema.get(f, (f"f{f}", None))
        if wt == 0:
            v, i = _rvarint(buf, i)
        elif wt == 2:
            ln, i = _rvarint(buf, i)
            if i + ln > len(buf):
                raise ValueError("longueur")
            chunk = buf[i:i + ln]; i += ln
            if genre == "str":
                try:
                    v = chunk.decode("utf-8")
                except UnicodeDecodeError:
                    v = {"hex": chunk.hex()}
            elif genre == "packed":
                try:
                    v, j = [], 0
                    while j < len(chunk):
                        x, j = _rvarint(chunk, j)
                        v.append(x)
                except ValueError:
                    v = {"hex": chunk.hex()}
            elif genre == "hex":
                v = chunk.hex()
            elif genre == "uuid":
                v = str(uuid.UUID(bytes=chunk)) if len(chunk) == 16 \
                    else {"hex": chunk.hex()}
            elif isinstance(genre, tuple) and genre[0] == "split":
                v = _split(chunk, genre[1])
            elif isinstance(genre, dict):
                try:
                    v = _decode_msg(chunk, genre)
                except ValueError:
                    v = {"hex": chunk.hex()}
            else:
                v = {"hex": chunk.hex()}
        elif wt == 5:
            if i + 4 > len(buf):
                raise ValueError("f32")
            v = {"f32": buf[i:i + 4].hex()}; i += 4
        elif wt == 1:
            if i + 8 > len(buf):
                raise ValueError("f64")
            v = {"f64": buf[i:i + 8].hex()}; i += 8
        else:
            raise ValueError(f"wire type {wt}")
        if isinstance(genre, dict):          # a list of entries: always a list
            out.setdefault(nom, []).append(v)
        elif nom in out:                     # unexpected repeat → list
            if not isinstance(out[nom], list):
                out[nom] = [out[nom]]
            out[nom].append(v)
        else:
            out[nom] = v
    return out


def _encode_msg(d, schema):
    inv = {nom: (f, genre) for f, (nom, genre) in schema.items()}
    out = bytearray()
    for nom, val in d.items():
        if nom in inv:
            f, genre = inv[nom]
        elif nom.startswith("f") and nom[1:].isdigit():
            f, genre = int(nom[1:]), None
        else:
            neuve = remplacante(nom)
            if neuve:
                raise ValueError(
                    f"key {nom!r} was retired on 2026-08-31: write {neuve!r}")
            raise ValueError(f"unknown key {nom!r}")
        if genre == "packed" and isinstance(val, list) and \
                not (val and isinstance(val[0], (list, dict))):
            vals = [val]                     # one occurrence = one list of ints
        else:
            vals = val if isinstance(val, list) else [val]
        for v in vals:
            out += _emit(f, genre, v)
    return bytes(out)


def _emit(f, genre, v):
    if isinstance(v, dict) and set(v) == {"f32"}:
        return _wvarint(f << 3 | 5) + bytes.fromhex(v["f32"])
    if isinstance(v, dict) and set(v) == {"f64"}:
        return _wvarint(f << 3 | 1) + bytes.fromhex(v["f64"])
    if isinstance(v, int):
        return _wvarint(f << 3) + _wvarint(v)
    if isinstance(v, dict) and set(v) == {"hex"}:
        pl = bytes.fromhex(v["hex"])
    elif genre == "uuid":                # before the str test below, which
        pl = uuid.UUID(v).bytes          # would encode the 36 chars as UTF-8
    elif genre == "packed" and isinstance(v, list):
        pl = b"".join(_wvarint(x) for x in v)
    elif genre == "hex":
        pl = bytes.fromhex(v)
    elif genre == "str" or isinstance(v, str):
        pl = v.encode("utf-8")
    elif isinstance(genre, tuple) and genre[0] == "split":
        pl = _unsplit(v, genre[1])
    elif isinstance(v, dict):
        pl = _encode_msg(v, genre if isinstance(genre, dict) else {})
    else:
        raise ValueError(f"value cannot be encoded for f{f}: {v!r}")
    return _wvarint(f << 3 | 2) + _wvarint(len(pl)) + pl


# --- API ---------------------------------------------------------------------

def encode(typ, d):
    if set(d) == {"raw"}:
        return bytes.fromhex(d["raw"])
    return _encode_msg(d, SCHEMAS.get(typ, {}))


def decode(typ, payload):
    if typ in SCHEMAS:
        try:
            d = _decode_msg(payload, SCHEMAS[typ])
            if encode(typ, d) == payload:    # byte-level self-check
                return d
        except ValueError:
            pass
    return {"raw": payload.hex()}


def projet_vers_dict(path):
    w = wpjlib.Wpj.load(path)
    return {"fichier": path, "prefixe": w.prefix.hex(),
            "records": [{"type": t, **decode(t, p)} for t, p in w.records]}


# --- the fidelity proof ------------------------------------------------------

def demo():
    files = wpjlib.corpus_files()
    if not files:
        return wpjlib.pas_de_corpus("wpj_codec")
    stats, nb_fichiers = {}, 0
    for path in files:
        try:
            w = wpjlib.Wpj.load(path)
        except (ValueError, OSError):
            continue                          # variantes B/C ou illisible
        nb_fichiers += 1
        for t, p in w.records:
            d = decode(t, p)
            assert encode(t, d) == p, f"fidelity broken: type {t} in {path}"
            occ, raw = stats.get(t, (0, 0))
            stats[t] = (occ + 1, raw + ("raw" in d))
    if not nb_fichiers:
        return wpjlib.pas_de_corpus("wpj_codec")
    print(f"byte fidelity verified on {nb_fichiers} variant-A files")
    print("type  occ  decoded")
    for t in sorted(stats):
        occ, raw = stats[t]
        etat = "yes" if t in SCHEMAS and raw == 0 else "no (passthrough)"
        print(f"{t:4d} {occ:4d}  {etat}")
        assert t not in SCHEMAS or raw == 0, f"type {t}: {raw}/{occ} as raw"


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("projet", nargs="?",
                         help="decode a variant-A project to JSON; "
                              "with no argument, self-check")
    args = parseur.parse_args(argv)
    if args.projet is None:
        demo()
        return 0
    print(json.dumps(projet_vers_dict(args.projet), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
