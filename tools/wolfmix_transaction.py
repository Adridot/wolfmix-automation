#!/usr/bin/env python3
"""Persistent writing to the W1, and what makes it reversible.

Module group: Device. Reference: docs/device.md.

One route leads to the controller's projects, and it goes through here:

    identity verified
      -> transactional archive of whatever is in place
      -> upload under a **derived** UUID, never an ordinary project
      -> download again and compare record by record
      -> rollback, and if the rollback fails, a state that blocks what follows

The experiment runner and the production deployment both call this module: the
"we never write an ordinary project" guard exists once, not twice.

Fail-closed: a backup that fails stops the deployment. An unarchived project is
exactly what we cannot get back.

With no argument this file runs its self-check — it touches no device.
"""

from __future__ import annotations
from os import PathLike
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wolfmix_device as device
import wolfmix_protocol as protocol
import wpj_codec
import wpjlib


def require_managed_uuid(project_uuid: str, label: str, kind: str = 'exp') -> tuple[str, str]:
    """Refuse any UUID this repository did not derive itself.

    This is the repository's invariant, and it is checked **before** the port
    is opened: an ordinary project is never written, with or without a flag.
    """
    attendu, nom = protocol.managed_identity(label, kind)
    if project_uuid != attendu:
        raise protocol.WolfmixError(
            f"Refusing to write {project_uuid}: not a derived UUID. "
            f"{label!r} ({kind}) derives {attendu} ({nom})"
        )
    return attendu, nom


DEFAULT_STATE_ROOT = ".wolfmix-state"

def utc_id() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%S.%fZ"
    )

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def atomic_json(path: str | PathLike[str], value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)

def read_json(path: str | PathLike[str]) -> object:
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)

def validate_project(
    path: str | PathLike[str],
    project_name: str | None = None,
) -> tuple[Path, bytes]:
    path = Path(path).resolve()
    project = wpjlib.Wpj.load(path)
    if project_name is not None:
        metadata = wpj_codec.decode(101, project.get(101))
        if set(metadata) == {"raw"}:
            raise protocol.WolfmixError("Project name record 101 is not decodable")
        metadata["name"] = project_name
        project.replace(101, wpj_codec.encode(101, metadata))
        body = project.body()
        data = hashlib.sha1(body).digest() + body
    else:
        data = path.read_bytes()
    return path, data

def state_paths(
    state_root: str | PathLike[str],
    label: str,
    kind: str = 'exp',
) -> tuple[Path, Path]:
    project_uuid, _ = protocol.managed_identity(label, kind)
    root = Path(state_root).resolve() / project_uuid
    return root, root / "state.json"

def load_state(
    state_root: str | PathLike[str],
    label: str,
    kind: str = 'exp',
) -> tuple[Path, Path, dict[str, object]]:
    root, state_file = state_paths(state_root, label, kind)
    if not state_file.exists():
        raise protocol.WolfmixError(
            f"Experiment is not initialized: {label!r}; run init first"
        )
    state = read_json(state_file)
    expected_uuid, expected_name = protocol.managed_identity(
        label, state.get("namespace", kind))
    if state.get("uuid") != expected_uuid or state.get("name") != expected_name:
        raise protocol.WolfmixError("Experiment state identity mismatch")
    return root, state_file, state

def connect(
    port: str | None = None,
    timeout: float = 8.0,
    allow_untested_firmware: bool = False,
) -> device.WolfmixConnection:
    """The same gate as `wolfmix.py`: a firmware this repository has never
    measured refuses every state change unless the caller says so."""
    return device.WolfmixConnection(port or device.discover_port(), timeout,
                                    allow_untested_firmware=allow_untested_firmware)

def preflight(connection: device.WolfmixConnection) -> dict[str, object]:
    settings = protocol.decode_settings(connection.request(protocol.GET_SETTINGS))
    if settings["projectChanged"]:
        raise protocol.WolfmixError(
            "The loaded project has unsaved changes; save it on the W1 first"
        )
    if settings["lockedState"] or settings["editLockedState"]:
        raise protocol.WolfmixError("The controller is locked")
    return settings

def project_list(connection: device.WolfmixConnection) -> list[dict[str, object]]:
    return protocol.decode_item_list(connection.request(protocol.GET_PROJECT_LIST))

def download_project(connection: device.WolfmixConnection, project_uuid: str) -> dict[str, object]:
    return device.fetch_project(connection, project_uuid)

def verify_project(
    connection: device.WolfmixConnection,
    expected_uuid: str,
    expected_data: bytes,
) -> dict[str, object]:
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

def snapshot_all(
    connection: device.WolfmixConnection,
    destination: str | PathLike[str],
    settings: dict[str, object],
) -> dict[str, object]:
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

def archive_manifest(item: dict[str, object], data: bytes, filename: str) -> dict[str, object]:
    return {**item, "sha256": sha256(data), "file": filename,
            "archivedAt": datetime.datetime.now(datetime.timezone.utc).isoformat()}

