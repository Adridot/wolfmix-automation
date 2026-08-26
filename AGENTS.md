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
make check          # from the repository root — six self-checks
```

Green means the structural claims hold on the corpus present. **If it prints
`ignoré, aucun corpus`, nothing was verified** — no project files ship with
this repository (see below). Do not read an abstention as a pass, and do not
"fix" it by inventing test data.

## Hard invariants — do not break these

| Invariant | Why |
|---|---|
| **No new dependencies.** Standard library only. | Portability, and the ability to audit every line. |
| **Never commit `*.wpj`, `*.wm`, `*.wmx`, `*.pdf`, or DMX captures.** | They carry the manufacturer's factory content and someone's real show — [`LEGAL.md`](LEGAL.md). `.gitignore` enforces it; never work around it with `git add -f`. |
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

A field may be written by the tools only at `correlated` or better. That is why
`size`/`fade`/`phase` are readable but not writable.

## Where truth lives

```text
research/        the lab notebook, in French. ALWAYS the most current.
SPEC.md          the consolidated English read of research/. May lag.
docs/            task-oriented guides for users.
tools/           the implementation. Self-checks are the ground truth.
```

When `SPEC.md` and `research/` disagree, `research/` is newer — and that gap is
itself worth recording rather than silently resolving.

## Conventions you will notice

- **Language:** `research/` and most tool output strings are French; `SPEC.md`,
  `LEGAL.md`, `PROVENANCE.md`, `docs/` and `README.md` are English. Keep it that
  way rather than mass-translating.
- **Codec keys:** a proven field gets a semantic key (`nom`, `profil`,
  `effet`); an unidentified one keeps a neutral `fN` key. Renaming `fN` → a
  guess is exactly the failure mode this repository exists to avoid.
- **Self-check idiom:** every tool run with no arguments executes its own
  check. New non-trivial logic follows suit — one runnable assertion, no test
  framework.
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
with the same care as the confirmations.

### Two traps that have already cost time

- **A field that is uniform across the whole corpus may still be per-group, or
  per-anything.** Uniformity over thousands of samples is evidence about the
  *corpus*, not about the field: nothing had ever varied it. `f30` was read as
  a scalar on those grounds and refuted by one photograph of the device.
- **Creating a preset does not save the project.** Nor does any other UI edit
  until the operator performs the separate project save. Read the `uint64` at
  offsets 40–47 before and after: if it has not incremented, nothing was
  written, whatever the screen shows.

Much of the format can also be measured **without writing anything**: set a
control on the device, capture `wolfmix.py dmx-envelope`, compare. Eleven modes
of `f30` were settled that way in an hour, with the rig returned to its opening
baseline on all 2048 channels.

## What this project will not do

No circumvention of any protection measure, no decryption of the vendor's
opaque sidecar formats, no licence/activation/entitlement work, no
redistribution of vendor material. If a request heads that way, stop and say
so — the reasoning is in [`LEGAL.md`](LEGAL.md).
