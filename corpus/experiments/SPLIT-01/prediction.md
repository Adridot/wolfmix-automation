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
