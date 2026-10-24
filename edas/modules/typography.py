"""MODULE B — TYPOGRAPHY (spec §4).

Geometry of the fonts themselves (B4–B9, B16) is separated from their use
in context (B1–B3, B10–B15, B17–B18).  Glyph geometry comes from PDFium
outlines of the font program embedded in the PDF; for raster pages it is
estimated from segmented glyph components.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np

from ..mathcore.color import contrast_ratio, relative_luminance, rgb_to_lab
from ..mathcore.stats import cosine, js_divergence, shannon_entropy, summary, wasserstein1
from ..schema import ErrorKind, MeasurementType as MT, ParameterResult, Status, make_result
from ..typo.glyphfeat import features_from_mask
from .common import DocContext, PageContext, spec

M = "typography"
SPECS = {s.parameter_id: s for s in [
    spec("B01", "font_sizes", M, unit="pt", formula="s = nominal size x |(c, d)| of the text matrix",
         definition="Effective glyph size of every character (char counts per size, rounded 0.1 pt).",
         domain="(0, inf)", error=ErrorKind.TWO_SIDED),
    spec("B02", "font_size_distribution", M, unit="pt", formula="mean, median, std, quantiles (char weighted)",
         definition="Distribution of B01 weighted by character count.", domain="(0, inf)"),
    spec("B03", "heading_body_ratio", M, unit="ratio", mtype=MT.ESTIMATED, formula="R_s = s_h / s_b",
         definition="s_b = char-count mode of sizes (body); s_h = largest line size among lines with >= 2 "
                    "non-space characters (heading). Role assignment is a rule, hence 'estimated'.",
         domain="[1, inf)", error=ErrorKind.TWO_SIDED),
    spec("B04", "stroke_thickness_ratio", M, unit="ratio", mtype=MT.ESTIMATED,
         formula="R_w = median(local stroke width) / h_glyph",
         definition="Per font: median over sampled glyphs; local stroke width = min run length over 0/45/90/135 "
                    "degrees on the rasterised outline.", domain="(0, 1]", error=ErrorKind.TWO_SIDED),
    spec("B05", "stroke_contrast", M, unit="ratio", mtype=MT.ESTIMATED, formula="C_s = w_max / w_min",
         definition="w_max, w_min = configured upper/lower quantiles of the local stroke width distribution.",
         domain="[1, inf)", error=ErrorKind.TWO_SIDED),
    spec("B06", "glyph_aspect_ratio", M, unit="ratio", formula="R_g = w_g / h_g",
         definition="Ink bounding box width over height per glyph; median per font.", domain="(0, inf)"),
    spec("B07", "glyph_ink_density", M, unit="ratio", mtype=MT.ESTIMATED, formula="D_g = A_ink / A_glyph_box",
         definition="Filled outline area over its bounding box area; median per font.", domain="[0, 1]"),
    spec("B08", "glyph_contour_complexity", M, unit="ratio", formula="L_contour / (2 (w_g + h_g))",
         definition="Exact outline length (flattened Béziers) over bounding-box perimeter; median per font.",
         domain="(0, inf)"),
    spec("B09", "glyph_curvature_distribution", M, unit="1/h_glyph",
         formula="κ(t) = |B'×B''| / |B'|^3 x h_glyph, arc-length weighted; corners counted separately",
         definition="Curvature distribution along outlines (lines contribute κ=0).", domain="[0, inf)"),
    spec("B10", "letter_spacing", M, unit="ratio", formula="(x_left(next) - x_right(prev)) / s",
         definition="Gap between tight boxes of adjacent non-space glyphs inside words, divided by size. "
                    "Advance-box variant (tracking + kerning) in details.", domain="R"),
    spec("B11", "letter_spacing_cv", M, unit="ratio", formula="CV_k = σ_k / (μ_k + ε)",
         definition="Coefficient of variation of B10 gaps.", domain="R",
         notes=["unstable when the mean gap is near 0 (spec formula kept)"]),
    spec("B12", "leading_ratio", M, unit="ratio", formula="R_l = baseline distance / s_b",
         definition="Consecutive baseline distances inside body-text blocks (block size within 5% of s_b), "
                    "divided by the body size.", domain="(0, inf)", error=ErrorKind.TWO_SIDED),
    spec("B13", "line_length", M, unit="chars / pt", formula="characters per line; line width",
         definition="For body lines: non-space character count and physical width (pt and /W).",
         domain="[0, inf)", error=ErrorKind.TWO_SIDED),
    spec("B14", "font_family_count", M, unit="count", formula="|{families}|",
         definition="Distinct families after removing subset prefixes and style suffixes.", domain="N"),
    spec("B15", "font_usage_entropy", M, unit="bits", formula="H_f = -Σ p_j log2 p_j",
         definition="p_j = share of characters set in font face j (family-level entropy in details).",
         domain="[0, log2 n_fonts]"),
    spec("B16", "font_shape_similarity", M, unit="cosine", scope="document",
         formula="cos(f_i, f_j), f = [B04, B05, B06, B07, B08, mean curvature]",
         definition="Cosine similarity of glyph-shape feature vectors between fonts. Standardised with the "
                    "reference profile when available, else with document statistics (>= 3 fonts), else raw.",
         domain="[-1, 1]", missing="undefined with fewer than 2 fonts"),
    spec("B17", "font_style_consistency", M, unit="bits / pt", scope="document",
         formula="mean_{p<q} JSD(face usage_p, face usage_q); mean_{p<q} W1(size_p, size_q)",
         definition="Between-page difference of font-face usage (Jensen–Shannon, bits) and size distribution "
                    "(1-D Wasserstein, pt).", domain="JSD in [0,1]; W1 >= 0",
         missing="undefined with fewer than 2 pages with text"),
    spec("B18", "text_contrast", M, unit="ratio", formula="C = (L_max + 0.05) / (L_min + 0.05)",
         definition="Per text line: luminance of the PDF fill colour vs median luminance of the rendered "
                    "background pixels in the line box (pixels with ΔE*ab > 20 from the text colour).",
         domain="[1, 21]", error=ErrorKind.MIN,
         target="technical: WCAG 2.x 1.4.3 (4.5:1, large text 3:1)"),
    spec("B19", "text_legibility", M, unit="accuracy", mtype=MT.PREDICTED,
         formula="OCR / glyph recognition accuracy against ground truth",
         definition="Requires an OCR engine and ground-truth transcription; not measured otherwise.",
         domain="[0, 1]", missing="null: no OCR engine / no ground truth"),
    spec("B20", "font_style_fit", M, unit="cosine", scope="document",
         formula="S_f = cos(e_f, e_target) in the B16 feature space",
         definition="Similarity of each font's shape vector to the target-style font vector of the reference "
                    "profile. Not a measure of font quality.", domain="[-1, 1]",
         missing="null without a reference profile"),
]}

GLYPH_KEYS = ["T_s", "C_stroke", "aspect", "D_ink", "outline_complexity", "curvature_mean"]


def body_size(sizes: list[float], weights: list[float], step: float) -> Optional[float]:
    if not sizes:
        return None
    c: Counter = Counter()
    for s, w in zip(sizes, weights):
        c[round(s / step) * step] += w
    return float(max(c.items(), key=lambda kv: (kv[1], -kv[0]))[0])


def _ink(chars):
    return [c for c in chars if not c.text.isspace() and not c.generated]


def font_glyph_summary(dctx: DocContext, font_key: str, chars: list[str]) -> Optional[dict]:
    """Median glyph features over the most frequent characters of a font."""
    feats = []
    vals, wts, corners = [], [], 0
    missing = 0
    for ch in chars:
        g = dctx.glyphs.get(font_key, ch)
        if g is None:
            missing += 1
            continue
        feats.append(g)
        vals.append(g["_curv_vals"])
        wts.append(g["_curv_wts"])
        corners += g["corners"]
    if not feats:
        return {"n_glyphs": 0, "missing_glyphs": missing}
    out = {"n_glyphs": len(feats), "missing_glyphs": missing}
    for k in ("T_s", "C_stroke", "aspect", "D_ink", "outline_complexity", "counter_ratio"):
        v = [f[k] for f in feats if f.get(k) is not None]
        out[k] = float(np.median(v)) if v else None
    cv, cw = np.concatenate(vals), np.concatenate(wts)
    if cw.sum() > 0:
        m = float(np.average(cv, weights=cw))
        from ..mathcore.stats import weighted_quantile
        q = weighted_quantile(cv, cw, (0.05, 0.25, 0.5, 0.75, 0.95))
        out["curvature"] = {"mean": m, "var": float(np.average((cv - m) ** 2, weights=cw)),
                            "quantiles": dict(zip(("q05", "q25", "q50", "q75", "q95"), map(float, q))),
                            "corners_per_glyph": corners / len(feats)}
        out["curvature_mean"] = m
    return out


def _font_chars(chars, font_key, k):
    c = Counter(ch.text for ch in chars if ch.font_key == font_key)
    return [ch for ch, _ in c.most_common(k)]


def raster_glyph_summary(pm, cfg) -> Optional[dict]:
    r = pm.raster
    if not r or not r["glyph_boxes"]:
        return None
    fg = r["fg_mask"]
    feats = []
    for (x0, y0, x1, y1) in r["glyph_boxes"][:400]:
        m = fg[y0:y1, x0:x1]
        if m.sum() < 6 or (y1 - y0) < 6:
            continue
        f = features_from_mask(np.pad(m, 2), 2.0, 2.0 + (y1 - y0), float(y1 - y0),
                               tuple(cfg["typography"]["stroke_quantiles"]))
        if f:
            feats.append(f)
    if not feats:
        return None
    out = {"n_components": len(feats)}
    for k in ("T_s", "C_stroke", "aspect", "D_ink", "complexity"):
        v = [f[k] for f in feats if f.get(k) is not None]
        out[k] = float(np.median(v)) if v else None
    out["note"] = ("connected components, not characters: Hangul syllables and i/j split into several "
                   "components; resolution-limited")
    return out


def _line_contrast(pm, line, text_rgb, cfg) -> Optional[float]:
    pad = 1.0
    b = (line.box[0] - pad, line.box[1] - pad, line.box[2] + pad, line.box[3] + pad)
    crop = pm.crop(b)
    if crop is None or crop.size == 0:
        return None
    px = crop.reshape(-1, 3)
    lab = rgb_to_lab(px)
    if text_rgb is None:   # raster: background = modal colour, text = far pixels
        q = np.clip((px * 15).round().astype(int), 0, 15)
        idx = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
        bgc = px[idx == np.bincount(idx).argmax()].mean(0)
        d = np.linalg.norm(lab - rgb_to_lab(bgc[None])[0], axis=1)
        if (d > 20).sum() < 3:
            return None
        text_rgb = np.median(px[d > 20], axis=0)
        bg = bgc
    else:
        d = np.linalg.norm(lab - rgb_to_lab(np.asarray(text_rgb)[None])[0], axis=1)
        far = d > 20
        if far.sum() < 5:
            return None
        bg = np.median(px[far], axis=0)
    return contrast_ratio(float(relative_luminance(np.asarray(text_rgb))), float(relative_luminance(bg)))


def analyze_page(ctx: PageContext, dctx: DocContext) -> list[ParameterResult]:
    pm, cfg = ctx.pm, ctx.cfg
    src, pi = ctx.source, pm.index
    out: list[ParameterResult] = []

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, source=kw.pop("source", src), page_index=pi, **kw))

    ink = _ink(pm.chars)
    raster = pm.extraction_mode == "raster"
    step = float(cfg["typography"]["body_size_round"])
    if raster:
        lines = pm.lines
        if lines:
            hs = [l.size for l in lines]
            note = ["raster: size = median glyph-component height (not the em size)"]
            R("B01", {"line_glyph_heights": hs}, notes=note)
            R("B02", summary(hs), notes=note)
            sb = float(np.median(hs))
            R("B03", max(hs) / sb if sb > 0 else None, details={"s_h": max(hs), "s_b": sb}, notes=note)
        else:
            for pid in ("B01", "B02", "B03"):
                R(pid, None, notes=["no text lines detected"])
        rg = raster_glyph_summary(pm, cfg)
        if rg:
            R("B04", {"raster": rg["T_s"]}, details=rg)
            R("B05", {"raster": rg["C_stroke"]})
            R("B06", {"raster": rg["aspect"]})
            R("B07", {"raster": rg["D_ink"]})
            R("B08", {"raster": rg["complexity"]}, notes=["Crofton perimeter of raster components"])
        else:
            for pid in ("B04", "B05", "B06", "B07", "B08"):
                R(pid, None, notes=["no glyph components"])
        R("B09", None, status=Status.NOT_MEASURED, notes=["curvature requires vector outlines"])
        gaps = [g / l["glyph_height_px"] for l in (pm.raster or {}).get("lines", []) for g in l["gaps_px"]
                if l["glyph_height_px"] > 0]
        if gaps:
            R("B10", summary(gaps), notes=["component gaps / glyph height (raster estimate)"])
            m, s = float(np.mean(gaps)), float(np.std(gaps))
            R("B11", s / (m + 1e-9))
        else:
            R("B10", None)
            R("B11", None)
        rl = []
        for b in pm.blocks:
            bl = sorted(b.lines, key=lambda l: l.baseline)
            rl += [(b2.baseline - b1.baseline) / b.size for b1, b2 in zip(bl[:-1], bl[1:]) if b.size > 0]
        R("B12", summary(rl), notes=["raster: baseline distance / glyph height, not / em size"])
        R("B13", summary([(l.box[2] - l.box[0]) / pm.width for l in pm.lines]),
          notes=["raster: line width / W only; character counts need OCR"])
        R("B14", None, status=Status.NOT_MEASURED, notes=["font identity unavailable from raster"])
        R("B15", None, status=Status.NOT_MEASURED, notes=["font identity unavailable from raster"])
    else:
        sizes = [c.size for c in ink]
        if not sizes:
            for pid in ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12",
                        "B13", "B14", "B15"):
                R(pid, None, notes=["no text on page"])
        else:
            hist = Counter(round(s / 0.1) * 0.1 for s in sizes)
            R("B01", {f"{k:.1f}": v for k, v in sorted(hist.items())})
            R("B02", summary(sizes))
            sb = body_size(sizes, [1.0] * len(sizes), step)
            cand = [l.size for l in pm.lines if len([c for c in l.chars if not c.text.isspace()]) >= 2]
            sh = max(cand) if cand else None
            R("B03", sh / sb if (sh and sb) else None, details={"s_h": sh, "s_b": sb})
            fonts = Counter(c.font_key for c in ink)
            k = int(cfg["typography"]["max_glyphs_per_font"])
            per_font = {fk: font_glyph_summary(dctx, fk, _font_chars(ink, fk, k)) for fk in fonts if fk}
            for pid, key in (("B04", "T_s"), ("B05", "C_stroke"), ("B06", "aspect"), ("B07", "D_ink"),
                             ("B08", "outline_complexity")):
                R(pid, {fk: v.get(key) for fk, v in per_font.items()},
                  details={"glyphs": {fk: v.get("n_glyphs") for fk, v in per_font.items()},
                           "missing_glyphs": {fk: v.get("missing_glyphs") for fk, v in per_font.items()}},
                  source="pdf_objects")
            R("B09", {fk: v.get("curvature") for fk, v in per_font.items()}, source="pdf_objects")
            # letter spacing within words
            gaps, loose = [], []
            for l in pm.lines:
                cs = l.chars
                for a, b in zip(cs[:-1], cs[1:]):
                    if a.text.isspace() or b.text.isspace() or b.generated or a.generated:
                        continue
                    s = max(a.size, 1e-6)
                    gaps.append((b.box[0] - a.box[2]) / s)
                    loose.append((b.loose_box[0] - a.loose_box[2]) / s)
            if gaps:
                R("B10", summary(gaps), details={"advance_box_variant": summary(loose)})
                m, sd = float(np.mean(gaps)), float(np.std(gaps))
                R("B11", sd / (m + 1e-9), details={"mean": m, "std": sd})
            else:
                R("B10", None, status=Status.UNDEFINED, notes=["no adjacent glyph pairs"])
                R("B11", None, status=Status.UNDEFINED)
            rl, body_lines = [], []
            for b in pm.blocks:
                if sb and abs(b.size - sb) <= 0.05 * sb:
                    bl = sorted(b.lines, key=lambda l: l.baseline)
                    body_lines += bl
                    rl += [(b2.baseline - b1.baseline) / sb for b1, b2 in zip(bl[:-1], bl[1:])]
            R("B12", summary(rl), details={"s_b": sb},
              status=None if rl else Status.UNDEFINED)
            R("B13", {"chars": summary([len([c for c in l.chars if not c.text.isspace()]) for l in body_lines]),
                      "width_pt": summary([l.box[2] - l.box[0] for l in body_lines]),
                      "width_ratio": summary([(l.box[2] - l.box[0]) / pm.width for l in body_lines])}
              if body_lines else None)
            fams = Counter(dctx.doc.fonts[fk].family for fk in fonts if fk in dctx.doc.fonts)
            R("B14", len(fams), details={"families": dict(fams)})
            R("B15", shannon_entropy(list(fonts.values())),
              details={"faces": dict(fonts), "family_entropy": shannon_entropy(list(fams.values()))})

    # B18 contrast
    thr = cfg["technical_targets"]["text_contrast_min"]
    crs, fails = [], 0
    for l in pm.lines:
        ink_l = _ink(l.chars)
        rgb = None
        bold = False
        if ink_l:
            cols = [c.fill_rgb for c in ink_l if c.fill_rgb is not None]
            rgb = tuple(np.median(np.array(cols), axis=0)) if cols else None
            f = dctx.doc.fonts.get(l.font_key) if l.font_key else None
            bold = bool(f and ((f.weight or 0) >= 700 or "bold" in f.style.lower()))
        elif not raster:
            continue
        cr = _line_contrast(pm, l, rgb, cfg)
        if cr is None:
            continue
        large = (not raster) and (l.size >= thr["large_text_pt"] or (bold and l.size >= 14.0))
        crs.append(cr)
        if cr < (thr["large_text_value"] if large else thr["value"]):
            fails += 1
    if crs:
        R("B18", {"min": float(min(crs)), "median": float(np.median(crs)),
                  "share_below_wcag": fails / len(crs)},
          details={"lines": len(crs), "threshold": thr["value"], "large_threshold": thr["large_text_value"],
                   "source_of_threshold": thr["source"]})
    else:
        R("B18", None, notes=["no measurable text line"])
    valid = [c for c in ink if c.text != "�" and not (0xE000 <= ord(c.text) <= 0xF8FF)]
    R("B19", None, status=Status.NOT_MEASURED,
      notes=["no OCR engine and no ground truth: recognition accuracy not reported"],
      details={"unicode_mapping_valid_share": (len(valid) / len(ink)) if ink else None,
               "note": "share of characters with a valid Unicode mapping; NOT a legibility accuracy"})
    return out


def font_vectors(dctx: DocContext) -> dict:
    """Document-level glyph-shape vectors per font (most frequent glyphs)."""
    chars = [c for p in dctx.doc.pages for c in _ink(p.chars)]
    fonts = Counter(c.font_key for c in chars if c.font_key)
    k = int(dctx.cfg["typography"]["max_glyphs_per_font"])
    out = {}
    for fk in fonts:
        s = font_glyph_summary(dctx, fk, _font_chars(chars, fk, k))
        if s and s.get("n_glyphs"):
            v = [s.get(x) for x in GLYPH_KEYS]
            out[fk] = {"vector": v, "summary": s, "chars": fonts[fk]}
    return out


def analyze_document(dctx: DocContext, reference: Optional[dict] = None) -> list[ParameterResult]:
    doc = dctx.doc
    out: list[ParameterResult] = []

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, scope="document", source=kw.pop("source", "pdf_objects"), **kw))

    chars = [c for p in doc.pages if p.extraction_mode != "raster" for c in _ink(p.chars)]
    if chars:
        sizes = [c.size for c in chars]
        R("B02", summary(sizes))
        sb = body_size(sizes, [1.0] * len(sizes), float(dctx.cfg["typography"]["body_size_round"]))
        cand = [l.size for p in doc.pages for l in p.lines
                if len([c for c in l.chars if not c.text.isspace()]) >= 2]
        sh = max(cand) if cand else None
        R("B03", sh / sb if sh and sb else None, details={"s_h": sh, "s_b": sb})
        fonts = Counter(c.font_key for c in chars)
        fams = Counter(doc.fonts[f].family for f in fonts if f in doc.fonts)
        R("B14", len(fams), details={"families": dict(fams)})
        R("B15", shannon_entropy(list(fonts.values())), details={"faces": dict(fonts)})
    fv = font_vectors(dctx)
    keys = [k for k in fv if all(v is not None for v in fv[k]["vector"])]
    if len(keys) >= 2:
        X = np.array([fv[k]["vector"] for k in keys], float)
        mode = "raw"
        ref = (reference or {}).get("font_feature_stats")
        if ref:
            X = (X - np.array(ref["mean"])) / (np.array(ref["std"]) + 1e-9)
            mode = "reference"
        elif len(keys) >= 3:
            X = (X - X.mean(0)) / (X.std(0) + 1e-9)
            mode = "document"
        S = [[cosine(X[i], X[j]) for j in range(len(keys))] for i in range(len(keys))]
        R("B16", {"fonts": keys, "matrix": S}, details={"standardisation": mode, "features": GLYPH_KEYS,
                                                        "vectors": {k: fv[k]["vector"] for k in keys}},
          notes=(["raw positive features: cosine compressed toward 1"] if mode == "raw" else []))
    else:
        R("B16", None, status=Status.UNDEFINED, notes=["fewer than 2 fonts with glyph geometry"])
    # B17
    pages = [p for p in doc.pages if p.extraction_mode != "raster" and _ink(p.chars)]
    if len(pages) >= 2:
        faces = sorted({c.font_key or "?" for p in pages for c in _ink(p.chars)})
        U = []
        S = []
        for p in pages:
            cnt = Counter(c.font_key or "?" for c in _ink(p.chars))
            U.append([cnt.get(f, 0) for f in faces])
            S.append([c.size for c in _ink(p.chars)])
        P = len(pages)
        jsd = [js_divergence(U[i], U[j]) for i in range(P) for j in range(i + 1, P)]
        w1 = [wasserstein1(S[i], S[j]) for i in range(P) for j in range(i + 1, P)]
        R("B17", {"mean_jsd_face_usage": float(np.mean(jsd)), "mean_w1_size_pt": float(np.mean(w1))},
          details={"pages": [p.index for p in pages]})
    else:
        R("B17", None, status=Status.UNDEFINED, notes=["fewer than 2 pages with text"])
    tgt = (reference or {}).get("font_target_vector")
    if tgt and fv:
        R("B20", {k: cosine(fv[k]["vector"], tgt) for k in keys}, details={"features": GLYPH_KEYS},
          notes=["similarity to target-style fonts; not font quality"])
    else:
        R("B20", None, status=Status.NO_REFERENCE, notes=["requires a reference profile with font vectors"])
    return out
