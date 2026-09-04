# AGENTS.md

Reader: Coding agents. Question: Which invariants and sources govern a change?

Orientation for coding agents and automated contributors. Humans: this is a
condensed version of [`README.md`](README.md) + [`docs/methodology.md`](docs/methodology.md).

## What this repository is

Reverse-engineering of the Wolfmix `.wpj` project file format, plus tools that
read and write it, plus a client for the W1 controller's USB protocol. Python
**3.10 or later**, **standard library only** — the floor is measured, and
[`.github/workflows/check.yml`](.github/workflows/check.yml) runs the gate on
3.10 and 3.14 on a clone with no corpus. The deliverable is trustworthy knowledge:
[`SPEC.md`](SPEC.md) is the product, `tools/` is its executable proof.

## The one command

```bash
make check          # from the repository root — every hardware-free self-check
```

Green means the structural claims hold on the corpus present — **file-format
code, `gobo_run.py`'s filesystem gates, `wolfmix_transaction.py`'s archive and
rollback guards, which run against a fake link, and the `tests/` suite, which
builds its own bytes and therefore proves the same thing on a bare clone**. No port is ever opened:
`wolfmix.py` and `wolfmix_experiment.py` are deliberately absent from the
list, which lives in [`tools/check.py`](tools/check.py). Their hardware-free
checks are separate subcommands: `python3 tools/wolfmix.py self-test` and
`python3 tools/wolfmix_experiment.py self-test`.

The run ends with a summary, and the exit code carries the distinction: **0**
every check passed, **3** green but at least one check verified nothing, **1**
something failed. A check with no corpus prints `ABSTAINED` and is named in
the summary — no project files ship with this repository (see below). Do not
read an abstention as a pass, and do not "fix" it by inventing test data.

## Hard invariants — do not break these

| Invariant | Why |
|---|---|
| **No new dependencies.** Standard library only. | Portability, and the ability to audit every line. |
| **Never commit `*.wpj`, `*.wm`, `*.wmx`, `*.pdf`, vendor extractions (`research/vendor/`), USB/serial captures, DMX captures (`corpus/**/dmx/`, `.wolfmix-state/`), or the local `.wpj-private-names` list.** | They carry the manufacturer's factory content, device identifiers or someone's real show — [`LEGAL.md`](LEGAL.md). `.gitignore` enforces it; never work around it with `git add -f`. |
| **Never write a real venue, client, project, group or device name into a tracked file.** Use the neutral labels the tree already uses: `rig-a`/`rig-b`/`rig-c`, `<group-A name>`, serial withheld. | `make check` fails on it — `tools/wpj_privacy.py` greps every tracked file against a list that lives outside the repository. This is the invariant most often broken by accident, including by writing a new research section. |
| **Unknown bytes pass through verbatim.** | A record with no schema round-trips exactly. `wpj_codec.decode` returns `{"raw": hex}` rather than a partial decode. |
| **Writes never overwrite.** Output opens with mode `x`. | An overwritten project is an unrecoverable show. |
| **Nothing leaves the machine.** No upload, no third-party API, no telemetry. | Rule 4, and the evidence chain depends on it. |
| **No executable-firmware operations, ever.** The outgoing event allowlist in `tools/wolfmix.py` is exhaustive by design. Event `0x19` is never allowlisted and no code path accepts or uploads `wolfmixFirmware.bin`. | A bricked controller is not recoverable from here. |
| **A resource flash is not firmware.** `wolfmixFlash.bin` carries the interface's graphics. A patched copy may be uploaded only by `wolfmix.py gobo-upload`, after a manifest-verified backup, exact source/result hashes, an operator-reviewed sheet and a byte diff confined to the declared gobo windows. Arbitrary flash images are refused. | The dedicated resource event `0x24` and executable-firmware event `0x19` are distinct in the measured WTOOLS interface; see [`LEGAL.md`](LEGAL.md). |
| **Do not write to a connected device** except through `wolfmix_experiment.py`, which uses its own derived UUIDs, or the guarded `gobo-upload` resource path above. | Ordinary projects and arbitrary device memory must never be touched. |
| **Never invent a name for an unconfirmed value.** | Ambiguity is recorded as a list of candidates. An absent field is *absent*, never `0` or `off`. |

## Evidence vocabulary

