# Registre du format .wpj — hypothèses et preuves

Statuts : `observed` (vu dans les octets) → `hypothesized` (interprétation
proposée) → `correlated` (cohérent sur ≥2 fichiers indépendants) →
`validated` (confirmé par expérience différentielle) → `device-confirmed`
(accepté par le W1). Jamais de valeur inventée ; ambiguïté = candidats listés.

Corpus de preuve : `corpus/SHA256SUMS`, relevé du 2026-08-25, WTOOLS 1.6.3.

## Trois variantes de conteneur observées localement

### Variante C — protobuf nu (1 fichier : f4a5d15f « Mariage Hermine »)
- **[correlated]** Fichier entier = wire format protobuf valide depuis
  l'offset 0 (parcours complet sans erreur, 275 516 octets).
- **[observed]** Champ 1 varint = **6**.

### Variante B — SHA-1 + protobuf (5 fichiers, les projets WTOOLS courants)
- **[correlated]** Octets 0–19 = **SHA-1 de bytes[20:EOF]** — vérifié
  exact sur les 5 fichiers B et les 3 fichiers A (8/9 du corpus).
  Concorde avec wpj-toolkit (« digest SHA-1, octets 20→EOF »).
- **[correlated]** Corps protobuf valide à partir de l'**offset 20**.
- **[observed]** Champ 1 varint = **7** (vs 6 en variante C).
- **[hypothesized]** Champ 1 = version du format de fichier ; le passage
  6→7 a introduit le digest SHA-1. Candidat alternatif : champ sans lien,
  coïncidence. À trancher par un fichier v6 avec digest ou v7 sans.

### Variante A — SHA-1 + conteneur TLV (dumps device + imports)

