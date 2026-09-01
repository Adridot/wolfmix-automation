# COV-62 — the three FX labels nobody here has measured (BEFORE measuring)

COV-61's worklist puts three names at the top of the `correlated` 25.5 %, and
they are the same shape: `bpm_division` (`f1`, **1.80 %**), `link_order`
(`f4`, **1.77 %**) and `speed_source` (`f10`) carry enum labels
**cross-referenced from `wpj-toolkit`**, an external project, and nothing on
this hardware has ever tested one. The FX6 campaign of 2026-08-30 measured
`f2`, `f6`, `f8`, `f9` and `f3`, and never put these three back on the table —
which is trap 2 exactly, on **4 %** of the corpus. FX6-02 is the reason to take
it seriously: `f2` had carried the name *speed %* since ACC-04 and was the fade.

**Stage 0 writes nothing.** The file already carries a contrast the corpus
sweep cannot use and a screen can.

## The state, and why it is already a discriminator

`COV-49/stage3-groupA.wpj`, version **9**, sha256 `ad388a41d63ca45a…`. One
preset, every FX engine at its default:

| engine | `bpm_division` | `link_order` | `speed_source` |
|---|---|---|---|
| `beam_fx1`, `beam_fx2` | **3** | 10 | absent |
| `color_fx1`, `color_fx2` | **3** | 10 | absent |
| `move_fx1`, `move_fx2` | **2** | 10 | absent |

Move disagrees with beam and colour on `bpm_division`, in the stored file, with
no manipulation at all. Under the published table 3 → **×1** and 2 → **×2**, so
the two screens must show **different** divisions and in that order. A table
that is right for the wrong reason cannot survive that; a table that is off by
one index shows the same pair shifted, and a table that is reversed shows them
swapped.

## Stage 0 — three photographs, no write

**Reload the project on the panel first** (main menu → Open, mode 26 —
PROJECTS-01), because the panel shows the live copy and this compares against
the stored file; GEN-03 is the entry that cost a session for skipping it. Then
photograph the `BEAM FX`, `COLOR FX` and `MOVE FX` screens.

| # | prediction | p | what the rival would mean |
|---|---|---|---|
| **1** | `BEAM FX` shows BPM division **×1** | 0.60 | any other value: the index base or the direction of the table is wrong |
| **2** | `MOVE FX` shows **×2**, and it **differs from beam's** | 0.60 | if the two screens agree, `f1` is not what is displayed there at all |
| 3 | Link order reads **Group / Fwd** on all three screens | 0.70 | `10` is documented as the default and as `Group/Fwd`; a bare `Fwd` would put the tens digit somewhere else |
| 4 | Speed source reads **Clock** | 0.85 | absent = 0 = Clock; anything else and absence is not zero here |
| 5 | the version counter does **not** move | 0.95 | a read-only stage that writes is a stage that has to be redone |

Predictions 1 and 2 are one measurement, not two: it is the **pair** that tests
the table, because a single screen agreeing with a single stored value is one
point and this repository has been wrong on one point before.

### The rider — `165.positions`, 1.66 % and never measured either

The preset stores `positions = [1] × 8`, and record 150's slots are named
`Floor`, `Center`, `Center Point`, `Crowd`, `Ceiling` at display slots 1–5.

| # | prediction | p |
|---|---|---|
| **6** | recall the preset, and group A's POSITION screen lights **`Center`** — `f28` is **0-based**, like the gobo index (F29-01) | 0.65 |
| — | rival: it lights **`Floor`**, and `f28` is 1-based | 0.35 |

One recall, no save. Whichever way it falls, `165.positions` stops being a name
inherited from its neighbour `f27` and becomes a reading — and if it is
`Floor`, then two per-group index fields in the same record disagree on their
base, which is worth knowing before a writer emits one.

## Stage 1 — the write direction, and only if stage 0 held

Not a capture. A capture rewrites the whole preset — EXP-07 watched one rewrite
seventeen fields at once — and the point here is one field at a time. Instead,
the file is edited outside the device and deployed under a **derived UUID**
(`wolfmix_experiment.py`), then reopened on the panel and photographed, which is
the direction FLASH-08 and FLASH-10 used to confirm the flash slices both ways.

Three values, mutually distinct and absent from this file:

| field | write | the table says it should read |
|---|---|---|
| `beam_fx1.bpm_division` | **6** | **⅛** |
| `beam_fx1.link_order` | **22** | **Fixture / Out** |
| `beam_fx1.speed_source` | **1** | **Microphone** |

| # | prediction | p |
|---|---|---|
| 7 | all three read back on the `BEAM FX` screen as the table says | 0.55 |
| 8 | `move_fx1` is untouched and still reads **×2** — the engines are independent | 0.85 |
| 9 | the project reopens (a 19-byte name limit is the only loader refusal known, PRESET-05) | 0.9 |

Three fields in one deploy is deliberate and is **not** the one-variable rule
being broken: the rule governs a *save whose diff must be attributed*, and here
the file is written by us, so every byte is already attributed before it leaves.
What the device supplies is only the read-back.

## What it is worth

Stage 0 alone, if it holds, takes `bpm_division`, `link_order` and
`speed_source` from `correlated` — on an external project's say-so — to
**device-confirmed**, read off this controller. That is **4 %** of the corpus
moving up one rung for three photographs and no write, which is the best ratio
anywhere on the worklist. Stage 1 adds the write direction. Prediction 6 adds
another 1.66 % for one recall.

## Ordering, if COV-60 runs in the same session

COV-60 stage 1 creates the project's first macro and carries a rider on record
161. Run **COV-62 stage 0 first**: it writes nothing, so it cannot disturb
anything, and doing it after a macro exists would leave the 161 rider arguing
with a screen visit. Everything else is one change per save.

## Refusals

No `PAN OFFSET` / `TILT OFFSET` encoder (COV-39 crashes the unit). Stage 1
deploys only under a derived UUID, never onto the operator's own projects.
WTOOLS stays closed.
