#!/usr/bin/env python3
"""Conduite du chantier gobos : où en est le dossier de travail, et après ?

Les six étapes de `docs/gobo-icons.md` sont portées par les outils du dépôt.
Ce qui n'appartenait à personne, ce sont les gardes *entre* les étapes — et
c'est un pas sauté qui coûte cher sur du matériel réel. Cet outil ne patche
rien, ne parle à aucun appareil et n'écrit aucun fichier : il regarde un
dossier de travail et refuse d'annoncer l'étape suivante tant qu'une garde est
rouge.

  gobo_run.py DOSSIER    l'état du chantier, puis la commande suivante
  gobo_run.py            self-check

Quatre gardes, celles qu'aucun outil ne tenait :

  0 sauvegarde    le bundle flash copié HORS du dossier WTOOLS — que WTOOLS
                  réécrit à chaque mise à jour — sha256 identiques au vivant
  1 silhouettes   au moins un `gobo*.png` dans le dossier
  2 flash patché  présent et de la longueur de l'original : les pointeurs de
                  la table sont absolus, une longueur qui bouge décale tout
  3 planche       rendue APRÈS le flash patché, donc relue depuis lui et non
                  depuis les sources — c'est la seule preuve avant l'upload

Le reste est déjà refusé par l'outil qui le possède : `Open` et ses 96 entrées
par `gobo_write.py`, les noms > 19 octets et la roue portée par un second
groupe par `wpj_show.py`. Ici on ne recalcule rien, on ordonne.

Exit 2 = garde rouge, l'étape suivante est refusée. Le dossier de travail est
celui de l'opérateur : silhouettes, flash patché et planche sont les données de
sa lyre et ne rentrent jamais dans le dépôt (LEGAL.md) — un dossier sous
l'arborescence du dépôt est refusé.
"""
import glob
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gobo_library import find_flash

DEPOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAUVEGARDE, PATCHE, PLANCHE = "backup", "flash-custom.bin", "planche.png"


