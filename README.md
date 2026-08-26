# wolfmix-automation

Read, decode, diff and rebuild Wolfmix `.wpj` project files — and drive a
Wolfmix W1 Mk1 over USB — from the command line, offline, with the Python
standard library and nothing else.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Firmware](https://img.shields.io/badge/W1%20Mk1%20firmware-2.0.18-orange.svg)](research/versions.md)
[![WTOOLS](https://img.shields.io/badge/WTOOLS-1.6.3-lightgrey.svg)](research/versions.md)
[![Python](https://img.shields.io/badge/python-3%20stdlib%20only-green.svg)](#what-you-need)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)](#what-you-need)

[What you get](#what-you-get) · [Quick start](#quick-start) ·
[Spec](SPEC.md) · [Docs](#documentation) · [FAQ](#faq) ·
[Legal](LEGAL.md)

---

## What you get

**A byte-level specification of the `.wpj` format** — [`SPEC.md`](SPEC.md).
Three container variants, 20 record types, the patch model, the preset and FX
sub-messages, the three static palette families, the write rules. Every claim
carries an evidence status and the experiment that produced it, including the
ones that turned out wrong. Nothing equivalent is published anywhere else.

**Tools that refuse to guess.**

| Tool | What it does |
|---|---|
| [`wpjlib.py`](tools/wpjlib.py) | variant-A container: TLV split, reassembly, SHA-1 recomputed. Byte-identical round-trip, never overwrites |
| [`wpj_codec.py`](tools/wpj_codec.py) | semantic JSON ↔ bytes per record type. `decode` self-verifies the round-trip; unsupported input falls back to `{"raw": hex}` |
| [`wpj_identities.py`](tools/wpj_identities.py) | structural identities between records — arithmetic constraints that refute a wrong reading without touching hardware |
| [`wpj_inspect.py`](tools/wpj_inspect.py) | protobuf wire walk of variants B/C → JSON tree. Exits 2 on anything it cannot parse |
| [`wpj_api.py`](tools/wpj_api.py) | inspect JSON in the shape of the `wpj-toolkit` schema — local, offline, no upload |
| [`wpj_show.py`](tools/wpj_show.py) | show compiler: a `show.json` edit spec applied to a donor project, auto-verified |
| [`wpj_diff.py`](tools/wpj_diff.py) | byte-range diff between two projects, for differential experiments |
| [`wolfmix.py`](tools/wolfmix.py) | talk to a connected W1 over USB serial: settings, project list, download, live DMX, mode watch |
| [`wolfmix_experiment.py`](tools/wolfmix_experiment.py) | transactional experiment runner — snapshot, deploy, verify, restore on failure, journal every run |

**A research log that shows its work.** Every field interpretation in
[`research/`](research/) carries the manipulation that produced it, the hashes,
the firmware, and the status it reached — including the refutations. Two
readings of the position palette were wrong and are recorded as wrong; a field
that looked like a blinder level turned out to be inert and is written up as
such.

**No project files.** None ship with this repository and none ever will — a
`.wpj` carries the manufacturer's factory content and someone's real show. You
point the tools at your own. See [`LEGAL.md`](LEGAL.md) and
[`docs/corpus.md`](docs/corpus.md).

## Where the format stands

| Area | State |
|---|---|
| Variant-A container, SHA-1 header, record 101 | **device-confirmed** — our generated files are accepted and stored byte-identically |
| Record inventory, 20 types | correlated across the corpus; 14 decoded, 6 round-tripped as opaque |
| Patch model (105/106/110/111/115/116/120/125) | locked by arithmetic identities; addresses confirmed against live DMX |
| Presets and FX sub-message (165) | effect type device-confirmed; `size`/`fade`/`phase` still hypothesised |
| Flash FX settings (102) | closed end to end except three fields; one of them refuted as inert |
| Static palettes — colour (140), gobo (145), position (150) | **device-confirmed**, one record per group A–H, read off the device's own editors |
| FX sequences (155) | decoded, 16 steps × 8 groups |
| UI mode enum (`WM_MODE_*`) | 26+ values measured on the device, not read out of a binary |
| Variants B and C | top level only — read-only by rule |

The gobo palette turned out not to be stored content at all: it is **derived
from the patch**, one pad per image-bearing range of the group's fixtures. That
identity is checked mechanically over the whole corpus by `wpj_identities.py`,
and confirmed on DMX — pressing pad *n* drives the gobo channel to the lower
bound of range *n*, exactly.

## What you need

- Python 3 — standard library only, no dependencies, no virtualenv.
  Developed on 3.14, no version-specific syntax used.
- macOS or Linux. Only `wolfmix.py` is OS-sensitive (POSIX serial via `termios`).
- **A project file of your own** to work on — see [Quick start](#quick-start).
- For device work: a Wolfmix W1 Mk1 on USB, and **WTOOLS closed** — the serial
  port is exclusive.

## Before you start

This is black-box research on a format its vendor does not publish, done on
hardware we own. It is not affiliated with, endorsed by, or sponsored by
Nicolaudie or Wolfmix. Read [`LEGAL.md`](LEGAL.md) — it is short, and it says
what is deliberately absent as well as what is here.

Use at your own risk. The tools are built to be conservative — writes always go
to a **new** file, `wpjlib.save()` opens with `x` and refuses to overwrite, the
device runner only ever writes project UUIDs derived from an experiment label,
and no firmware operation is exposed anywhere. That is a design stance, not a
warranty. Keep your own backups.

## Ground rules

These five constrain every line in the repository. They are the reason the
output is trustworthy, and the reason some obvious features are missing.

1. **Experimental truth.** Every interpretation carries a status
   (`observed → hypothesized → correlated → validated → device-confirmed`)
   and its evidence. Registry: [`research/wpj-format-registry.md`](research/wpj-format-registry.md).
2. **Read before write.** A field becomes writable only after a byte-identical
   round-trip, a differential validation, and acceptance by WTOOLS/EasyView.
   Unknown bytes are preserved verbatim. No overwrite, ever.
3. **Hardware is sacred.** No firmware operations, no fuzzing against a
   connected device, dangerous functions off by default.
4. **Local only.** Nothing leaves the machine — no upload, no third-party API.
5. **Honest compatibility.** "Compatible" means a tested cell in
   [`research/versions.md`](research/versions.md), and nothing more.

## Quick start

**1. Bring a project of your own.** Nothing here ships one.

```bash
mkdir -p corpus/projects
cp ~/Library/Application\ Support/WTOOLS/wlinkData/projects/*.wpj corpus/projects/
```

Or pull one off your controller with `python3 tools/wolfmix.py project <UUID>
out.wpj`. Either way the copies stay on your disk; no tool here uploads
anything. Details, and how to point `WPJ_CORPUS` somewhere else:
[`docs/corpus.md`](docs/corpus.md).

**2. Run the self-checks.** They are the acceptance test: six tools proving
byte fidelity and structural identities over whatever corpus you gave them.

```bash
make check
```

With no corpus present they say so, one line per tool, and exit 0 — nothing was
verified, and they will not pretend otherwise.

**3. Inspect a project.**

```bash
python3 tools/wpj_api.py corpus/projects/your-project.wpj | head -40
```

That is the `wpj-toolkit`-shaped inspect response — `modelVersion`, `project`,
`presets[]`, `fixtures`, `validation`, `unknown_tlvs` — produced locally.
For the raw record tree instead, use `tools/wpj_codec.py` or, on a variant B/C
file, `tools/wpj_inspect.py`.

**4. Compile a show.** Editing always starts from an existing donor project;
nothing is synthesised from scratch.

```json
{
  "base": "corpus/projects/your-project.wpj",
  "nom": "MY SHOW",
  "presets": [
    {"id": 33, "nom": "Chaser", "color_fx1": {"effet": 2}}
  ],
  "positions": [
    {"page": 1, "index": 0, "nom": "Public", "pan": 32768, "tilt": 15073}
  ]
}
```

```bash
python3 tools/wpj_show.py compile show.json out.wpj
```

The compiler validates every key against the fields whose status is at least
`correlated`, refuses anything out of scope, and re-reads its own output to
report exactly which records changed. Full key reference:
[`docs/show-format.md`](docs/show-format.md).

**5. Diff two projects** — the primitive behind every experiment.

```bash
python3 tools/wpj_diff.py before.wpj after.wpj
```

**6. Talk to the device** (optional, WTOOLS closed).

```bash
python3 tools/wolfmix.py settings
```

Then `projects`, `project UUID out.wpj`, `dmx --seconds 10`, `watch-mode`.
Protocol and command reference: [`docs/device.md`](docs/device.md).

## Working with the device

`wolfmix.py` is a client for the W1's USB serial protocol: 9-byte header,
protobuf payload, one event id per operation. The outgoing event whitelist is
explicit in the source — read commands, project set/delete, mode and preset
selection, restart. Firmware events are not implemented.

`wolfmix_experiment.py` wraps that into transactions: it snapshots every
controller project before initialising, derives a deterministic
`WMX EXP <label>` UUID that can never collide with a real project, uploads,
downloads the result back to verify it byte for byte, restores the previous
experiment project if anything fails, and journals each run under
`.wolfmix-state/`.

One manual bootstrap remains: firmware 2.0.18 exposes no USB command to select
a project, so after `init` you open the `WMX EXP …` project once on the W1
itself, then `arm`. Everything after that is automatic.

The DMX side is an oracle, not a screenshot: `dmx-envelope` records per-channel
min/max over a window, so a static channel has `min == max` and an animated one
keeps its range whatever the phase. That is what makes two runs comparable, and
it is how the gobo palette was confirmed and how a suspected blinder field was
refuted.

## Back to a clean state

The repository never writes to WTOOLS' own data — you copy out of it, and the
tools only read what you copied. Device-side, `wolfmix_experiment.py` only
touches its own `WMX EXP …` UUIDs; delete them from the controller and nothing
of yours has moved. `.wolfmix-state/` is local scratch and is git-ignored —
deleting it loses run history, not data.

## FAQ

**Do I need a W1?** No. Everything except `wolfmix.py` and
`wolfmix_experiment.py` works on files alone — but you do need a project file
of your own to point them at.

**Why does `make check` say it verified nothing?** Because you have no corpus
yet. See [`docs/corpus.md`](docs/corpus.md). An abstention is reported as an
abstention; the alternative would be a green check that means nothing.

**Why don't you ship a sample project?** Because a `.wpj` is not ours to
redistribute: ~70 of its strings are the manufacturer's factory content, its
profile data comes from the vendor's fixture library, and the rest is somebody's
real show. [`LEGAL.md`](LEGAL.md).

**Does it write projects back to the controller?** Only the experiment runner,
only to deterministic `WMX EXP …` UUIDs, only after verifying the upload by
downloading it again. Ordinary projects are never overwritten.

**Why can't I edit field X?** Because it has not been proven yet. `wpj_show.py`
covers records 101, 165, 150 and 135, and only the keys at status
`correlated` or better. `size`/`fade`/`phase` are still `hypothesized`, so
they are readable but not writable. See [`SPEC.md`](SPEC.md) §10–11.

**What are the three variants?** A is SHA-1 + a TLV container (type 100) — the
device/WLINK-side format, and the only one that is writable here. B is
SHA-1 + bare protobuf, C is bare protobuf without a digest. See
[`SPEC.md`](SPEC.md) §1.

**Does it upload anything to wpj-studio.com?** No. `wpj_api.py` emits that
schema's response shape locally so tooling written against it works offline.
The reasoning is in [`PROVENANCE.md`](PROVENANCE.md).

**Mk2 support?** Untested. The `wpj-toolkit` digest suggests Mk2 files use our
variant A container, but nothing measured here is Mk2 and no claim is made.

**Is the research in French?** `research/` is, deliberately. `SPEC.md`,
`LEGAL.md`, `PROVENANCE.md`, `docs/` and this README are in English. Some tool
output strings are still French.

## Roadmap

| Item | Status |
|---|---|
| Variant A container writer, byte-identical round-trip | done, device-confirmed |
| Record inventory, patch model, preset/FX sub-message | done, see `SPEC.md` |
| Static colour / gobo / position palettes (140/145/150) | done, device-confirmed |
| FX sequences (155) | decoded |
| Template-based show compiler (101/165/150/135) | done |
| Transactional device experiment runner | done |
| `size`/`fade`/`phase` attribution (f8/f6/f9) | open, needs one clean experiment each |
| Record 102 `f5`/`f6`/`f11` — three unattributed values | open, highest value per unit of effort |
| MIDI mapping record | not located — the gateway to live control |
| Types 106/110/111/130/151/161 | patch-side structure known, wire semantics partial |
| Variant B/C writer | not started — read-only by rule 2 |
| Fixture profile generation | not started |

## Documentation

| Document | What is in it |
|---|---|
| [`SPEC.md`](SPEC.md) | the `.wpj` wire format, byte by byte, with evidence status per claim |
| [`LEGAL.md`](LEGAL.md) | what is not distributed here and why; interoperability position |
| [`docs/corpus.md`](docs/corpus.md) | bringing your own project files, and what makes a good corpus |
| [`docs/tools.md`](docs/tools.md) | CLI reference for every tool in `tools/`, with exit codes |
| [`docs/show-format.md`](docs/show-format.md) | the `show.json` edit spec accepted by `wpj_show.py` |
| [`docs/device.md`](docs/device.md) | USB serial protocol, device commands, the experiment runner |
| [`docs/methodology.md`](docs/methodology.md) | evidence statuses, differential protocol, how to add an experiment |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | what the failure modes mean and what to do |
| [`PROVENANCE.md`](PROVENANCE.md) | sources, licences, what may be reused from where |
| [`research/`](research/) | the working log, in French — hypotheses, versions, per-experiment write-ups |

## Contributing

The bar is evidence, not code style. A patch that adds a field interpretation
must come with the experiment that produced it: the exact single-variable
manipulation, the before/after hashes, the diff, and the status it reaches. See
[`docs/methodology.md`](docs/methodology.md).

Practical rules: standard library only, no new dependencies; `make check` must
pass; any writer change must keep the byte-identical round-trip; unknown bytes
stay verbatim; **no project file, vendor document or extracted resource in a
commit** — `.gitignore` is there to catch it, do not work around it.

## License

MIT — see [`LICENSE`](LICENSE). Chosen to match `wpj-toolkit` so reuse works in
both directions.

## Acknowledgements

- [`gitfeber/wpj-toolkit`](https://github.com/gitfeber/wpj-toolkit) (MIT) — FX
  enumerations, the preset identity formula, the palette channel order and the
  inspect response shape. Attributed field by field in
  [`PROVENANCE.md`](PROVENANCE.md).
- [`mseerig/wolfmix-web-remote`](https://github.com/mseerig/wolfmix-web-remote)
  — two hardware-observed MIDI facts, cited only, not copied (no LICENSE file
  in that tree).
- `forum.wolfmix.com` — staff and user statements, quoted with thread ids.

Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their
respective owners. This project is independent of all of them.
