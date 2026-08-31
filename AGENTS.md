# AGENTS.md

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
| **Never commit `*.wpj`, `*.wm`, `*.wmx`, `*.pdf`, vendor extractions (`research/vendor/`), DMX captures (`corpus/**/dmx/`, `.wolfmix-state/`), or the local `.wpj-private-names` list.** | They carry the manufacturer's factory content and someone's real show — [`LEGAL.md`](LEGAL.md). `.gitignore` enforces it; never work around it with `git add -f`. |
| **Never write a real venue, client, project, group or device name into a tracked file.** Use the neutral labels the tree already uses: `rig-a`/`rig-b`/`rig-c`, `<group-A name>`, serial withheld. | `make check` fails on it — `tools/wpj_privacy.py` greps every tracked file against a list that lives outside the repository. This is the invariant most often broken by accident, including by writing a new research section. |
| **Unknown bytes pass through verbatim.** | A record with no schema round-trips exactly. `wpj_codec.decode` returns `{"raw": hex}` rather than a partial decode. |
| **Writes never overwrite.** Output opens with mode `x`. | An overwritten project is an unrecoverable show. |
| **Nothing leaves the machine.** No upload, no third-party API, no telemetry. | Rule 4, and the evidence chain depends on it. |
| **No executable-firmware operations, ever.** The outgoing event allowlist in `tools/wolfmix.py` is exhaustive by design, and no code path uploads firmware. | A bricked controller is not recoverable from here. |
| **A resource flash is not firmware.** `wolfmixFlash.bin` carries the interface's graphics. It is read, patched into a **copy** and verified here — backed up first, hash-anchored by a manifest, and uploaded by WTOOLS itself, never by this repository. | The distinction is what makes the gobo pipeline legitimate; see [`LEGAL.md`](LEGAL.md). |
| **Do not write to a connected device** except through `wolfmix_experiment.py`, which uses its own derived UUIDs. | Ordinary projects must never be touched. |
| **Never invent a name for an unconfirmed value.** | Ambiguity is recorded as a list of candidates. An absent field is *absent*, never `0` or `off`. |

## Evidence vocabulary

Every claim in `SPEC.md` and `research/` carries one status. Respect it when
you write or cite anything:

`observed` → `hypothesized` → `correlated` → `validated` → `device-confirmed`

