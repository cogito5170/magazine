"""Colour science: sRGB linearisation, relative luminance, HSV saturation,
CIE L*a*b* (D65) and CIEDE2000.  Inputs are float arrays in [0, 1]."""
from __future__ import annotations

import numpy as np

_M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]])
_WHITE_D65 = np.array([0.95047, 1.0, 1.08883])


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def relative_luminance(rgb: np.ndarray) -> np.ndarray:
    """Linear luminance Y in [0,1] (WCAG 2.x / Rec.709 coefficients)."""
    lin = srgb_to_linear(rgb)
    return lin[..., 0] * 0.2126 + lin[..., 1] * 0.7152 + lin[..., 2] * 0.0722


def contrast_ratio(l1: float, l2: float) -> float:
    """C = (L_max + 0.05) / (L_min + 0.05)  (spec B18, WCAG 2.x)."""
    hi, lo = max(l1, l2), min(l1, l2)
    return float((hi + 0.05) / (lo + 0.05))


def hsv_saturation(rgb: np.ndarray) -> np.ndarray:
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-12), 0.0)


def gray(rgb: np.ndarray) -> np.ndarray:
    """Gamma-encoded luma (Rec.601) in [0,1]; used for gradient-type features."""
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    lin = srgb_to_linear(rgb)
    xyz = lin @ _M_RGB2XYZ.T / _WHITE_D65
    d = 6 / 29
    f = np.where(xyz > d ** 3, np.cbrt(xyz), xyz / (3 * d * d) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def ciede2000(lab1, lab2, kL: float = 1.0, kC: float = 1.0, kH: float = 1.0) -> np.ndarray:
    """CIEDE2000 colour difference (Sharma, Wu & Dalal 2005 implementation)."""
    lab1 = np.asarray(lab1, float)
    lab2 = np.asarray(lab2, float)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    Cb = 0.5 * (C1 + C2)
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dhp = h2p - h1p
    dhp = np.where(dhp > 180, dhp - 360, dhp)
    dhp = np.where(dhp < -180, dhp + 360, dhp)
    dhp = np.where(C1p * C2p == 0, 0.0, dhp)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lbp = 0.5 * (L1 + L2)
    Cbp = 0.5 * (C1p + C2p)
    hsum = h1p + h2p
    hbp = np.where(np.abs(h1p - h2p) <= 180, hsum / 2,
                   np.where(hsum < 360, (hsum + 360) / 2, (hsum - 360) / 2))
    hbp = np.where(C1p * C2p == 0, hsum, hbp)
    T = (1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp))
         + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63)))
    dtheta = 30 * np.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25.0 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return np.sqrt((dLp / (kL * Sl)) ** 2 + (dCp / (kC * Sc)) ** 2 + (dHp / (kH * Sh)) ** 2
                   + Rt * (dCp / (kC * Sc)) * (dHp / (kH * Sh)))


def rgb_histogram(rgb: np.ndarray, bins: int = 8, mask=None) -> np.ndarray:
    """Joint RGB histogram with bins^3 cells (counts)."""
    px = rgb.reshape(-1, 3) if mask is None else rgb[mask]
    q = np.clip((px * bins).astype(int), 0, bins - 1)
    idx = q[:, 0] * bins * bins + q[:, 1] * bins + q[:, 2]
    return np.bincount(idx, minlength=bins ** 3).astype(float)


def dominant_colors(rgb: np.ndarray, k: int = 5, bins: int = 8, mask=None) -> list[dict]:
    """Top-k joint-histogram cells, reported by their mean colour and share."""
    px = rgb.reshape(-1, 3) if mask is None else rgb[mask]
    if px.size == 0:
        return []
    q = np.clip((px * bins).astype(int), 0, bins - 1)
    idx = q[:, 0] * bins * bins + q[:, 1] * bins + q[:, 2]
    counts = np.bincount(idx, minlength=bins ** 3)
    order = np.argsort(counts)[::-1][:k]
    out = []
    for c in order:
        if counts[c] == 0:
            break
        m = px[idx == c].mean(axis=0)
        out.append({"rgb": [float(x) for x in m], "hex": "#%02x%02x%02x" % tuple(int(round(x * 255)) for x in m),
                    "share": float(counts[c] / px.shape[0]),
                    "lab": [float(x) for x in rgb_to_lab(m[None, :])[0]]})
    return out
