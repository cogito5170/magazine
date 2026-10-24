"""MODULE C — PHOTOGRAPHY (spec §5).  Features of each placed raster image,
computed on its *visible* rendered region (what the reader sees)."""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..mathcore.color import ciede2000, hsv_saturation, relative_luminance, rgb_histogram, rgb_to_lab, gray
from ..mathcore.imaging import canny, hough_dominant_line, laplacian, resize_max
from ..mathcore.saliency import spectral_residual
from ..mathcore.stats import shannon_entropy, summary
from ..schema import ErrorKind, MeasurementType as MT, ParameterResult, Status, make_result
from .common import PageContext, spec

M = "photography"
SPECS = {s.parameter_id: s for s in [
    spec("C01", "image_aspect_ratio", M, unit="ratio", formula="R_i = W_i / H_i (visible box)", domain="(0, inf)"),
    spec("C02", "image_area_share", M, unit="ratio", formula="D_i = A_i / A_p (visible box)", domain="[0, 1]",
         error=ErrorKind.TWO_SIDED),
    spec("C03", "mean_luminance", M, unit="linear luminance", formula="mean Y(x,y), Y = 0.2126R+0.7152G+0.0722B (linear)",
         domain="[0, 1]", error=ErrorKind.TWO_SIDED),
    spec("C04", "luminance_variance", M, unit="luminance^2", formula="V_Y = Var(Y)", domain="[0, 0.25]"),
    spec("C05", "luminance_contrast", M, unit="linear luminance", formula="Q95(Y) - Q05(Y)", domain="[0, 1]"),
    spec("C06", "mean_saturation", M, unit="HSV saturation", formula="mean S", domain="[0, 1]"),
    spec("C07", "saturation_variance", M, unit="saturation^2", formula="V_S = Var(S)", domain="[0, 0.25]"),
    spec("C08", "color_entropy", M, unit="bits", formula="H_c = -Σ p_k log2 p_k, joint RGB histogram bins^3",
         domain="[0, 3 log2 bins]"),
    spec("C09", "sharpness_laplacian_variance", M, unit="gray^2/px^4", formula="Var(∇²I), I = luma at analysis size",
         domain="[0, inf)", notes=["resolution and noise dependent: not an absolute quality score"]),
    spec("C10", "edge_density", M, unit="ratio", formula="N_edge / N_px (Canny)", domain="[0, 1]"),
    spec("C11", "information_entropy", M, unit="bits", formula="Shannon entropy of the 256-bin luma histogram",
         domain="[0, 8]"),
    spec("C12", "subject_center", M, unit="normalized", mtype=MT.ESTIMATED,
         formula="(x_s, y_s) = centroid of {saliency > k·mean} in image coordinates",
         definition="Subject = spectral-residual saliency above k times its mean (Hou & Zhang threshold).",
         domain="[0, 1]^2"),
    spec("C13", "subject_area_share", M, unit="ratio", mtype=MT.ESTIMATED, formula="D_s = A_s / A_i", domain="[0, 1]",
         notes=["depends on the subject definition (saliency threshold)"]),
    spec("C14", "negative_space", M, unit="ratio", mtype=MT.ESTIMATED, formula="D_n = 1 - D_s", domain="[0, 1]",
         notes=["depends on the subject definition (saliency threshold)"]),
    spec("C15", "horizon_tilt", M, unit="deg", mtype=MT.ESTIMATED,
         formula="tilt of the strongest Hough line within ±max_tilt of horizontal", domain="[-max, max]",
         missing="null when no line has support >= horizon_min_support"),
    spec("C16", "image_symmetry", M, unit="ratio",
         formula="S = 1 - mean|I - flip(I)| (I = luma in [0,1]); left-right and top-bottom", domain="[0, 1]",
         notes=["spec defines 'normalised difference'; reported as symmetry S = 1 - d with d in details"]),
    spec("C17", "crop_retention", M, unit="ratio", formula="R_c = A_visible / A_placed (embedded source)",
         domain="(0, 1]", missing="not computable without the source image (raster pages)",
         notes=["the embedded XObject is treated as the source; crops made before embedding are invisible"]),
    spec("C18", "inter_image_color_difference", M, unit="ΔE00", formula="CIEDE2000(mean Lab_i, mean Lab_j)",
         domain="[0, ~100]", missing="undefined with fewer than 2 images"),
    spec("C19", "image_semantic_similarity", M, unit="cosine", mtype=MT.PREDICTED,
         formula="cos(e_i, e_j), e = image embedding of a pretrained model", domain="[-1, 1]",
         missing="null: no semantic embedding model configured"),
    spec("C20", "image_style_consistency", M, unit="standardised distance", scope="document",
         formula="mean pairwise ||v_i - v_j||, v = z-scored [C03, C05, C06, C08, C10, log C09, a*, b*]",
         definition="Colour/texture/composition style dispersion across the document's photographs. "
                    "Not semantic similarity.", domain="[0, inf)"),
]}

