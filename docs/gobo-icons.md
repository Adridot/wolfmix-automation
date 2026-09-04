# Your fixture's real gobos on the W1 screen

Reader: Controller operators. Question: How do I replace and verify gobo icons?

End-to-end recipe, every step device-confirmed — on firmware 2.0.18 on
2026-08-30 (RENAME-01/SORT-01 in `SPEC.md` §3.4 for the page edits), the
direct upload on 2.0.19 on 2026-09-04 (UPLOAD-08). A
**resource flash** carries the interface's graphics and is not executable
firmware — [`../LEGAL.md`](../LEGAL.md) states that boundary. This repository
prepares, verifies and can upload only a copy whose diff is confined to declared
gobo icon windows. Three independent layers:

| Layer | What changes | Where it lives | Tool |
|---|---|---|---|
| Icons | the 24×24 images themselves | `wolfmixFlash.bin`, global | `gobo_write.py` |
| Names | the label under each pad | the project, record 145 | `wpj_show.py`, key `gobo_names` |
| Order | which pad is where | the project, record 111 | `wpj_show.py`, key `gobo_order` |

Work in a directory of your own, **outside this repository** — every command
below calls it `$G`. `gobo_run.py` holds the gates between the steps and writes
nothing:

```bash
G=~/gobos
python3 tools/gobo_run.py $G
```

It prints where you are, refuses to name the next step while a gate is red, and
exits 2 when one is. Run it as often as you like.

## 1. Photograph the wheel

Project every gobo on a flat surface in the dark, one photo each, **in wheel
order** (gobo 1 is usually Open). The photos are only a reference for the next
step — nobody will see them at 24 pixels.

## 2. Generate silhouettes

A photo scaled to 24×24 is mush; a bold shape survives. Feed each photo to an
image generator with this prompt, then save the outputs in `$G` as
`gobo01.png`, `gobo02.png`, … in wheel order:

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
python3 tools/gobo_write.py patch $G/flash-custom.bin \
    342=mask:$G/gobo07.png 343=mask:$G/gobo08.png ...
```

`mask:` turns white-on-black into a cut-out silhouette; the 1024×1024 files
are reduced by area averaging. The tool checks the diff stays inside the
targeted windows and the length is unchanged, and writes
`flash-custom.bin.json` beside the output: the manifest carrying the source
bundle's SHA-256, the result's, the patched ids and the byte windows. That
manifest is what `gobo_run.py` verifies before it will name the upload step —
without it, any file of the right length would pass. To preview the real 24×24
result before uploading, render a sheet **from the patched file** and look at
it — rendering it from the sources proves nothing, and `gobo_run.py` fails the
gate when the sheet is older than the flash it claims to show:

```bash
WOLFMIX_FLASH=$G/flash-custom.bin python3 tools/gobo_library.py \
    sheet $G/sheet.png 342,343
