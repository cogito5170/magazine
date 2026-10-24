"""Change proposals (spec §11 + post-mortem protocol).

Every proposal is a ``ChangeProposal`` with evidence records, preserved
strengths, trade-offs and ``user_approval_status = not_requested``.  Nothing
is applied to any PDF: the original is never modified and no final document
is produced before approval (see ``governance.gate``).

Proposal sources
1. technical constraints with an external or logical basis (contrast, text
   inside page, image resolution [unverified convention]);
2. reference matching: only when the user supplied a reference profile;
   phrased as "closer to the selected reference", never as improvement.
Layout changes are simulated on the extracted geometry (uniform transforms
only: no distortion) and the resulting metrics are reported.
"""
from __future__ import annotations

import copy
from typing import Optional

import numpy as np

from ..governance.evidence import ChangeProposal, ClaimType, Evidence, Purpose
from ..mathcore.color import relative_luminance
from ..mathcore.geometry import union_area
from .solver import nelder_mead

# parameter -> modifiable design variables
LEVERS = {
    "A04": "margins: translate/scale the non-bleed content block", "A05": "horizontal/vertical content offset",
    "A06": "object sizes", "A07": "image sizes (uniform scaling)", "A08": "text size / measure / leading",
    "A09": "object sizes", "A03": "object positions (snap to grid lines)", "B03": "heading or body size",
    "B12": "leading", "B10": "tracking", "B13": "measure (text frame width)", "C03": "image tone",
    "C06": "image saturation", "D02": "placement of heavy objects",
}


def _req_luminance(bg: float, target: float = 4.5) -> dict:
    dark = (bg + 0.05) / target - 0.05
    light = target * (bg + 0.05) - 0.05
    return {"dark_text_max_luminance": dark if dark >= 0 else None,
            "light_text_min_luminance": light if light <= 1 else None}


def technical_proposals(doc, analysis, cfg, protected: set[int]) -> list[ChangeProposal]:
    props = []
    thr = cfg["technical_targets"]["text_contrast_min"]
    for pm in doc.pages:
        page = pm.index + 1
        if page in protected:
            continue
        for l in pm.lines:
            ink = [c for c in l.chars if not c.text.isspace() and c.fill_rgb is not None]
            if not ink:
                continue
            from ..modules.typography import line_contrast_detail
            rgb = tuple(np.median(np.array([c.fill_rgb for c in ink]), axis=0))
            det = line_contrast_detail(pm, l, rgb, cfg)
            target = thr["large_text_value"] if l.size >= thr["large_text_pt"] else thr["value"]
            if det is None or det["ratio"] >= target:
                continue
            cr, Lt, Lb = det["ratio"], det["text_luminance"], det["background_luminance"]
            props.append(ChangeProposal(
                page=page, element=f"text line '{l.text[:40]}'",
                original_state={"contrast_ratio": cr, "text_luminance": Lt, "background_luminance": Lb,
                                "size_pt": l.size},
                proposed_change={"goal": f"contrast >= {target}:1", **_req_luminance(Lb, target),
                                 "alternatives": ["darken/lighten text colour", "change the local background"]},
                purpose=Purpose.FUNCTIONAL,
                evidence=[Evidence(claim_type=ClaimType.OFFICIAL_STANDARD, source_id="wcag22_sc143",
                                   note="web accessibility criterion used as a legibility reference for a PDF"),
                          Evidence(claim_type=ClaimType.MEASURED_FACT,
                                   measurement_method="WCAG contrast of PDF fill colour vs median rendered "
                                                      f"background at {cfg['render']['dpi']} dpi",
                                   result=cr, uncertainty="background estimate on textured images; anti-aliasing")],
                preserved_strengths=["typeface, size, position and layout unchanged"],
                expected_tradeoffs=["text colour identity changes"]))
        for im in pm.images:
            thr_ppi = cfg["technical_targets"]["effective_ppi_min"]
            if im.effective_ppi and min(im.effective_ppi) < thr_ppi["value"]:
                w_pt = im.placed_box[2] - im.placed_box[0]
                props.append(ChangeProposal(
                    page=page, element="image", original_state={"effective_ppi": im.effective_ppi, "px": im.px_size},
                    proposed_change={"source_px_width_needed": int(np.ceil(thr_ppi["value"] * w_pt / 72)),
                                     "or_max_placed_width_pt": im.px_size[0] / thr_ppi["value"] * 72},
                    purpose=Purpose.FUNCTIONAL,
                    evidence=[Evidence(claim_type=ClaimType.MEASURED_FACT, measurement_method="pixel size / placed size",
                                       result=min(im.effective_ppi)),
                              Evidence(claim_type=ClaimType.SUBJECTIVE_HYPOTHESIS,
                                       note=f"threshold {thr_ppi['value']} ppi is a print convention without a "
                                            "verified source in this project; screen-only PDFs may not need it")],
                    preserved_strengths=["image content and crop unchanged"],
                    expected_tradeoffs=["larger file size"]))
    return props


