# Tool reference

Every tool is a standalone `python3` script in `tools/`, standard library only.
Run them **from the repository root** — the self-checks resolve `corpus/`
relative to the working directory.

Three conventions hold everywhere:

- **Run with no arguments = self-check.** Each tool proves its own invariant and
  exits non-zero if it cannot. Some prove it over your corpus (`wpjlib`,
  `wpj_codec`, `wpj_bc`, `wpj_api`, `wpj_identities`, `wpj_show`,
  `wpj_generate`); the others prove it against frozen inputs in their own
  source (`wpj_inspect`, `wpj_position`), against a tree they build themselves
  (`gobo_run`), or against the git index (`wpj_privacy`, `wpj_links`). **The
  canonical list is `tools/check.py`** — read it rather than a count written
  here. `wpj_diff.py` self-checks too but is not wired into it.
- **`make check` runs `tools/check.py`, which aggregates.** It runs every check
  even after one fails, then prints a summary naming each abstention. Exit 0 =
  all passed, 3 = green with abstentions, 1 = a failure. `--abstentions-ok`
  turns 3 into 0 for a context that expects them, such as the corpus-free CI
  job.
- **`wpj_links.py` checks the cross-references.** Every Markdown link in a
  tracked document must land on a tracked path; a renamed file that leaves a
  document pointing at nothing fails `make check`. It also checks **finding
  ids**: every `ACC-01`-shaped citation anywhere in the tree must resolve to an
  entry in [`research/evidence.md`](../research/evidence.md).
- **`wpj_counts.py` checks the figures.** Counts that move as the work moves
  — decoded and passthrough records, identities, checks — are computed from
  the code. A document that states one marks it with `<!--count:name-->` or
  `<!--types:name-->`, and a marker the code no longer supports fails
  `make check`. `python3 tools/wpj_counts.py --print` prints them all.
- **`wpj_evidence.py` keeps the spec honest.** `SPEC.md` declares an evidence
  cutoff and a pending list; the gate fails when a finding in
  [`research/evidence.md`](../research/evidence.md) is newer than the cutoff
  and unlisted, when a `SPEC §` reference points at no section, or when the
  specification leans on a finding the ledger has taken back.
- **`tests/` covers the refusals.** `python3 -m unittest discover -s tests -t .`
  (also the last line of `make check`) exercises what the tools reject:
  truncated files, impossible varints, an event outside the allowlist, an
  untested firmware, a raw mode, a failed rollback, an archive with no
  manifest, a flash from another bundle, an icon id out of the table, a broken
  PNG, an existing output. It builds its own bytes, so unlike the self-checks
  it never abstains.
- **No corpus, no claim.** No project file ships with this repository
  ([`../LEGAL.md`](../LEGAL.md)). The corpus root is `corpus/`, or `$WPJ_CORPUS`
  if set; with nothing there, a self-check prints one line saying it abstained
  and exits 0. See [`corpus.md`](corpus.md).
- **Writes never overwrite.** Output files are opened with mode `x`; an
  existing path is an error, not a target.

Tool output strings are partly still in French; the JSON keys are stable.

---

## `wpjlib.py` — variant-A container

The read/write core. Splits a file into raw TLV records without interpreting
them, reassembles with lengths and the SHA-1 header recomputed, and preserves
bytes 20–0x3F (the 44-byte opaque prefix) verbatim; the 6-byte root header at
0x40 is recomputed from the reassembled body.

```python
import wpjlib
w = wpjlib.Wpj.load("in.wpj")          # raises ValueError on a bad SHA-1
w.records                               # [(type:int, payload:bytes), ...]
w.replace(165, new_payload, occurrence=0)
sha256 = w.save("out.wpj")              # refuses to overwrite
```

`Wpj.from_bytes(data)` parses without touching the filesystem — that is what
the device runner uses on a freshly downloaded project.

`wpjlib.corpus_files()` is the shared corpus discovery used by every
self-check: it globs `**/*.wpj` under `$WPJ_CORPUS` (default `corpus/`).

**Invariant:** an unmodified record is re-emitted byte for byte, so load+save
without an edit produces a byte-identical file. Self-check: every variant-A file
in the corpus (45 of the 51 `.wpj` on the development machine — the other six
are variant B/C and out of scope for this library).

```bash
python3 tools/wpjlib.py     # self-check
```

