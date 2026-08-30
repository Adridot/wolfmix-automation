# Registre du format .wpj — hypothèses et preuves

Statuts : `observed` (vu dans les octets) → `hypothesized` (interprétation
proposée) → `correlated` (cohérent sur ≥2 fichiers indépendants) →
`validated` (confirmé par expérience différentielle) → `device-confirmed`
(accepté par le W1). Jamais de valeur inventée ; ambiguïté = candidats listés.

Corpus de preuve : `corpus/SHA256SUMS` (57 fichiers, régénéré le 2026-08-27).
Les expériences ACC-* ont tourné sous WTOOLS 1.6.3 ; la machine est passée à
WTOOLS 2.0.2 beta (build 248) depuis, et chaque entrée porte sa propre version —
voir `versions.md`.

## Trois variantes de conteneur observées localement

### Variante C — protobuf nu (1 fichier, `rig-C1`)
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
- **[observed]** Octets 20–63 : zone d'en-tête contenant notamment un motif
  répété qui reprend la moitié de l'UUID du nom de fichier —
  **[hypothesized]** numéro de série W1. Ni l'un ni l'autre n'est reproduit ici.
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
| 2 | len | 1 | **nom du projet** UTF-8 | correlated |
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
Request: `GET_PROJECT` on `<experiment-uuid>`
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
`<nom utilisateur>`, and the four factory MOVE presets id 56–59 (`D A N C E`, `J U M P`,
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

> **Fired 2026-08-26** — the result is the very next section, `Measured` (line
> 1287, F29-01): both points exact, `f29` is the **0-based** static gobo index,
> `device-confirmed`. The `[planned]` marker above is kept for the record; the
> protocol below is what was actually run.

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
3. **`f8` is a *group* name.** The experiment project names slot 0 `<group-A name>` and
   slot 1 `<group-B name>` — the operator's own names for their moving-head group and
   their par group, not category labels the firmware would ship.

`rig-c-bug`'s seventh profile at slot 3 is a `LASERBAR`: a fourth group, `D`.

### What this unlocks, and what is still missing

A show generator can now target a group: read `115[*].f4`, and the eight slots
of `f28`/`f29`/`f30`/`f31` in every preset address exactly those fixtures. The
group *names* are readable too, from `125[i].f8`.

Still open, and cheap to settle with one photograph: whether the device's
group A screen displays the name `<group-A name>`. That would take the slot → letter
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

> **Fired 2026-08-26** — and it did not settle what it set out to settle. F4-01
> (line 1909) refuted the enumeration and read `f4` as a bitmask; F4-02 (line
> 1999) then showed the **content mask is `f10`, not `f4`**, and F4-01's bit
> assignments were retracted with it (line 2048). `f4` came back at F4-03 (line
> 2949) as a **permission mask over the engines**. The screens this protocol
> asked for were read; the field they were read against was the wrong one.

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
| page 5 slot 1, `<nom utilisateur>` | `GOBO` | absent | **8** = bit 3 |
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
| Pinned by | three screens | three screens | four screens | the `<nom utilisateur>` write | the slot-2 write | slot 3's stored 32, read on the screen |

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
cleared. `<nom utilisateur>` did lose its group-A gobo (`f29[A]` 9 → 255) in the same save,
but across the corpus `f10` bit 3 and an all-255 `gobos` array agree on only
595/2197 presets, and bit 0 versus an empty `f31` on 1693/2197. The `<nom utilisateur>`
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

> **Fired 2026-08-26, and confirmed twice since** — POS-01 (line 2417) measured
> `106.f5`/`f6` as the per-fixture travel limits on tilt, six for six. The same
> two fields were measured again on a different **role** on 2026-08-27: GEN-02
> found the group dimmer running through the identical formula,
> `DMX = f5 + (f17/255)·(f6 − f5)`, exact on seven points. A pair of bounds
> that holds on two unrelated roles is no longer a reading about tilt.

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
89** and the same pan as `Ceiling`. **`<group-A name>`**, PAN 13 % / TILT 23 %,
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
switching `GOBO` off on `<nom utilisateur>` took `f18[0]` from **11 to 0**, not to 3.

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
before   <group-A> f1 = 4              151 has 4 items
after    <group-A> f1 = 4              151 has 5 items
         Ceiling    f1 = 1, f2 = 4
```

`f2` is the offset, `f1` the length: `[0,4)` for `<group-A name>` and `[4,5)` for
`Ceiling` tile `[0, 5)` exactly. It is the **same (offset, length) couple** the
format uses in `105.f4`/`f7` into 106 and `116.f3`/`f2` into 110 — the third
instance of one construction, which is why it was recognisable at a glance.

`tranches_151` checks the tiling; 11 identities, 31 files. This also closes an
entry left open under type 150: *"`field 1` = 4 appears on exactly one slot in
the corpus, group A's first, and is still unexplained"*. It is `<group-A name>`'s
slice length, and `<group-A name>` was already carrying four detached fixtures before
this session started.

### What 151 holds

Four items were frozen across 21 files; the fifth is new:

| | `f2` | `f3` | `f4` |
|---|---|---|---|
| items 0–3 (`<group-A name>`) | 32767 | 45546 / 41287 / 33095 / 33750 | 35716 / 35716 / 32767 / 34733 |
| item 4 (`Ceiling`, new) | 32767 | **37027** | **16383** |

Read as `v / 65536`: `f2` is **50 % on all five**, `f3` runs 50.5 – 69.5 % and
the new one is 56.5 %, `f4` runs 50 – 54.5 % and the new one is **25 %** — well
outside the band the four old ones occupy.

Three 16-bit fractions per detached fixture, and the record's population tracks
a feature that positions fixtures individually. `f3` and `f4` are the two that
move. **Which is PAN and which is TILT is not decided by the corpus**, and
neither is which fixture each item belongs to.

### The discriminator, published before measuring — **[planned]**

> **Withdrawn before it was ever measured, 2026-08-26** — its own retraction is
> at line 2672. The table below assumes record 151 holds **absolute positions**;
> POS-04 (line 2640) decoded 151 as **offsets**, and the value in question is
> negative, so the predicted DMX is wrong on both branches. Kept as written,
> because a prediction built on the wrong model is the cheapest kind of lesson.

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

Three for three, to the unit. And the four `<group-A name>` entries, frozen across 21
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
count and the order, but not the identity. `<group-A name>`'s four entries are four
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
<group-A> offset 0, 4 entries   f1 = 2, 3, 0, 1
Ceiling    offset 4, 1 entry     f1 absent = 0
Crowd      offset 5, 1 entry     f1 = 2
```

`151.f1` is the **fixture index**, absent meaning fixture 0. `Ceiling`'s entry
carries no `f1`, so fixture 0 — the lyre at DMX 0, which is exactly the fixture
POS-05 identified by watching four channels move. The measurement and the field
agree, and the field did not need the measurement.

`<group-A name>`'s four entries are fixtures **2, 3, 0, 1** — the lyres at DMX 32,
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

> **Closed 2026-08-27** — settled by POS-07, line 2825 (`Crowd` recalled after
> the second detach: the only two channels that changed in 2048 were the tilt
> pair 33 and 35, tilt **77**, so the offset is clamped at 100 %; the pan
> channels did not move at all and channel 32 still read **176**, so detaching
> does not remove a fixture from the fan — both predictions exact). This
> protocol was fired as written.

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
| `<nom utilisateur>` | 1, 2, 4 → 1, 4 |
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

## Fixture Setup, from the manual — a read-only check for `106.f5`/`f6`

### `FIXTURE LIMITS` shows the travel limits as percentages

The screen carries exactly four values — `MIN PAN`, `MAX PAN`, `MIN TILT`,
`MAX TILT` — as percentages, with "push the encoders to reset these values to 0
or 100%". That is `106.f5`/`f6`, per fixture and per axis, in the vendor's own
words.

**Measured on the lyre at DMX 0: 52 %, 79 %, 0 %, 56 % — all four exact.**
`106.f5`/`f6` is now held by three independent routes: the retrospective group C
capture, the forward group A predictions of POS-01/02, and the manufacturer's
own screen. Predicted, if the screen shows `f/255`:

| Lyre @ DMX | MIN PAN | MAX PAN | MIN TILT | MAX TILT |
|---|---|---|---|---|
| 0 | **52 %** | **79 %** | 0 % | **56 %** |
| 16 | 52 % | **75 %** | 0 % | 56 % |
| 32, 48 | **59 %** | **80 %** | 0 % | **30 %** |
| 64, 80 | **50 %** | **79 %** | 0 % | **50 %** |

Four distinct pan pairs and three distinct tilt maxima across six fixtures.
Opening the screen on any one lyre checks the whole reading, with nothing
written.

### `min` above `max` is a documented shape, not an anomaly

The channel editor's own screenshot reads `Wheel Rot min 191 / Wheel Rot Max
128` — a minimum above its maximum, shipped in the manufacturer's
documentation. POS-04 read the two `ZQ02344`'s `f5 = 255, f6 = 198` on tilt as
an inverted axis; the format uses that inversion generally, and the
`FIXTURE LIMITS` toolbar has explicit **Invert Pan** and **Invert Tilt**
actions.

### Profiles carry beams, and `116.f6` is the candidate

A profile may have up to **512 channels** and **64 beams** — "the number of
independently controllable beams a fixture has" — and the channel editor's
fourth encoder assigns a channel to a beam.

`116.f6` takes 0, 1 and 3, and is 1 on the `6x18W` and the `MH-100 BEAM`, 3 on
the `LASERBAR`, 0 on everything else. **[hypothesized]** a beam count or index.
It does not simply equal the block count the registry recorded for the
multi-block fixtures — `LASERBAR` is 6 × 8 channels and carries 3 — so the
reading is not yet right.

### Channel types, named

The fixture builder lists channel types verbatim: `Pan  Tilt  uPan  uTilt  Cyan
Magenta  Yellow  Iris  Zoom  Dimmer  Color Wheel  Gobo  Gobo Rotate  Shutter
Gobo  Gobo Rotate  Prism  Prism Rotate`. `uPan`/`uTilt` are the fine halves, and
`Gobo`/`Gobo Rotate` appearing **twice** is why a profile can carry two gobo
wheels — which the role table's duplicate feature ids already hinted at.

### Three small negatives from the same pass

- **`116.f6` is not the block count.** `LED BAR 252 RGB` occupies **three**
  record-105 entries and carries `f6 = 0`, while `MH-100 BEAM` occupies one and
  carries `1`. The `LASERBAR` has six entries and carries `3`. Whatever `f6`
  counts, it is not blocks. It is 1 on exactly two profiles and 3 on one.
- **`165.f13` carries nothing.** Six sub-messages, **all empty, on all 2778
  presets**. A writer must re-emit the six empty items and can read nothing
  from them.
- **The preset button's colour is not in any decoded field.** No field of the
  preset tracks the `COLOR` line across the six photographed screens — the three
  presets showing `Green` differ in `f11` and agree in nothing else. The manual
  explains it: the default is **AUTO**, where the button "will automatically
  fade between up to 4 of the colors used in the Preset", and the preset grid
  shows "the first 4 colors used". So the colour is **computed** unless forced,
  and no preset in this corpus has ever forced it — which is why no field
  exists for it. Forcing one colour on one preset and saving would make the
  field appear.

## F11-03 — `Button brightness`, prediction published before the download

`Settings → General → Button brightness` set to **14 %**, from the 100 % the
manual's screenshot shows and the 100 every corpus file carries in `102.f11`.

**Predicted**: `102.f11` reads **14**, and nothing else in the file moves except
the version counter and the per-save globals `115.f6`/`f7`.

**Refutation branch**: several Settings values have already been shown *not* to
be project data — master brightness was set to 80 % and wrote nothing. If `f11`
stays at 100, `Button brightness` joins that list and the field is elsewhere;
`Display brightness` and `Audio input level` are the neighbours to try next.

### Measured — refuted, and the experiment was mis-posed

Version 1787670974710 → 711, one save, **43688 bytes both times and not one
record changed**. `Button brightness` writes nothing into the project; it joins
the STATIC POSITION fade and master brightness on the controller-global list.
That much is a clean result and worth having.

**But the experiment could not have tested `f11`, and the fault is mine.** The
prediction rested on "`f11` = 100 in every corpus file". That stopped being true
**twenty-eight snapshots ago**: F11-01 wrote `f11 = 0` into this very project
ourselves, the controller accepted it, and every save since re-emits the field
**absent**. The record has read `{f2, f4, f5, f6, f9}` with no `f11` since
version 1787670974700.

So the comparison was 0 against 0. A one-line check of the current record before
proposing the test would have caught it — the same lesson the version counter
taught twice today, in a new disguise: **read the current state of the field you
are about to test, not the state the registry describes.**

*Correction to the F11-01 entry above*, which says "`field 11` = 100 in every
corpus file": true when written, false since. The line is left standing and
corrected here rather than edited, because the drift is the point.

**Consequence for the restore.** The experiment project has lost the factory
`f11 = 100`; it is one more divergence from `corpus/experiments/FX-01/before.wpj`.
And `f11` can no longer be observed at 100 on this controller without writing it
back first.

## FLASH-01 — where the flash state lives, prediction published first

`Include Flash buttons in Preset` is **already on** for this project, so every
preset in the corpus was captured with whatever flash state was live at the
time — and none of them shows one.

### The field numbers the preset never uses

Across **2778 presets**, record 165's sub-message emits fields
`1–11, 13–19, 21–35`. Two numbers are **holes in the middle of the range**:

```
f12   between f11 (FADE) and f13
f20   between f19 (id) and f21 (move_fx1)
```

Protobuf numbering is assigned when a message is designed, so a gap that sits
*between* used numbers is a field that exists in the schema and is simply **0
everywhere** — absent, under this format's convention throughout. `f36` onward
are absent too, but those are past the end and say nothing.

**So the flash state is `f12` or `f20`**, and it reads 0 on every corpus preset
because none was captured with a flash key held.

### The experiment, and the current state read first

`102.f4` presently reads `[1, 0, 0, 0, 0, 0]`: **WOLF is in `TOGGLE` mode** and
the other five are `FLASH`. Toggle is the one that stays on without a finger on
it, which makes WOLF the only flash key that can be active while a preset is
overwritten.

Preset 82 (page 5 slot 3) currently carries **neither `f12` nor `f20`**, and its
content mask is absent, so every toggle including `OTHER` is on.

1. Press `WOLF` once — it latches.
2. `SHIFT` + tap page 5 slot 3, overwriting it with the live state.
3. Save the project. Press `WOLF` again to release it.

**Predicted**: preset 82 gains exactly one field it did not have — `f12` or
`f20` — carrying **1**, WOLF being bit 0 in the order `102.f4` already uses
(`WOLF STROBE BLINDER SPEED BLACKOUT SMOKE`).

**Refutation branch**: if no new field number appears, the flash state is not in
the preset despite the setting, and `Include Flash buttons in Preset` governs
only recall. Then `f12` and `f20` are something else and the search moves on.

### Measured — refuted, and `f16` answers instead

Version 711 → 712, one save, **one record**: 165, one byte longer. Preset 82
gained **no new field number**. `f12` and `f20` are still absent.

The only thing that changed on the preset is **`f16`**:

```
before  ff01 fe01 01 00 00 e001 1f   00 00 00 00 00 10
after   ff01 fe01 01 00 00 e001 df01 7f 00 00 00 00 10
```

Cut at the 9-bit stride, exactly one slice moves:

| Slice | Before | After |
|---|---|---|
| **6** | 0 | **511** |

**`f16` slice 6 is `WOLF`.** And 511 is all **nine** bits — the eight groups
*and* the ninth slot, the one holding the fogger and the spark. Every other
non-zero slice in the entire corpus stops at 255. The manual says WOLF "plays a
Paparazzi style white flash across all light fixtures"; the mask says *all*
means all nine slots.

**The prediction is refuted.** `f12` and `f20` are holes in the numbering, but
they are not the flash state — the flash state is another engine in `f16`, which
already held Color, Move, Beam, the static layer and the strobe.

**And it refutes one of our own identities.** `moteurs_f16` asserted that no
slice ever sets the ninth bit — true on 2778 presets, false the moment a flash
key is latched. It now checks that only for slices 0–5, and the comment says
why. An identity that holds on a corpus is a statement about the corpus until
something new exercises it; this one lasted four hours.

### The six flash engines, in order — **[correlated]**

`102.f4` stores the six release modes in the order
`WOLF STROBE BLINDER SPEED BLACKOUT SMOKE`. Slice 6 is WOLF, measured. Slice 7
was already read as the strobe, from `Fire!` and `Strobe` being the only two
presets in 2778 that raise it — and STROBE is second in that same order.

Two independent points on the same sequence:

| Slice | Engine | Status |
|---|---|---|
| 6 | `WOLF` | **device-confirmed** |
| 7 | `STROBE` | correlated |
| 8 | `BLINDER` | **[hypothesized]** by position |
| 9 | `SPEED` | **[hypothesized]** by position |
| 10 | `BLACKOUT` | **[hypothesized]** by position |
| 11 | ? | **not** SMOKE — it is non-zero and constant per project (5, 2 or 7), which no unheld flash key would be |

Slices 8, 9 and 10 are zero on every file, which is what five never-latched
flash keys look like. Latching `BLINDER` in `TOGGLE` mode and capturing a preset
would test the whole sequence at once.

## FLASH-02 — `BLINDER` is slice 9, and the positional inference is refuted

`BLINDER` switched to `TOGGLE` and latched, preset 82 overwritten, one save.
Version 712 → 713.

`102.f4` moved `010000000000` → `0100**01**000000`: the **third** byte became 1,
which is `BLINDER` under the order that record already uses — an independent
check that the right key was latched.

`f16` moved two slices:

| Slice | Before | After | |
|---|---|---|---|
| 6 | 511 | **0** | `WOLF` released, as it should be |
| **9** | 0 | **511** | **`BLINDER`** |

**Slice 6 falling back to 0 is worth as much as slice 9 rising.** It shows the
slice tracks the key's live state at capture time, in both directions, rather
than accumulating.

### Retracted — the flash engines do not follow `102.f4`'s order

FLASH-01 inferred slices 8, 9 and 10 as `BLINDER`, `SPEED`, `BLACKOUT` from
`WOLF` at 6 and the strobe at 7 matching the first two entries of
`WOLF STROBE BLINDER SPEED BLACKOUT SMOKE`. **`BLINDER` is 9, not 8**, so two
points did not establish the sequence — they were consistent with it and with
other arrangements, and the third point separated them.

What survives is only what was measured:

| Slice | Engine | Status |
|---|---|---|
| 0 | `Color FX` | correlated, equals `color_fx_actif` |
| 1 | `Move FX` | correlated, equals `move_fx_actif` |
| 2 | `Beam FX` | correlated |
| 5 | static layer | hypothesized |
| **6** | **`WOLF`** | **device-confirmed** |
| 7 | strobe | correlated — `Fire!` and `Strobe` only |
| **9** | **`BLINDER`** | **device-confirmed** |
| 11 | per-project constant | observed |
| 3, 4, 8, 10 | zero in every file | — |

`SPEED`, `BLACKOUT` and `SMOKE` are somewhere in 3, 4, 8, 10 — or not in `f16`
at all, since `SPEED` and `SMOKE` have no group exclusion either. There is no
longer a positional argument to lean on; each needs its own latch.

**State note**: `BLINDER`'s release mode is now `TOGGLE` where it was `FLASH`,
one more divergence from `corpus/experiments/FX-01/before.wpj`.

## FLASH-03 — `BLACKOUT` is slice 8, and the two coexist

`BLACKOUT` switched to `TOGGLE` and latched, preset 82 overwritten, one save,
version 713 → 714. `102.f4` gained a 1 in its **fifth** byte — `BLACKOUT` under
that record's order, the independent check again.

`f16` slice **8** went 0 → 511. **`BLACKOUT` is slice 8.**

Slice 9 stayed at 511: `BLINDER` was still latched when the preset was captured,
and the operator released it afterwards. So the preset now carries **two** flash
engines at once, which is the first proof that the slices are independent rather
than a one-of-N selector.

The published prediction had two halves and split cleanly:

- *"exactly one slice among 3, 4, 8, 10 will rise"* — **correct**, slice 8.
- *"slice 9 will fall back to 0"* — **wrong**, and the reason is ordinary: the
  key was still down. Not a fault in the reading, a fault in assuming the
  operator's sequence.

### Three measured points, and still no order

| `102.f4` index | Key | `f16` slice |
|---|---|---|
| 0 | `WOLF` | **6** |
| 2 | `BLINDER` | **9** |
| 4 | `BLACKOUT` | **8** |

`0 → 6`, `2 → 9`, `4 → 8`. Not monotone, not an offset, not the panel's
left-to-right order either. **The flash engines are not laid out in `102.f4`'s
order, and three points are now enough to say so rather than to guess a fourth.**

Remaining: slices **3, 4, 7, 10**, and three keys — `STROBE`, `SPEED`, `SMOKE`.
Slice 7 is already read as a strobe from `Fire!` and `Strobe`, which would leave
`SPEED` and `SMOKE` in 3, 4 or 10 — or absent, since those two are also the
only flash keys with no group-exclusion mask in record 102. Each needs its own
latch; there is nothing left to infer from.

**State note**: `BLACKOUT`'s release mode is now `TOGGLE`, alongside `WOLF` and
`BLINDER`. Three of the six differ from `corpus/experiments/FX-01/before.wpj`.

## FLASH-04 — `SMOKE` has no `f16` slice

`SMOKE` switched to `TOGGLE` and latched, `BLACKOUT` released first, preset 82
overwritten, one save, version 714 → 715. `102.f4` gained a 1 in its **sixth**
byte, so the right key was switched.

`f16` moved two slices and **both fell**:

| Slice | | |
|---|---|---|
| 8 | 511 → **0** | `BLACKOUT`, released |
| 9 | 511 → **0** | `BLINDER`, released |

**No slice rose.** The published prediction was "at most one slice among 3, 4,
10 will rise, and slice 8 will fall" — both halves hold, and the "at most" was
doing real work.

### Why that fits

`SMOKE` and `SPEED` are the **only two flash keys with no group-exclusion mask
in record 102** — the operator confirmed the device offers no exclusion control
for either, and `Settings` lists only four exclusions. Neither effect is
per-group: smoke drives a fogger's channels and speed multiplies every effect
globally. A per-group mask would have nothing to say about them.

So `f16` carries a flash engine for exactly the four keys that *are* per-group:
`WOLF` (6), `BLACKOUT` (8), `BLINDER` (9), and — by elimination now rather than
by position — `STROBE`, which slice 7 already showed through `Fire!` and
`Strobe`. Slices 3, 4 and 10 stay zero in every file.

### The reservation this result carries

A null result cannot distinguish "`SMOKE` has no slice" from "`SMOKE` was not
actually latched when the preset was captured". Switching the release mode is
visible in `102.f4`; **pressing** the key is not visible anywhere in the file
unless it writes a slice — which is precisely what is in question.

The three earlier latches each produced a rise, so the procedure works; and the
two releases in this same save show the capture was reading live key state at
that moment. That is strong, not conclusive. Status **[correlated]**, and the
one thing that would close it is the operator confirming the smoke icon was on
screen at the moment of the overwrite.

## FLASH-05 — `STROBE`, prediction published before the measurement

`STROBE` switched to `TOGGLE` and latched, preset 82 overwritten, one save.

**Predicted**: `f16` slice **7** rises, and no other slice does. That converts
slice 7 from *elimination* — the last per-group flash key with a free slot — to
a direct measurement, and it re-validates the procedure that produced FLASH-04's
null result on `SMOKE`.

**The value is the interesting part.** `WOLF`, `BLACKOUT` and `BLINDER` each
came back **511**, all nine slots including the effects slot. But the two
presets that raise slice 7 on their own — `Fire!` and `Strobe` — carry **255**,
eight slots only.

| Slice 7 reads | Reading |
|---|---|
| **511** | the flash key writes the same nine-slot mask as the other three, and the preset engine's 255 is simply a different author |
| **255** | the strobe genuinely stops at the eight groups, and the ninth slot is reserved for effects that can black out or flash a fogger |

Either way slice 7 is settled. `102.f4`'s **second** byte should also become 1,
the independent check that the right key was switched.

### Better: both keys are latched, which makes one capture discriminating

The operator reports `STROBE` **and** `SMOKE` are currently latched together.
That is a stronger experiment than the one just published, because FLASH-04's
reservation — that a null result cannot separate "no slice" from "not latched" —
dissolves:

- **Exactly one slice rises** → it is `STROBE`, and `SMOKE` has no slice even
  though it was demonstrably held at the same moment. FLASH-04 goes from
  correlated to **device-confirmed**, by the very capture that proves the key
  was down.
- **Two slices rise** → `SMOKE` does have one, FLASH-04 was a false negative
  caused by the key not being latched, and both are named at once.

The prediction stands: slice 7 rises. What is added is that **no second slice
rises**, and that half is now the one carrying the weight.

*Correction to the slice-7 argument.* It rested on `Fire!` and `Strobe` being
the only two presets to raise it. The operator points out that **`Fire!` reads
as smoke, not strobe** — and they are right, the name is equivocal and this
registry leaned on it. `Strobe` alone is the unambiguous anchor, so the
correlated status came from one preset and a name, which is thinner than it was
written. The measurement about to happen replaces it either way.

### Measured — both halves hold, and FLASH-04 is closed

Version 715 → 716, one save. `102.f4`'s **second** byte became 1: `STROBE`
switched. `f16` moved **one** slice:

| Slice 7 | 0 → **511** |
|---|---|

- **`STROBE` is slice 7**, measured directly. It no longer rests on the name
  `Fire!` or on elimination.
- **The value is 511**, not 255. The flash key writes all nine slots, like
  `WOLF`, `BLACKOUT` and `BLINDER`. The `255` that `Fire!` and `Strobe` carry is
  a preset's own strobe engine writing eight — a different author, as the first
  branch predicted.
- **No second slice rose, while `SMOKE` was latched at the same moment.** That
  is the capture FLASH-04 needed: the key was demonstrably down and wrote
  nothing. **FLASH-04 becomes [device-confirmed]** — `SMOKE` has no `f16` slice.

### `f16`, complete for the flash keys — **[device-confirmed]**

| Slice | Key | Value when latched |
|---|---|---|
| 6 | `WOLF` | 511 |
| 7 | `STROBE` | 511 |
| 8 | `BLACKOUT` | 511 |
| 9 | `BLINDER` | 511 |
| — | `SMOKE` | **no slice** |
| — | `SPEED` | **no slice**, [hypothesized] by symmetry — the other key with no group exclusion |

Four keys, four slices, all writing the full nine-slot mask, and the two keys
with no group-exclusion control in record 102 have no slice either. The
correspondence between "has an exclusion mask in 102" and "has a slice in
`f16`" is exact on all six keys.

The slice order — `WOLF STROBE BLACKOUT BLINDER` — matches neither `102.f4`'s
release-mode order nor the order of 102's own mask fields. It is simply the
order the firmware assigned, and three refuted positional guesses got us here.

`f16` now reads: 0 Color FX, 1 Move FX, 2 Beam FX, 5 static, 6 WOLF, 7 STROBE,
8 BLACKOUT, 9 BLINDER, 11 a per-project constant. Slices 3, 4 and 10 are zero in
every file and every experiment.

## FLASH-06 — `SPEED` is slice 10, and the symmetry argument is refuted

`SPEED` switched to `TOGGLE` and latched, `STROBE` and `SMOKE` released, preset
82 overwritten, one save, version 716 → 717. `102.f4`'s **fourth** byte became 1.

`f16` moved two slices:

| Slice | | |
|---|---|---|
| 7 | 511 → **0** | `STROBE`, released |
| **10** | 0 → **511** | **`SPEED`** |

**Retracted**: "`SPEED` has no slice, by symmetry — the other key with no group
exclusion". It has one. The symmetry argument was published as
**[hypothesized]** one experiment ago and is now dead.

**And the rule it rested on is dead with it.** FLASH-05 recorded that the
correspondence between "has an exclusion mask in record 102" and "has a slice in
`f16`" was *exact on all six keys*. It was exact on the five measured at the
time. `SPEED` has a slice and no exclusion mask, so the two facts are
independent — which is what a group mask on a **global speed multiplier** should
have suggested in the first place.

### The flash side of `f16`, measured on all six — **[device-confirmed]**

| Slice | Key |
|---|---|
| 6 | `WOLF` |
| 7 | `STROBE` |
| 8 | `BLACKOUT` |
| 9 | `BLINDER` |
| 10 | `SPEED` |
| — | `SMOKE` — the only key with no slice |

Five of six, each measured by its own latch, each writing **511** — all nine
slots. Only `SMOKE` writes nothing, and that is device-confirmed by the capture
where it was held alongside `STROBE`.

Slices **3 and 4 remain zero** in every file and every experiment, and there are
no flash keys left to assign to them.

Whatever slice **11** is, it is not `SMOKE`: it is non-zero and constant per
project, and it did not move in the capture where `SMOKE` was latched.

### What five refuted guesses bought

The flash engines were guessed positionally three times — `102.f4`'s order, then
its mask-field order, then the panel layout — and by symmetry twice. All five
failed. The layout `WOLF STROBE BLACKOUT BLINDER SPEED` matches nothing else in
the format, and the only way it was ever going to be read is one latch at a
time. Five experiments, five measurements, no inference left in the result.

## FLASH-07 — `SMOKE` alone, and the flash side closes

Everything released, `SMOKE` alone latched, preset 82 overwritten, one save,
version 717 → 718. Record **165 only** — `102.f4` did not move, `SMOKE` already
being in `TOGGLE`.

`f16` moved **one** slice, and it fell:

| Slice 10 | 511 → **0** | `SPEED`, released |
|---|---|---|

**Nothing rose.** The preset's `f16` now reads slices 0, 1, 5 and 11 — Color FX,
Move FX, the static layer, and the per-project constant. No flash engine at all,
with a flash key held.

This is the cleanest form the experiment can take: **one key active, the only
candidate left, and not a bit written.** The three earlier null-adjacent results
each carried a "was it really latched" reservation; this one cannot, because
`SMOKE` is the only thing that was on.

And slice **11 did not move either** — it sits at 2 before and after — which
retires the last version of the idea that 11 might be `SMOKE` with a
project-constant mask.

### `f16` — final

| Slice | Engine | |
|---|---|---|
| 0 | `Color FX` | duplicates `color_fx_actif` |
| 1 | `Move FX` | duplicates `move_fx_actif` |
| 2 | `Beam FX` | |
| 3, 4 | zero everywhere | nothing left to assign |
| 5 | static layer | 255 on every preset, [hypothesized] |
| 6 | `WOLF` | flash, 511 |
| 7 | `STROBE` | flash, 511 |
| 8 | `BLACKOUT` | flash, 511 |
| 9 | `BLINDER` | flash, 511 |
| 10 | `SPEED` | flash, 511 |
| 11 | per-project constant, 2 / 5 / 7 | not a flash key |

Twelve slices: **nine named, two provably empty, one open.** Six experiments,
one latch each, and every naming in the flash half is a direct measurement —
after five positional and symmetry guesses that all failed.

## FLASH-08 — the reverse direction: a file we wrote, read back by the device

Every naming so far ran **device → file**: latch a key, capture, read the slice.
This runs it the other way. Three presets are edited to carry one flash slice
each and nothing else changed, the project is deployed, and the operator recalls
them.

Only `f16` is touched, on three presets, in one record:

| Preset | Slice set to 511 | Predicted key on recall |
|---|---|---|
| page 5 slot 1 (`<nom utilisateur>`) | 6 | **`WOLF`** |
| page 5 slot 2 | 7 | **`STROBE`** |
| page 5 slot 3 | 8 | **`BLACKOUT`** |

Slices 6–10 are cleared first on all three, so each preset carries exactly one
flash engine. A verification pass over the built file confirms record 165 is the
only record that differs and `f16` the only field.

Two presets are not enough for `BLINDER` and `SPEED` in the same pass, and the
repository's rule is **edit, do not synthesize** — duplicating a preset entry to
make room would create something the donor file does not contain. So slices 9
and 10 get a second pass rather than a shortcut.

### Side finding — `165.f1` is neither count

`f1` equals the number of presets on 24 files and the number of *named* presets
on the other 17, and neither rule survives the whole corpus: `base.wpj` has 82
presets, 81 named, `f1` = 82; `after-smoke-alone.wpj` has 83 presets, 81 named,
`f1` = 81. It is left **verbatim** by this edit. **[observed]**

### Measured — the reverse direction works, once the project is reloaded

The three presets were recalled and **all three triggered their predicted key**:
slot 1 `WOLF`, slot 2 `STROBE`, slot 3 `BLACKOUT`. `f16` slices 6, 7 and 8 are
now **device-confirmed in both directions** — captured from a latched key, and
written into a file the controller then interpreted.

**But only after the operator reopened the project by hand.** The deployment
performs a `RESTART` of its own and re-verifies afterwards, and that was not
enough: the controller kept running the project it already had open. So a
deployed project is not live until it is reopened from `Main Menu → Projects`,
and `restart` does not substitute for that. Worth stating plainly, because the
runner's docstring says deployments are "automatic after that point" — they are
automatic to *store*, not to *load*.

### FLASH-09 — the device deletes preset entries it did not create

To cover `BLINDER` and `SPEED` in one pass, two preset entries were duplicated
from preset 82 with only their `id` changed — the operation the device itself
offers as "SHIFT + tapping another Matrix button will copy the selected Preset".

The deployment reported success. **The controller returned 83 presets, not 85**:

```
sent      85 presets, record 165 = 30882 bytes, ids … 80 81 82 83 84
returned  83 presets, record 165 = 30184 bytes, ids … 80 81 82
```

Same version counter, different content: the firmware **normalises the record on
load and drops entries beyond what it recognises**. The two additions vanished
without an error anywhere.

So the repository's rule — *edit, do not synthesize; every preset written must
already exist in the donor file* — is not conservatism, it is a measured
constraint. **A preset cannot be added by writing the file. It has to be created
on the controller.** The rule was being followed for the wrong reason until now;
this is the reason.

**Note on the runner's verification.** `deploy` verifies after its restart and
reported success, yet a later download returns the truncated record. Its check
therefore does not catch this class of change — a caller that adds structure
must re-download and compare item counts itself.

## FLASH-09 revisited — the drop happens at reopen, not at store — 2026-08-26

Re-reading the run journal and the deployer's code corrects yesterday's
reading in one important way, and the corpus closes several doors.

### The device stored and returned all 85 entries — **[observed]**

`verify_project` compares the **record payloads byte for byte** (it raises on
any difference), and in run `20260826T163220.559340Z-FLASH-09` it passed
**twice — once after the store, once after the RESTART**. So at deploy time
the controller stored the 85-entry record 165 and served it back intact; the
`downloadedSha256` differs from `candidateSha256` only in the prefix (version
counter). The truncation to 83 appeared **only in the download made after the
operator reopened the project by hand** for the recall test.

Yesterday's sentence "the firmware normalises the record on load" was right by
accident: it is the **project-open path on the panel**, not the USB store
path, that drops the entries. The deployer's verification is not blind — at
the moment it ran, nothing had been dropped yet.

### The truncation kept the original 83 verbatim — **[observed]**

The returned record measured 30184 bytes — **exactly the size of the record
before the edit**, and

```
30882 − 30184 = 698 = 2 × (3 + 346)
```

i.e. precisely the two added entries with their `f5` headers. The device did
not renumber, rebuild or normalise anything: it kept its 83 entries and
discarded exactly the two it had not created. Encoded as an identity:
`ajout_de_preset()` in `tools/wpj_identities.py`, over
`corpus/experiments/FLASH-09/{before,candidate}.wpj`.

### No external preset count exists in the file — **[observed]**

Exhaustive record diff of the F30-04 pair (the device itself adds a preset,
82 → 83): outside record 165, only **{115, 125, 155, 161}** change, plus the
version counter.

| Record | Change | Reading |
|---|---|---|
| 115 | two bytes per fixture | live per-fixture values, changes at every save |
| 125 | last byte of every `f4` (all 9 slots): `30` → `38` | **not** a preset count: `38` also on rig-c (2 user presets), `30` on the 0-user factory files |
| 155 | `f5[0].f3`: 1 → 16 | sequencer state, single field |
| 161 | 3 bytes | volatile UI/machine state (known) |

Nothing anywhere holds "3 user presets". The FLASH-09 candidate also passes
all 15 corpus identities — the rejected file violates no known invariant.

### `165.f1`: both remaining candidate rules die on one pair — **[observed]**

Across the F30-04 pair, `f1` goes **82 → 81** while the count goes 82 → 83
and the named count stays 81 on both sides. So "f1 = presets" is refuted by
the after-file and "f1 = named presets" by the before-file — on a single
device-written pair, no corpus survey needed. `f1` is stable across every
later save of the same state (all 83-preset files carry 81), so it is not
per-save UI noise either. Semantics: **open**.

### Reading, and the two experiments that decide it — **[hypothesized]**

The behaviour matches a **warm-reopen merge**: reopening the project that is
already live updates existing presets by id and never creates one. This is
consistent with FLASH-08 ("the controller kept running the project it already
had") and with every successful edit experiment — all of them updates. The
one live alternative is a gate on `f1` (kept = `f1 + 2` fits the single
binding observation).

- **PRESET-01 — cold open.** Deploy the FLASH-09 candidate unchanged; the
  operator opens a *different* project on the panel, then opens
  format-lab. Warm-merge predicts **85** presets survive; an `f1` gate
  predicts 83.
- **PRESET-02 — f1 bumped.** Deploy the candidate with `f1` set to 83 as the
  only change; warm reopen as in FLASH-09. An `f1` gate predicts **85**;
  warm-merge predicts 83.

Either outcome answers the question "how do you add a preset by file". Both
are one deploy plus one panel gesture.

### The path that works today — **[device-confirmed]**

Until PRESET-01/02 run, adding capacity is a panel gesture and everything
else is a file edit: create the slots once on the controller (select a
preset, SHIFT + tap an empty pad — the documented copy gesture), then rewrite
those entries' contents entirely by file. Updates to existing entries are
device-confirmed to persist across store, restart and reopen (FLASH-05…08,
GOBO-01, POS-03/06). For the show generator this means: pre-create one page
of placeholder presets, then generate freely into them.

Candidates on disk, ready to deploy (never committed, like all `.wpj`):
`corpus/experiments/FLASH-09/candidate.wpj` for PRESET-01 (unchanged), and
`corpus/experiments/FLASH-09/candidate-f1-83.wpj` for PRESET-02 — built from
it with `f1` 81 → 83 as the **only** differing byte (offset 1 of record 165),
verified at build time.

## PRESET-01 — the truncation claim collapses before the experiment runs — 2026-08-26

Preparing PRESET-01 (WTOOLS closed, operator present), the pre-flight
download refutes yesterday's headline measurement:

- Storage today serves sha256 `c2458b0a…` — **exactly the FLASH-09 journal's
  `downloadedSha256`** — with records byte-identical to the candidate:
  **85 presets, ids … 83 84**, `f1` = 81. **[observed]**
- Its version counter is `1787761940828` = 16:32:20 UTC = the deploy run's
  own timestamp: the store stamped it, and **nothing has rewritten storage
  since**. No device save ever wrote an 83-preset version back.
- Yesterday's "returned 83 presets, record 165 = 30184, same version
  counter" matches `before.wpj` on every attribute — count, ids, record
  size, and counter `1787761074508` (which the byte-preserving edit had
  copied into the candidate, hence "same counter" against the sent file).
  The overwhelmingly likely reading: that download was a **pre-deploy
  state**, mis-attributed as post-deploy. FLASH-09's conclusion "the device
  deletes preset entries it did not create" is **retracted** as unsupported:
  no artifact of a truncated post-deploy download exists (`check1/check2`
  in the session scratchpad also hash to the *before* state).

### Prediction, published before the panel measurement

Storage has held the two file-added presets byte-for-byte for ~24 h, across
the deploy's RESTART and verify. Predicted, for a cold open (open another
project, then open format-lab from Main Menu → Projects):

1. Preset matrix page 5 shows **5 occupied pads** (valse + 2 unnamed + the
   two additions).
2. Recalling pad 4 lights **BLINDER**, pad 5 lights **SPEED** — the two
   entries carry `f16` slices 9 and 10 at 511, which would also close the
   flash-engine map's last two slices in the write direction.
3. A download taken afterwards still returns 85 presets.

If instead the panel shows 3 pads, the loader-gate model returns and
PRESET-02 (`f1` = 83) becomes the discriminating deploy.

### Measured — all three predictions held — **[device-confirmed]**

Cold open performed (another project opened, then format-lab from
Main Menu → Projects), operator at the panel, WTOOLS closed:

1. Preset matrix page 5 shows **5 occupied pads**. ✓
2. Pad 4 recall lights **BLINDER**, pad 5 recall lights **SPEED**. ✓ —
   `f16` slices **9 and 10 are now device-confirmed in the write
   direction**, closing the flash-engine map both ways for all five
   engines plus WOLF (slices 6–10, FLASH-03…08 + PRESET-01).
3. The post-reopen download returns **85 presets, records byte-identical
   to the deployed candidate, version counter unchanged** — the device did
   not even need to rewrite storage.

So, the answer to the question that opened FLASH-09:

**A preset is added to record 165 by appending a well-formed `f5` entry with
the next sequential id. Nothing else is required.** No count exists to
maintain, `165.f1` may be left verbatim (85 presets accepted with `f1` = 81),
and the firmware accepts, displays, recalls and conserves the additions
across store, RESTART, cold reopen and 24 h of storage. FLASH-09's
"the device deletes preset entries it did not create" is **refuted by device
measurement**; the *edit, do not synthesize* rule loses its measured
justification for preset entries and reverts to plain caution about
unknown fields.

**PRESET-02 is unposed.** It existed to discriminate a loader gate
(warm-merge vs `f1`) that PRESET-01 shows does not exist: `f1` = 81 gated
nothing at 85 presets. The `candidate-f1-83.wpj` build is kept as a donor
for future `f1` semantics work only.

Identity updated accordingly: `ajout_de_preset()` now records the edit
arithmetic and the retraction, not a truncation.

## PRESET-03 — a named preset at page 5 slot 20, hands-off — 2026-08-26

Request: create "preset test automatique" at the **bottom-right pad of
page 5** — id (5−1)·20 + (20−1) = **99** — transferred, loaded and activated
with zero panel interaction. Two new variables ride along: a **gap in the id
sequence** (85–98 absent, first ever in the corpus), and the first
**file-written `nom`** (f25). Candidate: donor = entry 82 verbatim, id → 99,
`nom` inserted in tag order, `f16` flash slices 6–10 cleared (donor carried
BLACKOUT on slice 8). 86 entries, `f1` left at 81, only record 165 differs
from the device's current state, 15/15 identities pass.

### Predictions, published before the deploy

1. Store + post-RESTART verify accept the 86 entries (per PRESET-01).
2. **The pad does not appear before a manual reopen.** FLASH-08 measured
   that the controller keeps running the project it has open across the
   deploy's RESTART; nothing suggests structure changes that. If the pad
   *is* visible with no panel touch, FLASH-08's reading must be revisited —
   either way the automation boundary gets measured.
3. On the next (manual) open, the preset sits at **page 5, slot 20,
   bottom-right, named** — pads are keyed by id, and the 85–98 gap is
   tolerated. Rival outcomes that would refute: entry dropped (sequential
   ids required) or pad at slot 6 (position-keyed matrix).

### Measured — the gap is fatal, loudly — **[observed]**

1. ✓ Store and both verifies accepted the 86 entries.
2. ✓ No panel touch, after the deploy's RESTART: nothing new on page 5.
   FLASH-08's boundary now holds for structure as well — the running
   project does not reload on RESTART, and firmware 2.0.18 exposes no USB
   open-project command. **Full hands-off activation is not achievable on
   this firmware**; the boundary is the reload, measured twice.
3. ✗ **Refuted, in an unforeseen direction**: on manual open the panel
   showed **"Error opening project"** — not a dropped entry, not a
   repositioned pad: the whole project refused to load. First *loud*
   rejection ever measured (FLASH-09's silent deletion was a
   mis-attribution; this is a real error dialog). Confounded variables:
   the id gap 85–98 and the first file-written `nom`. Storage still held
   the 86 entries byte-for-byte after the error — the loader rejects
   without rewriting.

Rollback: redeploying the 85-preset state (`after-cold-open` bytes)
restored a normally-opening project, operator-confirmed. The transactional
runner plus a kept known-good download make a failed loader experiment a
two-minute round trip.

## PRESET-04 — fill the gap, keep the name: the A/B that isolates the variable

Candidate: the 85-preset state plus entries id **85–98** (donor = entry 82,
flash slices cleared, unnamed) and id **99** named "preset test automatique"
— identical to PRESET-03 in every respect except the gap. 100 presets,
`f1` = 81 verbatim, page 5 becomes full.

### Predictions, published before the deploy

1. Store + verifies accept the 100 entries.
2. After manual reopen: the project **opens**; page 5 shows **20 occupied
   pads**, slots 6–19 unnamed, slot 20 named "preset test automatique";
   recalling slot 20 lights no flash key (slices 6–10 cleared). If this
   holds, the PRESET-03/PRESET-04 A/B pins the loader failure on the
   **id gap** — ids must be dense — and clears the file-written name.
3. If instead the open fails again, the `nom` (or its interaction with
   additions) becomes the prime suspect and the next build drops it.

## FLASH-10 — the five flash slices, confirmed in both directions

The project now carries **85 presets**, and page 5 slots 1–5 hold one flash
slice each:

| Slot | Slice | Key |
|---|---|---|
| 1 (`<nom utilisateur>`) | 6 | `WOLF` |
| 2 | 7 | `STROBE` |
| 3 | 8 | `BLACKOUT` |
| 4 | 9 | `BLINDER` |
| 5 | 10 | `SPEED` |

The operator reports `BLINDER` and `SPEED` validated alongside the three already
measured, so **all five slices are device-confirmed in both directions**:
captured from a latched key into the file, and written into a file the
controller then acts on.

That is the repository's highest standard, and it now covers the whole flash
half of `f16`. Together with `SMOKE` writing nothing — proven by the capture
where it was the only key held — the six flash keys are completely accounted
for.

**Presets 83 and 84 exist.** FLASH-09 measured that the firmware deletes preset
entries added by writing the file; these two were created by some other route,
which this registry did not observe. The FLASH-09 constraint stands as measured
— *writing a new entry into the file does not survive the load* — and how a
preset is created legitimately is still an open question, being pursued
separately.

### PRESET-04 measured — dense ids still refuse to load — **[observed]**

"Error opening project" again, with ids 85–99 dense. The gap was not the
fatal variable (or not alone). Rollback to the 85-preset state restored a
normally-opening project (operator-confirmed, second time). Remaining
suspects, by prior: the file-written `nom` — **no name in the 2778-preset
corpus exceeds 19 bytes**, and "preset test automatique" is 23 — and the
addition count (15 at once vs the 2 of PRESET-01).

## PRESET-05 — one entry, id 85, the 23-byte name: name vs quantity

Candidate: the 85-preset state plus a single entry id 85 (donor 82, flash
slices cleared) carrying `nom` = "preset test automatique". Against
PRESET-01 (two unnamed additions, loaded fine) the single new variable is
the name.

### Prediction, published before the deploy

Primary: **"Error opening project" again** — the name is fatal, most likely
its 23-byte length overflowing a firmware buffer sized around the corpus
maximum of 19. Rival: the project opens with 6 pads and slot 6 named — then
the name is innocent and PRESET-04's failure was the addition count. A
second build with a ≤19-byte name stands ready to split length from
presence if the primary holds.

### PRESET-05 measured — the 19-character name limit is the loader's — **[device-confirmed]**

A single, otherwise well-formed entry at id 85 carrying a **23-byte** name
made the project refuse to open ("Error opening project"). The operator
confirms the panel's rename UI caps names at **19 characters** — and
PRESET-05 shows the loader enforces the same bound on file-written names
rather than truncating or dropping the entry: **any name > 19 bytes makes
the whole project unloadable, loudly.** Combined with the corpus (no
factory name exceeds 19), the preset name field is a fixed 19-char buffer.

## PRESET-06 — the deliverable: dense ids, 16-byte name at slot 20

Candidate = PRESET-04 with the single fatal variable changed: entries 85–98
unnamed, entry 99 named **"preset test auto"** (16 bytes ≤ 19). If it opens,
the A/B against PRESET-04 pins that failure on name length and clears the
15-at-once addition count.

### Prediction, published before the deploy

The project opens; page 5 shows 20 occupied pads; slot 20 (bottom right)
reads "preset test auto"; recalling it lights no flash key. The id gap
remains untested in isolation (PRESET-03 confounded it with the long name);
a dedicated gap-only experiment stays open.

## SETP-01 — SET_PRESET payload discovery — 2026-08-26

Goal: recall a preset over USB (event 41, allowlisted, never yet sent), the
missing half of hands-off activation. Every decoded message in this protocol
is protobuf-shaped, so the candidate encodings, tried one at a time against
the live project (101 presets), each judged by RETURN_STATUS plus a DMX
frame comparison:

1. `f1 = varint(preset id)` — predicted encoding. Target: id 23 "Deep Red"
   (pure-red static look, unambiguous in a DMX frame).
2. Fallback: `f1 = varint(page 1-based), f2 = varint(slot 1-based)` (23 →
   page 2, slot 4).

Predicted: form 1 returns success and the next DMX frame shows the Deep Red
signature (red channels driven, others near zero).

### SETP-01 measured — recall by id works; missing ids are silent no-ops — **[device-confirmed]**

`SET_PRESET` with `f1 = varint(id)` returned success and repainted the DMX
frame on two targets (id 23 Deep Red, id 22 Deep Green — the green par
channels rise to 255 under 22). An out-of-range id (150) also returns
success but changes nothing: **RETURN_STATUS cannot discriminate a missing
preset; the DMX frame can.** Remote recall is closed; the reload is the
remaining half of hands-off activation.

## PRESET-07 + SETP-02 — sparse layout, and the delete-store-restart reload chain

The operator rejects the gap fillers (rightly: the device's own save writes
a 99 → 114 gap — their panel-created "Test" sits at id 114 = page 6
slot 15, confirming the id formula on page 6 and making the fillers
pointless). Candidate: the device's own save minus entries 85–98 —
87 presets, tail `… 84, 99 "preset test auto", 114 "Test"`, `f1` = 87
(count, the rule the device's writer just demonstrated).

Reload hypothesis: RESTART alone leaves the NVRAM live copy in charge
(FLASH-08), but **deleting the open project should invalidate that copy**;
re-storing the same UUID before the restart keeps the boot pointer valid,
so the reboot must re-read storage — the new bytes.

### Predictions, published before the run

1. Deploy of the sparse candidate: store + both verifies pass.
2. After the deploy's own RESTART, `SET_PRESET(92)` still repaints the
   frame — the live copy is stale and still holds the fillers (FLASH-08
   re-confirmed in-band, no panel needed).
3. After DELETE_PROJECT → SET_PROJECT → RESTART: `SET_PRESET(92)` leaves
   the frame unchanged (filler gone) while `SET_PRESET(99)` repaints it —
   the live project is now the sparse file, **activation with zero panel
   touches**. Rival: 92 still recalls → the NVRAM copy survives even
   deletion, and the allowlist holds no reload lever.
4. Panel, look only: page 5 shows 5 pads plus "preset test auto" bottom
   right; page 6 slot 15 shows "Test"; no filler pads anywhere.

### SETP-02 measured — no protocol event replaces the live copy — **[device-confirmed]**

The run took a detour that rewrote the recall story first:

- **[RÉTROGRADÉ le 2026-08-27 : [hypothesized], pas device-confirmed.** Ces
  rappels partaient en `f1=`/`f2=`, donc le firmware lisait le tag et tirait
  l'id 8 ou 16 quoi qu'on ait voulu (RAW-01) ; et le silence était jugé au
  discriminateur retiré par RECALL-01. Rivaux nommés : adressage faux, et
  rappel avalé (RECALL-03). À ajouter à la cascade de RECALL-01, qui l'avait
  omis.]
- **The PRESETS screen (mode 5) swallows USB recalls silently** — status
  still "Hooray!", frame untouched. Every "silent recall" observed today
  (including the early false "reload" verdicts) traces to the operator's
  panel sitting on the matrix screen. Recalls work from HOME and other
  screens. **[device-confirmed]**
- **`SET_PRESET.f2 = varint(id)` recalls any preset, factory or user**
  (id 92 → 75 channels, fade-free). `f1` recalled factory ids in early
  probes but is inert on ids ≥ 80 — semantics **open**; use `f2`.
- `SET_MODE` with `f1 = 0` returned success but landed on mode **8**, not
  0 — payload semantics **open**. It does kick the panel off mode 5, which
  un-gates recalls.
- Fade discipline: recalls must be judged on fade-free targets (donor
  clones have no `f11`) or after the fade completes; mid-fade captures
  produced most of today's ambiguity.

The reload chain itself, operator-approved: DELETE_PROJECT (open project,
count 5 → 4) → SET_PROJECT (sparse file) → RESTART → storage verified
byte-for-byte. Then the fade-free discriminator: **filler id 92 still
paints** — the old 101-preset copy is STILL live. A DISABLE_ENGINE →
ENABLE_ENGINE cycle changes nothing either. Four negative results —
RESTART (FLASH-08, and PRESET-07 in-band), delete-store-restart, engine
cycle — close the question: **firmware 2.0.18 keeps its NVRAM live copy
through every event in the known protocol surface; only a manual
Main Menu → Projects open replaces it.** Hands-off activation therefore
decomposes as: transfer (remote), reload (ONE panel gesture, irreducible
today), recall (remote, `SET_PRESET.f2`).

Open lead for a future session: WTOOLS 2.0.2 users see pushed edits live,
so either WTOOLS relies on the same manual gesture, or one of the
unidentified event ids (13–15, 17, 22–38, 40, 42) performs the reload.
Observing a WTOOLS push would decide.

Note: the earlier PRESET-07 prediction 2 ("recall 92 still repaints after
the deploy restart") was measured as *no repaint* at the time and briefly
read as a reload — that reading is **retracted**: the probe ran while the
panel sat on mode 5, which silences recalls. The corrected in-band probes
above supersede it. The sparse file's loadability (its two id gaps,
84→99→114) remains **untested** — no reload ever happened — and the next
manual open measures exactly that.

### PRESET-07 measured, and `f2` re-read: it is the entry POSITION — **[device-confirmed]**

The manual open of the sparse file succeeded: page 5 shows its 5 pads plus
"preset test auto" bottom right, page 6 shows "Test" mid-page, no fillers.
**Id gaps load fine** — PRESET-03's failure is now fully attributed to the
23-byte name, and the loader tolerates the device's own 84→99→114 layout.

With the sparse project live, the position/id ambiguity — invisible in
every dense state, where the two coincide — finally split: recalls of 85
and 92, which exist as no id in the live project, still paint, and 85/86/
92/99 all render pairwise-identical frames (the operator's "Test" was
captured from the donor-family look, hence the equality). Id addressing is
**refuted**; **`SET_PRESET.f2` = varint(entry position, 0-based, clamped
to the last entry when out of range)**. The mode-5 recall gate was
demonstrated a third time in the same run (all-silent grid until SET_MODE
kicked the panel off the matrix screen).

The generator's recipe, all device-confirmed today: write entries sparse
with the id formula (id = (page−1)·20 + (slot−1), gaps allowed), names
≤ 19 bytes, `f1` = count; deploy; ONE manual open; then
`SET_MODE` (un-gate) + `SET_PRESET.f2 = position` recalls anything,
hands-off.

## RELOAD-01 — l'event de rechargement : lecture statique de WTOOLS 2.0.2, puis capture USB — 2026-08-26

Question posée : quel event du protocole USB remplace la copie vive du
projet sans geste au panneau ? SETP-02 a fermé l'allowlist actuelle par
quatre négatifs ; le lead restant était « WTOOLS 2.0.2 pousse des éditions
qui apparaissent en direct, donc l'event existe ».

WTOOLS ouvre le tty en `TIOCEXCL` : impossible d'écouter le port pendant
qu'il tourne. La capture doit se faire au niveau du **bus USB**, ce qui
demande des privilèges et probablement une installation. Avant de payer ce
prix, lecture **statique** de ce qui est déjà sur la machine.

### Lecture statique — WTOOLS 2.0.2 (build 248, Flutter AOT) — **[observed]**

Même règle qu'au `mode-map.md` : seuls des **identifiants** sont lus, rien
du binaire n'est reproduit ici au-delà des noms.

1. **Surface API contrôleur.** Les noms de méthodes du client (suffixe
   `…Async` dans le pool de chaînes) couvrent : `downloadProjectToController`,
   `deleteProject`, `syncProjects`, `getDataFromController`,
   `sendProfileToController`, `deleteProfileFromController`,
   `refreshControllerSettings`, `updateFirmware`, `uploadFlash`,
   `factoryReset`, `disconnectController`. **Aucun verbe de chargement de
   projet côté contrôleur** : `loadProject`, `openProject`, `reloadProject`,
   `setActiveProject`, `activateProject`, `selectProject`, `switchProject`,
   `currentProject` sont **tous absents** du pool. Les seuls `load…` présents
   (`loadProjectFromFile`, `loadProjectFromDroppedFile`) chargent un fichier
   **dans l'app**, pas dans l'appareil.
2. **Vocabulaire des types de message.** Le pool contient, en camelCase
   exact, 13 des 18 noms de notre table d'events : `getProfileList`,
   `getProfile`, `getProjectList`, `getProject`, `deleteProject`,
   `setProject`, `returnStatus`, `returnProgress`, `getSettings`, `setMode`,
   `setPreset`, `skipPreset`, `restart`. Le même moule fournit des noms
   **non encore attribués à un id** : `setProfile`, `deleteProfile`,
   `setFlashData`, `getFlashData`, `setFirmware`, `factoryReset`, `rename`,
   `setLock`, `setUnlock`, `keepAlive`, `handshake`, `getPatch`, `setBeat`,
   `setKey`, `activate`. Aucun de ces candidats ne recharge un projet.
   ⚠ Le pool AOT est dédupliqué et **hors ordre de déclaration** (constat
   `mode-map.md`) : ces noms sont un **vocabulaire**, pas une numérotation.
   Aucune valeur numérique ne peut en être tirée.
   ⚠ Deux réserves qui limitent la portée de ce point : (i) 5 des 18 noms
   connus manquent (`disableEngine`, `enableEngine`, `disableUsbDmx`,
   `enableUsbDmx`, `dmxPacket`) — 2.0.2 les a donc renommés, et le
   vocabulaire lu n'est pas la table complète ; (ii) plusieurs candidats
   (`restart`, `activate`, `rename`, `refresh`, `handshake`, `keepAlive`)
   sont des mots courants du framework et peuvent n'avoir aucun rapport
   avec le protocole.
3. **`ProjectLoadingType` — faux ami écarté.** L'enum existe mais ses
   valeurs voisines dans le pool sont `cloud` / `controller` /`fromCloud` /
   `fromController` : c'est l'**origine** d'un projet dans l'app, pas le
   mode de chargement `ALL/FIXTURES/PRESETS` du panneau.
4. **Le guide intégré du vendeur** (`assets/guides/en.json`, chapitre
   « WTOOLS ») énumère les fonctions de l'app : sync BPM (Ableton Link,
   OS2L), Easy View 3D, achat d'add-ons, **sync de projets** (« click on a
   project to sync it to your Wolfmix, export or delete »), sync de profils,
   lock/unlock, factory reset, renommage. **Pas d'éditeur de projet ni de
   preset.** WTOOLS 2.0.2 ne peut donc pas « pousser une édition » : il
   transfère un fichier entier (notre `SET_PROJECT`) ou déclenche un preset
   depuis son écran LIVE (`Set Wolfmix Preset` / `Failed to set preset` =
   notre `SET_PRESET`, event 41, déjà acquis).
5. **Le geste manuel porte des paramètres.** Toujours d'après le guide, le
   « Open » du panneau expose trois encodeurs : projet, **partie**
   (ALL / FIXTURES / PRESETS), **fusion des presets**
   (replace / append / compact). Un event de rechargement devrait
   transporter ces deux enums en plus de l'identité du projet. Rien dans le
   vocabulaire du point 2 n'a cette forme.

**Lecture** : la prémisse du lead SETP-02 (« WTOOLS pousse des éditions en
direct ») ne survit pas à la documentation du vendeur lui-même. Le
phénomène décrit se réduit très probablement à l'écran LIVE de WTOOLS, qui
**rappelle** des presets — comportement déjà reproduit hands-off par
`SET_PRESET.f2`. Statut : **[observed]**, pas plus. Une lecture de noms
n'est pas une mesure du fil : elle ne peut pas exclure un event que WTOOLS
enverrait sans lui donner de nom lisible.

### Prédictions chiffrées, publiées avant la capture USB

Ordre honnête : la lecture statique ci-dessus a précédé ces prédictions ;
elles portent donc sur ce que la capture différentielle montrera.

1. **Aucun event de rechargement n'existe dans le protocole** (donc aucun
   id inconnu ne remplace la copie vive) — **p ≈ 0,8**. Réfutable : un id
   hors table apparaît en (b) et, rejoué seul, fait basculer le
   discriminateur.
2. Capture (a) — WTOOLS ouvert, navigation sans transfert : le flux
   sortant se réduit à `GET_SETTINGS` (21), `GET_PROJECT_LIST` (4),
   `GET_PROFILE_LIST` (2), plus **au plus un** id inconnu émis
   **périodiquement** (période < 2 s, charge utile vide ou constante). Cet
   id-là, s'il existe, est le `keepAlive`/`handshake` du point 2 —
   **pas** un rechargement — et sa périodicité le prouve. **p ≈ 0,7**.
3. Capture (b) — « sync » d'un projet vers le W1 depuis l'écran Projects :
   la séquence sortante est `SET_PROJECT` (18) — éventuellement fragmentée,
   avec `RETURN_PROGRESS` (20) en retour — et **rien d'autre hors table**.
   **p ≈ 0,75**.
4. Après (b), sans toucher le panneau : le discriminateur SETP-02 dit
   **copie vive inchangée** — une position présente seulement dans
   l'ancienne copie peint encore (> 25 canaux changés vs Startup).
   **p ≈ 0,85**.
5. **Si** malgré tout un id inconnu apparaît en (b) seul, classement a
   priori du suspect, par les trous et la sémantique de voisinage :
   **17** (seul trou du bloc projet 16 `DELETE_PROJECT` / 18 `SET_PROJECT`)
   ≈ 0,35 · **40 ou 42** (bloc « action panneau » 39 `SET_MODE`,
   41 `SET_PRESET`, 43 `SKIP_PRESET` — l'ouverture est un écran) ≈ 0,20 ·
   **13/14/15** (bloc pré-projet, plus probablement les jumeaux profils
   `setProfile`/`deleteProfile`) ≈ 0,20 · **22–38** (bloc de 16, plutôt
   firmware/flash/licence) ≈ 0,15 · **0/1/10/11** (0 = sentinelle,
   10/11 = paire enable/disable par symétrie avec 6/7 et 8/9) ≈ 0,10.
   Charge utile attendue si c'est 17 : l'UUID du projet, encodé comme dans
   `DELETE_PROJECT`, **plus** deux varints (partie, fusion) — l'absence de
   ces deux varints serait un indice fort que l'event n'est pas un
   rechargement.

### Capture — protocole et état

Pré-requis mesuré sur cette machine : `ifconfig -a` n'expose **aucune**
interface `XHC*`, ni Wireshark ni `tshark` installés, Xcode absent (seuls
les Command Line Tools), SIP actif, macOS 26.6.2. Le premier pas est donc
un test à privilèges, sans installation :

```
sudo ifconfig XHC20 up && ifconfig XHC20
```

**Mesuré le 2026-08-26 — la capture USB n'est pas disponible sur cette
machine** — **[observed]** : `sudo ifconfig XHC20 up` répond *interface
XHC20 does not exist*. Cause : les interfaces `XHC*` étaient fournies par
l'ancien kext `IOUSBFamily` (Intel) ; cette machine est en **arm64** et ne
charge que `IOUSBHostFamily` (dext), qui n'expose aucune interface de
capture. Aucune installation ne crée `XHC20` ici — ni Wireshark, ni
« Additional Tools for Xcode ». Le sniff du bus est donc **hors de portée
sans sonde matérielle** (analyseur USB externe).

**Ce qui n'est PAS une alternative** : sonder à l'aveugle les ids
inconnus depuis notre outil. Le vocabulaire lu au point 2 place
`setFirmware`, `setFlashData` et `factoryReset` dans ce même espace d'ids.
Envoyer un id inconnu, c'est l'exécuter s'il existe. L'invariant « aucune
opération firmware, jamais » couvre exactement ce geste.

**Statut de RELOAD-01 : mécanisme non mesurable ici.** Reste RELOAD-02,
qui mesure l'*effet* au lieu du mécanisme et ne demande aucun privilège.

### À ne pas oublier au moment de décoder

Réutiliser `wolfmix.read_frame` (resynchronisation sur `VERSION`), pas un
second décodeur : extraire la charge utile bulk du pcap et la lui donner
en flux. Séparer les deux sens par l'endpoint du bloc d'en-tête USB, pas
en devinant depuis l'event.

## RECALL-01 — la valeur du varint de `SET_PRESET` est ignorée : rétractation de l'adressage — 2026-08-27

Mesuré en préparant la baseline de RELOAD-02, W1 MK1 fw 2.0.18, projet vif
= le fichier clairsemé de PRESET-07 (87 entrées), DMX débranché.

### Ce qui a été mesuré — **[device-confirmed]**

1. **Deux sorties, pas plus.** Flux DMX continu (un seul
   `ENABLE_USB_DMX`, rappels injectés dedans) :

   | t | envoyé | effet |
   |---|---|---|
   | 2 s | `f1=23` | rien — l'oscillation 90↔124 canaux non nuls continue |
   | 8 s | `f1=22` | rien |
   | 14 s | `f2=23` | **transition** (pic à 75 canaux changés), se pose à 117 non nuls / 49 animés |
   | 20 s | `f1=76` | **transition** retour à l'oscillation 90↔124 |

   Confirmé par enveloppes : `f1∈{1,22,23,30}` donnent des enveloppes
   **strictement identiques** (0 canal disjoint, maxDiff 0) ;
   `f2∈{0,1,22,23,30,80}` de même ; A (un `f1` quelconque) vs B (un `f2`
   quelconque) = 14 canaux disjoints, 58 canaux de maxDiff.
   **Seule la présence du champ agit ; la valeur du varint n'agit pas.**
2. **Le moteur répond bien aux presets** : un appui sur le pad page 1
   colonne 2 ligne 3 (« Sequenced Sweep ») fait passer la sortie de
   49 animés / 117 non nuls à 75 / 127, 17 canaux à enveloppes disjointes.
   Ce n'est donc pas le sous-système preset qui est muet, c'est notre
   adressage USB.
3. **Le nom du pad situe la grille** : « Sequenced Sweep » est l'entrée 9 du
   fichier vif. Colonne 2, ligne 3 → slot 10 ⇒ **la grille est 4 colonnes ×
   5 lignes**, `slot = (ligne−1)·4 + colonne`. Confirme aussi que le projet
   vif est bien `WMX EXP format-lab` clairsemé.
4. **Aucun clone dans le fichier** : les 87 entrées ont 87 empreintes
   distinctes (payload hors `f19` id et `f25` nom). L'explication
   « apparences identiques parce que clones du même donneur » est donc
   **fausse** ; les enveloppes identiques du point 1 ne peuvent pas être
   mises sur le compte du contenu.

### Rétractations

- **PRESET-07, « `SET_PRESET.f2` = position d'entrée 0-based écrêtée » :
  RÉFUTÉ.** Tout ce qui le portait — 85/86/92/99 rendant des trames
  identiques, 92 « peint encore » — est exactement ce que prédit « valeur
  ignorée ». L'écrêtage n'a jamais été observé : il a été *inféré* d'une
  égalité qui a une cause plus simple.
- **SETP-01, « `f1` = varint(id) rappelle (23 Deep Red, 22 Deep Green) » :
  CONTESTÉ.** Aujourd'hui `f1=22` et `f1=23` sont indiscernables au canal
  près. Reste ouvert : cette mesure avait été faite sur l'autre projet vif
  (101 presets) ; l'adressage marche peut-être là et pas ici.
- **Conséquence en cascade sur SETP-02.** Les quatre négatifs de
  rechargement (RESTART, delete-store-restart, cycle moteur) ont été jugés
  au discriminateur « la position bouche-trou peint encore ». Si la valeur
  est ignorée, ce discriminateur ne distingue pas les copies : **les
  négatifs de SETP-02 ne sont plus établis**. Ils ne sont pas réfutés non
  plus — le seul élément indépendant qui subsiste est l'observation
  visuelle au panneau après l'ouverture manuelle (page 5 et page 6
  conformes au fichier clairsemé), qui prouve que l'ouverture manuelle
  recharge, pas que les events ne rechargent pas.
- **Recette générateur** : la dernière étape (« rappel hands-off par
  `SET_PRESET.f2` ») repasse de device-confirmed à **ouverte**. Le
  transfert et l'ouverture manuelle unique restent acquis.

### Ce qui reste à trancher, par ordre de coût

1. **Une ouverture manuelle d'un autre projet** (« rig-c », 101
   presets) puis `f1=22` vs `f1=23` : reproduit SETP-01 à l'identique. Si
   l'adressage marche là, le suspect devient le fichier clairsemé
   lui-même — ce qui intéresse directement le générateur. Sinon, la
   rétractation est totale.
2. Sémantique réelle de la charge utile : deux sorties stables pour « un
   `f1` quelconque » et « un `f2` quelconque » ressemblent à deux
   *défauts* de décodage, pas à un adressage. Candidat à tester :
   la cible n'est pas un varint nu mais un sous-message (wire type 2).
3. RELOAD-02 (poussée WTOOLS + discriminateur) est **suspendu** : un
   discriminateur qui ne distingue pas deux presets ne distinguera pas
   deux copies.

Note de méthode : la première lecture de la séance — « les rappels sont
inertes » — était fausse et est retirée. Les rappels agissent ; ils
agissent seulement toujours pareil. La sonde à enveloppes séparées ne
pouvait pas distinguer « rien ne bouge » de « on repeint la même chose » ;
c'est le flux continu, avec les transitions horodatées, qui a tranché.

## RECALL-02 — l'event 41 n'adresse rien : ce qu'il fait vraiment — 2026-08-27

Projet vif : le projet donneur `f2737ec3` (101 presets), ouvert au panneau —
c'est-à-dire **le projet même sur lequel SETP-01 avait été mesuré**. W1 MK1
fw 2.0.18, mode 0 (HOME), DMX débranché. Méthode : un seul flux DMX continu,
une empreinte de trame complète prise 4 s après chaque commande, aucune
comparaison entre fenêtres de capture séparées.

### Mesures — **[device-confirmed]**

1. **`f1` = un état absolu, idempotent.** `f1=23`, `f1=22`, `f1=76` donnent
   des trames **identiques au canal près** (0 écart), et cette empreinte
   (75 canaux non nuls, somme 10455) revient à l'identique après n'importe
   quelle autre manipulation, y compris dix `SKIP_PRESET`.
   **SETP-01 ne se reproduit pas sur son propre projet** : « f1=23 → Deep
   Red, f1=22 → Deep Green » est **réfuté**, pas seulement contesté.
2. **`f2` = un état qui dépend du contexte courant** : `f2=23` en début de
   séance donnait 70 non nuls / somme 10013 ; `f2=0` après une série de
   skips donne 87 / 9462. La valeur ne change rien, le contexte si.
3. **`f3`, `f4`, `f5` = des bascules.** Séquence `f3` = 0, 1, 2, 10, 50,
   100, 200, 1, 0 → sommes 5544, 8606, 5548, 8606, 5490, 9140, 5490, 9140,
   5490 : **alternance bas/haut calée sur le rang de l'envoi**, pas sur la
   valeur. `f3=10` rend exactement l'empreinte de `f3=1` (0 canal d'écart) ;
   `f3=1` rend deux empreintes différentes selon son rang. Un adressage ne
   peut pas faire ça.
4. **Forme imbriquée** `f1={f1:v}` (`0a 02 08 v`) : 8 canaux d'écart entre
   v=23 et v=1 — même famille de bascules, aucun adressage.
5. **`SKIP_PRESET` (43) parcourt bien des presets** : dix envois → dix
   empreintes distinctes (non nuls 93, 56, 59, 89, 97, 85, 83, 85, 51, 73).
6. `projectChanged` reste `false` de bout en bout : rien n'est écrit dans le
   projet, ces sondes ne touchent que l'état vif.

### Lecture

L'event 41 ne transporte **aucune cible numérique** dans les champs 1 à 5,
ni en varint nu ni en sous-message. Il agit sur un **état courant** — une
sélection — que `SKIP_PRESET` déplace. La télécommande du W1 existe donc,
mais elle est **relative** (avancer, basculer), pas **adressée** (« joue le
preset n »). Tant que la cible n'est pas trouvée, aucun rappel hands-off
d'un preset choisi n'est acquis.

Ce qui reste vrai de SETP-01 : `SET_PRESET` est bien accepté et **agit** sur
la sortie. Ce qui tombe : la lecture « f1 = id », et avec elle la dernière
étape de la recette du générateur.

### Réparation du discriminateur de RELOAD-02

Un discriminateur qui n'a pas besoin d'adressage : **compter les apparences
distinctes sur N `SKIP_PRESET`**. Contrôle fait aujourd'hui sur 101 entrées :
10 skips → 10 apparences distinctes, aucune répétition.

**Formulation corrigée le 2026-08-27 (RELOAD-05)** : le falsificateur n'est
PAS « une répétition au 7e skip » — la calibration a montré qu'une vraie copie
à 6 entrées rend **8 apparences sur 10**, la seule paire de décalage 6 dans les
sept premiers skips (1 contre 7) tombant à 31 canaux, au-dessus du seuil. Le
falsificateur est **« moins de 10 apparences ET une périodicité dans les
distances »**. Publier l'ancienne formulation ferait passer un vrai
rechargement pour une absence de rechargement. La poussée WTOOLS se juge
ainsi, hands-off :

- 10 skips avant la poussée → attendu 10 distinctes (copie à 87 entrées) ;
- 10 skips après la poussée → 10 distinctes = **pas de rechargement** ;
  < 10 distinctes **avec une périodicité lisible** = **rechargement**.

Réserves explicites, et elles comptent :
- L'ordre exact du parcours (positions ? pages ? entrées vides sautées ?)
  n'est **pas** établi. Le test ne repose que sur « moins d'entrées ⇒
  répétitions plus tôt ».
- ~~Le bras positif de l'instrument n'a jamais été observé.~~ **Levé le
  2026-08-27, voir RELOAD-05** : sur la copie vive à 6 entrées, la même série
  rend 8 apparences sur 10, et les quatre paires distantes de six skips sont
  les quatre plus proches de la série. Le parcours est cyclique, de période
  égale au nombre d'entrées.
- Une répétition peut **ne pas ressembler à une répétition** — vérifié : deux
  des quatre retours au même preset diffèrent de 16 et 31 canaux (phase des
  effets). Le seuil sous-compte, d'où le falsificateur reformulé en
  « moins de 10 apparences **et** une périodicité dans les distances ».

## RELOAD-02 mesuré — une poussée WTOOLS ne remplace pas la copie vive — 2026-08-27

Discriminateur : nombre d'**apparences distinctes sur 10 `SKIP_PRESET`**
(RECALL-02), seuil « même apparence » = moins de 8 canaux d'écart et
amplitude < 32. Aucun adressage requis, donc immunisé à la rétractation
RECALL-01. W1 MK1 fw 2.0.18, DMX débranché, `projectChanged` false du début
à la fin.

| Étape | Mesure |
|---|---|
| Copie vive = fichier clairsemé (87 entrées) — **ré-ouverte au panneau par l'opérateur juste avant**, sur demande — avant poussée | **10 apparences distinctes / 10 skips** (paire la plus proche : 13 canaux, amplitude 139) |
| Poussée du fichier à 6 entrées depuis WTOOLS 2.0.2, WTOOLS refermé, **aucun geste au panneau** | — |
| Après poussée | **10 apparences distinctes / 10 skips** |

Si la copie vive était passée à 6 entrées, une répétition était forcée au 7e
skip au plus tard. Elle n'a pas eu lieu. **La poussée WTOOLS ne rend pas
vivant le projet qu'elle vient d'envoyer.** — **[device-confirmed]**

### Un fait révélé par la même manipulation

WTOOLS **ré-attribue un UUID** au fichier importé : la liste des projets du
contrôleur montre l'original `<experiment-uuid>` (45112 o) intact, **plus** une
nouvelle entrée `ad80395f…` (15684 o = notre fichier au bit près) portant le
**même nom** `WMX EXP format-lab`. Deux projets homonymes coexistent.
Son estampille de version est `1787769278710000`, mille fois l'ordre de
grandeur des estampilles écrites par l'appareil (`1787766751371`) —
**[observed]**, candidat : microsecondes côté WTOOLS, millisecondes côté
firmware. — **[device-confirmed]** pour la ré-attribution.

Conséquence sur la portée : ce qui est mesuré est « la poussée ne rend pas
vivant le projet poussé ». La variante stricte — pousser de **nouveaux
octets sous le même UUID** et voir si la copie vive se rafraîchit — est
**hors de portée par WTOOLS**, qui ré-identifie systématiquement. Elle reste
testable par notre outil, qui écrit sous UUID dérivé constant.

### Ce que ça ferme, ce que ça laisse ouvert

- **Ferme** : la prémisse du lead SETP-02 (« WTOOLS pousse des éditions qui
  apparaissent en direct, donc l'event de rechargement existe et transite »)
  est **réfutée par la mesure**, après l'avoir été par la documentation du
  vendeur (RELOAD-01). Rien ne devient vivant sans geste au panneau.
- **Laisse ouvert** : les quatre négatifs de SETP-02 (RESTART,
  delete-store-restart, cycle moteur), toujours à re-prouver avec le
  discriminateur réparé — c'est maintenant faisable sans matériel humain, en
  déployant le fichier à 6 entrées sous l'UUID du bac-à-sable puis en
  comptant les apparences.
- **À nettoyer** : le doublon `ad80395f…` créé par WTOOLS sur l'appareil.
  Notre outil n'écrit que sous UUID dérivé ; cette suppression revient à
  l'opérateur, depuis WTOOLS.

## RELOAD-03 — re-preuve des négatifs de SETP-02 au discriminateur réparé — 2026-08-27

Les quatre négatifs de rechargement de SETP-02 avaient été jugés à un
discriminateur depuis réfuté (RECALL-01). On les rejoue au comptage
d'apparences sur 10 `SKIP_PRESET`, cette fois sous **le même UUID** — la
variante stricte que WTOOLS ne permet pas (RELOAD-02).

### Prédictions, publiées avant le déploiement

1. `deploy` (store du fichier à 6 entrées sous `<experiment-uuid>` + vérification
   octet-à-octet + RESTART) : le stockage passe, les deux vérifications
   passent. **p ≈ 0,95**.
2. Après le RESTART du deploy, 10 skips → **encore 10 apparences
   distinctes** : la copie vive reste celle à 87 entrées, FLASH-08
   re-confirmé avec un discriminateur valide. **p ≈ 0,85**.
   Falsificateur net : une répétition au plus tard au 7e skip.
3. Rival explicite : le RESTART recharge bel et bien, et le négatif
   d'origine n'était qu'un artefact du discriminateur réfuté. **p ≈ 0,15**.

### RELOAD-03 mesuré — **[device-confirmed]**

`deploy` du fichier à 6 entrées sous `73d06df4…` : stockage accepté
(15684 o, « Hooray! »), les deux vérifications par re-téléchargement passent
(comparaison enregistrement par enregistrement), RESTART inclus. Prédiction
1 confirmée.

Puis, sans toucher au panneau : 10 skips → **10 apparences distinctes**.
Aucune répétition, alors qu'une copie vive à 6 entrées en forçait une au 7e
skip au plus tard. **La copie vive reste celle à 87 entrées après
store + RESTART sous le même UUID.** Prédiction 2 confirmée, rival 3 écarté.

Corroboration de rang à rang avec la série d'avant la poussée : les rangs 3
et 10 rendent des trames **identiques au canal près**, les rangs 1 et 8 à
1–4 canaux près (amplitude 1) ; les six autres diffèrent, ce qu'explique la
phase des effets animés. Le parcours du skip est donc **le même parcours,
au même point de départ** — la copie vive n'a pas bougé.

**FLASH-08 est re-prouvé avec un discriminateur valide** : le RESTART ne
recharge pas. Les trois autres négatifs de SETP-02 (delete-store-restart,
cycle moteur) restent à rejouer de la même manière.

## RAW-01 — la charge utile n'est PAS du protobuf : l'octet 0 est l'index — 2026-08-27

Découvert en balayant les champs de `SET_MODE`. Ce que l'appareil a répondu,
`f<N>=0` signifiant une charge utile `[(N<<3)|0, 0x00]` :

| Envoyé | Octets | Mode obtenu |
|---|---|---|
| `f1=0` | `08 00` | 8 |
| `f2=0` | `10 00` | 16 |
| `f3=0` | `18 00` | 24 |
| `f4=0` | `20 00` | 32 |
| `f5=0` | `28 00` | 42 (≠ 40 : à re-mesurer) |
| `f6=0` | `30 00` | **erreur « Mode index too high »** |

8, 16, 24, 32 sont exactement `0x08, 0x10, 0x18, 0x20` — **l'octet de tag
protobuf lui-même**. Lecture : pour cet event, le firmware ne parse pas du
protobuf ; il lit **l'octet 0 de la charge utile comme l'index**. Nos
« champs » n'étaient qu'un octet de tag pris pour une valeur, et c'est
pourquoi la valeur qui suivait n'a jamais rien changé — ni ici, ni sur
`SET_PRESET` (RECALL-01/02).

### Prédictions, publiées avant la mesure

1. `SET_MODE` avec la charge utile d'**un seul octet** `1a` (26) amène le
   panneau sur **mode 26 = PROJECTS**, l'écran « main menu → Open » dont
   l'usage manuel recharge le projet. **p ≈ 0,8**.
2. `SET_MODE` `00` → mode 0 (HOME), `05` → mode 5 (PRESETS) : l'octet est
   l'index, sans décalage. **p ≈ 0,8**.
3. `SET_PRESET` avec un seul octet `17` (23) rappelle l'entrée 23 et non
   plus l'entrée 8 ; deux octets distincts donnent deux apparences DMX
   distinctes, le même octet répété fait **basculer** (les pads du panneau
   sont des bascules — c'est l'alternance observée en RECALL-02 sur `f3`,
   qui adressait en réalité toujours l'entrée 24). **p ≈ 0,7**.
4. Si (3) tient, le rappel adressé hands-off est **restauré**, et les
   rétractations de RECALL-01/02 se relisent ainsi : l'adressage existait,
   c'est notre encodage protobuf qui le masquait.

### RAW-01 mesuré — l'octet 0 EST l'index, sur les deux events — **[device-confirmed]**

`SET_MODE`, charge utile d'un seul octet, mode relu par `GET_SETTINGS` :

| Octet envoyé | 0 | 5 | 26 | 16 | 0 |
|---|---|---|---|---|---|
| Mode obtenu | 0 | 5 | **26** | 16 | 0 |

**5 sur 5.** Prédictions 1 et 2 confirmées. `1a` seul n'est pas du protobuf
valide (en-tête tronqué d'un champ length-delimited) et donne pourtant le
mode 26 : le firmware lit bien `payload[0]`, il ne parse pas.
**Le mode 26 « main menu → Open » est donc atteignable à distance.**

`SET_PRESET`, charge utile d'un seul octet, sur le projet clairsemé vif :

| Envoyé | 1 | 5 | 1 | 5 | 1 |
|---|---|---|---|---|---|
| Empreinte | 130 non nuls / 19111 | 102 / 15287 | 130 / 19111 | 102 / 15287 | 130 / 19111 |

Les trois envois de `01` rendent la **même trame au canal près** (0 écart,
trois fois) ; les deux envois de `05` aussi ; `01` vs `05` = 88 canaux
d'écart. **Le rappel adressé, déterministe et reproductible, est restauré.**
Prédiction 3 confirmée pour la partie adressage ; la « bascule » supposée
n'en était pas une (voir ci-dessous).

### Relecture des rétractations — l'adressage existait, notre encodage le masquait

Nos charges utiles « protobuf » étaient `[tag, valeur]`. Le firmware lisait
le **tag** : `f1=<v>` → `08` → toujours l'entrée **8** ; `f2=<v>` → `16` ;
`f3=<v>` → `24` ; `f4=<v>` → `32` ; `f5=<v>` → `40`. D'où, mécaniquement :
une apparence par « champ », insensible à la valeur. RECALL-01 et RECALL-02
ont **bien mesuré** ce qu'ils ont mesuré ; leur lecture (« la valeur est
ignorée, l'event n'adresse rien ») est **remplacée** par : nous n'avions
jamais envoyé l'index. Restent réfutées telles qu'écrites : « `f1` = id »
(SETP-01) et « `f2` = position écrêtée » (PRESET-07) — les deux décrivaient
un protobuf que le firmware ne lit pas. Ce que SETP-01 avait vu en croyant
rappeler l'id 23 était l'entrée **8**.

L'« alternance » de RECALL-02 sur `f3` (toujours l'entrée 24) se relit sans
bascule : un preset partiel — les pages usine séparent full / couleur /
move / beam — rappelé par-dessus un état animé ne redonne pas la même trame.
Sur les presets **complets** de la page 1 (octets 1 et 5), la reproduction
est exacte.

### Corroboration statique (WTOOLS 2.0.2, lecture de noms) — **[observed]**

- Les 15 classes protobuf que l'app désérialise (`X.fromBuffer`) sont
  `Beat, DmxPacket, PatchItem, PatchList, PbStatus, Profile, ProfileList,
  ProfileListItem, Progress, Project, ProjectList, ProjectListItem,
  RequestData, Settings, elementSettingsMsg_t`. **Aucun message de preset.**
- `_omitFieldNames` / `_omitMessageNames` : **zéro occurrence**. Les noms de
  champs ne sont donc pas retirés à la compilation — l'absence de `presetId`,
  `presetIndex`, `preset`, `id`, `idx` est **significative**, pas vacante.
- Le chemin de WTOOLS vers `setPreset` est un **bouton** (`getPresetButton`,
  `onPresetButtonPressed`, action OS2L « Set Wolfmix Preset ») — cohérent
  avec « appui de pad », pas avec un message porteur d'un champ cible.
- Rappel de prudence : les ids 39/41/43 viennent de `tools/wolfmix.py`, pas
  du binaire ; rien dans le binaire ne relie une classe à un id d'event, et
  le `.proto` n'est pas récupérable (aucun descripteur embarqué).

### Reste ouvert

1. **L'octet est-il un id ou une position ?** Elles ne divergent qu'en queue
   du fichier clairsemé (position 85 = id 99, position 86 = id 114).
   Un tir sur les octets 85, 86, 99, 114 tranche en une minute.
2. Le reste de la charge utile est-il lu (deuxième octet = paramètre) ?
3. `SET_PROJECT` et consorts restent bien protobuf : la lecture « octet 0 =
   index » vaut pour les events courts (39, 41), pas pour tout le protocole.

### MODE-40/42 — l'écran USB STICK, atteignable seulement par index brut — 2026-08-27 — **[device-confirmed]**

Envoyer l'index **40** à `SET_MODE` fait atterrir l'appareil sur le mode
**42**, que `GET_SETTINGS` rapporte et que l'opérateur identifie à l'écran :
**USB STICK**, avec import / export de projet, de fixtures, et full backup.
L'écran **tente une lecture dès son ouverture** : sans support (le MK1 n'a
pas de socket USB-A), il affiche « error reading project » ; tout bouton
*import* redonne la même erreur, *export* donne « error backing up data ».
C'est l'origine des deux écrans trouvés au matin après le balayage
d'index. Les boutons *import* et *export* ont été pressés **par l'opérateur**,
au panneau, pour caractériser l'écran. Vérifié après coup : `projectChanged`
est resté false, la liste des 6 projets est intacte avec les tailles
attendues, et **le projet bac-à-sable** (`73d06df4…`) se relit enregistrement
pour enregistrement identique à ce qui avait été déployé. Les cinq autres
projets n'ont pas été re-téléchargés : leur intégrité repose sur la liste,
pas sur une relecture.

Deux enseignements :
- `mode-map.md` classait `USB_STICK` et `FILE_BROWSER` comme inatteignables
  sur MK1. Ils le sont **par le menu**. L'index brut de `SET_MODE` ouvre des
  écrans que la navigation du panneau n'expose pas — donc ces sondes ne sont
  pas neutres, et un index inconnu peut déclencher une action (ici une
  lecture de média) sans validation de l'opérateur.
- L'identité index → mode n'est **pas** universelle : 0→0, 5→5, 16→16 et
  26→26 sont exacts, mais **40→42**. Candidat : 40 est un écran qui
  redirige (`FILE_BROWSER` ?) faute de matériel. À ne pas lire comme un
  décalage constant : quatre index sur cinq sont l'identité.

### PROJECTS-01 — l'écran « Open » est atteignable à distance — 2026-08-27 — **[device-confirmed]**

`SET_MODE` index **26** ouvre l'écran *main menu → Open*. L'opérateur
confirme à l'écran : la **liste des 6 projets** stockés, dont les **deux
`WMX EXP format-lab` homonymes** — l'original et le doublon ré-identifié par
WTOOLS (RELOAD-02). C'est l'écran dont l'usage manuel remplace la copie
vive. Manquent la sélection et la validation.

## RELOAD-04 — verdict : l'event de rechargement n'existe pas dans la surface atteignable — 2026-08-27

Question de la séance : quel event du protocole USB remplace la copie vive
sans geste au panneau. **Réponse : aucun**, et la chaîne de preuve est
maintenant complète.

| Preuve | Statut |
|---|---|
| Le guide embarqué du vendeur énumère les fonctions de WTOOLS 2.0.2 : sync BPM, 3D Link, add-ons, sync projets, sync profils, lock/unlock, factory reset, renommage. **Aucun éditeur, aucun rechargement.** | observed |
| La surface API contrôleur du binaire ne contient **aucun verbe de chargement** (`loadProject`, `openProject`, `reloadProject`, `setActiveProject`… tous absents ; les seuls `load…` chargent un fichier dans l'app). | observed |
| Une poussée WTOOLS **ne rend pas vivant** le projet poussé (10 apparences distinctes sur 10 skips, avant comme après). | device-confirmed |
| `store` + `RESTART` **sous le même UUID** ne recharge pas non plus (même mesure, plus la reproduction rang à rang du parcours de skip). | device-confirmed |
| L'écran qui recharge — mode 26, *main menu → Open* — **est atteignable à distance** par index brut, liste des 6 projets à l'écran. | device-confirmed |
| Sur cet écran, **`SKIP_PRESET` ne déplace rien** (trois envois espacés de 3 s) et **`SET_PRESET` avec l'octet 0 ne fait rien** (un envoi) : l'opérateur regardait le panneau et rapporte « il ne s'est rien passé ». Observation à l'œil, pas mesure instrumentée — le DMX n'était pas capturé. | observed (opérateur) |
| Le binaire WTOOLS ne porte **aucune primitive d'entrée à distance** (encodeur, appui, touche) : `onPresetButtonPressed`/`onNavigationButtonPressed`/`onModeButtonPressed` sont les boutons de son interface Flutter, `setEncoderColour` ne pilote que des LED. | observed |

**Lecture.** Le protocole expose le *changement de mode* et le *déclenchement
de preset*, pas l'*entrée utilisateur*. (L'inertie sur l'écran Open est une
observation à l'œil ; la ré-instrumenter au DMX la durcirait.) On peut amener le panneau devant la
liste des projets ; on ne peut ni y déplacer le curseur ni valider. Le
rechargement reste **un geste manuel irréductible**, et la prémisse de départ
(« WTOOLS pousse des éditions qui apparaissent en direct ») était fausse :
WTOOLS n'édite rien, il transfère.

**Incertitude résiduelle, assumée.** Les ids d'events jamais émis
(0, 1, 10, 11, 13–15, 17, 22–38, 40, 42, 45+) restent non testés. L'un d'eux
pourrait être une primitive d'entrée. Nous ne les sondons pas à l'aveugle :
le vocabulaire lu dans le binaire place `setFirmware`, `setFlashData` et
`factoryReset` dans ce même espace, et MODE-40/42 vient de démontrer qu'un
index inconnu peut déclencher une action sans validation. Trancher demanderait
une capture du bus USB — impossible sur cette machine arm64 (RELOAD-01) — ou
une sonde matérielle.

### Ce que la séance a acquis, malgré la réfutation

- **Les events courts ne sont pas du protobuf** : `payload[0]` est l'index
  (RAW-01). Le rappel adressé est restauré, déterministe au canal près.
- Un discriminateur de copie vive **sans adressage** : le comptage
  d'apparences distinctes sur 10 `SKIP_PRESET`.
- WTOOLS **ré-attribue un UUID** à l'import (deux homonymes sur l'appareil).
- Mode **42 = `USB_STICK`**, atteignable seulement par index brut.
- La recette du générateur, à jour : transfert **à distance**, rechargement
  **un geste manuel**, rappel **à distance et adressé**.

## RECALL-03 — l'octet de `SET_PRESET` est l'**id**, pas la position — 2026-08-27 — **[device-confirmed]**

Copie vive : 87 entrées, positions 0..86, ids 0..84 puis 99 et 114 — les deux
lectures ne divergent qu'en queue. Matrice des écarts entre trames (canaux
différents), octets rappelés un à un, DMX en flux continu :

```
       5    84    85    86    99   114   200
  5    0    32    32    32    94    59    59
 84   32     0     0     0    93    60    60
 85   32     0     0     0    93    60    60
 86   32     0     0     0    93    60    60
 99   94    93    93    93     0   111   111
114   59    60    60    60   111     0     0
200   59    60    60    60   111     0     0
```

Trois groupes : **{84, 85, 86}**, **{99}**, **{114, 200}**.

- Lecture « **position** » : 84, 85, 86 sont trois entrées différentes — elles
  devraient donner trois trames différentes. Elles n'en donnent qu'une.
  99, 114 et 200 sont tous hors domaine — ils devraient s'écraser sur le même
  écrêtage. 99 s'en distingue par 111 canaux. **Réfutée deux fois.**
- Lecture « **id** » : 84, 99 et 114 sont les trois derniers ids existants,
  et ils rendent trois trames distinctes. C'est le point décisif : sous la
  lecture « position », 99 **et** 114 seraient tous deux hors domaine et
  devraient donner **le même** résultat. Ils diffèrent de 111 canaux.
- Ce que la matrice ci-dessus ne dit **pas** : ce que devient un id absent.
  Les zéros (85 ≡ 84, 200 ≡ 114) ont une cause plus simple que l'écrêtage,
  voir la rétractation ci-dessous.

**Confirmation visuelle par l'opérateur**, qui a suivi le panneau pendant le
tir : le surlignage est passé par le 5e pad de la page 5 — `id = (5−1)·20 +
(5−1) = 84` — puis « preset test auto » (id 99, dernier pad de la page 5),
puis « Test » (id 114, page 6). Exactement les trois groupes, dans l'ordre.

**Ce qui est device-confirmed** :

> `SET_PRESET`, charge utile = **un octet = l'id du preset** — pas la position
> d'entrée. Un id existant rappelle son preset.

**Règle de résolution d'un id absent : RETIRÉE, question OUVERTE.** Elle avait
été publiée comme « plancher » sur la foi des zéros de la matrice et d'un tir
sur l'octet 92. Un audit adversarial du même jour a montré que **le rival
« un id absent ne fait rien » reproduit toutes les cellules** : les tirs
étaient en ordre croissant, donc un no-op laisse la trame du tir précédent —
85 après 84 rend F84, 200 après 114 rend F114, et 92 avait 84 pour
prédécesseur immédiat. Aucun des deux tirs ne discriminait quoi que ce soit.

Les re-mesures à historique constant (remise à un preset de référence avant
chaque tir) n'ont pas tranché non plus, et ont exhibé trois confusions qu'il
faudra maîtriser pour y arriver :

1. **Les presets sont partiels** — les pages usine séparent full / couleur /
   move / beam. La trame obtenue dépend donc de ce qu'il y avait dessous :
   comparer deux tirs d'historiques différents ne prouve rien.
2. **Le rig anime en permanence.** Un même rappel se re-mesure à 32 canaux
   d'écart en trame unique ; le plancher de bruit dépasse l'effet cherché.
   L'oracle prévu pour ça est l'enveloppe min/max, pas la trame.
3. **Le fondu, ou une garde d'anti-rebond, avale des rappels** : depuis une
   remise à l'id 114, un rappel de 84 envoyé 4 s plus tard ne prend pas,
   alors qu'il prend depuis une remise à l'id 5. Tant que ce délai n'est pas
   caractérisé, tout protocole « remise puis tir » est suspect.

Candidats encore en lice pour un id absent : **no-op**, **plancher**,
**écrêtage à la dernière entrée**, **état commun distinct**. Le tir qui
tranchera devra être jugé à l'enveloppe, à historique constant, et avec un
délai de remise mesuré — pas supposé.

Encodée dans l'outil : `wolfmix.py preset <id>` et `wolfmix.py mode <index>`,
avec `index_payload()` et son self-check (l'octet 23 doit partir en `0x17`,
jamais en `08 17`).

### Ce que ça referme

- **PRESET-07 est renversé** : `f2` = position écrêtée était faux sur les deux
  points — ce n'est ni `f2`, ni une position. C'est l'octet 0, et c'est l'id.
- **SETP-01 avait raison sur la sémantique** (« l'id ») et tort sur
  l'encodage ; ses deux mesures restent invalides — la charge utile `08 17`
  rappelait l'id 8.
- **La recette du générateur est complète et hands-off à un geste près** :
  écrire les entrées avec la formule d'id (trous tolérés), déployer à
  distance, **une ouverture manuelle**, puis rappeler n'importe quelle entrée
  à distance par `SET_PRESET` avec **un octet = l'id**.

Note pour l'opérateur : chaque rappel **change le preset joué en direct** —
c'est visible au panneau et sur la sortie DMX. Rien n'est écrit en mémoire
(`projectChanged` reste false du début à la fin), mais l'état vif bouge à
chaque tir.

## SCREEN-01 — le mode rapporté n'est pas l'écran affiché — 2026-08-27 — **[device-confirmed]**

Séquence envoyée à `SET_MODE`, un index toutes les 5 s, l'opérateur regardant
le panneau, l'appareil partant de l'écran Projects :

| Envoyé | `wolfmixMode` relu | Écran affiché |
|---|---|---|
| 5 | 5 | **Projects** (inchangé) |
| 0 | 0 | **Projects** (inchangé), **LED HOME allumée** |
| 26 | 26 | Projects |
| 0 | 0 | **Projects** (inchangé) |
| 1 | 1 | **COLOR FX** — la façade suit enfin |

Trois faits, tous nouveaux :

1. **`wolfmixMode` répond docilement l'index envoyé, sans que la façade
   bouge.** Le readback n'est donc **pas** une preuve de ce qui est affiché.
   Le `mode-map` a été bâti dans le sens panneau → readback, qui reste
   valide ; c'est le sens télécommande → écran qui ne l'est pas.
2. **L'état interne suit bien** : la LED HOME s'allume quand on envoie 0,
   pendant que l'écran montre Projects. Le firmware tient donc deux choses
   distinctes — un mode de navigation/moteur, et une façade.
3. **L'écran Projects est modal** : seul l'index 1 (COLOR FX) l'a fait céder
   dans cette séquence. — **[RÉTRACTÉ le 2026-08-27]** la clause « appuyer sur
   HOME au panneau ne le quitte pas non plus » : le même opérateur rapporte
   l'inverse le lendemain, sur une autre copie vive (SCREEN-03). Les deux sont
   des rapports verbaux, non instrumentés, et la variable qui a changé entre
   les deux (projet ouvert ? état hérité ?) n'est pas contrôlée. **Ce que fait
   la touche HOME depuis l'écran Projects est ouvert.**

### Conséquences

- **Rectification de PROJECTS-01** : « l'écran Open est atteignable à
  distance » reste vrai (l'opérateur l'a lu à l'écran), mais il faut y
  ajouter : **on entre, on ne sort pas** par `SET_MODE 0` ni `5`, et le
  panneau lui-même est piégé. Un `mode 26` envoyé sur un appareil en
  exploitation immobilise la façade devant la liste des projets.
- **Ça éclaire l'inertie mesurée sur cet écran** (RELOAD-04) : `SKIP_PRESET`
  et `SET_PRESET` n'y font rien parce que la façade est en attente d'une
  action locale, alors même que le protocole continue de répondre « Hooray! ».
- **Danger d'exploitation** à documenter dans `docs/device.md` : `mode` avec
  un index modal (26, 42) laisse l'appareil dans un état dont l'opérateur ne
  sort pas par HOME.

## SCREEN-02 — comment sortir d'un écran modal, et ce que ça dit du menu — 2026-08-27 — **[device-confirmed]**

Quatre essais, chacun : ouvrir Projects (index 26), attendre 6 s, envoyer un
candidat, attendre 7 s. Ordre exact des **neuf** envois, tel que le script les
a émis :

    26, 8, 26, 16, 26, 3, 26, 33, puis 1 (remise)

L'opérateur a relevé la suite des écrans affichés :

> PROJECT, GOBO, PROJECT, MOVE FX, PROJECTS, BLACKOUT, COLOR FX

Sept écrans pour neuf envois — la lecture est forcée : les deux envois
manquants sont ceux qui **n'ont rien changé**. Le candidat 16 laisse l'écran
sur Projects, et la réouverture de l'essai 3 tombe sur un écran déjà là.

| Index | Écran | Sort du modal ? |
|---|---|---|
| 1 | COLOR FX | **oui** |
| 3 | MOVE FX | **oui** |
| 8 | GOBO | **oui** |
| 33 | BLACKOUT | **oui** |
| 0 | HOME | non |
| 5 | PRESETS | non |
| 16 | SETUP, le menu parent | **non** |

**Lecture proposée — [hypothesized], pas mesurée.** La ligne de partage n'est
pas « touche physique contre écran » : PRESET est une touche physique et ne
sort pas. Elle sépare — sur sept points seulement — les écrans qui
**agissent sur la sortie lumière** (racks FX, gobo statique, blackout) de ceux
qui ne font que **naviguer** (HOME, grille des presets, menu principal). Un
rival tient aussi bien sur ces sept points : « touches FX et flash contre les
trois racines de navigation ». Prédiction publiée avant mesure pour les
départager : sous le rival, **30 (SPEED)** et **28 (WOLF)** sortent du modal ;
sous la règle proposée, non. **44 (BPM)** ne sort sous aucune des deux.

### Deux conséquences

- **Échappatoire fiable, à documenter** : pour libérer une façade coincée,
  envoyer 1, 3, 8 ou 33. C'est utile au-delà de nos sondes, puisque la touche
  HOME du panneau n'y suffit pas non plus.
- **Le menu parent ne reprend PAS la main** (16 ne sort pas de 26). La
  hiérarchie de navigation n'écoute donc plus quand un modal est ouvert :
  le chemin « Open → sélection → validation » n'est pas pilotable par des
  changements de mode. **RELOAD-04 est confirmé par un troisième angle.**
  Cette conséquence-là ne dépend pas de la lecture ci-dessus : elle tient au
  seul point 16, mesuré.

## RAW-02 — le deuxième octet n'est pas lu — 2026-08-27 — **[device-confirmed]**

Question laissée ouverte par RAW-01 : la charge utile au-delà de `payload[0]`
sert-elle à quelque chose ?

**`SET_MODE`** — cinq charges utiles, mode relu à chaque fois :
`05` → 5, `05 00` → 5, `05 c8` → 5, `08` → 8, `08 ff` → 8. **Le mode ne
dépend que de l'octet 0.**

**`SET_PRESET`** — d'abord un faux positif, gardé ici parce qu'il a failli
passer : `63 ff` (id 99 + 0xff) rendait une trame à 27 canaux d'écart du tir
nu `63`, alors que `63 00` et `63 07 07 07` étaient identiques. Le contrôle
qui tue l'hypothèse est le **dernier tir de la série, un `63` nu** : il
diffère lui aussi du premier `63` des mêmes 27 canaux. L'écart suit donc un
**état de l'appareil qui a changé en cours de série et n'est pas revenu**,
pas la charge utile. Sans ce contrôle, on écrivait « le 2e octet est un
drapeau ».

**Et ce n'est pas non plus un fondu.** Une empreinte posée 4 s après le
rappel ne verrait pas un paramètre de fondu ; on a donc capturé le
**transitoire**, distance à la trame finale échantillonnée dès l'envoi.
Les courbes de `63` et de `63 ff` se superposent (pic ≈ 10 000, mêmes
valeurs à chaque palier, stabilisation à 4,0 s dans les quatre passes) — et
l'oscillation qu'on y voit est celle de l'effet animé du preset, pas une
rampe.

**Portée** : aucun effet observable sur le mode atteint, sur la trame
stabilisée, ni sur le transitoire à 4 s. Cela n'exclut pas un effet sur
quelque chose que nous n'observons pas (un paramètre qui ne toucherait ni
l'écran ni le DMX). En l'état, **envoyer un seul octet est la forme juste**,
et c'est ce que fait `wolfmix.py`.

## MODE-39/40 — les deux derniers slots, et une troisième couche — 2026-08-27

Envoi de l'index brut depuis HOME, échappatoire COLOR FX après chaque essai,
l'opérateur lisant le panneau.

- **Index 39** — mode rapporté 39. **L'écran ne bouge pas** (il reste sur
  HOME) mais **les pads changent** : l'opérateur y reconnaît le sélecteur de
  positions du séquenceur Move FX, sans que l'écran correspondant s'affiche.
- **Index 40** — mode rapporté **42**, écran USB STICK et son erreur de
  chargement. **Troisième reproduction** de la redirection 40 → 42.

**Attributions**, portées au `mode-map.md` : 39 = `SEQ_POSITION_PICKER` et
40 = `FILE_BROWSER`, toutes deux **[hypothesized]** par élimination sur la
liste d'identifiants de 2.0.2 — un sélecteur qui peint des pads sans écran
d'un côté, un navigateur de fichiers qui retombe sur l'écran USB faute de
support de l'autre. Le comportement, lui, est **[device-confirmed]**. Rien
dans le binaire ne relie l'un ou l'autre nom à un numéro : les noms restent
des candidats, pas des faits.

**Ce que 39 ajoute à SCREEN-01** : le firmware déplace **trois** choses de
façon indépendante — le mode rapporté, les LED des pads, et l'écran. Le mode
39 déplace les deux premières et laisse la troisième en place. Notre readback
n'observe que la première ; c'est la limite qu'il faut garder en tête chaque
fois qu'on écrit « l'appareil est sur tel écran ».

## LINK-01 — la première requête après une inactivité expire — 2026-08-27 — **[observed]**

Constaté **cinq fois** dans la journée, toujours à l'identique : après une
pause (ou après qu'un autre processus a tenu le port), la première requête —
un `GET_SETTINGS` — expire au bout du timeout de 5 s, et la suivante passe
sans histoire. Aucune corrélation trouvée avec l'écran, le mode ou une
opération en cours. Aucun diagnostic : ce peut être le CDC côté firmware, le
pilote macOS, ou l'ouverture du tty elle-même. Consigne pratique, et rien de
plus : **relancer la commande**. Documenté ainsi dans `docs/device.md` ; pas
de nouvelle logique de retry dans l'outil tant que la cause n'est pas
comprise — un retry masquerait aussi les vraies pannes.

## RELOAD-05 — l'instrument est calibré sur ses deux bras — 2026-08-27 — **[device-confirmed]**

Réserve levée : le discriminateur « apparences distinctes sur 10
`SKIP_PRESET` » n'avait jamais été vu se déclencher. L'opérateur a ouvert au
panneau le fichier à **6 entrées**, et la même série a été rejouée.

| Copie vive | Apparences distinctes / 10 skips |
|---|---|
| 87 entrées | **10 / 10**, trois fois — mais **une seule** de ces trois séries a une copie vive établie indépendamment (celle d'avant poussée, ré-ouverte au panneau par l'opérateur). Les deux autres portent l'étiquette « 87 entrées » parce que RELOAD-02/03 l'ont *conclu* : c'est la conclusion qui sert de vérité de terrain dans son propre tableau de calibration. |
| **6 entrées** | **8 / 10**, avec répétitions |

Et le parcours se lit à nu dans les distances. Les quatre paires séparées de
**six** skips sont, de très loin, les plus proches de toute la série :

| Paire | Canaux d'écart |
|---|---|
| skip 2 vs 8 | **0** |
| skip 3 vs 9 | **0** |
| skip 4 vs 10 | 16 |
| skip 1 vs 7 | 31 |
| … toute autre paire | 60 au minimum, **médiane 79** |

**`SKIP_PRESET` parcourt donc les entrées en cycle**, et la période vaut 6 sur
la copie à 6 entrées. Réserve : dix skips n'exposent que les décalages 1 à 9,
donc les séries à 87 et 101 entrées n'excluent qu'une période ≤ 9. **L'égalité
« période = nombre d'entrées » n'est mesurée qu'à un seul nombre.** La prémisse
du discriminateur n'est plus une déduction par tiroirs, mais elle n'est
étayée que là.

**Et la réserve de l'audit se vérifie dans le même jeu** : deux des quatre
retours au même preset ne rendent **pas** la même trame (16 et 31 canaux
d'écart — la phase des effets animés). Le seuil « moins de 8 canaux »
sous-compte : le vrai cycle est 6, l'instrument affiche 8. Le falsificateur
correct n'est donc pas « ≤ 6 apparences » mais **« moins de 10, et une
périodicité dans les distances »**. Avec cette formulation, la séparation
reste franche du côté positif : 8/10 et une périodicité de 6 lisible dans les
distances. **Du côté négatif elle reste [hypothesized]** : aucune table de
distances par décalage n'a jamais été calculée sur une série à 87 entrées —
seulement une paire la plus proche (13 canaux, amplitude 139, lue comme
« différentes »), et 13 < 16, l'un des retours réels mesurés ici. Seules les
amplitudes réconcilient les deux, et la table ci-dessus ne les publie pas.
Les planchers de bruit diffèrent d'ailleurs par copie (paire non-périodique
la plus proche : 60 canaux à 6 entrées, 13 à 87), donc un seuil absolu ne
fait pas le même travail sur les deux bras.

Ce que ça consolide : **RELOAD-02, RELOAD-03 et le verdict RELOAD-04**
reposaient sur cet instrument. Son bras positif est maintenant démontré sur
le même appareil, le même jour, avec le fichier même qui servait de cible.

## RECALL-04 — un id absent ne fait rien — 2026-08-27 — **[device-confirmed]**

La copie vive est le fichier à **6 entrées, ids 0..5** : aucun trou intérieur,
donc tout id ≥ 6 est absent, et les deux lectures rivales prédisent des
choses opposées — no-op laisse la trame de la remise, plancher comme écrêtage
la remplacent par celle de l'id 5.

Précautions tirées des échecs de la matinée : historique constant, **remise
longue (8 s)** contre le rappel avalé, et jugement à l'**enveloppe** — trois
statistiques insensibles à la phase : canaux non nuls, canaux animés, somme
des maxima.

| Tir | Non nuls | Animés | Somme des max |
|---|---|---|---|
| `0 → 0` (la remise elle-même) | 122 | 0 | **18516** |
| `0 → 3` | 148 | 96 | 28652 |
| `0 → 5` | 122 | 60 | **21753** |
| `0 → 50` | 122 | 0 | **18516** |
| `0 → 200` | 122 | 0 | **18516** |
| `0 → 5` (répétition) | 122 | 60 | **21753** |
| `0 → 0` (répétition) | 122 | 0 | **18516** |

Les ids absents 50 et 200 rendent **exactement** la signature de la remise,
au chiffre près, deux fois. L'id 5 rend une signature nettement autre, elle
aussi reproduite au chiffre près.

> **Règle, corrigée :** `SET_PRESET`, charge utile = **un octet = l'id du
> preset**. Un id existant rappelle son preset. **Un id absent au-dessus du
> plus grand id existant ne fait rien** — pas de plancher, pas d'écrêtage sur
> la dernière entrée, pas de repli sur la première, pas de modulo. Les trous
> intérieurs ne sont **pas** sondés.

### Le tir qui tue les deux derniers rivaux — même jour

Un second audit a montré que le tableau ci-dessus ne suffisait pas : la
remise se faisait sur l'**id 0**, donc « un id absent se replie sur l'id 0 »
prédisait la même chose que le no-op ; et **50 mod 6 = 200 mod 6 = 2**, donc
« id modulo le nombre d'entrées » prédisait aussi leur égalité. Deux rivaux
survivants, invisibles dans mon protocole.

Le tir qui les sépare — remise sur l'**id 3**, puis l'octet **7** :

| Tir | Non nuls | Animés | Somme des max |
|---|---|---|---|
| `3 → 3` (la remise) | 148 | 90 | **26742** |
| `3 → 7` | 148 | 90 | **26742** |
| `3 → 1` | 152 | 106 | 24715 |
| `3 → 0` | 139 | 77 | 21671 |
| `3 → 7` (répétition) | 148 | 90 | **26742** |
| `3 → 3` (répétition) | 148 | 90 | **26742** |

No-op prédisait 26742, repli-sur-0 prédisait 21671, modulo (7 mod 6 = 1)
prédisait 24715. **C'est 26742, deux fois.** Les deux rivaux tombent, le
no-op tient.

**Domaine, et il est étroit** : tous les octets absents jamais tirés — 7, 50,
200 — sont **au-dessus du plus grand id existant**. Un **trou intérieur** n'a
jamais été sondé, et c'est pourtant le cas qui intéresse le générateur : la
copie à 87 entrées a des trous en 85–98 et 100–113. À mesurer en rouvrant ce
fichier-là.

Les zéros de la matrice de RECALL-03 (85 ≡ 84, 200 ≡ 114) s'expliquent enfin
sans rien inventer : les tirs étaient en ordre croissant, un no-op laisse la
trame précédente.

**Deux acquis de méthode**, chèrement payés :
- la statistique qui marche sur ce rig est l'**enveloppe agrégée** (non nuls,
  animés, somme des maxima), pas la trame unique — deux répétitions y sont
  identiques au chiffre près là où la trame variait de 32 canaux ;
- **8 s de remise** suffisent à faire disparaître le rappel avalé qui avait
  ruiné les essais depuis l'id 114. Le délai exact reste non caractérisé.

Note sur les ids hauts : l'octet **200** franchit bien 0x7f et se comporte
comme un id absent ordinaire. Un id existant supérieur à 127 (pages 7 à 10)
reste **non testé** — aucun projet du corpus n'en contient.

## SCREEN-03 — la façade cède aux touches, pas à `SET_MODE` : deux chemins distincts — 2026-08-27 — **[device-confirmed]**

Rejeu de **trois lignes** de la table de SCREEN-02 — les index 0, 5 et 16,
ceux qui ne sortaient pas — sur une **autre copie vive** (le fichier à
6 entrées, ouvert entre-temps au panneau) : ouvrir 26, envoyer le candidat,
chaque fois depuis l'écran Projects ; puis l'index 1 pour libérer la façade.
Les quatre lignes positives (1, 3, 8, 33) n'ont **pas** été rejouées.

**L'écran est resté sur Projects pour les trois.** Ces trois lignes-là ne
sont donc pas un artefact d'état : ni le projet vif, ni le modal hérité de l'écran USB de la
nuit n'y étaient pour quelque chose. La table tient.

### Ce que les LED ont montré en plus

L'opérateur regardait la façade entière, pas seulement l'écran :

| Index envoyé | LED de la touche | Écran |
|---|---|---|
| 0 (HOME) | **s'allume, puis s'éteint** | inchangé |
| 5 (PRESETS) | **s'allume, puis s'éteint** | inchangé |
| 16 (SETUP) | rien de visible — le menu principal est une icône tactile, sans touche dédiée | inchangé |
| 1 (COLOR FX) | s'allume **et reste allumée** | suit |

Les **pads** changeaient aussi pendant la séquence. On a donc maintenant
**quatre** choses qui bougent indépendamment : le mode rapporté par
`GET_SETTINGS`, les LED des touches, les pads, et l'écran. Là où un mode
« prend », tout suit ; là où il ne prend pas, la LED s'allume puis retombe —
le firmware accepte la commande, puis la façade reprend la main.

### Le fait qui compte pour la télécommande

Au **panneau**, l'opérateur rapporte que depuis l'écran Projects les touches
live — WOLF et SPEED comprises — affichent bien leur écran, **et HOME aussi**.
Par le **protocole**, ni 0 ni 5 ni 16 n'y parviennent.

> **Appuyer sur une touche et envoyer `SET_MODE` ne sont pas le même chemin.**
> La touche traverse le modal ; l'index ne le traverse que pour les modes qui
> agissent sur la lumière.

Ça referme la spéculation ouverte en séance (« si HOME sort maintenant, la
section décrit un état ») : **non**, le HOME qui sortait était la *touche*, pas
l'index. Et ça renforce RELOAD-04 par un quatrième angle : le protocole
n'atteint même pas la puissance des touches physiques, alors que ce sont ces
touches — encodeur, validation — qu'il faudrait pour recharger un projet
depuis l'écran Open.

Réserve : « la LED s'allume puis s'éteint » est une observation à l'œil, non
instrumentée ; `GET_SETTINGS` interrogé 1 s puis 5 s après l'envoi rendait, lui,
l'index envoyé dans les deux cas (SCREEN-01). Le mode rapporté et la LED ne
disent donc pas la même chose, et rien n'a encore mesuré lequel des deux suit
le moteur.

## GEN-01 — le générateur de shows, et sa prédiction publiée avant la mesure — 2026-08-27

Le générateur (`tools/wpj_generate.py`) prend une **intention** — des ambiances
avec une énergie, une couleur et des groupes — et rend un `.wpj` complet. Il ne
décrit pas le rig : il le **lit dans le donneur** (groupes, luminaires, profils,
positions nommées, palettes par groupe). Chaque ambiance devient un preset,
créé en queue de `165.f5` en clonant un preset du donneur.

### Ce sur quoi il s'appuie, et ce qu'il refuse d'inventer

| Il écrit | Champ | Statut avant GEN-01 |
|---|---|---|
| le nom du preset | `f25` | device-confirmed, ≤ 19 octets (PRESET-05) |
| l'entrée elle-même | `f5` en queue, `f1` verbatim | device-confirmed (PRESET-01/06/07) |
| le masque de contenu | `f10` | device-confirmed en **lecture** (F4-02) — jamais écrit par nous |
| les dimmers par groupe | `f17` | hypothesized ; écrits une fois (ACC-02) et **ignorés**, faute de `f10` |
| la couleur statique | `f31` | device-confirmed en **lecture** — jamais écrit par nous |
| le PATTERN de couleur | `f30` | device-confirmed en **lecture** — jamais écrit par nous |
| la position par groupe | `f28` | correlated |
| effet et vitesse d'un FX | `f7`/`f2` du sous-message | device-confirmed (ACC-04) |

| Il n'écrit pas | Pourquoi |
|---|---|
| `f16`, les masques de moteurs | son doublon `color_fx_actif`/`move_fx_actif` doit suivre, et ACC-03 a montré ce que coûte un désaccord entre les deux. Le générateur **choisit** un preset du donneur dont les moteurs conviennent et le clone. |
| le patch (105/106/110/111/115/116/125) | rien n'a été mesuré dans le sens de l'écriture ; un patch synthétisé n'aurait aucune preuve derrière lui. |
| la palette (135/140) | aucune écriture vérifiée sur appareil. La couleur demandée est donc rendue par le **pad le plus proche** de ceux que le groupe porte déjà. |

Les quatre familles du générateur — `statique`, `faisceau`, `mouvement`,
`mouvement+faisceau` — ont toutes le **moteur couleur à l'arrêt**. C'est
délibéré : c'est ce qui rend `f31` visible plutôt qu'écrasé par un Color FX.

### Le candidat

Donneur rig-c (82 presets, ids 0–81), page 6 libre, six ambiances → ids 100–105.
Fichier sha256 `c9422393ba59289b541f606474e86848870dc0789d47ae99c03ed1b92eba1572`,
41600 octets, 88 presets, `f1` laissé à 82.

Trois des six sont là pour le show ; **trois pour l'expérience** :

| id | nom | famille | groupes | dimmer | pad |
|---|---|---|---|---|---|
| 100 | Accueil | statique | B | 120 | 16 (255, 105, 8, blanc 64) |
| 101 | Rouge B | statique | B | 120 | **6** (255, 0, 0, reste 0) |
| 102 | Bleu B | statique | B | 120 | **9** (0, 0, 255, reste 0) |
| 103 | Scene | faisceau | ABC | 180 | 3 |
| 104 | Montee | mouvement | ABC | 225 | 14 |
| 105 | Peak | mouvement+faisceau | ABC | 255 | 20 |

**101 et 102 ne diffèrent que par `f31`** — vérifié champ par champ sur le
fichier produit : `couleur_statique`, `id` et `nom`, rien d'autre. C'est
l'expérience à une seule variable que la méthode réclame, en écriture cette
fois.

### Prédiction, publiée avant tout déploiement

Le groupe B est fait de dix `6x18W 6in1 RGBAW UV` à 10 canaux, adresses
1-based 100, 110, … 190. Les rôles `106.f4` donnent, par luminaire :
dimmer à l'adresse, rouge +1, vert +2, bleu +3, extra 1/2/3 +4/+5/+6,
shutter +7. Les deux `f10` valent 14 = `MOVE`, `BEAM`, `GOBO` éteints,
`COLOR` et `OTHER` **allumés**.

1. Le projet s'ouvre, la page 6 montre **six pads occupés** portant les six
   noms ci-dessus. *(p ≈ 0,9 — les trous d'id et l'ajout en queue sont
   device-confirmed ; c'est `f10`/`f30`/`f31` écrits par nous qui sont neufs.)*
2. Rappel de **101** : les canaux 101, 111, … 191 (rouge) montent, les canaux
   100, 110, … 190 (dimmer) montent, tout le reste du groupe B reste à 0.
   Les groupes A et C ne s'allument pas. *(p ≈ 0,85)*
3. Valeurs exactes : **rouge = 255 et dimmer = 120** — le pad porte la
   couleur, le preset porte l'intensité. Rival : rouge = 120 et dimmer = 255,
   si le moteur pré-multiplie. *(p ≈ 0,6 pour la première lecture)*
4. Rappel de **102** : **exactement vingt canaux bougent** par rapport à 101 —
   les dix rouges 255 → 0, les dix bleus 0 → 255. Aucun autre canal de
   l'univers ne change. *(p ≈ 0,8)*
5. Rappel de **100** : le pad 16 porte du blanc à 64 ; le canal `extra 2`
   (adresse +5) monte, ce que ni 101 ni 102 ne font. *(p ≈ 0,5 — l'ordre
   RGBAW+UV du profil n'est pas relu ici, seul `extra 2` est parié.)*

Falsificateurs, dans l'ordre du coût :

- la page 6 est vide ou le projet refuse de s'ouvrir → l'ajout en queue ne
  survit pas à un `f10`/`f30`/`f31` écrits par nous, et il faut isoler lequel ;
- les pads s'affichent mais aucun rappel ne peint → `f10` écrit ne vaut pas
  `f10` écrit par l'appareil ;
- le rappel peint mais la couleur ne suit pas le pad → `f31` n'est pas écrivable
  tel que lu, et la lecture « huit masques de 20 bits » ne vaut que dans le sens
  de la lecture ;
- la couleur suit mais les dimmers non → le bit 5 d'`f10` n'est pas `OTHER`,
  la seule attribution de F4-02 qui reposait sur un état déjà présent plutôt que
  sur une écriture.

Rappel des pièges de mesure applicables : juger à l'**enveloppe agrégée** et non
à une trame, garder un historique constant entre deux rappels (les presets sont
partiels), et rejouer 101 en fin de série — pas seulement 101 → 102 → 100.

### GEN-01 mesuré — `f31` écrit rend exactement ce qu'il lit ; les dimmers, non — **[device-confirmed]**

Déploiement du candidat sur « WMX EXP format-lab » (store + les deux vérifs +
RESTART), puis UNE ouverture manuelle au panneau, puis la série à distance :
`SET_MODE 1`, puis base → 101 → 102 → 100 → **101 rejoué en fin de série**,
8 s de repos après chaque rappel, 5 s d'enveloppe, 125 trames par capture.

Le fichier stocké est identique au candidat **sauf** le record 101 (le runner y
écrit le nom du projet expérimental) et le préfixe (UUID + compteur) : les six
presets sont arrivés octet pour octet, `f10`, `f17`, `f28`, `f30`, `f31`
compris.

**Le tir de contrôle est identique au premier 101 sur les 2048 canaux.**
L'instrument ne dérive pas ; tout ce qui suit se lit sur des différences
réelles.

| Prédiction | Résultat |
|---|---|
| 1 — six pads occupés page 6, les six noms | **tenue** — rapportée par l'opérateur |
| 2 — le rouge monte sur les dix pars, rien d'autre dans le groupe B | **tenue pour la couleur**, réfutée pour le dimmer (voir 3) ; A et C ne s'éteignent pas |
| 3 — rouge 255, dimmer 120 | **réfutée**, et sa rivale aussi : rouge 255, **dimmer 255** |
| 4 — 101 → 102 : exactement vingt canaux bougent | **tenue à la lettre** |
| 5 — le pad 16 fait monter un canal « extra » que 101/102 ne touchent pas | **tenue**, mais sur `extra 1`, pas `extra 2` comme parié |

### Ce que la paire 101/102 établit

101 → 102, deux presets qui ne diffèrent que par `f31` :

```
101 : rouge 255 vert 0 bleu 0   sur les dix pars (adresses 101, 111 … 191)
102 : rouge 0   vert 0 bleu 255 sur les dix pars (adresses 103, 113 … 193)
diff : 20 canaux, et AUCUN autre des 2048
```

Pad 6 = `(255, 0, 0)`, pad 9 = `(0, 0, 255)` dans la palette 140 du groupe B.
La sortie est la palette, canal pour canal.

> **`165.f31` est écrivable, et la lecture « huit masques de 20 bits, bit n du
> groupe g = pad n+1 » vaut dans les deux sens.** Elle n'était device-confirmed
> qu'en lecture ; elle l'est maintenant en écriture, par une expérience à une
> seule variable. `f30 = 9` (SINGLE) écrit par nous rend bien **une** couleur,
> identique sur les dix luminaires du groupe — pas d'alternance.

Le pad 16 ajoute une correspondance : `(255, 105, 8, blanc 64)` sort en
rouge 255, vert 105, bleu 8 et **`extra 1` (rôle 6, adresse +4) = 64**. Le
canal `blanc` du pad pilote donc `extra 1`. **Rétractation** : la prédiction 5
pariait `extra 2` ; le pari était faux, la structure était juste.

### Ce qui est réfuté : les dimmers du preset n'atteignent pas le DMX

Les trois presets écrivent `f17` = 120 sur le groupe B et **0** sur A et C,
avec `f10` = 14 — bit 5 (`OTHER`) **clair**, donc la bascule allumée, donc les
dimmers lus, si le modèle tient. Mesuré, dans les cinq captures :

```
dimmers groupe B (100, 110 … 190) : 255   (écrit : 120)
dimmers groupe A (8, 24 … 88)     : 220   (écrit : 0)
dimmers groupe C (206, 226)       : 255   (écrit : 0)
```

Aucun ne bouge d'une capture à l'autre. La valeur écrite n'apparaît nulle part,
et la rivale publiée (« rouge 120, dimmer 255 », un moteur qui pré-multiplie)
tombe avec elle : le rouge vaut 255.

Trois lectures survivent, aucune n'est départagée :

1. **le bit 5 de `f10` n'est pas `OTHER`.** C'est la plus faible attribution de
   F4-02 : les cinq autres bits ont été épinglés par une écriture ou par trois
   écrans, le bit 5 par un état **déjà présent** sur un preset que la sauvegarde
   n'a pas touché. Une attribution qui n'a jamais été testée par une écriture
   vient d'être testée par une écriture ;
2. **`f17` n'est pas le dimmer.** Son statut est resté `hypothesized` depuis le
   début, et il est le seul champ que le compilateur écrit sous ce statut ;
3. **la sortie du canal dimmer est l'état vif des faders de groupe du panneau**,
   pas de la donnée de projet. `220` sur A pendant que B et C sont à `255`
   ressemble beaucoup à un fader qui n'est pas tout en haut — et cette lecture
   explique aussi, sans mécanisme nouveau, l'« ACC-02 : dimmers ignorés » de
   2026-08-25, qu'on avait mis sur le dos de `f10`.

Le discriminateur le moins cher est un regard : **où sont les faders de groupe
au panneau ?** Si A est aux environs de 86 % et B et C en butée, la lecture 3
passe devant les deux autres et il faut la tester par une écriture qui varie
`f17` sans rien d'autre. Sinon, l'A/B à construire est un preset identique à
101 à `f17` près, ce qui coûte un déploiement et une ouverture manuelle.

Jusqu'à ce que ce soit tranché, **`dimmers` reste écrit par le générateur mais
son effet est inconnu** : la couleur d'une ambiance est device-confirmed, son
intensité ne l'est pas.

### Deux observations qui ne sont pas des conclusions

- Au premier rappel, la roue de couleur des six lyres du groupe A passe de 16 à
  47 et **n'en bouge plus** sur les trois pads suivants. C'est cohérent : les
  trois presets ne nomment que le groupe B, donc le masque `f31` de A est
  **vide**. Ce que fait le moteur d'un masque vide — 47 — n'est pas expliqué.
- `animatedChannels` vaut 0 dans les cinq captures : sous un preset `statique`,
  rien n'anime. La note permanente « le rig anime tout le temps » décrit les
  presets à FX, pas cet état.

## RECALL-05 — le trou intérieur, posé — 2026-08-27

Le second audit ferme RECALL-04 en écrivant son domaine : les trois octets
absents jamais tirés (7, 50, 200) sont **tous au-dessus du plus grand id
présent**, donc « un id absent ne fait rien » ne vaut que là. Le trou
**intérieur** reste non sondé — et c'est précisément ce que le générateur
fabrique : il pose sa banque sur une page libre, donc au-dessus, en laissant
un trou derrière lui.

La copie vive porte exactement ce cas : ids **0–81** puis **100–105**,
88 entrées, trou intérieur **82–99**. Octet de test : **90**.

Remise sur **101** et non sur 0 — la leçon de l'audit : une remise sur 0 rend
« repli sur 0 » indiscernable d'un no-op. La trame de 101 est connue canal par
canal (rouge pur sur les dix pars), celle de 100 aussi.

### Prédiction, publiée avant le tir

| Lecture | Trame attendue après l'envoi de 90 |
|---|---|
| **no-op** *(p ≈ 0,7)* | identique à 101 sur les 2048 canaux |
| première entrée d'id ≥ 90 *(p ≈ 0,15)* | celle de **100** — vert 105, bleu 8, `extra 1` 64 |
| dernière entrée d'id ≤ 90 | celle de **81** |
| position d'entrée écrêtée | position 90 > 87 → celle de **105** (FX, canaux animés) |
| modulo le nombre d'entrées | 90 mod 88 = 2 → celle de l'id **2** |

Les cinq rivales prédisent cinq trames distinctes, et deux d'entre elles sont
déjà sur le disque. Tir de contrôle : 101 rejoué après le test, qui doit
reproduire la trame de remise sur les 2048 canaux — sans quoi rien n'est lu.

### RECALL-05 mesuré — le trou intérieur ne fait rien non plus — **[device-confirmed]**

Remise 101 → envoi de **90** → contrôle 101, 8 s de repos, 5 s d'enveloppe :

```
contrôle 101 vs remise 101 : IDENTIQUE sur les 2048 canaux
test 90     vs remise 101 : 0 canal
test 90     vs « 100 » sur disque : 30 canaux
test 90     vs « 102 » sur disque : 20 canaux
```

**No-op.** La prédiction publiée à p ≈ 0,7 tient, et les quatre rivales
tombent, chacune sur une trame mesurée :

| Rivale | Ce qu'elle prédisait | Mesuré |
|---|---|---|
| première entrée d'id ≥ 90 → id 100 | 30 canaux d'écart avec 101 | 0 |
| position d'entrée écrêtée → id 105 | des canaux **animés** (FX) | `animatedChannels` = 0 |
| modulo 88 → id 2 | un preset `mouvement`, donc animé | `animatedChannels` = 0 |
| dernière entrée d'id ≤ 90 → id 81 | — | rappelé exprès : **72 canaux** d'écart avec 101 |

Le domaine de « un id absent ne fait rien » couvre donc maintenant les deux
cas : **au-dessus du plus grand id** (RECALL-04, octets 7, 50, 200) et
**dans un trou intérieur** (ici, 90 entre 81 et 100). C'est le cas que le
générateur fabrique à chaque fois qu'il pose sa banque sur une page libre, et
il est désormais sondé.

### Le détour par 81 rend une deuxième mesure, non prévue

Rappeler 81 puis revenir à 101 ne rend **pas** la trame de 101 : il reste
**24 canaux** d'écart, et ce sont exactement le pan et le tilt des six lyres du
groupe A, plus les deux canaux qui les suivent — ceux que le record 106 ne
nomme pas pour ce profil, très probablement les octets fins du couple 16 bits
(record 110 `f5`). Rien dans la couleur du groupe B, rien dans les dimmers.

C'est le piège n° 2 en action — *les presets sont partiels* — et c'est aussi
une mesure : le même preset, sous deux historiques différents, laisse le pan et
le tilt **là où le preset précédent les avait mis**. `165.f10` bit 1 (`MOVE`)
écrit par nous **est honoré** : un preset qui a la bascule `MOVE` éteinte ne
touche pas la couche position. **[validated]** — un différentiel à une variable
(l'historique), sur un preset que nous avons écrit.

Ça resserre la question ouverte des dimmers. Le masque de contenu n'est pas
inerte : au moins un de ses bits, écrit par nous, gate ce qu'il annonce. La
lecture « `f10` écrit ne vaut rien » tombe ; restent « le bit 5 n'est pas
`OTHER` », « `f17` n'est pas le dimmer », et « le canal dimmer sort les faders
du panneau ».

## GEN-02 — le dimmer manquant était un réglage d'appareil — 2026-08-27

L'opérateur tranche les trois lectures ouvertes par GEN-01, et aucune ne
gagne : **les potentiomètres sont tous à 100 %** — la lecture « le canal dimmer
sort les faders » tombe, et le `220` du groupe A n'est pas une position de
fader. La bonne réponse n'était dans aucune des trois :

> Le menu Settings porte une option **`store group dimmers in preset`**, et
> elle était **désactivée**. L'opérateur la garde éteinte par choix de métier :
> ça verrouille les dimmers pour une soirée entière — les pars LED plus
> discrets en plein jour — sans qu'un rappel de preset vienne les rehausser.

Il l'a activée et rapporte que **le changement de dimmer suivant le preset
fonctionne alors**. Donc `f17` *est* le dimmer, et il est gated par un réglage
qui ne vit pas dans le projet.

### Ce que ça retire au registre

**Rétractation.** « `dimmers` sont ignorés tant que le bit 5 (`OTHER`) de `f10`
n'est pas clair », attribué à ACC-02 et porté **device-confirmed** dans
SPEC.md §5.3, est **confondu** : le réglage était éteint le 2026-08-25 comme il
l'était aujourd'hui, donc ACC-02 ne pouvait pas distinguer les deux causes. Le
silence des dimmers d'ACC-02 s'explique intégralement par le réglage, sans
recourir au masque. Le bit 5 redescend à **hypothesized** — l'attribution
`OTHER` vient du manuel et d'un état déjà présent (F4-02), jamais d'une
écriture qui l'ait isolé.

Ce qui survit de GEN-01 sur `f10` : le bit 1 (`MOVE`) écrit par nous **est**
honoré, mesuré par le résidu de pan/tilt de RECALL-05. Le masque n'est pas
inerte ; c'est l'attribution du bit 5 qui n'a jamais été mesurée.

### Prédiction, publiée avant la re-mesure

Même série, mêmes presets, réglage maintenant **activé**. Les trois presets
écrivent `f17` = 120 sur B et 0 sur A et C.

1. Les dix canaux dimmer du groupe B (100, 110 … 190) passent à **120**.
   *(p ≈ 0,85 ; rival : une valeur mise à l'échelle, 120/255 d'un maximum
   propre au luminaire.)*
2. Les six dimmers du groupe A (8, 24 … 88) et les deux du groupe C (206, 226)
   passent à **0**. *(p ≈ 0,85)*
3. Le rouge du groupe B **reste 255** sous 101 : le luminaire a un canal dimmer
   dédié, le moteur n'a pas à pré-multiplier la couleur. *(p ≈ 0,85 ; rival :
   rouge = 120, et alors GEN-01 aurait vu 255 parce que le dimmer valait 255.)*
4. Les **dix-huit** canaux de dimmer sont les seuls à changer par rapport à la
   trame de 101 mesurée sous le réglage éteint, résidu de position mis à part.
   *(p ≈ 0,7)*

Et le `220` du groupe A, avec les potentiomètres en butée, reste inexpliqué :
si la prédiction 2 tient, il vient d'ailleurs — un maximum par groupe, un
`f17` de l'ancienne copie vive, ou un plafond du profil. À sonder après coup.

### GEN-02 mesuré — `f17` est un pourcentage, et il passe par `106.f5`/`f6` — **[device-confirmed]**

Même fichier, mêmes presets, même rig ; seul le réglage a bougé. Remise sur
**l'id 0** avant chaque tir — rig-c id 0 « Startup » a `f10` **absent** (les six
bascules allumées) et ses trois moteurs à l'arrêt : c'est la seule remise qui
réécrive toutes les couches. Contrôle : 0 canal d'écart, et les trois remises
identiques entre elles sur les 2048.

**Les quatre prédictions sont fausses, et le résultat vaut mieux qu'elles.**

| | Prédit | Mesuré |
|---|---|---|
| 1 | dimmer B → 120 | **255**, inchangé |
| 2 | dimmers A et C → 0 | A → **69**, C → **0** |
| 3 | rouge B reste 255 | **120** |
| 4 | 18 canaux changent | 49 |

### Le modèle, exact sur sept points

`f17` n'est pas une valeur DMX, c'est un **pourcentage**, et il traverse les
bornes de course du canal — la formule que POS-01 avait établie pour le pan et
le tilt, appliquée au rôle **dimmer** :

```
DMX = f5 + (f17 / 255) × (f6 − f5)          bornes lues dans 106.f5/f6
```

Les six lyres du groupe A portent `f5 = 69, f6 = 220` sur leur canal dimmer ;
le groupe C et les pars du groupe B portent `0`/`255`. Le fichier le disait
avant la mesure :

| Groupe | `f17` écrit | `f5`–`f6` | Attendu | Mesuré |
|---|---|---|---|---|
| A (6 lyres) | 0 | 69–220 | 69 | **69** |
| A, sous la remise | 255 | 69–220 | 220 | **220** |
| C (2 lyres) | 0 | 0–255 | 0 | **0** |
| C, sous la remise | 255 | 0–255 | 255 | **255** |

C'est aussi la fin du « `220` inexpliqué » de GEN-01 : ce n'était ni un fader
ni un plafond mystérieux, c'est `f6` de ces six luminaires.

**Et sur un luminaire qui a des canaux de couleur, l'intensité ne va PAS au
canal dimmer** : celui du groupe B reste à 255 pendant que les canaux de
couleur portent `pad × f17 / 255`, tronqué. Le pad 16 = `(255, 105, 8)` le
donne sur trois canaux à la fois :

```
255 × 120/255 = 120   mesuré 120
105 × 120/255 =  49,4 mesuré  49
  8 × 120/255 =   3,8 mesuré   3
```

Le moteur rend donc *couleur × intensité* là où le luminaire a de la couleur,
et l'intensité seule là où il n'en a pas.

### Ce que ça règle, et ce que ça laisse ouvert

`f17` = dimmer par groupe **[device-confirmed]** — il était `hypothesized`
depuis le premier jour, et il était le seul champ que le compilateur écrivait
sous ce statut. Le réglage `store group dimmers in preset` le gate
entièrement : éteint, aucune des sept valeurs ci-dessus n'apparaît.

**Conséquence pour un show généré : les dimmers ne sont pas auto-portants.**
Le fichier peut être parfait et ne rien faire, parce que la condition vit dans
les réglages de l'appareil et pas dans le projet. C'est le troisième gate de
cette famille, après `f10` et `f16`, et le premier qui ne soit pas dans le
fichier.

**Anomalie, reproductible, non expliquée.** Le preset **102** se comporte comme
si son `f17` valait 255 : bleu 255 au lieu de 120, A à 220, C à 255. Ses
voisins 100 et 101 mettent le même `f17` à l'échelle. Les trois entrées stockées
sont identiques **champ par champ sauf `f31`** — relu sur le fichier
retéléchargé — et 102 a été rappelé trois fois, dans deux séries indépendantes,
avec le même résultat.

| Preset | pad | bit dans la fenêtre du groupe B | `f17` appliqué ? |
|---|---|---|---|
| 100 | 16 | 15 | oui |
| 101 | 6 | 5 | oui |
| 102 | 9 | 8 | **non** |

Discriminateur, une seule variable : deux cues de plus, identiques à 101, l'une
sur le pad **7** (bit 6) et l'autre sur le pad **10** (bit 9). Si seul le pad 9
casse, c'est le pad ; si 10 casse aussi, c'est le rang du bit. Coût : un
déploiement et une ouverture manuelle. Jusque-là, **ne pas lire « `f17` est
appliqué » comme universel** — il l'est sur deux presets sur trois.

## GEN-03 — le discriminateur de l'anomalie 102, posé — 2026-08-27

Cinq cues de plus, **identiques à 101 sauf `f31`** — même modèle (20), même
`f17` = 120 sur B et 0 ailleurs, même `f10` = 14, même `f30`. Vérifié champ par
champ sur le candidat : la seule clé qui bouge est `couleur_statique`, plus
l'id et le nom. Candidat sha256
`7ce449110e99deb4a4d42c08625fb77d6a43c2fb3273c3ab814187a4b78b4a6c`,
43158 octets, 93 presets, `f1` toujours 82.

| id | pad | bit dans la fenêtre du groupe B | octet de `f31` | valeur | rôle |
|---|---|---|---|---|---|
| 120 | 7 | 6 | 3 | **4** | inconnue |
| 121 | 10 | 9 | 3 | **32** | inconnue |
| 122 | 6 | 5 | 3 | **2** | **contrôle** — doit se comporter comme 101 |
| 123 | 9 | 8 | 3 | **16** | **contrôle** — doit se comporter comme 102 |
| 124 | 20 | 19 | 4 | **128** | le seul cas à varint de deux octets |

Ce que les trois mesures existantes disent déjà : l'octet **2** (pad 6) et
l'octet **8** (pad 16) mettent le dimmer à l'échelle, l'octet **16** (pad 9) ne
le fait pas. La rupture est donc dans l'intervalle `]8, 16]` si elle tient à la
valeur de l'octet — et « le rang du bit dans la fenêtre de 20 » est **déjà
réfuté** par le pad 16, dont le bit 15 est plus haut que le bit 8 du pad 9 et
qui met pourtant à l'échelle.

### Prédiction, publiée avant le déploiement

| Lecture | 120 (4) | 121 (32) | 122 (2) | 123 (16) | 124 (128) | p |
|---|---|---|---|---|---|---|
| **le poids de l'octet** — rupture au bit 4 d'un octet, ou à la valeur ≥ 16 | échelle | **non** | échelle | **non** | **non** | 0,45 |
| le pad 9, et lui seul | échelle | échelle | échelle | **non** | échelle | 0,2 |
| l'anomalie ne suit pas `f31` (c'est l'entrée, la position, ou du bruit) | échelle | échelle | échelle | **échelle** | échelle | 0,2 |
| autre chose | — | — | — | — | — | 0,15 |

« Met à l'échelle » se lit sur trois familles de canaux à la fois, et chacune
suffit : les dix pars du groupe B portent `pad × 120/255`, les six lyres du
groupe A tombent à **69** (`f5` de leur canal dimmer) et les deux du groupe C
à **0**. « Non » = les valeurs de la remise : couleur pleine, A à 220, C à 255.

Le cas **124** est le seul où l'octet non nul de `f31` dépasse 127 et s'encode
donc sur **deux** octets de varint. S'il est le seul à casser, la cause n'est
pas la valeur mais l'encodage, et c'est une histoire différente — celle du
codec, pas du moteur.

Protocole : remise sur l'**id 0** avant chaque tir — la seule entrée du projet
qui réécrive toutes les couches — 8 s de repos, 5 s d'enveloppe, et 122 rejoué
en fin de série comme tir de contrôle.

### GEN-03 retiré, et l'anomalie 102 expliquée : la copie vive n'est pas le fichier — **[device-confirmed]**

Le déploiement de GEN-03 a été **refusé** par le runner : `projectChanged` était
vrai. L'opérateur a sauvegardé, et le diff de cette sauvegarde contre les octets
exactement déployés répond à la question que GEN-03 devait poser. **Le
discriminateur est retiré sans être tiré** — les cinq cues restent construites
et vérifiées, elles ne servent plus.

Un seul preset sur 88 voit ses `dimmers` ou ses `positions` changer, et c'est
**102** :

```
102  dimmers   [0, 120, 0, 0, 0, 0, 0, 0]  ->  [255, 255, 255, 255, 255, 255, 255, 255]
102  positions [1, 1, 1, 1, 1, 1, 1, 1]    ->  [4, 1, 1, 1, 1, 1, 1, 1]
```

Sa **copie vive** portait donc `f17` = 255 partout, pas le 120 du fichier. Et à
`f17` = 255 le modèle de GEN-02 prédit exactement ce qui a été mesuré, sans un
paramètre libre : groupe A → `f6` = **220**, groupe C → **255**, bleu →
**255**. L'anomalie n'a jamais eu de rapport avec `f31`.

> **La copie vive diverge du fichier, en silence.** Tout ce qu'un rappel mesure,
> il le mesure sur la copie vive. Mes trois cues étaient identiques *dans le
> fichier* — relu deux fois, champ par champ — et l'une d'elles ne l'était plus
> dans l'appareil. `f10` bit 4 (`LIVE EDIT`) est **allumé** sur les cues du
> générateur, donc un geste au panneau écrit dedans. Le seul moyen de voir la
> divergence est une sauvegarde suivie d'un téléchargement.

C'est un cinquième piège de mesure, et le plus coûteux rencontré ici : il a
produit une anomalie parfaitement reproductible — trois tirs, deux séries
indépendantes — qui pointait vers le mauvais champ. La reproductibilité ne
protège de rien quand c'est l'état, et non la mesure, qui est stable.

**Conséquence pour le générateur** : une cue destinée à une mesure doit porter
`LIVE EDIT` **éteint** (bit 4 de `f10` mis), sinon le panneau peut la réécrire
entre le déploiement et le tir.

### Ce que la sauvegarde apprend en plus, gratuitement

L'écriture de l'appareil sur un fichier que **nous** avons écrit est une source
rare. Records touchés : 115 et 165, plus le compteur de version.

**`f16` tranche 5 = le masque des groupes que le preset adresse.**
**[validated]** — refute la lecture « tranche 5 = 255 toujours »
(`correlated`, 2446 presets). Nos clones héritaient du 255 du modèle ;
l'appareil les a corrigés :

| Preset | groupes que la cue allume | tranche 5 avant | après |
|---|---|---|---|
| 100, 101 | B | 255 | **2** = B |
| 103, 104, 105 | A, B, C | 255 | **7** = A+B+C |
| 102 | *ses dimmers vifs sont à 255 partout* | 255 | **255**, inchangé |

Le contrôle est dans l'exception : 102 est le seul preset dont la tranche 5 ne
bouge pas, et c'est le seul dont la copie vive allume les huit groupes. Le
corpus était uniforme à 255 parce que **rien n'y avait jamais varié** — le
piège de l'uniformité, pour la troisième fois dans ce registre, et cette fois
c'est le graveur de l'appareil qui l'a cassé.

**Le graveur de l'appareil écrit `165.f1` = le nombre d'entrées** : 82 → **88**,
et il y avait bien 88 entrées des deux côtés. Ça ne contredit pas PRESET-01 —
`f1` ne *gate* rien à la lecture — mais ça dit ce que l'appareil, lui, y met.

**Il émet aussi les quatre tableaux de l'écran STATIC GOBO sur les 88 presets**,
à leurs valeurs par défaut, là où le fichier d'origine les omettait :
`gobo_focus` = 50, `gobo_zoom` = 100, `gobo_iris` = 100, `gobo_prism` = 0.
Un champ absent n'est pas un champ à zéro, et l'appareil le rend explicite.

**Record 115, entrées de luminaire** : `f6` = 94 et `f7` = 187 — identiques sur
les vingt entrées du fichier d'origine — disparaissent, remplacés par `f9` =
**l'index séquentiel du luminaire** (0 omis, puis 1…19). **[observed]** : une
migration de schéma par le graveur du firmware, sur laquelle rien n'est conclu.

## FW-01 — `f10` bit 5 s'appelait `DIMMER` jusqu'en 2.0.15 — 2026-08-27 — **[observed]**

### La source, et son rang

Le contrôleur a été mis volontairement en mode bootloader ce jour-là. Le
bootloader lui-même n'a rien donné : il énumère en `WOLFMIX_BL`
(VID `0x6244` / PID `0x0623`, CDC-ACM, ni DFU ni mass storage), il reste
**muet** — 4 s d'écoute passive, zéro octet, aucune écriture émise — et il ne
sait que flasher.

Ce qu'il a fait remonter, en revanche, c'est le cache de WTOOLS :
`~/Library/Application Support/com.nicolaudiegroup.wtools/wm-fw-bundle-2.0.18/`.

| Fichier | Lisible ? |
|---|---|
| `wolfmixFirmware.bin` (418 141 o) | **non — chiffré**. Entropie 7.99 sur les 16/16 blocs ; en-tête 8 o : taille en clair 418 068, puis `33`. Pas de rétro-ingénierie statique du firmware. |
| `wolfmixFlash.bin`, `wolfmixFlash-reset.bin` | en clair, mais ce sont des données graphiques (LUT, dégradés). Rien du format projet. |
| `changelog.json` (sha256 `66dc76d5…454714`) | **oui** — le vendeur décrit son propre firmware, version par version, de 2.0.5 à 2.0.18. `fwChannel: "debug"`, `modelId: "W1"`, `fwDate` 2026-07-07. |

**Statut.** Source **externe et statique**, du même rang que le manuel : elle
corrobore et elle date, elle ne confirme rien sur l'appareil, et elle ne peut
relever aucune lecture au-dessus de `observed`. Les binaires ne sont pas
commités (règle du dépôt) ; seul le chemin et l'empreinte sont cités.

### Deux lignes, deux versions

| Version | Ligne du changelog |
|---|---|
| **2.0.5** | « Add the possibility to exclude Gobo, Live Edit, and Dimmer values from a Preset. » |
| **2.0.15** | « Change DIMMER preset part to OTHER. » |

Trois bascules naissent **ensemble** en 2.0.5 — `GOBO`, `LIVE EDIT`, `DIMMER` —
soit exactement les bits 3, 4 et 5 de `f10`, dans l'ordre de lecture d'écran
établi par F4-02. Les bits 0–2 (`COLOR`, `MOVE`, `BEAM`) leur préexistent. **La
numérotation des bits est chronologique**, et l'ordre de l'écran la suit.

Et la sixième bascule s'appelait `DIMMER` avant de s'appeler `OTHER`.

### Ce que ça règle

Des trois lectures rivales laissées debout par GEN-01 — « le bit 5 n'est pas
`OTHER` », « `f17` n'est pas le dimmer », « le canal dimmer sort des faders du
panneau » — la première perd son dernier appui : le bit 5 est bien la bascule du
dimmer, sous son nom d'origine. Le manuel (« `OTHER` includes the group dimmer
values ») et le changelog désignent le même bit par deux chemins indépendants.

### Ce que ça ouvre, et c'est le piège

`OTHER` n'est **pas** un synonyme de `DIMMER` : c'est un **élargissement**, daté
2.0.15. Le firmware de mesure est 2.0.18, postérieur. Donc la phrase du manuel
décrit peut-être l'état d'avant le renommage, et **ce que le bit 5 gate en plus
du dimmer n'est pas connu**. Un writer qui pose le bit 5 pour « ne pas rappeler
les dimmers » éteint aussi tout ce qu'`OTHER` a absorbé depuis.

Deuxième ligne dimmer dans la **même** version 2.0.15 : « Revert "Store group
dimmers in Preset" operation to how it was in firmware 1.x. » Le réglage
d'appareil qui gate ce qu'un preset stocke a donc changé de comportement deux
fois. Conséquence de compatibilité honnête : **toute mesure de dimmer antérieure
à 2.0.15 est hors sujet pour ce rig.**

### Discriminateur, pas cher — **[planned]**

Sur une cue à nous, dont les dimmers passent déjà par le chemin établi en
GEN-02 : déployer la même cue deux fois, `f10 = 0` puis `f10 = 32` (bit 5 seul),
rappeler chacune et comparer les enveloppes DMX agrégées. Ce qui s'éteint **en
plus** des dimmers, c'est le contenu qu'`OTHER` a gagné en 2.0.15. Si rien
d'autre ne bouge, `OTHER` = `DIMMER` et le renommage est cosmétique.

> **Tiré le 2026-08-27 par FW-03**, avec une correction : la paire est devenue
> `f10 = 30` / `f10 = 62` et non `0` / `32`. `f10 = 0` laisse `LIVE EDIT`
> allumé, et GEN-03 a montré ce que ça coûte — la copie vive peut diverger du
> fichier en silence. Résultat : **exactement 18 canaux**, tous des dimmers ou
> leur report sur la couleur. Rien d'autre de ce qu'une cue statique porte
> n'est gaté par le bit 5, et le renommage de 2.0.15 est cosmétique **sur ce
> périmètre**.

## FW-02 — `f32`–`f35` sont datés : firmware 2.0.5, et ça date le schéma 10 — 2026-08-27 — **[observed]**

Même source que FW-01.

| Version | Ligne du changelog |
|---|---|
| **2.0.5** | « Add the possibility to set a Prism, Focus, Zoom and Iris value on each group. These values can be stored in a preset like Gobo Rotate. » |

Trois corroborations en une phrase, sur une lecture déjà **device-confirmed**
par GOBO-02 :

1. **« on each group »** — les quatre champs sont des tableaux **par groupe**,
   pas des scalaires. C'est la forme mesurée (groupe A seul non nul, zéro sur
   les sept autres).
2. **« like Gobo Rotate »** — `ROTATE` **préexiste** aux quatre autres. D'où
   `f14` pour rotate et `f32`–`f35` pour les nouveaux : un numéro de champ
   protobuf est attribué à la conception, donc un ajout part de la queue. **La
   numérotation raconte la chronologie**, ici comme pour les bits de `f10` en
   FW-01.
3. **Quatre features, quatre champs** — Prism, Focus, Zoom, Iris. Le registre
   les avait classés « a schema-10 addition, zeroed by the upgrade » sans
   jamais les lire ; ce sont les ajouts du firmware **2.0.5**.

**Donc schéma 10 ↔ firmware 2.0.5.** C'est la première date accrochée à un
numéro de schéma de ce format, et elle donne une borne : un projet au schéma 10
a été écrit par une 2.0.5 ou plus récente.

### Ce que ça ne fait pas

`f3`, `f7`, `f23` et `f27` **restent non attribués**. Le changelog ne les nomme
pas. L'hypothèse « les cinq tableaux à zéro sont les cinq features gobo » a été
rétractée par GOBO-02 — seul `f14` en était — et cette entrée ne la ressuscite
pas. Le compte de cardinalité qui l'avait produite reste une erreur de méthode,
pas une piste à reprendre.

### Deux lignes voisines, pour plus tard

- 2.0.5 : « Position focus values are now applied as a focus offset, relative to
  the focus value set on the Gobo screen. » Le `FOCUS OFFSET` décodé en POS-04
  (record 151) est donc **relatif à `f32`**, pas absolu. Un writer qui pose les
  deux doit les composer. **[hypothesized]** — jamais mesuré ici.
- 2.0.9 : « Add Iris min and max selection from fixture builder ». Les bornes
  d'iris vivent dans le **profil**, pas dans le preset. **[hypothesized]** :
  `f35` serait alors un pourcentage dans ces bornes, exactement la forme que
  GEN-02 a mesurée pour `f17` via `106.f5`/`f6`.

## FW-03 — le périmètre du bit 5 (`OTHER`), posé — 2026-08-27

Tire le discriminateur laissé `[planned]` par FW-01 : le bit 5 de `165.f10`
s'appelait `DIMMER` jusqu'en 2.0.15 et `OTHER` depuis, sur un firmware de
mesure (2.0.18) postérieur au renommage. Ce qu'il gate **en plus** du dimmer
n'est pas connu, et un writer qui pose ce bit pour « ne pas rappeler les
dimmers » éteint aussi tout ce qu'`OTHER` a absorbé.

### Le protocole change sur un point, et GEN-03 en est la raison

FW-01 esquissait la paire `f10 = 0` puis `f10 = 32`. **`f10 = 0` laisse
`LIVE EDIT` allumé** (bit 4 clair = bascule allumée), or GEN-03 vient de
montrer qu'une cue à `LIVE EDIT` allumé peut être réécrite dans la copie vive
sans que le fichier bouge — et c'est exactement ce qui a produit une anomalie
reproductible pointant vers le mauvais champ. La paire devient donc
**`f10 = 30` puis `f10 = 62`** : mêmes six bascules qu'avant, plus le verrou
de mesure sur les deux.

| | bit 0 `COLOR` | bit 1 `MOVE` | bit 2 `BEAM` | bit 3 `GOBO` | bit 4 `LIVE EDIT` | bit 5 `OTHER` |
|---|---|---|---|---|---|---|
| `f10 = 30` | allumé | éteint | éteint | éteint | **éteint (verrou)** | **allumé** |
| `f10 = 62` | allumé | éteint | éteint | éteint | **éteint (verrou)** | **éteint** |

La seule variable reste le bit 5.

### Le candidat

Donneur rig-c (82 presets, ids 0–81). Quatre cues ajoutées en queue —
deux pour FW-03, deux pour RECALL-06 ci-dessous. Fichier sha256
`582876a155efa30ed4d7f6c764eaf85b3b20610cc16112e2264faaeb26f7dac9`,
41000 octets, 86 presets, `f1` laissé à 82.

| id | nom | pad (groupe B) | `f17` | `f10` | rôle |
|---|---|---|---|---|---|
| 100 | `FW OTHER ON` | 6 — (255, 0, 0) | 120 sur B, 0 ailleurs | **30** | `OTHER` allumé |
| 101 | `FW OTHER OFF` | 6 — (255, 0, 0) | 120 sur B, 0 ailleurs | **62** | `OTHER` éteint |

**100 et 101 ne diffèrent que par `masque_contenu`** — relu champ par champ sur
le fichier produit : `id`, `nom`, `masque_contenu`, rien d'autre. `f17`, `f30`,
`f31`, `f16`, les deux FX et les positions sont identiques.

### Prédiction, publiée avant le déploiement

Remise sur l'**id 0** avant chaque tir : `f10` absent (les six bascules
allumées), `f17` = 255 partout, les trois moteurs à l'arrêt — la seule entrée
du projet qui réécrive toutes les couches (GEN-02). Sous cette remise, le
modèle de GEN-02 donne : groupe A (six lyres, `106.f5`/`f6` = 69/220) →
dimmer **220** ; groupe C → **255** ; groupe B → son pad de remise (pad 1,
`(255, 127, 0)`) à pleine échelle.

| | Sous 100 (`OTHER` allumé) | Sous 101 (`OTHER` éteint) |
|---|---|---|
| rouge des dix pars B (101, 111 … 191) | `255 × 120/255` = **120** | **255** — le dimmer n'est pas lu, l'échelle reste celle de la remise |
| vert des dix pars B (102, 112 … 192) | **0** | **0** |
| dimmer des six lyres A (8, 24 … 88) | `f5` = **69** | **220**, inchangé depuis la remise |
| dimmer des deux lyres C (206, 226) | **0** | **255**, inchangé depuis la remise |

1. **Exactement 18 canaux** diffèrent entre le tir 100 et le tir 101 : les dix
   rouges du groupe B, les six dimmers du groupe A, les deux du groupe C. Aucun
   autre des 2048. → **`OTHER` = `DIMMER`, le renommage de 2.0.15 est
   cosmétique pour ce que cette cue porte.** *(p ≈ 0,5)*
2. **Plus de 18 canaux** diffèrent. Les canaux en trop nomment ce
   qu'`OTHER` a absorbé, et c'est le résultat qu'on vient chercher.
   *(p ≈ 0,35)*
3. **Zéro canal** ne diffère : le bit 5 n'est pas la bascule du dimmer, ce qui
   contredirait à la fois le manuel et le changelog par deux chemins
   indépendants. *(p ≈ 0,1)*
4. Autre chose — moins de 18, ou 18 mais pas ceux-là. *(p ≈ 0,05)*

**Ce que ce tir ne peut pas voir, et il faut le dire avant.** La cue ne porte
**ni `f32`–`f35`** (Prism, Focus, Zoom, Iris — le générateur ne les écrit pas,
et le modèle cloné ne les porte pas non plus) **ni gobo actif** (bit 3 éteint).
Si `OTHER` a absorbé ces contenus-là, l'expérience est **aveugle** : un
résultat à 18 canaux dit « rien d'autre **de ce que cette cue porte** », pas
« `OTHER` = `DIMMER` » en général. La lecture 1 ne monterait donc qu'à
`validated` sur ce périmètre, pas au-delà.

Falsificateurs, dans l'ordre du coût :

- le projet refuse de s'ouvrir ou la page 6 est vide → l'écriture de `f10` = 62
  par nous casse quelque chose que `f10` = 30 ne casse pas ;
- les deux tirs sont identiques → lecture 3 ;
- le tir de contrôle ne reproduit pas le premier 100 → l'instrument a dérivé et
  rien n'est lu (le piège n° 3).

Protocole : remise 0 → 100 → remise 0 → 101 → remise 0 → **100 rejoué en fin de
série**, 8 s de repos et 5 s d'enveloppe par tir, jugement à l'enveloppe agrégée
sur les 2048 canaux et jamais à une trame.

**Le réglage `store group dimmers in preset` doit être ACTIF** pour ce tir :
c'est lui qui ouvre le chemin mesuré en GEN-02, et sans lui les deux tirs
seraient identiques pour une raison qui n'a rien à voir avec le bit 5.

## RECALL-06 — les ids ≥ 128, posé — 2026-08-27

Domaine prouvé du rappel par USB : **ids 0–127**. `SET_PRESET` porte l'id sur
un seul octet (RECALL-03), le deuxième n'est pas lu (RAW-02), et tous les tirs
publiés — RECALL-03, RECALL-04, RECALL-05 — tiennent sous 128. Le panneau, lui,
va jusqu'à **199** (page 10, slot 20). Rien ne dit ce que fait le firmware d'un
octet dont le bit 7 est mis.

### Le candidat, et pourquoi deux octets et non un

Les mêmes quatre cues que FW-03 ; ces deux-ci sont sur la page 8.

| id | nom | pad (groupe B) | couleur du pad | `f17` | `f10` |
|---|---|---|---|---|---|
| 140 | `R06 CIBLE 140` | 10 | (255, 0, 255) | 120 sur B | 30 |
| 141 | `R06 CIBLE 141` | 7 | (0, 255, 0) | 120 sur B | 30 |

140 et 141 ne diffèrent de 100 que par `couleur_statique` (et l'id, et le nom).
Trous d'id : 82–99, 102–139 — le cas du trou intérieur, déjà mesuré comme
no-op en RECALL-05, reste donc en place et n'est pas une variable ici.

**Deux octets sont tirés, pas un**, parce qu'un seul ne sépare pas les rivales :

- **octet 140** — un preset existe à cet id. `140 & 0x7F` = **12**, un preset du
  donneur dont la trame est inconnue : elle est donc **capturée avant le tir**,
  ce qui la rend prédictive au même titre que les autres.
- **octet 228** — aucun preset à cet id (le panneau s'arrête à 199).
  `228 & 0x7F` = **100**, qui est la cue `FW OTHER ON` de FW-03, mesurée dans la
  même séance. Une troncature à 7 bits est donc lisible sur une trame que nous
  aurons écrite nous-mêmes.

### Prédiction, publiée avant le tir

Remise sur l'id 0 avant chaque tir, comme en FW-03.

| Lecture | octet 140 | octet 228 | p |
|---|---|---|---|
| **rappel exact au-delà de 127** | la trame de **140** : magenta sur les dix pars B — rouge `255 × 120/255` = **120** ET bleu **120**, vert 0 | **no-op** (aucun preset d'id 228) : identique à la remise | **0,6** |
| **troncature à 7 bits** | la trame de l'**id 12**, capturée avant | la trame de **100** : rouge 120, vert 0, bleu 0 | 0,1 |
| **no-op au-dessus de 127** | identique à la remise sur les 2048 canaux | identique à la remise | 0,25 |
| autre chose | — | — | 0,05 |

Les trois lectures prédisent **six trames**, et cinq d'entre elles seront
mesurées dans la même séance — la remise, l'id 12, la cue 100, la cue 140 et la
cue 141. C'est la forme que RECALL-05 a validée : autant de trames distinctes
que de rivales.

`141` est tiré aussi, pour la même raison qu'un contrôle : un id ≥ 128 qui
marche une fois peut être un accident de table ; deux, sur deux pads
différents, non. `141 & 0x7F` = 13, encore un preset du donneur.

**Une mesure gratuite au passage.** Les pads 10 et 7 portent dans `f31` les
valeurs d'octet **32** et **4** — exactement deux des cinq cas que GEN-03 avait
construits avant d'être retiré. Si 140 et 141 mettent tous deux `f17` à
l'échelle, la lecture « le poids de l'octet de `f31` casse la mise à l'échelle
au-delà de 16 », déjà expliquée par la copie vive, est **réfutée une seconde
fois et par un autre chemin**. Si l'un des deux ne met pas à l'échelle, GEN-03
revient de sa retraite.

Protocole, à la suite de celui de FW-03, même cadence : remise 0 → **12** →
remise 0 → **140** → remise 0 → **141** → remise 0 → **228** → remise 0 →
**100 rejoué**, tir de contrôle final qui doit reproduire le 100 de FW-03 sur
les 2048 canaux.

## PAL-01 — écrire une couleur de palette (record 140), posé — 2026-08-27

Le générateur n'écrit **aucune** palette : il rend la couleur demandée par le
pad **le plus proche** de ceux que le groupe porte déjà (GEN-01). C'est la
dernière approximation du chemin intention → DMX, et la seule qui reste après
que `f31`, `f30` et `f17` sont passés device-confirmed. Décision de périmètre
prise le 2026-08-27 : on prouve l'écriture plutôt que de documenter la limite.

### Le round-trip, préalable et déjà acquis — **[validated]**

Le record 140 se décode et se ré-encode **octet pour octet** : 360 occurrences
sur 51 fichiers du corpus, 360 round-trips identiques. Le premier des trois
verrous de la règle « read before write » est donc levé sans matériel. Restent
le différentiel à une variable et l'acceptation par l'appareil, que ce tir vise.

### Le candidat, et pourquoi il ne contient qu'un seul octet de nouveau

Le candidat de FW-03, **avec une seule composante changée** :

```
record 140, occurrence 1 (groupe B), pad 6 : {rouge: 255}  ->  {rouge: 100}
```

Vérifié par relecture : un seul des 26 records diffère, un seul des 20 pads de
ce record, une seule des composantes de ce pad. Les palettes des sept autres
groupes sont identiques octet pour octet. Fichier sha256
`076911d109c6f8f02dd3e10a2c647244b202b0fdfba6b6ac5787c2407073ccb8`,
40999 octets — un de moins que son parent, parce que 100 tient sur un octet de
varint là où 255 en prend deux.

Le pad 6 du groupe B est choisi parce que **les cues 100 et 101 de FW-03
l'utilisent déjà** : leur trame est mesurée dans la séance A, avant ce tir.
L'état « avant » n'est donc pas à construire, il est capturé.

### Prédiction, publiée avant le déploiement

Dépend de la séance A, qui doit avoir rendu ses trames. Sous la même remise
(id 0) et la même cadence :

| Lecture | rappel de 100 (`OTHER` allumé) | rappel de 101 (`OTHER` éteint) | p |
|---|---|---|---|
| **la palette écrite est lue** | rouge des dix pars B = `100 × 120/255` = **47** (séance A : 120) | rouge = **100** (séance A : 255) | **0,6** |
| la palette n'est pas relue — moteur, ou palette vive qui prime comme la copie vive de GEN-03 | **120**, inchangé | **255**, inchangé | 0,2 |
| écriture acceptée mais normalisée par le graveur | une troisième valeur, ni 47 ni 120 | — | 0,1 |
| le projet refuse de s'ouvrir | — | — | 0,1 |

Deux contrôles, et ils ne coûtent rien :

- **rappel de 140** (pad 10, palette non touchée) : doit reproduire le tir 05 de
  la séance A sur les 2048 canaux. Si cette trame bouge, c'est la palette
  entière qui a été réécrite, pas le pad 6 — et la lecture change ;
- **un regard au panneau** sur le pad 6 de la palette du groupe B : rouge sombre
  au lieu de rouge saturé. Deuxième chemin d'évidence, indépendant du DMX.

Falsificateur qui compte plus que les autres : si le rouge sort à 47 **et** que
d'autres canaux bougent, l'écriture a débordé et il faut isoler quoi.

### Une observation en passant, qui n'est pas une conclusion

La clé `page` de `140.f2` porte les valeurs 0…7 sur les huit occurrences, et
l'occurrence *n* est la palette du groupe *n* — GEN-01 l'a prouvé par le rendu
(pad 16 du groupe B = `(255, 105, 8)`, mesuré, et non le `(255, 127, 80)` du
même pad du groupe A). **`f2` est donc l'index de GROUPE, pas une page**, et le
nom de la clé du codec induit en erreur. **[correlated]**, et device-confirmed
par le rendu de GEN-01. Rien n'est renommé ici : un renommage touche le codec,
la spec et les docs, et ça n'est pas le sujet de ce tir.

### FW-03 mesuré — `OTHER` ne gate rien de plus que le dimmer, ici — **[validated]**

Déploiement du candidat sur « WMX EXP format-lab » (store + les deux vérifs +
RESTART), UNE ouverture manuelle au panneau, réglage `store group dimmers in
preset` **actif**, puis la série à distance : `SET_MODE 1`, remise sur l'id 0
avant chaque tir, 8 s de repos, 5 s d'enveloppe, 125 trames par capture.

**Les deux tirs de contrôle sont identiques au premier 100 sur les 2048
canaux** — celui d'après la paire, et celui de fin de série huit tirs plus
loin. L'instrument n'a pas dérivé de toute la séance.

**Exactement 18 canaux séparent `f10 = 30` de `f10 = 62`, et ce sont ceux
annoncés.** La prédiction n° 1, publiée à p ≈ 0,5 :

```
 8, 24, 40, 56, 72, 88   dimmer des six lyres A    69 -> 220     (f5 -> f6)
