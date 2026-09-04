#!/usr/bin/env python3
"""Campaigns and experiments on a W1, without WTOOLS.

Module group: Device. Reference: docs/device.md.

This runner does one thing the production client does not: reproducible
campaigns — one case, one deployment, one DMX capture, one journal entry.
Everything about persistent writing (identity, archive, verified upload,
rollback) lives in `wolfmix_transaction.py` and is shared.

One manual bootstrap remains: firmware 2.0.18 exposes no USB command for
selecting a project. Run `init`, open the resulting `WMX EXP ...` project once
on the W1, then run `arm`. Everything after that is automatic.
"""

from __future__ import annotations
from os import PathLike
import wolfmix_device as device
import argparse
import datetime
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wolfmix_device as device
import wolfmix_protocol as protocol
import wolfmix_transaction as tx
import wpj_codec
import wpjlib

from wolfmix_transaction import (
    DEFAULT_STATE_ROOT, archive_projects, atomic_json, check_identity, connect,
    download_project, load_state, mark_rollback_failed, preflight,
    project_list, read_json, restore_previous, sha256, snapshot_all,
    state_paths, utc_id, validate_project, verify_project, wait_for_controller,
    restart,
)

def warn_about_dimmers(data: bytes) -> None:
    """A preset that writes group dimmers is inert unless the controller's
    Settings menu has ``store group dimmers in preset`` ON (GEN-02). That
    condition lives in the device, not in the project, so a perfectly
    compiled show can do nothing at all — and the Settings message we read
    does not carry the flag. Say so rather than let it fail silently."""
    try:
        presets = wpj_codec.decode(165, wpjlib.Wpj.from_bytes(data).get(165))
    except Exception:
        return                      # no record 165, or no schema: nothing to say
    entries = [p for p in presets.get("presets", ()) if isinstance(p, dict)]
    with_dimmers = sum(1 for p in entries if any(p.get("dimmers") or ()))
    if with_dimmers:
        print(f"warning: {with_dimmers}/{len(entries)} presets write group "
              "dimmers; those values stay inert unless the panel's "
              "Settings > store group dimmers in preset is ON (GEN-02) — "
              "the condition lives in the device, not in the project",
              file=sys.stderr)

def capture_dmx(connection: device.WolfmixConnection) -> dict[str, object]:
    settings = protocol.decode_settings(connection.request(protocol.GET_SETTINGS))
    enabled_by_us = not settings["dmxUsbSendState"]
    try:
        if enabled_by_us:
            device.require_success(
                connection.request(protocol.ENABLE_USB_DMX), "Enabling USB DMX"
            )
        while True:
            _, _, event, payload = connection.read_frame()
            if event == protocol.DMX_PACKET:
                return protocol.decode_dmx_packet(payload)
    finally:
        if enabled_by_us:
            device.require_success(
                connection.request(protocol.DISABLE_USB_DMX), "Disabling USB DMX"
            )

def record_fields(payload: bytes) -> dict[int, int | str] | None:
    """Top-level protobuf fields of a record, or None when it does not parse."""
    try:
        return {
            number: (value.hex(" ") if isinstance(value, bytes) else value)
            for number, _, value in protocol.protobuf_fields(payload)
        }
    except (protocol.ProtocolError, IndexError):
        return None

def describe_change(record_type: int, before: bytes, after: bytes) -> list[str]:
    """One human-readable line per changed field, or per changed byte."""
    lines = []
    old_fields, new_fields = record_fields(before), record_fields(after)
    if old_fields is not None and new_fields is not None:
        for number in sorted(set(old_fields) | set(new_fields)):
            old = old_fields.get(number)
            new = new_fields.get(number)
            if old != new:
                lines.append(
                    f"  type {record_type} field {number}: "
                    f"{'absent' if old is None else old} -> "
                    f"{'absent' if new is None else new}"
                )
    if lines:
        return lines
    if len(before) == len(after):
        changed = [
            f"byte {i} {x:02x}->{y:02x}"
            for i, (x, y) in enumerate(zip(before, after)) if x != y
        ]
        return [f"  type {record_type}: " + ", ".join(changed[:12])]
    return [f"  type {record_type}: {len(before)} -> {len(after)} bytes"]

