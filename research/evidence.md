# Evidence registry

Every finding this repository has published, one line each: the date, what was
done, what came out, and the status it ended at. `SPEC.md` is the consolidated
read of these; this is the ledger it was built from, and when the two disagree
this file is the one that was written next to the measurement.

**Reading a line.** The date is the day of the *measurement*, not of the
write-up. Status uses the vocabulary in [`AGENTS.md`](../AGENTS.md) —
`observed → hypothesized → correlated → validated → device-confirmed` — and an
arrow marks a status that **moved**, in either direction. Unless a line says
otherwise the controller ran firmware **2.0.18** and the editor was WTOOLS
1.6.3 (until 2026-08-30) or 2.0.2 beta (after); a line that depended on a
version says so. `snapshot` names a directory under `corpus/experiments/`: the
project files themselves are not in this repository, their SHA-256 are, in
[`corpus/SHA256SUMS`](../corpus/SHA256SUMS).

**Refutations come first, and in full.** They are the entries that cost the
most and the ones a summary is most tempted to lose. A status that went **down**
is written out below with what it dragged with it; the table then carries every
entry, refuted ones included.

## Refutations, withdrawals and status downgrades

### RECALL-01 — `device-confirmed` → **withdrawn** (2026-08-27)

Read: "the varint value of `SET_PRESET` is ignored — the event addresses
nothing." Measured from two DMX envelopes captured separately.

**Why it was wrong.** Two separately captured envelopes cannot separate
"nothing moved" from "the same thing was repainted". Preset recalls do act, and
they always act the same way, which the separate captures rendered
indistinguishable from inaction. One continuous capture with timestamped
transitions settled in minutes what they had got backwards.

**What it dragged down.** Four negatives rested on the same discriminator and
went with it; the repair is in RELOAD-02, and RECALL-03 is the reading that
replaced it — the payload is not protobuf at all, and the device had been
reading our tag byte as the index (RAW-01).

### GEN-02 — `device-confirmed` → `hypothesized` → `validated` (2026-08-27)

Read: "`165.f10` bit 5 (`OTHER`) is what silences the dimmers."

**Why it went down.** The dimmer silence it was thought to explain turned out
to be a **controller setting** that had been off the whole time. One cause is
enough, and the field had never been isolated. It climbed back to `validated`
the same week, but only because FW-03 wrote that bit **and nothing else**: a
status goes back up by measurement, not by the passage of time.

### F4-01 — `device-confirmed` → **retracted** (2026-08-26), superseded by F4-02

Read: "`COLOR` = `f4` bit 3, `MOVE` = bit 2, `BEAM` = bit 4", from six
photographed `PRESET EDIT` screens.

**Why it was wrong.** Wrong field. The content mask is **`f10`**. `f4` and
`f10` are *both* constant per factory page, so six screens could not tell them
apart — the four `f4` values happened to be in one-to-one correspondence with
the four `f10` values across the four pages. It took a write that moved one
without the other.

This is the corpus-uniformity trap in a new dress: not one field uniform
everywhere, but **two fields co-varying everywhere**, which is just as
indistinguishable and just as easy to mistake for a proof.

**What survives.** The mask *shape* — `Searchlight` lighting three toggles at
once still refutes an enumeration — and the retraction of ACC-03's "closed
vocabulary" reading. `f4` itself became unknown again, and F4-03 later read it
as a **permission mask** over the three engines.

### FX2-01 — an identity refuted the day it was added (2026-08-27)

`wpj_identities.py` gained "an FX engine that is on stores two *different* page
configurations" that morning: 3697 occurrences, zero exceptions. One preset
composed at the panel refuted it the same evening.

A correlation with no exception over the whole corpus is a fact **about the
corpus** until a fresh write tests it. The defence is the write, not more
counting — and the author of that warning fell into it inside a day.

### FLASH-01 — the published prediction was refuted, and took an identity with it

Predicted: the latched flash state lands in `165.f12` or `f20`, the two holes in
the field numbering. Measured: neither appeared; **`f16` slice 6** moved
instead, to 511 — all **nine** slots, the eight groups plus the one holding the
fogger and the spark.

It also refuted one of our own identities: `moteurs_f16` asserted that no slice
ever sets the ninth bit — true on 2778 presets, false the moment a flash key is
latched. **It lasted four hours.** The identity now checks that for slices 0–5
only, and the comment says why.

### F11-03 — refuted, and the experiment could not have tested what it claimed

`Button brightness` set to 14 %. Predicted `102.f11` = 14. Measured: one save,
43688 bytes both times, **not one record changed** — the setting is not project
data, which is a clean result.

**But the experiment was mis-posed, and the fault is the author's.** The
prediction rested on "`f11` = 100 in every corpus file". That had stopped being
true twenty-eight snapshots earlier: F11-01 wrote `f11 = 0` into that very
project, and every save since re-emits the field absent. The comparison was 0
against 0.

> Read the current state of the field you are about to test, not the state the
> registry describes.

### F11-01's side finding — "loading a project resets the flash release modes" — **retracted**

`102.f4` came back as `01 00 00 00 00 00` because **the operator reset those
modes by hand**, not because loading a project clears them. The SMOKE reversion
noted in FX-07 remains a single unexplained observation rather than the general
behaviour that entry claimed.

### EXP-06 — a prediction refuted in the middle of an otherwise exact result

Predicted, as the discriminator for the DMX address base: `f12.f3 = 115.f2 − 1`
(base 0 against base 1). Measured: **exact equality — both are base 0.**

The rest of the Rosetta pair held: profiles field for field, preset names, and
the FX tuples — though not as predicted either. The four 81-byte tables are
**banks per effect** (row *e* = the parameters of effect *e*), not tuples per
group; 21/21 engine×preset. The effect id is the **row index**, and it stayed
invisible because it was being looked for as a value.

### F30-02 — element 7 refuted the share rule that six derived rows had assumed

Predicted for `inward hard`: Amber 1,2,9,10 · Cyan 3–8. Measured: **Amber
1,2,3,8,9,10 · Cyan 4–7** — direction right, shares wrong. Seven of the eight
captures were exact; this one corrected the distribution rule, which F30-03 then
closed at three colours in both geometries.

`FLASH` also turned out to make a group's pads **momentary**, not a spatial
layout.

### F7-03 and F7-04 — two predictions the author got wrong, kept as written

- **F7-03**: predicted `f16` slice 1 (Move) = 0, reading "engine stopped" off a
  photograph of the `MOVE FX` tiles. Measured **4 = C**: the engine was on. The
  screen reading was wrong, or the operator lit it while setting the page, and
  nothing in the photographs can tell which.
- **F7-04**: the same box was left **empty** on purpose after that miss.
  Measured 3 = A+B. The abstention cost the shot nothing.

Both entries also carry a method note against themselves: the probabilities were
published **before reading** the file, but the operator had already measured. The
protection against retrospective confirmation holds — nothing had been read —
but "published before the measurement" does not apply, and the commit date alone
would have suggested otherwise.

### SCREEN-02 — one of six measures refuted its prediction (2026-08-31)

Predicted that `mode presets` would move the panel to the preset screen. It
reports `wolfmixMode: 5` and the panel **stays on HOME**. Recorded as false
rather than rewritten; the measured partition is in the table.

### GUARD-01 — one of nine measures refuted its prediction (2026-08-31)

The pre-deploy archive failure surfaced a bare `PermissionError` instead of the
named refusal the prediction claimed. Fixed in the same session — the message
now reads "Pre-deploy archive failed, nothing was uploaded: …" — and re-measured.

### COV-02 — `165.f27` is not zero everywhere (2026-09-01)

SPEC §5.6 and Q1 both stand on "`f27` is zero on all 3697 corpus presets".
On the corpus as it is today — 4312 presets over 76 variant-A files — **26 of
them carry `[1000] × 8`**, and the statement was true when it was written: the
files that carry it were added on 2026-08-31, after the sentence.

