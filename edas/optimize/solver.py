"""Nelder–Mead simplex minimiser (derivative-free, NumPy only)."""
from __future__ import annotations

import numpy as np


def nelder_mead(f, x0, step=None, max_iter: int = 500, tol: float = 1e-8) -> dict:
    x0 = np.asarray(x0, float)
    n = x0.size
    step = np.full(n, 0.05) if step is None else np.asarray(step, float)
    simplex = [x0] + [x0 + np.eye(n)[i] * step[i] for i in range(n)]
    vals = [f(x) for x in simplex]
    it = 0
    for it in range(max_iter):
        order = np.argsort(vals)
        simplex = [simplex[i] for i in order]
        vals = [vals[i] for i in order]
        if abs(vals[-1] - vals[0]) < tol:
            break
        c = np.mean(simplex[:-1], axis=0)
        xr = c + (c - simplex[-1])
        fr = f(xr)
        if fr < vals[0]:
            xe = c + 2 * (c - simplex[-1])
            fe = f(xe)
            simplex[-1], vals[-1] = (xe, fe) if fe < fr else (xr, fr)
        elif fr < vals[-2]:
            simplex[-1], vals[-1] = xr, fr
        else:
            xc = c + 0.5 * (simplex[-1] - c)
            fc = f(xc)
            if fc < vals[-1]:
                simplex[-1], vals[-1] = xc, fc
            else:
                simplex = [simplex[0]] + [simplex[0] + 0.5 * (x - simplex[0]) for x in simplex[1:]]
                vals = [vals[0]] + [f(x) for x in simplex[1:]]
    i = int(np.argmin(vals))
    return {"x": simplex[i], "fun": float(vals[i]), "iterations": it + 1}
