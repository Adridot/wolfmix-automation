# FW-04 — the 2.0.19 cell (BEFORE measuring)

Every measurement in this repository was made on firmware 2.0.18; the
controller has reported **2.0.19** since 2026-09-04. This sheet says what is
replayed to open the cell, what is already in hand from PATCH-02/03, and what
is deliberately not replayed.

## The vendor's own word

`~/Library/Application Support/com.nicolaudiegroup.wtools/wm-fw-bundle-2.0.19/changelog.json`,
channel `debug`, built 2026-09-01, `wolfmixFirmware.bin` 418 093 bytes (2.0.18:
418 141): **one line** — *«Fix issue showing gobo icons for gobo features with
self shake, self bounce and self index.»* A display fix on the gobo page,
nothing about the file, the protocol or the DMX engine.

## Already measured on 2.0.19, by PATCH-02 and PATCH-03

| 2.0.18 reading | 2.0.19 |
|---|---|
| a no-change save writes nothing but the counter (COV-64) | held, every record byte-identical |
| channels no role claims carry their record-120 value at rest (COV-16) | held exactly on seven channels |
| the output stream is a 25 Hz clock (COV-34) | 25.01 fps, 200 frames |
| the store is verified by download, record for record | held twice |

## Replayed here, with predictions

| # | Probe | Prediction | p |
|---|---|---|---|
| R1 | `GET_SETTINGS` decoded by the 20-field table | **no `unknownFields`** — 2.0.19 adds no setting the table cannot name | 0.85 |
| R2 | `GET_PROFILE` on the three PATCH-02 profiles and **20 profiles drawn at random** from the 3 364 on the device (PROFILE-02's tables) | no `unknownFields` anywhere | 0.85 |
| R3 | `SET_MODE presets` → `GET_SETTINGS` → `SET_MODE home` → `GET_SETTINGS` | reported mode **5** then **0** — the mechanism of SCREEN-01, not the map | 0.9 |

**Not replayed: a preset recall.** The live project's only preset paints
pad 0 of every group, and pad 0 of group B is R 255 G 127 A 255 — exactly the
colour already on the pars at rest. A recall would repaint what is there,
which proves nothing (trap 4). The recall mechanism (RECALL-03) waits for a
project with two presets that differ.

**Not replayed: the panel's mode map.** MODE-01 was a walk of the front
panel with the operator; R3 checks only that the reported mode follows the
byte sent.

If R1 or R2 fails, the new field is recorded under its neutral number and the
cell says which message grew.

## Results (2026-09-04, evening)

| # | Outcome |
|---|---|
| R1 | **held** — 20 fields, `firmwareVer` `2.0.19`, no `unknownFields` |
| R2 | **held** — 23 profiles read (the three of PATCH-02 and 20 drawn at random, seed 20260904, from the 3 364 on the device), **none** with an `unknownFields` anywhere in its tree |
| R3 | **held** — reported mode `5` after `SET_MODE presets`, `0` after `SET_MODE home` |

Seven readings replayed on 2.0.19, seven held. `2.0.19` joins the tested
firmware list, and the gate that refused it — rightly, four times in one
evening — closes behind it. What the cell does not say: nothing about the
gobo page, which is the one thing the vendor changed.
