"""Structure lever for the mood machine: the layout families of the previous session's rounds, each able to
carry any mood layer.  `nocturne` is the approved structure (moodmachine.nocturne_mood, untouched).

    lineup   four full-height bands, one body per place, the title crossing all four (artdirect.lineup, round 2)
    wild     one photograph as the whole spread, an oversized title off the edge, the rest as a contact strip
             (artdirect.wild, round 2)
    eyeline  every person scaled to one height, centres on one shared eye line, photos shoulder to shoulder
             (rapport.rapport_spread placement)
Rules kept so the judge can measure: copy sits on a solid panel of the paper colour, never on a photograph;
every layout reports its text and photo boxes.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .artdirect import cover, grain
from .contemporary import halation, matte, richter_strip, ruff_jpeg, soft_jpeg
from .defamiliar import text_mask
from .moodmachine import Layer, _face, _fx, _grade, nocturne_mood
from .photo_led import tracked
from .variants import fnt, width

W = 2000


def _hero(img, L: Layer):
    thr, rad, tint, st = L.halation
    g = _grade(img, L)
    if thr < 255 and st > 0:
        g = halation(g, thr, rad, tint, st)
    g = matte(g, *L.hero_matte)
    return _fx(g, L.hero_fx, L.paper, L.ink) if L.hero_fx else g


def _print(img, L: Layer):
    g = matte(_grade(img, L), *L.print_matte)
    if L.print_blur:
        g = g.filter(ImageFilter.GaussianBlur(L.print_blur))
    return _fx(g, L.print_fx, L.paper, L.ink) if L.print_fx else g


def _shadow(img, L: Layer):
    if L.shadow == "soft_jpeg":
        return soft_jpeg(img, L.paper, L.taupe)
    if L.shadow == "ruff":
        return ruff_jpeg(img, factor=4, quality=3)
    if L.shadow == "threshold":
        from .defamiliar2 import threshold_copy
        return threshold_copy(img, 0.45, L.taupe, L.paper)
    return None


def _title(page, text, size, xy, L: Layer, strip_src, tracking=10, color=None):
    f = _face(L.title_face, L.title_weight, size)
    tw = int(width(text, f, tracking)) + 40
    th = int(size * 1.25)
    m = text_mask((tw, th), text, f, (0, -int(size * 0.16)), tracking)
    if L.title_mode == "outline":
        hard = m.point(lambda v: 255 if v > 127 else 0)
        m = ImageChops.subtract(hard.filter(ImageFilter.MaxFilter(5)), hard.filter(ImageFilter.MinFilter(3)))
    if L.title_mode == "strip":
        a = np.asarray(strip_src, float)
        col = a[int(a.shape[0] * L.strip_col[1]):int(a.shape[0] * L.strip_col[2]), int(a.shape[1] * L.strip_col[0]), :]
        pa, pb, pc = L.strip_mix
        col = pa * col + pb * np.array(L.paper, float) * pc
        fill = richter_strip(col, tw, th, stages=L.stages).transpose(Image.ROTATE_90).resize((tw, th))
    else:
        fill = Image.new("RGB", (tw, th), color or L.title_color or L.ink)
    page.paste(fill, xy, m)
    return (xy[0], xy[1], xy[0] + tw, xy[1] + th)


def _text_panel(page, box, texts, L: Layer):
    """Head + body (or kicker + body) set horizontally on a solid paper panel; returns the used box."""
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(page)
    d.rectangle(box, fill=L.paper)
    pad = 28
    x, y = x0 + pad, y0 + pad
    if texts.get("head"):
        fh = _face(L.body_face, "Medium" if L.body_face == "serif" else "Regular", 28)
        d.text((x, y), texts["head"], font=fh, fill=L.ink)
        y += 52
    if texts.get("kicker"):
        tracked(d, (x, y), texts["kicker"], fnt("mono", 13) if L.caption_face == "mono" else fnt("serif_it", 16),
                L.camel, 3)
        y += 34
    fb = _face(L.body_face, L.body_weight, 20)
    cur, lines = "", []
    for wd in texts["body"].split(" "):
        cand = (cur + " " + wd).strip()
        if fb.getlength(cand) > (x1 - x0 - 2 * pad) and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    lines.append(cur)
    for ln in lines:
        d.text((x, y), ln, font=fb, fill=L.ink)
        y += 34
    return (x0, y0, x1, max(y1, y + pad))


def _cap(d, xy, text, L):
    f = fnt("serif_it", 15) if L.caption_face == "serif_it" else fnt("mono", 11)
    tracked(d, xy, text, f, L.camel, 0.3)


def lineup_mood(crops, texts, L: Layer, persons, H=1231):
    page = Image.new("RGB", (W, H), L.paper)
    pw = W // 4
    boxes = []
    for i, k in enumerate(("night", "park", "shop", "rock")):
        im = crops[k]
        px = persons[k]
        fx = ((px[0] + px[2]) / 2) / im.size[0]
        band, info = cover(im, (pw - 6, H), focus=(fx, 0.5))
        band = _hero(band, L) if i == 0 else _print(band, L)
        page.paste(band, (i * pw + 3, 0))
        boxes.append((i * pw + 3, 0, i * pw + pw - 3, H))
    tb = _title(page, texts["title"], 300, (60, int(H * 0.38)), L, crops[L.strip_key], tracking=40)
    tbox = _text_panel(page, (W - 640, H - 330, W - 40, H - 40), texts, L)
    return page, {"text_boxes": [tbox], "photo_boxes": [], "title_box": tb, "copy_on_photo_ok": False}


def wild_mood(crops, texts, L: Layer, persons, H=1231):
    key = "rock" if "rock" in crops and crops["rock"].size[0] > 300 else "night"
    page = Image.new("RGB", (W, H), L.paper)
    full, info = cover(crops[key], (W, H), focus=(0.5, 0.48))
    page.paste(_hero(full, L), (0, 0))
    tb = _title(page, texts["title"].rstrip("."), 520, (-40, -120), L, crops[L.strip_key], tracking=-10)
    d = ImageDraw.Draw(page)
    x, y = 60, H - 330
    boxes = []
    for k in [k for k in ("night", "park", "shop", "rock") if k != key]:
        im = crops[k]
        s = 220 / im.size[1]
        im2 = _print(im.resize((max(1, round(im.size[0] * s)), 220), Image.LANCZOS), L)
        sh = _shadow(im2, L)
        if sh is not None:
            page.paste(sh, (x + 12, y + 14))
        page.paste(im2, (x, y))
        boxes.append((x, y, x + im2.size[0], y + 220))
        x += im2.size[0] + 18
    tbox = _text_panel(page, (W - 700, H - 360, W - 40, H - 40), texts, L)
    return page, {"text_boxes": [tbox], "photo_boxes": boxes, "hero": key}


def eyeline_mood(crops, texts, L: Layer, persons, H=1231, eye=470, person_h=360):
    page = Image.new("RGB", (W, H), L.paper)
    items = []
    for k in ("night", "park", "shop", "rock"):
        im, px = crops[k], persons[k]
        s = person_h / max(1, px[3] - px[1])
        s = min(s, 620 / im.size[0], 700 / im.size[1])
        im2 = im.resize((max(1, round(im.size[0] * s)), max(1, round(im.size[1] * s))), Image.LANCZOS)
        im2 = _hero(im2, L) if k == "night" else _print(im2, L)
        b = tuple(round(v * s) for v in px)
        items.append((k, im2, b, s))
    total = sum(it[1].size[0] for it in items)
    gap = (W - 120 - total) / 3
    x = 60
    boxes = []
    for k, im2, b, s in items:
        y = int(np.clip(eye - (b[1] + b[3]) / 2, 40, H - 380 - im2.size[1]))
        sh = _shadow(im2, L)
        if sh is not None:
            page.paste(sh, (int(x) + 10, y + 16))
        page.paste(im2, (int(x), y))
        boxes.append((int(x), y, int(x) + im2.size[0], y + im2.size[1]))
        x += im2.size[0] + gap
    d = ImageDraw.Draw(page)
    for x0 in (14, W - 44):
        d.line([(x0, eye), (x0 + 30, eye)], fill=L.camel, width=2)
    tb = _title(page, texts["title"], 150, (60, H - 300), L, crops[L.strip_key], tracking=6)
    tbox = _text_panel(page, (W - 760, H - 330, W - 40, H - 40), texts, L)
    return page, {"text_boxes": [tbox], "photo_boxes": boxes, "title_box": tb}


def render(crops, texts, L: Layer, persons, H=1231):
    if L.structure == "nocturne":
        return nocturne_mood(crops, texts, L, H=H)
    fn = {"lineup": lineup_mood, "wild": wild_mood, "eyeline": eyeline_mood}[L.structure]
    page, spec = fn(crops, texts, L, persons, H=H)
    return grain(page, L.grain[0], 12, size=L.grain[1]), {"layer": L.__dict__, **spec}
