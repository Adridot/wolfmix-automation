# Corpus mining — static differential analysis of the variant-A `.wpj` container

Date 2026-08-25. Method: **static only**. No serial port, no controller, no
writes. Everything below is derived from files already in `corpus/`.
Status vocabulary as in `research/wpj-format-registry.md`:
`observed` → `hypothesized` → `correlated` → `validated` → `device-confirmed`.

Scripts used are throwaway (scratchpad); every claim is stated as an identity
that `tools/wpjlib.py` + `tools/wolfmix.py:protobuf_fields` can re-check in a
few lines.

## 0. Corpus actually usable

19 `.wpj` files parse as **variant A** (SHA-1 + TLV container):

| Group | Files | Independent? |
|---|---|---|
| `corpus/projects/00000000-…-cc21-….wpj` — *rig-a*, 10 fixtures | 1 | yes |
| `corpus/projects/00000000-…-cd21-….wpj` — *rig-b*, 15 fixtures | 1 | yes |
| `corpus/projects/rig-c.wpj`, `rig-c-bug.wpj`, `f2737ec3-….wpj` — *rig-c*, 20/22/20 fixtures | 3 | 3 revisions of one project |
| `corpus/experiments/ACC-0{1..6}/*.wpj` | 6 | **our own writer**, all derived from `cc21` |
| `corpus/experiments/FX-0{1,3,4,5,6}/*.wpj` — *WMX EXP format-lab* | 7 | 6 controller saves of one copy of `f2737ec3` |

Six files in `corpus/projects/` are **not** variant A and were parsed with
`tools/wpj_inspect.py` only: `386fbb63`, `4cf6b152`, `848d7dcf`, `8b6f612f`,
`ef8ba8f7` (variant B, SHA-1 + bare protobuf) and `f4a5d15f` (variant C, bare
protobuf, no SHA-1 header). They contain **no TLV records at all**, so they
contribute nothing to this analysis.

**Effective independent rigs: 4** (rig-a, rig-b, rig-c, and
rig-c-bug as a re-patched rig-c). Everything asserted on "18/18
files" below is therefore 4 independent rigs plus 14 derived files — good
enough to kill a hypothesis, not enough to call anything device-confirmed.

`corpus/experiments/FX-06/after-speed-half.wpj` appeared in the working tree
while this analysis ran; it is included and discussed in §3.1.

## 1. TLV record inventory

Every record has the same envelope: `field 1 varint = item count`, then
`field 5` repeated once per item. The exceptions are noted.

| Type | Size range (bytes) | Repeated items | Identification | Status |
|---|---|---|---|---|
| 101 | 12 – 20 | — | project name (`f1` UTF-8) | device-confirmed (ACC-01) |
| 102 | 16 – 22 | — | flash-FX settings, 6 keys | device-confirmed (FX-01…06) |
| 105 | 114 – 351 | 10 – 27 | **DMX patch**, one entry per patched block | correlated 18/18 |
| 106 | 600 – 2614 | 50 – 201 | one entry **per patched DMX channel** | correlated 18/18 (exact count identity) |
| 110 | 210 – 775 | 22 – 80 | flattened **channel table of all profiles** | correlated 18/18 (exact count identity) |
| 111 | 347 – 1526 | 45 – 201 | flattened **range/capability table**, indexed by 110 | correlated 18/18 (monotone index) |
| 115 | 116 – 409 | 10 – 22 | **fixture instances** (one per row of the fixture grid) | correlated 18/18 |
| 116 | 162 – 334 | 3 – 7 | **fixture profile catalogue** | correlated 18/18 (exact count + offset identity) |
| 120 | 532 – 1199 (575 in `rig-c-bug`) | 86 – 258 | **per-fixture-channel value table**, flat | correlated 18/18 (exact count identity) |
| 125 | 111 – 137 | **9** always | **the 8 groups A–H + a 9th slot** (§2.2, retracted and corrected 2026-08-26): name + profile bitmask | correlated 18/18 (mask fully derivable) |
| 130 | **102 always** | **9** always | 9 per-category records, **byte-identical in 18/18 files** | observed — carries no project data |
| 135 | 140 – 145 | **16** always | **the 16 ColorFX palette pads** (RGBWALU) | correlated |
| 140 ×8 | 182 – 189 | **20** each | 8 pages × 20 **static-colour pads**; `f2` = page 0…7 | correlated 18/18 |
| 145 ×8 | 40 – 159 | **20** each | 8 pages × 20 **glyph buttons**; `f2` = page 0…7 | correlated 18/18 |
| 150 ×8 | 483 – 491 | **20** each | 8 pages × 20 **pan/tilt positions**; `f2` = page 0…7 | correlated 18/18 |
| 151 | 0 or 64 | 0 or **4** | 4 × three 16-bit values centred on 32767 | observed |
| 155 | 562 – 563 | **4** always | **4 FX sequences**, each an 8 × 16 grid + step count | correlated |
| 160 | 393 – 542, **optional** | 8 – 11 | named macros | correlated (pre-existing) |
| 161 | 599 – 604 | **3** always | 3 × ~190-byte blob, volatile | observed |
| 165 | 26219 – 29831 | 80 – 82 | preset container — see `SPEC.md` §5 | correlated |

