# EXP-06 — la Rosette : un même show dans les deux sérialisations (AVANT mesure)

Manipulation : faire entrer dans WTOOLS, comme projet local, une COPIE d'un
projet variante A entièrement décodé (rig-a) — par import de fichier si WTOOLS
le propose, sinon via la synchro appareil puis duplication en projet local.
Nom neutre : « WMX EXP06 ». Sauver, copier le .wpj résultant ici.

Prédictions :
- le fichier est variante B (v8) et se décode sous la carte L8 (`wpj_bc.py`) ;
- ses profils (f13) == les records 116 de rig-a : hash 16 o, nb canaux,
  timestamp, exacts ;
- son patch (f12) == les records 115 : **f12.f3 = 115.f2 − 1** (base 0 vs
  base 1) — c'est le discriminateur de la base d'adresse ;
- ses noms de presets (f3.f1) == les noms des 165 de rig-a ;
- les tuples FX 9 octets d'un preset d'usine == les six FX du même preset en A,
  ce qui fige l'ordre size/fade et localise (ou exclut) l'id d'effet.

Rivale : l'import normalise/réécrit le contenu — l'alignement par valeurs
tient alors sur les invariants (profils, patch), pas sur les presets.

## Résultat (2026-08-31) — Rosette obtenue par le chemin appareil

`386fbb63` importé sur le W1 (opérateur), redescendu en variante A par
`wolfmix.py` (lecture seule) → `exp06-device.wpj`. Bilan contre les
prédictions :
- fichier variante A standard : ✅ (41 records, digest ok) ;
- profils == 116 (hash/canaux/timestamp) : ✅ champ à champ ;
- **f12.f3 = 115.f2 − 1 : ❌ RÉFUTÉ — égalité exacte, les deux sont en
  base 0** ; et f12.f4 = le groupe (== 115.f4) ;
- noms de presets == 165 : ✅, et l'index du slot B == 165.f19 (id) ;
- tuples FX : ✅ mais pas comme prédit — les 4 tableaux de 81 o sont des
  **banques par effet** (ligne e = paramètres de l'effet e), pas des tuples
  par groupe ; 21/21 moteur×preset. L'ordre size/fade est fixé
  ([3]=fade, [4]=size) et l'id d'effet est l'INDEX de ligne — il restait
  invisible parce qu'on le cherchait comme une valeur.
Détail complet : registre, « EXP-06 — the Rosetta pair, measured ».
