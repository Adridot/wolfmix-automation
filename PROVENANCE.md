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

Consequence, stated plainly: on a fresh clone the self-checks **abstain** and
verify nothing. They report that, and `make check` still exits 0. Point
`WPJ_CORPUS` at projects of your own and they become real again.

## Trademarks

Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their
respective owners. This project is independent and is not affiliated with,
endorsed by, or sponsored by any of them. The `.wpj` format is not published by
its vendor; everything here is the result of black-box observation of files and
of a device we own.
