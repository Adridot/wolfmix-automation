"""Synthetic bytes: a variant-A project and a flash image, built here.

Neither ships with this repository — the project files are someone's show and
the flash is the manufacturer's artwork (`LEGAL.md`). What the boundaries need
is the *shape*, and the shape is public: it is written down in `SPEC.md` and in
`tools/gobo_library.py`. So the tests build their own, and a wrong shape is a
failing test rather than a missing file.
"""
from collections.abc import Sequence

import hashlib
import struct

BODY_OFF = 0x40
ROOT_TYPE = 100

# Flash layout, from tools/gobo_library.py.
ICON = 1728
ENTRY = 30
TABLE_LEN = 800
FLASH_BASE = 0x10100000
OPEN_FLAGS = b"\x00\x00\x00\x00\x00\x01"      # what ANCHOR matches on
OTHER_FLAGS = b"\x00\x00\x00\x00\x00\x02"


def prefix_bytes() -> bytes:
    """The 44 bytes 20-63, with the four §9 constants where §9 puts them.

    `tools/wpj_coverage.py` declares those four spans inert and checks them on
    every file, so a test that feeds it zeros is testing the wrong refusal."""
    out = bytearray(BODY_OFF - 20)
    out[16:20] = bytes.fromhex("152b10c0")          # file offset 36
    out[28:30] = bytes.fromhex("01f9")              # 48
    out[32:44] = bytes.fromhex("02bee81ca26ccb546dc7b6ec")   # 52
    return bytes(out)


def project_bytes(
    records: Sequence[tuple[int, bytes]] = ((101, b"\x0a\x04demo"),),
    prefix: bytes | None = None,
) -> bytes:
    """A well-formed variant-A file: SHA-1 header, root container, records."""
    inner = b"".join(struct.pack("<IH", len(p), t) + p for t, p in records)
    body = (prefix if prefix is not None else b"\x00" * (BODY_OFF - 20))
    body += struct.pack("<IH", len(inner), ROOT_TYPE) + inner
    return hashlib.sha1(body).digest() + body


def flash_bytes(distinct: int = 4) -> bytes:
    """A flash image with `distinct` own icons and 796 sharing one pointer.

    The shared pointer is the point: on the device "Open" serves 96 entries at
    once, and patching it would repaint all of them. The last 30 bytes of the
    icon area are zeroed so that `Library`'s walk back out of the table stops
    where the table starts.
    """
    icons = [bytes((i * 37 + k) % 256 for k in range(ICON))
             for i in range(distinct)]
    shared = bytearray((k % 251) for k in range(ICON))
    shared[-ENTRY:] = b"\x00" * ENTRY
    icons.append(bytes(shared))

    offsets, running = [], 0
    for icon in icons:
        offsets.append(running)
        running += len(icon)
    table_offset = running
    pointers = [FLASH_BASE + off for off in offsets]

    entries = []
    for index in range(TABLE_LEN):
        if index < distinct:
            pointer, flags = pointers[index], OTHER_FLAGS
            name = f"Gobo{index:02d}".encode()
        else:
            pointer, flags = pointers[-1], OPEN_FLAGS
            name = b"Open"
        entries.append(struct.pack("<I", pointer) + flags
                       + name.ljust(20, b"\x00"))
    data = b"".join(icons) + b"".join(entries)
    assert data.find(OPEN_FLAGS + b"Open\x00") == table_offset + distinct * ENTRY + 4
    return data


def solid_icon(
    colour: tuple[int, int, int, int] = (255, 0, 255, 255),
) -> list[tuple[int, int, int, int]]:
    return [colour] * (24 * 24)
