"""MODULE A — LAYOUT (spec §3): spatial arrangement of layout objects."""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from ..mathcore.geometry import (area, center, connected_box_groups, iou, min_distance,
                                 union_area_in_cells)
from ..mathcore.imaging import label_components
from ..mathcore.stats import summary
from ..schema import ErrorKind, MeasurementType as MT, ParameterResult, Status, make_result
from .common import PageContext, spec

M = "layout"
SPECS = {s.parameter_id: s for s in [
    spec("A01", "page_aspect_ratio", M, unit="ratio", formula="r_p = W_p / H_p", domain="(0, inf)",
         definition="Page width over height (CropBox, after /Rotate).", error=ErrorKind.TWO_SIDED),
    spec("A02", "grid_structure", M, unit="pt", mtype=MT.ESTIMATED,
         formula="W = m_l + m_r + n c + (n-1) g ; fitted to object edges",
         definition="Column grid (n, c, g, m_l, m_r) and row grid estimated from non-bleed object edges. "
                    "For each n the gutter g maximising edge inliers (|edge-line| <= tol) is found; n is "
                    "chosen by the minimum binomial tail probability of the inlier count under "
                    "uniformly random edges (no complexity weight).",
         domain="n in {1..max_columns}; c,g,m >= 0",
         missing="null when no non-bleed object exists",
         notes=["the identity W = m_l + m_r + n c + (n-1) g holds by construction"]),
    spec("A03", "alignment_error", M, unit="normalized_distance",
         formula="E_a = 1/(N W) Σ_i |x_i - g(x_i)|  (x: left edges vs vertical grid lines; "
                 "y: top edges vs horizontal grid lines, divided by H)",
         definition="Mean distance of object reference edges to the nearest valid grid line of the fitted "
                    "grid (column starts and ends). Bleed objects excluded.", domain="[0, 1]",
         error=ErrorKind.MAX, missing="null when the grid is undefined",
         notes=["grid departures can be intentional: not a quality verdict on its own"]),
    spec("A04", "margin_ratios", M, unit="ratio", formula="M_l=m_l/W, M_r=m_r/W, M_t=m_t/H, M_b=m_b/H",
         definition="Distance from page edge to the union box of non-bleed objects.", domain="[0, 1]",
         error=ErrorKind.TWO_SIDED, missing="null when every object bleeds"),
    spec("A05", "margin_asymmetry", M, unit="ratio", formula="E_m = |M_l - M_r| ; |M_t - M_b|",
         definition="Absolute difference of opposite margin ratios.", domain="[0, 1]", error=ErrorKind.TWO_SIDED),
    spec("A06", "content_occupancy", M, unit="ratio", formula="D_c = A_content_union / A_p",
         definition="Union area of text-line, image and vector boxes clipped to the page.", domain="[0, 1]",
         error=ErrorKind.TWO_SIDED),
    spec("A07", "image_occupancy", M, unit="ratio", formula="D_i = A_image_union / A_p",
         definition="Union area of visible image boxes.", domain="[0, 1]", error=ErrorKind.TWO_SIDED),
    spec("A08", "text_occupancy", M, unit="ratio", formula="D_t = A_text_union / A_p",
         definition="Union area of text line boxes (tight glyph extents). Block-box variant in details.",
         domain="[0, 1]", error=ErrorKind.TWO_SIDED),
    spec("A09", "whitespace_ratio", M, unit="ratio", formula="D_w = 1 - D_c", domain="[0, 1]",
         definition="Complement of content occupancy.", error=ErrorKind.TWO_SIDED),
    spec("A10", "object_distances", M, unit="pt",
         formula="d_ij = min_{a in B_i, b in B_j} ||a - b||_2", domain="[0, diag]",
         definition="Pairwise shortest Euclidean distances between object boxes (0 if overlapping); "
                    "summary statistics as value.", missing="undefined for N < 2"),
    spec("A11", "object_overlap", M, unit="ratio", formula="IoU_ij = |B_i ∩ B_j| / |B_i ∪ B_j|",
         definition="Pairwise IoU; value summarises overlapping pairs.", domain="[0, 1]",
         missing="undefined for N < 2"),
    spec("A12", "object_size_variance", M, unit="ratio^2", formula="V_A = Var(A_1/A_p, ..., A_N/A_p)",
         definition="Population variance of object area shares.", domain="[0, 0.25]"),
    spec("A13", "object_position_variance", M, unit="normalized^2",
         formula="Var(x̃_c), Var(ỹ_c) of object centres", domain="[0, 0.25]",
         definition="Population variance of normalised object centre coordinates."),
    spec("A14", "horizontal_alignment_frequency", M, unit="ratio",
         formula="#{pairs sharing top, bottom or centre-y within tol*H} / (N(N-1)/2)", domain="[0, 1]",
         definition="Share of object pairs on a common horizontal reference line.",
         missing="undefined for N < 2"),
    spec("A15", "vertical_alignment_frequency", M, unit="ratio",
         formula="#{pairs sharing left, right or centre-x within tol*W} / (N(N-1)/2)", domain="[0, 1]",
         definition="Share of object pairs on a common vertical reference line.",
         missing="undefined for N < 2"),
    spec("A16", "spatial_clustering", M, unit="normalized_distance",
         formula="nn_i = min_j ||c̃_i - c̃_j|| ; Clark–Evans R = mean(nn) / (0.5/sqrt(N))",
         domain="nn in [0, sqrt 2]; R in [0, 2.15]",
         definition="Nearest-neighbour distance distribution of normalised object centres; R<1 clustered, "
                    "R≈1 random, R>1 dispersed (reference area = unit page).", missing="undefined for N < 2"),
    spec("A17", "whitespace_distribution", M, unit="ratio",
         formula="M_jk = 1 - |content ∩ cell_jk| / |cell_jk|", domain="[0, 1]^(ny x nx)",
         definition="Empty share of each cell of a uniform ny x nx partition (exact union area)."),
    spec("A18", "object_density", M, unit="1/pt^2", formula="ρ = N / A_p", domain="[0, inf)",
         definition="Number of layout objects per unit page area."),
    spec("A19", "page_complexity", M, unit="mixed",
         formula="(N objects, D_edge = N_edge_px / N_px of page render, regions = connected groups of "
                 "touching layout-object boxes)", domain="N>=0; D_edge in [0,1]; regions>=0",
         definition="Three separate complexity features (not combined)."),
    spec("A20", "grid_consistency", M, unit="normalized_distance", scope="document",
         formula="g_p = [c/W, g/W, m_l/W, m_r/W]; mean_{p<q} ||g_p - g_q||_2 ; share of pages with modal n",
         definition="Between-page dispersion of estimated grid geometry.",
         missing="undefined for fewer than 2 pages with a grid"),
]}


