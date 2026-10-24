"""The one final MATCH spread: round-I intensity (NOCTURNE), rebuilt with contemporary-art methods.

Anchors (verified this session; they are the lineage of each method and do not prove any effect):
* Gerhard Richter, *Strip* works and *Patterns: Divided, Mirrored, Repeated* (2012).  A painting is
  digitally divided into bands, each band mirrored and repeated, then stretched into horizontal stripes.
  Here one column of the night photograph is treated the same way and fills the title.
* Thomas Ruff, *jpegs* (from 2002).  An image is compressed at the maximum rate and enlarged until the
  codec's 8×8 blocks become the picture.  Here it is the shadow copy of each of the three other places.
* Hito Steyerl, "In Defense of the Poor Image" (e-flux #10, 2009).  The copy in motion: compressed,
  ripped, passed on.  The supplied spread is a low-resolution screenshot, and the page says so in numbers.
Kept from round I: slit-scan on the river lights, the vertical title along the gutter, 세로쓰기 copy,
registration marks.
"""
from __future__ import annotations

import io
import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from ..fontpaths import find
from .artdirect import cover, grain
from .defamiliar import crop_marks, misregister, reg_mark, rotated_text, slit_scan, text_mask, vertical_ko
from .final import kr
from .photo_led import tracked
from .variants import fnt

W, H, GUT = 2000, 1231, 1000


def richter_strip(column: np.ndarray, out_w: int, out_h: int, stages: int) -> Image.Image:
    """Divide, mirror, repeat.  The column is divided into 2^stages bands.  Each band is halved and joined
    to its own mirror, so every part of the source survives as a symmetric group of stripes.  The result is
    then stretched horizontally."""
    n = 2 ** stages
    L = len(column) - len(column) % n
    seg = L // n
    bands = []
    for i in range(n):
        b = column[i * seg:(i + 1) * seg].astype(float)
        half = b[::2]
        bands.append(np.concatenate([half, half[::-1]], axis=0))
    band = np.concatenate(bands, axis=0)
    col = Image.fromarray(np.clip(band, 0, 255).astype("uint8")[:, None, :])
    return col.resize((1, out_h), Image.NEAREST).resize((out_w, out_h), Image.NEAREST)


