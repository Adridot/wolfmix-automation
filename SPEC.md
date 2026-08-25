# Wolfmix `.wpj` — wire format specification

Independent reverse-engineering notes for Wolfmix project files. Not affiliated
with, endorsed by, or sponsored by Wolfmix or Nicolaudie.

This document describes the format **at the byte level**. It is the companion
to a reference implementation (`tools/wpjlib.py`, `tools/wpj_codec.py`) whose
self-checks prove every claim marked *device-confirmed* or *correlated* below
by round-tripping the corpus byte-for-byte.

## Evidence rules

Every statement carries a status. Nothing is asserted without one.

| Status | Meaning |
|---|---|
| `observed` | seen in the bytes, no interpretation |
| `hypothesized` | an interpretation is proposed, not yet tested |
| `correlated` | consistent across ≥ 2 independent files |
| `validated` | confirmed by a single-variable differential experiment |
| `device-confirmed` | the resulting file was accepted by a W1 |

Never invent a name for an unconfirmed enum value. Ambiguity is recorded as a
list of candidates, not resolved by guessing. Absent fields are *absent*, never
reported as `0` or `off`.

Measurement base: W1 Mk1, serial withheld, firmware **2.0.18**, WTOOLS **1.6.3**,
macOS. Corpus hashes in `corpus/SHA256SUMS`.

---

## 1. Three file variants

Three distinct container layouts exist under the same `.wpj` extension. Any
reader must branch on them; a tool that assumes one will silently fail on the
others.

| Variant | Layout | Where it comes from | Corpus |
|---|---|---|---|
| **A** | 20-byte SHA-1 + opaque prefix + TLV container | device dumps and WLINK imports | 5 files |
| **B** | 20-byte SHA-1 + bare protobuf from offset 20 | current WTOOLS projects | 5 files |
| **C** | bare protobuf from offset 0, no digest | older WTOOLS projects | 1 file |

**[correlated]** In variants A and B, bytes `0..19` are the **SHA-1 of
`bytes[20:EOF]`** — exact on 8 of 9 corpus files (the ninth is variant C, which
has no digest). A wrong digest makes Wolfmix tools refuse the file.

**[observed]** The protobuf body of B and C opens with field 1 = varint **7**
(B) or **6** (C). **[hypothesized]** field 1 is a file-format version and the
6 → 7 transition introduced the SHA-1 digest. Alternative candidate: an
unrelated field, coincidence. To settle: find a v6 file carrying a digest, or a
v7 file without one.

Variant A is the format described by `gitfeber/wpj-toolkit`, which documents
W1 **Mk2** files. Variants B and C are documented nowhere else.

### `.wm` / `.wmx` sidecars — **[observed]**

ASCII, four dot-separated segments: `VVV.<32 hex>.<payload hex>.<64 hex>`.
Versions 001, 002, 003 seen. Payload entropy ≈ 7.94 bits/byte → encrypted or
compressed (zlib/deflate ruled out at offsets 0–3). Segment 2 (MD5-sized) is
not the MD5 of the payload or of its hex; segment 4 (SHA-256-sized) likewise.
Candidates: HMAC, hash of the plaintext, derived key. Out of scope here.

---

## 2. Variant A container — **[device-confirmed]**

```
offset  size  content
0x00      20  SHA-1 of bytes[20:EOF]
0x14      44  opaque prefix — preserve verbatim
0x40       4  uint32 LE  root record length
0x44       2  uint16 LE  root record type = 100
0x46     ...  concatenated records, same 6-byte header each
```

**[correlated]** The root length equals `filesize - 0x46` (3/3 files checked).
Records are `uint32 LE length` + `uint16 LE type` + `length` bytes of payload.
Payloads are protobuf-shaped but **not** a published schema: unknown fields must
be preserved verbatim.

Round-tripping this container — parse, re-emit, recompute the SHA-1 — is
byte-identical on the whole variant-A corpus. This is what `tools/wpjlib.py`
proves on every run.

### Opaque prefix, bytes 0x14–0x3F — **[observed]**

- bytes `20..35` = the project UUID, which is also the `wlinkData` filename.
  **[device-confirmed]** these bytes are *not* an import identity key: creating
  a new project without touching them works.
- `cc 21 80 71` appears repeated — **[hypothesized]** W1 serial number.
- **byte at absolute offset 40 = save counter — [device-confirmed]**. It
  increments by exactly one per controller-side save (`5f→60→61→62`, then
  `62→66` across four saves).
- **[observed]** the byte at offset 50 moved once, during a first save only.
  Unattributed.

