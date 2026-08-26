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

Measurement base: W1 Mk1 (serial withheld), firmware **2.0.18**, WTOOLS **1.6.3**,
macOS. Corpus hashes in `corpus/SHA256SUMS`.

**On file counts.** The measurement corpus holds **27 variant-A files**, but only
**4 are independent rigs** (*rig-a* 10 fixtures, *rig-b* 15, *rig-c* 20,
*rig-c-bug* 22 = a re-patched *rig-c*). The rest are derived: files written
by our own writer from *rig-a*, and controller saves of one copy of
*rig-c*. An identity holding on all of them is strong enough to **kill** a
hypothesis; it is not by itself enough to call anything device-confirmed.
Counts written "27/27" below are re-checked by `make check` on whatever corpus
is present.

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
| 105 | 114–351 | 10–27 | **patch index**: one entry per DMX block, slicing record 106 | correlated (§7) |
| 106 | 600–2614 | 50–201 | one entry per **mapped** channel, `f2` = absolute DMX channel | correlated (§7) |
| 110 | 210–775 | 22–80 | flattened channel table of all profiles | correlated |
| 111 | 347–1526 | 45–201 | flattened range/capability table, indexed by 110 | correlated |
| 115 | 116–409 | 10–22 | **fixture instances** | correlated (§7) |
| 116 | 162–334 | 3–7 | **fixture profile catalogue** | correlated |
| 120 | 532–1199 | 86–258 | flat per-fixture-channel value table | correlated |
| 125 | 111–137 | **9** | **the 8 groups A–H + a 9th slot**: name + profile bitmask | correlated (§7.2) |
| 130 | **102** | **9** | byte-identical in 27/27 files | observed — no project data |
| 135 | 140–145 | **16** | the 16 ColorFX palette pads (RGBWALU) | correlated |
| 140 ×8 | 182–189 | **20** each | **static COLOUR palette**, one per group A–H, `f2` = group 0…7 | **device-confirmed** (§3.3) |
| 145 ×8 | 40–159 | **20** each | **static GOBO palette**, one per group A–H, `f2` = group 0…7 | **device-confirmed** (§3.4) |
| 150 ×8 | 483–491 | **20** each | **static POSITION palette**, one per group A–H, `f2` = group 0…7 | **device-confirmed** (§3.2) |
| 151 | 0 or 64 | 0 or **4** | 4 × three 16-bit values centred on 32767 | observed |
| 155 | 562–563 | **4** | **4 FX sequences**, 8 × 16 grid + step count | correlated (§8) |
| 160 | 393–542, **optional** | 8–11 | named macros | correlated |
| 161 | 599–604 | **3** | 3 × ~190-byte blob, volatile | observed |
| 165 | 26219–29831 | 80–82 | preset container | correlated (§5) |

160 is the only optional record: 40 records without it, 41 with.

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
  f3  FAN            unsigned, value = percent × 65535
  f4  FOCUS OFFSET   signed, 32768 = 0 %, 65535 = +100 %
  f5  name           UTF-8, absent when the slot is empty
  f6  PAN            unsigned, percent × 65535
  f7  TILT           unsigned, percent × 65535, absent = 0
  f8  CROSS          [hypothesized]
