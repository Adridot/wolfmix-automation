#!/usr/bin/env python3
"""The DMX output of a recalled position, computed from the project alone.

The model was measured channel by channel (registry, POS-01…07):

    pct_groupe(k) = (1 - FAN) + k * (2*FAN - 1) / (n - 1)   pan, k = rang
    pct_groupe    = TILT                                    tilt
    pct           = clamp(pct_groupe + offset, 0, 1)        offset = record 151
    borne16(f)    = f / 255 * 65535                         f = 106.f5 ou f6
    DMX16         = borne16(f5) + pct * (borne16(f6) - borne16(f5))

The self-check replays the four DMX captures of that session: 24 channels
predicted, the 12 tilt ones exactly. No capture is distributed — only the
measured values are frozen here, which makes the model checkable with no
hardware and breaks if anyone "simplifies" it.

Usage: python3 tools/wpj_position.py   (from the repository root)
"""
import sys

PLEINE_ECHELLE = 65535
DEMI_ECHELLE = 65536          # record 150 stores its fractions over 65536


def borne16(octet):
    """A travel limit (106.f5/f6), one byte, on the 16-bit scale."""
    return octet / 255 * PLEINE_ECHELLE


def etalement(fan, rang, effectif):
    """The pan fraction of rank k under FAN — the ramp from (1-FAN) to FAN."""
    if effectif < 2:
        return 0.5
    return (1 - fan) + rang * (2 * fan - 1) / (effectif - 1)


def dmx16(f5, f6, pct):
    """The 16-bit value emitted for a fraction, clamped by the travel limits."""
    pct = min(1.0, max(0.0, pct))
    bas, haut = borne16(f5), borne16(f6)
    return round(bas + pct * (haut - bas))


def canal(f5, f6, pct):
    """(high byte, low byte) of the 16-bit pair."""
    v = dmx16(f5, f6, pct)
    return v >> 8, v & 0xFF


def demo():
    # POS-01/02: Crowd then Ceiling on group A, six moving heads.
    # (f5 pan, f6 pan, f6 tilt) per head, in DMX address order.
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
    # POS-05/07: the detached head, signed offsets from record 151.
    signe = lambda v: (v - 32768) / 32767
    pan_off, tilt_off = signe(37027), signe(16383)      # +13 %, -50 %
    assert canal(133, 201, 0.5 + pan_off) == (176, 135), "detached pan"
    assert canal(0, 142, 1.0 + tilt_off)[0] == 71, "detached tilt"
    # POS-07: the offset is clamped, not wrapped — 70% + 91% gives the maximum.
    assert canal(0, 77, 45874 / DEMI_ECHELLE + signe(62585))[0] == 77, "clamp"
    assert dmx16(0, 77, 2.0) == round(borne16(77)) == 19789, "clamp 16 bits"
    assert rates == 1, f"pan: {rates} misses instead of the one known (Crowd, head 2)"
    print("self-check ok: 12/12 tilt, 11/12 pan, offsets and clamp",
          file=sys.stderr)


if __name__ == "__main__":
    demo()
