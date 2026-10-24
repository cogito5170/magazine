"""Alternative font candidates (BK13) from installed fonts.

Availability = installed file + full cmap coverage of the characters used;
licence/embedding fields are read from the font itself.  Geometry is
measured through the same outline route as the PDF fonts
(``FileFontOutlines``); fonts that cannot take that route (CFF-flavoured
OTF) are listed as 'not measured' rather than approximated.
The lists are ordered by geometric distance for browsing, never by quality.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np

from .catalog import FontFace, scan_system_fonts
from .glyphfeat import features_from_mask, outline_mask
from .harmony import harmony_vector, hangul_profile, latin_profile
from .outlines import FileFontOutlines, UnsupportedFont
from .scripts import char_class

_CATALOG: Optional[list[FontFace]] = None


def catalog() -> list[FontFace]:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = scan_system_fonts()
    return _CATALOG


def _getter(fo: FileFontOutlines, px: int):
    cache = {}

    def get(ch):
        if ch not in cache:
            c = fo.contours(ch)
            om = outline_mask(c, px) if c else None
            cache[ch] = features_from_mask(*om, px) if om else None
        return cache[ch]
    return get


def _dedupe(faces):
    seen, out = set(), []
    for f in faces:
        k = (f.family, f.subfamily)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def candidate_pairs(dctx, bdoc, max_latin: int = 25, max_korean: int = 8) -> dict:
    px = int(dctx.cfg["typography"]["glyph_raster_px"])
    bc = dctx.cfg["typography"]["bilingual"]
    kfreq, efreq = Counter(), Counter()
    for fk, fr in bdoc.freq.items():
        for ch, n in fr.items():
            cls = char_class(ch)
            if cls == "hangul":
                kfreq[ch] += n
            elif cls in ("latin_upper", "latin_lower", "digit"):
                efreq[ch] += n
    ktext, etext = "".join(kfreq), "".join(efreq)
    faces = catalog()
    kc = _dedupe([f for f in faces if ktext and f.coverage(ktext) == 1.0])[:max_korean]
    ec = _dedupe([f for f in faces if etext and f.coverage(etext) == 1.0 and f.subfamily in
                  ("Regular", "Bold", "Book", "Medium", "Roman")])[:max_latin]
    probe_chars = ktext + etext + "HxIlOo"
    meas, unsupported = {}, []
    for f in kc + ec:
        key = f"{f.family} {f.subfamily}".strip()
        try:
            fo = FileFontOutlines(f.path, f.index, chars=probe_chars, name=key)
        except UnsupportedFont as e:
            unsupported.append({"font": key, "reason": str(e)[:160], **f.to_dict()})
            continue
        get = _getter(fo, px)
        meas[key] = {"face": f.to_dict(),
                     "K": hangul_profile(kfreq, get, int(bc["hangul_per_stratum"])) if f in kc else None,
                     "E": latin_profile(efreq, get, int(bc["latin_per_class"])) if f in ec else None}
    pairs = []
    for kf, kp in bdoc.K.items():          # current Korean font x candidate Latin fonts
        for name, m in meas.items():
            if m["E"] and m["E"]["n_letters"] >= 2:
                pairs.append({"korean": kf, "korean_source": "pdf", "latin": name, "latin_source": "installed",
                              **harmony_vector(kp, m["E"])})
    for ef, ep in bdoc.E.items():          # candidate Korean fonts x current Latin font
        for name, m in meas.items():
            if m["K"]:
                pairs.append({"korean": name, "korean_source": "installed", "latin": ef, "latin_source": "pdf",
                              **harmony_vector(m["K"], ep)})

    def norm(p):
        v = [x for x in p["h"].values() if x is not None]
        return float(np.sqrt(np.mean(np.square(v)))) if v else None

    for p in pairs:
        p["h_rms"] = norm(p)
        for k in ("raw_pairs_K_E",):
            p.pop(k, None)
    valid = [p for p in pairs if p["h_rms"] is not None]
    return {
        "available_fonts": {k: m["face"] for k, m in meas.items()},
        "not_measured": unsupported,
        "pairs": pairs,
        "geometrically_similar": [f"{p['korean']} + {p['latin']}" for p in sorted(valid, key=lambda p: p["h_rms"])[:8]],
        "geometrically_contrasting": [f"{p['korean']} + {p['latin']}" for p in
                                      sorted(valid, key=lambda p: -p["h_rms"])[:8]],
        "note": "ordering by RMS of h is for browsing; neither similar nor contrasting pairs are assumed better",
        "measurement_route": "installed fonts embedded into a temporary PDF; outlines read by PDFium; "
                             "identical rasteriser as for PDF fonts",
    }
