"""Extracted document model.  All coordinates: PDF points, top-left origin."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from ..mathcore.geometry import Box


@dataclass
class FontInfo:
    key: str                 # unique per document: base name as stored in the PDF
    base_name: str           # without subset prefix
    family: str              # normalised family (style suffixes removed)
    style: str               # style suffix, e.g. Bold, Italic, Regular
    flags: int = 0
    weight: Optional[int] = None
    italic_angle: Optional[int] = None
    embedded: Optional[bool] = None
    handle: Any = None       # pdfium FPDF_FONT, valid while the document is open


@dataclass
class Char:
    text: str
    box: Box                 # tight glyph box
    loose_box: Box           # advance/ascent-descent box
    origin: tuple[float, float]   # baseline origin (top-left coordinates)
    size: float              # effective size (pt) = nominal size x vertical CTM scale
    nominal_size: float
    font_key: Optional[str]
    fill_rgb: Optional[tuple[float, float, float]]
    generated: bool = False  # synthetic space inserted by the text extractor


@dataclass
class TextLine:
    chars: list[Char]
    box: Box
    baseline: float
    size: float
    font_key: Optional[str]
    text: str


@dataclass
class TextBlock:
    lines: list[TextLine]
    box: Box
    size: float              # char-count weighted median size


@dataclass
class ImageObj:
    box: Box                 # visible box (placement ∩ clip ∩ page)
    placed_box: Box          # full placement box of the image
    px_size: tuple[int, int]
    effective_ppi: Optional[tuple[float, float]]
    crop_retention: Optional[float]
    bitmap: Optional[np.ndarray] = None   # native pixels (optional)


@dataclass
class VectorObj:
    box: Box
    filled: bool
    stroked: bool
    fill_rgb: Optional[tuple[float, float, float]]
    stroke_rgb: Optional[tuple[float, float, float]]
    is_background: bool = False


@dataclass
class LayoutObject:
    id: str
    kind: str                # text | image | vector
    box: Box
    bleed: bool = False
    locked: bool = False
    source: str = "pdf_objects"   # or raster
    meta: dict = field(default_factory=dict)

    @property
    def w(self) -> float:
        return self.box[2] - self.box[0]

    @property
    def h(self) -> float:
        return self.box[3] - self.box[1]


@dataclass
class PageModel:
    index: int
    width: float
    height: float
    rotation: int = 0
    unit: str = "pt"
    chars: list[Char] = field(default_factory=list)
    lines: list[TextLine] = field(default_factory=list)
    blocks: list[TextBlock] = field(default_factory=list)
    images: list[ImageObj] = field(default_factory=list)
    vectors: list[VectorObj] = field(default_factory=list)
    objects: list[LayoutObject] = field(default_factory=list)
    render: Optional[np.ndarray] = None       # HxWx3 float [0,1]
    render_scale: float = 1.0                 # pixels per point
    background_rgb: Optional[tuple[float, float, float]] = None
    extraction_mode: str = "pdf_objects"      # pdf_objects | raster
    raster: Optional[dict] = None             # raster segmentation by-products (lines, fg mask, glyphs)
    warnings: list[str] = field(default_factory=list)

    @property
    def area(self) -> float:
        return self.width * self.height

    def objects_of(self, kind: str) -> list[LayoutObject]:
        return [o for o in self.objects if o.kind == kind]

    def to_px(self, b: Box) -> tuple[int, int, int, int]:
        s = self.render_scale
        H, W = self.render.shape[:2]
        return (int(np.clip(np.floor(b[0] * s), 0, W)), int(np.clip(np.floor(b[1] * s), 0, H)),
                int(np.clip(np.ceil(b[2] * s), 0, W)), int(np.clip(np.ceil(b[3] * s), 0, H)))

    def crop(self, b: Box) -> Optional[np.ndarray]:
        if self.render is None:
            return None
        x0, y0, x1, y1 = self.to_px(b)
        if x1 <= x0 or y1 <= y0:
            return None
        return self.render[y0:y1, x0:x1]


@dataclass
class DocumentModel:
    path: str
    sha256: str
    pages: list[PageModel]
    fonts: dict[str, FontInfo] = field(default_factory=dict)
    handle: Any = None        # open pdfium document (needed for glyph outlines)
    warnings: list[str] = field(default_factory=list)

    def close(self):
        if self.handle is not None:
            try:
                self.handle.close()
            except Exception:
                pass
            self.handle = None
