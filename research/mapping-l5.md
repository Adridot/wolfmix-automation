# L5 — où vit la carte de mapping DMX (MK1, mode 43)

Objectif : localiser la table de l'écran `Mappings` — fichier de projet,
réglages de l'appareil, sidecar, ou nulle part. Analyse corpus + manuel,
aucune mesure appareil dans cette passe. Prédictions écrites avant MAP-01.

## Ce que le manuel fixe — [src-doc]

- L'écran `Mappings` est une **table fixe** : encodeur 1 = catégorie,
  encodeur 2 = le mapping dans la catégorie, encodeur 3 = le canal DMX IN
  assigné. « A list of available mappings » — on assigne des entrées
  préexistantes, on n'en crée pas. Bouton LEARN pour capturer l'entrée.
- La liste des contenus d'un projet inclut « Group names and **mappings** »
  (ambigu : mappings de groupes ou écran Mappings ?) et exclut explicitement
  les seuls réglages de l'écran **Settings**. Mappings n'est pas l'écran
  Settings.
- L'écran `DMX Values` porte un « DMX input mapping » par canal, **WLINK
  requis** — c'est un autre mécanisme que l'écran Mappings, à ne pas
  confondre.

## Ce que le corpus fixe — [observed]

### Record 130 : la structure, enfin lue

102 octets, identiques sur **50/50** fichiers (5 rigs). Protobuf propre :
`f1 = 9`, puis 9 items `f5` :

| slot | f2 | f4 | f6 | f7 | f8 |
|---|---|---|---|---|---|
| 0–7 | index (0 omis) | **20** | index | 1 | 1 |
| 8 | absent | **27** | 8 | absent | 1 |

> **Rétracté le 2026-08-31 par MAP-01.** `f6` n'est pas un index de slot :
> c'est le **canal DMX IN** de la mapping, en base zéro. Il coïncidait avec le
> rang parce que la carte d'usine est l'identité. Voir
> `research/mapping-dmx-plan.md`, « MAP-01 mesuré ».

Les 9 slots de 125 (8 groupes + hors-groupe), une config par slot jamais
touchée par l'opérateur. Compatible « carte vide par défaut » comme avec
n'importe quelle config par-groupe par défaut. Le corpus ne peut pas trancher.

### Record 161 : état machine, pas une carte

`f1 = 9`, 3 items : `f1` = 21/15/19, `f3` = blob 189–191 o quasi nul,
`f4` ∈ {1, 2}, `f2` présent seulement quand le blob est non nul. Les blobs des
fichiers ACC (2026-08-25) sont **tout à zéro** ; ils se remplissent ensuite
avec l'usage, et le dernier octet est le volatile connu (0xF0/0xB0/0xA0).
Une structure qui croît avec l'usage et dont la queue bouge à chaque session
ressemble à des compteurs/état, pas à une table d'assignations. Candidat
rétrogradé, pas éliminé.

### Aucun type de record inconnu, nulle part

Les 50 fichiers variante A portent exactement les 20 types connus. Compatible
avec les deux lectures : « record optionnel jamais créé » (précédent : 160,
absent de 9 fichiers) et « pas dans le fichier ».

### Sidecars .wmx : chiffrement par blocs, et hors sujet

Enveloppe `VVV.<32 hex>.<payload hex>.<64 hex>`. Mesuré sur les 4 fichiers :

| Fichier | payload | mod 16 | entropie |
|---|---|---|---|
| `wmPersistent` | 2528 o | 0 | 7,93 |
| `wmBrands` | 6784 o | 0 | 7,97 |
| `wmProfiles` | 132064 o | 0 | 8,00 |
| `wmProjects` | 3632 o | 0 | 7,94 |

Toutes les longueurs sont multiples de 16 et l'entropie est au plafond :
**chiffrement par blocs**. Les deux champs hex ne sont un condensat simple ni du
payload ni de sa forme hex — 5 constructions (`sha256`/`md5` du payload, de
l'hex, de `ver.h32.hex`) × 2 champs × 4 fichiers, **zéro correspondance**.

Hors périmètre pour L5, et pas parce que c'est dur : ce sont des **caches
applicatifs** (marques, profils, projets, état WTOOLS), pas du per-projet, et le
manuel place les mappings dans le projet.

### Les cinq gros .wpj ne sont pas chiffrés — c'est une variante de conteneur

`tlv.load` rejette 5 fichiers de ~277 Ko. Ce n'est pas du chiffré : **entropie
1,46**, pleins de zéros, et du protobuf en clair dès l'offset 0x14
(`f2 = "2 Lyres"`, `f5 = "Preset 1"`…). Variante de conteneur B/C, mêmes données
de show sous un autre cadrage. Ne change rien à L5, mais ferme la lecture
« il y a du chiffré dans le corpus ».

## Où ça laisse la piste

| Home | Statut |
|---|---|
| **fichier de projet** | **correlated** — le manuel l'affirme, aucun octet localisé |
| record 130 | `hypothesized` — 9 slots = les 9 slots de groupe, et `Group Dimmer` est la seule catégorie par groupe |
| record 161 | rétrogradé — état machine qui croît avec l'usage |
| sidecars `.wmx` | éliminé — caches applicatifs, pas du per-projet |
| réglages appareil | non éliminé, mais le manuel les exclut du projet ; retombée si MAP-01 réfute |

Le corpus est allé au bout de ce qu'il peut dire : **aucun fichier n'a jamais eu
de mapping créée**, donc tout candidat y est à sa valeur par défaut. La suite est
une mesure à une variable — voir `research/mapping-dmx-plan.md`.

## Le piège

La coïncidence « 9 slots » est exactement la forme d'argument qui a menti sur
« 125 = neuf catégories » et sur « 161 = trois séquences de faisceau ». `f4 = 20`
et `f4 = 27` restent des nombres tant qu'une écriture ne les a pas fait bouger.