def diff_projects(before: bytes, after: bytes) -> list[str]:
    lines = []
    if before.prefix != after.prefix:
        # Prefix bytes 20..27 are the uint64 project version, already reported
        # in the header line; showing its low byte as a diff is pure noise.
        lines += [
            f"  prefix byte {i} {x:02x}->{y:02x}"
            for i, (x, y) in enumerate(zip(before.prefix, after.prefix))
            if x != y and not 20 <= i < 28
        ]
    if [t for t, _ in before.records] != [t for t, _ in after.records]:
        lines.append("  record layout changed")
        return lines
    for (record_type, old), (_, new) in zip(before.records, after.records):
        if old != new:
            lines += describe_change(record_type, old, new)
    return lines

def watch(args: argparse.Namespace) -> None:
    """Report what each controller-side save changes, as it happens.

    Polls the project list, which is cheap, and downloads only when the
    experiment project's version moves. Read-only: nothing is written to the
    controller.
    """
    root, _, state = load_state(args.state_dir, args.label, args.namespace)
    destination = root / "watch"
    destination.mkdir(exist_ok=True)
    previous, previous_version = None, None
    print(f"Watching {state['name']}; save on the W1 to see a diff. Ctrl-C to stop.",
          file=sys.stderr)
    with connect(args.port, args.timeout, args.allow_untested_firmware) as connection:
        while True:
            item = next(
                (i for i in project_list(connection) if i.get("uuid") == state["uuid"]),
                None,
            )
            if item is None:
                raise protocol.WolfmixError("Experiment project is no longer on the W1")
            if item["version"] != previous_version:
                data = download_project(connection, state["uuid"])["data"]
                current = wpjlib.Wpj.from_bytes(data, "downloaded project")
                snapshot = destination / f"{item['version']}.wpj"
                try:
                    with snapshot.open("xb") as stream:
                        stream.write(data)
                except FileExistsError:
                    pass                      # this version is already captured
                if previous is None:
                    print(f"baseline version {item['version']} ({len(data)} bytes)")
                else:
                    lines = diff_projects(previous, current)
                    print(f"version {previous_version} -> {item['version']}")
                    print("\n".join(lines) if lines else "  no record changed")
                sys.stdout.flush()
                previous, previous_version = current, item["version"]
            time.sleep(args.interval)