def sha256(chemin):
    empreinte = hashlib.sha256()
    with open(chemin, "rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 20), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


def empreintes(dossier):
    """{nom: sha256} des fichiers directement sous `dossier`."""
    noms = sorted(os.listdir(dossier))
    return {n: sha256(os.path.join(dossier, n)) for n in noms
            if os.path.isfile(os.path.join(dossier, n))}


def sous(chemin, parent):
    parent = os.path.realpath(parent)
    return os.path.realpath(chemin).startswith(parent + os.sep)


def garde_sauvegarde(sauve, bundle):
    if not os.path.isdir(sauve):
        return False, f"{sauve} absent"
    if sous(sauve, bundle) or os.path.realpath(sauve) == os.path.realpath(bundle):
        return False, ("sous le dossier WTOOLS : la prochaine mise à jour "
                       "la réécrira")
    vivant, copie = empreintes(bundle), empreintes(sauve)
    ecarts = [n for n in vivant if copie.get(n) != vivant[n]]
    if ecarts:
        return False, (f"{len(ecarts)} fichier(s) absents ou différents du "
                       f"bundle vivant : {', '.join(ecarts[:3])}")
    return True, f"{len(vivant)} fichiers, {len(vivant)} sha256 identiques"


def gardes(travail, flash):
    """[(étiquette, vert, détail)] dans l'ordre des étapes de la recette."""
    bundle = os.path.dirname(flash)
    sauve = os.path.join(travail, SAUVEGARDE)
    patche = os.path.join(travail, PATCHE)
    planche = os.path.join(travail, PLANCHE)

    etats = [("0 sauvegarde",) + garde_sauvegarde(sauve, bundle)]

    silhouettes = glob.glob(os.path.join(travail, "gobo*.png"))
    etats.append(("1 silhouettes", bool(silhouettes),
                  f"{len(silhouettes)} fichier(s) gobo*.png"
                  if silhouettes else "aucun gobo*.png dans le dossier"))

    if not os.path.isfile(patche):
        etats.append(("2 flash patché", False, f"{PATCHE} absent"))
    elif os.path.getsize(patche) != os.path.getsize(flash):
        etats.append(("2 flash patché", False,
                      f"{os.path.getsize(patche)} octets contre "
                      f"{os.path.getsize(flash)} à l'original : les pointeurs "
                      "sont absolus, la longueur ne doit pas bouger"))
    else:
        etats.append(("2 flash patché", True,
                      f"{os.path.getsize(patche)} octets, longueur inchangée"))

    if not os.path.isfile(planche):
        etats.append(("3 planche", False, f"{PLANCHE} absente"))
    elif not os.path.isfile(patche):
        etats.append(("3 planche", False, "rendue sans flash patché"))
    elif os.path.getmtime(planche) < os.path.getmtime(patche):
        etats.append(("3 planche", False,
                      "plus ancienne que le flash patché : elle ne montre pas "
                      "ce qui partira dans l'appareil"))
    else:
        etats.append(("3 planche", True, "rendue après le flash patché"))
    return etats


def suite(etats, travail, flash):
    """Le texte de l'étape suivante : la première garde rouge, ou l'appareil."""
    bundle = os.path.dirname(flash)
    patche = os.path.join(travail, PATCHE)
    rouge = next((e for e in etats if not e[1]), None)
    if rouge is None:
        return ("planche validée par l'opérateur ? alors les préconditions "
                "appareil, puis l'upload à la main :\n"
                "  python3 tools/wolfmix.py profiles | tail -3   "
                "# lecture complète, sinon redémarrer le W1\n"
                "  python3 tools/wolfmix.py settings             "
                "# wlinkActivated doit être false\n"
                "  # puis research/flash-gobo-plan.md : secteur, projet "
                "enregistré, wtoolsMode=2\n"
                "  # noms et ordre ensuite, si besoin : docs/gobo-icons.md §6")
    etape = rouge[0][0]
    if etape == "0":
        return ("refus : pas de sauvegarde vérifiée, pas de patch ni "
                "d'upload.\n"
                f'  cp -R "{bundle}" "{os.path.join(travail, SAUVEGARDE)}"\n'
                f"  python3 tools/gobo_run.py {travail}")
    if etape == "1":
        return ("photographier la roue puis générer les silhouettes — le "
                "prompt est dans docs/gobo-icons.md §1-2.\n"
                f"  enregistrer gobo01.png, gobo02.png… dans {travail}")
    if etape == "2":
        return ("lire la palette, puis patcher une COPIE — jamais l'entrée "
                "`Open`, l'outil la refuse.\n"
                "  python3 tools/gobo_library.py palette VOTRE-PROJET.wpj\n"
                f"  python3 tools/gobo_write.py patch {patche} \\\n"
                f"      342=mask:{os.path.join(travail, 'gobo01.png')}")
    return ("rendre la planche DEPUIS le fichier patché, et la faire valider "
            "avant tout upload.\n"
            f"  WOLFMIX_FLASH={patche} python3 tools/gobo_library.py \\\n"
            f"      sheet {os.path.join(travail, PLANCHE)} 342,343")


def rapport(travail, flash):
    etats = gardes(travail, flash)
    largeur = max(len(e[0]) for e in etats)
    lignes = [f"dossier de travail  {travail}",
              f"flash d'origine     {flash}", ""]
    lignes += [f"{e[0]:<{largeur}}  {'OK ' if e[1] else 'NON'}  {e[2]}"
               for e in etats]
    lignes += ["", suite(etats, travail, flash)]
    return "\n".join(lignes), all(e[1] for e in etats)


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        bundle = os.path.join(tmp, "wm-fw-bundle-2.0.18")
        travail = os.path.join(tmp, "gobos")
        os.makedirs(bundle)
        os.makedirs(travail)
        flash = os.path.join(bundle, "wolfmixFlash.bin")
        for nom, corps in (("wolfmixFlash.bin", b"\x01" * 4096),
                           ("wolfmixFlash-reset.bin", b"\x02" * 16),
                           ("firmware.bin", b"\x03" * 16),
                           ("bundle.json", b"{}")):
            open(os.path.join(bundle, nom), "wb").write(corps)

        def etat(nom):
            return dict((e[0], e[1]) for e in gardes(travail, flash))[nom]

        assert etat("0 sauvegarde") is False, "sauvegarde absente = rouge"
        assert "cp -R" in suite(gardes(travail, flash), travail, flash)

        # Une sauvegarde restée dans le dossier WTOOLS n'en est pas une.
        dedans = os.path.join(bundle, "backup")
        os.makedirs(dedans)
        assert garde_sauvegarde(dedans, bundle)[0] is False

        sauve = os.path.join(travail, SAUVEGARDE)
        os.makedirs(sauve)
        for nom in os.listdir(bundle):
            chemin = os.path.join(bundle, nom)
            if os.path.isfile(chemin):
                open(os.path.join(sauve, nom), "wb").write(
                    open(chemin, "rb").read())
        assert etat("0 sauvegarde") is True, "copie fidèle = vert"

        # Un octet qui bouge dans la copie casse la garde : c'est tout l'objet
        # des empreintes, une copie partielle passerait sinon inaperçue.
        open(os.path.join(sauve, "firmware.bin"), "wb").write(b"\x04" * 16)
        assert etat("0 sauvegarde") is False, "sha256 différent = rouge"
        open(os.path.join(sauve, "firmware.bin"), "wb").write(b"\x03" * 16)

        assert etat("1 silhouettes") is False
        open(os.path.join(travail, "gobo01.png"), "wb").write(b"x")
        assert etat("1 silhouettes") is True

        assert etat("2 flash patché") is False
        patche = os.path.join(travail, PATCHE)
        open(patche, "wb").write(b"\x01" * 4095)
        assert etat("2 flash patché") is False, "longueur différente = rouge"
        open(patche, "wb").write(b"\x01" * 4096)
        assert etat("2 flash patché") is True

        # La planche doit être postérieure au flash patché, sinon elle montre
        # les sources et non ce qui partira dans l'appareil.
        planche = os.path.join(travail, PLANCHE)
        open(planche, "wb").write(b"png")
        os.utime(planche, (0, os.path.getmtime(patche) - 10))
        assert etat("3 planche") is False, "planche antérieure = rouge"
        os.utime(planche, (0, os.path.getmtime(patche) + 10))
        assert etat("3 planche") is True

        texte, vert = rapport(travail, flash)
        assert vert and "wlinkActivated" in texte and "profiles" in texte
    print("ok — 4 gardes, chacune rouge puis verte, refus en tête de rapport")


def main(argv):
    if len(argv) < 2:
        self_test()
        return 0
    travail = os.path.abspath(os.path.expanduser(argv[1]))
    if travail == DEPOT or sous(travail, DEPOT):
        print("refus : le dossier de travail est sous le dépôt. Silhouettes, "
              "flash patché et planche sont les données de votre lyre et "
              "restent dehors (LEGAL.md) — ~/gobos par exemple.",
              file=sys.stderr)
        return 2
    if not os.path.isdir(travail):
        print(f"refus : {travail} n'est pas un dossier", file=sys.stderr)
        return 2
    flash = find_flash(os.environ.get("WOLFMIX_FLASH"))
    if not flash:
        print("aucune image flash locale (WTOOLS n'a jamais téléchargé le "
              "firmware) — rien à conduire", file=sys.stderr)
        return 0
    texte, vert = rapport(travail, flash)
    print(texte)
    return 0 if vert else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
