"""The deploy boundary: the archive is a transaction, and a failed rollback is
a state on disk that stops the next run rather than a line in a log."""
from collections.abc import Callable, Iterator, Sequence

import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

import wolfmix_experiment
import wolfmix_protocol as protocol
import wolfmix_transaction as tx


@contextlib.contextmanager
def fake_link(
    projects: Sequence[dict[str, object]], downloads: Callable[[str], bytes],
) -> Iterator[None]:
    """Replace the two module-level calls that touch the controller."""
    real = tx.project_list, tx.download_project
    tx.project_list = lambda _c: list(projects)
    tx.download_project = lambda _c, uuid: {"data": downloads(uuid)}
    try:
        yield
    finally:
        tx.project_list, tx.download_project = real


class ArchiveIsATransaction(unittest.TestCase):
    """The manifest is the commit marker of the pair. A run killed before it
    is written leaves a project with no manifest — and the next run repairs
    that instead of treating the version as archived forever."""

    def setUp(self) -> None:
        self.calls = []
        self.projects = [{"uuid": "a" * 8, "version": 1},
                         {"uuid": "b" * 8, "version": 2}]

    def _download(self, uuid):
        self.calls.append(uuid)
        return b"payload-" + uuid.encode()

    def test_a_project_is_never_archived_without_its_manifest(self) -> None:
        with fake_link(self.projects, self._download), \
                tempfile.TemporaryDirectory() as directory:
            added = tx.archive_projects(None, directory)
            archive = Path(directory) / "archive"
            self.assertEqual(len(added), 2)
            for name in added:
                self.assertTrue((archive / name).with_suffix(".json").exists())

    def test_a_manifestless_archive_is_repaired_without_downloading_again(self) -> None:
        with fake_link(self.projects, self._download), \
                tempfile.TemporaryDirectory() as directory:
            tx.archive_projects(None, directory)
            archive = Path(directory) / "archive"
            orphan = archive / f"{'a' * 8}-1.json"
            orphan.unlink()
            repaired = tx.archive_projects(None, directory)
            self.assertEqual(repaired, [f"{'a' * 8}-1.wpj"])
            self.assertEqual(len(self.calls), 2, "the repair re-downloaded")
            self.assertEqual(tx.read_json(orphan)["sha256"],
                             tx.sha256(b"payload-" + b"a" * 8))

    def test_an_archive_that_no_longer_matches_its_manifest_stops_the_run(self) -> None:
        with fake_link(self.projects, self._download), \
                tempfile.TemporaryDirectory() as directory:
            tx.archive_projects(None, directory)
            target = Path(directory) / "archive" / f"{'a' * 8}-1.wpj"
            target.write_bytes(b"tampered")
            with self.assertRaises(protocol.WolfmixError) as caught:
                tx.archive_projects(None, directory)
            self.assertIn("manifest", str(caught.exception))

    def test_a_new_version_is_archived_beside_the_old_one(self) -> None:
        with fake_link(self.projects, self._download), \
                tempfile.TemporaryDirectory() as directory:
            tx.archive_projects(None, directory)
            with fake_link([{"uuid": "a" * 8, "version": 9}], self._download):
                self.assertEqual(tx.archive_projects(None, directory),
                                 [f"{'a' * 8}-9.wpj"])
            self.assertTrue(
                (Path(directory) / "archive" / f"{'a' * 8}-1.wpj").exists())


class FailedRollback(unittest.TestCase):
    """A restore that did not happen is not a warning: it is a lock."""

    def _armed_state(self, directory, label="boundary"):
        uuid, name = protocol.managed_identity(label, "exp")
        _, state_file = tx.state_paths(directory, label)
        tx.atomic_json(state_file, {"label": label, "uuid": uuid, "name": name,
                                    "armed": True, "namespace": "exp",
                                    "controllerSerial": 1234,
                                    "firmware": protocol.TESTED_FIRMWARE[0]})
        return state_file

    def test_the_failure_is_written_and_names_the_way_out(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_file = self._armed_state(directory)
            errors = io.StringIO()
            stderr, sys.stderr = sys.stderr, errors
            try:
                tx.mark_rollback_failed(directory, "boundary", "link died",
                                        "before.wpj")
            finally:
                sys.stderr = stderr
            self.assertIn("clear-rollback", errors.getvalue())
            pending = tx.read_json(state_file)["rollbackFailed"]
            self.assertEqual(pending["restore"], "before.wpj")

    def test_the_next_deploy_refuses_and_names_the_archive_to_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self._armed_state(directory)
            with open("/dev/null", "w") as sink, contextlib.redirect_stderr(sink):
                tx.mark_rollback_failed(directory, "boundary", "link died",
                                        "before.wpj")
            args = argparse.Namespace(state_dir=directory, label="boundary",
                                      namespace="exp", port=None, timeout=1.0)
            with self.assertRaises(protocol.WolfmixError) as caught:
                wolfmix_experiment.deploy_one(args, "unused.wpj", "case1")
            message = str(caught.exception)
            self.assertIn("before.wpj", message)
            self.assertIn("clear-rollback", message)

    def test_a_clean_state_does_not_refuse_for_that_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self._armed_state(directory)
            args = argparse.Namespace(state_dir=directory, label="boundary",
                                      namespace="exp", port=None, timeout=1.0)
            with self.assertRaises(Exception) as caught:
                wolfmix_experiment.deploy_one(args, "absent.wpj", "case1")
            self.assertNotIn("rollback", str(caught.exception).lower())


class DerivedUuidOnly(unittest.TestCase):
    """The repository's non-negotiable invariant, checked before a port is
    opened: an ordinary project is never written, with or without a flag."""

    def test_the_derived_uuid_is_accepted(self) -> None:
        expected, name = protocol.managed_identity("boundary", "exp")
        self.assertEqual(tx.require_managed_uuid(expected, "boundary", "exp"),
                         (expected, name))

    def test_a_foreign_uuid_is_refused(self) -> None:
        for foreign in ("11111111-2222-3333-4444-555555555555",
                        protocol.managed_identity("boundary", "auto")[0]):
            with self.assertRaises(protocol.WolfmixError) as caught:
                tx.require_managed_uuid(foreign, "boundary", "exp")
            self.assertIn("not a derived UUID", str(caught.exception))

    def test_the_two_namespaces_never_collide(self) -> None:
        exp, exp_name = protocol.managed_identity("boundary", "exp")
        auto, auto_name = protocol.managed_identity("boundary", "auto")
        self.assertNotEqual(exp, auto)
        self.assertTrue(auto_name.startswith("WMX AUTO "))
        self.assertTrue(exp_name.startswith("WMX EXP "))
        self.assertLessEqual(len(auto_name), protocol.PROJECT_NAME_MAX)


if __name__ == "__main__":
    unittest.main()
