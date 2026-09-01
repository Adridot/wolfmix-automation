# COV-44 rung 4 — deleting a fixture (BEFORE looking at the capture)

**Honest note on the method.** The operator ran this rung before the sheet was
committed. The prediction below was stated to them in writing *before* they
measured — `151.f1` must be rewritten from 1 to 0 — but it was not in the
repository, which is weaker and is recorded as such. What is preserved: this
file is written and committed **before the capture is opened**.

## The change

The fixture at index **0** — the panel's DMX **1** — deleted. Not the one
carrying the offset. That is the point: `151.f1` is **1**, and removing index 0
slides every index above it down by one, so a correct writer must **rewrite the
reference**.

## The state it starts from — `rung1-add.wpj`, 0 anomalies

| record | items | note |
|---|---|---|
| 105 | 5 | `offset_106` 0 / 10 / 20 / 30 / 40 |
| 106 | 50 | |
| 115 | 5 | addresses **0**, 16, 32, 48, 64; `f9` absent, 1, 2, 3, 4; order `0001020304` |
| 120 | 80 | `f1` 80 |
| 150 | 20 | `Floor` claims 1 entry at offset 0 |
| 151 | 1 | **`fixture` 1**, `pan_offset` **45874** |
| 161 | 3 | item 0 mask **31** = all-ones over five fixtures |

## Predictions

| # | Prediction | p |
|---|---|---|
| P1 | 115 → **4** rows at addresses 16, 32, 48, 64, `display_order` `00010203` | 0.8 |
| P2 | 105 → 4 entries, `offset_106` 0 / 10 / 20 / 30 | 0.8 |
| P3 | 106 → **40** entries, 120 → **64**, both with `f1` following | 0.7 |
| P4 | 110, 111 and 116 untouched — one profile, still used | 0.8 |
| **P5** | **`151.f1` is rewritten from 1 to 0**, the entry otherwise byte-identical at `pan_offset` 45874, and `Floor` still claims 1 | 0.5 |
| P6 | `161` item 0's mask goes **31 → 15**, all-ones over four fixtures — the reading COV-45 just made, tested on a *shrink* where it was measured on a growth | 0.6 |
| P7 | `f9` keeps **1, 2, 3, 4** on the survivors. COV-15 refuted the "sequential position index" reading, so a stable per-fixture identifier should not renumber | 0.5 |
| P8 | `wpj_identities`: **0 anomalies** | 0.45 |
| **R1** | rival, and the one that matters: **`151.f1` stays 1**. The offset then applies to the *wrong head*, silently — no anomaly, no counter mismatch, nothing any check would catch, and exactly the shape of a bug an operator only finds on stage | 0.3 |
| R2 | rival: the 151 entry is **dropped**. If `Floor` still claims 1 over an empty record, COV-32's anomaly is reproduced on clean data and the trigger is named | 0.2 |
| R3 | rival: `f9` renumbers to absent, 1, 2, 3 — then it *is* positional and COV-15's refutation needs revisiting | 0.25 |

## Collision check

P5, R1 and R2 are three mutually exclusive states of one number: `151.f1`
rewritten, unchanged, or gone. P7 and R3 are the same for `f9`. P6 is a single
integer with two candidate values, 15 and 31, which no other field on this
project carries. Nothing here can be satisfied two ways.

**R1 is the dangerous outcome and the reason to run this rung at all**: it
passes every structural check in this repository. `wpj_identities` would report
0 anomalies on a project whose stored offset points at the wrong fixture,
because the index is still in range. If R1 holds, the anomaly list needs a
fourth entry that this experiment will have to define — and there is no
file-internal way to define it, which is itself the finding.
