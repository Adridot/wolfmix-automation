#!/usr/bin/env python3
"""Renomme et réordonne la page gobos d'un projet — records 145 et 111.

Deux faits device-confirmed les portent (RENAME-01, SORT-01, 2026-08-30) :
le nom d'un pad est `145.f3`, écrit hors appareil et affiché tel quel ; et
l'ordre des pads est l'ordre du fil des plages roue (`f3 = 14`) du record
111 — le firmware accepte des plages non monotones, les bornes DMX voyagent
avec chaque plage, et les noms suivent leurs entrées.

  self-test                            invariants sur le corpus
  rename SRC DST id=Nom ...            écrit 145.f3 (≤ 19 octets UTF-8)
  order  SRC DST id,id,...             réordonne 111 et 145 en cohérence

`order` attend la liste complète des ids de la roue (la plage open sans id
reste en tête, hors palette). La permutation du 111 est une chirurgie à
l'octet : les sous-messages sont déplacés tels quels, rien d'autre ne bouge.
Les glyphes du 145 sont réassignés en séquence (`!`, `"`, …), comme sur les
fichiers écrits par l'appareil.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpj_codec
import wpjlib
from wpj_codec import _rvarint

WHEEL = 14          # 111.f3 : fonction « roue de gobos »
NAME_MAX = 19       # au-delà, un nom de preset brique l'ouverture (PRESET-05)


def wheel_slice(payload):
    """Le record 111 découpé : [(début, fin, id_gobo|None)] pour la tranche
    roue, contiguë, plage open (sans f4) en tête ; le reste est opaque."""
    spans, i = [], 0
    while i < len(payload):
        start = i
        tag, i = _rvarint(payload, i)
        if tag & 7 == 2:
            ln, i = _rvarint(payload, i)
            body, i = payload[i:i + ln], i + ln
            fields, j = {}, 0
            while j < len(body):
                t, j = _rvarint(body, j)
                if t & 7:
                    fields = None
                    break
                v, j = _rvarint(body, j)
                fields[t >> 3] = v
            gid = (fields.get(4) if fields and fields.get(3) == WHEEL
                   else None)
            in_wheel = fields is not None and fields.get(3) == WHEEL
        elif tag & 7 == 0:
            _, i = _rvarint(payload, i)
            in_wheel, gid = False, None
        else:
            raise ValueError(f"tag {tag:#x} inattendu dans le record 111")
        spans.append((start, i, in_wheel, gid))
    wheel = [k for k, s in enumerate(spans) if s[2]]
    if not wheel:
        return spans, []
    if wheel != list(range(wheel[0], wheel[0] + len(wheel))):
        raise ValueError("tranche roue non contiguë dans le record 111")
    return spans, wheel


def reorder_111(payload, order):
    spans, wheel = wheel_slice(payload)
    items = [spans[k] for k in wheel]
    ids = [s[3] for s in items if s[3] is not None]
    if sorted(ids) != sorted(order):
        return None                      # pas la roue demandée
    by_id = {s[3]: s for s in items if s[3] is not None}
    new = [s for s in items if s[3] is None] + [by_id[g] for g in order]
    out, k = bytearray(), 0
    for idx, span in enumerate(spans):
        s = new[k] if idx in wheel else span
        k += idx in wheel
        out += payload[s[0]:s[1]]
    assert len(out) == len(payload)
    return bytes(out)


def palette(payload):
    d = wpj_codec.decode(145, payload)
    if "raw" in d:
        raise ValueError("record 145 non décodé")
    return d


def reorder_145(payload, order):
    d = palette(payload)
    slots = d["gobos"]
    filled = [s for s in slots if "gobo_id" in s]
    if sorted(s["gobo_id"] for s in filled) != sorted(order):
        return None
    by_id = {s["gobo_id"]: s for s in filled}
    new = [by_id[g] for g in order]
    for k, s in enumerate(new):
        s["glyphe"] = chr(0x21 + k)
    d["gobos"] = new + slots[len(filled):]
    return wpj_codec.encode(145, d)


def rename_145(payload, names):
    d = palette(payload)
    hits = 0
    for slot in d["gobos"]:
        if slot.get("gobo_id") in names:
            slot["nom"] = names[slot["gobo_id"]]
            hits += 1
    return (wpj_codec.encode(145, d), hits) if hits else (None, 0)


def apply(src, dst, edit):
    """`edit(type, payload)` → payload neuf ou None ; refuse le vide."""
    w = wpjlib.Wpj.load(src)
    touched = []
    for occ, (typ, payload) in enumerate(w.records):
        if typ not in (111, 145):
            continue
        new = edit(typ, payload)
        if new is not None and new != payload:
            nth = sum(1 for t, _ in w.records[:occ] if t == typ)
            w.replace(typ, new, occurrence=nth)
            touched.append((occ, typ))
    if not touched:
        raise ValueError("aucun record ne correspond — mauvais ids ?")
    w.save(dst)
    return touched


def self_test():
    files = wpjlib.corpus_files()
    seen = 0
    for path in files:
        try:
            w = wpjlib.Wpj.load(path)
        except ValueError:
            continue                      # variante B/C, hors périmètre
        pals = [p for t, p in w.records if t == 145]
        r111 = [p for t, p in w.records if t == 111]
        for pal in pals:
            try:
                d = palette(pal)
            except ValueError:
                continue
            ids = [s["gobo_id"] for s in d["gobos"] if "gobo_id" in s]
            if not ids:
                continue
            seen += 1
            # permutation identité puis rotation + inverse : le 111 revient
            # à l'octet près — la chirurgie ne touche que l'ordre.
            rot = ids[1:] + ids[:1]
            for payload in r111:
                same = reorder_111(payload, ids)
                if same is None:
                    continue
                assert same == payload, f"{path} : l'identité a réécrit 111"
                once = reorder_111(payload, rot)
                back = reorder_111(once, ids)
                assert back == payload, f"{path} : rotation non inversible"
            # glyphes séquentiels (la forme que l'appareil écrit) : la
            # permutation identité du 145 est alors elle aussi un no-op.
            glyphs = [s.get("glyphe") for s in d["gobos"] if "gobo_id" in s]
            if glyphs == [chr(0x21 + k) for k in range(len(glyphs))]:
                assert reorder_145(pal, ids) == pal, path
    if not files:
        print("ignoré, aucun corpus")
        return
    print(f"ok — {seen} palettes gobo permutées et inversées à l'octet près")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "self-test"
    if cmd == "self-test":
        self_test()
        return 0
    if cmd not in ("rename", "order") or len(argv) < 5:
        print(__doc__, file=sys.stderr)
        return 2
    src, dst = argv[2], argv[3]
    try:
        if cmd == "rename":
            names = {}
            for spec in argv[4:]:
                key, sep, nom = spec.partition("=")
                if not sep or len(nom.encode()) > NAME_MAX or not nom:
                    raise ValueError(f"attendu id=Nom (1 à {NAME_MAX} octets "
                                     f"UTF-8), reçu « {spec} »")
                names[int(key)] = nom
            touched = apply(src, dst, lambda t, p:
                            rename_145(p, names)[0] if t == 145 else None)
        else:
            order = [int(x) for x in argv[4].split(",")]
            touched = apply(src, dst, lambda t, p:
                            reorder_111(p, order) if t == 111
                            else reorder_145(p, order))
    except (ValueError, FileExistsError) as err:
        print(f"refus : {err}", file=sys.stderr)
        return 1
    what = ", ".join(f"{t}[{i}]" for i, t in touched)
    print(f"{dst} — records modifiés : {what}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
