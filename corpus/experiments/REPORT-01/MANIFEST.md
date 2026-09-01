# REPORT-01 — the minimal pair for `docs/report-record-120.md`

Two project files, one save apart, **one change between them**: a fifth fixture
added to **group B**. The file before is structurally clean; the file after is
not.

The `.wpj` themselves are not in this repository — no project file ever is.
They sit beside this manifest on the machine that measured them, and the
hashes below identify them.

| | before | after |
|---|---|---|
| file | `before.wpj` | `after.wpj` |
| sha256 | `4064e36f859a4718192af833855e5191a7f793fb48b255a27a44a3857cb77b22` | `4db2b8a384922837c2552c49cfe551a80d21251f9150af8cae6df86a9ad348c5` |
| bytes | 9846 | 10165 |
| version counter | 5 | 6 |
| fixtures | 4, all in group A | 5, the new one in **group B** |
| DMX (as the panel shows) | 17, 33, 49, 65 | 17, 33, 49, 65, **81** |
| per-channel table | **64** entries = 4 × 16 ✓ | **79** entries, 5 × 16 = **80** required ✗ |
| internal checks | **0 anomalies** | **2 anomalies** |

## The change

On the controller, no PC connected: **add one fixture of the same 16-channel
moving-head profile at DMX 81 and assign it to group B. Save.** Nothing else
was touched.

## Records that differ

| record | bytes before | bytes after |
|---|---|---|
| 105 | 50 | 65 |
| 106 | 502 | 627 |
| 115 | 64 | 59 |
| 120 | 323 | 391 |
| 125 | 109 | 117 |
| 145 | 442 | 550 |
| 161 | 599 | 599 |

105, 106 and 115 grow because the patch grew — those are expected. **120 is the
defect**: it gained **15** entries where the new fixture requires 16.
125 and 145 gain group B's mask and its palettes; 161 moves as it does on every
save.

## What to look at

1. **Count the per-channel table.** 64 → 79, where 5 × 16 = 80 is required.
2. **The loss is at the head, not at the end.** Each entry of that table carries
   an absolute DMX channel number inside its own fixture's span. In `before` the
   first entry belongs to the fixture at DMX 17; in `after` the table starts one
   entry late and every fixture is one channel out of step.

## One thing to be aware of before you ask

`before.wpj` carries a **non-identity fixture display order** — the list reads
33, 49, 65, 17 — because the save before it moved a fixture in the list. That
is not the variable: the same defect was reproduced afterwards on a project
whose display order *was* the identity, and an add to group A on that same
project was clean. See the main report's measurement table.
