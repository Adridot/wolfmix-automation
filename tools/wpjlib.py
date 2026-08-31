#!/usr/bin/env python3
"""The read/write core of variant-A .wpj files (SHA-1 + TLV container).

The safety principle — "read before write":
- load() cuts the file into raw TLV records, interpreting nothing.
- save() reassembles: lengths recomputed, SHA-1 header recomputed, bytes
  20-63 (the opaque prefix) preserved verbatim.
- An untouched record is re-emitted byte for byte; a round trip with no edit
  gives a byte-identical file, by construction, and the self-check proves it
  over the whole corpus.
- Writing always goes to a NEW file, never over an existing one.
"""
import glob
import hashlib
import os
import struct
import sys

CORPUS_ENV = "WPJ_CORPUS"
CORPUS_DEFAUT = "corpus"

ROOT_TYPE = 100
BODY_OFF = 0x40  # root container; the opaque prefix is bytes 20..0x40


def corpus_files(motif="**/*.wpj"):
    """Fichiers de corpus locaux. Racine : $WPJ_CORPUS, sinon ./corpus.

    No .wpj file ships with this repository (see docs/corpus.md): the
    self-checks run on the corpus you supply, and abstain cleanly when there
    is none.
    """
    racine = os.environ.get(CORPUS_ENV) or CORPUS_DEFAUT
    return sorted(glob.glob(os.path.join(racine, motif), recursive=True))


# The word the runner in `tools/check.py` looks for. An abstention is not a
# pass, and it must be impossible to read as one — in the line itself, in the
# summary, and in the exit code.
ABSTENTION = "ABSTAINED"


def pas_de_corpus(outil):
    print(f"{outil}: {ABSTENTION} — no corpus in "
          f"{os.environ.get(CORPUS_ENV) or CORPUS_DEFAUT}/, nothing was "
          f"verified (see docs/corpus.md)", file=sys.stderr)


class Wpj:
    def __init__(self, prefix, records):
        self.prefix = prefix          # bytes 20..0x46 (prefix + root TLV header, raw)
        self.records = records        # list[(type:int, payload:bytes)]

    @classmethod
    def load(cls, path):
        with open(path, "rb") as flux:
            return cls.from_bytes(flux.read(), str(path))

    @classmethod
    def from_bytes(cls, d, source="<bytes>"):
        """Parse a variant-A project from bytes without creating a file."""
        if len(d) < BODY_OFF + 6:
            raise ValueError(f"{source}: too short for a variant-A project "
                             f"({len(d)} bytes, {BODY_OFF + 6} minimum)")
        if d[:20] != hashlib.sha1(d[20:]).digest():
            raise ValueError(f"{source}: invalid SHA-1 header")
        root_len, root_type = struct.unpack_from("<IH", d, BODY_OFF)
        if root_type != ROOT_TYPE or BODY_OFF + 6 + root_len != len(d):
            raise ValueError(f"{source}: not a root container type 100 "
                             f"(type={root_type}, length={root_len})")
        records, i, end = [], BODY_OFF + 6, len(d)
        while i < end:
            if i + 6 > end:
                raise ValueError(f"{source}: truncated record header at {i}")
            ln, typ = struct.unpack_from("<IH", d, i)
            if i + 6 + ln > end:
                raise ValueError(f"{source}: truncated record at {i}")
            records.append((typ, d[i + 6 : i + 6 + ln]))
            i += 6 + ln
        return cls(d[20:BODY_OFF], records)

    def body(self):
        inner = b"".join(struct.pack("<IH", len(p), t) + p for t, p in self.records)
        return (self.prefix
                + struct.pack("<IH", len(inner), ROOT_TYPE)
                + inner)

    def save(self, path):
        body = self.body()
        data = hashlib.sha1(body).digest() + body
        with open(path, "xb") as f:  # 'x': refuses to overwrite
            f.write(data)
        return hashlib.sha256(data).hexdigest()

    def replace(self, typ, new_payload, occurrence=0):
        """Replace the payload of the n-th occurrence of a type."""
        n = 0
        for idx, (t, _) in enumerate(self.records):
            if t == typ:
                if n == occurrence:
                    self.records[idx] = (typ, new_payload)
                    return
                n += 1
        raise KeyError(f"type {typ} occurrence {occurrence} absent")

    def get(self, typ, occurrence=0):
        n = 0
        for t, p in self.records:
            if t == typ:
                if n == occurrence:
                    return p
                n += 1
        raise KeyError(f"type {typ} occurrence {occurrence} absent")


def demo():
    files = corpus_files()
    if not files:
        return pas_de_corpus("wpjlib")
    tested = 0
    for path in files:
        try:
            w = Wpj.load(path)
        except ValueError:
            continue  # variants B/C: out of scope for this library
        orig = open(path, "rb").read()
        rebuilt = hashlib.sha1(w.body()).digest() + w.body()
        assert rebuilt == orig, f"round-trip NON identique : {path}"
        tested += 1
    if not tested:
        return pas_de_corpus("wpjlib")
    print(f"self-check ok: byte-identical round trip on {tested} files",
          file=sys.stderr)


def _refus_attendus():
    """A file too short but with a valid SHA-1 header must be refused as a
    format error — not raise struct.error from somewhere inside."""
    for corps in (b"", b"x" * 10, b"x" * (BODY_OFF - 20)):
        court = hashlib.sha1(corps).digest() + corps
        try:
            Wpj.from_bytes(court, "<court>")
            raise AssertionError(f"accepted: {len(court)} bytes")
        except ValueError as err:
            assert "short" in str(err) or "root container" in str(err), err
    # A record header running past the end of the body is a named refusal.
    corps = bytearray(b"\x00" * (BODY_OFF - 20))
    inner = struct.pack("<IH", 3, 101) + b"abc" + b"\x00\x00"
    corps += struct.pack("<IH", len(inner), ROOT_TYPE) + inner
    tronque = hashlib.sha1(bytes(corps)).digest() + bytes(corps)
    try:
        Wpj.from_bytes(tronque, "<truncated>")
        raise AssertionError("a truncated record got through")
    except ValueError as err:
        assert "truncated" in str(err), err


if __name__ == "__main__":
    _refus_attendus()
    demo()