The split is by author, not by content. Every preset of the three projects a
**WTOOLS 2.0.2 duplicate** produced (`WMX EXP05`, `2 Lyres-v2`) carries 1000 on
all eight groups; every preset of the projects composed **at the panel**
(`WMX EXP format-lab`, the four rigs) carries eight explicit zeros. Neither
side omits the field.

One preset crosses the line inside the corpus. In EXP-07 the device recaptured
`WMX EXP05`'s preset 0, and its `f27` came back `[0] × 8` while the six
untouched presets kept 1000. That is not a single-variable differential —
the recapture rewrote seventeen fields of that preset at once, `gobo_focus`
`50 → 0`, `gobo_zoom` and `gobo_iris` `100 → 0` among them — so it names the
author and not the meaning.

What it does buy is the **cheap discriminator Q1 says has not emerged**: the
contrast is reachable in WTOOLS, on a project already on this machine, with no
preset capture and no deploy. 1000 is the shape of a millisecond default, next
to `f11` FADE and `f15` HOLD which are milliseconds — and it sits in the same
group of per-group tables whose WTOOLS defaults this same diff shows written
out explicitly (`50 / 0 / 100 / 100` on `f32`–`f35`, §5.6). **Hypothesis, not a
reading**: a sixth per-group table whose WTOOLS default is 1000 and which this
firmware writes as 0.

Q1 is not answered. Its stated blocker is.

### COV-03 — record 120's entries are not empty (2026-09-01)

The unnamed-field inventory read `120.channels` as "`2a 00` entries, all
empty", which would have made it structurally empty on this rig rather than
undecoded. Measured: **10 754 of 14 698 entries carry content** — 73.2 %. The
fields are `f1` (9680 occurrences, DMX-shaped values), `f4` (7876, always 1),
`f5` (2148, only 1 or 2) and `f6` (2081).

The one file where the entries really are empty is *rig-c-bug*: 251 of 258, which
is **BUG-01**, the firmware erasure — not a property of the record. Reading the
corpus-wide shape off that file is the mistake the erasure invites.

No identity fell out. `f6` comes in pairs `(n, n−1)` whose `f5` reads 1 then 2,
which looks like a coarse/fine couple, and `f6` matches `110.principal_channel`
on 954 of the 2081 entries that carry it — enough to notice, nowhere near
enough to name. It stays unread, with a shape.

### COV-14 — `f16` slice 1 is not equal to `move_fx_active` (2026-09-01)

`slice 1 == move_fx_active` was `correlated 45/45`, held on 3697 presets, and
was one of the identities `wpj_identities.py` asserts. **The preset the device
composed for COV-10 carries slice 1 = 1 with `move_fx_active` = `[0]`.** The
counter-example is a preset the firmware wrote alone, on a capture whose only
deliberate variable was a per-group position FADE.

The identity was not wrong when it was written. It was **untested**: the two
files that break it — a WTOOLS-duplicated project and the capture made into it
— entered the corpus in the same commit that broke it. Adding two files to a
corpus of 78 refuted a claim that had stood on 3697 presets, which is the
clearest statement of the corpus rule this repository has: uniformity across a
corpus is a fact about the corpus.

What survives is the containment, exact on every preset:

    slice 1 ⊇ move_fx_active

and it keeps the whole refuting power — at a stride of 8 it fails on 1767 of
4339 presets, so the alignment still tests itself.

**Slice 0 against `color_fx_active` is now asserted at neither.** Both
containments fail — 6 presets one way, 18 the other — so `wpj_identities.py`
checks nothing there rather than checking a fitted rule. SPEC's "equals
`color_fx_active`, 3696/3697" is a count on a corpus that no longer exists.

Two readings of what slice 1 means are open and this measurement does not
separate them: that it marks the groups whose **movement** the preset touches,
a fade being movement; or that a capture sets it from live state that
`move_fx_active` does not track. Nothing here chooses.

### The unnumbered ones, for completeness

- **ACC-03's "closed vocabulary"** reading of `f4`: retracted by F4-01, which is
  itself retracted by F4-02. The display bug ACC-03 hit still has no cause.
- **`f30` read as a scalar** replicated eight times: refuted by one photograph
  of the device, then by F30-04's `[4, 3, 8, 0…]` — the first non-uniform `f30`
  ever observed, after 2033 corpus presets carrying the same value on all eight
  groups.
- **`165.f16` slice 5 "always 255"**: `correlated` over 2446 presets, refuted
  when the device's own writer put the mask of the groups each preset addresses
  there (GEN-03).
- **`f2` of the FX sub-message read as "speed %"** since ACC-04: it is the
  **fade**. The speed is `f9`, and a whole campaign was framed as a three-way
  permutation that was really a four-way, because `f2` already carried a name
  and was never put back on the table (FX6-02).
- **Record 155 "the 4 FX sequences"**, `device-confirmed`: the beam sequencer
  was hunted in an opaque blob (161) while the answer sat in 155 behind `f2`, a
  field named "sequence flavour" and never opened (FX6-05).

## Three ids mean two things each

Found while building this file, and worth more than the entries around it: three
ids were reused for **different experiments**. A citation that gives only the id
is ambiguous for these three, and every citation in the tree has been checked
against the intended one.

| id | first use | second use |
|---|---|---|
| `SCREEN-02` | 2026-08-27 — how to leave a modal screen | 2026-08-31 — which modes actually move the panel |
| `EXP-07` | 2026-08-25 (planned) — change a Beam FX type | 2026-08-31 — single-variable differentials on a variant-B project |
| `GOBO-01` | 2026-08-26 — the five static gobo features (**refuted**) | 2026-08-30 — where the gobo icon library lives |

They are **not renumbered**: a published id is a citation target, and rewriting
one to tidy the ledger is the same move as rewriting a refuted prediction. The
ambiguity is recorded instead, which is what this repository does with
ambiguity everywhere else.

## The register

`SPEC §` is filled where the source states it; a dash means the link has not
been made, not that there is none.

### Acceptance of files we wrote — the write chain

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| EXP-01, EXP-02, EXP-03, EXP-04 | 2026-08-25 | **planned only**: rename a project, rename a preset, one FX parameter, a null round trip. Superseded by ACC-01…04 and by the corpus round trip. | planned | — |
| ACC-01 | 2026-08-25 | A copy of `rig-a` with record 101 rewritten, imported into WTOOLS 1.6.3 and synced to the W1 → accepted, **stored byte for byte identical**, opened on the device. The variant-A container, the SHA-1 header and the 101 encoding all land at once. | device-confirmed | §2 |
| ACC-02 | 2026-08-25 | The same chain with a Color FX and dimmers added → the preset **name** applied, the FX and dimmers **ignored**. First sign that a mask gates what the W1 reads. | device-confirmed (name) | §5 |
| ACC-03 | 2026-08-25 | Two masks tried (`f4` = 25, then 255 + flag) → 25 produced a **UI bug** on the device, 255 was accepted and still ignored. Read as "`f4` is a closed vocabulary" — retracted by F4-01, whose own reading was then retracted by F4-02. The display bug still has no cause. | refuted | — |
| ACC-04 | 2026-08-25 | In-place edit of factory preset `Carnival`, `f7` 3 → 2 → the device shows a colour chaser. The preset-edit chain works end to end. Its by-product — reading `f2` as "speed %" — cost a whole campaign four days later (FX6-02). | device-confirmed | §5 |
| ACC-05 | 2026-08-25 | Planned discriminator for `f5` (the 16-bit pad mask) and the pads↔UI relation. Closed from the corpus instead, without generating a file. | planned, closed on corpus | §5 |
| ACC-06 | 2026-08-25 | Built (`corpus/experiments/ACC-06/build.py`): separate speed `f2` from `f9`, and read the second varint of the pad mask. The speed half was **answered the other way round** four days later — `f9` is the speed (FX6-02). | superseded | §5 |
| EXP-05 | 2026-08-31 | Duplicate the variant-**C** project under WTOOLS 2.0.2 → **refuses to open**: "the project comes from too old a version". The 6→8 migration path is closed on this machine. Rival 3 of 3 won. | observed | §1 |
| EXP-05bis | 2026-08-31 | Fallback, duplicate a **v7** project → WTOOLS 2.0.2 offers no duplication at all; done on the W1, and the store failed with `invalid wire_type` on both sides. Nothing was written. | observed | §1 |
| EXP-06 | 2026-08-31 | The **Rosetta pair**: the same show in both serialisations. Profiles, patch and preset names align field for field; the base-0/base-1 discriminator is **refuted** (both base 0); the FX tables are **banks per effect**, and the effect id is the row index. | device-confirmed | §1, §5 |
| EXP-07 | 2026-08-31 | Three single-variable edits on a variant-B duplicate. (c) gobo rename → `145[A][0].f3`, the RENAME-01 field, written by the device this time. (b) Color FX speed 50 → 83 → `f9`, but the save **recaptures** the whole preset. (a) DMX address 17 → 18 → exactly three records: `115.f2`, the eight `106` entries of that fixture, and `120`'s derived header. | device-confirmed / validated | §7 |
| EXP-08, EXP-09 | 2026-08-25 | **Planned only**: isolate `f28` (position) and `f31` (static colour) with single-pad edits. Both fields were later measured by other routes (POS-07, GEN-01/03). | planned, superseded | §5.1 |

