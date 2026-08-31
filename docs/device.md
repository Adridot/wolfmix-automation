# Talking to the W1

Two tools, one below the other. `wolfmix.py` is a client for the controller's
USB serial protocol. `wolfmix_experiment.py` builds transactions on top of it.

Measurement base: **W1 Mk1, firmware 2.0.18**, macOS. Nothing here is tested on
a Mk2.

## Before you plug in

- **Close WTOOLS.** The serial port is exclusive; the tool detects who holds it
  (via `lsof`) and tells you.
- The port is auto-detected as the single `/dev/cu.usbmodem*`. With several
  devices attached, pass `--port`.
- No firmware operation is implemented, anywhere. The outgoing event allowlist
  is a literal in the source (`ALLOWED_OUTGOING_EVENTS`) and `build_frame`
  refuses anything outside it.

## Protocol

A frame is a 9-byte big-endian header followed by a protobuf payload:

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | protocol version (`1`) |
| 1 | 4 | total size, header included |
| 5 | 2 | message id, echoed in the reply |
| 7 | 2 | event id |
| 9 | … | protobuf payload |

Events used: `GET_PROFILE_LIST` 2, `GET_PROFILE` 3, `GET_PROJECT_LIST` 4,
`GET_PROJECT` 5, `DISABLE_ENGINE` 6, `ENABLE_ENGINE` 7, `DISABLE_USB_DMX` 8,
`ENABLE_USB_DMX` 9, `DMX_PACKET` 12, `DELETE_PROJECT` 16, `SET_PROJECT` 18,
`RETURN_STATUS` 19, `RETURN_PROGRESS` 20, `GET_SETTINGS` 21, `SET_MODE` 39,
`SET_PRESET` 41, `SKIP_PRESET` 43, `RESTART` 44.

**`SET_PRESET` and `SET_MODE` do not carry protobuf.** Firmware 2.0.18 reads
`payload[0]` as the index: one raw byte, nothing else. A protobuf-shaped
`[tag, value]` pair makes the controller read the *tag* — `f1=<anything>`
recalls id 8, `f2=<anything>` id 16. For `preset`, the byte is the preset
**id** (`id = (page-1)*20 + (slot-1)`), not the entry position, and **an id
above the highest one present does nothing** — no floor, no clamp to the last
entry, no wrap to the first, no modulo (RECALL-04). **An id inside an
*interior* gap does nothing either** — id 90, in the hole between 81 and 100,
left the frame identical on all 2048 channels while the four rival readings
each predicted a different measured frame (RECALL-05). That is the case a
generated bank creates. **A present id above 127 is recalled exactly** — byte
140 and byte 141 each rendered their own cue to the channel, while byte 228,
where no preset exists, stayed a no-op; that kills the 7-bit-truncation reading
on two distinct measured frames (RECALL-06). The reachable domain is the
panel's own, **0–199**. Bytes 200–255 are unprobed.
For `mode`, the index is usually the mode reached, but not always —
index 40 lands on 42 — and a raw index can open a screen the panel menu does
not expose, some of which act on entry (mode 42 tries to read a USB medium).
See `research/wpj-format-registry.md`, sections RAW-01 and RECALL-03.

A recall changes what the controller is playing, live. It writes nothing:
`projectChanged` stays false. **Recalls sent close together can be swallowed**:
from a settled state, recalls 8 s apart all landed, while one sent 4 s after a
reset to id 114 did not. Delay and reset preset are still confounded — a script
firing cues faster than that may drop them silently.