STYLE_KEYS = ["C03", "C05", "C06", "C08", "C10", "logC09", "a", "b"]


def image_features(rgb: np.ndarray, cfg: dict) -> dict:
    pc = cfg["photography"]
    rgb, _ = resize_max(rgb, int(pc["max_side_px"]))
    Y = relative_luminance(rgb)
    S = hsv_saturation(rgb)
    g = gray(rgb)
    edges = canny(g, pc["canny"]["sigma"], pc["canny"]["low"], pc["canny"]["high"])
    hist = np.histogram(np.clip((g * 255).astype(int), 0, 255), bins=256, range=(0, 256))[0]
    sal = spectral_residual(g)
    thr = float(pc["subject_threshold_k"]) * sal.mean()
    subj = sal > thr
    H, W = g.shape
    ys, xs = np.nonzero(subj)
    hl = hough_dominant_line(edges, float(pc["horizon_max_tilt_deg"]))
    lab = rgb_to_lab(rgb).reshape(-1, 3).mean(0)
    return {
        "C03": float(Y.mean()), "C04": float(Y.var()),
        "C05": float(np.quantile(Y, 0.95) - np.quantile(Y, 0.05)),
        "C06": float(S.mean()), "C07": float(S.var()),
        "C08": shannon_entropy(rgb_histogram(rgb, int(pc["color_bins"]))),
        "C09": float(laplacian(g).var()), "C10": float(edges.mean()),
        "C11": shannon_entropy(hist),
        "C12": [float((xs.mean() + 0.5) / W), float((ys.mean() + 0.5) / H)] if xs.size else None,
        "C13": float(subj.mean()),
        "C15": hl["tilt_deg"] if hl and hl["support"] >= float(pc["horizon_min_support"]) else None,
        "C15_detail": hl,
        "C16": {"left_right": float(1 - np.abs(g - g[:, ::-1]).mean()),
                "top_bottom": float(1 - np.abs(g - g[::-1, :]).mean())},
        "lab_mean": [float(v) for v in lab],
        "analysis_px": [W, H],
    }


def photos(ctx: PageContext):
    pm = ctx.pm
    minf = float(ctx.cfg["photography"]["min_area_fraction"])
    out = []
    for o in [o for o in pm.objects if o.kind == "image"]:
        im = pm.images[o.meta["image_index"]]
        A = (o.box[2] - o.box[0]) * (o.box[3] - o.box[1])
        if A < minf * pm.area:
            continue
        crop = pm.crop(o.box)
        if crop is None or min(crop.shape[:2]) < 8:
            continue
        out.append((o, im, crop))
    return out


