# W1 UI mode enum (`WM_MODE_*`) — mapping status

Status vocabulary as in `wpj-format-registry.md`.

## Evidence

These are **interface constant names**, read as names, from software installed
on our own machine. Nothing from that software is reproduced here beyond the
identifiers themselves, and every numeric value in the confirmed map below was
measured on our own device rather than taken from a binary — see `LEGAL.md`.

- **[observed]** The legacy WTOOLS 1.x SDK bundle ships the enum as plain
  TypeScript with numeric values: 39 entries, `WM_MODE_HOME = 0` …
  `WM_MODE_UNREGISTERED = 38`. Listed below as the legacy numbering.
- **[observed]** WTOOLS 2.0.2 beta (build 248, Flutter AOT) carries 45 distinct
  `WM_MODE_*` identifiers in its string pool, names only, no values.
- **[observed]** The AOT string pool is not in declaration order
  (`WM_MODE_HOME` is the 41st string in binary order), so **no numeric value
  can be read from the 2.0.2 binary by string order**. Values below stay
  hypotheses until measured on the device.

## Set difference (36 common, 3 removed, 9 added)

| Only in 1.x SDK | Only in 2.0.2 |
|---|---|
| `WM_MODE_STATIC_GOBO` | `WM_MODE_GOBO` |
| `WM_MODE_POSITION_PICKER` | `WM_MODE_SEQ_POSITION_PICKER` |
| `WM_MODE_HUNGRY_WOLF` | `WM_MODE_STATIC_POSITION_PICKER` |
| | `WM_MODE_BPM` |
| | `WM_MODE_FILE_BROWSER` |
| | `WM_MODE_INTELLIGENT_PRESET` |
| | `WM_MODE_LIVE_EDIT_MACRO_EDIT` |
| | `WM_MODE_MAPPING` |
| | `WM_MODE_USB_STICK` |

**[hypothesized]** The numeric values are defined by the firmware, and the
same firmware 2.0.18 is driven by both the 1.x SDK and 2.0.2. The most
economical explanation is therefore: values 0–38 unchanged, the three removed
names are in-place renames (`STATIC_GOBO`→`GOBO` at 8,
`POSITION_PICKER`→ one of the two pickers at 12), and the six genuinely new
modes appended at 39–44. **Do not rely on this**: alternatives (renumbering
with a compatibility shim in WTOOLS, sparse values) are not excluded.

## Legacy table (1.x SDK, [observed])

```
 0 HOME              10 LIVE_EDIT             20 FIXTURE_BUILD    30 SPEED
 1 COLOR             11 STATIC_COLOR_PICKER   21 MOVE_SEQ         31 SMOKE
 2 COLOR_PICKER      12 POSITION_PICKER       22 BEAM_SEQ         32 BLINDER
 3 MOVE              13 PRESET_EDIT           23 DMX_LEVELS       33 BLACKOUT
 4 BEAM              14 GOBO_EDIT             24 GROUPS           34 HUNGRY_WOLF
 5 PRESETS           15 LIVE_EDIT_EDIT        25 SETTINGS         35 ACTIVATION
 6 STARTUP           16 SETUP                 26 PROJECTS         36 BEAM_EDITOR
 7 STATIC_COLOR      17 FIXTURE_SETUP         27 LOCK             37 SETUP_WIZARD
 8 STATIC_GOBO       18 FIXTURE_LIMIT         28 WOLF             38 UNREGISTERED
 9 STATIC_POSITION   19 FIXTURE_SELECTION     29 STROBE
```

## Confirmed map (W1 MK1 (serial withheld), firmware 2.0.18)

All values below are **[device-confirmed]**: the operator drove the front
panel while `watch-mode` polled `GET_SETTINGS`. Legacy names are the 1.x SDK
enum; where 2.0.2 renamed one, both are given.

