# COV-16 — is `120.f1` the channel's DMX value? (BEFORE measuring)

Record 120 is 2.0 % of the corpus and four of its fields are unnamed. §7 calls
it a "flat per-fixture-channel value table" and names nothing inside it.

Laid out in **ascending DMX-address order** — which is what §7 says the blocks
follow, and not the item order of 115 — the table stops looking arbitrary. It
is **constant per profile**: the four `6x18W 6in1 RGBAW UV` fixtures of the
project on the controller carry byte for byte the same ten entries, and the two
moving heads carry the same sixteen.

| profile | offsets 0–6 | 7 | 8 | 9 |
|---|---|---|---|---|
| the RGBAW+UV par | `255` ×7 | absent | `4` | `127` |

That is the shape of a channel value table: seven colour channels open, then
two small constants.

## The measurement, which writes nothing

`wolfmix.py dmx` reads the frame the controller is already emitting. The
outputs are unplugged; nothing moves in the room either way.

Of the 72 channels the patch covers, **26 have no entry in record 106**, so no
engine role claims them. Those are the ones `120` should be visible on. Eight
of the 26 are non-zero and they are the whole discriminator:

| channel | `120.f1` predicts |
|---|---|
| 108, 118, 128, 138 | **4** |
| 109, 119, 129, 139 | **127** |

The other 18 role-free channels predict **0**, which is not evidence on its own —
an unlit channel reads 0 whatever the reason.

| # | Prediction | p |
|---|---|---|
| 1 | ch 108/118/128/138 read **4**, and ch 109/119/129/139 read **127** | 0.7 |
| 2 | the 18 role-free channels at `120.f1 = 0` read 0 — consistent, not evidence | 0.9 |
| 3 | rival: those eight read 0 → `120` is not applied to the live frame, or not to these channels, and the table is something a save writes and the engine ignores | 0.25 |
| 4 | rival: they read something else entirely → `f1` is not a channel value | 0.05 |

**A role-carrying channel proves nothing here** and is excluded from the test on
purpose: the engine drives it, so whatever `120` says can be overwritten. That
is why the discriminator is built only from channels record 106 does not claim.

## Scope, stated before the fact

Confirmation names `f1` and nothing else. `f4` (1 everywhere), `f5` (1 or 2 on
the moving heads only) and `f6` stay unnamed — though the layout already shows
`f5`/`f6` are not noise: on both moving heads `f5` is 1 on offsets 0–1 and 2 on
offsets 2–3, and `f6` runs in consecutive quadruples whose two fixtures are
exactly 17 apart. That is a shape, and it is written down here so that a later
reading cannot claim to have predicted it.
