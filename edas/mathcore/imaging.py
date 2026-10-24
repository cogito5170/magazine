"""NumPy-only image operators (no OpenCV/SciPy dependency).

Images are float arrays in [0, 1]; grayscale is HxW, colour HxWx3.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image


def to_float_rgb(img) -> np.ndarray:
    if isinstance(img, Image.Image):
        img = np.asarray(img.convert("RGB"))
    a = np.asarray(img)
    if a.dtype == np.uint8:
        a = a.astype(float) / 255.0
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return a[..., :3].astype(float)


def resize(a: np.ndarray, width: int, height: int) -> np.ndarray:
    if a.ndim == 2:
        im = Image.fromarray(a.astype(np.float32), mode="F")
        return np.asarray(im.resize((width, height), Image.BILINEAR), dtype=float)
    ch = [resize(a[..., i], width, height) for i in range(a.shape[2])]
    return np.stack(ch, axis=-1)


def resize_max(a: np.ndarray, max_side: int) -> tuple[np.ndarray, float]:
    h, w = a.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s >= 1.0:
        return a, 1.0
    return resize(a, max(1, int(round(w * s))), max(1, int(round(h * s)))), s


def convolve2d(img: np.ndarray, k: np.ndarray) -> np.ndarray:
    """'same' correlation with edge replication (kernels used here are symmetric up to sign)."""
    kh, kw = k.shape
    ph, pw = kh // 2, kw // 2
    p = np.pad(img, ((ph, ph), (pw, pw)), mode="edge")
    out = np.zeros_like(img, dtype=float)
    for i in range(kh):
        for j in range(kw):
            if k[i, j] != 0:
                out += k[i, j] * p[i:i + img.shape[0], j:j + img.shape[1]]
    return out


def gaussian_kernel1d(sigma: float) -> np.ndarray:
    r = max(1, int(np.ceil(3 * sigma)))
    x = np.arange(-r, r + 1)
    g = np.exp(-x ** 2 / (2 * sigma ** 2))
    return g / g.sum()


def gaussian_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return img.astype(float)
    g = gaussian_kernel1d(sigma)
    return convolve2d(convolve2d(img, g[None, :]), g[:, None])


def box_filter(img: np.ndarray, rh: int, rw: int) -> np.ndarray:
    """Mean over a (2rh+1)x(2rw+1) window using an integral image."""
    p = np.pad(img.astype(float), ((rh + 1, rh), (rw + 1, rw)), mode="edge")
    s = p.cumsum(0).cumsum(1)
    H, W = img.shape
    kh, kw = 2 * rh + 1, 2 * rw + 1
    tot = s[kh:kh + H, kw:kw + W] - s[:H, kw:kw + W] - s[kh:kh + H, :W] + s[:H, :W]
    return tot / (kh * kw)


LAPLACIAN = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=float)
SOBEL_X = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float)
SOBEL_Y = SOBEL_X.T


def laplacian(gray: np.ndarray) -> np.ndarray:
    return convolve2d(gray, LAPLACIAN)


def sobel(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return convolve2d(gray, SOBEL_X), convolve2d(gray, SOBEL_Y)


def canny(gray: np.ndarray, sigma: float = 1.0, low: float = 0.05, high: float = 0.15) -> np.ndarray:
    """Canny edge detector: Gaussian, Sobel, non-maximum suppression,
    double threshold and hysteresis.  Thresholds are on the gradient magnitude
    normalised by the Sobel gain (4), so they are in units of intensity/pixel."""
    g = gaussian_blur(gray, sigma)
    gx, gy = sobel(g)
    mag = np.hypot(gx, gy) / 4.0
    ang = (np.degrees(np.arctan2(gy, gx)) + 180) % 180
    H, W = g.shape
    p = np.pad(mag, 1)
    c = p[1:-1, 1:-1]
    q = np.zeros_like(mag, dtype=bool)
    d0 = (ang < 22.5) | (ang >= 157.5)
    d45 = (ang >= 22.5) & (ang < 67.5)
    d90 = (ang >= 67.5) & (ang < 112.5)
    d135 = (ang >= 112.5) & (ang < 157.5)
    E, Wn = p[1:-1, 2:], p[1:-1, :-2]
    N, S = p[:-2, 1:-1], p[2:, 1:-1]
    NE, SW = p[:-2, 2:], p[2:, :-2]
    NW, SE = p[:-2, :-2], p[2:, 2:]
    q |= d0 & (c >= E) & (c >= Wn)
    q |= d90 & (c >= N) & (c >= S)
    q |= d45 & (c >= SE) & (c >= NW)   # gradient at 45deg in image coords (y down)
    q |= d135 & (c >= NE) & (c >= SW)
    nms = np.where(q, mag, 0.0)
    strong = nms >= high
    weak = (nms >= low) & ~strong
    edges = strong.copy()
    for _ in range(max(H, W)):
        grown = dilate(edges, 1) & weak
        new = edges | grown
        if new.sum() == edges.sum():
            break
        edges = new
    return edges


def dilate(mask: np.ndarray, r: int = 1) -> np.ndarray:
    m = np.pad(mask, r)
    out = np.zeros_like(mask, dtype=bool)
    H, W = mask.shape
    for i in range(2 * r + 1):
        for j in range(2 * r + 1):
            out |= m[i:i + H, j:j + W]
    return out


def dilate_rect(mask: np.ndarray, rh: int, rw: int) -> np.ndarray:
    return box_filter(mask.astype(float), rh, rw) > 1e-9


def label_components(mask: np.ndarray) -> tuple[np.ndarray, int]:
    """8-connected component labelling by run-length union-find.  Labels 1..n."""
    H, W = mask.shape
    runs_r, runs_s, runs_e = [], [], []
    m = mask.astype(np.int8)
    for y in range(H):
        row = m[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate([[0], row, [0]]))
        st = np.flatnonzero(d == 1)
        en = np.flatnonzero(d == -1)
        runs_r.extend([y] * len(st))
        runs_s.extend(st.tolist())
        runs_e.extend(en.tolist())
    n = len(runs_r)
    if n == 0:
        return np.zeros((H, W), dtype=np.int32), 0
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    # index runs by row
    row_start: dict[int, int] = {}
    row_end: dict[int, int] = {}
    for i, r in enumerate(runs_r):
        row_start.setdefault(r, i)
        row_end[r] = i + 1
    for y in sorted(row_start):
        if y - 1 not in row_start:
            continue
        a0, a1 = row_start[y - 1], row_end[y - 1]
        b0, b1 = row_start[y], row_end[y]
        i, j = a0, b0
        while i < a1 and j < b1:
            # 8-connectivity: runs overlap if [s-1, e+1) intersects
            if runs_s[i] <= runs_e[j] and runs_s[j] <= runs_e[i]:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri
            if runs_e[i] < runs_e[j]:
                i += 1
            else:
                j += 1
    roots = {}
    lab = np.zeros((H, W), dtype=np.int32)
    for i in range(n):
        r = find(i)
        if r not in roots:
            roots[r] = len(roots) + 1
        lab[runs_r[i], runs_s[i]:runs_e[i]] = roots[r]
    return lab, len(roots)


def component_boxes(lab: np.ndarray, n: int) -> list[dict]:
    """Bounding box (x0, y0, x1, y1 exclusive) and pixel area per label."""
    if n == 0:
        return []
    ys, xs = np.nonzero(lab)
    ls = lab[ys, xs]
    out = []
    x0 = np.full(n + 1, 1 << 30)
    y0 = np.full(n + 1, 1 << 30)
    x1 = np.full(n + 1, -1)
    y1 = np.full(n + 1, -1)
    np.minimum.at(x0, ls, xs)
    np.minimum.at(y0, ls, ys)
    np.maximum.at(x1, ls, xs)
    np.maximum.at(y1, ls, ys)
    cnt = np.bincount(ls, minlength=n + 1)
    for i in range(1, n + 1):
        out.append({"label": i, "box": (int(x0[i]), int(y0[i]), int(x1[i]) + 1, int(y1[i]) + 1),
                    "area": int(cnt[i])})
    return out


def local_maxima(a: np.ndarray, radius: int, threshold: float) -> list[tuple[int, int, float]]:
    """Points that are maxima in a (2r+1)^2 window and >= threshold."""
    H, W = a.shape
    p = np.pad(a, radius, mode="constant", constant_values=-np.inf)
    mx = np.full_like(a, -np.inf)
    for i in range(2 * radius + 1):
        for j in range(2 * radius + 1):
            mx = np.maximum(mx, p[i:i + H, j:j + W])
    ys, xs = np.nonzero((a >= mx) & (a >= threshold))
    pts = sorted(((int(y), int(x), float(a[y, x])) for y, x in zip(ys, xs)), key=lambda t: -t[2])
    kept: list[tuple[int, int, float]] = []
    for y, x, v in pts:  # suppress plateau duplicates
        if all((y - ky) ** 2 + (x - kx) ** 2 > radius ** 2 for ky, kx, _ in kept):
            kept.append((y, x, v))
    return kept


def hough_dominant_line(edges: np.ndarray, angle_range_deg: float = 20.0, step_deg: float = 0.25,
                        max_points: int = 20000, seed: int = 0) -> Optional[dict]:
    """Strongest straight line within ±angle_range of horizontal (Hough transform).

    Returns the line's tilt in degrees (positive = right end higher, image y down),
    and its vote count relative to the image width.
    """
    ys, xs = np.nonzero(edges)
    if xs.size < 10:
        return None
    if xs.size > max_points:
        idx = np.random.default_rng(seed).choice(xs.size, max_points, replace=False)
        xs, ys = xs[idx], ys[idx]
    H, W = edges.shape
    tilts = np.arange(-angle_range_deg, angle_range_deg + 1e-9, step_deg)
    # line normal angle theta = 90deg + tilt; rho = x cos(theta) + y sin(theta)
    th = np.radians(90.0 + tilts)
    rho = np.outer(xs, np.cos(th)) + np.outer(ys, np.sin(th))
    diag = int(np.ceil(np.hypot(H, W)))
    ri = np.round(rho).astype(int) + diag
    acc = np.zeros((2 * diag + 1, tilts.size), dtype=np.int32)
    np.add.at(acc, (ri, np.broadcast_to(np.arange(tilts.size), ri.shape)), 1)
    r, t = np.unravel_index(np.argmax(acc), acc.shape)
    return {"tilt_deg": float(-tilts[t]), "votes": int(acc[r, t]), "support": float(acc[r, t] / W),
            "rho_px": float(r - diag)}