| Value | Reached by | Name |
|---|---|---|
| 0 | idle, `HOME` | `HOME` |
| 1 | `COLOR FX` | `COLOR` |
| 3 | `MOVE FX` | `MOVE` |
| 4 | `BEAM FX` | `BEAM` |
| 5 | `PRESET` | `PRESETS` |
| 7 | STATIC `COLOR` | `STATIC_COLOR` |
| 8 | STATIC `GOBO` | `STATIC_GOBO` → **`GOBO`** |
| 9 | STATIC `POSITION` | `STATIC_POSITION` |
| 10 | STATIC `LIVE EDIT` | `LIVE_EDIT` |
| 12 | SHIFT + a position pad | `POSITION_PICKER` → **`STATIC_POSITION_PICKER`** |
| 14 | STATIC GOBO → SHIFT + a gobo pad | `GOBO_EDIT` |
| 15 | LIVE EDIT → fixture grid → EDIT | `LIVE_EDIT_EDIT` |
| 21 | MOVE FX → sequence editor | `MOVE_SEQ` |
| 16 | gear icon | `SETUP` — the main menu, parent of 19/23/25/26/43 |
| 17 | main menu → Fixtures | `FIXTURE_SETUP` |
| 19 | main menu → New, or Fixtures → ADD | `FIXTURE_SELECTION` |
| 23 | main menu → DMX VALUES | `DMX_LEVELS` |
| 25 | main menu → Settings | `SETTINGS` |
| 26 | main menu → Open | `PROJECTS` — **modal**: entered by raw index, not left by 0/5/16; escape with index 1. What the panel's own HOME key does from here is open — reported stuck one day, working the next (registry SCREEN-01/02/03) |
| 28 | `WOLF` key (chevrons) | `WOLF` — the paparazzi flash effect |
| 29 | `STROBE` | `STROBE` |
| 30 | `SPEED` | `SPEED` |
| 32 | `BLINDER` | `BLINDER` |
| 33 | `BLACKOUT` | `BLACKOUT` |
| 34 | PRESET → magic wand | `HUNGRY_WOLF` → **`INTELLIGENT_PRESET`** |
| 36 | DMX VALUES → beam editor | `BEAM_EDITOR` |
| 41 | LIVE EDIT → SHIFT + one of the first three encoders | **`LIVE_EDIT_MACRO_EDIT`** (new) — present on MK1 |
| 43 | main menu → Mappings | **`MAPPING`** (new) — present on MK1 |
| 39 | **unreachable by menu** — raw index 39; the **pads** light what the operator reads as the Move FX sequencer picker, while the **screen stays on HOME** | **`SEQ_POSITION_PICKER`** (new) — by elimination, name **hypothesized** |
| 40 | **unreachable by menu** — raw index 40 **redirects to 42** (three times out of three) | **`FILE_BROWSER`** (new) — by elimination, name **hypothesized** |
| 42 | **unreachable by menu** — `SET_MODE` raw index 40 lands here | **`USB_STICK`** (new) — operator-identified on screen; attempts a read on entry; escape with index 1 — never tested against 0/5/16, so "modal" is by analogy with 26, not measured |
| 44 | HOME → touch the tempo readout | **`BPM`** (new) |

**Result: the legacy 0–38 numbering is unchanged in firmware 2.0.18.** The
three names that vanished from the SDK are renames at their original values
(8, 12, 34); the six genuinely new modes live at 39–44, of which `BPM` = 44 is
confirmed and 43 is seen but unnamed.

`USB_STICK` is now **42**, measured 2026-08-27: `SET_MODE` with the raw index
byte **40** lands on mode 42, and the operator reads the screen — USB STICK,
with import/export of project, fixtures and full backup. It attempts a read on
entry and, with no medium (MK1 has no USB-A socket), shows "error reading
project"; import repeats it, export gives "error backing up data". Two
consequences: **the panel menu does not expose this screen, the raw index
does** — so an index probe is not a neutral act, it can start an action — and
the index→mode identity is not universal (0→0, 5→5, 16→16, 26→26 are exact,
40→42 is not). **[device-confirmed]** for 42; **[hypothesized]** that 40 is
`FILE_BROWSER` redirecting for want of a medium, leaving 39 for
`SEQ_POSITION_PICKER` by elimination — neither is measured.

