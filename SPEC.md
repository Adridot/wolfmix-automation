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

Measurement base: W1 Mk1 (serial withheld), firmware **2.0.18**, macOS. WTOOLS
**1.6.3** for the ACC-series acceptance tests; the host has since moved to WTOOLS
**2.0.2** build 248 — a **beta**, installed over the stable — which is what the
later protocol work was read against.

Corpus hashes in `corpus/SHA256SUMS` — 71 files, regenerated 2026-09-01; the
files themselves are not distributed ([`LEGAL.md`](LEGAL.md)).

### Evidence cutoff — 2026-09-01

Every claim below is consolidated from the ledger,
[`research/evidence.md`](research/evidence.md), up to that date. The ledger is
the newer of the two by construction: it is written next to the measurement,
this document is written afterwards. **When they disagree, the ledger is
right**, and `make check` refuses a tree in which this section's cutoff has
fallen behind a finding that contradicts a statement here.

**Pending consolidation.** These findings are in the ledger and have **no home
in this document yet**. A gap that is listed is a known gap; an unlisted one is
a lie of omission, which is why the list is here rather than in a commit
message.

| Finding | What is missing here |
|---|---|
| EXP-05, EXP-05bis, EXP-06, EXP-07 (2026-08-31) | The variant-B/C campaign: the Rosetta alignment, the FX **banks per effect**, the refuted base-0/base-1 discriminator, and the three single-variable differentials written by the device. §1 still describes B and C by their envelope only. |
| GOBO-01 (2026-08-30) | Where the gobo icon library lives — 800 entries at the tail of the resource flash, the entry index being the id in `145.f2`. §3.4 describes the palette without it. |
| UPLOAD-01, UPLOAD-02, UPLOAD-03, UPLOAD-04 (2026-08-31) | The channel that writes the resource flash: a tty and not raw USB, the 1 + 179 message geometry inferred from the vendor's own log, the installed bundle verified against the manifest it ships with, and the contradiction between two sessions refused at their first message and an upload published `device-confirmed`. §10.2 describes the link without that upload on it; nothing here describes the flash bundle at all; and the question of whether executable firmware shares the message is open, which is why no write path follows. |
| PROFILE-01 (2026-08-31), PROFILE-02, PROFILE-03, PROFILE-04 (2026-09-01) | Reading one fixture profile off the controller: `GET_PROFILE`'s reply layout, the sweep of 221 profiles that found no unnamed field and refuted three of the first pass's sub-readings, the preset `f4` axis settled against `ssl2.CIBLE_PRESET`, and the fact that the locally-authored profiles are served too. §10.2 describes the link without this read on it, and §7's record 116 now names the same key space (PROFILE-05, consolidated) without saying where the other side of it is read. |
| GUARD-01 (2026-08-31) | The nine bench measures of the write-path guards. They constrain the tools, not the format, so this may end up belonging in `docs/` rather than here — that decision is itself pending. |

**On file counts.** A figure like "45/45" below is **historical**: it names the
corpus that was present when the claim was measured, not a corpus you have. It
is never updated — updating it would erase what was actually checked — and the
live number comes from a command instead:

```bash
python3 tools/wpj_identities.py     # N identities verified on M variant-A files
python3 tools/wpj_counts.py --print # the current corpus size, and every drifting figure
```

`make check` re-runs every one of those counts on whatever corpus is present,
which is the only number that means anything on your machine.

And the size was never the strength. The measurement corpus held 45 variant-A
files, of which only **4 are independent rigs** (*rig-a* 10 fixtures, *rig-b*
15, *rig-c* 20, *rig-c-bug* 22 = a re-patched *rig-c*). The rest are derived:
files written by our own writer from *rig-a*, and controller saves of one copy
of *rig-c*. An identity holding on all of them is strong enough to **kill** a
hypothesis; it is not by itself enough to call anything device-confirmed.

---

## 1. Three file variants

Three distinct container layouts share the `.wpj` extension. A reader must
branch on them; one that assumes a single layout will fail silently on the
others.

| Variant | Layout | Origin | Corpus |
|---|---|---|---|
| **A** | 20-byte SHA-1 + opaque prefix + TLV container | device dumps, WLINK imports | 45 files |
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

## 3. Record inventory — **[correlated 45/45]**

20 record types <!--count:record_types-->, of which 20 <!--count:decoded-->
have a codec schema and 0 <!--count:passthrough--> round-trip verbatim as
opaque hex. Records 102, 106, 110 and 155 were documented here and undecoded
in the codec until 2026-09-01 — a gap `tools/wpj_coverage.py` made visible by
counting it. Record **161** was the last one without a schema and got one the
same day; it names **nothing** inside itself, and Q8 is exactly as open as it
was. A schema is a claim about the wire, not about the meaning.

| Type | Size (bytes) | Items | Identification | Status |
|---|---|---|---|---|
| 101 | 12–20 | — | project name (`f1` UTF-8) | **device-confirmed** (§4) |
| 102 | 16–28 | — | flash-FX settings, 6 keys | **device-confirmed** (§6) |
| 105 | 114–351 | 10–27 | **patch index**: one entry per DMX block, slicing record 106 | correlated (§7) |
| 106 | 600–2614 | 50–201 | one entry per **mapped** channel, `f2` = absolute DMX channel | correlated (§7) |
| 110 | 210–775 | 22–80 | flattened channel table of all profiles | correlated |
| 111 | 347–1526 | 45–201 | flattened range/capability table, indexed by 110 | correlated |
| 115 | 116–409 | 10–22 | **fixture instances** | correlated (§7) |
| 116 | 162–334 | 3–7 | **fixture profile catalogue** | correlated |
| 120 | 532–1199 | 86–258 | flat per-fixture-channel value table | correlated |
| 125 | 111–137 | **9** | **the 8 groups A–H + a 9th slot**: name + profile bitmask | correlated (§7.2) |
| 130 | 102–229 | 9–19 | **the DMX IN mapping table** | **device-confirmed** (§7.3) |
| 135 | 140–145 | **16** | the 16 ColorFX palette pads (RGBWALU) | correlated |
| 140 ×8 | 182–189 | **20** each | **static COLOUR palette**, one per group A–H, `f2` = group 0…7 | **device-confirmed** (§3.3) |
| 145 ×8 | 40–159 | **20** each | **static GOBO palette**, one per group A–H, `f2` = group 0…7 | **device-confirmed** (§3.4) |
| 150 ×8 | 483–498 | **20** each | **static POSITION palette**, one per group A–H, `f2` = group 0…7 | **device-confirmed** (§3.2) |
| 151 | 0–93 | 0 or **4–6** | **detached-fixture position offsets**, sliced by record 150 | **device-confirmed** (§8.1) |
| 155 | 562–567 | **4** | **4 FX sequences**, 16 steps × 8 groups + step count | **device-confirmed** (§8) |
| 160 | 393–542, **optional** | 7–9 | **`LIVE EDIT` macros** — one per operator-defined Live Edit button (COV-18) | correlated |
| 161 | 599–604 | **3** | 3 packed arrays of **188** varints; of the 564 values, 6 ever move (COV-06, COV-21). **Not volatile** — that word was wrong. Named nowhere: Q8 | observed |
| 165 | 26219–30882 | 80–85 | preset container | correlated (§5) |

**Field 1 is the item count on 15 of these types** — 105, 106, 110, 111, 115,
116, 120, 125, 130, 135, 140, 150, 151, 155, 160 — exact on the corpus with no
exception, an empty table writing **no** field 1 rather than a zero (COV-04).
Record 145 carries none: its 20 slots are implicit (§3.4). And `165.f1` is
**not** the count — it disagrees on 19 files, always low by exactly the entries
a preset capture appended (81 against 83, 81 against 85), so whatever it
counts, it is not the entries present.

### How much of a file is read — **[correlated]**

`tools/wpj_coverage.py` attributes every byte to a named field, an inert one, an
unnamed one, or a schemaless record, and asserts the four sum to the file. Run
it; the figure below is the corpus this repository was written against and
yours will differ.

| | corpus |
|---|---|
| **read** — a field a codec schema names | **92.8 %** |
| **inert** — no name, and one value in the whole corpus | 4.2 % |
| **partial** — a field inside a schema'd record that varies and that nothing names | 3.0 % |
| **unknown** — a record with no schema, or one whose protobuf does not parse | 0.0 % |

**`read` and `inert` are not added, and the distinction is the point.** `read`
says what a field means. `inert` says only that the field never says anything
different — a statement about the *corpus*, not about the field, and exactly
what calling one `constant_1` would smuggle in as a name. What makes it worth
recording anyway is that it is **checked**: each entry declares its value, the
value is verified on every file, and a second one stops the run instead of
widening the bucket. `116.profiles.f6` is 1 on ninety occurrences and **3** on
one, and `102.f11` is 0 and 100; neither is in the table. So "100 %" here would
mean `read + inert = 100` with nothing partial and nothing unknown, which is a
weaker claim than it sounds like and is stated that way on purpose.

Of the file, 54.0 % is named by a **device-confirmed** reading, 26.8 % by a
`correlated` one and 11.9 % by a `validated` one; each name carries a ledger id
the tool refuses to leave dangling. Read is a claim about *names*, not about
*measurements*, which is why the split by status is printed next to it and why
a field promoted without evidence fails the gate instead of raising the number
(COV-01).

160 is the only record ever absent outright: **9** files without it, **36** with.
Record 151 is present in all 45 but carries a **zero-length payload** in exactly
those same 9 — the rigs that never detached a fixture.

`gitfeber/wpj-toolkit` documents only types 101, 135 and 165; its published
inspect model emits the other 17 as `unknown_tlvs`, type and length only.

### 3.1 The `×8` families are the eight groups A–H — **[device-confirmed]**

`140 ×8`, `145 ×8` and `150 ×8` are the **groups A–H**, indexed by top-level
`field 2` = 0…7, absent for group A. An earlier survey in this document read
them as pages; that was wrong, and three independent device readings settle it:

- the first copy of 150 holds the operator's own `<group-A name>`, where the seven
  others hold the factory `Floor` — exactly what group A shows on the device;
- the colour picker on group B prints the header `<group-B name> / ITEM B1`, that name being
  the name record 125 gives group index 1;
- the gobo picker on group A prints that group's own name, index 0.

Each record carries exactly 20 items whatever the rig: **20 palette slots per
group**, not a per-group fixture list. Most are untouched factory content —
`140[4..7]`, `145[1..7]` and `150[1..7]` are byte-identical across all corpus
files, 4 independent rigs and two writers.

### 3.2 Type 150 — static POSITION palettes — **[device-confirmed]**

```
field 1 = 20                     slot count
field 2 = 0…7                    group index, absent for A
field 5 × 20                     one per slot
  f1  slice length   number of record-151 entries this slot owns  (§8.1)
  f2  slice offset   where they start in record 151                (§8.1)
  f3  FAN            unsigned, value = percent × 65536
  f4  FOCUS OFFSET   signed, 32768 = 0 %, 65535 = +100 %
  f5  name           UTF-8, absent when the slot is empty
  f6  PAN            unsigned, percent × 65536
  f7  TILT           unsigned, percent × 65536, absent = 0
  f8  CROSS          unsigned, percent × 65536 — device-confirmed (COV-08)
```

**Two conventions live in this one sub-message.** `f3`, `f6`, `f7` and `f8` are
**unsigned** — `percent = v / 65536`, 32768 = 50 %, and they cannot go negative.
`f4` alone is **signed** — `percent = (v − 32768) / 32767`, 32768 = 0 %. Both
halves are now read off the screen: on one slot `f4` = 32768 displays **0 %**,
where the unsigned reading would have shown 50 %. A writer that applies one
convention to the whole sub-message gets `FOCUS OFFSET` wrong by half its
range.

**Unnamed slots are named by the firmware — [device-confirmed] (COV-12).** A
slot with no `f5` prints `Position N`, N being the 1-based slot index, the same
synthesis record 145 applies to its unnamed gobo pads (§3.4). A writer must not
expect to find those strings in the file.

**The divisor is 65536, not 65535** — POS-02 measured it: 32768/65535 is
0.500008, which pushes two predicted channels one unit off, while 32768/65536 is
exactly 0.5 and every predicted channel lands. The difference only shows up once
you predict DMX, which is why the earlier reading survived so long.

Read off the device's own edit screen (SHIFT + a position pad shows PAN, TILT,
FOCUS OFFSET and FAN | CROSS as percentages), on slots where the four values
disagree.

**`f8` is `CROSS` — [device-confirmed] (COV-08).** The second half of the
`FAN | CROSS` encoder, read off the POSITION screen on two slots with the
prediction published first: 36044 showed **55 %** where the unsigned reading
predicts 55 and the signed one 10, and 32767 showed **50 %** against 50 and 0.
No write, no save, no deploy — the experiment project already held a slot where
the five values disagree, which is the condition this section states.

**An earlier reading of this document called `f3` pan and `f4` tilt. Both were
wrong**, and the corpus alone could not catch it: in the rigs available, every
named slot of the group examined reads PAN 50 %, which is indistinguishable
from the neutral fields. Only the device screen separated them. `tools/wpj_show.py`
writes `f6`/`f7`.

