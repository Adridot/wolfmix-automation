# EXP-07 — différentiels à une variable sur un projet B (AVANT mesure)

Manipulation : dupliquer un projet B existant (« WMX EXP07 »), copier le .wpj
(état 0), puis trois éditions successives, une sauvegarde et une copie après
chacune. Chaque diff consécutif isole UNE variable (motif MAP-01/etapes).

(a) décaler l'adresse DMX d'une fixture de +1 :
    prédit : f12.f3 de cette fixture +1, et RIEN d'autre que le dérivé —
    f15 (entrées déplacées), f16 (masque), f23 si le nombre de canaux occupés
    change ; aucun autre champ. Rivale : f15/f16 ne sont pas dérivés du patch.
(b) changer la vitesse d'un FX (un moteur, un preset, une valeur lisible à
    l'écran) : prédit : l'octet [0] du tuple 9 octets du slot visé, dans le
    tableau du moteur (beam=f13, color=f5, move=f9) de ce seul preset.
    Rivale : [0] n'est pas la vitesse, ou le tableau n'est pas ce moteur.
(c) renommer un gobo de la palette : prédit : f2 d'UNE entrée de f9 ou f31.
    Le champ touché tranche l'hypothèse « f9 = slots 1-5, f31 = 6-10 ».

## Résultat (2026-08-31) — exécuté sur l'appareil, sur le duplicata

Les trois éditions ont été faites sur le W1 (WTOOLS ne sait ni créer ni
dupliquer un projet — la variante B est un format legacy figé, voir le
registre). Une seule copie finale (`etape3-final.wpj`), trois deltas
attribuables car records disjoints. Contre `exp05-dup.wpj` (état 0) :

- **préfixe octets 40..** : 01 → 04 — trois sauvegardes, trois incréments :
  le compteur de sauvegardes est mesuré côté écriture. **[validated]**
- **(c) renommage gobo** : delta unique, `145[A][0].f3` = l'ancien nom
  suffixé — le champ de RENAME-01, écrit cette fois par l'appareil.
  **[device-confirmed]** Côté B le même nom vit dans `f9[slot].f2` (Rosette).
- **(b) vitesse COLOR FX 50 → 83 sur le preset 1** : `165[0].color_fx1.f9
  (vitesse) = 83` — exactement le champ prédit. MAIS la sauvegarde du preset
  est une **recapture** : le reste du preset est réécrit (positions, gobo_*,
  fx2 re-remplis aux défauts, f27 1000×8 → 0…). Pas un différentiel à une
  variable ; la valeur cible reste attribuable. **[validated]** pour f9.
- **(a) adresse 17 → 18 : NON MESURÉE** — 115 inchangé dans les deux projets
  de l'appareil, versions inchangées ailleurs : l'édition n'a été persistée
  nulle part. À refaire.

## Résultat (a), repris (2026-08-31, `etape4-adresse.wpj`)

Adresse de la 2e lyre 17 → 18 à l'écran, une seule sauvegarde (compteur
4 → 5). Diff contre `etape3-final.wpj` : **exactement trois records** —
- `115` : `f2` 16 → 17 sur cette fixture, unique champ touché ;
- `106` : les 8 entrées de la lyre décalent leur canal absolu `f2` de +1,
  tout le reste identique ;
- `120` : le blob d'en-tête `f4` bouge (dérivé par canal, non décodé).
Prédiction (a) : **validated** — le patch est la source, 106/120 des dérivés,
et rien d'autre ne bouge (contrairement au « save preset », qui recapture).
