#!/usr/bin/env python3
"""ACC-06 : discriminer vitesse (f2 vs f9) et le 2e varint du masque pads.
- id 39 « Insane Colors » : f2 laissé à 50 (valeur donneur), f9 70 -> 25 ;
  nom ACC06 Lent. Attendu si f9 = vitesse : UI clock à 25 %.
- id 35 « Wipeout » : f5 [240,0] -> [0,1] ; nom ACC06 PadX. La case
  allumée dira si le bit0 du 2e varint = pad 9 (ligne 3 case 1) ou
  pad 13 (ligne 4 case 1) ou autre.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools'))
from wpjlib import Wpj
import wpj_codec as C

w = Wpj.load('corpus/projects/rig-a.wpj')
d = C.decode(165, w.get(165))
by_id = {p.get('id', 0): p for p in d['presets']}
fx39 = by_id[39]['color_fx1'][0]
assert fx39['vitesse'] == 50 and fx39['f9'] == 70
fx39['f9'] = 25
by_id[39]['nom'] = 'ACC06 Lent'
fx35 = by_id[35]['color_fx1'][0]
assert fx35['f5'] == {'hex': 'f00100'}
fx35['f5'] = {'hex': '0001'}   # varints [0, 1]
by_id[35]['nom'] = 'ACC06 PadX'
w.replace(165, C.encode(165, d))
w.replace(101, C.encode(101, {'nom': 'WMX TEST ACC-06'}))
out = 'corpus/experiments/ACC-06/acc06.wpj'
w.save(out)
ps = C.decode(165, Wpj.load(out).get(165))['presets']
for p in ps:
    if p.get('id') in (35, 39):
        fx = p['color_fx1'][0]
        print(p['id'], repr(p['nom']), '| f5', fx.get('f5'), '| vitesse', fx.get('vitesse'), '| f9', fx.get('f9'))