### 3.3 Type 140 — static COLOUR palettes — **[device-confirmed]**

The item is the **same sub-message as record 135** (documented externally as the
global ColorFX palette), with 20 items instead of 16:

```
field 1 = 20 · field 2 = group 0…7 · field 5 × 20
  f1 red · f2 green · f3 blue · f4 white · f5 amber · f6 lime · f7 uv
  0…255, absent = 0
```

Settled by the picker's `RGB+` view, which prints the **raw 0–255 channel
values** and names all seven channels in field order. The other four views are
lossy: the display **truncates**, so 127/255 shows as 49 %, not 50 %.

**`SHIFT` + an encoder prints two decimals — [device-confirmed] (COV-11).**
On the POSITION screen the same gesture is a fine adjust *and* a
high-resolution read: `53.55 %`, `99.94 %`. **Measure positions this way.** A
whole-percent reading cannot separate `v/65536` from `v/65535`, nor rounding
from truncation, nor — as COV-08 nearly learned the hard way — two candidate
scales that happen to land one unit apart. Four two-decimal points settle the
sub-message on their own: PAN, TILT and FAN on unsigned `v/65536`, FOCUS
OFFSET on signed `(v−32768)/32767` where the unsigned reading would have
printed `99.97` against the screen's `99.94`.

**That rule does not hold on every screen — [device-confirmed] (COV-09).** The
POSITION screen **rounds**: 39976/65536 is 60.9985 % and shows **61**, 32767 is
49.9985 % and shows **50**. Seven of eight readings discriminate and rounding
takes all of them. Either the two screens format differently, or the colour
measurement above needs redoing — one photograph of the picker would say which.
**Predict with the right one.** COV-08's published prediction was wrong by one
on six values for using truncation here; it survived only because its two
rival readings sat 45 points apart.

**A pad component drives its engine role, not only red/green/blue.** Recalling a
cue on pad 16 = `(255, 105, 8, white 64)` put red 255, green 105 and blue 8 on
the group's colour channels **and 64 on its `extra1` channel** — role 6 of §7.5,
here at fixture address + 4 (GEN-01; the published prediction bet `extra2` and
was wrong on which extra, right on the structure). So `f4`…`f7` reach real
channels wherever the profile has them, on one measured point.

The 20 pads are named on screen (Amber, Lime, Cyan, UV, Pink, Red, …) but **no
name is stored in the file** — the labels are firmware constants tied to the
slot index, unlike record 150 where `f5` holds a per-slot name.

Grid layout, **[correlated]** by transposition from the type-145 measurement:
4 columns × 5 rows, filled column by column, top to bottom.

**Writable — [device-confirmed] (PAL-01, 2026-08-27).** The three locks of
*read before write* are all off for `f5`. The round-trip is byte-identical on
**360 occurrences across the 45 variant-A files**. A single-variable
differential changed one
component of one pad of one group — `140[B].pads[6].red`, 255 → 100, with every
other record byte-identical — and the device rendered it exactly: a cue on that
pad with `f17` = 120 drove the ten group-B reds to `trunc(100 × 120/255)` =
**47** where the same cue had driven them to 120 before, and to **100** under a
cue that does not read the dimmers. Exactly ten channels moved. The control is
the neighbour: a cue on **pad 10** of the same record reproduced its earlier
frame on all 2048 channels, so the write did not spill. The panel also redrew
the pad itself, before any recall.

**Scope.** The round-trip lock is off for the whole sub-message, but the
differential and the device acceptance are not: one pad, one group, one
component (`red`), on a profile that has colour channels. `white`, `amber`,
`lime` and `uv` were never varied, and nothing is measured on a profile with no
colour channel — the write is proven for the component measured, not for the
whole sub-message.

The consequence is a **trade, not a free win**: each distinct colour written
consumes one of the group's twenty pads, and those pads are the ones the
operator has under their fingers. The show generator therefore still picks the
nearest existing pad rather than writing one (`docs/generator.md`).

### 3.4 Type 145 — static GOBO palettes — **[device-confirmed]**

Same family, but **no `field 1` count** — the 20 slots are implicit.

```
field 2 = 0…7                    group index, absent for A
field 5 × 20                     one per gobo pad
  f1  glyph    one character, icon font; ' ' (0x20) = empty slot
  f2  gobo id  global image id, absent on an empty slot
  f3  name     UTF-8, optional, operator-assigned
```

**The palette is derived from the patch.** `f2` is the image id carried by the
gobo-wheel ranges of the group's fixtures: the `f4` values of record 111's
ranges whose function `f3` = 14, in wire order, skipping the "open" range and
the shake ranges. Two identities hold on every variant-A file of the corpus and
are checked mechanically by `tools/wpj_identities.py` (part of `make check`):

| Identity | Meaning |
|---|---|
| `110[c].f2 == len(111 slice of c)` | `110.f2` is a **range count**, not a feature enum |
| `[145 items].f2 == [111 ranges with f3 == 14].f4` | the gobo palette **is** the fixture's gobo wheel |

Confirmed on DMX, two points, exact: pressing pad *n* drives the group's gobo
channel to the **lower bound** of range *n* (`111.f1`) — pad 1 (`f2` = 425) gave
7, pad 10 (`f2` = 345) gave 70, and nothing else in 2048 channels moved. That
same capture confirms `115.f2` as the 0-based DMX start address.

Names: 19 slots print `Gobo N` with N = the 1-based slot index and store
nothing; the one named slot stores its string in `f3`. **The labels are
synthesised by the firmware**, so a writer must not expect to find them.

Two flavours of empty must both be reproduced: an empty slot inside a populated
palette stores `f1 = ' '`, while a wholly empty palette stores bare empty items
(`2a 00`).

**Scope.** Measured on one group, one profile (six instances of one moving
head). Nothing contradicts the general rule, but transposition to another rig
is **[hypothesized]** until measured.

### Writable, and the order is free — **[device-confirmed]**

Two deploys on the same rig (RENAME-01, SORT-01, 2026-08-30) extend the
reading from *derived* to *editable*:

- **`f3` written outside the device displays as-is.** Eleven names set in one
  edit all appeared on their pads after a reload. Cap names at **19 UTF-8
  bytes**: the limit is measured for preset names (PRESET-05, where exceeding
  it bricks the project open) and unmeasured here, so the tool refuses longer.
- **The wire order of the wheel ranges *is* the pad order.** Permuting the
  `f3 = 14` sub-messages of record 111 — each range keeping its own DMX
  bounds — reordered the page exactly, and the firmware accepted the
  resulting **non-monotonic** range list without re-sorting it. Pads still
  drive each range's lower bound.
- **Names follow their entries, not their positions**, when 145 is rewritten
  consistently with 111 (ids and names permuted together, glyphs reassigned
  sequentially from `!` — the shape device-written files use).

Both edits ride the standard path: record 111 now has a codec schema
(byte-exact on the whole corpus, like every schema), and `wpj_show` carries
them as the `gobo_names` and `gobo_order` spec keys — same auto-verify
contract as preset edits. The compiled specs reproduce the two accepted
candidates byte for byte.

---

## 4. Type 101 — project name — **[device-confirmed]**

Protobuf field 1, length-delimited, UTF-8. Example: `0a 05 "rig-a"`.

Experiment ACC-01: a file whose only edit was this string was accepted by WTOOLS
1.6.3 and by the W1 (fw 2.0.18) and stored byte-identically.

---

## 5. Type 165 — presets

### Envelope — **[correlated]**

`field 1` is a varint whose meaning is **open — [observed]**, then repeated
`field 5`, one submessage per preset. Layout: 4 factory pages × 20 (block 1 full
presets, block 2 colour, block 3 move, block 4 beam), then user presets appended.

**`f1` is not the preset count.** It equals it on 26 of the 45 corpus files and
disagrees on the other 19. Both candidate rules die on a single device-written
pair: in F30-04 the controller itself added a preset, and `f1` went 82 → **81**
while the count went 82 → 83, with 81 *named* presets on both sides. A writer
preserves it verbatim and maintains nothing.

**What the device's writer puts there, measured once — [observed] (GEN-03).** A
controller save of a file of **ours** rewrote `f1` from **82** to **88**, and
there were 88 entries on both sides: here the firmware wrote the **entry count**.
One device-written pair says count, the other (F30-04) says not-count, so the
field's meaning stays open — but the firmware does not always leave it alone, and
a record-by-record differential must expect `f1` to move after a save.

**[correlated]** Preset identity, agreeing with `wpj-toolkit`: the UI is 1-based,
20 slots per page, `id = (page - 1) * 20 + (slot - 1)`. Id 0 is omitted from the
wire, as protobuf default.

**[correlated]** 29 KB of preset payload survived five consecutive controller
saves **byte-identical**. A generated 165 is stable on the device — the firmware
does not re-serialise it the way it does record 115.

### Preset submessage

| Field | Meaning | Status |
|---|---|---|
| `f19` | preset id, `id = (page − 1) × 20 + (slot − 1)`; **gaps are tolerated by the loader**, and `SET_PRESET` on an id that falls in a gap is a **no-op** — it leaves the live frame untouched | **device-confirmed** (PRESET-07, RECALL-05) |
| `f25` | name, UTF-8, **capped at 19 bytes by the loader** — a longer one makes the whole project refuse to open | **device-confirmed** (§5.8) |
| `f1` / `f2` | Beam FX 1 / 2 | correlated |
| `f5` / `f6` | Color FX 1 / 2 | correlated |
| `f21` / `f22` | Move FX 1 / 2 (extra `f3`, default 50) | correlated |
| `f28` | position index per group A–H, 8 packed varints, indexes type 150 | correlated |
| `f29` | **gobo index per group A–H**, 8 packed varints, **0-based** into type 145, **255 = none and it clears the channel** | **device-confirmed** (§5.1) |
| `f30` | **static-colour `PATTERN` per group A–H**, 8 packed varints, 11 modes | **device-confirmed** (§5.1) |
| `f31` | **static colour: 20 bytes = 160 bits = eight 20-bit pad masks**, one per group A–H | **device-confirmed** (§5.1) |
| `f17` | **dimmer per group A–H as a percentage of `255`**, packed, default `[255]×8`. Rendered through the channel's travel limits: `DMX = 106.f5 + (f17/255)·(106.f6 − 106.f5)`, the same formula as pan/tilt. On a fixture that has colour channels the intensity goes into the **colour** (`pad × f17/255`) and the dimmer channel stays at `f6`. Gated by the controller setting `store group dimmers in preset`. | **device-confirmed** (GEN-02) |
| `f8` / `f24` | Color FX / Move FX active flag (packed, `[0]` or `[255]`) | correlated |
| `f4` | **permission mask over the FX engines** — an engine active in `f16` implies its bit here | **[correlated]** (§5.4), checked by `f4_autorise_les_moteurs` |
| `f16` | **twelve 9-bit group masks**, one per engine, five of them the flash keys | **device-confirmed** (§5.4, §5.7) |
| `f11` | **FADE in milliseconds**, absent = 0 | **device-confirmed** (§5.3) |
| `f10` | **content mask**: the six `PRESET EDIT` toggles, a set bit = toggle **off** | **device-confirmed** (§5.3) |
| `f32`…`f35` | per-group arrays added at schema 10, defaults `50 / 0 / 100 / 100`; all zero in a project upgraded from schema 8 | correlated |
| `f15` | **HOLD**, 1000 ↔ `00:01.00` on all 3697 corpus presets, never varied | correlated (§5.3) |
| `f18` | the **Live Edit mask** | correlated (§5.5) |
| `f9`=1, `f13`×6, `f3`, `f7`, `f23`, `f26`, `f27` | unknown | observed |

`f28` read from named factory presets: `Floor` = `[0]×8`, `Center` = `[1]×8`,
`Crowd` = `[3]×8`, `Ceiling` = `[4]×8` — the values index into type 150.

**[observed]** `f28`, `f17`, `f8`, `f24` are **packed** varints (wire type 2),
not repeated varints. The two "flags" are packed lists of one element.

### 5.1 The four per-group arrays — **[device-confirmed]**

A preset carries four arrays of eight slots, one slot per group A–H, and each
points into that group's own palette record:

| Field | Points at | Encoding |
|---|---|---|
| `f28` | type 150, positions | index |
| `f29` | type 145, gobos | **0-based** index, `255` = none |
| `f30` | — | `PATTERN`, the static-colour spread mode |
| `f31` | type 140, colours | one **20-bit mask** per group, packed 8 × 20 = 160 bits |

`f31` is not eight separate fields: it is 20 bytes read as one little-endian
integer, group *g* occupying bits `[20g, 20g + 20)`, bit *n* selecting pad
*n* + 1.

```python
mask = lambda blob, g: (int.from_bytes(blob, "little") >> (20 * g)) & 0xFFFFF
```

