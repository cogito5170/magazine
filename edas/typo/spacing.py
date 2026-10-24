"""Dimension B — spacing and optical quality of set words.

For a word as set in the PDF (chars with origins) and its font outlines:
* applied adjustment per pair = actual advance − nominal advance (em):
  kerning + tracking applied by the layout application;
* tight gap = ink-to-ink distance (em);
* optical gap = mean horizontal white run between the right ink profile of the
  left glyph and the left ink profile of the right glyph, inside the band
  [baseline, x-height] (lower-case) or [baseline, cap height]; this is the
  area-based "optical space" used in spacing proofs, expressed in em;
* word balance = coefficient of variation of the optical gaps;
* overshoot (optical alignment) = round letters' ink extent beyond flat letters;
* size dependence = change of coverage features when the same word is
  rasterised at small pixel sizes (anti-aliasing / resolution effect).
Nothing here is a quality score: the same values may be intended.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .outlines import OutlineFont, layout_word, render_outline_text

ROUND_TOP = set("Oocesa")
FLAT_TOP = {"O": "H", "o": "x", "c": "x", "e": "x", "s": "x", "a": "x"}


def _profiles(cov: np.ndarray, y0: int, y1: int, thr: float = 0.5):
    band = cov[y0:y1] >= thr
    W = band.shape[1]
    has = band.any(1)
    left = np.where(has, band.argmax(1), W)
    right = np.where(has, W - 1 - band[:, ::-1].argmax(1), -1)
    return left, right, has


def pair_optical_gaps(font: OutlineFont, text: str, positions_em: Optional[list[float]] = None,
                      px_per_em: int = 200, band: Optional[tuple[float, float]] = None) -> list[dict]:
    placed = layout_word(font, text, positions_em=positions_em)
    out = []
    for i in range(len(placed) - 1):
        (a, xa), (b, xb) = placed[i], placed[i + 1]
        if a.isspace() or b.isspace():
            continue
        ca, cb = font.contours(a), font.contours(b)
        if not ca or not cb:
            out.append({"pair": a + b, "measured": False})
            continue
        _, g2 = render_outline_text(font, [(a, 0.0), (b, xb - xa)], px_per_em, supersample=2)
        bb = g2["bbox_em"]
        A, _ = render_outline_text(font, [(a, 0.0)], px_per_em, supersample=2, bbox_em=bb)
        B, _ = render_outline_text(font, [(b, xb - xa)], px_per_em, supersample=2, bbox_em=bb)
        lo, hi = band if band else (0.0, 0.5)
        y0, y1 = int((bb[3] - hi) * px_per_em), int((bb[3] - lo) * px_per_em)
        _, ra, ha = _profiles(A, max(0, y0), max(1, y1))
        lb, _, hb = _profiles(B, max(0, y0), max(1, y1))
        both = ha & hb
        gap_rows = (lb - ra - 1)[both] / px_per_em
        tight = None
        cols_a = np.nonzero((A >= 0.5).any(0))[0]
        cols_b = np.nonzero((B >= 0.5).any(0))[0]
        if cols_a.size and cols_b.size:
            tight = (cols_b.min() - cols_a.max() - 1) / px_per_em
        adv = font.advance(a)
        out.append({"pair": a + b, "measured": True,
                    "applied_adjustment_em": (xb - xa - adv) if adv is not None else None,
                    "tight_gap_em": tight,
                    "optical_gap_em": float(gap_rows.mean()) if gap_rows.size else None,
                    "band_rows": int(both.sum())})
    return out


def word_spacing_report(font: OutlineFont, text: str, positions_em: Optional[list[float]] = None,
                        px_per_em: int = 200) -> dict:
    xh = font.contours("x")
    lower = any(c.islower() for c in text)
    band = (0.0, 0.45) if lower else (0.0, 0.65)
    if xh:
        from ..mathcore.glyph import flatten, outline_bbox
        bb = outline_bbox(flatten(xh))
        band = (0.0, bb[3]) if lower else band
    pairs = pair_optical_gaps(font, text, positions_em, px_per_em, band)
    og = np.array([p["optical_gap_em"] for p in pairs if p.get("optical_gap_em") is not None])
    return {"word": text, "pairs": pairs, "band_em": band,
            "optical_gap_mean_em": float(og.mean()) if og.size else None,
            "word_balance_cv": float(og.std() / og.mean()) if og.size >= 2 and og.mean() > 0 else None,
            "positions": "as_set_in_pdf" if positions_em is not None else "nominal_advances_no_kerning"}


def overshoot(font: OutlineFont) -> dict:
    from ..mathcore.glyph import flatten, outline_bbox
    out = {}
    for r, f in FLAT_TOP.items():
        cr, cf = font.contours(r), font.contours(f)
        if cr and cf:
            br, bf = outline_bbox(flatten(cr)), outline_bbox(flatten(cf))
            out[f"{r}_vs_{f}"] = {"top_em": br[3] - bf[3], "bottom_em": bf[1] - br[1]}
    return out


def size_dependence(font: OutlineFont, text: str, sizes_px=(10, 16, 24, 48, 200)) -> dict:
    """Ink coverage and apparent stroke darkness vs rasterisation size."""
    res = {}
    for s in sizes_px:
        img, _ = render_outline_text(font, layout_word(font, text), s, supersample=4)
        ink = img[img > 0.02]
        res[s] = {"coverage_mean": float(img.mean()), "mean_ink_alpha": float(ink.mean()) if ink.size else None}
    ref = res[max(sizes_px)]["coverage_mean"]
    for s in res:
        res[s]["coverage_rel_to_largest"] = res[s]["coverage_mean"] / ref if ref else None
    return {"text": text, "by_px_per_em": res,
            "note": "supersampled polygon rasteriser (no hinting); screen/print renderers will differ"}
