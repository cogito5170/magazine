"""Dimension A — typeface intrinsic morphology: the observed shape vector z_f.

z_f components are *observations*, not quality scores.  Their choice follows
the three morphological axes reported by Choi & Hyun (Sci. Rep. 14, 30820,
2024) – serif↔sans, basic↔decorative, light↔bold – plus width, contrast,
curvature, counters, terminals and glyph-to-glyph consistency.  Every
component has an explicit measurement rule below.

Counters: mean counter area / glyph box over glyphs that have counters, and
the share of glyphs with counters (a median would be 0 for most letter sets).

Terminals: Zhang–Suen skeleton; an end point is a skeleton pixel with one
8-neighbour.  Terminal width ratio = local stroke width at end points /
median stroke width of the glyph (flared > 1, tapered < 1).  Serif proxy =
skeleton end points per glyph on I, l, i, H, n, h, m, u when present (sans
designs have ~2 per stem, slab/bracketed serifs create extra short branches).
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..mathcore.glyph import curvature_samples, flatten, local_stroke_width, outline_bbox
from .glyphfeat import features_from_mask, outline_mask

SERIF_PROBE = set("IlHnhmuidL")
Z_KEYS = ["stroke_contrast", "width", "weight_stroke_em", "weight_ink", "curvature_mean",
          "curved_share", "counter_ratio", "counter_share", "terminal_width_ratio", "endpoints_per_glyph",
          "serif_probe_endpoints", "decorative_complexity", "corners_per_glyph", "stroke_cv", "contrast_cv"]


def zhang_suen(mask: np.ndarray, max_iter: int = 200) -> np.ndarray:
    img = np.pad(mask.astype(np.uint8), 1)
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            P = img
            p2, p3, p4 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:]
            p5, p6, p7 = P[2:, 2:], P[2:, 1:-1], P[2:, :-2]
            p8, p9 = P[1:-1, :-2], P[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(n.astype(int) for n in nb)
            seq = nb + [p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(int) for i in range(8))
            c = P[1:-1, 1:-1] == 1
            cond = c & (B >= 2) & (B <= 6) & (A == 1)
            if step == 0:
                cond &= (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                cond &= (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            if cond.any():
                img[1:-1, 1:-1][cond] = 0
                changed = True
        if not changed:
            break
    return img[1:-1, 1:-1].astype(bool)


def skeleton_endpoints(skel: np.ndarray) -> np.ndarray:
    P = np.pad(skel.astype(int), 1)
    n = sum(P[1 + dy:P.shape[0] - 1 + dy, 1 + dx:P.shape[1] - 1 + dx]
            for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0))
    return skel & (n == 1)


def glyph_morphology(contours, px_per_em: int = 128) -> Optional[dict]:
    om = outline_mask(contours, px_per_em)
    if om is None:
        return None
    mask, xo, bl = om
    f = features_from_mask(mask, xo, bl, px_per_em)
    if f is None:
        return None
    sw = local_stroke_width(mask)
    sk = zhang_suen(mask)
    ep = skeleton_endpoints(sk)
    med = float(np.median(sw[mask]))
    ep_w = sw[ep]
    polys = flatten(contours)
    x0, y0, x1, y1 = outline_bbox(polys)
    cs = curvature_samples(contours, y1 - y0)
    w = cs["weights"]
    curved = float(w[cs["values"] > 1.0].sum() / w.sum()) if w.sum() > 0 else None
    f.update({
        "endpoints": int(ep.sum()),
        "terminal_width_ratio": float(np.median(ep_w) / med) if ep_w.size and med > 0 else None,
        "curvature_mean": float(np.average(cs["values"], weights=w)) if w.sum() > 0 else None,
        "curved_share": curved,
        "corners": cs["corners"],
        "skeleton_px": int(sk.sum()),
    })
    return f


def morphology_vector(font, chars: list[str], px_per_em: int = 128) -> dict:
    """z_f for an OutlineFont over the given characters (letters preferred)."""
    per = {}
    for ch in chars:
        c = font.contours(ch)
        if c:
            g = glyph_morphology(c, px_per_em)
            if g:
                per[ch] = g
    if not per:
        return {"z": None, "n_glyphs": 0, "glyphs": {}}
    G = list(per.values())

    def med(k):
        v = [g[k] for g in G if g.get(k) is not None]
        return float(np.median(v)) if v else None

    def cv(k):
        v = np.array([g[k] for g in G if g.get(k) is not None], float)
        return float(v.std() / v.mean()) if v.size >= 2 and v.mean() != 0 else None

    probe = [per[c]["endpoints"] for c in per if c in SERIF_PROBE]
    z = {
        "stroke_contrast": med("C_stroke"),
        "width": med("aspect"),
        "weight_stroke_em": med("stroke_median_em"),
        "weight_ink": med("D_ink"),
        "curvature_mean": med("curvature_mean"),
        "curved_share": med("curved_share"),
        "counter_ratio": (float(np.mean([g["counter_ratio"] for g in G if (g.get("counter_ratio") or 0) > 0]))
                          if any((g.get("counter_ratio") or 0) > 0 for g in G) else 0.0),
        "counter_share": float(np.mean([(g.get("counter_ratio") or 0) > 0 for g in G])),
        "terminal_width_ratio": med("terminal_width_ratio"),
        "endpoints_per_glyph": med("endpoints"),
        "serif_probe_endpoints": float(np.median(probe)) if probe else None,
        "decorative_complexity": med("complexity"),
        "corners_per_glyph": med("corners"),
        "stroke_cv": cv("stroke_median_em"),
        "contrast_cv": cv("C_stroke"),
    }
    return {"z": z, "keys": Z_KEYS, "n_glyphs": len(G), "glyphs": per,
            "note": "observed shape descriptors; not aesthetic quality"}
