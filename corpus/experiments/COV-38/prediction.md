# COV-38 — the author fingerprint of a save (BEFORE measuring)

COV-37 attributed the `150` slice regression to a save and could not say **which
writer** made it. The version counter increments the same way for both, and
nothing this repository reads carries an author. COV-02 found one split —
WTOOLS writes `165.f27` = 1000 where the panel writes 0 — on a save that
*changed* something; nobody has asked what each writer touches on a save that
changes **nothing**.

That is the whole experiment: two no-op saves, one per author, and a diff.

> **Revised 2026-09-01, second attempt.** The first attempt's two files,
> `base.wpj` and `after-panel.wpj`, are **byte-identical, version counter
> included**. Two readings fit and the files cannot separate them: the panel
> save never happened, or it happened and wrote nothing. **A filename is not a
> measurement.** Step 1 is therefore *not established as run*, the pair is kept
> as the record of that ambiguity, and the method below fixes the hole — the
> version is read **off the device** before and after each save, so "a save
> happened" is measured rather than asserted.

## Why now, and not later

The restore of this project (option A, redeploying `COV-19/after-live-edit-200.wpj`)
**destroys the only live instance of the corrupted state**. This sheet is the
only planned experiment that needs that state. It runs first or it does not run.

## The state it starts from

`COV-38/base.wpj`, version **1788199970327**, 15907 bytes,
sha256 `6220d8ce0b8bdf8b…`. Anomalies: `_anomalie_comptes`,
`_anomalie_tranches`, `_anomalie_151_groupe`.

| | value |
|---|---|
| `115.f6`/`f7` | **(231, 20)** on all 20 rows |
| `120.f1` | **221** against **215** entries, and the patch justifies 215 |
| `120.occupancy` | 215 occupied, **exactly the patch** — nothing spare, nothing missing |
| `150` / `151` | 150 claims **6** slices, 151 holds **1** entry |
| `161` heads | item 0 `[0, 24, 0]`, item 1 `[255, 255, 15]`, item 2 `[0, 0, 0]` |
| `161` tails | **240** on all three, index 187 |
| `125.f4_tail` | **56** on all nine slots — the one-byte form (COV-51) |
| `116.f12` | carried by **2** profiles of 5, the COV-30 mis-slicing |
| `165` | 6 presets, `f1` = 6, **`f27` = `[0] × 8` on all six** |
| `145` | group A 252 bytes, the other seven at **42** — already the wholly-empty form |

## Do

**WTOOLS must be closed before every command** — the serial port is exclusive.

**0 — the baseline, and the oracle.** `projects` returns the version *and the
size* without downloading, which is what makes "a save happened" measurable.

```
python3 tools/wolfmix.py projects
python3 tools/wolfmix.py project <experiment-project-uuid> corpus/experiments/COV-38/v2-base.wpj
```

**1 — the panel.** Save from the controller, **changing nothing first**. Then,
before downloading:

```
python3 tools/wolfmix.py projects        # version and size: did anything happen?
python3 tools/wolfmix.py project <experiment-project-uuid> corpus/experiments/COV-38/v2-panel.wpj
```

**2 — WTOOLS.** Open WTOOLS 2.0.2, save, **changing nothing first**, then
**quit WTOOLS** before the next command.

```
python3 tools/wolfmix.py projects
python3 tools/wolfmix.py project <experiment-project-uuid> corpus/experiments/COV-38/v2-wtools.wpj
```

Nothing is edited at any point. The variable is the writer, and it is the only
one. If step 1's version does not move, **say so and stop reading the download
as a save** — that is trap 3's negative oracle doing its job, and it is exactly
what the first attempt could not establish.

## Predictions — the panel half

| # | Prediction | p |
|---|---|---|
| **P1** | the panel save **writes something**: the version moves and at least one record differs | 0.55 |
| P2 | it rewrites `115.f6`/`f7` — to a different pair, or deletes them | 0.60 |
| P3 | `161`'s shared tail moves off **240**, to 176 or 160 | 0.40 |
| P4 | `120.f1` is **repaired to 215** — the content was corrected at `…327` and the counter left behind, and a later save is the only thing that could catch it up | 0.30 |
| P5 | `150`'s slice table is rewritten to something consistent with 151's single entry (`A1:0+1`) | 0.30 |
| **P6** | rival, and it is real: **neither save changes a single record**. Then a no-op save is inert on this firmware, the `150` regression needed an edit, and COV-37's culprit stays unnamed | 0.30 |
| P7 | rival: the two saves are **indistinguishable** — same record types, same kind of change. Then there is no fingerprint and `…327` cannot be attributed by this route | 0.20 |