`160` is the only optional record (absent from `cc21`, `cd21` and everything
derived from them: 40 records instead of 41).

### 1.1 The `×8` types are **pages, not groups** — hypothesis refuted

The brief asked whether `140 ×8`, `145 ×8`, `150 ×8` are the 8 fixture groups
A–H. **They are not.** In 18/18 files:

- each of the 8 records carries **exactly 20 items**, whatever the project;
- the *n*-th record carries a top-level `field 2 = n` (absent for n = 0), i.e.
  an explicit page number 0…7;
- for `140` and `150` the top-level `field 1 = 20`, an explicit item count.

20 is the documented pads-per-page. A group-indexed record would have to vary
in size with how many fixtures each group holds; these do not. Status:
**correlated, 18/18, and "= groups A–H" is refuted.**

Stronger still: `140[4..7]`, `145[1..7]` and `150[1..7]` are **byte-identical
across all 18 files** — 4 independent rigs, two different writers. Those are
untouched factory pages. Only page 0 (and pages 1–3 of `140`) ever differ.

## 2. The patch model — six record types locked together by arithmetic

This is the strongest result of the session. Five identities hold **exactly,
18/18 files**, with no fitted constants:

```
1.  count(116)                       == 116.field1
2.  Σ 116[p].f2                      == count(110)
3.  116[p].f3                        == Σ_{q<p} 116[q].f2        (running offset)
4.  110[c].f3 is monotone and < count(111)
5.  Σ 105[e].f7                      == count(106)
6.  max(105[e].f5) + 1               == count(115)
7.  115[r].f3                        <  count(116)
8.  Σ 116[ 115[r].f3 ].f2            == count(120)
```

Read out:

- **116 = fixture profile catalogue.** `f2` = number of channels in the
  profile; `f3` = index of the profile's first channel inside record 110;
  `f8` = UTF-8 name truncated to 19 characters (`'LED PAR 56 Black RG'`,
  `'LASERBAR 6x400RGB J'`); `f9` = 16-byte profile hash; `f11` = epoch-ms
  timestamp (values seen: 2021-02-16 … 2022-10-28).
- **110 = the concatenated channel lists of all profiles**, profile *p*
  occupying `[116[p].f3, 116[p].f3 + 116[p].f2)`. Per channel: `f2` = channel
  feature/type enum, `f3` = index of its first entry in 111, `f4` = default
  value, `f5` = an ordinal.
- **111 = the concatenated range/capability lists**, indexed from 110. Entries
  look like `{f1 = from, f2 = to, f3 = function id}` — `cc21` contains clean
  8-way splits `1–50 / 51–100 / … / 241–255` and `31`-wide splits
  `0–31 / 32–63 / … / 224–255`, i.e. gobo or colour-wheel slots.
- **105 = the DMX patch.** `f1` = library fixture id (stable across projects:
  `1017` is the same `6x18W 6in1 RGBAW UV` in both *rig-b* and
  *rig-c*), `f4` = **running offset into record 106** — *retracted 2026-08-26,
  this was read as a 0-based DMX start address; the address is `115.f2`, see
  the registry* —, `f5` = index of the fixture row
  in 115, `f6` = category 0…8, `f7` = **number of 106 entries**, not channels.
  A fixture built from
  several DMX blocks emits several entries with the same `f5` (the
  `LED BAR 252 RGB` of *rig-b* = 3 × 4 ch; the `LASERBAR` of
  `rig-c-bug` = 6 × 8 ch).
