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

Sans liste, le contrôle s'abstient (exit 0) et le dit — comme les self-checks
sans corpus.

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
    print("self-check ok : détection, casse ignorée, absence de liste tolérée",
          file=sys.stderr)


def main(argv):
    regles = motifs()
    if not regles:
        print(f"wpj_privacy : ignoré, pas de {LISTE} (voir LEGAL.md)",
              file=sys.stderr)
        return 0
    chemins = argv or fichiers_suivis()
    trouves = controle(chemins, regles)
    if trouves:
        print(f"wpj_privacy : {len(trouves)} occurrence(s) de nom réel dans des "
              "fichiers suivis — à neutraliser avant de committer :", file=sys.stderr)
        for chemin, numero, motif in trouves:
            print(f"  {chemin}:{numero}  (motif /{motif}/)", file=sys.stderr)
        return 1
    print(f"wpj_privacy : {len(regles)} motifs, aucune occurrence dans "
          f"{len(chemins)} fichiers suivis", file=sys.stderr)
    return 0


if __name__ == "__main__":
    demo()
    sys.exit(main(sys.argv[1:]))
