"""MODULE D — COMPOSITION (spec §6): formal relations between objects.

Visual weight model (D1), fixed and *not learned*:
    w_i = (A_i / A_p) · c_i · s_i
    c_i = |mean Y(box_i) − Y_background|   (linear luminance contrast)
    s_i = mean saliency(box_i) / mean saliency(page)
Symmetry and centring are reported as measurements, never as quality.
"""
from __future__ import annotations

import numpy as np

from ..mathcore.color import rgb_to_lab, relative_luminance, ciede2000
from ..mathcore.geometry import area, center, min_distance
from ..mathcore.imaging import gaussian_blur, local_maxima, resize
from ..mathcore.stats import shannon_entropy, summary
from ..schema import MeasurementType as MT, ParameterResult, Status, make_result
from .common import PageContext, spec

M = "composition"
WEIGHT_MODEL = "w = area_share * |ΔY to background| * relative saliency (v1, fixed, not learned)"
SPECS = {s.parameter_id: s for s in [
    spec("D01", "visual_center_of_mass", M, unit="normalized", mtype=MT.ESTIMATED,
         formula="x_c = Σ w_i x_i / Σ w_i, y_c likewise; " + WEIGHT_MODEL, domain="[0, 1]^2",
         missing="undefined when Σ w_i = 0"),
    spec("D02", "center_deviation", M, unit="normalized", mtype=MT.ESTIMATED,
         formula="B = sqrt(((x_c - W/2)/W)^2 + ((y_c - H/2)/H)^2)", domain="[0, 0.7072]"),
    spec("D03", "horizontal_symmetry", M, unit="ratio",
         formula="S_h = 1 - Σ|M - flipLR(M)| / (2 Σ M), M = |Y - Y_bg|", domain="[0, 1]",
         notes=["spec phrase 'normalised difference' = d; reported S = 1 - d (d in details)"]),
    spec("D04", "vertical_symmetry", M, unit="ratio",
         formula="S_v = 1 - Σ|M - flipUD(M)| / (2 Σ M)", domain="[0, 1]"),
    spec("D05", "asymmetry", M, unit="ratio", formula="1 - S_h, 1 - S_v", domain="[0, 1]"),
    spec("D06", "object_area_contrast", M, unit="ratio", formula="R_A = A_max / A_min (A > 0)", domain="[1, inf)"),
    spec("D07", "object_size_entropy", M, unit="bits", formula="H = -Σ p_i log2 p_i, p_i = A_i / Σ A",
         domain="[0, log2 N]"),
    spec("D08", "distance_variance", M, unit="pt^2", formula="V_d = Var(d_ij)", domain="[0, inf)",
         missing="undefined for N < 2"),
    spec("D09", "alignment_consistency", M, unit="ratio",
         formula="#{objects on an edge/centre line shared with another object} / N", domain="[0, 1]"),
    spec("D10", "proportions", M, unit="ratio", formula="distributions of w/h and of successive sorted area ratios",
         domain="(0, inf)"),
    spec("D11", "visual_contrast", M, unit="mixed",
         formula="mean pairwise |ΔY|, |Δ log A|, |Δ log(w/h)|", domain="[0, inf)^3"),
    spec("D12", "tension_proxy", M, unit="vector", mtype=MT.ESTIMATED,
         formula="[E_a (A03 horizontal), B (D02), log R_A (D06)]", domain="R^3",
         notes=["a feature vector; not psychological tension and not combined into a score"]),
    spec("D13", "object_clustering", M, unit="mixed",
         formula="graph G: edge if d_ij <= link·diag; components, density, mean clustering coefficient",
         domain="components >= 1; density, clustering in [0, 1]"),
    spec("D14", "object_repetition", M, unit="ratio",
         formula="#{objects with a same-kind partner: |ΔA|/A <= r_s, |Δ aspect|/aspect <= r_a, ΔE00 <= e} / N",
         domain="[0, 1]"),
    spec("D15", "saliency_entropy", M, unit="bits", mtype=MT.ESTIMATED,
         formula="H = -Σ p log2 p, p = normalised spectral-residual saliency map", domain="[0, log2 N_px]"),
    spec("D16", "focal_point_count", M, unit="count", mtype=MT.ESTIMATED,
         formula="local maxima of the saliency map >= rel·max with suppression radius", domain="N"),
]}


