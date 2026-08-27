# Matrice de versions locales (relevé 2026-08-27)

| Composant | Version | Source |
|---|---|---|
| WTOOLS | 2.0.2, build 248 | `sq.version` du bundle, installé le 2026-08-14 |
| WTOOLS Beta | **non trouvée** | aucun bundle sur la machine au relevé — voir note |
| Easy View 3 | 3.0.0 (`26.0819.661.293`) | `/Applications/Easy View/`, installé le 2026-08-20 |
| EasyView 2 | 22.805.0.17 | `CFBundleVersion` seul (2024-01-11) |
| EasyViewConnect | aucune version déclarée | Info.plist muet |
| macOS | 26.6.2 (25G83) | `sw_vers` |
| W1 Mk1 firmware | 2.0.18 | `GET_SETTINGS` champ 14, appareil branché |
| wpj-toolkit | commit `2bd0ee3` (2026-08-14) | relevé externe, non revérifié |

Le firmware est lu sur l'appareil, pas cité. **Piège** : le champ 13
(`firmwareVersion`, flottant) vaut 0.0 sur ce firmware — lire le champ 14
(`firmwareVer`, chaîne).

**WTOOLS Beta.** Annoncée en `/Applications/WTOOLS Beta.app`, absente du disque
au relevé (`ls`, `find`, Spotlight, `/Volumes`, Downloads). Les expériences
ACC-* ont tourné sous WTOOLS 1.6.3 ; tout ce qui suit est sous 2.0.2. Une entrée
beta sera ajoutée quand le bundle sera là pour être lu.

## Corpus local (copies figées, hashes dans `corpus/SHA256SUMS`)

Source : `~/Library/Application Support/WTOOLS/wlinkData/`. Les originaux ne
sont jamais modifiés ; les copies sont en lecture seule.

| Fichier | Taille | Date origine | Variante (voir wpj-format-registry.md) |
|---|---|---|---|
| `rig-C1.wpj` | 275 516 | 2025-06-19 | C — protobuf nu, version champ1=6 |
| `rig-B1.wpj` | 276 923 | 2025-06-19 | B — SHA-1 + protobuf, champ1=7 |
| `rig-B2.wpj` | 276 750 | 2025-05-08 | B |
| `rig-B3.wpj` | 276 043 | 2025-05-08 | B |
| `rig-B4.wpj` | 282 886 | 2025-08-23 | B |
| `rig-B5.wpj` | 279 788 | 2025-08-23 | B |
| `rig-a.wpj` | 38 787 | 2025-09-20 | A — SHA-1 + conteneur TLV type 100 |
| `rig-b.wpj` | 40 391 | 2025-09-20 | A |
| `rig-c` (révision de base) | 43 329 | 2025-09-20 | A |
| rig-c.wpj | 39 737 | déposé par l'utilisateur 2026-08-25 — son projet principal | A |
| rig-c-bug.wpj | 44 729 | idem — même UUID que la révision de base ; révision récente **buggée** (voir research/rig-c-bug.md) | A |
| `rig-B?.wm` | 550 310 | 2023-10-16 | conteneur hex ASCII (chiffré ?) |
| `rig-C1.wm` | 551 142 | 2023-10-16 | idem |
| wmx/wmBrands.wmx, wmProfiles.wmx, wmProjects.wmx, wmPersistent.wmx | — | — | conteneur hex ASCII versionné (001–003), payload haute entropie |

Note : les fichiers dont l'UUID commence par des zéros portent des identifiants
dérivés du numéro de série de l'appareil, visible en clair dans l'en-tête —
hypothèse : dumps synchronisés depuis le W1 via WLINK. Ni l'UUID ni les octets
correspondants ne sont reproduits ici (LEGAL.md).
