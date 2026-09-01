# Bug report — patching a fixture into a secondary group drops a channel entry

**Product:** Wolfmix W1 MK1 · **Firmware:** 2.0.18 · **WTOOLS:** 2.0.2 beta
**Serial:** *(withheld here — supply it when sending)*
**Date:** 2026-09-01 · **Severity:** silent data corruption in the saved project

## Summary

On a project created on the controller itself, **adding a fixture to any group
other than the first writes one fewer entry into the project's per-channel
table than the patch requires.** The entry that goes missing is at the **head**
of that table, so every entry after it shifts by one and each fixture ends up
holding its neighbour's channel data.

The defect **accumulates** — two such adds drop two entries — and a subsequent
save can restore the entry *count* by appending at the tail while leaving the
shift in place, so the file then looks internally consistent by size while
still being wrong.

Reproduced 2 times out of 2. The same operation into the first group is clean,
2 times out of 2, including on a project that already had a second group.

## A note on naming

This report comes from black-box analysis of the `.wpj` container. **"Record
120" and "field 6" are our labels, not yours.** Record 120 is the table with
one entry per (fixture, profile channel), laid out in ascending DMX address,
that carries the value of channels no engine role drives. If your source names
these differently, the identification is: the record whose entry count equals
the sum over patched fixtures of their profile's channel count.

## Reproduction

Starting from nothing, on the controller only. No PC, no WTOOLS.

1. Create a new project.
2. Patch four fixtures of one 16-channel moving-head profile into **group A**,
   at DMX 17, 33, 49, 65. Save.
3. Add a fifth fixture of the same profile at DMX 81, into **group B**. Save.
4. Read the project back over USB and count the per-channel table.

**Expected:** 5 fixtures × 16 channels = **80** entries.
**Observed:** **79**.

Repeat step 3 with a sixth fixture at DMX 97, also into group B: expected 96,
observed **95**. Add a seventh at DMX 113 into **group A**: expected 112,
observed **111** — that add contributed its full 16, so the deficit did not
grow.

## Measurements

Nine consecutive saves on one project, each a single change:

| change | fixtures after | table entries | required | written |
|---|---|---|---|---|
| create, 4 fixtures in group A | 4 | 64 | 64 | — |
| detach one fixture, set a pan offset | 4 | 64 | 64 | 0 |
| **add a fixture to group A** | 5 | 80 | 80 | **+16** |
| delete a fixture | 4 | 64 | 64 | −16 |
| reorder the fixture list | 4 | 64 | 64 | 0 |
| **add a fixture to group B** | 5 | **79** | 80 | **+15** |
| restore the list order | 5 | 80 | 80 | +1 at the tail |
| **add a fixture to group B** | 6 | **95** | 96 | **+15** |
| **add a fixture to group A** | 7 | **111** | 112 | **+16** |

Only the two group-B adds are short. The arithmetic closes exactly:
`112 required − 2 dropped at the head + 1 appended at the tail = 111`.

## Where the loss happens, and why a size check misses it

Each entry of the table carries a field holding an **absolute DMX channel
number inside its own fixture's span**. Across 101 project files we hold, that
holds for 2671 entries of 2679; the eight exceptions are the two captures
above.

Reading that field against the lowest patched address shows the table starting
**one** entry late after the first group-B add and **two** after the second,
while the group-A add moved it by none. The loss is at the head, not at the
boundary of the group being added to.

The save at step 7 above — an unrelated list reorder — brought the entry count
back to the required 80 by **appending one entry at the end**. The count field
then agreed with the entry total and the table was still shifted. Any check
based on the count alone passes on that file.

## Consequence

The table holds the values for channels no engine role drives. Shifted by one,
each fixture emits its neighbour's channel values on those channels — for a
moving head that is typically the shutter, colour-wheel, gobo or macro
channels. The project stays loadable and shows nothing wrong on the panel.

## Scope of what was tested

- One unit, firmware 2.0.18. One 16-channel moving-head profile.
- Groups **A** and **B** only. Whether groups C–H behave like B is **untested**.
- Adds at ascending, non-overlapping DMX addresses only.
- Every save above was made on the controller. WTOOLS was closed throughout.
- **No claim is made about the cause.** The pattern is what was measured.

## Other observations, not characterised

Listed because they may be related, and labelled as unverified.

1. **Turning the `PAN OFFSET` / `TILT OFFSET` encoders on the Fixture Offset
   page has crashed the unit.** Not reproduced under controlled conditions; no
   detail on the failure mode was captured.
2. On a different project, an editing session through the fixture setup screens
   left a detached-fixture entry **naming a fixture of another group** than the
   position slot that owns it. The panel then shows no detached fixture at all,
   including the one entry the file does hold.
3. On that same project, a later save rewrote a record's slice table back to a
   state from **five versions earlier**, before an intervening editing session.

Happy to supply the project files, byte-level diffs, or SHA-256 of any state on
request.
