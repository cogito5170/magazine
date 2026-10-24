"""Defamiliarised (낯설게 하기) treatments built on the art-directed concepts.

Contemporary editorial techniques, combined per spread under one ink colour
and one type system so that complexity stays coherent:
  slit-scan displacement · stagger/offset panels · chromatic misregistration
  · ordered dither · halftone · image clipped into letterforms · outline type
  · rotated / vertical (세로쓰기) type · type on a wave · weaving
  · crop & registration marks · construction lines · process annotations.
Annotations only print real process values (crop windows, enlargement
factors), never invented data.  The photographs are the only imagery.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

from .artdirect import cover, grain, scrim
from .photo_led import tracked
from .variants import fnt, width

W, H, GUT = 2000, 1231, 1000


# ------------------------------------------------------------------ techniques
def slit_scan(img: Image.Image, x0: int, x1: int, amp: float, period: float, slit: int = 6) -> Image.Image:
    a = np.asarray(img).copy()
    for i, x in enumerate(range(x0, x1, slit)):
        t = (x - x0) / max(1, x1 - x0)
        dy = int(amp * t ** 1.5 * np.sin(2 * np.pi * i / period))
        idx = np.clip(np.arange(a.shape[0]) - dy, 0, a.shape[0] - 1)      # edge-clamped shift (no wrap-around)
        a[:, x:x + slit] = a[idx, x:x + slit]
    return Image.fromarray(a)


BAYER8 = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38],
                   [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                   [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64.0


def dither(img: Image.Image, ink, paper, cell: int = 2) -> Image.Image:
    g = np.asarray(img.convert("L"), float) / 255
    h, w = g.shape
    small = np.asarray(Image.fromarray((g * 255).astype("uint8")).resize((w // cell, h // cell), Image.BILINEAR), float) / 255
    th = np.tile(BAYER8, (small.shape[0] // 8 + 1, small.shape[1] // 8 + 1))[:small.shape[0], :small.shape[1]]
    m = small > th
    out = np.where(m[..., None], np.asarray(paper), np.asarray(ink)).astype("uint8")
    return Image.fromarray(out).resize((w, h), Image.NEAREST)


def halftone(img: Image.Image, cell: int, ink, paper) -> Image.Image:
    g = np.asarray(img.convert("L"), float) / 255
    h, w = g.shape
    out = Image.new("RGB", (w, h), paper)
    d = ImageDraw.Draw(out)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            v = 1 - g[y:y + cell, x:x + cell].mean()
            r = 0.5 * cell * 1.25 * np.sqrt(v)
            if r > 0.4:
                cx, cy = x + cell / 2, y + cell / 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink)
    return out


def misregister(img: Image.Image, dx: int, dy: int) -> Image.Image:
    r, g, b = img.split()
    return Image.merge("RGB", (ImageChops.offset(r, dx, dy), g, ImageChops.offset(b, -dx, -dy)))


def text_mask(size, text, font, xy, tracking=0.0) -> Image.Image:
    m = Image.new("L", size, 0)
    tracked(ImageDraw.Draw(m), xy, text, font, 255, tracking)
    return m


def outline(d, xy, text, font, color, stroke=2, tracking=0.0, bg=(0, 0, 0)):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=bg, stroke_width=stroke, stroke_fill=color)
        x += font.getlength(ch) + tracking


def rotated_text(page, xy, text, font, fill, angle=90, tracking=0.0):
    wd = int(width(text, font, tracking)) + 20
    hd = int(font.size * 1.4)
    t = Image.new("RGBA", (wd, hd), (0, 0, 0, 0))
    tracked(ImageDraw.Draw(t), (0, 0), text, font, fill, tracking)
    t = t.rotate(angle, expand=True)
    page.paste(t, xy, t)


def vertical_ko(d, x, y, text, font, fill, lead=1.15):
    """세로쓰기: one syllable per row, columns right-to-left are the caller's job."""
    yy = y
    for ch in text:
        if ch == " ":
            yy += int(font.size * 0.5)
            continue
        if ch in ",.":
            d.text((x + font.size * 0.55, yy - font.size * 0.45), ch, font=font, fill=fill)
            yy += int(font.size * 0.4)
            continue
        d.text((x, yy), ch, font=font, fill=fill)
        yy += int(font.size * lead)
    return yy


