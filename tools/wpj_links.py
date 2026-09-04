#!/usr/bin/env python3
"""The other guard: no tracked document may point at a file that is not there.

Module group: Verification. Reference: docs/tools.md.

`wpj_privacy.py` says what must never leave. This says what must still be
found: the tree is dense with cross-references — README to SPEC, SPEC to
research, every doc to a tool — and a file renamed in one commit leaves them
pointing at nothing. A dead link in a document whose whole claim is
"everything here is checkable" is worse than a missing document.

What is checked: Markdown links, inline `[text](target)` and reference
definitions `[label]: target`, in every tracked `.md`. Fenced code blocks are
skipped — an example is not a reference. Local Markdown section anchors are
checked too, including explicit HTML anchors. External links (`http`, `mailto`)
and empty targets are out of scope: this checks the tree, not the web.

A target is resolved relative to the document, and must be a **tracked** path
or a directory that holds tracked files — not merely present on this machine,
or a git-ignored corpus file would pass here and fail everywhere else.

Usage:
  wpj_links.py            check the tracked documents
  wpj_links.py file…      check those documents
"""

from __future__ import annotations
from os import PathLike
from collections.abc import Iterable
import html
import os
import re
import sys
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wpj_privacy import fichiers_suivis

REGISTRE = "research/evidence.md"
IDENTIFIANT = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-[0-9]{2})\b")

LIEN = re.compile(r"\[[^\]]*\]\(\s*<?([^)>\s]+)>?[^)]*\)")
DEFINITION = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?([^>\s]+)>?")
EXTERNES = ("http://", "https://", "mailto:", "ftp://", "//")


def _prose(texte: str) -> Iterable[tuple[int, str]]:
    """Lines outside fenced code, with their original numbers."""
    fence = None
    for numero, ligne in enumerate(texte.splitlines(), 1):
        marque = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", ligne)
        if marque:
            if fence is None:
                fence = marque.group(1)
            elif (marque.group(1)[0] == fence[0]
                  and len(marque.group(1)) >= len(fence)
                  and not marque.group(2).strip()):
                fence = None
            continue
        if fence is None:
            yield numero, ligne


def cibles(texte: str) -> list[tuple[int, str]]:
    """(line, target) of every local link — fenced blocks left out."""
    trouves = []
    for numero, ligne in _prose(texte):
        brut = [m.group(1) for m in LIEN.finditer(ligne)]
        definition = DEFINITION.match(ligne)
        if definition:
            brut.append(definition.group(1))
        for cible in brut:
            if cible.startswith(EXTERNES) or not cible:
                continue
            trouves.append((numero, cible))
    return trouves


