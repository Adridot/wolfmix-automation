# Troubleshooting

## Files

**`self-check ok` never appears / `corpus variante A introuvable (cwd ?)`**
The self-checks resolve `corpus/` relative to the working directory. Run from
the repository root.

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
106, 110, 111, 130, 151, 155 and 161 are passthrough today.

**`<path> existe déjà — écrasement refusé`**
Every writer opens output with mode `x`. Choose a new path; nothing is ever
overwritten.

**`clés hors périmètre [...]` from `wpj_show.py`**
The key is real in the format but not writable yet — its evidence status is
below `correlated`. The accepted set is in [`show-format.md`](show-format.md).

**`l'entrée doit exister dans le donneur`**
Creating a preset, position or palette entry from scratch has never been
validated on a device. Pick a donor project that already has the slot.

**`auto-verify : records modifiés hors édition`**
The compiler detected that an edit changed something it did not intend to. The
output file is deleted. This is a bug worth reporting, with the spec and the
donor.

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

**Nothing happens after `init`**
Firmware 2.0.18 has no USB command to select a project. Open the
`WMX EXP …` project once on the controller itself, then run `arm`. Note that
the project name is truncated to 19 characters on the device.

**DMX output looks identical between two candidates**
Compare envelopes (`dmx-envelope`), not frames — effects animate, so two
captures of the same project are never byte-equal. If the envelopes match too,
the field really is inert; that is a result, write it up.
