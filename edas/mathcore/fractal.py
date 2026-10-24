"""Fractal profiles and box-counting dimension."""
from __future__ import annotations

import numpy as np


def midpoint_profile(n_pow: int, hurst: float, seed: int = 0, amp: float = 1.0) -> np.ndarray:
    """1-D fractional-Brownian-like profile by midpoint displacement.
    For a self-affine profile the graph dimension is D = 2 - H."""
    rng = np.random.default_rng(seed)
    n = 2 ** n_pow + 1
    y = np.zeros(n)
    y[0], y[-1] = rng.normal(0, amp), rng.normal(0, amp)
    step, scale = n - 1, amp
    while step > 1:
        half = step // 2
        mids = 0.5 * (y[0:-1:step] + y[step::step]) + rng.normal(0, scale, (n - 1) // step)
        y[half::step] = mids
        step = half
        scale *= 2 ** (-hurst)
    return y


def box_counting_dimension(mask: np.ndarray, sizes=(2, 4, 8, 16, 32, 64)) -> dict:
    """Box-counting dimension of the True pixels of a binary image (e.g. a contour)."""
    H, W = mask.shape
    ns, used = [], []
    for s in sizes:
        if s >= min(H, W):
            continue
        h, w = (H // s) * s, (W // s) * s
        blocks = mask[:h, :w].reshape(h // s, s, w // s, s).any(axis=(1, 3))
        n = int(blocks.sum())
        if n > 0:
            ns.append(n)
            used.append(s)
    if len(used) < 3:
        return {"D": None, "sizes": used, "counts": ns}
    slope, _ = np.polyfit(np.log(1 / np.array(used, float)), np.log(np.array(ns, float)), 1)
    return {"D": float(slope), "sizes": used, "counts": ns}
