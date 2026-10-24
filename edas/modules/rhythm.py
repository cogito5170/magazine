"""MODULE E — VISUAL RHYTHM (spec §7): the page sequence as a time series.

Page feature vector (fixed order):
    x_p = [D_image (A07), D_text (A08), D_white (A09), B (D02), H_sal (D15),
           edge density (A19), object count (A19)]
Spec symbol H_p in x_p is ambiguous (H also denotes page height); it is
interpreted as an entropy feature, the saliency entropy D15 (reported in
docs/spec_issues.md).
Only real page sequences are analysed: independent images are never
arranged into a pseudo-sequence.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np

from ..mathcore.color import ciede2000, rgb_histogram, rgb_to_lab
from ..mathcore.stats import autocorrelation, cosine, js_divergence, shannon_entropy, sign_changes, summary, wasserstein1
from ..schema import MeasurementType as MT, ParameterResult, Status, make_result
from .common import spec

M = "rhythm"
FEATURES = ["D_image", "D_text", "D_white", "B", "H_saliency", "edge_density", "object_count"]
SPECS = {s.parameter_id: s for s in [
    spec("E01", "image_density_change", M, unit="ratio", scope="document",
         formula="ΔD_i(p) = |D_i(p+1) - D_i(p)|", domain="[0, 1]^(P-1)"),
    spec("E02", "text_density_change", M, unit="ratio", scope="document",
         formula="ΔD_t(p) = |D_t(p+1) - D_t(p)|", domain="[0, 1]^(P-1)"),
    spec("E03", "whitespace_change", M, unit="ratio", scope="document",
         formula="ΔD_w(p) = |D_w(p+1) - D_w(p)|", domain="[0, 1]^(P-1)"),
    spec("E04", "complexity_change", M, unit="mixed", scope="document",
         formula="|C(p+1) - C(p)| for each A19 component", domain="[0, inf)^(P-1)"),
    spec("E05", "page_transition_magnitude", M, unit="standardised", scope="document",
         formula="Δ_p = ||W (x_{p+1} - x_p)||_2, W = diag(1/(σ_k+ε))",
         definition="σ_k from the reference profile when given, else from the document pages.",
         domain="[0, inf)^(P-1)"),
    spec("E06", "mean_transition", M, unit="standardised", scope="document",
         formula="mean_p Δ_p", domain="[0, inf)"),
    spec("E07", "transition_variance", M, unit="standardised^2", scope="document",
         formula="Var(Δ_p)", domain="[0, inf)"),
    spec("E08", "feature_autocorrelation", M, unit="correlation", scope="document",
         formula="ρ(k) = Σ_{p<=P-k}(d_p-d̄)(d_{p+k}-d̄) / Σ_p (d_p-d̄)^2", domain="[-1, 1]",
         missing="undefined when the denominator is 0"),
    spec("E09", "period_candidates", M, unit="pages", scope="document", mtype=MT.ESTIMATED,
         formula="local maxima k>=2 of ρ(k) with ρ(k) > 2/sqrt(P)", domain="N",
         notes=["unreliable with few pages (flagged)"]),
    spec("E10", "layout_similarity", M, unit="cosine", scope="document",
         formula="cos(z_p, z_{p+1}), z = document-standardised x_p", domain="[-1, 1]^(P-1)"),
    spec("E11", "color_transition", M, unit="bits / ΔE00", scope="document",
         formula="JSD(RGB hist_p, RGB hist_{p+1}); CIEDE2000(mean Lab_p, mean Lab_{p+1})", domain="[0,1]; [0,100]"),
    spec("E12", "typography_transition", M, unit="bits / pt", scope="document",
         formula="JSD(face usage_p, face usage_{p+1}); W1(sizes_p, sizes_{p+1})", domain="[0,1]; [0,inf)"),
    spec("E13", "rhythm_entropy", M, unit="bits", scope="document",
         formula="H of page states; state = (bin(D_image), bin(D_text)) with configured edges (tertiles)",
         domain="[0, log2 9]"),
    spec("E14", "direction_changes", M, unit="count", scope="document",
         formula="# sign changes of diff(D_content) (zero differences skipped)", domain="N",
         notes=["few pages limit statistical interpretation (flagged)"]),
]}


def _scalar(v, key=None):
    if v is None:
        return None
    if key is not None:
        v = v.get(key) if isinstance(v, dict) else None
    return float(v) if isinstance(v, (int, float)) else None


def page_vector(params: dict) -> list[Optional[float]]:
    a19 = params.get("A19") or {}
    return [_scalar(params.get("A07")), _scalar(params.get("A08")), _scalar(params.get("A09")),
            _scalar(params.get("D02")), _scalar(params.get("D15")),
            _scalar(a19, "edge_density"), _scalar(a19, "object_count")]


def analyze_document(pages, page_params: list[dict], reference: Optional[dict] = None,
                     cfg: Optional[dict] = None) -> list[ParameterResult]:
    cfg = cfg or {}
    out: list[ParameterResult] = []
    P = len(page_params)

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, scope="document", source=kw.pop("source", "derived"), **kw))

    if P < 2:
        for pid in SPECS:
            R(pid, None, status=Status.UNDEFINED, notes=["fewer than 2 pages: no sequence"])
        return out
    X = np.array([[np.nan if v is None else v for v in page_vector(p)] for p in page_params], float)

    def diffs(col):
        c = X[:, col]
        return [None if np.isnan(a) or np.isnan(b) else float(abs(b - a)) for a, b in zip(c[:-1], c[1:])]

    R("E01", diffs(0))
    R("E02", diffs(1))
    R("E03", diffs(2))
    R("E04", {"edge_density": diffs(5), "object_count": diffs(6)},
      details={"region_count": [abs((page_params[i + 1].get("A19") or {}).get("region_count", 0)
                                    - (page_params[i].get("A19") or {}).get("region_count", 0)) for i in range(P - 1)]})
    ok = ~np.isnan(X).any(1)
    Xf = np.where(np.isnan(X), np.nanmean(X, 0), X)
    ref_sd = (reference or {}).get("rhythm_feature_std")
    sd = np.array(ref_sd) if ref_sd else Xf.std(0)
    Wd = 1.0 / (sd + 1e-9)
    deltas = [float(np.linalg.norm(Wd * (Xf[p + 1] - Xf[p]))) for p in range(P - 1)]
    note = [] if ok.all() else ["missing features imputed with the document mean for E05–E10"]
    R("E05", deltas, details={"features": FEATURES, "W_diag": Wd, "sigma_source": "reference" if ref_sd else "document"},
      notes=note)
    R("E06", float(np.mean(deltas)))
    R("E07", float(np.var(deltas)))
    kmax = max(1, P // 2)
    ac = {}
    for i, f in enumerate(FEATURES):
        ac[f] = [autocorrelation(Xf[:, i], k) for k in range(1, kmax + 1)]
    ac["transition"] = [autocorrelation(deltas, k) for k in range(1, max(1, (P - 1) // 2) + 1)]
    R("E08", ac, details={"lags": list(range(1, kmax + 1))})
    bound = 2 / np.sqrt(P)
    per = {}
    for f, rho in ac.items():
        cands = []
        for k in range(1, len(rho)):
            r = rho[k]
            if r is None:
                continue
            left = rho[k - 1] if rho[k - 1] is not None else -np.inf
            right = rho[k + 1] if k + 1 < len(rho) and rho[k + 1] is not None else -np.inf
            if r > left and r >= right and r > bound:
                cands.append(k + 1)
        per[f] = cands
    minp = int(((cfg.get("rhythm") or {}).get("min_pages_for_period")) or 6)
    R("E09", per, status=Status.INSUFFICIENT_DATA if P < minp else None,
      details={"significance_bound": bound, "pages": P, "min_pages_for_period": minp})
    Z = (Xf - Xf.mean(0)) / (Xf.std(0) + 1e-9)
    R("E10", [cosine(Z[p], Z[p + 1]) for p in range(P - 1)],
      details={"raw_cosine": [cosine(Xf[p], Xf[p + 1]) for p in range(P - 1)]})
    hists = [rgb_histogram(pm.render[::2, ::2], 8) for pm in pages]
    labs = [rgb_to_lab(pm.render[::4, ::4].reshape(-1, 3)).mean(0) for pm in pages]
    R("E11", {"jsd_bits": [js_divergence(hists[p], hists[p + 1]) for p in range(P - 1)],
              "delta_e00_mean_color": [float(ciede2000(labs[p], labs[p + 1])) for p in range(P - 1)]},
      source="raster")
    faces, sizes = [], []
    for pm in pages:
        ink = [c for c in pm.chars if not c.text.isspace()]
        faces.append(Counter(c.font_key or "?" for c in ink))
        sizes.append([c.size for c in ink])
    allf = sorted({f for c in faces for f in c})
    jsd, w1 = [], []
    for p in range(P - 1):
        a = [faces[p].get(f, 0) for f in allf]
        b = [faces[p + 1].get(f, 0) for f in allf]
        jsd.append(js_divergence(a, b) if sum(a) and sum(b) else None)
        w1.append(wasserstein1(sizes[p], sizes[p + 1]) if sizes[p] and sizes[p + 1] else None)
    R("E12", {"face_jsd_bits": jsd, "size_w1_pt": w1}, source="pdf_objects")
    edges = list((cfg.get("rhythm") or {}).get("state_bins") or [0, 1 / 3, 2 / 3, 1.0000001])
    states = []
    for p in range(P):
        di, dt_ = X[p, 0], X[p, 1]
        if np.isnan(di) or np.isnan(dt_):
            continue
        states.append((int(np.digitize(di, edges[1:-1])), int(np.digitize(dt_, edges[1:-1]))))
    cnt = Counter(states)
    R("E13", shannon_entropy(list(cnt.values())) if states else None,
      details={"rule": f"state = (bin(D_image), bin(D_text)), bin edges {edges}", "states": [list(s) for s in states],
               "max_bits": float(np.log2(9))})
    dc = [p.get("A06") for p in page_params]
    minsc = int(((cfg.get("rhythm") or {}).get("min_pages_for_sign_changes")) or 5)
    sc = sign_changes([v for v in dc if v is not None])
    R("E14", sc, status=Status.INSUFFICIENT_DATA if P < minsc else None,
      details={"series": "A06 content occupancy", "D_image": sign_changes(list(Xf[:, 0])),
               "D_text": sign_changes(list(Xf[:, 1])), "pages": P})
    return out
