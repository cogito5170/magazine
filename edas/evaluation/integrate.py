"""Integrated evaluation (spec §9).

Q = (Q_technical, Q_perceptual, Q_functional) are kept separate.
* Q_technical: measurable constraints, each with its value, threshold,
  error and evidence (source verification status included);
* Q_perceptual: only from trained preference models, else null;
* Q_functional: reading speed, comprehension, search time, recall require
  experiments; without data they are null and typed 'not_measured'.
L = Σ λ_k E_k is reported with ``validated: false`` unless the configuration
states otherwise; it is never presented as objective quality.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..governance.evidence import SOURCES
from ..mathcore.errors import error_value


def technical_constraints(doc, analysis, cfg: dict) -> list[dict]:
    tt = cfg["technical_targets"]
    rows = []
    for pa in analysis.pages:
        p = pa.get("B18")
        if p and isinstance(p.value, dict):
            share = p.value.get("share_below_wcag")
            rows.append({"page": pa.page_index + 1, "constraint": "text_contrast_wcag", "parameter": "B18",
                         "value": share, "unit": "share of lines below threshold", "threshold": 0.0,
                         "satisfied": share == 0, "error": error_value(share, 0.0, 0.1, "max"),
                         "evidence_source": "wcag22_sc143",
                         "evidence_status": SOURCES["wcag22_sc143"].verification_status.value,
                         "min_contrast": p.value.get("min")})
    thr = tt["effective_ppi_min"]
    for pm in doc.pages:
        for im in pm.images:
            if im.effective_ppi:
                ppi = min(im.effective_ppi)
                rows.append({"page": pm.index + 1, "constraint": "effective_image_resolution", "parameter": "X01",
                             "value": ppi, "unit": "ppi", "threshold": thr["value"], "satisfied": ppi >= thr["value"],
                             "error": error_value(ppi, thr["value"], thr["tolerance"], "min"),
                             "evidence_source": None, "evidence_status": "unverified",
                             "evidence_note": thr["source"]})
        out = 0
        for l in pm.lines:
            b = l.box
            if b[0] < -0.5 or b[1] < -0.5 or b[2] > pm.width + 0.5 or b[3] > pm.height + 0.5:
                out += 1
        rows.append({"page": pm.index + 1, "constraint": "text_inside_page", "parameter": "X02", "value": out,
                     "unit": "text lines crossing the page edge", "threshold": 0, "satisfied": out == 0,
                     "error": error_value(out, 0, 1, "max"), "evidence_source": None,
                     "evidence_status": "verified (logical constraint, measured)"})
    return rows


def integrate(doc, analysis, cfg: dict, reference_rows: Optional[list] = None, models: Optional[dict] = None) -> dict:
    tech = technical_constraints(doc, analysis, cfg)
    sat = [r["satisfied"] for r in tech if r["satisfied"] is not None]
    lam = cfg["objective"]["lambda"] or {}
    dl = float(cfg["objective"]["default_lambda"])
    terms = []
    for r in tech:
        if r["error"] is not None:
            terms.append((r["parameter"], r["error"], lam.get(r["parameter"], dl)))
    for r in reference_rows or []:
        if r.get("error") is not None:
            terms.append((r["feature"], r["error"], lam.get(r["feature"].split(".")[0], dl)))
    L = float(sum(e * l for _, e, l in terms)) if terms else None
    return {
        "Q_technical": {"constraints": tech, "satisfied": int(sum(sat)), "checked": len(sat),
                        "note": "counts of satisfied measurable constraints; no weighting"},
        "Q_perceptual": {"value": None, "status": "no_model" if not models else "see F-parameters",
                         "note": "requires preference models trained on pairwise human judgments"},
        "Q_functional": {k: {"value": None, "type": "not_measured", "note": "requires a reading/usability experiment"}
                         for k in ("reading_speed", "comprehension", "search_time", "recall")},
        "objective_L": {"value": L, "n_terms": len(terms), "validated": bool(cfg["objective"]["validated"]),
                        "note": "Σ λ_k E_k with configured λ; NOT an objective quality score",
                        "terms": [{"key": k, "E": e, "lambda": l} for k, e, l in terms][:200]},
    }
