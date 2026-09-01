#!/usr/bin/env python3
"""Repair the position layer of a project the COV-23/24 session damaged.

What is wrong, and it is three things in one record pair (COV-32, COV-37,
COV-48): record 150's group-A slots claim **six** slices of record 151, the
record holds **one**, and that one entry names a fixture of another group. The
panel shows no detached fixture at all, so the firmware is refusing the whole
table rather than surfacing what it can.

**The surviving entry is not salvageable, and the file says so itself.** It
names fixture 2, a `6x18W 6in1 RGBAW UV` whose ten channels carry no pan and no
tilt — it stores pan and tilt offsets for a fixture that cannot pan or tilt.
Repointing it at a group-A head would be inventing an intention nobody
recorded; the five entries the session dropped are gone and cannot be guessed.

So the repair is the one the device already believes: **no detached fixture.**
That is what the panel shows, so the file is made to agree with it rather than
the reverse. Record 151 goes to its empty form — the zero-length payload nine
corpus files already use — and record 150 stops claiming slices.

`120.f1` is fixed in the same pass, from 221 to the 215 entries the record
holds. It is a different defect (COV-32) on a record this touches nothing else
of; `occupation_120` ties `120.f4` to the entry *count*, not to `f1`, so the
correction cannot disturb it.

Usage:  build.py <damaged.wpj> <repaired.wpj>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "tools"))
import wpj_codec
import wpj_identities
import wpjlib


def reparer(w):
    """Every edit, on a loaded project. Returns what it changed, for the log."""
    journal = []

    d = wpj_codec.decode(151, w.get(151))
    if d.get("detached"):
        journal.append(f"151: {len(d['detached'])} entry/entries dropped")
    w.replace(151, b"")                       # the empty form, §8.1

    d = wpj_codec.decode(150, w.get(150, 0))
    for i, slot in enumerate(d["positions"]):
        if "entry_count_151" in slot or "offset_151" in slot:
            journal.append(f"150[A][{i + 1}]: slice "
                           f"{slot.get('offset_151', 0)}+"
                           f"{slot.get('entry_count_151', 0)} removed")
            slot.pop("entry_count_151", None)
            slot.pop("offset_151", None)
    w.replace(150, wpj_codec.encode(150, d), 0)

    d = wpj_codec.decode(120, w.get(120))
    reel = len(d["channels"])
    if d.get("entry_count") != reel:
        journal.append(f"120.f1: {d['entry_count']} -> {reel}")
        d["entry_count"] = reel
        w.replace(120, wpj_codec.encode(120, d))
    return journal


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    source, cible = argv
    w = wpjlib.Wpj.load(source)
    avant = wpj_identities.anomalies(source)
    for nom, message in avant:
        print(f"before   ANOMALY  {nom}: {message}", file=sys.stderr)
    for ligne in reparer(w):
        print(f"  fix    {ligne}", file=sys.stderr)
    w.save(cible)                             # mode "x": never overwrites

    echecs = wpj_identities.controler(cible)
    apres = wpj_identities.anomalies(cible)
    for nom, message in echecs:
        print(f"after    BROKEN   {nom}: {message}", file=sys.stderr)
    for nom, message in apres:
        print(f"after    ANOMALY  {nom}: {message}", file=sys.stderr)
    print(f"{cible}: {len(wpj_identities.IDENTITES) - len(echecs)}/"
          f"{len(wpj_identities.IDENTITES)} identities, {len(apres)} anomalies "
          f"(was {len(avant)})", file=sys.stderr)
    return 1 if echecs or apres else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