**`mode` can trap the panel.** The reported `wolfmixMode` is not the screen on
display: the controller answers the index you sent, and lights the matching
LED, while the front panel stays where it was. Modal screens trap it: 26
(Projects) is entered remotely and not left — neither `mode 0` nor
`mode 5` nor `mode 16` dismisses it. 42 (USB stick) escapes the same way
(index 1) but has never been tested against 0/5/16. What breaks out of 26,
measured: `1` (COLOR FX), `3` (MOVE FX), `8` (GOBO), `33` (BLACKOUT). What
does not: `0` (HOME), `5` (PRESETS), `16` (the main menu). Why those four and
not these three is a **hypothesis** ("the screens that act on the light"),
with an untested rival and a pre-registered discriminator — indexes 28 and 30
(SCREEN-02). **The panel's keys and `SET_MODE` are two different paths**: from
the Projects screen the physical keys — HOME included — do bring up their
screen, while indexes 0, 5 and 16 do not, replayed on a second live copy
(SCREEN-03, device-confirmed). Where an index does not take, the operator saw
the key LED light and then fall back — watched at the panel, not instrumented
— while `GET_SETTINGS` still reports the index you sent — so
four things move independently: the reported mode, the key LEDs, the pads, and
the screen. Do not send a modal index to a controller in service; if one is
stuck, send `mode 1`.

The first request after the port has been idle can time out; issue it again
(`research/wpj-format-registry.md`, LINK-01 — observed five times, undiagnosed,
and deliberately not papered over with a retry in the tool).

`GET_SETTINGS` returns 20 known fields, decoded by name: engine and USB-DMX
state, lock flags, profile and project counts, free memory, serial number,
universe count and mapping, firmware version (numeric and string),
`wolfmixMode`, `projectChanged`, and available project memory.

## `wolfmix.py`

```bash
python3 tools/wolfmix.py [--port PATH] [--timeout SECONDS] <command>
```

| Command | What it does |
|---|---|
| `settings` | full decoded settings/state as JSON. Twenty fields are named; any field number the firmware sends that we cannot name appears under `unknownFields`, raw and unlabelled — that is how you would find a setting we have not mapped, by toggling it at the panel and diffing two reads. The twenty fields we have mapped do not carry `store group dimmers in preset`, and GEN-02 never located it in this message; until the decoder's `unknownFields` output is diffed across a toggle at the panel, whether the firmware sends it under a field number we cannot name is untested. Reading it stays a human check at the panel. |
| `projects` | projects stored on the controller, with UUIDs |
| `profiles` | fixture profiles on the controller |
| `project UUID out.wpj` | download one project; refuses an existing output path |
| `experiment-uuid LABEL` | print the deterministic experiment UUID for a label |
| `dmx [--seconds N]` | stream DMX output; first frame per universe is the full set of non-zero channels, then only changes |
| `dmx-envelope out.json [--seconds N]` | per-channel min/max over a window |
| `watch-mode [--interval S] [--seconds N]` | print every change of `wolfmixMode` |
| `preset ID` | recall a preset by its id, hands-off |
| `mode NAME` | set the reported mode by name; raw indexes need `--experimental`. The panel follows for `color`, `move`, `beam` and raw 26 (Open) and stays put for `home`, `presets`, `setup` — `screenFollows` in the output says which, `null` when never measured (SCREEN-02) |
| `self-test` | protocol checks, no hardware needed |

`dmx` enables USB DMX only if it was off, and disables it again on exit.
Firmware 2.0.18 sends all four universes in one packet; the older
one-universe-per-packet layout is still handled.

**Why the envelope.** A single DMX frame is not comparable between runs because
effects animate. Per-channel min/max is: a static channel has `min == max`, an
animated one keeps its range whatever the phase. That makes it the oracle for
"did this **file** change alter the output at all".

It is not the oracle for a **command**. Two separately captured envelopes cannot
tell "nothing moved" apart from "the same thing was repainted", which is exactly
how RECALL-01 first misread the preset recalls as inert. For a command, stream
one continuous `dmx` capture and read the timestamped transitions. But on an
animated rig the single frame sits below the noise floor — one recall
re-measures 32 channels away from itself — so once the transition is located,
hold the history constant and judge the **aggregate envelope**: non-zero
channels, animated channels, sum of maxima (RECALL-04).

