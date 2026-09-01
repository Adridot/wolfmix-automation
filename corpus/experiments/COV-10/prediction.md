# COV-10 — is `165.f27` the per-group position FADE? (BEFORE measuring)

COV-02 showed `f27` is not zero everywhere: WTOOLS-written projects carry
`[1000] × 8`, panel-composed ones carry eight explicit zeros. It named the
author and not the meaning, and left 1.87 % of the file unread.

COV-08's photographs answered the meaning question by accident. The
`ALL POSITIONS` page carries **one `FADE` per group**, printed in seconds, and
on the experiment project — whose every preset has `f27 = [0] × 8` — all of
them read **`0s`**.

1000 is the shape of a millisecond default. `f11` FADE and `f15` HOLD are
already milliseconds. And the field numbering corroborates from a second
direction: `f27` sits immediately before `f28`, the per-group **position
index** — two per-group tables side by side, which is what §5.6 says the
numbering is good for.

## The measurement, which writes nothing

`WMX EXP05` is on the controller and carries **both values on two adjacent
pads**:

| Pad | preset | `f27` |
|---|---|---|
| page 1, slot 1 | the unnamed first entry | `[0] × 8` |
| page 1, slot 2 | the next one | `[1000] × 8` |

Recalling a preset is a read of the file into the live copy. No save, no
capture, no deploy.

| # | Manipulation | Prediction | p |
|---|---|---|---|
| 1 | open `WMX EXP05`, recall **page 1 slot 2**, look at `ALL POSITIONS` | every group's `FADE` reads **`1s`** | 0.65 |
| 2 | then recall **page 1 slot 1**, same page | every group's `FADE` returns to **`0s`** — the control, and the half that a one-shot cannot give | 0.6 |
| 3 | rival | the `FADE` does not move between the two recalls → `f27` is not this control, and the WTOOLS/panel split stays an author fact | 0.3 |
| 4 | rival | it moves, but not to `1s` → the unit is not milliseconds and the value is something else | 0.05 |

## What confirmation would buy

`f27` becomes `position_fade_ms`, a per-group array in milliseconds, and
1.87 % of the file moves from `partial` to a named field. It would also
explain the author split without any firmware theory: WTOOLS initialises the
table to a 1 s default, this panel writes 0.

## What refutation would cost

Nothing already published. COV-02's author split is a measurement and stands
either way; only the millisecond hypothesis falls, and Q1 goes back to needing
a control that moves the field.

## Note on the state

Opening another project on the panel changes the active project. That is not a
write to either file's content — F7-02 measured a panel action that moved only
the version counter, leaving all 45054 payload bytes identical. Return to
`WMX EXP format-lab` afterwards.
