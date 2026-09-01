# COV-08 — `150.f8`, the CROSS half of the POSITION screen (BEFORE measuring)

`150.f8` is 1.90 % of the corpus and the largest single unread field left. SPEC
§3.2 lists it as `CROSS`, **[hypothesized]**, and it has never been read off a
screen. It does not need a write, a save or a deploy: the experiment project
already holds a slot where it is not neutral.

Bench: W1 on firmware 2.0.18, WTOOLS **closed**, DMX outputs unplugged, project
`WMX EXP format-lab` open on the panel. Nothing is written.

## What is on screen

Record 150, group A, slot 3, named `Center Point`. Its five values disagree,
which is what §3.2 says a readable slot needs.

Two readings compete, and they are the two this format actually uses:

- **unsigned** — `percent = value / 65536`, the reading device-confirmed for
  PAN, TILT and FAN (POS-02), with the screen **truncating**;
- **signed** — `percent = (value − 32768) / 32767`, the reading device-confirmed
  for `151`'s three offsets (POS-04) and for `150.f4` FOCUS OFFSET.

| Field | raw | unsigned predicts | signed predicts |
|---|---|---|---|
| PAN `f6` | 39976 | **60** | +22 |
| TILT `f7` | 5242 | **7** | −84 |
| FAN `f3` | 33422 | **50** | +2 |
| FOCUS OFFSET `f4` | 32768 | 50 | **0** |
| **`f8`** | **36044** | **54** | **+10** |

`f8`'s two candidates are 54 and 10. Neither collides with the other, nor with
any other value on the same screen (7, 50, 60) — checked mechanically before
this file was written.

**The measurement carries its own control.** PAN, TILT and FAN are already
device-confirmed, so if the screen shows 60 / 7 / 50 the panel is holding the
state this prediction was computed from and the `f8` reading is usable. If it
does not, the project on the controller has moved and nothing is concluded.

The truncation matters and is not a detail: 39976 is 60.998 % and shows **60**,
5242 is 7.998 % and shows **7**. Predicting these by hand gives 61 and 8, and
would have made a correct reading look refuted.

## Predictions

| # | Manipulation | Prediction | p |
|---|---|---|---|
| 1 | `SHIFT` + position pad `Center Point`, group A | PAN **60**, TILT **7**, FAN **50** — the control, three fields already device-confirmed | 0.9 |
| 2 | same screen, `FOCUS OFFSET` | **0**, not 50: `f4` is the signed reading | 0.85 |
| 3 | same screen, the `CROSS` half of the `FAN \| CROSS` encoder | **54** — `f8` is unsigned like PAN/TILT/FAN, since it sits in their group and not in `151`'s | 0.6 |
| 4 | rival for 3 | **10** — `f8` is signed like the FOCUS OFFSET it sits next to | 0.35 |
| 5 | rival for 3 | the encoder has no `CROSS` mode on this firmware, or it shows something that is neither | 0.05 |
| 6 | slot 1 of the same palette, for a second point | `f8` = 32767 → unsigned **49**, signed **0**. Its FOCUS OFFSET is 65535 → unsigned 99, signed **+100**, which is §3.2's own worked example and a second check on reading 2 | 0.8 |

## What each outcome settles

- **54** → `f8` is CROSS on the unsigned scale, `150` is internally consistent,
  and 1.90 % of the file moves from `partial` to a device-confirmed name.
- **10** → `f8` is CROSS on the signed scale, and record 150 mixes both
  conventions in one sub-message — worth knowing, and a trap for any writer.
- **neither** → the name `CROSS` is wrong and §3.2's hypothesis goes, which is
  the outcome that would cost the most and is why it is written down first.

`FAN` and `CROSS` share one encoder, the way `Size | Fan` and `Size | Feature`
share `f3` on the FX engines. If the screen shows only `FAN`, the encoder has
to be switched before measure 3 can be read at all — and a screen that offers
no `CROSS` mode **is** outcome 5, not a failed attempt.
