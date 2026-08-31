# GUARD-01 — les gardes de la phase 1, sur l'appareil (AVANT mesure)

Les refus ajoutés en phase 1 sont tous prouvés hors matériel (self-checks).
Ce qui n'est pas prouvé, c'est qu'ils refusent **avant** que quoi que ce soit
parte sur le lien, et qu'aucun d'eux ne casse un chemin qui marchait. Banc :
W1 branché, WTOOLS fermé, label d'expérience `format-lab` armé, série retenue.

| # | Manipulation | Prédiction | p |
|---|---|---|---|
| 1 | `wolfmix.py settings` | passe sans rencontrer la garde — c'est une lecture. `firmwareVer` = 2.0.18, série = celle de l'état, `projectChanged` false | 0.9 |
| 2 | `wolfmix.py profiles` | lecture complète : le nombre de lignes égale `fixtureProfileCount` (la troncature du 30/08 était transitoire) | 0.9 |
| 3 | rappel de preset avec `TESTED_FIRMWARE` forcé à `0.0.0` | **refus** : message nommant 2.0.18 et 0.0.0, sortie non nulle, et **aucune trame émise** — le rig ne bouge pas | 0.97 |
| 4 | le même rappel avec `--allow-untested-firmware` | passe, et le rig change de cue | 0.95 |
| 5 | `wolfmix.py mode 42` | refus local nommant `--experimental` ; rien n'est envoyé, l'écran USB **ne s'ouvre pas** | 0.97 |
| 6 | `wolfmix.py mode presets` | trame envoyée, `wolfmixMode` rapporté = 5, et l'écran du W1 affiche la page PRESET. Le panneau ne suit pas toujours (SCREEN-01) : c'est le point le plus fragile | 0.8 |
| 7 | `wolfmix.py preset 228` | refus local : 228 > 199, rien n'est envoyé | 0.99 |
| 8 | `deploy` sur une **copie** de l'état dont `archive/` est en lecture seule et à qui il manque une paire | **abandon avant tout upload** : l'erreur nomme l'archivage, la version du projet d'expérience sur le contrôleur est inchangée, et aucun `rollbackFailed` n'est posé (rien n'avait été touché) | 0.9 |
| 9 | `settings` et `profiles` à la fin | identiques à 1 et 2 — `firmwareVer`, `fixtureProfileCount`, `projectCount` inchangés | 0.95 |

Rivales que ces mesures tuent :

- « la garde firmware s'applique aussi aux lectures » → 1 et 2 échoueraient ;
- « le refus arrive après l'envoi » → 3, 5 et 7 changeraient l'écran ou le rig ;
- « fail-closed n'empêche que le journal, pas l'upload » → en 8 la version du
  projet d'expérience bougerait.

Le seul état durablement modifié par la séance est la cue vive (mesure 4), et
elle est restaurée en rappelant le preset d'origine ou en rechargeant le projet
sur le panneau.
