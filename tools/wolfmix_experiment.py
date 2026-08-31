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
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wolfmix_device as device
import wolfmix_protocol as protocol
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
            raise protocol.WolfmixError("Project name record 101 is not decodable")
        metadata["nom"] = project_name
        project.replace(101, wpj_codec.encode(101, metadata))
        body = project.body()
        data = hashlib.sha1(body).digest() + body
    else:
        data = path.read_bytes()
    return path, data


def warn_about_dimmers(data):
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


def state_paths(state_root, label):
    project_uuid, _ = protocol.experiment_identity(label)
    root = Path(state_root).resolve() / project_uuid
    return root, root / "state.json"


def load_state(state_root, label):
    root, state_file = state_paths(state_root, label)
    if not state_file.exists():
        raise protocol.WolfmixError(
            f"Experiment is not initialized: {label!r}; run init first"
        )
    state = read_json(state_file)
    expected_uuid, expected_name = protocol.experiment_identity(label)
    if state.get("uuid") != expected_uuid or state.get("name") != expected_name:
        raise protocol.WolfmixError("Experiment state identity mismatch")
    return root, state_file, state


def connect(port=None, timeout=8.0):
    return device.WolfmixConnection(port or device.discover_port(), timeout)


def preflight(connection):
    settings = protocol.decode_settings(connection.request(protocol.GET_SETTINGS))
    if settings["projectChanged"]:
        raise protocol.WolfmixError(
            "The loaded project has unsaved changes; save it on the W1 first"
        )
    if settings["lockedState"] or settings["editLockedState"]:
        raise protocol.WolfmixError("The controller is locked")
    return settings


def project_list(connection):
    return protocol.decode_item_list(connection.request(protocol.GET_PROJECT_LIST))


def download_project(connection, project_uuid):
    return device.fetch_project(connection, project_uuid)


