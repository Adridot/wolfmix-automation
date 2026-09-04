# RECALL-07 — a preset recall on 2.0.19, with a discriminator (BEFORE measuring)

FW-04 left the recall out of the 2.0.19 cell: the live project's one preset
paints pad 1 of every group, the colour already at rest. This adds a second
preset that paints **pad 4** — R 60, B 255, UV 255 on every group's palette —
so a recall has something to change.

## The candidate

`show.json` on `candidate-v2.wpj` (the project on the device since
PATCH-03): one preset created by `template`, id **1** (page 1, slot 2), named
`Rappel bleu`, `static_color` = pad 4 on A–H, everything else cloned from
preset 0. `wpj_show.py verify`: record 165 is the only record that differs.
Candidate sha256 `…`.

## Procedure

1. `deploy two-presets.wpj --label patch02 --case RECALL-07` — the runner
   stores, verifies, restarts, verifies, captures a frame.
2. **Operator:** reopen `WMX EXP patch02` (the live copy does not follow a
   store, RELOAD-04).
3. `wolfmix.py dmx-envelope` at rest; `wolfmix.py preset 1`; envelope;
   `wolfmix.py preset 0`; envelope.

## Predictions

| # | Prediction | p |
|---|---|---|
| C1 | at rest after the reopen, the frame equals PATCH-03's `rest-v2.json` — the new preset changes nothing until recalled | 0.8 |
| C2 | after `preset 1`, the pars at 101/111/121 read **red 60, green 0, blue 255, white 0, amber 0, uv 255** (channels +1…+6), dimmer 255, shutter 0, 109/119/129 = 4, 110/120/130 = 127 | 0.7 |
| C3 | the bar's three cells read **60, 0, 255**; 200 = 68 | 0.7 |
| C4 | the heads' colour wheel (channels 9 and 25) leaves 88; pan/tilt, shutter, dimmer, focus unchanged | 0.6 |
| C5 | after `preset 0`, the frame returns to `rest-v2.json` exactly | 0.75 |

The byte sent is the **id** (RECALL-03); 1 is a present id, so the recall is
addressed. If C2 fails while C1 holds, the recall mechanism is what 2.0.19
changed, and that is the finding.