### Record 102 — the flash FX settings

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| FX-01 | 2026-08-25 | `STROBE` moved FLASH → TOGGLE and saved → **exactly one byte** of `102.f4` changed, at index 1. The operator's independent report that `WOLF` was already TOGGLE matched index 0. | device-confirmed | §6 |
| FX-02 | 2026-08-25 | Five release modes set at once, prediction `01 00 01 02 03 04` published first → **exact match, five bytes**. The whole enumeration (FLASH / TOGGLE / 1 s / 5 s / 10 s) is settled. | device-confirmed | §6 |
| FX-03 | 2026-08-25 | A save in which the operator opened the MOVE FX sequence editor → record **155** moved for the only time in five controller saves. Recorded as save noise, and it later mattered: 155 is the sequencer (FX6-05). | observed | §6 |
| FX-04 | 2026-08-25 | Four consecutive saves (strobe 100 %, speed 8×, group A excluded, speed 2×) → `f9` = STROBE speed 1–100, `f7` = SPEED multiplier, `f8` = excluded-group bitmask. Record 102 was the only record that changed. | device-confirmed / correlated | §6 |
| FX-05 | 2026-08-25 | SPEED 2× → 4× → `f7` = 4, which rules out a plain list index (it would have written 3). | correlated | §6 |
| FX-06 | 2026-08-25 | SPEED → 0.5× → `f7` = **1**. A literal multiplier cannot store 0.5, so `f7` is an enumeration that coincides with the multiplier on the integer steps and reserves 1 for the half. | device-confirmed | §6 |
| FX-07 | 2026-08-25 | Seven settings in one save → `f5` = SMOKE fan, `f6` = SMOKE intensity, both by unique value. One pair could not be separated by this save, and FX-08 separated it. SMOKE's release mode reverted on its own, unexplained and never reproduced. | device-confirmed | §6 |
| FX-08 | 2026-08-25 | BLINDER fade-out 2 s → 1 s and SPEED FREEZE → 2× → the FX-07 collision resolves: `f2` = BLINDER fade-out. Record 102 readable end to end. | device-confirmed | §6 |
| FX-09 | 2026-08-25 | BLACKOUT excludes D, STROBE excludes A **and** B → `f8` 1 → 3: the exclusion field is a genuine bitmask. Master brightness 80 % **wrote nothing** — the first setting shown not to be project data. | device-confirmed | §6 |
| FX-10 | 2026-08-25 | WOLF excludes group F → `f10` = 32. Record 102 is closed except `f11`, which F11-01 then measured as inert. | device-confirmed | §6 |
| F11-01 | 2026-08-26 | `102.f11` written ourselves, 100 → 0, uploaded and compared → **no visible change, and 2048 DMX channels identical** over two 12-second envelopes; then two more with the **blinder active**, 0 channels differing while the blinder itself plainly moves 48. The BLINDER hypothesis is refuted; the field is unattributed and inert. | correlated | §6 |
| F11-03 | 2026-08-26 | `Button brightness` 100 % → 14 % → **not one record changed**. The setting is controller-global. The prediction it was meant to test could not have been tested — see the refutations above. | observed — its own prediction refuted | §6 |

