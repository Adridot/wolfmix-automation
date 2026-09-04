# PATCH-02 — a compiled patch opened on the W1 (BEFORE measuring)

The first project whose patch was written by `tools/wpj_patch.py` and not by
the device. PATCH-01 proved the bytes against the corpus; this proves — or
refutes — that the controller accepts them, and it is written before the
first upload, with its probabilities.

## The candidate

`rig.json` in this directory: skeleton = `clean` as it sits on the device
(version 9, sha256 `ad388a41…`, byte-identical to COV-49 stage 3), profiles
read from *rig-b* and from COV-44 rung 1 — the skeleton's own 120 carries the
COV-53 drop, so its head is not a usable package, which the tool said — six
fixtures:

| # | Profile | Panel DMX | Group |
|---|---|---|---|
| 0, 1 | Lyre ZQ02244 (16 ch, 1 block) | 001, 017 | A «Lyres» |
| 2, 3, 4 | 6x18W 6in1 RGBAW UV (10 ch) | 101, 111, 121 | B «Pars» |
| 5 | LED BAR 252 RGB (11 ch, **3 blocks**) | 200 | C «Barre» |

Gobo pad 425 of group A named «Etoile». Candidate sha256 `d462d0c037e6c1d3…`, 24/24
identities, 0 anomalies. The three profile UUIDs are in the device library
(`wolfmix.py profiles`, read before this sheet).