def _obj_stats(ctx: PageContext):
    pm = ctx.pm
    Y = ctx.luminance
    bgY = float(relative_luminance(np.asarray(pm.background_rgb or (1, 1, 1))))
    sal = ctx.saliency
    sal_r = resize(sal, Y.shape[1], Y.shape[0])
    smean = sal_r.mean()
    out = []
    for o in pm.objects:
        x0, y0, x1, y1 = pm.to_px(o.box)
        if x1 <= x0 or y1 <= y0:
            continue
        reg = Y[y0:y1, x0:x1]
        rgb = pm.render[y0:y1, x0:x1].reshape(-1, 3)
        out.append({"obj": o, "Y": float(reg.mean()), "c": abs(float(reg.mean()) - bgY),
                    "s": float(sal_r[y0:y1, x0:x1].mean() / smean) if smean > 0 else 0.0,
                    "A": area(o.box) / pm.area, "lab": rgb_to_lab(rgb.mean(0)[None])[0]})
    return out, bgY


def _shared_lines(vals: np.ndarray, tol: float) -> set:
    idx = set()
    order = np.argsort(vals)
    v = vals[order]
    start = 0
    for i in range(1, len(v) + 1):
        if i == len(v) or v[i] - v[i - 1] > tol:
            if i - start >= 2:
                idx.update(order[start:i].tolist())
            start = i
    return idx


