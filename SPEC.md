# Wolfmix `.wpj` — wire format specification

Independent reverse-engineering notes for Wolfmix project files. Not affiliated
with, endorsed by, or sponsored by Wolfmix or Nicolaudie.

This document describes the format **at the byte level**. It is the companion to
a reference implementation (`tools/wpjlib.py`, `tools/wpj_codec.py`) whose
self-checks prove every structural claim below by round-tripping the corpus
byte-for-byte. Run them with `make check`.

## Evidence rules

Every statement carries a status. Nothing is asserted without one.

| Status | Meaning |
|---|---|
| `observed` | seen in the bytes, no interpretation |
| `hypothesized` | an interpretation is proposed, not yet tested |
| `correlated` | consistent across independent files |
| `validated` | confirmed by a single-variable differential experiment |
| `device-confirmed` | the resulting file was accepted by a W1 |

Never invent a name for an unconfirmed enum value. Ambiguity is recorded as a
list of candidates, not resolved by guessing. Absent fields are *absent*, never
reported as `0` or `off`.

Measurement base: W1 Mk1, serial withheld, firmware **2.0.18**, WTOOLS **1.6.3**,
macOS. Corpus hashes in `corpus/SHA256SUMS`.

**On "18/18 files".** The corpus holds 19 variant-A files, but only **4 are
independent rigs** (*rig-a* 10 fixtures, *rig-b* 15, *rig-c* 20,
*rig-c-bug* 22 = a re-patched *rig-c*). The rest are derived: 7 written
by our own writer from *rig-a*, 7 controller saves of one copy of
*rig-c*. An identity holding 18/18 is strong enough to **kill** a
hypothesis; it is not by itself enough to call anything device-confirmed.

---

## 1. Three file variants

Three distinct container layouts share the `.wpj` extension. A reader must
branch on them; one that assumes a single layout will fail silently on the
others.

| Variant | Layout | Origin | Corpus |
|---|---|---|---|
| **A** | 20-byte SHA-1 + opaque prefix + TLV container | device dumps, WLINK imports | 19 files |
| **B** | 20-byte SHA-1 + bare protobuf from offset 20 | current WTOOLS projects | 5 files |
| **C** | bare protobuf from offset 0, no digest | older WTOOLS projects | 1 file |

**[correlated]** In A and B, bytes `0..19` are the **SHA-1 of `bytes[20:EOF]`** —
exact on 8 of 9 files at the original census (the ninth is variant C, which has
no digest). A wrong digest makes Wolfmix tools refuse the file.

**[observed]** The protobuf body of B and C opens with field 1 = varint **7** (B)
or **6** (C). **[hypothesized]** field 1 is a file-format version and the 6 → 7
transition introduced the digest. Alternative candidate: an unrelated field,
coincidence. To settle: find a v6 file carrying a digest, or a v7 without one.

**[observed]** B and C contain **no TLV records at all** — their top-level
protobuf (`field 2` = project name, `field 3` ×100 = presets, `field 15` ×2048,
`field 5` ×80) is a different serialisation needing its own mapping. They cannot
help decode variant A.

Variant A is the format `gitfeber/wpj-toolkit` documents, from W1 **Mk2** files.
Variants B and C are documented nowhere else.

### `.wm` / `.wmx` sidecars — **[observed]**

ASCII, four dot-separated segments: `VVV.<32 hex>.<payload hex>.<64 hex>`.
Versions 001, 002, 003 seen. Payload entropy ≈ 7.94 bits/byte → encrypted or
compressed (zlib/deflate ruled out at offsets 0–3). Segment 2 (MD5-sized) is not
the MD5 of the payload or of its hex; segment 4 (SHA-256-sized) likewise.
Candidates: HMAC, hash of the plaintext, derived key. Out of scope here.

---

## 2. Variant A container — **[device-confirmed]**

```
offset  size  content
0x00      20  SHA-1 of bytes[20:EOF]
0x14      44  opaque prefix — see §9
0x40       4  uint32 LE  root record length
0x44       2  uint16 LE  root record type = 100
0x46     ...  concatenated records, same 6-byte header each
```

**[correlated]** Root length = `filesize - 0x46`. Records are `uint32 LE length`
+ `uint16 LE type` + `length` payload bytes. Payloads are protobuf-shaped but
**not** a published schema: unknown fields must be preserved verbatim.

