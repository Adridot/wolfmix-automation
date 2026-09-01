# COV-23 — four measurements, written BEFORE any of them

What the corpus can give alone is exhausted at 92.7 %. Each of these targets a
field the sweep could not move, on `WMX EXP format-lab` only, one change per
save, with a download between every one.

## 1. `FIXTURE SETUP` — targets `115.f5`, `115.f9`, `120.f4/f5/f6` (~1.2 %)

`115.f5` reads **65535 on all 1433 fixture rows** of the corpus — a sentinel
nothing has ever moved — and `f9` is a contiguous ascending run whose start is
not always 0 (COV-15). Both are per-fixture, and the firmware has a per-fixture
screen this project has never opened: mode 17, `fixture_setup`.

**Do:** open the fixture setup for **one** fixture, change **one** setting
(whatever it offers — invert pan, invert tilt, a dimmer curve, a swap), save.

| Prediction | p |
|---|---|
| record 115 changes, and only for that fixture's row | 0.8 |
| `f5` leaves 65535 on that row alone → the sentinel is a per-fixture settings word | 0.45 |
| nothing in 115 moves and the setting lives elsewhere (or is not persisted) | 0.35 |
| `120` changes too, on that fixture's block | 0.3 |

## 2. A macro with **one** feature — targets `160.f7` (0.42 %)

The macro measured in COV-19 has one fixture and **two** features
(`01 Pan` = 200, `03 uPan` = 0), giving `f1 = [17]`, `f8 = [200, 0]`,
`f7 = [129, 127, 127, 127, 127, 3]`. `len(f7) = 2 × len(f1) + 4` on 489 of 490
macros, so its length follows the **fixture** count — but nothing says whether
its *content* follows fixtures or features.

**Do:** create a second Live Edit macro on a free button, **same single
fixture**, and set **one** feature only — `02 Tilt` to **60**. Save.

| Prediction | p |
|---|---|
| `f1` has one element with **one** bit set, `f8 = [60]` | 0.85 |
| `f7` still has **6** elements — its length follows fixtures, not features | 0.8 |
| `f7`'s content **differs** from COV-19's → it encodes which features, and the field falls | 0.5 |
| `f7` is byte-identical to COV-19's → it encodes the fixture, and the feature is only in `f1` | 0.5 |

Either way this one resolves: the two outcomes are exclusive and both are
informative.

## 3. `LIVE EDIT` re-enabled — targets `161`'s 20-bit mask (attribution only)

Record 161's item 1 carries a little-endian 20-bit mask at its first three
values, `0x0FFFFF` or `0` (COV-21). It went **all-set → zero** on the FX6-02
save, whose stated variable included `LIVE EDIT` being off. The project on the
controller currently reads `0`.

**Do:** turn `LIVE EDIT` back on for one preset — capture it with `SHIFT` + tap
so the file records it — and save. **Nothing else.**

| Prediction | p |
|---|---|
| the mask returns to `0x0FFFFF`, i.e. `[255, 255, 15]` | 0.5 |
| it does not move → the FX6-02 coincidence was a coincidence | 0.4 |
| it takes some intermediate value → it is a real 20-slot selection and each bit can be chased | 0.1 |

This one **cannot raise coverage**: 182 of each item's 188 values have never
moved, so 161 stays unread whatever happens. It closes a question, not a gap.

## 4. One DMX address moved — targets `120.f4/f5/f6` (0.97 %)

EXP-07 showed that moving a fixture's address touches exactly three records:
`115.f2`, that fixture's eight `106` entries, and `120`. COV-17 killed three
readings of `f4`/`f5`/`f6` and left only a shape.

**Do:** change **one** fixture's DMX address by a few channels, save. Then put
it back and save again — the return is the control, and EXP-07's own return
left no trace where a naive model expected one.

| Prediction | p |
|---|---|
| `115`, `106` and `120` all change; nothing else does | 0.85 |
| `f6` follows the fixture's new position in the address-sorted order → it is an index into the flattened channel table | 0.4 |
| `f4`/`f5` do not move → they belong to the profile, not to the patch | 0.6 |
| the return restores the earlier bytes exactly | 0.5 |

## Order, and why

1 first: it is the only one aiming at a field **no experiment has ever
touched**, and its screen has never been opened in this project. 2 next: it is
the cheapest and it resolves either way. 3 and 4 after, in any order.

**One change per save. A download between every one.** If two of these end up
in one save, none of them measures anything — the whole value here is that a
single record moving is attributable.
