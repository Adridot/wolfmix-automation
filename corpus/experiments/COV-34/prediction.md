# COV-34 — the engine's tick, measured on the link (BEFORE measuring)

A third-party guide of **unknown provenance** states that the W1 rebuilds its
output "every 40 ms (25 fps)". The same document is **wrong** where this
repository has measured: it says the gobo palette is derived in real time and
not stored, which EXP-06 refuted and RENAME-01 contradicts device-confirmed.
So it is a source of leads, not of facts — and this is the cheapest of its
claims to test, because the controller already ships every frame over USB.

## What this measures, and what it does not

`dmx-envelope` receives one `DMX_PACKET` per output frame. Counting arrivals
gives the **cadence of the USB stream**. The DMX outputs are physically
unplugged and there is no receiver here, so **nothing below is a measurement of
the DMX line**. If the controller clocks the line and the link differently,
this experiment cannot see it, and the write-up must say so rather than let
"25 fps" stand as if a lighting desk had confirmed it.

What makes the number worth reading anyway: at 2048 channels a frame, 25 fps is
51 kB/s and 44 fps is 90 kB/s. Both are far under what the link carries — the
observed rate is not the link running out of room, so it reflects a decision
the firmware makes.

An average alone cannot separate "one frame every 40 ms" from "one every 20 ms
with every other dropped", which is why the tool now reports the **distribution
of arrival gaps** and not just a count.

## Do

Two windows of 30 s, one variable between them: whether the engine is animating.

- **A — static.** A preset with no FX running.
- **B — animated.** A preset with a Move FX *and* a Colour FX running, so a
  large number of channels change on every frame.

Nothing is written to the project. **Do not save**: a recall moves the live
copy, and `corpus/experiments/COV-32/before.wpj` has to stay a *before*.

## Predictions

Rival periods, pre-registered, with the median arrival gap that identifies each:

| median gap | rate | reading | p |
|---|---|---|---|
| **40.0 ms** | 25.0 fps | the guide's claim, a fixed engine tick | 0.45 |
| **22.7 ms** | 44.1 fps | one USB frame per DMX512 frame — 513 slots at 250 kbit/s plus break | 0.20 |
| **33.3 ms** | 30.0 fps | a 30 Hz tick | 0.15 |
| anything else, or no stable median | — | the stream is event-driven and not a clock | 0.20 |

| # | Prediction | p |
|---|---|---|
| 1 | the median gap lands on one of the three periods above, within ±2 ms | 0.8 |
| 2 | **A and B give the same rate**, within 5 % — a fixed tick does not care what the engine is drawing | 0.75 |
| 3 | tight jitter: p75 − p25 ≤ 8 ms | 0.6 |
| 4 | every frame carries **2048** channels, the four universes in natural order | 0.8 |
| 5 | rival worth naming: **B is faster than A**, or A produces almost nothing. Then the stream is emitted on change and the cadence says nothing about any engine tick — and prediction 2 is the one that catches it | 0.2 |

## Collision check

The three candidate periods are 40.0, 22.7 and 33.3 ms — the closest pair is
**6.7 ms apart**, and a 30 s window yields between 700 and 1300 gaps, so the
median resolves them by a wide margin. Nothing else on the reported line lands
near those values: `windowSeconds` is ~30, `framesPerSecond` is the reciprocal
and cannot corroborate the median independently, and `channels` is 512 or 2048.
Prediction 5 is separated from 1-3 by a **comparison between the two windows**,
not by any single number, so no observation satisfies both.

## What a wrong prediction buys

If 2 fails, the interesting object is not the tick but the emission rule, and
every DMX capture this repository has taken becomes a measurement of that rule
rather than of the output. That would touch the envelope oracle itself, which
is used as a differential instrument throughout `research/`.
