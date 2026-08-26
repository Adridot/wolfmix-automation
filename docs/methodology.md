# Methodology

How a claim gets into [`SPEC.md`](../SPEC.md), and what it takes to move it up.
This is the part of the repository that matters most: the tools are small, the
discipline is the product.

## Evidence statuses

Every statement carries one. Nothing is asserted without one.

| Status | Meaning |
|---|---|
| `observed` | seen in the bytes, no interpretation |
| `hypothesized` | an interpretation is proposed, not yet tested |
| `correlated` | consistent across independent files |
| `validated` | confirmed by a single-variable differential experiment |
| `device-confirmed` | the resulting file was accepted by a W1 |

Three rules go with the ladder:

- **Never name an unconfirmed enum value.** A number stays a number.
- **Ambiguity is recorded, not resolved.** Two candidate readings mean two
  candidates listed, not a coin flip.
- **An absent field is absent.** Never reported as `0` or `off`.

## Counting the corpus honestly

None of the corpus is published ([`../LEGAL.md`](../LEGAL.md)); what follows is
about how it was counted while measuring, and applies just as much to yours.

The variant-A corpus used here holds 27 files, but only **four independent
rigs**:
*rig-a* (10 fixtures), *rig-b* (15), *rig-c* (20) and
*rig-c-bug* (22, a re-patched *rig-c*). The rest are derived — seven
written by our own writer from *rig-a*, seven controller saves of one copy
of *rig-c*.

So an identity that holds on every file is strong enough to **kill** a
hypothesis. It is not by itself enough to promote one. Derived files inherit
their parent's structure; they are not independent evidence.

## The differential protocol

Software-only, no device connected. This is how EXP-01…05 in
[`../research/experiments.md`](../research/experiments.md) are run.

1. In WTOOLS, duplicate an existing project — **never the original**.
2. Change **exactly one** parameter. Save.
3. Copy the new `.wpj` out of `wlinkData/projects/`, hash it, freeze the pair
   under `corpus/experiments/<ID>/`.
4. `python3 tools/wpj_diff.py before.wpj after.wpj` — locate the changed bytes.
5. Write it up: the exact manipulation, the diff, the conclusion, the status
   reached. Serial, firmware and file hashes included.

One experiment validates at most one field. An ambiguous result is written down
as a list of candidates.

## The device protocol

When the question cannot be answered from files — "does this field do anything
at all?" — it goes to hardware, through `wolfmix_experiment.py`
([`device.md`](device.md)).

1. `init` + `arm` on a base project, capturing a reference DMX envelope.
2. `deploy` a candidate differing in exactly one field.
3. Compare the DMX envelope against the reference.

Per-channel min/max is the comparison, not a single frame: effects animate, so
frames are never equal between runs, while a static channel keeps
`min == max` and an animated one keeps its range whatever the phase.

A field that changes no channel in any state is recorded as **inert** — which
is a result, and a publishable one. F11-01 in `research/` is exactly that: a
refutation, written up as carefully as a confirmation.

## Promotion to `device-confirmed`

`validated` becomes `device-confirmed` only when a file **we generated** is
accepted downstream: opened by WTOOLS without complaint, or stored by the W1
and downloaded back byte-identical. ACC-01 did this for the variant-A
container, the SHA-1 header and record 101 — which is why those, and only
those, are writable without hedging.

## Contributing an experiment

A patch that adds or changes a field interpretation needs:

- the exact single-variable manipulation, reproducible by someone else;
- the SHA-256 sums of the before/after files — **the hashes, not the files**;
- the `wpj_diff.py` output;
- the status it reaches, and why it does not reach the next one;
- serial, firmware and WTOOLS version.

Then: `make check` still passes, the byte-identical round-trip still holds over
the whole corpus, unknown bytes are still preserved verbatim, and no new
dependency was added.

If the reading implies a count, an offset or a derivation, add it to
`tools/wpj_identities.py` as well: an arithmetic identity that holds on every
file is checkable forever, by anyone, without hardware.

Recording that something is *not* what it looked like is as valuable as
recording what it is. Both go in `research/`.
