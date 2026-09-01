# COV-33 — which side of `150` ↔ `151` is stale (BEFORE measuring)

COV-32 broke `tranches_151`, an identity exact on 90 files: group A's position
slots claim **6** entries of record 151 where the record holds **1**. Record
120's surplus in the same save is decided by arithmetic; this is not. Nothing
in the file says whether the counters over-claim or the record was truncated,
and the difference matters — a truncated 151 means a save can lose an
operator's detached positions.

Three photographs were taken and they **do not settle it**. What they give:

- The `ALL POSITIONS` page prints group A's five named slots in file order,
  and groups B and D empty. Consistent with the file and with COV-12.
- The position page of group A's first slot reads **PAN 53.55 %, TILT 35.11 %,
  FAN | CROSS 50.06 %, FOCUS OFFSET 99.94 %** — COV-11's four values, to two
  decimals, **unchanged by the canonicalisation save**. That is the control:
  the panel holds what the file holds for record 150's content.
- A screen this repository had never photographed: under a position slot, a
  per-fixture page with `PAN OFFSET`, `TILT OFFSET`, `FOCUS OFFSET` and a
  `FIXTURE | ON` encoder. That is the record-151 editor. On the fixture it
  happened to be showing, `Lyre Z 1`, all three read **0 %**.

`Lyre Z 1` is not the fixture the file stores, so 0 % is what the file predicts
there. The measurement is **one encoder turn**.

## Do — on the DMX, not on the screen

Superseded by a better instrument. The encoder turn below still works, but the
output itself answers the question without anyone reading a pixel: a fixture
carrying an offset lands on a different **tilt** channel value than its
neighbours, and the position model is device-confirmed on tilt **12 of 12**
(POS-01/02, `tools/wpj_position.py`).

Group A is six `Lyre ZQ02244`. **Rank 0 carries no `dmx_address` field, which this sheet read as unpatched. It is wrong: absent means address 0** (COV-41), and that fixture emits on channels 0-3 like any other.
Rank 1 carries travel limits `0/77` on tilt and `151/204` on pan. **Ranks 2-5
carry no travel limits at all** — neither `106.f5` nor `106.f6`, on either axis.

**What an absent limit means was predicted wrong here, and a photograph refuted
it before the measurement.** This sheet read absent as the full range and
predicted 84 on the control pad. The `FIXTURE LIMITS` screen reads **MIN PAN
0 %, MAX PAN 0 %, MIN TILT 0 %, MAX TILT 0 %** — absent in the file is **0** on
the screen, all four of them, and the head is **pinned at 0 / 0**. The
identification did not rest on which pad was selected — the only fixtures in
this file whose four limit fields are all absent are ranks 2-5 — and the
operator then named it: the panel's **DMX 33**, the file's address **32** at
base 0, **display rank 2**. That is the very rank the file's stored entry
points at, so **the one fixture carrying an offset is a pinned one**.

That is a device-confirmed reading, and it **guts the capture as designed**:
ranks 2-5 emit 0 on pan and tilt whatever position is recalled and whatever
offset they carry. Four of the group's six moving heads cannot move. The one
observable fixture is **rank 1**, and the file's stored entry is `fixture = 2`
— under the display-rank reading, a pinned one. So the DMX cannot see the
offset that matters, and the encoder turn is back to being the measurement.

What the capture is still worth: a **control**, on one pad, confirming on the
wire what the screen says in percent.

**One** window of 15 s on pad 1, **no FX running** so that `animatedChannels`
comes back 0 and `min == max` on every channel. The four pads below were the
plan when the capture was still the measurement; they are kept because the
pinned channels are the control and pad 1 carries it:

| pad | what the file claims | why it is in the list |
|---|---|---|
| **2** `Center` | nothing | the **control** — what "no detached fixture" looks like |
| **1** (operator-named) | 4 entries at 151 offset 0 | the question |
| **4** `Crowd` | 1 entry at 151 offset **5** | offset 5 of a one-entry record |
| **5** `Ceiling` | 1 entry at 151 offset **4** | offset 4 of a one-entry record |

### The predicted tilt bytes