101,111 … 191            rouge des dix pars B     120 -> 255
206, 226                 dimmer des deux lyres C    0 -> 255
                                                   ---
                         et AUCUN autre des 2048    18
```

Les valeurs sont celles du modèle de GEN-02, sans un paramètre libre : sous
`OTHER` allumé, `f17` = 120 rend `69 + (120/255)(220−69)` = 69 pour un groupe
dont `f17` vaut 0, `255 × 120/255` = 120 pour le rouge du pad 6, et 0 pour le
groupe C. Sous `OTHER` éteint, les trois couches gardent les valeurs de la
remise — 220, 255 et 255.

| Rivale | Ce qu'elle prédisait | Mesuré |
|---|---|---|
| 2 — plus de 18 canaux, `OTHER` a absorbé du contenu | des canaux en trop, qui le nomment | 18, pas un de plus |
| 3 — le bit 5 n'est pas la bascule du dimmer | 0 canal | 18 |
| 4 — autre chose | — | — |

> **Le bit 5 de `165.f10` gate les dimmers de groupe, et rien d'autre de ce
> qu'une cue statique porte.** Il remonte de `hypothesized` — où GEN-02 l'avait
> fait redescendre — à **`validated`** : c'est un différentiel à une seule
> variable, sur une paire que nous avons écrite, mesuré sur l'appareil. Le
> manuel, le changelog 2.0.15 et cette écriture désignent maintenant le même
> bit par trois chemins indépendants.

**Ce que ça ne dit pas, et c'était annoncé avant le tir.** La cue ne porte ni
`f32`–`f35` ni gobo actif. Si le renommage `DIMMER` → `OTHER` de 2.0.15 a
absorbé ces contenus-là, cette expérience est aveugle dessus. Le statut est
donc `validated` **sur le périmètre d'une cue statique**, et non
`device-confirmed` sur `OTHER` en général — la nuance est la raison pour
laquelle la limite avait été publiée d'avance.

### RECALL-06 mesuré — le rappel est exact au-delà de 127 — **[device-confirmed]**

Même séance, même série. Deux octets tirés, comme prévu.

```
octet 228 vs remise            : 0 canal          -> no-op strict
octet 140 vs cue 100           : 10 canaux        -> les dix bleus de B, 0 -> 120
octet 140 vs remise            : 64 canaux
octet 140 vs id 12 (capturé)   : 91 canaux
octet 141 vs cue 100           : 20 canaux        -> dix rouges et dix verts
```

Valeurs absolues sur le premier par du groupe B, adresses 100–103 :

| Tir | dimmer | rouge | vert | bleu | pad attendu |
|---|---|---|---|---|---|
| remise (id 0) | 255 | 255 | 127 | 0 | pad 1 `(255, 127, 0)` |
| **140** | 255 | **120** | 0 | **120** | pad 10 `(255, 0, 255)` × 120/255 |
| **141** | 255 | 0 | **120** | 0 | pad 7 `(0, 255, 0)` × 120/255 |
| 228 | 255 | 255 | 127 | 0 | identique à la remise |

**La lecture publiée à p = 0,6 tient, et les deux rivales tombent :**

| Rivale | Ce qu'elle prédisait pour 140 | Ce qu'elle prédisait pour 228 | Mesuré |
|---|---|---|---|
| troncature à 7 bits | la trame de l'id **12** | la trame de la cue **100** | 91 canaux d'écart avec 12 ; 0 canal d'écart avec la remise |
| no-op au-dessus de 127 | identique à la remise | identique à la remise | 64 canaux d'écart avec la remise |

> **Le domaine du rappel par USB est le domaine du panneau : les ids 0–199.**
> `SET_PRESET` lit son octet tel quel, sans masque et sans borne à 127. Un id
> présent est rappelé exactement, quel que soit son bit 7 ; un id absent reste
> un no-op — troisième domaine après RECALL-04 (au-dessus du plus grand id) et
> RECALL-05 (trou intérieur), et il couvre ici les ids ≥ 128.

Deux réserves honnêtes. L'octet **228** dépasse le maximum du panneau (199) :
son no-op peut venir de « aucun preset à cet id » comme d'une borne à 199, et
cette série ne les sépare pas — mais ni l'un ni l'autre n'est une troncature,
et c'est ce qui était en jeu. Et les ids testés, 140 et 141, sont dans la
plage du panneau ; 200–255 n'est pas sondé.

**Le rappel d'un id ≥ 128 est un rappel ordinaire sur toutes les couches.**
Hors groupe B, les tirs 100, 140 et 141 sont identiques canal pour canal : le
bit 7 de l'octet ne change rien à ce que le moteur fait des positions, des
dimmers ou des groupes que la cue n'adresse pas.

### La mesure gratuite annoncée : GEN-03 réfuté une seconde fois

Les cues 140 et 141 portent dans `f31` les valeurs d'octet **32** et **4** —
deux des cinq cas que GEN-03 avait construits. **Toutes deux mettent `f17` à
l'échelle** : 120 et non 255, sur les six familles de canaux. La lecture « le
poids de l'octet de `f31` casse la mise à l'échelle au-delà de 16 » est donc
réfutée par un second chemin, indépendant de la sauvegarde qui l'avait déjà
expliquée. L'anomalie 102 était bien la copie vive, et rien d'autre.

### PAL-01 mesuré — la palette écrite sort au canal, exactement — **[device-confirmed]**

Déploiement du candidat (`Hooray!`, 40999 octets stockés), UNE ouverture
manuelle, puis la même remise et la même cadence que la séance A. Le tir de
contrôle — la cue 100 rejouée en fin de série — est à **0 canal** d'écart avec
le premier.

**La prédiction n° 1, publiée à p = 0,6, tient sur les deux tirs et sur les deux
contrôles :**

| Tir | Séance A (pad 6 = `{rouge: 255}`) | Séance B (pad 6 = `{rouge: 100}`) | Attendu | Canaux qui bougent |
|---|---|---|---|---|
| cue 100, `OTHER` allumé | rouge **120** | rouge **47** | `100 × 120/255` = 47,06 → **47** | **10**, les dix rouges du groupe B |
| cue 101, `OTHER` éteint | rouge **255** | rouge **100** | le pad à pleine échelle → **100** | **10** |
| cue 140, pad 10 **intact** | — | — | identique à la séance A | **0 sur les 2048** |

Le tir 03 est le contrôle qui compte : la cue 140 tire sur le pad 10 de la même
palette, et sa trame est identique à celle de la séance A **canal pour canal
sur les 2048**. L'écriture n'a donc pas débordé — un pad a bougé, un seul, et
les dix-neuf autres du même record sont inchangés à la sortie DMX.

**Et un second chemin, indépendant du DMX** : l'opérateur rapporte que le pad 6
de la palette du groupe B est passé de rouge saturé à rouge sombre **à
l'écran**. Le panneau relit donc ce que nous avons écrit, avant tout rappel.

| Rivale | Ce qu'elle prédisait | Mesuré |
|---|---|---|
| la palette n'est pas relue (moteur, ou palette vive qui prime) | rouge inchangé à 120 / 255 | 47 / 100 |
| écriture normalisée par le graveur | une troisième valeur | 47, exactement la formule |
| le projet refuse de s'ouvrir | — | il s'ouvre |

> **`140.f5` est écrivable, et la valeur écrite est la valeur rendue.** Les trois
> verrous de « read before write » sont levés dans l'ordre : round-trip
> octet-identique (360 occurrences sur 51 fichiers), différentiel à une seule
> variable (une composante d'un pad), et acceptation par l'appareil (stocké,
> relu à l'écran, rendu au canal). **[device-confirmed]**

Ce que ça change pour le générateur : la couleur d'une ambiance n'a plus à être
approximée au pad le plus proche. Ce que ça ne change pas : chaque couleur
distincte consomme **un des vingt pads** du groupe, et ces pads sont ceux que
l'opérateur a sous les doigts. Écrire une palette est un arbitrage de métier,
pas une conséquence automatique de la mesure — le générateur ne l'a donc pas
été câblé dans la foulée.

Portée honnête : un pad, un groupe, une composante (`rouge`), sur un profil qui
a des canaux de couleur. Les composantes `ambre`, `lime`, `blanc` et `uv` du
même sous-message n'ont pas été variées, et rien n'est mesuré sur un profil qui
n'a pas de canal de couleur.

## FX2-01 — « Double Trouble » : les deux pages d'un effet, et le masque qui manque — 2026-08-27

Question posée par l'opérateur : le firmware 2.0 double les moteurs d'effet —
deux Color FX, deux Move FX, deux Beam FX — et le manuel dit qu'ils peuvent
tourner **en même temps sur des groupes différents**. Est-ce que le registre en
tient compte ?

**Réponse courte : la structure oui, l'affectation aux groupes non.** Et le
« non » est précisément le piège de l'uniformité, pour la quatrième fois.

### Ce qui est établi

Le record 165 porte **deux sous-messages par type d'effet**, décodés et
round-trippés depuis le premier jour :

| Type | slot 1 | slot 2 |
|---|---|---|
| Beam | `f1` → `beam_fx1` | `f2` → `beam_fx2` |
| Color | `f5` → `color_fx1` | `f6` → `color_fx2` |
| Move | `f21` → `move_fx1` | `f22` → `move_fx2` |

Et le second slot n'est pas un doublon décoratif : sur 3697 presets du corpus,
il porte des valeurs **différentes** du premier sur 742 presets en couleur,
1439 en mouvement et 1240 en faisceau.

Corrélation mesurée, sans matériel : **quand la tranche `f16` d'un type est non
nulle, le slot 2 diffère toujours du slot 1** — 738/738 en couleur, 1439/1439
en mouvement, 1186/1186 en faisceau, zéro exception. L'inverse est faux : 54
presets en faisceau et 4 en couleur portent deux slots différents avec la
tranche à zéro. **[correlated 45/45]** — un moteur allumé stocke bien deux
configurations, et un moteur éteint peut en garder deux vestigiales.

### Ce qui n'est PAS établi, et pourquoi le corpus ne peut pas le dire

`f16` porte douze tranches de 9 bits. Les tranches 0, 1 et 2 sont épinglées :
Color, Move, Beam — **le moteur numéro un de chaque type**. Rien n'épingle le
masque de groupes du **deuxième** moteur.

Distribution complète sur les 3697 presets, mesurée :

```
tranche  0 : 0×2959  255×738          Color FX      (= color_fx_actif)
tranche  1 : 0×2258  255×1420  1×19   Move FX       (= move_fx_actif)
tranche  2 : 0×2511  255×1186         Beam FX
tranche  3 : 0×3697                   ← ZÉRO PARTOUT
tranche  4 : 0×3697                   ← ZÉRO PARTOUT
tranche  5 : 255×3697                 groupes adressés (GEN-03)
tranches 6–10 : les cinq touches flash
tranche 11 : 5×1950  2×1665  7×82     non attribuée
```

**Les tranches 3 et 4 sont nulles sur les 3697 presets du corpus.** C'est
exactement la forme du piège : une uniformité qui dit quelque chose du corpus
et rien du champ. Personne, dans aucun des quatre rigs, n'a jamais allumé un
deuxième moteur sur un groupe. Les tranches 3 et 4 sont les candidates
évidentes pour Color FX 2 et Move FX 2, et **le corpus est structurellement
incapable de le confirmer ou de l'infirmer**.

Conséquence à écrire noir sur blanc : `SPEC.md` §5.4 listait les tranches 0, 1,
2, 5, 6–11 et **sautait 3 et 4 en silence**. Un lecteur ne pouvait pas savoir
qu'elles existaient, encore moins qu'elles étaient vides.

### La tension que ça crée sur la tranche 5

Si la disposition est `[Color1, Move1, Beam1, Color2, Move2, Beam2]`, alors la
tranche 5 est **Beam FX 2** — et non « les groupes que le preset adresse ». Les
deux lectures prédisent la même chose sur tout le corpus, où `f17` vaut
`[255]×8` partout et où la tranche 5 vaut 255 partout. **Elles ne sont pas
séparées par les données.**

Le seul discriminant existant est l'écriture du graveur de l'appareil en
GEN-03, sur **un** fichier : il a corrigé 255 → 2 (= B) et 255 → 7 (= A+B+C) sur
des cues dont le moteur faisceau était à l'arrêt. Un masque de Beam FX 2 n'a
aucune raison de valoir « les groupes que la cue allume » quand ce moteur est
éteint, donc la lecture « groupes adressés » reste la meilleure — mais elle
tient sur **une** sauvegarde, et il faut le dire. L'identité
`tranche5_f16` de `wpj_identities.py` est trivialement vraie sur le corpus et
n'est discriminante que sur ce fichier-là.

### Deux hypothèses tuées sur la tranche 11, sans matériel

Ses valeurs — 5, 2, 7 — ont la forme d'un masque de groupes. Deux lectures
testées et **réfutées** en une commande chacune :

- « les groupes qui portent un luminaire » : **1 fichier sur 45** seulement.
  rig-c porte A, B et C — masque 7 — et ses presets portent 5 ou 2 ;
- « le numéro de schéma » : le schéma 11 porte **et** 2 (20 fichiers) **et** 5
  (13 fichiers).

Elle varie entre presets dans **un** fichier sur 42, ce qui affaiblit aussi le
« constante par projet » de §5.4 sans le réfuter. Reste non attribuée.

### Discriminateur, pas cher — **[planned]**

Un seul preset, une seule sauvegarde, aucun déploiement, aucun risque : au
panneau, sur le projet d'expérimentation, composer une cue où **Color FX
page 1 tourne sur le groupe A et Color FX page 2 sur le groupe B**, sauvegarder,
télécharger, differ contre l'avant.

| Lecture | tranche 0 | tranche 3 | p |
|---|---|---|---|
| `[C1, M1, B1, C2, M2, B2]` — les tranches 3/4/5 sont les seconds moteurs | **1** (= A) | **2** (= B) | 0,55 |
| le masque de la page 2 vit ailleurs (un champ non décodé, ou `f16` a plus de douze tranches) | 1 ou 3 | **0** | 0,2 |
| les deux pages ne sont pas per-groupe : SHIFT bascule la page pour **tout** le preset, et le slot 2 n'est qu'une configuration en réserve | **3** (= A+B) | 0 | 0,2 |
| autre chose | — | — | 0,05 |

La troisième rivale compte autant que les deux autres : « tourner en même temps
sur des groupes différents » vient du **manuel et de la presse**, pas d'une
mesure. C'est une source externe, du rang de `observed`, et elle n'a jamais été
vérifiée sur cet appareil.

Si la tranche 3 s'allume, la tranche 5 redevient douteuse et il faut rejouer
GEN-03 : deux lectures se disputeraient à nouveau le même masque.

**À lire au même tir : F7-01.** La passe corpus sur `f3`/`f7`/`f23`/`f27` a
trouvé un champ qui bouge — `f7`, non nul sur quatre presets, et exactement les
quatre dont le moteur faisceau est éteint alors que ses deux pages diffèrent.
C'est un second candidat pour porter la sélection de page. La même sauvegarde
répond aux deux entrées ; il suffit de regarder `f3` en plus de la tranche 3.

## F7-01 — `f7` n'est pas vide, et il pointe vers la question de FX2-01 — 2026-08-27 — **[observed]**

T6 demandait « corpus d'abord » sur les quatre tableaux par groupe non attribués
de 165 — `f3`, `f7`, `f23`, `f27`. La passe coûte une commande et rend un
résultat sur les quatre :

| Champ | Valeurs sur les 3697 occurrences |
|---|---|
| `f3` | `0000000000000000` — **toujours** |
| `f23` | `0000000000000000` — **toujours** |
| `f27` | `0000000000000000` — **toujours** |
| **`f7`** | `0000000000000000` × 3643, **`0001000000000000` × 54** |

### Le compte honnête est 4, pas 54

Le corpus porte 3697 *occurrences* de preset mais seulement **352 presets
distincts par contenu** : sept fichiers écrits par notre propre writer et sept
sauvegardes d'une même copie, plus les paires avant/après des expériences,
répliquent les mêmes entrées. Les 54 occurrences de `f7` non nul sont
**4 presets distincts** — ids 1, 82, 83 et 84 — recopiés dans 33 fichiers.

C'est le piège que `docs/methodology.md` décrit sous « compter le corpus
honnêtement », et il fallait le vérifier avant d'écrire « 54/54 ». La
corrélation ci-dessous porte sur **quatre échantillons**, pas cinquante-quatre,
et c'est ce qui l'empêche de dépasser `observed`.

### Ce que les quatre partagent

Les quatre presets ont **exactement le même profil `f16`** — tranches 0 à 5 :

```
[255, 255, 0, 0, 0, 255]
 │    │    │  │  │  └── tranche 5
 │    │    │  └──┴───── tranches 3 et 4, nulles comme partout
 │    │    └─────────── Beam FX : ÉTEINT
 │    └──────────────── Move FX : allumé sur les huit groupes
 └───────────────────── Color FX : allumé sur les huit groupes