### Record 165 — the preset, and its masks

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| F4-01 | 2026-08-26 | Six `PRESET EDIT` screens photographed, no write → `f4` is a **bitmask**, not an enumeration (`Searchlight` lights three toggles at once). The bit assignments it published are **retracted** by F4-02. | shape device-confirmed, bits retracted | §5.3 |
| F4-02 | 2026-08-26 | Two toggles switched off on two presets, one save → **`f10`** moved, `f4` did not. `f10` is the six toggles in screen reading order, a set bit meaning **OFF**; six photographs re-read without a contradiction. Then confirmed in reverse, byte for byte: toggling off, on and off again returns the project to identical bytes. | device-confirmed | §5.3 |
| F4-03 | 2026-08-26 | Corpus cross of `f4` against the `f16` engine masks → `f4` is a **permission mask** over the three engines, one-directional; slice 2 of `f16` is the Beam FX; slice 7 is the strobe (two presets in 2446); slice 5 is the static layer, hypothesized. | correlated | §5.3, §5.4 |
| F7-01 | 2026-08-26 / 08-27 | First shot, a negative: recalling `Get Moving` moves 110 channels, so `f7` cannot be isolated from an envelope. Second shot on the panel: `f7` is the **Color FX page selector** per group — and both the earlier correlation and its attribution were refuted on the way. | device-confirmed | §5.6 |
| F7-02 | 2026-08-27 | Group C set to `MOVE FX2` and saved → **nothing moved in record 165**. The rival at p = 0.25 won: a project save does not write the live page; only a `SHIFT` + pad capture does. The version counter incremented while **all 45054 payload bytes stayed identical** — an increment proves nothing about content. | validated → device-confirmed | §5.6 |
| F7-03 | 2026-08-27 | The same state **captured** into a preset → `f23` = `[0,0,1,0,…]`, exactly as predicted, and `f7` rigorously unchanged. `165.f23` is the Move FX page selector; the record lays its engines out in regular quadruplets. The prediction about `f16` slice 1 was **wrong** (see refutations). | validated | §5.6 |
| F7-04 | 2026-08-27 | Group A to `BEAM FX2`, captured → `f3` = `[1,0,0,…]`, and the two earlier selectors did not move by a byte. The quadruplet holds on all three engines. The operator's unplanned control — setting B to `BEAM FX1` explicitly — showed that a hand-set page 1 is **indistinguishable** from a page never set. | validated | §5.6 |
| F11-02 | 2026-08-26 | Four `f11` values against six photographed screens → `f11` is **FADE in milliseconds**, every value as predicted. Negative in the same shot: the screen's `COLOR` line does not read `f31`, and where it reads from is open. | device-confirmed | §5.3 |
| FLASH-01 | 2026-08-26 | `WOLF` latched, preset overwritten, one save → the prediction (`f12`/`f20`) is **refuted**; `f16` slice 6 rises to **511** — all nine slots. Took one of our own identities with it. | device-confirmed | §5.7 |
| FLASH-02 | 2026-08-26 | `BLINDER` latched → slice **9**, and slice 6 falls back to 0 in the same capture. The positional inference from FLASH-01 is **retracted**: two points were consistent with the order and with other arrangements. | device-confirmed | §5.7 |
| FLASH-03 | 2026-08-26 | `BLACKOUT` latched → slice **8**, while slice 9 stays up because the key was still down. Two flash engines at once: the slices are independent, not a one-of-N selector. Three points, and still no order. | device-confirmed | §5.7 |
| FLASH-04 | 2026-08-26 | `SMOKE` latched → **no slice rose**. Closed by FLASH-05's capture, where `SMOKE` was demonstrably held alongside `STROBE` and wrote nothing. | correlated → device-confirmed | §5.7 |
| FLASH-05 | 2026-08-26 | `STROBE` latched → slice **7**, value **511**, not the 255 that `Fire!` and `Strobe` carry: the flash key and a preset's own strobe engine are different authors. | device-confirmed | §5.7 |
| FLASH-06 | 2026-08-26 | `SPEED` latched → slice **10**. **Retracts** "SPEED has no slice, by symmetry", and with it the rule that "has an exclusion mask in 102" ⇔ "has a slice in `f16`" — exact on the five measured at the time, false on the sixth. | device-confirmed | §5.7 |
| FLASH-07 | 2026-08-26 | `SMOKE` alone latched, everything else released → nothing rose. The cleanest form the experiment can take: one key active, the only candidate left, not a bit written. Slice 11 did not move either. | device-confirmed | §5.7 |
| FLASH-08 | 2026-08-26 | The reverse direction: three presets written with one flash slice each, deployed, recalled → all three fired their predicted key. **But only after a manual reopen** — a deployed project is stored, not live, and `RESTART` does not substitute. | device-confirmed | §5.7, §10.1 |
| FLASH-09 | 2026-08-26 | Two preset entries duplicated into a file, deployed → the controller returned 83, not 85. Read as "the device deletes entries it did not create". **Retracted** by PRESET-01: the pre-flight download showed the state had been misattributed. The drop happens at reopen, not at store. | retracted; the snapshot pair survives as a check fixture | §10.1 |
| FLASH-10 | 2026-08-26 | Slices 9 and 10 written into a file and recalled → both fire. The five flash slices are confirmed in **both directions**. Presets 83 and 84 exist, which is what re-opened the FLASH-09 question. | device-confirmed | §5.7 |
| PRESET-01 | 2026-08-26 | Pre-flight download before the planned experiment → 85 presets, ids up to 84: the previous day's headline **collapses before the experiment runs**. All three predictions then held on the deploy, and `f16` slices 9/10 became device-confirmed in the write direction. | device-confirmed | §10.1 |
| PRESET-02 | 2026-08-26 | Planned discriminating deploy with `f1` bumped to 83. Overtaken by PRESET-01's result. | planned, superseded | §10.1 |
| PRESET-03 | 2026-08-26 | A named preset written at page 5 slot 20 (id 99), hands off → the pad does not appear before a manual reopen, and on reopen the panel **rejects the project outright** — the first rejection ever measured. Refuted in an unforeseen direction. | observed | §10.1 |
| PRESET-04 | 2026-08-26 | The same, with the id gap filled → **dense ids still refuse to load**. The gap was not the variable. | observed | §10.1 |
| PRESET-05 | 2026-08-26 | One entry, a 23-byte name → the loader refuses. The **19-byte name limit** is the loader's, and exceeding it bricks the project open. | device-confirmed | §5.8 |
| PRESET-06 | 2026-08-26 | The same with a 16-byte name → it loads. The A/B pins the failure on name length and clears the rest. | device-confirmed | §10.1 |
| PRESET-07 | 2026-08-26 | A sparse layout, matching what the device's own save writes → loads. `SET_PRESET.f2` re-read as the entry **position**, 0-based and clamped — itself later refuted by RECALL-01/RAW-01. | device-confirmed on the file side; the `f2` reading refuted | §10.1, §10.2 |

### Static layers — colour, gobo, position

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| F29-01 | 2026-08-26 | Three read-only DMX envelopes, nothing written → the static gobo index is **0-based**, 255 = none. All three matched the published 0-based prediction; the 1-based alternative predicted different values. Closing envelope 2048/2048 against baseline. | device-confirmed | §5.1 |
| F30-01 | 2026-08-26 | Four read-only captures → five stored `PATTERN` values read off factory presets, and the eleven-entry icon list read off the encoder. **Retracts** "one scalar replicated eight times" — the screen shows three groups on different values at once. | device-confirmed | §5.1 |
| F30-02 | 2026-08-26 | The whole list walked live on group B, eight captures, each predicted in writing first, **nothing written** → seven exact; element 7 corrected the share rule. `FLASH` makes a group's pads **momentary**, not a spatial layout. | device-confirmed | §5.1 |
| F30-03 | 2026-08-26 | Two more captures at three colours in both geometries → the distribution rule, complete: deal in ascending pad order over the run, split as evenly as possible, remainder to the earliest colours. Enough to generate a static look for any rig. | device-confirmed | §5.1 |
| F30-04 | 2026-08-26 | One save, three groups on three patterns with three colour selections → `f30 = [4, 3, 8, 0…]` and three different masks, **every value exact**. The first non-uniform `f30` ever observed, after 2033 corpus presets carrying one value on all eight groups. | device-confirmed | §5.1 |
| GOBO-01 | 2026-08-26 | Five `STATIC GOBO` features set on group A, downloaded → **refuted on the published branch**: the features are live state and a save does not write them. It refutes the experiment, not the five-arrays reading. | refuted | §5.1 |
| GOBO-01 | 2026-08-30 | Where the gobo icon library lives: a table of 800 30-byte entries at the tail of the resource flash, each pointing at a 24×24 RGB565+alpha icon; the entry index **is** the gobo id read from `145.f2`. | validated | §3.4 |
| GOBO-02 | 2026-08-26 | The corrected experiment — features set, then `SHIFT` + tap to capture, then save → the five gobo features named. **Retracts** GOBO-01's guess at which fields they were. | device-confirmed | §5.1 |
| PAL-01 | 2026-08-27 | A palette colour (record 140) written by us and recalled → the written pad comes out at the channel, exactly. The last approximation on the intention → DMX path closes. | device-confirmed | §3.3 |
| RENAME-01 | 2026-08-30 | Eleven gobo names written outside the device and deployed → all eleven appear on their pads after a reload. Names cap at **19 UTF-8 bytes** (unmeasured here, taken from PRESET-05, so the tool refuses longer). | device-confirmed | §3.4 |
| SORT-01 | 2026-08-30 | The `f3 = 14` ranges of record 111 permuted, each keeping its DMX bounds → the page reorders exactly, and the firmware accepts a **non-monotonic** range list without re-sorting. The wire order **is** the pad order. | device-confirmed | §3.4 |

### Positions — records 150, 151 and 106

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| POS-01 | 2026-08-26 | One read-only capture, `Crowd` recalled on group A, 301 frames → tilt exact six for six; `106.f5`/`f6` are the **travel limits**. Pan missed by rounding and decoded `FAN` by the miss. | device-confirmed (limits), correlated (FAN) | §7.5 |
| POS-02 | 2026-08-26 | The discriminator: `Ceiling` stores `FAN = 50 %`, so the ramp must collapse → both halves held, every fixture at 50 % of its own band. | device-confirmed | §7.5 |
| POS-03 | 2026-08-26 | A moving head **detached** for independent control, one save → exactly two records moved; record **151** is the detached-fixture positions, and `150.f1`/`f2` are a slice of it. Its own prediction was built on the wrong model and was withdrawn before it was ever measured. | device-confirmed | §8.1 |
| POS-04 | 2026-08-26 | Two photographs of the `POSITION` editor → record 151 decoded end to end, with no measurement at all. | device-confirmed | §8.1 |
| POS-05 | 2026-08-26 | `Ceiling` recalled after the detach → **four channels changed in 2048**, and the 16-bit model turns an approximation into a measured value. | device-confirmed | §8.1 |
| POS-06 | 2026-08-26 | A second detach with a large `TILT OFFSET` → `151.f1` is the **fixture index**, and it had been there all along. Retracts a line written earlier the same day. | device-confirmed | §8.1 |
| POS-07 | 2026-08-26 | `Crowd` recalled after the second detach → **two channels changed in 2048**, exactly the pair `151[5].f1` names. Every term measured, none fitted, across four captures and 24 predicted values. | device-confirmed | §8.1 |

