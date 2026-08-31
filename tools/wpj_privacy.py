#!/usr/bin/env python3
"""Garde-fou : aucun nom réel ne doit entrer dans les fichiers suivis.

Le dépôt publie de la recherche, pas les lieux, les clients ni le matériel de
l'opérateur (LEGAL.md). Les noms sont remplacés par des étiquettes neutres
(rig-a/b/c, `<group-A name>`, série retirée) — mais rien n'empêchait de les
réintroduire en écrivant une nouvelle section, et c'est arrivé.

La liste des motifs interdits vit HORS du dépôt, sinon le garde-fou publierait
exactement ce qu'il protège : un fichier `.wpj-private-names` (git-ignoré) à la
racine, ou $WPJ_PRIVATE_NAMES. Un motif par ligne, insensible à la casse,
syntaxe d'expression régulière Python ; `#` en début de ligne = commentaire.
Un motif préfixé `cs:` est comparé en respectant la casse — indispensable quand
le nom propre interdit s'écrit comme un mot courant du code (« Marche », le
lieu, contre « marche », le verbe).

Sans liste, le contrôle des NOMS s'abstient (exit 0) et le dit — comme les
self-checks sans corpus. Le contrôle des fichiers interdits, lui, tourne
toujours : `.gitignore` ne protège pas de `git add -f`, celui-ci si.

Usage :
  wpj_privacy.py            contrôle les fichiers suivis par git
  wpj_privacy.py fichier…   contrôle ces fichiers
"""
import os
import re
import subprocess
import sys

LISTE = ".wpj-private-names"
ENV = "WPJ_PRIVATE_NAMES"

# Ce qu'un fichier suivi ne peut pas être, quelle que soit la liste de noms :
# projets et sidecars du fabricant, captures DMX, extractions, images flash.
EXTENSIONS_INTERDITES = (".wpj", ".wm", ".wmx", ".pdf")
MOTIFS_CHEMIN = ("research/vendor/", ".wolfmix-state/", "/dmx/",
                 "wm-fw-bundle", "wolfmixFlash", "wolfmixFirmware",
                 "flash-custom.bin", ".wpj-private-names")


def motifs(chemin=None):
    """Charge les motifs interdits, ou rend [] si la liste est absente."""
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
    """Fichiers suivis qui n'auraient jamais dû l'être — extension ou chemin."""
    return [c for c in chemins
            if c.lower().endswith(EXTENSIONS_INTERDITES)
            or any(m in c for m in MOTIFS_CHEMIN)]


def controle(chemins, regles):
    """Rend la liste des (fichier, ligne, motif) qui violent la liste."""
    trouves = []
    for chemin in chemins:
        try:
            with open(chemin, encoding="utf-8") as flux:
                for numero, ligne in enumerate(flux, 1):
                    for regle in regles:
                        if regle.search(ligne):
                            trouves.append((chemin, numero, regle.pattern))
        except (OSError, UnicodeDecodeError):
            continue                      # binaire ou illisible : hors périmètre
    return trouves


def demo():
    import tempfile
    regles = [re.compile("interdit", re.I), re.compile(r"\b12345\b")]
    with tempfile.TemporaryDirectory() as tmp:
        propre = os.path.join(tmp, "propre.md")
        sale = os.path.join(tmp, "sale.md")
        open(propre, "w").write("rig-a, rig-b, rien à signaler\n")
        open(sale, "w").write("ok\nnom INTERDIT ici\nsérie 12345\n")
        assert controle([propre], regles) == []
        trouves = controle([sale], regles)
        assert [(n, m) for _, n, m in trouves] == [(2, "interdit"), (3, r"\b12345\b")], trouves
        assert motifs(os.path.join(tmp, "absent")) == []
        # cs: = sensible à la casse, pour un nom propre homographe d'un mot courant
        liste = os.path.join(tmp, "noms")
        open(liste, "w").write("# commentaire\ncs:\\bMarche\\b\nautre\n")
        cs, insensible = motifs(liste)
        propre2 = os.path.join(tmp, "verbe.md")
        open(propre2, "w").write("le décodeur marche sur ce fichier\n")
        assert controle([propre2], [cs]) == []
        sale2 = os.path.join(tmp, "nom-propre.md")
        open(sale2, "w").write("les projets Marche\n")
        assert len(controle([sale2], [cs])) == 1
        assert insensible.flags & __import__("re").I
    # Un fichier interdit est refusé sur son extension ou son chemin, même
    # sans liste de noms — c'est ce que `git add -f` contournait.
    assert fichiers_interdits(["docs/tools.md", "README.md"]) == []
    for interdit in ("corpus/x.wpj", "a/b.WMX", "research/vendor/blob.txt",
                     "corpus/EXP/dmx/capture.bin", "manual.pdf",
                     "x/wm-fw-bundle-2.0.18/wolfmixFlash.bin",
                     "flash-custom.bin", ".wpj-private-names"):
        assert fichiers_interdits([interdit]) == [interdit], interdit
    print("self-check ok : détection, casse ignorée, absence de liste tolérée, "
          "extensions et chemins interdits refusés", file=sys.stderr)


def main(argv):
    chemins = argv or fichiers_suivis()
    interdits = fichiers_interdits(chemins)
    if interdits:
        print(f"wpj_privacy : {len(interdits)} fichier(s) suivis qui ne "
              "devraient jamais l'être (LEGAL.md) :", file=sys.stderr)
        for chemin in interdits:
            print(f"  {chemin}", file=sys.stderr)
        return 1
    regles = motifs()
    if not regles:
        print(f"wpj_privacy : {len(chemins)} fichiers suivis, aucune extension "
              f"ni chemin interdit — mais ABSTENTION sur les noms, pas de "
              f"{LISTE} (voir LEGAL.md) : aucun nom n'a été vérifié",
              file=sys.stderr)
        return 0
    trouves = controle(chemins, regles)
    if trouves:
        print(f"wpj_privacy : {len(trouves)} occurrence(s) de nom réel dans des "
              "fichiers suivis — à neutraliser avant de committer :", file=sys.stderr)
        for chemin, numero, motif in trouves:
            print(f"  {chemin}:{numero}  (motif /{motif}/)", file=sys.stderr)
        return 1
    print(f"wpj_privacy : {len(regles)} motifs, aucune occurrence dans "
          f"{len(chemins)} fichiers suivis, aucun fichier interdit",
          file=sys.stderr)
    return 0


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("fichiers", nargs="*",
                         help="fichiers a controler ; par defaut, ceux que "
                              "git suit")
    args = parseur.parse_args(argv)
    demo()
    return main(args.fichiers)


if __name__ == "__main__":
    sys.exit(_cli())
