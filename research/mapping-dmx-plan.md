# MAP-01 — où vit la carte de mapping DMX

Piste L5, reformulée : le MK1 n'a pas de MIDI, mais il a l'écran `Mappings`
(mode 43) et son côté **DMX**. La question n'est plus « fichier, réglage ou
sidecar » — le manuel a tranché.

## Ce qui est déjà acquis

| Fait | Source | Statut |
|---|---|---|
| Le projet contient les mappings | manuel §Projects : *« Group names and mappings »* | **correlated** |
| Les réglages du panneau ne sont **pas** dans le projet | même liste, dernière puce | correlated |
| L'écran existe sur ce MK1, mode 43 | opérateur, 16 ↔ 43 alternent proprement | device-confirmed |
| Record 130 : `f1=9` puis 9 items `f5` — 8 × `f4=20` (`f6` = 0–7) + 1 × `f4=27` (`f6`=8) | `tools/dump.py`, 50/50 fichiers | observed |
| 130 est **octet pour octet identique** sur 50/50, 4 rigs | idem | observed |
| 130 ne suit pas le rig : `rig-c-bug` a un groupe D et garde `8×20 + 1×27` | idem | observed |

Les 9 slots de 130 sont les 9 slots de groupe déjà `device-confirmed` (record
125 : A–H plus un neuvième pour ce qui n'est pas un groupe). `Group Dimmer` est
l'une des cinq catégories de l'écran `Mappings`, et la seule qui soit par
groupe.

**Aucun fichier du corpus n'a jamais eu de mapping créée.** Tout candidat est
donc à sa valeur par défaut sur les 50, ce qui explique l'invariance de 130 sans
rien prouver.

## Prédiction, écrite avant la mesure

| Issue | p |
|---|---|
| **130 bouge**, sur l'item `f6=0` — la carte `Group Dimmer` est là | **0,55** |
| un autre record bouge (106, 110, 111, 160, ou un type neuf) | 0,30 |
| les cinq catégories sont éclatées sur plusieurs records | 0,15 |

Et dans le cas où 130 bouge :

| Forme du changement | p |
|---|---|
| l'item gagne un champ qui porte **7** | 0,55 |
| `f4` passe de `20` à autre chose — `20` était le sentinel « non mappé » | 0,35 |
| autre chose | 0,10 |

`f4=20` et `f4=27` **ne sont pas nommés** et ne le seront pas avant qu'une
écriture les fasse bouger. La coïncidence « 9 slots » est exactement l'argument
qui a menti sur « 125 = neuf catégories » et sur « 161 = trois séquences ».

## Le gate que l'appareil vient de révéler — à vérifier avant tout

`GET_SETTINGS` sur l'unité de l'opérateur, 2026-08-31 : **`wlinkActivated: false`**.

WLINK est un add-on payant (manuel, §WTOOLS : « Purchase add-ons including extra
DMX universes, **WLINK** and 3D Link »), et c'est lui qui porte l'entrée DMX :
le connecteur est décrit comme « 1x 5pin DMX **IN**/OUT XLR connector **with
WLINK** », le réglage `WLINK input mode` a un mode **`DMX IN`** — « DMX input
data will be received via XLR C and **mapped to group dimmers** and DMX output
channels » — et l'écran `DMX Values` annote son mapping d'entrée « WLINK add-on
required ».

Deux lectures, et la première étape du protocole les sépare pour zéro geste
supplémentaire :

| Lecture | Conséquence |
|---|---|
| l'écran `Mappings` **laisse poser** la mapping sans WLINK (config stockée, simplement inerte) | MAP-01 se déroule tel quel |
| l'écran **refuse** le côté DMX sans WLINK (grisé, encodeur mort, catégorie vide) | la carte est inatteignable sur cette unité sans l'add-on — négatif publiable, et L5 s'arrête là faute de matériel |

Noter que « `mapped to group dimmers` » dans la définition même du mode `DMX IN`
corrobore la catégorie `Group Dimmer` comme cible privilégiée — sans rien dire
de l'endroit où la table est rangée.

## Le protocole — un seul geste discriminant

WTOOLS fermée (le port série est exclusif). Aucune écriture sur l'appareil :
lecture, sauvegarde au panneau, téléchargement.

**0 · Repérer le projet.** Noter l'UUID du projet d'expérience, et **ne plus en
changer** de toute la session :

```bash
python3 tools/wolfmix.py projects
```

**1 · La ligne de base.** `pre.wpj` a déjà été téléchargé sans aucun geste
(2026-08-31) ; le diff `pre` → `before` mesurera gratuitement ce qu'une
sauvegarde nue réécrit sur ce projet précis, c'est-à-dire le plancher de bruit.
 Sauvegarder le projet au panneau **sans rien
toucher**, puis :

```bash
python3 tools/wolfmix.py project <UUID> corpus/experiments/MAP-01/before.wpj
```

**2 · Le geste.** Menu principal → `Mappings`. Dans la barre d'outils,
s'assurer d'être du côté **DMX** (pas MIDI).

| Encodeur | Réglage |
|---|---|
| 1er | catégorie → **`Group Dimmer`** |
| 2e | mapping → **le premier groupe** (A) |
| 3e | canal DMX IN → **7** |

**Ne pas utiliser `LEARN`.** Il assigne le prochain message entrant : sans
source DMX branchée rien n'arrive, et l'état obtenu n'est pas celui qu'on croit
avoir posé. Le canal se règle au troisième encodeur, explicitement.

**3 · Sauvegarder le projet. Ne toucher à rien d'autre** — aucun preset, aucune
palette, aucun pad. Puis :

```bash
python3 tools/wolfmix.py project <UUID> corpus/experiments/MAP-01/after.wpj
```

**4 · Lire.**

```bash
python3 tools/wpj_diff.py corpus/experiments/MAP-01/{before,after}.wpj
python3 tools/dump.py corpus/experiments/MAP-01/after.wpj 130
```

## Photos

1. L'écran `Mappings` **avant de sortir**, montrant les trois réglages en même
   temps : catégorie `Group Dimmer`, mapping = groupe A, DMX IN = 7.
2. La barre d'outils, pour figer le fait qu'on était bien côté DMX.
3. La liste des mappings si elle affiche plusieurs lignes — elle dit combien
   d'entrées la catégorie contient, donc combien de slots la table doit avoir.

## Les pièges

- **Deux projets homonymes.** Télécharger `before` et `after` sur le même UUID,
  pas sur le même *nom*. Le nom ne distingue pas deux projets.
- **Le compteur de version (offsets 40–47) est un oracle négatif seulement.**
  S'il n'a pas bougé, rien n'a été écrit. S'il a bougé, ça ne prouve rien.
- **Une sauvegarde nue réécrit des octets vifs** — 115, 155, 161 bougent tout
  seuls. C'est pour ça que l'étape 1 est une sauvegarde à vide : elle absorbe
  cette volatilité dans la ligne de base au lieu de la laisser polluer le diff.
- **Un record qui porte déjà un nom n'est pas un record mesuré.** Si le diff
  tombe dans 155 ou 125, lire la valeur, pas l'étiquette.

## Ce que chaque issue vaut

- **130 bouge sur l'item du groupe A** : la carte est localisée, sa catégorie
  la plus utile est décodée, et un des six records encore traversés en verbatim
  quitte le lot. Un show généré peut déclarer ses propres associations de
  dimmer de groupe.
- **Un autre record bouge** : le diff le nomme directement, et la question
  « quel record » est close en une mesure.
- **Rien ne bouge hors du compteur et des octets vifs connus** : la carte n'est
  **pas** dans le projet, malgré le manuel. Réfutation propre, publiable telle
  quelle, du même calibre que F11-01 — et elle renvoie la piste vers les
  réglages de l'appareil (`GET_SETTINGS`, dont `f15 universeMapping` n'a jamais
  été interprété).

## Session B — conditionnelle, à ne lancer qu'après lecture du diff de A

Seulement si A confirme 130. Repartir de l'état de A, catégorie **`Preset`**
cette fois, un preset quelconque, DMX IN = **9**, sauvegarder, télécharger.
Si le `9` atterrit **aussi** dans 130, les cinq catégories partagent un record
et 130 est *la* carte ; s'il atterrit ailleurs, la carte est éclatée par
catégorie et B vient de trouver le second morceau.
