# COV-38 — the author fingerprint of a save (BEFORE measuring)

COV-37 attributed the `150` slice regression to a save, and could not say
**which writer** made it. The version counter increments the same way for both,
and nothing this repository reads carries an author. COV-02 found one split —
WTOOLS writes `165.f27` = 1000 where the panel writes 0 — on a save that
*changed* something; nobody has asked what each writer touches on a save that
changes **nothing**.

That is the whole experiment: two no-op saves, one per author, and a diff.

## Do

**0 — the baseline.** Download the project first. The last capture is
`COV-32/before.wpj` and `projectChanged` was `false`, but the controller has
since been reloaded and **crashed**, so the baseline is re-read rather than
assumed.

```
wolfmix.py project <uuid> corpus/experiments/COV-38/base.wpj
```

**1 — the panel.** Save from the controller, **changing nothing first**.
Download as `after-panel.wpj`.

**2 — WTOOLS.** Close nothing on the device; open WTOOLS 2.0.2, save,
**changing nothing first**. Download as `after-wtools.wpj`.

Order matters only in that each download must follow its own save. Nothing is
edited at any point: the variable is the writer, and that is the only one.

## What is already known about a no-op save

- §10: a controller-side save is **not byte-preserving**.
- COV-13: one such save gave every fixture row `115.f6 = 2`, absent before, and
  converted seven empty gobo palettes from one empty form to the other.
- COV-32: a save nobody meant as an edit rewrote `115.f6`/`f7` on all 20 rows,
  trimmed record 120 to the patch while leaving `120.f1` behind, reverted
  `150`'s slice table, and moved record 161's shared tail.
- Trap 3: a save can increment the version counter and change nothing at all.
  That outcome is live and is P6 below.

## Predictions

| # | Prediction | p |
|---|---|---|
| P1 | the panel save rewrites `115.f6` and `115.f7` — **uniform across all 20 rows**, as they are in every corpus file that carries them | 0.6 |
| P2 | it moves record **161**'s shared tail, the three values at index 187 that COV-21 and COV-32 both watched move on a save | 0.5 |
| P3 | **the two saves touch different sets of record types.** That set is the fingerprint, and it is the deliverable whichever way it falls | 0.55 |
| P4 | one of the two **rewrites `150`'s slice table** — either back to a consistent `A1:0+1`, which would make the firmware recompute it from its live state, or to something else again | 0.45 |
| P5 | each save writes a **new** `f6`/`f7` pair, and the two saves differ. Read as one 16-bit value in both byte orders, that is a save marker — a counter or a clock — and two points minutes apart would show which | 0.4 |
| P6 | rival, and it is real: **neither save changes a single record**, the version counter alone moves. Then a no-op save is genuinely inert on this firmware, the `150` regression needed an edit to happen, and COV-37's culprit is still unnamed | 0.25 |
| P7 | rival: the two saves are **indistinguishable** — same record types, same kind of change. Then there is no fingerprint to read and version `…327` cannot be attributed by this route at all | 0.2 |

## Collision check

The observable is the **set of record types that changed**, per save. P3, P6 and
P7 partition it exactly: different sets, empty sets, identical sets — no diff
can satisfy two of them. P1, P2 and P4 are statements about *which* records are
in that set and are read from the same diff without competing with each other.

P5 is the only numeric one: `f6`/`f7` are one value per file across every
corpus file that carries them, spanning 231/20, 232/113, 44/41, 110/218,
81/183, 94/187, 79/99, 57/6.

> **Corrected 2026-09-01, before this sheet was run.** It said "no two projects
> share a pair". They do: **231/20** is carried by two unrelated projects on 4
> fixtures and on 20, and 44/41 by two more (COV-46). So a repeat between the
> two saves is **not** the surprise this sheet claimed, and P5 cannot be read
> as "the pair identifies the writer". What it can still say is whether each
> save writes the pair at all, which is the part COV-42 and COV-46 made
> interesting.

## The hazard, and it is new

**Turning the `PAN OFFSET` / `TILT OFFSET` encoders crashes this controller**
(COV-39). Nothing in this sheet goes near that screen, and nothing here should
be run with those encoders in reach of a stray hand. A crash during a save is
how a project gets truncated, and this project has already lost five detached
fixtures to one editing session.
