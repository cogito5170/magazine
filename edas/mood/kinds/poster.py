"""poster -- after the Guerrilla Girls' 1989 Met poster: a stark yellow ground, a black-and-white figure,
loud black type, one small pink element.  The title is cut on its own centre line (Black | Thin); the copy is
set black on the yellow; the prints run in a row with black borders.  (Mood writer, round 3.)"""
from __future__ import annotations

from PIL import ImageDraw

from ..variants import fnt
from ._common import W, fit
from ._declare import strip_paste, bordered, copy_lines, mask_paste
from .recipe import Recipe, finish
from ..moodmachine import _grade

YELLOW, BLACK, PINK = (255, 212, 0), (14, 14, 14), (240, 120, 170)


def two_weights(text, fa, fb, tracking=2):
    """The word's first half (by letters, the full stop counted with the second) in one weight, the rest in another."""
    from PIL import Image
    k = (len(text.rstrip(".")) + 1) // 2
    size = max(fa.size, fb.size)
    w = int(fa.getlength(text[:k]) + fb.getlength(text[k:]) + tracking * len(text)) + 30
    m = Image.new("L", (w, int(size * 1.25)), 0)
    d = ImageDraw.Draw(m)
    x = 0.0
    for i, c in enumerate(text):
        f = fa if i < k else fb
        d.text((x, -int(size * 0.12)), c, font=f, fill=255)
        x += f.getlength(c) + tracking
    return m.crop(m.getbbox())


def render(crops, texts, L, persons, H=1231):
    st = texts.get("structure") or {}
    ground = tuple(st.get("ground", YELLOW))
    R = Recipe()
    G = W // 2
    page = __import__("PIL.Image", fromlist=["Image"]).new("RGB", (W, H), ground)
    key = "night"
    img = crops[key]
    hero, s = fit(_grade(img, L), W - G - 100, H - 140)
    hx, hy = W - 60 - hero.size[0], (H - hero.size[1]) // 2
    page.paste(R.hero(hero, slit=(int(hero.size[0] * 0.8), hero.size[0]), glow=False), (hx, hy))
    photos, tboxes, done = [(hx, hy, hx + hero.size[0], hy + hero.size[1])], [], []
    d = ImageDraw.Draw(page)
    size = 280
    while True:
        m = two_weights(texts["title"], fnt("black", size), fnt("thin", size))
        if m.size[0] <= hx - 110 or size < 120:
            break
        size -= 10
    tb = strip_paste(R, page, m, (56, 92), _grade(img, L), BLACK)
    tboxes.append(tb)
    R.title_boxes.append(tb)
    done.append(texts["title"])
    y = tb[3] + 56
    for k, ln, f in copy_lines(texts, L, 26, hx - 160):
        d.text((60, y), ln, font=f, fill=BLACK)
        bb = d.textbbox((60, y), ln, font=f)
        tboxes.append(bb)
        y = bb[3] + (14 if k == "body" else 22)
        if texts[k] not in done:
            done.append(texts[k])
    R.defamiliar = "the title in two weights joined at a letter: Black | Thin"
    ih, x, yi = 170, 60, y + 60
    for k in [k for k in ("park", "shop", "rock", "night") if k != key][:3]:
        im, s2 = bordered(R, crops[k], L, ih, BLACK, border=6)
        if x + im.size[0] > hx - 60:
            break
        page.paste(im, (x, yi))
        photos.append((x, yi, x + im.size[0], yi + im.size[1]))
        x += im.size[0] + 30
    d.rectangle((0, H - 18, 260, H), fill=PINK)
    R.note(d, (hx, hy + hero.size[1] + 14), img.size, s, BLACK, face="mono", extra=f" · {key}, black and white")
    R.frame(page, H, BLACK, None, ["Black on a stark yellow ground, one pink element (after the Guerrilla Girls, 1989).",
                                   "Slit-scan amp 40 · matte · title on its centre line, Black | Thin"],
            face="mono", head_fill=BLACK, proc_fill=BLACK, px=300)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done, "hero": key}, R)
