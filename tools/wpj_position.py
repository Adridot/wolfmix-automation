#!/usr/bin/env python3
"""Sortie DMX d'une position rappelée, calculée depuis le seul projet.

Le modèle a été mesuré canal par canal (registre, POS-01…07) :

    pct_groupe(k) = (1 - FAN) + k * (2*FAN - 1) / (n - 1)   pan, k = rang
    pct_groupe    = TILT                                    tilt
    pct           = clamp(pct_groupe + offset, 0, 1)        offset = record 151
    borne16(f)    = f / 255 * 65535                         f = 106.f5 ou f6
    DMX16         = borne16(f5) + pct * (borne16(f6) - borne16(f5))

Le self-check rejoue les quatre captures DMX de la session : 24 canaux
prédits, dont les 12 de tilt exacts. Aucune capture n'est distribuée — seules
les valeurs mesurées sont figées ici, ce qui rend le modèle vérifiable sans
matériel et casse si quelqu'un le « simplifie ».

Usage : python3 tools/wpj_position.py   (depuis la racine du dépôt)
"""
import sys

PLEINE_ECHELLE = 65535
DEMI_ECHELLE = 65536          # les fractions de 150 sont stockées sur 65536


def borne16(octet):
    """Une limite de débattement (106.f5/f6), octet, sur l'échelle 16 bits."""
    return octet / 255 * PLEINE_ECHELLE


def etalement(fan, rang, effectif):
    """Fraction de pan du rang k sous FAN, la rampe de (1-FAN) à FAN."""
    if effectif < 2:
        return 0.5
    return (1 - fan) + rang * (2 * fan - 1) / (effectif - 1)


def dmx16(f5, f6, pct):
    """Valeur 16 bits émise pour une fraction, bornée par le débattement."""
    pct = min(1.0, max(0.0, pct))
    bas, haut = borne16(f5), borne16(f6)
    return round(bas + pct * (haut - bas))


def canal(f5, f6, pct):
    """(octet de poids fort, octet de poids faible) du couple 16 bits."""
    v = dmx16(f5, f6, pct)
    return v >> 8, v & 0xFF


def demo():
    # POS-01/02 : Crowd puis Ceiling sur le groupe A, six lyres.
    # (f5 pan, f6 pan, f6 tilt) par lyre, dans l'ordre des adresses DMX.
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
                f"{nom} : tilt de la lyre {k} = {attendu}, mesuré {mes_tilt[k]}"
            if canal(p5, p6, etalement(fan, k, len(lyres)))[0] != mes_pan[k]:
                rates += 1
    # POS-05/07 : la lyre détachée, offsets signés du record 151.
    signe = lambda v: (v - 32768) / 32767
    pan_off, tilt_off = signe(37027), signe(16383)      # +13 %, -50 %
    assert canal(133, 201, 0.5 + pan_off) == (176, 135), "pan détaché"
    assert canal(0, 142, 1.0 + tilt_off)[0] == 71, "tilt détaché"
    # POS-07 : l'offset est borné, pas replié — 70 % + 91 % donne le maximum.
    assert canal(0, 77, 45874 / DEMI_ECHELLE + signe(62585))[0] == 77, "clamp"
    assert dmx16(0, 77, 2.0) == round(borne16(77)) == 19789, "clamp 16 bits"
    assert rates == 1, f"pan : {rates} écarts au lieu du seul connu (Crowd, lyre 2)"
    print("self-check ok : 12/12 tilt, 11/12 pan, offsets et clamp",
          file=sys.stderr)


if __name__ == "__main__":
    demo()