Nearly every record shares one envelope: `field 1 varint = item count`, then
`field 5` repeated once per item. Exceptions are noted per type.

Round-tripping this container — parse, re-emit, recompute the SHA-1 — is
byte-identical on the whole variant-A corpus. `tools/wpjlib.py` proves it on
every run.

---

## 3. Record inventory — **[correlated 18/18]**

| Type | Size (bytes) | Items | Identification | Status |
|---|---|---|---|---|
| 101 | 12–20 | — | project name (`f1` UTF-8) | **device-confirmed** (§4) |
| 102 | 16–22 | — | flash-FX settings, 6 keys | **device-confirmed** (§6) |
| 105 | 114–351 | 10–27 | **DMX patch**, one entry per patched block | correlated (§7) |
| 106 | 600–2614 | 50–201 | one entry per patched DMX channel | correlated (exact count identity) |
| 110 | 210–775 | 22–80 | flattened channel table of all profiles | correlated |
| 111 | 347–1526 | 45–201 | flattened range/capability table, indexed by 110 | correlated |
| 115 | 116–409 | 10–22 | **fixture instances** | correlated (§7) |
| 116 | 162–334 | 3–7 | **fixture profile catalogue** | correlated |
| 120 | 532–1199 | 86–258 | flat per-fixture-channel value table | correlated |
| 125 | 111–137 | **9** | **9 fixture categories**: name + profile bitmask | correlated (§7.2) |
| 130 | **102** | **9** | byte-identical in 18/18 files | observed — no project data |
| 135 | 140–145 | **16** | the 16 ColorFX palette pads (RGBWALU) | correlated |
| 140 ×8 | 182–189 | **20** each | 8 pages × 20 static-colour pads, `f2` = page 0…7 | correlated |
| 145 ×8 | 40–159 | **20** each | 8 pages × 20 glyph buttons, `f2` = page 0…7 | hypothesized |
| 150 ×8 | 483–491 | **20** each | 8 pages × 20 pan/tilt positions, `f2` = page 0…7 | correlated |
| 151 | 0 or 64 | 0 or **4** | 4 × three 16-bit values centred on 32767 | observed |
| 155 | 562–563 | **4** | **4 FX sequences**, 8 × 16 grid + step count | correlated (§8) |
| 160 | 393–542, **optional** | 8–11 | named macros | correlated |
| 161 | 599–604 | **3** | 3 × ~190-byte blob, volatile | observed |
| 165 | 26219–29831 | 80–82 | preset container | correlated (§5) |

160 is the only optional record: 40 records without it, 41 with.

`gitfeber/wpj-toolkit` documents only types 101, 135 and 165; its published
inspect model emits the other 17 as `unknown_tlvs`, type and length only.

### 3.1 The `×8` types are pages, not groups — **refuted, 18/18**

`140 ×8`, `145 ×8` and `150 ×8` are **not** the 8 fixture groups A–H. Each of
the 8 records carries exactly 20 items whatever the rig, and a top-level
`field 2` = an explicit page number 0…7 (absent for page 0). A group-indexed
record would vary in size with how many fixtures each group holds; these do not.

Stronger: `140[4..7]`, `145[1..7]` and `150[1..7]` are **byte-identical across
all 18 files** — 4 independent rigs, two different writers. Untouched factory
pages. Only page 0 (and pages 1–3 of 140) ever differ.

---

## 4. Type 101 — project name — **[device-confirmed]**

Protobuf field 1, length-delimited, UTF-8. Example: `0a 05 "rig-a"`.

Experiment ACC-01: a file whose only edit was this string was accepted by WTOOLS
1.6.3 and by the W1 (fw 2.0.18) and stored byte-identically.

---

## 5. Type 165 — presets

### Envelope — **[correlated]**

`field 1` varint = preset count (80–82 observed), then repeated `field 5`, one
submessage per preset. Layout: 4 factory pages × 20 (block 1 full presets,
block 2 colour, block 3 move, block 4 beam), then user presets appended.

**[correlated]** Preset identity, agreeing with `wpj-toolkit`: the UI is 1-based,
20 slots per page, `id = (page - 1) * 20 + (slot - 1)`. Id 0 is omitted from the
wire, as protobuf default.

