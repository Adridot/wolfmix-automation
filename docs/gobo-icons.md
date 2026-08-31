# Your fixture's real gobos on the W1 screen

End-to-end recipe, every step device-confirmed on firmware 2.0.18 on
2026-08-30 (RENAME-01/SORT-01 in `SPEC.md` §3.4 for the page edits). A
**resource flash** carries the interface's graphics and is not executable
firmware — [`../LEGAL.md`](../LEGAL.md) states that boundary, and this
repository never writes the controller's flash itself: it prepares a copy and
verifies it, WTOOLS uploads it. Three independent layers:

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

The controller's flash is written by WTOOLS, from the copy you just verified.
Before anything: **a verified backup of the original bundle, outside the WTOOLS
folder** — copy it to `$G/backup`; WTOOLS rewrites `wm-fw-bundle-2.0.18/` on
every update, and `gobo_run.py` re-checks on every run both the SHA-256 of the
copy against the live bundle **and** the live bundle against the manifest it
ships with (see the net, below).

Preconditions, all four:

```bash
python3 tools/wolfmix.py profiles | tail -3   # complete read; if truncated, restart the W1
python3 tools/wolfmix.py settings             # wlinkActivated must be false
```

- **`profiles` must answer completely** — the line count equals
  `fixtureProfileCount`. A truncated read happened once (2026-08-30) and was
  repaired by a restart; never write on a partial read.
- **WLINK off.** It is read-only and fails the write at 17% or 99%
  ([forum t=718](https://forum.wolfmix.com/viewtopic.php?t=718)).
- **The host machine on mains.** A write cut by a shutdown is the one scenario
  with no net.
- **The loaded project saved.** WTOOLS refuses otherwise: *Failed to update
  firmware — Save project before updating.*

Then reveal the control. `Upload Flash` only exists in WTOOLS' Full Debug mode,
which the SHIFT+CMD+D menu does not offer; the application accepts the mode as
a preference:

```bash
defaults write com.nicolaudiegroup.wtools flutter.wtoolsMode -int 2   # reveals the button
defaults write com.nicolaudiegroup.wtools flutter.wtoolsMode -int 0   # back to stock
```

WTOOLS must be closed for either, and restarted after. In mode 2,
**`Upload Firmware` sits right next to `Upload Flash`** — read the label out
loud before clicking. Select `$G/flash-custom.bin`.

**The W1 screen then sticks at "updating firmware 1/2 writing data 99%". This
is not a crash** — reproduced 2 times out of 2. The normal path pushes two
files where `Upload Flash` sends one, so the screen's state machine never
closes; the device keeps answering the protocol throughout (`getSettings` and
`getProjectList` come back complete, which a chip mid-erase would not do).
Check the `setFlashDataChunks` have stopped in the WTOOLS log, then restart the
W1 normally: the overlay lifts and the new flash loads.

That log is the only instrument on this side of the link, and it **rotates per
launch**: `~/Library/Application Support/com.nicolaudiegroup.wtools/logs/`
keeps five files, `wtools_logs_0.log` being the current run, and every start of
WTOOLS pushes the oldest one out. Copy the whole folder somewhere outside this
repository **before** launching WTOOLS again — five launches and the trace of
your upload is gone. The files carry the controller's serial number, which is
why `*.log` is git-ignored here and why the copy stays out of the tree.

Afterwards, put `wtoolsMode` back to 0, and re-read `settings` and `profiles`:
`firmwareVer`, `fixtureProfileCount` and `projectCount` must be what they were.

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