- **115 = the fixture instances.** `f3` = index into 116; `f2` = the fixture's
  start offset in an internal channel arena, stride = its profile's channel
  count; `f6` (repeated on the record, not on the items) = the display order,
  a permutation of 0…n−1.
- **120 = the flat per-fixture-channel value table**, `Σ` profile channel
  counts entries, laid out as one contiguous block per fixture in **ascending
  `115.f2` order**. Verified block-by-block on *rig-b*: six blocks of 10
  (`6x18W`), then blocks of 7 (`LED PAR 56`), then 11 (`LED BAR`), then 2
  (`Power Strobe`) — 134 entries, matching identity 8 exactly.

### 2.1 A real anomaly: the 115 arena has holes

Identity 8 (`Σ profile channels == count(120)`) holds 18/18. But the stronger
claim — that the `115.f2` offsets tile `[0, count(120))` exactly — holds only
for `cc21` and its ACC derivatives. In every other file the offsets are
*stride-correct per profile* but leave gaps and run past the end of 120:

| File | count(120) | max `115.f2` |
|---|---|---|
| `cc21` | 86 | 72 (+14 = 86, exact tiling) |
| `cd21` | 134 | 255 |
| `rig-c` | 215 | 499 |
| `rig-c-bug` | 258 | 499 |

Every value stays below 512. **[hypothesized]** `115.f2` is an address in a
512-slot internal channel arena that is *not* compacted when fixtures are
deleted or re-patched, while 120 is always rewritten densely. Alternative
candidate: `115.f2` is a stale field the firmware ignores entirely. This
matters because BUG-01 (`research/evidence.md`) blames the blackout on record
120 — if the firmware indexes 120 by `115.f2`, an un-compacted arena is a
second, independent way to read zeros. It does **not** by itself explain
rig-c: the healthy revision has out-of-range offsets too.

### 2.2 Record 125 is fully derived — no experiment needed

`125` has exactly **9** items in every file. Item *i* carries
`f4` = a 7-byte blob and `f8` = an optional UTF-8 name (the operator's group names, in
rig-c). The first 6 bytes of `f4`, read as a little-endian integer, are
**exactly the bitmask of the 116 profiles whose patch entries carry
`105.f6 == i`**:

```
mask[i] = OR over fixture rows r of (1 << 115[r].f3)  where  category(r) == i
```

**Verified 18/18 files, bit for bit.** Cross-check on rig-c: profile 0
(a 16-channel moving head) → mask 0x01, profile 1 (a 10-channel par) → 0x02,
profile 4 (a second moving head) → 0x10, profiles 2+3 → 0x0c at index 8, and
`rig-c-bug` adds a seventh profile → 0x40 at index 3. Each mask matches the
category name the operator gave it — four independent name↔content matches,
the names themselves being that rig's own and not reproduced here.

**Retracted 2026-08-26 — see the registry, *The fixture → group assignment*.**
The paragraph below is kept as written; only its conclusion is wrong.

So **125 is the 9 fixture *categories*, not the 8 groups A–H**, and its masks
are redundant data recomputable from 105 + 115 + 116. Status: **correlated**.
Only `f8` (the user-editable category name) carries information a writer must
preserve.

The 7th byte of `f4` is `0x30` in `cc21`/`cd21` and `0x38` in the rig-c
family — a per-project constant replicated on all 9 items. It correlates with
record 151 being populated. Candidates: a capability flags byte, or the same
"global stored per slot" pattern seen in 115 `f6`/`f7`. **[observed]**

### 2.3 Record 130 carries no project data

