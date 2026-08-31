# Local version matrix — read 2026-08-27

| Component | Version | Source |
|---|---|---|
| WTOOLS | 2.0.2, build 248 — **beta** | the bundle's `sq.version`; installed over the stable on 2026-08-14 |
| Easy View 3 | 3.0.0 (`26.0819.661.293`) | `/Applications/Easy View/`, installed 2026-08-20 |
| Easy View 2 | 22.805.0.17 | `CFBundleVersion` alone (2024-01-11) |
| EasyViewConnect | no version declared | its `Info.plist` says nothing |
| macOS | 26.6.2 (25G83) | `sw_vers` |
| W1 Mk1 firmware | 2.0.18 | `GET_SETTINGS` field 14, device connected |
| `wpj-toolkit` | commit `2bd0ee3` (2026-08-14) | external, not re-verified since |
| Cached W1 firmware bundle | 2.0.18, channel `debug`, `fwDate` 2026-07-07 | `~/Library/Application Support/com.nicolaudiegroup.wtools/wm-fw-bundle-2.0.18/` — the image is encrypted; only `changelog.json` is readable (FW-01) |

The firmware is **read off the device**, not cited. **The trap**: field 13
(`firmwareVersion`, a float) reads 0.0 on this firmware — read field 14
(`firmwareVer`, a string).

2.0.2 is a **beta**, confirmed by the operator: the package declares no channel
(`sq.version` carries the version, and `channel` is the architecture), and it
replaced the stable install. The honest compatibility consequence: **everything
measured after 2026-08-14 was measured against a beta**, and is not promised on
the public 2.0.x. The ACC-series experiments predate it, under WTOOLS 1.6.3.

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
| `wmx/wmBrands.wmx`, `wmProfiles.wmx`, `wmProjects.wmx`, `wmPersistent.wmx` | — | — | versioned ASCII-hex container (001–003), high-entropy payload |

Note: files whose UUID begins with zeros carry identifiers **derived from the
device serial**, which is visible in clear in the header — hypothesis: dumps
synced from the W1 over WLINK. Neither the UUID nor the corresponding bytes are
reproduced here ([`../LEGAL.md`](../LEGAL.md)).
