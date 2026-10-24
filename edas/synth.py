"""Synthetic magazine-like PDFs with known ground truth (spec §15).

``make_test_pdf`` writes a document whose geometry is fully specified by the
returned ``truth`` dict, so tests can compare computed values with the
analytic answers (grid, margins, occupancies, font sizes, leading ...).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

LOREM = ("Design measures space rhythm and proportion across the spread while typography "
         "sets the voice of every page in the issue ").split()


def _photo(w: int, h: int, seed: int, kind: str = "gradient") -> Image.Image:
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w] / max(w, h)
    if kind == "gradient":
        r = 0.5 + 0.5 * np.sin(6 * x + seed)
        g = 0.5 + 0.5 * np.cos(5 * y + 2 * seed)
        b = 0.5 + 0.5 * np.sin(3 * (x + y))
        a = np.stack([r, g, b], -1) * 0.8 + 0.2 * rng.random((h, w, 3))
    else:  # subject: bright disc on dark background
        cx, cy = 0.35, 0.4
        d = np.hypot(x * max(w, h) / w - cx, y * max(w, h) / h - cy)
        a = np.where((d < 0.2)[..., None], [0.95, 0.85, 0.3], [0.08, 0.1, 0.15]) + 0.02 * rng.random((h, w, 3))
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))


def _text_block(c, x, y_top, width, size, leading, font, n_lines, seed):
    """Left-aligned text block; returns its baseline list in top-left coordinates."""
    rng = np.random.default_rng(seed)
    c.setFont(font, size)
    H = c._pagesize[1]
    baselines = []
    for i in range(n_lines):
        words, line = list(LOREM), ""
        rng.shuffle(words)
        for wd in words:
            cand = (line + " " + wd).strip()
            if c.stringWidth(cand, font, size) > width:
                break
            line = cand
        by = y_top + size * 0.8 + i * leading     # top-left baseline
        c.drawString(x, H - by, line)
        baselines.append(by)
    return baselines


def make_test_pdf(path: str, pages: int = 4, W: float = 600.0, H: float = 800.0,
                  seed: int = 7) -> dict:
    ml, mr, mt, mb, gutter, ncol = 50.0, 50.0, 60.0, 60.0, 20.0, 3
    col = (W - ml - mr - (ncol - 1) * gutter) / ncol
    starts = [ml + k * (col + gutter) for k in range(ncol)]
    c = canvas.Canvas(path, pagesize=(W, H))
    truth = {"W": W, "H": H, "grid": {"n": ncol, "c": col, "g": gutter, "m_l": ml, "m_r": mr},
             "margins": {"m_t": mt, "m_b": mb}, "pages": []}
    for p in range(pages):
        pg: dict = {"images": [], "text_blocks": [], "rects": []}
        # heading over column 1..2
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Times-Bold", 30)
        c.drawString(starts[0], H - (mt + 24), f"Issue {p + 1} Feature")
        pg["heading"] = {"size": 30.0, "font": "Times-Bold", "x": starts[0], "baseline": mt + 24}
        y_text = mt + 50
        if p % 2 == 0:
            # image spans columns 2-3, body text in column 1
            img_box = (starts[1], mt + 50, starts[2] + col, mt + 50 + 300)
            bl = _text_block(c, starts[0], y_text, col, 10, 14, "Helvetica", 30, seed + p)
            pg["text_blocks"].append({"x": starts[0], "size": 10.0, "leading": 14.0, "baselines": bl})
        else:
            # full column image in col 1, two text columns
            img_box = (starts[0], mt + 50, starts[0] + col, mt + 50 + 200)
            for k in (1, 2):
                bl = _text_block(c, starts[k], y_text, col, 10, 14, "Helvetica", 40, seed + 10 * p + k)
                pg["text_blocks"].append({"x": starts[k], "size": 10.0, "leading": 14.0, "baselines": bl})
        iw, ih = int(img_box[2] - img_box[0]) * 2, int(img_box[3] - img_box[1]) * 2
        c.drawImage(ImageReader(_photo(iw, ih, seed + p, "subject" if p % 2 else "gradient")),
                    img_box[0], H - img_box[3], width=img_box[2] - img_box[0], height=img_box[3] - img_box[1])
        pg["images"].append({"box": img_box, "px": (iw, ih),
                             "ppi": iw / ((img_box[2] - img_box[0]) / 72.0)})
        # coloured rule at the bottom margin
        rb = (ml, H - mb - 4, W - mr, H - mb)
        c.setFillColorRGB(0.8, 0.1, 0.1)
        c.rect(rb[0], H - rb[3], rb[2] - rb[0], rb[3] - rb[1], fill=1, stroke=0)
        pg["rects"].append({"box": rb})
        truth["pages"].append(pg)
        c.showPage()
    c.save()
    return truth


def make_blank_pdf(path: str, W: float = 400, H: float = 400) -> None:
    c = canvas.Canvas(path, pagesize=(W, H))
    c.showPage()
    c.save()


def make_flattened_pdf(path: str, src_rgb: np.ndarray, W: float = 600, H: float = 800) -> None:
    """A PDF whose only content is one full-page image (exported-as-image portfolio)."""
    c = canvas.Canvas(path, pagesize=(W, H))
    c.drawImage(ImageReader(Image.fromarray((src_rgb * 255).astype("uint8"))), 0, 0, width=W, height=H)
    c.showPage()
    c.save()
