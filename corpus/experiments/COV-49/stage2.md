# COV-49 stage 2 — which of the two variables (BEFORE opening the capture)

**Honest note on the method, and it is the weak point of this sheet.** The
operator ran the change before this file existed. The prediction is the one
stated to them in the session immediately before they acted — *if the alignment
breaks again the second group is the trigger, if it does not the non-identity
display order was* — and this file is written and committed **before the
capture is opened**, which is what is left of the discipline. It is weaker than
COV-44's rungs and it is recorded as weaker.

## What is being separated

Stage 0 broke record 120 on a save that differed from COV-44's clean rung 1 in
**two** ways: the new fixture went to **group B** instead of A, and the
project's `display_order` was the **non-identity** one rung 3 left behind.
Stage 1 restored the identity order. So the state now has one variable left.

| | rung 1 (clean) | stage 0 (broke) | **stage 2** |
|---|---|---|---|
| new fixture's group | A | **B** | **B** |
| `display_order` | identity | **non-identity** | **identity** |

## The state it starts from — `stage1-order.wpj`

Five `Lyre ZQ02244` at addresses **16, 32, 48, 64** (group A) and **80**
(group B); `f9` **1, 2, 3, 4, 0**; `f6`/`f7` **231**/**4** on every row;
`display_order` **`0001020304`**, the identity. Record 120 holds **80** entries
with `f1` 80 — the right count over a table still **misaligned at the head**
(COV-50), which is the file's one standing anomaly. Record 161's item-0 mask is
**31**. Record 151 holds one entry, `fixture` absent = 0, `pan_offset` 45874.

## The change

A sixth `Lyre ZQ02244` at panel DMX **97**, in **group B**.

## The discriminator

The file is **already** misaligned, so "does it break" is the wrong question —
adding a fixture cannot repair a missing head entry. The question is whether it
breaks **again**, and the anomaly count answers it:

| # | Outcome | reading | p |
|---|---|---|---|
| **A** | **2 anomalies** — the count short again *and* the alignment | the **second group** is the trigger. It broke on an identity order, so the display order was never the variable | 0.45 |
| **B** | **1 anomaly** — the standing misalignment, count correct at 96 | the group is **not** the trigger; the non-identity display order was, and the existing damage simply persists | 0.4 |
| **C** | **0 anomalies** | the add repaired the head. Would refute COV-50's reading of what stage 1 did, and is the one I would least expect | 0.05 |
| **D** | something else — a third anomaly, or 151 disturbed | neither variable alone; the sheet is wrong about the shape of the defect | 0.1 |

## The rest

| # | Prediction | p |
|---|---|---|
| P1 | 115 → 6 rows, the new one at address **96** with `f4` = 1 (group B) and `f9` = **5**, the lowest free number after 0–4 (COV-49 stage 0 showed `f9` reuses freed slots) | 0.55 |
| P2 | `display_order` → `000102030405` | 0.8 |
| P3 | record 161's item-0 mask → **63**, all-ones over six fixtures (COV-45, a fourth test) | 0.7 |
| P4 | record 151 and `Floor` untouched: one entry, `fixture` absent, `pan_offset` 45874, count 1 | 0.85 |
| P5 | record 125's group-B slot unchanged — `profile_mask` already 1, one profile | 0.85 |
| P6 | `115.f6`/`f7` take yet another value. Five operations so far have given 177/124 (create), absent (plain save), absent (add to A), 231/20 (delete), 3/20 then 231/4 (reorder) | 0.5 |

## Collision check

A, B, C and D are four values of one integer — the anomaly count and which
anomalies — and no capture satisfies two. P1–P6 name different records and none
of them decides between A and B, which is why they are listed apart. P3 is the
only one that could confirm a previous reading rather than test this one, and
it is marked as such.
