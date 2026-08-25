#!/usr/bin/env python3
"""ACC-05 : deux édits en place, un champ chacun.
- id 35 « Wipeout » (Chaser) : f5 [240,0] -> [3,0] (candidat : pads 1+2
  uniquement) ; renommé ACC05 Pads12.
- id 39 « Insane Colors » : vitesse 50 -> 200 ; renommé ACC05 Vite.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools'))
from wpjlib import Wpj
import wpj_codec as C

w = Wpj.load('corpus/projects/rig-a.wpj')
d = C.decode(165, w.get(165))
by_id = {p.get('id', 0): p for p in d['presets']}
p35, p39 = by_id[35], by_id[39]
assert p35['color_fx1'][0]['f5'] == {'hex': 'f00100'}
p35['color_fx1'][0]['f5'] = {'hex': '0300'}   # varints [3, 0] = pads 1+2
p35['nom'] = 'ACC05 Pads12'
assert p39['color_fx1'][0]['vitesse'] == 50
p39['color_fx1'][0]['vitesse'] = 200
p39['nom'] = 'ACC05 Vite'
w.replace(165, C.encode(165, d))
w.replace(101, C.encode(101, {'nom': 'WMX TEST ACC-05'}))
out = 'corpus/experiments/ACC-05/acc05.wpj'
if os.path.exists(out): os.remove(out)
w.save(out)
# relecture de contrôle
ps = C.decode(165, Wpj.load(out).get(165))['presets']
for p in ps:
    if p.get('id') in (35, 39):
        fx = p['color_fx1'][0]
        print(p['id'], repr(p['nom']), '| f5', fx.get('f5'), '| vitesse', fx.get('vitesse', '(abs)'))
