# COV-44 — reproducing the damage on clean data (BEFORE measuring)

COV-42 established the negative that makes this worth doing: on a project the
panel created from scratch, detaching a fixture and saving writes **exactly**
what it should — 20/20 identities, 0 anomalies. So the 150/151 layer is not
permanently broken, and whatever wrecked the experiment project belongs to a
**patch edit**, which is what the COV-23/24 session was: "the patch was
reorganised, fixtures were added".

That session lost five of six detached fixtures, left six surplus entries in
record 120, and mis-sliced `116.channel_names`. This sheet asks whether any of
that reproduces, one operation at a time.

## Method — a ladder, one change per save

Each rung: **one** change on the panel, **one** save, download, check. Stop at
the first rung that reports an anomaly — that names the trigger.

```
python3 tools/wolfmix.py project <uuid> corpus/experiments/COV-44/<rung>.wpj
python3 tools/wpj_identities.py corpus/experiments/COV-44/<rung>.wpj
```

| rung | change | why it is in this order |
|---|---|---|
| **1** | **add a 5th `Lyre ZQ02244`** to group A, DMX **65** on the panel | the session's own words were "fixtures were added", and it is the least invasive edit that touches the patch |
| 2 | change one fixture's DMX address | COV-29 measured this clean on the other project — but never on one carrying a record-151 entry |
| 3 | reorder the fixtures | COV-26 showed record 116 reordering makes the 125 mask accumulate; the known-dirty operation |
| 4 | **delete** a fixture | the prime suspect: `151.f1` **is** a fixture index, and deleting shifts every index above it |

> **Do not touch the `PAN OFFSET` / `TILT OFFSET` encoders** — they crash this
> controller (COV-39), and a crash during a save is how a project gets
> truncated. Rung 1 needs the `FIXTURE SETUP` screen and nothing else.

## The state rung 1 starts from

`after-offset-40.wpj`, 20/20 identities, 0 anomalies.

| record | items | `f1` | note |
|---|---|---|---|
| 105 | 4 | 4 | `offset_106` 0 / 10 / 20 / 30, `entry_count_106` 10 each |
| 106 | 40 | 40 | |
| 110 | 16 | 16 | one profile |
| 111 | 69 | 69 | |
| 115 | 4 | 4 | addresses **0**, 16, 32, 48; `f9` absent, 1, 2, 3; `display_order` `00010203`; **no `f6`/`f7`** |
| 116 | 1 | 1 | 16 channels, `offset_110` 0, carries `channel_names` |
| 120 | 64 | 64 | 4 × 16 |
| 150 | 20 | 20 | `Floor` has `entry_count_151` = 1, no offset |
| 151 | 1 | 1 | `fixture` **1**, `pan_offset` **45874** |

## Predictions for rung 1

| # | Prediction | p |
|---|---|---|
| P1 | 115 gains one row: `dmx_address` **64**, `f9` **4**, and `display_order` becomes `0001020304` | 0.8 |
| P2 | 105 gains one entry: `offset_106` **40**, `fixture` **4**, `entry_count_106` **10** | 0.75 |
| P3 | 106 goes to **50** entries and its `f1` follows | 0.75 |
| P4 | 110 and 111 are **untouched** — the profile is already there and nothing about it changes | 0.8 |
| P5 | 116 is untouched, `channel_names` included. Mis-slicing needs a second profile, so this rung **cannot** test COV-30's bug; rung 1 is not the one that would show it | 0.85 |
| P6 | 120 goes to **80** entries **and `f1` follows to 80** | 0.6 |
| P7 | **151 is unchanged** — `fixture` 1, `pan_offset` 45874 — and `Floor` still claims 1. The new fixture appends *after* index 1, so no index moves | 0.7 |
| P8 | `wpj_identities`: **0 anomalies** | 0.6 |
| P9 | `115.f6`/`f7` **come back**. COV-42 watched a save delete them when the patch was untouched; this save touches the patch, so their return would read them as written when the fixture list is edited | 0.45 |
| R1 | rival: **the 151 entry is dropped**. Then the simplest possible patch edit destroys a detached fixture, and that alone explains the format-lab's 6 → 1 | 0.2 |
| R2 | rival: 120 grows to 80 and **`f1` stays 64**. COV-32's anomaly reproduced by adding one fixture, which would name the trigger on the first rung | 0.25 |

## Collision check

Every prediction names a different record, so a single diff reads them all at
once without any of them competing. The two rivals are each the **negation** of
one prediction on one number — R1 against P7 on whether record 151 still has
its entry, R2 against P6 on whether `120.f1` equals the entry count — so no
observation can satisfy a prediction and its rival. P9 is a yes/no on a field
that is currently **absent from every row**, which is the cleanest starting
state it could have.

If rung 1 comes back at 0 anomalies with P7 intact, the trigger is further up
the ladder and rung 4 is where I would bet: `151.f1` is an index, and deleting
a fixture is the only operation on the list that moves every index above it.
