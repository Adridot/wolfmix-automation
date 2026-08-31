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

---

# MAP-01 mesuré — 2026-08-31 — la carte est dans le fichier, record 130

## Les trois états

| Fichier | version | État au panneau | 130 |
|---|---|---|---|
| `pre.wpj` | …390 | aucune mapping touchée | 102 o, l'ordre d'usine |
| `before.wpj` | …391 | groupe A → **CH1** (posé par accident en vérifiant l'encodeur) | 102 o, **items permutés d'un cran**, contenu inchangé |
| `after.wpj` | …392 | groupe A → **CH7** | **104 o**, `f6` du dernier item : absent → **6** |

`before` → `after` est un différentiel à variable unique : même groupe, seul le
canal change. **Record 130 est le seul record dont la charge utile diffère** ;
tout le reste du fichier est identique, y compris 115, 155 et 161.

## Ce que l'appareil a écrit

Le dernier item passe de 6 à 8 octets par insertion de deux octets, `30 06` —
tag du champ 6 en varint, valeur 6 :

```
before  2a 06  2014        3801 4001     f4=20,         f7=1, f8=1
after   2a 08  2014 3006   3801 4001     f4=20, f6=6,   f7=1, f8=1
```

> **`130.f6` est le canal DMX IN de la mapping, en base zéro.**
> CH1 → `f6` absent (= 0), CH7 → `f6` = 6. **[device-confirmed]**

## Ce que ça explique rétroactivement

L'ordre d'usine de 130 est la **carte identité** : l'item de rang *i* porte
`f6 = i`, c'est-à-dire le canal *i+1*. C'est pour ça que 130 était octet pour
octet identique sur 51 fichiers — aucun opérateur n'avait jamais changé une
mapping, donc tous portaient la même carte par défaut.

Et c'est pour ça que poser **CH1 sur le groupe A n'a rien écrit** : le groupe A
était déjà sur CH1. Le modèle prédit les trois états, y compris celui qui n'avait
pas de sens quand on l'a mesuré.

## Rétractation — `f6` n'est pas un index de slot

`research/mapping-l5.md` lisait les 9 items comme « les 9 slots de groupe », avec
`f6 = index`. **Faux.** `f6` est le canal, et il **coïncidait** avec le rang
parce que la carte par défaut est l'identité. La coïncidence « 9 slots » que la
note signalait comme suspecte l'était bien — mais elle était fausse d'une façon
qu'on n'avait pas prévue : ce n'était pas le *compte* qui mentait, c'était le
*champ*.

Le piège n° 9 du dépôt, une fois de plus : `f6` portait déjà un nom, « index »,
posé par lecture et jamais par mesure.

## Ce qui n'est toujours pas mesuré

`f2`, `f4`, `f7`, `f8` n'ont **pas** bougé et n'ont donc **pas** de nom. Les
lectures qui tiennent, non nommées et non écrites :

| Champ | Domaine observé | Lecture candidate, **non mesurée** |
|---|---|---|
| `f2` | 0–7, absent sur l'item `f4=27` | l'instance visée dans la catégorie |
| `f4` | **20** sur 8 items, **27** sur 1 | la catégorie / la cible de la mapping |
| `f7` | 1, absent sur `f4=27` | — |
| `f8` | 1 partout | — |

## Un second [observed] sans lecture

Toucher une mapping **déplace son item en fin de liste** : le `pre` → `before`
est une rotation pure, multiset identique, ordre des records du fichier
inchangé. Mécanisme non nommé.

## MAP-02 — la prédiction, écrite avant la mesure

Deux sous-étapes, deux sauvegardes, un seul aller au panneau. Chaque diff reste
à variable unique.

**A · `Group Dimmer` → groupe B → CH20.**

| Issue | p |
|---|---|
| l'item qui porte `f2 = 1` prend `f6 = 19` | **0,75** |
| un autre item prend `f6 = 19` — alors `f2` n'est pas la clé | 0,20 |
| autre chose | 0,05 |
| *et*, indépendamment : l'item touché part en fin de liste | 0,60 |

**B · catégorie `Preset` → un preset → CH30.**

| Issue | p |
|---|---|
| un item de **130** prend `f6 = 29` — les catégories partagent le record | **0,50** |
| un **autre record** bouge — la carte est éclatée par catégorie | 0,40 |
| rien ne bouge — la catégorie `Preset` n'est pas stockée | 0,10 |

---

# MAP-02 mesuré — 2026-08-31 — la carte se lit en entier

Deux sauvegardes (392 → 394), l'état intermédiaire non récupérable ; les deux
changements portent des valeurs distinctes (19 et 29), donc le diff reste
lisible. **Record 130 est encore le seul record dont la charge utile bouge**,
+10 octets, 9 → 10 entrées.

| Geste au panneau | Écrit dans 130 |
|---|---|
| `Group Dimmer` → groupe **B** → **CH20** | l'entrée `f2 = 1` : `f6` 1 → **19** |
| `Preset` → un preset → **CH30** | **une entrée neuve** : `f4 = 70`, `f6 = 29`, `f7 = 1`, `f8 = 1` |
| — | `f1` : 9 → **10** |

```
groupe B   2a 0a  1001 2014 3013 3801 4001      f2=1, f4=20, f6=19, f7=1, f8=1
preset     2a 08       2046 301d 3801 4001            f4=70, f6=29, f7=1, f8=1
```

## Ce qui est nommé, et par quelle mesure

| Champ | Lecture | Statut | Ce qui l'établit |
|---|---|---|---|
| `f6` | **canal DMX IN, base zéro** | **device-confirmed** | trois écritures indépendantes : CH7→6, CH20→19, CH30→29 |
| `f4` | **la cible** : `20` = dimmer de groupe, `70` = preset | **device-confirmed** | `70` apparaît exactement quand l'opérateur choisit la catégorie `Preset` |
| `f4 = 27` | **MAIN** | correlated | l'écran liste A–H sur 1–8 puis `MAIN` sur **9**, et l'entrée `f4=27` porte `f6 = 8` |
| `f2` | **l'instance dans la cible** — l'index de groupe pour `f4 = 20` | **device-confirmed** | mapper le **groupe B** a modifié l'entrée `f2 = 1`, qui était en **position 0** : la clé est `f2`, pas le rang |
| `f1` | **le nombre d'entrées** | **device-confirmed** | 9 → 10 en suivant l'ajout |
| `f7`, `f8` | — | — | n'ont jamais bougé, pas de nom |

**La table est appendable.** Les 9 entrées d'usine sont la carte identité —
A–H sur 1–8, MAIN sur 9 — confirmée à l'écran par l'opérateur. Une catégorie
non mappée n'a **pas** d'entrée ; en mapper une en ajoute une. C'est l'explication
complète de l'invariance sur 51 fichiers.

**Les catégories partagent le record.** `Preset` et `Group Dimmer` écrivent
toutes deux dans 130, distinguées par `f4`. La carte n'est pas éclatée.

## Prédictions — le tableau de chasse

| Prédit | | |
|---|---|---|
| l'entrée `f2 = 1` prend `f6 = 19` — **p 0,75** | ✅ | et ça nomme `f2` |
| la mapping `Preset` atterrit dans **130** — **p 0,50** | ✅ | `f4 = 70`, entrée neuve |
| l'entrée touchée part en fin de liste — **p 0,60** | ❌ | le groupe B est resté en position 0 |

**La rotation de MAP-01 reste inexpliquée, et elle a maintenant un
contre-exemple.** Elle est `[observed]` et sans lecture : ce n'est pas
« l'entrée touchée passe en dernier ». Un writer doit donc traiter l'ordre des
entrées comme non significatif et ne jamais s'y fier — `f2` + `f4` sont la clé.

## Ce que L5 rend possible, et ce qui manque encore

Un show généré peut déclarer ses mappings de dimmer de groupe et de preset :
`f2`, `f4`, `f6` et `f1` sont mesurés, et `f7`/`f8` se recopient verbatim depuis
une entrée existante. Restent non mesurées : les catégories `Preset Page`,
`Flash` et `General` (leurs valeurs de `f4`), et l'instance `f2` d'un preset —
l'opérateur n'a pas dit lequel il avait choisi, et l'entrée porte `f2` absent.

---

# Vérifications sans matériel — 2026-08-31

Sept contrôles passés avant d'envisager un writer. Aucun ne demande l'appareil.

| # | Contrôle | Résultat |
|---|---|---|
| A | la carte d'usine sur tous les fichiers antérieurs | **50/50** portent exactement A–H → 1–8 et MAIN → 9, **zéro écart** |
| B | `130.f4` est-il l'énumération des features (`110.f4`) ? | **non** — `70` est hors du domaine des features, qui plafonne à **33**. Le chevauchement de 20 et 27 est fortuit |
| C | la carte existe-t-elle dans la variante de conteneur plate ? | **aucune trace** de la signature dans les 6 fichiers non-TLV — hors périmètre du writer |
| D | quels records bougent sur toute la chaîne ? | `pre→before→after→map02` : **130 et lui seul**, aux trois transitions |
| E | contrôle négatif de `carte_dmx_130` | fausser `f1` de 10 à 9 est rejeté ; l'identité mord |
| F | décodage dans le codec | round-trip **octet-identique sur 54 fichiers** — les champs non nommés `f7`/`f8` survivent |
| G | relecture de la carte par canal | **une collision** (voir ci-dessous) |

## B, en détail — le piège évité

`130.f4 = 20` et `f4 = 27` existent tous les deux dans le domaine de `110.f4`,
la feature d'un canal. La lecture tentante — « c'est la même énumération, donc
20 porte déjà un nom ailleurs » — est **réfutée par `70`** : les features
observées vont de 1 à 33 sur tout le corpus, et 70 n'y est pas. `130.f4` est une
énumération distincte. C'est exactement le piège n° 9 pris dans l'autre sens :
un nombre déjà nommé ailleurs n'est pas le même champ.

## G — l'appareil autorise deux entrées sur le même canal

Relue par canal, la table de `map02` donne :

```
CH3 C · CH4 D · CH5 E · CH6 F · CH7 G + A · CH8 H · CH9 MAIN · CH20 B · CH30 preset
```

Le groupe **A** a été mis sur CH7, or **G y était déjà** par la carte d'usine.
L'appareil n'a ni refusé, ni déplacé, ni vidé l'entrée de G : **les deux
coexistent sur le canal 7**. `[observed]`

Conséquences : aucune contrainte d'unicité n'est imposée par le firmware, donc
un writer n'a pas à en imposer une — mais il doit pouvoir la signaler, parce
qu'une collision est presque toujours une erreur d'intention. Et sur l'appareil
de l'opérateur, **une valeur reçue sur le canal 7 pilote aujourd'hui A et G
ensemble**.

## Ce que le writer peut écrire, et ce qu'il ne doit pas

| Écrivable | Interdit |
|---|---|
| `f6`, le canal, sur une entrée existante | inventer une valeur de `f4` non mesurée (`Preset Page`, `Flash`, `General`) |
| une entrée neuve `f4 = 20` ou `f4 = 70`, `f7`/`f8` recopiés verbatim | supposer que le rang porte du sens |
| `f1`, tenu égal au nombre d'entrées | supposer qu'un canal est unique |

## Le discriminateur qui reste, et il est à un geste

La rotation de MAP-01 est le seul `[observed]` sans lecture, et elle a un
contre-exemple. Une hypothèse la sépare proprement : **une écriture qui ne change
rien réinsère l'entrée en fin de liste.** Le groupe A avait été « posé » sur son
canal d'usine (no-op) et a migré ; le groupe B a réellement changé de valeur et
n'a pas bougé.

Test : `Group Dimmer` → **groupe C** → **CH3**, c'est-à-dire son canal d'usine.
Sauvegarder, télécharger.

| Issue | p |
|---|---|
| l'entrée de C part en fin de liste, charge utile inchangée par ailleurs | **0,55** |
| rien ne bouge du tout | 0,30 |
| autre chose | 0,15 |

Ça ne bloque pas le writer — l'ordre est déjà réputé non significatif — mais ça
ferme le dernier fait non lu du record.