## `wpj_codec.py` — semantic JSON ↔ bytes

Per-record-type decode/encode on top of `wpjlib`.

```bash
python3 tools/wpj_codec.py project.wpj   # full record tree as JSON
python3 tools/wpj_codec.py               # fidelity self-check over the corpus
```

The safety contract is the point: `decode(type, payload)` returns a
JSON-compatible dict whose `encode` reproduces the **exact** original bytes,
and it verifies that itself before returning. If a type has no schema, or the
protobuf is unexpected, it returns `{"raw": "<hex>"}` — never a partial or
approximate decode.

Naming: a field whose meaning is proven gets a semantic key (`name`, `profile`,
`effect`, …); an unidentified field keeps a neutral `fN` key. An absent field is
absent from the dict — never a synthesised `0`.

Decoded today: 101, 102, 105, **111**, 115, 116, 120, 125, **130**, 135, 140,
145, 150, **151**, 160, 165 <!--types:decoded--> — 16 <!--count:decoded-->.
`python3 tools/wpj_counts.py --print` prints the split, and `wpj_codec.SCHEMAS`
is the source of truth for it.

Note on 105: the keys are `offset_106` and `entry_count_106`, not an address and a
channel count — see `SPEC.md` §7. The old names were a misreading.

Passthrough (round-tripped, undecoded): 106, 110, 155, 161
<!--types:passthrough--> — 4 <!--count:passthrough-->. Several of these have a
documented structure in `SPEC.md` without a codec schema yet.

The self-check reads only the corpus you supply. It does **not** scan your
WTOOLS installation; copy what you want tested into the corpus root instead.

## `wpj_identities.py` — structural identities

```bash
python3 tools/wpj_identities.py    # self-check, part of `make check`
```

Each identity is an arithmetic constraint between two records — true on every
file or false. A reading that breaks one is refuted without touching hardware,
which is the cheapest kind of proof available here.

Checked today — 18 <!--count:identities-->, plus two before/after pair checks
(F30-04, and the FLASH-09 pair — the files, not its retracted reading):

| Identity | What it kills |
|---|---|
| `110[c].f2 == len(111 slice of c)` | reading `110.f2` as a feature enum |
| every `[145 item].f2` ∈ `[111 gobo ranges].f4` | a palette id that is not on the wheel. The stronger ordered equality ("the palette is derived from the patch") held on device-born projects only — refuted 2026-08-31 by a WTOOLS-imported project whose palette is the B-side 10-slot selection (EXP-06) |
| `105.f4`/`f7` tile `[0, count(106))` | reading `105.f4` as a DMX start address |
| `115.f2` windows never overlap | any patch reading that lets two fixtures share a channel |
| `115.f4 == 105.f6` == the group index | the "nine categories" reading of record 125 |
| `165.f16` = twelve 9-bit group masks | reading `f16` as complementary pairs |
| `111.f1`/`f2` are DMX bounds, every channel accounted for | a range table with holes |
| `106.f4` determines the feature `110.f4` | reading the role and the feature as independent |
| `115.f6` is a complete permutation | reading the display order as a partial list |
| `106.f1`/`f3` bound the range the role drives | an unbounded role |
| `150[slot].f2`/`f1` tile record 151 | reading 151 as a flat list |
| the preset's per-group fields are exactly 8 varints | reading any of the thirteen as a scalar |
| byte 50 is the schema version, and `165.f32`–`f35` arrive at 10 | treating the prefix as fully opaque |
| `110.f5` points at the channel's principal | guessing 16-bit byte order or adjacency |
| `155.f2` splits move (`1`, positions 0–19) from beam (`2`, 4-bit segment masks 0–15) | reading all four sequences as position indices |
| no preset name exceeds 19 UTF-8 bytes | a generator that writes a longer one and bricks the open |
| `165.f16` slice 5 == the mask of groups whose `f17` is non-zero | nothing on today's corpus — `f17` is `[255]×8` everywhere, so the identity is trivially true here. The device's own writer is what broke "slice 5 is always 255" (GEN-03, on one save); this check only guards the new reading on a file where some preset leaves a group dark |

Add one whenever a new reading implies a count, an offset or a derivation.

## `wpj_inspect.py` — variant B/C wire walk

```bash
python3 tools/wpj_inspect.py file.wpj [--depth N] > tree.json
```

