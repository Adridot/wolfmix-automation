---
name: gobo-icons
description: Put a fixture's real gobo shapes on the W1 screen — icons in the flash image, then names and pad order in the project. Use when the user wants custom gobo icons, to rename or reorder gobo pads, or to patch and upload wolfmixFlash.bin. Refuses to skip the backup, the proof sheet or the device preconditions.
license: MIT
---

Guided run of [`docs/gobo-icons.md`](../../../docs/gobo-icons.md) — **that
document is the authority**. If this checklist and the recipe ever disagree,
the recipe wins and this file is wrong. `research/flash-gobo-plan.md` is the
authority on the upload itself.

This skill orchestrates; it never re-implements. Every check belongs to the
tool that already owns it — announce what you expect, run the tool, relay its
verdict. Do not recompute a diff, a length, a byte window or a name limit that
a tool computes.

Three independent layers: icons live in the flash image and are global to the
machine, names and order live in the project and are optional. The steps run in
this order.

| Step | Tool | Control point |
|---|---|---|
| 0 backup | `shasum -a 256` | 4 hashes noted, copy **outside** the WTOOLS folder |
| 1 shapes + ids | image generator, `gobo_library.py palette` | one silhouette per gobo, and the ids this project shows |
| 2 patch | `gobo_write.py patch` | "N octets modifiés sur …", flash length unchanged |
| 3 proof sheet | `gobo_library.py sheet` **on the patched file** | operator says yes |
| 4 preconditions | `wolfmix.py profiles`, `wolfmix.py settings` | complete read, `wlinkActivated` false |
| 5 upload | WTOOLS, by hand | pad shows the new icon after a reboot |
| 6 names/order | `wpj_show.py compile` + `wolfmix_experiment.py deploy` | verified spec, manual reload |

Stop at the first step that fails. Never run a later step to "see if it works
anyway".

## 0. Verified backup — blocking

No backup, no patch and no upload. WTOOLS rewrites `wm-fw-bundle-*/` on every
update, so a copy left inside that folder is not a backup.

```bash
cp -R ~/Library/Application\ Support/com.nicolaudiegroup.wtools/wm-fw-bundle-*/ ~/wolfmix-backup/
shasum -a 256 ~/wolfmix-backup/*
```

Note the hashes and re-check them at the end. If the user cannot produce this,
stop here.

## 1. Silhouettes, then the ids to replace

Photos in wheel order, then one bold silhouette per gobo — recipe §1–2 carries
the generator prompt, use it verbatim. These are the user's fixture data:
**generated images, patched flash and renders stay outside the repository
tree** (`LEGAL.md`). If the user proposes a path under this repository, refuse
the location and suggest a working folder elsewhere, for example `~/gobos/`.

```bash
python3 tools/gobo_library.py palette their-project.wpj
```

Replace only ids the project's shows actually display. **Never `Open`** — its
pointer is shared by 96 entries, so rewriting it repaints all 96. Refuse that
id before calling the tool and say why; `gobo_write.py` refuses it too, and its
verdict is the one that counts.

## 2. Patch a copy

```bash
python3 tools/gobo_write.py patch ~/gobos/flash-custom.bin 342=mask:gobo07.png 343=mask:gobo08.png
```

`mask:` reads a white-on-black silhouette; an RGB export with no alpha lands
opaque. The tool writes a new file (never overwrites), checks the diff stays
inside the targeted windows and that the length is unchanged. Relay its line;
do not re-derive it.

## 3. Proof sheet — blocking

Render from the **patched file**, not from the sources, or the sheet proves
nothing:

```bash
WOLFMIX_FLASH=~/gobos/flash-custom.bin python3 tools/gobo_library.py sheet ~/gobos/check.png 342,343
```

Show it and ask the operator to approve. Fine detail dies at 24 px —
regenerate that one image with "solid silhouette, no interior detail" rather
than fighting it. **No approval, no upload.**

## 4. Device preconditions — blocking

```bash
python3 tools/wolfmix.py profiles | tail -3
python3 tools/wolfmix.py settings
```

- `profiles` must read completely — a truncated list is the transient
  `getProfileList` fault, fixed by rebooting the controller. Do not write
  through it.
- `wlinkActivated` must be `false`; WLINK is read-only and fails the write at
  17 % or 99 %.
- Ask the operator to confirm: host machine **on mains**, and the loaded
  project **saved** (WTOOLS refuses the upload otherwise).

Name the missing precondition and stop. A write cut by a power loss is the one
genuinely nasty scenario.

## 5. Upload — human, not automated

Follow `research/flash-gobo-plan.md`: the `wtoolsMode=2` (Full Debug)
preference that reveals `Upload Flash`, `Upload Firmware` sitting right next to
it, the screen stuck at "writing data 99 %" that is **not** a crash (the device
still answers the protocol; reboot lifts it), and the four-step safety net back
to stock. Do not drive it — read the procedure to the operator.

Nothing in this repository writes firmware, and this skill does not either.

## 6. Names and order — optional, per project

```json
{"base": "in.wpj",
 "gobo_noms": {"342": "Butterfly", "344": "Sun"},
 "gobo_ordre": [342, 343, 344, 425, 424]}
```

```bash
python3 tools/wpj_show.py compile spec.json out.wpj
python3 tools/wolfmix_experiment.py deploy out.wpj --label gobos --case gobo-01
```

Refuse before compiling, with the tool's own verdict:

- a name longer than **19 bytes** UTF-8 — past that the whole project refuses
  to open;
- `gobo_ordre` when the palette read shows the gobo wheel carried by a second
  group — unmeasured case, so the order/names layer is abandoned and said out
  loud. The icon layers stay available.

`deploy` writes a copy in the experiment slot, never the production project.
Two projects can share a name on the panel's Open screen — check the operator
opens the one that was deployed. **Reloading the project on the panel is always
manual.**
