#!/usr/bin/env python3
"""Lecteur wire de production : varints, champs protobuf, conteneur TLV.

Two wire implementations coexist here **on purpose** (AGENTS.md, "one
documented exception to no-repetition"):

  wpj_wire.py     this one, shared by the codec, the B/C reader, the USB
                  protocol and the gobo palette;
  wpj_inspect.py  a second, independent one, which serves as the oracle.

An oracle that shares its code with what it verifies only proves that code
agrees with itself. The other duplications are gone: this file replaces
`tlv.py` and `dump.py`.

Every refusal is a `WireError` (a `ValueError`): never an assertion — those
vanish under `python3 -O` — and never a standard-library exception passed
through as-is.

Usage :
  wpj_wire.py project.wpj            the container's record inventory
  wpj_wire.py project.wpj 165,150    the protobuf tree of those types
  wpj_wire.py                        self-check
"""
import hashlib
import sys

BODY_OFF = 0x40          # the opaque prefix is bytes 20..0x40
ROOT_TYPE = 100
ROOT_HEADER = 6          # longueur u32 + type u16


class WireError(ValueError):
    """What was read does not have the shape it claimed."""


def encode_varint(value: int) -> bytes:
    """Encode an unsigned varint; callers retain their input validation.

    This preserves the protocol encoder's bytes/exception behavior, including
    bool inputs. The semantic codec rejects bool before calling this function.
    """
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)


def read_varint(buf, i):
    """(value, next offset). Refuses a truncated or absurd varint."""
    value = shift = 0
    while True:
        if i >= len(buf):
            raise WireError(f"truncated varint at {i}")
        byte = buf[i]
        i += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, i
        if shift > 70:
            raise WireError(f"varint too long at {i}")


def fields(buf):
    """Top-level fields: (number, wire type, value).

    The value is an int for a varint and the raw bytes for the other three
    types. Nothing is interpreted further — that is the schemas' job.
    """
    i = 0
    while i < len(buf):
        tag, i = read_varint(buf, i)
        number, wire_type = tag >> 3, tag & 7
        if number == 0:
            raise WireError(f"field number 0 at {i}")
        if wire_type == 0:
            value, i = read_varint(buf, i)
        elif wire_type == 2:
            size, i = read_varint(buf, i)
            if i + size > len(buf):
                raise WireError(f"length {size} runs past the buffer at {i}")
            value, i = buf[i:i + size], i + size
        elif wire_type in (1, 5):
            width = 8 if wire_type == 1 else 4
            if i + width > len(buf):
                raise WireError(f"truncated {width * 8}-bit field at {i}")
            value, i = buf[i:i + width], i + width
        else:
            raise WireError(f"unknown wire type {wire_type} at {i}")
        yield number, wire_type, value


def walk(buf, depth=0, max_depth=6):
    """Tree: [(field, 'v'|'len'|'f32'|'f64', value[, subtree])].

    A `len` block is retried as a sub-message; when it does not parse, the
    subtree is None and the bytes stay available as they are.
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


def parse_container(data, *, source=None):
    """Child records: (index, type, offset, payload).

    A source label preserves Wpj's absolute-offset ValueError diagnostics;
    the wire inspector uses relative-offset WireError diagnostics.
    """
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
            if source is not None:
                raise ValueError(f"{source}: truncated record header at {start + i}")
            raise WireError(f"truncated record header at {i}")
        size = int.from_bytes(body[i:i + 4], "little")
        record_type = int.from_bytes(body[i + 4:i + 6], "little")
        if i + ROOT_HEADER + size > len(body):
            if source is not None:
                raise ValueError(f"{source}: truncated record at {start + i}")
            raise WireError(f"truncated record of type {record_type} at {i}")
        records.append((index, record_type, start + i + ROOT_HEADER,
                        body[i + ROOT_HEADER:i + ROOT_HEADER + size]))
        i += ROOT_HEADER + size
        index += 1
    return records


def load(path):
    """(bytes, records) of a variant-A file, SHA-1 header verified."""
    with open(path, "rb") as flux:
        data = flux.read()
    if len(data) < 20 or data[:20] != hashlib.sha1(data[20:]).digest():
        raise WireError(f"{path}: invalid SHA-1 header")
    return data, parse_container(data)


def fmt_tree(tree, indent=0, maxlen=64):
    """The tree as readable lines — text when it is text, hex otherwise."""
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
            raise AssertionError(f"accepted: {refus!r}")
        except WireError:
            pass

    # The container: a well-formed root passes, every truncation is named.
    inner = (3).to_bytes(4, "little") + (101).to_bytes(2, "little") + b"abc"
    racine = len(inner).to_bytes(4, "little") + ROOT_TYPE.to_bytes(2, "little")
    bon = b"\x00" * BODY_OFF + racine + inner
    assert parse_container(bon) == [(0, 101, BODY_OFF + 12, b"abc")]
    mauvais = {
        "too short": b"\x00" * 8,
        "root type": b"\x00" * BODY_OFF + len(inner).to_bytes(4, "little")
                     + (99).to_bytes(2, "little") + inner,
        "root overflowing": b"\x00" * BODY_OFF
                            + (len(inner) + 8).to_bytes(4, "little")
                            + ROOT_TYPE.to_bytes(2, "little") + inner,
        "record overflowing": b"\x00" * BODY_OFF + racine
                            + (99).to_bytes(4, "little")
                            + (101).to_bytes(2, "little") + b"abc",
    }
    for nom, corps in mauvais.items():
        try:
            parse_container(corps)
            raise AssertionError(f"accepted: {nom}")
        except WireError:
            pass
    print("self-check ok: varints, fields, tree and container — "
          "named refusals, no assertion")


def main(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("fichier", nargs="?",
                         help="the .wpj to read; with no argument, self-check")
    parseur.add_argument("types", nargs="?",
                         help="record types separated by commas; without "
                              "them, the inventory")
    args = parseur.parse_args(argv)
    if args.fichier is None:
        self_check()
        return 0
    data, records = load(args.fichier)
    if args.types is None:
        print(f"== {args.fichier} ({len(data)} o)")
        for index, record_type, offset, payload in records:
            empreinte = hashlib.sha1(payload).hexdigest()[:8]
            print(f"  [{index:2d}] type {record_type:3d} len {len(payload):5d} "
                  f"@0x{offset:05x} sha {empreinte}")
        return 0
    voulus = {int(x) for x in args.types.split(",")}
    for index, record_type, offset, payload in records:
        if record_type not in voulus:
            continue
        print(f"--- [{index}] type {record_type} len {len(payload)} @0x{offset:05x}")
        try:
            print("\n".join(fmt_tree(walk(payload), 1)))
        except WireError as erreur:
            apercu = payload[:96].hex() + ("…" if len(payload) > 96 else "")
            print(f"  (not protobuf: {erreur}) hex: {apercu}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except WireError as erreur:
        print(f"error: {erreur}", file=sys.stderr)
        sys.exit(2)