**`f31` holds in the writing direction too — [device-confirmed] (GEN-01).** Two
generated presets differing in `f31` and in nothing else — verified field by
field on the candidate, and stored byte for byte by the device — recalled as
exactly **twenty changed channels out of 2048**: ten reds 255 → 0 and ten blues
0 → 255, matching pad 6 = `(255, 0, 0)` and pad 9 = `(0, 0, 255)` of that group's
record 140. The output is the palette, channel for channel. The mask reading was
device-confirmed **on reading**; it is now confirmed **on writing**, by a
single-variable experiment. The same series confirms `f30` = 9 (`SINGLE`)
written by us: one colour, identical on all ten fixtures of the group, no
alternation.

**`f29`.** Recalling a preset with `f29[A]` = 9 drove the group's six gobo-wheel
fixtures to DMX 70 — pad 10, the lower bound of its range — and `f29[A]` = 2
drove them to 21, pad 3. A preset with `[255]×8` put them back to 0, so the
sentinel is **applied**, not skipped: there is no way to say "leave as is".

**`f30`.** Eleven modes: eight are four directions × two renderings, plus
`SINGLE`, `FLASH` and an alternating pattern.

| Value | Mode |
|---|---|
| 0 | stepped, alternating one fixture in two |
| 1 / 2 | blended / hard, dealt **centre → edges** |
| 3 / 4 | blended / hard, dealt **edges → centre** |
| 5 / 6 | blended / hard, dealt **first → last** |
| 7 / 8 | blended / hard, dealt **last → first** |
| 9 | `SINGLE` — one colour, every fixture the same |
| 10 | `FLASH` — the group's colour pads become **momentary**, not a layout |

Distribution, measured at two and three colours in both geometries: along the
run a direction defines — the **half-length** for the centre/edge directions,
the **full length** for the others — the selected pads are dealt in **ascending
pad order**, split as evenly as possible, with the **remainder to the earliest
colours**. Ten fixtures over three colours gives 4-3-3; a half-length of five
over three gives 2-2-1. Blended modes interpolate the same deal and **truncate**
rather than round.

Full experiment record, including the eight predictions published before each
capture, in [`research/evidence.md`](research/evidence.md).

### 5.3 The content mask is `f10`, not `f4` — **[device-confirmed]**

The `PRESET EDIT` screen's six toggles are `165.f10`, and a set bit means the
toggle is **off**:

| bit | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| | `COLOR` | `MOVE` | `BEAM` | `GOBO` | `LIVE EDIT` | `OTHER` |

The manual states what each includes: `COLOR` = Color FX **and static colours**,
`MOVE` = Move FX **and static positions**, `BEAM` = Beam FX, `GOBO` and
`LIVE EDIT` the corresponding parts, `OTHER` = **the group dimmer values**
(record 165 `f17`).

**Bit 5 was called `DIMMER` until firmware 2.0.15 — [observed] (FW-01).** The
vendor changelog names it twice. 2.0.5: "Add the possibility to exclude Gobo,
Live Edit, and Dimmer values from a Preset" — the three toggles born together
are exactly bits **3, 4 and 5**, so the bit numbering is **chronological** and
bits 0–2 (`COLOR`, `MOVE`, `BEAM`) predate them. 2.0.15: "Change DIMMER preset
part to OTHER". `OTHER` is therefore a **widening**, not a synonym, and what it
absorbed is not known — FW-03 measured the bit on a cue carrying neither
`f32`–`f35` nor an active gobo, so it is blind to precisely those contents. A
writer that sets bit 5 to keep the dimmers out also turns off whatever else
`OTHER` now covers. The changelog is an external, static source, the same rank
as the manual: it corroborates and it dates, it confirms nothing on the device.

**And the gate below moved too.** The same 2.0.15 entry reads "Revert 'Store
group dimmers in Preset' operation to how it was in firmware 1.x". The
controller setting has changed behaviour twice, so **any dimmer measurement
made on a firmware older than 2.0.15 is off-topic for this rig.** No experiment
in this repo is on record as having run on one — the device has read 2.0.18
throughout — so this is a bound on what may be imported from outside, not a
retraction of an entry above.

> **A third gate, and the first one outside the file (GEN-02, 2026-08-27).**
> After `f10` (§5.3) and `f16` (§5.4), both in the project. The Settings menu
> carries **`store group dimmers in preset`**. With it off, a preset's `f17`
> does nothing at all, whatever `f10` says — which is how GEN-01 measured five
> captures with no dimmer moving. With it on, `f17` acts — through the travel
> limits of `106.f5`/`f6`, see the `f17` row of §5's preset submessage table
> (GEN-02). The panel says the same thing by a path that never touches DMX: a
> preset carrying `f17` = 120 on one group prints that group's dimmer as
> **47 %** on the `HOME` screen, and `120 / 255` = 47.06 (F7-01).
>
> That confounds the `OTHER` attribution: ACC-02 ran with the setting off, so
> it could never separate "bit 5 silenced the dimmers" from "the setting did".
> **Bit 5 = `OTHER` came back down to `hypothesized`** — it rested on the
> manual plus a pre-existing state, never on a write that isolated it. Bit 1
> (`MOVE`) was unaffected: RECALL-05 measured it on a preset we wrote.
>
> **It is back up at `validated` (FW-03, 2026-08-27).** Two cues we wrote,
> identical field by field except `f10` — 30 against 62, bit 5 alone —
> recalled with the controller setting **on**: **exactly 18 channels** moved,
> and exactly the eighteen the model predicts. Six group-A dimmers 69 → 220
> (`106.f5` → `f6`), ten group-B reds 120 → 255, two group-C dimmers 0 → 255,
> and nothing else in 2048. The manual, the 2.0.15 changelog and this write
> now name the same bit by three independent paths.
>
> **Not `device-confirmed`, and the limit was published before the shot.**
> The cue carries neither `f32`–`f35` nor an active gobo, so if the
> `DIMMER` → `OTHER` rename of 2.0.15 widened the bit to cover those, this
> experiment is blind to it. `validated` on the perimeter of a static cue.

Screen order, left to right then down. Every bit is held by at least two
independent readings — six photographs of factory presets plus targeted writes —
and three of them by a single-variable differential. Corpus values re-read
sensibly: `51` = BEAM + GOBO, `61` = MOVE alone, `62` = COLOR alone, and nothing
above 62 in 3697 presets.

`f11` is **FADE in milliseconds**, absent = 0: 4000 → `00:04.00`, 2000 →
`00:02.00`, 500 → `00:00.50`, absent → `00:00.00`, all measured on screen.
`f15` is **HOLD**, 1000 ↔ `00:01.00`, consistent on six screens but never varied
— **[correlated]**.

### 5.4 `f16` — twelve 9-bit group masks — **[correlated 45/45]**

`f16`'s packed varints are the **bytes of a little-endian bit field**, the same
construction as `f31`. Cut at a stride of **9** — nine because record 125 has
nine slots — every slice is a group mask, and on the six **engine** slices 0–5
the ninth bit is never set. The flash slices 6–10 do set it (§5.7).

| Slice | Engine | Pinned by |
|---|---|---|
| 0 | **Color FX** | it *was* "equals `color_fx_active`, 3696/3697". On today's corpus neither containment holds — 6 presets one way, 18 the other — and `wpj_identities.py` asserts nothing here (COV-14) |
| 1 | **Move FX** | `slice 1 ⊇ move_fx_active`, exact. The **equality** held on 3697 presets and is **refuted** by a preset the device composed on 2026-09-01: slice 1 = 1 against `move_fx_active` = 0 (COV-14) |
| 2 | **Beam FX** | active only on beam-page presets |
| **3** | **unattributed, and *not* the second Colour engine** | `0` even on a preset that really runs a second Colour page — **[validated]**, FX2-01 |
| **4** | **unattributed, and *not* the second Move engine** | same shot, same reasoning |
| 5 | **the groups the preset addresses** | **[validated]** — the device's writer rewrote our clones' 255 to **2** (= B) and **7** (= A+B+C) (GEN-03), and a preset the device composed **from scratch** carries `2` = the one group whose `f17` is non-zero, with its Beam engine off (FX2-01) |
| **6** | **`WOLF`** | device-confirmed, 511 when latched |
| **7** | **`STROBE`** | device-confirmed, 511 |
| **8** | **`BLACKOUT`** | device-confirmed, 511 |
| **9** | **`BLINDER`** | device-confirmed, 511 |
| **10** | **`SPEED`** | device-confirmed, 511 |
| 11 | per-project constant | never varies between presets |

**Slice 5 was read as "255 always" and it is not — [validated] (GEN-03).** Every
preset of the corpus carries 255 there, over **2446** presets, and the reading
was `correlated` on that strength. The uniformity was the writer's, not the
field's: nothing in the corpus had ever varied it. Our generator cloned that 255
into six appended presets, and the device's own save corrected each one to the
groups its cue actually lights — **2** = B on the two group-B cues, **7** =
A+B+C on the three three-group cues. The control is the exception: the single
preset whose live copy lit all eight groups kept 255. What a writer should put
there is not measured — our 255 clones recalled correctly before the device
rewrote them — but the field is no longer a constant, and a generator that
clones a donor preset inherits a mask that does not describe its own cue.

A preset captures the **live flash-key state** when it is overwritten. Five of
the six keys have a slice, each measured by its own latch; only `SMOKE` writes
nothing, confirmed by a capture where it was held alongside `STROBE`. Having an
exclusion mask in record 102 and having a slice here are **independent** —
`SPEED` has a slice and no exclusion. The flash slices write all **nine** bits
including the effects slot, where the FX engines stop at 255.

The alignment tests itself: at a stride of 8, slice 1 would read 254 where
`move_fx_active` says 255, and the containment that replaced the equality still
fails there on 1767 presets. The value domain once given here as
`{0, 1, 2, 5, 7, 255, 511}` is **stale** — 3 and 4 both occur on the corpus as
it stands (COV-14) — which is the same lesson twice: a set measured over a
corpus describes the corpus.

**A writer must set both carriers.** `color_fx_active` and `move_fx_active`
duplicate slices 0 and 1; ACC-03b wrote one and not the other, and the firmware
followed `f16` — which is why its Color FX was ignored.

`165.f4` is a **permission mask over these engines**, not a content mask:
engine 0 active implies `f4` bit 3, engine 1 bit 2, engine 2 bit 4, on every
preset of every file. The implication is one-directional — a page may permit an
engine none of its presets uses.

### 5.4b The second FX engine has no proven group mask — **[correlated 45/45]**

Firmware 2.0 ("Double Trouble") doubles the FX engines: two Color, two Move,
two Beam, which the manual says can run **at once on different groups**. That
last clause is from the manual and the trade press — an external source, so
**[observed]** at best, and never verified on this controller.

The **structure** is decoded and round-trips: `f1`/`f2` = Beam 1/2, `f5`/`f6` =
Colour 1/2, `f21`/`f22` = Move 1/2. Slot 2 is not decorative — it holds values
that differ from slot 1 on 742 colour, 1439 move and 1240 beam presets. And
whenever a type's `f16` slice is non-zero, slot 2 differs from slot 1: 738/738,
1439/1439, 1186/1186, no exception. An engine that is on stores two
configurations.

**One slice per engine, covering both pages — [validated] (FX2-01).** A preset
composed at the panel with Colour page 1 on group A and page 2 on group B
carries slice 0 = **3** = A+B: a single mask for the engine, whichever page each
group is on. Slices 3 and 4 stayed `0` **while a second page was genuinely in
service**, so they are not the second Colour and Move engines. What they are is
still unknown, and the zeros across the corpus remain uninformative.

That also settles slice 5. The rival reading — layout
`[Colour1, Move1, Beam1, Colour2, Move2, Beam2]`, making slice 5 the second Beam
engine — is refuted: on that same device-composed preset the Beam engine is
**off** and slice 5 reads `2`, exactly the one group whose `f17` is non-zero. The
addressed-group reading no longer rests on a save of a file we wrote; it holds on
an entry the firmware authored alone.

**Where the page assignment lives: `f7` — [validated].** A per-group selector,
`0` = `FX1` and `1` = `FX2`, confirmed against a photograph of the `HOME` screen
element by element. It is orthogonal to this slice: slice 0 is which groups the
engine switches **on**, `f7` is which page each group is **assigned** to, on or
off — a group with the engine off keeps its pending page. See §5.6 and the
registry, F7-01.

Slice 11 stays unattributed. Its values look like group masks — 5, 2 and 7 —
but "the groups that have a fixture" fails on 44 of 45 files and "the schema
number" fails because schema 11 carries both 2 and 5. It also varies between
presets in one file of 42, which softens the "per-project constant" reading
above without refuting it.

The cheap discriminator is one preset and one save, no deploy:
[`research/evidence.md`](research/evidence.md), FX2-01.

### 5.5 `f18` = the Live Edit mask — **[correlated]**

The `LIVE EDIT` screen is 4 pages of 20 buttons; `f18` is 10 packed varints =
**80 bits**, one per button, the same byte-field construction as `f16` and
`f31`. Across the corpus only buttons **1, 2, 4, 5 and 20** are ever set — the
top of page 1 — out of eighty possible.

