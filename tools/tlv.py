#!/usr/bin/env python3
"""Extracteur TLV variante A + walker protobuf. Lecture seule."""
import sys, hashlib, json

def read_varint(buf, i):
    v = shift = 0
    while True:
        if i >= len(buf): raise ValueError("varint tronqué")
        b = buf[i]; i += 1
        v |= (b & 0x7F) << shift; shift += 7
        if not b & 0x80: return v, i
        if shift > 70: raise ValueError("varint")

def walk(buf, depth=0, max_depth=6):
    i, out = 0, []
    while i < len(buf):
        tag, i = read_varint(buf, i)
        f, wt = tag >> 3, tag & 7
        if f == 0: raise ValueError("f0")
        if wt == 0:
            v, i = read_varint(buf, i); out.append((f, "v", v))
        elif wt == 2:
            ln, i = read_varint(buf, i)
            if i + ln > len(buf): raise ValueError("len")
            chunk = buf[i:i+ln]; i += ln
            sub = None
            if depth < max_depth and ln:
                try: sub = walk(chunk, depth+1, max_depth)
                except ValueError: sub = None
            out.append((f, "len", chunk, sub))
        elif wt == 5:
            if i+4 > len(buf): raise ValueError("f32")
            out.append((f, "f32", buf[i:i+4])); i += 4
        elif wt == 1:
            if i+8 > len(buf): raise ValueError("f64")
            out.append((f, "f64", buf[i:i+8])); i += 8
        else: raise ValueError("wt")
    return out

def parse_tlv(data):
    """Retourne liste de (idx, type, abs_offset_payload, payload) des records enfants du root 100.

    Les refus sont des ValueError, jamais des assertions : `python3 -O` les
    ferait disparaître, et c'est une entrée externe qu'on valide ici.
    """
    if len(data) < 0x46:
        raise ValueError(f"fichier trop court : {len(data)} octets, 0x46 minimum")
    ln = int.from_bytes(data[0x40:0x44], "little")
    typ = int.from_bytes(data[0x44:0x46], "little")
    if typ != 100:
        raise ValueError(f"conteneur racine de type {typ}, 100 attendu")
    if 0x46 + ln > len(data):
        raise ValueError(f"racine de {ln} octets, {len(data) - 0x46} disponibles")
    body = data[0x46:0x46+ln]
    recs, i, idx = [], 0, 0
    while i < len(body):
        if i + 6 > len(body):
            raise ValueError(f"en-tête de record tronqué à {i}")
        rl = int.from_bytes(body[i:i+4], "little")
        rt = int.from_bytes(body[i+4:i+6], "little")
        if i + 6 + rl > len(body):
            raise ValueError(f"record de type {rt} tronqué à {i}")
        recs.append((idx, rt, 0x46 + i + 6, body[i+6:i+6+rl]))
        i += 6 + rl; idx += 1
    return recs

def load(path):
    data = open(path, "rb").read()
    if len(data) < 20 or data[:20] != hashlib.sha1(data[20:]).digest():
        raise ValueError(f"{path} : en-tête SHA-1 invalide")
    return data, parse_tlv(data)

def fmt_tree(fields, indent=0, maxlen=64):
    lines = []
    for e in fields:
        f, k = e[0], e[1]
        pad = "  " * indent
        if k == "v":
            lines.append(f"{pad}f{f}: {e[2]}")
        elif k in ("f32", "f64"):
            lines.append(f"{pad}f{f} {k}: {e[2].hex()}")
        else:
            chunk, sub = e[2], e[3]
            if sub is not None:
                lines.append(f"{pad}f{f} msg({len(chunk)}o):")
                lines.extend(fmt_tree(sub, indent+1, maxlen))
            else:
                try:
                    s = chunk.decode("utf-8")
                    if s.isprintable() and s:
                        lines.append(f"{pad}f{f} str: {s!r}"); continue
                except UnicodeDecodeError: pass
                h = chunk.hex()
                if len(h) > maxlen*2: h = h[:maxlen*2] + f"…(+{len(chunk)-maxlen}o)"
                lines.append(f"{pad}f{f} bytes({len(chunk)}o): {h}")
    return lines

if __name__ == "__main__":
    for p in sys.argv[1:]:
        data, recs = load(p)
        print(f"== {p} ({len(data)} o) uuid={data[20:36].hex()} b0x28={data[0x28]}")
        for idx, rt, off, pl in recs:
            h = hashlib.sha1(pl).hexdigest()[:8]
            print(f"  [{idx:2d}] type {rt:3d} len {len(pl):5d} @0x{off:05x} sha {h}")