The **envelope** is what refuted type 102 `field 11` as inert, and what
confirmed the gobo palette: pressing pad *n* drove the group's gobo channel to
the lower bound of range *n*, with nothing else moving in 2048 channels beyond a
±1 dither already present in the baseline. A pad press was judgeable that way
because the discriminator was a static channel going 0 → 70 — there, "nothing
moved" and "the same thing repainted" cannot be confused.

Read the whole state, not the delta you expect: the same captures pinned
`115.f2` as the 0-based DMX start address, because the block boundaries were
visible in the envelope.

`watch-mode` is the ground truth for the `WM_MODE_*` enum: it polls
`GET_SETTINGS` (read-only) while the operator walks the controller through its
screens. Mapping status: [`../research/mode-map.md`](../research/mode-map.md).

## `wolfmix_experiment.py`

A transactional runner for project experiments, without WTOOLS in the loop.

**The safety envelope.** It only ever writes a project UUID derived
deterministically (UUID v5) from the experiment label, named `WMX EXP <label>`
— the **client** truncates that name to 19 characters and refuses a longer one
before it reaches the wire. What the firmware does with an over-long *project*
name has not been measured; for *preset* names it has, and the answer is brutal:
past 19 UTF-8 bytes the whole project refuses to open.
It cannot collide with one of your projects. Before initialising it snapshots
every project on the controller. Every upload is verified by downloading it
back and comparing the **record list** — payload by payload, prefix excluded,
because the controller stamps its own version counter there. `deploy` verifies
twice: once right after the store, once after the restart. On failure it
restores the previous experiment project. Each run is journalled.

```bash
python3 tools/wolfmix_experiment.py [--port P] [--state-dir DIR] <command>
```

| Command | Arguments | What it does |
|---|---|---|
| `init` | `project` `--label L` | snapshot everything, upload the base project under the experiment UUID |
| `arm` | `--label L` `--loaded-on-controller` | check the experiment project is still there under its name, record that you opened it, store the controller's current mode |
| `deploy` | `project` `--label L` `--case ID` | save the current project as `before.wpj`, upload the candidate, verify, restart the controller, verify again, capture one DMX frame, journal |

`deploy` prints one preflight warning on stderr, before it touches the
controller: if the candidate writes group dimmers anywhere, it says so. Those
values are inert unless the panel's `Settings > store group dimmers in preset`
is **on**, and that condition lives in the device, not in the project (GEN-02) —
so a show can compile, verify, deploy and still do nothing. The warning is
unconditional because no read reports the flag — it has never been located in
the Settings message, and no panel toggle has been diffed to place it there.
| `campaign` | `manifest.json` `--label L` | deploy each case in a manifest in order |
| `watch` | `--label L` `[--interval S]` | report what each controller-side save changes, record by record |
| `status` | `--label L` | current state of that experiment |
| `self-test` | — | checks without hardware |

### The one manual step

Firmware 2.0.18 exposes no USB command **we have found** to *select* a project.
So:

1. `init` — uploads `WMX EXP <label>`.
2. **Open that project once on the W1 itself, and save it without changes** —
   `arm` refuses to proceed while the controller reports unsaved changes.
3. `arm` — from here everything is automatic.

That sentence went through a full cycle on 2026-08-27. SETP-02 had closed the
question with four negatives across three manoeuvres — RESTART (twice),
delete-store-restart, engine cycle — all judged with a preset-recall
discriminator that RECALL-01 then withdrew. **One has since been re-proved with
a discriminator that does not depend on it**: RELOAD-03 deployed a 6-entry file,
restarted, then counted appearances over ten `SKIP_PRESET` — ten distinct ones,
where a live 6-entry copy gives 8 of 10 with a period of six readable in the
distances (RELOAD-05, the calibration). Note the falsifier is "fewer than ten
**and** a periodicity", not "a repeat by the seventh skip": the instrument
undercounts, because two of the four real returns did not reproduce their
frame. Store + RESTART
under the same UUID does not replace the live copy. A WTOOLS push does not
either (RELOAD-02). The other two negatives are still to be replayed.

