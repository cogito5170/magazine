"""Pairwise preference models.

* ``BradleyTerry``: item scores q_i with P(A ≻ B) = σ(q_A − q_B); ties via
  Davidson (1970): P(tie) ∝ ν·sqrt(π_A π_B).  MAP with a Gaussian prior
  (precision ``l2``) for identifiability and small-sample stability.
* hierarchical option: q_{i,r} = q_i + δ_{i,r} with a tighter Gaussian prior
  on δ (shrinkage to the group); group and personal scores are both
  returned, so individual preference is never mistaken for consensus.
* ``FeatureBT``: conditional model q_θ(A, c) = θᵀ φ(A, c) on observed
  features (e.g. z_f and context), fitted as logistic regression on feature
  differences; generalises to unseen fonts.  Bootstrap uncertainty and a
  Mahalanobis OOD flag are provided.

'cannot_judge' answers are excluded from fitting (they are counted).
A model refuses to fit below ``min_decisive`` decisive comparisons.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40, 40)))


class InsufficientData(Exception):
    pass


class BradleyTerry:
    def __init__(self, l2: float = 0.1, l2_rater: float = 1.0, ties: bool = True,
                 hierarchical: bool = False, min_decisive: int = 20, max_iter: int = 3000, lr: float = 0.1):
        self.l2, self.l2_rater, self.ties, self.hier = l2, l2_rater, ties, hierarchical
        self.min_decisive, self.max_iter, self.lr = min_decisive, max_iter, lr
        self.items: list[str] = []
        self.raters: list[str] = []

    def fit(self, comps: Sequence[tuple[str, str, str, str]]) -> "BradleyTerry":
        """comps: (item_a, item_b, outcome in {'A','B','tie'}, rater)."""
        comps = [c for c in comps if c[2] in ("A", "B", "tie")]
        dec = sum(c[2] != "tie" for c in comps)
        if dec < self.min_decisive:
            raise InsufficientData(f"{dec} decisive comparisons < required {self.min_decisive}")
        self.items = sorted({c[0] for c in comps} | {c[1] for c in comps})
        self.raters = sorted({c[3] for c in comps})
        ii = {k: i for i, k in enumerate(self.items)}
        rr = {k: i for i, k in enumerate(self.raters)}
        a = np.array([ii[c[0]] for c in comps])
        b = np.array([ii[c[1]] for c in comps])
        r = np.array([rr[c[3]] for c in comps])
        yA = np.array([c[2] == "A" for c in comps], float)
        yB = np.array([c[2] == "B" for c in comps], float)
        yT = np.array([c[2] == "tie" for c in comps], float)
        nI, nR = len(self.items), len(self.raters)
        q = np.zeros(nI)
        D = np.zeros((nR, nI))
        lnu = np.log(0.5) if (self.ties and yT.any()) else -np.inf
        # Adam on the negative log posterior
        params = [q, D, np.array([lnu if np.isfinite(lnu) else 0.0])]
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        use_nu = self.ties and yT.any()
        for t in range(1, self.max_iter + 1):
            qa = q[a] + (D[r, a] if self.hier else 0)
            qb = q[b] + (D[r, b] if self.hier else 0)
            if use_nu:
                nu = np.exp(params[2][0])
                ea, eb = np.exp(qa - np.maximum(qa, qb)), np.exp(qb - np.maximum(qa, qb))
                et = nu * np.sqrt(ea * eb)
                Z = ea + eb + et
                pA, pB, pT = ea / Z, eb / Z, et / Z
                # d logL / d qa
                g = yA * (1 - pA - 0.5 * pT) + yB * (-pA - 0.5 * pT) + yT * (0.5 - pA - 0.5 * pT)
                gnu = float((yT * (1 - pT) - (yA + yB) * pT).sum())
            else:
                p = sigmoid(qa - qb)
                g = yA * (1 - p) - yB * p
                gnu = 0.0
            gq = np.zeros(nI)
            np.add.at(gq, a, g)
            np.add.at(gq, b, -g)
            gq -= self.l2 * q
            grads = [-gq, np.zeros_like(D), np.array([-gnu])]
            if self.hier:
                gD = np.zeros_like(D)
                np.add.at(gD, (r, a), g)
                np.add.at(gD, (r, b), -g)
                gD -= self.l2_rater * D
                grads[1] = -gD
            for k in range(3):
                if k == 2 and not use_nu:
                    continue
                m[k] = 0.9 * m[k] + 0.1 * grads[k]
                v[k] = 0.999 * v[k] + 0.001 * grads[k] ** 2
                step = self.lr * (m[k] / (1 - 0.9 ** t)) / (np.sqrt(v[k] / (1 - 0.999 ** t)) + 1e-8)
                params[k] -= step
            q, D = params[0], params[1]
            if t > 50 and np.abs(grads[0]).max() < 1e-5:
                break
        self.q = q - q.mean()
        self.D = D
        self.nu = float(np.exp(params[2][0])) if use_nu else 0.0
        self.n_comparisons = len(comps)
        self.n_decisive = dec
        return self

    def score(self, item: str, rater: Optional[str] = None) -> Optional[float]:
        if item not in self.items:
            return None
        i = self.items.index(item)
        s = float(self.q[i])
        if rater is not None and self.hier and rater in self.raters:
            s += float(self.D[self.raters.index(rater), i])
        return s

    def prob(self, a: str, b: str, rater: Optional[str] = None) -> Optional[float]:
        sa, sb = self.score(a, rater), self.score(b, rater)
        if sa is None or sb is None:
            return None
        return float(sigmoid(sa - sb))

    def to_dict(self) -> dict:
        return {"type": "bradley_terry", "items": self.items, "q_group": self.q.tolist(),
                "raters": self.raters, "rater_deviation": self.D.tolist() if self.hier else None,
                "tie_nu": self.nu, "l2": self.l2, "hierarchical": self.hier,
                "n_comparisons": self.n_comparisons, "n_decisive": self.n_decisive}


class FeatureBT:
    """q_θ(x) = θᵀ x on standardised features; fitted on pairwise differences."""

    def __init__(self, l2: float = 1.0, min_decisive: int = 30, max_iter: int = 500):
        self.l2, self.min_decisive, self.max_iter = l2, min_decisive, max_iter

    def fit(self, XA: np.ndarray, XB: np.ndarray, y: np.ndarray, w: Optional[np.ndarray] = None) -> "FeatureBT":
        """y = 1 if A preferred, 0 if B, 0.5 for tie."""
        dec = int(np.sum(y != 0.5))
        if dec < self.min_decisive:
            raise InsufficientData(f"{dec} decisive comparisons < required {self.min_decisive}")
        X = np.vstack([XA, XB])
        self.mu = X.mean(0)
        self.sd = X.std(0) + 1e-9
        Z = (XA - self.mu) / self.sd - (XB - self.mu) / self.sd
        w = np.ones(len(y)) if w is None else w
        th = np.zeros(Z.shape[1])
        for _ in range(self.max_iter):   # Newton / IRLS
            p = sigmoid(Z @ th)
            g = Z.T @ (w * (y - p)) - self.l2 * th
            Hm = (Z * (w * p * (1 - p))[:, None]).T @ Z + self.l2 * np.eye(len(th))
            step = np.linalg.solve(Hm, g)
            th += step
            if np.abs(step).max() < 1e-8:
                break
        self.theta = th
        Xs = (X - self.mu) / self.sd
        self.cov_inv = np.linalg.pinv(np.cov(Xs.T) + 1e-6 * np.eye(Xs.shape[1]))
        d = np.einsum("ij,jk,ik->i", Xs, self.cov_inv, Xs)
        self.ood_threshold = float(np.quantile(d, 0.99))
        self._train = (XA, XB, y, w)
        return self

    def q(self, x: np.ndarray) -> float:
        return float(((np.asarray(x) - self.mu) / self.sd) @ self.theta)

    def prob(self, xa, xb) -> float:
        return float(sigmoid(self.q(xa) - self.q(xb)))

    def is_ood(self, x) -> bool:
        z = (np.asarray(x) - self.mu) / self.sd
        return bool(z @ self.cov_inv @ z > self.ood_threshold)

    def bootstrap(self, xa, xb, n: int = 200, seed: int = 0) -> dict:
        XA, XB, y, w = self._train
        rng = np.random.default_rng(seed)
        ps = []
        for _ in range(n):
            idx = rng.integers(0, len(y), len(y))
            try:
                m = FeatureBT(self.l2, 1, self.max_iter).fit(XA[idx], XB[idx], y[idx], w[idx])
            except InsufficientData:
                continue
            ps.append(m.prob(xa, xb))
        ps = np.array(ps)
        return {"p": self.prob(xa, xb), "ci95": [float(np.quantile(ps, 0.025)), float(np.quantile(ps, 0.975))]
                if ps.size else None, "n_boot": int(ps.size),
                "ood": self.is_ood(xa) or self.is_ood(xb)}
