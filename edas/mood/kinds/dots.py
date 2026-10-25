"""dots -- John Baldessari's coloured dots over the faces in found press photographs.  Four press prints of
different sizes, slightly turned, scattered over both pages; a flat disc sits over each face (the top 22% of
the person box), its colour the mean of the clothes (the 35-75% band of the person box) with saturation ×2.
The disc is a graphic laid on the print; no photo pixel is changed or generated under it.  It still hides the
faces, so this kind is flagged for the user's OK under the no-overpaint rule."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ._common import W, caption, finish, fit, mean_sat, prep, rotated, set_copy, text_at

SLOTS = {"night": ((110, 100, 560, 900), -2.0), "park": ((1120, 90, 800, 380), 1.5),
         "shop": ((720, 560, 250, 420), 2.5), "rock": ((1300, 560, 560, 330), -1.2)}


def render(crops, texts, L: Layer, persons, H=1231):
    page = Image.new("RGB", (W, H), L.paper)
    photos, dots = [], {}
    d = ImageDraw.Draw(page)
    for k, ((x, y, w, h), ang) in SLOTS.items():
        img, pb = crops[k], persons[k]
        ph = pb[3] - pb[1]
        band = (pb[0], pb[1] + int(ph * 0.35), pb[2], pb[1] + int(ph * 0.75))
        col = mean_sat(img, band, 2.0)
        im, s = fit(prep(img, L), w, h)
        dd = ImageDraw.Draw(im)
        cx = (pb[0] + pb[2]) / 2 * s
        cy = (pb[1] + ph * 0.11) * s
        r = min(ph * 0.11 * s * 1.15, (pb[2] - pb[0]) * s * 0.5)
        whole = tuple(pb) == (0, 0) + img.size          # a detail crop: no measured face, no disc
        if not whole:
            dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
        card = Image.new("RGB", (im.size[0] + 24, im.size[1] + 24), (252, 252, 250))
        card.paste(im, (12, 12))
        rc = rotated(card, ang, None)
        page.paste(rc, (x, y), rc)
        photos.append((x, y, x + rc.size[0], y + rc.size[1]))
        dots[k] = {"colour": col, "radius": round(r, 1), "scale": round(s, 2)} if not whole else {"disc": None}
        d = ImageDraw.Draw(page)
    ft = _face(L.title_face, L.title_weight, 46)
    tbox = text_at(d, (110, H - 120), texts["title"], ft, L.title_color or L.ink, 2)
    box, done = set_copy(d, (1120, H - 300), texts, L, 780, size=18, head_size=22, lead=29)
    caption(d, (110, H - 56), "four press prints; discs laid over the faces, colour = clothes ×2 saturation", L)
    return finish(page, L, {"text_boxes": [tbox, box], "photo_boxes": photos, "texts_set": [texts["title"]] + done,
                            "dots": dots, "needs_user_ok": "discs cover the faces (no-overpaint rule)"})
