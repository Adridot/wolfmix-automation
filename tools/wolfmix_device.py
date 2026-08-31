#!/usr/bin/env python3
"""Le lien série avec le W1, et les opérations de haut niveau qui s'y appuient.

La garde firmware vit dans `WolfmixConnection.send` : un appelant ne peut pas
l'oublier. Le port est exclusif — WTOOLS ouvert, rien ne passe — et
`port_holders` le dit avec le nom du processus fautif plutôt qu'un errno.
"""
import datetime
import fcntl
import glob
import hashlib
import os
import select
import shutil
import struct
import subprocess
import sys
import termios
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wolfmix_protocol import (
    ALLOWED_OUTGOING_EVENTS, DELETE_PROJECT, DISABLE_USB_DMX, DMX_PACKET,
    ENABLE_USB_DMX, EVENT_NAMES, GET_PROJECT,
    GET_PROJECT_LIST, GET_SETTINGS, HEADER_SIZE, MAX_MESSAGE_SIZE,
    MUTATING_EVENTS, RETURN_PROGRESS, RETURN_STATUS, SET_PROJECT,
    TESTED_FIRMWARE, VERSION, ProtocolError, WolfmixError, build_frame,
    decode_dmx_packet, decode_item_list, decode_project, decode_settings,
    decode_status, encode_project, encode_request_uuid, is_managed_name,
    managed_identity, print_json,
)

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
    def __init__(self, path, timeout=5.0, allow_untested_firmware=False):
        self.path = path
        self.timeout = timeout
        self.fd = None
        self.buffer = bytearray()
        self.next_message_id = 1
        self.allow_untested_firmware = allow_untested_firmware
        self.firmware = None

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

    def check_firmware(self):
        """Refuse a state change on a firmware nobody here has measured.

        Read once, cached, and checked in ``send`` rather than in each caller:
        a gate a caller can forget is not a gate. Reads are unaffected — only
        the events in ``MUTATING_EVENTS`` pass through here.
        """
        if self.firmware is None:
            self.firmware = decode_settings(
                self.request(GET_SETTINGS)
            ).get("firmwareVer")
        if self.allow_untested_firmware or self.firmware in TESTED_FIRMWARE:
            return self.firmware
        raise WolfmixError(
            f"Controller firmware is {self.firmware!r}; this repository has "
            f"measured {', '.join(TESTED_FIRMWARE)}. Reads are allowed, state "
            "changes are refused — pass --allow-untested-firmware to proceed"
        )

    def send(self, event, payload=b""):
        """Write one complete request without waiting for its response."""
        if event in MUTATING_EVENTS:
            self.check_firmware()
        message_id = self.next_message_id
        self.next_message_id = 1 if message_id == 65535 else message_id + 1
        self.write_all(build_frame(message_id, event, payload))
        return message_id

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

def watch_mode(connection, interval, seconds):
    """Report every change of Settings.wolfmixMode; never writes to the W1.

    Ground truth for the WM_MODE_* enum: the operator walks the controller
    through its screens while this polls GET_SETTINGS, which is read-only.
    """
    previous = None
    deadline = time.monotonic() + seconds if seconds > 0 else None
    while deadline is None or time.monotonic() < deadline:
        settings = decode_settings(connection.request(GET_SETTINGS))
        mode = settings["wolfmixMode"]
        if mode != previous:
            print_json({
                "timestamp": datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                "wolfmixMode": mode,
                "previousMode": previous,
                "projectChanged": settings["projectChanged"],
            }, compact=True)
            previous = mode
        time.sleep(interval)

