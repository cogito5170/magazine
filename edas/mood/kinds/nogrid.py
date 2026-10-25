"""nogrid -- David Carson's Ray Gun pages: no grid.  One photo cropped to the person and blown up about 3× so
it bleeds over the gutter; the title broken into its letters at five sizes and baselines; the other photos cut
to slivers that overlap each other; the copy set once, plainly, so it can be read."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ._common import W, caption, finish, prep, set_copy, text_at

LETTERS = [(400, (40, -40)), (170, (420, 380)), (300, (60, 520)), (130, (430, 820)), (320, (1520, -10)),
           (110, (1830, 230))]


def render(crops, texts, L: Layer, persons, H=1231):
    key = "park" if crops["park"].size[0] >= 600 else max(crops, key=lambda k: crops[k].size[0] * crops[k].size[1])
    page = Image.new("RGB", (W, H), L.paper)
    img, pb = crops[key], persons[key]
    wx0, wx1 = max(0, pb[0] - 60), min(img.size[0], pb[2] + 60)
    win = img.crop((wx0, 0, wx1, img.size[1]))
    s = (H + 20) / win.size[1]
    hero = prep(win.resize((round(win.size[0] * s), H + 20), Image.LANCZOS), L, hero=True)
    hx = 1000 - int(hero.size[0] * 0.45)
    page.paste(hero, (hx, -10))
    photos = [(hx, 0, hx + hero.size[0], H)]
    right = hx + hero.size[0]
    rng = np.random.default_rng(21)
    others = [k for k in ("night", "shop", "rock", "park") if k != key][:3]
    x = right + 30
    slw = max(60, (W - 40 - x) // 4)
    for i, k in enumerate(others):
        im = crops[k]
        q = persons[k]
        sw = max(20, int((q[2] - q[0]) * 0.35))
        cx = (q[0] + q[2]) // 2 + int(rng.integers(-sw // 2, sw // 2 + 1))
        sl = im.crop((max(0, cx - sw // 2), 0, min(im.size[0], cx + sw // 2), im.size[1]))
        hh = int(rng.integers(420, 600))
        sc = hh / sl.size[1]
        sl = prep(sl.resize((max(1, round(sl.size[0] * sc)), hh), Image.LANCZOS), L)
        sx = min(W - 40 - sl.size[0], x + i * int(slw * 0.8))
        sy = 340 + i * 40
        page.paste(sl, (sx, sy))
        photos.append((sx, sy, sx + sl.size[0], sy + hh))
    d = ImageDraw.Draw(page)
    t = texts["title"]
    tboxes = []
    for i, ch in enumerate(t):
        size, (lx, ly) = LETTERS[i % len(LETTERS)]
        if lx >= 1000:
            lx = max(lx, right + 20)
        f = _face(L.title_face, L.title_weight, size)
        tboxes.append(text_at(d, (lx, ly), ch, f, L.title_color or L.ink))
    ybot = max(p[3] for p in photos[1:]) + 40 if len(photos) > 1 else 700
    box, done = set_copy(d, (right + 30, ybot), texts, L, W - 50 - (right + 30), size=18, head_size=22, lead=28,
                         tracking=1.2)
    tboxes.append(box)
    caption(d, (40, H - 40), f"{key} ×{s:.2f} (very soft), slivers of {', '.join(others)}", L)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": [t] + done,
                            "hero": key, "hero_scale": round(s, 2), "title_letters": len(t)})