---

## 3. Record inventory — **[correlated]**

Identical on 5/5 variant-A files except type 160, which is optional (40 records
without it, 41 with).

| Type | Content | Status |
|---|---|---|
| 101 | project metadata (UTF-8 name) | **device-confirmed** |
| 102 | flash FX settings, fixed 16 bytes | **device-confirmed** (§6) |
| 105 | fixture patch entries | correlated |
| 106, 110, 111, 130, 151 | not decoded | observed |
| 115 | 20-slot list, display order | observed (§7) |
| 116 | fixture profiles | correlated |
| 120 | per-channel table | observed |
| 125 | group definitions (named A–H) | correlated |
| 135 | global ColorFX palette | correlated |
| 140 ×8 | 8 pages × 20 static-colour pads | correlated |
| 145 ×8 | 8 pages × 20 glyph buttons | hypothesized |
| 150 ×8 | 8 pages × 20 named pan/tilt positions | correlated |
| 155 | 4 × 128-byte arrays | observed (§8) |
| 160 | macros (optional) | correlated |
| 161 | volatile UI/machine state, not show content | observed |
| 165 | preset container, the largest record (~30 KB) | correlated (§5) |

`gitfeber/wpj-toolkit` documents only types 101, 135 and 165; the remaining
17 types are undocumented anywhere else, and its published inspect model emits
them as `unknown_tlvs` with type and length only.

---

## 4. Type 101 — project name — **[device-confirmed]**

Protobuf field 1, length-delimited, UTF-8. Example: `0a 05 "rig-a"`.

Experiment ACC-01: a file whose only edit was this string was accepted by
WTOOLS 1.6.3 and by the W1 (fw 2.0.18) and stored byte-identically.

---

## 5. Type 165 — presets

### Envelope — **[correlated]**

`field 1` varint = preset count (82 and 80 observed), then repeated `field 5`,
one submessage per preset. Layout: 4 factory pages × 20 (block 1 full presets,
block 2 colour, block 3 move, block 4 beam), then user presets appended.

**[correlated]** Preset identity, agreeing with `wpj-toolkit`: the UI is
1-based, 20 slots per page, `id = (page - 1) * 20 + (slot - 1)`. Id 0 is
omitted from the wire, as protobuf default.

### Preset submessage

| Field | Meaning | Status |
|---|---|---|
| `f19` | preset id | correlated 5/5 |
| `f25` | name, UTF-8 | correlated (82 names) |
| `f1` / `f2` | Beam FX 1 / 2 (FX submessage) | correlated |
| `f5` / `f6` | Color FX 1 / 2 (FX submessage) | correlated |
| `f21` / `f22` | Move FX 1 / 2 (FX submessage, extra `f3`, default 50) | correlated |
| `f28` | position index per group A–H, 8 packed varints | correlated |
| `f17` | dimmer per group A–H, packed, default `[255]×8` | hypothesized |
| `f8` / `f24` | Color FX active / Move FX active flag (packed, `[0]` or `[255]`) | correlated |
| `f31` | static colour: 4 × 5 varints, bitmasks over type-140 pads | hypothesized |
| `f4` | content mask (255 full, 8 colour, 17 beam, 5 move) | hypothesized |
| `f16` | ~13 varints, FX-bank masks per group in complementary pairs | hypothesized |
| `f11` | 500 / 2000 / 4000 — fade time in ms? | hypothesized |
| `f10` | factory library version? | observed |
| `f9`=1, `f15`=1000, `f13`×6, `f18`, `f3`, `f7`, `f14`, `f23`, `f26`, `f27`, `f29`, `f30` | unknown | observed |

`f28` was read from named factory presets: `Floor` = `[0]×8`, `Center` = `[1]×8`,
`Crowd` = `[3]×8`, `Ceiling` = `[4]×8` — the values index into type 150.

**[observed]** `f28`, `f17`, `f8`, `f24` are **packed** varints (wire type 2),
not repeated varints. The two "flags" are packed lists of one element.

### FX submessage — shared by Beam, Color and Move

The wire fields below are ours; the enum *labels* are cross-referenced with
`wpj-toolkit` (MIT), which publishes the enumerations but no wire encoding.
Where both sources cover a value, they agree.

