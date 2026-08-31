#!/usr/bin/env python3
"""The production client for the W1: read it, drive its live state, download.

This file is the **command line**. What it calls lives elsewhere:

  wolfmix_protocol.py     frames, events, protobuf, decoding, domains
  wolfmix_device.py       the serial port and the operations built on it
  wolfmix_transaction.py  backup, archive, verified upload, rollback
  wolfmix_experiment.py   campaigns and experiments

A persistent write never targets an ordinary project: it goes to a derived
UUID. No executable-firmware operation is exposed, in any of these files.

Usage :
  python3 tools/wolfmix.py settings
  python3 tools/wolfmix.py projects
  python3 tools/wolfmix.py project UUID output.wpj
  python3 tools/wolfmix.py experiment-uuid LABEL
  python3 tools/wolfmix.py profiles
  python3 tools/wolfmix.py dmx
  python3 tools/wolfmix.py dmx --seconds 10
  python3 tools/wolfmix.py preset 12
  python3 tools/wolfmix.py mode presets
  python3 tools/wolfmix.py watch-mode
  python3 tools/wolfmix.py dmx-envelope before.json --seconds 12
  python3 tools/wolfmix.py self-test

WTOOLS must be closed: the serial port is exclusive.
"""
import argparse
import hashlib
import io
import json
import os
import struct
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wolfmix_protocol import (
    ACTING_MODES, ALLOWED_OUTGOING_EVENTS, DMX_PACKET, GET_PROFILE_LIST,
    GET_PROJECT_LIST, GET_SETTINGS, HEADER_SIZE, MODES_MOVING_SCREEN,
    MODES_SCREEN_INERT, MUTATING_EVENTS, NAMED_MODES, PRESET_ID_MAX,
    ProtocolError, SET_MODE, SET_PRESET, TESTED_FIRMWARE, VERSION,
    WolfmixError, build_frame, decode_dmx_packet, decode_item_list,
    decode_settings, encode_project, encode_protobuf_field,
    encode_request_uuid, experiment_identity, index_payload, preset_payload,
    print_json, protobuf_fields, resolve_mode, screen_follows
)
from wolfmix_device import (
    WolfmixConnection, discover_port, dmx_envelope, fetch_project,
    monitor_dmx, require_success, watch_mode
)