102 bytes, 9 items, **byte-identical in 18/18 files** across 4 rigs with
3 to 7 different profiles and 10 to 22 fixtures. Items 0–7 read
`{f2 = i, f4 = 20, f6 = i, f7 = 1, f8 = 1}`, item 8 reads
`{f4 = 27, f6 = 8, f8 = 1}`. The 9-item shape and the `f6 = 0…8` index match
record 125's nine slots one-for-one; `f4 = 20` matches the pads-per-page
limit. **[hypothesized]** per-category factory defaults (how many pads a
category's screen shows). Negative result worth recording: **no differential
experiment will ever be productive on 130 unless the operator edits something
category-related.**

## 3. Record 102 — closing the last three fields

Full field census over 18 files:

| Field | Values seen | Reading | Status |
|---|---|---|---|
| 2 | 1, absent | present **only** in `cc21`/`cd21` (WTOOLS-written, never controller-saved) | observed — legacy field, dropped by fw 2.0.18 |
| 3 | 2, absent | same | observed — legacy field |
| 4 | 6-byte array | release mode per flash key | device-confirmed |
| **5** | **100 in 18/18** | never moved | unattributed |
| **6** | **100 in 18/18** | never moved | unattributed |
| 7 | absent, 1, 2, 4 | SPEED multiplier — see 3.1 | device-confirmed with a correction |
| 8 | absent, 1 | group-exclusion mask | hypothesized |
| 9 | 1, 72, 75, 80, 100 | STROBE speed, stored 1–100 | device-confirmed |
| **11** | **100 in 18/18** | never moved | unattributed |

Guide 10 lists exactly **three** per-effect parameters that are still
unaccounted for: BLINDER fade-out, SMOKE intensity, SMOKE fan speed. Record
102 has exactly **three** fields that are 100 everywhere and have never moved.
The assignment is a 3! = 6-way permutation and one save resolves it (§4, P1).

### 3.1 Correction: `field 7` is not a literal multiplier

`corpus/experiments/FX-06/after-speed-half.wpj` (appeared 16:12 during this
session; intent read from the filename, *not* from an operator report) is a
one-save diff from FX-05 in which **record 102 is the only record that
changed** and `f7` went **4 → 1**.

| SPEED setting | `f7` |
|---|---|
| normal (1×) | absent |
| 0.5× | **1** |
| 2× | 2 |
| 4× | 4 |

A literal multiplier cannot store 0.5, and a list index would have written 3
for 4×. So `f7` is an **enumeration whose values coincide with the multiplier
for the integer steps and reserve 1 for 0.5×**. The registry's
"stored literally — device-confirmed" needs this footnote. Still open: 8× and
FREEZE.

## 4. Predictions to test on hardware

Ranked by unknowns-settled per controller save. Published before measuring.

**Noise budget for every prediction below.** Across the five controller saves
in the corpus (FX-01 ×2, FX-03, FX-04, FX-05) the *only* things that ever
changed outside the operator's intent were:

- the 8-byte little-endian integer at absolute offsets **40–47** (see §5),
- record **115**, whose items gained/lost `f6` and `f7` as a block,
- record **155**, once, during FX-03 (explained: the operator opened the
  MOVE FX sequence editor),
- offset **50**, once, `0x0a → 0x0b`.

**All 34 other records — including the 29 KB record 165 — were byte-identical
through all five saves.** Any prediction below that says "record X is the only
record that changes" is therefore a real, falsifiable claim, and in particular
**the firmware does not re-serialise our generated preset payloads on save**.

---

### P1 — Record 102 `f5` / `f6` / `f11`: three unknowns, one save. **Highest value.**

**Action.** On the W1, without touching anything else: BLINDER screen → set
the fade-out encoder to a distinctive value; SMOKE screen → set intensity and
fan speed to two other distinctive values. Suggested triple, chosen to be
mutually distinguishable and far from 100: **fade-out 10, intensity 40,
fan 70**. Save once.

**Prediction.** Record 102 is the only record that changes (plus the 115/prefix
noise). Its `f5`, `f6` and `f11` take the values **{10, 40, 70} in some order**,
and no other field of 102 moves. Whatever order comes back is the final
assignment of the three parameters, since each value is unique.

**Other outcomes.** If only one or two of the three move, the remaining
parameter lives outside record 102 — most likely in one of the still-opaque
records (110 `f4` defaults, or 161). If a *fourth* field appears, the
parameters are not all in 102 and the new field number is the smoke record. If
the values come back scaled (e.g. 25 for 10 %), the field is a raw DMX level
rather than a percentage — which would also retro-explain why the resting
value is 100 and not 255.

---

### P2 — Record 155: decode 512 opaque bytes with one save.

`155` holds 4 items, each `{f1 = 8, f2 ∈ {1,2}, f3 ∈ {2,4,16}, f4 = 128-byte
array}`. 8 × 16 = 128 = 8 groups × 16 steps. In FX-03 item 0's `f3` went
**4 → 16** and its array's byte 0 went `00 → 01` when the operator touched the
STEP control in the MOVE FX sequence editor. Sequence 1 of every project
contains `00×8, 01×8, 02×8, 03×8, 00×96` — a 4-step chase. Items 2 and 3 are
all-zero in every file: **free canvases**.

**Action.** MOVE FX → sequence editor → select **sequence 3** (an all-zero
one) → set its step count to **5** → enable **exactly one cell**: group B at
step 4. Save once.

**Prediction.** Only record 155 changes (plus noise). Item index 2 gets
`f3 = 5`, and **exactly one byte** of its 128-byte array becomes non-zero.
The byte index tells us the geometry outright:

| Byte index | Meaning |
|---|---|
| **25** (= 3 × 8 + 1) | step-major: 8 group slots per step, 16 steps. Group order A…H, step index 0-based. |
| **19** (= 1 × 16 + 3) | group-major: 16 step slots per group. |
| **33** (= 4 × 8 + 1) or **20** (= 1 × 16 + 4) | same two layouts but with the step number stored 1-based |
| anything else | neither; report the index and we re-derive |

The value written in that byte is also new information: `01` = a boolean
on/off, `0f` = the value seen in rig-c's sequence 2 (so a per-cell level
or a 4-bit sub-mask), `ff` = a level.

