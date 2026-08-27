# Tool reference

Every tool is a standalone `python3` script in `tools/`, standard library only.
Run them **from the repository root** — the self-checks resolve `corpus/`
relative to the working directory.

Three conventions hold everywhere:

- **Run with no arguments = self-check.** Each tool proves its own invariant and
  exits non-zero if it cannot. Six of them (`wpjlib`, `wpj_codec`, `wpj_api`,
  `wpj_identities`, `wpj_show`, `wpj_generate`) prove it over your corpus; the
  other three prove it against frozen inputs in their own source
  (`wpj_inspect`, `wpj_position`) or against the git index (`wpj_privacy`).
  `make check` runs nine of them;
  `wpj_diff.py` self-checks too but is not wired into it.
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

Naming: a field whose meaning is proven gets a semantic key (`nom`, `profil`,
`effet`, …); an unidentified field keeps a neutral `fN` key. An absent field is
absent from the dict — never a synthesised `0`.

Decoded today: 101, 102, 105, 115, 116, 120, 125, 135, 140, 145, 150, **151**,
160, 165.

Note on 105: the keys are `offset_106` and `nb_entrees_106`, not an address and a
channel count — see `SPEC.md` §7. The old names were a misreading.
Passthrough (round-tripped, undecoded): 106, 110, 111, 130, 155, 161 —
several of these have a documented structure in `SPEC.md` without a codec
schema yet.

The self-check reads only the corpus you supply. It does **not** scan your
WTOOLS installation; copy what you want tested into the corpus root instead.

## `wpj_identities.py` — structural identities

```bash
python3 tools/wpj_identities.py    # self-check, part of `make check`
```

Each identity is an arithmetic constraint between two records — true on every
file or false. A reading that breaks one is refuted without touching hardware,
which is the cheapest kind of proof available here.

Checked today — sixteen, plus two before/after pair checks (F30-04, FLASH-09):

| Identity | What it kills |
|---|---|
| `110[c].f2 == len(111 slice of c)` | reading `110.f2` as a feature enum |
| `[145 items].f2 == [111 gobo ranges].f4` | reading the gobo palette as stored content — it is derived from the patch |
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
| an engine active in `f16` implies its bit in `f4` | reading `f4` as a content mask |
| byte 50 is the schema version, and `165.f32`–`f35` arrive at 10 | treating the prefix as fully opaque |
| `110.f5` points at the channel's principal | guessing 16-bit byte order or adjacency |
| no preset name exceeds 19 UTF-8 bytes | a generator that writes a longer one and bricks the open |

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

Attributions still at `hypothesized` status (`sizePercent`, `fadePercent`,
`phasePercent`) *are* emitted, but always alongside an
`unconfirmed_field_attribution` issue in `validation.issues`. Treat them as
leads, not values.

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
donor's with the `modele` key — appending a well-formed `165.f5` entry with a
free, larger id is device-confirmed (PRESET-01/06/07), and `165.f1` is left
verbatim because it gates nothing.

Preset names are capped at **19 UTF-8 bytes** and the compiler now rejects a
longer one: past that the *whole project* refuses to open on the device
(PRESET-05), and the value reads back fine, so nothing downstream would catch
it.

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

One layer above `wpj_show.py`: it turns an **intention** — ambiances, energy,
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

## `tlv.py` / `dump.py` — analysis helpers

Standalone variant-A TLV extractor plus a protobuf tree walker, used for
exploration rather than production decoding.

```bash
python3 tools/dump.py project.wpj 165,150     # tree of every record of those types
```

`tlv.py` asserts the SHA-1 header on load and returns
`(data, [(index, type, absolute_offset, payload), …])`.

Neither has a self-check; they are exploration tools, and `wpjlib` is the
implementation that carries the guarantees.

## `wolfmix.py` / `wolfmix_experiment.py`

Device-side. Documented separately in [`device.md`](device.md).
