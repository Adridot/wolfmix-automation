# COV-60 — what a slot of `160.f7` indexes (BEFORE measuring)

COV-56 read the **container** of `160.f7` and stopped there: it is the
run-length map `120.f4` uses — under 128 a free run, at or above 128 an
occupied run of `v − 128` — the runs summing to exactly **512** and the
occupied slots numbering exactly `len(f1)`, one per targeted fixture, on all
**594** corpus macros, re-encoding the stored bytes byte for byte.

**What a slot indexes is not read.** The corpus offers two readings and scores
both badly: slot *p* as the DMX channels `[4p, 4p+4)` resolves 2998 of 3470
targeted bits, and slot *p* as a sixteen-channel window at display position
`p // 4` holds on 12 of 30 **distinct** macros. 86 % is what COV-17 refused to
name `120.f5` on, and both fail on the same handful of macros, always on their
non-moving-head entries.

This is the last field on the `partial` list worth an experiment: **0.47 %** of
the corpus, and the biggest single number left after COV-59.

## Why the corpus cannot answer it and one macro can

Every rig in the corpus patches its moving heads at multiples of 16 in display
order, so `address // 4` and `display position × 4` are the **same number** and
have been for every macro ever measured. The clean project is the one place
where they are not — COV-46 deleted fixture 0, so the addresses now start at 16
while the display positions still start at 0, and the two readings differ by a
constant 4.

## The state this starts from

`COV-49/stage3-groupA.wpj`, version **9**, sha256 `ad388a41d63ca45a…`. Seven
`Lyre ZQ02244`, 16 channels each, `display_order` = the identity
`00010203040506`, and **no record 160 at all** — this project has never had a
macro, which is what makes the first one the cleanest case available.

| 115 index | DMX address | group | `slot_id` | display position |
|---|---|---|---|---|
| 0 | 16 | A | 1 | 0 |
| 1 | 32 | A | 2 | 1 |
| 2 | 48 | A | 3 | 2 |
| 3 | 64 | A | 4 | 3 |
| **4** | **80** | **B** | **absent = 0** | **4** |
| 5 | 96 | B | 5 | 5 |
| 6 | 112 | A | 6 | 6 |

> It carries the COV-53 defect — record 120 holds 111 entries against the 112
> the patch justifies, and `_anomalie_120_patch` and `_anomalie_120_alignement`
> both fire. That is expected and is **not** a reason to use another project:
> nothing here touches the patch. Record 120 must come back byte-identical, and
> that is prediction 6.

## Stage 1 — one macro, and the fixture is chosen to split three readings

**On the panel:** `LIVE EDIT` macro edit, a free button, feature **`01 Pan`**,
value **111**, on the fixture at DMX **81** (the file's address 80, base 0 since
EXP-06 — 115 index 4, group B). Value 111 appears nowhere in the corpus's macro
values, which are `{0, 43, 50, 60, 86, 93, 96, 128, 131, 170, 174, 180, 183,
200, 255}`. **Then save. One change, one save.**

That fixture is chosen because its three identifiers disagree: display position
**4**, `slot_id` **0**, DMX address **80**. Its 115 index is 4 and therefore
still degenerate with the display position — stage 2 is what splits that pair.

### The rivals, as exact bytes

`01 Pan` is channel offset 0, so the slot is the fixture's base plus `0 // 4`.

| # | reading | slot | `f7` predicted | p |
|---|---|---|---|---|
| **R1** | slot = **DMX channel group**, `address // 4` | **20** | `[20, 129, 127, 127, 127, 110]` | 0.45 |
| **R2** | slot = **display position × 4** | **16** | `[16, 129, 127, 127, 127, 114]` | 0.30 |
| **R3** | slot = **`slot_id` × 4** | **0** | `[129, 127, 127, 127, 127, 3]` | 0.15 |
| R4 | none of the three | — | anything else | 0.10 |

R3's array would come back **byte-identical to COV-27's**, which is its own
tell. Each of the four sums to 512 and carries exactly one occupied slot, so
the container reading of COV-56 is not on trial here — if the runs do not sum
to 512, that is R4 and COV-56 is what falls.