def verify_project(connection, expected_uuid, expected_data):
    project = download_project(connection, expected_uuid)
    expected_records = wpjlib.Wpj.from_bytes(expected_data, "expected project").records
    downloaded_records = wpjlib.Wpj.from_bytes(
        project["data"], "downloaded project"
    ).records
    if downloaded_records != expected_records:
        raise protocol.ProtocolError(
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


def archive_manifest(item, data, filename):
    return {**item, "sha256": sha256(data), "file": filename,
            "archivedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}


def publish_archive(target, manifest_path, item, data):
    """Write the project, read it back, then publish its manifest.

    The manifest is the commit marker of the pair: a run killed before it is
    written leaves a project with no manifest, and the next run repairs that
    instead of treating the version as already archived — which is what the
    old existence check did, silently and forever.
    """
    temporary = target.with_suffix(target.suffix + ".part")
    with temporary.open("wb") as stream:      # our own scratch; a retry reuses it
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if sha256(temporary.read_bytes()) != sha256(data):
        temporary.unlink()
        raise protocol.WolfmixError(
            f"Archived project did not read back identical: {target}"
        )
    os.replace(temporary, target)
    atomic_json(manifest_path, archive_manifest(item, data, target.name))


def archive_projects(connection, root):
    """Archive every controller project we do not already hold, keyed (uuid, version).

    The snapshot taken by ``init`` is not enough: it happens once, and a project
    created after it and lost before the next ``init`` would be recoverable
    nowhere. On 2026-08-31 four projects vanished from the controller with no
    delete command and outside any run of this harness
    (``research/perte-projets-2026-08-31.md``); only the 25 August snapshot gave
    one of them back.

    Incremental because the link is slow and unreliable: the list is cheap, and
    only a version we do not already hold is downloaded. A failure here is
    **fatal** to the deploy that called it — an unarchived project is exactly
    what we cannot get back.
    """
    archive = Path(root) / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    added = []
    for item in project_list(connection):
        base = f"{item['uuid']}-{item.get('version', 0)}"
        target, manifest_path = archive / f"{base}.wpj", archive / f"{base}.json"
        if target.exists():
            data = target.read_bytes()
            if manifest_path.exists():
                if read_json(manifest_path).get("sha256") != sha256(data):
                    raise protocol.WolfmixError(
                        f"Archived project does not match its manifest: {target}"
                    )
                continue
            atomic_json(manifest_path, archive_manifest(item, data, target.name))
            added.append(target.name)
            continue
        publish_archive(target, manifest_path, item,
                        download_project(connection, item["uuid"])["data"])
        added.append(target.name)
    return added


def check_identity(settings, expected, moment):
    """Refuse a controller that is not the one this run started on."""
    for key in ("serialNumber", "firmwareVer"):
        wanted = expected.get(key)
        if wanted is not None and settings.get(key) != wanted:
            raise protocol.WolfmixError(
                f"Controller identity changed {moment}: {key} was {wanted!r}, "
                f"is now {settings.get(key)!r}"
            )
    return settings


def mark_rollback_failed(state_dir, label, error, restore):
    """A failed restore is a state, not a log line: no further deploy runs."""
    _, state_file = state_paths(state_dir, label)
    try:
        state = read_json(state_file)
    except (OSError, ValueError):
        state = {"label": label}
    state["rollbackFailed"] = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "error": str(error),
        "restore": str(restore),
    }
    atomic_json(state_file, state)
    print(
        f"CRITICAL: rollback failed: {error}\n"
        f"CRITICAL: restore {restore} on the controller, then run "
        f"clear-rollback --label {label!r}",
        file=sys.stderr,
    )


def capture_dmx(connection):
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


def restart(connection):
    # The firmware resets its USB device immediately and cannot reliably return
    # a response. A successful complete write is the restart acknowledgement.
    device = os.fstat(connection.fd)
    connection.send(protocol.RESTART)
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
        # Firmware 2.0.18 does not cycle its USB device on RESTART, so a missing
        # disconnect is normal and must not abort the run. Watching for one is
        # still worth doing: when it happens it tells us exactly when the device
        # went away, instead of racing the reconnect against a stale handle.
        grace = min(deadline, time.monotonic() + 3.0)
        while time.monotonic() < grace:
            if device_identity(port) != disconnected_identity:
                break
            time.sleep(0.05)
        else:
            print("warning: the Wolfmix stayed connected across the restart request",
                  file=sys.stderr)
    while time.monotonic() < deadline:
        connection = None
        try:
            candidate = port if Path(port).exists() else device.discover_port()
            connection = device.WolfmixConnection(candidate, timeout=1.5)
            connection.__enter__()
            protocol.decode_settings(connection.request(protocol.GET_SETTINGS))
            return connection
        except protocol.WolfmixError as error:
            if connection is not None:
                connection.close()
            last_error = error
            time.sleep(0.25)
    raise protocol.WolfmixError(
        f"Wolfmix did not reconnect after restart: {last_error}"
    )


def restore_previous(port, label, previous, disconnected_identity=None,
                     expected_identity=None):
    connection = wait_for_controller(
        port, disconnected_identity=disconnected_identity
    )
    restart_identity = None
    try:
        if expected_identity:
            check_identity(
                protocol.decode_settings(connection.request(protocol.GET_SETTINGS)),
                expected_identity, "before the rollback",
            )
        if previous is None:
            device.remove_experiment_project(connection, label)
        else:
            device.store_experiment_project(
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
        if expected_identity:
            check_identity(
                protocol.decode_settings(connection.request(protocol.GET_SETTINGS)),
                expected_identity, "after the rollback restart",
            )
        if previous is None:
            if any(
                item.get("uuid") == protocol.experiment_identity(label)[0]
                for item in project_list(connection)
            ):
                raise protocol.ProtocolError(
                    "Experiment project still exists after rollback"
                )
        else:
            verify_project(connection, previous["uuid"], previous["data"])
    finally:
        connection.close()


def record_fields(payload):
    """Top-level protobuf fields of a record, or None when it does not parse."""
    try:
        return {
            number: (value.hex(" ") if isinstance(value, bytes) else value)
            for number, _, value in protocol.protobuf_fields(payload)
        }
    except (protocol.ProtocolError, IndexError):
        return None


def describe_change(record_type, before, after):
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


def diff_projects(before, after):
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


def watch(args):
    """Report what each controller-side save changes, as it happens.

    Polls the project list, which is cheap, and downloads only when the
    experiment project's version moves. Read-only: nothing is written to the
    controller.
    """
    root, _, state = load_state(args.state_dir, args.label)
    destination = root / "watch"
    destination.mkdir(exist_ok=True)
    previous, previous_version = None, None
    print(f"Watching {state['name']}; save on the W1 to see a diff. Ctrl-C to stop.",
          file=sys.stderr)
    with connect(args.port, args.timeout) as connection:
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


def initialize(args):
    project_uuid, name = protocol.experiment_identity(args.label)
    project_path, data = validate_project(args.project, name)
    root, state_file = state_paths(args.state_dir, args.label)
    if state_file.exists():
        raise protocol.WolfmixError(
            f"Experiment already initialized: {state_file}"
        )
    root.mkdir(parents=True, exist_ok=True)
    previous = None
    stored_project = False
    port = args.port or device.discover_port()
    try:
        with connect(port, args.timeout) as connection:
            settings = preflight(connection)
            snapshot = snapshot_all(
                connection, root / "snapshots" / f"initial-{utc_id()}", settings
            )
            if any(item.get("uuid") == project_uuid for item in project_list(connection)):
                previous = download_project(connection, project_uuid)
            stored = device.store_experiment_project(connection, args.label, data)
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
                restore_previous(port, args.label, previous)
            except Exception as rollback_error:
                mark_rollback_failed(
                    args.state_dir, args.label, rollback_error,
                    "the project that held this UUID before init"
                    if previous else "nothing — delete the experiment project",
                )
        raise


def arm(args):
    _, state_file, state = load_state(args.state_dir, args.label)
    if not args.loaded_on_controller:
        raise protocol.WolfmixError(
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
            raise protocol.WolfmixError("Experiment project is missing or renamed")
    state["armed"] = True
    state["armedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state["armedControllerMode"] = settings["wolfmixMode"]
    atomic_json(state_file, state)
    protocol.print_json({"armed": True, "uuid": state["uuid"], "name": state["name"]})


def deploy_one(args, candidate_path, case_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", case_id):
        raise protocol.WolfmixError(
            "Case IDs may only contain letters, digits, dots, underscores, and hyphens"
        )
    root, _, state = load_state(args.state_dir, args.label)
    if not state.get("armed"):
        raise protocol.WolfmixError("Experiment is not armed; run arm first")
    pending = state.get("rollbackFailed")
    if pending:
        raise protocol.WolfmixError(
            f"A rollback failed on {args.label!r} at {pending.get('at')}: "
            f"{pending.get('error')}. Restore {pending.get('restore')} on the "
            f"controller, then run clear-rollback --label {args.label!r}"
        )
    path, data = validate_project(candidate_path, state["name"])
    warn_about_dimmers(data)
    run_dir = root / "runs" / f"{utc_id()}-{case_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    port = args.port or device.discover_port()
    previous = None
    restart_identity = None
    try:
        with connect(port, args.timeout) as connection:
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
            stored = device.store_experiment_project(connection, args.label, data)
            verified = verify_project(connection, state["uuid"], data)
            restart_identity = restart(connection)

        connection = wait_for_controller(
            port, args.restart_timeout, restart_identity
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
                    expected_identity=identity,
                )
            except Exception as rollback_error:
                mark_rollback_failed(args.state_dir, args.label, rollback_error,
                                     run_dir / "before.wpj")
        raise


def deploy(args):
    deploy_one(args, args.project, args.case)


def campaign(args):
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


def clear_rollback(args):
    _, state_file, state = load_state(args.state_dir, args.label)
    pending = state.pop("rollbackFailed", None)
    if pending is None:
        raise protocol.WolfmixError(f"No failed rollback on {args.label!r}")
    state["rollbackClearedAt"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat()
    atomic_json(state_file, state)
    protocol.print_json({"cleared": pending})


def status(args):
    root, state_file, state = load_state(args.state_dir, args.label)
    with connect(args.port, args.timeout) as connection:
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


def self_test(_args):
    # No project file is distributed with this repository (docs/corpus.md);
    # the file-backed half of the check runs only on a local corpus.
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
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "state.json"
            value = {"sha256": sha256(data), "size": len(data)}
            atomic_json(target, value)
            assert read_json(target) == value
    # archive_projects: incremental, transactional, and fail-closed.
    downloads = [0]
    real_list, real_download = globals()["project_list"], globals()["download_project"]
    globals()["project_list"] = lambda _c: [
        {"uuid": "a" * 8, "version": 1}, {"uuid": "b" * 8, "version": 2}]

    def _download(_c, uuid):
        downloads[0] += 1
        return {"data": b"payload-" + uuid.encode()}

    globals()["download_project"] = _download
    try:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive"
            first = archive_projects(None, directory)
            assert len(first) == 2 and downloads[0] == 2, first
            assert all((archive / name).with_suffix(".json").exists()
                       for name in first), "a project was archived with no manifest"
            assert archive_projects(None, directory) == [] and downloads[0] == 2
            # A run killed before its manifest: repaired, not skipped forever.
            orphan = archive / f"{'a' * 8}-1.json"
            orphan.unlink()
            repaired = archive_projects(None, directory)
            assert repaired == [f"{'a' * 8}-1.wpj"], repaired
            assert downloads[0] == 2, "the repair re-downloaded the project"
            assert read_json(orphan)["sha256"] == sha256(b"payload-" + b"a" * 8)
            # An archive that no longer matches its manifest stops the run.
            (archive / f"{'a' * 8}-1.wpj").write_bytes(b"tampered")
            try:
                archive_projects(None, directory)
                raise AssertionError("a corrupted archive passed")
            except protocol.WolfmixError as error:
                assert "manifest" in str(error), error
            (archive / f"{'a' * 8}-1.wpj").write_bytes(b"payload-" + b"a" * 8)
            # A fresh version of the same project is archived beside the old one.
            globals()["project_list"] = lambda _c: [{"uuid": "a" * 8, "version": 9}]
            assert archive_projects(None, directory) == [f"{'a' * 8}-9.wpj"]
            assert (archive / f"{'a' * 8}-1.wpj").exists(), "an archive was lost"
    finally:
        globals()["project_list"], globals()["download_project"] = real_list, real_download

    # The identity check refuses another controller, and says which field moved.
    reference = {"serialNumber": 1234, "firmwareVer": "2.0.18"}
    assert check_identity(dict(reference), reference, "now") == reference
    for moved in ({"serialNumber": 9, "firmwareVer": "2.0.18"},
                  {"serialNumber": 1234, "firmwareVer": "9.9.9"}):
        try:
            check_identity(moved, reference, "after the restart")
            raise AssertionError(f"identity change accepted: {moved}")
        except protocol.WolfmixError as error:
            assert "after the restart" in str(error), error

    # A failed rollback survives the process and blocks the next deploy.
    with tempfile.TemporaryDirectory() as directory:
        _, state_file = state_paths(directory, "self-test")
        atomic_json(state_file, dict(zip(("label", "uuid", "name", "armed"), (
            "self-test", *protocol.experiment_identity("self-test"), True))))
        errors = io.StringIO()
        stderr, sys.stderr = sys.stderr, errors
        try:
            mark_rollback_failed(directory, "self-test", "link died", "before.wpj")
        finally:
            sys.stderr = stderr
        assert "clear-rollback" in errors.getvalue(), errors.getvalue()
        assert read_json(state_file)["rollbackFailed"]["restore"] == "before.wpj"

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


def main(argv=None):
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
