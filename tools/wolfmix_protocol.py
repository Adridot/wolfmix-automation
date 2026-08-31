#!/usr/bin/env python3
"""The W1's protocol: frames, events, protobuf, decoding.

Nothing here touches a port or a file — only bytes and dicts. That is what
makes this module readable on its own, and testable with no device.

The domains that bound what may be sent live here too: the outgoing event
allowlist, the mutations subject to the firmware gate, the panel's own recall
range, and the named modes.
"""
import json
import os
import struct
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ssl2
import wpj_wire

VERSION = 1

HEADER_SIZE = 9

MAX_MESSAGE_SIZE = 1_000_000

GET_PROFILE = 3

GET_PROFILE_LIST = 2

GET_PROJECT_LIST = 4

GET_PROJECT = 5

DISABLE_ENGINE = 6

ENABLE_ENGINE = 7

DISABLE_USB_DMX = 8

ENABLE_USB_DMX = 9

DMX_PACKET = 12

DELETE_PROJECT = 16

SET_PROJECT = 18

RETURN_STATUS = 19

RETURN_PROGRESS = 20

GET_SETTINGS = 21

SET_MODE = 39

SET_PRESET = 41

SKIP_PRESET = 43

RESTART = 44

EXPERIMENT_NAMESPACE = uuid.UUID("d7ad3c90-367d-5eef-a8bb-f523c6f96d9a")

EXPERIMENT_NAME_PREFIX = "WMX EXP "

# The only two namespaces this repository writes. "exp" derives from the bare
# label — that is the historical scheme, and the states already on disk depend
# on it; "auto" derives from a prefixed label, so never the same UUID.
MANAGED_PREFIXES = {"exp": EXPERIMENT_NAME_PREFIX, "auto": "WMX AUTO "}

PROJECT_NAME_MAX = 19

ALLOWED_OUTGOING_EVENTS = {
    GET_PROFILE_LIST,
    GET_PROFILE,
    GET_PROJECT_LIST,
    GET_PROJECT,
    DISABLE_ENGINE,
    ENABLE_ENGINE,
    DISABLE_USB_DMX,
    ENABLE_USB_DMX,
    DELETE_PROJECT,
    SET_PROJECT,
    GET_SETTINGS,
    SET_MODE,
    SET_PRESET,
    SKIP_PRESET,
    RESTART,
}

# Events that change what the controller holds, shows or outputs. Reads stay
# unconditional; these are refused on a firmware nobody here has measured.
MUTATING_EVENTS = {
    DISABLE_ENGINE,
    ENABLE_ENGINE,
    DISABLE_USB_DMX,
    ENABLE_USB_DMX,
    DELETE_PROJECT,
    SET_PROJECT,
    SET_MODE,
    SET_PRESET,
    SKIP_PRESET,
    RESTART,
}

TESTED_FIRMWARE = ("2.0.18",)

# The panel's own range. 200-255 has only ever produced the no-op an absent id
# produces, which a byte masked at the far end would produce too (RECALL-06):
# unprobed either way, so it is not sent.
PRESET_ID_MAX = 199

# Modes reached from the panel and measured (SPEC.md §10.2). Entering
# one changes the screen, not the show — BLACKOUT excepted, and the operator
# asks for that one by name.
NAMED_MODES = {
    "home": 0,
    "color": 1,
    "move": 3,
    "beam": 4,
    "presets": 5,
    "static_color": 7,
    "gobo": 8,
    "static_position": 9,
    "live_edit": 10,
    "static_position_picker": 12,
    "gobo_edit": 14,
    "live_edit_edit": 15,
    "setup": 16,
    "fixture_setup": 17,
    "fixture_selection": 19,
    "move_seq": 21,
    "dmx_levels": 23,
    "settings": 25,
    "wolf": 28,
    "strobe": 29,
    "speed": 30,
    "blinder": 32,
    "blackout": 33,
    "intelligent_preset": 34,
    "beam_editor": 36,
    "live_edit_macro_edit": 41,
    "mapping": 43,
    "bpm": 44,
}