### The patch, and the DMX mapping table

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| MAP-01 | 2026-08-31 | Where the DMX mapping table lives → record **130**, in the project file. Closes lead L5, and the trap it cost is written into `AGENTS.md`: a record that already carries a name is not a record that was measured. | device-confirmed | §7.3 |
| MAP-02 | 2026-08-31 | Two sub-steps, two saves, one trip to the panel → the table reads in full. | device-confirmed | §7.3 |
| MAP-03 | 2026-08-31 | A channel moved away and back, then saved → **nothing is written**: a genuine write and its return leave no trace. "Touching an entry moves it" is refuted, second counter-example. | observed | §7.3 |
| MAP-04, MAP-05, MAP-06 | 2026-08-31 | Eleven saves, one variable each, a download between every one → the table is closed, and MAP-06 verifies the **write** on the device. | device-confirmed | §7.3 |
| MAP-07 | 2026-08-31 | Our encoder reproduces the factory table byte for byte, with no device at all. | validated | §7.3 |
| MAP-08 | 2026-08-31 | A file we wrote deployed onto a device holding 13 entries **in a different order** → read back unchanged: the device renormalises nothing. Deleting and ordering are ours to do. | device-confirmed | §7.3 |
| MAP-09 | 2026-08-31 | The ten remaining functions in one save → the table is complete, and the writer covers all of it. | device-confirmed | §7.3 |
| MAP-10 | 2026-08-31 | Ten entries **created** by our encoder, deployed → accepted **at the byte**, not merely "a file that loads". Deliberately using values the factory never writes, so a wrong field would be visible and refutable. | device-confirmed | §7.3 |
| MAP-11 | 2026-08-31 | The return to factory, produced by the show compiler from the device's own state → record 130 identical byte for byte to the factory table. | device-confirmed | §7.3 |

### Failures of the device, and of the data

Two findings that carried no id until the ledger was written. They are numbered
here for the first time — a new number for something previously unnumbered, not
a renumbering of anything.

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| BUG-01 | 2026-08-25 | A real blackout on the operator's rig, diagnosed from the file alone → record **120** emptied for every fixture but the first, 251 of 258 entries reduced to `2a 00`, which reads back as 0. Matches a documented 2.0.x bug family and the 2.0.18 changelog entry that fixes it. The patch itself is intact. | erasure observed, cause hypothesized | — |
| LOSS-01 | 2026-08-31 | Four projects vanished from the controller between the 30th and the 31st, **outside any run of this harness**, with no delete command. The harness's own snapshots from 25 August gave them back, hashes intact. No reading is offered: the device is not perfectly healthy, and that is all the traces support. **Later the same day** (SPLIT-01) the controller reported 4 projects again, the missing one among them at its August version: the loss was **not permanent**, which explains nothing but is a fact the entry lacked. | observed | — |

### The USB protocol

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| MODE-01 | 2026-08-25 | `watch-mode` polling `GET_SETTINGS` while the operator walked the front panel, **zero writes** → 19 modes named in firmware 2.0.18, 14 device-confirmed. `SMOKE` and a single `BPM TAP` change no mode. | device-confirmed | §10.2 |
| SETP-01 | 2026-08-26 | `SET_PRESET` payload discovery, one encoding at a time → recall by id works, missing ids are silent no-ops. The reading of *what the payload is* was wrong and is repaired by RAW-01. | device-confirmed | §10.2 |
| SETP-02 | 2026-08-26 | Four candidate reload events → **no protocol event replaces the live copy**. Judged on a discriminator later refuted (RECALL-01); re-proved by RELOAD-03 on a repaired one. | device-confirmed, via RELOAD-03 | §10.2 |
| RELOAD-01 | 2026-08-26 | Static read of WTOOLS 2.0.2, then an attempted USB capture → **the capture is not available on this machine** (`XHC20` refuses to come up). The static read gave names only, `[observed]`. | observed | §10.2 |
| RELOAD-02 | 2026-08-27 | A WTOOLS push, judged on the repaired discriminator — counting distinct appearances over 10 `SKIP_PRESET` → a push **does not** make the pushed project live. | device-confirmed | §10.2 |
| RELOAD-03 | 2026-08-27 | The four SETP-02 negatives replayed on the repaired discriminator, under the same UUID → they hold. The original result was not an artefact. | device-confirmed | §10.2 |
| RELOAD-04 | 2026-08-27 | Verdict for the session: **no reachable event reloads the live copy**. Only a manual open on the panel does — and that screen (mode 26) *is* reachable remotely, which is the consolation prize. | device-confirmed | §10.2 |
| RELOAD-05 | 2026-08-27 | The instrument calibrated on **both** arms: the discriminator had never been seen to fire, so the 6-entry file was opened by hand and the series replayed. | device-confirmed | §10.2 |
| RECALL-02 | 2026-08-27 | One continuous DMX stream with timestamped transitions, on the very project SETP-01 was measured on → what event 41 actually does. Kills "f1 = 22 → Deep Green" outright rather than merely contesting it. | device-confirmed | §10.2 |
| RECALL-03 | 2026-08-27 | Bytes recalled one at a time against a live copy whose ids and positions diverge only at the tail → the byte is the **id**, not the position. The position reading is refuted twice over. | device-confirmed | §10.2 |
| RECALL-04 | 2026-08-27 | A live copy of 6 entries, ids 0…5, so every id ≥ 6 is absent → **an absent id does nothing**, and the two rival readings predicted opposite frames. | device-confirmed | §10.2 |
| RECALL-05 | 2026-08-27 | The **interior** hole, which RECALL-04 could not reach: every absent byte it fired was above the highest present id → an interior hole does nothing either. A single-variable differential in the same shot showed a recall does not touch the position layer. | device-confirmed | §10.2 |
| RECALL-06 | 2026-08-27 | Ids ≥ 128, the last unprobed range of the byte → recall is exact beyond 127. Refutes, a second time, the idea that something masks the high bit. | device-confirmed | §10.2 |
| RAW-01 | 2026-08-27 | Found by sweeping `SET_MODE`'s field numbers → **the payload is not protobuf**: `payload[0]` is the index, and the device had been reading our *tag* byte all along. Re-reads the RECALL-01/02 retractions: the addressing existed, our encoding hid it. | device-confirmed | §10.2 |
| RAW-02 | 2026-08-27 | Five payloads per event, mode re-read each time → the **second byte is not read**. | device-confirmed | §10.2 |
| MODE-39/40 | 2026-08-27 | Raw indexes 39 and 40 sent from HOME, with a COLOR FX escape after each → 39 reports 39 and leaves the screen alone; 40 lands the device on mode **42**. The behaviour is device-confirmed; the *names* are hypothesized by elimination. | device-confirmed (behaviour) | §10.2 |
| MODE-40/42 | 2026-08-27 | Index 40 → the **USB STICK** screen, with project, fixture and full-backup import/export. Reachable only by raw index. | device-confirmed | §10.2 |
| PROJECTS-01 | 2026-08-27 | Index 26 → *main menu → Open*, with the list of six stored projects on screen. This is the screen that reloads, and it is reachable remotely. | device-confirmed | §10.2 |
| SCREEN-01 | 2026-08-27 | A sequence of indexes at 5-second intervals, operator watching → **the reported mode is not the displayed screen**. One clause of the entry was retracted the same day. | device-confirmed | §10.2 |
| SCREEN-02 | 2026-08-27 | How to leave a modal screen, and what that says about the menu. | device-confirmed | §10.2 |
| SCREEN-02 | 2026-08-31 | Which indexes actually move the panel → **pushable {1, 3, 4, 26}, inert {0, 5, 16}**. The *target* decides, not the screen you start from; "only modals are pushable" was refuted by indexes 4 and 5, and one of the six measures refuted its own prediction. WTOOLS uses the same `setWMMode`, so there is no private channel. | device-confirmed | §10.2 |
| SCREEN-03 | 2026-08-27 | The three indexes that would not move the screen, replayed on **another live copy** → the panel yields to keys, not to `SET_MODE`. Two distinct paths, and nothing has yet measured which one the panel follows. | device-confirmed | §10.2 |
| LINK-01 | 2026-08-27 | Seen five times in one day, always identically: after a pause, or after another process held the port, the **first** request times out and the next succeeds. | observed | §10.2 |

