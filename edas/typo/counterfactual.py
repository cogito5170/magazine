"""Counterfactual font comparison (font-only changes).

Experiment A — typeface itself
  same word, same white background, same visual height (cap or x height
  equalised), same rasteriser and resolution; spacing = nominal advances
  without kerning for every font (recorded), plus the as-set spacing of the
  original.  Ink density is *recorded*, not equalised.

Experiment B — fit in the real page
  same page rendering with the target text removed (in-memory copy of the
  PDF; the source file is never written), same title region and point size,
  same colour; only the font of the target run changes.  Width change,
  overflow beyond the right margin and the greedy re-wrap line count are
  recorded.  Every variant, including the original, is redrawn by the same
  outline rasteriser so all stimuli share the rendering conditions.

Outputs: PNG stimuli + manifest.json (stimulus ids, sha256, conditions, pairs).
The two experiments are separate manifests and must never be pooled.
"""
from __future__ import annotations

import ctypes
import datetime as dt
import hashlib
import json
import os
import re
from typing import Optional

import numpy as np
from PIL import Image

import pypdfium2 as pdfium
import pypdfium2.raw as R

from ..mathcore.glyph import flatten, outline_bbox
from .outlines import OutlineFont, PdfFontOutlines, layout_word, render_outline_text


def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")[:48]


def _sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def find_run(doc, page_index: int, text: str) -> Optional[dict]:
    """Locate ``text`` in a page's lines; returns chars, font and as-set geometry."""
    pm = doc.pages[page_index]
    for l in pm.lines:
        chars = [c for c in l.chars if not c.generated]
        s = "".join(c.text for c in chars)
        i = s.find(text)
        if i >= 0:
            run = chars[i:i + len(text)]
            fk = run[0].font_key
            size = float(np.median([c.size for c in run if not c.text.isspace()]))
            x0 = run[0].origin[0]
            return {"chars": run, "font_key": fk, "size": size, "line": l,
                    "baseline": float(np.median([c.origin[1] for c in run])), "x0": x0,
                    "positions_em": [(c.origin[0] - x0) / size for c in run],
                    "fill_rgb": next((c.fill_rgb for c in run if c.fill_rgb), (0, 0, 0)),
                    "page": page_index}
    return None


def _cap_em(font: OutlineFont, metric: str) -> Optional[float]:
    probe = "H" if metric == "cap" else "x"
    c = font.contours(probe)
    if not c:
        return None
    return outline_bbox(flatten(c))[3]


def _save(img: np.ndarray, rgb, path: str, bg=(1.0, 1.0, 1.0)):
    a = img[..., None]
    out = (1 - a) * np.asarray(bg)[None, None, :] + a * np.asarray(rgb)[None, None, :]
    Image.fromarray((np.clip(out, 0, 1) * 255).astype("uint8")).save(path)