Walks the raw protobuf wire format and emits field numbers, wire types and
values. No invented semantics: names are numbers, unknown bytes come out as
hex, and a length-delimited chunk is emitted as a sub-message if it parses as
one, else as text if it is printable UTF-8, else as hex — a fallback ladder,
first match wins.

Exit **2** with a message on stderr if the input is not protobuf. Variant-A
files — the small TLV containers, device dumps and WLINK imports alike — are not
protobuf at either offset, and the tool says so instead of guessing; use
`wpj_codec.py` for those.

Until 2026-08-27 this section described a contract the tool did not honour: an
unbounded varint read raised `IndexError` from the sub-message probe, escaping
the `except ValueError` that both the probe and the offset fallback rely on, so
**all six variant-B/C files exited 1 with a traceback** — the exact class of file
this tool exists to read. Fixed, with three truncated buffers added to the
self-check.

## `wpj_bc.py` — variant B/C semantic reader

```bash
python3 tools/wpj_bc.py file.wpj   # identified fields as JSON (read-only)
python3 tools/wpj_bc.py            # identity-lattice self-check over the corpus
```

The semantic layer over `wpj_inspect.py`'s raw walk, for the WTOOLS
serialization: profiles, patch, groups, presets, positions, edits, gobos come
out under their names; everything below `correlated` stays a numbered field.
The self-check re-runs the identity lattice from the registry ("Variant B/C
top-level map") on every B/C file present, and abstains without a corpus.
Strictly read-only — variants B and C have no writer, by rule.

## `wpj_api.py` — inspect JSON, `wpj-toolkit` shape

```bash
python3 tools/wpj_api.py project.wpj > inspect.json
```

Emits the same response shape as WPJ Studio's `POST /api/v1/inspect`
(`modelVersion`, `project`, `presets[]`, `fixtures`, `validation`,
`unknown_tlvs`), computed locally and offline. Tooling written against that
schema works here with no upload. See [`../PROVENANCE.md`](../PROVENANCE.md)
for why the hosted API is not called.

Two additive differences, both deliberate:

- `fixtures.status` may be `"partial"` — types 105/116 are decoded where the
  upstream schema reports `unsupported`;
- `x_records` carries the full codec decode, so nothing is lost.

`speedPercent`, `phasePercent`, `sizePercent` and `fadePercent` are emitted
without reservation: the four were measured field by field against the panel
(FX6-02/03, `SPEC.md` §5). The `unconfirmed_field_attribution` issue that used
to accompany them is gone, along with the `fN` fallbacks that carried the
retracted reading.

Variant B/C files produce an `unsupported_variant` issue rather than an error.

## `wpj_show.py` — show compiler

```bash
python3 tools/wpj_show.py compile show.json out.wpj   # compile + auto-verify
python3 tools/wpj_show.py verify base.wpj out.wpj     # list differing records
python3 tools/wpj_show.py                             # self-check
```

Applies a JSON edit spec to a donor project. A position or palette entry being
edited must already exist in the donor; everything else is preserved byte for
byte by `wpjlib`. A **preset** may also be created, by cloning one of the
donor's with the `template` key — appending a well-formed `165.f5` entry with a
free, larger id is device-confirmed (PRESET-01/06/07), and `165.f1` is left
verbatim because it gates nothing.

Preset names are capped at **19 UTF-8 bytes** and the compiler now rejects a
longer one: past that the *whole project* refuses to open on the device
(PRESET-05), and the value reads back fine, so nothing downstream would catch
it. The same cap guards gobo pad names.

The **gobo page** is edited the same way (`SPEC.md` §3.4, RENAME-01/SORT-01):
`gobo_names` writes pad names into `145.f3`, and `gobo_order` — the complete
id list of the wheel — permutes the record-111 wheel ranges and rewrites the
palette consistently, names travelling with their gobos and glyphs
resequenced. A wheel shared by a second group is refused as unmeasured. See
[`show-format.md`](show-format.md) and, for the whole icon pipeline,
[`gobo-icons.md`](gobo-icons.md).

After writing, it reloads its own output (revalidating the SHA-1), re-decodes
every edited record, checks each requested value reads back, and confirms that
**no record outside the edit set changed**. If any check fails the output file
is deleted. Exit 1 on error, 2 on bad usage.

Key reference: [`show-format.md`](show-format.md).

## `wpj_generate.py` — show generator

```bash
python3 tools/wpj_generate.py rig donor.wpj                     # read the rig
python3 tools/wpj_generate.py compose intent.json out.wpj       # compose
python3 tools/wpj_generate.py compose intent.json out.wpj --spec spec.json
python3 tools/wpj_generate.py                                   # self-check
```

One layer above `wpj_show.py`: it turns an **intention** — moods, energy,
colour, groups — into the preset bank of a show, then hands the resulting edit
spec to the compiler, so every guarantee above still applies. The rig is not
described by hand; it is read out of the donor (groups, fixtures, named
positions, per-group palettes). `--spec` writes the intermediate edit spec, and
that file is the audit trail: it names every field written.

Format reference: [`generator.md`](generator.md).

## `wpj_position.py` — the position model, executable

```bash
python3 tools/wpj_position.py     # self-check, part of `make check`
```

Computes the DMX a recalled position emits, from the project file alone:

```
pct_group(k) = (1 − FAN) + k × (2·FAN − 1) / (n − 1)     pan, k = fixture rank
pct_group    = TILT                                       tilt
pct          = clamp(pct_group + offset, 0, 1)            offset from record 151
DMX16        = borne16(f5) + pct × (borne16(f6) − borne16(f5))
```

Five records feed the formula — 150 for the group's FAN/PAN/TILT, 115 and the
address order for the rank, 151 through the `150.f1`/`f2` slice for the
per-fixture offset, 106 for the travel limits, 105 to find the channels — and
two more, 110 and 116, are walked to resolve which channel is which.

The self-check replays four DMX captures taken on the device: 24 predicted
channels, **tilt exact everywhere, pan exact everywhere but one** — the lyre at
DMX 0 on `Crowd`, where the ramp lands a hair above a boundary (39424 = coarse
154) and the device emits 153. No capture is distributed — only
the measured values are frozen in the source, which makes the model verifiable
with no hardware and breaks loudly if someone "simplifies" it.

## `wpj_privacy.py` — the anonymisation guard

```bash
python3 tools/wpj_privacy.py           # every tracked file, part of `make check`
python3 tools/wpj_privacy.py file…     # just these
```

Greps every git-tracked file for real venue, client, project, group and device
names and **exits 1 with `file:line`** if it finds one. This repository publishes
research, not the operator's rigs ([`../LEGAL.md`](../LEGAL.md)), and the names
had come back once by hand before this existed — then once more after it,
through patterns the first list did not cover.

The pattern list lives **outside** the repository — `.wpj-private-names` at the
root, git-ignored, or `$WPJ_PRIVATE_NAMES`. A guard that shipped the names it
protects would publish exactly what it is there to stop. One regex per line,
case-insensitive; prefix a line with `cs:` for a case-sensitive one, which is
what you need when the forbidden proper noun is also an ordinary word in French
code comments.

No list, no check: it abstains and says so, like the corpus self-checks.

## `wpj_diff.py` — byte-range diff

```bash
python3 tools/wpj_diff.py before.wpj after.wpj
```

Prints the differing byte ranges with offset, length and hex on both sides.
When the sizes differ it falls back to a common prefix/suffix scan and reports
the approximate changed window. This is the first command of every differential
experiment.

## `wpj_wire.py` — the production wire reader

```bash
python3 tools/wpj_wire.py project.wpj            # record inventory
python3 tools/wpj_wire.py project.wpj 165,150    # protobuf tree of those types
python3 tools/wpj_wire.py                        # self-check
```

Varints, protobuf fields, the TLV container and a readable tree — one
implementation, shared by the codec, the B/C reader, the USB protocol and the
gobo palette. It replaces the former `tlv.py` and `dump.py`.

Every refusal is a `WireError` (a `ValueError`) naming what did not have the
shape it claimed: truncated varint, field number 0, a length past the end of
the buffer, a record overflowing its container. No assertion validates input
here — `python3 -O` erases those.

**The one duplication this repository keeps** is [`wpj_inspect.py`](#wpj_inspectpy--variant-bc-wire-walk):
a second, independent walk over the same bytes. An oracle that shares its code
with what it verifies only proves that code is consistent with itself.

## `gobo_library.py` — the controller's gobo icon library

Reads the flash image WTOOLS downloads with the firmware bundle, never the
controller. The 800-entry table maps a gobo id to a name and to a 24×24
RGB565+alpha icon; the id is what `145.f2` and the profile's `userNum` carry
(registry, GOBO-01).

```bash
python3 tools/gobo_library.py                       # self-check
python3 tools/gobo_library.py list                  # id → name, 800 lines
python3 tools/gobo_library.py palette project.wpj   # each group's pads, named
python3 tools/gobo_library.py sheet out.png         # contact sheet, id = row*20+col
```

No flash bundle on the machine → one line and exit 0. **Renders stay out of the
repository**: the icons are the manufacturer's artwork ([`../LEGAL.md`](../LEGAL.md)).

## `gobo_write.py` — replacing icons in a copy of the flash

The exact inverse of `gobo_library`'s decoder. An icon is a fixed 1728-byte
block and the table's pointers are absolute, so an edit is an in-place
overwrite: same length, same table, same pointers. The original image is never
touched — `patch` writes a new file and then checks the diff falls entirely
inside the windows it aimed at.

```bash
python3 tools/gobo_write.py                              # self-check
python3 tools/gobo_write.py patch out.bin 342=icon.png   # 24×24 PNG, RGB or RGBA
python3 tools/gobo_write.py patch out.bin 342='#ff00ff'  # a flat colour, no file
python3 tools/gobo_write.py patch out.bin 342=mask:big.png  # silhouette
```

Any **square** PNG larger than 24×24 is reduced by exact area averaging, so a
1024×1024 export patches directly. The `mask:` prefix reads luminance × alpha
as the icon's alpha channel and renders the shape in white — the inverse of a
"white motif on a black background" image, which is what an image generator
produces most reliably (see [`gobo-icons.md`](gobo-icons.md)).

Two refusals, both deliberate. Writing an icon whose pointer is shared is
blocked: in 2.0.18 `Open` (`0x1029417E`) serves 96 entries, and overwriting it
would repaint all of them. Writing over the source flash is blocked too.

An RGB PNG carries no alpha, so it lands fully opaque — the manufacturer's
icons are cut out, and exporting them without alpha flattens that away. Feed
RGBA when the shape matters.

`patch` also writes `SORTIE.json`, the manifest that ties the copy to the
installed bundle: source SHA-256 and size, result SHA-256 and size, bundle
version, patched ids, allowed byte windows, and the number of bytes that
actually differ. `gobo_run.py` verifies that chain before naming the upload.

Uploading the result is a separate, device-side act performed by WTOOLS; see
[`gobo-icons.md`](gobo-icons.md) §5 for the order of operations and the way
back.

## `gobo_run.py` — the gates between the gobo steps

The six steps of [`gobo-icons.md`](gobo-icons.md) each belong to a tool. What
belonged to nobody were the gates *between* them, and on real hardware a
skipped step is expensive. This one patches nothing, talks to no device and
writes no file: it reads a working directory and refuses to name the next step
while a gate is red.

```bash
python3 tools/gobo_run.py            # self-check
python3 tools/gobo_run.py ~/gobos    # the board, then the next command
```

```text
0 backup           OK   4 files, 4 matching SHA-256
1 silhouettes      OK   11 gobo*.png file(s)
2 patched flash    OK   2931442 bytes, 11 icon(s), chain verified
3 sheet            OK   rendered after the patched flash
```

A red gate says why on its own line, and the block below the board becomes the
command that clears it instead of the next step.

Four gates, each one a mistake already made or one step from being made: a
backup left **inside** the WTOOLS bundle folder (WTOOLS rewrites it on every
update) or whose SHA-256 no longer match the live bundle; no silhouettes; a
patched flash whose length moved, which would shift every absolute pointer; and
a proof sheet older than the patched flash — rendered from the sources, so
proving nothing about what will reach the device.

**Exit 2 means a red gate**, so an agent or a script stops where a human would.
The working directory must sit outside this repository: silhouettes, patched
flash and sheet are your fixture's data ([`../LEGAL.md`](../LEGAL.md)). Icon
`Open`, names over 19 bytes and a wheel carried by a second group stay refused
by the tools that own them — `gobo_write.py` and `wpj_show.py`.

## `wolfmix.py` / `wolfmix_experiment.py`

Device-side. Documented separately in [`device.md`](device.md).
