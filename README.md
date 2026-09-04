<div align="center">

<img src="docs/assets/banner.svg" alt="wolfmix-automation — the Wolfmix .wpj format, byte by byte" width="880">

# wolfmix-automation

Reader: New users and contributors. Question: Where do I start, and where is each authoritative answer?

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
git clone https://github.com/Adridot/wolfmix-automation.git
cd wolfmix-automation
```

**Bring a project of your own.** Copy — never move — a `.wpj` out of your
WTOOLS library into `corpus/projects/`, or point `WPJ_CORPUS` at wherever you
keep them. Full guide: [`docs/corpus.md`](docs/corpus.md).

**Prove the tools work on *your* files.**

```bash
make check
```

It ends with a summary — 21 <!--count:checks--> checks, and a line naming
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

The [tool reference](docs/tools.md) groups the stable `tools/*.py` commands
by format, composition, device, resources and verification. It documents
arguments, output and exit codes. Run `make check` for the aggregate gate;
USB clients use an explicit `self-test` subcommand.

## The rules that shape the code

These five explain both what is here and what is deliberately missing.

| # | Rule | Consequence you will notice |
|---|---|---|
| 1 | **Experimental truth** | Use the [evidence rules](SPEC.md#evidence-rules) and record the measurement in the ledger |
| 2 | **Read before write** | A field becomes writable only after a byte-identical round trip *and* a differential validation *and* acceptance downstream |
| 3 | **Hardware is sacred** | No executable-firmware operations, no fuzzing; the resource uploader accepts only a manifest-verified gobo diff and is off by default |
| 4 | **Local only** | Nothing leaves the machine — no upload, no third-party API, ever |
| 5 | **Honest compatibility** | "Compatible" means a tested cell in [`research/versions.md`](research/versions.md), nothing more |

The [writing rules](SPEC.md#10-writing-rules) govern file preservation and
verification; [device transactions](docs/device.md) govern stored projects.
Rule 2 above is deliberately stricter than the compiler's `correlated` threshold:
it describes the downstream acceptance standard, not the complete writable-key
list. Consult the [edit specification](docs/show-format.md) for that list.

## Repository map

The [documentation map](#documentation) is the entry point. `tools/` contains
the executable proof, `tests/` the corpus-free refusal checks, and `corpus/`
your private specimens plus published hashes and experiment recipes.

## Documentation

Reader: choose the row matching your task. Question: where is the authoritative
answer, and what evidence supports it?

Navigation follows [Diátaxis](https://diataxis.fr/start-here/): learning,
practical tasks, reference and explanation. Existing paths remain stable.
The current byte-level claim belongs in `SPEC.md`; guides link to it. Historical
measurements remain in `research/` and the frozen experiments rather than being
rewritten to agree with today's interpretation.

| Need | Reader's question | Direct destination |
|---|---|---|
| Tutorial | How do I run my first check and inspect a project? | [Quick start](#quick-start) |
| How-to | Where do I get my own specimens? | [Corpus](docs/corpus.md) |
| How-to | How do I operate the USB client safely? | [Device](docs/device.md) |
| How-to | How do I replace gobo icons and recover? | [Gobo icons](docs/gobo-icons.md) |
| How-to | What should I do about this error? | [Troubleshooting](docs/troubleshooting.md) |
| Reference | What are the commands and module groups? | [Tools](docs/tools.md) |
| Reference | What can I put in an edit specification? | [Show format](docs/show-format.md) |
| Reference | How do I describe moods and energy? | [Generator input](docs/generator.md) |
| Reference | What do the bytes mean, at what proof status? | [WPJ specification](SPEC.md) |
| Reference | How are fixture profiles encoded? | [SSL2 format](docs/ssl2-format.md) |
| Explanation | How do I establish or retract a finding? | [Methodology](docs/methodology.md) |
| Evidence | What was measured, and what was withdrawn? | [Evidence ledger](research/evidence.md) |
| Evidence | Which software and firmware were tested? | [Versions](research/versions.md) |
| Evidence | What is the record-120 defect and its reproduction? | [Historical bug report](docs/report-record-120.md) |
| Provenance | What may be reused, and where did it come from? | [Legal](LEGAL.md), [Provenance](PROVENANCE.md) |
| Contribution | How do I contribute or report a security issue? | [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), [Code of conduct](CODE_OF_CONDUCT.md) |
| Automation | What instructions govern repository changes? | [Agent instructions](AGENTS.md) |
| Assets | What artwork belongs to the documentation? | [Asset notes](docs/assets/README.md) |

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
