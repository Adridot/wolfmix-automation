#!/usr/bin/env python3
"""The DMX output of a recalled position, computed from the project alone.

Module group: Format. Reference: SPEC.md.

The model was measured channel by channel (registry, POS-01…07):

    pct_groupe(k) = PAN + etalement(FAN, k, n) - 0.5        pan, k = rang
    etalement     = (1 - FAN) + k * (2*FAN - 1) / (n - 1)   the FAN ramp
    pct_groupe    = TILT                                    tilt
    pct           = clamp(pct_groupe + offset, 0, 1)        offset = record 151
    borne16(f)    = f / 255 * 65535                         f = 106.f5 or f6
    DMX16         = borne16(f5) + pct * (borne16(f6) - borne16(f5))

The self-check replays the four DMX captures of that session: 24 channels
predicted, the 12 tilt ones exactly. No capture is distributed — only the
measured values are frozen here, which makes the model checkable with no
hardware and breaks if anyone "simplifies" it.

Usage: python3 tools/wpj_position.py   (from the repository root)
"""

from __future__ import annotations
import sys

PLEINE_ECHELLE = 65535
DEMI_ECHELLE = 65536          # record 150 stores its fractions over 65536


def borne16(octet: int) -> float:
    """A travel limit (106.f5/f6), one byte, on the 16-bit scale."""
    return octet / 255 * PLEINE_ECHELLE


def etalement(fan: float, rang: int, effectif: int) -> float:
    """The FAN ramp of rank k — from (1-FAN) to FAN, centred on 0.5."""
    if effectif < 2:
        return 0.5
    return (1 - fan) + rang * (2 * fan - 1) / (effectif - 1)


def fraction_pan(pan: float, fan: float, rang: int, effectif: int) -> float:
    """The pan fraction of rank k: the FAN ramp **offset by the slot's PAN**.

    The ramp is centred on 0.5, so the slot's own PAN shifts it: a group at
    PAN 52 % with FAN 60 % puts its second head at 0.52 + 0.44 - 0.5 = 0.45999,
    and the wire reads 0.45995 — under half a DMX unit at 16 bits (COV-36).

    **The PAN term was missing until 2026-09-01** and nothing had caught it:
    both frozen captures below sit at PAN 50 %, where this reduces to
    `etalement` exactly. That is the corpus-uniformity trap in its usual dress
    — a formula that held because nothing had exercised the other case.

    `effectif` is the group's fixture count: at n = 5 instead of 6 the same
    reading lands on 0.46999, a full point and some 136 DMX units away from
    what was measured. (An earlier note here said "the unpatched ones
    included". There was no unpatched fixture — an absent `115.f2` is **address
    0**, COV-41, and that fixture is on channels 0-3 like any other.)

    Two exact points, on two ranks and two kinds of travel limit.
    """
    return pan + etalement(fan, rang, effectif) - 0.5


def dmx16(f5: int, f6: int, pct: float) -> int:
    """The 16-bit value emitted for a fraction, clamped by the travel limits."""
    pct = min(1.0, max(0.0, pct))
    bas, haut = borne16(f5), borne16(f6)
    return round(bas + pct * (haut - bas))


def canal(f5: int, f6: int, pct: float) -> tuple[int, int]:
    """(high byte, low byte) of the 16-bit pair."""
    v = dmx16(f5, f6, pct)
    return v >> 8, v & 0xFF


def demo() -> None:
    lyres = [(133, 201, 142), (133, 190, 142), (151, 204, 77),
             (151, 204, 77), (128, 202, 127), (128, 202, 127)]
    captures = [
        # nom, FAN, TILT, pan mesures, tilt mesures
        ("Crowd", 45874 / DEMI_ECHELLE, 45874 / DEMI_ECHELLE,
         [153, 155, 176, 180, 174, 180], [99, 99, 54, 54, 89, 89]),
        ("Ceiling", 32768 / DEMI_ECHELLE, 65535 / DEMI_ECHELLE,
         [167, 162, 178, 178, 165, 165], [142, 142, 77, 77, 127, 127]),
    ]
    rates = 0
    for nom, fan, tilt, mes_pan, mes_tilt in captures:
        for k, (p5, p6, t6) in enumerate(lyres):
            attendu = canal(0, t6, tilt)[0]
            assert attendu == mes_tilt[k], \
                f"{nom}: tilt of head {k} = {attendu}, measured {mes_tilt[k]}"
            if canal(p5, p6, etalement(fan, k, len(lyres)))[0] != mes_pan[k]:
                rates += 1
    # COV-36: the PAN term, on a 16-bit pan read off the wire. Group A of the
    # experiment rig, pad `Center`: PAN 52 %, FAN 60 %, six fixtures of which
    # the first is unpatched, and the head of rank 1 sits at limits 151/204.
    mesure = 45072                                    # coarse 176, fine 16
    attendu = dmx16(151, 204, fraction_pan(34078 / DEMI_ECHELLE,
                                           39321 / DEMI_ECHELLE, 1, 6))
    assert abs(attendu - mesure) <= 1, f"pan with PAN: {attendu} vs {mesure}"
    # and the rival that the same reading kills: the ramp over the *patched*
    # fixtures only, which misses by more than a hundred DMX units.
    rival = dmx16(151, 204, fraction_pan(34078 / DEMI_ECHELLE,
                                         39321 / DEMI_ECHELLE, 1, 5))
    assert abs(rival - mesure) > 100, "n = 5 should not fit"
    # The tilt of the same frame, to the unit, on the same head.
    assert dmx16(0, 77, 21626 / DEMI_ECHELLE) == 6530, "tilt 16-bit"
    # COV-41: the second point, same frame, rank 0 of the same group — a
    # different term of the ramp and **inverted** pan limits, 201 down to 133.
    assert dmx16(201, 133, fraction_pan(34078 / DEMI_ECHELLE,
                                        39321 / DEMI_ECHELLE, 0, 6)) == 44317, \
        "pan with PAN, inverted limits"
    assert abs(dmx16(0, 142, 21626 / DEMI_ECHELLE) - 12042) <= 1, "tilt rank 0"
    # COV-35: a fixture whose four travel limits are absent is pinned at 0.
    assert dmx16(0, 0, 0.42) == 0 and dmx16(0, 0, 1.0) == 0, "pinned head"
    # POS-05/07: the detached head, signed offsets from record 151.
    signe = lambda v: (v - 32768) / 32767
    pan_off, tilt_off = signe(37027), signe(16383)      # +13 %, -50 %
    assert canal(133, 201, 0.5 + pan_off) == (176, 135), "detached pan"
    assert canal(0, 142, 1.0 + tilt_off)[0] == 71, "detached tilt"
    # POS-07: the offset is clamped, not wrapped — 70% + 91% gives the maximum.
    assert canal(0, 77, 45874 / DEMI_ECHELLE + signe(62585))[0] == 77, "clamp"
    assert dmx16(0, 77, 2.0) == round(borne16(77)) == 19789, "clamp 16 bits"
    assert rates == 1, f"pan: {rates} misses instead of the one known (Crowd, head 2)"
    print("self-check ok: 12/12 tilt, 11/12 pan, the PAN term, a pinned head, "
          "offsets and clamp",
          file=sys.stderr)


if __name__ == "__main__":
    demo()