# Left out of NAMED_MODES on purpose, reachable only with --experimental:
# 26 is modal and is not left by 0/5/16; 40 redirects to 42, which attempts a
# USB read on entry; 39 lights the pads with the screen stuck on HOME and its
# name is a guess. Every other index is simply unmeasured.
ACTING_MODES = {26, 39, 40, 42}

# SCREEN-02: the reported mode always takes the value asked for; the screen
# does not. Measured on the device, stable, and independent of the screen the
# panel starts from. An index in neither set was never tried.
MODES_MOVING_SCREEN = {1, 3, 4, 26}

MODES_SCREEN_INERT = {0, 5, 16}

def screen_follows(index):
    """True / False / None (never measured) — SCREEN-02."""
    if index in MODES_MOVING_SCREEN:
        return True
    if index in MODES_SCREEN_INERT:
        return False
    return None

EVENT_NAMES = {
    GET_PROFILE_LIST: "GET_PROFILE_LIST",
    GET_PROFILE: "GET_PROFILE",
    GET_PROJECT_LIST: "GET_PROJECT_LIST",
    GET_PROJECT: "GET_PROJECT",
    DISABLE_ENGINE: "DISABLE_ENGINE",
    ENABLE_ENGINE: "ENABLE_ENGINE",
    DISABLE_USB_DMX: "DISABLE_USB_DMX",
    ENABLE_USB_DMX: "ENABLE_USB_DMX",
    DMX_PACKET: "DMX_PACKET",
    DELETE_PROJECT: "DELETE_PROJECT",
    SET_PROJECT: "SET_PROJECT",
    RETURN_STATUS: "RETURN_STATUS",
    RETURN_PROGRESS: "RETURN_PROGRESS",
    GET_SETTINGS: "GET_SETTINGS",
    SET_MODE: "SET_MODE",
    SET_PRESET: "SET_PRESET",
    SKIP_PRESET: "SKIP_PRESET",
    RESTART: "RESTART",
}

SETTINGS_FIELDS = {
    1: ("dmxEngineState", "bool"),
    2: ("extSyncState", "bool"),
    3: ("dmxUsbSendState", "bool"),
    4: ("lockedState", "bool"),
    5: ("editLockedState", "bool"),
    6: ("fixtureProfileCount", "uint"),
    7: ("projectCount", "uint"),
    8: ("availableMemory", "uint"),
    9: ("serialNumber", "uint"),
    10: ("activatedUniverses", "uint"),
    11: ("availableUniverses", "uint"),
    12: ("visualiserActivated", "bool"),
    13: ("firmwareVersion", "float"),
    14: ("firmwareVer", "string"),
    15: ("universeMapping", "packed_uint"),
    16: ("wlinkActivated", "bool"),
    17: ("wolfmixMode", "uint"),
    18: ("oem", "uint"),
    19: ("projectChanged", "bool"),
    20: ("availableProjectMemory", "uint"),
}

# GET_PROFILE's reply — measured 2026-08-31 on fw 2.0.18 (PROFILE-01), from one
# profile family read three times. Field → (name, kind); a kind wrapped in a
# list is repeated. A field the repository has observed but not attributed
# keeps its neutral `fN` name here; a field number absent from these tables
# lands in `unknownFields`, the way `decode_settings` surfaces one.
PROFILE_CHANNEL_FIELDS = {
    1: ("index", "uint"),
    2: ("type", "enum"),
    3: ("default", "uint"),
    4: ("name", "string"),
}

# `f4` is the axis the two readings disagree on: `research/versions.md` reads it
# as the channel type of what the preset acts on, `ssl2.CIBLE_PRESET` points the
# same preset type elsewhere. Unsettled, so the key stays neutral and no
# equivalence with SSLPRESETTARGET is claimed. `f5` is a flag whose kind was
# never established.
PROFILE_PRESET_FIELDS = {
    1: ("channel", "uint"),
    2: ("dmxStart", "uint"),
    3: ("dmxEnd", "uint"),
    4: ("f4", "enum"),
    5: ("f5", "uint"),
    6: ("dmxDefault", "uint"),
    7: ("red", "uint"),
    8: ("green", "uint"),
    9: ("blue", "uint"),
    10: ("iconId", "uint"),
    11: ("isDefault", "bool"),
}

