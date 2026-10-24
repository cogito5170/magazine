"""Spectral-residual saliency (Hou & Zhang, CVPR 2007).

Model-free and deterministic; it is an *estimator* of bottom-up visual
saliency, not a measurement of human attention.
"""
from __future__ import annotations

import numpy as np

from .imaging import box_filter, gaussian_blur, resize

MODEL_ID = "spectral_residual_hou_zhang_2007"


def spectral_residual(gray: np.ndarray, work_width: int = 64, avg_size: int = 3,
                      blur_sigma: float = 2.5) -> np.ndarray:
    """Saliency map at the input resolution, normalised to sum 1 (probability map)."""
    H, W = gray.shape
    w = work_width
    h = max(1, int(round(H * w / W)))
    small = resize(gray, w, h)
    F = np.fft.fft2(small)
    logamp = np.log(np.abs(F) + 1e-9)
    phase = np.angle(F)
    r = avg_size // 2
    resid = logamp - box_filter(logamp, r, r)
    sal = np.abs(np.fft.ifft2(np.exp(resid + 1j * phase))) ** 2
    sal = gaussian_blur(sal, blur_sigma * w / 64.0)
    sal = resize(sal, W, H)
    sal = np.clip(sal, 0, None)
    s = sal.sum()
    return sal / s if s > 0 else np.full_like(sal, 1.0 / sal.size)