```

Et leurs **trois** types d'effet ont slot 1 ≠ slot 2. Sur tout le corpus,
`f7` non nul et « moteur faisceau éteint **et** ses deux pages diffèrent »
coïncident sans exception dans les deux sens — sur ces quatre presets.

`f7` vaut toujours la même chose : élément **1** = 1, les sept autres nuls. Si
la lecture « tableau par groupe » de §5 tient, c'est le groupe **B**. Mais ces
presets adressent les **huit** groupes (tranches à 255), donc « le groupe B et
lui seul » n'a pas d'explication évidente, et une lecture « index » ou
« compteur » n'est pas écartée. **Aucun nom n'est proposé.**

### Pourquoi ça compte pour FX2-01

FX2-01 laissait une question ouverte : où vit l'affectation de la **deuxième
page** d'un effet ? `f7` est le premier champ du record qui bouge en même temps
qu'une deuxième page de faisceau. Candidat, à ce titre seulement :
**`f7` sélectionne la page active du Beam FX**, `f3` et `f23` faisant de même
pour Color et Move — ce qui expliquerait qu'ils soient nuls partout, personne
n'ayant jamais sélectionné une deuxième page dans ce corpus. `f27` resterait
sans emploi dans cette lecture, ce qui est un point contre elle : trois moteurs,
quatre champs.

Rivales, aucune départagée :

- `f7` sélectionne la page du Beam FX, par groupe ;
- `f7` marque « ce preset porte une configuration de faisceau en réserve », un
  drapeau et non un masque, et le `1` à l'élément 1 est un artefact d'encodage ;
- `f7` n'a aucun rapport avec les pages, et la coïncidence tient à quatre
  presets issus de la même séance d'édition — ce qui, à quatre échantillons,
  reste parfaitement possible.

### Ce que ça coûte de trancher

**Rien de plus que le discriminateur déjà posé en FX2-01** : un preset, une
sauvegarde au panneau, un téléchargement, un diff. Il suffit d'y ajouter une
lecture. Prédictions publiées, sur la cue où Color FX page 1 tourne sur A et
page 2 sur B :

| Lecture | `f16` tranche 3 | `f3` |
|---|---|---|
| la page vit dans `f16` (FX2-01, lecture 1) | **2** (= B) | inchangé, nul |
| la page vit dans `f3`/`f7`/`f23` (celle-ci) | 0 | **non nul**, élément 1 |
| les deux portent l'information | **2** | **non nul** |
| ni l'un ni l'autre | 0 | nul — et il faut chercher ailleurs |

Une seule sauvegarde répond aux deux entrées. C'est la raison d'écrire celle-ci
maintenant plutôt que de la garder pour plus tard : elle change ce qu'il faut
regarder après le tir, pas ce qu'il faut tirer.

### Un détail qui change la lecture

SPEC §5.6 note que ces quatre champs sont de l'**état vif** jusqu'à ce qu'un
preset les capture : une sauvegarde de projet ne les écrit pas, seul un
`SHIFT` + tap sur un pad le fait. Le `1` de `f7` n'a donc pas été tapé par
l'auteur du projet — il a été **cueilli au panneau** dans l'état où l'opérateur
l'avait laissé. Ça renforce la lecture « sélecteur » et affaiblit « drapeau
écrit par le writer » : un champ qui enregistre une sélection d'écran est
exactement ce qu'un sélecteur de page serait.

`f3`, `f23` et `f27` restent **non attribués**, et le corpus ne peut rien en
dire : ils sont nuls sur les 3697 occurrences. Uniformité du corpus, pas du
champ — pour la cinquième fois dans ce registre.

## FX2-01 et F7-01 mesurés — la page n'est pas dans `f16`, et j'ai posé une identité fausse — 2026-08-27

Le discriminateur a été tiré tel que publié : l'opérateur a composé au panneau
une cue **Color FX page 1 sur le groupe A, page 2 sur le groupe B**, puis a
sauvegardé. `projectChanged` valait `true` avant la sauvegarde et `false` après,
le fichier passe de 40999 à 45054 octets, et le preset créé est **l'id 82** —
dans le trou intérieur 82–99, celui que le générateur laisse derrière lui.

### Ce que la sauvegarde a touché, et rien d'autre

| Record | Changement |
|---|---|
| 165 | une entrée neuve (id 82), les quatre tableaux `STATIC GOBO` écrits sur **les 86** presets, et `f16` réécrit sur **exactement les quatre cues que nous avions écrites** (100, 101, 140, 141) |
| 115 | 349 → 287 octets, la migration `f6`/`f7` → `f9` séquentiel |

GEN-03 est reconfirmé point par point sur une seconde sauvegarde indépendante.

### FX2-01 : la prédiction à p = 0,55 est fausse

| | Prédit | Mesuré |
|---|---|---|
| `f16` tranche 0 (Color FX) | **1** = A | **3 = A+B** |
| `f16` tranche 3 | **2** = B | **0** |
| `f16` tranche 4 | — | 0 |

| Lecture publiée | p | Verdict |
|---|---|---|
| `[C1, M1, B1, C2, M2, B2]` — les tranches 3/4/5 sont les seconds moteurs | 0,55 | **réfutée** : la tranche 3 reste nulle alors qu'une deuxième page est en service |
| le masque de la page 2 vit **ailleurs** | 0,2 | **tenue** |
| les deux pages ne sont pas per-groupe, SHIFT bascule tout le preset | 0,2 | numériquement compatible (tranche 0 = 3), mais **son mécanisme est réfuté** : un champ par groupe distingue bien A de B, voir plus bas |
| autre chose | 0,05 | — |

> **Une seule tranche de `f16` porte un moteur d'effet, et elle couvre tous les
> groupes que ce moteur adresse — les deux pages comprises.** Le moteur couleur
> de la cue 82 vaut `3` = A+B, un seul masque pour deux pages. Les tranches 3
> et 4 restent nulles, y compris quand une deuxième page est réellement en
> service. Elles ne sont donc **pas** les seconds moteurs. **[validated]**

### La tranche 5 est tranchée, et gratuitement

La cue 82 a été **créée par l'appareil**, pas clonée par nous. Ses dimmers
valent `[0, 120, 0, 0, 0, 0, 0, 0]` — le groupe B seul — et sa tranche 5 vaut
**2 = B**. Son moteur faisceau est **éteint**.

> La rivale « la tranche 5 est le masque de Beam FX 2 » **tombe** : le faisceau
> est à l'arrêt et la tranche suit exactement le masque des dimmers non nuls. La
> lecture de GEN-03 ne repose plus sur une seule sauvegarde d'un fichier que
> nous avions écrit — elle tient sur une entrée que le firmware a composée seul.
> `tranche5_f16` passe sur ce fichier.

### F7-01 : ma corrélation ET mon attribution sont réfutées

`f7` de la cue 82 vaut **`[0, 1, 1, 0, 0, 0, 0, 0]`**, contre `[0, 1, 0, …]` sur
les quatre presets du corpus.

| Ce que F7-01 affirmait | Verdict |
|---|---|
| `f7` non nul ⟺ moteur faisceau éteint **et** ses deux pages diffèrent | **réfutée** : la cue 82 a `f7` non nul, le faisceau éteint et ses deux pages **identiques**. Le cinquième échantillon a tué une corrélation qui en avait quatre, exactement comme annoncé |
| répartition supposée `f3` = couleur, `f7` = faisceau, `f23` = mouvement | **réfutée** : c'est une édition de **couleur** qui a fait bouger `f7`, et `f3` est resté nul |

Ce qui reste, et c'est le résultat : **`f7` est le seul champ du record qui
distingue le groupe A du groupe B dans cette cue.** L'opérateur a mis A en
page 1 et B en page 2 ; `f7` vaut 0 sur A et 1 sur B. La lecture la plus
économique est un **sélecteur de page par groupe, 0 = page 1, 1 = page 2** —
et elle explique aussi les quatre presets du corpus, dont le groupe B est le
seul en page 2.

**Une anomalie franche, non expliquée : `f7[C]` vaut 1 aussi**, alors que le
moteur couleur de la cue n'adresse que A et B et que l'opérateur n'a nommé que
ces deux groupes. Trois lectures, aucune départagée : le groupe C a été touché
sans que ce soit rapporté ; le panneau applique la page à une sélection plus
large que les groupes du moteur ; ou l'index de `f7` n'est pas le groupe.
**Aucun nom n'est proposé pour `f7`, et son statut reste `observed`.**

### Une identité fausse, posée par moi ce matin, réfutée par l'appareil ce soir

`deux_pages_fx` affirmait qu'un moteur allumé stocke toujours **deux
configurations différentes** — 738/738, 1439/1439, 1186/1186 sur le corpus,
zéro exception. La cue 82 a le moteur couleur **allumé** (tranche 0 = 3) et ses
deux pages **identiques**. L'identité est **retirée du code**.

> C'est le piège de l'uniformité pour la cinquième fois dans ce registre, et
> cette fois c'est l'auteur de l'avertissement qui est tombé dedans, dans la
> même journée. Une corrélation sans exception sur 3697 occurrences n'était,
> encore une fois, qu'un fait sur le **corpus** : personne n'avait jamais
> enregistré une cue dont un moteur tourne avec ses deux pages au même réglage.
> La leçon n'est pas « vérifier plus » — elle est que **la seule défense est une
> écriture neuve**, et qu'ici elle a coûté un geste au panneau.

`f3`, `f23` et `f27` restent nuls, et non attribués.

### F7-01 confirmé à l'écran — `f7` est le sélecteur de page, et `f7[C]` n'était pas une anomalie — **[validated]**

Trois photographies du panneau, prises sur l'état qui a produit le fichier :
l'écran `HOME`, puis l'écran `COLOR FX` sur chacune des deux pages.

L'écran `HOME` donne l'affectation par groupe, et le fichier la donne aussi.
Correspondance **élément par élément** :

| Groupe | `f7` | Page à l'écran | `f16` tranche 0 | Moteur à l'écran | `f17` | Dimmer à l'écran |
|---|---|---|---|---|---|---|
| A | **0** | `COLOR FX1` | bit mis | encadré = actif | 0 | 0 % |
| B | **1** | `COLOR FX2` | bit mis | encadré = actif | 120 | **47 %** |
| C | **1** | `COLOR FX2` | bit **clair** | texte simple = inactif | 0 | 0 % |
| D–H | 0 | — | — | — | 0 | — |

> **`165.f7` est le sélecteur de page du Color FX, par groupe : 0 = `FX1`,
> 1 = `FX2`.** Huit éléments, trois groupes peuplés, deux valeurs distinctes, et
> la lecture tombe juste sur les trois. **[validated]**

### L'anomalie `f7[C]` est expliquée, et elle sépare deux champs

Le groupe C portait `f7` = 1 alors que le moteur couleur ne l'adresse pas.
L'opérateur : *« j'avais dû l'activer sur le C pour le tester, donc même s'il
est off, il doit considérer que c'est le Color FX 2 qui est en attente »* — et
l'écran le montre : le `COLOR FX2` du groupe C est écrit **sans cadre**, là où
ceux de A et B sont encadrés.

Ce n'était donc pas une anomalie mais **la mesure la plus utile de la série** :
deux champs orthogonaux, qu'on aurait pu confondre indéfiniment sur un corpus
où ils coïncident.

| Champ | Ce qu'il dit |
|---|---|
| `f16` tranche 0 | quels groupes le moteur couleur **allume** |
| `f7` | à quelle **page** chaque groupe est affecté, allumé **ou non** |

Un groupe éteint garde sa page en attente. C'est aussi ce qui explique les
quatre presets du corpus, dont le seul groupe B est en page 2 sans que rien
d'autre ne le trahisse.

### Pourquoi pas `device-confirmed`, et ce qu'il faudrait

La lecture est prise sur **un** état d'écran. Nous n'avons jamais **écrit**
`f7` nous-mêmes, et aucune page demandée par nous n'a été relue au panneau.
Le pas suivant est le même que pour tous les autres champs : composer deux cues
qui ne diffèrent que par `f7`, déployer, ouvrir, et vérifier à l'écran que la
page demandée est celle affichée.

**Le codec ne renomme pas `f7` pour autant.** Seule la couleur a été variée ;
`f3`, `f23` et `f27` restent nuls, et rien ne dit encore si `f7` porte la page
de la couleur seule ou si chaque moteur a la sienne. Un `fN` qui deviendrait
`page_color_fx` alors qu'il porte la page de tous les moteurs serait exactement
le renommage que ce dépôt existe pour éviter. Discriminateur : mettre un groupe
en **Move FX2** et regarder si c'est `f7` ou `f23` qui bouge.

### Corroboration gratuite pour GEN-02

L'écran `HOME` affiche le dimmer du groupe B à **47 %** là où le fichier porte
`f17` = 120. `120 / 255 = 47,06 %`, tronqué à **47**. Les groupes A et C, à
`f17` = 0, affichent **0 %**.

> `f17` est un **pourcentage** — GEN-02 l'avait établi par la sortie DMX et les
> bornes de course `106.f5`/`f6` ; le panneau le dit maintenant en toutes
> lettres, par un chemin qui ne passe pas du tout par le DMX. Deux voies
> indépendantes, même lecture.

### Les deux pages portent le même effet, et c'est pour ça que les slots sont égaux

Les écrans `COLOR FX` des deux pages montrent le **même** effet — `RAINBOW`,
`FADE` 100 %, `PHASE` 20 %, `SPEED` 50 %, `LINK GROUP` — ce qui explique
`color_fx1 == color_fx2` dans le fichier sans rien de mystérieux : l'opérateur a
affecté une page, pas réglé un effet différent dessus.

C'est aussi ce qui a tué l'identité `deux_pages_fx` : elle supposait qu'un
moteur allumé implique deux réglages distincts, alors que **la page est une
affectation, pas une configuration**. Les deux notions sont indépendantes, et
c'est la même confusion que celle entre `f16` et `f7` ci-dessus.

### F7-02 — le sélecteur est-il par moteur ? Prédiction publiée avant lecture — 2026-08-27

L'opérateur a mis le groupe **C en `MOVE FX2`** et sauvegardé. Le fichier n'a pas
encore été téléchargé au moment où ces lignes sont écrites.

État de départ, celui de la cue 82 déjà mesurée : `f7` = `[0, 1, 1, 0, 0, 0, 0, 0]`
(A en `COLOR FX1`, B et C en `COLOR FX2`), `f23` = `0000000000000000`, moteur
mouvement **éteint** (tranche 1 de `f16` = 0).

| Lecture | `f7` élément 2 | `f23` élément 2 | p |
|---|---|---|---|
| **un sélecteur par moteur** — `f7` couleur, `f23` mouvement | reste **1** | devient **1** | 0,4 |
| un sélecteur partagé, en **masque par moteur** (bit 0 couleur, bit 1 mouvement) | **1 → 3** | reste 0 | 0,2 |
| c'est `f3` ou `f27` qui porte le mouvement — ma répartition est encore fausse | reste 1 | reste 0, mais l'un des deux autres bouge | 0,1 |
| **rien ne bouge dans le record 165** : la page est de l'état vif, et une sauvegarde de projet ne l'écrit pas — seul un `SHIFT` + tap sur un pad le fait (SPEC §5.6) | reste 1 | reste 0 | **0,25** |
| autre chose | — | — | 0,05 |

La quatrième rivale n'est pas un remplissage : c'est la règle que SPEC énonce
déjà pour cette famille de champs, et la cue 82 n'avait reçu son `f7` que parce
qu'un preset avait été **capturé**. Si elle gagne, le résultat est une
confirmation de la règle et non un échec du tir — et il faudra refaire le geste
en capturant un preset.

Un sélecteur partagé en masque prédit `1 → 3`, ce qui le rend distinguable d'un
« rien ne bouge » ; c'était le point faible de la formulation initiale du
discriminateur, où « partagé » et « rien » rendaient la même trame.

### F7-02 mesuré — la rivale à p = 0,25 gagne, et le compteur de version ment — **[validated]**

Téléchargement après la sauvegarde. Le fichier fait toujours 45054 octets et
**vingt et un octets** le séparent du précédent :

```
positions 0–19  : l'en-tête SHA-1, recalculé par construction
position     40 : l'octet de poids faible du compteur de version, …666 -> …667
ailleurs        : RIEN, sur 45054 octets
```

Les 87 presets sont identiques champ par champ. `f7` n'a pas bougé — id 1 reste
`[0,1,0,…]`, id 82 reste `[0,1,1,…]` — et `f3`, `f23`, `f27` restent nuls.

| Lecture publiée | p | Verdict |
|---|---|---|
| un sélecteur par moteur — `f23` prend le mouvement | 0,4 | **non testée** : le tir n'est pas allé jusqu'à elle |
| sélecteur partagé en masque par moteur, `1 → 3` | 0,2 | **réfutée** : `f7[C]` reste 1 |
| c'est `f3` ou `f27` | 0,1 | **réfutée** : les deux restent nuls |
| **rien ne bouge : la page est de l'état vif, qu'une sauvegarde de projet n'écrit pas** | **0,25** | **tenue, à l'octet près** |

> **Confirmation propre de la règle de SPEC §5.6.** Un réglage de page fait au
> panneau ne quitte pas l'état vif : la sauvegarde de projet ne l'écrit pas dans
> le record 165. Seule une **capture de preset** — `SHIFT` + tap sur un pad — le
> fait, et c'est bien ainsi que la cue 82 avait reçu son `f7`. C'est un
> différentiel à une seule variable, et son résultat tient sur un octet.

**La question du sélecteur du Move FX reste donc entière.** Elle n'est pas
réfutée, elle n'a pas été posée : il faut refaire le geste en **capturant** la
cue dans un preset.

### Le compteur de version s'incrémente sur une sauvegarde qui n'écrit rien — **[validated]**

Le compteur des octets 40–47 est passé de `1787841428666` à `1787841428667`,
l'appareil rapporte la nouvelle version, `projectChanged` est retombé à `false`
— et **pas un octet de donnée n'a changé**.

`AGENTS.md` porte la consigne : « si le compteur n'a pas bougé, rien n'a été
écrit ». Elle reste vraie. **Sa réciproque est fausse, et c'est nouveau** : un
compteur qui s'incrémente ne prouve **pas** qu'une donnée a changé. Le piège
avait déjà été mal lu deux fois sur une seule expérience, dans les deux sens ;
voici le troisième cas, celui où le compteur dit « oui » et le contenu dit
« non ».

Conséquence pratique : le compteur est un oracle **négatif** et rien d'autre.
Pour savoir si quelque chose a changé, il faut comparer les records.

**Une réserve, et elle coûte un regard.** Ce fichier ne peut pas distinguer
« l'édition est restée dans l'état vif » de « l'édition n'a jamais pris au
panneau ». Les deux rendent le même octet. L'écran `HOME` les sépare
immédiatement : si le groupe C y affiche `MOVE FX2`, l'édition a pris et c'est
bien la première lecture.

### La réserve de F7-02 est levée — **[device-confirmed]**

L'opérateur confirme que l'écran `HOME` affiche bien `MOVE FX2` sur le groupe C.
L'édition avait donc **pris** et était restée dans l'état vif. Des deux lectures
que le fichier ne pouvait pas séparer, c'est la bonne qui tenait : une
sauvegarde de projet n'écrit pas un réglage de page, et le geste n'était pas en
cause.

## F7-03 — la capture dans un preset, prédiction publiée avant la sauvegarde — 2026-08-27

Même état vif, cette fois **capturé** dans un preset — `SHIFT` + tap, le seul
geste qui écrive cette famille de champs (SPEC §5.6, F7-02). L'opérateur annonce
le pad « 84 » ; au tir précédent le pad « 83 » a rendu l'**id 82**, donc l'entrée
attendue porte l'**id 83**, et cette correspondance pad = id + 1 est elle-même
une prédiction.

État vif à capturer, lu sur l'écran `HOME` : Color FX **A → FX1, B → FX2,
C → FX2** ; Move FX **C → FX2**, A et B en FX1.

| Lecture | `f7` | `f23` | p |
|---|---|---|---|
| **un sélecteur par moteur** — `f23` porte le mouvement | `[0,1,1,0,0,0,0,0]`, inchangé | **`[0,0,1,0,0,0,0,0]`** | **0,45** |
| `f3` ou `f27` porte le mouvement, ma répartition est encore fausse | inchangé | reste nul, mais l'un des deux prend l'élément 2 | 0,2 |
| `f7` est partagé, en masque par moteur | élément 2 : **1 → 3** | reste nul | 0,15 |
| la page du mouvement vit ailleurs — dans `f16`, ou dans un champ qu'on traite en opaque | inchangé | reste nul | 0,15 |
| autre chose | — | — | 0,05 |

Ce qui se lit sur **l'élément 2 et lui seul** : les groupes A et B restent en
`FX1` pour le mouvement, donc un champ qui porterait la page du mouvement doit
valoir 0 sur A et B et 1 sur C. Une valeur non nulle ailleurs qu'en position 2
réfute la lecture par groupe pour ce champ-là.

Deux observations attendues en plus, gratuites :

- le moteur mouvement est **à l'arrêt** sur les trois groupes (`MOVE FX1`/`FX2`
  s'affichent sans cadre) ; la tranche 1 de `f16` doit donc valoir **0** alors
  qu'un sélecteur de page marque C. C'est le même découplage que `f7[C]` a déjà
  montré pour la couleur, et le revoir sur un autre moteur le généralise ;
- `f7` de la nouvelle entrée doit reproduire `[0,1,1,0,…]`, puisque les pages
  couleur n'ont pas bougé. S'il diffère, c'est que la capture ne fige pas ce
  qu'on croit.

**Il faut les deux gestes** : la capture écrit dans la copie vive, la sauvegarde
de projet la porte au fichier. F7-02 vient de montrer qu'une sauvegarde seule ne
suffit pas ; une capture seule ne suffira pas non plus.

### F7-03 mesuré — `f23` est le sélecteur du mouvement, et le record range ses moteurs en quadruplets — **[validated]**

**Note de méthode, à charge.** La prédiction ci-dessus a été publiée et commitée
**avant lecture** du fichier, mais l'opérateur avait déjà capturé et sauvegardé :
la mesure existait sur l'appareil quand j'ai écrit les probabilités. La
protection contre la confirmation rétrospective tient — rien n'avait été lu —
mais la formule « publiée avant la mesure » ne s'applique pas ici, et il fallait
le dire plutôt que de laisser la date du commit le suggérer.

La capture crée l'entrée **id 83**, depuis le pad annoncé « 84 » : la
correspondance **pad = id + 1** tient, comme au tir précédent. Aucun preset
existant n'est modifié ; seul le record 165 grandit, de 31591 à 31928 octets.

| | Prédit | Mesuré |
|---|---|---|
| `f23` | `[0, 0, 1, 0, 0, 0, 0, 0]` | **`[0, 0, 1, 0, 0, 0, 0, 0]`** |
| `f7` | `[0, 1, 1, 0, 0, 0, 0, 0]`, inchangé | **inchangé** |
| id de l'entrée | 83 | **83** |
| `f16` tranche 1 (Move) | 0 | **4 = C** — *faux* |

La favorite à **p = 0,45** est exacte, sur l'élément **2 et lui seul**. Les trois
rivales tombent : `f7` n'a pas pris de second usage, `f3` et `f27` restent nuls.

> **`165.f23` est le sélecteur de page du Move FX, par groupe : 0 = `FX1`,
> 1 = `FX2`.** Et le tir vaut autant pour l'autre champ : une modification de la
> page **mouvement** a laissé `f7` **rigoureusement identique**. C'est le
> différentiel à une variable qui manquait pour dire que `f7` porte la couleur
> **et elle seule**, au lieu d'un sélecteur partagé. Les deux montent à
> `validated`.

### Ce que je pariais en plus, et que j'ai raté

J'avais prédit `f16` tranche 1 = **0**, en lisant sur la photographie que les
`MOVE FX` sans cadre valaient « moteur à l'arrêt ». Mesuré : **4 = C**, le moteur
mouvement est **allumé** sur ce groupe. Ma lecture de l'écran était fausse — ou
l'opérateur a allumé le moteur en posant la page, et rien dans les photos ne
permet de trancher.

Le découplage annoncé survit quand même, mais sur la **couleur** et non sur le
mouvement : la tranche 0 vaut `3` = A+B pendant que `f7` marque aussi **C**. Un
groupe garde sa page couleur en attente, moteur éteint. Ce n'est plus une
mesure nouvelle, c'est la même qu'en F7-01 — la généralisation à un second
moteur, elle, n'a pas eu lieu.

### La structure du record, et la place vide qu'elle désigne

Les trois moteurs sont rangés en **quadruplets réguliers** : la paire de pages,
le sélecteur, puis le champ « actif ».

| Moteur | page 1 | page 2 | **sélecteur** | actif |
|---|---|---|---|---|
| Beam | `f1` | `f2` | **`f3`** | *(place occupée par `f4`)* |
| Color | `f5` | `f6` | **`f7`** — mesuré | `f8` |
| Move | `f21` | `f22` | **`f23`** — mesuré | `f24` |

> **Prédiction structurelle : `f3` est le sélecteur de page du Beam FX.**
> **[hypothesized]** — il est nul sur les 3697 occurrences du corpus parce que
> personne n'y a jamais posé de deuxième page de faisceau, exactement comme
> `f23` l'était avant ce tir. Le geste qui la teste est le même : mettre un
> groupe en `BEAM FX2`, **capturer**, sauvegarder. Attendu :
> `f3` = un 1 sur le groupe choisi, `f7` et `f23` inchangés.

Deux réserves sur le tableau. `f4` occupe la place du « actif » du faisceau mais
F4-03 en a fait un **masque de permission sur les trois moteurs** ; la
coïncidence de position est notée, elle n'est pas une lecture. Et `f27` ne suit
pas le motif — `f25` est le nom du preset — donc il reste sans emploi et sans
nom.

### Le codec nomme les deux champs prouvés, et pas le troisième

`f7` devient `page_color_fx`, `f23` devient `page_move_fx`, tous deux en
tableaux de huit varints. Round-trip octet-identique revérifié : 45/45 sur le
corpus, plus les deux fichiers écrits par l'appareil ce soir. **`f3` garde sa
clé neutre** : une place dans un motif régulier n'est pas une mesure, et le
renommer sur cette base serait précisément la faute que ce dépôt existe pour
éviter.

Confirmation au passage, troisième d'affilée sur une entrée que l'appareil a
composée seule : la tranche 5 vaut **2 = B**, exactement le masque des groupes
dont `f17` est non nul.

## F7-04 — `f3` et le troisième moteur, prédiction publiée avant lecture — 2026-08-27

L'opérateur a mis le groupe **A en `BEAM FX2`** et le groupe **B en `BEAM FX1`**,
capturé dans un preset et sauvegardé. Comme au tir précédent, la mesure existe
déjà sur l'appareil : ces probabilités sont publiées **avant lecture**, pas avant
la mesure, et c'est une garantie plus faible qu'il faut nommer.

État attendu de l'entrée neuve, par report des deux tirs précédents : `f7` =
`[0,1,1,0,…]` (couleur inchangée), `f23` = `[0,0,1,0,…]` (mouvement inchangé).

| Lecture | `f3` | `f7` / `f23` | p |
|---|---|---|---|
| **`f3` est le sélecteur du faisceau** — le quadruplet tient sur les trois moteurs | **`[1, 0, 0, 0, 0, 0, 0, 0]`** | inchangés | **0,6** |
| la page du faisceau vit ailleurs — `f16`, ou un champ traité en opaque | reste nul | inchangés | 0,2 |
| c'est `f27` qui la porte, et le motif du quadruplet est une coïncidence | reste nul | inchangés, `f27` prend l'élément 0 | 0,1 |
| `f3` bouge mais pas en position 0 | non nul ailleurs | — | 0,05 |
| autre chose | — | — | 0,05 |

**Le groupe B est le contrôle, et il n'était pas prévu au protocole.** L'opérateur
l'a mis en `BEAM FX1` *explicitement*, alors que 0 est déjà la valeur d'un groupe
auquel personne n'a touché. Si `f3[B]` vaut **0**, une page 1 posée à la main est
indiscernable d'une page jamais réglée : le champ encode la page, pas le fait
d'avoir été réglé. Une troisième valeur en position 1 dirait le contraire, et ce
serait une découverte à part entière.

Je ne prédis **pas** la tranche 2 de `f16`. Au tir précédent j'avais déduit
l'état du moteur d'une photographie et je me suis trompé ; sans photo cette
fois, je n'ai aucune base, et une case laissée vide vaut mieux qu'un pari
déguisé en lecture.

Id attendu : **84**, la première place libre.

### F7-04 mesuré — le quadruplet tient sur les trois moteurs — **[validated]**

La capture crée l'entrée **id 84**, et aucun preset existant ne bouge. Records
touchés : 165, plus la migration habituelle de 115.

| | Prédit | Mesuré |
|---|---|---|
| `f3` | `[1, 0, 0, 0, 0, 0, 0, 0]` | **`[1, 0, 0, 0, 0, 0, 0, 0]`** |
| `page_color_fx` (`f7`) | `[0, 1, 1, 0, …]`, inchangé | **inchangé** |
| `page_move_fx` (`f23`) | `[0, 0, 1, 0, …]`, inchangé | **inchangé** |
| id | 84 | **84** |
| `f27` | — | reste nul |

La favorite à **p = 0,6** est exacte, et les trois rivales tombent. Deux pages
posées sur deux moteurs différents, deux tirs plus tôt, n'ont pas bougé d'un
octet : c'est le différentiel à une variable, pour la troisième fois d'affilée.

> **`165.f3` est le sélecteur de page du Beam FX, par groupe.** Le record range
> ses trois moteurs en **quadruplets réguliers** — paire, sélecteur, actif — et
> le motif est maintenant mesuré sur les trois, pas déduit sur deux.

| Moteur | page 1 | page 2 | sélecteur | actif | tir |
|---|---|---|---|---|---|
| Beam | `f1` | `f2` | **`f3`** | *(`f4`)* | F7-04 |
| Color | `f5` | `f6` | **`f7`** | `f8` | F7-01 |
| Move | `f21` | `f22` | **`f23`** | `f24` | F7-03 |

### Le contrôle que l'opérateur a ajouté sans le vouloir

Le groupe B a été mis en `BEAM FX1` **explicitement**, alors que 0 est déjà la
valeur d'un groupe auquel personne n'a touché. Mesuré : **`f3[B]` = 0**.

> Une page 1 posée à la main est **indiscernable** d'une page jamais réglée. Le
> champ encode la **page**, pas le fait d'avoir été réglé. C'est ce qui autorise
> à lire les zéros des sept autres groupes comme « page 1 » et non comme
> « absent », et ça vaut pour les trois sélecteurs.

### La case que je n'ai pas remplie

J'avais refusé de prédire la tranche 2 de `f16`, après m'être trompé au tir
précédent en déduisant l'état d'un moteur d'une photographie. Mesuré :
**3 = A+B**, le moteur faisceau est allumé sur les deux groupes. La retenue
était justifiée — je n'avais aucune base — et l'abstention n'a rien coûté au
tir.

### Ce que ça ferme, et ce qui reste

Les quatre tableaux par groupe non attribués de 165 étaient `f3`, `f7`, `f23` et
`f27`. **Trois sont maintenant nommés**, un tir chacun, et le codec leur donne
leur clé sémantique : `page_beam_fx`, `page_color_fx`, `page_move_fx`. Round-trip
octet-identique revérifié : 45/45 sur le corpus et sur les trois fichiers écrits
par l'appareil.

**`f27` reste seul et sans emploi.** Il ne suit pas le motif du quadruplet —
`f25` est le nom du preset — et il est nul sur les 3697 occurrences comme sur les
trois entrées neuves. Aucune hypothèse à discriminateur pas cher n'a émergé, et
c'est la condition que T6 posait pour aller au matériel.

Ce que « Double Trouble » ajoutait au format est donc décrit en entier côté
fichier : deux configurations par moteur, un masque de groupes par moteur qui
couvre les deux, et un sélecteur par groupe qui dit laquelle est en service —
indépendant de l'allumage du moteur.

## FX6-01 — le décompte du manuel : « quatre propriétés pour trois champs » était faux — 2026-08-30 — **[observed]**

Le manuel décrit les trois écrans FX un par un. Lus côte à côte, ils ne disent
pas ce que ce registre leur faisait dire.

| Écran | Propriétés annoncées |
|---|---|
| `COLOR FX` | Speed · Phase · Order · Size · Fade — **cinq** |
| `MOVE FX` | Speed · Phase · Order · Size · Fan · Fade · Flick — **sept** |
| `BEAM FX` | Speed · Phase · Order · Size · **Feature** · Fade — **six** |

L'écran du faisceau n'avait jamais été lu ici. Il porte une propriété que ni la
couleur ni le mouvement n'ont : la **Feature**, le canal auquel le Beam FX est
accroché — dimmer par défaut, changeable vers pan, tilt, iris ou zoom. Elle
partage le troisième encodeur avec `Size`, une pression bascule de l'une à
l'autre, exactement comme `Size | Fan` sur le mouvement.

### Le décompte corrigé

Trois erreurs se cumulaient dans la formule « quatre propriétés d'écran, trois
champs ».

1. **`Order` était compté deux fois.** C'est `f4`, déjà nommé `link_order` dans
   ce registre depuis F4-03 (0–3 None, 10–13 Group, 20–23 Fixture). Le compter
   parmi les non attribués gonflait le numérateur d'une unité.
2. **`Flick` n'est pas une valeur.** Le manuel en fait un **mode** du quatrième
   encodeur : il pousse le temps de fondu au-delà de 100 % du temps de pas, ce
   qui annule les fondus en cours. C'est le haut de la course de `Fade`, pas un
   champ. Corroboré par le corpus : `f6`, `f8` et `f9` restent **dans 0–100 sur
   les 352 presets distincts**, aucun débordement, sur les trois moteurs — le
   mode Flick n'a simplement jamais été utilisé ici.
3. **`Feature` manquait au dénominateur.** Elle explique `f5` côté faisceau, la
   case que L1 laissait vide.

Décompte réel, une fois `Speed` (`f2` + `f1` + `f10`) et `Order` (`f4`) mis de
côté :

| Moteur | Propriétés restantes | Champs disponibles |
|---|---|---|
| Beam | Phase · Size · Fade · **Feature** | `f6` · `f8` · `f9` · **`f5`** |
| Colour | Phase · Size · Fade | `f6` · `f8` · `f9` |
| Move | Phase · Size · Fade · **Fan** | `f6` · `f8` · `f9` · **`f3`** |

**Trois propriétés pour trois champs sur les trois moteurs**, plus une
quatrième propre à chaque moteur qui tombe sur le champ que ce moteur est le
seul à porter. Le motif est régulier, et il l'était depuis le début.

### Ce que ça rétracte

> La formule « les écrans du fabricant portent **quatre** propriétés pour trois
> champs, donc trois champs ne peuvent pas les tenir » est **retirée**. Elle
> reposait sur un double comptage d'`Order` et sur `Flick` pris pour une valeur.

Cascade, comme la méthodologie l'exige. Ce qui reposait dessus :

- **L9 change de nature, pas de statut.** `f6` et `f9` restent `[observed]` — le
  décompte ne dit pas *laquelle* des trois propriétés tombe sur quel champ. Mais
  la question passe de « quatre noms pour trois cases, insoluble sans plus » à
  **une permutation à trois éléments**, que la section suivante ferme en une
  sauvegarde.
- **`wpj_show.py` continue de refuser d'écrire `f6`/`f9`.** Le refus est
  maintenu, sa justification change : ce n'est plus « la question est mal
  posée », c'est « la permutation n'est pas encore mesurée ».
- **`f8` = `Size` et `f3` = `Fan` restent `[hypothesized]`.** Le décompte les
  rend plus probables, il ne les mesure pas. Un décompte n'est pas une mesure.

### Les défauts d'usine, relevés sur la page 2

Les pages 2 des trois moteurs sont **constantes sur les 352 presets distincts**
du corpus — personne n'y a jamais touché. Ce sont donc les valeurs de sortie
d'usine, et elles servent d'ancrage aux prédictions qui suivent.

| | `f3` | `f5` | `f6` | `f8` | `f9` | `vitesse` | `link_order` | `bpm_division` |
|---|---|---|---|---|---|---|---|---|
| `beam_fx2` | absent | **absent** | 25 | 100 | 50 | 100 | 10 | 3 |
| `color_fx2` | absent | `2000` | 20 | **absent** | 50 | 100 | 10 | 3 |
| `move_fx2` | 50 | `00` | **absent** | 100 | 50 | 100 | 10 | 2 |

Deux anomalies à garder en tête, parce qu'elles sont des prédictions en creux :

- **`beam_fx1.f5` et `beam_fx2.f5` sont absents sur les 352 presets distincts**
  — 3697 occurrences, pas une seule valeur. Si `f5` est la Feature, `0` =
  Dimmer est le défaut, omis par proto3, et **personne dans ce corpus n'a jamais
  changé la Feature d'un Beam FX**. C'est exactement la forme attendue, et c'est
  ce qui rend FX6-03 binaire.
- **`color_fx1.f8` est présent sur 10 presets sur 352**, absent — donc à `0` —
  sur les 342 autres, et absent partout sur `color_fx2`. Si `f8` est `Size`, la
  taille par défaut d'un effet de couleur est **0**, alors qu'elle est 100 sur
  le faisceau et le mouvement. Soit `Size` ne se stocke pas en `f8` côté
  couleur, soit son neutre y est réellement 0. FX6-02 le mesure au passage.

---

## FX6-02 — `Phase` / `Size` / `Fade` du Color FX, prédiction publiée avant la mesure — 2026-08-30

Une permutation à trois éléments se ferme en une capture, à condition que les
trois valeurs soient **mutuellement distinctes** et **absentes du vocabulaire
d'usine** : la lecture se lit alors dans la valeur elle-même, sans arbitrage.
Précédent maison : GOBO-02 avait nommé les cinq features du `STATIC GOBO` en un
seul différentiel, par le même argument.

**Manipulation.** Écran `COLOR FX`, **page 1**. Deuxième encodeur poussé sur
`Phase` (et non `Order`) → **37**. Troisième encodeur → `Size` **62**.
Quatrième encodeur → `Fade` **88**. Rien d'autre. Puis `SHIFT` + tap sur le
premier pad libre pour capturer, et sauvegarde du projet.

`37 / 62 / 88` : trois valeurs distinctes, aucune dans `{20, 25, 50, 100}`, le
vocabulaire d'usine des trois champs.

| Lecture | `f6` | `f8` | `f9` | p |
|---|---|---|---|---|
| **`f6` = Phase, `f8` = Size, `f9` = Fade** | **37** | **62** | **88** | **0,55** |
| `f6` = Phase, `f8` = Fade, `f9` = Size | 37 | 88 | 62 | 0,15 |
| `f6` = Fade, `f8` = Size, `f9` = Phase | 88 | 62 | 37 | 0,12 |
| une autre des six permutations | — | — | — | 0,08 |
| hors modèle : un numéro de champ jamais vu apparaît, ou une des trois propriétés ne s'écrit pas | — | — | — | 0,10 |

La favorite tient à trois arguments de neutre, tous tirés du tableau des
défauts ci-dessus, et aucun n'est décisif seul :

- `f9` vaut **50 sur les six pages des trois moteurs**. Une uniformité parfaite
  entre moteurs va à une propriété générique — `Fade` — plutôt qu'à une
  propriété dont le réglage utile dépend de l'effet.
- `f6` vaut 25 / 20 / **0** selon le moteur. Un neutre qui change par moteur va
  à `Phase` : un chase de faisceau veut un peu d'étalement, un effet de
  mouvement n'en veut aucun.
- `f8` vaut 100 sur le faisceau et le mouvement, ce qui est le neutre de
  `Size` partout ailleurs dans ce format. Le 0 de la couleur est l'anomalie
  qu'on mesure.

**Sous-prédiction, indépendante de la permutation** : `color_fx1.f8` doit
**apparaître** dans l'entrée neuve. Il est absent sur 342 presets sur 352. S'il
reste absent après avoir tourné l'encodeur `Size`, alors `Size` ne s'écrit pas
en `f8` côté couleur, et la troisième ligne du tableau monte quoi qu'il arrive
sur le reste.

**Contrôles, intégrés à la capture** — ce sont eux qui ont porté F7-01, F7-03 et
F7-04, trois fois de suite :

- `color_fx2` reste **octet pour octet** identique : la page 2 n'a pas été
  touchée ;
- `beam_fx1` et `move_fx1` de l'entrée neuve restent aux défauts d'usine ;
- aucun preset existant ne bouge ;
- `LIVE EDIT` **désactivé** sur la cue mesurée (`165.f10` bit 4 posé), sans quoi
  c'est la copie vive qu'on lit et pas le fichier — le cinquième piège du
  registre, celui qui a coûté GEN-03.

Id attendu : **85**, la première place libre après F7-04.

---

## FX6-03 — L1 : la `Feature` du Beam FX, prédiction publiée avant la mesure — 2026-08-30

`wpj-toolkit` (MIT) publie une énumération `feature` réservée au faisceau —
`0` Dimmer · `1` Zoom · `2` Iris · `3` Pan · `4` Tilt · `5` Effect — **sans
emplacement sur le fil**. Le manuel décrit la même propriété sur l'écran `BEAM
FX`, dimmer par défaut, et cite pan, tilt, iris et zoom comme destinations.
Le corpus donne le troisième point : `beam_fx1.f5` est **absent sur les 352
presets distincts**, ce qui est la signature d'un `0` jamais changé.

Trois sources indépendantes désignent la même case. Aucune ne l'a mesurée.

**Manipulation.** Écran `BEAM FX`, **page 1**. Troisième encodeur **poussé**
pour passer de `Size` à `Feature`, puis tourné jusqu'à **`Zoom`**. Rien
d'autre — en particulier ne pas toucher `Size`, qui partage l'encodeur. Puis
`SHIFT` + tap sur le pad libre suivant, et sauvegarde.

| Lecture | `beam_fx1.f5` | p |
|---|---|---|
| **`f5` = Feature, énumération du toolkit, `Zoom` = 1** | **`1`** | **0,55** |
| `f5` = Feature, mais l'ordre de l'énumération diffère | un autre petit entier | 0,20 |
| la Feature vit dans un champ jamais observé | `f5` absent, un numéro neuf apparaît | 0,10 |
| état vif, non capturé par un preset | record 165 inchangé | 0,10 |
| autre chose | — | 0,05 |

La quatrième ligne n'est pas un remplissage : F7-02 a mesuré qu'une
réassignation de page faite au panneau et sauvegardée laisse les 45054 octets
identiques au compteur de version près. Tout ce qui vit sur ces écrans n'est pas
forcément dans le fichier, et la capture est ce qui l'y met — ou pas.

**Contrôles** : `beam_fx2.f5` reste absent ; `color_fx1` et `move_fx1` de
l'entrée neuve restent aux défauts ; `beam_fx1.f8` (`Size`) reste à 100, ce qui
prouve que l'encodeur partagé a bien basculé de mode et n'a pas seulement
tourné.

Id attendu : **86**.

### Le bonus DMX, et il nomme un rôle

Le projet d'expérience est taillé sur *rig-c* : son record 106 porte les quatre
rôles encore sans nom, **14** (1 canal), **15**, **21** et **22** (6 canaux
chacun). Si la Feature est bien le canal auquel le moteur s'accroche, alors avec
le Beam FX allumé l'animation doit **quitter les canaux de rôle 0** (dimmer) et
atterrir sur l'un de ces quatre groupes.

Ce serait un second résultat gratuit : le rôle qui bouge **est** le zoom, et
`ROLES_106` dans `tools/wpj_identities.py` gagne un nom sur les quatre qui lui
manquent. Enveloppe min/max par canal sur 2048, comme d'habitude, jamais une
trame isolée.

Conditionnel : il faut qu'au moins une fixture du groupe adressé porte
réellement un canal de zoom. Si l'animation reste sur le rôle 0, ça ne réfute
pas `f5` = Feature — ça dit que le groupe testé n'a pas la feature demandée, et
le manuel ne promet pas ce que fait le moteur dans ce cas. La mesure côté
**fichier** reste la mesure principale ; le DMX est un bonus, pas un juge.

### Pourquoi les deux tirs tiennent dans une seule session

Deux captures successives sur le même projet, une seule sauvegarde, un seul
téléchargement. Les deux entrées sont des **entrées séparées** du record 165 :
l'entrée 85 doit montrer `beam_fx1.f5` absent, l'entrée 86 doit montrer
`color_fx1.f6/f8/f9` aux défauts couleur (20 / absent / 50). Chacune est donc le
contrôle de l'autre, et aucune des deux ne perd son caractère de différentiel à
variable unique.

Si les deux tirs tombent, il ne reste dans le sous-message FX que `f3` (`Fan`,
mouvement) et `f8` (`Size`) au statut `[hypothesized]`, tous deux tenus par le
même décompte — et le trou sémantique du format de show est fermé.

## GOBO-01 — la bibliothèque d'icônes gobo, et où elle vit — **[validated]**

Ouverte le 2026-08-30 sans toucher au W1 : tout est dans des fichiers locaux
que WTOOLS a déjà téléchargés. Elle ferme « `f2` est un id d'image globale …
qui doit vivre dans la bibliothèque de luminaires » — c'était presque ça, mais
l'image n'est ni dans le projet ni dans le profil : **elle est dans le flash de
l'appareil**.

| Maillon | Où | Contenu |
|---|---|---|
| profil du luminaire | `~/Library/Application Support/com.nicolaudiegroup.wtools/fixture_profiles.db`, table `CachedFixtureProfile`, colonne `profile_data` = JSON du cloud Nicolaudie | `profileFeatures[].userNum` = l'id d'image, par plage DMX |
| projet | `.wpj` record 111 `f4`, puis record 145 `f2` | le même id, recopié |
| image | `wm-fw-bundle-*/wolfmixFlash.bin`, table de **800 entrées de 30 o** en fin de fichier | `ptr u32 LE • 6 o • nom 20 o` ; **705 icônes distinctes**, les autres slots pointent sur `Open` |
| icône | `ptr − 0x10100000` | **1728 o = 24×24 px, RGB565 LE + alpha 8 bits** |

La base `0x10100000` n'est pas devinée : la zone d'images se termine à l'octet
près là où la table commence. `tools/gobo_library.py` la recalcule à chaque
lecture et son self-check l'assert.

Vérification croisée sur *rig-c*, trois sources qui ne se parlent pas : le
profil `UKing ZQ02244` (17 plages `type 8`, `userNum` 425→420 puis 342→352), le
record 145 du projet (mêmes 17 valeurs, même ordre), et les noms lus dans le
flash — `Open7…Open2` puis `Gobo01…Gobo11`. Les six premières sont bien la
**série de disques gradués** décrite d'après photographie en 2026-08-26, et les
onze suivantes sont des **icônes génériques numérotées** (un anneau de points
avec le chiffre au centre) : le profil du fabricant n'a jamais cartographié les
vrais gobos de cette lyre.

**Le piège** : les icônes numérotées ressemblent à un motif réel sur l'écran.
Ce n'est pas un rendu approximatif du gobo physique, c'est un remplissage — le
`userNum` du profil pointe sur un espace réservé.

### Ce qui reste ouvert — ce qu'écrit GOBO EDIT (mode 14)

Le pad 10 de *rig-c* porte `145.f3 = 'points'` alors que son `f2` (345 =
`Gobo04`) suit toujours le profil. L'écran GOBO EDIT (STATIC GOBO → SHIFT + un
pad, `mode-map.md`) propose une liste d'icônes nommées sur 4 pages, et
« Dots » s'y traduit en français par « points ».

Prédiction avant mesure, p = 0,7 : GOBO EDIT écrit **`f3` seul**, le nom, et
laisse `f2` sur la valeur du profil — sinon `f2` du pad 10 aurait déjà quitté
345. Rivale : il écrit les deux, et le pad 10 n'a jamais été confirmé par
`ENTER`. Discriminateur, une seule sauvegarde : ouvrir GOBO EDIT sur le pad 7,
choisir une icône franchement différente (`Cross`, id 212), sauvegarder,
retélécharger, differ le record 145. Si `f2[7]` passe à 212, la palette est
éditable au panneau et l'identité `[145].f2 == [111 f3==14].f4` cesse d'être
vraie sur un fichier édité — elle décrit alors une palette **jamais retouchée**,
pas une contrainte du format.

### FX6-02 amendé — l'opérateur voit `SIZE` grisé sur Rainbow, et le corpus le dit aussi — 2026-08-30

Deux écarts au protocole, tous deux signalés par l'opérateur au moment de la
capture, et tous deux **utiles** :

1. l'effet n'est pas resté sur le défaut : `SPARKLE` a été choisi **parce que
   `RAINBOW` affiche `SIZE` désactivé** ;
2. `SPEED` laissé à **50 %**, mode `Clock`, au lieu du 100 d'usine.

Les deux tombent sur des champs déjà nommés — `f7` (ACC-04, device-confirmed) et
`f2`/`f10` — donc la permutation `f6`/`f8`/`f9` reste un différentiel propre. La
photo de l'écran donne l'état exact avant capture : `FX1 | SPARKLE`,
`LINK NONE`, `FADE 88 %`, `SIZE 62 %`, `PHASE 37 %`, `SPEED 50 %`.

**La remarque sur Rainbow est une mesure, pas une anecdote.** Croisée avec le
type d'effet sur les 352 presets distincts, la présence de `f8` côté couleur est
**exactement** gouvernée par l'effet :

| `color_fx1.effet` | n | `f6` | `f8` | `f9` |
|---|---|---|---|---|
| `0` Rainbow 1 | 314 | 293 | **0** | 314 |
| `2` Chaser 1 | 10 | 10 | 6 | 10 |
| `3` Light Fever | 12 | 12 | 4 | 12 |
| `6` Rainbow 3 | 16 | 12 | **0** | 16 |

**330 presets sur un effet Rainbow, pas un seul `f8`.** Les deux seuls effets qui
en portent jamais sont les deux non-Rainbow. L'anomalie « la taille par défaut
d'un effet de couleur serait 0 » est **retirée** : `f8` n'est pas à zéro sur
Rainbow, il est **absent parce que la propriété n'existe pas sur cet effet** —
ce que l'écran affiche en grisé et ce que l'opérateur a lu avant nous.

### Trois arguments de structure, publiés avant la lecture du téléchargement

Le même croisement sur les trois moteurs sépare les trois champs par leur
**forme d'absence**, indépendamment de toute valeur :

| Champ | Forme | Ce que ça dit |
|---|---|---|
| `f9` | présent **352/352**, sur les trois moteurs et tous les effets | n'est **jamais** à 0 → n'est **pas** `Phase`, dont le neutre 0 serait omis sur la majorité |
| `f8` | présent partout **sauf** là où l'effet désactive la propriété (Rainbow) | une présence **gatée par l'effet**, ce qui est la signature d'une propriété que l'écran retire — `Size` |
| `f6` | absent sur 252/352 en mouvement, 25/352 en couleur | souvent à 0 → un neutre à 0 → `Phase` |

Aucun des trois n'est décisif seul. Ensemble ils pointent tous vers la même
permutation, et c'est la favorite déjà publiée. Je **monte** donc sa probabilité
avant de lire, plutôt qu'après :

| Lecture | `f6` | `f8` | `f9` | p posée | **p amendée** |
|---|---|---|---|---|---|
| **`f6` = Phase, `f8` = Size, `f9` = Fade** | **37** | **62** | **88** | 0,55 | **0,80** |
| `f6` = Phase, `f8` = Fade, `f9` = Size | 37 | 88 | 62 | 0,15 | 0,05 |
| `f6` = Fade, `f8` = Size, `f9` = Phase | 88 | 62 | 37 | 0,12 | 0,03 |
| une autre des six permutations | — | — | — | 0,08 | 0,05 |
| hors modèle | — | — | — | 0,10 | 0,07 |

Prédictions annexes de la même capture, toutes lisibles d'un coup :

- `color_fx1.f7` = **1** (`Sparkle 1`, énumération couleur) — un type d'effet que
  le corpus n'a **jamais** porté : les 352 presets distincts n'utilisent que 0,
  2, 3 et 6. La capture élargit le vocabulaire mesuré de `f7`.
- `color_fx1.vitesse` = **50**, `speed_source` absent (`Clock`).
- `color_fx1.f8` **apparaît**. Sur `SPARKLE` l'écran affiche `SIZE 62 %`, donc la
  propriété est active sur cet effet — et si `f8` est bien `Size`, il ne peut pas
  rester absent. C'est le point le plus dur du tir : une absence de `f8` ici
  réfute la favorite à elle seule, sans avoir besoin des deux autres valeurs.

### FX6-03 amendé — l'opérateur a bougé `PHASE` et `FADE` aussi, et `FADE 0 %` est un test gratuit — 2026-08-30

État de l'écran `BEAM FX` au moment de la capture B, lu sur photo :
`FX1 | SIN WAVE`, `LINK GROUP`, `FADE 0 %`, `SIZE | FEATURE → ZOOM`,
`PHASE | ORDER 94 %`, `SPEED 75 %`.

Trois écarts au protocole posé, qui demandait de ne toucher que la `Feature` :

| Écart | Conséquence |
|---|---|
| `PHASE` porté à **94 %** | une **seconde** lecture de la permutation, sur un autre moteur, avec une autre valeur |
| `FADE` porté à **0 %** | voir ci-dessous — c'est le test le plus informatif du tir |
| `SPEED` à 75 %, `LINK GROUP` | champs déjà nommés (`f2`, `f4` = 10, le défaut) ; sans effet sur la permutation |

**`FADE 0 %` teste directement l'argument publié plus haut.** J'ai écrit que `f9`
est présent sur les 352 presets distincts, donc jamais à 0, donc pas `Phase`
dont le neutre est 0. Si `f9` est `Fade`, alors un fondu réglé à **0** doit le
faire **disparaître** de l'entrée neuve — proto3 omet les zéros. Ce serait la
première absence de `f9` jamais observée, et elle serait provoquée exprès.

Aucune autre permutation ne prédit la même chose. Prédictions pour l'entrée
neuve, `beam_fx1` :

| Lecture | `f6` | `f8` | `f9` |
|---|---|---|---|
| **favorite** — `f6` Phase, `f8` Size, `f9` Fade | **94** | **100** (inchangé) | **absent** |
| `f6` Fade, `f8` Size, `f9` Phase | **absent** | 100 | **94** |
| `f6` Phase, `f8` Fade, `f9` Size | 94 | **absent** | 100 |

Les trois lectures rivales tombent sur des motifs **disjoints** : la valeur 94 et
l'absence se déplacent ensemble d'un champ à l'autre. Une seule entrée les
sépare toutes les trois.

Le reste de la prédiction, inchangé sur le fond :

- `beam_fx1.f5` = **1** (`Zoom`, énumération du toolkit) — p **0,55** ;
- `beam_fx1.f8` reste à **100** : l'encodeur a basculé en mode `Feature`, donc
  `Size` n'a pas tourné. Si `f8` bouge, c'est que la bascule n'a pas eu lieu et
  le tir est contaminé — c'est le contrôle de la manipulation elle-même ;
- `beam_fx1.effet` **absent** (`SIN WAVE` = 0), `vitesse` = **75**,
  `link_order` = **10**, `speed_source` absent (`Clock`) ;
- `beam_fx2` **octet pour octet** inchangé ;
- `color_fx1` de cette entrée aux défauts couleur, et `beam_fx1` de l'entrée
  précédente aux défauts faisceau — chaque capture contrôle l'autre.

**Une prédiction déjà fausse, avant même la lecture.** J'annonçais les ids
**85 et 86** ; l'opérateur rapporte **86 et 87**. La place 85 était donc déjà
prise avant cette session. C'est une erreur sans conséquence sur la permutation,
mais elle se note : l'état de l'appareil n'était pas celui que je supposais
depuis F7-04, et je ne l'avais pas vérifié avant de prédire.

### FX6-02 / FX6-03 mesurés — la permutation était une **quadruple**, et la vitesse n'était pas où on la lisait — 2026-08-30 — **[validated]**

Projet `WMX EXP format-lab` (`73d06df4-…`), version 1787841428672, 46414 octets,
`sha256 646e11d5cecbeecb0c543ae76efe5fb9717538e730cf7902084ab85efacf182b`,
W1 Mk1 firmware 2.0.18, WTOOLS fermé. Deux entrées neuves, **ids 85 et 86** —
la prédiction d'id était juste, c'est ma lecture du rapport de l'opérateur qui
était fausse : « nom 86 et 87 » désignait les **noms d'écran**, pas les ids.

### Le différentiel le plus propre du registre

Les deux entrées diffèrent par **un seul champ de charge utile**, sur 30 :

```
id 85  beam_fx1 = {bpm_division 3,          link_order 10, f6 94, f8 100, f9 75}
id 86  beam_fx1 = {bpm_division 3, f3 1,    link_order 10, f6 94, f8 100, f9 75}
                                   ^^^^
