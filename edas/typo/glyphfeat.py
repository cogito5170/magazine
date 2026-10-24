"""Glyph geometry features from a binary glyph mask in em-relative coordinates.

Both sources go through ``features_from_mask`` so that every feature is
computed by the same code:
* PDF fonts: PDFium outline -> even-odd polygon fill (``outline_mask``);
* installed font files: FreeType rasterisation through Pillow (``file_mask``).
The residual difference between the two rasterisers is measured in tests
and recorded as a measurement-error estimate.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..mathcore.glyph import crofton_perimeter, flatten, local_stroke_width, outline_bbox
from ..mathcore.imaging import label_components

PAD = 3


def outline_mask(contours, px_per_em: int) -> Optional[tuple[np.ndarray, float, float]]:
    """Returns (mask, x_origin_px, baseline_px) for outlines given in em units (y up)."""
    polys = flatten(contours)
    bb = outline_bbox(polys)
    if bb is None:
        return None
    x0, y0, x1, y1 = bb
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return None
    s = float(px_per_em)
    W = int(np.ceil((x1 - x0) * s)) + 2 * PAD
    H = int(np.ceil((y1 - y0) * s)) + 2 * PAD
    mask = np.zeros((H, W), dtype=bool)
    for p in polys:
        im = Image.new("1", (W, H), 0)
        ImageDraw.Draw(im).polygon([((x - x0) * s + PAD, (y1 - y) * s + PAD) for x, y in p], fill=1)
        mask ^= np.asarray(im, dtype=bool)
    # em origin (x=0, y=0) in mask pixel coordinates
    return mask, PAD - x0 * s, PAD + y1 * s


_FONT_CACHE: dict = {}


def load_font_file(path: str, px_per_em: int, index: int = 0):
    key = (path, px_per_em, index)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(path, size=px_per_em, index=index)
    return _FONT_CACHE[key]


def file_mask(font, ch: str) -> Optional[tuple[np.ndarray, float, float]]:
    """FreeType raster of ``ch`` (threshold 50% coverage) with em origin."""
    l, t, r, b = font.getbbox(ch, anchor="ls")
    if r - l <= 0 or b - t <= 0:
        return None
    W, H = int(r - l) + 2 * PAD, int(b - t) + 2 * PAD
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).text((PAD - l, PAD - t), ch, font=font, fill=255, anchor="ls")
    mask = np.asarray(im) >= 128
    if not mask.any():
        return None
    return mask, PAD - l, PAD - t


def features_from_mask(mask: np.ndarray, x_origin: float, baseline: float, px_per_em: float,
                       stroke_q=(0.1, 0.9)) -> Optional[dict]:
    ys, xs = np.nonzero(mask)
    if xs.size < 4:
        return None
    s = float(px_per_em)
    x0p, x1p, y0p, y1p = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    w = (x1p - x0p) / s
    h = (y1p - y0p) / s
    top = (baseline - y0p) / s            # em above baseline
    bottom = (baseline - y1p) / s         # em above baseline (negative = descends)
    sw = local_stroke_width(mask)[mask] / s
    med = float(np.median(sw))
    qlo, qhi = np.quantile(sw, stroke_q)
    ink = mask.sum() / (s * s)
    box_area = w * h
    # counters: background components not connected to the border
    bg = ~mask[y0p:y1p, x0p:x1p]
    bgp = np.pad(bg, 1, constant_values=True)
    lbl, n = label_components(bgp)
    outside = lbl[0, 0]
    holes = float(((lbl > 0) & (lbl != outside)).sum()) / (s * s)
    cx = (xs.mean() + 0.5 - x_origin) / s
    cy = (baseline - (ys.mean() + 0.5)) / s
    per = crofton_perimeter(mask) / s
    return {
        "width_em": w, "height_em": h, "top_em": top, "bottom_em": bottom,
        "aspect": w / h if h > 0 else None,
        "stroke_median_em": med,
        "T_s": med / h if h > 0 else None,
        "C_stroke": float(qhi / qlo) if qlo > 0 else None,
        "D_ink": float(ink / box_area) if box_area > 0 else None,
        "counter_ratio": float(holes / box_area) if box_area > 0 else None,
        "cg_x_rel": float(((xs.mean() + 0.5) - x0p) / (x1p - x0p)),
        "cg_y_rel": float((y1p - (ys.mean() + 0.5)) / (y1p - y0p)),
        "cg_x_em": float(cx), "cg_y_em": float(cy),
        "complexity": float(per / (2 * (w + h))) if w + h > 0 else None,
    }
