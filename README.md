# wolfmix-automation

Outillage local (macOS, Apple Silicon) pour inspecter, valider et — à terme —
éditer des projets Wolfmix `.wpj`, générer des profils de fixtures et composer
des shows pour un W1 Mk1. Recherche personnelle, aucun objectif commercial.

## Règles invariantes

1. **Vérité expérimentale** — toute interprétation porte un statut
   (observed → hypothesized → correlated → validated → device-confirmed)
   et sa preuve. Registre : `research/wpj-format-registry.md`.
2. **Lecture avant écriture** — écriture d'un champ seulement après
   round-trip octet-identique + validation différentielle + acceptation
   WTOOLS/EasyView. Octets inconnus préservés verbatim. Jamais d'écrasement,
   jamais d'écriture directe vers le W1.
3. **Matériel sacré** — pas de firmware, pas de fuzzing sur matériel
   connecté, fonctions dangereuses désactivées par défaut.
4. **Local only** — rien ne quitte la machine (ce dépôt privé excepté).
5. **Compatibilité honnête** — « compatible » = cellule testée de
   `research/versions.md`, rien de plus.

## Architecture (minimale, stdlib Python uniquement)

```
corpus/          copies figées en lecture seule des fichiers réels + SHA256SUMS
  projects/      .wpj / .wm depuis ~/Library/Application Support/WTOOLS/wlinkData
  wmx/           wmProfiles / wmBrands / wmProjects / wmPersistent
  experiments/   paires avant/après des expériences différentielles
research/        registre d'hypothèses, versions, plan d'expériences, digests
tools/           scripts d'inspection lecture seule (pas de writer tant que
                 la règle 2 n'est pas satisfaite)
```

## Pipeline cible (création de show de bout en bout)

```
show.json (patch + presets + FX, éditable)
   │  wpj_codec (encode, fidélité octet prouvée type par type)
   ▼
wpjlib (conteneur TLV + SHA-1, round-trip octet-identique garanti)
   ▼
nouveau .wpj → acceptation WTOOLS → synchro W1 (toujours par l'utilisateur)
```

Chaque étage n'écrit que ce que l'étage de validation a prouvé ; tout le
reste transite en octets bruts préservés.

## Outils

- `tools/wpjlib.py` — cœur lecture/écriture variante A : découpe TLV,
  réassemblage, SHA-1 recalculé, écriture sans écrasement. Self-check :
  round-trip octet-identique sur tout le corpus variante A.
- `tools/wpj_inspect.py fichier.wpj` — parcourt le wire format protobuf
  (variantes B/C), émet un arbre JSON. Refuse (exit 2) ce qui ne parse
  pas plutôt que de deviner. Sans argument = self-check.
- `tools/tlv.py`, `tools/dump.py` — extracteur TLV variante A + dumps
  d'analyse.

## État (2026-08-25)

Trois variantes de `.wpj` identifiées dans le corpus local, en-tête SHA-1
confirmé sur 8/9 fichiers, corps protobuf localisé, nom de projet et liste
de 100 presets repérés. Voir `research/wpj-format-registry.md`. Prochaine
étape : expériences EXP-01…05 (`research/experiments.md`).