Use [SPEC's evidence rules](SPEC.md#evidence-rules) and
[methodology](docs/methodology.md#evidence-statuses). Never silently promote a
claim, resolve candidates by guessing, or turn absence into a value.

The code permits writing at `correlated` or better; README rule 2 deliberately
states the stricter downstream acceptance standard. Preserve that distinction
and the [actual writable surface](docs/show-format.md).

## Where truth lives

```text
research/evidence.md   the ledger: every finding, one line each — date, what
                 was done, what came out, the status it ended at. Refutations
                 and status downgrades are written out in full at the top.
                 Every id cited anywhere in the tree must resolve to an entry;
                 `make check` fails when one does not.
research/        the lab notebook. ALWAYS the most current. Historical
                 observations retain their evidence status when translated.
SPEC.md          the consolidated English read of research/. May lag.
docs/            task-oriented guides for users.
tools/           the implementation. Self-checks are the ground truth.
tests/           boundary tests: what is refused, and what never reaches
                 the wire. Corpus-free, and not stripped by `python3 -O`.
```

When `SPEC.md` and `research/` disagree, `research/` is newer — and that gap is
itself worth recording rather than silently resolving. `SPEC.md` declares an
**evidence cutoff** and a **pending list** for exactly that, and
`tools/wpj_evidence.py` refuses a tree where the specification has fallen
behind without saying so, points at a section that does not exist, or leans on
a finding the ledger has taken back.

## Conventions you will notice

### Architecture to preserve on every change

- Keep existing `tools/*.py` command paths and import names stable: frozen
  experiment recipes depend on them. Use the five [module groups](docs/tools.md#module-groups),
  and declare the owning group and reference near the module's opening.
- Put shared wire operations in `wpj_wire`, schema operations in `wpj_codec`,
  and project IO in `wpjlib`. Trace callers before extracting a duplicate;
  preserve their validation, error types, encoding order and unknown bytes.
  Keep `wpj_inspect` independent. Do not create a third reader, generic utility
  package, wrapper CLI or dependency without an actual need.
- Annotate public module functions and class methods, including magic methods,
  using Python 3.10-compatible types. Preserve missing values explicitly.
  An annotation is documentation, not runtime validation or proof of correctness.
- Give maintained documentation a `Reader:` and `Question:` introduction and a
  direct README link. Put the current measured WPJ claim in `SPEC.md` and link
  to its stable anchor from guides. Keep command/input contracts in their own
  references; preserve historical measurements and their proof statuses.
- After a change, run `make check`; for parsing, validation or guard changes,
  also run `python3 -O -m unittest discover -s tests -t .`. Exercise changed
  USB clients only with their explicit hardware-free `self-test` commands.
  A final refactor check also runs `tools/check.py --abstentions-ok` in a local
  clone without private corpus or names. Keep abstentions visible.
- Review the diff for unintended behavior, evidence promotions and changed
  corpus/prediction files. Stage named source/document paths, inspect the staged
  diff and privacy result, then make a small thematic commit. Push only when
  the operator has authorized publishing; never add ignored artifacts.
- Keep task notes outside tracked documentation, including the baseline,
  decisions, preserved contract differences and claim-to-source moves. Re-read
  them at each stage; do not turn an implementation log into a new source of
  format facts.

### Existing conventions

- **Language:** write all repository content in English: documentation, code
  identifiers, comments, docstrings, diagnostics, CLI help, examples and agent
  instructions. Review every added or changed line for this requirement.
  Conversations with the operator remain in French. Translate prose without
  changing measured values, hashes, evidence IDs or statuses. A translation
  supplies no new evidence. Existing API names and frozen archives require the
  operator's migration decision before changing their contracts. Preserve
  Unicode coverage in tests; English-only prose does not mean ASCII-only data.
- **Codec keys:** a proven field gets a semantic key (`name`, `profile`,
  `effect`); an unidentified one keeps a neutral `fN` key. Renaming `fN` → a
  guess is exactly the failure mode this repository exists to avoid.
- **Self-check idiom, plus one suite at the boundaries:** the tools listed in
  `make check`, plus `wpj_diff.py`, run their own check with no arguments.
  `wolfmix.py` and `wolfmix_experiment.py` use a `self-test` subcommand. New
  non-trivial logic follows the idiom — one runnable assertion, in the file it
  proves. `tests/` is the deliberate exception: it holds what the tools
  **refuse**, on `unittest`, because those two properties matter there and the
  idiom cannot give them — `assert` disappears under `python3 -O`, and a
  self-check that needs a corpus abstains on the clone where a rotted boundary
  would go unnoticed. `tests/fixtures.py` builds every byte it needs.
- **One wire reader, and one oracle.** `tools/wpj_wire.py` is the production
  reader: varints, protobuf fields, the TLV container, shared by the codec, the
  B/C reader, the USB protocol and the gobo palette. `tools/wpj_inspect.py`
  keeps its **own** independent walk on purpose — this is the one documented
  exception to "no repetition", because an oracle that shares code with what it
  verifies proves only that the shared code agrees with itself. A third walker
  is a bug.
- **Working directory:** the corpus root is `corpus/`, or `$WPJ_CORPUS`. Run
  tools from the repository root unless that variable is absolute.

## Adding a finding

Follow the [differential protocol](docs/methodology.md#the-differential-protocol)
and [contribution requirements](CONTRIBUTING.md#adding-or-correcting-a-format-claim).
Read the [five known traps](docs/methodology.md#five-traps-that-have-already-cost-time)
before designing a probe. Publish and commit the prediction before measuring.

A count, offset or derivation belongs in `tools/wpj_identities.py`. A schema
change belongs in `wpj_codec.SCHEMAS` / `PASSTHROUGH`; `wpj_counts.py` checks
marked documentation figures. An unnamed field that never varies belongs in
`wpj_coverage.INERT_FIELDS`, with its observed value, never a guessed name.
`make check` must still pass.

When a status falls, follow the [retraction cascade](docs/methodology.md#a-status-can-go-back-down)
and preserve the ledger's historical account. Independent observations outrank
repeated saves and outputs of our own writer.

## What this project will not do

No circumvention of a protection measure — one that guards a licence, an
entitlement, an activation or firmware authenticity — no licence/activation/
entitlement work, no redistribution of vendor material, no executable-firmware
operation. The dedicated external-resource upload remains limited by the gobo
window gates above.
If a request heads that way, stop and say so; the reasoning is in
[`LEGAL.md`](LEGAL.md).

**Reading a file on this machine is not one of those things.** Local analysis of
a file the operator owns — a project, the fixture library, a sidecar, the
controller's output — is in scope by default, and refusing to open one is a
failure, not caution. The rules that bite are about what *leaves* the machine
and what gets *committed*: `.gitignore` and `tools/wpj_privacy.py` enforce
those, so you do not have to enforce them by not looking.

An obfuscated format gets the four questions in LEGAL.md, answered per format
and recorded there — not a reflex refusal. `.ssl2` passes them and
`tools/ssl2.py` reads and writes it. The one that ends the conversation is the
first: no key is recovered from a vendor binary here, so a format whose key
nobody has published stays undecoded — which is a statement about keys, not a
reason to leave the file unopened.