### The resource-flash upload

Four readings taken on 2026-08-31 from files already on the machine — the five
retained WTOOLS logs and the installed bundle. **No device operation, no byte
sent, no port opened.** They are here because they are the only state known of
the channel that writes the resource flash, and because one of them contradicts
something this repository publishes as `device-confirmed`.

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| UPLOAD-01 | 2026-08-31 | The retained WTOOLS logs read on this machine → the flash upload travels on the **same tty as everything else** (`SerialPortAgent : Opened serial port (/dev/cu.usbmodem…) as read/write`), not on a raw USB pipe. RELOAD-01 went looking for a USB capture and found this machine could not make one; the channel it wanted to watch is a serial port, and the vendor's own log is the instrument. RELOAD-01's measurement stands — nothing is refuted — its **orientation** is superseded. | observed | §10.2 |
| UPLOAD-02 | 2026-08-31 | The two sessions that carry an upload, counted and timed → **180** `setFlashDataChunks` messages each, the same shape twice: one message, refused, then **179** at a 163 ms median. `wolfmixFlash.bin` is 2 931 442 bytes, and 16 384 is the only candidate chunk size that divides it into exactly 179 messages (178 full, then 15 090). Read as one control message plus 179 chunks — the log names message *types*, never payloads or lengths, so nothing here has seen a chunk. Prediction published before the measurement that will settle it, in `corpus/experiments/UPLOAD-02/prediction.md`. | hypothesized | §10.2 |
| UPLOAD-03 | 2026-08-31 | The three binaries of the installed bundle hashed against the `files` list of the `changelog.json` shipped inside it → **three matches out of three**. The factory image is present and provable, so a copy taken outside the WTOOLS folder is a verified restore point and not a copy of whatever was there. Local integrity only: the manifest travelled inside the same bundle and says nothing about what the vendor's server served. `gobo_run.py`'s gate 0 re-runs the comparison on every run. | observed | — |
| UPLOAD-04 | 2026-08-31 | The two upload sessions read against what `docs/gobo-icons.md` §5 publishes → both were **refused at their first message** (`UNSAVED_PROJECT`, *Save project before updating*), and the 179 that followed came after the operator saved and clicked again; yet the upload itself is published `device-confirmed` for the same day, on the magenta-icon write and its undo. The disagreement is written rather than resolved: nothing here establishes what the device does with a refused first message, and no claim is added to §5 about what it keeps. | observed | §10.2 |

The boundary question stays **open**: nothing above establishes whether
executable firmware and the resource flash travel on the same message.
`tools/wolfmix.py` gains no event, and this repository still writes no flash of
its own.

### Reading a fixture profile off the controller

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| PROFILE-01 | 2026-08-31 | `GET_PROFILE` (event 3), allowlisted since the start and never called, sent with the same UUID payload `GET_PROJECT` takes. Prediction published first: same payload (0.6), a different field layout (0.25), a refusal wanting an index (0.15) → **the first held**, and the reply is plain protobuf. `f1` UUID, `f2` name, `f3` the body, `f4` version in ms epoch, `f5` brand; in the body, `f1` per channel, `f3` per preset band, `f4` the mode table. The consequence is the point: the `.wmx` fixture library on disk is encrypted with no public key, and the controller hands the same content over **in the clear**. The layout now lives in `PROFILE_FIELDS` and `decode_profile`, not in prose. One profile family, three reads — swept by PROFILE-02. | device-confirmed | §10.2 |
| PROFILE-02 | 2026-09-01 | The sweep PROFILE-01's risk table asked for: **221 profiles across 60 brands**, 1 to 58 channels, 27 of them carrying two gobo-wheel channels, decoded and checked for fields the tables do not name → **no `unknownFields`, anywhere**, and every channel type in all 221 lies inside `ssl2.TYPE_CANAL` — the enum the controller and the `.ssl2` writer share, corroborated well past the eleven values PROFILE-01 had checked. Three of PROFILE-01's sub-readings were **refuted** by the same sweep: the body's `f2` link table is **not ×16** (16 in 15 profiles out of 221; it holds one entry per mode-channel, `len(f2) == Σ modes[].channelCount` in 221/221), the body's `f5`/`f6` are **not always zero** (one profile reads 6400 / 2358, two omit both), and the mode table's `f3` is **not always 1** (15 distinct values over 498 modes). None of the three is named in the decoder, so each surfaced as a value under its neutral `fN` key rather than as a wrong name — which is what the neutral keys were for. | device-confirmed | §10.2 |
| PROFILE-03 | 2026-09-01 | The preset `f4` disagreement, measured over **13 291 preset bands** of the sweep: `research/versions.md` read `f4` as the channel type of what the band acts on, `ssl2.CIBLE_PRESET` maps a `.ssl2` **preset** type to a target channel type. → **two different axes, neither reading wrong.** `f4`'s domain is 26 values, every one of them in `TYPE_CANAL`, and **not one** of the 17 numbers that are in `TYPE_PRESET` but not `TYPE_CANAL` ever appears — so `f4` is a channel-type number, not a preset type. It equals its own channel's declared type in 82.6 % of bands and names the band's function in the rest (a `Generic` channel whose band is a colour selection, a `Prism Rotation` channel whose index band reads 21 `Prism Index`). `SSLPRESETTARGET` is a channel **index** within the mode, resolved by `CIBLE_PRESET`'s rule — a different question from what `f4` answers. **No equivalence is encoded in either tool**, and none should be: `CIBLE_PRESET` stays the 97.4 % statistical derivation it was. | device-confirmed | §10.2 |
| PROFILE-04 | 2026-09-01 | Whether `GET_PROFILE` serves the locally-authored profiles whose identifiers are derived from the device serial, or only the vendor library → **it serves them**, both of them, decoded by the same tables with no `unknownFields`. They are visibly written by a different encoder: every zero-valued scalar is omitted, so channels come back as `{}` or `{"index": 1}` where a vendor profile writes explicit zeros. Their brand also **disagrees between two events**: `GET_PROFILE_LIST` reports one brand for both, `GET_PROFILE` reports a different one for the first and none at all for the second. Recorded, not resolved. Neither identifier is reproduced here ([`../LEGAL.md`](../LEGAL.md)). | device-confirmed | §10.2 |
| PROFILE-05 | 2026-08-31 | Record `116.f9`, published as a "16-byte profile hash" since the corpus mining, parsed as a UUID across the whole variant-A corpus → **293 of 357 entries are RFC 4122 v5**, and the residue of 64 is the two locally-authored profiles PROFILE-04 reads off the device, whose identifiers are serial-derived. `116.f9` is the profile **UUID**: the `.wpj` and the controller share one key space, and it is the identifier `GET_PROFILE` takes. Nothing here parses as a digest of anything. **BREAKING**: the codec key `hash` is removed, not aliased — `116.f9` is `uuid`, dashed, and the corpus round-trip stays byte-exact in both directions, the two serial-derived identifiers included. No version validation: refusing a non-v5 identifier would refuse a project the operator owns. | correlated | §7 |

