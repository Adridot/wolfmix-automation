# Provenance

Reader: Reviewers and redistributors. Question: Where did the code and external claims come from?

What in this repository is original, what comes from elsewhere, and what may be
reused under which terms. Anyone building on this needs to know which is which.

## Original work

Every **byte-level** claim in `tools/`, `SPEC.md` and `research/` comes from
three locally retained sources:

1. **Our own corpus** — `.wpj` files produced by our own WTOOLS installation and
   our own W1, hashed in `corpus/SHA256SUMS`.
2. **Our own differential experiments** — single-variable changes made by the
   operator on our own device, downloaded before and after, compared record by
   record. Each one is a line in [`research/evidence.md`](research/evidence.md),
   with its date, its status, and the snapshot directory whose hashes are in
   `corpus/SHA256SUMS`.
3. **Our own parallel interoperability archive** — targeted offline analysis of
   the WTOOLS copy installed and licensed on this machine. For UPLOAD-07, 22
   selected function ranges are bound directly to App image SHA-256
   `f3466a2d070ddb3107f85922093dbddb981ce859b33511f1f9271b4e44a54923`
   and checked against independent disassembly. Only interface facts needed for
   the independently written client are carried here; no vendor code,
   decompiler output or application dump is distributed.

The local archive is outside this repository and its captures, application
images and generated reconstruction remain private. The frozen hashes and the
resulting event/framing facts are the provenance published here.

**Correction, 2026-08-31.** An earlier revision of this paragraph said
*everything* came from those two sources "and nothing else", and then the
section below listed four things reused from `wpj-toolkit`. Both cannot be
true. What is true is the narrower claim above: the **wire format** is ours,
and some **labels and one formula** are borrowed, with attribution, from a
source that publishes no byte layout. The distinction is the whole point of
this file, and the sweeping version quietly destroyed it.

## External sources

### `gitfeber/wpj-toolkit` — MIT

<https://github.com/gitfeber/wpj-toolkit>, commit `2bd0ee3` (2026-08-14), read
on 2026-08-14 and re-checked on 2026-08-25: the HEAD tree was still the same 14
files. **The pin has not been re-verified since**, and doing so needs a network
fetch — a manual step, not something `make check` can do.

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

### How external claims are graded

An external source cannot be `device-confirmed` by us, so those findings carry
their own scale, and it is deliberately weaker than the one in `SPEC.md`:

| Tier | Meaning |
|---|---|
| `src-doc` | stated in a source we fetched ourselves — the fact is *that the source says it*, not that it is true of our hardware |
| `src-tested` | the source claims it observed the behaviour on real Wolfmix hardware |
| `snippet` | reachable only through a search-engine summary; the page itself refused automated fetch. Weakest tier, treat as a lead |
| `ours-inferred` | our reading of the source, not something it says |

`forum.wolfmix.com`, `qlcplus.org/forum` and some vendor pages sit behind a bot
challenge that returns HTTP 403. **It was not bypassed**, so every forum fact
here is `snippet`.

### The survey — everything public, checked 2026-08-25

