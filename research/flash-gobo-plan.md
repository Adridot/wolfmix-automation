# Remplacer des icônes de gobo dans l'image flash

Lu dans le dump Blutter de WTOOLS 2.0.2 (`blutter-out/asm/wolfmix/`), puis
**mesuré sur le W1 du banc (firmware 2.0.18, série retenue) le 2026-08-30**.

## Fait, et vérifié sur l'appareil

Une icône dessinée hors du contrôleur s'affiche sur son écran, et l'opération
s'annule. Les cinq points, dans l'ordre où ils ont été mesurés :

| # | Mesure | Résultat |
|---|---|---|
| 1 | Upload d'un `wolfmixFlash.bin` modifié | **accepté**, écrit en entier, aucun refus de signature |
| 2 | Icône 342 remplacée par un carré magenta | pad 7 du groupe 0 magenta après redémarrage |
| 3 | Re-upload du flash d'origine | pad 7 redevenu « Gobo01 » — **réversibilité prouvée** |
| 4 | État de l'appareil après les deux écritures | 3364 profils, 6 projets, 2.0.18, lecture des profils propre |
| 5 | Sauvegardes | les 4 SHA256 du bundle intacts de bout en bout |

La signature ne garde donc pas le flash, ce que la lecture du binaire annonçait.
Le vrai obstacle est ailleurs, et il n'est pas cryptographique — voir plus bas.

## Le verrou n'existe pas

La chaîne « Invalid file - Bad Signature » ne garde pas le flash.

| Chaîne | Où elle vit | Ce qu'elle garde |
|---|---|---|
| `Invalid file - Bad Signature` | `wm_cipher.dart:610`, levée dans `decipherBuffer` (AES-256-CBC + HMAC) | appelée **uniquement** par `wm_fixture_manager.dart` et `wm_project.dart` → profils et projets |
| `buildSignature` | aussi dans `package_info_plus` | champ Flutter standard, sans rapport |
| `File selected is not a Flash file.` | `settings_presenter.dart:2115` | `_substringMatches(nom, ".bin")` — **l'extension, rien d'autre** |

Chemin complet de l'upload flash, sans une seule fonction de crypto :

    onUploadFlashPressedAsync   pickFiles → test ".bin" → uploadFlashAsync
    SetFlashDataFromFilepathAsync   basename, _setLoadingMessage/Progress
    AWmController::setFlashDataAsync   chunkSize, Uint8Array, _slowSetRange

Le fichier part par blocs, tel quel. Aucun en-tête, aucune taille, aucun HMAC vérifiés.

## Le vrai verrou : le bouton, pas la signature

`Upload Flash` n'existe qu'en **mode 2**. Il y a trois modes applicatifs, pas
deux : `0 = Default`, `1 = Debug`, `2 = Full Debug`. Le menu SHIFT+CMD+D
n'offre que les deux premiers — le mode 2 porte un `ModeRequirements`
`_internal = true`, un build interne du fabricant.

Mais `WtoolsMode::fromIdOrDefault` ne revalide **pas** ce prérequis : il ne fait
qu'un `firstWhereOrNull` sur l'id. Le test `_internal` ne vit que dans le menu
qui masque l'entrée. Écrire l'id dans la préférence suffit donc :

```bash
defaults write com.nicolaudiegroup.wtools flutter.wtoolsMode -int 2   # révèle le bouton
defaults write com.nicolaudiegroup.wtools flutter.wtoolsMode -int 0   # état d'usine
```

WTOOLS doit être fermé, et redémarré ensuite. En mode 2, **`Upload Firmware`
est le bouton voisin d'`Upload Flash`** : viser juste.

## L'encodeur existe

`tools/gobo_write.py`, inverse exact de `Library.icon()` : 24×24, 3
octets/pixel entrelacés, RGB565 LE puis alpha. 1728 octets, **taille fixe**.
Il réduit une image carrée quelconque par moyenne de zone et sait lire une
silhouette « blanc sur noir » (`mask:`) — le pipeline complet est dans
[`../docs/gobo-icons.md`](../docs/gobo-icons.md).

Remplacer une icône n'est qu'un `data[ptr-base : ptr-base+1728] = neuf`.
Table, pointeurs, longueur du fichier : inchangés. Diff attendu ≤ N×1728 octets.

Mesure annexe, en passant : les 705 icônes se suivent à 1728 octets pile,
**sauf deux** — les ids 227 et 229 (`DS12GB08`/`DS12GB10`) traînent 72 octets
excédentaires quasi transparents (une ligne de 24 pixels, alpha ≈ 0), un
déchet d'export du fabricant sans effet. Aucune résolution cachée : ce que
Nicolaudie montre de plus beau ailleurs ne vient pas de ce fichier.