```

Read off the device's own edit screen (SHIFT + a position pad shows PAN, TILT,
FOCUS OFFSET and FAN | CROSS as percentages), on slots where the four values
disagree.

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

The 20 pads are named on screen (Amber, Lime, Cyan, UV, Pink, Red, …) but **no
name is stored in the file** — the labels are firmware constants tied to the
slot index, unlike record 150 where `f5` holds a per-slot name.

Grid layout, **[correlated]** by transposition from the type-145 measurement:
4 columns × 5 rows, filled column by column, top to bottom.

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
| `f28` | position index per group A–H, 8 packed varints, indexes type 150 | correlated |
| `f29` | **gobo index per group A–H**, 8 packed varints, **0-based** into type 145, **255 = none and it clears the channel** | **device-confirmed** (§5.1) |
| `f30` | **static-colour `PATTERN` per group A–H**, 8 packed varints, 11 modes | **device-confirmed** (§5.1) |
| `f31` | **static colour: 20 bytes = 160 bits = eight 20-bit pad masks**, one per group A–H | **device-confirmed** (§5.1) |
| `f17` | dimmer per group A–H, packed, default `[255]×8` | hypothesized |
| `f8` / `f24` | Color FX / Move FX active flag (packed, `[0]` or `[255]`) | correlated |
| `f4` | content mask (255 full, 8 colour, 17 beam, 5 move) | hypothesized |
| `f16` | ~13 varints, FX-bank masks per group in complementary pairs | hypothesized |
| `f11` | 500 / 2000 / 4000 — fade time in ms? | hypothesized |
| `f10` | factory library version? | observed |
| `f32`…`f35` | per-group arrays added at schema 10, defaults `50 / 0 / 100 / 100`; all zero in a project upgraded from schema 8 | correlated |
| `f9`=1, `f15`=1000, `f13`×6, `f18`, `f3`, `f7`, `f14`, `f23`, `f26`, `f27` | unknown, all zero on the measured rig | observed |

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
capture, in `research/wpj-format-registry.md`.

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

Screen order, left to right then down. Every bit is held by at least two
independent readings — six photographs of factory presets plus targeted writes —
and three of them by a single-variable differential. Corpus values re-read
sensibly: `51` = BEAM + GOBO, `61` = MOVE alone, `62` = COLOR alone, and nothing
above 62 in 2612 presets.

`f11` is **FADE in milliseconds**, absent = 0: 4000 → `00:04.00`, 2000 →
`00:02.00`, 500 → `00:00.50`, absent → `00:00.00`, all measured on screen.
`f15` is **HOLD**, 1000 ↔ `00:01.00`, consistent on six screens but never varied
— **[correlated]**.

### 5.4 `f16` — twelve 9-bit group masks — **[correlated 32/32]**

`f16`'s packed varints are the **bytes of a little-endian bit field**, the same
construction as `f31`. Cut at a stride of **9** — nine because record 125 has
nine slots — every slice is a group mask and the ninth bit is never set.

| Slice | Engine | Pinned by |
|---|---|---|
| 0 | **Color FX** | equals `color_fx_actif`, 2445/2446 |
| 1 | **Move FX** | equals `move_fx_actif`, 2446/2446 |
| 2 | **Beam FX** | active only on beam-page presets |
| 5 | static layer | 255 on every preset — **[hypothesized]** |
| 7 | strobe | active on `Fire!` and `Strobe`, and nothing else |
| 11 | per-project constant | never varies between presets |

The alignment tests itself: at a stride of 8, slice 1 would read 254 where
`move_fx_actif` says 255. Across 29352 slice extractions not one falls outside
`{0, 1, 2, 5, 7, 255}`.

**A writer must set both carriers.** `color_fx_actif` and `move_fx_actif`
duplicate slices 0 and 1; ACC-03b wrote one and not the other, and the firmware
followed `f16` — which is why its Color FX was ignored.

`165.f4` is a **permission mask over these engines**, not a content mask:
engine 0 active implies `f4` bit 3, engine 1 bit 2, engine 2 bit 4, on every
preset of every file. The implication is one-directional — a page may permit an
engine none of its presets uses.

### 5.5 `f18` = the Live Edit mask — **[correlated]**

The `LIVE EDIT` screen is 4 pages of 20 buttons; `f18` is 10 packed varints =
**80 bits**, one per button, the same byte-field construction as `f16` and
`f31`. Across the corpus only buttons **1, 2, 4, 5 and 20** are ever set — the
top of page 1 — out of eighty possible.

`f10`'s `LIVE EDIT` bit says *whether* a preset carries Live Edits; `f18` says
*which*.

### 5.6 Thirteen per-group arrays — **[correlated 32/32]**

Sweeping the whole format for fields that always decode to exactly 8 packed
varints returns thirteen, all in record 165:

```
f3  f7  f14  f17  f23  f27  f28  f29  f30  f32  f33  f34  f35
```

`f17` dimmers, `f28` positions, `f29` gobos, `f30` colour pattern are named. The
other nine are **known to be per-group** even where their meaning is not, which
rules out reading them as scalars. `f32`–`f35` appear at schema 10.

**[device-confirmed]** five of them are the **`STATIC GOBO` features**, measured
by setting all five on group A to distinct values and capturing them into a
preset:

| Screen | Field | | Screen | Field |
|---|---|---|---|---|
| `ROTATE` | `f14` | | `ZOOM` | `f34` |
| `FOCUS` | `f32` | | `IRIS` | `f35` |
| `PRISM` | `f33` | | | |

Their schema-10 defaults `50 / 0 / 100 / 100` on `f32`–`f35` read as Focus 50 %,
Prism 0 %, Zoom 100 %, Iris 100 %. `f3`, `f7`, `f23` and `f27` remain
unattributed.

These are **live state** until a preset captures them: a project save alone does
not write them, only `SHIFT` + tapping a preset does.

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

Three more, added once `105.f4` was corrected, and mechanically re-checked on
**27/27** files by `tools/wpj_identities.py`:

```
9.  the [f4, f4+f7) intervals of 105, sorted by f4, tile [0, count(106))
10. every 106 entry of a slice lies in [115[r].f2, 115[r].f2 + profile channels)
11. the fixtures' DMX windows are pairwise disjoint
```

Identity 10 fails immediately if slices are attached to the wrong fixtures, and
identity 11 has no reason to hold for an internal arena index — together they
are what pins `115.f2` to a real DMX patch.

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
- **105 = the patch index into 106.** `f1` = library fixture id, **stable across
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

**Refuted**: record 115 does *not* have a fixed 20 slots (10/15/20/22 across the
four rigs, always `max(105.f5) + 1`); the "20" in earlier notes was a
coincidence of one rig having 20 fixtures. Record 155 is *not* the DMX patch map
(§8).

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

### 7.2 Record 125 is fully derived — **[correlated 18/18]**

Nine items in every file. Item *i* carries `f4` = a 7-byte blob and `f8` = an
optional UTF-8 name (the operator's own group names). The first 6 bytes of `f4`, read
little-endian, are exactly:

```
mask[i] = OR over fixture rows r of (1 << 115[r].f3)   where category(r) == i
```

Verified bit for bit, 18/18, with four independent name↔content matches. So
**125 is the 9 fixture categories, not the 8 groups A–H**, and its masks are
recomputable from 105 + 115 + 116. Only `f8`, the user-editable category name,
carries information a writer must preserve.

**Retracted 2026-08-26**: they are the **8 fixture groups A–H plus a ninth slot** for the fixtures that have no group pads. See the registry, *The fixture → group assignment*. `rig-b` groups two different profiles into slot 0, which a model-derived category could not do, and slots 0/1/2 are the DMX-measured groups A/B/C.

The fixture → group assignment itself is `115[r].f4`, mirrored on every patch
entry as `105[e].f6`: 457/457 fixture rows agree across 27 files, checked by
`groupe_fixture` in `tools/wpj_identities.py`.

**[observed]** The 7th byte of `f4` is `0x30` in the *Porte* projects and `0x38`
in the rig-c family — a per-project constant replicated on all 9 items,
correlating with record 151 being populated.

### 7.3 Record 130 carries no project data — **[observed]**

102 bytes, 9 items, byte-identical in 18/18 files across 4 rigs with 3–7
profiles and 10–22 fixtures. Items 0–7 read `{f2 = i, f4 = 20, f6 = i, f7 = 1,
f8 = 1}`, item 8 reads `{f4 = 27, f6 = 8, f8 = 1}`. The 9-item shape matches
record 125's nine slots one-for-one and `f4 = 20` matches the pads-per-page
limit. **[hypothesized]** per-category factory defaults. Negative result worth
recording: **no differential experiment will be productive on 130** unless the
operator edits something category-related.

---

## 7.4 The fixture → group assignment — **[correlated 32/32]**

`115[r].f4` is the fixture's **group index**, absent meaning 0 = group A, and
`105[e].f6` repeats it on every patch entry of that fixture. The two agree on
**457/457 fixture rows across 32 files**.

Record **125**'s nine items are the eight groups **A–H plus a ninth slot** that
collects fixtures with no group pads — foggers, sparks — and `125[i].f8` is the
operator's own name for the group. Its `f4` is the OR of `1 << 115[r].f3` over
the group's fixtures, a **profile** mask, which is why the record reads as
derived and why §7.2's "nine categories" was wrong: `rig-b` puts two different
profiles in slot 0, which a model-derived category cannot do.

## 7.5 Record 106 — the channel roles — **[correlated 32/32]**

Each `106` entry targets a channel of its fixture's profile through
`106.f2 − 115.f2 + 116.f3`. Its fields then read:

| Field | Meaning |
|---|---|
| `f2` | absolute 0-based DMX channel |
| `f4` | the channel's **role in the W1 engine** |
| `f1`, `f3` | the **DMX window** the role drives — one of the channel's `111` ranges on 2643 of 3775 entries |
| `f5`, `f6` | the fixture's **travel limits**, per fixture and per axis |

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
  pointed channel always carries the same feature. 1100/1100, no exception. A
  16-bit pan is emitted without guessing byte order or adjacency.
- `111.f1`/`f2` are a range's **first and last DMX value**. Every channel falls
  into one of three cases with nothing left over: **944** whose ranges tile
  `[0, 255]`, **53** unassigned (no `f4`, one *empty* `111` item), and **29**
  carrying an isolated `{f1: 255, f3: 41}` on `110.f4 = 18`.

## 8. Type 155 — 4 FX sequences — **[correlated]**

`field 1` = 4, then four `field 5` items, each with `f1 = 8`, `f2 ∈ {1,2}`,
`f3 ∈ {2,4}` and `f4` = a 128-byte array.

**Refuted**: 4 × 128 = 512 is *not* a DMX universe. The DMX patch is record 105
(identity 5 above). The arrays are **8 groups × 16 steps**, four sequences, and
`f3` is a step count — it moved 4 → 16 when the operator touched the sequence
editor's STEP control.

---

## 8.1 Type 151 — detached-fixture offsets — **[device-confirmed]**

A firmware feature detaches a fixture from its group and positions it
independently. Each detached fixture gets one `151` entry, and each position
slot of record 150 points at its own slice:

```
150[slot].f2 = offset into 151      150[slot].f1 = length
```

The slices **tile** `[0, count(151))` — the same (offset, length) couple as
`105.f4`/`f7` into 106 and `116.f3`/`f2` into 110.

| Field | Screen | Encoding |
|---|---|---|
| `151.f1` | — | **fixture index**, absent = 0 |
| `151.f2` | `FOCUS OFFSET` | signed, `(v − 32768) / 32767` |
| `151.f3` | `PAN OFFSET` | signed, same |
| `151.f4` | `TILT OFFSET` | signed, same |

### The position model, end to end — **[device-confirmed]**

Everything a recalled position emits is computable from the file:

```
pct_group(k) = (1 − FAN) + k × (2·FAN − 1) / (n − 1)     pan; k = rank in group
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
| 36–39 | constant `15 2b 10 c0` in 18/18 | observed — container magic |
| **40–47** | **little-endian uint64 version**, incremented by one per save | **correlated** |
| 48–49 | constant `01 f9` in 18/18 | observed |
| 50 | **schema version**: 8, 10 or 11 | correlated 32/32 |
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

