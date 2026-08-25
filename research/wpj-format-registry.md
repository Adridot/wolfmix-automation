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
| 3 | len ×100 | 100 | **presets** (sous-msg : champ1=nom, champ2=varint 1000, champ4=blob 135 o) | correlated (100 = 5 pages × 20 slots ? à valider) |
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

**Experiment FX-01, 2026-08-25, W1 serial withheld, fw 2.0.18.**
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

Still open: **PAN**, **FOCUS OFFSET** and **CROSS** share `f4`, `f6` and `f8`,
all sitting at 32768 for group C. FOCUS OFFSET displays **0 %** while its field
holds 32768, so that value is **signed with 32768 as zero**, unlike TILT and FAN.

**One screenshot resolves all three.** Group A's `<group-A name>` is the only slot in
the corpus where these fields disagree: `f4` = 65535, `f6` = 8519 (13 %),
`f8` = 32767. SHIFT + `<group-A name>` on group A and reading PAN, FOCUS OFFSET and
CROSS off the screen assigns each field in one shot.

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
