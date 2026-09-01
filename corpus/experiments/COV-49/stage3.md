# COV-49 stage 3 — group A or more than one group (BEFORE measuring)

Stage 2 settled that the display order is not the variable: a sixth head added
to **group B** on an **identity** order dropped an entry from record 120, as
stage 0 had. Adding to **group A** was clean at COV-44 rung 1 — but that was on
a project with **one** group. Two readings still fit:

- **G** — the trigger is *adding to a group other than the first*;
- **M** — the trigger is *adding to a project that has more than one group*.

One save separates them.

## Do

Add a seventh `Lyre ZQ02244` at panel DMX **113** — file address 112, the next
free 16-channel block after the head at 97 — and put it in **group A**. One
addition, one save.

```
wolfmix.py project <uuid> corpus/experiments/COV-49/stage3-groupA.wpj
wpj_identities.py corpus/experiments/COV-49/stage3-groupA.wpj
```

> No offset encoder is touched (COV-39).

## The state it starts from — `stage2-groupB2.wpj`

Six heads: **17, 33, 49, 65** in group A and **81, 97** in group B (panel DMX);
`f9` **1, 2, 3, 4, 0, 5**; `display_order` `000102030405`, the identity. Record
120 holds **95** entries where the patch justifies **96** — one short — over a
table already misaligned at the head. Two anomalies stand.

## The discriminator is a count, not the anomaly total

Both outcomes leave two anomalies standing, because the file is already one
short and already misaligned. **The anomaly count cannot separate them.** What
separates them is the exact size of record 120:

| # | `120` entries | reading | p |
|---|---|---|---|
| **G** | **111** — 95 + 16, the deficit unchanged at one | the add was clean, so the trigger is **adding to a group other than the first**. Group A stays safe however many groups exist | 0.45 |
| **M** | **110** — 95 + 15, the deficit now two | it dropped one again, so the trigger is **more than one group in the project**, and every fixture added to this project from now on loses an entry | 0.45 |
| R | **112** — the deficit repaired | the add rebuilt the record instead of appending. Would refute COV-50's reading of how a save repairs a count, and is the least expected | 0.1 |

`_anomalie_120_patch` will fire under all three except R, saying `111 against
112` or `110 against 112`. **Read the number in the message, not the count of
anomalies.**

## The rest

| # | Prediction | p |
|---|---|---|
| P1 | 115 → 7 rows, the new one at file address **112** with no `f4` (group A) and `f9` = **6**, the lowest free after 0-5 | 0.6 |
| P2 | `display_order` → `00010203040506` | 0.8 |
| P3 | record 161's item-0 mask **63 → 127**, all-ones over seven fixtures — COV-45's fifth test | 0.7 |
| P4 | record 151 and `Floor` untouched: one entry, `fixture` absent, `pan_offset` 45874, count 1 | 0.85 |
| P5 | record 125's group-A slot unchanged: `profile_mask` already 1, one profile | 0.8 |
| P6 | `115.f6`/`f7` take a seventh distinct form. So far: 177/124 on creation, absent after a plain save, absent after an add to group A, 231/20 after a delete, 3/20 then 231/4 after reorders, 18/absent after the last add | 0.5 |

## Collision check

G, M and R are three values of one integer — 111, 110, 112 — and no capture
gives two. P1–P6 name other records and none of them decides between G and M.

**Either answer completes the report.** G means a Wolfmix user loses a channel
entry every time they patch into a secondary group; M means they lose one on
every patch once a second group exists. Both are reproducible from a project
the device wrote from nothing, in under five minutes, and the per-file check
names the damage.
