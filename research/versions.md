# Matrice de versions locales (relevé **2026-08-27**)

Relevé refait sur la machine et **sur l'appareil connecté**, pas recopié. Chaque
ligne porte la commande qui l'a produite ; le relevé précédent (2026-08-25)
était faux sur trois lignes, WTOOLS en tête.

| Composant | Version | Source |
|---|---|---|
| WTOOLS | **2.0.2**, build 248 | `Contents/Resources/sq.version` (`<version>2.0.2</version>`) et Info.plist `CFBundleShortVersionString` / `CFBundleVersion`. Bundle `com.nicolaudiegroup.wtools`, installé le 2026-08-14 |
| Easy View 3 | **3.0.0**, build `26.0819.661.293` | `/Applications/Easy View/Easy View/Easy View.app` Info.plist ; `components.xml` : `easyView3.osx 3.0.0`. Installé le 2026-08-20 |
| EasyView 2 | 22.805.0.17 | `/Applications/EasyViewConnect/EasyView2/` — pas de `CFBundleShortVersionString`, seul `CFBundleVersion` est rempli. Installé le 2024-01-11 |
| EasyViewConnect | **aucune version déclarée** | Info.plist muet sur les deux clés ; `components.xml` donne `mev.osx 0.0.0.1` |
| macOS | **26.6.2** (25G83) | `sw_vers` |
| W1 Mk1 firmware | **2.0.18** | lu **en direct** par `GET_SETTINGS` (champ 14 `firmwareVer`), appareil branché, 2026-08-27 |
| wpj-toolkit | commit `2bd0ee3` (2026-08-14) | github.com/gitfeber/wpj-toolkit — relevé externe, non revérifié depuis |

### Ce que « beta » veut dire ici — à qualifier avant usage

Le paquet installé **ne se déclare pas beta** : `sq.version` porte
`<version>2.0.2</version>` et `<channel>arm64</channel>`, où `channel` est
l'architecture, pas un canal de diffusion. Ses notes de version décrivent une
2.0.2 ordinaire (sauvegarde des profils Wolfmix, communication contrôleur,
désynchro du visualiseur, traductions).

En revanche l'application **connaît la notion de beta pour le firmware** : son
snapshot AOT contient `betaFirmwareInfo` / `_betaFirmwareInfo` et une expression
régulière `\((stable|beta|dev)\)` qui reconnaît un suffixe de canal dans une
chaîne de version. **[observed]**

Donc « WTOOLS beta » est ambigu et il faut dire lequel :

- une **build beta de l'application** — rien dans le bundle installé ne l'indique ;
- un **firmware beta proposé par WTOOLS** pour le contrôleur — le mécanisme
  existe, et le W1 branché répond `2.0.18` sans suffixe de canal.

Tant que ce n'est pas tranché, aucune conclusion du dépôt ne doit s'appuyer sur
« la beta » : les résultats sont datés et attachés aux versions ci-dessus.

### Relevé appareil du 2026-08-27 — **[observed]**

Lecture seule (`GET_SETTINGS`), W1 branché, WTOOLS fermé. Le numéro de série
n'est pas reproduit (LEGAL.md).

| Champ | Valeur |
|---|---|
| `firmwareVer` (champ 14, chaîne) | `2.0.18` |
| `firmwareVersion` (champ 13, flottant) | **0.0** — le champ numérique est vide sur ce firmware ; un outil qui le lit obtient 0.0 et non 2.018 |
| `wolfmixMode` | 26 (`PROJECTS`) |
| `projectCount` / `fixtureProfileCount` | 6 / 3363 |
| `activatedUniverses` / `availableUniverses` | 2 / 4 |
| `wlinkActivated` | **false** |
| `visualiserActivated` | true |
| `availableMemory` / `availableProjectMemory` | 13 / 94 |
| `lockedState` / `editLockedState` / `projectChanged` | false / false / false |

Le couple `firmwareVer` = « 2.0.18 » et `firmwareVersion` = 0.0 est le piège à
retenir : **lire le champ 14, jamais le 13**.

### Disposition des données WTOOLS après la 2.0.2 — **[observed]**

`~/Library/Application Support/WTOOLS/` contient toujours `wlinkData/projects`
(16 `.wpj` au relevé), mais la 2.0.x a ajouté à côté `fixture_profiles.db`,
`ssl_fixture_profiles.db` et `logs/`. `docs/corpus.md` reste donc exact sur
l'emplacement des projets.

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
