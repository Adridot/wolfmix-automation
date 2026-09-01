#!/usr/bin/env python3
"""Byte coverage of a variant-A `.wpj`: how much of the file a name explains.

Four buckets, and their sum is the file — that assertion is the whole point:

  read     a field the codec schema NAMES (its tag, its length prefix and its
           payload), plus the container bytes §2/§9 identifies
  inert    a field with no name that carries ONE value in the whole corpus,
           declared in `INERT_FIELDS` with that value
  partial  a field present inside a schema'd record that no schema names and
           that is not inert — it varies, and nothing reads it
  unknown  the payload of a record with no schema at all, and any record whose
           protobuf does not parse

`read` and `inert` are printed **separately and never added**, because they are
not the same claim. `read` says what a field means. `inert` says only that the
field never says anything different — a statement about the *corpus*, not the
field, and exactly the statement `constant_1` would smuggle in as a name. The
difference is that this one is checked: a declared value is verified on every
file, and a second value raises `InertBroken` instead of quietly widening the
bucket. `116.profiles.f6` (1 and, once, 3) and `102.f11` (0 and 100) are not in
the table for that reason — one sample is all it takes to turn a "constant"
into an "almost constant", and this is where that gets caught.

So "100 %" here means `read + inert = 100`, `partial = 0`, `unknown = 0`, and
it means less than it sounds like. What the read number does NOT say: it counts
bytes a name covers, not bytes a name has been *proved* to cover. Cross it with
`tools/wpj_evidence.py` before believing it — a named field with no ledger
entry is worse than an unknown one.

Rules worth knowing before reading a percentage:

- A named sub-message whose schema names nothing (`120.channels`) still has a
  read tag and length: an entry of `2a 00` is 2 bytes of pure envelope and 0
  bytes of content, so it counts read and carries no unknown content. It is
  structurally empty, not undecoded.
- A record whose codec round trip fails is unknown in full, exactly as
  `wpj_codec.decode` reports it: `{"raw": …}`.

Usage:
  wpj_coverage.py project.wpj      per-field coverage of one file
  wpj_coverage.py --corpus         the corpus aggregate, biggest gaps first
  wpj_coverage.py                  self-check
"""
import sys

import wpj_codec
import wpj_wire
import wpjlib

READ, INERT, PARTIAL, UNKNOWN = "read", "inert", "partial", "unknown"


class InertBroken(Exception):
    """A field declared inert carries a second value. NOT a ValueError: the
    corpus walk catches those to skip variants B and C, and this must not be
    skipped — it is the whole point of declaring the value."""


# §9: what the 44 prefix bytes are. Offsets are **absolute in the file**, as
# §9's own table gives them; bytes 0-19 are the SHA-1 and belong to the
# container. A span the section reports as a constant with no meaning is
# `inert` — reproducible is not the same as understood, and the value is
# checked on every file rather than taken from the section.
_PREFIX = [
    (20, 16, READ, "prefix.project_uuid"),
    (36, 4, INERT, "prefix.magic"),
    (40, 8, READ, "prefix.version"),
    (48, 2, INERT, "prefix.const_48_49"),
    (50, 1, READ, "prefix.schema_version"),
    (51, 1, INERT, "prefix.const_51"),
    (52, 12, INERT, "prefix.const_52_63"),
]


# --- what licenses a name ----------------------------------------------------
#
# Every `read` path must appear here with a status and a piece of evidence: a
# ledger id from `research/evidence.md`, or a `SPEC.md` section. The self-check
# refuses a name that has neither, which is the point — promoting a field into
# `wpj_codec.SCHEMAS` on a hunch then fails `make check` instead of quietly
# raising the read percentage. A named field with no proof is worse than an
# unknown one: it lies without ever being wrong out loud.
#
# Keyed by (record type as a string, leaf name). One entry serves every path
# that ends in that leaf under that record — `color_fx1.speed` and
# `move_fx2.speed` are the same reading, measured once.

DEVICE, VALIDATED, CORRELATED, OBSERVED, HYPOTHESIZED = (
    "device-confirmed", "validated", "correlated", "observed", "hypothesized")