Channels are 0-based and absolute, as `106.f2` gives them. The high byte of the
16-bit pair is what the table holds.

| pad | TILT | ch 17 (limits 0/77) | ch 33, 49, 65, 81 — **pinned, 0 whatever happens** |
|---|---|---|---|
| 2 `Center` | 33.00 % | **25** | **0** |
| 1 (operator-named) | 35.11 % | **27** | **0** |
| 4 `Crowd` | 70.00 % | **54** | **0** |
| 5 `Ceiling` | 100.00 % | **77** | **0** |

**Pan is a deviation test only, never a value test.** The frozen model ignores
the slot's own `PAN` for the pan axis and scores 11/12, a known hole — but the
stored offset is `+39 %`, which on a fixture with no travel limits moves the
coarse byte by about **99 counts** whatever the baseline is. Channels 16, 32,
48, 64, 80.

## The old plan, kept

On group A's **first** slot (the operator-named one), turn the `FIXTURE`
encoder through every fixture of the group and photograph each. Then the same
on slots **4** (`Crowd`) and **5** (`Ceiling`).

**Turn the `FIXTURE` encoder only.** `PAN OFFSET` / `TILT OFFSET` /
`FOCUS OFFSET` are setters, not selectors — COV-11 moved four values by turning
one. **Do not save.** This measurement writes nothing; if a save happens the
reference is gone and COV-32's capture stops being a before.

## The file, decoded

Group A is the six `Lyre ZQ02244`, display ranks 0–5. Rank 0 carries **no DMX
address**; ranks 1–5 are at DMX **16, 32, 48, 64, 80**.

| slot | claims | at 151 offset | record 151 actually holds |
|---|---|---|---|
| 1 (operator-named) | 4 entries | 0 | 1 entry: `fixture = 2`, **PAN 39.00 %, TILT 9.00 %, FOCUS 0 %** |
| 4 `Crowd` | 1 entry | 5 | nothing — the record ends at 1 |
| 5 `Ceiling` | 1 entry | 4 | nothing — the record ends at 1 |

## What the vendor manual says, and what the photograph then shows

The manual's `Fixture Offset Mode` page lists, among the displayed data, the
offset of the **currently selected** fixture, shown as a *white dot*. That is
the marker at the centre of the green target in the photograph — white, because
the selected fixture is at 0 / 0 / 0 and sits on the group position. The
`Position Picker` page one section earlier lists no such dot, and the
photograph of that page has none. So the manual accounts for **one** marker.

The photograph carries **three**. Isolating the UI green on the raw pixels and
clustering it gives, inside the grid and away from the text: the target at
(1370, 654) and two small round markers of 25 × 25 and 22 × 23 pixels, at
(2041, 623) and (430, 854). Nothing else above noise.

Calibrating on the two axis lines — the local dips at x = 1313 and y = 549 —
against the group's own device-confirmed `PAN 53.55 %` / `TILT 35.11 %` places
them roughly at **(+42 %, +5 %)** and **(−58 %, −28 %)** of offset. **Treat the
magnitudes as indicative and the signs as solid**: the photograph is taken at
an angle, a linear map strains on it, and the second marker's absolute pan
comes out below 0, which cannot be. What survives the angle is the **quadrant**
and the **count**.

The first marker is in the `(+pan, +tilt)` quadrant with pan far larger than
tilt — the signature of the file's only stored entry, `+39 % / +9 %`. **The
second is deep in `(−pan, −tilt)`, and the file holds no entry with a negative
offset at all.**

Naming the small markers "the other fixtures' offsets" is an **inference**: the
manual documents the white dot and not these. The rival is that they are drawn
for some other reason, and one encoder turn separates the two.

## Predictions

