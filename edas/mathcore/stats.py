"""Statistics helpers.  All entropies are in bits (log base 2)."""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

EPS = 1e-12
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)


def summary(values: Sequence[float], weights: Optional[Sequence[float]] = None) -> Optional[dict]:
    """mean, median, std (population), min, max, quantiles, n.  None when empty."""
    v = np.asarray([x for x in values if x is not None], dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    if weights is None:
        q = np.quantile(v, QUANTILES)
        return {
            "n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
            "std": float(v.std()), "min": float(v.min()), "max": float(v.max()),
            "quantiles": {f"q{int(p*100):02d}": float(x) for p, x in zip(QUANTILES, q)},
        }
    w = np.asarray(weights, dtype=float)
    q = weighted_quantile(v, w, QUANTILES)
    m = float(np.average(v, weights=w))
    return {
        "n": int(v.size), "weight_total": float(w.sum()), "mean": m,
        "median": float(q[2]), "std": float(np.sqrt(np.average((v - m) ** 2, weights=w))),
        "min": float(v.min()), "max": float(v.max()),
        "quantiles": {f"q{int(p*100):02d}": float(x) for p, x in zip(QUANTILES, q)},
    }


def weighted_quantile(v, w, qs):
    v = np.asarray(v, float)
    w = np.asarray(w, float)
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w) - 0.5 * w
    cw /= w.sum()
    return np.interp(qs, cw, v)


def shannon_entropy(p: Sequence[float]) -> Optional[float]:
    """H = -Σ p log2 p over a (re-normalised) non-negative vector."""
    p = np.asarray(p, dtype=float).ravel()
    s = p.sum()
    if s <= 0:
        return None
    p = p[p > 0] / s
    return float(-(p * np.log2(p)).sum())


def js_divergence(p: Sequence[float], q: Sequence[float]) -> Optional[float]:
    """Jensen–Shannon divergence in bits, in [0, 1]."""
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    if p.sum() <= 0 or q.sum() <= 0:
        return None
    p, q = p / p.sum(), q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        mask = a > 0
        return float((a[mask] * np.log2(a[mask] / b[mask])).sum())

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def wasserstein1(a: Sequence[float], b: Sequence[float],
                 wa: Optional[Sequence[float]] = None, wb: Optional[Sequence[float]] = None) -> Optional[float]:
    """1-D earth mover's distance between two (weighted) empirical distributions."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.size == 0 or b.size == 0:
        return None
    wa = np.ones_like(a) if wa is None else np.asarray(wa, float)
    wb = np.ones_like(b) if wb is None else np.asarray(wb, float)
    xs = np.sort(np.unique(np.concatenate([a, b])))

    def cdf(v, w):
        o = np.argsort(v)
        v, w = v[o], np.cumsum(w[o]) / w.sum()
        idx = np.searchsorted(v, xs, side="right") - 1
        return np.where(idx >= 0, w[np.clip(idx, 0, None)], 0.0)

    fa, fb = cdf(a, wa), cdf(b, wb)
    return float(np.sum(np.abs(fa - fb)[:-1] * np.diff(xs)))


def cosine(a: Sequence[float], b: Sequence[float]) -> Optional[float]:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return None
    return float(a @ b / (na * nb))


def autocorrelation(d: Sequence[float], k: int) -> Optional[float]:
    """ρ(k) per spec E8; None (undefined) when the denominator is 0 or k out of range."""
    d = np.asarray(d, float)
    P = d.size
    if k < 1 or k >= P:
        return None
    m = d.mean()
    den = float(((d - m) ** 2).sum())
    if den == 0:
        return None
    return float(((d[: P - k] - m) * (d[k:] - m)).sum() / den)


def sign_changes(d: Sequence[float]) -> Optional[int]:
    """Number of sign changes of the first difference; zero differences are skipped."""
    d = np.asarray(d, float)
    if d.size < 3:
        return None
    s = np.sign(np.diff(d))
    s = s[s != 0]
    if s.size < 2:
        return 0
    return int(np.sum(s[1:] != s[:-1]))


def bootstrap_ci(values: Sequence[float], stat=np.median, n_boot: int = 1000,
                 alpha: float = 0.05, seed: int = 0) -> Optional[dict]:
    v = np.asarray(values, float)
    if v.size < 2:
        return None
    rng = np.random.default_rng(seed)
    bs = np.array([stat(rng.choice(v, v.size, replace=True)) for _ in range(n_boot)])
    return {"lower": float(np.quantile(bs, alpha / 2)), "upper": float(np.quantile(bs, 1 - alpha / 2)),
            "std": float(bs.std()), "n_boot": n_boot, "alpha": alpha, "seed": seed}