def self_test():
    settings_payload = b"".join((
        encode_protobuf_field(1, 0, 1),
        encode_protobuf_field(3, 0, 0),
        encode_protobuf_field(9, 0, 1_234_567),
        encode_protobuf_field(13, 5, struct.pack("<f", 2.018)),
        encode_protobuf_field(14, 2, b"2.0.18"),
        encode_protobuf_field(15, 2, b"\x00\x01\x02\x03"),
    ))
    settings = decode_settings(settings_payload)
    assert settings["dmxEngineState"] is True
    assert settings["dmxUsbSendState"] is False
    assert settings["serialNumber"] == 1_234_567
    assert settings["firmwareVer"] == "2.0.18"
    assert settings["universeMapping"] == [0, 1, 2, 3]
    assert "unknownFields" not in settings
    inconnu = decode_settings(settings_payload + encode_protobuf_field(99, 0, 1))
    assert inconnu["unknownFields"] == {99: 1}

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
    # An event we can name but never send is refused by that name.
    try:
        build_frame(1, DMX_PACKET)
        raise AssertionError("An incoming-only event was framed")
    except ProtocolError as error:
        assert "DMX_PACKET" in str(error), error
    # RAW-01: one raw byte, no protobuf tag. 23 must go on the wire as 0x17.
    assert index_payload(23) == b"\x17" and index_payload(114) == b"\x72"
    assert build_frame(1, SET_PRESET, index_payload(23)) == (
        struct.pack(">BIHH", VERSION, HEADER_SIZE + 1, 1, SET_PRESET) + b"\x17"
    )
    for out_of_range in (-1, 256):
        try:
            index_payload(out_of_range)
            raise AssertionError("index_payload accepted an out-of-range index")
        except WolfmixError:
            pass
    # The recall domain stops at the panel's own range.
    assert preset_payload(PRESET_ID_MAX) == bytes([PRESET_ID_MAX])
    for refused in (-1, PRESET_ID_MAX + 1, 255):
        try:
            preset_payload(refused)
            raise AssertionError(f"preset_payload accepted {refused}")
        except WolfmixError:
            pass
    # A measured mode by name; a raw or acting index only with --experimental.
    assert resolve_mode("presets") == 5 and resolve_mode("Static-Color") == 7
    for refused in ("42", "26", "99", "not-a-mode"):
        try:
            resolve_mode(refused)
            raise AssertionError(f"resolve_mode accepted {refused!r} bare")
        except WolfmixError:
            pass
    assert resolve_mode("42", experimental=True) == 42
    assert not ACTING_MODES & set(NAMED_MODES.values())
    # SCREEN-02: measured on both sides, and silent about what was never tried.
    assert not MODES_MOVING_SCREEN & MODES_SCREEN_INERT
    assert screen_follows(4) is True and screen_follows(26) is True
    assert screen_follows(0) is False and screen_follows(5) is False
    assert screen_follows(29) is None
    # No firmware operation is reachable: the allowlist is the only way out.
    assert MUTATING_EVENTS <= ALLOWED_OUTGOING_EVENTS

    class FakeGate(WolfmixConnection):
        """The firmware gate without a port: reads answer, writes must not happen."""

        def __init__(self, version, allow=False):
            super().__init__("fake", allow_untested_firmware=allow)
            self.version = version
            self.wrote = False

        def request(self, event, payload=b""):
            assert event == GET_SETTINGS, "the gate read something else"
            return encode_protobuf_field(14, 2, self.version.encode())

        def write_all(self, data):
            self.wrote = True

    tested = FakeGate(TESTED_FIRMWARE[0])
    tested.send(SET_PRESET, b"\x01")
    assert tested.wrote, "a tested firmware refused a mutation"
    untested = FakeGate("9.9.9")
    try:
        untested.send(SET_PRESET, b"\x01")
        raise AssertionError("an untested firmware accepted a mutation")
    except WolfmixError as error:
        assert "9.9.9" in str(error) and TESTED_FIRMWARE[0] in str(error), error
    assert not untested.wrote, "the refused mutation still reached the wire"
    overridden = FakeGate("9.9.9", allow=True)
    overridden.send(SET_PRESET, b"\x01")
    assert overridden.wrote, "--allow-untested-firmware did not let it through"

    class FakeConnection:
        """Replays a scripted list of project payloads, one per request."""

        def __init__(self, bodies):
            self.bodies = list(bodies)

        def request(self, event, payload=b""):
            body = self.bodies.pop(0)
            return b"".join((
                encode_protobuf_field(1, 2, uuid.UUID(experiment_uuid).bytes),
                encode_protobuf_field(5, 2, body),
            ))

    good = hashlib.sha1(b"body").digest() + b"body"
    corrupt = bytes(20) + b"body"
    # A corrupt first transfer is discarded once the next one verifies.
    assert fetch_project(FakeConnection([corrupt, good]), experiment_uuid)["data"] == good
    # Without a valid SHA-1 header, two identical transfers are accepted.
    assert fetch_project(
        FakeConnection([corrupt, corrupt]), experiment_uuid
    )["data"] == corrupt
    try:
        fetch_project(FakeConnection([corrupt, bytes(21), bytes(22)]), experiment_uuid)
        raise AssertionError("Three unverifiable transfers were accepted")
    except ProtocolError:
        pass
    print("self-test OK")

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="USB serial port; auto-detected by default")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="request timeout in seconds (default: 5)")
    parser.add_argument("--allow-untested-firmware", action="store_true",
                        help="allow state changes on a firmware this "
                             "repository has never measured; reads never "
                             "need it")
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
    watch = commands.add_parser(
        "watch-mode", help="log every UI mode change reported by the controller"
    )
    watch.add_argument("--interval", type=float, default=0.2,
                       help="polling period in seconds (default: 0.2)")
    watch.add_argument("--seconds", type=float, default=0,
                       help="stop after this duration; 0 runs until Ctrl-C")
    envelope = commands.add_parser(
        "dmx-envelope", help="per-channel min/max of the output over a window"
    )
    envelope.add_argument("output", help="new JSON file; existing files are refused")
    envelope.add_argument("--seconds", type=float, default=12.0)
    dmx = commands.add_parser("dmx", help="stream changed DMX channel values")
    dmx.add_argument("--seconds", type=float, default=0,
                     help="stop after this duration; 0 runs until Ctrl-C")
    preset = commands.add_parser(
        "preset", help="recall a preset by its id (id = (page-1)*20 + slot-1)"
    )
    preset.add_argument("id", type=int,
                        help=f"preset id, 0-{PRESET_ID_MAX}; an id above the "
                             "highest one present does nothing, and interior "
                             "gaps are a no-op")
    mode = commands.add_parser(
        "mode", help="set the reported mode; the panel does not always follow"
    )
    mode.add_argument("mode",
                      help="mode name: " + ", ".join(sorted(NAMED_MODES)))
    mode.add_argument("--experimental", action="store_true",
                      help="accept a raw index instead of a name; raw indexes "
                           "reach screens the panel menu does not expose and "
                           "some act on entry — see MODE-40/42")
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
    if args.command in ("dmx", "watch-mode") and args.seconds < 0:
        raise WolfmixError("--seconds cannot be negative")
    if args.command == "dmx-envelope" and args.seconds <= 0:
        raise WolfmixError("--seconds must be greater than zero")
    if args.command == "watch-mode" and args.interval <= 0:
        raise WolfmixError("--interval must be greater than zero")

    port = args.port or discover_port()
    with WolfmixConnection(
        port, timeout=args.timeout,
        allow_untested_firmware=args.allow_untested_firmware,
    ) as connection:
        if args.command == "settings":
            print_json(decode_settings(connection.request(GET_SETTINGS)))
        elif args.command == "projects":
            print_json(decode_item_list(connection.request(GET_PROJECT_LIST)))
        elif args.command == "profiles":
            print_json(decode_item_list(
                connection.request(GET_PROFILE_LIST), profile=True
            ))
        elif args.command == "project":
            project = fetch_project(connection, args.uuid)
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
        elif args.command == "dmx-envelope":
            result = dmx_envelope(connection, args.seconds)
            try:
                with open(args.output, "x", encoding="utf-8") as output:
                    json.dump(result, output)
            except FileExistsError as error:
                raise WolfmixError(
                    f"Output already exists and was not overwritten: {args.output}"
                ) from error
            print_json({k: v for k, v in result.items() if k not in ("min", "max")})
        elif args.command == "preset":
            payload = preset_payload(args.id)
            require_success(
                connection.request(SET_PRESET, payload),
                f"Recalling preset {args.id}",
            )
            # The id sent is not necessarily the entry reached, and nothing
            # in GET_SETTINGS names it — so report what was requested.
            print_json({"requested": args.id,
                        "untestedFirmware": args.allow_untested_firmware})
        elif args.command == "mode":
            index = resolve_mode(args.mode, args.experimental)
            require_success(
                connection.request(SET_MODE, index_payload(index)),
                f"Switching to mode {index}",
            )
            settings = decode_settings(connection.request(GET_SETTINGS))
            # The index is not always the mode reached: 40 lands on 42.
            print_json({"requested": index,
                        "measured": index not in ACTING_MODES
                                    and index in NAMED_MODES.values(),
                        "screenFollows": screen_follows(index),
                        "wolfmixMode": settings["wolfmixMode"]})
        elif args.command == "watch-mode":
            watch_mode(connection, args.interval, args.seconds)
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
