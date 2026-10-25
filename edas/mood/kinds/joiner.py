"""joiner -- David Hockney's photocollages: one scene rebuilt from many overlapping, slightly turned prints with
white borders.  Hockney shot each print separately; here one source frame is cut into tiles whose sampling
centres are spread less than their page positions, so neighbouring tiles repeat parts of the scene the way
shifted viewpoints do.  The big joiner crosses the gutter; the other three photos are small joiners."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ._common import W, caption, finish, prep, rotated, set_copy, text_at


def joiner(page, img, region, cols, rows, rng, L, border=8, overlap=0.12, rot=(-6, 6)):
    x0, y0, x1, y1 = region
    rw, rh = x1 - x0, y1 - y0
    iw, ih = img.size
    s = min(rh / ih, rw / iw) * 1.0 if rw / iw < rh / ih else rh / ih
    s = max(s, rh / ih)
    tw, th = rw / cols * (1 + overlap), rh / rows * (1 + overlap)
    boxes = []
    for r in range(rows):
        for c in range(cols):
            zs = s * float(rng.uniform(0.95, 1.08))
            ww, wh = min(iw, tw / zs), min(ih, th / zs)
            u = (c + 0.5) / cols
            v = (r + 0.5) / rows
            sx = ww / 2 + u * (iw - ww)
            sy = wh / 2 + v * (ih - wh)
            win = img.crop((round(sx - ww / 2), round(sy - wh / 2), round(sx + ww / 2), round(sy + wh / 2)))
            tile = win.resize((max(1, round(tw - 2 * border)), max(1, round(th - 2 * border))), Image.LANCZOS)
            card = Image.new("RGB", (tile.size[0] + 2 * border, tile.size[1] + 2 * border), (248, 247, 243))
            card.paste(prep(tile, L), (border, border))
            im = rotated(card, float(rng.uniform(*rot)), None)
            px = x0 + c * rw / cols + rw / cols / 2 - im.size[0] / 2 + float(rng.uniform(-6, 6))
            py = y0 + r * rh / rows + rh / rows / 2 - im.size[1] / 2 + float(rng.uniform(-6, 6))
            page.paste(im, (round(px), round(py)), im)
            boxes.append((round(px), round(py), round(px) + im.size[0], round(py) + im.size[1]))
    return boxes, round(s, 2)


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    src = st.get("source", "night")
    n = int(st.get("tiles", 36))
    rot = tuple(st.get("tile_rot_deg", (-6, 6)))
    page = Image.new("RGB", (W, H), L.paper)
    rng = np.random.default_rng(36)
    img = crops[src]
    aspect = img.size[0] / img.size[1]
    rows = 6 if n == 36 else int(round(np.sqrt(n)))
    cols = max(2, n // rows)
    sfit = (H - 120) / img.size[1]
    jw = min(1240, int(img.size[0] * sfit * 1.3))
    main = (780 - jw // 2, 60, 780 + jw // 2, H - 60)
    boxes, s = joiner(page, img, main, cols, rows, rng, L, int(st.get("white_border", 8)),
                      float(st.get("overlap", 0.12)), rot)
    d = ImageDraw.Draw(page)
    others = [k for k in ("park", "shop", "rock") if k != src and k in crops]
    slots = {0: (1470, 190, 1950, 420), 1: (1470, 470, 1620, 760), 2: (1660, 470, 1950, 760)}
    small = {}
    for i, k in enumerate(others[:3]):
        x0, y0, x1, y1 = slots[i]
        im = crops[k]
        sc = min((x1 - x0) / im.size[0], (y1 - y0) / im.size[1])
        w2, h2 = im.size[0] * sc, im.size[1] * sc
        reg = (round(x0 + (x1 - x0 - w2) / 2), round(y0 + (y1 - y0 - h2) / 2),
               round(x0 + (x1 - x0 + w2) / 2), round(y0 + (y1 - y0 + h2) / 2))
        c, r = (3, 2) if w2 > h2 * 1.4 else (2, 3) if h2 > w2 * 1.4 else (2, 2)
        b, ss = joiner(page, im, reg, c, r, rng, L, 5, 0.12, (-4, 4))
        boxes += b
        small[k] = {"tiles": c * r, "scale": ss}
    d = ImageDraw.Draw(page)
    ft = _face(L.title_face, L.title_weight, 64)
    tbox = text_at(d, (1470, 70), texts["title"], ft, L.title_color or L.ink, 8)
    box, done = set_copy(d, (1470, 830), texts, L, 470, size=19, head_size=24)
    caption(d, (1470, H - 70), f"{rows * cols} tiles cut from one {img.size[0]} × {img.size[1]} frame, ×{s}", L)
    return finish(page, L, {"text_boxes": [tbox, box], "photo_boxes": boxes, "texts_set": [texts["title"]] + done,
                            "joiner": {"source": src, "tiles": rows * cols, "scale": s, "aspect": round(aspect, 2)},
                            "small_joiners": small})
