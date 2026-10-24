"""Reference-based targets (spec §10).

A profile is built from analysed reference documents or images.  Targets are
distributions (quantiles), never single 'ideal' numbers:
    t = median,  τ = IQR / 1.349 (robust σ; falls back to σ),
    plus q05..q95, n and a bootstrap CI of the median.
With fewer than ``min_n`` samples the target is flagged ``insufficient``.
Style presets carry no built-in numbers: a style profile exists only after
references for that style have been analysed.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Optional

import numpy as np

from ..features import ALL_KEYS, MODULE_OF, SOURCE_DEPENDENT
from ..mathcore.stats import bootstrap_ci

STYLES = ["fashion_editorial", "architecture_magazine", "luxury_editorial", "minimalist_magazine",
          "contemporary_art_magazine", "lifestyle_magazine"]


def build_profile(page_vectors: list[dict], doc_vectors: Optional[list[dict]] = None, style: Optional[str] = None,
                  sources: Optional[list[dict]] = None, min_n: int = 8, extra: Optional[dict] = None) -> dict:
    feats = {}
    for k in ALL_KEYS:
        v = np.array([pv[k] for pv in page_vectors if pv.get(k) is not None], float)
        if v.size == 0:
            continue
        q = np.quantile(v, [0.05, 0.25, 0.5, 0.75, 0.95])
        iqr_sigma = (q[3] - q[1]) / 1.349
        tau = float(iqr_sigma) if iqr_sigma > 0 else (float(v.std()) if v.std() > 0 else None)
        feats[k] = {"n": int(v.size), "median": float(q[2]), "mean": float(v.mean()), "std": float(v.std()),
                    "quantiles": dict(zip(("q05", "q25", "q50", "q75", "q95"), map(float, q))),
                    "tau": tau, "median_ci95": bootstrap_ci(v, n_boot=500),
                    "status": "ok" if v.size >= min_n else "insufficient_samples",
                    "module": MODULE_OF[k], "source_dependent": k in SOURCE_DEPENDENT}
    prof = {"style": style, "created": dt.datetime.now(dt.timezone.utc).isoformat(),
            "n_pages": len(page_vectors), "min_n": min_n, "features": feats, "sources": sources or [],
            "target_rule": "t = median; tau = IQR/1.349 (fallback σ); error per parameter error kind"}
    if doc_vectors:
        keys = sorted({k for d in doc_vectors for k, v in d.items() if v is not None})
        prof["doc_vector_stats"] = {
            "mean": {k: float(np.mean([d[k] for d in doc_vectors if d.get(k) is not None])) for k in keys},
            "std": {k: float(np.std([d[k] for d in doc_vectors if d.get(k) is not None])) for k in keys},
            "median": {k: float(np.median([d[k] for d in doc_vectors if d.get(k) is not None])) for k in keys}}
    sty = {}
    for k in ("A06", "A07", "A08", "A09", "D02", "D15", "C03.area_weighted_mean", "C06.area_weighted_mean",
              "B15", "A19.edge_density"):
        if k in feats:
            sty[k] = feats[k]
    if sty:
        prof["page_style_stats"] = {"mean": {k: v["mean"] for k, v in sty.items()},
                                    "std": {k: v["std"] for k, v in sty.items()}}
    if extra:
        prof.update(extra)
    return prof


def save_profile(prof: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(prof, fh, ensure_ascii=False, indent=2)


def load_profile(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def compare_to_profile(vec: dict, prof: dict, error_kinds: dict) -> list[dict]:
    """Per feature: current value, target distribution, deviation, τ, error E."""
    from ..mathcore.errors import error_value
    rows = []
    for k, t in prof.get("features", {}).items():
        x = vec.get(k)
        if x is None:
            continue
        kind = error_kinds.get(k.split(".")[0], "two_sided")
        if kind == "none":
            kind = "two_sided"
        E = error_value(x, t["median"], t["tau"], kind) if t.get("tau") else None
        pct = None
        qs = t["quantiles"]
        if x < qs["q05"]:
            pct = "below q05"
        elif x > qs["q95"]:
            pct = "above q95"
        rows.append({"feature": k, "module": t["module"], "value": x, "target_median": t["median"],
                     "target_range_q25_q75": [qs["q25"], qs["q75"]], "target_range_q05_q95": [qs["q05"], qs["q95"]],
                     "deviation": x - t["median"], "tau": t.get("tau"), "error_kind": kind, "error": E,
                     "position": pct, "n_reference": t["n"], "target_status": t["status"],
                     "source_dependent": t.get("source_dependent", False)})
    return sorted(rows, key=lambda r: -(r["error"] or 0))