def analyze_page(ctx: PageContext) -> tuple[list[ParameterResult], list[dict]]:
    pm, cfg = ctx.pm, ctx.cfg
    out: list[ParameterResult] = []
    src, pi = ctx.source, pm.index

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, source=kw.pop("source", src), page_index=pi, **kw))

    items = photos(ctx)
    feats = []
    for o, im, crop in items:
        f = image_features(crop, cfg)
        f["id"] = o.id
        f["C01"] = (o.box[2] - o.box[0]) / (o.box[3] - o.box[1])
        f["C02"] = (o.box[2] - o.box[0]) * (o.box[3] - o.box[1]) / pm.area
        f["C17"] = im.crop_retention if pm.extraction_mode != "raster" else None
        f["ppi"] = im.effective_ppi
        feats.append(f)
    if not feats:
        for pid in SPECS:
            if SPECS[pid].scope != "document":
                R(pid, None, status=Status.UNDEFINED if pid != "C19" else Status.NOT_MEASURED,
                  notes=["no photograph above the minimum area share on this page"])
        return out, feats
    w = np.array([f["C02"] for f in feats])

    def per(key, agg=True):
        vals = {f["id"]: f[key] for f in feats}
        res = {"images": vals}
        nums = [(f[key], wi) for f, wi in zip(feats, w) if isinstance(f[key], (int, float))]
        if agg and nums:
            res["area_weighted_mean"] = float(sum(v * x for v, x in nums) / sum(x for _, x in nums))
        return res

    for pid in ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11"):
        R(pid, per(pid), details={"analysis_px": {f["id"]: f["analysis_px"] for f in feats}})
    R("C12", per("C12", agg=False))
    R("C13", per("C13"))
    R("C14", {"images": {f["id"]: 1 - f["C13"] for f in feats},
              "area_weighted_mean": float(np.average([1 - f["C13"] for f in feats], weights=w))})
    R("C15", per("C15", agg=False), details={f["id"]: f["C15_detail"] for f in feats})
    R("C16", {"images": {f["id"]: f["C16"] for f in feats},
              "area_weighted_mean": {k: float(np.average([f["C16"][k] for f in feats], weights=w))
                                     for k in ("left_right", "top_bottom")}})
    if pm.extraction_mode == "raster":
        R("C17", None, status=Status.NOT_COMPUTABLE, notes=["source image unavailable (raster page)"])
    else:
        R("C17", per("C17"), source="pdf_objects")
    if len(feats) >= 2:
        labs = np.array([f["lab_mean"] for f in feats])
        n = len(feats)
        de = [[float(ciede2000(labs[i], labs[j])) for j in range(n)] for i in range(n)]
        R("C18", summary([de[i][j] for i in range(n) for j in range(i + 1, n)]),
          details={"ids": [f["id"] for f in feats], "matrix": de})
    else:
        R("C18", None, status=Status.UNDEFINED, notes=["fewer than 2 photographs"])
    R("C19", None, status=Status.NOT_MEASURED, notes=["no semantic image embedding model configured"])
    return out, feats


def style_vector(f: dict) -> list[float]:
    return [f["C03"], f["C05"], f["C06"], f["C08"] or 0.0, f["C10"], float(np.log1p(f["C09"])),
            f["lab_mean"][1], f["lab_mean"][2]]


def analyze_document(all_feats: list[dict], embedder=None) -> list[ParameterResult]:
    out = []
    if len(all_feats) >= 2:
        V = np.array([style_vector(f) for f in all_feats])
        Z = (V - V.mean(0)) / (V.std(0) + 1e-9)
        n = len(Z)
        d = [float(np.linalg.norm(Z[i] - Z[j])) for i in range(n) for j in range(i + 1, n)]
        labs = np.array([f["lab_mean"] for f in all_feats])
        de = [float(ciede2000(labs[i], labs[j])) for i in range(n) for j in range(i + 1, n)]
        out.append(make_result(SPECS["C20"], {"mean_pairwise_distance": float(np.mean(d))}, scope="document",
                               source="derived", details={"features": STYLE_KEYS, "standardisation": "document",
                                                          "ids": [f["id"] for f in all_feats],
                                                          "ciede2000_all_pairs": summary(de)}))
    else:
        out.append(make_result(SPECS["C20"], None, scope="document", status=Status.UNDEFINED,
                               notes=["fewer than 2 photographs in the document"]))
    return out