| Source | Licence | Scope | Value to us |
|---|---|---|---|
| [`mseerig/wolfmix-web-remote`](https://github.com/mseerig/wolfmix-web-remote) | README says MIT, **no LICENSE file**, GitHub detects none | USB-MIDI gadget + web UI + OSC bridge. No serial, no protobuf, no `.wpj` | The only public project that drives a W1 live; two hardware-observed firmware behaviours |
| [`gitfeber/wpj-toolkit`](https://github.com/gitfeber/wpj-toolkit) | MIT | `.wpj` inspect/validate, W1 Mk2 files | Labels for enums we already had the fields for |
| [WPJ Studio](https://wpj-studio.com/) | proprietary | Hosted inspect/validate, private writer | Its research pages only link the four toolkit documents |
| [Companion module request #1467](https://github.com/bitfocus/companion-module-requests/issues/1467) | n/a | Open since 2024, labelled *Missing documentation* | **A negative result**: nobody has published a Wolfmix control protocol |
| OS2L ↔ Wolfmix (forum t=630, VirtualDJ) | n/a | OS2L into **WTOOLS on the host**, port 9996 | The OS2L endpoint is WTOOLS, not the W1 |
| Wolfmix forum t=736 (staff) | n/a | Vendor position on remote control | "No communication protocols embedded beside MIDI" |
| Magic 3D Easy View / MEVP | proprietary | A Windows **DLL** loaded in-process; ArtNet is the documented interop | Dead end for the UDP 3024 link we sniffed — MEVP is not a network protocol |
| GitHub search `wolfmix` | n/a | 3 repositories total | Two are unrelated name collisions |

Nothing on npm, no vendor SDK, no `.proto`, no published event list for the USB
serial link: **the protocol work in `tools/wolfmix.py` has no public prior
art.** Three second-order facts from the same survey are worth keeping because
each one saves someone a search:

- **OS2L reaches the device over the same USB link we speak.** The W1 honours
  beat/BPM sync only — `os2l_button`, `os2l_cmd`, `os2l_info` and `os2l_scene`
  are not acted on. So there is an unidentified beat event on our link, and
  `Settings.extSyncState` is presumably its gate. `ours-inferred`, and a cheap
  target.
- **Nothing public documents the WTOOLS → Easy View link**, the UDP port 3024,
  its frame format or its XOR. This entry used to add "Easy View also ingests
  ArtNet, so a visualiser fed by our own data does not need those frames
  reproduced" — **withdrawn on 2026-08-31**. Easy View 3.0.0 has no Art-Net:
  `art-net`, `artnet`, `sACN` and `E1.31` appear nowhere in its 185 MB bundle,
  its Preferences offer General/Stage/Rendering and no input at all, and the
  running application binds one UDP port of its own. Whatever another build or
  another platform does, the escape hatch that sentence promised is not there.
  Not reproducing the 3024 frames remains the decision — it is now a choice
  about a proprietary link rather than a free one, and the price is that a
  fixture profile generated here cannot be exercised in the visualiser without
  WTOOLS driving it.
- **`wolfmix_project_v2` does not exist.** The only "v2" in this world is
  cosmetic: converting a pre-2.0 project appends a `v2` suffix to the project
  *name*. Do not go looking for a v2 container.

### The `WM_MODE_*` identifiers — names read, values measured

These are **interface constant names**, read as names, from software installed
on our own machine. Nothing of that software is reproduced here beyond the
identifiers themselves, and **every numeric value** in the measured map
(`SPEC.md` §10.2) was measured on our own device rather than taken from a
binary.

- `src-doc` — the legacy WTOOLS 1.x SDK bundle ships the enum as plain
  TypeScript **with** numeric values: 39 entries, `WM_MODE_HOME = 0` …
  `WM_MODE_UNREGISTERED = 38`.
- `src-doc` — WTOOLS 2.0.2 beta carries 45 distinct `WM_MODE_*` identifiers in
  its string pool, **names only, no values**.
- `src-doc` — that string pool is **not in declaration order** (`WM_MODE_HOME`
  is the 41st string), so no numeric value can be read from the 2.0.2 binary by
  string order. This is why the values were measured instead of read.

Three names left the SDK and nine arrived. Measurement then showed the legacy
0–38 numbering unchanged, the three departures being renames at their original
values, and the new modes living at 39–44:

| Only in the 1.x SDK | Only in 2.0.2 |
|---|---|
| `WM_MODE_STATIC_GOBO` | `WM_MODE_GOBO`, `WM_MODE_SEQ_POSITION_PICKER`, `WM_MODE_STATIC_POSITION_PICKER` |
| `WM_MODE_POSITION_PICKER` | `WM_MODE_BPM`, `WM_MODE_FILE_BROWSER`, `WM_MODE_INTELLIGENT_PRESET` |
| `WM_MODE_HUNGRY_WOLF` | `WM_MODE_LIVE_EDIT_MACRO_EDIT`, `WM_MODE_MAPPING`, `WM_MODE_USB_STICK` |

### `forum.wolfmix.com` and vendor guides — quoted facts

Staff statements and user reports are quoted with their thread id (e.g. t=736
for "no communication protocols embedded beside MIDI"). Vendor guides are cited
by number. Short factual quotations, attributed; no document is reproduced.

## Corpus — none of it is published

The earlier revision of this file weighed which corpus files were safe to
publish and concluded that nine of them were. **That conclusion is withdrawn.**

Re-reading the files settled it: ~70 of the ~78 printable strings in a project
are **byte-identical across unrelated rigs** — factory preset, effect, macro and
position names authored by the manufacturer. Every project also embeds fixture
profile data (names, channel layouts, capability ranges, gobo image ids) taken
from the vendor's profile library, and a device-derived UUID. There is no
"small, clean" project file; the smallest one still carries all three.

So the rule is now per-repository, not per-file: **no `.wpj`, `.wm` or `.wmx`
file is distributed here**, and `.gitignore` enforces it. What is published
instead:

| Published | Not published |
|---|---|
| `corpus/SHA256SUMS` — what was measured, by hash | the files themselves |
| the write-ups in `research/`, with per-experiment hashes | the before/after pairs |
| the tools that read and write the format | any project to read |
| `corpus/experiments/*/build.py`, `show.json` — our own edit specs | the donors they were run against |

Full reasoning, including everything else that is deliberately absent, in
[`LEGAL.md`](LEGAL.md). How to supply your own corpus:
[`docs/corpus.md`](docs/corpus.md).

Consequence, stated plainly: on a fresh clone the corpus-dependent checks
**abstain** and verify nothing. They say `ABSTAINED`, the run names every one
of them in its summary, and `make check` exits **3** rather than 0 — green with
abstentions is not a pass. Point `WPJ_CORPUS` at projects of your own and they
become real again.

## Trademarks

Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their
respective owners. This project is independent and is not affiliated with,
endorsed by, or sponsored by any of them. The `.wpj` format is not published by
its vendor; everything here is the result of black-box observation of files and
of a device we own.
