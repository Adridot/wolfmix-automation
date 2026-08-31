#!/usr/bin/env python3
"""Lecteur wire de production : varints, champs protobuf, conteneur TLV.

Deux implémentations du wire coexistent **volontairement** dans ce dépôt
(AGENTS.md, « une exception documentée à la non-répétition ») :

  wpj_wire.py     celle-ci, partagée par le codec, le lecteur B/C, le
                  protocole USB et la palette gobo ;
  wpj_inspect.py  une seconde, indépendante, qui sert d'oracle.

Un oracle qui partage son code avec ce qu'il vérifie ne vérifie que la
cohérence de ce code avec lui-même. Les autres duplications, elles, ont été
supprimées : ce fichier remplace `tlv.py` et `dump.py`.

Tout refus est une `WireError` (une `ValueError`) : jamais une assertion — elles
disparaissent sous `python3 -O` — et jamais une exception de la bibliothèque
standard remontée telle quelle.

Usage :
  wpj_wire.py fichier.wpj            l'inventaire des records du conteneur
  wpj_wire.py fichier.wpj 165,150    l'arbre protobuf de ces types
  wpj_wire.py                        self-check
"""
import hashlib
import sys

BODY_OFF = 0x40          # préfixe opaque : octets 20..0x40
ROOT_TYPE = 100
ROOT_HEADER = 6          # longueur u32 + type u16


class WireError(ValueError):
    """Ce qui est lu n'a pas la forme annoncée."""


def read_varint(buf, i):
    """(valeur, offset suivant). Refuse un varint tronqué ou aberrant."""
    value = shift = 0
    while True:
        if i >= len(buf):
            raise WireError(f"varint tronqué à {i}")
        byte = buf[i]
        i += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, i
        if shift > 70:
            raise WireError(f"varint trop long à {i}")


def fields(buf):
    """Champs de premier niveau : (numéro, type wire, valeur).

    La valeur est un entier pour un varint, les octets bruts pour les trois
    autres types. Rien n'est interprété plus loin : c'est le rôle des schémas.
    """
    i = 0
    while i < len(buf):
        tag, i = read_varint(buf, i)
        number, wire_type = tag >> 3, tag & 7
        if number == 0:
            raise WireError(f"numéro de champ 0 à {i}")
        if wire_type == 0:
            value, i = read_varint(buf, i)
        elif wire_type == 2:
            size, i = read_varint(buf, i)
            if i + size > len(buf):
                raise WireError(f"longueur {size} dépasse le tampon à {i}")
            value, i = buf[i:i + size], i + size
        elif wire_type in (1, 5):
            width = 8 if wire_type == 1 else 4
            if i + width > len(buf):
                raise WireError(f"champ {width * 8} bits tronqué à {i}")
            value, i = buf[i:i + width], i + width
        else:
            raise WireError(f"type wire {wire_type} inconnu à {i}")
        yield number, wire_type, value


def walk(buf, depth=0, max_depth=6):
    """Arbre : [(champ, 'v'|'len'|'f32'|'f64', valeur[, sous-arbre])].

    Un bloc `len` est ré-essayé comme sous-message ; s'il ne parse pas, le
    sous-arbre vaut None et les octets restent disponibles tels quels.
    """
    out = []
    for number, wire_type, value in fields(buf):
        if wire_type == 0:
            out.append((number, "v", value))
        elif wire_type == 2:
            sub = None
            if depth < max_depth and value:
                try:
                    sub = walk(value, depth + 1, max_depth)
                except WireError:
                    sub = None
            out.append((number, "len", value, sub))
        else:
            out.append((number, "f64" if wire_type == 1 else "f32", value))
    return out


def parse_container(data):
    """Records enfants du conteneur racine : (index, type, offset, payload)."""
    if len(data) < BODY_OFF + ROOT_HEADER:
        raise WireError(f"fichier trop court : {len(data)} octets, "
                        f"{BODY_OFF + ROOT_HEADER} minimum")
    length = int.from_bytes(data[BODY_OFF:BODY_OFF + 4], "little")
    root_type = int.from_bytes(data[BODY_OFF + 4:BODY_OFF + 6], "little")
    if root_type != ROOT_TYPE:
        raise WireError(f"conteneur racine de type {root_type}, "
                        f"{ROOT_TYPE} attendu")
    start = BODY_OFF + ROOT_HEADER
    if start + length > len(data):
        raise WireError(f"racine de {length} octets, "
                        f"{len(data) - start} disponibles")
    body = data[start:start + length]
    records, i, index = [], 0, 0
    while i < len(body):
        if i + ROOT_HEADER > len(body):
            raise WireError(f"en-tête de record tronqué à {i}")
        size = int.from_bytes(body[i:i + 4], "little")
        record_type = int.from_bytes(body[i + 4:i + 6], "little")
        if i + ROOT_HEADER + size > len(body):
            raise WireError(f"record de type {record_type} tronqué à {i}")
        records.append((index, record_type, start + i + ROOT_HEADER,
                        body[i + ROOT_HEADER:i + ROOT_HEADER + size]))
        i += ROOT_HEADER + size
        index += 1
    return records


