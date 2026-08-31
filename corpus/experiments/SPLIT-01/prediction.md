# SPLIT-01 — le découpage ne change rien d'observable (AVANT mesure)

Phase 2 a réécrit tout le chemin appareil sans changer une seule intention :
`wolfmix.py` est passé de 1 100 lignes à un CLI de 370, et son contenu vit
maintenant dans `wolfmix_protocol.py` (trames, events, domaines),
`wolfmix_device.py` (transport et opérations) et `wolfmix_transaction.py`
(archive, rollback, identité). Les clés publiques du codec sont passées en
anglais. Le lecteur wire de production a remplacé `tlv.py` et `dump.py`.

Tout ça est prouvé hors matériel : `make check` est vert, 18 contrôles, plus
61 tests de bornes qui tiennent sous `python3 -O`. **Ce qui n'est pas prouvé,
c'est qu'aucune de ces réécritures n'a changé un octet qui part sur le lien.**
Un self-check vérifie ce qu'on a pensé à vérifier ; l'appareil vérifie le
reste.

## La prédiction

**Rien d'observable ne change.** Ni sur l'écran, ni sur le DMX, ni dans les
octets rendus par le contrôleur. Formulée ainsi, c'est une prédiction faible —
elle est confirmée par l'inaction. Donc elle est découpée en cinq mesures dont
chacune peut échouer seule, et dont trois ont un point de comparaison **écrit
avant la phase 2**.

| # | Geste | Prédit | Ce qui le réfuterait |
|---|---|---|---|
| 1 | `wolfmix.py settings` | Les mêmes champs qu'au 2026-08-31, `firmwareVer` = `2.0.18` en champ 14, `firmwareVersion` = 0.0 en champ 13 | un champ absent, ou un décodage qui a bougé de nom |
| 2 | `wolfmix.py projects` puis `download` d'un projet | Le fichier redescendu porte un en-tête SHA-1 valide et se relit par `wpjlib` ; deux téléchargements consécutifs donnent le même SHA-256 | un fichier qui ne se parse plus, ou deux téléchargements différents (ce serait LINK-01, pas le découpage) |
| 3 | `wolfmix.py mode color` | Mode rapporté **1**, écran sur COLOR FX — la ligne « poussable » de SCREEN-02 | un mode rapporté différent de 1, ou l'écran inerte |
| 4 | `wolfmix.py mode presets` | Mode rapporté **5**, écran **inchangé** — l'inertie mesurée en SCREEN-02, qui avait réfuté ma prédiction ce jour-là | l'écran qui suit : ce serait une régression de SCREEN-02, pas du découpage |
| 5 | `wolfmix.py preset <id présent>` | La cue jouée change, et `projectChanged` reste **false** | un rappel sans effet, ou un `projectChanged` qui passe true |
| 6 | `wolfmix_experiment.py deploy` d'un projet compilé | Archive préalable écrite avec son manifeste, upload accepté, relecture identique, `rollbackFailed` absent | un déploiement qui réussit **sans** archiver, ou une relecture non identique |

## Les deux endroits où je parie contre moi

- **La garde firmware vit dans `send`**, pas chez les appelants. Si je me suis
  trompé sur l'ensemble `MUTATING_EVENTS`, la mesure 5 ou 6 refusera un event
  qui marchait avant. C'est le risque que le découpage a créé, et c'est
  exactement ce que les mesures 5 et 6 testent.
- **`preset` est borné à 0–199 avant émission.** Si l'id choisi par
  l'opérateur est au-dessus, l'outil refuse *avant* le lien. Ce serait un refus
  correct, pas une régression — mais il faut le distinguer, d'où « id présent »
  dans la mesure 5.

## Ce que je ne prédis pas

L'état de l'écran après la mesure 6. Le déploiement redémarre le contrôleur, et
`FLASH-08` a mesuré qu'un projet déployé n'est pas vivant tant que l'opérateur
ne l'ouvre pas au panneau. Je n'ai aucune base pour dire où l'écran atterrit, et
une case vide vaut mieux qu'un pari déguisé en lecture — la leçon de F7-04.

## Protocole

WTOOLS fermé, W1 branché, DMX débranché pour les mesures 1 à 5. Chaque mesure
se termine par une question explicite à l'opérateur : l'écran du W1 n'est pas
lisible depuis la machine hôte.

Publié avant de brancher. Commité avant la première commande.

