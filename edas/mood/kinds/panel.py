"""panel -- Sophie Calle's pairing of a framed photograph with a framed text panel, hung like evidence.  Left
page: the night photo in black and white, black frame, white mat.  Right page: the copy, verbatim, framed the
same way, its first line typed (the title in a monospaced face; the Korean copy is set in Pretendard because no
bundled monospaced face has Hangul).  Three small framed prints in a row under the panel."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer
from ..variants import fnt
from ._common import W, caption, finish, fit, framed, prep, set_copy, text_at

MAT_C, FRAME_C = (252, 252, 250), (18, 18, 18)


def render(crops, texts, L: Layer, persons, H=1231):
    page = Image.new("RGB", (W, H), L.paper)
    hero, s = fit(prep(crops["night"], L, hero=True), 700, H - 330)
    fr = framed(hero, 64, 12, MAT_C, FRAME_C)
    hx, hy = 500 - fr.size[0] // 2, (H - fr.size[1]) // 2 - 10
    page.paste(fr, (hx, hy))
    photos = [(hx + 76, hy + 76, hx + 76 + hero.size[0], hy + 76 + hero.size[1])]
    d = ImageDraw.Draw(page)
    caption(d, (hx, hy + fr.size[1] + 16), f"night, {crops['night'].size[0]} × {crops['night'].size[1]} px, ×{s:.2f}", L)
    # the text panel: drawn as a frame and a mat, then the copy typed onto the mat
    pw = 680
    px0, py0 = 1500 - pw // 2, 110
    tmp = Image.new("RGB", (pw, 900), MAT_C)
    td = ImageDraw.Draw(tmp)
    t1 = text_at(td, (76, 76), texts["title"], fnt("mono", 30), L.ink, 2)
    box, done = set_copy(td, (76, t1[3] + 40), texts, L, pw - 152, size=19, head_size=24, face="sans")
    ph = box[3] + 76
    panel = framed(tmp.crop((12, 12, pw - 12, ph - 12)), 0, 12, MAT_C, FRAME_C)
    page.paste(panel, (px0, py0))
    tboxes = [(px0 + t1[0], py0 + t1[1], px0 + t1[2], py0 + t1[3]), (px0 + box[0], py0 + box[1], px0 + box[2], py0 + box[3])]
    y = py0 + panel.size[1] + 90
    items = []
    for k in ("park", "shop", "rock"):
        if k == "night" or k not in crops:
            continue
        im, sc = fit(prep(crops[k], L), 320, 170)
        items.append((k, framed(im, 22, 6, MAT_C, FRAME_C), im, sc))
    total = sum(f.size[0] for _, f, _, _ in items) + 30 * (len(items) - 1)
    x = 1500 - total // 2
    for k, f, im, sc in items:
        page.paste(f, (x, y))
        photos.append((x + 28, y + 28, x + 28 + im.size[0], y + 28 + im.size[1]))
        caption(d, (x, y + f.size[1] + 12), f"{k}, ×{sc:.2f}", L)
        x += f.size[0] + 30
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": [texts["title"]] + done,
                            "frames": "black 12 px, white mat 64 px (prints 6 / 22)",
                            "type_note": "title in JetBrains Mono; Korean copy in Pretendard (no Hangul mono bundled)"})