PROFILE_MODE_FIELDS = {
    1: ("index", "uint"),
    2: ("channelCount", "uint"),
    3: ("f3", "uint"),
}

PROFILE_BODY_FIELDS = {
    1: ("channels", [PROFILE_CHANNEL_FIELDS]),
    2: ("f2", ["hex"]),                   # a link table, undecoded; one
                                          # entry per (mode, channel), not
                                          # the ×16 versions.md read
    3: ("presets", [PROFILE_PRESET_FIELDS]),
    4: ("modes", [PROFILE_MODE_FIELDS]),
    5: ("f5", "uint"),
    6: ("f6", "uint"),
}

PROFILE_FIELDS = {
    1: ("uuid", "uuid"),
    2: ("name", "string"),
    3: ("body", PROFILE_BODY_FIELDS),
    4: ("version", "uint"),
    5: ("brandName", "string"),
}

class WolfmixError(Exception):
    """Base error for direct Wolfmix communication."""

class ProtocolError(WolfmixError):
    """Raised for malformed or rejected protocol messages."""

def read_varint(data, offset=0):
    """The shared production reader, with this module's error type."""
    try:
        return wpj_wire.read_varint(data, offset)
    except wpj_wire.WireError as error:
        raise ProtocolError(str(error)) from None

def protobuf_fields(data):
    """Yield ``(field_number, wire_type, value)`` tuples.

    One wire reader for the whole repository (``wpj_wire``); only the error
    type is this module's, because callers catch ``ProtocolError``.
    """
    try:
        yield from wpj_wire.fields(data)
    except wpj_wire.WireError as error:
        raise ProtocolError(str(error)) from None

def decode_packed_varints(data):
    values = []
    offset = 0
    while offset < len(data):
        value, offset = read_varint(data, offset)
        values.append(value)
    return values

def decode_settings(data):
    result = {
        name: ([] if kind == "packed_uint" else "" if kind == "string"
               else False if kind == "bool" else 0.0 if kind == "float" else 0)
        for name, kind in SETTINGS_FIELDS.values()
    }
    inconnus = {}
    for number, wire_type, value in protobuf_fields(data):
        field = SETTINGS_FIELDS.get(number)
        if not field:
            # The firmware carries settings we cannot name — "store group
            # dimmers in preset" (GEN-02) may well be one of them. Surfacing
            # them lets a plain before/after diff settle it when the operator
            # flips a switch, without ever inventing a name for them.
            inconnus[number] = value.hex() if isinstance(value, bytes) else value
            continue
        name, kind = field
        if kind == "bool" and wire_type == 0:
            result[name] = bool(value)
        elif kind == "uint" and wire_type == 0:
            result[name] = value
        elif kind == "float" and wire_type == 5:
            result[name] = struct.unpack("<f", value)[0]
        elif kind == "string" and wire_type == 2:
            result[name] = value.decode("utf-8", "replace")
        elif kind == "packed_uint" and wire_type == 2:
            result[name] = decode_packed_varints(value)
        elif kind == "packed_uint" and wire_type == 0:
            result.setdefault(name, []).append(value)
        else:
            raise ProtocolError(f"Unexpected wire type for Settings.{name}")
    if inconnus:
        result["unknownFields"] = inconnus
    return result

def format_uuid(value):
    if len(value) != 16:
        return value.hex()
    hex_value = value.hex()
    return "-".join(
        (hex_value[:8], hex_value[8:12], hex_value[12:16],
         hex_value[16:20], hex_value[20:])
    )

def _profile_value(kind, value):
    """One field's value, plus the extra keys it carries (an enum's name)."""
    if isinstance(kind, dict):
        return _profile_fields(value, kind), {}
    if kind == "uuid":
        return format_uuid(value), {}
    if kind == "string":
        return value.decode("utf-8", "replace"), {}
    if kind == "hex":
        return value.hex(), {}
    if kind == "bool":
        return bool(value), {}
    if kind == "enum":
        # The number is the measurement and is always emitted; the name is the
        # reading. `TYPE_CANAL` was checked against the firmware for eleven of
        # its 47 values, so a number it does not hold gets no name rather than
        # a guess.
        libelle = ssl2.TYPE_CANAL.get(value)
        return value, {"Name": libelle[0]} if libelle else {}
    return value, {}