**Byte 50 gates the schema.** `165.f32`–`f35` are absent from the one schema-8
file and present in all 31 schema-10 and schema-11 files. Schema **11** is this
firmware's and is the one that carries the detach feature: every schema-11 file
has record 151. A writer must not raise the byte without emitting what the
schema requires. Across seven consecutive saves of one project **only byte 40
moved**; 24 of the 44 prefix bytes are constant in every file and carry no
project information at all.

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
- ~~**L2 — group-mask asymmetry.**~~ **Closed** (§5.4): `f16` is twelve **9-bit**
  group masks, not complementary pairs. The stride is nine because record 125
  has nine slots. Slice 0 equals `color_fx_actif` and slice 1 `move_fx_actif`
  exactly; slice 2 is the Beam FX, slice 7 the strobe.
- **L3 — record 102 `f5`/`f6`/`f11`.** Three fields at 100, three unassigned
  guide parameters, one save (§6). **Highest value per unit of effort.**
- ~~**L4 — static colour `f31`.**~~ **Closed** (§5.1): eight 20-bit masks, one
  per group A–H, confirmed at the bit level by a save carrying three different
  masks. The "4 repetitions" reading was cutting 160 bits into the wrong slices.
- ~~**L4′ — the preset content mask.**~~ **Closed** (§5.3), and it was never
  `f4`: the `PRESET EDIT` toggles live in **`f10`**, six bits, `1` = toggle
  **off**, in screen order `COLOR MOVE BEAM GOBO LIVE EDIT OTHER`. `f11` is
  `FADE` in milliseconds and `f15` is `HOLD`. `f4` turned out to be a
  **permission mask over the FX engines** (§5.4).
