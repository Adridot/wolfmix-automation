# PATCH-02 — a compiled patch opened on the W1 (BEFORE measuring)

The first project whose patch was written by `tools/wpj_patch.py` and not by
the device. PATCH-01 proved the bytes against the corpus; this proves — or
refutes — that the controller accepts them, and it is written before the
first upload, with its probabilities.

## The candidate

`rig.json` in this directory: skeleton = `clean` as it sits on the device
(version 9, sha256 `ad388a41…`, byte-identical to COV-49 stage 3), profiles
read from *rig-b* and from the skeleton, six fixtures:

| # | Profile | Panel DMX | Group |
|---|---|---|---|
| 0, 1 | Lyre ZQ02244 (16 ch, 1 block) | 001, 017 | A «Lyres» |
| 2, 3, 4 | 6x18W 6in1 RGBAW UV (10 ch) | 101, 111, 121 | B «Pars» |
| 5 | LED BAR 252 RGB (11 ch, **3 blocks**) | 200 | C «Barre» |

Gobo pad 425 of group A named «Etoile». Candidate sha256 `…`, 24/24
identities, 0 anomalies. The three profile UUIDs are in the device library
(`wolfmix.py profiles`, read before this sheet).

**Not a hand-patched twin.** The ledger row promised a comparison against the
same rig patched by hand; the DMX predictions below are derived from the file
instead (COV-16's rule), which is stricter and costs no gesture. The twin
stays optional, for a refusal that needs a control.

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