def initialize(args: argparse.Namespace) -> None:
    project_uuid, name = protocol.managed_identity(args.label, args.namespace)
    # Before the port is opened: is the target a UUID we derive ourselves?
    tx.require_managed_uuid(project_uuid, args.label, args.namespace)
    project_path, data = validate_project(args.project, name)
    root, state_file = state_paths(args.state_dir, args.label, args.namespace)
    if state_file.exists():
        raise protocol.WolfmixError(
            f"Experiment already initialized: {state_file}"
        )
    root.mkdir(parents=True, exist_ok=True)
    previous = None
    stored_project = False
    port = args.port or device.discover_port()
    try:
        with connect(port, args.timeout, args.allow_untested_firmware) as connection:
            settings = preflight(connection)
            snapshot = snapshot_all(
                connection, root / "snapshots" / f"initial-{utc_id()}", settings
            )
            if any(item.get("uuid") == project_uuid for item in project_list(connection)):
                previous = download_project(connection, project_uuid)
            stored = device.store_managed_project(connection, args.label, data,
                                                  kind=args.namespace)
            stored_project = True
            verified = verify_project(connection, project_uuid, data)
        baseline = root / "baseline.wpj"
        with baseline.open("xb") as stream:
            stream.write(data)
        state = {
            "label": args.label,
            "namespace": args.namespace,
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
        protocol.print_json({
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
                restore_previous(port, args.label, previous,
                                 kind=args.namespace,
                                 allow_untested_firmware=args.allow_untested_firmware)
            except Exception as rollback_error:
                mark_rollback_failed(
                    args.state_dir, args.label, rollback_error,
                    "the project that held this UUID before init"
                    if previous else "nothing — delete the managed project",
                    args.namespace,
                )
        raise


def arm(args: argparse.Namespace) -> None:
    _, state_file, state = load_state(args.state_dir, args.label, args.namespace)
    if not args.loaded_on_controller:
        raise protocol.WolfmixError(
            "Arming requires --loaded-on-controller after opening the experiment "
            "project on the W1"
        )
    with connect(args.port, args.timeout, args.allow_untested_firmware) as connection:
        settings = preflight(connection)
        item = next(
            (item for item in project_list(connection) if item.get("uuid") == state["uuid"]),
            None,
        )
        if item is None or item.get("name") != state["name"]:
            raise protocol.WolfmixError("Experiment project is missing or renamed")
    state["armed"] = True
    state["armedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state["armedControllerMode"] = settings["wolfmixMode"]
    atomic_json(state_file, state)
    protocol.print_json({"armed": True, "uuid": state["uuid"], "name": state["name"]})

def deploy_one(
    args: argparse.Namespace,
    candidate_path: str | PathLike[str],
    case_id: str,
) -> dict[str, object]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case_id):
        raise protocol.WolfmixError(
            "Case IDs may only contain letters, digits, dots, underscores, and hyphens"
        )
    root, _, state = load_state(args.state_dir, args.label, args.namespace)
    if not state.get("armed"):
        raise protocol.WolfmixError("Experiment is not armed; run arm first")
    pending = state.get("rollbackFailed")
    if pending:
        raise protocol.WolfmixError(
            f"A rollback failed on {args.label!r} at {pending.get('at')}: "
            f"{pending.get('error')}. Restore {pending.get('restore')} on the "
            f"controller, then run clear-rollback --label {args.label!r}"
        )
    # Before any port: is the target a UUID we derive ourselves?
    tx.require_managed_uuid(state["uuid"], args.label,
                            state.get("namespace", args.namespace))
    path, data = validate_project(candidate_path, state["name"])
    warn_about_dimmers(data)
    run_dir = root / "runs" / f"{utc_id()}-{case_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    port = args.port or device.discover_port()
    previous = None
    restart_identity = None
    try:
        with connect(port, args.timeout, args.allow_untested_firmware) as connection:
            before_settings = preflight(connection)
            identity = {"serialNumber": state["controllerSerial"],
                        "firmwareVer": state.get("firmware")}
            check_identity(before_settings, identity, "since init")
            # Fail-closed: an unarchived project is what we cannot get back,
            # so a failure here stops the run before anything is uploaded — and
            # says which step failed rather than leaking a bare OSError.
            try:
                archived = archive_projects(connection, root)
            except (OSError, protocol.WolfmixError) as error:
                raise protocol.WolfmixError(
                    f"Pre-deploy archive failed, nothing was uploaded: {error}"
                ) from error
            if archived:
                print(f"archive: {len(archived)} project(s) saved", file=sys.stderr)
            previous = download_project(connection, state["uuid"])
            previous_data = previous["data"]
            with (run_dir / "before.wpj").open("xb") as stream:
                stream.write(previous_data)
            stored = device.store_managed_project(connection, args.label, data,
                                                  kind=args.namespace)
            verified = verify_project(connection, state["uuid"], data)
            restart_identity = restart(connection)

        connection = wait_for_controller(
            port, args.restart_timeout, restart_identity,
            allow_untested_firmware=args.allow_untested_firmware,
        )
        try:
            after_settings = check_identity(
                preflight(connection), identity, "after the restart"
            )
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
        protocol.print_json({"run": str(run_dir), **journal})
        return journal
    except Exception:
        if previous is not None:
            try:
                restore_previous(
                    port, args.label, previous, restart_identity,
                    expected_identity=identity, kind=args.namespace,
                    allow_untested_firmware=args.allow_untested_firmware,
                )
            except Exception as rollback_error:
                mark_rollback_failed(args.state_dir, args.label, rollback_error,
                                     run_dir / "before.wpj", args.namespace)
        raise

def deploy(args: argparse.Namespace) -> None:
    deploy_one(args, args.project, args.case)

def campaign(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest).resolve()
    manifest = read_json(manifest_path)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise protocol.WolfmixError("Campaign manifest requires a non-empty cases list")
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not case.get("id") or not case.get("project"):
            raise protocol.WolfmixError(f"Invalid campaign case at index {index}")
        project = (manifest_path.parent / case["project"]).resolve()
        deploy_one(args, project, case["id"])

def clear_rollback(args: argparse.Namespace) -> None:
    _, state_file, state = load_state(args.state_dir, args.label, args.namespace)
    pending = state.pop("rollbackFailed", None)
    if pending is None:
        raise protocol.WolfmixError(f"No failed rollback on {args.label!r}")
    state["rollbackClearedAt"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()
    atomic_json(state_file, state)
    protocol.print_json({"cleared": pending})

def status(args: argparse.Namespace) -> None:
    root, state_file, state = load_state(args.state_dir, args.label, args.namespace)
    with connect(args.port, args.timeout, args.allow_untested_firmware) as connection:
        settings = protocol.decode_settings(connection.request(protocol.GET_SETTINGS))
        item = next(
            (item for item in project_list(connection) if item.get("uuid") == state["uuid"]),
            None,
        )
    protocol.print_json({
        "state": str(state_file),
        "armed": state.get("armed", False),
        "rollbackFailed": state.get("rollbackFailed"),
        "controllerSettings": settings,
        "experimentProject": item,
        "baseline": str(root / state["baseline"]),
    })

def self_test(_args: argparse.Namespace | None) -> None:
    sample = next(iter(wpjlib.corpus_files()), None)
    if sample is None:
        wpjlib.pas_de_corpus("wolfmix_experiment")
    else:
        path, data = validate_project(Path(sample))
        assert path == Path(sample).resolve() and data
        warned = io.StringIO()
        stderr, sys.stderr = sys.stderr, warned
        try:
            warn_about_dimmers(data)          # a real project: says something
            spoken = warned.getvalue()
            warn_about_dimmers(b"not a project")   # garbage: stays quiet
        finally:
            sys.stderr = stderr
        assert "store group dimmers" in spoken, spoken
        assert warned.getvalue() == spoken, "warned on a non-project"
    changes = describe_change(102, bytes.fromhex("2802"), bytes.fromhex("2803"))
    assert changes == ["  type 102 field 5: 2 -> 3"], changes
    appeared = describe_change(102, b"", bytes.fromhex("2807"))
    assert appeared == ["  type 102 field 5: absent -> 7"], appeared
    opaque = describe_change(99, b"\xff\x00", b"\xff\x01")
    assert opaque == ["  type 99: byte 1 00->01"], opaque
    experiment_uuid, name = protocol.experiment_identity("self-test")
    assert experiment_uuid == "d1cd1fd9-2559-5692-be1c-6526d52f3123"
    assert name.startswith(protocol.EXPERIMENT_NAME_PREFIX)
    print("self-test OK")

def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--port")
    result.add_argument("--allow-untested-firmware", action="store_true",
                        help="allow state changes on a firmware this repository "
                             "has never measured (PATCH-02 met 2.0.19); the "
                             "refusal is the default, as in wolfmix.py")
    result.add_argument("--timeout", type=float, default=8.0)
    result.add_argument("--restart-timeout", type=float, default=20.0)
    result.add_argument("--state-dir", default=DEFAULT_STATE_ROOT)
    result.add_argument("--namespace", choices=sorted(protocol.MANAGED_PREFIXES),
                        default="exp",
                        help="managed namespace: 'exp' for a campaign, "
                             "'auto' for a backed-up, transactional production "
                             "deployment (default: exp)")
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

    watch_parser = commands.add_parser("watch")
    watch_parser.add_argument("--label", required=True)
    watch_parser.add_argument("--interval", type=float, default=1.0,
                              help="project-list polling period in seconds")
    watch_parser.set_defaults(handler=watch)

    clear_parser = commands.add_parser(
        "clear-rollback",
        help="clear a failed-rollback state once the project is restored",
    )
    clear_parser.add_argument("--label", required=True)
    clear_parser.set_defaults(handler=clear_rollback)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("--label", required=True)
    status_parser.set_defaults(handler=status)
    self_test_parser = commands.add_parser("self-test")
    self_test_parser.set_defaults(handler=self_test)
    return result

def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.timeout <= 0 or args.restart_timeout <= 0:
        raise protocol.WolfmixError("Timeouts must be greater than zero")
    args.handler(args)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped", file=sys.stderr)
        sys.exit(130)
    except (protocol.WolfmixError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(2)