def analyze_page(ctx: PageContext, layout_results: dict) -> list[ParameterResult]:
    pm, cfg = ctx.pm, ctx.cfg
    W, H = pm.width, pm.height
    out: list[ParameterResult] = []
    src, pi = ctx.source, pm.index

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, source=kw.pop("source", src), page_index=pi, **kw))

    st, bgY = _obj_stats(ctx)
    N = len(st)
    w = np.array([s["A"] * s["c"] * s["s"] for s in st]) if st else np.array([])
    if N and w.sum() > 0:
        cs = np.array([center(s["obj"].box) for s in st])
        xc, yc = float((w * cs[:, 0]).sum() / w.sum()), float((w * cs[:, 1]).sum() / w.sum())
        Ys, Xs = np.mgrid[0:ctx.saliency.shape[0], 0:ctx.saliency.shape[1]]
        sx = float((ctx.saliency * (Xs + 0.5)).sum() / ctx.saliency.shape[1])
        sy = float((ctx.saliency * (Ys + 0.5)).sum() / ctx.saliency.shape[0])
        R("D01", [xc / W, yc / H], details={"weight_model": WEIGHT_MODEL, "learned": False,
                                            "weights": {s["obj"].id: float(x) for s, x in zip(st, w)},
                                            "saliency_pixel_centroid": [sx, sy]})
        B = float(np.hypot((xc - W / 2) / W, (yc - H / 2) / H))
        R("D02", B)
    else:
        B = None
        R("D01", None, status=Status.UNDEFINED, notes=["sum of visual weights is 0"])
        R("D02", None, status=Status.UNDEFINED)
    from ..mathcore.imaging import resize_max
    Ysm, _ = resize_max(ctx.luminance, 300)
    Mmap = np.abs(Ysm - bgY)
    tot = Mmap.sum()
    if tot > 0:
        dh = float(np.abs(Mmap - Mmap[:, ::-1]).sum() / (2 * tot))
        dv = float(np.abs(Mmap - Mmap[::-1, :]).sum() / (2 * tot))
        R("D03", 1 - dh, details={"d": dh, "feature_map": "|Y - Y_background|"}, source="raster")
        R("D04", 1 - dv, details={"d": dv}, source="raster")
        R("D05", {"horizontal": dh, "vertical": dv}, source="raster")
    else:
        for pid in ("D03", "D04", "D05"):
            R(pid, None, status=Status.UNDEFINED, notes=["blank page"])
    areas = np.array([s["A"] for s in st if s["A"] > 0])
    if areas.size:
        RA = float(areas.max() / areas.min())
        R("D06", RA)
        p = areas / areas.sum()
        Hs = shannon_entropy(p)
        R("D07", Hs, details={"normalised": Hs / np.log2(areas.size) if areas.size > 1 else None})
    else:
        RA = None
        R("D06", None, status=Status.UNDEFINED)
        R("D07", None, status=Status.UNDEFINED)
    boxes = [s["obj"].box for s in st]
    diag = float(np.hypot(W, H))
    if N >= 2:
        d = np.array([min_distance(boxes[i], boxes[j]) for i in range(N) for j in range(i + 1, N)])
        R("D08", float(d.var()), details={"normalised_by_diag2": float(d.var() / diag ** 2)})
    else:
        R("D08", None, status=Status.UNDEFINED, notes=["N < 2"])
    if N >= 1:
        b = np.array(boxes)
        tol = float(cfg["layout"]["align_tolerance_fraction"])
        sh = set()
        for col, ext in ((0, W), (2, W), (1, H), (3, H)):
            sh |= _shared_lines(b[:, col], tol * ext)
        sh |= _shared_lines(0.5 * (b[:, 0] + b[:, 2]), tol * W)
        sh |= _shared_lines(0.5 * (b[:, 1] + b[:, 3]), tol * H)
        R("D09", len(sh) / N)
        asp = (b[:, 2] - b[:, 0]) / np.maximum(b[:, 3] - b[:, 1], 1e-9)
        sa = np.sort(areas)[::-1] if areas.size else np.array([])
        R("D10", {"aspect": summary(asp), "successive_area_ratio": summary(sa[:-1] / sa[1:]) if sa.size > 1 else None})
    else:
        R("D09", None, status=Status.UNDEFINED)
        R("D10", None, status=Status.UNDEFINED)
    if N >= 2:
        Yv = np.array([s["Y"] for s in st])
        lA = np.log(np.maximum([s["A"] for s in st], 1e-12))
        b = np.array(boxes)
        la = np.log(np.maximum((b[:, 2] - b[:, 0]) / np.maximum(b[:, 3] - b[:, 1], 1e-9), 1e-9))
        iu = np.triu_indices(N, 1)
        R("D11", {"luminance": float(np.abs(Yv[:, None] - Yv[None])[iu].mean()),
                  "log_area": float(np.abs(lA[:, None] - lA[None])[iu].mean()),
                  "log_aspect": float(np.abs(la[:, None] - la[None])[iu].mean())})
    else:
        R("D11", None, status=Status.UNDEFINED)
    ea = (layout_results.get("A03") or {}).get("horizontal") if isinstance(layout_results.get("A03"), dict) else None
    R("D12", {"alignment_error": ea, "center_deviation": B, "log_area_contrast": float(np.log(RA)) if RA else None},
      notes=["vector only; components are not weighted or summed"])
    if N >= 1:
        link = float(cfg["layout"]["cluster_link_fraction"]) * diag
        A = np.zeros((N, N), bool)
        for i in range(N):
            for j in range(i + 1, N):
                if min_distance(boxes[i], boxes[j]) <= link:
                    A[i, j] = A[j, i] = True
        seen, comps = set(), 0
        for i in range(N):
            if i in seen:
                continue
            comps += 1
            stack = [i]
            while stack:
                k = stack.pop()
                if k in seen:
                    continue
                seen.add(k)
                stack.extend(np.nonzero(A[k])[0].tolist())
        cc = []
        for i in range(N):
            nb = np.nonzero(A[i])[0]
            if len(nb) >= 2:
                sub = A[np.ix_(nb, nb)]
                cc.append(sub.sum() / (len(nb) * (len(nb) - 1)))
            else:
                cc.append(0.0)
        R("D13", {"components": comps, "density": float(A.sum() / (N * (N - 1))) if N > 1 else 0.0,
                  "mean_clustering_coefficient": float(np.mean(cc))}, details={"link_distance_pt": link})
        rc = cfg["composition"]["repetition"]
        rep = 0
        for i in range(N):
            for j in range(N):
                if i == j or st[i]["obj"].kind != st[j]["obj"].kind:
                    continue
                Ai, Aj = st[i]["A"], st[j]["A"]
                bi, bj = boxes[i], boxes[j]
                ai = (bi[2] - bi[0]) / max(bi[3] - bi[1], 1e-9)
                aj = (bj[2] - bj[0]) / max(bj[3] - bj[1], 1e-9)
                if (abs(Ai - Aj) / max(Ai, Aj, 1e-12) <= rc["size_rel"] and abs(ai - aj) / max(ai, aj) <= rc["aspect_rel"]
                        and float(ciede2000(st[i]["lab"], st[j]["lab"])) <= rc["delta_e"]):
                    rep += 1
                    break
        R("D14", rep / N, details={"thresholds": rc})
    else:
        R("D13", None, status=Status.UNDEFINED)
        R("D14", None, status=Status.UNDEFINED)
    sal = ctx.saliency
    Hs = shannon_entropy(sal)
    R("D15", Hs, details={"normalised": Hs / np.log2(sal.size), "model": "spectral residual"}, source="raster")
    sm = gaussian_blur(sal, 2.0)
    r = max(1, int(float(cfg["composition"]["focal_radius_fraction"]) * max(sm.shape)))
    pk = local_maxima(sm, r, float(cfg["composition"]["focal_threshold_rel"]) * sm.max())
    R("D16", len(pk), details={"peaks_normalised": [[x / sm.shape[1], y / sm.shape[0]] for y, x, _ in pk]},
      source="raster")
    return out
