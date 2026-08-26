# Tool reference

Every tool is a standalone `python3` script in `tools/`, standard library only.
Run them **from the repository root** — the self-checks resolve `corpus/`
relative to the working directory.

Three conventions hold everywhere:

- **Run with no arguments = self-check.** Each tool proves its own invariant
  over your corpus and exits non-zero if it cannot. `make check` runs the six
  that matter.
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
bytes 20–0x46 (the opaque prefix plus the root header) verbatim.

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
in the corpus (25 on the development machine).

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

Naming: a field whose meaning is proven gets a semantic key (`nom`, `adresse`,
`effet`, …); an unidentified field keeps a neutral `fN` key. An absent field is
absent from the dict — never a synthesised `0`.

Decoded today: 101, 102, 105, 115, 116, 120, 125, 135, 140, 145, 150, 160, 165.
Passthrough (round-tripped, undecoded): 106, 110, 111, 130, 151, 155, 161 —
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

Checked today:

| Identity | What it kills |
|---|---|
| `110[c].f2 == len(111 slice of c)` | reading `110.f2` as a feature enum |
| `[145 items].f2 == [111 ranges with f3 == 14].f4` | reading the gobo palette as stored content — it is derived from the patch |

Add one whenever a new reading implies a count, an offset or a derivation.

## `wpj_inspect.py` — variant B/C wire walk

```bash
python3 tools/wpj_inspect.py file.wpj [--depth N] > tree.json
```

Walks the raw protobuf wire format and emits field numbers, wire types and
values. No invented semantics: names are numbers, unknown bytes come out as
hex, and a length-delimited chunk is emitted as sub-message *and* text *and*
hex when all three parse — candidates, not a choice.

Exit **2** with a message on stderr if the input is not protobuf. Small `.wpj`
files (device dumps) do not parse, and the tool says so instead of guessing.

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

Applies a JSON edit spec to a donor project. Nothing is synthesised: a preset,
position or palette entry being edited must already exist in the donor;
everything else is preserved byte for byte by `wpjlib`.

After writing, it reloads its own output (revalidating the SHA-1), re-decodes
every edited record, checks each requested value reads back, and confirms that
**no record outside the edit set changed**. If any check fails the output file
is deleted. Exit 1 on error, 2 on bad usage.

Key reference: [`show-format.md`](show-format.md).

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