### The rest of the macro, and the records that must not move

1. `f1` = **[17]** — bits 0 and 4, because the panel drags the fine channel
   with the coarse one and `01 Pan` takes `03 uPan` (COV-27). p 0.85; the rival
   is `[1]`, one bit, p 0.15.
2. `f8` = **[111, 0]** — one value per set bit, in order (COV-20). p 0.9.
3. `f5` = the button pressed, 0-based (COV-19). `f6` **absent**, the panel
   synthesising `Live Edit N`. p 0.9.
4. Record 160 is **created**, going from absent to one macro — the first time
   this repository will have watched that record appear.
5. `len(f7)` = 6 varints. p 0.8 — it is 6 for every single-fixture macro
   measured, and the arithmetic above gives 6 for R1, R2 and R3 alike.
6. **Records 105, 106, 110, 111, 115, 116, 120, 125, 145, 150, 151 all
   byte-identical.** COV-19, COV-27 and COV-28 each changed record 160 and
   nothing else. p 0.85. Record 120 keeping its 111 entries is the part that
   matters: a macro is not a patch edit and must not touch the defect.

### The rider that costs nothing — record 161

This project has **no macros at all** and its record 161 reads item 0 head
`[127, 0, 0]` (mask 127 = all-ones over seven fixtures, COV-45 a sixth time),
items 1 and 2 heads `[0, 0, 0]`, and all three tails **176**.

COV-21's open 20-bit mask sits in item 1's head. On the corpus it is `0x0FFFFF`
only on the twenty-fixture rigs and 0 everywhere else — including here, on a
project whose single preset has `LIVE EDIT` **ON**, which already refutes
"item 1 is the LIVE EDIT enable" from the corpus alone. What it has never been
tested against is a project **acquiring its first Live Edit button**.

7. Item 1's head stays `[0, 0, 0]`. p 0.6.
8. Rival, and it is the interesting one: it becomes **`[1, 0, 0]`** — bit 0 for
   the one defined button — which would make it a **Live Edit button mask over
   a page of 20** and would answer half of Q8. p 0.25.
9. The three tails stay **176**, and `125.f4_tail` stays **184** on all nine
   slots. p 0.8. If either moves on a save that only created a macro, COV-22's
   refuted coupling gets a third data point for free.

## Stage 2 — the reorder that splits R2 from R3

Only if stage 1 returns R2 or R3, which are degenerate here for a second
reason: 115 index and display position are equal under the identity order.

**On the panel:** reorder the fixtures so the fixture now at display position 4
moves — COV-47 did exactly this and it wrote **records 105 and 115 only**,
leaving 106, 110, 111, 116, 120, 150, 151 and 161 byte-identical. Save.

| outcome | record 160 | reading |
|---|---|---|
| **A** | **byte-identical** | the slot does not follow the display position: R1 or R3 — or R2 with the macro left **stale**, which is what the failing corpus macros look like |
| **B** | `f7` renumbered to the new display position | **R2 confirmed**, and the firmware rewrites macros on a reorder |
| **C** | 160 rewritten some other way | both refuted, and the sheet says so |

Outcome A does not close on the file alone and the discriminator is at the
panel, not in the bytes: **fire the macro and watch which head moves.** If it is
the head at DMX 81 → the slot is an address (R1). If it is whichever head now
sits at display position 4 → the slot is a display position and the file was
stale. That would also be the first direct evidence for the stale-macro reading
COV-56 offered for its own failures, and it would explain them without a new
mechanism — the accumulation COV-26 measured on record 125, in another record.

## What each outcome is worth

R1 or R2 confirmed and stable under stage 2 → `160.f7` gets a name and **0.47 %**
leaves `partial`, which would put the corpus at 93.8 % read and 0.2 % partial.
R3 → the same, and `slot_id` gains its first consumer, which is the thing
COV-54 could not say about it. R4 → COV-56's container reading is what falls,
and that is worth knowing too.

## Refusals

No `PAN OFFSET` / `TILT OFFSET` encoder is touched (COV-39 crashes the unit).
Nothing is written to the device by this repository: every change is made on
the panel and every capture is a download. WTOOLS stays closed.
