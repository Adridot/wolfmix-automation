#!/usr/bin/env python3
"""Independent read-only WPJ wire inspector.

Module group: Format. Reference: SPEC.md.

Walks the protobuf wire format of a "WTOOLS-shaped" .wpj and emits a JSON tree
(fields, wire types, values). No invented semantics: field names are numbers,
and unknown bytes come out as hex.

Usage: wpj_inspect.py fichier.wpj [--depth N] > out.json
Format status: the wire format was validated on 6/6 large local .wpj files
(2026-08-25). Small .wpj files (device dumps?) do NOT parse — the tool says so
and exits with an error rather than guessing.
"""

from __future__ import annotations
import json
import sys
import hashlib

MAX_DEPTH_DEFAULT = 6


def read_varint(buf: bytes, i: int) -> tuple[int, int]:
    v = shift = 0
    while True:
        if i >= len(buf):
            raise ValueError(f"truncated varint at {i}")  # end of buffer: not protobuf
        b = buf[i]
        i += 1
        v |= (b & 0x7F) << shift
        shift += 7
        if not b & 0x80:
            return v, i
        if shift > 70:
            raise ValueError(f"varint too long at {i}")


def walk(buf: bytes, depth: int, max_depth: int) -> list[dict[str, object]]:
    """Returns a list of fields, or raises ValueError if this is not protobuf."""
    i, out = 0, []
    while i < len(buf):
        tag, i = read_varint(buf, i)
        field, wt = tag >> 3, tag & 7
        if field == 0:
            raise ValueError(f"field number 0 at {i}")
        if wt == 0:
            v, i = read_varint(buf, i)
            out.append({"f": field, "wt": "varint", "v": v})
        elif wt == 2:
            ln, i = read_varint(buf, i)
            if i + ln > len(buf):
                raise ValueError(f"length {ln} runs past the buffer at {i}")
            chunk = buf[i : i + ln]
            i += ln
            entry = {"f": field, "wt": "len", "n": ln}
            # candidates, not a choice: emit sub-message AND/OR text AND hex
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
                raise ValueError(f"truncated f32 at {i}")
            out.append({"f": field, "wt": "f32", "hex": buf[i : i + 4].hex()})
            i += 4
            continue
        elif wt == 1:
            if i + 8 > len(buf):
                raise ValueError(f"truncated f64 at {i}")
            out.append({"f": field, "wt": "f64", "hex": buf[i : i + 8].hex()})
            i += 8
            continue
        else:
            raise ValueError(f"unknown wire type {wt} at {i}")
        if wt == 2:
            out.append(entry)
    return out


def inspect(path: str, max_depth: int = MAX_DEPTH_DEFAULT) -> dict[str, object]:
    data = open(path, "rb").read()
    # variant C: protobuf from 0; variant B: SHA-1 (20 B) then protobuf
    entete = len(data) > 20 and data[:20] == hashlib.sha1(data[20:]).digest()
    for off in ((20, 0) if entete else (0, 20)):
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
        "format": "protobuf-wire (structure observed, semantics not validated)",
        "bodyOffset": off,
        "sha1HeaderOk": sha1_ok if off == 20 else None,
        "fields": tree,
    }


def demo() -> None:
    """Self-check on a protobuf message built by hand."""
    msg = bytes([0x08, 0x06, 0x12, 0x03]) + b"abc" + bytes([0x1A, 0x02, 0x08, 0x01])
    out = walk(msg, 0, 3)
    assert out[0] == {"f": 1, "wt": "varint", "v": 6}
    assert out[1]["text"] == "abc"
    assert out[2]["msg"] == [{"f": 1, "wt": "varint", "v": 1}]
    try:
        walk(b"\x07\xff\xff", 0, 3)
        raise AssertionError("should have been rejected")
    except ValueError:
        pass
    for tronque in (b"\x08", b"\x08\x80", b"\x12\x05abc"):
        try:
            walk(tronque, 0, 3)
            raise AssertionError(f"should have rejected {tronque!r}")
        except ValueError:
            pass                       # truncated buffer -> ValueError, never IndexError
    print("self-check ok", file=sys.stderr)


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("fichier", nargs="?",
                         help="the .wpj to walk; with no argument, self-check")
    parseur.add_argument("--depth", type=int, default=MAX_DEPTH_DEFAULT,
                         help="profondeur maximale de descente "
                              f"(defaut : {MAX_DEPTH_DEFAULT})")
    args = parseur.parse_args(argv)
    if args.fichier is None:
        demo()
        return 0
    try:
        json.dump(inspect(args.fichier, args.depth), sys.stdout,
                  ensure_ascii=False)
        print()
    except ValueError as erreur:
        print(f"NOT the protobuf wire format: {erreur}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