## Predictions — the WTOOLS half, and this is the sharp one

COV-02 measured the author split on `165.f27`: every preset of a project WTOOLS
2.0.2 produced carries **1000** on all eight groups; every preset composed at
the panel carries eight explicit zeros. What it never asked is **at which
moment** WTOOLS writes that — at creation, or on every save. This project's six
presets all carry `[0] × 8` right now, so one no-op save answers it.

| # | Prediction | p |
|---|---|---|
| **P8** | after the WTOOLS save, all six presets read `f27` = **`[1000] × 8`** | 0.50 |
| — | rival: `f27` stays `[0] × 8` — WTOOLS **preserves** what it read, and COV-02's split is about creation and not about saving | 0.40 |
| — | rival: something else entirely, including a partial rewrite | 0.10 |
| P9 | if P8 holds, `f32`/`f34`/`f35` take the WTOOLS defaults COV-02 saw written out (`50 / 0 / 100 / 100` on `f32`–`f35`), all currently `[0] × 8` | 0.40 |

**Either answer is worth the trip.** If P8 holds, a single field names the author
of any save, and every WTOOLS-touched capture in the corpus becomes
identifiable retroactively. If it falls, COV-02 is sharpened rather than
weakened — the split is about how a project is *born*, and the ledger currently
says only "the split is by author" without saying when.

## The rider — `115.f6`/`f7`, and it is decisive

COV-58 killed four readings of that pair and left one testable statement:
**if it moves between two saves that change nothing else, it is not project
data.** It is `(231, 20)` on all 20 rows right now.

| # | Prediction | p |
|---|---|---|
| **P10** | across the two saves the pair takes **at least two distinct states** — a new pair, or absence | 0.60 |
| — | it is unchanged through both | 0.40 |

P10 holding closes the question COV-58 opened: a value that changes on a save
which changes nothing is not a property of the fixtures it is written on, and
the codec comment stops being a warning and becomes a reading. P10 failing is
weaker but not nothing — it removes "a save rewrites it unconditionally".

## Free riders — consequences of this session's readings, checked at no cost

| # | Prediction | p |
|---|---|---|
| P11 | `120.occupancy`'s occupied count equals record 120's entry count in **every** capture, whatever the saves do (COV-55) | 0.95 |
| P12 | the 16-bit pairing of `120.f5`/`f6` survives both saves intact — `_anomalie_120_alignement` stays silent (COV-57) | 0.95 |
| P13 | `125.f4_tail` stays **56**. If it moves **in the same save** as `161`'s tail, COV-22's refuted coupling gets its third point and comes back; if it moves alone, the refutation stands | 0.75 |
| P14 | `116.f12` stays on 2 profiles of 5 — neither writer repairs the COV-30 mis-slicing | 0.8 |
| P15 | `145`'s seven empty palettes stay at 42 bytes; the COV-13 conversion is already done and cannot repeat | 0.9 |

## Collision check

The observable is the **set of record types that changed**, per save. P1, P6 and
P7 partition it exactly — non-empty and different, empty, non-empty and
identical — so no diff satisfies two of them. P2 to P5 and P8 to P15 name
*which* records are in that set and are read from the same diffs without
competing. P8 and P10 are on different records (165 and 115) and cannot mask
each other.

## Hazards, and the refusals

**Turning the `PAN OFFSET` / `TILT OFFSET` encoders crashes this controller**
(COV-39). Nothing here goes near that screen, and a crash during a save is how
a project gets truncated — this project has already lost five detached
fixtures to one editing session, and those five are what the restore gives back.

Nothing is written to the device by this repository in this sheet: both saves
are made by their own author, every capture is a download. WTOOLS is closed
before every command and quit after step 2.
