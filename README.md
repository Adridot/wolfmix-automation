<div align="center">

<img src="docs/assets/banner.svg" alt="wolfmix-automation — the Wolfmix .wpj format, byte by byte" width="880">

# wolfmix-automation

**Read, decode, diff and rebuild Wolfmix `.wpj` project files — and drive a Wolfmix W1 over USB — from the command line.**

*Offline. Python standard library only. No dependencies, no uploads, no guessing.*

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python](https://img.shields.io/badge/python-3.10%2B%20stdlib%20only-3776AB.svg)](#requirements) [![Firmware](https://img.shields.io/badge/W1%20Mk1%20fw-2.0.18-orange.svg)](research/versions.md) [![WTOOLS](https://img.shields.io/badge/WTOOLS-2.0.2%20beta-lightgrey.svg)](research/versions.md) [![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)](#requirements) [![Status](https://img.shields.io/badge/status-research-yellow.svg)](SPEC.md)

[**What is this?**](#what-is-this) · [**Quick start**](#quick-start) · [**Tools**](#the-tools) · [**The rules**](#the-rules-that-shape-the-code) · [**Docs**](#documentation)

</div>

---

## What is this?

The Wolfmix W1 is a standalone DMX lighting controller. Its projects are `.wpj`
files, and **the manufacturer does not publish that format**. So you cannot
generate a show from a script, diff two versions of a rig, or check a project
into version control in any meaningful way.

This repository is the result of taking that format apart — by reading files we
own, changing one parameter at a time in the vendor's own editor, and watching
what our own controller does on its USB link and on its DMX output.

**📄 A specification.** [`SPEC.md`](SPEC.md) describes the format byte by byte:
three container variants, 20 <!--count:record_types--> record types, the patch
model, presets, FX,
the static palettes and the USB protocol. Every claim carries an evidence
status, and [`research/evidence.md`](research/evidence.md) is the ledger it was
built from — one line per finding, refutations first.

**🛠 Tools that use it.** A container writer with a proven byte-identical round
trip, a codec that verifies its own fidelity, a show compiler and generator,
and a client for the controller's USB protocol.

> [!NOTE]
> Not an official tool, not affiliated with Wolfmix or Nicolaudie, not a
> finished product. Fields that have not been proven are **not writable**, on
> purpose — see [the rules](#the-rules-that-shape-the-code).

## Requirements

| What | Detail |
|---|---|
| **Python** | 3.10 or later, standard library only — no `pip install`, no virtualenv. CI runs 3.10 and 3.14. |
| **OS** | macOS or Linux. Only the device client is OS-sensitive (POSIX serial). |
| **A project file** | One of your own. **None ship with this repository** — [here is why](LEGAL.md). |
| **Hardware** *(optional)* | A Wolfmix W1 Mk1 on USB, with WTOOLS closed. Everything else works on files alone. |

## Quick start

```bash
git clone https://github.com/<owner>/wolfmix-automation.git
cd wolfmix-automation
```

**Bring a project of your own.** Copy — never move — a `.wpj` out of your
WTOOLS library into `corpus/projects/`, or point `WPJ_CORPUS` at wherever you
keep them. Full guide: [`docs/corpus.md`](docs/corpus.md).

**Prove the tools work on *your* files.**

```bash
make check
```

It ends with a summary — 19 <!--count:checks--> checks, and a line naming
every one that abstained.

> [!IMPORTANT]
> With no project files present, the corpus-dependent checks **abstain**. They
> say `ABSTAINED`, the summary names every one of them, and the run exits **3**
> rather than 0 — green with abstentions is not a pass. Nothing was verified,
> and they will not pretend otherwise.

**Look inside a project**, then **compile a show**. `show.json` is an edit spec
applied to a donor: the compiler refuses any field the evidence does not yet
support, and verifies its own output ([`docs/show-format.md`](docs/show-format.md)).

```bash
python3 tools/wpj_api.py corpus/projects/your-project.wpj | head -40
python3 tools/wpj_show.py compile show.json donor.wpj out.wpj
```

## The tools

Run any of them with **no arguments** to execute its self-check — except
`wolfmix.py` and `wolfmix_experiment.py`, which take it as a subcommand
(`python3 tools/wolfmix.py self-test`). The rest — the identity checker, the
diff, the position model, the readers, and the guards that keep the tree
honest — plus every flag and exit code: [`docs/tools.md`](docs/tools.md).

| Tool | One line |
|---|---|
| [`wpjlib.py`](tools/wpjlib.py) | The container: TLV split, reassembly, SHA-1 recomputed, byte-identical round trip. |
| [`wpj_codec.py`](tools/wpj_codec.py) | Semantic JSON ↔ bytes per record type; `decode` verifies its own round trip or falls back to raw hex. |
| [`wpj_show.py`](tools/wpj_show.py) | The show compiler: an edit spec applied to a donor, auto-verified. |
| [`wpj_generate.py`](tools/wpj_generate.py) | The show generator: moods, energy and groups in, a preset bank out — the rig read from the donor. |
| [`wolfmix.py`](tools/wolfmix.py) | The device: settings, projects, download, live DMX, envelopes, mode watch, preset recall. |
| [`wolfmix_experiment.py`](tools/wolfmix_experiment.py) | Transactional experiments: snapshot → deploy → verify → restore on failure. |
| [`gobo_run.py`](tools/gobo_run.py) | The gobo-icon pipeline's gates — four of them, each red until its step is really done. |

## The rules that shape the code

These five explain both what is here and what is deliberately missing.

| # | Rule | Consequence you will notice |
|---|---|---|
| 1 | **Experimental truth** | Every claim carries a status: `observed → hypothesized → correlated → validated → device-confirmed` |
| 2 | **Read before write** | A field becomes writable only after a byte-identical round trip *and* a differential validation *and* acceptance downstream |
| 3 | **Hardware is sacred** | No firmware operations, no fuzzing a connected device, dangerous functions off by default |
| 4 | **Local only** | Nothing leaves the machine — no upload, no third-party API, ever |
| 5 | **Honest compatibility** | "Compatible" means a tested cell in [`research/versions.md`](research/versions.md), nothing more |

Three properties hold at every stage of a write: unknown bytes **pass through
verbatim**, outputs open with mode `x` so a write **never overwrites**, and
nothing is stored on the controller except by the experiment runner, under its
own derived UUIDs, verified by reading it back.

## Repository map

```text
SPEC.md              the format, byte by byte, evidence status per claim
research/evidence.md the ledger: every finding, one line each
LEGAL.md · PROVENANCE.md   what is not distributed, and where the rest came from
AGENTS.md            orientation for coding agents
tools/ · tests/      the implementation, and what it refuses
docs/                task-oriented guides
corpus/              your own projects go here; ships only hashes and recipes
```

## Documentation

| Document | Read it when |
|---|---|
| [`docs/corpus.md`](docs/corpus.md) | you are starting out and need files to work on |
| [`docs/tools.md`](docs/tools.md) | you want the CLI surface, flags and exit codes |
| [`docs/show-format.md`](docs/show-format.md) · [`docs/generator.md`](docs/generator.md) | you are writing a `show.json`, or want one written from an intention |
| [`docs/device.md`](docs/device.md) | you are talking to a real controller |
| [`docs/gobo-icons.md`](docs/gobo-icons.md) | you want your fixture's real gobo shapes on the W1 screen |
| [`docs/methodology.md`](docs/methodology.md) | you want to *add* a finding, not just use one |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | something printed a message you did not expect |
| [`SPEC.md`](SPEC.md) · [`research/evidence.md`](research/evidence.md) | you need the bytes, or what measured them |
| [`LEGAL.md`](LEGAL.md) · [`PROVENANCE.md`](PROVENANCE.md) | you are reusing, forking or publishing any of this |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`SECURITY.md`](SECURITY.md) | you are sending something back |

**Reading this repository automatically?** Start with [`AGENTS.md`](AGENTS.md).

## Contributing

The bar is **evidence, not code style**: a patch that adds a field
interpretation comes with the experiment that produced it — the exact
single-variable manipulation, the hashes, the diff, and the status it reaches.
See [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`docs/methodology.md`](docs/methodology.md). One rule bears repeating: **no
project file, vendor document or extracted resource in a commit.** And
recording that something is *not* what it looked like counts as much here as
recording what it is.

## License

[MIT](LICENSE) — chosen to match `wpj-toolkit` so reuse works in both directions.

## Acknowledgements

[**gitfeber/wpj-toolkit**](https://github.com/gitfeber/wpj-toolkit) (MIT) for FX
enumerations, the preset identity formula, the palette channel order and the
inspect response shape; [**mseerig/wolfmix-web-remote**](https://github.com/mseerig/wolfmix-web-remote)
for two hardware-observed MIDI facts, cited not copied; **forum.wolfmix.com**
for staff statements, quoted with thread ids. Attributed field by field in
[`PROVENANCE.md`](PROVENANCE.md).

---

<div align="center">

<sub>Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their respective owners. This project is independent and is not affiliated with, endorsed by, or sponsored by any of them.</sub>

</div>