def _profile_fields(data, table):
    result = {}
    inconnus = {}
    for number, wire_type, value in protobuf_fields(data):
        field = table.get(number)
        if not field:
            inconnus[number] = value.hex() if isinstance(value, bytes) else value
            continue
        name, kind = field
        repete = isinstance(kind, list)
        decoded, extra = _profile_value(kind[0] if repete else kind, value)
        if repete:
            result.setdefault(name, []).append(decoded)
        else:
            result[name] = decoded
        for suffixe, supplement in extra.items():
            result[name + suffixe] = supplement
    if inconnus:
        result["unknownFields"] = inconnus
    return result


def decode_profile(data):
    """One fixture profile as the controller hands it over — GET_PROFILE."""
    return _profile_fields(data, PROFILE_FIELDS)


def decode_item(data, profile=False):
    result = {}
    for number, wire_type, value in protobuf_fields(data):
        if number == 1 and wire_type == 2:
            result["uuid"] = format_uuid(value)
        elif number == 2 and wire_type == 0:
            result["version"] = value
        elif number == 3 and wire_type == 2:
            result["name"] = value.decode("utf-8", "replace")
        elif number == 4 and wire_type == 2 and profile:
            result["brandName"] = value.decode("utf-8", "replace")
        elif number == 4 and wire_type == 0 and not profile:
            result["size"] = value
    return result

def decode_item_list(data, profile=False):
    return [
        decode_item(value, profile=profile)
        for number, wire_type, value in protobuf_fields(data)
        if number == 1 and wire_type == 2
    ]

def decode_project(data):
    project = {}
    for number, wire_type, value in protobuf_fields(data):
        if number == 1 and wire_type == 2:
            project["uuid"] = format_uuid(value)
        elif number == 2 and wire_type == 0:
            project["version"] = value
        elif number == 3 and wire_type == 2:
            project["name"] = value.decode("utf-8", "replace")
        elif number == 4 and wire_type == 0:
            project["size"] = value
        elif number == 5 and wire_type == 2:
            project["data"] = value
    if "data" not in project:
        raise ProtocolError("Project response contains no data")
    return project

def decode_status(data):
    result = {"success": False, "description": ""}
    for number, wire_type, value in protobuf_fields(data):
        if number == 1 and wire_type == 0:
            result["id"] = value
        elif number == 2 and wire_type == 0:
            result["success"] = bool(value)
        elif number == 3 and wire_type == 2:
            result["description"] = value.decode("utf-8", "replace")
        elif number == 4 and wire_type == 0:
            result["code"] = value
    return result

def decode_dmx_packet(data):
    packet = {}
    for number, wire_type, value in protobuf_fields(data):
        if number == 1 and wire_type == 2:
            packet["data"] = value
        elif number == 2 and wire_type == 0:
            packet["field2"] = value
    dmx = packet.get("data", b"")
    if not dmx or len(dmx) % 512 or "field2" not in packet:
        raise ProtocolError("Malformed DMX packet")
    return packet

def build_frame(message_id, event, payload=b""):
    if event not in ALLOWED_OUTGOING_EVENTS:
        raise ProtocolError(
            f"Outgoing event {EVENT_NAMES.get(event, event)} is not allowlisted"
        )
    size = HEADER_SIZE + len(payload)
    return struct.pack(">BIHH", VERSION, size, message_id, event) + payload

def print_json(value, compact=False):
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":") if compact else None,
                     indent=None if compact else 2), flush=compact)

def encode_varint(value):
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)

def encode_protobuf_field(number, wire_type, value):
    tag = encode_varint((number << 3) | wire_type)
    if wire_type == 0:
        return tag + encode_varint(value)
    if wire_type == 2:
        return tag + encode_varint(len(value)) + value
    if wire_type == 5:
        return tag + value
    raise AssertionError("Unsupported self-test wire type")