Statut global : conteneur + SHA-1 + record 101 **device-confirmed**
(ACC-01, 2026-08-25 : fichier généré accepté par WTOOLS 1.6.3 et W1
fw 2.0.18, stocké octet-identique). Octets 20–35 : PAS une clé
d'identité à l'import (nouveau projet créé sans les modifier).
- **[correlated]** Octets 0–19 = SHA-1 de bytes[20:EOF] (idem B).
- **[observed]** Octets 20–63 : zone d'en-tête contenant notamment
  `cc 21 80 71` (répété, = moitié de l'UUID du nom de fichier) —
  **[hypothesized]** numéro de série W1.
- **[correlated]** Offset **0x40** : `uint32 LE longueur` + `uint16 LE type`,
  type racine **100**, longueur = taille fichier − 0x46 (vérifié 3/3).
  Enregistrements imbriqués : même en-tête. Type **101** observé avec
  payload protobuf `0a 05 "rig-a"` = nom du projet (concorde
  wpj-toolkit : 101 = project metadata, nom UTF-8).
- Concordance directe avec le conteneur documenté par wpj-toolkit
  (types connus 101 / 135 / 165). **[hypothesized]** format « device /
  MK2-era », produit par la synchro WLINK.
- **[correlated]** Inventaire des types TLV, identique sur 5/5 fichiers A
  à une exception près : le type 160 (macros) est optionnel — absent de
  cc21/cd21/47c10d40 (40 enregistrements), présent ailleurs (41) : 101, 102 (16 o fixe), 105, 106, 110, 111, 115,
  116, 120, 125, 130, 135, 140 ×8, 145 ×8, 150 ×8, 151, 155, 160, 161,
  165 (le plus gros, ~30 Ko — conteneur presets selon wpj-toolkit).
  ×8 : candidat groupes A–H. Sémantique des 17 types non documentés par
  wpj-toolkit : inconnue.
- **[observed]** En-tête : octets 20–35 = UUID du projet (= nom de
  fichier wlinkData) ; octet 0x28 diffère entre deux révisions du même
  projet (0x07 → 0x0f) — candidat compteur de révision/sauvegarde.
- Paire différentielle disponible : `f2737ec3….wpj` et
  `rig-c-bug.wpj` = même UUID, deux révisions (16 records diffèrent,
  type 101/nom identique). Trop de changements simultanés pour valider
  des champs — utile comme corpus, pas comme expérience minimale.

## Corps protobuf (variantes B et C) — structure top-level

Relevé sur f4a5d15f (C) ; à corréler sur les fichiers B (offset 20).

| Champ | Type wire | Occurrences | Interprétation | Statut |
|---|---|---|---|---|
| 1 | varint | 1 | version du format (6 ou 7) | hypothesized |
| 2 | len | 1 | **nom du projet** UTF-8 (« Mariage Hermine », « 2 Lyres ») | correlated |
| 3 | len ×100 | 100 | **presets** (sous-msg : champ1=nom, champ2=varint 1000, champ4=blob 135 o) | correlated (le manuel donne **10 pages × 20**, soit 200 slots) |
| 15 | len ×2048 | 2048 | inconnu (gros volume — steps ? séquences ?) | observed |
| 5 | len ×80 | 80 | inconnu | observed |
| 17 | len ×87, 6 ×48, 7/9/30/31 ×40, 40 ×32… | — | inconnus | observed |

Détail preset (sous-message du champ 3) : champ 1 = nom UTF-8, champ 2 =
varint 1000 (constant sur les 8 premiers presets — candidat : BPM ×10 ?
valeur par défaut ?), champ 4 = 135 octets à faible densité. Statut : observed.

## Conteneurs .wm / .wmx

- **[correlated]** Format texte ASCII : `VVV.<32 hex>.<payload hex>.<64 hex>`
  (4 segments séparés par des points). Versions vues : 001, 002, 003.
- **[observed]** Payload décodé : entropie ≈ 7,94 bits/octet → chiffré ou
  compressé (zlib/deflate exclus aux offsets 0–3).
- **[observed]** Segment 2 (32 hex, taille MD5) ≠ MD5 du payload ni de son
  hex. Segment 4 (64 hex, taille SHA-256) ≠ SHA-256 du payload ni de son
  hex. Candidats : HMAC, hash du clair, clé dérivée. Non prioritaire :
  ces fichiers (profils fixtures, marques) seront traités après le .wpj.

## Type 102 — flash FX settings (16 bytes, fixed size)

*(Section written in English per the repository rule; the French sections above
predate it.)*

Wire content, identical layout in all readable corpus files:

```
22 06 <6 bytes>   field 4, length-delimited, always 6 bytes
28 64             field 5  = 100
30 64             field 6  = 100
48 50             field 9  = 80   (75 or 72 in other files)
58 64             field 11 = 100
```
Some files also carry `field 2 = 1`, `field 3 = 2`, `field 7 = 2`.

### Field 4 = release mode of the six flash FX — **[device-confirmed]**

One byte per flash key, in the order guide 10 lists them:

| Index | Key |
|---|---|
| 0 | `WOLF` (chevrons) |
| 1 | `STROBE` |
| 2 | `BLINDER` |
| 3 | `SPEED` |
| 4 | `BLACKOUT` |
| 5 | `SMOKE` |

Values: **0 = FLASH**, **1 = TOGGLE**. Guide 10 documents five release modes
(FLASH, TOGGLE, 1 s, 5 s, 10 s timer), and `corpus/projects/rig-c.wpj`
carries a **4** at index 5, so the domain is **[hypothesized]** 0–4 with 2/3/4
the three timers.

**Experiment FX-01, 2026-08-25, W1 (serial withheld), fw 2.0.18.**
Request: `GET_PROJECT` on `73d06df4-9b5d-5cd1-9645-51ba125f71a5`
(`WMX EXP format-lab`, the dedicated experiment project) before and after the
operator moved **STROBE only** from FLASH to TOGGLE with the fourth encoder
and saved on the controller.

- Before: `corpus/experiments/FX-01/before.wpj`, size 43337, version
  1787654382431, sha256 `171ae1c5…`, field 4 = `01 00 00 00 00 01`.
- After: `corpus/experiments/FX-01/after-strobe-toggle.wpj`, size 43295,
  version 1787654382432, field 4 = `01 01 00 00 00 01`.
- **Exactly one byte of field 4 changed, at index 1 = STROBE, 00 → 01.**

Independent cross-check: the operator reported *before the experiment* that
the `WOLF` key was set to TOGGLE, and index 0 was already `01` in the baseline.
Two facts, two indices, one consistent encoding.

**Experiment FX-02, same session, one save.** Prediction published before
measuring: `01 00 01 02 03 04`. The operator set STROBE back to FLASH, BLINDER
to TOGGLE, SPEED to the 1 s timer, BLACKOUT to 5 s, SMOKE to 10 s, left WOLF
on TOGGLE, and saved once.

- Result: `01 00 01 02 03 04`. **Exact match, five bytes at once.**

The whole field is therefore settled:

| Value | Release mode |
|---|---|
| 0 | `FLASH` |
| 1 | `TOGGLE` |
| 2 | `1 s` timer |
| 3 | `5 s` timer |
| 4 | `10 s` timer |

Independent corroboration from the operator: on each flash screen the value can
also be set with the right-hand pad column, top to bottom FLASH → 10 s, i.e.
the UI exposes the enumeration in its natural order.

Certainty: **device-confirmed**, all six indices and all five values.
Restoring is symmetric: set the mode back and save.

### Other diffs produced by a controller-side save — **[observed]**

Saving on the W1 also rewrote two things unrelated to the experiment:

- **Type 115** shrank 329 → 287 bytes. Its 20 repeated `field 5` items each
  lost `field 6` and `field 7` and gained a sequential `field 9` (1…0x13).
  The firmware re-serialises this record into its own canonical form; the
  incoming file had been produced by the WTOOLS-era pipeline.
- Two prefix counters incremented by one: absolute offsets **40** (`5f`→`60`)
  and **50** (`0a`→`0b`).

**Consequence for the method**: a controller-side save is *not* byte-preserving,
so a round-trip through the W1 cannot be verified by file hash. Differential
experiments must compare record by record and expect this canonicalisation
noise. **[hypothesized]** re-saving a project twice in a row would isolate the
noise exactly; worth doing once.

## Type 102 `field 9` = STROBE speed — **[correlated]**

**Experiment FX-03.** The operator set the STROBE screen's first encoder — the
speed, per guide 10 — to **0 %** and saved. `field 9` went **80 → 1**, and
`field 4`, `field 5`, `field 6` and `field 11` did not move.

Corpus values for `field 9`: 80 (`f2737ec3`), 75 (`cc21`, `rig-c`), 72
(`cd21`). A per-project percentage-shaped number, consistent with a speed.

**[hypothesized]** the stored range is 1–100 rather than 0–100, since 0 % on
screen wrote 1. One more point (set the encoder to 100 %) would settle both the
range and whether the mapping is affine.

**Confounded in the same save**: the operator also visited the STATIC POSITION,
LIVE EDIT macro and Settings → Project screens while answering questions, and
two other records moved (type 115 `field 6` back to absent, type 155 first item
grew by one byte and its `field 3` went 4 → 16). Those changes cannot be
attributed. Single-variable saves only from now on.

## Type 150 ×8 — the static POSITION palettes, one per group — **[device-confirmed]**

Found by searching the corpus for the position names the operator photographed
on the SEQUENCER screen. Record 150 appears **eight times**, and:

- the **first** copy contains `<group-A name>`, the seven others contain `Floor`;
- `<group-A name>` is exactly what the operator's **group A** shows where every other
  group shows the factory default `Floor`.

That settles it: **the ×8 record families are the eight groups A–H**, indexed by
top-level `field 2` = 0…7 (absent for group A). An earlier survey concluded the
opposite; it was wrong.

### Structure

```
field 1 = 20                     slot count — matches "20 slots per group"
field 2 = 0…7                    group index, absent for A
field 5 × 20                     one per palette slot
  field 3   pan     16-bit, 0…65535
  field 4   ?       32768 or 65535 in the whole corpus
  field 5   name    UTF-8, absent when the slot is empty
  field 6   ?       9 distinct values corpus-wide
  field 7   tilt    16-bit, 0…65535, absent = 0
  field 8   ?       32767 / 32768 / 36044
```

### Field meanings, read off the device's own edit screen — **[device-confirmed]**

SHIFT + a position pad opens an editor showing **PAN, TILT, FOCUS OFFSET and
FAN | CROSS** as percentages. The operator photographed three slots of group C,
and every displayed percentage matches a stored field exactly:

| Slot | screen FAN\|CROSS | `f3` | screen TILT | `f7` |
|---|---|---|---|---|
| Center | 60 % | 39321 = **60 %** | 50 % | 32768 = **50 %** |
| Center Point | 30 % | 19660 = **30 %** | 40 % | 26214 = **40 %** |
| Floor | 50 % | 32768 = **50 %** | 0 % | absent = **0 %** |

So **`field 3` = FAN | CROSS** and **`field 7` = TILT**, both 16-bit with
value = percent × 65535.

**An earlier entry here called `field 3` pan. That was wrong**, and the corpus
alone could not have caught it: group C's PAN reads 50 % on every named slot, so
pan and the neutral fields are indistinguishable in this rig. Only the device's
own screen separated them.

Resolved with one more screen. Group A's `<group-A name>` is the only slot in the
corpus where these fields disagree, and it reads **PAN 13, TILT 23, FOCUS
OFFSET 100, FAN|CROSS 50**:

| Field | Value | Unsigned | Screen |
|---|---|---|---|
| `f3` | 32768 | 50 % | FAN\|CROSS **50** |
| `f4` | 65535 | 100 % | FOCUS OFFSET **100** |
| `f6` | 8519 | **13 %** | PAN **13** |
| `f7` | 15073 | **23 %** | TILT **23** |
| `f8` | 32767 | 50 % | — |

### Slot layout — **[device-confirmed]**

```
field 3   FAN            unsigned, percent × 65535
field 4   FOCUS OFFSET   signed, 32768 = 0 %, 65535 = +100 %
field 5   name           UTF-8, absent when the slot is empty
field 6   PAN            unsigned, percent × 65535
field 7   TILT           unsigned, percent × 65535, absent = 0
field 8   CROSS          [hypothesized] — see below
```

`f4` is the one signed field: group C shows **FOCUS OFFSET 0 %** while holding
32768, and group A shows **100 %** holding 65535. Both fit `(v − 32768) / 32767`.
Every other field is a plain unsigned fraction of 65535, and each matched its
screen percentage to the unit across four slots and two groups.

**`f8` stays [hypothesized] = CROSS.** The editor labels one encoder
`FAN | CROSS` and shows a single percentage, which always tracked `f3`, so
CROSS is presumably the other half revealed by pushing that encoder. `f8` is
50 % in both photographed groups and takes only three values corpus-wide
(32767, 32768, 36044 = 55 %), consistent with a rarely-touched control. It
needs a slot where CROSS is actually set.

`field 1` = 4 appears on exactly one slot in the corpus, group A's first, and is
still unexplained.

### Why the DMX cross-check could not settle it

Recalling Floor then Ceiling moved **exactly four channels**, a 16-bit pair on
each of two fixtures, and left pan untouched — the right shape. But the values
ran 255 → 198 where the palette says 0 % → 100 %, both inverted and compressed
into 57 DMX steps.

The operator confirms **movement limits are set on these fixtures**. The Fixture
Limit screen remaps the palette's full range into a restricted band, so DMX
output is *not* a direct image of the stored value and cannot be used to read
these fields. It stays useful for locating which channel carries tilt, and it
makes the limits themselves a target worth decoding.

**Resolved on 2026-08-26 — the limits are `106.f5`/`f6`.** See the record 106
entry below. The two fixtures in that capture are group C's `Lyre ZQ02344`, and
their tilt entries hold `f5 = 255`, `f6 = 198` — the exact endpoints measured,
in the exact order measured, spanning exactly the 57 steps observed. The
anomaly was never an anomaly; it was an undecoded field, and it now reads:

```
DMX = f5 + percent × (f6 − f5)        0 % → 255,  100 % → 198
```

That makes the DMX cross-check usable again for every fixture whose limits are
known, and it upgrades the reading below from correlated to
**[device-confirmed]** — by a measurement taken before the field was decoded,
which is the strongest form this notebook has.

## Type 155 — the four FX sequences — **[device-confirmed]**

Earlier entries in this registry called this record a DMX patch map and then a
set of 128-byte arrays. Both were wrong. It is the **sequencer**, and it is now
decoded end to end.

### Structure

```
field 1 = 4                      number of sequences
field 5 × 4                      one per sequence
  field 1 = 8                    constant in every file
  field 2 ∈ {1, 2}               sequence kind
  field 3                        step count, 1…16
  field 4                        PACKED VARINTS — 128 values, not raw bytes
```

**The `field 4` blob is a packed varint array, not a byte array.** That is why
its length varies: 128 in most files, 133 when five values need two bytes.
Verified on **25/25** corpus and experiment files: every one holds exactly four
sequences of exactly 128 varints.

### Layout: step-major, 16 steps × 8 groups

Index = `step × 8 + group`, group 0 = A. Each value is a **position index into
that group's own palette**, and **255 means "no position"**.

The value domain is **0–19**: the static position palette holds 20 slots, shown
on the device as 5 entries × 4 pages. 255 is a sentinel outside that range.

### How it was confirmed

The operator photographed the SEQUENCER screen at every step from 1/16 to
16/16 while the file was in a known state. The decoded array predicts each
screen exactly:

| Step | Decoded row | Screen |
|---|---|---|
| 1 | A = 255, C = 255, rest 0 | no highlight on the A or C rows |
| 2 | all = 1 | "Center" highlighted on every group |
| 3 | all = 2 | "Center Point" |
| 4 | all = 3 | "Crowd" |
| 5 | A = 255, C = 255 | no highlight again |
| 6 | all = 0 | `<group-A name>` on A, "Floor" on C — the same index, each group's own name |

Reading the same array as 8 groups × 16 steps produces ragged nonsense, so the
step-major order is not a coin flip.

### Sequencer UI, for future experiments

- The pad matrix is 4 columns × 5 rows. **Row 1 activates the sequence per
  group**; rows 2–5 are the **16 steps**.
- **SHIFT + a step pad sets the step count** to that step: the operator did
  SHIFT + step 1 and `field 3` went 16 → 1.
- The screen lists 5 position names per group with a PAGE 1/4 indicator, and
  each group carries its own names for the same index.

**No hardware experiment was needed.** The photographs plus the bytes already
in hand were enough, which is worth remembering: describing the UI is often
cheaper than another write-and-save cycle.

## Type 102, remaining fields — **FX-04**

Four consecutive controller saves (strobe 100 %, speed 8×, group A excluded
from strobe, speed 2×). Only the final state could be downloaded, but the three
net changes landed in three distinct fields, so they stay separable. **Record
102 was the only record that changed**, which also refutes an earlier guess.

| Field | Before | After | Reading |
|---|---|---|---|
| 9 | 1 | **100** | STROBE speed. 0 % wrote 1, 100 % wrote 100 → stored range **1–100**. **[device-confirmed]** |
| 7 | absent (0) | **2** | SPEED multiplier, set to 2×. **[correlated]** |
| 8 | absent (0) | **1** | appeared exactly when group A was excluded from STROBE → **[hypothesized]** excluded-group bitmask, bit 0 = group A |

Unchanged throughout: `field 4` (release modes), `field 5` = 100, `field 6` =
100, `field 11` = 100. Those three remain unattributed; blinder fade-out,
smoke intensity and smoke fan are the documented candidates.

**`field 7` = SPEED multiplier — mapping [device-confirmed], meaning open.**
Four single-variable saves:

| Setting | `field 7` |
|---|---|
| normal | absent (0) |
| 0.5× | 1 |
| 2× | 2 |
| 4× | 4 |
| 8× | not yet measured |
| FREEZE | not yet measured |

FX-05 (2× → 4×) ruled out a plain list index, which would have written 3. FX-06
(4× → 0.5×) then ruled out the literal multiplier, which would have needed a
fraction: it wrote **1**. The measured values are **1, 2, 4, 8-shaped** — powers
of two. Two readings still fit all four points: the literal multiplier with 0.5
rounded up to 1, or a rank encoded as `1 << rank` (0.5× = rank 0, 2× = rank 1,
4× = rank 2). They coincide on 2 and 4 by accident.

Discriminator: **FREEZE**. The rank reading predicts 16 (the next bit) or a
sentinel; the literal reading predicts 0 or a sentinel distinct from "normal".
Measuring 8× as well would confirm whichever survives.

**Open on `field 8`**: one field appeared for one exclusion, but six effects can
each exclude groups. Either `field 8` is STROBE's own mask and the other five
live in their own fields, or it is shared. Excluding **A + C** from STROBE
(expect 5 if bit-per-group) then moving the exclusion to another effect
separates the two readings.

**Refuted**: type 115 `field 6` is **not** the SPEED multiplier. The multiplier
changed twice across these saves and record 115 did not move at all. What set
it to 4 during FX-02 is still unknown.

## Prefix offsets 40 and 50 — **[device-confirmed]**, earlier reading corrected

**Offset 40 is a little-endian `uint64`, and it is the project version** — the
same number `GET_PROJECT_LIST` reports. Verified exactly on five snapshots:

| File | `uint64` @ 40 | version from the project list |
|---|---|---|
| `before.wpj` | 1787654382431 | 1787654382431 |
| `after-strobe-toggle.wpj` | 1787654382432 | 1787654382432 |
| `after-fx02.wpj` | 1787654382433 | 1787654382433 |
| `after-speed-exclusion.wpj` | 1787654382438 | 1787654382438 |
| `after-speed-half.wpj` | 1787654382440 | — |

An earlier entry in this registry called offset 40 a one-byte save counter. That
was wrong: what was observed (`5f → 60 → 61 → 62 → 66`) is the **low byte** of
this `uint64`, which the firmware increments by one per save. The value looks
like an epoch-ms stamp at creation and is then bumped as a counter. **A writer
must treat offsets 40–47 as one 64-bit field**; touching only the low byte
corrupts the file at every wrap.

**Offset 50 is a `uint16` writer/schema version**: 10 in files produced by the
WTOOLS-era pipeline, **11** as soon as firmware 2.0.18 saves the project, and 11
in every save after that. This lines up exactly with the type 115
re-serialisation observed in FX-01, which is a schema change, not noise.

## Patch-side structure — six record types locked together — **[correlated]**

Five arithmetic identities hold **exactly on 19/19 variant-A files**, with
widely different values per project (Σ 22/50, 30/114, 37/153, 80/201), so they
are not trivially satisfied. Records store their repeated items under
**field 5**.

| Identity | Meaning |
|---|---|
| `Σ 116[p].f2 == count(110)` | 116 = profile catalogue, `f2` = channel count per profile |
| `116[p].f3 == Σ_{q<p} 116[q].f2` | `f3` = running offset into 110 |
| `Σ 105[e].f7 == count(106)` | 105 = DMX patch, 106 = one entry per patched channel |
| `max(105.f5) + 1 == count(115)` | 115 = fixture instances |
| `Σ 116[115[r].f3].f2 == count(120)` | 120 = flat per-fixture-channel table |

116 items also carry `f8` = profile name (e.g. a fixture model string), `f9` =
a 16-byte UUID and `f11` = a timestamp, which corroborates the catalogue
reading.

Full derivation, plus record 125 (9 category masks, reproduced bit-for-bit from
105/115/116) and the refutations, in `research/corpus-mining-2026-08-25.md`.

## FX-07 — one save, seven settings; type 102 nearly closed

Settings applied together then saved once: SPEED → FREEZE, BLINDER fade-out →
2 s, SMOKE intensity → 40, SMOKE fan → 70, STROBE excludes A (already set),
BLINDER excludes C, STATIC POSITION fade → 37. **Record 102 was the only record
that changed.**

| Field | Before | After | Reading |
|---|---|---|---|
| 5 | 100 | **70** | **SMOKE fan speed** — [device-confirmed], unique value |
| 6 | 100 | **40** | **SMOKE intensity** — [device-confirmed], unique value |
| 4[5] | 04 | **01** | SMOKE release mode back to TOGGLE, see below |
| 7 | 1 | **absent (0)** | **FREEZE writes 0**, indistinguishable from normal speed in this field alone |
| 2 | absent | **4** | new — see the collision below |
| 3 | absent | **4** | new — see the collision below |
| 8 | 1 | 1 | **unchanged**, so BLINDER's group exclusion is *not* stored here |
| 9, 11 | 100, 100 | 100, 100 | unchanged; `f9` = STROBE speed, `f11` still unattributed |

### The one thing this save could not separate — **[hypothesized]**

Two fields appeared at once, `f2 = 4` and `f3 = 4`, and two of the applied
settings both encode as 4:

- BLINDER fade-out set to **2 s**, which is index **4** of the list the operator
  read off the device (0, 0.2, 0.5, 1 s, 2 s);
- BLINDER excluding **group C**, which is bit 2 = **4** in a per-group mask.

The experiment design is at fault: the prediction promised distinct values but
the fade index and the group bit collided. Both assignments fit, and `f8`
staying at 1 shows exclusions are **per effect**, in separate fields.

Corpus support, either way: `cc21` and `cd21` carry `f2 = 1` and `f3 = 2`.

**Discriminator (one save)**: set BLINDER fade to **1 s** (index 3) and SPEED
to **2×**. Whichever of `f2`/`f3` becomes **3** is the fade-out; the other is
BLINDER's exclusion mask. `f7` should return to 2, and any field that changes
in step with leaving FREEZE belonged to FREEZE instead.

### Negative results

- **STATIC POSITION fade did not land in type 115**, which did not change by a
  single byte. Either the value never took, or that fade lives elsewhere.
- The three fields sitting at 100 were expected to be BLINDER fade, SMOKE
  intensity and SMOKE fan. Two matched (`f5`, `f6`) but the BLINDER fade turned
  out to be a **new** field, so **`f11 = 100` is still unattributed**.

### SMOKE release mode reverted on its own — **[observed]**

`f4[5]` went from 4 (10 s timer) back to 1 (TOGGLE) without the operator
choosing it. If confirmed, the 10 s timer is not persistent for SMOKE, which
would explain why no corpus file carries a 2 or 3 at that index while
`rig-c.wpj` does carry a 4.

## FX-08 — the collision resolved; type 102 is now readable end to end

One save: BLINDER fade-out 2 s → **1 s**, SPEED FREEZE → **2×**. Record 102 was
again the only record touched.

- `f2`: **4 → 3** — it tracked the fade-out, so **`f2` = BLINDER fade-out**,
  an index into the list the device offers (0, 0.2, 0.5, 1 s, 2 s).
- `f3`: **stayed 4** — so **`f3` = BLINDER's excluded-group mask**, group C =
  bit 2 = 4.
- `f7`: **absent → 2**, confirming both the SPEED multiplier mapping and that
  FREEZE stores 0.

### Type 102 as it now stands

| Field | Meaning | Encoding | Status |
|---|---|---|---|
| 2 | BLINDER fade-out | index into 0 / 0.2 / 0.5 / 1 s / 2 s | device-confirmed |
| 3 | BLINDER excluded groups | bitmask, bit 0 = A | device-confirmed |
| 4 | release mode ×6 | WOLF, STROBE, BLINDER, SPEED, BLACKOUT, SMOKE; 0=FLASH 1=TOGGLE 2=1s 3=5s 4=10s | device-confirmed |
| 5 | SMOKE fan speed | 0–100 | device-confirmed |
| 6 | SMOKE intensity | 0–100 | device-confirmed |
| 7 | SPEED multiplier | absent/0 = normal **and** FREEZE, 1 = 0.5×, 2 = 2×, 4 = 4×, 8 = 8× | device-confirmed |
| 8 | STROBE excluded groups | bitmask, bit 0 = A | device-confirmed |
| 9 | STROBE speed | 1–100 | device-confirmed |
| 11 | unknown, 100 in every file | — | unattributed |

Missing: the excluded-group masks for WOLF, SPEED, BLACKOUT and SMOKE. Since
BLINDER's and STROBE's live in separate fields, four more field numbers should
exist and appear only once a group is actually excluded.

**FREEZE is not distinguishable from normal speed inside record 102.** Either
it is not persisted, or it lives in another record.

## STATIC POSITION fade is not project data — **[correlated]**

The operator set the fade to **37 s**, saved, and not one byte moved anywhere in
the file; then to **46 s**, saved, and again only record 102 changed, for
unrelated reasons. The encoder offers 0–60 s in 1 s steps, so both values were
reachable and displayed.

This matches guide 8, which says the static screens' values are "saved
globally". **[hypothesized]** the fade is controller-global state, stored
outside the project — a candidate for `wmPersistent.wmx` rather than `.wpj`.

## FX-09 — the mask is a real bitmask, and two more negatives

One save: BLACKOUT excludes group **D**, STROBE excludes **A and B**, master
brightness set to **80 %**. Record 102 only.

- **`f8`: 1 → 3** — A + B together. The excluded-group field is genuinely a
  **bitmask**, bit 0 = A, bit 1 = B. **[device-confirmed]**
- **`f1` = 8 appeared** — BLACKOUT's own mask, group D = bit 3.
  **[device-confirmed]**

Field numbers do not follow the effect order: BLACKOUT = 1, BLINDER = 3,
STROBE = 8. Two effects have no mask yet, WOLF and SPEED, and the operator
reports **SMOKE has no exclusion control at all** on this MK1.

### Negatives

- **Master brightness is not project data.** Set to 80 %, saved, and `f11`
  stayed at 100 — nothing anywhere in the file moved except the two mask
  fields. Like the STATIC POSITION fade, it is controller-global or live-only
  state.
- **WOLF has no adjustable parameter** on the first encoder, so `f11` cannot be
  a WOLF setting.

`f11 = 100` is still unattributed, and is now the last unknown in record 102.
**[hypothesized]** a BLINDER level, since the guide describes BLINDER as
setting everything to full power and the value sits at exactly 100.

## Type 102 — final map, FX-10

`field 10` appeared at **32** when WOLF excluded group F. The record is closed
except for one field.

| Field | Meaning | Encoding | Status |
|---|---|---|---|
| 1 | BLACKOUT excluded groups | bitmask, bit 0 = A … bit 7 = H | device-confirmed |
| 2 | BLINDER fade-out | index into 0 / 0.2 / 0.5 / 1 s / 2 s | device-confirmed |
| 3 | BLINDER excluded groups | bitmask | device-confirmed |
| 4 | release mode ×6 | order WOLF, STROBE, BLINDER, SPEED, BLACKOUT, SMOKE; 0=FLASH 1=TOGGLE 2=1 s 3=5 s 4=10 s | device-confirmed |
| 5 | SMOKE fan speed | 0–100 | device-confirmed |
| 6 | SMOKE intensity | 0–100 | device-confirmed |
| 7 | SPEED multiplier | 0 = normal **and** FREEZE, 1 = 0.5×, 2 = 2×, 4 = 4×, 8 = 8× | device-confirmed |
| 8 | STROBE excluded groups | bitmask; A+B wrote 3 | device-confirmed |
| 9 | STROBE speed | 1–100 | device-confirmed |
| 10 | WOLF excluded groups | bitmask | device-confirmed |
| 11 | **unknown**, 100 in every corpus file | — | unattributed |

A mask field only exists once a group is actually excluded; absent means none.
Only four effects can exclude groups — the operator confirms **SPEED and SMOKE
have no exclusion control** on this MK1, which is why exactly four mask fields
exist.

### What `field 11` is not

Ruled out by measurement or by the absence of a control: SMOKE intensity and
fan (`f5`/`f6`), BLINDER fade-out (`f2`) and any other BLINDER value (the
screen has no second parameter), any WOLF parameter (the screen has none),
STROBE speed (`f9`), and master brightness (set to 80 %, wrote nothing). Look
for it in Settings → Project, where the group exclusions also live.

### Settings that are NOT project data — **[correlated]**

Three controller settings were changed and saved without writing a single byte
anywhere in the `.wpj`:

- STATIC POSITION fade (37 s, then 46 s)
- master brightness (80 %)

Guide 8 calls the static screens' values "saved globally". These belong to
controller-global storage, a candidate for `wmPersistent.wmx`. A show generator
cannot set them through a project file.

## F11-01 — writing type 102 `field 11` ourselves

The observation route was exhausted: the 2.0 reference manual shows Settings →
Project holds only the four group exclusions, and the operator found no control
that moves the field. So we wrote it.

**A project identical in every byte except `field 11` was uploaded to the
experiment project**, loaded on the controller, and compared.

- The operator reports **no visible change anywhere** in the UI.
- **DMX output is identical.** Two 12-second envelopes, ~300 frames each, 2048
  channels: `field 11` = 0 and `field 11` = 100 agree on **every channel**, in
  both min and max. The output was fully static (0 animated channels, 122
  non-zero), so there was no animation noise to hide a difference.

**[correlated]** `field 11` is inert for the rendered output in the state
tested. It is *not* proof of inertness in every state: the capture exercised one
static lighting look with no effect running and no flash key held.

**The BLINDER hypothesis is refuted.** `field 11` = 100 in every corpus file and
has no UI control, which is exactly what a BLINDER level would look like — guide
10 describes BLINDER as setting everything to full power. Two further envelopes
were captured **with the blinder active**, once at `field 11` = 100 and once at
0, each 200 frames in mode 32:

| | frames | non-zero channels | channels differing |
|---|---|---|---|
| blinder on, `f11` = 100 | 200 | 144 | — |
| blinder on, `f11` = 0 | 200 | 144 | **0** |

The blinder itself is plainly visible in the data — enabling it moves 48
channels, driving dimmers from 127 or 0 up to 255 — so the capture is sensitive
to exactly the kind of change the hypothesis predicted. It shows none.

### Verdict on `field 11`

**[correlated]** Inert in every condition tested: idle static output, and with
the blinder active. No UI control moves it, the 2.0 reference manual lists no
setting it could correspond to, it predates firmware 2.0 (present in a
schema-8 file), and forcing it from 100 to 0 changes neither the display nor a
single one of the 2048 DMX channels.

It is recorded as **unattributed and inert**, and the search is stopped here
rather than continued speculatively. A writer should preserve it verbatim,
treating absent and 0 as the same value. Conditions never exercised, for
whoever picks this up: strobe or smoke active, effects running, a second
universe in use, MK2/MK3 hardware.

### Side findings

- **Writing 0 stores the field as absent.** The firmware omits protobuf
  defaults, so "absent" and 0 are the same value. Any writer must treat them
  alike.
- ~~Loading a project resets the flash release modes.~~ **Retracted.** The
  `field 4` value came back as `01 00 00 00 00 00` because **the operator reset
  those modes by hand**, not because loading a project clears them. Nothing here
  supports an automatic reset, and the SMOKE reversion noted in FX-07 remains a
  single unexplained observation rather than the general behaviour this entry
  claimed.
- **RESTART (event 44) does not always cycle the USB device** on firmware
  2.0.18. One run kept the port open throughout; a later one reconnected
  normally. Automation must not require the disconnect.
- **Uploads are corruptible like downloads.** A 43 KB `SET_PROJECT` was refused
  by the firmware with its own message, "invalid wire_type", and succeeded on
  retry. Nothing is stored on a failed status.

## Type 115 — a 20-slot list, `field 6` moves as a block — **[observed]**

The record holds 20 repeated `field 5` items plus a 20-byte `field 6` on the
record itself, whose content is a permutation
(`00 01 02 03 0f 10 04 05 06 07 08 09 0a 0b 0c 0d 0e 11 12 13`) — a display
order. Each item carries `f2` (16, 32, 48, 99, 109, 119, 129 …), sometimes
`f3`/`f4` = 1, `f5` = 0x3FFFF (18 bits set), and a trailing `f9` = its index.

Across the three FX-01/FX-02 saves, each item's **`field 6` moved as a block**:

| Snapshot | Item `field 6` | Item `field 7` |
|---|---|---|
| `before.wpj` (WTOOLS-era pipeline) | 44 on every item | 41 on every item |
| after the first controller save | absent (default 0) | absent |
| after the second controller save | **4 on every item** | absent |

`field 7` was dropped by the firmware and never came back. `field 6` is a
single value applied uniformly to all 20 slots, so it is a **global setting
stored per slot**. **[hypothesized]** candidates, from what the operator did
between the two saves: the FADE time of the STATIC POSITION screen (guide 8:
"Move the encoder to set a FADE time between the positions"), or the STEP 1/4
control of the MOVE FX sequence editor. Both were touched. Discriminating
experiment: set the STATIC POSITION fade encoder to a distinctive value, save,
and check whether all 20 items take it.

## Serial transfer integrity — **[device-confirmed]**

The USB serial link is **not** error-free. In one session two of four
`GET_PROJECT` transfers of a 43 KB project failed: one raised
`Unsupported protobuf wire type 4` while parsing the response, and one returned
the correct length with wrong bytes and a SHA-1 header that did not match its
own body. Two subsequent transfers agreed byte for byte and verified.

`tools/wolfmix.py fetch_project` now retries: it accepts a transfer whose SHA-1
header matches (variants A and B carry one), otherwise requires two identical
consecutive transfers, and gives up after three attempts. Every project
download in the CLI and in the experiment runner goes through it. **Never
trust a single download of a project.**

## Sources externes

- wpj-toolkit `2bd0ee3` : digest complet dans `research/wpj-toolkit-digest.md`.
  Attention : il documente des fichiers **W1 MK2** ; nos variantes B/C
  (protobuf sans TLV) n'y figurent pas. Son conteneur TLV = notre variante A.
  Ne pas reproduire le writer privé de WPJ Studio (avertissement explicite
  du dépôt).

## Type 165 (presets) et types frères

Structure complète décodée le 2026-08-25 : voir `research/preset-format-165.md`
(enveloppe correlated, sous-message preset et FX largement correlated,
correction : type 140 = pads couleur statique, pas configs FX ;
type 161 = état volatil, pas du contenu de show).

## Type 140 ×8 — the static COLOUR palettes, one per group — **[device-confirmed]**

Same family shape as type 150: eight copies, `field 1` = 20, top-level
`field 2` = group index 0…7 (absent for A), and 20 repeated `field 5` items.
Every value in every item is ≤ 255 across the whole corpus (25 variant-A files,
4000 pads), so the items are byte-wide channel levels, not 16-bit like the
position palette.

### The item is the same sub-message as type 135

Record **135** carries 16 items of exactly the same shape, and wpj-toolkit
documents 135 as the global ColorFX palette whose pads hold
`red / green / blue / white / amber / lime / uv`, absent = omitted. Fields 1–7
in that order. Record 140 reuses that sub-message with 20 items instead of 16.

```
field 1 = 20                     pad count
field 2 = 0…7                    group index, absent for A
field 5 × 20                     one per colour pad
  f1 red    f2 green   f3 blue   f4 white
  f5 amber  f6 lime    f7 uv     — 0…255, absent = 0
```

### Why the corpus alone already argues for it

Only **26 distinct pads** exist corpus-wide, and the four "extra" channels
appear only on the hues that would actually use them:

| Pad | Stored | Reading | Sense |
|---|---|---|---|
| 20 | `f1..f4 = 255, f6 = 255` | R G B W L all full | the **white** pad, and the only pad with `f4` in a factory page |
| 1 | `f1=255 f2=127 f5=255` | R 100 G 50 **A 100** | orange — the one pad that drives **amber** |
| 4 | `f1=60 f3=255 f7=255` | R 24 B 100 **UV 100** | violet — the only pad with `f7`, and `f7` is **255 or absent, never anything else** |
| 6 | `f1=255` | pure red | matches `preset-format-165.md`: preset "Deep Red" points at pad 6 |
| 2, 8, 12, 13, 17, 18, 19 | carry `f6` | green/yellow/cyan family | **lime** appears on exactly the hues a lime LED helps |

Read as RGB, the 20 factory pads land on a clean hue sweep — 0°, 30°, 60°, 90°,
120°, 150°, 180°, 210°, 240°, 300°, 330° — with saturation and value at 100 %
on the pure ones. Read with the fields permuted, they do not.

Status was **correlated** when written — internal consistency plus one external
document. The device then confirmed it exactly; see below.

### Prediction published before measuring — group B, experiment project

The eight groups are identical in the experiment project except pads 2 (group A)
and 11, 16 (group B). Group B carries the only edited pads with a `f4`, so it is
the one to read. `field 11` of record 102 aside, record 140 has not moved once
across the 25 snapshots, so these are the values on the device right now.

Expected on SHIFT + pad, if the picker shows per-channel percentages
(`round(v / 255 × 100)`):

| Group B pad | Stored | R | G | B | W | A | L | UV |
|---|---|---|---|---|---|---|---|---|
| 16 | `f1=255 f2=105 f3=8 f4=64` | **100** | **41** | **3** | **25** | 0 | 0 | 0 |
| 11 | `f1=255 f2=64 f4=52` | **100** | **25** | 0 | **20** | 0 | 0 | 0 |
| 8 | `f2=255 f3=127 f6=40` | 0 | **100** | **50** | 0 | 0 | **16** | 0 |
| 4 | `f1=60 f3=255 f7=255` | **23–24** | 0 | **100** | 0 | 0 | 0 | **100** |
| 1 | `f1=255 f2=127 f5=255` | **100** | **50** | 0 | 0 | **100** | 0 | 0 |

Pad 16 alone separates `f1`, `f2`, `f3` and `f4` with four distinct values
(100 / 41 / 3 / 25) — no collision. Pads 8, 4 and 1 then pin `f6`, `f7` and
`f5`; each has one unique value (16, 23, and amber's presence) and the rest are
already pinned by pad 16.

If the picker is a colour wheel instead (mode **11 = `STATIC_COLOR_PICKER`**
exists in `mode-map.md`), the same five pads predict distinct hues:
pad 16 → **23.6°**, pad 11 → **15.1°**, pad 8 → **150°**, pad 4 → **254°**,
pad 1 → **30°**, all at saturation 100 % except pad 16 at 96.9 %.

Either display shape is decisive. The two readings cannot both be right.


### Measured — **[device-confirmed]**, and the editor turned out to have five views

The operator opened SHIFT + pad 1 on group B (its own name, which record 125 gives
group index 1) and photographed all five views of the picker. The header reads
`<group-B name> / ITEM B1` — the group's name and the item's group letter plus 1-based
index, which corroborates the A–H group ordering a third time.

Pad 1 stores `f1 = 255, f2 = 127, f5 = 255`. What the screen showed:

| View | Screen | Matches |
|---|---|---|
| `RGB+` | RED **255**, AMBER **255**, GREEN **127**, LIME 000, BLUE 000, UV 000, WHITE 000 | **the stored bytes, exactly** |
| `RGBW` | RED 100 %, GREEN **49 %**, BLUE 0 %, WHITE 0 % | 127/255 |
| `CMY` | CYAN 0, MAGENTA **128**, YELLOW **255** | 255 − G, 255 − B |
| `HUE` | HUE **29**, SATURATION 100 %, RGB 100 %, W A L 0 % | predicted 29.9° |
| `GRID` | the 20 pads by name — see below | |

The `RGB+` view is the decisive one: it prints the **raw 0–255 channel values**,
not percentages, and it names all seven channels in exactly the order of fields
1–7. Field → channel is settled:

```
f1 RED   f2 GREEN   f3 BLUE   f4 WHITE   f5 AMBER   f6 LIME   f7 UV
```

The four encoders carry two channels each in `RGB+` (`RED|AMBER`,
`GREEN|LIME`, `BLUE|UV`, `WHITE`), which is why a MK1 with four encoders can
still reach seven channels.

**The display truncates, it does not round.** 127/255 = 49.8 % showed as **49**,
and hue 29.93° showed as **29**. The earlier prediction of "50 %" and the
"23–24" hedge were both off by that one rule. Percentages read off this screen
are `floor(v / 255 × 100)`, so they are lossy — **always read `RGB+`**.

### The 20 pads are named, and the wire order is the grid order — **[device-confirmed]**

The `GRID` view lists the palette by name. Every name matches the decoded
channels, 20 for 20:

| # | Name | Stored | # | Name | Stored |
|---|---|---|---|---|---|
| 1 | Amber | R255 G127 **A255** | 11 | Orange | R255 G63 |
| 2 | Lime | R127 G255 **L127** | 12 | Pale Green | R41 G255 B30 **L41** |
| 3 | Cyan | G255 B255 | 13 | Mint | R81 G255 B110 **L81** |
| 4 | UV | R60 B255 **UV255** | 14 | Purple | R20 B255 |
| 5 | Pink | R255 B128 | 15 | Pink Panther | R255 G91 B193 |
| 6 | Red | R255 | 16 | Coral | R255 G127 B80 |
| 7 | Green | G255 | 17 | Yellow | R255 G255 **L127** |
| 8 | Turquoise | G255 B127 **L40** | 18 | Lemon | R255 G245 B80 **L127** |
| 9 | Blue | B255 | 19 | Sky Blue | G127 B255 **L20** |
| 10 | Magenta | R255 B255 | 20 | White | R255 G255 B255 **W255 L255** |

The pad named **UV** is the only pad carrying `f7`, and the pad named **Amber**
is the only factory pad carrying `f5`. The names are **not stored in the file** —
no string field ever appears in a 140 item — so they are firmware labels tied to
the slot index, unlike the position palette where `f5` holds a per-slot name.

**Grid layout — [correlated], corrected twice.** The matrix is **4 columns × 5
rows**, and the wire order fills it **column by column, top to bottom**:

```
        col 1        col 2       col 3          col 4
row 1    1 Amber      6 Red      11 Orange      16 Coral
row 2    2 Lime       7 Green    12 Pale Green  17 Yellow
row 3    3 Cyan       8 Turq.    13 Mint        18 Lemon
row 4    4 UV         9 Blue     14 Purple      19 Sky Blue
row 5    5 Pink      10 Magenta  15 Pink Panth. 20 White
```

Column 2 is the saturated column — Red, Green, Turquoise, Blue, Magenta — which
is what a designer would build. Two earlier readings of this layout were wrong:
first "5 rows × 4 columns" read the screen groups as rows, then "5 columns × 4
rows, bottom row first" inverted it. **Only the type-145 version below was
tested on hardware**; this one is transposed from it, since both palettes are
drawn by the same 20-slot screen. No colour pad has been pressed.

### Consequences for the other records

- Type **135** (16 items, the same sub-message, externally documented as the
  ColorFX palette) inherits the field → channel mapping. Its pad 15 is the same
  RGB+W+Lime white signature as 140's pad 20. **[correlated]**
- `research/preset-format-165.md` reads preset `f31` as bitmasks of type-140
  pads, citing "Deep Red" → mask 32 → pad 6. Pad 6 is now confirmed to be
  **Red** (`f1 = 255` alone), so a **bit `n` of that mask selects pad `n + 1`**
  in this same order. Still **[hypothesized]** overall, but the anchor holds.
- The static colour picker is mode **11** (`STATIC_COLOR_PICKER`) in
  `mode-map.md`, reached with SHIFT + a pad from mode 7.

### Still open on type 140

- Whether a pad's **name** can be changed at all, and where it would be stored.
- Whether any group can hold a **different number of pads** than 20 (`field 1`
  is 20 in every record of every file).

## Type 145 ×8 — the static GOBO palettes — **[device-confirmed]**

Same family as 140 and 150: one record per group, top-level `field 2` = group
index 0…7 (absent for A), 20 repeated `field 5` items. **Unlike 140 and 150 it
carries no `field 1` count** — the 20 slots are implicit.

```
field 2 = 0…7                    group index, absent for A
field 5 × 20                     one per gobo pad
  f1  glyph   one character; ' ' (0x20) = empty slot
  f2  gobo id see below — absent on an empty slot
  f3  name    UTF-8, optional, operator-assigned
```

In the whole corpus only **group A** is ever populated, with 17 gobos and pads
18–20 empty. Groups B–H hold 20 fully empty items. Note the two flavours of
empty: an empty slot inside a populated palette is stored as `f1 = ' '`, while
a wholly empty palette stores bare empty items (`2a 00`). A writer must
reproduce both.

### `f2` is a gobo image id, and the palette is generated from the patch

Record **111** is the range/capability table. On the gobo-wheel channel of the
profile `Lyre ZQ02244` (record 110 channel 10, `f4 = 8`), the 20 ranges are:

```
   0–  6  f3=14            no f4   "open"
   7– 13  f3=14  f4=425 ┐
  14– 20  f3=14  f4=424 │
  …                     │ 17 ranges carrying an image id
 119–127  f3=14  f4=352 ┘
 128–191  f3=26            gobo shake
 192–255  f3=26            gobo shake
```

Those 17 `f4` values, **in that order**, are exactly the 17 `f2` values of the
type-145 items. The odd-looking sequence in the palette — 425, 424, 423, 422,
421, 420 then 342 … 352 — is simply the order the ranges appear on the fixture's
gobo wheel; it is not a counter.

Two identities, checked mechanically on **25/25** variant-A files by
`tools/wpj_identities.py` (part of `make check`):

| Identity | Meaning |
|---|---|
| `110[c].f2 == len(111 slice of c)` | `110.f2` is the **range count**, not a feature enum |
| `[145 items].f2 == [111 ranges with f3 == 14].f4` | the gobo palette is the fixture's gobo wheel |

The second is not vacuous: `cc21` and `cd21` have **no** gobo-wheel fixture, and
their gobo palettes are empty on both sides — 0 = 0.

So the static gobo palette is **derived from the patch**: the firmware fills it
with one pad per image-bearing gobo range of the group's fixtures, skipping the
"open" range and the shake ranges. `f2` is a **global gobo-image id**, not a
project-local index — 342…352 and 420…425 are outside record 111's own indexing
(120 entries) and must live in the fixture library (`wmProfiles.wmx`).

### `f1` is an icon-font glyph, and the corpus cannot say more

Filled slots carry consecutive characters `!` `"` `#` … `1` (0x21…0x31) in slot
order, empty slots carry `' '` (0x20). Two readings fit and the corpus cannot
separate them, because this palette has never been reordered:

- a glyph index into a per-project gobo icon atlas, 0 = blank, allocated in
  order as the palette was built — in which case it identifies the **image**;
- a pure function of the slot index for filled slots — in which case it is
  **redundant** and a writer can regenerate it.

Discriminator: clear or reorder one gobo pad and see whether the remaining
glyphs keep their characters or renumber.

### Side findings on the patch side — **[correlated]**

`110.f4` (channel feature) and `111.f3` (range function) are nearly one-to-one
across the corpus:

| `110.f4` | `111.f3` seen | Reading |
|---|---|---|
| 1 / 2 | 1 / 3 | pan / tilt |
| 5 | 9, 10, 11 | colour wheel + scrolls |
| 7 | 12 (+32, 33) | dimmer |
| **8** | **14, 26** | **gobo wheel + gobo shake** |
| 15 | 32, 33, 34, 37 | shutter / strobe |
| 25, 26, 27 | 50, 51, 52 | red, green, blue |
| 31, 32, 33 | 56, 57, 58 | the extra colour channels |

`111.f4` is therefore a **capability id whose namespace depends on the feature**:
a gobo image id under `f3 = 14`, a colour id under `f3 = 9` (small integers
1…19 there, not 342…425).

### The record 105 contradiction — resolved on the corpus, `f4` was misread

Two readings could not both be right: `115[r].f2` as the **0-based DMX start
address** — six `Lyre ZQ02244` (16 ch) at 0, 16, 32, 48, 64, 80, ten `6x18W`
(10 ch) at 99, 109 … 189, and confirmed by the gobo DMX test above — against
record 105's `f4` = start address, `f7` = channels consumed, which gave spacing
10 for the 16-channel lyres and 8 for the 10-channel pars.

**`105.f4` is not a DMX address. It is the running offset into record 106**,
the same shape as `116.f3` into 110. Sorting the 105 entries of `rig-c` by `f4`
makes it obvious:

```
f4    0  10  20  30  40  48 … 112  120  121  131  141  141  147
f7   10  10  10  10   8   8 …   8    1   10    10    0    6    6   Σ = 153 = count(106)
```

Each `f4` is the sum of the preceding `f7`, and the intervals `[f4, f4+f7)`
tile `[0, count(106))` **exactly**. The tell is the pair at 141: two entries
share an offset because the first has span 0. A DMX address could not do that,
and the fixture at `115.f2 = 64` carries `105.f4 = 121`.

`106` is one entry per **mapped** channel of a fixture, and `106.f2` is its
absolute 0-based DMX channel. Subtracting the fixture's `115.f2` gives the
per-profile offset pattern — for the lyre, `0, 1, 6, 6, 7, 8, 10, 12, 13, 14`,
ten mapped channels out of sixteen, repeated identically at +16, +32 … That is
why `f7` = 10 for a 16-channel profile: **`f7` counts 106 entries, not DMX
channels.**

Three identities, checked mechanically on **25/25** variant-A files by
`tools/wpj_identities.py`:

| Identity | Meaning |
|---|---|
| the `[f4, f4+f7)` intervals tile `[0, count(106))` | `105.f4` = offset into 106, `f7` = its span |
| every `106[k].f2` of a slice ∈ `[115[r].f2, 115[r].f2 + profile channels)` | ties each slice to its fixture's DMX window |
| the fixtures' DMX windows are pairwise disjoint | `115.f2` is a real patch address |

None is vacuous: the window test fails immediately if the slices are assigned
to the wrong fixtures, and a rig whose `115.f2` were an internal arena index
would have no reason to keep its windows disjoint. The offset pattern is
constant per profile in every file except for the two **multi-block** fixtures
(`rig-b`'s `LED BAR 252 RGB`, 3 × 4 ch, and `rig-c-bug`'s `LASERBAR`, 6 × 8 ch),
where it is constant per block — the case where several 105 entries already
share one `f5`.

**Retracted**: `105.f4` = "0-based start address" and `105.f7` = "channels
consumed", as written in `research/corpus-mining-2026-08-25.md` and
`research/rig-c-bug.md`. `tools/wpj_codec.py` now names them `offset_106` and
`nb_entrees_106`. **`115.f2` is the DMX start address** — device-confirmed by
the gobo test, and now corroborated by the corpus.

Consequence for `research/rig-c-bug.md`: its address survey read the wrong
field, so the address ranges quoted there are wrong. Its conclusion is not —
the real patch is disjoint in both revisions, so there is still no DMX
collision.

**Still open**: which 110 channels get a 106 entry, and what `106`'s own fields
`f1`, `f3`…`f6` hold. `f7` being a per-profile constant means the whole 105/106
pair is probably derivable from the profile, like the gobo palette is.

### Measured on the device — layout and naming **[device-confirmed]**

The operator opened STATIC GOBO on group A. The screen header reads the name
record 125 gives group index 0 — a third independent corroboration of
the A–H ordering.

Three predictions were published before the photograph; all three hold.

**1. The grid order — settled by pressing pads, after two wrong readings.**
The matrix is **4 columns × 5 rows**, filled **column by column, top to
bottom**:

```
        col 1     col 2    col 3     col 4
row 1   Gobo 1    Gobo 6   Gobo 11   Gobo 16
row 2   Gobo 2    Gobo 7   Gobo 12   Gobo 17
row 3   Gobo 3    Gobo 8   Gobo 13   Gobo 18
row 4   Gobo 4    Gobo 9   Gobo 14   Gobo 19
row 5   Gobo 5    points   Gobo 15   Gobo 20
```

Established by DMX, not by reading a photograph: the **top-left** pad emitted 7
(item 1) and the **bottom-left** pad emitted 35 (item 5), so the left edge is a
column of five. The four groups visible on the screen are its **columns**.

Both earlier readings in this registry were wrong — "5 rows × 4 columns" read
those groups as rows, then "5 columns × 4 rows, bottom row first" inverted the
vertical axis on top of that. Deriving a physical layout by rotating a
photograph does not work; three pad presses settled it in minutes.

**2. Names are firmware-generated, and `f3` overrides them.** Nineteen slots
read `Gobo N` with **N = the 1-based slot index**; slot 10 reads **`points`**,
which is the one and only string stored in the whole record. Confirmed: the
`.wpj` carries no name for an unnamed gobo, and the label is synthesised from
the index.

**3. Slots 18–20 are the empty ones**, in the top row's last three positions as
predicted. The firmware still prints `Gobo 18/19/20` for them, but their icon is
a plain neutral disc rather than a gobo pattern — the label is not the tell, the
icon is. The earlier phrasing "the top row should read `[pad 16] [pad 17]
[empty] [empty] [empty]`" was right about *which* slots are empty and wrong to
expect blank labels.

### The icons corroborate the two id runs — **[observed]**

The palette's ids fall in two runs, 425→420 and 342→352, and the icons split at
exactly the same place:

| Slots | Ids | Icon on screen |
|---|---|---|
| 1–6 | 425, 424, 423, 422, 421, 420 | plain discs in a **graded size series**, smallest at slot 1 |
| 7–17 | 342 … 352 | **patterned** gobo glyphs |
| 18–20 | none | a single neutral disc, all three identical |

Read as an id space, that is one family of beam-size / dot gobos taken in
decreasing id order and one family of patterned gobos taken in increasing id
order — which is just the order the two families sit on the fixture's gobo
wheel. Icon reading is from a photograph and is **[observed]**, not proof.

`f2` therefore stays **[correlated]**: the screen never shows the id. The DMX
band test below would settle it, and is still worth doing.

**Caveat recorded at the operator's request**: the icons and labels come from
the Nicolaudie profile builder, whose gobo library the operator cannot fully
control. They describe what the *profile declares*, not necessarily what the
fixture physically projects. The claim here is about `f2` matching the profile's
declared id, and nothing more.

### UI facts for the mode map — **[device-confirmed]**

- The STATIC GOBO screen carries a **`ROTATE 0 %`** control on the fourth
  encoder and a **vertical strip of five feature icons** down the left edge,
  one highlighted — sub-pages of the gobo screen, not yet identified.
- An **`ALL GOBOS`** view exists, reached before a group is selected; it dims
  the palette and shows the A / B / C / D group letters unhighlighted.

### The DMX test — **[device-confirmed]**, two points, exact

Prediction published before measuring: pressing pad *n* drives the lyres' gobo
channel into the band of range *n*. Measured on the six `Lyre ZQ02244`, whose
gobo channel is offset 10 of each 16-channel block (DMX 11, 27, 43, 59, 75, 91
— the block starts 0, 16, 32, 48, 64, 80 confirm `115.f2` = **DMX start
address**):

| Pad pressed | `f2` | Predicted band | Measured, all six channels |
|---|---|---|---|
| none (baseline) | — | 0–6 "open" | **0** |
| 10 = `points` | 345 | 70–76 | **70** |
| 1 | 425 | 7–13 | **7** |

Nothing else in 2048 channels moved, in either capture, beyond a ±1 dither on
DMX 163/165/173 already present in the baseline.

So **`145[n].f2` is the gobo image id of range *n* of the group's gobo-wheel
channel**, and the controller emits that range's **lower bound** (`111.f1`),
not its midpoint. All six fixtures of the group take the value together.

### The rig was left as found

Pressing the lit pad a second time deselects it. A closing envelope agrees with
the opening baseline on **2045 of 2048 channels**; the three that differ (DMX
163, 171, 173) are the ±1 dither already present before the test, caught at a
different phase. The gobo channels are back to 0. **Nothing was written to the
controller and nothing was saved** — the whole experiment was live UI state
plus read-only captures.

### Scope of everything above — recorded at the operator's request

All of it was measured on **group A's gobo palette only**, sourced from **one
fixture profile** (`Lyre ZQ02244`, six instances). It is plausibly the general
rule and nothing contradicts that, but no other group, profile or fixture type
has been exercised. Treat transposition to another rig as **[hypothesized]**
until measured.

### The full band table, for reference

| pad | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| band | 7–13 | 14–20 | 21–27 | 28–34 | 35–41 | 42–48 | 49–55 | 56–62 | 63–69 |

| pad | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |
|---|---|---|---|---|---|---|---|---|
| band | 70–76 | 77–83 | 84–90 | 91–97 | 98–104 | 105–111 | 112–118 | 119–127 |

Pad 10 is `points`, so **`points` should land in 70–76**. Gobo channels are not
subject to the movement limits that made the position palette unreadable from
DMX, so the oracle can read this one directly.

## Preset `f29` — the static GOBO index per group — **[device-confirmed]**

Surveying the packed per-group arrays of record 165 in the experiment project:

| Field | 8 varints | Default | Reading |
|---|---|---|---|
| `f28` | position index per group | 1 | **static POSITION**, correlated |
| `f17` | dimmer per group | 255 | dimmer, hypothesized |
| **`f29`** | **255 on all eight** | **255** | **candidate static GOBO index** |
| `f30` | 9 on all eight, 1 on some presets | 9 | unknown |
| `f3`, `f7`, `f14`, `f23`, `f27`, `f32`…`f35` | all zero in this rig | 0 | unexercised |

`f29` is the only per-group array whose default is **255**, and 255 is exactly
the "nothing selected" sentinel already **device-confirmed** in the type-155
sequencer. Seven presets carry `[9, 255, 255, …]` — a single value on group A,
which is the only group with a gobo palette. If the index is 0-based like the
sequencer's, **9 = item 10 = `points`**, the one gobo the operator named.

That is three coincidences pointing the same way, but no experiment. It stays
**[hypothesized]** until one preset is saved with a known gobo on a known group.
If it holds, the preset record's palette references are symmetric — `f28`
positions, `f29` gobos, `f31` colours — and the three palette records 150, 145
and 140 are each reachable from a preset.

### What the corpus adds, and what it takes away — **[observed]**

Surveying `f29` over all 25 variant-A files (four rigs, 2038 presets), exactly
**three** non-sentinel patterns exist:

| Pattern | Presets | Where |
|---|---|---|
| `[1]×8` | 3 | `70's Paradise`, `Milky Way`, `Fire!` — **every file** |
| `[2]×8` | 1 | `Sizzle` — **every file** |
| `[9, 255×7]` | 7 | **only** the rig lineage that has a gobo palette |

**In favour.** The `[9, 255×7]` presets are `Get Moving`, `Candy Floss Swing`,
`valse`, and the four factory MOVE presets id 56–59 (`D A N C E`, `J U M P`,
`Point to Point`, `Lights to the Siren`). Those last four are **the same factory
presets in every rig**, and in `rig-a` and `rig-b` — whose eight gobo palettes
are all empty, no gobo-wheel fixture patched — they carry all-255 instead. So
the value is not shipped with the preset: something writes group A's slot
**only when group A actually has a gobo palette**, exactly like the palette
itself being derived from the patch.

**Against, and it must be said.** `f29`'s neighbour `f30` sits at `[9]×8` on
~65 presets of *every* file, so **9 is a common default value in this record**,
not a rare one — the "9 = `points`" coincidence is worth less than it looked.
And the four `[1]×8` / `[2]×8` presets carry a gobo index on all eight groups in
projects with **no gobo palette anywhere**, which kills any rule of the form
"255 wherever the group has no palette". They are factory constants nothing has
touched.

Net: the hypothesis survives and gained one real argument, the corpus is out of
road, and the base is still 0-based-vs-1-based undecided.

### Discriminator without a save — press a pad and measure — **[planned]**

The original discriminator needed group B to own a gobo palette, which it
cannot: the palette is derived from the patch and only group A has a gobo-wheel
fixture. But `f29` can be read **live**, through the DMX oracle that already
settled the type-145 gobo ids, with no write and no save.

Recall a preset and measure the lyres' gobo channel (0-based DMX 10, 26, 42, 58,
74, 90). Predictions published before measuring, from the band table above:

| Preset | page/slot | `f29[A]` | 0-based → pad | expect | 1-based → pad | expect |
|---|---|---|---|---|---|---|
| `Get Moving` | 1 / 2 | 9 | 10 = `points` | **70** | 9 | **63** |
| `Sizzle` | 1 / 13 | 2 | 3 | **21** | 2 | **14** |

Four distinct values, no collision. Anything else — the gobo channels staying at
0, or a value outside {70, 63, 21, 14} — refutes `f29` as a static gobo index.
A range instead of a single value would mean the preset's beam FX is animating
the gobo channel, which is itself worth knowing.

### Measured — **[device-confirmed]**, two points, both exact

**Experiment F29-01, 2026-08-26, W1 fw 2.0.18, `WMX EXP format-lab` version
1787670974700.** The project was downloaded first and its `f29` values checked
against the prediction. Nothing was written and nothing was saved: three
read-only 10-second envelopes, 2048 channels, with the operator recalling a
preset between them.

| Capture | gobo channels 10, 26, 42, 58, 74, 90 | Predicted 0-based | Predicted 1-based |
|---|---|---|---|
| baseline, nothing recalled | **0** on all six | — | — |
| `Get Moving`, `f29[A]` = 9 | **70** on all six | **70** | 63 |
| `Sizzle`, `f29[A]` = 2 | **21** on all six | **21** | 14 |

Both hit exactly, both static (min == max) while 44–60 other channels were
animated by the presets' FX. So:

```
f29 = static gobo index per group A–H, 8 packed varints
      0-based index into that group's type-145 palette
      255 = no gobo, the same sentinel as the type-155 sequencer
```

The controller emits the **lower bound** of the selected range, exactly as the
type-145 pad test found.

### The factory values are not inert

`Sizzle` carries `[2]×8` — one of the factory constants that appear even in
projects with no gobo palette at all, and the reason this entry was hedged
above. It applied. So those `[1]×8` / `[2]×8` presets do carry a real gobo
index; it simply has no effect on a group whose palette is empty. The argument
against the hypothesis dissolves, and the argument from `f30 = [9]×8` was
irrelevant: `f30` is a different field that happens to share a default.

The preset record's palette references are therefore symmetric and all three
are now anchored: **`f28` positions (150), `f29` gobos (145), `f31` colours
(140)**, each an index or mask into that group's own palette.

### 255 clears the channel, it does not mean "leave alone" — **[device-confirmed]**

A third recall closed the loop. `Startup` (page 1, slot 1) is a full-content
preset — `f4` = 255, the same content mask as the other two — carrying
`f29 = [255]×8`. Recalling it from the `Sizzle` state drove all six gobo
channels back to **0**.

So the sentinel is applied, not skipped: a preset with 255 actively clears the
group's static gobo. A writer that means "keep whatever is there" has no way to
say so in this field.

### UI fact, and the rig was left as found — **[device-confirmed]**

**Preset pads do not toggle off.** Pressing a lit preset a second time does
nothing — unlike the type-145 gobo pads, which deselect on a second press. The
only way back is to recall another preset.

The closing envelope after `Startup` agrees with the opening baseline on
**2048 of 2048 channels**, in both min and max, with the same 122 non-zero and
0 animated channels. Nothing was written to the controller and nothing was
saved: the whole experiment was live UI state plus three read-only captures.

### Scope

Measured on **group A only**, whose six `Lyre ZQ02244` are the only gobo-wheel
fixtures on this rig. Groups B–H have empty palettes, so nothing there could be
exercised. Transposition to another group, profile or rig stays
**[hypothesized]**, as for type 145 itself.


## Preset `f32`–`f35` — a schema-10 addition, zeroed by the upgrade — **[correlated]**

Four more packed 8-varint per-group arrays, and their presence splits cleanly on
the writer/schema version at offset 50:

| Files | Schema | `f32` … `f35` |
|---|---|---|
| `rig-c.wpj` | **8** | **absent from every preset** |
| `rig-a`, `rig-b`, the ACC series | 10 | `50` / `0` / `100` / `100`, on all 8 groups of all 80 presets |
| `f2737ec3`, `rig-c-bug`, the whole experiment lineage | 10 and 11 | `0` / `0` / `0` / `0`, everywhere |

Read out: the four fields **did not exist at schema 8**. Projects authored at
schema 10 carry a plausible default set — 50 %, 0, 100 %, 100 % — while the one
project that was **upgraded from schema 8** carries zeros in all four, on every
preset, and keeps them through every later save. The upgrade path added the
fields without filling them.

`50 / 0 / 100 / 100` on a per-group array is the shape of a Move FX
offset/width pair — pan offset 50 %, tilt offset 0, pan width 100 %, tilt
width 100 % — but nothing has been measured, so that is **[hypothesized]** and
the assignment order is a guess.

### It is not the rig-c blackout — **[correlated]**

Tempting, given the lineage: `research/rig-c-bug.md` blames a firmware upgrade
on this very project. But `f2737ec3` is the **healthy** revision of the pair and
it carries the zeros too, identically to `rig-c-bug`. The zeros predate the
fault and cannot cause it. One candidate removed, not added.

### Consequence for a writer

A generator targeting schema 10 or 11 should emit `50 / 0 / 100 / 100` rather
than copying the zeros of the experiment project, which are an upgrade artefact
rather than a chosen value.


## Preset `f30` — the static-colour spread mode — **[device-confirmed]**

### It is a per-group array, and the corpus alone said otherwise

`f30` is stored like `f28`/`f29` — eight packed varints — and across **2033
presets in 25 files it is never non-uniform**: all eight groups always carry the
same value.

**An earlier version of this entry read that as "one scalar replicated eight
times". That was wrong.** The device shows the control, named **`PATTERN`**,
once per group on the STATIC COLOUR screen, and the operator photographed a
state where **group A reads `SINGLE`, group B reads `FLASH` and group C reads
`SINGLE`** — three groups, two different values, side by side. `f30` is a
genuine per-group array; the corpus is uniform only because no factory preset
ever varies it between groups.

Worth keeping as a method note: uniformity across 2033 samples is evidence about
the *corpus*, not about the *field*. One screen refuted it.

Its domain is small: `9` (1618 presets), `1` (239), `0` (100), `2` (50), `5` (25).

### The corpus pins it to the static colour

On the factory **colour page** (preset ids 20–39, content mask `f4` = 8), a
preset carries exactly **two** payload fields, `f30` and `f31`. Everything else
is identical across the whole page. So `f30` belongs to the static colour,
next to the pad selection.

And it is only ever non-9 when at least **two** pads are selected:

| pads in `f31` | `f30` seen |
|---|---|
| 0 | 9 ×1336 |
| 1 | 9 ×257 |
| 2 | 0 ×75, 1 ×189, 2 ×25, 5 ×25, 9 ×25 |
| 3 | 0 ×25, 1 ×25, 2 ×25 |
| 4 | 1 ×25 |

The single exception is `Purple Rain`, and it has a structure of its own: it is
the one preset in the corpus whose **two 20-bit masks differ** (`UV + Purple`
against `UV + Pink`), so its "two pads" are not two pads of one selection.

### Measured — **F30-01**, four modes, four read-only captures

Predictions were published before each recall. Ten `6x18W` pars at DMX bases
99, 109 … 189 (`R` = base+1, `G` = base+2, `B` = base+3) and six
`Lyre ZQ02244`, whose colour arrives on their **colour wheel** at DMX 8, 24, 40,
56, 72, 88. Nothing was written and nothing was saved.

| `f30` | preset | pads | pars 1 → 10 |
|---|---|---|---|
| **0** | `Sizzle` | Red, Orange | green only on the **even** pars — **alternating, one in two** |
| **1** | `Moulin rouge` | Red, Magenta | blue `255 191 127 63 0 0 63 127 191 255` — **gradient, mirrored** |
| **2** | `Neon Rave` | Lime, Pink | `Pink Pink Lime Lime Lime Lime Lime Lime Pink Pink` — **hard step, mirrored** |
| **5** | `Jet Set` | Lime, Turquoise | red `122 104 94 82 67 52 40 27 13 0`, blue the complement — **gradient, not mirrored** |
| **9** | `Startup` | Amber only | all ten identical — **no spread, one colour** |

So `f30` is the **spread mode of a multi-pad static colour selection**, and two
axes are visible in it: interpolated against stepped, and mirrored about the
centre against running straight across.

| Value | Reading |
|---|---|
| 0 | stepped, alternating fixture by fixture |
| 1 | gradient, mirrored about the middle |
| 2 | stepped, mirrored about the middle |
| 5 | gradient, straight across |
| 9 | none — one colour or no static colour |

Recalling `Startup` at the end brought the output back to the opening baseline
on **2048 of 2048 channels**. Five recalls, five read-only captures, nothing
written and nothing saved.

### Two things it settles beyond `f30`

- **A static colour reaches a fixture with no RGB through its colour wheel.**
  The lyres took discrete wheel positions under every mode — `72 / 0` under
  mode 2, `56 72 8 8 72 56` under mode 1 — and the controller emits each
  range's **lower bound**, the same rule already confirmed for gobos.
- **Each group's fixtures are spread independently**, over that group's own
  ordered list: the six lyres and the ten pars each carry the full pattern.

### The full enumeration, read off the encoder — **[correlated]**

The operator stepped the `PATTERN` encoder clockwise one detent at a time and
described each entry. The list is **eleven entries and it wraps**. Eight of them
are **four directions × two renderings**, the rendering shown by whether a run
of overlapping circles — a blend indicator — accompanies the chevrons:

| Screen order | Icon | `f30` | How it was fixed |
|---|---|---|---|
| 1 | `SINGLE` | **9** | **measured** — one colour, all fixtures identical |
| 2 | `FLASH` | 10 | derived |
| 3 | four dots, filled / empty / filled / empty | **0** | **measured** — alternating one fixture in two |
| 4 | chevrons pointing **outward** + circles | **1** | **measured** — gradient, symmetric about the centre |
| 5 | chevrons pointing **outward**, alone | **2** | **measured** — hard split, symmetric |
| 6 | chevrons pointing **inward** + circles | 3 | derived |
| 7 | chevrons pointing **inward**, alone | 4 | derived |
| 8 | chevron pointing **right** + circles | **5** | **measured** — gradient running par 1 → par 10 |
| 9 | chevron pointing **right**, alone | 6 | derived |
| 10 | chevron pointing **left** + circles | 7 | derived |
| 11 | chevron pointing **left**, alone | 8 | derived |

The alignment is `value = (screen position − 3) mod 11`. **Five of the eleven
entries were measured on DMX before the list was read, and all five land
exactly**, with no collision and nothing left over. The six values the corpus
never shows — 3, 4, 6, 7, 8 and 10 — are precisely the modes no factory preset
uses: both "inward", both "left", the hard "right", and `FLASH`.

The two axes visible in the DMX captures now factor properly. It was never
gradient-against-stepped crossed with mirrored-against-straight; it is
**direction** (outward, inward, right, left) × **rendering** (blended, hard),
with `SINGLE`, `FLASH` and the alternating pattern sitting outside that grid.

### Every entry then measured — **F30-02**, eight captures, no write at all

The six derived rows did not stay derived. The `PATTERN` control can be driven
**live** from the STATIC COLOUR screen, so the whole list was walked one detent
at a time on **group B** — ten `6x18W` pars, the most readable group on this rig
— with `Amber` (pad 1) and `Cyan` (pad 3) selected. Every step's DMX was
predicted in writing before the operator turned the encoder. Nothing was
written to the controller and nothing was saved.

Amber is `R255 G127 A255`, Cyan is `G255 B255`, so R and B separate them cleanly.

| Element | Predicted | Measured | |
|---|---|---|---|
| 4 outward blended | R `0 64 128 191 255 …` | R `0 63 127 191 255 255 191 127 63 0` | exact, firmware **truncates** |
| 5 outward hard | Cyan 1,2,9,10 · Amber 3–8 | identical | exact |
| 6 inward blended | mirror of 4 | R `255 191 127 63 0 0 63 127 191 255` | exact |
| 7 inward hard | Amber 1,2,9,10 · Cyan 3–8 | **Amber 1,2,3,8,9,10 · Cyan 4–7** | direction right, **shares wrong** |
| 8 right blended | R `255 226 198 170 141 113 85 56 28 0` | same, one value off by 1 | exact |
| 9 right hard | Amber 1–5 · Cyan 6–10 | identical | exact |
| 10 left blended | reverse of 8 | identical | exact |
| 11 left hard | Cyan 1–5 · Amber 6–10 | identical | exact |

### The share rule, corrected by element 7

Element 7 was the one miss, and it is worth keeping. The prediction mirrored the
*positions* of element 5; the firmware instead re-runs the sequence from the
other end, and **the share belongs to the colour, not to the position**:

> Over the run of positions a direction defines — the half-length for the
> mirrored directions, the full length for the straight ones — the colours are
> dealt in order and **the first colour takes the larger share**.

Two colours over a half-length of 5 gives 3 then 2. Outward deals from the
centre outward: 3+3 = six central pars Amber, 2+2 = four edge pars Cyan.
Inward deals from the edges inward: 3+3 = six edge pars Amber, 2+2 = four
central pars Cyan. Both measured, both fit. Ten positions straight gives 5 and
5, also measured.

### The distribution rule, complete — **F30-03**, **[device-confirmed]**

How the firmware deals N colours over M fixtures when M is not divisible by N
is what a show generator actually needs, and two more captures on group B — the
ten pars, with `Amber` (pad 1), `Cyan` (pad 3) and `UV` (pad 4) selected, red
reading 255 / 0 / 60 so the three never collide — settled it. Both splits were
predicted in writing first.

| Geometry | Run length | Colours | Predicted | Measured |
|---|---|---|---|---|
| element 9, right hard | 10 | 3 | **4-3-3** | Amber 1–4, Cyan 5–7, UV 8–10 |
| element 5, outward hard | 5 (half) | 3 | **2-2-1** | Amber 4–7, Cyan 2,3,8,9, UV 1,10 |
| element 5, outward hard | 5 (half) | 2 | 3-2 | measured earlier |
| element 9, right hard | 10 | 2 | 5-5 | measured earlier |

The rule, in one sentence:

> Along the run a direction defines — the **half-length** for the mirrored
> directions (`outward`, `inward`), the **full length** for the straight ones
> (`right`, `left`) — the selected pads are dealt **in ascending pad order**,
> split as evenly as possible, and the **remainder goes to the earliest
> colours**.

`outward` deals from the centre towards the edges, `inward` from the edges
towards the centre, `right` from the first fixture to the last, `left` from the
last to the first. The blended variants interpolate the same deal instead of
stepping it, truncating rather than rounding.

That is enough to generate a static colour look for any rig and reproduce what
the controller does, which was the point.

### `FLASH` is not a geometry — **[device-confirmed]**

Every other entry lays colours out in space. `FLASH` does not: it makes the
group's colour pads **momentary**. The operator tapped a second colour on a
group set to `FLASH`, the output changed while the pad was held and reverted on
release — and the group was then left with **no colour at all**, its first pad
having become momentary too. Confirmed in DMX: with `FLASH` and a single pad
latched the output was byte-identical to the baseline on all 2048 channels, and
after the flash the group's six fixtures sat at their no-colour value.

### The final table

| Screen | Icon | `f30` | Behaviour |
|---|---|---|---|
| 1 | `SINGLE` | 9 | one colour, every fixture the same |
| 2 | `FLASH` | 10 | pads momentary, not a spatial layout |
| 3 | four dots, filled/empty/filled/empty | 0 | alternating, one fixture in two |
| 4 | outward + circles | 1 | blended, dealt centre → edges |
| 5 | outward | 2 | hard, dealt centre → edges |
| 6 | inward + circles | 3 | blended, dealt edges → centre |
| 7 | inward | 4 | hard, dealt edges → centre |
| 8 | right + circles | 5 | blended, dealt first → last |
| 9 | right | 6 | hard, dealt first → last |
| 10 | left + circles | 7 | blended, dealt last → first |
| 11 | left | 8 | hard, dealt last → first |

### The stored values, read out of a save — **F30-04**

The remaining gap was that six of the eleven stored values were arithmetic
rather than read. One save closed it, and it was designed to test three things
at once. The operator set three groups to three different patterns with three
different colour selections, then saved:

| Group | Pattern set on screen | Pads selected | Predicted `f30` | Predicted `f31` |
|---|---|---|---|---|
| A | element 7, inward hard | Amber, Cyan | **4** | **5** |
| B | element 6, inward blended | Amber, Cyan, UV | **3** | **13** |
| C | element 11, left hard | Amber, UV | **8** | **9** |

Read back off the controller:

```
f30      = [4, 3, 8, 0, 0, 0, 0, 0]
f31[A]   = 5    Amber, Cyan
f31[B]   = 13   Amber, Cyan, UV
f31[C]   = 9    Amber, UV
f31[D…H] = 24   UV, Pink        — the live residue of the Milky Way recall
```

**Every value exact**, including the D–H residue. Three consequences:

- `f30` is a **genuine per-group array**, proven in the bytes and not only on
  the screen. This is the first non-uniform `f30` ever observed — 2033 corpus
  presets carry the same value on all eight groups.
- Stored values **4, 3 and 8** are now read rather than derived, and they land
  exactly where the icon order says. With 9, 0, 1, 2 and 5 already read from
  factory presets, **eight of the eleven** entries have their stored byte
  confirmed. The map is an order-preserving cyclic bijection, which one point
  and a direction already determine; eight leave 6, 7 and 10 with no freedom.
- `f31` = eight 20-bit masks is confirmed at the **bit level**, with three
  different masks in one record.

### Saving a preset does not save the project — **[device-confirmed]**

Worth its own line, because it cost a false negative. Creating a preset with
SHIFT + a pad, naming it and confirming leaves it in the controller's live
state: the screen showed `Preset 83` on page 5, yet two full downloads returned
**82 presets and an unchanged version**, 1787670974700. Only after the operator
performed the separate **project** save did the file change — version
1787670974701, 43400 → 43751 bytes, 83 presets.

Any experiment that writes through the UI must therefore save the project
explicitly and check the version counter before concluding anything.

### The PRESET EDIT screen — **[observed]**

Photographed while creating the preset. It shows the preset's content as six
toggles — `COLOR`, `MOVE`, `BEAM`, `GOBO`, `LIVE EDIT`, `OTHER` — plus
`FADE 00:00.00` and `HOLD 00:01.00`. Those six are the obvious candidates for
the bits of `f4`, the content mask (255 on a full preset, 8 on the colour page,
17 on beam, 5 on move), and `FADE` is a candidate for `f11` (500 / 2000 / 4000,
already guessed to be milliseconds). The new preset came out with `f4` = 255
and no `f11`. Nothing here is confirmed; it is the map for the next session.

Also confirmed in passing: the firmware names an unnamed preset `Preset N` with
**N = id + 1**, so page 5 slot 2 reads `Preset 82` for id 81. That corroborates
`id = (page − 1) × 20 + (slot − 1)`.

### Group membership, read off the DMX — **[device-confirmed]**

Setting three groups to different patterns at once made the group layout visible
for the first time, since every factory preset carries the same value on all
four repetitions of `f31`:

| Group | Fixtures |
|---|---|
| A | the six `Lyre ZQ02244` at DMX 0, 16, 32, 48, 64, 80 |
| B | the ten `6x18W` at DMX 99, 109 … 189 |
| C | two `Lyre ZQ02344` (operator's own report; they did not move in this capture) |

**Correction to an earlier assumption**: the `GROUPS` key (SHIFT + BPM TAP) does
**not** display group membership. The operator reports it only pages the display
to show groups E–H. Nothing in the project file has yet been shown to carry the
fixture → group assignment; where it lives is still open.

### `f31` — one 20-pad mask per group A–H — **[device-confirmed]**

`f31` is 20 packed varints = **160 bits = eight 20-bit masks**, one per group
A–H, little-endian, bit *n* of group *g* selecting pad *n+1* of that group's
type-140 palette:

```
mask(g) = (int.from_bytes(20 bytes, "little") >> (20 * g)) & 0xFFFFF
```

That makes the preset's four per-group arrays line up exactly: `f28` positions,
`f29` gobos, `f30` pattern, `f31` colour mask — eight slots each.

It reads out sensibly where the earlier attempt did not. `Startup` is `Amber` on
all eight groups, `Deep Red` a single bit 5 = pad 6 = Red, `Neon Rave` is
`Lime + Pink` on all eight — and the presets that differ between groups are
plainly designed that way:

| Preset | A | B | C…H |
|---|---|---|---|
| `Purple Rain` | UV + Purple | UV + Pink | UV |
| `Aim` | UV + Red | Red + White | Red |
| `Milky Way` | White | UV + Pink | UV + Pink |

**Retracted**: an earlier entry read `f31` as *four repetitions of five bytes,
each holding two 20-bit masks*. It was cutting eight 20-bit groups into four
40-bit packets, which is why one mask kept looking like a mysterious duplicate
of the other and why `Purple Rain` looked like a lone anomaly. It is not an
anomaly; it is a preset with three different colour selections across its
groups.

### Measured — `Milky Way`, the preset that separates the two readings

`Milky Way` carries `White` on group A and `UV + Pink` on groups B–H, with
`f30` = 0, alternating. The two readings disagree sharply about it: the correct
one says group A holds a single pad and group B two, the retracted one put both
selections on group A. Recalling it settled the matter.

| | Predicted | Measured |
|---|---|---|
| six lyres, group A | one colour, all six identical | colour wheel **0** on all six |
| ten pars, group B | alternating UV / Pink, UV first | odd pars `R60 B255 UV255`, even pars `R255 B128 UV0` |

`UV` is pad 4 and `Pink` pad 5, and the lower index came first, as everywhere
else. The pars' channels were animated by the preset's beam FX, so the maxima
are the colour; the alternation itself is unmistakable.

Side finding: the `6x18W` profile's `110.f4` = 33 is its **UV** channel — the
one that carried 255 on exactly the UV pars.

**Consequence for the pad-count table above.** The "pads in `f31`" column was
computed from the first 20 bits, which under the correct reading is **group A's
mask alone**. The rule it supported still holds in the corrected reading — `9`
is the only value seen when no group has two pads — but `Purple Rain` is no
longer its exception: it genuinely holds two pads on A and on B while sitting on
`SINGLE`, which is a legitimate if unusual choice. `Milky Way` is the reverse
case, one pad on A and two on B, carrying `0`.

## The fixture → group assignment — it was in the file, filed under "category"

**[correlated on 27/27 files; the slot 0/1/2 → group A/B/C mapping is
device-confirmed]**

The open question of the previous session — *nothing in the project file has yet
been shown to carry the fixture → group assignment* — is answered, and it needed
no hardware at all. The assignment was already decoded; it was named
**`categorie`**, and that name is what hid it.

### Where it lives — two redundant carriers

| Field | Scope | Reading |
|---|---|---|
| `115[r].f4` | one per fixture | the fixture's group index, **absent = 0 = group A** |
| `105[e].f6` | one per patch entry | the same index, repeated on every entry of that fixture |
| `125[i].f4` | one per slot, 6 bytes LE | the OR of `1 << 115[r].f3` over the fixtures of slot *i* — a **profile** mask, so it cannot address a single fixture |

The first two agree on **457/457 fixture rows across 27 files**, and the third
is derivable from them bit for bit. All three are now checked by
`groupe_fixture` in `tools/wpj_identities.py` — 5 identities, 27 files.

`tools/wpj_codec.py` renames `105.f6` from `categorie` to `groupe` and gives
record 115 its three proven keys: `adresse_dmx` (`f2`), `profil` (`f3`),
`groupe` (`f4`).

### Prediction published before measuring

Written before the dump, on the experiment project, from the DMX-measured
membership alone: the six `Lyre ZQ02244` at DMX 0, 16, 32, 48, 64, 80 carry
`f6 = 0`; the ten `6x18W` at 99, 109 … 189 carry `f6 = 1`; the two
`Lyre ZQ02344` carry `f6 = 2`. **All twenty entries exact**, including the two
lyres that live at fixture indices 15 and 16, far from the other four.

The two remaining fixtures — `Entour Faze` and `Spark` — carry `f6 = 8`.

### Nine slots: A–H, plus a ninth for what is not a group

`125` has exactly 9 items in every file, and the group index reaches 8 in the
corpus. Slot 8 is not a ninth group: it collects the fixtures that have no
group pads on the device — `Entour Faze`, `Spark`, `Sonicboom` in the two rigs
that own such machines. That matches the preset's four per-group arrays being
**eight** slots wide (`f28` positions, `f29` gobos, `f30` pattern, `f31` colour
mask), and record 130's ninth item being the odd one out (`f4 = 27` where the
first eight carry `f4 = 20`).

### Retracted — "125 is the 9 fixture *categories*, not the 8 groups A–H"

Written in `research/corpus-mining-2026-08-25.md` §2.2 and carried into
`SPEC.md` §7.2. The mask really is derivable from the profiles, and that
observation was correct; the conclusion drawn from it was not. A derived mask
says nothing about what the slot *means*.

Three things refute the category reading:

1. **`rig-b` slot 0 holds two different profiles** — `6x18W 6in1 RGBAW UV` and
   `LED PAR 56 Black RG`, mask `0x09`. A fixture *category* derived from the
   model cannot merge two models; an operator building a group of "all my pars"
   does exactly that.
2. **The slot 0/1/2 members are the measured groups A/B/C.** Group A was read
   off the DMX as the six `Lyre ZQ02244` and group B as the ten pars (F30-02,
   and again on `Milky Way`); those are precisely the members of slots 0 and 1.
   Slot 2 is the two `Lyre ZQ02344`, the operator's group C.
3. **`f8` is a *group* name.** The experiment project names slot 0 `Beam` and
   slot 1 `Pars` — the operator's own names for their moving-head group and
   their par group, not category labels the firmware would ship.

`rig-c-bug`'s seventh profile at slot 3 is a `LASERBAR`: a fourth group, `D`.

### What this unlocks, and what is still missing

A show generator can now target a group: read `115[*].f4`, and the eight slots
of `f28`/`f29`/`f30`/`f31` in every preset address exactly those fixtures. The
group *names* are readable too, from `125[i].f8`.

Still open, and cheap to settle with one photograph: whether the device's
group A screen displays the name `Beam`. That would take the slot → letter
mapping from *measured membership* to *named on the device*, and would confirm
slots 3–7 as D–H without patching anything.

## Preset `f4`, the content mask — what the corpus can and cannot say

### `f4` is constant per preset page — **[correlated, 27/27 files]**

2158 factory presets, 27 files, four values and not one exception:

| Page | `f4` | Binary | The operator's name for the page |
|---|---|---|---|
| 1 | 255 | `11111111` | full |
| 2 | 8 | `00001000` | colour |
| 3 | 5 | `00000101` | move |
| 4 | 17 | `00010001` | beam |
| 5 | 255 | `11111111` | the three user presets, all full |

That is the whole vocabulary the corpus contains. Every factory page carries one
value on all twenty of its slots, so **the corpus cannot separate the six
toggles** — no factory preset ever differs from its page.

### The one out-of-vocabulary value is ours, not the firmware's

`acc03a.wpj` carries `f4 = 25` on preset 78. It is **not** evidence: ACC-03
wrote it with our own tools, deliberately, as `17 | 8`, and the W1 rejected it —
the preset's tile vanished when clicked, and no Color FX played
(`research/experiments.md`, ACC-03). The follow-up `acc03b.wpj` with `f4 = 255`
produced no UI bug.

**That is a real signal about the shape of the field.** A plain bitmask should
have accepted `25` as "beam plus colour" and shown something. The display bug
argues for `f4` being read against a **closed vocabulary** — an enumeration of
preset kinds, or a mask whose legal combinations are constrained — rather than
eight free bits. Status: **[observed]**, one data point, and it is our own
write. It does not settle the question either way; it says the question is not
the trivial one.

### The bits, if it is a mask

`8` shares no bit with `5` or `17`; `5` and `17` share **bit 0**. So a mask
reading needs a toggle that both the move page and the beam page carry and the
colour page does not — and the colour page would then be a single toggle, which
would have to be `COLOR`. `GOBO`, `LIVE EDIT` and `OTHER` are the candidates for
bit 0. Bits 1, 5, 6 and 7 are never seen except inside 255.

### The read-only measurement that settles it — **[planned]**

No write, no save. Open `PRESET EDIT` (SHIFT + the pad) on one preset of each
page and read which of the six toggles are lit.

| Preset to open | `f4` | Predicted |
|---|---|---|
| any page 2 slot | 8 | exactly **one** toggle lit, and it is `COLOR` |
| any page 3 slot | 5 | exactly **two**, one of them `MOVE` |
| any page 4 slot | 17 | exactly **two**, one of them `BEAM`, and its second toggle is the **same** one as the page-3 preset's |
| any page 1 slot | 255 | all six lit |

If instead each page shows a single lit toggle — `COLOR`, `MOVE`, `BEAM` — then
`f4` is an enumeration and the mask reading is refuted, which is exactly what
the ACC-03 display bug hints at.

## Preset `f11` = FADE and `f15` = HOLD — the numbers to check on the screen

### `f11`, the fade — **[correlated]**, and predicted to the centisecond

`f11` is absent on all of pages 1 and 4, and carries `500` on most of pages 2
and 3. Exactly two presets in the whole corpus carry anything else, the same two
in all 27 files:

| Preset | Page, slot | `f11` | Predicted `FADE` on screen |
|---|---|---|---|
| `Split The Atom` | 3, 6 (id 45) | 4000 | `00:04.00` |
| `Wander The Forest` | 3, 7 (id 46) | 2000 | `00:02.00` |
| `Rise up` (id 44), its neighbour | 3, 5 | 500 | `00:00.50` |
| any page 4 preset | — | absent | `00:00.00` |

The names fit a long fade, and the newly created preset 82 came out with no
`f11` while its screen read `FADE 00:00.00` — absent = 0 = no fade, which is the
`ACC-01` reading of absence throughout this format.

### `f15` = HOLD — **[hypothesized]**, one anchor and no variation

Preset 82's screen read `HOLD 00:01.00` and its `f15` is `1000`. But `f15` is
`1000` on **2197/2197 presets in 27 files** — nobody has ever changed a hold
time, so the corpus contributes nothing beyond that single anchor. Falsifiable
in one glance: every `PRESET EDIT` screen should read `HOLD 00:01.00`.

## F4-01 — `f4` is a bitmask after all, and three of its bits are named

Six `PRESET EDIT` screens, photographed. **No write, no save**: the file was not
touched, and the six presets cover all four `f4` values the corpus contains.

| Preset | Page, slot | `f4` | Binary | Top row lit |
|---|---|---|---|---|
| `Searchlight` | 1, 6 (id 5) | 255 | `11111111` | `COLOR` + `MOVE` + `BEAM` |
| `1982` | 2, 6 (id 25) | 8 | `00001000` | `COLOR` |
| `Rise up` | 3, 5 (id 44) | 5 | `00000101` | `MOVE` |
| `Split The Atom` | 3, 6 (id 45) | 5 | `00000101` | `MOVE` |
| `Wander The Forest` | 3, 7 (id 46) | 5 | `00000101` | `MOVE` |
| `Pulse Out` | 4, 6 (id 65) | 17 | `00010001` | `BEAM` |

### An enumeration is refuted

`Searchlight` lights `COLOR`, `MOVE` and `BEAM` **at the same time**, each in its
own category colour. A closed vocabulary of preset kinds cannot do that. `f4` is
a bitmask.

**Retracted, same session**: "the ACC-03 display bug argues for `f4` being read
against a closed vocabulary rather than eight free bits", written earlier today.
It does not. Under the mask reading, ACC-03's `25` = `1 | 8 | 16` = bit 0 +
`COLOR` + `BEAM` is a perfectly legitimate combination — a beam preset with
colour added, which is exactly what ACC-03 was trying to build. So the W1's
display bug had **another cause**, still open; `color_fx_actif = 0` and `f16`
are the remaining suspects from that experiment.

### Three bits named, and one that is not

| Bit | Value | Toggle | How it is pinned |
|---|---|---|---|
| 3 | 8 | **`COLOR`** | `1982` carries `8` alone and lights `COLOR` alone |
| 2 | 4 | **`MOVE`** | page 3 is `5` = bit 0 + bit 2 and lights `MOVE`; bit 0 cannot be `MOVE` because `Pulse Out` carries bit 0 and shows `MOVE` **unlit** |
| 4 | 16 | **`BEAM`** | symmetric: page 4 is `17` = bit 0 + bit 4, and page 3 carries bit 0 with `BEAM` unlit |
| 0 | 1 | **unnamed** | set on the move and beam pages, clear on the colour page |
| 1, 5, 6, 7 | | **unnamed** | never observed outside `255` |

`GOBO`, `LIVE EDIT` and `OTHER` were rendered the same orange on **all six**
screens, including on `1982` where bit 0 is clear. So these photographs name
none of their bits, and — per the rule paid for three times already — nothing is
inferred here about what that orange means. An orange tile has simply never been
seen in any other state.

Status: `COLOR`, `MOVE`, `BEAM` **[device-confirmed]**; the mask shape
**[device-confirmed]**; bit 0 **[observed]**.

## F11-02 — `f11` is FADE in milliseconds — **[device-confirmed]**

Four distinct values on six screens, every one as predicted before the
photographs were taken:

| Preset | `f11` | Predicted | On screen |
|---|---|---|---|
| `Split The Atom` | 4000 | `00:04.00` | `00:04.00` |
| `Wander The Forest` | 2000 | `00:02.00` | `00:02.00` |
| `1982` | 500 | `00:00.50` | `00:00.50` |
| `Searchlight`, `Rise up`, `Pulse Out` | absent | `00:00.00` | `00:00.00` |

**Absent = 0**, once more, in a format that never writes an explicit zero.

*Correction to the request that produced these photographs*: its table listed
`Rise up` at `f11 = 500`. The dump it was built from says `f11` is **absent** on
`Rise up`, and the screen agrees. The prediction that was actually derived from
the data was right; the line transcribing it was not.

### `f15` = HOLD — **[correlated]**, still one value

Six screens, six times `HOLD 00:01.00`, and `f15` = 1000 on all six. It is 1000
on 2197/2197 presets corpus-wide, so the millisecond scale still rests on the
single ratio 1000 ↔ 1.00 s. Consistent, not yet varied.

### Negative — the screen's `COLOR` line is not `f31`

`PRESET EDIT` shows one named colour at the fourth encoder. It does not read the
preset's static-colour mask:

| Preset | Screen | `f31`, group A |
|---|---|---|
| `Searchlight` | `-` | **Red** |
| `1982` | `Cyan` | Lime + Cyan + Pink |
| `Rise up`, `Split The Atom`, `Wander The Forest` | `Green` | **empty** |
| `Pulse Out` | `Magenta` | **empty** |

Four presets show a colour while `f31` is empty, and the one preset with a
single clean `f31` pad shows nothing. No top-level scalar of the preset carries
the pad index either (3 = Cyan, 7 = Green, 10 = Magenta were searched for, and
`f10` — which is page-constant like `f4` — is 6 / 5 / 3 on those pages). Where
that line reads from is **open**.

## F4-02 — the content mask is `f10`, not `f4` — **[device-confirmed]**

One project save, two toggles switched off on two user presets, downloaded
twice with identical SHA-256. Version 1787670974701 → **1787670974702**, so the
save reached the file.

### The prediction was wrong in an informative way

The published prediction was that `f4` would read `254` on the preset whose
`GOBO` toggle was switched off. **`f4` did not move at all** — it is still `255`
on all three page-5 presets. `f10` moved instead:

| Preset | Toggle switched off | `f10` before | after |
|---|---|---|---|
| page 5 slot 1, `valse` | `GOBO` | absent | **8** = bit 3 |
| page 5 slot 2 | `LIVE EDIT` | absent | **16** = bit 4 |
| page 5 slot 3 | `OTHER` | absent | absent — nothing changed |

### `f10` is the six toggles, in screen order, and a set bit means OFF

`0` = nothing switched off = all six lit. That alone re-reads the six
photographs from this morning **without a single contradiction**:

| Preset | `f10` | Bits set | Predicted OFF | Screen showed OFF |
|---|---|---|---|---|
| `Searchlight` | absent | — | none | none |
| `1982` | 6 | 1, 2 | `MOVE`, `BEAM` | `MOVE`, `BEAM` |
| `Rise up`, `Split The Atom`, `Wander The Forest` | 5 | 0, 2 | `COLOR`, `BEAM` | `COLOR`, `BEAM` |
| `Pulse Out` | 3 | 0, 1 | `COLOR`, `MOVE` | `COLOR`, `MOVE` |

Six for six. The bit order is the **reading order of the screen**, the top row
then the bottom row:

| Bit | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| Toggle | `COLOR` | `MOVE` | `BEAM` | `GOBO` | `LIVE EDIT` | `OTHER` |
| Pinned by | three screens | three screens | four screens | the `valse` write | the slot-2 write | slot 3's stored 32, read on the screen |

`f10` is **≤ 62 on all 2197 presets of the corpus** and never reaches 64, which
is exactly a six-bit field. Every value the corpus holds reads cleanly:
`3` = a beam page, `5` = a move page, `6` = a colour page, `32` = only `OTHER`
off, `51` = `BEAM` + `GOBO`, `61` = `MOVE` alone, `62` = `COLOR` alone.

It also settles the rendering, which no photograph could be asked to settle on
its own: on `1982`, `f10 = 6` leaves bits 3, 4, 5 clear, so `GOBO`, `LIVE EDIT`
and `OTHER` are **on** there — the orange tile is the **lit** state of the
bottom row, and the top row simply takes its category colour when lit and drops
its tile when not.

### Retracted — F4-01's bit assignments on `f4`

Written earlier today: "`COLOR` = `f4` bit 3, `MOVE` = bit 2, `BEAM` = bit 4",
at **[device-confirmed]**. Wrong field. `f4` and `f10` are *both* constant per
factory page, so the six screens could not tell them apart — the four `f4`
values simply happened to be in one-to-one correspondence with the four `f10`
values across the four pages. It took a write that moved one without the other.

That is the corpus-uniformity trap in a new dress: not one field uniform
everywhere, but **two fields co-varying everywhere**, which is just as
indistinguishable and just as easy to mistake for a proof. The reading that
survives is the one where a single experiment separated them.

What survives from F4-01: the mask **shape** — `Searchlight` lighting three
toggles at once still refutes an enumeration — and the retraction of the
ACC-03 "closed vocabulary" reading. **`f4` itself is unknown again**: 255 on
pages 1 and 5, 8 / 5 / 17 on pages 2 / 3 / 4, and unmoved by a content-mask
edit.

### `OTHER` = bit 5, confirmed by the state that was already there

The prediction was that switching `OTHER` off alone would read `f10 = 32`.
Page 5 slot 3 did not change in this save — and it did not need to: it carries
`f10 = 32` **before and after**, and the operator, opening its `PRESET EDIT`
screen, reports that `OTHER` was **already off** on it and switched it back on.
Two independent readings of the same bit, one stored and one on the screen.

*Correction*: this entry first read that null diff as "either the toggle was not
pressed or `OTHER` does not toggle". That was reading the diff instead of the
absolute value. The value was in the file the whole time.

All six bits are now named.

### The reverse differential — missed once, then measured

The published prediction was that with `OTHER` switched back on, the next save
would read `f10` **absent** on page 5 slot 3.

**First attempt, missed.** The operator switched `OTHER` on, saved, switched it
off again and saved again. The version counter went 1787670974702 → **704**, two
increments, and the intermediate state was gone before the download. Nothing was
learned about the prediction.

**Second attempt, exact.** `OTHER` switched back on and saved once more:

| | Predicted | Measured |
|---|---|---|
| `f10` on page 5 slot 3 | absent | **absent** |
| `f4` on that preset | unchanged, 255 | 255 |
| records touched by the save | 165 only | **165 only** |
| bytes | — | 43654 → **43652**, exactly the two bytes of a `f10` varint field |

Version 1787670974705, `sha256 0ec6b169…0280546f`, downloaded twice identically.
Bit 5 is now confirmed in **both directions**, and the byte accounting is exact:
one tag byte plus one value byte, removed when the toggle goes back on.

*A second correction on this experiment.* The download that measured it was
launched as a **baseline**, with the published expectation that the counter
would still read 704 because a screen edit does not reach the file. It read 705:
the operator had already saved. The prediction that mattered was right; the one
about when to look was wrong — twice in a row on the same experiment, in
opposite directions. The lesson is not "take a baseline", it is that the version
counter is the only thing that says which state a download holds, and it has to
be read before anything is concluded, not after.

### A clean round-trip, from the pair of saves that missed

The file at version 704 is **byte-identical** to the one at 702 — same 43654 bytes, and not one record differs, only the
version counter in the opaque prefix:

```
after-two-toggles    version 1787670974702
after two more saves version 1787670974704  every record identical
```

So switching a content-mask toggle off, on and off again returns the project to
**exactly** the same bytes. The toggle leaves no residue anywhere else in the
file, and `f10` is the only thing in the project that carries it — which is a
stronger statement than "`f10` changed when we pressed it", and it comes free.
**[device-confirmed]**

**Negative**: switching a toggle off does **not** imply the masked content is
cleared. `valse` did lose its group-A gobo (`f29[A]` 9 → 255) in the same save,
but across the corpus `f10` bit 3 and an all-255 `gobos` array agree on only
595/2197 presets, and bit 0 versus an empty `f31` on 1693/2197. The `valse`
erasure came from something else in that save, which also moved
`move_fx_actif`, `f16`, `f18` and two `move_fx1` fields.

### Side observation — record 115 lost `f6` and `f7` on every fixture

All 20 fixtures dropped `f6 = 231` and `f7 = 20` in this save, which is the
whole 100-byte shrink of record 115. Both were a per-project constant
replicated on every slot, and the registry already flagged that shape as
suspected volatile state. The `groupe`, `profil` and `adresse_dmx` fields are
untouched, and `groupe_fixture` still holds — 5 identities on **29** files.
**[observed]**

## Preset `f16` — twelve 9-bit group masks, and the answer to ACC-02/ACC-03

**[correlated, 30/30 files, 2446 presets]**

`f16` is a packed-varint field whose values are all `< 256`: they are the
**bytes of one little-endian bit field**, the same construction as `f31`. Cut
that bit field into slices of **9 bits** and every slice is a group mask.

Nine, not eight — because record 125 has nine slots, the groups A–H plus the
one that holds the fixtures with no group pads. The ninth bit is **never set**
in any slice of any preset.

### The alignment tests itself

At a 9-bit stride, slice 1 equals `move_fx_actif` **exactly, 2446/2446**:
`0 ↔ 0`, `255 ↔ 255`, `1 ↔ 1`. At an 8-bit stride the same field reads `254`
where `move_fx_actif` says `255` — a mask meaning "every group except A" sitting
on a preset that drives every group. One stride is coherent and the other is
not.

Stronger still: across 2446 presets × 12 slices = **29352 extractions**, not one
slice falls outside `{0, 1, 2, 5, 7, 255}`. A wrong alignment would smear
arbitrary values everywhere.

```
slice 0   0 or 255      == color_fx_actif       (2445/2446, see below)
slice 1   0, 1 or 255   == move_fx_actif        (2446/2446)
slice 2   0 or 255      a third engine, independent of both
slice 5   255 always
slice 7   255 on 60 presets, 0 elsewhere
slice 11  5 (A+C), 2 (B) or 7 (A+B+C) — constant per project, never per preset
slices 3, 4, 6, 8, 9, 10   always 0 in this corpus
```

`moteurs_f16` in `tools/wpj_identities.py` checks the ninth bit and the
`move_fx_actif` equality on every preset of every file — 6 identities, 30 files.

### The one exception is `acc03b`, and it closes an open question

Exactly one preset in the corpus has slice 0 = `0` while `color_fx_actif` = 255:
preset 78 of **`acc03b.wpj`**. That is our own write, from the experiment whose
result was recorded on 2026-08-25 as *"accepté, pas de bug UI, mais Color FX et
dimmers toujours ignorés"*.

**That is why it was ignored.** ACC-03b set `color_fx_actif` and left `f16`
alone, so the two carriers of the colour engine's group mask disagreed and the
firmware followed `f16`. The suspicion recorded at the time — *"nouveau suspect :
1er varint de f16 = masque de groupes du moteur couleur"* — was right, and the
9-bit reading now says why it is a mask and what its slots are.

**Consequence for a writer**: `color_fx_actif` and `move_fx_actif` are
**duplicates** of slices 0 and 1. Writing one without the other produces a
preset the device renders differently from what the file appears to say. This is
the second redundant pair found in this format, after `115.f4` / `105.f6`.

## Record 111 — `f1`/`f2` are the DMX bounds of a range — **[correlated, 30/30]**

The tell was in the value distributions: `f1` and `f2` are drawn from paired
sets — `16/15`, `32/31`, `56/55`, `64/63`, `96/95`, `128/127`, `192/191` — with
`f2 = 255` on 944 items. Those are the boundaries of a channel's function
ranges, `f1` = first DMX value, `f2` = last.

Prediction published before the test: for each channel, the ranges tile
`[0, 255]` — first `f1` = 0, each `f1` following the previous `f2`, last
`f2` = 255. **944 channels tile exactly.** Every one of the 1026 channels in
the corpus then falls into one of three cases, with nothing left over:

| Case | Count | Shape |
|---|---|---|
| the ranges tile `[0, 255]` | **944** | the ordinary channel |
| **unassigned channel** | **53** | `110` carries no `f4`, and its single `111` item is **empty** |
| the isolated `f4 = 18` pattern | **29** | a single range `{f1: 255, f3: 41}`, which the start/end reading does not cover |

944 + 53 + 29 = 1026. `plages_111` in `tools/wpj_identities.py` checks the
trichotomy on every channel of every file — 7 identities, 30 files. It is not
vacuous: it fails immediately if `f1` and `f2` are swapped, or if a channel's
range slice is taken from the wrong offset.

### The `f4 = 18` pattern is worth an experiment

`110.f4 = 18` and `111.f3 = 41` are both **absent from the feature table**
recorded earlier under "side findings on the patch side". The 29 channels
carrying it belong to moving heads only — `Lyre ZQ02244` (21) and `MH-100 BEAM`
(8) — and the same profiles also carry a `{f2: 255, f3: 41}` variant that tiles
normally. A single range anchored at DMX 255 on a moving head, on a feature the
rest of the corpus never names, is the shape of a **reset or a special
function**. It is one `dmx-envelope` away from being settled, and the operator
owns six `Lyre ZQ02244`.

### An unassigned channel is explicit, not missing

The 53 channels with no `f4` still carry a `111` item — an **empty** one. The
format does not omit the slot; it fills it with a message whose every field is
absent. That is the same convention as `120`'s empty entries (`2a 00`), and it
is why `count(111)` stays derivable from `110.f2` on every file.

## Record 106 — the channel's engine role, and the pan/tilt travel limits

**[correlated, 30/30 files, 3775 entries]**

`106` had one decoded field, `f2` = absolute DMX channel. Two more now read.

### `f4` = the role of the channel in the W1's engine — the missing link

Each `106` entry targets a channel of its fixture's profile: add
`106.f2 − 115.f2` to the profile's offset `116.f3`. Do that, and `106.f4` and
the profile's feature `110.f4` correspond **term for term**, everywhere:

| `106.f4` | Role | `110.f4` | | `106.f4` | Role | `110.f4` |
|---|---|---|---|---|---|---|
| 0 | dimmer | 7 | | 9 | shutter | 15 |
| 1 | pan | 1 | | 10 | strobe | 15 |
| 2 | tilt | 2 | | 11 | colour wheel | 5 |
| 3 | red | 25 | | 12 | gobo wheel | 8 |
| 4 | green | 26 | | 14 | *unnamed* | 22 |
| 5 | blue | 27 | | 15 | *unnamed* | 16 |
| 6 | extra 1 | 31 | | 21 | *unnamed* | 20 |
| 7 | extra 2 | 32 | | 22 | *unnamed* | 19 |
| 8 | extra 3 | 33 | | | | |

`9` and `10` are the only pair sharing a feature — shutter and strobe both live
on `110.f4 = 15`, which is what that feature was already read as.

**This is the field a show generator needs.** It answers "which DMX channel
carries this fixture's red" directly, without inferring anything from the
profile's channel order. `roles_106` in `tools/wpj_identities.py` checks the
table on every entry of every file, and an unknown role fails rather than
passing unnoticed — 8 identities, 30 files.

### `f5`/`f6` = the fixture's travel limits on pan and tilt — **[device-confirmed]**

On the colour roles, `f5`/`f6` are `0`/`255`: the whole channel. On pan and tilt
they vary **per fixture**, and they vary in pairs — which is what a rig hung in
symmetric pairs looks like:

| Fixture, DMX | pan `f5`–`f6` | tilt `f5`–`f6` |
|---|---|---|
| lyre @ 0 | 133–201 | 0–142 |
| lyre @ 16 | 133–190 | 0–142 |
| lyre @ 32 | 151–204 | 0–77 |
| lyre @ 48 | 151–204 | 0–77 |
| lyre @ 64 | 128–202 | 0–127 |
| lyre @ 80 | 128–202 | 0–127 |
| `ZQ02344` @ 199, 219 | 48–88 | **255–198** |

This is the answer to a standing note in the operator's own brief — *"the DMX
output is not the image of the stored values for pan/tilt: I have travel limits
on my moving heads"*. The limits are **here**, in `106.f5`/`f6`, per fixture and
per axis.

The two `ZQ02344` carry `f5 > f6` on tilt. Read as `[low, high]` that is
malformed; read as `[start, end]` it is an **inverted axis**, which is what a
moving head hung upside down needs.

**And that pair is already measured.** The `Floor` → `Ceiling` capture recorded
earlier in this registry, under type 150, drove exactly two fixtures' tilt from
**255 to 198** and was written up as "both inverted and compressed into 57 DMX
steps", with no explanation available at the time. Those two fixtures are the
two `ZQ02344`, and their tilt limits are `f5 = 255`, `f6 = 198`: same endpoints,
same order, same 57 steps. The prediction was published years — well, hours —
after the measurement, and it fits without a free parameter:

```
DMX = f5 + percent × (f6 − f5)
```

`Floor` is TILT 0 % → 255. `Ceiling` is TILT 100 % → 198. Both exact. The
inversion is `f5 > f6`, not a sign bit anywhere.

`f1`/`f3` are *not* the enclosing bounds: they read `0`/`127` on pan while `f6`
reaches 201. They stay unnamed.

### The read-only test that would settle it — **[planned]**

Nothing is written and nothing is edited. Recalling a **position from the
palette** is enough; the Fixture Limit screen must be left alone, since touching
it would change the very field under test.

Group A's pan is its fixture's own DMX address, tilt is address + 1 — roles 1
and 2 sit on channel offsets 0 and 1 of the `ZQ02244`.

**Identify the pad by what its editor shows, never by its position.** The first
attempt at this told the operator "pad 5" on the assumption that the wire order
is the pad order. It is not — the pad they opened showed `50 70 0 70`, which is
`Crowd` (PAN 50, TILT 70, FOCUS 0, FAN 70) and not `Ceiling` (50 / 100 / 0 / 50).
The same trap as the colour grid, paid a third time. The slot → pad mapping for
type 150 is **still unknown**, and this is a reminder that it is.

**Recall the position whose editor reads TILT = 100 %** — that is `Ceiling`. At
100 % the formula has no rounding left in it: the tilt channel must read exactly
`f6`.

| Lyre @ DMX | tilt channel | Predicted |
|---|---|---|
| 0 | 1 | **142** |
| 16 | 17 | **142** |
| 32 | 33 | **77** |
| 48 | 49 | **77** |
| 64 | 65 | **127** |
| 80 | 81 | **127** |

Three distinct values across six fixtures, no rounding, and a wide margin — with
no limits at all the six would read 255. Its pan is 50 %, predicting **167, 161,
177, 177, 165, 165**, with ±1 allowed for rounding.

**`Crowd` works just as well**, TILT 70 %, predicting tilt **99, 99, 54, 54, 89,
89** and the same pan as `Ceiling`. **`Orchestre`**, PAN 13 % / TILT 23 %,
exercises the low end: tilt **33, 33, 18, 18, 29, 29**, pan **142, 140, 158,
158, 138, 138**. All non-extreme values ±1 for rounding.

Any two of the three recalls cover each limit pair at two points, and a reading
that ignored the limits would land on the same value for all six fixtures.

### A feature to come back to

The operator reports that a firmware update added the ability to **detach the
moving heads and set them independently**. Nothing in this registry has been
attributed to it yet. The per-group preset arrays that are zero throughout the
corpus — `f3`, `f23`, `f27` — and the schema-10 additions `f32`–`f35` are the
places to look first.

## Record 115 `f6` — the fixture display order — **[correlated, 30/30]**

The record's own `field 6` — not the per-fixture one — is one byte per fixture,
and it is a **complete permutation** of the fixture indices in every file.
`ordre_fixtures_115` checks it; 9 identities, 30 files.

What it is *not*: neither a sort by group nor a sort by profile explains it
corpus-wide, and the two explain **complementary** halves — 9/30 for
`(group, address)`, 21/30 for `(profile, index)`, 30 between them. The operator's
own rig is the interesting case:

```
stored     0 1 2 3 15 16 | 4 5 6 7 8 9 10 11 12 13 | 14 | 17 | 18 19
profiles   ZQ02244 ×6    | 6x18W ×10               | Faze | Spark | ZQ02344 ×2
groups     A ×6          | B ×10                   | 9th slot   | C ×2
```

Read by profile it is exact; read by group it would put C before the ninth slot.
`rig-a` is the mirror image — there the group order and the profile order
disagree the other way, and the stored list follows the **group**. A rule that
holds for one and fails for the other is not the rule.

So `f6` is an **ordering the project carries explicitly**, most likely the patch
list order as the editor shows it, which the operator can rearrange. Only the
permutation property is claimed. **This is one glance in WTOOLS from being
settled**: open the patch and read the fixture order off the screen.

### Preset `f18` — a false lead, recorded so it is not walked again

`f18` is 10 varints of which only the first is ever non-zero, on 8 factory
presets and 2 user ones. One clean single-variable differential looked
decisive: switching `LIVE EDIT` off on page 5 slot 2 took `f18[0]` from **24 to
8** — losing exactly bit 4, which is the bit `f10` gained. That suggested
`f18[0] & f10 == 0`.

**It does not hold**: 84 presets violate it, all of them page-3 presets carrying
`f18[0] = 3` against `f10 = 5`. And the companion differential disagrees too —
switching `GOBO` off on `valse` took `f18[0]` from **11 to 0**, not to 3.

`f18[0]` takes the values 1, 3, 8, 9, 11, 16, 19, 24 across the corpus, on
presets whose names are all movement-flavoured (`Get Moving`, `Runway`, `Aim`,
`Point to Point`, `D A N C E`). It reacts to the content mask but is not masked
by it. Still **open**.

## POS-01 — the travel limits measured, and `FAN` decoded by the miss

One read-only capture. `Crowd` recalled on group A, 301 frames, 2048 channels,
nothing written. The predictions were published beforehand.

### Tilt — six for six, exact

| Lyre @ DMX | tilt channel | `f5`–`f6` | Predicted | **Measured** |
|---|---|---|---|---|
| 0 | 1 | 0–142 | 99 | **99** |
| 16 | 17 | 0–142 | 99 | **99** |
| 32 | 33 | 0–77 | 54 | **54** |
| 48 | 49 | 0–77 | 54 | **54** |
| 64 | 65 | 0–127 | 89 | **89** |
| 80 | 81 | 0–127 | 89 | **89** |

`min == max` on all six, so these are static values, not the ends of an
animation. Three distinct results from three distinct limit pairs, each computed
as `f5 + 0.70 × (f6 − f5)` from a stored `TILT = 70 %`, and every one landed on
the unit.

**`106.f5`/`f6` are the travel limits.** This is now device-confirmed twice over
and by two different routes: the retrospective `Floor` → `Ceiling` capture on
group C, and this forward prediction on group A.

### Pan — the prediction was wrong, and the reason is `FAN`

Predicted 167, 161, 177, 177, 165, 165. Measured **153, 155, 176, 180, 174,
180**. Not a near miss — and the tell is that the two lyres of each pair, which
share a limit pair exactly, came out **different**: 176 against 180, 174 against
180. Whatever set the pan was not applying one value to the group.

`Crowd` stores `FAN = 70 %`, and the prediction ignored it. Expressed as a
percentage of each lyre's own band, the six measured pans are:

```
29.4   38.6   47.2   54.7   62.2   70.3        measured
30     38     46     54     62     70          30 + 8k, k = 0…5
```

A monotone ramp from **30 % to 70 %**, in DMX address order, across the six
fixtures of the group. So `FAN` spreads pan symmetrically about 50 %, from
`100 − FAN` to `FAN`, distributed evenly over the group's fixtures:

```
pan_k = (100 − FAN) + k × (2·FAN − 100) / (n − 1)      k = 0 … n−1
DMX_k = f5 + pan_k/100 × (f6 − f5)
```

Every one of the six lands within 1 DMX step of that, which is what 8-bit
rounding over bands of 53 to 74 steps costs. Status **[correlated]** — one FAN
value, one group, one geometry.

**And the miss is what produced it.** A pan prediction that had been *right*
would have said nothing about `FAN`; it was the pairs splitting apart that
forced the field into view. Recorded because the temptation is to publish only
the tilt table.

### The discriminator — measured, POS-02 — **[device-confirmed]**

`Ceiling` stores `FAN = 50 %`. Under the rule above, `2·FAN − 100 = 0`: the ramp
collapses and **every fixture sits at 50 %** of its own band. The pairs that
split on `Crowd` must come back together.

| Lyre @ DMX | pan | tilt (`TILT = 100 %`) |
|---|---|---|
| 0 | **167** | **142** |
| 16 | **161** | **142** |
| 32 | **177** | **77** |
| 48 | **177** | **77** |
| 64 | **165** | **127** |
| 80 | **165** | **127** |

Tilt at 100 % has no rounding in it at all and must read exactly `f6`. Pan is
±1. The two predictions fail in different ways: if the limits are wrong the tilt
column breaks, and if the `FAN` rule is wrong the pan pairs stay split.

**Both held.** Measured: pan **167, 162, 178, 178, 165, 165**, tilt **142, 142,
77, 77, 127, 127**.

- **Tilt exact on all six**, and exact on all six of `Crowd` too — **12/12
  across the two captures**, from three different limit pairs at two different
  percentages. `106.f5`/`f6` are the travel limits, with nothing left to argue.
- **The pan pairs closed**: `(178, 178)` and `(165, 165)`, where `Crowd` gave
  `(176, 180)` and `(174, 180)`. Expressed against each lyre's own band the six
  sit at 50.0, 50.9, 50.9, 50.9, 50.0, 50.0 % — the ramp collapsed exactly as
  the `FAN` rule requires.

### The divisor is 65536, not 65535

The first pass predicted 161 where 162 was measured, and 177 where 178 was
measured — both of them the two cases whose exact value lands on `.5`. The cause
is that `32768 / 65535` is *not* one half: it is 0.500008, and the ramp term
pushed it a hair under. Dividing by **65536** makes `32768` exactly 50 % and
takes `Ceiling`'s pan from 4/6 to **6/6**, degrading nothing else.

So the stored 16-bit fields are `percent × 65536`, read back as `v / 65536`,
with the result rounded to nearest. That is the natural encoding for a firmware
that stores a fraction in a `uint16`, and the two `.5` cases are what exposed it.

### Final tally, and the one that still misses

```
DMX = round( f5 + frac × (f6 − f5) )
frac = (1 − FAN) + k × (2·FAN − 1) / (n − 1)      k = fixture rank, 0…n−1
FAN, PAN, TILT = stored / 65536                    n = fixtures in the group
```

| | pan | tilt |
|---|---|---|
| `Crowd` | 5/6 | **6/6** |
| `Ceiling` | **6/6** | **6/6** |

**11/12 and 12/12.** The single miss is `Crowd` on the lyre at DMX 32: predicted
175, measured 176, an exact value of 175.38. It is the third fixture of six on a
53-step band, so an intermediate rounding inside the ramp would explain it —
that remains **[hypothesized]**, and one more capture at a different `FAN` would
pin it. The tilt column, which has no ramp in it, never misses.

## Record 106 `f1`/`f3` — the DMX window the role drives — **[correlated, 30/30]**

`[f1, f3]` is **exactly one of the channel's `111` ranges** on 2643 of the 3775
entries, and the range it picks is always the one the role calls for:

| Role | Range `111.f3` | | Role | Range `111.f3` |
|---|---|---|---|---|
| 0 dimmer | 12 | | 6 extra 1 | 56 |
| 3 red | 50 | | 7 extra 2 | 57 |
| 4 green | 51 | | 8 extra 3 | 58 |
| 5 blue | 52 | | 9 shutter | 34 |
| 14 *unnamed* | 48 | | 15 *unnamed* | 38 |

That is a second, independent confirmation of the role table: the roles were
derived from `110.f4`, the profile's channel feature, and they land on the
matching `111.f3`, the range's own function, through a completely different
path. `bornes_106` checks it — 10 identities, 30 files.

### The 1132 that do not match are four named patterns, not noise

| Count | Role | `[f1, f3]` | What the channel has |
|---|---|---|---|
| 412 | **1 pan, 2 tilt** | `(0, 127)` | one range `(0, 255)` |
| 378 | **11 colour wheel, 12 gobo wheel** | `(0, 0)` — absent | 17 to 20 ranges |
| 174 | **10 strobe** | `(0, 241)`, `(0, 251)`, `(0, 16)` | spans several ranges |
| 126 | 21, 22 | `(190, 255)`, `(0, 32)` | — |

Each is coherent with the reading. A **wheel** has no single range to point at —
its slots are chosen through the gobo and colour palettes — so the window is
left absent. **Strobe** is a continuous speed that legitimately spans several
ranges. Only **pan and tilt** are odd: a flat `(0, 127)` on every one of the 206
fixtures in the corpus, against a channel whose single range is `(0, 255)`.
Those are the two roles carried on a 16-bit pair, and `127` is the one constant
here that nothing explains yet. **[observed]**

Note that this window is *not* the travel limit: the limits are `f5`/`f6`, they
are per fixture, and on pan they run to 201 or 204 — well past the 127 in `f3`.
The two pairs of fields do different jobs, which is why both exist.

## POS-03 — record 151 is the detached-fixture positions

The operator toggled the firmware feature that **detaches moving heads for
independent control**, on group A's `Ceiling`, and saved. Version
1787670974705 → 706, 43652 → 43669 bytes, and exactly **two** records moved.

### `150.f1`/`f2` are a slice of 151 — **[device-confirmed]**

```
before   Orchestre  f1 = 4              151 has 4 items
after    Orchestre  f1 = 4              151 has 5 items
         Ceiling    f1 = 1, f2 = 4
```

`f2` is the offset, `f1` the length: `[0,4)` for `Orchestre` and `[4,5)` for
`Ceiling` tile `[0, 5)` exactly. It is the **same (offset, length) couple** the
format uses in `105.f4`/`f7` into 106 and `116.f3`/`f2` into 110 — the third
instance of one construction, which is why it was recognisable at a glance.

`tranches_151` checks the tiling; 11 identities, 31 files. This also closes an
entry left open under type 150: *"`field 1` = 4 appears on exactly one slot in
the corpus, group A's first, and is still unexplained"*. It is `Orchestre`'s
slice length, and `Orchestre` was already carrying four detached fixtures before
this session started.

### What 151 holds

Four items were frozen across 21 files; the fifth is new:

| | `f2` | `f3` | `f4` |
|---|---|---|---|
| items 0–3 (`Orchestre`) | 32767 | 45546 / 41287 / 33095 / 33750 | 35716 / 35716 / 32767 / 34733 |
| item 4 (`Ceiling`, new) | 32767 | **37027** | **16383** |

Read as `v / 65536`: `f2` is **50 % on all five**, `f3` runs 50.5 – 69.5 % and
the new one is 56.5 %, `f4` runs 50 – 54.5 % and the new one is **25 %** — well
outside the band the four old ones occupy.

Three 16-bit fractions per detached fixture, and the record's population tracks
a feature that positions fixtures individually. `f3` and `f4` are the two that
move. **Which is PAN and which is TILT is not decided by the corpus**, and
neither is which fixture each item belongs to.

### The discriminator, published before measuring — **[planned]**

`Ceiling` recalled on group A. Five of the six lyres must hold the group
position — tilt **142, 142, 77, 77, 127, 127** — and exactly **one** must differ from
it. That one is the detached fixture, and its tilt names the field:

| If TILT is… | lyre @ 0 or 16 | @ 32 or 48 | @ 64 or 80 |
|---|---|---|---|
| `f4` = 25 % | **36** | **19** | **32** |
| `f3` = 56.5 % | **80** | **44** | **72** |

The two hypotheses are 40 to 60 DMX steps apart on every band, so one capture
separates them and identifies the detached lyre at the same time. Under
`f4` = TILT, its pan (`f3` = 56.5 %) would read 171, 165, 181, 181, 170, 170
depending on which lyre it is.

## POS-04 — record 151 decoded end to end — **[device-confirmed]**

Two photographs of the `POSITION` editor on group A's `Ceiling` settled it
without any measurement.

The second screen is the **group** view: `PAN 50 %`, `TILT 100 %`,
`FOCUS OFFSET 0 %`, `FAN | CROSS 50 %` — which is exactly `150[A][Ceiling]`
(`f6` = 32768, `f7` = 65535, `f4` = 32768, `f3` = 32768). Four fields, four
matches, and an independent confirmation of the type 150 layout.

The first screen is the **detached fixture** view: `FIXTURE | ON — Lyre Z 1`,
`PAN OFFSET 13 %`, `TILT OFFSET −50 %`, `FOCUS OFFSET 0 %`.

### The fields, and the sign convention

They are **signed offsets**, using the same encoding as `150.f4`:
`percent = (v − 32768) / 32767`.

| Field | Screen | Stored | Decoded |
|---|---|---|---|
| `151.f2` | `FOCUS OFFSET` | 32767 | **0 %** |
| `151.f3` | `PAN OFFSET` | 37027 | **13 %** |
| `151.f4` | `TILT OFFSET` | 16383 | **−50 %** |

Three for three, to the unit. And the four `Orchestre` entries, frozen across 21
files, decode to whole percentages under the same rule — pan **39, 26, 1, 3 %**
and tilt **9, 9, 0, 6 %** — where any wrong convention would scatter them.

`tools/wpj_codec.py` names them `focus_offset`, `pan_offset`, `tilt_offset`, and
151 leaves the passthrough list. Two of the three opaque record types are now
down to 130 and 161.

### Retraction — the POS-03 prediction was built on the wrong model

POS-03 published a DMX table on the assumption that 151 holds **absolute
positions**, predicting a tilt of 36 / 19 / 32 under `f4` = TILT. It does not:
`f4` is an **offset**, and the value is negative. The prediction is withdrawn
before it was ever measured.

Corrected: `Ceiling` puts the group at TILT 100 %, so the detached lyre sits at
`100 − 50 = 50 %` and its pan at `50 + 13 = 63 %`. Because the mapping through
the travel limits is linear, adding the offset before or after it gives the same
answer — the two models are indistinguishable here, and that is worth knowing
before an experiment is designed to tell them apart.

If `Lyre Z 1` is the fixture at DMX 0, recalling `Ceiling` should now read
**tilt 71** on channel 1 where POS-02 measured 142, and **pan 176** on channel 0
where it measured 167. The other five lyres must be unchanged. That capture
would also identify which physical lyre the firmware calls `Lyre Z 1` — an
ordering the file has not yet been shown to carry.

## POS-05 — the detached lyre found, and the model closed in 16 bits

`Ceiling` recalled after the detach. **Four channels changed in the whole
2048-channel universe: 0, 1, 2, and 3.** Everything else was byte-identical to
the POS-02 capture.

| Lyre @ DMX | pan before → after | tilt before → after |
|---|---|---|
| **0** | 167 → **176** | 142 → **71** |
| 16, 32, 48, 64, 80 | unchanged | unchanged |

Predicted 176 and 71 from `PAN OFFSET +13 %` and `TILT OFFSET −50 %` against a
group at PAN 50 % / TILT 100 %. **Both exact.**

So **`Lyre Z 1` is the fixture at DMX 0**, the first one — and the entry order
of record 151 now has one anchor. One lyre detached, one lyre moved, five
untouched: the offsets apply per fixture and nothing leaks to the group.

### Channels 2 and 3 are the fine pair, and that fixes the model

The `ZQ02244` profile's first four channels carry `110.f4` = **1, 2, 1, 2** —
pan, tilt, pan, tilt. Channels 2 and 3 are the **fine** halves, and they moved
together with the coarse ones, which is why exactly four channels changed.

Reading the pair as one 16-bit value shows the earlier ±1 misses for what they
were — **rounding twice**. The limits are stored as bytes but applied on the
full 16-bit scale:

```
borne16(f) = f / 255 × 65535
DMX16      = borne16(f5) + pct × (borne16(f6) − borne16(f5))
coarse     = DMX16 >> 8        fine = DMX16 & 0xFF
```

| | Predicted 16-bit | Measured |
|---|---|---|
| pan, group at 50 % (POS-02) | 42919 | **42918** |
| pan, detached at 63 % | 45191 | **45190** |
| tilt, group at 100 % | 36494 | **36494** |
| tilt, detached at 50 % | 18247 | **18246** |

Within one part in 65536, and the coarse byte is exact every time. `142` is not
`142/256` of full scale but `142/255` — that single choice is what turns 36494
from an approximation into the measured value.

Re-scored against all three captures the coarse predictions are **tilt 12/12,
pan 11/12**, the lone miss still `Crowd` on the lyre at DMX 32. The tilt column,
which carries no `FAN` ramp, has never missed once across 18 predictions.

### What is still not in the file

The capture named `Lyre Z 1` by elimination, not by reading it. **Nothing in the
project has been shown to map a 151 entry to a fixture** — the slice gives the
count and the order, but not the identity. `Orchestre`'s four entries are four
of six lyres, and which four is unknown. Detaching a second, known fixture on a
slot with an empty slice would settle whether the order is the fixture index,
the DMX address, or the `115.f6` display order.

## POS-06 — `151.f1` is the fixture index, and it was there all along

A second detach, on group A's `Crowd`, with a large `TILT OFFSET`. Version
1787670974706 → 707. Three records moved: `150` gained the slice on `Crowd`,
`151` gained a sixth entry, and `115` picked up `f6 = 18` on **all twenty**
fixtures at once.

### The mapping was in the file from the first dump

```
Orchestre  offset 0, 4 entries   f1 = 2, 3, 0, 1
Ceiling    offset 4, 1 entry     f1 absent = 0
Crowd      offset 5, 1 entry     f1 = 2
```

`151.f1` is the **fixture index**, absent meaning fixture 0. `Ceiling`'s entry
carries no `f1`, so fixture 0 — the lyre at DMX 0, which is exactly the fixture
POS-05 identified by watching four channels move. The measurement and the field
agree, and the field did not need the measurement.

`Orchestre`'s four entries are fixtures **2, 3, 0, 1** — the lyres at DMX 32,
48, 0 and 16, stored in neither index nor address order. That is why the slice
needs an explicit index rather than an implied position.

**Retracted**, from POS-05, written earlier today: *"Nothing in the project has
been shown to map a 151 entry to a fixture — the slice gives the count and the
order, but not the identity."* It does, through `f1`. The very first dump of
this record printed `{"f1": 2, ...}, {"f1": 3, ...}, {...}, {"f1": 1, ...}` and
that reading called `f1` an item index, noting it "was not in order" — the
disorder was the answer, not a curiosity. A field whose values are a permutation
of small integers, on a record with no other identifier, deserved one more
question.

`tools/wpj_codec.py` names it `fixture`; `tranches_151` now also checks that
every `f1` is a valid fixture index — 11 identities, 32 files.

### `115.f6` = 18 on every fixture

The field reappeared simultaneously on all twenty fixtures, having been absent
since before this session. Corpus values are 231, 232, 110, 4 and now 18 — one
value per project, replicated per slot, never varying between fixtures of the
same file. It is the "global stored per slot" shape already noted on `115.f6`/
`f7`, and this save re-stamped it. **[observed]**, and it carries no per-fixture
information.

### The next prediction, published before measuring — **[planned]**

`Crowd`'s new entry is fixture **2**, the lyre at DMX 32, with `PAN OFFSET 0 %`
and `TILT OFFSET +91 %`. Recall `Crowd` and only channels 32, 33, 34, 35 should
differ from the POS-01 capture.

Its group tilt is 70 %, so the offset asks for **161 %**. Two outcomes, and they
are far apart:

| | tilt on channel 33 |
|---|---|
| clamped at 100 % | **77** |
| not clamped, wrapping or overflowing | anything else |

The pan is the second question, and it is independent. `Crowd` has `FAN = 70 %`,
which put fixture 2 at 46 % of its band — DMX **176**. With a zero pan offset:

| | pan on channel 32 |
|---|---|
| the fan still applies to a detached fixture | **176** |
| detaching removes it from the fan | **178** |

One capture answers both.

## POS-07 — the position model, closed — **[device-confirmed]**

`Crowd` recalled after the second detach. **Two channels changed in 2048: 33 and
35** — the tilt pair of the lyre at DMX 32, which is fixture 2, which is exactly
what `151[5].f1` says. Everything else identical to POS-01.

### Both questions answered

| | Predicted | Measured |
|---|---|---|
| tilt, offset asking for 161 % | **77** if clamped at 100 % | **77** |
| pan, zero offset | **176** if the fan still applies | **176** |

**The offset is clamped**, and in 16 bits the agreement is exact rather than
approximate: `borne16(77)` = `77/255 × 65535` = **19789**, and the measured pair
`(77, 77)` is **19789**. Not one part off.

**Detaching does not remove a fixture from the fan.** Fixture 2 sat at 46 % of
its band under `FAN = 70 %` before the detach and sits there still — 45072
measured against 45073 predicted. The offset stacks on top of the group value,
fan included; it does not replace it.

The pan channels did not move at all, which is the strongest form of the second
answer: a zero offset really is zero, and the two axes are independent.

### The whole model

```
pct_group(k) = (1 − FAN) + k × (2·FAN − 1) / (n − 1)     pan, k = fixture rank
pct_group    = TILT                                       tilt
pct          = clamp(pct_group + offset, 0, 1)            offset from 151, signed
borne16(f)   = f / 255 × 65535                            f = 106.f5 or f6
DMX16        = borne16(f5) + pct × (borne16(f6) − borne16(f5))
coarse       = DMX16 >> 8         fine = DMX16 & 0xFF
```

Every term measured, none fitted. Across four captures and 24 predicted
channels: **tilt exact everywhere**, pan exact everywhere but one — `Crowd` on
the lyre at DMX 32 in POS-01, where the fan ramp lands on 175.4 and the device
emits 176.

From a project file alone, the DMX output of a recalled position is now
computable for any fixture: its group's `FAN`/`PAN`/`TILT` from record 150, its
rank in the group from `115.f4` and the address order, its per-fixture offsets
from record 151 through the `150.f1`/`f2` slice, and its travel limits from
`106.f5`/`f6` found through the role table. Six records, one formula.

## The preset's per-group arrays — thirteen of them — **[correlated, 32/32]**

Sweeping every length-delimited field of every record for one that decodes to
exactly **8 packed varints, always**, returns thirteen fields, and all thirteen
are in record 165:

```
f3   f7   f14  f17  f23  f27  f28  f29  f30  f32  f33  f34  f35
```

Four were already named — `f17` dimmers, `f28` positions, `f29` gobos, `f30`
colour pattern. The other nine are now **known to be per-group** even where
their meaning is not, which is a real constraint rather than a label: it says
`f3`, `f7`, `f14`, `f23` and `f27` are eight values indexed A–H, not scalars and
not blobs. `tableaux_par_groupe_165` checks the count on every preset of every
file — 12 identities, 32 files. It is not vacuous: a wrong varint split, or a
field read as a scalar, changes the count immediately.

Nothing outside 165 is a fixed 8-array. Record 160's `f1` and `f8` reach 8 on
115 of their occurrences but drop to 1 or 2 on others, so they are *sometimes*
per-group; `116.f9` is a 16-byte UUID that occasionally decodes to 8 varints by
coincidence, which is exactly the kind of false positive this sweep should
surface rather than hide.

### What that fixes about the never-exercised fields

`f3`, `f23` and `f27` are zero on all 2612 presets, and `f7` and `f14` are
non-zero on exactly one preset each — `Get Moving` carries `f7 = [0,1,0,0,0,0,0,0]`
and `70's Paradise` carries `f14 = [6]×8`. Under the array reading those two are
now legible: `f7` sets **group B only**, and `f14` sets **the same value on all
eight groups**. Both are one read-only DMX recall away from being named, and
both presets exist on the operator's controller.

### Record 160 — the macros are per-group too

```
Prism           f1 = [4]×6 + [1]×2      f8 = [50]×8
Prism rot OFF   f1 = [16]×6 + [4]×2     f8 = [128]×8
Frost           f1 = [4]×6 + [1]×2      f8 = [255]×8
blanc chaud     f1 = [1]×6 + [64]×2     f8 = [43]×8
ambre           f1 = [1]×6 + [64]×2     f8 = [93]×8
```

`f8` is one byte-wide value per group and `f1` one small power of two per group
— 1, 4, 16, 64, and 20 = 4 + 16 elsewhere, so a mask rather than an index. The
operator's own names line up with the values: `blanc chaud` and `ambre` differ
only in `f8` (43 against 93) while sharing an identical `f1`, which is what two
presets of the same control at two settings look like. `f7` resolves into
**eight pairs** `(v, 128)`, one per group, followed by four trailing bytes.
**[observed]** — the shape is clear, the semantics are not.

### Record 161 stays volatile

Seven consecutive saves of the experiment project moved record 161 exactly
**once**, and by one bit: the last byte of each of the three blobs went
`0xF0` → `0xB0`, at offsets 187, 188 and 189 — the end of each. The blobs are
not packed varints (`0xF0` would leave a dangling continuation), and the six
other saves left them untouched. Consistent with the existing reading: volatile
state, no show content, and nothing a writer must reproduce.

## F7-01 — a negative: recalling `Get Moving` cannot isolate `f7`

`Get Moving` recalled and captured. **110 channels differ** from the previous
capture, because a preset drives everything at once — beam FX, colour, gobo,
dimmer — and `f7` is one field among thirty. Nothing in the envelope can be
attributed to it.

Recorded so the experiment is not repeated. What the capture *does* show:

- The **ten pars of group B are byte-identical to one another** — dimmer 255,
  blue 255, red animated 0–167, `extra 3` animated 0–255. Whatever `f7 = 1` does
  on group B, it does not differentiate the fixtures within it.
- The pars have **no pan, tilt, gobo or wheel channels** — their eight mapped
  roles are dimmer, R, G, B, three extras and shutter. So `f7` on group B cannot
  be a position, a gobo or a wheel index, which removes the obvious candidates.
- The first lyre's channel 10 reads **70**, which is `f29 = 9` through the gobo
  palette — F29-01 measured exactly that, and it still holds.

Isolating `f7` needs a single-variable differential, and the control that writes
it is unknown: no screen seen so far exposes anything that varies per group with
one preset in the whole corpus carrying it. `f14` is in the same position, on
`70's Paradise`. Both stay **[observed]**: eight values indexed A–H, contents
unattributed.

## F4-03 — `f4` gates the engines, and `f16`'s slice 2 is the Beam FX

Crossing the preset's `f4` with the `f16` engine masks makes both fields say
something the other could not.

| `f4` | binary | engines seen active | count |
|---|---|---|---|
| 8 | `00001000` | **0** only, or none | 640 |
| 5 | `00000101` | **1** only, or none | 640 |
| 17 | `00010001` | **2** only, or none | 638 |
| 255 | `11111111` | any combination | 693 |

The implication holds on every preset of every file, and it is one-directional:

```
engine 0 active  ⇒  f4 bit 3        Color FX
engine 1 active  ⇒  f4 bit 2        Move FX
engine 2 active  ⇒  f4 bit 4        Beam FX
```

`f4_autorise_les_moteurs` checks it — 13 identities, 32 files. A page may permit
an engine no preset on it uses, which is why the converse fails and why `f4`
reads as a **permission mask** rather than a record of what is running.

### Slice 2 of `f16` is the Beam FX — **[correlated]**

Slice 0 was pinned to `color_fx_actif` and slice 1 to `move_fx_actif` by direct
equality. Slice 2 had no partner field. It is now named by exclusion that is not
hand-waving: it is active on **574 of the 638 presets whose `f4` is 17** — the
beam page — and on **none** of the 1280 presets of the colour and move pages. A
mask confined to the beam page, on a device whose third FX engine is Beam FX.

That leaves `f16` with three named engines out of twelve, slices 5 and 7
unexplained, and slice 11 a per-project constant.

### What `f4` bit 0 still is not

Bit 0 is set on the move page (`5` = bits 0 + 2) and the beam page
(`17` = bits 0 + 4), and clear on the colour page (`8` = bit 3 alone). Under the
permission reading it is a fourth capability that movement and beam presets both
need and colour presets do not — and the pars, which carry no pan, tilt, gobo or
wheel channel, are exactly the fixtures a colour preset addresses. Nothing in
the corpus separates the candidates, and bits 1, 5, 6 and 7 are still never seen
outside 255.

### `f16` slices 5 and 7 — **[correlated]**

**Slice 7 is the strobe engine.** It is active on exactly **two** presets in the
whole corpus, in all 32 files: `Fire!` (id 17) and `Strobe` (id 76). Two presets
whose names both describe a flicker, and nothing else in 2446 presets. The W1
has a dedicated `STROBE` key and record 102 carries a strobe speed, so a
twelfth-of-a-record mask that only those two presets raise is that engine.

**Slice 5 is active on every preset, always 255.** Under the permission reading
that is an engine every preset is allowed to drive on every group — which is
what the **static layer** is: every preset carries a static colour (`f31`), a
position (`f28`) and a gobo (`f29`), and those are never optional. **[hypothesized]**,
since a field that never varies cannot be pinned by the corpus alone.

`f16` now reads: 0 Color FX, 1 Move FX, 2 Beam FX, 5 static (hypothesised),
7 strobe, 11 a per-project constant, and 3, 4, 6, 8, 9, 10 never non-zero.

## The opaque prefix, mapped — **[correlated, 32/32]**

The 44 bytes at offsets 20–63 were carried through verbatim and never read past
offsets 40 and 50. Across seven consecutive saves of one project **only byte 40
ever moved**, and across three different projects only three regions differ at
all:

| Offset | Content | Status |
|---|---|---|
| 20–35 | the project **UUID**, 16 bytes | device-confirmed |
| 36–39 | `15 2b 10 c0` — identical in every file | constant |
| 40–47 | little-endian `uint64`, the **project version** | device-confirmed |
| 48–49 | `01 f9` — identical in every file | constant |
| **50** | the **schema version** | correlated |
| 51 | `00` in every file | constant |
| 52–63 | `02 be e8 1c a2 6c cb 54 6d c7 b6 ec` — identical in every file | constant |

### Byte 50 is the schema version

| Schema | Files | `165.f32`–`f35` | Record 151 |
|---|---|---|---|
| **8** | 1 (`rig-c`) | absent | present |
| **10** | 11 | present, 11/11 | 2/11 |
| **11** | 20 | present, 20/20 | 20/20 |

The correlation is total, and it settles a reading that had only been inferred:
`f32`–`f35` are **schema-10 additions**, which is why the one project authored
at schema 8 carries nothing there. `schema_du_prefixe` checks both the four
constant regions and the schema ↔ `f32` equivalence — 14 identities, 32 files.

Schema **11** is this firmware's, and it is the one that carries the detach
feature: every schema-11 file has record 151, and only schema-11 files have gone
past four detached entries. A writer must therefore not raise the schema byte
without also emitting what that schema requires.

The four constant regions are worth stating as constants rather than leaving
them unread: 24 of the 44 prefix bytes carry no project information at all, and
any change there is a format change, not a project change.

## Record 110 `f5` — the coarse/fine link — **[correlated, 1100/1100]**

`110.f5` had 31 distinct values and no reading. It is the **index, within the
profile, of the channel this one belongs to**: a principal channel points at
itself, and a **fine** channel points at its coarse half.

The rule holds on every channel of every profile of every file, with **no
exception**:

```
f5 ≤ j                                   never points forward
110[offset + f5].f4 == 110[offset + j].f4    same feature as the channel it points at
```

959 channels point at themselves; the 141 that do not are exactly the fine
halves, and they name themselves by doing so:

| Profile | Position | `f5` | Feature |
|---|---|---|---|
| `ZQ02244`, 16 ch | 2 | **0** | pan — the fine half of channel 0 |
| `ZQ02244`, 16 ch | 3 | **1** | tilt — the fine half of channel 1 |
| `ZQ02344`, 8 ch | 1 | **0** | pan fine |
| `ZQ02344`, 8 ch | 3 | **2** | tilt fine |

POS-05 found the fine channels by watching four DMX channels move together. The
file said so all along, and says it for **every** profile including the ones the
operator does not own. `canal_principal_110` checks it — 15 identities, 32 files.

A show generator can now emit a 16-bit pan without guessing byte order or
adjacency: the coarse channel is the one whose `f5` equals its own index, and
its fine half is whichever channel points back at it.

## Two more negatives

### `f18` is not a strided bit field

`f16` turned out to be twelve 9-bit slices, so `f18` was cut the same way. It
produces nothing: slice 0 simply restates the first byte, slices 1 and 3–7 are
always zero, and slice 2 is non-zero on a single preset in a single file. The
construction that unlocked `f16` does not apply here. `f18[0]` keeps its eight
values — 1, 3, 8, 9, 11, 16, 19, 24 — on movement-flavoured presets, and stays
**unattributed**.

### The FX submessages — shape, not meaning

The six FX slots divide cleanly, and the "2" slots are near-uniformly defaults:

| | `f3` | `f5` | `f6` | `f8` | `f9` | default when idle |
|---|---|---|---|---|---|---|
| beam | — | — | ✓ | ✓ | ✓ | `f6` 25, `f8` 100, `f9` 50 |
| colour | — | ✓ blob | ✓ | ✓ | ✓ | `f5` `2000`, `f6` 20, `f9` 50 |
| move | ✓ | ✓ byte | ✓ | ✓ | ✓ | `f3` 50, `f5` `00`, `f8` 100, `f9` 50 |

`beam_fx2` and `move_fx2` are **one single value each across all 2612 presets**
— secondary slots nobody uses — while `color_fx2` varies on 23. `f3` exists only
on movement, which is what a field like amplitude would do. `f8` defaults to 100
and `f9` to 50 in every family, so they are a full-scale quantity and a centred
one respectively.

That narrows the size/fade/phase attribution without settling it: the corpus
gives the defaults and the shape, and only a measurement can say which name goes
where. Recorded so the next attempt starts from the defaults rather than from
the value lists.

## Record 120 — what it is not — **[observed]**

Three readings tested and all three refuted:

| Reading | Test | Result |
|---|---|---|
| live channel state | compare `120.f1` to the measured DMX envelope | in range on **66–71 of 215** channels, across three different captures |
| a snapshot that follows saves | compare across seven consecutive saves | **byte-identical** from version 701 to 707 |
| derived from the profile | compare the block of each fixture to another of the same profile | differs on **397** fixtures |

So it is frozen, per fixture, and not recomputable — a writer must preserve it,
and no experiment on the show side will move it.

The channels where `120.f1` *does* match the measured DMX are the ones no preset
was driving: on the first lyre, channel 6 reads 241 in both and channel 7 reads
220 in both, while pan and tilt disagree because the preset was moving them.
**[hypothesized]** `120.f1` is each channel's **resting value** — what the
controller emits when nothing drives it. One capture with every preset released
would settle it, and it is the only remaining reading that fits all three
negatives.

## Where the corpus stops

Everything below now needs the device; the corpus has been swept field by field
and has nothing further to say about them.

| Open | Why the corpus cannot close it |
|---|---|
| `165.f4` bit 0, and bits 1, 5, 6, 7 | bit 0 is set on the move and beam pages and clear on the colour page; no factory preset separates the candidates, and the other four are never seen outside 255 |
| `165.f18` | eight values on movement presets; not a strided bit field, not masked by `f10` |
| `165.f3`, `f7`, `f14`, `f23`, `f27` | per-group arrays, zero everywhere except `f7` and `f14` on one preset each |
| `f16` slices 3, 4, 6, 8, 9, 10 | never non-zero |
| FX `f6`/`f8`/`f9` — size / fade / phase | defaults known, attribution not |
| `102.f11` = 100 | one value in every file |
| `106.f1`/`f3` = `(0, 127)` on pan and tilt | flat on all 206 fixtures; the fine-channel hypothesis is refuted — six pan/tilt roles with **no** fine channel carry 127 too |
| `110.f4 = 18` / `111.f3 = 41` | a feature absent from the table, on moving heads only |
| `116.f6` | 1 on `6x18W` and `MH-100 BEAM`, 3 on `LASERBAR`, 0 elsewhere |
| record 120 | see above |
| record 130 | byte-identical in all 32 files |
| record 161 | one bit moved in seven saves |
| MIDI mapping | never located |

## The vendor manual, read — several fields named at once

`Wolfmix W1 Reference Manual`, version 2.0, fetched from the manufacturer's own
distribution URL and read for the screens this registry had already
photographed. Nothing is reproduced here beyond field names; the document is
not redistributed.

### `f18` = the preset's Live Edit mask — **[correlated]**

The `LIVE EDIT` screen is **4 pages of 20 buttons**. Eighty buttons, and `f18`
is **10 packed varints = 80 bits**, the same byte-field construction as `f16`
and `f31`. Decoded that way, every preset in the corpus lands on plausible
button numbers and nothing else:

| Preset | Live Edits |
|---|---|
| `Aim`, `Candy Floss Swing`, `D A N C E`, `J U M P`, `Point to Point`, `Lights to the Siren` | 1, 2 |
| `Get Moving` | 1, 2, 5 — and 1, 20 in one file |
| `Runway` | 5 |
| `valse` | 1, 2, 4 → 1, 4 |
| page 5 slot 2 | 4, 5 → 4 |

**Out of 80 possible bits the corpus only ever sets 1, 2, 4, 5 and 20** — the
top of page 1, which is exactly what a factory preset set would use. A wrong
reading would scatter bits across the range.

This also explains why `f18` refused to correlate with `f10`: they are different
things. `f10`'s `LIVE EDIT` bit says *whether* the preset carries Live Edits;
`f18` says *which*. The manual is explicit that a preset stores "the parts of
the project" the toggles select, and Live Edits are one of those parts.

**Retracted**: the F18 entry's framing as "eight values on movement presets, not
a strided bit field". The strided reading was tried at 9 bits, `f16`'s stride,
and failed. The right stride is **1** — it is a flat bit field, and the
movement flavour of the presets was a coincidence of which factory presets
happen to use Live Edits.

### `f3`, `f7`, `f14`, `f23`, `f27` = the five gobo features — **[hypothesized]**

The `STATIC GOBO` screen carries a **per-group feature value**: its bottom row
reads `A ROTATE 6%  B ROTATE 6%  C ROTATE 6%  D ROTATE 6%`, and a toolbar
switches the feature between **Rotation, Prism, Focus, Zoom and Iris** — five
features, each a percentage, each per group.

Record 165 has exactly **five** per-group arrays with no meaning attached:
`f3`, `f7`, `f14`, `f23`, `f27`. The cardinality matches exactly, and the two
non-zero examples fit:

- `70's Paradise` carries `f14 = [6]×8` — the same value on all eight groups,
  which is what setting one feature with no per-group differentiation looks
  like, and `6` is the number the manual's own screenshot shows on `ROTATE`.
- `Get Moving` carries `f7 = [0,1,0,0,0,0,0,0]` — **group B only**, at 1 %.

Which array is which feature is **not** settled: the manual gives the five
names and the corpus gives five arrays, but only two are ever non-zero. Setting
`Prism` to a distinctive value on one group, then `Zoom` on another, names two
per save.

### Confirmations, and one negative closed

- **`f10`'s six toggles**, verbatim from the manual: `COLOR` includes Color FX
  **and static colours**, `MOVE` includes Move FX **and static positions**,
  `BEAM` includes Beam FX, `GOBO` and `LIVE EDIT` the corresponding parts, and
  **`OTHER` includes the group dimmer values**. That names `OTHER` — and record
  165's `f17`, already decoded as `dimmers`, is what it gates.
- **Record 151 is `Fixture Offset Mode`**, reached from the Position Picker. Its
  screen carries `PAN OFFSET`, `TILT OFFSET`, `FOCUS OFFSET` and a
  `FIXTURE | ON` selector — the three fields decoded in POS-04, under the
  manufacturer's own names, in the same order.
- **`110.f5`**: the Live Edit value grid lists channels as `01 Pan  02 Tilt
  03 uPan  04 uTilt` — the fine halves are named `uPan`/`uTilt`, which is the
  coarse/fine pairing that `f5` encodes.
- **The preset grid is 10 pages of 20**, so 200 presets, not 100. Preset ids run
  to 199.
- **Negative closed**: the `COLOR` line on the `PRESET EDIT` screen is the
  **colour of the preset's button in the matrix**, settable or `AUTO`. It was
  never expected to match `f31`, and the earlier entry recording that mismatch
  as a puzzle can rest. Which field stores it is still unlocated.
- **`Flash`** is a per-preset boolean set from the `PRESET EDIT` toolbar: the
  preset is triggered on press and the previous one recalled on release.
  Unlocated in the file.

Source: <https://storage.googleapis.com/nicolaudie-us-litterature/Release/wolfmix_w1_reference_manual_en.pdf>

## GOBO-01 — prediction, published before the download

The operator set all five `STATIC GOBO` features on **group A** — the only group
whose fixtures have gobos — to five distinct values:

```
Rotate 15    Prism 77    Focus 58    Zoom 96    Iris 55
```

Five different fields, five distinct values, one save. No two expected values
collide, and none of them appears in any of the five arrays today.

**Predicted**: exactly five per-group arrays change, and they are `f3`, `f7`,
`f14`, `f23`, `f27`. Each becomes `[v, 0, 0, 0, 0, 0, 0, 0]` with `v` one of
`{15, 55, 58, 77, 96}`, each used once. The assignment then names all five
features in a single differential.

**Named prediction**: `f14` = **Rotate** = 15, from `70's Paradise` carrying
`f14 = [6]×8` against the manual's `ROTATE 6 %` screenshot. If `f14` comes back
55, 58, 77 or 96 that inference is refuted and the array is whichever feature
the value names.

**The branch that would refute the whole hypothesis**: the static gobo features
may be *live* state that only reaches the file when a preset captures them. If
no preset's arrays move, the five values live elsewhere — record 145, or a
global — and the cardinality match was a coincidence.

### Measured — the prediction is refuted, and it is the branch that was published

Version 1787670974707 → **709**, two saves. **One record moved: 115.** Record
165 did not change at all, and none of the five arrays moved.

None of `15`, `55`, `58`, `77` or `96` appears anywhere new in the file — their
byte counts across the whole body are identical before and after, except `15`
which went *down*. The five settings did not reach the project.

**So the static gobo features are live state**, exactly the refutation branch
written before the download. A project save does not capture them.

This does **not** refute the five-arrays hypothesis; it refutes the experiment.
`f3`, `f7`, `f14`, `f23`, `f27` are still five per-group arrays against five
per-group features, and `70's Paradise` still carries `f14 = [6]×8`. What the
save showed is that the path from screen to file runs **through a preset**: the
manual says `GOBO` in the content mask "will include the corresponding parts of
the project", so a preset must capture the state first.

**Next experiment**: set the five features, then **SHIFT + tap a preset**, which
the manual says overwrites that preset with the current controller state, then
save the project. Page 5 slot 3 is the expendable one. The prediction above
carries over unchanged.

### `115.f6`/`f7` move on every save — **[observed]**

The only change this save produced: all twenty fixtures went from `f6 = 18` with
no `f7`, to `f6 = 232, f7 = 113`. Identical on every fixture, including the ten
pars and the fogger, none of which has a gobo channel.

Corpus values are `f6` ∈ {4, 110, 231, 232, 18} and `f7` ∈ {20, 113, 187, 218},
always one pair per file replicated across every slot. They changed here while
**nothing in the patch did**, so they track the save rather than the patch —
consistent with the "global stored per slot" shape noted long ago, and now with
a stronger claim: a writer must expect them to be rewritten by the device and
must not read anything per-fixture from them.

## GOBO-02 — the five gobo features, named — **[device-confirmed]**

The corrected experiment: the five features set on group A, then **SHIFT + tap**
on page 5 slot 3 to overwrite that preset with the controller's live state, then
one project save. Version 709 → 710, one save, records 115 and 165.

**Five for five, each value in exactly one field:**

| Screen feature | Set to | Field | Read back |
|---|---|---|---|
| `ROTATE` | 15 | **`f14`** | `[15, 0, 0, 0, 0, 0, 0, 0]` |
| `FOCUS` | 58 | **`f32`** | `[58, 0, …]` |
| `PRISM` | 77 | **`f33`** | `[77, 0, …]` |
| `ZOOM` | 96 | **`f34`** | `[96, 0, …]` |
| `IRIS` | 55 | **`f35`** | `[55, 0, …]` |

Group A only, zero on the seven others — which is what setting one group does,
and which no other reading of these fields would produce. The codec names them
`gobo_rotate`, `gobo_focus`, `gobo_prism`, `gobo_zoom`, `gobo_iris`.

### The named prediction held, the field list did not

**`f14` = Rotate = 15 was published before the download** and is exact. It was
derived from `70's Paradise` carrying `f14 = [6]×8` against the manual's
`ROTATE 6 %` screenshot — a one-preset corpus observation and a vendor
screenshot, and they were enough.

**Retracted**: the prediction that the five features are `f3`, `f7`, `f14`,
`f23`, `f27`. Only `f14` is. The other four are **`f32`–`f35`**, which this
registry had filed as "a schema-10 addition, zeroed by the upgrade" and never
looked at again. The cardinality argument picked the wrong five: it counted the
arrays with *no* attribution and missed that `f32`–`f35` had a *provisional*
one, which is a worse failure than having no idea — it was a label standing in
for a reading.

The tell was there and unread. `f32`–`f35` carry `50 / 0 / 100 / 100` on
projects authored at schema 10, and under the names just measured that reads
**Focus 50 %, Prism 0 %, Zoom 100 %, Iris 100 %** — exactly the defaults a
lighting desk would ship. Four numbers that mean nothing as an opaque quadruple
and are obvious as soon as the fields have names.

`f3`, `f7`, `f23` and `f27` stay unattributed. `f7` did move in this save, to
`[0, 1, 0, 0, 0, 0, 0, 0]` — group B at 1, the same value `Get Moving` carries.

### Side confirmations from the same capture

- `color_fx_actif` went `[0]` → `[255]` and `f16` slice 0 went `0` → `255` **in
  the same save**, which is the duplication ACC-03b violated.
- `f18` came back `[3, 0, …]` = Live Edits **1 and 2** — the operator had two
  live edits running, and the mask captured exactly them.
- `gobos` went `[1]×8` → `[9, 255×7]`: gobo 9 on group A, cleared elsewhere,
  the 0-based index with 255 as "none" that F29-01 measured.

## The FX screens, from the manual — **[correlated]**

The `COLOR FX` screen has four encoders: **Speed**, **Phase | Order**, **Size**,
**Fade**. The `MOVE FX` screen has the same four, but two of them carry a second
mode: **Size | Fan** and **Fade | Flick**. That is the asymmetry the corpus
showed as an extra field: move FX submessages carry `f3` and colour ones do not.

### `move_fx.f5` = the effect's position — **[correlated]**

The manual: tapping one of 16 light-green matrix buttons "adjusts the position
of the entire effect to the top left, top, top right, right, bottom right,
bottom, bottom left, left and center" — **nine** positions.

`move_fx1.f5` is a single byte and takes only `0, 1, 5, 6` across **2778
occurrences**, never 9 or above. Nine slots, four ever used, none out of range.

### `color_fx.f5` = the effect's colour mask — **[correlated]**

The manual: tapping one of the 16 coloured matrix buttons "adds and removes the
corresponding color from the effect". `color_fx1.f5` is 2 to 4 bytes and
ACC-05 already wrote `[3, 0]` into it expecting pads 1 + 2. Both readings agree:
it is a pad mask over the 16-pad ColorFX palette of record 135.

### What is now constrained, and what is not

Speed is already three named fields — `vitesse`, `bpm_division`,
`speed_source` — matching the encoder's Clock / BPM / Audio sync modes. That
leaves `f6`, `f8`, `f9` for **Phase, Order, Size, Fade** on colour, plus `f3`
and the Fan/Flick modes on move.

Two anchors from the defaults:

- `f8` defaults to **100** in all three families, and `SIZE` is the property a
  desk ships at 100 %.
- `f3` exists **only on move** and defaults to **50** — and 50 % is the neutral
  value of `FAN` everywhere else in this format, as POS-02 measured on the
  position picker's own `FAN`.

Both are **[hypothesized]**. `f6` and `f9` remain unattributed between Phase,
Order, Fade and Flick, and `PHASE 0 %` being the neutral means the phase field
would simply be **absent** on most presets — which is the shape of `f6` on move,
present on only a fraction of them.

## The Flash screens and Settings — type 102 corroborated, `f11` narrowed

Every flash screen's parameters, from the manual, against the decoded record:

| Screen | Parameters | Record 102 |
|---|---|---|
| `WOLF` | release mode **only** | `f4`, `f10` mask |
| `STROBE` | speed, 1 – 100 % | `f9`, `f8` mask |
| `BLINDER` | fade-out 0 / 0.2 / 0.5 / 1 / 2 s | `f2`, `f3` mask |
| `SPEED` | Freeze / 0.5× / 2× / 4× / 8× | `f7` |
| `BLACKOUT` | release mode **only** | `f1` mask |
| `SMOKE` | intensity + fan speed | `f5`, `f6` |

Six screens, every parameter accounted for, and the two screens with no
parameter are exactly the two with no value field. The `Settings` list confirms
the asymmetry from the other side: it offers `Exclude Wolf`, `Exclude Strobe`,
`Exclude Blinder` and `Exclude Blackout` — **four** exclusions, which is why
record 102 has exactly four mask fields and none for SPEED or SMOKE.

**`f11` is not on any flash screen.** Combined with the measurements already
recorded — not SMOKE, not BLINDER, not WOLF, not STROBE speed, not master
brightness — the flash side is now exhausted.

**New candidate**: `Settings → General → Button brightness`, which the manual's
own screenshot shows at **100 %**. It has never been tested, unlike the master
dimmer. One save after changing it settles it. `Display brightness` (45 % in the
screenshot) and `Audio input level` (50 %) are the two neighbours to check if it
fails.

### Two settings that gate what a preset stores

- **`Store group dimmers in Preset`** — when off, the group dimmer values are
  not recalled by the preset. That is the setting behind the content mask's
  `OTHER` bit, which the manual defines as "the group dimmer values".
- **`Include Flash buttons in Preset`** — when set, the state of the flash
  buttons is stored in the preset. So a preset carries flash state, and nothing
  in record 165 has been attributed to it yet. Six flash buttons, and `f4` has
  **four** unexplained bits (1, 5, 6, 7) plus bit 0.

### MIDI mapping is MK2 and higher — lead L5 does not apply to this hardware

The `Mappings` screen maps "a DMX or MIDI (MK2 and higher) command". The
operator's controller is a **MK1**, so no MIDI map can exist in this corpus, and
L5's premise — that the map must live in the file — cannot be tested here. The
**DMX** mapping side does exist on MK1. Categories are `Group Dimmer`, `Preset`,
`Preset Page`, `Flash` and `General`.
