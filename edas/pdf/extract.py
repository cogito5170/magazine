"""PDF parsing, rendering and object extraction (pipeline steps 1–4).

Backend: PDFium through pypdfium2 (text with per-glyph boxes, fonts and
glyph outlines, image/path/form objects, clip paths, rendering).  The
original file is opened read-only and is never written.

Coordinates are converted to a single top-left-origin system in points
with an affine map obtained from ``FPDF_PageToDevice`` (handles CropBox
offsets and /Rotate).
"""
from __future__ import annotations

import ctypes
import hashlib
import re
from typing import Optional

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as R

from ..mathcore.geometry import area, clip_box, intersect
from ..mathcore.imaging import to_float_rgb
from .layout_objects import build_layout_objects, build_lines_and_blocks
from .model import Char, DocumentModel, FontInfo, ImageObj, PageModel, VectorObj
from . import raster

OBJ_TEXT, OBJ_PATH, OBJ_IMAGE, OBJ_SHADING, OBJ_FORM = 1, 2, 3, 4, 5

_SUBSET = re.compile(r"^[A-Z]{6}\+")
_STYLE_TOKENS = ["extrabold", "ultrabold", "semibold", "demibold", "bold", "black", "heavy", "medium",
                 "extralight", "ultralight", "light", "thin", "hairline", "book", "regular", "roman",
                 "normal", "italic", "oblique", "condensed", "cond", "extended", "narrow", "display",
                 "text", "caption", "it", "bd", "md", "lt", "rg", "bk", "mt", "psmt", "ps"]


def split_font_name(name: str) -> tuple[str, str, str]:
    """(base_name, family, style).  Rule: strip a 6-letter subset prefix, then
    split at the first '-' or ',' ; trailing style tokens are removed from a
    name without a separator (e.g. 'HelveticaBold')."""
    base = _SUBSET.sub("", name or "unknown")
    m = re.split(r"[-,]", base, maxsplit=1)
    fam = m[0]
    style = m[1] if len(m) > 1 else ""
    low = fam.lower()
    changed = True
    while changed and not style:
        changed = False
        for t in _STYLE_TOKENS:
            if low.endswith(t) and len(low) > len(t) + 2:
                style = fam[-len(t):] + style
                fam = fam[: -len(t)]
                low = fam.lower()
                changed = True
                break
    return base, fam.strip() or base, style or "Regular"


class _Affine:
    """Maps PDF user space (y up) to top-left page points."""

    def __init__(self, page, W: float, H: float):
        K = 100.0  # sub-point precision for the integer device API
        sx, sy = int(round(W * K)), int(round(H * K))
        rot = 0
        pts = {}
        for name, (x, y) in {"o": (0.0, 0.0), "x": (1000.0, 0.0), "y": (0.0, 1000.0)}.items():
            dx, dy = ctypes.c_int(), ctypes.c_int()
            R.FPDF_PageToDevice(page, 0, 0, sx, sy, rot, ctypes.c_double(x), ctypes.c_double(y), dx, dy)
            pts[name] = np.array([dx.value / K, dy.value / K])
        self.o = pts["o"]
        self.ex = (pts["x"] - pts["o"]) / 1000.0
        self.ey = (pts["y"] - pts["o"]) / 1000.0

    def pt(self, x: float, y: float) -> tuple[float, float]:
        p = self.o + x * self.ex + y * self.ey
        return float(p[0]), float(p[1])

    def box(self, l: float, b: float, r: float, t: float) -> tuple[float, float, float, float]:
        c = np.array([self.pt(l, b), self.pt(r, b), self.pt(l, t), self.pt(r, t)])
        return float(c[:, 0].min()), float(c[:, 1].min()), float(c[:, 0].max()), float(c[:, 1].max())


def _mat(m) -> np.ndarray:
    return np.array([[m.a, m.c, m.e], [m.b, m.d, m.f], [0, 0, 1.0]])


def _transform_box(M: np.ndarray, l, b, r, t):
    c = np.array([[l, b, 1], [r, b, 1], [l, t, 1], [r, t, 1]], float) @ M.T
    return float(c[:, 0].min()), float(c[:, 1].min()), float(c[:, 0].max()), float(c[:, 1].max())


