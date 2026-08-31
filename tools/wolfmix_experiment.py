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


def archive_projects(connection, root):
    """Archive tout projet du contrôleur qu'on n'a pas déjà, clé (uuid, version).

    L'instantané d'`init` ne suffit pas : il est pris une fois, et un projet
    créé après lui puis perdu avant le prochain `init` ne serait récupérable
    nulle part. Le 2026-08-31, quatre projets ont disparu du contrôleur sans
    commande de suppression et hors de toute exécution du harnais
    (`research/perte-projets-2026-08-31.md`) ; seul l'instantané du 25 août a
    permis d'en rendre un.

    Incrémental parce que le lien est lent et faillible : la liste est bon
    marché, et on ne retélécharge que ce dont on n'a pas déjà la version. Un
    échec d'archivage ne fait pas échouer le déploiement — mieux vaut une
    archive incomplète qu'un déploiement bloqué.
    """
    archive = Path(root) / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    ajoutes = []
    for item in project_list(connection):
        base = f"{item['uuid']}-{item.get('version', 0)}"
        cible = archive / f"{base}.wpj"
        if cible.exists():
            continue
        data = download_project(connection, item["uuid"])["data"]
        with cible.open("xb") as stream:
            stream.write(data)
        atomic_json(archive / f"{base}.json",
                    {**item, "sha256": sha256(data), "file": cible.name,
                     "archivedAt": datetime.datetime.now(
                         datetime.timezone.utc).isoformat()})
        ajoutes.append(cible.name)
    return ajoutes


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


def record_fields(payload):
    """Top-level protobuf fields of a record, or None when it does not parse."""
    try:
        return {
            number: (value.hex(" ") if isinstance(value, bytes) else value)
            for number, _, value in wolfmix.protobuf_fields(payload)
        }
    except (wolfmix.ProtocolError, IndexError):
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
                raise wolfmix.WolfmixError("Experiment project is no longer on the W1")
            if item["version"] != previous_version:
                data = download_project(connection, state["uuid"])["data"]
                current = wpjlib.Wpj.from_bytes(data, "downloaded project")
                snapshot = destination / f"{item['version']}.wpj"
                if not snapshot.exists():
                    snapshot.write_bytes(data)
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
    warn_about_dimmers(data)
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
            try:
                ajoutes = archive_projects(connection, root)
                if ajoutes:
                    print(f"archive : {len(ajoutes)} projet(s) sauvegardes",
                          file=sys.stderr)
            except Exception as error:            # jamais bloquant
                print(f"warning: archivage impossible ({error})", file=sys.stderr)
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
    # archive_projects : incrémental, et un échec de téléchargement n'avale pas
    # les projets déjà archivés.
    class FauxLien:
        def __init__(self): self.telecharges = 0
    faux = FauxLien()
    vrai_liste, vrai_dl = globals()["project_list"], globals()["download_project"]
    globals()["project_list"] = lambda _c: [
        {"uuid": "a" * 8, "version": 1}, {"uuid": "b" * 8, "version": 2}]
    def _dl(_c, uuid):
        faux.telecharges += 1
        return {"data": b"charge-" + uuid.encode()}
    globals()["download_project"] = _dl
    try:
        with tempfile.TemporaryDirectory() as directory:
            premier = archive_projects(None, directory)
            assert len(premier) == 2 and faux.telecharges == 2, premier
            second = archive_projects(None, directory)
            assert second == [] and faux.telecharges == 2, second
            # une version neuve du même projet est archivée à part
            globals()["project_list"] = lambda _c: [{"uuid": "a" * 8, "version": 9}]
            troisieme = archive_projects(None, directory)
            assert troisieme == [f"{'a' * 8}-9.wpj"], troisieme
            garde = Path(directory) / "archive" / f"{'a' * 8}-1.wpj"
            assert garde.exists(), "l'archive precedente a ete perdue"
    finally:
        globals()["project_list"], globals()["download_project"] = vrai_liste, vrai_dl

    changes = describe_change(102, bytes.fromhex("2802"), bytes.fromhex("2803"))
    assert changes == ["  type 102 field 5: 2 -> 3"], changes
    appeared = describe_change(102, b"", bytes.fromhex("2807"))
    assert appeared == ["  type 102 field 5: absent -> 7"], appeared
    opaque = describe_change(99, b"\xff\x00", b"\xff\x01")
    assert opaque == ["  type 99: byte 1 00->01"], opaque
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

    watch_parser = commands.add_parser("watch")
    watch_parser.add_argument("--label", required=True)
    watch_parser.add_argument("--interval", type=float, default=1.0,
                              help="project-list polling period in seconds")
    watch_parser.set_defaults(handler=watch)

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