## Le piège

- **`Open` (ptr `0x1029417E`) est partagé par 96 entrées.** C'est le seul
  pointeur partagé de la table ; les 704 autres icônes sont en 1:1. L'écraser
  repeint 96 emplacements d'un coup. Ne jamais le viser.
- WTOOLS réécrit `wm-fw-bundle-2.0.18/` à chaque mise à jour. La sauvegarde
  vit **hors** de ce dossier ou elle disparaîtra.
- Le mode WLINK est en lecture seule et fait échouer l'écriture à 17 % ou 99 %
  ([forum t=718](https://forum.wolfmix.com/viewtopic.php?t=718)). Le couper avant.
- Toute icône dont la taille n'est pas 1728 décale tout : les pointeurs sont
  absolus, pas relatifs.
- **L'écran du W1 reste bloqué sur « updating firmware 1/2 writing data 99 % ».**
  Reproduit 2 fois sur 2. Le chemin normal pousse deux fichiers
  (`wolfmixFlash.bin` puis `wolfmixFlash-reset.bin` — d'où la chaîne « Bundle
  does not contain flash reset file. »), alors qu'`Upload Flash` n'en envoie
  qu'un : la machine à états de l'écran ne se referme jamais.
  **Ce n'est pas un plantage.** Pendant tout ce temps l'appareil répond au
  protocole — `getSettings` et `getProjectList` reviennent complets, ce qu'une
  puce en train de graver ne ferait pas. Un redémarrage normal lève l'overlay
  et charge le nouveau flash. Avant de couper : vérifier que les
  `setFlashDataChunks` ont cessé dans le log WTOOLS.
- WTOOLS refuse l'upload si le projet chargé a des modifications non
  enregistrées : « Failed to update firmware — Save project before updating. »
  Sauvegarder d'abord.
- Un PNG RGB écrase l'alpha et rend l'icône opaque : les icônes du fabricant
  sont détourées, nourrir `gobo_write.py` en RGBA quand la forme compte.

## Les phases

| # | Étape | Sortie vérifiable |
|---|---|---|
| 0 | Copier le bundle intact hors du dossier WTOOLS, `sha256sum` des 4 fichiers | 4 empreintes notées |
| 1 | `tools/gobo_write.py` + self-test round-trip | `encode(decode(i)) == brut(i)` pour les 705 icônes |
| 2 | Patch à blanc : 1 icône magenta sur un id libre, sans upload | `cmp -l` donne exactement 1728 octets, tous dans `[ptr-base, +1728[` |
| 3 | Upload réel du flash patché (WLINK coupé, `wtoolsMode=2`) | ✅ magenta sur le pad 7 après redémarrage |
| 4 | **Re-upload du flash d'origine** | ✅ « Gobo01 » revenu — retour arrière prouvé |
| 5 | Les vraies icônes des lyres, par lots | ✅ 11 icônes d'un coup (ids 342–352), silhouettes issues d'images générées, toutes affichées après redémarrage |

Les cinq phases sont exécutées, le 2026-08-30. La suite — renommer les pads et
réordonner la page — n'est **pas** dans le flash : c'est une édition de projet
(records 145 et 111, cas RENAME-01/SORT-01), portée par
`tools/wpj_gobopage.py` et documentée dans `SPEC.md` §3.4.

L'ordre 3→4 n'est pas négociable :
prouver l'annulation sur une icône avant d'en toucher plusieurs. Tant que la
phase 4 n'a pas tourné, le filet est théorique.

Deux préconditions à revérifier avant chaque écriture, apprises en route :
`python3 tools/wolfmix.py profiles` doit répondre proprement (voir la panne du
30/08, réparée au redémarrage), et la machine hôte doit être sur secteur — une
écriture coupée par une extinction est le seul scénario vraiment méchant.

## Le filet, par ordre de gravité

1. Re-upload du flash d'origine (phase 4, la voie normale).
2. WTOOLS *Settings > Factory Reset* — réinstalle le dernier firmware **et**
   son flash (manuel W1 v2.0 p.70).
3. WOLF+SPEED au démarrage → bootloader → WTOOLS, si le W1 ne démarre plus.
4. WOLF+SMOKE → firmware d'usine embarqué, sans PC.

Aucun cas public de bricking n'est imputable à une modification de flash : les
cas rapportés viennent de mises à jour firmware ratées ou de pannes USB.
