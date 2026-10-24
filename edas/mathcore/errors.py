"""Error functions (spec §2.2) and normalisation (spec §2.1)."""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from ..schema import ErrorKind

EPS = 1e-9


def error_value(x: Optional[float], t: Optional[float], tau: Optional[float],
                kind: ErrorKind | str) -> Optional[float]:
    """E_i for a single variable.

    two_sided: ((x-t)/tau)^2
    min:       (max(0, t-x)/tau)^2
    max:       (max(0, x-t)/tau)^2
    Returns None when the variable has no target (spec: output measurement only)
    or when x is missing.
    """
    kind = ErrorKind(kind)
    if kind == ErrorKind.NONE or x is None or t is None or tau is None:
        return None
    if not tau > 0:
        raise ValueError("tolerance scale tau must be > 0")
    if kind == ErrorKind.TWO_SIDED:
        d = x - t
    elif kind == ErrorKind.MIN:
        d = max(0.0, t - x)
    else:
        d = max(0.0, x - t)
    return float((d / tau) ** 2)


def zscore(x: float, mu: float, sigma: float, eps: float = EPS) -> float:
    """z = (x - mu) / (sigma + eps); mu, sigma estimated on the reference set."""
    return float((x - mu) / (sigma + eps))


def quantile_normalize(x: float, reference: Sequence[float]) -> Optional[float]:
    """Empirical CDF position of x in the reference sample, in [0, 1].

    Uses the mid-rank convention F(x) = (#{r < x} + 0.5 #{r == x}) / n so that
    ties are handled symmetrically.  Returns None for an empty reference.
    """
    r = np.asarray([v for v in reference if v is not None], dtype=float)
    if r.size == 0:
        return None
    return float((np.sum(r < x) + 0.5 * np.sum(r == x)) / r.size)