---

## Résultat — 2026-08-31, W1 Mk1 (serial withheld), fw 2.0.18, WTOOLS fermé

**Six mesures, six conformes.** Aucune régression observable après le
découpage. Une prédiction était mal formulée — pas fausse, moins précise que
l'outil qu'elle décrivait — et une observation gratuite est arrivée que je ne
peux pas attribuer.

| # | Prédit | Mesuré | |
|---|---|---|---|
| 1 | `firmwareVer` = `2.0.18` en champ 14, `firmwareVersion` = 0.0 en champ 13, tous les champs présents | exactement ça, 22 champs décodés | ✅ |
| 2 | deux téléchargements consécutifs identiques, en-tête SHA-1 valide, relisible | même SHA-256 sur les deux, en-tête valide, 41 records, et le lecteur wire indépendant compte les mêmes | ✅ |
| 3 | mode rapporté 1, écran sur COLOR FX | mode 1, `screenFollows: true`, **opérateur : COLOR FX** | ✅ |
| 4 | mode rapporté 5, écran **inchangé** | mode 5, `screenFollows: false`, **opérateur : toujours COLOR FX** | ✅ |
| 5 | la cue change, `projectChanged` reste false | l'id 4 allume le **5e pad**, `projectChanged` false | ✅ |
| 6 | archive préalable + manifeste, upload accepté, relecture identique, pas de `rollbackFailed` | 7 projets archivés avec 7 manifestes, store `success`, vérification **avant et après le restart**, pas de `rollbackFailed` | ✅ |

### La mesure 4 vaut double

C'est la prédiction que j'avais **ratée** le 2026-08-31 en écrivant SCREEN-02 :
j'avais prédit que `mode presets` déplacerait l'écran, il ne l'a pas fait. Elle
est ici confirmée dans l'autre sens, par un opérateur qui regardait, sur un
écran de départ différent (COLOR FX au lieu de HOME). L'inertie de l'index 5 ne
dépend donc pas de l'écran de départ — ce que SCREEN-02 affirmait déjà, et qui
tient sur un troisième point.

### Ma formulation était plus lâche que l'outil — mesure 6

J'avais écrit « relecture **identique** ». Mesuré : le SHA-256 du fichier
redescendu **diffère** de celui envoyé. Ce n'est pas une réfutation, c'est mon
imprécision :

```
records identiques      : True  (41 records)
préfixe identique       : False
octets du préfixe qui bougent : 40, 41, 42, 43
compteur de version     : 1788174926116 -> 1788199970319
```

Seul le compteur de version bouge, et `verify_project` compare **record par
record**, précisément parce que SPEC §9 et FX-01 ont mesuré qu'une sauvegarde
côté contrôleur n'est pas préservatrice d'octets. L'outil avait raison et la
prédiction aurait dû dire « identique record par record ». Corrigé ici plutôt
que dans la prédiction, qui reste telle qu'elle a été publiée.

### Les trois bornes de la phase 1, revérifiées gratuitement

- `preset 200` → refusé **avant le lien** : « 200-255 is unprobed and is not sent ».
- `mode 26` → refusé, et le refus nomme les 28 modes mesurés et l'indicateur `--experimental`.
- Un event hors liste blanche ne peut pas être encadré du tout.

### L'observation que je ne peux pas attribuer

Le mode rapporté a fait **5 → 0 → 5** entre mes commandes, sans qu'aucun
`SET_MODE` ne parte. L'opérateur, interrogé, n'est pas sûr d'avoir touché le
panneau entre-temps.

Donc : **non attribuable**. Ni « le mode poussé ne persiste pas », ni « c'est
la main de l'opérateur ». Les deux expliquent la trace, rien ne les sépare, et
le dépôt préfère une case vide à une lecture inventée. Le geste qui trancherait
est connu et coûte une minute : pousser un mode, ne toucher à rien, relire
`GET_SETTINGS` deux fois à une minute d'intervalle.

### Une nouvelle qui concerne LOSS-01

Le contrôleur porte **4 projets** aujourd'hui, et le projet que LOSS-01
enregistrait comme disparu le 2026-08-31 **est de retour**, à sa version d'août.
LOSS-01 ne disait rien sur la permanence de la perte, et n'avait proposé aucune
lecture ; ce retour ne l'explique toujours pas. Il ajoute un fait : la perte
n'était pas définitive. `[observed]`
