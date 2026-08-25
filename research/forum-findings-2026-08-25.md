# Forum Wolfmix — relevé du 2026-08-25 (lecture seule)

Contexte : W1 Mk1 fw 2.0.18, WTOOLS 1.6.3. Symptôme utilisateur : après
ajout de lasers, seules les lyres à l'adresse 1 s'allument ; autres lyres
et pars en blackout.

## Threads pertinents

1. **Changelog officiel 2.0.x** — viewtopic.php?t=1055 (staff, 2025-05-08)
   - 2.0.18 : « Fix issue with default channel values sometimes not being
     saved correctly » (valeurs par défaut de canaux → 0/blackout).
   - 2.0.16 : corruption bibliothèque fixtures à l'import USB.
   - 2.0.14 : corruption preset/Live Edit en dernière position ; corruption
     données fixtures à la suppression (projets >180 fixtures).
   - 2.0.8 : projet dupliqué lors de la synchro WTOOLS.
   - 2.0.7 : shutter bloqué fermé sur certaines fixtures.
   - 2.0.4 : corruption critique de projet (2.0.0→2.0.3 irrécupérables) ;
     perte des assignations d'univers au redémarrage.
2. **V2 Fixture Issue** — t=1059 (2025-05) — **le plus proche du symptôme** :
   après ajout de certaines fixtures, canal 1 (dimmer) de la première
   fixture patchée forcé à 0. Staff : survient en **patchant plusieurs
   fixtures d'un coup**, seulement avec certains profils. Remède validé :
   supprimer la fixture touchée et re-patcher seule / profil sain.
3. **FW 2.0 Bugs** — t=1112 : migration 1.2.6→2.0.x, blackout partiel.
   Réponse officielle : **supprimer les fixtures du Fixture Setup et
   re-patcher à l'identique** (mêmes adresses/modes/groupes, presets
   conservés) ; profil corrigé via WTOOLS > Fixtures > Cloud > Sync.
4. **Firmware 2.0.5 errors** — t=1164 : lumières éteintes dès l'ajout
   d'une fixture (shutter forcé à 0) ; corrigé en 2.0.7. Le preset OPEN
   du canal Shutter&Strobe doit être « Default » dans le profil.
5. **Fixtures not responding correctly** — t=1284 (2025-10) : fixture
   adresse 001 muette, presets dupliqués. Staff : mémoire du W1 pas 100 %
   fiable ; procédure : W1 HOME>SETUP>PROJECT>SAVE puis WTOOLS>Projects>
   BACKUP ; en cas de corruption, **recharger le backup = reset sans perte**.
6. **Blackout issues** — t=1280 : un état blackout peut être mémorisé DANS
   un preset via « Save Flash FX in Presets » → désactiver l'option.
7. **Output goes black randomly** — t=1361 : fixtures ignorant les presets,
   résolu en supprimant/re-créant la fixture (corruption de patch).
8. **WTOOLS and 2.0.4 FW issues** — t=1150 : backup/restore erratique ;
   WTOOLS ≥1.6.1 requis ; alimentation USB insuffisante → hub alimenté.
9. **Feedback FW 2.0.4** — t=1090 : canaux DMX jamais émis (toujours 0)
   sur certaines fixtures d'un projet migré ; OK dans un projet neuf.
10. **.wpj Mac↔Windows** — t=1246 : le .wpj contient tout (fixtures,
    adresses, groupes, presets), indépendant de l'OS. Circuit officiel de
    transfert : W1 SAVE → WTOOLS BACKUP → cloud.nicolaudiegroup.com.

## Synthèse pour le bug rig-c

- Pattern dominant 2.0.x : **ajouter des fixtures à un projet existant
  corrompt le patch** — canaux dimmer/shutter émis en permanence à 0 pour
  certaines fixtures (t=1059, t=1164, t=1090). « Seules les fixtures
  adresse 1 répondent » colle avec le canal 1 forcé à 0 (t=1059) plutôt
  qu'un vrai problème d'adressage. Le déclencheur documenté : **patcher
  plusieurs fixtures d'un coup** — cohérent avec l'ajout des lasers.
- Remède récurrent validé par le support : supprimer les fixtures
  touchées et re-patcher à l'identique (presets conservés).
- Filet officiel : backup W1+WTOOLS puis rechargement du projet.
- À vérifier aussi : option « Save Flash FX in Presets » ; alimentation
  USB pendant les synchros.

Cible pour l'analyse binaire : chercher dans rig-c-bug.wpj des
valeurs par défaut de canaux (dimmer/shutter) à 0 sur les fixtures
ajoutées/touchées, plutôt qu'une corruption d'adresses.