```

## 5. Upload

The controller can receive the verified copy directly, with WTOOLS closed:

```bash
python3 tools/wolfmix.py gobo-upload "$G" --confirm-mains-power
```

The command refuses before opening the port unless all local gates pass:

- `$G/backup/changelog.json` verifies the backup image by SHA-256;
- `flash-custom.bin` and its manifest have the declared hashes and sizes;
- every changed byte is inside the icon windows named by the manifest;
- `sheet.png` exists and is newer than the patched image;
- the operator explicitly confirms mains power.

It then checks that the project is saved, WLINK is off, the firmware is one of
the measured versions and the complete profile inventory is readable. The
[resource-flash reference](../SPEC.md#resource-flash) owns the device-confirmed
chunk layout and the distinction from the forbidden executable-firmware event.

After the last acknowledged chunk, the command re-reads the firmware version,
profile count and project count and refuses a changed baseline. The W1 screen
sits at *updating firmware 1/2 … 99 %* meanwhile and still answers the
protocol. Restart it — the panel, or `RESTART` over USB — to clear the overlay
and load the new icons. Measured: 179 chunks in 28 s, 158 ms each (UPLOAD-08).

### The net, by severity

1. Re-upload the original `wolfmixFlash.bin` you backed up — the normal way
   back, and it is **proven**: a magenta test icon was written and then undone,
   stock names restored (2026-08-30). The image it restores is not merely a
   copy of what was on disk: the bundle ships `changelog.json`, the vendor's
   own manifest, with one SHA-256 per binary, and the three installed binaries
   hash to exactly what it declares (2026-08-31, `UPLOAD-03`). `gobo_run.py`
   re-runs that comparison on every run and says so on gate 0's line.
   **The limit, so the check is not read for more than it is:** the manifest
   proves the *local* integrity of the image — nothing has rotted, been
   truncated or been patched on this machine since the download. It says
   nothing about what the vendor's server served, because the manifest
   travelled inside the same bundle. A bundle that ships no manifest is not
   refused; the gate says the provenance could not be verified and the verdict
   rests on the copy alone.
2. WTOOLS *Settings > Factory Reset* — reinstalls the last firmware **and** its
   flash (W1 manual v2.0 p.70).
3. WOLF+SPEED at power-on → bootloader → WTOOLS, if the W1 no longer boots.
4. WOLF+SMOKE → the factory firmware embedded in the device, without a PC.

Present, and deliberately unnumbered: the bundle also carries
`wolfmixFlash-reset.bin`, 15 724 544 bytes, listed in `changelog.json` and
hashing to the digest declared there. It is **[observed]** — a name, a size and
a place in the bundle. Nothing here has measured what it contains, what sends
it or what it would restore, so it is given no role in the list above; it is
named because leaving a 15 MB file out of a description of the net would be the
omission, not the caution.

No public bricking case is attributable to a flash modification; the reported
ones come from failed firmware updates or USB faults.

## 6. Names and order (optional, per project)

Both are ordinary `wpj_show` edits ([`show-format.md`](show-format.md)),
with the same auto-verified spec as preset edits:

```json
{"base": "in.wpj",
 "gobo_names": {"342": "Butterfly", "344": "Sun"},
 "gobo_order": [342, 343, 344, 425, 424]}
```

```bash
python3 tools/wpj_show.py compile spec.json out.wpj
```

Deploy with `wolfmix_experiment.py deploy` (`device.md`), then reload the
project on the panel — reloading is always manual. Names follow their gobos
through a reorder; DMX bounds travel with each range, so every pad keeps
projecting its own motif.

## The traps

- **A firmware update erases your icons.** The normal update pushes the
  vendor's flash after the firmware (UPLOAD-05, on 2.0.19). Keep the exact
  24×24 renders — `gobo_library.py sheet` shows them, the `id=img.png` plain
  form re-writes them byte for byte — and re-upload after every update.
  The `mask:` path from the 1024² sources gives a *similar* image, not the
  same bytes, once the tool's resampling has changed.
- **Why the direct uploader is narrow.** Targeted analysis of the exact WTOOLS
  2.0.2 image closed UPLOAD-06: resource event `0x24` and firmware event `0x19`
  are separate, and the former's 12-byte prefix is fully determined. The CLI
  still accepts only a gobo manifest whose byte diff re-verifies against the
  backed-up original; it is not a general flash writer (UPLOAD-07).

- An RGB export with no alpha lands opaque; `mask:` exists so you never hand
  the tool a flattened icon by accident.
- Fine detail (wing veins, thin outlines) dies at 24 px — regenerate that one
  image with "solid silhouette, no interior detail" rather than fighting it.
- Two projects can share a name on the panel's Open screen (the experiment
  slot is a copy) — check you are opening the one you deployed to.
- Your generated images and patched flash are **your fixture's data**: keep
  them outside the repository, like every render (`LEGAL.md`).
- An icon whose size is not 1728 bytes shifts everything: the table's pointers
  are absolute, not relative. The tool refuses it; do not work around it.
- Two icons out of 705 (ids 227 and 229) carry 72 near-transparent surplus
  bytes — a vendor export leftover, harmless.
