# Digest — wpj-toolkit, commit `2bd0ee3` (2026-08-14)

Source : https://github.com/gitfeber/wpj-toolkit — registre d'hypothèses
adossé au comportement de WPJ Studio, **pas une spec**. Base documentée :
fichiers **W1 MK2**. Il correspond à notre **variante A** uniquement
(voir `wpj-format-registry.md`) ; nos variantes B/C n'y figurent pas.

Vocabulaire de preuve du kit : **verified** (exposé par WPJ Studio en prod),
**confirmed** / **unconfirmed** (`raw N (unconfirmed)`), **not decoded**,
**unknown**, **not tested**. Règle : jamais de nom inventé pour un enum non
confirmé ; clés absentes = omises, jamais 0 %/off.

## 1. Format (format-overview.md)

- Intégrité [verified] : digest **SHA-1 de 20 octets** en tête, calculé sur
  les octets 20→EOF. Digest faux ⇒ échecs d'ouverture dans les outils Wolfmix.
- Préfixe d'en-tête [opaque] : le reste des 64 premiers octets est traité
  comme opaque et préservé tel quel.
- Conteneur [verified] : à l'offset **0x40**, `uint32 LE longueur` +
  `uint16 LE type` ; enregistrements imbriqués au même en-tête ; payloads
  « protobuf-like » ; non-décodé conservé verbatim.
- Types connus [verified] : **101** = project metadata (nom UTF-8),
  **135** = palette ColorFX globale, **165** = conteneur preset. Le reste →
  `unknown_tlvs[]` (type + longueur seulement, jamais le payload).
- Identité preset [verified] : UI 1-based, 20 slots/page,
  `id = (page-1)*20 + (slot-1)` ; pages 1–10 ; « specials » sans page/slot.
- Versioning binaire : **non documenté** (seul `modelVersion: "1"` côté API).
- Non décodé : valeurs static colour, patch fixtures/DMX, encodage wire des
  groups/banks, writer/round-trip.

## 2. FX (beam-fx.md, color-fx.md ; beam-fx1.md = stub de redirection)

Mappent des **clés inspect** et des enums, pas des octets — l'encodage wire
n'est pas publié.

Champs communs `known.beamFx1/2`, `colorFx1/2` : `fadePercent`,
`sizePercent`, `speedPercent`, `phasePercent` (0–100) ; `type(Raw/Confirmed)` ;
`speedSource(Raw/Confirmed)` ; `linkOrder(Raw/Confirmed)` ; `bpmDivision`
(0–7). Beam : `feature(Raw/Confirmed)`. Color : `pads(Confirmed)` (1–16),
`maskRaw`, `unknownMaskBitsRaw`.

Enums confirmés :
- Beam type : 0 Sin Wave · 1 Sparkle · 2 Chaser · 3 CanCan · 4 Heartbeat ·
  5 Wolf Rider · 6–8 FX Seq 1–3.
- Beam feature : 0 Dimmer · 1 Zoom · 2 Iris · 3 Pan · 4 Tilt · 5 Effect.
- Color type : 0 Rainbow 1 · 1 Sparkle 1 · 2 Chaser 1 · 3 Light Fever ·
  4 Rainbow 2 · 5 Sparkle 2 · 6 Rainbow 3 · 7 Chaser 2.
- speedSource (Beam+Color) : 0 Clock · 1 Microphone · 2 Audio/BPM.
- bpmDivision : 0→8, 1→4, 2→2, 3→1, 4→1/2, 5→1/4, 6→1/8, 7→1/16.
- linkOrder Beam : 0 None/Fwd · 10–13 Group/{Fwd,Rev,Out,In} ·
  20–23 Fixture/{…} ; **1/2/3 non confirmés côté Beam**.
- linkOrder Color (jeu plus large) : 0–3 None/{Fwd,Back,Out,In} · 10–13
  Group/{…} · 20–23 Fixture/{…}.

Banks `colorBank`/`beamBank` : groupes **A–H**, 1 = FX1, 2 = FX2 ;
indépendants du mask. Group masks : `colorGroupMask` A–H,
`beamGroupMask` **A–D seulement**. Flags de présence : `beamGroupPresent`,
`staticColorPresent` (présence seule, valeurs non décodées).

Palette ColorFX (type 135, inspect-only) : `pads[]` avec `index` 1-based et
canaux 0–255 `red/green/blue/white/amber/lime/uv` (absents = omis).

## 3. Compatibilité (compatibility.md)

Firmware et build WTOOLS d'origine **non enregistrés** ; tests matériels
**non faits** ; écritures vérifiées software-path uniquement (bit-exact +
re-inspect), **aucun sign-off WTOOLS/device**. `fixtures.status:
unsupported`. Consigne : **DMX OUT débranché** pour tout test appareil.

## 4. Inspect API (inspect-api.md + schema)

`POST /api/v1/inspect` et `/validate` sur wpj-studio.com (multipart `file`,
max 10 MiB). Réponse : `modelVersion` (required, "1"), `project{name,
warnings, known.colorFxPalette}`, `presets[]{id,page,slot,name,rawPreserved,
known{…}}`, `fixtures{status,items}`, `validation{checksumOk,issues[]}`,
`unknown_tlvs[{type,payloadLength,rawPreserved}]`. Issues : severity
error/warning/info, codes `checksum_ok`/`checksum_mismatch`/doublons d'ids/
enums non confirmés (warnings).

## 5. Avertissements et lacunes

- **Writer privé** : `/organize`, `/transfer`, `/bulk-edit`, `/repair` =
  WPJ Studio Pro ; « Do not treat this repo as a recreation of the private
  writer ». CONTRIBUTING interdit : notes RE privées, hex dumps, .wpj de
  labo, field maps TLV non documentés, labels devinés, claims « all
  firmware supported ».
- Non décodé : static colour, patch DMX, wire des banks/masks/pads, Beam
  E–H, linkOrder Beam 1/2/3, payloads Move/Flash/séquenceur, préfixe 0–63
  hors digest, versioning binaire.
- Portée : miroir du comportement produit (« if a field is not in the
  shipped Inspector, it is not documented here »).
