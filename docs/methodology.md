# Methodology

Reader: Experiment authors. Question: How do I establish, challenge and retract a claim?

How a claim gets into [`SPEC.md`](../SPEC.md), and what it takes to move it up.
This is the part of the repository that matters most: the tools are small, the
discipline is the product.

## Evidence statuses

Use the [canonical evidence vocabulary](../SPEC.md#evidence-rules). Each claim
keeps its status and uncertainty; promotion requires new evidence, not a more
confident paraphrase.

## Counting the corpus honestly

None of the corpus is published ([`../LEGAL.md`](../LEGAL.md)); what follows is
about how it was counted while measuring, and applies just as much to yours.

The variant-A corpus used here holds 45 files, but only **four independent
rigs**:
*rig-a* (10 fixtures), *rig-b* (15), *rig-c* (20) and
*rig-c-bug* (22, a re-patched *rig-c*). The rest are derived — seven
written by our own writer from *rig-a*, seven controller saves of one copy
of *rig-c*.

So an identity that holds on every file is strong enough to **kill** a
hypothesis. It is not by itself enough to promote one. Derived files inherit
their parent's structure; they are not independent evidence.

And count what is **distinct**, not what is present. The 45 files hold 3697
preset occurrences but only **352 presets distinct by content**: the derived
files replicate the same entries. A correlation announced as "54 for 54" was
four presets copied into thirty-three files (F7-01). Check that ratio before
publishing any count.

## The differential protocol

Software-only, no device connected. This is how EXP-01…05 in
[`../research/evidence.md`](../research/evidence.md) are run.

1. In WTOOLS, duplicate an existing project — **never the original**.
2. Change **exactly one** parameter. Save.
3. Copy the new `.wpj` out of `wlinkData/projects/`, hash it, freeze the pair
   under `corpus/experiments/<ID>/`.
4. `python3 tools/wpj_diff.py before.wpj after.wpj` — locate the changed bytes.
5. Write it up: the exact manipulation, the diff, the conclusion, the status
   reached. Serial, firmware and file hashes included.

One experiment validates at most one field. An ambiguous result is written down
as a list of candidates.

**On record 165, overwrite a preset rather than appending one.** A fresh entry
adds a few hundred bytes and shifts everything after it, so the diff is a wall.
Re-capturing over an **existing** experiment preset leaves every length intact,
and a one-byte field then shows up as a single one-byte range in
`wpj_diff.py` — no protobuf reading required to see it. FX6-04 closed the move
`Fan` that way: one byte on 46414, `50` → `83`. The cost is the overwritten
preset, so this is for experiment entries only, never a real show's cues.

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

### The live copy is not the file

The controller plays a **live copy**, and a recall measures that copy, not the
bytes you deployed. Two consequences, both expensive:

- `deploy` does not replace it — and `deploy` *is* `store` + `RESTART` under
  the same UUID, so there is no second manoeuvre hiding there. Neither does a
  WTOOLS push (RELOAD-02/03). Only a manual open on the panel does
  (RELOAD-04) — measure before that open and you measure the previous show.
- With `LIVE EDIT` on (`165.f10` bit 4 clear), one gesture at the panel
  rewrites a cue's live copy while the file on the device stays exactly as
  uploaded. The divergence is invisible until you save on the panel and
  download the result.

This is the most expensive measurement trap found here (the registry counts it
as the fifth): it produced a perfectly reproducible anomaly — three shots, two
independent series — that pointed at the wrong field for a whole session
(GEN-03). **Reproducibility protects nothing when it is the state, not the
measurement, that is stable.** A cue meant to be measured carries `LIVE EDIT`
**off**, and a session that ends in doubt ends with a panel save and a
download.

### The version counter is a negative oracle only

The `uint64` at offsets 40–47 increments when the controller saves. If it has
**not** moved, nothing was written — that direction holds. The other direction
does not: on 2026-08-27 a save incremented it while leaving all 45054 payload
bytes identical (F7-02). An increment says a save happened, never that the
content changed. Diff the records.

## A status can go back down

Promotion is not one-way. On 2026-08-27 a `device-confirmed` reading of the
USB preset-recall payload was withdrawn, and it took four negatives with it —
they had all been judged with the discriminator that turned out not to
discriminate. The honest state after a retraction is usually **neither confirmed
nor refuted**, and saying so is what stops the next experiment from being built
on sand.

When you retract, follow the cascade: list every claim that rested on the same
evidence and mark each one explicitly, including the ones you would rather keep.

## Promotion to `device-confirmed`

`validated` becomes `device-confirmed` only when a file **we generated** is
accepted downstream: opened by WTOOLS without complaint, or stored by the W1
and downloaded back byte-identical. ACC-01 did this for the variant-A
container, the SHA-1 header and record 101 — which is why those, and only
those, are writable without hedging.

## Five traps that have already cost time

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

## Contributing an experiment

A patch that adds or changes a field interpretation needs:

- **the prediction, written before the measurement** — which channel, which
  value, which screen. This is now the dominant practice here: roughly twenty
  entries in `research/` are written that way, and several of those predictions
  were wrong — GEN-02 published four and lost all four, and the model that
  replaced them was exact on seven measured points, which is exactly what makes
  the method worth the trouble;
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
