"""MODULE B-K — Korean–Latin (bilingual) typography extension.

Extends Module B without changing B01–B20.  Five evaluation dimensions:
  1 Glyph Geometry Quality ...... BK03, BK04, BK10   (measured / estimated)
  2 Korean–Latin Visual Harmony . BK05, BK06, BK07, BK08 (measured description, not a verdict)
  3 Typographic Composition ..... BK08, BK09         (measured / estimated)
  4 Contextual Compatibility .... BK11              (predicted; requires a trained model)
  5 Human Aesthetic Preference .. BK12              (predicted; requires pairwise labels)
plus identification (BK01, BK02) and alternatives (BK13).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Optional

import numpy as np

from ..mathcore.geometry import min_distance
from ..mathcore.stats import summary
from ..schema import MeasurementType as MT, ParameterResult, Status, make_result
from ..typo.harmony import harmony_vector, hangul_profile, ink_complexity_relation, latin_profile
from ..typo.scripts import char_class, script_group
from .common import DocContext, PageContext, spec

M = "typography_bilingual"
CRITERIA = ("visual_harmony", "sophistication", "professionalism", "readability", "target_style_fit")
ROLES = ("title", "subhead", "body", "caption", "label")

SPECS = {s.parameter_id: s for s in [
    spec("BK01", "script_composition", M, unit="count / ratio",
         formula="n_class, n_class / Σ n  for hangul, hangul_jamo, latin_upper, latin_lower, digit, punct, other",
         definition="Unicode classification of non-space characters; K/E mixing ratio n_K/(n_K+n_E).",
         domain="[0, 1]"),
    spec("BK02", "font_identification", M, unit="categorical", mtype=MT.ESTIMATED,
         formula="per script: font share, embedded flag, outline coverage -> status",
         definition="status: verified (embedded program provides every sampled glyph), partial (some glyphs "
                    "missing -> renderer fallback), named_only (font not embedded: renderer substitutes), "
                    "unidentified (raster / outlined text). Outlined-text suspicion from vector paths.",
         domain="categorical", confidence="categorical identification status, no numeric score"),
    spec("BK03", "hangul_glyph_geometry", M, unit="em / ratio", mtype=MT.ESTIMATED,
         formula="T_s = median(stroke)/H_g; D_ink = A_ink/A_glyph; c_g = Σ I(x,y)(x,y)/Σ I; ... per shape type 1-6",
         definition="Per Hangul font: features of the most frequent syllables of each of the 6 shape types "
                    "(vowel position x final consonant); aggregate = usage-weighted mean of stratum medians.",
         domain="see feature list", scope="document"),
    spec("BK04", "latin_glyph_geometry", M, unit="em / ratio", mtype=MT.ESTIMATED,
         formula="same features per class: uppercase, lowercase, digits, punctuation; cap/x-height, baseline",
         definition="Per Latin font: per-class medians, cap height, x-height (acemnorsuvwxz), baseline "
                    "(flat-bottom capitals).", domain="see feature list", scope="document"),
    spec("BK05", "bilingual_visual_size", M, unit="ratio",
         formula="H_hangul / H_cap at equal nominal size (outline: em; page: tight boxes / size)",
         definition="Visual size of Hangul relative to Latin capitals (and x-height) for co-occurring fonts; "
                    "verifies that equal point size does not imply equal visual size.", domain="(0, inf)"),
    spec("BK06", "bilingual_baseline_center_offset", M, unit="em",
         formula="bottom_K − bottom_E ; center_K − center_E (ink, em, baseline = 0)",
         definition="Vertical offset of Hangul ink relative to Latin baseline and visual centre.", domain="R"),
    spec("BK07", "korean_latin_harmony_vector", M, unit="standardised", mtype=MT.ESTIMATED,
         formula="h = [ΔT_s, ΔD_ink, ΔH_visual, ΔB_baseline, ΔC_stroke, ΔR_spacing]",
         definition="Normalised Hangul−Latin differences per co-occurring font pair (Cohen's d for glyph/gap "
                    "distributions, relative to cap height for vertical metrics). Descriptive only.",
         domain="R^6", notes=["smaller differences are NOT assumed to be better"]),
    spec("BK08", "spacing_by_script", M, unit="ratio",
         formula="gap/size for KK, EE, K|E boundary pairs; word-space width/size by script",
         definition="Inter-glyph gaps (tight boxes) and word spaces split by script context.", domain="R"),
    spec("BK09", "typographic_hierarchy", M, unit="pt / ratio", mtype=MT.ESTIMATED,
         formula="roles by size relative to s_b and proximity to images; size levels; ratios between levels",
         definition="Role assignment rule: body |s-s_b|<=5%; title s>=title_ratio*s_b; subhead in between; "
                    "caption: smaller than body and within caption_distance*s of an image; label: other small text.",
         domain="categorical / ratios"),
    spec("BK10", "hangul_complexity_ink_relation", M, unit="ratio / component", mtype=MT.ESTIMATED,
         formula="OLS: D_ink = a + b * components(syllable)", scope="document",
         definition="Change of ink density with syllable complexity (jamo component count).", domain="R"),
    spec("BK11", "contextual_appropriateness", M, unit="probability", mtype=MT.PREDICTED,
         formula="P(appropriate | f_K, f_E, c) = σ(g_θ(h, e_K, e_E, c))",
         definition="Conditional appropriateness from a trained model; context vector c is reported.",
         domain="[0, 1]", missing="null without a trained model (no score is produced)"),
    spec("BK12", "bilingual_preference", M, unit="logit", mtype=MT.PREDICTED,
         formula="P(A ≻ B | c) = σ(q_θ(A,c) − q_θ(B,c)), one model per criterion",
         definition="Per-criterion Bradley–Terry scores (visual_harmony, sophistication, professionalism, "
                    "readability, target_style_fit); criteria never mixed.", domain="R",
         missing="null without pairwise data for that criterion"),
    spec("BK13", "alternative_font_candidates", M, unit="list", mtype=MT.DIRECT, scope="document",
         formula="installed faces with full coverage of the used characters; h for each candidate pair",
         definition="Availability (installed path, cmap coverage) and licence fields read from the font "
                    "'name'/'OS/2' tables. Ordered by geometric distance for browsing only (similar and "
                    "contrasting lists), not by quality.", domain="list"),
]}


def _ink(chars):
    return [c for c in chars if not c.text.isspace() and not c.generated]


def _group_counts(chars) -> dict:
    cls = Counter(char_class(c.text) for c in chars)
    return dict(cls)


def _font_status(dctx: DocContext, fk: str, chars: list[str]) -> dict:
    f = dctx.doc.fonts.get(fk)
    sample = chars[:60]
    have = sum(1 for ch in sample if dctx.glyphs.get(fk, ch) is not None)
    cov = have / len(sample) if sample else None
    if f is None:
        status = "unidentified"
    elif f.embedded is False:
        status = "named_only"
    elif cov is not None and cov < 1.0:
        status = "partial"
    else:
        status = "verified"
    return {"font": fk, "family": f.family if f else None, "style": f.style if f else None,
            "weight": f.weight if f else None, "embedded": f.embedded if f else None,
            "subset": bool(f and f.key != f.base_name), "glyph_outline_coverage": cov,
            "status": status}


def _outlined_text_suspicion(pm) -> dict:
    W, H = pm.width, pm.height
    small = [v for v in pm.vectors if not v.is_background and v.filled and
             (v.box[3] - v.box[1]) <= 0.03 * H and (v.box[2] - v.box[0]) <= 0.05 * W]
    rows = Counter(round(((v.box[1] + v.box[3]) / 2) / (0.01 * H)) for v in small)
    dense_rows = sum(1 for n in rows.values() if n >= 8)
    return {"small_filled_paths": len(small), "rows_with_8plus": dense_rows,
            "suspected": len(small) >= 30 and dense_rows >= 2,
            "rule": "≥30 small filled paths (h≤3%H, w≤5%W) forming ≥2 rows of ≥8 -> outlined text suspected"}


class BilingualDoc:
    """Document-level geometry profiles shared by page analyses."""

    def __init__(self, dctx: DocContext):
        self.dctx = dctx
        cfg = dctx.cfg["typography"]["bilingual"]
        chars = [c for p in dctx.doc.pages for c in _ink(p.chars)]
        self.freq: dict[str, Counter] = defaultdict(Counter)
        for c in chars:
            if c.font_key:
                self.freq[c.font_key][c.text] += 1
        self.K, self.E = {}, {}
        for fk, fr in self.freq.items():
            get = (lambda ch, fk=fk: dctx.glyphs.get(fk, ch))
            kp = hangul_profile(fr, get, int(cfg["hangul_per_stratum"]))
            if kp:
                self.K[fk] = kp
            ep = latin_profile(fr, get, int(cfg["latin_per_class"]))
            if ep and ep["n_letters"] >= 2:
                self.E[fk] = ep
        self.gaps = self._gaps(chars_by_page=[p for p in dctx.doc.pages])

    def _gaps(self, chars_by_page):
        g: dict = defaultdict(list)
        for p in chars_by_page:
            for l in p.lines:
                cs = l.chars
                for a, b in zip(cs[:-1], cs[1:]):
                    if a.text.isspace() or b.text.isspace() or a.generated or b.generated:
                        continue
                    ga, gb = script_group(char_class(a.text)), script_group(char_class(b.text))
                    if ga == gb and ga in "KE" and a.font_key == b.font_key:
                        g[(ga, a.font_key)].append((b.box[0] - a.box[2]) / max(a.size, 1e-6))
        return g

    def pair(self, kf: str, ef: str) -> Optional[dict]:
        if kf not in self.K or ef not in self.E:
            return None
        return harmony_vector(self.K[kf], self.E[ef], self.gaps.get(("K", kf)), self.gaps.get(("E", ef)))


def _roles(pm, sb: Optional[float], cfg) -> list[dict]:
    rc = cfg["typography"]["bilingual"]["roles"]
    imgs = [o.box for o in pm.objects if o.kind == "image"]
    out = []
    for b in pm.blocks:
        s = b.size
        n = sum(len([c for c in l.chars if not c.text.isspace()]) for l in b.lines)
        if not sb or s <= 0:
            role = "unknown"
        elif abs(s - sb) <= 0.05 * sb:
            role = "body"
        elif s >= float(rc["title_ratio"]) * sb:
            role = "title"
        elif s > sb:
            role = "subhead"
        elif imgs and min(min_distance(b.box, ib) for ib in imgs) <= float(rc["caption_distance"]) * s:
            role = "caption"
        else:
            role = "label"
        fonts = Counter(c.font_key for l in b.lines for c in l.chars if not c.text.isspace())
        out.append({"role": role, "size": s, "chars": n, "box": b.box,
                    "fonts": dict(fonts), "lines": len(b.lines)})
    return out


def _levels(sizes: list[float], rel: float = 0.05) -> list[float]:
    lv: list[float] = []
    for s in sorted(set(round(x, 2) for x in sizes), reverse=True):
        if not lv or abs(s - lv[-1]) > rel * lv[-1]:
            lv.append(s)
    return lv


def context_vector(pm, roles, comp: dict, page_params: dict, target_style: Optional[str]) -> dict:
    """Inputs c of the contextual model (all measured or rule-estimated, documented)."""
    nK = comp.get("hangul", 0) + comp.get("hangul_jamo", 0)
    nE = comp.get("latin_upper", 0) + comp.get("latin_lower", 0)
    rc = Counter(r["role"] for r in roles)
    return {
        "role_shares": {r: rc.get(r, 0) / max(len(roles), 1) for r in ROLES},
        "mix_ratio_K": nK / (nK + nE) if nK + nE else None,
        "size_levels": len(_levels([r["size"] for r in roles])) if roles else 0,
        "image_occupancy": page_params.get("A07"),
        "whitespace_ratio": page_params.get("A09"),
        "photo_mean_luminance": page_params.get("C03"),
        "photo_saturation": page_params.get("C06"),
        "font_family_count": page_params.get("B14"),
        "target_style": target_style,
    }


def analyze_page(ctx: PageContext, dctx: DocContext, bdoc: BilingualDoc, page_params: dict,
                 models: Optional[dict] = None, target_style: Optional[str] = None) -> list[ParameterResult]:
    pm, cfg = ctx.pm, ctx.cfg
    pi, src = pm.index, ctx.source
    out: list[ParameterResult] = []

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, source=kw.pop("source", src), page_index=pi, **kw))

    ink = _ink(pm.chars)
    comp = _group_counts(ink)
    nK = comp.get("hangul", 0) + comp.get("hangul_jamo", 0)
    nE = comp.get("latin_upper", 0) + comp.get("latin_lower", 0)
    tot = sum(comp.values())
    if pm.extraction_mode == "raster":
        for pid in SPECS:
            if SPECS[pid].scope != "document":
                R(pid, None, status=Status.NOT_MEASURED,
                  notes=["raster page: script/font identity requires text objects or OCR"])
        return out
    R("BK01", {"counts": comp, "shares": {k: v / tot for k, v in comp.items()} if tot else {},
               "mix_ratio_K": nK / (nK + nE) if nK + nE else None})

    # BK02 identification by script group
    by_group: dict = defaultdict(Counter)
    chars_by_font: dict = defaultdict(Counter)
    for c in ink:
        g = script_group(char_class(c.text))
        by_group[g][c.font_key] += 1
        chars_by_font[c.font_key][c.text] += 1
    ident = {}
    for g, cnt in by_group.items():
        n = sum(cnt.values())
        ident[{"K": "korean", "E": "latin", "D": "digits", "P": "punctuation", "O": "other"}[g]] = [
            dict(_font_status(dctx, fk, [ch for ch, _ in chars_by_font[fk].most_common()]) if fk else
                 {"font": None, "status": "unidentified"}, share=v / n) for fk, v in cnt.most_common()]
    R("BK02", ident, details={"outlined_text": _outlined_text_suspicion(pm),
                              "fallback_note": "named_only/partial: rendered glyphs come from a substitute "
                                               "font; geometry then describes the substitute"})

    # BK05/BK06 on the page: mixed lines, same size
    vs, bo = [], []
    for l in pm.lines:
        ks = [c for c in l.chars if char_class(c.text) == "hangul"]
        es = [c for c in l.chars if char_class(c.text) == "latin_upper" and c.text in "BDEFHIKLMNPRTXZ"]
        if ks and es and abs(np.median([c.size for c in ks]) - np.median([c.size for c in es])) < 0.01:
            hk = np.median([c.box[3] - c.box[1] for c in ks])
            he = np.median([c.box[3] - c.box[1] for c in es])
            if he > 0:
                vs.append(hk / he)
                s = float(np.median([c.size for c in ks]))
                bo.append((np.median([c.box[3] for c in ks]) - np.median([c.box[3] for c in es])) / s)
    pairs = []
    kfonts = [fk for fk in by_group.get("K", {}) if fk in bdoc.K]
    efonts = [fk for fk in by_group.get("E", {}) if fk in bdoc.E]
    for kf in kfonts:
        for ef in efonts:
            hv = bdoc.pair(kf, ef)
            if hv:
                pairs.append({"korean_font": kf, "latin_font": ef, **hv})
    R("BK05", {"page_tight_box_ratio": summary(vs),
               "outline_pairs": {f"{p['korean_font']}|{p['latin_font']}": {
                   "hangul_over_cap": (p["raw_pairs_K_E"]["H_visual_em"][0] / p["raw_pairs_K_E"]["H_visual_em"][1])
                   if p["raw_pairs_K_E"]["H_visual_em"][1] else None,
                   "hangul_over_x_height": p["raw_pairs_K_E"]["hangul_over_x_height"]} for p in pairs}}
      if (vs or pairs) else None,
      notes=["page ratio: same-size mixed lines, Hangul tight-box height / flat-bottom capital height"])
    R("BK06", {"page_bottom_offset_over_size": summary(bo),
               "outline_pairs": {f"{p['korean_font']}|{p['latin_font']}": {
                   "bottom_em_K_E": p["raw_pairs_K_E"]["bottom_em"],
                   "visual_center_em_K_E": p["raw_pairs_K_E"]["visual_center_em"]} for p in pairs}}
      if (bo or pairs) else None, notes=["positive bottom offset = Hangul ink ends above the Latin baseline "
                                          "(top-left page coordinates for the page variant: positive = lower)"])
    R("BK07", pairs or None, status=None if pairs else Status.UNDEFINED,
      notes=[] if pairs else ["no co-occurring Hangul and Latin fonts with measurable glyphs"])

    # BK08 spacing by script
    sp = defaultdict(list)
    ws = defaultdict(list)
    for l in pm.lines:
        cs = [c for c in l.chars if not c.generated]
        for a, b in zip(cs[:-1], cs[1:]):
            if a.text.isspace() or b.text.isspace():
                continue
            ga, gb = script_group(char_class(a.text)), script_group(char_class(b.text))
            key = ga + gb if ga == gb else "boundary_" + "".join(sorted(ga + gb))
            sp[key].append((b.box[0] - a.box[2]) / max(a.size, 1e-6))
        allc = l.chars
        for i, c in enumerate(allc):
            if c.text == " " and 0 < i < len(allc) - 1:
                nb = script_group(char_class(allc[i + 1].text))
                ws[nb].append((c.loose_box[2] - c.loose_box[0]) / max(c.size, 1e-6))
    R("BK08", {"gaps": {k: summary(v) for k, v in sp.items() if k in ("KK", "EE") or k.startswith("boundary")},
               "word_space": {k: summary(v) for k, v in ws.items()}} if sp else None,
      notes=["word-space widths are from PDFium (possibly generated) space boxes"])

    # BK09 hierarchy
    from .typography import body_size
    sizes = [c.size for c in ink]
    sb = body_size(sizes, [1.0] * len(sizes), float(cfg["typography"]["body_size_round"])) if sizes else None
    roles = _roles(pm, sb, cfg)
    lv = _levels([r["size"] for r in roles]) if roles else []
    per_role = {}
    for r in ROLES:
        rr = [x for x in roles if x["role"] == r]
        if rr:
            fonts = Counter()
            for x in rr:
                fonts.update(x["fonts"])
            per_role[r] = {"blocks": len(rr), "sizes": sorted({round(x["size"], 2) for x in rr}),
                           "fonts": dict(fonts)}
    R("BK09", {"body_size": sb, "levels": lv,
               "level_ratios": [lv[i] / lv[i + 1] for i in range(len(lv) - 1)], "roles": per_role}
      if roles else None, details={"blocks": roles})

    # BK11 contextual model
    c = context_vector(pm, roles, comp, page_params, target_style)
    model = (models or {}).get("bilingual_appropriateness")
    if model is not None and pairs:
        preds = []
        for p in pairs:
            preds.append({"pair": f"{p['korean_font']}|{p['latin_font']}",
                          **model.predict_pair(p, c, bdoc)})
        R("BK11", preds, details={"context": c}, source="model")
    else:
        R("BK11", None, status=Status.NO_MODEL, details={"context": c, "harmony_pairs": len(pairs)},
          notes=["no trained appropriateness model: no score is produced"])
    # BK12 per-criterion preference
    prefs, missing = {}, []
    for cr in CRITERIA:
        m = (models or {}).get(f"preference_{cr}")
        if m is None:
            missing.append(cr)
        else:
            prefs[cr] = m.predict_page(page_params)
    R("BK12", prefs or None, status=None if prefs else Status.NO_MODEL,
      details={"criteria_without_model": missing}, source="model" if prefs else src,
      notes=["criteria are separate labels and separate models"])
    return out


def analyze_document(dctx: DocContext, bdoc: BilingualDoc, with_candidates: bool = True) -> list[ParameterResult]:
    out: list[ParameterResult] = []

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, scope="document", source=kw.pop("source", "pdf_objects"), **kw))

    if bdoc.K:
        R("BK03", {fk: {"aggregate": p["aggregate"], "strata": p["strata"], "strata_covered": p["strata_covered"],
                        "n_glyphs": p["n_glyphs"]} for fk, p in bdoc.K.items()})
        rel = {fk: ink_complexity_relation(p) for fk, p in bdoc.K.items()}
        R("BK10", rel)
    else:
        R("BK03", None, status=Status.UNDEFINED, notes=["no Hangul set in a font with outlines"])
        R("BK10", None, status=Status.UNDEFINED)
    if bdoc.E:
        R("BK04", {fk: {"classes": p["classes"], "cap_height_em": p["cap_height_em"],
                        "x_height_em": p["x_height_em"], "baseline_em": p["baseline_em"]}
                   for fk, p in bdoc.E.items()})
    else:
        R("BK04", None, status=Status.UNDEFINED, notes=["no Latin letters with outlines"])
    if with_candidates and (bdoc.K or bdoc.E):
        from ..typo.candidates import candidate_pairs
        R("BK13", candidate_pairs(dctx, bdoc), source="derived")
    else:
        R("BK13", None, status=Status.NOT_MEASURED, notes=["candidate search disabled or no bilingual text"])
    return out