**Not a hand-patched twin.** The ledger row promised a comparison against the
same rig patched by hand; the DMX predictions below are derived from the file
instead (COV-16's rule), which is stricter and costs no gesture. The twin
stays optional, for a refusal that needs a control.

## A second variable, found at the port

The controller reports firmware **2.0.19** — every measurement in this
repository was made on 2.0.18, and the local bundle is still 2.0.18. The
runner refused the upload on that ground; the upload proceeds under the
untested-firmware flag, deliberately: the write goes to a derived UUID behind
a snapshot, so it is reversible. But the reading rule changes — a **refusal**
here has two candidate causes (the compiled patch, the firmware) and does not
refute the compiler on its own; a **success** is the first row of the 2.0.19
cell in `research/versions.md`, and not a statement about 2.0.18.

## Procedure

1. `wolfmix_experiment.py init candidate.wpj --label patch02` — snapshot,
   upload under `WMX EXP patch02`, verified by download. Nothing else on the
   controller is written.
2. **Operator:** `Main Menu → Projects`, open `WMX EXP patch02`. Photograph
   the `FIXTURES` screen (and the message, if it refuses).
3. `wolfmix.py dmx-envelope rest.json --seconds 10`, nothing touched.
4. **Operator:** save the project on the W1, no change. Then
   `arm --label patch02 --loaded-on-controller`, download, diff against the
   candidate — the one occasion to watch the device's writer rewrite a
   patch it did not write.

## Predictions

| # | Prediction | p |
|---|---|---|
| P1 | the store is verified by download, record for record | 0.9 |
| P2 | the project **opens** — no «Error opening project» | 0.8 |
| P3 | `FIXTURES` lists six fixtures at 001 / 017 / 101 / 111 / 121 / 200, groups A A B B B C, the bar as one fixture | 0.7 |
| P4 | at rest, the channels **no engine role claims** carry their record-120 value, exactly: **109, 119, 129 = 4**; **110, 120, 130 = 127**; **200 = 68** (COV-16) | 0.6 |
| P5 | the heads' pan/tilt sit at **127** on 1, 2, 17, 18 — the file's default, if nothing recalls a position | 0.5 |
| P6 | after the operator's no-change save, 105/106/110/111/116 come back **byte-identical** | 0.7 |
| P7 | record 120 comes back byte-identical — **73 entries, none dropped**: the COV-53 defect is in the device's *add*, not in its save | 0.6 |
| P8 | 115 unchanged — the save allocates no `slot_id` on rows that carry none | 0.5 |
| P9 | 125 unchanged; 161's head stays 63 | 0.6 |

If P2 fails, the three candidates named in the ledger are tested one at a
time on the same skeleton, in this order: `105.f1` (library_id), the omitted
`115.f9`, record 125's flags. One variable per upload.

> No offset encoder, no preset, no FX is touched anywhere in this sheet.

## Results, steps 1–3 (2026-09-04, firmware 2.0.19)

| # | Outcome |
|---|---|
| P1 | **held** — stored as `WMX EXP patch02`, uuid `46642f4b-…`, 10 815 bytes, verified by download |
| P2 | **held** — the project opens; operator-reported at the panel |
| P3 | **held** — six fixtures listed; operator-reported, photograph pending |
| P4 | **held exactly** — `rest.json`, 200 frames at 25.0 Hz, 0 animated channels: 109/119/129 = **4**, 110/120/130 = **127**, 200 = **68** |
| P5 | **refuted, and explained by the frame** — pan 102 / tilt 128 on the head at 001, pan 153 / tilt 128 at 017: the two heads sit **fanned** around 127.5, so the skeleton's position layer drives them as two members of group A |

What the frame says beyond the sheet, 1-based channels, from `rest.json`:

- **head at 001**: 102 128 102 0 · 0 0 **241 220** 88 0 · 0 0 127 0 **192** 0 — shutter and dimmer at the record-120 defaults, the colour wheel at 88 and channel 13 at 127 driven by engines, focus at its default;
- **pars at 101 / 111 / 121**, identical: **255 255 127 0 0 255 0** 0 4 127 — dimmer, red, green, blue, white, amber, uv addressed on the exact channels the compiled 106 names, a static colour (R 255, G 127, A 255) applied to all three;
- **bar at 200**: 68 0 · 255 127 0 · 255 127 0 · 255 127 0 — the same colour on each of the **three cells**, which is the three-block layout read correctly.

A patch whose roles were wrong would put a colour on a wheel or a dimmer on a
fine channel; none of the 41 non-zero channels is misplaced.

## Results, step 4 — the device's writer over a patch it did not write

P3 closed by the operator at the panel: six fixtures, as expected. Then one
no-change save on the W1, `arm`, download: version `…534 → …535`, 10 815
bytes both, **every record byte-identical** but 101 — which carries the
runner's own `WMX EXP patch02` rename, not the device's hand. 24/24
identities, 0 anomalies.

| # | Outcome |
|---|---|
| P6 | **held** — 105/106/110/111/116 byte-identical |
| P7 | **held** — 120 byte-identical, **73 entries**, none dropped |
| P8 | **held** — 115 unchanged, no `slot_id` allocated |
| P9 | **held** — 125 unchanged, 161's head 63 |

**Device-confirmed, on firmware 2.0.19.** And the operator saw the one thing
the file could not show: **`MOVE FX` is selectable on the pars.** The
compiler wrote `125`'s four flags `f1 f2 f5 f7` on every non-empty group,
copied from a fresh project whose two groups both held moving heads. On the
corpus the flags follow the group's *features* — see COV-68 — and the pars
should carry `f1 f2` only. That is PATCH-03's single variable.

## PATCH-03 — the flags, one variable (BEFORE measuring)

`candidate-v2.wpj`: the same `rig.json`, rebuilt after COV-68 — the compiler
now derives 125's flags from the group's features. `wpj_show.py verify`
against `candidate.wpj`: **record 125 is the only record that differs**.
Group A (heads) keeps `has_intensity has_color has_gobo has_move`; groups B
(pars) and C (bar) carry `has_intensity has_color` only.

Procedure: `deploy candidate-v2.wpj --label patch02 --case PATCH-03` —
verified twice, restart, one frame — then **operator:** reopen
`WMX EXP patch02` at the panel and look at the pages offered per group.

| # | Prediction | p |
|---|---|---|
| Q1 | `MOVE FX` and the gobo page are **no longer offered** on groups B and C | 0.8 |
| Q2 | both still offered on group A | 0.9 |
| Q3 | colour still offered on all three | 0.9 |
| Q4 | the frame at rest is unchanged from `rest.json` | 0.8 |

If Q1 fails with Q2–Q4 holding, the flags are not what gates the pages and
COV-68 stays a corpus correlation without a meaning.
