"""Shared helpers for analysis modules: spec construction and per-page caches."""
from __future__ import annotations

from functools import cached_property
from typing import Optional

import numpy as np

from ..mathcore.color import gray, relative_luminance
from ..mathcore.geometry import union_area
from ..mathcore.imaging import canny, resize_max
from ..mathcore.saliency import spectral_residual
from ..pdf.model import PageModel
from ..schema import ErrorKind, MeasurementType, ParameterSpec


def spec(pid: str, name: str, module: str, *, unit: str, formula: str, definition: str = "",
         mtype: MeasurementType = MeasurementType.DIRECT, domain: str = "R", scope: str = "page",
         error: ErrorKind = ErrorKind.NONE, normalization: str = "none",
         target: str = "reference_profile (quantiles) when available; otherwise none",
         confidence: str = "deterministic given extraction", validation: str = "synthetic PDF with known answer",
         missing: str = "null when inputs are absent", notes: Optional[list[str]] = None) -> ParameterSpec:
    return ParameterSpec(parameter_id=pid, name=name, module=module, definition=definition or formula, unit=unit,
                         formula=formula, normalization=normalization, target=target, error_kind=error,
                         confidence=confidence, validation=validation, measurement_type=mtype,
                         domain=domain, missing=missing, scope=scope, notes=notes or [])


class PageContext:
    """Lazily computed per-page quantities shared by all modules."""

    def __init__(self, pm: PageModel, cfg: dict):
        self.pm = pm
        self.cfg = cfg

    @property
    def source(self) -> str:
        return "raster" if self.pm.extraction_mode == "raster" else "pdf_objects"

    @cached_property
    def gray(self) -> np.ndarray:
        return gray(self.pm.render)

    @cached_property
    def luminance(self) -> np.ndarray:
        return relative_luminance(self.pm.render)

    @cached_property
    def edges(self) -> np.ndarray:
        g, _ = resize_max(self.gray, 800)
        c = self.cfg["photography"]["canny"]
        return canny(g, c["sigma"], c["low"], c["high"])

    @cached_property
    def saliency(self) -> np.ndarray:
        g, _ = resize_max(self.gray, 400)
        return spectral_residual(g, int(self.cfg["composition"]["saliency_work_width"]))

    @cached_property
    def text_boxes(self):
        """Text area primitive: union of text *line* boxes (tight glyph extents)."""
        return [l.box for l in self.pm.lines]

    @cached_property
    def image_boxes(self):
        return [o.box for o in self.pm.objects if o.kind == "image"]

    @cached_property
    def vector_boxes(self):
        return [o.box for o in self.pm.objects if o.kind == "vector"]

    @cached_property
    def content_boxes(self):
        return self.text_boxes + self.image_boxes + self.vector_boxes

    @cached_property
    def page_box(self):
        return (0.0, 0.0, self.pm.width, self.pm.height)

    def union_fraction(self, boxes) -> float:
        return union_area(boxes, clip=self.page_box) / self.pm.area


class GlyphCache:
    """Per-document cache of glyph geometry for (font_key, char).

    Each entry combines raster features (``features_from_mask`` on the
    PDFium outline) with exact outline features (contour length ratio,
    curvature).  ``None`` marks a glyph PDFium could not provide (missing in
    the font program -> fallback/notdef at render time).
    """

    def __init__(self, doc, cfg: dict):
        self.doc = doc
        self.cfg = cfg
        self.px = int(cfg["typography"]["glyph_raster_px"])
        self.q = tuple(cfg["typography"]["stroke_quantiles"])
        self._c: dict = {}

    def get(self, font_key: str, ch: str):
        key = (font_key, ch)
        if key in self._c:
            return self._c[key]
        from ..mathcore.glyph import contour_length, curvature_samples, flatten, outline_bbox
        from ..pdf.extract import glyph_outline
        from ..typo.glyphfeat import features_from_mask, outline_mask
        f = self.doc.fonts.get(font_key)
        res = None
        if f is not None and f.handle is not None and self.doc.handle is not None:
            cont = glyph_outline(f.handle, ch)
            if cont:
                om = outline_mask(cont, self.px)
                if om is not None:
                    res = features_from_mask(om[0], om[1], om[2], self.px, self.q)
                if res is not None:
                    polys = flatten(cont)
                    x0, y0, x1, y1 = outline_bbox(polys)
                    res["outline_complexity"] = contour_length(polys) / (2 * ((x1 - x0) + (y1 - y0)))
                    cs = curvature_samples(cont, y1 - y0, corner_deg=float(
                        self.cfg["typography"]["curvature_corner_deg"]))
                    res["_curv_vals"] = cs["values"]
                    res["_curv_wts"] = cs["weights"]
                    res["corners"] = cs["corners"]
                    res["n_contours"] = len(cont)
        self._c[key] = res
        return res


class DocContext:
    def __init__(self, doc, cfg: dict):
        self.doc = doc
        self.cfg = cfg
        self.glyphs = GlyphCache(doc, cfg)
