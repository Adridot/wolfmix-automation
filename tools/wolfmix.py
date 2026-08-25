#!/usr/bin/env python3
"""Manage a Wolfmix W1 directly over its USB serial connection.

Project writes are restricted to deterministic experiment UUIDs and never
overwrite ordinary controller projects. Firmware operations are not exposed.

Usage:
  python3 tools/wolfmix.py settings
  python3 tools/wolfmix.py projects
  python3 tools/wolfmix.py project UUID output.wpj
  python3 tools/wolfmix.py experiment-uuid LABEL
  python3 tools/wolfmix.py profiles
  python3 tools/wolfmix.py dmx
  python3 tools/wolfmix.py dmx --seconds 10
  python3 tools/wolfmix.py self-test

WTOOLS must be closed because the serial port is exclusive.
"""

import argparse
import datetime
import fcntl
import glob
import json
import os
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
import uuid


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


class WolfmixError(Exception):
    """Base error for direct Wolfmix communication."""


class ProtocolError(WolfmixError):
    """Raised for malformed or rejected protocol messages."""


def read_varint(data, offset=0):
    value = 0
    for shift in range(0, 70, 7):
        if offset >= len(data):
            raise ProtocolError("Truncated protobuf varint")
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
    raise ProtocolError("Protobuf varint exceeds 64 bits")


def protobuf_fields(data):
    """Yield ``(field_number, wire_type, value)`` tuples."""
    offset = 0
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        field_number, wire_type = tag >> 3, tag & 7
        if field_number == 0:
            raise ProtocolError("Invalid protobuf field number 0")
        if wire_type == 0:
            value, offset = read_varint(data, offset)
        elif wire_type == 1:
            if offset + 8 > len(data):
                raise ProtocolError("Truncated protobuf 64-bit field")
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == 2:
            size, offset = read_varint(data, offset)
            if offset + size > len(data):
                raise ProtocolError("Truncated protobuf length-delimited field")
            value = data[offset : offset + size]
            offset += size
        elif wire_type == 5:
            if offset + 4 > len(data):
                raise ProtocolError("Truncated protobuf 32-bit field")
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ProtocolError(f"Unsupported protobuf wire type {wire_type}")
        yield field_number, wire_type, value


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
    for number, wire_type, value in protobuf_fields(data):
        field = SETTINGS_FIELDS.get(number)
        if not field:
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
    return result


def format_uuid(value):
    if len(value) != 16:
        return value.hex()
    hex_value = value.hex()
    return "-".join(
        (hex_value[:8], hex_value[8:12], hex_value[12:16],
         hex_value[16:20], hex_value[20:])
    )


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
        raise ProtocolError(f"Outgoing event {event} is not allowlisted")
    size = HEADER_SIZE + len(payload)
    return struct.pack(">BIHH", VERSION, size, message_id, event) + payload


def discover_port():
    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    if not ports:
        raise WolfmixError("No USB modem port found; connect the Wolfmix W1")
    if len(ports) > 1:
        raise WolfmixError(
            "Multiple USB modem ports found; select one with --port: "
            + ", ".join(ports)
        )
    return ports[0]


def port_holders(path):
    """Return processes already holding the serial port on macOS."""
    lsof = shutil.which("lsof")
    if not lsof:
        return []
    result = subprocess.run(
        [lsof, "-Fpc", path], capture_output=True, text=True, check=False
    )
    holders = []
    pid = None
    for line in result.stdout.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("c") and pid is not None and pid != os.getpid():
            holders.append((pid, line[1:]))
    return holders