def _color(getter, obj) -> Optional[tuple[float, float, float]]:
    r, g, b, a = (ctypes.c_uint() for _ in range(4))
    if not getter(obj, r, g, b, a):
        return None
    return (r.value / 255.0, g.value / 255.0, b.value / 255.0)


class PdfExtractor:
    def __init__(self, config: dict):
        self.cfg = config

    # ------------------------------------------------------------------
    def open(self, path: str) -> DocumentModel:
        with open(path, "rb") as fh:
            data = fh.read()
        sha = hashlib.sha256(data).hexdigest()
        pdf = pdfium.PdfDocument(data)   # in-memory copy: the source file is never modified
        doc = DocumentModel(path=path, sha256=sha, pages=[], handle=pdf)
        dpi = float(self.cfg["render"]["dpi"])
        for i in range(len(pdf)):
            doc.pages.append(self._page(pdf, i, dpi, doc))
        self._apply_raster_policy(doc)
        return doc

    # ------------------------------------------------------------------
    def _page(self, pdf, index: int, dpi: float, doc: DocumentModel) -> PageModel:
        page = pdf[index]
        W, H = page.get_size()
        pm = PageModel(index=index, width=float(W), height=float(H), rotation=page.get_rotation())
        aff = _Affine(page, W, H)
        scale = dpi / 72.0
        pil = page.render(scale=scale).to_pil().convert("RGB")
        pm.render = to_float_rgb(pil)
        pm.render_scale = pm.render.shape[1] / W
        self._text(page, pm, aff, doc)
        self._objects(page, pm, aff)
        pm.background_rgb = raster.estimate_background(pm.render)
        build_lines_and_blocks(pm, self.cfg["text"])
        build_layout_objects(pm, self.cfg)
        return pm

    def _font(self, handle, doc: DocumentModel) -> Optional[str]:
        if not handle:
            return None
        buf = ctypes.create_string_buffer(512)
        n = R.FPDFFont_GetBaseFontName(handle, buf, 512)
        raw = buf.value.decode("utf-8", "replace") if n else "unknown"
        if raw in doc.fonts:
            return raw
        base, fam, style = split_font_name(raw)
        ang = ctypes.c_int()
        has_ang = R.FPDFFont_GetItalicAngle(handle, ang)
        w = R.FPDFFont_GetWeight(handle)
        doc.fonts[raw] = FontInfo(key=raw, base_name=base, family=fam, style=style,
                                  flags=int(R.FPDFFont_GetFlags(handle)),
                                  weight=int(w) if w and w > 0 else None,
                                  italic_angle=int(ang.value) if has_ang else None,
                                  embedded=bool(R.FPDFFont_GetIsEmbedded(handle) == 1), handle=handle)
        return raw

    def _text(self, page, pm: PageModel, aff: _Affine, doc: DocumentModel):
        tp = page.get_textpage()
        n = tp.count_chars()
        l, r, b, t = (ctypes.c_double() for _ in range(4))
        ox, oy = ctypes.c_double(), ctypes.c_double()
        m = R.FS_MATRIX()
        rect = R.FS_RECTF()
        cr, cg, cb, ca = (ctypes.c_uint() for _ in range(4))
        font_cache: dict[int, Optional[str]] = {}
        for i in range(n):
            code = R.FPDFText_GetUnicode(tp, i)
            try:
                ch = chr(code)
            except (ValueError, OverflowError):
                ch = "�"
            if ch in "\r\n" or code == 0:
                continue
            gen = bool(R.FPDFText_IsGenerated(tp, i) == 1)
            R.FPDFText_GetCharBox(tp, i, l, r, b, t)
            box = aff.box(l.value, b.value, r.value, t.value)
            if R.FPDFText_GetLooseCharBox(tp, i, rect):
                loose = aff.box(rect.left, rect.bottom, rect.right, rect.top)
            else:
                loose = box
            R.FPDFText_GetCharOrigin(tp, i, ox, oy)
            org = aff.pt(ox.value, oy.value)
            nominal = float(R.FPDFText_GetFontSize(tp, i))
            vscale = 1.0
            if R.FPDFText_GetMatrix(tp, i, m):
                vscale = float(np.hypot(m.c, m.d)) or 1.0
            fill = None
            if R.FPDFText_GetFillColor(tp, i, cr, cg, cb, ca):
                fill = (cr.value / 255.0, cg.value / 255.0, cb.value / 255.0)
            tobj = R.FPDFText_GetTextObject(tp, i)
            fk = None
            if tobj:
                addr = ctypes.cast(tobj, ctypes.c_void_p).value
                if addr not in font_cache:
                    font_cache[addr] = self._font(R.FPDFTextObj_GetFont(tobj), doc)
                fk = font_cache[addr]
            pm.chars.append(Char(text=ch, box=box, loose_box=loose, origin=org, size=nominal * vscale,
                                 nominal_size=nominal, font_key=fk, fill_rgb=fill, generated=gen))

    def _objects(self, page, pm: PageModel, aff: _Affine):
        W, H = pm.width, pm.height
        page_box = (0.0, 0.0, W, H)
        bg_frac = float(self.cfg["layout"]["background_area_fraction"])

        def walk(container_count, container_get, M: np.ndarray, depth: int):
            for k in range(container_count()):
                obj = container_get(k)
                typ = R.FPDFPageObj_GetType(obj)
                bl, bb, br, bt = (ctypes.c_float() for _ in range(4))
                if not R.FPDFPageObj_GetBounds(obj, bl, bb, br, bt):
                    continue
                ub = _transform_box(M, bl.value, bb.value, br.value, bt.value)
                box = aff.box(*ub)
                if typ == OBJ_FORM and depth < 8:
                    fm = R.FS_MATRIX()
                    R.FPDFPageObj_GetMatrix(obj, fm)
                    M2 = M @ _mat(fm)
                    walk(lambda o=obj: R.FPDFFormObj_CountObjects(o),
                         lambda j, o=obj: R.FPDFFormObj_GetObject(o, j), M2, depth + 1)
                elif typ == OBJ_IMAGE:
                    self._image(obj, M, box, page_box, aff, pm)
                elif typ in (OBJ_PATH, OBJ_SHADING):
                    vis = clip_box(box, W, H)
                    if vis is None:
                        continue
                    if typ == OBJ_PATH:
                        fmode, stroke = ctypes.c_int(), ctypes.c_int()
                        R.FPDFPath_GetDrawMode(obj, fmode, stroke)
                        filled, stroked = fmode.value != 0, bool(stroke.value)
                        if not filled and not stroked:
                            continue
                        fill = _color(R.FPDFPageObj_GetFillColor, obj) if filled else None
                        sc = _color(R.FPDFPageObj_GetStrokeColor, obj) if stroked else None
                    else:
                        filled, stroked, fill, sc = True, False, None, None
                    is_bg = filled and area(vis) >= bg_frac * W * H
                    pm.vectors.append(VectorObj(box=vis, filled=filled, stroked=stroked, fill_rgb=fill,
                                                stroke_rgb=sc, is_background=is_bg))

        walk(lambda: R.FPDFPage_CountObjects(page), lambda j: R.FPDFPage_GetObject(page, j),
             np.eye(3), 0)

    def _image(self, obj, M, box, page_box, aff: _Affine, pm: PageModel):
        pw, ph = ctypes.c_uint(), ctypes.c_uint()
        px = (int(pw.value), int(ph.value)) if R.FPDFImageObj_GetImagePixelSize(obj, pw, ph) else (0, 0)
        im = R.FS_MATRIX()
        R.FPDFPageObj_GetMatrix(obj, im)
        IM = M @ _mat(im)
        w_pt = float(np.hypot(IM[0, 0], IM[1, 0]))
        h_pt = float(np.hypot(IM[0, 1], IM[1, 1]))
        ppi = None
        if px[0] and w_pt > 0 and h_pt > 0:
            ppi = (px[0] / (w_pt / 72.0), px[1] / (h_pt / 72.0))
        vis = intersect(box, page_box)
        clip = R.FPDFPageObj_GetClipPath(obj)
        if clip and vis is not None:
            for k in range(R.FPDFClipPath_CountPaths(clip)):
                pts = []
                for s in range(R.FPDFClipPath_CountPathSegments(clip, k)):
                    seg = R.FPDFClipPath_GetPathSegment(clip, k, s)
                    x, y = ctypes.c_float(), ctypes.c_float()
                    if R.FPDFPathSegment_GetPoint(seg, x, y):
                        q = M @ np.array([x.value, y.value, 1.0])
                        pts.append(aff.pt(q[0], q[1]))
                if pts:
                    a = np.asarray(pts)
                    cb = (a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max())
                    vis = intersect(vis, cb) if vis else None
                    if vis is None:
                        break
        if vis is None or area(box) <= 0:
            return
        pm.images.append(ImageObj(box=vis, placed_box=box, px_size=px, effective_ppi=ppi,
                                  crop_retention=area(vis) / area(box)))

    # ------------------------------------------------------------------
    def _apply_raster_policy(self, doc: DocumentModel):
        """Switch to raster analysis when PDF objects carry no usable structure.

        Policy (config ``extraction.raster_fallback``):
        * page without any extractable object -> raster
        * 'auto': if the *whole document* has no text characters and every page
          is a single image covering >= full_page_image_fraction of the page,
          the document is treated as flattened (exported as images) -> raster.
        """
        pol = self.cfg["extraction"]["raster_fallback"]
        frac = float(self.cfg["extraction"]["full_page_image_fraction"])
        if pol == "never":
            return
        no_text = all(len(p.chars) == 0 for p in doc.pages)
        flattened = no_text and all(
            len(p.images) == 1 and area(p.images[0].box) >= frac * p.area and
            not any(not v.is_background for v in p.vectors) for p in doc.pages)
        for p in doc.pages:
            empty = not p.chars and not p.images and not [v for v in p.vectors if not v.is_background]
            if pol == "always" or empty or (pol == "auto" and flattened):
                raster.segment_page(p, self.cfg)
                p.warnings.append("raster fallback: objects estimated from rendering "
                                  f"(reason={'empty' if empty else 'flattened document' if flattened else pol})")