**[correlated]** 29 KB of preset payload survived five consecutive controller
saves **byte-identical**. A generated 165 is stable on the device — the firmware
does not re-serialise it the way it does record 115.

### Preset submessage

| Field | Meaning | Status |
|---|---|---|
| `f19` | preset id | correlated 5/5 |
| `f25` | name, UTF-8 | correlated (82 names) |
| `f1` / `f2` | Beam FX 1 / 2 | correlated |
| `f5` / `f6` | Color FX 1 / 2 | correlated |
| `f21` / `f22` | Move FX 1 / 2 (extra `f3`, default 50) | correlated |
| `f28` | position index per group A–H, 8 packed varints | correlated |
| `f17` | dimmer per group A–H, packed, default `[255]×8` | hypothesized |
| `f8` / `f24` | Color FX / Move FX active flag (packed, `[0]` or `[255]`) | correlated |
| `f31` | static colour: 4 × 5 varints, bitmasks over type-140 pads | hypothesized |
| `f4` | content mask (255 full, 8 colour, 17 beam, 5 move) | hypothesized |
| `f16` | ~13 varints, FX-bank masks per group in complementary pairs | hypothesized |
| `f11` | 500 / 2000 / 4000 — fade time in ms? | hypothesized |
| `f10` | factory library version? | observed |
| `f9`=1, `f15`=1000, `f13`×6, `f18`, `f3`, `f7`, `f14`, `f23`, `f26`, `f27`, `f29`, `f30` | unknown | observed |

`f28` read from named factory presets: `Floor` = `[0]×8`, `Center` = `[1]×8`,
`Crowd` = `[3]×8`, `Ceiling` = `[4]×8` — the values index into type 150.

**[observed]** `f28`, `f17`, `f8`, `f24` are **packed** varints (wire type 2),
not repeated varints. The two "flags" are packed lists of one element.

### FX submessage — shared by Beam, Color and Move

The wire fields are ours; the enum *labels* are cross-referenced with
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
| `f5` | Color FX: 2 varints = 16-bit pad mask (v1 = pads 1–8, v2 = 9–16). Move FX: one varint 0–6. Beam FX: see lead L1 | correlated (Color) |

Effect type `f7`, Beam: `0` Sin Wave · `1` Sparkle · `2` Chaser · `3` CanCan ·
`4` Heartbeat · `5` Wolf Rider · `6–8` FX Seq 1–3.
Effect type `f7`, Color: `0` Rainbow 1 · `1` Sparkle 1 · `2` Chaser 1 ·
`3` Light Fever · `4` Rainbow 2 · `5` Sparkle 2 · `6` Rainbow 3 · `7` Chaser 2.

ACC-04 wrote `f7` 3 → 2 on a Color FX and the operator read **Chaser** on the
device — matching the Color enumeration at index 2, an independent confirmation
of both the field and the label set.

**[hypothesized]** Merging the two sources resolves `f8`/`f6`/`f9`: the toolkit
names `sizePercent` / `fadePercent` / `phasePercent` in 0–100 and our defaults
are 100 / 25 / 50, which reads naturally as size 100 %, fade 25 %, phase 50 %.
Not yet tested by a single-variable save.

---

## 6. Type 102 — flash FX settings

Full field census over 18 files:

| Field | Values seen | Reading | Status |
|---|---|---|---|
| 2 | 1, absent | present only in WTOOLS-written files, never after a controller save | observed — legacy, dropped by fw 2.0.18 |
| 3 | 2, absent | same | observed — legacy |
| 4 | 6-byte array | release mode per flash key | **device-confirmed** |
| 5 | **100 in 18/18** | never moved | unattributed |
| 6 | **100 in 18/18** | never moved | unattributed |
| 7 | absent, 1, 2, 4 | SPEED multiplier | **device-confirmed**, see below |
| 8 | absent, 1 | group-exclusion mask | hypothesized |
| 9 | 1, 72, 75, 80, 100 | STROBE speed, stored 1–100 | **device-confirmed** |
| 11 | **100 in 18/18** | never moved | unattributed |

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

FX-01 moved STROBE only, FLASH → TOGGLE: exactly one byte changed, at index 1.
FX-02 then published the prediction `01 00 01 02 03 04` *before* measuring and
set five keys in one save — exact match, five bytes at once.

### `field 9` = STROBE speed — **[device-confirmed]**

0 % on screen writes **1**, 100 % writes **100**. Stored range **1–100**.

