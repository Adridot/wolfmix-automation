#!/usr/bin/env python3
"""Inspecteur .wpj lecture seule.

Parcourt le wire format protobuf d'un .wpj « format WTOOLS » et émet un arbre
JSON (champs, types wire, valeurs). Aucune sémantique inventée : les noms de
champs sont des numéros, les octets inconnus sont émis en hex.

Usage: wpj_inspect.py fichier.wpj [--depth N] > out.json
Statut format : wire format validé sur 6/6 gros .wpj locaux (2026-08-25).
Les petits .wpj (dumps device ?) ne parsent PAS — l'outil le signale et sort
en erreur plutôt que de deviner.
"""
import json
import sys
import hashlib

MAX_DEPTH_DEFAULT = 6


def read_varint(buf, i):
    v = shift = 0
    while True:
        b = buf[i]
        i += 1
        v |= (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            return v, i
        if shift > 70:
            raise ValueError(f"varint trop long à {i}")


def walk(buf, depth, max_depth):
    """Retourne une liste de champs, ou lève ValueError si pas du protobuf."""
    i, out = 0, []
    while i < len(buf):
        tag, i = read_varint(buf, i)
        field, wt = tag >> 3, tag & 7
        if field == 0:
            raise ValueError(f"champ 0 à {i}")
        if wt == 0:
            v, i = read_varint(buf, i)
            out.append({"f": field, "wt": "varint", "v": v})
        elif wt == 2:
            ln, i = read_varint(buf, i)
            if i + ln > len(buf):
                raise ValueError(f"longueur {ln} dépasse le buffer à {i}")
            chunk = buf[i : i + ln]
            i += ln
            entry = {"f": field, "wt": "len", "n": ln}
            # candidats, pas un choix : on émet sous-message ET/OU texte ET hex
            if depth < max_depth and ln:
                try:
                    entry["msg"] = walk(chunk, depth + 1, max_depth)
                except ValueError:
                    pass
            if "msg" not in entry:
                try:
                    s = chunk.decode("utf-8")
                    if s.isprintable() or s == "":
                        entry["text"] = s
                except UnicodeDecodeError:
                    pass
            if "msg" not in entry and "text" not in entry:
                entry["hex"] = chunk.hex() if ln <= 512 else chunk[:512].hex() + "…"
        elif wt == 5:
            if i + 4 > len(buf):
                raise ValueError(f"f32 tronqué à {i}")
            out.append({"f": field, "wt": "f32", "hex": buf[i : i + 4].hex()})
            i += 4
            continue
        elif wt == 1:
            if i + 8 > len(buf):
                raise ValueError(f"f64 tronqué à {i}")
            out.append({"f": field, "wt": "f64", "hex": buf[i : i + 8].hex()})
            i += 8
            continue
        else:
            raise ValueError(f"wire type {wt} inconnu à {i}")
        if wt == 2:
            out.append(entry)
    return out


def inspect(path, max_depth=MAX_DEPTH_DEFAULT):
    data = open(path, "rb").read()
    # variante C : protobuf dès 0 ; variante B : SHA-1 (20 o) puis protobuf
    for off in (0, 20):
        try:
            tree = walk(data[off:], 0, max_depth)
            break
        except ValueError as e:
            err = e
    else:
        raise err
    sha1_ok = off == 20 and data[:20] == hashlib.sha1(data[20:]).digest()
    return {
        "file": path,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "format": "protobuf-wire (structure observée, sémantique non validée)",
        "bodyOffset": off,
        "sha1HeaderOk": sha1_ok if off == 20 else None,
        "fields": tree,
    }


def demo():
    """Self-check sur un message protobuf construit à la main."""
    msg = bytes([0x08, 0x06, 0x12, 0x03]) + b"abc" + bytes([0x1A, 0x02, 0x08, 0x01])
    out = walk(msg, 0, 3)
    assert out[0] == {"f": 1, "wt": "varint", "v": 6}
    assert out[1]["text"] == "abc"
    assert out[2]["msg"] == [{"f": 1, "wt": "varint", "v": 1}]
    try:
        walk(b"\x07\xff\xff", 0, 3)
        raise AssertionError("aurait dû rejeter")
    except ValueError:
        pass
    print("self-check ok", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        demo()
        sys.exit(0)
    depth = MAX_DEPTH_DEFAULT
    if "--depth" in sys.argv:
        depth = int(sys.argv[sys.argv.index("--depth") + 1])
    try:
        json.dump(inspect(sys.argv[1], depth), sys.stdout, ensure_ascii=False)
        print()
    except ValueError as e:
        print(f"PAS du wire format protobuf : {e}", file=sys.stderr)
        sys.exit(2)