The other two slots were measured the same day, same method. **Index 39**:
the screen does not move — it stays on HOME — but the **pads change**, and the
operator reads them as the Move FX sequencer's position picker. **Index 40**:
the panel shows the USB-stick screen and its "cannot load a project" error,
i.e. it **redirects to 42**, reproduced three times. Behaviour
**[device-confirmed]**; the two *names* are **[hypothesized]**, by elimination
against the 2.0.2 identifier list — a picker that paints pads without a screen
fits `SEQ_POSITION_PICKER`, and a browser that falls through to the USB screen
for want of a medium fits `FILE_BROWSER`. Nothing in the binary binds either
name to either number.

Note what index 39 adds to SCREEN-01: the firmware moves **three** things
independently — the reported mode, the pad LEDs, and the screen. Mode 39
moves the first two and leaves the third alone.

Previously unmeasured: `FILE_BROWSER`, `SEQ_POSITION_PICKER` and `USB_STICK`
shared the three remaining slots 39, 40 and 42. The macro editor turned out to exist
on MK1 (feature list: PRISM ROT., SMOKE, STROBE, ZOOM, DIMMER, EFFECT, FOCUS,
GOBO ROT., IRIS; value 0–100 %; per-fixture selection) and sits at 41. Neither picker showed up
inside its parent editor: the whole sequence session (group toggle, step
buttons, settings sub-page) stayed at 21, and the gobo edit stayed at 14. `USB_STICK` and
`FILE_BROWSER` are probably unreachable here (the USB-A socket is MK2+).
`MAPPING` turned out to exist on MK1 after all, at 43 — operator-confirmed by
toggling between it and the main menu with the back button. Also unreached:
`GROUPS` (24) — the
A–D / E–H bank switch is SHIFT + `BPM TAP`, which changes no mode.

## MODE-01 results — 2026-08-25, W1 (serial withheld), fw 2.0.18

Method: `tools/wolfmix.py watch-mode --interval 0.15` (GET_SETTINGS polling
only, zero writes) while the operator walked the front panel, returning to
HOME between each  step so the capture self-synchronises on mode 0. Raw capture:
`research/mode-01-session.jsonl`. Controller state before and after:
`wolfmixMode 0`, `projectChanged false`, unlocked.

**[device-confirmed]** — front-panel key → value, unambiguous (one key, one
transition, HOME on both sides):

| Value | Key pressed | Legacy 1.x name | Verdict |
|---|---|---|---|
| 0 | (idle) / `HOME` | `WM_MODE_HOME` | unchanged |
| 1 | `COLOR FX` | `WM_MODE_COLOR` | unchanged |
| 3 | `MOVE FX` | `WM_MODE_MOVE` | unchanged |
| 4 | `BEAM FX` | `WM_MODE_BEAM` | unchanged |
| 5 | `PRESET` | `WM_MODE_PRESETS` | unchanged |
| 7 | STATIC `COLOR` | `WM_MODE_STATIC_COLOR` | unchanged |
| 8 | STATIC `GOBO` | `WM_MODE_STATIC_GOBO` | **renamed in place** to `WM_MODE_GOBO` |
| 9 | STATIC `POSITION` | `WM_MODE_STATIC_POSITION` | unchanged |
| 10 | STATIC `LIVE EDIT` | `WM_MODE_LIVE_EDIT` | unchanged |
| 16 | main menu (gear icon) | `WM_MODE_SETUP` | unchanged; parent of 17/25/26/43 |
| 17 | main menu → fixture patch | `WM_MODE_FIXTURE_SETUP` | unchanged |
| 25 | main menu → settings | `WM_MODE_SETTINGS` | unchanged |
| 26 | main menu → projects | `WM_MODE_PROJECTS` | unchanged |
| 28 | `WOLF` key (chevrons) | `WM_MODE_WOLF` | unchanged |

**[correlated]** — FX keys, mapping rests on the press order being the panel
order (STROBE, BLINDER, SPEED, BLACKOUT top to bottom). Every value then lands
on its legacy name, which a wrong order would not produce:

| Value | Key | Legacy name |
|---|---|---|
| 29 | `STROBE` | `WM_MODE_STROBE` |
| 30 | `SPEED` | `WM_MODE_SPEED` |
| 32 | `BLINDER` | `WM_MODE_BLINDER` |
| 33 | `BLACKOUT` (toggles, observed twice) | `WM_MODE_BLACKOUT` |

**[observed]** — one value outside the legacy range:

