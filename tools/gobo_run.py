#!/usr/bin/env python3
"""The gobo job, guided: where the working directory stands, and what is next.

Module group: Resources. Reference: docs/tools.md.

The six steps of `docs/gobo-icons.md` each belong to a tool of this repository.
What belonged to nobody were the gates *between* them — and on real hardware a
skipped step is expensive. This tool patches nothing, talks to no device and
writes no file: it reads a working directory and refuses to name the next step
while a gate is red. Its `upload_plan` function is the final local proof used
by `wolfmix.py` before the device port opens.

  gobo_run.py DIRECTORY   the state of the job, then the next command
  gobo_run.py             self-check

Four gates, the ones no tool was holding:

  0 backup        the flash bundle copied OUTSIDE the WTOOLS folder — which
                  WTOOLS rewrites on every update — SHA-256 equal to the live
                  one, AND the live one checked against the manifest it ships
                  with: a faithful copy of a bundle that is not the vendor's
                  image is a copy of whatever was there
  1 silhouettes   at least one `gobo*.png` in the directory
  2 patched flash present, the original's length — the table's pointers are
                  absolute — and tied by its manifest to the installed bundle:
                  length alone let any file of the same size through
  3 sheet         rendered AFTER the patched flash, therefore read back from it
                  and not from the sources — the only proof before an upload

The rest is already refused by the tool that owns it: `Open` and its 96 entries
by `gobo_write.py`, names over 19 bytes and a wheel carried by a second group by
`wpj_show.py`. Nothing is recomputed here; things are put in order.

Exit 2 = a red gate, the next step is refused. The working directory is the
operator's: silhouettes, patched flash and contact sheet are their fixture's
data and never enter this repository (LEGAL.md) — a directory under the
repository tree is refused.
"""

from __future__ import annotations
from os import PathLike
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gobo_library import ICON, Library, find_flash
import gobo_write

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP, PATCHED, SHEET = "backup", "flash-custom.bin", "sheet.png"
# The manifest WTOOLS ships inside the bundle: one SHA-256 per binary,
# under `files`. It is the vendor's, not ours — see docs/gobo-icons.md §5
# for what it proves and what it does not.
MANIFEST = "changelog.json"


