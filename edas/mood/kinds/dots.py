"""dots -- John Baldessari's coloured dots over the faces in found press photographs.  The structure: one press
print blown up to the full right page, three more scattered and turned over the left; over each face a flat
disc in the colour of that person's clothes (saturation ×2).  The title repeats the gesture: its letters striped
from the photo, its counters and the full stop filled as discs (the device).  The disc is a graphic laid on the
print; no photo pixel is generated under it, but it hides the faces, so this kind comes back HOLD until the user
says yes.  Recipe: halation + matte on the big print, matte + soft JPEG shadows on the small ones; size notes."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer
from ..variants import fnt
from ._common import W, cover_fill, fit, mean_sat, rotated, set_copy
from .recipe import Recipe, finish

SLOTS = {"park": ((70, 100, 600, 260), 2.0), "shop": ((740, 130, 180, 310), -3.0),
         "rock": ((240, 450, 430, 240), -1.5)}


def disc(im, pb, s, col):
    ph = pb[3] - pb[1]
    cx, cy = (pb[0] + pb[2]) / 2 * s, (pb[1] + ph * 0.11) * s
    r = min(ph * 0.11 * s * 1.15, (pb[2] - pb[0]) * s * 0.5)
    ImageDraw.Draw(im).ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    return round(r, 1)


def clothes(img, pb):
    ph = pb[3] - pb[1]
    return mean_sat(img, (pb[0], pb[1] + int(ph * 0.35), pb[2], pb[1] + int(ph * 0.75)), 2.0)


def render(crops, texts, L: Layer, persons, H=1231):
    R = Recipe()
    page = Image.new("RGB", (W, H), L.paper)
    dots = {}
    # the big press print: the left page, edge to edge
    img, pb = crops["night"], persons["night"]
    big, info = cover_fill(img, (1000, H), focus=(((pb[0] + pb[2]) / 2) / img.size[0], 0.45))
    s, (wx0, wy0) = info["scale"], info["source_window"][:2]
    big = R.hero(big)
    q = ((pb[0] - wx0) * 1, (pb[1] - wy0) * 1, (pb[2] - wx0) * 1, (pb[3] - wy0) * 1)
    col = clothes(img, pb)
    dots["night"] = {"colour": col, "radius": disc(big, q, s, col)}
    page.paste(big, (1000, 0))           # the big press print on the right page
    photos = [(1000, 0, 2000, H)]
    d = ImageDraw.Draw(page)
    for k, ((x, y, w, h), ang) in SLOTS.items():
        img, pb = crops[k], persons[k]
        im, sc = fit(R.print_(img), w, h)
        whole = tuple(pb) == (0, 0) + img.size          # a detail crop: no measured face, no disc
        if not whole:
            c = clothes(img, pb)
            dots[k] = {"colour": c, "radius": disc(im, pb, sc, c)}
        card = Image.new("RGB", (im.size[0] + 20, im.size[1] + 20), (252, 252, 250))
        card.paste(im, (10, 10))
        R.shadow(page, card, (x, y), L.paper, L.taupe)
        rc = rotated(card, ang, None)
        page.paste(rc, (x, y), rc)
        photos.append((x, y, x + rc.size[0], y + rc.size[1]))
        d = ImageDraw.Draw(page)
        R.note(d, (x, y + rc.size[1] + 30), img.size, sc, L.camel, face="mono")
    # the title, striped from the big print, its full stop a disc in the night's colour
    t = texts["title"]
    size = 236
    f = fnt("bold", size)
    mask = None if t.endswith(".") else R.ramp_mask(t, size, tracking=-4)   # no full stop to turn into a disc
    if mask is not None:
        mask = mask.crop(mask.getbbox())
    tb = R.strip_title(page, t, f, (60, 790), crops["night"], (0.5, 0.35, 0.95), L.paper, tracking=-4,
                       toward=L.ink, mix=0.4, mask=mask)
    d = ImageDraw.Draw(page)
    if t.endswith("."):
        r = size * 0.075
        d.ellipse((tb[2] - 2 * r - 4, tb[3] - 2 * r - 2, tb[2] - 4, tb[3] - 2), fill=dots["night"]["colour"])
        R.defamiliar = "the title's full stop is a disc in the colour of the night figure's clothes"
    box, done = set_copy(d, (60, tb[3] + 30), texts, L, 880, size=17, head_size=22, lead=26)
    R.frame(page, H, L.ink, None, ["Press prints with discs over the faces (after Baldessari, 1985-).",
                                   "Halation · matte · JPEG shadows · disc colour = clothes, saturation ×2"],
            face="mono", px=60)
    return finish(page, L, {"text_boxes": [tb, box], "photo_boxes": photos, "texts_set": [t] + done, "dots": dots,
                            "needs_user_ok": "discs cover the faces (no-overpaint rule)"}, R)
