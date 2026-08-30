# Your fixture's real gobos on the W1 screen

End-to-end recipe, every step device-confirmed on firmware 2.0.18
(`research/flash-gobo-plan.md` for the measurements, RENAME-01/SORT-01 in
`SPEC.md` §3.4 for the page edits). Three independent layers:

| Layer | What changes | Where it lives | Tool |
|---|---|---|---|
| Icons | the 24×24 images themselves | `wolfmixFlash.bin`, global | `gobo_write.py` |
| Names | the label under each pad | the project, record 145 | `wpj_show.py`, key `gobo_noms` |
| Order | which pad is where | the project, record 111 | `wpj_show.py`, key `gobo_ordre` |

## 1. Photograph the wheel

Project every gobo on a flat surface in the dark, one photo each, **in wheel
order** (gobo 1 is usually Open). The photos are only a reference for the next
step — nobody will see them at 24 pixels.

## 2. Generate silhouettes

A photo scaled to 24×24 is mush; a bold shape survives. Feed each photo to an
image generator with this prompt, then save the outputs as `gobo01.png`,
`gobo02.png`, … in wheel order:

> I will send you photos of gobos projected by a moving-head light onto a
> surface, in the dark. For EACH photo, generate a stylised icon of the
> projected motif, meant to be displayed at 24×24 pixels on a controller
> screen. Hard constraints, all mandatory: square 1024×1024 image; pure black
> background (#000000), no gradient, no halo; the motif in pure white
> (#FFFFFF), flat fill, no shadow, no glow, no 3D; ignore the colour of the
> light in the photo — it comes from the colour wheel, only the SHAPE counts;
> simplified geometric silhouette, no photorealism — drop any detail finer
> than 1/20 of the image width; motif centred, about 80% of the width; match
> the number and layout of visible elements (count the dots, branches, arms);
> no text, no frame, no watermark. One image per photo, in the order I send
> them. If a motif is ambiguous, ask before generating.

## 3. Find the ids to replace

```bash
python3 tools/gobo_library.py palette your-project.wpj
```

prints each pad's gobo id and stock name. Replace only ids that project shows
actually display. Never touch `Open` — its pointer is shared by 96 entries and
the tool refuses it.

## 4. Patch and verify

```bash
python3 tools/gobo_write.py patch flash-custom.bin 342=mask:gobo07.png 343=mask:gobo08.png ...
```

`mask:` turns white-on-black into a cut-out silhouette; the 1024×1024 files
are reduced by area averaging. The tool itself checks the diff stays inside
the targeted windows and the length is unchanged. To preview the real 24×24
result before uploading, render a sheet from the patched file with
`gobo_library.py sheet` and look at it.

## 5. Upload

`research/flash-gobo-plan.md` is the authority — preconditions (complete
`profiles` read, WLINK off, machine on mains, saved project), the WTOOLS
Full Debug mode that reveals `Upload Flash`, the screen frozen at 99% that is
**not** a crash, and the four-step safety net back to stock. Keep a verified
backup of the original bundle **outside** the WTOOLS folder first.

## 6. Names and order (optional, per project)

Both are ordinary `wpj_show` edits ([`show-format.md`](show-format.md)),
with the same auto-verified spec as preset edits:

```json
{"base": "in.wpj",
 "gobo_noms": {"342": "Butterfly", "344": "Sun"},
 "gobo_ordre": [342, 343, 344, 425, 424]}
```

```bash
python3 tools/wpj_show.py compile spec.json out.wpj
```

Deploy with `wolfmix_experiment.py deploy` (`device.md`), then reload the
project on the panel — reloading is always manual. Names follow their gobos
through a reorder; DMX bounds travel with each range, so every pad keeps
projecting its own motif.

## The traps

- An RGB export with no alpha lands opaque; `mask:` exists so you never hand
  the tool a flattened icon by accident.
- Fine detail (wing veins, thin outlines) dies at 24 px — regenerate that one
  image with "solid silhouette, no interior detail" rather than fighting it.
- Two projects can share a name on the panel's Open screen (the experiment
  slot is a copy) — check you are opening the one you deployed to.
- Your generated images and patched flash are **your fixture's data**: keep
  them outside the repository, like every render (`LEGAL.md`).
