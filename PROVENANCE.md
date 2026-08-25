# Provenance

What in this repository is original, what comes from elsewhere, and what may be
reused under which terms. Anyone building on this needs to know which is which.

## Original work

Everything in `tools/`, `SPEC.md` and `research/` is derived from two sources
and nothing else:

1. **Our own corpus** — `.wpj` files produced by our own WTOOLS installation and
   our own W1, hashed in `corpus/SHA256SUMS`.
2. **Our own differential experiments** — single-variable changes made by the
   operator on our own device, downloaded before and after, compared record by
   record. Each one is written up in `research/` with its serial, firmware,
   file hashes and result.

No byte of any third-party implementation was read, disassembled or inspected.
This matters for one specific claim below.

## External sources

### `gitfeber/wpj-toolkit` — MIT

<https://github.com/gitfeber/wpj-toolkit>, commit `2bd0ee3` (2026-08-14).
Full digest in `research/wpj-toolkit-digest.md`.

**Reused here, with attribution:**

- FX enumerations — Beam type, Beam feature, Color type, `speedSource`,
  `bpmDivision`, `linkOrder`. We had the wire fields and the numeric domains;
  they had the labels. Marked as such in `SPEC.md` §5.
- The preset identity formula `id = (page - 1) * 20 + (slot - 1)`.
- The 7-channel order of a palette pad (`red, green, blue, white, amber, lime,
  uv`), used in `tools/wpj_codec.py`.
- The shape of the inspect response (`schemas/inspect-response.schema.json`),
  adopted as an output format by `tools/wpj_api.py` so that tooling written
  against it also works here — offline, with no upload.

**Not reused, because it does not exist there:** any wire-level encoding. The
toolkit documents inspection *keys* and enums; it publishes no byte layout, no
container writer, and no record type beyond 101, 135 and 165.

**On the writer.** That repository asks readers not to treat it as a recreation
of the private WPJ Studio writer. It is not one. Our writer (`tools/wpjlib.py`)
was derived from our own corpus and confirmed on our own device (experiment
ACC-01), and could not have been derived from that repository, which publishes
no writer and no byte layout to derive one from.

**Scope caveat:** the toolkit documents W1 **Mk2** files. Its container is our
variant A. Our variants B and C do not appear there.

### `wpj-studio.com` — proprietary, not used

A hosted product by the same author, with a private writer behind a paywall.
We do not call its `POST /api/v1/inspect` or `/validate` endpoints. Two reasons,
both binding:

1. Doing so would upload project files to a third party, which the repository's
   local-only rule forbids.
2. Using someone else's decoder as an oracle would break the provenance chain
   that gives every line of `SPEC.md` its evidence status.

### `mseerig/wolfmix-web-remote` — licence unclear, cited only

<https://github.com/mseerig/wolfmix-web-remote>. Its README claims MIT but the
tree contains **no LICENSE file** and the GitHub API reports no detected
licence. Treat as all-rights-reserved: **cite, do not copy.**

Two hardware-observed behaviours are quoted as facts in `research/`: the W1 is
a MIDI **sink only** (no feedback path), and on firmware 2.0 page switching and
live-effect editing over MIDI are not supported. Its default MIDI map is that
author's own learned assignment, **not** a factory map — do not publish it as
one.

### `forum.wolfmix.com` and vendor guides — quoted facts

Staff statements and user reports are quoted with their thread id (e.g. t=736
for "no communication protocols embedded beside MIDI"). Vendor guides are cited
by number. Short factual quotations, attributed; no document is reproduced.

## Corpus

Only a subset of `corpus/` may be published. The rule is per-file, not
per-directory.

| Publishable | Files | Why |
|---|---|---|
| **yes** (9 files) | `corpus/projects/00000000-…-cc21-….wpj` (*rig-a*, 10 fixtures), `…cd21-….wpj` (*rig-b*, 15 fixtures) | two small real projects, no third-party content |
| **yes** | `corpus/experiments/ACC-0{1..6}/*.wpj` (7 files) | written by our own writer, all derived from *rig-a* |
| **review first** | `corpus/experiments/FX-0{1,3,4,5,6}/*.wpj` (7 files) | named *WMX EXP format-lab*, but they are controller saves of a **copy of `f2737ec3` = the rig-c rig**: 20 fixtures, its patch and its presets. Only the project name differs. Publishing them publishes that rig |
| **no** | `rig-c.wpj`, `rig-c-bug.wpj`, `f2737ec3-….wpj` | the operator's production show, including its patch |
| **no** | the 5 variant-B files, the variant-C file, and the `.wm`/`.wmx` sidecars | WTOOLS-side data, not reviewed for third-party content |

The 9 safe files are enough for every self-check in `tools/` to run (each asserts
at least 5 variant-A files). Publishing the FX-\* set as well would raise the
evidence base from 2 independent rigs to 3 — worth doing **if** the operator
accepts that the rig-c patch becomes public.

Note: *rig-a* / *rig-b* are small real projects, not factory defaults.
Review them once before any public push.

## Trademarks

Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their
respective owners. This project is independent and is not affiliated with,
endorsed by, or sponsored by any of them. The `.wpj` format is not published by
its vendor; everything here is the result of black-box observation of files and
of a device we own.