CONTAINER_PROOF = {
    "container.sha1": (DEVICE, "ACC-01"),
    "container.root_header": (DEVICE, "§2"),
    "container.record_header": (DEVICE, "§2"),
    "prefix.project_uuid": (DEVICE, "ACC-01"),
    "prefix.version": (CORRELATED, "§9"),
    "prefix.schema_version": (CORRELATED, "§9"),
}

PROOF = {
    # Field 1 = the item count, on the 15 record types that carry one. The
    # identity holds with no exception on the corpus and refutes nothing else,
    # so it is `correlated`, not measured on a device.
    **{(str(t), "entry_count"): (CORRELATED, "§3")
       for t in (105, 106, 110, 111, 115, 116, 120, 125, 130, 135, 140, 150,
                 151, 155, 160)},
    # The group index of the three ×8 palette families, absent for group A —
    # settled by three independent device readings (§3.1).
    **{(str(t), "group"): (DEVICE, "§3.1") for t in (140, 145, 150)},

    ("101", "name"): (DEVICE, "ACC-01"),

    # 102 — every field but the inert `f11`, each written by the device in a
    # single-variable save and read back off the Settings screen (§6).
    ("102", "blackout_excluded_groups"): (DEVICE, "FX-09"),
    ("102", "blinder_fade_out"): (DEVICE, "FX-08"),
    ("102", "blinder_excluded_groups"): (DEVICE, "FX-08"),
    ("102", "release_modes"): (DEVICE, "FX-02"),
    ("102", "smoke_fan_speed"): (DEVICE, "FX-07"),
    ("102", "smoke_intensity"): (DEVICE, "FX-07"),
    ("102", "speed_multiplier"): (DEVICE, "FX-06"),
    ("102", "strobe_excluded_groups"): (DEVICE, "FX-09"),
    ("102", "strobe_speed"): (DEVICE, "§6"),
    ("102", "wolf_excluded_groups"): (DEVICE, "FX-10"),

    ("105", "patch"): (CORRELATED, "§7"),
    ("105", "library_id"): (CORRELATED, "§7"),
    ("105", "offset_106"): (CORRELATED, "§7"),
    ("105", "entry_count_106"): (CORRELATED, "§7"),
    ("105", "fixture"): (CORRELATED, "§7"),
    ("105", "group"): (CORRELATED, "§7.4"),

    ("106", "channel_roles"): (CORRELATED, "§7.5"),
    ("106", "dmx_channel"): (DEVICE, "COV-29"),
    ("106", "role"): (CORRELATED, "§7.5"),
    ("106", "range_start"): (CORRELATED, "§7.5"),
    ("106", "range_end"): (CORRELATED, "§7.5"),
    ("106", "limit_low"): (DEVICE, "POS-01"),
    ("106", "limit_high"): (DEVICE, "POS-01"),

    ("110", "channels"): (CORRELATED, "§7.6"),
    ("110", "range_count"): (CORRELATED, "§3.4"),
    ("110", "offset_111"): (CORRELATED, "§7"),
    ("110", "feature"): (DEVICE, "COV-25"),
    ("110", "principal_channel"): (CORRELATED, "§7.6"),

    ("111", "ranges"): (CORRELATED, "§7.6"),
    ("111", "start"): (CORRELATED, "§7.6"),
    ("111", "end"): (CORRELATED, "§7.6"),
    ("111", "function"): (CORRELATED, "§7.6"),
    ("111", "gobo_id"): (DEVICE, "SORT-01"),

    ("115", "fixtures"): (CORRELATED, "§7"),
    ("115", "dmx_address"): (DEVICE, "§3.4"),
    ("115", "profile"): (CORRELATED, "§7"),
    ("115", "group"): (CORRELATED, "§7.4"),
    ("115", "display_order"): (DEVICE, "COV-47"),
    ("115", "slot_id"): (DEVICE, "COV-46"),

    ("116", "profiles"): (CORRELATED, "§7"),
    ("116", "channel_count"): (CORRELATED, "§7"),
    ("116", "offset_110"): (CORRELATED, "§7"),
    ("116", "name"): (CORRELATED, "§7"),
    ("116", "uuid"): (CORRELATED, "PROFILE-05"),
    ("116", "timestamp"): (CORRELATED, "§7"),
    ("116", "channel_names"): (DEVICE, "COV-43"),

    ("120", "channels"): (CORRELATED, "§7"),
    ("120", "value"): (DEVICE, "COV-16"),
    ("120", "dmx_channel"): (DEVICE, "COV-50"),
    ("120", "occupancy"): (VALIDATED, "COV-55"),

    ("125", "groups"): (CORRELATED, "§7.4"),
    ("125", "name"): (DEVICE, "COV-08"),
    # The split: 6 of the 7 bytes are the profile mask, and byte 6 is not.
    # `mask` names the field COV-26 measured; `f4b6` stays neutral and lands
    # in `partial`, which is what the split is for.
    ("125", "mask"): (DEVICE, "COV-26"),
    ("125", "profile_mask"): (DEVICE, "COV-26"),

    ("130", "mappings"): (DEVICE, "MAP-02"),
    ("130", "instance"): (DEVICE, "MAP-04"),
    ("130", "function"): (DEVICE, "MAP-04"),
    ("130", "channel_high_byte"): (DEVICE, "MAP-04"),
    ("130", "channel_low_byte"): (DEVICE, "MAP-04"),

    # The seven components and their field order: the picker's RGB+ view prints
    # the raw 0-255 channel values and names all seven, in field order (§3.3).
    # That settles record 140; record 135's own meaning comes from an external
    # source, so it stays correlated. `read` is a claim about reading — PAL-01
    # confirms the *write* direction, and for `red` alone.
    ("135", "pads"): (CORRELATED, "§3.3"),
    ("140", "pads"): (DEVICE, "PAL-01"),
    **{("140", c): (DEVICE, "§3.3") for c in
       ("red", "green", "blue", "white", "amber", "lime", "uv")},
    **{("135", c): (CORRELATED, "§3.3") for c in
       ("red", "green", "blue", "white", "amber", "lime", "uv")},
    ("145", "gobos"): (DEVICE, "§3.4"),
    ("150", "positions"): (DEVICE, "§3.2"),
    ("151", "detached"): (DEVICE, "POS-03"),
    ("155", "sequences"): (DEVICE, "§8"),
    ("155", "groups_per_step"): (DEVICE, "§8"),
    ("155", "engine"): (VALIDATED, "FX6-05"),
    ("155", "step_count"): (DEVICE, "§8"),
    ("155", "steps"): (DEVICE, "§8"),

    ("160", "macros"): (CORRELATED, "§3"),
    ("165", "presets"): (CORRELATED, "§5"),

    # The weakest name in this table, and deliberately so: `items` says that
    # field 5 is the record's repeated entry list and nothing else — the
    # container convention 15 record types already follow (§3), counted three
    # times per record on the whole corpus (COV-06). Everything inside keeps a
    # neutral key. Q8 is untouched by it.
    ("161", "items"): (OBSERVED, "COV-06"),

    ("145", "glyph"): (DEVICE, "§3.4"),
    ("145", "gobo_id"): (DEVICE, "§3.4"),
    ("145", "name"): (DEVICE, "RENAME-01"),

    ("150", "name"): (DEVICE, "§3.2"),
    ("150", "entry_count_151"): (DEVICE, "POS-03"),
    ("150", "offset_151"): (DEVICE, "POS-03"),
    ("150", "fan"): (DEVICE, "POS-02"),
    ("150", "focus_offset"): (DEVICE, "§3.2"),
    ("150", "pan"): (DEVICE, "§3.2"),
    ("150", "tilt"): (DEVICE, "POS-01"),
    ("150", "cross"): (DEVICE, "COV-08"),

    ("151", "fixture"): (DEVICE, "POS-06"),
    ("151", "focus_offset"): (DEVICE, "POS-04"),
    ("151", "pan_offset"): (DEVICE, "POS-04"),
    ("151", "tilt_offset"): (DEVICE, "POS-04"),

    ("160", "name"): (CORRELATED, "§3"),
    ("160", "button"): (DEVICE, "COV-19"),
    ("160", "value_masks"): (CORRELATED, "COV-20"),
    ("160", "values"): (DEVICE, "COV-19"),

    ("165", "id"): (DEVICE, "PRESET-07"),
    ("165", "name"): (DEVICE, "PRESET-05"),
    ("165", "content_mask"): (DEVICE, "F4-02"),
    ("165", "engine_masks"): (DEVICE, "§5.7"),
    ("165", "live_edit_mask"): (CORRELATED, "§5.5"),
    ("165", "fade_ms"): (DEVICE, "§5.3"),
    ("165", "hold_ms"): (CORRELATED, "§5.3"),
    ("165", "engine_permissions"): (CORRELATED, "§5.4"),
    ("165", "dimmers"): (DEVICE, "GEN-02"),
    ("165", "positions"): (CORRELATED, "§5.1"),
    ("165", "gobos"): (DEVICE, "F29-01"),
    ("165", "color_pattern"): (DEVICE, "F30-04"),
    ("165", "static_color"): (DEVICE, "GEN-01"),
    ("165", "gobo_rotate"): (DEVICE, "GOBO-02"),
    ("165", "gobo_focus"): (DEVICE, "GOBO-02"),
    ("165", "gobo_prism"): (DEVICE, "GOBO-02"),
    ("165", "gobo_zoom"): (DEVICE, "GOBO-02"),
    ("165", "gobo_iris"): (DEVICE, "GOBO-02"),
    ("165", "color_fx_active"): (CORRELATED, "§5.4"),
    ("165", "move_fx_active"): (CORRELATED, "§5.4"),
    ("165", "position_fade_ms"): (DEVICE, "COV-10"),
    ("165", "page_beam_fx"): (VALIDATED, "F7-04"),
    ("165", "page_color_fx"): (VALIDATED, "F7-01"),
    ("165", "page_move_fx"): (VALIDATED, "F7-03"),

    # the FX sub-message, shared by the three engines
    ("165", "beam_fx1"): (CORRELATED, "§5"),
    ("165", "beam_fx2"): (CORRELATED, "§5"),
    ("165", "color_fx1"): (CORRELATED, "§5"),
    ("165", "color_fx2"): (CORRELATED, "§5"),
    ("165", "move_fx1"): (CORRELATED, "§5"),
    ("165", "move_fx2"): (CORRELATED, "§5"),
    ("165", "effect"): (DEVICE, "ACC-04"),
    ("165", "link_order"): (CORRELATED, "§5"),
    ("165", "speed_source"): (CORRELATED, "§5"),
    ("165", "bpm_division"): (CORRELATED, "§5"),
    ("165", "fade"): (VALIDATED, "FX6-02"),
    ("165", "phase"): (VALIDATED, "FX6-02"),
    ("165", "size"): (VALIDATED, "FX6-02"),
    ("165", "speed"): (VALIDATED, "FX6-02"),
    ("165", "feature"): (VALIDATED, "FX6-03"),
    ("165", "fan"): (VALIDATED, "FX6-04"),
    ("165", "color_mask"): (CORRELATED, "§5"),
    ("165", "effect_position"): (CORRELATED, "§5"),
}