- `correlated` = consistent across **independent** files. Derived files (our own
  writer's output, repeated saves of one project) are not independent evidence.
- `validated` = a single-variable differential experiment.
- `device-confirmed` = a file *we generated* was accepted downstream, or the
  behaviour was measured on the controller itself.

A field may be written by the tools only at `correlated` or better — the
threshold the code enforces (`tools/wpj_show.py`), and why the unattributed FX
fields are readable but not writable. Note that [`README.md`](README.md) rule 2
states a stricter one (round-trip *and* differential validation *and* acceptance
downstream); the two texts disagree, and the disagreement is deliberate — rule 2
describes what earns a `device-confirmed` field, the code's threshold is what it
takes to be writable at all.

## Where truth lives

```text
research/        the lab notebook. ALWAYS the most current. Mostly English
                 since its type-102 entry; the oldest and newest sections
                 are French.
SPEC.md          the consolidated English read of research/. May lag.
docs/            task-oriented guides for users.
tools/           the implementation. Self-checks are the ground truth.
tests/           boundary tests: what is refused, and what never reaches
                 the wire. Corpus-free, and not stripped by `python3 -O`.
```

When `SPEC.md` and `research/` disagree, `research/` is newer — and that gap is
itself worth recording rather than silently resolving.

## Conventions you will notice

- **Language:** mixed on purpose. Tool output strings are French. `SPEC.md`,
  `LEGAL.md`, `PROVENANCE.md`, `docs/` and `README.md` are English. `research/`
  is both — English since the type-102 entry, French before it and in the newest
  entries. Keep each file in the language it is in rather than mass-translating.
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

1. Change **one** variable, in the vendor editor or on the device.
2. `python3 tools/wpj_diff.py before.wpj after.wpj`.
3. Write it up in `research/` with the manipulation, the **hashes** (not the
   files), firmware and WTOOLS versions, and the status reached.
4. If the reading implies a count, an offset or a derivation, encode it in
   `tools/wpj_identities.py` — an arithmetic identity is checkable forever, by
   anyone, without hardware.
   If it moves a record between decoded and passthrough, change
   `wpj_codec.SCHEMAS` / `PASSTHROUGH` and let `make check` tell you which
   documents now lie: figures marked `<!--count:…-->` are checked against the
   code, never trusted.
5. `make check` must still pass.

A refutation is a result. `research/` contains several, and they are written up
with the same care as the confirmations. A published status can also go **back
down**: RECALL-01 (2026-08-27) withdrew a `device-confirmed` reading and, with
it, four negatives that had rested on the same discriminator. The same day,
GEN-02 sent `165.f10` bit 5 (`OTHER`) from `device-confirmed` back to
`hypothesized` — the dimmer silence it was thought to explain turned out to be
a controller setting that had been off the whole time, and one cause is enough.
It climbed back to `validated` only once FW-03 wrote that bit and nothing else
(2026-08-27), which is the point: a status goes back up by measurement, not by
the passage of time.
When a status falls,
follow the cascade and mark everything it touched as no longer established —
neither confirmed nor refuted is an honest state, and it is the one that keeps
the next experiment honest too.

### Publish the prediction before you measure

This is now the dominant method here, and roughly seventeen entries in the
registry are written that way: state what the reading predicts — which channel,
which value, which screen, and a rough probability — **commit it**, then
measure. It costs nothing and it is the only protection against reading a
confirmation into an ambiguous result after the fact. Several of those
predictions were wrong, and each was worth more than a vague success.

### Five traps that have already cost time

- **A field that is uniform across the whole corpus may still be per-group, or
  per-anything.** Uniformity over thousands of samples is evidence about the
  *corpus*, not about the field: nothing had ever varied it. `f30` was read as
  a scalar on those grounds and refuted by one photograph of the device. It has
  now happened five times. `165.f16` slice 5 was `correlated` as "always 255"
  over 2446 presets, then refuted when the device's own writer put the mask of
  the groups each preset addresses there (GEN-03). And on 2026-08-27 an identity
  added to `wpj_identities.py` that morning — "an FX engine that is on stores two
  *different* page configurations", 3697 occurrences, zero exceptions — was
  refuted the same evening by one preset composed at the panel (FX2-01). **The
  author of this warning fell into it inside a day.** A correlation with no
  exception over the whole corpus is a fact about the corpus until a fresh write
  tests it; the defence is the write, not more counting.
- **A field that already carries a name is not a field that was measured.** The
  most expensive mistake of 2026-08-30, made twice in one session. `f2` of the
  FX submessage had read "speed %" since ACC-04 at status `correlated`, so a
  whole campaign was framed as "which of Phase / Size / Fade lands on `f6`,
  `f8`, `f9`" — and never put `f2` back on the table. `f2` is the **fade**; the
  speed was `f9`, sitting among the unattributed. The three-way permutation was
  a four-way. Hours later the same shape repeated one level up: record 155 was
  `device-confirmed` as "the 4 FX sequences", so the beam sequencer was hunted
  in an opaque blob (161) while the answer sat in 155 behind `f2`, a field named
  "sequence flavour" and never opened. **A record marked decoded is not a record
  closed, and `correlated` is a statement about consistency, not about meaning.**
  When a reading resists, list the fields you excluded *because they already had
  names*, and check what measured them.
- **Creating a preset does not save the project.** Nor does any other UI edit
  until the operator performs the separate project save. Read the `uint64` at
  offsets 40–47 before and after: if it has not incremented, nothing was
  written, whatever the screen shows. **The converse is false** — on 2026-08-27
  a save incremented that counter and left all 45054 payload bytes identical
  (F7-02), so an increment proves nothing about the content. It is a
  **negative** oracle only; to know whether anything changed, diff the records.
  Misread three times now, in all three directions — check it, do not assume it.
- **A probe that cannot separate "nothing moved" from "the same thing was
  repainted" proves nothing.** Two separately captured DMX envelopes cannot tell
  those apart, which is how RECALL-01 first concluded that preset recalls were
  inert. They were not: they act, and they always act the same. One continuous
  capture with timestamped transitions settled in minutes what the separate
  envelopes had got backwards.
- **An equality with a simpler explanation is not evidence.** "Positions 85, 86,
  92 and 99 all render identically" was read as clamping. It was neither
  clamping nor, as the next reading had it, a target being ignored: the payload
  was not protobuf at all, and the device had been reading our tag byte as the
  index. Prefer the reading that needs fewer new mechanisms — and when a whole
  family of values behaves identically, suspect the **encoding** before the
  semantics.
- **The live copy is not the file, and it diverges in silence.** A recall
  measures what the controller holds in RAM. `deploy` does not replace it — nor
  does `store` + `RESTART`, nor a WTOOLS push; only a manual open on the panel
  does (RELOAD-04). And with `LIVE EDIT` on (`165.f10` bit 4 clear), one gesture
  at the panel rewrites a cue's live copy while the file stays exactly as
  uploaded. That produced a perfectly reproducible anomaly — three shots, two
  independent series — that pointed at the wrong field for a whole session
  (GEN-03). Reproducibility protects nothing when it is the *state*, not the
  measurement, that is stable. Cues meant for measurement carry `LIVE EDIT`
  off, and a panel save followed by a download is the only way to see the
  divergence.

Much of the format can also be measured **without writing anything**: set a
control on the device, capture `wolfmix.py dmx-envelope`, compare. Five of the
eleven `f30` colour-spread modes were settled that way in an hour, read-only,
with the rig returned to its opening baseline on all 2048 channels; three more
needed a project save, and three remain derived rather than read.

## What this project will not do

No circumvention of any protection measure, no decryption of the vendor's
opaque sidecar formats, no licence/activation/entitlement work, no
redistribution of vendor material. If a request heads that way, stop and say
so — the reasoning is in [`LEGAL.md`](LEGAL.md).
