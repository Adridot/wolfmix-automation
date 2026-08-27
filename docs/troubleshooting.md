# Troubleshooting

## Files

**`… : ignoré, aucun corpus dans corpus/ (voir docs/corpus.md)`**
Working as intended: no project file ships with this repository, and you have
not supplied one. The self-check abstained rather than passing vacuously. Put
`.wpj` files under `corpus/`, or set `WPJ_CORPUS` to where you keep them —
[`corpus.md`](corpus.md).

**A self-check finds no files even though they are there**
The corpus root is resolved relative to the working directory unless
`WPJ_CORPUS` is absolute. Run from the repository root, or export an absolute
path.

**`wpj_show` abstains although the corpus has files**
Its self-check needs a donor carrying the slots it edits (preset id 80, a
position at page 1 index 1, palette pad 0). It tries each file in turn and
abstains if none qualifies. Any full factory-derived project has them.

**`invalid SHA-1 header`**
`wpjlib` refuses anything whose bytes 0–19 are not the SHA-1 of bytes 20→EOF.
Usually it means the file is variant B or C, not A — use `wpj_inspect.py`
instead. If it is genuinely variant A, the file is corrupt.

**`not a root container type 100`**
Same conclusion: not a variant-A file. The variants are described in
[`../SPEC.md`](../SPEC.md) §1.

**`wpj_inspect.py` exits 2 with `PAS du wire format protobuf`**
The input is not protobuf from the offset tried. Small `.wpj` files (device
dumps) do this. The tool refuses to guess rather than emit a plausible tree.

**A record decodes to `{"raw": "<hex>"}`**
No schema for that type, or its protobuf did not match the schema. That is the
designed fallback, not a failure: the bytes still round-trip exactly. Types
106, 110, 111, 130, 155 and 161 are passthrough today.

**`<path> existe déjà — écrasement refusé`**
Every writer opens output with mode `x`. Choose a new path; nothing is ever
overwritten.

**`clés hors périmètre [...]` from `wpj_show.py`**
The key is real in the format but not writable yet — its evidence status is
below `correlated`. The accepted set is in [`show-format.md`](show-format.md).

**`l'entrée doit exister dans le donneur`**
Creating a position or palette entry from scratch has never been validated on a
device — this message only fires for those two. A **preset** may be created:
appending an entry with an id above every id in the donor is device-confirmed
(PRESET-01/06/07), so pass `modele` instead. Otherwise pick a donor project that
already has the slot.

**`auto-verify : records modifiés hors édition`**
The compiler detected that an edit changed something it did not intend to. The
output file is deleted. This is a bug worth reporting, with the spec and the
donor.

**`wpj_privacy : N occurrence(s) de nom réel dans des fichiers suivis`**
A real venue, client, project, group or device name reached a tracked file, and
`make check` refuses to pass. Replace it with the neutral label the rest of the
tree uses — `rig-a`/`rig-b`/`rig-c`, `<group-A name>`, serial withheld — and
re-run. The message prints `file:line` and which pattern matched.

**`wpj_privacy : ignoré, pas de .wpj-private-names`**
Expected on a fresh clone: the pattern list is deliberately not distributed
([`../LEGAL.md`](../LEGAL.md)). Create one at the repository root, one regex per
line, if you keep material that must never be published.

## Device

**`No USB modem port found`**
The W1 is not connected, or not enumerating. Check the cable — some are
charge-only.

**`Multiple USB modem ports found`**
Pass `--port /dev/cu.usbmodemXXXX`.

**The port is busy, or reads time out immediately**
WTOOLS is open. Close it — the port is exclusive. `wolfmix.py` reports the
holding processes when `lsof` is available.

**`Outgoing event N is not allowlisted`**
Working as intended. `build_frame` only emits events from the explicit
allowlist; firmware operations are not implemented and will not be.

**`Experiment is not initialized`**
Run `init` for that label first. State lives in
`.wolfmix-state/<experiment-uuid>/`.

**`Experiment state identity mismatch`**
The label no longer derives the UUID recorded in `state.json` — usually a typo
in `--label`, or a state directory copied between labels.

**`deploy` verifies the upload and fails**
The controller stored something different from what was sent. The runner
restores the previous experiment project. Keep `runs/<utc>-<case>/` — the
before/candidate pair is the evidence.

**A recall plays something other than what I deployed**
The controller plays a live copy, and `deploy` does not replace it — only a
manual open on the panel does (RELOAD-04). If the project was already open and
`LIVE EDIT` is on for that cue (`165.f10` bit 4 clear), a gesture at the panel
also rewrites the live copy while the file stays exactly as uploaded (GEN-03).
Save on the panel, download the project, and diff it against the bytes you
sent — that is the only way to see the divergence. Generate measurement cues
with `live_edit: false`.

**`wolfmix.py preset N` does nothing at all**
An id that is not present is a silent no-op — above the highest id present
(RECALL-04) or inside an interior hole (RECALL-05). The rig keeps playing the
previous cue and nothing reports an error. Check the id against the project
(`id = (page - 1) * 20 + (slot - 1)`) — ids above 127 are fine, the whole panel
range 0–199 is reachable (RECALL-06) — and remember that recalls fired a few
seconds apart can also be swallowed.

**The panel is stuck on a screen after `wolfmix.py mode N`**
Indexes 26 (Projects) and 42 (USB stick) are modal. Send `mode 1` — `1`, `3`,
`8` and `33` release the panel; `0`, `5` and `16` do not (SCREEN-02). The
physical keys get through where `SET_MODE` does not (SCREEN-03).

**`The loaded project has unsaved changes; save it on the W1 first`**
`arm` and `deploy` refuse to run against a controller holding unsaved edits.
Save on the panel. Worth doing deliberately rather than grudgingly: that save
is the only way to read what the live copy has drifted to, and it is how the
GEN-03 anomaly was explained.

**Nothing happens after `init`**
Firmware 2.0.18 has no USB command to select a project. Open the
`WMX EXP …` project once on the controller itself, then run `arm`. Note that
the project name is truncated to 19 characters on the device.

**My generated show's dimmers do nothing**
The condition is not in the file: the Settings menu carries
`store group dimmers in preset`, and with it **off** every `dimmers` value is
silent while the show still compiles, verifies and deploys perfectly (GEN-02,
device-confirmed). Some operators keep it off on purpose. Turn it on, then
re-check — [`generator.md`](generator.md) has the percentage formula and the
colour-folding case.

**DMX output looks identical between two candidates**
Compare envelopes (`dmx-envelope`), not frames — effects animate, so two
captures of the same project are never byte-equal. If the envelopes match too,
the field really is inert; that is a result, write it up.
