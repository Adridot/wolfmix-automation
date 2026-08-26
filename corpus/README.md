# corpus/

**Empty on purpose.** No Wolfmix project or library file is distributed with
this repository — see [`../LEGAL.md`](../LEGAL.md) for what a `.wpj` actually
carries and whose it is. `.gitignore` blocks `*.wpj`, `*.wm` and `*.wmx`
repository-wide so that a stray `git add` cannot undo that.

What lives here:

| Path | What it is |
|---|---|
| `SHA256SUMS` | the hashes of the files every result in `SPEC.md` and `research/` was measured on — provenance without redistribution |
| `experiments/*/build.py`, `experiments/*/show.json` | our own edit recipes, kept as worked examples |
| `projects/` | where you drop your own projects — see [`../docs/corpus.md`](../docs/corpus.md) |

The build scripts and specs still name the donor files they were run against.
Those donors are not here; the paths are part of the record, not an instruction
to go looking. Point them at a project of your own to re-run one.
