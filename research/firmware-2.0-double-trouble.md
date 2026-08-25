# Firmware 2.0 "Double Trouble" — external research

Survey date 2026-08-25. Target: find a public explanation for type 102
`field 11` = 100. **Result for that question: negative.** Nothing in the
2.0 feature set is a per-project numeric that defaults to 100. Details and
the residual candidates are below.

## Retrieval note

`forum.wolfmix.com` is behind a Cloudflare challenge (HTTP 403 on
`viewtopic.php?t=1101`, the English feature breakdown; same for `t=1100`,
the German one). No bypass was attempted. Everything sourced from the forum
below comes from **search-result snippets only** and is marked *low*
confidence.

The primary usable source is the **official Wolfmix W1 Reference Manual
version 2.0 (EN)**, which is public and fetchable:
<https://storage.googleapis.com/nicolaudie-us-litterature/Release/wolfmix_w1_reference_manual_en.pdf>
It documents firmware 2.0 for MK1/MK2/MK3 and contains the complete Settings
list and the complete Flash-screen chapters. Everything attributed to
"manual 2.0" below is *high* confidence.

## What Double Trouble is

Firmware 2.0, marketed as "Double Trouble", is the 2025 major update for the
Wolfmix W1 (MK1 and MK2; MK3 ships with it). The name refers to capacity
doubling: the update roughly doubles presets, live edits, palettes and — the
headline item — the number of **simultaneous FX engines**, so two Color FX,
two Move FX and two Beam FX can run at once on different groups.

Secondary themes: a "Wolfmix Intelligence" preset generator, reworked BEAM
and MOVE sequencers, finer palette control, and a reorganised Settings
screen split into four categories.

