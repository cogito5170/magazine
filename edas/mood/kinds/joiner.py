"""joiner -- David Hockney's photocollages: one scene rebuilt from many overlapping, slightly turned prints with
white borders.  Hockney shot each print separately; here one source frame is cut into tiles whose sampling
centres are spread 1.3× less than their page positions, so neighbouring tiles repeat parts of the scene the way
shifted viewpoints do.  The structure: the big joiner fills the page height and crosses the gutter; the title is
a joiner too (each letter its own turned tile of Richter strip); the other photos are small joiners.
Recipe: halation + matte on the source and prints, size note, final frame."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..defamiliar import text_mask
from ..moodmachine import Layer
from ..variants import fnt, width
from ._common import W, rotated, set_copy
from .recipe import Recipe, finish


def joiner(page, img, region, cols, rows, rng, border=8, overlap=0.12, rot=(-6, 6)):
    x0, y0, x1, y1 = region
    rw, rh = x1 - x0, y1 - y0
    iw, ih = img.size
    s = rh / ih
    tw, th = rw / cols * (1 + overlap), rh / rows * (1 + overlap)
    boxes = []
    for r in range(rows):
        for c in range(cols):
            zs = s * float(rng.uniform(0.95, 1.08))
            ww, wh = min(iw, tw / zs), min(ih, th / zs)
            sx = ww / 2 + (c + 0.5) / cols * (iw - ww)
            sy = wh / 2 + (r + 0.5) / rows * (ih - wh)
            win = img.crop((round(sx - ww / 2), round(sy - wh / 2), round(sx + ww / 2), round(sy + wh / 2)))
            tile = win.resize((max(1, round(tw - 2 * border)), max(1, round(th - 2 * border))), Image.LANCZOS)
            card = Image.new("RGB", (tile.size[0] + 2 * border, tile.size[1] + 2 * border), (248, 247, 243))
            card.paste(tile, (border, border))
            im = rotated(card, float(rng.uniform(*rot)), None)
            px = x0 + c * rw / cols + rw / cols / 2 - im.size[0] / 2 + float(rng.uniform(-6, 6))
            py = y0 + r * rh / rows + rh / rows / 2 - im.size[1] / 2 + float(rng.uniform(-6, 6))
            page.paste(im, (round(px), round(py)), im)
            boxes.append((round(px), round(py), round(px) + im.size[0], round(py) + im.size[1]))
    return boxes, round(s, 2)


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    src = st.get("source", "night")
    R = Recipe()
    page = Image.new("RGB", (W, H), L.paper)
    rng = np.random.default_rng(36)
    img = R.hero(crops[src])
    rows, cols = 6, 6
    sfit = (H - 80) / img.size[1]
    jw = min(1100, int(img.size[0] * sfit * 1.3))
    x0 = max(200, 1000 - jw // 2 - 160)
    main = (x0, 40, x0 + jw, H - 40)
    boxes, s = joiner(page, img, main, cols, rows, rng, int(st.get("white_border", 8)),
                      float(st.get("overlap", 0.12)), tuple(st.get("tile_rot_deg", (-6, 6))))
    d = ImageDraw.Draw(page)
    R.note(d, (main[0], H - 24), crops[src].size, s, L.camel, face="mono", extra=f" · {rows * cols} tiles from one frame")
    # the title as a joiner: each letter a tile of Richter strip cut from the source, turned like the prints
    rx = max(b[2] for b in boxes) + 60
    colw = W - 56 - rx
    t = texts["title"]
    lines = [t[:3], t[3:]]
    size = 230
    while max(width(x, fnt("bold", size)) for x in lines) + 40 > colw:
        size -= 6
    f = fnt("bold", size)
    R.defamiliar = "the title as a joiner: one turned tile per letter"
    tbox, y = None, 70
    for li, ln in enumerate(lines):
        x = rx
        for i, ch in enumerate(ln):
            cw = int(width(ch, f)) + 24
            m = text_mask((cw, int(size * 1.2)), ch, f, (12, -int(size * 0.1)))
            m = m.rotate(float(rng.uniform(-7, 7)), resample=Image.BICUBIC, expand=True)
            m = m.crop(m.getbbox())
            fill = R.strip_fill(img, (0.35 + 0.08 * (i + 3 * li), 0.1, 0.9), m.size[0], m.size[1], L.paper,
                                toward=L.light or L.ink, mix=0.5)
            page.paste(fill, (x, y + int(rng.integers(-8, 9))), m)
            b = (x, y - 8, x + m.size[0], y + m.size[1] + 8)
            tbox = b if tbox is None else (min(tbox[0], b[0]), min(tbox[1], b[1]), max(tbox[2], b[2]), max(tbox[3], b[3]))
            x += m.size[0] + 4
        y += int(size * 0.92)
    R.title_boxes.append(tbox)
    # the copy anchored to the foot of the column; the other photos as small joiners in between
    from ._common import wrap
    from ..moodmachine import _face
    fb = _face(L.body_face, L.body_weight, 18)
    n_lines = len(wrap(texts["body"], fb, colw)) + (2 if texts.get("head") else 0) + (1 if texts.get("kicker") else 0)
    copy_y = H - 110 - n_lines * 30 - 50
    others = [k for k in ("park", "shop", "rock") if k != src and k in crops][:3]
    gap = 34
    avail = copy_y - 50 - (tbox[3] + 50) - gap * (len(others) - 1)
    hmax = max(60, min(170, avail // max(1, len(others))))
    y = tbox[3] + 50
    for i, k in enumerate(others):
        im = R.print_(crops[k])
        sc = min(colw / im.size[0], hmax / im.size[1])
        w2, h2 = round(im.size[0] * sc), round(im.size[1] * sc)
        c, r = (3, 2) if w2 > h2 * 1.4 else (2, 2)
        b, _ = joiner(page, im, (rx, y, rx + w2, y + h2), c, r, rng, 5, 0.12, (-4, 4))
        boxes += b
        y += h2 + gap
    d = ImageDraw.Draw(page)
    box, done = set_copy(d, (rx, copy_y), texts, L, colw, size=18, head_size=24, lead=30)
    R.frame(page, H, L.ink, None, [f"One frame, {rows * cols} tiles (after Hockney; he shot each).",
                                   "Halation · matte · title as a joiner of strip tiles"],
            face="mono", px=rx)
    return finish(page, L, {"text_boxes": [tbox, box], "photo_boxes": boxes, "texts_set": [t] + done,
                            "joiner": {"source": src, "tiles": rows * cols, "scale": s}}, R)