### Firmware provenance

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| FW-01 | 2026-08-27 | The vendor's own changelog, read on this machine → `165.f10` bit 5 was called **`DIMMER`** until 2.0.15 and `OTHER` since. The measuring firmware (2.0.18) is later than the rename. | observed | §5.3 |
| FW-02 | 2026-08-27 | Same source → `f32`–`f35` are dated to firmware 2.0.5, which dates schema 10. Three corroborations in one line, on a reading already device-confirmed. | observed | §5.3 |
| FW-03 | 2026-08-27 | The discriminator FW-01 left planned: write bit 5 **and nothing else** → `OTHER` gates the dimmer of a static cue and nothing more, on this scope. It is what lifts GEN-02's bit back from `hypothesized`. | validated | §5.3 |

### Read coverage

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| COV-01 | 2026-09-01 | Every byte of a variant-A project attributed to a named field, an unnamed one, or a schemaless record, with the three asserted to sum to the file → the corpus reads **62.4 % / 27.8 % / 9.8 %**. Most of the gap was not undiscovered but **unpromoted**: records 102, 106, 110 and 155 had full field tables in SPEC.md and no codec schema, and so did `150.f3`/`f4`/`f6`/`f7`, `165.f4`/`f11`/`f15`/`f16`/`f18` and the engine-specific `f3`/`f5` of the FX sub-message. Promoting only what the ledger already supported, with a byte-exact round trip throughout, takes it to **87.6 % / 10.6 % / 1.8 %** — 48.4 % of the file named by a device-confirmed reading, 26.6 % correlated, 12.7 % validated, and nothing named without an entry in the ledger. | correlated | §3 |
| COV-02 | 2026-09-01 | Whether `165.f27` is really zero everywhere → **refuted**, see above: 26 presets carry `[1000] × 8`, split by author (WTOOLS writes 1000, the panel writes 0). Q1's blocker — "no cheap discriminator has emerged" — no longer holds. | observed | §5.6 |
| COV-03 | 2026-09-01 | Whether record 120's entries are structurally empty on this rig → **no**: 10 754 of 14 698 carry content. The all-empty file is *rig-c-bug*, which is BUG-01's erasure. | correlated | §7 |
| COV-04 | 2026-09-01 | Field 1 as the item count, swept over every record type → exact on **15** of them, with an empty table writing no field 1 at all rather than a zero. `165.f1` is **not** the count: it disagrees on 19 files, always low by exactly the entries a preset capture appended (81 against 83, 81 against 85). Whatever it counts, it is not the entries present. Now `comptes_de_tete` in `wpj_identities.py`. | correlated | §3 |
| COV-06 | 2026-09-01 | Record 161, SPEC's Q8 — "three opaque blobs of ~190 bytes", the only record type with no schema — asked whether the blob is packed varints, the shape `155.f4` turned out to have → **it is**: exactly **188 values** in all 228 occurrences (76 files × 3 items), while the byte length varies 189/190/191 because some values pass 127. Reading it as a byte array works by accident, which is the same trap 155 sprang. The rest of the record is regular too: `f1` takes exactly three values, one per item position — **21, 15, 19**, constant across the whole corpus — `f2` is 1, `f4` is 1 or 2, and the record's own `f1` is **9** against 3 items, so the field-1-is-the-count identity does not hold here. The array is nearly all zeros: two or three non-zero values at the head and one at index 187, which is 160, 176 or 240. **Nothing is named**: this is the shape, not a reading, and 161 stays passthrough. But it is no longer opaque. | observed | §11 |
| COV-08 | 2026-09-01 | `150.f8`, the CROSS half of the POSITION screen — 1.90 % of the corpus and the largest unread field left, `[hypothesized]` in §3.2 and never read off a screen. **No write, no save, no deploy**: the experiment project already holds a slot where it is not neutral. Prediction published before the measurement, with the two competing readings — unsigned `v/65536` (54) against signed `(v−32768)/32767` (10) — and the collision check that neither lands on another value of the same screen. The measurement carries its own control: PAN, TILT and FAN are device-confirmed, so 60 / 7 / 50 on screen is what says the panel holds the state the prediction was computed from. Full sheet: [`corpus/experiments/COV-08/prediction.md`](../corpus/experiments/COV-08/prediction.md). **Measured, two slots, five photographs, nothing written.** `f8` is `CROSS` on the **unsigned** scale: the screen read **55** where the unsigned reading predicts 55 and the signed one 10, then **50** where they predict 50 and 0. Prediction 3 held, prediction 4 refuted. `FOCUS OFFSET` is confirmed signed in the same shot — 32768 shows **0 %**, not 50 %. The control held on identity rather than on value: the screen's header reads the group-A name record 125 carries, and the ALL POSITIONS page reproduces the palette slot for slot, group A's operator-named first slot against `Floor` on the others. | device-confirmed | §3.2 |
| COV-10 | 2026-09-01 | Whether `165.f27` is the per-group **position FADE**. COV-08's photographs show the `ALL POSITIONS` page carrying one `FADE` per group, printed in seconds, reading `0s` on a project whose every preset has `f27 = [0] × 8`. 1000 would be 1 s, `f11` and `f15` are already milliseconds, and `f27` sits immediately before `f28`, the per-group position index — two per-group tables side by side. The measurement **writes nothing**: `WMX EXP05` is on the controller with `[0] × 8` and `[1000] × 8` on two adjacent pads, so two recalls and one screen settle it in both directions. Sheet: [`corpus/experiments/COV-10/prediction.md`](../corpus/experiments/COV-10/prediction.md). **Measured, both directions, and the unit is named.** Recalling a preset carrying `[1000] × 8` puts group A's `FADE` at exactly `1s`. Then the second point, published before the download because one point cannot separate a unit from a table: `FADE` set to **3 s** on group A alone and captured into a new preset → that preset carries `f27 = [3000, 1000, 1000, 1000, 1000, 1000, 1000, 1000]`. Three points on one line — 0 ↔ `0s` on a panel-composed project, 1000 ↔ `1s`, 3000 ↔ `3s` — so the unit is the **millisecond**. The seven trailing 1000s are their own control: they are the live state the recall had just installed, captured unchanged. **One save, one preset created, not one existing preset altered by a single field.** Measured on group A only — no fixture sits on the other seven here (COV-13 records what else the save touched). | device-confirmed | §5.6 |
| COV-11 | 2026-09-01 | **`SHIFT` + an encoder puts the POSITION screen into two decimals**, found at the panel. It is also a fine adjust, so the four values of group A's first slot moved and were saved; the download shows **one record changed and one slot in it**, which makes the pair a clean single-slot differential. At 100× the resolution the display formula stops being ambiguous: PAN 35093 → `53.55`, TILT 23009 → `35.11`, FAN 32807 → `50.06` all land on **unsigned `v/65536`**, and FOCUS OFFSET 65515 → `99.94` lands on **signed `(v−32768)/32767`**, where the unsigned reading would have printed `99.97`. Four independent points, and **rounding takes 4/4 against truncation's 0/4** — COV-09 re-measured at two decimals instead of zero. The consequence is a method, not a field: every future position measurement should be read this way, because a two-decimal reading discriminates hypotheses that a whole-percent one cannot. Snapshot `COV-11`. | device-confirmed | §3.2 |
| COV-12 | 2026-09-01 | Record 150's unnamed slots are **named by the firmware**, `Position N` with N the 1-based slot index, exactly as record 145's unnamed pads print `Gobo N` (§3.4). Read off the `ALL POSITIONS` page of a project whose stored palette names slots 1, 6 and 11–14 and leaves the rest absent: the screen prints the four stored names where they exist and `Position 2`, `Position 3`, … everywhere else. The same page also confirms the archive reflects the controller — twenty slots, name for name. **A writer must not expect to find these strings**, the same trap §3.4 records for gobos. | device-confirmed | §3.2 |
| COV-14 | 2026-09-01 | `f16` slice 1 = `move_fx_active` — `correlated 45/45`, 3697 presets, asserted as an identity — **refuted** by the preset the device composed for COV-10: slice 1 = 1 against `move_fx_active` = 0. See the refutations. `slice 1 ⊇ move_fx_active` survives, exact, and still kills the stride-8 alignment on 1767 presets. Slice 0 against `color_fx_active` now fails both containments and is asserted at neither. The slice value domain SPEC gives as `{0, 1, 2, 5, 7, 255, 511}` is also stale: **3 and 4 occur**. | device-confirmed | §5.4 |
| COV-16 | 2026-09-01 | `120.f1` — record 120 is 2.0 % of the corpus and named nothing inside. Laid out in **ascending DMX-address order** (what §7 says the blocks follow, not the item order of 115) the table is **constant per profile**: four identical ten-entry blocks for one par model, two identical sixteen-entry blocks for the moving heads. Prediction published first, built only from the **26 channels record 106 gives no role**, of which eight are non-zero → **all eight exact off the live frame**: 4 on channels 108/118/128/138, 127 on 109/119/129/139, and none of the eight moves in six consecutive change frames while an effect drives ten other channels. `120.f1` is the channel's **DMX value**, emitted wherever no engine claims the channel. Prediction 2 was **wrong in a useful way**: several role-free channels are *not* idle, because a 16-bit pair is driven on both halves while only its principal appears in 106 (POS-05) — "no entry in 106" is not "not driven", and a future test must exclude fine channels too. `f4`, `f5`, `f6` stay unnamed. Sheet: [`corpus/experiments/COV-16/prediction.md`](../corpus/experiments/COV-16/prediction.md). | device-confirmed | §7 |
| COV-15 | 2026-09-01 | `115.f9`, which §10 reads as "the fixture's **sequential index** (0 omitted, then 1…19)" from one rig's canonicalisation → **the index reading is wrong**. It is a contiguous ascending run in 68 of 80 corpus files, but the run does not always start at 0: a six-fixture project carries **20…25**. A position index cannot exceed its own count. What it is — a creation counter, a stable per-fixture identifier — is not settled here, so nothing is named; `f9` keeps its neutral key. The 12 files with no run at all are the rig-a family, where the field is simply absent. | correlated | §10 |
| COV-13 | 2026-09-01 | Side effects of the COV-10 save, recorded because a "single-variable" claim has to survive looking at the rest of the file. One save, version 5 → 6, **one preset created and not one existing preset changed by a field** — but two other records moved, both canonicalisations rather than edits. `115`'s six fixture entries each **gained `f6 = 2`**, absent before; and the seven empty gobo palettes of records 145 went from 123 bytes to 42, i.e. from the "empty slot" form (`f1 = ' '` × 20) to the "wholly empty" form (`2a 00` × 20). §3.4 documents both forms and requires a writer to reproduce whichever it read; what is new is that **a controller-side save converts one into the other**, which is a second instance of the rule §10 already states — a device save is not byte-preserving. Neither touches record 165, so COV-10 stands. | observed | §10 |
| COV-09 | 2026-09-01 | The published COV-08 prediction was **wrong by one** on six of eight values, and the cause is a rule this repository applies everywhere: "the display truncates". On the POSITION screen it **rounds**. Seven of the eight readings discriminate between the two, and rounding matches **8/8** against truncation's 1/8 — 39976 is 60.9985 % and shows **61**, 32767 is 49.9985 % and shows **50**. The reading of `f8` survives untouched because its two candidates were 55 and 10, which no ±1 can bridge; a measurement whose rivals sat one apart would have been decided by the wrong rule. Truncation stays established on the **colour** picker (§3.3, 127/255 → 49): either the two screens format differently, or one of the two measurements needs redoing. | device-confirmed | §3.2 |
| COV-07 | 2026-09-01 | COV-02's author split applied to the twelve `f16` slices, to see whether a WTOOLS-written project fills what the panel leaves empty → **it does not**, and that is the useful part. Slices **3 and 4 are zero on both sides**, so Q4's "empty in everything reachable from this panel" now also covers everything reachable from WTOOLS 2.0.2. Slice 11 reads {2, 5, 7} from the panel and {2} from WTOOLS — no new contrast. Slice 5 is 255 on every WTOOLS preset, consistent with GEN-03's reading that the panel is what narrows it to the groups a cue lights. A negative result, published because the method that worked on `f27` was tried here and failed. | observed | §5.4b |
| COV-05 | 2026-09-01 | `105.f1` against `115[f5].f3`, both named "profile" by the codec → **they never agree**, on any of the 1394 patch entries. `105.f1` is the library fixture id, `115.f3` an index into record 116: one name covered two key spaces. Renamed `library_id`. | correlated | §7 |

