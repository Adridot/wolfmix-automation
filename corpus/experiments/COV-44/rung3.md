# COV-44 rung 3 — reordering the fixtures (BEFORE measuring)

Rungs 1 and 4 came back clean: adding a fixture and deleting one both write
correctly, and the firmware even **remaps** `151.f1` when indices slide
(COV-46). So neither caused the format-lab's damage. Reordering is what is
left of "the patch was reorganised", and it is the operation COV-26 already
caught misbehaving — record 116 reordered makes record 125's profile mask
**accumulate** without ever clearing.

**This project cannot test that half.** It has **one** profile, so profile
reordering is impossible and record 125's mask cannot accumulate. What it can
test is the other half, and that half answers a question that has been open
since COV-33.

## Why this rung is worth more than the ladder position suggests

`151.f1` is a fixture index — into **which** list? `display_order` has been the
identity permutation on every capture of this project, so "rank in display
order" and "index into record 115" have been **indistinguishable** throughout.
COV-33's D3 could not separate them and said so. **Reordering breaks the
degeneracy in one move.**

## Do

On the panel, move the fixture at DMX **17** — the one carrying the offset,
currently first in the list — to the **end**. One move, one save, download,
check.

**Pre-check, free:** open the Fixture Offset page on `Floor` and confirm the
`40 %` is on the head at DMX 17. The file says `151.f1` = 0, which after the
deletion is that head. If the screen disagrees, stop — COV-46's remap reading
is wrong and that matters more than this rung.

> Do not touch the `PAN OFFSET` / `TILT OFFSET` encoders (COV-39).

## The state it starts from — `rung4-delete.wpj`, 0 anomalies

| record | value |
|---|---|
| 115 | 4 rows, addresses **16, 32, 48, 64**; `f9` **1, 2, 3, 4**; `f6`/`f7` **231**/**20**; `display_order` **`00010203`** |
| 105 | `offset_106` 0 / 10 / 20 / 30 |
| 106 / 120 | 40 / 64 entries, `f1` following |
| 150 | `Floor` claims 1 entry at offset 0 |
| 151 | one entry, `fixture` **absent = 0**, `pan_offset` **45874** |
| 161 | item 0 mask **15** |

## The four outcomes, and what each one means

| # | `display_order` | record 115 rows | `151.f1` | reading | p |
|---|---|---|---|---|---|
| **A** | `01020300` | unchanged order | **stays 0** | `151.f1` is an **index into record 115**. D3 answered | 0.35 |
| **B** | `01020300` | unchanged order | **becomes 3** | `151.f1` is a **rank in display order**. D3 answered the other way | 0.2 |
| **C** | stays `00010203` | rewritten to 32, 48, 64, 16 | **becomes 3** | the device renumbers the array itself; the two readings coincide again and D3 stays open | 0.25 |
| **D** | anything else | — | leaves the 40 % on a **different head** | **the trigger is found** | 0.2 |

Outcome D is the one this ladder exists for. It is also the only one that
`wpj_identities` would report as **0 anomalies** while being wrong, exactly as
R1 would have been on rung 4 — an index in range, pointing at the wrong head.

## The rest

| # | Prediction | p |
|---|---|---|
| P1 | record **120 is untouched**. It is laid out in ascending **DMX address** order, not the item order of 115 (COV-16), and a display reorder moves no address | 0.7 |
| P2 | `Floor` still claims **1** entry at offset 0, and `pan_offset` is still **45874** | 0.85 |
| P3 | 110, 111 and 116 untouched — one profile, unchanged | 0.85 |
| P4 | `115.f9` keeps **1, 2, 3, 4** attached to their own addresses. A reorder that renumbered it would refute the stable-identifier reading COV-46 just extended | 0.6 |
| P5 | record 161's item-0 mask stays **15**. All-ones is permutation-invariant, so this rung **cannot** discriminate what the mask is ordered by — noted so the result is not over-read | 0.85 |
| P6 | `wpj_identities`: **0 anomalies** | 0.55 |
| P7 | `115.f6`/`f7` change or vanish. A third data point on a third kind of operation: created writes them, a plain save deleted them, an add left them absent, a delete wrote **231/20** | 0.5 |

## Collision check

A, B, C and D are mutually exclusive by construction — they are the four
combinations of two observables (`display_order`, the 115 row order) crossed
with where the offset ends up, and no capture can satisfy two. P1–P7 each name
a different record or field and none of them decides between A–D, which is why
they are listed apart.

**If this rung is clean too**, then no single patch operation on fresh data
reproduces the damage, and the remaining suspects are WTOOLS — which COV-38
would name — or something particular to the format-lab project rather than to
any operation at all. That would be a result worth having, and it is why the
sheet is written before the answer.