# --- what licenses `inert` ---------------------------------------------------
#
# path -> (the only value ever seen, the occurrences counted the day it was
# declared). Keyed by the **full path**, not by `_leaf` as PROOF is, and the
# difference is deliberate: a reading is shared by every path that ends in the
# same leaf, a constant is a property of one path and one only. `120.f4` and
# `120.channels.f4` collide under `_leaf` and are not the same field — one
# varies, the other does not.
#
# The VALUE is asserted on every file. The count is historical, like SPEC's
# "45/45" figures: it says what was checked when the line was written, never
# what your corpus holds, and a small one is a warning in plain sight
# (`115.fixtures.f1` rests on five occurrences).
#
# Varints are the integer, length-delimited and fixed fields the payload hex.
# What is NOT here, and why the table has a point: `116.profiles.f6` is 1 on 90
# occurrences and **3** on one, and `102.f11` is 0 and 100. Both stay `partial`.
INERT_FIELDS = {
    "prefix.magic": ("152b10c0", 90),
    "prefix.const_48_49": ("01f9", 90),
    "prefix.const_51": ("00", 90),
    "prefix.const_52_63": ("02bee81ca26ccb546dc7b6ec", 90),

    "165.presets.f13": ("", 26394),      # a zero-length packed array, six per
                                         # preset: 1.9 % of the corpus in pure
                                         # protobuf framing
    "120.channels.f4": (1, 9352),
    "165.presets.f26": ("00", 4399),     # a one-element array holding a zero
    "165.presets.f9": (1, 4399),
    "115.fixtures.f5": (65535, 1633),    # a sentinel, on the face of it
    "130.mappings.f8": (1, 830),
    "130.mappings.f7": (1, 746),
    "110.channels.f1": (1, 680),
    "160.macros.f2": (1, 564),
    "116.profiles.f1": (1, 272),
    "125.groups.f1": (1, 265),
    "116.profiles.f4": (1, 263),
    "125.groups.f2": (1, 256),
    "116.profiles.f7": (1, 171),
    "125.groups.f7": (1, 165),
    "116.profiles.f5": (1, 87),
    "125.groups.f5": (1, 81),
    "160.macros.f3": (1, 78),
    "116.profiles.f13": (1, 18),
    "115.fixtures.f1": (1, 5),

    # Record 161. Its own `f1` is **9** against 3 items, so it is not the count
    # the other 15 record types put there (COV-06) — and it has never been
    # anything else. `items.f2` is present on 69 of 270 items and 1 on all of
    # them; `items.f1` (21/15/19 by position) and `items.f4` (1 or 2) vary and
    # stay `partial`.
    "161.f1": (9, 90),
    "161.items.f2": (1, 69),
}