class WolfmixConnection:
    def __init__(self, path, timeout=5.0):
        self.path = path
        self.timeout = timeout
        self.fd = None
        self.buffer = bytearray()
        self.next_message_id = 1

    def __enter__(self):
        holders = port_holders(self.path)
        if holders:
            details = ", ".join(f"{name} (PID {pid})" for pid, name in holders)
            raise WolfmixError(
                f"Cannot open {self.path}: already used by {details}; "
                "close WTOOLS and try again"
            )
        try:
            self.fd = os.open(
                self.path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK
            )
            fcntl.ioctl(self.fd, termios.TIOCEXCL)
            attributes = termios.tcgetattr(self.fd)
            attributes[0] = 0
            attributes[1] = 0
            attributes[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
            attributes[3] = 0
            attributes[4] = termios.B115200
            attributes[5] = termios.B115200
            attributes[6][termios.VMIN] = 0
            attributes[6][termios.VTIME] = 0
            termios.tcsetattr(self.fd, termios.TCSANOW, attributes)
        except OSError as error:
            self.close()
            if error.errno in (13, 16, 35):
                raise WolfmixError(
                    f"Cannot open {self.path}: close WTOOLS and try again"
                ) from error
            raise WolfmixError(f"Cannot open {self.path}: {error}") from error
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def write_all(self, data):
        offset = 0
        deadline = time.monotonic() + self.timeout
        while offset < len(data):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WolfmixError("Timed out writing to the Wolfmix")
            _, writable, _ = select.select([], [self.fd], [], remaining)
            if not writable:
                continue
            offset += os.write(self.fd, data[offset:])

    def read_frame(self, timeout=None):
        deadline = time.monotonic() + (self.timeout if timeout is None else timeout)
        while True:
            if len(self.buffer) >= HEADER_SIZE:
                if self.buffer[0] != VERSION:
                    del self.buffer[0]
                    continue
                size = struct.unpack(">I", self.buffer[1:5])[0]
                if size < HEADER_SIZE or size > MAX_MESSAGE_SIZE:
                    del self.buffer[0]
                    continue
                if len(self.buffer) >= size:
                    frame = bytes(self.buffer[:size])
                    del self.buffer[:size]
                    version, _, message_id, event = struct.unpack(">BIHH", frame[:9])
                    return version, message_id, event, frame[9:]
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WolfmixError("Timed out waiting for the Wolfmix")
            readable, _, _ = select.select([self.fd], [], [], remaining)
            if readable:
                chunk = os.read(self.fd, 65536)
                if not chunk:
                    raise WolfmixError("Wolfmix connection closed")
                self.buffer.extend(chunk)

    def request(self, event, payload=b""):
        message_id = self.send(event, payload)
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WolfmixError(
                    f"Timed out waiting for {EVENT_NAMES.get(event, event)}"
                )
            _, reply_id, reply_event, payload = self.read_frame(remaining)
            if reply_id != message_id:
                continue
            if reply_event == RETURN_PROGRESS:
                continue
            if reply_event == RETURN_STATUS:
                status = decode_status(payload)
                if not status["success"]:
                    raise ProtocolError(
                        status["description"] or f"Wolfmix error {status.get('code')}"
                    )
                return payload
            if reply_event != event:
                raise ProtocolError(
                    f"Expected event {event}, received event {reply_event}"
                )
            return payload

    def send(self, event, payload=b""):
        """Write one complete request without waiting for its response."""
        message_id = self.next_message_id
        self.next_message_id = 1 if message_id == 65535 else message_id + 1
        self.write_all(build_frame(message_id, event, payload))
        return message_id


def print_json(value, compact=False):
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":") if compact else None,
                     indent=None if compact else 2), flush=compact)