**Each button is defined in record 160 — [device-confirmed] (COV-19).** A macro
created at the panel on the button labelled `Live Edit 6`, feature `01 Pan`,
value 200, changed **one record and one only**: `160.f5` = **5**, the button
index 0-based, and `160.f8` = `[200, 0]`, the values. Three identities hold on
all 71 files that carry the record and are checked by `wpj_identities.py`: the
buttons in a file are distinct, all fall inside the 80-button grid, and **every
bit any preset sets here lands on a button some macro defines** — a preset
cannot carry a Live Edit that does not exist. Their wire order is free, 65 of
71 files storing them out of button order.

Inside a macro, `f1` is a list of **bit masks** and `f8` gives **one value per
set bit** — `popcount(f1) == len(f8)`, exact on all 490 corpus macros and
checked on every run. The measured macro shows it bare: one targeted fixture,
`f1 = [17]` (two bits), `f8 = [200, 0]`. This **refutes** reading `f8` as a
per-group array of eight, which its `[50] × 8` shape on the factory macros
invites. `len(f1)` never exceeds the fixture count, which fits one mask per
targeted fixture — consistent, not measured. **`f7` encodes the targeted fixture — [device-confirmed] (COV-27).** Two macros
on the same fixture with different features come back with a byte-identical
`f7`; its length is `2 × len(f1) + 4` on 489 of 490. What it *says* about the
fixture is **not** any of the three identifiers the file already carries
(COV-28): a second macro differing only in which of two identical moving heads
it targets moves a leading `129 → 4` and a trailing `3 → 126`, matching
neither the record-115 index (14 vs 15), nor the DMX address (1 vs 17), nor
`f9` (20 vs absent). It keeps its neutral key.

**The panel takes the fine channel with the coarse one.** A macro set on
`01 Pan` alone stores two bits and two values, the second being `03 uPan` at 0;
`02 Tilt` likewise drags `04 uTilt`. A writer asking for one feature gets two.

`f10`'s `LIVE EDIT` bit says *whether* a preset carries Live Edits; `f18` says
*which*. **And record 160 is where those buttons are defined — [correlated]
(COV-18).** The firmware's mode table names the screen itself
(`live_edit_macro_edit`, mode 41), and the **9 corpus files with no record 160
carry no `f18` bit anywhere**, 9/9, while every file that has the record has
bits. The record's name arrived here as `correlated (pre-existing)` — inherited,
never measured — and this is the first evidence under it. The bits do **not**
index the macro list: 7 files of 71 set one past the macro count.

### 5.6 Thirteen per-group arrays — **[correlated 45/45]**

Sweeping the whole format for fields that always decode to exactly 8 packed
varints returns thirteen, all in record 165:

```
f3  f7  f14  f17  f23  f27  f28  f29  f30  f32  f33  f34  f35
```

`f17` dimmers, `f28` positions, `f29` gobos, `f30` colour pattern are named. The
other nine are **known to be per-group** even where their meaning is not, which
rules out reading them as scalars. `f32`–`f35` appear at schema 10, and the
vendor changelog dates them to firmware **2.0.5** — "Add the possibility to set a
Prism, Focus, Zoom and Iris value on each group. These values can be stored in a
preset like Gobo Rotate." — **[observed]** (FW-02). "On each group" corroborates
the per-group shape from outside the bytes; "like Gobo Rotate" puts `f14`
(`ROTATE`) **before** the four newcomers, which is why they sit at the tail of
the field numbering: a protobuf field number is assigned at design time, so an
addition starts from the tail — **the numbering tells the chronology** (FW-01
reads the bits of `f10` the same way).

**[device-confirmed]** five of them are the **`STATIC GOBO` features**, measured
by setting all five on group A to distinct values and capturing them into a
preset:

| Screen | Field | | Screen | Field |
|---|---|---|---|---|
| `ROTATE` | `f14` | | `ZOOM` | `f34` |
| `FOCUS` | `f32` | | `IRIS` | `f35` |
| `PRISM` | `f33` | | | |

Their schema-10 defaults `50 / 0 / 100 / 100` on `f32`–`f35` read as Focus 50 %,
Prism 0 %, Zoom 100 %, Iris 100 %. **[observed]** The device writes those
defaults out explicitly: a controller save of a file of ours that **omitted**
the four tables brought all 88 presets back carrying `focus` = 50, `prism` = 0,
`zoom` = 100, `iris` = 100 (GEN-03). **An absent field is not a zero field** —
here the firmware makes the difference visible, and a reader that had reported
the missing tables as `0` would have had Zoom and Iris wrong by their whole
range and Focus wrong by half of it. **[hypothesized]** (FW-02) `f35` is a
percentage inside the iris bounds the **fixture profile** carries — firmware
2.0.9 added "Iris min and max selection from fixture builder" — which is
exactly the shape GEN-02 measured for `f17` through `106.f5`/`f6`. `f3`, `f7`,
`f23` and `f27` remain unattributed, and the changelog does not name them
either (FW-02).

These are **live state** until a preset captures them: a project save alone does
not write them, only `SHIFT` + tapping a preset does. **[validated] (F7-02)** —
a page reassignment made at the panel and then saved left all 45054 bytes of the
project identical but for the version counter's low byte and the SHA-1 header it
forces. One byte of payload, and record 165 untouched.

**The record files each engine as a regular quadruple — [validated] (F7-03).**
Page 1, page 2, the page **selector**, then the "active" field:

| Engine | page 1 | page 2 | selector | active | shot |
|---|---|---|---|---|---|
| Beam | `f1` | `f2` | **`f3`** = `page_beam_fx` | *(`f4` sits here)* | F7-04 |
| Colour | `f5` | `f6` | **`f7`** = `page_color_fx` | `f8` | F7-01 |
| Move | `f21` | `f22` | **`f23`** = `page_move_fx` | `f24` | F7-03 |

A selector is a per-group array of eight: `0` = `FX1`, `1` = `FX2`. All three are
measured, one shot each, and each shot left the other two byte-identical. `f4`
occupies the Beam "active" slot but F4-03 read it as a permission mask over all
three engines — the coincidence of position is noted, not read. `f27` does not
follow the pattern (`f25` is the preset name) and stays unattributed.

**`f27` is the per-group position FADE, in milliseconds — [device-confirmed]
(COV-10).** The `FADE` the `ALL POSITIONS` page prints per group. Three points
on one line: `0` ↔ `0s` on a panel-composed project, `1000` ↔ `1s` on recall,
and `3000` ↔ `3s` written by a capture — the third published before the
download, because one point cannot separate a unit from a table. Measured on
**group A alone**: this rig has no fixture on the other seven, so their slots
are read by position in an array whose eight-element shape is
`correlated 45/45`, not measured. The save that wrote it created one preset and
altered no existing one by a single field.

Its neighbour is the reason it was found: `f27` sits immediately before `f28`,
the per-group position **index**. Two per-group tables side by side, which is
what §5.6 says the field numbering is good for.

**`f27` is not zero everywhere — [observed] (COV-02).** This document said it
was, on 3697 occurrences, and that was true of the corpus that existed when the
sentence was written. On today's 4312 presets, **26 carry `[1000] × 8`**, and
the split is by **author**: every preset of a project a WTOOLS 2.0.2 duplicate
produced carries 1000 on all eight groups, every preset composed at the panel
carries eight explicit zeros. Neither side omits the field. One preset crosses
the line inside the corpus — the device recaptured it during EXP-07 and it came
back `[0] × 8` while its six untouched neighbours kept 1000 — but that
recapture rewrote seventeen fields at once, so it names the author and not the
meaning. 1000 is the shape of a millisecond default, beside `f11` FADE and
`f15` HOLD; that is a **hypothesis** and nothing here tests it.

**A hand-set page 1 is indistinguishable from a page never set.** A group put on
`BEAM FX1` explicitly came back as `0`, exactly like the six groups nobody
touched (F7-04). The field encodes the page, not the fact of having been set —
which is what licenses reading every zero as "page 1" rather than "absent".

**`f7` is the per-group Colour FX page selector, `0` = `FX1` and `1` = `FX2` —
[validated] (F7-01, F7-03).** A change to the **Move** page left it byte-identical,
which is the single-variable differential that makes it Colour-specific rather
than a shared selector. A preset composed at the panel came back with
`f7` = `[0, 1, 1, 0, 0, 0, 0, 0]`, and a photograph of the `HOME` screen taken on
that same state reads `COLOR FX1` for group A and `COLOR FX2` for groups B and C.
Eight elements, three populated groups, two distinct values, and the mapping
lands on all three.

**`f7` and `f16` slice 0 are orthogonal, and the corpus hid it.** Slice 0 says
which groups the Colour engine **switches on**; `f7` says which page each group
is **assigned to**, switched on or not. On that preset slice 0 is `3` = A+B while
`f7` marks B *and* C: group C is assigned to `FX2` with its engine off, and the
screen prints its `COLOR FX2` without the box that A and B carry. A group keeps
its pending page. That also explains the four corpus presets, where group B is
the only one on page 2 and nothing else betrays it.

That discriminator has been fired three times, once per engine, and each shot
left the other two selectors byte-identical (F7-01, F7-03, F7-04). None is
`device-confirmed`: we have never **written** a selector, and no page we asked for
has been read back off the panel.

**A project save alone writes none of this.** The same page change, made at the
panel and saved without a preset capture, left all 45054 bytes identical but for
the version counter (F7-02). The capture is what writes it.

Two earlier readings of this field are **refuted**. "`f7` marks a preset whose
Beam engine is off while its two Beam pages differ" held on four corpus presets
and died on the fifth. And the guessed split `f3` = Colour / `f7` = Beam /
`f23` = Move is wrong: a **Colour** edit moved `f7` and left `f3` at zero.

The live-state rule above matters here: that value was captured off the panel by
a `SHIFT` + tap, so it records what the operator had selected, not what a project
author typed. `f3` and `f23` are `0` on all 3697 occurrences — corpus
uniformity, not field uniformity, as `f27` then went on to demonstrate the hard
way (COV-02).

### 5.7 The flash keys live in `f16` — **[device-confirmed]**

Five of the twelve 9-bit slices of `f16` (§5.4) carry the **flash key state** a
preset captures:

| Slice | Key |
|---|---|
| 6 | `WOLF` |
| 7 | `STROBE` |
| 8 | `BLACKOUT` |
| 9 | `BLINDER` |
| 10 | `SPEED` |

A latched key writes **511** into its slice — all nine bits — which is why 511
is the only value outside `{0, 1, 2, 5, 7, 255}` in the whole corpus.

All five are confirmed **in both directions**: captured from a latched key into
the file, and written into a file the controller then acted on. `SMOKE` is the
sixth flash key and writes **nothing** — proven by the capture where it was
latched **alongside `STROBE`**: slice 7 rose and no second slice did, which a
solo capture could not have separated from "not latched". The six keys are
completely accounted for.

Whether a preset carries flash state at all is a Settings toggle (`Include Flash
buttons in Preset`), not a property of the file format.

### 5.8 Preset names are capped at 19 UTF-8 bytes — **[device-confirmed]**

A name of 23 bytes does not get truncated and the entry is not dropped: the
**whole project refuses to open**, with `Error opening project` on the panel.
Re-cutting the same file with a 16-byte name opens normally, which isolates the
name as the sole cause (PRESET-05, PRESET-06).

No name in the 3697-preset corpus exceeds 19 bytes, and
`tools/wpj_identities.py` asserts it on every file so a generator cannot
regress past it.

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
| `f9` | **speed %** | 0–100, never above on any engine over 352 distinct presets; default 50. **Present 352/352** — a speed is never 0 | **validated** (FX6-02/03) |
| `f6` | **phase %** | defaults 25 beam / 20 colour / absent (0) move | **validated** (FX6-02/03) |
| `f8` | **size %** | 100 beam and move; **absent whenever the effect has no `SIZE`** — 330/330 colour presets on a Rainbow carry none | **validated** (FX6-02) |
| `f2` | **fade %** | default 100; **above 100 is `Flick`** on move (200 ×12). Colour's 150/200 unexplained | **validated** (FX6-02/03) |
| `f3` | the third encoder's **second mode**, engine-dependent: **`Feature`** on beam, **`Fan`** on move. Colour has no second mode and never carries `f3` — 0 occurrences on 352 distinct presets | Beam: `1` = `Zoom` measured, absent = `0` = Dimmer. Move: direct %, `83` measured, default **50** — the field is present 352/352 because a centred fan is not a null fan | **validated** on both engines (FX6-03, FX6-04) |
| `f5` | Color FX: 16-bit **colour mask** over record 135's pads. Move FX: the **effect's position**. Beam FX: **unattributed, and with no candidate left** — all six beam screen properties are placed, and `f5` is absent on all 352 distinct presets | Color: 2 varints (v1 = pads 1–8, v2 = 9–16). Move: one varint, nine on screen, only 0/1/5/6 seen | correlated (Color and Move) |

