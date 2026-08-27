# AGENTS.md

Orientation for coding agents and automated contributors. Humans: this is a
condensed version of [`README.md`](README.md) + [`docs/methodology.md`](docs/methodology.md).

## What this repository is

Reverse-engineering of the Wolfmix `.wpj` project file format, plus tools that
read and write it, plus a client for the W1 controller's USB protocol. Python
3, **standard library only**. The deliverable is trustworthy knowledge:
[`SPEC.md`](SPEC.md) is the product, `tools/` is its executable proof.

## The one command

```bash
make check          # from the repository root — nine self-checks
```

Green means the structural claims hold on the corpus present — **file-format
code only**. No USB protocol code runs: `wolfmix.py` and
`wolfmix_experiment.py` are deliberately absent from the Makefile. Their
hardware-free checks are separate subcommands:
`python3 tools/wolfmix.py self-test` and
`python3 tools/wolfmix_experiment.py self-test`. **If it prints
`ignoré, aucun corpus`, nothing was verified** — no project files ship with
this repository (see below). Do not read an abstention as a pass, and do not
"fix" it by inventing test data.

## Hard invariants — do not break these

| Invariant | Why |
|---|---|
| **No new dependencies.** Standard library only. | Portability, and the ability to audit every line. |
| **Never commit `*.wpj`, `*.wm`, `*.wmx`, `*.pdf`, vendor extractions (`research/vendor/`), DMX captures (`corpus/**/dmx/`, `.wolfmix-state/`), or the local `.wpj-private-names` list.** | They carry the manufacturer's factory content and someone's real show — [`LEGAL.md`](LEGAL.md). `.gitignore` enforces it; never work around it with `git add -f`. |
| **Never write a real venue, client, project, group or device name into a tracked file.** Use the neutral labels the tree already uses: `rig-a`/`rig-b`/`rig-c`, `<group-A name>`, serial withheld. | `make check` fails on it — `tools/wpj_privacy.py` greps every tracked file against a list that lives outside the repository. This is the invariant most often broken by accident, including by writing a new research section. |
| **Unknown bytes pass through verbatim.** | A record with no schema round-trips exactly. `wpj_codec.decode` returns `{"raw": hex}` rather than a partial decode. |
| **Writes never overwrite.** Output opens with mode `x`. | An overwritten project is an unrecoverable show. |
| **Nothing leaves the machine.** No upload, no third-party API, no telemetry. | Rule 4, and the evidence chain depends on it. |
| **No firmware operations, ever.** | The outgoing event allowlist in `tools/wolfmix.py` is exhaustive by design. |
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
```

When `SPEC.md` and `research/` disagree, `research/` is newer — and that gap is
itself worth recording rather than silently resolving.

## Conventions you will notice

- **Language:** mixed on purpose. Tool output strings are French. `SPEC.md`,
  `LEGAL.md`, `PROVENANCE.md`, `docs/` and `README.md` are English. `research/`
  is both — English since the type-102 entry, French before it and in the newest
  entries. Keep each file in the language it is in rather than mass-translating.
- **Codec keys:** a proven field gets a semantic key (`nom`, `profil`,
  `effet`); an unidentified one keeps a neutral `fN` key. Renaming `fN` → a
  guess is exactly the failure mode this repository exists to avoid.
- **Self-check idiom:** the nine tools in `make check`, plus `wpj_diff.py`,
  run their own check with no arguments. `wolfmix.py` and
  `wolfmix_experiment.py` use a `self-test` subcommand; `tlv.py` and `dump.py`
  are argument-only helpers. New non-trivial logic follows the idiom — one
  runnable assertion, no test framework.
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

### Four traps that have already cost time

- **A field that is uniform across the whole corpus may still be per-group, or
  per-anything.** Uniformity over thousands of samples is evidence about the
  *corpus*, not about the field: nothing had ever varied it. `f30` was read as
  a scalar on those grounds and refuted by one photograph of the device. It has
  now happened three times: the latest is `165.f16` slice 5, `correlated` as
  "always 255" over 2446 presets, then refuted when the device's own writer
  saved a file of ours and put the mask of the groups each preset addresses
  there (GEN-03, validated).
- **Creating a preset does not save the project.** Nor does any other UI edit
  until the operator performs the separate project save. Read the `uint64` at
  offsets 40–47 before and after: if it has not incremented, nothing was
  written, whatever the screen shows. That counter has been misread twice on one
  experiment, in opposite directions — check it, do not assume it.
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