def load(path):
    """(octets, records) d'un fichier variante A, en-tête SHA-1 vérifié."""
    with open(path, "rb") as flux:
        data = flux.read()
    if len(data) < 20 or data[:20] != hashlib.sha1(data[20:]).digest():
        raise WireError(f"{path} : en-tête SHA-1 invalide")
    return data, parse_container(data)


def fmt_tree(tree, indent=0, maxlen=64):
    """L'arbre en lignes lisibles — texte quand c'est du texte, hex sinon."""
    lines = []
    for entry in tree:
        number, kind, pad = entry[0], entry[1], "  " * indent
        if kind == "v":
            lines.append(f"{pad}f{number}: {entry[2]}")
        elif kind in ("f32", "f64"):
            lines.append(f"{pad}f{number} {kind}: {entry[2].hex()}")
        else:
            chunk, sub = entry[2], entry[3]
            if sub is not None:
                lines.append(f"{pad}f{number} msg({len(chunk)}o):")
                lines += fmt_tree(sub, indent + 1, maxlen)
                continue
            try:
                text = chunk.decode("utf-8")
                if text and text.isprintable():
                    lines.append(f"{pad}f{number} str: {text!r}")
                    continue
            except UnicodeDecodeError:
                pass
            hexa = chunk.hex()
            if len(hexa) > maxlen * 2:
                hexa = hexa[:maxlen * 2] + f"…(+{len(chunk) - maxlen}o)"
            lines.append(f"{pad}f{number} bytes({len(chunk)}o): {hexa}")
    return lines


def self_check():
    message = bytes([0x08, 0x06, 0x12, 0x03]) + b"abc" + bytes([0x1A, 0x02, 0x08, 0x01])
    assert list(fields(message)) == [
        (1, 0, 6), (2, 2, b"abc"), (3, 2, b"\x08\x01")]
    tree = walk(message)
    assert tree[0] == (1, "v", 6) and tree[1][2] == b"abc"
    assert tree[2][3] == [(1, "v", 1)], tree[2]
    assert fmt_tree(tree)[1] == "f2 str: 'abc'"

    for refus in (b"\x08", b"\x08\x80", b"\x12\x05abc", b"\x07\xff",
                  b"\x0d\x01\x02", b"\x09\x01"):
        try:
            list(fields(refus))
            raise AssertionError(f"accepté : {refus!r}")
        except WireError:
            pass

    # Le conteneur : une racine bien formée passe, chaque troncature est nommée.
    inner = (3).to_bytes(4, "little") + (101).to_bytes(2, "little") + b"abc"
    racine = len(inner).to_bytes(4, "little") + ROOT_TYPE.to_bytes(2, "little")
    bon = b"\x00" * BODY_OFF + racine + inner
    assert parse_container(bon) == [(0, 101, BODY_OFF + 12, b"abc")]
    mauvais = {
        "trop court": b"\x00" * 8,
        "type racine": b"\x00" * BODY_OFF + len(inner).to_bytes(4, "little")
                       + (99).to_bytes(2, "little") + inner,
        "racine débordante": b"\x00" * BODY_OFF
                             + (len(inner) + 8).to_bytes(4, "little")
                             + ROOT_TYPE.to_bytes(2, "little") + inner,
        "record débordant": b"\x00" * BODY_OFF + racine
                            + (99).to_bytes(4, "little")
                            + (101).to_bytes(2, "little") + b"abc",
    }
    for nom, corps in mauvais.items():
        try:
            parse_container(corps)
            raise AssertionError(f"accepté : {nom}")
        except WireError:
            pass
    print("self-check ok : varints, champs, arbre et conteneur — "
          "refus nommés, pas d'assertion")


def main(argv):
    if len(argv) < 2:
        self_check()
        return 0
    data, records = load(argv[1])
    if len(argv) < 3:
        print(f"== {argv[1]} ({len(data)} o)")
        for index, record_type, offset, payload in records:
            empreinte = hashlib.sha1(payload).hexdigest()[:8]
            print(f"  [{index:2d}] type {record_type:3d} len {len(payload):5d} "
                  f"@0x{offset:05x} sha {empreinte}")
        return 0
    voulus = {int(x) for x in argv[2].split(",")}
    for index, record_type, offset, payload in records:
        if record_type not in voulus:
            continue
        print(f"--- [{index}] type {record_type} len {len(payload)} @0x{offset:05x}")
        try:
            print("\n".join(fmt_tree(walk(payload), 1)))
        except WireError as erreur:
            apercu = payload[:96].hex() + ("…" if len(payload) > 96 else "")
            print(f"  (pas du protobuf : {erreur}) hex: {apercu}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except WireError as erreur:
        print(f"erreur : {erreur}", file=sys.stderr)
        sys.exit(2)
