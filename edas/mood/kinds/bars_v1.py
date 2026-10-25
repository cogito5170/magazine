"""bars_v1 -- frozen copy of kinds/bars.py at commit fda3f55 (the render the user liked for the cover: "이건 좋아",
2026-10-25). Do not edit; it reproduces that cover.

bars -- Barbara Kruger: one black-and-white photograph across both pages, the title and the copy set
white on red bars laid across it (Inter Black/Bold sheared 12° as an oblique; Futura is not bundled).  The
other photos are three small insets with a red border on the right page.  Every text box sits on a solid
panel, which the page reports so the judge can measure it."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ._common import W, caption, cover_fill, finish, prep, scale_h, wrap
from ..variants import width


def bar(page, x, y, text, f, fg, bg, pad=(22, 12), shear=0.21):
    tw = int(width(text, f)) + 2 * pad[0] + int(f.size * shear)
    asc, desc = f.getmetrics()
    th = asc + desc + 2 * pad[1]
    im = Image.new("RGB", (tw, th), bg)
    m = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(m).text((pad[0], pad[1]), text, font=f, fill=255)
    m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * th * 0.5, 0, 1, 0), resample=Image.BICUBIC)
    im.paste(Image.new("RGB", (tw, th), fg), (0, 0), m)
    page.paste(im, (x, y))
    return (x, y, x + tw, y + th)


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    red = tuple(st.get("bar_color", (204, 20, 30)))
    fg = tuple(st.get("text_color", (255, 255, 255)))
    key = "park" if crops["park"].size[0] >= 600 else max(crops, key=lambda k: crops[k].size[0] * crops[k].size[1])
    img, pb = crops[key], persons[key]
    hero, info = cover_fill(img, (W, H), focus=(((pb[0] + pb[2]) / 2) / img.size[0], 0.5))
    page = prep(hero, L, hero=True)
    photos, panels, tboxes, done = [(0, 0, W, H)], [], [], []
    ft = _face("inter", "Black", 130)
    b = bar(page, 60, int(H * 0.18) - 60, texts["title"], ft, fg, red, (28, 6))
    panels.append(b)
    tboxes.append(b)
    done.append(texts["title"])
    fs = _face(L.body_face, L.body_weight, 34)
    y = int(H * 0.64) - 60
    for key_ in ("head", "kicker", "body"):
        if not texts.get(key_):
            continue
        lines = wrap(texts[key_], fs, 1300) if key_ == "body" else [texts[key_]]
        for ln in lines:
            b = bar(page, 60, y, ln, fs, fg, red)
            panels.append(b)
            tboxes.append(b)
            y = b[3] + 10
        done.append(texts[key_])
    d = ImageDraw.Draw(page)
    title_bottom = panels[0][3]
    copy_top = panels[1][1] if len(panels) > 1 else H - 60
    ih = min(250, copy_top - title_bottom - 100)
    x, yi = 68, title_bottom + 50
    for k in [k for k in ("night", "shop", "rock", "park") if k != key][:3]:
        im, s = scale_h(prep(crops[k], L), ih)
        d.rectangle((x - 8, yi - 8, x + im.size[0] + 7, yi + ih + 7), fill=red)
        page.paste(im, (x, yi))
        photos.append((x - 8, yi - 8, x + im.size[0] + 8, yi + ih + 8))
        x += im.size[0] + 30
    lum = sum(page.crop((W - 520, H - 44, W - 60, H - 24)).convert("L").getdata()) / (460 * 20)
    caption(d, (W - 520, H - 40), f"{key}, black and white, ×{info['scale']:.2f}", L,
            color=(16, 16, 16) if lum > 128 else (240, 240, 240))
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done,
                            "panels": [{"box": p, "fill": red, "text": fg} for p in panels], "hero": key})
