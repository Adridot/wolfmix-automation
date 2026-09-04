# Local version matrix — read 2026-08-27

| Component | Version | Source |
|---|---|---|
| WTOOLS | 2.0.2, build 248 — **beta** | the bundle's `sq.version`; installed over the stable on 2026-08-14 |
| Easy View 3 | 3.0.0 (`26.0819.661.293`) | `/Applications/Easy View/`, installed 2026-08-20 |
| Easy View 2 | 22.805.0.17 | `CFBundleVersion` alone (2024-01-11) |
| EasyViewConnect | no version declared | its `Info.plist` says nothing |
| macOS | 26.6.2 (25G83) | `sw_vers` |
| W1 Mk1 firmware | **2.0.19** since 2026-09-04 — 2.0.18 for every measurement before that date | `GET_SETTINGS` field 14, device connected; PATCH-02 is the first measurement on 2.0.19 |
| `wpj-toolkit` | commit `2bd0ee3` (2026-08-14) | external, not re-verified since |
| Cached W1 firmware bundle | 2.0.19, channel `debug`, built 2026-09-01 — and 2.0.18 beside it | `~/Library/Application Support/com.nicolaudiegroup.wtools/wm-fw-bundle-2.0.19/` — the image is encrypted; only `changelog.json` is readable (FW-01) |

The firmware is **read off the device**, not cited. **The trap**: field 13
(`firmwareVersion`, a float) reads 0.0 on this firmware — read field 14
(`firmwareVer`, a string).

2.0.2 is a **beta**, confirmed by the operator: the package declares no channel
(`sq.version` carries the version, and `channel` is the architecture), and it
replaced the stable install. The honest compatibility consequence: **everything
measured after 2026-08-14 was measured against a beta**, and is not promised on
the public 2.0.x. The ACC-series experiments predate it, under WTOOLS 1.6.3.

## Firmware cells — what «compatible» means here (README rule 5)

| Firmware | Measured | What held |
|---|---|---|
| 2.0.18 | every finding dated before 2026-09-04 | the whole ledger |
| 2.0.19 | 2026-09-04: PATCH-02, PATCH-03, FW-04 | a compiled patch opens and survives the device's save byte for byte; record-120 defaults at rest; the 25 Hz clock; the verified store; `GET_SETTINGS` and `GET_PROFILE` with no unknown field; `SET_MODE` read back. **Not** replayed: a preset recall, the panel's mode map, the gobo page — the one thing the vendor's changelog names |

## Local corpus — frozen copies, hashes in `corpus/SHA256SUMS`

Source: `~/Library/Application Support/WTOOLS/wlinkData/`. The originals are
never modified; the copies are read-only. Variant letters as in
[`../SPEC.md`](../SPEC.md) §1.

| File | Size | Origin date | Variant |
|---|---|---|---|
| `rig-C1.wpj` | 275 516 | 2025-06-19 | C — bare protobuf, field 1 = 6 |
| `rig-B1.wpj` | 276 923 | 2025-06-19 | B — SHA-1 + protobuf, field 1 = 7 |
| `rig-B2.wpj` | 276 750 | 2025-05-08 | B |
| `rig-B3.wpj` | 276 043 | 2025-05-08 | B |
| `rig-B4.wpj` | 282 886 | 2025-08-23 | B |
| `rig-B5.wpj` | 279 788 | 2025-08-23 | B |
| `rig-a.wpj` | 38 787 | 2025-09-20 | A — SHA-1 + TLV container type 100 |
| `rig-b.wpj` | 40 391 | 2025-09-20 | A |
| `rig-c` (base revision) | 43 329 | 2025-09-20 | A |
| `rig-c.wpj` | 39 737 | supplied by the operator 2026-08-25 — their main project | A |
| `rig-c-bug.wpj` | 44 729 | same, same UUID as the base revision; a recent **broken** revision (BUG-01) | A |
| `rig-B?.wm` | 550 310 | 2023-10-16 | ASCII-hex container, possibly encrypted |
| `rig-C1.wm` | 551 142 | 2023-10-16 | same |
| `wmx/wmBrands.wmx`, `wmProfiles.wmx`, `wmProjects.wmx`, `wmPersistent.wmx` | — | — | versioned ASCII-hex container, see below |

Note: files whose UUID begins with zeros carry identifiers **derived from the
device serial**, which is visible in clear in the header — hypothesis: dumps
synced from the W1 over WLINK. Neither the UUID nor the corresponding bytes are
reproduced here ([`../LEGAL.md`](../LEGAL.md)).

## The `.wmx` container — **[observed]**

Four dot-separated ASCII fields, the last three hex:

```
<version> . <32 hex = 16 bytes> . <ciphertext, hex> . <64 hex = 32 bytes>
```

| | |
|---|---|
| version | `001` (`wmProjects`), `002` (`wmPersistent`), `003` (`wmBrands`, `wmProfiles`) |
| field 2 | 16 bytes, different in every file — reads as an **IV** |
| payload | 3 664 / 2 560 / 6 816 / 132 096 bytes — **always a multiple of 16**, entropy 7.93–8.00 b/o |
| trailer | 32 bytes; not SHA-256 of the payload, the IV+payload, or the prefix, in any combination tried |

A 16-byte block size, a per-file IV and full entropy say **block cipher**, not
obfuscation — and AraCrypt with the published `DasCryptKey` leaves the entropy
untouched, so it is not the `.ssl2` cipher either. No key for this container is
public. Per [`../LEGAL.md`](../LEGAL.md) none is recovered from a vendor binary
here, so the payload stays undecoded; the container above is what its own bytes
show.

**The way round it is the device** — measured, 2026-08-31, W1 Mk1 fw 2.0.18.
`GET_PROFILE` (event 3) was already in the outgoing allowlist but had no
command. Prediction before the test: it takes the same UUID payload as
`GET_PROJECT` (0.6), replies with a different field layout (0.25), or refuses
because it wants an index (0.15). **The first held**, and the reply is plain
protobuf — the encrypted library on disk hides nothing the controller will not
hand over in the clear.

The layout is not repeated here: it is `PROFILE_FIELDS` and its three
sub-tables in [`../tools/wolfmix_protocol.py`](../tools/wolfmix_protocol.py),
which `decode_profile` reads and `wolfmix.py self-test` proves without a
device. A field the repository has observed but not attributed keeps its
neutral `fN` name there; a field number the decoder does not know lands in
`unknownFields`. `wolfmix.py profile UUID` prints the result.

Status: **device-confirmed** (PROFILE-01, PROFILE-02). The decode began as
`observed` — one profile family read three times — and was swept on 2026-09-01
across 221 profiles and 60 brands, 1 to 58 channels, 27 of them with two gobo
wheels: **no `unknownFields` anywhere**. Three sub-readings of the first pass
did not survive the sweep, and are corrected in the ledger rather than here:
the body's `f2` is not ×16, the body's `f5`/`f6` are not always zero, and the
mode table's `f3` is not always 1.
