#!/usr/bin/env python3
"""A minimal binary diff, for single-variable experiments.

Module group: Format. Reference: SPEC.md.

Usage: wpj_diff.py avant.wpj apres.wpj
Emits the byte ranges that differ (offset, length, hex before/after). When the
sizes differ, it attempts a naive realignment on the common suffix.
"""

from __future__ import annotations
from os import PathLike
import sys


def ranges(a: bytes | bytearray, b: bytes | bytearray) -> list[tuple[int, int]]:
    """The differing ranges between two buffers of the same size."""
    out, start = [], None
    for i in range(len(a)):
        if a[i] != b[i]:
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(a)))
    return out


def main(pa: str | PathLike[str], pb: str | PathLike[str]) -> None:
    a, b = open(pa, "rb").read(), open(pb, "rb").read()
    print(f"{pa}: {len(a)} bytes / {pb}: {len(b)} bytes")
    if len(a) != len(b):
        # common suffix, to estimate the inserted/deleted region
        n = 0
        while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
            n += 1
        p = 0
        while p < min(len(a), len(b)) and a[p] == b[p]:
            p += 1
        print(f"sizes differ (Δ={len(b)-len(a):+}); common prefix {p} B, "
              f"common suffix {n} B → changed region ≈ [{p}, {len(a)-n})")
        print(f"avant [{p}:{min(len(a)-n, p+64)}]: {a[p:min(len(a)-n, p+64)].hex(' ')}")
        print(f"after  [{p}:{min(len(b)-n, p+64)}]: {b[p:min(len(b)-n, p+64)].hex(' ')}")
        return
    diffs = ranges(a, b)
    print(f"{len(diffs)} differing range(s)")
    for s, e in diffs:
        print(f"  0x{s:06x}+{e-s}: {a[s:e][:32].hex(' ')}  ->  {b[s:e][:32].hex(' ')}")


def demo() -> None:
    assert ranges(b"abcdef", b"abXdeY") == [(2, 3), (5, 6)]
    assert ranges(b"same", b"same") == []
    print("self-check ok", file=sys.stderr)


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("avant", nargs="?", help="the reference project")
    parseur.add_argument("apres", nargs="?", help="the project to compare")
    args = parseur.parse_args(argv)
    if args.avant is None or args.apres is None:
        if args.avant or args.apres:
            parseur.error("give both files, or neither (self-check)")
        demo()
        return 0
    main(args.avant, args.apres)
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
