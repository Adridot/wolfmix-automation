#!/usr/bin/env python3
"""The gate between the ledger and the specification.

`research/evidence.md` is written next to the measurement; `SPEC.md` is written
afterwards. The second is allowed to **lag** — it says so, with an evidence
cutoff — but it is not allowed to **contradict**. Three things are checked, and
each is a refusal rather than a warning:

1. **Every `SPEC §` the ledger points at exists.** A reference to a section
   that was renumbered or removed sends the reader nowhere, which is the same
   failure as a dead link.
2. **Nothing in the ledger is newer than the cutoff without being declared
   pending.** Add a finding dated after `SPEC.md`'s cutoff and the gate fails
   until either the specification absorbs it or the pending table names it. A
   listed gap is a known gap; an unlisted one is a lie of omission.
3. **A refuted or retracted finding is never cited as support.** If `SPEC.md`
   names such an id, the sentence around it must say so — `retracted`,
   `refuted` or `withdrawn`. This is the contradiction that matters: the
   specification standing on a measurement the ledger has taken back.

Usage:
  wpj_evidence.py          check the ledger against the specification
  wpj_evidence.py --list   the ledger as parsed, one line per finding
"""
import os
import re
import sys

REGISTRE = "research/evidence.md"
SPEC = "SPEC.md"

LIGNE = re.compile(r"^\|\s*([A-Z][^|]*?)\s*\|\s*(\d{4}-\d{2}-\d{2}|[^|]*?)\s*\|"
                   r"\s*(.*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$")
IDENTIFIANT = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-[0-9]{2})\b")
SECTION = re.compile(r"§(\d+(?:\.\d+[a-z]?)?)")
TITRE = re.compile(r"^#{2,3} (\d+(?:\.\d+[a-z]?)?)[.\s]", re.M)
COUPURE = re.compile(r"Evidence cutoff\s*—\s*(\d{4}-\d{2}-\d{2})")
REPRISE = ("retract", "refut", "withdraw", "réfut", "rétract")
# A status that keeps one of these has something left standing, so the id is
# citable: only a finding taken back **in full** may not be leaned on.
DEBOUT = ("device-confirmed", "validated", "correlated", "observed")


def entrees(chemin=REGISTRE):
    """[(ids, date, status, sections)] — one per row of the register."""
    out = []
    with open(chemin, encoding="utf-8") as flux:
        for ligne in flux:
            trouve = LIGNE.match(ligne)
            if not trouve:
                continue
            colonne, date, _, statut, spec = trouve.groups()
            ids = IDENTIFIANT.findall(colonne)
            if not ids or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                continue
            out.append((ids, date, statut, SECTION.findall(spec)))
    return out


def sections(chemin=SPEC):
    with open(chemin, encoding="utf-8") as flux:
        return set(TITRE.findall(flux.read()))


def coupure(chemin=SPEC):
    """The declared evidence cutoff, or None when there is none."""
    with open(chemin, encoding="utf-8") as flux:
        trouve = COUPURE.search(flux.read())
    return trouve.group(1) if trouve else None


def en_attente(chemin=SPEC):
    """The ids the specification declares pending, under its cutoff heading."""
    with open(chemin, encoding="utf-8") as flux:
        texte = flux.read()
    debut = texte.find("Pending consolidation")
    if debut < 0:
        return set()
    fin = texte.find("\n## ", debut)
    return set(IDENTIFIANT.findall(texte[debut:fin if fin > 0 else len(texte)]))


def reprise(statut):
    """True when the status takes the finding back and leaves nothing."""
    bas = statut.lower()
    return (any(mot in bas for mot in REPRISE)
            and not any(mot in bas for mot in DEBOUT))


def cites_par_spec(chemin=SPEC):
    """{id: [(line, paragraph)]} for every finding id the spec names.

    The paragraph, not the line: a sentence that says "refuted as written"
    wraps, and a citation three lines below it is still inside the disclaimer.
    """
    with open(chemin, encoding="utf-8") as flux:
        texte = flux.read()
    trouves, debut, numero = {}, 0, 1
    for paragraphe in re.split(r"\n[ \t]*\n", texte):
        for trouve in set(IDENTIFIANT.findall(paragraphe)):
            decalage = paragraphe.index(trouve)
            ligne = numero + paragraphe.count("\n", 0, decalage)
            trouves.setdefault(trouve, []).append((ligne, paragraphe))
        numero += paragraphe.count("\n") + 2
        debut += len(paragraphe)
    return trouves


