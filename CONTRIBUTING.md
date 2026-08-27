# Contributing

The bar here is **evidence, not code style**. This repository documents a file
format nobody publishes; its only value is that every claim in it can be
traced back to something that was actually measured. A patch is judged on
whether it keeps that true.

Read [`docs/methodology.md`](docs/methodology.md) first — it is short, and it is
the whole method.

## Before you open anything

- Run `make check` from the repository root. Nine self-checks; they need a
  corpus of your own ([`docs/corpus.md`](docs/corpus.md)).
- If they abstain (`ignoré, aucun corpus`), nothing was verified. That is not a
  pass.

## Adding or correcting a format claim

Open an issue with the **Format finding** template, or a PR carrying the same
information:

1. **The manipulation** — exactly one variable changed, described so someone
   else can repeat it.
2. **The evidence** — `tools/wpj_diff.py` output, DMX capture, or the device
   screen you read it from. Hashes of the before/after files, **never the files
   themselves**.
3. **The versions** — controller model and firmware, WTOOLS version, OS.
4. **The status reached**, from the ladder in
   [`SPEC.md`](SPEC.md): `observed → hypothesized → correlated → validated →
   device-confirmed`. Say why it does not reach the next one.

A refutation is a contribution. Several entries in `research/` exist only to
record that something is *not* what it looked like, and they saved more time
than the confirmations.

## Rules any patch must respect

| Rule | Why |
|---|---|
| Standard library only | No dependency has ever been needed; adding one costs every user. |
| `make check` passes, byte-identical round-trip intact | It is the acceptance test, not a formality. |
| Unknown bytes stay verbatim | A record with no schema must round-trip exactly. Never emit a partial decode. |
| No invented names for unconfirmed values | Ambiguity is recorded as a list of candidates. An absent field is *absent*, never `0`. |
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
