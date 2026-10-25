"""panel -- Sophie Calle's pairing of a framed photograph with a framed text panel, hung like evidence.  The
structure: the photograph in black and white, framed, as tall as the page allows on the left; on the right the
text panel framed the same way, its headline the title at display size with its weight stepped 100 → 900
(ostranenie: the word read slowly, letter by letter) and filled with a Richter strip from the photo; three small
framed prints hang under it.  Recipe: matte and a progressive blur growing away from the person (the record
fading); size notes; final frame.  No shadows: Calle's frames hang flat."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..moodmachine import Layer, _grade
from ._common import W, fit, framed, set_copy
from .recipe import Recipe, finish

MAT_C, FRAME_C = (252, 252, 250), (18, 18, 18)


def blur_away(img, box, max_r=7, reach=260):
    """Progressive blur that grows with the distance from the person box (sharp on the person)."""
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    dx = np.maximum(np.maximum(box[0] - xx, xx - box[2]), 0)
    dy = np.maximum(np.maximum(box[1] - yy, yy - box[3]), 0)
    t = np.clip(np.hypot(dx, dy) / reach, 0, 1)[..., None]
    a = np.asarray(img, float)
    b = np.asarray(img.filter(ImageFilter.GaussianBlur(max_r)), float)
    return Image.fromarray((a * (1 - t) + b * t).astype("uint8"))


def render(crops, texts, L: Layer, persons, H=1231):
    R = Recipe()
    page = Image.new("RGB", (W, H), L.paper)
    night, pb = _grade(crops["night"], L), persons["night"]
    hero, s = fit(night, 760, H - 384)
    hero = blur_away(hero, tuple(round(v * s) for v in pb))
    R.used("progressive blur")
    hero = R.print_(hero)
    fr = framed(hero, 48, 14, MAT_C, FRAME_C)
    hx, hy = 520 - fr.size[0] // 2, 110
    page.paste(fr, (hx, hy))
    photos = [(hx + 62, hy + 62, hx + 62 + hero.size[0], hy + 62 + hero.size[1])]
    d = ImageDraw.Draw(page)
    R.note(d, (hx, hy + fr.size[1] + 16), crops["night"].size, s, L.camel, face="mono",
           extra=" · black and white, blurred away from the person")
    # the text panel: headline = the title, ramped 100→900, striped from the photo
    pw = 880
    px0, py0 = 1530 - pw // 2, 90
    panel = Image.new("RGB", (pw, 1000), MAT_C)
    size = 300
    while True:
        m = R.ramp_mask(texts["title"], size, tracking=2)
        m = m.crop(m.getbbox())
        if m.size[0] <= pw - 110:
            break
        size -= 6
    fill = R.strip_fill(night, (0.62, 0.05, 0.95), m.size[0], m.size[1], MAT_C, toward=L.ink, mix=0.5)
    panel.paste(fill, (60, 70), m)
    tl = (60, 70, 60 + m.size[0], 70 + m.size[1])
    td = ImageDraw.Draw(panel)
    box, done = set_copy(td, (64, tl[3] + 56), texts, L, pw - 128, size=20, head_size=26, face="sans")
    ph = box[3] + 64
    panel = framed(panel.crop((0, 0, pw, ph)), 0, 14, MAT_C, FRAME_C)
    page.paste(panel, (px0, py0))
    off = lambda b: (px0 + 14 + b[0], py0 + 14 + b[1], px0 + 14 + b[2], py0 + 14 + b[3])  # noqa: E731
    R.title_boxes.append(off(tl))
    tboxes = [off(tl), off(box)]
    y = py0 + panel.size[1] + 80
    items = []
    for k in ("park", "shop", "rock"):
        if k in crops:
            im, sc = fit(R.print_(_grade(crops[k], L)), 300, 160)
            items.append((k, framed(im, 20, 6, MAT_C, FRAME_C), im, sc))
    total = sum(f.size[0] for _, f, _, _ in items) + 50 * (len(items) - 1)
    x = 1530 - total // 2
    d = ImageDraw.Draw(page)
    for k, f, im, sc in items:
        page.paste(f, (x, y))
        photos.append((x + 26, y + 26, x + 26 + im.size[0], y + 26 + im.size[1]))
        d = ImageDraw.Draw(page)
        R.note(d, (x, y + f.size[1] + 14), crops[k].size, sc, L.camel, face="mono")
        x += f.size[0] + 50
    R.frame(page, H, L.ink, None, ["A photograph and a text panel, framed alike (after Sophie Calle).",
                                   "Matte · blur growing away from the person · title ramped 100→900, striped"],
            face="mono", px=40)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": [texts["title"]] + done,
                            "type_note": "headline Inter Display 100→900; Korean copy in Pretendard"}, R)