| # | Prediction | p |
|---|---|---|
| ~~D1~~ | **Refuted before the measurement, by a photograph.** This read an absent travel limit as the full range and predicted 84. The `FIXTURE LIMITS` screen reads 0 % on all four limits: absent is **0**, and the head is pinned. What replaces it is D0 | — |
| D0 | on the wire, ch 33, 49, 65 and 81 all read **0**, on every pad — the pinned heads confirmed where the screen only said it in percent. Ch 17 reads **27** on pad 1 | 0.85 |
| D2 | **the encoder turn**, on pad 1: exactly **one** of the six fixtures reads a non-zero offset | 0.45 |
| D3 | it is display rank **2**, the fixture at DMX 32, reading `PAN +39 %` and `TILT +9 %`. That makes `151.f1` a rank in **display** order and not an index into record 115, where 2 is a par of another group | 0.5 |
| D4 | **a second fixture reads a clearly negative offset on both axes** — the marker the screen showed and the file has no entry for. If it does, record 151 was **truncated on write** and a device save can lose an operator's detached positions | 0.5 |
| D5 | pads 4 and 5 show **no** stored offset on any fixture: their claimed entries at 151 offsets 5 and 4 are stale counters over a record that ends at 1 | 0.7 |
| D6 | rival: every fixture reads 0 on every pad. Then the stored entry is not applied either, the screen markers mean something else, and both readings of `tranches_151` are wrong | 0.15 |

### Collision check

The encoder reads a **percentage per axis**, and the three outcomes are far
apart: `0 %` (no stored offset), `+39 % / +9 %` (the file's entry) and a
clearly negative pair. Nothing else on that page can be confused with them —
`FOCUS OFFSET` is a third number on its own encoder and the file puts it at
0 % for the stored entry. D2 and D4 are separated by **how many** fixtures
carry an offset, D3 by **which one**, D5 by two pads that must be empty, and D6
by all of them reading zero. No observation satisfies two rows.

D0 is on a different instrument from D2-D6 and cannot corroborate them: it says
the pinned heads are pinned, which is why the wire cannot answer the question
and the encoder has to.

## Predictions on the screen, from the earlier plan

| # | Prediction | p |
|---|---|---|
| 1 | the `FIXTURE` encoder cycles **6** fixtures on this slot, the group's six | 0.9 |
| 2 | **exactly one** of them reads `PAN OFFSET` **39 %**, `TILT OFFSET` **9 %**, `FOCUS OFFSET` **0 %**; the other five read 0 / 0 / 0 | 0.75 |
| 3 | that one is the fixture at **DMX 32**, display rank 2 — so `151.f1` is a rank in **display** order and not an index into record 115, where 2 is a par of another group and could not be here | 0.7 |
| 4 | slots 4 and 5 show **0 / 0 / 0 on all six fixtures** — they claim entries at offsets 5 and 4 of a one-entry record, so there is nothing to show | 0.75 |
| 5 | if 2 and 4 hold: the **counters are stale** and record 151 is right. `tranches_151` fell the same way `comptes_de_tete` did in the same save — a count left behind — and a reader must clamp a slice to the record | 0.7 |
| 6 | rival, and the one that matters: **four** fixtures carry offsets on the first slot, or slots 4/5 show any. Then record **151 was truncated on write**, the counters are right, and a device save can lose detached positions | 0.2 |
| 6b | sharpened by the photograph: **one** fixture reads clearly **negative** `PAN OFFSET` and `TILT OFFSET`, and it is the entry the file lost — the count of markers already exceeds the count of stored entries, and only the encoder can say by how much | 0.6 |
| 7 | rival: no fixture anywhere reads 39/9 → the stored entry is not reachable from this screen at all, and `151.f1` indexes something neither candidate covers | 0.1 |

## Collision check

The discriminating value is the **pair (39 %, 9 %)**, not the zeros. Nothing
else on these screens is near it: the position page of the same slot reads
53.55 / 35.11 / 50.06 / 99.94, and `FOCUS OFFSET` there is 99.94 % against 0 %
here — the two `FOCUS OFFSET` labels are different quantities on different
pages and the reading must not confuse them. No pair of predictions above lands
on the same observation: 2 and 6 differ by the **count** of fixtures carrying
offsets (one against four), 3 is decided by **which** fixture, and 4 by two
slots that must be empty under prediction 5 and populated under 6.

## What a wrong prediction buys

If 3 fails and the fixture is at DMX 16 or has no address, `151.f1` is neither
the display rank nor the 115 index, and POS-06's name — "fixture index" — is a
field that carries a name rather than a field that was measured. That is trap 2
and it is worth finding.
