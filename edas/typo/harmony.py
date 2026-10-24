"""Korean–Latin geometry profiles and the harmony feature vector h.

h = [ΔT_s, ΔD_ink, ΔH_visual, ΔB_baseline, ΔC_stroke, ΔR_spacing]

Normalisation (documented, fixed):
* ΔT_s, ΔD_ink, ΔC_stroke, ΔR_spacing: standardised mean difference
  (Hangul − Latin) / pooled SD of the glyph-level (or gap-level) samples
  (Cohen's d).  None when either side has < 2 samples or pooled SD = 0.
* ΔH_visual: (H_K − H_cap,E) / H_cap,E, H_K = median Hangul ink height (em),
  H_cap,E = median uppercase ink height (em).  x-height variant in details.
* ΔB_baseline: (bottom_K − bottom_E) / H_cap,E, bottoms = median ink bottom
  (em, relative to the baseline) of Hangul and of flat-bottom capitals
  (flat-bottom lowercase h i k l m n r x z when no such capital is used).
  If no capital is used, H_cap,E is unavailable and the vertical terms are None.

h is a *description* of the pair.  Neither small nor large values are
assumed to be better: similar pairings and deliberate contrast are both
described by the same vector, and appropriateness requires a trained model.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Callable, Optional

import numpy as np

from .scripts import char_class, hangul_structure

FLAT_BOTTOM_CAPS = set("BDEFHIKLMNPRTXZ")
FLAT_BOTTOM_LOWER = set("hiklmnrxz")
X_HEIGHT_CHARS = set("acemnorsuvwxz")
GLYPH_FEATURES = ("T_s", "C_stroke", "aspect", "D_ink", "counter_ratio", "cg_x_rel", "cg_y_rel",
                  "height_em", "top_em", "bottom_em", "stroke_median_em", "complexity")


def stratified_hangul_sample(freq: Counter, per_stratum: int) -> dict[int, list[str]]:
    """Most frequent syllables of each of the 6 shape types."""
    strata: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for ch, n in freq.items():
        hs = hangul_structure(ch)
        if hs:
            strata[hs["type"]].append((ch, n))
    return {t: [c for c, _ in sorted(v, key=lambda x: (-x[1], x[0]))[:per_stratum]] for t, v in strata.items()}


def _median(vals):
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None


def hangul_profile(freq: Counter, get: Callable[[str], Optional[dict]], per_stratum: int) -> Optional[dict]:
    """Stratified Hangul geometry: per-type medians and a usage-weighted aggregate."""
    sample = stratified_hangul_sample(freq, per_stratum)
    if not sample:
        return None
    usage: Counter = Counter()
    for ch, n in freq.items():
        hs = hangul_structure(ch)
        if hs:
            usage[hs["type"]] += n
    strata, glyphs, by_comp = {}, [], defaultdict(list)
    for t, chars in sorted(sample.items()):
        feats = []
        for ch in chars:
            f = get(ch)
            if f is None:
                continue
            feats.append(f)
            glyphs.append(f)
            by_comp[hangul_structure(ch)["components"]].append(f["D_ink"])
        if feats:
            strata[t] = {k: _median([f.get(k) for f in feats]) for k in GLYPH_FEATURES}
            strata[t]["n"] = len(feats)
            strata[t]["usage"] = usage[t]
    if not strata:
        return None
    tot = sum(strata[t]["usage"] for t in strata)
    agg = {}
    for k in GLYPH_FEATURES:
        num = [(strata[t][k], strata[t]["usage"]) for t in strata if strata[t][k] is not None]
        agg[k] = float(sum(v * w for v, w in num) / sum(w for _, w in num)) if num and tot else None
    return {"strata": strata, "aggregate": agg, "n_glyphs": len(glyphs),
            "strata_covered": sorted(strata), "glyphs": glyphs,
            "ink_by_components": {int(k): v for k, v in sorted(by_comp.items())}}


def latin_profile(freq: Counter, get: Callable[[str], Optional[dict]], per_class: int) -> Optional[dict]:
    classes: dict[str, list[str]] = defaultdict(list)
    for ch, _ in freq.most_common():
        c = char_class(ch)
        if c in ("latin_upper", "latin_lower", "digit", "punct") and len(classes[c]) < per_class:
            classes[c].append(ch)
    if not classes:
        return None
    out, letters = {}, []
    caps_top, caps_bottom, xh, low_bottom = [], [], [], []
    for c, chars in classes.items():
        feats = []
        for ch in chars:
            f = get(ch)
            if f is None:
                continue
            feats.append(f)
            if c in ("latin_upper", "latin_lower"):
                letters.append(f)
            if c == "latin_upper":
                caps_top.append(f["top_em"])
                if ch in FLAT_BOTTOM_CAPS:
                    caps_bottom.append(f["bottom_em"])
            if ch in X_HEIGHT_CHARS:
                xh.append(f["top_em"])
            if ch in FLAT_BOTTOM_LOWER:
                low_bottom.append(f["bottom_em"])
        if feats:
            out[c] = {k: _median([f.get(k) for f in feats]) for k in GLYPH_FEATURES}
            out[c]["n"] = len(feats)
    return {"classes": out, "cap_height_em": _median(caps_top), "x_height_em": _median(xh),
            "baseline_em": _median(caps_bottom) if caps_bottom else _median(low_bottom),
            "baseline_probe": "flat-bottom capitals" if caps_bottom else ("flat-bottom lowercase" if low_bottom else None),
            "glyphs": letters, "n_letters": len(letters)}


def cohens_d(a, b) -> Optional[float]:
    a = np.asarray([x for x in a if x is not None], float)
    b = np.asarray([x for x in b if x is not None], float)
    if a.size < 2 or b.size < 2:
        return None
    sp = np.sqrt(((a.size - 1) * a.var(ddof=1) + (b.size - 1) * b.var(ddof=1)) / (a.size + b.size - 2))
    if sp == 0:
        return None
    return float((a.mean() - b.mean()) / sp)


def harmony_vector(K: dict, E: dict, gaps_K=None, gaps_E=None) -> dict:
    kg, eg = K["glyphs"], E["glyphs"]
    cap = E.get("cap_height_em")
    hK = _median([g["height_em"] for g in kg])
    bK = _median([g["bottom_em"] for g in kg])
    bE = E.get("baseline_em")
    h = {
        "dT_s": cohens_d([g["T_s"] for g in kg], [g["T_s"] for g in eg]),
        "dD_ink": cohens_d([g["D_ink"] for g in kg], [g["D_ink"] for g in eg]),
        "dH_visual": (hK - cap) / cap if (hK is not None and cap) else None,
        "dB_baseline": (bK - bE) / cap if (bK is not None and bE is not None and cap) else None,
        "dC_stroke": cohens_d([g["C_stroke"] for g in kg], [g["C_stroke"] for g in eg]),
        "dR_spacing": cohens_d(gaps_K or [], gaps_E or []),
    }
    raw = {
        "T_s": (_median([g["T_s"] for g in kg]), _median([g["T_s"] for g in eg])),
        "D_ink": (_median([g["D_ink"] for g in kg]), _median([g["D_ink"] for g in eg])),
        "H_visual_em": (hK, cap),
        "x_height_em": E.get("x_height_em"),
        "hangul_over_x_height": (hK / E["x_height_em"]) if (hK and E.get("x_height_em")) else None,
        "bottom_em": (bK, bE),
        "C_stroke": (_median([g["C_stroke"] for g in kg]), _median([g["C_stroke"] for g in eg])),
        "spacing_gap_over_size": (_median(gaps_K or []), _median(gaps_E or [])),
        "visual_center_em": (_median([g["cg_y_em"] for g in kg]), _median([g["cg_y_em"] for g in eg])),
        "stroke_em": (_median([g["stroke_median_em"] for g in kg]), _median([g["stroke_median_em"] for g in eg])),
    }
    return {"h": h, "raw_pairs_K_E": raw,
            "order": ["dT_s", "dD_ink", "dH_visual", "dB_baseline", "dC_stroke", "dR_spacing"],
            "interpretation": "description only; no direction is assumed to be better"}


def ink_complexity_relation(profile: dict) -> Optional[dict]:
    """OLS slope of glyph ink density on Hangul component count (validation item)."""
    pts = [(k, v) for k, vs in profile.get("ink_by_components", {}).items() for v in vs if v is not None]
    if len(pts) < 3 or len({k for k, _ in pts}) < 2:
        return None
    x = np.array([p[0] for p in pts], float)
    y = np.array([p[1] for p in pts], float)
    slope, icpt = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else None
    return {"slope_per_component": float(slope), "intercept": float(icpt), "pearson_r": r, "n": len(pts),
            "mean_by_components": {int(k): float(np.mean(v)) for k, v in profile["ink_by_components"].items()}}
