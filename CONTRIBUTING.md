# Contributing

Reader: Contributors. Question: What evidence and checks must accompany a contribution?

The bar here is **evidence, not code style**. This repository documents a file
format nobody publishes; its only value is that every claim in it can be
traced back to something that was actually measured. A patch is judged on
whether it keeps that true.

Read [`docs/methodology.md`](docs/methodology.md) first — it is short, and it is
the whole method.

## Before you open anything

- Run `make check` from the repository root — it runs every hardware-free
  self-check, and [`tools/check.py`](tools/check.py) is the canonical list.
  Some of them need a corpus of your own ([`docs/corpus.md`](docs/corpus.md)).
- Exit **0** = everything passed. Exit **3** = green, but something abstained:
  the summary names it, and nothing it covers was verified. That is not a pass.
  Exit **1** = something failed.
- CI runs the same gate on a clone with no corpus, on Python 3.10 and 3.14, so
  a change that only works with your project files fails there. It passes
  `--abstentions-ok` because that context expects them — the summary still
  names every one.

## The ledger, and the spec

Findings go in [`research/evidence.md`](research/evidence.md) — one line each,
with the date of the **measurement**. `SPEC.md` is allowed to lag behind it and
says so in its evidence cutoff; it is not allowed to contradict it. Adding a
finding dated after the cutoff means either consolidating it into `SPEC.md` in
the same change, or naming it in the pending list. `make check` decides.

## Adding or correcting a format claim

Open an issue with the **Format finding** template, or a PR carrying the same
information:

1. **The manipulation** — exactly one variable changed, described so someone
   else can repeat it.
2. **The evidence** — `tools/wpj_diff.py` output, DMX capture, or the device
   screen you read it from. Hashes of the before/after files, **never the files
   themselves**.
3. **The versions** — controller model and firmware, WTOOLS version, OS.
4. **The status reached**, using [SPEC's evidence rules](SPEC.md#evidence-rules).
   Say why it does not reach the next one.

A refutation is a contribution. Several entries in `research/` exist only to
record that something is *not* what it looked like, and they saved more time
than the confirmations.

## Rules any patch must respect

| Rule | Why |
|---|---|
| Standard library only | No dependency has ever been needed; adding one costs every user. |
| `make check` passes, byte-identical round-trip intact | It is the acceptance test, not a formality. |
| Preserve the [writing rules](SPEC.md#10-writing-rules) | Round-trip verification must include unknown bytes and untouched records. |
| Follow the [evidence rules](SPEC.md#evidence-rules) | Keep uncertainty and absent values explicit. |
| Fields below `correlated` are not writable | That is why `size`/`fade`/`phase` are readable only. |
| **No project file, vendor document or extracted resource in a commit** | See [`LEGAL.md`](LEGAL.md). `.gitignore` catches the common cases; do not work around it. |

New non-trivial logic leaves one runnable check behind — a `demo()` guarded by
`__main__`, in the style of the existing tools. No test framework.

## Language

`research/` is the author's lab notebook and is in French. `SPEC.md`,
`LEGAL.md`, `PROVENANCE.md`, `docs/`, `README.md` and this file are in English.
Contribute in either; do not mass-translate the other.

## Automated contributors

If you are running an agent against this repository, start with
[`AGENTS.md`](AGENTS.md). Everything above still applies, and the invariants are
not negotiable because a model finds them inconvenient.