def wave_text(page, x0, y0, text, font, fill, amp, period, tracking=0.0):
    x = x0
    for ch in text:
        cw = font.getlength(ch)
        cx = x + cw / 2
        y = y0 + amp * np.sin(2 * np.pi * cx / period)
        ang = -np.degrees(np.arctan(amp * 2 * np.pi / period * np.cos(2 * np.pi * cx / period)))
        g = Image.new("RGBA", (int(cw) + 20, int(font.size * 1.5)), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((10, 0), ch, font=font, fill=fill)
        g = g.rotate(ang, expand=True, resample=Image.BICUBIC)
        page.paste(g, (int(cx - g.size[0] / 2), int(y)), g)
        x += cw + tracking


def crop_marks(d, box, color, L=26, gap=8):
    x0, y0, x1, y1 = box
    for (x, y, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x0, y1, -1, 1), (x1, y1, 1, 1)):
        d.line([(x + sx * gap, y), (x + sx * (gap + L), y)], fill=color, width=1)
        d.line([(x, y + sy * gap), (x, y + sy * (gap + L))], fill=color, width=1)


def reg_mark(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=1)
    d.line([(cx - 1.6 * r, cy), (cx + 1.6 * r, cy)], fill=color, width=1)
    d.line([(cx, cy - 1.6 * r), (cx, cy + 1.6 * r)], fill=color, width=1)


def weave(a: Image.Image, b: Image.Image, band: int, horizontal=True) -> Image.Image:
    A, B = np.asarray(a), np.asarray(b)
    out = A.copy()
    n = (A.shape[0] if horizontal else A.shape[1]) // band
    for i in range(1, n, 2):
        if horizontal:
            out[i * band:(i + 1) * band] = B[i * band:(i + 1) * band]
        else:
            out[:, i * band:(i + 1) * band] = B[:, i * band:(i + 1) * band]
    return Image.fromarray(out)


# ------------------------------------------------------------------ 1. NOCTURNE — 잔상
def nocturne_x(crops, texts):
    ink = (232, 228, 220)
    dim = (70, 72, 72)
    page = Image.new("RGB", (W, H), (9, 10, 10))
    left, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    left = slit_scan(left, 620, GUT, amp=140, period=9)          # the river lights smear into an afterimage
    page.paste(left, (0, 0))
    d = ImageDraw.Draw(page)
    # the three other places: dithered negatives, each paired with a misregistered positive
    spots = (("park", 300, (1430, 120)), ("shop", 110, (1360, 470)), ("rock", 240, (1420, 720)))
    for key, w_, (x, y) in spots:
        im = crops[key]
        s = w_ / im.size[0]
        im2 = im.resize((w_, round(im.size[1] * s)), Image.LANCZOS)
        neg = dither(ImageChops.invert(im2), ink=(9, 10, 10), paper=(118, 120, 118), cell=2)
        page.paste(neg, (x - 26, y + 22))
        page.paste(misregister(im2, 3, 0), (x, y))
        crop_marks(d, (x, y, x + im2.size[0], y + im2.size[1]), dim)
        tracked(d, (x, y + im2.size[1] + 14), f"x{s:.2f}", fnt("mono", 12), dim, 1)
    # outline title running up the gutter
    rot = Image.new("RGBA", (1300, 260), (0, 0, 0, 0))
    outline(ImageDraw.Draw(rot), (0, 0), texts["title"], fnt("black", 220), (58, 60, 60), stroke=2, tracking=6,
            bg=(9, 10, 10))
    rot = rot.rotate(90, expand=True)
    page.paste(rot, (GUT + 20, 0), rot)
    # 세로쓰기 copy, two columns read right-to-left
    fk = fnt("ko", 22)
    vertical_ko(d, 1880, 760 - 300, texts["body_ko"][0], fk, ink)
    vertical_ko(d, 1840, 760 - 300, texts["body_ko"][1], fk, ink)
    rotated_text(page, (1300, 640), texts["kicker"], fnt("light", 14), ink + (255,), angle=90, tracking=6)
    reg_mark(d, 1960, 40, 10, dim)
    reg_mark(d, 1960, H - 40, 10, dim)
    tracked(d, (40, H - 44), f"SLIT-SCAN 620–1000 PX · NIGHT x{info['scale']:.2f}", fnt("mono", 12), ink, 1)
    tracked(d, (W - 80, H - 44), texts["folio"], fnt("mono", 12), dim, 1)
    return grain(page, 0.03, 12, size=1.4), {
        "name": "NOCTURNE — 잔상", "techniques": ["slit-scan (river lights only, face untouched)",
        "dithered negatives + misregistered positives", "outline title rotated along the gutter",
        "Korean vertical setting (세로쓰기)", "crop/registration marks", "process annotations (real scale factors)"]}


