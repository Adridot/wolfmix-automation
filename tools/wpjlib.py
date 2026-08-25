#!/usr/bin/env python3
"""Cœur lecture/écriture des .wpj variante A (SHA-1 + conteneur TLV).

Principe de sûreté (règle « lecture avant écriture ») :
- load() découpe le fichier en enregistrements TLV bruts, sans interpréter.
- save() réassemble : longueurs recalculées, en-tête SHA-1 recalculé,
  octets 20–63 (préfixe opaque) préservés verbatim.
- Un enregistrement non modifié est réémis octet pour octet ; round-trip
  sans édition = fichier octet-identique, garanti par construction et
  vérifié par self-check sur tout le corpus.
- Écriture toujours vers un NOUVEAU fichier, jamais d'écrasement.
"""
import hashlib
import struct
import sys

ROOT_TYPE = 100
BODY_OFF = 0x40  # conteneur racine ; préfixe opaque = octets 20..0x40


class Wpj:
    def __init__(self, prefix, records):
        self.prefix = prefix          # octets 20..0x46 (préfixe + en-tête TLV racine, brut)
        self.records = records        # list[(type:int, payload:bytes)]

    @classmethod
    def load(cls, path):
        return cls.from_bytes(open(path, "rb").read(), str(path))

    @classmethod
    def from_bytes(cls, d, source="<bytes>"):
        """Parse a variant-A project from bytes without creating a file."""
        if d[:20] != hashlib.sha1(d[20:]).digest():
            raise ValueError(f"{source}: invalid SHA-1 header")
        root_len, root_type = struct.unpack_from("<IH", d, BODY_OFF)
        if root_type != ROOT_TYPE or BODY_OFF + 6 + root_len != len(d):
            raise ValueError(f"{source}: not a root container type 100 "
                             f"(type={root_type}, length={root_len})")
        records, i, end = [], BODY_OFF + 6, len(d)
        while i < end:
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
        with open(path, "xb") as f:  # 'x' : refuse d'écraser
            f.write(data)
        return hashlib.sha256(data).hexdigest()

    def replace(self, typ, new_payload, occurrence=0):
        """Remplace le payload de la n-ième occurrence d'un type."""
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
    import glob
    files = sorted(glob.glob("corpus/**/*.wpj", recursive=True))
    tested = 0
    for path in files:
        try:
            w = Wpj.load(path)
        except ValueError:
            continue  # variantes B/C : hors périmètre de cette lib
        orig = open(path, "rb").read()
        rebuilt = hashlib.sha1(w.body()).digest() + w.body()
        assert rebuilt == orig, f"round-trip NON identique : {path}"
        tested += 1
    assert tested >= 5, f"corpus variante A introuvable (cwd ?) : {tested} fichiers"
    print(f"self-check ok : round-trip octet-identique sur {tested} fichiers",
          file=sys.stderr)


if __name__ == "__main__":
    demo()