Effect type `f7`, Beam: `0` Sin Wave · `1` Sparkle · `2` Chaser · `3` CanCan ·
`4` Heartbeat · `5` Wolf Rider · `6–8` FX Seq 1–3.
Effect type `f7`, Color: `0` Rainbow 1 · `1` Sparkle 1 · `2` Chaser 1 ·
`3` Light Fever · `4` Rainbow 2 · `5` Sparkle 2 · `6` Rainbow 3 · `7` Chaser 2.

ACC-04 wrote `f7` 3 → 2 on a Color FX and the operator read **Chaser** on the
device — matching the Color enumeration at index 2, an independent confirmation
of both the field and the label set.

**The property count, corrected — [validated] (FX6-01/02/03).** Two earlier
revisions of this document got this wrong in opposite directions: one lined
`f8`/`f6`/`f9` up with the toolkit's three names, the other declared the screens
carried **four** properties for three fields so no assignment could work. Read
one by one, the three screens carry **five** properties on colour, **six** on
beam and **seven** on move, and every one of them now has a field:

| Property | Field | Colour | Beam | Move |
|---|---|---|---|---|
| Speed (+ sync `f10`, division `f1`) | `f9` | ✓ | ✓ | ✓ |
| Phase | `f6` | ✓ | ✓ | ✓ |
| Order | `f4` | ✓ | ✓ | ✓ |
| Size | `f8` | ✓ | ✓ | ✓ |
| Fade | `f2` | ✓ | ✓ | ✓ (`> 100` = `Flick`) |
| the third encoder's second mode | `f3` | — | `Feature` (`Zoom` = 1) | `Fan` (83 % measured) |

Three corrections got the count right. **`Order` was double-counted** — it is
`f4`, named `link_order` since F4-03. **`Flick` is not a value** but the top of
Fade's range, pushing the fade past 100 % of the step time. And the **beam
screen had never been read here**: it carries a sixth property, `Feature`,
sharing the third encoder with `Size` exactly as move's `Size | Fan` does — and
both second modes land on the same field, `f3`.

**Then the measurement moved a field nobody had questioned.** FX6-02 and FX6-03
read nine screen values off two fresh entries and matched all nine: `f6` = Phase,
`f8` = Size, `f9` = **Speed**, `f2` = **Fade**. `f2` had been read as "speed %"
since ACC-04 and carried a `correlated` status; it is the fade. The permutation
this document set out to resolve was a three-way over `f6`/`f8`/`f9`; it was
really a **four-way**, and the fourth element was hidden behind a name that had
never been measured. Consistency across files is not attribution.

`wpj_show.py` still refuses to write `phase`, `size` and `fade`: they are read,
not written, and rule 2 wants a byte-identical round-trip *and* acceptance
downstream before any of them becomes writable.

---

## 6. Type 102 — flash FX settings

Full field census over the 45 variant-A files:

| Field | Values seen | Reading | Status |
|---|---|---|---|
| 1 | absent, 8 | **BLACKOUT excluded groups**, bitmask | **device-confirmed** (FX-09) |
| 2 | 1, 3, 4, absent | **BLINDER fade-out**, index into 0 / 0.2 / 0.5 / 1 / 2 s | **device-confirmed** (FX-08) |
| 3 | 2, 4, absent | **BLINDER excluded groups**, bitmask, bit 0 = A | **device-confirmed** (FX-08) |
| 4 | 6-byte array | release mode per flash key | **device-confirmed** |
| 5 | 100, 70 | **SMOKE fan speed**, 0–100 | **device-confirmed** (FX-07) |
| 6 | 100, 40 | **SMOKE intensity**, 0–100 | **device-confirmed** (FX-07) |
| 7 | absent, 1, 2, 4 | SPEED multiplier | **device-confirmed**, see below |
| 8 | absent, 1, 3 | **STROBE excluded groups**, bitmask, bit 0 = A (A+B wrote 3) | **device-confirmed** (FX-09) |
| 9 | 1, 72, 75, 80, 100 | STROBE speed, stored 1–100 | **device-confirmed** |
| 10 | absent, 32 | **WOLF excluded groups**, bitmask | **device-confirmed** (FX-10) |
| 11 | 100, 0, absent | **unattributed and inert** — see below | correlated (F11-01) |

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

### The three 100s — resolved, except one

An earlier revision of this document framed `f5`/`f6`/`f11` as a 3! permutation
over the three guide parameters left unaccounted for. The framing was wrong, and
one save (FX-07) showed why: `f5` went to **70** and `f6` to **40** with
distinct values, naming them SMOKE **fan speed** and SMOKE **intensity**, while
the third parameter — BLINDER fade-out — turned out not to be a 100 at all. It
is a **new field `f2`** that only appeared once the operator moved it (FX-08).
A field can be absent until it is used; a permutation argument over the fields
present cannot see that.

### `field 11` — unattributed and inert — **[correlated]**

`f11` is the last unknown in record 102, and the search for it is deliberately
**stopped**. No UI control moves it, the firmware-2.0 manual lists no setting
that would, F11-03 ruled out `Button brightness`, and F11-01 wrote `f11` = 0
into a project the controller accepted: neither the display nor a single one of
2048 DMX channels moved, idle or with the blinder active. Since then the device
re-emits the field **absent**, so absent and 0 are the same value. Preserve it
verbatim; do not spend another experiment on it.

### `field 8` — STROBE's excluded groups — **[device-confirmed]**

Excluding A + B wrote **3**, so it is a per-group bitmask with bit 0 = A. The
masks are **per effect, in separate fields**: `f1` BLACKOUT, `f3` BLINDER, `f8`
STROBE, `f10` WOLF. Exactly four, because the Settings list offers `Exclude
Wolf / Strobe / Blinder / Blackout` and nothing for SPEED or SMOKE — the field
count and the menu agree.

### What record 102 does not hold

**FREEZE writes 0** — absent, indistinguishable from normal speed (FX-07,
re-confirmed FX-08): either it is not persisted, or it lives elsewhere. And a
contradiction inside `research/` is carried here rather than resolved: the
closing maps list `8` as a `f7` SPEED value, while FX-04's own table records 8×
as never measured and no corpus file carries `f7` = 8. One save settles it.

---

## 7. The patch model — six record types locked by arithmetic

The strongest structural result available. Eight identities hold **exactly,
45/45 files, with no fitted constants**:

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

Three more, added once `105.f4` was corrected, and mechanically re-checked on
**45/45** files by `tools/wpj_identities.py`, which now runs **20** identities
<!--count:identities--> plus two before/after pair checks (F30-04, and the
FLASH-09 pair — the files, not its retracted reading):

```
9.  the [f4, f4+f7) intervals of 105, sorted by f4, tile [0, count(106))
10. every 106 entry of a slice lies in [115[r].f2, 115[r].f2 + profile channels)
11. the fixtures' DMX windows are pairwise disjoint
```

Identity 10 fails immediately if slices are attached to the wrong fixtures, and
identity 11 has no reason to hold for an internal arena index — together they
are what pins `115.f2` to a real DMX patch.

- **116 = fixture profile catalogue.** `f2` = channel count of the profile;
  `f3` = index of its first channel in record 110 (`offset_110` in the codec
  since 2026-09-01 — it was documented here from the start and never named,
  and a reader that defaults it to 0 decodes every profile as the first one); `f8` = UTF-8 name **truncated
  to 19 characters** (`'LED PAR 56 Black RG'`); `f9` = the profile
  **UUID** (16 bytes), the identifier `GET_PROFILE` takes and
  `wolfmix.py profiles` reports — the file and the controller share one key
  space, and 293 of the corpus's 357 entries are RFC 4122 v5 (PROFILE-05);
  `f11` = epoch-ms timestamp (2021-02-16 … 2022-10-28).
- **110 = concatenated channel lists of all profiles**, profile *p* occupying
  `[116[p].f3, 116[p].f3 + 116[p].f2)`. Per channel: `f2` = the **number of
  ranges** this channel owns in 111, `f3` = index of its first entry in 111,
  `f4` = the **feature**, `f5` = the index of the channel this one belongs to
  (§7.6). **This corrects two names an earlier revision of this bullet carried**
  — `f2` as a feature enum and `f4` as a default value. The identity
  `110[c].f2 == len(111 slice of c)` kills the first (§3.4) and `roles_106`
  puts the second in bijection with the engine role `106.f4` (§7.5). Both
  checks have been running in `wpj_identities.py` the whole time; the prose
  simply never caught up.
- **111 = concatenated range/capability lists**, indexed from 110. Entries read
  `{f1 = from, f2 = to, f3 = function id}`; *rig-a* holds clean 8-way
  splits `1–50 / 51–100 / … / 241–255` and 31-wide splits `0–31 / … / 224–255`,
  i.e. gobo or colour-wheel slots.