| Field | Meaning | Domain | Status |
|---|---|---|---|
| `f7` | effect type | see below | **device-confirmed** (ACC-04) |
| `f4` | link order | `0–3` None/{Fwd,Back,Out,In}, `10–13` Group/{…}, `20–23` Fixture/{…}; default 10 | correlated |
| `f10` | speed source | `0` Clock (omitted), `1` Microphone, `2` Audio/BPM | correlated |
| `f1` | BPM division | `0`→×8, `1`→×4, `2`→×2, `3`→×1, `4`→½, `5`→¼, `6`→⅛, `7`→1/16; default 3 | correlated |
| `f2` | speed % | observed up to 200, above the 0–100 the toolkit documents | correlated |
| `f8` / `f6` / `f9` | size % / fade % / phase %, defaults 100 / 25 / 50 | hypothesized |
| `f5` | Color FX: 2 varints = 16-bit pad mask (v1 = pads 1–8, v2 = pads 9–16). Move FX: one varint 0–6. Beam FX: see lead L1 | correlated (Color) |

Effect type `f7`, Beam: `0` Sin Wave · `1` Sparkle · `2` Chaser · `3` CanCan ·
`4` Heartbeat · `5` Wolf Rider · `6–8` FX Seq 1–3.
Effect type `f7`, Color: `0` Rainbow 1 · `1` Sparkle 1 · `2` Chaser 1 ·
`3` Light Fever · `4` Rainbow 2 · `5` Sparkle 2 · `6` Rainbow 3 · `7` Chaser 2.

ACC-04 wrote `f7` 3 → 2 on a Color FX and the operator read **Chaser** on the
device, which matches the Color enumeration at index 2 — an independent
confirmation of both the field and the label set.

**[hypothesized]** merging the two sources resolves `f8`/`f6`/`f9`: the toolkit
names `sizePercent` / `fadePercent` / `phasePercent` in 0–100 and our defaults
are 100 / 25 / 50, which reads naturally as size 100 %, fade 25 %, phase 50 %.
Not yet tested by a single-variable save.

---

## 6. Type 102 — flash FX settings — 16 bytes, fixed

```
22 06 <6 bytes>   field 4, always 6 bytes
28 64             field 5  = 100
30 64             field 6  = 100
48 50             field 9  = 80   (75 or 72 in other files)
58 64             field 11 = 100
```

### `field 4` = release mode of the six flash keys — **[device-confirmed]**

One byte per key, in guide order: `0` WOLF · `1` STROBE · `2` BLINDER ·
`3` SPEED · `4` BLACKOUT · `5` SMOKE.

| Value | Release mode |
|---|---|
| 0 | FLASH |
| 1 | TOGGLE |
| 2 | 1 s timer |
| 3 | 5 s timer |
| 4 | 10 s timer |

Experiment FX-01 moved STROBE only, FLASH → TOGGLE: exactly one byte changed,
at index 1. FX-02 then published the prediction `01 00 01 02 03 04` *before*
measuring and set five keys in one save — exact match, five bytes at once.

### `field 9` = STROBE speed — **[device-confirmed]**

0 % on screen writes **1**; 100 % writes **100**. Stored range is **1–100**,
not 0–100 (FX-03 and FX-04).

### `field 7` = SPEED multiplier — mapping **[device-confirmed]**, meaning open

| Setting | `field 7` |
|---|---|
| normal | absent (0) |
| 0.5× | 1 |
| 2× | 2 |
| 4× | 4 |

FX-05 ruled out a list index (which would have written 3 for 4×); FX-06 ruled
out the literal multiplier (0.5× wrote 1, not a fraction). Two readings still
fit: literal multiplier with 0.5 rounded up, or `1 << rank`. They coincide on 2
and 4 by accident. **Discriminator: FREEZE** — the rank reading predicts 16 or
a sentinel, the literal reading predicts 0 or a distinct sentinel.

### `field 8` — **[hypothesized]** excluded-group bitmask

Appeared as `1` exactly when group A was excluded from STROBE. Bit 0 = group A.
Open question: six effects can each exclude groups, so `field 8` is either
STROBE's own mask with five siblings elsewhere, or a shared one. Excluding
A + C (expect 5) then moving the exclusion to another effect separates them.

`field 5`, `field 6` and `field 11` (all 100) remain unattributed. Documented
candidates: blinder fade-out, smoke intensity, smoke fan.

---

## 7. Type 115 — 20-slot list — **[observed]**

20 repeated `field 5` items plus a 20-byte `field 6` on the record itself whose
content is a permutation (`00 01 02 03 0f 10 04 05 06 07 08 09 0a 0b 0c 0d 0e
11 12 13`) — a display order. Each item carries `f2` (16, 32, 48, 99, 109 …),
sometimes `f3`/`f4` = 1, `f5` = 0x3FFFF, and a trailing `f9` = its index.

