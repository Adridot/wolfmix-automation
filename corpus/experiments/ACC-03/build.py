#!/usr/bin/env python3
"""ACC-03 : deux candidats pour activer le Color FX du preset 78.
a) f4 17->25 (ajoute le bit couleur b3=8 au masque beam 17)
b) f4 17->255 + f8=[255] (mimique d'un preset « full »)
Base : acc02-show.wpj (édits FX/dimmers déjà en place)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools'))
from wpjlib import Wpj
import wpj_codec as C

def variant(out, mutate):
    w = Wpj.load('corpus/experiments/ACC-02/acc02-show.wpj')
    d = C.decode(165, w.get(165))
    ps = d.get('presets') or d.get('f5')
    p = next(p for p in ps if p.get('id') == 78)
    mutate(p)
    w.replace(165, C.encode(165, d))
    w.replace(101, C.encode(101, {'nom': f'WMX TEST {os.path.basename(out)[:7].upper()}'}))
    w.save(out)
    # contrôle : relecture
    p2 = next(q for q in (C.decode(165, Wpj.load(out).get(165)).get('presets') or []) if q.get('id') == 78)
    print(out, '| f4 =', p2.get('f4'), '| actif =', p2.get('color_fx_actif'))

variant('corpus/experiments/ACC-03/acc03a.wpj', lambda p: p.__setitem__('f4', 25))
def full(p):
    p['f4'] = 255
    p['color_fx_actif'] = [255]
variant('corpus/experiments/ACC-03/acc03b.wpj', full)