### `field 7` = SPEED multiplier — **[device-confirmed]** with a footnote

| Setting | `f7` |
|---|---|
| normal (1×) | absent |
| 0.5× | **1** |
| 2× | 2 |
| 4× | 4 |

FX-05 ruled out a list index (which would have written 3 for 4×); FX-06 ruled
out a literal multiplier (0.5× cannot be stored as a fraction, and wrote 1). So
`f7` is an **enumeration whose values coincide with the multiplier on the
integer steps and reserve 1 for 0.5×**. A `1 << rank` reading also fits all four
points. Still open: **8× and FREEZE** separate them — the rank reading predicts
16 for the next step, the enumeration predicts 8.

### The three unattributed 100s — the highest-value single experiment

Guide 10 lists exactly **three** per-effect parameters still unaccounted for:
BLINDER fade-out, SMOKE intensity, SMOKE fan speed. Record 102 has exactly
**three** fields that read 100 in every file and have never moved (`f5`, `f6`,
`f11`). The assignment is a 3! = 6-way permutation, and **one save with three
distinct values resolves it completely.**

### `field 8` — **[hypothesized]** excluded-group bitmask

Appeared as `1` exactly when group A was excluded from STROBE. Bit 0 = group A.
Six effects can each exclude groups, so `f8` is either STROBE's own mask with
five siblings elsewhere, or a shared one. Excluding A + C (expect 5) then moving
the exclusion to another effect separates the two readings.

---

## 7. The patch model — six record types locked by arithmetic

The strongest structural result available. Eight identities hold **exactly,
18/18 files, with no fitted constants**:

```
1.  count(116)                    == 116.field1
2.  Σ 116[p].f2                   == count(110)
3.  116[p].f3                     == Σ_{q<p} 116[q].f2      (running offset)
4.  110[c].f3 monotone and        <  count(111)
5.  Σ 105[e].f7                   == count(106)
6.  max(105[e].f5) + 1            == count(115)
7.  115[r].f3                     <  count(116)
8.  Σ 116[ 115[r].f3 ].f2         == count(120)
```

- **116 = fixture profile catalogue.** `f2` = channel count of the profile;
  `f3` = index of its first channel in record 110; `f8` = UTF-8 name **truncated
  to 19 characters** (`'LED PAR 56 Black RG'`); `f9` = 16-byte profile hash;
  `f11` = epoch-ms timestamp (2021-02-16 … 2022-10-28).
- **110 = concatenated channel lists of all profiles**, profile *p* occupying
  `[116[p].f3, 116[p].f3 + 116[p].f2)`. Per channel: `f2` = feature/type enum,
  `f3` = index of its first entry in 111, `f4` = default value, `f5` = ordinal.
- **111 = concatenated range/capability lists**, indexed from 110. Entries read
  `{f1 = from, f2 = to, f3 = function id}`; *rig-a* holds clean 8-way
  splits `1–50 / 51–100 / … / 241–255` and 31-wide splits `0–31 / … / 224–255`,
  i.e. gobo or colour-wheel slots.
- **105 = the DMX patch.** `f1` = library fixture id, **stable across projects**
  (`1017` is the same `6x18W 6in1 RGBAW UV` in two unrelated rigs); `f4` =
  0-based start address; `f5` = index of the fixture row in 115; `f6` = category
  0…8; `f7` = channels consumed. A fixture built from several DMX blocks emits
  several entries **sharing one `f5`** (a `LED BAR 252 RGB` = 3 × 4 ch; a
  `LASERBAR` = 6 × 8 ch).
- **115 = fixture instances**, one per row of the fixture grid. `f3` = index into
  116; `f2` = start offset in an internal channel arena; `f6` (on the record,
  not the items) = display order, a permutation of 0…n−1.
- **120 = flat per-fixture-channel value table**, one contiguous block per
  fixture in ascending `115.f2` order. Verified block by block on *rig-b*:
  six blocks of 10, then 7, then 11, then 2 — 134 entries, matching identity 8.

**Refuted**: record 115 does *not* have a fixed 20 slots (10/15/20/22 across the
four rigs, always `max(105.f5) + 1`); the "20" in earlier notes was a
coincidence of one rig having 20 fixtures. Record 155 is *not* the DMX patch map
(§8).

### 7.1 The 115 arena has holes — **[hypothesized]**

