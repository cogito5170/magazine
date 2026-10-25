"""nogrid -- David Carson's Ray Gun pages: no grid.  One photo cropped to the person and blown up about 3× so
it bleeds over the gutter, printed off register; the title broken into its letters at five sizes and baselines,
their weight stepped 100 → 900 and filled with a Richter strip of the photo pulled toward the accent colour; the
other photos cut to slivers whose edges are pixel-stretched; the copy set once, plainly, so it can be read.
Recipe: misregister, pixel stretch, matte; size notes; final frame."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..defamiliar import text_mask
from ..defamiliar2 import pixel_stretch
from ..moodmachine import Layer
from ..variants import fnt
from ._common import W, set_copy
from .recipe import INTER, Recipe, finish

LETTERS = [(560, (30, 60)), (200, (420, 470)), (380, (40, 560)), (170, (430, 880)), (360, (0, 0)), (130, (0, 0))]


def render(crops, texts, L: Layer, persons, H=1231):
    R = Recipe()
    key = "park" if crops["park"].size[0] >= 600 else max(crops, key=lambda k: crops[k].size[0] * crops[k].size[1])
    page = Image.new("RGB", (W, H), L.paper)
    img, pb = crops[key], persons[key]
    wx0, wx1 = max(0, pb[0] - 60), min(img.size[0], pb[2] + 60)
    win = img.crop((wx0, 0, wx1, img.size[1]))
    s = (H + 20) / win.size[1]
    hero = win.resize((round(win.size[0] * s), H + 20), Image.LANCZOS)
    hero = R.misreg(R.hero(hero, glow=False), 6)
    hx = 1000 - int(hero.size[0] * 0.45)
    page.paste(hero, (hx, -10))
    photos = [(hx, 0, hx + hero.size[0], H)]
    right = hx + hero.size[0]
    rng = np.random.default_rng(21)
    others = [k for k in ("night", "shop", "rock", "park") if k != key][:3]
    x = right + 36
    d = ImageDraw.Draw(page)
    for i, k in enumerate(others):
        im, q = crops[k], persons[k]
        sw = max(24, int((q[2] - q[0]) * 0.4))
        cx = (q[0] + q[2]) // 2
        sl = im.crop((max(0, cx - sw // 2), 0, min(im.size[0], cx + sw // 2), im.size[1]))
        hh = int(rng.integers(430, 560))
        sl = R.print_(sl.resize((max(1, round(sl.size[0] * hh / sl.size[1])), hh), Image.LANCZOS))
        band = max(2, sl.size[0] // 14)
        ext = pixel_stretch(sl, sl.size[0] - band, band, int(sl.size[0] * 0.8))     # the edge pulled out
        R.used("pixel stretch")
        comp = Image.new("RGB", (sl.size[0] + ext.size[0], hh))
        comp.paste(sl, (0, 0))
        comp.paste(ext, (sl.size[0], 0))
        sx = min(W - 50 - comp.size[0], x + i * int(comp.size[0] * 0.62))
        sy = 330 + i * 46
        page.paste(comp, (sx, sy))
        photos.append((sx, sy, sx + comp.size[0], sy + hh))
        d = ImageDraw.Draw(page)
    R.note(d, (40, H - 110), img.size, s, L.camel, face="mono", extra=f" · {key}, very soft")
    # the title: letters at five sizes and baselines, weight 100 → 900, striped toward the accent colour
    t = texts["title"]
    tboxes, tb_all = [], None
    R.defamiliar = "the title's weight stepped 100→900 across letters set at five sizes and baselines"
    for i, ch in enumerate(t):
        size, (lx, ly) = LETTERS[i % len(LETTERS)]
        if i >= 4:
            lx, ly = (right + 30, 20) if i == 4 else (right + 330, 210)
        f = fnt(INTER[min(5, round(i * 5 / max(1, len(t) - 1)))], size)
        m = text_mask((int(f.getlength(ch)) + 20, int(size * 1.2)), ch, f, (0, -int(size * 0.12)))
        m = m.crop(m.getbbox())
        fill = R.strip_fill(img, (0.1 + 0.15 * i, 0.05, 0.95), m.size[0], m.size[1], L.paper,
                            toward=L.title_color or L.camel, mix=0.35)
        page.paste(fill, (lx, ly), m)
        b = (lx, ly, lx + m.size[0], ly + m.size[1])
        tboxes.append(b)
        tb_all = b if tb_all is None else (min(tb_all[0], b[0]), min(tb_all[1], b[1]), max(tb_all[2], b[2]),
                                           max(tb_all[3], b[3]))
    R.title_boxes.append(max(tboxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1])))
    ybot = max(p[3] for p in photos[1:]) + 40 if len(photos) > 1 else 700
    box, done = set_copy(d, (right + 36, ybot), texts, L, W - 56 - (right + 36), size=18, head_size=22, lead=28,
                         tracking=1.2)
    tboxes.append(box)
    R.frame(page, H, L.ink, None, ["No grid (after David Carson, Ray Gun).",
                                   "Misregister · pixel-stretched slivers · title 100→900, striped"], face="mono", px=40)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": [t] + done,
                            "hero": key, "hero_scale": round(s, 2)}, R)
