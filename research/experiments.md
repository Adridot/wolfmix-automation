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

## EXP-07..09 — validation du type 165 (ajoutées 2026-08-25)

Voir research/preset-format-165.md §Expériences : type d'un Beam FX
(f1.f7), position d'un seul groupe (f28), couleur statique mono-pad (f31).

## Journal — ACC-01 (2026-08-25) : PREMIÈRE ACCEPTATION COMPLÈTE

Fichier généré par wpjlib+wpj_codec (copie de « rig-a », record 101
réécrit : nom → « WMX TEST ACC-01 », seul record différent, SHA-1 recalculé).
- Import WTOOLS 1.6.3 : accepté, affiché comme projet séparé (pas de
  confusion avec rig-a malgré les octets 20–35 inchangés).
- Stockage wlinkData : octet pour octet IDENTIQUE à notre fichier, sous
  un nouveau nom de fichier <UUID neuf> (UUID attribué par
  WTOOLS ; les octets internes 20–35 ne servent donc pas de clé
  d'identité à l'import).
- Synchro W1 fw 2.0.18 : acceptée, projet ouvert sur l'appareil
  (rapporté par l'utilisateur).
→ Conteneur variante A + SHA-1 + encodage du record 101 :
  **device-confirmed**. Chaîne d'écriture wpjlib/codec : acceptée
  WTOOLS + W1 pour ce périmètre.

## Journal — ACC-02 (2026-08-25) : acceptation structurelle OK, sémantique partielle

Import WTOOLS + synchro W1 : OK. Sur l'appareil : nom du preset 78
appliqué (**f25/nom device-confirmed**), mais Color FX et dimmers
ignorés — le preset garde son masque de contenu f4=17 (bloc beam-only)
et son flag color_fx_actif=[0]. Palette non encore vérifiée.
→ Hypothèse renforcée : f4 (et/ou le flag f8) conditionne les sections
que le W1 lit. Écrire des valeurs dans une section masquée est sans
effet. ACC-03 en deux candidats : a) f4=25 (bit couleur ajouté, flag
laissé à 0) ; b) f4=255 + color_fx_actif=[255].

## Journal — ACC-03 (2026-08-25) : activation couleur non résolue par f4/flag

a (f4=25, flag 0) : valeur de masque illégitime → bug d'affichage UI sur
le W1 (case du preset disparaît au clic) ; pas de Color FX. b (f4=255 +
color_fx_actif=255) : accepté, pas de bug UI, mais Color FX et dimmers
toujours ignorés. → f4=25 hors du vocabulaire ; f17=dimmer affaibli ;
nouveau suspect : 1er varint de f16 = masque de groupes du moteur
couleur (255 sur tous les presets ColorFX usine, 0 sur statiques/beam —
correlated sur le bloc 20-39). ACC-04 : édition en place d'un preset
ColorFX existant (id 33 « Carnival », effet 3→2) — teste le mapping FX
seul, sans la question d'activation.

## Journal — ACC-04 (2026-08-25) : effet FX device-confirmed

Édition en place de « Carnival » (id 33) : f7 3→2. Sur W1 : Chaser de
couleurs constaté, mode audio conservé. → FX f7 (effet)
**device-confirmed** ; chaîne d'édition de presets validée de bout en
bout. Observations UI : vitesse affichée « 1 » quand f2 est absent ;
pads de couleur « désactivés partout » sur ce preset alors que f5=[240,4]
inchangé — relation f5↔UI pads à trancher (ACC-05 : f5 [240,0]→[3,0] sur
« Wipeout », attendu pads 1+2 ; vitesse 50→200 sur « Insane Colors »,
attendu chaser nettement plus rapide).
