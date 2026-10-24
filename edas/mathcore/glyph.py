"""Glyph outline geometry (spec B4–B9).

Outlines are lists of contours; each contour is a list of segments
("L", p0, p1) or ("C", p0, c1, c2, p3) (cubic Bézier) in font space with y up.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

Contour = list[tuple]


def bezier_points(p0, c1, c2, p3, t: np.ndarray) -> np.ndarray:
    p0, c1, c2, p3 = (np.asarray(v, float) for v in (p0, c1, c2, p3))
    t = t[:, None]
    mt = 1 - t
    return mt ** 3 * p0 + 3 * mt ** 2 * t * c1 + 3 * mt * t ** 2 * c2 + t ** 3 * p3


def _bezier_d1(p0, c1, c2, p3, t):
    p0, c1, c2, p3 = (np.asarray(v, float) for v in (p0, c1, c2, p3))
    t = t[:, None]
    mt = 1 - t
    return 3 * mt ** 2 * (c1 - p0) + 6 * mt * t * (c2 - c1) + 3 * t ** 2 * (p3 - c2)


def _bezier_d2(p0, c1, c2, p3, t):
    p0, c1, c2, p3 = (np.asarray(v, float) for v in (p0, c1, c2, p3))
    t = t[:, None]
    return 6 * (1 - t) * (c2 - 2 * c1 + p0) + 6 * t * (p3 - 2 * c2 + c1)


def flatten(contours: list[Contour], samples: int = 24) -> list[np.ndarray]:
    polys = []
    t = np.linspace(0, 1, samples + 1)[1:]
    for c in contours:
        pts = []
        for seg in c:
            if not pts:
                pts.append(np.asarray(seg[1], float))
            if seg[0] == "L":
                pts.append(np.asarray(seg[2], float))
            else:
                pts.extend(bezier_points(seg[1], seg[2], seg[3], seg[4], t))
        if len(pts) >= 3:
            polys.append(np.asarray(pts))
    return polys


def outline_bbox(polys: list[np.ndarray]) -> Optional[tuple[float, float, float, float]]:
    if not polys:
        return None
    a = np.concatenate(polys)
    return float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())


def contour_length(polys: list[np.ndarray]) -> float:
    total = 0.0
    for p in polys:
        q = np.vstack([p, p[:1]])
        total += float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum())
    return total


def curvature_samples(contours: list[Contour], height: float, samples: int = 24,
                      corner_deg: float = 30.0) -> dict:
    """Arc-length-weighted samples of |κ|·h along Bézier segments (lines: κ=0).

    Corners (tangent discontinuities > corner_deg between consecutive
    segments) have infinite curvature and are counted separately rather than
    included in the distribution.
    """
    vals, wts = [], []
    corners = 0
    t = (np.arange(samples) + 0.5) / samples
    for c in contours:
        prev_dir = None
        first_dir = None
        for seg in c:
            if seg[0] == "L":
                d = np.asarray(seg[2], float) - np.asarray(seg[1], float)
                L = float(np.linalg.norm(d))
                if L == 0:
                    continue
                vals.append(0.0)
                wts.append(L)
                d_in, d_out = d, d
            else:
                d1 = _bezier_d1(*seg[1:], t)
                d2 = _bezier_d2(*seg[1:], t)
                sp = np.linalg.norm(d1, axis=1)
                ok = sp > 1e-12
                k = np.zeros_like(sp)
                k[ok] = np.abs(d1[ok, 0] * d2[ok, 1] - d1[ok, 1] * d2[ok, 0]) / sp[ok] ** 3
                vals.extend((k * height).tolist())
                wts.extend((sp / samples).tolist())
                e0 = _bezier_d1(*seg[1:], np.array([1e-6]))[0]
                e1 = _bezier_d1(*seg[1:], np.array([1 - 1e-6]))[0]
                d_in, d_out = e0, e1
            if prev_dir is not None and _angle(prev_dir, d_in) > corner_deg:
                corners += 1
            if first_dir is None:
                first_dir = d_in
            prev_dir = d_out
        if prev_dir is not None and first_dir is not None and _angle(prev_dir, first_dir) > corner_deg:
            corners += 1
    return {"values": np.asarray(vals), "weights": np.asarray(wts), "corners": corners}


def _angle(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b) / (na * nb), -1, 1))))


def rasterize(polys: list[np.ndarray], bbox, height_px: int = 96, pad: int = 2) -> np.ndarray:
    """Even-odd fill of the outline polygons; bool mask with y down."""
    x0, y0, x1, y1 = bbox
    h = max(y1 - y0, 1e-9)
    s = (height_px - 2 * pad) / h
    W = int(np.ceil((x1 - x0) * s)) + 2 * pad
    mask = np.zeros((height_px, max(W, 1)), dtype=bool)
    for p in polys:
        im = Image.new("1", (mask.shape[1], mask.shape[0]), 0)
        pts = [((x - x0) * s + pad, (y1 - y) * s + pad) for x, y in p]
        ImageDraw.Draw(im).polygon(pts, fill=1)
        mask ^= np.asarray(im, dtype=bool)
    return mask


def _runs_along(mask: np.ndarray) -> np.ndarray:
    """For every True pixel, length of the horizontal run containing it."""
    H, W = mask.shape
    out = np.zeros((H, W), dtype=float)
    m = mask.astype(np.int8)
    for y in range(H):
        d = np.diff(np.concatenate([[0], m[y], [0]]))
        st = np.flatnonzero(d == 1)
        en = np.flatnonzero(d == -1)
        for s, e in zip(st, en):
            out[y, s:e] = e - s
    return out


def _diag_runs(mask: np.ndarray, anti: bool) -> np.ndarray:
    H, W = mask.shape
    m = mask[:, ::-1] if anti else mask
    out = np.zeros((H, W), dtype=float)
    for k in range(-H + 1, W):
        idx_y = np.arange(max(0, -k), min(H, W - k))
        idx_x = idx_y + k
        line = m[idx_y, idx_x].astype(np.int8)
        if not line.any():
            continue
        d = np.diff(np.concatenate([[0], line, [0]]))
        st = np.flatnonzero(d == 1)
        en = np.flatnonzero(d == -1)
        vals = np.zeros(line.size)
        for s, e in zip(st, en):
            vals[s:e] = (e - s) * np.sqrt(2)
        out[idx_y, idx_x] = vals
    return out[:, ::-1] if anti else out


def local_stroke_width(mask: np.ndarray) -> np.ndarray:
    """Per-ink-pixel stroke width estimate: minimum run length over the 4
    directions 0°, 90°, 45°, 135° (diagonal runs scaled by √2).  Pixels."""
    h = _runs_along(mask)
    v = _runs_along(mask.T).T
    d1 = _diag_runs(mask, anti=False)
    d2 = _diag_runs(mask, anti=True)
    st = np.stack([h, v, d1, d2])
    st[st == 0] = np.inf
    w = st.min(axis=0)
    w[~mask] = 0
    return w


def crofton_perimeter(mask: np.ndarray) -> float:
    """Cauchy–Crofton perimeter estimate from horizontal + vertical transitions."""
    m = mask.astype(np.int8)
    nh = np.abs(np.diff(np.pad(m, ((0, 0), (1, 1))), axis=1)).sum()
    nv = np.abs(np.diff(np.pad(m, ((1, 1), (0, 0))), axis=0)).sum()
    return float(np.pi / 4 * (nh + nv))