def experiment_a(fonts: dict[str, OutlineFont], word: str, out_dir: str, original: Optional[str] = None,
                 as_set_positions_em: Optional[list[float]] = None, target_height_px: int = 96,
                 metric: str = "cap", page_ref: Optional[dict] = None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rend = {}
    for label, f in fonts.items():
        h = _cap_em(f, metric)
        if not h:
            rend[label] = {"error": f"no '{'H' if metric == 'cap' else 'x'}' glyph to equalise height"}
            continue
        ppem = target_height_px / h
        variants = [("nominal", None)]
        if label == original and as_set_positions_em:
            variants.append(("as_set", as_set_positions_em))
        for vname, pos in variants:
            img, info = render_outline_text(f, layout_word(f, word, positions_em=pos), ppem, supersample=4)
            rend[f"{label}|{vname}"] = {"img": img, "info": info, "ppem": ppem, "height_em": h, "font": label,
                                        "spacing": "as set in PDF (includes applied kerning/tracking)"
                                        if pos else "nominal advances, no kerning", "source": f.source}
    ok = {k: v for k, v in rend.items() if "img" in v}
    if not ok:
        return {"experiment": "A_typeface", "stimuli": [], "errors": rend}
    Hc = max(v["img"].shape[0] for v in ok.values()) + 40
    Wc = max(v["img"].shape[1] for v in ok.values()) + 40
    stimuli = []
    for k, v in ok.items():
        img = v["img"]
        canvas = np.zeros((Hc, Wc))
        oy = int(round(Hc / 2 + target_height_px / 2 - v["info"]["origin_px"][1]))   # common baseline
        ox = (Wc - img.shape[1]) // 2
        oy = max(0, min(oy, Hc - img.shape[0]))
        canvas[oy:oy + img.shape[0], ox:ox + img.shape[1]] = img
        sid = f"A-{_slug(word)}-{_slug(k)}"
        path = os.path.join(out_dir, sid + ".png")
        _save(canvas, (0, 0, 0), path)
        ink = img[img > 0.02]
        stimuli.append({"stimulus_id": sid, "file": os.path.basename(path), "sha256": _sha(path), "font": v["font"],
                        "variant": k.split("|")[1], "font_source": v["source"], "spacing": v["spacing"],
                        "px_per_em": v["ppem"], "equalised_metric": metric, "metric_height_em": v["height_em"],
                        "ink_coverage_in_box": float(img.mean()), "mean_ink_alpha": float(ink.mean()) if ink.size else None,
                        "word_width_px": int(img.shape[1]), "missing_glyphs": v["info"]["missing"]})
    pairs = []
    base = [s for s in stimuli if s["font"] == original and s["variant"] == "nominal"]
    others = [s for s in stimuli if s["font"] != original and s["variant"] == "nominal"]
    if base:
        pairs = [{"a": base[0]["stimulus_id"], "b": o["stimulus_id"]} for o in others]
    man = {"experiment": "A_typeface", "word": word, "original_font": original, "page_ref": page_ref,
           "created": dt.datetime.now(dt.timezone.utc).isoformat(),
           "conditions": {"background": "#ffffff", "ink": "#000000", "target_height_px": target_height_px,
                          "equalised_metric": metric, "rasteriser": "even-odd polygon fill, 4x supersampling",
                          "canvas_px": [Wc, Hc], "ink_density": "recorded, not equalised",
                          "kerning": "not applied to nominal variants; as_set variant reproduces PDF positions"},
           "stimuli": stimuli, "pairs": pairs,
           "errors": {k: v["error"] for k, v in rend.items() if "error" in v}}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=2)
    return man


def _remove_text_objects(page, char_indices: list[int], tp) -> int:
    targets = set()
    for i in char_indices:
        o = R.FPDFText_GetTextObject(tp, i)
        if o:
            targets.add(ctypes.cast(o, ctypes.c_void_p).value)
    removed = 0
    n = R.FPDFPage_CountObjects(page)
    for k in reversed(range(n)):
        obj = R.FPDFPage_GetObject(page, k)
        if ctypes.cast(obj, ctypes.c_void_p).value in targets:
            if R.FPDFPage_RemoveObject(page, obj):
                R.FPDFPageObj_Destroy(obj)
                removed += 1
    R.FPDFPage_GenerateContent(page)
    return removed


