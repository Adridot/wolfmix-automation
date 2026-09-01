# COV-28 — what `160.f7` says about the fixture (BEFORE measuring)

COV-27 established that `f7` encodes the **targeted fixture** and not the
features: two macros on one fixture, different features, byte-identical `f7` =
`[129, 127, 127, 127, 127, 3]`. One fixture is not a mapping, so nothing was
named.

**Do:** a third macro, on the free button the panel calls `Live Edit 7`,
targeting **`002 : Lyre ZQ02244`** — the *second* moving head, at DMX 17, same
profile as the first — with the same single feature `02 Tilt` = 60. Save.

Same profile, same feature, same value: the **only** variable is which fixture.

| # | Prediction | p |
|---|---|---|
| 1 | one record changes, 160 alone, one macro appended on `button` = 6 | 0.9 |
| 2 | `values` = `[60, 0]` and `value_masks` = `[68]`, both identical to COV-27 — the feature side is settled and must not move | 0.85 |
| 3 | `f7` **differs** from COV-27's, confirming the fixture reading in the only way one fixture could not | 0.85 |
| 4 | it differs in a way that names it: the fixture's **index** in record 115, its **DMX address**, or its `f9` | 0.5 |
| 5 | rival: `f7` is identical → it does not encode the fixture either, and COV-27's reading was a coincidence of two macros sharing more than the fixture | 0.1 |

The reference values, so the comparison cannot drift — read off the controller
before the measurement, and **one of them was written wrong here first**:
fixture `001` is item **14** of record 115 at DMX **1** with `f9` = **20**;
fixture `002` is item **15** at DMX **17** with `f9` **absent** (0), not 21 as
this sheet claimed until it was checked. A difference of **1** in the index,
**16** in the address and **20** in `f9` — three candidates a single byte of
`f7` can tell apart, and the corrected `f9` separates them further rather than
less.