- **43**, entered from the main menu (16) right after leaving Settings, held
  1.4 s, returned to 16. Which menu entry produced it is not yet known. It
  falls in the 39–44 window predicted for the six genuinely new modes.

**[observed]** — keys that changed no mode: `SMOKE` and `BPM TAP` (single tap)
and `SHIFT` alone. `BPM TAP` is a tap-tempo key; the guides say the BPM
*screen* is reached by touching the tempo readout in the HOME toolbar.

### Conclusion so far

The hypothesis holds where it was tested: **legacy values 0–38 are unchanged
in firmware 2.0.18**, 14 of them device-confirmed, 4 more correlated, and one
removed name (`STATIC_GOBO`) is a pure rename at its original value 8. New
modes live above 38; 43 is the first one seen.

### Resolved: there was never a `GROUPS` key

Earlier rounds mislabelled the chevrons key as `GROUPS`. It is the **`WOLF`**
key, and it reports **28** = `WM_MODE_WOLF`, its own legacy name — nothing to
explain. Groups are not a panel key at all: the A–D / E–H bank switch is
SHIFT + `BPM TAP`, and it changes no mode. `WM_MODE_GROUPS = 24` stays
unreached; if it exists on MK1 it is somewhere else entirely.

## MODE-01 round 2 — touchscreen and menu paths, same session

**[device-confirmed]** new findings:

| Value | Path | Name | Note |
|---|---|---|---|
| 44 | HOME → touch the tempo readout | `WM_MODE_BPM` | **first value above the legacy range** |
| 34 | PRESET → magic-wand icon | `WM_MODE_INTELLIGENT_PRESET` | legacy `HUNGRY_WOLF` **renamed in place** |
| 12 | STATIC POSITION → SHIFT + a position pad | `WM_MODE_STATIC_POSITION_PICKER` | legacy `POSITION_PICKER` renamed in place |
| 19 | main menu → Fixtures → ADD | `WM_MODE_FIXTURE_SELECTION` | unchanged |
| 23 | main menu → DMX VALUES | `WM_MODE_DMX_LEVELS` | unchanged |
| 36 | DMX VALUES → beam editor | `WM_MODE_BEAM_EDITOR` | unchanged |
| 28 | `WOLF` key (chevrons) | `WM_MODE_WOLF` | **operator-confirmed**: the wolf auto-effect |

**[observed]**, name still open:

- **43** — a project-menu entry (New / Open / Save), reached twice from mode 16.
  The three entries were visited in one pass so the pairing is not yet
  unambiguous. Round-3 target.
- **15** — LIVE EDIT → editing screen. Both `WM_MODE_LIVE_EDIT_EDIT` (legacy 15)
  and the new `WM_MODE_LIVE_EDIT_MACRO_EDIT` exist in 2.0.2, so they must hold
  different values; which one is 15 depends on whether the pad or the encoder
  was used. Round-3 target.

**[device-confirmed]** operator report: `WM_MODE_GROUPS` (24) was still not
reached. Group banks A–D / E–H are switched with SHIFT + `BPM TAP`, which
produces no mode change. On a MK1 there may be no groups screen at all.

**Unreachable on this hardware (MK1)**: `USB_STICK`, `FILE_BROWSER` (USB-A
socket is MK2+), and probably `MAPPING` (MIDI is MK2+).

## MODE-01 round 3 — menu entries isolated, and a lesson

**[device-confirmed]**

- The chevrons key gives **28** again, on its own, isolated from any other
  action. The operator describes it as the wolf auto-effect with a TOGGLE
  release, which matches guide 10. `34` therefore stays with the magic wand:
  it was entered from the PRESET screen and returned to it.
- main menu → **New** = **19**: creating a project drops straight into fixture
  selection. → **Open** = **26**. → **Save** changes no mode at all; it is a
  dialog drawn inside mode 16.
- **43 = `WM_MODE_MAPPING`**, main menu → Mappings. Identified by the operator
  in a self-driven session: 16 and 43 alternate cleanly as Mappings is entered
  and left with the back button. It is the second value confirmed above the
  legacy range, and it shows MK1 hardware does expose the Mappings screen.

