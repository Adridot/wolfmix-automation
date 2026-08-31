#!/usr/bin/env python3
"""Inspect JSON matching the wpj-toolkit schema (MIT), computed locally.

Goal: emit the same response shape as WPJ Studio's `POST /api/v1/inspect`
WPJ Studio (`modelVersion`, `project`, `presets[]`, `fixtures`, `validation`,
`unknown_tlvs`) so that tooling written against that schema works here — no
upload, offline. See PROVENANCE.md.

Two deliberate differences, both additive:
- `fixtures.status` may read "partial" (types 105/116 are decoded) where the
  original schema reports "unsupported";
- `x_records` carries the codec's full decode, so nothing is lost.

Phase, Size, Fade and Speed are measured (FX6-02/03, `SPEC.md` §5): they are
emitted under their own names, without reservation. An absent field is absent,
never 0.

Usage :
  wpj_api.py project.wpj    inspect JSON on stdout
  wpj_api.py                self-check over the corpus
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wpjlib
import wpj_codec

MODEL_VERSION = "1"
# codec key → wpj-toolkit key. The `fN` fallbacks went with FX6-02/03: they
# carried the retracted reading (f6 = fade, f9 = phase), which is wrong.
_FX_OUT = {"effect": "type", "speed": "speedPercent",
           "fade": "fadePercent", "phase": "phasePercent", "size": "sizePercent",
           "link_order": "linkOrder", "speed_source": "speedSource",
           "bpm_division": "bpmDivision"}
_FX_SLOTS = {"beam_fx1": "beamFx1", "beam_fx2": "beamFx2",
             "color_fx1": "colorFx1", "color_fx2": "colorFx2",
             "move_fx1": "moveFx1", "move_fx2": "moveFx2"}
_PAD_OUT = {"red": "red", "green": "green", "blue": "blue", "white": "white",
            "amber": "amber", "lime": "lime", "uv": "uv"}


def _issue(issues, severity, code, message):
    issues.append({"severity": severity, "code": code, "message": message})


def _fx(sub):
    """Sous-message FX → dict wpj-toolkit."""
    return {dst: sub[src] for src, dst in _FX_OUT.items() if src in sub}


def _preset(p):
    pid = p.get("id", 0)
    out = {"id": pid, "page": pid // 20 + 1, "slot": pid % 20 + 1,
           "rawPreserved": True}
    if "name" in p:
        out["name"] = p["name"]
    known = {}
    for src, dst in _FX_SLOTS.items():
        sub = p.get(src)
        if isinstance(sub, list) and sub and isinstance(sub[0], dict):
            fx = _fx(sub[0])
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

    project = {"warnings": warnings}
    if "name" in by_type.get(101, {}):
        project["name"] = by_type[101]["name"]
    pads = by_type.get(135, {}).get("pads", [])
    if pads:
        project["known"] = {"colorFxPalette": {"pads": [
            {"index": i + 1, **{_PAD_OUT[k]: v for k, v in pad.items()
                                if k in _PAD_OUT}}
            for i, pad in enumerate(pads) if isinstance(pad, dict)]}}

    presets = [_preset(p) for p in by_type.get(165, {}).get("presets", [])
               if isinstance(p, dict)]
    ids = [p["id"] for p in presets]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        _issue(issues, "warning", "duplicate_preset_id", f"preset id {dup} appears twice")

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
        json.dumps(r)                                  # serialisable
        if any(i["code"] == "unsupported_variant" for i in r["validation"]["issues"]):
            continue                                   # variants B/C: out of scope
        assert r["validation"]["checksumOk"], f"{path} : SHA-1 invalide"
        assert r["presets"], f"{path}: no preset decoded"
        for p in r["presets"]:
            assert p["id"] == (p["page"] - 1) * 20 + (p["slot"] - 1)
        assert all(u["type"] not in wpj_codec.SCHEMAS for u in r["unknown_tlvs"]), \
            f"{path}: a schema-backed type fell back to unknown_tlv"
        ok += 1
    if not ok:
        return wpjlib.pas_de_corpus("wpj_api")
    print(f"self-check ok: valid inspect JSON on {ok} variant-A files")


def _cli(argv=None):
    import argparse
    parseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parseur.add_argument("projet", nargs="?",
                         help="emit the wpj-toolkit inspect JSON; "
                              "with no argument, self-check")
    args = parseur.parse_args(argv)
    if args.projet is None:
        demo()
        return 0
    print(json.dumps(inspect(args.projet), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