Identity 8 holds 18/18, but the stronger claim that `115.f2` offsets tile
`[0, count(120))` exactly holds only for *rig-a* and its derivatives.
Elsewhere the offsets are stride-correct per profile but leave gaps and run past
the end of 120 — always staying below 512.

| File | `count(120)` | `max 115.f2` |
|---|---|---|
| *rig-a* | 86 | 72 (+14 = 86, exact tiling) |
| *rig-b* | 134 | 255 |
| *rig-c* | 215 | 499 |
| *rig-c-bug* | 258 | 499 |

**[hypothesized]** `115.f2` addresses a 512-slot internal channel arena that is
not compacted when fixtures are deleted or re-patched, while 120 is always
rewritten densely. Alternative candidate: `f2` is stale and the firmware ignores
it. This matters: if the firmware indexes 120 by `115.f2`, an un-compacted arena
is a second independent way to read zeros — though it does not by itself explain
the rig-c blackout, since the healthy revision has out-of-range offsets too.

### 7.2 Record 125 is fully derived — **[correlated 18/18]**

Nine items in every file. Item *i* carries `f4` = a 7-byte blob and `f8` = an
optional UTF-8 name (`'Beam'`, `'<group-B name>'`). The first 6 bytes of `f4`, read
little-endian, are exactly:

```
mask[i] = OR over fixture rows r of (1 << 115[r].f3)   where category(r) == i
```

Verified bit for bit, 18/18, with four independent name↔content matches. So
**125 is the 9 fixture categories, not the 8 groups A–H**, and its masks are
recomputable from 105 + 115 + 116. Only `f8`, the user-editable category name,
carries information a writer must preserve.

**[observed]** The 7th byte of `f4` is `0x30` in the *Porte* projects and `0x38`
in the rig-c family — a per-project constant replicated on all 9 items,
correlating with record 151 being populated.

### 7.3 Record 130 carries no project data — **[observed]**

102 bytes, 9 items, byte-identical in 18/18 files across 4 rigs with 3–7
profiles and 10–22 fixtures. Items 0–7 read `{f2 = i, f4 = 20, f6 = i, f7 = 1,
f8 = 1}`, item 8 reads `{f4 = 27, f6 = 8, f8 = 1}`. The 9-item shape matches
record 125's categories one-for-one and `f4 = 20` matches the pads-per-page
limit. **[hypothesized]** per-category factory defaults. Negative result worth
recording: **no differential experiment will be productive on 130** unless the
operator edits something category-related.

---

## 8. Type 155 — 4 FX sequences — **[correlated]**

`field 1` = 4, then four `field 5` items, each with `f1 = 8`, `f2 ∈ {1,2}`,
`f3 ∈ {2,4}` and `f4` = a 128-byte array.

**Refuted**: 4 × 128 = 512 is *not* a DMX universe. The DMX patch is record 105
(identity 5 above). The arrays are **8 groups × 16 steps**, four sequences, and
`f3` is a step count — it moved 4 → 16 when the operator touched the sequence
editor's STEP control.

---

## 9. Prefix bytes 20–63

| Offset | Content | Status |
|---|---|---|
| 20–35 | 16-byte project UUID = the `wlinkData` file name | correlated |
| 36–39 | constant `15 2b 10 c0` in 18/18 | observed — container magic |
| **40–47** | **little-endian uint64 version**, incremented by one per save | **correlated** |
| 48–49 | constant `01 f9` in 18/18 | observed |
| 50 | writer/schema version: 8 (older WTOOLS), 10 (WTOOLS-written), 11 (after any controller save) | correlated |
| 51 | constant 0 | observed |
| 52–63 | constant `02 be e8 1c a2 6c cb 54 6d c7 b6 ec` in 18/18 | observed |

**This corrects an earlier claim that byte 40 is a save counter.** Byte 40 is the
*least significant byte* of a 64-bit version field the firmware increments by one
per save; the observed `62 → 66` across four saves is +4 on that LSB.
**Falsifiable consequence:** after enough saves the LSB wraps, offset 41
increments and offset 40 drops to `0x00`. **A writer must treat 40–47 as one
64-bit integer, not a byte, or it will corrupt the version at the wrap.**

**[device-confirmed]** Bytes 20–35 are *not* an import identity key: creating a
new project without touching them works (ACC-01).