def dmx_envelope(connection, seconds):
    """Per-channel min/max of the DMX output over a window.

    A single frame is not comparable between runs because effects animate. The
    envelope is: a static channel has min == max, an animated one keeps its
    range whatever the phase. This is the oracle for differential experiments —
    it answers "did this project change alter the output at all".
    """
    settings = decode_settings(connection.request(GET_SETTINGS))
    enabled_by_us = not settings["dmxUsbSendState"]
    if enabled_by_us:
        require_success(connection.request(ENABLE_USB_DMX), "Enabling USB DMX")
    low = high = None
    frames = 0
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            try:
                _, _, event, payload = connection.read_frame(
                    max(0.001, min(connection.timeout, deadline - time.monotonic()))
                )
            except WolfmixError:
                # The residual wait shrinks to nothing at the end of the window;
                # that is the window closing, not a dead controller.
                if time.monotonic() >= deadline:
                    break
                raise
            if event != DMX_PACKET:
                continue
            data = decode_dmx_packet(payload)["data"]
            if low is None:
                low, high = list(data), list(data)
            else:
                for index, value in enumerate(data):
                    if value < low[index]:
                        low[index] = value
                    if value > high[index]:
                        high[index] = value
            frames += 1
    finally:
        if enabled_by_us:
            connection.request(DISABLE_USB_DMX)
    if not frames:
        raise WolfmixError("No DMX frame was received")
    return {
        "frames": frames,
        "channels": len(low),
        "wolfmixMode": settings["wolfmixMode"],
        "animatedChannels": sum(1 for a, b in zip(low, high) if a != b),
        "nonZeroChannels": sum(1 for value in high if value),
        "min": low,
        "max": high,
    }

def fetch_project(connection, project_uuid, attempts=3):
    """Download one project, guarding against serial corruption.

    The link is not error-free: a 43 KB transfer has been observed returning
    the right length with wrong bytes, and another returning an unparsable
    payload. Variant A and B files carry a SHA-1 of their own body, so verify
    it; for anything else, require two identical consecutive downloads.
    """
    previous = None
    last_error = None
    for _ in range(attempts):
        try:
            project = decode_project(connection.request(
                GET_PROJECT, encode_request_uuid(project_uuid)
            ))
        except ProtocolError as error:
            last_error = error
            continue
        data = project["data"]
        if len(data) > 20 and data[:20] == hashlib.sha1(data[20:]).digest():
            return project
        if previous == data:
            return project
        previous = data
        last_error = ProtocolError("Downloaded project failed its SHA-1 header")
    raise ProtocolError(
        f"Project download did not verify after {attempts} attempts: {last_error}"
    )

def require_success(payload, operation):
    status = decode_status(payload)
    if not status["success"]:
        raise ProtocolError(
            status["description"] or f"{operation} failed with code {status.get('code')}"
        )
    return status

def store_managed_project(connection, label, data, version=None, attempts=3,
                          kind="exp"):
    """Upload a project, retrying when the controller rejects the transfer.

    The link corrupts large transfers in both directions. A corrupted upload is
    refused outright by the firmware — observed as "invalid wire_type" on a
    43 KB project — so a rejection is retried rather than treated as fatal. The
    firmware stores nothing on a failed status, and the caller verifies by
    downloading afterwards.
    """
    project_uuid, name = managed_identity(label, kind)
    version = int(time.time() * 1000) if version is None else version
    payload = encode_project(project_uuid, version, name, data)
    for attempt in range(1, attempts + 1):
        try:
            status = require_success(
                connection.request(SET_PROJECT, payload), "Storing experiment project"
            )
            break
        except ProtocolError as error:
            if attempt == attempts:
                raise ProtocolError(
                    f"Upload rejected {attempts} times, last: {error}"
                ) from error
            print(f"warning: upload attempt {attempt} rejected ({error}); retrying",
                  file=sys.stderr)
    return {
        "uuid": project_uuid,
        "name": name,
        "version": version,
        "size": len(data),
        "status": status,
    }

def remove_managed_project(connection, label, project_list=None, kind="exp"):
    project_uuid, name = managed_identity(label, kind)
    projects = project_list
    if projects is None:
        projects = decode_item_list(connection.request(GET_PROJECT_LIST))
    item = next((item for item in projects if item.get("uuid") == project_uuid), None)
    if item is None:
        raise WolfmixError(f"Experiment project is not on the controller: {name}")
    if not is_managed_name(item.get("name", "")):
        raise WolfmixError("Refusing to delete a project we did not derive")
    return require_success(
        connection.request(DELETE_PROJECT, encode_request_uuid(project_uuid)),
        "Deleting experiment project",
    )


# Anciens noms, gardes le temps d'une version : le seul changement est que la
# cible peut desormais etre l'espace « auto ».
store_experiment_project = store_managed_project
remove_experiment_project = remove_managed_project
