# UPLOAD-08 — the first resource-flash write from here (BEFORE measuring)

UPLOAD-07 reconstructed the host side of `setFlashDataChunks` and put it
behind `wolfmix.py gobo-upload`; nothing has run it. This is the run: the
eleven August silhouettes back onto the W1 after the 2.0.19 update erased
them (UPLOAD-05), WTOOLS closed.

## Input

`~/gobos`, four gates green: backup = the 2.0.19 bundle verified against its
own manifest; `flash-custom.bin` sha256 `a624bc7d…`, 2 931 442 bytes, the
same image the device displayed on 2026-08-30, rebuilt from the exact 24×24
renders; 11 icons, ids 342–352, 16 566 bytes changed inside their windows;
sheet rendered after the patch and approved by the operator. Controller:
firmware 2.0.19 (tested), WLINK off, project saved, 3 364 profiles read
complete. Host on mains, confirmed by the operator at the command line.

## What is sent

179 requests of event 36: 178 chunks of 16 384 bytes, one of 15 090, each
prefixed by `chunk_size, total_size, offset` as big-endian uint32, each
awaited for a success status before the next. Timeout per chunk 30 s.

| # | Prediction | p |
|---|---|---|
| U1 | the first chunk is **acknowledged** — no `UNSAVED_PROJECT`, the project being saved | 0.75 |
| U2 | all 179 chunks acknowledged, median gap **under 250 ms** (the vendor's 163 ms) | 0.6 |
| U3 | the controller's firmware, profile and project counts unchanged after the last chunk | 0.9 |
| U4 | the W1 screen shows *updating firmware 1/2 … 99 %* and answers the protocol throughout, as it did for WTOOLS | 0.7 |
| U5 | after a restart, the gobo page of group A shows the eleven silhouettes on pads 7–17 | 0.65 |

What refuses without a net: a status other than success on a chunk after
the first — the write stops there and the image on the device is partial
until the next upload, from here or from WTOOLS's own update path, which
rewrites the factory image (UPLOAD-05). That path is the net.

## Results, the write (2026-09-04, 23:2x)

| # | Outcome |
|---|---|
| U1 | **held** — the first chunk acknowledged in 157 ms; no `UNSAVED_PROJECT` |
| U2 | **held** — 179 chunks acknowledged in 28.4 s; gap median **158 ms**, max 176 ms — the vendor's own cadence, 163 ms (UPLOAD-02) |
| U3 | **held** — firmware 2.0.19, 3 364 profiles, 6 projects, before and after |

No erase pause is visible on the first chunk: whatever the device does before
writing, it does it inside the same 160 ms. U4 and U5 follow the restart.

## Results, after the restart

| # | Outcome |
|---|---|
| U4 | **held** — the screen showed *updating firmware 1/2 … 99 %* during the write and answered the protocol from the gobo page (mode 8) |
| U5 | **held** — after `RESTART` over USB, the eleven silhouettes are back on pads 7–17 of group A |

Five of five. The direct uploader is **device-confirmed** on 2.0.19, and the
click in WTOOLS is no longer part of the recipe.
