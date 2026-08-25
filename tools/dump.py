#!/usr/bin/env python3
"""Dump arbre protobuf d'un ou plusieurs records TLV par type."""
import sys
from tlv import load, walk, fmt_tree

path = sys.argv[1]
want = [int(x) for x in sys.argv[2].split(",")]
data, recs = load(path)
for idx, rt, off, pl in recs:
    if rt not in want: continue
    print(f"--- [{idx}] type {rt} len {len(pl)} @0x{off:05x}")
    try:
        tree = walk(pl)
        print("\n".join(fmt_tree(tree, 1)))
    except ValueError as e:
        print(f"  (pas protobuf: {e}) hex: {pl[:96].hex()}{'…' if len(pl)>96 else ''}")