def ecarts(registre=REGISTRE, spec=SPEC):
    """Every disagreement, as readable lines."""
    problemes = []
    lignes, connues = entrees(registre), sections(spec)
    for ids, date, _statut, refs in lignes:
        for ref in refs:
            if ref not in connues:
                problemes.append(
                    f"{registre}: {'/'.join(ids)} points at SPEC §{ref}, "
                    "which does not exist")
    limite, attente = coupure(spec), en_attente(spec)
    if limite is None:
        problemes.append(f"{spec}: no evidence cutoff declared")
    else:
        for ids, date, _statut, _refs in lignes:
            if date > limite and not any(i in attente for i in ids):
                problemes.append(
                    f"{registre}: {'/'.join(ids)} is dated {date}, after the "
                    f"{spec} cutoff {limite}, and is not in the pending list")
    cites = cites_par_spec(spec)
    debout = {i for ids, _d, statut, _r in lignes if not reprise(statut)
              for i in ids}
    for ids, _date, statut, _refs in lignes:
        if not reprise(statut):
            continue
        for identifiant in ids:
            if identifiant in debout:
                continue          # another row of the same id still stands
            for numero, paragraphe in cites.get(identifiant, []):
                if not any(mot in paragraphe.lower() for mot in REPRISE):
                    problemes.append(
                        f"{spec}:{numero}: cites {identifiant}, which the "
                        f"ledger records as \"{statut}\", without saying so")
    return problemes


def demo():
    import tempfile
    # The fixture ids are assembled rather than written out: a literal would
    # be a citation, and `wpj_links.py` reads this file like any other.
    bon, tard, mort = ("AAA" + "-01"), ("BBB" + "-02"), ("CCC" + "-03")
    registre = ("| id | date | what | status | SPEC § |\n"
                "|---|---|---|---|---|\n"
                f"| {bon} | 2026-01-01 | did a thing | device-confirmed | §2 |\n"
                f"| {tard} | 2026-09-09 | later | observed | §2 |\n"
                f"| {mort} | 2026-01-01 | wrong | refuted | §9 |\n")
    spec = ("## 2. A section\n\nEvidence cutoff — 2026-01-31\n\n"
            "Pending consolidation\n\n" + f"| {tard} | missing |\n\n"
            "## 3. Another\n\n" + f"{bon} says so, and {mort} too.\n")
    with tempfile.TemporaryDirectory() as tmp:
        r = os.path.join(tmp, "r.md"); s = os.path.join(tmp, "s.md")
        open(r, "w", encoding="utf-8").write(registre)
        open(s, "w", encoding="utf-8").write(spec)
        lignes = entrees(r)
        assert [i for ids, *_ in lignes for i in ids] == [bon, tard, mort], lignes
        assert coupure(s) == "2026-01-31"
        assert en_attente(s) == {tard}
        trouves = ecarts(r, s)
        assert len(trouves) == 2, trouves
        assert "§9, which does not exist" in trouves[0], trouves[0]
        assert mort in trouves[1] and "refuted" in trouves[1], trouves[1]
        # The late one is past the cutoff but declared pending: fine.
        assert not any(tard in p for p in trouves), trouves
        # Saying it is retracted at the point of citation clears the third.
        open(s, "w", encoding="utf-8").write(
            spec.replace(f"and {mort} too", f"and {mort}, retracted, too"))
        assert len(ecarts(r, s)) == 1, ecarts(r, s)
    print("self-check ok: absent section, finding past the cutoff, and a "
          "refuted finding cited as support", file=sys.stderr)


def main(argv):
    if "--list" in argv:
        for ids, date, statut, refs in entrees():
            spec = ", ".join(f"§{r}" for r in refs) or "—"
            print(f"{'/'.join(ids):24s} {date}  {statut:34s} {spec}")
        return 0
    problemes = ecarts()
    if problemes:
        print(f"wpj_evidence: {len(problemes)} disagreement(s) between "
              f"{REGISTRE} and {SPEC}:", file=sys.stderr)
        for probleme in problemes:
            print(f"  {probleme}", file=sys.stderr)
        return 1
    lignes = entrees()
    print(f"wpj_evidence: {len(lignes)} dated findings, cutoff {coupure()}, "
          f"{len(en_attente())} declared pending — no contradiction",
          file=sys.stderr)
    return 0


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("--list", action="store_true", dest="lister",
                         help="print the ledger as parsed instead of checking")
    args = parseur.parse_args(argv)
    demo()
    return main(["--list"] if args.lister else [])


if __name__ == "__main__":
    sys.exit(_cli())
