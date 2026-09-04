# `intent.json` — the show generator

Reader: Show authors. Question: How do I describe moods for the generator?

The input of `tools/wpj_generate.py compose`. Where
[`show.json`](show-format.md) names fields, this names **intentions**: a list
of moods with an energy, a colour and the groups they light. The generator
reads the rig out of the donor, turns each mood into one preset, and hands
the result to the same compiler.

```bash
python3 tools/wpj_generate.py rig donor.wpj                  # what the donor holds
python3 tools/wpj_generate.py compose intent.json out.wpj --spec spec.json
```

Start with `rig` — it prints the groups that actually have fixtures, the named
positions each group knows, and which template presets the donor can supply.
Everything the intention may refer to comes from that listing.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `base` | string | **required** — donor variant-A `.wpj` |
| `name` | string | project name (record 101) |
| `page` | int 1–10 | preset page to fill; default = the first page above the donor's highest id |
| `moods` | array | one cue each, filled into slots 1, 2, 3 … of that page |

Ids follow the panel formula `id = (page − 1)·20 + (slot − 1)`, so more than
twenty moods simply spill onto the next page.

## `moods[]`

| Key | Type | Meaning |
|---|---|---|
| `name` | string | cue name, **truncated to 19 UTF-8 bytes** on a character boundary |
| `energy` | int 0–100 | how much the cue does — see the ladder below |
| `color` | `"#rrggbb"` | the static colour asked for |
| `groups` | array of `"A"`…`"H"` | which groups light; default = every group that has a fixture |
| `position` | string | a named position from record 150, e.g. `"Crowd"` |
| `dimmer` | int 0–255 | override the ladder's dimmer level; energy says how busy the cue is, this says how bright |
| `live_edit` | bool | `false` locks the cue against panel edits. Default: inherit the template's. **Set it `false` for any cue you intend to measure** — with LIVE EDIT on, a gesture at the panel rewrites the cue's *live copy* while the file stays exactly as deployed, and a recall then measures something else (GEN-03). |
| `template` | int | force a template preset id instead of the one the ladder picks |

## The energy ladder

Energy selects a **family**, which is a template preset in the donor, plus a
dimmer level and an FX speed. The values are settings, not measurements — the
table lives at the top of `wpj_generate.py` and is meant to be retuned on the
rig.

| `energy` | family | dimmer* | beam FX | speed |
|---|---|---|---|---|
| 0–24 | `static` | 120 | — | — |
| 25–49 | `beam` | 180 | Sparkle | 45 % |
| 50–74 | `move` | 225 | — | 70 % |
| 75–100 | `move+beam` | 255 | Chaser | 95 % |

> [!WARNING]
> Before FX6-02 the two upper rungs read 110 % and 170 %, and the speed key
> wrote codec field `f2`. `f2` is the **fade**: those shows were lengthening the
> fade — into the `Flick` range — instead of speeding the effect up. The key now
> writes `f9`, the real speed, and the rungs are back inside 0–100. Regenerate
> any show built before 2026-08-30.

\* **The dimmer only acts if the controller says so.** The Settings menu carries
`store group dimmers in preset`; with it **off**, a cue's dimmers do nothing at
all and the show still looks compiled and correct (GEN-01/GEN-02). Some
operators keep it off on purpose — it locks the rig's levels for a whole
evening. A generated show is therefore **not self-contained on this point**:
check the setting before blaming the file.

With it on, the value is a **percentage**, not a DMX level: the output is
`f5 + (dimmer/255)·(f6 − f5)` using that channel's travel limits, so a fixture
with a floor never reaches 0. On a fixture that has colour channels the
intensity is folded into the colour instead, and the dimmer channel stays at
full.

A family is a state of the first three `165.f16` engine slices — colour,
movement, beam. All four have the **colour engine off**, which is what makes
the requested colour visible instead of overwritten by a Color FX. If the donor
carries no preset for the family the ladder asked for, the generator falls back
to the most active one it does carry.

## Where the colour comes from

The generator writes no palette. Each group has its own 20-pad palette
(record 140), and the generator picks the pad **nearest** to the requested RGB,
then sets that group's bit in `165.f31` and its `165.f30` pattern to `SINGLE`.
So the colour you get is the closest one the rig was already set up with —
check the pad column the compose report prints.

That is a **choice, not a limit**: writing a palette pad is device-confirmed
since PAL-01 (2026-08-27) — the value written is the value rendered, to the
channel. Measured on one component (`red`) of one pad of one group, on a
profile that has colour channels; the other components (`green`, `blue`,
`white`, `amber`, `lime`, `uv`) and colourless profiles are untested.

It stays unwired because every distinct colour costs one of the group's twenty
pads, and those are the pads the operator plays by hand. Burning one is an
operational decision, not a compiler default. If you want an exact colour, edit
record 140 deliberately and say which pad you are spending.

## The trap this exists to avoid

Check `store group dimmers in preset` in the controller's Settings menu before
using generated dimmers. The generator writes the content mask with `COLOR`
and `OTHER` on, `MOVE`/`BEAM` per family, `GOBO` off and `LIVE EDIT` per its
input key; it clones a donor whose engine masks already fit.

The measured behavior belongs in the [content-mask reference](../SPEC.md#content-mask)
and [engine-mask reference](../SPEC.md#engine-masks). Cloning does not establish
that every inherited mask describes the new cue: the addressed-group slice was
rewritten on a device save (GEN-03, validated), and the
[second-engine experiment](../SPEC.md#second-engine) records the later rival
reading and its refutation. Keep that limit in mind when choosing a template.

## What it will not compose

No fixture, no group, no profile — the patch comes from the donor untouched.
Nothing has been measured about writing one, and a synthesised patch would have
no evidence behind it. To generate for a different rig, use a donor patched for
that rig.

## Then deploy, then pilot

The generator stops at the file. The rest is the frontier, unchanged:

```bash
python3 tools/wolfmix_experiment.py deploy out.wpj --label format-lab --case gen-01
```

then **one manual open** on the panel (Main Menu → Projects), which is
irreducible today — no event in the protocol replaces the live copy
(RELOAD-04) — and then, remotely:

```bash
python3 tools/wolfmix.py mode 1
python3 tools/wolfmix.py preset 80
```

`mode 1` first: it is the escape from any modal screen (`1`, `3`, `8` and `33`
release a trapped panel; `0`, `5` and `16` do not — SCREEN-02), and on a modal
screen the recalls are inert: with the Projects list up, `SET_PRESET` and
`SKIP_PRESET` did nothing while the protocol kept answering normally
(RELOAD-04 — watched at the panel, not instrumented).

**A wrong id fails silently.** An absent id does nothing at all — no floor, no
clamp to the last entry, no wrap, no modulo — and that now covers both cases:
above the highest id present (RECALL-04) and inside an interior hole
(RECALL-05: id 90, between 81 and 100, left the frame identical on all 2048
channels). Interior holes are exactly what a generated bank leaves behind it,
and nothing reports the miss — the rig simply keeps playing the previous cue.
An id **above 127** is fine: `SET_PRESET` reads its byte as-is, bit 7 included,
across the panel's whole range 0–199 (RECALL-06 — bytes 140 and 141 rendered
their own cues exactly). Pages 1 to 10 are all reachable over USB. Bytes
200–255 are unprobed: byte 228 came back a strict no-op, but that shot cannot
separate "no preset at that id" from a bound at 199 (RECALL-06).