def open_document(path: str, config: dict) -> DocumentModel:
    return PdfExtractor(config).open(path)


def glyph_outline(font_handle, ch: str) -> Optional[list]:
    """Outline of the glyph for unicode ``ch`` from an embedded/standard font.

    Returns a list of contours with segments ("L", p0, p1) / ("C", p0, c1, c2, p3)
    in font space (y up), or None if PDFium cannot provide it.
    """
    if not font_handle:
        return None
    gp = R.FPDFFont_GetGlyphPath(font_handle, ord(ch), ctypes.c_float(1000.0))
    if not gp:
        return None
    n = R.FPDFGlyphPath_CountGlyphSegments(gp)
    contours: list[list] = []
    cur: list = []
    last = None
    start = None
    bez: list = []
    for s in range(n):
        seg = R.FPDFGlyphPath_GetGlyphPathSegment(gp, s)
        x, y = ctypes.c_float(), ctypes.c_float()
        R.FPDFPathSegment_GetPoint(seg, x, y)
        p = (float(x.value), float(y.value))
        typ = R.FPDFPathSegment_GetType(seg)
        if typ == R.FPDF_SEGMENT_MOVETO:
            if cur:
                contours.append(cur)
            cur, last, start, bez = [], p, p, []
        elif typ == R.FPDF_SEGMENT_LINETO:
            if last is not None and p != last:
                cur.append(("L", last, p))
            last = p
        elif typ == R.FPDF_SEGMENT_BEZIERTO:
            bez.append(p)
            if len(bez) == 3:
                cur.append(("C", last, bez[0], bez[1], bez[2]))
                last, bez = bez[2], []
        if R.FPDFPathSegment_GetClose(seg) and start is not None and last is not None:
            if last != start:
                cur.append(("L", last, start))
            last = start
    if cur:
        contours.append(cur)
    return contours or None