- **105 = the patch index into 106.** `f1` = library fixture id (`library_id`
  in the codec since 2026-09-01: it had been called "profile", the name
  `115.f3` also carries, and the two never agree on a single one of the
  corpus's 1394 patch entries — COV-05), **stable across
  projects** (`1017` is the same `6x18W 6in1 RGBAW UV` in two unrelated rigs);
  `f5` = index of the fixture row in 115; `f6` = category 0…8. **`f4` is the
  running offset into record 106 and `f7` is that slice's length** — *not* a DMX
  address and *not* a channel count. A fixture built from several DMX blocks
  emits several entries **sharing one `f5`** (a `LED BAR 252 RGB` = 3 × 4 ch; a
  `LASERBAR` = 6 × 8 ch).
- **106 = one entry per *mapped* channel**, `f2` holding the **absolute 0-based
  DMX channel**. Subtracting the fixture's `115.f2` gives an offset pattern that
  is constant per profile — a 16-channel moving head exposes ten mapped
  channels at offsets `0 1 6 6 7 8 10 12 13 14`, which is why its `f7` reads 10.

  **Retracted**: earlier notes called `105.f4` a 0-based start address and
  `105.f7` a channel count. Sorted by `f4`, the intervals `[f4, f4+f7)` tile
  `[0, count(106))` exactly, and two entries share offset 141 in *rig-c* because
  one has span 0 — which no DMX address could do. **The DMX start address is
  `115.f2`**, device-confirmed by the gobo capture in §3.4.
- **115 = fixture instances**, one per row of the fixture grid. `f3` = index into
  116; `f2` = start offset in an internal channel arena; `f6` (on the record,
  not the items) = display order, a permutation of 0…n−1.
- **120 = flat per-fixture-channel value table**, one contiguous block per
  fixture in ascending `115.f2` order. Verified block by block on *rig-b*:
  six blocks of 10, then 7, then 11, then 2 — 134 entries, matching identity 8.
  **`f1` is the channel's DMX value — [device-confirmed] (COV-16).** Emitted on
  every channel no engine role claims: eight such channels were predicted from
  the file and read back off the live frame exactly, and none moved while an
  effect drove ten others. Read the blocks in **ascending DMX-address order** —
  the item order of 115 is a different order and produces nonsense. The table
  is constant per profile. Careful with the complement: "no entry in record
  106" is **not** "not driven" — a 16-bit pair is driven on both halves while
  only its principal appears in 106 (POS-05), which is how COV-16's second
  prediction came out wrong.
  Its entries are **not** empty: 10 754 of 14 698 carry content (COV-03), and
  the one file where they are is *rig-c-bug*, which is BUG-01's erasure. Their
  four fields stay unnamed. **Moving one fixture's DMX address changes exactly
  three records — 115, 106 and 120 — and inside 120 it changes nothing but the
  record-level `f4` (COV-29).** No entry moves, so the per-entry fields belong
  to the profile and not to the patch; the moved fixture's entry is empty,
  though, so a block that shifted would not show at this resolution. **Moving
  the address back restores every record byte for byte**, the record-level
  `f4` included: it is a pure function of the ordering, with no hysteresis —
  unlike record 125's mask, which accumulates (§7.2). `f4` is 1 everywhere; `f5` is 1 or 2 and pairs with
  an `f6` that comes as `(n, n−1)`, which looks like a coarse/fine couple and
  matches `110.f5` on 954 of the 2081 entries carrying it — a shape, not a
  reading.

**Refuted**: record 115 does *not* have a fixed 20 slots (10/15/20/22 across the
four rigs, always `max(105.f5) + 1`); the "20" in earlier notes was a
coincidence of one rig having 20 fixtures. Record 155 is *not* the DMX patch map
(§8).

### Record 120's count can outrun its content — **[observed]** (COV-32)

`120.f1` is the entry count on every file but one, where the device trimmed the
record from 221 entries to 215 and left `f1` at 221. Arithmetic says which side
is stale: **215 is exactly `Σ channel_count` over each fixture's profile**, so
the content was corrected and the counter was not. The surplus of six rode in
on the WTOOLS 2.0.2 session of COV-23 and sat in the same **eight** files that
carry the misplaced `116.f12` (§7.6) — one session, two artefacts, and a later
save repaired one of them without touching the other.

`comptes_de_tete` checks `f1 >= len` on record 120 and equality on the other
fourteen. **A writer must not derive the entry list from `f1`**, and a reader
that trusts it reads six entries that are not there.

### 7.1 The "115 arena" was a real DMX patch all along — **resolved**

Identity 8 holds everywhere, but the stronger claim that `115.f2` offsets tile
`[0, count(120))` exactly holds only for *rig-a* and its derivatives.
Elsewhere the offsets are stride-correct per profile but leave gaps and run past
the end of 120 — always staying below 512.

**That was the wrong frame.** `115.f2` is the **DMX start address**: the gaps are
unused address space in a 512-channel universe, which is why nothing ever
exceeds 512, and identity 11 shows the resulting windows never overlap — a
constraint a real patch must satisfy and an internal arena has no reason to.
The table below is a picture of how the operators patched their rigs, nothing
more.

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

### 7.2 Record 125's masks are fully derived — **[correlated 45/45]** — but they are groups, not categories

Nine items in every file. Item *i* carries `f4` = a 7-byte blob and `f8` = an
optional UTF-8 name (the operator's own group names). The first 6 bytes of `f4`, read
little-endian, are exactly:

```
mask[i] = OR over fixture rows r of (1 << 115[r].f3)   where category(r) == i
```

Verified bit for bit, 45/45, with four independent name↔content matches.

**The equality is refuted — [device-confirmed] (COV-26).** Reordering record
116 changes every profile index, and the firmware **ORs the new bit in without
clearing the stale one**: a slot whose two fixtures give `0x6` stores `0xe`.
The mask **accumulates**; it is not recomputed. `stored ⊇ derived` is what
holds, exact on all 747 corpus slots. A reader must not treat the mask as
derived — it can claim a profile the group does not have.

**Retracted 2026-08-26**: they are the **8 fixture groups A–H plus a ninth slot** for the fixtures that have no group pads. See the registry, *The fixture → group assignment*. `rig-b` groups two different profiles into slot 0, which a model-derived category could not do, and slots 0/1/2 are the DMX-measured groups A/B/C.

The fixture → group assignment itself is `115[r].f4`, mirrored on every patch
entry as `105[e].f6`: 817/817 fixture rows agree across 45 files, checked by
`groupe_fixture` in `tools/wpj_identities.py`.

**[observed]** The 7th byte of `f4` is `0x30` or `0x38` — a per-project constant
replicated on all 9 items. It flipped `0x30` → `0x38` **within one project** when
the device added a preset (F30-04). **That attribution is refuted (COV-22):** a
later save created a preset and left the byte alone, and a second project runs
`0x38` → `0x30` → `0x38` with its preset count constant at 82 — so it moves
without a preset being added, and it moves **back**, which no one-way flag does.
An earlier reading tied it to record 151 being populated: also withdrawn, since
15 of the 24 files at `0x30` carry a populated 151.

A **coupling** was published here and is **refuted (COV-32)**: the byte was read
as moving in the same save as the shared tail of record 161 (COV-21), on the
strength of the two projects that had more than one version. A third save moved
the tail — all three items, `176 → 240` — and left record 125 **byte-for-byte
identical**, its 7th byte `0x38` on all nine slots before and after. Two
coincidences were the whole basis and the third save separates them.

Both fields are unattributed again, separately, and nothing else falls with the
coupling because nothing was ever named on it. What survives from COV-22 is its
own refutation: the byte does not track preset creation, and it moves back.

### 7.3 Record 130 is the DMX IN mapping table — **[device-confirmed]**

The `Mappings` screen (mode 43) binds an incoming DMX channel to a controller
action. On a Mk1 only the DMX side exists; MIDI is Mk2 and higher. That table
is record 130, and every field below was written by the device in a
single-variable differential, then read back.

| Field | Meaning | Status |
|---|---|---|
| `f1` | number of entries | **device-confirmed** — tracked 9 → 13 on append and 13 → 12 on removal |
| `f2` | the **instance** inside the function, zero-based; **255** when the function has no instance | **device-confirmed** — group B wrote `f2 = 1`, the 5th preset wrote `f2 = 4`, BPM Tap and Wolf wrote 255 |
| `f4` | the **function** targeted | **device-confirmed** — see the table below |
| `f5`, `f6` | the DMX IN channel, zero-based, as **two bytes**: `channel0 = f5 × 256 + f6` | **device-confirmed** — CH300 wrote (1, 43), CH512 wrote (1, 255) |
| `f7`, `f8` | 1 everywhere, never moved | **no name** |

Functions measured, each by the entry the device created when that item was
selected on the `Mappings` screen. MAP-09 took the last ten in a single save:
each was given a distinct channel, so the channel labels its own entry and no
intermediate state had to be preserved.

| `f4` | Function | Instance | Category on screen |
|---|---|---|---|
| 20 | group dimmer | the group, 0–7 | Group Dimmer |
| 27 | MAIN dimmer | 0 | Group Dimmer |
| 70 | a specific preset | the preset index | Preset |
| 70 | Select Preset | 255 | General |
| 82 | a preset page | the page, 0-based | Preset Page |
| 10 | Wolf | 255 | Flash |
| 11 | Strobe | 255 | Flash |
| 12 | Blinder | 255 | Flash |
| 13 | Speed | 255 | Flash |
| 14 | Blackout | 255 | Flash |
| 15 | Smoke | 255 | Flash |
| 17 | BPM Tap | 255 | Flash |
| 78 | Jump Preset | 255 | General |
| 78 | Previous Preset | 1 | General |
| 78 | Next Preset | 2 | General |

That is the whole screen: fifteen functions across five categories, and no id
is inferred from a neighbour. The `Flash` run 10–15 is contiguous but **BPM Tap
sits at 17, not 16** — the gap is real, and it is why the sequence was measured
rather than extrapolated.

**A function id does not identify an entry on its own.** `f4 = 70` is carried
by both a specific preset and `Select Preset`; `f4 = 78` by all three preset
navigation actions. The identifying key is the **pair** `(f4, f2)`.

**`f2 = 255` means "no numbered instance".** It covers the seven flash keys and
also `Select Preset` and `Jump Preset`, where the incoming DMX **value** is
what picks the preset. `Previous`/`Next Preset` carry 1 and 2 under the same
`f4`; nothing carries 0 there, and why is not measured. `MAIN` carrying 0 rather
than 255 is the other unexplained instance — it is the one factory entry among
the non-instanced functions.

**`f4` is the function, not the screen's category.** BPM Tap and Wolf both live
under the `Flash` category and carry different `f4`. The five categories the
screen offers are a display grouping and are not stored at all.

**An unmapped function has no entry.** Removing a mapping deletes its line and
decrements `f1`; there is no sentinel value to recognise.

**The order of the entries carries no meaning.** Two reorders were observed in
eleven saves, neither caused by the entry that had just been edited, and no
reading survives them. An entry is keyed by `(f4, f2)` and never by its rank.

**Duplicate channels are allowed.** Group A was put on CH7 where group G
already sat; the device kept both, and a value on that channel drives the two
together. No uniqueness is enforced by the firmware, so none is enforced here.

### Why it looked inert for so long — **[observed]**

130 was byte-identical in the first 51 files of the corpus, which is what made
it read as "no project data". The factory table is the **identity map** — groups
A–H on channels 1–8 and MAIN on channel 9, confirmed on the device's own screen
— and no operator had ever changed a mapping. Item *i* carrying `f6 = i` was the
channel, not a slot index, and the coincidence hid the field.

`f5` stayed invisible for the same kind of reason: every channel ever seen was
below 256, so the high byte was always zero and therefore omitted. It only
appeared when the operator was asked to push the encoder to its ceiling.

### Written back, and accepted — **[device-confirmed]**

MAP-06: group D moved from CH4 to CH200 by editing the file alone — one entry's
`f6` from 3 to 199, +1 byte, record 130 the only payload record touched, SHA-1
recomputed, all identities passing before upload. Deployed, and the controller's
`Mappings` screen displays **CH200**. The table is writable, not just readable.

MAP-08 closed the rest of it. A file carrying the factory table was deployed
over a device state that held thirteen entries in a different order: the
controller kept **every record byte-identical**, so writing the table also
covers **deleting** entries and **choosing their order** — the device
renormalises nothing.

MAP-08 and MAP-10 close the rest. A file carrying the factory table was
deployed over a device state that held thirteen entries in a different order,
and the controller kept **every record byte-identical** — so writing covers
**deleting** entries and **choosing their order**, and the device renormalises
nothing. MAP-10 then deployed ten entries **created by our own encoder**, on
channels the controller had never written: the screen shows all ten on the
right functions, and the read-back is again byte-identical.

Writing the table is therefore device-confirmed on all four operations —
create, modify, delete, order — with byte-level fidelity, not merely a file the
firmware tolerates.

**The bytes are part of the contract.** The controller emits an entry's fields
in ascending field number and never emits a zero-valued field; a writer that
decodes to the same map but lays the bytes out differently is *semantically*
right and still wrong, because the next diff against a device-rewritten file
becomes unreadable. That defect was real in this repository's own writer and
was only caught by comparing bytes rather than decoded maps.

---

## 7.4 The fixture → group assignment — **[correlated 45/45]**

`115[r].f4` is the fixture's **group index**, absent meaning 0 = group A, and
`105[e].f6` repeats it on every patch entry of that fixture. The two agree on
**817/817 fixture rows across 45 files**.

Record **125**'s nine items are the eight groups **A–H plus a ninth slot** that
collects fixtures with no group pads — foggers, sparks — and `125[i].f8` is the
operator's own name for the group. Its `f4` is the OR of `1 << 115[r].f3` over
the group's fixtures, a **profile** mask, which is why the record reads as
derived and why §7.2's "nine categories" was wrong: `rig-b` puts two different
profiles in slot 0, which a model-derived category cannot do.

## 7.5 Record 106 — the channel roles — **[correlated 45/45]**

Each `106` entry targets a channel of its fixture's profile through
`106.f2 − 115.f2 + 116.f3`. Its fields then read:

| Field | Meaning |
|---|---|
| `f2` | absolute 0-based DMX channel |
| `f4` | the channel's **role in the W1 engine** |
| `f1`, `f3` | the **DMX window** the role drives — one of the channel's `111` ranges on 4188 of 6070 entries |
| `f5`, `f6` | the fixture's **travel limits**, per fixture and per axis — the `MIN`/`MAX` of the `FIXTURE LIMITS` screen, as `v/255` (COV-24). **Invert pan swaps the two.** **Absent means 0, not "unset" (COV-35):** a fixture whose four limit fields are all absent reads `0 %` four times on that screen and is **pinned** — `min == max == 0` collapses the range, and it emits 0 on both axes whatever position is recalled. A reader must not fill an absent limit with the full range. |

**`110.f4` is the channel type the `FIXTURE BUILDER` shows — [device-confirmed]
(COV-25)**, name for name, 16 of 16 on a moving head, the two `Generic` values
landing on the entries the W1 labels `Color Effect` and `Reset`. **Do not cross
it with `ssl2.TYPE_CANAL`:** the two agree up to 27 and diverge after — a
`RGBAW UV` par's three extra colours are 31, 32, 33 here, where the `.ssl2`
table reads 31 White, 32 Gobo Bounce, 33 Framing Rotation. PROFILE-02
established that table for profiles read off the **controller**; it does not
transfer to the file. `extra1/2/3` below stays the right name until something
measures them.

Seventeen roles, in bijection with the profile feature `110.f4`:

```
0 dimmer(7)  1 pan(1)   2 tilt(2)   3 red(25)  4 green(26)  5 blue(27)
6 extra1(31) 7 extra2(32) 8 extra3(33) 9 shutter(15) 10 strobe(15)
11 colour wheel(5)  12 gobo wheel(8)  14(22)  15(16)  21(20)  22(19)
```

**This is the field a show generator needs**: it answers "which DMX channel
carries this fixture's red" without inferring anything from channel order.

## 7.6 Records 110 and 111 — channels and ranges — **[correlated]**

- `110.f5` is the **index of the channel this one belongs to**: a principal
  channel points at itself, a **fine** channel at its coarse half, and the
  pointed channel always carries the same feature. 1581/1581, no exception. A
  16-bit pan is emitted without guessing byte order or adjacency.
- `111.f1`/`f2` are a range's **first and last DMX value**. Every channel falls
  into one of three cases with nothing left over: **1454** whose ranges tile
  `[0, 255]`, **83** unassigned (no `f4`, one *empty* `111` item), and **44**
  carrying an isolated `{f1: 255, f3: 41}` on `110.f4 = 18`.
- The wire **order** of a channel's ranges is free: the firmware accepted a
  non-monotonic gobo-wheel list and used it as the pad order (SORT-01,
  §3.4). Device-written files happen to be DMX-sorted; nothing requires it.

### `116.f12` carries channel labels — of the wrong profile — **[observed]**

`116.f12` is a repeated **UTF-8 string**, and the only text in the file that
had never been opened: `Pan`, `Tilt`, `Pan/Tilt Speed`, `Strobe`,
`Color Effect`, `Reset` — labels of the `FIXTURE BUILDER` kind. It exists in 8
corpus files, one save lineage, and holds two arrays.

**They are not the channel names of the profile that carries them.** The array
on a 10-channel par — whose own `110.f4` types are *Dimmer, Red, Green, Blue,
extra1, extra2, extra3, Shutter, Generic, Speed* — names `Pan` at index 2.
Of the 28 offsets into record 110, **exactly one** fits all five non-empty
entries: **21**, the `116.f3` of the 16-channel moving head COV-25 measured.
`Color Effect` and `Reset` are name for name the two labels that screen prints
on its two `Generic` channels, which anchors the identification on a
device-confirmed reading.

The rule closes all five profile items with no exception: item *i*'s `f12[k]`
names the **moving head's** own channel `offset_110(i) + k`. WTOOLS 2.0.2 cut
one profile-local array with each item's **global** offset into record 110 —
§7.5's own warning, committed by the vendor's editor in the other direction,
which is why the profile the names belong to carries none of them.

**Nothing is named.** The one established fact is the negative: `f12` is not
the carrying profile's channel names, and a reader that trusts it gets
another profile's labels. Eight derived files of one project and one session
cannot take this past `observed` (COV-30).

## 8. Type 155 — the 4 FX sequences — **[device-confirmed]**

`field 1` = 4, then four `field 5` items:

```
f1 = 8        groups per step
f2 ∈ {1,2}    sequence flavour
f3            step count, 1…16
f4            128 PACKED VARINTS — not a byte array
```

`f4` is packed varints, which is why its byte length varies: 128 bytes in most
files, 133 when five of the values need two bytes. Reading it as raw bytes works
by accident until one value exceeds 127.

**The layout is step-major: 16 steps × 8 groups**, index = `step × 8 + group`,
group 0 = A. Reading it the other way round produces ragged nonsense.

**`f2` says which engine the sequence belongs to, and that sets the value's
domain — [validated] (FX6-05).** The record holds *both* sequencers:

| `f2` | Engine | Value | Domain |
|---|---|---|---|
| **1** (item 0) | **Move** | position index into that group's own record-150 palette | 0–19, plus **255** = no position at that step |
| **2** (items 1–3) | **Beam** — the three `FX Seq` of the beam enum | a **4-bit mask** over the group's four segments | **0–15** |

Eight groups × four segments = the manual's "up to 32 beam selections". The
16 × 8 shape is shared; only the domain differs.

Confirmed against the device twice. For **move**: the operator photographed the
SEQUENCER screen at every step from 1/16 to 16/16 and the decoded array predicts
each screen exactly, including the case where one index means a different named
position in each group — because each group indexes its own palette. For
**beam** (FX6-05): ticking segments 1 and 4 on group A of step 1 and saving the
project — **no preset capture** — changed exactly one payload byte in the whole
file, `15` → `9`, that is `0b1111` → `0b1001`, at item 1 index 0.

An earlier revision read *all four* items as position indices. That
generalisation was wrong where the original measurement was right: it had only
ever exercised the move sequencer. `f2` was named "sequence flavour" and never
opened.

`flavours_155` in `tools/wpj_identities.py` checks the split and both domains on
every file.

`f3` is the step count: SHIFT + a step pad sets it, and SHIFT + step 1 took it
from 16 to 1.

**Refuted**: 4 × 128 = 512 is *not* a DMX universe. The DMX patch is record 105
(identity 5 above).

---

## 8.1 Type 151 — detached-fixture offsets — **[device-confirmed]**

A firmware feature detaches a fixture from its group and positions it
independently. Each detached fixture gets one `151` entry, and each position
slot of record 150 points at its own slice:

```
150[slot].f2 = offset into 151      150[slot].f1 = length
```

The slices are contiguous from 0 — the same (offset, length) couple as
`105.f4`/`f7` into 106 and `116.f3`/`f2` into 110.

**They no longer tile `[0, count(151))` — [refuted] (COV-32).** That held on
all 90 corpus files and fell to a save the device wrote on 2026-09-01: group
A's slots claim **6** entries where record 151 holds **1**, the three slices
still contiguous. **Which side is stale is not settled** — unlike record 120's
surplus in the same file, no arithmetic decides it, and the discriminator is
one photograph of the `ALL POSITIONS` page. `tranches_151` now checks only what
survives, `referenced >= present`: no entry of 151 is orphaned. **A reader must
clamp a slice to the record rather than trust its length.**

| Field | Screen | Encoding |
|---|---|---|
| `151.f1` | — | **fixture index**, absent = 0 |
| `151.f2` | `FOCUS OFFSET` | signed, `(v − 32768) / 32767`; **[hypothesized]** relative to `165.f32` rather than absolute — see below |
| `151.f3` | `PAN OFFSET` | signed, same |
| `151.f4` | `TILT OFFSET` | signed, same |

**[hypothesized]** (FW-02) `FOCUS OFFSET` is **relative to the group's focus
value**, `165.f32`, not absolute: firmware 2.0.5 states "Position focus values
are now applied as a focus offset, relative to the focus value set on the Gobo
screen." A writer that sets both must **compose** them. Never measured here —
the position model below is device-confirmed on **pan and tilt**, and the focus
offset has no DMX capture behind it.

### The position model, end to end — **[device-confirmed]**

**The `PAN` term was missing until 2026-09-01 (COV-36).** The pan line above
ignored the slot's own `PAN` and scored 11/12; the wire gives a fraction of
**0.45995** where `PAN + ramp − 0.5` gives **0.45999**, under half a DMX unit
at 16 bits. The old formula is the special case `PAN = 50 %`, which is where
both measured captures sat — re-scored under the new rule they are unchanged,
the one known miss included. Nothing had ever exercised a slot away from
centre. **`n` counts the group's fixtures including any that are not
patched**: at 5 instead of 6 the same reading misses by 136 DMX units.

Everything a recalled position emits is computable from the file:

```
pct_group(k) = PAN + ramp(FAN, k, n) − 0.5               pan; k = rank in group
ramp(FAN,k,n)= (1 − FAN) + k × (2·FAN − 1) / (n − 1)     the FAN spread
pct_group    = TILT                                       tilt
pct          = clamp(pct_group + offset, 0, 1)            offset from 151
borne16(f)   = f / 255 × 65535                            f = 106.f5 or f6
DMX16        = borne16(f5) + pct × (borne16(f6) − borne16(f5))
coarse       = DMX16 >> 8        fine = DMX16 & 0xFF
```

`FAN`, `PAN` and `TILT` come from record 150 as `stored / 65536`. Measured over
four DMX captures and 24 predicted channels: **tilt exact everywhere**, pan
exact everywhere but once. Detaching a fixture does **not** remove it from the
fan; the offset stacks on top of the group value and is clamped.

## 9. Prefix bytes 20–63

| Offset | Content | Status |
|---|---|---|
| 20–35 | 16-byte project UUID = the `wlinkData` file name | correlated |
| 36–39 | constant `15 2b 10 c0` in 45/45 | observed — container magic |
| **40–47** | **little-endian uint64 version**, incremented by one per save | **correlated** |
| 48–49 | constant `01 f9` in 45/45 | observed |
| 50 | **schema version**: 8 (×1), 10 (×11) or 11 (×33) | correlated 45/45 |
| 51 | constant 0 | observed |
| 52–63 | constant `02 be e8 1c a2 6c cb 54 6d c7 b6 ec` in 45/45 | observed |

**This corrects an earlier claim that byte 40 is a save counter.** Byte 40 is the
*least significant byte* of a 64-bit version field the firmware increments by one
per save; the observed `62 → 66` across four saves is +4 on that LSB.
**Falsifiable consequence:** after enough saves the LSB wraps, offset 41
increments and offset 40 drops to `0x00`. **A writer must treat 40–47 as one
64-bit integer, not a byte, or it will corrupt the version at the wrap.**

**[device-confirmed]** Bytes 20–35 are *not* an import identity key: creating a
new project without touching them works (ACC-01).

**Byte 50 gates the schema.** `165.f32`–`f35` are absent from the one schema-8
file and present in all 44 schema-10 and schema-11 files. Schema **11** is this
firmware's. **[observed]** (FW-02) The vendor changelog dates `f32`–`f35` to
firmware **2.0.5**, which dates **schema 10 to firmware 2.0.5** — the first date
attached to a schema number of this format, and a bound worth having: a
schema-10 project was written by a 2.0.5 or newer. Record 151 is present at
**every** schema and populated at 8, 10 and
11 alike; what correlates with schema is only its **zero-length** form, in the
same 9 files that also lack record 160 — the rigs that never detached a
fixture. A writer must not raise the byte without emitting what the
schema requires. Across seven consecutive saves of one project **only byte 40
moved**; 21 of the 44 prefix bytes take the same value in every corpus file.
Two of those 21 are the high bytes of the version counter, so "constant" there
means "not yet reached", not "carries nothing".

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
5. **Edit, do not synthesize — with one measured exception.** Prefer donor
   entries for anything you do not fully understand; that is caution about
   unknown fields, not a measured constraint. The exception is record 165: a
   preset **is** added by appending a well-formed `f5` entry — see §10.1.

### 10.1 Adding a preset — **[device-confirmed]**

An earlier revision of this document said the device deletes preset entries it
did not create. **That is retracted**: the measurement behind it (FLASH-09) was
a mis-attributed download, and PRESET-01 showed a cold open with the added
entries intact. What a generator must respect instead, all measured:

| Rule | Evidence |
|---|---|
| Append an `f5` entry with `f19` = `id = (page − 1) × 20 + (slot − 1)` | PRESET-01, PRESET-07 |
| **Names are capped at 19 UTF-8 bytes.** A 23-byte name does not get truncated — the whole project **refuses to open** | PRESET-05, and no name in the 3697-preset corpus exceeds 19 bytes |
| **Id gaps are fine.** A sparse page loads; the gap was never the fatal variable | PRESET-07 |
| Maintain no count: `165.f1` is not one (§5) | F30-04 |
| The project is not live until a manual `Main Menu → Projects` open. `RESTART` does not substitute | FLASH-08, PRESET-07 |

The failure mode is loud and total — "Error opening project", not a silently
dropped entry — which makes this one of the safer things to get wrong.

### The live copy is not the file — **[device-confirmed]**

Everything a recall measures, it measures on the controller's **live copy**, and
that copy diverges from the stored file in silence. Three generated cues were
identical field by field *in the file* — re-read twice, byte for byte after
storage — and one of them was no longer identical *inside the device*: its `f17`
read `[255]×8` live where the file said `[0, 120, 0, 0, 0, 0, 0, 0]`, and its
`f28` had moved on group A. That divergence produced a perfectly reproducible
anomaly — three recalls across two independent series — which pointed at `f31`,
a field that had nothing to do with it (GEN-03). **Reproducibility protects
nothing when it is the state, and not the measurement, that is stable.**

The only way to see the divergence is a controller save followed by a download
and a field-by-field diff against the bytes actually deployed.

**Consequence for a generator: a cue meant for measurement must carry
`LIVE EDIT` off — `f10` bit 4 set (§5.3).** Our cues left it on, which is what
lets a gesture at the panel write into them between deployment and the shot.

### What a patch-editing writer must recompute

Record **125**'s masks are fully derivable from 105 + 115 + 116, and the offsets
in `116.f3`, `110.f3`, `115.f2` plus the size of 120 are all determined by the
profile channel counts (§7). A writer that changes the patch must **recompute**
them, not preserve them. A writer that does not touch the patch can leave all six
records untouched — which `tools/wpjlib.py` does by construction.

### A controller-side save is not byte-preserving — **[device-confirmed]**

Saving on the W1 re-serialises some records into the firmware's canonical form.
Observed: type 115 shrank 329 → 287 bytes as its 20 items each lost `f6` and `f7`
and gained a sequential `f9`; `f7` never came back. The same canonicalisation ran
again on a file **our** writer produced (GEN-03): the twenty items dropped `f6` =
94 and `f7` = 187 — identical on all twenty — for a sequential `f9`.
**That `f9` is not a position index — [correlated] (COV-15).** It is a
contiguous ascending run in 68 of 80 corpus files, but the run does not always
start at 0: a six-fixture project carries **20…25**, which no index into six
entries can do. A creation counter fits; nothing here establishes it, and the
field keeps its neutral key. **[observed]**; nothing is concluded
from it beyond "the firmware's writer migrates this record". Consequence: **a round-trip
through the device cannot be verified by file hash.** Differential experiments
must compare record by record and expect canonicalisation noise. Record 165 was
long the happy exception, and it is **not** one for a file we wrote: the same
save rewrote `165.f1`, corrected `165.f16` slice 5 on the presets whose mask we
had inherited wrong, and emitted the four `STATIC GOBO` tables on all 88
presets (§5, GEN-03).

### The USB serial link is not error-free — **[device-confirmed]**

Two of four `GET_PROJECT` transfers of a 43 KB project failed in one session: one
produced an unparseable body, one returned the correct length with wrong bytes
*and* a SHA-1 header that did not match its own body. **Never trust a single
download.** Accept a transfer whose SHA-1 header verifies, otherwise require two
identical consecutive transfers.

**Uploads are corruptible too.** A 43 KB `SET_PROJECT` was refused by the
firmware with its own message — `invalid wire_type` — and succeeded unchanged on
retry. So a writer must verify in both directions: read the project back after
storing it, and be prepared to retry a rejected store rather than treating the
rejection as a verdict on the file.

### 10.2 Driving the device over USB — **[device-confirmed]**

`SET_PRESET` (41) and `SET_MODE` (39) **do not carry protobuf**. The firmware
reads **`payload[0]` as the index**, and the second byte is not read at all
(RAW-01, RAW-02).

This is the single most expensive misreading in the project's history, and it
is worth stating as a mechanism rather than a conclusion: every payload sent
before it was `[tag, value]`, so the device was reading our **tag** byte —
`f1` → 8, `f2` → 16, `f3` → 24. That is exactly why each "field" produced one
appearance and never a reaction to the value. RECALL-01 and RECALL-02 measured
correctly; their *reading* — "the event addresses nothing" — is replaced by "we
had never sent the index".

| Statement | Evidence |
|---|---|
| The byte is the **id**, not the entry position | RECALL-03 |
| An **absent** id is a strict **no-op** — no floor, no clamp, no fall-back, no modulo. Proven above the highest id, inside an interior hole, and with bit 7 set | RECALL-04, RECALL-05, RECALL-06 |
| A **present** id above 127 is recalled exactly, bit 7 and all | RECALL-06 |
| The reachable domain is the panel's own, **0–199**; 200–255 is unprobed and is not sent | RECALL-06 |
| `SET_MODE` sets the **reported** mode every time; the panel does not always follow | SCREEN-01, SCREEN-02 |
| The longer events stay protobuf | throughout |

Two readings stay **refuted as written**, both describing a protobuf the
firmware never parses: SETP-01's `f1` = id, and PRESET-07's `f2` = entry
position clamped to the last entry. PRESET-07 was wrong on both halves — not
that field, and not a position. Its **file-side** results are untouched: the
`f19` id formula, gaps tolerated, and the manual open.

**No reachable event reloads the live copy** (RELOAD-04). A WTOOLS push does
not, `store` + `RESTART` under the same UUID does not, and only a manual open
on the panel does. The screen that performs it — mode 26, *main menu → Open* —
**is** reachable remotely, which is as close as the protocol gets.

#### The mode map — firmware 2.0.18 — **[device-confirmed]**

Measured by polling `GET_SETTINGS` while the operator walked the front panel,
returning to HOME between steps so the capture self-synchronises on mode 0
(MODE-01). **Zero writes.** Names are the vendor's own `WM_MODE_*` identifiers;
where firmware 2.0's editor renamed one, both are given. The raw capture is
[`research/raw/mode-01-session.jsonl`](research/raw/mode-01-session.jsonl).

| Value | Reached by | Name |
|---|---|---|
| 0 | idle, `HOME` | `HOME` |
| 1 | `COLOR FX` | `COLOR` |
| 3 | `MOVE FX` | `MOVE` |
| 4 | `BEAM FX` | `BEAM` |
| 5 | `PRESET` | `PRESETS` |
| 7 | STATIC `COLOR` | `STATIC_COLOR` |
| 8 | STATIC `GOBO` | `STATIC_GOBO` → **`GOBO`** |
| 9 | STATIC `POSITION` | `STATIC_POSITION` |
| 10 | STATIC `LIVE EDIT` | `LIVE_EDIT` |
| 12 | SHIFT + a position pad | `POSITION_PICKER` → **`STATIC_POSITION_PICKER`** |
| 14 | STATIC GOBO → SHIFT + a gobo pad | `GOBO_EDIT` |
| 15 | LIVE EDIT → fixture grid → EDIT | `LIVE_EDIT_EDIT` |
| 16 | gear icon | `SETUP` — the main menu, parent of 17/19/23/25/26/43 |
| 17 | main menu → Fixtures | `FIXTURE_SETUP` |
| 19 | main menu → New, or Fixtures → ADD | `FIXTURE_SELECTION` |
| 21 | MOVE FX → sequence editor | `MOVE_SEQ` |
| 23 | main menu → DMX VALUES | `DMX_LEVELS` |
| 25 | main menu → Settings | `SETTINGS` |
| 26 | main menu → Open | `PROJECTS` — **modal**, escape with index 1 |
| 28 | `WOLF` key (chevrons) | `WOLF` |
| 29 | `STROBE` | `STROBE` |
| 30 | `SPEED` | `SPEED` |
| 32 | `BLINDER` | `BLINDER` |
| 33 | `BLACKOUT` | `BLACKOUT` |
| 34 | PRESET → magic wand | `HUNGRY_WOLF` → **`INTELLIGENT_PRESET`** |
| 36 | DMX VALUES → beam editor | `BEAM_EDITOR` |
| 41 | LIVE EDIT → SHIFT + one of the first three encoders | `LIVE_EDIT_MACRO_EDIT` |
| 43 | main menu → Mappings | `MAPPING` — **present on MK1**, operator-confirmed by toggling against the main menu with the back button |
| 44 | HOME → touch the tempo readout | `BPM` |

The legacy 0–38 numbering is **unchanged** in firmware 2.0.18: the three names
that vanished from the older SDK are renames at their original values (8, 12,
34), and the new modes live at 39–44.

Three of those are reachable only by raw index, and the way they behave is why
`wolfmix.py` puts raw indexes behind `--experimental`:

| Value | Behaviour | Name |
|---|---|---|
| 39 | the **pads** light what the operator reads as the Move FX sequencer's position picker, and the **screen stays on HOME** | `SEQ_POSITION_PICKER`, **[hypothesized]** by elimination |
| 40 | **redirects to 42**, three times out of three | `FILE_BROWSER`, **[hypothesized]** by elimination |
| 42 | `USB STICK` — import/export of project, fixtures and full backup. **Attempts a read on entry**, and with no medium (MK1 has no USB-A socket) shows "error reading project" | `USB_STICK`, operator-identified on screen |

Two consequences worth stating plainly. **An index probe is not a neutral
act** — mode 42 starts an action on entry. And the index → mode identity is
**not** universal: 0, 5, 16 and 26 are exact, 40 → 42 is not.

`GROUPS` (24) was never reached: the A–D / E–H bank switch is SHIFT +
`BPM TAP`, which changes no mode. `SMOKE` and a single `BPM TAP` change no mode
either.

#### The screen does not always follow — **[device-confirmed]**

The reported mode takes the value asked for **every time**. The panel does not.
Measured over nine sends, the operator reading the screen after each
(SCREEN-01, SCREEN-02, SCREEN-03):

| | Indexes |
|---|---|
| The screen follows | **1, 3, 4, 26** |
| The screen ignores it | **0, 5, 16** |
| Never tried | everything else |

**The target decides, not the screen you start from**: index 5 was inert from
HOME, from the modal Open, and from COLOR FX. Index 1 closes the modal Open
*and* opens COLOR FX, which confirms the escape noted for 26 and refutes "only
modals are pushable".

No mechanism is named — all six pages have a dedicated key or icon on the
panel, and the firmware moves **three** things independently: the reported
mode, the pad LEDs, and the screen. Mode 39 moves the first two and leaves the
third alone. Practical consequence: from the host you reach the three FX
engines and the Open page, and **you cannot get back to HOME** — that needs a
key.

---

### The output stream is a 25 Hz clock — **[device-confirmed]** (COV-34)

The controller ships one `DMX_PACKET` of **2048 channels** — the four universes
in natural order — every **40 ms**. Measured over three windows: 25.04, 25.04
and 25.01 fps, median arrival gaps of 40.023, 39.991 and 39.870 ms, and an
interquartile spread of **0.65 to 1.3 ms**.

**It is a clock and not an emission on change.** A 30 s window with the engine
static and `animatedChannels = 0` shipped 751 frames, and a second window with
a Move FX and a Colour FX running gave a rate **0.12 %** away from it. Nor is
it a faster stream decimated: the gap counts are 100.16 % and 100.03 % of an
exact 25.000 Hz clock, so no frame was lost, and the longest gap is twice the
median rather than twice a half-median — one delivery slot missed on the
**host** and caught up on the next.

**This is the USB cadence, not the DMX line.** The outputs were physically
unplugged and no receiver saw the wire. Whether the firmware clocks the line at
the same rate is untested here and must not be read into the number.

What it settles is the instrument: `dmx-envelope` is used as a differential
oracle throughout `research/`, and a window of N seconds is 25 N frames
whatever the engine is doing — which is what makes "did this change alter the
output at all" a fair question rather than a race with an animation.

## 11. Open questions

Only questions **nothing has answered**. A lead that closed is not listed here:
its result lives in the section it belongs to, and its history in the ledger.
Ten leads (L1–L5, L4′, L4″, L9, L10) were carried in this section long after
they closed, which made the list read as a research agenda when it was a
changelog.

| # | Question | What would settle it |
|---|---|---|
| ~~Q1~~ | **Closed 2026-09-01.** `165.f27` is the per-group position FADE in milliseconds (COV-10, §5.6). The route was COV-02 — the field is not zero everywhere, and the WTOOLS/panel split is what made a contrast reachable — then three points on one line. What remains is not this question but its **scope**: only group A is measured, because no fixture sits on the other seven. | — |
| Q2 | **`f4` bit 0**, set on the move and beam pages, clear on the colour page; bits 1, 5, 6, 7 are never seen outside 255. Under the permission reading, bit 0 is a fourth capability that movement and beam need and colour does not. | A preset composed at the panel on a rig where the candidates separate. Nothing in this corpus does. |
| Q3 | **`f16` slice 11** — non-zero and constant per project (2, 5 or 7), unmoved by every flash latch including the one that had `SMOKE` alone held. | It is not a flash key; nothing says what it is. |
| Q4 | **`f16` slices 3 and 4** — zero in every file and every experiment, with no key left to assign. COV-07 tried COV-02's author split on them: a WTOOLS 2.0.2 project leaves them zero too. | Provably empty, or empty in everything reachable from this panel **and from WTOOLS**. The second author has now been checked and adds nothing. |
| Q5 | **`102.f11`** — unattributed and inert across idle static output and with the blinder active, no UI control, no manual entry, present before firmware 2.0. | The search is **stopped**, not open-ended. Untried conditions, for whoever picks it up: strobe or smoke active, effects running, a second universe, MK2/MK3 hardware. |
| Q6 | **The `PRESET EDIT` screen's `COLOR` line.** It shows a named colour that is not the preset's `f31`, and no top-level scalar carries the pad index either. | Where that line reads from. |
| Q7 | **`beam.f5`** — absent on all 352 distinct presets and on both entries written during FX6-03. Hypothesized inert: a slot the shared FX schema carries and the beam engine does not use. | One capture where a beam control writes it, or a reason it never can. |
| Q8 | **Record 161** — three items, each a **packed array of exactly 188 varints** (COV-06). Not volatile, as this document long said: of the 564 values, exactly **6 ever differ**, and they are the same six in two unrelated projects (COV-21) — the **last value of each item**, which move together and to the same number (240 or 176), and the **first three of item 1**, which read as a little-endian **20-bit mask**, `0x0FFFFF` or `0`. The other 182 per item have not moved in 82 files, 13 projects, two authors. Its `f1` is 21, 15, 19 by item position; the record's own `f1` is 9 against 3 items, so it is not a count. FX6-05 removed the beam-sequencer hypothesis, the only one it ever had. | An attribution for any of the six. Three observed transitions of the tail (F30-04, COV-22's pair, and COV-32's `176 → 240` on a save the operator could not attribute) and one of the mask (FX6-02) are not an attribution, and a 20-bit mask has too many candidates here — a palette page, a preset page and a Live Edit page are all 20. It has a **schema** since 2026-09-01 and that changes nothing here: the schema names `items` and types the three arrays as packed, so a diff points at which of the 564 values moved instead of at 190 bytes of hex. The values themselves keep neutral keys and count `partial`, not `read`. |
| Q9 | **Which of the two paths the panel follows.** `SET_MODE` and the front-panel keys move the device differently (SCREEN-03), and nothing has measured which one the displayed screen tracks. | A capture where the two disagree and the panel is watched. |
| Q10 | **The colour engine's `f2` at 150 and 200.** `f2` is the fade, and above 100 it is move's `Flick` — but the manual gives colour no `Flick`. | The residual of L9, and the only part of the FX submessage that does not read cleanly. |
| Q11 | **Variants B and C below the top level.** EXP-06 aligned profiles, patch, preset names and the FX banks against a variant-A twin, which is far more than "only the top level is mapped" — but it is one pair, and the campaign was never run out. | Its own campaign, on more than one pair. |
| Q12 | **Transposition off this rig.** §3.4's palette rule, and most of the static layer, were measured on **one** group of **one** profile. Nothing contradicts the general rule; nothing tests it either. | A second rig. |

## References

See `PROVENANCE.md` for sources, licences, and what may be reused from where.
Detailed experiment write-ups, with hashes and dates, live in `research/`.
