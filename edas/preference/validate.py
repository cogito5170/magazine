"""Validation of preference data and models.

* inter-rater agreement: raw pairwise agreement and Krippendorff's α
  (nominal, categories A/B/tie with A/B orientation normalised);
* leakage-safe grouped cross-validation (groups = page_id, project_id or
  font family): all variants of one page stay in the same fold;
* predictive accuracy on decisive judgments, log loss, Brier score,
  expected calibration error and a reliability table;
* per-rater agreement with the group-majority (individual differences);
* association between aesthetic and readability judgments of the same
  rater on the same pair;
* original-vs-alternative comparison with bootstrap intervals.
Every function returns ``status='insufficient_data'`` instead of a number
when its minimum sample is not met.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Callable, Optional

import numpy as np

from .bt import BradleyTerry, InsufficientData, sigmoid
from .schema import Judgment


def _canon(j: Judgment):
    """Orientation-free key and outcome (outcome expressed for the sorted pair)."""
    a, b = sorted([j.stimulus_a, j.stimulus_b])
    if j.choice == "tie":
        return (a, b, j.criterion, j.experiment), "tie"
    win = j.stimulus_a if j.choice == "A" else j.stimulus_b
    return (a, b, j.criterion, j.experiment), ("first" if win == a else "second")


def inter_rater_agreement(js: list[Judgment], min_units: int = 5) -> dict:
    units = defaultdict(list)
    for j in js:
        if j.choice == "cannot_judge":
            continue
        k, o = _canon(j)
        units[k].append(o)
    units = {k: v for k, v in units.items() if len(v) >= 2}
    if len(units) < min_units:
        return {"status": "insufficient_data", "units_with_2plus_raters": len(units), "required": min_units}
    agree = tot = 0
    for v in units.values():
        for i in range(len(v)):
            for j in range(i + 1, len(v)):
                tot += 1
                agree += v[i] == v[j]
    # Krippendorff alpha, nominal
    cats = sorted({o for v in units.values() for o in v})
    ci = {c: i for i, c in enumerate(cats)}
    O = np.zeros((len(cats), len(cats)))
    for v in units.values():
        m = len(v)
        cnt = Counter(v)
        for c1 in cnt:
            for c2 in cnt:
                n = cnt[c1] * (cnt[c2] - (1 if c1 == c2 else 0))
                O[ci[c1], ci[c2]] += n / (m - 1)
    n = O.sum()
    nc = O.sum(1)
    Do = (n - np.trace(O)) / n
    De = (n * n - (nc ** 2).sum()) / (n * (n - 1)) if n > 1 else 0
    alpha = float(1 - Do / De) if De > 0 else None
    return {"status": "ok", "units": len(units), "pairwise_agreement": agree / tot,
            "krippendorff_alpha_nominal": alpha, "categories": cats}


def grouped_folds(js: list[Judgment], key: Callable[[Judgment], str], k: int = 5, seed: int = 0):
    groups = sorted({key(j) for j in js})
    rng = np.random.default_rng(seed)
    rng.shuffle(groups)
    folds = [groups[i::k] for i in range(min(k, len(groups)))]
    for f in folds:
        fs = set(f)
        yield [j for j in js if key(j) not in fs], [j for j in js if key(j) in fs], f


def _calibration(p: np.ndarray, y: np.ndarray, bins: int = 10) -> dict:
    edges = np.linspace(0, 1, bins + 1)
    rows, ece = [], 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            conf, acc = float(p[m].mean()), float(y[m].mean())
            ece += m.mean() * abs(conf - acc)
            rows.append({"bin": [float(lo), float(hi)], "n": int(m.sum()), "mean_p": conf, "observed": acc})
    return {"ece": float(ece), "table": rows}


def cross_validate_bt(js: list[Judgment], group_key: Callable[[Judgment], str], item_key=None,
                      k: int = 5, min_decisive: int = 20, **bt_kw) -> dict:
    """Leakage-safe evaluation of an item-level BT model.

    Note: an item-level model can only score items seen in training; test
    judgments on unseen items are counted as 'not predictable' (this is what
    makes the font-family / project hold-out informative)."""
    item_key = item_key or (lambda j, side: j.font_a if side == "a" else j.font_b)
    ps, ys, skipped, folds = [], [], 0, 0
    for tr, te, grp in grouped_folds(js, group_key, k):
        comps = [(item_key(j, "a"), item_key(j, "b"), j.choice, j.rater_id) for j in tr if j.choice != "cannot_judge"]
        try:
            m = BradleyTerry(min_decisive=min_decisive, **bt_kw).fit(comps)
        except InsufficientData:
            continue
        folds += 1
        for j in te:
            if j.choice not in ("A", "B"):
                continue
            p = m.prob(item_key(j, "a"), item_key(j, "b"))
            if p is None:
                skipped += 1
                continue
            ps.append(p)
            ys.append(1.0 if j.choice == "A" else 0.0)
    if not ps:
        return {"status": "insufficient_data", "folds_fitted": folds, "unpredictable_test_items": skipped}
    p, y = np.array(ps), np.array(ys)
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    return {"status": "ok", "folds_fitted": folds, "n_test": int(p.size), "unpredictable_test_items": skipped,
            "accuracy": float(((p > 0.5) == (y == 1)).mean()),
            "log_loss": float(-(y * np.log(pc) + (1 - y) * np.log(1 - pc)).mean()),
            "brier": float(((p - y) ** 2).mean()), "calibration": _calibration(p, y)}


def rater_differences(js: list[Judgment], min_per_rater: int = 5) -> dict:
    units = defaultdict(list)
    for j in js:
        if j.choice in ("A", "B", "tie"):
            k, o = _canon(j)
            units[k].append((j.rater_id, o))
    majority = {k: Counter(o for _, o in v).most_common(1)[0][0] for k, v in units.items() if len(v) >= 3}
    per = defaultdict(lambda: [0, 0])
    for k, v in units.items():
        if k not in majority:
            continue
        for r, o in v:
            per[r][1] += 1
            per[r][0] += o == majority[k]
    out = {r: {"agreement_with_majority": a / n, "n": n} for r, (a, n) in per.items() if n >= min_per_rater}
    return {"status": "ok" if out else "insufficient_data", "raters": out,
            "note": "agreement with the majority of the other raters; low values indicate individual taste, "
                    "not error"}


def criterion_association(js: list[Judgment], c1: str = "glyph_beauty", c2: str = "readability",
                          min_pairs: int = 10) -> dict:
    by = defaultdict(dict)
    for j in js:
        if j.choice in ("A", "B"):
            k, o = _canon(j)
            by[(j.rater_id, k[0], k[1], k[3])][j.criterion] = o
    both = [(v[c1], v[c2]) for v in by.values() if c1 in v and c2 in v]
    if len(both) < min_pairs:
        return {"status": "insufficient_data", "n": len(both), "required": min_pairs}
    x = np.array([a == "first" for a, _ in both], float)
    y = np.array([b == "first" for _, b in both], float)
    phi = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else None
    return {"status": "ok", "n": len(both), "same_choice_rate": float((x == y).mean()), "phi": phi,
            "criteria": [c1, c2]}


def original_vs_alternatives(js: list[Judgment], original: str, n_boot: int = 300, seed: int = 0,
                             min_decisive: int = 20) -> dict:
    comps = [(j.font_a, j.font_b, j.choice, j.rater_id) for j in js if j.choice in ("A", "B", "tie")]
    try:
        m = BradleyTerry(min_decisive=min_decisive).fit(comps)
    except InsufficientData as e:
        return {"status": "insufficient_data", "reason": str(e)}
    rng = np.random.default_rng(seed)
    boots = defaultdict(list)
    for _ in range(n_boot):
        idx = rng.integers(0, len(comps), len(comps))
        try:
            mb = BradleyTerry(min_decisive=1, max_iter=800).fit([comps[i] for i in idx])
        except InsufficientData:
            continue
        so = mb.score(original)
        if so is None:
            continue
        for it in mb.items:
            if it != original:
                boots[it].append(mb.score(it) - so)
    res = {}
    for it in m.items:
        if it == original:
            continue
        b = np.array(boots.get(it, []))
        res[it] = {"score_minus_original": m.score(it) - m.score(original),
                   "p_preferred_over_original": m.prob(it, original),
                   "ci95": [float(np.quantile(b, .025)), float(np.quantile(b, .975))] if b.size > 10 else None}
    return {"status": "ok", "original": original, "alternatives": res, "model": m.to_dict()}
