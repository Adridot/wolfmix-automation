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
| `settings` | full decoded settings/state as JSON |
| `projects` | projects stored on the controller, with UUIDs |
| `profiles` | fixture profiles on the controller |
| `project UUID out.wpj` | download one project; refuses an existing output path |
| `experiment-uuid LABEL` | print the deterministic experiment UUID for a label |
| `dmx [--seconds N]` | stream DMX output; first frame per universe is the full set of non-zero channels, then only changes |
| `dmx-envelope out.json [--seconds N]` | per-channel min/max over a window |
| `watch-mode [--interval S] [--seconds N]` | print every change of `wolfmixMode` |
| `self-test` | protocol checks, no hardware needed |

`dmx` enables USB DMX only if it was off, and disables it again on exit.
Firmware 2.0.18 sends all four universes in one packet; the older
one-universe-per-packet layout is still handled.

**Why the envelope.** A single DMX frame is not comparable between runs because
effects animate. Per-channel min/max is: a static channel has `min == max`, an
animated one keeps its range whatever the phase. That makes it the oracle for
"did this project change alter the output at all" — see `research/` for how it
settled the type-102 field-11 question.

`watch-mode` is the ground truth for the `WM_MODE_*` enum: it polls
`GET_SETTINGS` (read-only) while the operator walks the controller through its
screens. Mapping status: [`../research/mode-map.md`](../research/mode-map.md).

## `wolfmix_experiment.py`

A transactional runner for project experiments, without WTOOLS in the loop.

**The safety envelope.** It only ever writes a project UUID derived
deterministically (UUID v5) from the experiment label, named `WMX EXP <label>`.
It cannot collide with one of your projects. Before initialising it snapshots
every project on the controller. Every upload is verified by downloading it
back and comparing bytes. On failure it restores the previous experiment
project. Each run is journalled.

```bash
python3 tools/wolfmix_experiment.py [--port P] [--state-dir DIR] <command>
```

| Command | Arguments | What it does |
|---|---|---|
| `init` | `project` `--label L` | snapshot everything, upload the base project under the experiment UUID |
| `arm` | `--label L` `[--loaded-on-controller]` | record that the experiment project is the one loaded, capture the reference DMX |
| `deploy` | `project` `--label L` `--case ID` | upload one candidate, verify, capture DMX, journal |
| `campaign` | `manifest.json` `--label L` | deploy each case in a manifest in order |
| `watch` | `--label L` `[--interval S]` | report what each controller-side save changes, record by record |
| `status` | `--label L` | current state of that experiment |
| `self-test` | — | checks without hardware |

### The one manual step

Firmware 2.0.18 exposes no USB command to *select* a project. So:

1. `init` — uploads `WMX EXP <label>`.
2. **Open that project once on the W1 itself.**
3. `arm` — from here everything is automatic.

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
output looked like. It is what a write-up in `research/` cites.

## Failure modes

See [`troubleshooting.md`](troubleshooting.md).