def _check_inert(path, value):
    """INERT if the path is declared and carries its value, PARTIAL if it is
    not declared. A declared path carrying anything else stops the run."""
    declared = INERT_FIELDS.get(path)
    if declared is None:
        return PARTIAL
    if value != declared[0]:
        raise InertBroken(
            f"{path} is declared inert at {declared[0]!r} and carries "
            f"{value!r}: it is not inert, remove it from INERT_FIELDS")
    return INERT


def _leaf(path):
    """The PROOF key a coverage path answers to."""
    if path.startswith(("container.", "prefix.")):
        return path
    parts = path.split(".")
    return (parts[0], parts[-1])


def unproven(acc):
    """[(path, bytes)] for every `read` path with no entry in PROOF."""
    out = []
    for (bucket, path), n in acc.items():
        if bucket != READ:
            continue
        key = _leaf(path)
        if key not in (CONTAINER_PROOF if isinstance(key, str) else PROOF):
            out.append((path, n))
    return sorted(out, key=lambda x: -x[1])


def proof_of(path):
    key = _leaf(path)
    return (CONTAINER_PROOF if isinstance(key, str) else PROOF).get(key)


def by_status(acc):
    """{status: bytes} over the `read` bucket."""
    out = {}
    for (bucket, path), n in acc.items():
        if bucket != READ:
            continue
        found = proof_of(path)
        status = found[0] if found else "NAMED WITHOUT PROOF"
        out[status] = out.get(status, 0) + n
    return out


