# `intent.json` — the show generator

The input of `tools/wpj_generate.py compose`. Where
[`show.json`](show-format.md) names fields, this names **intentions**: a list
of ambiances with an energy, a colour and the groups they light. The generator
reads the rig out of the donor, turns each ambiance into one preset, and hands
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
| `nom` | string | project name (record 101) |
| `page` | int 1–10 | preset page to fill; default = the first page above the donor's highest id |
| `ambiances` | array | one cue each, filled into slots 1, 2, 3 … of that page |

Ids follow the panel formula `id = (page − 1)·20 + (slot − 1)`, so more than
twenty ambiances simply spill onto the next page.

## `ambiances[]`

| Key | Type | Meaning |
|---|---|---|
| `nom` | string | cue name, **truncated to 19 UTF-8 bytes** on a character boundary |
| `energie` | int 0–100 | how much the cue does — see the ladder below |
| `couleur` | `"#rrggbb"` | the static colour asked for |
| `groupes` | array of `"A"`…`"H"` | which groups light; default = every group that has a fixture |
| `position` | string | a named position from record 150, e.g. `"Crowd"` |
| `dimmer` | int 0–255 | override the ladder's dimmer level; energy says how busy the cue is, this says how bright |
| `live_edit` | bool | `false` locks the cue against panel edits. Default: inherit the template's. **Set it `false` for any cue you intend to measure** — with LIVE EDIT on, a gesture at the panel rewrites the cue's *live copy* while the file stays exactly as deployed, and a recall then measures something else (GEN-03). |
| `modele` | int | force a template preset id instead of the one the ladder picks |

## The energy ladder

Energy selects a **family**, which is a template preset in the donor, plus a
dimmer level and an FX speed. The values are settings, not measurements — the
table lives at the top of `wpj_generate.py` and is meant to be retuned on the
rig.

| `energie` | family | dimmer* | beam FX | speed |
|---|---|---|---|---|
| 0–24 | `statique` | 120 | — | — |
| 25–49 | `faisceau` | 180 | Sparkle | 45 % |
| 50–74 | `mouvement` | 225 | — | 110 % |
| 75–100 | `mouvement+faisceau` | 255 | Chaser | 170 % |

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

Nothing writes a palette. Each group has its own 20-pad palette (record 140),
and the generator picks the pad **nearest** to the requested RGB, then sets that
group's bit in `165.f31` and its `165.f30` pattern to `SINGLE`. So the colour
you get is the closest one the rig was already set up with — check the pad
column the compose report prints.

## The trap this exists to avoid

Two masks decide whether a clean compile does anything at all, and only one of
them is writable:

| Mask | What it does | Handled how |
|---|---|---|
| `165.f10`, content mask — a **set** bit means the toggle is **off** | silences dimmers unless bit 5 `OTHER` is clear | written: `COLOR` and `OTHER` on, `MOVE`/`BEAM` per family, `GOBO` off |
| `165.f16`, the engine group masks | an FX edit is invisible for an engine that is off | **not written** — the generator clones a donor preset that already has the right engines |

`f16` is duplicated by `color_fx_actif`/`move_fx_actif`, and writing one without
the other produces a preset the device renders differently from what the file
says (ACC-03). Cloning sidesteps the whole question; that is why the generator
picks a template instead of assembling a preset from nothing.

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

`mode 1` first: it is the escape from any modal screen, and the panel's screen
has been *suspected* of gating recalls — unsettled, since the runs that showed
it were addressing the wrong id and judged by a withdrawn discriminator. An id
above the highest one present does nothing; interior gaps are unprobed, and no
preset above id 127 has ever been measured.