def encode_request_uuid(value):
    try:
        raw_uuid = uuid.UUID(value).bytes
    except ValueError as error:
        raise WolfmixError(f"Invalid UUID: {value}") from error
    return encode_protobuf_field(1, 2, raw_uuid)

def managed_identity(label, kind="exp"):
    """(derived UUID, name) of a managed project. Deterministic, never random.

    This is what keeps an ordinary project from ever being written: the target
    is not chosen, it is computed from the label.
    """
    if kind not in MANAGED_PREFIXES:
        raise WolfmixError(
            f"Unknown managed namespace {kind!r}; "
            f"known: {', '.join(sorted(MANAGED_PREFIXES))}"
        )
    label = label.strip()
    if not label:
        raise WolfmixError("Managed project label cannot be empty")
    graine = label if kind == "exp" else f"{kind}:{label}"
    nom = (MANAGED_PREFIXES[kind] + label)[:PROJECT_NAME_MAX]
    return str(uuid.uuid5(EXPERIMENT_NAMESPACE, graine)), nom


def is_managed_name(name):
    return name.startswith(tuple(MANAGED_PREFIXES.values()))


def experiment_identity(label):
    """The experiment namespace — the historical case."""
    return managed_identity(label, "exp")

def encode_project(project_uuid, version, name, data):
    try:
        raw_uuid = uuid.UUID(project_uuid).bytes
    except ValueError as error:
        raise WolfmixError(f"Invalid UUID: {project_uuid}") from error
    if not is_managed_name(name):
        raise WolfmixError(
            "Managed project names must start with one of "
            + ", ".join(repr(x) for x in sorted(MANAGED_PREFIXES.values()))
        )
    if len(name) > PROJECT_NAME_MAX:
        raise WolfmixError("Wolfmix project names cannot exceed 19 characters")
    if not data:
        raise WolfmixError("Refusing to upload an empty project")
    return b"".join((
        encode_protobuf_field(1, 2, raw_uuid),
        encode_protobuf_field(2, 0, version),
        encode_protobuf_field(3, 2, name.encode("utf-8")),
        encode_protobuf_field(4, 0, len(data)),
        encode_protobuf_field(5, 2, data),
    ))

def index_payload(value):
    """Payload for the short events: firmware 2.0.18 reads ``payload[0]``.

    These events are NOT protobuf. Sending a protobuf-shaped ``[tag, value]``
    pair makes the controller read the *tag* byte as the index — the trap that
    produced a day of "the value is ignored" readings. See RAW-01 and RECALL-03
    in ``research/evidence.md``.

    An id above the highest one present is a no-op (RECALL-04); interior gaps
    are unprobed. Nothing above 0x7f has produced anything but that no-op, which
    a byte rejected or masked at the far end would produce too — so ids 128-199,
    pages 7 to 10, are untested either way.
    """
    if not 0 <= value <= 255:
        raise WolfmixError("Index must be between 0 and 255")
    return bytes([value])

def preset_payload(value):
    """Recall id, bounded to the panel's own range."""
    if not 0 <= value <= PRESET_ID_MAX:
        raise WolfmixError(
            f"Preset id must be 0-{PRESET_ID_MAX}, the panel's own range; "
            "200-255 is unprobed and is not sent"
        )
    return index_payload(value)

def resolve_mode(value, experimental=False):
    """A measured mode by name, or a raw index behind --experimental."""
    key = str(value).strip().lower().replace("-", " ").replace(" ", "_")
    if key in NAMED_MODES:
        return NAMED_MODES[key]
    if not experimental:
        known = ", ".join(sorted(NAMED_MODES))
        raise WolfmixError(
            f"Unknown mode {value!r}. Raw and unmeasured indexes — including "
            f"{sorted(ACTING_MODES)}, which act on entry or are modal — need "
            f"--experimental. Measured modes: {known}"
        )
    try:
        index = int(str(value), 0)
    except ValueError:
        raise WolfmixError(f"Not a mode name and not an index: {value!r}") from None
    if not 0 <= index <= 255:
        raise WolfmixError("Mode index must be between 0 and 255")
    return index