def monitor_dmx(connection, seconds):
    settings = decode_settings(connection.request(GET_SETTINGS))
    enabled_by_us = not settings.get("dmxUsbSendState", False)
    if enabled_by_us:
        status = decode_status(connection.request(ENABLE_USB_DMX))
        if not status["success"]:
            raise ProtocolError(status["description"] or "USB DMX was rejected")

    previous = {}
    deadline = time.monotonic() + seconds if seconds > 0 else None
    try:
        while deadline is None or time.monotonic() < deadline:
            timeout = connection.timeout
            if deadline is not None:
                timeout = max(0.001, min(timeout, deadline - time.monotonic()))
            try:
                _, _, event, payload = connection.read_frame(timeout)
            except WolfmixError as error:
                if deadline is not None and time.monotonic() >= deadline:
                    break
                raise error
            if event != DMX_PACKET:
                continue
            packet = decode_dmx_packet(payload)
            dmx = packet["data"]
            # Firmware 2.0.18 sends all four universes in natural order.
            # Older firmware sent one universe and used protobuf field 2 as its index.
            universe_chunks = (
                [(packet["field2"], dmx)] if len(dmx) == 512 else
                [(index, dmx[index * 512 : (index + 1) * 512])
                 for index in range(len(dmx) // 512)]
            )
            for universe, current in universe_chunks:
                before = previous.get(universe)
                if before is None:
                    values = {
                        str(i + 1): value
                        for i, value in enumerate(current)
                        if value
                    }
                    key = "channels"
                else:
                    values = {
                        str(i + 1): value
                        for i, (old, value) in enumerate(zip(before, current))
                        if old != value
                    }
                    key = "changes"
                previous[universe] = current
                if values or before is None:
                    output = {
                        "timestamp": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                        "universeIndex": universe,
                        "universeNumber": universe + 1,
                        key: values,
                    }
                    if len(dmx) > 512:
                        output["unknownFrameField2"] = packet["field2"]
                    print_json(output, compact=True)
    finally:
        if enabled_by_us:
            try:
                connection.request(DISABLE_USB_DMX)
            except WolfmixError as error:
                print(f"warning: could not disable USB DMX: {error}", file=sys.stderr)


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


def experiment_identity(label):
    label = label.strip()
    if not label:
        raise WolfmixError("Experiment label cannot be empty")
    return (
        str(uuid.uuid5(EXPERIMENT_NAMESPACE, label)),
        (EXPERIMENT_NAME_PREFIX + label)[:19],
    )


def encode_project(project_uuid, version, name, data):
    try:
        raw_uuid = uuid.UUID(project_uuid).bytes
    except ValueError as error:
        raise WolfmixError(f"Invalid UUID: {project_uuid}") from error
    if not name.startswith(EXPERIMENT_NAME_PREFIX):
        raise WolfmixError(
            f"Experiment project names must start with {EXPERIMENT_NAME_PREFIX!r}"
        )
    if len(name) > 19:
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


def require_success(payload, operation):
    status = decode_status(payload)
    if not status["success"]:
        raise ProtocolError(
            status["description"] or f"{operation} failed with code {status.get('code')}"
        )
    return status


def store_experiment_project(connection, label, data, version=None):
    project_uuid, name = experiment_identity(label)
    version = int(time.time() * 1000) if version is None else version
    payload = encode_project(project_uuid, version, name, data)
    status = require_success(
        connection.request(SET_PROJECT, payload), "Storing experiment project"
    )
    return {
        "uuid": project_uuid,
        "name": name,
        "version": version,
        "size": len(data),
        "status": status,
    }


def remove_experiment_project(connection, label, project_list=None):
    project_uuid, name = experiment_identity(label)
    projects = project_list
    if projects is None:
        projects = decode_item_list(connection.request(GET_PROJECT_LIST))
    item = next((item for item in projects if item.get("uuid") == project_uuid), None)
    if item is None:
        raise WolfmixError(f"Experiment project is not on the controller: {name}")
    if not item.get("name", "").startswith(EXPERIMENT_NAME_PREFIX):
        raise WolfmixError("Refusing to delete a project without the experiment prefix")
    return require_success(
        connection.request(DELETE_PROJECT, encode_request_uuid(project_uuid)),
        "Deleting experiment project",
    )


def self_test():
    settings_payload = b"".join((
        encode_protobuf_field(1, 0, 1),
        encode_protobuf_field(3, 0, 0),
        encode_protobuf_field(9, 0, 2_001_998),
        encode_protobuf_field(13, 5, struct.pack("<f", 2.018)),
        encode_protobuf_field(14, 2, b"2.0.18"),
        encode_protobuf_field(15, 2, b"\x00\x01\x02\x03"),
    ))
    settings = decode_settings(settings_payload)
    assert settings["dmxEngineState"] is True
    assert settings["dmxUsbSendState"] is False
    assert settings["serialNumber"] == 2_001_998
    assert settings["firmwareVer"] == "2.0.18"
    assert settings["universeMapping"] == [0, 1, 2, 3]

    uuid_bytes = bytes(range(16))
    item = b"".join((
        encode_protobuf_field(1, 2, uuid_bytes),
        encode_protobuf_field(2, 0, 42),
        encode_protobuf_field(3, 2, b"Demo"),
        encode_protobuf_field(4, 0, 1234),
    ))
    project_list = decode_item_list(encode_protobuf_field(1, 2, item))
    assert project_list == [{
        "uuid": "00010203-0405-0607-0809-0a0b0c0d0e0f",
        "version": 42,
        "name": "Demo",
        "size": 1234,
    }]

    dmx = bytes([0, 255]) + bytes(510)
    packet = decode_dmx_packet(
        encode_protobuf_field(1, 2, dmx) + encode_protobuf_field(2, 0, 1)
    )
    assert packet == {"data": dmx, "field2": 1}

    frame = build_frame(7, GET_SETTINGS)
    assert struct.unpack(">BIHH", frame) == (1, 9, 7, GET_SETTINGS)
    assert encode_request_uuid("00010203-0405-0607-0809-0a0b0c0d0e0f") == (
        encode_protobuf_field(1, 2, uuid_bytes)
    )
    experiment_uuid, experiment_name = experiment_identity("self-test")
    project_payload = encode_project(
        experiment_uuid, 42, experiment_name, b"project"
    )
    fields = list(protobuf_fields(project_payload))
    assert fields[0][2] == uuid.UUID(experiment_uuid).bytes
    assert fields[1][2] == 42
    assert fields[2][2].decode() == experiment_name
    assert fields[3][2] == 7 and fields[4][2] == b"project"
    try:
        build_frame(1, 25)
        raise AssertionError("The outgoing event allowlist was bypassed")
    except ProtocolError:
        pass
    print("self-test OK")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="USB serial port; auto-detected by default")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="request timeout in seconds (default: 5)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("settings", help="read controller settings and state")
    commands.add_parser("projects", help="list projects stored on the controller")
    commands.add_parser("profiles", help="list fixture profiles on the controller")
    project = commands.add_parser("project", help="download one project")
    project.add_argument("uuid", help="project UUID from the projects command")
    project.add_argument("output", help="new output file; existing files are refused")
    identity = commands.add_parser(
        "experiment-uuid", help="show the deterministic UUID for an experiment label"
    )
    identity.add_argument("label")
    dmx = commands.add_parser("dmx", help="stream changed DMX channel values")
    dmx.add_argument("--seconds", type=float, default=0,
                     help="stop after this duration; 0 runs until Ctrl-C")
    commands.add_parser("self-test", help="run protocol checks without hardware")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "self-test":
        self_test()
        return 0
    if args.command == "experiment-uuid":
        experiment_uuid, name = experiment_identity(args.label)
        print_json({"label": args.label, "uuid": experiment_uuid, "name": name})
        return 0
    if args.timeout <= 0:
        raise WolfmixError("--timeout must be greater than zero")
    if args.command == "dmx" and args.seconds < 0:
        raise WolfmixError("--seconds cannot be negative")

    port = args.port or discover_port()
    with WolfmixConnection(port, timeout=args.timeout) as connection:
        if args.command == "settings":
            print_json(decode_settings(connection.request(GET_SETTINGS)))
        elif args.command == "projects":
            print_json(decode_item_list(connection.request(GET_PROJECT_LIST)))
        elif args.command == "profiles":
            print_json(decode_item_list(
                connection.request(GET_PROFILE_LIST), profile=True
            ))
        elif args.command == "project":
            project = decode_project(connection.request(
                GET_PROJECT, encode_request_uuid(args.uuid)
            ))
            try:
                with open(args.output, "xb") as output:
                    output.write(project.pop("data"))
            except FileExistsError as error:
                raise WolfmixError(
                    f"Output already exists and was not overwritten: {args.output}"
                ) from error
            project["output"] = os.path.abspath(args.output)
            print_json(project)
        elif args.command == "dmx":
            monitor_dmx(connection, args.seconds)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped", file=sys.stderr)
        sys.exit(130)
    except WolfmixError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
