# Raw captures

Instrument output, kept as it came off the tool. Nothing here is edited, and
nothing here is a conclusion — a reading of one of these files is a line in
[`../evidence.md`](../evidence.md), and this directory is what that line was
read from.

| File | What it is |
|---|---|
| `mode-01-session.jsonl` | `wolfmix.py watch-mode` polling `GET_SETTINGS` at 0.15 s while the operator walked the front panel, 2026-08-25. The measurement behind the mode map in [`../../SPEC.md`](../../SPEC.md) §10.2. Zero writes: the session only reads settings. |

DMX captures are **not** here and never will be — they carry the operator's own
show ([`../../LEGAL.md`](../../LEGAL.md)), and `.gitignore` refuses them.
