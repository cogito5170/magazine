"""diagonal -- after Rodchenko: the black-and-white photograph turned off the level (his odd angles and
diagonal compositions), a red wedge cutting the spread from the top left, the title white in the wedge, the
copy black on white panels over the photograph.  Every element keeps the same angle family.
(Mood writer, round 3.)"""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import _grade
from ._common import W
from ._declare import strip_paste, bordered, copy_lines, mask_paste, panel_line
from ._common import cover_fill
from .recipe import Recipe, finish

RED, WHITE, BLACK = (206, 28, 32), (246, 244, 238), (14, 14, 14)


def render(crops, texts, L, persons, H=1231):
    st = texts.get("structure") or {}
    red, ang = tuple(st.get("wedge", RED)), float(st.get("angle", 8))
    R = Recipe()
    key = "park" if crops["park"].size[0] >= 600 else "night"
    img, pb = crops[key], persons[key]
    big, info = cover_fill(_grade(img, L), (int(W * 1.3), int(H * 1.3)),
                           focus=(((pb[0] + pb[2]) / 2) / img.size[0], (pb[1] + 0.3 * (pb[3] - pb[1])) / img.size[1]))
    turned = big.rotate(ang, resample=Image.BICUBIC)
    l, t = (turned.size[0] - W) // 2, (turned.size[1] - H) // 2
    page = R.misreg(R.hero(turned.crop((l, t, l + W, t + H)), glow=False), 3)
    d = ImageDraw.Draw(page)
    wx, wy = int(W * 0.66), int(H * 0.92)
    d.polygon([(0, 0), (wx, 0), (0, wy)], fill=red)
    photos, panels, tboxes, done = [(0, 0, W, H)], [], [], []
    m = R.ramp_mask(texts["title"], 210, tracking=4)
    m = m.crop(m.getbbox())
    tb = strip_paste(R, page, m, (56, 86), _grade(img, L), WHITE)
    tboxes.append(tb)
    R.title_boxes.append(tb)
    panels.append({"box": tb, "fill": red, "text": WHITE})
    done.append(texts["title"])
    # prints inside the wedge, under the title, framed white
    ih, x, yi = 150, 60, tb[3] + 50
    for k in [k for k in ("night", "shop", "rock", "park") if k != key][:3]:
        im, s = bordered(R, crops[k], L, ih, WHITE, border=6)
        if x + im.size[0] > wx * (1 - (yi + ih) / wy) - 20:
            break
        page.paste(im, (x, yi))
        photos.append((x, yi, x + im.size[0], yi + im.size[1]))
        x += im.size[0] + 26
    lines = copy_lines(texts, L, 24, 760)
    y = H - 90 - sum(52 for _ in lines)
    for k, ln, f in lines:
        b = panel_line(page, (W - 60 - 820, y), ln, f, BLACK, WHITE, pad=(16, 8))
        panels.append({"box": b, "fill": WHITE, "text": BLACK})
        tboxes.append(b)
        y = b[3] + 4
        if texts[k] not in done:
            done.append(texts[k])
    d.rectangle((W - 880, H - 60, W - 40, H - 30), fill=BLACK)
    R.note(d, (W - 860, H - 54), img.size, info["scale"], WHITE, face="mono",
           extra=f" · {key}, black and white, turned {ang:.0f}°")
    R.frame(page, H, WHITE, None, ["A red wedge over a photograph turned off the level (after Rodchenko).",
                                   "Matte · misregister 3 px · title 100→900"],
            face="mono", head_fill=WHITE, px=40)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done,
                            "panels": panels, "hero": key}, R)
