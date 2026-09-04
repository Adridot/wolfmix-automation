#!/usr/bin/env python3
"""Counts that drift: produced here, and checked against the documents.

Module group: Verification. Reference: docs/tools.md.

"16 decoded, 4 passthrough", "18 identities", "15 checks" — every one of those
moves as the work moves, and every one was written by hand in three places. On
2026-08-31 `SPEC.md` still said seventeen identities while the code ran
eighteen: nobody lied, the number simply aged.

So the numbers are computed from the code, and a document that states one
marks it:

    ... **18 identities** <!--count:identities-->
    Decoded: 101, 102, … <!--types:decoded--> — 16 <!--count:decoded-->

A `count:` marker claims the last integer written before it; a `types:` marker
claims every integer in that stretch. A mismatch fails `make check` — so
moving a record from passthrough to decoded makes the **gate** react, not a
reader noticing months later.

Usage:
  wpj_counts.py            check the tracked documents
  wpj_counts.py --print    the counts themselves, for pasting or scripting
"""

from __future__ import annotations
from os import PathLike
from collections.abc import Iterable
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check
import wpj_codec
import wpj_identities
import wpjlib
from wpj_privacy import fichiers_suivis

MARQUEUR = re.compile(r"<!--\s*(count|types):(\w+)\s*-->")
ENTIER = re.compile(r"\d+")


def compter() -> dict[str, int]:
    """Every drifting figure, from the code that defines it."""
    return {
        "checks": check.NOMBRE_DE_CONTROLES,
        "identities": len(wpj_identities.IDENTITES),
        "record_types": len(wpj_codec.TYPES),
        "decoded": len(wpj_codec.SCHEMAS),
        "passthrough": len(wpj_codec.PASSTHROUGH),
    }


def listes() -> dict[str, list[int]]:
    return {
        "decoded": sorted(wpj_codec.SCHEMAS),
        "passthrough": sorted(wpj_codec.PASSTHROUGH),
        "record_types": list(wpj_codec.TYPES),
    }


PARAGRAPHE = re.compile(r"\n[ \t]*\n")


def revendications(texte: str) -> list[tuple[int, str, str, int | list[int] | None]]:
    """(line, kind, name, claimed) for every marker, with what precedes it.

    The stretch a marker claims runs back to the previous marker, or to the
    start of its paragraph — a sentence wraps, and a claim should not have to
    fit on one line to be checked.
    """
    coupures = [0] + [m.end() for m in PARAGRAPHE.finditer(texte)]
    trouves, fin = [], 0
    for marque in MARQUEUR.finditer(texte):
        if (texte[marque.start() - 1:marque.start()] == "`"
                and texte[marque.end():marque.end() + 1] == "`"):
            continue                  # `<!--count:name-->` in prose: an example
        debut = max([fin] + [c for c in coupures if c <= marque.start()])
        segment = texte[debut:marque.start()]
        fin = marque.end()
        numero = texte.count("\n", 0, marque.start()) + 1
        entiers = [int(x) for x in ENTIER.findall(segment)]
        if not entiers:
            trouves.append((numero, marque.group(1), marque.group(2), None))
        elif marque.group(1) == "count":
            trouves.append((numero, "count", marque.group(2), entiers[-1]))
        else:
            trouves.append((numero, "types", marque.group(2), entiers))
    return trouves


def ecarts(
    documents: Iterable[str | PathLike[str]],
    comptes: dict[str, int],
    tables: dict[str, list[int]],
) -> list[tuple[str | PathLike[str], int, str, object, object]]:
    """(document, line, name, claimed, actual) for every marker that lies."""
    trouves = []
    for document in documents:
        try:
            with open(document, encoding="utf-8") as flux:
                texte = flux.read()
        except (OSError, UnicodeDecodeError):
            continue
        for numero, genre, nom, revendique in revendications(texte):
            reference = comptes if genre == "count" else tables
            if nom not in reference:
                trouves.append((document, numero, f"{genre}:{nom}",
                                revendique, "unknown marker"))
            elif revendique != reference[nom]:
                trouves.append((document, numero, f"{genre}:{nom}",
                                revendique, reference[nom]))
    return trouves


def demo() -> None:
    ligne = ("| 20 types <!--count:record_types--> | 16 decoded "
             "<!--count:decoded-->, 4 <!--count:passthrough--> verbatim "
             "(106, 110, 155, 161) <!--types:passthrough--> |")
    assert revendications(ligne) == [
        (1, "count", "record_types", 20),
        (1, "count", "decoded", 16),
        (1, "count", "passthrough", 4),
        (1, "types", "passthrough", [106, 110, 155, 161]),
    ], revendications(ligne)
    # A marker with no number in front of it is a claim of nothing, and that
    # is an error rather than a silent pass.
    assert revendications("nothing <!--count:decoded-->") == [
        (1, "count", "decoded", None)]
    # A marker inside backticks is an example, not a claim — this file's own
    # documentation contains three of them.
    assert revendications("write `<!--count:decoded-->` after the figure") == []
    # A claim that wraps is still one claim; the paragraph before it is not.
    enroule = "an old figure: 99\n\n101, 102,\n105 <!--types:decoded--> — 3\n"
    assert revendications(enroule) == [
        (4, "types", "decoded", [101, 102, 105])], revendications(enroule)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        document = os.path.join(tmp, "d.md")
        with open(document, "w", encoding="utf-8") as flux:
            flux.write("9 identities <!--count:identities-->\n"
                       "1, 2 <!--types:decoded-->\n"
                       "3 <!--count:absent-->\n")
        trouves = ecarts([document], {"identities": 18}, {"decoded": [1, 2]})
    assert [(n, c, r, a) for _, n, c, r, a in trouves] == [
        (1, "count:identities", 9, 18),
        (3, "count:absent", 3, "unknown marker")], trouves
    print("self-check ok: markers read, a stale figure and an unknown name "
          "both caught, a matching list left alone", file=sys.stderr)


def main(argv: list[str] | None) -> int:
    comptes, tables = compter(), listes()
    if "--print" in argv:
        for nom, valeur in comptes.items():
            print(f"{nom}: {valeur}")
        for nom, valeur in tables.items():
            print(f"{nom}: {', '.join(str(x) for x in valeur)}")
        corpus = wpjlib.corpus_files()
        print(f"corpus: {len(corpus)} file(s) "
              f"({os.environ.get(wpjlib.CORPUS_ENV) or wpjlib.CORPUS_DEFAUT}/)"
              " — yours, not a published figure")
        return 0
    documents = [f for f in fichiers_suivis() if f.endswith(".md")]
    trouves = ecarts(documents, comptes, tables)
    if trouves:
        print(f"wpj_counts: {len(trouves)} figure(s) the code no longer "
              "supports:", file=sys.stderr)
        for document, numero, nom, revendique, reel in trouves:
            print(f"  {document}:{numero}  {nom}: document says "
                  f"{revendique}, code says {reel}", file=sys.stderr)
        return 1
    marques = sum(len(revendications(open(d, encoding="utf-8").read()))
                  for d in documents)
    print(f"wpj_counts: {marques} marked figures in {len(documents)} "
          f"documents, all matching the code", file=sys.stderr)
    return 0


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--print", action="store_true", dest="afficher",
                         help="print the counts instead of checking documents")
    args = parseur.parse_args(argv)
    demo()
    return main(["--print"] if args.afficher else [])


if __name__ == "__main__":
    sys.exit(_cli())
