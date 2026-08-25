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

## Couche publique (dépôt encore privé)

Base préparée pour que d'autres puissent s'en servir, sans publication pour
l'instant. Langue : anglais pour cette couche, français conservé dans
`research/`.

- `SPEC.md` — le format `.wpj` au niveau octet, chaque affirmation avec son
  statut de preuve. Couvre les trois variantes, les 20 types
  d'enregistrement, le modèle de patch (8 identités exactes sur 6 types),
  le sous-message preset et FX, les règles d'écriture et huit pistes
  ouvertes. Consolide `wpj-format-registry.md`, `preset-format-165.md` et
  `corpus-mining-2026-08-25.md`, dont trois corrections : l'octet 40 est le
  LSB d'un uint64 de version, le type 155 est le séquenceur FX et non le
  patch DMX, le type 115 n'a pas 20 slots fixes. Rien d'équivalent n'existe
  publiquement : `wpj-toolkit` publie des enums sans encodage wire et
  s'arrête à 3 types.
- `PROVENANCE.md` — sources, licences, ce qui est réutilisable et sous quelles
  conditions ; sous-ensemble du corpus publiable (9 fichiers sûrs, 7 à
  arbitrer car dérivés du rig rig-c) ; position sur le writer privé
  de WPJ Studio.
- `LICENSE` — MIT, comme `wpj-toolkit`, pour que la réutilisation croisée
  marche dans les deux sens. Une ligne à changer si l'arbitrage évolue.
- `tools/wpj_api.py` — inspect JSON à la forme du schéma `wpj-toolkit`
  (`modelVersion`, `project`, `presets[]`, `fixtures`, `validation`,
  `unknown_tlvs`), en local et hors ligne. Tout outil écrit contre l'API
  WPJ Studio fonctionne contre ce CLI, sans upload. Extensions additives :
  `fixtures.status: "partial"` (types 105/116 décodés là où l'amont annonce
  `unsupported`) et `x_records` (décodage complet du codec).
- `make check` — lance les cinq self-checks (round-trip octet, fidélité du
  codec, parcours B/C, compilateur de show, inspect JSON).

Deux pistes neuves sont nées du croisement de notre décodage octet avec les
enums MIT de `wpj-toolkit` — voir `SPEC.md` §10 : L1 (le `feature` des Beam FX
est probablement `f5`, inoccupé chez nous et sans emplacement wire chez eux) et
L2 (`beamGroupMask` limité à A–D contraint la lecture de `f16`).