def dangling_evidence():
    """Evidence citations that resolve to nothing, or to a retracted finding."""
    import wpj_evidence
    live, taken_back = set(), set()
    for ids, _, statut, _ in wpj_evidence.entrees():
        for one in ids:
            (taken_back if wpj_evidence.reprise(statut) else live).add(one)
    sections = wpj_evidence.sections()
    bad = []
    for key, (_, cite) in list(PROOF.items()) + list(CONTAINER_PROOF.items()):
        if cite.startswith("§"):
            if cite[1:] not in sections:
                bad.append((key, cite, "no such SPEC section"))
        elif cite in taken_back and cite not in live:
            bad.append((key, cite, "the ledger takes this finding back"))
        elif cite not in live:
            bad.append((key, cite, "no such finding in the ledger"))
    return bad


def _tally(acc, bucket, path, n):
    if n:
        acc[(bucket, path)] = acc.get((bucket, path), 0) + n


def _walk_split(chunk, parts, path, acc):
    """A split field's payload, part by part.

    The one place where PROOF and not the schema decides `read`: a part the
    schema names and the ledger does not is counted `partial`. That
    undercounts rather than lies, which is the direction to fail in — and it
    is what lets one field carry a measured half and an unread one without
    either borrowing the other's status.

    A `varint` part is measured, not assumed: its width is what it encodes to,
    which is the whole reason `125.f4`'s tail is one now and was two the day
    its value passed 128 (COV-51)."""
    spans, i = [], 0
    for n, part in parts:
        if n == "varint":
            try:
                _, apres = wpj_wire.read_varint(chunk, i)
            except wpj_wire.WireError:
                i = -1
                break
            spans.append((part, apres - i)); i = apres
        else:
            spans.append((part, n)); i += n
    if i != len(chunk):
        _tally(acc, PARTIAL, path + ".<unsplit>", len(chunk))
        return
    for part, n in spans:
        sub = f"{path}.{part}"
        _tally(acc, READ if proof_of(sub) else PARTIAL, sub, n)


