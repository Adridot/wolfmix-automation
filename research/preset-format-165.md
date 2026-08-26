# Type 165 — conteneur presets (variante A) — relevé 2026-08-25

Corpus : 5 fichiers A, 406 presets analysés. Statuts : observed /
hypothesized / correlated (aucune validation différentielle encore).

## Enveloppe [correlated]

Protobuf : `f1 varint = nombre de presets` (82 rig-c, 80 cc21/cd21),
puis `f5` répété = un sous-message par preset. Organisation : 4 pages
usine ×20 (bloc 1 « full presets », bloc 2 couleurs, bloc 3 move, bloc 4
beam) + presets utilisateur en queue.

## Sous-message preset

| Champ | Sémantique | Statut |
|---|---|---|
| f19 | id du preset = (page-1)·20+(slot-1), séquentiel, 0 omis | correlated 5/5 |
| f25 | nom UTF-8 (« Startup », « <nom utilisateur> »…) | correlated (82 noms) |
| f1/f2 | Beam FX 1/2 (sous-msg FX) | correlated (la page beam ne touche que f1) |
| f5/f6 | Color FX 1/2 | correlated (presets ColorFX ne touchent que f5) |
| f21/f22 | Move FX 1/2 (f3 supplémentaire, déf. 50) | correlated |
| f28 | index de position (type 150) par groupe A–H, 8 varints | correlated (« Floor »=[0]⁸, « Center »=[1]⁸, « Crowd »=[3]⁸, « Ceiling »=[4]⁸) |
| f29 | index de gobo (type 145) par groupe A–H, 8 varints packés, **0-based**, 255 = aucun | **device-confirmed** (F29-01 : f29[A]=9 → DMX 70, f29[A]=2 → DMX 21, deux prédictions exactes) |
| f31 | couleur statique : 4 rép. × 5 varints, bitmasks de pads du type 140 (« Deep Red » mask 32 = pad 6 {R:255}) ; 4 rép. = candidat groupes A–D | hypothesized |
| f17 | dimmer par groupe A–H (packé, déf. [255]⁸) | hypothesized |
| f8 / f24 | flag Color FX actif / Move FX actif (0\|255) | correlated |
| f4 | masque de contenu (255 full, 8 couleur, 17 beam, 5 move ; b3=couleur b4=beam b2=position ?) | hypothesized |
| f16 | ~13 varints : masques de banques FX par groupe en paires complémentaires + 1 varint global recopié | hypothesized |
| f11 | 500/2000/4000 — candidat fondu ms | hypothesized |
| f10 | candidat version librairie usine | observed |
| f9=1, f15=1000 (même constante que champ 2 des presets B/C), f13 ×6, f18, f3/f7/f14/f23/f26/f27/f30 | inconnus (tableaux par groupe) | observed |
| f32/f33/f34/f35 | tableaux par groupe ajoutés au schéma 10 (déf. 50/0/100/100) ; zéros dans le projet migré depuis le schéma 8 | correlated (voir le registre) |

## Sous-message FX (commun Beam/Color/Move)

| Champ | Sémantique | Statut |
|---|---|---|
| f7 | type d'effet : Sparkle=1, Chaser=2, CanCan=3, Heartbeat=4, Wolf Rider=5, FX Seq1=6 (0=Sin Wave omis) | **device-confirmed** (ACC-04 : 3→2 = Chaser constaté sur W1) |
| f4 | linkOrder {10,11,12,13} = Group/Fwd-Rev-Out-In, déf. 10 | correlated (enum wpj-toolkit) |
| f10 | speedSource {1 micro, 2 audio/BPM} (0 Clock omis) | correlated |
| f1 | bpmDivision {1,2,3}, déf. 3 | correlated |
| f2 | speed % (observé jusqu'à 200 — dépasse le 0-100 du toolkit) | correlated |
| f8 / f6 / f9 | size % / fade % / phase % (déf. 100/25/50) — attribution size/fade permutable | hypothesized |
| f5 | ColorFX : 2 varints = masque 16 bits des pads (v1=pads 1-8, v2=pads 9-16 : Rainbow [224,10]=6-8+10/12, Carnival [240,4]=5-8+11) ; MoveFX : 1 varint 0-6 | correlated (ACC-05 en cours) |

## Corrections et types frères

- **Type 140 ×8 = les palettes de couleur statique, une par groupe A–H**,
  20 pads, champs 1–7 = R, G, B, W, A, L, UV en 0–255. **device-confirmed**,
  voir le registre : la vue `RGB+` de l'écran imprime les octets stockés.
  Les 8 « pages » sont les groupes, pas des pages. Le pad 6 est **Red**, ce qui
  ancre la lecture de `f31` (bit n → pad n+1).
  **Corrige l'hypothèse antérieure** (« configs FX par groupe ») : faux.
- **Type 145 ×8 = 8 pages de 20 boutons à glyphe** (char police d'icônes,
  id, nom optionnel) ; pages 2-8 vides partout. | hypothesized
- Type 150 ×8 : 8 pages de 20 positions {f3,f4 = pan/tilt 16 bits,
  f6-f8 = 16 bits supplémentaires}, entrées usine nommées. | correlated
- Type 151 (64 o) : 4 entrées uint16 centrées 32767, vide dans cc21/cd21 —
  candidat état pan/tilt Move FX par groupe A–D. | hypothesized
- Type 155 (562 o) : 4 séquences, grilles 8 groupes × 16 pas, décalages
  par groupe — candidat séquenceur FX Seq. | hypothesized
- Type 161 : change à chaque révision (cinci≠bug≠f2737) → état volatil
  UI/machine, pas du contenu de show. | observed

## Diff f2737ec3 → rig-c-bug sur le 165

Varint global de f16 40→16 sur les 82 presets + retouches live sur
« Get Moving » et « Aim » (micro, phase/size, dimmer groupe B 255→64/71).
Rien qui explique le blackout → renforce le diagnostic type 120.

## Expériences de validation minimales (à ajouter au plan)

- EXP-07 : changer le type d'un Beam FX (Sin Wave → Sparkle) → seul
  165[preset].f1.f7 doit passer 0→1.
- EXP-08 : position du seul groupe A (Center → Ceiling) → f28
  [1,…]→[4,1,…] ; valide l'ordre A–H.
- EXP-09 : couleur statique mono-pad (pad 6 rouge, groupe A) → localise
  l'encodage de f31 et tranche « 4 répétitions = groupes A–D ? ».

## Corrections post-codec (2026-08-25)

- **[observed]** f28/f17/f8/f24 sont des varints **packés** (wire type 2,
  concaténation de varints), pas des varints répétés ; f8/f24 « flags »
  sont packés à 1 élément ([255]), pas des varints nus.
- **[observed]** f3 des boutons du type 145 = nom UTF-8 optionnel
  (confirmé : « points »).
- Codec : 165/140/145 fidèles octet sur 9 fichiers, 649 presets, zéro
  repli raw (python3 tools/wpj_codec.py pour la preuve).
