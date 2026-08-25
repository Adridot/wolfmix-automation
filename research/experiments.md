# Expériences différentielles — plan et journal

Protocole commun (sans risque, logiciel uniquement, W1 jamais connecté) :
1. Dans WTOOLS 1.6.3, dupliquer un projet existant (jamais l'original).
2. Modifier **un seul** paramètre, fermer/sauver.
3. Copier le nouveau .wpj depuis `wlinkData/projects/`, hasher, figer dans
   `corpus/experiments/EXP-NN/`.
4. `tools/wpj_diff.py avant après` → localiser les octets changés.
5. Consigner ici : manipulation exacte, diff, conclusion, statut atteint.

Chaque expérience valide au plus un champ. Résultat ambigu = candidats
listés, pas de choix.

## EXP-01 — Renommage du projet
Dupliquer un projet B, changer 1 caractère du nom.
Attendu : seul le champ 2 change (longueur ou contenu) + digest SHA-1
recalculé. Valide : champ 2 = nom, et la règle du digest en écriture.

## EXP-02 — Renommage d'un preset
Renommer « Preset 5 » (vierge) d'un projet dupliqué.
Attendu : un seul sous-message champ 3 change, dans son champ 1.
Valide : ordre des presets dans le fichier ↔ page/slot UI (candidats :
index linéaire `(page-1)*20 + slot-1` comme wpj-toolkit, ou autre).

## EXP-03 — Un paramètre FX
Sur un preset, changer uniquement Color FX speed (ex. 50 % → 51 %).
Attendu : 1 octet dans le sous-message preset. Valide : emplacement et
échelle du champ speed (0–100 direct ? 0–255 ?).

## EXP-04 — Round-trip nul (fondation de toute écriture)
Ouvrir un projet dans WTOOLS, sauver sans rien toucher, comparer.
Attendu inconnu : identique octet à octet, ou réordonnancement/timestamps.
Détermine si « ouvrir+sauver » est déjà non déterministe — préalable
obligatoire à la règle « round-trip octet-identique » du writer.

## EXP-05 — Version 6 vs 7
Prendre f4a5d15f (variante C, champ1=6, sans digest), l'ouvrir dans
WTOOLS 1.6.3, sauver sous un nouveau nom.
Attendu : si WTOOLS réécrit en champ1=7 + SHA-1, l'hypothèse « champ 1 =
version, 7 = digest introduit » passe à validated. Diff C→B donne en
bonus la migration complète du format.

## Journal

_(vide — aucune expérience exécutée)_
