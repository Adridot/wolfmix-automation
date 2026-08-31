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

## Résultat (2026-08-31) — banc, W1 branché, WTOOLS fermé

Les neuf mesures sont faites, l'opérateur devant l'appareil. Huit conformes,
une fausse — la 6, sur ce que le panneau affiche.

| # | Prédit | Mesuré | Verdict |
|---|---|---|---|
| 1 | lecture non gardée, 2.0.18, série de l'état, `projectChanged` false | exactement cela ; `wolfmixMode` 0 | **conforme** |
| 2 | lecture complète des profils | 3364 lignes pour `fixtureProfileCount` 3364 | **conforme** |
| 3 | refus nommant les deux versions, **aucune trame** | refus nommant 2.0.18 et 0.0.0 ; 0 trame `SET_PRESET`, un seul événement sorti — le `GET_SETTINGS` de la garde elle-même | **conforme** |
| 4 | l'override laisse passer | `SET_MODE` accepté, `wolfmixMode` = 0 | **conforme** |
| 5 | refus local, rien d'envoyé, l'écran USB ne s'ouvre pas | refus nommant `--experimental` et les index 26/39/40/42, exit 2, **aucun événement sorti** — pas même une lecture ; l'opérateur voit HOME, pas d'écran USB | **conforme** |
| 6 | trame émise, mode rapporté 5, **et la page PRESET à l'écran** | trame émise, `wolfmixMode` = 5 — mais l'opérateur lit **HOME** sur le panneau | **fausse sur la moitié écran** |
| 7 | refus local sur 228 | « Preset id must be 0-199 … 200-255 is unprobed and is not sent », exit 2 | **conforme** |
| 8 | abandon avant tout upload, version inchangée, pas de `rollbackFailed` | abandon sur l'écriture d'archive, exit 2, version du projet d'expérience identique avant/après, aucun `rollbackFailed` posé | **conforme** |
| 9 | état final identique à 1 et 2 | `firmwareVer`, `fixtureProfileCount`, `projectCount`, série, `projectChanged` identiques ; profils complets | **conforme** |

### La prédiction fausse : le panneau n'a pas suivi

La mesure 6 prédisait la page PRESET à l'écran avec p=0.8, en sachant que
« le panneau ne suit pas toujours ». Il n'a pas suivi : `wolfmixMode` est
resté **5** de bout en bout — avant les deux refus, après eux — pendant que
l'opérateur lisait **HOME**. C'est SCREEN-01 qui se reproduit, à la lettre :
*le mode rapporté n'est pas l'écran affiché*. La prédiction est notée fausse
telle qu'écrite ; elle n'est pas réécrite.

Ce que ça ne dit pas : on ignore si l'écran a affiché PRESET puis est revenu,
ou s'il n'a jamais bougé — l'opérateur n'a regardé qu'après la séquence. Pour
trancher il faudrait une observation continue, et ça n'a pas d'incidence sur
les gardes mesurées ici.

Ce que ça confirme au passage : le refus de l'index 42 n'a pas ouvert l'écran
USB. L'écran était sur HOME à la fin, ce qu'un `SET_MODE 42` parti sur le lien
n'aurait pas laissé.

### Une seconde prédiction fausse, sur un détail, et ce qu'elle a corrigé

La mesure 8 disait « l'erreur nomme l'archivage ». Elle nommait un chemin —
`…/archive/…​.wpj.part` — et une `PermissionError` brute. Le chemin contenait
le mot, la phrase non. L'échec d'archivage est désormais enveloppé dans
« Pre-deploy archive failed, nothing was uploaded: … », et la mesure a été
refaite avec ce message. Une erreur qu'il faut lire deux fois n'est pas une
erreur fail-closed lisible.

### Ce que la séance n'a pas prouvé

- Le rappel d'un preset **présent** n'a pas été exercé : le projet chargé sur
  le panneau n'est pas celui dont on connaît les ids, et RECALL-03/06 l'ont
  déjà établi. La garde firmware a été montrée sur `SET_PRESET` (mesure 3) et
  l'override sur `SET_MODE` (mesure 4).
- L'upload réel d'un déploiement n'a pas été rejoué : la mesure 8 s'arrête
  volontairement avant, et c'est tout ce qu'elle avait à montrer.
