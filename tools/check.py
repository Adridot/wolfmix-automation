#!/usr/bin/env python3
"""The gate: every hardware-free check, then a summary that names abstentions.

`make check` runs this. It exists because `make` cannot do the one thing that
matters here — a check that verified nothing for want of a corpus must not be
readable as a check that passed. `make` stops at the first failure and
aggregates nothing; this runs everything, then says in one place what held,
what abstained, and what broke.

Exit codes, which is where the distinction becomes mechanical:

  0   every check ran and passed
  3   green, but at least one check verified nothing — the summary names them
  1   at least one check failed

3 is the code a clone with no corpus gets. It is not a failure and it is not a
pass: it is "the structural claims hold, and the ones that need project files
were not tested here". `--abstentions-ok` maps it to 0 for a context that
expects it — the corpus-free CI job, which is exactly that context.

No port is opened: `wolfmix.py` and `wolfmix_experiment.py` are deliberately
absent, and their hardware-free checks are separate `self-test` subcommands.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wpjlib import ABSTENTION

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The canonical list. Adding a self-check means adding a line here.
CONTROLES = [
    ("wpjlib", ["python3", "tools/wpjlib.py"]),
    ("wpj_wire", ["python3", "tools/wpj_wire.py"]),
    ("wpj_codec", ["python3", "tools/wpj_codec.py"]),
    ("wpj_inspect", ["python3", "tools/wpj_inspect.py"]),
    ("wpj_bc", ["python3", "tools/wpj_bc.py"]),
    ("wpj_show", ["python3", "tools/wpj_show.py"]),
    ("wpj_generate", ["python3", "tools/wpj_generate.py"]),
    ("wpj_api", ["python3", "tools/wpj_api.py"]),
    ("wpj_identities", ["python3", "tools/wpj_identities.py"]),
    ("wpj_position", ["python3", "tools/wpj_position.py"]),
    ("wolfmix_transaction", ["python3", "tools/wolfmix_transaction.py"]),
    ("wpj_privacy", ["python3", "tools/wpj_privacy.py"]),
    ("wpj_links", ["python3", "tools/wpj_links.py"]),
    ("wpj_counts", ["python3", "tools/wpj_counts.py"]),
    ("gobo_run", ["python3", "tools/gobo_run.py"]),
    ("boundaries", ["python3", "-m", "unittest", "discover", "-s", "tests",
                    "-t", "."]),
]

PASSE, ABSTENU, ECHEC = "passed", "abstained", "failed"


def executer(commande):
    """(exit code, combined output). The output is echoed as it is captured."""
    resultat = subprocess.run(commande, cwd=RACINE, text=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
    sys.stdout.write(resultat.stdout)
    sys.stdout.flush()
    return resultat.returncode, resultat.stdout


def classer(code, sortie):
    """A non-zero code is a failure; the marker word is an abstention."""
    if code != 0:
        return ECHEC, ""
    for ligne in sortie.splitlines():
        if ABSTENTION in ligne:
            _, _, detail = ligne.strip().partition(ABSTENTION)
            return ABSTENU, (ABSTENTION + detail)
    return PASSE, ""


def resume(resultats):
    """The last thing the reader sees. Abstentions are named, one per line."""
    comptes = {etat: [n for n, e, _ in resultats if e == etat]
               for etat in (PASSE, ABSTENU, ECHEC)}
    print()
    print(f"== check: {len(resultats)} checks, {len(comptes[PASSE])} passed, "
          f"{len(comptes[ABSTENU])} abstained, {len(comptes[ECHEC])} failed")
    for nom, etat, ligne in resultats:
        if etat == ABSTENU:
            print(f"   abstained: {nom} — {ligne}")
    for nom, etat, _ in resultats:
        if etat == ECHEC:
            print(f"   FAILED:    {nom}")
    if comptes[ECHEC]:
        print("   green means green: this run is not green.")
    elif comptes[ABSTENU]:
        print("   Nothing failed, but the checks named above verified "
              "nothing. Do not read this as a pass (docs/corpus.md).")
    return comptes


def main(argv=None):
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--abstentions-ok", action="store_true",
                         help="exit 0 instead of 3 when checks abstained; for "
                              "a context that expects it, such as the "
                              "corpus-free CI job")
    args = parseur.parse_args(argv)
    resultats = []
    for nom, commande in CONTROLES:
        print(f"--- {nom}: {' '.join(commande)}")
        etat, ligne = classer(*executer(commande))
        resultats.append((nom, etat, ligne))
    comptes = resume(resultats)
    if comptes[ECHEC]:
        return 1
    if comptes[ABSTENU] and not args.abstentions_ok:
        return 3
    return 0


def demo():
    """The classifier is the whole load-bearing part: prove it separately."""
    assert classer(0, "self-check ok: 76 files") == (PASSE, "")
    etat, ligne = classer(0, f"wpjlib: {ABSTENTION} — no corpus in corpus/")
    assert etat == ABSTENU, etat
    assert ligne == f"{ABSTENTION} — no corpus in corpus/", ligne
    assert classer(1, f"x: {ABSTENTION}")[0] == ECHEC, "a failure outranks it"
    assert classer(2, "boom")[0] == ECHEC


if __name__ == "__main__":
    demo()
    sys.exit(main())