Across saves, each item's `field 6` **moves as a block** — one value applied
uniformly to all 20 slots, i.e. a global setting stored per slot.
**[hypothesized]** candidates: the STATIC POSITION fade time, or the MOVE FX
sequence STEP control. Both were touched between the two saves.

**Refuted**: `field 6` is *not* the SPEED multiplier (that is 102 `field 7`).

---

## 8. Type 155 — 4 × 128-byte arrays — **[observed]**

`field 1` = 4, then four `field 5` items, each with `f1 = 8`, `f2 ∈ {1,2}`,
`f3 ∈ {2,4}` and `f4` = a **128-byte array**. 4 × 128 = 512 = one DMX universe.
The first array reads `00×9, 01×8, 02×8, 03×8 …` — a fixture index per channel.
**[hypothesized]** the DMX patch map, or the FX sequencer grid (8 groups ×
16 steps × 4 sequences also fits the size).

---

## 9. Writing rules

A writer that does not follow all five will produce files the device rejects,
or worse, silently corrupt a show.

1. **Recompute the SHA-1** over `bytes[20:EOF]` on every save. A stale digest
   makes WTOOLS refuse the file.
2. **Preserve unknown bytes verbatim.** Re-emit any record you did not edit
   exactly as read, and any field you do not understand inside a record you did.
3. **Never overwrite.** Write to a new path (`open(path, "xb")`), always.
4. **Verify by re-reading.** Reload the written file, re-decode, compare against
   what was asked, and diff record-by-record against the source: any record that
   moved outside the intended edit is a bug, not a detail.
5. **Edit, do not synthesize.** Every preset, position or palette entry you
   write must already exist in the donor file. Creating structures from scratch
   is not validated by anything in this document.

### A controller-side save is not byte-preserving — **[device-confirmed]**

Saving on the W1 re-serialises records into the firmware's own canonical form.
Observed on one save: type 115 shrank 329 → 287 bytes as its 20 items each lost
`field 6` and `field 7` and gained a sequential `field 9`. Consequence:
**a round-trip through the device cannot be verified by file hash.** Differential
experiments must compare record by record and expect canonicalisation noise.

### The USB serial link is not error-free — **[device-confirmed]**

Two of four `GET_PROJECT` transfers of a 43 KB project failed in one session:
one produced an unparseable body, one returned the correct length with wrong
bytes *and* a SHA-1 header that did not match its own body. **Never trust a
single download.** Accept a transfer whose SHA-1 header verifies, otherwise
require two identical consecutive transfers.

---

## 10. Open leads

Two of these come from cross-referencing our byte-level decoding with the
`wpj-toolkit` enumerations; neither source has them alone.

- **L1 — Beam FX `feature`.** The toolkit documents a Beam-only `feature` enum
  (`0` Dimmer · `1` Zoom · `2` Iris · `3` Pan · `4` Tilt · `5` Effect) with no
  wire location. We have `f5` carrying a pad mask for Color FX and a bare
  varint 0–6 for Move FX, and unmapped for Beam. **[hypothesized]** Beam `f5`
  is `feature`. One single-variable save (change a beam FX from Dimmer to Zoom)
  settles it.
- **L2 — group-mask asymmetry.** The toolkit reports `colorGroupMask` over
  A–H but `beamGroupMask` over **A–D only**. Our `f16` hypothesis is
  "FX-bank masks per group in complementary pairs". The A–D restriction is a
  strong constraint on which halves of `f16` are which.
- **L3 — static colour `f31`.** 4 repetitions × 5 varints, bitmasks over type
  140 pads (`Deep Red` = mask 32 = pad 6). Are the 4 repetitions groups A–D?
  Experiment: one pad, one group.
- **L4 — MIDI mapping record.** The W1 accepts MIDI (preset select by note,
  group/master dimmers by CC, MIDI clock at 24 PPQN) and the map is learned
  per project on `WM_MODE_MAPPING = 43`. It must therefore live in the file.
  Not yet located. This is the gateway to live control.
- **L5 — fixture patch.** Types 105 / 115 / 116 / 120 / 155 all touch the
  patch; none is fully decoded. `wpj-toolkit` reports `fixtures.status:
  unsupported`, so no external source covers it either.
- **L6 — variants B and C.** Only the top level is mapped: field 2 = project
  name, field 3 ×100 = presets (submessage: `f1` name, `f2` = 1000, `f4` =
  135 opaque bytes), field 15 ×2048 and field 5 ×80 unknown.

---

## References

See `PROVENANCE.md` for sources, licences, and what may be reused from where.
