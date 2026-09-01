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

## Do

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

## Predictions

| # | Prediction | p |
|---|---|---|
| 1 | the `FIXTURE` encoder cycles **6** fixtures on this slot, the group's six | 0.9 |
| 2 | **exactly one** of them reads `PAN OFFSET` **39 %**, `TILT OFFSET` **9 %**, `FOCUS OFFSET` **0 %**; the other five read 0 / 0 / 0 | 0.75 |
| 3 | that one is the fixture at **DMX 32**, display rank 2 — so `151.f1` is a rank in **display** order and not an index into record 115, where 2 is a par of another group and could not be here | 0.7 |
| 4 | slots 4 and 5 show **0 / 0 / 0 on all six fixtures** — they claim entries at offsets 5 and 4 of a one-entry record, so there is nothing to show | 0.75 |
| 5 | if 2 and 4 hold: the **counters are stale** and record 151 is right. `tranches_151` fell the same way `comptes_de_tete` did in the same save — a count left behind — and a reader must clamp a slice to the record | 0.7 |
| 6 | rival, and the one that matters: **four** fixtures carry offsets on the first slot, or slots 4/5 show any. Then record **151 was truncated on write**, the counters are right, and a device save can lose detached positions | 0.2 |
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
