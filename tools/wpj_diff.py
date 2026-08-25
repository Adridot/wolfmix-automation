#!/usr/bin/env python3
"""Diff binaire minimal pour expériences différentielles.

Usage: wpj_diff.py avant.wpj apres.wpj
Émet les plages d'octets différentes (offset, longueur, hex avant/après).
Si les tailles diffèrent, tente un réalignement naïf par suffixe commun.
"""
import sys


def ranges(a, b):
    """Plages différentes entre deux buffers de même taille."""
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


def main(pa, pb):
    a, b = open(pa, "rb").read(), open(pb, "rb").read()
    print(f"{pa}: {len(a)} octets / {pb}: {len(b)} octets")
    if len(a) != len(b):
        # suffixe commun pour estimer la zone insérée/supprimée
        n = 0
        while n < min(len(a), len(b)) and a[-1 - n] == b[-1 - n]:
            n += 1
        p = 0
        while p < min(len(a), len(b)) and a[p] == b[p]:
            p += 1
        print(f"tailles différentes (Δ={len(b)-len(a):+}) ; préfixe commun "
              f"{p} o, suffixe commun {n} o → zone changée ≈ [{p}, {len(a)-n})")
        print(f"avant [{p}:{min(len(a)-n, p+64)}]: {a[p:min(len(a)-n, p+64)].hex(' ')}")
        print(f"après [{p}:{min(len(b)-n, p+64)}]: {b[p:min(len(b)-n, p+64)].hex(' ')}")
        return
    diffs = ranges(a, b)
    print(f"{len(diffs)} plage(s) différente(s)")
    for s, e in diffs:
        print(f"  0x{s:06x}+{e-s}: {a[s:e][:32].hex(' ')}  ->  {b[s:e][:32].hex(' ')}")


def demo():
    assert ranges(b"abcdef", b"abXdeY") == [(2, 3), (5, 6)]
    assert ranges(b"same", b"same") == []
    print("self-check ok", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        demo()
        sys.exit(0)
    main(sys.argv[1], sys.argv[2])
