# Experiment log — 2026-08-26

Index only. Every result is written up in full, with its predictions and its
retractions, in `research/wpj-format-registry.md`.

W1 Mk1, firmware 2.0.18, DMX outputs physically disconnected, WTOOLS closed
throughout. Experiment project `WMX EXP format-lab`
(`73d06df4-9b5d-5cd1-9645-51ba125f71a5`), version 1787670974700 at the start.

## Corpus only, no hardware

| | Result |
|---|---|
| **record 105** | `f4` is the running offset into record 106 and `f7` is that slice's length — **not** a DMX start address and **not** a channel count. The DMX address is `115.f2`. Three identities added to `tools/wpj_identities.py`, 27/27. |
| **`f32`–`f35`** | per-group arrays added at schema 10; the one project upgraded from schema 8 carries zeros where projects authored at 10 carry `50 / 0 / 100 / 100`. Not the rig-c blackout — the healthy revision has the same zeros. |
| **`f31`** | 20 bytes = 160 bits = **eight 20-bit pad masks**, one per group A–H. Retracts an earlier "four repetitions of two masks", which sliced the same bits wrongly. |

## F29-01 — the static gobo index

Three read-only DMX envelopes, nothing written, nothing saved. Baseline 0 on the
six gobo channels; `Get Moving` (`f29[A]` = 9) drove all six to **70**;
`Sizzle` (`f29[A]` = 2) drove them to **21**; `Startup` (`[255]×8`) put them
back to **0**. All three were the published 0-based prediction; the 1-based
alternative predicted 63 and 14. Closing envelope 2048/2048 against baseline.

## F30-01…04 — the static-colour `PATTERN`

| | |
|---|---|
| **F30-01** | five values measured from factory presets (9, 0, 1, 2, 5); the eleven-entry icon list read off the encoder; alignment `value = (screen position − 3) mod 11`. Retracts "one scalar replicated eight times" — the screen shows three groups on different values at once. |
| **F30-02** | the whole list walked live on group B, eight captures, each predicted in writing first. Seven exact; element 7 corrected the share rule. `FLASH` turns out to make the group's pads **momentary**, not a spatial layout. Group membership read off DMX: six lyres in A, ten pars in B. |
| **F30-03** | the distribution rule, at three colours, in both geometries: 10 over 3 straight = **4-3-3**, half-length 5 over 3 = **2-2-1**. |
| **F30-04** | one save, three groups on three patterns with three colour selections. Read back `f30 = [4, 3, 8, 0…]` and masks `5 / 13 / 9 / 24×5` — **every value exact**, and the first non-uniform `f30` ever observed. Snapshots in `corpus/experiments/F30-04/`. |

## Device behaviours worth remembering

- **Creating a preset does not save the project.** The screen showed `Preset 83`
  while two downloads still returned 82 presets and an unchanged version. Only
  the separate project save moved the file. Check the version counter at
  offsets 40–47 before concluding anything.
- **Preset pads do not toggle off**, unlike the gobo palette pads.
- The `GROUPS` key does **not** show group membership; it pages the display to
  groups E–H.
- The `PRESET EDIT` screen exposes the content mask as six toggles — `COLOR`,
  `MOVE`, `BEAM`, `GOBO`, `LIVE EDIT`, `OTHER` — plus `FADE` and `HOLD`.

## State left behind

The rig was returned to the opening baseline, **2048/2048 channels**, three
times over the session. The experiment project gained one preset, id 82, and is
now at version 1787670974701. It was already off its original state before
today; `corpus/experiments/FX-01/before.wpj` remains the reference for a
restore.