**Why it is worth a save.** 4 × 128 = 512 bytes go from opaque to fully
addressable, and the `f1 = 8` / `f3 = steps` reading gets validated at the same
time. It also confirms or kills the "8 groups A–H" ordering that record 165's
`f28`/`f17` per-group arrays already assume.

---

### P3 — Record 115 `f6` / `f7`: turn the last source of save-noise into a known field.

`f6`/`f7` are **not** per-fixture: every item of a given file carries the same
pair. Values: `(110, 218)` rig-b, `(94, 187)` rig-c, `(79, 99)`
rig-c-bug, `(44, 41)` f2737ec3, `(0, 0)` rig-a, and after controller
saves `(0, 0)`, once `(4, 0)`. Both are 0–255. A global written into every
fixture slot.

**Action.** STATIC POSITION screen → set the FADE encoder to a distinctive
value (**37**, unlikely to arise by accident) → save once, touching nothing
else.

**Prediction.** Record 115 is the only record that changes. **All** items take
`f6 = 37`; `f7` stays absent. That confirms `f6` = the STATIC POSITION fade
time, "a global stored per slot", and demotes the whole 115 diff from noise to
signal.

**Other outcomes.** `f7 = 37` instead → the pair is (something else, fade) and
the two candidates swap. Neither moves → the STATIC POSITION fade is refuted
and the remaining documented candidate is the MOVE FX sequence STEP control
(which we can then test with P2 in the same session, since P2 already visits
that editor — check 115 in the P2 diff before concluding). All items taking
**different** values → the "global stored per slot" reading is wrong and
`f6`/`f7` really are per-fixture (pan/tilt trim is then the candidate).

---

### P4 — Record 102 `f8`: is the group-exclusion mask shared or per-effect?

One exclusion (group A, from STROBE) produced one field `f8 = 1`. Six effects
can each exclude groups; only one field exists. Two readings.

**Action.** Main menu → Settings → Project. Set STROBE to exclude **group A**
and BLINDER to exclude **group C**. Nothing else. Save once.

**Prediction, reading 1 (shared mask).** `f8 = 5` (bit 0 | bit 2), no new
field. Consequence: group exclusion is a single global setting and guide 10's
"pick the flash effect, then the groups" is UI sugar over one value — which
would be surprising and is worth knowing.

**Prediction, reading 2 (per-effect fields).** `f8 = 1` and a **new field
appears** carrying `4`. Its field number identifies BLINDER's slot, and by
extension the other four effects live in the remaining free numbers of record
102 (1, 10, 12, 13 are unused today). This is the outcome I expect.

