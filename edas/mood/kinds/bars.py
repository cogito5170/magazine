"""bars -- Barbara Kruger: one black-and-white photograph across both pages, the title and the copy set
white on red bars laid across it (Inter Black/Bold sheared 12° as an oblique; Futura is not bundled).  The
other photos are three small insets with a red border on the right page.  Every text box sits on a solid
panel, which the page reports so the judge can measure it."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face, _grade
from ..variants import fnt, width
from ._common import W, cover_fill, scale_h, wrap
from .recipe import INTER, Recipe, finish


def bar(page, x, y, text, f, fg, bg, pad=(22, 12), shear=0.21, mask=None, fill=None):
    if mask is not None:
        tw, th = mask.size[0] + 2 * pad[0] + int(mask.size[1] * shear), mask.size[1] + 2 * pad[1]
    else:
        tw = int(width(text, f)) + 2 * pad[0] + int(f.size * shear)
        asc, desc = f.getmetrics()
        th = asc + desc + 2 * pad[1]
    im = Image.new("RGB", (tw, th), bg)
    m = Image.new("L", (tw, th), 0)
    if mask is not None:
        m.paste(mask, (pad[0], pad[1]))
    else:
        ImageDraw.Draw(m).text((pad[0], pad[1]), text, font=f, fill=255)
    m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * th * 0.5, 0, 1, 0), resample=Image.BICUBIC)
    im.paste(fill.resize((tw, th)) if fill is not None else Image.new("RGB", (tw, th), fg), (0, 0), m)
    page.paste(im, (x, y))
    return (x, y, x + tw, y + th)


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    red = tuple(st.get("bar_color", (204, 20, 30)))
    fg = tuple(st.get("text_color", (255, 255, 255)))
    R = Recipe()
    key = "park" if crops["park"].size[0] >= 600 else max(crops, key=lambda k: crops[k].size[0] * crops[k].size[1])
    img, pb = crops[key], persons[key]
    bw = _grade(img, L)
    hero, info = cover_fill(bw, (W, H), focus=(((pb[0] + pb[2]) / 2) / img.size[0], 0.5))
    page = R.hero(hero, slit=(int(W * 0.8), W), bold=True, glow=False)
    photos, panels, tboxes, done = [(0, 0, W, H)], [], [], []
    # the title bar: weight stepped 100 → 900, the white letters striped (pulled almost to white) from the photo
    size = 186
    m = R.ramp_mask(texts["title"], size, tracking=0)
    m = m.crop(m.getbbox())
    fill = R.strip_fill(bw, (0.3, 0.05, 0.95), m.size[0] + 200, m.size[1] + 40, L.paper, toward=fg, mix=0.2)
    b = bar(page, 56, int(H * 0.16) - 60, texts["title"], None, fg, red, (34, 22), mask=m, fill=fill)
    panels.append(b)
    tboxes.append(b)
    R.title_boxes.append(b)
    done.append(texts["title"])
    fs = _face(L.body_face, L.body_weight, 34)
    y = int(H * 0.62) - 60
    for key_ in ("head", "kicker", "body"):
        if not texts.get(key_):
            continue
        lines = wrap(texts[key_], fs, 1300) if key_ == "body" else [texts[key_]]
        for ln in lines:
            b = bar(page, 56, y, ln, fs, fg, red)
            panels.append(b)
            tboxes.append(b)
            y = b[3] + 10
        done.append(texts[key_])
    d = ImageDraw.Draw(page)
    title_bottom = panels[0][3]
    copy_top = panels[1][1] if len(panels) > 1 else H - 60
    ih = min(250, copy_top - title_bottom - 110)
    x, yi = 64, title_bottom + 54
    for k in [k for k in ("night", "shop", "rock", "park") if k != key][:3]:
        im, s = scale_h(R.print_(_grade(crops[k], L)), ih)
        framed_ = Image.new("RGB", (im.size[0] + 16, ih + 16), red)
        framed_.paste(im, (8, 8))
        page.paste(framed_, (x - 8, yi - 8))
        photos.append((x - 8, yi - 8, x + im.size[0] + 8, yi + ih + 8))
        x += im.size[0] + 44
    d = ImageDraw.Draw(page)
    d.rectangle((W - 580, H - 124, W - 40, H - 30), fill=(16, 16, 16))          # captions on a black bar
    R.note(d, (W - 560, H - 110), img.size, info["scale"], (236, 234, 228), face="mono", extra=f" · {key}, black and white")
    R.defamiliar = "the title's weight stepped 100→900 inside the bar"
    R.frame(page, H, (236, 234, 228), None, ["White on red over black and white (after Barbara Kruger).",
                                             "Slit-scan amp 140 · matte · title 100→900, striped"],
            face="mono", px=W - 560, proc_fill=(236, 234, 228))
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done,
                            "panels": [{"box": p, "fill": red, "text": fg} for p in panels], "hero": key}, R)
