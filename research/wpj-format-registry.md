# Format registry — index

This file held **8 293 lines** of running lab notebook: every reading of the
`.wpj` format from 2026-08-25 to 2026-08-31, in the order it happened, with the
predictions, the arguments and the corrections in between.

It is not deleted, it is **replaced**, and the difference matters. The full
text is one command away:

```bash
git log --diff-filter=M --oneline -- research/wpj-format-registry.md | tail -1
git show <that commit>^:research/wpj-format-registry.md | less
```

Nothing was thrown away — the reasoning is in git, where a notebook belongs,
and what the tree carries now is the part a reader needs:

| You want | Read |
|---|---|
| What is known about the format, by record and field | [`../SPEC.md`](../SPEC.md) |
| What was done to learn it, one line per finding | [`evidence.md`](evidence.md) |
| The refutations and the status downgrades, in full | [`evidence.md`](evidence.md), first section |
| What is still open | [`../SPEC.md`](../SPEC.md) §11 |
| Where an external claim came from | [`../PROVENANCE.md`](../PROVENANCE.md) |

## Why it was replaced

A notebook and a specification want opposite things. The notebook is
chronological and never rewritten — a refuted prediction stays exactly as
published, which is what makes it worth anything. The specification is
organised by subject and is rewritten every time a reading improves.

Keeping both in one 8 293-line file meant the specification competed with its
own history for the reader, and lost: `SPEC.md` §11 carried ten leads that had
closed days earlier, because the file that would have told you was too long to
re-read. The ledger fixes the part a person actually needs — *what was measured
and what came of it* — in a form small enough to check.

**Every finding id still resolves.** `make check` fails if a citation anywhere
in the tree names an id with no entry in [`evidence.md`](evidence.md), so this
replacement cannot silently orphan a reference.

## The one thing that did not survive intact

The registry contained the argument for each reading — why a rival was
dismissed, what the probabilities were before a shot, which sentence turned out
to be the expensive one. The ledger keeps the *result* and, for refutations,
the reason. If you are re-deriving one of these findings rather than using it,
read the original in git: it is longer for a reason.
