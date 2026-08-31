#!/usr/bin/env python3
"""The guard: no real name may enter a tracked file.

This repository publishes research, not the operator's venues, clients or gear
(LEGAL.md). Names are replaced by neutral labels (rig-a/b/c, `<group-A name>`,
serial withheld) — but nothing stopped anyone from reintroducing one by writing
a new section, and it happened.

The list of forbidden patterns lives OUTSIDE the repository, or the guard would
publish exactly what it protects: a `.wpj-private-names` file (git-ignored) at
the root, or $WPJ_PRIVATE_NAMES. One pattern per line, case-insensitive, Python
regular-expression syntax; a leading `#` is a comment. A pattern prefixed with
`cs:` is matched case-sensitively — indispensable when the forbidden proper
noun is spelled like an ordinary word in the code.

With no list, the NAME check abstains (exit 0) and says so — like the
self-checks with no corpus. The forbidden-file check always runs:
`.gitignore` does not survive `git add -f`, this does.

Usage:
  wpj_privacy.py          check the files git tracks
  wpj_privacy.py file…    check those files
"""
import os
import re
import subprocess
import sys

LISTE = ".wpj-private-names"
ENV = "WPJ_PRIVATE_NAMES"

# What a tracked file may never be, whatever the name list says: projects and
# vendor sidecars, DMX captures, extractions, flash images.
EXTENSIONS_INTERDITES = (".wpj", ".wm", ".wmx", ".pdf")
MOTIFS_CHEMIN = ("research/vendor/", ".wolfmix-state/", "/dmx/",
                 "wm-fw-bundle", "wolfmixFlash", "wolfmixFirmware",
                 "flash-custom.bin", ".wpj-private-names")


def motifs(chemin=None):
    """Loads the forbidden patterns, or returns [] when the list is absent."""
    chemin = chemin or os.environ.get(ENV) or LISTE
    try:
        with open(chemin, encoding="utf-8") as flux:
            lignes = [l.strip() for l in flux]
    except OSError:
        return []
    regles = []
    for ligne in lignes:
        if not ligne or ligne.startswith("#"):
            continue
        if ligne.startswith("cs:"):
            regles.append(re.compile(ligne[3:]))
        else:
            regles.append(re.compile(ligne, re.I))
    return regles


def fichiers_suivis():
    sortie = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                            check=True).stdout
    return [f for f in sortie.splitlines() if f]


def fichiers_interdits(chemins):
    """Tracked files that should never have been — by extension or by path."""
    return [c for c in chemins
            if c.lower().endswith(EXTENSIONS_INTERDITES)
            or any(m in c for m in MOTIFS_CHEMIN)]


def controle(chemins, regles):
    """Returns the (file, line, pattern) triples that violate the list."""
    trouves = []
    for chemin in chemins:
        try:
            with open(chemin, encoding="utf-8") as flux:
                for numero, ligne in enumerate(flux, 1):
                    for regle in regles:
                        if regle.search(ligne):
                            trouves.append((chemin, numero, regle.pattern))
        except (OSError, UnicodeDecodeError):
            continue                      # binary or unreadable: out of scope
    return trouves


def demo():
    import tempfile
    regles = [re.compile("forbidden", re.I), re.compile(r"\b12345\b")]
    with tempfile.TemporaryDirectory() as tmp:
        propre = os.path.join(tmp, "propre.md")
        sale = os.path.join(tmp, "sale.md")
        open(propre, "w").write("rig-a, rig-b, nothing to report\n")
        open(sale, "w").write("ok\nname FORBIDDEN here\nserial 12345\n")
        assert controle([propre], regles) == []
        trouves = controle([sale], regles)
        assert [(n, m) for _, n, m in trouves] == [
            (2, "forbidden"), (3, r"\b12345\b")], trouves
        assert motifs(os.path.join(tmp, "absent")) == []
        # cs: = case-sensitive, for a proper noun spelled like a common word
        liste = os.path.join(tmp, "noms")
        open(liste, "w").write("# comment\ncs:\\bMarche\\b\nother\n")
        cs, insensible = motifs(liste)
        propre2 = os.path.join(tmp, "verbe.md")
        open(propre2, "w").write("the decoder marche on this file\n")
        assert controle([propre2], [cs]) == []
        sale2 = os.path.join(tmp, "nom-propre.md")
        open(sale2, "w").write("the Marche projects\n")
        assert len(controle([sale2], [cs])) == 1
        assert insensible.flags & __import__("re").I
    # A forbidden file is refused on its extension or its path, even with no
    # name list — this is what `git add -f` used to slip past.
    assert fichiers_interdits(["docs/tools.md", "README.md"]) == []
    for interdit in ("corpus/x.wpj", "a/b.WMX", "research/vendor/blob.txt",
                     "corpus/EXP/dmx/capture.bin", "manual.pdf",
                     "x/wm-fw-bundle-2.0.18/wolfmixFlash.bin",
                     "flash-custom.bin", ".wpj-private-names"):
        assert fichiers_interdits([interdit]) == [interdit], interdit
    print("self-check ok: detection, case folding, missing list tolerated, "
          "forbidden extensions and paths refused", file=sys.stderr)


def main(argv):
    chemins = argv or fichiers_suivis()
    interdits = fichiers_interdits(chemins)
    if interdits:
        print(f"wpj_privacy: {len(interdits)} tracked file(s) that should "
              "never be (LEGAL.md):", file=sys.stderr)
        for chemin in interdits:
            print(f"  {chemin}", file=sys.stderr)
        return 1
    regles = motifs()
    if not regles:
        print(f"wpj_privacy: {len(chemins)} tracked files, no forbidden "
              f"extension or path — but ABSTAINING on names, no {LISTE} "
              f"(see LEGAL.md): not one name was checked", file=sys.stderr)
        return 0
    trouves = controle(chemins, regles)
    if trouves:
        print(f"wpj_privacy: {len(trouves)} occurrence(s) of a real name in "
              "tracked files — neutralise before committing:", file=sys.stderr)
        for chemin, numero, motif in trouves:
            print(f"  {chemin}:{numero}  (pattern /{motif}/)", file=sys.stderr)
        return 1
    print(f"wpj_privacy: {len(regles)} patterns, no occurrence in "
          f"{len(chemins)} tracked files, no forbidden file", file=sys.stderr)
    return 0


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("fichiers", nargs="*",
                         help="files to check; by default, the ones git "
                              "tracks")
    args = parseur.parse_args(argv)
    demo()
    return main(args.fichiers)


if __name__ == "__main__":
    sys.exit(_cli())
