# COV-49 — a session, not an operation (BEFORE measuring)

Five device saves on the fresh project came back at 0 anomalies: create,
detach with an offset, add a fixture, delete a fixture, reorder. **No single
patch operation reproduces the damage.** Two things are left, and this sheet is
the second — the first is COV-38, still unrun.

## Why those five proved less than they look

COV-48's anomaly is *a detached entry naming a fixture of another group*. The
clean project has **one** group: every fixture is in A. **The anomaly is
unexpressible there.** Five clean saves could not have found it whatever the
writer did, and saying that out loud is the point of writing this before
measuring rather than after.

The format-lab has four groups. Its damaged entry names a fixture of group 1 on
a slice owned by group A.

## The other thing those five did not test

COV-23/24 in its own words: the operator *"moved through the setup screens and
saved once at the end"*. Every rung here saved after **one** change. The
firmware demonstrably remaps `151.f1` across a single deletion (COV-46) — the
untested case is whether it still does across **two index shifts before one
save**.

So: two groups, several operations, one save.

## Stage 0 — make the anomaly expressible

Add a fifth `Lyre ZQ02244` at DMX **81** and put it in **group B**. Save.

```
wolfmix.py project <uuid> corpus/experiments/COV-49/stage0-groupB.wpj
wpj_identities.py corpus/experiments/COV-49/stage0-groupB.wpj
```

| # | Prediction | p |
|---|---|---|
| S0-1 | 115 → 5 rows, the new one with `f4` = **1** (group B) and `f9` **5** | 0.7 |
| S0-2 | record 125's group-B slot gains the profile bit — `profile_mask` **1**, as group A already has | 0.7 |
| S0-3 | 151 untouched: one entry, `fixture` absent = 0, `pan_offset` **45874**; `Floor` still claims 1 | 0.85 |
| S0-4 | **0 anomalies** | 0.8 |

If S0-4 fails, stop and report: putting a fixture in a second group would then
be the trigger on its own, which would be a far simpler answer than a session.

## Stage 1 — the session

**One visit to `FIXTURE SETUP`, no save in between**, then **one** save:

1. **delete** the head at DMX **17** — index 0, *the one carrying the 40 %*;
2. **add** a head at DMX **97**, in **group B**;
3. **reorder** the list, moving the first entry to the end.

Then save once, download, check.

> No offset encoder is touched anywhere in this sheet (COV-39).

## Predictions for stage 1

`151.f1` currently names index **0**, and step 1 deletes exactly that fixture.
Three futures for the entry, and they are what this rung is for:

| # | Outcome | reading | p |
|---|---|---|---|
| **A** | the entry is **dropped**, 151 empty, `Floor` claims **0** | the writer removes an offset with its fixture. Clean, and the damage is elsewhere | 0.35 |
| **B** | the entry survives, `f1` remapped to a **group-A** head | the writer keeps the offset and moves it to another fixture of the same group. Odd but internally consistent — **0 anomalies** | 0.2 |
| **C** | the entry survives naming a **group-B** fixture | **COV-48 reproduced.** The trigger is a multi-operation session, and the report writes itself | 0.25 |
| **D** | the entry survives, `Floor` claims a count 151 cannot serve | **COV-32's slice mismatch reproduced** — the other half of the format-lab's damage | 0.2 |

| # | Prediction | p |
|---|---|---|
| P1 | 115 → 5 rows: the three surviving group-A heads at 32, 48, 64, plus two in group B at 81 and 97 | 0.6 |
| P2 | `115.f9` keeps its values on the survivors — 2, 3, 4, 5 — and the new head takes **6**, not a reused number | 0.5 |
| P3 | record 161's item-0 mask stays **15**: four fixtures before, five after one delete and two adds… so **31**. Stated as 31, and if it reads 15 the mask is not simply all-ones over the count | 0.55 |
| P4 | record 120 → **80** entries with `f1` following | 0.6 |
| P5 | `115.f6`/`f7` take a **fourth** distinct value. Created 177/124, a plain save deleted them, an add left them absent, a delete wrote 231/20, a reorder wrote 3/20 | 0.5 |

## Collision check

A, B, C and D are four mutually exclusive states of one entry — gone, in-group,
out-of-group, or present under a broken count — and no capture satisfies two.
P1–P5 name different records and none of them decides between A–D.

**C and D are the outcomes worth the session.** Both are what the per-file
check now catches; A and B are clean and would mean the trigger is neither an
operation nor a session, which leaves WTOOLS and COV-38 as the last suspect
standing.
