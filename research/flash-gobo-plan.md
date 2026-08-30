# Remplacer des icônes de gobo dans l'image flash

Mesuré sur le dump Blutter de WTOOLS 2.0.2 (`blutter-out/asm/wolfmix/`), 2026-08-30.

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

## Ce qu'il reste à écrire

Un encodeur, inverse exact de `Library.icon()` : 24×24, 3 octets/pixel
entrelacés, RGB565 LE puis alpha. 1728 octets, **taille fixe**.

Remplacer une icône n'est qu'un `data[ptr-base : ptr-base+1728] = neuf`.
Table, pointeurs, longueur du fichier : inchangés. Diff attendu = N×1728 octets.

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
- `SetFlashDataFromFilepathAsync` affiche « Mise à jour du Wolfmix 1/2 ».
  Deux phases pour un seul fichier choisi : à observer, non expliqué.

## Les phases

| # | Étape | Sortie vérifiable |
|---|---|---|
| 0 | Copier le bundle intact hors du dossier WTOOLS, `sha256sum` des 4 fichiers | 4 empreintes notées |
| 1 | `tools/gobo_write.py` + self-test round-trip | `encode(decode(i)) == brut(i)` pour les 705 icônes |
| 2 | Patch à blanc : 1 icône magenta sur un id libre, sans upload | `cmp -l` donne exactement 1728 octets, tous dans `[ptr-base, +1728[` |
| 3 | Upload réel du flash patché (WLINK coupé, debug WTOOLS SHIFT+CMD+D) | l'icône magenta s'affiche sur le W1 |
| 4 | **Re-upload du flash d'origine** | l'icône d'origine revient — le retour arrière est prouvé |
| 5 | Les vraies icônes des lyres, par lots | — |

L'ordre 3→4 n'est pas négociable : prouver l'annulation sur une icône avant
d'en toucher plusieurs. Tant que la phase 4 n'a pas tourné, le filet est
théorique.

## Le filet, par ordre de gravité

1. Re-upload du flash d'origine (phase 4, la voie normale).
2. WTOOLS *Settings > Factory Reset* — réinstalle le dernier firmware **et**
   son flash (manuel W1 v2.0 p.70).
3. WOLF+SPEED au démarrage → bootloader → WTOOLS, si le W1 ne démarre plus.
4. WOLF+SMOKE → firmware d'usine embarqué, sans PC.

Aucun cas public de bricking n'est imputable à une modification de flash : les
cas rapportés viennent de mises à jour firmware ratées ou de pannes USB.
