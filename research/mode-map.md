# W1 UI mode enum (`WM_MODE_*`) — mapping status

Status vocabulary as in `wpj-format-registry.md`.

## Evidence

- **[observed]** Legacy WTOOLS 1.x SDK (`/tmp/wolfmix-sdk-inspect/main.cjs`)
  contains the complete TypeScript enum with numeric values, 39 entries,
  `WM_MODE_HOME = 0` … `WM_MODE_UNREGISTERED = 38`. Reproduced in the table
  below; extraction command:
  `grep -o 'WM_MODE_[A-Z_0-9]*=[0-9-]*' main.cjs`.
- **[observed]** WTOOLS 2.0.2 (build 248, Flutter AOT) contains 45 distinct
  `WM_MODE_*` strings. Extraction: `grep -o 'WM_MODE_[A-Z_0-9]*'` over
  `/tmp/wtools-2.0.2-strings.txt`, deduplicated.
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

## How to measure without mutating anything (planned, MODE-01)

`Settings.wolfmixMode` (protobuf field 17, already decoded by
`tools/wolfmix.py settings`) reports the controller's current UI mode. Polling
`GET_SETTINGS` while the operator walks the W1 through its screens yields
ground truth `screen → number` with **zero writes** to the controller. Only
modes unreachable by hand then need a `SET_MODE` probe (event 39, reversible
with `SET_MODE 0`).
