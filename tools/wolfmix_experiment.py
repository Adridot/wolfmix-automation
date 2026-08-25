#!/usr/bin/env python3
"""Run transactional Wolfmix project experiments without WTOOLS.

The runner only writes a deterministic project UUID derived from an experiment
label. It snapshots controller projects before initialization, verifies every
upload by downloading it again, restores the previous experiment project on
failure, and records each run under ``.wolfmix-state``.

One manual bootstrap remains necessary because firmware 2.0.18 exposes no
USB command for selecting a project: run ``init``, open the resulting
``WMX EXP ...`` project once on the W1, then run ``arm``. Deployments and
campaigns are automatic after that point.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wolfmix
import wpj_codec
import wpjlib


DEFAULT_STATE_ROOT = ".wolfmix-state"


def utc_id():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ"
    )


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_project(path, project_name=None):
    path = Path(path).resolve()
    project = wpjlib.Wpj.load(path)
    if project_name is not None:
        metadata = wpj_codec.decode(101, project.get(101))
        if set(metadata) == {"raw"}:
            raise wolfmix.WolfmixError("Project name record 101 is not decodable")
        metadata["nom"] = project_name
        project.replace(101, wpj_codec.encode(101, metadata))
        body = project.body()
        data = hashlib.sha1(body).digest() + body
    else:
        data = path.read_bytes()
    return path, data


def state_paths(state_root, label):
    project_uuid, _ = wolfmix.experiment_identity(label)
    root = Path(state_root).resolve() / project_uuid
    return root, root / "state.json"


def load_state(state_root, label):
    root, state_file = state_paths(state_root, label)
    if not state_file.exists():
        raise wolfmix.WolfmixError(
            f"Experiment is not initialized: {label!r}; run init first"
        )
    state = read_json(state_file)
    expected_uuid, expected_name = wolfmix.experiment_identity(label)
    if state.get("uuid") != expected_uuid or state.get("name") != expected_name:
        raise wolfmix.WolfmixError("Experiment state identity mismatch")
    return root, state_file, state


def connect(port=None, timeout=8.0):
    return wolfmix.WolfmixConnection(port or wolfmix.discover_port(), timeout)


def preflight(connection):
    settings = wolfmix.decode_settings(connection.request(wolfmix.GET_SETTINGS))
    if settings["projectChanged"]:
        raise wolfmix.WolfmixError(
            "The loaded project has unsaved changes; save it on the W1 first"
        )
    if settings["lockedState"] or settings["editLockedState"]:
        raise wolfmix.WolfmixError("The controller is locked")
    return settings


def project_list(connection):
    return wolfmix.decode_item_list(connection.request(wolfmix.GET_PROJECT_LIST))


def download_project(connection, project_uuid):
    return wolfmix.fetch_project(connection, project_uuid)


def verify_project(connection, expected_uuid, expected_data):
    project = download_project(connection, expected_uuid)
    expected_records = wpjlib.Wpj.from_bytes(expected_data, "expected project").records
    downloaded_records = wpjlib.Wpj.from_bytes(
        project["data"], "downloaded project"
    ).records
    if downloaded_records != expected_records:
        raise wolfmix.ProtocolError(
            "Uploaded project records differ after download verification"
        )
    project["recordsIdentical"] = True
    return project


def snapshot_all(connection, destination, settings):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    items = project_list(connection)
    manifest = {
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "settings": settings,
        "projects": [],
    }
    for item in items:
        project = download_project(connection, item["uuid"])
        data = project.pop("data")
        output = destination / f"{item['uuid']}.wpj"
        with output.open("xb") as stream:
            stream.write(data)
        manifest["projects"].append({
            **project,
            "sha256": sha256(data),
            "file": output.name,
        })
    atomic_json(destination / "manifest.json", manifest)
    return manifest


def capture_dmx(connection):
    settings = wolfmix.decode_settings(connection.request(wolfmix.GET_SETTINGS))
    enabled_by_us = not settings["dmxUsbSendState"]
    try:
        if enabled_by_us:
            wolfmix.require_success(
                connection.request(wolfmix.ENABLE_USB_DMX), "Enabling USB DMX"
            )
        while True:
            _, _, event, payload = connection.read_frame()
            if event == wolfmix.DMX_PACKET:
                return wolfmix.decode_dmx_packet(payload)
    finally:
        if enabled_by_us:
            wolfmix.require_success(
                connection.request(wolfmix.DISABLE_USB_DMX), "Disabling USB DMX"
            )


def restart(connection):
    # The firmware resets its USB device immediately and cannot reliably return
    # a response. A successful complete write is the restart acknowledgement.
    device = os.fstat(connection.fd)
    connection.send(wolfmix.RESTART)
    return device.st_dev, device.st_ino, device.st_rdev


def device_identity(port):
    try:
        device = os.stat(port)
    except OSError:
        return None
    return device.st_dev, device.st_ino, device.st_rdev


def wait_for_controller(port, timeout=20.0, disconnected_identity=None):
    deadline = time.monotonic() + timeout
    last_error = None
    if disconnected_identity is not None:
        while time.monotonic() < deadline:
            if device_identity(port) != disconnected_identity:
                break
            time.sleep(0.05)
        else:
            raise wolfmix.WolfmixError(
                "Wolfmix USB device did not disconnect during restart"
            )
    while time.monotonic() < deadline:
        connection = None
        try:
            candidate = port if Path(port).exists() else wolfmix.discover_port()
            connection = wolfmix.WolfmixConnection(candidate, timeout=1.5)
            connection.__enter__()
            wolfmix.decode_settings(connection.request(wolfmix.GET_SETTINGS))
            return connection
        except wolfmix.WolfmixError as error:
            if connection is not None:
                connection.close()
            last_error = error
            time.sleep(0.25)
    raise wolfmix.WolfmixError(
        f"Wolfmix did not reconnect after restart: {last_error}"
    )


def restore_previous(port, label, previous, disconnected_identity=None):
    connection = wait_for_controller(
        port, disconnected_identity=disconnected_identity
    )
    restart_identity = None
    try:
        if previous is None:
            wolfmix.remove_experiment_project(connection, label)
        else:
            wolfmix.store_experiment_project(
                connection,
                label,
                previous["data"],
                version=previous["version"],
            )
            verify_project(connection, previous["uuid"], previous["data"])
        restart_identity = restart(connection)
    finally:
        connection.close()
    connection = wait_for_controller(
        port, disconnected_identity=restart_identity
    )
    try:
        if previous is None:
            if any(
                item.get("uuid") == wolfmix.experiment_identity(label)[0]
                for item in project_list(connection)
            ):
                raise wolfmix.ProtocolError(
                    "Experiment project still exists after rollback"
                )
        else:
            verify_project(connection, previous["uuid"], previous["data"])
    finally:
        connection.close()


def initialize(args):
    project_uuid, name = wolfmix.experiment_identity(args.label)
    project_path, data = validate_project(args.project, name)
    root, state_file = state_paths(args.state_dir, args.label)
    if state_file.exists():
        raise wolfmix.WolfmixError(
            f"Experiment already initialized: {state_file}"
        )
    root.mkdir(parents=True, exist_ok=True)
    previous = None
    stored_project = False
    port = args.port or wolfmix.discover_port()
    try:
        with connect(port, args.timeout) as connection:
            settings = preflight(connection)
            snapshot = snapshot_all(
                connection, root / "snapshots" / f"initial-{utc_id()}", settings
            )
            if any(item.get("uuid") == project_uuid for item in project_list(connection)):
                previous = download_project(connection, project_uuid)
            stored = wolfmix.store_experiment_project(connection, args.label, data)
            stored_project = True
            verified = verify_project(connection, project_uuid, data)
        baseline = root / "baseline.wpj"
        with baseline.open("xb") as stream:
            stream.write(data)
        state = {
            "label": args.label,
            "uuid": project_uuid,
            "name": name,
            "armed": False,
            "baseline": baseline.name,
            "baselineSha256": sha256(data),
            "source": str(project_path),
            "initializedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "controllerSerial": settings["serialNumber"],
            "firmware": settings["firmwareVer"],
            "initialSnapshotProjectCount": len(snapshot["projects"]),
        }
        atomic_json(state_file, state)
        wolfmix.print_json({
            "stored": {**stored, "sha256": sha256(verified["data"])},
            "state": str(state_file),
            "manualBootstrapRequired": (
                f"Open {name!r} once on the W1, save it without changes, "
                f"then run: wolfmix_experiment.py arm --label {args.label!r} "
                "--loaded-on-controller"
            ),
        })
    except Exception:
        if stored_project:
            try:
                restore_previous(port, args.label, previous)
            except Exception as rollback_error:
                print(f"CRITICAL: rollback failed: {rollback_error}", file=sys.stderr)
        raise


def arm(args):
    _, state_file, state = load_state(args.state_dir, args.label)
    if not args.loaded_on_controller:
        raise wolfmix.WolfmixError(
            "Arming requires --loaded-on-controller after opening the experiment "
            "project on the W1"
        )
    with connect(args.port, args.timeout) as connection:
        settings = preflight(connection)
        item = next(
            (item for item in project_list(connection) if item.get("uuid") == state["uuid"]),
            None,
        )
        if item is None or item.get("name") != state["name"]:
            raise wolfmix.WolfmixError("Experiment project is missing or renamed")
    state["armed"] = True
    state["armedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state["armedControllerMode"] = settings["wolfmixMode"]
    atomic_json(state_file, state)
    wolfmix.print_json({"armed": True, "uuid": state["uuid"], "name": state["name"]})


def deploy_one(args, candidate_path, case_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case_id):
        raise wolfmix.WolfmixError(
            "Case IDs may only contain letters, digits, dots, underscores, and hyphens"
        )
    root, _, state = load_state(args.state_dir, args.label)
    if not state.get("armed"):
        raise wolfmix.WolfmixError("Experiment is not armed; run arm first")
    path, data = validate_project(candidate_path, state["name"])
    run_dir = root / "runs" / f"{utc_id()}-{case_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    port = args.port or wolfmix.discover_port()
    previous = None
    restart_identity = None
    try:
        with connect(port, args.timeout) as connection:
            before_settings = preflight(connection)
            if before_settings["serialNumber"] != state["controllerSerial"]:
                raise wolfmix.WolfmixError("Refusing a different Wolfmix controller")
            previous = download_project(connection, state["uuid"])
            previous_data = previous["data"]
            with (run_dir / "before.wpj").open("xb") as stream:
                stream.write(previous_data)
            stored = wolfmix.store_experiment_project(connection, args.label, data)
            verified = verify_project(connection, state["uuid"], data)
            restart_identity = restart(connection)

        connection = wait_for_controller(
            port, args.restart_timeout, restart_identity
        )
        try:
            after_settings = preflight(connection)
            after = verify_project(connection, state["uuid"], data)
            dmx = capture_dmx(connection)
        finally:
            connection.close()

        with (run_dir / "candidate.wpj").open("xb") as stream:
            stream.write(data)
        with (run_dir / "dmx.bin").open("xb") as stream:
            stream.write(dmx["data"])
        journal = {
            "case": case_id,
            "source": str(path),
            "uuid": state["uuid"],
            "name": state["name"],
            "beforeSha256": sha256(previous_data),
            "candidateSha256": sha256(data),
            "downloadedSha256": sha256(after["data"]),
            "stored": stored,
            "beforeSettings": before_settings,
            "afterSettings": after_settings,
            "dmx": {
                "size": len(dmx["data"]),
                "sha256": sha256(dmx["data"]),
                "nonZeroChannels": sum(value != 0 for value in dmx["data"]),
                "unknownFrameField2": dmx["field2"],
            },
        }
        atomic_json(run_dir / "journal.json", journal)
        wolfmix.print_json({"run": str(run_dir), **journal})
        return journal
    except Exception:
        if previous is not None:
            try:
                restore_previous(
                    port, args.label, previous, restart_identity
                )
            except Exception as rollback_error:
                print(f"CRITICAL: rollback failed: {rollback_error}", file=sys.stderr)
        raise


def deploy(args):
    deploy_one(args, args.project, args.case)


def campaign(args):
    manifest_path = Path(args.manifest).resolve()
    manifest = read_json(manifest_path)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise wolfmix.WolfmixError("Campaign manifest requires a non-empty cases list")
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not case.get("id") or not case.get("project"):
            raise wolfmix.WolfmixError(f"Invalid campaign case at index {index}")
        project = (manifest_path.parent / case["project"]).resolve()
        deploy_one(args, project, case["id"])


def status(args):
    root, state_file, state = load_state(args.state_dir, args.label)
    with connect(args.port, args.timeout) as connection:
        settings = wolfmix.decode_settings(connection.request(wolfmix.GET_SETTINGS))
        item = next(
            (item for item in project_list(connection) if item.get("uuid") == state["uuid"]),
            None,
        )
    wolfmix.print_json({
        "state": str(state_file),
        "armed": state.get("armed", False),
        "controllerSettings": settings,
        "experimentProject": item,
        "baseline": str(root / state["baseline"]),
    })


def self_test(_args):
    repository = Path(__file__).resolve().parent.parent
    sample = repository / "corpus/projects/f2737ec3-c2a8-5565-a05b-10ec4c0d46d0.wpj"
    path, data = validate_project(sample)
    assert path == sample and data
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "state.json"
        value = {"sha256": sha256(data), "size": len(data)}
        atomic_json(target, value)
        assert read_json(target) == value
    experiment_uuid, name = wolfmix.experiment_identity("self-test")
    assert experiment_uuid == "d1cd1fd9-2559-5692-be1c-6526d52f3123"
    assert name.startswith(wolfmix.EXPERIMENT_NAME_PREFIX)
    print("self-test OK")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--port")
    result.add_argument("--timeout", type=float, default=8.0)
    result.add_argument("--restart-timeout", type=float, default=20.0)
    result.add_argument("--state-dir", default=DEFAULT_STATE_ROOT)
    commands = result.add_subparsers(dest="command", required=True)

    initialize_parser = commands.add_parser("init")
    initialize_parser.add_argument("project")
    initialize_parser.add_argument("--label", required=True)
    initialize_parser.set_defaults(handler=initialize)

    arm_parser = commands.add_parser("arm")
    arm_parser.add_argument("--label", required=True)
    arm_parser.add_argument("--loaded-on-controller", action="store_true")
    arm_parser.set_defaults(handler=arm)

    deploy_parser = commands.add_parser("deploy")
    deploy_parser.add_argument("project")
    deploy_parser.add_argument("--label", required=True)
    deploy_parser.add_argument("--case", required=True)
    deploy_parser.set_defaults(handler=deploy)

    campaign_parser = commands.add_parser("campaign")
    campaign_parser.add_argument("manifest")
    campaign_parser.add_argument("--label", required=True)
    campaign_parser.set_defaults(handler=campaign)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("--label", required=True)
    status_parser.set_defaults(handler=status)
    self_test_parser = commands.add_parser("self-test")
    self_test_parser.set_defaults(handler=self_test)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.timeout <= 0 or args.restart_timeout <= 0:
        raise wolfmix.WolfmixError("Timeouts must be greater than zero")
    args.handler(args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped", file=sys.stderr)
        sys.exit(130)
    except (wolfmix.WolfmixError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