Sources: [alia.com.au hands-on](https://alia.com.au/wolfmix-beta-2-0-double-trouble-hands-on-preview-available-now/),
[Bekafun news](https://www.bekafun.com/en/news/n/880/WOLFMIX-W1-Firmware-2-0),
[Prolight+Sound exhibitor entry](https://pls.messefrankfurt.com/frankfurt/en/exhibitor-search.detail.html/lightingsoft-ag/mf_1_0015052945_4383493_10000005202501.html),
[reference manual 2.0](https://storage.googleapis.com/nicolaudie-us-litterature/Release/wolfmix_w1_reference_manual_en.pdf).

## Feature table

"Per-project?" answers the only question that matters here: could this
feature store a scalar in the project file?

| Feature | UI screen | Per-project state? | Source | Confidence |
|---|---|---|---|---|
| Two FX engines per type (Color/Move/Beam) | Home — SHIFT + COLOR/MOVE/BEAM FX toggles engine 1 ↔ 2 | Yes, but structural (duplicated FX blocks inside preset records), not a scalar | manual 2.0, Home chapter | high |
| Presets 100 → 200 | Preset screen | Capacity, not a stored value | forum snippet via search | low |
| Live Edits 40 → 80 | Live Edit screen | Capacity | forum snippet via search | low |
| Projects 6 → 100 | Setup → Projects | Device capacity; manual 2.0 states "Up to 100 projects, or 3.5mb" | manual 2.0, Projects chapter | high |
| Gobos / positions / colors: 20 per group, 4 pages | Static Gobo / Static Position / Static Color, "Expand Mode" | Palette data, arrays not scalars | manual 2.0 | high |
| Intelligent Preset (generates ~80 presets) | Preset → Intelligent Preset (`WM_MODE_INTELLIGENT_PRESET`) | Generates presets; no persisted parameter documented | manual 2.0 TOC; alia.com.au | high / medium |
| Wolf Rider Beam FX, criss-cross beams | Beam FX | Per-preset FX type enum | Bekafun; forum snippet | medium |
| Sequencer with phase and fade | Move FX / Beam FX sequencer | Per-preset FX properties | manual 2.0 | high |
| LIME channel support | Color Picker, RGB+ mode | Per-fixture channel data | Bekafun; forum snippet | medium |
| FOCUS OFFSET, FAN, CROSS | Move FX + Fixture Offset Mode | Per-fixture / per-preset | manual 2.0, Move FX chapter | high |
| Preset combining / stacking | Preset screen | Per-preset flags | forum snippet (t=1111) | low |
| Fixture & Group FX linking (LINK NONE / GROUP / FIXTURE) | Color/Move/Beam FX screens | Per-preset enum | manual 2.0 | high |
| Flash MIDI mapping; new Mappings screen | Setup → Mappings (`WM_MODE_MAPPING`) | Mappings are project data per manual ("Group names and mappings") | manual 2.0 | high |
| Settings split into DMX / General / Project / Presets | Setup → Settings | The **Project** category is the four flash-FX group exclusions — already decoded as f1/f3/f8/f10 | manual 2.0, Settings chapter | high |
| USB stick import/export | Setup → USB (MK2+) | No | manual 2.0 | high |
| BPM screen | `WM_MODE_BPM` | Live state | manual 2.0 TOC | high |

### The full Settings list in 2.0 (manual 2.0, verbatim item names)

DMX: XLR A – XLR D. General: WLINK input mode, Audio input level, Display
brightness, Button brightness, Lock password, Jump back on mode release,
Live Edit release mode, Show Flash FX Screens, Auto switch group bank,
Switch group bank, Retro mode, Quick Setup (beta). Project: Exclude Wolf,
Exclude Strobe, Exclude Blinder, Exclude Blackout. Presets: Store group
dimmers in Preset, Include Flash buttons in Preset, Fade effects during
preset change, Show color preview on Preset, Startup on Preset screen.

**This is the decisive negative.** The Project category contains exactly the
four exclusion masks we have already attributed, and every other Settings
item is either an enum or a boolean, or (brightness, audio gain) explicitly
controller-global. The manual states plainly that settings from the Settings
screen "are not saved within the project". **There is no numeric
project-scoped setting in the 2.0 Settings screen that could be `field 11`.**

The Flash chapters are equally closed: Wolf has no encoder action at all;
Strobe has speed only (= f9); Blinder has fade-out only (= f2); Speed has the
multiplier only (= f7); Blackout has nothing; Smoke has intensity and fan
(= f6/f5). Release mode is the fourth matrix column on each (= f4). Every
documented flash parameter is already mapped.

## Candidates for type 102 `field 11`

Ranked. Each names a single device-side change to make, save, and diff.

### 1. MAIN dimmer (master level) — medium confidence, testable

The Home screen carries a **MAIN dimmer** next to the group dimmers, changed
with **SHIFT + any encoder** (manual 2.0, Home chapter). Its resting value is
100 %: a forum thread title asks why WTOOLS dims "the Wolfmix Main Dimmer
from 100% to 20%" ([t=430](https://forum.wolfmix.com/viewtopic.php?t=430),
title text from search results, *low* confidence on the body). A 0–100 master
level defaulting to 100 is the single best-fitting explanation for a field
that reads 100 in every corpus file, and it belongs naturally next to
BLACKOUT and the flash-FX state in record 102.

**Caveat that must be cleared first:** `wpj-format-registry.md` (FX-09)
records "master brightness set to 80 %" as a negative, but does not name the
screen. The 2.0 Settings screen contains *Display brightness* and *Button
brightness*, which are unambiguously global; the Home MAIN dimmer is a
different control. If the earlier test used the Settings item, this candidate
is untested.

**Test:** on Home, hold SHIFT and turn any encoder until MAIN reads ~50 %,
then Setup → Project → Save. Diff. Expect `f11` 100 → ~50.

### 2. A group-dimmer or preset-scope master captured at save time — low

Related to (1): 2.0 adds "Store group dimmers in Preset". If group dimmers go
into preset records, a single project-level master could still be the leftover
scalar in 102.

**Test:** same as (1) but instead pull one group dimmer (encoder A) to 50 %
and leave MAIN at 100, save, diff. If a *group* value moves and `f11` does
not, (2) is dead and (1) is cleanly isolated.

### 3. BLINDER level — low, and only indirectly testable

Existing repo hypothesis. The manual defines Blinder as setting "all dimmers
to 100%" (manual 2.0, Blinder chapter), so a stored 100 is a literal match.
But the Blinder screen exposes **no** encoder parameter on MK1/MK2, so there
is no way to change it from the device UI — which makes it unfalsifiable by
the diff method and therefore a poor candidate to spend a save on.

**Test (weak, indirect):** none available on-device. Only WTOOLS or a
firmware with a Blinder-level control would move it.

### 4. Vestigial / reserved writer constant — this is the honest default

`field 11` is 100 in every file, across writer-schema versions 8, 10 and 11,
and every parameter the official 2.0 manual documents for the six flash
screens is already attributed to another field. A field that never varies
across three schema generations and has no documented control behind it is
most economically explained as a **reserved slot or a hard-coded default**
(a percentage scale, a 100 % output ceiling, an unshipped feature) that the
writer emits unconditionally. No test can confirm this; it is what remains
if candidates 1–3 all fail.

## Ruled out

| Not `field 11` | Why |
|---|---|
| Any 2.0 "doubling" (presets 200, live edits 80, projects 100, palettes) | Capacities of the *device*, not per-project values. If `f11` were a preset capacity it would read 200 in 2.0-written corpus files; it reads 100 everywhere. |
| Second FX engine | Structural duplication inside preset records; the operator already confirmed only record 102 moves for flash-FX edits, and FX engines are not flash FX. |
| Intelligent Preset | An action that writes 80 preset records; nothing scalar persists in 102. |
| Wolf Rider, criss-cross, sequencer phase/fade | Per-preset FX type and FX property values, in preset records. |
| LIME support, focus offset | Per-fixture channel/offset data, not flash FX. |
| Expand Mode (20 items visible) | UI view state, not persisted per project. |
| Flash MIDI mapping / Mappings screen | New in 2.0, but mappings are a list; a new record type is expected, not a scalar in an existing one. `f11` predates 2.0 anyway. |
| Universe activation (2 vs 4) | See below — tied to the serial number and an in-app purchase, device-global. |
| Settings → General items | Manual 2.0: Settings-screen values are not saved in the project; brightness was already measured as a no-op. |
| Settings → Presets items | All five are booleans. |

## Universes, activation and add-ons

- The W1 is advertised as supporting **up to 4 DMX universes**; the Settings
  DMX category maps XLR A–D to universes 1–4 (manual 2.0). This matches the
  `activatedUniverses = 2` / `availableUniverses = 4` the W1 reports.
- **Universe 2 is free**: it only requires assigning an XLR socket to it in
  Settings (forum snippets, [t=455](https://forum.wolfmix.com/viewtopic.php?t=455),
  [t=877](https://forum.wolfmix.com/viewtopic.php?t=877) — *low* confidence,
  bodies not retrievable).
- **Universes 3 and 4 are a paid add-on** bought through WTOOLS. Manual 2.0,
  WTOOLS chapter: purchase add-ons "including extra DMX universes, WLINK and
  3D Link". WLINK status is shown on the WTOOLS *My Wolf* screen as an
  in-app-purchase flag. *high* confidence.
- Activation itself is a **per-controller** flow: a registration code shown on
  the device, exchanged for an activation key at
  [wolfmix.com/activate](https://www.wolfmix.com/en/activate); the serial and
  activation key are displayed on the Settings screen. *high* confidence.

**Conclusion for the project file:** entitlements are bound to the serial
number and to the cloud account, not to a project. Nothing suggests a
per-project feature gate, and a gate would not be encoded as 100. Universe
*assignment* of a fixture (universe + address) is project data, but it lives
with the fixture records, not in 102.

## Project file format and backwards compatibility in 2.0

*All of this is from search-result snippets of Cloudflare-blocked forum
threads; treat as **low** confidence and verify on-device before relying on
it.*

- Upgrading to 2.0 **erases all projects on the controller**; back up via
  WTOOLS first. This is stated on the public
  [alia.com.au](https://alia.com.au/wolfmix-beta-2-0-double-trouble-hands-on-preview-available-now/)
  page too (*medium* confidence) — it warns projects "will be cleared from
  the controller".
- Projects opened under 2.0 become **2.0-native and are no longer compatible
  with 1.x**; syncing a 1.x project from WTOOLS is supposed to prompt to
  convert it (the prompt was reported missing in 2.0.1,
  [t=1056](https://forum.wolfmix.com/viewtopic.php?t=1056)).
- Conversion **appends a `v2` suffix** to the project name, deliberately, so
  the 1.x original is not overwritten on backup.

That last point is the only format-level claim with a testable side effect,
and it is a *name* change, not a structural one. No public source describes
the container, the record types, or a schema-version bump — consistent with
our own finding that `field 11` exists in schema 8 as well as 10 and 11.

## Bottom line

Nothing in the public 2.0 material explains `field 11`. The 2.0 feature set
is capacity increases, a second FX engine, palette/sequencer refinements and
a Settings reorganisation; none of it introduces a per-project scalar with a
default of 100, and the official 2.0 manual's Settings and Flash chapters
account for every flash-FX parameter already attributed to fields 1–10.

The one action worth taking is disambiguating the earlier "master brightness"
negative: re-test the **Home screen MAIN dimmer** (SHIFT + encoder) rather
than the Settings brightness items. If that also writes nothing, `field 11`
should be recorded as a reserved constant and the record closed.
