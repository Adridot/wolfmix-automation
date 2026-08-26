#!/usr/bin/env python3
"""Inspect JSON compatible avec le schéma wpj-toolkit (MIT), en local.

But : émettre la même forme de réponse que `POST /api/v1/inspect` de
WPJ Studio (`modelVersion`, `project`, `presets[]`, `fixtures`, `validation`,
`unknown_tlvs`) pour que les outils écrits contre ce schéma fonctionnent ici —
sans upload, hors ligne. Voir PROVENANCE.md.

Deux différences assumées, toutes deux additives :
- `fixtures.status` peut valoir "partial" (types 105/116 décodés) là où le
  schéma d'origine annonce "unsupported" ;
- `x_records` porte le décodage complet du codec, pour ne rien perdre.

Les attributions encore `hypothesized` (size/fade/phase) sont émises MAIS
signalées par une issue `unconfirmed_field_attribution` — jamais de valeur
présentée comme sûre. Champ absent = absent, jamais 0.

Usage :
  wpj_api.py fichier.wpj    inspect JSON sur stdout
  wpj_api.py                self-check sur le corpus
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpjlib
import wpj_codec

MODEL_VERSION = "1"
# clé codec → clé wpj-toolkit ; les trois dernières sont hypothesized
_FX_OUT = {"effet": "type", "vitesse": "speedPercent",
           "link_order": "linkOrder", "speed_source": "speedSource",
           "bpm_division": "bpmDivision",
           "f8": "sizePercent", "f6": "fadePercent", "f9": "phasePercent"}
_FX_HYPO = {"f8", "f6", "f9"}
_FX_SLOTS = {"beam_fx1": "beamFx1", "beam_fx2": "beamFx2",
             "color_fx1": "colorFx1", "color_fx2": "colorFx2",
             "move_fx1": "moveFx1", "move_fx2": "moveFx2"}
_PAD_OUT = {"rouge": "red", "vert": "green", "bleu": "blue", "blanc": "white",
            "ambre": "amber", "lime": "lime", "uv": "uv"}


def _issue(issues, severity, code, message):
    issues.append({"severity": severity, "code": code, "message": message})


def _fx(sub, hypo):
    """Sous-message FX → dict wpj-toolkit. Signale les clés hypothesized."""
    out = {}
    for src, dst in _FX_OUT.items():
        if src in sub:
            out[dst] = sub[src]
            if src in _FX_HYPO:
                hypo.add(dst)
    return out


def _preset(p, hypo):
    pid = p.get("id", 0)
    out = {"id": pid, "page": pid // 20 + 1, "slot": pid % 20 + 1,
           "rawPreserved": True}
    if "nom" in p:
        out["name"] = p["nom"]
    known = {}
    for src, dst in _FX_SLOTS.items():
        sub = p.get(src)
        if isinstance(sub, list) and sub and isinstance(sub[0], dict):
            fx = _fx(sub[0], hypo)
            if fx:
                known[dst] = fx
    for src, dst in (("positions", "positionIndexPerGroup"),
                     ("dimmers", "dimmerPerGroup")):
        if isinstance(p.get(src), list):
            known[dst] = p[src]
    if known:
        out["known"] = known
    return out


def inspect(path):
    data = open(path, "rb").read()
    issues, warnings = [], []
    checksum_ok = len(data) > 20 and data[:20] == hashlib.sha1(data[20:]).digest()
    _issue(issues, "info" if checksum_ok else "error",
           "checksum_ok" if checksum_ok else "checksum_mismatch",
           "SHA-1 header over bytes[20:] " + ("verified" if checksum_ok else "does not match"))

    try:
        w = wpjlib.Wpj.from_bytes(data, path)
    except ValueError as e:
        _issue(issues, "error", "unsupported_variant", str(e))
        return {"modelVersion": MODEL_VERSION, "project": {"warnings": warnings},
                "presets": [], "fixtures": {"status": "unsupported", "items": []},
                "validation": {"checksumOk": checksum_ok, "issues": issues},
                "unknown_tlvs": []}

    dec = [(t, wpj_codec.decode(t, p), len(p)) for t, p in w.records]
    by_type = {t: d for t, d, _ in dec}
    hypo = set()

    project = {"warnings": warnings}
    if "nom" in by_type.get(101, {}):
        project["name"] = by_type[101]["nom"]
    pads = by_type.get(135, {}).get("pads", [])
    if pads:
        project["known"] = {"colorFxPalette": {"pads": [
            {"index": i + 1, **{_PAD_OUT[k]: v for k, v in pad.items()
                                if k in _PAD_OUT}}
            for i, pad in enumerate(pads) if isinstance(pad, dict)]}}

    presets = [_preset(p, hypo) for p in by_type.get(165, {}).get("presets", [])
               if isinstance(p, dict)]
    ids = [p["id"] for p in presets]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        _issue(issues, "warning", "duplicate_preset_id", f"preset id {dup} appears twice")
    if hypo:
        _issue(issues, "warning", "unconfirmed_field_attribution",
               "field attribution still hypothesized: " + ", ".join(sorted(hypo)))

    items = [e for e in by_type.get(105, {}).get("patch", []) if isinstance(e, dict)]
    fixtures = {"status": "partial" if items else "unsupported", "items": items}

    unknown = [{"type": t, "payloadLength": n, "rawPreserved": True}
               for t, d, n in dec if set(d) == {"raw"}]

    return {"modelVersion": MODEL_VERSION, "project": project,
            "presets": presets, "fixtures": fixtures,
            "validation": {"checksumOk": checksum_ok, "issues": issues},
            "unknown_tlvs": unknown,
            "x_records": [{"type": t, **d} for t, d, _ in dec]}


def demo():
    files = wpjlib.corpus_files()
    if not files:
        return wpjlib.pas_de_corpus("wpj_api")
    ok = 0
    for path in files:
        r = inspect(path)
        assert r["modelVersion"] == MODEL_VERSION
        assert isinstance(r["validation"]["checksumOk"], bool)
        json.dumps(r)                                  # sérialisable
        if any(i["code"] == "unsupported_variant" for i in r["validation"]["issues"]):
            continue                                   # variantes B/C : hors périmètre
        assert r["validation"]["checksumOk"], f"{path} : SHA-1 invalide"
        assert r["presets"], f"{path} : aucun preset décodé"
        for p in r["presets"]:
            assert p["id"] == (p["page"] - 1) * 20 + (p["slot"] - 1)
        assert all(u["type"] not in wpj_codec.SCHEMAS for u in r["unknown_tlvs"]), \
            f"{path} : un type schématisé est retombé en unknown_tlv"
        ok += 1
    if not ok:
        return wpjlib.pas_de_corpus("wpj_api")
    print(f"self-check ok : inspect JSON valide sur {ok} fichiers variante A")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(inspect(sys.argv[1]), ensure_ascii=False, indent=1))
    else:
        demo()
