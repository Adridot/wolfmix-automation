#!/usr/bin/env python3
"""The gobo job, guided: where the working directory stands, and what is next.

The six steps of `docs/gobo-icons.md` each belong to a tool of this repository.
What belonged to nobody were the gates *between* them — and on real hardware a
skipped step is expensive. This tool patches nothing, talks to no device and
writes no file: it reads a working directory and refuses to name the next step
while a gate is red.

  gobo_run.py DIRECTORY   the state of the job, then the next command
  gobo_run.py             self-check

Four gates, the ones no tool was holding:

  0 backup        the flash bundle copied OUTSIDE the WTOOLS folder — which
                  WTOOLS rewrites on every update — SHA-256 equal to the live one
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
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gobo_library import find_flash

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP, PATCHED, SHEET = "backup", "flash-custom.bin", "sheet.png"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digests(directory):
    """{name: sha256} of the files directly under `directory`."""
    names = sorted(os.listdir(directory))
    return {n: sha256(os.path.join(directory, n)) for n in names
            if os.path.isfile(os.path.join(directory, n))}


def under(path, parent):
    parent = os.path.realpath(parent)
    return os.path.realpath(path).startswith(parent + os.sep)


def gate_backup(backup, bundle):
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
    return True, f"{len(live)} files, {len(live)} matching SHA-256"


def gate_patched(patched, flash):
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


def gates(work, flash):
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


def next_step(states, work, flash):
    """The text of the next step: the first red gate, or the device."""
    bundle = os.path.dirname(flash)
    patched = os.path.join(work, PATCHED)
    red = next((e for e in states if not e[1]), None)
    if red is None:
        return ("sheet approved by the operator? then the device "
                "preconditions, and the upload by hand:\n"
                "  python3 tools/wolfmix.py profiles | tail -3   "
                "# a complete read, otherwise restart the W1\n"
                "  python3 tools/wolfmix.py settings             "
                "# wlinkActivated must be false\n"
                "  # then docs/gobo-icons.md: mains power, saved project, "
                "wtoolsMode=2, and the safety net\n"
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


def report(work, flash):
    states = gates(work, flash)
    width = max(len(e[0]) for e in states)
    lines = [f"working directory  {work}",
             f"original flash     {flash}", ""]
    lines += [f"{e[0]:<{width}}  {'OK ' if e[1] else 'NO '}  {e[2]}"
              for e in states]
    lines += ["", next_step(states, work, flash)]
    return "\n".join(lines), all(e[1] for e in states)


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        bundle = os.path.join(tmp, "wm-fw-bundle-2.0.18")
        work = os.path.join(tmp, "gobos")
        os.makedirs(bundle)
        os.makedirs(work)
        flash = os.path.join(bundle, "wolfmixFlash.bin")
        for name, body in (("wolfmixFlash.bin", b"\x01" * 4096),
                           ("wolfmixFlash-reset.bin", b"\x02" * 16),
                           ("firmware.bin", b"\x03" * 16),
                           ("bundle.json", b"{}")):
            open(os.path.join(bundle, name), "wb").write(body)

        def state(name):
            return dict((e[0], e[1]) for e in gates(work, flash))[name]

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
        assert green and "wlinkActivated" in text and "profiles" in text
    print("ok — 4 gates, each red then green, the patched flash's chain of "
          "hashes verified, refusal at the head of the report")


def _parser():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", nargs="?",
                        help="the working directory, OUTSIDE the repository; "
                             "with no argument, self-check")
    return parser


def main(argv=None):
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