And the screen itself is now reachable: `SET_MODE` with a one-byte payload lands
the panel on mode 26, `main menu → Open`. What has no known command is the
selection gesture on that screen.

### Recalling a preset over USB — the payload is not protobuf

The short events do **not** carry protobuf. For `SET_MODE` (39) and
`SET_PRESET` (41) the firmware reads **`payload[0]` as the index** and parses
nothing — device-confirmed, 2026-08-27.

That was found by sweeping `SET_MODE`'s fields: sending `f1=0` … `f4=0`
selected modes 8, 16, 24 and 32 — which are exactly the protobuf **tag bytes**
`0x08 0x10 0x18 0x20`. The device had been reading our tag as the index all
along, so the value behind it could never matter.

With a one-byte payload both events behave:

| Event | Sent | Result |
|---|---|---|
| `SET_MODE` | one byte: 0, 5, 26, 16, 0 (decimal) | modes 0, 5, 26, 16, 0 — **5 of 5** |
| `SET_PRESET` | one byte: 1, 5, 1, 5, 1 (decimal) | two stable fingerprints, each repeat identical to the channel |

**Addressed, deterministic, hands-off preset recall works.** And mode 26 —
`main menu → Open`, the screen whose manual use reloads a project — is
reachable remotely.

This supersedes two earlier readings on this page. RECALL-01 and RECALL-02
measured correctly and concluded that the event carried no target; the real
situation was that we had never sent one. What stays refuted as written is
`f1` = id (SETP-01) and `f2` = clamped entry position (PRESET-07) — both
described a protobuf the firmware does not read.

Both questions this paragraph used to leave open are now closed. The byte is
the **id**, not the entry position: ids 99 and 114 recall two different
presets, where a position reading makes both of them out of range and so
identical (RECALL-03). And a **second byte is not read** — the one payload
that seemed to prove otherwise was undone by its own control shot, and a fade
parameter is excluded by the transient (RAW-02).

An absent id is now closed on both sides: nothing happens, whether the id sits
above the highest one present (RECALL-04, bytes 7, 50 and 200) or inside an
interior hole (RECALL-05, id 90 between 81 and 100 — the frame stayed identical
on all 2048 channels, and the four rivals each predicted a different measured
frame). And a **present** id beyond 127 is reachable: the byte is read as-is,
bit 7 included, over the panel's whole range 0–199 (RECALL-06). Off the recall
layer the cue behaves like any other — outside the groups it addresses, an
id ≥ 128 leaves the same 2048 channels as an id < 128. `SET_PROJECT` and the
long events remain protobuf; the raw-byte reading is for the short ones.

### Campaign manifest

```json
{
  "cases": [
    {"id": "f11-zero",    "project": "candidate-f11-zero.wpj"},
    {"id": "f11-hundred", "project": "candidate-f11-100.wpj"}
  ]
}
```

`project` paths are resolved relative to the manifest. A case needs both `id`
and `project`.

### State layout

Under `.wolfmix-state/<experiment-uuid>/` (git-ignored), one directory per
experiment label:

```
baseline.wpj          the armed reference project
state.json            experiment state
snapshots/            every controller project, captured before init
watch/                projects captured by `watch`
runs/<utc>-<case>/    before.wpj, candidate.wpj, dmx.bin, journal.json
```

`runs/` is the audit trail: what was deployed, what came back, what the DMX
output looked like. It stays on your machine — `.wolfmix-state/` is git-ignored.
What a write-up in `research/` cites is the extract copied out of it into
`corpus/experiments/<ID>/`.

## Failure modes

See [`troubleshooting.md`](troubleshooting.md).
