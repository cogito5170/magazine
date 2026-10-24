"""Grouping of extracted primitives into layout objects.

chars -> lines -> blocks (text objects); images; vector paths grouped by
proximity (vector objects).  All grouping thresholds come from the config and
are expressed relative to the font size or the page diagonal.
"""
from __future__ import annotations

import numpy as np

from ..mathcore.geometry import area, connected_box_groups, union_bbox
from .model import LayoutObject, PageModel, TextBlock, TextLine


def _wmedian(vals, wts):
    o = np.argsort(vals)
    v, w = np.asarray(vals)[o], np.asarray(wts, float)[o]
    c = np.cumsum(w)
    return float(v[np.searchsorted(c, 0.5 * c[-1])])


def build_lines_and_blocks(pm: PageModel, tcfg: dict) -> None:
    base_tol = float(tcfg["line_baseline_tol"])      # x size
    gap_tol = float(tcfg["line_gap_tol"])            # x size
    lines: list[list] = []
    cur: list = []
    for ch in pm.chars:
        if ch.text.isspace():
            if cur:
                cur.append(ch)
            continue
        if not cur:
            cur = [ch]
            continue
        prev = next((c for c in reversed(cur) if not c.text.isspace()), cur[-1])
        s = max(prev.size, ch.size, 1e-6)
        same_base = abs(ch.origin[1] - prev.origin[1]) <= base_tol * s
        gap = ch.box[0] - prev.box[2]
        if same_base and -0.5 * s <= gap <= gap_tol * s:
            cur.append(ch)
        else:
            lines.append(cur)
            cur = [ch]
    if cur:
        lines.append(cur)
    out: list[TextLine] = []
    for ln in lines:
        ink = [c for c in ln if not c.text.isspace()]
        if not ink:
            continue
        box = union_bbox([c.box for c in ink])
        sizes = [c.size for c in ink]
        fonts: dict = {}
        for c in ink:
            fonts[c.font_key] = fonts.get(c.font_key, 0) + 1
        out.append(TextLine(chars=ln, box=box, baseline=float(np.median([c.origin[1] for c in ink])),
                            size=float(np.median(sizes)), font_key=max(fonts, key=fonts.get),
                            text="".join(c.text for c in ln).strip()))
    pm.lines = out

    # blocks: top-to-bottom greedy assignment
    lead_tol = float(tcfg["block_leading_tol"])
    size_ratio = float(tcfg["block_size_ratio"])
    blocks: list[list[TextLine]] = []
    for ln in sorted(out, key=lambda l: (l.baseline, l.box[0])):
        best = None
        for bl in blocks:
            last = bl[-1]
            s = max(last.size, ln.size)
            if max(last.size, ln.size) / max(min(last.size, ln.size), 1e-6) > size_ratio:
                continue
            vgap = ln.box[1] - last.box[3]
            if not (-0.3 * s <= vgap <= lead_tol * s):
                continue
            ov = min(ln.box[2], last.box[2]) - max(ln.box[0], last.box[0])
            left_al = abs(ln.box[0] - last.box[0]) <= 0.5 * s
            if ov > 0.3 * min(ln.box[2] - ln.box[0], last.box[2] - last.box[0]) or left_al:
                best = bl
                break
        if best is None:
            blocks.append([ln])
        else:
            best.append(ln)
    pm.blocks = []
    for bl in blocks:
        n = [len([c for c in l.chars if not c.text.isspace()]) for l in bl]
        pm.blocks.append(TextBlock(lines=bl, box=union_bbox([l.box for l in bl]),
                                   size=_wmedian([l.size for l in bl], n)))


def build_layout_objects(pm: PageModel, cfg: dict) -> None:
    W, H = pm.width, pm.height
    bleed_tol = float(cfg["layout"]["bleed_tolerance_pt"])
    diag = float(np.hypot(W, H))
    objs: list[LayoutObject] = []

    def bleed(b):
        return b[0] <= bleed_tol or b[1] <= bleed_tol or b[2] >= W - bleed_tol or b[3] >= H - bleed_tol

    for i, b in enumerate(pm.blocks):
        objs.append(LayoutObject(id=f"p{pm.index}-t{i}", kind="text", box=b.box, bleed=bleed(b.box),
                                 meta={"size": b.size, "lines": len(b.lines),
                                       "text": " ".join(l.text for l in b.lines)[:200]}))
    for i, im in enumerate(pm.images):
        if area(im.box) <= 0:
            continue
        objs.append(LayoutObject(id=f"p{pm.index}-i{i}", kind="image", box=im.box, bleed=bleed(im.box),
                                 meta={"px_size": im.px_size, "ppi": im.effective_ppi}))
    vec = [v for v in pm.vectors if not v.is_background]
    min_frac = float(cfg["layout"]["vector_min_area_fraction"])
    gap = float(cfg["layout"]["vector_group_gap"]) * diag
    if vec:
        groups = connected_box_groups([v.box for v in vec], gap=gap)
        k = 0
        for g in groups:
            box = union_bbox([vec[j].box for j in g])
            # hairline rules have ~0 area: keep them if long enough
            long_side = max(box[2] - box[0], box[3] - box[1])
            if area(box) < min_frac * W * H and long_side < 0.05 * diag:
                continue
            objs.append(LayoutObject(id=f"p{pm.index}-v{k}", kind="vector", box=box, bleed=bleed(box),
                                     meta={"paths": len(g)}))
            k += 1
    pm.objects = objs
