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
better — with one exception in each direction. `dimmers` (`165.f17`) is writable
although its status is `hypothesized`; `f29` (gobos) stays out of scope although
it is device-confirmed, because nothing needs it yet. `size`/`fade`/`phase`
(`f8`/`f6`/`f9`) are excluded on purpose: their attribution is still
`hypothesized`, so they are readable via the codec but not writable here.

Keys are French, matching the codec's key names.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `base` | string | **required** — path to the donor variant-A `.wpj` |
| `nom` | string | new project name (record 101) |
| `presets` | array | preset edits (record 165) |
| `positions` | array | named pan/tilt positions (record 150, one copy per group A–H) |
| `palette` | array | Color FX palette pads (record 135) |

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
| `dimmers` | int[8] | 0–255 | dimmer level per group A–H. **No measured effect**: GEN-01 wrote 120 and 0 with the `OTHER` toggle on and no dimmer channel moved. Writable, unproven — see the gates below. |
| `masque_contenu` | int | 0–63 | `f10`, the six `PRESET EDIT` toggles: bit 0 `COLOR`, 1 `MOVE`, 2 `BEAM`, 3 `GOBO`, 4 `LIVE EDIT`, 5 `OTHER`. A **set** bit means the toggle is **off**. device-confirmed, F4-02. |
| `pattern_couleur` | int[8] | 0–10 | `f30`, the static colour's spread mode per group; `9` = `SINGLE`. device-confirmed, F30-02. |
| `couleur_statique` | 8 × int[] | pads 1–20 | `f31`, the static colour: for each group A–H, the pads of **that group's** palette (record 140) to light. device-confirmed. |
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
| `vitesse` | 0–200 | speed percent |
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
      "color_fx1": {"effet": 2, "vitesse": 120}
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

## Two gates that make a clean compile do nothing

The compiler verifies the **file**. Two masks decide whether the device acts on
what it verified. One is now writable; the other is not — so pick a donor preset
that already has it right.

| Gate | What it silences | Where |
|---|---|---|
| `165.f10`, the content mask — a **set** bit means the toggle is **off** | bit 1 (`MOVE`) written by us **is** honoured (GEN-01). Bit 5 (`OTHER`) was supposed to gate `dimmers`, and with it clear the dimmers still did nothing — so ACC-02's silence is *not* explained by this mask after all. **Writable since this version** via `masque_contenu`. | SPEC.md §5.3 |
| `165.f16`, the engine group masks — slices 0/1/2 = Color/Move/Beam | an FX edit is invisible for a group the engine is not enabled on. ACC-03 set `color_fx_actif` without `f16` and the device followed `f16`. | SPEC.md §5.4, correlated |

`color_fx_actif` and `move_fx_actif` duplicate slices 0 and 1 of `f16`. They are
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