### The FX sub-message

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| FX2-01 | 2026-08-27 | "Double Trouble": firmware 2.0 doubles the FX engines, and the registry is asked whether it can see it → an engine that is on stores two page configurations, `correlated 45/45` — **refuted the same evening** by one preset composed at the panel. | validated (one slice per engine); the prediction and one identity refuted | §5.6 |
| FX6-01 | 2026-08-30 | The three FX screens of the manual read side by side → the registry's "four properties for three fields" count was **wrong**. What it retracts is a count, not a status. | observed | §5 |
| FX6-02 | 2026-08-30 | `Phase` / `Size` / `Fade` set to mutually distinct values absent from the factory vocabulary, `LIVE EDIT` off → the three-way permutation was a **four-way**: `f2` is the fade and the speed is `f9`, after ACC-04 had left `f2` named "speed %" and unexamined for four days. | validated | §5 |
| FX6-03 | 2026-08-30 | The Beam FX `Feature`, three independent sources pointing at one slot and none having measured it → measured. | validated | §5 |
| FX6-04 | 2026-08-30 | `f3` on the movement engine → the **`Fan`**, one byte out of 46414. | validated | §5 |
| FX6-05 | 2026-08-30 | The beam sequencer, hunted in the opaque record 161 → it is in record **155**, behind `f2`, a field that already carried the name "sequence flavour" and had never been opened. 155 was `device-confirmed` with a reading that was too general. | validated | §8 |

### The show generator, and the guards

| id | date | manipulation → result | status | SPEC § |
|---|---|---|---|---|
| GEN-01 | 2026-08-27 | Intention → `.wpj` → deploy → recall, with the rig read from the donor rather than described → `f31` written comes out exactly as it reads; the **dimmers do not**. | device-confirmed | §10 |
| GEN-02 | 2026-08-27 | The operator settles the three open readings, and none wins: the faders are all at 100 % → the missing dimmer was a **controller setting**, off the whole time. `f17` is a percentage and reaches DMX through `106.f5`/`f6`. Downgrades the `OTHER` attribution — see the refutations. | device-confirmed | §10 |
| GEN-03 | 2026-08-27 | Five cues identical but for `f31`, to discriminate the record-102 anomaly → the anomaly is that **the live copy is not the file**: with `LIVE EDIT` on, one gesture at the panel rewrites a cue's live copy while the file stays as uploaded. Refutes "`f16` slice 5 is always 255" (`correlated` over 2446 presets), and the fixture index is sequential with 0 omitted. | device-confirmed | §5.4, §10 |
| SPLIT-01 | 2026-08-31 | Six measures re-running read, named mode, preset recall and one experiment deploy after phase 2 split the device path into four modules → **six conforming**. Measure 4 confirms SCREEN-02's inertia from a *different* starting screen, which is the prediction its author had got wrong. Measure 6's wording was looser than the tool: the read-back differs by SHA-256 and is identical **record by record**, only the version counter at bytes 40–43 moving — which is what `verify_project` compares, and what SPEC §9 measured. | device-confirmed | §9, §10.2 |
| GUARD-01 | 2026-08-31 | The phase-1 refusals, on the device: nine measures checking that each guard refuses **before** anything reaches the link and that none breaks a path that worked → eight conforming, one refuted and fixed in the session. | device-confirmed | — |