```

Entre les deux captures l'opérateur n'a touché qu'une chose : le troisième
encodeur du `BEAM FX`, poussé en mode `Feature`, tourné de `Dimmer` à `Zoom`.
Un geste, un champ, une valeur.

### Écran contre fichier, huit valeurs

| Écran (photo) | Valeur | Champ mesuré |
|---|---|---|
| `COLOR FX` · `PHASE` | 37 % | `color_fx1.f6` = **37** |
| `COLOR FX` · `SIZE` | 62 % | `color_fx1.f8` = **62** |
| `COLOR FX` · `SPEED` | 50 % | `color_fx1.f9` = **50** |
| `COLOR FX` · `FADE` | 88 % | `color_fx1.f2` = **88** |
| `BEAM FX` · `PHASE` | 94 % | `beam_fx1.f6` = **94** |
| `BEAM FX` · `SIZE` | inchangé | `beam_fx1.f8` = **100** |
| `BEAM FX` · `SPEED` | 75 % | `beam_fx1.f9` = **75** |
| `BEAM FX` · `FADE` | **0 %** | `beam_fx1.f2` **absent** |
| `BEAM FX` · `FEATURE` | `ZOOM` | `beam_fx1.f3` = **1** |

Neuf lignes, neuf exactes, deux moteurs, aucune ambiguïté de valeur.

> **`f6` = `Phase`, `f8` = `Size`, `f9` = `Speed`, `f2` = `Fade`.** Et
> **`f3` porte le second mode du troisième encodeur** : `Feature` sur le
> faisceau — mesuré ici à `1` = `Zoom` — comme `Fan` sur le mouvement.

Le `FADE 0 %` a fait exactement ce qu'un zéro protobuf doit faire : `f2`
**disparaît** de `beam_fx1`. C'est la première absence de ce champ provoquée
exprès, et elle vaut une valeur.

## La rétractation : `f2` n'a jamais été la vitesse

`f2` = « speed % » était **`correlated`** dans SPEC depuis ACC-04, et c'est faux.
C'est le **fondu**. La vitesse est `f9`, un champ que ce registre comptait parmi
les **non attribués** et que trois sections ont discuté sans jamais le
soupçonner.

**La faute de méthode, nommée.** Toute la campagne FX6 a été posée comme « quelle
propriété tombe sur `f6`, `f8` ou `f9` », en tenant `f2` pour acquis parce qu'il
portait déjà un nom. Ce nom n'avait jamais été mesuré : il venait d'une
cohérence de corpus, et **une cohérence n'est pas une attribution**. La
permutation à trois était une permutation à **quatre**, et le quatrième élément
se cachait derrière une étiquette. C'est la leçon de RAW-01 sous un autre
déguisement : là on avait déduit l'encodage des voisins, ici on a déduit le sens
d'un nom qu'on avait écrit soi-même.

### Cascade — ce qui reposait sur `f2` = vitesse

- **Trois anomalies de corpus s'expliquent d'un coup**, et elles auraient dû
  alerter plus tôt :

  | Anomalie | Sous « `f2` = vitesse » | Sous « `f2` = fondu » |
  |---|---|---|
  | `f2` monte à **200** | une vitesse au-delà des 0–100 du toolkit, jamais expliquée | le manuel donne au `Flick` un fondu **au-delà de 100 %** du temps de pas — c'est le mode, mesuré sans le savoir |
  | `f9` présent **352/352** | un champ mystérieux jamais nul | une **vitesse n'est jamais 0**, sinon l'effet est figé |
  | `f8` absent sur 330 presets Rainbow | une taille par défaut à 0 | `SIZE` grisé sur Rainbow — ce que l'opérateur a lu sur l'écran |

  Le `200` reste **partiellement** inexpliqué : il apparaît 12 fois sur le
  mouvement, où le manuel place le `Flick`, mais aussi 3 fois à 150 et 1 fois à
  200 sur la **couleur**, à qui le manuel n'en donne pas. Noté, pas résolu.

- **ACC-04, journal du 2026-08-25** : « vitesse affichée 1 quand `f2` est
  absent ». Sous la nouvelle lecture, `f2` absent = fondu 0, et le « 1 » de
  l'écran est très probablement la **division BPM** (`bpm_division` = 3 = ×1),
  pas un pourcentage. **[hypothesized]** — c'est une relecture, pas une mesure,
  et elle demande une photo pour être tranchée.
- **ACC-05** avait posé « vitesse 50→200 sur *Insane Colors*, attendu chaser
  nettement plus rapide ». Cette moitié n'a **jamais été mesurée** — seule la
  moitié `f5` a été écrite. Sous la nouvelle lecture elle aurait échoué, et
  l'échec aurait sauvé quatre mois. Une prédiction posée et jamais tirée est une
  dette, pas une réserve.
- **`tools/wpj_generate.py` écrivait le fondu en croyant écrire la vitesse.**
  Les paliers d'énergie posaient `vitesse` = 45 / 110 / 170 sur `f2` : les deux
  paliers hauts **allongeaient le fondu** au lieu d'accélérer l'effet, et
  tombaient dans la plage `Flick`. La clé `vitesse` vise maintenant `f9` — elle
  change de champ, pas de sens, donc aucun appelant ne bouge — et les paliers
  rentrent dans 0–100 (45 / 70 / 95, toujours des réglages, pas des mesures).
- **`wpj_show.py`** bornait `vitesse` à 0–200, une borne qui n'avait de sens que
  pour le fondu. Ramenée à **0–100** : 352 presets distincts, `f9` ne dépasse
  jamais 100 sur aucun moteur.

## L1 : le champ est réfuté, la valeur est confirmée

> **La `Feature` du Beam FX est `f3`, pas `f5`.** `beam_fx1.f5` reste absent sur
> les 352 presets distincts **et** sur les deux entrées neuves : il n'a rien à
> voir avec la Feature, et il reste non attribué côté faisceau.

La valeur, elle, tombe pile : `Zoom` = **1**, l'énumération que `wpj-toolkit`
publie sans emplacement (`0` Dimmer · `1` Zoom · `2` Iris · `3` Pan · `4` Tilt ·
`5` Effect). Le toolkit avait raison sur l'enum, ce registre avait tort sur le
fil. Les autres valeurs restent non mesurées : une seule a été exercée.

**Et `f3` devient régulier.** Le troisième encodeur porte deux modes sur deux
moteurs — `Size | Fan` en mouvement, `Size | Feature` en faisceau — et les deux
seconds modes tombent sur **le même champ**. La couleur n'a pas de second mode
sur cet encodeur, et ne porte **jamais** de `f3` : 352 presets distincts, zéro
occurrence. Le sens de `f3` dépend donc du moteur, comme `f5` avant lui, et le
codec le laisse en clé neutre pour cette raison — un schéma partagé ne peut pas
porter deux noms.

`f3` = `Fan` sur le mouvement reste **[hypothesized]** : le créneau est mesuré,
le manuel nomme `Fan` comme second mode de cet encodeur, le défaut 50 est le
neutre de `FAN` partout ailleurs dans ce format — trois arguments, aucune
mesure. Un tour d'encodeur le fermerait.

## Le tableau de chasse de mes prédictions

| Prédit | Mesuré | |
|---|---|---|
| `f6` = Phase | 37 et 94 | ✅ |
| `f8` = Size | 62, et 100 inchangé | ✅ |
| `f8` apparaît sur `SPARKLE` | apparaît à 62 | ✅ |
| `f9` = Fade, absent à `FADE 0` | `f9` = 75, **présent** ; c'est `f2` qui disparaît | ❌ |
| `beam.f5` = 1 (`Zoom`) | `f5` absent, **`f3` = 1** | ❌ sur le champ, ✅ sur la valeur |
| `beam_fx2` inchangé, défauts d'usine | inchangé | ✅ |
| `beam_fx1.f8` reste à 100 | 100 | ✅ |
| ids 85 et 86 | 85 et 86 | ✅ |

La favorite à **p = 0,80** était **à moitié juste** — et la moitié fausse ne
venait pas d'une rivale mal pesée, elle venait d'une case que je n'avais pas
mise sur la table. Aucune des cinq lignes de mon tableau ne contenait la bonne
réponse. Monter une probabilité à 0,80 sur un espace d'hypothèses incomplet ne
rend pas la prédiction meilleure, ça rend l'erreur plus difficile à voir.

## Ce que ça ferme

Le sous-message FX est **entièrement attribué**, propriété par propriété :

| Écran | Champ | Statut |
|---|---|---|
| `Speed` | `f9` | **validated** (FX6-02/03) |
| — sync `Clock / BPM / Audio` | `f10` | correlated |
| — division BPM | `f1` | correlated |
| `Phase` | `f6` | **validated** |
| `Order` | `f4` | correlated (F4-03) |
| `Size` | `f8` | **validated** |
| `Fade` | `f2` | **validated** — et `> 100` = `Flick` sur le mouvement |
| `Feature` (faisceau) | `f3` | **validated** à une valeur, `Zoom` = 1 |
| `Fan` (mouvement) | `f3` | hypothesized |
| type d'effet | `f7` | device-confirmed (ACC-04) |
| pads couleur / position du mouvement | `f5` | correlated ; **non attribué sur le faisceau** |

Il ne reste rien d'ouvert dans ce sous-message qu'un tour d'encodeur ne ferme :
`f3` sur le mouvement, et `f5` sur le faisceau — s'il porte quoi que ce soit.

**Aucune écriture n'est promue.** Tout ceci est mesuré **en lecture** : le
fichier a été produit par l'appareil, pas par nous. `wpj_show.py` continue de
refuser `phase`, `size` et `fade` à l'écriture — la règle 2 demande un
aller-retour octet-identique **et** une acceptation en aval, et aucun des deux
n'a été fait sur ces champs.

Instantané figé : `corpus/experiments/FX6-02/after-two-captures.wpj` (hash
ci-dessus ; le fichier n'est pas publié, conformément à `LEGAL.md`).