def _walk(buf, schema, path, acc):
    """Attribute every byte of a protobuf message. Raises WireError if it is
    not one — the caller then charges the whole payload to `unknown`."""
    i = 0
    while i < len(buf):
        start = i
        tag, i = wpj_wire.read_varint(buf, i)
        f, wt = tag >> 3, tag & 7
        if f == 0:
            raise wpj_wire.WireError("field 0")
        name, kind = schema.get(f, (f"f{f}", None))
        # A schema entry may carry a wire kind under a NEUTRAL key, to type
        # bytes it does not read (`161.items.f3`). A name is what licenses
        # `read`, so `fN` never does, whether it came from the schema or from
        # this field being absent from it.
        named = f in schema and not (name[:1] == "f" and name[1:].isdigit())
        sub = f"{path}.{name}"
        value = None                     # only read for the inert check below
        if wt == 0:
            value, i = wpj_wire.read_varint(buf, i)
        elif wt == 2:
            ln, i = wpj_wire.read_varint(buf, i)
            if i + ln > len(buf):
                raise wpj_wire.WireError("length past the end")
            if isinstance(kind, dict) or (isinstance(kind, tuple)
                                          and kind[0] == "split"):
                # the tag and length belong to the field itself; its content is
                # attributed piece by piece below
                _tally(acc, READ, sub, i - start)
                if isinstance(kind, dict):
                    _walk(buf[i:i + ln], kind, sub, acc)
                else:
                    _walk_split(buf[i:i + ln], kind[1], sub, acc)
                i += ln
                continue
            value = buf[i:i + ln].hex()
            i += ln
        elif wt == 5:
            value = buf[i:i + 4].hex(); i += 4
        elif wt == 1:
            value = buf[i:i + 8].hex(); i += 8
        else:
            raise wpj_wire.WireError(f"wire type {wt}")
        if i > len(buf):
            raise wpj_wire.WireError("field past the end")
        _tally(acc, READ if named else _check_inert(sub, value), sub, i - start)


def coverage(data, source="<bytes>"):
    """{(bucket, path): bytes} for one variant-A file. Sums to len(data)."""
    w = wpjlib.Wpj.from_bytes(data, source)
    acc = {}
    _tally(acc, READ, "container.sha1", 20)
    for off, n, bucket, name in _PREFIX:
        if bucket is INERT:
            bucket = _check_inert(name, data[off:off + n].hex())
        _tally(acc, bucket, name, n)
    _tally(acc, READ, "container.root_header", wpj_wire.ROOT_HEADER)
    for typ, payload in w.records:
        _tally(acc, READ, "container.record_header", wpj_wire.ROOT_HEADER)
        path = f"{typ}"
        if typ not in wpj_codec.SCHEMAS:
            _tally(acc, UNKNOWN, path + ".<no schema>", len(payload))
            continue
        before = dict(acc)
        try:
            _walk(payload, wpj_codec.SCHEMAS[typ], path, acc)
        except wpj_wire.WireError:
            acc.clear()
            acc.update(before)
            _tally(acc, UNKNOWN, path + ".<unparsed>", len(payload))
    total = sum(acc.values())
    assert total == len(data), f"{source}: {total} attributed, {len(data)} bytes"
    return acc