# ---------------------------------------------------------------- geometry simulation
def geometry_metrics(objs, lines, W, H) -> dict:
    nb = [o for o in objs if not o.bleed]
    page = (0, 0, W, H)
    content = [l.box for l in lines] + [o.box for o in objs if o.kind != "text"]
    out = {"A06": union_area(content, page) / (W * H),
           "A07": union_area([o.box for o in objs if o.kind == "image"], page) / (W * H)}
    out["A09"] = 1 - out["A06"]
    if nb:
        b = np.array([o.box for o in nb])
        out.update({"A04.M_l": b[:, 0].min() / W, "A04.M_r": (W - b[:, 2].max()) / W,
                    "A04.M_t": b[:, 1].min() / H, "A04.M_b": (H - b[:, 3].max()) / H})
        out["A05.horizontal"] = abs(out["A04.M_l"] - out["A04.M_r"])
        out["A05.vertical"] = abs(out["A04.M_t"] - out["A04.M_b"])
    return out


def _transform(box, tx, ty, s, cx, cy):
    return ((box[0] - cx) * s + cx + tx, (box[1] - cy) * s + cy + ty,
            (box[2] - cx) * s + cx + tx, (box[3] - cy) * s + cy + ty)


def simulate_content_transform(pm, tx, ty, s, locked: set[str]):
    nb = [o for o in pm.objects if not o.bleed and o.id not in locked]
    if not nb:
        return None
    b = np.array([o.box for o in nb])
    cx, cy = b[:, 0].min(), b[:, 1].min()
    objs = copy.deepcopy(pm.objects)
    moved = {o.id for o in nb}
    for o in objs:
        if o.id in moved:
            o.box = _transform(o.box, tx, ty, s, cx, cy)
    lines = copy.deepcopy(pm.lines)
    tb = [o.box for o in pm.objects if o.kind == "text" and o.id in moved]
    for l in lines:
        if any(l.box[0] >= t[0] - 0.5 and l.box[2] <= t[2] + 0.5 and l.box[1] >= t[1] - 0.5 and l.box[3] <= t[3] + 0.5
               for t in tb):
            l.box = _transform(l.box, tx, ty, s, cx, cy)
    return objs, lines


def _violations(objs, W, H, locked_boxes):
    v = 0.0
    for o in objs:
        if o.bleed:
            continue
        b = o.box
        v += max(0, -b[0]) + max(0, -b[1]) + max(0, b[2] - W) + max(0, b[3] - H)
    return v