def experiment_b(pdf_path: str, doc, run: dict, fonts: dict[str, OutlineFont], out_dir: str,
                 original: str, dpi: float = 120.0, right_limit_pt: Optional[float] = None) -> dict:
    """Redraw the target run with each font on the same text-free page background."""
    os.makedirs(out_dir, exist_ok=True)
    with open(pdf_path, "rb") as fh:
        data = fh.read()
    pdf = pdfium.PdfDocument(data)
    page = pdf[run["page"]]
    tp = page.get_textpage()
    pm = doc.pages[run["page"]]
    # character indices of the run in PDFium's text page (match by origin)
    idx = []
    ox, oy = ctypes.c_double(), ctypes.c_double()
    H = pm.height
    targets = {(round(c.origin[0], 2), round(c.origin[1], 2)) for c in run["chars"] if not c.text.isspace()}
    for i in range(tp.count_chars()):
        R.FPDFText_GetCharOrigin(tp, i, ox, oy)
        if (round(ox.value, 2), round(H - oy.value, 2)) in targets:
            idx.append(i)
    # other characters sharing the removed objects are redrawn with their own font
    objs = {ctypes.cast(R.FPDFText_GetTextObject(tp, i), ctypes.c_void_p).value for i in idx}
    keep = []
    for i in range(tp.count_chars()):
        o = R.FPDFText_GetTextObject(tp, i)
        if o and ctypes.cast(o, ctypes.c_void_p).value in objs and i not in idx:
            keep.append(i)
    tp.close()
    removed = _remove_text_objects(page, idx, page.get_textpage())
    scale = dpi / 72.0
    bg = np.asarray(page.render(scale=scale).to_pil().convert("RGB"), dtype=float) / 255.0
    Hpx, Wpx = bg.shape[:2]
    size = run["size"]
    ppem = size * scale
    limit = right_limit_pt if right_limit_pt is not None else pm.width
    stimuli = []
    variants = {original + "|as_set": (fonts[original], run["positions_em"])}
    for label, f in fonts.items():
        variants[label + "|nominal"] = (f, None)
    word = "".join(c.text for c in run["chars"])
    orig_width = (run["chars"][-1].box[2] - run["chars"][0].box[0])
    for key, (f, pos) in variants.items():
        placed = layout_word(f, word, positions_em=pos)
        img, info = render_outline_text(f, placed, ppem, supersample=4)
        x0_em, y0_em, x1_em, y1_em = info["bbox_em"]
        left = int(round(run["x0"] * scale + x0_em * ppem))
        top = int(round(run["baseline"] * scale - y1_em * ppem))
        canvas = bg.copy()
        h, w = img.shape
        ys, xs = max(0, top), max(0, left)
        ye, xe = min(Hpx, top + h), min(Wpx, left + w)
        a = img[ys - top:ye - top, xs - left:xe - left][..., None]
        canvas[ys:ye, xs:xe] = (1 - a) * canvas[ys:ye, xs:xe] + a * np.asarray(run["fill_rgb"])[None, None, :]
        ink_cols = np.nonzero((img >= 0.5).any(0))[0]
        width_pt = (ink_cols.max() - ink_cols.min() + 1) / scale if ink_cols.size else None
        right_pt = (left + (ink_cols.max() + 1 if ink_cols.size else 0)) / scale
        sid = f"B-p{run['page'] + 1}-{_slug(word)}-{_slug(key)}"
        path = os.path.join(out_dir, sid + ".png")
        Image.fromarray((np.clip(canvas, 0, 1) * 255).astype("uint8")).save(path)
        lines_needed = 1
        if width_pt and right_pt > limit and " " in word:
            lines_needed = 2   # greedy re-wrap would break the run
        stimuli.append({"stimulus_id": sid, "file": os.path.basename(path), "sha256": _sha(path),
                        "font": key.split("|")[0], "variant": key.split("|")[1], "font_source": f.source,
                        "size_pt": size, "ink_width_pt": width_pt, "width_change_ratio":
                        (width_pt / orig_width) if (width_pt and orig_width) else None,
                        "right_edge_pt": right_pt, "exceeds_right_limit": bool(right_pt > limit),
                        "lines_after_rewrap": lines_needed, "missing_glyphs": info["missing"]})
    base = next(s for s in stimuli if s["font"] == original and s["variant"] == "as_set")
    pairs = [{"a": base["stimulus_id"], "b": s["stimulus_id"]} for s in stimuli
             if s["font"] != original and s["variant"] == "nominal"]
    man = {"experiment": "B_page", "page": run["page"] + 1, "text": word, "original_font": original,
           "created": dt.datetime.now(dt.timezone.utc).isoformat(),
           "conditions": {"dpi": dpi, "size_pt": size, "baseline_pt": run["baseline"], "x0_pt": run["x0"],
                          "removed_text_objects": removed, "other_chars_in_removed_objects": len(keep),
                          "right_limit_pt": limit, "rasteriser": "even-odd polygon fill, 4x supersampling",
                          "background": "PDFium render of the page with the target text objects removed",
                          "source_pdf_sha256": doc.sha256},
           "stimuli": stimuli, "pairs": pairs}
    if keep:
        man["warnings"] = [f"{len(keep)} other characters shared the removed text object(s) and are absent "
                           "from every variant"]
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(man, fh, ensure_ascii=False, indent=2)
    return man