def ruff_jpeg(img: Image.Image, factor: int = 4, quality: int = 3) -> Image.Image:
    """Shrink, compress at near-maximum rate, then enlarge with nearest neighbour, so the 8×8 blocks show."""
    small = img.resize((max(8, img.size[0] // factor), max(8, img.size[1] // factor)), Image.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=quality)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB").resize(img.size, Image.NEAREST)


def nocturne_contemporary(crops, texts):
    ink, dim, bg = (232, 228, 220), (88, 90, 90), (9, 10, 10)
    page = Image.new("RGB", (W, H), bg)
    src_w, src_h = crops["night"].size
    left, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    clean = left.copy()
    left = slit_scan(left, 620, GUT, amp=140, period=9)
    page.paste(left, (0, 0))
    # the title: the most varied column of the river lights, divided, mirrored and repeated into horizontal
    # stripes on the page, seen only through the letters
    a = np.asarray(clean).astype(float)
    lum = a.mean(axis=2)
    xs = np.arange(520, 980)
    y0 = 540                                               # the river: lights, reflections, bridge
    cx = int(xs[np.argmax(lum[y0:, 520:980].std(axis=0))])
    m = text_mask((1240, 300), texts["title"], fnt("black", 252), (0, 0), 4).rotate(90, expand=True)
    strip = richter_strip(a[y0:, cx, :], m.size[0], m.size[1], stages=5)
    page.paste(strip, (GUT + 12, H - m.size[1] + 4), m)
    d = ImageDraw.Draw(page)
    # the other three places: a clean positive over its own maximally compressed copy
    spots = (("park", 320, (1440, 110)), ("shop", 130, (1380, 430)), ("rock", 250, (1430, 810)))
    for key, w_, (x, y) in spots:
        im = crops[key]
        s = w_ / im.size[0]
        im2 = im.resize((w_, round(im.size[1] * s)), Image.LANCZOS)
        poor = ruff_jpeg(im2.resize((int(w_ * 1.18), int(im2.size[1] * 1.18)), Image.LANCZOS), factor=4, quality=3)
        page.paste(poor, (x - 34, y + 26))
        page.paste(misregister(im2, 3, 0), (x, y))
        crop_marks(d, (x, y, x + im2.size[0], y + im2.size[1]), dim)
        tracked(d, (x - 34, y + 26 + poor.size[1] + 12),
                f"{im.size[0]}×{im.size[1]} → ×{s:.2f} · JPEG Q3", fnt("mono", 11), dim, 1)
    # 세로쓰기, two columns read right to left
    fk = kr("regular", 22)
    vertical_ko(d, 1880, 440, texts["body_ko"][0], fk, ink)
    vertical_ko(d, 1838, 440, texts["body_ko"][1], fk, ink)
    rotated_text(page, (1316, 640), texts["kicker"], fnt("light", 14), ink + (255,), angle=90, tracking=6)
    reg_mark(d, 1960, 40, 10, dim)
    reg_mark(d, 1960, H - 40, 10, dim)
    tracked(d, (40, 40 - 12), texts["running_head"], fnt("mono", 12), ink, 1.2)
    tracked(d, (40, H - 66), f"SOURCE {src_w}×{src_h} → ×{info['scale']:.2f} (POOR IMAGE) · SLIT-SCAN 620–1000",
            fnt("mono", 12), ink, 1)
    tracked(d, (40, H - 44), f"STRIP: COLUMN x={cx}, y≥{y0} DIVIDED / MIRRORED / REPEATED ×5 · JPEG Q3 8×8", fnt("mono", 12),
            ink, 1)
    tracked(d, (W - 80, H - 44), texts["folio"], fnt("mono", 12), dim, 1)
    return grain(page, 0.03, 12, size=1.4), {
        "name": "MATCH. — final (NOCTURNE, contemporary)",
        "methods": {"slit-scan": "river lights only, face untouched",
                    "Richter strip": "the most varied column (x=520–980) of the night photo, 5 stages divided/mirrored/repeated, "
                                     "stretched into the title",
                    "Ruff jpeg": "each place re-compressed at JPEG quality 3 after 4× reduction, enlarged nearest",
                    "Steyerl poor image": "real source size and enlargement printed on the page"},
        "anchors": ["Richter, Patterns: Divided, Mirrored, Repeated (2012)", "Ruff, jpegs (2002–)",
                    "Steyerl, In Defense of the Poor Image (2009)"],
        "night_scale": info["scale"]}


# ======================================================================= soft dandy


def serif_kr(weight: str, size: int):
    """Noto Serif KR (OFL 1.1); falls back to Caladea / WenQuanYi when not installed."""
    path = find(f"NotoSerifKR-{weight}.otf", "notoserifkr")
    if os.path.exists(path):
        return ImageFont.truetype(path, size=size)
    return fnt("serif", size)


def matte(img: Image.Image, black: int = 22, white: int = 242) -> Image.Image:
    """Lift the black point and lower the white point (a faded, matte print)."""
    a = np.asarray(img, float)
    return Image.fromarray((black + a * (white - black) / 255).astype("uint8"))


def halation(img: Image.Image, threshold: int = 190, radius: float = 16, tint=(255, 214, 180),
             strength: float = 0.45) -> Image.Image:
    """Soft warm glow around highlights, as on film without an anti-halation layer."""
    a = np.asarray(img, float)
    lum = a.mean(axis=2)
    hi = np.clip((lum - threshold) / (255 - threshold), 0, 1)
    glow = np.asarray(Image.fromarray((hi * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(radius)), float) / 255
    out = a + strength * glow[..., None] * np.array(tint, float)
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def soft_jpeg(img: Image.Image, paper, ink, factor: int = 4) -> Image.Image:
    """Ruff's maximal compression, printed as a single soft tone between paper and ink."""
    poor = ruff_jpeg(img, factor=factor, quality=3).convert("L")
    t = np.asarray(poor, float)[..., None] / 255
    p, k = np.array(paper, float), np.array(ink, float)
    return Image.fromarray((k + (p - k) * (0.35 + 0.65 * t)).astype("uint8"))


def nocturne_dandy(crops, texts):
    paper, ink, taupe, camel = (233, 227, 216), (58, 54, 50), (170, 160, 146), (156, 128, 98)
    page = Image.new("RGB", (W, H), paper)
    src_w, src_h = crops["night"].size
    left, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    left = slit_scan(left, 640, GUT, amp=40, period=22)
    left = matte(halation(left), black=24, white=240)
    page.paste(left, (0, 0))
    # the title cut from the knit: one column of the sea-side sweater, divided, mirrored, repeated —
    # read at this size as a soft suiting stripe
    knit = np.asarray(crops["rock"]).astype(float)
    p_rock = knit.shape
    kx = int(p_rock[1] * 0.72)
    col = knit[int(p_rock[0] * 0.18):int(p_rock[0] * 0.95), kx, :]
    col = 0.55 * col + 0.45 * np.array(paper, float) * 0.86                 # softened toward the paper
    m = text_mask((1180, 300), texts["title"], serif_kr("SemiBold", 250), (0, -40), 10).rotate(90, expand=True)
    strip = richter_strip(col, m.size[0], m.size[1], stages=6)
    page.paste(strip, (GUT + 40, H - m.size[1] - 40), m)
    d = ImageDraw.Draw(page)
    # the other three places: positive prints over their own soft, maximally compressed shadow
    spots = (("park", 320, (1440, 120)), ("shop", 130, (1390, 440)), ("rock", 250, (1440, 815)))
    cap = fnt("serif_it", 15)
    for key, w_, (x, y) in spots:
        im = crops[key]
        s = w_ / im.size[0]
        im2 = matte(im.resize((w_, round(im.size[1] * s)), Image.LANCZOS), 18, 244)
        shadow = soft_jpeg(im2.resize((int(w_ * 1.16), int(im2.size[1] * 1.16)), Image.LANCZOS), paper, taupe)
        page.paste(shadow, (x - 30, y + 24))
        page.paste(im2, (x, y))
        d.rectangle([x - 1, y - 1, x + im2.size[0], y + im2.size[1]], outline=taupe, width=1)
        tracked(d, (x - 30, y + 24 + shadow.size[1] + 10), f"{im.size[0]} × {im.size[1]}, ×{s:.2f}", cap, camel, 0.3)
    # 세로쓰기 in a light serif, right to left
    fk = serif_kr("Light", 22)
    vertical_ko(d, 1880, 440, texts["body_ko"][0], fk, ink)
    vertical_ko(d, 1838, 440, texts["body_ko"][1], fk, ink)
    rotated_text(page, (1330, 600), texts["kicker"], serif_kr("Regular", 14), ink + (255,), angle=90, tracking=7)
    d = ImageDraw.Draw(page)
    tracked(d, (40, 30), texts["running_head"], serif_kr("Light", 13), (236, 230, 220), 2.4)
    it = fnt("serif_it", 16)
    tracked(d, (40, H - 70), f"Source {src_w} × {src_h}, enlarged ×{info['scale']:.2f} — a poor image, kept soft.",
            it, (226, 220, 210), 0.3)
    tracked(d, (40, H - 46), "Slit-scan on the river · halation · matte print · title cut from the knit "
            "(divided, mirrored, repeated) · JPEG shadows", it, (226, 220, 210), 0.3)
    tracked(d, (W - 76, H - 46), texts["folio"], serif_kr("Light", 14), ink, 1)
    d.line([(GUT + 40, 40), (W - 40, 40)], fill=taupe, width=1)
    return grain(page, 0.022, 12, size=1.5), {
        "name": "MATCH. — final (soft dandy)",
        "mood_intent": "soft dandy: ivory paper, warm charcoal ink, light serif, tailored stripe, matte night",
        "methods": {"slit-scan": "river lights, amp 40px", "halation": "highlights >190, blur 16px, warm tint",
                    "matte print": "black point 24, white point 240 (left page); 18/244 on the three prints",
                    "Richter strip": "column of the rock-photo knit, 6 stages divided/mirrored/repeated, "
                                     "softened 45% toward paper, poured into the serif title",
                    "Ruff jpeg": "JPEG quality 3 after 4× reduction, printed as one taupe tone",
                    "Steyerl poor image": "source size and enlargement stated on the page"},
        "fonts": ["Noto Serif KR (OFL 1.1)", "Caladea Italic (Apache 2.0)"],
        "night_scale": info["scale"]}
