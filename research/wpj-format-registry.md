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

## Type 155 — 4 × 128 byte arrays, likely the DMX patch map — **[observed]**

`field 1` = 4, then four `field 5` items. Each item carries `f1 = 8`,
`f2` ∈ {1, 2}, `f3` ∈ {2, 4}, and `f4` = a **128-byte array**. 4 × 128 = 512,
one DMX universe. The first item's array reads `00×9, 01×8, 02×8, 03×8 …`,
i.e. a fixture index per channel.

In FX-03 the first item's array grew to **129 bytes** with a `01` prepended and
its `f3` went 4 → 16. Not attributable — see the confound above.

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

**Open on `field 7`**: the multiplier list is FREEZE, 0.5×, 2×, 4×, 8×. A value
of 2 for "2×" fits both a list index (0,1,2,3,4) and the literal multiplier.
Setting **4×** discriminates: index would write 3, literal would write 4.

**Open on `field 8`**: one field appeared for one exclusion, but six effects can
each exclude groups. Either `field 8` is STROBE's own mask and the other five
live in their own fields, or it is shared. Excluding **A + C** from STROBE
(expect 5 if bit-per-group) then moving the exclusion to another effect
separates the two readings.

**Refuted**: type 115 `field 6` is **not** the SPEED multiplier. The multiplier
changed twice across these saves and record 115 did not move at all. What set
it to 4 during FX-02 is still unknown.

## Prefix offset 40 = save counter — **[device-confirmed]**

The byte at absolute offset **40** increments by exactly one per controller-side
save: `5f → 60` (one save), `60 → 61`, `61 → 62`, then `62 → 66` across four
consecutive saves. Offset 50 moved once, during the first save only, and is
something else.

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