# --------------------------------------------------------------------------
def _binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k), X ~ Binomial(n, p)."""
    if k <= 0:
        return 1.0
    if p <= 0:
        return 0.0
    if p >= 1:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq
             for i in range(k, n + 1)]
    m = max(terms)
    return float(min(1.0, math.exp(m) * sum(math.exp(t - m) for t in terms)))


def fit_grid(starts: np.ndarray, ends: np.ndarray, extent: float, max_n: int, step: float,
             max_g_frac: float, tol: float) -> Optional[dict]:
    """1-D grid fit (columns or rows) from object edge coordinates.

    For each n and gutter g (searched with ``step``), an edge is an inlier if it
    lies within ``tol`` of a line of its kind (starts vs column starts, ends vs
    column ends).  Per n, g maximises the inlier count (ties: smaller mean
    distance).  n is selected by the smallest binomial tail probability
    P(X >= k | N edges, chance = 2·tol·n / content extent): the column count
    whose alignment is least likely under uniformly random edges.  This needs
    no complexity weight.
    """
    if starts.size == 0:
        return None
    m0 = float(starts.min())
    m1 = float(extent - ends.max())
    Wc = extent - m0 - m1
    if Wc <= 0:
        return None
    Nedges = int(starts.size + ends.size)
    cands = []
    for n in range(1, max_n + 1):
        gs = np.array([0.0]) if n == 1 else np.arange(0.0, max_g_frac * Wc + 1e-9, step)
        best = None
        for g in gs:
            c = (Wc - (n - 1) * g) / n
            if c <= 0:
                break
            s = m0 + np.arange(n) * (c + g)
            e = s + c
            ds = np.abs(starts[:, None] - s[None, :]).min(1)
            de = np.abs(ends[:, None] - e[None, :]).min(1)
            k = int((ds <= tol).sum() + (de <= tol).sum())
            cost = float(0.5 * (ds.mean() + de.mean()))
            if best is None or k > best[0] or (k == best[0] and cost < best[1] - 1e-12):
                best = (k, cost, float(c), float(g))
        if best:
            chance = min(1.0, 2 * tol * n / Wc)
            cands.append({"n": n, "inliers": best[0], "cost": best[1], "c": best[2], "g": best[3],
                          "chance": chance, "p_value": _binom_sf(best[0], Nedges, chance)})
    if not cands:
        return None
    chosen = min(cands, key=lambda c: (c["p_value"], c["n"]))
    lines_s = [m0 + k * (chosen["c"] + chosen["g"]) for k in range(chosen["n"])]
    lines_e = [s + chosen["c"] for s in lines_s]
    return {"n": chosen["n"], "c": chosen["c"], "g": chosen["g"], "m_start": m0, "m_end": m1,
            "fit_cost": chosen["cost"], "inliers": chosen["inliers"], "edges": Nedges,
            "p_value": chosen["p_value"], "tolerance": tol, "starts": lines_s, "ends": lines_e,
            "identity_residual": float(extent - (m0 + m1 + chosen["n"] * chosen["c"]
                                                  + (chosen["n"] - 1) * chosen["g"])),
            "candidates": [{k: c[k] for k in ("n", "inliers", "cost", "p_value")} for c in cands]}


def page_grid(ctx: PageContext) -> dict:
    pm, cfg = ctx.pm, ctx.cfg["layout"]["grid"]
    objs = [o for o in pm.objects if not o.bleed]
    if not objs:
        return {"columns": None, "rows": None, "objects": []}
    b = np.array([o.box for o in objs])
    step = float(cfg["gutter_step_pt"]) * (pm.width / 600.0 if pm.unit == "px" else 1.0)
    tol = float(ctx.cfg["layout"]["align_tolerance_fraction"])
    cols = fit_grid(b[:, 0], b[:, 2], pm.width, int(cfg["max_columns"]), step,
                    float(cfg["max_gutter_fraction"]), tol * pm.width)
    rows = fit_grid(b[:, 1], b[:, 3], pm.height, int(cfg["max_rows"]), step * pm.height / pm.width,
                    float(cfg["max_gutter_fraction"]), tol * pm.height)
    return {"columns": cols, "rows": rows, "objects": [o.id for o in objs]}


def alignment_error(coords: np.ndarray, lines: list[float], extent: float) -> Optional[float]:
    if coords.size == 0 or not lines:
        return None
    L = np.asarray(lines)
    return float(np.abs(coords[:, None] - L[None, :]).min(1).sum() / (coords.size * extent))


def _pairs_sharing(vals: list[np.ndarray], tol: float) -> tuple[int, int]:
    n = vals[0].size
    hit = 0
    for i in range(n):
        for j in range(i + 1, n):
            if any(abs(v[i] - v[j]) <= tol for v in vals):
                hit += 1
    return hit, n * (n - 1) // 2


def analyze_page(ctx: PageContext) -> tuple[list[ParameterResult], dict]:
    pm, cfg = ctx.pm, ctx.cfg
    W, H, Ap = pm.width, pm.height, pm.area
    src, pi = ctx.source, pm.index
    out: list[ParameterResult] = []

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, source=kw.pop("source", src), page_index=pi, **kw))

    R("A01", W / H, source="pdf_objects" if pm.unit == "pt" else "raster")

    grid = page_grid(ctx)
    cols, rows = grid["columns"], grid["rows"]
    if cols:
        R("A02", {"n": cols["n"], "c": cols["c"], "g": cols["g"], "m_l": cols["m_start"],
                  "m_r": cols["m_end"], "rows_n": rows["n"] if rows else None,
                  "row_r": rows["c"] if rows else None, "row_g": rows["g"] if rows else None,
                  "m_t": rows["m_start"] if rows else None, "m_b": rows["m_end"] if rows else None},
          details={"columns": cols, "rows": rows, "unit": pm.unit},
          confidence={"fit_cost_pt": cols["fit_cost"], "n_objects": len(grid["objects"])})
    else:
        R("A02", None, status=Status.UNDEFINED, notes=["no non-bleed object"])

    nb = [o for o in pm.objects if not o.bleed]
    if cols and nb:
        xs = np.array([o.box[0] for o in nb])
        xr = np.array([o.box[2] for o in nb])
        ys = np.array([o.box[1] for o in nb])
        vlines = cols["starts"] + cols["ends"]
        hlines = (rows["starts"] + rows["ends"]) if rows else []
        R("A03", {"horizontal": alignment_error(xs, vlines, W), "vertical": alignment_error(ys, hlines, H)},
          details={"right_edge_variant": alignment_error(xr, vlines, W), "N": len(nb),
                   "bleed_excluded": len(pm.objects) - len(nb)})
    else:
        R("A03", None, status=Status.UNDEFINED)

    if nb:
        ub = np.array([o.box for o in nb])
        ml, mt = ub[:, 0].min(), ub[:, 1].min()
        mr, mb = W - ub[:, 2].max(), H - ub[:, 3].max()
        M4 = {"M_l": ml / W, "M_r": mr / W, "M_t": mt / H, "M_b": mb / H}
        R("A04", M4, details={"m_l": ml, "m_r": mr, "m_t": mt, "m_b": mb, "unit": pm.unit})
        R("A05", {"horizontal": abs(M4["M_l"] - M4["M_r"]), "vertical": abs(M4["M_t"] - M4["M_b"])})
    else:
        R("A04", None, status=Status.UNDEFINED, notes=["all objects bleed"])
        R("A05", None, status=Status.UNDEFINED)

    Dc = ctx.union_fraction(ctx.content_boxes)
    Di = ctx.union_fraction(ctx.image_boxes)
    Dt = ctx.union_fraction(ctx.text_boxes)
    R("A06", Dc)
    R("A07", Di)
    R("A08", Dt, details={"block_box_variant": ctx.union_fraction([b.box for b in pm.blocks])})
    R("A09", 1.0 - Dc)

    objs = pm.objects
    N = len(objs)
    boxes = [o.box for o in objs]
    diag = float(np.hypot(W, H))
    if N >= 2:
        d = np.array([[min_distance(boxes[i], boxes[j]) for j in range(N)] for i in range(N)])
        iu = np.triu_indices(N, 1)
        dv = d[iu]
        det = {"normalized_by_diagonal": summary(dv / diag)}
        if N <= 60:
            det["matrix"] = d
            det["ids"] = [o.id for o in objs]
        R("A10", summary(dv), details=det)
        ious = np.array([iou(boxes[i], boxes[j]) for i, j in zip(*iu)])
        ov = ious[ious > 0]
        R("A11", {"overlapping_pairs": int(ov.size), "pairs": int(ious.size),
                  "mean_iou_overlapping": float(ov.mean()) if ov.size else 0.0,
                  "max_iou": float(ious.max())},
          details={"pairs": [[objs[i].id, objs[j].id, float(v)] for (i, j), v in
                             zip(zip(*iu), ious) if v > 0][:200]})
    else:
        R("A10", None, status=Status.UNDEFINED, notes=["N < 2"])
        R("A11", None, status=Status.UNDEFINED, notes=["N < 2"])

    if N >= 1:
        shares = np.array([area(b) / Ap for b in boxes])
        R("A12", float(shares.var()))
        cs = np.array([center(b) for b in boxes]) / np.array([W, H])
        R("A13", {"var_x": float(cs[:, 0].var()), "var_y": float(cs[:, 1].var())})
    else:
        R("A12", None, status=Status.UNDEFINED, notes=["no objects"])
        R("A13", None, status=Status.UNDEFINED, notes=["no objects"])

    tol = float(cfg["layout"]["align_tolerance_fraction"])
    if N >= 2:
        b = np.array(boxes)
        hh, hp = _pairs_sharing([b[:, 1], b[:, 3], 0.5 * (b[:, 1] + b[:, 3])], tol * H)
        vh, vp = _pairs_sharing([b[:, 0], b[:, 2], 0.5 * (b[:, 0] + b[:, 2])], tol * W)
        R("A14", hh / hp, details={"pairs_sharing": hh, "pairs": hp, "tolerance": tol * H})
        R("A15", vh / vp, details={"pairs_sharing": vh, "pairs": vp, "tolerance": tol * W})
        cs = np.array([center(x) for x in boxes]) / np.array([W, H])
        dd = np.linalg.norm(cs[:, None] - cs[None, :], axis=-1)
        np.fill_diagonal(dd, np.inf)
        nn = dd.min(1)
        R("A16", {"mean_nn": float(nn.mean()), "clark_evans_R": float(nn.mean() / (0.5 / np.sqrt(N)))},
          details={"nn_summary": summary(nn)},
          notes=["Clark–Evans uses the unit page as study area without edge correction"])
    else:
        for pid in ("A14", "A15", "A16"):
            R(pid, None, status=Status.UNDEFINED, notes=["N < 2"])

    nx, ny = cfg["layout"]["whitespace_cells"]
    cov = union_area_in_cells(ctx.content_boxes, W, H, int(nx), int(ny))
    R("A17", 1.0 - cov, details={"nx": nx, "ny": ny, "summary": summary((1.0 - cov).ravel())})
    R("A18", N / Ap, details={"N": N, "unit_area": pm.unit + "^2"})

    regions = len(connected_box_groups(boxes, gap=0.0)) if boxes else 0
    R("A19", {"object_count": N, "edge_density": float(ctx.edges.mean()), "region_count": regions},
      details={"edge_density_source": "Canny on page rendering (always raster)",
               "region_rule": "connected groups of touching/overlapping layout-object boxes"})
    return out, grid


def analyze_document(page_grids: list[dict], pages: list) -> list[ParameterResult]:
    vecs, ns = [], []
    for g, pm in zip(page_grids, pages):
        c = g.get("columns")
        if c:
            vecs.append([c["c"] / pm.width, c["g"] / pm.width, c["m_start"] / pm.width, c["m_end"] / pm.width])
            ns.append(c["n"])
    if len(vecs) < 2:
        return [make_result(SPECS["A20"], None, status=Status.UNDEFINED, scope="document",
                            notes=["fewer than 2 pages with an estimated grid"])]
    V = np.array(vecs)
    P = len(V)
    dists = [float(np.linalg.norm(V[i] - V[j])) for i in range(P) for j in range(i + 1, P)]
    modal = max(set(ns), key=ns.count)
    return [make_result(SPECS["A20"], {"mean_pairwise_distance": float(np.mean(dists)),
                                       "modal_column_share": ns.count(modal) / P},
                        source="derived", scope="document",
                        details={"modal_n": modal, "column_counts": ns, "vectors": V,
                                 "distance_to_median": np.linalg.norm(V - np.median(V, 0), axis=1)},
                        measurement_type=MT.ESTIMATED)]
