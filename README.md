<div align="center">

# wolfmix-automation

**Read, decode, diff and rebuild Wolfmix `.wpj` project files — and drive a Wolfmix W1 over USB — from the command line.**

*Offline. Python standard library only. No dependencies, no uploads, no guessing.*

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.x%20stdlib%20only-3776AB.svg)](#requirements)
[![Firmware](https://img.shields.io/badge/W1%20Mk1%20fw-2.0.18-orange.svg)](research/versions.md)
[![WTOOLS](https://img.shields.io/badge/WTOOLS-1.6.3-lightgrey.svg)](research/versions.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg)](#requirements)
[![Status](https://img.shields.io/badge/status-research-yellow.svg)](#where-the-format-stands)

[**What is this?**](#what-is-this) ·
[**Quick start**](#quick-start) ·
[**How it works**](#how-it-works) ·
[**Format status**](#where-the-format-stands) ·
[**Docs**](#documentation) ·
[**FAQ**](#faq)

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

It gives you two things:

|  | |
|---|---|
| 📄 **A specification** | [`SPEC.md`](SPEC.md) — the `.wpj` format byte by byte. 3 container variants, 20 record types, the patch model, presets, FX, the static palettes. **Every claim carries its evidence status and the experiment that produced it.** |
| 🛠 **Tools that use it** | A container writer with a proven byte-identical round-trip, a codec that verifies its own fidelity, a show compiler, and a client for the controller's USB protocol. |

> [!NOTE]
> **What this is not.** Not an official tool, not affiliated with Wolfmix or
> Nicolaudie, and not a finished product. It is careful research with runnable
> proofs attached. Fields that have not been proven are not writable, on
> purpose — see [the rules](#the-rules-that-shape-the-code).

## Requirements

| | |
|---|---|
| **Python** | 3.x, standard library only — no `pip install`, no virtualenv. Developed on 3.14. |
| **OS** | macOS or Linux. Only the device client is OS-sensitive (POSIX serial). |
| **A project file** | One of your own. **None ship with this repository** — [here is why](LEGAL.md). |
| **Hardware** *(optional)* | A Wolfmix W1 Mk1 on USB, with WTOOLS closed. Everything else works on files alone. |

## Quick start

### 1 · Get the code

```bash
git clone https://github.com/Adridot/wolfmix-automation.git
cd wolfmix-automation
```

### 2 · Bring a project of your own

```bash
mkdir -p corpus/projects
cp ~/Library/Application\ Support/WTOOLS/wlinkData/projects/*.wpj corpus/projects/
```

<details>
<summary>No WTOOLS install? Pull one straight off the controller</summary>

```bash
python3 tools/wolfmix.py projects                       # list what is on the W1
python3 tools/wolfmix.py project <UUID> corpus/projects/mine.wpj
```

This is a read. Nothing is written to the device. Keep WTOOLS closed — the
serial port is exclusive.

</details>

Copies only — never work on the originals. Full guide: [`docs/corpus.md`](docs/corpus.md).

### 3 · Prove the tools work on *your* files

```bash
make check
```

```text
self-check ok : round-trip octet-identique sur 25 fichiers
fidélité octet vérifiée sur 25 fichiers variante A
2 identités vérifiées sur 25 fichiers variante A
```

Six self-checks: byte-identical round-trip, codec fidelity per record type,
wire parsing, the show compiler, the inspect API, and the structural identities.

> [!IMPORTANT]
> With no project files present, the self-checks **abstain** — one line each,
> exit code 0. Nothing was verified, and they will not pretend otherwise.

### 4 · Look inside a project

```bash
python3 tools/wpj_api.py corpus/projects/your-project.wpj | head -40
```

<details>
<summary>What comes out (trimmed)</summary>

```jsonc
{
  "modelVersion": "1",
  "project": { "name": "MY SHOW", "warnings": [],
               "known": { "colorFxPalette": { "pads": [ { "index": 1, "red": 255 } ] } } },
  "presets": [
    { "id": 33, "page": 2, "slot": 14, "name": "Chaser", "rawPreserved": true,
      "known": { "colorFx1": { "type": 2, "speedPercent": 120, "linkOrder": 10 } } }
  ],
  "fixtures": { "status": "partial",
                "items": [ { "profil": 57, "adresse": 44, "fixture": 7, "nb_canaux": 4 } ] },
  "validation": {
    "checksumOk": true,
    "issues": [
      { "severity": "info", "code": "checksum_ok",
        "message": "SHA-1 header over bytes[20:] verified" },
      { "severity": "warning", "code": "unconfirmed_field_attribution",
        "message": "field attribution still hypothesized: fadePercent, phasePercent, sizePercent" }
    ]
  },
  "unknown_tlvs": [ { "type": 106, "payloadLength": 600, "rawPreserved": true } ]
}
```

Same response shape as the `wpj-toolkit` inspect schema, computed locally so
tooling written against it works offline. Note the second issue: attributions
that are **still hypotheses are emitted with a warning attached**, never as
plain values. `x_records` (omitted above) carries the full codec decode so
nothing is lost.

</details>

### 5 · Compile a show

Editing always starts from a donor project. Nothing is synthesised from scratch.

```jsonc
// show.json
{
  "base": "corpus/projects/your-project.wpj",
  "nom": "MY SHOW",
  "presets": [
    { "id": 33, "nom": "Chaser", "color_fx1": { "effet": 2, "vitesse": 120 } }
  ],
  "positions": [
    { "page": 1, "index": 0, "nom": "Public", "pan": 32768, "tilt": 15073 }
  ]
}
```

```bash
python3 tools/wpj_show.py compile show.json out.wpj
```

The compiler refuses any key outside what has been proven, writes to a **new**
file, then reloads its own output and checks that every requested value reads
back and that **nothing else moved**. Key reference: [`docs/show-format.md`](docs/show-format.md).

## How it works

```mermaid
flowchart LR
    A["show.json<br/>your edits"] --> B["wpj_show.py<br/>validates,<br/>refuses the unproven"]
    D["donor .wpj<br/>one of yours"] --> B
    B --> C["wpj_codec.py<br/>JSON to bytes,<br/>fidelity self-checked"]
    C --> E["wpjlib.py<br/>TLV container,<br/>SHA-1 recomputed"]
    E --> F["new .wpj<br/>auto-verified"]
    F -.-> G(["WTOOLS / W1<br/>your call, always"])
```

Three properties hold at every stage:

1. **Unknown bytes pass through verbatim.** A record with no schema is
   re-emitted exactly as it came in. The codec proves this on your whole corpus
   before it will run.
2. **Writes never overwrite.** Every output opens with mode `x`; an existing
   path is an error, not a target.
3. **Nothing is written to the controller** except by the experiment runner,
   and then only to its own UUIDs, verified by reading them back.

## What's in the box

| Tool | One line |
|---|---|
| [`wpjlib.py`](tools/wpjlib.py) | The container. TLV split, reassembly, SHA-1 recomputed, byte-identical round-trip. |
| [`wpj_codec.py`](tools/wpj_codec.py) | Semantic JSON ↔ bytes per record type. `decode` verifies its own round-trip or falls back to raw hex. |
| [`wpj_identities.py`](tools/wpj_identities.py) | Arithmetic identities between records — refutes a wrong reading without touching hardware. |
| [`wpj_show.py`](tools/wpj_show.py) | The show compiler: an edit spec applied to a donor, auto-verified. |
| [`wpj_api.py`](tools/wpj_api.py) | Inspect JSON in the `wpj-toolkit` schema shape, local and offline. |
| [`wpj_inspect.py`](tools/wpj_inspect.py) | Protobuf wire walk for variants B/C. Exits 2 rather than guess. |
| [`wpj_diff.py`](tools/wpj_diff.py) | Byte-range diff — the first command of every experiment. |
| [`wolfmix.py`](tools/wolfmix.py) | The device: settings, projects, download, live DMX, mode watch. |
| [`wolfmix_experiment.py`](tools/wolfmix_experiment.py) | Transactional experiments: snapshot → deploy → verify → restore on failure. |

Run any of them with **no arguments** to execute its self-check.

## Where the format stands

| Area | State |
|---|---|
| Variant-A container, SHA-1 header, project name | 🟢 **device-confirmed** — our files are accepted and stored byte-identically |
| Record inventory — 20 types | 🟢 13 decoded, 7 round-tripped verbatim |
| Patch model (105/106/110/111/115/116/120/125) | 🟢 locked by arithmetic identities, addresses confirmed on live DMX |
| Static palettes — colour, gobo, position (140/145/150) | 🟢 **device-confirmed**, one record per group A–H |
| FX sequences (155) | 🟢 decoded — 16 steps × 8 groups |
| Presets and FX (165) | 🟡 effect type device-confirmed; `size`/`fade`/`phase` still hypotheses |
| Flash FX settings (102) | 🟡 closed end to end except three fields — one of them **refuted as inert** |
| UI mode enum (`WM_MODE_*`) | 🟡 26+ values measured on the device, not read out of a binary |
| Variants B and C | 🔴 top level only — read-only by rule |
| MIDI mapping record | 🔴 not located — the gateway to live control |

<details>
<summary><b>A worked example: the gobo palette is not stored, it is derived</b></summary>

Record 145 looked like 20 stored gobo slots per group. It is not. Its image ids
are exactly the `f4` values of record 111's gobo-wheel ranges, in wire order —
so **the palette is generated from the patch**. Two consequences:

- the identity is checkable on any corpus, forever, by `wpj_identities.py`;
- it predicts DMX. Pressing pad *n* should drive the group's gobo channel to
  the **lower bound** of range *n*. Measured: pad 1 → 7, pad 10 → 70, and
  nothing else moved in 2048 channels.

That is the standard this repository holds itself to: a reading that predicts
an observation, then the observation.

</details>

## The rules that shape the code

These five explain both what is here and what is deliberately missing.

| # | Rule | Consequence you will notice |
|---|---|---|
| 1 | **Experimental truth** | Every claim carries a status: `observed → hypothesized → correlated → validated → device-confirmed` |
| 2 | **Read before write** | A field becomes writable only after a byte-identical round-trip *and* a differential validation *and* acceptance downstream |
| 3 | **Hardware is sacred** | No firmware operations, no fuzzing a connected device, dangerous functions off by default |
| 4 | **Local only** | Nothing leaves the machine — no upload, no third-party API, ever |
| 5 | **Honest compatibility** | "Compatible" means a tested cell in [`research/versions.md`](research/versions.md), nothing more |

## Repository map

```text
SPEC.md            the format, byte by byte, with evidence status per claim
LEGAL.md           what is not distributed here, and why
PROVENANCE.md      sources, licences, what may be reused from where
AGENTS.md          orientation for coding agents and automated contributors
tools/             the implementation — stdlib only, self-checking
docs/              task-oriented guides (corpus, tools, show format, device…)
research/          the working log, in French — one write-up per experiment
corpus/            where you drop your own projects; ships only SHA256SUMS
```

> [!TIP]
> **Where the truth lives.** `research/` is the lab notebook and always leads.
> `SPEC.md` is the consolidated, English-language read of it. When the two
> disagree, `research/` is newer — and that gap is itself recorded.

## For AI agents

Reading this repository automatically? Start with [`AGENTS.md`](AGENTS.md): it
states the invariants, the one command that proves the tree is healthy, the
vocabulary of evidence, and the actions that are refused here. Then
[`SPEC.md`](SPEC.md) for the format and [`docs/tools.md`](docs/tools.md) for the
interfaces. The self-checks are the ground truth — if `make check` passes on a
real corpus, the structural claims hold.

## FAQ

<details>
<summary><b>Do I need a Wolfmix W1?</b></summary>

No. Everything except `wolfmix.py` and `wolfmix_experiment.py` works on files
alone. You do need a project file of your own to point the tools at.

</details>

<details>
<summary><b>Why don't you ship a sample project?</b></summary>

Because a `.wpj` is not ours to give away. About 70 of the ~78 printable
strings in one are byte-identical across unrelated rigs — the manufacturer's
factory presets, macros and position names. Every file also embeds fixture
profile data from the vendor's library, plus somebody's real show. There is no
"small clean" project file. Full reasoning: [`LEGAL.md`](LEGAL.md).

</details>

<details>
<summary><b>Why does <code>make check</code> say it verified nothing?</b></summary>

Because you have no corpus yet — see [`docs/corpus.md`](docs/corpus.md). An
abstention is reported as an abstention. The alternative would be a green tick
that means nothing.

</details>

<details>
<summary><b>Why can't I edit field X?</b></summary>

Because it has not been proven yet. The compiler covers records 101, 165, 150
and 135, and only keys at status `correlated` or better. `size`/`fade`/`phase`
are readable but not writable. See [`SPEC.md`](SPEC.md) §10–11.

</details>

<details>
<summary><b>What are the three file variants?</b></summary>

**A** — SHA-1 + a TLV container (root type 100). The device/WLINK-side format,
and the only one writable here.
**B** — SHA-1 + bare protobuf. Most current WTOOLS projects.
**C** — bare protobuf, no digest. Older.
Details in [`SPEC.md`](SPEC.md) §1.

</details>

<details>
<summary><b>Does anything get uploaded to a hosted service?</b></summary>

No. `wpj_api.py` reproduces that schema's *response shape* locally so tooling
written against it works offline. Calling a third-party decoder would break
both the local-only rule and the evidence chain. See [`PROVENANCE.md`](PROVENANCE.md).

</details>

<details>
<summary><b>Is the W1 Mk2 supported?</b></summary>

Untested. External work suggests Mk2 files use our variant A container, but
nothing measured here is Mk2, so no claim is made.

</details>

<details>
<summary><b>Why is the research in French?</b></summary>

Deliberately — `research/` is the author's lab notebook. `SPEC.md`, `LEGAL.md`,
`PROVENANCE.md`, `docs/` and this README are English. Some tool output strings
are still French.

</details>

## Roadmap

| | Item |
|---|---|
| ✅ | Variant-A writer with a byte-identical round-trip, device-confirmed |
| ✅ | Record inventory, patch model, preset/FX sub-message |
| ✅ | Static colour / gobo / position palettes, FX sequences |
| ✅ | Template-based show compiler, transactional device experiment runner |
| 🔜 | `size`/`fade`/`phase` attribution — one clean experiment each |
| 🔜 | Record 102 `f5`/`f6`/`f11` — three unattributed values, highest value per unit of effort |
| 🔮 | The MIDI mapping record — live control |
| 🔮 | Variant B/C writer, fixture profile generation |

## Documentation

| Document | Read it when |
|---|---|
| [`docs/corpus.md`](docs/corpus.md) | you are starting out and need files to work on |
| [`docs/tools.md`](docs/tools.md) | you want the CLI surface, flags and exit codes |
| [`docs/show-format.md`](docs/show-format.md) | you are writing a `show.json` |
| [`docs/device.md`](docs/device.md) | you are talking to a real controller |
| [`docs/methodology.md`](docs/methodology.md) | you want to *add* a finding, not just use one |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | something printed a message you did not expect |
| [`SPEC.md`](SPEC.md) | you need the bytes |
| [`LEGAL.md`](LEGAL.md) · [`PROVENANCE.md`](PROVENANCE.md) | you are reusing, forking or publishing any of this |

## Contributing

The bar here is **evidence, not code style**. A patch that adds a field
interpretation comes with the experiment that produced it: the exact
single-variable manipulation, the before/after hashes, the diff, and the status
it reaches. [`docs/methodology.md`](docs/methodology.md) walks through it.

Ground rules for any patch:

- standard library only — no new dependencies;
- `make check` passes, and the byte-identical round-trip still holds;
- unknown bytes stay verbatim;
- **no project file, vendor document or extracted resource in a commit.**
  `.gitignore` is there to catch it; do not work around it.

Recording that something is *not* what it looked like is as valuable here as
recording what it is.

## License

[MIT](LICENSE) — chosen to match `wpj-toolkit` so reuse works in both directions.

## Acknowledgements

- [**gitfeber/wpj-toolkit**](https://github.com/gitfeber/wpj-toolkit) (MIT) — FX
  enumerations, the preset identity formula, the palette channel order and the
  inspect response shape, attributed field by field in [`PROVENANCE.md`](PROVENANCE.md).
- [**mseerig/wolfmix-web-remote**](https://github.com/mseerig/wolfmix-web-remote)
  — two hardware-observed MIDI facts, cited only, not copied.
- **forum.wolfmix.com** — staff and user statements, quoted with thread ids.

---

<div align="center">
<sub>

Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their respective owners.<br>
This project is independent and is not affiliated with, endorsed by, or sponsored by any of them.

</sub>
</div>