def totals(acc):
    out = {READ: 0, INERT: 0, PARTIAL: 0, UNKNOWN: 0}
    for (bucket, _), n in acc.items():
        out[bucket] += n
    return out


def report(acc, title, top=25):
    t = totals(acc)
    total = sum(t.values())
    print(f"{title}: {total} bytes")
    for bucket in (READ, INERT, PARTIAL, UNKNOWN):
        print(f"  {bucket:<8} {t[bucket]:>9}  {100.0 * t[bucket] / total:5.1f} %")
    for status, n in sorted(by_status(acc).items(), key=lambda x: -x[1]):
        print(f"    of which {100.0 * n / total:5.1f} %  read, {status}")
    inert = sorted(((n, p) for (b, p), n in acc.items() if b is INERT),
                   reverse=True)
    if inert:
        print("  inert — one value, no name, checked on every file:")
        for n, path in inert:
            value, occ = INERT_FIELDS[path]
            print(f"    {n:>9}  {100.0 * n / total:5.2f} %  {path:<22} "
                  f"= {value!r}  ({occ} occurrences when declared)")
    gaps = sorted(((n, b, p) for (b, p), n in acc.items()
                   if b in (PARTIAL, UNKNOWN)), reverse=True)
    if gaps:
        print(f"  neither read nor inert, by weight (top {top}):")
        for n, bucket, path in gaps[:top]:
            print(f"    {n:>9}  {100.0 * n / total:5.2f} %  {bucket:<7} {path}")


def _corpus_accumulated():
    acc, files = {}, 0
    for path in wpjlib.corpus_files():
        try:
            data = open(path, "rb").read()
            one = coverage(data, path)
        except (ValueError, OSError):
            continue                     # variants B/C: another container
        files += 1
        for key, n in one.items():
            acc[key] = acc.get(key, 0) + n
    return acc, files


def demo():
    acc, files = _corpus_accumulated()
    if not files:
        return wpjlib.pas_de_corpus("wpj_coverage")
    orphans = unproven(acc)
    assert not orphans, ("named with no entry in PROOF: "
                         + ", ".join(f"{p} ({n} bytes)" for p, n in orphans))
    bad = dangling_evidence()
    assert not bad, "evidence that resolves to nothing: " + str(bad)
    named = {_leaf(p) for (b, p), _ in acc.items() if b is READ}
    both = [p for p in INERT_FIELDS if _leaf(p) in named]
    assert not both, "declared inert AND named: " + ", ".join(both)
    unseen = sorted(set(INERT_FIELDS) - {p for (b, p), _ in acc.items()
                                         if b is INERT})
    t = totals(acc)
    total = sum(t.values())
    statuses = by_status(acc)
    print(f"coverage: {100.0 * t[READ] / total:.1f} % read, "
          f"{100.0 * t[INERT] / total:.1f} % inert, "
          f"{100.0 * t[PARTIAL] / total:.1f} % partial, "
          f"{100.0 * t[UNKNOWN] / total:.1f} % unknown "
          f"on {files} variant-A files ({total} bytes)")
    print("  read and inert are not added: the first says what a field means, "
          "the second only that it never varies")
    if unseen:
        print(f"  {len(unseen)} declared inert and absent from this corpus, "
              f"so unverified here: " + ", ".join(unseen))
    print("  read, by the status of what names it: "
          + ", ".join(f"{100.0 * n / total:.1f} % {s}"
                      for s, n in sorted(statuses.items(), key=lambda x: -x[1])))


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("project", nargs="?", help="a variant-A .wpj")
    p.add_argument("--corpus", action="store_true",
                   help="aggregate over the whole local corpus")
    p.add_argument("--top", type=int, default=25)
    args = p.parse_args(argv)
    if args.corpus:
        acc, files = _corpus_accumulated()
        if not files:
            wpjlib.pas_de_corpus("wpj_coverage")
            return 0
        report(acc, f"corpus, {files} variant-A files", args.top)
    elif args.project:
        report(coverage(open(args.project, "rb").read(), args.project),
               args.project, args.top)
    else:
        demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
