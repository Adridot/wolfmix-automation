# EXP-05 — réécrire le fichier C sous WTOOLS 2.0.2 (prédiction AVANT mesure)

Manipulation : dupliquer dans WTOOLS le projet `f4a5d15f` (variante C,
champ 1 = 6, sans digest), sous le nom neutre « WMX EXP05 », sauver, copier le
nouveau .wpj de wlinkData ici. L'original n'est jamais touché.

Prédiction (hypothèse « champ 1 = version ») :
- le fichier réécrit porte **champ 1 = 8**, un **digest SHA-1** (octets 0-19),
  et le champ **43** (visé : v8, celle de WTOOLS 2.0.x — comme `848d7dcf`) ;
- le schéma top-level reste identique par ailleurs ; le diff C→v8 EST la
  migration de format.

Lectures rivales :
- champ 1 inchangé (= 6) → champ 1 n'est pas une version de format ;
- champ 1 = 7 → la valeur 8 n'est pas liée à WTOOLS 2.0.x ;
- WTOOLS refuse d'ouvrir le projet → v6 n'est plus migrable, à noter.

## Résultat (2026-08-31) — la rivale n° 3

WTOOLS 2.0.2 beta **refuse d'ouvrir** le projet `f4a5d15f` : erreur « le
projet provient d'une version trop ancienne » (formulation de l'opérateur ;
capture à joindre si possible). **[observed]** v6 n'est plus lisible par
WTOOLS 2.0.x — le chemin de migration 6→8 est fermé sur cette machine.
L'erreur montre que WTOOLS discrimine les projets par version de format, ce
qui **renforce** « champ 1 = version » sans le valider : on ne sait pas encore
que c'est ce champ-là qu'il lit.

## EXP-05bis — migration 7→8 (prédiction AVANT mesure)

Manipulation de repli : dupliquer un projet **v7** (`386fbb63`, champ 1 = 7)
sous « WMX EXP05 », sauver, quitter, copier.

Prédiction : le duplicata est écrit en **champ 1 = 8**, digest présent,
**champ 43** présent (comme `848d7dcf`, seul v8 du corpus) ; le reste du
schéma top-level inchangé. Le diff donne la migration 7→8.

Rivales :
- champ 1 reste 7 → une sauvegarde ne migre pas ; 8 vient d'ailleurs ;
- champ 1 = 8 mais sans f43 → f43 n'est pas lié à la version ;
- refus d'ouvrir → 2.0.2 ne lit pas v7 non plus (peu probable : il liste ces
  projets).

## Résultat EXP-05bis (tentative, 2026-08-31)

- **[observed]** WTOOLS 2.0.2 beta n'offre pas de duplication de projet dans
  son UI ; la duplication a été faite **sur le W1** (projet source : à noter).
- **[observed]** WTOOLS : dialogue `CTRL_STORE_PROJECT_FAILED` /
  `invalid wire_type` — une erreur de parsing **protobuf** au moment de
  ranger le projet ; le W1 affiche de son côté « error reading project ».
- **[observed]** `wlinkData/projects/` : aucun fichier créé ni modifié — le
  store a avorté avant écriture, la bibliothèque locale est intacte.
- **[hypothesized]** le canal projet WTOOLS ↔ W1 transporte du protobuf, et le
  duplicata fabriqué côté appareil produit des octets que le parseur de
  WTOOLS 2.0.2 rejette. Candidats : duplicata corrompu côté W1 ; disposition
  (TLV vs protobuf) inattendue par le parseur ; défaut transitoire du W1 (cf.
  registre, getProfileList tronqué — réparé par redémarrage).