def optimize_reference_layout(pm, rows: list[dict], cfg) -> Optional[dict]:
    """min_x Σ E_k(x) over x = (tx, ty, s) of the non-bleed, unlocked content,
    for layout features with a reference target; constraints as penalties:
    page bounds, uniform scale only (no distortion), locked objects fixed,
    s in [0.8, 1.2], |t| <= max_shift."""
    from ..mathcore.errors import error_value
    targets = {r["feature"]: r for r in rows if r["feature"] in
               ("A04.M_l", "A04.M_r", "A04.M_t", "A04.M_b", "A05.horizontal", "A05.vertical", "A06", "A07", "A09")
               and r.get("tau")}
    if not targets:
        return None
    locked = set(cfg["optimization"]["locked_ids"])
    W, H = pm.width, pm.height
    ms = float(cfg["optimization"]["max_shift_fraction"])

    def f(x):
        tx, ty, s = x
        sim = simulate_content_transform(pm, tx * W, ty * H, s, locked)
        if sim is None:
            return 1e9
        objs, lines = sim
        m = geometry_metrics(objs, lines, W, H)
        loss = sum(error_value(m[k], r["target_median"], r["tau"], "two_sided") for k, r in targets.items() if k in m)
        pen = _violations(objs, W, H, None) / max(W, H) * 1e3
        pen += 1e3 * (max(0, abs(tx) - ms) + max(0, abs(ty) - ms) + max(0, 0.8 - s) + max(0, s - 1.2))
        return loss + pen

    x0 = np.array([0.0, 0.0, 1.0])
    res = nelder_mead(f, x0, step=np.array([0.01, 0.01, 0.03]), max_iter=300)
    tx, ty, s = res["x"]
    sim = simulate_content_transform(pm, tx * W, ty * H, s, locked)
    before = geometry_metrics(pm.objects, pm.lines, W, H)
    after = geometry_metrics(*sim, W, H) if sim else None
    return {"transform": {"translate_x_pt": tx * W, "translate_y_pt": ty * H, "uniform_scale": s},
            "objective_before": f(x0), "objective_after": res["fun"], "metrics_before": before,
            "metrics_after": after, "targets": list(targets), "constraint_violation": _violations(sim[0], W, H, None) if sim else None}


def reference_proposals(doc, page_rows: dict[int, list[dict]], cfg, protected: set[int],
                        reference_label: str, top_k: int = 5) -> list[ChangeProposal]:
    props = []
    for pi, rows in page_rows.items():
        page = pi + 1
        if page in protected:
            continue
        off = [r for r in rows if r.get("error") and r["error"] > 1.0 and r["target_status"] == "ok"][:top_k]
        if not off:
            continue
        opt = optimize_reference_layout(doc.pages[pi], rows, cfg)
        for r in off:
            pid = r["feature"].split(".")[0]
            change = {"modifiable_variable": LEVERS.get(pid, "not mapped to a design variable"),
                      "toward_reference_median": r["target_median"],
                      "reference_q25_q75": r["target_range_q25_q75"]}
            if opt and r["feature"] in (opt["metrics_after"] or {}):
                change["simulated_layout_transform"] = opt["transform"]
                change["simulated_value_after"] = opt["metrics_after"][r["feature"]]
            props.append(ChangeProposal(
                page=page, element=r["feature"], original_state={"value": r["value"]}, proposed_change=change,
                purpose=Purpose.REFERENCE_MATCH,
                evidence=[Evidence(claim_type=ClaimType.MEASURED_FACT,
                                   measurement_method=f"comparison with reference profile '{reference_label}' "
                                                      f"(n={r['n_reference']}, t=median, τ=IQR/1.349)",
                                   result={"deviation": r["deviation"], "error": r["error"], "tau": r["tau"]},
                                   uncertainty="reference median CI and n in the profile; "
                                               + ("definition depends on extraction source" if r["source_dependent"] else "")),
                          Evidence(claim_type=ClaimType.SUBJECTIVE_HYPOTHESIS,
                                   note="moving toward the selected reference is not evidence of better design")],
                preserved_strengths=["all other features unchanged in the simulation"],
                expected_tradeoffs=["other features may move away from the reference; check simulated metrics"]))
    return props