- ~~**L4″ — where the fixture → group assignment lives.**~~ **Closed** (§7.4):
  `115[r].f4` is the group index, absent = 0 = group A, mirrored on every patch
  entry as `105[e].f6`. It had been decoded all along under the name
  *category*. Record 125 is the eight groups plus a ninth slot, not nine
  categories.
- **L5 — MIDI mapping record.** The W1 accepts MIDI (preset select by note,
  group/master dimmers by CC, MIDI clock at 24 PPQN) and the map is learned per
  project on `WM_MODE_MAPPING = 43`, so it must live in the file. Not yet
  located. This is the gateway to live control.
- ~~**L6 — record 151.**~~ **Closed** (§8.1): the **detached-fixture offsets**.
  One entry per fixture positioned independently of its group, carrying
  `f1` = fixture index, `f2` = `FOCUS OFFSET`, `f3` = `PAN OFFSET`,
  `f4` = `TILT OFFSET`, all signed as `(v − 32768) / 32767`. `150.f2`/`f1` are
  the offset and length of each position slot's slice.
- ~~**L7 — the 115 arena.**~~ **Closed** (§7.1): `115.f2` is the DMX start
  address, and identities 10 and 11 pin it. There is no arena.
- **L8 — variants B and C.** Only the top level is mapped. A different
  serialisation of the same show; needs its own campaign.

---

## References

See `PROVENANCE.md` for sources, licences, and what may be reused from where.
Detailed experiment write-ups, with hashes and dates, live in `research/`.
