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
[Provenance](PROVENANCE.md)

---

## What you get

**A byte-level specification of the `.wpj` format** — [`SPEC.md`](SPEC.md).
Three container variants, 20 record types, the patch model, the preset and FX
sub-messages, the write rules. Every claim carries an evidence status and the
experiment that produced it. Nothing equivalent is published anywhere else.

**Tools that refuse to guess.**

| Tool | What it does |
|---|---|
| [`wpjlib.py`](tools/wpjlib.py) | variant-A container: TLV split, reassembly, SHA-1 recomputed. Byte-identical round-trip, never overwrites |
| [`wpj_codec.py`](tools/wpj_codec.py) | semantic JSON ↔ bytes per record type. `decode` self-verifies the round-trip; unsupported input falls back to `{"raw": hex}` |
| [`wpj_inspect.py`](tools/wpj_inspect.py) | protobuf wire walk of variants B/C → JSON tree. Exits 2 on anything it cannot parse |
| [`wpj_api.py`](tools/wpj_api.py) | inspect JSON in the shape of the `wpj-toolkit` schema — local, offline, no upload |
| [`wpj_show.py`](tools/wpj_show.py) | show compiler: a `show.json` edit spec applied to a donor project, auto-verified |
| [`wpj_diff.py`](tools/wpj_diff.py) | byte-range diff between two projects, for differential experiments |
| [`wolfmix.py`](tools/wolfmix.py) | talk to a connected W1 over USB serial: settings, project list, download, live DMX, mode watch |
| [`wolfmix_experiment.py`](tools/wolfmix_experiment.py) | transactional experiment runner — snapshot, deploy, verify, restore on failure, journal every run |

**A frozen corpus and a research log.** Real `.wpj` files with SHA-256 sums,
before/after pairs for every differential experiment, and the reasoning
in [`research/`](research/) (in French; the public layer is in English).

## What you need

- Python 3 — standard library only, no dependencies, no virtualenv.
  Developed on 3.14, no version-specific syntax used.
- macOS or Linux. Only `wolfmix.py` is OS-sensitive (POSIX serial via `termios`).
- For file work: nothing else. A W1 is **not** required to read, decode,
  diff or compile projects.
- For device work: a Wolfmix W1 Mk1 on USB, and **WTOOLS closed** — the serial
  port is exclusive.

## Before you start

This is black-box research on a format its vendor does not publish, done on
hardware we own. It is not affiliated with, endorsed by, or sponsored by
Nicolaudie or Wolfmix. See [`PROVENANCE.md`](PROVENANCE.md).

Use at your own risk. The tools are built to be conservative — writes always
go to a **new** file, `wpjlib.save()` opens with `x` and refuses to overwrite,
the device runner only ever writes project UUIDs derived from an experiment
label, and no firmware operation is exposed anywhere. That is a design stance,
not a warranty. Keep your own backups of anything you care about.

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

**1. Clone and run the self-checks.** They are the acceptance test: five tools
proving byte fidelity over the frozen corpus.

```bash
make check
```

Expected tail: `round-trip octet-identique sur 25 fichiers`, `fidélité octet
vérifiée sur 35 fichiers variante A`, then three `self-check ok` lines.

**2. Inspect a project.**

```bash
python3 tools/wpj_api.py corpus/projects/rig-a.wpj | head -40
```

That is the `wpj-toolkit`-shaped inspect response — `modelVersion`, `project`,
`presets[]`, `fixtures`, `validation`, `unknown_tlvs` — produced locally.
For the raw record tree instead, use `tools/wpj_codec.py` or, on a variant B/C
file, `tools/wpj_inspect.py`.

**3. Compile a show.** Editing always starts from an existing donor project;
nothing is synthesised from scratch.

```json
{
  "base": "corpus/projects/rig-a.wpj",
  "nom": "MY SHOW",
  "presets": [
    {"id": 33, "nom": "Chaser", "color_fx1": {"effet": 2}}
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

**4. Diff two projects** — the primitive behind every experiment.

```bash
python3 tools/wpj_diff.py before.wpj after.wpj
```

**5. Talk to the device** (optional, WTOOLS closed).

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

## Back to a clean state

The repository never writes to WTOOLS' own data. `corpus/` holds frozen
read-only copies of `~/Library/Application Support/WTOOLS/wlinkData/`, verified
by `corpus/SHA256SUMS`. Device-side, `wolfmix_experiment.py` only touches its
own `WMX EXP …` UUIDs; delete them from the controller and nothing of yours has
moved. `.wolfmix-state/` is local scratch and is git-ignored — deleting it
loses run history, not data.

## FAQ

**Do I need a W1?** No. Everything except `wolfmix.py` and
`wolfmix_experiment.py` works on files alone.

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
variant A container, but nothing in the corpus is Mk2 and no claim is made.

**Is the research in French?** `research/` is, deliberately. `SPEC.md`,
`PROVENANCE.md`, `docs/` and this README are in English. Some tool output
strings are still French.

## Roadmap

| Item | Status |
|---|---|
| Variant A container writer, byte-identical round-trip | done, device-confirmed |
| Record inventory, patch model, preset/FX sub-message | done, see `SPEC.md` |
| Template-based show compiler (101/165/150/135) | done |
| Transactional device experiment runner | done |
| EXP-01…05 — WTOOLS-side differential experiments | planned, `research/experiments.md` |
| `size`/`fade`/`phase` attribution (f8/f6/f9) | open, needs one clean experiment each |
| Types 106/110/111/130/151/161 | passthrough only, undecoded |
| Variant B/C writer | not started — read-only by rule 2 |
| Fixture profile generation | not started |

## Documentation

| Document | What is in it |
|---|---|
| [`SPEC.md`](SPEC.md) | the `.wpj` wire format, byte by byte, with evidence status per claim |
| [`docs/tools.md`](docs/tools.md) | CLI reference for all eight tools, with exit codes |
| [`docs/show-format.md`](docs/show-format.md) | the `show.json` edit spec accepted by `wpj_show.py` |
| [`docs/device.md`](docs/device.md) | USB serial protocol, device commands, the experiment runner |
| [`docs/methodology.md`](docs/methodology.md) | evidence statuses, differential protocol, how to add an experiment |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | what the failure modes mean and what to do |
| [`PROVENANCE.md`](PROVENANCE.md) | sources, licences, what may be reused and published |
| [`research/`](research/) | the working log, in French — hypotheses, versions, per-experiment write-ups |

## Contributing

The bar is evidence, not code style. A patch that adds a field interpretation
must come with the experiment that produced it: the exact single-variable
manipulation, the before/after files, their hashes, the diff, and the status it
reaches. See [`docs/methodology.md`](docs/methodology.md).

Practical rules: standard library only, no new dependencies; `make check` must
pass; any writer change must keep the byte-identical round-trip over the whole
corpus; unknown bytes stay verbatim.

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
