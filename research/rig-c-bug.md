# Diagnostic — blackout du projet « rig-c » (2026-08-25)

Symptôme (matériel réel, fw 2.0.18) : depuis l'ajout des lasers, seules
les lyres à l'adresse DMX 1 s'allument ; autres lyres et pars en blackout.

## Résultat

**Cause la plus plausible : le record TLV type 120 de rig-c-bug.wpj
a été vidé pour toutes les fixtures sauf la première (la lyre à DMX 1).**
251 entrées vides (`2a 00`) sur 258 ; seuls les canaux internes de la
fixture idx 0 conservent des valeurs. Dans les révisions saines (f2737ec3
et rig-c, shas de record identiques), la table est remplie à 73–78 %
avec des blocs par fixture ({1:240}, {1:255, 4:1}×7…), et les deux
fichiers de contrôle (« rig-a », cd21) sont remplis à ~90 %.
Offsets : bug @0x01811 (575 o) vs f2737 @0x010c9 (1199 o).

Si le type 120 porte les niveaux par canal (défaut/statique — dimmer,
shutter…), cet effacement reproduit exactement le symptôme. Statuts :
effacement **observed** ; causalité **hypothesized** (à valider).

Mécanisme : une entrée vidée `2a 00` (message protobuf de longueur 0) se
relit champ par champ comme **0** — exactement le « default channel
values saved to 0 » du forum, en polarité inverse (ici la première
fixture survit, tout le reste est à 0). Contre-vérifications : le type
106 n'a AUCUNE entrée vide dans les deux révisions et les 48 canaux
lasers y ont des défauts sains (255…) ; le type 111 est sain ; dans les
révisions saines les pars ont bien `{1:255, 4:1}` ×7 (dimmer 255) là où
le bug lit 0. Le record 120 de rig-c et f2737ec3 est sha-identique
(07982a6d…), ce qui fait de f2737ec3 un donneur fiable.

Corrélation forum (research/forum-findings-2026-08-25.md) : famille de
bugs 2.0.x documentée — l'ajout de plusieurs fixtures d'un coup force à 0
des valeurs par défaut de canaux (dimmer/shutter), la 2.0.18 corrigeait
justement « default channel values sometimes not being saved correctly ».
Déclencheur cohérent : l'extension de la table (215→258 entrées) lors de
l'ajout du LASERBAR 32 canaux a vraisemblablement réécrit la table en
perdant les valeurs.

Anomalies secondaires (peu plausibles comme cause) : 102.f9 80→75
(présent aussi dans des fichiers sains) ; multi-patch ×6 du LASERBAR sur
idx 21 (motif légitime, vu ailleurs) ; 2 entrées de patch vides
(placeholder présent aussi dans les révisions saines).

**Aucune collision d'adresses DMX réelle** : le patch est propre, dans les
deux révisions.

> **Correction 2026-08-26.** Les adresses citées ici à l'origine (« lyres 0–39
> et 121–140, pars 40–119, lasers 141–200 ») venaient de `105.f4`, qui n'est
> **pas** une adresse DMX mais un offset dans le record 106 — voir le registre,
> « The record 105 contradiction ». Les vraies adresses sont dans `115.f2` :
> lyres 0–95, pars 99–198, le reste plus haut. La conclusion tient : l'identité
> `patch_disjoint` de `tools/wpj_identities.py` vérifie sur 25/25 fichiers que
> les fenêtres DMX ne se recouvrent pas, `rig-c-bug` compris.

## Cartographie TLV établie au passage (variante A)

| Type | Sémantique | Statut |
|---|---|---|
| 101 | nom projet | correlated |
| 102 | réglages globaux 16 o (f9 = % global 72–80) | hypothesized |
| **105** | par entrée {f1 id profil, f4 offset dans 106, f5 index fixture, f6 catégorie (0 beam, 1 par, 2/3 laser, 8 fumée), f7 nb d'entrées de 106}. **f4 n'est pas une adresse DMX** (rétracté, voir le registre) ; l'adresse est `115.f2` | **correlated** (pavage exact de 106 sur 25/25) |
| 106 | 1 entrée par canal patché | correlated (comptage exact ×2) |
| 110 | 1 entrée par canal de profil | correlated (comptage exact ×2) |
| 111 | plages de valeurs par canal (min/max/id fonction) | hypothesized |
| 115 | table des fixtures logiques (offset buffer, index profil, ordre) | correlated |
| 116 | **catalogue profils fixtures** : f2 nb canaux, f8 nom UTF-8, f9 hash 16 o, f11 timestamp | correlated (noms lisibles : « Lyre ZQ02244 », « LASERBAR 6x400RGB J »…) |
| **120** | valeurs par canal interne (niveaux défaut/statique) | hypothesized — **record en cause** |
| 125 | 9 groupes : nom + bitmask des profils membres | correlated |
| 130 | constant 5/5 (défauts usine ?) | observed |
| 135 | palette ColorFX | correlated (wpj-toolkit) |
| 140 ×8 | pages de pads couleur statique (20/page) | correlated (voir preset-format-165.md) |
| 145 ×8 | pages de boutons à glyphe | hypothesized |
| 150 ×8 | positions pan/tilt 16 bits nommées (« <nom du groupe A> »…) | correlated |
| 160 | macros/boutons statiques nommés (« Prism », « Co2 On »…) | correlated |
| 151, 155, 161 | inconnus | observed |
| 165 | conteneur presets (83 éléments) | correlated (wpj-toolkit) |

Scripts : tools/wpj_wire.py (qui a remplacé tlv.py et dump.py).

## Voie de réparation (non exécutée — attend les prérequis)

1. Valider d'abord EXP-04 (round-trip) et la sémantique de 120 par
   expérience différentielle minimale dans WTOOLS (changer UNE valeur par
   défaut d'un canal d'une fixture → le diff doit toucher le type 120).
2. Alors seulement : reconstruire une COPIE de rig-c-bug avec le
   record 120 regonflé depuis f2737ec3 (+ extension pour les 43 nouveaux
   canaux), longueurs TLV et SHA-1 recalculés, octets inconnus préservés.
3. Acceptation WTOOLS (le fichier s'ouvre, patch intact), puis test
   matériel par l'utilisateur, DMX OUT débranché d'abord.
4. Contre-épreuve si utile : injecter le 120 vide dans une copie de
   f2737ec3 et vérifier que le blackout apparaît (sur banc, jamais en show).

Alternative sans writer (validée par le support sur des cas voisins) :
supprimer les fixtures touchées dans le Fixture Setup et re-patcher à
l'identique (presets conservés), ou recharger un backup sain.
