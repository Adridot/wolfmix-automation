# Bringing your own corpus

No Wolfmix project file ships with this repository, and none ever will — see
[`../LEGAL.md`](../LEGAL.md) for why. Every tool therefore works against a
corpus **you** supply, from your own installation and your own controller.

> [!CAUTION]
> Nothing of the sort is distributed here. This step is yours to run, and what
> it leaves on your disk stays on your disk.

Everything below stays local. No tool in this repository uploads anything.

## Where your projects already are

WTOOLS keeps the projects it has synchronised on your machine:

```
macOS    ~/Library/Application Support/WTOOLS/wlinkData/projects/
```

Those are the originals. **Copy them, do not work on them in place** — this is
the whole point of a frozen corpus, and no tool here is allowed to touch that
directory on its own.

```bash
mkdir -p corpus/projects
cp ~/Library/Application\ Support/WTOOLS/wlinkData/projects/*.wpj corpus/projects/
```

## Or pull one straight off the controller

With the W1 on USB and WTOOLS closed:

```bash
python3 tools/wolfmix.py projects
python3 tools/wolfmix.py project <UUID> corpus/projects/mine.wpj
```

This is a read: the controller is asked for a project and the bytes are written
to a new local file. Nothing is written to the device.

## Telling the tools where it is

The default corpus root is `corpus/` under the repository. Point somewhere else
with an environment variable:

```bash
WPJ_CORPUS=~/wolfmix-corpus make check
```

The tools glob `**/*.wpj` under that root, skip anything that is not a
variant-A file, and never write into it.

## What "no corpus" looks like

Self-checks abstain rather than fail:

```
wpjlib : ignoré, aucun corpus dans corpus/ (voir docs/corpus.md)
```

`make check` still exits 0. That is honest — it means nothing was verified, not
that everything passed. With a corpus present you get the real thing:

```
self-check ok : round-trip octet-identique sur 25 fichiers
fidélité octet vérifiée sur 25 fichiers variante A
2 identités vérifiées sur 25 fichiers variante A
```

## What makes a good corpus

Rough order of value:

1. **Two or more unrelated rigs.** A claim that holds across independent
   projects means something; the same claim across five saves of one project
   means almost nothing. See [`methodology.md`](methodology.md).
2. **A project with moving heads**, if you want the gobo and position palettes
   (records 145/150) to carry anything.
3. **Before/after pairs** from single-variable edits — the actual engine of
   this research.
4. Variant B/C files (larger, protobuf without the TLV container) if you want
   to work on `wpj_inspect.py`. Most current WTOOLS projects are variant B.

## Keeping it out of git

`.gitignore` already excludes `*.wpj`, `*.wm`, `*.wmx`, `corpus/**/dmx/` and
`.wolfmix-state/`. Leave those rules alone. If you fork this repository to
publish your own findings, publish the **write-up and the hashes**, not the
files: `corpus/SHA256SUMS` is the model — it identifies exactly what was
measured without shipping a byte of it.
