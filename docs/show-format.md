# `show.json` — the edit spec

The input format of `tools/wpj_show.py compile`. It is an **edit spec**, not a
show description: it names a donor `.wpj` and the handful of fields to change
in it. Everything not named is preserved byte for byte.

```bash
python3 tools/wpj_show.py compile show.json out.wpj
```

No project file ships with this repository, so the donor is one of yours —
see [`corpus.md`](corpus.md).

## Why template-based

Creating a record from scratch is not something the compiler does. A
**position** or a **palette entry** you edit must already exist in the donor;
nothing has been measured about synthesising one. A **preset** may be created,
by cloning one of the donor's with `modele`: PRESET-01, 06 and 07 showed that
appending a well-formed entry with a free id works, is accepted, and survives
store, restart and a cold reopen — `165.f1` gates nothing and is left verbatim
(85 entries loaded with `f1` = 81). Creation is append-only: the new id must
exceed every id in the donor, which is what both measured additions did. Gaps
in the id sequence load fine.

Pick a donor that already has the positions and pads you need — that constraint
is rule 2 ("read before write") applied to editing.

Scope is records 101, 165, 150 and 135, at evidence status `correlated` or
better. `f29` (gobos) stays out of scope although it is device-confirmed,
because nothing needs it yet. `dimmers` (`165.f17`) used to be the one field
written below the threshold; GEN-02 moved it to device-confirmed. `phase`, `size`
and `fade` (`f6`, `f8`, `f2`) are now **named and validated** (FX6-02/03) but
stay out of the writer: rule 2 wants a byte-identical round-trip *and*
acceptance downstream before a field becomes writable, and neither has been done
on them. They are readable through the codec.

Keys are French, matching the codec's key names.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `base` | string | **required** — path to the donor variant-A `.wpj` |
| `nom` | string | new project name (record 101) |
| `presets` | array | preset edits (record 165) |
| `positions` | array | named pan/tilt positions (record 150, one copy per group A–H) |
| `palette` | array | Color FX palette pads (record 135) |
| `gobo_names` | object | gobo pad names, `{"<gobo id>": "Nom"}` (record 145, group A) |
| `gobo_order` | array | the wheel's complete gobo id list, in the wanted pad order (records 111 + 145) |
| `mappings` | array | DMX IN mappings — bind an incoming channel to a controller function (record 130) |

Any other key is an error. A spec with only `base` is legal and produces a
byte-identical copy of the donor — the cheapest possible proof that the
pipeline is lossless.

## `presets[]`

Addressed by `id`, which is the linear preset index
`id = (page - 1) * 20 + (slot - 1)`.

| Key | Type | Bounds | Meaning |
|---|---|---|---|
| `id` | int | ≥ 0 | **required** — an existing preset in the donor, or a new id above every existing one when `modele` is given |
| `modele` | int | ≥ 0 | id of the donor preset to **clone** into a new entry. Only on an id the donor does not have; refused on one it does. The clone carries every unknown field verbatim, which is the point. |
| `nom` | string | **≤ 19 UTF-8 bytes** | preset name. **Enforced** — past 19 bytes the *whole project* refuses to open on the device (device-confirmed, PRESET-05), and auto-verify could not see it: the value reads back fine. |
| `positions` | int[8] | ≥ 0 | position index per group A–H |
| `dimmers` | int[8] | 0–255 | dimmer per group A–H, as a **percentage of 255** — the output is `f5 + (v/255)·(f6 − f5)` through the channel's travel limits, and on a fixture with colour channels it scales the colour instead. Device-confirmed (GEN-02), **but silent unless the controller setting `store group dimmers in preset` is on** — see the gates below. |
| `content_mask` | int | 0–63 | `f10`, the six `PRESET EDIT` toggles: bit 0 `COLOR`, 1 `MOVE`, 2 `BEAM`, 3 `GOBO`, 4 `LIVE EDIT`, 5 `OTHER`. A **set** bit means the toggle is **off**. device-confirmed, F4-02. |
| `color_pattern` | int[8] | 0–10 | `f30`, the static colour's spread mode per group; `9` = `SINGLE`. device-confirmed, F30-02. |
| `static_color` | 8 × int[] | pads 1–20 | `f31`, the static colour: for each group A–H, the pads of **that group's** palette (record 140) to light. device-confirmed. |
| `beam_fx1`, `beam_fx2` | object | see below | beam effect slots |
| `color_fx1`, `color_fx2` | object | see below | colour effect slots |
| `move_fx1`, `move_fx2` | object | see below | movement effect slots |

An FX slot must already exist on that preset in the donor; creating one is not
validated.

### FX sub-message

The same shape for all six slots. Only these keys are accepted:

| Key | Bounds | Meaning |
|---|---|---|
| `effet` | 0–8 | effect type, device-confirmed (ACC-04). The bound is the **Beam** enum; Color defines only `0`–`7` and no enum is published for Move, so the compiler accepts out-of-enum values on those slots — check the right enum yourself (`SPEC.md` §5). |
| `vitesse` | 0–100 | speed percent — **codec field `f9`**. Until FX6-02 this key wrote `f2` and the bound was 0–200; `f2` is the **fade**, so a show that set `vitesse` above 100 was lengthening the fade, not speeding the effect. The key kept its name and changed field. |
| `link_order` | 10–13 | link order, **Group family only**. The field's domain is `0–3` None, `10–13` Group, `20–23` Fixture; the compiler accepts only the Group range. |
| `speed_source` | 0–2 | speed source |
| `bpm_division` | int | BPM division: `0`→×8 … `7`→1/16, default 3. **The compiler does not enforce 0–7** — any non-negative int passes. |

## `positions[]`

Record 150 exists eight times, **one per group A–H**; `page` selects which
(1 = A … 8 = H — the key is named `page` for historical reasons).

| Key | Type | Bounds | Meaning |
|---|---|---|---|
| `page` | int | 1–8 | **required** — group A–H |
| `index` | int | ≥ 0 | **required** — slot index within the group, must exist |
| `nom` | string | — | position name |
| `pan` | int | 0–65535 | PAN, value = percent × 65535 (codec field `f6`) |
| `tilt` | int | 0–65535 | TILT, same scale (codec field `f7`) |
| `fan` | int | 0–65535 | FAN, same scale (codec field `f3`) |

Percentages are stored as `round(percent × 65535 / 100)`: 50 % = 32768, 23 % =
15073. The device's own screens **truncate** when they display a percentage, so
reading a value back off the panel can show one less than you wrote.

FOCUS OFFSET (`f4`) is signed — 32768 is 0 % — and CROSS (`f8`) is still
hypothesised; neither is writable here.

> An earlier version of this document mapped `pan`/`tilt` to `f3`/`f4`. That
> attribution was refuted by the device's own edit screen: `f3` is FAN and `f4`
> is FOCUS OFFSET. The compiler now writes `f6`/`f7`. If you built a show
> against the old mapping, recompile it.

## `palette[]`

| Key | Type | Bounds | Meaning |
|---|---|---|---|
| `index` | int | ≥ 0 | **required** — pad index, must exist in the donor |
| `rouge` | int | 0–255 | red |
| `vert` | int | 0–255 | green |
| `bleu` | int | 0–255 | blue |

The remaining four pad channels (`blanc`, `ambre`, `lime`, `uv`) decode fine but
are not writable here. The seven-channel order was read off the W1's own `RGB+`
view and is device-confirmed on record **140**; record 135 inherits it at
`correlated`, and no write to 135 has been checked on a device either.

## `gobo_names` / `gobo_order`

Both device-confirmed (RENAME-01, SORT-01 — `SPEC.md` §3.4), on group A.

`gobo_names` writes `145.f3`, the operator-assignable pad label, addressed by
gobo image id: `{"343": "Papillon"}`. Names are capped at 19 UTF-8 bytes —
the preset-name limit (PRESET-05), unmeasured on this field, so refused
conservatively.

`gobo_order` is the **complete** id list of the wheel in the wanted order;
anything else is refused. The record-111 wheel ranges (`fonction` 14) are
permuted — each keeps its DMX bounds, the id-less open range stays first —
and the record-145 palette is rewritten consistently: names travel with
their gobos, glyphs are resequenced from `!`. The firmware accepts the
resulting non-monotonic range list and uses it as the pad order. A wheel
carried by a second group's palette is refused as unmeasured.

## `mappings[]`

Each item binds one incoming DMX channel to one function of the controller —
the `Mappings` screen, mode 43. On a Mk1 only the DMX side exists; MIDI is Mk2
and higher.

| Key | Type | Meaning |
|---|---|---|
| `cible` | string | **required** — the function; see the table below |
| `groupe` | string | `"A"`–`"H"`, required for `dimmer_groupe` only |
| `index` | int | the preset index, required for `preset` only |
| `canal` | int or null | **required** — the DMX IN channel **1–512**, or `null` to remove the mapping |

| `cible` | `f4` | Function | Instance |
|---|---|---|---|
| `dimmer_groupe` | 20 | a group's dimmer | `groupe`, A–H |
| `main` | 27 | the MAIN dimmer | none |
| `preset` | 70 | a specific preset | `index`, 0–199 |
| `select_preset` | 70 | Select Preset — the incoming **value** picks | none |
| `preset_page` | 82 | a preset page | `page`, 1–7 |
| `bpm_tap` | 17 | BPM Tap | none |
| `wolf` | 10 | Wolf | none |
| `strobe` | 11 | Strobe | none |
| `blinder` | 12 | Blinder | none |
| `speed` | 13 | Speed | none |
| `blackout` | 14 | Blackout | none |
| `smoke` | 15 | Smoke | none |
| `jump_preset` | 78 | Jump Preset — the incoming **value** picks | none |
| `previous_preset` | 78 | Previous Preset | none |
| `next_preset` | 78 | Next Preset | none |