Either way one save settles the arity, the bit order (bit 0 = A), and — if
reading 2 — one more field number.

---

### P5 — Patch one fixture: validate six record types at once.

**Action.** On the format-lab project only: main menu → Fixtures → ADD → patch
**one** fixture of a profile the project does not already use, at a free
address. Save once. (Destructive-ish; do it on `WMX EXP format-lab`, never on
a show project.)

**Prediction, exact:**

- `116` gains one item, at the **end**, with `f2 = N` (the new profile's
  channel count) and `f3 = ` the old `Σ f2`.
- `110` gains exactly **N** items, appended.
- `111` gains the new profile's ranges, appended.
- `105` gains one item with `f5 = ` the new row index, `f7 = ` the address span.
- `106` gains exactly `f7` items.
- `115` gains one row with `f3 = ` the new profile index.
- `120` grows by exactly **N** items — and *where* they land tells us whether
  the firmware inserts them at the arena offset or appends.
- `125[category].f4` gains the new profile's bit, still matching the derived
  formula in §2.2.
- `130` does **not** change.

**Why it is worth a save.** It validates identities 1–8 in the write
direction, which is exactly what a writer needs before it can patch fixtures.
And the answer to "does 120 stay dense while `115.f2` keeps its holes?"
(§2.1) is a direct lead on the rig-c blackout. A mismatch anywhere is a
firmware bug we can then characterise instead of guessing.

---

### P6 — SPEED `f7`: finish the enumeration.

**Action.** SPEED screen → **8×** → save. Then SPEED → **FREEZE** → save.
(Two saves, but each is a single change and the second cannot be inferred.)

**Prediction.** 8× writes `f7 = 8`. FREEZE cannot write a multiplier, so
candidates in order: a large sentinel (`255`), `0` *with* a companion flag
field appearing, or a separate field entirely. If 8× writes anything other
than 8, the "value = multiplier except 0.5×→1" reading in §3.1 collapses and
`f7` is an opaque enum — in which case FREEZE's value is the only way to map
it.

---

### P7 — Record 135 = the 16 ColorFX palette pads (cheap, bundle with anything).

`135` holds exactly 16 RGBWALU items and is identical in 3 of 4 rigs. Record
165's ColorFX `f5` is already read as a 16-bit pad mask
(`Rainbow = [224, 10]`, `Carnival = [240, 4]`).

**Action.** COLOR FX screen → edit palette pad **3** to pure green. Save.

**Prediction.** Only record 135 changes, and only item **index 2**, which
becomes `{f2: 255}` alone (all other channels absent/0). That nails the
pad-index → item-index mapping and, with it, the bit order of the preset
`f5` mask — closing the ACC-05/ACC-06 line without generating another file.

**Other outcome.** If item 2 keeps its old value and another item changes, the
palette is stored in UI order rather than pad order; the index that moves
gives the permutation directly.

---

### P8 — Record 151 (lowest confidence, list it so nobody re-derives it).

`151` is **empty** in rig-a and rig-b and holds 4 items in all three
rig-c revisions. Each item: `f1` = index 0…3, `f2` = 32767 always,
`f3`, `f4` = 16-bit values in 32767…45546. Exactly 4 items — the same count as
record 155's 4 sequences.

Candidates, in order: (a) per-sequence pan/tilt home for the 4 FX sequences;
(b) live pan/tilt state for groups A–D; (c) volatile UI state like 161.

**Action.** MOVE FX → sequence editor → sequence 2 → move its position picker.
Save.

**Prediction.** If (a): `151[1].f3`/`f4` change and `f2` stays 32767.
If (b): nothing in 151 changes (a sequence is not a group) — then instead move
group A's live pan and re-test. If (c): 151 changes on *every* save, which the
noise budget above already partly rules out (151 did not move in five saves) —
so (c) is already weak.

## 5. Prefix bytes 20–63, refined

