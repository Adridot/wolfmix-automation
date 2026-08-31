# Legal position

What this repository contains, what it deliberately does not, and why.

This project is independent black-box research on a file format its
manufacturer does not publish, carried out on hardware and files we own. It is
not affiliated with, endorsed by, or sponsored by Wolfmix or Nicolaudie.
Wolfmix, Wolfmix W1, WTOOLS, WLINK and Nicolaudie are trademarks of their
respective owners.

## Nothing from the manufacturer is distributed here

This is the rule the repository is built around, and it is enforced by
`.gitignore`, not by good intentions.

**No project files.** Not one `.wpj`, `.wm` or `.wmx` file ships with this
repository. That is not squeamishness: a real project file is a bundle of
material we have no right to redistribute.

| What a `.wpj` carries | Whose it is |
|---|---|
| Factory preset, effect, macro and palette names — ~70 strings, byte-identical across unrelated rigs | the manufacturer's authored content |
| Fixture profile data — profile names, channel layouts, capability ranges, gobo image ids | the profile's manufacturer, redistributed through the vendor's library |
| The patch, addresses, group and position names | the operator, and often their client or venue |
| A device-derived UUID and header bytes | the operator's hardware |

`wmProfiles.wmx` and `wmBrands.wmx` are worse: they are the vendor's **entire
fixture-profile library**, not a project that happens to embed a few entries.

**No firmware, no vendor binaries, no extracted resources.** No firmware image,
no part of one, no dump of any vendor application, no icon or font extracted
from a device or an installer.

**No vendor documents.** The manufacturer's reference manual is used as a
source and cited by URL and SHA-256 in [`research/vendor.md`](research/vendor.md).
The PDF itself is git-ignored. Quotations elsewhere are short, factual and
attributed, with thread ids for forum statements.

**No hosted-service oracle.** No project file is ever uploaded to a third-party
inspection API. See [`PROVENANCE.md`](PROVENANCE.md) for why that rule is also
what keeps the evidence chain intact.

## What you have to obtain yourself

The tools read and write Wolfmix project files; they do not invent one. To run
the self-checks over real data, or to compile a show, you need a donor project
of your own.

> [!CAUTION]
> Nothing of the sort is distributed here. This step is yours to run, and
> what it leaves on your disk stays on your disk.

You already have everything you need if you own a W1: the projects in your own
WTOOLS installation, or a project downloaded from your own controller with
`tools/wolfmix.py`. Both are described in [`docs/corpus.md`](docs/corpus.md).
Point the tools at that directory and nothing leaves your machine.

The same applies to the manufacturer's manual, to WTOOLS itself, and to
fixture profiles: get them from the manufacturer, on your own machine, under
whatever terms the manufacturer sets.

What you produce from them stays yours too: gobo photographs, the silhouettes
generated from them and any patched `wolfmixFlash.bin` are your fixture's data
and the manufacturer's icon work — they are never committed here, and
`tools/gobo_run.py` refuses a working directory inside this tree.

## Interoperability, and what we did not do

The format was mapped by reading files we own, by changing one parameter at a
time in the vendor's own editor and comparing the result, and by watching what
our own controller does over its USB link and on its DMX output. Nothing
published here reproduces vendor source code, and no decompiler output is
quoted: what this repository states about the editor comes from running it —
its strings, its preferences, its observable behaviour — and every claim is
backed by a measurement on our own device.

### Resource flash, and why it is not firmware

`wolfmixFlash.bin` is the interface's graphics: the icons the screen draws. A
resource-flash operation is not an executable-firmware update, and the two are
kept apart on purpose:

- reading the installed image, extracting icons locally, patching a **copy**,
  verifying the patch and previewing it are supported here;
- the copy is uploaded by WTOOLS, by the operator, with a verified backup of
  the original taken first — this repository never writes it;
- **executable firmware updates stay out of scope**, in every direction;
- no vendor image, extracted resource or patched copy is ever distributed, and
  `.gitignore` plus `tools/wpj_privacy.py` refuse them.

Revealing the editor's own `Upload Flash` control by setting a documented
application preference is use of software we hold a licence for, on our own
machine, to interoperate with our own device.

Where the work touches vendor software, it stays on the interface: the
`WM_MODE_*` names in [`PROVENANCE.md`](PROVENANCE.md) are
constant names read out of strings in software installed on our own machine,
and every **numeric value** in that map was measured on our own device rather
than taken from a binary. Names and numbers of an interface are facts about how
to interoperate with it, and that is the only use made of them here.

Two things are deliberately absent, and if you are looking for them this is the
answer:

- **No circumvention of any protection measure.** The `.wm`/`.wmx` sidecars are
  observed to be high-entropy and are recorded as opaque. We do not attempt to
  decrypt them, and no key, key-recovery routine or decryptor for any vendor
  format or link is published here.
- **No licence, activation or entitlement work.** Universe count, WLINK and
  3D Link are paid, per-controller entitlements. The research notes that they
  exist and that they are bound to the device and the vendor account; nothing
  here touches, emulates or bypasses them.

## Hardware safety

No firmware operation is implemented. The device client's outgoing event list
is an explicit allowlist in the source, and anything outside it is refused
before a byte reaches the port. The experiment runner writes only project UUIDs
derived from its own experiment label, verifies each upload by reading it back,
and restores the previous state on failure. See [`docs/device.md`](docs/device.md).

## Your files, your risk

The tools never overwrite: every write opens a new path and fails if it exists.
That is a design stance, not a warranty. The software is provided under the
[MIT licence](LICENSE), without warranty of any kind. Keep backups.

If you believe something in this repository infringes your rights, open an
issue and it will be removed while the question is settled.
