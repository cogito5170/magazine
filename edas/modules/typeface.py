"""Typeface evaluation in five independent dimensions (typography correction).

  A Typeface intrinsic morphology ..... TA01, TA02          measured descriptors
  B Spacing & optical quality ......... TB01, TB02, TB03    measured descriptors
  C Contextual compatibility .......... TC01                Q = g_θ(z_f, z_c): model only
  D Korean–Latin harmony .............. BK01–BK13 (bilingual module)
  E Human aesthetic preference ........ TE01 (typeface itself, Experiment A)
                                        TE02 (in-page fit, Experiment B)
  TX01 keeps functional facts (size, contrast, hierarchy) apart from every
  aesthetic output for each display line.

The dimensions are never summed.  Size, contrast, alignment, hierarchy,
popularity, geometric similarity and font count are not inputs of any
aesthetic output here; aesthetic outputs exist only as preference-model
predictions from controlled tests, otherwise they are null.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

import numpy as np

from ..schema import MeasurementType as MT, ParameterResult, Status, make_result
from ..typo.morphology import morphology_vector
from ..typo.outlines import PdfFontOutlines
from ..typo.spacing import overshoot, size_dependence, word_spacing_report
from .common import DocContext, PageContext, spec

M = "typeface"
FORBIDDEN_INFERENCES = [
    "large title -> beautiful", "good readability -> sophisticated typeface",
    "good alignment -> appropriate font choice", "famous font -> high aesthetic quality",
    "geometric similarity of two fonts -> good pairing", "many fonts -> necessarily bad",
    "user dislikes -> universally bad typeface", "low saturation -> sophisticated",
    "few fonts -> good design", "wide margins -> luxurious",
    "balanced glyph geometry -> aesthetically superior", "similar to a famous brand/font -> appropriate",
    "model taste -> verified design defect",
]

SPECS = {s.parameter_id: s for s in [
    spec("TA01", "typeface_morphology_vector", M, unit="mixed", scope="document", mtype=MT.ESTIMATED,
         formula="z_f = [stroke contrast, width, weight (stroke/em, ink), curvature, curved share, counters, "
                 "terminal width ratio, skeleton end points, serif probe, decorative complexity, corners, "
                 "consistency CVs]",
         definition="Observed glyph-shape descriptors from the embedded outlines (not quality).",
         domain="see typo.morphology", missing="not measured for raster-only text (no outlines)"),
    spec("TA02", "glyph_shape_consistency", M, unit="CV", scope="document",
         formula="CV of stroke width (em) and of stroke contrast across glyphs of a font",
         definition="Glyph-to-glyph variation of stroke properties; per-glyph tables in details.",
         domain="[0, inf)"),
    spec("TB01", "display_word_optical_spacing", M, unit="em",
         formula="per adjacent pair: applied adjustment = actual − nominal advance; tight gap; optical gap "
                 "(mean white run in the x-height/cap band); word balance = CV(optical gaps)",
         definition="For display lines (size >= title_ratio x body size): spacing as set in the PDF.",
         domain="R"),
    spec("TB02", "optical_overshoot", M, unit="em", scope="document",
         formula="top/bottom of round letters (O o c e s a) minus flat references (H x)", domain="R"),
    spec("TB03", "render_size_dependence", M, unit="ratio",
         formula="ink coverage at s px/em ÷ coverage at 200 px/em", domain="(0, inf)",
         notes=["polygon rasteriser without hinting; actual renderers differ"]),
    spec("TC01", "typeface_contextual_compatibility", M, unit="probability", mtype=MT.PREDICTED,
         formula="Q_aesthetic(f, c) = g_θ(z_f, z_c)", domain="[0, 1]",
         missing="null without a trained and validated model"),
    spec("TE01", "typeface_preference_intrinsic", M, unit="BT score", mtype=MT.PREDICTED, scope="document",
         formula="Bradley–Terry on Experiment A judgments, one model per criterion", domain="R",
         missing="insufficient_data below the minimum number of decisive judgments"),
    spec("TE02", "typeface_preference_in_page", M, unit="BT score", mtype=MT.PREDICTED, scope="document",
         formula="Bradley–Terry on Experiment B judgments, one model per criterion", domain="R",
         missing="insufficient_data below the minimum number of decisive judgments"),
    spec("TX01", "evaluation_separation", M, unit="report",
         formula="functional facts | morphology | spacing | context | preference, kept apart per display line",
         definition="Guards against substituting size/contrast/hierarchy for aesthetic suitability.",
         domain="report"),
]}


def _font_outlines(dctx: DocContext, fk: str):
    f = dctx.doc.fonts.get(fk)
    if f is None or f.handle is None:
        return None
    return PdfFontOutlines(f.handle, fk)


def _display_lines(pm, sb: Optional[float], ratio: float, k: int = 3):
    if not sb:
        return []
    ls = [l for l in pm.lines if l.size >= ratio * sb and l.font_key]
    return sorted(ls, key=lambda l: -l.size)[:k]


def _body(pm_chars, step):
    from .typography import body_size
    sizes = [c.size for c in pm_chars if not c.text.isspace()]
    return body_size(sizes, [1.0] * len(sizes), step) if sizes else None


def analyze_document(dctx: DocContext) -> tuple[list[ParameterResult], dict]:
    out = []
    morph = {}
    chars = [c for p in dctx.doc.pages if p.extraction_mode != "raster" for c in p.chars
             if not c.text.isspace() and not c.generated]
    by_font = {}
    for c in chars:
        by_font.setdefault(c.font_key, Counter())[c.text] += 1
    for fk, cnt in by_font.items():
        fo = _font_outlines(dctx, fk)
        if fo is None:
            continue
        letters = [ch for ch, _ in cnt.most_common() if ch.isalpha()][:40] or [ch for ch, _ in cnt.most_common(20)]
        mv = morphology_vector(fo, letters)
        f = dctx.doc.fonts[fk]
        mv["font_source"] = "embedded outlines" if f.embedded else "NOT embedded: outlines of the renderer's substitute"
        morph[fk] = mv
    if morph:
        out.append(make_result(SPECS["TA01"], {fk: m["z"] for fk, m in morph.items()}, scope="document",
                               source="pdf_objects",
                               details={fk: {"n_glyphs": m["n_glyphs"], "font_source": m["font_source"]}
                                        for fk, m in morph.items()},
                               notes=["descriptors are observations, not aesthetic quality"]))
        out.append(make_result(SPECS["TA02"], {fk: {"stroke_cv": m["z"]["stroke_cv"], "contrast_cv": m["z"]["contrast_cv"]}
                                               for fk, m in morph.items() if m["z"]}, scope="document",
                               source="pdf_objects",
                               details={"per_glyph": {fk: {ch: {k: g.get(k) for k in (
                                   "T_s", "C_stroke", "aspect", "D_ink", "counter_ratio", "cg_x_rel", "cg_y_rel",
                                   "terminal_width_ratio", "endpoints", "curvature_mean", "height_em")}
                                   for ch, g in m["glyphs"].items()} for fk, m in morph.items()}}))
        out.append(make_result(SPECS["TB02"], {fk: overshoot(_font_outlines(dctx, fk)) for fk in morph},
                               scope="document", source="pdf_objects"))
    else:
        for pid in ("TA01", "TA02", "TB02"):
            out.append(make_result(SPECS[pid], None, scope="document", status=Status.NOT_MEASURED,
                                   notes=["no font outlines available (raster-only or no text); "
                                          "shape is never inferred from font names"]))
    return out, morph


def preference_results(store, fonts: list[str], min_decisive: int = 20) -> list[ParameterResult]:
    from ..preference.bt import BradleyTerry, InsufficientData
    from ..preference.schema import CRITERIA
    from ..preference.validate import cross_validate_bt, inter_rater_agreement
    out = []
    for pid, exp in (("TE01", "A_typeface"), ("TE02", "B_page")):
        res, missing = {}, {}
        js_all = store.load(experiment=exp) if store else []
        for cr, meta in CRITERIA.items():
            if exp not in meta["experiments"]:
                continue
            js = [j for j in js_all if j.criterion == cr]
            comps = [(j.font_a, j.font_b, j.choice, j.rater_id) for j in js if j.choice != "cannot_judge"]
            try:
                m = BradleyTerry(min_decisive=min_decisive, hierarchical=True).fit(comps)
            except InsufficientData as e:
                missing[cr] = str(e)
                continue
            cv = cross_validate_bt(js, lambda j: j.page_id or "?", min_decisive=min_decisive)
            res[cr] = {"scores": {f: m.score(f) for f in fonts if m.score(f) is not None},
                       "all_items": dict(zip(m.items, m.q.tolist())), "n_judgments": len(js),
                       "raters": len(m.raters), "agreement": inter_rater_agreement(js),
                       "grouped_cv": {k: cv.get(k) for k in ("status", "accuracy", "log_loss", "brier", "n_test")},
                       "claim_type": "controlled_preference_test"}
        out.append(make_result(SPECS[pid], res or None, scope="document",
                               status=None if res else Status.INSUFFICIENT_DATA, source="model" if res else "derived",
                               details={"criteria_without_enough_data": missing,
                                        "personal_vs_group": "group score = q; personal = q + rater deviation"},
                               notes=["one model per criterion; Experiment A and B never pooled"]))
    return out


def analyze_page(ctx: PageContext, dctx: DocContext, morph: dict, page_params: dict,
                 target_style: Optional[str] = None, model=None) -> list[ParameterResult]:
    pm, cfg = ctx.pm, ctx.cfg
    out = []
    pi = pm.index

    def R(pid, value, **kw):
        out.append(make_result(SPECS[pid], value, source=kw.pop("source", ctx.source), page_index=pi, **kw))

    if pm.extraction_mode == "raster":
        for pid in ("TB01", "TB03", "TC01", "TX01"):
            R(pid, None, status=Status.NOT_MEASURED,
              notes=["raster-only text: glyph outlines unavailable; resolution/anti-aliasing uncertainty too large"])
        return out
    sb = _body(pm.chars, float(cfg["typography"]["body_size_round"]))
    ratio = float(cfg["typography"]["bilingual"]["roles"]["title_ratio"])
    disp = _display_lines(pm, sb, ratio)
    spacing, sizedep, sep = [], {}, []
    for l in disp:
        fo = _font_outlines(dctx, l.font_key)
        if fo is None:
            continue
        chars = [c for c in l.chars if not c.generated]
        words, cur = [], []
        for c in chars + [None]:
            if c is None or c.text.isspace():
                if cur:
                    words.append(cur)
                cur = []
            else:
                cur.append(c)
        for w in words[:3]:
            txt = "".join(c.text for c in w)
            if len(txt) < 2:
                continue
            s = float(np.median([c.size for c in w]))
            pos = [(c.origin[0] - w[0].origin[0]) / s for c in w]
            rep = word_spacing_report(fo, txt, positions_em=pos)
            rep["font"] = l.font_key
            rep["size_pt"] = s
            spacing.append(rep)
            if txt not in sizedep:
                sizedep[txt] = size_dependence(fo, txt)
        sep.append({
            "text": l.text[:80], "font": l.font_key,
            "functional_facts": {"size_pt": l.size, "size_over_body": l.size / sb if sb else None,
                                 "contrast_ratio_page_B18": (page_params.get("B18") or {}).get("median")
                                 if isinstance(page_params.get("B18"), dict) else None,
                                 "role": "display (size rule)"},
            "intrinsic_morphology": "TA01/TA02[%s]" % l.font_key if l.font_key in morph else None,
            "spacing": "TB01",
            "contextual_compatibility": None,
            "human_preference": "see TE01/TE02 (null without judgments)",
            "aesthetic_verdict": None,
            "aesthetic_verdict_reason": "no validated preference model; functional facts are not aesthetic evidence",
        })
    R("TB01", spacing or None, status=None if spacing else Status.UNDEFINED, source="pdf_objects",
      notes=[] if spacing else ["no display line (size >= title_ratio x body size)"])
    R("TB03", sizedep or None, status=None if sizedep else Status.UNDEFINED, source="pdf_objects")
    zc = {"role": "display", "page_image_occupancy": page_params.get("A07"),
          "page_whitespace": page_params.get("A09"),
          "photo_luminance": (page_params.get("C03") or {}).get("area_weighted_mean")
          if isinstance(page_params.get("C03"), dict) else None,
          "photo_saturation": (page_params.get("C06") or {}).get("area_weighted_mean")
          if isinstance(page_params.get("C06"), dict) else None,
          "script_mix_K": ((page_params.get("BK01") or {}).get("mix_ratio_K")
                           if isinstance(page_params.get("BK01"), dict) else None),
          "target_style": target_style}
    if model is not None and disp:
        R("TC01", {l.font_key: model.predict(morph.get(l.font_key, {}).get("z"), zc) for l in disp},
          source="model", details={"z_c": zc, "validation": model.validation_summary()})
    else:
        R("TC01", None, status=Status.NO_MODEL, details={"z_c": zc},
          notes=["Q_aesthetic is not produced without a trained, validated model"])
    R("TX01", {"display_lines": sep, "forbidden_inferences": FORBIDDEN_INFERENCES},
      status=None if sep else Status.UNDEFINED, source="derived")
    return out