---

## 10. Writing rules

Five rules. A writer that skips any of them will produce files the device
rejects, or worse, silently corrupt a show.

1. **Recompute the SHA-1** over `bytes[20:EOF]` on every save. A stale digest
   makes WTOOLS refuse the file.
2. **Preserve unknown bytes verbatim.** Re-emit untouched records exactly as
   read, and any field you do not understand inside a record you did touch.
3. **Never overwrite.** Write to a new path (`open(path, "xb")`), always.
4. **Verify by re-reading.** Reload the written file, re-decode, compare against
   what was asked, and diff record-by-record against the source: any record that
   moved outside the intended edit is a bug, not a detail.
5. **Edit, do not synthesize.** Every preset, position or palette entry written
   must already exist in the donor file. Creating structures from scratch is not
   validated by anything in this document.

### What a patch-editing writer must recompute

Record **125**'s masks are fully derivable from 105 + 115 + 116, and the offsets
in `116.f3`, `110.f3`, `115.f2` plus the size of 120 are all determined by the
profile channel counts (§7). A writer that changes the patch must **recompute**
them, not preserve them. A writer that does not touch the patch can leave all six
records untouched — which `tools/wpjlib.py` does by construction.

### A controller-side save is not byte-preserving — **[device-confirmed]**

Saving on the W1 re-serialises some records into the firmware's canonical form.
Observed: type 115 shrank 329 → 287 bytes as its 20 items each lost `f6` and `f7`
and gained a sequential `f9`; `f7` never came back. Consequence: **a round-trip
through the device cannot be verified by file hash.** Differential experiments
must compare record by record and expect canonicalisation noise. Record 165 is
the happy exception (§5).

### The USB serial link is not error-free — **[device-confirmed]**

Two of four `GET_PROJECT` transfers of a 43 KB project failed in one session: one
produced an unparseable body, one returned the correct length with wrong bytes
*and* a SHA-1 header that did not match its own body. **Never trust a single
download.** Accept a transfer whose SHA-1 header verifies, otherwise require two
identical consecutive transfers.

---

## 11. Open leads

L1 and L2 exist only because our byte-level decoding was cross-referenced with
the `wpj-toolkit` enumerations; neither source has them alone.

- **L1 — Beam FX `feature`.** The toolkit documents a Beam-only `feature` enum
  (`0` Dimmer · `1` Zoom · `2` Iris · `3` Pan · `4` Tilt · `5` Effect) with no
  wire location. We have `f5` carrying a pad mask for Color FX and a bare varint
  0–6 for Move FX, and unmapped for Beam. **[hypothesized]** Beam `f5` is
  `feature`. One single-variable save (Dimmer → Zoom) settles it.
- **L2 — group-mask asymmetry.** The toolkit reports `colorGroupMask` over A–H
  but `beamGroupMask` over **A–D only**. Our `f16` hypothesis is "FX-bank masks
  per group in complementary pairs"; the A–D restriction constrains which halves
  of `f16` are which.
- **L3 — record 102 `f5`/`f6`/`f11`.** Three fields at 100, three unassigned
  guide parameters, one save (§6). **Highest value per unit of effort.**
- **L4 — static colour `f31`.** 4 repetitions × 5 varints, bitmasks over type-140
  pads (`Deep Red` = mask 32 = pad 6). Are the 4 repetitions groups A–D?
  Experiment: one pad, one group.
- **L5 — MIDI mapping record.** The W1 accepts MIDI (preset select by note,
  group/master dimmers by CC, MIDI clock at 24 PPQN) and the map is learned per
  project on `WM_MODE_MAPPING = 43`, so it must live in the file. Not yet
  located. This is the gateway to live control.
- **L6 — record 151.** 0 or 64 bytes, 4 × three 16-bit values centred on 32767.
  Correlates with the `0x38` byte in 125 `f4`. Lowest confidence; recorded so
  nobody re-derives it.
- **L7 — the 115 arena.** Is `115.f2` a live address into a 512-slot arena, or a
  stale field? Bears on the rig-c blackout (§7.1).
- **L8 — variants B and C.** Only the top level is mapped. A different
  serialisation of the same show; needs its own campaign.

---

## References

See `PROVENANCE.md` for sources, licences, and what may be reused from where.
Detailed experiment write-ups, with hashes and dates, live in `research/`.