def publish_archive(
    target: str | PathLike[str],
    manifest_path: str | PathLike[str],
    item: dict[str, object],
    data: bytes,
) -> None:
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

def archive_projects(connection: device.WolfmixConnection, root: str | PathLike[str]) -> list[str]:
    """Archive every controller project we do not already hold, keyed (uuid, version).

    The snapshot taken by ``init`` is not enough: it happens once, and a project
    created after it and lost before the next ``init`` would be recoverable
    nowhere. On 2026-08-31 four projects vanished from the controller with no
    delete command and outside any run of this harness
    (``research/evidence.md``, LOSS-01); only the 25 August snapshot gave
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

def check_identity(
    settings: dict[str, object],
    expected: dict[str, object],
    moment: str,
) -> dict[str, object]:
    """Refuse a controller that is not the one this run started on."""
    for key in ("serialNumber", "firmwareVer"):
        wanted = expected.get(key)
        if wanted is not None and settings.get(key) != wanted:
            raise protocol.WolfmixError(
                f"Controller identity changed {moment}: {key} was {wanted!r}, "
                f"is now {settings.get(key)!r}"
            )
    return settings

def mark_rollback_failed(
    state_dir: str | PathLike[str],
    label: str,
    error: Exception | str,
    restore: str | PathLike[str],
    kind: str = 'exp',
) -> None:
    """A failed restore is a state, not a log line: no further deploy runs."""
    _, state_file = state_paths(state_dir, label, kind)
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

def restart(connection: device.WolfmixConnection) -> tuple[int, int, int]:
    device = os.fstat(connection.fd)
    connection.send(protocol.RESTART)
    return device.st_dev, device.st_ino, device.st_rdev

def device_identity(port: str) -> tuple[int, int, int] | None:
    try:
        device = os.stat(port)
    except OSError:
        return None
    return device.st_dev, device.st_ino, device.st_rdev

def wait_for_controller(
    port: str,
    timeout: float = 20.0,
    disconnected_identity: tuple[int, int, int] | None = None,
    allow_untested_firmware: bool = False,
) -> device.WolfmixConnection:
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
            connection = device.WolfmixConnection(
                candidate, timeout=1.5,
                allow_untested_firmware=allow_untested_firmware)
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

def restore_previous(
    port: str,
    label: str,
    previous: dict[str, object] | None,
    disconnected_identity: tuple[int, int, int] | None = None,
    expected_identity: dict[str, object] | None = None,
    kind: str = 'exp',
    allow_untested_firmware: bool = False,
) -> None:
    connection = wait_for_controller(
        port, disconnected_identity=disconnected_identity,
        allow_untested_firmware=allow_untested_firmware,
    )
    restart_identity = None
    try:
        if expected_identity:
            check_identity(
                protocol.decode_settings(connection.request(protocol.GET_SETTINGS)),
                expected_identity, "before the rollback",
            )
        if previous is None:
            device.remove_managed_project(connection, label, kind=kind)
        else:
            device.store_managed_project(
                connection,
                label,
                previous["data"],
                version=previous["version"],
                kind=kind,
            )
            verify_project(connection, previous["uuid"], previous["data"])
        restart_identity = restart(connection)
    finally:
        connection.close()
    connection = wait_for_controller(
        port, disconnected_identity=restart_identity,
        allow_untested_firmware=allow_untested_firmware,
    )
    try:
        if expected_identity:
            check_identity(
                protocol.decode_settings(connection.request(protocol.GET_SETTINGS)),
                expected_identity, "after the rollback restart",
            )
        if previous is None:
            if any(
                item.get("uuid") == protocol.managed_identity(label, kind)[0]
                for item in project_list(connection)
            ):
                raise protocol.ProtocolError(
                    "Experiment project still exists after rollback"
                )
        else:
            verify_project(connection, previous["uuid"], previous["data"])
    finally:
        connection.close()

def self_check() -> None:
    """No device: a fake link, temporary directories, and refusals."""
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

    # The derived-UUID guard: it refuses before a port is even opened.
    derive, nom = protocol.managed_identity("self-test", "exp")
    assert require_managed_uuid(derive, "self-test", "exp") == (derive, nom)
    auto, nom_auto = protocol.managed_identity("self-test", "auto")
    assert auto != derive and nom_auto.startswith("WMX AUTO ")
    for etranger in ("11111111-2222-3333-4444-555555555555", auto):
        try:
            require_managed_uuid(etranger, "self-test", "exp")
            raise AssertionError(f"UUID accepte : {etranger}")
        except protocol.WolfmixError as erreur:
            assert "not a derived UUID" in str(erreur), erreur

    print("self-check ok: transactional archive, identity, rollback, and "
          "the derived UUID as the only target")


if __name__ == "__main__":
    self_check()
