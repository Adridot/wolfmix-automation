#!/usr/bin/env python3
"""The gate: every hardware-free check, then a summary that names abstentions.

Module group: Verification. Reference: docs/tools.md.

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

from __future__ import annotations
from collections.abc import Sequence
import argparse
import os
import subprocess
import sys
from pathlib import Path

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
    ("ssl2", ["python3", "tools/ssl2.py"]),
    ("wpj_show", ["python3", "tools/wpj_show.py"]),
    ("wpj_generate", ["python3", "tools/wpj_generate.py"]),
    ("wpj_patch", ["python3", "tools/wpj_patch.py"]),
    ("wpj_api", ["python3", "tools/wpj_api.py"]),
    ("wpj_identities", ["python3", "tools/wpj_identities.py"]),
    ("wpj_coverage", ["python3", "tools/wpj_coverage.py"]),
    ("wpj_position", ["python3", "tools/wpj_position.py"]),
    ("wolfmix_transaction", ["python3", "tools/wolfmix_transaction.py"]),
    ("wpj_privacy", ["python3", "tools/wpj_privacy.py"]),
    ("wpj_links", ["python3", "tools/wpj_links.py"]),
    ("wpj_counts", ["python3", "tools/wpj_counts.py"]),
    ("wpj_evidence", ["python3", "tools/wpj_evidence.py"]),
    ("gobo_run", ["python3", "tools/gobo_run.py"]),
    ("boundaries", ["python3", "-m", "unittest", "discover", "-s", "tests",
                    "-t", "."]),
]

# What the summary counts: the subprocesses above, plus the in-process
# stdlib-only step below. `wpj_counts.py` reads this rather than len(CONTROLES),
# so a document quoting the number cannot drift from what a run prints.
NOMBRE_DE_CONTROLES = len(CONTROLES) + 1

PASSE, ABSTENU, ECHEC = "passed", "abstained", "failed"

# The repository's first invariant had no gate until now: "standard library
# only" was a promise in three documents and a habit in the code.
NOTRES = ("tools", "tests")


def imports_hors_stdlib() -> list[tuple[Path, int, str]]:
    """Every module imported by our own code that the standard library lacks.

    Parsed, not executed: a dependency that only appears at run time under a
    `try` is still a dependency, and importing the tree to find out would run
    it. `sys.stdlib_module_names` is the authority — it is what this
    interpreter actually ships.
    """
    import ast
    trouves = []
    for dossier in NOTRES:
        for chemin in sorted(Path(RACINE, dossier).rglob("*.py")):
            arbre = ast.parse(chemin.read_text(encoding="utf-8"), str(chemin))
            for noeud in ast.walk(arbre):
                if isinstance(noeud, ast.Import):
                    noms = [a.name for a in noeud.names]
                elif isinstance(noeud, ast.ImportFrom):
                    noms = [noeud.module] if noeud.level == 0 and noeud.module else []
                else:
                    continue
                for nom in noms:
                    racine = nom.split(".")[0]
                    if (racine in sys.stdlib_module_names
                            or Path(RACINE, "tools", racine + ".py").exists()
                            or racine in ("tests",)):
                        continue
                    trouves.append((chemin.relative_to(RACINE), noeud.lineno, nom))
    return trouves


def executer(commande: Sequence[str]) -> tuple[int, str]:
    """(exit code, combined output). The output is echoed as it is captured."""
    resultat = subprocess.run(commande, cwd=RACINE, text=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
    sys.stdout.write(resultat.stdout)
    sys.stdout.flush()
    return resultat.returncode, resultat.stdout


def classer(code: int, sortie: str) -> tuple[str, str]:
    """A non-zero code is a failure; the marker word is an abstention."""
    if code != 0:
        return ECHEC, ""
    for ligne in sortie.splitlines():
        if ABSTENTION in ligne:
            _, _, detail = ligne.strip().partition(ABSTENTION)
            return ABSTENU, (ABSTENTION + detail)
    return PASSE, ""


def resume(resultats: list[tuple[str, str, str]]) -> dict[str, list[str]]:
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


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--abstentions-ok", action="store_true",
                         help="exit 0 instead of 3 when checks abstained; for "
                              "a context that expects it, such as the "
                              "corpus-free CI job")
    args = parseur.parse_args(argv)
    resultats = []
    etrangers = imports_hors_stdlib()
    print("--- stdlib-only: no import outside the standard library")
    if etrangers:
        for chemin, ligne, nom in etrangers:
            print(f"{chemin}:{ligne}: imports {nom!r}, which is not in the "
                  "standard library", file=sys.stderr)
        resultats.append(("stdlib-only", ECHEC, ""))
    else:
        print(f"ok — {NOMBRE_DE_CONTROLES} checks in this run, none of them "
              "needs a dependency")
        resultats.append(("stdlib-only", PASSE, ""))
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


def demo() -> None:
    """The classifier is the whole load-bearing part: prove it separately."""
    assert classer(0, "self-check ok: 76 files") == (PASSE, "")
    etat, ligne = classer(0, f"wpjlib: {ABSTENTION} — no corpus in corpus/")
    assert etat == ABSTENU, etat
    assert ligne == f"{ABSTENTION} — no corpus in corpus/", ligne
    assert classer(1, f"x: {ABSTENTION}")[0] == ECHEC, "a failure outranks it"
    assert classer(2, "boom")[0] == ECHEC
    # Not asserted here on purpose: a real dependency must be *reported* by the
    # run, with the file and the line, not crash the self-check before it.


if __name__ == "__main__":
    demo()
    sys.exit(main())