def anchors(texte: str) -> set[str]:
    """GitHub-style ATX/Setext headings and explicit HTML id/name anchors.

    Handles the Markdown conventions used in this repository, not every HTML
    rendering extension. Duplicate heading slugs receive numeric suffixes.
    """
    found, headings = set(), set()
    previous = ""
    for _, line in _prose(texte):
        found.update(html.unescape(m[1]) for m in re.findall(
            r'<[^>]+\b(?:id|name)\s*=\s*([\'"])(.*?)\1', line))
        match = re.match(r"^ {0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
        title = match[1] if match else previous if re.fullmatch(r" {0,3}(?:=+|-+)\s*", line) else None
        if title:
            title = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", title)
            title = html.unescape(re.sub(r"<[^>]*>", "", title)).lower()
            # Strip formatting without removing underscores inside code names.
            title = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", title)
            slug = re.sub(r"[^\w\- ]", "", title).replace(" ", "-")
            candidate, suffix = slug, 0
            while candidate in headings:
                suffix += 1
                candidate = f"{slug}-{suffix}"
            headings.add(candidate)
            found.add(candidate)
        previous = line.strip()
    return found


def resoudre(document: str | PathLike[str], cible: str) -> str | None:
    """The target as a repository path, without its anchor or its query."""
    chemin = unquote(cible.split("#", 1)[0].split("?", 1)[0])
    if not chemin:
        return None
    return os.path.normpath(os.path.join(os.path.dirname(document), chemin))


def casses(
    documents: Iterable[str | PathLike[str]],
    suivis: Iterable[str],
) -> list[tuple[str | PathLike[str], int, str]]:
    """(document, line, target) for every link that lands nowhere."""
    connus, dossiers = set(suivis), set()
    for fichier in connus:                    # a link may name a directory
        parent = os.path.dirname(fichier)
        while parent and parent not in dossiers:
            dossiers.add(parent)
            parent = os.path.dirname(parent)
    trouves, cache = [], {}
    for document in documents:
        try:
            with open(document, encoding="utf-8") as flux:
                texte = flux.read()
        except (OSError, UnicodeDecodeError):
            continue
        for numero, cible in cibles(texte):
            chemin = resoudre(document, cible) or os.fspath(document)
            if chemin not in connus and chemin not in dossiers:
                trouves.append((document, numero, cible))
                continue
            fragment = unquote(cible.partition("#")[2])
            if fragment and chemin.endswith(".md"):
                if chemin not in cache:
                    try:
                        with open(chemin, encoding="utf-8") as target:
                            cache[chemin] = anchors(target.read())
                    except (OSError, UnicodeDecodeError):
                        cache[chemin] = set()
                if fragment not in cache[chemin]:
                    trouves.append((document, numero, cible))
    return trouves


def identifiants(chemin: str | PathLike[str] = REGISTRE) -> set[str]:
    """The finding ids the evidence registry defines."""
    try:
        with open(chemin, encoding="utf-8") as flux:
            return set(IDENTIFIANT.findall(flux.read()))
    except OSError:
        return set()


def orphelins(
    suivis: Iterable[str | PathLike[str]],
    connus: set[str],
) -> list[tuple[str | PathLike[str], int, str]]:
    """(file, line, id) for every finding id with no entry in the registry.

    A citation that resolves to nothing is the same failure as a dead link, and
    it is the one this repository would notice last: an id outlives the section
    that defined it, and the reader is sent to a page that no longer says
    anything.
    """
    trouves = []
    for chemin in suivis:
        if chemin == REGISTRE:
            continue
        try:
            with open(chemin, encoding="utf-8") as flux:
                texte = flux.read()
        except (OSError, UnicodeDecodeError):
            continue
        for numero, ligne in enumerate(texte.splitlines(), 1):
            for trouve in sorted(set(IDENTIFIANT.findall(ligne))):
                if trouve not in connus:
                    trouves.append((chemin, numero, trouve))
    return trouves


def demo() -> None:
    import tempfile
    texte = (
        "[a](docs/tools.md) and [b](absent.md)\n"
        "```\n[c](in-a-fence.md)\n```\n"
        "[d]: SPEC.md\n"
        "[e]: nowhere.md\n"
        "[f](https://example.invalid/x) [g](#anchor) [h](docs/tools.md#part)\n"
    )
    attendus = [(1, "docs/tools.md"), (1, "absent.md"), (5, "SPEC.md"),
                (6, "nowhere.md"), (7, "#anchor"), (7, "docs/tools.md#part")]
    assert cibles(texte) == attendus, cibles(texte)
    # Relative to the document, and an anchor does not make a file exist.
    assert resoudre("docs/guide.md", "../SPEC.md") == "SPEC.md"
    assert resoudre("docs/guide.md", "tools.md#x") == "docs/tools.md"
    # A deliberately broken link is caught, and only that one.
    suivis = ["docs/tools.md", "SPEC.md", "tools/wpj_links.py"]
    with tempfile.TemporaryDirectory() as tmp:
        document = os.path.join(tmp, "doc.md")
        with open(document, "w", encoding="utf-8") as flux:
            flux.write(texte)
        avant = os.getcwd()
        os.chdir(tmp)
        try:
            trouves = casses(["doc.md"], suivis)
        finally:
            os.chdir(avant)
    assert [(n, c) for _, n, c in trouves] == [
        (1, "absent.md"), (6, "nowhere.md"), (7, "#anchor"),
        (7, "docs/tools.md#part")], trouves
    # A link to a directory that holds tracked files resolves.
    with tempfile.TemporaryDirectory() as tmp:
        document = os.path.join(tmp, "doc.md")
        with open(document, "w", encoding="utf-8") as flux:
            flux.write("[tools](tools/) and [t](tools)\n")
        avant = os.getcwd()
        os.chdir(tmp)
        try:
            assert casses(["doc.md"], suivis) == []
        finally:
            os.chdir(avant)
    # An id with no entry in the registry is caught, and only that one. The
    # fixture id is assembled here rather than written out: a literal would be
    # a citation, and this check reads its own source like any other file.
    absent = "FX" + "-99"
    with tempfile.TemporaryDirectory() as tmp:
        document = os.path.join(tmp, "doc.md")
        with open(document, "w", encoding="utf-8") as flux:
            flux.write(f"see {absent} and ACC-01\n")
        avant = os.getcwd()
        os.chdir(tmp)
        try:
            trouves = orphelins(["doc.md"], {"ACC-01"})
        finally:
            os.chdir(avant)
    assert trouves == [("doc.md", 1, absent)], trouves
    print("self-check ok: inline and reference links, fenced blocks ignored, "
          "local anchors checked, external links skipped, orphan finding ids caught",
          file=sys.stderr)


def main(argv: list[str] | None) -> int:
    suivis = fichiers_suivis()
    documents = argv or [f for f in suivis if f.endswith(".md")]
    trouves = casses(documents, suivis)
    if trouves:
        print(f"wpj_links: {len(trouves)} broken link(s) in tracked "
              "documents:", file=sys.stderr)
        for document, numero, cible in trouves:
            print(f"  {document}:{numero}  -> {cible}", file=sys.stderr)
        return 1
    connus = identifiants()
    if not connus:
        print(f"wpj_links: {len(documents)} documents, every local link "
              f"resolves — but {REGISTRE} is unreadable, so no finding id was "
              "checked", file=sys.stderr)
        return 1
    perdus = orphelins(argv or suivis, connus)
    if perdus:
        print(f"wpj_links: {len(perdus)} citation(s) of a finding id with no "
              f"entry in {REGISTRE}:", file=sys.stderr)
        for chemin, numero, trouve in perdus:
            print(f"  {chemin}:{numero}  {trouve}", file=sys.stderr)
        return 1
    print(f"wpj_links: {len(documents)} documents, every local link resolves; "
          f"{len(connus)} finding ids in the registry, every citation resolves",
          file=sys.stderr)
    return 0


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("fichiers", nargs="*",
                         help="documents to check; by default, every tracked "
                              ".md")
    args = parseur.parse_args(argv)
    demo()
    return main(args.fichiers)


if __name__ == "__main__":
    sys.exit(_cli())
