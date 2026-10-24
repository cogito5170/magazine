"""Uniform vector-outline access for PDF fonts and installed font files.

All glyph measurements and all counterfactual specimens go through the same
path: Unicode -> PDFium glyph outline (em units) -> one anti-aliased polygon
rasteriser.  This keeps rendering conditions identical between the
original font and its alternatives.

* ``PdfFontOutlines``  – the font program embedded in the analysed PDF.
* ``FileFontOutlines`` – an installed TrueType/TTC font, embedded into a
  temporary in-memory PDF with reportlab so that PDFium reads the real
  outlines (no substitution).  CFF-flavoured OpenType files cannot take this
  route; they are reported as unsupported instead of being approximated.
"""
from __future__ import annotations

import ctypes
import io
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

import pypdfium2 as pdfium
import pypdfium2.raw as R

from ..mathcore.glyph import flatten
from ..pdf.extract import glyph_outline


class OutlineFont:
    name: str = "?"
    source: str = "?"

    def contours(self, ch: str):
        raise NotImplementedError

    def advance(self, ch: str) -> Optional[float]:
        raise NotImplementedError


class PdfFontOutlines(OutlineFont):
    def __init__(self, handle, name: str):
        self.h = handle
        self.name = name
        self.source = "pdf_embedded"
        self._c: dict = {}

    def contours(self, ch):
        if ch not in self._c:
            self._c[ch] = glyph_outline(self.h, ch)
        return self._c[ch]

    def advance(self, ch):
        w = ctypes.c_float()
        if R.FPDFFont_GetGlyphWidth(self.h, ord(ch), ctypes.c_float(1.0), w):
            return float(w.value)
        return None


class UnsupportedFont(Exception):
    pass


class FileFontOutlines(OutlineFont):
    """Embed ``chars`` of a TrueType font file into a temporary PDF and read outlines."""

    _seq = 0

    def __init__(self, path: str, index: int = 0, chars: str = "", name: Optional[str] = None):
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont, TTFError
        from reportlab.pdfgen import canvas
        FileFontOutlines._seq += 1
        rl_name = f"EDASCand{FileFontOutlines._seq}"
        try:
            pdfmetrics.registerFont(TTFont(rl_name, path, subfontIndex=index))
        except (TTFError, Exception) as e:  # noqa: BLE001 - reportlab raises several types
            raise UnsupportedFont(f"{path}#{index}: {e}") from e
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(600, 600))
        c.setFont(rl_name, 10)
        uniq = "".join(sorted(set(ch for ch in chars if not ch.isspace())))
        for k in range(0, max(len(uniq), 1), 80):
            c.drawString(5, 590 - (k // 80) * 12, uniq[k:k + 80] or "H")
        c.showPage()
        c.save()
        self.pdf = pdfium.PdfDocument(buf.getvalue())
        self.page = self.pdf[0]
        self.tp = self.page.get_textpage()
        self.h = None
        if self.tp.count_chars():
            self.h = R.FPDFTextObj_GetFont(R.FPDFText_GetTextObject(self.tp, 0))
        if not self.h:
            raise UnsupportedFont(f"{path}#{index}: no font object")
        self.name = name or f"{path}#{index}"
        self.path, self.index = path, index
        self.source = "file_via_pdf_embedding"
        self.chars = set(uniq)
        self._c: dict = {}

    def contours(self, ch):
        if ch not in self.chars:
            return None   # not embedded in the probe document -> not measured
        if ch not in self._c:
            self._c[ch] = glyph_outline(self.h, ch)
        return self._c[ch]

    def advance(self, ch):
        if ch not in self.chars and not ch.isspace():
            return None
        w = ctypes.c_float()
        if R.FPDFFont_GetGlyphWidth(self.h, ord(ch), ctypes.c_float(1.0), w):
            return float(w.value)
        return None


def layout_word(font: OutlineFont, text: str, tracking_em: float = 0.0,
                positions_em: Optional[list[float]] = None) -> list[tuple[str, float]]:
    """Pen x positions (em) per character: nominal advances (no kerning) unless
    explicit positions are given (e.g. the as-set positions from the PDF)."""
    if positions_em is not None:
        return list(zip(text, positions_em))
    x, out = 0.0, []
    for ch in text:
        out.append((ch, x))
        a = font.advance(ch)
        x += (a if a is not None else 0.5) + tracking_em
    return out


def render_outline_text(font: OutlineFont, placed: list[tuple[str, float]], px_per_em: float,
                        supersample: int = 4, pad_em: float = 0.15,
                        bbox_em: Optional[tuple[float, float, float, float]] = None) -> tuple[np.ndarray, dict]:
    """Anti-aliased coverage image (float [0,1], 1 = ink) of glyph outlines placed
    at pen positions (em, baseline y=0).  Returns (image, geometry info)."""
    polys_all = []
    missing = []
    for ch, x in placed:
        if ch.isspace():
            continue
        c = font.contours(ch)
        if not c:
            missing.append(ch)
            continue
        for p in flatten(c):
            polys_all.append(p + np.array([x, 0.0]))
    if not polys_all:
        return np.zeros((4, 4)), {"missing": missing}
    allp = np.concatenate(polys_all)
    if bbox_em is not None:
        x0, y0, x1, y1 = bbox_em
    else:
        x0, y0 = allp[:, 0].min() - pad_em, min(allp[:, 1].min(), 0.0) - pad_em
        x1, y1 = allp[:, 0].max() + pad_em, max(allp[:, 1].max(), 0.0) + pad_em
    s = px_per_em * supersample
    W, H = int(np.ceil((x1 - x0) * s)), int(np.ceil((y1 - y0) * s))
    mask = np.zeros((H, W), dtype=bool)
    for p in polys_all:
        im = Image.new("1", (W, H), 0)
        ImageDraw.Draw(im).polygon([((x - x0) * s, (y1 - y) * s) for x, y in p], fill=1)
        mask ^= np.asarray(im, dtype=bool)
    Hs, Ws = H // supersample, W // supersample
    cov = mask[:Hs * supersample, :Ws * supersample].reshape(Hs, supersample, Ws, supersample).mean((1, 3))
    return cov, {"origin_px": (-x0 * px_per_em, y1 * px_per_em), "px_per_em": px_per_em,
                 "missing": missing, "bbox_em": (x0, y0, x1, y1), "supersample": supersample}
