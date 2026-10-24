"""MODULE F — STYLE & AESTHETICS (spec §8): latent constructs.

Q_a = f_θ(X, S_target) is produced only by a trained preference model
(``edas.preference``).  Without training data every F-parameter except the
directly computable ones (F13 consistency, F14 reference similarity, F15
reference distance) is null with status ``no_model``.  No rule-based score
is ever substituted.  The input schema of every construct is recorded so
that a model can be trained later.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..mathcore.stats import cosine
from ..schema import MeasurementType as MT, ParameterResult, Status, make_result
from .common import spec

M = "aesthetics"

# Input features of each latent construct (parameter ids, flattened keys).
# These are *candidate model inputs* (hypotheses about what may matter), not
# rules: no direction or weight is implied, and whether a feature is
# predictive must be shown by a controlled preference test.
INPUTS = {
    "F01": ["A06", "A07", "A08", "A17", "B03", "B14", "C02", "D02", "D15", "E06"],
    # spec example s = [N_fonts, H_color, E_alignment, D_decoration, D_whitespace, C_visual, S_reference];
    # D_decoration has no measurement in this system yet and is omitted (see docs/spec_issues.md)
    "F02": ["B14", "C08", "A03", "A09", "D11", "F14"],
    "F03": ["A09", "A18", "A19", "B14", "C08", "D16"],
    "F04": ["C18", "C20", "B16", "D11", "E11"],
    "F05": ["C03", "C06", "B03", "B05", "A09", "F14"],
    "F06": ["B04", "B05", "B08", "C06", "A02", "D12"],
    "F07": ["B05", "B09", "B12", "D02", "A04"],
    "F08": ["A03", "A20", "B12", "B18", "C09", "B17"],
    "F09": ["B04", "B05", "B06", "B07", "B08", "B09", "B16", "BK07"],
    "F10": ["C03", "C05", "C06", "C08", "C10", "C12", "C13", "C20"],
    "F11": ["C18", "E11", "C06", "C08"],
    "F12": ["A02", "A04", "A06", "A07", "A08", "A14", "A15", "D09"],
    "F13": ["page style vectors"],
    "F14": ["document embedding", "reference embedding"],
    "F15": ["reference distance", "human novelty rating"],
    "F16": ["all of X"],
}
NAMES = {
    "F01": "magazine_likeness", "F02": "sophistication", "F03": "minimalism", "F04": "visual_harmony",
    "F05": "luxury_style_affinity", "F06": "modernity", "F07": "elegance", "F08": "professional_appearance",
    "F09": "typography_style_compatibility", "F10": "photography_style_compatibility",
    "F11": "color_harmony_preference", "F12": "layout_style_compatibility", "F13": "cross_page_style_consistency",
    "F14": "reference_similarity", "F15": "perceived_originality", "F16": "overall_human_preference",
}
SPECS = {}
for k, n in NAMES.items():
    if k == "F13":
        SPECS[k] = spec(k, n, M, unit="standardised^2", scope="document", mtype=MT.DIRECT,
                        formula="trace Cov(z_p) of page style vectors z_p (document- or reference-standardised); "
                                "mean distance to reference median when a profile is given",
                        definition="Dispersion of page style features (spec 8.4). Consistency is not quality.",
                        domain="[0, inf)")
    elif k == "F14":
        SPECS[k] = spec(k, n, M, unit="cosine", scope="document", mtype=MT.DIRECT,
                        formula="S_ref = e_design·e_ref / (|e_design||e_ref|), reference-standardised features",
                        definition="Spec 8.1 with e = standardised feature vector (same feature space).",
                        domain="[-1, 1]", missing="null without a reference profile")
    elif k == "F15":
        SPECS[k] = spec(k, n, M, unit="standardised distance", scope="document", mtype=MT.DIRECT,
                        formula="distance to the reference set (reported) ; human novelty rating (separate)",
                        definition="Spec 8.5: distance is NOT originality; human rating reported separately.",
                        domain="[0, inf)", missing="null without a reference profile / ratings")
    else:
        SPECS[k] = spec(k, n, M, unit="latent score", scope="document", mtype=MT.PREDICTED,
                        formula="Q_a = f_θ(X, S_target), Bradley–Terry trained on pairwise judgments",
                        definition=f"Latent construct; model inputs: {INPUTS[k]}",
                        domain="R", missing="null: no trained model / no labelled data")

STYLE_FEATURES = ["A06", "A07", "A08", "A09", "D02", "D15", "C03.area_weighted_mean", "C06.area_weighted_mean",
                  "B15", "A19.edge_density"]


def _get(params: dict, key: str):
    if "." in key:
        k, sub = key.split(".", 1)
        v = params.get(k)
        return v.get(sub) if isinstance(v, dict) else None
    v = params.get(key)
    return v if isinstance(v, (int, float)) else None


def analyze_document(page_params: list[dict], doc_vector: dict, reference: Optional[dict] = None,
                     models: Optional[dict] = None) -> list[ParameterResult]:
    out = []

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, scope="document", source=kw.pop("source", "derived"), **kw))

    # F13
    rows = [[_get(p, k) for k in STYLE_FEATURES] for p in page_params]
    cols = [i for i in range(len(STYLE_FEATURES)) if all(r[i] is not None for r in rows)]
    if len(rows) >= 2 and cols:
        X = np.array([[r[i] for i in cols] for r in rows], float)
        ref = (reference or {}).get("page_style_stats")
        if ref:
            mu = np.array([ref["mean"][STYLE_FEATURES[i]] for i in cols])
            sd = np.array([ref["std"][STYLE_FEATURES[i]] for i in cols])
            mode = "reference"
        else:
            mu, sd, mode = X.mean(0), X.std(0), "document"
        Z = (X - mu) / (sd + 1e-9)
        val = {"trace_covariance": float(np.trace(np.atleast_2d(np.cov(Z.T, bias=True))))}
        if ref:
            val["mean_distance_to_reference_center"] = float(np.linalg.norm(Z, axis=1).mean())
        R("F13", val, details={"features": [STYLE_FEATURES[i] for i in cols], "standardisation": mode},
          notes=["document standardisation makes per-feature variance 1 by construction; trace then counts "
                 "features unless a reference profile supplies μ, σ"] if mode == "document" else [])
    else:
        R("F13", None, status=Status.UNDEFINED, notes=["fewer than 2 pages or no complete style feature"])
    # F14 / F15
    if reference and reference.get("doc_vector_stats"):
        st = reference["doc_vector_stats"]
        keys = [k for k in st["mean"] if doc_vector.get(k) is not None and st["std"].get(k)]
        if keys:
            z = np.array([(doc_vector[k] - st["mean"][k]) / (st["std"][k] + 1e-9) for k in keys])
            zr = np.array([(st["median"][k] - st["mean"][k]) / (st["std"][k] + 1e-9) for k in keys])
            R("F14", cosine(z, zr) if np.linalg.norm(zr) > 0 else None,
              details={"features": keys, "note": "reference embedding = standardised reference median"})
            R("F15", {"reference_distance": float(np.sqrt(np.mean(z ** 2))), "human_novelty_rating": None},
              details={"features": keys}, notes=["distance from references is not originality"])
        else:
            R("F14", None, status=Status.NO_REFERENCE)
            R("F15", None, status=Status.NO_REFERENCE)
    else:
        R("F14", None, status=Status.NO_REFERENCE, notes=["no reference profile"])
        R("F15", None, status=Status.NO_REFERENCE, notes=["no reference profile; no human novelty ratings"])
    for k in NAMES:
        if k in ("F13", "F14", "F15"):
            continue
        m = (models or {}).get(k)
        if m is None:
            R(k, None, status=Status.NO_MODEL, details={"model_inputs": INPUTS[k]},
              notes=["no trained preference model: no score is produced"])
        else:
            pred = m.predict_document(doc_vector)
            R(k, pred, source="model",
              details={"claim_type": "controlled_preference_test" if m.validated else "subjective_hypothesis",
                       "validation": m.validation_summary()},
              notes=[] if m.validated else ["model not validated on held-out groups: hypothesis only"])
    return out
