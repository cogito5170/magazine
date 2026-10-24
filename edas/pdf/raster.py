"""Raster-based object estimation (pipeline fallback, spec §12) and image
"pages" for web references.

Everything produced here is an *estimate* (source='raster').

Algorithm (all thresholds in config ``raster``):
1. background colour = most frequent 5-bit-quantised colour of the border band;
2. foreground mask  = CIE76 ΔE*ab distance to the background > ``fg_delta_e``;
3. 8-connected components of the foreground mask;
4. a component is a *glyph candidate* if its height <= ``glyph_max_height``·H;
   glyph candidates are merged into text lines by horizontal dilation
   (``line_join`` x median glyph height) and lines into blocks;
5. remaining large components (area >= ``image_min_area``·A) with fill density
   >= ``image_min_fill`` are images; others are vector graphics.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from ..mathcore.color import rgb_to_lab
from ..mathcore.geometry import connected_box_groups, union_bbox
from ..mathcore.imaging import component_boxes, dilate_rect, label_components, resize_max
from .model import ImageObj, LayoutObject, PageModel, TextBlock, TextLine


def estimate_background(rgb: np.ndarray, band: float = 0.02) -> tuple[float, float, float]:
    H, W = rgb.shape[:2]
    b = max(1, int(round(band * min(H, W))))
    border = np.concatenate([rgb[:b].reshape(-1, 3), rgb[-b:].reshape(-1, 3),
                             rgb[:, :b].reshape(-1, 3), rgb[:, -b:].reshape(-1, 3)])
    q = np.clip((border * 31).round().astype(int), 0, 31)
    idx = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    mode = np.bincount(idx).argmax()
    sel = border[idx == mode]
    return tuple(float(x) for x in sel.mean(axis=0))


def segment_rgb(rgb: np.ndarray, cfg: dict) -> dict:
    """Segment an RGB image (any units) into estimated text lines, text blocks,
    images and vector regions.  Boxes are returned in *pixel* coordinates of
    the input image."""
    rc = cfg["raster"]
    small, s = resize_max(rgb, int(rc["work_max_side"]))
    H, W = small.shape[:2]
    bg = estimate_background(small)
    lab = rgb_to_lab(small)
    bgl = rgb_to_lab(np.asarray(bg)[None, None, :])[0, 0]
    fg = np.linalg.norm(lab - bgl, axis=-1) > float(rc["fg_delta_e"])
    lbl, n = label_components(fg)
    comps = component_boxes(lbl, n)
    gmax = float(rc["glyph_max_height"]) * H
    glyphs, large = [], []
    for c in comps:
        x0, y0, x1, y1 = c["box"]
        h, w = y1 - y0, x1 - x0
        if c["area"] < 3:
            continue
        if h <= gmax and w <= float(rc["glyph_max_aspect"]) * max(h, 1):
            glyphs.append(c)
        else:
            large.append(c)
    # images vs vectors among large components
    images, vectors = [], []
    for c in large:
        x0, y0, x1, y1 = c["box"]
        bw, bh = x1 - x0, y1 - y0
        fill = c["area"] / max(bw * bh, 1)
        region = small[y0:y1, x0:x1]
        var = float(region.reshape(-1, 3).std(axis=0).mean())
        if bw * bh >= float(rc["image_min_area"]) * W * H and fill >= float(rc["image_min_fill"]):
            images.append({"box": c["box"], "fill": fill, "color_std": var})
        else:
            vectors.append({"box": c["box"], "fill": fill})
    # glyphs inside an image are part of the image
    def inside(b, B):
        return b[0] >= B[0] and b[1] >= B[1] and b[2] <= B[2] and b[3] <= B[3]
    glyphs = [g for g in glyphs if not any(inside(g["box"], im["box"]) for im in images)]
    lines, blocks = [], []
    if glyphs:
        gh = float(np.median([g["box"][3] - g["box"][1] for g in glyphs]))
        mask = np.zeros((H, W), dtype=bool)
        for g in glyphs:
            x0, y0, x1, y1 = g["box"]
            mask[y0:y1, x0:x1] = True
        join = max(1, int(round(float(rc["line_join"]) * gh)))
        lm = dilate_rect(mask, 0, join)
        ll, nl = label_components(lm)
        for c in component_boxes(ll, nl):
            x0, y0, x1, y1 = c["box"]
            members = [g for g in glyphs if g["box"][0] >= x0 - 1 and g["box"][2] <= x1 + 1
                       and g["box"][1] >= y0 - 1 and g["box"][3] <= y1 + 1]
            if not members:
                continue
            tb = union_bbox([m["box"] for m in members])
            if len(members) < int(rc["min_glyphs_per_line"]):
                vectors.append({"box": tb, "fill": None})
                continue
            hs = np.array([m["box"][3] - m["box"][1] for m in members], float)
            bottoms = np.array([m["box"][3] for m in members], float)
            xs = sorted(members, key=lambda m: m["box"][0])
            gaps = [b["box"][0] - a["box"][2] for a, b in zip(xs[:-1], xs[1:])]
            lines.append({"box": tb, "glyph_height_px": float(np.median(hs)),
                          "line_height_px": float(tb[3] - tb[1]),
                          "baseline_px": float(np.median(bottoms)), "n_glyphs": len(members),
                          "gaps_px": [float(g) for g in gaps]})
        if lines:
            groups = connected_box_groups([l["box"] for l in lines],
                                          gap=float(rc["block_join"]) * gh)
            for g in groups:
                blocks.append({"box": union_bbox([lines[i]["box"] for i in g]), "lines": sorted(g)})
    inv = 1.0 / s

    def up(b):
        return tuple(float(v * inv) for v in b)

    for d in images + vectors + lines + blocks:
        d["box"] = up(d["box"])
    for l in lines:
        for k in ("glyph_height_px", "line_height_px", "baseline_px"):
            l[k] *= inv
        l["gaps_px"] = [g * inv for g in l["gaps_px"]]
    glyph_boxes = [g["box"] for g in glyphs]   # work-scale pixel boxes (fg mask coordinates)
    return {"images": images, "vectors": vectors, "lines": lines, "blocks": blocks,
            "background_rgb": bg, "work_scale": s, "foreground_fraction": float(fg.mean()),
            "fg_mask": fg, "glyph_boxes": glyph_boxes}


def segment_page(pm: PageModel, cfg: dict) -> None:
    """Replace a page's PDF-derived objects by raster estimates (in points)."""
    seg = segment_rgb(pm.render, cfg)
    k = 1.0 / pm.render_scale

    def pt(b):
        return tuple(v * k for v in b)

    pm.extraction_mode = "raster"
    pm.background_rgb = seg["background_rgb"]
    pm.images = [ImageObj(box=pt(i["box"]), placed_box=pt(i["box"]), px_size=(0, 0), effective_ppi=None,
                          crop_retention=None) for i in seg["images"]]
    pm.lines, pm.blocks = [], []
    for l in seg["lines"]:
        pm.lines.append(TextLine(chars=[], box=pt(l["box"]), baseline=l["baseline_px"] * k,
                                 size=l["glyph_height_px"] * k, font_key=None, text=""))
    for b in seg["blocks"]:
        ls = [pm.lines[i] for i in b["lines"]]
        pm.blocks.append(TextBlock(lines=ls, box=pt(b["box"]), size=float(np.median([l.size for l in ls]))))
    pm.chars = []
    W, H = pm.width, pm.height
    tol = float(cfg["layout"]["bleed_tolerance_pt"])

    def bleed(b):
        return b[0] <= tol or b[1] <= tol or b[2] >= W - tol or b[3] >= H - tol

    objs = []
    for i, b in enumerate(pm.blocks):
        objs.append(LayoutObject(id=f"p{pm.index}-t{i}", kind="text", box=b.box, bleed=bleed(b.box),
                                 source="raster", meta={"size_est": b.size, "lines": len(b.lines)}))
    for i, im in enumerate(pm.images):
        objs.append(LayoutObject(id=f"p{pm.index}-i{i}", kind="image", box=im.box, bleed=bleed(im.box),
                                 source="raster", meta={"image_index": i}))
    for i, v in enumerate(seg["vectors"]):
        b = pt(v["box"])
        if (b[2] - b[0]) * (b[3] - b[1]) < float(cfg["layout"]["vector_min_area_fraction"]) * W * H:
            continue
        objs.append(LayoutObject(id=f"p{pm.index}-v{i}", kind="vector", box=b, bleed=bleed(b), source="raster"))
    pm.objects = objs
    pm.raster = {"lines": seg["lines"], "fg_mask": seg["fg_mask"], "glyph_boxes": seg["glyph_boxes"],
                 "work_scale": seg["work_scale"]}


def image_page(rgb: np.ndarray, cfg: dict, index: int = 0, unit: str = "px") -> PageModel:
    """Wrap a standalone image (e.g. a web reference) as a raster page whose
    unit is the image pixel; normalised features are then comparable."""
    H, W = rgb.shape[:2]
    pm = PageModel(index=index, width=float(W), height=float(H), unit=unit, render=rgb, render_scale=1.0)
    segment_page(pm, cfg)
    pm.warnings.append("standalone image: page boundary assumed to equal the image boundary "
                       "(not verified; photographs of physical magazines violate this)")
    return pm