def sha256(path: str | PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digests(directory: str | PathLike[str]) -> dict[str, str]:
    """{name: sha256} of the files directly under `directory`."""
    names = sorted(os.listdir(directory))
    return {n: sha256(os.path.join(directory, n)) for n in names
            if os.path.isfile(os.path.join(directory, n))}


def under(path: str | PathLike[str], parent: str | PathLike[str]) -> bool:
    parent = os.path.realpath(parent)
    return os.path.realpath(path).startswith(parent + os.sep)


def manifest_state(bundle: str | PathLike[str]) -> tuple[str, int | str | None]:
    """The live bundle against the manifest it ships with — three outcomes.

    Not a boolean: ("absent", None) when there is nothing to check against,
    ("verified", n) when the n files it lists all hash to the digest declared,
    and ("diverges", name) at the first one that does not. A manifest that
    cannot be read is `absent`, not a contradiction: an older WTOOLS, or a
    folder copied by hand, is a real state and blocking on it would cost more
    than the information is worth.
    """
    path = os.path.join(bundle, MANIFEST)
    try:
        with open(path, encoding="utf-8") as stream:
            listed = [(e["file"], e["sha256"])
                      for e in json.load(stream)["files"]]
    except (OSError, ValueError, KeyError, TypeError):
        return "absent", None
    for name, digest in listed:
        target = os.path.join(bundle, name)
        if not os.path.isfile(target) or sha256(target) != digest:
            return "diverges", name
    return "verified", len(listed)


def gate_backup(backup: str | PathLike[str], bundle: str | PathLike[str]) -> tuple[bool, str]:
    provenance, what = manifest_state(bundle)
    if provenance == "diverges":
        return False, (f"the live bundle contradicts its own {MANIFEST} at "
                       f"{what}: a copy would not be a factory restore point — "
                       "reinstall the bundle from WTOOLS before copying it")
    if not os.path.isdir(backup):
        return False, f"{backup} is missing"
    if under(backup, bundle) or os.path.realpath(backup) == os.path.realpath(bundle):
        return False, ("inside the WTOOLS folder: the next update will "
                       "overwrite it")
    live, copy = digests(bundle), digests(backup)
    gaps = [n for n in live if copy.get(n) != live[n]]
    if gaps:
        return False, (f"{len(gaps)} file(s) missing or different from the "
                       f"live bundle: {', '.join(gaps[:3])}")
    checked = (f"provenance verified against {MANIFEST}"
               if provenance == "verified"
               else f"provenance not verified: no {MANIFEST} in the bundle")
    return True, f"{len(live)} files, {len(live)} matching SHA-256, {checked}"


def gate_patched(patched: str | PathLike[str], flash: str | PathLike[str]) -> tuple[bool, str]:
    """The chain installed bundle → manifest → the file that goes in the device.

    Length proves nothing: an arbitrary file of the same size used to pass this
    gate. The manifest written by `gobo_write.py patch` carries the two hashes
    that close it.
    """
    if not os.path.isfile(patched):
        return False, f"{PATCHED} is missing"
    path = patched + ".json"
    if not os.path.isfile(path):
        return False, (f"{os.path.basename(path)} is missing: run the patch "
                       "again, it writes one alongside the file")
    try:
        with open(path, encoding="utf-8") as stream:
            manifest = json.load(stream)
        source, result = manifest["source"], manifest["result"]
        expected = source["sha256"], result["sha256"]
    except (ValueError, KeyError, OSError) as error:
        return False, f"unreadable manifest ({error})"
    if os.path.getsize(patched) != os.path.getsize(flash):
        return False, (f"{os.path.getsize(patched)} bytes against "
                       f"{os.path.getsize(flash)} in the original: the pointers "
                       "are absolute, the length must not move")
    if sha256(patched) != expected[1]:
        return False, ("the patched file does not match its manifest: the same "
                       "length does not mean the same content")
    if sha256(flash) != expected[0]:
        return False, (f"the installed bundle is no longer the one the patch "
                       f"came from ({source.get('bundle')}): re-patch from the "
                       "current bundle")
    return True, (f"{os.path.getsize(patched)} bytes, "
                  f"{len(manifest.get('ids', []))} icon(s), chain verified")


def upload_plan(work: str | PathLike[str]) -> tuple[bytes, dict[str, object]]:
    """Return a flash image only after the complete local upload proof passes."""
    if os.path.realpath(work) == os.path.realpath(REPO) or under(work, REPO):
        raise ValueError("the gobo working directory must be outside the repository")
    backup = os.path.join(work, BACKUP)
    patched = os.path.join(work, PATCHED)
    sheet = os.path.join(work, SHEET)
    manifest_path = patched + ".json"
    backup_flash = os.path.join(backup, "wolfmixFlash.bin")
    provenance, detail = manifest_state(backup)
    if provenance != "verified":
        raise ValueError(
            f"backup is not verified by {MANIFEST}"
            + (f" ({detail})" if detail else "")
        )
    try:
        with open(manifest_path, encoding="utf-8") as stream:
            manifest = json.load(stream)
        source = manifest["source"]
        result = manifest["result"]
        ids = manifest["ids"]
        windows = manifest["windows"]
        expected_changed = manifest["bytesChanged"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"unreadable patch manifest: {error}") from None
    if os.path.basename(source.get("path", "")) != "wolfmixFlash.bin":
        raise ValueError("the patch source is not wolfmixFlash.bin")
    if result.get("file") != PATCHED:
        raise ValueError(f"the patch result must be named {PATCHED}")
    if not ids or any(not isinstance(value, int) or isinstance(value, bool)
                      for value in ids):
        raise ValueError("the patch manifest has no valid gobo ids")
    try:
        with open(backup_flash, "rb") as stream:
            before = stream.read()
        with open(patched, "rb") as stream:
            after = stream.read()
    except OSError as error:
        raise ValueError(f"unreadable upload input: {error}") from None
    digest_before = hashlib.sha256(before).hexdigest()
    digest_after = hashlib.sha256(after).hexdigest()
    if (source.get("sha256"), source.get("size")) != (digest_before, len(before)):
        raise ValueError("the verified backup does not match the patch source")
    if (result.get("sha256"), result.get("size")) != (digest_after, len(after)):
        raise ValueError("the patched flash does not match its manifest")
    library = Library(backup_flash)
    expected_windows = [
        [library.ptrs[value] - library.base,
         library.ptrs[value] - library.base + ICON]
        for value in sorted(ids)
    ]
    if windows != expected_windows:
        raise ValueError("the manifest windows do not match its gobo ids")
    changed = gobo_write.verify(before, after, library, ids)
    if not changed or changed != expected_changed:
        raise ValueError("the changed-byte count does not match the manifest")
    if not os.path.isfile(sheet) or os.path.getmtime(sheet) < os.path.getmtime(patched):
        raise ValueError("the contact sheet is missing or older than the patched flash")
    return after, {
        "size": len(after),
        "sha256": digest_after,
        "ids": sorted(ids),
        "bytesChanged": changed,
        "backupFilesVerified": detail,
    }


def gates(work: str | PathLike[str], flash: str | PathLike[str]) -> list[tuple[str, bool, str]]:
    """[(label, green, detail)] in the order of the recipe's steps."""
    bundle = os.path.dirname(flash)
    backup = os.path.join(work, BACKUP)
    patched = os.path.join(work, PATCHED)
    sheet = os.path.join(work, SHEET)

    states = [("0 backup",) + gate_backup(backup, bundle)]

    silhouettes = glob.glob(os.path.join(work, "gobo*.png"))
    states.append(("1 silhouettes", bool(silhouettes),
                   f"{len(silhouettes)} gobo*.png file(s)"
                   if silhouettes else "no gobo*.png in the directory"))

    states.append(("2 patched flash",) + gate_patched(patched, flash))

    if not os.path.isfile(sheet):
        states.append(("3 sheet", False, f"{SHEET} is missing"))
    elif not os.path.isfile(patched):
        states.append(("3 sheet", False, "rendered with no patched flash"))
    elif os.path.getmtime(sheet) < os.path.getmtime(patched):
        states.append(("3 sheet", False,
                       "older than the patched flash: it does not show what "
                       "will go into the device"))
    else:
        states.append(("3 sheet", True, "rendered after the patched flash"))
    return states


def next_step(
    states: list[tuple[str, bool, str]],
    work: str | PathLike[str],
    flash: str | PathLike[str],
) -> str | None:
    """The text of the next step: the first red gate, or the device."""
    bundle = os.path.dirname(flash)
    patched = os.path.join(work, PATCHED)
    red = next((e for e in states if not e[1]), None)
    if red is None:
        return ("sheet approved by the operator? connect mains power, close "
                "WTOOLS, then run the guarded upload:\n"
                f"  python3 tools/wolfmix.py gobo-upload {work} "
                "--confirm-mains-power\n"
                "  # project save, WLINK, firmware and complete profile "
                "inventory are checked before the first chunk\n"
                "  # names and order afterwards, if needed: "
                "docs/gobo-icons.md §6")
    step = red[0][0]
    if step == "0":
        return ("refused: no verified backup, no patch and no upload.\n"
                f'  cp -R "{bundle}" "{os.path.join(work, BACKUP)}"\n'
                f"  python3 tools/gobo_run.py {work}")
    if step == "1":
        return ("photograph the wheel, then generate the silhouettes — the "
                "prompt is in docs/gobo-icons.md §1-2.\n"
                f"  save gobo01.png, gobo02.png… in {work}")
    if step == "2":
        return ("read the palette, then patch a COPY — never the `Open` entry, "
                "the tool refuses it.\n"
                "  python3 tools/gobo_library.py palette YOUR-PROJECT.wpj\n"
                f"  python3 tools/gobo_write.py patch {patched} \\\n"
                f"      342=mask:{os.path.join(work, 'gobo01.png')}")
    return ("render the sheet FROM the patched file, and have it approved "
            "before any upload.\n"
            f"  WOLFMIX_FLASH={patched} python3 tools/gobo_library.py \\\n"
            f"      sheet {os.path.join(work, SHEET)} 342,343")


def report(work: str | PathLike[str], flash: str | PathLike[str]) -> tuple[str, bool]:
    states = gates(work, flash)
    width = max(len(e[0]) for e in states)
    lines = [f"working directory  {work}",
             f"original flash     {flash}", ""]
    lines += [f"{e[0]:<{width}}  {'OK ' if e[1] else 'NO '}  {e[2]}"
              for e in states]
    lines += ["", next_step(states, work, flash)]
    return "\n".join(lines), all(e[1] for e in states)


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        bundle = os.path.join(tmp, "wm-fw-bundle-2.0.18")
        work = os.path.join(tmp, "gobos")
        os.makedirs(bundle)
        os.makedirs(work)
        flash = os.path.join(bundle, "wolfmixFlash.bin")
        for name, body in (("wolfmixFlash.bin", b"\x01" * 4096),
                           ("wolfmixFlash-reset.bin", b"\x02" * 16),
                           ("firmware.bin", b"\x03" * 16)):
            open(os.path.join(bundle, name), "wb").write(body)

        def state(name):
            return dict((e[0], e[1]) for e in gates(work, flash))[name]

        def detail(name):
            return dict((e[0], e[2]) for e in gates(work, flash))[name]

        assert state("0 backup") is False, "missing backup = red"
        assert "cp -R" in next_step(gates(work, flash), work, flash)

        # A backup left inside the WTOOLS folder is not a backup.
        inside = os.path.join(bundle, "backup")
        os.makedirs(inside)
        assert gate_backup(inside, bundle)[0] is False

        backup = os.path.join(work, BACKUP)
        os.makedirs(backup)
        for name in os.listdir(bundle):
            path = os.path.join(bundle, name)
            if os.path.isfile(path):
                open(os.path.join(backup, name), "wb").write(
                    open(path, "rb").read())
        assert state("0 backup") is True, "faithful copy = green"
        # No manifest in this bundle yet: the copy decides the verdict alone,
        # and the line says the provenance was not checked.
        assert "not verified" in detail("0 backup"), detail("0 backup")

        def publish(digests_):
            """Write the bundle's manifest, and mirror it into the backup."""
            path = os.path.join(bundle, MANIFEST)
            with open(path, "w", encoding="utf-8") as stream:
                json.dump({"fwVersion": "2.0.18",
                           "files": [{"file": n, "sha256": d}
                                     for n, d in digests_.items()]}, stream)
            open(os.path.join(backup, MANIFEST), "wb").write(
                open(path, "rb").read())

        truth = {n: sha256(os.path.join(bundle, n))
                 for n in ("wolfmixFlash.bin", "wolfmixFlash-reset.bin",
                           "firmware.bin")}
        publish(truth)
        assert state("0 backup") is True, "manifest honoured = green"
        assert "provenance verified" in detail("0 backup"), detail("0 backup")

        # The whole point of the check: the copy is still faithful, and the
        # thing it was copied from is not the vendor's image.
        publish({**truth, "firmware.bin": "00" * 32})
        assert state("0 backup") is False, "manifest contradicted = red"
        assert "firmware.bin" in detail("0 backup"), detail("0 backup")
        publish(truth)
        assert state("0 backup") is True

        # One byte moving in the copy breaks the gate: that is the whole point
        # of the hashes — a partial copy would otherwise go unnoticed.
        open(os.path.join(backup, "firmware.bin"), "wb").write(b"\x04" * 16)
        assert state("0 backup") is False, "different sha256 = red"
        open(os.path.join(backup, "firmware.bin"), "wb").write(b"\x03" * 16)

        assert state("1 silhouettes") is False
        open(os.path.join(work, "gobo01.png"), "wb").write(b"x")
        assert state("1 silhouettes") is True

        assert state("2 patched flash") is False
        patched = os.path.join(work, PATCHED)

        def manifest(source_sha, result_sha):
            with open(patched + ".json", "w", encoding="utf-8") as stream:
                json.dump({"source": {"sha256": source_sha,
                                      "bundle": "wm-fw-bundle-2.0.18"},
                           "result": {"sha256": result_sha},
                           "ids": [342]}, stream)

        open(patched, "wb").write(b"\x01" * 4095)
        assert state("2 patched flash") is False, "missing manifest = red"
        manifest(sha256(flash), sha256(patched))
        assert state("2 patched flash") is False, "different length = red"
        open(patched, "wb").write(b"\x01" * 4096)
        manifest(sha256(flash), sha256(patched))
        assert state("2 patched flash") is True

        # Same length, foreign content: the length gate let it through, the
        # chain of hashes does not.
        foreign = os.path.join(work, "other.bin")
        open(foreign, "wb").write(b"\x09" * 4096)
        manifest(sha256(flash), sha256(foreign))
        assert state("2 patched flash") is False, "patch sha ignored"

        # The bundle rewritten by WTOOLS since the patch: red as well.
        manifest(sha256(foreign), sha256(patched))
        assert state("2 patched flash") is False, "source bundle ignored"
        os.remove(foreign)
        manifest(sha256(flash), sha256(patched))
        assert state("2 patched flash") is True

        # The sheet must be newer than the patched flash, otherwise it shows
        # the sources and not what will go into the device.
        sheet = os.path.join(work, SHEET)
        open(sheet, "wb").write(b"png")
        os.utime(sheet, (0, os.path.getmtime(patched) - 10))
        assert state("3 sheet") is False, "older sheet = red"
        os.utime(sheet, (0, os.path.getmtime(patched) + 10))
        assert state("3 sheet") is True

        text, green = report(work, flash)
        assert green and "gobo-upload" in text and "confirm-mains-power" in text
    print("ok — 4 gates, each red then green, the live bundle checked against "
          "its manifest in all three states, the patched flash's chain of "
          "hashes verified, refusal at the head of the report")


def _parser():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", nargs="?",
                        help="the working directory, OUTSIDE the repository; "
                             "with no argument, self-check")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.directory is None:
        self_test()
        return 0
    work = os.path.abspath(os.path.expanduser(args.directory))
    if work == REPO or under(work, REPO):
        print("refused: the working directory is under the repository. "
              "Silhouettes, patched flash and contact sheet are your fixture's "
              "data and stay outside (LEGAL.md) — ~/gobos, for example.",
              file=sys.stderr)
        return 2
    if not os.path.isdir(work):
        print(f"refused: {work} is not a directory", file=sys.stderr)
        return 2
    flash = find_flash(os.environ.get("WOLFMIX_FLASH"))
    if not flash:
        print("no local flash image (WTOOLS never downloaded the firmware) — "
              "nothing to guide", file=sys.stderr)
        return 0
    text, green = report(work, flash)
    print(text)
    return 0 if green else 2


if __name__ == "__main__":
    sys.exit(main())