# ------------------------------------------------------------------ 2. LINEUP — 어긋남
def lineup_x(crops, texts):
    ink = (238, 236, 230)
    page = Image.new("RGB", (W, H), (7, 7, 7))
    pw = W // 4
    focus = {"night": (0.43, 0.55), "park": (0.73, 0.5), "shop": (0.42, 0.5), "rock": (0.56, 0.45)}
    offs = [0, -70, 54, -26]                                      # each body slips out of line
    order = ["night", "park", "shop", "rock"]
    d = ImageDraw.Draw(page)
    for i, k in enumerate(order):
        im, info = cover(crops[k], (pw - 6, H), focus=focus[k])
        if k == "rock":
            im = im.transpose(Image.FLIP_LEFT_RIGHT)              # the only mirrored body
        if i in (1, 2):
            im = misregister(im, 4 if i == 1 else -4, 0)
        page.paste(im, (i * pw + 3, offs[i]))
    # the word MATCH broken by the same offsets: it only 'matches' if the bodies line up again
    ft = fnt("thin", 260)
    letters = list(texts["title"])
    total = width(texts["title"], ft, 34)
    x = (W - total) / 2
    for ch in letters:
        cx = x + ft.getlength(ch) / 2
        panel = min(3, int(cx // pw))
        tracked(d, (x, 470 + offs[panel]), ch, ft, ink, 0)
        x += ft.getlength(ch) + 34
    # outline numerals, oversized, sitting behind the top edge
    for i in range(4):
        outline(d, (i * pw + 24, -60 + offs[i]), f"0{i + 1}", fnt("black", 200), ink, stroke=1, bg=(0, 0, 0))
    # copy turned 90°, running along the panel seams
    rotated_text(page, (pw - 40, 700), texts["body_ko"][0], fnt("ko", 17), ink + (255,), angle=90, tracking=0.6)
    rotated_text(page, (3 * pw - 40, 640), texts["body_ko"][1], fnt("ko", 17), ink + (255,), angle=90, tracking=0.6)
    tracked(d, (26, H - 44), f"{texts['kicker']}   OFFSETS {offs[0]} / {offs[1]} / {offs[2]} / {offs[3]} PX",
            fnt("mono", 12), ink, 1)
    tracked(d, (W - 60, H - 44), texts["folio"], fnt("mono", 12), ink, 1)
    page = scrim(page, (0, H - 120, W, H), 0.45)
    d = ImageDraw.Draw(page)
    tracked(d, (26, H - 44), f"{texts['kicker']}   OFFSETS {offs[0]} / {offs[1]} / {offs[2]} / {offs[3]} PX",
            fnt("mono", 12), ink, 1)
    tracked(d, (W - 60, H - 44), texts["folio"], fnt("mono", 12), ink, 1)
    return grain(page, 0.04, 22, size=1.6), {
        "name": "LINEUP — 어긋남", "techniques": ["staggered panels", "the title broken by the same offsets",
        "one mirrored body", "chromatic misregistration on two panels", "outline numerals cut by the edge",
        "type rotated along seams", "process annotation (real offsets)"]}


# ------------------------------------------------------------------ 3. WILD — 균열
def wild_x(crops, texts):
    bone = (236, 232, 222)
    rock, info = cover(crops["rock"], (W, H), focus=(0.5, 0.48))
    # left third dissolves into a halftone of itself; the transition is a hard diagonal tear
    ht = halftone(rock, 14, ink=(16, 22, 30), paper=(214, 210, 198))
    yy, xx = np.mgrid[0:H, 0:W]
    tear = xx < (560 + 0.35 * (H - yy) + 18 * np.sin(yy / 23.0))
    page = Image.fromarray(np.where(tear[..., None], np.asarray(ht), np.asarray(rock)))
    # the night is poured into the letterforms: one place seen through another
    ft = fnt("black", 520)
    band, _ = cover(crops["night"], (W, 420), focus=(0.5, 0.64))          # river lights + coat
    night = Image.new("RGB", (W, H))
    night.paste(band, (0, 0))
    m = text_mask((W, H), texts["title"].rstrip("."), ft, (-48, -150), -14)
    page = Image.composite(night, page, m)
    d = ImageDraw.Draw(page)
    # film strip with sprocket holes on the right edge, carrying the other two places
    sx = W - 210
    d.rectangle([sx, 0, W, H], fill=(12, 12, 12))
    for y in range(18, H, 46):
        d.rounded_rectangle([sx + 12, y, sx + 30, y + 22], 4, fill=(60, 58, 54))
        d.rounded_rectangle([W - 30, y, W - 12, y + 22], 4, fill=(60, 58, 54))
    y = 120
    for k in ("park", "shop"):
        im = crops[k]
        s = 130 / im.size[0]
        im2 = im.resize((130, round(im.size[1] * s)), Image.LANCZOS)
        page.paste(im2, (sx + 40, y))
        tracked(d, (sx + 40, y + im2.size[1] + 10), f"x{s:.2f}", fnt("mono", 11), (150, 146, 138), 1)
        y += im2.size[1] + 70
    page = scrim(page, (560, H - 260, sx, H), 0.6)
    d = ImageDraw.Draw(page)
    fk = fnt("ko", 20)
    tracked(d, (760, H - 120), texts["body_ko"][0], fk, bone, 0.6)
    tracked(d, (760, H - 86), texts["body_ko"][1], fk, bone, 0.6)
    rotated_text(page, (sx - 46, 480), texts["kicker"], fnt("bold", 15), bone + (255,), angle=-90, tracking=5)
    tracked(d, (40, H - 44), f"HALFTONE 14 PX · ROCK x{info['scale']:.2f} · NIGHT INSIDE THE LETTERS",
            fnt("mono", 12), (20, 24, 30), 1)
    tracked(d, (sx - 60, H - 44), texts["folio"], fnt("mono", 12), bone, 1)
    return grain(page, 0.045, 32, size=1.8), {
        "name": "WILD — 균열", "techniques": ["halftone dissolve behind a torn diagonal", "night photo clipped into the "
        "letterforms (one place seen through another)", "film strip with sprocket holes", "rotated kicker",
        "process annotation (real factors)"]}


# ------------------------------------------------------------------ 4. FABRIC — 직조
def fabric_x(crops, texts, photos):
    ink = (240, 238, 232)
    pw = W // 4
    byk = {p.key: p for p in photos}
    fields = []
    for k in ["night", "park", "shop", "rock"]:
        p = byk[k]
        cx0, cy0 = p.crop[0], p.crop[1]
        px0, _, px1, _ = p.person
        win = (max(0, max(px0, cx0) - cx0), max(0, p.outfit[1] - 40 - cy0), min(crops[k].size[0], px1 - cx0),
               crops[k].size[1])
        im, _ = cover(crops[k].crop(win), (pw, H))
        fields.append(im)
    base = Image.new("RGB", (W, H))
    for i, f in enumerate(fields):
        base.paste(f, (i * pw, 0))
    # weave: every second horizontal band is taken from the neighbouring garment
    shifted = Image.new("RGB", (W, H))
    for i, f in enumerate(fields):
        shifted.paste(fields[(i + 1) % 4], (i * pw, 0))
    page = weave(base, shifted, band=52, horizontal=True)
    # one field dithered: cloth turned into its own print
    sub = page.crop((2 * pw, 0, 3 * pw, H))
    page.paste(dither(sub, ink=(10, 14, 20), paper=(120, 128, 138), cell=3), (2 * pw, 0))
    a = np.asarray(page, float)
    a[:, W - 150:W - 40] *= 0.42                                           # quiet column for 세로쓰기
    page = Image.fromarray(a.astype("uint8"))
    d = ImageDraw.Draw(page)
    # construction lines: the weave grid
    for y in range(0, H, 104):
        d.line([(0, y), (W, y)], fill=(255, 255, 255), width=1)
    # title travels on a wave across all four cloths
    wave_text(page, 120, 520, texts["title"], fnt("thin", 210), ink + (255,), amp=46, period=900, tracking=40)
    fk = fnt("ko", 20)
    vertical_ko(d, W - 70, 120, texts["body_ko"][0], fk, ink)
    vertical_ko(d, W - 110, 120, texts["body_ko"][1], fk, ink)
    for i, wd in enumerate(["NIGHT", "DUSK", "DAY", "SEA"]):
        tracked(d, (i * pw + 26, H - 60), wd, fnt("light", 14), ink, 5)
    tracked(d, (26, 26), "WEAVE 52 PX · BAND n FROM GARMENT n+1", fnt("mono", 12), ink, 1)
    return grain(page, 0.045, 42, size=2.0), {
        "name": "FABRIC — 직조", "techniques": ["garments woven band by band (outfit n with outfit n+1)",
        "one field dithered", "weave construction lines", "title on a wave", "Korean vertical setting",
        "process annotation"]}


def render(src_path, photos, texts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    inset = 3
    crops = {p.key: srcim.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
             for p in photos}
    out = {}
    for k, fn in (("1_nocturne_x", nocturne_x), ("2_lineup_x", lineup_x), ("3_wild_x", wild_x), ("4_fabric_x", fabric_x)):
        page, spec = fn(crops, texts, photos) if k == "4_fabric_x" else fn(crops, texts)
        path = os.path.join(out_dir, f"{k}.png")
        page.save(path, optimize=True)
        page.save(os.path.join(out_dir, f"{k}.pdf"), "PDF", resolution=144.0)
        spec["file"] = path
        out[k] = spec
    return out