**These fifteen are the whole screen, and nothing else is writable.** The
screen offers five *categories*, but the file stores the *function*: the seven
`Flash` entries carry seven different ids. Every id above was written by the
controller when the operator selected that item; nothing is inferred from a
sequence, so any other `cible` is refused.

**A function id is not unique on its own.** `preset` and `select_preset` share
`f4 = 70`; `jump_preset`, `previous_preset` and `next_preset` share `f4 = 78`.
An entry is identified by the **pair** `(f4, instance)`, which is also how this
compiler addresses it.

**Instance 255 means "no fixed instance".** Every function without a numbered
target carries it — including the two where the incoming DMX *value* is what
picks the preset. Only `dimmer_groupe`, `preset` and `preset_page` take a
number, and `main` is the one function that carries 0 instead of 255: it is a
factory entry, and why it differs is not measured.

**Removing is an absence, not a value.** `"canal": null` deletes the entry —
there is no "unmapped" sentinel to write. Removing a mapping that does not
exist is an error, so a spec cannot silently do nothing.

**An entry is addressed by function and instance, never by position.** The wire
order of the table shifts on its own between saves, twice observed in eleven,
with no reading that survives. The compiler edits in place, appends new
entries at the end, and keeps `f1` equal to the entry count.

**Channels above 256 are not special to you but are to the format.** The
channel is stored zero-based across two fields, `f5 × 256 + f6`. The compiler
splits it; you always write the channel as it appears on the screen.

**Duplicates are allowed.** Two functions may share a channel — the firmware
permits it, and one value then drives both. Nothing here prevents it, so check
your own map.

```json
"mappings": [
  {"cible": "dimmer_groupe", "groupe": "A", "canal": 1},
  {"cible": "main", "canal": 9},
  {"cible": "preset", "index": 4, "canal": 40},
  {"cible": "wolf", "canal": 45},
  {"cible": "dimmer_groupe", "groupe": "C", "canal": null}
]
```

## Example

```json
{
  "base": "corpus/projects/your-project.wpj",
  "nom": "MY SHOW",
  "presets": [
    {
      "id": 33,
      "nom": "Chaser",
      "dimmers": [255, 255, 128, 0, 0, 0, 0, 0],
      "color_fx1": {"effet": 2, "vitesse": 80}
    }
  ],
  "positions": [
    {"page": 1, "index": 0, "nom": "Public", "pan": 32768, "tilt": 15073}
  ],
  "palette": [
    {"index": 0, "rouge": 255, "vert": 40, "bleu": 0}
  ]
}
```

## Three gates that make a clean compile do nothing

The compiler verifies the **file**. Three gates decide whether the device acts
on what it verified — and one of them is not in the file at all.

| Gate | What it silences | Where |
|---|---|---|
| **`store group dimmers in preset`**, a **controller setting** — not in the file at all | every `dimmers` value in the project, whatever `f10` says. A show can compile, verify and deploy perfectly and still move no level. | GEN-02, device-confirmed |
| `165.f10`, the content mask — a **set** bit means the toggle is **off** | bit 1 (`MOVE`) written by us **is** honoured — a preset whose `MOVE` toggle is off leaves pan and tilt where the previous cue put them (RECALL-05, validated). Bit 5 (`OTHER`) gates `dimmers`, and nothing else a static cue carries: GEN-02 first showed the silence blamed on it was a controller setting, then FW-03 wrote the bit alone and measured exactly the eighteen dimmer channels the model predicts — **`validated`**. **Writable since this version** via `content_mask`. | RECALL-05, GEN-02, FW-03 |
| `165.f16`, the engine group masks — slices 0/1/2 = Color/Move/Beam | an FX edit is invisible for a group the engine is not enabled on. ACC-03 set `color_fx_active` without `f16` and the device followed `f16`. | SPEC.md §5.4, correlated |

`color_fx_active` and `move_fx_active` duplicate slices 0 and 1 of `f16`. They are
redundant, and a writer must not let them drift apart. That is why `f16` stays
out of scope: [`wpj_generate.py`](generator.md) picks a donor preset whose
engines already match the cue and clones it, rather than writing the mask.

## What compile guarantees

On success, `compile` prints one line per changed record (type, occurrence,
size before/after) and `ok : out.wpj`. Before it gets there it has:

1. rejected every key outside the scope above, and every value out of bounds;
2. rejected any target that does not already exist in the donor;
3. written to a **new** file (an existing path is refused);
4. reloaded that file, revalidating the SHA-1 header;
5. re-decoded every edited record and checked each requested value reads back;
6. verified that **no record outside the edit set changed**.

If any of 4–6 fails, the output file is deleted and the command exits 1. The
same comparison is available on its own:

```bash
python3 tools/wpj_show.py verify base.wpj out.wpj
```

The compiled file has not been through WTOOLS or a controller — that step is
yours, and it is what moves a field from `validated` to `device-confirmed`.