| Offset | Content | Status |
|---|---|---|
| 20–35 | 16-byte project UUID = the `wlinkData` file name | correlated (pre-existing) |
| 36–39 | constant `15 2b 10 c0` in 18/18 files | observed — container magic |
| **40–47** | **little-endian uint64 version**. FX-01 `before` = 1 787 654 382 431 (an epoch-ms value); `cc21` = 2, `rig-c` = 6, `rig-c-bug` = 15 | **correlated** |
| 48–49 | constant `01 f9` in 18/18 | observed |
| **50** | 8 (`rig-c`), 10 (WTOOLS-written files and `FX-01/before`), 11 (**every file after a controller save**) | correlated |
| 51 | constant 0 | observed |
| 52–63 | constant `02 be e8 1c a2 6c cb 54 6d c7 b6 ec` in 18/18 | observed |

**This corrects the registry's "byte 40 = save counter".** Byte 40 is the
*least significant byte* of a 48/64-bit version field that the firmware
increments by one per save. The registry's own observation `62 → 66` across
four saves is +4 on the LSB, consistent. **Falsifiable consequence:** after
enough saves the LSB wraps and **offset 41 increments while offset 40 drops to
0x00**. For the format-lab project (currently at `0x68 = 104`) that happens on
the 152nd further save — not worth doing on purpose, but any writer must treat
this as a 64-bit integer, not a byte, or it will corrupt the version after a
wrap.

Offset **50** is better read as a **writer/schema version** than a counter: it
takes only three values, it is 10 in every WTOOLS-written file, and it moved
`10 → 11` on the *first* controller save of FX-01 and never again through five
more saves. `rig-c = 8` is an older writer.

## 6. Refuted / dead ends

- **`140/145/150 ×8` = fixture groups A–H.** Refuted, 18/18: each of the 8
  records holds exactly 20 items regardless of the rig, and carries an
  explicit page number in top-level `f2`. They are 8 **pages** of 20 pads.
- **`155` = the DMX patch map (4 × 128 = 512 channels).** Refuted. The DMX
  patch is record 105 (correlated by the exact `Σ f7 == count(106)` identity),
  and `155`'s arrays are 8 × 16 grids with a step count in `f3` that moved
  4 → 16 when the operator touched the sequence editor's STEP control.
  `4 × 128` is 4 sequences × 8 groups × 16 steps, not a universe.
- **`125` = the 8 groups A–H.** Refuted: 9 items, and the mask is exactly
  reproducible from `105.f6` (category) + `115.f3` (profile) in 18/18 files.
  It is the 9 fixture *categories*. **This refutation is itself retracted on
  2026-08-26**: the 9 slots are groups A–H plus a ninth for the fixtures with
  no group pads, and `105.f6` is the group index. See the registry.
- **Record 102 `f7` is the SPEED multiplier "stored literally".** Corrected,
  not refuted: 0.5× writes 1 (FX-06).
- **Prefix byte 40 is a byte-wide save counter.** Corrected: it is the LSB of
  a 64-bit version integer at offsets 40–47.
- **Record 115 has a fixed 20 slots.** Refuted: 10/15/20/22 items across the
  four rigs, always equal to `max(105.f5) + 1`. The "20" in the registry was a
  coincidence of the rig-c rig having 20 fixtures.
- **Record 115 `f6`/`f7` are per-fixture values.** Refuted for the corpus:
  every item of a file carries the same pair. They are one global written into
  every slot.
- **Type 130 is worth diffing.** Dead end: byte-identical in 18/18 files.
- **The variant-B/C files can help decode TLV records.** Dead end: they
  contain no TLV container at all. Their top-level protobuf (`field 3` ×100
  presets, `field 15` ×2048, `field 5` ×80) is a *different* serialisation and
  needs its own mapping.
- **Record 165 is rewritten by the firmware on save.** Refuted, and this is
  good news: 29 KB of preset payload survived five controller saves
  byte-identical, so a generated 165 is stable on the device.

## 7. What a writer can now compute instead of copying

Records **125** (masks) is fully derivable from 105 + 115 + 116, and the
offsets in **116.f3**, **110.f3**, **115.f2** and the size of **120** are all
determined by the profile channel counts. A patch-editing writer must
recompute them rather than preserve them verbatim; a non-patch-editing writer
(everything we have built so far) can leave all six records untouched, which
is what `tools/wpjlib.py` already does by construction.