**Invalidated by the operator's own report**: `New` created an empty project,
so steps 4–7 of round 3 ran with **no fixtures patched**. LIVE EDIT pad edit
and SHIFT + encoder both reported 15, MOVE FX stayed at 3, and SHIFT + a gobo
pad stayed at 8 — all inconclusive, because those sub-screens have nothing to
edit in an empty project. `LIVE_EDIT_MACRO_EDIT`, `MOVE_SEQ` (21),
`GOBO_EDIT` (14) and `SEQ_POSITION_PICKER` must be retested on a project with
fixtures.

**Controller integrity after the incident**: the five stored projects are
unchanged and `WMX EXP format-lab` re-downloads byte-identical
(`171ae1c5acf1baa1de8947fc250f3c0a1c7b07e912fce69c6203f744db3bcd99`). The new
project only ever existed in RAM; nothing was saved over anything.

**Lesson for future probes**: on this firmware a menu entry acts immediately,
there is no confirmation dialog. Never ask the operator to "open and leave" an
entry whose name implies a state change.

## MODE-01 round 4 — sub-editors, on a project that has fixtures

**[device-confirmed]**, operator narrating each gesture:

- **21 = `MOVE_SEQ`** — MOVE FX → sequence editor. Everything done inside it
  (gear sub-page, enabling then disabling the sequence on group A, a pad, the
  STEP 1/4 touch button) stayed at 21.
- **14 = `GOBO_EDIT`** — STATIC GOBO → SHIFT + a gobo pad, 27 s, back to 8.
- **15 = `LIVE_EDIT_EDIT`** — reached through the fixture grid → EDIT → channel
  list. Toggling a live edit pad on and off does **not** leave mode 10, which
  corrects the round-3 reading.

`LIVE_EDIT_MACRO_EDIT` is still unmeasured. Guide 9 describes a different
screen from the one reached here: SHIFT + press one of the first three
encoders should open a **feature chooser** (first encoder picks which feature
the macro controls, third filters the fixture grid by group), not the channel
list. Whether a MK1 exposes it is unknown.

## Flash FX buttons — project data worth decoding

Guide 10 documents the six flash keys (`WOLF`, `STROBE`, `BLINDER`, `SPEED`,
`BLACKOUT`, `SMOKE`) and three settings each, all of which must live inside
the project file:

- **Release mode**, set with the fourth encoder: `FLASH` (on press, off on
  release), `TOGGLE`, or a `1s` / `5s` / `10s` timer.
- **Per-effect parameters**: strobe speed, blinder fade-out time, speed
  multiplier (FREEZE / 0.5× / 2× / 4× / 8×), smoke intensity and fan speed.
- **Group exclusion**, from main menu → Settings → Project → pick the flash
  effect → fourth encoder selects the excluded group(s).
- The flash screens themselves can be disabled in the settings; they are then
  reached with SHIFT + the flash key.

**[hypothesized]** These six effects × (release mode, parameters, excluded
group mask) are a compact, highly structured block — an ideal differential
target. Six unknown TLV types are still unattributed (110, 111, 115, 116, 120,
125, 130, 151, 155, 161). Planned experiment **FX-01**: download the
experiment project, change exactly one release mode on the W1, save, download
again, diff records.

### Navigation facts extracted from the embedded guides (WTOOLS 2.0.2)

The W1 screen is a **touchscreen**, which is how the remaining modes are
reached:

- BPM screen: touch the tempo readout in the HOME toolbar.
- Intelligent Preset: magic-wand icon, top right of the PRESET screen.
- Mappings (MIDI/DMX): main menu → Mappings.
- USB stick export/import: USB icon on the main menu (FAT32 stick required).
- Live Edit Macro edit: on the LIVE EDIT screen, SHIFT + press one of the
  first three encoders.
- Static position picker: SHIFT + one of the position pads on the STATIC
  POSITION screen.

## How to measure without mutating anything (planned, MODE-01)

`Settings.wolfmixMode` (protobuf field 17, already decoded by
`tools/wolfmix.py settings`) reports the controller's current UI mode. Polling
`GET_SETTINGS` while the operator walks the W1 through its screens yields
ground truth `screen → number` with **zero writes** to the controller. Only
modes unreachable by hand then need a `SET_MODE` probe (event 39, reversible
with `SET_MODE 0`).
